"""
import os
import google.generativeai as genai
print(os.environ.get("GOOGLE_NLP_API_KEY"))

GOOGLE_NLP_API_KEY = os.getenv("GOOGLE_NLP_API_KEY")
genai.configure(api_key=GOOGLE_NLP_API_KEY)

for m in genai.list_models():
    print(m.name)
    
python -m venv .pdf_summarizer
C:\AA_Desktop\VsCode\projects_repo\pdf_summarizer\.pdf_summarizer\Scripts\activate.bat

pip install -r "C:\AA_Desktop\VsCode\projects_repo\pdf_summarizer\requirements.txt" --no-cache-dir

pip install ctransformers

"""

print("hey")