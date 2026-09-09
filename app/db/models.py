from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=True) # Лучше разрешить NULL
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="user")

class LocomotiveModel(Base):
    __tablename__ = "locomotive_models"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    manufacture: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locomotives: Mapped[list["Locomotive"]] = relationship(back_populates="model")

class Locomotive(Base):
    __tablename__ = "locomotives"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    system: Mapped[str] = mapped_column(String(50), nullable=False)
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[int] = mapped_column(ForeignKey("locomotive_models.id"), nullable=False)
    model: Mapped["LocomotiveModel"] = relationship(back_populates="locomotives")
    maintenances: Mapped[list["Maintenance"]] = relationship(back_populates="locomotive")

class Detail(Base):
    __tablename__ = "details"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity_in_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    maintenances: Mapped[list["Maintenance"]] = relationship(
        secondary="maintenance_details", back_populates="details"
    )

class Maintenance(Base):
    __tablename__ = "maintenances"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    locomotive_id: Mapped[int] = mapped_column(ForeignKey("locomotives.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    maintenance_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locomotive: Mapped["Locomotive"] = relationship(back_populates="maintenances")
    user: Mapped["User"] = relationship(back_populates="maintenances")
    details: Mapped[list["Detail"]] = relationship(
        secondary="maintenance_details", back_populates="maintenances"
    )

class MaintenanceDetail(Base):
    __tablename__ = "maintenance_details"
    maintenance_id: Mapped[int] = mapped_column(ForeignKey("maintenances.id"), primary_key=True)
    detail_id: Mapped[int] = mapped_column(ForeignKey("details.id"), primary_key=True)
    quantity_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    maintenance: Mapped["Maintenance"] = relationship(viewonly=True)
    detail: Mapped["Detail"] = relationship(viewonly=True)
