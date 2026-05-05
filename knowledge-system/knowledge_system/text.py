from __future__ import annotations

import re
import unicodedata


def slugify(value: str, fallback: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or fallback


def excerpt(text: str, length: int = 500) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= length:
        return cleaned
    return cleaned[: length - 3].rstrip() + "..."

