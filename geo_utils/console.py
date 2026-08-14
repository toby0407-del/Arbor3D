"""終端機輸出設定（Windows cp950 無法印 emoji 時的保險）。"""
import sys


def ensure_utf8_stdout():
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (AttributeError, OSError, ValueError):
                pass
