"""认证：登录 / 注册 / 重置密码。"""
from fastapi import APIRouter
from pydantic import BaseModel
from tortoise.exceptions import IntegrityError

from common.deps import user_to_dict
from common.exception import BizException
from common.response import ok
from common.security import create_token, hash_password, verify_password
from models import Admin, User

router = APIRouter()
prefix = "/api/auth"


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str
    password: str
    nickname: str = ""


class ResetBody(BaseModel):
    username: str
    old_password: str
    new_password: str


@router.post("/login")
async def login(body: LoginBody):
    user = await User.filter(username=body.username).first()
    if not user or not verify_password(body.password, user.password):
        raise BizException("用户名或密码错误", 401)
    if user.status != 1:
        raise BizException("账号已禁用", 403)
    return ok({"token": create_token(user.id, user.username), "user": user_to_dict(user)})


@router.post("/register")
async def register(body: RegisterBody):
    if len(body.username) < 3 or len(body.password) < 6:
        raise BizException("用户名至少 3 位，密码至少 6 位", 400)
    if await User.filter(username=body.username).exists():
        raise BizException("用户名已存在", 400)
    try:
        user = await User.create(
            username=body.username,
            password=hash_password(body.password),
            nickname=body.nickname or body.username,
            role=1, status=1,
        )
    except IntegrityError:
        raise BizException("用户名已存在", 400)
    return ok({"token": create_token(user.id, user.username), "user": user_to_dict(user)})


@router.post("/reset-password")
async def reset_password(body: ResetBody):
    user = await User.filter(username=body.username).first()
    if not user or not verify_password(body.old_password, user.password):
        raise BizException("原密码错误", 400)
    user.password = hash_password(body.new_password)
    await user.save()
    return ok()


# ---------- 管理员登录（独立 admin 表） ----------

@router.post("/admin/login")
async def admin_login(body: LoginBody):
    admin = await Admin.filter(username=body.username).first()
    if not admin or not verify_password(body.password, admin.password):
        raise BizException("管理员用户名或密码错误", 401)
    if admin.status != 1:
        raise BizException("管理员账号已禁用", 403)
    return ok({
        "token": create_token(admin.id, admin.username, role=9),
        "admin": {"id": admin.id, "username": admin.username, "nickname": admin.nickname},
    })
