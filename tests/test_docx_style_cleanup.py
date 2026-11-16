"""DOCX 样式清理回归测试。"""

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn

from mdtrans.export_services.services.svc_md_to_docx import _step1_delete_styles


def test_legacy_style_references_are_migrated_before_deletion():
    """正文和表格中的旧样式引用应先迁移，再删除样式定义。"""
    doc = Document()
    legacy_paragraph = doc.styles.add_style(
        "Legacy Paragraph", WD_STYLE_TYPE.PARAGRAPH
    )
    legacy_character = doc.styles.add_style(
        "Legacy Character", WD_STYLE_TYPE.CHARACTER
    )

    paragraph = doc.add_paragraph("正文")
    paragraph.style = legacy_paragraph
    paragraph.runs[0].style = legacy_character

    table_paragraph = doc.add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]
    table_paragraph.style = legacy_paragraph
    table_run = table_paragraph.add_run("表格")
    table_run.style = legacy_character

    _step1_delete_styles(doc)

    assert paragraph.style.name == "Normal"
    assert table_paragraph.style.name == "Normal"
    assert paragraph.runs[0]._element.find(qn("w:rPr")).find(qn("w:rStyle")) is None
    assert table_run._element.find(qn("w:rPr")).find(qn("w:rStyle")) is None
    assert "Legacy Paragraph" not in {style.name for style in doc.styles}
    assert "Legacy Character" not in {style.name for style in doc.styles}
