"""LangGraph 编排：Supervisor 路由 + 8 Worker 顺序流水线 + 防死循环 + 追问分支。

- fact 之后按「是否有未知项」决定：继续或 END（待追问）
- 其余节点线性串联
- 复用 MemorySaver（thread_id = analysis-{id}），与参考项目 InMemorySaver 一致
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent import llm
from agent.nodes import (chart, fact, family, parser, planner, reviewer,
                         searcher, status)
from agent.state import AgentState

_checkpointer = MemorySaver()
_graph = None


def _route_after_fact(state: dict) -> str:
    if state.get("error"):
        return "end"
    if state.get("needs_clarification"):
        return "end"
    return "planner"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("fact", fact.fact_node)
    g.add_node("planner", planner.planner_node)
    g.add_node("searcher", searcher.searcher_node)
    g.add_node("family", family.family_node)
    g.add_node("status", status.status_node)
    g.add_node("parser", parser.parser_node)
    g.add_node("chart", chart.chart_node)
    g.add_node("reviewer", reviewer.reviewer_node)

    g.add_edge(START, "fact")
    g.add_conditional_edges("fact", _route_after_fact, {"planner": "planner", "end": END})
    g.add_edge("planner", "searcher")
    g.add_edge("searcher", "family")
    g.add_edge("family", "status")
    g.add_edge("status", "parser")
    g.add_edge("parser", "chart")
    g.add_edge("chart", "reviewer")
    g.add_edge("reviewer", END)
    return g.compile(checkpointer=_checkpointer)


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_analysis(analysis_id: int) -> dict:
    """执行一次分析：从初始状态跑到 END（可能是完成，也可能是待追问）。"""
    from models import Analysis

    a = await Analysis.get(id=analysis_id)
    a.status = 2
    await a.save()

    degraded = not await llm.llm_enabled()
    initial = {
        "analysis_id": analysis_id,
        "product_description": a.product_description or "",
        "jurisdiction": a.jurisdiction or "CN",
        "product_facts": [],
        "needs_clarification": False,
        "clarification_id": None,
        "clarification_questions": [],
        "retrieval_plan": None,
        "patents": [],
        "family_records": [],
        "legal_statuses": [],
        "claims": [],
        "claim_chart": [],
        "risk_assessment": [],
        "risk_summary": None,
        "dossier": None,
        "degraded": degraded,
        "error": None,
        "step": "start",
    }
    graph = get_graph()
    config = {"configurable": {"thread_id": f"analysis-{analysis_id}"}}
    result = await graph.ainvoke(initial, config)
    return result
