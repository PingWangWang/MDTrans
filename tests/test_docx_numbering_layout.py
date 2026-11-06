"""DOCX 编号列表排版回归测试。"""

from docx import Document
from docx.oxml.ns import qn

from mdtrans.export_services.services.svc_md_to_docx import convert_md_to_docx


def _get_numbering_levels(doc):
    """读取文档中的全部编号级别定义。"""
    return list(doc.part.numbering_part.element.iter(qn("w:lvl")))


def test_numbered_list_suffix_uses_space_and_bullets_are_unchanged(tmp_path):
    """数字编号后使用空格，项目符号的编号后缀保持不变。"""
    numbered_lines = [
        f"{index}. 第 {index} 条技术要求。" for index in range(1, 11)
    ]
    md_text = "\n".join(numbered_lines) + "\n\n- 项目符号内容。\n"
    output_path = tmp_path / "numbered_list.docx"

    convert_md_to_docx(md_text, output_path, convert_mermaid=False)

    doc = Document(output_path)
    numbered_levels = 0
    bullet_levels = 0
    for level in _get_numbering_levels(doc):
        num_format = level.find(qn("w:numFmt"))
        if num_format is None:
            continue
        format_value = num_format.get(qn("w:val"))
        suffix = level.find(qn("w:suff"))
        suffix_value = suffix.get(qn("w:val")) if suffix is not None else None

        if format_value == "bullet":
            bullet_levels += 1
            assert suffix_value != "space"
        elif format_value not in {None, "none"}:
            numbered_levels += 1
            assert suffix_value == "space"

    assert numbered_levels > 0
    assert bullet_levels > 0
    assert "第 10 条技术要求。" in "\n".join(p.text for p in doc.paragraphs)
