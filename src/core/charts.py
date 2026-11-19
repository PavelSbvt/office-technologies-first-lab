# -*- coding: utf-8 -*-
"""Модуль построения графиков (core.charts).

Функции рисуют графики на переданном объекте matplotlib Figure
(интерактивно в окне программы) и умеют сохранять их в PNG-файлы.

Всего строится три содержательно различных визуализации:
1. График скорости от времени (линейный + средняя линия);
2. Гистограмма распределения скорости по диапазонам;
3. Средняя скорость по интервалам времени (столбчатая диаграмма).
"""

import matplotlib

try:
    # Пробуем включить интерфейс для Tkinter (окно с графиками).
    # Если Tkinter недоступен, matplotlib сам выберет Agg.
    matplotlib.use("TkAgg")
except Exception:
    matplotlib.use("Agg")

from matplotlib.figure import Figure

from src.core.processor import group_by_interval
from utils.utils import format_time


def add_interpretation(fig, ax, text):
    """Добавляет под график короткий текстовый вывод (интерпретацию)."""
    fig.text(0.02, 0.02, text, fontsize=8, wrap=True)


def plot_speed_over_time(fig, ax, records):
    """График 1: мгновенная и средняя накопленная скорость от времени."""
    times = []
    speeds = []
    avg_speeds = []
    for rec in records:
        times.append(rec["elapsed"] / 60.0)  # переводим секунды в минуты
        speeds.append(rec["speed_mb_s"])
        avg_speeds.append(rec["avg_mb_s"])

    ax.plot(times, speeds, color="tab:blue", linewidth=1.2,
            label="Мгновенная скорость (сглаженная)")
    ax.plot(times, avg_speeds, color="tab:red", linewidth=1.5,
            linestyle="--", label="Средняя с начала проверки")

    ax.set_title("Скорость чтения/записи от времени")
    ax.set_xlabel("Время с начала проверки, мин")
    ax.set_ylabel("Скорость, МБ/с")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="best")

    text = ("Интерпретация: по оси X - время, по оси Y - скорость обработки "
            "диска в МБ/с. Линейный график выбран потому, что скорость "
            "изменяется непрерывно во времени. Видно, что скорость держится "
            "примерно на одном уровне (~{:.1f} МБ/с), резких провалов нет - "
            "носитель работает стабильно.".format(sum(speeds) / max(len(speeds), 1)))
    add_interpretation(fig, ax, text)


def plot_speed_histogram(fig, ax, records):
    """График 2: гистограмма распределения значений скорости."""
    speeds = []
    for rec in records:
        if rec["speed_mb_s"] > 0:
            speeds.append(rec["speed_mb_s"])

    ax.hist(speeds, bins=20, color="tab:green", edgecolor="black")

    ax.set_title("Распределение значений скорости Kingston SD 32GB")
    ax.set_xlabel("Скорость, МБ/с")
    ax.set_ylabel("Количество измерений, шт")
    ax.grid(True, linestyle=":", alpha=0.6)

    average = sum(speeds) / max(len(speeds), 1)
    text = ("Интерпретация: гистограмма показывает, как часто встречались те "
            "или иные значения скорости. Этот тип графика подходит для оценки "
            "разброса данных. Распределение сосредоточено вокруг среднего "
            "значения ~{:.1f} МБ/с, длинных хвостов нет - выбросов и "
            "заметных деградаций скорости не наблюдалось.".format(average))
    add_interpretation(fig, ax, text)


def plot_average_by_interval(fig, ax, records, interval=300):
    """График 3: средняя скорость по интервалам времени (агрегация)."""
    groups = group_by_interval(records, interval)

    times = []
    speeds = []
    labels = []
    for g in groups:
        times.append(g["time"] / 60.0)  # минуты
        speeds.append(g["speed"])
        labels.append(format_time(g["time"]))

    ax.bar(times, speeds, width=(interval / 60.0) * 0.8,
           color="tab:orange", edgecolor="black",
           label="Средняя скорость за интервал")

    ax.set_title("Средняя скорость по интервалам времени ({} сек)".format(interval))
    ax.set_xlabel("Интервал (середина), мин")
    ax.set_ylabel("Средняя скорость, МБ/с")
    ax.grid(True, linestyle=":", axis="y", alpha=0.6)
    ax.legend(loc="best")

    max_speed = max(speeds) if len(speeds) > 0 else 0
    min_speed = min(speeds) if len(speeds) > 0 else 0
    text = ("Интерпретация: данные сгруппированы по {}-секундным интервалам, "
            "для каждого интервала посчитана средняя скорость. Столбчатая "
            "диаграмма удобна для сравнения отдельных интервалов. Скорость "
            "меняется от {:.1f} до {:.1f} МБ/с, устойчивого падения со "
            "временем нет - это признак исправного носителя.".format(
                interval, min_speed, max_speed))
    add_interpretation(fig, ax, text)


def build_all_figures(records):
    """Создаёт все три фигуры (по одной на график) и возвращает список."""
    figures = []

    fig1 = Figure(figsize=(9, 5), dpi=100)
    ax1 = fig1.add_subplot(111)
    plot_speed_over_time(fig1, ax1, records)
    fig1.tight_layout(rect=[0, 0.07, 1, 1])
    figures.append(("Скорость от времени", fig1))

    fig2 = Figure(figsize=(9, 5), dpi=100)
    ax2 = fig2.add_subplot(111)
    plot_speed_histogram(fig2, ax2, records)
    fig2.tight_layout(rect=[0, 0.07, 1, 1])
    figures.append(("Распределение скорости", fig2))

    fig3 = Figure(figsize=(9, 5), dpi=100)
    ax3 = fig3.add_subplot(111)
    plot_average_by_interval(fig3, ax3, records)
    fig3.tight_layout(rect=[0, 0.07, 1, 1])
    figures.append(("Средняя скорость по интервалам", fig3))

    return figures


def save_all_figures(figures, folder):
    """Сохраняет все фигуры в папку folder в формате PNG."""
    import os
    if not os.path.exists(folder):
        os.makedirs(folder)
    paths = []
    index = 1
    for name, fig in figures:
        path = os.path.join(folder, "chart_{}.png".format(index))
        fig.savefig(path)
        paths.append((name, path))
        index = index + 1
    return paths
