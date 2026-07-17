"""MDTrans - GUI 启动入口。

初始化 Tkinter 根窗口、ttkbootstrap 主题、ThemeManager、配置，
创建 Navigator 并启动主循环。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 确保 src/ 在 sys.path 中（开发环境）
_project_root = Path(__file__).resolve().parent.parent.parent  # MDTrans/
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _preconfigure_pandoc() -> None:
    """PyInstaller 打包环境下预配置 Pandoc 路径。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        pandoc_exe = Path(meipass) / "pypandoc" / "files" / "pandoc.exe"
        if pandoc_exe.exists():
            os.environ["PYPANDOC_PANDOC"] = str(pandoc_exe)


def main() -> None:
    """MDTrans 主入口。"""
    # ── 前置配置 ──────────────────────────────────────────────────────────
    _preconfigure_pandoc()

    # ── Tkinter 初始化 ────────────────────────────────────────────────────
    has_dnd = False
    try:
        from tkinterdnd2 import TkinterDnD

        root = TkinterDnD.Tk()
        has_dnd = True
    except Exception:
        import tkinter as tk

        root = tk.Tk()

    root.title("MDTrans — 双向文档转换工具")

    # ── 主题管理 ──────────────────────────────────────────────────────────
    from ttkbootstrap import Style

    from mdtrans.gui._config import load_config, save_config
    from mdtrans.gui._theme_manager import ThemeManager

    config = load_config()
    theme_mode = config.get("theme", "light")
    initial_theme = "darkly" if theme_mode == "dark" else "flatly"
    style = Style(theme=initial_theme)
    theme_manager = ThemeManager(style, mode=theme_mode)

    # ── 窗口尺寸与居中 ────────────────────────────────────────────────────
    window_width = config.get("window", {}).get("width", 750)
    window_height = config.get("window", {}).get("height", 560)
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(
        f"{window_width}x{window_height}"
        f"+{(sw - window_width) // 2}+{(sh - window_height) // 2}"
    )
    root.resizable(True, True)
    root.minsize(600, 400)

    # ── 窗口图标 ──────────────────────────────────────────────────────────
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "MDTrans.App"
            )
        from mdtrans.gui._gui_helpers import get_icon_path

        icon_path = get_icon_path()
        if icon_path:
            root.iconbitmap(default=icon_path)
    except Exception:
        pass

    # ── 创建导航器 ────────────────────────────────────────────────────────
    from mdtrans.app.navigator import Navigator

    navigator = Navigator(root, theme_manager, config, has_dnd=has_dnd)

    # ── 全局拖拽绑定 ──────────────────────────────────────────────────────
    if has_dnd:
        from tkinterdnd2 import DND_FILES

        root.drop_target_register(DND_FILES)
        root.dnd_bind("<<Drop>>", lambda e: navigator.handle_drop(e))

    # ── 窗口关闭时保存配置 ────────────────────────────────────────────────
    def _on_close() -> None:
        save_config(config)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    # ── 启动 ──────────────────────────────────────────────────────────────
    root.mainloop()


if __name__ == "__main__":
    main()
