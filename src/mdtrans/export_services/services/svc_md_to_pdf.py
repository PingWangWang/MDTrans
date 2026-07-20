#!/usr/bin/env python3
"""
Markdown to PDF conversion service
Provides common functionality for converting Markdown to PDF format
"""

import shutil
import tempfile
from pathlib import Path

from ..utils import get_logger
from ..utils.markdown_utils import convert_markdown_to_html, get_md_text
from ..utils.text_utils import contains_chinese, contains_japanese

logger = get_logger(__name__)


def convert_to_html_with_font_support(md_text: str) -> str:
    """
    Convert Markdown to HTML and add Chinese/Japanese font support

    Args:
        md_text: Markdown text to convert

    Returns:
        str: HTML string with appropriate font support
    """
    html_str = convert_markdown_to_html(md_text)

    if not contains_chinese(md_text) and not contains_japanese(md_text):
        return html_str

    # Add Chinese/Japanese font CSS
    font_families = ",".join(
        [
            "Sans-serif",
            "STSong-Light",
            "MSung-Light",
            "HeiseiMin-W3",
        ]
    )
    css_style = f"""
    <style>
        html {{
            font-family: "{font_families}";
        }}
    </style>
    """

    result = f"""
    {css_style}
    {html_str}
    """
    return result


def convert_md_to_pdf(
    md_text: str,
    output_path: Path,
    is_strip_wrapper: bool = False,
    convert_mermaid: bool = False,
) -> None:
    """
    Convert Markdown text to PDF format

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

        # Convert to HTML with font support
        html_str = convert_to_html_with_font_support(processed_md)

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
