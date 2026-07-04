from pathlib import Path

from PySide6.QtCore import QThread, Signal

import downloader
import spotify


class CancelledError(Exception):
    pass


class DownloadWorker(QThread):
    progress = Signal(str, int, int)  # label, downloaded, total
    status = Signal(str, str, str)  # label, status (ok/error/cancelled), detail

    def __init__(
        self,
        url: str,
        output_dir: Path,
        fmt: str,
        label: str = "",
        filename: str | None = None,
        metadata: dict | None = None,
        info: dict | None = None,
    ):
        super().__init__()
        self._url = url
        self._output_dir = output_dir
        self._fmt = fmt
        self._label = label
        self._filename = filename
        self._metadata = metadata
        self._info = info

    def run(self):
        worker = self

        def progress_hook(d):
            if worker.isInterruptionRequested():
                raise CancelledError("Cancellato")
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    worker.progress.emit(worker._label, downloaded, total)
            elif d["status"] == "finished":
                worker.progress.emit(worker._label, 100, 100)

        try:
            downloader.download(
                self._url,
                self._output_dir,
                self._fmt,
                progress_hook=progress_hook,
                filename=self._filename,
                metadata=self._metadata,
                info=self._info,
            )
        except CancelledError:
            self.status.emit(self._label, "cancelled", "annullato")
        except Exception as e:
            self.status.emit(self._label, "error", str(e))
        else:
            self.status.emit(self._label, "ok", "")


class SpotifyPipelineWorker(QThread):
    tracks_found = Signal(list)  # list of spotdl Song objects
    search_progress = Signal(str, str, str)  # label, status (matched/skip/error), detail
    searches_done = Signal(list)  # list of (song, yt_url, label, metadata dict)

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def run(self):
        try:
            songs = spotify.fetch_tracks(self._url)
        except Exception as e:
            self.search_progress.emit("", "fetch_error", str(e))
            return

        if not songs:
            self.search_progress.emit("", "fetch_error", "Nessuna traccia trovata.")
            return

        self.tracks_found.emit(songs)

        results = []
        for song in songs:
            artist = ", ".join(song.artists) if song.artists else song.artist
            label = f"{artist} - {song.name}"

            try:
                yt = spotify.youtube_url(song)
            except Exception as e:
                self.search_progress.emit(label, "error", f"ricerca YouTube: {e}")
                continue

            if not yt:
                self.search_progress.emit(label, "skip", "nessun match YouTube")
                continue

            metadata = spotify.track_metadata(song)
            results.append((song, yt, label, metadata))
            self.search_progress.emit(label, "matched", yt)

        self.searches_done.emit(results)
