"""⑤ Legal Status Verifier：核验法律状态与准入（M3 实现）。"""
import time

from agent.log import write_log


async def status_node(state: dict) -> dict:
    if state.get("error"):
        return {"step": "status"}

    analysis_id = state["analysis_id"]
    await write_log(analysis_id, "status", "verify", {"patents": len(state.get("patents", []))},
                    {"admissible": 0, "note": "M3 实现（官方法律状态证据）"}, None, 0, 1)
    return {"legal_statuses": [], "step": "status"}
