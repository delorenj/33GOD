import asyncpg
from asyncpg import Pool

from .config import settings

_pool: Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=settings.DB_POOL_MIN,
        max_size=settings.DB_POOL_MAX,
    )


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    return _pool
