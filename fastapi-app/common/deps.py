"""鉴权依赖：用户/管理员 token 角色隔离 + 序列化工具。"""
from fastapi import HTTPException, Request

from common.security import verify_token
from models import Admin, User


def _extract_token(request: Request) -> str:
    token = request.headers.get("token", "")
    if token:
        return token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""


async def get_current_user(request: Request) -> User:
    """依赖：解析当前普通用户（拒绝管理员 token）。"""
    payload = verify_token(_extract_token(request))
    if not payload or payload.get("role") == 9:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = await User.filter(id=payload.get("uid")).first()
    if not user or user.status != 1:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


async def get_current_admin(request: Request) -> Admin:
    """依赖：仅管理员（独立 admin 表 + role=9 token）。"""
    payload = verify_token(_extract_token(request))
    if not payload or payload.get("role") != 9:
        raise HTTPException(status_code=401, detail="管理员登录已过期")
    admin = await Admin.filter(id=payload.get("uid")).first()
    if not admin or admin.status != 1:
        raise HTTPException(status_code=401, detail="管理员不存在或已禁用")
    return admin


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


def admin_to_dict(admin: Admin) -> dict:
    return {
        "id": admin.id,
        "username": admin.username,
        "nickname": admin.nickname,
        "status": admin.status,
    }
