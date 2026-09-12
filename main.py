import logging
import sys

from app.layouts.auth import Ui_Auth
from datetime import datetime
from pathlib import Path
from app.db.db import engine, session_factory
from app.db.functions import init_db

logger = logging.getLogger(__name__)

def create_directories(dirs: list[Path]) -> None:
    """
    Creating directories on startup
    """
    for path in dirs:
        Path(path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory {path} not found. Creating...")

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        format="[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s",
        handlers=[
            logging.FileHandler(
                f"./data/logs/app_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log",
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )

if __name__ == "__main__":
    create_directories([Path("./data"), Path("./data/logs")])
    setup_logging()
    init_db(engine, session_factory)

    app = QApplication(sys.argv)
    window = AuthWindow()
    window.showMaximized()

    sys.exit(app.exec())
