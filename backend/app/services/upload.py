"""图片 / 视频上传服务（SECURITY S-22 / S-23 / S-24 + ADR-0003）

- 分块读取，超过上限立即中止（不把整个文件读入内存后再拒绝）
- 图片只按魔数判定 JPEG/PNG/WebP，视频只按 ISO BMFF（ftyp）判定 MP4/MOV
- 文件名服务端 UUID 生成；落盘路径必须位于 UPLOAD_DIR 内，防路径穿越
- 视频时长从 moov/mvhd 盒解析，不依赖外部 ffprobe（ADR-0003 S5：≤3 分钟）
"""

import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.response import (
    FileTooLarge,
    InternalError,
    UnsupportedMedia,
    UnsupportedVideo,
    ValidationError,
    VideoTooLarge,
    VideoTooLong,
    VideoUnreadable,
)

_CHUNK_SIZE = 1024 * 1024
_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
)
# ISO BMFF 品牌 → (content_type, ext)；统一以 offset 4 的 "ftyp" 作为容器标识
_QUICKTIME_BRANDS = {b"qt  "}


def _detect_type(head: bytes) -> tuple[str, str] | None:
    """返回 (content_type, ext)；WebP 需同时校验 RIFF....WEBP。"""
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"
    for signature, content_type, ext in _SIGNATURES:
        if head.startswith(signature):
            return content_type, ext
    return None


async def save_image(file: UploadFile) -> dict:
    """校验并落盘，返回 UploadResult 所需字段（url/original_filename/size/content_type）。"""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLarge
        chunks.append(chunk)

    if total == 0:
        raise ValidationError

    data = b"".join(chunks)
    detected = _detect_type(data[:12])
    if detected is None:
        raise UnsupportedMedia

    content_type, ext = detected
    now = datetime.now(timezone.utc)
    relative_dir = Path(f"{now.year:04d}") / f"{now.month:02d}"
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    target_dir = (upload_root / relative_dir).resolve()

    # 防路径穿越：目录与最终文件都必须落在 uploads/ 内
    if upload_root not in target_dir.parents and target_dir != upload_root:
        raise InternalError

    filename = f"{uuid4().hex}{ext}"
    target_path = (target_dir / filename).resolve()
    if target_path.parent != target_dir:
        raise InternalError

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
    except OSError:
        raise InternalError

    url = f"/uploads/{relative_dir.as_posix()}/{filename}"
    return {
        "url": url,
        "original_filename": file.filename or "",
        "size": total,
        "content_type": content_type,
    }


# === 视频（ADR-0003 S5）====================================================


def _detect_video_type(head: bytes) -> tuple[str, str] | None:
    """按 ISO BMFF 容器标识判定 MP4/MOV；不信任扩展名与 Content-Type。"""
    if len(head) < 12 or head[4:8] != b"ftyp":
        return None
    brand = head[8:12]
    if brand in _QUICKTIME_BRANDS:
        return "video/quicktime", ".mov"
    return "video/mp4", ".mp4"


def _iter_boxes(data: bytes, offset: int, end: int):
    """遍历 ISO BMFF 顶层盒：(type, payload_start, box_end)。"""
    while offset + 8 <= end:
        size = int.from_bytes(data[offset : offset + 4], "big")
        box_type = data[offset + 4 : offset + 8]
        header = 8
        if size == 1:  # 64 位长度
            if offset + 16 > end:
                return
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header = 16
        elif size == 0:  # 延伸到文件末尾
            size = end - offset
        if size < header or offset + size > end:
            return
        yield box_type, offset + header, offset + size
        offset += size


def _probe_duration(data: bytes) -> float | None:
    """从 moov/mvhd 解析时长（秒）；解析失败返回 None。"""
    try:
        for box_type, start, end in _iter_boxes(data, 0, len(data)):
            if box_type != b"moov":
                continue
            for inner_type, inner_start, inner_end in _iter_boxes(data, start, end):
                if inner_type != b"mvhd":
                    continue
                version = data[inner_start]
                if version == 1:
                    timescale = int.from_bytes(data[inner_start + 20 : inner_start + 24], "big")
                    duration = int.from_bytes(data[inner_start + 24 : inner_start + 32], "big")
                else:
                    timescale = int.from_bytes(data[inner_start + 12 : inner_start + 16], "big")
                    duration = int.from_bytes(data[inner_start + 16 : inner_start + 20], "big")
                if timescale <= 0 or duration <= 0:
                    return None
                return duration / timescale
    except (IndexError, ValueError):
        return None
    return None


async def save_video(file: UploadFile) -> dict:
    """校验并落盘视频，返回 url/original_filename/size/content_type/duration。"""
    max_bytes = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise VideoTooLarge
        chunks.append(chunk)

    if total == 0:
        raise ValidationError

    data = b"".join(chunks)
    detected = _detect_video_type(data[:12])
    if detected is None:
        raise UnsupportedVideo

    content_type, ext = detected

    duration = _probe_duration(data)
    if duration is None:
        raise VideoUnreadable
    # 向上取整，避免 179.6s 被判成 179s 后前端展示与限制不一致
    duration_seconds = math.ceil(duration)
    if duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
        raise VideoTooLong

    now = datetime.now(timezone.utc)
    relative_dir = Path("videos") / f"{now.year:04d}" / f"{now.month:02d}"
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    target_dir = (upload_root / relative_dir).resolve()

    if upload_root not in target_dir.parents and target_dir != upload_root:
        raise InternalError

    filename = f"{uuid4().hex}{ext}"
    target_path = (target_dir / filename).resolve()
    if target_path.parent != target_dir:
        raise InternalError

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
    except OSError:
        raise InternalError

    url = f"/uploads/{relative_dir.as_posix()}/{filename}"
    return {
        "url": url,
        "original_filename": file.filename or "",
        "size": total,
        "content_type": content_type,
        "duration": duration_seconds,
    }
