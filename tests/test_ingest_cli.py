"""Тест CLI извлечения текста: `python -m ingest extract <file>` печатает текст в stdout."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_cli_extract_prints_text(tmp_path):
    cv = tmp_path / "cv.txt"
    cv.write_text("Иван — Frontend, React", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "ingest", "extract", str(cv)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert "Frontend" in result.stdout


def test_cli_extract_missing_file_nonzero(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "ingest", "extract", str(tmp_path / "nope.pdf")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode != 0
