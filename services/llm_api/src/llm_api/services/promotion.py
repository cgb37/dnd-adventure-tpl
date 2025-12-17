from __future__ import annotations

import shutil
from pathlib import Path

from llm_api.services.errors import ApiError
from llm_api.services.kinds import normalize_kind
from llm_api.services.promotion_mapping import get_draft_path, get_promoted_path


def _is_within(*, child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _validate_slug(slug: str) -> str:
    s = (slug or "").strip()
    if not s:
        raise ApiError(code="invalid_slug", message="Slug is required", status_code=400)
    if "/" in s or "\\" in s:
        raise ApiError(code="invalid_slug", message="Slug must not contain path separators", status_code=400)
    if ".." in s:
        raise ApiError(code="invalid_slug", message="Slug must not contain '..'", status_code=400)
    return s


def promote_draft(*, campaign_root: Path, kind: str, slug: str) -> tuple[Path, Path]:
    kind_norm = normalize_kind(kind)
    slug_norm = _validate_slug(slug)

    try:
        draft_path = get_draft_path(campaign_root=campaign_root, kind=kind_norm, slug=slug_norm)
        promoted_path = get_promoted_path(campaign_root=campaign_root, kind=kind_norm, slug=slug_norm)
    except KeyError:
        raise ApiError(code="unsupported_kind", message=f"Unsupported kind: {kind_norm}", status_code=400)

    if not _is_within(child=draft_path, parent=campaign_root):
        raise ApiError(code="invalid_path", message="Draft path is outside campaign root", status_code=400)
    if not _is_within(child=promoted_path, parent=campaign_root):
        raise ApiError(code="invalid_path", message="Promoted path is outside campaign root", status_code=400)

    if not draft_path.exists():
        raise ApiError(code="draft_not_found", message="Draft not found", status_code=404)

    promoted_path.parent.mkdir(parents=True, exist_ok=True)

    if promoted_path.exists():
        raise ApiError(code="target_exists", message="Target already exists", status_code=409)

    try:
        shutil.move(str(draft_path), str(promoted_path))
    except Exception as exc:
        raise ApiError(
            code="promote_failed",
            message="Failed to promote draft",
            status_code=500,
            details={"error": str(exc)},
        )

    # Best-effort: remove empty draft kind directory
    try:
        draft_dir = draft_path.parent
        draft_dir.rmdir()
    except Exception:
        pass

    return draft_path, promoted_path
