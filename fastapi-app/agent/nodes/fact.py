"""① Input & Fact Agent：解析产品技术特征事实 + 一轮追问。"""
import re
import time

from agent import llm, prompts
from agent.log import write_log
from models import Clarification, ProductFact


def _fact_to_dict(f) -> dict:
    return {
        "id": f.id, "feature": f.feature, "feature_type": f.feature_type,
        "value": f.value, "is_unknown": f.is_unknown, "status": f.status,
        "evidence": f.evidence,
    }


def _extract_rule(desc: str) -> list:
    """规则引擎：按句切分 + 关键词；缺弯曲控制信息则标记未知项。"""
    parts = [p.strip() for p in re.split(r"[。；;，,\n]", desc) if p.strip()]
    facts = [{"feature": f"特征{i + 1}", "feature_type": "结构", "value": p, "is_unknown": 0}
             for i, p in enumerate(parts)]
    if not facts:
        facts = [{"feature": "产品整体", "feature_type": "结构", "value": desc, "is_unknown": 0}]
    if "弯" not in desc and "控" not in desc:
        facts.append({"feature": "弯曲控制方式", "feature_type": "运动", "value": "", "is_unknown": 1})
    return facts


async def _extract_llm(desc: str):
    system = await prompts.get_prompt("fact")
    data = await llm.ask_json(system, desc)
    if not data:
        return None
    items = data.get("facts") or data.get("features") or []
    if isinstance(data, list):
        items = data
    facts = []
    for it in items:
        if not isinstance(it, dict):
            continue
        facts.append({
            "feature": it.get("feature") or it.get("name") or "特征",
            "feature_type": it.get("feature_type") or it.get("type") or "结构",
            "value": it.get("value") or "",
            "is_unknown": 1 if (it.get("is_unknown") or it.get("unknown")) else 0,
        })
    return facts or None


async def fact_node(state: dict) -> dict:
    t0 = time.time()
    analysis_id = state["analysis_id"]
    desc = state.get("product_description") or ""
    degraded = state.get("degraded", False)

    if state.get("error"):
        return {"step": "fact"}

    try:
        existing = await ProductFact.filter(analysis_id=analysis_id).order_by("id")
        if not existing:
            # 读取上传附件内容（草图/参数表/权要草稿）
            from agent.file_parser import extract_analysis_files
            file_extra = await extract_analysis_files(analysis_id)
            full_desc = desc
            if file_extra.get("text"):
                full_desc = f"{desc}\n{file_extra['text']}"

            raw = None
            if await llm.llm_enabled():
                raw = await _extract_llm(full_desc)
            if raw is None:
                degraded = True
                raw = _extract_rule(full_desc)
            for r in raw:
                await ProductFact.create(
                    analysis_id=analysis_id,
                    feature=r["feature"], feature_type=r["feature_type"],
                    value=r.get("value") or None,
                    is_unknown=r.get("is_unknown", 0),
                    status=3 if r.get("is_unknown") else 1,
                )
            # 有草图但无视觉模型识别 → 标记为未知项，触发追问补充
            if file_extra.get("unrecognized_images", 0) > 0:
                await ProductFact.create(
                    analysis_id=analysis_id,
                    feature="结构草图内容", feature_type="结构",
                    value=None, is_unknown=1, status=3,
                )
            existing = await ProductFact.filter(analysis_id=analysis_id).order_by("id")

        facts = [_fact_to_dict(f) for f in existing]
        unknowns = [f for f in existing if f.is_unknown == 1 and f.status == 3]

        if unknowns:
            answered = await Clarification.filter(
                analysis_id=analysis_id, round=1).exclude(answer__isnull=True).first()
            if not answered:
                questions = [{"fact_id": u.id, "question": u.feature} for u in unknowns]
                c = await Clarification.create(
                    analysis_id=analysis_id, round=1,
                    question="；".join(q["question"] for q in questions),
                    fact_ids=[u.id for u in unknowns],
                )
                await write_log(
                    analysis_id, "fact", "extract",
                    {"desc": desc[:200]},
                    {"facts": len(facts), "unknowns": len(unknowns)},
                    None, int((time.time() - t0) * 1000), 1,
                )
                return {
                    "product_facts": facts,
                    "needs_clarification": True,
                    "clarification_id": c.id,
                    "clarification_questions": questions,
                    "degraded": degraded,
                    "step": "fact",
                }

        await write_log(
            analysis_id, "fact", "extract",
            {"desc": desc[:200]},
            {"facts": len(facts), "unknowns": 0},
            None, int((time.time() - t0) * 1000), 1,
        )
        return {
            "product_facts": facts,
            "needs_clarification": False,
            "clarification_id": None,
            "clarification_questions": [],
            "degraded": degraded,
            "step": "fact",
        }
    except Exception as e:
        await write_log(analysis_id, "fact", "extract", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "fact"}
