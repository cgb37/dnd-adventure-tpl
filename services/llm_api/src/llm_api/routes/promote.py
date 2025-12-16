from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from llm_api.services.active_campaign import get_active_campaign, get_repo_root
from llm_api.services.kinds import normalize_kind
from llm_api.services.promotion import promote_draft
from llm_api.services.responses import ok
from llm_api.services.security import require_api_key

router = APIRouter()


@router.post("/promote/{kind}/{slug}", dependencies=[Depends(require_api_key)])
async def promote(kind: str, slug: str):
    kind = normalize_kind(kind)
    campaign = get_active_campaign()
    repo_root = get_repo_root()
    campaign_root = Path(repo_root) / "campaigns" / campaign

    draft_path, promoted_path = promote_draft(campaign_root=campaign_root, kind=kind, slug=slug)

    return ok(
        {
            "kind": kind,
            "campaign": campaign,
            "slug": slug,
            "from": str(draft_path.relative_to(repo_root)),
            "to": str(promoted_path.relative_to(repo_root)),
        }
    )
