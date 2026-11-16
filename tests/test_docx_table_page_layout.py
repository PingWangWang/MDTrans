"""DOCX 表格分页排版回归测试。"""

from docx import Document
from docx.oxml.ns import qn

from mdtrans.export_services.services.svc_md_to_docx import convert_md_to_docx


def test_docx_table_rows_do_not_split_and_headers_do_not_repeat(tmp_path):
    """DOCX 表格行不应跨页拆分，跨页时也不应重复表头。"""
    md_text = """| 序号 | 名称 | 说明 |
|---|---|---|
| 1 | 项目一 | 内容一 |
| 2 | 项目二 | 内容二 |
"""
    output_path = tmp_path / "table_page_layout.docx"

    convert_md_to_docx(md_text, output_path, convert_mermaid=False)

    table = Document(output_path).tables[0]
    for row in table.rows:
        trPr = row._tr.trPr
        assert trPr is not None

        cant_split = trPr.find(qn("w:cantSplit"))
        assert cant_split is not None
        assert cant_split.get(qn("w:val")) == "true"
        assert trPr.find(qn("w:tblHeader")) is None
