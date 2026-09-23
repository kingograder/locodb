from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator
from app.db.base import Base


def now() -> datetime:
    """Возвращает текущее локальное время с часовым поясом."""
    return datetime.now().astimezone()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
    )


class LowercaseString(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower()
        return value

class LocomotiveModelDetail(Base):
    """Связь Модель - Деталь"""
    __tablename__ = "locomotive_model_details"
    id: Mapped[int] = mapped_column(primary_key=True)
    locomotive_model: Mapped["LocomotiveModel"] = relationship(back_populates="details")
    detail: Mapped["Detail"] = relationship(back_populates="locomotive_models")
    quantity: Mapped[int]

    locomotive_model_id: Mapped[int] = mapped_column(ForeignKey("locomotive_models.id"))
    detail_id: Mapped[int] = mapped_column(ForeignKey("details.id"))


class MaintenanceDetail(Base):
    """Связь Детали - Обслуживания"""
    __tablename__ = "maintenance_details"
    id: Mapped[int] = mapped_column(primary_key=True)
    maintenance: Mapped["Maintenance"] = relationship(back_populates="details")
    detail: Mapped["Detail"] = relationship(back_populates="maintenances")
    quantity_used: Mapped[int]

    detail_id: Mapped[int] = mapped_column(ForeignKey("details.id"))
    maintenance_id: Mapped[int] = mapped_column(ForeignKey("maintenances.id"))


class LocomotiveModel(Base):
    """Модели локомотивов"""
    __tablename__ = "locomotive_models"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[int]
    name: Mapped[str] = mapped_column(LowercaseString(255))
    image_path: Mapped[str | None] = mapped_column(String(255) ,unique=True)
    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="locomotive_models")
    locomotives: Mapped[list["Locomotive"]] = relationship(back_populates="model")
    details: Mapped[list["LocomotiveModelDetail"]] = relationship(back_populates="locomotive_model")

    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"))

    __table_args__ = (UniqueConstraint("code", "manufacturer_id"))

class Detail(Base):
    """Детали"""
    __tablename__ = "details"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[int]
    name: Mapped[str] = mapped_column(LowercaseString(255))
    quantity_in_stock: Mapped[int]
    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="details")
    locomotive_models: Mapped[list["LocomotiveModelDetail"]] = relationship(back_populates="detail")
    maintenances: Mapped[list["MaintenanceDetail"]] = relationship(back_populates="detail")

    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"))

    __table_args__ = (UniqueConstraint("code", "manufacturer_id"))


class Manufacturer(Base):
    """Производитель"""
    __tablename__ = "manufacturers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(LowercaseString(255), unique=True)
    locomotive_models: Mapped[list["LocomotiveModel"]] = relationship(back_populates="manufacturer")
    details: Mapped[list["Detail"]] = relationship(back_populates="manufacturer")


class User(Base):
    """Пользователи"""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    first_name: Mapped[str | None] = mapped_column(LowercaseString(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(LowercaseString(50), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="user")


class Maintenance(Base):
    """Листы обслуживания"""
    __tablename__ = "maintenances"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    maintenance_type: Mapped["MaintenanceType"] = relationship(back_populates="maintenances")
    locomotive: Mapped["Locomotive"] = relationship(back_populates="maintenances")
    user: Mapped["User"] = relationship(back_populates="maintenances")
    details: Mapped[list["MaintenanceDetail"]] = relationship(back_populates="maintenance")

    maintenance_type_id: Mapped[int] = mapped_column(ForeignKey("maintenance_types.id"))
    locomotive_id: Mapped[int] = mapped_column(ForeignKey("locomotives.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Locomotive(Base):
    """Локомотивы"""
    __tablename__ = "locomotives"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int]
    system: Mapped[int]
    model: Mapped["LocomotiveModel"] = relationship(back_populates="locomotives")
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="locomotive")

    locomotive_model_id: Mapped[int] = mapped_column(ForeignKey("locomotive_models.id"))


class MaintenanceType(Base):
    """Тип обслуживания"""
    __tablename__ = "maintenance_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(LowercaseString(255))
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="maintenance_type")
