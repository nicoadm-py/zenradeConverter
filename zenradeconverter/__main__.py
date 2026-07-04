import sys

from .gui import run_gui


def main():
    if "--cli" in sys.argv:
        from .cli import run_cli
        sys.argv.remove("--cli")
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()
