from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from sourcing1688.config import Settings, get_settings


RUNTIME_DIRS = ["config", "data", "assets", "raw", "browser-profile", "token-cache", "logs"]
CLEAN_DIRS = ["assets", "raw", "logs"]
SECRET_DIRS = ["token-cache", "browser-profile"]


def runtime_paths(settings: Settings | None = None) -> dict[str, Path]:
    settings = settings or get_settings()
    home = settings.home
    return {
        "home": home,
        "config": home / "config",
        "config_json": home / "config" / "config.json",
        "env_local": home / "config" / ".env.local",
        "data": home / "data",
        "db": settings.db_path,
        "assets": settings.output_dir,
        "raw": home / "raw",
        "browser_profile": Path(settings.browser_profile or home / "browser-profile"),
        "token_cache": settings.ali1688_token_cache_path,
        "token_cache_dir": settings.ali1688_token_cache_path.parent,
        "logs": home / "logs",
    }


def home_payload(settings: Settings | None = None) -> dict[str, Any]:
    paths = runtime_paths(settings)
    home = paths["home"]
    return {
        "status": "ok",
        "home": str(home),
        "exists": home.exists(),
        "paths": {key: str(value) for key, value in paths.items() if key != "home"},
    }


def init_home(settings: Settings | None = None) -> dict[str, Any]:
    paths = runtime_paths(settings)
    for name in RUNTIME_DIRS:
        (paths["home"] / name).mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "home": str(paths["home"]), "created": [str(paths["home"] / name) for name in RUNTIME_DIRS], "paths": {key: str(value) for key, value in paths.items() if key != "home"}}


def _children_for_delete(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.is_file():
        return [str(path)]
    return [str(child) for child in path.iterdir()]


def clean_home(*, dry_run: bool, yes: bool, include_secrets: bool = False, all_data: bool = False, settings: Settings | None = None) -> dict[str, Any]:
    paths = runtime_paths(settings)
    names = list(CLEAN_DIRS)
    if include_secrets or all_data:
        names.extend(SECRET_DIRS)
    targets = [paths["home"] / name for name in names]
    would_delete = [item for target in targets for item in _children_for_delete(target)]
    if dry_run:
        return {"status": "dry_run", "home": str(paths["home"]), "would_delete": would_delete, "preserved": [str(paths["home"] / name) for name in SECRET_DIRS if name not in names]}
    if not yes:
        return {"status": "error", "message": "Pass --yes to clean runtime files.", "error": {"code": "confirmation_required", "message": "Pass --yes to clean runtime files.", "needs_human_action": False, "suggested_action": "Re-run with --yes after reviewing --dry-run.", "details": {}}}
    deleted: list[str] = []
    for target in targets:
        if not target.exists():
            continue
        for child in list(target.iterdir()) if target.is_dir() else [target]:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
            deleted.append(str(child))
    return {"status": "ok", "home": str(paths["home"]), "deleted": deleted}


def uninstall_home(*, yes: bool, keep_browser_profile: bool = False, keep_token_cache: bool = False, settings: Settings | None = None) -> dict[str, Any]:
    paths = runtime_paths(settings)
    home = paths["home"]
    if not yes:
        return {"status": "error", "message": "Pass --yes to uninstall sourcing1688 runtime state.", "error": {"code": "confirmation_required", "message": "Pass --yes to uninstall sourcing1688 runtime state.", "needs_human_action": False, "suggested_action": "Re-run with --yes after backing up anything important.", "details": {}}}
    kept = []
    if keep_browser_profile and paths["browser_profile"].exists():
        kept.append(str(paths["browser_profile"]))
    if keep_token_cache and paths["token_cache_dir"].exists():
        kept.append(str(paths["token_cache_dir"]))
    if not home.exists():
        return {"status": "ok", "home": str(home), "deleted": False, "kept": kept}
    if keep_browser_profile or keep_token_cache:
        for child in list(home.iterdir()):
            if keep_browser_profile and child == paths["browser_profile"]:
                continue
            if keep_token_cache and child == paths["token_cache_dir"]:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        return {"status": "ok", "home": str(home), "deleted": True, "kept": kept}
    shutil.rmtree(home)
    return {"status": "ok", "home": str(home), "deleted": True, "kept": kept}
