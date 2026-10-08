import os
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")

print(f"URL found: {MONGODB_URL[:40]}...")

try:
    client = MongoClient(
        MONGODB_URL,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,  # ← Increased to 10 seconds
        connectTimeoutMS=10000,          # ← Added this
        socketTimeoutMS=10000,           # ← Added this
    )
    client.admin.command("ping")
    print("✅ MongoDB connected successfully!")
except Exception as e:
    print(f"❌ Error: {e}")