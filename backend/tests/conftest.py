"""pytest 全局配置：强制测试使用独立测试库，禁止读写开发库。

优先级：
1. 环境变量 ``DATABASE_URL_TEST``（推荐 CI/本地显式指定）；
2. 未指定时默认使用 ``tea_guide_test``。

必须在导入 ``app.*`` 之前完成环境变量设置，因为 ``settings`` 在模块导入时即实例化。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.parse import unquote


def _use_test_database() -> None:
    # 上传目录同样隔离，避免测试的清理逻辑误删开发环境的真实图片
    os.environ["UPLOAD_DIR"] = str(Path(tempfile.gettempdir()) / "tea_guide_test_uploads")

    # 测试固定使用 http://testserver，必须保持 DEBUG=true，
    # 否则会话 Cookie 带 Secure 标记不会被回传，全部鉴权用例会 401。
    os.environ.setdefault("DEBUG", "true")
    # 测试环境注入专用签名密钥（生产环境禁止使用）
    os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-production")

    test_url = os.environ.get("DATABASE_URL_TEST")
    if test_url:
        from sqlalchemy.engine import make_url

        url = make_url(test_url)
        os.environ["MYSQL_HOST"] = url.host or "localhost"
        os.environ["MYSQL_PORT"] = str(url.port or 3306)
        os.environ["MYSQL_USER"] = unquote(url.username or "root")
        os.environ["MYSQL_PASSWORD"] = unquote(url.password or "")
        os.environ["MYSQL_DATABASE"] = url.database or "tea_guide_test"
    else:
        os.environ["MYSQL_DATABASE"] = "tea_guide_test"

    # 注意：不要覆盖 DEBUG。会话 Cookie 的 Secure 标记由 DEBUG 派生，
    # 测试使用 http://testserver，Secure Cookie 不会被回传，会导致全部鉴权用例 401。


_use_test_database()

import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    """双保险：任何情况下都不允许测试指向非 *_test 库。"""
    if not settings.MYSQL_DATABASE.endswith("_test"):
        pytest.exit(
            f"测试库配置错误：当前库为 {settings.MYSQL_DATABASE}，必须使用 *_test 库",
            returncode=1,
        )


@pytest.fixture(autouse=True)
def _reset_login_attempts():
    """S14：每个用例前清空登录失败记录。

    TestClient 的客户端 IP 固定为 testclient，若不清空会跨用例累计并误触发
    IP 维度锁定；该清理只触碰 login_attempts 表，不影响其他用例数据。
    """
    from app.core.database import SessionLocal
    from app.models.login_attempt import LoginAttempt

    db = SessionLocal()
    try:
        db.query(LoginAttempt).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    yield
