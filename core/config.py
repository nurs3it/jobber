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

from core.paths import PACKAGE_ROOT, config_path, env_path, jobber_home

# Обратная совместимость: ROOT раньше указывал на корень кода.
ROOT = PACKAGE_ROOT
CONFIG_PATH = config_path()


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Прочитать config.yaml в dict (из JOBBER_HOME, иначе упакованный дефолт)."""
    path = path or config_path()
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_secrets() -> dict[str, str | None]:
    """Прочитать секреты из .env. НЕ логировать возвращаемое значение."""
    load_dotenv(env_path())
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
    path = Path(path) if path is not None else jobber_home() / ".env"
    path.parent.mkdir(parents=True, exist_ok=True)
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
    """Абсолютный путь к подпапке дайджеста внутри Obsidian vault.

    Относительный vault_path резолвится относительно JOBBER_HOME (пользовательские данные).
    """
    digest = config.get("digest", {})
    base = Path(digest.get("vault_path", "./vault"))
    if not base.is_absolute():
        base = jobber_home() / base
    return base / digest.get("subfolder", "Jobber")
