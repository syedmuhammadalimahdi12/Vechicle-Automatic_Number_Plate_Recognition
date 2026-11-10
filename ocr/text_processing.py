from __future__ import annotations

import re

_ALLOWED = re.compile(r"[^A-Z0-9]")


def clean_plate_text(text: str) -> str:
    """Normalize OCR output while keeping the source plate format flexible."""
    normalized = _ALLOWED.sub("", text.upper())
    return normalized[:16]


def validate_plate_text(text: str, minimum_length: int = 3, maximum_length: int = 12) -> bool:
    normalized = clean_plate_text(text)
    return minimum_length <= len(normalized) <= maximum_length and normalized.isalnum()


def format_plate_text(text: str) -> str:
    normalized = clean_plate_text(text)
    if len(normalized) > 4:
        return f"{normalized[:-4]}-{normalized[-4:]}"
    return normalized