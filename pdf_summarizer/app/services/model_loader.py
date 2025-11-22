import torch
from transformers import (
    T5Tokenizer, T5ForConditionalGeneration,
    BartTokenizer, BartForConditionalGeneration,
    AutoTokenizer, AutoModelForCausalLM
)

_loaded = {}

def get_model_and_tokenizer(name: str):
    if name in _loaded:
        return _loaded[name]

    if name == "t5-small":
        tok = T5Tokenizer.from_pretrained("t5-small")
        mdl = T5ForConditionalGeneration.from_pretrained("t5-small")

    elif name == "bart-large-cnn":
        tok = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
        mdl = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")

    elif name == "mistral":
        try:
            from ctransformers import AutoModelForCausalLM
        except ImportError:
            raise ImportError("ctransformers is required for GGUF Mistral. Install via `pip install ctransformers`")

        model_path = "mistral-7b-v0.1.Q4_K_M.gguf"  # local GGUF file

        # GGUF Mistral model
        mdl = AutoModelForCausalLM.from_pretrained(
            model_path,
            model_type="mistral",
            gpu_layers=50,  # adjust based on VRAM
            context_length=4096
        )

        tok = None  # handled internally by ctransformers

    elif name == "api":
        tok, mdl = None, None   # Handled separately
    else:
        raise ValueError(f"Unknown model: {name}")

    _loaded[name] = (tok, mdl)
    return tok, mdl

