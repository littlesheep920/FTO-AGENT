"""全局配置：全部走环境变量，未引入 python-dotenv（与参考项目一致）。

所有默认值见下方 _get 的 default 参数，生产环境务必通过环境变量覆盖。
"""
import os


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# ---------- 服务 ----------
SERVER_HOST = _get("SERVER_HOST", "http://127.0.0.1:9090")
SERVER_PORT = int(_get("SERVER_PORT", "9090"))

# ---------- 数据库 ----------
DB_ENGINE = _get("DB_ENGINE", "tortoise.backends.mysql")
DB_HOST = _get("DB_HOST", "localhost")
DB_PORT = int(_get("DB_PORT", "3306"))
DB_NAME = _get("DB_NAME", "fto_agent_system")
DB_USER = _get("DB_USER", "root")
DB_PASSWORD = _get("DB_PASSWORD", "root")
# dev 默认自动建表；生产建议关闭并手工执行 SQL
AUTO_CREATE_SCHEMA = _get("AUTO_CREATE_SCHEMA", "1") == "1"

# ---------- 认证 ----------
APP_SECRET_KEY = _get("APP_SECRET_KEY", "fto-demo-secret-key-change-me-in-prod")
TOKEN_TTL_DAYS = int(_get("TOKEN_TTL_DAYS", "7"))
PASSWORD_ITERATIONS = int(_get("PASSWORD_ITERATIONS", "100000"))

# ---------- 大模型（M2+ 使用） ----------
LLM_API_KEY = _get("LLM_API_KEY", "") or _get("DEEPSEEK_API_KEY", "")
LLM_BASE_URL = _get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_CHAT_MODEL = _get("LLM_CHAT_MODEL", "deepseek-chat")
LLM_VISION_MODEL = _get("LLM_VISION_MODEL", "")
LLM_EMBED_MODEL = _get("LLM_EMBED_MODEL", "text-embedding-3-small")
LLM_TEMPERATURE = float(_get("LLM_TEMPERATURE", "0.7"))
LLM_TIMEOUT = int(_get("LLM_TIMEOUT", "60"))

# ---------- 检索 ----------
JURISDICTION = _get("JURISDICTION", "CN")
RETRIEVE_TOP_K = int(_get("RETRIEVE_TOP_K", "20"))
SEARCH_TTL_HOURS = int(_get("SEARCH_TTL_HOURS", "24"))
SEARCH_CONCURRENCY = int(_get("SEARCH_CONCURRENCY", "3"))
SEARCH_INTERVAL = float(_get("SEARCH_INTERVAL", "0.2"))

# ---------- 专利数据源 ----------
# 降级链顺序：google_patents -> espacenet -> patentscope（可加 mock 用于演示）
PATENT_SOURCES = _get("PATENT_SOURCES", "google_patents,espacenet,patentscope")
OPS_API_KEY = _get("OPS_API_KEY", "")           # Espacenet OPS 官方 key
PATENT_TIMEOUT = int(_get("PATENT_TIMEOUT", "30"))

# ---------- 上传 ----------
UPLOAD_DIR = _get("UPLOAD_DIR", "files")
MAX_UPLOAD_MB = int(_get("MAX_UPLOAD_MB", "8"))

# ---------- 数据目录 / 向量 ----------
DATA_DIR = _get("DATA_DIR", "data")
VECTOR_STORE_PATH = _get("VECTOR_STORE_PATH", "data/vector_store.json")
VECTOR_DIM = int(_get("VECTOR_DIM", "1024"))


def build_db_url() -> str:
    """根据 DB_ENGINE 拼 Tortoise 连接串。"""
    if DB_ENGINE == "tortoise.backends.sqlite":
        # SQLite 时 DB_NAME 形如 data/fto_demo.sqlite3
        import os as _os
        if not _os.path.isabs(DB_NAME):
            _dir = _os.path.dirname(DB_NAME)
            if _dir and not _os.path.isdir(_dir):
                _os.makedirs(_dir, exist_ok=True)
        return f"sqlite://{DB_NAME}"
    return f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"


TORTOISE_ORM = {
    "connections": {"default": build_db_url()},
    "apps": {
        "models": {
            "models": ["models"],
            "default_connection": "default",
        }
    },
}
