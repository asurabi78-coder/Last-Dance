import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from sourcing1688.cli import app
from sourcing1688.config import get_settings
from sourcing1688.providers.browser_provider import Browser1688Provider


runner = CliRunner()
ROOT = Path(__file__).resolve().parents[1]


def invoke_json(args, env=None):
    result = runner.invoke(app, [*args, "--json"], env=env)
    return result, json.loads(result.output)


def test_home_default_path_resolution(monkeypatch):
    monkeypatch.delenv("SOURCING1688_HOME", raising=False)
    settings = get_settings()

    assert settings.home == Path.home() / ".sourcing1688"
    assert settings.db_path == settings.home / "data" / "sourcing1688.duckdb"
    assert settings.output_dir == settings.home / "assets"
    assert settings.ali1688_token_cache_path == settings.home / "token-cache" / ".1688_token_cache.json"


def test_init_home_creates_expected_dirs(tmp_path):
    result, payload = invoke_json(["init-home"], env={"SOURCING1688_HOME": str(tmp_path)})

    assert result.exit_code == 0
    assert payload["status"] == "ok"
    for name in ["config", "data", "assets", "raw", "browser-profile", "token-cache", "logs"]:
        assert (tmp_path / name).is_dir()


def test_home_cli_json(tmp_path):
    result, payload = invoke_json(["home"], env={"SOURCING1688_HOME": str(tmp_path)})

    assert result.exit_code == 0
    assert payload["status"] == "ok"
    assert payload["home"] == str(tmp_path)
    assert "token_cache" in payload["paths"]


def test_clean_dry_run_does_not_delete(tmp_path):
    target = tmp_path / "assets" / "sample.txt"
    target.parent.mkdir(parents=True)
    target.write_text("keep", encoding="utf-8")

    result, payload = invoke_json(["clean", "--dry-run"], env={"SOURCING1688_HOME": str(tmp_path)})

    assert result.exit_code == 0
    assert payload["status"] == "dry_run"
    assert target.exists()
    assert payload["would_delete"]


def test_uninstall_requires_yes(tmp_path):
    result, payload = invoke_json(["uninstall"], env={"SOURCING1688_HOME": str(tmp_path)})

    assert result.exit_code == 1
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "confirmation_required"


def test_uninstall_yes_deletes_temp_home(tmp_path):
    (tmp_path / "assets").mkdir(parents=True)

    result, payload = invoke_json(["uninstall", "--yes"], env={"SOURCING1688_HOME": str(tmp_path)})

    assert result.exit_code == 0
    assert payload["status"] == "ok"
    assert not tmp_path.exists()


def test_auth_status_redacts_secrets(tmp_path):
    env = {
        "SOURCING1688_HOME": str(tmp_path),
        "ALI1688_APP_KEY": "app-key-secret",
        "ALI1688_APP_SECRET": "app-secret-secret",
        "ALI1688_REFRESH_TOKEN": "refresh-token-secret",
    }
    result, payload = invoke_json(["auth", "status"], env=env)

    assert result.exit_code == 0
    assert payload["ready"] is True
    assert "app-key-secret" not in result.output
    assert "app-secret-secret" not in result.output
    assert "refresh-token-secret" not in result.output


def test_auth_url_builds_expected_url_without_secret(tmp_path):
    env = {"SOURCING1688_HOME": str(tmp_path), "ALI1688_APP_KEY": "test-app-key", "ALI1688_APP_SECRET": "hidden-secret"}
    result, payload = invoke_json(["auth", "url", "--redirect-uri", "https://example.com/callback"], env=env)

    assert result.exit_code == 0
    assert payload["status"] == "ok"
    assert "client_id=test-app-key" in payload["authorization_url"]
    assert "hidden-secret" not in result.output


def test_auth_exchange_uses_mocked_http_and_stores_token_without_printing(monkeypatch, tmp_path):
    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "access-secret", "refresh_token": "refresh-secret", "expires_in": 3600}

    async def mock_post(self, url, data=None):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    env = {
        "SOURCING1688_HOME": str(tmp_path),
        "ALI1688_APP_KEY": "test-app-key",
        "ALI1688_APP_SECRET": "hidden-secret",
    }
    result, payload = invoke_json(["auth", "exchange", "--code", "code-123", "--redirect-uri", "https://example.com/callback"], env=env)

    assert result.exit_code == 0
    assert payload["token_saved"] is True
    assert payload["has_refresh_token"] is True
    assert "access-secret" not in result.output
    assert "refresh-secret" not in result.output
    assert (tmp_path / "token-cache" / ".1688_token_cache.json").exists()


def test_browser_profile_open_command_can_be_mocked(monkeypatch, tmp_path):
    async def mock_open_browser_profile(path, url):
        return {"status": "ok", "profile_path": str(path), "url": url, "profile_saved": True}

    monkeypatch.setattr("sourcing1688.cli.open_browser_profile", mock_open_browser_profile)
    result, payload = invoke_json(["browser-profile", "open", "--path", str(tmp_path / "profile")])

    assert result.exit_code == 0
    assert payload["status"] == "ok"
    assert payload["profile_saved"] is True


def test_distribution_files_are_root_codex_desktop_plugin_only():
    mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    plugin = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    bundle_root = ROOT / "plugins" / "sourcing-agent-1688"
    bundled_plugin = json.loads((bundle_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    bundled_mcp = json.loads((bundle_root / ".mcp.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    skill = (ROOT / "skills" / "sourcing-agent-1688" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "C:/Users" not in json.dumps(mcp)
    assert "C:\\Users" not in json.dumps(mcp)
    assert "mcpServers" in mcp
    assert "mcp_servers" not in mcp
    assert mcp["mcpServers"]["sourcing1688"]["command"] == "uvx"
    assert "--refresh" in mcp["mcpServers"]["sourcing1688"]["args"]
    assert "git+https://github.com/Squirbie/sourcing-agent-1688.git" in mcp["mcpServers"]["sourcing1688"]["args"]
    assert mcp["mcpServers"]["chrome-devtools"]["command"] == "npx"
    assert "chrome-devtools-mcp@latest" in mcp["mcpServers"]["chrome-devtools"]["args"]
    assert "--autoConnect" in mcp["mcpServers"]["chrome-devtools"]["args"]
    assert "--redact-network-headers" in mcp["mcpServers"]["chrome-devtools"]["args"]
    assert mcp["mcpServers"]["chrome-devtools"]["startup_timeout_sec"] == 60
    assert mcp["mcpServers"]["chrome-devtools"]["tool_timeout_sec"] == 300
    assert plugin["version"] == "0.5.30"
    assert plugin["name"] == "sourcing-agent-1688"
    assert plugin["skills"] == "./skills/"
    assert plugin["mcpServers"] == "./.mcp.json"
    assert marketplace["plugins"][0]["source"] == {"source": "local", "path": "./plugins/sourcing-agent-1688"}
    assert marketplace["plugins"][0]["policy"]["installation"] == "INSTALLED_BY_DEFAULT"
    assert bundled_plugin["name"] == "sourcing-agent-1688"
    assert bundled_plugin["version"] == "0.5.30"
    assert bundled_plugin["mcpServers"] == "./.mcp.json"
    assert "mcpServers" in bundled_mcp
    assert "mcp_servers" not in bundled_mcp
    assert bundled_mcp["mcpServers"]["chrome-devtools"]["command"] == "npx"
    assert "chrome-devtools-mcp@latest" in bundled_mcp["mcpServers"]["chrome-devtools"]["args"]
    assert "--autoConnect" in bundled_mcp["mcpServers"]["chrome-devtools"]["args"]
    assert bundled_mcp["mcpServers"]["chrome-devtools"]["startup_timeout_sec"] == 60
    assert bundled_mcp["mcpServers"]["chrome-devtools"]["tool_timeout_sec"] == 300
    assert "sourcing1688-mcp" in pyproject
    assert "sourcing-agent-1688" in pyproject
    assert "스마트폰 거치대" in readme
    assert "@sourcing-agent-1688" in readme
    assert "chrome devtools" in readme
    assert "codex desktop" in readme
    assert "삭제" in readme
    assert "sourcing-agent-1688" in skill


def test_removed_cross_platform_and_demo_files_are_absent():
    assert not (ROOT / "docs").exists()
    assert not (ROOT / "scripts").exists()
    assert not (ROOT / ".claude-plugin").exists()
    assert not (ROOT / ".mcp.codex.json").exists()
    assert not (ROOT / "README.en.md").exists()
    assert not (ROOT / "src" / "sourcing1688" / "providers" / "mock_provider.py").exists()
    assert "mock" not in (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "claude" not in (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "openclaw" not in (ROOT / "README.md").read_text(encoding="utf-8").lower()


def test_browser_raw_snapshot_uses_runtime_home(tmp_path):
    provider = Browser1688Provider(settings=get_settings().model_copy(update={"home": tmp_path}))
    path = provider._raw_snapshot_path("search")

    assert path.is_relative_to(tmp_path / "raw")
