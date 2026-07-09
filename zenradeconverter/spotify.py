"""Supporto Spotify.

Spotify non permette di scaricare l'audio originale (DRM): leggiamo i
METADATI dal link (titolo, artista, album, copertina) tramite spotdl,
troviamo la traccia corrispondente su YouTube Music e scarichiamo l'audio
da lì alla massima qualità riusando downloader.py.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache


SPOTIFY_SEARCH_WORKERS = 4

_SPOTDL_ERR = (
    "spotdl non installato o incompatibile. "
    "Esegui: pip install 'spotdl>=4.5.0'  (Python 3.10–3.12 consigliato)"
)


def is_spotify_url(url: str) -> bool:
    u = url.lower()
    return "spotify.com" in u or u.startswith("spotify:")


@lru_cache(maxsize=1)
def _client():
    try:
        from spotdl import Spotdl
        from spotdl.utils.config import DEFAULT_CONFIG
    except ImportError as e:
        raise ImportError(_SPOTDL_ERR) from e

    logging.getLogger("spotdl").setLevel(logging.CRITICAL)

    try:
        cid = DEFAULT_CONFIG["client_id"]
        csec = DEFAULT_CONFIG["client_secret"]
    except (KeyError, TypeError) as e:
        raise RuntimeError(
            f"spotdl API cambiata (versione {getattr(Spotdl, '__version__', '?')}): {e}"
        ) from e

    return Spotdl(client_id=cid, client_secret=csec, downloader_settings={"print_errors": False})


def fetch_tracks(url: str) -> list:
    """URL Spotify (traccia/album/playlist) → lista di Song con i metadati.

    Una sola chiamata alle API Spotify; la ricerca del match YouTube avviene
    poi per-traccia con youtube_url() / youtube_urls().
    """
    return _client().search([url])


def youtube_url(song) -> str | None:
    """Trova l'URL YouTube Music del miglior match per una traccia Spotify."""
    return _client().downloader.search(song) or None


@dataclass
class TrackMatch:
    song: object
    yt_url: str | None
    label: str
    error: str | None = None


def _song_label(song) -> str:
    artist = ", ".join(song.artists) if song.artists else song.artist
    return f"{artist} - {song.name}"


def _search_one(song) -> TrackMatch:
    label = _song_label(song)
    try:
        yt = youtube_url(song)
    except Exception as e:
        return TrackMatch(song, None, label, error=str(e))
    return TrackMatch(song, yt, label)


def youtube_urls(songs: list, max_workers: int = SPOTIFY_SEARCH_WORKERS) -> list[TrackMatch]:
    """Ricerca match YouTube per un batch di tracce IN PARALLELO.

    Velocizza drammaticamente raccolte grandi (N/`max_workers`× più
    veloce rispetto alla ricerca sequenziale). Preserva l'ordine di input.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_search_one, songs))


def track_metadata(song) -> dict:
    """Estrae i metadati utili da un oggetto Song di spotdl."""
    return {
        "title": song.name,
        "artist": ", ".join(song.artists) if song.artists else song.artist,
        "album_artist": song.album_artist,
        "album": song.album_name,
        "date": song.date or song.year,
        "cover_url": song.cover_url,
    }