# ==========================================
# 1. IMPORTS & Setup
# ==========================================

# Third-Party Libraries
import fitz  # PyMuPDF: The fastest library for reading PDFs
import asyncio
import logging

# Local Logic
from app.utils.text_utils import chunk_text
from app.services.model_loader import get_model_and_tokenizer
from app.config import CHUNK_PROFILES

from app.services.summarizers import (
    summarize_t5, finalize_t5,
    summarize_bart, finalize_bart,
    summarize_mistral, finalize_mistral,
    summarize_api, finalize_api
)

# Logger setup
logger = logging.getLogger("uvicorn.error")


# ==========================================
# 2. MAIN PROCESS
# ==========================================
async def summarize_text(file_bytes, model_choice):
    """
    The Main Workflow:
    PDF -> Raw Text -> Chunks -> Partial Summaries -> Final Summary
    """
    
    # ==========================================
    # A. EXTRACTION (PDF -> Text)
    # ==========================================
    # Use 'fitz' (PyMuPDF) because it is much faster than PyPDF2, 'stream=file_bytes' tells it to read from RAM, not look for a file on disk.
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    text = "".join([p.get_text() for p in doc])

    if not text.strip():
        # Edge Case: Scanned PDFs (images) have no text layer.
        yield "SUMMARY:No readable text found. This might be a scanned image PDF."
        return

    # ==========================================
    # B. PREPARATION (Text -> Chunks)
    # ==========================================
    profile = CHUNK_PROFILES.get(model_choice)

    tokenizer, model = get_model_and_tokenizer(model_choice)

    chunks = chunk_text(
        text,
        tokenizer=tokenizer,
        max_tokens=profile["max_tokens"],
        overlap_tokens=profile["overlap"]
    )

    for idx, chunk in enumerate(chunks):
        logger.info(f"Chunk {idx+1} for {model_choice} (Length: {len(chunk)} chars)")

    total = len(chunks)

    # ==========================================
    # C. SELECTION 
    # ==========================================

    if model_choice == "t5-small":
        summarizer = summarize_t5(tokenizer, model, chunks)
    elif model_choice == "bart-large-cnn":
        summarizer = summarize_bart(tokenizer, model, chunks)
    elif model_choice == "mistral":
        summarizer = summarize_mistral(model, chunks)
    elif model_choice == "api":
        summarizer = summarize_api(chunks)
    else:
        yield "SUMMARY:Invalid model choice."
        return

    # ==========================================
    # D. COLLECTION
    # ==========================================
    summaries = []
    
    async for idx, summary in summarizer:
        summaries.append(summary)
        
        # PROTOCOL: Send progress update to Frontend
        # Frontend sees: "PROGRESS:1/max" -> Updates bar 
        yield f"PROGRESS:{idx}/{total}"

    # ==========================================
    # E. FINALIZATION 
    # ==========================================
    combined_summaries = "\n\n".join(summaries)
    
    final_summary = ""
    
    try:
        if model_choice == "t5-small":
            final_summary = await finalize_t5(tokenizer, model, combined_summaries)
        elif model_choice == "bart-large-cnn":
            final_summary = await finalize_bart(tokenizer, model, combined_summaries)
        elif model_choice == "mistral":
            final_summary = await finalize_mistral(model, combined_summaries)
        elif model_choice == "api":
            final_summary = await finalize_api(combined_summaries)
        else:
            final_summary = " ".join(summaries) 

        # ==========================================
        # F. TRANSPORT FORMATTING
        # ==========================================
        # CRITICAL: The streaming protocol relies on "\n" to separate messages, escape real newlines ("\n" -> "\\n").
        safe_summary = final_summary.replace("\n", "\\n") 
        
        yield "SUMMARY:" + safe_summary
    
    except Exception as e:
        logger.error(f"Finalization failed: {e}")
        yield f"ERROR:Could not generate final summary. Error: {e}"