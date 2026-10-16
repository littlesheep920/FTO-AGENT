"""检索缓存：search_cache 表（TTL 默认 24h）。"""
from datetime import datetime, timedelta

import settings
from models import SearchCache


async def get(key: str):
    row = await SearchCache.filter(cache_key=key).first()
    if row and row.expire_at and row.expire_at > datetime.now():
        return row.result_json
    return None


async def set(key: str, query: str, result, ttl_hours: int = None):
    ttl = ttl_hours or settings.SEARCH_TTL_HOURS
    expire = datetime.now() + timedelta(hours=ttl)
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
