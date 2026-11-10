from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from detection.yolo_detector import BoundingBox, YOLODetector
from ocr.ocr_engine import OCREngine, OCRResult
from ocr.preprocessing import prepare_plate


@dataclass(frozen=True)
class PlateDetection:
    vehicle: BoundingBox | None
    plate: BoundingBox
    ocr: OCRResult


@dataclass(frozen=True)
class ProcessingReport:
    detections: list[PlateDetection]
    vehicle_count: int
    plate_count: int
    associated_plate_count: int


class ImageProcessor:
    def __init__(self, vehicle_model: str, plate_model: str, vehicle_confidence: float,
                 plate_confidence: float, ocr_engine: OCREngine) -> None:
        self.vehicle_detector = YOLODetector(vehicle_model, vehicle_confidence)
        self.plate_detector = YOLODetector(plate_model, plate_confidence)
        self.ocr_engine = ocr_engine
        self.last_report = ProcessingReport([], 0, 0, 0)

    def process(self, path: str) -> list[PlateDetection]:
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError("OpenCV is not installed. Install requirements.txt first.") from error
        image = cv2.imread(path)
        if image is None:
            raise ValueError(f"Unable to read image: {path}")
        return self.process_frame(image)

    def process_frame(self, image: Any) -> list[PlateDetection]:
        vehicles = self.vehicle_detector.predict(image)
        plates = self.plate_detector.predict(image)
        if not plates:
            plates = self.plate_detector.predict(image, confidence=max(0.15, self.plate_detector.confidence * 0.6))
        detections: list[PlateDetection] = []
        associated_count = 0
        for plate in plates:
            vehicle = self._owning_vehicle(plate, vehicles)
            if vehicle is not None:
                associated_count += 1
            crop = image[plate.y1:plate.y2, plate.x1:plate.x2]
            prepared_result = self.ocr_engine.read(prepare_plate(crop))
            raw_result = self.ocr_engine.read(crop) if not prepared_result.text else prepared_result
            result = raw_result if raw_result.confidence > prepared_result.confidence else prepared_result
            detections.append(PlateDetection(vehicle, plate, result))
        self.last_report = ProcessingReport(detections, len(vehicles), len(plates), associated_count)
        return detections

    @staticmethod
    def _owning_vehicle(plate: BoundingBox, vehicles: list[BoundingBox]) -> BoundingBox | None:
        center_x = (plate.x1 + plate.x2) / 2
        center_y = (plate.y1 + plate.y2) / 2
        matches = [vehicle for vehicle in vehicles if vehicle.x1 <= center_x <= vehicle.x2 and vehicle.y1 <= center_y <= vehicle.y2]
        return max(matches, key=lambda box: (box.x2 - box.x1) * (box.y2 - box.y1), default=None)