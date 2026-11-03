import re
from pathlib import Path

import matplotlib.pyplot as plt


# ---------- 1. ПАРАМЕТРЫ ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = PROJECT_ROOT / "resources" / "SanDisk-Ultra-64G.bbl"
BLOCK_SIZE = 1024  # badblocks по умолчанию 1024 байта; уточните, если запускали с -b

# ---------- 2. ЧТЕНИЕ И "РАЗКЛЕЙКА" СТРОК ----------
with open(LOG_FILE, "r", errors="replace") as f:
    raw = f.read()

# badblocks обновляет строку через \r, поэтому разбиваем по \r и \n
lines = re.split(r"[\r\n\x08]+", raw)

# ---------- 3. РЕГУЛЯРКИ ----------
# Пример: "0.01% done, 0:03 elapsed. (0/0/0 errors)"
progress_re = re.compile(
    r"(?P<percent>\d+\.\d+)% done,\s+"
    r"(?P<h>\d+):(?P<m>\d{2})(?::(?P<s>\d{2}))?\s+elapsed"
)
# Строка с диапазоном блоков
range_re = re.compile(r"From block\s+(\d+)\s+to\s+(\d+)")
# Метка этапа (read-write / read-only / pattern)
phase_re = re.compile(r"^(Testing with .+|Чтение и сравнение.*|Checking for bad blocks.*)")

# ---------- 4. ПАРСИНГ ----------
records = []          # [(phase, t_sec, percent), ...]
current_phase = "unknown"
first_block = last_block = None

for line in lines:
    line = line.strip()
    if not line:
        continue

    m = range_re.search(line)
    if m:
        first_block, last_block = int(m.group(1)), int(m.group(2))
        continue

    m = phase_re.match(line)
    if m:
        current_phase = m.group(1).strip()
        continue

    m = progress_re.search(line)
    if m:
        h = int(m.group("h"))
        mnt = int(m.group("m"))
        s = int(m.group("s") or 0)
        t_sec = h * 3600 + mnt * 60 + s
        percent = float(m.group("percent"))
        records.append((current_phase, t_sec, percent))

print(f"Всего точек прогресса: {len(records)}")
print(f"Диапазон блоков: {first_block} .. {last_block}")

# ---------- 5. РАСЧЁТ ОБЩЕГО ОБЪЁМА ----------
if first_block is not None:
    total_blocks = last_block - first_block + 1
    total_bytes = total_blocks * BLOCK_SIZE
    print(f"Всего блоков: {total_blocks}, объём: {total_bytes / 1e9:.2f} ГБ")

# ---------- 6. РАСЧЁТ СКОРОСТИ ПО КАЖДОМУ ЭТАПУ ----------
def compute_speed(recs):
    """recs = [(phase, t, percent), ...] для одного этапа."""
    times, speeds = [], []
    for i in range(1, len(recs)):
        _, t0, p0 = recs[i - 1]
        _, t1, p1 = recs[i]
        dt = t1 - t0
        dp = (p1 - p0) / 100.0
        if dt <= 0 or dp <= 0:
            continue
        speed_bytes = dp * total_bytes / dt   # байт/с
        times.append(t1)
        speeds.append(speed_bytes)
    return times, speeds

# Группируем записи по этапу
from itertools import groupby
phases = {}
for phase, group in groupby(records, key=lambda r: r[0]):
    phases[phase] = list(group)

# ---------- 7. ПОСТРОЕНИЕ ГРАФИКОВ ----------
fig, ax = plt.subplots(figsize=(14, 7))

for phase, recs in phases.items():
    times, speeds = compute_speed(recs)
    if not times:
        continue
    # В МБ/с
    speeds_mb = [s / (1024 * 1024) for s in speeds]
    ax.plot(times, speeds_mb, label=phase, linewidth=1.2)

ax.set_xlabel("Время, с")
ax.set_ylabel("Скорость, МБ/с")
ax.set_title("Скорость чтения/записи по данным badblocks")
ax.grid(True, alpha=0.3)
ax.legend(loc="best", fontsize=9)
plt.tight_layout()
plt.show()