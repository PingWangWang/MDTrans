"""代码块打印排版回归测试。"""

from docx import Document
from docx.oxml.ns import qn

from mdtrans.export_services.services.svc_md_to_docx import convert_md_to_docx
from mdtrans.export_services.styles.css_adapter import (
    style_def_to_css,
    style_def_to_xhtml2pdf_css,
)
from mdtrans.export_services.styles.definitions import CODE_BLOCK


def _get_code_block_paragraph(doc):
    """返回文档中的代码块段落。"""
    return next(
        paragraph
        for paragraph in doc.paragraphs
        if paragraph.style.name == "Code Block"
    )


def test_docx_code_block_uses_black_text_without_background(tmp_path):
    """DOCX 代码块应使用黑字且不设置深色段落底纹。"""
    md_text = '正文。\n\n```python\nprint("printable")\n```\n'
    output_path = tmp_path / "code_block.docx"

    convert_md_to_docx(md_text, output_path, convert_mermaid=False)

    doc = Document(output_path)
    code_paragraph = _get_code_block_paragraph(doc)
    code_style = doc.styles["Code Block"]
    shading = code_style.element.get_or_add_pPr().find(qn("w:shd"))

    assert CODE_BLOCK.color_hex == "#000000"
    assert CODE_BLOCK.background_color_hex is None
    assert shading is None or shading.get(qn("w:fill")) in {None, "auto", "FFFFFF"}
    assert code_paragraph.runs
    assert all(str(run.font.color.rgb) == "000000" for run in code_paragraph.runs)


def test_shared_css_code_block_uses_black_text_without_background():
    """共享 CSS 不应再给代码块设置深色背景。"""
    for css in (
        style_def_to_css(CODE_BLOCK),
        style_def_to_xhtml2pdf_css(CODE_BLOCK),
    ):
        assert "color: #000000;" in css
        assert "background-color:" not in css
