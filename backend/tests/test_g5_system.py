"""阶段 5（G5）系统测试补充用例。

仅补齐 TEST_PLAN 中现有测试未覆盖的细分断言，函数名直接携带 TC 编号，
便于测试报告逐条回溯。断言同时检查 HTTP 状态码、业务 code 与数据库状态。
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import text as sa_text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import verify_session_token
from app.main import app
from app.models.collection_list import CollectionList
from app.models.favorite import FavoriteItem, ShareToken
from app.models.operation_log import OperationLog
from app.models.tea import Tea
from app.models.user import User
from app.repositories import user_repo

# ===== 通用工具 =====


def _uid() -> str:
    return str(int(time.time() * 1000) % 100000000)


def _register(username: str, password: str = "tea2026") -> tuple[TestClient, str]:
    client = TestClient(app)
    resp = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return client, resp.cookies["tea_session"]


def _login(username: str, password: str = "tea2026") -> TestClient:
    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return client


def _admin_client() -> TestClient:
    return _login(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)


def _create_tea(**overrides) -> int:
    db = SessionLocal()
    try:
        data = {
            "name": f"G5测试茶{_uid()}",
            "category": "green",
            "origin": "浙江 测试产区",
            "season": "春茶",
            "shape_desc": "条索紧结",
            "soup_desc": "汤色清亮",
            "aroma_desc": "清香",
            "taste_desc": "回甘",
            "is_active": True,
            "favorite_count": 0,
        }
        data.update(overrides)
        tea = Tea(**data)
        db.add(tea)
        db.commit()
        db.refresh(tea)
        return tea.id
    finally:
        db.close()


def _delete_tea(tea_id: int) -> None:
    db = SessionLocal()
    try:
        db.query(FavoriteItem).filter(FavoriteItem.tea_id == tea_id).delete(
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
            db.query(FavoriteItem).filter(FavoriteItem.user_id == user.id).delete(
                synchronize_session=False
            )
            list_ids = [
                row.id for row in db.query(CollectionList).filter(CollectionList.user_id == user.id)
            ]
            if list_ids:
                db.query(ShareToken).filter(ShareToken.list_id.in_(list_ids)).delete(
                    synchronize_session=False
                )
                db.query(CollectionList).filter(CollectionList.id.in_(list_ids)).delete(
                    synchronize_session=False
                )
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _payload(**overrides) -> dict:
    data = {
        "name": f"G5管理茶{_uid()}",
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
    }
    data.update(overrides)
    return data


def _max_log_id() -> int:
    db = SessionLocal()
    try:
        latest = db.query(OperationLog).order_by(OperationLog.id.desc()).first()
        return latest.id if latest else 0
    finally:
        db.close()


def _db_counts() -> tuple[int, int, int]:
    db = SessionLocal()
    try:
        return (
            db.query(FavoriteItem).count(),
            db.query(CollectionList).count(),
            db.query(ShareToken).count(),
        )
    finally:
        db.close()


# ===== TC-AUTH-03：用户名/密码边界 =====


def test_tc_auth_03_username_password_boundaries():
    suffix = _uid()
    created: list[str] = []
    cases = [
        ("ab", "Tea123", 400, 40000),
        (f"u3{suffix}"[:3], "Tea123", 200, 0),
        (("u20" + suffix).ljust(20, "x")[:20], "Tea123", 200, 0),
        (("u21" + suffix).ljust(21, "x")[:21], "Tea123", 400, 40000),
        (f"p5{suffix}"[:20], "12345", 400, 40000),
        (f"p6{suffix}"[:20], "123456", 200, 0),
        (f"p64{suffix}"[:20], "p" * 64, 200, 0),
        (f"p65{suffix}"[:20], "p" * 65, 400, 40000),
        (f"p1000{suffix}"[:20], "p" * 1000, 400, 40000),
        ("  ab  ", "Tea123", 400, 40000),
    ]
    try:
        for username, password, expected_http, expected_code in cases:
            resp = TestClient(app).post(
                "/api/v1/auth/register",
                json={"username": username, "password": password},
            )
            assert resp.status_code == expected_http, (username, resp.text)
            assert resp.json()["code"] == expected_code, username
            if expected_http == 200:
                created.append(username)
        db = SessionLocal()
        try:
            assert db.query(User).filter(User.username.in_(created)).count() == len(created)
        finally:
            db.close()
    finally:
        for name in created:
            _cleanup_user(name)


# ===== TC-AUTH-02：昵称唯一性大小写不敏感 =====


def test_tc_auth_02_duplicate_username_is_case_insensitive():
    base = "Case" + _uid()
    variants = [base, base.upper(), base.lower()]
    client = TestClient(app)
    db = SessionLocal()
    try:
        before = db.query(User).count()
    finally:
        db.close()
    try:
        first = client.post(
            "/api/v1/auth/register", json={"username": variants[0], "password": "Tea1234"}
        )
        assert first.status_code == 200 and first.json()["code"] == 0
        db = SessionLocal()
        try:
            assert db.query(User).count() == before + 1
        finally:
            db.close()
        for variant in variants[1:]:
            resp = TestClient(app).post(
                "/api/v1/auth/register",
                json={"username": variant, "password": "Tea1234"},
            )
            assert resp.status_code == 409, variant
            assert resp.json()["code"] == 40910, variant
            assert resp.json()["data"] is None
        db = SessionLocal()
        try:
            assert db.query(User).count() == before + 1
        finally:
            db.close()
    finally:
        _cleanup_user(variants[0])


# ===== TC-AUTH-04：管理员与普通用户登录 / me =====


def test_tc_auth_04_admin_and_user_login_roles():
    admin = _login(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
    admin_me = admin.get("/api/v1/auth/me")
    assert admin_me.status_code == 200 and admin_me.json()["code"] == 0
    assert admin_me.json()["data"]["role"] == "admin"

    username = f"auth4{_uid()}"
    user_client, _ = _register(username)
    try:
        me = user_client.get("/api/v1/auth/me")
        assert me.status_code == 200 and me.json()["code"] == 0
        assert me.json()["data"]["role"] == "user"
        assert "password" not in me.text and "password_hash" not in me.text

        db = SessionLocal()
        try:
            user = user_repo.get_by_username(db, username)
            assert user is not None and user.role == "user"
        finally:
            db.close()
    finally:
        _cleanup_user(username)


# ===== TC-AUTH-05：登录失败消息一致、无 Cookie、等时 =====


def test_tc_auth_05_login_failure_is_uniform_and_timed():
    username = f"auth5{_uid()}"
    _register(username)
    try:
        ghost_times: list[float] = []
        wrong_times: list[float] = []
        ghost_body = None
        wrong_body = None
        for _ in range(5):
            start = time.perf_counter()
            ghost = TestClient(app).post(
                "/api/v1/auth/login",
                json={"username": "ghost_user_xyz", "password": "Any123"},
            )
            ghost_times.append(time.perf_counter() - start)
            ghost_body = ghost

        # S14：同一 IP 连续失败会触发锁定，先清空失败记录再测“密码错误”路径，
        # 保证本用例只验证 401 文案与等时性，不混入 429 锁定行为。
        db = SessionLocal()
        try:
            db.execute(sa_text("DELETE FROM login_attempts"))
            db.commit()
        finally:
            db.close()

        for _ in range(5):
            start = time.perf_counter()
            wrong = TestClient(app).post(
                "/api/v1/auth/login",
                json={"username": username, "password": "WrongPwd"},
            )
            wrong_times.append(time.perf_counter() - start)
            wrong_body = wrong

        assert ghost_body.status_code == 401 and wrong_body.status_code == 401
        assert ghost_body.json()["code"] == 40110 and wrong_body.json()["code"] == 40110
        assert ghost_body.json()["message"] == wrong_body.json()["message"]
        assert "tea_session" not in ghost_body.cookies
        assert "tea_session" not in wrong_body.cookies
        median_gap = abs(sorted(ghost_times)[2] - sorted(wrong_times)[2])
        assert median_gap <= 0.100, median_gap
    finally:
        _cleanup_user(username)


# ===== TC-AUTH-06：全部受保护端点未登录 =====


def test_tc_auth_06_all_protected_endpoints_require_session():
    before = _db_counts()
    client = TestClient(app)
    requests = [
        ("get", "/api/v1/auth/me", {}),
        ("post", "/api/v1/favorites/1", {}),
        ("get", "/api/v1/lists", {}),
        ("post", "/api/v1/lists", {"json": {"title": "未登录标题"}}),
        ("get", "/api/v1/lists/1", {}),
        ("put", "/api/v1/lists/1", {"json": {"title": "未登录标题"}}),
        ("delete", "/api/v1/lists/1", {}),
        ("put", "/api/v1/lists/1/notes/1", {"json": {"content": "未登录笔记"}}),
        ("post", "/api/v1/shares/generate", {}),
        ("post", "/api/v1/shares/ZZZZZZZZ/copy", {}),
        ("get", "/api/v1/admin/stats", {}),
    ]
    for method, path, kwargs in requests:
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code == 401, path
        assert resp.json()["code"] == 40100, path
        assert resp.json()["data"] is None, path
    assert _db_counts() == before


# ===== TC-AUTH-07：篡改 / 异密钥 / 过期会话 =====


def test_tc_auth_07_tampered_foreign_and_expired_session():
    username = f"auth7{_uid()}"
    client, token = _register(username)
    db = SessionLocal()
    try:
        uid = user_repo.get_by_username(db, username).id
    finally:
        db.close()
    try:
        # 篡改最后一个字符。itsdangerous 签名末位 base64 字符含 2 个未使用位，
        # A/B/C/D 之间互换可能解码为相同字节；翻转高位确保解码结果必然不同。
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        tampered = token[:-1] + alphabet[alphabet.index(token[-1]) ^ 32]
        c1 = TestClient(app)
        c1.cookies.set("tea_session", tampered)
        r1 = c1.get("/api/v1/auth/me")
        assert r1.status_code == 401 and r1.json()["code"] == 40100

        # 另一 SECRET_KEY 签发
        foreign = URLSafeTimedSerializer("foreign-secret-key").dumps({"uid": uid})
        c2 = TestClient(app)
        c2.cookies.set("tea_session", foreign)
        r2 = c2.get("/api/v1/auth/me")
        assert r2.status_code == 401 and r2.json()["code"] == 40100

        # 过期分支：0 与负数都必须立即过期，不能回落默认 30 天
        assert verify_session_token(token, max_age_days=0) is None
        assert verify_session_token(token, max_age_days=-1) is None
        assert verify_session_token(token) == uid
    finally:
        _cleanup_user(username)


# ===== TC-AUTH-08：登出 Cookie 属性与旧 Cookie 重放（登出吊销） =====


def test_tc_auth_08_logout_clears_cookie_and_replay_revoked():
    username = f"auth8{_uid()}"
    client, token = _register(username)
    try:
        login_resp = client.post(
            "/api/v1/auth/login", json={"username": username, "password": "tea2026"}
        )
        cookie = login_resp.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie
        assert "Max-Age=2592000" in cookie and "Path=/" in cookie

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 200
        assert logout.json() == {"code": 0, "message": "ok", "data": None}
        cleared = logout.headers.get("set-cookie", "")
        assert "Max-Age=0" in cleared and "Path=/" in cleared
        assert "HttpOnly" in cleared and "SameSite=lax" in cleared

        assert client.get("/api/v1/auth/me").status_code == 401

        # 登出吊销（S-10）：旧 Cookie 重放必须 401，且 session_version 已递增
        replay = TestClient(app)
        replay.cookies.set("tea_session", token)
        replay_resp = replay.get("/api/v1/auth/me")
        assert replay_resp.status_code == 401
        assert replay_resp.json()["code"] == 40100

        db = SessionLocal()
        try:
            user = user_repo.get_by_username(db, username)
            assert user is not None and user.session_version == 1
        finally:
            db.close()
    finally:
        _cleanup_user(username)


# ===== TC-AUTH-09：响应与日志不含密码明文 =====


def test_tc_auth_09_no_password_in_response_or_logs(caplog):
    username = f"auth9{_uid()}"
    password = "SecretPass2026"
    with caplog.at_level(logging.INFO):
        client, token = _register(username, password)
        try:
            assert (
                client.post(
                    "/api/v1/auth/login", json={"username": username, "password": password}
                ).status_code
                == 200
            )
            me = client.get("/api/v1/auth/me")
            assert me.status_code == 200
            assert password not in me.text
            assert token not in caplog.text
            assert password not in caplog.text
            keys: list[str] = []

            def collect(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        keys.append(k)
                        collect(v)
                elif isinstance(obj, list):
                    for v in obj:
                        collect(v)

            collect(me.json())
            assert "password" not in keys and "password_hash" not in keys
        finally:
            _cleanup_user(username)


# ===== TC-TEA-02 / 03 / 04：管理员茶品校验 =====


def test_tc_tea_02_valid_fermentation_and_unknown_field_rejected():
    admin = _admin_client()
    created: list[int] = []
    try:
        ok = admin.post("/api/v1/admin/teas", json=_payload(fermentation="后发酵"))
        assert ok.status_code == 200 and ok.json()["code"] == 0
        created.append(ok.json()["data"]["id"])

        extra = admin.post("/api/v1/admin/teas", json=_payload(unknown_field="x"))
        assert extra.status_code == 400 and extra.json()["code"] == 40000

        for bad in (
            {k: v for k, v in _payload().items() if k != "name"},
            _payload(category="black"),
            _payload(season="夏季"),
        ):
            resp = admin.post("/api/v1/admin/teas", json=bad)
            assert resp.status_code == 400 and resp.json()["code"] == 40000
    finally:
        for tea_id in created:
            _delete_tea(tea_id)


def test_tc_tea_03_numeric_boundaries():
    admin = _admin_client()
    created: list[int] = []
    try:
        for overrides, expect_ok in (
            ({"water_temp": 69.9}, False),
            ({"water_temp": 70.0}, True),
            ({"water_temp": 100.0}, True),
            ({"water_temp": 100.1}, False),
            ({"tea_amount": 0}, False),
            ({"tea_amount": 999.9}, True),
            ({"tea_amount": 1000}, False),
            ({"brew_time": -1}, False),
            ({"water_temp": 85.55}, False),
        ):
            resp = admin.post("/api/v1/admin/teas", json=_payload(**overrides))
            if expect_ok:
                assert resp.status_code == 200 and resp.json()["code"] == 0, overrides
                created.append(resp.json()["data"]["id"])
            else:
                assert resp.status_code == 400 and resp.json()["code"] == 40000, overrides
    finally:
        for tea_id in created:
            _delete_tea(tea_id)


def test_tc_tea_04_field_length_limits():
    admin = _admin_client()
    db = SessionLocal()
    try:
        before = db.query(Tea).count()
    finally:
        db.close()
    cases = [
        {"name": "茶" * 101},
        {"origin": "浙" * 201},
        {"price_range": "p" * 33},
        {"representative_variety": "v" * 101},
        {"main_image_url": "/uploads/" + "a" * 492},
    ]
    for overrides in cases:
        resp = admin.post("/api/v1/admin/teas", json=_payload(**overrides))
        assert resp.status_code == 400, overrides
        assert resp.json()["code"] == 40000, overrides
    db = SessionLocal()
    try:
        assert db.query(Tea).count() == before
    finally:
        db.close()


# ===== TC-LIST-01 / 05 / 06 / 08 / 09 =====


def test_tc_list_01_pagination_with_13_plus_active_teas():
    created = [_create_tea(name=f"分页茶{_uid()}{i}") for i in range(7)]
    try:
        page1 = TestClient(app).get("/api/v1/teas")
        assert page1.status_code == 200 and page1.json()["code"] == 0
        data1 = page1.json()["data"]
        assert data1["page"] == 1 and data1["page_size"] == 12
        assert data1["total"] >= 13 and len(data1["items"]) == 12

        page2 = TestClient(app).get("/api/v1/teas", params={"page": 2}).json()["data"]
        assert len(page2["items"]) == data1["total"] - 12
        ids1 = [i["id"] for i in data1["items"]]
        ids2 = [i["id"] for i in page2["items"]]
        assert len(set(ids1 + ids2)) == data1["total"]
        assert ids1[:7] == list(reversed(created))

        all_items = (
            TestClient(app).get("/api/v1/teas", params={"page_size": 50}).json()["data"]["items"]
        )
        all_ids = [i["id"] for i in all_items]
        assert set(all_ids) == set(ids1 + ids2)
    finally:
        for tea_id in created:
            _delete_tea(tea_id)


def test_tc_list_05_wildcards_are_escaped():
    total = TestClient(app).get("/api/v1/teas").json()["data"]["total"]
    for keyword in ("%", "_", "\\"):
        data = TestClient(app).get("/api/v1/teas", params={"keyword": keyword}).json()["data"]
        assert data["total"] < total, keyword

    admin = _admin_client()
    admin_total = admin.get("/api/v1/admin/teas").json()["data"]["total"]
    for keyword in ("%", "_"):
        admin_data = admin.get("/api/v1/admin/teas", params={"keyword": keyword}).json()["data"]
        assert admin_data["total"] < admin_total, keyword


def test_tc_list_06_keyword_length_boundaries():
    client = TestClient(app)
    ok = client.get("/api/v1/teas", params={"keyword": "茶" * 50})
    assert ok.status_code == 200 and ok.json()["code"] == 0
    for keyword in ("茶" * 51, "x" * 1000):
        resp = client.get("/api/v1/teas", params={"keyword": keyword})
        assert resp.status_code == 400 and resp.json()["code"] == 40000


def test_tc_list_08_favorite_sort_secondary_id_desc():
    same_time = datetime(2026, 1, 1, 8, 0, 0)
    first = _create_tea(name=f"同分茶A{_uid()}", favorite_count=50, created_at=same_time)
    second = _create_tea(name=f"同分茶B{_uid()}", favorite_count=50, created_at=same_time)
    extras = [_create_tea(name=f"排序茶{_uid()}{i}", favorite_count=i) for i in range(5)]
    try:
        all_items = (
            TestClient(app)
            .get("/api/v1/teas", params={"sort": "favorite", "page_size": 50})
            .json()["data"]["items"]
        )
        assert all_items[0]["favorite_count"] >= all_items[-1]["favorite_count"]
        ids = [i["id"] for i in all_items]
        assert ids.index(second) < ids.index(first)

        total = TestClient(app).get("/api/v1/teas").json()["data"]["total"]
        assert total >= 13
        page1 = (
            TestClient(app)
            .get("/api/v1/teas", params={"sort": "favorite", "page": 1})
            .json()["data"]
        )
        page2 = (
            TestClient(app)
            .get("/api/v1/teas", params={"sort": "favorite", "page": 2})
            .json()["data"]
        )
        ids1 = [i["id"] for i in page1["items"]]
        ids2 = [i["id"] for i in page2["items"]]
        assert len(ids1) == 12
        assert len(set(ids1 + ids2)) == total
        assert set(ids1 + ids2) == set(ids)
    finally:
        for tea_id in [first, second] + extras:
            _delete_tea(tea_id)


def test_tc_list_09_categories_origins_exclude_off_shelf_and_clamp():
    db = SessionLocal()
    try:
        yellow = db.query(Tea).filter(Tea.id == 3).first()
        was_active = yellow.is_active
        yellow.is_active = False
        db.commit()
    finally:
        db.close()
    try:
        categories = TestClient(app).get("/api/v1/teas/categories").json()["data"]
        yellow_row = next(c for c in categories if c["category"] == "yellow")
        assert yellow_row["count"] == 0
        assert [c["category"] for c in categories] == [
            "green",
            "white",
            "yellow",
            "red",
            "oolong",
            "dark",
            "reprocessed",
        ]

        origins = TestClient(app).get("/api/v1/teas/origins").json()["data"]
        assert "湖南" not in {o["origin"] for o in origins}

        hot_zero = TestClient(app).get("/api/v1/teas/hot", params={"limit": 0}).json()["data"]
        hot_max = TestClient(app).get("/api/v1/teas/hot", params={"limit": 21}).json()["data"]
        assert len(hot_zero) == 1
        assert len(hot_max) <= 20

        random_data = (
            TestClient(app).get("/api/v1/teas/random", params={"exclude_id": 1}).json()["data"]
        )
        assert random_data is None or random_data["id"] != 1
    finally:
        db = SessionLocal()
        try:
            db.query(Tea).filter(Tea.id == 3).update({"is_active": was_active})
            db.commit()
        finally:
            db.close()


# ===== TC-PERM-04：管理员角色实时读取 =====


def test_tc_perm_04_admin_role_is_read_live():
    admin = _admin_client()
    tea_id = _create_tea(name=f"角色茶{_uid()}")
    try:
        assert admin.post(f"/api/v1/favorites/{tea_id}").status_code == 200
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
            assert user.role == "admin"
            user.role = "user"
            db.commit()
        finally:
            db.close()

        assert admin.get("/api/v1/admin/stats").status_code == 403

        db = SessionLocal()
        try:
            db.query(User).filter(User.username == settings.ADMIN_USERNAME).update(
                {"role": "admin"}
            )
            db.commit()
        finally:
            db.close()
        stats = admin.get("/api/v1/admin/stats")
        assert stats.status_code == 200 and stats.json()["code"] == 0
        assert admin.get("/api/v1/auth/me").json()["data"]["role"] == "admin"
    finally:
        db = SessionLocal()
        try:
            db.query(User).filter(User.username == settings.ADMIN_USERNAME).update(
                {"role": "admin"}
            )
            db.commit()
        finally:
            db.close()
        _delete_tea(tea_id)


# ===== TC-PERM-01 / 02：拒绝时无任何副作用 =====


def test_tc_perm_01_02_admin_endpoints_have_no_side_effects():
    username = f"perm12{_uid()}"
    normal, _ = _register(username)
    upload_dir = Path(settings.UPLOAD_DIR)
    db = SessionLocal()
    try:
        teas_before = db.query(Tea).count()
        tea_one_active = db.query(Tea).filter(Tea.id == 1).first().is_active
    finally:
        db.close()
    logs_before = _max_log_id()
    files_before = sum(1 for p in upload_dir.rglob("*") if p.is_file())

    request_defs = [
        ("get", "/api/v1/admin/stats", {}),
        ("get", "/api/v1/admin/teas", {}),
        ("get", "/api/v1/admin/teas/1", {}),
        ("post", "/api/v1/admin/teas", {"json": _payload()}),
        ("put", "/api/v1/admin/teas/1", {"json": _payload()}),
        ("patch", "/api/v1/admin/teas/1/toggle", {}),
        ("put", "/api/v1/admin/teas/1/tips", {"json": {"tips_history": None}}),
        (
            "post",
            "/api/v1/admin/upload",
            {"files": {"file": ("x.jpg", b"\xff\xd8\xff\xe0" + b"0" * 100, "image/jpeg")}},
        ),
    ]
    try:
        for method, url, kwargs in request_defs:
            resp = getattr(normal, method)(url, **kwargs)
            assert resp.status_code == 403, url
            assert resp.json()["code"] == 40300, url
        guest = TestClient(app)
        for method, url, kwargs in request_defs:
            resp = getattr(guest, method)(url, **kwargs)
            assert resp.status_code == 401, url
            assert resp.json()["code"] == 40100, url

        db = SessionLocal()
        try:
            assert db.query(Tea).count() == teas_before
            assert db.query(Tea).filter(Tea.id == 1).first().is_active == tea_one_active
        finally:
            db.close()
        assert _max_log_id() == logs_before
        files_after = sum(1 for p in upload_dir.rglob("*") if p.is_file())
        assert files_after == files_before
    finally:
        _cleanup_user(username)


# ===== TC-SHARE-05 / 08 =====


def test_tc_share_05_public_fields_and_off_shelf_flag():
    username = f"share5{_uid()}"
    active_tea = _create_tea(name=f"公开茶A{_uid()}")
    off_tea = _create_tea(name=f"公开茶B{_uid()}")
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{active_tea}")
        client.post(f"/api/v1/favorites/{off_tea}")
        default_list = client.get("/api/v1/lists").json()["data"][0]["id"]
        client.put(f"/api/v1/lists/{default_list}/notes/{active_tea}", json={"content": "私有笔记"})
        db = SessionLocal()
        try:
            db.query(Tea).filter(Tea.id == off_tea).update({"is_active": False})
            db.commit()
        finally:
            db.close()
        token = client.post("/api/v1/shares/generate").json()["data"]["token"]

        guest = TestClient(app)
        body = guest.get(f"/api/v1/shares/{token}")
        assert body.status_code == 200 and body.json()["code"] == 0
        data = body.json()["data"]
        assert data["tea_count"] == 2 and data["revoked"] is False and data["is_owner"] is False
        assert "username" not in data and "user_id" not in data
        assert data["title"] == "我的收藏"
        expected_keys = {
            "tea_id",
            "name",
            "category",
            "origin",
            "season",
            "main_image_url",
            "favorite_count",
            "is_available",
        }
        for item in data["items"]:
            assert set(item.keys()) == expected_keys
            assert "tasting_note" not in item
        by_id = {item["tea_id"]: item for item in data["items"]}
        assert by_id[active_tea]["is_available"] is True
        assert by_id[off_tea]["is_available"] is False
    finally:
        _cleanup_user(username)
        _delete_tea(active_tea)
        _delete_tea(off_tea)


def test_tc_share_08_copy_added_skipped_total():
    owner_name = f"copy8a{_uid()}"
    copier_name = f"copy8c{_uid()}"
    teas = [_create_tea(name=f"复制茶{_uid()}{i}", favorite_count=i) for i in range(3)]
    off_tea = _create_tea(name=f"复制下架茶{_uid()}", favorite_count=100)
    owner, _ = _register(owner_name)
    copier, _ = _register(copier_name)
    try:
        for tea_id in teas + [off_tea]:
            assert owner.post(f"/api/v1/favorites/{tea_id}").status_code == 200
        db = SessionLocal()
        try:
            db.query(Tea).filter(Tea.id == off_tea).update({"is_active": False})
            db.commit()
        finally:
            db.close()
        token = owner.post("/api/v1/shares/generate").json()["data"]["token"]

        first = copier.post(f"/api/v1/shares/{token}/copy")
        assert first.status_code == 200 and first.json()["code"] == 0
        assert first.json()["data"] == {"added": 3, "skipped": 1, "total": 4}

        repeat = copier.post(f"/api/v1/shares/{token}/copy").json()["data"]
        assert repeat == {"added": 0, "skipped": 4, "total": 4}

        db = SessionLocal()
        try:
            copier_id = user_repo.get_by_username(db, copier_name).id
            for tea_id in teas:
                assert (
                    db.query(FavoriteItem)
                    .filter(FavoriteItem.user_id == copier_id, FavoriteItem.tea_id == tea_id)
                    .count()
                    == 1
                )
            assert (
                db.query(FavoriteItem)
                .filter(FavoriteItem.user_id == copier_id, FavoriteItem.tea_id == off_tea)
                .count()
                == 0
            )
            for index, tea_id in enumerate(teas):
                count = db.query(Tea).filter(Tea.id == tea_id).first().favorite_count
                assert int(count) == index + 2
            assert int(db.query(Tea).filter(Tea.id == off_tea).first().favorite_count) == 101
        finally:
            db.close()
    finally:
        _cleanup_user(owner_name)
        _cleanup_user(copier_name)
        for tea_id in teas + [off_tea]:
            _delete_tea(tea_id)


# ===== TC-DEF-02：超大请求体不得 500 =====


def test_tc_def_02_oversize_body_is_rejected_without_500():
    admin = _admin_client()
    db = SessionLocal()
    try:
        before = db.query(Tea).count()
    finally:
        db.close()

    # ① 超过应用层 6MB 上限：中间件直接 413，不进入 ORM
    huge = _payload()
    huge["shape_desc"] = "x" * (10 * 1024 * 1024)
    resp = admin.post("/api/v1/admin/teas", json=huge)
    assert resp.status_code == 413, resp.text[:160]
    assert resp.json()["code"] == 41300

    # ② 未超 6MB、但超过 TEXT 列容量：DataError 映射为 400，不得 500
    big = _payload(name=f"超长描述{_uid()}")
    big["shape_desc"] = "x" * 70000
    resp2 = admin.post("/api/v1/admin/teas", json=big)
    assert resp2.status_code == 400, resp2.text[:160]
    assert resp2.json()["code"] == 40000

    db = SessionLocal()
    try:
        assert db.query(Tea).count() == before
    finally:
        db.close()


# ===== TC-DEF-04：管理员密码轮换 =====


def _rotate_admin(password: str) -> subprocess.CompletedProcess:
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["NEW_ADMIN_PASSWORD"] = password
    env["ADMIN_USERNAME"] = settings.ADMIN_USERNAME
    return subprocess.run(
        [sys.executable, "-m", "app.scripts.rotate_admin_password"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_tc_def_04_admin_password_rotation():
    original = settings.ADMIN_PASSWORD
    assert original, "测试环境必须通过 .env 注入 ADMIN_PASSWORD"
    new_password = "Str0ng!Admin#2026"
    try:
        result = _rotate_admin(new_password)
        assert result.returncode == 0, result.stderr
        output = result.stdout + result.stderr
        assert new_password not in output

        old = TestClient(app).post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": original},
        )
        assert old.status_code == 401 and old.json()["code"] == 40110

        fresh = _login(settings.ADMIN_USERNAME, new_password)
        assert fresh.get("/api/v1/auth/me").json()["data"]["role"] == "admin"

        db = SessionLocal()
        try:
            admin = user_repo.get_by_username(db, settings.ADMIN_USERNAME)
            assert admin.password_hash.startswith("$2b$10$")
            assert admin.password_hash != original
        finally:
            db.close()

        backend_dir = Path(__file__).resolve().parents[1]
        assert "admin123" not in (backend_dir / "app/core/config.py").read_text("utf-8")
        assert "admin123" not in (backend_dir / ".env.example").read_text("utf-8")
    finally:
        restored = _rotate_admin(original)
        assert restored.returncode == 0, restored.stderr


# ===== TC-E2E-01：MVP 端到端闭环 =====


def test_tc_e2e_mvp_closure():
    owner_name = f"e2ea{_uid()}"
    copier_name = f"e2eb{_uid()}"
    tea_id = _create_tea(name=f"闭环茶{_uid()}", favorite_count=0)
    owner, owner_token = _register(owner_name)
    try:
        # 1 游客浏览
        guest = TestClient(app)
        assert guest.get("/api/v1/teas").json()["code"] == 0
        assert guest.get("/api/v1/teas/1").json()["code"] == 0
        assert guest.get("/api/v1/teas/categories").json()["code"] == 0

        # 2 注册成功（_register）
        assert owner.get("/api/v1/auth/me").json()["data"]["username"] == owner_name

        # 3 收藏
        fav = owner.post(f"/api/v1/favorites/{tea_id}")
        assert fav.status_code == 200 and fav.json()["data"]["is_favorited"] is True

        # 4 写笔记
        default_list = owner.get("/api/v1/lists").json()["data"][0]["id"]
        note = owner.put(
            f"/api/v1/lists/{default_list}/notes/{tea_id}", json={"content": "闭环笔记"}
        )
        assert note.status_code == 200 and note.json()["data"]["tasting_note"] == "闭环笔记"

        # 5 生成分享
        share = owner.post("/api/v1/shares/generate").json()["data"]
        assert share["is_new"] is True and re.match(r"^[A-Za-z0-9_-]{8}$", share["token"])
        token = share["token"]

        # 6 登出
        assert owner.post("/api/v1/auth/logout").status_code == 200

        # 7 游客打开分享链接
        view = guest.get(f"/api/v1/shares/{token}")
        assert view.status_code == 200 and view.json()["data"]["tea_count"] == 1
        assert "tasting_note" not in view.json()["data"]["items"][0]

        # 8 另一用户登录并一键收藏
        copier, _ = _register(copier_name)
        copied = copier.post(f"/api/v1/shares/{token}/copy")
        assert copied.status_code == 200
        assert copied.json()["data"]["added"] == 1

        db = SessionLocal()
        try:
            owner_id = user_repo.get_by_username(db, owner_name).id
            row = (
                db.query(FavoriteItem)
                .filter(FavoriteItem.user_id == owner_id, FavoriteItem.tea_id == tea_id)
                .first()
            )
            assert row is not None and row.tasting_note == "闭环笔记"
            assert (
                db.query(FavoriteItem)
                .filter(
                    FavoriteItem.user_id == user_repo.get_by_username(db, copier_name).id,
                    FavoriteItem.tea_id == tea_id,
                )
                .count()
                == 1
            )
            assert int(db.query(Tea).filter(Tea.id == tea_id).first().favorite_count) == 2
        finally:
            db.close()
    finally:
        _cleanup_user(owner_name)
        _cleanup_user(copier_name)
        _delete_tea(tea_id)
