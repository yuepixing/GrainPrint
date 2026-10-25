import os
import sys


def _show_startup_error(message: str) -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "GrainPrint", 0x10)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


if __name__ == "__main__":
    try:
        import flet as ft
        from grainprint.core.single_instance import acquire_or_exit
        acquire_or_exit()
        from grainprint.ui.main import main
    except Exception as exc:
        _show_startup_error(str(exc))
        raise SystemExit(1)
    ft.run(main)
