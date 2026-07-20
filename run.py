"""MDTrans - 开发环境快速启动脚本。

用法:
    uv run python run.py
    python run.py          （已激活虚拟环境时）
"""

import sys
from pathlib import Path

# 检查是否在虚拟环境中（uv 或 venv）
_in_venv = hasattr(sys, "real_prefix") or (
    hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
)
if not _in_venv:
    # 检测 .venv 是否存在但未激活
    _venv_root = Path(__file__).resolve().parent / ".venv"
    _hint = ""
    if _venv_root.is_dir():
        _hint = "  uv run python run.py"
    else:
        _hint = "  uv sync && uv run python run.py"
    print(
        "⚠ 未检测到 Python 虚拟环境。\n"
        f"请使用 UV 运行:\n"
        f"    {_hint}",
        file=sys.stderr,
    )
    sys.exit(1)

# 确保 src/ 在 sys.path 中
_src = Path(__file__).resolve().parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from mdtrans.main import main

main()
