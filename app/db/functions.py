import logging
from sqlalchemy import select

from app.autorization import hash_password
from app.db.models import User
from app.db.base import Base

logger = logging.getLogger(__name__)

def get_user(session_factory, login) -> User | None:
    with session_factory() as session:
        return session.scalar(select(User).where(User.login == login))

def add_user(session_factory, login: str, password_hash: str, password_salt: str, first_name: str, last_name: str, is_admin: bool) -> None:
    new_user = User(login=login, password_hash=password_hash, first_name=first_name, last_name=last_name, is_admin=is_admin)
    with session_factory() as session:
            existing = session.scalar(select(User).where(User.login == login))
            if existing:
                logger.error(f"Пользователь {login} уже существует.")
                return
            new_user = User(
                login=login,
                password_hash=password_hash,
                password_salt=password_salt,
                first_name=first_name,
                last_name=last_name,
                is_admin=is_admin
            )
            try:
                session.add(new_user)
                session.commit()
                logger.info(f"Пользователь {login} успешно создан.")
            except Exception as e:
                session.rollback()
                logger.error(f"Ошибка при создании пользователя {login}: {e}")

def drop_tables(engine):
    Base.metadata.drop_all(engine)
    logger.info("Все таблицы сброшены.")

def create_tables(engine):
    Base.metadata.create_all(engine)
    logger.info("Все таблицы созданы.")

def init_db(engine, session_factory) -> None:
    """
    Создание таблиц и первого пользователя admin
    """
    create_tables(engine)
    admin = get_user(session_factory, login="admin")
    if not admin:
        hash, salt = hash_password("admin")
        add_user(
                    session_factory,
                    login="admin",
                    password_hash=hash,
                    password_salt=salt,
                    first_name="",
                    last_name="",
                    is_admin=True
                )

def add_maintenance():
    pass

def mark_on_delete_maintenance():
    pass

"""
Работа с моделью локомотива
"""

def add_lokomotive_model():
    pass

def remove_lokomotive_model():
    pass

def get_lokomotive_model():
    pass

"""
Работа с локомотивом
"""
