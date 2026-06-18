from __future__ import annotations


def normalize_legacy_product_text(text: str) -> str:
    """Normalize old demo-era wording when rendering user-facing evidence."""
    replacements = {
        "Feishu dry-run plan": "Feishu preview plan",
        "feishu dry-run plan": "feishu preview plan",
        "Feishu dry-run write plan": "Feishu preview write plan",
        "Feishu write remains dry-run": "Feishu write is currently preview-only",
        "Feishu plan is dry-run": "Feishu plan is preview-only",
        "dry-run Feishu plan": "Feishu preview plan",
    }
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized
