# -*- coding: utf-8 -*-
"""Графический интерфейс программы (gui.window).

Окно на Tkinter: выбор файла, кнопка обработки, список графиков.
При выборе графика он показывается во встроенном окне matplotlib.
Если построить графики не удалось (например, нет дисплея), они
просто сохраняются в папку output.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from src.core.processor import process
from src.core.charts import build_all_figures, save_all_figures
from src.core.utils import format_time


class AppWindow:
    """Главное окно приложения."""

    def __init__(self, root, default_path):
        self.root = root
        self.records = []       # обработанные записи
        self.summary = {}       # сводные показатели
        self.figures = []       # построенные фигуры [(имя, fig), ...]

        root.title("Лабораторная работа №1: обработка лога badblocks")
        root.geometry("700x520")

        self.path_var = tk.StringVar(value=default_path)
        self.make_widgets()

    def make_widgets(self):
        """Создаёт элементы интерфейса."""
        frame_top = tk.Frame(self.root)
        frame_top.pack(fill="x", padx=8, pady=6)

        tk.Label(frame_top, text="Файл лога:").pack(side="left")
        entry = tk.Entry(frame_top, textvariable=self.path_var, width=60)
        entry.pack(side="left", fill="x", expand=True, padx=4)
        tk.Button(frame_top, text="Обзор...", command=self.choose_file)\
            .pack(side="left")

        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(fill="x", padx=8)
        tk.Button(frame_buttons, text="Обработать и построить графики",
                  command=self.on_process).pack(side="left", pady=4)
        tk.Button(frame_buttons, text="Сохранить графики в PNG",
                  command=self.on_save).pack(side="left", padx=8, pady=4)

        frame_main = tk.Frame(self.root)
        frame_main.pack(fill="both", expand=True, padx=8, pady=6)

        self.listbox = tk.Listbox(frame_main, width=34)
        self.listbox.pack(side="left", fill="y")
        # Двойной клик по названию графика - открыть его в отдельном окне.
        self.listbox.bind("<Double-Button-1>", self.on_double_click)

        self.info_text = scrolledtext.ScrolledText(frame_main, wrap="word",
                                                   font=("Segoe UI", 10))
        self.info_text.pack(side="left", fill="both", expand=True, padx=(8, 0))

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.status_var = tk.StringVar(value="Файл не обработан.")
        tk.Label(status_frame, textvariable=self.status_var, anchor="w")\
            .pack(fill="x")

    def choose_file(self):
        """Открывает диалог выбора файла."""
        path = filedialog.askopenfilename(
            title="Выберите лог-файл badblocks",
            filetypes=[("Логи badblocks", "*.bbl *.log *.txt"),
                       ("Все файлы", "*.*")])
        if path != "":
            self.path_var.set(path)

    def on_process(self):
        """Читает файл, обрабатывает данные и строит графики."""
        path = self.path_var.get()
        if not os.path.exists(path):
            messagebox.showerror("Ошибка", "Файл не найден: {}".format(path))
            return

        try:
            records, summary = process(path)
        except Exception as exc:
            messagebox.showerror("Ошибка", "Не удалось обработать файл:\n{}"
                                 .format(exc))
            return

        if len(records) < 3:
            messagebox.showwarning(
                "Мало данных",
                "В файле найдено меньше трёх корректных записей прогресса.")
            return

        self.records = records
        self.summary = summary

        try:
            self.figures = build_all_figures(records)
        except Exception as exc:
            self.figures = []
            messagebox.showerror("Ошибка",
                                 "Не удалось построить графики:\n{}".format(exc))

        self.listbox.delete(0, tk.END)
        for name, fig in self.figures:
            self.listbox.insert(tk.END, name)

        self.show_summary()
        self.status_var.set(
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
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, text)

    def on_double_click(self, event):
        """Открывает график, выбранный двойным кликом в списке."""
        selection = self.listbox.curselection()
        if len(selection) == 0:
            return
        index = selection[0]
        self.show_figure(index)

    def show_figure(self, index):
        """Открывает окно matplotlib с выбранным графиком."""
        if index >= len(self.figures):
            return
        name, fig = self.figures[index]
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            window = tk.Toplevel(self.root)
            window.title(name)
            canvas = FigureCanvasTkAgg(fig, master=window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            try:
                from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
                NavigationToolbar2Tk(canvas, window)
            except Exception:
                pass  # панель навигации не обязательна
        except Exception as exc:
            messagebox.showerror("Ошибка",
                                 "Не удалось показать график:\n{}".format(exc))

    def on_save(self):
        """Сохраняет все графики в папку output рядом с программой."""
        if len(self.figures) == 0:
            messagebox.showwarning("Нет данных",
                                   "Сначала обработайте файл.")
            return
        base_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        folder = os.path.join(base_dir, "output")
        paths = save_all_figures(self.figures, folder)
        message = "Графики сохранены:\n"
        for name, path in paths:
            message = message + "- {} -> {}\n".format(name, path)
        messagebox.showinfo("Готово", message)


def run(default_path):
    """Создаёт окно приложения и запускает главный цикл."""
    root = tk.Tk()
    AppWindow(root, default_path)
    root.mainloop()
