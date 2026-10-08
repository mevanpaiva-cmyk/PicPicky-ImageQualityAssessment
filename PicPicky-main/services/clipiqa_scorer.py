"""CLIP-IQA Aesthetic Quality Scorer."""

# ✅ Patch for Python 3.12+ compatibility — pkgutil.ImpImporter was removed
import pkgutil
if not hasattr(pkgutil, 'ImpImporter'):
    class _FakeImpImporter:
        def __init__(self, path=None):
            self.path = path
        def find_module(self, fullname, path=None):
            return None
    pkgutil.ImpImporter = _FakeImpImporter

import torch
import pyiqa
import numpy as np
import cv2
from PIL import Image
import io

# Load model once
device = torch.device("cpu")
model = None

def load_model():
    global model
    if model is None:
        print("Loading CLIP-IQA model...")
        model = pyiqa.create_metric('clipiqa', device=device)
        print("CLIP-IQA model loaded successfully!")
    return model

def predict_aesthetic_score(image_bytes: bytes) -> dict:
    """Takes image bytes, returns aesthetic score 0-1."""
    try:
        iqa_model = load_model()

        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Run inference
        with torch.no_grad():
            score = iqa_model(image)
            final_score = round(float(score.item()), 4)

        # Label based on score
        if final_score >= 0.75:
            label = "high"
        elif final_score >= 0.45:
            label = "medium"
        else:
            label = "low"

        return {
            "aesthetic_score": final_score,
            "aesthetic_label": label
        }

    except Exception as e:
        print(f"CLIP-IQA error: {e}")
        return {"aesthetic_score": 0.0, "aesthetic_label": "unknown"}