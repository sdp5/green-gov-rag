# Cleaning, preprocessing

# etl/utils.py

from __future__ import annotations

import re
import unicodedata


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters (e.g., accents, ligatures)."""
    return unicodedata.normalize("NFKC", text)


def remove_urls(text: str) -> str:
    """Remove URLs from text."""
    return re.sub(r"http\S+|www\.\S+", "", text)


def remove_non_alphanumeric(text: str) -> str:
    """Keep only alphanumeric, basic punctuation, and whitespace."""
    return re.sub(r"[^0-9a-zA-Z\s.,;:!?()\"\'-]", " ", text)


def collapse_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into a single space."""
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    """Apply all cleaning steps to a single text string.
    Order matters: normalize → remove urls → clean chars → collapse spaces.
    """
    text = normalize_unicode(text)
    text = remove_urls(text)
    text = remove_non_alphanumeric(text)
    return collapse_whitespace(text)


def batch_clean(texts: list[str]) -> list[str]:
    """Clean a list of text strings."""
    return [clean_text(t) for t in texts]
