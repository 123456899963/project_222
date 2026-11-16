"""管理员密码轮换脚本（SECURITY S-31）。

用法（任选其一）：
    python -m app.scripts.rotate_admin_password --password "新密码"
    $env:NEW_ADMIN_PASSWORD="新密码"; python -m app.scripts.rotate_admin_password

仅更新指定管理员账号的 password_hash（bcrypt cost=10），不输出明文密码。
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.repositories import user_repo


def rotate_password(db: Session, username: str, new_password: str) -> bool:
    """更新管理员密码哈希；账号不存在返回 False。"""
    user = user_repo.get_by_username(db, username)
    if user is None:
        return False
    user.password_hash = hash_password(new_password)
    db.commit()
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="茶·图鉴管理员密码轮换")
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument(
        "--password",
        default=os.getenv("NEW_ADMIN_PASSWORD"),
        help="新密码；也可通过环境变量 NEW_ADMIN_PASSWORD 提供",
    )
    args = parser.parse_args(argv)

    if not args.password:
        print("未提供新密码：请使用 --password 或 NEW_ADMIN_PASSWORD", file=sys.stderr)
        return 2
    if len(args.password) < 8:
        print("新密码长度至少 8 位", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        rotated = rotate_password(db, args.username, args.password)
    finally:
        db.close()

    if not rotated:
        print(f"管理员 {args.username} 不存在", file=sys.stderr)
        return 1

    # 只输出结果，不输出密码明文
    print(f"管理员 {args.username} 密码轮换成功（bcrypt cost=10）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
