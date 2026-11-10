from __future__ import annotations

import sys
from pathlib import Path

from config.settings import load_settings
from database.connection import create_database
from utils.logger import configure_logging


def main() -> int:
    root = Path(__file__).resolve().parent
    settings = load_settings(root / "config" / "config.yaml")
    configure_logging(root / settings.logging.path)
    create_database(settings.database.url)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is not installed. Run: pip install -r requirements.txt")
        return 1

    from gui.main_window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("AI ANPR")
    window = MainWindow(settings)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
