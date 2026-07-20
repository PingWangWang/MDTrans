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
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk
from typing import Any

# ── 布局常量 ──────────────────────────────────────────────────────────────

# 标签列最小宽度（与 ExportPage 最长标签“选择 Markdown 文件:”匹配）
# 使 ImportPage 与 ExportPage 的左侧标签列宽保持一致
LABEL_COL_WIDTH: int = 70

# DOCX 专属选项区域高度（Mermaid 2 行，每行约 30px）
# 固定容器高度使两 Tab 页上半部编辑区域高度一致，切换格式时不跳变
DOCX_OPTIONS_HEIGHT: int = 95

# 日志 ScrolledText 默认行数
DEFAULT_LOG_HEIGHT: int = 7


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


# ── 共享布局组件 ──────────────────────────────────────────────────────────


def create_log_section(
    parent: ttk.Frame,
    row: int,
    theme_manager: Any,
    tag_list: list[tuple[str, str]],
) -> tuple[int, scrolledtext.ScrolledText]:
    """创建统一的日志区域（标签 + ScrolledText + 主题联动）。

    供 ImportPage / ExportPage 共同调用，确保两页日志窗口大小一致。

    Args:
        parent: 父容器 Frame。
        row: 起始行号。
        theme_manager: ThemeManager 实例，提供 colors 和 watch 方法。
        tag_list: [(tag名, 前景色), ...] 列表。

    Returns:
        (下一行号, ScrolledText 控件)。
    """
    ttk.Label(parent, text="处理日志:", font=("Microsoft YaHei UI", 9)).grid(
        row=row, column=0, sticky=tk.NW, pady=(8, 2), padx=(0, 8))

    colors = theme_manager.colors
    log_text = scrolledtext.ScrolledText(
        parent, height=DEFAULT_LOG_HEIGHT, wrap=tk.WORD,
        font=("Consolas", 9),
        bg=colors["log_bg"], fg=colors["log_fg"],
        insertbackground=colors["log_fg"],
        selectbackground=colors["select_bg"],
        selectforeground=colors["select_fg"],
        relief="flat", borderwidth=0, state="disabled")
    log_text.grid(row=row, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(8, 2))
    parent.rowconfigure(row, weight=1)

    theme_manager.watch(log_text, refresh_callback=lambda c: {
        "bg": c["log_bg"], "fg": c["log_fg"],
        "insertbackground": c["log_fg"],
        "selectbackground": c["select_bg"],
        "selectforeground": c["select_fg"],
    })

    for tag, color in tag_list:
        log_text.tag_configure(tag, foreground=color)

    return row + 1, log_text


def create_action_buttons(
    parent: ttk.Frame,
    row: int,
    process_text: str,
    process_cmd: Any,
    open_output_dir_cmd: Any,
    open_last_doc_cmd: Any,
    open_doc_width: int = 14,
) -> tuple[int, ttk.Button, ttk.Button]:
    """创建统一的操作栏（分隔线 + 三按钮）。

    供 ImportPage / ExportPage 共同调用，确保两页按钮位置和大小一致。

    Args:
        parent: 父容器 Frame。
        row: 起始行号。
        process_text: 主操作按钮的文字。
        process_cmd: 主操作按钮的回调。
        open_output_dir_cmd: "打开输出目录"按钮回调。
        open_last_doc_cmd: "打开文档"按钮回调。
        open_doc_width: "打开文档"按钮宽度（默认 14）。

    Returns:
        (下一行号, 主操作按钮, 打开文档按钮)。
    """
    ttk.Separator(parent, orient="horizontal").grid(
        row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=6)
    row += 1

    bf = ttk.Frame(parent)
    bf.grid(row=row, column=0, columnspan=2, pady=4)

    process_btn = ttk.Button(
        bf, text=process_text, command=process_cmd,
        style="success.TButton", width=14)
    process_btn.pack(side=tk.LEFT, padx=6)

    ttk.Button(bf, text="📂  打开输出目录", command=open_output_dir_cmd,
               style="info.TButton", width=14).pack(side=tk.LEFT, padx=6)

    open_doc_btn = ttk.Button(
        bf, text="📄  打开文档", command=open_last_doc_cmd,
        style="info.TButton", width=open_doc_width, state="disabled")
    open_doc_btn.pack(side=tk.LEFT, padx=6)

    return row + 1, process_btn, open_doc_btn
