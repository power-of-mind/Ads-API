import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from aiohttp import web

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 24


# ── Пароли ────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Хэширует пароль через bcrypt. Возвращает строку для хранения в БД."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, password_hash: str) -> bool:
    """Сравнивает введённый пароль с хэшом из БД."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_token(user_id: int) -> str:
    """Создаёт JWT-токен с user_id и временем истечения."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Декодирует JWT. Выбрасывает исключение если токен невалиден или истёк."""
    return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])


# ── Middleware-хелпер ─────────────────────────────────────────────────────────

def get_current_user_id(request: web.Request) -> int:
    """
    Извлекает user_id из заголовка Authorization: Bearer <token>.
    Вызывается внутри защищённых хендлеров.
    Возвращает 401 если токен отсутствует или невалиден.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise web.HTTPUnauthorized(text="Missing or invalid Authorization header")

    token = auth_header[len("Bearer "):]
    try:
        payload = decode_token(token)
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise web.HTTPUnauthorized(text="Token expired")
    except jwt.InvalidTokenError:
        raise web.HTTPUnauthorized(text="Invalid token")