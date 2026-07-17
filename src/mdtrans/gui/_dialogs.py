"""MDTrans - 对话框组件。

合并自 MarkdownExporterGUI 和 MarkitDownGUI 的对话框，
使用 ttk.Button + bootstyle 确保主题一致性。
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import Any, Callable

from mdtrans.gui._gui_helpers import open_url
from mdtrans.__about__ import __version__


# ── DialogTheme ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DialogTheme:
    """对话框样式参数（不可变）。

    请始终从 ThemeManager.colors 传入值，不要依赖默认值。
    """

    root: tk.Tk | tk.Toplevel | None = None
    bg: str = "#FFFFFF"
    header_bg: str = "#2C3E50"
    header_fg: str = "#FFFFFF"
    label_fg: str = "#333333"
    border_color: str = "#CCCCCC"


# ── 内部工具 ──────────────────────────────────────────────────────────────


def _center_dialog(window: tk.Toplevel, parent: tk.Widget, w: int, h: int) -> None:
    """将窗口居中显示在父窗口上。"""
    px = parent.winfo_x()
    py = parent.winfo_y()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2
    window.geometry(f"{w}x{h}+{x}+{y}")


def _create_dialog_button(
    parent: tk.Widget,
    text: str,
    command: Callable[..., Any],
    bootstyle: str = "primary",
    **kwargs: Any,
) -> ttk.Button:
    """创建一个 ttkbootstrap 样式的对话框按钮。

    Args:
        parent: 父控件。
        text: 按钮文字。
        command: 点击回调。
        bootstyle: ttkbootstrap bootstyle 名（如 "success", "primary", "danger"）。
        **kwargs: 传递给 ``ttk.Button`` 的其他参数。

    Returns:
        创建的按钮。
    """
    btn = ttk.Button(
        parent,
        text=text,
        command=command,
        bootstyle=bootstyle,
        **kwargs,
    )
    return btn


# ── 关于窗口 ──────────────────────────────────────────────────────────────


def show_about(theme: DialogTheme) -> None:
    """显示关于 MDTrans 的窗口。"""
    if theme.root is None:
        return
    top = tk.Toplevel(theme.root)
    top.title(f"关于 MDTrans v{__version__}")
    top.configure(bg=theme.bg)
    top.resizable(False, False)

    # ── 标题栏 ────────────────────────────────────────────────────────
    header = tk.Frame(top, bg=theme.header_bg, height=40)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(
        header,
        text="MDTrans",
        bg=theme.header_bg,
        fg=theme.header_fg,
        font=("Microsoft YaHei UI", 13, "bold"),
    ).pack(side="left", padx=16, pady=6)
    tk.Label(
        header,
        text=f"v{__version__}",
        bg=theme.header_bg,
        fg=theme.header_fg,
        font=("Microsoft YaHei UI", 9),
    ).pack(side="right", padx=16, pady=6)

    # ── 内容区域 ──────────────────────────────────────────────────────
    content = tk.Frame(top, bg=theme.bg, padx=24, pady=18)
    content.pack(fill="both", expand=True)

    # 工具描述
    tk.Label(
        content,
        text="双向文档转换工具",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 11, "bold"),
    ).pack(fill="x", pady=(0, 2))
    tk.Label(
        content,
        text="导入多种格式为 Markdown，或将 Markdown 导出为其他格式",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9),
        anchor="w",
        justify="left",
    ).pack(fill="x", pady=(0, 10))

    # 格式支持
    fmt_frame = tk.Frame(content, bg=theme.bg)
    fmt_frame.pack(fill="x", pady=(0, 10))

    tk.Label(
        fmt_frame,
        text="📥 导入",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9, "bold"),
    ).pack(anchor="w")
    tk.Label(
        fmt_frame,
        text="PDF / DOCX / PPTX / XLSX / HTML / 图片 / 文本 → Markdown",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9),
        anchor="w",
        justify="left",
    ).pack(fill="x", pady=(1, 6))

    tk.Label(
        fmt_frame,
        text="📤 导出",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9, "bold"),
    ).pack(anchor="w")
    tk.Label(
        fmt_frame,
        text="Markdown → DOCX / PDF / HTML",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9),
        anchor="w",
        justify="left",
    ).pack(fill="x", pady=(1, 0))

    tk.Frame(content, bg=theme.border_color, height=1).pack(fill="x", pady=12)

    # 版本与链接
    info_frame = tk.Frame(content, bg=theme.bg)
    info_frame.pack(fill="x")

    tk.Label(
        info_frame,
        text="基于 MarkdownExporterGUI v3.6.9 + MarkitDownGUI 合并",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9),
        anchor="w",
        justify="left",
    ).pack(fill="x", pady=1)

    link = tk.Label(
        info_frame,
        text="在 GitHub 上查看文档 >>",
        bg=theme.bg,
        fg="#3498DB",
        font=("Microsoft YaHei UI", 9, "underline"),
        cursor="hand2",
    )
    link.pack(fill="x", pady=(6, 0))
    link.bind(
        "<ButtonRelease-1>",
        lambda e: open_url("https://github.com/PingWangWang/MDTrans"),
    )

    tk.Frame(content, bg=theme.border_color, height=1).pack(fill="x", pady=12)

    # ── 关闭按钮 ─────────────────────────────────────────────────────
    btn_frame = tk.Frame(content, bg=theme.bg)
    btn_frame.pack(fill="x", pady=(4, 0))
    _create_dialog_button(btn_frame, "关闭", top.destroy, "primary").pack(side="right")

    top.update_idletasks()
    _center_dialog(top, theme.root, 460, 330)
    top.grab_set()
    top.wait_window()


# ── 覆盖确认对话框（单文件） ──────────────────────────────────────────────


def ask_overwrite(theme: DialogTheme, filename: str) -> bool:
    """单文件覆盖确认对话框。

    Args:
        theme: 对话框主题样式。
        filename: 目标文件名。

    Returns:
        ``True`` 表示覆盖，``False`` 表示跳过。
    """
    if theme.root is None:
        return True
    result: list[bool] = [False]
    top = tk.Toplevel(theme.root)
    top.title("文件已存在")
    top.configure(bg=theme.bg)
    top.resizable(False, False)

    header = tk.Frame(top, bg=theme.header_bg, height=36)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(
        header,
        text="⚠ 文件已存在",
        bg=theme.header_bg,
        fg=theme.header_fg,
        font=("Microsoft YaHei UI", 10, "bold"),
    ).pack(padx=12, pady=4)

    body = tk.Frame(top, bg=theme.bg, padx=20, pady=16)
    body.pack(fill="both", expand=True)

    tk.Label(
        body,
        text="文件已存在，是否覆盖？",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9),
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        body,
        text=filename,
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9, "bold"),
        anchor="w",
        wraplength=380,
    ).pack(fill="x", pady=(4, 12))

    btn_frame = tk.Frame(body, bg=theme.bg)
    btn_frame.pack(fill="x")

    _create_dialog_button(btn_frame, "跳过", lambda: (result.__setitem__(0, False), top.destroy()), "primary").pack(side="right", padx=(4, 0))
    _create_dialog_button(btn_frame, "覆盖", lambda: (result.__setitem__(0, True), top.destroy()), "success").pack(side="right", padx=(0, 4))

    top.update_idletasks()
    _center_dialog(top, theme.root, 400, 170)
    top.grab_set()
    top.wait_window()
    return result[0]


# ── 批量覆盖确认对话框 ────────────────────────────────────────────────────


def ask_overwrite_batch(
    theme: DialogTheme,
    filename: str,
    overwrite_all: bool,
    skip_all: bool,
) -> tuple[bool, bool, bool]:
    """批量文件覆盖确认对话框。

    Args:
        theme: 对话框主题样式。
        filename: 目标文件名。
        overwrite_all: 当前是否已勾选"全部覆盖"。
        skip_all: 当前是否已勾选"全部跳过"。

    Returns:
        ``(继续处理?, 新overwrite_all, 新skip_all)``。
    """
    if theme.root is None:
        return (True, overwrite_all, skip_all)
    result: list[Any] = [True, overwrite_all, skip_all]

    top = tk.Toplevel(theme.root)
    top.title("文件已存在")
    top.configure(bg=theme.bg)
    top.resizable(False, False)

    header = tk.Frame(top, bg=theme.header_bg, height=36)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(
        header,
        text="⚠ 文件已存在",
        bg=theme.header_bg,
        fg=theme.header_fg,
        font=("Microsoft YaHei UI", 10, "bold"),
    ).pack(padx=12, pady=4)

    body = tk.Frame(top, bg=theme.bg, padx=20, pady=16)
    body.pack(fill="both", expand=True)

    tk.Label(
        body,
        text="目标文件已存在，请选择操作：",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9),
    ).pack(fill="x")
    tk.Label(
        body,
        text=filename,
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9, "bold"),
        anchor="w",
        wraplength=380,
    ).pack(fill="x", pady=(4, 12))

    btn_frame = tk.Frame(body, bg=theme.bg)
    btn_frame.pack(fill="x", pady=(4, 0))

    def _do_overwrite() -> None:
        result[0] = True
        result[1] = False
        result[2] = False
        top.destroy()

    def _do_skip() -> None:
        result[0] = True
        result[1] = False
        result[2] = False
        top.destroy()

    def _set_overwrite_all() -> None:
        result[0] = True
        result[1] = True
        result[2] = False
        top.destroy()

    def _set_skip_all() -> None:
        result[0] = True
        result[1] = False
        result[2] = True
        top.destroy()

    _create_dialog_button(btn_frame, "全部覆盖", _set_overwrite_all, "success").pack(side="left", fill="x", expand=True, padx=2)
    _create_dialog_button(btn_frame, "全部跳过", _set_skip_all, "secondary").pack(side="left", fill="x", expand=True, padx=2)
    _create_dialog_button(btn_frame, "覆盖", _do_overwrite, "success").pack(side="left", fill="x", expand=True, padx=2)
    _create_dialog_button(btn_frame, "跳过", _do_skip, "secondary").pack(side="left", fill="x", expand=True, padx=2)

    top.update_idletasks()
    _center_dialog(top, theme.root, 420, 190)
    top.grab_set()
    top.wait_window()
    return (result[0], result[1], result[2])


# ── 文件锁定提示 ─────────────────────────────────────────────────────────


def ask_file_locked(theme: DialogTheme, filename: str) -> bool:
    """文件被占用提示对话框。

    Args:
        theme: 对话框主题样式。
        filename: 被占用的文件名。

    Returns:
        ``True`` 表示重试，``False`` 表示跳过。
    """
    if theme.root is None:
        return False
    result: list[bool] = [False]

    top = tk.Toplevel(theme.root)
    top.title("文件被占用")
    top.configure(bg=theme.bg)
    top.resizable(False, False)

    header = tk.Frame(top, bg=theme.header_bg, height=36)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(
        header,
        text="🔒 文件被占用",
        bg=theme.header_bg,
        fg=theme.header_fg,
        font=("Microsoft YaHei UI", 10, "bold"),
    ).pack(padx=12, pady=4)

    body = tk.Frame(top, bg=theme.bg, padx=20, pady=16)
    body.pack(fill="both", expand=True)

    tk.Label(
        body,
        text="文件被其他程序占用，无法写入：",
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9),
    ).pack(fill="x")
    tk.Label(
        body,
        text=filename,
        bg=theme.bg,
        fg=theme.label_fg,
        font=("Microsoft YaHei UI", 9, "bold"),
        anchor="w",
        wraplength=380,
    ).pack(fill="x", pady=(4, 12))

    btn_frame = tk.Frame(body, bg=theme.bg)
    btn_frame.pack(fill="x", pady=(4, 0))

    _create_dialog_button(btn_frame, "重试", lambda: (result.__setitem__(0, True), top.destroy()), "success").pack(side="right", padx=(4, 0))
    _create_dialog_button(btn_frame, "跳过", lambda: (result.__setitem__(0, False), top.destroy()), "secondary").pack(side="right", padx=(0, 4))

    top.update_idletasks()
    _center_dialog(top, theme.root, 400, 180)
    top.grab_set()
    top.wait_window()
    return result[0]
