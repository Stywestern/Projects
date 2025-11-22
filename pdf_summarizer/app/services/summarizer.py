import fitz
import asyncio
from app.utils.text_utils import chunk_text
from app.services.model_loader import get_model_and_tokenizer

from app.services.summarizers import (
    summarize_t5,
    summarize_bart,
    summarize_mistral,
    summarize_api
)

from app.services.summarizers import (
    finalize_t5,
    finalize_bart,
    finalize_mistral,
    finalize_api
)

from app.config import (
    DEVICE, CHUNK_PROFILES
)

import logging

# Get the logger that uvicorn uses
logger = logging.getLogger("uvicorn.error")


async def summarize_text(file_bytes, model_choice):
    # Extract text from PDF
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "".join([p.get_text() for p in doc])

    if not text.strip():
        yield "SUMMARY:No readable text found in the PDF."
        return

    # Chunk text
    profile = CHUNK_PROFILES.get(model_choice)

    tokenizer, model = get_model_and_tokenizer(model_choice)

    chunks = chunk_text(
        text,
        tokenizer=tokenizer,
        max_tokens=profile["max_tokens"],
        overlap_tokens=profile["overlap"]
    )

    for idx, chunk in enumerate(chunks):
        logger.info(f"Chunk{idx+1} for {model}: {chunk}")

    total = len(chunks)

    # Pick summarizer function
    if model_choice == "t5-small":
        summarizer = summarize_t5(tokenizer, model, chunks)
    elif model_choice == "bart-large-cnn":
        summarizer = summarize_bart(tokenizer, model, chunks)
    elif model_choice == "api":
        summarizer = summarize_api(chunks)
    elif model_choice == "mistral":
        summarizer = summarize_mistral(model, chunks)
    else:
        yield "SUMMARY:Invalid model choice."
        return

    # Run summarization
    summaries = []
    async for idx, summary in summarizer:
        summaries.append(summary)
        yield f"PROGRESS:{idx}/{total}"

    # Output final
    combined_summaries = "\n\n".join(summaries)
    
    final_summary = ""
    try:
        if model_choice == "t5-small":
            final_summary = await finalize_t5(tokenizer, model, combined_summaries)
        elif model_choice == "bart-large-cnn":
            final_summary = await finalize_bart(tokenizer, model, combined_summaries)
        elif model_choice == "api":
            final_summary = await finalize_api(combined_summaries)
        elif model_choice == "mistral":
            final_summary = await finalize_mistral(model, combined_summaries)
        else:
            final_summary = " ".join(summaries) # Fallback to the old, simple join
        
        # We replace actual newlines with a literal "\n" string (escaped).
        # This keeps the whole summary on one line for the stream transport.
        # Your frontend will need to convert "\n" back to newlines or <br> tags.
        safe_summary = final_summary.replace("\n", "\\n") 
        
        yield "SUMMARY:" + safe_summary
    
    except Exception as e:
        # Send a useful error to the frontend
        yield f"ERROR:Could not generate final summary. The combined text may be too long. Error: {e}"