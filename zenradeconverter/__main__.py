import sys

from .ffmpeg_setup import ensure_ffmpeg


def main():
    # Risolvi ffmpeg PRIMA di avviare la GUI/CLI.
    # Ordine: ffmpeg su PATH → ./bin cache → download automatico (ffbinaries).
    # Se ffmpeg non è disponibile, lo scarica ora (stamp/emit stato).
    if "--cli" in sys.argv:
        from .cli import run_cli
        sys.argv.remove("--cli")
        ffmpeg_path = ensure_ffmpeg(on_status=print)
        run_cli(ffmpeg_location=ffmpeg_path)
    else:
        from .gui import run_gui
        # La GUI mostrerà lo stato del download ffmpeg nella status bar;
        # se fallisce (es. Rosetta mancante) mostriamo un messaggio chiaro.
        try:
            ffmpeg_path = ensure_ffmpeg(on_status=print)
        except RuntimeError as e:
            print(f"[ffmpeg] {e}", file=sys.stderr)
            ffmpeg_path = None
        run_gui(ffmpeg_location=ffmpeg_path)


if __name__ == "__main__":
    main()