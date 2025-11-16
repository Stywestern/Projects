## Backend Imports
from fastapi import FastAPI
from app.routes import upload

## Frontend Imports
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

## Main app
app = FastAPI()

# Allow frontend JS to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

## Routes
app.include_router(upload.router)


## Frontend Send
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")