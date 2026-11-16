import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine  # noqa: F401 —— 开发期建表开关使用
from app.core.response import ok, register_exception_handlers
from app.routers import (
    admin,
    auth,
    contents,
    contributions,
    favorites,
    lists,
    me,
    shares,
    teas,
    tips,
)

# 初始化数据库表（开发期用，生产环境走 Alembic 迁移）
# Base.metadata.create_all(bind=engine)


def create_app() -> FastAPI:
    app = FastAPI(
        title="茶·图鉴 API",
        description="七大茶类结构化知识库平台 — MVP 后端",
        version="0.1.0",
    )

    # 请求体上限：先注册，后注册的 CORS 作为最外层，保证 413 响应也带跨域头。
    # 对齐 TEST_PLAN DEF-02 / S-20：网关 6MB，应用层兜底，避免超大请求触发 500。
    @app.middleware("http")
    async def limit_request_body(request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
            except ValueError:
                size = 0
            # 视频端点单独放宽（ADR-0003：≤50 MB），其余端点沿用 6 MB 网关限制
            is_video_upload = request.url.path.rstrip("/").endswith("/admin/media/video")
            limit_mb = (
                settings.MAX_VIDEO_REQUEST_BODY_MB
                if is_video_upload
                else settings.MAX_REQUEST_BODY_MB
            )
            if size > limit_mb * 1024 * 1024:
                return JSONResponse(
                    status_code=413,
                    content={"code": 41300, "message": "请求体过大", "data": None},
                )
        return await call_next(request)

    # CORS 配置（开发期兜底；生产经 Nginx 同域反代后跨域消失）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册全局异常处理器（业务异常 → 统一响应体，HTTP status = code // 100）
    register_exception_handlers(app)

    # 生产环境关闭 Secure 仅适用于纯 HTTP 演示；显式告警，避免登录后 Cookie 不落盘
    if not settings.DEBUG and not settings.cookie_secure:
        logging.getLogger(__name__).warning(
            "COOKIE_SECURE=false 且 DEBUG=false：仅适用于纯 HTTP 演示；"
            "生产 HTTPS 请设置 COOKIE_SECURE=true"
        )

    # 注册路由
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
    app.include_router(me.router, prefix="/api/v1/me", tags=["我的"])
    app.include_router(teas.router, prefix="/api/v1/teas", tags=["茶品"])
    app.include_router(tips.router, prefix="/api/v1/tips", tags=["小贴士"])
    app.include_router(favorites.router, prefix="/api/v1/favorites", tags=["收藏"])
    app.include_router(lists.router, prefix="/api/v1/lists", tags=["清单"])
    app.include_router(shares.router, prefix="/api/v1/shares", tags=["分享"])
    app.include_router(contributions.router, prefix="/api/v1/contributions", tags=["贡献"])
    app.include_router(contents.router, prefix="/api/v1", tags=["内容板块"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理员"])

    # 静态挂载 uploads 目录（图片存储；目录与上传服务保持一致）
    uploads_dir = Path(settings.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.get("/api/v1/health")
    def health():
        return ok({"status": "ok"})

    return app


app = create_app()
