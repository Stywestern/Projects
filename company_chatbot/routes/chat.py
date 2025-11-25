# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import logging

# Local Modules
from src import rag

# Logger setup to print info to console
logger = logging.getLogger("uvicorn.error")

# ==========================================
# 2. ROUTER SETUP
# ==========================================
router = APIRouter()

# ==========================================
# 3. INPUT SETUP
# ==========================================
class ChatRequest(BaseModel):
    question: str

# ==========================================
# 4. THE ENDPOINT
# ==========================================
@router.post("/ask")
async def ask_question(request: ChatRequest):
    """
    Receives a question, searches the knowledge base, and returns an answer.
    """
    try:
        # Extract question from the Pydantic model
        user_query = request.question

        # Call the RAG logic
        answer_text = rag.query_rag(user_query)
        
        # Return standardized JSON
        return {
            "question": user_query,
            "answer": answer_text
        }

    except Exception as e:
        # Log the error to the terminal for debugging
        logger.error(f"Error processing request: {e}")
        
        # Return a 500 error to the frontend
        raise HTTPException(status_code=500, detail=str(e))