# FTO 多 Agent 专利自由实施分析系统

基于 **FastAPI + LangGraph + LangChain** 构建的 FTO（Freedom to Operate，自由实施）分析系统：面向中国法域、聚焦"控弯导管"细分领域，用户输入一段产品描述（可附结构草图、参数表、权利要求草稿），系统编排 **8 个子 Agent** 完成专利检索、法律状态核验、权利要求比对，最终输出一份**证据可追溯的 FTO Dossier**（网页 / Markdown / PDF 三端导出）。

**最大特点：完全离线可用。** 未配置大模型 Key 时，全系统自动降级为「本地规则引擎」，检索、权要解析、特征比对、风险定级照常返回有意义的结果，不会因为缺 Key 而不可用。

【截图预留：系统首页 · 分析列表】

【截图预留：Dossier 卷宗页 · 风险卡片 + Claim Chart 着色比对】

【截图预留：运营大屏 · 风险分布饼图 + Agent 节点统计】

---

## 一、技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn（异步） |
| ORM / 数据库 | Tortoise ORM + MySQL 8.0（aiomysql），可切 SQLite |
| Agent 编排 | LangGraph（StateGraph + InMemorySaver）+ LangChain Tools |
| 大模型 | langchain-openai 协议，兼容 OpenAI / DeepSeek / 通义千问 / 智谱 / Moonshot / Ollama |
| 向量检索 | 自研轻量向量库（numpy 余弦相似度 + JSON 持久化），不引入 FAISS / Chroma |
| 专利数据源 | Google Patents / Espacenet OPS / PATENTSCOPE（降级链 + 缓存 + mock 演示源） |
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Pinia + axios |
| 渲染 | markdown-it + highlight.js（Dossier 渲染） |
| 导出 | reportlab + 中文字体（Noto Sans SC / 微软雅黑） |
| 认证 | pbkdf2 密码摘要 + HMAC Token（用户/管理员 token 角色隔离） |
| 可观测 | agent_run_log + trace（节点/意图/输入输出/tool_calls/耗时）+ Prompt 中心 + 模型热加载 |

---

## 二、系统架构

【截图预留：系统架构图 · 前端 → FastAPI → LangGraph 8 子 Agent → 专利数据源 → MySQL】

### 一次 FTO 分析的完整链路

以门户端 `POST /api/fto/analysis/{id}/run` 为例：

1. 前端带上用户 token 请求 → `deps.py` 解析出当前用户
2. ① **Input & Fact**：解析产品描述 + 上传附件（草图/参数表/权要草稿），提取技术特征事实，未知项发起一轮追问
3. ② **Retrieval Planner**：由已确认事实生成检索路线、中英查询词、IPC/CPC 分类锚点与检索式
4. ③ **Searcher**：走降级链实时检索 → 去重 → n-gram 相关性初筛 → 落命中快照
5. ④ **Family Resolver**：整理候选同族/分案关系（不自行确认同族）
6. ⑤ **Legal Status Verifier**：核验法律状态与 FTO 准入（有效/审中→准入，失效/届满→排除）
7. ⑥ **Claim Parser**：拆解授权独立权利要求的技术要素 + 原文定位
8. ⑦ **Claim Chart Draft**：产品事实 vs 权要要素逐项对照（命中/缺失/部分/存疑，LLM 优先 + 规则兜底）
9. ⑧ **Reviewer**：全面覆盖判定 → 高/中/低/排除定级 → 规避设计建议 → 组装 Dossier
10. 结果落库：patent / claim / claim_element / claim_chart / risk_assessment，返回 Dossier 三端可导出

---

## 三、核心功能

### 用户端（门户端）

| 功能 | 说明 |
|---|---|
| 分析管理 | 新建 / 列表 / 详情 / 删除，状态流转（草稿→进行中→待追问→完成/失败） |
| 多模态输入 | 产品文字描述 + 上传结构草图（图片）/ 参数表（Excel）/ 权利要求草稿（PDF/文本） |
| 澄清追问 | fact 提取出未知项时发起一轮追问，用户补充后继续 |
| FTO Dossier | 8 板块卷宗：执行摘要 / 检索策略 / 专利清单 / Claim Chart / 风险分级 / 规避建议 / 证据溯源 / 免责声明 |
| Claim Chart 可视化 | 独立权要要素逐项比对，命中/缺失/部分/存疑四色着色 |
| Agent 链路回放 | 8 个节点的执行过程、输入输出、tool_calls、耗时 |
| 三端导出 | 网页端渲染 + Markdown 下载 + PDF（中文字体） |

### 管理端

| 功能 | 说明 |
|---|---|
| 运营大屏 | 用户数/分析数/专利数 + 风险分布饼图 + Agent 节点调用统计 + 数据源命中统计 |
| Agent 日志 | 分页查看所有运行的节点日志（节点/意图/状态/耗时） |
| Prompt 管理 | 8 个场景 Prompt 在线编辑，保存即热生效（DB 优先于内置默认） |
| 模型配置 | 模型/Base URL/Key 在线配置，Key 掩码显示（环境变量/数据库来源区分） |

---

## 四、多 Agent 编排

【截图预留：Agent 编排图 · Supervisor 调度 8 子 Agent】

采用 **Supervisor + Workers** 模式，共 1 Supervisor + 8 子 Agent（防死循环双保险：MAX_LOOPS=6 + recursion_limit=30）：

| 节点 | 职责 | 离线（规则引擎）行为 |
|---|---|---|
| Supervisor | 总调度、轮次控制、trace 记录 | 固定顺序流水线 |
| ① Input & Fact | 多模态解析产品资料，提取结构事实、未知项、证据定位 | 正则按句切分 + 关键词 + 词典抽特征 |
| ② Retrieval Planner | 检索路线、查询词、IPC/CPC 分类锚点、检索式 | 关键词 + 固定 IPC 锚点拼布尔式 |
| ③ Searcher | 降级链检索、去重、相关性初筛、落快照 | 固定检索式打库，关键词命中数判相关 |
| ④ Family Resolver | 整理候选同族/分案关系（不自行确认） | 按公开号/优先权号规则分组 |
| ⑤ Legal Status Verifier | 核验官方状态证据、法域、日期、准入 | 规则匹配状态词（有效/失效/届满/撤回） |
| ⑥ Claim Parser | 拆解授权独立权要技术要素 + 原文定位 | 正则按"；、包括、其特征在于"切分 |
| ⑦ Claim Chart Draft | 产品事实 vs 权要要素逐项对照 | 关键词重合度 + 要素级包含判断 |
| ⑧ Reviewer | 全面覆盖判定、风险定级、规避建议、Dossier 组装 | 模板拼装 |

---

## 五、目录结构

```
fto_agent_system/
├─ fastapi-app/                  # 后端
│  ├─ main.py                    # 启动入口、CORS、路由自动扫描、建表、种子
│  ├─ settings.py                # 全部配置（环境变量）
│  ├─ models.py                  # 20 张表（user/admin/analysis/patent/claim/claim_chart...）
│  ├─ seed.py                    # 种子数据（管理员/IPC 分类/Prompt/模型配置）
│  ├─ api/                       # 路由模块（auth/user/analysis/files/admin 自动注册）
│  ├─ agent/                     # LangGraph 编排层
│  │  ├─ graph.py                # Supervisor + 8 Worker + 追问分支 + 防死循环
│  │  ├─ nodes/                  # fact/planner/searcher/family/status/parser/chart/reviewer
│  │  ├─ tools.py                # LangChain Tools（检索/权要解析/比对）
│  │  ├─ llm.py                  # 模型入口 + 配置热加载
│  │  ├─ prompts.py              # Prompt 中心（DB > 内置默认）
│  │  ├─ claim_utils.py          # 权要切分/领域关键词/规则比对
│  │  ├─ file_parser.py          # 附件解析（txt/md/pdf/xlsx）
│  │  └─ multimodal.py           # 视觉识图（结构草图）
│  ├─ services/                  # 专利数据源适配层（google_patents/espacenet/patentscope/mock）
│  ├─ exports/                   # Dossier 导出（markdown / pdf）
│  ├─ common/                    # 统一响应、异常、鉴权、安全
│  ├─ files/                     # 上传文件目录
│  └─ data/                      # 向量库/缓存/PDF 输出目录
├─ vue/                          # 前端
│  └─ src/
│     ├─ views/front/            # 门户端（Login/Home/AnalysisDetail）
│     ├─ views/manager/          # 管理端（Dashboard/Logs/Prompts/LlmConfig）
│     └─ components/             # DossierView 等
└─ PRD.md                        # 需求与架构文档
```

---

## 六、快速开始

### 1. 环境要求

- Python 3.10+（建议 3.11）
- Node.js 18+
- MySQL 5.7+/8.0（或改配置用 SQLite）

### 2. 数据库初始化

```sql
CREATE DATABASE fto_agent_system DEFAULT CHARSET utf8mb4;
```

> 开发环境默认 `AUTO_CREATE_SCHEMA=1` 自动建表 + 写入种子数据（管理员、IPC 分类、8 个 Prompt、模型配置）；生产建议关闭并手工执行迁移。

### 3. 启动后端

```bash
cd fastapi-app
pip install -r requirements.txt
python main.py
```

- 服务：http://127.0.0.1:9090
- 接口文档：http://127.0.0.1:9090/docs（Swagger）、/redoc

### 4. 启动前端

```bash
cd vue
npm install
npm run dev        # http://localhost:5173（已代理 /api 到后端 9090）
```

### 5. 默认账号

| 角色 | 账号 | 密码 |
|---|---|---|
| 管理员（管理端） | admin | admin123 |
| 用户（门户端） | 自行注册 | 注册时设置 |

---

## 七、配置说明

所有配置走**环境变量**（未引入 python-dotenv，无 .env 文件），默认值见 `fastapi-app/settings.py`。

### 数据库

| 变量 | 默认值 | 说明 |
|---|---|---|
| DB_ENGINE | tortoise.backends.mysql | 演示可改 tortoise.backends.sqlite |
| DB_HOST / DB_PORT | localhost / 3306 | |
| DB_NAME | fto_agent_system | SQLite 时改 data/demo.sqlite3 |
| DB_USER / DB_PASSWORD | root / root | |

### 大模型（不配即用规则引擎）

| 变量 | 默认值 | 说明 |
|---|---|---|
| LLM_API_KEY | 空（回退 DEEPSEEK_API_KEY） | **为空则全局降级为本地规则引擎** |
| LLM_BASE_URL | https://api.deepseek.com/v1 | OpenAI 协议，兼容各家 |
| LLM_CHAT_MODEL | deepseek-chat | |
| LLM_VISION_MODEL | 空 | 视觉模型（如 qwen-vl-max，用于草图识图） |
| LLM_EMBED_MODEL | text-embedding-3-small | |
| LLM_TEMPERATURE / LLM_TIMEOUT | 0.7 / 60 | |

### 专利数据源

| 变量 | 默认值 | 说明 |
|---|---|---|
| PATENT_SOURCES | google_patents,espacenet,patentscope | 降级链顺序；演示可设 mock |
| OPS_API_KEY | 空 | Espacenet OPS 官方 key（注册后填写） |
| JURISDICTION | CN | 法域 |
| SEARCH_TTL_HOURS | 24 | 检索缓存 TTL |

### 其他

| 变量 | 默认值 | 说明 |
|---|---|---|
| SERVER_PORT | 9090 | |
| APP_SECRET_KEY | 默认密钥 | **生产必须改** |
| TOKEN_TTL_DAYS | 7 | |
| UPLOAD_DIR / MAX_UPLOAD_MB | files / 8 | 上传目录与大小限制 |
| VECTOR_DIM | 1024 | 向量维度（降级 n-gram 哈希向量） |

---

## 八、API 一览

统一响应体：`{"code":200,"msg":"操作成功","data":...}`；异常也返回 HTTP 200，靠 code 判断。鉴权 token 放 Header `token`（用户 token 与管理端 token 角色隔离）。

| 模块 | 主要接口 |
|---|---|
| 用户认证 | POST /api/auth/login、POST /api/auth/register、POST /api/auth/reset-password |
| 管理员认证 | POST /api/auth/admin/login |
| 分析 | POST /api/fto/analysis、GET /api/fto/analysis/list、GET /api/fto/analysis/{id}、DELETE /api/fto/analysis/{id} |
| 执行 | POST /api/fto/analysis/{id}/run、POST /api/fto/analysis/{id}/clarify、GET /api/fto/analysis/{id}/status |
| 结果 | GET /api/fto/analysis/{id}/dossier、GET /api/fto/analysis/{id}/facts、GET /api/fto/analysis/{id}/trace、GET /api/fto/analysis/{id}/files |
| 导出 | GET /api/fto/analysis/{id}/export/markdown、GET /api/fto/analysis/{id}/export/pdf |
| 文件 | POST /api/files/upload（支持绑定 analysis_id）、GET /api/files/download/{filename} |
| 运维 | GET /api/fto/agent/logs、GET /api/fto/dashboard/overview、GET/PUT /api/fto/prompt、GET/PUT /api/fto/llm/config、POST /api/fto/llm/test |

---

## 九、离线降级机制

系统不依赖大模型也能跑通全部流程，降级点如下：

| 能力 | 有 Key | 无 Key |
|---|---|---|
| 事实提取 | LLM 结构化抽取 | 正则按句切分 + 领域词典 |
| 检索规划 | LLM 生成检索式 | 关键词 + 固定 IPC 锚点拼布尔式 |
| 特征比对 | LLM 语义比对（区分"单根/两根拉线"等） | 关键词重合度 + 要素级包含判断 |
| 权要解析 | 语义切要素 | 正则按"；、包括、其特征在于"切分 |
| 风险定级 | 归纳定级 + 规避建议润色 | 模板拼装 |
| 草图识图 | 视觉大模型返回描述 | 标记"需人工看图"并触发追问 |

数据源降级链：`Google Patents → Espacenet OPS → PATENTSCOPE →（可配 mock）`，每源独立限流（并发 ≤3、间隔 0.2s、失败重试 1 次、缓存 TTL 24h），全部失败则**明确报错 + 返回已获证据，绝不静默编造**。

---

## 十、项目亮点

1. **双引擎架构，无 Key 也能完整运行** —— 每个 Agent 节点都有「LLM 路径 + 本地规则路径」，无 Key、超时、解析失败均自动回落，没有大模型 Key 也能完整演示全部业务流程。
2. **多 Agent 协作，过程可解释** —— Supervisor 调度 8 个专家 Agent 顺序协作，每次运行写入 agent_run_log（node/意图/输入输出/tool_calls/耗时），前端可逐节点回放。
3. **证据可追溯的 FTO Dossier** —— 每个风险结论都能追溯到"哪件专利、哪条权利要求、哪个技术要素、哪段原文"，Claim Chart 四色着色。
4. **双端分离、角色隔离** —— 管理员/用户独立表、独立登录、token 角色隔离（互访对方接口返回 401）。
5. **多模态输入闭环** —— 文字描述 + 草图（识图）+ 参数表（Excel 解析）+ 权要草稿（PDF 抽取），统一进 fact 提取。
6. **模型与 Prompt 在线可调、热生效** —— 8 个场景 Prompt 存库在线编辑；模型配置支持各家 OpenAI 协议一键切换，保存即生效。
7. **三端导出** —— 网页交互视图 + Markdown 下载 + PDF（中文字体嵌入，reportlab）。
8. **工程细节经得起追问** —— 防死循环双保险、路径穿越防护、文件所有权校验、API Key 不落库/掩码返回、追问幂等重跑、检索缓存 TTL。

---

## 十一、已知注意事项

1. 真实专利源：Google Patents 非官方接口且国内不可达；Espacenet OPS 需注册 key；PATENTSCOPE 需登录会话（后续可扩展本地语料库模式）
2. 目前只做字面侵权（全面覆盖原则）级比对，等同侵权需专利律师人工判断
3. 只比对了独立权利要求，从属权要已解析入库、暂未进 Claim Chart（后续版本）
4. 法律状态目前取检索结果自带字段，真源需单独调 INPADOC/官方实时核验
5. MemorySaver 为进程内检查点，长期运行建议换 DB checkpointer
6. 管理员密码为 admin/admin123 仅用于开发演示，生产必须修改
7. 前端未启用图标自动导入，新增 Element Plus 图标需在 script 中显式 import
