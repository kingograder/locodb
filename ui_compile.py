from pathlib import Path
import subprocess

INPUT_DIR = Path("uis")
OUTPUT_DIR = Path("app/widgets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Использование rglob для рекурсивного поиска всех файлов .ui
for file in INPUT_DIR.rglob("*.ui"):
    # Вычисляем относительный путь файла по отношению к INPUT_DIR
    relative_path = file.relative_to(INPUT_DIR)

    # Формируем путь для выходного файла с сохранением подпапок
    out_file = OUTPUT_DIR / relative_path.parent / f"ui_{file.stem}.py"

    # Создаем поддиректории, если их еще нет
    out_file.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["pyside6-uic", str(file), "-o", str(out_file)],
        check=True,
    )
    print(f"{file} -> {out_file}")
