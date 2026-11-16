"""官方小贴士路由（S7 首页最新小贴士预览）

路由声明 / 参数接收 / Depends 注入；业务逻辑在 services，查询在 repositories。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.services import teas as teas_service

router = APIRouter()


@router.get("/latest")
def latest_tips(limit: int = Query(3), db: Session = Depends(get_db)):
    """最新小贴士（API_CONTRACT §4.2.9）：limit 夹取 1-6，默认 3。"""
    return ok(teas_service.latest_tips(db, limit=limit))
