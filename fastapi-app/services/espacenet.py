"""Espacenet OPS 适配器：官方 REST API（需 OPS_API_KEY）。

检索用 published-data/search（CQL），返回 XML；用 ElementTree 解析。
无 key 时抛 SourceSkipped 由降级链跳过。
"""
import xml.etree.ElementTree as ET

import settings
from services.base import BaseSource, PatentDoc, SourceSkipped


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(el, tag):
    if el is None:
        return None
    for child in el.iter():
        if _local(child.tag) == tag:
            return (child.text or "").strip() or None
    return None


class EspacenetSource(BaseSource):
    name = "espacenet"
    needs_key = True
    BASE = "https://ops.epo.org/3.2/rest-services"

    def _headers(self):
        if not settings.OPS_API_KEY:
            raise SourceSkipped("未配置 OPS_API_KEY")
        return {"Authorization": f"Bearer {settings.OPS_API_KEY}",
                "Accept": "application/xml"}

    def _build_cql(self, expression, jurisdiction):
        # 简化：从表达式提取关键词 + 分类号拼 CQL（完整 CQL 映射留待细化）
        import re
        ipc = re.findall(r"[A-H]\d{2}[A-Z]\d{1,2}/\d{2,4}", expression)
        pn = f' pn="{jurisdiction}"' if jurisdiction else ""
        if ipc:
            ipc_q = " OR ".join(f'ipc="{i}"' for i in ipc)
            return f"({ipc_q}) AND{pn}"
        return f'text anywhere "{expression[:40]}" AND{pn}'

    async def search(self, expression, jurisdiction="CN", limit=20):
        cql = self._build_cql(expression, jurisdiction)
        url = f"{self.BASE}/published-data/search"
        resp = await self._get(url, params={"q": cql, "Range": f"1-{limit}"},
                               headers=self._headers())
        root = ET.fromstring(resp.text)
        docs = []
        for doc in root.iter():
            if _local(doc.tag) != "exchange-document":
                continue
            bib = next((c for c in doc if _local(c.tag) == "bibliographic-data"), None)
            if bib is None:
                continue
            pubref = _find_text(bib, "publication-reference")
            country = _find_text(bib, "country")
            number = _find_text(bib, "doc-number")
            kind = _find_text(bib, "kind")
            pn = f"{country or ''}{number or ''}{kind or ''}"
            ipc = [((_find_text(bib, "text"))) for _ in [0]] if False else []
            # 分类
            ipc_codes = []
            for c in bib.iter():
                if _local(c.tag) == "classification-ipcr":
                    t = (c.text or "").strip()
                    if t:
                        ipc_codes.append(t)
            docs.append(PatentDoc(
                patent_no=pn,
                title=_find_text(bib, "invention-title"),
                abstract=_find_text(bib, "abstract"),
                applicant=_find_text(bib, "applicant"),
                inventor=_find_text(bib, "inventor"),
                ipc_codes=ipc_codes,
                source=self.name,
                source_url=f"https://worldwide.espacenet.com/patent/search?q={pn}",
            ))
        return docs
