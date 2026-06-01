"""Смоук-тесты MCP-сервера: импорт, регистрация инструментов, write_digest/sources/get_profile.

Telegram-I/O (scan_candidates) тут не дёргаем — он требует реальной сессии; покрыт через
collect_candidates в test_candidates.py / test_pipeline.py.
"""

from __future__ import annotations

import asyncio

from mcp_server import server


def test_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert {"sources", "get_profile", "scan_candidates", "write_digest", "seen_reset"} <= names


def test_sources_tool_lists_capabilities():
    out = server.sources()
    by_name = {s["name"]: s for s in out}
    assert by_name["telegram"]["can_apply"] is False
    assert by_name["telegram"]["can_scan"] is True
    assert "linkedin" in by_name and "webboards" in by_name


def test_write_digest_writes_file(tmp_path, monkeypatch):
    cfg = {
        "digest": {
            "vault_path": str(tmp_path / "vault"),
            "subfolder": "Jobber",
            "filename_format": "%Y-%m-%d-jobber.md",
            "dedup_similarity": 0.85,
        }
    }
    monkeypatch.setattr(server, "load_config", lambda: cfg)

    items = [{
        "title": "Frontend Developer", "company": "Acme",
        "link": "https://t.me/jobs/55", "score": 82, "reason": "React",
        "contact": {"username": "hr_anna"}, "cover_letter": "Привет! Заинтересовала вакансия.",
        "dialog_title": "Jobs", "text": "Ищем Frontend",
    }]
    res = server.write_digest(items, date="2026-06-01")
    assert res["count"] == 1
    from pathlib import Path
    p = Path(res["path"])
    assert p.exists() and p.name == "2026-06-01-jobber.md"
    content = p.read_text(encoding="utf-8")
    assert "Frontend Developer" in content
    assert "@hr_anna" in content
    assert "Привет! Заинтересовала" in content


def test_write_digest_empty_not_blank(tmp_path, monkeypatch):
    cfg = {"digest": {"vault_path": str(tmp_path / "v"), "subfolder": "Jobber",
                      "filename_format": "%Y-%m-%d-jobber.md", "dedup_similarity": 0.85}}
    monkeypatch.setattr(server, "load_config", lambda: cfg)
    res = server.write_digest([], date="2026-06-01")
    from pathlib import Path
    assert Path(res["path"]).read_text(encoding="utf-8").strip() != ""
