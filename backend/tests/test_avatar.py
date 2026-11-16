"""头像与个人中心接口测试（TEST_PLAN AVATAR-01 ~ AVATAR-05 / ADR-0004）

覆盖：未登录拦截、上传成功、非图片拒绝、超限拒绝、预置头像白名单。
测试用户使用时间戳命名，用例结束清理用户、日志与产生的上传文件。
"""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.models.operation_log import OperationLog
from app.repositories import user_repo

# 只校验魔数的实现允许最小合法头；与 services/upload._detect_type 对齐
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def _unique_username(prefix: str = "avataruser") -> str:
    return f"{prefix}{int(time.time() * 1000) % 100000}"


def _register(username: str) -> TestClient:
    client = TestClient(app)
    resp = client.post("/api/v1/auth/register", json={"username": username, "password": "tea2026"})
    assert resp.status_code == 200, resp.text
    return client


def _cleanup_user(username: str, avatar_urls: list[str] | None = None) -> None:
    db = SessionLocal()
    try:
        user = user_repo.get_by_username(db, username)
        if user:
            db.query(OperationLog).filter(OperationLog.user_id == user.id).delete(
                synchronize_session=False
            )
            db.delete(user)
            db.commit()
    finally:
        db.close()

    for url in avatar_urls or []:
        if url.startswith("/uploads/"):
            path = Path(settings.UPLOAD_DIR) / url.removeprefix("/uploads/")
            path.unlink(missing_ok=True)


# ===== AVATAR-01：未登录不得修改头像 =====


def test_avatar_requires_login():
    client = TestClient(app)
    resp = client.post(
        "/api/v1/me/avatar",
        files={"file": ("a.png", PNG_BYTES, "image/png")},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100

    resp = client.put("/api/v1/me/avatar", json={"preset": "tea-01"})
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


# ===== AVATAR-02：上传图片成功并写入用户信息 =====


def test_avatar_upload_success_persists_url():
    username = _unique_username()
    client = _register(username)
    avatar_urls: list[str] = []
    try:
        resp = client.post(
            "/api/v1/me/avatar",
            files={"file": ("avatar.png", PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        avatar_url = body["data"]["avatar_url"]
        avatar_urls.append(avatar_url)
        assert avatar_url.startswith("/uploads/")
        assert avatar_url.endswith(".png")

        # 文件实际落盘
        stored = Path(settings.UPLOAD_DIR) / avatar_url.removeprefix("/uploads/")
        assert stored.is_file()

        # 会话读取到的用户信息同步带出头像
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["data"]["avatar_url"] == avatar_url

        # 头像变更留痕
        db = SessionLocal()
        try:
            user = user_repo.get_by_username(db, username)
            assert user is not None
            logs = (
                db.query(OperationLog)
                .filter(
                    OperationLog.user_id == user.id,
                    OperationLog.action == "avatar_update",
                )
                .all()
            )
            assert len(logs) == 1
        finally:
            db.close()
    finally:
        _cleanup_user(username, avatar_urls)


# ===== AVATAR-03：非图片文件拒绝 =====


def test_avatar_upload_rejects_non_image():
    username = _unique_username()
    client = _register(username)
    try:
        resp = client.post(
            "/api/v1/me/avatar",
            files={"file": ("note.txt", b"plain text, not an image", "text/plain")},
        )
        assert resp.status_code == 415
        assert resp.json()["code"] == 41500
    finally:
        _cleanup_user(username)


# ===== AVATAR-04：超过 5 MB 拒绝 =====


def test_avatar_upload_rejects_too_large():
    username = _unique_username()
    client = _register(username)
    try:
        oversized = PNG_BYTES + b"\x00" * (settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024)
        resp = client.post(
            "/api/v1/me/avatar",
            files={"file": ("huge.png", oversized, "image/png")},
        )
        assert resp.status_code == 413
        assert resp.json()["code"] == 41300
    finally:
        _cleanup_user(username)


# ===== AVATAR-05：预置头像白名单 =====


def test_avatar_preset_success_and_whitelist():
    username = _unique_username()
    client = _register(username)
    avatar_urls: list[str] = []
    try:
        resp = client.put("/api/v1/me/avatar", json={"preset": "tea-03"})
        assert resp.status_code == 200
        assert resp.json()["data"]["avatar_url"] == "/avatars/tea-03.svg"

        # 上传过的头像可被预置头像覆盖
        uploaded = client.post(
            "/api/v1/me/avatar",
            files={"file": ("avatar.jpg", JPEG_BYTES, "image/jpeg")},
        )
        avatar_urls.append(uploaded.json()["data"]["avatar_url"])
        resp = client.put("/api/v1/me/avatar", json={"preset": "tea-08"})
        assert resp.status_code == 200
        assert resp.json()["data"]["avatar_url"] == "/avatars/tea-08.svg"

        resp = client.put("/api/v1/me/avatar", json={"preset": "tea-99"})
        assert resp.status_code == 400
        assert resp.json()["code"] == 40000
    finally:
        _cleanup_user(username, avatar_urls)


def test_avatar_preset_rejects_extra_field():
    username = _unique_username()
    client = _register(username)
    try:
        resp = client.put(
            "/api/v1/me/avatar",
            json={"preset": "tea-01", "avatar_url": "/uploads/evil.png"},
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40000
    finally:
        _cleanup_user(username)
