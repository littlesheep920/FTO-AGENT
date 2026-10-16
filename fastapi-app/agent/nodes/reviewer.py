"""⑧ Reviewer：全面覆盖判定 + 风险定级 + 规避建议 + Dossier 组装。"""
import time

from agent.log import write_log
from models import Analysis, RiskAssessment

DISCLAIMER = ("本报告由 AI 自动生成，仅作初筛参考，不构成法律意见。"
              "最终结论需由具备资质的专利律师人工复核，并以官方登记簿为准。")


def _build_dossier(state: dict, summary: dict, verdict: str, exec_summary: str) -> str:
    plan = state.get("retrieval_plan") or {}
    patents = state.get("patents", [])
    chart = state.get("claim_chart", [])
    risks = state.get("risk_assessment", [])
    lines = [
        "# FTO 分析卷宗", "", "## 1. 执行摘要", exec_summary, "",
        "## 2. 检索策略",
        f"- 检索式：{plan.get('search_expressions', [])}",
        f"- IPC/CPC 锚点：{plan.get('ipc_anchors', [])}",
        f"- 数据源：{plan.get('data_sources', [])}",
        "",
        "## 3. 专利清单",
    ]
    if patents:
        if any(p.get("source") == "mock" for p in patents):
            lines.append("> ⚠️ 当前为演示数据（mock），非真实检索结果")
        lines += ["| 专利号 | 标题 | 申请人 | 法律状态 |", "|---|---|---|---|"]
        for p in patents:
            lines.append(f"| {p.get('patent_no', '')} | {p.get('title', '')} | {p.get('applicant', '')} | {p.get('legal_status', '')} |")
    else:
        lines.append("（暂无候选专利）")

    lines += ["", "## 4. Claim Chart（独立权利要求要素比对）", "| 专利号 | 权要 | 技术要素 | 判定 |", "|---|---|---|---|"]
    if chart:
        for c in chart:
            lines.append(f"| {c.get('patent_no', '')} | 权要{c.get('claim_no', '')} | {c.get('element', '')} | {c.get('match_status', '')} |")
    else:
        lines.append("（暂无对照记录）")

    lines += ["", "## 5. 风险分级",
              f"- 高风险 {summary['high']} 件 / 中风险 {summary['medium']} 件 / 低风险 {summary['low']} 件 / 排除 {summary['excluded']} 件",
              "", "## 6. 规避设计建议"]
    da = [r.get("design_around") for r in risks if r.get("design_around")]
    if da:
        seen = set()
        for r in risks:
            pn = r.get("patent_no", "")
            if pn in seen:
                continue
            seen.add(pn)
            lines.append(f"- [{r.get('risk_level', '')}] {pn}：{r.get('design_around', '')}")
    else:
        lines.append("（暂无）")
    lines += ["", "## 7. 证据与溯源",
              "（比对证据见 claim_chart 表；官方链接见各专利 source_url）",
              "", "## 8. 免责声明", DISCLAIMER]
    return "\n".join(lines)


async def reviewer_node(state: dict) -> dict:
    t0 = time.time()
    analysis_id = state["analysis_id"]

    if state.get("error"):
        return {"step": "reviewer"}

    try:
        coverage = state.get("coverage", [])
        legal_statuses = state.get("legal_statuses", [])
        ls_by_patent = {s.get("patent_no"): s for s in legal_statuses}

        # 1. 逐件定级 + 落库
        risks = []
        for cov in coverage:
            ls = ls_by_patent.get(cov.get("patent_no"), {})
            admissible = ls.get("admissible", 1)
            if admissible == 2:
                risk, design = "排除", "法律状态已失效/届满，无需规避"
            elif cov.get("all_matched"):
                risk = "高"
                design = "独立权利要求被产品全面覆盖（字面侵权风险高），建议：①修改/移除核心要素；②寻求许可或无效"
            elif cov.get("matched", 0) > 0:
                risk = "中"
                design = "存在部分覆盖，建议针对未命中/存疑要素进一步确认，必要时规避设计"
            else:
                risk = "低"
                design = "未命中独立权利要求要素，风险较低"
            basis = (f"独立权要{cov.get('claim_no')} 命中{cov.get('matched')}/{cov.get('total')}，"
                     f"法律状态:{ls.get('status') or '未知'}")
            await RiskAssessment.create(
                analysis_id=analysis_id, patent_id=cov.get("patent_id"),
                risk_level=risk, basis=basis, design_around=design,
                conclusion=f"{risk}风险",
            )
            risks.append({"patent_no": cov.get("patent_no"), "risk_level": risk,
                          "design_around": design, "basis": basis})

        # 2. 汇总
        summary = {"high": 0, "medium": 0, "low": 0, "excluded": 0}
        for r in risks:
            lv = r["risk_level"]
            if lv == "高":
                summary["high"] += 1
            elif lv == "中":
                summary["medium"] += 1
            elif lv == "低":
                summary["low"] += 1
            elif lv == "排除":
                summary["excluded"] += 1

        patents = state.get("patents", [])
        is_mock = all((p.get("source") == "mock") for p in patents) if patents else False

        if summary["high"] > 0:
            verdict = f"发现 {summary['high']} 件高风险专利（独立权利要求被全面覆盖），建议规避设计并交由律师复核"
        elif summary["medium"] > 0:
            verdict = f"存在 {summary['medium']} 件中风险专利，建议人工复核 Claim Chart"
        elif patents:
            verdict = (f"演示数据（mock）：{len(patents)} 件示例专利已完成比对，正式分析需接入真实数据源"
                       if is_mock else "未发现全面覆盖的高风险专利，建议继续推进（仍需律师确认）")
        else:
            verdict = "检索无候选专利（数据源不可用或未命中），请检查数据源配置"

        exec_summary = (f"命中高风险 {summary['high']} 件、中风险 {summary['medium']} 件、"
                        f"低风险 {summary['low']} 件、排除 {summary['excluded']} 件。结论：{verdict}。")
        state["risk_assessment"] = risks   # 写回 state，供 _build_dossier 渲染
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
            "risk_assessment": risks,
            "risk_summary": summary,
            "dossier": {"summary": summary, "verdict": verdict,
                        "executive_summary": exec_summary, "markdown": md},
            "step": "reviewer",
        }
    except Exception as e:
        await write_log(analysis_id, "reviewer", "summarize", {}, {"error": str(e)},
                        None, int((time.time() - t0) * 1000), 3)
        return {"error": str(e), "step": "reviewer"}
