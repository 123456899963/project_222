"""分享链路测试（对齐 TEST_PLAN TC-SHARE-01 ~ 10 / TC-PERM-03 撤销越权）

覆盖：生成复用、并发生成、撤销不可逆、公开字段过滤、大小写敏感、
一键收藏 added/skipped、所有者/游客/撤销态错误码、并发 copy。
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.favorite import FavoriteItem, ShareToken
from app.models.tea import Tea
from app.repositories import user_repo

TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{8}$")


def _unique_username(prefix: str = "shareuser") -> str:
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
            name=f"分享茶{int(time.time() * 1000000) % 100000000}",
            category="oolong",
            origin="福建 测试产区",
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


def _set_tea_active(tea_id: int, active: bool) -> None:
    db = SessionLocal()
    try:
        db.query(Tea).filter(Tea.id == tea_id).update({"is_active": active})
        db.commit()
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


def _active_tokens(list_id: int) -> int:
    db = SessionLocal()
    try:
        return (
            db.query(ShareToken)
            .filter(ShareToken.list_id == list_id, ShareToken.is_active.is_(True))
            .count()
        )
    finally:
        db.close()


def _token_rows(token: str) -> int:
    db = SessionLocal()
    try:
        return db.query(ShareToken).filter(ShareToken.token == token).count()
    finally:
        db.close()


def _tea_count(tea_id: int) -> int:
    db = SessionLocal()
    try:
        return int(db.query(Tea).filter(Tea.id == tea_id).first().favorite_count)
    finally:
        db.close()


def _favorite_rows(user_id: int, tea_id: int) -> int:
    db = SessionLocal()
    try:
        return (
            db.query(FavoriteItem)
            .filter(FavoriteItem.user_id == user_id, FavoriteItem.tea_id == tea_id)
            .count()
        )
    finally:
        db.close()


def _user_id(username: str) -> int:
    db = SessionLocal()
    try:
        return user_repo.get_by_username(db, username).id
    finally:
        db.close()


def _list_id(client: TestClient) -> int:
    return client.get("/api/v1/lists").json()["data"][0]["id"]


def test_share_01_generate_reuses_active_token():
    username = _unique_username()
    client, _ = _register(username)
    try:
        first = client.post("/api/v1/shares/generate")
        assert first.status_code == 200
        data = first.json()["data"]
        assert TOKEN_RE.match(data["token"])
        assert data["url"] == f"/c/{data['token']}"
        assert data["is_new"] is True

        second = client.post("/api/v1/shares/generate").json()["data"]
        assert second["token"] == data["token"]
        assert second["is_new"] is False

        list_id = _list_id(client)
        assert _active_tokens(list_id) == 1
        share = client.get(f"/api/v1/lists/{list_id}").json()["data"]["share"]
        assert share["token"] == data["token"]
    finally:
        _cleanup([], [username])


def test_share_02_concurrent_generate_only_one_active():
    username = _unique_username("shareconc")
    _client, session = _register(username)
    try:

        def _do_generate(_: int) -> dict:
            c = TestClient(app)
            c.cookies.set("tea_session", session)
            r = c.post("/api/v1/shares/generate")
            return {"status": r.status_code, "body": r.json()}

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(_do_generate, range(20)))

        assert all(r["status"] == 200 and r["body"]["code"] == 0 for r in results)
        tokens = {r["body"]["data"]["token"] for r in results}
        assert len(tokens) == 1
        assert sum(1 for r in results if r["body"]["data"]["is_new"] is True) == 1

        db = SessionLocal()
        try:
            list_obj = db.query(ShareToken.list_id).filter(ShareToken.token == tokens.pop()).first()
            assert list_obj is not None
            assert _active_tokens(list_obj[0]) == 1
        finally:
            db.close()
    finally:
        _cleanup([], [username])


def test_share_03_revoke_soft_and_idempotent_error():
    username = _unique_username()
    client, _ = _register(username)
    try:
        token = client.post("/api/v1/shares/generate").json()["data"]["token"]

        resp = client.post(f"/api/v1/shares/revoke/{token}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["token"] == token
        assert data["is_active"] is False
        assert data["revoked_at"]

        again = client.post(f"/api/v1/shares/revoke/{token}")
        assert again.status_code == 409
        assert again.json()["code"] == 40900

        db = SessionLocal()
        try:
            row = db.query(ShareToken).filter(ShareToken.token == token).first()
            assert row is not None and row.is_active is False and row.revoked_at is not None
        finally:
            db.close()
        assert _token_rows(token) == 1
    finally:
        _cleanup([], [username])


def test_share_04_revoked_cannot_revive_and_new_token_required():
    username = _unique_username()
    client, _ = _register(username)
    try:
        old = client.post("/api/v1/shares/generate").json()["data"]["token"]
        client.post(f"/api/v1/shares/revoke/{old}")

        guest = TestClient(app)
        revoked_view = guest.get(f"/api/v1/shares/{old}")
        assert revoked_view.status_code == 200
        body = revoked_view.json()["data"]
        assert body["revoked"] is True
        assert body["items"] == []
        assert body["tea_count"] == 0

        new_data = client.post("/api/v1/shares/generate").json()["data"]
        assert new_data["is_new"] is True
        assert new_data["token"] != old

        assert guest.get(f"/api/v1/shares/{old}").json()["data"]["revoked"] is True
        new_view = guest.get(f"/api/v1/shares/{new_data['token']}")
        assert new_view.json()["data"]["revoked"] is False
    finally:
        _cleanup([], [username])


def test_share_05_public_view_filters_private_fields():
    username_a = _unique_username("sharea")
    username_b = _unique_username("shareb")
    tea_id = _create_tea()
    client_a, _ = _register(username_a)
    client_b, _ = _register(username_b)
    try:
        client_a.post(f"/api/v1/favorites/{tea_id}")
        list_a = client_a.get("/api/v1/lists").json()["data"][0]["id"]
        client_a.put(f"/api/v1/lists/{list_a}/notes/{tea_id}", json={"content": "私有笔记"})
        token = client_a.post("/api/v1/shares/generate").json()["data"]["token"]

        guest = TestClient(app)
        guest_body = guest.get(f"/api/v1/shares/{token}").json()["data"]
        assert guest_body["is_owner"] is False
        assert guest_body["revoked"] is False
        assert guest_body["tea_count"] == 1
        assert "tasting_note" not in guest_body["items"][0]
        assert "username" not in guest_body
        assert "user_id" not in guest_body

        owner_body = client_a.get(f"/api/v1/shares/{token}").json()["data"]
        assert owner_body["is_owner"] is True
        assert "tasting_note" not in owner_body["items"][0]

        other_body = client_b.get(f"/api/v1/shares/{token}").json()["data"]
        assert other_body["is_owner"] is False
    finally:
        _cleanup([tea_id], [username_a, username_b])


def test_share_06_unknown_and_case_sensitive_token():
    guest = TestClient(app)
    missing = guest.get("/api/v1/shares/ZZZZZZZZ")
    assert missing.status_code == 404
    assert missing.json()["code"] == 40410

    username = _unique_username()
    client, _ = _register(username)
    try:
        token = client.post("/api/v1/shares/generate").json()["data"]["token"]
        for variant in {token.upper(), token.lower()} - {token}:
            resp = guest.get(f"/api/v1/shares/{variant}")
            assert resp.status_code == 404
            assert resp.json()["code"] == 40410
    finally:
        _cleanup([], [username])


def test_share_07_other_user_cannot_revoke():
    username_a = _unique_username("revokea")
    username_b = _unique_username("revokeb")
    client_a, _ = _register(username_a)
    client_b, _ = _register(username_b)
    try:
        token = client_a.post("/api/v1/shares/generate").json()["data"]["token"]

        resp = client_b.post(f"/api/v1/shares/revoke/{token}")
        assert resp.status_code == 403
        assert resp.json()["code"] == 40300

        db = SessionLocal()
        try:
            row = db.query(ShareToken).filter(ShareToken.token == token).first()
            assert row.is_active is True and row.revoked_at is None
        finally:
            db.close()

        guest = TestClient(app)
        assert guest.get(f"/api/v1/shares/{token}").json()["data"]["revoked"] is False
    finally:
        _cleanup([], [username_a, username_b])


def test_share_08_copy_returns_added_skipped_total():
    username_a = _unique_username("copya")
    username_b = _unique_username("copyb")
    tea1 = _create_tea(count=10)
    tea2 = _create_tea(count=20)
    tea3 = _create_tea(count=30)
    tea_off = _create_tea(count=40)
    client_a, _ = _register(username_a)
    client_b, _ = _register(username_b)
    try:
        for tea_id in (tea1, tea2, tea3, tea_off):
            assert client_a.post(f"/api/v1/favorites/{tea_id}").status_code == 200
        _set_tea_active(tea_off, False)

        client_b.post(f"/api/v1/favorites/{tea1}")
        token = client_a.post("/api/v1/shares/generate").json()["data"]["token"]

        first = client_b.post(f"/api/v1/shares/{token}/copy")
        assert first.status_code == 200
        assert first.json()["data"] == {"added": 2, "skipped": 2, "total": 4}

        second = client_b.post(f"/api/v1/shares/{token}/copy").json()["data"]
        assert second == {"added": 0, "skipped": 4, "total": 4}

        user_b = _user_id(username_b)
        assert _favorite_rows(user_b, tea1) == 1
        assert _favorite_rows(user_b, tea2) == 1
        assert _favorite_rows(user_b, tea3) == 1
        assert _favorite_rows(user_b, tea_off) == 0
        assert _tea_count(tea2) == 22
        assert _tea_count(tea_off) == 41
    finally:
        _cleanup([tea1, tea2, tea3, tea_off], [username_a, username_b])


def test_share_09_copy_permission_and_revoked_errors():
    username_a = _unique_username("copyperm")
    tea_id = _create_tea()
    client_a, _ = _register(username_a)
    try:
        client_a.post(f"/api/v1/favorites/{tea_id}")
        token = client_a.post("/api/v1/shares/generate").json()["data"]["token"]

        owner = client_a.post(f"/api/v1/shares/{token}/copy")
        assert owner.status_code == 403
        assert owner.json()["code"] == 40300

        guest = TestClient(app)
        assert guest.post(f"/api/v1/shares/{token}/copy").status_code == 401

        client_a.post(f"/api/v1/shares/revoke/{token}")
        revoked = client_a.post(f"/api/v1/shares/{token}/copy")
        assert revoked.status_code == 409
        assert revoked.json()["code"] == 40900

        missing = client_a.post("/api/v1/shares/ZZZZZZZZ/copy")
        assert missing.status_code == 404
        assert missing.json()["code"] == 40410
    finally:
        _cleanup([tea_id], [username_a])


def test_share_10_concurrent_copy_adds_once():
    username_a = _unique_username("copyconca")
    username_c = _unique_username("copyconcc")
    teas = [_create_tea(count=i) for i in range(3)]
    tea_off = _create_tea(count=100)
    client_a, _ = _register(username_a)
    _client_c, session_c = _register(username_c)
    try:
        for tea_id in teas + [tea_off]:
            client_a.post(f"/api/v1/favorites/{tea_id}")
        _set_tea_active(tea_off, False)
        token = client_a.post("/api/v1/shares/generate").json()["data"]["token"]

        def _do_copy(_: int) -> dict:
            c = TestClient(app)
            c.cookies.set("tea_session", session_c)
            r = c.post(f"/api/v1/shares/{token}/copy")
            return {"status": r.status_code, "body": r.json()}

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(_do_copy, range(20)))

        assert all(r["status"] == 200 and r["body"]["code"] == 0 for r in results)
        assert all(r["body"]["data"]["total"] == 4 for r in results)
        assert sum(r["body"]["data"]["added"] for r in results) == 3

        user_c = _user_id(username_c)
        for index, tea_id in enumerate(teas):
            assert _favorite_rows(user_c, tea_id) == 1
            assert _tea_count(tea_id) == index + 2
        assert _favorite_rows(user_c, tea_off) == 0
        assert _tea_count(tea_off) == 101
    finally:
        _cleanup(teas + [tea_off], [username_a, username_c])
