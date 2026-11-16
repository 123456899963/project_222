from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # === 基础 ===
    APP_NAME: str = "茶·图鉴 API"
    # 默认关闭调试，避免未配置 .env 时把 SQL 与堆栈写入日志（SECURITY S-30）
    DEBUG: bool = False

    # === 数据库 ===
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    # 不内置默认密码；由 .env 或环境变量注入
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "tea_guide"

    # === 会话 ===
    # 不内置默认密钥；必须注入随机值，否则拒绝启动（SECURITY S-31）
    SECRET_KEY: str = ""
    SESSION_EXPIRE_DAYS: int = 30  # PRD FR-4.3：30 天 Cookie 会话
    # 会话 Cookie 的 Secure 标记；未设置时由 DEBUG 推导（生产默认 True）。
    # 纯 HTTP 演示部署必须显式设为 false，否则浏览器不会回传 Cookie。
    COOKIE_SECURE: bool | None = None

    # === 登录失败锁定（S14 / SECURITY S-33）===
    # 统计窗口内，同一用户名或同一 IP 失败达到阈值即拒绝登录，窗口滚动过期后解锁
    LOGIN_MAX_FAILURES: int = 5
    LOGIN_WINDOW_MINUTES: int = 15
    LOGIN_ATTEMPT_RETENTION_HOURS: int = 24

    # === CORS ===
    # 开发期允许的前端源；生产经 Nginx 同域反代后可改为 ["http://localhost"]
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # === 文件 ===
    UPLOAD_DIR: Path = Path("uploads")
    MAX_UPLOAD_SIZE_MB: int = 5
    # 视频上传（ADR-0003 / PRD S5）：≤3 分钟、≤50 MB、仅 MP4/MOV
    MAX_VIDEO_SIZE_MB: int = 50
    MAX_VIDEO_DURATION_SECONDS: int = 180
    # 请求体上限（对齐 TEST_PLAN DEF-02 的网关 6MB 限制）
    MAX_REQUEST_BODY_MB: int = 6
    # 视频端点专属请求体上限（50 MB 文件 + multipart 开销余量）
    MAX_VIDEO_REQUEST_BODY_MB: int = 52

    # === 管理员初始账号 ===
    ADMIN_USERNAME: str = "admin"
    # 不在代码中内置默认密码（SECURITY S-31）；开发/测试由 .env 注入
    ADMIN_PASSWORD: str = ""

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        """缺少签名密钥时直接拒绝启动，避免用可预测密钥签发会话。

        生成方式：python -c "import secrets; print(secrets.token_urlsafe(48))"
        """
        if not self.SECRET_KEY.strip():
            raise ValueError("SECRET_KEY 未配置：请在 .env 或环境变量中注入随机密钥")
        return self

    @property
    def cookie_secure(self) -> bool:
        """Cookie Secure 的最终取值：显式配置优先，否则 DEBUG 关闭时启用。"""
        return not self.DEBUG if self.COOKIE_SECURE is None else self.COOKIE_SECURE

    @property
    def DATABASE_URL(self) -> str:
        # charset=utf8mb4 支持完整中文 + emoji
        # 排序规则在建库时指定（utf8mb4_unicode_ci，兼容 MySQL 5.7 / 8.0），
        # 见 docs/architecture/TECH_STACK.md §6
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
