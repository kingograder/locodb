"""
Сервис для работы с листами обслуживания.
Предоставляет методы для получения и управления данными об обслуживании.
"""
from datetime import datetime
from sqlalchemy import select, func

from app.db.models import Maintenance, Locomotive, User, MaintenanceDetail, Detail


class MaintenanceService:
    """Сервис для работы с листами обслуживания."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def get_all_maintenances(self) -> list[dict]:
        """
        Получить все записи об обслуживании.
        
        Returns:
            Список словарей с данными об обслуживании.
        """
        with self.session_factory() as session:
            query = (
                select(
                    Maintenance.id,
                    Maintenance.maintenance_date,
                    Maintenance.maintenance_type,
                    Maintenance.description,
                    Locomotive.number.label("locomotive_number"),
                    Locomotive.system.label("locomotive_system"),
                    User.first_name.label("user_first_name"),
                    User.last_name.label("user_last_name")
                )
                .join(Locomotive, Maintenance.locomotive_id == Locomotive.id)
                .join(User, Maintenance.user_id == User.id)
                .where(Maintenance.is_deleted == False)
                .order_by(Maintenance.maintenance_date.desc())
            )
            
            result = session.execute(query)
            maintenances = []
            
            for row in result:
                maintenances.append({
                    "id": row.id,
                    "maintenance_date": row.maintenance_date,
                    "maintenance_type": row.maintenance_type,
                    "description": row.description,
                    "locomotive_number": row.locomotive_number,
                    "locomotive_system": row.locomotive_system,
                    "user_first_name": row.user_first_name,
                    "user_last_name": row.user_last_name
                })
            
            return maintenances

    def add_maintenance(
        self,
        locomotive_id: int,
        user_id: int,
        maintenance_date: datetime,
        maintenance_type: str,
        description: str | None = None,
        details: list[tuple[int, int]] | None = None
    ) -> Maintenance | None:
        """
        Добавить новую запись об обслуживании.
        
        Args:
            locomotive_id: ID локомотива
            user_id: ID пользователя
            maintenance_date: Дата обслуживания
            maintenance_type: Тип обслуживания
            description: Описание
            details: Список кортежей (detail_id, quantity_used)
            
        Returns:
            Созданный объект Maintenance или None при ошибке.
        """
        with self.session_factory() as session:
            try:
                maintenance = Maintenance(
                    locomotive_id=locomotive_id,
                    user_id=user_id,
                    maintenance_date=maintenance_date,
                    maintenance_type=maintenance_type,
                    description=description
                )
                session.add(maintenance)
                session.flush()  # Получаем ID записи

                # Добавляем использованные детали
                if details:
                    for detail_id, quantity_used in details:
                        maint_detail = MaintenanceDetail(
                            maintenance_id=maintenance.id,
                            detail_id=detail_id,
                            quantity_used=quantity_used
                        )
                        session.add(maint_detail)

                session.commit()
                session.refresh(maintenance)
                return maintenance
            except Exception as e:
                session.rollback()
                print(f"Ошибка при добавлении записи об обслуживании: {e}")
                return None

    def get_locomotives_for_select(self) -> list[dict]:
        """Получить список локомотивов для выпадающего списка."""
        with self.session_factory() as session:
            query = select(
                Locomotive.id,
                Locomotive.number,
                Locomotive.system
            ).order_by(Locomotive.number)
            
            result = session.execute(query)
            return [
                {"id": row.id, "number": row.number, "system": row.system}
                for row in result
            ]

    def get_users_for_select(self) -> list[dict]:
        """Получить список пользователей для выпадающего списка."""
        from app.db.models import User
        with self.session_factory() as session:
            query = select(
                User.id,
                User.first_name,
                User.last_name
            ).where(User.is_active == True).order_by(User.last_name)
            
            result = session.execute(query)
            return [
                {"id": row.id, "first_name": row.first_name, "last_name": row.last_name}
                for row in result
            ]

    def get_details_for_select(self) -> list[dict]:
        """Получить список деталей для выпадающего списка."""
        with self.session_factory() as session:
            query = select(
                Detail.id,
                Detail.code,
                Detail.name
            ).order_by(Detail.name)
            
            result = session.execute(query)
            return [
                {"id": row.id, "code": row.code, "name": row.name}
                for row in result
            ]
