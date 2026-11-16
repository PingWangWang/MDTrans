"""配置持久化回归测试。"""

from copy import deepcopy

from mdtrans.app.navigator import Navigator
from mdtrans.gui import _config as config_module


class _Page:
    """记录页面停用调用次数。"""

    def __init__(self) -> None:
        self.deactivated = 0

    def on_deactivate(self) -> None:
        """模拟页面将状态同步到配置对象。"""
        self.deactivated += 1


def test_navigator_save_state_deactivates_both_pages():
    """窗口关闭前应主动同步导入页和导出页状态。"""
    navigator = object.__new__(Navigator)
    navigator._config = {"active_tab": "import"}
    navigator._current_tab = Navigator.TAB_EXPORT
    navigator._import_page = _Page()
    navigator._export_page = _Page()

    navigator.save_state()

    assert navigator._import_page.deactivated == 1
    assert navigator._export_page.deactivated == 1
    assert navigator._config["active_tab"] == "export"


def test_ui_config_round_trip(monkeypatch, tmp_path):
    """界面设置应可写入并重新加载。"""
    config_file = tmp_path / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    config = deepcopy(config_module.DEFAULT_CONFIG)
    config["active_tab"] = "export"
    config["import"]["image_mode"] = "embed"
    config["export"]["last_format"] = "pdf"
    config["export"]["convert_mermaid_images"] = False
    config["export"]["save_mermaid_images"] = True
    config["export"]["image"].update(
        {"format": "webp", "page_count": 3, "dpi": 192, "background": "transparent"}
    )
    config["export"]["docx"] = {"footer": {"enabled": True}}
    config_module.save_config(config)
    loaded = config_module.load_config()

    assert loaded["active_tab"] == "export"
    assert loaded["import"]["image_mode"] == "embed"
    assert loaded["export"]["last_format"] == "pdf"
    assert loaded["export"]["convert_mermaid_images"] is False
    assert loaded["export"]["save_mermaid_images"] is True
    assert loaded["export"]["image"] == {
        "format": "webp",
        "page_count": 3,
        "dpi": 192,
        "background": "transparent",
    }
    assert "docx" not in loaded["export"]
