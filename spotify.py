"""Supporto Spotify.

Spotify non permette di scaricare l'audio originale (DRM). Come tutti i tool
del genere, qui leggiamo i METADATI dal link Spotify (titolo, artista, album,
copertina) tramite spotdl, troviamo la traccia corrispondente su YouTube Music
e scarichiamo l'audio da lì alla massima qualità riusando downloader.py.
"""

import logging
from functools import lru_cache


def is_spotify_url(url: str) -> bool:
    u = url.lower()
    return "spotify.com" in u or u.startswith("spotify:")


@lru_cache(maxsize=1)
def _client():
    # Import pesante e lento: lo facciamo solo quando serve davvero.
    from spotdl import Spotdl
    from spotdl.utils.config import DEFAULT_CONFIG

    logging.getLogger("spotdl").setLevel(logging.CRITICAL)
    return Spotdl(
        client_id=DEFAULT_CONFIG["client_id"],
        client_secret=DEFAULT_CONFIG["client_secret"],
        downloader_settings={"print_errors": False},
    )


def fetch_tracks(url: str) -> list:
    """URL Spotify (traccia/album/playlist) -> lista di oggetti Song con i metadati.

    Veloce: una sola chiamata alle API Spotify. La ricerca del match su YouTube
    avviene poi traccia per traccia con youtube_url().
    """
    return _client().search([url])


def youtube_url(song) -> str | None:
    """Trova l'URL YouTube Music del miglior match per una traccia Spotify."""
    return _client().downloader.search(song) or None


def track_metadata(song) -> dict:
    """Estrae i metadati utili da un oggetto Song di spotdl."""
    artist = ", ".join(song.artists) if song.artists else song.artist
    return {
        "title": song.name,
        "artist": artist,
        "album_artist": song.album_artist,
        "album": song.album_name,
        "date": song.date or song.year,
    }
