# zenradeConverter

YouTube / Spotify URL → audio file (MP3/FLAC/M4A).

## Run

```bash
python3 main.py                              # GUI (legacy entrypoint)
python3 -m zenradeconverter                  # GUI (default)
python3 -m zenradeconverter --cli URL        # CLI
```
**ffmpeg is auto-provisioned** at startup: if missing from `PATH`, the app downloads it from ffbinaries.com into `./bin/` and passes the path to yt-dlp via `ffmpeg_location`. On arm64 macOS the downloaded Intel build runs via Rosetta 2.
Python 3.13+ may lack prebuilt wheels for `spotdl` dependencies (stick to 3.10–3.12 if issues arise).

## Architecture

| File | Role |
|---|---|
| `main.py` | Qt (PySide6) GUI, queue, parallel dispatch |
| `zenradeconverter/gui.py` | GUI widgetry: `MainWindow`, `DownloadRow`, `run_gui()` |
| `zenradeconverter/cli.py` | CLI interface (argparse) |
| `zenradeconverter/downloader.py` | yt-dlp wrapper: best audio, FFmpeg post-process, embed thumbnail + metadata |
| `zenradeconverter/spotify.py` | spotdl wrapper: fetch metadata, YouTube Music match (batch parallelo via `youtube_urls()`), mutagen tag override |
| `zenradeconverter/workers.py` | `QThread` subclasses — non-blocking download and Spotify pipeline |
| `zenradeconverter/ffmpeg_setup.py` | auto-detect / download ffmpeg via ffbinaries.com API (cached in `./bin/`) |

Flow: `main.py`/`__main__` → `ffmpeg_setup.ensure_ffmpeg()` (PATH → `./bin` cache → download) → `zenradeconverter.gui` → `spotify.fetch_tracks()` → `spotify.youtube_urls()` (parallelo) / `downloader.download(ffmpeg_location=...)` → yt-dlp (`concurrent_fragments=4`, `retries=10`) → FFmpeg → mutagen tag patch.

## Key quirks

- **UI is Italian** — prompts, labels, error messages. Don't "translate" or refactor.
- **`download()` param è `fmt`** (non `format`) per non shadoware il builtin — coerente in tutto il pacchetto.
- **Spotify YouTube search in parallelo**: `spotify.youtube_urls(songs)` usa `ThreadPoolExecutor` (`SPOTIFY_SEARCH_WORKERS=4`), preserva l'ordine di input, ritorna `list[TrackMatch]`.
- **yt-dlp `concurrent_fragments=4`** scarica frammenti HLS/DASH in parallelo (speed-up su video lunghi); `retries=10`/`fragment_retries=10` per robustezza.
- **GUI `_enqueue`** prende una `@dataclass DownloadJob` (non 7 arg posizionali): vedi `gui.py`.
- **spotdl uses default client_id** from `spotdl.utils.config.DEFAULT_CONFIG` — rate-limited, not for prod.
- **spotify client is cached** (`@lru_cache(maxsize=1)`) — lazy import to avoid slow startup.
- **No tests, no linters, no type checking** — no CI, no pre-commit, no config files beyond `pyproject.toml`.
- **`--cli` flag** for `python -m zenradeconverter` enables headless mode (argparse). Without it, GUI opens.
- **Thread pool** `MAX_WORKERS=4` for parallel **download** jobs (separate dalla search pool).
- **Default output**: `~/Music/zenradeConverter`.
- **`.claude/settings.local.json`** allows `Bash(python3 *)` — already configured.
