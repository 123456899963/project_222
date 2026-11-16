"""user_session_version：users 增加 session_version（SECURITY S-10 改密吊销会话）

Revision ID: 0011_user_session_version
Revises: 0010_user_avatar
Create Date: 2026-11-11

会话 Cookie 载荷携带 sv，鉴权时与 users.session_version 比对；
用户自助修改密码后 session_version + 1，所有旧 Cookie 立即失效。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger

# revision identifiers, used by Alembic.
revision: str = "0011_user_session_version"
down_revision: str | None = "0010_user_avatar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "session_version",
            MySQLInteger(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
            comment="会话版本号：改密后 +1，旧 Cookie 立即失效",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "session_version")
