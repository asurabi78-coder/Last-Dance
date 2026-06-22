from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from sourcing1688.assets.manifest import write_manifest
from sourcing1688.models import AssetManifest, FailedAsset, PlannedAsset, ProductDetail, SavedAsset
from sourcing1688.utils import sanitize_filename, slugify


DEFAULT_INCLUDE = {"html", "main_images", "detail_images", "option_images", "video", "attributes"}
INCLUDE_ALIASES = {"videos": "video", "main": "main_images", "detail": "detail_images", "options": "option_images"}


def parse_include(include: str | set[str] | list[str] | None) -> set[str]:
    if include is None:
        return set(DEFAULT_INCLUDE)
    if isinstance(include, str):
        items = [item.strip() for item in include.split(",") if item.strip()]
    else:
        items = [str(item).strip() for item in include if str(item).strip()]
    return {INCLUDE_ALIASES.get(item, item) for item in items}


def _extension_from_url(url: str, default: str = ".bin") -> str:
    suffix = Path(urlparse(url).path).suffix
    if suffix and len(suffix) <= 8:
        return suffix
    return default


async def _download_url(
    client: httpx.AsyncClient,
    url: str,
    target_dir: Path,
    offer_id: str,
    asset_type: str,
    index: int,
    min_bytes: int = 1,
    retries: int = 2,
) -> SavedAsset | FailedAsset:
    extension = _extension_from_url(url, ".mp4" if asset_type == "video" else ".jpg")
    filename = sanitize_filename(f"{offer_id}-{asset_type}-{index:03d}{extension}")
    target = target_dir / filename
    try:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                content = response.content
                if len(content) < min_bytes:
                    raise ValueError(f"Downloaded file too small: {len(content)} bytes")
                content_type = response.headers.get("content-type", "")
                extension = _extension_from_url(url, ".mp4" if "video" in content_type or asset_type == "video" else ".jpg")
                target = target.with_suffix(extension)
                target.write_bytes(content)
                return SavedAsset(url=url, path=str(target))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < retries:
                    await _sleep_backoff(attempt)
        raise last_error or RuntimeError("download failed")
    except Exception as exc:  # noqa: BLE001 - record failures without killing the batch.
        return FailedAsset(url=url, reason=str(exc), asset_type=asset_type)


async def _sleep_backoff(attempt: int) -> None:
    import anyio

    await anyio.sleep(min(1.5, 0.25 * (attempt + 1)))


async def download_assets(
    detail: ProductDetail,
    output_dir: str | Path,
    *,
    include: str | set[str] | list[str] | None = None,
    client: httpx.AsyncClient | None = None,
    html: str | None = None,
    source_url: str | None = None,
    raw_html_path: str | None = None,
    parser_version: str | None = None,
    zip_output: bool = False,
    dry_run: bool = False,
    user_agent: str = "Mozilla/5.0 sourcing1688/0.2",
    referer: str | None = None,
) -> AssetManifest:
    include_set = parse_include(include)
    slug = slugify(detail.title_zh, fallback=detail.offer_id)
    saved_dir = Path(output_dir) / f"{detail.offer_id}-{slug}"
    saved_dir.mkdir(parents=True, exist_ok=True)

    manifest = AssetManifest(
        offer_id=detail.offer_id,
        saved_dir=str(saved_dir),
        downloaded_at=datetime.now(timezone.utc),
        source_url=source_url or detail.url,
        raw_html_path=raw_html_path,
        parser_version=parser_version,
    )

    if "html" in include_set and html is not None:
        html_path = saved_dir / f"{detail.offer_id}-page.html"
        html_path.write_text(html, encoding="utf-8")
        manifest.html_path = str(html_path)

    if "attributes" in include_set:
        attr_path = saved_dir / f"{detail.offer_id}-attributes.json"
        attr_path.write_text(json.dumps(detail.attributes, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.attributes_json = str(attr_path)

    seen: set[str] = set()
    own_client = client is None
    if client is None and not dry_run:
        headers = {"user-agent": user_agent}
        if referer or detail.url:
            headers["referer"] = referer or detail.url
        client = httpx.AsyncClient(timeout=20, headers=headers)

    try:
        asset_groups = [
            ("main_images", "main_image", detail.main_image_urls, manifest.main_images),
            ("detail_images", "detail_image", detail.detail_image_urls, manifest.detail_images),
            ("option_images", "option_image", detail.option_image_urls, manifest.option_images),
            ("video", "video", detail.video_urls, manifest.videos),
        ]
        for include_name, asset_type, urls, destination in asset_groups:
            if include_name not in include_set:
                continue
            index = 1
            for url in urls:
                if url in seen:
                    continue
                seen.add(url)
                if dry_run:
                    manifest.dry_run_assets.append(PlannedAsset(url=url, asset_type=asset_type))
                    index += 1
                    continue
                if client is None:
                    manifest.failed_assets.append(FailedAsset(url=url, reason="HTTP client unavailable", asset_type=asset_type))
                    index += 1
                    continue
                result = await _download_url(client, url, saved_dir, detail.offer_id, asset_type, index)
                index += 1
                if isinstance(result, SavedAsset):
                    destination.append(result)
                else:
                    manifest.failed_assets.append(result)
    finally:
        if own_client and client is not None:
            await client.aclose()

    if dry_run:
        manifest.status = "dry_run"
    elif manifest.failed_assets:
        manifest.status = "partial_success"
    manifest.counts = {
        "main_images": len(manifest.main_images),
        "detail_images": len(manifest.detail_images),
        "option_images": len(manifest.option_images),
        "videos": len(manifest.videos),
        "dry_run_assets": len(manifest.dry_run_assets),
        "failed_assets": len(manifest.failed_assets),
    }
    if zip_output:
        zip_path = saved_dir.with_suffix(".zip")
        manifest.zip_path = str(zip_path)
        write_manifest(manifest)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in saved_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(saved_dir.parent))
    else:
        write_manifest(manifest)
    return manifest
