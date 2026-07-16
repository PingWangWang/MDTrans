"""MDTrans - 开发环境快速启动脚本。

用法:
    python run.py
"""

import sys
from pathlib import Path

# 确保 src/ 在 sys.path 中
_src = Path(__file__).resolve().parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from mdtrans.main import main

main()
