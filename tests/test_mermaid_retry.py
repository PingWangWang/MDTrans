"""Mermaid 在线渲染重试策略回归测试。"""

import logging

import pytest
import requests

from mdtrans.export_services.utils import mermaid_utils


class _Response:
    """提供重试测试所需的最小 HTTP 响应接口。"""

    def __init__(self, status_code: int, content: bytes = b"") -> None:
        self.status_code = status_code
        self.content = content
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        """在状态码表示失败时抛出与 requests 一致的 HTTPError。"""
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Server Error", response=self
            )


def test_transient_server_error_is_retried(tmp_path, monkeypatch):
    """HTTP 503 后应等待并重试，最终成功返回图片路径。"""
    responses = iter([_Response(503), _Response(200, b"image-bytes")])
    get_calls: list[str] = []
    sleep_calls: list[float] = []

    def fake_get(url, timeout):
        get_calls.append(url)
        assert timeout == 15
        return next(responses)

    monkeypatch.setattr(mermaid_utils.requests, "get", fake_get)
    monkeypatch.setattr(mermaid_utils.time, "sleep", sleep_calls.append)

    output_path = tmp_path / "retry.png"
    result = mermaid_utils.convert_mermaid_to_image(
        "flowchart LR\nA --> B",
        output_path,
        timeout=15,
        max_retries=2,
        retry_delay=2,
    )

    assert result == output_path
    assert output_path.read_bytes() == b"image-bytes"
    assert len(get_calls) == 2
    assert sleep_calls == [2.0]


def test_non_retryable_client_error_stops_immediately(tmp_path, monkeypatch):
    """HTTP 4xx（429 除外）通常表示请求无效，不应重复请求。"""
    get_calls = 0

    def fake_get(url, timeout):
        nonlocal get_calls
        get_calls += 1
        return _Response(400)

    monkeypatch.setattr(mermaid_utils.requests, "get", fake_get)
    monkeypatch.setattr(
        mermaid_utils.time,
        "sleep",
        lambda _seconds: pytest.fail("HTTP 400 不应进入重试等待"),
    )

    result = mermaid_utils.convert_mermaid_to_image(
        "flowchart LR\nA --> B",
        tmp_path / "bad-request.png",
        max_retries=3,
    )

    assert result is None
    assert get_calls == 1


def test_failure_log_reports_actual_attempt_count(tmp_path, monkeypatch, caplog):
    """连续 5xx 失败时，日志应报告实际尝试次数而非配置上限。"""
    monkeypatch.setattr(
        mermaid_utils.requests,
        "get",
        lambda url, timeout: _Response(503),
    )
    monkeypatch.setattr(mermaid_utils.time, "sleep", lambda _seconds: None)
    caplog.set_level(logging.ERROR)

    result = mermaid_utils.convert_mermaid_to_image(
        "flowchart LR\nA --> B",
        tmp_path / "unavailable.png",
        max_retries=2,
        retry_delay=0,
    )

    assert result is None
    assert "已尝试 2 次" in caplog.text
