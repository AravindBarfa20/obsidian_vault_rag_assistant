"""Small, provider-neutral cleanup for text that is safe to show to users."""

from __future__ import annotations

import re

_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def clean_answer_text(text: str) -> str:
    """Render copied Obsidian wikilinks as readable labels in generated prose."""

    def replace_wikilink(match: re.Match[str]) -> str:
        target, label = match.groups()
        return (label or target).strip()

    return _WIKILINK.sub(replace_wikilink, text).strip()
