"""⑥ Claim Parser：拆解授权专利权利要求 → 技术要素 + 原文定位。"""
import json
import time

from agent.claim_utils import categorize, split_claims, split_elements
from agent.log import write_log
from models import Claim, ClaimElement, Patent


async def parser_node(state: dict) -> dict:
    if state.get("error"):
        return {"step": "parser"}

    analysis_id = state["analysis_id"]
    patents = state.get("patents", [])
    t0 = time.time()
    result = []
    try:
        for p in patents:
            rec = await Patent.filter(id=p.get("id")).first()
            if not rec or not rec.raw_snapshot:
                continue
            try:
                raw = json.loads(rec.raw_snapshot)
            except Exception:
                continue
            claims_text = raw.get("claims") if isinstance(raw, dict) else None
            if isinstance(claims_text, list):
                claims_text = "\n".join(claims_text)
            if not claims_text:
                continue

            for c in split_claims(claims_text):
                claim = await Claim.create(
                    analysis_id=analysis_id, patent_id=rec.id,
                    claim_no=c["claim_no"], claim_type=c["claim_type"],
                    claim_text=c["claim_text"],
                    text_location=f"权利要求{c['claim_no']}",
                    status=1,
                )
                # 只为独立权利要求切分技术要素（FTO 比对主对象）
                if c["claim_type"] == 1:
                    for i, el in enumerate(split_elements(c["claim_text"])):
                        await ClaimElement.create(
                            analysis_id=analysis_id, patent_id=rec.id, claim_id=claim.id,
                            element_no=i + 1, element_text=el,
                            element_category=categorize(el),
                            text_location=f"权利要求{c['claim_no']}要素{i + 1}",
                        )
                result.append({
                    "patent_no": p.get("patent_no"),
                    "claim_no": c["claim_no"], "claim_type": c["claim_type"],
                })

        await write_log(analysis_id, "parser", "parse",
                        {"patents": len(patents)},
                        {"claims": len(result)}, None,
                        int((time.time() - t0) * 1000), 1)
        return {"claims": result, "step": "parser"}
    except Exception as e:
        await write_log(analysis_id, "parser", "parse", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "parser"}
