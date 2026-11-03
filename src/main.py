from pathlib import Path

LOG_FILE = Path(__file__).resolve().parents[1] / "resources" / "SanDisk-Ultra-64G.bbl"

# 1. Первые 500 байт
with open(LOG_FILE, "rb") as f:
    head = f.read(500)
print("=== Первые 500 байт ===")
print(head)

# 2. Есть ли вообще ключевые слова
with open(LOG_FILE, "r", errors="replace") as f:
    raw = f.read()
print("=== Есть '% done' ? ===", "% done" in raw)
print("=== Есть 'elapsed' ? ===", "elapsed" in raw)
print("=== Есть 'Testing with' ? ===", "Testing with" in raw)
print("=== Размер файла, байт ===", len(raw))