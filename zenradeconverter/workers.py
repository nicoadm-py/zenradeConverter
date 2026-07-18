import re
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from . import downloader, spotify


class CancelledError(Exception):
    pass


class DownloadWorker(QThread):
    progress = Signal(int, int, int)     # row_id, downloaded, total
    status = Signal(int, str, str)        # row_id, status (ok/error/cancelled), detail

    def __init__(
        self,
        row_id: int,
        url: str,
        output_dir: Path,
        fmt: str,
        label: str = "",
        filename: str | None = None,
        metadata: dict | None = None,
        ffmpeg_location: str | None = None,
    ):
        super().__init__()
        self._row_id = row_id
        self._url = url
        self._output_dir = output_dir
        self._fmt = fmt
        self._label = label           # ancora utile per log/debug
        self._filename = filename
        self._metadata = metadata
        self._ffmpeg_location = ffmpeg_location

    def run(self):
        worker = self

        def progress_hook(d):
            if worker.isInterruptionRequested():
                raise CancelledError("Cancellato")
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    worker.progress.emit(worker._row_id, downloaded, total)
            elif d["status"] == "finished":
                worker.progress.emit(worker._row_id, 100, 100)

        try:
            downloader.download(
                self._url, self._output_dir, self._fmt,
                progress_hook=progress_hook,
                filename=self._filename,
                metadata=self._metadata,
                ffmpeg_location=self._ffmpeg_location,
            )
        except CancelledError:
            self.status.emit(self._row_id, "cancelled", "annullato")
        except Exception as e:
            self.status.emit(self._row_id, "error", str(e))
        else:
            self.status.emit(self._row_id, "ok", "")


class YouTubeInfoWorker(QThread):
    """Estrae metadati YouTube fuori dal thread GUI.

    Distingue singolo video vs playlist:
      - singolo  → emit info_ready(dict)
      - playlist → emit playlist_ready(list[(title, entry_url)])
    """
    info_ready = Signal(dict)
    playlist_ready = Signal(list)      # list[(title, url)]
    error = Signal(str)

    def __init__(self, url: str, ffmpeg_location: str | None = None):
        super().__init__()
        self._url = url
        self._ffmpeg_location = ffmpeg_location

    def run(self):
        try:
            info = downloader.get_info(self._url, ffmpeg_location=self._ffmpeg_location)
        except Exception as e:
            self.error.emit(str(e))
            return

        # yt-dlp marca le playlist con _type == "playlist"; per le playlist
        # twilight (singolo video in lista) entries può contenere un dict
        # principale invece di una lista — gestiamo entrambi.
        if isinstance(info, dict) and info.get("_type") == "playlist":
            entries = info.get("entries") or []
            flat = []
            for e in entries:
                if not e:
                    continue
                title = (e.get("title") or "Sconosciuto") if isinstance(e, dict) else "Sconosciuto"
                e_url = (e.get("url") or e.get("webpage_url")) if isinstance(e, dict) else None
                if not e_url:
                    continue
                flat.append((title, e_url))
            self.playlist_ready.emit(flat)
        else:
            self.info_ready.emit(info or {})


class SpotifyPipelineWorker(QThread):
    tracks_found = Signal(list)               # list di spotdl Song
    search_progress = Signal(str, str, str)   # label, status (matched/skip/error), detail
    searches_done = Signal(list)              # list di (song, yt_url, label, metadata)

    def __init__(self, url: str):
        super().__init__()
        self._url = url
        self.collection_folder = ""

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

        if len(songs) > 1:
            first = songs[0].album_name
            same = all(s.album_name == first for s in songs[1:])
            raw = first if same else (songs[0].list_name or "Raccolta")
            self.collection_folder = re.sub(r'[/\\:*?"<>|]', "-", raw.strip())[:100]

        # Ricerca match YouTube in parallelo (ThreadPool dentro spotify.youtube_urls)
        results = []
        for match in spotify.youtube_urls(songs):
            if match.error:
                self.search_progress.emit(match.label, "error", f"ricerca YouTube: {match.error}")
            elif not match.yt_url:
                self.search_progress.emit(match.label, "skip", "nessun match YouTube")
            else:
                metadata = spotify.track_metadata(match.song)
                results.append((match.song, match.yt_url, match.label, metadata))
                self.search_progress.emit(match.label, "matched", match.yt_url)

        self.searches_done.emit(results)