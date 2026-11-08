#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pocsag_gui.py — Interfaz gráfica profesional para POCSAG Sender via HackRF One.

Características:
  - Tema oscuro premium inspirado en herramientas SDR
  - Historial de mensajes enviados (persistente)
  - Perfiles / Favoritos guardables
  - Modo de repetición configurable
  - Indicador en tiempo real del estado del HackRF
  - Ganancia RF/IF/BB configurable desde la UI
  - Soporte para mensajes alfanuméricos, numéricos y tone-only
  - Consola con colores y timestamps
  - Barra de progreso animada durante la transmisión
  - Persistencia de configuración entre sesiones
"""

from __future__ import annotations

import json
from portable_runtime import tool_path, sender_command, subprocess_options
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRect, QSize, Qt,
    QThread, QTimer, QProcess, pyqtSignal, QObject,
)
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QIcon, QPalette,
    QTextCharFormat, QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QSpinBox, QSplitter, QStatusBar, QTabWidget,
    QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

# Importación local opcional — la app debe funcionar aunque no exista config.py
try:
    import config as cfg_module
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

VERSION = "2.1.0"
SCRIPT_DIR = Path(__file__).parent.resolve()

# ---------------------------------------------------------------------------
# Paleta de colores — tema oscuro SDR
# ---------------------------------------------------------------------------
COLORS = {
    "bg":           "#101722",   # fondo principal
    "bg_panel":     "#161b22",   # paneles / grupos
    "bg_input":     "#1c2128",   # campos de entrada
    "bg_console":   "#0a0e14",   # consola
    "accent":       "#58e0c0",   # color de acento (verde SDR)
    "accent_dim":   "#007a62",   # acento apagado
    "accent2":      "#388bfd",   # acento secundario (azul)
    "danger":       "#f85149",   # rojo de error
    "warning":      "#d29922",   # amarillo de advertencia
    "success":      "#3fb950",   # verde de éxito
    "text":         "#e6edf3",   # texto principal
    "text_dim":     "#8b949e",   # texto secundario
    "border":       "#30363d",   # bordes
    "border_focus": "#00d4aa",   # borde activo
    "hover":        "#21262d",   # hover de elementos
    "tx_active":    "#f85149",   # rojo durante TX
}

STYLESHEET = f"""
/* ── Ventana principal ─────────────────────────────────────────────── */
QMainWindow {{
    background-color: {COLORS['bg']};
}}
QWidget {{
    color: {COLORS['text']};
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 10pt;
}}

QLabel, QCheckBox {{
    background: transparent;
}}

/* ── Grupos ────────────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    font-size: 9pt;
    font-weight: bold;
    color: {COLORS['text_dim']};
    letter-spacing: 0.5px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: -1px;
    padding: 0 6px;
    background-color: transparent;
    color: {COLORS['accent']};
    text-transform: uppercase;
}}

/* ── Inputs ────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLORS['text']};
    selection-background-color: {COLORS['accent_dim']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS['border_focus']};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {COLORS['text_dim']};
    background-color: {COLORS['bg_panel']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {COLORS['text_dim']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent_dim']};
    color: {COLORS['text']};
    outline: none;
}}

/* ── Botones ───────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS['bg_panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 7px 16px;
    color: {COLORS['text']};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLORS['hover']};
    border-color: {COLORS['text_dim']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent_dim']};
}}
QPushButton:disabled {{
    color: {COLORS['text_dim']};
    border-color: {COLORS['border']};
}}
QPushButton#btn_send {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
    color: #000000;
    font-weight: bold;
    font-size: 11pt;
    border-radius: 8px;
}}
QPushButton#btn_send:hover {{
    background-color: #00e5b8;
    border-color: #00e5b8;
}}
QPushButton#btn_send:disabled {{
    background-color: {COLORS['tx_active']};
    border-color: {COLORS['tx_active']};
    color: white;
}}
QPushButton#btn_cancel {{
    background-color: transparent;
    border-color: {COLORS['danger']};
    color: {COLORS['danger']};
}}
QPushButton#btn_cancel:hover {{
    background-color: {COLORS['danger']};
    color: white;
}}
QPushButton#btn_profile_save {{
    background-color: transparent;
    border-color: {COLORS['accent2']};
    color: {COLORS['accent2']};
}}
QPushButton#btn_profile_save:hover {{
    background-color: {COLORS['accent2']};
    color: white;
}}

/* ── Tabs ──────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['bg_panel']};
}}
QTabBar::tab {{
    background-color: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 8px 20px;
    color: {COLORS['text_dim']};
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {COLORS['bg_panel']};
    color: {COLORS['accent']};
    border-color: {COLORS['border']};
    border-bottom-color: {COLORS['bg_panel']};
}}
QTabBar::tab:hover {{
    color: {COLORS['text']};
    background-color: {COLORS['hover']};
}}

/* ── Consola ───────────────────────────────────────────────────────── */
QTextEdit#console {{
    background-color: {COLORS['bg_console']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    color: {COLORS['text']};
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 9pt;
    selection-background-color: {COLORS['accent_dim']};
}}

/* ── Lista de historial / perfiles ────────────────────────────────── */
QListWidget {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    color: {COLORS['text']};
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {COLORS['border']};
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent_dim']};
    color: white;
}}
QListWidget::item:hover {{
    background-color: {COLORS['hover']};
}}

/* ── Barra de progreso ─────────────────────────────────────────────── */
QProgressBar {{
    background-color: {COLORS['bg_input']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['text']};
    height: 8px;
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 4px;
}}

/* ── Sliders (ganancia) ────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {COLORS['border']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; height: 14px;
    margin: -5px 0;
    background: {COLORS['accent']};
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {COLORS['accent']};
    border-radius: 2px;
}}

/* ── CheckBox ──────────────────────────────────────────────────────── */
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background: {COLORS['bg_input']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}

/* ── ScrollBar ─────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {COLORS['bg']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['text_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ── Status bar ────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {COLORS['bg_panel']};
    border-top: 1px solid {COLORS['border']};
    color: {COLORS['text_dim']};
    font-size: 9pt;
}}

/* ── Labels ────────────────────────────────────────────────────────── */
QLabel#label_header {{
    font-size: 16pt;
    font-weight: bold;
    color: {COLORS['accent']};
}}
QLabel#label_subheader {{
    font-size: 9pt;
    color: {COLORS['text_dim']};
}}
QLabel#hackrf_status {{
    font-size: 9pt;
    font-weight: bold;
    padding: 4px 10px;
    border-radius: 12px;
    border: 1px solid {COLORS['border']};
}}
QLabel#char_counter {{
    font-size: 8pt;
    color: {COLORS['text_dim']};
}}
"""


# ---------------------------------------------------------------------------
# Worker de transmisión (hilo secundario)
# ---------------------------------------------------------------------------
class TxSignals(QObject):
    line_stdout = pyqtSignal(str)
    line_stderr = pyqtSignal(str)
    finished    = pyqtSignal(int)   # código de retorno


class TxWorker(QThread):
    """Ejecuta pocsag_sender.py en un hilo separado."""

    def __init__(self, cmd: list[str]):
        super().__init__()
        self.cmd     = cmd
        self.signals = TxSignals()
        self._process: Optional[subprocess.Popen] = None

    def run(self) -> None:
        try:
            self._process = subprocess.Popen(
                self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace", bufsize=1, **subprocess_options(),
            )
            for line in self._process.stdout:
                self.signals.line_stderr.emit(line.rstrip())
            self._process.wait()
            self.signals.finished.emit(self._process.returncode)
        except FileNotFoundError as e:
            self.signals.line_stderr.emit(f"Script no encontrado: {e}")
            self.signals.finished.emit(1)
        except Exception as e:
            self.signals.line_stderr.emit(f"Error inesperado: {e}")
            self.signals.finished.emit(1)

    def cancel(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()


# ---------------------------------------------------------------------------
# Widget: indicador de HackRF
# ---------------------------------------------------------------------------
class HackRFIndicator(QLabel):
    """Pill que muestra el estado de conexión del HackRF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hackrf_status")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(30)
        self.setText("Comprobando HackRF…")
        self._probe = QProcess(self)
        self._probe.finished.connect(self._probe_finished)
        self._probe.errorOccurred.connect(lambda _: self._show_connection(False))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)
        self._timer.start(5000)
        QTimer.singleShot(0, self._check)

    def _check(self) -> None:
        if self._probe.state() != QProcess.ProcessState.NotRunning:
            return
        try:
            self._probe.start(tool_path("hackrf_info"), [])
            QTimer.singleShot(2500, self._timeout)
        except FileNotFoundError:
            self._show_connection(False)

    def _timeout(self):
        if self._probe.state() != QProcess.ProcessState.NotRunning:
            self._probe.kill()

    def _probe_finished(self, code, status):
        self._show_connection(code == 0 and b"Serial number" in bytes(self._probe.readAllStandardOutput()))

    def _show_connection(self, connected):
        if connected:
            self.setText("● HackRF conectado")
            self.setStyleSheet(
                f"color: {COLORS['success']}; background: rgba(63,185,80,0.1); "
                f"border: 1px solid {COLORS['success']}; border-radius: 12px; padding: 4px 10px;"
            )
        else:
            self.setText("○ HackRF no detectado")
            self.setStyleSheet(
                f"color: {COLORS['text_dim']}; background: rgba(139,148,158,0.1); "
                f"border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 4px 10px;"
            )


# ---------------------------------------------------------------------------
# Widget: consola con colores y timestamps
# ---------------------------------------------------------------------------
class Console(QTextEdit):
    """Consola de salida con colores y timestamps opcionales."""

    def __init__(self, max_lines: int = 500, show_timestamps: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("console")
        self.setReadOnly(True)
        self.max_lines  = max_lines
        self.show_ts    = show_timestamps

    def _append_html(self, html: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html)
        cursor.insertHtml("<br>")
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        # Limitar número de líneas
        doc = self.document()
        while doc.blockCount() > self.max_lines:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _ts(self) -> str:
        if self.show_ts:
            return f'<span style="color:{COLORS["text_dim"]};font-size:8pt;">[{datetime.now().strftime("%H:%M:%S")}]</span> '
        return ""

    def log(self, msg: str) -> None:
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._append_html(f'{self._ts()}<span style="color:{COLORS["text"]};">{safe}</span>')

    def log_info(self, msg: str) -> None:
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._append_html(f'{self._ts()}<span style="color:{COLORS["accent"]};">[INFO]</span> <span style="color:{COLORS["text"]};">{safe}</span>')

    def log_error(self, msg: str) -> None:
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._append_html(f'{self._ts()}<span style="color:{COLORS["danger"]};">[ERROR] {safe}</span>')

    def log_warn(self, msg: str) -> None:
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._append_html(f'{self._ts()}<span style="color:{COLORS["warning"]};">[WARN] {safe}</span>')

    def log_success(self, msg: str) -> None:
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._append_html(f'{self._ts()}<span style="color:{COLORS["success"]};">✓ {safe}</span>')

    def export_to_file(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar consola", str(Path.home() / "pocsag_log.txt"), "Text files (*.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.toPlainText())
            except OSError as e:
                self.log_error(f"No se pudo guardar: {e}")


# ---------------------------------------------------------------------------
# Diálogo para guardar perfil
# ---------------------------------------------------------------------------
class SaveProfileDialog(QDialog):
    def __init__(self, existing_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guardar perfil")
        self.setFixedSize(340, 130)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Nombre del perfil:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Mi Bíper")
        layout.addWidget(self.name_input)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_name(self) -> str:
        return self.name_input.text().strip()


# ---------------------------------------------------------------------------
# Tab: Transmisión
# ---------------------------------------------------------------------------
class TransmitTab(QWidget):
    transmission_started  = pyqtSignal()
    transmission_finished = pyqtSignal(bool)  # success

    def __init__(self, console: Console, parent=None):
        super().__init__(parent)
        self.console = console
        self._worker: Optional[TxWorker] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Parámetros principales ──────────────────────────────────────
        params_grp = QGroupBox("Parámetros POCSAG")
        params_grp.setMinimumHeight(185)
        pg = QGridLayout(params_grp)
        pg.setSpacing(8)
        pg.setColumnStretch(1, 1)
        pg.setColumnStretch(3, 1)

        # RIC
        pg.addWidget(self._lbl("RIC"), 0, 0)
        self.ric_input = QLineEdit("1107305")
        self.ric_input.setToolTip("Número RIC del receptor (1 – 2 097 151)")
        pg.addWidget(self.ric_input, 0, 1)

        # SubRIC
        pg.addWidget(self._lbl("Sub-RIC"), 0, 2)
        self.subric_combo = QComboBox()
        self.subric_combo.addItems(["0", "1", "2", "3"])
        self.subric_combo.setToolTip("SubRIC del receptor (0–3)")
        pg.addWidget(self.subric_combo, 0, 3)

        # Frecuencia
        pg.addWidget(self._lbl("Frecuencia (MHz)"), 1, 0)
        self.freq_input = QDoubleSpinBox()
        self.freq_input.setRange(1.0, 6000.0)
        self.freq_input.setDecimals(4)
        self.freq_input.setSingleStep(0.025)
        self.freq_input.setValue(148.625)
        self.freq_input.setToolTip("Frecuencia de transmisión en MHz")
        pg.addWidget(self.freq_input, 1, 1)

        # Bitrate
        pg.addWidget(self._lbl("Bitrate"), 1, 2)
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["512", "1200", "2400"])
        self.bitrate_combo.setCurrentText("2400")
        self.bitrate_combo.setToolTip("Velocidad de transmisión POCSAG")
        pg.addWidget(self.bitrate_combo, 1, 3)

        # Modo de mensaje
        pg.addWidget(self._lbl("Modo"), 2, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Alfanumérico (alpha)", "Numérico (numeric)", "Solo tono (tone)"])
        self.mode_combo.setToolTip("Tipo de mensaje POCSAG a transmitir")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        pg.addWidget(self.mode_combo, 2, 1, 1, 3)

        root.addWidget(params_grp)

        # ── Mensaje ─────────────────────────────────────────────────────
        msg_grp = QGroupBox("Mensaje")
        msg_grp.setMinimumHeight(100)
        mg = QVBoxLayout(msg_grp)

        msg_row = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Escribe el mensaje aquí…")
        self.text_input.setToolTip("Texto a enviar al bíper")
        self.text_input.textChanged.connect(self._update_char_count)
        msg_row.addWidget(self.text_input)

        self.char_counter = QLabel("0 / ∞")
        self.char_counter.setObjectName("char_counter")
        self.char_counter.setFixedWidth(60)
        msg_row.addWidget(self.char_counter)
        mg.addLayout(msg_row)

        root.addWidget(msg_grp)

        # ── Repetición ──────────────────────────────────────────────────
        rep_grp = QGroupBox("Repetición")
        rep_grp.setMinimumHeight(100)
        rg = QHBoxLayout(rep_grp)

        self.repeat_check = QCheckBox("Repetir envío")
        self.repeat_check.stateChanged.connect(self._toggle_repeat)
        rg.addWidget(self.repeat_check)

        rg.addWidget(self._lbl("Veces:"))
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 99)
        self.repeat_spin.setValue(3)
        self.repeat_spin.setFixedWidth(60)
        self.repeat_spin.setEnabled(False)
        rg.addWidget(self.repeat_spin)

        rg.addWidget(self._lbl("Pausa (s):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.5, 60.0)
        self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setValue(2.0)
        self.delay_spin.setFixedWidth(70)
        self.delay_spin.setEnabled(False)
        rg.addWidget(self.delay_spin)
        rg.addStretch()

        root.addWidget(rep_grp)

        # ── Botones de acción ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_send = QPushButton("TRANSMITIR")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.setMinimumHeight(46)
        self.btn_send.clicked.connect(self.start_transmission)
        btn_row.addWidget(self.btn_send, stretch=3)

        self.btn_cancel = QPushButton("✕  Cancelar")
        self.btn_cancel.setObjectName("btn_cancel")
        self.btn_cancel.setMinimumHeight(46)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_transmission)
        btn_row.addWidget(self.btn_cancel, stretch=1)

        root.addLayout(btn_row)

        # ── Barra de progreso ────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)      # modo indeterminado
        self.progress.setFixedHeight(6)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        root.addStretch()

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 9pt;")
        return lbl

    def _on_mode_changed(self, idx: int) -> None:
        is_tone = (idx == 2)
        self.text_input.setEnabled(not is_tone)
        if is_tone:
            self.text_input.setPlaceholderText("(Modo tone-only: sin texto)")
        else:
            mode = "numérico" if idx == 1 else "alfanumérico"
            self.text_input.setPlaceholderText(f"Escribe el mensaje {mode} aquí…")
        self._update_char_count()

    def _toggle_repeat(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self.repeat_spin.setEnabled(enabled)
        self.delay_spin.setEnabled(enabled)

    def _update_char_count(self) -> None:
        count = len(self.text_input.text())
        self.char_counter.setText(f"{count} / ∞")
        if count > 200:
            self.char_counter.setStyleSheet(f"color: {COLORS['warning']}; font-size: 8pt;")
        else:
            self.char_counter.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 8pt;")

    def get_config(self) -> dict:
        """Retorna los valores actuales de los controles de transmisión."""
        modes = ["alpha", "numeric", "tone"]
        return {
            "ric":      self.ric_input.text().strip(),
            "subric":   self.subric_combo.currentText(),
            "freq_mhz": self.freq_input.value(),
            "freq_hz":  int(self.freq_input.value() * 1_000_000),
            "bitrate":  self.bitrate_combo.currentText(),
            "mode":     modes[self.mode_combo.currentIndex()],
            "text":     self.text_input.text().strip(),
            "repeat":   self.repeat_spin.value() if self.repeat_check.isChecked() else 1,
            "delay":    self.delay_spin.value() if self.repeat_check.isChecked() else 2.0,
        }

    def set_config(self, data: dict) -> None:
        """Carga valores en los controles de la UI."""
        if "ric" in data:
            self.ric_input.setText(str(data["ric"]))
        if "subric" in data:
            self.subric_combo.setCurrentText(str(data["subric"]))
        if "freq_mhz" in data:
            self.freq_input.setValue(float(data["freq_mhz"]))
        if "bitrate" in data:
            self.bitrate_combo.setCurrentText(str(data["bitrate"]))
        if "mode" in data:
            mode_map = {"alpha": 0, "numeric": 1, "tone": 2}
            self.mode_combo.setCurrentIndex(mode_map.get(data["mode"], 0))
        if "text" in data:
            self.text_input.setText(str(data["text"]))

    def _validate(self) -> Optional[dict]:
        c = self.get_config()
        try:
            ric = int(c["ric"])
            if not (1 <= ric <= 2_097_151):
                raise ValueError("RIC fuera de rango")
        except ValueError:
            self.console.log_error("RIC inválido. Debe ser un entero entre 1 y 2 097 151.")
            return None
        if c["mode"] != "tone" and not c["text"]:
            self.console.log_error("El mensaje no puede estar vacío.")
            return None
        return c

    def start_transmission(self) -> None:
        if self._worker and self._worker.isRunning():
            self.console.log_warn("Ya hay una transmisión en curso.")
            return

        c = self._validate()
        if c is None:
            return

        cmd = sender_command() + [
            "--RIC",           c["ric"],
            "--SubRIC",        c["subric"],
            "--pagerfreq",     str(c["freq_hz"]),
            "--pocsagbitrate", c["bitrate"],
            "--mode",          c["mode"],
            "--repeat",        str(c["repeat"]),
            "--repeat-delay",  str(c["delay"]),
            "--verbose",
        ]
        gains = self._rf_gains()
        cmd += ["--tx-gain", str(gains["tx_gain"]), "--if-gain", str(gains["if_gain"])]
        if c["mode"] != "tone":
            cmd += ["--Text", c["text"]]

        self.console.log_info(f"Iniciando transmisión → RIC:{c['ric']} @ {c['freq_mhz']:.3f} MHz | {c['mode'].upper()}")
        if c["mode"] != "tone":
            self.console.log_info(f"Mensaje: '{c['text']}'")

        self.btn_send.setEnabled(False)
        self.btn_send.setText("TRANSMITIENDO…")
        self.btn_cancel.setEnabled(True)
        self.progress.setVisible(True)

        self._worker = TxWorker(cmd)
        self._worker.signals.line_stdout.connect(self.console.log)
        self._worker.signals.line_stderr.connect(self._handle_stderr)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.start()
        self.transmission_started.emit()

    def _handle_stderr(self, line: str) -> None:
        if "[ERROR]" in line:
            self.console.log_error(line)
        elif "[WARN]" in line:
            self.console.log_warn(line)
        else:
            self.console.log(line)

    def cancel_transmission(self) -> None:
        if self._worker:
            self._worker.cancel()
            self.console.log_warn("Transmisión cancelada por el usuario.")

    def _on_finished(self, returncode: int) -> None:
        success = returncode == 0
        if success:
            self.console.log_success("Transmisión completada correctamente.")
        else:
            self.console.log_error(f"Transmisión finalizada con error (código {returncode}).")

        self.btn_send.setEnabled(True)
        self.btn_send.setText("TRANSMITIR")
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        self.transmission_finished.emit(success)


# ---------------------------------------------------------------------------
# Tab: Configuración RF
# ---------------------------------------------------------------------------
class RFConfigTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Ganancia HackRF ─────────────────────────────────────────────
        gain_grp = QGroupBox("Ganancia HackRF")
        gg = QGridLayout(gain_grp)
        gg.setSpacing(10)
        gg.setColumnStretch(1, 1)

        # TX gain
        gg.addWidget(QLabel("RF Gain (TX):"), 0, 0)
        self.tx_gain_combo = QComboBox()
        self.tx_gain_combo.addItems(["0 dB (desactivado)", "14 dB (amplificador)"])
        self.tx_gain_combo.setToolTip("Amplificador de potencia RF (0 o 14 dB)")
        gg.addWidget(self.tx_gain_combo, 0, 1)
        gg.addWidget(self._hint("Recomendado: 0 dB para corto alcance"), 0, 2)

        # IF gain slider
        gg.addWidget(QLabel("TX VGA:"), 1, 0)
        if_row = QHBoxLayout()
        self.if_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.if_gain_slider.setRange(0, 5)       # 0..5 × 8 = 0..40 dB
        self.if_gain_slider.setValue(0)           # 0 dB por defecto (3 hardcoded antes)
        self.if_gain_slider.setTickInterval(1)
        self.if_gain_slider.valueChanged.connect(lambda v: self.if_gain_lbl.setText(f"{v*8} dB"))
        if_row.addWidget(self.if_gain_slider)
        self.if_gain_lbl = QLabel("0 dB")
        self.if_gain_lbl.setFixedWidth(50)
        if_row.addWidget(self.if_gain_lbl)
        gg.addLayout(if_row, 1, 1)
        gg.addWidget(self._hint("Rango: 0–40 dB (múltiplos de 8)"), 1, 2)

        # BB gain slider
        gg.addWidget(QLabel("BB (solo RX):"), 2, 0)
        bb_row = QHBoxLayout()
        self.bb_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.bb_gain_slider.setRange(0, 31)      # 0..31 × 2 = 0..62 dB
        self.bb_gain_slider.setEnabled(False)
        self.bb_gain_slider.setValue(10)         # 20 dB por defecto
        self.bb_gain_slider.setTickInterval(1)
        self.bb_gain_slider.valueChanged.connect(lambda v: self.bb_gain_lbl.setText(f"{v*2} dB"))
        bb_row.addWidget(self.bb_gain_slider)
        self.bb_gain_lbl = QLabel("20 dB")
        self.bb_gain_lbl.setFixedWidth(50)
        bb_row.addWidget(self.bb_gain_lbl)
        gg.addLayout(bb_row, 2, 1)
        gg.addWidget(self._hint("No se utiliza en transmisión"), 2, 2)

        root.addWidget(gain_grp)

        # ── Presets de frecuencia ────────────────────────────────────────
        freq_grp = QGroupBox("Frecuencias POCSAG comunes (España / Europa)")
        fg = QVBoxLayout(freq_grp)
        self.freq_list = QListWidget()
        self.freq_list.setMaximumHeight(160)
        presets = [
            ("148.625 MHz — Protección Civil España",      148.625),
            ("152.000 MHz — Bípers industriales comunes",  152.000),
            ("153.000 MHz — Frecuencia de pruebas",        153.000),
            ("158.850 MHz — Servicios de emergencia",      158.850),
            ("169.800 MHz — POCSAG digital EU",            169.800),
            ("466.075 MHz — POCSAG 70cm UHF",              466.075),
        ]
        for name, _ in presets:
            self.freq_list.addItem(name)
        self.freq_list.itemDoubleClicked.connect(
            lambda item: self._apply_freq(presets[self.freq_list.row(item)][1])
        )
        fg.addWidget(self.freq_list)
        fg.addWidget(QLabel("↑ Doble clic para aplicar la frecuencia al transmisor"))
        root.addWidget(freq_grp)

        root.addStretch()

        # Señal interna a la que se conectará la tab principal
        self._freq_presets = presets

    def _hint(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 8pt; font-style: italic;")
        return lbl

    def _apply_freq(self, freq: float) -> None:
        # Se conecta desde MainWindow para actualizar el campo en TransmitTab
        if hasattr(self, "_freq_callback"):
            self._freq_callback(freq)

    def get_gains(self) -> dict:
        return {
            "tx_gain": 14 if self.tx_gain_combo.currentIndex() == 1 else 0,
            "if_gain": self.if_gain_slider.value() * 8,
            "bb_gain": self.bb_gain_slider.value() * 2,
        }

    def set_gains(self, tx: int, if_: int, bb: int) -> None:
        self.tx_gain_combo.setCurrentIndex(1 if tx == 14 else 0)
        self.if_gain_slider.setValue(if_ // 8)
        self.bb_gain_slider.setValue(bb // 2)


# ---------------------------------------------------------------------------
# Tab: Historial
# ---------------------------------------------------------------------------
class HistoryTab(QWidget):
    load_into_transmit = pyqtSignal(dict)   # emite datos para cargar en TransmitTab

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Últimos mensajes transmitidos:"))
        top_row.addStretch()
        self.btn_clear = QPushButton("Borrar historial")
        self.btn_clear.clicked.connect(self.clear_history)
        top_row.addWidget(self.btn_clear)
        root.addLayout(top_row)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_click)
        root.addWidget(self.list_widget)

        hint = QLabel("↑ Doble clic en un mensaje para cargarlo en el transmisor")
        hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 8pt;")
        root.addWidget(hint)

    def refresh(self) -> None:
        self.list_widget.clear()
        if HAS_CONFIG:
            self._entries = cfg_module.load_history()
            for e in self._entries:
                item = QListWidgetItem(e.to_display())
                item.setForeground(
                    QColor(COLORS["success"] if e.success else COLORS["danger"])
                )
                self.list_widget.addItem(item)
        else:
            self.list_widget.addItem("(Historial no disponible sin config.py)")

    def add_entry(self, entry) -> None:
        if HAS_CONFIG:
            cfg_module.append_history(entry)
        self.refresh()

    def clear_history(self) -> None:
        if HAS_CONFIG:
            cfg_module.clear_history()
        self.refresh()

    def _on_item_double_click(self, item: QListWidgetItem) -> None:
        row = self.list_widget.row(item)
        if row < len(self._entries):
            e = self._entries[row]
            self.load_into_transmit.emit({
                "ric":      e.ric,
                "subric":   e.subric,
                "freq_mhz": e.freq_mhz,
                "bitrate":  e.bitrate,
                "mode":     e.msg_mode,
                "text":     e.text,
            })


# ---------------------------------------------------------------------------
# Tab: Perfiles
# ---------------------------------------------------------------------------
class ProfilesTab(QWidget):
    load_into_transmit = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profiles: list = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(QLabel("Perfiles guardados:"))
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_load)
        root.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.clicked.connect(self._on_delete)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()
        root.addLayout(btn_row)

        hint = QLabel("↑ Doble clic en un perfil para cargarlo")
        hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 8pt;")
        root.addWidget(hint)

    def refresh(self) -> None:
        self.list_widget.clear()
        if HAS_CONFIG:
            self._profiles = cfg_module.load_profiles()
            for p in self._profiles:
                self.list_widget.addItem(p.to_display())
        else:
            self.list_widget.addItem("(Perfiles no disponibles sin config.py)")

    def _on_load(self, item: QListWidgetItem) -> None:
        row = self.list_widget.row(item)
        if row < len(self._profiles):
            p = self._profiles[row]
            c = p.config
            self.load_into_transmit.emit({
                "ric":      c.ric,
                "subric":   c.subric,
                "freq_mhz": c.freq_mhz,
                "bitrate":  c.bitrate,
                "mode":     c.msg_mode,
                "text":     c.text,
            })

    def _on_delete(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._profiles):
            return
        name = self._profiles[row].name
        if HAS_CONFIG:
            cfg_module.delete_profile(name)
        self.refresh()


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"POCSAG Sender  v{VERSION}  —  HackRF One")
        self.setWindowIcon(QIcon(str(SCRIPT_DIR / "assets" / "icon.png")))
        self.setMinimumSize(820, 680)
        self._setup_ui()
        self._load_saved_state()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Header ──────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("app_header")
        header.setFixedHeight(86)
        header.setStyleSheet(
            f"QWidget#app_header {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 #0d1117, stop:1 #161b22); "
            f"border-bottom: 1px solid {COLORS['border']}; }}"
        )
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(18, 0, 18, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        logo = QLabel()
        logo.setPixmap(QIcon(str(SCRIPT_DIR / "assets" / "icon.png")).pixmap(48, 48))
        logo.setFixedSize(56, 56)
        hrow.addWidget(logo)
        t = QLabel("POCSAG Sender")
        t.setObjectName("label_header")
        sub = QLabel(f"Centro de transmisión · HackRF One · v{VERSION}")
        sub.setObjectName("label_subheader")
        title_col.addWidget(t)
        title_col.addWidget(sub)
        hrow.addLayout(title_col)
        hrow.addStretch()

        # Indicador HackRF
        self.hackrf_indicator = HackRFIndicator()
        hrow.addWidget(self.hackrf_indicator)

        root.addWidget(header)

        # ── Splitter: izquierda (tabs) + derecha (consola) ───────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {COLORS['border']}; }}")

        # Panel izquierdo: tabs
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 12, 20)
        left_layout.setSpacing(8)

        self.tabs = QTabWidget()

        # Instanciar consola (compartida entre tabs)
        self.console = Console()

        self.tx_tab       = TransmitTab(self.console)
        self.rf_tab       = RFConfigTab()
        self.history_tab  = HistoryTab()
        self.profiles_tab = ProfilesTab()

        for widget, label in ((self.tx_tab, "Transmitir"), (self.rf_tab, "Radio / RF"),
                              (self.history_tab, "Historial"), (self.profiles_tab, "Perfiles")):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(widget)
            self.tabs.addTab(scroll, label)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        left_layout.addWidget(self.tabs, stretch=1)
        actions = QHBoxLayout()
        actions.addWidget(self.tx_tab.btn_send, stretch=1)
        actions.addWidget(self.tx_tab.btn_cancel)
        left_layout.addLayout(actions)

        # Botones de perfil debajo de las tabs
        profile_row = QHBoxLayout()
        self.btn_save_profile = QPushButton("Guardar perfil")
        self.btn_save_profile.setObjectName("btn_profile_save")
        self.btn_save_profile.clicked.connect(self._save_profile)
        profile_row.addWidget(self.btn_save_profile)
        profile_row.addStretch()
        toggle_log = QPushButton("Mostrar registro")
        toggle_log.setCheckable(True)
        profile_row.addWidget(toggle_log)
        left_layout.addLayout(profile_row)

        splitter.addWidget(left_panel)

        # Panel derecho: consola
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 12, 12, 12)
        right_layout.setSpacing(6)

        console_header = QHBoxLayout()
        console_header.addWidget(QLabel("Consola de salida"))
        console_header.addStretch()
        btn_clear_console = QPushButton("Limpiar")
        btn_clear_console.setMinimumHeight(32)
        btn_clear_console.clicked.connect(self.console.clear)
        console_header.addWidget(btn_clear_console)
        btn_export = QPushButton("Exportar")
        btn_export.setMinimumHeight(32)
        btn_export.clicked.connect(self.console.export_to_file)
        console_header.addWidget(btn_export)
        right_layout.addLayout(console_header)

        right_layout.addWidget(self.console, stretch=1)

        splitter.addWidget(right_panel)
        right_panel.setMinimumHeight(130)
        right_panel.setMaximumHeight(240)
        right_panel.hide()
        toggle_log.toggled.connect(right_panel.setVisible)
        toggle_log.toggled.connect(lambda visible: toggle_log.setText("Ocultar registro" if visible else "Mostrar registro"))
        splitter.setSizes([500, 160])

        root.addWidget(splitter, stretch=1)

        # ── Status bar ──────────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo.")

        # ── Conexiones entre componentes ─────────────────────────────────
        self.tx_tab.transmission_started.connect(self._on_tx_started)
        self.tx_tab.transmission_finished.connect(self._on_tx_finished)
        self.history_tab.load_into_transmit.connect(self._load_config_into_tx)
        self.profiles_tab.load_into_transmit.connect(self._load_config_into_tx)

        # Conectar selección de frecuencia preset → TransmitTab
        self.tx_tab._rf_gains = self.rf_tab.get_gains
        self.rf_tab._freq_callback = lambda freq: self.tx_tab.freq_input.setValue(freq)

    # ------------------------------------------------------------------
    # Tab change
    # ------------------------------------------------------------------
    def _on_tab_changed(self, idx: int) -> None:
        if idx == 2:
            self.history_tab.refresh()
        elif idx == 3:
            self.profiles_tab.refresh()

    # ------------------------------------------------------------------
    # Transmisión
    # ------------------------------------------------------------------
    def _on_tx_started(self) -> None:
        self.hackrf_indicator._timer.stop()
        self.hackrf_indicator._probe.kill()
        self.status_bar.showMessage("📡 Transmitiendo…")

    def _on_tx_finished(self, success: bool) -> None:
        self.hackrf_indicator._timer.start(5000)
        self.status_bar.showMessage(
            "✓ Transmisión completada." if success else "✗ Error en la transmisión."
        )
        # Guardar en historial
        if HAS_CONFIG:
            c    = self.tx_tab.get_config()
            gains = self.rf_tab.get_gains()
            tc   = cfg_module.TransmissionConfig(
                ric=int(c["ric"]) if c["ric"].isdigit() else 0,
                subric=int(c["subric"]),
                freq_mhz=c["freq_mhz"],
                bitrate=int(c["bitrate"]),
                text=c["text"],
                msg_mode=c["mode"],
                tx_gain=gains["tx_gain"],
                if_gain=gains["if_gain"],
                bb_gain=gains["bb_gain"],
                repeat=c["repeat"],
                repeat_delay_s=c["delay"],
            )
            entry = cfg_module.HistoryEntry.from_config(tc, success)
            self.history_tab.add_entry(entry)

    # ------------------------------------------------------------------
    # Carga de configuración
    # ------------------------------------------------------------------
    def _load_config_into_tx(self, data: dict) -> None:
        self.tx_tab.set_config(data)
        self.tabs.setCurrentWidget(self.tx_tab)
        self.console.log_info(f"Configuración cargada: RIC={data.get('ric')} @ {data.get('freq_mhz')} MHz")

    # ------------------------------------------------------------------
    # Perfiles
    # ------------------------------------------------------------------
    def _save_profile(self) -> None:
        existing = [p.name for p in cfg_module.load_profiles()] if HAS_CONFIG else []
        dlg = SaveProfileDialog(existing, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name = dlg.get_name()
        if not name:
            self.console.log_warn("El nombre del perfil no puede estar vacío.")
            return
        if HAS_CONFIG:
            c     = self.tx_tab.get_config()
            gains = self.rf_tab.get_gains()
            tc    = cfg_module.TransmissionConfig(
                ric=int(c["ric"]) if c["ric"].isdigit() else 0,
                subric=int(c["subric"]),
                freq_mhz=c["freq_mhz"],
                bitrate=int(c["bitrate"]),
                text=c["text"],
                msg_mode=c["mode"],
                tx_gain=gains["tx_gain"],
                if_gain=gains["if_gain"],
                bb_gain=gains["bb_gain"],
            )
            cfg_module.save_profile(cfg_module.Profile(name=name, config=tc))
            self.console.log_success(f"Perfil '{name}' guardado correctamente.")
            self.profiles_tab.refresh()

    # ------------------------------------------------------------------
    # Persistencia de sesión
    # ------------------------------------------------------------------
    def _load_saved_state(self) -> None:
        if not HAS_CONFIG:
            return
        try:
            tc = cfg_module.load_last_config()
            self.tx_tab.set_config({
                "ric":      tc.ric,
                "subric":   tc.subric,
                "freq_mhz": tc.freq_mhz,
                "bitrate":  tc.bitrate,
                "mode":     tc.msg_mode,
                "text":     tc.text,
            })
            self.rf_tab.set_gains(tc.tx_gain, tc.if_gain, tc.bb_gain)

            settings = cfg_module.load_settings()
            self.resize(settings.window_w, settings.window_h)
            self.move(settings.window_x, settings.window_y)
        except Exception:
            pass

    def _save_state(self) -> None:
        if not HAS_CONFIG:
            return
        try:
            c     = self.tx_tab.get_config()
            gains = self.rf_tab.get_gains()
            tc    = cfg_module.TransmissionConfig(
                ric=int(c["ric"]) if c["ric"].isdigit() else 0,
                subric=int(c["subric"]),
                freq_mhz=c["freq_mhz"],
                bitrate=int(c["bitrate"]),
                text=c["text"],
                msg_mode=c["mode"],
                tx_gain=gains["tx_gain"],
                if_gain=gains["if_gain"],
                bb_gain=gains["bb_gain"],
            )
            cfg_module.save_last_config(tc)

            geo = self.geometry()
            s = cfg_module.load_settings()
            s.window_x = geo.x()
            s.window_y = geo.y()
            s.window_w = geo.width()
            s.window_h = geo.height()
            cfg_module.save_settings(s)
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self.hackrf_indicator._timer.stop()
        self.hackrf_indicator._probe.kill()
        self.hackrf_indicator._probe.waitForFinished(1000)
        worker = self.tx_tab._worker
        if worker and worker.isRunning():
            worker.cancel()
            if not worker.wait(3000):
                event.ignore()
                return
        self._save_state()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET + """
    QTabWidget::pane { border: 1px solid #303e50; border-radius: 8px; padding: 10px; }
    QTabBar::tab { padding: 11px 15px; margin-right: 4px; }
    QTabBar::tab:selected { color: #58e0c0; border-bottom: 2px solid #58e0c0; }
    QGroupBox { padding: 18px 14px 14px; margin-top: 20px; }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { min-height: 24px; }
    QLabel#label_header { font-size: 21pt; font-weight: 700; }
    QLabel#label_subheader { color: #a2b2c5; padding-top: 4px; }
    """)
    app.setWindowIcon(QIcon(str(SCRIPT_DIR / "assets" / "icon.png")))

    # Paleta base oscura para los componentes nativos
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(COLORS["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(COLORS["bg_input"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(COLORS["bg_panel"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(COLORS["bg_panel"]))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Button,          QColor(COLORS["bg_panel"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(COLORS["accent_dim"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
