# FTO 多 Agent 专利自由实施分析系统

面向中国法域、聚焦"控弯导管"细分领域的 FTO（自由实施）分析系统：
输入产品描述 → 8 个子 Agent 完成检索与权利要求比对 → 输出证据可追溯的 FTO Dossier。

## 技术栈
- 后端：FastAPI + Uvicorn
- ORM：Tortoise ORM + MySQL 8.0（可切 SQLite）
- Agent 编排：LangGraph + LangChain（1 Supervisor + 8 子 Agent）
- 专利数据源：Google Patents / Espacenet OPS / PATENTSCOPE（+ mock 演示源）
- 前端：Vue 3 + Vite + Element Plus + Pinia

## 目录结构
```
fto_agent_system/
├─ fastapi-app/          # 后端
│  ├─ main.py            # 启动入口（CORS、自动扫描路由、建表、种子）
│  ├─ settings.py        # 全部配置（环境变量）
│  ├─ models.py          # 19 张表 Tortoise ORM 定义
│  ├─ seed.py            # 种子数据（管理员/IPC 分类/Prompt/模型配置）
│  ├─ common/            # 统一响应、异常、鉴权、安全
│  ├─ api/               # 路由模块（自动扫描注册）
│  ├─ agent/             # LangGraph 编排层（graph + 8 nodes + 工具）
│  ├─ services/          # 专利数据源适配层（降级链 + 缓存）
│  ├─ exports/           # Dossier 导出（Markdown / PDF）
│  ├─ files/             # 上传文件目录
│  └─ data/              # 向量库/缓存/PDF 输出目录
├─ vue/                  # 前端（Vue3 + Element Plus）
└─ PRD.md                # 需求与架构文档
```

## 快速开始

### 1. 环境要求
- Python 3.10+（建议 3.11）
- Node.js 18+
- MySQL 5.7+/8.0（或改用 SQLite，见下）

### 2. 启动后端
```bash
cd fastapi-app
pip install -r requirements.txt

# 无 MySQL 时用 SQLite 演示
# Windows PowerShell:
$env:DB_ENGINE="tortoise.backends.sqlite"; $env:DB_NAME="data/fto_demo.sqlite3"; $env:PATENT_SOURCES="mock"
# Linux/macOS:
DB_ENGINE=tortoise.backends.sqlite DB_NAME=data/fto_demo.sqlite3 PATENT_SOURCES=mock python main.py

# Windows（MySQL）:
python main.py
```
- 服务：http://127.0.0.1:9090
- 接口文档：http://127.0.0.1:9090/docs

### 3. 启动前端
```bash
cd vue
npm install
npm run dev        # http://localhost:5173（已代理 /api 到后端 9090）
```

### 4. 默认账号
| 角色 | 账号 | 密码 |
|---|---|---|
| 管理员 | admin | admin123 |

### 5. 关键环境变量
| 变量 | 默认值 | 说明 |
|---|---|---|
| DB_ENGINE | tortoise.backends.mysql | 可改 tortoise.backends.sqlite |
| DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD | localhost / 3306 / fto_agent_system / root / root | |
| AUTO_CREATE_SCHEMA | 1 | dev 默认自动建表 |
| APP_SECRET_KEY | 默认密钥 | 生产必须改 |
| LLM_API_KEY | 空（回退 DEEPSEEK_API_KEY） | 为空则全局降级规则引擎 |
| LLM_BASE_URL / LLM_CHAT_MODEL | api.deepseek.com/v1 / deepseek-chat | OpenAI 协议 |
| PATENT_SOURCES | google_patents,espacenet,patentscope | 降级链；演示可设 mock |
| OPS_API_KEY | 空 | Espacenet OPS 官方 key |

## 里程碑
- [x] M1 骨架：main.py + models.py + 路由 + 鉴权
- [x] M2 Harness：graph.py + 8 node + trace + 降级
- [x] M3 数据源：专利数据源适配层 + 检索
- [x] M4 分析链：事实解析 → 权要解析 → Claim Chart → 风险定级
- [x] M5 输出：Reviewer + Dossier + 三端导出（PDF/Markdown）
- [x] M6 前端：门户端（输入/追问/Dossier）+ 管理端
- [ ] M7 打磨：真实数据源实测、Prompt 调优、文档
