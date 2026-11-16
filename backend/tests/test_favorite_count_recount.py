"""收藏数重算脚本测试：以真实 favorite_items 为准修正冗余计数。"""

import time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.tea import Tea
from app.repositories import user_repo
from app.scripts.recount_favorite_counts import recount


def _unique_username() -> str:
    return f"recount{int(time.time() * 1000000) % 100000000}"


def test_recount_uses_distinct_users_and_ignores_stale_value():
    username = _unique_username()
    db = SessionLocal()
    try:
        tea = Tea(
            name=f"重算测试茶{int(time.time() * 1000000) % 100000000}",
            category="green",
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
        tea_id = tea.id
    finally:
        db.close()

    try:
        client = TestClient(app)
        assert (
            client.post(
                "/api/v1/auth/register",
                json={"username": username, "password": "tea2026"},
            ).status_code
            == 200
        )
        assert client.post(f"/api/v1/favorites/{tea_id}").status_code == 200

        db = SessionLocal()
        try:
            tea = db.get(Tea, tea_id)
            assert tea.favorite_count == 1  # 收藏时已 +1
            tea.favorite_count = 999  # 模拟历史脏数据
            db.commit()

            changed, total = recount(db)
            db.refresh(tea)
            assert tea.favorite_count == 1
            assert changed >= 1
            assert total >= 1
        finally:
            db.close()
    finally:
        db = SessionLocal()
        try:
            user = user_repo.get_by_username(db, username)
            if user is not None:
                db.delete(user)
            tea = db.get(Tea, tea_id)
            if tea is not None:
                db.delete(tea)
            db.commit()
        finally:
            db.close()
