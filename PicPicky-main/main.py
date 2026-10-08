from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import cloudinary
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
from database import db
from routes.auth import router as auth_router
from routes.upload import router as upload_router
from routes.admin import router as admin_router  # ← NEW

app = FastAPI(
    title="Image Quality Assessment API",
    description="API for assessing image quality and photographer profiling",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(admin_router)  # ← NEW

@app.get("/")
def home():
    return {"message": "Image Quality Assessment API is running!"}