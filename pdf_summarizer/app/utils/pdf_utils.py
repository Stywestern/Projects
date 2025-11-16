from pypdf import PdfReader

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract all text from a PDF file.
    Returns a single string containing the text.
    """
    
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:  # Some pages may be empty
            text += page_text + "\n"
    return text


