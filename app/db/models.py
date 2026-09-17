from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


def now() -> datetime:
    """Текущее локальное время."""
    return datetime.now().astimezone()


class LocalDateTime(TypeDecorator):
    """Хранит время в UTC, отдаёт в локальной зоне."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """При записи: переводит в UTC без зоны."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        """При чтении: помечает как UTC и переводит в локальную зону."""
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc).astimezone()


class AuditMixin:
    """Поля аудита: кто и когда создал/изменил запись.

    Даёт только колонки (created_at, updated_at, created_by_id, updated_by_id).
    Relationship created_by / updated_by объявляются в каждом классе отдельно —
    так избегаем проблем с резолвом имён в миксине.
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Когда запись создана."""
        return mapped_column(LocalDateTime, default=now, nullable=False)

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Когда запись последний раз меняли."""
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
    password_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(24), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Аудит — кто создал и менял этого пользователя
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="User.created_by_id",
        remote_side="User.id",
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="User.updated_by_id",
        remote_side="User.id",
    )

    # Что этот пользователь создал
    created_maintenances: Mapped[list["Maintenance"]] = relationship(
        foreign_keys="Maintenance.created_by_id",
        back_populates="created_by",
    )
    created_locomotives: Mapped[list["Locomotive"]] = relationship(
        foreign_keys="Locomotive.created_by_id",
        back_populates="created_by",
    )
    created_locomotive_models: Mapped[list["LocomotiveModel"]] = relationship(
        foreign_keys="LocomotiveModel.created_by_id",
        back_populates="created_by",
    )
    created_details: Mapped[list["Detail"]] = relationship(
        foreign_keys="Detail.created_by_id",
        back_populates="created_by",
    )
    created_maintenance_types: Mapped[list["MaintenanceType"]] = relationship(
        foreign_keys="MaintenanceType.created_by_id",
        back_populates="created_by",
    )

    # Что этот пользователь последним изменил
    updated_maintenances: Mapped[list["Maintenance"]] = relationship(
        foreign_keys="Maintenance.updated_by_id",
        back_populates="updated_by",
    )
    updated_locomotives: Mapped[list["Locomotive"]] = relationship(
        foreign_keys="Locomotive.updated_by_id",
        back_populates="updated_by",
    )
    updated_locomotive_models: Mapped[list["LocomotiveModel"]] = relationship(
        foreign_keys="LocomotiveModel.updated_by_id",
        back_populates="updated_by",
    )
    updated_details: Mapped[list["Detail"]] = relationship(
        foreign_keys="Detail.updated_by_id",
        back_populates="updated_by",
    )
    updated_maintenance_types: Mapped[list["MaintenanceType"]] = relationship(
        foreign_keys="MaintenanceType.updated_by_id",
        back_populates="updated_by",
    )


class LocomotiveModel(Base, AuditMixin):
    """Модель локомотива — справочник."""

    __tablename__ = "locomotive_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Аудит
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="LocomotiveModel.created_by_id",
        back_populates="created_locomotive_models",
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="LocomotiveModel.updated_by_id",
        back_populates="updated_locomotive_models",
    )

    # Связи
    locomotives: Mapped[list["Locomotive"]] = relationship(back_populates="model")
    details: Mapped[list["LocomotiveDetails"]] = relationship(
        back_populates="locomotive_model",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Одна модель одного производителя должна быть уникальной
        UniqueConstraint(
            "manufacturer", "code",
            name="uq_locomotive_models_manufacturer_code",
        ),
    )


class LocomotiveDetails(Base):
    """Связка «модель — деталь» с количеством."""

    __tablename__ = "locomotive_details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    locomotive_model_id: Mapped[int] = mapped_column(
        ForeignKey("locomotive_models.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    detail_id: Mapped[int] = mapped_column(
        ForeignKey("details.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Связи
    locomotive_model: Mapped["LocomotiveModel"] = relationship(back_populates="details")
    detail: Mapped["Detail"] = relationship(back_populates="locomotive_models")

    __table_args__ = (
        # В одной модели деталь встречается только один раз
        UniqueConstraint(
            "locomotive_model_id", "detail_id",
            name="uq_locomotive_details_model_detail",
        ),
        # Количество всегда больше нуля
        CheckConstraint("quantity > 0"),
    )


class Locomotive(Base, AuditMixin):
    """Конкретный локомотив."""

    __tablename__ = "locomotives"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system: Mapped[str] = mapped_column(String(50), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("locomotive_models.id"),
        nullable=False, index=True,
    )

    # Аудит
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="Locomotive.created_by_id",
        back_populates="created_locomotives",
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="Locomotive.updated_by_id",
        back_populates="updated_locomotives",
    )

    # Связи
    model: Mapped["LocomotiveModel"] = relationship(back_populates="locomotives")
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="locomotive")

    __table_args__ = (
        # Номер локомотива уникален в пределах системы
        UniqueConstraint("system", "number", name="uq_locomotives_system_number"),
    )


class Detail(Base, AuditMixin):
    """Деталь — справочник с остатком на складе."""

    __tablename__ = "details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    quantity_in_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Аудит
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="Detail.created_by_id",
        back_populates="created_details",
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="Detail.updated_by_id",
        back_populates="updated_details",
    )

    # Связи
    locomotive_models: Mapped[list["LocomotiveDetails"]] = relationship(
        back_populates="detail",
        cascade="all, delete-orphan",
    )
    maintenance_details: Mapped[list["MaintenanceDetail"]] = relationship(
        back_populates="detail",
        cascade="all, delete-orphan",
    )
    maintenances: Mapped[list["Maintenance"]] = relationship(
        secondary="maintenance_details",
        back_populates="details",
        viewonly=True,
    )


class MaintenanceType(Base, AuditMixin):
    """Тип обслуживания — справочник."""

    __tablename__ = "maintenance_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Аудит
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="MaintenanceType.created_by_id",
        back_populates="created_maintenance_types",
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="MaintenanceType.updated_by_id",
        back_populates="updated_maintenance_types",
    )

    # Связи
    maintenances: Mapped[list["Maintenance"]] = relationship(
        back_populates="maintenance_type",
    )


class Maintenance(Base, AuditMixin):
    """Лист обслуживания локомотива."""

    __tablename__ = "maintenances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    locomotive_id: Mapped[int] = mapped_column(
        ForeignKey("locomotives.id"),
        nullable=False, index=True,
    )
    maintenance_type_id: Mapped[int] = mapped_column(
        ForeignKey("maintenance_types.id"),
        nullable=False, index=True,
    )
    maintenance_date: Mapped[datetime] = mapped_column(LocalDateTime, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Аудит
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="Maintenance.created_by_id",
        back_populates="created_maintenances",
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="Maintenance.updated_by_id",
        back_populates="updated_maintenances",
    )

    # Связи
    locomotive: Mapped["Locomotive"] = relationship(back_populates="maintenances")
    maintenance_type: Mapped["MaintenanceType"] = relationship(
        back_populates="maintenances",
    )
    maintenance_details: Mapped[list["MaintenanceDetail"]] = relationship(
        back_populates="maintenance",
        cascade="all, delete-orphan",
    )
    details: Mapped[list["Detail"]] = relationship(
        secondary="maintenance_details",
        back_populates="maintenances",
        viewonly=True,
    )


class MaintenanceDetail(Base):
    """Связка «обслуживание — деталь» с количеством."""

    __tablename__ = "maintenance_details"

    maintenance_id: Mapped[int] = mapped_column(
        ForeignKey("maintenances.id", ondelete="CASCADE"),
        primary_key=True,
    )
    detail_id: Mapped[int] = mapped_column(
        ForeignKey("details.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Связи
    maintenance: Mapped["Maintenance"] = relationship(back_populates="maintenance_details")
    detail: Mapped["Detail"] = relationship(back_populates="maintenance_details")

    __table_args__ = (
        # Количество всегда больше нуля
        CheckConstraint("quantity_used > 0"),
    )
