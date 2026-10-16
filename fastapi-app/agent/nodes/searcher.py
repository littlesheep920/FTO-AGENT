"""③ Searcher：实时检索（降级链）+ 去重 + 相关性初筛 + 落命中快照。"""
import json
import time

from agent.log import write_log
from models import (Claim, ClaimChart, ClaimElement, LegalStatus, Patent,
                    PatentFamily, RiskAssessment)
from services import search_patents


def _ngrams(s, n=2):
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def _relevance(query_terms, title, abstract) -> float:
    """相关度：精确命中 + 2-gram 部分重叠。"""
    text = f"{title or ''} {abstract or ''}"
    terms = [t for t in (query_terms or []) if t]
    if not terms:
        return 50.0
    text_ng = _ngrams(text)
    total = 0.0
    for t in terms:
        if t in text:
            total += 1.0
        elif _ngrams(t) & text_ng:
            total += 0.5
    return round(total / len(terms) * 100, 2)


async def _cleanup(analysis_id: int):
    """清理该分析上次检索的专利及关联数据（幂等重跑）。"""
    for model in (RiskAssessment, ClaimChart, ClaimElement, Claim,
                  LegalStatus, PatentFamily, Patent):
        await model.filter(analysis_id=analysis_id).delete()


async def searcher_node(state: dict) -> dict:
    t0 = time.time()
    analysis_id = state["analysis_id"]

    if state.get("error"):
        return {"step": "searcher"}

    plan = state.get("retrieval_plan") or {}
    expressions = plan.get("search_expressions") or []
    query_terms = plan.get("query_terms") or []
    jurisdiction = state.get("jurisdiction") or "CN"

    try:
        await _cleanup(analysis_id)

        docs, source, is_mock, note = await search_patents(
            expressions, jurisdiction, limit=20)

        # 去重
        seen, unique = set(), []
        for d in docs:
            if d.patent_no and d.patent_no not in seen:
                seen.add(d.patent_no)
                unique.append(d)

        # 相关性初筛 + 落库
        patents = []
        for d in unique:
            score = _relevance(query_terms, d.title, d.abstract)
            rec = await Patent.create(
                analysis_id=analysis_id, patent_no=d.patent_no, title=d.title,
                abstract=d.abstract, applicant=d.applicant, inventor=d.inventor,
                application_date=d.application_date, publication_date=d.publication_date,
                grant_date=d.grant_date, ipc_codes=d.ipc_codes, cpc_codes=d.cpc_codes,
                source=d.source, source_url=d.source_url,
                raw_snapshot=json.dumps(d.raw, ensure_ascii=False) if d.raw else None,
                relevance_score=score,
                screen_status=1 if score > 0 else 2,
                screen_reason=f"来源:{source} 相关度{score}",
            )
            dd = d.to_dict()
            dd["id"] = rec.id
            dd["relevance_score"] = score
            patents.append(dd)

        status = 2 if (is_mock or not source) else 1
        await write_log(
            analysis_id, "searcher", "search",
            {"expressions": expressions, "jurisdiction": jurisdiction},
            {"patents": len(patents), "source": source, "is_mock": is_mock, "note": note},
            None, int((time.time() - t0) * 1000), status,
        )
        return {"patents": patents, "step": "searcher"}
    except Exception as e:
        await write_log(analysis_id, "searcher", "search", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "searcher"}
