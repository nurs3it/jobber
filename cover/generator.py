"""Генерация сопроводительных писем под конкретную вакансию + cv.md.

Тон/длина/язык — из config.yaml (cover_letter.*). Письмо ВСЕГДА только черновик (is_draft=True);
ничего не отправляется автоматически — отклик делает пользователь руками.

В основном сценарии текст пишет сам Claude Code (правила /cover). Программный путь (этот модуль)
нужен для автономного дайджеста по расписанию — тогда передаётся LLM-клиент.
"""

from __future__ import annotations

import re
from typing import Any

from core.llm import LLM
from core.models import CoverLetter, Profile, Vacancy

_CYRILLIC_RE = re.compile(r"[а-яё]", flags=re.IGNORECASE)


def _resolve_language(config_lang: str, vacancy: Vacancy) -> str:
    """Определить язык письма. 'auto' → по языку текста вакансии (кириллица → ru, иначе en)."""
    if config_lang and config_lang != "auto":
        return config_lang
    return "ru" if _CYRILLIC_RE.search(vacancy.text or "") else "en"


def _build_system(cfg: dict[str, Any], language: str) -> str:
    tone = cfg.get("tone", "friendly")
    youthful = cfg.get("youthful", True)
    max_sentences = cfg.get("max_sentences", 6)
    youthful_note = "молодёжный, человечный, живой" if youthful else "сдержанный"
    return (
        "Ты пишешь короткое сопроводительное письмо под конкретную вакансию и резюме соискателя. "
        f"Тон: {tone} ({youthful_note}). Длина: не более {max_sentences} предложений. "
        f"Язык письма: {language}. Письмо — черновик под ревью, его отправит сам человек. "
        "Зацепи реальным релевантным опытом из резюме, без шаблонной воды и без выдумывания фактов. "
        "Не указывай контакты и подпись — только текст письма."
    )


def _build_user(vacancy: Vacancy, profile: Profile) -> str:
    return (
        f"=== РЕЗЮМЕ (cv.md) ===\n{profile.raw_markdown or profile.summary or ''}\n\n"
        f"=== ВАКАНСИЯ ===\n{vacancy.title or ''}\n{vacancy.text}\n\n"
        "Напиши текст письма."
    )


def generate_cover_letter(
    vacancy: Vacancy,
    profile: Profile,
    config: dict[str, Any],
    llm: LLM,
) -> CoverLetter:
    """Сгенерировать короткий персональный черновик письма."""
    cfg = config.get("cover_letter", {})
    language = _resolve_language(cfg.get("language", "ru"), vacancy)
    system = _build_system(cfg, language)
    user = _build_user(vacancy, profile)
    text = llm.complete(system, user).strip()
    return CoverLetter(
        text=text,
        language=language,
        tone=cfg.get("tone", "friendly"),
        is_draft=True,
    )
