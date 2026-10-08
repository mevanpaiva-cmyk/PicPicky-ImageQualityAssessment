import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ✅ USE THE CORRECT ENV VARIABLE NAME
MONGO_URI = os.getenv("MONGODB_URL")

try:
    client = MongoClient(
        MONGO_URI,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000
    )

    # ✅ Force connection test
    client.admin.command("ping")

    # ✅ Use database name from .env
    db = client[os.getenv("DATABASE_NAME")]

    print("✅ MongoDB connected successfully!")

except Exception as e:
    print("❌ MongoDB connection error:", e)
    db = None