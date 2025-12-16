from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from llm_api.services import active_campaign
from llm_api.services.errors import ApiError


def _drafts_dir(*, campaign: str) -> Path:
    root = active_campaign.get_repo_root()
    return root / "campaigns" / campaign / "_drafts"


def write_draft(
    *,
    kind: str,
    campaign: str,
    slug: str,
    title: str,
    yaml_frontmatter: dict[str, Any],
    markdown_body: str,
) -> str:
    drafts_dir = _drafts_dir(campaign=campaign) / kind
    try:
        drafts_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise ApiError(
            code="draft_write_failed",
            message="Failed to create drafts directory",
            status_code=500,
            details={"error": str(exc)},
        )

    path = drafts_dir / f"{slug}.md"

    frontmatter_yaml_str = yaml.safe_dump(
        yaml_frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )

    content = (
        "---\n"
        f"{frontmatter_yaml_str}"
        "---\n\n"
        f"# {title}\n\n"
        f"{markdown_body.strip()}\n"
    )

    try:
        path.write_text(content, encoding="utf-8")
    except Exception as exc:
        raise ApiError(
            code="draft_write_failed",
            message="Failed to write draft",
            status_code=500,
            details={"error": str(exc), "path": str(path)},
        )

    # Return workspace-relative path for convenience
    root = active_campaign.get_repo_root()
    return str(path.relative_to(root))
