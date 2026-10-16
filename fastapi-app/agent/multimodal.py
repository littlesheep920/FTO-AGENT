"""多模态识图：有视觉模型时描述产品结构草图，否则返回 None（由 fact 标记需人工）。"""
import base64

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

import settings
from models import LlmConfig


async def describe_image(path: str):
    cfg = await LlmConfig.first()
    model_name = (cfg.vision_model if cfg and cfg.vision_model else None) or settings.LLM_VISION_MODEL
    if not model_name:
        return None
    key = (cfg.api_key if cfg and cfg.api_key else None) or settings.LLM_API_KEY
    base = (cfg.base_url if cfg and cfg.base_url else None) or settings.LLM_BASE_URL
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except Exception:
        return None
    model = ChatOpenAI(model=model_name, base_url=base, api_key=key, timeout=settings.LLM_TIMEOUT)
    resp = await model.ainvoke([HumanMessage(content=[
        {"type": "text", "text": "请描述这张医疗器械结构草图的技术特征（结构/材料/连接/运动/参数），用于专利侵权比对。"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
    ])])
    content = resp.content
    return content if isinstance(content, str) else str(content)
