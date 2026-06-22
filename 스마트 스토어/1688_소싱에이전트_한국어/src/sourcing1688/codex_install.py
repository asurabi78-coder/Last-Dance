from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from sourcing1688.chrome_setup import (
    CHROME_DEVTOOLS_SETUP_URL,
    DEFAULT_CHROME_DEVTOOLS_URL,
    check_chrome_devtools_endpoint,
    chrome_devtools_setup_manual_action,
    chrome_devtools_setup_requires_manual_navigation,
    chrome_devtools_setup_command,
    is_chrome_setup_marker_verified,
    list_chrome_devtools_pages,
    mark_chrome_devtools_endpoint_verified,
    mark_chrome_setup_opened,
    read_chrome_setup_marker,
    start_chrome_devtools_port,
)


REPO_URL = "https://github.com/Squirbie/sourcing-agent-1688.git"
MARKETPLACE_NAME = "sourcing-agent-1688-marketplace"
PLUGIN_NAME = "sourcing-agent-1688"
PLUGIN_CONFIG_ID = f'{PLUGIN_NAME}@{MARKETPLACE_NAME}'
SOURCING_MCP_NAME = "sourcing1688"
CHROME_MCP_NAME = "chrome-devtools"


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def sourcing_home() -> Path:
    return Path(os.environ.get("SOURCING1688_HOME") or Path.home() / ".sourcing1688")


def _run(command: list[str], *, check: bool = False, stage: str | None = None) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return {
            "command": command,
            "stage": stage,
            "returncode": 127,
            "ok": False,
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
        }
    except PermissionError as exc:
        return {
            "command": command,
            "stage": stage,
            "returncode": 126,
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
            "error_code": "windows_access_denied",
            "message": f"Windows denied access while running {command[0]}.",
            "next_step": "On Windows this can happen when Codex resolves to a WindowsApps app alias. Use `sourcing-agent-1688 install-codex --manual-windows-install --verify`.",
        }
    result = {
        "command": command,
        "stage": stage,
        "returncode": completed.returncode,
        "ok": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    if sys.platform.startswith("win") and completed.returncode != 0 and "Access is denied" in (completed.stderr or completed.stdout):
        result.update(
            {
                "error_code": "windows_access_denied",
                "message": f"Windows denied access while running {command[0]}.",
                "next_step": "Codex CLI may be resolving through a WindowsApps app alias. Rerun with `--manual-windows-install --verify`.",
            }
        )
    if check and completed.returncode != 0:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def _plugin_block() -> str:
    return f'[plugins."{PLUGIN_CONFIG_ID}"]\nenabled = true\n'


def enable_plugin_in_config(config_path: Path) -> dict[str, Any]:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    lines = original.splitlines()
    header = f'[plugins."{PLUGIN_CONFIG_ID}"]'
    output: list[str] = []
    index = 0
    replaced = False

    while index < len(lines):
        line = lines[index]
        if line.strip() == header:
            output.append(header)
            output.append("enabled = true")
            replaced = True
            index += 1
            while index < len(lines) and not lines[index].lstrip().startswith("["):
                index += 1
            continue
        output.append(line)
        index += 1

    if not replaced:
        if output and output[-1].strip():
            output.append("")
        output.extend(_plugin_block().rstrip("\n").splitlines())

    config_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    return {"config_path": str(config_path), "plugin_id": PLUGIN_CONFIG_ID, "enabled": True}


def disable_plugin_in_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {"config_path": str(config_path), "removed": False}
    lines = config_path.read_text(encoding="utf-8").splitlines()
    header = f'[plugins."{PLUGIN_CONFIG_ID}"]'
    output: list[str] = []
    removed = False
    index = 0
    while index < len(lines):
        if lines[index].strip() == header:
            removed = True
            index += 1
            while index < len(lines) and not lines[index].lstrip().startswith("["):
                index += 1
            continue
        output.append(lines[index])
        index += 1
    config_path.write_text("\n".join(output).rstrip() + ("\n" if output else ""), encoding="utf-8")
    return {"config_path": str(config_path), "removed": removed}


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _resolve_chrome_mode(chrome_mode: str) -> str:
    selected = chrome_mode.lower().strip()
    if selected in {"default", "windows-default", "existing", "existing-session"}:
        return "auto"
    if selected in {"auto", "auto-connect", "autoconnect"}:
        return "auto"
    if selected in {"port", "browser-url", "dedicated", "dedicated-profile"}:
        return "port"
    raise ValueError("chrome_mode must be default, auto, existing, dedicated, or port.")


def _npx_command() -> str:
    if _is_windows():
        return "npx.cmd"
    return "npx"


def _rewrite_chrome_mcp_config(mcp_path: Path, *, chrome_mode: str) -> dict[str, Any]:
    data = json.loads(mcp_path.read_text(encoding="utf-8"))
    servers = data.setdefault("mcpServers", {})
    chrome = servers.get(CHROME_MCP_NAME)
    if not isinstance(chrome, dict):
        return {"status": "skipped", "reason": "chrome_devtools_server_missing", "path": str(mcp_path)}

    chrome["command"] = _npx_command()
    args = list(chrome.get("args") or [])
    args = [arg for arg in args if arg not in {"--auto-connect", "--autoConnect"}]
    if chrome_mode == "port":
        endpoint = DEFAULT_CHROME_DEVTOOLS_URL
        filtered: list[str] = []
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg == "--browserUrl":
                skip_next = True
                continue
            if arg.startswith("--browserUrl="):
                continue
            filtered.append(arg)
        args = filtered
        args.extend(["--browserUrl", endpoint])
    elif "--autoConnect" not in args:
        package_index = args.index("chrome-devtools-mcp@latest") if "chrome-devtools-mcp@latest" in args else len(args)
        args.insert(package_index + 1, "--autoConnect")
    chrome["args"] = args
    mcp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "ok", "path": str(mcp_path), "chrome_mode": chrome_mode, "command": chrome["command"], "args": args}


def _copy_plugin_bundle_to_cache(home: Path, source: Path, *, chrome_mode: str) -> dict[str, Any]:
    manifest_path = source / ".codex-plugin" / "plugin.json"
    if not manifest_path.exists() or not (source / ".mcp.json").exists():
        return {
            "status": "error",
            "reason": "plugin_bundle_missing_required_files",
            "source": str(source),
        }

    try:
        version = json.loads(manifest_path.read_text(encoding="utf-8")).get("version", "current")
    except Exception:
        version = "current"

    cache_root = _plugin_cache_root(home)
    removed_versions = _plugin_cache_versions(home)
    target = cache_root / str(version)
    if cache_root.exists():
        shutil.rmtree(cache_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    mcp_adjustment = _rewrite_chrome_mcp_config(target / ".mcp.json", chrome_mode=chrome_mode)
    return {
        "status": "ok",
        "source": str(source),
        "target": str(target),
        "version": version,
        "removed_versions": removed_versions,
        "mcp_adjustment": mcp_adjustment,
    }


def _marketplace_plugin_bundle_source(home: Path) -> Path:
    return home / ".tmp" / "marketplaces" / MARKETPLACE_NAME / "plugins" / PLUGIN_NAME


def _local_plugin_bundle_source() -> Path | None:
    module_path = Path(__file__).resolve()
    candidates = [
        module_path.parents[2] / "plugins" / PLUGIN_NAME,
        module_path.parents[1] / "plugins" / PLUGIN_NAME,
        Path.cwd() / "plugins" / PLUGIN_NAME,
        Path.cwd() if (Path.cwd() / ".codex-plugin" / "plugin.json").exists() else Path.cwd() / "__missing__",
    ]
    for candidate in candidates:
        if (candidate / ".codex-plugin" / "plugin.json").exists() and (candidate / ".mcp.json").exists():
            return candidate
    return None


def _copy_plugin_bundle(home: Path, *, chrome_mode: str) -> dict[str, Any]:
    source = _marketplace_plugin_bundle_source(home)
    if not source.exists():
        return {
            "status": "skipped",
            "reason": "marketplace_plugin_bundle_not_found",
            "source": str(source),
        }
    return _copy_plugin_bundle_to_cache(home, source, chrome_mode=chrome_mode)


def _clear_plugin_cache(home: Path) -> dict[str, Any]:
    cache = home / "plugins" / "cache" / MARKETPLACE_NAME
    if not cache.exists():
        return {"status": "ok", "path": str(cache), "removed": False}
    try:
        shutil.rmtree(cache)
    except Exception as exc:  # noqa: BLE001
        return {"status": "warning", "path": str(cache), "removed": False, "message": str(exc)}
    return {"status": "ok", "path": str(cache), "removed": True}


def _open_chrome_setup_page() -> dict[str, Any]:
    marker = read_chrome_setup_marker()
    endpoint = check_chrome_devtools_endpoint()
    if endpoint.get("ok"):
        pages = list_chrome_devtools_pages()
        verified_marker = mark_chrome_devtools_endpoint_verified(endpoint=DEFAULT_CHROME_DEVTOOLS_URL, command=None, pages=pages.get("pages", []))
        return {
            "url": CHROME_DEVTOOLS_SETUP_URL,
            "ok": True,
            "skipped": True,
            "endpoint_verified": True,
            "endpoint": endpoint,
            "marker": verified_marker,
        }
    if is_chrome_setup_marker_verified(marker):
        return {
            "url": CHROME_DEVTOOLS_SETUP_URL,
            "ok": True,
            "skipped": True,
            "marker": marker,
        }
    if chrome_devtools_setup_requires_manual_navigation():
        return chrome_devtools_setup_manual_action()
    command = chrome_devtools_setup_command()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    except FileNotFoundError as exc:
        return {"url": CHROME_DEVTOOLS_SETUP_URL, "command": command, "ok": False, "error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {"url": CHROME_DEVTOOLS_SETUP_URL, "command": command, "ok": False, "error": f"Timed out after {exc.timeout} seconds."}
    return {
        "url": CHROME_DEVTOOLS_SETUP_URL,
        "command": command,
        "ok": completed.returncode == 0,
        "skipped": False,
        "marker": mark_chrome_setup_opened(command=command) if completed.returncode == 0 else None,
        "returncode": completed.returncode,
        "stderr": completed.stderr.strip(),
    }


def _remove_global_mcp_servers() -> list[dict[str, Any]]:
    return [
        _run(["codex", "mcp", "remove", SOURCING_MCP_NAME], stage="global_mcp_cleanup_sourcing1688"),
        _run(["codex", "mcp", "remove", CHROME_MCP_NAME], stage="global_mcp_cleanup_chrome_devtools"),
    ]


def _has_windows_access_denied(value: Any) -> bool:
    if isinstance(value, dict):
        return value.get("error_code") == "windows_access_denied" or any(_has_windows_access_denied(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_windows_access_denied(item) for item in value)
    return False


def _direct_plugin_cache_install(home: Path, config_path: Path, *, chrome_mode: str) -> dict[str, Any]:
    steps: dict[str, Any] = {}
    source = _local_plugin_bundle_source()
    if source is None:
        steps["plugin_cache"] = {
            "status": "error",
            "reason": "local_plugin_bundle_not_found",
            "checked_from": str(Path(__file__).resolve()),
        }
        return {
            "status": "error",
            "message": "Codex CLI could not be used, and the packaged plugin bundle was not found.",
            "steps": steps,
            "manual_check_files": [
                str(config_path),
                str(home / "plugins" / "cache" / MARKETPLACE_NAME / PLUGIN_NAME),
            ],
            "next_step": "Install from a source checkout or rerun after upgrading sourcing-agent-1688 to a package that includes the bundled plugin files.",
        }

    steps["plugin_enabled"] = enable_plugin_in_config(config_path)
    steps["plugin_cache"] = _copy_plugin_bundle_to_cache(home, source, chrome_mode=chrome_mode)
    return {"status": "ok", "steps": steps, "source": str(source)}


def _start_or_open_chrome(*, chrome_mode: str) -> dict[str, Any]:
    if chrome_mode == "port":
        return start_chrome_devtools_port(port=9222, url="https://www.1688.com/")
    return _open_chrome_setup_page()


def install_codex(
    *,
    open_chrome_setup: bool = True,
    manual_windows_install: bool = False,
    chrome_mode: str = "default",
    verify: bool = False,
) -> dict[str, Any]:
    selected_chrome_mode = _resolve_chrome_mode(chrome_mode)
    codex_cli = shutil.which("codex")
    if codex_cli is None and not manual_windows_install:
        return {
            "status": "error",
            "message": "Codex CLI was not found on PATH.",
            "stage": "codex_cli_lookup",
            "next_step": "Install or open Codex Desktop first. On Windows, you can also run `sourcing-agent-1688 install-codex --manual-windows-install --verify`.",
        }
    if shutil.which("uvx") is None:
        return {
            "status": "error",
            "message": "uvx was not found on PATH.",
            "stage": "uvx_lookup",
            "next_step": "Install uv first, then rerun this command.",
        }

    home = codex_home()
    config_path = home / "config.toml"
    home.mkdir(parents=True, exist_ok=True)

    steps: dict[str, Any] = {}
    install_method = "codex-cli-marketplace"

    if manual_windows_install:
        fallback = _direct_plugin_cache_install(home, config_path, chrome_mode=selected_chrome_mode)
        steps.update(fallback["steps"])
        if fallback["status"] != "ok":
            return fallback
        install_method = "direct-plugin-cache"
    else:
        steps["marketplace_add"] = _run(["codex", "plugin", "marketplace", "add", REPO_URL], stage="marketplace_add")
        steps["old_plugin_cache"] = _clear_plugin_cache(home)
        steps["marketplace_upgrade"] = _run(["codex", "plugin", "marketplace", "upgrade", MARKETPLACE_NAME], stage="marketplace_upgrade")
        if _has_windows_access_denied(steps):
            fallback = _direct_plugin_cache_install(home, config_path, chrome_mode=selected_chrome_mode)
            steps["windows_direct_fallback"] = fallback
            if fallback["status"] != "ok":
                return {
                    "status": "error",
                    "message": "Codex CLI failed with Windows access denied, and direct plugin-cache install could not complete.",
                    "steps": steps,
                    "manual_check_files": [
                        str(config_path),
                        str(home / "plugins" / "cache" / MARKETPLACE_NAME / PLUGIN_NAME),
                    ],
                    "next_step": "Rerun `sourcing-agent-1688 install-codex --manual-windows-install --verify` from a source checkout.",
                }
            steps.update(fallback["steps"])
            install_method = "direct-plugin-cache"
        elif not steps["marketplace_add"]["ok"] and not steps["marketplace_upgrade"]["ok"]:
            return {
                "status": "error",
                "message": "Could not add or upgrade the Codex plugin marketplace.",
                "stage": "marketplace_registration",
                "steps": steps,
                "next_step": "Rerun with `--json` and check marketplace_add/marketplace_upgrade stderr.",
            }
        else:
            steps["plugin_enabled"] = enable_plugin_in_config(config_path)
            steps["plugin_cache"] = _copy_plugin_bundle(home, chrome_mode=selected_chrome_mode)
            if steps["plugin_cache"].get("status") != "ok":
                return {
                    "status": "error",
                    "message": "Plugin marketplace was registered, but the plugin bundle was not copied into the Codex plugin cache.",
                    "stage": "plugin_cache",
                    "steps": steps,
                    "next_step": "Rerun `codex plugin marketplace upgrade sourcing-agent-1688-marketplace`, then rerun install-codex.",
                }
            steps["global_mcp_cleanup"] = _remove_global_mcp_servers()
            steps["mcp_list"] = _run(["codex", "mcp", "list"], stage="mcp_list")

    if open_chrome_setup:
        steps["chrome_devtools"] = _start_or_open_chrome(chrome_mode=selected_chrome_mode)

    status = "ok"
    payload = {
        "status": status,
        "message": "Codex Desktop plugin is installed. MCP servers are loaded from the plugin bundle.",
        "codex_home": str(home),
        "config_path": str(config_path),
        "plugin_id": PLUGIN_CONFIG_ID,
        "install_method": install_method,
        "chrome_mode": selected_chrome_mode,
        "mcp_servers": "plugin-bundled",
        "steps": steps,
        "next_step": "Restart Codex Desktop, open a new chat, then use @sourcing-agent-1688.",
    }
    if verify:
        payload["verification"] = doctor()
    return payload


def _plugin_cache_root(home: Path) -> Path:
    return home / "plugins" / "cache" / MARKETPLACE_NAME / PLUGIN_NAME


def _plugin_cache_versions(home: Path) -> list[str]:
    cache_root = _plugin_cache_root(home)
    if not cache_root.exists():
        return []
    return sorted(path.name for path in cache_root.iterdir() if path.is_dir())


def _latest_plugin_cache(home: Path) -> Path | None:
    cache_root = _plugin_cache_root(home)
    candidates = _plugin_cache_versions(home)
    if not candidates:
        return None
    return cache_root / candidates[-1]


def _check(check_id: str, passed: bool, *, message: str, next_step: str | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "message": message,
    }
    if next_step:
        payload["next_step"] = next_step
    if details:
        payload["details"] = details
    return payload


def doctor() -> dict[str, Any]:
    home = codex_home()
    config_path = home / "config.toml"
    cache = _latest_plugin_cache(home)
    mcp_path = cache / ".mcp.json" if cache else None
    checks: list[dict[str, Any]] = []

    config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    config_enabled = f'[plugins."{PLUGIN_CONFIG_ID}"]' in config_text and "enabled = true" in config_text
    checks.append(
        _check(
            "config_plugin_enabled",
            config_enabled,
            message=f"Codex config plugin block {'is enabled' if config_enabled else 'is missing'} at {config_path}.",
            next_step=f"Run `sourcing-agent-1688 install-codex --manual-windows-install --verify`." if not config_enabled else None,
            details={"path": str(config_path)},
        )
    )

    manifest_path = cache / ".codex-plugin" / "plugin.json" if cache else None
    manifest_ok = bool(manifest_path and manifest_path.exists())
    checks.append(
        _check(
            "plugin_manifest",
            manifest_ok,
            message=f"Plugin manifest {'exists' if manifest_ok else 'was not found'} in the Codex plugin cache.",
            next_step="Reinstall the plugin cache with install-codex." if not manifest_ok else None,
            details={"path": str(manifest_path) if manifest_path else str(home / "plugins" / "cache" / MARKETPLACE_NAME / PLUGIN_NAME)},
        )
    )

    mcp_ok = bool(mcp_path and mcp_path.exists())
    mcp_config: dict[str, Any] = {}
    if mcp_ok and mcp_path:
        try:
            mcp_config = json.loads(mcp_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            mcp_ok = False
    checks.append(
        _check(
            "plugin_mcp_json",
            mcp_ok,
            message=f"Plugin MCP config {'is readable' if mcp_ok else 'is missing or invalid'}.",
            next_step="Reinstall the plugin cache; .mcp.json must be valid JSON." if not mcp_ok else None,
            details={"path": str(mcp_path) if mcp_path else ""},
        )
    )

    versions = _plugin_cache_versions(home)
    single_version = len(versions) == 1
    checks.append(
        _check(
            "plugin_cache_single_version",
            single_version,
            message="Exactly one plugin cache version is present." if single_version else f"Expected one plugin cache version, found {len(versions)}.",
            next_step="Run `sourcing-agent-1688 install-codex --manual-windows-install --verify` to prune old cached versions." if not single_version else None,
            details={"cache_root": str(_plugin_cache_root(home)), "versions": versions},
        )
    )

    servers = mcp_config.get("mcpServers", {}) if isinstance(mcp_config, dict) else {}
    sourcing = servers.get(SOURCING_MCP_NAME, {}) if isinstance(servers, dict) else {}
    sourcing_command = sourcing.get("command") if isinstance(sourcing, dict) else None
    sourcing_found = bool(sourcing_command and shutil.which(str(sourcing_command)))
    checks.append(
        _check(
            "sourcing1688_mcp_command",
            sourcing_found,
            message=f"sourcing1688 MCP command `{sourcing_command or ''}` {'resolves on PATH' if sourcing_found else 'does not resolve on PATH'}.",
            next_step="Install uv/uvx, then rerun doctor." if not sourcing_found else None,
            details={"command": sourcing_command or ""},
        )
    )

    chrome = servers.get(CHROME_MCP_NAME, {}) if isinstance(servers, dict) else {}
    chrome_command = chrome.get("command") if isinstance(chrome, dict) else None
    chrome_args = [str(arg) for arg in (chrome.get("args") or [])] if isinstance(chrome, dict) else []
    chrome_found = bool(chrome_command and shutil.which(str(chrome_command)))
    checks.append(
        _check(
            "chrome_devtools_mcp_command",
            chrome_found,
            message=f"Chrome DevTools MCP command `{chrome_command or ''}` {'resolves on PATH' if chrome_found else 'does not resolve on PATH'}.",
            next_step="Install Node.js LTS. On Windows, reinstall so the plugin uses npx.cmd instead of npx.ps1." if not chrome_found else None,
            details={"command": chrome_command or ""},
        )
    )

    auto_connect = any(arg in {"--autoConnect", "--auto-connect"} for arg in chrome_args)
    browser_url = None
    for index, arg in enumerate(chrome_args):
        if arg == "--browserUrl" and index + 1 < len(chrome_args):
            browser_url = chrome_args[index + 1]
        elif arg.startswith("--browserUrl="):
            browser_url = arg.split("=", 1)[1]
    chrome_mode_ok = auto_connect or bool(browser_url)
    checks.append(
        _check(
            "chrome_devtools_mcp_mode",
            chrome_mode_ok,
            message=(
                "Chrome DevTools MCP is configured for the user's existing Chrome session."
                if auto_connect
                else "Chrome DevTools MCP is configured for a dedicated browserUrl endpoint."
                if browser_url
                else "Chrome DevTools MCP is missing autoConnect or browserUrl."
            ),
            next_step="Reinstall with `sourcing-agent-1688 install-codex --verify`." if not chrome_mode_ok else None,
            details={"args": chrome_args, "browser_url": browser_url, "auto_connect": auto_connect},
        )
    )

    if auto_connect and not browser_url:
        checks.append(
            _check(
                "chrome_devtools_existing_session_permission",
                True,
                message="Existing-session mode is installed. Chrome permission is confirmed inside Codex when the chrome-devtools MCP connects.",
                next_step=f"Open {CHROME_DEVTOOLS_SETUP_URL} in your signed-in Chrome profile, enable remote debugging, restart Codex, then approve the Chrome prompt.",
                details={"setup_url": CHROME_DEVTOOLS_SETUP_URL},
            )
        )
    else:
        endpoint = browser_url or DEFAULT_CHROME_DEVTOOLS_URL
        endpoint_status = check_chrome_devtools_endpoint(endpoint)
        checks.append(
            _check(
                "chrome_devtools_endpoint",
                bool(endpoint_status.get("ok")),
                message=f"Chrome DevTools endpoint {endpoint} {'responds' if endpoint_status.get('ok') else 'does not respond'}.",
                next_step="Run `sourcing-agent-1688 chrome-devtools start`, then rerun doctor." if not endpoint_status.get("ok") else None,
                details=endpoint_status,
            )
        )

        pages_status = list_chrome_devtools_pages(endpoint) if endpoint_status.get("ok") else {"ok": False, "pages": []}
        pages = pages_status.get("pages") or []
        has_1688_page = any("1688.com" in str(page.get("url", "")) for page in pages if isinstance(page, dict))
        checks.append(
            _check(
                "chrome_devtools_1688_page",
                has_1688_page,
                message="A 1688 page is visible in Chrome DevTools." if has_1688_page else "No 1688 page is visible in Chrome DevTools.",
                next_step="Open https://www.1688.com/ in the Chrome window started by `sourcing-agent-1688 chrome-devtools start`." if not has_1688_page else None,
                details={"endpoint": endpoint, "page_count": len(pages)},
            )
        )

    failed = [item for item in checks if item["status"] != "pass"]
    return {
        "status": "ok" if not failed else "needs_attention",
        "codex_home": str(home),
        "plugin_id": PLUGIN_CONFIG_ID,
        "checks": checks,
    }


def uninstall_codex(*, remove_runtime: bool = False) -> dict[str, Any]:
    home = codex_home()
    steps: dict[str, Any] = {}
    steps["mcp_remove"] = [
        _run(["codex", "mcp", "remove", SOURCING_MCP_NAME]),
        _run(["codex", "mcp", "remove", CHROME_MCP_NAME]),
    ]
    steps["marketplace_remove"] = _run(["codex", "plugin", "marketplace", "remove", MARKETPLACE_NAME])
    steps["plugin_config"] = disable_plugin_in_config(home / "config.toml")

    cache = home / "plugins" / "cache" / MARKETPLACE_NAME
    if cache.exists():
        shutil.rmtree(cache)
        cache_removed = True
    else:
        cache_removed = False
    steps["plugin_cache"] = {"path": str(cache), "removed": cache_removed}

    if remove_runtime:
        runtime = sourcing_home()
        if runtime.exists():
            shutil.rmtree(runtime)
            runtime_removed = True
        else:
            runtime_removed = False
        steps["runtime"] = {"path": str(runtime), "removed": runtime_removed}

    return {
        "status": "ok",
        "message": "Codex Desktop plugin, marketplace, and MCP server config removed.",
        "steps": steps,
        "next_step": "Restart Codex Desktop.",
    }
