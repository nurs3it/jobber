"""Тесты TelegramSource с фейковым backend (Фаза 2). Реальный Telegram не дёргаем.

Проверяем: маппинг диалогов/сообщений, фильтр архива, передачу курсора (min_id),
вежливые задержки между запросами.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from core.models import DialogKind
from sources.telegram.source import TelegramSource


def _entity(username=None, megagroup=False, broadcast=False):
    return SimpleNamespace(username=username, megagroup=megagroup, broadcast=broadcast)


def _raw_dialog(id, title, *, archived=False, channel=False, megagroup=False, username=None):
    return SimpleNamespace(
        id=id, name=title, title=title,
        is_user=not channel, is_group=False, is_channel=channel,
        archived=archived, entity=_entity(username=username, megagroup=megagroup),
    )


def _raw_msg(id, text, date=None):
    return SimpleNamespace(id=id, date=date or datetime(2026, 5, 1, tzinfo=timezone.utc),
                           message=text, sender=_entity(username="hr"))


class FakeBackend:
    def __init__(self, dialogs, messages):
        self._dialogs = dialogs           # list of (raw_dialog, archived)
        self._messages = messages         # dict: dialog_id -> list[raw_msg]
        self.connected = False
        self.iter_messages_calls = []     # (dialog_id, min_id)
        self.yielded = 0                  # сколько сырых сообщений реально отдал backend

    async def connect(self):
        self.connected = True

    async def close(self):
        self.connected = False

    async def iter_dialogs(self, include_archived):
        for raw in self._dialogs:
            if raw.archived and not include_archived:
                continue
            yield raw

    async def iter_messages(self, dialog_id, min_id):
        self.iter_messages_calls.append((dialog_id, min_id))
        for m in self._messages.get(dialog_id, []):
            self.yielded += 1
            yield m


async def _collect(aiter):
    return [x async for x in aiter]


@pytest.mark.asyncio
async def test_iter_dialogs_maps_and_includes_archive():
    backend = FakeBackend(
        dialogs=[
            _raw_dialog(111, "Иван"),
            _raw_dialog(-100222, "Jobs", archived=True, channel=True, username="jobs"),
        ],
        messages={},
    )
    src = TelegramSource({}, backend=backend)
    dialogs = await _collect(src.iter_dialogs(include_archived=True))
    assert len(dialogs) == 2
    assert dialogs[0].kind == DialogKind.private
    assert dialogs[1].archived is True
    assert dialogs[1].username == "jobs"


@pytest.mark.asyncio
async def test_iter_dialogs_can_exclude_archive():
    backend = FakeBackend(
        dialogs=[_raw_dialog(-100222, "Jobs", archived=True, channel=True, username="jobs")],
        messages={},
    )
    src = TelegramSource({}, backend=backend)
    dialogs = await _collect(src.iter_dialogs(include_archived=False))
    assert dialogs == []


@pytest.mark.asyncio
async def test_iter_new_messages_maps_and_passes_cursor():
    slept = []
    backend = FakeBackend(
        dialogs=[_raw_dialog(-100222, "Jobs", channel=True, username="jobs")],
        messages={-100222: [_raw_msg(10, "Ищем Frontend"), _raw_msg(11, "Remote")]},
    )
    src = TelegramSource(
        {"sources": {"telegram": {"delay_between_requests": 0.123}}},
        backend=backend,
        sleeper=lambda s: slept.append(s),
    )
    dialog = (await _collect(src.iter_dialogs()))[0]
    msgs = await _collect(src.iter_new_messages(dialog, cursor="9"))

    assert [m.message_id for m in msgs] == ["10", "11"]
    assert msgs[0].link == "https://t.me/jobs/10"
    # курсор "9" пробросился как min_id=9 в backend
    assert backend.iter_messages_calls == [(-100222, 9)]
    # вежливая задержка применялась
    assert slept and slept[0] == 0.123


@pytest.mark.asyncio
async def test_iter_new_messages_no_cursor_means_none_min_id():
    backend = FakeBackend(
        dialogs=[_raw_dialog(-100222, "Jobs", channel=True, username="jobs")],
        messages={-100222: []},
    )
    src = TelegramSource({}, backend=backend, sleeper=lambda s: None)
    dialog = (await _collect(src.iter_dialogs()))[0]
    await _collect(src.iter_new_messages(dialog, cursor=None))
    assert backend.iter_messages_calls == [(-100222, None)]


@pytest.mark.asyncio
async def test_iter_new_messages_sleeps_once_per_page():
    """Задержка — анти-flood МЕЖДУ запросами (страницами), а не на каждое сообщение.

    При request_page_size=2 и 5 сообщениях ждём 3 паузы (на границах страниц: i=0,2,4),
    а не 5. Это и есть фикс производительности: sleep не умножается на сотни сообщений.
    """
    slept = []
    msgs5 = {-100222: [_raw_msg(i, f"m{i}") for i in range(10, 15)]}
    backend = FakeBackend(
        dialogs=[_raw_dialog(-100222, "Jobs", channel=True, username="jobs")],
        messages=msgs5,
    )
    src = TelegramSource(
        {"sources": {"telegram": {"delay_between_requests": 0.5, "request_page_size": 2}}},
        backend=backend,
        sleeper=lambda s: slept.append(s),
    )
    dialog = (await _collect(src.iter_dialogs()))[0]
    out = await _collect(src.iter_new_messages(dialog, cursor=None))

    assert len(out) == 5                 # все сообщения отдаются
    assert len(slept) == 3               # но пауз — по числу страниц (ceil(5/2)), не 5
    assert all(s == 0.5 for s in slept)


@pytest.mark.asyncio
async def test_iter_new_messages_stops_at_cutoff_date():
    """`since` обрывает перебор на первом сообщении старше cutoff (Telethon: новые→старые).

    Это фикс B: depth_days реально ограничивает выборку, а не пост-фильтрует уже скачанное.
    """
    d = lambda day: datetime(2026, 5, day, tzinfo=timezone.utc)  # noqa: E731
    backend = FakeBackend(
        dialogs=[_raw_dialog(-100222, "Jobs", channel=True, username="jobs")],
        messages={-100222: [                       # порядок: от новых к старым
            _raw_msg(30, "Ищем Frontend", date=d(10)),
            _raw_msg(29, "Remote", date=d(9)),
            _raw_msg(28, "старое", date=d(3)),      # < cutoff → обрыв здесь
            _raw_msg(27, "ещё старее", date=d(2)),  # не должно быть тронуто
        ]},
    )
    src = TelegramSource({}, backend=backend, sleeper=lambda s: None)
    dialog = (await _collect(src.iter_dialogs()))[0]
    out = await _collect(src.iter_new_messages(dialog, cursor=None, since=d(5)))

    assert [m.message_id for m in out] == ["30", "29"]   # только свежие отдаются
    assert backend.yielded == 3            # backend дошёл лишь до старого (30,29,28) и встал
                                           # (а не до конца списка из 4) — ранний обрыв, не пост-фильтр


def test_capabilities_read_only():
    src = TelegramSource({}, backend=FakeBackend([], {}))
    caps = src.capabilities
    assert caps.can_scan is True
    assert caps.can_apply is False
