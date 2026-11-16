"""DOCX 标题分页排版回归测试。"""

from docx import Document

from mdtrans.export_services.services.svc_md_to_docx import convert_md_to_docx


def test_docx_heading_styles_allow_page_breaks(tmp_path):
    """DOCX 一级至六级标题不应强制与下段同页或整段保持同页。"""
    md_text = "\n\n".join(
        f"{'#' * level} 标题 {level}\n\n正文 {level}" for level in range(1, 7)
    )
    output_path = tmp_path / "heading_page_layout.docx"

    convert_md_to_docx(md_text, output_path, convert_mermaid=False)

    doc = Document(output_path)
    for level in range(1, 7):
        paragraph_format = doc.styles[f"Heading {level}"].paragraph_format
        assert paragraph_format.keep_with_next is False
        assert paragraph_format.keep_together is False
