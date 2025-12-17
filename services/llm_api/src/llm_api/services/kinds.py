from __future__ import annotations


def normalize_kind(kind: str) -> str:
    """Normalize user/UI input into the canonical kind identifier.

    Canonical kind format is kebab-case for URLs and folder names.
    Accepts common variants like:
      - "Encounter Table"
      - "encounter table"
      - "encounter_table"
      - "encounter-table"

    Note: canonical kinds are validated against the supported generator list.
    """

    k = (kind or "").strip().lower()
    k = k.replace("_", "-").replace(" ", "-")
    while "--" in k:
        k = k.replace("--", "-")
    return k
