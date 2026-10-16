"""Espacenet OPS 适配器：官方 REST API（需 OPS_API_KEY）。

检索用 published-data/search（CQL），返回 XML；用 ElementTree 解析。
无 key 时抛 SourceSkipped 由降级链跳过。
"""
import xml.etree.ElementTree as ET

import settings
from services.base import BaseSource, PatentDoc, SourceSkipped


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_first(el, tag):
    """在 el 的后代中找第一个 local name == tag 的元素。"""
    if el is None:
        return None
    for child in el.iter():
        if _local(child.tag) == tag:
            return child
    return None


def _text(el):
    """取元素全部文本（含嵌套子元素）。"""
    if el is None:
        return None
    return "".join(el.itertext()).strip() or None


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
        # 简化：从表达式提取分类号拼 CQL（完整 CQL 映射留待细化）
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
            bib = _find_first(doc, "bibliographic-data")
            if bib is None:
                continue

            # 公开号：publication-reference/document-id 下的 country+doc-number+kind
            pubref = _find_first(bib, "publication-reference")
            country = _text(_find_first(pubref, "country"))
            number = _text(_find_first(pubref, "doc-number"))
            kind = _text(_find_first(pubref, "kind"))
            pn = f"{country or ''}{number or ''}{kind or ''}"

            # IPC 分类（classification-ipcr 元素，文本如 "A61M 25/092"）
            ipc_codes = []
            for c in bib.iter():
                if _local(c.tag) == "classification-ipcr":
                    t = _text(c)
                    if t:
                        ipc_codes.append(t.replace(" ", ""))

            docs.append(PatentDoc(
                patent_no=pn,
                title=_text(_find_first(bib, "invention-title")),
                abstract=_text(_find_first(bib, "abstract")),
                applicant=_text(_find_first(bib, "applicant")),
                inventor=_text(_find_first(bib, "inventor")),
                ipc_codes=ipc_codes,
                source=self.name,
                source_url=f"https://worldwide.espacenet.com/patent/search?q={pn}",
            ))
        return docs
