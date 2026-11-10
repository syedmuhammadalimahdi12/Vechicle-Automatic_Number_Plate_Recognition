from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ocr.text_processing import clean_plate_text, format_plate_text

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float


class OCREngine:
    def __init__(self, engine: str = "easyocr", languages: list[str] | None = None) -> None:
        self.engine_name = engine
        self.languages = languages or ["en"]
        self._reader: Any = None

    def _load(self) -> None:
        if self._reader is not None:
            return
        if self.engine_name == "easyocr":
            try:
                import easyocr
                self._reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
            except ImportError as error:
                raise RuntimeError("EasyOCR is not installed. Install requirements.txt first.") from error
        else:
            raise RuntimeError(f"Unsupported OCR engine: {self.engine_name}")

    def read(self, image: Any) -> OCRResult:
        self._load()
        results = self._reader.readtext(image)
        if not results:
            return OCRResult("", 0.0)
        text, confidence = max(((item[1], float(item[2])) for item in results), key=lambda item: item[1])
        return OCRResult(format_plate_text(clean_plate_text(text)), confidence)