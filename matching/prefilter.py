"""Эвристический предфильтр — первая ступень детекции вакансий (до LLM, экономит токены).

Сообщение проходит дальше, если содержит ключевые слова/хэштеги из config.yaml (prefilter.*).
RU + EN, регистронезависимо. Расширяемо через конфиг.
"""

from __future__ import annotations

from typing import Any

from core.models import RawMessage


def looks_like_vacancy(message: RawMessage, config: dict[str, Any]) -> bool:
    """True, если сообщение похоже на вакансию по эвристике (keywords/hashtags).

    Если prefilter.enabled == False — пропускать всё (True), полагаясь на LLM (дороже).
    """
    pf = config.get("prefilter", {})
    if not pf.get("enabled", True):
        return True

    text = (message.text or "").lower()
    if not text.strip():
        return False

    keywords = list(pf.get("keywords_ru", [])) + list(pf.get("keywords_en", []))
    for kw in keywords:
        if kw and kw.lower() in text:
            return True

    for tag in pf.get("hashtags", []):
        if tag and f"#{tag.lower()}" in text:
            return True

    return False
