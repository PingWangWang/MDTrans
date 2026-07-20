"""MDTrans - 导出转换业务逻辑层。

从 MarkdownExporterGUI 迁移，导入路径适配为 mdtrans.export_services。
与 GUI 框架完全解耦，通过 OverwriteStrategy Protocol 处理覆盖确认等交互。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

# 输出格式定义：{格式代码: (描述, 扩展名)}
OUTPUT_FORMATS: dict[str, tuple[str, str]] = {
    "DOCX": ("Word 文档", ".docx"),
    "PDF": ("PDF 文档", ".pdf"),
    "HTML": ("HTML 网页", ".html"),
    "IMAGE": ("图片", ".png"),
}


# ── 协议与数据类 ─────────────────────────────────────────────────────────────


@runtime_checkable
class OverwriteStrategy(Protocol):
    """覆盖确认策略，由 GUI 层实现。"""

    def ask_overwrite(
        self, filename: str, *, is_batch: bool, overwrite_all: bool, skip_all: bool,
    ) -> tuple[bool, bool, bool]:
        ...

    def ask_file_locked(self, filename: str) -> bool:
        ...


@dataclass
class ConversionOptions:
    """转换选项。"""
    format_code: str = "DOCX"
    save_mermaid_images: bool = False
    convert_mermaid_images: bool = False
    # 图片专属选项
    image_format: str = "png"
    image_quality: int = 100
    image_page_count: int = 1
    image_width: int = 1200
    image_dpi: int = 96
    image_background: str = "white"
    image_padding: int = 40


@dataclass
class _BatchState:
    """批量转换的运行时状态。"""
    overwrite_all: bool = False
    skip_all: bool = False
    last_output_file: str | None = None


# ── 文件锁定检测 ─────────────────────────────────────────────────────────────


def is_file_locked(filepath: str) -> bool:
    """检测文件是否被其他程序占用。"""
    if not os.path.exists(filepath):
        return False
    test_path = filepath + ".lock_test"
    try:
        os.rename(filepath, test_path)
        os.rename(test_path, filepath)
        return False
    except OSError:
        if os.path.exists(test_path):
            try:
                os.remove(test_path)
            except OSError:
                pass
        return True
    except Exception:
        return False


# ── Pandoc 路径设置 ──────────────────────────────────────────────────────────


def setup_pandoc_path(log_callback: Callable[[str], None] | None = None) -> None:
    """配置 Pandoc 路径（支持 PyInstaller 打包环境）。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    pandoc_exe_name = "pandoc.exe" if sys.platform == "win32" else "pandoc"
    pandoc_exe = Path(meipass) / "pypandoc" / "files" / pandoc_exe_name
    if pandoc_exe.exists():
        os.environ["PYPANDOC_PANDOC"] = str(pandoc_exe)
        try:
            import pypandoc
            pypandoc._pandoc_path = None
        except ImportError:
            pass
        if log_callback:
            log_callback(f"  使用内置 Pandoc: {pandoc_exe.name}")


# ── 文件读取 ─────────────────────────────────────────────────────────────────


def read_markdown_file(file_path: str) -> str:
    """读取 Markdown 文件内容。"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="gbk", errors="replace")
        except Exception as e:
            raise RuntimeError(f"无法读取文件（编码不支持）: {file_path}") from e
    except PermissionError as e:
        raise PermissionError(f"无权限读取文件: {file_path}") from e
    except OSError as e:
        raise RuntimeError(f"读取文件失败: {file_path}") from e


# ── 转换服务 ─────────────────────────────────────────────────────────────────


class ConversionService:
    """格式转换业务逻辑层，与 GUI 完全解耦。

    Args:
        strategy: 覆盖确认策略（由 GUI 层实现）。
        log_callback: 日志输出回调。
    """

    def __init__(
        self,
        strategy: OverwriteStrategy,
        log_callback: Callable[[str], None],
    ) -> None:
        self._strategy = strategy
        self._log = log_callback
        self._state = _BatchState()

    @property
    def last_output_file(self) -> str | None:
        return self._state.last_output_file

    def reset_batch_state(self) -> None:
        self._state = _BatchState()

    # ── 单文件转换 ────────────────────────────────────────────────────────

    def prepare_output_file(self, file_path: str, output_dir: str, format_code: str) -> Path:
        """准备输出文件路径。"""
        stem = Path(file_path).stem
        ext = OUTPUT_FORMATS[format_code][1]
        output_file = Path(output_dir) / f"{stem}{ext}"
        self._log(f"  → 准备保存到: {output_file.name}")
        return output_file

    def check_file_exists_and_overwrite(self, output_file: Path, *, is_batch: bool = False) -> bool:
        """检查文件是否存在，处理覆盖/重试/跳过逻辑。"""
        if not output_file.exists():
            return True
        if is_file_locked(str(output_file)):
            self._log(f"  ⚠ 文件被占用: {output_file.name}")
            if self._strategy.ask_file_locked(output_file.name):
                return True
            self._log(f"  ✗ 已跳过: {output_file.name}")
            return False
        if self._state.overwrite_all:
            return True
        if self._state.skip_all:
            self._log(f"  ✗ 已跳过: {output_file.name}")
            return False
        should_continue, new_overwrite_all, new_skip_all = self._strategy.ask_overwrite(
            output_file.name,
            is_batch=is_batch,
            overwrite_all=self._state.overwrite_all,
            skip_all=self._state.skip_all,
        )
        self._state.overwrite_all = new_overwrite_all
        self._state.skip_all = new_skip_all
        if not should_continue:
            self._log(f"  ✗ 已跳过: {output_file.name}")
            return False
        return True

    def execute_conversion(self, md_text: str, output_file: Path, options: ConversionOptions) -> None:
        """根据格式执行相应的转换。"""
        format_code = options.format_code
        try:
            if format_code == "DOCX":
                self._convert_to_docx(md_text, output_file, options)
            elif format_code == "PDF":
                from mdtrans.export_services.services import svc_md_to_pdf
                svc_md_to_pdf.convert_md_to_pdf(
                    md_text, output_file,
                    convert_mermaid=options.convert_mermaid_images,
                )
            elif format_code == "HTML":
                from mdtrans.export_services.services import svc_md_to_html
                svc_md_to_html.convert_md_to_html(md_text, output_file)
            elif format_code == "IMAGE":
                self._convert_to_image(md_text, output_file, options)
            else:
                raise ValueError(f"不支持的输出格式: {format_code}")
        except ImportError as e:
            raise RuntimeError(f"缺少必要模块: {e}\n请运行 uv sync 安装依赖") from e

    def _convert_to_docx(self, md_text: str, output_file: Path, options: ConversionOptions) -> None:
        """转换 Markdown 到 DOCX，支持 Mermaid 图片渲染。"""
        from mdtrans.export_services.services import svc_md_to_docx
        svc_md_to_docx.convert_md_to_docx(
            md_text=md_text,
            output_path=output_file,
            convert_mermaid=options.convert_mermaid_images,
            save_mermaid_images=options.save_mermaid_images,
            output_dir=output_file.parent,
        )

    def _convert_to_image(self, md_text: str, output_file: Path, options: ConversionOptions) -> None:
        """转换 Markdown 到图片，输出多页图片文件。

        ``output_file`` 仅用于推导目录和前缀名（扩展名被忽略）。
        实际输出文件为 ``{stem}_p001.png``、``{stem}_p002.png`` 等。
        """
        from mdtrans.export_services.services.svc_md_to_image import (
            ImageOptions,
            convert_md_to_image,
        )

        img_options = ImageOptions(
            image_format=options.image_format,
            quality=options.image_quality,
            page_count=options.image_page_count,
            image_width=options.image_width,
            dpi=options.image_dpi,
            background_color=options.image_background,
            padding=options.image_padding,
            convert_mermaid=options.convert_mermaid_images,
        )
        saved = convert_md_to_image(
            md_text=md_text,
            output_stem=output_file.stem,
            output_dir=str(output_file.parent),
            options=img_options,
            log_callback=self._log,
        )
        # 存储第一张图片路径供"打开文件"按钮使用
        if saved:
            self._state.last_output_file = str(saved[0])

    def convert_single_file(
        self, file_path: str, output_dir: str, options: ConversionOptions,
        *, max_retries: int = 3, is_batch: bool = False,
    ) -> str | None:
        """转换单个文件并写入输出目录。"""
        for retry_count in range(max_retries):
            try:
                setup_pandoc_path(self._log)
                md_text = read_markdown_file(file_path)
                output_file = self.prepare_output_file(file_path, output_dir, options.format_code)
                if not self.check_file_exists_and_overwrite(output_file, is_batch=is_batch):
                    return None
                self.execute_conversion(md_text, output_file, options)
                # IMAGE 格式在 _convert_to_image 内部已设置 last_output_file 为实际图片路径
                if options.format_code != "IMAGE":
                    self._state.last_output_file = str(output_file)
                return self._state.last_output_file or str(output_file)
            except (FileNotFoundError, PermissionError) as e:
                raise RuntimeError(str(e)) from e
            except Exception as e:
                if self._should_retry_on_error(str(e), retry_count, max_retries):
                    self._log("  ⚠ 写入失败，可能是文件被占用，正在重试...")
                else:
                    raise RuntimeError(f"转换文件 {Path(file_path).name} 失败: {e}") from e
        return None

    def process_batch(self, files: list[str], output_dir: str, options: ConversionOptions) -> list[str]:
        """批量转换文件。"""
        self.reset_batch_state()
        total = len(files)
        format_desc = OUTPUT_FORMATS[options.format_code][0]
        self._log(f"开始处理 {total} 个文件...")
        self._log(f"目标格式: {format_desc}")
        converted: list[str] = []
        for i, file_path in enumerate(files, 1):
            self._log(f"[{i}/{total}] 正在转换: {Path(file_path).name}")
            result = self.convert_single_file(file_path, output_dir, options, is_batch=True)
            if result is not None:
                stem = Path(file_path).stem
                ext = OUTPUT_FORMATS[options.format_code][1]
                self._log(f"✓ 转换成功: {stem}{ext}")
                converted.append(result)
        self._log(f"\n处理完成！共处理 {total} 个文件。")
        return converted

    @staticmethod
    def _should_retry_on_error(error_msg: str, retry_count: int, max_retries: int) -> bool:
        """判断是否应该根据错误重试。"""
        msg_lower = error_msg.lower()
        is_file_error = any(
            k in msg_lower for k in ("permission", "denied", "占用", "pandoc", "utf-8", "ioerror", "errno")
        )
        return is_file_error and retry_count < max_retries - 1

    def set_overwrite_all(self, value: bool) -> None:
        self._state.overwrite_all = value

    def set_skip_all(self, value: bool) -> None:
        self._state.skip_all = value
