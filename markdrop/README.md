# Markdrop

**Ziehen, ablegen, fertig: Dokumente werden zu Markdown, das LLMs gut lesen können.**

Markdrop ist eine kleine Mac-App. Du ziehst PDFs, PowerPoint-Folien, Word-Dokumente, Excel-Tabellen & Co. ins Fenster und bekommst daneben eine `.md`-Datei zurück. Die Datei kannst du direkt in Claude, ChatGPT oder ein anderes LLM hochladen oder einfügen.

Unter der Haube arbeitet [Microsoft MarkItDown](https://github.com/microsoft/markitdown). Die Umwandlung läuft **komplett lokal**, keine Datei verlässt deinen Mac.

## Funktionen

- **Drag & Drop**: einzelne Dateien, mehrere Dateien oder ganze Ordner (rekursiv)
- **Aufs Dock-Symbol ziehen** oder im Finder *Öffnen mit → Markdrop*
- **Zielordner**: neben der Originaldatei (Standard) oder in einem festen Ordner
- **Alles in eine Datei**: fasst mehrere Dokumente zu einer Sammeldatei zusammen (gut für ein einzelnes LLM-Upload)
- **Zwischenablage**: Ergebnis automatisch kopieren und mit ⌘V in den Chat einfügen
- **Wieder herausziehen**: Einträge aus der Ergebnisliste lassen sich direkt in ein Chatfenster ziehen
- Vorhandene Dateien werden nie überschrieben (`bericht (2).md`)
- Dark Mode, deutsche Oberfläche

### Unterstützte Formate

| Typ | Endungen |
| --- | --- |
| PDF | `.pdf` |
| PowerPoint | `.pptx` |
| Word | `.docx` |
| Excel | `.xlsx`, `.xls` |
| Daten | `.csv`, `.json`, `.xml` |
| Web | `.html`, `.htm` |
| Sonstiges | `.epub`, `.ipynb`, `.msg` (Outlook), `.zip`, `.txt` |

**Nicht unterstützt** sind alte Binärformate (`.ppt`, `.doc`) und Apple-Formate (`.key`, `.pages`, `.numbers`). Markdrop zeigt dann einen Hinweis, wie du die Datei vorher als `.pptx`, `.docx` oder `.pdf` exportierst.
**Gescannte PDFs** (nur Bilder, kein Text) brauchen vorher eine Texterkennung (OCR).

## Installation

### Variante A: fertige App (empfohlen)

1. Unter **Actions → „macOS-App bauen“** den letzten Lauf öffnen und das Artefakt **Markdrop-macOS** herunterladen. Bei einem Release mit Tag `v…` hängt die DMG auch unter **Releases**.
2. DMG öffnen und `Markdrop.app` in den Ordner **Programme** ziehen.
3. Beim ersten Start: **Rechtsklick auf die App → Öffnen**. Die App ist nicht von Apple notarisiert, deshalb fragt macOS einmal nach. Falls macOS meldet, die App sei „beschädigt“:
   ```bash
   xattr -dr com.apple.quarantine /Applications/Markdrop.app
   ```

### Variante B: selbst auf dem Mac bauen

Voraussetzung: Python 3.10 oder neuer (z. B. `brew install python`).

```bash
git clone https://github.com/<dein-name>/markdrop.git
```

```bash
cd markdrop
```

```bash
./scripts/build_mac_app.sh --dmg
```

```bash
cp -R dist/Markdrop.app /Applications/
```

### Variante C: ohne App-Bundle aus dem Quellcode starten

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

```bash
markdrop
```

## Kommandozeile

Mit dem Paket wird auch ein CLI installiert:

```bash
markdrop-cli praesentation.pptx bericht.pdf
```

```bash
markdrop-cli ~/Dokumente/Projekt -o ~/Desktop/markdown
```

```bash
markdrop-cli *.pdf --combine alles.md
```

```bash
markdrop-cli vertrag.docx --stdout | pbcopy
```

## Entwicklung

```bash
pip install -e ".[dev]"
```

```bash
pytest
```

Projektstruktur:

```
src/markdrop/
  converter.py   # Konvertierungs-Kern (ohne GUI), nutzt MarkItDown
  app.py         # Qt-Oberfläche (PySide6)
  cli.py         # Kommandozeile
tests/           # erzeugt echte PDF/PPTX/DOCX/XLSX-Dateien und prüft die Umwandlung
markdrop.spec    # PyInstaller-Konfiguration fürs .app-Bundle (inkl. Dock-Drop)
scripts/build_mac_app.sh
.github/workflows/build-macos.yml   # Tests + automatischer App-Build auf macOS
```

Ein eigenes App-Icon: `assets/Markdrop.icns` ablegen, der Build nimmt es automatisch.

## Lizenz

MIT
