"""Prompt 中心：DB 优先，内置默认兜底。"""
from models import PromptTemplate

BUILTIN_PROMPTS = {
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


async def get_prompt(scene: str) -> str:
    row = await PromptTemplate.filter(scene=scene, enabled=1).first()
    if row and row.content:
        return row.content
    return BUILTIN_PROMPTS.get(scene, "")
