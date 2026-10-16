"""种子数据：管理员账号、IPC/CPC 分类锚点、Prompt 模板、模型配置。

幂等设计：重复启动不会重复插入。
"""
import settings
from common.security import hash_password
from models import IpcCode, LlmConfig, PromptTemplate, User

# 8 个 Agent 场景的默认 Prompt（M2 起由对应节点读取并覆盖）
DEFAULT_PROMPTS = {
    "fact": "你是 Input & Fact Agent。从用户提供的产品资料中提取技术特征事实（结构/材料/连接/运动/参数/功能），"
            "逐项给出证据定位，无法确认的标记为未知项并生成追问问题。输出 JSON。",
    "planner": "你是 Retrieval Planner。基于已确认的产品事实，生成中国法域专利检索路线、中英查询词、IPC/CPC 分类锚点与检索式。输出 JSON。",
    "searcher": "你是 Searcher。执行专利检索、去重、相关性初筛，为每条候选给出纳入/排除理由。输出 JSON。",
    "family": "你是 Family Resolver。整理候选同族/分案关系与待核验证据，不自行确认同族。输出 JSON。",
    "status": "你是 Legal Status Verifier。核查官方法律状态证据、法域与日期，判断是否满足 FTO 准入条件。输出 JSON。",
    "parser": "你是 Claim Parser。拆解授权独立权利要求的技术要素并标注原文定位。输出 JSON。",
    "chart": "你是 Claim Chart Draft。将产品事实与权利要求技术要素逐项对照，给出命中/缺失/部分/存疑判断。输出 JSON。",
    "reviewer": "你是 Reviewer。基于 Claim Chart 与法律状态做全面覆盖判定、风险定级、规避建议，组装 FTO Dossier。输出 JSON。",
}

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
    if not await LlmConfig.exists():
        await LlmConfig.create(
            provider="deepseek", base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY, chat_model=settings.LLM_CHAT_MODEL,
            vision_model=settings.LLM_VISION_MODEL, embed_model=settings.LLM_EMBED_MODEL,
            enabled=1,
        )
