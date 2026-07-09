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

- Python **3.10–3.12** (recommended: 3.11 or 3.12; 3.13+ may lack prebuilt wheels for some dependencies)
- **ffmpeg**: auto-provisioned at startup. If `ffmpeg` isn't found on `PATH`, the app downloads the correct build for your platform (Windows/macOS/Linux x64) from [ffbinaries.com](https://ffbinaries.com) into a local `./bin/` folder and tells yt-dlp to use it. On **Apple Silicon (arm64)**, since ffbinaries publishes Intel builds only, the downloaded binary runs via Rosetta 2 — if Rosetta is missing the app prints the install command (`softwareupdate --install-rosetta`). You can always bypass auto-download by installing ffmpeg yourself (`brew install ffmpeg`, etc.).

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
| `ffmpeg_setup.py` | detects / auto-downloads ffmpeg via ffbinaries.com API (cached in `./bin/`) |

---

## Limitations

- **No tests, no CI** — this is a personal utility tool.
- **Apple Silicon (arm64)** — auto-downloaded ffmpeg is an Intel build via Rosetta 2; install ffmpeg via `brew` to bypass.

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

- Python 3.10–3.12 (consigliato: 3.11 o 3.12; 3.13+ può mancare di prebuilt wheel per alcune dipendenze)
- **ffmpeg**: provisionato automaticamente all'avvio. Se non è su `PATH`, l'app scarica da [ffbinaries.com](https://ffbinaries.com) il binario corretto per la piattaforma (Windows/macOS/Linux x64) in `./bin/` e yt-dlp lo usa. Su **Apple Silicon (arm64)** ffbinaries pubblica solo build Intel → il binario gira via Rosetta 2; se Rosetta manca, viene mostrato il comando per installarlo (`softwareupdate --install-rosetta`). Puoi sempre installare ffmpeg a mano (`brew install ffmpeg`) e l'app userà quello.

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
| `ffmpeg_setup.py` | rileva / scarica ffmpeg via API ffbinaries.com (cached in `./bin/`) |

### Limitazioni

- Richiede connessione internet.
- **Apple Silicon (arm64)** — ffmpeg scaricato è una build Intel via Rosetta 2; installa ffmpeg con `brew` per bypassare.
