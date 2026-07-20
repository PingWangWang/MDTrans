#!/usr/bin/env python3
"""
MDTrans 开发环境一键安装脚本。

用法：
    python scripts/setup_dev.py

自动完成：
    1. uv sync（安装 Python 依赖）
    2. playwright install chromium（下载 Chromium 浏览器）
"""

import subprocess
from pathlib import Path


def _run_step(description: str, cmd: list[str]) -> None:
    """运行一条命令并输出结果。"""
    print(f"\n▶ {description} ...")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode == 0:
        print(f"  ✓ {description}")
    else:
        print(f"  ✗ {description} 失败 (exit code {result.returncode})")
        sys.exit(result.returncode)


def main() -> None:
    print("=" * 50)
    print("  MDTrans 开发环境安装")
    print("=" * 50)

    # 1. 安装 Python 依赖
    _run_step("安装 Python 依赖 (uv sync)", ["uv", "sync"])

    print("\n" + "=" * 50)
    print("  ✓ 安装完成！")
    print("  运行 python -m mdtrans 启动应用")
    print("  （图片导出功能将使用系统已安装的 Edge/Chrome 浏览器）")
    print("=" * 50)


if __name__ == "__main__":
    main()
