"""③ Searcher：执行检索 + 初筛 + 落快照（M2 为桩，M3 接入真实数据源）。"""
import time

from agent.log import write_log


async def searcher_node(state: dict) -> dict:
    t0 = time.time()
    analysis_id = state["analysis_id"]

    if state.get("error"):
        return {"step": "searcher"}

    plan = state.get("retrieval_plan") or {}
    # M2 桩：返回空候选；M3 调 tools.search_patents 真实检索
    await write_log(
        analysis_id, "searcher", "search",
        {"plan": plan},
        {"patents": 0, "note": "M3 接入真实数据源（Google Patents/Espacenet/PATENTSCOPE）"},
        None, int((time.time() - t0) * 1000), 2,   # status=2 降级
    )
    return {"patents": [], "step": "searcher"}
