"""MDTrans - 导航器。

Tab 切换导航，管理导入/导出两个模式页面的切换、主题同步、共享状态。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from mdtrans.__about__ import __version__
from mdtrans.gui._dialogs import DialogTheme, show_about
from mdtrans.gui._theme_manager import ThemeManager
from mdtrans.export_ui.app import ExportPage
from mdtrans.import_ui.app import ImportPage


class Navigator:
    """MDTrans 主导航器。

    负责 Tab 切换、拖拽分发、主题同步、配置持久化。

    Args:
        root: Tkinter 根窗口。
        theme_manager: ThemeManager 实例。
        config: 配置字典。
        has_dnd: 是否支持拖拽。
    """

    TAB_IMPORT = "import"
    TAB_EXPORT = "export"

    def __init__(
        self,
        root: tk.Tk,
        theme_manager: ThemeManager,
        config: dict,
        has_dnd: bool = False,
    ) -> None:
        self.root = root
        self._tm = theme_manager
        self._config = config
        saved_tab = str(config.get("active_tab", self.TAB_IMPORT))
        self._current_tab: str = (
            saved_tab if saved_tab in {self.TAB_IMPORT, self.TAB_EXPORT}
            else self.TAB_IMPORT
        )
        self.has_dnd = has_dnd

        # 窗口标题
        root.title(f"MDTrans v{__version__} — 双向文档转换工具")

        # 主容器
        self._main = ttk.Frame(root)
        self._main.pack(fill=tk.BOTH, expand=True)

        # ── Tab 栏 ────────────────────────────────────────────────────────
        self._tab_bar = ttk.Frame(self._main)
        self._tab_bar.pack(fill=tk.X, padx=14, pady=(10, 0))

        # 导入 Tab 按钮 — 使用 Label 实现更丰富的高亮效果
        self._import_tab_btn = tk.Label(
            self._tab_bar,
            text="📥  To Markdown",
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
            padx=16,
            pady=6,
        )
        self._import_tab_btn.pack(side=tk.LEFT, padx=(0, 2))
        self._import_tab_btn.bind("<ButtonRelease-1>", lambda e: self.switch_tab(self.TAB_IMPORT))

        # 导出 Tab 按钮
        self._export_tab_btn = tk.Label(
            self._tab_bar,
            text="📤  From Markdown",
            font=("Microsoft YaHei UI", 9, "bold"),
            cursor="hand2",
            padx=16,
            pady=6,
        )
        self._export_tab_btn.pack(side=tk.LEFT)
        self._export_tab_btn.bind("<ButtonRelease-1>", lambda e: self.switch_tab(self.TAB_EXPORT))

        # Tab 栏右侧操作按钮组
        action_frame = ttk.Frame(self._tab_bar)
        action_frame.pack(side=tk.RIGHT)

        self._about_btn = ttk.Button(
            action_frame,
            text="关于",
            command=self._show_about,
            width=6,
        )
        self._about_btn.pack(side=tk.RIGHT, padx=(4, 0))

        self._theme_btn = ttk.Button(
            action_frame,
            text="亮色主题" if self._tm.is_dark else "暗色主题",
            command=self._toggle_theme,
            width=10,
        )
        self._theme_btn.pack(side=tk.RIGHT)

        # ── 内容区域 ──────────────────────────────────────────────────────
        self._content = ttk.Frame(self._main)
        self._content.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        # 创建两个页面（各自使用独立的 Frame）
        self._import_frame = ttk.Frame(self._content)
        self._export_frame = ttk.Frame(self._content)

        self._import_page = ImportPage(
            self._import_frame, root, theme_manager, config.get("import", {}),
            has_dnd=has_dnd,
        )
        self._export_page = ExportPage(
            self._export_frame, root, theme_manager, config.get("export", {}),
            has_dnd=has_dnd,
        )

        # [修改] 原因：恢复上次关闭时激活的Tab页面
        initial_frame = (
            self._import_frame
            if self._current_tab == self.TAB_IMPORT
            else self._export_frame
        )
        initial_frame.pack(fill=tk.BOTH, expand=True)
        self._update_tab_style()

    # ── Tab 切换 ──────────────────────────────────────────────────────────

    def switch_tab(self, tab: str) -> None:
        """切换到指定 Tab。

        Args:
            tab: ``"import"`` 或 ``"export"``。
        """
        if tab not in {self.TAB_IMPORT, self.TAB_EXPORT}:
            return
        # [修改] 原因：记录当前Tab，供下次启动恢复
        self._config["active_tab"] = tab
        if tab == self._current_tab:
            return

        # 隐藏当前页
        if self._current_tab == self.TAB_IMPORT:
            self._import_frame.pack_forget()
            self._import_page.on_deactivate()
        else:
            self._export_frame.pack_forget()
            self._export_page.on_deactivate()

        # 显示新页
        self._current_tab = tab
        if tab == self.TAB_IMPORT:
            self._import_frame.pack(fill=tk.BOTH, expand=True)
            self._import_page.on_activate()
        else:
            self._export_frame.pack(fill=tk.BOTH, expand=True)
            self._export_page.on_activate()

        self._update_tab_style()

    def save_state(self) -> None:
        """将两个页面的当前状态同步到配置对象，供窗口关闭前保存。"""
        # [修改] 原因：直接关闭窗口时不会切换Tab，必须主动触发页面状态同步
        self._config["active_tab"] = self._current_tab
        self._import_page.on_deactivate()
        self._export_page.on_deactivate()

    def _update_tab_style(self) -> None:
        """更新 Tab 按钮的样式：激活按钮使用主题 primary 色作为背景。"""
        c = self._tm.colors
        bg_active = c["primary"]
        fg_active = "#FFFFFF"  # 白色字体始终可读
        bg_normal = c["bg"]
        fg_normal = c["fg"]

        if self._current_tab == self.TAB_IMPORT:
            self._import_tab_btn.configure(bg=bg_active, fg=fg_active)
            self._export_tab_btn.configure(bg=bg_normal, fg=fg_normal)
        else:
            self._export_tab_btn.configure(bg=bg_active, fg=fg_active)
            self._import_tab_btn.configure(bg=bg_normal, fg=fg_normal)

    # ── 拖拽分发 ─────────────────────────────────────────────────────────

    def handle_drop(self, event: Any) -> None:
        """分发拖拽事件到当前激活页面。

        Args:
            event: tkinterdnd2 拖拽事件。
        """
        if self._current_tab == self.TAB_IMPORT:
            self._import_page.on_drop(event)
        else:
            self._export_page.on_drop(event)

    # ── 主题切换 ──────────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        """切换明暗主题并更新按钮文本。"""
        self._tm.toggle()
        self._theme_btn.configure(
            text="亮色主题" if self._tm.is_dark else "暗色主题"
        )
        # 刷新 Tab 按钮颜色以匹配新主题
        self._update_tab_style()
        # 持久化
        self._config["theme"] = "dark" if self._tm.is_dark else "light"
        from mdtrans.gui._config import save_config

        save_config(self._config)

    def get_dialog_root(self) -> tk.Tk:
        """返回根窗口（供对话框使用）。"""
        return self.root


    def _show_about(self) -> None:
        """显示关于对话框。"""
        c = self._tm.colors
        theme = DialogTheme(
            root=self.root,
            bg=c["bg"],
            header_bg=c["header_bg"],
            header_fg=c["header_fg"],
            label_fg=c["label_fg"],
            border_color=c["border"],
        )
        show_about(theme)
