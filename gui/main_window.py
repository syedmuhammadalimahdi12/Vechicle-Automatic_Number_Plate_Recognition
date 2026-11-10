from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from config.settings import Settings
from database.repository import DetectionRepository
from ocr.ocr_engine import OCREngine
from vision.image_processor import ImageProcessor
from vision.camera_worker import CameraWorker
from vision.video_worker import VideoWorker


STYLE = """
QMainWindow, QWidget { background: #0c1118; color: #e8eef5; font-family: Segoe UI; }
QFrame#sidebar { background: #111923; border-right: 1px solid #22303e; }
QLabel#brand { color: #6ee7b7; font-size: 22px; font-weight: 700; padding: 20px 18px; }
QLabel#muted { color: #8fa2b5; }
QLabel#title { font-size: 28px; font-weight: 700; }
QPushButton { background: #1b2937; border: 1px solid #2a4052; border-radius: 6px; padding: 10px 14px; color: #edf5fb; }
QPushButton:hover { background: #263b4c; border-color: #6ee7b7; }
QPushButton#active { background: #123c3b; color: #6ee7b7; border-color: #2e9d87; }
QFrame#card { background: #141f2b; border: 1px solid #233445; border-radius: 8px; }
QLabel#metric { color: #6ee7b7; font-size: 28px; font-weight: 700; }
QLabel#section { color: #d7e3ed; font-size: 16px; font-weight: 600; }
QLabel#statusReady { color: #6ee7b7; font-weight: 700; }
QLabel#statusMissing { color: #f6b26b; font-weight: 700; }
QTableWidget { background: #121c26; border: 1px solid #233445; gridline-color: #233445; }
QHeaderView::section { background: #1b2937; color: #9fb3c5; padding: 8px; border: 0; }
QListWidget { border: 0; background: transparent; padding: 8px; }
QListWidget::item { padding: 12px 10px; border-radius: 5px; }
QListWidget::item:selected { background: #123c3b; color: #6ee7b7; }
"""


class MetricCard(QFrame):
    def __init__(self, label: str, value: str) -> None:
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        caption = QLabel(label.upper())
        caption.setObjectName("muted")
        self.number = QLabel(value)
        self.number.setObjectName("metric")
        layout.addWidget(caption)
        layout.addWidget(self.number)

    def set_value(self, value: str) -> None:
        self.number.setText(value)


class DashboardPage(QWidget):
    def __init__(self, repository: DetectionRepository, settings: Settings) -> None:
        super().__init__()
        self.repository = repository
        self.layout = QVBoxLayout(self)
        title = QLabel("Operations overview")
        title.setObjectName("title")
        self.layout.addWidget(title)
        subtitle = QLabel("Real-time recognition telemetry and recent events")
        subtitle.setObjectName("muted")
        self.layout.addWidget(subtitle)
        cards = QHBoxLayout()
        self.vehicle_card = MetricCard("Total detections", "0")
        self.plate_card = MetricCard("Unique plates", "0")
        self.status_card = MetricCard("System status", "ONLINE")
        for card in (self.vehicle_card, self.plate_card, self.status_card):
            cards.addWidget(card)
        self.layout.addLayout(cards)
        model_panel = QFrame()
        model_panel.setObjectName("card")
        model_layout = QVBoxLayout(model_panel)
        model_title = QLabel("Inference readiness")
        model_title.setObjectName("section")
        model_layout.addWidget(model_title)
        self.vehicle_status = self._model_status("Vehicle model", settings.models.vehicle, model_layout)
        self.plate_status = self._model_status("Plate model", settings.models.license_plate, model_layout)
        self.layout.addWidget(model_panel)
        events_title = QLabel("Recent recognition events")
        events_title.setObjectName("section")
        self.layout.addWidget(events_title)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["PLATE", "VEHICLE", "OCR", "DETECTED"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)
        self.refresh()

    @staticmethod
    def _model_status(label: str, path: str, layout: QVBoxLayout) -> QLabel:
        row = QHBoxLayout()
        name = QLabel(label)
        name.setObjectName("muted")
        detail = QLabel(Path(path).name)
        detail.setObjectName("muted")
        status = QLabel("READY" if Path(path).exists() else "MISSING")
        status.setObjectName("statusReady" if Path(path).exists() else "statusMissing")
        row.addWidget(name)
        row.addWidget(detail)
        row.addStretch()
        row.addWidget(status)
        layout.addLayout(row)
        return status

    def refresh(self) -> None:
        self.vehicle_card.set_value(str(self.repository.count()))
        self.plate_card.set_value(str(self.repository.unique_plates()))
        rows = self.repository.recent()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, key in enumerate(("plate_number", "vehicle_type", "ocr_confidence", "detected_at")):
                value = row[key]
                text = f"{float(value):.0%}" if key == "ocr_confidence" else str(value)
                self.table.setItem(row_index, column, QTableWidgetItem(text))


class LiveCameraPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.worker: CameraWorker | None = None
        layout = QVBoxLayout(self)
        title = QLabel("Live camera")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Monitor a connected camera with a responsive preview stream")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Camera source"))
        self.source = QComboBox()
        self.source.addItems(["Camera 0", "Camera 1", "Camera 2"])
        toolbar.addWidget(self.source)
        self.start_button = QPushButton("Start camera")
        self.start_button.clicked.connect(self.start_camera)
        toolbar.addWidget(self.start_button)
        self.stop_button = QPushButton("Stop camera")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_camera)
        toolbar.addWidget(self.stop_button)
        toolbar.addStretch()
        self.status = QLabel("OFFLINE")
        self.status.setObjectName("statusMissing")
        toolbar.addWidget(self.status)
        self.fps = QLabel("0.0 FPS")
        self.fps.setObjectName("muted")
        toolbar.addWidget(self.fps)
        layout.addLayout(toolbar)

        content = QHBoxLayout()
        self.preview = QLabel("Camera preview\n\nPress Start camera to begin")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(700, 430)
        self.preview.setStyleSheet("background: #071018; border: 1px solid #233445; color: #8fa2b5;")
        content.addWidget(self.preview, 3)
        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        heading = QLabel("Detection monitor")
        heading.setObjectName("section")
        panel_layout.addWidget(heading)
        panel_layout.addWidget(QLabel("Vehicle\nWaiting for stream", objectName="muted"))
        panel_layout.addWidget(QLabel("License plate\nWaiting for inference", objectName="muted"))
        panel_layout.addWidget(QLabel("OCR confidence\n--", objectName="muted"))
        panel_layout.addStretch()
        content.addWidget(panel, 1)
        layout.addLayout(content)

    def start_camera(self) -> None:
        self.stop_camera()
        self.worker = CameraWorker(self.source.currentIndex())
        self.worker.frame_ready.connect(self._show_frame)
        self.worker.status_changed.connect(self._set_status)
        self.worker.error.connect(self._show_error)
        self.worker.fps_changed.connect(lambda value: self.fps.setText(f"{value:.1f} FPS"))
        self.worker.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_camera(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        self.worker = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._set_status("OFFLINE")

    def _show_frame(self, image) -> None:
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _set_status(self, value: str) -> None:
        self.status.setText(value)
        self.status.setObjectName("statusReady" if value == "LIVE" else "statusMissing")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _show_error(self, message: str) -> None:
        self.stop_camera()
        QMessageBox.warning(self, "Camera unavailable", message)


class ImageDetectionPage(QWidget):
    def __init__(self, settings: Settings, repository: DetectionRepository) -> None:
        super().__init__()
        self.settings = settings
        self.repository = repository
        self.image_path = ""
        self.detections = []
        self.original = None
        layout = QVBoxLayout(self)
        title = QLabel("Image detection")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Upload a vehicle image to detect, highlight, and recognize license plates")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        actions = QHBoxLayout()
        open_button = QPushButton("Open image")
        open_button.clicked.connect(self.open_image)
        actions.addWidget(open_button)
        self.process_button = QPushButton("Process image")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.process_image)
        actions.addWidget(self.process_button)
        self.save_button = QPushButton("Save detections")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_detections)
        actions.addWidget(self.save_button)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        actions.addWidget(clear_button)
        actions.addStretch()
        self.status = QLabel("Select an image to begin")
        self.status.setObjectName("muted")
        actions.addWidget(self.status)
        layout.addLayout(actions)

        content = QHBoxLayout()
        self.preview = QLabel("No image selected")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(680, 420)
        self.preview.setStyleSheet("background: #071018; border: 1px solid #233445; color: #8fa2b5;")
        content.addWidget(self.preview, 3)
        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        heading = QLabel("Recognition results")
        heading.setObjectName("section")
        panel_layout.addWidget(heading)
        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(["RECOGNIZED PLATE", "OCR CONF.", "PLATE CONF.", "VEHICLE"])
        self.result_table.horizontalHeader().setStretchLastSection(True)
        panel_layout.addWidget(self.result_table)
        self.summary = QLabel("No detections yet")
        self.summary.setObjectName("muted")
        panel_layout.addWidget(self.summary)
        content.addWidget(panel, 2)
        layout.addLayout(content)

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select image", str(Path.home()), "Images (*.jpg *.jpeg *.png)")
        if not path:
            return
        try:
            import cv2
            image = cv2.imread(path)
            if image is None:
                raise ValueError(f"Unable to read image: {path}")
            self.image_path = path
            self.original = image
            self.detections = []
            self._display_image(image)
            self.process_button.setEnabled(True)
            self.save_button.setEnabled(False)
            self.status.setText(f"Loaded: {Path(path).name}")
            self.summary.setText("Ready to process")
        except (ImportError, ValueError) as error:
            QMessageBox.warning(self, "Image unavailable", str(error))

    def process_image(self) -> None:
        if not self.image_path:
            return
        self.process_button.setEnabled(False)
        self.status.setText("Running vehicle, plate, and OCR inference...")
        try:
            processor = ImageProcessor(
                self.settings.models.vehicle,
                self.settings.models.license_plate,
                self.settings.detection.vehicle_confidence,
                self.settings.detection.plate_confidence,
                OCREngine(self.settings.ocr.engine, self.settings.ocr.languages),
            )
            self.detections = processor.process(self.image_path)
            self._display_image(self._annotated_image(self.original, self.detections))
            self._populate_results(processor.last_report)
            self.save_button.setEnabled(any(item.ocr.text for item in self.detections))
            self.status.setText("Detection complete")
        except (RuntimeError, FileNotFoundError, ValueError) as error:
            self.status.setText("Detection failed")
            QMessageBox.warning(self, "Processing unavailable", str(error))
        finally:
            self.process_button.setEnabled(True)

    def _annotated_image(self, image, detections):
        import cv2
        output = image.copy()
        for item in detections:
            if item.vehicle:
                vehicle = item.vehicle
                cv2.rectangle(output, (vehicle.x1, vehicle.y1), (vehicle.x2, vehicle.y2), (255, 170, 45), 2)
                cv2.putText(output, f"{vehicle.label} {vehicle.confidence:.0%}", (vehicle.x1, max(24, vehicle.y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 190, 70), 2)
            plate = item.plate
            cv2.rectangle(output, (plate.x1, plate.y1), (plate.x2, plate.y2), (80, 235, 170), 3)
            label = item.ocr.text or "PLATE DETECTED"
            cv2.rectangle(output, (plate.x1, max(0, plate.y1 - 32)), (plate.x1 + max(170, len(label) * 13), plate.y1), (80, 235, 170), -1)
            cv2.putText(output, label, (plate.x1 + 6, max(22, plate.y1 - 9)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (5, 20, 20), 2)
        return output

    def _display_image(self, image) -> None:
        import cv2
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        qimage = QImage(rgb.data, width, height, channels * width, QImage.Format_RGB888).copy()
        self.preview.setPixmap(QPixmap.fromImage(qimage).scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _populate_results(self, report) -> None:
        self.result_table.setRowCount(len(report.detections))
        recognized = 0
        for row, item in enumerate(report.detections):
            values = (item.ocr.text or "Unreadable", f"{item.ocr.confidence:.0%}", f"{item.plate.confidence:.0%}", item.vehicle.label if item.vehicle else "Unknown")
            recognized += bool(item.ocr.text)
            for column, value in enumerate(values):
                self.result_table.setItem(row, column, QTableWidgetItem(str(value)))
        self.summary.setText(f"Vehicles: {report.vehicle_count}   Plates: {report.plate_count}   Recognized: {recognized}")

    def save_detections(self) -> None:
        saved = 0
        for item in self.detections:
            if not item.ocr.text or self.repository.seen_recently(item.ocr.text, self.settings.processing.duplicate_interval):
                continue
            self.repository.save(item.ocr.text, item.vehicle.label if item.vehicle else "Unknown", item.vehicle.confidence if item.vehicle else 0.0, item.plate.confidence, item.ocr.confidence, self.image_path)
            saved += 1
        self.save_button.setEnabled(False)
        QMessageBox.information(self, "Detections saved", f"Saved {saved} unique detection(s) to the database.")

    def clear(self) -> None:
        self.image_path = ""
        self.original = None
        self.detections = []
        self.preview.clear()
        self.preview.setText("No image selected")
        self.result_table.setRowCount(0)
        self.summary.setText("No detections yet")
        self.status.setText("Select an image to begin")
        self.process_button.setEnabled(False)
        self.save_button.setEnabled(False)


class VideoDetectionPage(QWidget):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.path = ""
        self.worker: VideoWorker | None = None
        layout = QVBoxLayout(self)
        title = QLabel("Video detection")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Process vehicle footage with configurable frame skipping and OCR")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        actions = QHBoxLayout()
        open_button = QPushButton("Open video")
        open_button.clicked.connect(self.open_video)
        actions.addWidget(open_button)
        self.process_button = QPushButton("Process video")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.process_video)
        actions.addWidget(self.process_button)
        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        actions.addWidget(self.pause_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_video)
        actions.addWidget(self.stop_button)
        actions.addStretch()
        self.status = QLabel("Select a video to begin")
        self.status.setObjectName("muted")
        actions.addWidget(self.status)
        layout.addLayout(actions)

        content = QHBoxLayout()
        self.preview = QLabel("No video selected")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(700, 430)
        self.preview.setStyleSheet("background: #071018; border: 1px solid #233445; color: #8fa2b5;")
        content.addWidget(self.preview, 3)
        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        heading = QLabel("Processing statistics")
        heading.setObjectName("section")
        panel_layout.addWidget(heading)
        self.fps = QLabel("FPS\n0.0", objectName="muted")
        self.vehicles = QLabel("Vehicles\n0", objectName="muted")
        self.plates = QLabel("Plates\n0", objectName="muted")
        self.unique = QLabel("Unique plates\n0", objectName="muted")
        for label in (self.fps, self.vehicles, self.plates, self.unique):
            panel_layout.addWidget(label)
        panel_layout.addStretch()
        content.addWidget(panel, 1)
        layout.addLayout(content)

    def open_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select video", str(Path.home()), "Videos (*.mp4 *.avi *.mov *.mkv)")
        if path:
            self.stop_video()
            self.path = path
            self.preview.setText(f"Loaded video:\n{Path(path).name}\n\nPress Process video")
            self.process_button.setEnabled(True)
            self.status.setText(f"Loaded: {Path(path).name}")

    def process_video(self) -> None:
        if not self.path:
            return
        self.stop_video()
        try:
            processor = ImageProcessor(
                self.settings.models.vehicle,
                self.settings.models.license_plate,
                self.settings.detection.vehicle_confidence,
                self.settings.detection.plate_confidence,
                OCREngine(self.settings.ocr.engine, self.settings.ocr.languages),
            )
            self.worker = VideoWorker(self.path, processor, self.settings.processing.frame_skip)
            self.worker.frame_ready.connect(self.show_frame)
            self.worker.status_changed.connect(self.set_status)
            self.worker.stats_changed.connect(self.update_stats)
            self.worker.error.connect(self.show_error)
            self.worker.finished.connect(self.processing_finished)
            self.worker.start()
            self.process_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
        except (RuntimeError, FileNotFoundError, ValueError) as error:
            QMessageBox.warning(self, "Video unavailable", str(error))

    def toggle_pause(self) -> None:
        if not self.worker:
            return
        if self.pause_button.text() == "Pause":
            self.worker.pause()
            self.pause_button.setText("Resume")
        else:
            self.worker.resume()
            self.pause_button.setText("Pause")

    def stop_video(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        self.worker = None
        self.pause_button.setText("Pause")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.process_button.setEnabled(bool(self.path))

    def show_frame(self, image: QImage) -> None:
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_status(self, status: str) -> None:
        self.status.setText(status)

    def update_stats(self, vehicles: int, plates: int, unique: int, fps: float) -> None:
        self.vehicles.setText(f"Vehicles\n{vehicles}")
        self.plates.setText(f"Plates\n{plates}")
        self.unique.setText(f"Unique plates\n{unique}")
        self.fps.setText(f"FPS\n{fps:.1f}")

    def processing_finished(self) -> None:
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.process_button.setEnabled(bool(self.path))
        self.worker = None

    def show_error(self, message: str) -> None:
        self.stop_video()
        QMessageBox.warning(self, "Video processing error", message)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.repository = DetectionRepository(settings.database.url)
        self.setWindowTitle("AI ANPR | Intelligent Plate Recognition")
        self.resize(1280, 760)
        self.setStyleSheet(STYLE)
        root = QWidget()
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        brand = QLabel("AI ANPR")
        brand.setObjectName("brand")
        side_layout.addWidget(brand)
        nav = QListWidget()
        nav.addItems(["Dashboard", "Live camera", "Image detection", "Video detection", "History", "Analytics", "Cameras", "Settings"])
        nav.setCurrentRow(0)
        nav.currentRowChanged.connect(self._switch_page)
        side_layout.addWidget(nav)
        footer = QLabel("●  SYSTEM ONLINE\n\nLocal inference ready")
        footer.setObjectName("muted")
        side_layout.addWidget(footer)
        shell.addWidget(sidebar)
        self.pages = QStackedWidget()
        self.dashboard = DashboardPage(self.repository, settings)
        self.pages.addWidget(self.dashboard)
        self.live_camera = LiveCameraPage()
        self.pages.addWidget(self.live_camera)
        self.image_detection = ImageDetectionPage(settings, self.repository)
        self.pages.addWidget(self.image_detection)
        self.video_detection = VideoDetectionPage(settings)
        self.pages.addWidget(self.video_detection)
        for label in ("History", "Analytics", "Cameras", "Settings"):
            self.pages.addWidget(self._placeholder(label))
        shell.addWidget(self.pages)
        self.setCentralWidget(root)

    def _switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    def _placeholder(self, title: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        heading = QLabel(title)
        heading.setObjectName("title")
        layout.addWidget(heading)
        message = QLabel("This workspace is ready for the configured model and input source.")
        message.setObjectName("muted")
        layout.addWidget(message)
        if title == "Image detection":
            button = QPushButton("Open image")
            button.clicked.connect(self._open_image)
            layout.addWidget(button)
        layout.addStretch()
        return page

    def _open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select image", str(Path.home()), "Images (*.jpg *.jpeg *.png)")
        if not path:
            return
        try:
            processor = ImageProcessor(
                self.settings.models.vehicle,
                self.settings.models.license_plate,
                self.settings.detection.vehicle_confidence,
                self.settings.detection.plate_confidence,
                OCREngine(self.settings.ocr.engine, self.settings.ocr.languages),
            )
            detections = processor.process(path)
            recognized = [item.ocr.text for item in detections if item.ocr.text]
            report = processor.last_report
            if recognized:
                message = f"Recognized plates: {', '.join(recognized)}\n\nVehicles: {report.vehicle_count}\nPlates: {report.plate_count}\nOCR matches: {len(recognized)}"
            elif report.plate_count == 0:
                message = f"No license plate was detected.\n\nVehicles found: {report.vehicle_count}\n\nTry a clearer image with the full vehicle and plate visible."
            elif report.associated_plate_count == 0:
                message = f"A plate was detected, but it was not inside a detected vehicle.\n\nVehicles: {report.vehicle_count}\nPlates: {report.plate_count}"
            else:
                message = f"Plate detected, but OCR could not read its characters.\n\nVehicles: {report.vehicle_count}\nPlates: {report.plate_count}\nAssociated plates: {report.associated_plate_count}\n\nTry a sharper, larger plate crop."
            QMessageBox.information(self, "Image processed", message)
        except (RuntimeError, FileNotFoundError, ValueError) as error:
            QMessageBox.warning(self, "Processing unavailable", str(error))

    def closeEvent(self, event) -> None:
        self.live_camera.stop_camera()
        self.video_detection.stop_video()
        event.accept()