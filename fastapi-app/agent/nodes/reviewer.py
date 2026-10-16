"""⑧ Reviewer：全面覆盖判定 + 风险定级 + 规避建议 + Dossier 组装。"""
import time

from agent.log import write_log
from models import Analysis

DISCLAIMER = ("本报告由 AI 自动生成，仅作初筛参考，不构成法律意见。"
              "最终结论需由具备资质的专利律师人工复核，并以官方登记簿为准。")


def _build_dossier(state: dict, summary: dict, verdict: str, exec_summary: str) -> str:
    plan = state.get("retrieval_plan") or {}
    patents = state.get("patents", [])
    chart = state.get("claim_chart", [])
    risks = state.get("risk_assessment", [])
    lines = [
        "# FTO 分析卷宗",
        "",
        "## 1. 执行摘要",
        exec_summary,
        "",
        "## 2. 检索策略",
        f"- 检索式：{plan.get('search_expressions', [])}",
        f"- IPC/CPC 锚点：{plan.get('ipc_anchors', [])}",
        f"- 数据源：{plan.get('data_sources', [])}",
        "",
        "## 3. 专利清单",
    ]
    if patents:
        lines += ["| 专利号 | 标题 | 申请人 | 法律状态 |", "|---|---|---|---|"]
        for p in patents:
            lines.append(f"| {p.get('patent_no', '')} | {p.get('title', '')} | {p.get('applicant', '')} | {p.get('legal_status', '')} |")
    else:
        lines.append("（暂未检索到候选专利 —— M3 接入真实数据源）")

    lines += ["", "## 4. Claim Chart", "| 产品特征 | 权要要素 | 判定 |", "|---|---|---|"]
    if chart:
        for c in chart:
            lines.append(f"| {c.get('product_feature', '')} | {c.get('claim_element', '')} | {c.get('match_status', '')} |")
    else:
        lines.append("（暂无对照记录）")

    lines += [
        "",
        "## 5. 风险分级",
        f"- 高风险 {summary['high']} 件 / 中风险 {summary['medium']} 件 / 低风险 {summary['low']} 件",
        "",
        "## 6. 规避设计建议",
    ]
    da = [r.get("design_around") for r in risks if r.get("design_around")]
    lines += [f"- {x}" for x in da] if da else ["（暂无）"]
    lines += [
        "",
        "## 7. 证据与溯源",
        "（M3/M4 起随检索与比对结果生成官方链接）",
        "",
        "## 8. 免责声明",
        DISCLAIMER,
    ]
    return "\n".join(lines)


async def reviewer_node(state: dict) -> dict:
    t0 = time.time()
    analysis_id = state["analysis_id"]

    if state.get("error"):
        return {"step": "reviewer"}

    try:
        patents = state.get("patents", [])
        risks = state.get("risk_assessment", [])
        summary = {"high": 0, "medium": 0, "low": 0, "excluded": 0}
        for r in risks:
            lv = r.get("risk_level")
            if lv == "高":
                summary["high"] += 1
            elif lv == "中":
                summary["medium"] += 1
            elif lv == "低":
                summary["low"] += 1

        if summary["high"] > 0:
            verdict = "发现高风险专利，建议规避设计并交由律师复核"
        elif summary["medium"] > 0:
            verdict = "存在中风险专利，建议人工复核 Claim Chart"
        elif patents:
            verdict = "未发现全面覆盖的高风险专利，建议继续推进（仍需律师确认）"
        else:
            verdict = "M2 阶段：检索尚未接入真实数据源，无候选专利（待 M3）"

        exec_summary = (f"命中高风险 {summary['high']} 件、中风险 {summary['medium']} 件、"
                        f"低风险 {summary['low']} 件。结论：{verdict}。")
        md = _build_dossier(state, summary, verdict, exec_summary)

        a = await Analysis.get(id=analysis_id)
        a.risk_summary = summary
        a.executive_summary = exec_summary
        a.dossier_markdown = md
        a.disclaimer = DISCLAIMER
        a.status = 4
        await a.save()

        await write_log(analysis_id, "reviewer", "summarize", {},
                        {"summary": summary, "verdict": verdict}, None,
                        int((time.time() - t0) * 1000), 1)
        return {
            "risk_summary": summary,
            "dossier": {"summary": summary, "verdict": verdict,
                        "executive_summary": exec_summary, "markdown": md},
            "step": "reviewer",
        }
    except Exception as e:
        await write_log(analysis_id, "reviewer", "summarize", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "reviewer"}
