"""检索缓存：search_cache 表（TTL 默认 24h）。

注意：Tortoise 存储/读取的 DatetimeField 是带时区（UTC）的，
比较时必须用 aware 的当前时间，否则报 offset-naive/offset-aware 错误。
"""
from datetime import datetime, timedelta, timezone

import settings
from models import SearchCache


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    """把无时区的 datetime 当作 UTC 补上时区，保证可比较。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def get(key: str):
    row = await SearchCache.filter(cache_key=key).first()
    if row and row.expire_at and _ensure_aware(row.expire_at) > _now():
        return row.result_json
    return None


async def set(key: str, query: str, result, ttl_hours: int = None):
    ttl = ttl_hours or settings.SEARCH_TTL_HOURS
    expire = _now() + timedelta(hours=ttl)
    row = await SearchCache.filter(cache_key=key).first()
    if row:
        row.query = query
        row.result_json = result
        row.ttl_hours = ttl
        row.expire_at = expire
        await row.save()
    else:
        await SearchCache.create(
            cache_key=key, query=query, result_json=result,
            ttl_hours=ttl, expire_at=expire,
        )
