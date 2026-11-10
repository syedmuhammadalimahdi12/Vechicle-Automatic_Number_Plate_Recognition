from ocr.text_processing import clean_plate_text, format_plate_text, validate_plate_text


def test_cleaning_and_formatting() -> None:
    assert clean_plate_text(" lea 1234 ") == "LEA1234"
    assert format_plate_text("lea 1234") == "LEA-1234"


def test_flexible_validation() -> None:
    assert validate_plate_text("ABC-1234")
    assert not validate_plate_text("--")