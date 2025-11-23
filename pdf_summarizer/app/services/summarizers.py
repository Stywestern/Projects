# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
import asyncio
import logging
import google.generativeai as genai
from app.config import (
    DEVICE, SUMMARY_MAX_LENGTH, SUMMARY_MIN_LENGTH, GOOGLE_NLP_API_KEY
)

# Logger setup to print info to console
logger = logging.getLogger("uvicorn.error")

# ==============================================================================
# STRATEGY 1: T5 (The "Classic" Encoder-Decoder)
# Best for: Fast, short summaries. strict input limits (512 tokens).
# ==============================================================================

async def summarize_t5(tokenizer, model, chunks):
    """
    MAP STEP: Process each chunk independently.
    """
    model.to(DEVICE)

    for idx, chunk in enumerate(chunks):
        logger.info("  > Starting T5 map step...")

        # 1. Encode
        # T5 was trained with the specific prefix "summarize: "
        text = "summarize: " + chunk

        inputs = tokenizer.encode(
            text, return_tensors="pt", max_length=512, truncation=True
        ).to(DEVICE)

        # 2. Generate
        ids = model.generate(
            inputs,
            max_length=SUMMARY_MAX_LENGTH,
            min_length=SUMMARY_MIN_LENGTH,
            num_beams=4,        # Looks at 4 possible futures at once (better quality)
            early_stopping=True
        )

        # 3. Decode
        summary = tokenizer.decode(ids[0], skip_special_tokens=True)
        
        # Yield result so frontend can update progress bar
        yield idx + 1, summary
        await asyncio.to_thread(asyncio.sleep, 0.05)


async def finalize_t5(tokenizer, model, combined_summaries: str) -> str:
    """
    REDUCE STEP: Combine mini-summaries into one.
    """
    logger.info("  > Starting T5 final 'Reduce' step...")
    model.to(DEVICE)
    
    text = "summarize: " + combined_summaries
    
    # 1. Encode
    inputs = tokenizer.encode(
        text, return_tensors="pt", max_length=512, truncation=True
    ).to(DEVICE)

    # 2. Generate
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
    return final_summary


# ==============================================================================
# STRATEGY 2: BART 
# Best for: High quality, abstractive summarization. Handles 1024 tokens.
# ==============================================================================

async def summarize_bart(tokenizer, model, chunks):
    """ MAP STEP """
    logger.info("  > Starting BART map step...")
    model.to(DEVICE)

    for idx, chunk in enumerate(chunks):
        logger.info(f"  > BART chunk {idx+0}/{len(chunks)}")
        
        inputs = tokenizer(
            chunk, return_tensors="pt",
            max_length=1024, truncation=True
        ).to(DEVICE)

        ids = model.generate(
            inputs["input_ids"],
            max_length=SUMMARY_MAX_LENGTH,
            min_length=SUMMARY_MIN_LENGTH,
            num_beams=4,
            length_penalty=2.0, # Encourages slightly longer, more detailed outputs
            early_stopping=True
        )

        summary = tokenizer.decode(ids[0], skip_special_tokens=True)
        yield idx + 1, summary
        await asyncio.sleep(0.05)


async def finalize_bart(tokenizer, model, combined_summaries: str) -> str:
    """ REDUCE STEP """
    logger.info("  > Starting BART final 'Reduce' step...")
    model.to(DEVICE)

    inputs = tokenizer(
        combined_summaries, return_tensors="pt",
        max_length=1024, truncation=True
    ).to(DEVICE)

    ids = await asyncio.to_thread(
        model.generate,
        inputs["input_ids"],
        max_length=SUMMARY_MAX_LENGTH,
        min_length=SUMMARY_MIN_LENGTH,
        num_beams=4,
        length_penalty=2.0,
        early_stopping=True
    )

    final_summary = tokenizer.decode(ids[0], skip_special_tokens=True)
    return final_summary


# ==============================================================================
# STRATEGY 3: MISTRAL (The Local LLM)
# Best for: Instruction following, works with prompts
# ==============================================================================

async def summarize_mistral(model, chunks):
    """ MAP STEP """
    logger.info(f"  > Starting Mistral map step...")
    total_chunks = len(chunks)
    
    # Dynamic Math: Depending on the chunk size the created summary must be smaller in order to safely reduce the summaries
    safe_final_context = 3500
    dynamic_max_tokens = max(100, min(350, safe_final_context // total_chunks))

    for idx, chunk in enumerate(chunks):
        logger.info(f"  > Processing Mistral chunk {idx + 1}/{total_chunks}")
        
        clean_chunk = chunk.replace("\n", " ").strip()
        if len(clean_chunk) < 30: continue

        prompt = (
            f"[INST] Analyze the text below and extract the key information. "
            f"Focus on capturing main ideas. Output a concise list of bullet points. "
            f"Text: {clean_chunk} [/INST]\nKey Points:"
        )

        summary_raw = await asyncio.to_thread(
            model,
            prompt,
            max_new_tokens=dynamic_max_tokens,
            temperature=0.1,       # Low creativity (strict facts)
            repetition_penalty=1.15 
        )

        # Text Cleanup: Remove the prompt and the instruction tags from the output
        summary = summary_raw.replace("[/INST]", "").replace("Key Points:", "").strip()
        
        if not summary: summary = clean_chunk 
        
        yield idx + 1, summary
        await asyncio.sleep(0.05)


async def finalize_mistral(model, combined_summaries: str) -> str:
    """ REDUCE STEP """
    logger.info("  > Starting Mistral final 'Reduce' step...")

    # Clean previous artifacts
    clean_combined = combined_summaries.replace("[INST]", "").replace("[/INST]", "")

    final_prompt = (
        f"[INST] You are a professional editor. "
        f"Synthesize the notes below into a single, coherent narrative summary. "
        f"--- NOTES ---\n{clean_combined}\n--- END NOTES ---\n"
        f"[/INST]\nSummary:"
    )

    final_summary_raw = await asyncio.to_thread(
        model,
        final_prompt,
        max_new_tokens=800,
        temperature=0.1, 
        repetition_penalty=1.15 
    )

    if "Summary:" in final_summary_raw:
        result = final_summary_raw.split("Summary:")[-1]
    else:
        result = final_summary_raw.split("[/INST]")[-1]

    if "[INST]" in result: # Safety check if model hallucinated a new prompt
        result = result.split("[INST]")[0]

    return result.strip()


# ==============================================================================
# STRATEGY 4: GEMINI API (The Cloud Option)
# Best for: Unlimited power, but requires internet and API Key.
# ==============================================================================

async def summarize_api(chunks):
    """ MAP STEP """
    logger.info(f"  > Starting API map step...")
    genai.configure(api_key=GOOGLE_NLP_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    for idx, chunk in enumerate(chunks):
        prompt = f"Summarize:\n{chunk}"
        response = await asyncio.to_thread(model.generate_content, prompt)
        
        summary = getattr(response, "text", "").strip() or "(Empty response)"
        yield idx + 1, summary
        await asyncio.sleep(0.05)


async def finalize_api(combined_summaries: str) -> str:
    """ REDUCE STEP """
    logger.info("  > Starting Gemini API final 'Reduce' step...")
    genai.configure(api_key=GOOGLE_NLP_API_KEY)
    model = genai.GenerativeModel("gemini-pro") # Stronger model for final synthesis

    final_prompt = (
        "You are an expert editor. Synthesize these partial summaries into one cohesive summary:\n\n"
        f"### Partial Summaries:\n{combined_summaries}"
    )

    try:
        response = await asyncio.to_thread(model.generate_content, final_prompt)
        final_summary = getattr(response, "text", "").strip() or "(Empty response)"
    except Exception as e:
        logger.error(f"Gemini API finalizer error: {e}")
        final_summary = f"(Error: {e})"

    return final_summary