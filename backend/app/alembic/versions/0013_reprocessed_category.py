"""teas / tea_name_category_map：category ENUM 新增再加工茶（reprocessed）

Revision ID: 0013_reprocessed_category
Revises: 0012_brewing_guides
Create Date: 2026-11-12

- 茶类枚举顺序固定为 green, white, yellow, red, oolong, dark, reprocessed
- 仅扩展 ENUM 取值，不改列约束与索引
- 已知回滚风险：若库中已存在 reprocessed 茶品，downgrade 在严格模式下会失败，
  需先人工处理这些行再回滚
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013_reprocessed_category"
down_revision: str | None = "0012_brewing_guides"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_VALUES = "'green','white','yellow','red','oolong','dark'"
NEW_VALUES = "'green','white','yellow','red','oolong','dark','reprocessed'"


def upgrade() -> None:
    op.execute(f"ALTER TABLE teas MODIFY category ENUM({NEW_VALUES}) NOT NULL")
    op.execute(
        "ALTER TABLE tea_name_category_map "
        f"MODIFY category ENUM({NEW_VALUES}) NOT NULL COMMENT '应有茶类'"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE teas MODIFY category ENUM({OLD_VALUES}) NOT NULL")
    op.execute(
        "ALTER TABLE tea_name_category_map "
        f"MODIFY category ENUM({OLD_VALUES}) NOT NULL COMMENT '应有茶类'"
    )
