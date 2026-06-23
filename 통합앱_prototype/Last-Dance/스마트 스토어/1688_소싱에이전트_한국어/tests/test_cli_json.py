import json

from typer.testing import CliRunner

from sourcing1688.cli import app


runner = CliRunner()


def parse_json_output(result):
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_cli_expand_keywords_json():
    keyword = "\uc554\ub9c9\uc6b0\uc0b0"
    result = runner.invoke(app, ["expand-keywords", keyword, "--json"])
    payload = parse_json_output(result)

    assert payload["status"] == "ok"
    assert "\u9ed1\u80f6\u4f1e" in payload["keywords"]
    assert "\\u9ed1" not in result.output
    assert keyword in result.output


def test_cli_search_json_with_auto_provider_does_not_launch_browser(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCING1688_PROVIDER", "auto")
    monkeypatch.setenv("SOURCING1688_HOME", str(tmp_path / "missing-home"))
    result = runner.invoke(app, ["search", "\uc554\ub9c9\uc6b0\uc0b0", "--top", "1", "--json"])
    payload = parse_json_output(result)

    assert payload["status"] == "provider_unavailable"
    assert payload["error"]["code"] == "chrome_devtools_required"
    assert payload["items"] == []


def test_cli_search_unknown_korean_keyword_includes_expansion_workflow(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCING1688_PROVIDER", "auto")
    monkeypatch.setenv("SOURCING1688_HOME", str(tmp_path / "missing-home"))
    result = runner.invoke(app, ["search", "\uc720\uc544\uc6a9 \ubb3c\ubcd1", "--json"])
    payload = parse_json_output(result)

    assert payload["status"] == "partial_data"
    assert payload["keyword_expansion"]["strategy"] == "agent_generate_terms"
    assert payload["keyword_expansion"]["search_workflow"]
    assert payload["expanded_keywords"] == []


def test_cli_failure_is_valid_json():
    result = runner.invoke(app, ["analyze-url", "not-a-valid-offer", "--json"])
    payload = json.loads(result.output)

    assert result.exit_code != 0
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_offer_id"


def test_cli_unknown_provider_json_failure_is_valid_json():
    result = runner.invoke(app, ["search", "\uc554\ub9c9\uc6b0\uc0b0", "--provider", "nope", "--json"])
    payload = json.loads(result.output)

    assert result.exit_code != 0
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "unknown_provider"
