import os
import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def get_default_path():
    """Возвращает путь к демонстрационному файлу данных."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "resource", "files", "Kingston-SD-32G.bbl")


def main():
    path = ""
    if path == "":
        path = get_default_path()


if __name__ == "__main__":
    App = QApplication(sys.argv)

    Win = MainWindow()
    Win.show()

    sys.exit(App.exec())
