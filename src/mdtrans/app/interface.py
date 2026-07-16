"""MDTrans - 应用层接口定义。

定义 Page 接口和 NavigationController，供导入/导出页面实现。
"""

from __future__ import annotations

from typing import Any, Protocol


class IPage(Protocol):
    """页面接口，所有模式页面必须实现。"""

    def on_activate(self) -> None:
        """页面被激活时调用（切换到当前 Tab）。"""
        ...

    def on_deactivate(self) -> None:
        """页面被停用时调用（切换到其他 Tab）。"""
        ...

    def log_message(self, message: str, tag: str = "info") -> None:
        """向日志区域追加消息。

        Args:
            message: 日志文本。
            tag: 标签（``"info"``、``"success"``、``"warning"``、``"error"``）。
        """
        ...

    def destroy(self) -> None:
        """销毁页面释放资源。"""
        ...
