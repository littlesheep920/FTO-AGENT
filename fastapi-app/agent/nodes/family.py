"""④ Family Resolver：整理候选同族关系（只整理不确认，M3 实现）。"""
import time

from agent.log import write_log


async def family_node(state: dict) -> dict:
    if state.get("error"):
        return {"step": "family"}

    analysis_id = state["analysis_id"]
    await write_log(analysis_id, "family", "resolve", {"patents": len(state.get("patents", []))},
                    {"families": 0, "note": "M3 实现（基于检索快照）"}, None, 0, 1)
    return {"family_records": [], "step": "family"}
