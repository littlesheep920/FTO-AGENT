"""数据源基础：统一 PatentDoc 结构 + 抽象 Source + HTTP 助手。"""
import httpx

import settings


class SourceError(Exception):
    """数据源错误基类。"""


class SourceSkipped(SourceError):
    """源不可用（无 key / 未配置），应跳过而非报错。"""


class PatentDoc:
    """统一专利文档结构（各源解析后归一化为此结构）。"""

    def __init__(self, patent_no, title=None, abstract=None, applicant=None, inventor=None,
                 application_date=None, publication_date=None, grant_date=None,
                 ipc_codes=None, cpc_codes=None, legal_status=None,
                 family=None, source="", source_url=None, raw=None):
        self.patent_no = patent_no
        self.title = title
        self.abstract = abstract
        self.applicant = applicant
        self.inventor = inventor
        self.application_date = application_date
        self.publication_date = publication_date
        self.grant_date = grant_date
        self.ipc_codes = ipc_codes or []
        self.cpc_codes = cpc_codes or []
        self.legal_status = legal_status
        self.family = family or []
        self.source = source
        self.source_url = source_url
        self.raw = raw

    def to_dict(self) -> dict:
        return {
            "patent_no": self.patent_no,
            "title": self.title,
            "abstract": self.abstract,
            "applicant": self.applicant,
            "inventor": self.inventor,
            "application_date": self.application_date,
            "publication_date": self.publication_date,
            "grant_date": self.grant_date,
            "ipc_codes": self.ipc_codes,
            "cpc_codes": self.cpc_codes,
            "legal_status": self.legal_status,
            "family": self.family,
            "source": self.source,
            "source_url": self.source_url,
        }


class BaseSource:
    name = "base"
    needs_key = False

    async def search(self, expression: str, jurisdiction: str = "CN", limit: int = 20):
        raise NotImplementedError

    async def _get(self, url, params=None, headers=None, retries: int = 1):
        """带重试的 GET；返回 httpx.Response 或抛异常。"""
        import asyncio
        headers = headers or {}
        headers.setdefault("User-Agent", "FTO-Agent/1.0 (patent research)")
        last_err = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.PATENT_TIMEOUT,
                                             follow_redirects=True) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    if resp.status_code in (401, 403):
                        raise SourceSkipped(f"无访问权限({resp.status_code})")
                    if resp.status_code == 200:
                        return resp
                    last_err = SourceError(f"HTTP {resp.status_code}")
            except SourceSkipped:
                raise
            except Exception as e:  # noqa: BLE001
                last_err = e
            if attempt < retries:
                await asyncio.sleep(settings.SEARCH_INTERVAL)
        raise last_err if last_err else SourceError("请求失败")
