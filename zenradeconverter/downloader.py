"""Wrapper su yt-dlp: miglior audio → FFmpeg → tag + copertina."""

import ssl
import urllib.request
from pathlib import Path

import certifi
import yt_dlp
from yt_dlp.utils import sanitize_filename

# ── Tabella post-processori per formato (costante, non ricostruita ogni call) ──
_FORMAT_PP: dict[str, dict] = {
    "mp3": {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"},
    "flac": {"key": "FFmpegExtractAudio", "preferredcodec": "flac"},
    "m4a": {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"},
}

# ── Cover embedder per estensione (dispatch invece di if/elif chain) ──
def _embed_mp3(path: Path, data: bytes) -> None:
    from mutagen.id3 import APIC, ID3
    audio = ID3(path)
    audio.delall("APIC")
    audio.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=data))
    audio.save()


def _embed_m4a(path: Path, data: bytes) -> None:
    from mutagen.mp4 import MP4, MP4Cover
    audio = MP4(path)
    audio["covr"] = [MP4Cover(data, MP4Cover.FORMAT_JPEG)]
    audio.save()


def _embed_flac(path: Path, data: bytes) -> None:
    from mutagen.flac import FLAC, Picture
    pic = Picture()
    pic.type = 3
    pic.mime = "image/jpeg"
    pic.data = data
    audio = FLAC(path)
    audio.clear_pictures()
    audio.add_picture(pic)
    audio.save()


_COVER_EMBEDDERS = {".mp3": _embed_mp3, ".m4a": _embed_m4a, ".flac": _embed_flac}


def build_ydl_opts(
    output_dir: Path,
    fmt: str = "mp3",
    filename: str | None = None,
    progress_hook=None,
    ffmpeg_location: str | None = None,
) -> dict:
    """Costruisce le opzioni yt-dlp per il download + post-processing."""
    postprocessors = [
        _FORMAT_PP[fmt],
        {"key": "FFmpegMetadata", "add_metadata": True},
        {"key": "EmbedThumbnail"},
    ]

    if filename:
        stem = sanitize_filename(filename, restricted=False)
        outtmpl = str(output_dir / f"{stem}.%(ext)s")
    else:
        outtmpl = str(output_dir / "%(title)s.%(ext)s")

    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": postprocessors,
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        # Velocità: scarica N frammenti in parallelo (HLS/DASH) + retry robusti
        "concurrent_fragments": 4,
        "retries": 10,
        "fragment_retries": 10,
        # YouTube: il client web di default viene bloccato con 403 (SABR-only
        # streaming experiment, vedi yt-dlp issue #12482). tv_embedded espone
        # formati audio-only e bypassa il 403.
        "extractor_args": {"youtube": {"player_client": ["tv_embedded"]}},
    }
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


def _embed_cover(path: Path, cover_url: str) -> None:
    """Scarica la copertina da Spotify e la incorpora nel file audio.

    Silenzioso su qualunque errore: in caso di problema la copertina di
    YouTube (già embedded da yt-dlp) rimane intatta.
    """
    req = urllib.request.Request(cover_url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = resp.read()
    except Exception:
        return

    embedder = _COVER_EMBEDDERS.get(path.suffix.lower())
    if not embedder:
        return
    try:
        embedder(path, data)
    except Exception:
        pass


def _apply_tags(path: Path, metadata: dict) -> None:
    """Sovrascrive i tag con i metadati Spotify (interfaccia 'easy' di mutagen)."""
    from mutagen import File

    audio = File(str(path), easy=True)
    if audio is None:
        return

    album_artist = metadata.get("album_artist") or metadata.get("artist")
    date = metadata.get("date")
    mapping = {
        "title": metadata.get("title"),
        "artist": metadata.get("artist"),
        "albumartist": album_artist,
        "album": metadata.get("album"),
        "date": str(date) if date else None,
    }
    for key, value in mapping.items():
        if value:
            try:
                audio[key] = value
            except (KeyError, ValueError):
                pass  # chiave non supportata dal formato: la saltiamo
    audio.save()

    cover_url = metadata.get("cover_url")
    if cover_url:
        _embed_cover(path, cover_url)


_YT_EXTRACTOR_ARGS = {"youtube": {"player_client": ["tv_embedded"]}}


def get_info(url: str, ffmpeg_location: str | None = None) -> dict:
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extractor_args": _YT_EXTRACTOR_ARGS,
    }
    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def download(
    url: str,
    output_dir: Path,
    fmt: str = "mp3",
    progress_hook=None,
    filename: str | None = None,
    metadata: dict | None = None,
    ffmpeg_location: str | None = None,
) -> str:
    """Scarica audio da `url`.

    Il download vero viene sempre effettuato via `extract_info(url, download=True)`
    per garantire che `extractor_args` (player_client etc.) vengano onorati:
    yt-dlp non riapplica extractor_args a URL già cached, quindi il riuso di
    info pre-estratte porterebbe a 403 sui format streaming di YouTube.
    """
    opts = build_ydl_opts(
        output_dir, fmt, filename=filename, progress_hook=progress_hook, ffmpeg_location=ffmpeg_location
    )

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "unknown")

        if metadata:
            req = info.get("requested_downloads", [])
            final_path = Path(req[0]["filepath"]) if req else None
            if final_path and final_path.exists():
                _apply_tags(final_path, metadata)

    return filename or title