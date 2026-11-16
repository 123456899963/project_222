"""防御性测试（对齐 TEST_PLAN TC-DEF-01 / TC-DEF-03）

DEF-01：非法请求一律映射为 400/40000，不暴露框架内部细节。
DEF-03：未捕获异常返回 500/50000，响应体不含堆栈 / SQL / 表名，且服务可恢复。
"""

from __future__ import annotations

import logging
import time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.repositories import user_repo


def _unique_username(prefix: str = "defuser") -> str:
    return f"{prefix}{int(time.time() * 1000000) % 100000000}"


def _assert_40000(resp) -> None:
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body == {"code": 40000, "message": "参数校验失败", "data": None}


def test_def_01_illegal_requests_map_to_40000():
    client = TestClient(app)

    # 1) 畸形 JSON
    _assert_40000(
        client.post(
            "/api/v1/auth/login",
            content="{",
            headers={"Content-Type": "application/json"},
        )
    )

    # 2) 非 JSON Content-Type
    _assert_40000(
        client.post(
            "/api/v1/auth/login",
            content='{"username": "admin", "password": "admin123"}',
            headers={"Content-Type": "text/plain"},
        )
    )

    # 3) 查询参数类型错误（page_size 非整数）
    _assert_40000(client.get("/api/v1/teas", params={"page_size": "abc"}))

    # 4) 越权字段注入：注册时携带 role 必须被拒绝且不落库
    username = _unique_username()
    _assert_40000(
        client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "tea2026", "role": "admin"},
        )
    )
    db = SessionLocal()
    try:
        assert user_repo.get_by_username(db, username) is None
    finally:
        db.close()


def test_def_03_unhandled_exception_returns_generic_500(monkeypatch, caplog):
    from app.routers import teas as teas_router

    def _boom(*args, **kwargs):
        raise RuntimeError("internal detail: SELECT * FROM users WHERE password_hash='x'")

    with monkeypatch.context() as m:
        m.setattr(teas_router.teas_service, "list_teas", _boom)
        with caplog.at_level(logging.ERROR):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/api/v1/teas")

    assert resp.status_code == 500
    assert resp.json() == {"code": 50000, "message": "服务器内部错误", "data": None}

    # 响应体不得泄露异常类型、SQL、表名或堆栈
    for leaked in ("RuntimeError", "SELECT", "users", "password_hash", "Traceback"):
        assert leaked not in resp.text

    # 服务端必须记录堆栈，便于排查
    assert any("未处理异常" in record.getMessage() for record in caplog.records)

    # 异常结束后服务应恢复正常
    assert TestClient(app).get("/api/v1/teas").status_code == 200
