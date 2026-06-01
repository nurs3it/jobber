"""Гарантирует, что корень репозитория есть в sys.path при сборе тестов.

Top-level модули (registry.py, pipeline.py) и пакеты (storage, core, ...) импортируются
напрямую из корня. Console-script `pytest` (как в CI) не добавляет cwd в sys.path, а editable
pip-установка может не экспонировать top-level модули — этот conftest решает обе проблемы.
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
