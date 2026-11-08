"""Locate bundled HackRF tools and invoke the frozen CLI safely."""
import os
from pathlib import Path
import shutil
import sys


def tool_path(name):
    filename = name + (".exe" if os.name == "nt" else "")
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    for candidate in (base / "tools" / filename, base / filename):
        if candidate.is_file():
            return str(candidate)
    result = shutil.which(filename)
    if result:
        return result
    raise FileNotFoundError(f"No se encuentra {filename}. El paquete portable está incompleto.")


def sender_command():
    if getattr(sys, "frozen", False):
        return [str(Path(sys._MEIPASS) / "worker" / "POCSAG-CLI" / ("POCSAG-CLI.exe" if os.name == "nt" else "POCSAG-CLI"))]
    return [sys.executable, str(Path(__file__).parent / "pocsag_sender.py")]


def subprocess_options():
    return {"creationflags": 0x08000000} if os.name == "nt" else {}
