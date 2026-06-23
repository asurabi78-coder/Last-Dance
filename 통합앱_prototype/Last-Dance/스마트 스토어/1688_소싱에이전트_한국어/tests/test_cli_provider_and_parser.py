import json
import os
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from sourcing1688.cli import app


runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"


def test_providers_cli_json_lists_capabilities():
    result = runner.invoke(app, ["providers", "--json"])
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["status"] == "ok"
    assert {"auto", "api", "browser", "local_html"}.issubset(payload["providers"])
    assert "mock" not in payload["providers"]


def test_provider_check_auto_json(tmp_path):
    result = runner.invoke(app, ["provider-check", "--provider", "auto", "--json"], env={"SOURCING1688_HOME": str(tmp_path)})
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["provider"] == "auto"
    assert payload["live_verified"] is False
    assert payload["capabilities"]["search"] is True


def test_parse_html_cli_json():
    result = runner.invoke(app, ["parse-html", str(FIXTURES / "singlefile_detail_sample.html"), "--json"])
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["status"] == "partial_data"
    assert payload["item"]["offer_id"] == "123456789"


def test_parse_html_cli_non_json_forces_utf8_when_parent_encoding_is_cp949():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp949"
    result = subprocess.run(
        [sys.executable, "-m", "sourcing1688.cli", "parse-html", str(FIXTURES / "product_detail_sample.html")],
        cwd=Path(__file__).parents[1],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert "黑胶防晒晴雨伞" in result.stdout.decode("utf-8")


def test_download_assets_from_html_cli_json(tmp_path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run must not attempt network downloads")

    monkeypatch.setattr("sourcing1688.assets.downloader._download_url", fail_if_called)
    result = runner.invoke(
        app,
        ["download-assets-from-html", str(FIXTURES / "singlefile_detail_sample.html"), "--out", str(tmp_path), "--dry-run", "--json"],
    )
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["status"] == "dry_run"
    assert payload["manifest_path"]
    assert payload["manifest"]["dry_run_assets"]


def test_download_assets_from_html_default_out_uses_home_assets(tmp_path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run must not attempt network downloads")

    monkeypatch.setattr("sourcing1688.assets.downloader._download_url", fail_if_called)
    result = runner.invoke(
        app,
        ["download-assets-from-html", str(FIXTURES / "singlefile_detail_sample.html"), "--dry-run", "--json"],
        env={"SOURCING1688_HOME": str(tmp_path)},
    )
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["status"] == "dry_run"
    assert Path(payload["manifest"]["saved_dir"]).is_relative_to(tmp_path / "assets")


def test_download_assets_cli_dry_run_json(tmp_path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run must not attempt network downloads")

    monkeypatch.setattr("sourcing1688.assets.downloader._download_url", fail_if_called)
    result = runner.invoke(
        app,
        ["download-assets", str(FIXTURES / "singlefile_detail_sample.html"), "--provider", "local_html", "--out", str(tmp_path), "--dry-run", "--json"],
    )
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["status"] == "dry_run"
    assert payload["manifest"]["dry_run_assets"]


def test_download_assets_default_out_uses_home_assets(tmp_path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run must not attempt network downloads")

    monkeypatch.setattr("sourcing1688.assets.downloader._download_url", fail_if_called)
    result = runner.invoke(
        app,
        ["download-assets", str(FIXTURES / "singlefile_detail_sample.html"), "--provider", "local_html", "--dry-run", "--json"],
        env={"SOURCING1688_HOME": str(tmp_path)},
    )
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["status"] == "dry_run"
    assert Path(payload["manifest"]["saved_dir"]).is_relative_to(tmp_path / "assets")


def test_image_search_api_without_credentials_json(monkeypatch):
    for key in ["ALI1688_APP_KEY", "ALI1688_APP_SECRET", "ALI1688_REFRESH_TOKEN", "ALI1688_ACCESS_TOKEN"]:
        monkeypatch.delenv(key, raising=False)
    result = runner.invoke(app, ["image-search", "--image-url", "https://cbu01.alicdn.com/img/ibank/O1CN.jpg", "--provider", "api", "--json"])
    payload = json.loads(result.output)

    assert result.exit_code == 0
    assert payload["status"] == "missing_credentials"
    assert payload["error"]["code"] == "missing_credentials"
