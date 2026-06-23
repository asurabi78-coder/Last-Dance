import json
from pathlib import Path

from typer.testing import CliRunner

from sourcing1688 import codex_install
from sourcing1688.cli import app


runner = CliRunner()


class Completed:
    def __init__(self, returncode=0, stdout="ok", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def sample_mcp_config() -> dict:
    return {
        "mcpServers": {
            "sourcing1688": {
                "command": "uvx",
                "args": ["--refresh", "--from", codex_install.REPO_URL, "sourcing1688-mcp"],
            },
            "chrome-devtools": {
                "command": "npx",
                "args": ["-y", "chrome-devtools-mcp@latest", "--autoConnect", "--redact-network-headers"],
                "startup_timeout_sec": 60,
                "tool_timeout_sec": 300,
            },
        }
    }


def write_marketplace_bundle(home: Path) -> None:
    plugin_dir = home / ".tmp" / "marketplaces" / codex_install.MARKETPLACE_NAME / "plugins" / codex_install.PLUGIN_NAME
    manifest_dir = plugin_dir / ".codex-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(json.dumps({"version": "0.5.16"}), encoding="utf-8")
    (plugin_dir / ".mcp.json").write_text(json.dumps(sample_mcp_config()), encoding="utf-8")
    (plugin_dir / "README.md").write_text("# Plugin", encoding="utf-8")


def test_enable_and_disable_plugin_config(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("[features]\nhooks = true\n", encoding="utf-8")

    enabled = codex_install.enable_plugin_in_config(config)

    assert enabled["enabled"] is True
    assert f'[plugins."{codex_install.PLUGIN_CONFIG_ID}"]' in config.read_text(encoding="utf-8")
    assert "enabled = true" in config.read_text(encoding="utf-8")

    removed = codex_install.disable_plugin_in_config(config)

    assert removed["removed"] is True
    assert codex_install.PLUGIN_CONFIG_ID not in config.read_text(encoding="utf-8")


def test_install_codex_registers_marketplace_plugin_and_removes_global_mcp(monkeypatch, tmp_path):
    write_marketplace_bundle(tmp_path)
    commands = []

    def fake_which(name):
        return f"C:/bin/{name}.exe"

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[:3] == ["codex", "mcp", "remove"]:
            return Completed(returncode=1, stderr="not found")
        return Completed()

    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(codex_install.shutil, "which", fake_which)
    monkeypatch.setattr(codex_install.subprocess, "run", fake_run)

    payload = codex_install.install_codex(open_chrome_setup=False)

    assert payload["status"] == "ok"
    assert payload["chrome_mode"] == "auto"
    assert ["codex", "plugin", "marketplace", "add", codex_install.REPO_URL] in commands
    assert ["codex", "mcp", "remove", "sourcing1688"] in commands
    assert ["codex", "mcp", "remove", "chrome-devtools"] in commands
    assert not any(command[:3] == ["codex", "mcp", "add"] for command in commands)
    assert codex_install.PLUGIN_CONFIG_ID in (tmp_path / "config.toml").read_text(encoding="utf-8")
    assert (tmp_path / "plugins" / "cache" / codex_install.MARKETPLACE_NAME / codex_install.PLUGIN_NAME / "0.5.16").exists()


def test_run_reports_windows_access_denied_with_stage(monkeypatch):
    def fake_run(command, **kwargs):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(codex_install.subprocess, "run", fake_run)

    payload = codex_install._run(["codex", "mcp", "list"], stage="mcp_list")

    assert payload["ok"] is False
    assert payload["returncode"] == 126
    assert payload["stage"] == "mcp_list"
    assert payload["error_code"] == "windows_access_denied"
    assert "WindowsApps" in payload["next_step"]


def test_manual_windows_install_copies_local_bundle_and_rewrites_port_mcp(monkeypatch, tmp_path):
    source = tmp_path / "local-plugin"
    manifest_dir = source / ".codex-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(json.dumps({"version": "0.5.17"}), encoding="utf-8")
    (source / ".mcp.json").write_text(json.dumps(sample_mcp_config()), encoding="utf-8")
    (source / "README.md").write_text("# Plugin", encoding="utf-8")

    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setattr(codex_install.shutil, "which", lambda name: f"C:/bin/{name}")
    monkeypatch.setattr(codex_install.sys, "platform", "win32")
    monkeypatch.setattr(codex_install, "_local_plugin_bundle_source", lambda: source)
    monkeypatch.setattr(codex_install, "start_chrome_devtools_port", lambda **kwargs: {"status": "ok", "endpoint": f"http://127.0.0.1:{kwargs['port']}"})

    payload = codex_install.install_codex(manual_windows_install=True, chrome_mode="port")

    assert payload["status"] == "ok"
    assert payload["steps"]["plugin_cache"]["source"] == str(source)
    assert payload["chrome_mode"] == "port"
    copied_mcp = json.loads(
        (
            tmp_path
            / "codex"
            / "plugins"
            / "cache"
            / codex_install.MARKETPLACE_NAME
            / codex_install.PLUGIN_NAME
            / "0.5.17"
            / ".mcp.json"
        ).read_text(encoding="utf-8")
    )
    chrome = copied_mcp["mcpServers"]["chrome-devtools"]
    assert chrome["command"] == "npx.cmd"
    assert "--auto-connect" not in chrome["args"]
    assert "--browserUrl" in chrome["args"]
    assert "http://127.0.0.1:9222" in chrome["args"]


def test_windows_default_install_keeps_existing_chrome_session_mode(monkeypatch, tmp_path):
    source = tmp_path / "local-plugin"
    manifest_dir = source / ".codex-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(json.dumps({"version": "0.5.19"}), encoding="utf-8")
    (source / ".mcp.json").write_text(json.dumps(sample_mcp_config()), encoding="utf-8")

    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setattr(codex_install.shutil, "which", lambda name: f"C:/bin/{name}")
    monkeypatch.setattr(codex_install.sys, "platform", "win32")
    monkeypatch.setattr(codex_install, "_local_plugin_bundle_source", lambda: source)

    payload = codex_install.install_codex(manual_windows_install=True, open_chrome_setup=False)

    copied_mcp = json.loads(
        (
            tmp_path
            / "codex"
            / "plugins"
            / "cache"
            / codex_install.MARKETPLACE_NAME
            / codex_install.PLUGIN_NAME
            / "0.5.19"
            / ".mcp.json"
        ).read_text(encoding="utf-8")
    )
    chrome = copied_mcp["mcpServers"]["chrome-devtools"]
    assert payload["chrome_mode"] == "auto"
    assert chrome["command"] == "npx.cmd"
    assert "--autoConnect" in chrome["args"]
    assert "--browserUrl" not in chrome["args"]


def test_plugin_cache_copy_removes_other_cached_versions(tmp_path):
    source = tmp_path / "local-plugin"
    manifest_dir = source / ".codex-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(json.dumps({"version": "0.5.20"}), encoding="utf-8")
    (source / ".mcp.json").write_text(json.dumps(sample_mcp_config()), encoding="utf-8")

    cache_root = tmp_path / "plugins" / "cache" / codex_install.MARKETPLACE_NAME / codex_install.PLUGIN_NAME
    (cache_root / "0.5.18").mkdir(parents=True)
    (cache_root / "0.5.19").mkdir(parents=True)

    payload = codex_install._copy_plugin_bundle_to_cache(tmp_path, source, chrome_mode="auto")

    versions = [path.name for path in cache_root.iterdir() if path.is_dir()]
    assert payload["status"] == "ok"
    assert payload["removed_versions"] == ["0.5.18", "0.5.19"]
    assert versions == ["0.5.20"]


def test_install_codex_falls_back_to_local_bundle_when_codex_access_is_denied(monkeypatch, tmp_path):
    source = tmp_path / "local-plugin"
    manifest_dir = source / ".codex-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(json.dumps({"version": "0.5.18"}), encoding="utf-8")
    (source / ".mcp.json").write_text(json.dumps(sample_mcp_config()), encoding="utf-8")

    def fake_run(command, **kwargs):
        if command[0] == "codex":
            raise PermissionError(5, "Access is denied")
        return Completed()

    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setattr(codex_install.shutil, "which", lambda name: f"C:/bin/{name}")
    monkeypatch.setattr(codex_install.sys, "platform", "win32")
    monkeypatch.setattr(codex_install.subprocess, "run", fake_run)
    monkeypatch.setattr(codex_install, "_local_plugin_bundle_source", lambda: source)
    monkeypatch.setattr(codex_install, "start_chrome_devtools_port", lambda **kwargs: {"status": "ok", "endpoint": f"http://127.0.0.1:{kwargs['port']}"})

    payload = codex_install.install_codex(chrome_mode="port")

    assert payload["status"] == "ok"
    assert payload["install_method"] == "direct-plugin-cache"
    assert payload["steps"]["marketplace_add"]["error_code"] == "windows_access_denied"
    assert payload["steps"]["plugin_cache"]["status"] == "ok"


def test_doctor_reports_plugin_files_commands_and_chrome_endpoint(monkeypatch, tmp_path):
    write_marketplace_bundle(tmp_path)
    cache_source = tmp_path / ".tmp" / "marketplaces" / codex_install.MARKETPLACE_NAME / "plugins" / codex_install.PLUGIN_NAME
    codex_install.enable_plugin_in_config(tmp_path / "config.toml")
    codex_install._copy_plugin_bundle_to_cache(tmp_path, cache_source, chrome_mode="port")

    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(codex_install.shutil, "which", lambda name: f"C:/bin/{name}")
    monkeypatch.setattr(
        codex_install,
        "check_chrome_devtools_endpoint",
        lambda endpoint="http://127.0.0.1:9222", timeout=2.0: {"ok": True, "endpoint": endpoint, "browser": "Chrome"},
    )
    monkeypatch.setattr(
        codex_install,
        "list_chrome_devtools_pages",
        lambda endpoint="http://127.0.0.1:9222", timeout=2.0: {"ok": True, "pages": [{"url": "https://www.1688.com/"}]},
    )

    payload = codex_install.doctor()

    assert payload["status"] == "ok"
    checks = {item["id"]: item for item in payload["checks"]}
    assert checks["config_plugin_enabled"]["status"] == "pass"
    assert checks["plugin_manifest"]["status"] == "pass"
    assert checks["plugin_mcp_json"]["status"] == "pass"
    assert checks["sourcing1688_mcp_command"]["status"] == "pass"
    assert checks["chrome_devtools_mcp_command"]["status"] == "pass"
    assert checks["chrome_devtools_endpoint"]["status"] == "pass"
    assert checks["chrome_devtools_1688_page"]["status"] == "pass"


def test_doctor_reports_multiple_plugin_cache_versions(monkeypatch, tmp_path):
    write_marketplace_bundle(tmp_path)
    cache_source = tmp_path / ".tmp" / "marketplaces" / codex_install.MARKETPLACE_NAME / "plugins" / codex_install.PLUGIN_NAME
    codex_install.enable_plugin_in_config(tmp_path / "config.toml")
    codex_install._copy_plugin_bundle_to_cache(tmp_path, cache_source, chrome_mode="auto")

    cache_root = tmp_path / "plugins" / "cache" / codex_install.MARKETPLACE_NAME / codex_install.PLUGIN_NAME
    (cache_root / "0.5.15").mkdir()

    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setattr(codex_install.shutil, "which", lambda name: f"C:/bin/{name}")
    monkeypatch.setattr(codex_install, "check_chrome_devtools_endpoint", lambda endpoint="http://127.0.0.1:9222", timeout=2.0: {"ok": False})

    payload = codex_install.doctor()
    checks = {item["id"]: item for item in payload["checks"]}

    assert payload["status"] == "needs_attention"
    assert checks["plugin_cache_single_version"]["status"] == "fail"
    assert checks["plugin_cache_single_version"]["details"]["versions"] == ["0.5.15", "0.5.16"]


def test_install_codex_cli_json_can_be_mocked(monkeypatch, tmp_path):
    payload = {
        "status": "ok",
        "plugin_id": codex_install.PLUGIN_CONFIG_ID,
        "mcp_servers": "plugin-bundled",
    }

    monkeypatch.setattr("sourcing1688.cli.install_codex", lambda **kwargs: payload)
    result = runner.invoke(app, ["install-codex", "--no-open-chrome-setup", "--json"])
    parsed = json.loads(result.output)

    assert result.exit_code == 0
    assert parsed["status"] == "ok"
    assert parsed["mcp_servers"] == "plugin-bundled"


def test_install_codex_cli_accepts_manual_windows_install_and_chrome_mode(monkeypatch):
    payload = {
        "status": "ok",
        "manual_windows_install": True,
        "chrome_mode": "port",
    }

    def fake_install(open_chrome_setup=True, manual_windows_install=False, chrome_mode="default", verify=False):
        assert manual_windows_install is True
        assert chrome_mode == "port"
        assert verify is True
        return payload

    monkeypatch.setattr("sourcing1688.cli.install_codex", fake_install)
    result = runner.invoke(app, ["install-codex", "--manual-windows-install", "--chrome-mode", "port", "--verify", "--json"])
    parsed = json.loads(result.output)

    assert result.exit_code == 0
    assert parsed["status"] == "ok"
    assert parsed["chrome_mode"] == "port"


def test_install_codex_cli_human_output_is_concise(monkeypatch):
    payload = {
        "status": "ok",
        "chrome_mode": "auto",
        "steps": {
            "plugin_cache": {"version": "0.5.30"},
            "chrome_devtools": {
                "status": "needs_user_action",
                "next_steps": [
                    "Open chrome://inspect/#remote-debugging in your normal signed-in Chrome profile.",
                    "Restart Codex Desktop or open a new chat.",
                ],
            },
        },
    }

    monkeypatch.setattr("sourcing1688.cli.install_codex", lambda **kwargs: payload)

    result = runner.invoke(app, ["install-codex"])

    assert result.exit_code == 0
    assert "Installed 1688 Sourcing Agent" in result.output
    assert "Version: 0.5.30" in result.output
    assert "existing signed-in Chrome session" in result.output
    assert "chrome://inspect/#remote-debugging" in result.output
    assert '"steps"' not in result.output
    assert result.output.lstrip()[0] != "{"


def test_doctor_cli_json_can_be_mocked(monkeypatch):
    monkeypatch.setattr("sourcing1688.cli.doctor", lambda: {"status": "ok", "checks": []})

    result = runner.invoke(app, ["doctor", "--json"])
    parsed = json.loads(result.output)

    assert result.exit_code == 0
    assert parsed["status"] == "ok"


def test_global_mcp_cleanup_removes_legacy_servers(monkeypatch):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return Completed()

    monkeypatch.setattr(codex_install.subprocess, "run", fake_run)

    codex_install._remove_global_mcp_servers()

    assert ["codex", "mcp", "remove", "sourcing1688"] in commands
    assert ["codex", "mcp", "remove", "chrome-devtools"] in commands
    assert not any(command[:3] == ["codex", "mcp", "add"] for command in commands)


def test_open_chrome_setup_page_does_not_skip_opened_only_marker(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCING1688_HOME", str(tmp_path))
    codex_install.mark_chrome_setup_opened(tmp_path, command=["already-opened"])
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr(codex_install.subprocess, "run", fake_run)
    monkeypatch.setattr(codex_install, "check_chrome_devtools_endpoint", lambda **kwargs: {"ok": False})

    payload = codex_install._open_chrome_setup_page()

    assert payload["status"] == "needs_user_action"
    assert payload["ok"] is False
    assert payload["skipped"] is False
    assert payload["requires_manual_navigation"] is True
    assert calls == []


def test_uninstall_codex_cli_json_can_be_mocked(monkeypatch):
    monkeypatch.setattr("sourcing1688.cli.uninstall_codex", lambda remove_runtime=False: {"status": "ok", "remove_runtime": remove_runtime})

    result = runner.invoke(app, ["uninstall-codex", "--remove-runtime", "--json"])
    parsed = json.loads(result.output)

    assert result.exit_code == 0
    assert parsed["status"] == "ok"
    assert parsed["remove_runtime"] is True


def test_uninstall_codex_cli_human_output_is_concise(monkeypatch):
    monkeypatch.setattr(
        "sourcing1688.cli.uninstall_codex",
        lambda remove_runtime=False: {"status": "ok", "steps": {"runtime": {"removed": True}}, "next_step": "Restart Codex Desktop."},
    )

    result = runner.invoke(app, ["uninstall-codex", "--remove-runtime"])

    assert result.exit_code == 0
    assert "Removed 1688 Sourcing Agent" in result.output
    assert "Runtime data: removed" in result.output
    assert '"steps"' not in result.output
    assert result.output.lstrip()[0] != "{"
