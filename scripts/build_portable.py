"""Build a windowless GUI and a private console worker on the target OS."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
dist = ROOT / "dist" / platform.system().lower()
common = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
          "--distpath", str(dist), "--workpath", str(ROOT / "build" / platform.system().lower()),
          "--exclude-module", "gnuradio", "--exclude-module", "osmosdr", "--exclude-module", "PyQt5", "--exclude-module", "PyQt6",
          "--add-data", f"{ROOT / 'assets'}{os.pathsep}assets",
          "--add-data", f"{ROOT / 'web_ui'}{os.pathsep}web_ui"]
for name in ("hackrf_transfer", "hackrf_info"):
    tool = shutil.which(name)
    if not tool:
        raise SystemExit(f"Missing build dependency: {name}")
    common += ["--add-binary", f"{tool}{os.pathsep}tools"]
subprocess.run(common + ["--name", "POCSAG-CLI", "cli_entry.py"], check=True)
gui_options = ["--name", "POCSAG-Sender", "--icon", str(ROOT / "assets/icon.ico")]
if os.name == "nt":
    gui_options += ["--windowed"]
subprocess.run(common + gui_options + ["app.py"], check=True)
folder = dist / "POCSAG-Sender"
shutil.copytree(dist / "POCSAG-CLI", folder / "_internal/worker/POCSAG-CLI", dirs_exist_ok=True)
shutil.copy2(ROOT / "PORTABLE.md", folder)
label = f"POCSAG-Sender-{platform.system().lower()}-{platform.machine().lower()}"
print(shutil.make_archive(str(ROOT / "dist" / label), "zip", folder.parent, folder.name))
