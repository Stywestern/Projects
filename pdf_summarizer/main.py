# ==========================================
# 1. IMPORTS
# ==========================================

# Third-Party Libraries
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Local Modules
from app.routes import upload  # This contains the PDF processing logic

# ==========================================
# 2. APP INITIALIZATION
# ==========================================
app = FastAPI(
    title="PDF Summarizer",
    description="A backend API that processes PDFs and streams summaries back to the client.",
    version="1.0.0"
)

# ==========================================
# 3. SECURITY & MIDDLEWARE (CORS)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 4. API ROUTES
# ==========================================
# This connects "http://localhost:8000/upload" to the logic in upload.py.

app.include_router(upload.router)

# ==========================================
# 5. FRONTEND SERVING
# ==========================================
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")