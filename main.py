import uvicorn
import os

# Ensure the Tesseract executable path is set if not in PATH
# This is crucial for PyInstaller bundles or non-standard installations.
# Example (uncomment and adjust if needed):
# try:
#     import pytesseract
#     # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
#     # Or for Linux/macOS:
#     # pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
# except ImportError:
#     print("Pytesseract not installed or Tesseract executable not found.")

if __name__ == "__main__":
    # Ensure the database directory exists
    os.makedirs("data", exist_ok=True)
    # You might want to initialize the database here as well
    from database.db import init_db
    init_db()

    print("Starting FastAPI application...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
    # reload=True is good for development, set to False for production/PyInstaller
