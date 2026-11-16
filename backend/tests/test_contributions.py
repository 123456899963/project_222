"""用户贡献与审核测试（对齐 TEST_PLAN TC-CONTRIB-01 ~ 08 / S10–S13）

覆盖：
- 新茶提交：名品-茶类映射校验、名称查重、待审核落库
- 科普投稿：目标茶品有效性、内容长度、通过后详情页展示
- 我的提交：仅本人可见、仅 pending 可删除
- 管理端：审核队列、通过后新茶上架、拒绝理由回传、权限门禁
"""

import time

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.models.contribution import Contribution
from app.models.favorite import FavoriteItem
from app.models.tea import Tea
from app.models.user import User
from app.repositories import user_repo


def _suffix() -> str:
    return f"{int(time.time() * 1000000) % 100000000}"


def _register(username: str) -> TestClient:
    client = TestClient(app)
    resp = client.post("/api/v1/auth/register", json={"username": username, "password": "tea2026"})
    assert resp.status_code == 200
    return client


def _admin_client() -> TestClient:
    admin = TestClient(app)
    resp = admin.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return admin


def _create_tea(*, name: str | None = None, active: bool = True) -> int:
    db = SessionLocal()
    try:
        tea = Tea(
            name=name or f"贡献茶{_suffix()}",
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


def _tea_payload(name: str, category: str = "green", **overrides) -> dict:
    data = {
        "name": name,
        "category": category,
        "origin": "浙江 测试产区",
        "season": "明前",
        "fermentation": "不发酵",
        "representative_variety": None,
        "shape_desc": "扁平光滑",
        "soup_desc": "嫩绿明亮",
        "aroma_desc": "豆香清雅",
        "taste_desc": "鲜爽甘醇",
        "water_temp": 85,
        "tea_amount": 3,
        "brew_time": 90,
        "main_image_url": None,
        "tips_history": None,
        "tips_suitable": None,
        "tips_misconception": None,
        "tips_official_note": None,
    }
    data.update(overrides)
    return data


def _submit_tea(client: TestClient, payload: dict) -> dict:
    return client.post("/api/v1/contributions", json={"type": "new_tea", "tea": payload}).json()


def _cleanup(*, usernames: list[str], tea_ids: list[int], names: list[str]) -> None:
    db = SessionLocal()
    try:
        if usernames:
            user_ids = [
                user.id
                for name in usernames
                if (user := user_repo.get_by_username(db, name)) is not None
            ]
            if user_ids:
                db.query(Contribution).filter(Contribution.user_id.in_(user_ids)).delete(
                    synchronize_session=False
                )
                db.query(FavoriteItem).filter(FavoriteItem.user_id.in_(user_ids)).delete(
                    synchronize_session=False
                )
                db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        if tea_ids:
            db.query(FavoriteItem).filter(FavoriteItem.tea_id.in_(tea_ids)).delete(
                synchronize_session=False
            )
            db.query(Tea).filter(Tea.id.in_(tea_ids)).delete(synchronize_session=False)
        if names:
            db.query(Tea).filter(Tea.name.in_(names)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_contrib_01_submit_new_tea_pending():
    username = f"ctb1{_suffix()}"
    client = _register(username)
    name = f"测试新茶{_suffix()}"
    try:
        data = _submit_tea(client, _tea_payload(name))
        assert data["code"] == 0, data
        item = data["data"]
        assert item["type"] == "new_tea"
        assert item["status"] == "pending"
        assert item["payload"]["name"] == name
        assert item["target_tea_id"] is None
        assert item["reject_reason"] is None

        mine = client.get("/api/v1/contributions/mine").json()["data"]
        assert [row["id"] for row in mine] == [item["id"]]
    finally:
        _cleanup(usernames=[username], tea_ids=[], names=[name])


def test_contrib_02_name_category_mapping_blocks_contradiction():
    username = f"ctb2{_suffix()}"
    client = _register(username)
    try:
        # 碧螺春在映射表中属于绿茶，提交为红茶应立即拦截
        data = _submit_tea(client, _tea_payload("碧螺春", category="red"))
        assert data["code"] == 40000
        assert "绿茶" in data["message"]
        assert client.get("/api/v1/contributions/mine").json()["data"] == []
    finally:
        _cleanup(usernames=[username], tea_ids=[], names=[])


def test_contrib_03_duplicate_name_blocked():
    username = f"ctb3{_suffix()}"
    client = _register(username)
    try:
        # 已存在茶品同名（相似度 100%）→ 拦截
        data = _submit_tea(client, _tea_payload("大红袍", category="oolong"))
        assert data["code"] == 40000
        assert "过于相似" in data["message"]
    finally:
        _cleanup(usernames=[username], tea_ids=[], names=[])


def test_contrib_04_article_validation_and_submit():
    username = f"ctb4{_suffix()}"
    tea_id = _create_tea()
    client = _register(username)
    try:
        short = client.post(
            "/api/v1/contributions",
            json={"type": "article", "target_tea_id": tea_id, "content": "太短"},
        )
        assert short.status_code == 400
        assert short.json()["code"] == 40000

        missing_tea = client.post(
            "/api/v1/contributions",
            json={"type": "article", "target_tea_id": 999999, "content": "这是一段有效的科普内容"},
        )
        assert missing_tea.json()["code"] == 40000

        ok_resp = client.post(
            "/api/v1/contributions",
            json={
                "type": "article",
                "target_tea_id": tea_id,
                "title": "品鉴小记",
                "content": "这是一段有效的科普内容，介绍白茶的冲泡要点。",
            },
        )
        assert ok_resp.json()["code"] == 0
        item = ok_resp.json()["data"]
        assert item["target_tea_id"] == tea_id
        assert item["target_tea_name"]
        assert item["payload"]["title"] == "品鉴小记"
    finally:
        _cleanup(usernames=[username], tea_ids=[tea_id], names=[])


def test_contrib_05_mine_scope_and_delete_rules():
    username_a = f"ctb5a{_suffix()}"
    username_b = f"ctb5b{_suffix()}"
    client_a = _register(username_a)
    client_b = _register(username_b)
    name = f"待删新茶{_suffix()}"
    try:
        item = _submit_tea(client_a, _tea_payload(name))["data"]
        assert client_b.get("/api/v1/contributions/mine").json()["data"] == []
        # 非本人删除 → 40440（不泄露存在性）
        denied = client_b.delete(f"/api/v1/contributions/{item['id']}")
        assert denied.status_code == 404
        assert denied.json()["code"] == 40440
        # 本人删除 pending → 成功
        assert client_a.delete(f"/api/v1/contributions/{item['id']}").json()["code"] == 0
        assert client_a.get("/api/v1/contributions/mine").json()["data"] == []
    finally:
        _cleanup(usernames=[username_a, username_b], tea_ids=[], names=[name])


def test_contrib_06_admin_approve_new_tea_creates_active_tea():
    username = f"ctb6{_suffix()}"
    client = _register(username)
    admin = _admin_client()
    name = f"审核通过茶{_suffix()}"
    try:
        item = _submit_tea(client, _tea_payload(name))["data"]
        queue = admin.get(
            "/api/v1/admin/contributions", params={"status": "pending", "type": "new_tea"}
        ).json()["data"]
        assert any(
            row["id"] == item["id"] and row["username"] == username for row in queue["items"]
        )

        approved = admin.post(f"/api/v1/admin/contributions/{item['id']}/approve").json()
        assert approved["code"] == 0
        assert approved["data"]["status"] == "approved"
        assert approved["data"]["reviewer_id"] is not None
        assert approved["data"]["reviewed_at"] is not None

        db = SessionLocal()
        try:
            tea = db.query(Tea).filter(Tea.name == name).first()
            assert tea is not None and tea.is_active is True
        finally:
            db.close()
        # 已处理记录不可重复审核
        again = admin.post(f"/api/v1/admin/contributions/{item['id']}/approve").json()
        assert again["code"] == 40000
    finally:
        _cleanup(usernames=[username], tea_ids=[], names=[name])


def test_contrib_07_reject_reason_visible_and_immutable():
    username = f"ctb7{_suffix()}"
    client = _register(username)
    admin = _admin_client()
    name = f"被拒新茶{_suffix()}"
    try:
        item = _submit_tea(client, _tea_payload(name))["data"]
        rejected = admin.post(
            f"/api/v1/admin/contributions/{item['id']}/reject",
            json={"reason": "信息不完整"},
        ).json()
        assert rejected["code"] == 0
        assert rejected["data"]["status"] == "rejected"
        assert rejected["data"]["reject_reason"] == "信息不完整"

        mine = client.get("/api/v1/contributions/mine").json()["data"]
        assert mine[0]["status"] == "rejected"
        assert mine[0]["reject_reason"] == "信息不完整"
        # 已拒绝不可删除 / 不可再通过
        assert client.delete(f"/api/v1/contributions/{item['id']}").json()["code"] == 40000
        assert (
            admin.post(f"/api/v1/admin/contributions/{item['id']}/approve").json()["code"] == 40000
        )
    finally:
        _cleanup(usernames=[username], tea_ids=[], names=[name])


def test_contrib_08_permissions_and_approved_article_in_detail():
    username = f"ctb8{_suffix()}"
    tea_id = _create_tea()
    client = _register(username)
    admin = _admin_client()
    guest = TestClient(app)
    try:
        # 游客不能提交；普通用户不能进审核队列
        assert (
            guest.post(
                "/api/v1/contributions", json={"type": "new_tea", "tea": _tea_payload("x")}
            ).status_code
            == 401
        )
        assert client.get("/api/v1/admin/contributions").status_code == 403

        item = client.post(
            "/api/v1/contributions",
            json={
                "type": "article",
                "target_tea_id": tea_id,
                "title": "审核后展示",
                "content": "通过审核的科普内容应在详情页展示。",
            },
        ).json()["data"]
        assert admin.post(f"/api/v1/admin/contributions/{item['id']}/approve").json()["code"] == 0

        detail = guest.get(f"/api/v1/teas/{tea_id}").json()["data"]
        articles = detail["contributed_articles"]
        assert any(row["id"] == item["id"] and row["contributor"] == username for row in articles)
    finally:
        _cleanup(usernames=[username], tea_ids=[tea_id], names=[])
