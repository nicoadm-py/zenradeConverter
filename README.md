# zenradeConverter

**YouTube / Spotify URL → audio file (MP3 / FLAC / M4A).**

A PySide6 desktop GUI that downloads audio from YouTube and Spotify links. Spotify tracks are resolved via YouTube Music and tagged with correct metadata (title, artist, album, cover).

---

## Features

- **YouTube support** — single video, playlists
- **Spotify support** — tracks, albums, playlists (metadata via Spotify API, audio via YouTube Music)
- **3 output formats** — MP3 (VBR 0, best quality), FLAC (lossless), M4A (AAC)
- **Embed metadata + thumbnail** — correct title, artist, album, date and cover art via mutagen
- **Parallel downloads** — up to 4 concurrent downloads
- **Italian UI** — all labels and prompts are in Italian
- **Cancel in-flight downloads** — per-item cancel button

---

## Requirements

- Python **3.10+**
- **ffmpeg** on `PATH` (used by yt-dlp for audio extraction and re-encoding)

---

## Install

```bash
git clone https://github.com/nicoadm-py/zenradeConverter
cd zenradeConverter
pip install -r requirements.txt
```

---

## Usage

```bash
python3 main.py
```

1. Paste a YouTube or Spotify URL in the input bar.
2. Choose output format (MP3 / FLAC / M4A).
3. Choose output folder (default `~/Music/zenradeConverter`).
4. Click **Scarica** — progress bars and status icons track each download.

---

## How it works

**YouTube flow:**  
URL → `yt-dlp` extract best audio → FFmpeg convert to chosen format → embed thumbnail + metadata → file.

**Spotify flow:**  
URL → `spotdl` (Spotify API) fetch track list + metadata → match each track on YouTube Music → download audio with `yt-dlp` → override tags with correct Spotify metadata via mutagen.

Spotify does not provide downloadable audio (DRM). The tool reads metadata from Spotify, finds the corresponding track on YouTube Music, and downloads the audio from there.

---

## Architecture

| File | Role |
|---|---|
| `main.py` | Qt (PySide6) GUI, download queue, parallel worker dispatch |
| `downloader.py` | `yt-dlp` wrapper — best audio extraction, FFmpeg post-processing, mutagen tag writer |
| `spotify.py` | `spotdl` wrapper — fetch Spotify metadata, YouTube Music search |
| `workers.py` | `QThread` subclasses — non-blocking download and Spotify pipeline |

---

## Limitations

- **Spotify rate limiting** — uses `spotdl`'s default public `client_id` / `client_secret`. Rate-limited and not suitable for production.
- **Audio only** — no video download.
- **Requires internet** and **ffmpeg** on `PATH`.
- **No tests, no CI** — this is a personal utility tool.

---

# 🇮🇹 Italiano

## zenradeConverter

**URL YouTube / Spotify → file audio (MP3 / FLAC / M4A).**

Interfaccia grafica PySide6 per scaricare audio da YouTube e Spotify. Le tracce Spotify vengono risolte tramite YouTube Music e etichettate con i metadati corretti (titolo, artista, album, copertina).

### Caratteristiche

- **YouTube** — video singoli e playlist
- **Spotify** — tracce, album, playlist (metadati via API Spotify, audio via YouTube Music)
- **3 formati** — MP3 (VBR 0), FLAC (lossless), M4A (AAC)
- **Metadati + copertina** — titolo, artista, album, data e copertina corretti
- **Download paralleli** — fino a 4 download simultanei
- **UI in italiano**

### Prerequisiti

- Python 3.10+
- **ffmpeg** su `PATH`

### Installazione

```bash
git clone https://github.com/nicoadm-py/zenradeConverter
cd zenradeConverter
pip install -r requirements.txt
```

### Utilizzo

```bash
python3 main.py
```

1. Incolla un URL YouTube o Spotify nella barra in alto.
2. Scegli il formato (MP3 / FLAC / M4A).
3. Scegli la cartella di output (default `~/Music/zenradeConverter`).
4. Clicca **Scarica** — barre di progresso e icone di stato seguono ogni download.

### Architettura

| File | Ruolo |
|---|---|
| `main.py` | GUI Qt (PySide6), coda download, dispatch parallelo |
| `downloader.py` | wrapper `yt-dlp` — estrazione audio, FFmpeg, scrittura tag |
| `spotify.py` | wrapper `spotdl` — metadati Spotify, ricerca YouTube Music |
| `workers.py` | sottoclassi `QThread` — download e pipeline Spotify non bloccanti |

### Limitazioni

- **Rate limit Spotify** — usa il `client_id` pubblico di default di `spotdl`, non adatto alla produzione.
- **Solo audio** — niente video.
- Richiede **ffmpeg** su `PATH` e connessione internet.
