"""部署配置与后端上限的一致性检查（TEST_PLAN DEF-02）。

这些断言不需要数据库，但沿用 conftest 的测试库环境初始化。
"""

from pathlib import Path

from app.core.config import settings

ROOT = Path(__file__).resolve().parents[2]


def test_nginx_video_endpoint_allows_52m() -> None:
    nginx = (ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")

    # 全站默认仍为 6MB
    assert "client_max_body_size 6m;" in nginx

    marker = "location = /api/v1/admin/media/video {"
    assert marker in nginx
    video_block = nginx.split(marker, 1)[1].split("}", 1)[0]
    assert "client_max_body_size 52m;" in video_block


def test_backend_video_limits_are_consistent() -> None:
    # 文件上限 50MB，请求体上限需留 multipart 余量且不小于文件上限
    assert settings.MAX_VIDEO_SIZE_MB == 50
    assert settings.MAX_VIDEO_REQUEST_BODY_MB >= settings.MAX_VIDEO_SIZE_MB
    assert settings.MAX_VIDEO_REQUEST_BODY_MB == 52
    # 非视频端点仍保持 6MB
    assert settings.MAX_REQUEST_BODY_MB == 6
