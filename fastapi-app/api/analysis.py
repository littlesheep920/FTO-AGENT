"""FTO 分析：创建 / 列表 / 详情 / 删除；执行类接口为 M2-M5 占位。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from common.deps import get_current_user
from common.exception import BizException
from common.response import fail, ok
from models import Analysis, User

router = APIRouter()
prefix = "/api/fto"


class CreateBody(BaseModel):
    title: str = "未命名分析"
    product_description: str = ""
    jurisdiction: str = "CN"


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
    a = await Analysis.filter(id=aid, user=user).first()
    if not a:
        raise BizException("分析不存在", 404)
    return ok(_analysis_to_dict(a))


@router.delete("/analysis/{aid}")
async def delete_analysis(aid: int, user: User = Depends(get_current_user)):
    a = await Analysis.filter(id=aid, user=user).first()
    if not a:
        raise BizException("分析不存在", 404)
    await a.delete()
    return ok()


# ---------- M2+ 占位（后续里程碑实现） ----------

@router.post("/analysis/{aid}/run")
async def run_analysis(aid: int, user: User = Depends(get_current_user)):
    return fail("分析执行将在 M2-M4 实现（Agent 编排 + 检索 + 比对）", 501)


@router.get("/analysis/{aid}/status")
async def analysis_status(aid: int, user: User = Depends(get_current_user)):
    return fail("进度查询将在 M2 实现", 501)


@router.get("/analysis/{aid}/dossier")
async def analysis_dossier(aid: int, user: User = Depends(get_current_user)):
    return fail("Dossier 将在 M5 实现", 501)


@router.get("/analysis/{aid}/export/markdown")
async def export_markdown(aid: int, user: User = Depends(get_current_user)):
    return fail("Markdown 导出将在 M5 实现", 501)


@router.get("/analysis/{aid}/export/pdf")
async def export_pdf(aid: int, user: User = Depends(get_current_user)):
    return fail("PDF 导出将在 M5 实现", 501)
