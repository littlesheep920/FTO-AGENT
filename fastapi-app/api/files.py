"""文件上传 / 下载（草图、参数表、权要草稿）。"""
import os
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

import settings
from common.deps import get_current_user
from common.exception import BizException
from common.response import ok
from models import FileAsset, User

router = APIRouter()
prefix = "/api/files"

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".xlsx", ".xls", ".pdf", ".txt", ".md"}


@router.post("/upload")
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise BizException(f"不支持的文件类型：{ext}", 400)
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise BizException(f"文件超过 {settings.MAX_UPLOAD_MB}MB 限制", 400)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)

    file_type = "image" if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} else \
                "excel" if ext in {".xlsx", ".xls"} else \
                "pdf" if ext == ".pdf" else "text"
    asset = await FileAsset.create(
        user=user, file_type=file_type, file_path=path,
        original_name=file.filename, status=1,
    )
    return ok({"id": asset.id, "path": path, "type": file_type, "name": file.filename})


@router.get("/download/{filename}")
async def download(filename: str, user: User = Depends(get_current_user)):
    # 防路径穿越：只允许纯文件名（不含路径分隔符/上级目录）
    if os.path.basename(filename) != filename or ".." in filename:
        raise BizException("非法文件名", 400)
    path = os.path.join(settings.UPLOAD_DIR, filename)
    # 所有权校验：只能下载自己上传的文件
    asset = await FileAsset.filter(file_path=path, user_id=user.id).first()
    if not asset:
        raise BizException("文件不存在或无权访问", 404)
    if not os.path.isfile(path):
        raise BizException("文件不存在", 404)
    return FileResponse(path, filename=asset.original_name or filename)
