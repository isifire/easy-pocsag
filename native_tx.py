"""Standalone continuous-phase 2-FSK synthesis and HackRF transport."""
from __future__ import annotations
import logging
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from pocsag_generator import PocsagSender
from portable_runtime import tool_path, subprocess_options

SAMPLE_RATE = 12_000_000  # Match the known-working HackRF configuration.
DEVIATION = 4500.0
AMPLITUDE = 127
logger = logging.getLogger(__name__)


def iq_chunks(symbols, bitrate, chunk_size=262144):
    """Yield interleaved signed 8-bit I/Q with continuous phase and bounded RAM."""
    if bitrate not in (512, 1200, 2400):
        raise ValueError("Bitrate debe ser 512, 1200 o 2400")
    symbols = np.asarray(symbols, dtype=np.int8)
    total = len(symbols) * SAMPLE_RATE // bitrate
    phase = 0.0
    for start in range(0, total, chunk_size):
        positions = np.arange(start, min(start + chunk_size, total), dtype=np.int64)
        values = symbols[positions * bitrate // SAMPLE_RATE]
        # Match the receiver/legacy waveform: logical 1 uses negative deviation.
        angles = -np.cumsum(values, dtype=np.float64) * (2 * np.pi * DEVIATION / SAMPLE_RATE) + phase
        phase = float(angles[-1] % (2 * np.pi))
        iq = np.empty((len(values), 2), dtype=np.int8)
        iq[:, 0] = np.rint(AMPLITUDE * np.cos(angles)).astype(np.int8)
        iq[:, 1] = np.rint(AMPLITUDE * np.sin(angles)).astype(np.int8)
        iq[values == 0] = 0
        yield iq.tobytes()


def export_iq(path, ric, subric, text, bitrate, mode):
    frame = PocsagSender(number=ric, source=subric, text=text, mode=mode)
    with open(path, "wb") as output:
        for chunk in iq_chunks(frame.pocsagmsg, bitrate):
            output.write(chunk)
        # Keep the device running while the last USB buffers reach the DAC.
        output.write(bytes(SAMPLE_RATE * 2))
        output.write(bytes((-output.tell()) % 262144))
        # Drain the USB TX pipeline before ending the process.
        output.write(bytes(SAMPLE_RATE // 2))
        padding = (-output.tell()) % 262144
        output.write(bytes(padding))
    return Path(path).stat().st_size


class PocsagTransmitter:
    def __init__(self, ric, subric, text, pagerfreq, pocsagbitrate, tx_gain, if_gain, bb_gain, mode):
        if not 1_000_000 <= pagerfreq <= 6_000_000_000:
            raise ValueError("Frecuencia fuera del rango HackRF")
        if tx_gain not in (0, 14) or not 0 <= if_gain <= 47:
            raise ValueError("Ganancia inválida: RF 0/14, TX VGA 0–47 dB")
        self.tool = tool_path("hackrf_transfer")
        if not self.tool:
            raise RuntimeError("Falta hackrf_transfer. Instala el paquete hackrf.")
        self.params = (ric, subric, text, pocsagbitrate, mode)
        self.frequency, self.amp, self.gain = pagerfreq, tx_gain != 0, if_gain
        if bb_gain != 20:
            logger.warning("BB gain es un parámetro de recepción; se ignora en TX. Usa --if-gain.")
        self.started = False

    def start(self):
        self.started = True

    def wait(self):
        if not self.started:
            raise RuntimeError("El transmisor no está iniciado")
        with tempfile.TemporaryDirectory(prefix="pocsag-") as directory:
            path = Path(directory) / "message.iq"
            export_iq(path, *self.params)
            command = [self.tool, "-t", str(path), "-f", str(self.frequency),
                       "-s", str(SAMPLE_RATE), "-a", str(int(self.amp)), "-x", str(self.gain)]
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, **subprocess_options())
            try:
                _, errors = process.communicate()
            except BaseException:
                process.terminate()
                process.communicate()
                raise
            if process.returncode:
                raise RuntimeError(errors.strip() or "Falló hackrf_transfer")
            logger.info("%s", errors.strip())
            logger.info("Muestras entregadas al HackRF; recepción pendiente de verificar")
