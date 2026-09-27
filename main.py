# -*- coding: utf-8 -*-
"""Точка входа: настройка логирования, инициализация БД, запуск UI."""

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.init import init_db
from app.services import Services
from app.app import ScreensStack

logger = logging.getLogger(__name__)

DATA_DIR = Path("./data")
LOGS_DIR = DATA_DIR / "logs"
IMAGES_DIR = DATA_DIR / "images"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'database.sqlite'}"


def create_directories(dirs: list[Path]) -> None:
    """Создаёт директории, если их ещё нет."""
    for path in dirs:
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Директория подготовлена: {path}")


def setup_logging() -> None:
    """Настраивает логирование в файл и в консоль."""
    log_file = LOGS_DIR / f"app_{datetime.now(UTC):%Y-%m-%d_%H-%M-%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def build_services() -> Services:
    """Создаёт движок, фабрику сессий и контейнер репозиториев."""
    # expire_on_commit=False — объекты остаются живыми после коммита,
    # это удобно для UI, который читает поля уже после сохранения.
    engine = create_engine(DATABASE_URL, echo=False)
    session_factory = sessionmaker(engine, expire_on_commit=False)
    init_db(engine, session_factory)
    return Services(session_factory)


def main() -> int:
    """Запускает приложение и возвращает код выхода."""
    create_directories([DATA_DIR, LOGS_DIR, IMAGES_DIR])
    setup_logging()

    services = build_services()

    app = QApplication(sys.argv)
    stack = ScreensStack(services)
    stack.resize(1280, 720)
    stack.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
