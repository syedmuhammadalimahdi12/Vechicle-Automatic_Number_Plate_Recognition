from __future__ import annotations

from typing import Any


def prepare_plate(image: Any) -> Any:
    """Create a high-contrast OCR crop when OpenCV is available."""
    try:
        import cv2
    except ImportError:
        return image
    if image is None or getattr(image, "size", 0) == 0:
        return image
    height, width = image.shape[:2]
    resized = cv2.resize(image, (max(160, width * 3), max(48, height * 3)))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    return cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]