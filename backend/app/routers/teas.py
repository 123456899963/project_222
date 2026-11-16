"""茶品路由（只读，游客可访问）

路由声明 / 参数接收 / Depends 注入；业务逻辑在 services，查询在 repositories。
注意：静态段 /categories /origins /hot /random 必须先于动态段 /{tea_id} 注册
（API_CONTRACT §1.1）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth_deps import get_optional_user
from app.core.database import get_db
from app.core.response import ok
from app.services import tea_media as tea_media_service
from app.services import teas as teas_service

router = APIRouter()


@router.get("")
def list_teas(
    category: str | None = Query(None, description="逗号分隔茶类枚举"),
    origin: str | None = Query(None, description="逗号分隔省级名称"),
    season: str | None = Query(None, description="逗号分隔采摘季节"),
    fermentation: str | None = Query(None, description="逗号分隔发酵程度（S2）"),
    price_min: int | None = Query(None, ge=0, description="价格下限（元/斤，S2）"),
    price_max: int | None = Query(None, ge=0, description="价格上限（元/斤，S2）"),
    filter_mode: str = Query("and", description="and | or 跨维度组合方式（S1）"),
    keyword: str | None = Query(None, description="关键词（name/origin 模糊匹配）"),
    sort: str = Query("newest", description="newest | favorite"),
    page: int = Query(1),
    page_size: int = Query(12),
    db: Session = Depends(get_db),
):
    """茶品列表（筛选 + 排序 + 分页，API_CONTRACT §4.2.1）"""
    data = teas_service.list_teas(
        db,
        category=category,
        origin=origin,
        season=season,
        fermentation=fermentation,
        price_min=price_min,
        price_max=price_max,
        filter_mode=filter_mode,
        keyword=keyword,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ok(data)


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    """七大茶类计数（API_CONTRACT §4.2.2）"""
    return ok(teas_service.categories(db))


@router.get("/origins")
def origins(db: Session = Depends(get_db)):
    """产地选项（省级 + 计数，API_CONTRACT §4.2.3）"""
    return ok(teas_service.origins(db))


@router.get("/hot")
def hot_teas(limit: int = Query(8), db: Session = Depends(get_db)):
    """热门推荐（API_CONTRACT §4.2.4）"""
    return ok(teas_service.hot_teas(db, limit=limit))


@router.get("/random")
def random_tea(exclude_id: int | None = Query(None), db: Session = Depends(get_db)):
    """随机发现（API_CONTRACT §4.2.5）"""
    return ok(teas_service.random_tea(db, exclude_id=exclude_id))


@router.get("/recommended")
def recommended_teas(
    limit: int = Query(1, description="返回条数，夹取 1-8"),
    exclude_id: int | None = Query(None, description="排除指定茶品（避免“换一款”重复）"),
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """个性化推荐（S16 / API_CONTRACT §4.2.10）：未登录或无收藏回退随机。"""
    user_id = current_user.id if current_user else None
    return ok(
        teas_service.recommended_teas(db, user_id=user_id, limit=limit, exclude_id=exclude_id)
    )


@router.get("/{tea_id}")
def get_tea(tea_id: int, db: Session = Depends(get_db)):
    """茶品详情（API_CONTRACT §4.2.6）"""
    return ok(teas_service.get_tea(db, tea_id))


@router.get("/{tea_id}/images")
def get_tea_images(tea_id: int, db: Session = Depends(get_db)):
    """茶品图片集（ADR-0003 S4 / API_CONTRACT §4.2.7）：按 sort_order 升序。"""
    items = tea_media_service.list_images(db, tea_id)
    return ok([item.model_dump(mode="json") for item in items])


@router.get("/{tea_id}/related")
def related_teas(
    tea_id: int,
    limit: int = Query(4, description="返回条数，夹取 1-8"),
    db: Session = Depends(get_db),
):
    """相关推荐（S6 / API_CONTRACT §4.2.8）：同茶类优先，同产地补足。"""
    return ok(teas_service.related_teas(db, tea_id, limit=limit))
