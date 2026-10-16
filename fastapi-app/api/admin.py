"""管理端：Agent 日志、Prompt 管理、模型配置、运营大屏。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

import settings
from common.deps import get_current_admin
from common.exception import BizException
from common.response import fail, ok
from models import AgentRunLog, LlmConfig, PromptTemplate, Admin, Analysis, Patent, User

router = APIRouter()
prefix = "/api/fto"


# ---------- Agent 日志 ----------

@router.get("/agent/logs")
async def agent_logs(page: int = 1, size: int = 20, _: Admin = Depends(get_current_admin)):
    total = await AgentRunLog.all().count()
    rows = await AgentRunLog.all().order_by("-id").offset((page - 1) * size).limit(size)
    return ok({
        "total": total,
        "records": [{
            "id": r.id, "analysis_id": r.analysis_id, "node": r.node,
            "intent": r.intent, "status": r.status, "duration_ms": r.duration_ms,
            "create_time": r.create_time.strftime("%Y-%m-%d %H:%M:%S") if r.create_time else None,
        } for r in rows],
    })


@router.get("/agent/stats")
async def agent_stats(_: Admin = Depends(get_current_admin)):
    return fail("节点统计将在 M2 实现", 501)


# ---------- Prompt 管理 ----------

class PromptBody(BaseModel):
    scene: str
    content: str
    enabled: int = 1


@router.get("/prompt")
async def list_prompt(_: Admin = Depends(get_current_admin)):
    rows = await PromptTemplate.all().order_by("id")
    return ok([{
        "id": p.id, "scene": p.scene, "content": p.content,
        "enabled": p.enabled, "version": p.version,
    } for p in rows])


@router.put("/prompt")
async def save_prompt(body: PromptBody, _: Admin = Depends(get_current_admin)):
    p = await PromptTemplate.filter(scene=body.scene).first()
    if not p:
        p = await PromptTemplate.create(scene=body.scene, content=body.content, enabled=body.enabled, version=1)
    else:
        p.content = body.content
        p.enabled = body.enabled
        p.version += 1
        await p.save()
    return ok()


# ---------- 模型配置 ----------

class LlmBody(BaseModel):
    provider: str = ""
    base_url: str = ""
    api_key: str = ""
    chat_model: str = ""
    vision_model: str = ""
    embed_model: str = ""
    enabled: int = 1


@router.get("/llm/config")
async def get_llm(_: Admin = Depends(get_current_admin)):
    c = await LlmConfig.first()
    if not c:
        raise BizException("模型配置不存在", 404)
    db_key = c.api_key or ""
    env_key = settings.LLM_API_KEY or ""
    effective = db_key or env_key
    return ok({
        "provider": c.provider, "base_url": c.base_url,
        # 安全：不返回完整 Key，只返回掩码 + 是否已配置
        "api_key": ("****" + effective[-4:]) if effective else "",
        "api_key_configured": bool(effective),
        "api_key_source": "database" if db_key else ("env" if env_key else "none"),
        "chat_model": c.chat_model, "vision_model": c.vision_model,
        "embed_model": c.embed_model, "enabled": c.enabled,
    })


@router.put("/llm/config")
async def save_llm(body: LlmBody, _: Admin = Depends(get_current_admin)):
    c = await LlmConfig.first()
    if not c:
        await LlmConfig.create(**body.model_dump())
    else:
        for k, v in body.model_dump().items():
            setattr(c, k, v)
        await c.save()
    return ok()


@router.post("/llm/test")
async def test_llm(_: Admin = Depends(get_current_admin)):
    return fail("模型连接测试将在 M2 实现", 501)


# ---------- 运营大屏 ----------

@router.get("/dashboard/overview")
async def dashboard(_: Admin = Depends(get_current_admin)):
    total_users = await User.all().count()
    total_analyses = await Analysis.all().count()
    total_patents = await Patent.all().count()

    risk = {"high": 0, "medium": 0, "low": 0, "excluded": 0}
    for a in await Analysis.all():
        rs = a.risk_summary or {}
        risk["high"] += rs.get("high", 0)
        risk["medium"] += rs.get("medium", 0)
        risk["low"] += rs.get("low", 0)
        risk["excluded"] += rs.get("excluded", 0)

    node_stats = {}
    for l in await AgentRunLog.all():
        s = node_stats.setdefault(l.node, {"total": 0, "success": 0, "degraded": 0, "failed": 0})
        s["total"] += 1
        if l.status == 1:
            s["success"] += 1
        elif l.status == 2:
            s["degraded"] += 1
        else:
            s["failed"] += 1

    source_stats = {}
    for p in await Patent.all():
        key = p.source or "unknown"
        source_stats[key] = source_stats.get(key, 0) + 1

    return ok({
        "total_users": total_users, "total_analyses": total_analyses,
        "total_patents": total_patents, "risk_distribution": risk,
        "node_stats": node_stats, "source_stats": source_stats,
    })
