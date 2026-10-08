from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from database import db
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM
from typing import Optional
from bson import ObjectId

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer()

# Admin emails list
ADMIN_EMAILS = ["admin1@picpicky.com", "admin2@picpicky.com"]

# ─────────────────────────────────────────
# Helper: Convert MongoDB doc to JSON-safe
# ─────────────────────────────────────────
def serialize_doc(doc):
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        doc = doc.copy()
        if '_id' in doc:
            doc['id'] = str(doc['_id'])
            del doc['_id']
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                doc[key] = str(value)
            elif isinstance(value, datetime):
                doc[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                doc[key] = serialize_doc(value)
        return doc
    return doc

# ─────────────────────────────────────────
# Admin Token Verification
# ─────────────────────────────────────────
def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        if email not in ADMIN_EMAILS:
            raise HTTPException(status_code=403, detail="Admin access required")
        return {"email": email}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ─────────────────────────────────────────
# GET /admin/metrics
# ─────────────────────────────────────────
@router.get("/metrics")
def get_metrics():
    try:
        # Total users
        total_users = db.users.count_documents({})

        # Total uploads
        total_uploads = db.images.count_documents({})

        # Uploads today
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        processed_today = db.images.count_documents({
            "uploaded_at": {"$gte": today_start}
        })

        # Average analysis time (based on technical_score as proxy)
        pipeline_avg = [
            {"$group": {
                "_id": None,
                "avg_technical": {"$avg": "$technical_score"},
                "avg_aesthetic": {"$avg": "$aesthetic_score"},
                "avg_sharpness": {"$avg": "$sharpness"}
            }}
        ]
        avg_result = list(db.images.aggregate(pipeline_avg))
        avg_data = avg_result[0] if avg_result else {}

        # Blurry images count
        blurry_count = db.images.count_documents({"is_blurry": True})

        # Duplicate images count
        duplicate_count = db.images.count_documents({"is_duplicate": True})

        # Total views (total images * 3 as proxy)
        total_views = total_uploads * 3

        # Last month users (for trend)
        last_month = datetime.utcnow() - timedelta(days=30)
        new_users_this_month = db.users.count_documents({
            "created_at": {"$gte": last_month}
        })

        # Last week uploads (for trend)
        last_week = datetime.utcnow() - timedelta(days=7)
        new_uploads_this_week = db.images.count_documents({
            "uploaded_at": {"$gte": last_week}
        })

        return {
            "totalUsers": total_users,
            "totalUploads": total_uploads,
            "processedToday": processed_today,
            "avgAnalysisTime": round(avg_data.get("avg_technical", 0) / 100, 2),
            "totalViews": total_views,
            "blurryImages": blurry_count,
            "duplicateImages": duplicate_count,
            "avgTechnicalScore": round(avg_data.get("avg_technical", 0), 2),
            "avgAestheticScore": round(avg_data.get("avg_aesthetic", 0), 2),
            "avgSharpness": round(avg_data.get("avg_sharpness", 0), 2),
            "newUsersThisMonth": new_users_this_month,
            "newUploadsThisWeek": new_uploads_this_week,
            "trends": {
                "users": round((new_users_this_month / max(total_users, 1)) * 100, 1),
                "uploads": round((new_uploads_this_week / max(total_uploads, 1)) * 100, 1),
                "processed": processed_today,
                "analysisTime": 1.2,
                "views": 0
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching metrics: {str(e)}"
        )

# ─────────────────────────────────────────
# GET /admin/users
# ─────────────────────────────────────────
@router.get("/users")
def get_all_users(
    start: Optional[str] = None,
    end: Optional[str] = None
):
    try:
        query = {}

        if start and end:
            query["created_at"] = {
                "$gte": datetime.fromisoformat(start),
                "$lte": datetime.fromisoformat(end)
            }

        users = list(db.users.find(query, {"password": 0}))

        result = []
        for user in users:
            user_email = user.get("email")

            # Get upload stats for each user
            total_uploads = db.images.count_documents(
                {"user_email": user_email}
            )
            blurry = db.images.count_documents({
                "user_email": user_email,
                "is_blurry": True
            })
            duplicates = db.images.count_documents({
                "user_email": user_email,
                "is_duplicate": True
            })

            # Get average scores
            pipeline = [
                {"$match": {"user_email": user_email}},
                {"$group": {
                    "_id": None,
                    "avg_technical": {"$avg": "$technical_score"},
                    "avg_aesthetic": {"$avg": "$aesthetic_score"}
                }}
            ]
            avg_result = list(db.images.aggregate(pipeline))
            avg_data = avg_result[0] if avg_result else {}

            avg_technical = round(avg_data.get("avg_technical", 0), 2)
            avg_aesthetic = round(avg_data.get("avg_aesthetic", 0), 2)

            # Determine photographer level
            profile_score = round(
                (avg_technical * 0.4) + (avg_aesthetic * 0.6), 2
            )
            if profile_score >= 85:
                level = "Expert"
            elif profile_score >= 70:
                level = "Advanced"
            elif profile_score >= 50:
                level = "Intermediate"
            else:
                level = "Beginner"

            result.append({
                "id": str(user["_id"]),
                "name": user.get("name", "Unknown"),
                "email": user_email,
                "uploads": total_uploads,
                "blurry": blurry,
                "duplicates": duplicates,
                "avgTechnicalScore": avg_technical,
                "avgAestheticScore": avg_aesthetic,
                "profileScore": profile_score,
                "level": level,
                "status": user.get("status", "active"),
                "joinDate": user.get("created_at", datetime.utcnow()).isoformat()
                if isinstance(user.get("created_at"), datetime)
                else str(user.get("created_at", "")),
                "created_at": user.get("created_at", datetime.utcnow()).isoformat()
                if isinstance(user.get("created_at"), datetime)
                else str(user.get("created_at", ""))
            })

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching users: {str(e)}"
        )

# ─────────────────────────────────────────
# GET /admin/users/{user_id}
# ─────────────────────────────────────────
@router.get("/users/{user_id}")
def get_user_details(user_id: str):
    try:
        user = db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"password": 0}
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_email = user.get("email")

        # Get all uploads for this user
        uploads = list(db.images.find(
            {"user_email": user_email}
        ).sort("uploaded_at", -1).limit(10))

        total_uploads = db.images.count_documents({"user_email": user_email})
        blurry = db.images.count_documents({
            "user_email": user_email,
            "is_blurry": True
        })
        duplicates = db.images.count_documents({
            "user_email": user_email,
            "is_duplicate": True
        })

        # Scores pipeline
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
        avg_data = avg_result[0] if avg_result else {}

        avg_technical = round(avg_data.get("avg_technical", 0), 2)
        avg_aesthetic = round(avg_data.get("avg_aesthetic", 0), 2)
        profile_score = round((avg_technical * 0.4) + (avg_aesthetic * 0.6), 2)

        if profile_score >= 85:
            level = "Expert"
        elif profile_score >= 70:
            level = "Advanced"
        elif profile_score >= 50:
            level = "Intermediate"
        else:
            level = "Beginner"

        return {
            "id": str(user["_id"]),
            "name": user.get("name", "Unknown"),
            "email": user_email,
            "status": user.get("status", "active"),
            "joinDate": user.get("created_at", datetime.utcnow()).isoformat()
            if isinstance(user.get("created_at"), datetime)
            else str(user.get("created_at", "")),
            "uploads": total_uploads,
            "blurry": blurry,
            "duplicates": duplicates,
            "profileScore": profile_score,
            "level": level,
            "avgTechnicalScore": avg_technical,
            "avgAestheticScore": avg_aesthetic,
            "avgSharpness": round(avg_data.get("avg_sharpness", 0), 2),
            "avgExposure": round(avg_data.get("avg_exposure", 0), 2),
            "avgNoise": round(avg_data.get("avg_noise", 0), 2),
            "recentUploads": serialize_doc(uploads)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user details: {str(e)}"
        )

# ─────────────────────────────────────────
# PATCH /admin/users/{user_id}/suspend
# ─────────────────────────────────────────
@router.patch("/users/{user_id}/suspend")
def suspend_user(user_id: str):
    try:
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "status": "suspended",
                "suspended_at": datetime.utcnow()
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "User suspended successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error suspending user: {str(e)}"
        )

# ─────────────────────────────────────────
# PATCH /admin/users/{user_id}/activate
# ─────────────────────────────────────────
@router.patch("/users/{user_id}/activate")
def activate_user(user_id: str):
    try:
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "status": "active",
                "activated_at": datetime.utcnow()
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "User activated successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error activating user: {str(e)}"
        )

# ─────────────────────────────────────────
# GET /admin/activity
# ─────────────────────────────────────────
@router.get("/activity")
def get_activity(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 50
):
    try:
        query = {}

        if start and end:
            query["uploaded_at"] = {
                "$gte": datetime.fromisoformat(start),
                "$lte": datetime.fromisoformat(end)
            }

        # Fetch recent uploads from db.images
        uploads = list(
            db.images.find(query).sort("uploaded_at", -1).limit(limit)
        )

        activity = []
        for upload in uploads:
            user = db.users.find_one(
                {"email": upload.get("user_email")},
                {"name": 1, "_id": 0}
            )
            user_name = user.get("name", "Unknown") if user else "Unknown"

            # Determine status
            if upload.get("is_duplicate"):
                status = "pending"
                action_label = f"Duplicate detected: {upload.get('filename', 'image')}"
            elif upload.get("is_blurry"):
                status = "error"
                action_label = f"Blurry image: {upload.get('filename', 'image')}"
            else:
                status = "success"
                action_label = f"Uploaded: {upload.get('filename', 'image')}"

            uploaded_at = upload.get("uploaded_at", datetime.utcnow())

            activity.append({
                "id": str(upload["_id"]),
                "user": user_name,
                "userName": user_name,
                "userEmail": upload.get("user_email", ""),
                "action": action_label,
                "filename": upload.get("filename", ""),
                "status": status,
                "technicalScore": upload.get("technical_score", 0),
                "aestheticScore": upload.get("aesthetic_score", 0),
                "isBlurry": upload.get("is_blurry", False),
                "isDuplicate": upload.get("is_duplicate", False),
                "timestamp": uploaded_at.isoformat()
                if isinstance(uploaded_at, datetime)
                else str(uploaded_at),
                "time": uploaded_at.isoformat()
                if isinstance(uploaded_at, datetime)
                else str(uploaded_at)
            })

        return activity

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching activity: {str(e)}"
        )

# ─────────────────────────────────────────
# GET /admin/alerts
# ─────────────────────────────────────────
@router.get("/alerts")
def get_alerts():
    try:
        alerts = []
        alert_id = 1

        # Check failed/blurry uploads spike (last 1 hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_blurry = db.images.count_documents({
            "uploaded_at": {"$gte": one_hour_ago},
            "is_blurry": True
        })

        if recent_blurry > 5:
            alerts.append({
                "id": alert_id,
                "type": "error",
                "priority": "High",
                "title": "Blurry Uploads Spike",
                "description": f"{recent_blurry} blurry images uploaded in the last hour.",
                "icon": "warning",
                "resolved": False
            })
            alert_id += 1

        # Check duplicates spike
        recent_duplicates = db.images.count_documents({
            "uploaded_at": {"$gte": one_hour_ago},
            "is_duplicate": True
        })

        if recent_duplicates > 5:
            alerts.append({
                "id": alert_id,
                "type": "warning",
                "priority": "Med",
                "title": "Duplicate Uploads Spike",
                "description": f"{recent_duplicates} duplicate images detected in the last hour.",
                "icon": "content_copy",
                "resolved": False
            })
            alert_id += 1

        # Check low quality uploads
        recent_low_quality = db.images.count_documents({
            "uploaded_at": {"$gte": one_hour_ago},
            "technical_score": {"$lt": 40}
        })

        if recent_low_quality > 10:
            alerts.append({
                "id": alert_id,
                "type": "warning",
                "priority": "Med",
                "title": "Low Quality Uploads",
                "description": f"{recent_low_quality} low quality images uploaded recently.",
                "icon": "image_not_supported",
                "resolved": False
            })
            alert_id += 1

        # Check new user registrations spike (last 24 hours)
        one_day_ago = datetime.utcnow() - timedelta(hours=24)
        new_users_today = db.users.count_documents({
            "created_at": {"$gte": one_day_ago}
        })

        if new_users_today > 50:
            alerts.append({
                "id": alert_id,
                "type": "info",
                "priority": "Low",
                "title": "High User Registrations",
                "description": f"{new_users_today} new users registered in the last 24 hours.",
                "icon": "person_add",
                "resolved": False
            })
            alert_id += 1

        # Always add system health check
        total_uploads = db.images.count_documents({})
        alerts.append({
            "id": alert_id,
            "type": "info",
            "priority": "Low",
            "title": "System Status",
            "description": f"System running normally. Total images in database: {total_uploads}",
            "icon": "check_circle",
            "resolved": False
        })

        return alerts

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching alerts: {str(e)}"
        )

# ─────────────────────────────────────────
# PATCH /admin/alerts/{alert_id}/resolve
# ─────────────────────────────────────────
@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int):
    try:
        return {
            "message": "Alert resolved successfully",
            "alert_id": alert_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error resolving alert: {str(e)}"
        )

# ─────────────────────────────────────────
# GET /admin/chart-data
# ─────────────────────────────────────────
@router.get("/chart-data")
def get_chart_data(period: str = "24H"):
    try:
        now = datetime.utcnow()

        if period == "24H":
            intervals = 12
            time_delta = timedelta(hours=2)
        elif period == "7D":
            intervals = 7
            time_delta = timedelta(days=1)
        elif period == "30D":
            intervals = 30
            time_delta = timedelta(days=1)
        else:
            intervals = 12
            time_delta = timedelta(hours=2)

        chart_data = []

        for i in range(intervals):
            start_time = now - time_delta * (intervals - i)
            end_time = start_time + time_delta

            # Count uploads in this interval
            count = db.images.count_documents({
                "uploaded_at": {
                    "$gte": start_time,
                    "$lt": end_time
                }
            })

            # Count blurry in this interval
            blurry_count = db.images.count_documents({
                "uploaded_at": {
                    "$gte": start_time,
                    "$lt": end_time
                },
                "is_blurry": True
            })

            chart_data.append({
                "value": count,
                "blurry": blurry_count,
                "timestamp": start_time.isoformat(),
                "label": start_time.strftime(
                    "%H:%M" if period == "24H" else "%b %d"
                )
            })

        return chart_data

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching chart data: {str(e)}"
        )

# ─────────────────────────────────────────
# GET /admin/images
# ─────────────────────────────────────────
@router.get("/images")
def get_all_images(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 100
):
    try:
        query = {}

        if start and end:
            query["uploaded_at"] = {
                "$gte": datetime.fromisoformat(start),
                "$lte": datetime.fromisoformat(end)
            }

        images = list(
            db.images.find(query).sort("uploaded_at", -1).limit(limit)
        )

        return serialize_doc(images)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching images: {str(e)}"
        )

# ─────────────────────────────────────────
# GET /admin/stats/export
# ─────────────────────────────────────────
@router.get("/stats/export")
def get_export_stats(
    start: Optional[str] = None,
    end: Optional[str] = None
):
    try:
        user_query = {}
        image_query = {}

        if start and end:
            user_query["created_at"] = {
                "$gte": datetime.fromisoformat(start),
                "$lte": datetime.fromisoformat(end)
            }
            image_query["uploaded_at"] = {
                "$gte": datetime.fromisoformat(start),
                "$lte": datetime.fromisoformat(end)
            }

        users = list(db.users.find(user_query, {"password": 0}))
        images = list(db.images.find(image_query))

        export_users = []
        for user in users:
            user_email = user.get("email")
            upload_count = db.images.count_documents(
                {"user_email": user_email}
            )
            export_users.append({
                "name": user.get("name", ""),
                "email": user_email,
                "uploads": upload_count,
                "status": user.get("status", "active"),
                "joinDate": user.get("created_at", "").isoformat()
                if isinstance(user.get("created_at"), datetime)
                else str(user.get("created_at", ""))
            })

        export_images = []
        for img in images:
            uploaded_at = img.get("uploaded_at", "")
            export_images.append({
                "filename": img.get("filename", ""),
                "userEmail": img.get("user_email", ""),
                "technicalScore": img.get("technical_score", 0),
                "aestheticScore": img.get("aesthetic_score", 0),
                "isBlurry": img.get("is_blurry", False),
                "isDuplicate": img.get("is_duplicate", False),
                "verdict": img.get("verdict", ""),
                "uploadedAt": uploaded_at.isoformat()
                if isinstance(uploaded_at, datetime)
                else str(uploaded_at)
            })

        return {
            "users": export_users,
            "images": export_images,
            "totalUsers": len(export_users),
            "totalImages": len(export_images)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching export stats: {str(e)}"
        )