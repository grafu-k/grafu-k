"""Markdrop – Desktop-App (PySide6/Qt).

Dateien oder Ordner ins Fenster (oder aufs Dock-Symbol) ziehen → daneben
liegt eine .md-Datei. Fertige Markdown-Dateien lassen sich aus der Liste
direkt wieder herausziehen, z. B. in ein Chatfenster von Claude oder ChatGPT.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QMimeData, QSettings, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QFont, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from markdrop import __version__
from markdrop.converter import (
    SUPPORTED_EXTENSIONS,
    ConversionResult,
    collect_files,
    combine,
    convert_file,
    unique_path,
)

IS_MAC = sys.platform == "darwin"
ROLE_RESULT = Qt.ItemDataRole.UserRole


# --------------------------------------------------------------------------- Worker
class ConvertWorker(QThread):
    progress = Signal(int, int, str)  # aktuell, gesamt, Dateiname
    file_done = Signal(object)  # ConversionResult
    all_done = Signal(object, object)  # list[ConversionResult], Path | None (Sammeldatei)

    def __init__(self, files: list[Path], out_dir: Path | None, combine_all: bool, add_header: bool):
        super().__init__()
        self.files = files
        self.out_dir = out_dir
        self.combine_all = combine_all
        self.add_header = add_header

    def run(self) -> None:
        results: list[ConversionResult] = []
        total = len(self.files)
        for i, f in enumerate(self.files, start=1):
            self.progress.emit(i, total, f.name)
            r = convert_file(f, self.out_dir, write=not self.combine_all, add_source_header=self.add_header)
            results.append(r)
            self.file_done.emit(r)

        combined_path: Path | None = None
        if self.combine_all and any(r.ok for r in results):
            target_dir = self.out_dir or results[0].source.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d %H-%M")
            combined_path = unique_path(target_dir / f"Markdrop {stamp}.md")
            combined_path.write_text(combine(results), encoding="utf-8")
        self.all_done.emit(results, combined_path)


# --------------------------------------------------------------------------- Widgets
class DropZone(QFrame):
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropZone")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(190)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("⬇︎")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setObjectName("dropIcon")
        title = QLabel("Dateien oder Ordner hierher ziehen")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("dropTitle")
        exts = " · ".join(sorted(e.lstrip(".").upper() for e in SUPPORTED_EXTENSIONS - {".md", ".htm", ".txt"}))
        sub = QLabel(f"oder klicken zum Auswählen\n{exts}")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("dropSub")
        sub.setWordWrap(True)
        for w in (icon, title, sub):
            layout.addWidget(w)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class ResultList(QListWidget):
    """Liste der Ergebnisse – fertige .md-Dateien können herausgezogen werden."""

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setAlternatingRowColors(True)

    def mimeData(self, items):  # noqa: N802
        urls, texts = [], []
        for item in items:
            r: ConversionResult | None = item.data(ROLE_RESULT)
            if r and r.ok:
                if r.output:
                    urls.append(QUrl.fromLocalFile(str(r.output)))
                texts.append(r.markdown)
        mime = QMimeData()
        if urls:
            mime.setUrls(urls)
        if texts:
            mime.setText("\n\n---\n\n".join(texts))
        return mime


# --------------------------------------------------------------------------- Hauptfenster
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Markdrop")
        self.resize(640, 640)
        self.setAcceptDrops(True)
        self.settings = QSettings("Markdrop", "Markdrop")
        self.worker: ConvertWorker | None = None
        self.queue: list[Path] = []
        self.last_markdown: str = ""

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)
        self.setCentralWidget(central)

        # Drop-Zone
        self.drop_zone = DropZone()
        self.drop_zone.clicked.connect(self.choose_files)
        root.addWidget(self.drop_zone)

        # Optionen
        opts = QHBoxLayout()
        opts.addWidget(QLabel("Speichern:"))
        self.target_combo = QComboBox()
        self.target_combo.addItem("Neben der Originaldatei", None)
        self.target_combo.addItem("Ordner wählen …", "__choose__")
        saved_dir = self.settings.value("out_dir", "", str)
        if saved_dir and Path(saved_dir).is_dir():
            self._add_dir_to_combo(Path(saved_dir))
        self.target_combo.activated.connect(self._target_changed)
        opts.addWidget(self.target_combo, 1)
        root.addLayout(opts)

        checks = QHBoxLayout()
        self.combine_check = QCheckBox("Alles in eine Datei")
        self.combine_check.setToolTip("Alle Dokumente in EINE Markdown-Datei – praktisch zum Hochladen in ein LLM.")
        self.clipboard_check = QCheckBox("In Zwischenablage kopieren")
        self.clipboard_check.setToolTip("Das Ergebnis automatisch in die Zwischenablage legen.")
        self.header_check = QCheckBox("Quellname einfügen")
        self.header_check.setToolTip("Setzt einen Kommentar mit dem Original-Dateinamen an den Anfang.")
        for chk, key, default in (
            (self.combine_check, "combine", False),
            (self.clipboard_check, "clipboard", False),
            (self.header_check, "header", True),
        ):
            chk.setChecked(self.settings.value(key, default, bool))
            chk.toggled.connect(lambda v, k=key: self.settings.setValue(k, v))
            checks.addWidget(chk)
        checks.addStretch(1)
        root.addLayout(checks)

        # Fortschritt
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.hide()
        root.addWidget(self.progress)
        self.status = QLabel("Bereit.")
        self.status.setObjectName("status")
        root.addWidget(self.status)

        # Ergebnisse
        self.list = ResultList()
        self.list.itemDoubleClicked.connect(self._open_item)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        root.addWidget(self.list, 1)

        hint = QLabel("Tipp: Doppelklick öffnet die Datei. Einträge lassen sich direkt in ein Chatfenster ziehen.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # Buttons
        buttons = QHBoxLayout()
        self.copy_btn = QPushButton("Markdown kopieren")
        self.copy_btn.clicked.connect(self.copy_selected)
        self.reveal_btn = QPushButton("Im Finder zeigen" if IS_MAC else "Ordner öffnen")
        self.reveal_btn.clicked.connect(self.reveal_selected)
        clear_btn = QPushButton("Liste leeren")
        clear_btn.clicked.connect(self.list.clear)
        buttons.addWidget(self.copy_btn)
        buttons.addWidget(self.reveal_btn)
        buttons.addStretch(1)
        buttons.addWidget(clear_btn)
        root.addLayout(buttons)

        self._build_menu()
        self._apply_style()

    # ------------------------------------------------------------------ Menü & Stil
    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Ablage")
        open_act = QAction("Dateien öffnen …", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self.choose_files)
        file_menu.addAction(open_act)
        copy_act = QAction("Markdown kopieren", self)
        copy_act.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_act.triggered.connect(self.copy_selected)
        file_menu.addAction(copy_act)
        about = QAction("Über Markdrop", self)
        about.setMenuRole(QAction.MenuRole.AboutRole)
        about.triggered.connect(
            lambda: self.status.setText(f"Markdrop {__version__} – basiert auf Microsoft MarkItDown.")
        )
        file_menu.addAction(about)

    def _apply_style(self) -> None:
        dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        accent = "#0A84FF" if dark else "#007AFF"
        border = "#5a5a5e" if dark else "#c7c7cc"
        zone_bg = "#2c2c2e" if dark else "#f5f5f7"
        muted = "#98989d" if dark else "#6e6e73"
        self.setStyleSheet(
            f"""
            #dropZone {{ border: 2px dashed {border}; border-radius: 16px; background: {zone_bg}; }}
            #dropZone[active="true"] {{ border-color: {accent}; background: {accent}22; }}
            #dropIcon {{ font-size: 40px; color: {accent}; }}
            #dropTitle {{ font-size: 18px; font-weight: 600; }}
            #dropSub, #hint, #status {{ color: {muted}; }}
            #dropSub {{ font-size: 11px; }}
            #hint {{ font-size: 11px; }}
            QProgressBar {{ border: none; border-radius: 3px; background: {zone_bg}; }}
            QProgressBar::chunk {{ border-radius: 3px; background: {accent}; }}
            QListWidget {{ border-radius: 8px; padding: 4px; }}
            """
        )

    # ------------------------------------------------------------------ Zielordner
    def _add_dir_to_combo(self, path: Path) -> None:
        idx = self.target_combo.findData(str(path))
        if idx < 0:
            self.target_combo.insertItem(1, f"📁 {path.name}", str(path))
            self.target_combo.setItemData(1, str(path), Qt.ItemDataRole.ToolTipRole)
            idx = 1
        self.target_combo.setCurrentIndex(idx)

    def _target_changed(self, index: int) -> None:
        data = self.target_combo.itemData(index)
        if data == "__choose__":
            folder = QFileDialog.getExistingDirectory(self, "Zielordner wählen")
            if folder:
                self._add_dir_to_combo(Path(folder))
                self.settings.setValue("out_dir", folder)
            else:
                self.target_combo.setCurrentIndex(0)
        elif data is None:
            self.settings.setValue("out_dir", "")
        else:
            self.settings.setValue("out_dir", data)

    def out_dir(self) -> Path | None:
        data = self.target_combo.currentData()
        return Path(data) if data and data != "__choose__" else None

    # ------------------------------------------------------------------ Drag & Drop
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls() and event.source() is None:
            event.acceptProposedAction()
            self.drop_zone.set_active(True)

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.drop_zone.set_active(False)

    def dropEvent(self, event) -> None:  # noqa: N802
        self.drop_zone.set_active(False)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.enqueue(paths)

    def choose_files(self) -> None:
        patterns = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self, "Dateien auswählen", "", f"Dokumente ({patterns});;Alle Dateien (*)"
        )
        if files:
            self.enqueue(files)

    # ------------------------------------------------------------------ Konvertierung
    def enqueue(self, paths: list[str]) -> None:
        files = collect_files(paths)
        if not files:
            self.status.setText("Keine unterstützten Dateien gefunden.")
            return
        self.queue.extend(files)
        if self.worker is None:
            self._start_next()

    def _start_next(self) -> None:
        files, self.queue = self.queue, []
        self.progress.setRange(0, len(files))
        self.progress.setValue(0)
        self.progress.show()
        self.worker = ConvertWorker(
            files, self.out_dir(), self.combine_check.isChecked(), self.header_check.isChecked()
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.file_done.connect(self._on_file_done)
        self.worker.all_done.connect(self._on_all_done)
        self.worker.start()

    def _on_progress(self, current: int, total: int, name: str) -> None:
        self.progress.setValue(current - 1)
        self.status.setText(f"Wandle um ({current}/{total}): {name} …")

    def _on_file_done(self, r: ConversionResult) -> None:
        if r.ok:
            words = len(r.markdown.split())
            label = f"✅  {r.source.name}"
            label += f"  →  {r.output.name}" if r.output else ""
            label += f"   ({words:,} Wörter)".replace(",", ".")
            tooltip = str(r.output or r.source)
        else:
            label = f"⚠️  {r.source.name} – {r.error}"
            tooltip = r.error or ""
        item = QListWidgetItem(label)
        item.setData(ROLE_RESULT, r)
        item.setToolTip(tooltip)
        self.list.insertItem(0, item)

    def _on_all_done(self, results: list[ConversionResult], combined: Path | None) -> None:
        ok = [r for r in results if r.ok]
        failed = len(results) - len(ok)
        if combined:
            r = ConversionResult(source=combined, output=combined, markdown=combined.read_text("utf-8"))
            item = QListWidgetItem(f"📚  Sammeldatei: {combined.name}  ({len(ok)} Dokumente)")
            item.setData(ROLE_RESULT, r)
            item.setToolTip(str(combined))
            self.list.insertItem(0, item)
            self.last_markdown = r.markdown
        else:
            self.last_markdown = combine(ok) if len(ok) > 1 else (ok[0].markdown if ok else "")

        msg = f"Fertig: {len(ok)} umgewandelt"
        if failed:
            msg += f", {failed} fehlgeschlagen"
        if self.clipboard_check.isChecked() and self.last_markdown:
            QGuiApplication.clipboard().setText(self.last_markdown)
            msg += " – in die Zwischenablage kopiert"
        self.status.setText(msg + ".")
        self.progress.setValue(self.progress.maximum())
        self.list.setCurrentRow(0)

        self.worker.deleteLater()
        self.worker = None
        if self.queue:
            self._start_next()
        else:
            QTimer.singleShot(800, self.progress.hide)

    # ------------------------------------------------------------------ Aktionen
    def _selected_results(self) -> list[ConversionResult]:
        items = self.list.selectedItems() or ([self.list.item(0)] if self.list.count() else [])
        return [i.data(ROLE_RESULT) for i in items if i and i.data(ROLE_RESULT) and i.data(ROLE_RESULT).ok]

    def copy_selected(self) -> None:
        results = self._selected_results()
        if not results:
            self.status.setText("Nichts zum Kopieren ausgewählt.")
            return
        text = results[0].markdown if len(results) == 1 else combine(results)
        QGuiApplication.clipboard().setText(text)
        self.status.setText(f"{len(results)} Dokument(e) in die Zwischenablage kopiert.")

    def reveal_selected(self) -> None:
        results = self._selected_results()
        if results:
            self._reveal(results[0].output or results[0].source)

    def _reveal(self, path: Path) -> None:
        if IS_MAC:
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _open_item(self, item: QListWidgetItem) -> None:
        r: ConversionResult | None = item.data(ROLE_RESULT)
        if r and r.ok and r.output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(r.output)))

    def _context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        menu.addAction("Öffnen", lambda: self._open_item(item))
        menu.addAction("Markdown kopieren", self.copy_selected)
        menu.addAction("Im Finder zeigen" if IS_MAC else "Ordner öffnen", self.reveal_selected)
        menu.exec(self.list.mapToGlobal(pos))


# --------------------------------------------------------------------------- App
class MarkdropApp(QApplication):
    """Fängt macOS-„Öffnen mit …“ und Drops aufs Dock-Symbol ab."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.window: MainWindow | None = None
        self._pending: list[str] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)  # mehrere Dateien kommen als einzelne Events
        self._timer.timeout.connect(self._flush)

    def event(self, e) -> bool:  # noqa: A003
        if e.type() == QEvent.Type.FileOpen:
            self._pending.append(e.file())
            self._timer.start()
            return True
        return super().event(e)

    def _flush(self) -> None:
        if self.window and self._pending:
            paths, self._pending = self._pending, []
            self.window.enqueue(paths)
            self.window.raise_()
            self.window.activateWindow()


def main() -> None:
    app = MarkdropApp(sys.argv)
    app.setApplicationName("Markdrop")
    app.setApplicationDisplayName("Markdrop")
    if IS_MAC:
        app.setFont(QFont(".AppleSystemUIFont", 13))
    window = MainWindow()
    app.window = window
    window.show()
    # Dateien, die als Argumente übergeben wurden (z. B. beim Start aus dem Terminal)
    args = [a for a in sys.argv[1:] if not a.startswith("-") and Path(a).exists()]
    if args:
        window.enqueue(args)
    app._flush()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
