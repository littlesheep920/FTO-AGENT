"""鉴权依赖：从 Header 取 token 解析当前用户；附带用户序列化工具。"""
from fastapi import HTTPException, Request

from common.security import verify_token
from models import User


def _extract_token(request: Request) -> str:
    token = request.headers.get("token", "")
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""


async def get_current_user(request: Request) -> User:
    """依赖：解析当前登录用户，失败抛 401。"""
    payload = verify_token(_extract_token(request))
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = await User.filter(id=payload.get("uid")).first()
    if not user or user.status != 1:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


async def get_current_admin(request: Request) -> User:
    """依赖：仅管理员（role=9）。"""
    user = await get_current_user(request)
    if user.role != 9:
        raise HTTPException(status_code=403, detail="无权限")
    return user


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "email": user.email,
        "role": user.role,
        "status": user.status,
    }
