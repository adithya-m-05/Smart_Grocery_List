"""Receipt-powered grocery list application."""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge

try:
    from google import genai as google_genai
    from google.genai import types as genai_types
except ImportError:
    # Keep existing installations working while they upgrade to google-genai.
    google_genai = None
    genai_types = None

try:
    import google.generativeai as legacy_genai
except ImportError:
    legacy_genai = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "grocery.db"))
EXCEL_PATH = Path(os.getenv("EXCEL_PATH", BASE_DIR / "receipts.xlsx"))
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "frontend"),
    static_folder=str(BASE_DIR / "frontend"),
    static_url_path="",
)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

RECOMMENDATION_MAP = {
    "milk": ["cereal", "cookies"],
    "bread": ["butter", "jam"],
    "rice": ["lentils", "spices"],
    "egg": ["cheese", "bread"],
    "banana": ["milk", "peanut butter"],
    "coffee": ["sugar", "milk"],
    "pasta": ["tomato sauce", "parmesan"],
    "tomato": ["onion", "basil"],
}


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS grocery_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_grocery_items_timestamp "
            "ON grocery_items(timestamp DESC)"
        )


def recommend_items(items):
    purchased = " ".join(item["name"].casefold() for item in items)
    suggestions = set()
    for keyword, related in RECOMMENDATION_MAP.items():
        plural = "(?:s|es)?" if keyword.endswith(("a", "o")) else "s?"
        if re.search(rf"\b{re.escape(keyword)}{plural}\b", purchased):
            suggestions.update(related)
    purchased_words = set(re.findall(r"[a-z]+", purchased))
    return sorted(
        suggestion for suggestion in suggestions
        if not any(word in purchased_words for word in suggestion.casefold().split())
    )


def parse_model_items(response_text):
    """Parse and validate the model's JSON response before storing it."""
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    payload = json.loads(cleaned)
    if isinstance(payload, dict):
        payload = payload.get("items", [])
    if not isinstance(payload, list):
        raise ValueError("The receipt response did not contain an item list.")

    items = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        name = re.sub(r"\s+", " ", str(entry.get("name", ""))).strip()
        try:
            price = float(entry.get("price"))
        except (TypeError, ValueError):
            continue
        if name and len(name) <= 120 and 0 <= price < 1_000_000:
            items.append({"name": name, "price": round(price, 2)})
    return items


def save_items(items):
    if not items:
        return
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [{**item, "timestamp": timestamp} for item in items]
    with get_connection() as connection:
        connection.executemany(
            "INSERT INTO grocery_items (item, price, timestamp) VALUES (?, ?, ?)",
            [(row["name"], row["price"], row["timestamp"]) for row in rows],
        )

    # Excel is a convenient export; SQLite remains the primary data store.
    try:
        export_rows = pd.DataFrame(
            [{"Item": row["name"], "Price": row["price"], "Timestamp": row["timestamp"]}
             for row in rows]
        )
        EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        if EXCEL_PATH.exists():
            old_rows = pd.read_excel(EXCEL_PATH)
            export_rows = pd.concat([old_rows, export_rows], ignore_index=True)
        export_rows.to_excel(EXCEL_PATH, index=False)
    except Exception:
        app.logger.exception("Could not update the Excel export")


def extract_items(image_bytes, mime_type):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Receipt scanning is not configured. Set GEMINI_API_KEY in your environment.")

    prompt = """Read this grocery receipt and return only purchased grocery line items.
Return valid JSON in exactly this shape: {"items":[{"name":"Milk","price":3.49}]}.
Use the final charged price for each item. Exclude tax, subtotal, total, payment,
change, discounts, store details, and non-product lines. Do not guess missing
prices. Use a number for price and an empty array when no items can be read."""
    if google_genai:
        client = google_genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
            config=genai_types.GenerateContentConfig(response_mime_type="application/json"),
        )
    elif legacy_genai:
        legacy_genai.configure(api_key=api_key)
        model = legacy_genai.GenerativeModel(GEMINI_MODEL)
        with Image.open(BytesIO(image_bytes)) as image:
            response = model.generate_content(
                [prompt, image],
                generation_config={"response_mime_type": "application/json"},
            )
    else:
        raise RuntimeError("Install the Gemini SDK with: python -m pip install -r requirements.txt")
    if not response.text:
        raise ValueError("The receipt scanner returned an empty response.")
    return parse_model_items(response.text)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/history")
def history():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, item, price, timestamp FROM grocery_items "
            "ORDER BY timestamp DESC, id DESC LIMIT 100"
        ).fetchall()
    return jsonify({"items": [dict(row) for row in rows]})


@app.route("/upload", methods=["POST"])
def upload():
    receipt = request.files.get("receipt")
    if not receipt or not receipt.filename:
        return jsonify(error="Choose a receipt image to upload."), 400

    image_bytes = receipt.read(MAX_UPLOAD_BYTES + 1)
    if not image_bytes:
        return jsonify(error="The selected file is empty."), 400
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        return jsonify(error="The image must be 8 MB or smaller."), 413

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image_format = image.format
            image.verify()
        if image_format not in ALLOWED_FORMATS:
            return jsonify(error="Use a JPEG, PNG, or WebP receipt image."), 415
        mime_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[image_format]
        items = extract_items(image_bytes, mime_type)
        if items:
            save_items(items)
        return jsonify(items=items, recommendations=recommend_items(items))
    except (UnidentifiedImageError, OSError):
        return jsonify(error="That file could not be read as an image."), 400
    except (json.JSONDecodeError, ValueError) as error:
        app.logger.info("Receipt response could not be parsed: %s", error)
        return jsonify(error="We couldn't read grocery items from that receipt. Try a clearer image."), 422
    except Exception:
        app.logger.exception("Receipt processing failed")
        return jsonify(error="Receipt scanning failed. Check the API configuration and try again."), 502


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(_error):
    return jsonify(error="The image must be 8 MB or smaller."), 413


init_db()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").casefold() == "true")
