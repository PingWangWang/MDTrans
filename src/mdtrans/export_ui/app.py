"""MDTrans - 导出模式页面（Markdown → 其他格式）。

从 MarkdownExporterGUI/gui/_app.py 迁移，适配为 Navigator 的子页面。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from mdtrans.export_ui.conversion import OUTPUT_FORMATS, ConversionOptions, ConversionService
from mdtrans.gui._dialogs import (
    DialogTheme,
    ask_file_locked,
    ask_overwrite_batch,
)
from mdtrans.gui._gui_helpers import (
    DEFAULT_LOG_HEIGHT,
    LABEL_COL_WIDTH,
    check_dependencies,
    get_icon_path,
    open_file_or_dir,
    parse_dnd_paths,
    resolve_log_tag,
    create_log_section,
    create_action_buttons,
)
from mdtrans.gui._theme_manager import ThemeManager
from mdtrans.gui._version import APP_VERSION

DEFAULT_WINDOW_WIDTH: int = 750
DEFAULT_LISTBOX_HEIGHT: int = 4


class ExportPage:
    """导出模式页面 — Markdown → DOCX/PDF/HTML。

    Args:
        parent_frame: 父容器 Frame（Navigator 传入）。
        root: Tkinter 根窗口。
        theme_manager: ThemeManager 实例。
        config: 导出配置字典。
    """

    def __init__(
        self,
        parent_frame: ttk.Frame,
        root: tk.Tk,
        theme_manager: ThemeManager,
        config: dict,
        has_dnd: bool = False,
    ) -> None:
        self._parent = parent_frame
        self.root = root
        self._tm = theme_manager
        self._config = config
        self.has_dnd = has_dnd

        self.input_files: list[str] = []
        self.output_dir = tk.StringVar(value="")  # 每次启动清空，拖入文件后自动更新
        self.output_format = tk.StringVar(value="DOCX")
        self.is_processing: bool = False
        self.last_output_file: str | None = None
        self.last_single_output: str | None = None
        self.use_template = tk.BooleanVar(value=config.get("use_template", False))
        self.template_path = tk.StringVar(value=config.get("template_path", ""))
        self.save_mermaid_images = tk.BooleanVar(value=config.get("save_mermaid_images", False))
        self.convert_mermaid_images = tk.BooleanVar(value=config.get("convert_mermaid_images", True))

        self._conversion: ConversionService | None = None
        self._setup_gui_logging()
        self._create_conversion_service()
        self._build_ui()

    # ── IPage 接口 ──────────────────────────────────────────────────────────

    def on_activate(self) -> None:
        """页面被激活时调用。"""
        pass

    def on_deactivate(self) -> None:
        """页面被停用时保存配置。"""
        self._config["last_output_dir"] = self.output_dir.get()
        self._config["last_format"] = self.get_selected_format()
        self._config["use_template"] = self.use_template.get()
        self._config["template_path"] = self.template_path.get()
        self._config["save_mermaid_images"] = self.save_mermaid_images.get()
        self._config["convert_mermaid_images"] = self.convert_mermaid_images.get()

    def destroy(self) -> None:
        """销毁页面。"""
        for widget in self._parent.winfo_children():
            widget.destroy()

    # ── 转换服务 ────────────────────────────────────────────────────────────

    def _create_conversion_service(self) -> None:
        """创建转换服务实例——ExportPage 自身实现 OverwriteStrategy 协议。"""
        self._conversion = ConversionService(
            strategy=self,
            log_callback=self.log_message,
        )

    def _get_dialog_theme(self) -> DialogTheme:
        """从 ThemeManager 构建对话框样式。"""
        c = self._tm.colors
        return DialogTheme(
            root=self.root,
            bg=c["bg"],
            header_bg=c["header_bg"],
            header_fg=c["header_fg"],
            label_fg=c["label_fg"],
            border_color=c["border"],
        )

    # ── 覆盖确认策略实现 ────────────────────────────────────────────────────

    def ask_overwrite(
        self, filename: str, *, is_batch: bool, overwrite_all: bool, skip_all: bool,
    ) -> tuple[bool, bool, bool]:
        theme = self._get_dialog_theme()
        return ask_overwrite_batch(theme, filename, overwrite_all, skip_all)

    def ask_file_locked(self, filename: str) -> bool:
        theme = self._get_dialog_theme()
        return ask_file_locked(theme, filename)

    # ── 日志回调 ────────────────────────────────────────────────────────────

    def _setup_gui_logging(self) -> None:
        try:
            from mdtrans.export_services.utils.logger_utils import set_gui_log_callback

            def gui_log_callback(message: str) -> None:
                self.root.after(0, lambda: self._log_message_from_service(message))

            set_gui_log_callback(gui_log_callback)
        except ImportError:
            pass

    def _log_message_from_service(self, message: str) -> None:
        self.log_message(f"[服务] {message}")

    def log_message(self, message: str, tag: str | None = None) -> None:
        """向日志区域追加消息。"""
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        t = tag or resolve_log_tag(message)
        self.log_text.insert(tk.END, message + "\n", t)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    # ── 界面构建 ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        mf = ttk.Frame(self._parent, padding="14 10 14 6")
        mf.pack(fill=tk.BOTH, expand=True)
        mf.columnconfigure(0, minsize=LABEL_COL_WIDTH)
        mf.columnconfigure(1, weight=1)
        self._main_frame = mf
        row = 0

        row = self._create_file_section(mf, row)
        row = self._create_output_dir_section(mf, row)
        row = self._create_format_section(mf, row)
        row = self._create_docx_options_section(mf, row)
        # 分隔线 + 操作按钮（与 ImportPage 共享布局）
        row, self.process_button, self.open_doc_button = create_action_buttons(
            mf, row,
            process_text="▶  开始转换",
            process_cmd=self.start_processing,
            open_output_dir_cmd=self.open_output_dir,
            open_last_doc_cmd=self.open_last_document,
        )
        # 日志区域（与 ImportPage 共享布局）
        row, self.log_text = create_log_section(
            mf, row, self._tm, [
                ("success", "#00AA00"), ("error", "#CC0000"), ("warning", "#CC9900"),
                ("info", "#0066CC"), ("arrow", "#666666"), ("complete", "#0066CC"),
                ("summary", "#CC6600"), ("service", "#666666"),
                ("normal", self._tm.colors["log_fg"]),
            ])
        self._create_footer(mf, row)

        # Treeview 本地拖拽注册（与根窗口全局监听互备）
        if self.has_dnd:
            self._register_drop_target()

    # ── 界面子区域 ────────────────────────────────────────────────────────

    def _create_file_section(self, mf: ttk.Frame, row: int) -> int:
        ttk.Label(mf, text="待转文件:", font=("Microsoft YaHei UI", 9)).grid(
            row=row, column=0, sticky=tk.NW, pady=4, padx=(0, 8))
        ff = ttk.Frame(mf)
        ff.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=4)
        ff.columnconfigure(0, weight=1)

        list_frame = ttk.Frame(ff)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))
        list_frame.columnconfigure(0, weight=1)

        self.file_treeview = ttk.Treeview(
            list_frame, columns=("filename",), show="",
            height=DEFAULT_LISTBOX_HEIGHT + 1, selectmode="extended")
        self.file_treeview.column("filename", width=400, minwidth=200)
        self.file_treeview.grid(row=0, column=0, sticky=(tk.W, tk.E))
        list_sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_treeview.yview)
        self.file_treeview.configure(yscrollcommand=list_sb.set)
        list_sb.grid(row=0, column=1, sticky=(tk.N, tk.S))

        btn_col = ttk.Frame(ff)
        btn_col.grid(row=0, column=1, sticky=tk.N)
        ttk.Button(btn_col, text="添加文件", command=self.select_files,
                   style="primary.TButton", width=10).pack(anchor=tk.E, pady=(0, 4))
        ttk.Button(btn_col, text="删除选中", command=self.remove_selected_files,
                   style="danger.TButton", width=10).pack(anchor=tk.E, pady=(0, 4))
        ttk.Button(btn_col, text="清空列表", command=self.clear_files,
                   style="warning.TButton", width=10).pack(anchor=tk.E)
        self.file_treeview.bind("<Delete>", lambda e: self.remove_selected_files())
        return row + 1

    def _create_output_dir_section(self, mf: ttk.Frame, row: int) -> int:
        ttk.Label(mf, text="保存位置:", font=("Microsoft YaHei UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        sf = ttk.Frame(mf)
        sf.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=4)
        sf.columnconfigure(0, weight=1)
        ttk.Entry(sf, textvariable=self.output_dir, state="readonly").grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))
        ttk.Button(sf, text="保存位置", command=self.select_output_dir,
                   style="primary.TButton", width=10).grid(row=0, column=1)
        return row + 1

    def _create_format_section(self, mf: ttk.Frame, row: int) -> int:
        ttk.Label(mf, text="输出格式:", font=("Microsoft YaHei UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        cf = ttk.Frame(mf)
        cf.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=4)
        format_list = [f"{desc} ({ext})" for desc, ext in OUTPUT_FORMATS.values()]
        self.format_combo = ttk.Combobox(cf, values=format_list, state="readonly", width=30)
        self.format_combo.set("Word 文档 (.docx)")
        self.format_combo.grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.format_combo.bind("<<ComboboxSelected>>", self.on_format_change)
        return row + 1

    def _create_docx_options_section(self, mf: ttk.Frame, row: int) -> int:
        """创建 DOCX 专属选项区域（模板 + Mermaid 设置）。

        使用固定高度容器统一占位，使两 Tab 页上半部编辑区域高度一致；
        切换输出格式时容器始终保留高度，仅显隐内部子控件。
        """
        from mdtrans.gui._gui_helpers import DOCX_OPTIONS_HEIGHT, LABEL_COL_WIDTH

        container = ttk.Frame(mf, height=DOCX_OPTIONS_HEIGHT)
        container.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E))
        container.grid_propagate(False)
        container.columnconfigure(0, minsize=LABEL_COL_WIDTH)
        container.columnconfigure(1, weight=1)
        self._docx_frame = container

        r = 0  # 容器内行号

        # ── 模板行 ──
        self.template_label = ttk.Label(container, text="文档模板:",
                                        font=("Microsoft YaHei UI", 9))
        self.template_label.grid(row=r, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        tf = ttk.Frame(container)
        tf.grid(row=r, column=1, sticky=(tk.W, tk.E), pady=4)
        tf.columnconfigure(1, weight=1)
        self.template_check = ttk.Checkbutton(tf, text="", variable=self.use_template,
                                              command=self.on_template_toggle)
        self.template_check.grid(row=0, column=0, padx=(0, 4))
        self.template_path_entry = ttk.Entry(tf, textvariable=self.template_path,
                                             state="readonly")
        self.template_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 4))
        self.select_template_btn = ttk.Button(
            tf, text="选择模板", command=self.select_template,
            state="disabled", style="primary.TButton", width=10)
        self.select_template_btn.grid(row=0, column=2)
        self.template_frame = tf
        if not self.use_template.get():
            self.select_template_btn.configure(state="disabled")
        r += 1

        # ── Mermaid 转换行 ──
        self.convert_mermaid_label = ttk.Label(container, text="转换图表:",
                                               font=("Microsoft YaHei UI", 9))
        self.convert_mermaid_label.grid(row=r, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        mf1 = ttk.Frame(container)
        mf1.grid(row=r, column=1, sticky=tk.W, pady=4)
        ttk.Checkbutton(mf1, text="", variable=self.convert_mermaid_images).pack(
            side=tk.LEFT, padx=(0, 8))
        self.convert_mermaid_frame = mf1
        r += 1

        # ── Mermaid 保存行 ──
        self.save_mermaid_label = ttk.Label(container, text="保存图片:",
                                            font=("Microsoft YaHei UI", 9))
        self.save_mermaid_label.grid(row=r, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        mf2 = ttk.Frame(container)
        mf2.grid(row=r, column=1, sticky=tk.W, pady=4)
        ttk.Checkbutton(mf2, text="", variable=self.save_mermaid_images).pack(
            side=tk.LEFT, padx=(0, 8))
        self.save_mermaid_frame = mf2
        r += 1

        return row + 1

    def _create_footer(self, mf: ttk.Frame, row: int) -> None:
        lf = ttk.Frame(mf)
        lf.grid(row=row, column=0, columnspan=2, pady=(4, 2), sticky=(tk.W, tk.E))
        ttk.Label(lf, text=f"v{APP_VERSION}", font=("Microsoft YaHei UI", 9)).pack(side=tk.RIGHT)

    # ── 交互回调 ────────────────────────────────────────────────────────────

    def on_format_change(self, event: tk.Event | None = None) -> None:
        output_format = self.get_selected_format()
        visible = output_format == "DOCX"
        for child in self._docx_frame.winfo_children():
            child.grid() if visible else child.grid_remove()
        if not visible:
            self.use_template.set(False)
            self.template_path.set("")
            self.save_mermaid_images.set(False)
            self.convert_mermaid_images.set(True)

    def on_template_toggle(self) -> None:
        if self.use_template.get():
            self.select_template_btn.configure(state="normal")
        else:
            self.select_template_btn.configure(state="disabled")
            self.template_path.set("")

    def select_template(self) -> None:
        template = filedialog.askopenfilename(
            title="选择 DOCX 模板文件",
            filetypes=[("Word 模板文件", "*.docx"), ("所有文件", "*.*")])
        if template:
            self.template_path.set(template)
            self.log_message(f"已选择模板: {Path(template).name}")

    def on_drop(self, event: Any) -> None:
        """处理拖拽放入的文件（由 Navigator.handle_drop 或 Treeview 本地事件调用）。

        自动筛选：仅接受 .md / .markdown 文件。
        兼容 tkinterdnd2 的两种常见数据格式：\n 分隔 和 Tcl 列表格式。
        """
        raw_data = getattr(event, "data", "")
        if not raw_data:
            return
        # 优先用 newline 分隔格式解析（Windows 最常见）
        files = parse_dnd_paths(raw_data)
        # 若结果不佳（0-1 条）且数据含多文件特征 → 尝试 Tcl splitlist
        if len(files) <= 1 and ("{" in raw_data or raw_data.count(" ") > len(files)):
            try:
                sp = self.root.splitlist(raw_data)
                if len(sp) > len(files):
                    files = list(sp)
            except Exception:
                pass
        if not files:
            return
        # 筛选支持的文档类型
        md_files = [f for f in files if f.lower().endswith((".md", ".markdown"))]
        if not md_files:
            self.log_message("✗ 拖入的文件中不含 .md / .markdown 文件，已全部忽略")
            return
        self._add_files(md_files)
        total = len(files)
        accepted = len(md_files)
        if total == accepted:
            self.log_message(f"已拖入 {accepted} 个 Markdown 文件")
        else:
            self.log_message(f"已拖入 {accepted}/{total} 个文件（已自动筛除非 Markdown 文件）")

    def _register_drop_target(self) -> None:
        """注册 Treeview 为拖拽目标（与根窗口全局监听互备）。"""
        """注册 Treeview 为拖拽目标（与根窗口全局监听互备）。"""
        try:
            from tkinterdnd2 import DND_FILES
            self.file_treeview.drop_target_register(DND_FILES)
            self.file_treeview.dnd_bind("<<Drop>>", self._on_drop_local)
        except Exception:
            pass

    def _on_drop_local(self, event: Any) -> None:
        """处理 Treeview 本地拖拽事件。"""
        self.on_drop(event)

    def select_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="选择 Markdown 文件",
            filetypes=[("Markdown 文件", "*.md *.markdown"), ("所有文件", "*.*")])
        if not files:
            return
        self._add_files(list(files))

    def _add_files(self, files: list[str]) -> None:
        existing = set(self.input_files)
        new_files = [f for f in files if f not in existing]
        for f in new_files:
            self.input_files.append(f)
            self.file_treeview.insert("", tk.END, values=(Path(f).name,))
        self._update_output_dir_from_files()

    def _update_output_dir_from_files(self) -> None:
        """将输出目录更新为第一个输入文件所在目录。"""
        if self.input_files:
            self.output_dir.set(str(Path(self.input_files[0]).parent))

    def clear_files(self) -> None:
        self.input_files = []
        for item in self.file_treeview.get_children():
            self.file_treeview.delete(item)
        self.output_dir.set("")

    def remove_selected_files(self) -> None:
        selected = self.file_treeview.selection()
        for item_id in reversed(selected):
            index = self.file_treeview.index(item_id)
            self.file_treeview.delete(item_id)
            del self.input_files[index]

    def select_output_dir(self) -> None:
        d = filedialog.askdirectory(title="选择保存位置")
        if d:
            self.output_dir.set(d)

    def open_output_dir(self) -> None:
        out = self.output_dir.get()
        if not out:
            messagebox.showwarning("警告", "请先选择保存位置！")
            return
        if not os.path.exists(out):
            messagebox.showerror("错误", f"目录不存在：{out}")
            return
        try:
            select_file = self.last_output_file if self.last_output_file else None
            open_file_or_dir(out, select_in_explorer=bool(select_file and os.path.exists(select_file)))
            if sys.platform == "win32" and select_file and os.path.exists(select_file):
                subprocess.run(["explorer", "/select,", select_file], check=False)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录：{e}")

    def get_selected_format(self) -> str:
        selected = self.format_combo.get()
        for code, (desc, ext) in OUTPUT_FORMATS.items():
            if f"{desc} ({ext})" == selected:
                return code
        return "DOCX"

    def open_last_document(self) -> None:
        path = self.last_single_output
        if not path or not os.path.exists(path):
            messagebox.showwarning("警告", "文档不存在或尚未转换。")
            return
        try:
            open_file_or_dir(path)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文档：{e}")

    # ── 转换处理 ────────────────────────────────────────────────────────────

    def start_processing(self) -> None:
        if not self.input_files:
            messagebox.showwarning("警告", "请先选择要处理的文件！")
            return
        if not self.output_dir.get():
            messagebox.showwarning("警告", "请选择保存位置！")
            return
        output_format = self.get_selected_format()
        self.log_message(f"输出格式: {OUTPUT_FORMATS[output_format][0]}")
        self.last_single_output = None
        self.open_doc_button.configure(state="disabled")
        self.process_button.configure(state="disabled")
        self.is_processing = True
        t = threading.Thread(target=self._process_files_thread, daemon=True)
        t.start()

    def _process_files_thread(self) -> None:
        assert self._conversion is not None
        try:
            options = ConversionOptions(
                format_code=self.get_selected_format(),
                use_template=self.use_template.get(),
                template_path=self.template_path.get(),
                save_mermaid_images=self.save_mermaid_images.get(),
                convert_mermaid_images=self.convert_mermaid_images.get(),
            )
            converted = self._conversion.process_batch(
                self.input_files, self.output_dir.get(), options)
            if len(converted) == 1:
                self.last_single_output = converted[0]
        except Exception as e:
            self.log_message(f"\n✗ 处理失败: {e}")
        finally:
            self.root.after(0, self._processing_complete)

    def _processing_complete(self) -> None:
        self.is_processing = False
        self.process_button.configure(state="normal")
        if self.last_single_output and os.path.exists(self.last_single_output):
            self.open_doc_button.configure(state="normal")
        else:
            self.open_doc_button.configure(state="disabled")


