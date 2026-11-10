from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    label: str


class YOLODetector:
    """Lazy Ultralytics adapter. Model loading happens once on first inference."""

    def __init__(self, model_path: str, confidence: float = 0.4) -> None:
        self.model_path = Path(model_path)
        self.confidence = confidence
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        if not self.model_path.exists() and self.model_path.name != "yolo11n.pt":
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        try:
            from ultralytics import YOLO
        except ImportError as error:
            raise RuntimeError("Ultralytics is not installed. Install requirements.txt first.") from error
        self._model = YOLO(str(self.model_path))

    def predict(self, image: Any, confidence: float | None = None) -> list[BoundingBox]:
        self._load()
        results = self._model.predict(image, conf=confidence if confidence is not None else self.confidence, verbose=False)
        detections: list[BoundingBox] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                coordinates = [int(value) for value in box.xyxy[0].tolist()]
                class_id = int(box.cls[0])
                detections.append(BoundingBox(*coordinates, float(box.conf[0]), str(names[class_id])))
        return detections