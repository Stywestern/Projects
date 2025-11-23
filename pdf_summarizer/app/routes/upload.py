# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import logging

# Local Logic
from app.services.summarizer import summarize_text

# Logger setup to print info to console
logger = logging.getLogger("uvicorn.error")

# ==========================================
# 2. ROUTER SETUP
# ==========================================
router = APIRouter()

# ==========================================
# 3. THE ENDPOINT
# ==========================================
@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), model_choice: str = Form(...)):
    """
    Receives the PDF and model selection, reads the file into memory,
    and opens a streaming connection back to the client.
    """

    # A. READ THE FILE
    content = await file.read()
    
    # B. DEFINE THE STREAM GENERATOR
    async def event_stream():
        async for msg in summarize_text(content, model_choice):
            # CRITICAL: Append "\n" because Frontend looks for newlines to split the stream into messages. Without this, the frontend 
            # buffer would just keep filling up and never process anything.
            yield msg + "\n"

    # C. RETURN THE STREAM
    return StreamingResponse(event_stream(), media_type="text/plain")