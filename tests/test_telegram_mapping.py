"""Тесты маппинга Telethon → доменные модели (Фаза 2).

Не вызываем реальный Telegram: используем лёгкие фейки с теми же атрибутами,
что у объектов Telethon (Dialog/Message/entity). Это тестирует НАШУ логику маппинга.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from core.models import DialogKind
from sources.telegram import mapping


def _entity(username=None, megagroup=False, broadcast=False):
    return SimpleNamespace(username=username, megagroup=megagroup, broadcast=broadcast)


def test_map_dialog_private():
    tg = SimpleNamespace(
        id=111, name="Иван", title="Иван",
        is_user=True, is_group=False, is_channel=False,
        archived=False, entity=_entity(username="ivan"),
    )
    d = mapping.map_dialog(tg)
    assert d.source == "telegram"
    assert d.id == "111"
    assert d.title == "Иван"
    assert d.kind == DialogKind.private
    assert d.username == "ivan"
    assert d.archived is False


def test_map_dialog_supergroup_archived():
    tg = SimpleNamespace(
        id=-100222, name="Jobs Chat", title="Jobs Chat",
        is_user=False, is_group=False, is_channel=True,
        archived=True, entity=_entity(username=None, megagroup=True),
    )
    d = mapping.map_dialog(tg)
    assert d.kind == DialogKind.supergroup
    assert d.archived is True
    assert d.username is None


def test_map_dialog_broadcast_channel():
    tg = SimpleNamespace(
        id=-100333, name="Vacancies", title="Vacancies",
        is_user=False, is_group=False, is_channel=True,
        archived=False, entity=_entity(username="vacancies", broadcast=True),
    )
    d = mapping.map_dialog(tg)
    assert d.kind == DialogKind.channel
    assert d.username == "vacancies"


def test_map_dialog_basic_group():
    tg = SimpleNamespace(
        id=-444, name="Team", title="Team",
        is_user=False, is_group=True, is_channel=False,
        archived=False, entity=_entity(),
    )
    d = mapping.map_dialog(tg)
    assert d.kind == DialogKind.group


def test_map_message_with_public_link():
    dialog = mapping.map_dialog(SimpleNamespace(
        id=-100333, name="Vacancies", title="Vacancies",
        is_user=False, is_group=False, is_channel=True,
        archived=False, entity=_entity(username="vacancies", broadcast=True),
    ))
    msg = SimpleNamespace(
        id=42, date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        message="Ищем Frontend-разработчика", sender=_entity(username="hr_anna"),
    )
    m = mapping.map_message(msg, dialog)
    assert m.message_id == "42"
    assert m.dialog_id == "-100333"
    assert "Frontend" in m.text
    assert m.sender == "hr_anna"
    assert m.link == "https://t.me/vacancies/42"


def test_map_message_private_no_public_link():
    dialog = mapping.map_dialog(SimpleNamespace(
        id=111, name="Иван", title="Иван",
        is_user=True, is_group=False, is_channel=False,
        archived=False, entity=_entity(username=None),
    ))
    msg = SimpleNamespace(id=5, date=datetime(2026, 5, 1, tzinfo=timezone.utc),
                          message="привет", sender=None)
    m = mapping.map_message(msg, dialog)
    assert m.link is None
    assert m.sender is None


def test_map_message_private_channel_c_link():
    dialog = mapping.map_dialog(SimpleNamespace(
        id=-100777, name="Closed", title="Closed",
        is_user=False, is_group=False, is_channel=True,
        archived=False, entity=_entity(username=None, megagroup=True),
    ))
    msg = SimpleNamespace(id=9, date=datetime(2026, 5, 1, tzinfo=timezone.utc),
                          message="вакансия", sender=None)
    m = mapping.map_message(msg, dialog)
    # Приватный супергруппа/канал → ссылка вида t.me/c/<id без -100>/<msg>
    assert m.link == "https://t.me/c/777/9"
