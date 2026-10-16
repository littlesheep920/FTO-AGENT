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
        file_type=file_type, file_path=path,
        original_name=file.filename, status=1,
    )
    return ok({"id": asset.id, "path": path, "type": file_type, "name": file.filename})


@router.get("/download/{filename}")
async def download(filename: str, user: User = Depends(get_current_user)):
    path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        raise BizException("文件不存在", 404)
    return FileResponse(path, filename=filename)
