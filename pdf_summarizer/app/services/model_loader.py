# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
from transformers import (
    T5Tokenizer, T5ForConditionalGeneration,
    BartTokenizer, BartForConditionalGeneration,
)
import logging

# Logger setup to print info to console
logger = logging.getLogger("uvicorn.error")

# ==========================================
# 2. THE CACHE (MEMORY OPTIMIZATION)
# ==========================================
_loaded = {}

def get_model_and_tokenizer(name: str):
    """
    Factory function to load LLMs.
    Implements 'Memoization' to load models only once per runtime.
    """
    
    # A. CHECK CACHE
    if name in _loaded:
        return _loaded[name]

    # ==========================================
    # MODEL A: T5 (Small & Fast)
    # ==========================================
    if name == "t5-small":
        tok = T5Tokenizer.from_pretrained("t5-small")
        mdl = T5ForConditionalGeneration.from_pretrained("t5-small")

    # ==========================================
    # MODEL B: BART (High Quality / Heavy)
    # ==========================================
    elif name == "bart-large-cnn":
        # Uses the 'facebook/bart-large-cnn' weights specifically tuned for summarization
        tok = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
        mdl = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

    # ==========================================
    # MODEL C: MISTRAL (Local Quantized LLM)
    # ==========================================
    elif name == "mistral":
        # Validation: Need a special library 'ctransformers' to run GGUF files.
        try:
            from ctransformers import AutoModelForCausalLM
        except ImportError:
            raise ImportError("ctransformers is required for GGUF Mistral. Install via `pip install ctransformers`")

        # CRITICAL WARNING: This expects a file named "mistral-7b...gguf" in the working directory or in the docker image
        model_path = "mistral-7b-v0.1.Q4_K_M.gguf"

        # Loading the GGUF model (Quantized for efficiency)
        mdl = AutoModelForCausalLM.from_pretrained(
            model_path,
            model_type="mistral",
            gpu_layers=50,      # Offloads layers to Nvidia GPU. Set to 0 if CPU only.
            context_length=4096
        )

        # ctransformers handles tokenization internally within the model object
        tok = None 

    # ==========================================
    # MODEL D: EXTERNAL API
    # ==========================================
    elif name == "api":
        # No local model or tokenizer to load. The Logic layer handles the API call.
        tok, mdl = None, None

    else:
        raise ValueError(f"Unknown model: {name}")

    # UPDATE CACHE
    _loaded[name] = (tok, mdl)
    
    return tok, mdl

