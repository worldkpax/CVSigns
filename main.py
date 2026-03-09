from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.settings import AppSettings
from ui.main_window import MainWindow


def load_app_settings() -> AppSettings:
    config_path = Path("config.json")
    if config_path.exists():
        try:
            return AppSettings.load(config_path)
        except Exception:
            return AppSettings()
    return AppSettings()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("CVSigns")
    app.setOrganizationName("CVSigns")

    window = MainWindow(load_app_settings())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
