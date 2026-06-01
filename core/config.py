"""Загрузчик конфигурации: config.yaml + .env.

Единственная точка чтения настроек. Остальной код берёт конфиг отсюда, а не парсит YAML сам.
Секреты приходят из .env (через python-dotenv), настройки поведения — из config.yaml.

ИНВАРИАНТ: секреты (TG_API_HASH, сессия) никогда не логируются и не попадают в дайджест.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Прочитать config.yaml в dict."""
    path = path or CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_secrets() -> dict[str, str | None]:
    """Прочитать секреты из .env. НЕ логировать возвращаемое значение."""
    load_dotenv(ROOT / ".env")
    return {
        "api_id": os.getenv("TG_API_ID"),
        "api_hash": os.getenv("TG_API_HASH"),
        "phone": os.getenv("TG_PHONE"),
        "session_name": os.getenv("TG_SESSION_NAME", "jobber"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
    }


def update_env(updates: dict[str, str], path: Path | None = None) -> Path:
    """Записать/обновить ключи в .env, сохраняя остальные строки и комментарии.

    Существующие ключи обновляются на месте; новые — дописываются в конец.
    Создаёт файл, если его нет. Возвращает путь.

    ⚠️ Значения — секреты. Не логировать содержимое и не печатать в чат.
    """
    path = Path(path) if path is not None else ROOT / ".env"
    remaining = dict(updates)

    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)

    for key, value in remaining.items():
        out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def vault_dir(config: dict[str, Any]) -> Path:
    """Абсолютный путь к подпапке дайджеста внутри Obsidian vault."""
    digest = config.get("digest", {})
    base = Path(digest.get("vault_path", "./vault"))
    if not base.is_absolute():
        base = ROOT / base
    return base / digest.get("subfolder", "Jobber")
