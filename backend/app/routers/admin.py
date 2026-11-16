"""管理员后台路由（API_CONTRACT §4.6）

红线：
- 所有端点先鉴权后校验参数：router 级 Depends(get_admin_user) 在最前执行
- 前端路由守卫仅是体验层，不构成安全边界（SECURITY S-11）
- 不提供用户管理/审核队列外的日志写入/批量导入/物理删除
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.auth_deps import get_admin_user
from app.core.database import get_db
from app.core.response import ok
from app.schemas.admin import TipsUpdateRequest
from app.schemas.content import ContentCreateRequest, ContentUpdateRequest
from app.schemas.contribution import RejectRequest
from app.schemas.tea import (
    BrewingGuideUpdateRequest,
    TeaCreateRequest,
    TeaMediaCreateRequest,
    TeaUpdateRequest,
)
from app.services import admin as admin_service
from app.services import contents as content_service
from app.services import contributions as contribution_service
from app.services import tea_media as tea_media_service

router = APIRouter(dependencies=[Depends(get_admin_user)])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """A2 仪表盘统计（API_CONTRACT §4.6.8）。"""
    return ok(admin_service.stats(db).model_dump(mode="json"))


@router.get("/operation-logs")
def list_operation_logs(
    page: int = Query(1),
    page_size: int = Query(admin_service.DEFAULT_LOG_PAGE_SIZE),
    action: str | None = Query(None, description="动作精确匹配，如 create_tea"),
    target_type: str | None = Query(None, description="目标类型，如 tea"),
    admin_id: int | None = Query(None, description="操作人 user_id"),
    start_date: str | None = Query(None, description="起始日期 YYYY-MM-DD（含）"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD（含）"),
    db: Session = Depends(get_db),
):
    """A6 操作日志查询（API_CONTRACT §4.6.12）：仅管理员，时间倒序。"""
    data = admin_service.list_operation_logs(
        db,
        page=page,
        page_size=page_size,
        action=action,
        target_type=target_type,
        admin_id=admin_id,
        start_date=start_date,
        end_date=end_date,
    )
    return ok(data.model_dump(mode="json"))


@router.get("/teas")
def list_teas(
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    is_active: bool | None = Query(None),
    sort: str = Query("newest"),
    page: int = Query(1),
    page_size: int = Query(12),
    db: Session = Depends(get_db),
):
    """A3 后台茶品列表（API_CONTRACT §4.6.1）：包含下架茶品。"""
    data = admin_service.list_teas(
        db,
        category=category,
        keyword=keyword,
        is_active=is_active,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ok(data.model_dump(mode="json"))


@router.get("/teas/{tea_id}")
def get_tea(tea_id: int, db: Session = Depends(get_db)):
    """A5 后台茶品详情（API_CONTRACT §4.6.2）。"""
    return ok(admin_service.get_tea(db, tea_id).model_dump(mode="json"))


@router.post("/teas")
def create_tea(
    payload: TeaCreateRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """A4 新增茶品（API_CONTRACT §4.6.3）。"""
    data = admin_service.create_tea(db, admin_id=admin.id, req=payload)
    return ok(data.model_dump(mode="json"))


@router.put("/teas/{tea_id}")
def update_tea(
    tea_id: int,
    payload: TeaUpdateRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """A5 全量编辑茶品（API_CONTRACT §4.6.4），不接受 tips_* 与 is_active。"""
    data = admin_service.update_tea(db, admin_id=admin.id, tea_id=tea_id, req=payload)
    return ok(data.model_dump(mode="json"))


@router.patch("/teas/{tea_id}/toggle")
def toggle_tea(
    tea_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """A3/A5 上下架（API_CONTRACT §4.6.5）：不物理删除。"""
    data = admin_service.toggle_tea(db, admin_id=admin.id, tea_id=tea_id)
    return ok(data.model_dump(mode="json"))


@router.put("/teas/{tea_id}/tips")
def update_tips(
    tea_id: int,
    payload: TipsUpdateRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """A5 官方小贴士编辑（API_CONTRACT §4.6.6）。"""
    data = admin_service.update_tips(db, admin_id=admin.id, tea_id=tea_id, req=payload)
    return ok(data.model_dump(mode="json"))


@router.put("/teas/{tea_id}/brewing-guide")
def update_brewing_guide(
    tea_id: int,
    payload: BrewingGuideUpdateRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """A5 冲泡教程整篇保存（ADR-0005）：3–8 步，逐茶独立维护。"""
    data = admin_service.update_brewing_guide(db, admin_id=admin.id, tea_id=tea_id, req=payload)
    return ok(data.model_dump(mode="json"))


@router.delete("/teas/{tea_id}/brewing-guide")
def delete_brewing_guide(
    tea_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """A5 删除冲泡教程（ADR-0005）：幂等，前台退回三格速查卡。"""
    data = admin_service.delete_brewing_guide(db, admin_id=admin.id, tea_id=tea_id)
    return ok(data.model_dump(mode="json"))


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """A4/A5 图片上传（API_CONTRACT §4.6.7）：JPEG/PNG/WebP ≤ 5 MB。"""
    data = await admin_service.upload_image(db, admin_id=admin.id, file=file)
    return ok(data.model_dump(mode="json"))


@router.post("/media/video")
async def upload_video(
    file: UploadFile = File(...),
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """视频上传（ADR-0003 S5 / API_CONTRACT §4.6.9）：MP4/MOV ≤ 50 MB、≤ 3 分钟。"""
    data = await admin_service.upload_video(db, admin_id=admin.id, file=file)
    return ok(data.model_dump(mode="json"))


@router.post("/teas/{tea_id}/images")
def add_tea_image(
    tea_id: int,
    payload: TeaMediaCreateRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """追加茶品图片（ADR-0003 S4 / API_CONTRACT §4.6.10）：单茶上限 9 张。"""
    item = tea_media_service.add_image(db, admin_id=admin.id, tea_id=tea_id, req=payload)
    return ok(item.model_dump(mode="json"))


@router.delete("/teas/{tea_id}/images/{image_id}")
def delete_tea_image(
    tea_id: int,
    image_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """删除茶品图片（ADR-0003 S4 / API_CONTRACT §4.6.11）：物理删除。"""
    tea_media_service.delete_image(db, admin_id=admin.id, tea_id=tea_id, image_id=image_id)
    return ok({"deleted": image_id})


@router.get("/contributions")
def list_contributions(
    status: str | None = Query("pending", description="pending | approved | rejected"),
    type: str | None = Query(None, description="new_tea | article"),
    page: int = Query(1),
    page_size: int = Query(12),
    db: Session = Depends(get_db),
):
    """审核队列（API_CONTRACT §4.6.12）：默认待审核。"""
    data = contribution_service.admin_list(
        db, status=status, type=type, page=page, page_size=page_size
    )
    return ok(data.model_dump(mode="json"))


@router.post("/contributions/{contribution_id}/approve")
def approve_contribution(
    contribution_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """审核通过（API_CONTRACT §4.6.13）：新茶上架 / 科普展示。"""
    data = contribution_service.approve(db, admin_id=admin.id, contribution_id=contribution_id)
    return ok(data.model_dump(mode="json"))


@router.post("/contributions/{contribution_id}/reject")
def reject_contribution(
    contribution_id: int,
    payload: RejectRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """审核拒绝（API_CONTRACT §4.6.14）：原因 1–200 字。"""
    data = contribution_service.reject(
        db, admin_id=admin.id, contribution_id=contribution_id, reason=payload.reason
    )
    return ok(data.model_dump(mode="json"))


# === 批次五 R1–R5 内容管理 ===


@router.get("/contents")
def admin_list_contents(
    type: str | None = Query(None, description="板块 code"),
    is_active: bool | None = Query(None, description="是否上架"),
    page: int = Query(1),
    page_size: int = Query(12),
    db: Session = Depends(get_db),
):
    """后台内容列表（含下架；API_CONTRACT §4.6.12）。"""
    data = content_service.admin_list_contents(
        db, type_code=type, is_active=is_active, page=page, page_size=page_size
    )
    return ok(data.model_dump(mode="json"))


@router.get("/contents/{item_id}")
def admin_get_content(item_id: int, db: Session = Depends(get_db)):
    """后台内容详情（编辑回填；含下架条目）。"""
    data = content_service.admin_get_content(db, item_id=item_id)
    return ok(data.model_dump(mode="json"))


@router.post("/contents")
def admin_create_content(
    payload: ContentCreateRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员创建内容条目（API_CONTRACT §4.6.12 POST）。"""
    data = content_service.admin_create_content(db, admin_id=admin.id, req=payload)
    return ok(data.model_dump(mode="json"))


@router.put("/contents/{item_id}")
def admin_update_content(
    item_id: int,
    payload: ContentUpdateRequest,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """管理员更新内容条目（全量替换；API_CONTRACT §4.6.13 PUT）。"""
    data = content_service.admin_update_content(db, admin_id=admin.id, item_id=item_id, req=payload)
    return ok(data.model_dump(mode="json"))


@router.delete("/contents/{item_id}")
def admin_delete_content(
    item_id: int,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """软删除：is_active=0（API_CONTRACT §4.6.13 DELETE）。"""
    content_service.admin_delete_content(db, admin_id=admin.id, item_id=item_id)
    return ok({"deleted": item_id})
