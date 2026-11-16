"""baseline：现有 7 表基线（空操作）

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-09

说明：
- 本项目 Alembic 在 MVP 完成后才接管版本链（此前 versions/ 为空）。
- 基线结构（users / teas / tea_tips / collection_lists / favorite_items /
  share_tokens / operation_logs 共 7 张表）由 database/init.sql 建立，
  本迁移不重复执行任何 DDL，仅作为 Alembic 版本起点。
- 全新环境（当前 init.sql）：init.sql 已随批次演进包含最新全部结构与种子，
  建库后直接执行 `alembic stamp head` 接管，之后一律 `alembic upgrade head`
  应用增量（AGENTS.md §6：禁止手工 ALTER TABLE）。
  【2026-11-10 部署演练修正】旧流程「stamp 0001_baseline → upgrade head」会与
  init.sql 中已有的后期列冲突（如 0002 的 teas.video_url，报 1060 Duplicate
  column），故改为直接 stamp head。
- 早期按旧版 init.sql 建库且版本链已运行的环境：直接 `alembic upgrade head`。
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 空操作：基线结构由 database/init.sql 管理
    pass


def downgrade() -> None:
    # 空操作：基线不可降级（降级即删库，由人工执行）
    pass
