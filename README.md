# Goodbasket

Goodbasket turns grocery receipt photos into a clean list of purchased items and prices. It saves a shopping history, exports that history to Excel, and suggests a few related groceries based on what was scanned.

## How it works

1. Select or drop a JPEG, PNG, or WebP receipt image (up to 8 MB).
2. The Flask backend validates the image and sends it to Gemini for item and price extraction.
3. Extracted items are saved to SQLite and appended to `receipts.xlsx`.
4. The page displays the latest scan, a receipt total, relevant suggestions, and the last 100 saved items.

Receipt images are processed in memory and are not saved by the current upload flow. SQLite is the primary store; the Excel workbook is a convenient export.

## Setup

1. Install Python 3.10 or newer.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` in the project root and add your Gemini API key:

   ```env
   GEMINI_API_KEY=your_gemini_api_key
   ```

   The key is read from the environment and must not be committed to source control. You can optionally set `GEMINI_MODEL`, `DATABASE_PATH`, `EXCEL_PATH`, or `FLASK_DEBUG` in the same file. If you used an earlier version of this project, replace the Gemini key that was previously embedded in `app.py`.

4. Start the app:

   ```bash
   python app.py
   ```

5. Open <http://127.0.0.1:5000>.

Without `GEMINI_API_KEY`, the page and saved history remain available, but receipt scanning returns a configuration error.

## Project structure

```text
app.py                 Flask routes, Gemini extraction, recommendations, and storage
frontend/              All frontend files in one folder
  index.html           Page template
  styles.css           Responsive UI styles
  script.js            Upload flow and page interactions
grocery.db             SQLite purchase history (created automatically)
receipts.xlsx          Spreadsheet export (created after the first successful scan)
requirements.txt       Python dependencies
```

The frontend is served by Flask from the single `frontend/` directory. Uploaded receipt images are limited to JPEG, PNG, and WebP and are not retained after processing.
