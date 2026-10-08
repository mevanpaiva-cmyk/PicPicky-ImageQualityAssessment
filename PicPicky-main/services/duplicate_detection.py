"""Duplicate detection using pHash."""
import numpy as np
from PIL import Image
import imagehash
import io

def get_phash(image_bytes: bytes, hash_size: int = 16) -> str:
    """Compute pHash from image bytes."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return str(imagehash.phash(image, hash_size=hash_size))

def check_duplicate(new_image_bytes: bytes, existing_hashes: list, threshold: int = 5) -> dict:
    """
    Compare new image against existing hashes from MongoDB.
    Returns is_duplicate flag and the matching image if found.
    """
    new_hash = imagehash.hex_to_hash(get_phash(new_image_bytes))

    for entry in existing_hashes:
        if not entry.get("phash"):
            continue
        existing_hash = imagehash.hex_to_hash(entry["phash"])
        distance = new_hash - existing_hash
        if distance <= threshold:
            return {
                "is_duplicate": True,
                "duplicate_of": entry["filename"],
                "distance": distance,
                "phash": str(new_hash)
            }

    return {
        "is_duplicate": False,
        "duplicate_of": None,
        "distance": None,
        "phash": str(new_hash)
    }