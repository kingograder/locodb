"""Контейнер репозиториев приложения.

Создаётся один раз при старте и передаётся во все экраны и диалоги.
Единственное, что нужно UI — этот объект; про сессии и SQLAlchemy он не знает.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm.session import sessionmaker

from app.db.exceptions import (
    DetailNotFoundError,
    MaintenanceNotFoundError,
    SupplyNotFoundError,
)
from app.db.models import (
    Detail,
    Locomotive,
    LocomotiveModelDetail,
    Maintenance,
    MaintenanceDetail,
    Supply,
    User,
)
from app.db.repositories import (
    DetailRepository,
    LocomotiveModelRepository,
    LocomotiveRepository,
    MaintenanceRepository,
    MaintenanceTypeRepository,
    ManufacturerRepository,
    SupplyRepository,
    UserRepository,
)

logger = logging.getLogger(__name__)


class Services:
    """Единая точка доступа к репозиториям."""

    def __init__(self, session_factory: sessionmaker):
        self.users = UserRepository(session_factory)
        self.manufacturers = ManufacturerRepository(session_factory)
        self.maintenance_types = MaintenanceTypeRepository(session_factory)
        self.locomotive_models = LocomotiveModelRepository(session_factory)
        self.locomotives = LocomotiveRepository(session_factory)
        self.details = DetailRepository(session_factory)
        self.maintenances_repo = MaintenanceRepository(session_factory)
        self.maintenances = MaintenanceService(self.maintenances_repo)
        self.supplies_repo = SupplyRepository(session_factory)
        self.supplies = SupplyService(self.supplies_repo)

class MaintenanceService:
    """Работа с листами обслуживания и расходом деталей."""

    def __init__(self, repository: MaintenanceRepository):
        self._repository = repository
        self._session_factory = repository.session_factory

    def list_all(self) -> list[Maintenance]:
        """Возвращает активные листы для вкладки обслуживания."""
        return self._repository.list_all()

    def get_rows(self, maintenance_id: int) -> dict[int, int]:
        """Возвращает расход деталей листа в формате {detail_id: quantity}."""
        with self._session_factory() as session:
            maintenance = self._repository.get_with_details_in_session(
                session, maintenance_id
            )
            if maintenance is None:
                raise MaintenanceNotFoundError(maintenance_id)
            return {
                row.detail_id: row.quantity_used
                for row in maintenance.details
            }

    def save_with_details(
        self,
        *,
        maintenance_id: int | None,
        fields: dict,
        rows: dict[int, int],
        allow_negative_stock: bool = False,
    ) -> dict[int, int]:
        """Сохраняет лист и расход в одной транзакции.

        Возвращает дефицит по деталям без фиксации, если нужно подтверждение.
        При allow_negative_stock=True сохраняет даже отрицательный остаток.
        """
        with self._session_factory() as session:
            old_rows: list[MaintenanceDetail] = []
            maintenance = None

            if maintenance_id is not None:
                maintenance = self._repository.get_with_details_in_session(
                    session, maintenance_id
                )
                if maintenance is None or maintenance.is_deleted:
                    raise MaintenanceNotFoundError(maintenance_id)
                old_rows = list(maintenance.details)

            # Возвращаем прежний расход перед проверкой нового состава.
            for old_row in old_rows:
                detail = session.get(Detail, old_row.detail_id)
                if detail is not None:
                    detail.quantity_in_stock += old_row.quantity_used

            deficits: dict[int, int] = {}
            for detail_id, quantity in rows.items():
                detail = session.get(Detail, detail_id)
                if detail is None:
                    raise DetailNotFoundError(detail_id)
                if detail.quantity_in_stock < quantity:
                    deficits[detail_id] = quantity - detail.quantity_in_stock

            if deficits and not allow_negative_stock:
                return deficits

            if maintenance is None:
                maintenance = Maintenance(**fields)
                session.add(maintenance)
                session.flush()
            else:
                for name, value in fields.items():
                    setattr(maintenance, name, value)

            # Полностью заменяем расходные строки листа.
            for old_row in old_rows:
                session.delete(old_row)

            locomotive = session.get(Locomotive, maintenance.locomotive_id)
            model_id = locomotive.locomotive_model_id if locomotive else None

            for detail_id, quantity in rows.items():
                detail = session.get(Detail, detail_id)
                if detail is None:
                    raise DetailNotFoundError(detail_id)

                detail.quantity_in_stock -= quantity
                session.add(
                    MaintenanceDetail(
                        maintenance_id=maintenance.id,
                        detail_id=detail_id,
                        quantity_used=quantity,
                    )
                )

                # Эталон хранит только факт соответствия модели и детали.
                if model_id is not None:
                    existing = session.scalar(
                        select(LocomotiveModelDetail.id).where(
                            LocomotiveModelDetail.locomotive_model_id == model_id,
                            LocomotiveModelDetail.detail_id == detail_id,
                        )
                    )
                    if existing is None:
                        session.add(
                            LocomotiveModelDetail(
                                locomotive_model_id=model_id,
                                detail_id=detail_id,
                                quantity=1,
                            )
                        )

            session.commit()
            return deficits

    def delete(self, maintenance_id: int) -> None:
        """Мягко удаляет лист и возвращает использованные детали на склад."""
        with self._session_factory() as session:
            maintenance = self._repository.get_with_details_in_session(
                session, maintenance_id
            )
            if maintenance is None or maintenance.is_deleted:
                raise MaintenanceNotFoundError(maintenance_id)

            for row in maintenance.details:
                detail = session.get(Detail, row.detail_id)
                if detail is not None:
                    detail.quantity_in_stock += row.quantity_used

            maintenance.is_deleted = True
            session.commit()


class SupplyService:
    """Операции с приходом деталей на склад."""

    def __init__(self, supplies: SupplyRepository):
        self._supplies = supplies
        self._session_factory = supplies.session_factory

    # Чтение партии

    def get_rows_by_number(self, supply_number: int) -> dict[int, int]:
        """Возвращает {detail_id: quantity} для указанной партии.

        Одна партия может содержать одну и ту же деталь только один раз,
        поэтому словарь безопасен как источник данных.
        """
        rows = self._supplies.list_by_number(supply_number)
        return {row.detail_id: row.quantity for row in rows}

    def list_batches(self) -> list[dict]:
        """Возвращает список партий для таблицы вкладки «Приход».

        Каждый элемент — словарь с полями, которые нужны UI:
            number          — номер прихода (supply_number)
            created_at      — дата создания партии (самая ранняя строка)
            positions       — сколько разных деталей в партии
            total_quantity  — сумма количеств всех позиций
            user_login      — логин пользователя, создавшего приход
        """
        stmt = (
            select(
                Supply.supply_number.label("number"),
                func.min(Supply.created_at).label("created_at"),
                func.count(Supply.id).label("positions"),
                func.sum(Supply.quantity).label("total_quantity"),
                func.min(User.login).label("user_login"),
            )
            .join(User, Supply.user_id == User.id)
            .group_by(Supply.supply_number)
            .order_by(Supply.supply_number.desc())
        )
        with self._session_factory() as session:
            return [dict(row._mapping) for row in session.execute(stmt).all()]

    # Создание партии

    def create_batch(
        self,
        rows: dict[int, int],
        user_id: int,
    ) -> int:
        """Создаёт партию прихода: N записей Supply с одним supply_number.

        В той же транзакции увеличивает quantity_in_stock у каждой детали.
        Если хотя бы одна деталь не найдена — откат, ничего не сохраняется.
        """
        if not rows:
            raise ValueError("Партия не может быть пустой")
        with self._session_factory() as session:
            # Блокируем конкурирующую запись до назначения следующего номера.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            max_number = session.scalar(select(func.max(Supply.supply_number)))
            supply_number = (max_number or 0) + 1

            for detail_id, quantity in rows.items():
                # Проверяем, что деталь существует, до создания записи.
                detail = session.get(Detail, detail_id)
                if detail is None:
                    raise DetailNotFoundError(detail_id)

                # Остаток на складе — кеш, обновляем синхронно.
                detail.quantity_in_stock += quantity

            self._supplies.add_batch_rows(session, supply_number, rows, user_id)

            session.commit()
            logger.info(
                f"Приход №{supply_number}: создан, позиций — {len(rows)}"
            )
            return supply_number

    # Обновление партии

    def update_batch(
        self,
        supply_number: int,
        rows: dict[int, int],
    ) -> None:
        """Перезаписывает партию прихода целиком.

        Алгоритм: сначала снимаем эффект старой партии со склада
        (возвращаем quantity обратно), затем удаляем старые строки
        и создаём новые. Всё в одной транзакции.
        """
        if not rows:
            raise ValueError("Партия не может быть пустой")
        with self._session_factory() as session:
            old_rows = self._supplies.list_by_number_in_session(
                session, supply_number
            )
            if not old_rows:
                raise SupplyNotFoundError(supply_number)

            # Сохраняем происхождение и исходную дату партии.
            creator_id = old_rows[0].user_id
            created_at = old_rows[0].created_at

            # Проверяем новые детали и возвращаем прежнее количество на склад.
            for old in old_rows:
                detail = session.get(Detail, old.detail_id)
                if detail is not None:
                    detail.quantity_in_stock -= old.quantity

            # Добавляем новую партию в той же транзакции, сохраняя аудит автора.
            for detail_id, quantity in rows.items():
                detail = session.get(Detail, detail_id)
                if detail is None:
                    raise DetailNotFoundError(detail_id)

                detail.quantity_in_stock += quantity

            self._supplies.delete_batch_rows(session, old_rows)
            self._supplies.add_batch_rows(
                session,
                supply_number,
                rows,
                creator_id,
                created_at=created_at,
            )

            session.commit()
            logger.info(
                f"Приход №{supply_number}: обновлён, позиций — {len(rows)}"
            )

    # Удаление партии

    def delete_batch(self, supply_number: int) -> None:
        """Удаляет партию и возвращает остатки на склад.

        Уменьшаем quantity_in_stock на величину каждой строки партии.
        Если партии нет — бросаем SupplyNotFoundError.
        """
        with self._session_factory() as session:
            rows = self._supplies.list_by_number_in_session(session, supply_number)
            if not rows:
                raise SupplyNotFoundError(supply_number)

            for row in rows:
                detail = session.get(Detail, row.detail_id)
                if detail is not None:
                    detail.quantity_in_stock -= row.quantity
            self._supplies.delete_batch_rows(session, rows)

            session.commit()
            logger.info(f"Приход №{supply_number}: удалён")
