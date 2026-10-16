"""⑦ Claim Chart Draft：产品事实 vs Claim 要素逐项对照（LLM 优先，规则兜底）。"""
import time

from agent import llm, prompts
from agent.claim_utils import ratio_to_status, rule_match
from agent.log import write_log
from models import Claim, ClaimChart, ClaimElement, ProductFact


def _rule_chart(product_desc: str, facts: list, element) -> dict:
    """规则比对：关键词命中比例。"""
    ratio, hits = rule_match(product_desc, element.element_text)
    best_fact = None
    if ratio >= 0.3 and facts:
        # 找与要素最相关的产品事实作证据
        best = max(facts, key=lambda f: rule_match((f.get("value") or f.get("feature") or ""),
                                                   element.element_text)[0])
        best_fact = best
    return {
        "match_status": ratio_to_status(ratio),
        "rationale": f"关键词命中{hits}（比例{ratio}）",
        "evidence_claim": element.element_text,
        "evidence_product": (best_fact.get("value") if best_fact else None),
        "product_fact_id": (best_fact.get("id") if best_fact else None),
        "confidence": round(ratio, 2),
    }


async def _llm_chart(product_desc: str, facts: list, elements) -> dict:
    """LLM 比对：一次请求比对全部要素，返回 {element_no: {match, reason}}。"""
    system = await prompts.get_prompt("chart")
    user = (f"产品描述：{product_desc}\n"
            f"权利要求技术要素（JSON）：{ [{'element_no': e.element_no, 'text': e.element_text} for e in elements] }\n"
            "对每个要素判断产品是否具备：命中/缺失/部分，输出 JSON："
            '{"rows":[{"element_no":1,"match":"命中","reason":"..."}]}')
    data = await llm.ask_json(system, user)
    if not data:
        return None
    rows = data.get("rows") or []
    return {int(r.get("element_no", 0)): r for r in rows if isinstance(r, dict)}


async def chart_node(state: dict) -> dict:
    if state.get("error"):
        return {"step": "chart"}

    analysis_id = state["analysis_id"]
    product_desc = state.get("product_description") or ""
    facts = state.get("product_facts", [])
    patents = state.get("patents", [])
    degraded = state.get("degraded", False)
    t0 = time.time()
    rows, coverage = [], []
    try:
        for p in patents:
            indep_claims = await Claim.filter(
                analysis_id=analysis_id, patent_id=p.get("id"), claim_type=1).order_by("claim_no")
            for claim in indep_claims:
                elements = await ClaimElement.filter(
                    analysis_id=analysis_id, claim_id=claim.id).order_by("element_no")
                if not elements:
                    continue

                # LLM 比对优先
                llm_rows = None
                if await llm.llm_enabled():
                    llm_rows = await _llm_chart(product_desc, facts, elements)

                matched = 0
                for el in elements:
                    if llm_rows and el.element_no in llm_rows:
                        r = llm_rows[el.element_no]
                        status = r.get("match", "存疑")
                        if status not in ("命中", "缺失", "部分"):
                            status = "存疑"
                        rationale = r.get("reason", "")
                        evidence_product = None
                        product_fact_id = None
                        confidence = 0.9 if status == "命中" else (0.5 if status == "部分" else 0.2)
                    else:
                        rc = _rule_chart(product_desc, facts, el)
                        status = rc["match_status"]
                        rationale = rc["rationale"]
                        evidence_product = rc["evidence_product"]
                        product_fact_id = rc["product_fact_id"]
                        confidence = rc["confidence"]

                    if status == "命中":
                        matched += 1
                    await ClaimChart.create(
                        analysis_id=analysis_id, patent_id=p.get("id"), claim_id=claim.id,
                        product_fact_id=product_fact_id, match_status=status,
                        rationale=rationale, evidence_product=evidence_product,
                        evidence_claim=el.element_text, confidence=confidence,
                        is_full_coverage=0,
                    )
                    rows.append({
                        "patent_no": p.get("patent_no"), "claim_no": claim.claim_no,
                        "element": el.element_text[:40], "match_status": status,
                    })

                all_matched = matched == len(elements) and len(elements) > 0
                coverage.append({
                    "patent_id": p.get("id"), "patent_no": p.get("patent_no"),
                    "claim_id": claim.id, "claim_no": claim.claim_no,
                    "all_matched": all_matched, "matched": matched, "total": len(elements),
                })

        await write_log(analysis_id, "chart", "compare",
                        {"facts": len(facts), "patents": len(patents)},
                        {"rows": len(rows), "coverage": coverage}, None,
                        int((time.time() - t0) * 1000), 1)
        return {"claim_chart": rows, "coverage": coverage, "degraded": degraded, "step": "chart"}
    except Exception as e:
        await write_log(analysis_id, "chart", "compare", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "chart"}
