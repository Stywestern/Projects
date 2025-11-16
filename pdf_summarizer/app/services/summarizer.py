from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch
import fitz  # PyMuPDF
import io, asyncio
import google.generativeai as genai

from app.utils.text_utils import chunk_text
from app.config import DEVICE, CHUNK_TOKENS, CHUNK_OVERLAP, SUMMARY_MAX_LENGTH, SUMMARY_MIN_LENGTH, GOOGLE_NLP_API_KEY

## Mount the processor
device = torch.device(DEVICE)

## Set the model and tokenizer of the NLP system
_loaded_models = {}

def get_model_and_tokenizer(model_choice: str):
    global _loaded_models
    if model_choice not in _loaded_models:
        model_name = {
            "t5-small": "t5-small",
            "t5-base": "t5-base",
            "api": None,  # handled separately
        }.get(model_choice, "t5-small")

        if model_name:
            tokenizer = T5Tokenizer.from_pretrained(model_name)
            model = T5ForConditionalGeneration.from_pretrained(model_name)
            _loaded_models[model_choice] = (tokenizer, model)
        else:
            _loaded_models[model_choice] = (None, None)
    return _loaded_models[model_choice]


async def summarize_text(file_bytes: bytes, model_choice: str = "t5-small"):
    ## Get the whole text
    pdf = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in pdf:
        text += page.get_text()

    if not text.strip():
        yield "SUMMARY:No readable text found in the PDF."
        return

    ## Set the NLP part
    tokenizer, model = get_model_and_tokenizer(model_choice)
    chunks = chunk_text(text, max_tokens=CHUNK_TOKENS, overlap_tokens=CHUNK_OVERLAP)
    total = len(chunks)
    summaries = []

    ## Start summary
    if model_choice == "api":
        # External API summarization (Gemini)
        genai.configure(api_key=GOOGLE_NLP_API_KEY)

        model = genai.GenerativeModel("gemini-2.5-flash")

        for i, chunk in enumerate(chunks):
            prompt = f"Summarize the following text:\n{chunk}"
            response = await asyncio.to_thread(model.generate_content, prompt)

            if hasattr(response, "text"):
                summary = response.text.strip()
            else:
                summary = "(Error: No text returned from API.)"

            summaries.append(summary)
            yield f"PROGRESS:{i+1}/{total}"
            await asyncio.sleep(0.1)

    else:
        # Local T5 summarization
        tokenizer, model = get_model_and_tokenizer(model_choice)
        model.to(DEVICE)

        for i, chunk in enumerate(chunks):
            input_text = "summarize: " + chunk
            inputs = tokenizer.encode(
                input_text, return_tensors="pt", max_length=512, truncation=True
            ).to(DEVICE)

            summary_ids = model.generate(
                inputs,
                max_length=SUMMARY_MAX_LENGTH,
                min_length=SUMMARY_MIN_LENGTH,
                num_beams=4,
                early_stopping=True
            )

            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            summaries.append(summary)

            yield f"PROGRESS:{i+1}/{total}"
            await asyncio.sleep(0.1)

    final_text = " ".join(summaries)
    yield f"SUMMARY:{final_text}"