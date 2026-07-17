"""MDTrans - 主题管理器。

集中管理 ttkbootstrap 主题状态、颜色映射和原生 tk 控件的主题刷新。
支持一键切换明暗主题。
从 MarkdownExporterGUI 迁移，增强为全局共享实例。
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

# 亮/暗主题对（ttkbootstrap 内置主题名）
THEME_LIGHT: str = "flatly"
THEME_DARK: str = "darkly"

# 主题切换回调类型
ThemeChangeCallback = Callable[[str], None]  # 参数为 "light" / "dark"


class ThemeManager:
    """管理 ttkbootstrap 主题切换和颜色映射。

    Args:
        style: ttkbootstrap.Style 实例。
    """

    def __init__(self, style: Any, mode: str = "light") -> None:
        self._style = style
        self._mode = mode
        self._colors: dict[str, str] = {}
        self._watched_widgets: list[dict[str, Any]] = []
        self._global_callbacks: list[ThemeChangeCallback] = []
        self._load_colors()

    # ── 公开属性 ──────────────────────────────────────────────────────────

    @property
    def colors(self) -> dict[str, str]:
        """当前主题下的语义颜色字典。"""
        return self._colors

    @property
    def mode(self) -> str:
        """当前模式，``"light"`` 或 ``"dark"``。"""
        return self._mode

    @property
    def style(self) -> Any:
        """ttkbootstrap.Style 实例。"""
        return self._style

    @property
    def theme_name(self) -> str:
        """当前 ttkbootstrap 主题名。"""
        return THEME_LIGHT if self._mode == "light" else THEME_DARK

    @property
    def is_dark(self) -> bool:
        """当前是否为暗色主题。"""
        return self._mode == "dark"

    # ── 主题切换 ──────────────────────────────────────────────────────────

    def toggle(self) -> None:
        """切换明暗主题。"""
        self._mode = "dark" if self._mode == "light" else "light"
        target = THEME_DARK if self._mode == "dark" else THEME_LIGHT
        self._style.theme_use(target)
        self._load_colors()
        self._refresh_widgets()
        self._notify_global_callbacks()

    def set_theme(self, mode: str) -> None:
        """设置指定的主题模式。

        Args:
            mode: ``"light"`` 或 ``"dark"``。
        """
        if mode not in ("light", "dark"):
            raise ValueError(f"无效主题模式: {mode}")
        if mode != self._mode:
            self.toggle()

    # ── 全局回调 ──────────────────────────────────────────────────────────

    def on_theme_changed(self, callback: ThemeChangeCallback) -> None:
        """注册全局主题切换回调（用于不同 Page 间的主题同步）。

        Args:
            callback: 主题切换时调用，参数为 ``"light"`` 或 ``"dark"``。
        """
        self._global_callbacks.append(callback)

    def _notify_global_callbacks(self) -> None:
        """通知所有全局回调。"""
        for cb in self._global_callbacks:
            try:
                cb(self._mode)
            except Exception:
                pass

    # ── 原生控件注册 ──────────────────────────────────────────────────────

    def watch(
        self,
        widget: tk.Widget,
        refresh_callback: Any,
    ) -> None:
        """注册一个原生 tk 控件，使其在主题切换时自动更新颜色。

        Args:
            widget: 原生 tk 控件实例（如 ``tk.Text``、``tk.Listbox``）。
            refresh_callback: 接收当前 ``colors`` 字典，返回 ``configure`` 参数字典的
                可调用对象。每次主题切换时会自动调用。
        """
        self._watched_widgets.append({
            "widget": widget,
            "refresh": refresh_callback,
        })
        # 立即应用当前主题的配置
        cfg = refresh_callback(self._colors)
        if cfg:
            try:
                widget.configure(**cfg)
            except tk.TclError:
                pass

    # ── 内部方法 ──────────────────────────────────────────────────────────

    def _load_colors(self) -> None:
        """从 ttkbootstrap 当前主题加载颜色映射。"""
        c = self._style.colors
        is_dark = self._mode == "dark"

        self._colors = {
            "bg": c.bg,
            "fg": c.fg,
            "primary": c.primary,
            "secondary": c.secondary,
            "success": c.success,
            "info": c.info,
            "warning": c.warning,
            "danger": c.danger,
            "light": c.light,
            "dark": c.dark,
            "header_bg": c.primary,
            "header_fg": "#FFFFFF",
            "panel_bg": c.dark if is_dark else c.light,
            "label_fg": c.fg,
            "entry_bg": getattr(c, "input_bg", c.bg),
            "border": c.secondary if is_dark else getattr(c, "border", "#CCCCCC"),
            "log_bg": c.dark if is_dark else c.bg,
            "log_fg": "#D4D4D4" if is_dark else c.fg,
            "link": c.info,
            "select_bg": c.primary,
            "select_fg": "#FFFFFF",
        }

    def _refresh_widgets(self) -> None:
        """遍历已注册的原生控件，调用回调刷新颜色。"""
        for entry in self._watched_widgets:
            try:
                cfg = entry["refresh"](self._colors)
                if cfg:
                    entry["widget"].configure(**cfg)
            except tk.TclError:
                pass  # 控件已销毁时静默跳过
