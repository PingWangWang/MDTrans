"""
Markdown to HTML conversion service
Provides common functionality for converting Markdown to HTML format
"""

from pathlib import Path

from ..utils import get_logger
from ..utils.markdown_utils import get_md_text
from ..styles.css_adapter import generate_full_stylesheet

logger = get_logger(__name__)


def convert_md_to_html(md_text: str, output_path: Path, is_strip_wrapper: bool = False) -> None:
    """
    Convert Markdown text to HTML format with full CSS styling.

    The generated HTML includes a complete stylesheet that matches
    DOCX output styling (fonts, sizes, spacing, etc.).

    Args:
        md_text: Markdown text to convert
        output_path: Path to save the output HTML file
        is_strip_wrapper: Whether to remove code block wrapper if present

    Raises:
        ValueError: If input processing fails
        Exception: If conversion fails
    """
    from pypandoc import convert_text  # noqa: PLC0415

    # Process Markdown text
    processed_md = get_md_text(md_text, is_strip_wrapper=is_strip_wrapper)

    logger.info(f"Converting Markdown to HTML: {output_path}")

    # Convert to HTML
    html_body = convert_text(processed_md, format="markdown", to="html")

    # Wrap in full HTML page with DOCX-matching styles
    full_css = generate_full_stylesheet()
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
{full_css}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

    # Write to file
    output_path.write_bytes(full_html.encode("utf-8"))
    logger.info(f"Successfully created HTML: {output_path}")
