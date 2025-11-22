import asyncio
import google.generativeai as genai

from app.config import (
    DEVICE, SUMMARY_MAX_LENGTH, SUMMARY_MIN_LENGTH, GOOGLE_NLP_API_KEY
)

import logging

# Get the logger that uvicorn uses
logger = logging.getLogger("uvicorn.error")


# ----------------------------------
# T5 Summarizer
# ----------------------------------
async def summarize_t5(tokenizer, model, chunks):
    model.to(DEVICE)

    for idx, chunk in enumerate(chunks):
        text = "summarize: " + chunk
        inputs = tokenizer.encode(
            text, return_tensors="pt", max_length=512, truncation=True
        ).to(DEVICE)

        ids = model.generate(
            inputs,
            max_length=SUMMARY_MAX_LENGTH,
            min_length=SUMMARY_MIN_LENGTH,
            num_beams=4,
            early_stopping=True
        )

        summary = tokenizer.decode(ids[0], skip_special_tokens=True)
        yield idx + 1, summary

        await asyncio.sleep(0.05)


# ----------------------------------
# BART Summarizer
# ----------------------------------
async def summarize_bart(tokenizer, model, chunks):
    model.to(DEVICE)

    for idx, chunk in enumerate(chunks):
        inputs = tokenizer(
            chunk, return_tensors="pt",
            max_length=1024, truncation=True
        ).to(DEVICE)

        ids = model.generate(
            inputs["input_ids"],
            max_length=SUMMARY_MAX_LENGTH,
            min_length=SUMMARY_MIN_LENGTH,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True
        )

        summary = tokenizer.decode(ids[0], skip_special_tokens=True)
        yield idx + 1, summary

        await asyncio.sleep(0.05)


# ----------------------------------
# Mistral LLM Summarizer
# ----------------------------------
async def summarize_mistral(model, chunks):
    """
    It processes one chunk at a time and yields the result,
    which plugs directly into the 'async for' loop in 'summarize_text'.
    """
    total_chunks = len(chunks)

    # --- DYNAMIC DENSITY CALCULATION ---
    # We want the final combined text to stay under ~3000 tokens to be safe.
    # So we calculate how much space we have for each chunk.
    
    # Dynamic token allocation
    safe_final_context = 3500
    dynamic_max_tokens = max(100, min(350, safe_final_context // total_chunks))

    for idx, chunk in enumerate(chunks):
        logger.info(f"  > Processing Mistral chunk {idx + 1}/{total_chunks}")
        
        clean_chunk = chunk.replace("\n", " ").strip()
        if len(clean_chunk) < 30:
             continue

        # --- UNIVERSAL PROMPT: INFORMATION COMPRESSION ---
        prompt = (
            f"[INST] Analyze the text below and extract the key information. "
            f"Focus on capturing main ideas, specific names, dates, numbers, and core arguments. "
            f"Output a concise list of bullet points. "
            f"Do NOT write a narrative. Do NOT add outside info.\n\n"
            f"Text: {clean_chunk} [/INST]\n"
            f"Key Points:"
        )

        summary_raw = await asyncio.to_thread(
            model,
            prompt,
            max_new_tokens=dynamic_max_tokens,
            temperature=0.1,       
            repetition_penalty=1.15 
        )

        # Clean output
        summary = summary_raw.replace("[/INST]", "").replace("Key Points:", "").strip()
        
        if not summary:
            summary = clean_chunk # failsafe for blank summaries
        
        logger.info(f"  > Summary of chunk {idx+1}:\n{summary}")
        yield idx + 1, summary
        await asyncio.sleep(0.05)

# ----------------------------------
# GEMINI API Summarizer
# ----------------------------------
async def summarize_api(chunks):
    genai.configure(api_key=GOOGLE_NLP_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    for idx, chunk in enumerate(chunks):
        prompt = f"Summarize:\n{chunk}"
        response = await asyncio.to_thread(model.generate_content, prompt)

        summary = getattr(response, "text", "").strip() or "(Empty response)"
        yield idx + 1, summary

        await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------------

# ----------------------------------
# T5 Finalizer ("Reduce" Step)
# ----------------------------------
async def finalize_t5(tokenizer, model, combined_summaries: str) -> str:
    """
    Takes the combined partial summaries and runs the T5 model
    one last time to create a single, cohesive summary.
    """
    logger.info("  > Starting T5 final 'Reduce' step...")
    model.to(DEVICE)
    
    text = "summarize: " + combined_summaries
    
    # 1. Encode
    # Truncate to 512, as this is the max T5 can handle
    inputs = tokenizer.encode(
        text, return_tensors="pt", max_length=512, truncation=True
    ).to(DEVICE)

    # 2. Generate (wrapped in to_thread)
    # This is a BLOCKING call, so it MUST run in a thread
    ids = await asyncio.to_thread(
        model.generate,
        inputs,
        max_length=SUMMARY_MAX_LENGTH,
        min_length=SUMMARY_MIN_LENGTH,
        num_beams=4,
        early_stopping=True
    )

    # 3. Decode
    final_summary = tokenizer.decode(ids[0], skip_special_tokens=True)
    logger.info("  > T5 'Reduce' step complete.")
    return final_summary


# ----------------------------------
# BART Finalizer ("Reduce" Step)
# ----------------------------------
async def finalize_bart(tokenizer, model, combined_summaries: str) -> str:
    """
    Takes the combined partial summaries and runs the BART model
    one last time to create a single, cohesive summary.
    """
    logger.info("  > Starting BART final 'Reduce' step...")
    model.to(DEVICE)

    # 1. Encode
    # Truncate to 1024, as this is the max BART can handle
    inputs = tokenizer(
        combined_summaries, return_tensors="pt",
        max_length=1024, truncation=True
    ).to(DEVICE)

    # 2. Generate (wrapped in to_thread)
    # This is a BLOCKING call, so it MUST run in a thread
    ids = await asyncio.to_thread(
        model.generate,
        inputs["input_ids"],
        max_length=SUMMARY_MAX_LENGTH,
        min_length=SUMMARY_MIN_LENGTH,
        num_beams=4,
        length_penalty=2.0,
        early_stopping=True
    )

    # 3. Decode
    final_summary = tokenizer.decode(ids[0], skip_special_tokens=True)
    logger.info("  > BART 'Reduce' step complete.")
    return final_summary


# ----------------------------------
# Mistral LLM Finalizer ("Reduce" Step)
# ----------------------------------
async def finalize_mistral(model, combined_summaries: str) -> str:
    """
    Takes the combined partial summaries and runs the Mistral model
    one last time to create a single, cohesive summary.
    """
    logger.info("  > Starting Mistral final 'Reduce' step...")

    # 1. Sanitize the combined text 
    clean_combined = combined_summaries.replace("[INST]", "").replace("[/INST]", "")

    logger.info(f"  > Combined summaries:\n{clean_combined}")

    # 2. SIMPLE PROMPT
    final_prompt = (
        f"[INST] You are a professional editor. "
        f"Synthesize the notes below into a single, coherent summary. "
        f"The output should be a concise narrative (approx. 8-20 lines). "
        f"Do NOT use bullet points. Do NOT use section headers. "
        f"Write clear, continuous text.\n\n"
        f"--- NOTES ---\n{clean_combined}\n--- END NOTES ---\n"
        f"[/INST]\n"
        f"Summary:" # Trigger word
    )

    # 3. GENERATE
    final_summary_raw = await asyncio.to_thread(
        model,
        final_prompt,
        max_new_tokens=800,
        temperature=0.1,        # Keep it factual
        repetition_penalty=1.15 
    )

    # 4. ROBUST CLEANUP
    # A. Isolate the content after the trigger word
    if "Summary:" in final_summary_raw:
        result = final_summary_raw.split("Summary:")[-1]
    else:
        # Fallback: split by the end of the instruction tag
        result = final_summary_raw.split("[/INST]")[-1]

    # B. Cut off any hallucinated new instructions at the end
    if "[INST]" in result:
        result = result.split("[INST]")[0]

    # C. Final trim
    result = result.strip()
    
    # D. Fail-safe for empty results
    if not result:
        return "Could not generate summary."
    logger.info(f"  > Result :\n{result}")

    return result

# ----------------------------------
# GEMINI API Finalizer ("Reduce" Step)
# ----------------------------------
async def finalize_api(combined_summaries: str) -> str:
    """
    Takes the combined partial summaries and runs the Gemini API
    one last time to create a single, cohesive summary.
    """
    logger.info("  > Starting Gemini API final 'Reduce' step...")
    genai.configure(api_key=GOOGLE_NLP_API_KEY)
    
    # Initialize the model just for this call
    # Note: For efficiency, you could initialize this once and pass it in
    model = genai.GenerativeModel("gemini-pro") # Using 'pro' for better quality reduce

    # Use a prompt designed for "reducing" summaries
    final_prompt = (
        "You are an expert editor. The following text consists of several partial summaries "
        "of a longer document. Your task is to synthesize them into a single, clear, "
        "and cohesive summary. Do not add any introduction or conclusion, just "
        "provide the final summary.\n\n"
        f"### Partial Summaries:\n{combined_summaries}"
    )

    try:
        # Run the blocking SDK call in a separate thread
        response = await asyncio.to_thread(model.generate_content, final_prompt)
        final_summary = getattr(response, "text", "").strip() or "(Empty response)"
    except Exception as e:
        logger.error(f"Gemini API finalizer error: {e}")
        final_summary = f"(Error: {e})"

    logger.info("  > Gemini API 'Reduce' step complete.")
    return final_summary