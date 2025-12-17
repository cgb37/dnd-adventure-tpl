from __future__ import annotations

import uuid

from llm_api.constants import UUID_NAMESPACE


def content_id(*, kind: str, campaign: str, slug: str) -> uuid.UUID:
    name = f"{kind}:{campaign}:{slug}"
    return uuid.uuid5(UUID_NAMESPACE, name)
