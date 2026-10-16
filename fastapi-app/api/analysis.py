"""FTO 分析：创建 / 列表 / 详情 / 删除 / 执行 / 追问 / 状态 / 卷宗 / 导出。"""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent import graph as agent_graph
from common.deps import get_current_user
from common.exception import BizException
from common.response import fail, ok
from models import AgentRunLog, Analysis, Clarification, ProductFact, User

router = APIRouter()
prefix = "/api/fto"


class CreateBody(BaseModel):
    title: str = "未命名分析"
    product_description: str = ""
    jurisdiction: str = "CN"


class ClarifyBody(BaseModel):
    answers: list  # [{fact_id, answer}]


def _analysis_to_dict(a: Analysis) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "status": a.status,
        "product_description": a.product_description,
        "jurisdiction": a.jurisdiction,
        "risk_summary": a.risk_summary,
        "create_time": a.create_time.strftime("%Y-%m-%d %H:%M:%S") if a.create_time else None,
        "update_time": a.update_time.strftime("%Y-%m-%d %H:%M:%S") if a.update_time else None,
    }


def _resolve(aid: int, user: User) -> Analysis:
    return Analysis.filter(id=aid, user=user).first()


@router.post("/analysis")
async def create_analysis(body: CreateBody, user: User = Depends(get_current_user)):
    a = await Analysis.create(
        user=user, title=body.title,
        product_description=body.product_description,
        jurisdiction=body.jurisdiction or "CN", status=1,
    )
    return ok(_analysis_to_dict(a))


@router.get("/analysis/list")
async def list_analysis(user: User = Depends(get_current_user)):
    rows = await Analysis.filter(user=user).order_by("-id").all()
    return ok([_analysis_to_dict(a) for a in rows])


@router.get("/analysis/{aid}")
async def get_analysis(aid: int, user: User = Depends(get_current_user)):
    a = await _resolve(aid, user)
    if not a:
        raise BizException("分析不存在", 404)
    return ok(_analysis_to_dict(a))


@router.delete("/analysis/{aid}")
async def delete_analysis(aid: int, user: User = Depends(get_current_user)):
    a = await _resolve(aid, user)
    if not a:
        raise BizException("分析不存在", 404)
    await a.delete()
    return ok()


# ---------- 执行（M2：真实编排） ----------

@router.post("/analysis/{aid}/run")
async def run_analysis(aid: int, user: User = Depends(get_current_user)):
    a = await _resolve(aid, user)
    if not a:
        raise BizException("分析不存在", 404)
    try:
        result = await agent_graph.run_analysis(aid)
    except Exception as e:
        a.status = 5
        await a.save()
        return fail(f"分析执行失败：{e}", 500)

    if result.get("needs_clarification"):
        a.status = 3
        await a.save()
        return ok({
            "status": 3,
            "need_clarification": True,
            "questions": result.get("clarification_questions", []),
        })
    if result.get("error"):
        a.status = 5
        await a.save()
        return fail(f"分析执行失败：{result['error']}", 500)

    return ok({"status": 4, "dossier": result.get("dossier")})


@router.post("/analysis/{aid}/clarify")
async def clarify(aid: int, body: ClarifyBody, user: User = Depends(get_current_user)):
    a = await _resolve(aid, user)
    if not a:
        raise BizException("分析不存在", 404)

    # 回填答案到产品事实
    for item in body.answers:
        if not isinstance(item, dict):
            continue
        fid, ans = item.get("fact_id"), item.get("answer")
        if fid is None or ans is None:
            continue
        f = await ProductFact.filter(id=fid, analysis_id=aid).first()
        if f:
            f.value = str(ans)
            f.status = 1
            await f.save()

    # 标记追问已回复
    c = await Clarification.filter(analysis_id=aid, round=1, answer__isnull=True).first()
    if c:
        c.answer = json.dumps(body.answers, ensure_ascii=False)
        await c.save()

    # 重新执行完整流水线
    try:
        result = await agent_graph.run_analysis(aid)
    except Exception as e:
        a.status = 5
        await a.save()
        return fail(f"分析执行失败：{e}", 500)

    if result.get("error"):
        a.status = 5
        await a.save()
        return fail(f"分析执行失败：{result['error']}", 500)

    return ok({"status": 4, "dossier": result.get("dossier")})


@router.get("/analysis/{aid}/status")
async def analysis_status(aid: int, user: User = Depends(get_current_user)):
    a = await _resolve(aid, user)
    if not a:
        raise BizException("分析不存在", 404)
    last = await AgentRunLog.filter(analysis_id=aid).order_by("-id").first()
    return ok({
        "status": a.status,
        "current_step": last.node if last else None,
        "risk_summary": a.risk_summary,
    })


@router.get("/analysis/{aid}/dossier")
async def analysis_dossier(aid: int, user: User = Depends(get_current_user)):
    a = await _resolve(aid, user)
    if not a:
        raise BizException("分析不存在", 404)
    return ok({
        "risk_summary": a.risk_summary,
        "executive_summary": a.executive_summary,
        "dossier_markdown": a.dossier_markdown,
        "disclaimer": a.disclaimer,
    })


# ---------- 导出 ----------

@router.get("/analysis/{aid}/export/markdown")
async def export_markdown(aid: int, user: User = Depends(get_current_user)):
    a = await _resolve(aid, user)
    if not a:
        raise BizException("分析不存在", 404)
    if not a.dossier_markdown:
        raise BizException("卷宗尚未生成", 400)
    return ok({"markdown": a.dossier_markdown})


@router.get("/analysis/{aid}/export/pdf")
async def export_pdf(aid: int, user: User = Depends(get_current_user)):
    return fail("PDF 导出将在 M5 实现", 501)
