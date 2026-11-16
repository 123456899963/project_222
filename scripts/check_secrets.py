#!/usr/bin/env python3
"""高置信度敏感信息扫描：私钥、云厂商密钥、平台 Token 与误提交的 .env。"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "私钥": re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "AWS Access Key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub Token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"),
    "Slack Token": re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
}
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf", ".zip", ".gz",
    ".mp4", ".woff", ".woff2", ".ttf", ".eot", ".lock",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


LOCAL_ENV = ROOT / "backend" / ".env"
SENSITIVE_KEYS = ("MYSQL_PASSWORD", "ADMIN_PASSWORD", "SECRET_KEY")


def local_env_report() -> tuple[list[str], list[str]]:
    """检查本地 .env：不读取、不输出任何值，只确认存在性与忽略规则。

    返回 (warnings, errors)。--share-check 模式下由调用方把存在性升级为错误。
    """
    warnings: list[str] = []
    errors: list[str] = []
    if not LOCAL_ENV.is_file():
        return warnings, errors

    present: list[str] = []
    for line in LOCAL_ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() in SENSITIVE_KEYS and value.strip():
            present.append(key.strip())
    warnings.append(
        "WARN: backend/.env 存在"
        + (f"（非空项：{', '.join(present)}）" if present else "")
        + "；该文件含真实口令/密钥，压缩整个项目分享或打包前必须排除。"
    )

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "backend/.env"], cwd=ROOT, capture_output=True
    )
    if ignored.returncode != 0:
        errors.append("backend/.env 未被 .gitignore 忽略，存在误提交风险")

    dockerignore = ROOT / ".dockerignore"
    if dockerignore.is_file():
        entries = {
            line.strip()
            for line in dockerignore.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        if ".env" not in entries and ".env*" not in entries:
            warnings.append("WARN: .dockerignore 未排除 .env，镜像可能带入本地密钥")
    else:
        warnings.append("WARN: 未找到 .dockerignore，无法确认镜像是否排除 .env")

    return warnings, errors


def main() -> int:
    share_check = "--share-check" in sys.argv[1:]
    warnings, local_errors = local_env_report()
    for warning in warnings:
        print(warning)

    errors: list[str] = list(local_errors)
    if share_check and LOCAL_ENV.is_file():
        errors.append(
            "分享检查失败：backend/.env 仍在项目目录中；请先移出压缩包/共享目录再分享"
        )
    scanned = 0
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            errors.append(f"{rel}: .env 文件不得进入 Git")
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{rel}:{line}: 疑似{name}")

    if errors:
        print("FAIL: 发现疑似敏感信息：")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"OK: 已扫描 {scanned} 个文本文件，未发现高置信度敏感信息。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
