"""Репозитории, слой доступа к данным.

BaseRepository даёт CRUD, декларативную проверку уникальности и хуки.
Наследник обычно задаёт только атрибуты класса.
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
    DetailNotFoundError, AlreadyAddedError, EntityInUseError,
    InvalidPasswordError, LastActiveAdminError, LocomotiveModelNotFoundError,
    LocomotiveNotFoundError, LoginAlreadyTakenError, MaintenanceNotFoundError,
    MaintenanceTypeNotFoundError, ManufacturerNotFoundError, NotFoundError,
    SupplyNotFoundError, UserNotActiveError, UserNotFoundError,
)
from app.db.models import (
    Detail, Locomotive, LocomotiveModel, LocomotiveModelDetail, Maintenance,
    MaintenanceDetail, MaintenanceType, Manufacturer, Supply, User,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _count(session: Session, stmt) -> int:
    """Обёртка над scalar для COUNT. None заменяет на 0."""
    return session.scalar(stmt) or 0


@dataclass(frozen=True)
class InUseCheck:
    """Ссылка из другой таблицы, мешающая удалению записи.

    model: ORM класс связанной таблицы.
    field: имя FK колонки в этой таблице.
    label: человекочитаемое имя для текста ошибки.
    """
    model: type
    field: str
    label: str


class BaseRepository(Generic[T]):
    """Общий CRUD и хуки для всех репозиториев.

    Настройки задаются атрибутами класса, кроме model и not_found_error
    все опциональны.

    model: ORM класс сущности.
    not_found_error: исключение, если запись не найдена.
    default_order_by: сортировка для list_all.
    default_options: joinedload или contains_eager для list_all.
    in_use_checks: связи, блокирующие физическое удаление.
    soft_delete_field: если задан, delete ставит флаг, а не удаляет.
    unique_fields: кортеж кортежей имён полей, уникальных вместе.
    unique_message: шаблон текста AlreadyAddedError.
    strip_fields: имена строковых полей, у которых срезаем пробелы.
    lower_fields: имена строковых полей, приводимых к нижнему регистру.
    join_field: имя связи для JOIN в list_all вместе с contains_eager.
    """

    model: type[T]
    not_found_error: type[NotFoundError] = NotFoundError
    default_order_by: Sequence = ()
    default_options: Sequence = ()
    in_use_checks: Sequence[InUseCheck] = ()
    soft_delete_field: str | None = None
    unique_fields: tuple[tuple[str, ...], ...] = ()
    unique_message: str = "Запись с такими данными уже существует"
    strip_fields: tuple[str, ...] = ()
    lower_fields: tuple[str, ...] = ()
    join_field: str | None = None

    def __init__(self, session_factory: sessionmaker):
        # Храним фабрику, а не сессию. Каждый метод открывает свою сессию.
        self._session_factory = session_factory

    # Публичные методы CRUD.

    def get(self, item_id: int) -> T | None:
        """Возвращает запись по идентификатору или None."""
        with self._session_factory() as s:
            return s.get(self.model, item_id)

    def get_or_raise(self, item_id: int) -> T:
        """Возвращает запись по идентификатору или бросает not_found_error."""
        if (item := self.get(item_id)) is None:
            raise self.not_found_error(item_id)
        return item

    def list_all(self) -> list[T]:
        """Возвращает все записи с сортировкой и eager загрузкой."""
        stmt = self._build_list_query()
        if self.default_options:
            stmt = stmt.options(*self.default_options)
        if self.default_order_by:
            stmt = stmt.order_by(*self.default_order_by)
        with self._session_factory() as s:
            return list(s.scalars(stmt).all())

    def create(self, **fields) -> T:
        """Создаёт запись из переданных полей и возвращает её."""
        with self._session_factory() as s:
            # Нормализуем поля до валидации, чтобы проверки видели то же,
            # что попадёт в базу.
            prepared = self._normalize(dict(fields), for_update=False)
            self._validate_create(s, prepared)
            item = self.model(**prepared)
            s.add(item)
            self._commit(s, "создан")
            s.refresh(item)
            s.expunge(item)
            return item

    def update(self, item_id: int, **fields) -> T:
        """Обновляет переданные поля и возвращает запись.

        Поля со значением None игнорируются. Работает как частичное
        обновление.
        """
        with self._session_factory() as s:
            item = self._require(s, item_id)
            prepared = self._normalize(dict(fields), for_update=True)
            self._validate_update(s, item, prepared)
            for k, v in prepared.items():
                setattr(item, k, v)
            self._commit(s, "обновлён")
            s.refresh(item)
            s.expunge(item)
            return item

    def delete(self, item_id: int) -> None:
        """Удаляет запись или помечает её удалённой, если задан флаг."""
        with self._session_factory() as s:
            item = self._require(s, item_id)
            self._validate_delete(s, item)
            if self.soft_delete_field:
                # Мягкое удаление. Физическую запись оставляем в базе.
                setattr(item, self.soft_delete_field, True)
                action = "помечен как удалённый"
            else:
                # Перед DELETE проверяем внешние ключи, чтобы дать
                # понятную ошибку вместо IntegrityError.
                self._check_not_in_use(s, item_id)
                s.delete(item)
                action = "удалён"
            self._commit(s, action)

    # Хуки, которые могут переопределять наследники.

    def _build_list_query(self):
        """Строит базовый SELECT. По умолчанию с опциональным JOIN."""
        if self.join_field:
            rel = getattr(self.model, self.join_field)
            # contains_eager работает поверх явного join, без второго JOIN.
            return select(self.model).join(rel).options(contains_eager(rel))
        return select(self.model)

    def _validate_create(self, s: Session, fields: dict) -> None:
        """Проверки перед созданием. По умолчанию проверяет уникальность."""
        self._check_unique(s, fields)

    def _validate_update(self, s: Session, item: T, fields: dict) -> None:
        """Проверки перед обновлением. По умолчанию проверяет уникальность."""
        self._check_unique(s, fields, exclude_id=item.id, current=item)

    def _validate_delete(self, s: Session, item: T) -> None:
        """Проверки перед удалением. По умолчанию не делает ничего."""
        pass

    # Вспомогательные методы для наследников.

    def _normalize(self, fields: dict, for_update: bool) -> dict:
        """Нормализует поля перед валидацией и записью.

        При обновлении убирает None. Срезает пробелы и приводит к нижнему
        регистру поля из strip_fields и lower_fields.
        """
        if for_update:
            fields = {k: v for k, v in fields.items() if v is not None}
        for name in self.strip_fields:
            if isinstance(v := fields.get(name), str):
                fields[name] = v.strip()
        for name in self.lower_fields:
            if isinstance(v := fields.get(name), str):
                fields[name] = v.lower()
        return fields

    def _check_unique(
        self, s: Session, fields: dict,
        exclude_id: int | None = None, current: T | None = None,
    ) -> None:
        """Проверяет уникальность каждой комбинации из unique_fields.

        При обновлении недостающие поля берутся из current. Это нужно,
        чтобы проверить составной ключ, когда пришло только одно поле.
        """
        for combo in self.unique_fields:
            # Собираем значения полей комбинации из переданных полей или
            # из текущей записи.
            values: dict | None = {}
            for name in combo:
                if name in fields:
                    values[name] = fields[name]
                elif current is not None:
                    values[name] = getattr(current, name)
                else:
                    values = None
                    break
            if not values:
                continue
            conds = [getattr(self.model, n) == v for n, v in values.items()]
            # При обновлении исключаем саму запись из поиска.
            if exclude_id is not None:
                conds.append(self.model.id != exclude_id)
            if s.scalar(select(self.model.id).where(*conds)):
                raise AlreadyAddedError(self.unique_message.format(**values))

    def _require(self, s: Session, item_id: int) -> T:
        """Возвращает запись из открытой сессии или бросает not_found_error."""
        if (item := s.get(self.model, item_id)) is None:
            raise self.not_found_error(item_id)
        return item

    def _check_not_in_use(self, s: Session, item_id: int) -> None:
        """Считает ссылки из связанных таблиц и бросает EntityInUseError."""
        problems = []
        for c in self.in_use_checks:
            col = getattr(c.model, c.field)
            n = _count(s, select(func.count()).select_from(c.model).where(col == item_id))
            if n:
                problems.append(f"{c.label}: {n}")
        if problems:
            raise EntityInUseError(
                f"Нельзя удалить {self.model.__name__}: " + ", ".join(problems)
            )

    def _commit(self, s: Session, action: str) -> None:
        """Коммитит сессию. Логирует и пробрасывает ошибки БД.

        Уникальность проверяется в _validate_*, поэтому IntegrityError
        сюда долетать не должен. Если долетел, это сигнал о баге или о
        гонке между проверкой и вставкой, и лучше увидеть настоящий
        трейсбек, чем замаскировать его под AlreadyAddedError.
        """
        try:
            s.commit()
            logger.info(f"{action}: {self.model.__name__}")
        except SQLAlchemyError:
            s.rollback()
            logger.exception(f"Ошибка БД при '{action}' {self.model.__name__}")
            raise


class ManufacturerRepository(BaseRepository[Manufacturer]):
    """Репозиторий производителей. Имя уникально и лоуэркейсится моделью."""

    model = Manufacturer
    not_found_error = ManufacturerNotFoundError
    default_order_by = (Manufacturer.name,)
    in_use_checks = (
        InUseCheck(LocomotiveModel, "manufacturer_id", "моделей"),
        InUseCheck(Detail, "manufacturer_id", "деталей"),
    )
    unique_fields = (("name",),)
    unique_message = "Производитель «{name}» уже существует"
    strip_fields = ("name",)

    def get_by_name(self, name: str) -> Manufacturer | None:
        """Ищет производителя по имени. Регистр приводит модель."""
        with self._session_factory() as s:
            return s.scalar(select(Manufacturer).where(Manufacturer.name == name.strip()))

    def get_or_create_by_name(self, name: str) -> Manufacturer:
        """Возвращает производителя по имени или создаёт нового."""
        return self.get_by_name(name) or self.create(name=name)


class MaintenanceTypeRepository(BaseRepository[MaintenanceType]):
    """Репозиторий типов обслуживания. Имя уникально."""

    model = MaintenanceType
    not_found_error = MaintenanceTypeNotFoundError
    default_order_by = (MaintenanceType.name,)
    in_use_checks = (
        InUseCheck(Maintenance, "maintenance_type_id", "листов обслуживания"),
    )
    unique_fields = (("name",),)
    unique_message = "Тип обслуживания «{name}» уже существует"
    strip_fields = ("name",)

    def get_by_name(self, name: str) -> MaintenanceType | None:
        """Ищет тип обслуживания по имени."""
        with self._session_factory() as s:
            return s.scalar(select(MaintenanceType).where(MaintenanceType.name == name.strip()))


class LocomotiveModelRepository(BaseRepository[LocomotiveModel]):
    """Репозиторий моделей локомотивов. Артикул уникален у производителя."""

    model = LocomotiveModel
    not_found_error = LocomotiveModelNotFoundError
    default_order_by = (Manufacturer.name, LocomotiveModel.name)
    in_use_checks = (
        InUseCheck(Locomotive, "locomotive_model_id", "локомотивов"),
        InUseCheck(LocomotiveModelDetail, "locomotive_model_id", "связей с деталями"),
    )
    unique_fields = (("manufacturer_id", "code"),)
    unique_message = "Артикул «{code}» у этого производителя уже занят"
    strip_fields = ("name",)
    join_field = "manufacturer"


class LocomotiveRepository(BaseRepository[Locomotive]):
    """Репозиторий локомотивов. Номер локомотива уникален."""

    model = Locomotive
    not_found_error = LocomotiveNotFoundError
    default_order_by = (Locomotive.system, Locomotive.number)
    default_options = (
        joinedload(Locomotive.model).joinedload(LocomotiveModel.manufacturer),
    )
    in_use_checks = (
        InUseCheck(Maintenance, "locomotive_id", "листов обслуживания"),
    )
    unique_fields = (("number",),)
    unique_message = "Локомотив с номером {number} уже есть"


class DetailRepository(BaseRepository[Detail]):
    """Репозиторий деталей. Артикул уникален у производителя."""

    model = Detail
    not_found_error = DetailNotFoundError
    default_order_by = (Detail.name,)
    in_use_checks = (
        InUseCheck(LocomotiveModelDetail, "detail_id", "связей с моделями"),
        InUseCheck(MaintenanceDetail, "detail_id", "связей с обслуживанием"),
    )
    unique_fields = (("manufacturer_id", "code"),)
    unique_message = "Деталь с артикулом «{code}» у этого производителя уже есть"
    strip_fields = ("name",)
    join_field = "manufacturer"


class MaintenanceRepository(BaseRepository[Maintenance]):
    """Репозиторий листов обслуживания.

    Удаление мягкое, вместо DELETE ставится флаг is_deleted.
    list_all показывает только активные записи.
    """

    model = Maintenance
    not_found_error = MaintenanceNotFoundError
    soft_delete_field = "is_deleted"
    default_order_by = (Maintenance.created_at.desc(),)
    default_options = (
        joinedload(Maintenance.locomotive)
        .joinedload(Locomotive.model).joinedload(LocomotiveModel.manufacturer),
        joinedload(Maintenance.maintenance_type),
        joinedload(Maintenance.user),
    )

    def _build_list_query(self):
        """Возвращает только неудалённые листы."""
        return select(self.model).where(Maintenance.is_deleted.is_(False))

    @property
    def session_factory(self) -> sessionmaker:
        """Даёт сервису фабрику для общих транзакций обслуживания."""
        return self._session_factory

    def get_with_details_in_session(
        self, s: Session, maintenance_id: int,
    ) -> Maintenance | None:
        """Читает лист вместе с деталями внутри открытой транзакции."""
        stmt = (
            select(Maintenance)
            .where(Maintenance.id == maintenance_id)
            .options(joinedload(Maintenance.details))
        )
        return s.scalars(stmt).unique().first()


class UserRepository(BaseRepository[User]):
    """Репозиторий пользователей.

    Отвечает за хеширование пароля, уникальность логина и запрет
    убирать последнего активного администратора.
    """

    model = User
    not_found_error = UserNotFoundError
    default_order_by = (User.id,)
    in_use_checks = (
        InUseCheck(Maintenance, "user_id", "листов обслуживания"),
    )
    # Логин в модели обычный String, поэтому лоуэркейсим руками.
    lower_fields = ("login",)

    def get_by_login(self, login: str) -> User | None:
        """Ищет пользователя по логину без учёта регистра и пробелов."""
        with self._session_factory() as s:
            return s.scalar(select(User).where(User.login == login.strip().lower()))

    def authenticate(self, login: str, password: str) -> User:
        """Проверяет логин и пароль, возвращает пользователя.

        Бросает UserNotFoundError, UserNotActiveError или
        InvalidPasswordError.
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

    def _normalize(self, fields: dict, for_update: bool) -> dict:
        """Хеширует пароль и нормализует логин поверх базовой логики."""
        fields = super()._normalize(fields, for_update)
        if "password" in fields:
            pw = fields.pop("password")
            fields["password_hash"], fields["password_salt"] = hash_password(pw)
        return fields

    def _validate_create(self, s: Session, fields: dict) -> None:
        """Проверяет, что логин ещё не занят."""
        login = fields["login"]
        if s.scalar(select(User.id).where(User.login == login)):
            raise LoginAlreadyTakenError(login)

    def _validate_update(self, s: Session, item: User, fields: dict) -> None:
        """Проверяет уникальность логина и правило последнего админа."""
        new_login = fields.get("login")
        if new_login and new_login != item.login:
            if s.scalar(select(User.id).where(User.login == new_login, User.id != item.id)):
                raise LoginAlreadyTakenError(new_login)

        # Если активный админ перестаёт быть активным админом, проверяем,
        # что в системе останется хотя бы один такой же.
        was = item.is_admin and item.is_active
        will = fields.get("is_admin", item.is_admin) and fields.get("is_active", item.is_active)
        if was and not will and self._admins_count(s, exclude_id=item.id) == 0:
            raise LastActiveAdminError(item.id)

    def _validate_delete(self, s: Session, item: User) -> None:
        """Запрещает удалять последнего активного администратора."""
        if item.is_admin and item.is_active and self._admins_count(s, exclude_id=item.id) == 0:
            raise LastActiveAdminError(item.id)

    @staticmethod
    def _admins_count(s: Session, exclude_id: int | None = None) -> int:
        """Считает активных администраторов в открытой сессии."""
        stmt = select(func.count()).select_from(User).where(User.is_admin, User.is_active)
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return _count(s, stmt)


class SupplyRepository(BaseRepository[Supply]):
    """Репозиторий приходов.

    Каждая строка это одна деталь. Партия определяется по supply_number.
    """

    model = Supply
    not_found_error = SupplyNotFoundError
    default_order_by = (Supply.supply_number.desc(), Supply.id)

    def list_by_number(self, supply_number: int) -> list[Supply]:
        """Возвращает все строки одной партии прихода."""
        with self._session_factory() as s:
            return self._rows(s, supply_number)

    @property
    def session_factory(self) -> sessionmaker:
        """Даёт сервису фабрику для общей транзакции прихода и склада."""
        return self._session_factory

    def list_by_number_in_session(self, s: Session, supply_number: int) -> list[Supply]:
        """Читает строки партии внутри уже открытой транзакции."""
        return self._rows(s, supply_number)

    @staticmethod
    def _rows(s: Session, n: int) -> list[Supply]:
        """Общий SELECT строк партии, используется двумя методами выше."""
        stmt = select(Supply).where(Supply.supply_number == n).order_by(Supply.id)
        return list(s.scalars(stmt).all())

    def add_batch_rows(
        self, s: Session, supply_number: int, rows: dict[int, int],
        user_id: int, created_at: datetime | None = None,
    ) -> None:
        """Добавляет строки партии в переданную транзакцию."""
        for detail_id, quantity in rows.items():
            kw = {"created_at": created_at} if created_at else {}
            s.add(Supply(
                supply_number=supply_number, detail_id=detail_id,
                quantity=quantity, user_id=user_id, **kw,
            ))

    @staticmethod
    def delete_batch_rows(s: Session, rows: list[Supply]) -> None:
        """Удаляет строки партии, не коммитя переданную транзакцию."""
        for row in rows:
            s.delete(row)
