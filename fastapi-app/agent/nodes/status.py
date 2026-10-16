"""⑤ Legal Status Verifier：核验法律状态与 FTO 准入。"""
import time

from agent.log import write_log
from models import LegalStatus, Patent

INVALID_STATUS = {"失效", "届满", "撤回", "视为放弃", "驳回", "未缴年费"}


def _admissible(status) -> tuple:
    if not status:
        return 1, "状态未知，默认准入待人工核验"
    if status in INVALID_STATUS:
        return 2, f"状态 {status} → 排除"
    if status == "有效":
        return 1, "有效 → 准入"
    if status == "审中":
        return 1, "审中 → 准入（授权前风险，需持续监控）"
    return 1, f"状态 {status} → 待人工核验"


async def status_node(state: dict) -> dict:
    if state.get("error"):
        return {"step": "status"}

    analysis_id = state["analysis_id"]
    patents = state.get("patents", [])
    t0 = time.time()
    result = []
    try:
        for p in patents:
            ls = p.get("legal_status")
            admissible, reason = _admissible(ls)
            await LegalStatus.create(
                analysis_id=analysis_id, patent_id=p.get("id"),
                jurisdiction=state.get("jurisdiction") or "CN",
                status=ls, status_source=p.get("source"),
                source_url=p.get("source_url"),
                admissibility=admissible, admissibility_reason=reason,
            )
            result.append({
                "patent_no": p.get("patent_no"), "status": ls,
                "admissible": admissible, "reason": reason,
            })
        await write_log(analysis_id, "status", "verify",
                        {"patents": len(patents)},
                        {"admissible": sum(1 for r in result if r["admissible"] == 1)},
                        None, int((time.time() - t0) * 1000), 1)
        return {"legal_statuses": result, "step": "status"}
    except Exception as e:
        await write_log(analysis_id, "status", "verify", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "status"}
