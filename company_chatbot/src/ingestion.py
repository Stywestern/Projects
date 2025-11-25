# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
import os
import torch
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Load environment variables
load_dotenv()

# Define flexible paths relative to this script
CURRENT_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(CURRENT_DIR, "../data/handbook.txt")
DB_PATH = os.path.join(CURRENT_DIR, "../vector_db")

# ==========================================
# 2. MAIN PROCESS
# ==========================================

def ingest_docs():
    # ---------------------------------------------------------
    # Step 1: Hardware Check
    # ---------------------------------------------------------
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Starting ingestion logic...")
    print(f"Compute Device: {device.upper()} (Targeting your RTX 4070)" if device == "cuda" else "Compute Device: CPU")

    # ---------------------------------------------------------
    # Step 2: Load Data
    # ---------------------------------------------------------
    if not os.path.exists(DATA_PATH):
        print(f"Error: File not found at {DATA_PATH}")
        return
    
    loader = TextLoader(DATA_PATH, encoding="utf-8")
    documents = loader.load()
    print(f"Loaded {len(documents)} document(s) from 'data/handbook.txt'.")

    # ---------------------------------------------------------
    # Step 3: Chunking
    # ---------------------------------------------------------
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"Split document into {len(chunks)} chunks.")

    # ---------------------------------------------------------
    # Step 4: Embed & Store
    # ---------------------------------------------------------
    print(f"Generating embeddings and saving to ChromaDB...")
    
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': device} 
    )
    
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=DB_PATH
    )
    
    print(f"Ingestion complete! Database created in: {DB_PATH}")

if __name__ == "__main__":
    ingest_docs()