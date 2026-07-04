# zenradeConverter

YouTube / Spotify URL → audio file (MP3/FLAC/M4A).

## Run

```bash
python3 main.py          # .venv already present, skip pip install
```
Requires **ffmpeg** on `PATH` — yt-dlp uses `FFmpegExtractAudio` post-processor.
Python 3.13+ may lack prebuilt wheels for `spotdl` dependencies (stick to 3.10–3.12 if issues arise).

## Architecture

| File | Role |
|---|---|
| `main.py` | Qt (PySide6) GUI, queue, parallel dispatch |
| `downloader.py` | yt-dlp wrapper: best audio, FFmpeg post-process, embed thumbnail + metadata |
| `spotify.py` | spotdl wrapper: fetch Spotify metadata, YouTube Music match, mutagen tag override |
| `workers.py` | `QThread` subclasses — non-blocking download and Spotify pipeline |

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
