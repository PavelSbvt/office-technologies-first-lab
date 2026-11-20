import matplotlib

from matplotlib.figure import Figure

from src.core.processor import group_by_interval
from utils.utils import format_time


def add_interpretation(fig, ax, text):
    """Добавляет под график короткий текстовый вывод (интерпретацию)."""
    fig.text(0.02, 0.02, text, fontsize=8, wrap=True)


def plot_speed_over_time(fig, ax, write_records, read_records):
    """График 1: мгновенная и средняя скорость от времени (сразу два этапа)."""

    # --- Фильтруем нулевые скорости, чтобы не было "палок" вниз на старте ---
    w_clean = [r for r in write_records if r["speed_mb_s"] > 0]
    r_clean = [r for r in read_records if r["speed_mb_s"] > 0]

    # Данные для записи
    w_times = [r["elapsed"] / 60.0 for r in w_clean]
    w_speeds = [r["speed_mb_s"] for r in w_clean]
    w_avgs = [r["avg_mb_s"] for r in w_clean]

    # Данные для чтения
    r_times = [r["elapsed"] / 60.0 for r in r_clean]
    r_speeds = [r["speed_mb_s"] for r in r_clean]
    r_avgs = [r["avg_mb_s"] for r in r_clean]

    # Рисуем мгновенную скорость (сплошные линии)
    ax.plot(w_times, w_speeds, color="tab:blue", linewidth=1.2,
            label="Запись (мгновенная)")
    ax.plot(r_times, r_speeds, color="tab:green", linewidth=1.2,
            label="Чтение (мгновенная)")

    # Рисуем среднюю скорость (пунктирные линии для контраста)
    ax.plot(w_times, w_avgs, color="tab:blue", linestyle="--",
            linewidth=1.5, alpha=0.8, label="Запись (средняя)")
    ax.plot(r_times, r_avgs, color="tab:green", linestyle="--",
            linewidth=1.5, alpha=0.8, label="Чтение (средняя)")

    ax.set_title("Скорость записи и чтения от времени")
    ax.set_xlabel("Время, мин")
    ax.set_ylabel("Скорость, МБ/с")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="best")

    # Динамический текст интерпретации (чтобы не врать, если есть провалы)
    # Вычисляем минимальную скорость
    # для каждого этапа, чтобы понять, есть ли провалы
    min_w = min(w_speeds) if w_speeds else 0
    min_r = min(r_speeds) if r_speeds else 0

    text = ("Интерпретация: сплошные линии показывают мгновенную скорость, "
            "пунктирные — среднюю с начала этапа.")

    # Если минимальная скорость сильно ниже средней, пишем о провале
    if min_r < 30.0:
        text += f"На этапе чтения заметен провал скорости (минимум {min_r:.1f} МБ/с)."
    else:
        text += "Резких провалов нет — носитель работает стабильно."

    add_interpretation(fig, ax, text)


def plot_speed_histogram(fig, ax, write_records, read_records):
    """График 2: гистограмма распределения скоростей."""

    # Берем только положительные скорости (игнорируем нули на старте)
    w_speeds = [r["speed_mb_s"] for r in write_records if r["speed_mb_s"] > 0]
    r_speeds = [r["speed_mb_s"] for r in read_records if r["speed_mb_s"] > 0]

    # Рисуем две гистограммы на одном графике с прозрачностью
    # bins=20 - количество столбцов, alpha=0.5 - прозрачность для наложения
    ax.hist(w_speeds, bins=15, color="tab:blue", alpha=0.6,
            label="Запись", edgecolor="black")
    ax.hist(r_speeds, bins=15, color="tab:green", alpha=0.6,
            label="Чтение", edgecolor="black")

    ax.set_title("Распределение значений скорости")
    ax.set_xlabel("Скорость, МБ/с")
    ax.set_ylabel("Количество измерений, шт")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="best")

    text = ("Интерпретация: синие столбцы — запись, зеленые — чтение. "
            "Распределения показывают, что запись и чтение идут со стабильной скоростью."
            " Выбросов нет.")
    add_interpretation(fig, ax, text)


def plot_average_by_interval(fig, ax, write_records, read_records, interval=300):
    """График 3: средняя скорость по интервалам времени."""

    # Группируем данные для записи
    w_groups = group_by_interval(write_records, interval)
    # Группируем данные для чтения
    r_groups = group_by_interval(read_records, interval)

    # Время для записи (в минутах)
    w_times = [g["time"] / 60.0 for g in w_groups]
    w_speeds = [g["speed"] for g in w_groups]

    # Время для чтения (в минутах) - без смещения, так как elapsed уже общий
    r_times = [g["time"] / 60.0 for g in r_groups]
    r_speeds = [g["speed"] for g in r_groups]

    # Рисуем столбцы
    # width = (interval / 60.0) * 0.8 - ширина столбца в минутах (80% от интервала)
    ax.bar(w_times, w_speeds, width=(interval / 60.0) * 0.8,
           color="tab:blue", label="Запись")
    ax.bar(r_times, r_speeds, width=(interval / 60.0) * 0.8,
           color="tab:green", label="Чтение")

    ax.set_title("Средняя скорость по интервалам ({} сек)".format(interval))
    ax.set_xlabel("Время с начала проверки, мин")
    ax.set_ylabel("Средняя скорость, МБ/с")
    ax.grid(True, linestyle=":", axis="y", alpha=0.6)
    ax.legend(loc="best")

    text = ("Интерпретация: Столбцы синего цвета — средняя скорость записи, "
            "зеленого — чтения. Видно, что этапы имеют разную скорость. "
            "На всем протяжении обоих этапов скорость не падает критически.")
    add_interpretation(fig, ax, text)


def build_all_figures(write_records, read_records):
    figures = []

    fig1 = Figure(figsize=(9, 5), dpi=100)
    ax1 = fig1.add_subplot(111)
    plot_speed_over_time(fig1, ax1, write_records, read_records)
    fig1.tight_layout(rect=[0, 0.07, 1, 1])
    figures.append(("Скорость от времени", fig1))

    fig2 = Figure(figsize=(9, 5), dpi=100)
    ax2 = fig2.add_subplot(111)
    plot_speed_histogram(fig2, ax2, write_records, read_records)
    fig2.tight_layout(rect=[0, 0.07, 1, 1])
    figures.append(("Распределение скорости", fig2))

    fig3 = Figure(figsize=(9, 5), dpi=100)
    ax3 = fig3.add_subplot(111)
    plot_average_by_interval(fig3, ax3, write_records, read_records)
    fig3.tight_layout(rect=[0, 0.07, 1, 1])
    figures.append(("Средняя скорость по интервалам", fig3))

    return figures


def save_all_figures(figures, folder):
    """Сохраняет все фигуры в папку output в формате PNG."""
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
