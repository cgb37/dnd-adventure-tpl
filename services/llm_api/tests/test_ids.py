from __future__ import annotations

import uuid

from llm_api.services.ids import content_id


def test_content_id_is_deterministic() -> None:
    a = content_id(kind="npc", campaign="rpg-theForsakenCrown", slug="lady-velden")
    b = content_id(kind="npc", campaign="rpg-theForsakenCrown", slug="lady-velden")
    assert a == b
    assert isinstance(a, uuid.UUID)


def test_content_id_changes_with_slug() -> None:
    a = content_id(kind="npc", campaign="rpg-theForsakenCrown", slug="lady-velden")
    b = content_id(kind="npc", campaign="rpg-theForsakenCrown", slug="lord-velden")
    assert a != b
