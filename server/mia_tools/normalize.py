"""Bounded, read-only normalization for trusted MC response shapes.

These helpers do not perform I/O, persistence, model calls, or network access.
They intentionally omit large/private report fields before data can reach MIA.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_TEXT_LIMIT = 2000
_ITEM_LIMIT = 10


def _text(value: Any, limit: int = _TEXT_LIMIT) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)[:limit]
    return ""


def _list(value: Any, limit: int = _ITEM_LIMIT) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit]


def _recommendations(value: Any) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in _list(value):
        if not isinstance(item, Mapping):
            continue
        result.append({
            "title": _text(item.get("title"), 500),
            "status": _text(item.get("status"), 100),
        })
    return result


def _strings(value: Any) -> list[str]:
    return [_text(item, 500) for item in _list(value) if _text(item, 500)]


def _require_items(raw: Any) -> list[Mapping[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("expected_list")
    return [item for item in raw if isinstance(item, Mapping)]


def normalize_projects(raw: Any) -> list[dict[str, Any]]:
    """Return bounded project summaries; omit unknown and sensitive fields."""
    result = []
    for item in _require_items(raw):
        result.append({
            "id": _text(item.get("id"), 128),
            "name": _text(item.get("name")),
            "domain": _text(item.get("domain"), 500),
            "type": _text(item.get("type"), 100),
            "status": _text(item.get("status"), 100),
            "description": _text(item.get("description")),
            "recommendations": _recommendations(item.get("recommendations")),
            "created_at": _text(item.get("created_at"), 80),
            "updated_at": _text(item.get("updated_at"), 80),
        })
    return result


def normalize_clients(raw: Any) -> list[dict[str, Any]]:
    """Return bounded client summaries without unlisted fields."""
    result = []
    for item in _require_items(raw):
        result.append({
            "id": _text(item.get("id"), 128),
            "name": _text(item.get("name")),
            "website": _text(item.get("website"), 2048),
            "email": _text(item.get("email"), 320),
            "phone": _text(item.get("phone"), 100),
            "cif": _text(item.get("cif"), 100),
            "sector": _text(item.get("sector"), 200),
            "status": _text(item.get("status"), 100),
            "notes": _text(item.get("notes")),
            "source": _text(item.get("source"), 200),
            "created_at": _text(item.get("created_at"), 80),
            "updated_at": _text(item.get("updated_at"), 80),
        })
    return result


def normalize_audits(raw: Any) -> list[dict[str, Any]]:
    """Return bounded audit summaries without full reports or plan documents."""
    result = []
    for item in _require_items(raw):
        result.append({
            "id": _text(item.get("id"), 128),
            "client_id": _text(item.get("client_id"), 128),
            "url": _text(item.get("url"), 2048),
            "status": _text(item.get("status"), 100),
            "summary": _text(item.get("summary")),
            "tech_stack": _strings(item.get("tech_stack")),
            "seo_score": _text(item.get("seo_score"), 100),
            "recommendations": _strings(item.get("recommendations")),
            "created_at": _text(item.get("created_at"), 80),
            "is_test": bool(item.get("is_test", False)),
        })
    return result
