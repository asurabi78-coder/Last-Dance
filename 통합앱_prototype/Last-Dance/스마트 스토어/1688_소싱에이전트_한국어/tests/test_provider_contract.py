import pytest

from sourcing1688.providers.api_provider import Api1688Provider
from sourcing1688.providers.base import Base1688Provider
from sourcing1688.providers.browser_provider import Browser1688Provider


def test_live_providers_implement_base_contract():
    api = Api1688Provider()
    browser = Browser1688Provider()

    assert isinstance(api, Base1688Provider)
    assert isinstance(browser, Base1688Provider)


@pytest.mark.anyio
async def test_api_provider_without_credentials_returns_missing_credentials(monkeypatch):
    monkeypatch.delenv("ALI1688_APP_KEY", raising=False)
    monkeypatch.delenv("ALI1688_APP_SECRET", raising=False)
    monkeypatch.delenv("ALI1688_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("ALI1688_ACCESS_TOKEN", raising=False)
    provider = Api1688Provider()

    result = await provider.search_products("黑胶伞")

    assert result.status == "missing_credentials"
    assert result.error is not None
    assert result.error.code == "missing_credentials"
    assert result.needs_human_action is False


@pytest.mark.anyio
async def test_browser_provider_without_profile_returns_needs_human_login(monkeypatch, tmp_path):
    monkeypatch.delenv("SOURCING1688_BROWSER_PROFILE", raising=False)
    monkeypatch.setenv("SOURCING1688_HOME", str(tmp_path / "missing-home"))
    provider = Browser1688Provider()

    result = await provider.search_products("黑胶伞")

    assert result.status == "needs_human_login"
    assert result.error is not None
    assert result.error.code == "needs_human_login"
    assert result.needs_human_action is True
