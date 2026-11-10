from pathlib import Path

from database.repository import DetectionRepository


def test_detection_persistence(tmp_path: Path) -> None:
    repository = DetectionRepository(f"sqlite:///{tmp_path / 'anpr.db'}")
    repository.save("ABC-1234", "Car", 0.9, 0.8, 0.95)
    assert repository.count() == 1
    assert repository.unique_plates() == 1
    assert repository.recent()[0]["plate_number"] == "ABC-1234"