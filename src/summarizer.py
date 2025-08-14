from transformers import pipeline
import fitz  # PyMuPDF

# Load summarizer model
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

def summarize_report(text, max_length=200, min_length=50):
    if not text:
        return "No readable text found in the PDF."
    
    # Limit to 2000 characters for fast summarization
    if len(text) > 2000:
        text = text[:2000]
    
    try:
        output = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        return output[0]['summary_text']
    except Exception as e:
        return f"Error during summarization: {e}"
