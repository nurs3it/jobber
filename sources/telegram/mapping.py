"""Маппинг сырых объектов Telethon → доменные модели Jobber + извлечение контакта.

Здесь живёт вся телеграм-специфика преобразования, чтобы source.py оставался тонким.
"""

from __future__ import annotations

import re
from typing import Any

from core.models import Contact, Dialog, DialogKind, RawMessage


def _dialog_kind(tg_dialog: Any) -> DialogKind:
    """Определить нормализованный тип диалога из флагов Telethon."""
    if getattr(tg_dialog, "is_user", False):
        return DialogKind.private
    if getattr(tg_dialog, "is_group", False):
        return DialogKind.group
    if getattr(tg_dialog, "is_channel", False):
        entity = getattr(tg_dialog, "entity", None)
        # Супергруппа (megagroup) vs вещательный канал (broadcast).
        if getattr(entity, "megagroup", False):
            return DialogKind.supergroup
        return DialogKind.channel
    return DialogKind.unknown


def map_dialog(tg_dialog: Any) -> Dialog:
    """Telethon Dialog → core Dialog (тип, username, archived)."""
    entity = getattr(tg_dialog, "entity", None)
    title = getattr(tg_dialog, "title", None) or getattr(tg_dialog, "name", None) or ""
    return Dialog(
        source="telegram",
        id=str(tg_dialog.id),
        title=title,
        kind=_dialog_kind(tg_dialog),
        username=getattr(entity, "username", None),
        archived=bool(getattr(tg_dialog, "archived", False)),
    )


def _message_link(dialog: Dialog, message_id: str) -> str | None:
    """Построить ссылку t.me на сообщение, если это возможно.

    - публичный канал/группа с @username → t.me/<username>/<id>
    - приватный канал/супергруппа (id вида -100<rest>) → t.me/c/<rest>/<id>
    - личные чаты/обычные группы → ссылки нет (None)
    """
    if dialog.username:
        return f"https://t.me/{dialog.username}/{message_id}"
    if dialog.kind in (DialogKind.channel, DialogKind.supergroup):
        raw = dialog.id
        if raw.startswith("-100"):
            internal = raw[len("-100"):]
            return f"https://t.me/c/{internal}/{message_id}"
    return None


def map_message(tg_message: Any, dialog: Dialog) -> RawMessage:
    """Telethon Message → core RawMessage (текст, дата, отправитель, ссылка t.me)."""
    text = getattr(tg_message, "message", None)
    if text is None:
        text = getattr(tg_message, "text", "") or ""

    sender = getattr(tg_message, "sender", None)
    sender_username = getattr(sender, "username", None) if sender is not None else None

    message_id = str(tg_message.id)
    return RawMessage(
        source="telegram",
        dialog_id=dialog.id,
        message_id=message_id,
        date=tg_message.date,
        text=text,
        sender=sender_username,
        link=_message_link(dialog, message_id),
    )


# --- Извлечение контакта (используется на Фазе 4 при классификации) ---

_USERNAME_RE = re.compile(r"(?<![\w@/])@([A-Za-z][A-Za-z0-9_]{3,31})")
_TME_RE = re.compile(r"https?://t\.me/[A-Za-z0-9_+/]+")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\-\s()]{7,}\d")


def extract_contact(text: str) -> Contact:
    """Вытащить контакт из текста вакансии: @username / t.me-ссылка / бот / email / телефон.

    Если ничего не нашли — Contact(found=False, note="контакт не указан").
    """
    if not text:
        return Contact(found=False, note="контакт не указан")

    tme = _TME_RE.search(text)
    email = _EMAIL_RE.search(text)
    username_match = _USERNAME_RE.search(text)
    username = username_match.group(1) if username_match else None

    bot = username if (username and username.lower().endswith("bot")) else None

    if not any([username, tme, email]):
        phone = _PHONE_RE.search(text)
        if phone:
            return Contact(found=True, raw=phone.group(0).strip())
        return Contact(found=False, note="контакт не указан")

    return Contact(
        found=True,
        username=username,
        url=tme.group(0) if tme else None,
        bot=bot,
        raw=email.group(0) if email else None,
    )
