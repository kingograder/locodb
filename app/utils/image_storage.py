# -*- coding: utf-8 -*-
"""Хранение изображений: сохранение и удаление файлов моделей.

Файлы лежат в data/images, имя — {производитель}_{код}.jpeg.
В БД пишем относительный путь вида "data/images/xxx.jpeg",
чтобы проект можно было перенести на другую машину без правок.
"""

import logging
from pathlib import Path

from PySide6.QtGui import QImage

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
JPEG_QUALITY = 85


def _sanitize_filename_part(value: str) -> str:
    """Оставляет в строке только безопасные для файла символы.

    Пробелы заменяет на подчёркивания, всё лишнее выбрасывает.
    """
    keep = []
    for ch in value.strip().lower():
        if ch.isalnum() or ch in ("-", "_"):
            keep.append(ch)
        elif ch.isspace():
            keep.append("_")
    return "".join(keep) or "unknown"


def save_model_image(source_path: str, manufacturer_name: str, code: int) -> str:
    """Сохраняет картинку в data/images как JPEG и возвращает относительный путь.

    source_path — путь к исходному файлу, выбранному пользователем.
    Если файл не читается или не сохраняется — бросает ValueError/OSError,
    чтобы вызывающий код мог показать пользователю понятное сообщение.
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{_sanitize_filename_part(manufacturer_name)}_{code}.jpeg"
    target = IMAGES_DIR / filename

    image = QImage(source_path)
    if image.isNull():
        raise ValueError(f"Не удалось прочитать изображение: {source_path}")

    # Формат определяется по расширению .jpeg, quality — уровень сжатия 0–100.
    if not image.save(str(target), quality=JPEG_QUALITY):
        raise OSError(f"Не удалось сохранить изображение в {target}")

    logger.info(f"Изображение сохранено: {target}")
    return target.relative_to(PROJECT_ROOT).as_posix()


def delete_image(relative_path: str | None) -> None:
    """Удаляет файл изображения, если он существует.

    Относительные пути разрешаются от корня проекта, абсолютные сохраняются.
    Отсутствие файла — не ошибка: значит его уже кто-то удалил.
    """
    if not relative_path:
        return

    path = Path(relative_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        return

    try:
        path.unlink()
        logger.info(f"Изображение удалено: {path}")
    except OSError:
        # Файл может быть занят другим процессом — не валим сохранение из-за этого.
        logger.exception(f"Не удалось удалить изображение: {path}")
