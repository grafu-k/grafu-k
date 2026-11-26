"""Erzeugt echte Beispieldokumente und prüft die Umwandlung."""

from pathlib import Path

import pytest

from markdrop.cli import main as cli_main
from markdrop.converter import clean_pdf_text, collect_files, combine, convert_file


@pytest.fixture
def pptx_file(tmp_path: Path) -> Path:
    from pptx import Presentation

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Quartalszahlen"
    slide.placeholders[1].text = "Umsatz gestiegen"
    path = tmp_path / "folien.pptx"
    prs.save(path)
    return path


@pytest.fixture
def docx_file(tmp_path: Path) -> Path:
    import docx

    d = docx.Document()
    d.add_heading("Projektbericht", level=1)
    d.add_paragraph("Alles läuft nach Plan.")
    path = tmp_path / "bericht.docx"
    d.save(path)
    return path


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    from reportlab.pdfgen import canvas

    path = tmp_path / "dokument.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Hallo aus dem PDF")
    c.save()
    return path


@pytest.fixture
def xlsx_file(tmp_path: Path) -> Path:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Produkt", "Preis"])
    ws.append(["Apfel", 1.5])
    path = tmp_path / "tabelle.xlsx"
    wb.save(path)
    return path


def test_pptx(pptx_file: Path):
    r = convert_file(pptx_file)
    assert r.ok, r.error
    assert r.output == pptx_file.with_suffix(".md")
    text = r.output.read_text("utf-8")
    assert "Quartalszahlen" in text and "Umsatz gestiegen" in text
    assert text.startswith("<!-- Quelle: folien.pptx -->")


def test_docx(docx_file: Path):
    r = convert_file(docx_file)
    assert r.ok, r.error
    assert "# Projektbericht" in r.markdown


def test_pdf(pdf_file: Path):
    r = convert_file(pdf_file)
    assert r.ok, r.error
    assert "Hallo aus dem PDF" in r.markdown


def test_xlsx_table(xlsx_file: Path):
    r = convert_file(xlsx_file)
    assert r.ok, r.error
    assert "| Produkt | Preis |" in r.markdown


def test_out_dir_and_no_overwrite(docx_file: Path, tmp_path: Path):
    out = tmp_path / "ausgabe"
    first = convert_file(docx_file, out)
    second = convert_file(docx_file, out)
    assert first.output == out / "bericht.md"
    assert second.output == out / "bericht (2).md"


def test_legacy_format_gives_hint(tmp_path: Path):
    old = tmp_path / "alt.ppt"
    old.write_bytes(b"\xd0\xcf\x11\xe0")
    r = convert_file(old)
    assert not r.ok and ".pptx" in r.error


def test_collect_files_recurses_and_skips(tmp_path: Path, docx_file: Path, pptx_file: Path):
    sub = tmp_path / "unter"
    sub.mkdir()
    (sub / "notiz.pdf").write_bytes(b"")
    (tmp_path / "bild.png").write_bytes(b"")
    (tmp_path / "schon.md").write_text("x")
    (tmp_path / ".versteckt").mkdir()
    (tmp_path / ".versteckt" / "geheim.pdf").write_bytes(b"")
    names = {p.name for p in collect_files([tmp_path])}
    assert names == {"bericht.docx", "folien.pptx", "notiz.pdf"}


def test_markdown_input_is_skipped(tmp_path: Path):
    """Erneutes Reinziehen von .md-Dateien darf keine x.md.md-Ketten erzeugen."""
    src = tmp_path / "x.md"
    src.write_text("# schon Markdown")
    r = convert_file(src)
    assert not r.ok and "bereits Markdown" in r.error
    assert not (tmp_path / "x.md.md").exists()


def test_pdf_pages_and_repeated_footer(tmp_path: Path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "folien.pdf"
    c = canvas.Canvas(str(path))
    for i in range(1, 6):
        c.drawString(72, 720, f"Titel Folie {i}")
        c.drawString(72, 60, "VO Einfuehrung Fusszeile")
        c.drawString(500, 60, str(i + 1))
        c.showPage()
    c.save()
    r = convert_file(path, write=False)
    assert r.ok, r.error
    assert "## Seite 1" in r.markdown and "## Seite 5" in r.markdown
    assert "Titel Folie 3" in r.markdown
    assert "Fusszeile" not in r.markdown
    assert "\f" not in r.markdown
    assert "\n4\n" not in r.markdown  # Seitenzahl entfernt


def test_clean_pdf_text_keeps_single_page():
    assert clean_pdf_text("nur eine Seite") == "nur eine Seite"


def test_combine(docx_file: Path, pptx_file: Path):
    results = [convert_file(docx_file, write=False), convert_file(pptx_file, write=False)]
    text = combine(results)
    assert "# bericht.docx" in text and "# folien.pptx" in text and "\n---\n" in text


def test_cli_combine(docx_file: Path, pptx_file: Path, tmp_path: Path):
    target = tmp_path / "alles.md"
    assert cli_main([str(docx_file), str(pptx_file), "--combine", str(target)]) == 0
    assert "Projektbericht" in target.read_text("utf-8")
