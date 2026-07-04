# zenradeConverter

CLI tool: YouTube / Spotify URL → audio file (MP3/FLAC/M4A).

## Run

```bash
pip install -r requirements.txt   # yt-dlp, mutagen, PySide6, spotdl
python3 main.py
```

Requires **ffmpeg** on `PATH` (yt-dlp uses `FFmpegExtractAudio`).

## Architecture

| File | Role |
|---|---|
| `main.py` | Qt (PySide6) GUI entrypoint |
| `downloader.py` | yt-dlp wrapper: best audio, post-process with FFmpeg, embed thumbnail + metadata |
| `spotify.py` | spotdl wrapper: fetch Spotify metadata, YouTube Music match, mutagen tag override |

Flow: `main.py` → `spotify.fetch_tracks()` / `downloader.download()` → yt-dlp → FFmpeg → mutagen tag patch.

## Key quirks

- **UI is Italian** — prompts, labels, error messages. Don't "translate" or refactor.
- **spotdl uses default client_id** from `spotdl.utils.config.DEFAULT_CONFIG` — rate-limited, not for prod.
- **spotify client is cached** (`@lru_cache(maxsize=1)`) — lazy import to avoid slow startup.
- **No tests, no linters, no type checking** — no CI, no pre-commit, no config files beyond `requirements.txt`.
- **No `__init__.py`** — run via `python3 main.py`, not as a package. Imports work because all files are in the same directory.
- **Thread pool** `MAX_WORKERS=4` for parallel Spotify downloads.
- **Default output**: `~/Music/zenradeConverter`.
- **`.claude/settings.local.json`** allows `Bash(python3 *)` — already configured.
