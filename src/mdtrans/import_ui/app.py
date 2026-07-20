"""MDTrans - 导入模式页面（其他格式 → Markdown）。

从 MarkitDownGUI/gui/_app.py 迁移，适配为 Navigator 的子页面。
与 ExportPage 保持 UI 一致性：统一使用 ttk.Treeview、tkinter.scrolledtext.ScrolledText、
ThemeManager 主题联动等。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

from mdtrans.gui._version import APP_VERSION
from mdtrans.gui._dialogs import DialogTheme
from mdtrans.gui._gui_helpers import (
    DEFAULT_LOG_HEIGHT,
    LABEL_COL_WIDTH,
    parse_dnd_paths,
    resolve_log_tag,
    create_log_section,
    create_action_buttons,
)
from mdtrans.gui._theme_manager import ThemeManager

# 文件后缀 → 可读类型名
_FILE_TYPE_MAP = {
    ".pdf": "PDF 文档",
    ".docx": "Word 文档",
    ".doc": "Word 文档(旧版)",
    ".xlsx": "Excel 表格",
    ".xls": "Excel 表格(旧版)",
    ".pptx": "PowerPoint 演示文稿",
    ".jpg": "JPEG 图片",
    ".jpeg": "JPEG 图片",
    ".png": "PNG 图片",
    ".gif": "GIF 图片",
    ".bmp": "BMP 图片",
    ".html": "HTML 网页",
    ".htm": "HTML 网页",
    ".csv": "CSV 数据",
    ".json": "JSON 数据",
    ".xml": "XML 数据",
    ".zip": "ZIP 压缩包",
    ".epub": "EPUB 电子书",
    ".wav": "WAV 音频",
    ".mp3": "MP3 音频",
    ".msg": "Outlook 邮件",
    ".ipynb": "Jupyter Notebook",
    ".rss": "RSS 订阅",
    ".rtf": "RTF 文档",
}

DEFAULT_LISTBOX_HEIGHT: int = 4


class ImportPage:
    """导入模式页面 — PDF/DOCX/PPTX/HTML/图片等 → Markdown。

    Args:
        parent_frame: 父容器 Frame（Navigator 传入）。
        root: Tkinter 根窗口。
        theme_manager: ThemeManager 实例。
        config: 导入配置字典。
        has_dnd: 是否支持拖拽。
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
        self.image_mode = tk.StringVar(value=config.get("image_mode", "file"))
        self.is_processing = False
        self.last_output_file: str | None = None

        # 覆盖确认状态
        self._overwrite_all = False
        self._skip_all = False

        self._build_ui()

    # ── IPage 接口 ──────────────────────────────────────────────────────────

    def on_activate(self) -> None:
        """页面被激活时调用。"""
        pass

    def on_deactivate(self) -> None:
        """页面被停用时保存配置。"""
        self._config["last_output_dir"] = self.output_dir.get()
        self._config["image_mode"] = self.image_mode.get()

    def destroy(self) -> None:
        """销毁页面。"""
        for widget in self._parent.winfo_children():
            widget.destroy()

    def log_message(self, message: str, tag: str | None = None) -> None:
        """向日志区域追加消息。"""
        if not hasattr(self, "log_text"):
            return
        self.log_text.configure(state="normal")
        t = tag or resolve_log_tag(message)
        self.log_text.insert(tk.END, message + "\n", t)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    # ── 对话框主题 ──────────────────────────────────────────────────────────

    def _get_dialog_theme(self) -> DialogTheme:
        """从 ThemeManager 构建对话框样式（与 ExportPage 一致）。"""
        c = self._tm.colors
        return DialogTheme(
            root=self.root,
            bg=c["bg"],
            header_bg=c["header_bg"],
            header_fg=c["header_fg"],
            label_fg=c["label_fg"],
            border_color=c["border"],
        )

    # ── 界面构建 ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        mf = ttk.Frame(self._parent, padding="14 10 14 6")
        mf.pack(fill=tk.BOTH, expand=True)
        mf.columnconfigure(0, minsize=LABEL_COL_WIDTH)
        mf.columnconfigure(1, weight=1)
        row = 0

        # 文件选择区域 — 使用 ttk.Treeview（与 ExportPage 一致）
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
        self.file_treeview.bind("<Delete>", lambda e: self.remove_selected_files())

        btn_col = ttk.Frame(ff)
        btn_col.grid(row=0, column=1, sticky=tk.N)
        ttk.Button(btn_col, text="添加文件", command=self.select_files,
                   style="primary.TButton", width=10).pack(anchor=tk.E, pady=(0, 4))
        ttk.Button(btn_col, text="删除选中", command=self.remove_selected_files,
                   style="danger.TButton", width=10).pack(anchor=tk.E, pady=(0, 4))
        ttk.Button(btn_col, text="清空列表", command=self.clear_file_list,
                   style="warning.TButton", width=10).pack(anchor=tk.E)
        row += 1
        
        # 选择保存位置
        ttk.Label(mf, text="保存位置:", font=("Microsoft YaHei UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        sf = ttk.Frame(mf)
        sf.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=4)
        sf.columnconfigure(0, weight=1)
        ttk.Entry(sf, textvariable=self.output_dir, state="readonly").grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 6))
        ttk.Button(sf, text="保存位置", command=self.select_output_dir,
                   style="primary.TButton", width=10).grid(row=0, column=1)
        row += 1

        # 图片处理方式
        ttk.Label(mf, text="图片处理:", font=("Microsoft YaHei UI", 9)).grid(
            row=row, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        rf = ttk.Frame(mf)
        rf.grid(row=row, column=1, sticky=tk.W, pady=4)
        ttk.Radiobutton(rf, text="提取为文件（推荐）", variable=self.image_mode,
                        value="file").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(rf, text="嵌入 base64", variable=self.image_mode,
                        value="embed").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(rf, text="忽略图片", variable=self.image_mode,
                        value="none").pack(side=tk.LEFT)
        row += 1

        # DOCX 选项占位：固定高度容器，与 ExportPage 的 DOCX 选项区域保持一致
        # 使两 Tab 页上半部编辑区域高度一致，分隔线/按钮位置与 ExportPage 对齐
        from mdtrans.gui._gui_helpers import DOCX_OPTIONS_HEIGHT
        docx_placeholder = ttk.Frame(mf, height=DOCX_OPTIONS_HEIGHT)
        docx_placeholder.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E))
        docx_placeholder.grid_propagate(False)
        row += 1

        # 分割线 + 操作按钮（与 ExportPage 共享布局）
        row, self.process_button, self.open_doc_button = create_action_buttons(
            mf, row,
            process_text="▶  开始处理",
            process_cmd=self.start_processing,
            open_output_dir_cmd=self.open_output_dir,
            open_last_doc_cmd=self.open_last_document,
        )

        # 日志区域（与 ExportPage 一致）
        row, self.log_text = create_log_section(
            mf, row, self._tm, [
                ("success", "#00AA00"), ("error", "#CC0000"), ("warning", "#CC9900"),
                ("info", "#0066CC"), ("arrow", "#666666"), ("complete", "#0066CC"),
                ("normal", self._tm.colors["log_fg"]),
            ])

        # 底部版本号
        lf = ttk.Frame(mf)
        lf.grid(row=row, column=0, columnspan=2, pady=(4, 2), sticky=(tk.W, tk.E))
        ttk.Label(lf, text=f"v{APP_VERSION}", font=("Microsoft YaHei UI", 9)).pack(side=tk.RIGHT)

        # Treeview 本地拖拽注册（与根窗口全局监听互备）
        if self.has_dnd:
            self._register_drop_target()

    # ── 拖拽 ──────────────────────────────────────────────────────────────

    def on_drop(self, event: Any) -> None:
        """处理拖拽放入的文件（由 Navigator.handle_drop 或 Treeview 本地事件调用）。

        自动筛选：仅接受 _FILE_TYPE_MAP 中定义的受支持格式。
        兼容 tkinterdnd2 的两种常见数据格式：\n 分隔 和 Tcl 列表格式。
        """
        raw_data = getattr(event, "data", "")
        if not raw_data:
            return
        # 优先用 newline 分隔格式解析（Windows 最常见）
        paths = parse_dnd_paths(raw_data)
        # 若结果不佳（0-1 条）且数据含多文件特征 → 尝试 Tcl splitlist
        if len(paths) <= 1 and ("{" in raw_data or raw_data.count(" ") > len(paths)):
            try:
                sp = self.root.splitlist(raw_data)
                if len(sp) > len(paths):
                    paths = list(sp)
            except Exception:
                pass
        if not paths:
            return
        accepted = 0
        for f in paths:
            ext = Path(f).suffix.lower()
            if ext in _FILE_TYPE_MAP or ext in (".txt", ".rtf"):
                if f not in self.input_files:
                    self.input_files.append(f)
                    accepted += 1
        if accepted:
            self._update_file_list()
            # 始终更新输出目录为拖入文件的目录
            if self.input_files:
                self.output_dir.set(str(Path(self.input_files[0]).parent))
            total = len(paths)
            if total == accepted:
                self.log_message(f"已拖入 {accepted} 个文件")
            else:
                self.log_message(f"已拖入 {accepted}/{total} 个文件（已自动筛除不支持的文件格式）")

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

    # ── 文件操作 ────────────────────────────────────────────────────────────

    def select_files(self) -> None:
        filetypes = [
            ("所有支持的文件",
             "*.pdf *.docx *.doc *.xlsx *.pptx *.jpg *.jpeg *.png "
             "*.html *.csv *.json *.xml *.zip *.epub"),
            ("PDF 文件", "*.pdf"),
            ("Word 文件", "*.docx *.doc"),
            ("Excel 文件", "*.xlsx"),
            ("PowerPoint 文件", "*.pptx"),
            ("图片文件", "*.jpg *.jpeg *.png"),
            ("HTML 文件", "*.html"),
            ("所有文件", "*.*"),
        ]
        files = filedialog.askopenfilenames(title="选择要转换的文件", filetypes=filetypes)
        if not files:
            return
        for f in files:
            if f not in self.input_files:
                self.input_files.append(f)
        self._update_file_list()
        if self.input_files:
            self.output_dir.set(str(Path(self.input_files[0]).parent))

    def select_output_dir(self) -> None:
        d = filedialog.askdirectory(title="选择保存位置")
        if d:
            self.output_dir.set(d)

    def _update_file_list(self) -> None:
        """更新文件 Treeview 显示。"""
        for item in self.file_treeview.get_children():
            self.file_treeview.delete(item)
        for f in self.input_files:
            name = Path(f).name
            if len(name) > 50:
                name = name[:47] + "..."
            self.file_treeview.insert("", tk.END, values=(name,))

    def remove_selected_files(self) -> None:
        selected = self.file_treeview.selection()
        for item_id in reversed(selected):
            index = self.file_treeview.index(item_id)
            self.file_treeview.delete(item_id)
            del self.input_files[index]

    def clear_file_list(self) -> None:
        self.input_files.clear()
        self.output_dir.set("")
        for item in self.file_treeview.get_children():
            self.file_treeview.delete(item)

    def open_output_dir(self) -> None:
        out = self.output_dir.get()
        if not out:
            messagebox.showwarning("警告", "请先选择保存位置！")
            return
        if not os.path.exists(out):
            messagebox.showerror("错误", f"目录不存在：{out}")
            return
        try:
            if sys.platform == "win32":
                if self.last_output_file and os.path.exists(self.last_output_file):
                    subprocess.run(["explorer", "/select,", self.last_output_file], check=False)
                else:
                    os.startfile(out)
            elif sys.platform == "darwin":
                if self.last_output_file and os.path.exists(self.last_output_file):
                    subprocess.run(["open", "-R", self.last_output_file], check=False)
                else:
                    subprocess.run(["open", out], check=False)
            else:
                os.system(f'xdg-open "{out}"')
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录：{e}")

    def open_last_document(self) -> None:
        if not self.last_output_file or not os.path.exists(self.last_output_file):
            messagebox.showwarning("警告", "没有可打开的文档！")
            return
        try:
            if sys.platform == "win32":
                os.startfile(self.last_output_file)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.last_output_file], check=False)
            else:
                subprocess.run(["xdg-open", self.last_output_file], check=False)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文档：{e}")

    def show_contact(self) -> None:
        messagebox.showinfo(
            "联系我们",
            "如有问题或建议，请访问：\n\n"
            "GitHub: https://github.com/microsoft/markitdown\n\n"
            "或提交 Issue 获取帮助。")

    # ── 覆盖确认 ────────────────────────────────────────────────────────────

    def _ask_overwrite(self, filename: str) -> bool:
        """批量覆盖确认（与 ExportPage 使用相同的 ask_overwrite_batch 对话框）。"""
        from mdtrans.gui._dialogs import ask_overwrite_batch
        should_continue, self._overwrite_all, self._skip_all = ask_overwrite_batch(
            self._get_dialog_theme(), filename,
            self._overwrite_all, self._skip_all,
        )
        return should_continue

    # ── 转换处理 ────────────────────────────────────────────────────────────

    def start_processing(self) -> None:
        if not self.input_files:
            messagebox.showwarning("警告", "请先选择要处理的文件！")
            return
        if not self.output_dir.get():
            messagebox.showwarning("警告", "请选择保存位置！")
            return
        self.process_button.configure(state="disabled")
        self.is_processing = True
        t = threading.Thread(target=self.process_files, daemon=True)
        t.start()

    def process_files(self) -> None:
        """后台线程：批量转换文件。"""
        self._overwrite_all = False
        self._skip_all = False
        try:
            total = len(self.input_files)
            self.log_message(f"开始处理 {total} 个文件...")
            for i, file_path in enumerate(self.input_files, 1):
                if not self.is_processing:
                    self.log_message("处理已取消")
                    break
                ext = Path(file_path).suffix.lower()
                file_type = _FILE_TYPE_MAP.get(ext, f"{ext.upper()} 文件")
                self.log_message(
                    f"[{i}/{total}] 正在转换: {Path(file_path).name} ({file_type})")
                self.convert_file(file_path)
                self.log_message(f"✓ 转换成功: {Path(file_path).stem}.md")
            self.log_message(f"\n处理完成！共处理 {total} 个文件。")
        except Exception as e:
            self.log_message(f"\n✗ 处理失败: {e}")
        finally:
            self.root.after(0, self.processing_complete)

    def convert_file(self, file_path: str) -> None:
        """转换单个文件并写入输出目录。"""
        try:
            stem = Path(file_path).stem
            ext = Path(file_path).suffix.lower()

            if ext == ".doc":
                self.log_message("  ✗ 暂不支持 .doc 格式")
                self.log_message("  → 请使用 Microsoft Word 或 LibreOffice 手动转换为 .docx")
                self.log_message("  → 转换步骤：打开 .doc 文件 → 另存为 .docx → 重新处理")
                raise RuntimeError("不支持的格式：.doc 文件。请先转换为 .docx")

            from markitdown import MarkItDown

            self.log_message("  → 初始化 MarkItDown 转换器...")

            convert_kwargs = {}
            mode = self.image_mode.get()
            if ext in (".docx",):
                if mode == "file":
                    images_dir = Path(self.output_dir.get()) / f"{stem}_images"
                    convert_kwargs["docx_images_dir"] = str(images_dir)
                elif mode == "embed":
                    # 标记为 embed 模式，后续会通过 mammoth data URI 处理
                    convert_kwargs["docx_embed_images"] = True
                    convert_kwargs["keep_data_uris"] = True
            elif ext in (".pptx",):
                if mode == "file":
                    images_dir = Path(self.output_dir.get()) / f"{stem}_images"
                    convert_kwargs["pptx_images_dir"] = str(images_dir)
                elif mode == "embed":
                    convert_kwargs["pptx_embed_images"] = True
            elif ext in (".epub",):
                if mode == "file":
                    images_dir = Path(self.output_dir.get()) / f"{stem}_images"
                    convert_kwargs["epub_images_dir"] = str(images_dir)
                elif mode == "embed":
                    convert_kwargs["epub_embed_images"] = True
            else:
                if mode == "embed":
                    convert_kwargs["keep_data_uris"] = True

            # DOCX embed 模式：修补 DocxConverter，让 mammoth 生成 data URI
            _restore_patch = False
            if ext in (".docx",) and mode == "embed":
                _restore_patch = self._patch_docx_converter_for_embed()

            try:
                result = MarkItDown().convert(file_path, **convert_kwargs)
            finally:
                if _restore_patch:
                    self._unpatch_docx_converter()

            output_file = Path(self.output_dir.get()) / f"{stem}.md"
            self.log_message(f"  → 保存结果到: {output_file}")

            if output_file.exists():
                if self._overwrite_all:
                    pass
                elif self._skip_all:
                    self.log_message(f"  ✗ 已跳过: {output_file.name}")
                    return
                elif not self._ask_overwrite(output_file.name):
                    self.log_message(f"  ✗ 已跳过: {output_file.name}")
                    return

            output_file.write_text(result.text_content, encoding="utf-8")
            self.last_output_file = str(output_file)
        except ImportError as e:
            raise RuntimeError(f"模块导入失败: {e}") from e
        except Exception as e:
            raise RuntimeError(f"转换文件 {file_path} 失败: {e}") from e

    # ── DOCX 图片嵌入修补 ─────────────────────────────────────────────────────

    @staticmethod
    def _patch_docx_converter_for_embed() -> bool:
        """修补 markitdown 的 DocxConverter，使 mammoth 将图片渲染为 data URI。

        当 convert_kwargs 含 docx_embed_images=True 时，使用
        mammoth.images.data_uri() 作为图片处理器，生成 data:image/... 引用，
        配合 keep_data_uris=True 确保 _CustomMarkdownify 不截断。

        Returns:
            是否修补成功。成功返回 True，后续应调用 _unpatch_docx_converter。
        """
        try:
            import markitdown.converters._docx_converter as docx_mod
            from markitdown.converter_utils.docx.pre_process import pre_process_docx

            if hasattr(docx_mod.DocxConverter, "_patched") and docx_mod.DocxConverter._patched:
                return False  # 已修补，无需重复

            _orig_convert = docx_mod.DocxConverter.convert

            def _patched_convert(self, file_stream, stream_info, **kwargs):
                if kwargs.get("docx_embed_images"):
                    # 使用 data URI 图片处理器渲染 DOCX 中的图片
                    pre_processed = pre_process_docx(file_stream)
                    html = docx_mod.mammoth.convert_to_html(
                        pre_processed,
                        style_map=kwargs.get("style_map"),
                        convert_image=docx_mod.mammoth.images.data_uri,
                    ).value
                    # 弹出已显式传出的参数，避免与 **kwargs 冲突
                    kwargs.pop("keep_data_uris", None)
                    # 传出 keep_data_uris=True，确保 _CustomMarkdownify 不截断
                    return self._html_converter.convert_string(
                        html, keep_data_uris=True, **kwargs,
                    )
                return _orig_convert(self, file_stream, stream_info, **kwargs)

            docx_mod.DocxConverter.convert = _patched_convert
            docx_mod.DocxConverter._patched = True
            docx_mod.DocxConverter._orig_convert = _orig_convert
            return True
        except ImportError:
            return False

    @staticmethod
    def _unpatch_docx_converter() -> None:
        """恢复 DocxConverter 的原始 convert 方法。"""
        try:
            import markitdown.converters._docx_converter as docx_mod
            if hasattr(docx_mod.DocxConverter, "_orig_convert"):
                docx_mod.DocxConverter.convert = docx_mod.DocxConverter._orig_convert
                docx_mod.DocxConverter._patched = False
                del docx_mod.DocxConverter._orig_convert
        except ImportError:
            pass

    def processing_complete(self) -> None:
        self.is_processing = False
        self.process_button.configure(state="normal")
        if (len(self.input_files) == 1
                and self.last_output_file
                and os.path.exists(self.last_output_file)):
            self.open_doc_button.configure(state="normal")
        else:
            self.open_doc_button.configure(state="disabled")





