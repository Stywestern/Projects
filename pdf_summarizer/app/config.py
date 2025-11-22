import torch
import os

CHUNK_PROFILES = {
    "t5-small":      {"max_tokens": 350, "overlap": 50},
    "bart-large-cnn": {"max_tokens": 800, "overlap": 100},
    "mistral": {"max_tokens": 256, "overlap": 32},
    "api":           {"max_tokens": 2000, "overlap": 0},  # API can handle large chunks
}

SUMMARY_MAX_LENGTH = 300
SUMMARY_MIN_LENGTH = 100
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

UPLOAD_DIR = "uploads"

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_NLP_API_KEY = os.getenv("GOOGLE_NLP_API_KEY")
