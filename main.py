import sys

from zenradeconverter.gui import run_gui
from zenradeconverter.ffmpeg_setup import ensure_ffmpeg

if __name__ == "__main__":
    try:
        ffmpeg_path = ensure_ffmpeg(on_status=print)
    except RuntimeError as e:
        print(f"[ffmpeg] {e}", file=sys.stderr)
        ffmpeg_path = None
    run_gui(ffmpeg_location=ffmpeg_path)
