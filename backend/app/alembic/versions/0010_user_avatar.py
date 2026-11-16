"""user_avatar：users 增加 avatar_url（ADR-0004）

Revision ID: 0010_user_avatar
Revises: 0009_seed_content_items_more
Create Date: 2026-11-10

头像地址：本地上传为 /uploads/...，预置头像为 /avatars/tea-0X.svg。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_user_avatar"
down_revision: str | None = "0009_seed_content_items_more"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
