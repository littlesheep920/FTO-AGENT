"""AgentState：LangGraph 图状态定义。"""
from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    # 输入
    analysis_id: int
    product_description: str
    jurisdiction: str

    # ① Input & Fact
    product_facts: list                       # list[dict]
    needs_clarification: bool
    clarification_id: Optional[int]
    clarification_questions: list

    # ② Retrieval Planner
    retrieval_plan: Optional[dict]

    # ③ Searcher
    patents: list                             # list[dict]

    # ④ Family Resolver / ⑤ Legal Status Verifier
    family_records: list
    legal_statuses: list

    # ⑥ Claim Parser / ⑦ Claim Chart Draft
    claims: list
    claim_chart: list

    # ⑧ Reviewer
    risk_assessment: list
    risk_summary: Optional[dict]
    dossier: Optional[dict]

    # 元信息
    degraded: bool                            # 是否处于规则引擎降级模式
    error: Optional[str]
    step: str
