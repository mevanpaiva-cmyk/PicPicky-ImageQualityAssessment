from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from database import db
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from config import MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_FROM_NAME, MAIL_PORT, MAIL_SERVER
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from services.encryption import generate_user_key  # ✅ NEW IMPORT
import secrets

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

ADMIN_EMAILS = ["admin1@picpicky.com", "admin2@picpicky.com"]

conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_FROM_NAME=MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

class RegisterModel(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginModel(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordModel(BaseModel):
    email: EmailStr

class ResetPasswordModel(BaseModel):
    token: str
    new_password: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # ✅ Fetch full user from DB so encryption_key is available
        user = db.users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return {
            "email": email,
            "encryption_key": user.get("encryption_key")  # ✅ NEW
        }
    except JWTError:
        raise HTTPException(
            status_code=401, detail="Invalid or expired token"
        )

@router.post("/register")
def register(user: RegisterModel):
    try:
        existing_user = db.users.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email already registered"
            )

        hashed_password = pwd_context.hash(user.password[:72])

        db.users.insert_one({
            "name": user.name,
            "email": user.email,
            "password": hashed_password,
            "created_at": datetime.utcnow(),
            "status": "active",
            "encryption_key": generate_user_key()  # ✅ NEW — one key per user
        })

        return {"message": "User registered successfully!"}

    except HTTPException:
        raise
    except ServerSelectionTimeoutError:
        raise HTTPException(
            status_code=503,
            detail="❌ Cannot connect to database. Please try again later."
        )
    except ConnectionFailure:
        raise HTTPException(
            status_code=503,
            detail="❌ Database connection failed."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"❌ Server error: {str(e)}"
        )

@router.post("/login")
def login(user: LoginModel):
    try:
        existing_user = db.users.find_one({"email": user.email})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")

        if not pwd_context.verify(
            user.password[:72], existing_user["password"]
        ):
            raise HTTPException(
                status_code=401, detail="Incorrect password"
            )

        token = create_access_token({"sub": existing_user["email"]})
        is_admin = user.email in ADMIN_EMAILS

        return {
            "message": "Login successful",
            "name": existing_user["name"],
            "email": existing_user["email"],
            "access_token": token,
            "is_admin": is_admin
        }

    except HTTPException:
        raise
    except ServerSelectionTimeoutError:
        raise HTTPException(
            status_code=503,
            detail="❌ Cannot connect to database. Please try again later."
        )
    except ConnectionFailure:
        raise HTTPException(
            status_code=503,
            detail="❌ Database connection failed."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"❌ Server error: {str(e)}"
        )

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordModel):
    try:
        user = db.users.find_one({"email": data.email})
        if not user:
            raise HTTPException(
                status_code=404,
                detail="No account found with this email"
            )

        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        db.password_resets.insert_one({
            "email": data.email,
            "token": reset_token,
            "expires_at": expires_at,
            "used": False,
            "created_at": datetime.utcnow()
        })

        reset_link = f"http://127.0.0.1:5500/frontend/reset-password.html?token={reset_token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Inter', Arial, sans-serif;
                    background-color: #0b1326;
                    color: #dae2fd;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background: rgba(23, 31, 51, 0.9);
                    border-radius: 16px;
                    padding: 40px;
                    border: 1px solid rgba(165, 200, 255, 0.1);
                }}
                .logo {{
                    text-align: center;
                    font-size: 32px;
                    font-weight: 900;
                    font-style: italic;
                    color: #a5c8ff;
                    margin-bottom: 30px;
                }}
                h1 {{
                    color: #a5c8ff;
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                p {{
                    color: #c1c7d4;
                    line-height: 1.6;
                    margin-bottom: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 16px 32px;
                    background: linear-gradient(135deg, #a5c8ff 0%, #3e92f3 100%);
                    color: #00315e;
                    text-decoration: none;
                    border-radius: 12px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid rgba(165, 200, 255, 0.1);
                    color: #8b919e;
                    font-size: 12px;
                }}
                .warning {{
                    background: rgba(255, 180, 171, 0.1);
                    padding: 16px;
                    border-radius: 8px;
                    border-left: 4px solid #ffb4ab;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">PicPicky</div>
                <h1>Password Reset Request</h1>
                <p>Hi {user['name']},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <a href="{reset_link}" class="button">Reset Password</a>
                <div class="warning">
                    <p style="margin: 0;"><strong>⚠️ Security Notice:</strong></p>
                    <p style="margin: 8px 0 0 0;">This link expires in 1 hour. If you didn't request this reset, please ignore this email.</p>
                </div>
                <p style="color: #8b919e; font-size: 14px;">Or copy and paste this link in your browser:</p>
                <p style="color: #a5c8ff; word-break: break-all; font-size: 12px;">{reset_link}</p>
                <div class="footer">
                    <p>© 2024 PicPicky Optical Systems</p>
                    <p>Precision tools for the visionary eye.</p>
                </div>
            </div>
        </body>
        </html>
        """

        message = MessageSchema(
            subject="Reset Your PicPicky Password",
            recipients=[data.email],
            body=html,
            subtype="html"
        )

        fm = FastMail(conf)
        await fm.send_message(message)

        return {
            "message": "Password reset link sent to your email",
            "email": data.email
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )

@router.post("/reset-password")
def reset_password(data: ResetPasswordModel):
    try:
        reset_request = db.password_resets.find_one({
            "token": data.token,
            "used": False
        })

        if not reset_request:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired reset link"
            )

        if reset_request["expires_at"] < datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="Reset link has expired. Please request a new one."
            )

        hashed_password = pwd_context.hash(data.new_password[:72])

        db.users.update_one(
            {"email": reset_request["email"]},
            {"$set": {"password": hashed_password}}
        )

        db.password_resets.update_one(
            {"token": data.token},
            {"$set": {"used": True}}
        )

        return {
            "message": "Password reset successful! You can now login with your new password."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"❌ Server error: {str(e)}"
        )