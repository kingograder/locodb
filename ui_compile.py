from pathlib import Path
import subprocess

INPUT_DIR = Path("uis")
OUTPUT_DIR = Path("app/widgets")

# Создаем целевую папку, если её нет
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Рекурсивный обход всех поддиректорий
for file in INPUT_DIR.rglob("*.ui"):
    # Формируем путь для .py файла прямо в корне OUTPUT_DIR (плоская структура)
    out_file = OUTPUT_DIR / f"ui_{file.stem}.py"

    # Запускаем компиляцию
    subprocess.run(
        ["pyside6-uic", str(file), "-o", str(out_file)],
        check=True,
    )
    print(f"{file} -> {out_file}")
