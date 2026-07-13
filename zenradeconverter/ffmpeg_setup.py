"""Rileva o scarica automaticamente ffmpeg per yt-dlp.

Strategia:
  1. Se ffmpeg è su PATH → usalo (preferenza al sistema, evita duplicati).
  2. Altrimenti, se un binario è già cached in ./bin/ → usalo.
  3. Altrimenti scarica da ffbinaries.com (API REST, nessuna dipendenza extra)
     nella cartella ./bin/ e rendilo eseguibile.

Su Apple Silicon (arm64) ffbinaries pubblica solo build Intel (osx-64):
il binario gira via Rosetta 2. Se Rosetta manca, il check di esecuzione
fallisce con "Bad CPU type" e mostriamo all'utente come installarlo.
"""

import io
import json
import logging
import platform
import shutil
import ssl
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import certifi

log = logging.getLogger(__name__)

# Cartella locale per il binario cached (stessa root della repo, .gitignore-ata)
FFMPEG_BIN_DIR = Path(__file__).resolve().parent.parent / "bin"

_API_LATEST = "https://ffbinaries.com/api/v1/version/latest"

# Messaggio guida per arm64 senza Rosetta 2
_ROSETTA_HINT = (
    "ffmpeg (build Intel) non avviabile su Apple Silicon senza Rosetta 2. "
    "Installalo con:  softwareupdate --install-rosetta"
)


def _platform_id() -> str:
    """Mappa sys/platform → id ffbinaries. Ritorna '' se piattaforma non supportata."""
    if sys.platform == "win32":
        # ffbinaries ha solo windows-64 per versioni recenti
        return "windows-64"
    if sys.platform == "darwin":
        # Su arm64 usiamo osx-64 (Intel) + Rosetta 2: ffbinaries non publica arm64
        return "osx-64"
    if sys.platform.startswith("linux"):
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "linux-64"
        if machine.startswith("arm"):
            return "linux-armv7"  # best-effort
    return ""


def _ctx() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _http_get_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
        return json.load(resp)


def _http_get_bytes(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as resp:
        return resp.read()


def _system_ffmpeg() -> str | None:
    """shutil.which su ffmpeg + verifica che almeno parta. None se assente/rotto."""
    path = shutil.which("ffmpeg")
    if not path:
        return None
    try:
        subprocess.run([path, "-version"], capture_output=True, timeout=10, check=False)
    except Exception:
        return None
    return path


def _cached_ffmpeg() -> str | None:
    """Verifica il binario cached in FFMPEG_BIN_DIR. None se assente/non avviabile."""
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    candidate = FFMPEG_BIN_DIR / exe
    if not candidate.exists():
        return None
    try:
        subprocess.run([str(candidate), "-version"], capture_output=True, timeout=10, check=False)
    except Exception as e:
        # Cattura anche "Bad CPU type" (Rosetta mancante su arm64)
        stderr = str(e)
        if "Bad CPU type" in stderr or "Rosetta" in stderr:
            raise RuntimeError(_ROSETTA_HINT) from e
        return None
    return str(candidate)


def _download_ffmpeg(platform_id: str, dest_dir: Path, on_status=None) -> str:
    """Scarica ffmpeg da ffbinaries per la piattaforma data in dest_dir.

    Ritorna path al binario. Solleva RuntimeError su errori di rete/API/zip.
    """
    if on_status:
        on_status(f"[ffmpeg] versione corrente da ffbinaries.com...")
    meta = _http_get_json(_API_LATEST)
    bin_map = meta.get("bin", {})
    entry = bin_map.get(platform_id)
    if not entry or not entry.get("ffmpeg"):
        raise RuntimeError(
            f"Nessun binario ffbinaries per piattaforma '{platform_id}'. "
            "Installa ffmpeg manualmente."
        )
    url = entry["ffmpeg"]

    if on_status:
        on_status(f"[ffmpeg] scarico {url.split('/')[-1]}...")
    data = _http_get_bytes(url)

    dest_dir.mkdir(parents=True, exist_ok=True)
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    dest = dest_dir / exe_name

    # Estrai solo 'ffmpeg' dallo ZIP (ignora ffprobe/eventuali extra)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        # Match esatto per evitare di estrarre binari arbitrari da uno ZIP malevolo
        # (es. "ffmpeg_evil" in un pacchetto compromesso).
        target = next(
            (n for n in names
             if n.lower() in ("ffmpeg", "ffmpeg.exe")
             or n.lower().endswith("/ffmpeg")
             or n.lower().endswith("/ffmpeg.exe")),
            None,
        )
        if not target:
            raise RuntimeError(f"ZIP ffbinaries non contiene ffmpeg (trovati: {names})")
        # Scrittura atomica: estrai in dest.tmp poi os.replace(dest.tmp, dest).
        # Evita cache ffmpeg semi-scritta se il processo viene interrotto
        # (Ctrl-C durante la decompressione): in tal caso il file .tmp
        # orfano non viene riconosciuto come cache valido al prossimo avvio.
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        with z.open(target) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
        tmp.replace(dest)

    if sys.platform != "win32":
        dest.chmod(0o755)

    if on_status:
        on_status(f"[ffmpeg] installato in {dest}")
    return str(dest)


def ensure_ffmpeg(on_status=None) -> str | None:
    """Garantisce che ffmpeg sia disponibile. Ritorna path o None (con on_status per messaggi).

    Ordine: system PATH → ./bin cache → download da ffbinaries.
    Su arm64 senza Rosetta rilancia RuntimeError col messaggio utente.
    """
    p = _system_ffmpeg()
    if p:
        return p

    try:
        p = _cached_ffmpeg()
        if p:
            return p
    except RuntimeError as e:
        if on_status:
            on_status(str(e))
        raise

    pid = _platform_id()
    if not pid:
        if on_status:
            on_status("ffmpeg non trovato e piattaforma non supportata da ffbinaries.")
        return None

    try:
        path = _download_ffmpeg(pid, FFMPEG_BIN_DIR, on_status=on_status)
    except Exception as e:
        if on_status:
            on_status(f"[ffmpeg] errore download: {e}")
        return None

    # Verifica che il binario scaricato parta davvero (catch Rosetta mancante)
    try:
        subprocess.run([path, "-version"], capture_output=True, timeout=10, check=False)
    except Exception as e:
        msg = f"{_ROSETTA_HINT} ({e})" if "Bad CPU type" in str(e) else f"ffmpeg scaricato non avviabile: {e}"
        if on_status:
            on_status(msg)
        raise RuntimeError(msg) from e

    return path


if __name__ == "__main__":
    # Smoke test manuale: python3 -m zenradeconverter.ffmpeg_setup
    p = ensure_ffmpeg(on_status=print)
    print("Resolved ffmpeg:", p)