from bs4 import BeautifulSoup

from sourcing1688.parsers.asset_extractor import extract_assets, extract_urls_from_text, normalize_url


def test_extract_urls_skips_xpath_like_invalid_url_candidates():
    text = """
    const bad = "https://*[@id=";
    const image = "https://cbu01.alicdn.com/img/ibank/O1CN-valid.jpg";
    const video = "https://cloud.video.taobao.com/play/u/1/p/1/e/6/t/1/valid.mp4";
    """

    images, videos = extract_urls_from_text(text)

    assert images == ["https://cbu01.alicdn.com/img/ibank/O1CN-valid.jpg"]
    assert videos == ["https://cloud.video.taobao.com/play/u/1/p/1/e/6/t/1/valid.mp4"]


def test_normalize_url_rejects_malformed_netloc_without_raising():
    assert normalize_url("https://*[@id=") is None
    assert normalize_url("https://[bad") is None


def test_extract_assets_does_not_crash_on_malformed_script_url():
    html = """
    <html>
      <body>
        <img src="//cbu01.alicdn.com/img/ibank/O1CN-main.jpg">
        <script>
          window.xpath = "https://*[@id=";
          window.video = "https://cloud.video.taobao.com/play/u/1/p/1/e/6/t/1/valid.mp4";
        </script>
      </body>
    </html>
    """

    assets = extract_assets(BeautifulSoup(html, "html.parser"), html)

    assert assets["main_images"] == ["https://cbu01.alicdn.com/img/ibank/O1CN-main.jpg"]
    assert assets["videos"] == ["https://cloud.video.taobao.com/play/u/1/p/1/e/6/t/1/valid.mp4"]


def test_extract_urls_ignores_scripts_fonts_and_root_hosts():
    text = """
    https://g.alicdn.com/upkg-solution/detail/0.1.14/index.js
    https://at.alicdn.com/t/a/font.woff2
    https://cbu01.alicdn.com/
    https://cbu01.alicdn.com/img/ibank/O1CN-real.jpg
    """

    images, videos = extract_urls_from_text(text)

    assert images == ["https://cbu01.alicdn.com/img/ibank/O1CN-real.jpg"]
    assert videos == []


def test_extract_assets_accepts_live_lazy_sources_and_video_poster():
    html = """
    <html>
      <body>
        <img data-lazy-src="//cbu01.alicdn.com/img/ibank/O1CN-lazy.jpg">
        <img data-img="https://cbu01.alicdn.com/img/ibank/O1CN-data-img.jpg">
        <img srcset="https://cbu01.alicdn.com/img/ibank/O1CN-srcset.jpg 1x, https://cbu01.alicdn.com/img/ibank/O1CN-srcset-2x.jpg 2x">
        <video poster="https://cbu01.alicdn.com/img/ibank/O1CN-poster.jpg">
          <source src="https://cloud.video.taobao.com/play/u/1/p/1/e/6/t/1/video.mp4">
        </video>
      </body>
    </html>
    """

    assets = extract_assets(BeautifulSoup(html, "html.parser"), html)

    assert "https://cbu01.alicdn.com/img/ibank/O1CN-lazy.jpg" in assets["main_images"]
    assert "https://cbu01.alicdn.com/img/ibank/O1CN-data-img.jpg" in assets["main_images"]
    assert "https://cbu01.alicdn.com/img/ibank/O1CN-srcset.jpg" in assets["main_images"]
    assert "https://cbu01.alicdn.com/img/ibank/O1CN-poster.jpg" in assets["main_images"]
    assert assets["videos"] == ["https://cloud.video.taobao.com/play/u/1/p/1/e/6/t/1/video.mp4"]
