# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Local Modules
from routes import chat  # This contains the Chatbot logic

# ==========================================
# 2. APP INITIALIZATION
# ==========================================
app = FastAPI(
    title="Company Wiki Chatbot",
    description="A backend API that answers questions based on company documents.",
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
app.include_router(chat.router, prefix="/api")

# ==========================================
# 5. FRONTEND SERVING
# ==========================================
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")