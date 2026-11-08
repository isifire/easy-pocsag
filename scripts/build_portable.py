"""Bundle the local web app and its private transmission worker."""
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
shutil.copy2(ROOT / "LICENSE", folder)
# Include corresponding application source and available dependency license notices.
import importlib.metadata
import tempfile
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary)
    for path in list(ROOT.glob("*.py")) + [ROOT / name for name in ("README.md", "PORTABLE.md", "LICENSE", "requirements.txt")]:
        shutil.copy2(path, source / path.name)
    for name in ("web_ui", "assets", "images", "scripts", ".github"):
        shutil.copytree(ROOT / name, source / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.make_archive(str(folder / "source"), "zip", source)
licenses = folder / "licenses"
shutil.copytree(ROOT / "assets/licenses", licenses, dirs_exist_ok=True)
for package in ("numpy", "pyinstaller"):
    distribution = importlib.metadata.distribution(package)
    for item in distribution.files or []:
        if any(word in item.name.lower() for word in ("license", "copying", "notice")):
            path = Path(distribution.locate_file(item))
            if path.is_file():
                destination = licenses / package
                destination.mkdir(exist_ok=True)
                shutil.copy2(path, destination / path.name)
for name in ("LICENSE.txt", "LICENSE_PYTHON.txt"):
    path = Path(sys.base_prefix) / name
    if path.exists():
        shutil.copy2(path, licenses / ("Python-" + name))

label = f"POCSAG-Sender-{platform.system().lower()}-{platform.machine().lower()}"
print(shutil.make_archive(str(ROOT / "dist" / label), "zip", folder.parent, folder.name))
