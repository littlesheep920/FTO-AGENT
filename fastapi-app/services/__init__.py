"""专利数据源门面：降级链检索 + 缓存。

降级链顺序由 settings.PATENT_SOURCES 决定：
  google_patents -> espacenet -> patentscope -> (可选 mock)
每个源失败/无 key 时记录原因并尝试下一个；全部失败返回空 + 明确原因。
"""
import settings
from services import cache
from services.base import PatentDoc, SourceSkipped
from services.espacenet import EspacenetSource
from services.google_patents import GooglePatentsSource
from services.mock import MockSource
from services.patentscope import PatentscopeSource

SOURCE_CLASSES = {
    "google_patents": GooglePatentsSource,
    "espacenet": EspacenetSource,
    "patentscope": PatentscopeSource,
    "mock": MockSource,
}


def _sources():
    names = [s.strip() for s in settings.PATENT_SOURCES.split(",") if s.strip()]
    return [SOURCE_CLASSES[n]() for n in names if n in SOURCE_CLASSES]


async def search_patents(expressions, jurisdiction="CN", limit=20):
    """依次尝试数据源，返回 (docs, source_name, is_mock, note)。"""
    expr = (expressions or [""])[0]
    notes = []
    for src in _sources():
        cache_key = f"{src.name}:{jurisdiction}:{expr}"
        cached = await cache.get(cache_key)
        if cached:
            docs = [PatentDoc(**d) for d in cached]
            return docs, src.name, src.name == "mock", "cache"
        try:
            docs = await src.search(expr, jurisdiction, limit)
        except SourceSkipped as e:
            notes.append(f"{src.name}: {e}")
            continue
        except Exception as e:  # noqa: BLE001
            notes.append(f"{src.name}: {type(e).__name__}: {e}")
            continue
        if docs:
            await cache.set(cache_key, expr, [d.to_dict() for d in docs])
            return docs, src.name, src.name == "mock", ""
        notes.append(f"{src.name}: 无结果")

    return [], None, False, " | ".join(notes) if notes else "无可用数据源"
