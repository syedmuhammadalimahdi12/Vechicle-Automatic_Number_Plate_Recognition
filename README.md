# AI ANPR

Professional desktop foundation for automatic number plate recognition using Python, OpenCV, Ultralytics YOLO, OCR, and PySide6.

## Architecture

The project uses a two-stage detection design: a general vehicle detector and a dedicated license-plate detector. Plate crops go through OpenCV preprocessing, OCR normalization, configurable validation, duplicate suppression, and persistence. Models are lazy-loaded and never initialized inside a frame loop.

The included Ultralytics `yolo11n.pt` model is suitable for vehicle classes such as car, motorcycle, bus, and truck. It does **not** detect license plates. A dedicated license-plate `.pt` model must be supplied separately at `models/license_plate.pt`; the application intentionally does not invent or bundle one.

## Install on Windows

Use Python 3.10 or 3.11 for the broadest computer-vision compatibility:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Models

Create `models/` and place a compatible plate detector at `models/license_plate.pt`. Ultralytics downloads `yolo11n.pt` on first use when configured as shown. For production, download model weights only from a source you trust and verify its license.

## Database and configuration

The default development database is local SQLite at `data/anpr.db`, requiring no server setup. For MySQL, create `anpr_db` and set `ANPR_DATABASE_URL` or change `database.url` in `config/config.yaml` to a `mysql+pymysql://...` URL. The schema is created on startup for the supported SQLite path.

Thresholds, frame skipping, duplicate interval, OCR engine, model paths, and evidence behavior live in `config/config.yaml`.

## Run

```powershell
python main.py
```

The dashboard opens with operational metrics backed by the database. Image, camera, video, history, analytics, and settings pages are structured in the same window; the next integration step is to connect their workers to the `YOLODetector` and `OCREngine` services.

## Verify

```powershell
pytest -q
```

The test suite covers OCR cleaning and validation, duplicate event suppression, and database insertion/query behavior. Missing model weights or unavailable cameras are surfaced as setup/runtime errors rather than fake detections.