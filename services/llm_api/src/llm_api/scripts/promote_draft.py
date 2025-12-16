from __future__ import annotations

import argparse

from llm_api.services.active_campaign import get_active_campaign, get_repo_root
from llm_api.services.promotion import promote_draft


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a draft into _pages using the canonical mapping.")
    parser.add_argument("kind", help='Kind (e.g. "npc", "encounter-table", "encounter table")')
    parser.add_argument("slug", help="Slug (kebab-case)")
    args = parser.parse_args()

    campaign = get_active_campaign()
    repo_root = get_repo_root()
    campaign_root = repo_root / "campaigns" / campaign

    draft_path, promoted_path = promote_draft(campaign_root=campaign_root, kind=args.kind, slug=args.slug)

    print(str(draft_path.relative_to(repo_root)))
    print("->")
    print(str(promoted_path.relative_to(repo_root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
