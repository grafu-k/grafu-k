#!/usr/bin/env bash
# Baut dist/Markdrop.app (und optional ein DMG). Auf einem Mac ausführen.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
if [ ! -d .venv ]; then
  "$PYTHON" -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

rm -rf build dist
pyinstaller --noconfirm markdrop.spec

# Ad-hoc-Signatur, damit macOS die App lokal ohne Murren startet
codesign --force --deep --sign - dist/Markdrop.app || true

if [ "${1:-}" = "--dmg" ]; then
  hdiutil create -volname Markdrop -srcfolder dist/Markdrop.app -ov -format UDZO dist/Markdrop.dmg
  echo "DMG: dist/Markdrop.dmg"
fi

echo ""
echo "Fertig: dist/Markdrop.app"
echo "Installieren:  cp -R dist/Markdrop.app /Applications/"
