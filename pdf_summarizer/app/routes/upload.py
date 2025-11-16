from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from app.services.summarizer import summarize_text

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), model_choice: str = Form(...)):
    content = await file.read()
    
    # Send it to main logic
    async def event_stream():
        async for msg in summarize_text(content, model_choice):
            yield msg + "\n"

    return StreamingResponse(event_stream(), media_type="text/plain")