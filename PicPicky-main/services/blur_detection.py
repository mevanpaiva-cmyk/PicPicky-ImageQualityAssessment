"""Blur detection using Laplacian variance."""
import numpy as np
import cv2

def calculate_laplacian_variance(image):
    """Compute sharpness score. Higher = sharper, lower = blurrier."""
    if len(image.shape) == 3:
        if image.max() <= 1.0:
            image = (image * 255).astype(np.uint8)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image if image.max() > 1.0 else (image * 255).astype(np.uint8)
    return cv2.Laplacian(gray, cv2.CV_64F, ksize=3).var()

def detect_blur(image_bytes: bytes, threshold: float = 100.0):
    """
    Takes raw image bytes, returns blur score and classification.
    Returns dict with score and is_blurry flag.
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return {"blur_score": 0.0, "is_blurry": True}

    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    score = calculate_laplacian_variance(image_rgb)
    is_blurry = score < threshold

    return {
        "blur_score": round(float(score), 2),
        "is_blurry": bool(is_blurry)
    }