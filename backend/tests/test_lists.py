"""清单与品鉴笔记测试（对齐 TEST_PLAN TC-NOTE-01 ~ 05 / TC-PERM-03 / TC-LIST-01 ~ 05）"""

import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.collection_list import CollectionList
from app.models.favorite import FavoriteItem
from app.models.tea import Tea
from app.repositories import user_repo


def _unique_username(prefix: str = "noteuser") -> str:
    return f"{prefix}{int(time.time() * 1000000) % 100000000}"


def _register(username: str) -> tuple[TestClient, str]:
    client = TestClient(app)
    resp = client.post("/api/v1/auth/register", json={"username": username, "password": "tea2026"})
    assert resp.status_code == 200
    return client, resp.cookies["tea_session"]


def _create_tea(*, active: bool = True) -> int:
    db = SessionLocal()
    try:
        tea = Tea(
            name=f"笔记茶{int(time.time() * 1000000) % 100000000}",
            category="white",
            origin="福建 测试产区",
            season="明前",
            shape_desc="",
            soup_desc="",
            aroma_desc="",
            taste_desc="",
            is_active=active,
            favorite_count=0,
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


def _user_id(username: str) -> int:
    db = SessionLocal()
    try:
        return user_repo.get_by_username(db, username).id
    finally:
        db.close()


def _lists(client: TestClient) -> list[dict]:
    resp = client.get("/api/v1/lists")
    assert resp.status_code == 200
    return resp.json()["data"]


def _default_list(client: TestClient) -> dict:
    lists = _lists(client)
    assert lists
    assert lists[0]["is_default"] is True
    return lists[0]


def _create_list(client: TestClient, title: str) -> dict:
    resp = client.post("/api/v1/lists", json={"title": title})
    assert resp.status_code == 200
    return resp.json()["data"]


def test_note_01_save_and_read_back():
    username = _unique_username()
    tea_id = _create_tea()
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_id}")
        default = _default_list(client)

        resp = client.put(
            f"/api/v1/lists/{default['id']}/notes/{tea_id}", json={"content": "第一泡豆香突出"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "tea_id": tea_id,
            "list_id": default["id"],
            "tasting_note": "第一泡豆香突出",
        }

        data = client.get(f"/api/v1/lists/{default['id']}").json()["data"]
        assert data["title"] == "我的收藏"
        assert data["is_default"] is True
        assert data["tea_count"] == 1
        assert data["items"][0]["tasting_note"] == "第一泡豆香突出"
        assert data["items"][0]["is_available"] is True
        assert data["share"] is None
    finally:
        _cleanup([tea_id], [username])


def test_note_02_cannot_write_note_for_unfavorited_tea():
    username = _unique_username()
    tea_id = _create_tea()
    client, _ = _register(username)
    try:
        default = _default_list(client)
        resp = client.put(
            f"/api/v1/lists/{default['id']}/notes/{tea_id}", json={"content": "不该保存"}
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == 40430

        db = SessionLocal()
        try:
            assert (
                db.query(FavoriteItem)
                .filter(FavoriteItem.user_id == _user_id(username), FavoriteItem.tea_id == tea_id)
                .count()
                == 0
            )
        finally:
            db.close()
    finally:
        _cleanup([tea_id], [username])


def test_note_03_clear_note_keeps_favorite_item():
    username = _unique_username()
    tea_id = _create_tea()
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_id}")
        default = _default_list(client)
        path = f"/api/v1/lists/{default['id']}/notes/{tea_id}"
        client.put(path, json={"content": "原始笔记"})

        cleared = client.put(path, json={"content": None})
        assert cleared.status_code == 200
        assert cleared.json()["data"]["tasting_note"] is None

        client.put(path, json={"content": "再来一条"})
        blank = client.put(path, json={"content": "   "})
        assert blank.status_code == 200
        assert blank.json()["data"]["tasting_note"] is None

        data = client.get(f"/api/v1/lists/{default['id']}").json()["data"]
        assert data["tea_count"] == 1
        assert data["items"][0]["tasting_note"] is None
    finally:
        _cleanup([tea_id], [username])


def test_note_04_length_limit():
    username = _unique_username()
    tea_id = _create_tea()
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_id}")
        default = _default_list(client)
        path = f"/api/v1/lists/{default['id']}/notes/{tea_id}"

        ok_resp = client.put(path, json={"content": "好" * 20000})
        assert ok_resp.status_code == 200
        assert len(ok_resp.json()["data"]["tasting_note"]) == 20000

        too_long = client.put(path, json={"content": "好" * 20001})
        assert too_long.status_code == 400
        assert too_long.json()["code"] == 40000

        huge = client.put(path, json={"content": "好" * 30000})
        assert huge.status_code == 400
        assert huge.json()["code"] == 40000

        # 原笔记未被截断或破坏
        data = client.get(f"/api/v1/lists/{default['id']}").json()["data"]
        assert len(data["items"][0]["tasting_note"]) == 20000
    finally:
        _cleanup([tea_id], [username])


def test_note_05_notes_are_isolated_between_users():
    username_a = _unique_username("notea")
    username_b = _unique_username("noteb")
    tea_id = _create_tea()
    client_a, _ = _register(username_a)
    client_b, _ = _register(username_b)
    try:
        client_a.post(f"/api/v1/favorites/{tea_id}")
        client_b.post(f"/api/v1/favorites/{tea_id}")
        list_a = _default_list(client_a)
        list_b = _default_list(client_b)
        client_a.put(f"/api/v1/lists/{list_a['id']}/notes/{tea_id}", json={"content": "A-原始笔记"})
        client_b.put(f"/api/v1/lists/{list_b['id']}/notes/{tea_id}", json={"content": "B-新笔记"})

        a_items = client_a.get(f"/api/v1/lists/{list_a['id']}").json()["data"]["items"]
        b_items = client_b.get(f"/api/v1/lists/{list_b['id']}").json()["data"]["items"]
        assert a_items[0]["tasting_note"] == "A-原始笔记"
        assert b_items[0]["tasting_note"] == "B-新笔记"
    finally:
        _cleanup([tea_id], [username_a, username_b])


def test_list_title_validation_and_persistence():
    username = _unique_username()
    client, _ = _register(username)
    try:
        default = _default_list(client)
        assert default["title"] == "我的收藏"

        updated = client.put(f"/api/v1/lists/{default['id']}", json={"title": "  我的私房茶单  "})
        assert updated.status_code == 200
        assert updated.json()["data"]["title"] == "我的私房茶单"
        assert (
            client.get(f"/api/v1/lists/{default['id']}").json()["data"]["title"] == "我的私房茶单"
        )

        for bad in ("", "茶", "   ", "茶" * 21):
            resp = client.put(f"/api/v1/lists/{default['id']}", json={"title": bad})
            assert resp.status_code == 400
            assert resp.json()["code"] == 40000

        assert (
            client.get(f"/api/v1/lists/{default['id']}").json()["data"]["title"] == "我的私房茶单"
        )
    finally:
        _cleanup([], [username])


def test_perm_03_lists_are_user_scoped():
    username_a = _unique_username("perma")
    username_b = _unique_username("permb")
    tea_a = _create_tea()
    tea_b = _create_tea()
    client_a, _ = _register(username_a)
    client_b, _ = _register(username_b)
    try:
        client_a.post(f"/api/v1/favorites/{tea_a}")
        client_b.post(f"/api/v1/favorites/{tea_b}")
        list_a = _default_list(client_a)
        list_b = _default_list(client_b)
        client_b.put(f"/api/v1/lists/{list_b['id']}/notes/{tea_b}", json={"content": "B 的笔记"})

        items_a = client_a.get(f"/api/v1/lists/{list_a['id']}").json()["data"]["items"]
        items_b = client_b.get(f"/api/v1/lists/{list_b['id']}").json()["data"]["items"]
        assert [i["tea_id"] for i in items_a] == [tea_a]
        assert [i["tea_id"] for i in items_b] == [tea_b]

        # A 访问 B 的清单、写 B 的笔记均应 40420（不泄露清单存在性）
        assert client_a.get(f"/api/v1/lists/{list_b['id']}").json()["code"] == 40420
        assert (
            client_a.put(
                f"/api/v1/lists/{list_b['id']}/notes/{tea_b}", json={"content": "篡改"}
            ).json()["code"]
            == 40420
        )
        # A 在自己的清单里对未收藏茶写笔记 → 40430
        resp = client_a.put(f"/api/v1/lists/{list_a['id']}/notes/{tea_b}", json={"content": "篡改"})
        assert resp.status_code == 404
        assert resp.json()["code"] == 40430
        assert (
            client_b.get(f"/api/v1/lists/{list_b['id']}").json()["data"]["items"][0]["tasting_note"]
            == "B 的笔记"
        )
    finally:
        _cleanup([tea_a, tea_b], [username_a, username_b])


def test_list_default_get_or_create_is_concurrent_safe():
    username = _unique_username("listconc")
    client, session = _register(username)
    try:

        def _do_get(_: int) -> int:
            c = TestClient(app)
            c.cookies.set("tea_session", session)
            r = c.get("/api/v1/lists")
            assert r.status_code == 200
            return r.json()["data"][0]["id"]

        with ThreadPoolExecutor(max_workers=20) as pool:
            ids = list(pool.map(_do_get, range(20)))

        assert len(set(ids)) == 1
        db = SessionLocal()
        try:
            assert (
                db.query(CollectionList)
                .filter(CollectionList.user_id == _user_id(username))
                .count()
                == 1
            )
        finally:
            db.close()
    finally:
        _cleanup([], [username])


def test_list_endpoints_require_login():
    c = TestClient(app)
    assert c.get("/api/v1/lists").status_code == 401
    assert c.post("/api/v1/lists", json={"title": "测试标题"}).status_code == 401
    assert c.get("/api/v1/lists/1").status_code == 401
    assert c.put("/api/v1/lists/1", json={"title": "测试标题"}).status_code == 401
    assert c.delete("/api/v1/lists/1").status_code == 401
    assert c.put("/api/v1/lists/1/notes/1", json={"content": "x"}).status_code == 401


# ===== S9 多清单 =====


def test_list_01_create_limit_and_summary_shape():
    username = _unique_username("listmax")
    client, _ = _register(username)
    try:
        default = _default_list(client)
        assert default["tea_count"] == 0

        created = []
        for index in range(9):
            created.append(_create_list(client, f"清单{index}"))
        assert all(item["is_default"] is False for item in created)

        lists = _lists(client)
        assert len(lists) == 10
        assert lists[0]["id"] == default["id"]

        overflow = client.post("/api/v1/lists", json={"title": "第十一个"})
        assert overflow.status_code == 400
        assert overflow.json()["code"] == 40000
    finally:
        _cleanup([], [username])


def test_list_02_delete_migrates_items_and_protects_default():
    username = _unique_username("listdel")
    tea_default = _create_tea()
    tea_extra = _create_tea()
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_default}")
        default = _default_list(client)
        extra = _create_list(client, "待删清单")

        added = client.post(f"/api/v1/favorites/{tea_extra}", json={"list_id": extra["id"]})
        assert added.status_code == 200
        assert added.json()["data"]["list_ids"] == [extra["id"]]
        note = client.put(
            f"/api/v1/lists/{extra['id']}/notes/{tea_extra}", json={"content": "迁移笔记"}
        )
        assert note.status_code == 200

        deleted = client.delete(f"/api/v1/lists/{extra['id']}")
        assert deleted.status_code == 200
        assert deleted.json()["code"] == 0

        assert client.get(f"/api/v1/lists/{extra['id']}").json()["code"] == 40420
        detail = client.get(f"/api/v1/lists/{default['id']}").json()["data"]
        by_id = {item["tea_id"]: item for item in detail["items"]}
        assert set(by_id) == {tea_default, tea_extra}
        assert by_id[tea_extra]["tasting_note"] == "迁移笔记"

        protected = client.delete(f"/api/v1/lists/{default['id']}")
        assert protected.status_code == 400
        assert protected.json()["code"] == 40000
        assert client.get(f"/api/v1/lists/{default['id']}").status_code == 200
    finally:
        _cleanup([tea_default, tea_extra], [username])


def test_list_03_delete_merges_duplicate_tea_without_losing_note():
    username = _unique_username("listmerge")
    tea_id = _create_tea()
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_id}")
        default = _default_list(client)
        extra = _create_list(client, "重复清单")
        again = client.post(f"/api/v1/favorites/{tea_id}", json={"list_id": extra["id"]})
        assert again.status_code == 200
        assert again.json()["data"]["favorite_count"] == 1
        assert len(again.json()["data"]["list_ids"]) == 2

        client.put(f"/api/v1/lists/{extra['id']}/notes/{tea_id}", json={"content": "第二清单笔记"})
        assert client.delete(f"/api/v1/lists/{extra['id']}").status_code == 200

        detail = client.get(f"/api/v1/lists/{default['id']}").json()["data"]
        assert detail["tea_count"] == 1
        assert detail["items"][0]["tasting_note"] == "第二清单笔记"

        db = SessionLocal()
        try:
            assert (
                db.query(FavoriteItem)
                .filter(FavoriteItem.user_id == _user_id(username), FavoriteItem.tea_id == tea_id)
                .count()
                == 1
            )
        finally:
            db.close()
    finally:
        _cleanup([tea_id], [username])


def test_list_04_delete_list_cascades_share_token():
    username = _unique_username("listshare")
    client, _ = _register(username)
    try:
        extra = _create_list(client, "可分享清单")
        share = client.post("/api/v1/shares/generate", json={"list_id": extra["id"]}).json()["data"]
        assert share["is_new"] is True

        guest = TestClient(app)
        assert guest.get(f"/api/v1/shares/{share['token']}").status_code == 200

        assert client.delete(f"/api/v1/lists/{extra['id']}").status_code == 200
        assert guest.get(f"/api/v1/shares/{share['token']}").json()["code"] == 40410
    finally:
        _cleanup([], [username])


def test_list_05_share_is_per_list():
    username = _unique_username("listper")
    tea_id = _create_tea()
    client, _ = _register(username)
    try:
        client.post(f"/api/v1/favorites/{tea_id}")
        default = _default_list(client)
        extra = _create_list(client, "另一个清单")

        default_share = client.post("/api/v1/shares/generate").json()["data"]
        extra_share = client.post("/api/v1/shares/generate", json={"list_id": extra["id"]}).json()[
            "data"
        ]
        assert default_share["token"] != extra_share["token"]

        guest = TestClient(app)
        assert (
            guest.get(f"/api/v1/shares/{default_share['token']}").json()["data"]["tea_count"] == 1
        )
        assert guest.get(f"/api/v1/shares/{extra_share['token']}").json()["data"]["tea_count"] == 0

        assert (
            client.get(f"/api/v1/lists/{default['id']}").json()["data"]["share"]["token"]
            == default_share["token"]
        )
        assert (
            client.get(f"/api/v1/lists/{extra['id']}").json()["data"]["share"]["token"]
            == extra_share["token"]
        )
    finally:
        _cleanup([tea_id], [username])
