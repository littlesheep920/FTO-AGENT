"""LLM 访问：配置热加载（DB 优先）+ 无 Key 降级。"""
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

import settings
from models import LlmConfig

_model_cache = {"sig": None, "model": None}


def _content_text(resp) -> str:
    content = getattr(resp, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
    return str(content)


async def get_chat_model():
    """返回 ChatOpenAI 实例；未配置 Key 返回 None（触发规则引擎降级）。"""
    cfg = await LlmConfig.first()
    key = (cfg.api_key if cfg and cfg.api_key else None) or settings.LLM_API_KEY
    if not key:
        return None
    base = (cfg.base_url if cfg and cfg.base_url else None) or settings.LLM_BASE_URL
    model_name = (cfg.chat_model if cfg and cfg.chat_model else None) or settings.LLM_CHAT_MODEL
    sig = (base, model_name, key)
    if _model_cache["sig"] != sig:
        _model_cache["model"] = ChatOpenAI(
            model=model_name, base_url=base, api_key=key,
            temperature=settings.LLM_TEMPERATURE, timeout=settings.LLM_TIMEOUT,
        )
        _model_cache["sig"] = sig
    return _model_cache["model"]


async def llm_enabled() -> bool:
    return (await get_chat_model()) is not None


async def ask_json(system_prompt: str, user_content: str):
    """请求 LLM 返回 JSON；无 Key 或解析失败返回 None。"""
    model = await get_chat_model()
    if model is None:
        return None
    resp = await model.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])
    text = _content_text(resp).strip()
    # 剥离 markdown 代码围栏
    if text.startswith("```"):
        first = text.find("\n")
        text = text[first + 1:] if first != -1 else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return None
