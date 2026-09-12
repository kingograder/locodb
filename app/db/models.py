from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(24), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    maintenances: Mapped[list["Maintenance"]] = relationship(
        back_populates="user"
    )


class LocomotiveModel(Base):
    __tablename__ = "locomotive_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    locomotives: Mapped[list["Locomotive"]] = relationship(
        back_populates="model"
    )
    details: Mapped[list["LocomotiveDetails"]] = relationship(
        back_populates="locomotive_model",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "manufacturer",
            "code",
            name="uq_locomotive_models_manufacturer_code",
        ),
    )


class LocomotiveDetails(Base):
    __tablename__ = "locomotive_details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    locomotive_model_id: Mapped[int] = mapped_column(
        ForeignKey("locomotive_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detail_id: Mapped[int] = mapped_column(
        ForeignKey("details.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    locomotive_model: Mapped["LocomotiveModel"] = relationship(
        back_populates="details"
    )
    detail: Mapped["Detail"] = relationship(
        back_populates="locomotive_models"
    )

    __table_args__ = (
        UniqueConstraint(
            "locomotive_model_id",
            "detail_id",
            name="uq_locomotive_details_model_detail",
        ),
        CheckConstraint("quantity > 0"),
    )


class Locomotive(Base):
    __tablename__ = "locomotives"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system: Mapped[str] = mapped_column(String(50), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[int] = mapped_column(
        ForeignKey("locomotive_models.id"),
        nullable=False,
        index=True,
    )

    model: Mapped["LocomotiveModel"] = relationship(
        back_populates="locomotives"
    )
    maintenances: Mapped[list["Maintenance"]] = relationship(
        back_populates="locomotive"
    )

    __table_args__ = (
        UniqueConstraint(
            "system",
            "number",
            name="uq_locomotives_system_number",
        ),
    )


class Detail(Base):
    __tablename__ = "details"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    quantity_in_stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

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


class Maintenance(Base):
    __tablename__ = "maintenances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    locomotive_id: Mapped[int] = mapped_column(
        ForeignKey("locomotives.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    maintenance_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    maintenance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    locomotive: Mapped["Locomotive"] = relationship(
        back_populates="maintenances"
    )
    user: Mapped["User"] = relationship(
        back_populates="maintenances"
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
    __tablename__ = "maintenance_details"

    maintenance_id: Mapped[int] = mapped_column(
        ForeignKey("maintenances.id", ondelete="CASCADE"),
        primary_key=True,
    )
    detail_id: Mapped[int] = mapped_column(
        ForeignKey("details.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    maintenance: Mapped["Maintenance"] = relationship(
        back_populates="maintenance_details"
    )
    detail: Mapped["Detail"] = relationship(
        back_populates="maintenance_details"
    )

    __table_args__ = (
        CheckConstraint("quantity_used > 0"),
    )
