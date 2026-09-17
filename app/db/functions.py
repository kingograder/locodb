import logging
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, sessionmaker
from app.autorization import check_password, hash_password
from app.db.base import Base
from app.db.models import (
    User, Maintenance, MaintenanceType, Locomotive, LocomotiveModel, Detail,
)

logger = logging.getLogger(__name__)


class UserNotFoundError(Exception):
    """Пользователь с указанным ID не найден."""
    pass

class LoginAlreadyTakenError(Exception):
    """Логин уже занят другим пользователем."""
    pass

class LastActiveAdminError(Exception):
    """Попытка убрать последнего активного администратора."""
    pass

class LocomotiveNotFoundError(Exception):
    """Локомотив с указанным ID не найден."""
    pass

class LocomotiveModelNotFoundError(Exception):
    """Модель локомотива с указанным ID не найдена."""
    pass

class DetailNotFoundError(Exception):
    """Деталь с указанным ID не найдена."""
    pass

class MaintenanceNotFoundError(Exception):
    """Лист обслуживания с указанным ID не найден."""
    pass

class MaintenanceTypeNotFoundError(Exception):
    """Тип обслуживания с указанным ID не найден."""
    pass


def _update_entity(session_factory, model_class, entity_id: int, not_found_error, **fields) -> None:
    """Обновляет поля сущности и сохраняет в БД."""
    with session_factory() as session:
        entity = session.get(model_class, entity_id)
        if entity is None:
            raise not_found_error(entity_id)

        # Применяем переданные поля
        for field, value in fields.items():
            setattr(entity, field, value)

        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception(f"Ошибка БД при обновлении {model_class.__name__} ID {entity_id}")
            raise

        logger.info(f"Обновлён {model_class.__name__} ID {entity_id}")


def _delete_entity(session_factory, model_class, entity_id: int, not_found_error) -> None:
    """Удаляет сущность из БД."""
    with session_factory() as session:
        entity = session.get(model_class, entity_id)
        if entity is None:
            raise not_found_error(entity_id)

        session.delete(entity)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception(f"Ошибка БД при удалении {model_class.__name__} ID {entity_id}")
            raise

        logger.info(f"Удалён {model_class.__name__} ID {entity_id}")


def get_user(session_factory: sessionmaker, login: str) -> User | None:
    """Возвращает пользователя по логину или None."""
    with session_factory() as session:
        return session.scalar(
            select(User).where(User.login == login.strip().lower())
        )


def get_all_users(session_factory: sessionmaker) -> list[User]:
    """Возвращает список всех пользователей."""
    with session_factory() as session:
        return list(session.scalars(select(User).order_by(User.id)).all())


def count_active_admins(session_factory: sessionmaker, exclude_user_id: int | None = None) -> int:
    """Считает количество активных администраторов."""
    with session_factory() as session:
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.is_admin, User.is_active)
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return session.scalar(stmt)


def assert_not_last_admin(session_factory: sessionmaker, user_id: int) -> None:
    """Выбрасывает LastActiveAdminError, если user_id — последний активный админ."""
    if count_active_admins(session_factory, exclude_user_id=user_id) == 0:
        raise LastActiveAdminError(user_id)


def authenticate(session_factory: sessionmaker, login: str, password: str) -> User | None:
    """Проверяет логин и пароль. Возвращает User или None."""
    user = get_user(session_factory, login)
    if user is None:
        logger.warning(f"Вход: пользователь {login} не найден")
        return None

    if not user.is_active:
        logger.warning(f"Вход: учётная запись {login} отключена")
        return None

    if not check_password(user, password):
        logger.warning(f"Вход: неверный пароль для {login}")
        return None

    logger.info(f"Пользователь {login} авторизирован")
    return user


def add_user(
    session_factory: sessionmaker,
    login: str,
    password: str,
    first_name: str,
    last_name: str,
    is_admin: bool,
    is_active: bool = True,
) -> None:
    """Создаёт нового пользователя."""
    password_hash, password_salt = hash_password(password)

    with session_factory() as session:
        existing = session.scalar(
            select(User).where(User.login == login.strip().lower())
        )
        if existing is not None:
            raise LoginAlreadyTakenError(login)

        new_user = User(
            login=login.strip().lower(),
            password_hash=password_hash,
            password_salt=password_salt,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            is_active=is_active,
        )
        session.add(new_user)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception(f"Ошибка БД при создании пользователя {login}")
            raise

        logger.info(f"Пользователь {login} создан")


def update_user_full(
    session_factory: sessionmaker,
    user_id: int,
    *,
    login: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    password: str | None = None,
    is_admin: bool | None = None,
    is_active: bool | None = None,
) -> None:
    """Атомарно обновляет пользователя. Все переданные поля — в одной транзакции."""
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        # 1. Проверка уникальности логина (если он меняется)
        new_login = login.strip().lower() if login else None
        if new_login and new_login != user.login:
            existing = session.scalar(
                select(User).where(User.login == new_login, User.id != user_id)
            )
            if existing is not None:
                raise LoginAlreadyTakenError(new_login)

        # 2. Проверка "последнего активного админа"
        will_be_admin = is_admin if is_admin is not None else user.is_admin
        will_be_active = is_active if is_active is not None else user.is_active

        if user.is_admin and user.is_active and not (will_be_admin and will_be_active):
            assert_not_last_admin(session_factory, user_id)

        # 3. Применение изменений
        if new_login:
            user.login = new_login
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if password is not None:
            user.password_hash, user.password_salt = hash_password(password)
        if is_admin is not None:
            user.is_admin = is_admin
        if is_active is not None:
            user.is_active = is_active

        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception(f"Ошибка БД при полном обновлении пользователя ID {user_id}")
            raise

        logger.info(f"Пользователь ID {user_id} полностью обновлен")


def update_user_data(
    session_factory: sessionmaker,
    user_id: int,
    user_login: str,
    user_firstname: str,
    user_lastname: str,
) -> None:
    """Обновляет логин, имя и фамилию пользователя."""
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        if user_login.strip().lower() != user.login:
            existing = session.scalar(
                select(User).where(User.login == user_login.strip().lower())
            )
            if existing is not None:
                raise LoginAlreadyTakenError(user_login)

        user.login = user_login.strip().lower()
        user.first_name = user_firstname
        user.last_name = user_lastname

        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception(f"Ошибка БД при обновлении пользователя ID {user_id}")
            raise

        logger.info(f"Данные пользователя ID {user_id} обновлены")


def update_user_is_admin(session_factory: sessionmaker, user_id: int, is_admin: bool) -> None:
    """Меняет роль пользователя."""
    _update_entity(session_factory, User, user_id, UserNotFoundError, is_admin=is_admin)


def update_user_is_active(session_factory: sessionmaker, user_id: int, is_active: bool) -> None:
    """Включает или отключает пользователя."""
    _update_entity(session_factory, User, user_id, UserNotFoundError, is_active=is_active)


def update_user_password(session_factory: sessionmaker, user_id: int, password: str) -> None:
    """Меняет пароль пользователя."""
    password_hash, password_salt = hash_password(password)
    _update_entity(
        session_factory, User, user_id, UserNotFoundError,
        password_hash=password_hash,
        password_salt=password_salt,
    )


def delete_user(session_factory: sessionmaker, user_id: int) -> None:
    """Удаляет пользователя."""
    _delete_entity(session_factory, User, user_id, UserNotFoundError)


def get_all_maintenance_types(session_factory: sessionmaker) -> list[MaintenanceType]:
    """Возвращает список всех типов обслуживания."""
    with session_factory() as session:
        return list(session.scalars(
            select(MaintenanceType).order_by(MaintenanceType.name)
        ).all())


def add_maintenance_type(
    session_factory: sessionmaker,
    name: str,
    description: str | None,
    created_by_id: int,
) -> None:
    """Создаёт новый тип обслуживания."""
    with session_factory() as session:
        new_type = MaintenanceType(
            name=name.strip(),
            description=description,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        session.add(new_type)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception(f"Ошибка БД при создании типа обслуживания {name}")
            raise

        logger.info(f"Создан тип обслуживания ID {new_type.id}")


def update_maintenance_type(
    session_factory: sessionmaker,
    type_id: int,
    name: str,
    description: str | None,
    updated_by_id: int,
) -> None:
    """Обновляет существующий тип обслуживания."""
    _update_entity(
        session_factory, MaintenanceType, type_id, MaintenanceTypeNotFoundError,
        name=name.strip(),
        description=description,
        updated_by_id=updated_by_id,
    )


def delete_maintenance_type(session_factory: sessionmaker, type_id: int) -> None:
    """Удаляет тип обслуживания."""
    _delete_entity(session_factory, MaintenanceType, type_id, MaintenanceTypeNotFoundError)


def get_all_locomotive_models(session_factory: sessionmaker) -> list[LocomotiveModel]:
    """Возвращает список всех моделей локомотивов."""
    with session_factory() as session:
        return list(session.scalars(
            select(LocomotiveModel)
            .order_by(LocomotiveModel.manufacturer, LocomotiveModel.model_name)
        ).all())


def add_locomotive_model(
    session_factory: sessionmaker,
    code: str,
    manufacturer: str,
    model_name: str,
    image_path: str | None,
    created_by_id: int,
) -> None:
    """Создаёт новую модель локомотива."""
    with session_factory() as session:
        model = LocomotiveModel(
            code=code,
            manufacturer=manufacturer,
            model_name=model_name,
            image_path=image_path,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        session.add(model)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Ошибка БД при создании модели локомотива")
            raise

        logger.info(f"Создана модель локомотива ID {model.id}")


def update_locomotive_model(
    session_factory: sessionmaker,
    model_id: int,
    code: str,
    manufacturer: str,
    model_name: str,
    image_path: str | None,
    updated_by_id: int,
) -> None:
    """Обновляет существующую модель локомотива."""
    _update_entity(
        session_factory, LocomotiveModel, model_id, LocomotiveModelNotFoundError,
        code=code,
        manufacturer=manufacturer,
        model_name=model_name,
        image_path=image_path,
        updated_by_id=updated_by_id,
    )


def get_all_locomotives(session_factory: sessionmaker) -> list[Locomotive]:
    """Возвращает список всех локомотивов с подгруженными связями."""
    with session_factory() as session:
        return list(session.scalars(
            select(Locomotive)
            .options(
                joinedload(Locomotive.model),
                joinedload(Locomotive.created_by),
                joinedload(Locomotive.updated_by),
            )
            .order_by(Locomotive.system, Locomotive.number)
        ).all())


def add_locomotive(
    session_factory: sessionmaker,
    system: str,
    number: str,
    model_type: str,
    model_id: int,
    created_by_id: int,
) -> None:
    """Создаёт новый локомотив."""
    with session_factory() as session:
        locomotive = Locomotive(
            system=system,
            number=number,
            model_type=model_type,
            model_id=model_id,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        session.add(locomotive)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Ошибка БД при создании локомотива")
            raise

        logger.info(f"Создан локомотив ID {locomotive.id}")


def update_locomotive(
    session_factory: sessionmaker,
    locomotive_id: int,
    system: str,
    number: str,
    model_type: str,
    model_id: int,
    updated_by_id: int,
) -> None:
    """Обновляет существующий локомотив."""
    _update_entity(
        session_factory, Locomotive, locomotive_id, LocomotiveNotFoundError,
        system=system,
        number=number,
        model_type=model_type,
        model_id=model_id,
        updated_by_id=updated_by_id,
    )


def delete_locomotive(session_factory: sessionmaker, locomotive_id: int) -> None:
    """Удаляет локомотив."""
    _delete_entity(session_factory, Locomotive, locomotive_id, LocomotiveNotFoundError)


def get_all_details(session_factory: sessionmaker) -> list[Detail]:
    """Возвращает список всех деталей."""
    with session_factory() as session:
        return list(session.scalars(select(Detail).order_by(Detail.name)).all())


def add_detail(
    session_factory: sessionmaker,
    code: str,
    manufacturer: str,
    name: str,
    quantity_in_stock: int,
    created_by_id: int,
) -> None:
    """Создаёт новую деталь."""
    with session_factory() as session:
        detail = Detail(
            code=code,
            manufacturer=manufacturer,
            name=name,
            quantity_in_stock=quantity_in_stock,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        session.add(detail)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Ошибка БД при создании детали")
            raise

        logger.info(f"Создана деталь ID {detail.id}")


def update_detail(
    session_factory: sessionmaker,
    detail_id: int,
    code: str,
    manufacturer: str,
    name: str,
    quantity_in_stock: int,
    updated_by_id: int,
) -> None:
    """Обновляет существующую деталь."""
    _update_entity(
        session_factory, Detail, detail_id, DetailNotFoundError,
        code=code,
        manufacturer=manufacturer,
        name=name,
        quantity_in_stock=quantity_in_stock,
        updated_by_id=updated_by_id,
    )


def delete_detail(session_factory: sessionmaker, detail_id: int) -> None:
    """Удаляет деталь."""
    _delete_entity(session_factory, Detail, detail_id, DetailNotFoundError)


def get_all_maintenances(session_factory: sessionmaker) -> list[Maintenance]:
    """Возвращает список всех активных листов обслуживания."""
    with session_factory() as session:
        return list(session.scalars(
            select(Maintenance)
            .options(
                joinedload(Maintenance.locomotive),
                joinedload(Maintenance.maintenance_type),
                joinedload(Maintenance.created_by),
            )
            .where(Maintenance.is_deleted.is_(False))
            .order_by(Maintenance.maintenance_date.desc())
        ).all())


def add_maintenance(
    session_factory: sessionmaker,
    locomotive_id: int,
    maintenance_type_id: int,
    maintenance_date: datetime,
    description: str | None,
    created_by_id: int,
) -> None:
    """Создаёт новую запись об обслуживании."""
    with session_factory() as session:
        maintenance = Maintenance(
            locomotive_id=locomotive_id,
            maintenance_type_id=maintenance_type_id,
            maintenance_date=maintenance_date,
            description=description,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        session.add(maintenance)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            logger.exception("Ошибка БД при создании обслуживания")
            raise

        logger.info(f"Создано обслуживание ID {maintenance.id}")


def update_maintenance(
    session_factory: sessionmaker,
    maintenance_id: int,
    locomotive_id: int,
    maintenance_type_id: int,
    maintenance_date: datetime,
    description: str | None,
    updated_by_id: int,
) -> None:
    """Обновляет существующую запись об обслуживании."""
    _update_entity(
        session_factory, Maintenance, maintenance_id, MaintenanceNotFoundError,
        locomotive_id=locomotive_id,
        maintenance_type_id=maintenance_type_id,
        maintenance_date=maintenance_date,
        description=description,
        updated_by_id=updated_by_id,
    )


def mark_maintenance_deleted(
    session_factory: sessionmaker,
    maintenance_id: int,
    updated_by_id: int,
) -> None:
    """Помечает лист обслуживания как удалённый."""
    _update_entity(
        session_factory, Maintenance, maintenance_id, MaintenanceNotFoundError,
        is_deleted=True,
        updated_by_id=updated_by_id,
    )


def drop_tables(engine):
    """Удаляет все таблицы. Осторожно: данные пропадут."""
    Base.metadata.drop_all(engine)
    logger.info("Все таблицы сброшены")


def create_tables(engine):
    """Создаёт все таблицы. Существующие не трогает."""
    Base.metadata.create_all(engine)
    logger.info("Все таблицы созданы")


def init_db(engine, session_factory) -> None:
    """Инициализирует БД: создаёт таблицы и первого админа admin/admin."""
    create_tables(engine)
    try:
        add_user(
            session_factory,
            login="admin",
            password="admin",
            first_name="John",
            last_name="Blade",
            is_admin=True,
        )
    except LoginAlreadyTakenError:
        logger.info("Пользователь admin уже существует, пропускаем создание")
