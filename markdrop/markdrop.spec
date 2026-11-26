# PyInstaller-Spezifikation für die macOS-App.  Bauen mit:  ./scripts/build_mac_app.sh
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("markitdown", "magika", "pdfminer", "pdfplumber", "pptx", "docx", "mammoth", "openpyxl", "xlrd", "olefile"):
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["src/markdrop/__main__.py"],
    pathex=["src"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick", "PySide6.QtQml"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Markdrop", console=False, argv_emulation=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Markdrop")

DOC_TYPES = {
    "PDF": ["pdf"],
    "PowerPoint": ["pptx"],
    "Word": ["docx"],
    "Excel": ["xlsx", "xls"],
    "Daten": ["csv", "json", "xml"],
    "Web": ["html", "htm"],
    "E-Book": ["epub"],
    "Weitere": ["txt", "ipynb", "msg", "zip", "md"],
}

app = BUNDLE(
    coll,
    name="Markdrop.app",
    icon="assets/Markdrop.icns" if __import__("os").path.exists("assets/Markdrop.icns") else None,
    bundle_identifier="com.markdrop.app",
    info_plist={
        "CFBundleName": "Markdrop",
        "CFBundleDisplayName": "Markdrop",
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # Dark Mode erlauben
        "LSMinimumSystemVersion": "12.0",
        # Erlaubt Drag & Drop aufs Dock-Symbol und „Öffnen mit → Markdrop“
        "CFBundleDocumentTypes": [
            {"CFBundleTypeName": name, "CFBundleTypeRole": "Viewer", "LSHandlerRank": "Alternate", "CFBundleTypeExtensions": exts}
            for name, exts in DOC_TYPES.items()
        ]
        + [{"CFBundleTypeName": "Ordner", "CFBundleTypeRole": "Viewer", "LSHandlerRank": "Alternate", "LSItemContentTypes": ["public.folder"]}],
    },
)
