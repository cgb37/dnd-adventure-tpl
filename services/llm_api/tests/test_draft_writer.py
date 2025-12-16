from __future__ import annotations

from pathlib import Path

import yaml

from llm_api.services.drafts import write_draft


def test_write_draft_writes_frontmatter_and_body(tmp_path: Path, monkeypatch) -> None:
    # Arrange a fake repo root with campaigns/<active>/_drafts.
    root = tmp_path
    (root / "campaigns" / "test-campaign").mkdir(parents=True)

    # Patch repo root resolver.
    from llm_api.services import active_campaign

    monkeypatch.setattr(active_campaign, "get_repo_root", lambda: root)

    # Act
    draft_path = write_draft(
        kind="npc",
        campaign="test-campaign",
        slug="test-npc",
        title="Test NPC",
        yaml_frontmatter={"layout": "npc", "title": "Test NPC", "slug": "test-npc"},
        markdown_body="Hello world",
    )

    # Assert
    abs_path = root / draft_path
    assert abs_path.exists()

    text = abs_path.read_text(encoding="utf-8")
    assert text.startswith("---\n")

    parts = text.split("---\n")
    # Format is: "" | yaml | "\n# Title..."
    assert len(parts) >= 3
    parsed = yaml.safe_load(parts[1])
    assert parsed["layout"] == "npc"
    assert parsed["title"] == "Test NPC"
    assert "Hello world" in text
