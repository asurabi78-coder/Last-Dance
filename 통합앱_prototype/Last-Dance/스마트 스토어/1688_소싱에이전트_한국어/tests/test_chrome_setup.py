from pathlib import Path

from sourcing1688 import chrome_setup


def test_windows_chrome_setup_uses_chrome_exe_directly(monkeypatch, tmp_path):
    chrome = tmp_path / "chrome.exe"
    chrome.write_text("", encoding="utf-8")

    monkeypatch.setattr(chrome_setup.sys, "platform", "win32")
    monkeypatch.setattr(chrome_setup.shutil, "which", lambda name: str(chrome) if name == "chrome.exe" else None)

    command = chrome_setup.chrome_devtools_setup_command()

    assert command[:4] == ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass"]
    assert str(chrome) in command[-1]
    assert "chrome://inspect/#remote-debugging" in command[-1]
    assert "--remote-debugging-port=$port" not in command[-1]
    assert "chrome-devtools-profile" not in command[-1]
    assert "/json/version" not in command[-1]
    assert "/json/new?$inspectUrl" not in command[-1]
    assert "WScript.Shell" not in command[-1]
    assert "SendKeys" not in command[-1]
    assert "--new-tab" not in command[-1]
    assert "UIAutomationClient" not in command[-1]
    assert "ValuePattern" not in command[-1]
    assert "about:blank" not in command[-1]
    assert "keybd_event" not in command[-1]
    assert "cmd" not in command


def test_windows_chrome_setup_falls_back_without_cmd_start(monkeypatch):
    monkeypatch.setattr(chrome_setup.sys, "platform", "win32")
    monkeypatch.setattr(chrome_setup.shutil, "which", lambda name: None)
    monkeypatch.setattr(Path, "exists", lambda self: False)

    command = chrome_setup.chrome_devtools_setup_command()

    assert command[:4] == ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass"]
    assert "chrome.exe" in command[-1]
    assert "chrome://inspect/#remote-debugging" in command[-1]
    assert "chrome-devtools-profile" not in command[-1]
    assert "SendKeys" not in command[-1]
    assert "cmd" not in command


def test_windows_setup_reports_manual_navigation(monkeypatch):
    monkeypatch.setattr(chrome_setup.sys, "platform", "win32")

    payload = chrome_setup.chrome_devtools_setup_manual_action()

    assert payload["status"] == "needs_user_action"
    assert payload["opened"] == []
    assert payload["requires_manual_navigation"] is True
    assert payload["url"] == chrome_setup.CHROME_DEVTOOLS_SETUP_URL


def test_chrome_devtools_port_command_uses_dedicated_profile(monkeypatch, tmp_path):
    chrome = tmp_path / "chrome.exe"
    chrome.write_text("", encoding="utf-8")

    monkeypatch.setattr(chrome_setup.shutil, "which", lambda name: str(chrome) if name == "chrome.exe" else None)

    command = chrome_setup.chrome_devtools_port_command(
        port=9222,
        user_data_dir=tmp_path / "profile",
        url="https://www.1688.com/",
    )

    assert command[0] == str(chrome)
    assert "--remote-debugging-port=9222" in command
    assert f"--user-data-dir={tmp_path / 'profile'}" in command
    assert "--no-first-run" in command
    assert "--new-window" in command
    assert "https://www.1688.com/" in command


def test_start_chrome_devtools_port_verifies_endpoint_before_marker(monkeypatch, tmp_path):
    chrome = tmp_path / "chrome.exe"
    chrome.write_text("", encoding="utf-8")
    calls = {"checks": 0, "popen": []}

    class FakeProcess:
        pid = 1234

    def fake_check(endpoint="http://127.0.0.1:9222", timeout=2.0):
        calls["checks"] += 1
        return {"ok": calls["checks"] >= 2, "endpoint": endpoint, "browser": "Chrome"}

    def fake_popen(command, **kwargs):
        calls["popen"].append(command)
        return FakeProcess()

    monkeypatch.setenv("SOURCING1688_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(chrome_setup.shutil, "which", lambda name: str(chrome) if name == "chrome.exe" else None)
    monkeypatch.setattr(chrome_setup.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(chrome_setup, "check_chrome_devtools_endpoint", fake_check)
    monkeypatch.setattr(chrome_setup, "list_chrome_devtools_pages", lambda *args, **kwargs: {"ok": True, "pages": [{"url": "https://www.1688.com/"}]})
    monkeypatch.setattr(chrome_setup.time, "sleep", lambda seconds: None)

    payload = chrome_setup.start_chrome_devtools_port(wait_seconds=2)

    assert payload["status"] == "ok"
    assert payload["endpoint_verified"] is True
    assert calls["popen"]
    marker = chrome_setup.read_chrome_setup_marker(tmp_path / "home")
    assert marker["status"] == "verified"
    assert marker["endpoint"] == "http://127.0.0.1:9222"


def test_setup_marker_verified_helper_rejects_opened_only_marker(tmp_path):
    marker = chrome_setup.mark_chrome_setup_opened(tmp_path, command=["opened-only"])

    assert chrome_setup.is_chrome_setup_marker_verified(marker) is False

    verified = chrome_setup.mark_chrome_devtools_endpoint_verified(
        tmp_path,
        endpoint="http://127.0.0.1:9222",
        command=["chrome"],
        pages=[{"url": "https://www.1688.com/"}],
    )

    assert chrome_setup.is_chrome_setup_marker_verified(verified) is True


def test_macos_chrome_setup_uses_open_app(monkeypatch):
    monkeypatch.setattr(chrome_setup.sys, "platform", "darwin")

    command = chrome_setup.chrome_devtools_setup_command()

    assert command == ["open", "-a", "Google Chrome", chrome_setup.CHROME_DEVTOOLS_SETUP_URL]


def test_linux_chrome_setup_uses_chrome_command(monkeypatch):
    monkeypatch.setattr(chrome_setup.sys, "platform", "linux")
    monkeypatch.setattr(chrome_setup.shutil, "which", lambda name: None)

    command = chrome_setup.chrome_devtools_setup_command()

    assert command == ["google-chrome", "--new-tab", chrome_setup.CHROME_DEVTOOLS_SETUP_URL]
