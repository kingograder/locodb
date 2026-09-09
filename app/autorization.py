import hashlib
import logging
import os
import hmac
from app.db.models import User

logger = logging.getLogger(__name__)

def hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310000)
    return pw_hash.hex(), salt.hex()

def check_password(user: User, password: str) -> bool:
    logger.info(f"Выполняется проверка пароля для пользователя {user.login}")
    try:
        salt = bytes.fromhex(user.password_salt)
        calculated_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310000)
        stored_hash = bytes.fromhex(user.password_hash)
        return hmac.compare_digest(calculated_hash, stored_hash)
    except (ValueError, TypeError):
        return False
