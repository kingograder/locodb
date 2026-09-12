"""
Сервис для работы с локомотивами.
Предоставляет методы для получения и управления данными о локомотивах.
"""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.db.models import Locomotive, LocomotiveModel, Maintenance


class LocomotiveService:
    """Сервис для работы с локомотивами."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def get_all_locomotives_with_last_maintenance(self) -> list[dict]:
        """
        Получить все локомотивы с информацией о модели и датой последнего ТО.
        
        Returns:
            Список словарей с данными о локомотивах.
        """
        with self.session_factory() as session:
            # Подзапрос для получения последней даты обслуживания для каждого локомотива
            subquery = (
                select(
                    Maintenance.locomotive_id,
                    func.max(Maintenance.maintenance_date).label("last_maintenance_date")
                )
                .where(Maintenance.is_deleted == False)
                .group_by(Maintenance.locomotive_id)
                .subquery()
            )

            # Основной запрос с объединением всех таблиц
            query = (
                select(
                    Locomotive.id,
                    Locomotive.number,
                    Locomotive.system,
                    Locomotive.model_type,
                    LocomotiveModel.model_name,
                    LocomotiveModel.manufacturer,
                    subquery.c.last_maintenance_date
                )
                .join(LocomotiveModel, Locomotive.model_id == LocomotiveModel.id)
                .outerjoin(subquery, Locomotive.id == subquery.c.locomotive_id)
                .order_by(LocomotiveModel.model_name, Locomotive.number)
            )

            result = session.execute(query)
            locomotives = []
            
            for row in result:
                locomotives.append({
                    "id": row.id,
                    "number": row.number,
                    "system": row.system,
                    "model_type": row.model_type,
                    "model_name": row.model_name,
                    "manufacturer": row.manufacturer,
                    "last_maintenance_date": row.last_maintenance_date
                })
            
            return locomotives

    def add_locomotive(
        self,
        model_id: int,
        number: str,
        system: str,
        model_type: str
    ) -> Locomotive | None:
        """
        Добавить новый локомотив.
        
        Args:
            model_id: ID модели локомотива
            number: Инвентарный номер
            system: Система
            model_type: Тип модели
            
        Returns:
            Созданный объект Locomotive или None при ошибке.
        """
        with self.session_factory() as session:
            try:
                # Проверка на уникальность
                existing = session.scalar(
                    select(Locomotive).where(
                        (Locomotive.number == number) & 
                        (Locomotive.system == system)
                    )
                )
                if existing:
                    return None

                locomotive = Locomotive(
                    model_id=model_id,
                    number=number,
                    system=system,
                    model_type=model_type
                )
                session.add(locomotive)
                session.commit()
                session.refresh(locomotive)
                return locomotive
            except Exception as e:
                session.rollback()
                print(f"Ошибка при добавлении локомотива: {e}")
                return None

    def get_all_models(self) -> list[dict]:
        """
        Получить все модели локомотивов.
        
        Returns:
            Список словарей с данными о моделях.
        """
        with self.session_factory() as session:
            query = select(
                LocomotiveModel.id,
                LocomotiveModel.code,
                LocomotiveModel.model_name,
                LocomotiveModel.manufacturer
            ).order_by(LocomotiveModel.model_name)
            
            result = session.execute(query)
            models = []
            
            for row in result:
                models.append({
                    "id": row.id,
                    "code": row.code,
                    "model_name": row.model_name,
                    "manufacturer": row.manufacturer
                })
            
            return models
