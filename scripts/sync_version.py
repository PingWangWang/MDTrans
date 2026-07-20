#!/usr/bin/env python3
"""
版本号同步脚本

``src/mdtrans/__about__.py`` 是版本号的**单源真理**（Single Source of Truth）。
修改版本时只需编辑该文件，然后运行本脚本同步到 ``pyproject.toml``。

用法：
    python scripts/sync_version.py          # 检查并同步
    python scripts/sync_version.py --check  # 仅检查不一致
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ABOUT_FILE = PROJECT_ROOT / "src" / "mdtrans" / "__about__.py"
PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"


def read_version_from_about() -> str | None:
    """从 ``__about__.py`` 读取 ``__version__``。"""
    content = ABOUT_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else None


def read_version_from_pyproject() -> str | None:
    """从 ``pyproject.toml`` 读取 ``version``。"""
    content = PYPROJECT_FILE.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else None


def update_pyproject(version: str) -> bool:
    """将 ``pyproject.toml`` 中的 ``version`` 更新为指定值。"""
    content = PYPROJECT_FILE.read_text(encoding="utf-8")
    new_content = re.sub(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if new_content == content:
        return False
    PYPROJECT_FILE.write_text(new_content, encoding="utf-8")
    return True


def main() -> None:
    check_only = "--check" in sys.argv

    about_ver = read_version_from_about()
    pyproject_ver = read_version_from_pyproject()

    if not about_ver:
        print("错误：无法从 __about__.py 读取版本号")
        sys.exit(1)
    if not pyproject_ver:
        print("错误：无法从 pyproject.toml 读取版本号")
        sys.exit(1)

    if about_ver == pyproject_ver:
        print(f"版本号一致：{about_ver}")
        return

    print(f"版本号不一致：__about__.py={about_ver}  pyproject.toml={pyproject_ver}")

    if check_only:
        print("\n提示：运行 `python scripts/sync_version.py` 自动同步")
        sys.exit(1)

    if update_pyproject(about_ver):
        print(f"已同步：pyproject.toml → {about_ver}")
    else:
        print("错误：同步失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
