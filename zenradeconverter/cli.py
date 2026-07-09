import argparse
from pathlib import Path

from . import downloader
from . import spotify


def _download_url(url: str, output_dir: Path, fmt: str, ffmpeg_location: str | None = None) -> None:
    if spotify.is_spotify_url(url):
        print("[*] Spotify URL: recupero tracce...")
        songs = spotify.fetch_tracks(url)
        if not songs:
            print("[!] Nessuna traccia trovata.")
            return

        print(f"[*] {len(songs)} tracce — cerco match su YouTube Music in parallelo...")
        for match in spotify.youtube_urls(songs):
            if match.error:
                print(f"[!] Errore ricerca '{match.label}': {match.error}")
                continue
            if not match.yt_url:
                print(f"[!] Nessun match per '{match.label}'")
                continue
            metadata = spotify.track_metadata(match.song)
            print(f"[*] Download: {match.label}")
            downloader.download(
                match.yt_url, output_dir, fmt,
                metadata=metadata, filename=match.label, ffmpeg_location=ffmpeg_location,
            )
            print(f"[✓] {match.label}")
    else:
        print("[*] YouTube: recupero info...")
        info = downloader.get_info(url, ffmpeg_location=ffmpeg_location)
        title = info.get("title", "Sconosciuto")
        print(f"[*] Download: {title}")
        downloader.download(url, output_dir, fmt, ffmpeg_location=ffmpeg_location)
        print(f"[✓] {title}")


def run_cli(ffmpeg_location: str | None = None) -> None:
    parser = argparse.ArgumentParser(description="zenradeConverter CLI")
    parser.add_argument("url", help="URL YouTube o Spotify")
    parser.add_argument("--format", "-f", choices=["mp3", "flac", "m4a"], default="mp3")
    parser.add_argument("--output", "-o", type=Path, default=Path.home() / "Music" / "zenradeConverter")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    _download_url(args.url, args.output, args.format, ffmpeg_location=ffmpeg_location)