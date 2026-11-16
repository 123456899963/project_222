"""茶品只读接口测试（对齐 API_CONTRACT §4.2.1 ~ §4.2.6 / TEST_PLAN TEAS 用例）

覆盖：列表筛选（同维 OR / 跨维 AND）、排序、分页夹取、关键词、枚举校验、
六大茶类计数、产地选项、热门推荐、随机发现、详情与下架处理、422 重映射。
测试数据依赖 database/init.sql 的 6 款种子茶品；下架场景用临时数据，用例结束清理。
"""

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.tea import Tea

client = TestClient(app)

LIST_ITEM_FIELDS = {
    "id",
    "name",
    "category",
    "origin",
    "season",
    "main_image_url",
    "favorite_count",
}


def _create_off_shelf_tea() -> int:
    db = SessionLocal()
    try:
        tea = Tea(
            name="测试下架茶",
            category="green",
            origin="浙江 测试产区",
            season="春茶",
            shape_desc="",
            soup_desc="",
            aroma_desc="",
            taste_desc="",
            is_active=False,
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


# ===== 4.2.1 列表：分页与结构 =====


def test_list_default_pagination_and_fields():
    resp = client.get("/api/v1/teas")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["page"] == 1
    assert data["page_size"] == 12
    assert data["total"] >= 6  # 种子 6 款
    assert len(data["items"]) >= 6
    # 卡片字段与契约 §2.2 完全一致，不多不少
    assert set(data["items"][0].keys()) == LIST_ITEM_FIELDS


def test_list_pagination_page_size_and_clamping():
    resp = client.get("/api/v1/teas", params={"page": 2, "page_size": 2})
    data = resp.json()["data"]
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2
    # 页码与每页条数越界夹取
    resp = client.get("/api/v1/teas", params={"page": 0, "page_size": 999})
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 50


def test_list_page_beyond_last_returns_empty_items():
    resp = client.get("/api/v1/teas", params={"page": 99999})
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["items"] == []
    assert body["data"]["total"] >= 6


# ===== 4.2.1 列表：筛选（同维 OR / 跨维 AND） =====


def test_list_filter_category_single():
    resp = client.get("/api/v1/teas", params={"category": "green"})
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert all(t["category"] == "green" for t in items)


def test_list_filter_category_multi_or():
    resp = client.get("/api/v1/teas", params={"category": "green,oolong"})
    items = resp.json()["data"]["items"]
    assert len(items) >= 2
    assert {t["category"] for t in items} <= {"green", "oolong"}


def test_list_filter_origin_province_prefix():
    # 省级前缀匹配："浙江" 命中 "浙江 杭州 西湖狮峰"
    resp = client.get("/api/v1/teas", params={"origin": "浙江"})
    items = resp.json()["data"]["items"]
    assert len(items) >= 1
    assert all(t["origin"].startswith("浙江") for t in items)
    assert any(t["name"] == "西湖龙井" for t in items)


def test_list_filter_origin_wildcard_is_escaped():
    # "%" 应按字面量处理，不能退化为全表匹配（origin 通配符转义回归）
    resp = client.get("/api/v1/teas", params={"origin": "%"})
    assert resp.status_code == 200
    assert resp.json()["data"]["items"] == []


def test_list_filter_season():
    resp = client.get("/api/v1/teas", params={"season": "明前"})
    items = resp.json()["data"]["items"]
    assert len(items) >= 2  # 西湖龙井 + 白毫银针
    assert all(t["season"] == "明前" for t in items)


def test_list_filter_cross_dimension_and():
    # 茶类 AND 季节：green AND 明前 → 只剩西湖龙井（种子中）
    resp = client.get("/api/v1/teas", params={"category": "green", "season": "明前"})
    items = resp.json()["data"]["items"]
    assert all(t["category"] == "green" and t["season"] == "明前" for t in items)
    assert any(t["name"] == "西湖龙井" for t in items)
    # green AND 冬茶 → 种子中无结果，空数组不报错
    resp = client.get("/api/v1/teas", params={"category": "green", "season": "冬茶"})
    assert resp.json()["data"]["items"] == []


# ===== 4.2.1 列表：关键词与排序 =====


def test_list_keyword_matches_name_and_origin():
    resp = client.get("/api/v1/teas", params={"keyword": "龙井"})
    names = [t["name"] for t in resp.json()["data"]["items"]]
    assert "西湖龙井" in names
    # 关键词命中产地
    resp = client.get("/api/v1/teas", params={"keyword": "福建"})
    items = resp.json()["data"]["items"]
    assert len(items) >= 3
    assert all("福建" in t["origin"] for t in items)


def test_list_keyword_too_long_returns_40000():
    resp = client.get("/api/v1/teas", params={"keyword": "茶" * 51})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40000


def test_list_sort_favorite_desc():
    resp = client.get("/api/v1/teas", params={"sort": "favorite", "page_size": 50})
    items = resp.json()["data"]["items"]
    counts = [t["favorite_count"] for t in items]
    assert counts == sorted(counts, reverse=True)


def test_list_invalid_enum_returns_40000():
    for params in (
        {"category": "black"},
        {"season": "早春"},
        {"sort": "relevance"},
    ):
        resp = client.get("/api/v1/teas", params=params)
        assert resp.status_code == 400, params
        assert resp.json()["code"] == 40000


def test_list_non_int_page_remapped_to_40000():
    resp = client.get("/api/v1/teas", params={"page": "abc"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40000


# ===== 下架茶品（FR-6.3）：列表/搜索隐藏，详情 40401 =====


def test_off_shelf_tea_hidden_and_detail_40401():
    tea_id = _create_off_shelf_tea()
    try:
        # 列表不出现（含关键词搜索）
        resp = client.get("/api/v1/teas", params={"keyword": "测试下架茶"})
        assert resp.json()["data"]["items"] == []
        # 详情 40401
        resp = client.get(f"/api/v1/teas/{tea_id}")
        assert resp.status_code == 404
        assert resp.json()["code"] == 40401
        assert resp.json()["message"] == "该茶品暂不可用"
        # 随机发现不会抽到下架茶（多次抽样）
        for _ in range(5):
            data = client.get("/api/v1/teas/random").json()["data"]
            assert data is None or data["id"] != tea_id
    finally:
        _cleanup_tea(tea_id)


# ===== 4.2.2 七大茶类计数 =====


def test_categories_fixed_seven_in_order():
    resp = client.get("/api/v1/teas/categories")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert [c["category"] for c in data] == [
        "green",
        "white",
        "yellow",
        "red",
        "oolong",
        "dark",
        "reprocessed",
    ]
    count_map = {c["category"]: c["count"] for c in data}
    assert count_map["green"] >= 1
    assert all(c >= 0 for c in count_map.values())


# ===== 4.2.3 产地选项 =====


def test_origins_province_derived_and_sorted():
    resp = client.get("/api/v1/teas/origins")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    # 省级名称不含空格（从 origin 第一段派生）
    assert all(" " not in o["origin"] for o in data)
    provinces = {o["origin"]: o["count"] for o in data}
    # 种子数据含 3 款福建茶（白毫银针/正山小种/大红袍）
    assert provinces.get("福建", 0) >= 3
    # count DESC 排序
    counts = [o["count"] for o in data]
    assert counts == sorted(counts, reverse=True)


# ===== 4.2.4 热门推荐 =====


def test_hot_default_and_limit_clamping():
    resp = client.get("/api/v1/teas/hot")
    data = resp.json()["data"]
    assert 1 <= len(data) <= 8
    counts = [t["favorite_count"] for t in data]
    assert counts == sorted(counts, reverse=True)
    # limit 生效与夹取
    assert len(client.get("/api/v1/teas/hot", params={"limit": 3}).json()["data"]) == 3
    assert len(client.get("/api/v1/teas/hot", params={"limit": 999}).json()["data"]) <= 20
    # limit 非整数 → 40000
    resp = client.get("/api/v1/teas/hot", params={"limit": "abc"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40000


# ===== 4.2.5 随机发现 =====


def test_random_returns_detail_or_null_and_excludes():
    resp = client.get("/api/v1/teas/random")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data is not None
    # 返回 TeaDetail 结构（含四大感官与扁平 tips_* 键）
    for key in (
        "shape_desc",
        "soup_desc",
        "aroma_desc",
        "taste_desc",
        "tips_history",
        "tips_suitable",
        "tips_misconception",
        "tips_official_note",
    ):
        assert key in data
    # exclude_id 生效
    excluded = data["id"]
    data = client.get("/api/v1/teas/random", params={"exclude_id": excluded}).json()["data"]
    if data is not None:  # 仅剩 1 款时为 null，契约允许
        assert data["id"] != excluded
    # exclude_id 非整数 → 40000
    resp = client.get("/api/v1/teas/random", params={"exclude_id": "abc"})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40000


# ===== 4.2.6 茶品详情 =====


def test_detail_full_fields_and_tips_flattened():
    resp = client.get("/api/v1/teas/1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "西湖龙井"
    assert data["category"] == "green"
    assert data["is_active"] is True
    assert data["fermentation"] == "不发酵"
    assert data["shape_desc"]
    # 种子茶 1 四块小贴士齐全（扁平化派生字段）
    assert data["tips_history"]
    assert data["tips_suitable"]
    assert data["tips_misconception"]
    assert data["tips_official_note"]
    # 时间字段 ISO8601 带 Z
    assert data["created_at"].endswith("Z")
    assert data["updated_at"].endswith("Z")


def test_detail_not_found_returns_40400():
    resp = client.get("/api/v1/teas/999999")
    assert resp.status_code == 404
    assert resp.json()["code"] == 40400
    assert resp.json()["data"] is None
