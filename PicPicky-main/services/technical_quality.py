"""
Technical Quality Analysis Module
Metrics:
- Sharpness
- Exposure Accuracy
- Noise Control
- Saturation Balance
- Contrast Quality
"""
import cv2
import numpy as np

def normalize_score(value, min_val, max_val):
    """Normalize value to 0–100 scale."""
    value = np.clip(value, min_val, max_val)
    return 100 * (value - min_val) / (max_val - min_val)

# 1️⃣ Sharpness (Laplacian Variance)
def compute_sharpness(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    std_dev = np.std(gray)

    # Motion blur detection — low sharpness but high contrast image
    if laplacian_var < 200 and std_dev > 30:
        return normalize_score(laplacian_var, 10, 500) * 0.7 + 30

    return normalize_score(laplacian_var, 10, 500)

# 2️⃣ Exposure Accuracy
def compute_exposure(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    mean_intensity = np.mean(gray)
    clipped_low = np.sum(gray < 5) / gray.size
    clipped_high = np.sum(gray > 250) / gray.size
    exposure_score = 100 - abs(mean_intensity - 128) * 0.8
    exposure_score -= (clipped_low + clipped_high) * 100
    return np.clip(exposure_score, 0, 100)

# 3️⃣ Noise Control
def compute_noise(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    if laplacian_var < 50:
        return round(float(np.clip(laplacian_var, 0, 100)), 2)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    noise_map = gray.astype(np.float32) - blurred.astype(np.float32)
    noise_variance = np.var(noise_map)
    noise_score = 100 - normalize_score(noise_variance, 0, 150)  # Changed 50 → 150
    return float(np.clip(noise_score, 0, 100))
    

# 4️⃣ Saturation Balance
def compute_saturation(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    saturation_channel = hsv[:, :, 1]
    mean_saturation = np.mean(saturation_channel)
    saturation_score = 100 - abs(mean_saturation - 140) * 0.5
    return np.clip(saturation_score, 0, 100)

# 5️⃣ Contrast Quality
def compute_contrast(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    std_dev = np.std(gray)
    return normalize_score(std_dev, 10, 70)

def analyze_technical_quality(image_bytes: bytes) -> dict:
    """Takes raw image bytes, returns technical quality scores."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return {
            "sharpness": 0.0,
            "exposure_accuracy": 0.0,
            "noise_control": 0.0,
            "saturation_balance": 0.0,
            "contrast_quality": 0.0,
            "technical_score": 0.0
        }

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    sharpness = compute_sharpness(image)
    exposure = compute_exposure(image)
    noise = compute_noise(image)
    saturation = compute_saturation(image)
    contrast = compute_contrast(image)

    technical_score = (
        0.30 * sharpness +
        0.25 * exposure +
        0.15 * noise +
        0.15 * saturation +
        0.15 * contrast
    )

    return {
        "sharpness": round(float(sharpness), 2),
        "exposure_accuracy": round(float(exposure), 2),
        "noise_control": round(float(noise), 2),
        "saturation_balance": round(float(saturation), 2),
        "contrast_quality": round(float(contrast), 2),
        "technical_score": round(float(technical_score), 2)
    }
