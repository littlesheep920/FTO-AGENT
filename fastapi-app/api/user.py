"""用户：信息 / 资料 / 改密码。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from common.deps import get_current_user, user_to_dict
from common.exception import BizException
from common.response import ok
from common.security import hash_password, verify_password
from models import User

router = APIRouter()
prefix = "/api/user"


class ProfileBody(BaseModel):
    nickname: str = ""
    email: str = ""


class PasswordBody(BaseModel):
    old_password: str
    new_password: str


@router.get("/info")
async def info(user: User = Depends(get_current_user)):
    return ok(user_to_dict(user))


@router.put("/profile")
async def update_profile(body: ProfileBody, user: User = Depends(get_current_user)):
    if body.nickname:
        user.nickname = body.nickname
    if body.email:
        user.email = body.email
    await user.save()
    return ok(user_to_dict(user))


@router.put("/password")
async def update_password(body: PasswordBody, user: User = Depends(get_current_user)):
    if not verify_password(body.old_password, user.password):
        raise BizException("原密码错误", 400)
    if len(body.new_password) < 6:
        raise BizException("新密码至少 6 位", 400)
    user.password = hash_password(body.new_password)
    await user.save()
    return ok()
