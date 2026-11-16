"""收藏模块测试（对齐 TEST_PLAN TC-FAV-01 ~ TC-FAV-07）

测试使用独立临时茶品与临时用户，避免污染种子数据；用例结束清理。
并发用例使用独立 TestClient + 同一会话 Cookie，验证唯一索引与计数原子性。
"""

import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.favorite import FavoriteItem
from app.models.tea import Tea
from app.repositories import favorite_repo, user_repo


def _unique_username(prefix: str = "favuser") -> str:
    return f"{prefix}{int(time.time() * 1000000) % 100000000}"


def _register(username: str) -> tuple[TestClient, str]:
    client = TestClient(app)
    resp = client.post("/api/v1/auth/register", json={"username": username, "password": "tea2026"})
    assert resp.status_code == 200
    return client, resp.cookies["tea_session"]


def _create_tea(*, active: bool = True, count: int = 0) -> int:
    db = SessionLocal()
    try:
        tea = Tea(
            name=f"测试茶{int(time.time() * 1000000) % 100000000}",
            category="green",
            origin="浙江 测试产区",
            season="春茶",
            shape_desc="",
            soup_desc="",
            aroma_desc="",
            taste_desc="",
            is_active=active,
            favorite_count=count,
        )
        db.add(tea)
        db.commit()
        db.refresh(tea)
        return tea.id
    finally:
        db.close()


def _cleanup(tea_ids: list[int], usernames: list[str]) -> None:
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


def _tea_count(tea_id: int) -> int:
    db = SessionLocal()
    try:
        return int(db.query(Tea).filter(Tea.id == tea_id).first().favorite_count)
    finally:
        db.close()


def _favorite_rows(tea_id: int) -> int:
    db = SessionLocal()
    try:
        return db.query(FavoriteItem).filter(FavoriteItem.tea_id == tea_id).count()
    finally:
        db.close()


def test_fav_01_add_favorite_updates_count_and_status():
    username = _unique_username()
    tea_id = _create_tea(count=10)
    client, _ = _register(username)
    try:
        resp = client.post(f"/api/v1/favorites/{tea_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["tea_id"] == tea_id
        assert data["is_favorited"] is True
        assert data["favorite_count"] == 11
        assert len(data["list_ids"]) == 1
        assert _favorite_rows(tea_id) == 1
        assert _tea_count(tea_id) == 11

        status = client.get(f"/api/v1/favorites/{tea_id}/status").json()["data"]
        assert status["is_favorited"] is True
        assert status["favorite_count"] == 11
    finally:
        _cleanup([tea_id], [username])


def test_fav_02_add_is_idempotent_and_concurrent():
    username = _unique_username()
    tea_id = _create_tea(count=0)
    client, session = _register(username)
    try:
        # 连续两次点击
        assert client.post(f"/api/v1/favorites/{tea_id}").json()["data"]["is_favorited"] is True
        assert client.post(f"/api/v1/favorites/{tea_id}").json()["data"]["is_favorited"] is True
        assert _favorite_rows(tea_id) == 1
        assert _tea_count(tea_id) == 1

        # 20 线程并发收藏同一茶品（需先清理该用户已有收藏）
        db = SessionLocal()
        try:
            favorite_repo.delete_all_for_tea(db, user_repo.get_by_username(db, username).id, tea_id)
            db.commit()
        finally:
            db.close()
        # 计数回滚到 0，保证并发断言基于干净状态
        db = SessionLocal()
        try:
            db.query(Tea).filter(Tea.id == tea_id).update({"favorite_count": 0})
            db.commit()
        finally:
            db.close()

        def _do_add(_: int) -> dict:
            c = TestClient(app)
            c.cookies.set("tea_session", session)
            r = c.post(f"/api/v1/favorites/{tea_id}")
            return {"status": r.status_code, "body": r.json()}

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(_do_add, range(20)))

        assert all(r["status"] == 200 and r["body"]["code"] == 0 for r in results)
        assert _favorite_rows(tea_id) == 1
        assert _tea_count(tea_id) == 1
    finally:
        _cleanup([tea_id], [username])


def test_fav_03_remove_favorite_decrements_count():
    username = _unique_username()
    tea_id = _create_tea(count=5)
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_id}")
        resp = client.delete(f"/api/v1/favorites/{tea_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tea_id"] == tea_id
        assert data["is_favorited"] is False
        assert data["favorite_count"] == 5
        assert data["list_ids"] == []
        assert _favorite_rows(tea_id) == 0
        assert _tea_count(tea_id) == 5
        status = client.get(f"/api/v1/favorites/{tea_id}/status").json()["data"]
        assert status["is_favorited"] is False
    finally:
        _cleanup([tea_id], [username])


def test_fav_04_remove_is_idempotent_and_never_negative():
    username = _unique_username()
    tea_id = _create_tea(count=0)
    client, session = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_id}")
        assert _tea_count(tea_id) == 1

        def _do_remove(_: int) -> dict:
            c = TestClient(app)
            c.cookies.set("tea_session", session)
            r = c.delete(f"/api/v1/favorites/{tea_id}")
            return {"status": r.status_code, "body": r.json()}

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(_do_remove, range(10)))

        assert all(r["status"] == 200 and r["body"]["code"] == 0 for r in results)
        assert _favorite_rows(tea_id) == 0
        assert _tea_count(tea_id) == 0

        # 未收藏时再次取消仍幂等成功
        again = client.delete(f"/api/v1/favorites/{tea_id}")
        assert again.status_code == 200
        assert again.json()["data"]["favorite_count"] == 0
        assert _tea_count(tea_id) == 0
    finally:
        _cleanup([tea_id], [username])


def test_fav_05_missing_and_off_shelf_tea():
    username = _unique_username()
    tea_id = _create_tea(active=False, count=7)
    client, _ = _register(username)
    try:
        missing = client.post("/api/v1/favorites/999999")
        assert missing.status_code == 404
        assert missing.json()["code"] == 40400

        off_shelf = client.post(f"/api/v1/favorites/{tea_id}")
        assert off_shelf.status_code == 404
        assert off_shelf.json()["code"] == 40401
        assert _favorite_rows(tea_id) == 0
        assert _tea_count(tea_id) == 7

        # 下架茶允许状态查询（但未收藏）
        status = client.get(f"/api/v1/favorites/{tea_id}/status")
        assert status.status_code == 200
        assert status.json()["data"]["is_favorited"] is False
    finally:
        _cleanup([tea_id], [username])


def test_fav_06_status_is_user_scoped_and_allows_off_shelf():
    username_a = _unique_username("fava")
    username_b = _unique_username("favb")
    tea_id = _create_tea(count=3, active=True)
    client_a, _ = _register(username_a)
    client_b, _ = _register(username_b)
    try:
        client_a.post(f"/api/v1/favorites/{tea_id}")
        assert (
            client_a.get(f"/api/v1/favorites/{tea_id}/status").json()["data"]["is_favorited"]
            is True
        )
        assert (
            client_b.get(f"/api/v1/favorites/{tea_id}/status").json()["data"]["is_favorited"]
            is False
        )

        # 下架后允许查询状态，且保留已收藏事实
        db = SessionLocal()
        try:
            db.query(Tea).filter(Tea.id == tea_id).update({"is_active": False})
            db.commit()
        finally:
            db.close()
        status = client_a.get(f"/api/v1/favorites/{tea_id}/status")
        assert status.status_code == 200
        assert status.json()["data"]["is_favorited"] is True

        # 下架后仍可取消收藏
        removed = client_a.delete(f"/api/v1/favorites/{tea_id}")
        assert removed.status_code == 200
        assert removed.json()["data"]["is_favorited"] is False

        assert client_a.get("/api/v1/favorites/999999/status").json()["code"] == 40400
    finally:
        _cleanup([tea_id], [username_a, username_b])


def test_fav_07_requires_login():
    tea_id = _create_tea(count=0)
    try:
        c = TestClient(app)
        for method, path in (
            ("post", f"/api/v1/favorites/{tea_id}"),
            ("delete", f"/api/v1/favorites/{tea_id}"),
            ("get", f"/api/v1/favorites/{tea_id}/status"),
        ):
            resp = getattr(c, method)(path)
            assert resp.status_code == 401
            assert resp.json()["code"] == 40100
    finally:
        _cleanup([tea_id], [])


def test_fav_08_multi_user_concurrent_add():
    """多人同时收藏同一茶品：每人 1 行，计数 +N。"""
    tea_id = _create_tea(count=0)
    usernames: list[str] = []
    sessions: list[str] = []
    try:
        for index in range(12):
            username = _unique_username(f"multifav{index}")
            _client, session = _register(username)
            usernames.append(username)
            sessions.append(session)

        def _do_add(session: str) -> dict:
            c = TestClient(app)
            c.cookies.set("tea_session", session)
            r = c.post(f"/api/v1/favorites/{tea_id}")
            return {"status": r.status_code, "body": r.json()}

        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(_do_add, sessions))

        assert all(r["status"] == 200 and r["body"]["code"] == 0 for r in results)
        assert _favorite_rows(tea_id) == 12
        assert _tea_count(tea_id) == 12
    finally:
        _cleanup([tea_id], usernames)


def test_fav_09_multi_list_counts_once_across_lists():
    """S9：同一茶品跨清单只计 1 次收藏数，按清单取消不影响其它清单。"""
    username = _unique_username("favlists")
    tea_id = _create_tea(count=0)
    client, _ = _register(username)
    try:
        default = client.get("/api/v1/lists").json()["data"][0]
        extra = client.post("/api/v1/lists", json={"title": "第二清单"}).json()["data"]

        first = client.post(f"/api/v1/favorites/{tea_id}").json()["data"]
        assert first["favorite_count"] == 1
        assert first["list_ids"] == [default["id"]]

        second = client.post(f"/api/v1/favorites/{tea_id}", json={"list_id": extra["id"]}).json()[
            "data"
        ]
        assert second["favorite_count"] == 1
        assert sorted(second["list_ids"]) == sorted([default["id"], extra["id"]])

        removed_one = client.delete(f"/api/v1/favorites/{tea_id}", params={"list_id": extra["id"]})
        assert removed_one.json()["data"]["favorite_count"] == 1
        assert removed_one.json()["data"]["list_ids"] == [default["id"]]

        status = client.get(f"/api/v1/favorites/{tea_id}/status").json()["data"]
        assert status["is_favorited"] is True
        assert status["list_ids"] == [default["id"]]

        removed_all = client.delete(f"/api/v1/favorites/{tea_id}")
        assert removed_all.json()["data"]["favorite_count"] == 0
        assert removed_all.json()["data"]["list_ids"] == []
        assert _tea_count(tea_id) == 0

        # 不存在的清单 / 他人的清单 → 40420
        assert (
            client.post(f"/api/v1/favorites/{tea_id}", json={"list_id": 999999}).json()["code"]
            == 40420
        )
    finally:
        _cleanup([tea_id], [username])
