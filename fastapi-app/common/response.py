"""统一响应体：{code, msg, data}。"""
from typing import Any


def ok(data: Any = None, msg: str = "操作成功") -> dict:
    return {"code": 200, "msg": msg, "data": data}


def fail(msg: str = "操作失败", code: int = 500) -> dict:
    return {"code": code, "msg": msg, "data": None}
