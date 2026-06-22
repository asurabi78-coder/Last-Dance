from __future__ import annotations

import json
from pathlib import Path

from sourcing1688.models import AssetManifest


def write_manifest(manifest: AssetManifest) -> Path:
    path = Path(manifest.saved_dir) / "manifest.json"
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_manifest(path: Path) -> AssetManifest:
    return AssetManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))

