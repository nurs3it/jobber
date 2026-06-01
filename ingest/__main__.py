"""CLI импорта резюме. Используется командой /onboard для извлечения текста.

Примеры:
  python -m ingest extract resume.pdf        # печатает извлечённый текст в stdout
  python -m ingest extract resume.docx

Для изображений лучший путь в Claude Code — зрение Claude (читает картинку напрямую).
Программный OCR-fallback требует extra `ocr` и системный tesseract.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ingest.cv_import import extract_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest", description="Импорт резюме Jobber")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Извлечь текст из резюме (pdf/docx/img/txt)")
    p_extract.add_argument("path", type=Path, help="Путь к файлу резюме")

    args = parser.parse_args(argv)

    if args.cmd == "extract":
        try:
            text = extract_text(args.path)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            return 1
        sys.stdout.write(text)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
