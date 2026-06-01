"""Доменные модели Jobber (pydantic).

Это provider-agnostic контракт: ни одно поле не завязано на Telegram.
Любой источник (Telegram, LinkedIn, веб-доска) маппит свои данные в эти модели.

Инвариант: модели не импортируют ничего из sources/. Зависимость только в одну сторону.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DialogKind(str, Enum):
    """Тип диалога/контейнера сообщений (нормализованный, не телеграм-специфичный)."""

    private = "private"
    group = "group"
    supergroup = "supergroup"
    channel = "channel"
    unknown = "unknown"


class Dialog(BaseModel):
    """Контейнер сообщений в источнике (чат, группа, канал, сообщество)."""

    source: str                      # имя источника, напр. "telegram"
    id: str                          # стабильный id диалога внутри источника
    title: str
    kind: DialogKind = DialogKind.unknown
    username: str | None = None      # @username, если есть (для построения ссылок)
    archived: bool = False           # из архива? (Telegram folder_id == 1)


class RawMessage(BaseModel):
    """Сырое сообщение из источника до классификации."""

    source: str
    dialog_id: str
    message_id: str                  # стабильный id сообщения внутри диалога
    date: datetime
    text: str
    sender: str | None = None        # @username/имя отправителя, если доступно
    link: str | None = None          # прямая ссылка на сообщение, если её можно построить
    dialog_title: str | None = None  # денормализация для дайджеста/кандидатов
    archived: bool = False           # сообщение из архивного диалога?


class Contact(BaseModel):
    """Кому писать по вакансии. Если ничего не нашли — found=False (честная пометка)."""

    found: bool = False
    username: str | None = None      # @hr_user
    url: str | None = None           # https://t.me/... или внешняя ссылка
    bot: str | None = None           # @some_bot, если отклик через бота
    raw: str | None = None           # как контакт выглядел в тексте (email/телефон/прочее)
    note: str | None = None          # напр. "контакт не указан"


class Profile(BaseModel):
    """Профиль соискателя, извлечённый из резюме (источник истины — profile/cv.md)."""

    role: str | None = None          # основная роль/желаемая позиция
    grade: str | None = None         # junior/middle/senior/lead и т.п.
    skills: list[str] = Field(default_factory=list)
    years_experience: float | None = None
    location: str | None = None
    remote_ok: bool | None = None
    relocation_ok: bool | None = None
    salary_min: float | None = None
    salary_currency: str | None = None
    languages: list[str] = Field(default_factory=list)
    stop_factors: list[str] = Field(default_factory=list)
    summary: str | None = None       # краткое саммари из cv.md
    raw_markdown: str | None = None  # полный cv.md, чтобы LLM имела весь контекст


class Vacancy(BaseModel):
    """Вакансия, извлечённая из сообщения."""

    source: str
    dialog_id: str
    message_id: str
    title: str | None = None
    company: str | None = None
    text: str                        # исходный текст вакансии
    link: str | None = None          # ссылка на пост/чат/канал
    contact: Contact = Field(default_factory=Contact)
    location: str | None = None
    remote: bool | None = None
    salary: str | None = None        # как указано в тексте (свободная форма)
    posted_at: datetime | None = None
    dialog_title: str | None = None  # источник для карточки дайджеста
    archived: bool = False


class MatchResult(BaseModel):
    """Результат оценки релевантности вакансии профилю."""

    score: int = Field(ge=0, le=100)
    reason: str                      # краткая причина скора (1–2 предложения)
    is_vacancy: bool = True          # LLM подтвердила, что это реально вакансия


class CoverLetter(BaseModel):
    """Сопроводительное письмо — ВСЕГДА только черновик под ревью пользователя."""

    text: str
    language: str = "ru"
    tone: str = "friendly"
    is_draft: bool = True            # инвариант: ничего не отправляется автоматически


class ScoredVacancy(BaseModel):
    """Агрегат для дайджеста: вакансия + оценка + (опц.) письмо."""

    vacancy: Vacancy
    match: MatchResult
    cover_letter: CoverLetter | None = None
    dedup_key: str | None = None     # ключ схлопывания повторов из разных каналов
