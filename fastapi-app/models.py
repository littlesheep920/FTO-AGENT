"""FTO Agent System 数据模型（19 张表，Tortoise ORM）。

设计说明：
- 基础表：user（合并 admin，用 role 区分）、agent_run_log、prompt_template、llm_config
- FTO 核心表：analysis、product_fact、clarification、retrieval_plan、patent、
  patent_family、legal_status、claim、claim_element、claim_chart、risk_assessment
- 支撑表：ipc_code、file_asset、search_cache、vector_index
"""
from tortoise import fields
from tortoise.models import Model


class TimestampMixin(Model):
    """带 id + 创建/更新时间的基础模型。"""
    id = fields.BigIntField(pk=True)
    create_time = fields.DatetimeField(auto_now_add=True)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True


# ============ 基础表 ============

class User(TimestampMixin):
    """用户（合并管理员：role=9 为管理员）。"""
    username = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=128)          # pbkdf2 摘要
    nickname = fields.CharField(max_length=50, null=True)
    avatar = fields.CharField(max_length=255, null=True)
    email = fields.CharField(max_length=100, null=True)
    role = fields.SmallIntField(default=1)               # 1 普通用户 / 9 管理员
    status = fields.SmallIntField(default=1)             # 1 正常 / 0 禁用

    class Meta:
        table = "user"


class AgentRunLog(Model):
    """Agent 运行日志（可观测，沿用参考项目）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="agent_logs",
        on_delete=fields.CASCADE, null=True)
    node = fields.CharField(max_length=50)               # fact/planner/searcher/.../reviewer
    intent = fields.CharField(max_length=50, null=True)
    input = fields.JSONField(null=True)
    output = fields.JSONField(null=True)
    tool_calls = fields.JSONField(null=True)
    duration_ms = fields.IntField(null=True)
    status = fields.SmallIntField(default=1)             # 1成功/2降级/3失败
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "agent_run_log"


class PromptTemplate(Model):
    """Prompt 中心（DB 优先于内置默认）。"""
    id = fields.BigIntField(pk=True)
    scene = fields.CharField(max_length=50, unique=True)
    content = fields.TextField()
    enabled = fields.SmallIntField(default=1)
    version = fields.IntField(default=1)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "prompt_template"


class LlmConfig(Model):
    """模型配置（热加载）。"""
    id = fields.BigIntField(pk=True)
    provider = fields.CharField(max_length=50, null=True)
    base_url = fields.CharField(max_length=255, null=True)
    api_key = fields.CharField(max_length=255, null=True)
    chat_model = fields.CharField(max_length=100, null=True)
    vision_model = fields.CharField(max_length=100, null=True)
    embed_model = fields.CharField(max_length=100, null=True)
    enabled = fields.SmallIntField(default=1)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "llm_config"


# ============ FTO 核心表 ============

class Analysis(TimestampMixin):
    """FTO 分析主卷宗（一次分析一行）。"""
    user = fields.ForeignKeyField(
        "models.User", related_name="analyses", on_delete=fields.CASCADE)
    title = fields.CharField(max_length=200)
    status = fields.SmallIntField(default=1)             # 1草稿/2进行中/3待追问/4完成/5失败
    product_description = fields.TextField(null=True)
    input_files = fields.JSONField(null=True)            # 上传文件 id 列表
    jurisdiction = fields.CharField(max_length=20, default="CN")
    risk_summary = fields.JSONField(null=True)           # {high:2, medium:3, low:5, excluded:40}
    executive_summary = fields.TextField(null=True)      # Markdown
    dossier_markdown = fields.TextField(null=True)       # 完整卷宗 Markdown
    dossier_pdf_path = fields.CharField(max_length=255, null=True)
    disclaimer = fields.TextField(null=True)

    class Meta:
        table = "analysis"


class ProductFact(Model):
    """产品技术特征事实（Input & Fact Agent 输出）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="product_facts", on_delete=fields.CASCADE)
    feature = fields.CharField(max_length=200)
    feature_type = fields.CharField(max_length=20, null=True)  # 结构/材料/连接/运动/参数/功能
    value = fields.TextField(null=True)
    evidence = fields.CharField(max_length=500, null=True)     # 证据定位
    confidence = fields.DecimalField(max_digits=3, decimal_places=2, null=True)
    is_unknown = fields.SmallIntField(default=0)               # 是否未知项
    status = fields.SmallIntField(default=1)                   # 1已确认/2存疑/3待追问/4已追问
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "product_fact"


class Clarification(Model):
    """追问记录（一轮追问）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="clarifications", on_delete=fields.CASCADE)
    round = fields.IntField(default=1)
    question = fields.CharField(max_length=500)
    answer = fields.TextField(null=True)
    fact_ids = fields.JSONField(null=True)               # 关联 product_fact.id
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "clarification"


class RetrievalPlan(Model):
    """检索计划（Retrieval Planner 输出）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="retrieval_plans", on_delete=fields.CASCADE)
    query_terms = fields.JSONField(null=True)
    ipc_anchors = fields.JSONField(null=True)
    search_expressions = fields.JSONField(null=True)
    data_sources = fields.JSONField(null=True)
    date_range = fields.JSONField(null=True)
    status = fields.SmallIntField(default=1)             # 1计划中/2已执行
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "retrieval_plan"


class Patent(Model):
    """专利命中快照（Searcher 落库，分析阶段基于它离线进行）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="patents", on_delete=fields.CASCADE)
    patent_no = fields.CharField(max_length=50)          # 公开号，如 CN1133xxxxxA
    title = fields.CharField(max_length=500, null=True)
    abstract = fields.TextField(null=True)
    applicant = fields.CharField(max_length=255, null=True)
    inventor = fields.CharField(max_length=255, null=True)
    application_date = fields.DateField(null=True)
    publication_date = fields.DateField(null=True)
    grant_date = fields.DateField(null=True)
    ipc_codes = fields.JSONField(null=True)
    cpc_codes = fields.JSONField(null=True)
    source = fields.CharField(max_length=20, null=True)  # google_patents/espacenet/patentscope
    source_url = fields.CharField(max_length=500, null=True)  # 官方链接溯源
    raw_snapshot = fields.TextField(null=True)           # 原始 JSON/XML 快照
    relevance_score = fields.DecimalField(max_digits=5, decimal_places=2, null=True)
    screen_status = fields.SmallIntField(default=3)      # 1候选/2排除/3待定
    screen_reason = fields.CharField(max_length=500, null=True)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "patent"
        unique_together = (("analysis", "patent_no"),)


class PatentFamily(Model):
    """家族关系（Family Resolver：只整理不确认）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="patent_families", on_delete=fields.CASCADE)
    patent = fields.ForeignKeyField(
        "models.Patent", related_name="family_records", on_delete=fields.CASCADE)
    family_id = fields.CharField(max_length=50, null=True)
    related_patent_no = fields.CharField(max_length=50, null=True)
    relation_type = fields.CharField(max_length=20, null=True)  # 同族/分案/母案/继续申请/疑似
    evidence = fields.CharField(max_length=500, null=True)
    status = fields.SmallIntField(default=1)             # 1待核验/2已核验/3存疑
    note = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "patent_family"


class LegalStatus(Model):
    """法律状态快照（Legal Status Verifier，单独现查）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="legal_statuses", on_delete=fields.CASCADE)
    patent = fields.ForeignKeyField(
        "models.Patent", related_name="legal_statuses", on_delete=fields.CASCADE)
    jurisdiction = fields.CharField(max_length=20, default="CN")
    status = fields.CharField(max_length=20, null=True)  # 有效/失效/审中/届满/视为放弃/撤回
    status_date = fields.DateField(null=True)
    status_source = fields.CharField(max_length=30, null=True)  # INPADOC/google_legal_events/cnipa
    source_url = fields.CharField(max_length=500, null=True)
    fee_status = fields.CharField(max_length=20, null=True)
    admissibility = fields.SmallIntField(default=1)      # 1准入/2排除
    admissibility_reason = fields.CharField(max_length=500, null=True)
    verify_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "legal_status"


class Claim(Model):
    """权利要求（Claim Parser 输出）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="claims", on_delete=fields.CASCADE)
    patent = fields.ForeignKeyField(
        "models.Patent", related_name="claims", on_delete=fields.CASCADE)
    claim_no = fields.IntField()
    claim_type = fields.SmallIntField(default=2)         # 1独立/2从属
    claim_text = fields.TextField(null=True)
    text_location = fields.CharField(max_length=100, null=True)  # 原文定位
    status = fields.SmallIntField(default=1)             # 1已解析/2需人工

    class Meta:
        table = "claim"


class ClaimElement(Model):
    """技术要素（Claim Parser 拆解结果）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="claim_elements", on_delete=fields.CASCADE)
    patent = fields.ForeignKeyField(
        "models.Patent", related_name="claim_elements", on_delete=fields.CASCADE)
    claim = fields.ForeignKeyField(
        "models.Claim", related_name="elements", on_delete=fields.CASCADE)
    element_no = fields.IntField()
    element_text = fields.TextField(null=True)
    element_category = fields.CharField(max_length=20, null=True)  # 结构/材料/连接/运动/参数/功能
    text_location = fields.CharField(max_length=100, null=True)

    class Meta:
        table = "claim_element"


class ClaimChart(Model):
    """特征对照（Claim Chart Draft 输出，全系统最核心的表）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="claim_charts", on_delete=fields.CASCADE)
    patent = fields.ForeignKeyField(
        "models.Patent", related_name="claim_charts", on_delete=fields.CASCADE)
    claim = fields.ForeignKeyField(
        "models.Claim", related_name="claim_charts", on_delete=fields.CASCADE)
    product_fact = fields.ForeignKeyField(
        "models.ProductFact", related_name="claim_charts", on_delete=fields.CASCADE)
    match_status = fields.CharField(max_length=10, null=True)  # 命中/缺失/部分/存疑
    rationale = fields.TextField(null=True)
    evidence_product = fields.CharField(max_length=500, null=True)
    evidence_claim = fields.CharField(max_length=500, null=True)
    confidence = fields.DecimalField(max_digits=3, decimal_places=2, null=True)
    is_full_coverage = fields.SmallIntField(default=0)   # 该权要是否被全面覆盖
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "claim_chart"


class RiskAssessment(Model):
    """风险定级（Reviewer 输出，一件专利一行）。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="risk_assessments", on_delete=fields.CASCADE)
    patent = fields.ForeignKeyField(
        "models.Patent", related_name="risk_assessments", on_delete=fields.CASCADE)
    risk_level = fields.CharField(max_length=10, null=True)  # 高/中/低/排除
    basis = fields.TextField(null=True)                   # 定级依据：法律状态 + 全面覆盖
    design_around = fields.TextField(null=True)           # 规避设计建议
    conclusion = fields.TextField(null=True)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "risk_assessment"


# ============ 支撑表 ============

class IpcCode(Model):
    """IPC/CPC 分类锚点（种子数据）。"""
    id = fields.BigIntField(pk=True)
    code = fields.CharField(max_length=30, unique=True)
    level = fields.IntField(default=1)
    title_zh = fields.CharField(max_length=200, null=True)
    title_en = fields.CharField(max_length=200, null=True)
    parent_code = fields.CharField(max_length=30, null=True)
    keywords = fields.JSONField(null=True)

    class Meta:
        table = "ipc_code"


class FileAsset(Model):
    """上传附件（草图/参数表/权要草稿）+ 解析结果。"""
    id = fields.BigIntField(pk=True)
    analysis = fields.ForeignKeyField(
        "models.Analysis", related_name="file_assets",
        on_delete=fields.CASCADE, null=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="file_assets",
        on_delete=fields.CASCADE, null=True)
    file_type = fields.CharField(max_length=20, null=True)  # image/excel/pdf/text
    file_path = fields.CharField(max_length=255)
    original_name = fields.CharField(max_length=255, null=True)
    parsed_content = fields.TextField(null=True)
    status = fields.SmallIntField(default=1)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "file_asset"


class SearchCache(Model):
    """检索缓存（TTL 24h）。"""
    id = fields.BigIntField(pk=True)
    cache_key = fields.CharField(max_length=255, unique=True)
    query = fields.TextField(null=True)
    result_json = fields.JSONField(null=True)
    ttl_hours = fields.IntField(default=24)
    expire_at = fields.DatetimeField(null=True)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "search_cache"


class VectorIndex(Model):
    """自研向量库持久化（专利文本 → 向量）。"""
    id = fields.BigIntField(pk=True)
    patent = fields.ForeignKeyField(
        "models.Patent", related_name="vectors",
        on_delete=fields.CASCADE, null=True)
    doc_text = fields.TextField(null=True)
    vector = fields.JSONField(null=True)
    dim = fields.IntField(default=1024)
    model_used = fields.CharField(max_length=100, null=True)
    create_time = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "vector_index"
