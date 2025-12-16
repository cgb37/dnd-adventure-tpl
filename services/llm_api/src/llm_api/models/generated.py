from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class GeneratedDraft(ABC):
    title: str
    slug: str
    markdown_body: str

    @abstractmethod
    def frontmatter_yaml(self, *, draft_id: UUID, campaign: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def required_yaml_keys(self) -> list[str]:
        raise NotImplementedError
