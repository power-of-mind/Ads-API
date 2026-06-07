import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS advertisement (
    id          SERIAL       PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT         NOT NULL,
    created_at  TIMESTAMP    DEFAULT NOW(),
    owner       VARCHAR(100) NOT NULL
);
"""


async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        os.getenv("DATABASE_URL", "postgresql://ads_user:password@localhost:5432/ads_db")
    )


async def init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
