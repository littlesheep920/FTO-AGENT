"""种子数据：管理员账号、IPC/CPC 分类锚点、Prompt 模板、模型配置。

幂等设计：重复启动不会重复插入。
"""
import settings
from common.security import hash_password
from agent.prompts import BUILTIN_PROMPTS
from models import IpcCode, LlmConfig, PromptTemplate, User

# 8 个 Agent 场景的默认 Prompt（与 agent/prompts.py 同源）
DEFAULT_PROMPTS = BUILTIN_PROMPTS

IPC_SEED = [
    ("A61M25/092", "导管远端操控/弯曲控制装置", "Catheter distal steering/deflection control",
     ["控弯", "可调弯", "弯曲控制", "偏转", "steerable", "deflectable"]),
    ("A61M25/01", "导管；空心探针", "Catheters; hollow probes",
     ["导管", "catheter"]),
    ("A61M25/10", "球囊导管", "Balloon catheters",
     ["球囊", "balloon"]),
    ("A61M25/09", "导丝", "Guide wires",
     ["导丝", "guide wire"]),
    ("A61B18/14", "消融导管（射频）", "Probes/electrodes for ablation",
     ["消融", "射频", "ablation"]),
    ("A61B17/00", "外科器械", "Surgical instruments",
     ["外科", "器械", "surgical"]),
]


async def seed_all():
    # 1. 管理员（默认 admin / admin123）
    if not await User.filter(username="admin").exists():
        await User.create(
            username="admin", password=hash_password("admin123"),
            nickname="管理员", role=9, status=1,
        )

    # 2. IPC/CPC 分类锚点
    for code, zh, en, kws in IPC_SEED:
        await IpcCode.get_or_create(
            code=code,
            defaults={"level": 1, "title_zh": zh, "title_en": en, "parent_code": None, "keywords": kws},
        )

    # 3. Prompt 模板（8 个场景）
    for scene, content in DEFAULT_PROMPTS.items():
        await PromptTemplate.get_or_create(
            scene=scene,
            defaults={"content": content, "enabled": 1, "version": 1},
        )

    # 4. 模型配置（默认 DeepSeek，无 Key 时降级规则引擎）
    # 注意：不把环境变量里的 API Key 写入数据库（Key 只存在环境变量，llm.py 运行时回退读取）
    if not await LlmConfig.exists():
        await LlmConfig.create(
            provider="deepseek", base_url=settings.LLM_BASE_URL,
            api_key="", chat_model=settings.LLM_CHAT_MODEL,
            vision_model=settings.LLM_VISION_MODEL, embed_model=settings.LLM_EMBED_MODEL,
            enabled=1,
        )
