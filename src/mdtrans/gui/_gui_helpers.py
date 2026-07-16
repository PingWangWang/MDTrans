"""MDTrans - GUI 辅助函数。

从 MarkdownExporterGUI 和 MarkitDownGUI 合并。
提供资源路径解析、文件/URL 操作、拖拽路径解析、日志标签识别、依赖检查等功能。
"""

from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── 资源路径解析 ──────────────────────────────────────────────────────────


def get_resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径（兼容 PyInstaller 打包环境）。

    Args:
        relative_path: 相对于项目根目录或 _MEIPASS 的路径。

    Returns:
        资源的绝对路径字符串。
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[arg-type]
    else:
        base = Path(__file__).resolve().parent.parent.parent.parent  # 项目根目录
    return str(base / relative_path)


def get_icon_path() -> str:
    """获取应用图标路径。

    Returns:
        .ico 文件的绝对路径。
    """
    path = get_resource_path("res/icon.ico")
    if Path(path).exists():
        return path
    # 回退：从原始项目复制来的图标
    for candidate in ["res/icon.ico", "res/icad.ico", "res/ProductIcon.ico"]:
        p = get_resource_path(candidate)
        if Path(p).exists():
            return p
    return ""


# ── 文件/URL 操作 ─────────────────────────────────────────────────────────


def open_file_or_dir(path: str, *, select_in_explorer: bool = False) -> None:
    """跨平台打开文件或目录。

    Args:
        path: 要打开的文件或目录路径。
        select_in_explorer: 如果为 True，在资源管理器中选中该文件。
    """
    if select_in_explorer:
        subprocess.run(["explorer", "/select,", path], check=False)
    else:
        os.startfile(path)  # Windows only


def open_url(url: str) -> None:
    """在默认浏览器中打开 URL。

    Args:
        url: 网页地址。
    """
    import webbrowser

    webbrowser.open(url)


# ── 拖拽路径解析 ──────────────────────────────────────────────────────────


def parse_dnd_paths(raw_data: str) -> list[str]:
    """解析 tkinterdnd2 拖拽事件中的文件路径列表。

    Args:
        raw_data: tkinterdnd2 事件中的 ``data`` 字符串。

    Returns:
        文件路径列表。
    """
    if not raw_data:
        return []
    # tkinterdnd2 在不同平台/版本下的格式不同
    # Windows: 路径用 \r\n 分隔，可能含 { }
    paths: list[str] = []
    for part in re.split(r"[\r\n]+", raw_data.strip()):
        part = part.strip().strip("{}").strip()
        if part and not part.startswith("#"):
            paths.append(part)
    return paths


# ── 日志标签识别 ──────────────────────────────────────────────────────────


_LOG_TAG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(错误|失败|Error|Failed|ERROR)", re.IGNORECASE), "error"),
    (re.compile(r"(警告|Warning|WARN)", re.IGNORECASE), "warning"),
    (re.compile(r"(成功|完成|Success|Done|Complete)", re.IGNORECASE), "success"),
    (re.compile(r"(信息|Info|INFO)", re.IGNORECASE), "info"),
]


def resolve_log_tag(message: str) -> str:
    """根据消息内容判断日志标签颜色。

    Args:
        message: 日志消息文本。

    Returns:
        标签名：``"error"``、``"warning"``、``"success"``、``"info"`` 之一。
    """
    for pattern, tag in _LOG_TAG_PATTERNS:
        if pattern.search(message):
            return tag
    return "info"


# ── 依赖检查 ──────────────────────────────────────────────────────────────


def check_dependency(mod_name: str, display_name: str | None = None) -> tuple[str, bool]:
    """检查单个 Python 模块是否可导入。

    Args:
        mod_name: 模块名（如 ``"pypandoc"``）。
        display_name: 显示名称，为 ``None`` 时使用模块名。

    Returns:
        ``(显示名称, 是否可用)``。
    """
    name = display_name or mod_name
    try:
        importlib.import_module(mod_name)
        return (name, True)
    except ImportError:
        return (name, False)


def check_dependencies() -> list[tuple[str, bool]]:
    """检查主要依赖是否可用。

    Returns:
        ``[(名称, 是否可用), ...]`` 列表。
    """
    deps: list[tuple[str, bool]] = []
    for mod, display in [
        ("markdown", "markdown"),
        ("pypandoc", "pypandoc-binary"),
        ("docx", "python-docx"),
        ("xhtml2pdf", "xhtml2pdf"),
        ("pandas", "pandas"),
        ("reportlab", "reportlab"),
        ("PIL", "pillow"),
        ("requests", "requests"),
        ("markitdown", "markitdown (导入引擎)"),
    ]:
        deps.append(check_dependency(mod, display))
    return deps
