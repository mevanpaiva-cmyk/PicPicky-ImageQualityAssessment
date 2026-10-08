from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List
import cloudinary
import cloudinary.uploader
from database import db
from datetime import datetime
from routes.auth import verify_token
from services.blur_detection import detect_blur
from services.duplicate_detection import check_duplicate
from services.technical_quality import analyze_technical_quality
from services.clipiqa_scorer import predict_aesthetic_score
from services.explainability import generate_explanation
from services.encryption import encrypt_image, decrypt_image

from PIL import Image
from bson import ObjectId
import requests
import io
import pillow_heif

router = APIRouter()


# ✅ Helper: Convert & Compress any image to JPEG under 10MB
def process_image(contents, filename):
    filename_lower = filename.lower()
    
    try:
        if filename_lower.endswith(('.heic', '.heif')):
            heif_file = pillow_heif.read_heif(io.BytesIO(contents))
            pil_image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride,
            )
        else:
            pil_image = Image.open(io.BytesIO(contents))
        
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        max_dimension = 4096
        if max(pil_image.size) > max_dimension:
            pil_image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
        
        quality = 90
        while quality >= 30:
            output_buffer = io.BytesIO()
            pil_image.save(output_buffer, format="JPEG", quality=quality)
            processed_bytes = output_buffer.getvalue()
            
            if len(processed_bytes) < 10 * 1024 * 1024:
                return processed_bytes
            
            quality -= 10
        
        return processed_bytes
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")


# ✅ UPLOAD ROUTE
@router.post("/upload")
async def upload_images(
    file: UploadFile = File(...),
    current_user: dict = Depends(verify_token)
):
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
    filename_lower = file.filename.lower()
    is_image = file.content_type.startswith("image/") or any(filename_lower.endswith(ext) for ext in allowed_extensions)

    if not is_image:
        raise HTTPException(status_code=400, detail=f"{file.filename} is not a supported image format!")

    contents = await file.read()
    
    processed_contents = process_image(contents, file.filename)

    # ✅ Run ALL analysis BEFORE encrypting
    blur_result = detect_blur(processed_contents)
    technical_result = analyze_technical_quality(processed_contents)
    aesthetic_result = predict_aesthetic_score(processed_contents)

    existing_hashes = list(db.images.find(
        {"user_email": current_user["email"]},
        {"filename": 1, "phash": 1, "_id": 0}
    ))
    duplicate_result = check_duplicate(processed_contents, existing_hashes)

    explanation = generate_explanation({
        "sharpness": technical_result["sharpness"],
        "exposure_accuracy": technical_result["exposure_accuracy"],
        "noise_control": technical_result["noise_control"],
        "saturation_balance": technical_result["saturation_balance"],
        "contrast_quality": technical_result["contrast_quality"],
        "technical_score": technical_result["technical_score"],
        "aesthetic_score": aesthetic_result["aesthetic_score"]
    })

    # ✅ Encrypt AFTER analysis, BEFORE uploading to Cloudinary
    user_record = db.users.find_one({"email": current_user["email"]})
    if not user_record or not user_record.get("encryption_key"):
        raise HTTPException(status_code=500, detail="Encryption key not found for user.")
    
    encrypted_contents = encrypt_image(processed_contents, user_record["encryption_key"])

    result = cloudinary.uploader.upload(
        io.BytesIO(encrypted_contents),
        folder="picpicky/uploads",
        resource_type="raw"
    )

    image_doc = {
        "user_email": current_user["email"],
        "filename": file.filename,
        "cloudinary_url": result["secure_url"],
        "cloudinary_id": result["public_id"],
        "uploaded_at": datetime.utcnow(),
        "status": "uploaded",
        "blur_score": blur_result["blur_score"],
        "is_blurry": blur_result["is_blurry"],
        "phash": duplicate_result["phash"],
        "is_duplicate": duplicate_result["is_duplicate"],
        "duplicate_of": duplicate_result["duplicate_of"],
        "sharpness": technical_result["sharpness"],
        "exposure_accuracy": technical_result["exposure_accuracy"],
        "noise_control": technical_result["noise_control"],
        "saturation_balance": technical_result["saturation_balance"],
        "contrast_quality": technical_result["contrast_quality"],
        "technical_score": technical_result["technical_score"],
        "aesthetic_score": aesthetic_result["aesthetic_score"],
        "aesthetic_label": aesthetic_result["aesthetic_label"],
        "verdict": explanation["verdict"],
        "strengths": explanation["strengths"],
        "issues": explanation["issues"],
        "suggestions": explanation["suggestions"]
    }

    db.images.insert_one(image_doc)

    return {
        "message": "Image uploaded successfully!",
        "filename": file.filename,
        "url": result["secure_url"],
        "blur_score": blur_result["blur_score"],
        "is_blurry": blur_result["is_blurry"],
        "is_duplicate": duplicate_result["is_duplicate"],
        "duplicate_of": duplicate_result["duplicate_of"],
        "technical_score": technical_result["technical_score"],
        "sharpness": technical_result["sharpness"],
        "exposure_accuracy": technical_result["exposure_accuracy"],
        "noise_control": technical_result["noise_control"],
        "saturation_balance": technical_result["saturation_balance"],
        "contrast_quality": technical_result["contrast_quality"],
        "aesthetic_score": aesthetic_result["aesthetic_score"],
        "aesthetic_label": aesthetic_result["aesthetic_label"],
        "verdict": explanation["verdict"],
        "strengths": explanation["strengths"],
        "issues": explanation["issues"],
        "suggestions": explanation["suggestions"]
    }


# ✅ DECRYPT & SERVE IMAGE ROUTE
@router.get("/image/{image_id}")
async def get_image(image_id: str, current_user: dict = Depends(verify_token)):
    if not ObjectId.is_valid(image_id):
        raise HTTPException(status_code=400, detail="Invalid image ID format.")

    image_doc = db.images.find_one({
        "_id": ObjectId(image_id),
        "user_email": current_user["email"]
    })

    if not image_doc:
        raise HTTPException(status_code=404, detail="Image not found or access denied.")

    user_record = db.users.find_one({"email": current_user["email"]})
    if not user_record or not user_record.get("encryption_key"):
        raise HTTPException(status_code=500, detail="Encryption key not found for user.")

    try:
        response = requests.get(image_doc["cloudinary_url"], timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch image from storage: {str(e)}")

    try:
        decrypted_bytes = decrypt_image(response.content, user_record["encryption_key"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decrypt image: {str(e)}")

    return StreamingResponse(
        io.BytesIO(decrypted_bytes),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"}
    )


# ✅ DASHBOARD ROUTE
@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(verify_token)):
    user_email = current_user["email"]
    
    total_images = db.images.count_documents({"user_email": user_email})
    
    blurry_images = db.images.count_documents({
        "user_email": user_email,
        "is_blurry": True
    })
    
    duplicate_images = db.images.count_documents({
        "user_email": user_email,
        "is_duplicate": True
    })
    
    pipeline = [
        {"$match": {"user_email": user_email}},
        {"$group": {
            "_id": None,
            "avg_technical": {"$avg": "$technical_score"},
            "avg_aesthetic": {"$avg": "$aesthetic_score"},
            "avg_sharpness": {"$avg": "$sharpness"},
            "avg_exposure": {"$avg": "$exposure_accuracy"},
            "avg_noise": {"$avg": "$noise_control"}
        }}
    ]
    
    avg_result = list(db.images.aggregate(pipeline))
    
    if avg_result:
        avg_data = avg_result[0]
    else:
        avg_data = {
            "avg_technical": 0,
            "avg_aesthetic": 0,
            "avg_sharpness": 0,
            "avg_exposure": 0,
            "avg_noise": 0
        }
    
    recent_images = list(db.images.find(
        {"user_email": user_email}
    ).sort("uploaded_at", -1).limit(5))
    
    for img in recent_images:
        img["_id"] = str(img["_id"])
    
    return {
        "total_images": total_images,
        "blurry_images": blurry_images,
        "duplicate_images": duplicate_images,
        "avg_technical_score": round(avg_data.get("avg_technical", 0), 2),
        "avg_aesthetic_score": round(avg_data.get("avg_aesthetic", 0), 2),
        "avg_sharpness": round(avg_data.get("avg_sharpness", 0), 2),
        "avg_exposure": round(avg_data.get("avg_exposure", 0), 2),
        "avg_noise": round(avg_data.get("avg_noise", 0), 2),
        "recent_images": recent_images
    }


# ✅ PROFILE ROUTE
@router.get("/profile")
async def get_profile(current_user: dict = Depends(verify_token)):
    user_email = current_user["email"]
    
    user_info = db.users.find_one({"email": user_email})
    
    total_uploads = db.images.count_documents({"user_email": user_email})
    
    pipeline = [
        {"$match": {"user_email": user_email}},
        {"$group": {
            "_id": None,
            "avg_technical": {"$avg": "$technical_score"},
            "avg_aesthetic": {"$avg": "$aesthetic_score"}
        }}
    ]
    
    avg_result = list(db.images.aggregate(pipeline))
    
    if avg_result:
        avg_technical = avg_result[0].get("avg_technical", 0)
        avg_aesthetic = avg_result[0].get("avg_aesthetic", 0)
    else:
        avg_technical = 0
        avg_aesthetic = 0
    
    profile_score = round((avg_technical * 0.4) + (avg_aesthetic * 0.6), 2)
    
    if profile_score >= 85:
        level = "Expert"
    elif profile_score >= 70:
        level = "Advanced"
    elif profile_score >= 50:
        level = "Intermediate"
    else:
        level = "Beginner"
    
    high_quality = db.images.count_documents({
        "user_email": user_email,
        "technical_score": {"$gte": 70}
    })
    
    medium_quality = db.images.count_documents({
        "user_email": user_email,
        "technical_score": {"$gte": 50, "$lt": 70}
    })
    
    low_quality = db.images.count_documents({
        "user_email": user_email,
        "technical_score": {"$lt": 50}
    })
    
    return {
        "name": user_info.get("name", "User"),
        "email": user_email,
        "total_uploads": total_uploads,
        "profile_score": profile_score,
        "level": level,
        "avg_technical_score": round(avg_technical, 2),
        "avg_aesthetic_score": round(avg_aesthetic, 2),
        "high_quality_count": high_quality,
        "medium_quality_count": medium_quality,
        "low_quality_count": low_quality,
        "member_since": user_info.get("created_at").strftime("%B %Y") if user_info.get("created_at") else "Unknown"
    }


# ✅ BEST ALBUM ROUTE — technical_score > 80 AND aesthetic_score > 0.6
@router.get("/best-album")
async def get_best_album(current_user: dict = Depends(verify_token)):
    user_email = current_user["email"]

    top_images = list(db.images.find(
        {
            "user_email": user_email,
            "technical_score": {"$gt": 80},
            "aesthetic_score": {"$gt": 0.6},   # ← changed from 0.7 to 0.6
            "is_blurry": False,
            "is_duplicate": False
        }
    ).sort("aesthetic_score", -1).limit(20))

    duplicate_images = list(db.images.find(
        {"user_email": user_email, "is_duplicate": True}
    ).sort("uploaded_at", -1).limit(10))

    blurry_images = list(db.images.find(
        {"user_email": user_email, "is_blurry": True}
    ).sort("uploaded_at", -1).limit(10))

    all_images = top_images + duplicate_images + blurry_images

    for img in all_images:
        img["_id"] = str(img["_id"])

    return {
        "message": "Best album fetched successfully!",
        "total_images": len(top_images),
        "images": all_images
    }


# ✅ GET ALL USER IMAGES
@router.get("/my-images")
async def get_my_images(current_user: dict = Depends(verify_token)):
    user_email = current_user["email"]
    
    images = list(db.images.find(
        {"user_email": user_email}
    ).sort("uploaded_at", -1))
    
    for img in images:
        img["_id"] = str(img["_id"])
        if "uploaded_at" in img:
            img["uploaded_at"] = img["uploaded_at"].isoformat()
    
    return {
        "total": len(images),
        "images": images
    }