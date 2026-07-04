import yt_dlp
from yt_dlp.utils import sanitize_filename
from pathlib import Path


def build_ydl_opts(output_dir: Path, format: str = "mp3", filename: str | None = None) -> dict:
    format_opts = {
        "mp3": {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",  # 0 = best VBR quality
        },
        "flac": {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "flac",
        },
        "m4a": {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
            "preferredquality": "0",
        },
    }

    postprocessors = [format_opts[format]]
    postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
    postprocessors.append({"key": "EmbedThumbnail"})

    # When a filename is forced (es. tracce Spotify), lo usiamo come template,
    # altrimenti manteniamo il titolo del video.
    if filename:
        stem = sanitize_filename(filename, restricted=False)
        outtmpl = str(output_dir / f"{stem}.%(ext)s")
    else:
        outtmpl = str(output_dir / "%(title)s.%(ext)s")

    return {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": postprocessors,
        "writethumbnail": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,  # la barra di avanzamento la gestisce rich via progress_hook
    }


def _apply_tags(path: Path, metadata: dict) -> None:
    """Sovrascrive i tag principali con i metadati corretti (es. da Spotify).

    Usa l'interfaccia 'easy' di mutagen che unifica le chiavi comuni tra
    MP3 (ID3), MP4/M4A e FLAC.
    """
    from mutagen import File

    audio = File(str(path), easy=True)
    if audio is None:
        return

    mapping = {
        "title": metadata.get("title"),
        "artist": metadata.get("artist"),
        "albumartist": metadata.get("album_artist") or metadata.get("artist"),
        "album": metadata.get("album"),
        "date": str(metadata["date"]) if metadata.get("date") else None,
    }
    for key, value in mapping.items():
        if value:
            try:
                audio[key] = value
            except (KeyError, ValueError):
                pass  # chiave non supportata dal formato: la saltiamo
    audio.save()


def get_info(url: str) -> dict:
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        return ydl.extract_info(url, download=False)


def download(
    url: str,
    output_dir: Path,
    format: str = "mp3",
    progress_hook=None,
    filename: str | None = None,
    metadata: dict | None = None,
    info: dict | None = None,
) -> str:
    opts = build_ydl_opts(output_dir, format, filename=filename)
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(opts) as ydl:
        if info:
            ydl.process_ie_result(info, download=True)
        else:
            info = ydl.extract_info(url, download=True)
        title = info.get("title", "unknown")

        if metadata:
            req = info.get("requested_downloads", [])
            final_path = Path(req[0]["filepath"]) if req else None
            if final_path and final_path.exists():
                _apply_tags(final_path, metadata)

    return filename or title
