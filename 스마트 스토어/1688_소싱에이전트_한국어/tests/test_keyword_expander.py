from sourcing1688.keyword_expander import expand_keywords


def test_expands_korean_blackout_umbrella_to_chinese_sourcing_terms():
    result = expand_keywords("\uc554\ub9c9\uc6b0\uc0b0")

    assert result.status == "ok"
    assert "\u9ed1\u80f6\u4f1e" in result.keywords
    assert "\u9632\u6652\u4f1e" in result.keywords
    assert result.needs_review is True
    assert result.strategy == "curated_seed_terms"
    assert result.agent_instruction


def test_expands_requested_commerce_terms_without_placeholder():
    examples = {
        "\uc6d4\ub4dc\ucef5 \ucd95\uad6c \uc720\ub2c8\ud3fc": ["\u4e16\u754c\u676f\u7403\u8863", "\u8db3\u7403\u670d", "\u56fd\u5bb6\u961f\u7403\u8863", "2026\u4e16\u754c\u676f\u7403\u8863", "\u8db3\u7403\u8bad\u7ec3\u670d"],
        "\uc6b4\ub3d9 \uc591\ub9d0": ["\u8fd0\u52a8\u889c", "\u8dd1\u6b65\u889c", "\u6bdb\u5dfe\u5e95\u889c", "\u4e2d\u7b52\u8fd0\u52a8\u889c"],
        "\ub0a8\uc131 \ubca8\ud2b8": ["\u7537\u58eb\u76ae\u5e26", "\u81ea\u52a8\u6263\u76ae\u5e26", "\u8170\u5e26", "\u5546\u52a1\u76ae\u5e26"],
        "\ud06c\ub77c\ud504\ud2b8 \ud3ec\uc7a5\ubd09\ud22c": ["\u725b\u76ae\u7eb8\u888b", "\u5916\u5356\u5305\u88c5\u888b", "\u98df\u54c1\u5305\u88c5\u888b", "\u624b\u63d0\u725b\u76ae\u7eb8\u888b"],
        "\ub7ec\ub2dd\ud654": ["\u8dd1\u6b65\u978b", "\u8fd0\u52a8\u978b", "\u900f\u6c14\u8dd1\u978b", "\u4f11\u95f2\u8fd0\u52a8\u978b"],
        "\ub0a8\uc131 \uc18d\uc637": ["\u7537\u58eb\u5185\u88e4", "\u5e73\u89d2\u88e4", "\u7eaf\u68c9\u7537\u5185\u88e4", "\u7537\u58eb\u56db\u89d2\u88e4"],
        "\uc2a4\ub9c8\ud2b8\ud3f0 \uac70\uce58\ub300": ["\u624b\u673a\u652f\u67b6", "\u8f66\u8f7d\u624b\u673a\u652f\u67b6", "\u684c\u9762\u624b\u673a\u652f\u67b6", "\u61d2\u4eba\u624b\u673a\u652f\u67b6", "\u624b\u673a\u67b6"],
        "\uc5ec\ud589\uc6a9\ud488": ["\u65c5\u884c\u7528\u54c1", "\u65c5\u6e38\u7528\u54c1", "\u65c5\u884c\u6536\u7eb3", "\u4fbf\u643a\u65c5\u884c\u7528\u54c1", "\u6d17\u6f31\u5305", "\u5206\u88c5\u74f6", "\u62a4\u7167\u5939", "\u884c\u674e\u724c", "\u538b\u7f29\u6536\u7eb3\u888b", "\u65c5\u884c\u6536\u7eb3\u888b"],
    }

    for keyword, expected in examples.items():
        result = expand_keywords(keyword)
        assert result.status == "ok"
        assert result.keywords == expected
        assert result.seed_terms == expected
        assert result.search_urls
        assert not any("\u4e2d\u6587\u5173\u952e\u8bcd\u5019\u9009" in item for item in result.keywords)


def test_unknown_keyword_requests_agent_generated_terms_without_fake_placeholder():
    result = expand_keywords("\uc0c8\ub85c\uc6b4\ud14c\uc2a4\ud2b8\uc0c1\ud488")

    assert result.status == "partial_data"
    assert result.original_keyword == "\uc0c8\ub85c\uc6b4\ud14c\uc2a4\ud2b8\uc0c1\ud488"
    assert result.keywords == []
    assert result.needs_review is True
    assert result.strategy == "agent_generate_terms"
    assert "\u4e2d\u6587\u5173\u952e\u8bcd\u5019\u9009" not in " ".join(result.keywords)
    assert "Generate 5-8 practical Chinese 1688 sourcing search terms" in result.agent_instruction
    assert result.note


def test_component_keyword_is_hint_not_closed_mapping():
    result = expand_keywords("\ucea0\ud551\uc6a9 \ub79c\ud134")

    assert result.status == "partial_data"
    assert result.strategy == "component_seed_terms"
    assert "\u9732\u8425\u7528\u54c1" in result.keywords
    assert result.needs_review is True
    assert result.warnings


def test_phone_component_does_not_force_stand_terms_for_other_products():
    result = expand_keywords("\ud734\ub300\ud3f0 \ucf00\uc774\uc2a4")

    assert result.status == "partial_data"
    assert "\u624b\u673a" in result.keywords
    assert "\u624b\u673a\u58f3" in result.keywords
    assert "\u624b\u673a\u652f\u67b6" not in result.keywords
    assert any("s.1688.com" in url for url in result.search_urls)
