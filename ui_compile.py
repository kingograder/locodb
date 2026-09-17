from pathlib import Path
import subprocess

INPUT_DIR = Path("uis")
OUTPUT_DIR = Path("app/widgets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for file in INPUT_DIR.glob("*.ui"):
    out_file = OUTPUT_DIR / f"ui_{file.stem}.py"
    subprocess.run(
        ["pyside6-uic", str(file), "-o", str(out_file)],
        check=True,
    )
    print(f"{file} -> {out_file}")
