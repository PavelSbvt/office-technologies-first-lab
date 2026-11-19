import os
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox, QMainWindow, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from src.core.processor import process
from src.core.charts import build_all_figures, save_all_figures
from utils.utils import format_time
from gui.ui.ui_main_window import Ui_window
from utils.output_rich import Rich


class FigureWindow(QMainWindow):
    def __init__(self, name, fig, parent=None):
        super().__init__(parent)
        self.setWindowTitle(name)
        self.resize(800, 600)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        self.setCentralWidget(central)


class MainWindow(QWidget):
    """Класс окна"""

    def __init__(self):
        super().__init__()

        self.records = []  # обработанные записи
        self.summary = {}  # сводные показатели
        self.figures = []  # построенные фигуры [(имя, fig), ...]
        self.figure_windows = []  # чтобы окна не собирались

        self.path_var = Path("resources/files/Kingston-SD-32G.bbl").as_posix()

        self.setObjectName("main_window")

        Rich.enter_log("Показ окна приложения.")

        self.ui = Ui_window()
        self.ui.setupUi(self)

        self.run_button_path = Path("resources/images/icons/run-button.png")

        self.ui.run_button.setStyleSheet(f"""
                    QPushButton {{
                        background-image: url({self.run_button_path.as_posix()});
                        background-repeat: no-repeat;
                        background-position: center;
                        border: none;
                        background-color: transparent;
                        border-radius: 5px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.08);
                    }}
                    QPushButton:pressed {{
                        background-color: rgba(255, 255, 255, 0.15);
                    }}
                """)

        self.ui.run_button.clicked.connect(self.on_process)
        self.ui.button_rewiev.clicked.connect(self.choose_file)
        self.ui.button_save_graphics_to_png.clicked.connect(self.on_save)

        self.ui.line_for_path.setText(self.path_var)

        self.ui.list_widget_for_show_graphics.itemDoubleClicked.connect(
            self.on_double_click)

    def choose_file(self):
        """
        Открывает диалог выбора файла.
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите лог-файл badblocks",
            "",
            "Логи badblocks (*.bbl *.log *.txt);;Все файлы (*)")
        if path:
            self.ui.line_for_path.setText(path)

    def on_process(self):
        """
        Читает файл, обрабатывает данные и строит графики.
        """
        path = self.ui.line_for_path.text()
        if not os.path.exists(path):
            QMessageBox.critical(self, "Ошибка", "Файл не найден: {}".format(path))
            return

        try:
            records, summary = process(path)
        except Exception as exc:
            QMessageBox.critical(
                self, "Ошибка",
                "Не удалось обработать файл:\n{}".format(exc))
            return

        if len(records) < 3:
            QMessageBox.warning(
                self, "Мало данных",
                "В файле найдено меньше трёх корректных записей прогресса.")
            return

        self.records = records
        self.summary = summary

        try:
            self.figures = build_all_figures(records)
        except Exception as exc:
            self.figures = []
            QMessageBox.critical(
                self, "Ошибка",
                "Не удалось построить графики:\n{}".format(exc))

        self.ui.list_widget_for_show_graphics.clear()
        for name, _fig in self.figures:
            self.ui.list_widget_for_show_graphics.addItem(name)

        self.show_summary()
        self.ui.label_for_log.setText(
            "Загружено записей: {}. Время проверки: {}. Ошибок: {}.".format(
                summary["count"],
                format_time(summary["total_time"]),
                summary["errors"]))

    def show_summary(self):
        """Показывает сводку по данным в текстовом поле."""
        s = self.summary
        text = (
            "Сводка по файлу\n"
            "================\n"
            "Корректных записей: {count}\n"
            "Полное время проверки: {time} ({total_time} сек)\n"
            "Средняя скорость: {avg:.2f} МБ/с\n"
            "Минимальная скорость: {min:.2f} МБ/с\n"
            "Максимальная скорость: {max:.2f} МБ/с\n"
            "Найдено ошибок: {errors}\n\n"
            "Двойной клик по названию графика слева - открыть окно с "
            "графиком.\n".format(
                count=s["count"],
                time=format_time(s["total_time"]),
                total_time=s["total_time"],
                avg=s["avg_speed"],
                min=s["min_speed"],
                max=s["max_speed"],
                errors=s["errors"]))
        self.ui.log_widget.setPlainText(text)

    def on_double_click(self, item):
        """Открывает график, выбранный двойным кликом в списке."""
        index = self.ui.list_widget_for_show_graphics.row(item)
        self.show_figure(index)

    def show_figure(self, index):
        """Открывает окно matplotlib с выбранным графиком."""
        if index < 0 or index >= len(self.figures):
            return
        name, fig = self.figures[index]
        try:
            window = FigureWindow(name, fig, parent=self)
            window.show()
            # сохраняем ссылку, чтобы окно не было уничтожено сборщиком мусора
            self.figure_windows.append(window)
        except Exception as exc:
            QMessageBox.critical(
                self, "Ошибка",
                "Не удалось показать график:\n{}".format(exc))

    def on_save(self):
        """Сохраняет все графики в папку output рядом с программой."""
        if len(self.figures) == 0:
            QMessageBox.warning(self, "Нет данных",
                                "Сначала обработайте файл.")
            return

        base_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        folder = os.path.join(base_dir, "output")
        paths = save_all_figures(self.figures, folder)

        message = "Графики сохранены:\n"
        for name, path in paths:
            message += "- {} -> {}\n".format(name, path)
        QMessageBox.information(self, "Готово", message)
