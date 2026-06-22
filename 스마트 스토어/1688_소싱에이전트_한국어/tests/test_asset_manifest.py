import json
import zipfile

import httpx
import pytest

from sourcing1688.assets.downloader import download_assets
from sourcing1688.models import ProductDetail


@pytest.mark.anyio
async def test_download_assets_writes_manifest_and_records_failures(tmp_path):
    detail = ProductDetail(
        offer_id="123456789",
        url="https://detail.1688.com/offer/123456789.html",
        title_zh="黑胶防晒晴雨伞 三折遮阳伞",
        main_image_urls=[
            "https://assets.example.com/main.jpg",
            "https://assets.example.com/main.jpg",
        ],
        detail_image_urls=["https://assets.example.com/detail.jpg"],
        video_urls=["https://assets.example.com/missing.mp4"],
        attributes={"材质": "碰击布"},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("missing.mp4"):
            return httpx.Response(404)
        return httpx.Response(200, content=b"asset-bytes")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        manifest = await download_assets(
            detail,
            tmp_path,
            include={"main_images", "detail_images", "video", "attributes", "html"},
            client=client,
            html="<html></html>",
        )

    assert manifest.status == "partial_success"
    assert len(manifest.main_images) == 1
    assert len(manifest.detail_images) == 1
    assert len(manifest.failed_assets) == 1
    manifest_json = tmp_path / "123456789-hei-jiao-fang-shai-qing-yu-san-san-zhe-zhe-yang-san" / "manifest.json"
    assert manifest_json.exists()
    parsed = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert parsed["offer_id"] == "123456789"


@pytest.mark.anyio
async def test_zip_package_includes_manifest_json(tmp_path):
    detail = ProductDetail(
        offer_id="123456789",
        url="https://detail.1688.com/offer/123456789.html",
        title_zh="黑胶防晒晴雨伞 三折遮阳伞",
        attributes={"材质": "碰击布"},
    )

    manifest = await download_assets(
        detail,
        tmp_path,
        include={"attributes", "html"},
        html="<html></html>",
        zip_output=True,
    )

    assert manifest.zip_path
    with zipfile.ZipFile(manifest.zip_path) as archive:
        names = archive.namelist()
    assert any(name.endswith("manifest.json") for name in names)


@pytest.mark.anyio
async def test_download_assets_accepts_videos_include_alias(tmp_path):
    detail = ProductDetail(
        offer_id="123456789",
        url="https://detail.1688.com/offer/123456789.html",
        title_zh="旅行收纳袋",
        video_urls=["https://cloud.video.taobao.com/play/u/1/p/2/e/6/t/1/example.mp4"],
    )

    manifest = await download_assets(detail, tmp_path, include={"videos"}, dry_run=True)

    assert manifest.status == "dry_run"
    assert len(manifest.dry_run_assets) == 1
    assert manifest.dry_run_assets[0].asset_type == "video"
