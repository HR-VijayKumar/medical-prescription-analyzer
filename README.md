# Medical Prescription Analyzer

A web-based application to analyze medical prescriptions.  
It extracts medicines from handwritten prescriptions, fetches detailed information, and generates a structured PDF report for easy reference.

## Features

- 📸 Upload prescription images
- 🔍 Extract medicine names using AI-powered OCR and text parsing
- 💊 Fetch detailed medicine information (uses automated web scraping & APIs)
- 📄 Generate clean, structured PDF reports
- 🌐 Deployable as a Hugging Face Space (Docker-powered)

## Demo

🚀 **Try the app live:** [Medical Prescription Analyzer on Hugging Face Spaces](https://huggingface.co/spaces/vijaykumar1372/Medical_prescription_analyser)

> ⚠️ **Note:** Web scraping features (🔍 medicine information fetching) may not work properly on Hugging Face Spaces due to browser limitations in the Docker environment.  
> 🖥️ For full functionality, especially web scraping, please run the app locally if needed.

## Tech Stack

- **Web Framework:** Gradio  
- **OCR / Text Extraction:** Google Gemini API
- **Medicine Info Scraping:** Playwright (headless browser)  
- **PDF Report Generation:** Custom Python script (pdf_generator.py)  
- **Deployment:** Hugging Face Spaces (Docker)

## Project Structure

```
├── app.py                      # Main Gradio app
├── pdf_generator.py            # Custom PDF generation script
├── prescription_data.py        # Text extraction logic
├── medicine_info.py            # Medicine scraping & info fetch
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker config for Hugging Face Space
└── README.md                   # Project documentation
```

## Installation (Local)

```
git clone https://github.com/your-username/medical-prescription-analyzer.git
cd medical-prescription-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app locally
python app.py
```


```
## Usage

1. Upload a clear photo or scanned image of your medical prescription.
2. The app will:
   - Extract text and detect medicine names
   - Search for detailed medicine information
   - Display a summary and download link for the PDF report
3. Download the PDF report for personal use or consultation.

## Disclaimer

This tool is intended for informational purposes only and is not a substitute for professional medical advice. Always consult a healthcare provider for prescriptions and medication guidance.

## Contributing

Contributions are welcome!  
Please open issues or submit pull requests for feature suggestions, bug fixes, or improvements.

## License

MIT License — see LICENSE file for details.
