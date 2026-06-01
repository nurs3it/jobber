"""Смоук-тесты каркаса (Фаза 0). Без внешних зависимостей.

Проверяют, что структура проекта на месте и config.yaml парсится.
Доменные тесты (ядро, предфильтр, маппинг, импорт CV) появятся в Фазах 1–5.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_key_paths_exist():
    expected = [
        "config.yaml",
        ".env.example",
        ".gitignore",
        "pyproject.toml",
        "registry.py",
        "core/models.py",
        "core/interfaces.py",
        "core/config.py",
        "ingest/cv_import.py",
        "sources/telegram/source.py",
        "sources/linkedin/source.py",
        "sources/webboards/source.py",
        "matching/prefilter.py",
        "matching/classifier.py",
        "cover/generator.py",
        "digest/dedup.py",
        "digest/render.py",
        "storage/store.py",
        "mcp_server/server.py",
        "profile/cv.md.template",
        "scripts/install.sh",
    ]
    missing = [p for p in expected if not (ROOT / p).exists()]
    assert not missing, f"Отсутствуют файлы каркаса: {missing}"


def test_claude_docs_exist():
    docs = ["setup", "architecture", "adding-a-source", "runbook", "security", "troubleshooting"]
    missing = [d for d in docs if not (ROOT / ".claude" / "docs" / f"{d}.md").exists()]
    assert not missing, f"Отсутствуют доки: {missing}"


def test_commands_exist():
    cmds = ["onboard", "scan", "digest", "cover", "profile-edit", "sources", "seen-reset"]
    missing = [c for c in cmds if not (ROOT / ".claude" / "commands" / f"{c}.md").exists()]
    assert not missing, f"Отсутствуют команды: {missing}"


def test_config_parses():
    yaml = pytest.importorskip("yaml")  # пропустить, если pyyaml ещё не установлен
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    for key in ("sources", "prefilter", "scoring", "filters", "cover_letter", "digest"):
        assert key in cfg, f"В config.yaml нет секции {key}"
