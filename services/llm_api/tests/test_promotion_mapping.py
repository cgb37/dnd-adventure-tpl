from __future__ import annotations

from pathlib import Path

from llm_api.services.promotion_mapping import get_promoted_path


def test_magic_item_promotes_to_pages_magic_items(tmp_path: Path):
    campaign_root = tmp_path / "campaigns" / "test-campaign"
    result = get_promoted_path(campaign_root=campaign_root, kind="magic-item", slug="ring-of-warmth")
    assert result == campaign_root / "_pages" / "magic-items" / "ring-of-warmth.md"


def test_magic_item_kind_is_listed_as_promotable():
    from llm_api.services.promotion_mapping import list_promotable_kinds

    assert "magic-item" in list_promotable_kinds()
