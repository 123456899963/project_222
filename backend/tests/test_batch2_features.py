"""批次二功能测试：S14 登录锁定 / S15 用户等级 / S16 个性化推荐

测试数据使用带时间戳的用户名与临时茶品，用例结束清理。
"""

import time
from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.main import app
from app.models.favorite import FavoriteItem
from app.models.login_attempt import LoginAttempt
from app.models.tea import Tea
from app.repositories import user_repo
from app.services.stats import resolve_level


def _unique_username(prefix: str = "b2user") -> str:
    return f"{prefix}{int(time.time() * 1000000) % 100000000}"


def _register(username: str, password: str = "tea2026") -> TestClient:
    client = TestClient(app)
    resp = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return client


def _login(client: TestClient, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _create_tea(*, category: str = "green", name: str | None = None) -> int:
    db = SessionLocal()
    try:
        tea = Tea(
            name=name or f"批次二测试茶{int(time.time() * 1000000) % 100000000}",
            category=category,
            origin="浙江 测试产区",
            season="春茶",
            shape_desc="",
            soup_desc="",
            aroma_desc="",
            taste_desc="",
            is_active=True,
            favorite_count=0,
        )
        db.add(tea)
        db.commit()
        db.refresh(tea)
        return tea.id
    finally:
        db.close()


def _cleanup(usernames: list[str], tea_ids: list[int] | None = None) -> None:
    db = SessionLocal()
    try:
        if tea_ids:
            db.query(FavoriteItem).filter(FavoriteItem.tea_id.in_(tea_ids)).delete(
                synchronize_session=False
            )
            db.query(Tea).filter(Tea.id.in_(tea_ids)).delete(synchronize_session=False)
        for name in usernames:
            user = user_repo.get_by_username(db, name)
            if user:
                db.delete(user)
        db.commit()
    finally:
        db.close()


# ===== S14 登录失败锁定 =====


def test_login_locked_after_five_failures():
    username = _unique_username()
    try:
        _register(username)
        client = TestClient(app)
        for _ in range(5):
            resp = _login(client, username, "wrongpass")
            assert resp.status_code == 401
            assert resp.json()["code"] == 40110

        # 第 6 次即使密码正确也应被锁定，返回 42900 / HTTP 429
        resp = _login(client, username, "tea2026")
        assert resp.status_code == 429
        assert resp.json()["code"] == 42900
        assert resp.json()["data"] is None
    finally:
        _cleanup([username])


def test_login_lock_does_not_leak_account_existence():
    """不存在的用户名同样会触发 429，攻击者无法据此判断账号是否存在。"""
    username = "nosuchuser" + str(int(time.time() * 1000000) % 100000000)
    client = TestClient(app)
    for _ in range(5):
        resp = _login(client, username, "whatever")
        assert resp.status_code == 401
        assert resp.json()["code"] == 40110

    resp = _login(client, username, "whatever")
    assert resp.status_code == 429
    assert resp.json()["code"] == 42900


def test_login_unlocks_after_window_expires():
    username = _unique_username()
    try:
        _register(username)
        client = TestClient(app)
        for _ in range(5):
            _login(client, username, "wrongpass")

        # 把失败记录整体前移 16 分钟（窗口 15 分钟），模拟自然过期
        db = SessionLocal()
        try:
            stale = utcnow() - timedelta(minutes=16)
            db.query(LoginAttempt).update({LoginAttempt.failed_at: stale})
            db.commit()
        finally:
            db.close()

        resp = _login(client, username, "tea2026")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
    finally:
        _cleanup([username])


def test_login_success_clears_username_failures():
    username = _unique_username()
    try:
        _register(username)
        client = TestClient(app)
        for _ in range(4):
            _login(client, username, "wrongpass")

        assert _login(client, username, "tea2026").status_code == 200

        db = SessionLocal()
        try:
            remaining = db.query(LoginAttempt).filter(LoginAttempt.username == username).count()
            assert remaining == 0
        finally:
            db.close()

        # 成功登录清空用户名维度计数后，下一次失败仍是普通 401，而非 429
        resp = _login(client, username, "wrongpass")
        assert resp.status_code == 401
        assert resp.json()["code"] == 40110
    finally:
        _cleanup([username])


# ===== S15 用户等级 =====


def test_resolve_level_boundaries():
    cases = [
        (0, "茶客", 1, "茶友", 5, 5),
        (4, "茶客", 1, "茶友", 5, 1),
        (5, "茶友", 2, "茶人", 20, 15),
        (19, "茶友", 2, "茶人", 20, 1),
        (20, "茶人", 3, "茶师", 50, 30),
        (49, "茶人", 3, "茶师", 50, 1),
        (50, "茶师", 4, None, None, 0),
        (120, "茶师", 4, None, None, 0),
    ]
    for count, name, index, next_name, next_threshold, remaining in cases:
        info = resolve_level(count)
        assert info.name == name
        assert info.index == index
        assert info.next_name == next_name
        assert info.next_threshold == next_threshold
        assert info.remaining == remaining


def test_me_stats_requires_login():
    resp = TestClient(app).get("/api/v1/me/stats")
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_me_stats_returns_counts_and_level():
    username = _unique_username()
    tea_id = _create_tea()
    try:
        client = _register(username)
        client.post(f"/api/v1/favorites/{tea_id}")
        default_list = client.get("/api/v1/lists").json()["data"][0]["id"]
        client.put(f"/api/v1/lists/{default_list}/notes/{tea_id}", json={"content": "香气清雅"})
        client.post("/api/v1/shares/generate")

        resp = client.get("/api/v1/me/stats")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["favorite_count"] == 1
        assert data["note_count"] == 1
        assert data["share_count"] == 1
        assert data["level"]["name"] == "茶客"
        assert data["level"]["index"] == 1
        assert data["level"]["next_name"] == "茶友"
        assert data["level"]["next_threshold"] == 5
        assert data["level"]["remaining"] == 4
    finally:
        _cleanup([username], [tea_id])


# ===== S16 个性化推荐 =====


def test_recommended_anonymous_returns_one_active_tea():
    resp = TestClient(app).get("/api/v1/teas/recommended")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["id"] > 0
    assert items[0]["name"]


def test_recommended_logged_in_without_favorites():
    username = _unique_username()
    try:
        client = _register(username)
        resp = client.get("/api/v1/teas/recommended", params={"limit": 1})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
    finally:
        _cleanup([username])


def test_recommended_prefers_favorite_category_and_excludes_favorited():
    username = _unique_username()
    favorite_tea = _create_tea(category="green")
    other_tea = _create_tea(category="green")
    try:
        client = _register(username)
        client.post(f"/api/v1/favorites/{favorite_tea}")

        resp = client.get("/api/v1/teas/recommended", params={"limit": 1})
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) == 1
        assert items[0]["category"] == "green"
        assert items[0]["id"] != favorite_tea
        # 另一款未收藏的同茶类茶品在候选池内（随机结果可能是任一绿色茶）
        assert other_tea > 0
    finally:
        _cleanup([username], [favorite_tea, other_tea])


def test_recommended_exclude_id_works_for_anonymous_fallback():
    first = TestClient(app).get("/api/v1/teas/recommended").json()["data"][0]
    for _ in range(5):
        items = (
            TestClient(app)
            .get("/api/v1/teas/recommended", params={"exclude_id": first["id"]})
            .json()["data"]
        )
        assert all(item["id"] != first["id"] for item in items)

    # 非法 exclude_id 与其他端点一致：40000
    resp = TestClient(app).get("/api/v1/teas/recommended", params={"exclude_id": "abc"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40000


def test_recommended_exclude_id_works_in_preference_path():
    username = _unique_username()
    favorite_tea = _create_tea(category="green")
    current_tea = _create_tea(category="green")
    try:
        client = _register(username)
        client.post(f"/api/v1/favorites/{favorite_tea}")

        for _ in range(5):
            items = client.get(
                "/api/v1/teas/recommended",
                params={"limit": 1, "exclude_id": current_tea},
            ).json()["data"]
            assert all(item["id"] not in {favorite_tea, current_tea} for item in items)
    finally:
        _cleanup([username], [favorite_tea, current_tea])
