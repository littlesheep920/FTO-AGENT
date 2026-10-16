"""LangChain Tools：8 个 Agent 挂载的能力接口。

M2 阶段为桩实现（返回空/占位），M3 接入专利数据源、M4 接入权要解析与比对。
"""
from langchain_core.tools import tool


@tool
def search_patents(query: str, ipc: str = "", date_range: str = "", limit: int = 20) -> list:
    """在中国法域检索专利。query=检索式，ipc=IPC/CPC分类号，date_range=申请日区间。

    M3 实现：真实调用 Google Patents / Espacenet OPS / PATENTSCOPE。
    """
    return []


@tool
def get_patent_detail(patent_no: str) -> dict:
    """拉取单篇专利著录/摘要/权利要求。M3 实现。"""
    return {}


@tool
def get_legal_status(patent_no: str) -> dict:
    """查询专利法律状态（官方证据）。M3 实现。"""
    return {}


@tool
def get_family_members(patent_no: str) -> list:
    """查询同族/分案关系。M3 实现。"""
    return []


@tool
def get_claims(patent_no: str) -> list:
    """获取专利权利要求全文。M3 实现。"""
    return []


@tool
def split_claims(claim_text: str) -> list:
    """将权利要求切分为技术要素。M4 实现。"""
    return []


@tool
def compare_features(product_feature: str, claim_element: str) -> str:
    """比对产品特征与权利要求要素，返回 命中/缺失/部分/存疑。M4 实现。"""
    return "存疑"
