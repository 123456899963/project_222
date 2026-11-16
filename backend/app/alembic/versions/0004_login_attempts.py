"""login_attempts：S14 登录失败锁定

Revision ID: 0004_login_attempts
Revises: 0003_batch1_filters
Create Date: 2026-11-09

依据：PLAN_剩余功能 批次二（2026-11-09 已确认）
- 新表 login_attempts 记录失败事件（用户名 + IP + 时间）
- 索引 (username, failed_at) / (ip, failed_at) 支撑窗口计数
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0004_login_attempts"
down_revision: str | None = "0003_batch1_filters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", MySQLInteger(unsigned=True), autoincrement=True, primary_key=True),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("ip", sa.String(45), nullable=False),
        sa.Column(
            "failed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Index("idx_login_attempt_username", "username", "failed_at"),
        sa.Index("idx_login_attempt_ip", "ip", "failed_at"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_comment="登录失败尝试（S14 锁定依据；不记录密码明文）",
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
