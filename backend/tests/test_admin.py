"""管理员后台测试（对齐 API_CONTRACT §4.6 / TEST_PLAN PERM / TEA / UPLOAD）

覆盖：
- PERM：游客 401、普通用户 403、角色实时读库、先鉴权后校验参数
- TEA：后台列表（含下架/状态筛选/分页/关键词）、详情、新增、全量编辑、上下架联动
- TIPS：省略保持、null/空白清空
- STATS：总数/上架/下架/六大茶类分布
- UPLOAD：JPEG/PNG/WebP、超限 413、非法类型 415、魔数、UUID 文件名、防路径穿越

测试数据带唯一后缀，用例结束清理茶品、收藏、操作日志与上传文件。
"""

import re
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.models.favorite import FavoriteItem
from app.models.operation_log import OperationLog
from app.models.tea import Tea, TeaTips
from app.repositories import user_repo

client = TestClient(app)

JPEG_BYTES = b"\xff\xd8\xff" + b"jpeg-test" * 20
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"png-test" * 20
WEBP_BYTES = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"webp-test" * 20


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _admin_client() -> TestClient:
    admin = TestClient(app)
    resp = admin.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["role"] == "admin"
    return admin


def _payload(name: str | None = None, **overrides) -> dict:
    data = {
        "name": name or f"测试茶品{_uid()}",
        "category": "green",
        "origin": "浙江 测试产区",
        "season": "春茶",
        "fermentation": "不发酵",
        "price_range": "100-300元/50g",
        "representative_variety": "测试品种",
        "shape_desc": "条索紧结",
        "soup_desc": "汤色清亮",
        "aroma_desc": "清香持久",
        "taste_desc": "鲜爽回甘",
        "water_temp": 85.5,
        "tea_amount": 3.0,
        "brew_time": 90.0,
        "main_image_url": "/uploads/2026/01/seed.jpg",
        "tips_history": "测试历史",
        "tips_suitable": "测试人群",
        "tips_misconception": "测试误区",
        "tips_official_note": "测试笔记",
    }
    data.update(overrides)
    return data


def _update_payload(**overrides) -> dict:
    """PUT 全量编辑不接受 tips_*（小贴士走独立端点）。"""
    data = _payload(**overrides)
    for key in ("tips_history", "tips_suitable", "tips_misconception", "tips_official_note"):
        data.pop(key, None)
    return data


def _create_tea(admin: TestClient, **overrides) -> dict:
    resp = admin.post("/api/v1/admin/teas", json=_payload(**overrides))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    return body["data"]


def _cleanup_teas(tea_ids: list[int]) -> None:
    db = SessionLocal()
    try:
        for tea_id in tea_ids:
            db.query(FavoriteItem).filter(FavoriteItem.tea_id == tea_id).delete(
                synchronize_session=False
            )
            db.query(TeaTips).filter(TeaTips.tea_id == tea_id).delete(synchronize_session=False)
            db.query(OperationLog).filter(OperationLog.target_id == tea_id).delete(
                synchronize_session=False
            )
            db.query(Tea).filter(Tea.id == tea_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _cleanup_user(username: str) -> None:
    db = SessionLocal()
    try:
        user = user_repo.get_by_username(db, username)
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _max_log_id() -> int:
    db = SessionLocal()
    try:
        latest = db.query(OperationLog).order_by(OperationLog.id.desc()).first()
        return latest.id if latest else 0
    finally:
        db.close()


def _cleanup_logs_after(log_id: int) -> None:
    db = SessionLocal()
    try:
        db.query(OperationLog).filter(OperationLog.id > log_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _remove_upload(url: str) -> None:
    path = Path(settings.UPLOAD_DIR) / url.removeprefix("/uploads/")
    path.unlink(missing_ok=True)


# ===== PERM =====


def _guest_requests() -> list[dict]:
    return [
        {"method": "get", "url": "/api/v1/admin/stats"},
        {"method": "get", "url": "/api/v1/admin/teas"},
        {"method": "get", "url": "/api/v1/admin/teas/1"},
        {"method": "post", "url": "/api/v1/admin/teas", "json": _payload()},
        {"method": "put", "url": "/api/v1/admin/teas/1", "json": _update_payload()},
        {"method": "patch", "url": "/api/v1/admin/teas/1/toggle"},
        {"method": "put", "url": "/api/v1/admin/teas/1/tips", "json": {"tips_history": None}},
        {
            "method": "post",
            "url": "/api/v1/admin/upload",
            "files": {"file": ("test.jpg", JPEG_BYTES, "image/jpeg")},
        },
    ]


def test_admin_perm_01_guest_gets_401_for_all_endpoints():
    for request in _guest_requests():
        resp = client.request(**request)
        assert resp.status_code == 401, request
        assert resp.json()["code"] == 40100, request
        assert resp.json()["data"] is None


def test_admin_perm_02_normal_user_gets_403_for_all_endpoints():
    username = f"perm{_uid()}"
    try:
        register = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "tea2026"},
        )
        assert register.status_code == 200
        normal = TestClient(app)
        normal.cookies = register.cookies
        for request in _guest_requests():
            resp = normal.request(**request)
            assert resp.status_code == 403, request
            assert resp.json()["code"] == 40300, request
            assert resp.json()["data"] is None
    finally:
        _cleanup_user(username)


def test_admin_perm_03_role_is_read_live_from_db():
    username = f"perm{_uid()}"
    try:
        register = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "tea2026"},
        )
        live = TestClient(app)
        live.cookies = register.cookies
        assert live.get("/api/v1/admin/stats").status_code == 403

        db = SessionLocal()
        try:
            user = user_repo.get_by_username(db, username)
            user.role = "admin"
            db.commit()
        finally:
            db.close()
        # 不重新登录，角色实时读库后立即可用
        assert live.get("/api/v1/admin/stats").status_code == 200

        db = SessionLocal()
        try:
            user = user_repo.get_by_username(db, username)
            user.role = "user"
            db.commit()
        finally:
            db.close()
        assert live.get("/api/v1/admin/stats").status_code == 403
    finally:
        _cleanup_user(username)


def test_admin_perm_04_auth_precedes_parameter_validation():
    # 无会话 + 非法参数 → 仍返回 401，而不是 400
    resp = client.get("/api/v1/admin/teas", params={"category": "black", "page": "abc"})
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100

    resp = client.post("/api/v1/admin/teas", json={"name": 123})
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100

    # 普通用户 + 非法参数 → 403
    username = f"perm{_uid()}"
    try:
        register = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "tea2026"},
        )
        normal = TestClient(app)
        normal.cookies = register.cookies
        resp = normal.get("/api/v1/admin/teas", params={"category": "black"})
        assert resp.status_code == 403
        assert resp.json()["code"] == 40300
    finally:
        _cleanup_user(username)


# ===== TEA / 列表与详情 =====


def test_admin_tea_01_list_includes_inactive_and_filters_status():
    admin = _admin_client()
    tea = _create_tea(admin)
    tea_id = tea["id"]
    try:
        resp = admin.patch(f"/api/v1/admin/teas/{tea_id}/toggle")
        assert resp.status_code == 200

        # 省略 is_active：含下架茶品
        data = admin.get("/api/v1/admin/teas", params={"page_size": 50}).json()["data"]
        ids = {item["id"] for item in data["items"]}
        assert tea_id in ids
        item = next(i for i in data["items"] if i["id"] == tea_id)
        assert item["is_active"] is False
        assert set(item.keys()) == {
            "id",
            "name",
            "category",
            "origin",
            "season",
            "main_image_url",
            "is_active",
            "favorite_count",
            "created_at",
            "updated_at",
        }

        data = admin.get(
            "/api/v1/admin/teas", params={"is_active": "false", "page_size": 50}
        ).json()["data"]
        assert all(i["is_active"] is False for i in data["items"])
        assert tea_id in {i["id"] for i in data["items"]}

        data = admin.get(
            "/api/v1/admin/teas", params={"is_active": "true", "page_size": 50}
        ).json()["data"]
        assert all(i["is_active"] is True for i in data["items"])
        assert tea_id not in {i["id"] for i in data["items"]}
    finally:
        _cleanup_teas([tea_id])


def test_admin_tea_02_list_filter_keyword_category_and_pagination():
    admin = _admin_client()
    marker = _uid()
    tea = _create_tea(admin, name=f"筛选茶{marker}", category="white")
    tea_id = tea["id"]
    try:
        data = admin.get("/api/v1/admin/teas", params={"keyword": marker}).json()["data"]
        assert [i["id"] for i in data["items"]] == [tea_id]

        data = admin.get(
            "/api/v1/admin/teas", params={"category": "white", "page": 1, "page_size": 2}
        ).json()["data"]
        assert data["page"] == 1 and data["page_size"] == 2
        assert len(data["items"]) <= 2
        assert all(i["category"] == "white" for i in data["items"])

        data = admin.get("/api/v1/admin/teas", params={"page": 0, "page_size": 999}).json()["data"]
        assert data["page"] == 1 and data["page_size"] == 50
    finally:
        _cleanup_teas([tea_id])


def test_admin_tea_03_list_invalid_params_and_detail_off_shelf():
    admin = _admin_client()
    tea = _create_tea(admin)
    tea_id = tea["id"]
    try:
        admin.patch(f"/api/v1/admin/teas/{tea_id}/toggle")
        detail = admin.get(f"/api/v1/admin/teas/{tea_id}").json()["data"]
        assert detail["is_active"] is False
        assert detail["name"] == tea["name"]

        for params in (
            {"category": "black"},
            {"sort": "relevance"},
            {"is_active": "abc"},
            {"page": "abc"},
            {"keyword": "茶" * 51},
        ):
            resp = admin.get("/api/v1/admin/teas", params=params)
            assert resp.status_code == 400, params
            assert resp.json()["code"] == 40000, params

        resp = admin.get("/api/v1/admin/teas/999999")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40400
    finally:
        _cleanup_teas([tea_id])


# ===== TEA / 新增 =====


def test_admin_tea_04_create_writes_tea_tips_and_log():
    admin = _admin_client()
    name = f"新增茶品{_uid()}"
    tea_id = None
    try:
        tea = _create_tea(admin, name=name)
        tea_id = tea["id"]
        assert tea["name"] == name
        assert tea["is_active"] is True
        assert tea["favorite_count"] == 0
        assert tea["tips_history"] == "测试历史"
        assert tea["created_at"].endswith("Z")

        db = SessionLocal()
        try:
            row = db.query(Tea).filter(Tea.id == tea_id).first()
            assert row is not None and row.name == name
            tips = db.query(TeaTips).filter(TeaTips.tea_id == tea_id).first()
            assert tips is not None and tips.history == "测试历史"
            log = (
                db.query(OperationLog)
                .filter(OperationLog.target_id == tea_id, OperationLog.action == "create_tea")
                .first()
            )
            assert log is not None and log.user_id is not None and log.target_type == "tea"
        finally:
            db.close()
    finally:
        if tea_id:
            _cleanup_teas([tea_id])


def test_admin_tea_05_create_rejects_business_managed_fields_and_invalid_values():
    admin = _admin_client()
    db = SessionLocal()
    try:
        before = db.query(Tea).count()
    finally:
        db.close()

    for overrides in (
        {"is_active": False},
        {"favorite_count": 9},
        {"id": 1},
        {"name": "   "},
        {"category": "black"},
        {"origin": ""},
        {"shape_desc": ""},
        {"water_temp": 69.9},
        {"water_temp": 85.55},
        {"tea_amount": 0},
        {"main_image_url": "javascript:alert(1)"},
        {"tips_history": 123},
    ):
        resp = admin.post("/api/v1/admin/teas", json=_payload(**overrides))
        assert resp.status_code == 400, overrides
        assert resp.json()["code"] == 40000, overrides
        assert resp.json()["data"] is None

    db = SessionLocal()
    try:
        assert db.query(Tea).count() == before
    finally:
        db.close()


# ===== TEA / 全量编辑 =====


def test_admin_tea_06_update_replaces_fields_and_keeps_managed_fields():
    admin = _admin_client()
    tea = _create_tea(admin)
    tea_id = tea["id"]
    try:
        favorite = admin.post(f"/api/v1/favorites/{tea_id}")
        assert favorite.status_code == 200

        new_name = f"编辑后{_uid()}"
        update = _update_payload(
            name=new_name,
            season=None,
            fermentation=None,
            price_range=None,
            representative_variety=None,
            water_temp=90.0,
        )
        resp = admin.put(f"/api/v1/admin/teas/{tea_id}", json=update)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["name"] == new_name
        assert data["season"] is None and data["fermentation"] is None
        assert data["price_range"] is None and data["representative_variety"] is None
        assert data["water_temp"] == 90.0
        assert data["is_active"] is True
        assert data["favorite_count"] == 1
        assert data["tips_history"] == "测试历史"  # 茶品 PUT 不触碰小贴士

        db = SessionLocal()
        try:
            log_count = (
                db.query(OperationLog)
                .filter(OperationLog.target_id == tea_id, OperationLog.action == "update_tea")
                .count()
            )
            assert log_count == 1
        finally:
            db.close()
    finally:
        admin.delete(f"/api/v1/favorites/{tea_id}")
        _cleanup_teas([tea_id])


def test_admin_tea_07_update_rejects_managed_fields_and_missing_tea():
    admin = _admin_client()
    tea = _create_tea(admin)
    tea_id = tea["id"]
    try:
        for overrides in (
            {"is_active": False},
            {"favorite_count": 9},
            {"id": 1},
            {"tips_history": "x"},
        ):
            body = (
                _payload(**overrides)
                if "tips_history" in overrides
                else _update_payload(**overrides)
            )
            resp = admin.put(f"/api/v1/admin/teas/{tea_id}", json=body)
            assert resp.status_code == 400, overrides
            assert resp.json()["code"] == 40000, overrides

        resp = admin.put("/api/v1/admin/teas/999999", json=_update_payload())
        assert resp.status_code == 404
        assert resp.json()["code"] == 40400
    finally:
        _cleanup_teas([tea_id])


# ===== TEA / 上下架联动 =====


def test_admin_tea_08_toggle_links_public_visibility_and_keeps_favorites():
    admin = _admin_client()
    marker = _uid()
    tea = _create_tea(admin, name=f"联动茶{marker}")
    tea_id = tea["id"]
    try:
        assert admin.post(f"/api/v1/favorites/{tea_id}").status_code == 200
        before_count = admin.get(f"/api/v1/teas/{tea_id}").json()["data"]["favorite_count"]

        resp = admin.patch(f"/api/v1/admin/teas/{tea_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] is False

        # 前台列表/搜索/热门/随机/详情全部不可见
        public = client.get("/api/v1/teas", params={"keyword": marker}).json()["data"]
        assert public["items"] == []
        hot_ids = {
            i["id"] for i in client.get("/api/v1/teas/hot", params={"limit": 20}).json()["data"]
        }
        assert tea_id not in hot_ids
        for _ in range(3):
            random_data = client.get("/api/v1/teas/random").json()["data"]
            assert random_data is None or random_data["id"] != tea_id
        resp = client.get(f"/api/v1/teas/{tea_id}")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401

        # 已收藏条目保留并灰显，收藏计数不被上下架改变
        default_list = admin.get("/api/v1/lists").json()["data"][0]["id"]
        my_list = admin.get(f"/api/v1/lists/{default_list}").json()["data"]
        item = next(i for i in my_list["items"] if i["tea_id"] == tea_id)
        assert item["is_available"] is False
        detail = admin.get(f"/api/v1/admin/teas/{tea_id}").json()["data"]
        assert detail["favorite_count"] == before_count
        assert detail["is_active"] is False

        # 重新上架 → 前台恢复
        assert (
            admin.patch(f"/api/v1/admin/teas/{tea_id}/toggle").json()["data"]["is_active"] is True
        )
        assert client.get(f"/api/v1/teas/{tea_id}").status_code == 200

        db = SessionLocal()
        try:
            logs = (
                db.query(OperationLog)
                .filter(OperationLog.target_id == tea_id, OperationLog.action == "toggle_tea")
                .all()
            )
            assert len(logs) == 2
        finally:
            db.close()
    finally:
        admin.delete(f"/api/v1/favorites/{tea_id}")
        _cleanup_teas([tea_id])


# ===== TIPS =====


def test_admin_tips_01_omitted_keeps_null_clears():
    admin = _admin_client()
    tea = _create_tea(admin)
    tea_id = tea["id"]
    try:
        resp = admin.put(
            "/api/v1/admin/teas/{}/tips".format(tea_id),
            json={"tips_misconception": None},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tips_history"] == "测试历史"
        assert data["tips_suitable"] == "测试人群"
        assert data["tips_misconception"] is None
        assert data["tips_official_note"] == "测试笔记"

        resp = admin.put(
            "/api/v1/admin/teas/{}/tips".format(tea_id),
            json={"tips_history": "   "},
        )
        data = resp.json()["data"]
        assert data["tips_history"] is None
        assert data["tips_suitable"] == "测试人群"

        # 空对象：全部保持原值
        data = admin.put(f"/api/v1/admin/teas/{tea_id}/tips", json={}).json()["data"]
        assert data["tips_suitable"] == "测试人群"
        assert data["tips_misconception"] is None

        db = SessionLocal()
        try:
            tips = db.query(TeaTips).filter(TeaTips.tea_id == tea_id).first()
            assert tips.history is None and tips.misconception is None
            assert tips.suitable == "测试人群"
        finally:
            db.close()
    finally:
        _cleanup_teas([tea_id])


def test_admin_tips_02_create_when_missing_and_reject_unknown_fields():
    admin = _admin_client()
    tea = _create_tea(
        admin,
        tips_history=None,
        tips_suitable=None,
        tips_misconception=None,
        tips_official_note=None,
    )
    tea_id = tea["id"]
    try:
        data = admin.put(
            f"/api/v1/admin/teas/{tea_id}/tips", json={"tips_suitable": "新人群"}
        ).json()["data"]
        assert data["tips_suitable"] == "新人群"
        assert data["tips_history"] is None

        resp = admin.put(f"/api/v1/admin/teas/{tea_id}/tips", json={"tips_unknown": "x"})
        assert resp.status_code == 400
        assert resp.json()["code"] == 40000

        resp = admin.put("/api/v1/admin/teas/999999/tips", json={"tips_history": "x"})
        assert resp.status_code == 404
        assert resp.json()["code"] == 40400
    finally:
        _cleanup_teas([tea_id])


# ===== STATS =====


def test_admin_stats_counts_and_fixed_distribution():
    admin = _admin_client()
    before = admin.get("/api/v1/admin/stats").json()["data"]
    tea = _create_tea(admin)
    tea_id = tea["id"]
    try:
        after_create = admin.get("/api/v1/admin/stats").json()["data"]
        assert after_create["total_count"] == before["total_count"] + 1
        assert after_create["active_count"] == before["active_count"] + 1
        assert after_create["inactive_count"] == before["inactive_count"]

        admin.patch(f"/api/v1/admin/teas/{tea_id}/toggle")
        after_toggle = admin.get("/api/v1/admin/stats").json()["data"]
        assert after_toggle["total_count"] == before["total_count"] + 1
        assert after_toggle["active_count"] == before["active_count"]
        assert after_toggle["inactive_count"] == before["inactive_count"] + 1
        assert (
            after_toggle["active_count"] + after_toggle["inactive_count"]
            == after_toggle["total_count"]
        )
        assert [c["category"] for c in after_toggle["category_distribution"]] == [
            "green",
            "white",
            "yellow",
            "red",
            "oolong",
            "dark",
            "reprocessed",
        ]
        assert (
            sum(c["count"] for c in after_toggle["category_distribution"])
            == after_toggle["total_count"]
        )
    finally:
        _cleanup_teas([tea_id])


# ===== UPLOAD =====


def test_admin_upload_01_supports_jpeg_png_webp_with_uuid_filename():
    admin = _admin_client()
    log_id = _max_log_id()
    urls = []
    try:
        for filename, content, content_type, ext in (
            ("photo.jpg", JPEG_BYTES, "image/jpeg", "jpg"),
            ("photo.png", PNG_BYTES, "image/png", "png"),
            ("photo.webp", WEBP_BYTES, "image/webp", "webp"),
        ):
            resp = admin.post(
                "/api/v1/admin/upload", files={"file": (filename, content, content_type)}
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()["data"]
            assert data["content_type"] == content_type
            assert data["size"] == len(content)
            assert data["original_filename"] == filename
            assert re.match(rf"^/uploads/\d{{4}}/\d{{2}}/[0-9a-f]{{32}}\.{ext}$", data["url"]), (
                data["url"]
            )
            urls.append(data["url"])

            saved = Path(settings.UPLOAD_DIR) / data["url"].removeprefix("/uploads/")
            assert saved.is_file()
            assert client.get(data["url"]).status_code == 200

        db = SessionLocal()
        try:
            logs = (
                db.query(OperationLog)
                .filter(OperationLog.id > log_id, OperationLog.action == "upload_image")
                .all()
            )
            assert len(logs) == 3
            assert all(log.target_id is None for log in logs)
        finally:
            db.close()
    finally:
        for url in urls:
            _remove_upload(url)
        _cleanup_logs_after(log_id)


def test_admin_upload_02_oversize_returns_413():
    admin = _admin_client()
    log_id = _max_log_id()
    try:
        resp = admin.post(
            "/api/v1/admin/upload",
            files={"file": ("big.jpg", b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024), "image/jpeg")},
        )
        assert resp.status_code == 413
        assert resp.json()["code"] == 41300
        assert resp.json()["data"] is None

        db = SessionLocal()
        try:
            assert (
                db.query(OperationLog)
                .filter(OperationLog.id > log_id, OperationLog.action == "upload_image")
                .count()
                == 0
            )
        finally:
            db.close()
    finally:
        _cleanup_logs_after(log_id)


def test_admin_upload_03_rejects_non_image_by_magic_and_empty_file():
    admin = _admin_client()
    log_id = _max_log_id()
    cases = [
        ("fake.jpg", b"plain text", "image/jpeg"),
        ("fake.png", b"GIF89a" + b"x" * 20, "image/png"),
        ("fake.webp", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "image/webp"),
        ("fake.jpg", b"MZ" + b"x" * 20, "image/jpeg"),
    ]
    try:
        for filename, content, content_type in cases:
            resp = admin.post(
                "/api/v1/admin/upload", files={"file": (filename, content, content_type)}
            )
            assert resp.status_code == 415, filename
            assert resp.json()["code"] == 41500, filename

        resp = admin.post("/api/v1/admin/upload", files={"file": ("empty.jpg", b"", "image/jpeg")})
        assert resp.status_code == 400
        assert resp.json()["code"] == 40000

        resp = admin.post("/api/v1/admin/upload")
        assert resp.status_code == 400
        assert resp.json()["code"] == 40000

        db = SessionLocal()
        try:
            assert (
                db.query(OperationLog)
                .filter(OperationLog.id > log_id, OperationLog.action == "upload_image")
                .count()
                == 0
            )
        finally:
            db.close()
    finally:
        _cleanup_logs_after(log_id)


def test_admin_upload_04_path_traversal_attempt_is_stored_safely():
    admin = _admin_client()
    log_id = _max_log_id()
    url = None
    try:
        resp = admin.post(
            "/api/v1/admin/upload",
            files={"file": ("../../evil.jpg", JPEG_BYTES, "image/jpeg")},
        )
        assert resp.status_code == 200
        url = resp.json()["data"]["url"]
        assert ".." not in url
        saved = (Path(settings.UPLOAD_DIR) / url.removeprefix("/uploads/")).resolve()
        assert (Path(settings.UPLOAD_DIR).resolve() / "..") not in saved.parents
        assert saved.is_file()
    finally:
        if url:
            _remove_upload(url)
        _cleanup_logs_after(log_id)


# ===== OPERATION LOGS / 操作日志查询（API_CONTRACT §4.6.12） =====


def test_admin_oplog_01_list_returns_pagination_and_fields():
    admin = _admin_client()
    tea = _create_tea(admin)
    try:
        resp = admin.get("/api/v1/admin/operation-logs", params={"page": 1, "page_size": 5})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0

        data = body["data"]
        assert set(data) == {"items", "total", "page", "page_size"}
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert data["total"] >= 1
        assert len(data["items"]) <= 5

        item = data["items"][0]
        assert set(item) == {
            "id",
            "admin_id",
            "admin_username",
            "action",
            "target_type",
            "target_id",
            "detail",
            "ip_address",
            "created_at",
        }
        assert item["created_at"].endswith("Z")
        assert data["items"] == sorted(
            data["items"], key=lambda row: (row["created_at"], row["id"]), reverse=True
        )
    finally:
        _cleanup_teas([tea["id"]])


def test_admin_oplog_02_page_and_page_size_are_clamped():
    admin = _admin_client()
    resp = admin.get("/api/v1/admin/operation-logs", params={"page": 0, "page_size": 999})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 50


def test_admin_oplog_03_normal_user_gets_403():
    username = f"oplog{_uid()}"
    try:
        register = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "tea2026"},
        )
        assert register.status_code == 200
        normal = TestClient(app)
        normal.cookies = register.cookies

        resp = normal.get("/api/v1/admin/operation-logs")
        assert resp.status_code == 403
        assert resp.json()["code"] == 40300
        assert resp.json()["data"] is None
    finally:
        _cleanup_user(username)


def test_admin_oplog_04_guest_gets_401():
    resp = client.get("/api/v1/admin/operation-logs")
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100
    assert resp.json()["data"] is None


def test_admin_oplog_05_action_filter_and_invalid_date():
    admin = _admin_client()
    tea = _create_tea(admin)
    try:
        resp = admin.get(
            "/api/v1/admin/operation-logs",
            params={"action": "create_tea", "target_type": "tea", "page_size": 50},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert all(item["action"] == "create_tea" for item in data["items"])
        assert all(item["target_type"] == "tea" for item in data["items"])

        matched = [item for item in data["items"] if item["target_id"] == tea["id"]]
        assert matched
        assert matched[0]["admin_id"] == admin.get("/api/v1/auth/me").json()["data"]["id"]
        assert matched[0]["admin_username"] == settings.ADMIN_USERNAME

        bad = admin.get("/api/v1/admin/operation-logs", params={"start_date": "2026/11/11"})
        assert bad.status_code == 400
        assert bad.json()["code"] == 40000

        reversed_range = admin.get(
            "/api/v1/admin/operation-logs",
            params={"start_date": "2026-11-12", "end_date": "2026-11-11"},
        )
        assert reversed_range.status_code == 400
        assert reversed_range.json()["code"] == 40000
    finally:
        _cleanup_teas([tea["id"]])
