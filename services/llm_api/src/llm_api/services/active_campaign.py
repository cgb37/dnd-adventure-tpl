from __future__ import annotations

from pathlib import Path

from llm_api.services.errors import ApiError


def get_repo_root() -> Path:
    # services/llm_api/src/llm_api/services -> repo root is 5 parents up
    return Path(__file__).resolve().parents[5]


def get_active_campaign() -> str:
    root = get_repo_root()
    active_path = root / ".active-campaign"
    if not active_path.exists():
        raise ApiError(
            code="no_active_campaign",
            message="No active campaign. Run scripts/use-campaign first.",
            status_code=409,
        )

    campaign = active_path.read_text(encoding="utf-8").strip()
    if not campaign:
        raise ApiError(
            code="no_active_campaign",
            message="Active campaign file is empty. Re-run scripts/use-campaign.",
            status_code=409,
        )

    return campaign
