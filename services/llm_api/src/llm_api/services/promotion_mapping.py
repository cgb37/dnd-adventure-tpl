from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from llm_api.services.kinds import normalize_kind


@dataclass(frozen=True)
class PromotionRule:
    kind: str
    target_pages_dir: str  # relative to campaign root (e.g. "_pages/npcs")


PROMOTION_RULES: Final[dict[str, PromotionRule]] = {
    "encounter": PromotionRule(kind="encounter", target_pages_dir="_pages/encounters"),
    "encounter-table": PromotionRule(kind="encounter-table", target_pages_dir="_pages/encounter-tables"),
    "location": PromotionRule(kind="location", target_pages_dir="_pages/locations"),
    "monster": PromotionRule(kind="monster", target_pages_dir="_pages/monsters"),
    "npc": PromotionRule(kind="npc", target_pages_dir="_pages/npcs"),
    "character": PromotionRule(kind="character", target_pages_dir="_pages/characters"),
}


def get_draft_path(*, campaign_root: Path, kind: str, slug: str) -> Path:
    kind_norm = normalize_kind(kind)
    return campaign_root / "_drafts" / kind_norm / f"{slug}.md"


def get_promoted_path(*, campaign_root: Path, kind: str, slug: str) -> Path:
    kind_norm = normalize_kind(kind)
    rule = PROMOTION_RULES.get(kind_norm)
    if rule is None:
        raise KeyError(kind_norm)
    return campaign_root / rule.target_pages_dir / f"{slug}.md"


def list_promotable_kinds() -> list[str]:
    return sorted(PROMOTION_RULES.keys())
