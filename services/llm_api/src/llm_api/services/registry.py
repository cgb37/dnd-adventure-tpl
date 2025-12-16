from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from llm_api.generators.dispatch import SUPPORTED_KINDS
from llm_api.models.requests import GenerateRequest
from llm_api.services.kinds import normalize_kind


class FieldMeta(TypedDict, total=False):
    required: bool
    annotation: str
    default: Any
    description: str


def list_generator_kinds() -> list[str]:
    return sorted(SUPPORTED_KINDS)


def get_request_model_for_kind(kind: str) -> type[BaseModel]:
    """Return the Pydantic request model for a generator kind.

    Today, all generators share `GenerateRequest`. In future iterations we can
    return per-kind models without changing the UI contract.
    """

    k = normalize_kind(kind)
    if k not in SUPPORTED_KINDS:
        raise KeyError(k)
    return GenerateRequest


def schema_for_kind(kind: str) -> dict[str, Any]:
    """Return a minimal schema for the UI (derived from a Pydantic model)."""

    model = get_request_model_for_kind(kind)
    fields = model.model_fields

    required = [name for name, f in fields.items() if f.is_required()]
    optional = [name for name, f in fields.items() if not f.is_required()]

    properties: dict[str, FieldMeta] = {}
    for name, f in fields.items():
        meta: FieldMeta = {
            "required": f.is_required(),
            "annotation": str(f.annotation),
        }
        # Pydantic v2 uses a sentinel default for required fields which is not
        # JSON serializable. Only expose real defaults.
        if f.default is not PydanticUndefined and f.default is not None:
            meta["default"] = f.default
        if f.description:
            meta["description"] = f.description
        properties[name] = meta

    # Also include a full JSON schema in case the UI wants richer types.
    json_schema = model.model_json_schema()

    return {
        "model": f"{model.__module__}.{model.__name__}",
        "required": required,
        "optional": optional,
        "properties": properties,
        "json_schema": json_schema,
    }
