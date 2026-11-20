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
            # Распаковываем данные для двух этапов
            (write_smoothed, write_summary), (read_smoothed, read_summary) = process(path)
        except Exception as exc:
            QMessageBox.critical(
                self, "Ошибка",
                "Не удалось обработать файл:\n{}".format(exc))
            return

        # Проверяем, что данных достаточно хотя бы на одном из этапов
        total_records = len(write_smoothed) + len(read_smoothed)
        if total_records < 3:
            QMessageBox.warning(
                self, "Мало данных",
                "В файле найдено меньше трёх корректных записей прогресса.")
            return

        # Сохраняем данные и сводки в атрибуты класса
        self.write_records = write_smoothed
        self.read_records = read_smoothed
        self.write_summary = write_summary
        self.read_summary = read_summary

        try:
            # Передаем ДВА списка в функцию построения
            self.figures = build_all_figures(write_smoothed, read_smoothed)
        except Exception as exc:
            self.figures = []
            QMessageBox.critical(
                self, "Ошибка",
                "Не удалось построить графики:\n{}".format(exc))

        self.ui.list_widget_for_show_graphics.clear()
        for name, _fig in self.figures:
            self.ui.list_widget_for_show_graphics.addItem(name)

        # Вызываем показ сводки (она возьмет данные из self.write_summary и self.read_summary)
        self.show_summary()

        # Формируем текст статуса (время и ошибки - общие из второй фазы,
        # так как время там накопленное, а ошибки суммарные)
        total_time = read_summary["total_time"] if read_summary else write_summary["total_time"]
        total_errors = write_summary["errors"] + read_summary["errors"] if read_summary else write_summary["errors"]

        self.ui.label_for_log.setText(
            "Загружено записей: {} (Запись: {}, Чтение: {}). Время: {}. Ошибок: {}.".format(
                total_records,
                len(write_smoothed),
                len(read_smoothed),
                format_time(total_time),
                total_errors))

    def show_summary(self):
        """Показывает сводку по данным в текстовом поле."""
        w = getattr(self, "write_summary", {})
        r = getattr(self, "read_summary", {})

        if not w and not r:
            self.ui.log_widget.setPlainText("Нет данных для отображения.")
            return

        # Безопасно извлекаем значения с дефолтами, чтобы не упасть, если одно из полей пустое
        w_count = w.get("count", 0)
        r_count = r.get("count", 0)
        w_avg = w.get("avg_speed", 0.0)
        r_avg = r.get("avg_speed", 0.0)
        w_min = w.get("min_speed", 0.0)
        r_min = r.get("min_speed", 0.0)
        w_max = w.get("max_speed", 0.0)
        r_max = r.get("max_speed", 0.0)
        w_err = w.get("errors", 0)
        r_err = r.get("errors", 0)

        # Для времени берем максимум из двух (так как проверка идет последовательно)
        total_time = max(w.get("total_time", 0), r.get("total_time", 0))
        total_count = w_count + r_count
        total_errors = w_err + r_err

        text = (
            "Сводка по файлу\n"
            "\n"
            "Корректных записей: {total_count} (Запись: {w_count}, Чтение: {r_count})\n"
            "Полное время проверки: {time} ({total_time} сек)\n\n"
            "ЭТАП ЗАПИСИ\n"
            "Средняя скорость: {w_avg:.2f} МБ/с\n"
            "Минимальная скорость: {w_min:.2f} МБ/с\n"
            "Максимальная скорость: {w_max:.2f} МБ/с\n\n"
            "ЭТАП ЧТЕНИЯ\n"
            "Средняя скорость: {r_avg:.2f} МБ/с\n"
            "Минимальная скорость: {r_min:.2f} МБ/с\n"
            "Максимальная скорость: {r_max:.2f} МБ/с\n\n"
            "Найдено ошибок: {total_errors}\n\n"
            "Двойной клик по названию графика слева - открыть окно с графиком.\n".format(
                total_count=total_count,
                w_count=w_count,
                r_count=r_count,
                time=format_time(total_time),
                total_time=total_time,
                w_avg=w_avg,
                w_min=w_min,
                w_max=w_max,
                r_avg=r_avg,
                r_min=r_min,
                r_max=r_max,
                total_errors=total_errors
            ))
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
