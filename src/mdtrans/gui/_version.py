"""MDTrans - 版本信息。

版本号读取优先级：
  1. 环境变量 ``APP_VERSION``（打包脚本注入）
  2. ``__about__.py``（单源真理）
  3. 硬编码回退值
"""

from __future__ import annotations

import os


def _read_version() -> str:
    """读取版本号，按优先级尝试。"""
    # 1. 环境变量优先（打包脚本可注入）
    env_version = os.environ.get("APP_VERSION")
    if env_version:
        return env_version

    # 2. 从 __about__.py 读取
    try:
        from mdtrans.__about__ import __version__

        return __version__
    except Exception:
        pass

    # 3. 回退
    return "1.2.2"


APP_VERSION: str = _read_version()
