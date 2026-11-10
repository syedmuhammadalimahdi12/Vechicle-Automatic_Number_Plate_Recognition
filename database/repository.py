from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from database.connection import connect, create_database


class DetectionRepository:
    def __init__(self, url: str) -> None:
        self.url = url
        create_database(url)

    def count(self) -> int:
        connection = connect(self.url)
        try:
            return int(connection.execute("SELECT COUNT(*) FROM detections").fetchone()[0])
        finally:
            connection.close()

    def unique_plates(self) -> int:
        connection = connect(self.url)
        try:
            return int(connection.execute("SELECT COUNT(DISTINCT plate_number) FROM detections").fetchone()[0])
        finally:
            connection.close()

    def recent(self, limit: int = 8) -> list[dict[str, object]]:
        connection = connect(self.url)
        try:
            rows = connection.execute(
                "SELECT plate_number, vehicle_type, ocr_confidence, detected_at "
                "FROM detections ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        finally:
            connection.close()
        return [dict(row) for row in rows]

    def save(self, plate_number: str, vehicle_type: str, vehicle_confidence: float,
             plate_confidence: float, ocr_confidence: float, image_path: str = "",
             camera_id: str = "") -> None:
        detected_at = datetime.now().isoformat(timespec="seconds")
        connection = connect(self.url)
        try:
            connection.execute(
                "INSERT INTO detections (plate_number, vehicle_type, vehicle_confidence, "
                "plate_confidence, ocr_confidence, image_path, camera_id, detected_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (plate_number, vehicle_type, vehicle_confidence, plate_confidence,
                 ocr_confidence, image_path, camera_id, detected_at),
            )
            connection.commit()
        finally:
            connection.close()

    def seen_recently(self, plate_number: str, seconds: int) -> bool:
        threshold = datetime.now() - timedelta(seconds=seconds)
        connection = connect(self.url)
        try:
            row = connection.execute(
                "SELECT detected_at FROM detections WHERE plate_number = ? "
                "ORDER BY id DESC LIMIT 1", (plate_number,)
            ).fetchone()
        finally:
            connection.close()
        if not row:
            return False
        return datetime.fromisoformat(row[0]) >= threshold