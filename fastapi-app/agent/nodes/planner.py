"""② Retrieval Planner：生成检索路线、查询词、IPC/CPC 锚点、检索式。"""
import re
import time

from agent import llm, prompts
from agent.log import write_log
from models import RetrievalPlan

IPC_ANCHORS = ["A61M25/092", "A61M25/01", "A61M25/10", "A61M25/09", "A61B18/14", "A61B17/00"]


def _plan_rule(desc: str) -> dict:
    kws = re.findall(r"[\u4e00-\u9fa5]{2,8}", desc)[:6]
    return {
        "query_terms": kws,
        "ipc_anchors": IPC_ANCHORS,
        "search_expressions": [f"{' '.join(kws)} country:CN status:GRANT".strip()],
        "data_sources": ["google_patents", "espacenet", "patentscope"],
    }


async def planner_node(state: dict) -> dict:
    t0 = time.time()
    analysis_id = state["analysis_id"]
    desc = state.get("product_description") or ""
    degraded = state.get("degraded", False)

    if state.get("error"):
        return {"step": "planner"}

    try:
        plan = None
        if await llm.llm_enabled():
            system = await prompts.get_prompt("planner")
            plan = await llm.ask_json(system, desc)
        if not plan:
            degraded = True
            plan = _plan_rule(desc)

        await RetrievalPlan.create(
            analysis_id=analysis_id,
            query_terms=plan.get("query_terms"),
            ipc_anchors=plan.get("ipc_anchors"),
            search_expressions=plan.get("search_expressions"),
            data_sources=plan.get("data_sources"),
            status=2,
        )
        await write_log(analysis_id, "planner", "plan", {"desc": desc[:200]}, plan,
                        None, int((time.time() - t0) * 1000), 1)
        return {"retrieval_plan": plan, "degraded": degraded, "step": "planner"}
    except Exception as e:
        await write_log(analysis_id, "planner", "plan", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "planner"}
