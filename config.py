#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — Gestión centralizada de configuración, historial y perfiles.

Almacena los datos en ~/.pocsag_sender/ para persistencia entre sesiones.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directorio de datos de la aplicación
# ---------------------------------------------------------------------------
APP_DIR = Path.home() / ".pocsag_sender"
CONFIG_FILE   = APP_DIR / "config.json"
HISTORY_FILE  = APP_DIR / "history.json"
PROFILES_FILE = APP_DIR / "profiles.json"

MAX_HISTORY_ENTRIES = 50


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class TransmissionConfig:
    """Configuración de transmisión completa."""
    ric:        int   = 1107305
    subric:     int   = 0
    freq_mhz:   float = 148.625
    bitrate:    int   = 2400
    text:       str   = ""
    # Ganancia del HackRF
    tx_gain:    int   = 0      # RF gain (0 o 14 dB)
    if_gain:    int   = 3      # IF gain (0-47 dB, step 8)
    bb_gain:    int   = 20     # BB gain (0-62 dB, step 2)
    # Repetición
    repeat:     int   = 1      # número de envíos
    repeat_delay_s: float = 2.0  # pausa entre envíos (segundos)
    # Modo de mensaje
    msg_mode:   str   = "alpha"  # "alpha" | "numeric" | "tone"

    @property
    def freq_hz(self) -> int:
        return int(self.freq_mhz * 1_000_000)


@dataclass
class AppSettings:
    """Preferencias generales de la aplicación."""
    theme:          str  = "dark"
    font_size:      int  = 10
    console_lines:  int  = 500
    auto_scroll:    bool = True
    show_timestamps: bool = True
    last_profile:   str  = ""

    # Geometría de la ventana
    window_x:    int = 200
    window_y:    int = 200
    window_w:    int = 780
    window_h:    int = 680


@dataclass
class HistoryEntry:
    """Un mensaje enviado registrado en el historial."""
    timestamp:  str
    ric:        int
    subric:     int
    freq_mhz:   float
    bitrate:    int
    text:       str
    msg_mode:   str
    success:    bool

    @classmethod
    def from_config(cls, cfg: TransmissionConfig, success: bool) -> "HistoryEntry":
        return cls(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ric=cfg.ric,
            subric=cfg.subric,
            freq_mhz=cfg.freq_mhz,
            bitrate=cfg.bitrate,
            text=cfg.text,
            msg_mode=cfg.msg_mode,
            success=success,
        )

    def to_display(self) -> str:
        status = "✅" if self.success else "❌"
        mode_icon = {"alpha": "🔤", "numeric": "🔢", "tone": "🔔"}.get(self.msg_mode, "📨")
        return f"{status} {mode_icon} [{self.timestamp}] RIC:{self.ric} @ {self.freq_mhz} MHz — {self.text or '(tone-only)'}"


@dataclass
class Profile:
    """Perfil/favorito de configuración guardado por el usuario."""
    name:   str
    config: TransmissionConfig = field(default_factory=TransmissionConfig)

    def to_display(self) -> str:
        return f"📋 {self.name}  (RIC:{self.config.ric} @ {self.config.freq_mhz} MHz)"


# ---------------------------------------------------------------------------
# Funciones de serialización
# ---------------------------------------------------------------------------
def _ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("No se pudo leer %s: %s. Usando valores por defecto.", path, e)
        return default


def _save_json(path: Path, data) -> bool:
    _ensure_app_dir()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        logger.error("No se pudo guardar %s: %s", path, e)
        return False


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

# ---- Configuración de transmisión ----

def load_last_config() -> TransmissionConfig:
    data = _load_json(CONFIG_FILE, {})
    cfg = TransmissionConfig()
    for k, v in data.get("last_config", {}).items():
        if hasattr(cfg, k):
            try:
                setattr(cfg, k, type(getattr(cfg, k))(v))
            except (ValueError, TypeError):
                pass
    return cfg


def save_last_config(cfg: TransmissionConfig) -> bool:
    data = _load_json(CONFIG_FILE, {})
    data["last_config"] = asdict(cfg)
    return _save_json(CONFIG_FILE, data)


# ---- Ajustes de la aplicación ----

def load_settings() -> AppSettings:
    data = _load_json(CONFIG_FILE, {})
    s = AppSettings()
    for k, v in data.get("settings", {}).items():
        if hasattr(s, k):
            try:
                setattr(s, k, type(getattr(s, k))(v))
            except (ValueError, TypeError):
                pass
    return s


def save_settings(settings: AppSettings) -> bool:
    data = _load_json(CONFIG_FILE, {})
    data["settings"] = asdict(settings)
    return _save_json(CONFIG_FILE, data)


# ---- Historial ----

def load_history() -> list[HistoryEntry]:
    raw = _load_json(HISTORY_FILE, [])
    entries: list[HistoryEntry] = []
    for item in raw:
        try:
            entries.append(HistoryEntry(**item))
        except TypeError:
            pass
    return entries


def append_history(entry: HistoryEntry) -> bool:
    entries = load_history()
    entries.insert(0, entry)                         # más reciente primero
    entries = entries[:MAX_HISTORY_ENTRIES]          # limitar tamaño
    return _save_json(HISTORY_FILE, [asdict(e) for e in entries])


def clear_history() -> bool:
    return _save_json(HISTORY_FILE, [])


# ---- Perfiles ----

def load_profiles() -> list[Profile]:
    raw = _load_json(PROFILES_FILE, [])
    profiles: list[Profile] = []
    for item in raw:
        try:
            cfg_data = item.get("config", {})
            cfg = TransmissionConfig()
            for k, v in cfg_data.items():
                if hasattr(cfg, k):
                    try:
                        setattr(cfg, k, type(getattr(cfg, k))(v))
                    except (ValueError, TypeError):
                        pass
            profiles.append(Profile(name=item["name"], config=cfg))
        except (KeyError, TypeError):
            pass
    return profiles


def save_profiles(profiles: list[Profile]) -> bool:
    data = []
    for p in profiles:
        data.append({"name": p.name, "config": asdict(p.config)})
    return _save_json(PROFILES_FILE, data)


def save_profile(profile: Profile) -> bool:
    profiles = load_profiles()
    # Reemplazar si ya existe el mismo nombre
    profiles = [p for p in profiles if p.name != profile.name]
    profiles.insert(0, profile)
    return save_profiles(profiles)


def delete_profile(name: str) -> bool:
    profiles = load_profiles()
    profiles = [p for p in profiles if p.name != name]
    return save_profiles(profiles)
