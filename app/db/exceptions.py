"""Исключения слоя доступа к данным.

Все ошибки наследуются от RepositoryError, чтобы вызывающий код
мог ловить либо конкретную проблему, либо сразу всю группу.
"""




class RepositoryError(Exception):
    """Базовое исключение всех репозиториев."""


class AlreadyAddedError(RepositoryError):
    """Уже есть в базе данных"""


class NotFoundError(RepositoryError):
    """Запись с указанным ID не найдена.

    Наследники переопределяют item_label — он попадёт в текст ошибки.
    """

    item_label = "Запись"

    def __init__(self, item_id):
        self.item_id = item_id
        super().__init__(f"{self.item_label} с ID {item_id} не найден")


class UserNotFoundError(NotFoundError):
    item_label = "Пользователь"


class ManufacturerNotFoundError(NotFoundError):
    item_label = "Производитель"


class MaintenanceTypeNotFoundError(NotFoundError):
    item_label = "Тип обслуживания"


class LocomotiveModelNotFoundError(NotFoundError):
    item_label = "Модель локомотива"


class LocomotiveNotFoundError(NotFoundError):
    item_label = "Локомотив"


class DetailNotFoundError(NotFoundError):
    item_label = "Деталь"


class MaintenanceNotFoundError(NotFoundError):
    item_label = "Лист обслуживания"


class EntityInUseError(RepositoryError):
    """Запись используется в других таблицах и не может быть удалена."""


class LoginAlreadyTakenError(RepositoryError):
    """Логин занят другим пользователем."""


class LastActiveAdminError(RepositoryError):
    """Нельзя убрать последнего активного администратора."""

class AuthenticationError(RepositoryError):
    """Базовое исключение для неудачной попытки входа."""


class UserNotActiveError(AuthenticationError):
    """Учётная запись отключена администратором."""

    def __init__(self, login: str):
        self.login = login
        super().__init__(f"Учётная запись {login!r} отключена")


class InvalidPasswordError(AuthenticationError):
    """Неверный пароль для существующего активного пользователя."""

    def __init__(self, login: str):
        self.login = login
        super().__init__(f"Неверный пароль для {login!r}")


class SupplyNotFoundError(NotFoundError):
    item_label = "Приход"
