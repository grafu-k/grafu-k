"""Konvertierungs-Kern: wandelt Dateien mit Microsofts MarkItDown in Markdown um.

Dieses Modul hat keine GUI-Abhängigkeiten, damit es auch von der CLI und den
Tests genutzt werden kann.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

# Formate, die MarkItDown zuverlässig versteht.
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".pptx",
        ".docx",
        ".xlsx",
        ".xls",
        ".csv",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".txt",
        ".epub",
        ".ipynb",
        ".msg",
        ".zip",
    }
)

# Alte Binärformate, die MarkItDown NICHT kann – wir geben einen hilfreichen Hinweis.
LEGACY_HINTS: dict[str, str] = {
    ".ppt": "Altes PowerPoint-Format (.ppt) – bitte in PowerPoint/Keynote als .pptx speichern.",
    ".doc": "Altes Word-Format (.doc) – bitte in Word/Pages als .docx speichern.",
    ".key": "Keynote-Datei – bitte in Keynote als .pptx oder .pdf exportieren.",
    ".pages": "Pages-Datei – bitte in Pages als .docx oder .pdf exportieren.",
    ".numbers": "Numbers-Datei – bitte in Numbers als .xlsx oder .csv exportieren.",
    ".md": "Ist bereits Markdown – übersprungen.",
}


@dataclass
class ConversionResult:
    source: Path
    output: Path | None = None
    markdown: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


_markitdown = None


def _get_markitdown():
    """MarkItDown wird erst beim ersten Gebrauch geladen (schnellerer App-Start)."""
    global _markitdown
    if _markitdown is None:
        from markitdown import MarkItDown

        _markitdown = MarkItDown(enable_plugins=False)
    return _markitdown


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def collect_files(paths: Iterable[str | os.PathLike]) -> list[Path]:
    """Expandiert Ordner rekursiv und liefert alle Dateien (ohne versteckte)."""
    result: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw).expanduser()
        candidates: Iterator[Path]
        if p.is_dir():
            candidates = (
                f
                for f in sorted(p.rglob("*"))
                if f.is_file() and not any(part.startswith(".") for part in f.relative_to(p).parts)
            )
        else:
            candidates = iter([p])
        for f in candidates:
            ext = f.suffix.lower()
            if p.is_dir() and ext not in SUPPORTED_EXTENSIONS and (ext not in LEGACY_HINTS or ext == ".md"):
                continue  # unbekannte Dateien und vorhandenes Markdown in Ordnern still überspringen
            key = f.resolve()
            if key not in seen:
                seen.add(key)
                result.append(f)
    return result


def unique_path(path: Path) -> Path:
    """Hängt (2), (3), … an, falls die Datei schon existiert."""
    if not path.exists():
        return path
    i = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def output_path_for(source: Path, out_dir: Path | None = None, overwrite: bool = False) -> Path:
    target_dir = out_dir if out_dir is not None else source.parent
    name = source.name + ".md" if source.suffix.lower() == ".md" else source.stem + ".md"
    target = target_dir / name
    return target if overwrite else unique_path(target)


def convert_to_markdown(source: Path, add_source_header: bool = True) -> str:
    """Konvertiert eine einzelne Datei und liefert den Markdown-Text."""
    source = Path(source)
    ext = source.suffix.lower()
    if not source.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {source}")
    if ext in LEGACY_HINTS:
        raise ValueError(LEGACY_HINTS[ext])
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Format '{ext or 'ohne Endung'}' wird nicht unterstützt.")

    result = _get_markitdown().convert(str(source))
    text = result.text_content or ""
    if ext == ".pdf":
        text = clean_pdf_text(text)
    text = text.strip()
    if not text:
        raise ValueError(
            "Kein Text gefunden. Handelt es sich um ein gescanntes PDF (nur Bilder)? "
            "Dann vorher eine Texterkennung (OCR) durchführen, z. B. in Vorschau oder Acrobat."
        )
    if add_source_header:
        text = f"<!-- Quelle: {source.name} -->\n\n{text}"
    return text + "\n"


_PAGE_NUMBER = re.compile(r"^(seite\s*)?\d{1,4}(\s*(/|von)\s*\d{1,4})?$", re.IGNORECASE)


def clean_pdf_text(text: str) -> str:
    """Macht PDF-Text LLM-freundlicher.

    - Seitenumbrüche (Form-Feed) werden zu sichtbaren Seitenmarken (``## Seite N``),
      damit sich ein LLM auf konkrete Seiten/Folien beziehen kann.
    - Kopf-/Fußzeilen, die sich auf den meisten Seiten wiederholen (Vortragstitel,
      Autor, …), werden entfernt – sie kosten nur Tokens.
    - Reine Seitenzahlen am Seitenanfang oder -ende werden entfernt.
    """
    pages = [pg for pg in text.split("\f")]
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) < 2:
        return text.replace("\f", "\n")

    # Zeilen finden, die auf mindestens 60 % der Seiten vorkommen (Kopf-/Fußzeilen).
    repeated: set[str] = set()
    if len(pages) >= 4:
        counts: Counter[str] = Counter()
        for pg in pages:
            counts.update({ln.strip() for ln in pg.splitlines() if len(ln.strip()) > 3})
        repeated = {ln for ln, n in counts.items() if n >= 0.6 * len(pages)}

    out: list[str] = []
    for number, pg in enumerate(pages, start=1):
        lines = [ln for ln in pg.splitlines() if ln.strip() not in repeated]
        # Seitenzahlen am Anfang/Ende entfernen (Leerzeilen überspringen)
        for idx in (-1, 0):
            content = [i for i, ln in enumerate(lines) if ln.strip()]
            if content and _PAGE_NUMBER.match(lines[content[idx]].strip()):
                del lines[content[idx]]
        body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        out.append(f"## Seite {number}\n\n{body}" if body else f"## Seite {number}\n\n*(keine Textinhalte)*")
    return "\n\n".join(out)


def convert_file(
    source: Path,
    out_dir: Path | None = None,
    overwrite: bool = False,
    write: bool = True,
    add_source_header: bool = True,
) -> ConversionResult:
    """Konvertiert eine Datei und schreibt (optional) die .md-Datei. Wirft nie."""
    source = Path(source)
    res = ConversionResult(source=source)
    try:
        res.markdown = convert_to_markdown(source, add_source_header=add_source_header)
        if write:
            if out_dir is not None:
                out_dir.mkdir(parents=True, exist_ok=True)
            res.output = output_path_for(source, out_dir, overwrite)
            res.output.write_text(res.markdown, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 – Fehler werden dem Nutzer angezeigt
        res.error = str(exc) or exc.__class__.__name__
    return res


def combine(results: Iterable[ConversionResult]) -> str:
    """Fasst mehrere Ergebnisse zu einem einzigen Markdown-Dokument zusammen."""
    parts = []
    for r in results:
        if r.ok:
            parts.append(f"# {r.source.name}\n\n{r.markdown.strip()}\n")
    return "\n---\n\n".join(parts)
