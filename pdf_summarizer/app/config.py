import torch
import os

MODEL_NAME = "t5-small"
CHUNK_TOKENS = 450
CHUNK_OVERLAP = 50
SUMMARY_MAX_LENGTH = 200
SUMMARY_MIN_LENGTH = 50
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

UPLOAD_DIR = "uploads"

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_NLP_API_KEY = os.getenv("GOOGLE_NLP_API_KEY")
