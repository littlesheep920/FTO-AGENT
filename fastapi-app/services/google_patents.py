"""Google Patents 适配器：非官方 XHR 接口。

注意：patents.google.com 无官方 API，接口可能变更/反爬；且在中国大陆不可达。
解析做防御性处理，失败抛 SourceSkipped 或 SourceError 由降级链接管。
"""
import urllib.parse

from services.base import BaseSource, PatentDoc


class GooglePatentsSource(BaseSource):
    name = "google_patents"

    async def search(self, expression, jurisdiction="CN", limit=20):
        query = expression.strip() or "catheter"
        if jurisdiction and f"country:{jurisdiction}" not in query:
            query = f"{query} country:{jurisdiction}"
        url = "https://patents.google.com/xhr/query"
        params = {"url": f"q={urllib.parse.quote(query)}"}
        resp = await self._get(url, params=params)
        data = resp.json()
        docs = []
        clusters = (data.get("results") or {}).get("cluster") or []
        for c in clusters[:limit]:
            r = (c or {}).get("result") or {}
            pn = r.get("patent_number") or ""
            if not pn:
                continue
            classifications = r.get("classifications") or []
            ipc = [x.get("code") for x in classifications if x.get("type") == "ipc"] or \
                  [x.get("code") for x in classifications]
            docs.append(PatentDoc(
                patent_no=pn,
                title=(r.get("title") or {}).get("text") or r.get("title"),
                abstract=(r.get("snippet") or "").strip() or None,
                applicant=(r.get("assignee") or "").strip() or None,
                inventor=(r.get("inventor") or "").strip() or None,
                publication_date=(r.get("publication_date") or "")[:10] or None,
                application_date=(r.get("filing_date") or "")[:10] or None,
                grant_date=(r.get("grant_date") or "")[:10] or None,
                ipc_codes=ipc,
                source=self.name,
                source_url=f"https://patents.google.com/patent/{pn}/zh",
                raw=r,
            ))
        return docs
