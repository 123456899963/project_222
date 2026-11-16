"""批次一功能测试（S1 OR 切换 / S2 五档筛选 / S6 相关推荐 / S7 最新小贴士 / S17 热度权重）

测试库：tea_guide_test（conftest 强制隔离）；临时数据用完即删。
"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.main import app
from app.models.favorite import FavoriteItem
from app.models.tea import Tea, TeaTips
from app.models.user import User
from app.services import lists as lists_service

client = TestClient(app)


def _make_tea(**overrides) -> int:
    db = SessionLocal()
    try:
        payload = {
            "name": "批次一测试茶",
            "category": "green",
            "origin": "测试省 测试产区",
            "season": "春茶",
            "fermentation": "不发酵",
            "shape_desc": "",
            "soup_desc": "",
            "aroma_desc": "",
            "taste_desc": "",
            "is_active": True,
            "favorite_count": 0,
        }
        payload.update(overrides)
        tea = Tea(**payload)
        db.add(tea)
        db.commit()
        db.refresh(tea)
        return tea.id
    finally:
        db.close()


def _cleanup(*tea_ids: int) -> None:
    db = SessionLocal()
    try:
        db.query(Tea).filter(Tea.id.in_(tea_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


# ===== S2 五档筛选 =====


def test_s2_filter_by_fermentation():
    green_id = _make_tea(name="S2绿茶", fermentation="不发酵")
    red_id = _make_tea(name="S2红茶", category="red", fermentation="全发酵")
    try:
        data = client.get("/api/v1/teas", params={"fermentation": "全发酵"}).json()["data"]
        ids = {item["id"] for item in data["items"]}
        assert red_id in ids
        assert green_id not in ids
    finally:
        _cleanup(green_id, red_id)


def test_s2_price_range_overlap():
    cheap_id = _make_tea(name="S2低价茶", price_min=100, price_max=300)
    dear_id = _make_tea(name="S2高价茶", price_min=2000, price_max=3000)
    try:
        data = client.get("/api/v1/teas", params={"price_min": 0, "price_max": 500}).json()["data"]
        ids = {item["id"] for item in data["items"]}
        assert cheap_id in ids
        assert dear_id not in ids
    finally:
        _cleanup(cheap_id, dear_id)


def test_s2_price_bounds_validation():
    assert (
        client.get("/api/v1/teas", params={"price_min": 500, "price_max": 100}).json()["code"]
        == 40000
    )
    assert client.get("/api/v1/teas", params={"price_min": -1}).status_code == 400


# ===== S1 AND / OR 切换 =====


def test_s1_filter_mode_and_vs_or():
    green_id = _make_tea(name="S1绿茶", category="green", origin="测试省A 产区")
    white_id = _make_tea(name="S1白茶", category="white", origin="测试省B 产区")
    try:
        params = {"category": "green", "origin": "测试省B"}
        and_ids = {
            item["id"]
            for item in client.get("/api/v1/teas", params={**params, "filter_mode": "and"}).json()[
                "data"
            ]["items"]
        }
        assert green_id not in and_ids and white_id not in and_ids

        or_ids = {
            item["id"]
            for item in client.get("/api/v1/teas", params={**params, "filter_mode": "or"}).json()[
                "data"
            ]["items"]
        }
        # OR：茶类命中（绿）或产地命中（白）
        assert green_id in or_ids and white_id in or_ids
    finally:
        _cleanup(green_id, white_id)


def test_s1_invalid_filter_mode():
    resp = client.get("/api/v1/teas", params={"filter_mode": "xor"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40000


# ===== S6 相关推荐 =====


def test_s6_related_excludes_self_and_prefers_same_category():
    base_id = _make_tea(name="S6基准茶", category="yellow", origin="测试省C 产区")
    same_cat_id = _make_tea(name="S6同茶类", category="yellow", origin="测试省D 产区")
    other_id = _make_tea(name="S6其他类", category="dark", origin="测试省E 产区")
    try:
        data = client.get(f"/api/v1/teas/{base_id}/related", params={"limit": 5}).json()["data"]
        ids = [item["id"] for item in data]
        assert base_id not in ids
        assert len(ids) <= 5
        if same_cat_id in ids and other_id in ids:
            assert ids.index(same_cat_id) < ids.index(other_id)
    finally:
        _cleanup(base_id, same_cat_id, other_id)


def test_s6_related_not_found_and_off_shelf():
    assert client.get("/api/v1/teas/999999/related").json()["code"] == 40400
    off_id = _make_tea(name="S6下架茶", is_active=False)
    try:
        assert client.get(f"/api/v1/teas/{off_id}/related").json()["code"] == 40401
    finally:
        _cleanup(off_id)


# ===== S7 最新小贴士 =====


def test_s7_latest_tips_sorted_desc_and_limit():
    old_id = _make_tea(name="S7旧贴士")
    new_id = _make_tea(name="S7新贴士")
    db = SessionLocal()
    try:
        # 与 MySQL CURRENT_TIMESTAMP 写入口径一致（本地时区）
        now = datetime.now()
        db.add_all(
            [
                TeaTips(
                    tea_id=old_id, official_note="旧贴士内容", updated_at=now - timedelta(seconds=5)
                ),
                TeaTips(tea_id=new_id, official_note="新贴士内容", updated_at=now),
            ]
        )
        db.commit()
    finally:
        db.close()
    try:
        data = client.get("/api/v1/tips/latest", params={"limit": 2}).json()["data"]
        assert len(data) == 2
        ids = [item["tea_id"] for item in data]
        assert ids == [new_id, old_id]
        first = next(item for item in data if item["tea_id"] == new_id)
        assert first["summary"] == "新贴士内容"
        assert first["tea_name"] == "S7新贴士"
    finally:
        _cleanup(old_id, new_id)


def test_s7_latest_tips_excludes_off_shelf():
    off_id = _make_tea(name="S7下架贴士", is_active=False)
    db = SessionLocal()
    try:
        db.add(TeaTips(tea_id=off_id, official_note="下架茶贴士", updated_at=utcnow()))
        db.commit()
    finally:
        db.close()
    try:
        data = client.get("/api/v1/tips/latest", params={"limit": 6}).json()["data"]
        assert off_id not in [item["tea_id"] for item in data]
    finally:
        _cleanup(off_id)


# ===== S17 热门 7 天权重 =====


def test_s17_hot_weights_recent_favorites():
    """B：累计 0 + 近 7 天 1 次收藏（得分 3）；A：累计 2（得分 2）→ B 应排在 A 前。"""
    a_id = _make_tea(name="S17累计高", favorite_count=2)
    b_id = _make_tea(name="S17近期热", favorite_count=0)
    db = SessionLocal()
    try:
        user = db.query(User).first()
        assert user is not None, "测试库需存在种子用户"
        list_obj = lists_service.get_or_create_default_list(db, user.id)
        db.commit()
        db.add(
            FavoriteItem(
                user_id=user.id,
                tea_id=b_id,
                list_id=list_obj.id,
                created_at=utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()
    try:
        items = client.get("/api/v1/teas/hot", params={"limit": 20}).json()["data"]
        ids = [item["id"] for item in items]
        assert b_id in ids and a_id in ids
        assert ids.index(b_id) < ids.index(a_id)
    finally:
        _cleanup(a_id, b_id)
