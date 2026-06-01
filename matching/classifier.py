"""LLM-классификация (вторая ступень): вакансия ли это + извлечение полей + скоринг 0–100.

Вход: сообщение, прошедшее предфильтр, + Profile (profile/cv.md). Выход: (Vacancy|None, MatchResult).

В основном сценарии этот шаг делает САМ Claude Code (через MCP и правила /scan). Программный
путь (этот модуль) нужен для автономного запуска по расписанию — тогда передаётся LLM-клиент.
Контакт извлекается детерминированно из текста (mapping.extract_contact), не из LLM.
"""

from __future__ import annotations

from typing import Any

from core.llm import LLM, extract_json
from core.models import MatchResult, Profile, RawMessage, Vacancy
from sources.telegram.mapping import extract_contact

_SYSTEM = (
    "Ты помощник по поиску работы. Тебе дают текст сообщения из Telegram и профиль соискателя. "
    "Определи, является ли сообщение вакансией, извлеки поля и оцени релевантность профилю 0–100. "
    "Отвечай СТРОГО одним JSON-объектом без пояснений со схемой: "
    '{"is_vacancy": bool, "title": str|null, "company": str|null, "location": str|null, '
    '"remote": bool|null, "salary": str|null, "score": int(0-100), "reason": str}. '
    "score — насколько вакансия подходит соискателю (учитывай навыки, грейд, стоп-факторы, "
    "локацию/удалёнку). Если это не вакансия — is_vacancy=false, score=0. reason — кратко по-русски."
)


def _build_user_prompt(message: RawMessage, profile: Profile) -> str:
    return (
        f"=== ПРОФИЛЬ СОИСКАТЕЛЯ (cv.md) ===\n{profile.raw_markdown or profile.summary or ''}\n\n"
        f"=== СООБЩЕНИЕ ИЗ TELEGRAM ===\n{message.text}\n\n"
        "Верни JSON по схеме."
    )


def classify_and_score(
    message: RawMessage,
    profile: Profile,
    config: dict[str, Any],
    llm: LLM,
) -> tuple[Vacancy | None, MatchResult]:
    """Определить, вакансия ли это, извлечь поля и оценить релевантность профилю."""
    raw = llm.complete(_SYSTEM, _build_user_prompt(message, profile))
    data = extract_json(raw)

    is_vacancy = bool(data.get("is_vacancy"))
    score = _clamp_score(data.get("score", 0))
    reason = str(data.get("reason", "")).strip() or "без пояснения"

    if not is_vacancy:
        return None, MatchResult(score=0, reason=reason, is_vacancy=False)

    vacancy = Vacancy(
        source=message.source,
        dialog_id=message.dialog_id,
        message_id=message.message_id,
        title=data.get("title"),
        company=data.get("company"),
        text=message.text,
        link=message.link,
        contact=extract_contact(message.text),
        location=data.get("location"),
        remote=data.get("remote"),
        salary=data.get("salary"),
        posted_at=message.date,
    )
    return vacancy, MatchResult(score=score, reason=reason, is_vacancy=True)


def _clamp_score(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, n))
