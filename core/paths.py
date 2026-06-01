"""Пути Jobber: разделяем КОД пакета и пользовательские ДАННЫЕ.

- `PACKAGE_ROOT` — где лежит установленный код (репозиторий/npm-пакет). Только для чтения
  упакованных дефолтов (шаблон config.yaml, cv.md.template).
- `JOBBER_HOME` — где живут пользовательские данные: config.yaml, .env, сессия, vault, storage,
  profile/cv.md. По умолчанию `~/.jobber`, переопределяется переменной окружения `JOBBER_HOME`.

Такое разделение позволяет ставить Jobber глобально (npm/yarn) и держать данные отдельно от кода.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def jobber_home() -> Path:
    """Каталог пользовательских данных (по умолчанию ~/.jobber)."""
    env = os.environ.get("JOBBER_HOME")
    return Path(env).expanduser() if env else Path.home() / ".jobber"


def config_path() -> Path:
    """Путь к config.yaml: из JOBBER_HOME, с откатом на упакованный дефолт (для dev/тестов)."""
    home_cfg = jobber_home() / "config.yaml"
    return home_cfg if home_cfg.exists() else PACKAGE_ROOT / "config.yaml"


def env_path() -> Path:
    """Путь к .env: из JOBBER_HOME, с откатом на репозиторий (для dev)."""
    home_env = jobber_home() / ".env"
    if home_env.exists():
        return home_env
    repo_env = PACKAGE_ROOT / ".env"
    return repo_env if repo_env.exists() else home_env


def data_dir(*parts: str) -> Path:
    """Подкаталог пользовательских данных внутри JOBBER_HOME."""
    return jobber_home().joinpath(*parts)
