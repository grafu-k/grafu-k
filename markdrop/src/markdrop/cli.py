"""Kommandozeile: markdrop-cli datei.pdf ordner/ -o ausgabe/"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from markdrop.converter import collect_files, combine, convert_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="markdrop-cli",
        description="Wandelt PDFs, PowerPoints, Word, Excel & Co. in Markdown um.",
    )
    parser.add_argument("paths", nargs="+", help="Dateien oder Ordner")
    parser.add_argument("-o", "--out-dir", type=Path, help="Zielordner (Standard: neben der Originaldatei)")
    parser.add_argument("--combine", type=Path, metavar="DATEI.md", help="Alles in EINE Markdown-Datei schreiben")
    parser.add_argument("--overwrite", action="store_true", help="Vorhandene .md-Dateien überschreiben")
    parser.add_argument("--stdout", action="store_true", help="Markdown auf stdout ausgeben statt Dateien zu schreiben")
    parser.add_argument("--no-header", action="store_true", help="Keinen Quell-Kommentar an den Anfang setzen")
    args = parser.parse_args(argv)

    files = collect_files(args.paths)
    if not files:
        print("Keine unterstützten Dateien gefunden.", file=sys.stderr)
        return 1

    write = not (args.stdout or args.combine)
    results = []
    for f in files:
        r = convert_file(f, args.out_dir, args.overwrite, write=write, add_source_header=not args.no_header)
        results.append(r)
        if r.ok:
            if write:
                print(f"✓ {f}  →  {r.output}", file=sys.stderr)
        else:
            print(f"✗ {f}: {r.error}", file=sys.stderr)

    if args.stdout:
        sys.stdout.write(combine(results) if len(results) > 1 else (results[0].markdown or ""))
    elif args.combine:
        args.combine.write_text(combine(results), encoding="utf-8")
        print(f"→ zusammengefasst in {args.combine}", file=sys.stderr)

    return 0 if all(r.ok for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
