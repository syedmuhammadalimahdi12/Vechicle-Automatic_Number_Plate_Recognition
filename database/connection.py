from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import urlparse


SCHEMA = """
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,
    vehicle_confidence REAL NOT NULL,
    plate_confidence REAL NOT NULL,
    ocr_confidence REAL NOT NULL,
    image_path TEXT,
    camera_id TEXT,
    detected_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_detections_plate ON detections(plate_number);
"""


def sqlite_path(url: str) -> Path:
    parsed = urlparse(url)
    path = Path(parsed.path.lstrip("/"))
    if parsed.netloc and not path.is_absolute():
        path = Path(parsed.netloc) / path
    return path


def create_database(url: str) -> None:
    if not url.startswith("sqlite"):
        return
    path = sqlite_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        connection.commit()
    finally:
        connection.close()


def connect(url: str) -> sqlite3.Connection:
    if not url.startswith("sqlite"):
        raise RuntimeError("MySQL connections require SQLAlchemy; configure a mysql+pymysql URL.")
    connection = sqlite3.connect(sqlite_path(url))
    connection.row_factory = sqlite3.Row
    return connection