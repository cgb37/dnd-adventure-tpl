from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from llm_api.models.requests import GenerateRequest
from llm_api.services.security import require_api_key
from llm_api.services.active_campaign import get_active_campaign
from llm_api.services.drafts import write_draft
from llm_api.services.kinds import normalize_kind
from llm_api.services.ids import content_id
from llm_api.services.limits import get_limits
from llm_api.services.responses import created
from llm_api.generators.dispatch import generate_for_kind

router = APIRouter()


@router.post("/generate/{kind}", dependencies=[Depends(require_api_key)])
async def generate(
    kind: str,
    req: GenerateRequest,
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
):
    kind = normalize_kind(kind)
    campaign = get_active_campaign()

    limits = get_limits()
    async with limits.guard():
        generated = await generate_for_kind(
            kind=kind,
            request=req,
            campaign=campaign,
            provider_override=x_llm_provider,
        )

    slug = generated.slug
    draft_id = content_id(kind=kind, campaign=campaign, slug=slug)

    draft_path = write_draft(
        kind=kind,
        campaign=campaign,
        slug=slug,
        title=generated.title,
        yaml_frontmatter=generated.frontmatter_yaml(draft_id=draft_id, campaign=campaign),
        markdown_body=generated.markdown_body,
    )

    return created(
        {
            "kind": kind,
            "campaign": campaign,
            "slug": slug,
            "id": str(draft_id),
            "draft_path": draft_path,
            "placeholders_used": True,
            "yaml_keys_present": generated.required_yaml_keys(),
        }
    )
