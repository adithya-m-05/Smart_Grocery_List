# 🧾 Smart Grocery List Generator from Receipt Scans

An AI-powered web application that helps users manage their grocery lists by automatically extracting items and prices from receipt images.

## ✨ Features

- **AI-Powered Extraction**: Upload a photo of a receipt, and the app uses Google's Gemini AI (`gemini-1.5-flash`) to accurately extract grocery items and their prices, intelligently ignoring taxes and totals.
- **Persistent Storage**: Automatically logs all extracted items, prices, and timestamps into a SQLite database (`grocery.db`) and an Excel spreadsheet (`receipts.xlsx`) for easy expense tracking and record-keeping.
- **Smart Recommendations**: Suggests related grocery items you might need based on your purchases (e.g., if you bought milk, it recommends cereal or cookies).
- **Clean User Interface**: A simple and intuitive web interface for uploading receipts and viewing results.

## 🛠️ Technology Stack

- **Backend**: Python, Flask
- **AI Engine**: Google Generative AI (Gemini 1.5 Flash)
- **Database**: SQLite
- **Data Export**: pandas, openpyxl (Excel integration)
- **Image Processing**: Pillow (PIL)
- **Frontend**: HTML, CSS, JavaScript

## 🚀 Setup & Installation

1. **Clone the repository** or navigate to the project directory.
2. **Install required dependencies**:
   ```bash
   pip install Flask pandas openpyxl Pillow google-generativeai
   ```
3. **Configure API Key**:
   The app requires a Google Gemini API key to function. The key is currently set in `app.py`. *(Note: For production, it is highly recommended to store this key in a `.env` file instead of hardcoding it).*
4. **Run the Application**:
   ```bash
   python app.py
   ```
5. Open your web browser and navigate to `http://127.0.0.1:5000`.

## 📁 Project Structure

- `app.py`: The main Flask application containing routing logic, Gemini AI integration, and database operations.
- `grocery.db`: The SQLite database that stores your extracted grocery data. *(Auto-generated upon running)*
- `receipts.xlsx`: An Excel file acting as a secondary data log. *(Auto-generated upon running)*
- `templates/`: Contains HTML templates for the web interface.
- `static/`: Contains static assets like CSS styles and JavaScript files.
- `uploads/`: A temporary directory for storing uploaded receipt images before they are processed by the AI.

## 💡 How it Works

1. **Upload**: The user uploads an image of a grocery receipt via the web interface.
2. **Process**: The backend saves the image temporarily and sends it to the Gemini AI model with a specific prompt to extract just the purchased items and their prices.
3. **Store**: The extracted data is formatted and saved to both the SQLite database and appended to the Excel file.
4. **Recommend**: The app cross-references the extracted items against a predefined recommendation map to generate smart suggestions.
5. **Display**: The parsed list and recommendations are sent back and displayed neatly on the frontend.
