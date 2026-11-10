from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class CameraWorker(QThread):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    error = Signal(str)
    fps_changed = Signal(float)

    def __init__(self, source: int = 0) -> None:
        super().__init__()
        self.source = source
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    def run(self) -> None:
        try:
            import cv2
        except ImportError:
            self.error.emit("OpenCV is not installed. Run: pip install -r requirements.txt")
            return

        capture = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            self.error.emit(f"Camera {self.source} could not be opened. Check the camera connection.")
            return

        self.status_changed.emit("LIVE")
        frame_count = 0
        started = time.monotonic()
        try:
            while self._running:
                ok, frame = capture.read()
                if not ok:
                    self.error.emit("Camera stopped returning frames.")
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channels = frame.shape
                image = QImage(frame.data, width, height, channels * width, QImage.Format_RGB888).copy()
                self.frame_ready.emit(image)
                frame_count += 1
                elapsed = time.monotonic() - started
                if elapsed > 0:
                    self.fps_changed.emit(frame_count / elapsed)
        finally:
            capture.release()
            self.status_changed.emit("OFFLINE")