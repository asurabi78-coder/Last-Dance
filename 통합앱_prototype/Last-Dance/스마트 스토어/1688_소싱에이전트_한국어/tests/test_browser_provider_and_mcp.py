from pathlib import Path

import pytest

from sourcing1688 import chrome_setup, mcp_server
from sourcing1688.mcp_server import mcp
from sourcing1688.providers.browser_provider import Browser1688Provider


@pytest.mark.anyio
async def test_browser_provider_verification_marker_detection():
    provider = Browser1688Provider()

    status, message = provider.detect_block_state_from_text("https://sec.taobao.com", "安全验证", "验证码")

    assert status == "blocked_by_verification"
    assert "verification" in message.lower()


def test_browser_search_dom_parser_fixture():
    html = (Path(__file__).parent / "fixtures" / "search_result_sample.html").read_text(encoding="utf-8")
    provider = Browser1688Provider()

    items = provider._parse_search_dom(html, "黑胶伞", 5)

    assert items[0].offer_id == "123456789"
    assert items[0].source_keyword == "黑胶伞"


def test_browser_search_dom_parser_handles_mobile_offer_links():
    html = """
    <html><body>
      <a href="http://detail.m.1688.com/page/index.html?offerId=812305105474&skuId=5505516668292">
        抖音款金属直播手机支架 10万+件 回头率55%
        <img src="//cbu01.alicdn.com/img/ibank/O1CN015ws3s41zgo2Mv28yO_!!2216935376744-0-cib.jpg">
      </a>
      <a href="https://s.1688.com/selloffer/similar_search.html?offerIds=812305105474">找相似</a>
    </body></html>
    """
    provider = Browser1688Provider()

    items = provider._parse_search_dom(html, "\u624b\u673a\u652f\u67b6", 5)

    assert len(items) == 1
    assert items[0].offer_id == "812305105474"
    assert items[0].image_url == "https://cbu01.alicdn.com/img/ibank/O1CN015ws3s41zgo2Mv28yO_!!2216935376744-0-cib.jpg"


def test_mcp_server_registers_expected_tools():
    tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}

    assert "parse_1688_rendered_html" in tool_names
    assert "parse_1688_rendered_html_content" in tool_names
    assert "parse_1688_visible_page_snapshot" in tool_names
    assert "parse_1688_network_payload_content" in tool_names
    assert "download_1688_product_assets_from_html_content" in tool_names
    assert "image_search_1688_products" in tool_names
    assert "check_1688_provider_capabilities" in tool_names
    assert "provider_check_1688" in tool_names
    assert "check_1688_browser_profile" in tool_names
    assert "open_1688_browser_profile" in tool_names
    assert "open_chrome_devtools_setup" in tool_names
    assert "start_chrome_devtools" in tool_names
    assert "check_chrome_devtools" in tool_names
    assert "parse_1688_review_snapshot" in tool_names
    assert "parse_1688_search_results_snapshot" in tool_names


def test_mcp_rendered_html_content_marks_chrome_capture():
    html = """
    <html><head><title>旅行收纳袋</title></head><body>
      <div>浙江华彩箱包有限公司</div>
      <div>¥41.00</div>
      <div>2件起批</div>
    </body></html>
    """

    payload = mcp_server.parse_1688_rendered_html_content(html, source_url="https://detail.1688.com/offer/755178864684.html")

    assert payload["provider"] == "chrome_devtools"
    assert payload["source_type"] == "browser"
    assert payload["live_verified"] is True
    assert payload["item"]["provider"] == "chrome_devtools"


def test_mcp_rendered_html_content_non_1688_page_message_is_clear():
    payload = mcp_server.parse_1688_rendered_html_content("<html><body>not a product page</body></html>", source_url="https://github.com/example")

    assert payload["provider"] == "chrome_devtools"
    assert payload["source_type"] == "browser"
    assert payload["live_verified"] is False
    assert "not a 1688 offer page" in payload["message"]
    assert payload["warnings"]


def test_open_chrome_devtools_setup_can_be_mocked(monkeypatch, tmp_path):
    calls = []

    class MockCompleted:
        returncode = 0
        stderr = ""

    def mock_run(args, **kwargs):
        calls.append(args)
        return MockCompleted()

    monkeypatch.setattr(mcp_server.subprocess, "run", mock_run)
    monkeypatch.setattr(chrome_setup.sys, "platform", "win32")
    monkeypatch.setenv("SOURCING1688_HOME", str(tmp_path))

    payload = mcp_server.open_chrome_devtools_setup()

    assert payload["status"] == "needs_user_action"
    assert payload["skipped"] is False
    assert payload["opened"] == []
    assert payload["requires_manual_navigation"] is True
    assert payload["url"] == "chrome://inspect/#remote-debugging"
    assert calls == []
    assert not (tmp_path / "config" / "chrome-devtools-setup.json").exists()


def test_open_chrome_devtools_setup_skips_after_verified_marker(monkeypatch, tmp_path):
    marker = chrome_setup.mark_chrome_devtools_endpoint_verified(
        tmp_path,
        endpoint="http://127.0.0.1:9222",
        command=["already-opened"],
        pages=[{"url": "https://www.1688.com/"}],
    )
    calls = []

    def mock_run(args, **kwargs):
        calls.append(args)
        raise AssertionError("setup command should not run when marker exists")

    monkeypatch.setenv("SOURCING1688_HOME", str(tmp_path))
    monkeypatch.setattr(mcp_server.subprocess, "run", mock_run)
    monkeypatch.setattr(mcp_server, "check_chrome_devtools_endpoint", lambda **kwargs: {"ok": False})

    payload = mcp_server.open_chrome_devtools_setup()

    assert payload["status"] == "ok"
    assert payload["skipped"] is True
    assert payload["opened"] == []
    assert payload["marker"]["path"] == marker["path"]
    assert calls == []


def test_windows_chrome_setup_command_preserves_window_state(monkeypatch):
    monkeypatch.setattr(chrome_setup.sys, "platform", "win32")
    monkeypatch.setattr(chrome_setup, "find_chrome_executable", lambda: "C:/Program Files/Google/Chrome/Application/chrome.exe")

    command = chrome_setup.chrome_devtools_setup_command()
    script = command[-1]

    assert "chrome://inspect/#remote-debugging" in script
    assert "--remote-debugging-port=$port" not in script
    assert "/json/new?$inspectUrl" not in script
    assert "WScript.Shell" not in script
    assert "SendKeys" not in script
    assert "--new-tab" not in script
    assert "ShowWindowAsync" not in script
    assert "SetForegroundWindow" not in script
    assert "about:blank" not in script
