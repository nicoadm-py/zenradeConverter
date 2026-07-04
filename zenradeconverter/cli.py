import argparse
import sys
from pathlib import Path

from . import downloader
from . import spotify


def _download_url(url: str, output_dir: Path, fmt: str) -> None:
    if spotify.is_spotify_url(url):
        print(f"[*] Spotify URL: recupero tracce...")
        songs = spotify.fetch_tracks(url)
        if not songs:
            print("[!] Nessuna traccia trovata.")
            return
        for song in songs:
            artist = ", ".join(song.artists) if song.artists else song.artist
            label = f"{artist} - {song.name}"
            print(f"[*] Cerco '{label}' su YouTube Music...")
            yt_url = spotify.youtube_url(song)
            if not yt_url:
                print(f"[!] Nessun match per '{label}'")
                continue
            metadata = spotify.track_metadata(song)
            print(f"[*] Download: {label}")
            downloader.download(yt_url, output_dir, fmt, metadata=metadata, filename=label)
            print(f"[✓] {label}")
    else:
        print(f"[*] YouTube: recupero info...")
        info = downloader.get_info(url)
        title = info.get("title", "Sconosciuto")
        print(f"[*] Download: {title}")
        downloader.download(url, output_dir, fmt, info=info)
        print(f"[✓] {title}")


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="zenradeConverter CLI")
    parser.add_argument("url", help="URL YouTube o Spotify")
    parser.add_argument("--format", "-f", choices=["mp3", "flac", "m4a"], default="mp3")
    parser.add_argument("--output", "-o", type=Path, default=Path.home() / "Music" / "zenradeConverter")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    _download_url(args.url, args.output, args.format)
