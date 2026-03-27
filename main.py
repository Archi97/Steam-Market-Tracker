import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from app.main_window import MainWindow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_qss() -> str:
    path = os.path.join(BASE_DIR, "styles", "dark.qss")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    qss = load_qss()
    if qss:
        app.setStyleSheet(qss)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
