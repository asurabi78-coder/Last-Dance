from sourcing1688.config import get_settings


def test_browser_provider_defaults_to_visible_for_1688_login_compatibility(monkeypatch):
    monkeypatch.delenv("SOURCING1688_BROWSER_HEADLESS", raising=False)

    assert get_settings().browser_headless is False


def test_browser_headless_can_be_enabled_when_user_accepts_login_risk(monkeypatch):
    monkeypatch.setenv("SOURCING1688_BROWSER_HEADLESS", "true")

    assert get_settings().browser_headless is True
