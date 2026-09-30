"""Инициализация базы данных: создание таблиц и стартового администратора."""

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base
from app.db.exceptions import LoginAlreadyTakenError
from app.db.repositories import MaintenanceRepository, MaintenanceTypeRepository, ManufacturerRepository, UserRepository

logger = logging.getLogger(__name__)


def _create_tables(engine) -> None:
    """Создаёт все таблицы, описанные в моделях. Существующие не трогает."""
    Base.metadata.create_all(engine)
    logger.info("Все таблицы созданы")


def init_db(engine, session_factory) -> None:
    """Готовит БД к работе: создаёт таблицы и первого админа admin/admin.

    Если пользователь admin уже существует — просто пропускает создание,
    чтобы повторный запуск приложения не падал с ошибкой.
    """
    _create_tables(engine)
    _ensure_default_admin(session_factory)
    # Производители создаются в любом случае при старте программы, это проблема надо будет исправить
    _create_manufacturers_on_startup(session_factory)
    _create_maintenance_type_on_startup(session_factory)

def _ensure_default_admin(session_factory) -> None:
    """Создаёт стартового администратора admin/admin, если его ещё нет."""
    users = UserRepository(session_factory)
    try:
        users.create(
            login="admin",
            password="admin",
            first_name="John",
            last_name="Blade",
            is_admin=True,
            is_active=True,
        )
        logger.info("Создан стартовый администратор admin")
    except LoginAlreadyTakenError:
        logger.info("Пользователь admin уже существует, пропускаем создание")

def _create_manufacturers_on_startup(session_factory) -> None:
    manufacturers = ManufacturerRepository(session_factory)
    if not manufacturers.get_by_name("Roco"):
        manufacturer_list = ["Roco", "Piko"]
        try:
            for i in manufacturer_list:
                manufacturers.create(
                    name=i
                )
            logger.info("Созданы производители")
        except SQLAlchemyError as e:
            logger.info(f"Ошибка при заполнении номенклатуры производителей: {e}")

def _create_maintenance_type_on_startup(session_factory) -> None:
    maintenance_types = MaintenanceTypeRepository(session_factory)
    maintenance_types_list = ["Разное"]
    if not maintenance_types.get_by_name("Разное"):
        try:
            for i in maintenance_types_list:
                maintenance_types.create(
                    name=i
                )
            logger.info("Созданы типы обслуживания")
        except SQLAlchemyError as e:
            logger.info(f"Ошибка при заполнении номенклатуры типов обслуживания: {e}")
