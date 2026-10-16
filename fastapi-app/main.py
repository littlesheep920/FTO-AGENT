"""FTO Agent System 启动入口。

- CORS
- 业务异常处理（HTTP 200 + code 区分）
- api/ 路由自动扫描注册
- Tortoise ORM 注册 + 自动建表（dev）
- 启动时写入种子数据
"""
import importlib
import pkgutil

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from tortoise.contrib.fastapi import register_tortoise

import api
import settings
from common.exception import BizException
from common.response import fail

app = FastAPI(title="FTO Agent System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(status_code=200, content=fail(exc.msg, exc.code))


def register_routers():
    """自动扫描 api/ 下所有模块，注册其 router。"""
    for _, name, _ in pkgutil.iter_modules(api.__path__):
        if name.startswith("_"):
            continue
        module = importlib.import_module(f"api.{name}")
        router = getattr(module, "router", None)
        if router is None:
            continue
        prefix = getattr(module, "prefix", f"/api/{name}")
        app.include_router(router, prefix=prefix, tags=[name])


register_routers()

register_tortoise(
    app,
    config=settings.TORTOISE_ORM,
    generate_schemas=settings.AUTO_CREATE_SCHEMA,
    add_exception_handlers=True,
)


@app.get("/")
async def root():
    return {"code": 200, "msg": "FTO Agent System API", "data": None}


@app.on_event("startup")
async def on_startup():
    from seed import seed_all
    await seed_all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVER_PORT, reload=True)
