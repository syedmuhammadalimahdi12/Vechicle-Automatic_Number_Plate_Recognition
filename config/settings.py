from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelSettings:
    vehicle: str = "models/yolo11n.pt"
    license_plate: str = "models/license_plate.pt"


@dataclass(frozen=True)
class OCRSettings:
    engine: str = "easyocr"
    languages: list[str] = field(default_factory=lambda: ["en"])


@dataclass(frozen=True)
class DetectionSettings:
    vehicle_confidence: float = 0.4
    plate_confidence: float = 0.4


@dataclass(frozen=True)
class ProcessingSettings:
    frame_skip: int = 2
    duplicate_interval: int = 10
    evidence_enabled: bool = True


@dataclass(frozen=True)
class DatabaseSettings:
    url: str = "sqlite:///data/anpr.db"


@dataclass(frozen=True)
class LoggingSettings:
    path: str = "logs/anpr.log"


@dataclass(frozen=True)
class UISettings:
    theme: str = "dark"
    region: str = "flexible"


@dataclass(frozen=True)
class Settings:
    models: ModelSettings = field(default_factory=ModelSettings)
    ocr: OCRSettings = field(default_factory=OCRSettings)
    detection: DetectionSettings = field(default_factory=DetectionSettings)
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    ui: UISettings = field(default_factory=UISettings)


def _read_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def load_settings(path: Path | None = None) -> Settings:
    if path:
        path = path.resolve()
    values = _read_mapping(path) if path else {}
    project_root = path.parent.parent if path else Path.cwd()
    model_values = dict(values.get("models", {}))
    defaults = ModelSettings()
    for key in ("vehicle", "license_plate"):
        model_path = Path(model_values.get(key, getattr(defaults, key)))
        model_values[key] = str(model_path if model_path.is_absolute() else project_root / model_path)
    return Settings(
        models=ModelSettings(**model_values),
        ocr=OCRSettings(**values.get("ocr", {})),
        detection=DetectionSettings(**values.get("detection", {})),
        processing=ProcessingSettings(**values.get("processing", {})),
        database=DatabaseSettings(**values.get("database", {})),
        logging=LoggingSettings(**values.get("logging", {})),
        ui=UISettings(**values.get("ui", {})),
    )