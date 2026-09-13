"""
Сервис для работы с деталями.
Предоставляет методы для получения и управления данными о деталях.
"""
from sqlalchemy import select

from app.db.models import Detail, LocomotiveModel, LocomotiveDetails


class DetailService:
    """Сервис для работы с деталями."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def get_all_details(self) -> list[dict]:
        """
        Получить все детали.
        
        Returns:
            Список словарей с данными о деталях.
        """
        with self.session_factory() as session:
            query = select(
                Detail.id,
                Detail.code,
                Detail.name,
                Detail.manufacturer,
                Detail.quantity_in_stock
            ).order_by(Detail.name)
            
            result = session.execute(query)
            details = []
            
            for row in result:
                details.append({
                    "id": row.id,
                    "code": row.code,
                    "name": row.name,
                    "manufacturer": row.manufacturer,
                    "quantity_in_stock": row.quantity_in_stock
                })
            
            return details

    def add_detail(
        self,
        code: str,
        name: str,
        manufacturer: str,
        quantity_in_stock: int = 0
    ) -> Detail | None:
        """
        Добавить новую деталь.
        
        Args:
            code: Код детали
            name: Название
            manufacturer: Производитель
            quantity_in_stock: Количество на складе
            
        Returns:
            Созданный объект Detail или None при ошибке.
        """
        with self.session_factory() as session:
            try:
                # Проверка на уникальность кода
                existing = session.scalar(
                    select(Detail).where(Detail.code == code)
                )
                if existing:
                    return None

                detail = Detail(
                    code=code,
                    name=name,
                    manufacturer=manufacturer,
                    quantity_in_stock=quantity_in_stock
                )
                session.add(detail)
                session.commit()
                session.refresh(detail)
                return detail
            except Exception as e:
                session.rollback()
                print(f"Ошибка при добавлении детали: {e}")
                return None
