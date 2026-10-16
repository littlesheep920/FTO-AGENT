"""⑦ Claim Chart Draft：产品事实 vs Claim 要素逐项对照（M4 实现）。"""
import time

from agent.log import write_log


async def chart_node(state: dict) -> dict:
    if state.get("error"):
        return {"step": "chart"}

    analysis_id = state["analysis_id"]
    await write_log(analysis_id, "chart", "compare",
                    {"facts": len(state.get("product_facts", [])), "claims": len(state.get("claims", []))},
                    {"rows": 0, "note": "M4 实现（特征级比对）"}, None, 0, 1)
    return {"claim_chart": [], "step": "chart"}
