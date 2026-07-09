import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from . import downloader, spotify
from .workers import DownloadWorker, SpotifyPipelineWorker

MAX_WORKERS = 4
DEFAULT_OUTPUT = Path.home() / "Music" / "zenradeConverter"
FORMATS = ["mp3", "flac", "m4a"]


@dataclass
class DownloadJob:
    label: str
    url: str
    fmt: str
    directory: Path
    filename: str | None = None
    metadata: dict | None = None
    info: dict | None = None


def _format_bytes(b: int) -> str:
    if b >= 1024 * 1024:
        return f"{b / 1024 / 1024:.1f} MB"
    elif b >= 1024:
        return f"{b / 1024:.0f} KB"
    return f"{b} B"


class DownloadRow(QFrame):
    cancelled = Signal()

    def __init__(self, label: str):
        super().__init__()
        self._label = label

        self.setFrameStyle(QFrame.StyledPanel)
        self.setMaximumHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._icon = QLabel("▷")
        self._icon.setFixedWidth(24)
        self._icon.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(self._icon)

        self._name = QLabel(label)
        self._name.setMinimumWidth(140)
        self._name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._name.setWordWrap(True)
        layout.addWidget(self._name)

        self._progress = QProgressBar()
        self._progress.setFixedWidth(180)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._size = QLabel("")
        self._size.setFixedWidth(110)
        self._size.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._size)

        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setFixedSize(26, 26)
        self._cancel_btn.setToolTip("Annulla")
        self._cancel_btn.clicked.connect(self.cancelled.emit)
        self._cancel_btn.setVisible(False)
        layout.addWidget(self._cancel_btn)

    def set_status(self, status: str, detail: str = ""):
        icons = {
            "pending": "▷",
            "downloading": "↓",
            "ok": "✓",
            "error": "✗",
            "skip": "⊘",
            "cancelled": "⏸",
        }
        self._icon.setText(icons.get(status, "?"))

        colors = {
            "pending": "gray",
            "downloading": "#2196F3",
            "ok": "#4CAF50",
            "error": "#F44336",
            "skip": "#FF9800",
            "cancelled": "#9E9E9E",
        }
        color = colors.get(status, "gray")
        self._icon.setStyleSheet(f"font-size: 14px; color: {color};")

        if status == "downloading":
            self._progress.setVisible(True)
            self._cancel_btn.setVisible(True)
            self._name.setStyleSheet(f"color: {color};")
        elif status in ("error", "skip", "cancelled"):
            self._progress.setVisible(False)
            self._cancel_btn.setVisible(False)
            self._name.setToolTip(detail)
            self._size.setText(detail)
        elif status == "ok":
            self._progress.setVisible(False)
            self._cancel_btn.setVisible(False)
            self._size.setText("Completato")
        elif status == "pending":
            self._progress.setVisible(False)
            self._cancel_btn.setVisible(False)

    def set_progress(self, downloaded: int, total: int):
        if total:
            pct = int(downloaded / total * 100)
            self._progress.setValue(pct)
            self._size.setText(
                f"{_format_bytes(downloaded)} / {_format_bytes(total)}"
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._output_dir = DEFAULT_OUTPUT
        self._active = 0
        self._queue: list[DownloadJob] = []
        self._rows: dict[str, DownloadRow] = {}
        self._worker_for_row: dict[str, DownloadWorker] = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("zenradeConverter")
        self.resize(780, 520)
        self.setMinimumSize(550, 350)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── URL bar ──
        top = QHBoxLayout()
        top.setSpacing(8)

        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(FORMATS)
        self._fmt_combo.setCurrentText("mp3")
        self._fmt_combo.setFixedWidth(72)
        top.addWidget(self._fmt_combo)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("URL YouTube o Spotify...")
        self._url_input.returnPressed.connect(self._on_download)
        top.addWidget(self._url_input)

        self._dl_btn = QPushButton("Scarica")
        self._dl_btn.setDefault(True)
        self._dl_btn.clicked.connect(self._on_download)
        top.addWidget(self._dl_btn)

        root.addLayout(top)

        # ── Output dir ──
        odir = QHBoxLayout()
        odir.setSpacing(8)

        odir.addWidget(QLabel("Cartella:"))

        self._dir_input = QLineEdit(str(self._output_dir))
        self._dir_input.textChanged.connect(self._on_dir_changed)
        odir.addWidget(self._dir_input)

        browse = QPushButton("Sfoglia")
        browse.clicked.connect(self._on_browse_dir)
        odir.addWidget(browse)

        open_btn = QPushButton("Apri cartella")
        open_btn.clicked.connect(self._on_open_dir)
        odir.addWidget(open_btn)

        root.addLayout(odir)

        # ── Track list ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameStyle(QFrame.NoFrame)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll, stretch=1)

        # ── Status bar ──
        self._status = QStatusBar()
        self._status.showMessage("Pronto")
        self.setStatusBar(self._status)

    # ── Helpers ──

    def _add_row(self, label: str) -> DownloadRow:
        row = DownloadRow(label)
        self._list_layout.insertWidget(self._list_layout.count() - 1, row)
        return row

    def _enqueue(self, job: DownloadJob) -> DownloadRow:
        row = self._add_row(job.label)
        self._rows[job.label] = row
        self._queue.append(job)
        self._process_queue()
        return row

    def _process_queue(self):
        while self._active < MAX_WORKERS and self._queue:
            job = self._queue.pop(0)
            row = self._rows.get(job.label)

            worker = DownloadWorker(
                job.url, job.directory, job.fmt,
                label=job.label,
                filename=job.filename,
                metadata=job.metadata,
                info=job.info,
            )
            worker.progress.connect(self._on_progress)
            worker.status.connect(self._on_download_status)
            worker.finished.connect(self._on_worker_done)

            if row:
                row.cancelled.connect(worker.requestInterruption)
                row.set_status("downloading")

            self._worker_for_row[job.label] = worker
            self._active += 1
            worker.start()

    def _update_status_bar(self):
        if self._active > 0:
            self._status.showMessage(
                f"{self._active} download in corso  |  "
                f"{len(self._queue)} in coda"
            )
        else:
            self._status.showMessage("Pronto")

    # ── Slots ──

    def _on_dir_changed(self, text: str):
        self._output_dir = Path(text).expanduser()

    def _on_browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Cartella output", str(self._output_dir))
        if path:
            self._output_dir = Path(path)
            self._dir_input.setText(path)

    def _on_open_dir(self):
        self._output_dir.mkdir(parents=True, exist_ok=True)
        import subprocess
        subprocess.Popen(["open", str(self._output_dir)])

    def _on_download(self):
        url = self._url_input.text().strip()
        if not url:
            return

        fmt = self._fmt_combo.currentText()
        output_dir = self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        self._url_input.clear()

        if spotify.is_spotify_url(url):
            self._start_spotify(url, output_dir, fmt)
        else:
            self._start_youtube(url, output_dir, fmt)

    def _start_youtube(self, url: str, output_dir: Path, fmt: str):
        self._dl_btn.setEnabled(False)
        self._status.showMessage("Recupero info...")

        try:
            info = downloader.get_info(url)
        except Exception as e:
            self._status.showMessage(f"Errore: {e}")
            self._dl_btn.setEnabled(True)
            return

        title = info.get("title", "Sconosciuto")
        self._enqueue(DownloadJob(title, url, fmt, output_dir, info=info))
        self._dl_btn.setEnabled(True)
        self._update_status_bar()

    def _start_spotify(self, url: str, output_dir: Path, fmt: str):
        self._dl_btn.setEnabled(False)
        self._status.showMessage("Recupero tracce da Spotify...")

        self._spotify_fmt = fmt
        self._spotify_dir = output_dir

        self._pipeline = SpotifyPipelineWorker(url)
        self._pipeline.tracks_found.connect(self._on_tracks_found)
        self._pipeline.search_progress.connect(self._on_search_progress)
        self._pipeline.searches_done.connect(self._on_searches_done)
        self._pipeline.finished.connect(lambda: None)
        self._pipeline.start()

    def _on_tracks_found(self, songs: list):
        self._status.showMessage(
            f"Trovate {len(songs)} tracce — cerco su YouTube Music..."
        )

    def _on_search_progress(self, label: str, status: str, detail: str):
        if status == "matched":
            self._status.showMessage(
                f"Match trovati: {len(self._rows) + 1}"
            )
        elif status in ("error", "skip"):
            row = self._add_row(label)
            row.set_status(status, detail)
            self._rows[label] = row
        elif status == "fetch_error":
            self._status.showMessage(f"Errore Spotify: {detail}")
            self._dl_btn.setEnabled(True)

    def _on_searches_done(self, results: list):
        self._dl_btn.setEnabled(True)

        final_dir = self._spotify_dir
        if self._pipeline.collection_folder:
            final_dir = self._spotify_dir / self._pipeline.collection_folder
            final_dir.mkdir(parents=True, exist_ok=True)

        for _song, yt_url, label, metadata in results:
            self._enqueue(DownloadJob(label, yt_url, self._spotify_fmt, final_dir, filename=label, metadata=metadata))

        self._update_status_bar()

    def _on_progress(self, label: str, downloaded: int, total: int):
        row = self._rows.get(label)
        if row:
            row.set_progress(downloaded, total)

    def _on_download_status(self, label: str, status: str, detail: str):
        row = self._rows.get(label)
        if row:
            row.set_status(status, detail)

    def _on_worker_done(self):
        self._active -= 1
        self._process_queue()
        self._update_status_bar()


def run_gui():
    app = QApplication(sys.argv)
    app.setApplicationName("zenradeConverter")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
