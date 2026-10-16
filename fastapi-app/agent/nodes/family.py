"""④ Family Resolver：整理候选同族关系（只整理不确认）。"""
import time

from agent.log import write_log
from models import Patent, PatentFamily


async def family_node(state: dict) -> dict:
    if state.get("error"):
        return {"step": "family"}

    analysis_id = state["analysis_id"]
    patents = state.get("patents", [])
    t0 = time.time()
    records = []
    try:
        for p in patents:
            for f in (p.get("family") or []):
                if not isinstance(f, dict) or not f.get("patent_no"):
                    continue
                rec = await PatentFamily.create(
                    analysis_id=analysis_id,
                    patent_id=p.get("id"),
                    related_patent_no=f.get("patent_no"),
                    relation_type=f.get("relation") or "疑似",
                    evidence=p.get("source_url"),
                    status=1,   # 待核验（不自行确认）
                )
                records.append({
                    "patent_no": p.get("patent_no"),
                    "related": f.get("patent_no"),
                    "relation": f.get("relation"),
                    "status": 1,
                })
        await write_log(analysis_id, "family", "resolve",
                        {"patents": len(patents)},
                        {"families": len(records)}, None,
                        int((time.time() - t0) * 1000), 1)
        return {"family_records": records, "step": "family"}
    except Exception as e:
        await write_log(analysis_id, "family", "resolve", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "family"}
