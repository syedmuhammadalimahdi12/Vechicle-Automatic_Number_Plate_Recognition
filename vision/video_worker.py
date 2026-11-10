from __future__ import annotations

import time

from PySide6.QtCore import QMutex, QThread, Signal
from PySide6.QtGui import QImage

from ocr.ocr_engine import OCREngine
from vision.image_processor import ImageProcessor


class VideoWorker(QThread):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    stats_changed = Signal(int, int, int, float)
    error = Signal(str)

    def __init__(self, path: str, processor: ImageProcessor, frame_skip: int = 2) -> None:
        super().__init__()
        self.path = path
        self.processor = processor
        self.frame_skip = max(1, frame_skip)
        self._running = True
        self._paused = False
        self._mutex = QMutex()

    def stop(self) -> None:
        self._running = False
        self.wait(5000)

    def pause(self) -> None:
        self._mutex.lock()
        self._paused = True
        self._mutex.unlock()
        self.status_changed.emit("PAUSED")

    def resume(self) -> None:
        self._mutex.lock()
        self._paused = False
        self._mutex.unlock()
        self.status_changed.emit("PROCESSING")

    def _is_paused(self) -> bool:
        self._mutex.lock()
        paused = self._paused
        self._mutex.unlock()
        return paused

    def run(self) -> None:
        try:
            import cv2
        except ImportError:
            self.error.emit("OpenCV is not installed. Run: pip install -r requirements.txt")
            return

        capture = cv2.VideoCapture(self.path)
        if not capture.isOpened():
            capture.release()
            self.error.emit(f"Unable to open video: {self.path}")
            return

        frame_number = 0
        vehicle_total = 0
        plate_total = 0
        unique_plates: set[str] = set()
        started = time.monotonic()
        self.status_changed.emit("PROCESSING")
        try:
            while self._running:
                if self._is_paused():
                    self.msleep(50)
                    continue
                ok, frame = capture.read()
                if not ok:
                    break
                frame_number += 1
                if frame_number % self.frame_skip != 0:
                    continue
                detections = self.processor.process_frame(frame)
                vehicle_total += self.processor.last_report.vehicle_count
                plate_total += self.processor.last_report.plate_count
                unique_plates.update(item.ocr.text for item in detections if item.ocr.text)
                annotated = self._annotate(frame, detections)
                rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                height, width, channels = rgb.shape
                image = QImage(rgb.data, width, height, channels * width, QImage.Format_RGB888).copy()
                self.frame_ready.emit(image)
                elapsed = max(0.001, time.monotonic() - started)
                self.stats_changed.emit(vehicle_total, plate_total, len(unique_plates), frame_number / elapsed)
        except Exception as error:
            self.error.emit(f"Video processing failed: {error}")
        finally:
            capture.release()
            self.status_changed.emit("STOPPED")

    @staticmethod
    def _annotate(frame, detections):
        import cv2
        output = frame.copy()
        for item in detections:
            if item.vehicle:
                vehicle = item.vehicle
                cv2.rectangle(output, (vehicle.x1, vehicle.y1), (vehicle.x2, vehicle.y2), (255, 170, 45), 2)
            plate = item.plate
            cv2.rectangle(output, (plate.x1, plate.y1), (plate.x2, plate.y2), (80, 235, 170), 3)
            label = item.ocr.text or "PLATE"
            cv2.putText(output, label, (plate.x1, max(20, plate.y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 235, 170), 2)
        return output