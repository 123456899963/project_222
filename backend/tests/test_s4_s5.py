"""内容扩展 S4/S5 测试（ADR-0003 / PRD S4 S5）

覆盖：
- S5 视频上传：正常 MP4、非视频拒绝、超时长拒绝、未登录拒绝、外链 video_url 拒绝
- S4 图片集：公开查询、TeaDetail.image_set、上限 9 张、删除、越权与非法路径
测试自带数据构造与清理，不依赖种子茶品的图片集状态。
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.models.tea import Tea

client = TestClient(app)


def _admin_client() -> TestClient:
    admin = TestClient(app)
    resp = admin.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return admin


def _mp4_bytes(duration_seconds: int = 60, timescale: int = 1000) -> bytes:
    """构造最小 ISO BMFF 文件：ftyp + moov/mvhd，供时长解析使用。"""
    payload = bytearray(100)
    payload[0] = 0  # mvhd version 0
    payload[12:16] = timescale.to_bytes(4, "big")
    payload[16:20] = (duration_seconds * timescale).to_bytes(4, "big")
    mvhd = (8 + len(payload)).to_bytes(4, "big") + b"mvhd" + bytes(payload)
    moov = (8 + len(mvhd)).to_bytes(4, "big") + b"moov" + mvhd
    ftyp = (24).to_bytes(4, "big") + b"ftyp" + b"isom" + (0).to_bytes(4, "big") + b"isommp42"
    return ftyp + moov


def _create_tea(*, is_active: bool = True) -> int:
    db = SessionLocal()
    try:
        tea = Tea(
            name=f"扩展测试茶{uuid.uuid4().hex[:6]}",
            category="green",
            origin="浙江 测试产区",
            season="春茶",
            shape_desc="扁平",
            soup_desc="清澈",
            aroma_desc="清香",
            taste_desc="鲜爽",
            is_active=is_active,
            favorite_count=0,
        )
        db.add(tea)
        db.commit()
        db.refresh(tea)
        return tea.id
    finally:
        db.close()


def _cleanup_tea(tea_id: int) -> None:
    db = SessionLocal()
    try:
        tea = db.query(Tea).filter(Tea.id == tea_id).first()
        if tea:
            db.delete(tea)
            db.commit()
    finally:
        db.close()


# === S5 视频上传 ============================================================


def test_s5_upload_mp4_ok():
    admin = _admin_client()
    resp = admin.post(
        "/api/v1/admin/media/video",
        files={"file": ("intro.mp4", _mp4_bytes(60), "video/mp4")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["url"].startswith("/uploads/videos/")
    assert data["duration"] == 60
    assert data["content_type"] == "video/mp4"


def test_s5_upload_rejects_non_video():
    admin = _admin_client()
    resp = admin.post(
        "/api/v1/admin/media/video",
        files={"file": ("fake.mp4", b"not-a-video", "video/mp4")},
    )
    assert resp.status_code == 415
    assert resp.json()["code"] == 41500


def test_s5_upload_rejects_too_long():
    admin = _admin_client()
    resp = admin.post(
        "/api/v1/admin/media/video",
        files={"file": ("long.mp4", _mp4_bytes(181), "video/mp4")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 40000
    assert "3 分钟" in resp.json()["message"]


def test_s5_upload_requires_admin():
    resp = TestClient(app).post(
        "/api/v1/admin/media/video",
        files={"file": ("intro.mp4", _mp4_bytes(30), "video/mp4")},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_s5_reject_third_party_video_url():
    admin = _admin_client()
    tea_id = _create_tea()
    try:
        payload = {
            "name": "外链视频茶",
            "category": "green",
            "origin": "浙江 测试产区",
            "shape_desc": "扁平",
            "soup_desc": "清澈",
            "aroma_desc": "清香",
            "taste_desc": "鲜爽",
            "water_temp": 85,
            "tea_amount": 3,
            "brew_time": 2,
            "main_image_url": "/uploads/2026/11/demo.png",
            "video_url": "https://cdn.example.com/a.mp4",
        }
        resp = admin.put(f"/api/v1/admin/teas/{tea_id}", json=payload)
        assert resp.status_code == 400
        assert resp.json()["code"] == 40000
    finally:
        _cleanup_tea(tea_id)


def test_s5_detail_returns_video_fields():
    tea_id = _create_tea()
    try:
        resp = client.get(f"/api/v1/teas/{tea_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "video_url" in data and data["video_url"] is None
        assert "video_duration" in data and data["video_duration"] is None
        assert data["image_set"] == []
    finally:
        _cleanup_tea(tea_id)


# === S4 图片集 ==============================================================


def _add_image(admin: TestClient, tea_id: int, url: str, sort_order: int | None = None):
    payload = {"image_url": url}
    if sort_order is not None:
        payload["sort_order"] = sort_order
    return admin.post(f"/api/v1/admin/teas/{tea_id}/images", json=payload)


def test_s4_add_list_and_detail_image_set():
    admin = _admin_client()
    tea_id = _create_tea()
    try:
        first = _add_image(admin, tea_id, "/uploads/2026/11/a.png")
        second = _add_image(admin, tea_id, "/uploads/2026/11/b.png")
        assert first.status_code == 200, first.text
        assert first.json()["data"]["sort_order"] == 0
        assert second.json()["data"]["sort_order"] == 1

        listed = client.get(f"/api/v1/teas/{tea_id}/images")
        assert listed.status_code == 200
        urls = [row["image_url"] for row in listed.json()["data"]]
        assert urls == ["/uploads/2026/11/a.png", "/uploads/2026/11/b.png"]

        detail = client.get(f"/api/v1/teas/{tea_id}").json()["data"]
        assert detail["image_set"] == urls
    finally:
        _cleanup_tea(tea_id)


def test_s4_max_nine_images():
    admin = _admin_client()
    tea_id = _create_tea()
    try:
        for index in range(9):
            resp = _add_image(admin, tea_id, f"/uploads/2026/11/{index}.png")
            assert resp.status_code == 200, resp.text

        over = _add_image(admin, tea_id, "/uploads/2026/11/over.png")
        assert over.status_code == 400
        assert over.json()["code"] == 40000
        assert "9" in over.json()["message"]
    finally:
        _cleanup_tea(tea_id)


def test_s4_delete_image():
    admin = _admin_client()
    tea_id = _create_tea()
    try:
        created = _add_image(admin, tea_id, "/uploads/2026/11/del.png").json()["data"]
        deleted = admin.delete(f"/api/v1/admin/teas/{tea_id}/images/{created['id']}")
        assert deleted.status_code == 200
        assert deleted.json()["data"]["deleted"] == created["id"]

        listed = client.get(f"/api/v1/teas/{tea_id}/images").json()["data"]
        assert listed == []
    finally:
        _cleanup_tea(tea_id)


def test_s4_delete_missing_image_404():
    admin = _admin_client()
    tea_id = _create_tea()
    try:
        resp = admin.delete(f"/api/v1/admin/teas/{tea_id}/images/99999999")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40400
    finally:
        _cleanup_tea(tea_id)


def test_s4_rejects_external_image_url():
    admin = _admin_client()
    tea_id = _create_tea()
    try:
        resp = _add_image(admin, tea_id, "https://cdn.example.com/x.png")
        assert resp.status_code == 400
        assert resp.json()["code"] == 40000
    finally:
        _cleanup_tea(tea_id)


def test_s4_write_requires_admin():
    tea_id = _create_tea()
    try:
        resp = TestClient(app).post(
            f"/api/v1/admin/teas/{tea_id}/images",
            json={"image_url": "/uploads/2026/11/a.png"},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == 40100
    finally:
        _cleanup_tea(tea_id)


def test_s4_off_shelf_tea_images_hidden():
    tea_id = _create_tea(is_active=False)
    try:
        resp = client.get(f"/api/v1/teas/{tea_id}/images")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401
    finally:
        _cleanup_tea(tea_id)
