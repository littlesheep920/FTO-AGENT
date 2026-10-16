"""PATENTSCOPE (WIPO) 适配器：检索需登录/会话，接口较复杂。

M3 先占位：明确标注需要后续接入，当前跳过（不静默编造）。
"""
from services.base import BaseSource, SourceSkipped


class PatentscopeSource(BaseSource):
    name = "patentscope"
    needs_key = True

    async def search(self, expression, jurisdiction="CN", limit=20):
        # PATENTSCOPE 检索接口需先建立会话 + 鉴权，M3 暂以结构占位
        raise SourceSkipped("PATENTSCOPE 需登录会话，留待后续接入")
