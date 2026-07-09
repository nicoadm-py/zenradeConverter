from zenradeconverter.gui import run_gui
from zenradeconverter.ffmpeg_setup import ensure_ffmpeg

if __name__ == "__main__":
    ffmpeg_path = ensure_ffmpeg(on_status=print)
    run_gui(ffmpeg_location=ffmpeg_path)