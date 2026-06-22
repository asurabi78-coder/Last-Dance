from __future__ import annotations

import sys
import zipfile
from functools import partial
from pathlib import Path
from typing import Annotated

import anyio
import typer

from sourcing1688.auth import auth_status, build_authorization_url, clear_token_cache, exchange_code_for_token
from sourcing1688.assets.manifest import write_manifest
from sourcing1688.browser_profile import open_browser_profile
from sourcing1688.chrome_setup import start_chrome_devtools_port
from sourcing1688.codex_install import doctor, install_codex, uninstall_codex
from sourcing1688.config import get_settings
from sourcing1688.keyword_expander import expand_keywords
from sourcing1688.parsers.rendered_html import parse_rendered_html_file
from sourcing1688.services import (
    analyze_product_url,
    check_provider,
    download_product_assets,
    get_all_provider_capabilities,
    get_product_detail,
    get_provider,
    image_search_products,
    recommend_products,
    search_sourcing_products,
)
from sourcing1688.state import clean_home, home_payload, init_home, runtime_paths, uninstall_home
from sourcing1688.storage import SourcingStorage
from sourcing1688.utils import dumps_json, error_payload


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


_configure_utf8_stdio()

app = typer.Typer(help="Agent-friendly 1688 sourcing toolkit.")
shortlist_app = typer.Typer(help="Manage sourcing shortlists.")
browser_profile_app = typer.Typer(help="Manage Playwright browser profiles.")
chrome_devtools_app = typer.Typer(help="Manage Chrome DevTools connection.")
live_smoke_app = typer.Typer(help="Opt-in live smoke commands.")
auth_app = typer.Typer(help="Manage 1688 API OAuth credentials.")
app.add_typer(shortlist_app, name="shortlist")
app.add_typer(browser_profile_app, name="browser-profile")
app.add_typer(chrome_devtools_app, name="chrome-devtools")
app.add_typer(live_smoke_app, name="live-smoke")
app.add_typer(auth_app, name="auth")


JsonOption = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]
ProviderOption = Annotated[str | None, typer.Option("--provider", help="Provider: auto, chrome, api, browser, or local_html.")]


def _echo_json(payload, *, exit_code: int = 0) -> None:
    _configure_utf8_stdio()
    typer.echo(dumps_json(payload))
    if exit_code:
        raise typer.Exit(exit_code)


def _echo_install_codex_summary(payload: dict) -> None:
    if payload.get("status") != "ok":
        typer.echo("Install failed.")
        if payload.get("stage"):
            typer.echo(f"Stage: {payload['stage']}")
        if payload.get("message"):
            typer.echo(payload["message"])
        if payload.get("next_step"):
            typer.echo(f"Next: {payload['next_step']}")
        typer.echo("Details: rerun with --json.")
        return

    steps = payload.get("steps") if isinstance(payload.get("steps"), dict) else {}
    plugin_cache = steps.get("plugin_cache") if isinstance(steps.get("plugin_cache"), dict) else {}
    chrome_step = steps.get("chrome_devtools") if isinstance(steps.get("chrome_devtools"), dict) else {}
    chrome_mode = payload.get("chrome_mode")
    chrome_label = "existing signed-in Chrome session" if chrome_mode == "auto" else "separate recovery Chrome profile"

    typer.echo("Installed 1688 Sourcing Agent for Codex Desktop.")
    if plugin_cache.get("version"):
        typer.echo(f"Version: {plugin_cache['version']}")
    typer.echo(f"Chrome: {chrome_label}")

    next_steps = chrome_step.get("next_steps") if isinstance(chrome_step.get("next_steps"), list) else []
    if next_steps:
        typer.echo("")
        typer.echo("Next:")
        for index, step in enumerate(next_steps, start=1):
            typer.echo(f"{index}. {step}")
    elif payload.get("next_step"):
        typer.echo("")
        typer.echo(f"Next: {payload['next_step']}")

    typer.echo("")
    typer.echo("Check later: sourcing-agent-1688 doctor")
    typer.echo("Details: rerun with --json.")


def _echo_uninstall_codex_summary(payload: dict, *, remove_runtime: bool) -> None:
    typer.echo("Removed 1688 Sourcing Agent from Codex Desktop.")
    if remove_runtime:
        runtime = (payload.get("steps") or {}).get("runtime") if isinstance(payload.get("steps"), dict) else None
        if isinstance(runtime, dict):
            typer.echo(f"Runtime data: {'removed' if runtime.get('removed') else 'not found'}")
    if payload.get("next_step"):
        typer.echo(f"Next: {payload['next_step']}")
    typer.echo("Details: rerun with --json.")


def _handle_exception(exc: Exception, *, json_output: bool, code: str = "command_failed") -> None:
    if isinstance(exc, ValueError) and str(exc).startswith("Unknown provider:"):
        code = "unknown_provider"
    payload = error_payload(code, str(exc))
    if json_output:
        _echo_json(payload, exit_code=1)
    raise exc


def _is_offer_id_error(exc: ValueError) -> bool:
    return "offer_id" in str(exc) or "1688 offer" in str(exc)


def _zip_manifest_dir(result) -> None:
    if not result.manifest or result.manifest.zip_path:
        return
    saved_dir = Path(result.manifest.saved_dir)
    if not saved_dir.exists():
        result.warnings.append("zip_skipped_saved_dir_missing")
        return
    zip_path = saved_dir.with_suffix(".zip")
    result.manifest.zip_path = str(zip_path)
    write_manifest(result.manifest)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in saved_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(saved_dir.parent))


@app.command("home")
def home_command(json_output: JsonOption = False) -> None:
    payload = home_payload()
    if json_output:
        _echo_json(payload)
    else:
        typer.echo(dumps_json(payload))


@app.command("init-home")
def init_home_command(json_output: JsonOption = False) -> None:
    payload = init_home()
    if json_output:
        _echo_json(payload)
    else:
        typer.echo(dumps_json(payload))


@app.command("clean")
def clean_command(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be deleted.")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Delete non-secret runtime files.")] = False,
    include_secrets: Annotated[bool, typer.Option("--include-secrets", help="Also delete token-cache and browser-profile.")] = False,
    all_data: Annotated[bool, typer.Option("--all", help="Delete all runtime subdirectories including secrets.")] = False,
    json_output: JsonOption = False,
) -> None:
    payload = clean_home(dry_run=dry_run, yes=yes, include_secrets=include_secrets, all_data=all_data)
    exit_code = 1 if payload.get("status") == "error" else 0
    if json_output:
        _echo_json(payload, exit_code=exit_code)
    else:
        typer.echo(dumps_json(payload))
        if exit_code:
            raise typer.Exit(exit_code)


@app.command("uninstall")
def uninstall_command(
    yes: Annotated[bool, typer.Option("--yes", help="Confirm deleting SOURCING1688_HOME.")] = False,
    keep_browser_profile: Annotated[bool, typer.Option("--keep-browser-profile", help="Preserve browser profile directory.")] = False,
    keep_token_cache: Annotated[bool, typer.Option("--keep-token-cache", help="Preserve token cache directory.")] = False,
    json_output: JsonOption = False,
) -> None:
    payload = uninstall_home(yes=yes, keep_browser_profile=keep_browser_profile, keep_token_cache=keep_token_cache)
    exit_code = 1 if payload.get("status") == "error" else 0
    if json_output:
        _echo_json(payload, exit_code=exit_code)
    else:
        typer.echo(dumps_json(payload))
        if exit_code:
            raise typer.Exit(exit_code)


@app.command("install-codex")
def install_codex_command(
    open_chrome_setup: Annotated[
        bool,
        typer.Option("--open-chrome-setup/--no-open-chrome-setup", help="Open Chrome DevTools setup page after registering MCP servers."),
    ] = True,
    manual_windows_install: Annotated[
        bool,
        typer.Option("--manual-windows-install", help="Bypass Codex CLI marketplace commands and write Codex config/plugin cache directly."),
    ] = False,
    chrome_mode: Annotated[
        str,
        typer.Option("--chrome-mode", help="Chrome DevTools mode: default/auto uses the signed-in Chrome session; port uses a separate recovery profile."),
    ] = "default",
    verify: Annotated[bool, typer.Option("--verify", help="Run doctor checks after installation.")] = False,
    json_output: JsonOption = False,
) -> None:
    payload = install_codex(
        open_chrome_setup=open_chrome_setup,
        manual_windows_install=manual_windows_install,
        chrome_mode=chrome_mode,
        verify=verify,
    )
    exit_code = 1 if payload.get("status") == "error" else 0
    if json_output:
        _echo_json(payload, exit_code=exit_code)
    else:
        _echo_install_codex_summary(payload)
        if exit_code:
            raise typer.Exit(exit_code)


@app.command("doctor")
def doctor_command(json_output: JsonOption = False) -> None:
    payload = doctor()
    exit_code = 1 if payload.get("status") == "error" else 0
    if json_output:
        _echo_json(payload, exit_code=exit_code)
    else:
        for item in payload.get("checks", []):
            marker = "PASS" if item.get("status") == "pass" else "FAIL"
            typer.echo(f"{marker} {item.get('id')}: {item.get('message')}")
            if item.get("next_step"):
                typer.echo(f"  next: {item['next_step']}")
        if exit_code:
            raise typer.Exit(exit_code)


@app.command("uninstall-codex")
def uninstall_codex_command(
    remove_runtime: Annotated[bool, typer.Option("--remove-runtime", help="Also delete SOURCING1688_HOME runtime data.")] = False,
    json_output: JsonOption = False,
) -> None:
    payload = uninstall_codex(remove_runtime=remove_runtime)
    if json_output:
        _echo_json(payload)
    else:
        _echo_uninstall_codex_summary(payload, remove_runtime=remove_runtime)


@app.command("setup")
def setup_command(
    provider: Annotated[str, typer.Option("--provider", help="Provider to set up: api or browser.")] = "api",
    json_output: JsonOption = False,
) -> None:
    init = init_home()
    selected = provider.lower()
    if selected == "api":
        payload = {
            "status": "ok",
            "provider": "api",
            "home": init["home"],
            "auth_status": auth_status(),
            "next_steps": [
                "Set ALI1688_APP_KEY and ALI1688_APP_SECRET.",
                "Run `sourcing1688 auth url --redirect-uri ... --json`.",
                "Run `sourcing1688 auth exchange --code CODE --redirect-uri ... --json`.",
                "Run `sourcing1688 provider-check --provider api --json`.",
            ],
            "provider_check": check_provider("api"),
        }
    elif selected == "browser":
        paths = runtime_paths()
        payload = {
            "status": "ok",
            "provider": "browser",
            "home": init["home"],
            "browser_profile": str(paths["browser_profile"]),
            "next_steps": [
                "Run `sourcing1688 browser-profile open --json` and complete login/verification manually.",
                "Run `sourcing1688 browser-profile check --json`.",
                "Run `sourcing1688 provider-check --provider browser --json`.",
            ],
            "provider_check": check_provider("browser"),
        }
    else:
        payload = error_payload("unsupported_provider", "setup currently supports provider=api or provider=browser.", status="provider_unavailable")
    if json_output:
        _echo_json(payload, exit_code=1 if payload.get("status") == "provider_unavailable" else 0)
    else:
        typer.echo(dumps_json(payload))


@app.command("expand-keywords")
def expand_keywords_command(keyword: str, json_output: JsonOption = False) -> None:
    result = expand_keywords(keyword)
    if json_output:
        _echo_json(result)
    else:
        typer.echo("\n".join(result.keywords))


@app.command("search")
def search_command(
    keyword: str,
    top: Annotated[int, typer.Option("--top", min=1, max=100)] = 30,
    provider: ProviderOption = None,
    json_output: JsonOption = False,
) -> None:
    try:
        result = anyio.run(partial(search_sourcing_products, keyword, top=top, provider_name=provider))
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        for item in result.items:
            typer.echo(f"{item.offer_id}\t{item.title_zh}\t{item.price_min or ''}\t{item.url}")


@app.command("providers")
def providers_command(json_output: JsonOption = False) -> None:
    result = get_all_provider_capabilities()
    if json_output:
        _echo_json({"status": "ok", "providers": {key: value.model_dump(mode="json") for key, value in result.providers.items()}})
    else:
        for name, capability in result.providers.items():
            typer.echo(f"{name}\tsearch={capability.search}\tdetail={capability.detail}\tlive_verified={capability.live_verified}")


@app.command("provider-check")
def provider_check_command(
    provider: Annotated[str, typer.Option("--provider")],
    json_output: JsonOption = False,
) -> None:
    try:
        result = check_provider(provider)
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@app.command("analyze-url")
def analyze_url_command(
    url: str,
    provider: ProviderOption = None,
    json_output: JsonOption = False,
) -> None:
    try:
        result = anyio.run(partial(analyze_product_url, url, provider_name=provider))
    except ValueError as exc:
        if _is_offer_id_error(exc):
            _echo_json(error_payload("invalid_offer_id", str(exc)), exit_code=1)
        _handle_exception(exc, json_output=json_output)
        return
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@app.command("detail")
def detail_command(
    offer_id_or_url: str,
    provider: ProviderOption = None,
    json_output: JsonOption = False,
) -> None:
    try:
        result = anyio.run(partial(get_product_detail, offer_id_or_url, provider_name=provider))
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@app.command("download-assets")
def download_assets_command(
    offer_id_or_url: str,
    out: Annotated[Path | None, typer.Option("--out", help="Output directory.")] = None,
    include: Annotated[str | None, typer.Option("--include", help="Comma-separated include list.")] = None,
    provider: ProviderOption = None,
    zip_output: Annotated[bool, typer.Option("--zip", help="Create a zip package next to the saved asset directory.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Write manifest/html/attributes but do not download image or video URLs.")] = False,
    json_output: JsonOption = False,
) -> None:
    try:
        output_dir = out or get_settings().output_dir
        result = anyio.run(partial(download_product_assets, offer_id_or_url, output_dir, include=include, provider_name=provider, dry_run=dry_run))
        if zip_output:
            _zip_manifest_dir(result)
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@app.command("parse-html")
def parse_html_command(file: Path, json_output: JsonOption = False) -> None:
    try:
        result = parse_rendered_html_file(file)
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@app.command("download-assets-from-html")
def download_assets_from_html_command(
    file: Path,
    out: Annotated[Path | None, typer.Option("--out", help="Output directory.")] = None,
    include: Annotated[str | None, typer.Option("--include", help="Comma-separated include list.")] = None,
    zip_output: Annotated[bool, typer.Option("--zip", help="Create a zip package.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Write manifest/html/attributes but do not download image or video URLs.")] = False,
    json_output: JsonOption = False,
) -> None:
    from sourcing1688.assets.downloader import download_assets
    from sourcing1688.parsers.rendered_html import PARSER_VERSION

    try:
        parsed = parse_rendered_html_file(file)
        if parsed.item is None:
            _echo_json(parsed, exit_code=1)
            return
        manifest = anyio.run(
            partial(
                download_assets,
                parsed.item,
                out or get_settings().output_dir,
                include=include,
                html=file.read_text(encoding="utf-8"),
                source_url=parsed.item.url,
                raw_html_path=str(file),
                parser_version=PARSER_VERSION,
                zip_output=zip_output,
                dry_run=dry_run,
            )
        )
        result = {"status": manifest.status, "manifest": manifest.model_dump(mode="json"), "manifest_path": str(Path(manifest.saved_dir) / "manifest.json")}
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@app.command("hot-keywords")
def hot_keywords_command(
    category_id: Annotated[str | None, typer.Option("--category-id")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 20,
    provider: ProviderOption = None,
    json_output: JsonOption = False,
) -> None:
    try:
        selected = get_provider(provider)
        result = anyio.run(partial(selected.get_hot_keywords, category_id=category_id, limit=limit))
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        for item in result.items:
            typer.echo(f"{item.rank or ''}\t{item.keyword}\t{item.heat or ''}")


@app.command("rankings")
def rankings_command(
    category_id: Annotated[str | None, typer.Option("--category-id")] = None,
    rank_type: Annotated[str, typer.Option("--rank-type")] = "hot",
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 20,
    provider: ProviderOption = None,
    json_output: JsonOption = False,
) -> None:
    try:
        selected = get_provider(provider)
        result = anyio.run(partial(selected.get_rankings, category_id=category_id, rank_type=rank_type, limit=limit))
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        for item in result.items:
            typer.echo(f"{item.rank}\t{item.keyword or ''}\t{item.offer_id or ''}\t{item.title_zh or ''}")


@app.command("recommend")
def recommend_command(
    keyword: str,
    top: Annotated[int, typer.Option("--top", min=1, max=100)] = 10,
    save: Annotated[bool, typer.Option("--save", help="Save candidates and scores to storage.")] = False,
    project: Annotated[str | None, typer.Option("--project", help="Project name for saved candidates.")] = None,
    provider: ProviderOption = None,
    json_output: JsonOption = False,
) -> None:
    try:
        result = anyio.run(partial(recommend_products, keyword, top=top, save=save, provider_name=provider, project=project))
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        for item in result.items:
            typer.echo(f"{item.score.score:0.1f}\t{item.product.offer_id}\t{item.product.title_zh}")


@app.command("image-search")
def image_search_command(
    image_url: Annotated[str | None, typer.Option("--image-url")] = None,
    image_path: Annotated[Path | None, typer.Option("--image-path")] = None,
    top: Annotated[int, typer.Option("--top", min=1, max=100)] = 20,
    provider: ProviderOption = None,
    json_output: JsonOption = False,
) -> None:
    try:
        result = anyio.run(partial(image_search_products, image_url=image_url, image_path=str(image_path) if image_path else None, top=top, provider_name=provider))
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output)
        return
    if json_output:
        _echo_json(result)
    else:
        for item in result.items:
            typer.echo(f"{item.offer_id}\t{item.title_zh}\t{item.url}")


@browser_profile_app.command("init")
def browser_profile_init_command(
    path: Annotated[Path | None, typer.Option("--path")] = None,
    json_output: JsonOption = False,
) -> None:
    if path is None:
        path = runtime_paths()["browser_profile"]
    path.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "ok",
        "profile_path": str(path),
        "message": "Browser profile directory created.",
        "suggested_action": "Run `sourcing1688 browser-profile open --json`, log in to 1688 manually, close the browser, then use provider=auto or provider=browser.",
    }
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@browser_profile_app.command("check")
def browser_profile_check_command(
    live: Annotated[bool, typer.Option("--live", help="Open 1688 with the profile and detect login/verification pages.")] = False,
    json_output: JsonOption = False,
) -> None:
    provider = get_provider("browser")
    result = anyio.run(partial(provider.check_profile, live=live)) if hasattr(provider, "check_profile") else {"status": "provider_unavailable"}
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@browser_profile_app.command("open")
def browser_profile_open_command(
    path: Annotated[Path | None, typer.Option("--path")] = None,
    url: Annotated[str, typer.Option("--url")] = "https://www.1688.com",
    json_output: JsonOption = False,
) -> None:
    selected_path = path or runtime_paths()["browser_profile"]
    try:
        result = anyio.run(partial(open_browser_profile, selected_path, url))
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc, json_output=json_output, code="browser_profile_open_failed")
        return
    if json_output:
        _echo_json(result)
    else:
        typer.echo(dumps_json(result))


@chrome_devtools_app.command("start")
def chrome_devtools_start_command(
    port: Annotated[int, typer.Option("--port", help="Remote debugging port.")] = 9222,
    url: Annotated[str, typer.Option("--url", help="Initial URL to open in the separate recovery Chrome profile.")] = "https://www.1688.com/",
    json_output: JsonOption = False,
) -> None:
    payload = start_chrome_devtools_port(port=port, url=url)
    exit_code = 0 if payload.get("status") == "ok" else 1
    if json_output:
        _echo_json(payload, exit_code=exit_code)
    else:
        typer.echo(dumps_json(payload))
        if exit_code:
            raise typer.Exit(exit_code)


@auth_app.command("status")
def auth_status_command(json_output: JsonOption = False) -> None:
    payload = auth_status()
    if json_output:
        _echo_json(payload)
    else:
        typer.echo(dumps_json(payload))


@auth_app.command("url")
def auth_url_command(
    redirect_uri: Annotated[str, typer.Option("--redirect-uri")],
    json_output: JsonOption = False,
) -> None:
    payload = build_authorization_url(redirect_uri)
    if json_output:
        _echo_json(payload, exit_code=1 if payload.get("status") == "missing_credentials" else 0)
    else:
        typer.echo(dumps_json(payload))


@auth_app.command("exchange")
def auth_exchange_command(
    code: Annotated[str, typer.Option("--code")],
    redirect_uri: Annotated[str, typer.Option("--redirect-uri")],
    json_output: JsonOption = False,
) -> None:
    try:
        payload = anyio.run(partial(exchange_code_for_token, code, redirect_uri))
    except Exception as exc:  # noqa: BLE001
        payload = error_payload("token_exchange_failed", str(exc), status="provider_unavailable")
    if json_output:
        _echo_json(payload, exit_code=1 if payload.get("status") not in {"ok"} else 0)
    else:
        typer.echo(dumps_json(payload))


@auth_app.command("clear")
def auth_clear_command(
    yes: Annotated[bool, typer.Option("--yes", help="Confirm token-cache deletion.")] = False,
    json_output: JsonOption = False,
) -> None:
    if not yes:
        payload = error_payload("confirmation_required", "Pass --yes to delete the token cache.")
        if json_output:
            _echo_json(payload, exit_code=1)
            return
        typer.echo(dumps_json(payload))
        raise typer.Exit(1)
    payload = clear_token_cache()
    if json_output:
        _echo_json(payload)
    else:
        typer.echo(dumps_json(payload))


@live_smoke_app.command("search")
def live_smoke_search_command(
    keyword: str,
    provider: ProviderOption = "browser",
    top: Annotated[int, typer.Option("--top", min=1, max=10)] = 3,
    json_output: JsonOption = False,
) -> None:
    settings = get_settings()
    if not settings.live_smoke:
        payload = error_payload("live_smoke_disabled", "Set SOURCING1688_LIVE_SMOKE=true to run live smoke commands.", status="live_not_verified")
        if json_output:
            _echo_json(payload, exit_code=1)
            return
    search_command(keyword, top=top, provider=provider, json_output=json_output)


@live_smoke_app.command("detail")
def live_smoke_detail_command(
    offer_id_or_url: str,
    provider: ProviderOption = "browser",
    json_output: JsonOption = False,
) -> None:
    settings = get_settings()
    if not settings.live_smoke:
        payload = error_payload("live_smoke_disabled", "Set SOURCING1688_LIVE_SMOKE=true to run live smoke commands.", status="live_not_verified")
        if json_output:
            _echo_json(payload, exit_code=1)
            return
    detail_command(offer_id_or_url, provider=provider, json_output=json_output)


@shortlist_app.command("add")
def shortlist_add_command(
    project: Annotated[str, typer.Option("--project")],
    offer_id: Annotated[str, typer.Option("--offer-id")],
    notes: Annotated[str | None, typer.Option("--notes")] = None,
    json_output: JsonOption = False,
) -> None:
    storage = SourcingStorage(get_settings().db_path)
    storage.add_to_shortlist(project, offer_id, notes)
    storage.close()
    payload = {"status": "ok", "project": project, "offer_id": offer_id}
    if json_output:
        _echo_json(payload)
    else:
        typer.echo(f"Added {offer_id} to {project}.")


@shortlist_app.command("export")
def shortlist_export_command(
    project: Annotated[str, typer.Option("--project")],
    format: Annotated[str, typer.Option("--format")] = "json",
    json_output: JsonOption = False,
) -> None:
    storage = SourcingStorage(get_settings().db_path)
    payload = storage.export_project(project, format)
    storage.close()
    if json_output:
        _echo_json(payload)
    else:
        if "content" in payload:
            typer.echo(payload["content"])
        else:
            typer.echo(dumps_json(payload))


def main() -> None:
    try:
        app()
    except Exception as exc:  # pragma: no cover - Typer handles most command errors.
        typer.echo(dumps_json(error_payload("unhandled_error", str(exc))), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
