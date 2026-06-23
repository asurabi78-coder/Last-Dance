import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_root_codex_plugin_manifest_points_to_root_mcp_json():
    plugin = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))

    assert plugin["name"] == "sourcing-agent-1688"
    assert plugin["version"] == "0.5.30"
    assert plugin["skills"] == "./skills/"
    assert plugin["mcpServers"] == "./.mcp.json"
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


def test_codex_marketplace_points_to_bundled_plugin_layout():
    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    bundle = ROOT / "plugins" / "sourcing-agent-1688"
    plugin = json.loads((bundle / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((bundle / ".mcp.json").read_text(encoding="utf-8"))

    entry = marketplace["plugins"][0]
    assert entry["name"] == "sourcing-agent-1688"
    assert entry["source"] == {"source": "local", "path": "./plugins/sourcing-agent-1688"}
    assert entry["policy"]["installation"] == "INSTALLED_BY_DEFAULT"
    assert entry["policy"]["authentication"] == "ON_INSTALL"
    assert plugin["name"] == "sourcing-agent-1688"
    assert plugin["version"] == "0.5.30"
    assert plugin["mcpServers"] == "./.mcp.json"
    assert plugin["skills"] == "./skills/"
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


def test_removed_cross_platform_layouts_are_absent():
    assert not (ROOT / ".mcp.codex.json").exists()
    assert not (ROOT / ".claude-plugin").exists()
