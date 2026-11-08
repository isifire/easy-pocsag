"""Local-only browser interface for the standalone POCSAG transmitter."""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import config
from portable_runtime import tool_path, sender_command, subprocess_options

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
TOKEN = secrets.token_urlsafe(32)


def transmission_config(data):
    result = config.TransmissionConfig(
        ric=int(data["ric"]), subric=int(data.get("subric", 0)),
        freq_mhz=float(data["freq_mhz"]), bitrate=int(data.get("bitrate", 2400)),
        text=str(data.get("text", "")), msg_mode=str(data.get("msg_mode", "alpha")),
        tx_gain=int(data.get("tx_gain", 0)), if_gain=int(data.get("if_gain", 0)),
        repeat=int(data.get("repeat", 1)), repeat_delay_s=float(data.get("repeat_delay_s", 2)),
    )
    import math
    from pocsag_generator import PocsagSender
    from pocsag_sender import sanitize_text
    PocsagSender._validate_params(result.ric, result.subric, result.text, result.msg_mode)
    sanitize_text(result.text, result.msg_mode)
    if result.bitrate not in (512, 1200, 2400):
        raise ValueError("Velocidad no válida")
    if not math.isfinite(result.freq_mhz) or not 1 <= result.freq_mhz <= 6000:
        raise ValueError("Frecuencia fuera de rango")
    if result.tx_gain not in (0, 14) or not 0 <= result.if_gain <= 47:
        raise ValueError("Ganancia fuera de rango")
    if not 1 <= result.repeat <= 100 or not .5 <= result.repeat_delay_s <= 60:
        raise ValueError("Repetición fuera de rango")
    if len(result.text) > 10000:
        raise ValueError("El mensaje supera 10000 caracteres")
    return result


class Controller:
    def __init__(self):
        self.lock = threading.RLock()
        self.device_lock = threading.Lock()
        self.phase = "idle"
        self.connected = None
        self.logs = []
        self.process = None
        self.cancelled = threading.Event()
        self.stopped = threading.Event()

    def log(self, message):
        with self.lock:
            self.logs.append({"time": time.strftime("%H:%M:%S"), "message": str(message)})
            self.logs = self.logs[-300:]

    def probe(self):
        while not self.stopped.is_set():
            if self.device_lock.acquire(blocking=False):
                try:
                    result = subprocess.run([tool_path("hackrf_info")], capture_output=True, timeout=3, **subprocess_options())
                    self.connected = result.returncode == 0 and b"Serial number" in result.stdout
                except (OSError, subprocess.TimeoutExpired):
                    self.connected = False
                finally:
                    self.device_lock.release()
            self.stopped.wait(5)

    def send(self, data):
        cfg = transmission_config(data)
        with self.lock:
            if self.phase == "sending":
                raise ValueError("Ya hay un envío en curso")
            self.phase = "sending"
            self.cancelled.clear()
            self.logs = []
        threading.Thread(target=self._transmit, args=(cfg,), daemon=True).start()

    def _transmit(self, cfg):
        success = False
        try:
            with self.device_lock:
                if self.cancelled.is_set():
                    return
                cmd = sender_command() + ["--RIC", str(cfg.ric), "--SubRIC", str(cfg.subric),
                    "--pagerfreq", str(cfg.freq_hz), "--pocsagbitrate", str(cfg.bitrate),
                    "--mode", cfg.msg_mode, "--Text", cfg.text, "--tx-gain", str(cfg.tx_gain),
                    "--if-gain", str(cfg.if_gain), "--repeat", str(cfg.repeat),
                    "--repeat-delay", str(cfg.repeat_delay_s)]
                self.log(f"Enviando a RIC {cfg.ric} · {cfg.freq_mhz:.4f} MHz · {cfg.bitrate} bps")
                self.log(f"RF: {cfg.tx_gain} dB · TX VGA: {cfg.if_gain} dB · Repeticiones: {cfg.repeat}")
                kwargs = subprocess_options()
                if os.name != "nt":
                    kwargs["start_new_session"] = True
                with self.lock:
                    self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, errors="replace", **kwargs)
                    process = self.process
                for line in process.stdout:
                    self.log(line.rstrip())
                success = process.wait() == 0 and not self.cancelled.is_set()
                config.save_last_config(cfg)
                config.append_history(config.HistoryEntry.from_config(cfg, success))
        except Exception as error:
            self.log(str(error))
        finally:
            with self.lock:
                self.process = None
                self.phase = "cancelled" if self.cancelled.is_set() else ("sent" if success else "error")

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            process = self.process
            if process and process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, **subprocess_options())
                else:
                    os.killpg(process.pid, signal.SIGTERM)

    def state(self):
        with self.lock:
            return {"phase": self.phase, "connected": self.connected, "logs": list(self.logs),
                    "config": asdict(config.load_last_config()),
                    "history": [asdict(item) for item in config.load_history()],
                    "profiles": [{"name": p.name, "config": asdict(p.config)} for p in config.load_profiles()]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, data, status=200, content_type="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def allowed(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.allowed():
            return self.respond({"error": "Host no permitido"}, 403)
        if self.path == "/health":
            return self.respond({"app": "pocsag-studio"})
        if self.path == "/":
            html = (ROOT / "web_ui/index.html").read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
            return self.respond(html.encode(), content_type="text/html; charset=utf-8")
        if self.path == "/api/state" and self.headers.get("X-POCSAG-Token") == TOKEN:
            return self.respond(self.server.controller.state())
        if self.path == "/icon.png":
            return self.respond((ROOT / "assets/icon.png").read_bytes(), content_type="image/png")
        self.respond({"error": "No encontrado"}, 404)

    def do_POST(self):
        if not self.allowed() or self.headers.get("X-POCSAG-Token") != TOKEN:
            return self.respond({"error": "Solicitud no autorizada"}, 403)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 100000:
                raise ValueError("Tamaño no permitido")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Solicitud inválida")
            if self.path == "/api/send":
                self.server.controller.send(data)
            elif self.path == "/api/cancel":
                self.server.controller.cancel()
            elif self.path == "/api/profile":
                name = str(data.get("name", "")).strip()
                if not name or len(name) > 100:
                    raise ValueError("Introduce un nombre de perfil")
                if not config.save_profile(config.Profile(name, transmission_config(data["config"]))):
                    raise ValueError("No se pudo guardar el perfil")
            elif self.path == "/api/quit":
                self.server.controller.cancel()
                self.server.controller.stopped.set()
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                return self.respond({"error": "No encontrado"}, 404)
            self.respond({"ok": True})
        except (ValueError, TypeError, KeyError) as error:
            self.respond({"error": str(error)}, 400)


def main():
    import urllib.request
    from urllib.parse import urlsplit
    url_file = config.APP_DIR / "web-url.txt"
    if url_file.exists():
        previous = url_file.read_text(encoding="utf-8").strip()
        parsed = urlsplit(previous)
        if parsed.scheme == "http" and parsed.hostname == "127.0.0.1":
            try:
                with urllib.request.urlopen(previous.rstrip("/") + "/health", timeout=1) as response:
                    if json.load(response).get("app") == "pocsag-studio":
                        if "--no-browser" not in sys.argv:
                            webbrowser.open(previous)
                        return
            except (OSError, ValueError):
                pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.controller = Controller()
    threading.Thread(target=server.controller.probe, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/"
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    (config.APP_DIR / "web-url.txt").write_text(url, encoding="utf-8")
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.controller.stopped.set()
        server.server_close()

if __name__ == "__main__": main()
