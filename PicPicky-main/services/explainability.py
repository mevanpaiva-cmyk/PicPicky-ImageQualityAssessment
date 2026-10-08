"""
Explainable IQA Module
Generates human-readable explanations based on image quality scores.
"""

def generate_explanation(scores: dict) -> dict:
    issues = []
    strengths = []
    suggestions = []

    # Sharpness
    if scores["sharpness"] < 20:
        issues.append("Image is significantly blurry")
        suggestions.append("Use a tripod or increase shutter speed to reduce blur")
    elif scores["sharpness"] < 40:
        issues.append("Possible motion blur detected")
        suggestions.append("Use faster shutter speed to freeze motion")
    else:
        strengths.append("Image is sharp and clear")

    # Exposure
    if scores["exposure_accuracy"] < 30:
        issues.append("Image is severely over or underexposed")
        suggestions.append("Adjust exposure compensation or use manual mode")
    elif scores["exposure_accuracy"] < 60:
        issues.append("Exposure could be improved")
        suggestions.append("Try adjusting brightness in post-processing")
    else:
        strengths.append("Exposure is well balanced")

    # Noise
    if scores["noise_control"] < 30:
        issues.append("High noise or blur detected")
        suggestions.append("Shoot in better lighting or reduce ISO settings")
    elif scores["noise_control"] < 50:
        issues.append("Moderate noise present")
        suggestions.append("Apply noise reduction in post-processing")
    else:
        strengths.append("Image has good noise control")

    # Saturation
    if scores["saturation_balance"] < 30:
        issues.append("Colors appear dull or overly saturated")
        suggestions.append("Adjust saturation and vibrance in editing")
    elif scores["saturation_balance"] < 60:
        issues.append("Color balance could be improved")
        suggestions.append("Fine tune color grading for better vibrancy")
    else:
        strengths.append("Colors are well balanced")

    # Contrast
    if scores["contrast_quality"] < 25:
        issues.append("Image lacks contrast — appears flat or washed out")
        suggestions.append("Increase contrast or use curves adjustment")
    elif scores["contrast_quality"] < 40:
        issues.append("Contrast could be stronger")
        suggestions.append("Add slight contrast boost in post-processing")
    else:
        strengths.append("Good contrast and tonal range")

    # Aesthetic
    if scores["aesthetic_score"] >= 0.65:
        strengths.append("Image has strong aesthetic appeal")
    elif scores["aesthetic_score"] >= 0.45:
        issues.append("Aesthetic quality is moderate")
        suggestions.append("Consider improving composition or lighting")
    else:
        issues.append("Image has low aesthetic appeal")
        suggestions.append("Focus on composition, lighting and subject placement")

    # Overall verdict
    technical = scores["technical_score"]
    aesthetic = scores["aesthetic_score"]

    if technical >= 75 or aesthetic >= 0.65:
        verdict = "Great Shot"
    elif technical >= 45 or aesthetic >= 0.45:
        verdict = "Average Shot"
    else:
        verdict = "Needs Improvement"

    return {
        "verdict": verdict,
        "strengths": strengths,
        "issues": issues,
        "suggestions": suggestions
    }