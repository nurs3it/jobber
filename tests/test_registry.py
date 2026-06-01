"""Тесты реестра источников и conformance заглушек (Фаза 7)."""

from __future__ import annotations

from core.interfaces import JobSource
from registry import build_sources


def test_disabled_sources_not_built():
    cfg = {"sources": {"telegram": {"enabled": False}, "linkedin": {"enabled": False},
                       "webboards": {"enabled": False}}}
    assert build_sources(cfg, secrets={}) == []


def test_telegram_built_when_enabled():
    cfg = {"sources": {"telegram": {"enabled": True}}}
    sources = build_sources(cfg, secrets={"session_name": "x"})
    assert [s.name for s in sources] == ["telegram"]
    assert sources[0].capabilities.can_apply is False


def test_stub_sources_built_when_enabled():
    cfg = {"sources": {"linkedin": {"enabled": True}, "webboards": {"enabled": True}}}
    names = {s.name for s in build_sources(cfg, secrets={})}
    assert names == {"linkedin", "webboards"}


def test_sources_conform_to_protocol():
    cfg = {"sources": {"telegram": {"enabled": True}, "linkedin": {"enabled": True},
                       "webboards": {"enabled": True}}}
    for s in build_sources(cfg, secrets={"session_name": "x"}):
        assert isinstance(s, JobSource)         # структурное соответствие интерфейсу
        assert s.capabilities.can_apply is False  # read-only по платформе
