from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


def now() -> datetime:
    """Возвращает текущее локальное время с часовым поясом."""
    return datetime.now().astimezone()


class LocalDateTime(TypeDecorator):
    """Кастомный тип для хранения времени в UTC, а выдачи в локальной зоне.

    SQLAlchemy сохраняет все даты в БД как naive UTC.
    При чтении автоматически добавляет часовой пояс и конвертирует в локальное время.
    Это предотвращает проблемы со временем при переносе БД между серверами.
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Конвертация перед записью в БД: убирает TZ и переводит в UTC."""
        if value is None:
            return None
        if value.tzinfo is None:
            # Если время уже без зоны, считаем его UTC
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        """Конвертация после чтения из БД: помечает как UTC и переводит в локаль."""
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc).astimezone()


class AuditMixin:
    """Миксин для добавления полей аудита к основным сущностям.

    Добавляет 4 колонки: created_at, updated_at, created_by_id, updated_by_id.
    Связи (relationships) объявляются в каждом классе отдельно,
    чтобы избежать конфликтов имен в миксине.
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Дата и время создания записи."""
        return mapped_column(LocalDateTime, default=now, nullable=False)

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Дата и время последнего изменения записи."""
        return mapped_column(LocalDateTime, default=now, onupdate=now, nullable=False)

    @declared_attr
    def created_by_id(cls) -> Mapped[int | None]:
        """ID пользователя, создавшего запись."""
        return mapped_column(
            ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
        )

    @declared_attr
    def updated_by_id(cls) -> Mapped[int | None]:
        """ID пользователя, последним изменившего запись."""
        return mapped_column(
            ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
        )


class User(Base, AuditMixin):
    """Пользователь системы."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # SHA-256 hex digest = 64 символа
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Соль для PBKDF2 (16 байт в hex = 32 символа)
    password_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Самореференсные связи для аудита пользователей
    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="User.created_by_id", remote_side="User.id"
    )
    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="User.updated_by_id", remote_side="User.id"
    )

    # Обратные связи: что создал/изменил этот пользователь
    created_manufacturers: Mapped[list["Manufacturer"]] = relationship(
        foreign_keys="Manufacturer.created_by_id", back_populates="created_by"
    )
    created_locomotive_models: Mapped[list["LocomotiveModel"]] = relationship(
        foreign_keys="LocomotiveModel.created_by_id", back_populates="created_by"
    )
    created_details: Mapped[list["Detail"]] = relationship(
        foreign_keys="Detail.created_by_id", back_populates="created_by"
    )
    created_maintenances: Mapped[list["Maintenance"]] = relationship(
        foreign_keys="Maintenance.created_by_id", back_populates="created_by"
    )
    created_locomotives: Mapped[list["Locomotive"]] = relationship(
        foreign_keys="Locomotive.created_by_id", back_populates="created_by"
    )

    updated_manufacturers: Mapped[list["Manufacturer"]] = relationship(
        foreign_keys="Manufacturer.updated_by_id", back_populates="updated_by"
    )
    updated_locomotive_models: Mapped[list["LocomotiveModel"]] = relationship(
        foreign_keys="LocomotiveModel.updated_by_id", back_populates="updated_by"
    )
    updated_details: Mapped[list["Detail"]] = relationship(
        foreign_keys="Detail.updated_by_id", back_populates="updated_by"
    )
    updated_maintenances: Mapped[list["Maintenance"]] = relationship(
        foreign_keys="Maintenance.updated_by_id", back_populates="updated_by"
    )
    updated_locomotives: Mapped[list["Locomotive"]] = relationship(
        foreign_keys="Locomotive.updated_by_id", back_populates="updated_by"
    )


class Manufacturer(Base, AuditMixin):
    """Справочник производителей деталей и локомотивов."""
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Manufacturer.created_by_id", back_populates="created_manufacturers"
    )
    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Manufacturer.updated_by_id", back_populates="updated_manufacturers"
    )

    # Одна деталь может подходить к нескольким моделям локомотивов
    locomotive_models: Mapped[list["LocomotiveModel"]] = relationship(back_populates="manufacturer_rel")
    details: Mapped[list["Detail"]] = relationship(back_populates="manufacturer_rel")


class LocomotiveModel(Base, AuditMixin):
    """Модель локомотива (справочник типов)."""
    __tablename__ = "locomotive_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Связь с производителем через FK
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturers.id"), nullable=False, index=True
    )
    manufacturer_rel: Mapped["Manufacturer"] = relationship(back_populates="locomotive_models")

    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="LocomotiveModel.created_by_id", back_populates="created_locomotive_models"
    )
    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="LocomotiveModel.updated_by_id", back_populates="updated_locomotive_models"
    )

    # Конкретные локомотивы этой модели
    locomotives: Mapped[list["Locomotive"]] = relationship(back_populates="model")
    # Детали, подходящие к этой модели (many-to-many через LocomotiveDetails)
    details: Mapped[list["LocomotiveDetails"]] = relationship(
        back_populates="locomotive_model", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Артикул уникален в рамках одного производителя
        UniqueConstraint("manufacturer_id", "code", name="uq_models_manufacturer_code"),
    )


class LocomotiveDetails(Base):
    """Таблица-связь: Модель локомотива ↔ Деталь.

    Реализует many-to-many: одна деталь подходит к нескольким моделям,
    одна модель использует несколько деталей.
    Хранит количество деталей, необходимых для одной единицы модели.
    """
    __tablename__ = "locomotive_details"

    # Составной первичный ключ: пара (модель, деталь) уникальна
    locomotive_model_id: Mapped[int] = mapped_column(
        ForeignKey("locomotive_models.id", ondelete="CASCADE"), primary_key=True
    )
    detail_id: Mapped[int] = mapped_column(
        ForeignKey("details.id", ondelete="CASCADE"), primary_key=True
    )
    # Сколько штук этой детали нужно на одну модель
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    locomotive_model: Mapped["LocomotiveModel"] = relationship(back_populates="details")
    detail: Mapped["Detail"] = relationship(back_populates="locomotive_models")

    __table_args__ = (
        CheckConstraint("quantity > 0"),
    )


class Locomotive(Base, AuditMixin):
    """Конкретный экземпляр локомотива."""
    __tablename__ = "locomotives"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system: Mapped[str] = mapped_column(String(50), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("locomotive_models.id"), nullable=False, index=True
    )

    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Locomotive.created_by_id", back_populates="created_locomotives"
    )
    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Locomotive.updated_by_id", back_populates="updated_locomotives"
    )

    model: Mapped["LocomotiveModel"] = relationship(back_populates="locomotives")
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="locomotive")

    __table_args__ = (
        # Номер уникален в пределах системы
        UniqueConstraint("system", "number", name="uq_locomotives_system_number"),
    )


class Detail(Base, AuditMixin):
    """Деталь на складе."""
    __tablename__ = "details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    quantity_in_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturers.id"), nullable=False, index=True
    )
    manufacturer_rel: Mapped["Manufacturer"] = relationship(back_populates="details")

    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Detail.created_by_id", back_populates="created_details"
    )
    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Detail.updated_by_id", back_populates="updated_details"
    )

    # К каким моделям локомотивов подходит эта деталь (many-to-many)
    locomotive_models: Mapped[list["LocomotiveDetails"]] = relationship(
        back_populates="detail", cascade="all, delete-orphan"
    )
    # В каких обслуживаниях использовалась
    maintenance_details: Mapped[list["MaintenanceDetail"]] = relationship(
        back_populates="detail", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Артикул уникален в рамках производителя
        UniqueConstraint("manufacturer_id", "code", name="uq_details_manufacturer_code"),
    )


class MaintenanceType(Base):
    """Справочник типов обслуживания (без аудита)."""
    __tablename__ = "maintenance_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="maintenance_type")


class Maintenance(Base, AuditMixin):
    """Лист обслуживания конкретного локомотива."""
    __tablename__ = "maintenances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    locomotive_id: Mapped[int] = mapped_column(
        ForeignKey("locomotives.id"), nullable=False, index=True
    )
    maintenance_type_id: Mapped[int] = mapped_column(
        ForeignKey("maintenance_types.id"), nullable=False, index=True
    )
    maintenance_date: Mapped[datetime] = mapped_column(LocalDateTime, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Maintenance.created_by_id", back_populates="created_maintenances"
    )
    updated_by: Mapped["User | None"] = relationship(
        "User", foreign_keys="Maintenance.updated_by_id", back_populates="updated_maintenances"
    )

    locomotive: Mapped["Locomotive"] = relationship(back_populates="maintenances")
    maintenance_type: Mapped["MaintenanceType"] = relationship(back_populates="maintenances")
    # Детали, использованные в этом обслуживании
    maintenance_details: Mapped[list["MaintenanceDetail"]] = relationship(
        back_populates="maintenance", cascade="all, delete-orphan"
    )


class MaintenanceDetail(Base):
    """Таблица-связь: Обслуживание ↔ Деталь (без аудита).

    Фиксирует, сколько деталей было списано при конкретном обслуживании.
    """
    __tablename__ = "maintenance_details"

    maintenance_id: Mapped[int] = mapped_column(
        ForeignKey("maintenances.id", ondelete="CASCADE"), primary_key=True
    )
    detail_id: Mapped[int] = mapped_column(
        ForeignKey("details.id", ondelete="CASCADE"), primary_key=True
    )
    quantity_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    maintenance: Mapped["Maintenance"] = relationship(back_populates="maintenance_details")
    detail: Mapped["Detail"] = relationship(back_populates="maintenance_details")

    __table_args__ = (
        CheckConstraint("quantity_used > -1"),
    )
