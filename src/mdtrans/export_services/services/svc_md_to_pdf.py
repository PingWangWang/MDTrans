#!/usr/bin/env python3
"""
Markdown to PDF conversion service
Provides common functionality for converting Markdown to PDF format
"""

import os
import shutil
import tempfile
from pathlib import Path

from ..utils import get_logger
from ..utils.markdown_utils import get_md_text
from ..styles.css_adapter import generate_xhtml2pdf_stylesheet

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# CJK 字体初始化（注册到 ReportLab + xhtml2pdf）
# ---------------------------------------------------------------------------

_FONT_INIT_DONE: bool = False


def _ensure_cjk_font() -> None:
    """注册系统中文字体到 ReportLab 并添加到 xhtml2pdf 字体映射表。

    只需执行一次。在 ``C:\\Windows\\Fonts`` 中查找可用的中文字体，
    将所有候选字体名都注册到 ``xhtml2pdf.default.DEFAULT_FONT``，
    确保 CSS font-family 中的任何中文字体名都能被 xhtml2pdf 识别。
    """
    global _FONT_INIT_DONE
    if _FONT_INIT_DONE:
        return

    from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415
    from reportlab.pdfbase.ttfonts import TTFont  # noqa: PLC0415
    import xhtml2pdf.default  # noqa: PLC0415

    font_dir = r"C:\Windows\Fonts"
    candidates = [
        ("SimSun", "simsun.ttc", True),
        ("Microsoft YaHei", "msyh.ttc", True),
        ("SimHei", "simhei.ttf", False),
        ("FangSong", "simfang.ttf", False),
    ]

    for font_name, filename, is_ttc in candidates:
        font_path = os.path.join(font_dir, filename)
        if not os.path.exists(font_path):
            continue
        try:
            kwargs = {"subfontIndex": 0} if is_ttc else {}
            register_name = "SimSun"
            pdfmetrics.registerFont(TTFont(register_name, font_path, **kwargs))
            # 将所有候选字体名都注册到 xhtml2pdf 映射表
            all_aliases = [
                register_name,
                register_name.lower(),
                font_name,
                font_name.lower(),
            ]
            for alias in all_aliases:
                xhtml2pdf.default.DEFAULT_FONT[alias] = register_name
            _FONT_INIT_DONE = True
            logger.info(f"已注册中文字体: {register_name} -> {filename}")
            return
        except Exception as exc:
            logger.warning(f"注册字体 {font_name} 失败: {exc}")
            continue

    logger.warning("未找到可用的中文字体，PDF 中的中文可能显示为方块")


# ---------------------------------------------------------------------------
# 转换逻辑
# ---------------------------------------------------------------------------


def convert_to_html_with_styles(md_text: str) -> str:
    """
    Convert Markdown to HTML (via Pandoc) and inject xhtml2pdf-compatible
    CSS stylesheet that matches DOCX output styling.

    Uses Pandoc for MD→HTML to keep HTML structure consistent with
    the DOCX and HTML export services, ensuring CSS selectors match.

    Also ensures CJK fonts are registered so xhtml2pdf can render
    Chinese characters correctly.

    Args:
        md_text: Markdown text to convert

    Returns:
        str: HTML string with full style support for PDF generation
    """
    from pypandoc import convert_text  # noqa: PLC0415

    _ensure_cjk_font()
    html_str = convert_text(md_text, format="markdown", to="html")
    full_css = generate_xhtml2pdf_stylesheet()

    result = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
{full_css}
</style>
</head>
<body>
{html_str}
</body>
</html>
"""
    return result


def convert_md_to_pdf(
    md_text: str,
    output_path: Path,
    is_strip_wrapper: bool = False,
    convert_mermaid: bool = False,
) -> None:
    """
    Convert Markdown text to PDF format.

    .. note::
        PDF 中文渲染依赖系统 CJK 字体。首次转换时会自动注册
        ``simsun.ttc``（宋体）或 ``msyh.ttc``（微软雅黑）等字体。

    Args:
        md_text: Markdown text to convert
        output_path: Path to save the output PDF file
        is_strip_wrapper: Whether to remove code block wrapper if present
        convert_mermaid: Whether to convert Mermaid code blocks to images

    Raises:
        ValueError: If input processing fails
        Exception: If conversion fails
    """
    from xhtml2pdf import pisa  # noqa: PLC0415
    from ..utils.mermaid_utils import (  # noqa: PLC0415
        replace_mermaid_with_images,
        cleanup_temp_images,
    )

    # Process Markdown text
    processed_md = get_md_text(md_text, is_strip_wrapper=is_strip_wrapper)

    # Mermaid 图表渲染：将代码块替换为图片引用，供后续 HTML/PDF 嵌入
    temp_images: list[Path] = []
    temp_dir: Path | None = None

    try:
        if convert_mermaid:
            temp_dir = Path(tempfile.mkdtemp(prefix="mdtrans_mermaid_"))
            modified_md, temp_images, mermaid_stats, _ = replace_mermaid_with_images(
                processed_md,
                temp_dir,
                image_format="png",
                scale=3,
            )
            if mermaid_stats and mermaid_stats["total"] > 0:
                logger.info(
                    f"Mermaid 渲染完成: {mermaid_stats['success']}/"
                    f"{mermaid_stats['total']} 个成功"
                )
                processed_md = modified_md

        # Convert to HTML with full styles
        html_str = convert_to_html_with_styles(processed_md)

        logger.info(f"Converting Markdown to PDF: {output_path}")

        # Convert to PDF
        # path=temp_dir 使 xhtml2pdf 能解析 <img src="filename.png"> 相对路径
        result_file_bytes = pisa.CreatePDF(
            src=html_str,
            dest_bytes=True,
            encoding="utf-8",
            path=str(temp_dir) if temp_dir else None,
            capacity=400 * 1024 * 1024,
        )

        # Write to file
        output_path.write_bytes(result_file_bytes)
        logger.info(f"Successfully created PDF: {output_path}")

    finally:
        # 清理临时图片文件
        if temp_images:
            cleanup_temp_images(temp_images)
        # 清理临时目录
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
