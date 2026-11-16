"""覆盖确认策略回归测试。"""

from pathlib import Path

from mdtrans.export_ui import app as export_app
from mdtrans.export_ui.app import ExportPage
from mdtrans.export_ui.conversion import ConversionOptions, ConversionService


class _Strategy:
    """提供覆盖策略协议所需的空实现。"""

    def ask_overwrite(self, filename, *, is_batch, overwrite_all, skip_all):
        return True, overwrite_all, skip_all

    def ask_file_locked(self, filename):
        return True


def test_process_batch_uses_single_file_mode_for_one_file(monkeypatch, tmp_path):
    """仅选择一个文件时不应启用批量覆盖选项。"""
    service = ConversionService(strategy=_Strategy(), log_callback=lambda _message: None)
    received_modes: list[bool] = []

    def fake_convert_single_file(file_path, output_dir, options, *, is_batch=False):
        received_modes.append(is_batch)
        return str(tmp_path / "result.docx")

    monkeypatch.setattr(service, "convert_single_file", fake_convert_single_file)

    result = service.process_batch(
        [str(tmp_path / "single.md")],
        str(tmp_path),
        ConversionOptions(),
    )

    assert received_modes == [False]
    assert result == [str(tmp_path / "result.docx")]


def test_process_batch_reports_mermaid_degradation(monkeypatch, tmp_path):
    """Mermaid 部分失败时应显示内容降级，而不是完整成功。"""
    source_file = tmp_path / "source.md"
    source_file.write_text("# 测试", encoding="utf-8")
    logs: list[str] = []
    service = ConversionService(strategy=_Strategy(), log_callback=logs.append)

    monkeypatch.setattr(
        service,
        "execute_conversion",
        lambda *_args: {"total": 2, "success": 1, "failed": 1},
    )

    result = service.process_batch(
        [str(source_file)],
        str(tmp_path),
        ConversionOptions(),
    )

    assert result == [str(tmp_path / "source.docx")]
    assert any("部分降级" in message for message in logs)
    assert any("1 个存在内容降级" in message for message in logs)


def test_export_page_uses_single_dialog_for_one_file(monkeypatch):
    """导出页单文件模式应调用双按钮覆盖对话框。"""
    page = object.__new__(ExportPage)
    monkeypatch.setattr(ExportPage, "_get_dialog_theme", lambda _self: object())

    calls: list[str] = []
    monkeypatch.setattr(
        export_app,
        "ask_overwrite_single",
        lambda _theme, filename: calls.append(filename) or True,
    )
    monkeypatch.setattr(
        export_app,
        "ask_overwrite_batch",
        lambda *_args: (_ for _ in ()).throw(AssertionError("不应调用批量对话框")),
    )

    result = ExportPage.ask_overwrite(
        page,
        "single.md",
        is_batch=False,
        overwrite_all=False,
        skip_all=False,
    )

    assert result == (True, False, False)
    assert calls == ["single.md"]
