import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# SQL для создания таблицы пользователей
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL       PRIMARY KEY,
    email         VARCHAR(200) UNIQUE NOT NULL,
    password_hash TEXT         NOT NULL
);
"""

# SQL для создания таблицы объявлений.
# owner_id — внешний ключ, ссылается на users.id
CREATE_ADS_TABLE = """
CREATE TABLE IF NOT EXISTS advertisement (
    id          SERIAL       PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT         NOT NULL,
    created_at  TIMESTAMP    DEFAULT NOW(),
    owner_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE
);
"""


async def get_pool() -> asyncpg.Pool:
    """Создаёт и возвращает пул соединений с PostgreSQL."""
    return await asyncpg.create_pool(
        os.getenv("DATABASE_URL", "postgresql://ads_user:password@localhost:5432/ads_db")
    )


async def init_db(pool: asyncpg.Pool) -> None:
    """Инициализирует БД: создаёт таблицы если их нет."""
    async with pool.acquire() as conn:
        await conn.execute(CREATE_USERS_TABLE)
        await conn.execute(CREATE_ADS_TABLE)