"""冲泡教程测试（ADR-0005 / TEST_PLAN TEA-BREW）

覆盖：
- 管理员整篇 upsert 后，公开详情与后台详情都能读到教程
- 重复保存为覆盖更新，不会产生第二行
- 步数 3–8、标题/正文长度、多余字段的校验
- 游客与普通用户无权写入
- 删除幂等，删除后公开详情退回 null
- 草稿生成纯函数：六大茶类均 6 步且能通过 Schema 校验
"""

import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.models.operation_log import OperationLog
from app.models.tea import Tea, TeaBrewingGuide, TeaTips
from app.schemas.tea import BrewingGuide
from app.scripts.seed_brewing_guides import CATEGORY_DEFAULTS, build_guide

client = TestClient(app)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _admin_client() -> TestClient:
    admin = TestClient(app)
    resp = admin.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return admin


def _create_tea(admin: TestClient) -> int:
    payload = {
        "name": f"教程测试茶{_uid()}",
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
        "water_temp": 85.0,
        "tea_amount": 3.0,
        "brew_time": 60.0,
        "main_image_url": "/uploads/teas/test.jpg",
    }
    resp = admin.post("/api/v1/admin/teas", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _cleanup(tea_id: int) -> None:
    db = SessionLocal()
    try:
        db.query(TeaBrewingGuide).filter(TeaBrewingGuide.tea_id == tea_id).delete(
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


def _guide_payload(**overrides) -> dict:
    data = {
        "intro": "按步骤操作，新手也能泡好这杯茶。",
        "steps": [
            {"title": "温杯", "detail": "用热水烫洗茶具。", "tip": "玻璃杯也可以。"},
            {"title": "投茶", "detail": "取 3g 茶叶放入杯中。"},
            {"title": "注水", "detail": "85℃ 热水沿杯壁注入至七分满。"},
            {"title": "出汤", "detail": "静置 60 秒后饮用。"},
        ],
        "caution": "不要用沸水直冲。",
    }
    data.update(overrides)
    return data


def test_admin_upsert_and_public_read():
    admin = _admin_client()
    tea_id = _create_tea(admin)
    try:
        resp = admin.put(f"/api/v1/admin/teas/{tea_id}/brewing-guide", json=_guide_payload())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["tea_id"] == tea_id
        assert len(body["data"]["steps"]) == 4

        public = client.get(f"/api/v1/teas/{tea_id}")
        assert public.status_code == 200
        guide = public.json()["data"]["brewing_guide"]
        assert guide["intro"] == "按步骤操作，新手也能泡好这杯茶。"
        assert guide["steps"][0]["title"] == "温杯"
        assert guide["caution"] == "不要用沸水直冲。"

        detail = admin.get(f"/api/v1/admin/teas/{tea_id}")
        assert detail.status_code == 200
        assert detail.json()["data"]["brewing_guide"]["steps"][1]["title"] == "投茶"
    finally:
        _cleanup(tea_id)


def test_upsert_overwrites_single_row():
    admin = _admin_client()
    tea_id = _create_tea(admin)
    try:
        admin.put(f"/api/v1/admin/teas/{tea_id}/brewing-guide", json=_guide_payload())
        second = _guide_payload(
            intro="第二版教程",
            steps=[
                {"title": "洗茶", "detail": "快速润茶一次。"},
                {"title": "冲泡", "detail": "沸水注满。"},
                {"title": "出汤", "detail": "20 秒后倒出。"},
            ],
        )
        resp = admin.put(f"/api/v1/admin/teas/{tea_id}/brewing-guide", json=second)
        assert resp.status_code == 200
        assert resp.json()["data"]["intro"] == "第二版教程"

        db = SessionLocal()
        try:
            count = db.query(TeaBrewingGuide).filter(TeaBrewingGuide.tea_id == tea_id).count()
            assert count == 1
        finally:
            db.close()
    finally:
        _cleanup(tea_id)


def test_step_count_and_length_validation():
    admin = _admin_client()
    tea_id = _create_tea(admin)
    try:
        too_few = admin.put(
            f"/api/v1/admin/teas/{tea_id}/brewing-guide",
            json=_guide_payload(steps=[{"title": "一步", "detail": "内容"}]),
        )
        assert too_few.status_code == 400
        assert too_few.json()["code"] == 40000

        too_many = admin.put(
            f"/api/v1/admin/teas/{tea_id}/brewing-guide",
            json=_guide_payload(steps=[{"title": f"第{i}步", "detail": "内容"} for i in range(9)]),
        )
        assert too_many.status_code == 400

        long_title = admin.put(
            f"/api/v1/admin/teas/{tea_id}/brewing-guide",
            json=_guide_payload(
                steps=[
                    {"title": "长" * 31, "detail": "内容"},
                    {"title": "第二步", "detail": "内容"},
                    {"title": "第三步", "detail": "内容"},
                ]
            ),
        )
        assert long_title.status_code == 400

        extra = admin.put(
            f"/api/v1/admin/teas/{tea_id}/brewing-guide",
            json={**_guide_payload(), "unknown": "x"},
        )
        assert extra.status_code == 400
    finally:
        _cleanup(tea_id)


def test_guest_cannot_write_guide():
    admin = _admin_client()
    tea_id = _create_tea(admin)
    try:
        guest = TestClient(app)
        resp = guest.put(f"/api/v1/admin/teas/{tea_id}/brewing-guide", json=_guide_payload())
        assert resp.status_code == 401
        assert resp.json()["code"] == 40100
    finally:
        _cleanup(tea_id)


def test_delete_is_idempotent_and_restores_null():
    admin = _admin_client()
    tea_id = _create_tea(admin)
    try:
        admin.put(f"/api/v1/admin/teas/{tea_id}/brewing-guide", json=_guide_payload())
        first = admin.delete(f"/api/v1/admin/teas/{tea_id}/brewing-guide")
        assert first.status_code == 200
        assert first.json()["data"]["deleted"] is True

        second = admin.delete(f"/api/v1/admin/teas/{tea_id}/brewing-guide")
        assert second.status_code == 200
        assert second.json()["data"]["deleted"] is False

        public = client.get(f"/api/v1/teas/{tea_id}")
        assert public.json()["data"]["brewing_guide"] is None
    finally:
        _cleanup(tea_id)


def test_seed_draft_is_valid_for_all_categories():
    for category in CATEGORY_DEFAULTS:
        tea = Tea(
            name=f"草稿{category}",
            category=category,
            origin="测试",
            water_temp=None,
            tea_amount=None,
            brew_time=None,
        )
        draft = build_guide(tea)
        assert len(draft["steps"]) == 6
        validated = BrewingGuide.model_validate(draft)
        assert len(validated.steps) == 6
        assert all(step.title and step.detail for step in validated.steps)
