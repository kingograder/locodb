"""Репозитории — слой доступа к данным.

Каждая сущность получает класс-наследник BaseRepository.
Базовый класс реализует стандартный CRUD и набор хуков:
наследнику обычно достаточно задать атрибуты класса
и, при необходимости, переопределить один-два метода.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, contains_eager, joinedload, sessionmaker

from app.autorization import check_password, hash_password
from app.db.exceptions import (
    DetailNotFoundError,
    EntityInUseError,
    InvalidPasswordError,
    LastActiveAdminError,
    LocomotiveModelNotFoundError,
    LocomotiveNotFoundError,
    LoginAlreadyTakenError,
    MaintenanceNotFoundError,
    MaintenanceTypeNotFoundError,
    ManufacturerNotFoundError,
    NotFoundError,
    SupplyNotFoundError,
    UserNotActiveError,
    UserNotFoundError,
)
from app.db.models import (
    Detail,
    Locomotive,
    LocomotiveModel,
    LocomotiveModelDetail,
    Maintenance,
    MaintenanceDetail,
    MaintenanceType,
    Manufacturer,
    Supply,
    User,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _scalar_int(session: Session, stmt) -> int:
    """Возвращает целое из COUNT-запроса, подставляя 0 вместо None.

    Нужно, потому что session.scalar типизируется как int | None,
    хотя COUNT(*) на пустой выборке всегда даёт 0.
    """
    result = session.scalar(stmt)
    return result if result is not None else 0


@dataclass(frozen=True)
class InUseCheck:
    """Проверка "на запись ссылаются из другой таблицы".

    Используется перед удалением, чтобы вернуть понятную ошибку,
    а не SQLAlchemy IntegrityError из-за внешнего ключа.
    """

    model: type
    field: str
    label: str


class BaseRepository(Generic[T]):
    """Общий CRUD и хуки для всех репозиториев.

    Наследнику достаточно задать атрибуты класса:

        model              — ORM-класс
        not_found_error    — исключение, если запись не найдена
        default_order_by   — сортировка по умолчанию для list_all
        default_options    — joinedload/contains_eager для list_all
        in_use_checks      — связи, блокирующие удаление
        soft_delete_field  — если задан, delete помечает запись, а не удаляет

    Точки расширения (переопределяются при необходимости):

        _build_list_query            — базовый SELECT для list_all
        _prepare_create_fields       — нормализация полей перед созданием
        _prepare_update_fields       — нормализация полей перед обновлением
        _validate_create             — проверки перед созданием
        _validate_update             — проверки перед обновлением
        _validate_delete             — проверки перед удалением
    """

    model: type[T]
    not_found_error: type[NotFoundError] = NotFoundError
    default_order_by: Sequence = ()
    default_options: Sequence = ()
    in_use_checks: Sequence[InUseCheck] = ()
    soft_delete_field: str | None = None

    def __init__(self, session_factory: sessionmaker):
        # Фабрика сессий хранится, а не готовая сессия:
        # каждый метод работает в своей короткой транзакции.
        self._session_factory = session_factory

    def get(self, item_id: int) -> T | None:
        """Возвращает запись по ID или None."""
        with self._session_factory() as session:
            return session.get(self.model, item_id)

    def get_or_raise(self, item_id: int) -> T:
        """Возвращает запись по ID или бросает not_found_error."""
        item = self.get(item_id)
        if item is None:
            raise self.not_found_error(item_id)
        return item

    def list_all(self) -> list[T]:
        """Возвращает все записи с сортировкой и eager-loading по умолчанию."""
        stmt = self._build_list_query()
        if self.default_options:
            stmt = stmt.options(*self.default_options)
        if self.default_order_by:
            stmt = stmt.order_by(*self.default_order_by)
        with self._session_factory() as session:
            return list(session.scalars(stmt).all())

    def create(self, **fields) -> T:
        """Создаёт запись и возвращает её."""
        with self._session_factory() as session:
            prepared = self._prepare_create_fields(dict(fields))
            self._validate_create(session, prepared)
            item = self.model(**prepared)
            session.add(item)
            self._commit(session, action="создан")
            session.refresh(item)
            session.expunge(item)
            return item

    def update(self, item_id: int, **fields) -> T:
        """Обновляет переданные поля и возвращает запись.

        Работает как patch: поля со значением None отбрасываются,
        поэтому можно обновлять только часть атрибутов.
        """
        with self._session_factory() as session:
            item = self._require(session, item_id)
            prepared = self._prepare_update_fields(dict(fields))
            self._validate_update(session, item, prepared)
            for name, value in prepared.items():
                setattr(item, name, value)
            self._commit(session, action="обновлён")
            session.refresh(item)
            session.expunge(item)
            return item

    def delete(self, item_id: int) -> None:
        """Удаляет запись.

        Если задан soft_delete_field — просто ставит флаг,
        иначе удаляет физически и проверяет ссылки из других таблиц.
        """
        with self._session_factory() as session:
            item = self._require(session, item_id)
            self._validate_delete(session, item)
            if self.soft_delete_field:
                setattr(item, self.soft_delete_field, True)
                action = "помечен как удалённый"
            else:
                self._check_not_in_use(session, item_id)
                session.delete(item)
                action = "удалён"
            self._commit(session, action=action)

    def _build_list_query(self):
        """Базовый SELECT для list_all. Переопределяется для join'ов и фильтров."""
        return select(self.model)

    def _prepare_create_fields(self, fields: dict) -> dict:
        """Нормализация полей перед созданием (strip/lower и т.п.)."""
        return fields

    def _prepare_update_fields(self, fields: dict) -> dict:
        """Нормализация полей перед обновлением. По умолчанию убирает None."""
        return {name: value for name, value in fields.items() if value is not None}

    def _validate_create(self, session: Session, fields: dict) -> None:
        """Проверки перед созданием. Бросает исключения при нарушении правил."""

    def _validate_update(self, session: Session, item: T, fields: dict) -> None:
        """Проверки перед обновлением."""

    def _validate_delete(self, session: Session, item: T) -> None:
        """Проверки перед удалением."""

    def _strip_fields(self, fields: dict, *names: str) -> dict:
        """Убирает пробелы по краям у строковых полей с указанными именами."""
        for name in names:
            value = fields.get(name)
            if isinstance(value, str):
                fields[name] = value.strip()
        return fields

    def _require(self, session: Session, item_id: int) -> T:
        """Возвращает запись из открытой сессии или бросает not_found_error."""
        item = session.get(self.model, item_id)
        if item is None:
            raise self.not_found_error(item_id)
        return item

    def _check_not_in_use(self, session: Session, item_id: int) -> None:
        """Считает ссылки в связанных таблицах и бросает EntityInUseError, если они есть."""
        if not self.in_use_checks:
            return
        problems = []
        for check in self.in_use_checks:
            column = getattr(check.model, check.field)
            count = _scalar_int(
                session,
                select(func.count()).select_from(check.model).where(column == item_id),
            )
            if count:
                problems.append(f"{check.label}: {count}")
        if problems:
            raise EntityInUseError(
                f"Нельзя удалить {self.model.__name__}: " + ", ".join(problems)
            )

    def _commit(self, session: Session, action: str) -> None:
        """Коммитит сессию с единообразной обработкой ошибок и логом."""
        try:
            session.commit()
            logger.info(f"{action}: {self.model.__name__}")
        except SQLAlchemyError:
            session.rollback()
            logger.exception(
                f"Ошибка БД при действии '{action}' для {self.model.__name__}"
            )
            raise


class ManufacturerRepository(BaseRepository[Manufacturer]):
    """Репозиторий производителей."""

    model = Manufacturer
    not_found_error = ManufacturerNotFoundError
    default_order_by = (Manufacturer.name,)
    in_use_checks = (
        InUseCheck(LocomotiveModel, "manufacturer_id", "моделей"),
        InUseCheck(Detail, "manufacturer_id", "деталей"),
    )

    def get_by_name(self, name: str) -> Manufacturer | None:
        """Ищет производителя по имени без учёта регистра и пробелов."""
        normalized = name.strip()
        with self._session_factory() as session:
            return session.scalar(
                select(Manufacturer).where(Manufacturer.name == normalized)
            )

    def get_or_create_by_name(self, name: str) -> Manufacturer:
        """Возвращает производителя по имени, создавая его при отсутствии.

        Удобно там, где пользователь вводит имя руками (например, в форме
        детали), а внешний ключ должен уже существовать.
        """
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        return self.create(name=name)

    def _prepare_create_fields(self, fields: dict) -> dict:
        return self._strip_fields(fields, "name")

    def _prepare_update_fields(self, fields: dict) -> dict:
        return self._strip_fields(super()._prepare_update_fields(fields), "name")


class MaintenanceTypeRepository(BaseRepository[MaintenanceType]):
    """Репозиторий типов обслуживания."""

    model = MaintenanceType
    not_found_error = MaintenanceTypeNotFoundError
    default_order_by = (MaintenanceType.name,)
    in_use_checks = (
        InUseCheck(Maintenance, "maintenance_type_id", "листов обслуживания"),
    )

    def _prepare_create_fields(self, fields: dict) -> dict:
        return self._strip_fields(fields, "name")

    def _prepare_update_fields(self, fields: dict) -> dict:
        return self._strip_fields(super()._prepare_update_fields(fields), "name")


class LocomotiveModelRepository(BaseRepository[LocomotiveModel]):
    """Репозиторий моделей локомотивов."""

    model = LocomotiveModel
    not_found_error = LocomotiveModelNotFoundError
    default_order_by = (Manufacturer.name, LocomotiveModel.name)
    in_use_checks = (
        InUseCheck(Locomotive, "locomotive_model_id", "локомотивов"),
        InUseCheck(LocomotiveModelDetail, "locomotive_model_id", "связей с деталями"),
    )

    def _build_list_query(self):
        # JOIN нужен и для contains_eager, и для сортировки по имени производителя.
        return (
            select(self.model)
            .join(self.model.manufacturer)
            .options(contains_eager(self.model.manufacturer))
        )

    def _prepare_create_fields(self, fields: dict) -> dict:
        return self._strip_fields(fields, "name")

    def _prepare_update_fields(self, fields: dict) -> dict:
        return self._strip_fields(super()._prepare_update_fields(fields), "name")


class LocomotiveRepository(BaseRepository[Locomotive]):
    """Репозиторий локомотивов."""

    model = Locomotive
    not_found_error = LocomotiveNotFoundError
    default_order_by = (Locomotive.system, Locomotive.number)
    default_options = (
        joinedload(Locomotive.model).joinedload(LocomotiveModel.manufacturer),
    )
    in_use_checks = (
        InUseCheck(Maintenance, "locomotive_id", "листов обслуживания"),
    )


class DetailRepository(BaseRepository[Detail]):
    """Репозиторий деталей."""

    model = Detail
    not_found_error = DetailNotFoundError
    default_order_by = (Detail.name,)
    in_use_checks = (
        InUseCheck(LocomotiveModelDetail, "detail_id", "связей с моделями"),
        InUseCheck(MaintenanceDetail, "detail_id", "связей с обслуживанием"),
    )

    def _build_list_query(self):
        # join + contains_eager — эффективнее, чем joinedload: без лишнего JOIN.
        return (
            select(self.model)
            .join(self.model.manufacturer)
            .options(contains_eager(self.model.manufacturer))
        )

    def _prepare_create_fields(self, fields: dict) -> dict:
        return self._strip_fields(fields, "name")

    def _prepare_update_fields(self, fields: dict) -> dict:
        return self._strip_fields(super()._prepare_update_fields(fields), "name")


class MaintenanceRepository(BaseRepository[Maintenance]):
    """Репозиторий листов обслуживания.

    Удаление мягкое: флаг is_deleted вместо физического DELETE.
    list_all возвращает только активные записи.
    """

    model = Maintenance
    not_found_error = MaintenanceNotFoundError
    soft_delete_field = "is_deleted"
    default_order_by = (Maintenance.created_at.desc(),)
    default_options = (
        joinedload(Maintenance.locomotive)
        .joinedload(Locomotive.model)
        .joinedload(LocomotiveModel.manufacturer),
        joinedload(Maintenance.maintenance_type),
        joinedload(Maintenance.user),
    )

    def _build_list_query(self):
        return select(self.model).where(Maintenance.is_deleted.is_(False))

    @property
    def session_factory(self) -> sessionmaker:
        """Даёт сервису фабрику для транзакций обслуживания и склада."""
        return self._session_factory

    def get_with_details_in_session(
        self, session: Session, maintenance_id: int
    ) -> Maintenance | None:
        """Загружает лист и его детали внутри текущей транзакции."""
        stmt = (
            select(Maintenance)
            .where(Maintenance.id == maintenance_id)
            .options(joinedload(Maintenance.details))
        )
        return session.scalars(stmt).unique().first()


class UserRepository(BaseRepository[User]):
    """Репозиторий пользователей.

    Отвечает за хеширование пароля, уникальность логина
    и запрет убирать последнего активного администратора.
    """

    model = User
    not_found_error = UserNotFoundError
    default_order_by = (User.id,)
    in_use_checks = (
        InUseCheck(Maintenance, "user_id", "листов обслуживания"),
    )

    def get_by_login(self, login: str) -> User | None:
        """Ищет пользователя по логину, приводя его к нижнему регистру."""
        normalized = login.strip().lower()
        with self._session_factory() as session:
            return session.scalar(select(User).where(User.login == normalized))

    def authenticate(self, login: str, password: str) -> User:
        """Проверяет логин и пароль. Возвращает User или бросает исключение.

        Возможные исключения (все — наследники AuthenticationError,
        кроме UserNotFoundError):
            UserNotFoundError   — логина нет в базе
            UserNotActiveError  — учётная запись отключена
            InvalidPasswordError — пароль не подходит
        """
        user = self.get_by_login(login)
        if user is None:
            logger.warning(f"Вход: пользователь {login!r} не найден")
            raise UserNotFoundError(login)

        if not user.is_active:
            logger.warning(f"Вход: учётная запись {user.login!r} отключена")
            raise UserNotActiveError(user.login)

        if not check_password(user, password):
            logger.warning(f"Вход: неверный пароль для {user.login!r}")
            raise InvalidPasswordError(user.login)

        logger.info(f"Пользователь {user.login!r} авторизован")
        return user

    def _prepare_create_fields(self, fields: dict) -> dict:
        # На вход ждём "password", в модель кладём хеш и соль.
        fields["login"] = fields["login"].strip().lower()
        password = fields.pop("password")
        fields["password_hash"], fields["password_salt"] = hash_password(password)
        return fields

    def _prepare_update_fields(self, fields: dict) -> dict:
        fields = super()._prepare_update_fields(fields)
        if "login" in fields:
            fields["login"] = fields["login"].strip().lower()
        if "password" in fields:
            password = fields.pop("password")
            fields["password_hash"], fields["password_salt"] = hash_password(password)
        return fields

    def _validate_create(self, session: Session, fields: dict) -> None:
        login = fields["login"]
        if session.scalar(select(User.id).where(User.login == login)):
            raise LoginAlreadyTakenError(login)

    def _validate_update(self, session: Session, item: User, fields: dict) -> None:
        new_login = fields.get("login")
        if new_login and new_login != item.login:
            exists = session.scalar(
                select(User.id).where(User.login == new_login, User.id != item.id)
            )
            if exists:
                raise LoginAlreadyTakenError(new_login)

        # Если активный админ перестаёт быть активным админом — проверяем,
        # что в системе останется хотя бы один такой же.
        was_active_admin = item.is_admin and item.is_active
        will_be_admin = fields.get("is_admin", item.is_admin)
        will_be_active = fields.get("is_active", item.is_active)
        if was_active_admin and not (will_be_admin and will_be_active) and self._count_active_admins(session, exclude_user_id=item.id) == 0:
            raise LastActiveAdminError(item.id)

    def _validate_delete(self, session: Session, item: User) -> None:
        # Нельзя удалить последнего активного админа — иначе система
        # останется без администраторов.
        if item.is_admin and item.is_active and self._count_active_admins(session, exclude_user_id=item.id) == 0:
            raise LastActiveAdminError(item.id)

    def _count_active_admins(
        self, session: Session, exclude_user_id: int | None = None
    ) -> int:
        """Считает активных админов в уже открытой сессии.

        Отдельный метод нужен, чтобы не открывать вложенную сессию
        внутри _validate_update — иначе можно получить рассинхрон данных.
        """
        stmt = select(func.count()).select_from(User).where(User.is_admin, User.is_active)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return _scalar_int(session, stmt)

class SupplyRepository(BaseRepository[Supply]):
    """Репозиторий приходов."""

    model = Supply
    not_found_error = SupplyNotFoundError
    default_order_by = (Supply.supply_number.desc(), Supply.id)

    def list_by_number(self, supply_number: int) -> list[Supply]:
        """Возвращает все строки одной партии прихода."""
        with self._session_factory() as session:
            stmt = (
                select(Supply)
                .where(Supply.supply_number == supply_number)
                .order_by(Supply.id)
            )
            return list(session.scalars(stmt).all())

    @property
    def session_factory(self) -> sessionmaker:
        """Даёт сервису фабрику для общей транзакции прихода и остатков."""
        return self._session_factory

    def list_by_number_in_session(
        self, session: Session, supply_number: int
    ) -> list[Supply]:
        """Читает строки партии внутри уже открытой транзакции."""
        stmt = (
            select(Supply)
            .where(Supply.supply_number == supply_number)
            .order_by(Supply.id)
        )
        return list(session.scalars(stmt).all())

    def add_batch_rows(
        self,
        session: Session,
        supply_number: int,
        rows: dict[int, int],
        user_id: int,
        created_at: datetime | None = None,
    ) -> None:
        """Добавляет строки партии в переданную транзакцию."""
        for detail_id, quantity in rows.items():
            session.add(
                Supply(
                    supply_number=supply_number,
                    detail_id=detail_id,
                    quantity=quantity,
                    user_id=user_id,
                    **({"created_at": created_at} if created_at is not None else {}),
                )
            )

    @staticmethod
    def delete_batch_rows(session: Session, rows: list[Supply]) -> None:
        """Удаляет строки партии, не фиксируя переданную транзакцию."""
        for row in rows:
            session.delete(row)
