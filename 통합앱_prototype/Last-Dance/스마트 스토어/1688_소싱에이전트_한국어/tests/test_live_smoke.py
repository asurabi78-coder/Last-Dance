import os

import pytest


@pytest.mark.live
def test_live_smoke_is_opt_in():
    if os.getenv("SOURCING1688_LIVE_SMOKE", "false").lower() not in {"1", "true", "yes"}:
        pytest.skip("Live 1688 smoke tests are disabled by default.")

    assert os.getenv("SOURCING1688_LIVE_SMOKE")
