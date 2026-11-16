"""批次五后端测试

用例：CONT-01 ~ CONT-05 冒烟 + CONT-06 ~ CONT-11 扩展（CRUD + meta 校验）
CONT-12 ~ CONT-16：内容列表关键词搜索（GET /contents?keyword=）
"""

import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def _admin() -> TestClient:
    """登录管理员并返回带 session cookie 的 client。"""
    c = TestClient(app)
    resp = c.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return c


def test_cont_01_list_types():
    """游客访问 /content-types -> 返回 5 板块。"""
    r = client.get("/api/v1/content-types")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == 0
    types = d["data"]
    assert len(types) == 5
    codes = {t["code"] for t in types}
    assert codes == {"teaware", "origin", "culture", "brand", "knowledge"}


def test_cont_02_list_contents_public():
    """游客访问 /contents -> 返回种子数据条目。"""
    r = client.get("/api/v1/contents?type=teaware")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == 0
    assert d["data"]["total"] >= 2  # 种子：盖碗 + 紫砂壶


def test_cont_03_invalid_type_rejected():
    """非法 type 参数 -> 400/40000。"""
    r = client.get("/api/v1/contents?type=INVALID")
    assert r.status_code == 400
    assert r.json()["code"] == 40000


def test_cont_04_item_not_found():
    """不存在的条目 -> 404/40460。"""
    r = client.get("/api/v1/contents/9999")
    assert r.status_code == 404
    assert r.json()["code"] == 40460


def test_cont_05_admin_auth_required():
    """管理员端点未登录 -> 401。"""
    r = client.get("/api/v1/admin/contents")
    assert r.status_code == 401

    r = client.post("/api/v1/admin/contents", json={})
    assert r.status_code == 401

    r = client.put("/api/v1/admin/contents/1", json={})
    assert r.status_code == 401

    r = client.delete("/api/v1/admin/contents/1")
    assert r.status_code == 401


# === 扩展用例 CONT-06 ~ CONT-11 ===


def test_cont_06_meta_validation_rejects_invalid_structure():
    """meta JSON 校验：错误结构 → 400/40000。"""
    admin = _admin()

    # extra 字段（Schema extra=forbid + 校验层双重）
    r = admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "origin",
            "title": "测试产地",
            "summary": "测试",
            "body": "测试正文",
            "meta": {"province": "浙江", "region": "杭州", "unknown": "field"},
            "sort_order": 10,
        },
    )
    assert r.status_code == 400, r.text
    assert r.json()["code"] == 40000

    # culture.tags 不是 list[str]
    r = admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "culture",
            "title": "测试文化",
            "summary": "测试",
            "body": "测试正文",
            "meta": {"era": "唐代", "tags": "陆羽,茶经"},  # 应该是数组
            "sort_order": 10,
        },
    )
    assert r.status_code == 400, r.text
    assert r.json()["code"] == 40000

    # knowledge.difficulty 枚举超出
    r = admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "knowledge",
            "title": "测试知识",
            "summary": "测试",
            "body": "测试正文",
            "meta": {"subtype": "standard", "difficulty": "master"},  # 非法枚举值
            "sort_order": 10,
        },
    )
    assert r.status_code == 400, r.text
    assert r.json()["code"] == 40000

    # brand.website URL 格式错误
    r = admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "brand",
            "title": "测试品牌",
            "summary": "测试",
            "body": "测试正文",
            "meta": {"brand_origin": "福建", "website": "not-a-url"},
            "sort_order": 10,
        },
    )
    assert r.status_code == 400, r.text
    assert r.json()["code"] == 40000

    # 非法 type_code
    r = admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "INVALID",
            "title": "测试",
            "summary": "测试",
            "body": "测试正文",
            "meta": {},
            "sort_order": 10,
        },
    )
    assert r.status_code == 400, r.text
    assert r.json()["code"] == 40000


def test_cont_07_admin_crud_full_lifecycle():
    """管理员 CRUD 全链路：创建 → 后台详情 → 更新 → 软删 → 前台不可见。"""
    admin = _admin()

    # 创建
    created = admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "knowledge",
            "title": "测试知识条目-CRUD",
            "summary": "CRUD 全链路测试",
            "body": "这是一条用于 CRUD 全链路测试的正文内容。",
            "meta": {"subtype": "standard", "difficulty": "beginner"},
            "sort_order": 99,
        },
    )
    assert created.status_code == 200
    assert created.json()["code"] == 0
    item_id = created.json()["data"]["id"]
    assert created.json()["data"]["is_active"] is True

    # 后台详情（刚创建时）
    detail = admin.get(f"/api/v1/admin/contents/{item_id}")
    assert detail.status_code == 200
    assert detail.json()["code"] == 0
    d = detail.json()["data"]
    assert d["title"] == "测试知识条目-CRUD"
    assert d["type_code"] == "knowledge"
    assert d["is_active"] is True

    # 更新（改标题 + is_active 改为 False）
    updated = admin.put(
        f"/api/v1/admin/contents/{item_id}",
        json={
            "title": "测试知识条目-CRUD-已更新",
            "summary": "更新后摘要",
            "body": "更新后的正文。",
            "meta": {"subtype": "brewing", "difficulty": "intermediate"},
            "sort_order": 98,
            "is_active": False,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["code"] == 0
    assert updated.json()["data"]["title"] == "测试知识条目-CRUD-已更新"
    assert updated.json()["data"]["is_active"] is False

    # 前台列表过滤：软删后不可见
    public = client.get("/api/v1/contents?type=knowledge")
    assert public.status_code == 200
    public_titles = [i["title"] for i in public.json()["data"]["items"]]
    assert "测试知识条目-CRUD-已更新" not in public_titles

    # 后台列表：含下架
    admin_list = admin.get("/api/v1/admin/contents", params={"is_active": "false"})
    assert admin_list.status_code == 200
    admin_ids = [i["id"] for i in admin_list.json()["data"]["items"]]
    assert item_id in admin_ids

    # 前台详情：软删后 404
    public_detail = client.get(f"/api/v1/contents/{item_id}")
    assert public_detail.status_code == 404
    assert public_detail.json()["code"] == 40460


def test_cont_08_soft_delete_and_recover():
    """软删后可通过 PUT is_active=True 恢复。"""
    admin = _admin()

    # 创建
    created = admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "teaware",
            "title": "软删恢复测试",
            "summary": "测试软删后恢复",
            "body": "正文",
            "meta": {"material": "玻璃", "volume": "180ml", "category": "品茗杯"},
            "sort_order": 99,
        },
    )
    item_id = created.json()["data"]["id"]

    # 软删
    deleted = admin.delete(f"/api/v1/admin/contents/{item_id}")
    assert deleted.status_code == 200
    assert deleted.json()["code"] == 0

    # 后台详情：is_active=False
    detail = admin.get(f"/api/v1/admin/contents/{item_id}")
    assert detail.json()["data"]["is_active"] is False

    # 前台不可见
    assert client.get(f"/api/v1/contents/{item_id}").status_code == 404

    # 恢复
    recovered = admin.put(
        f"/api/v1/admin/contents/{item_id}",
        json={
            "title": "软删恢复测试",
            "summary": "测试软删后恢复",
            "body": "正文",
            "meta": {"material": "玻璃", "volume": "180ml", "category": "品茗杯"},
            "sort_order": 99,
            "is_active": True,
        },
    )
    assert recovered.json()["data"]["is_active"] is True

    # 前台可见
    assert client.get(f"/api/v1/contents/{item_id}").status_code == 200

    # 清理：软删
    admin.delete(f"/api/v1/admin/contents/{item_id}")


def test_cont_09_get_admin_detail_not_found():
    """后台详情：不存在的条目 → 404/40460。"""
    admin = _admin()
    r = admin.get("/api/v1/admin/contents/99999")
    assert r.status_code == 404
    assert r.json()["code"] == 40460


def test_cont_10_admin_list_filter_by_type():
    """后台列表：按板块筛选。"""
    admin = _admin()

    # 创建一个 teaware 和一个 knowledge
    for tc, title in [("teaware", "筛选用茶具"), ("knowledge", "筛选用知识")]:
        admin.post(
            "/api/v1/admin/contents",
            json={
                "type_code": tc,
                "title": title,
                "summary": "筛选测试",
                "body": "正文",
                "meta": (
                    {"material": "陶瓷", "volume": "200ml", "category": "盖碗"}
                    if tc == "teaware"
                    else {"subtype": "brewing", "difficulty": "beginner"}
                ),
                "sort_order": 99,
            },
        )

    r = admin.get("/api/v1/admin/contents", params={"type": "teaware"})
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert items  # 有数据
    assert all(i["type_code"] == "teaware" for i in items)


def test_cont_11_crud_records_operation_log():
    """后台 CRUD 操作应写入 operation_logs。"""
    from app.core.database import SessionLocal
    from app.models.content import ContentItem
    from app.models.operation_log import OperationLog

    admin = _admin()

    before_count = SessionLocal().query(OperationLog).count()
    admin.post(
        "/api/v1/admin/contents",
        json={
            "type_code": "culture",
            "title": "operation_log 测试条目",
            "summary": "log 测试",
            "body": "正文",
            "meta": {"era": "现代", "tags": ["测试"]},
            "sort_order": 99,
        },
    )
    after_count = SessionLocal().query(OperationLog).count()
    assert after_count > before_count  # 至少新增一条 create_content

    # 清理
    db = SessionLocal()
    item = db.query(ContentItem).filter(ContentItem.title == "operation_log 测试条目").first()
    if item:
        item.is_active = 0
        db.commit()
    db.close()


# === 扩展用例 CONT-12 ~ CONT-16：关键词搜索 ===


def _public_contents(**params) -> dict:
    """调用前台内容列表，断言成功并返回 data 分页结构。"""
    r = client.get("/api/v1/contents", params=params)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 0
    return body["data"]


def _create_content(admin: TestClient, *, type_code: str, title: str, summary: str) -> int:
    """创建一条用于搜索校验的条目，返回 id。"""
    payload = {
        "type_code": type_code,
        "title": title,
        "summary": summary,
        "body": "关键词搜索测试正文",
        "meta": (
            {"material": "陶瓷", "volume": "150ml", "category": "盖碗"}
            if type_code == "teaware"
            else {"subtype": "standard", "difficulty": "beginner"}
        ),
        "sort_order": 99,
    }
    r = admin.post("/api/v1/admin/contents", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["code"] == 0
    return r.json()["data"]["id"]


def test_cont_12_keyword_matches_title():
    """keyword 命中标题。"""
    admin = _admin()
    marker = f"kw-title-{uuid.uuid4().hex[:8]}"
    item_id = _create_content(
        admin, type_code="knowledge", title=f"{marker} 标题命中", summary="摘要不含搜索标记"
    )
    try:
        data = _public_contents(keyword=marker)
        assert data["total"] == 1
        assert data["items"][0]["id"] == item_id
    finally:
        admin.delete(f"/api/v1/admin/contents/{item_id}")


def test_cont_13_keyword_matches_summary():
    """keyword 命中摘要。"""
    admin = _admin()
    marker = f"kw-summary-{uuid.uuid4().hex[:8]}"
    item_id = _create_content(
        admin, type_code="knowledge", title="标题不含搜索标记", summary=f"{marker} 仅摘要命中"
    )
    try:
        data = _public_contents(keyword=marker)
        assert data["total"] == 1
        assert data["items"][0]["id"] == item_id
    finally:
        admin.delete(f"/api/v1/admin/contents/{item_id}")


def test_cont_14_keyword_no_match_returns_empty():
    """keyword 无命中 → 空列表且 code=0。"""
    data = _public_contents(keyword="zzz-不存在的关键词-zzz")
    assert data["total"] == 0
    assert data["items"] == []


def test_cont_15_keyword_wildcards_are_literal():
    """keyword 为 % / _ 时按字面量匹配，不得返回全表。"""
    baseline = _public_contents()["total"]
    assert baseline > 0
    for kw in ("%", "_"):
        data = _public_contents(keyword=kw)
        assert data["total"] < baseline, kw


def test_cont_16_keyword_and_type_combined():
    """keyword 与 type 同时生效（AND）。"""
    admin = _admin()
    marker = f"kw-and-{uuid.uuid4().hex[:8]}"
    teaware_id = _create_content(
        admin, type_code="teaware", title=f"{marker} 茶具条目", summary="搜索标记在标题"
    )
    knowledge_id = _create_content(
        admin, type_code="knowledge", title=f"{marker} 知识条目", summary="搜索标记在标题"
    )
    try:
        data = _public_contents(keyword=marker, type="teaware")
        assert data["total"] == 1
        assert data["items"][0]["id"] == teaware_id

        data = _public_contents(keyword=marker, type="knowledge")
        assert data["total"] == 1
        assert data["items"][0]["id"] == knowledge_id

        data = _public_contents(keyword=marker, type="culture")
        assert data["total"] == 0
    finally:
        admin.delete(f"/api/v1/admin/contents/{teaware_id}")
        admin.delete(f"/api/v1/admin/contents/{knowledge_id}")
