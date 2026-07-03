# 📡 POCSAG Sender + HackRF One

Herramienta completa para enviar mensajes POCSAG a un bíper (busca) usando
**GNU Radio** y un **HackRF One** como transmisor SDR.

Incluye CLI potente e interfaz gráfica profesional con tema oscuro, historial de mensajes,
perfiles guardables, soporte para mensajes alfanuméricos, numéricos y tone-only.

<img src="images/isi.jpg" alt="Mensaje recibido en bíper" width="300">

---

## Características

| Característica | CLI | GUI |
|---|:---:|:---:|
| Mensajes alfanuméricos | ✅ | ✅ |
| Mensajes numéricos | ✅ | ✅ |
| Tone-only | ✅ | ✅ |
| Ganancia RF/IF/BB configurable | ✅ | ✅ |
| Repetición N veces con pausa | ✅ | ✅ |
| Salida JSON | ✅ | — |
| Historial de mensajes | — | ✅ |
| Perfiles / Favoritos | — | ✅ |
| Indicador HackRF en tiempo real | — | ✅ |
| Persistencia de configuración | — | ✅ |

---

## Requisitos

### Hardware
- **HackRF One** (u otro SDR compatible con OsmoSDR)
- Antena para la frecuencia objetivo

### Software
- GNU Radio 3.10+
- Python 3.10+
- Paquetes Python: `numpy`, `bitstring`, `PyQt6`
- OsmoSDR (`gr-osmosdr`)

---

## Instalación

### Debian / Ubuntu

```sh
sudo apt update && sudo apt install -y gnuradio gr-osmosdr python3-pip libxcb-cursor0
pip3 install numpy bitstring PyQt6
```

### Arch Linux

```sh
sudo pacman -S gnuradio gr-osmosdr python-pip xcb-util-cursor
pip install numpy bitstring PyQt6
```

### Verificar HackRF

```sh
hackrf_info
```

Si el dispositivo aparece con número de serie, está correctamente configurado.

---

## Uso — Interfaz gráfica (recomendado)

```sh
python3 pocsag_gui.py
```

La GUI incluye cuatro pestañas:

| Pestaña | Descripción |
|---|---|
| 📡 Transmitir | Configuración del mensaje y botón de envío |
| ⚙️ Config RF | Ganancia HackRF y presets de frecuencia |
| 📋 Historial | Últimos 50 mensajes enviados |
| ⭐ Perfiles | Guardar y cargar configuraciones completas |

---

## Uso — Línea de comandos

### Parámetros disponibles

| Parámetro | Descripción | Por defecto |
|---|---|---|
| `--RIC` | Número RIC del receptor | `1122551` |
| `--SubRIC` | Sub-RIC (0–3) | `0` |
| `--Text` | Mensaje a enviar | — |
| `--mode` | Tipo: `alpha` / `numeric` / `tone` | `alpha` |
| `--pagerfreq` | Frecuencia en Hz | `148625000` |
| `--pocsagbitrate` | Bitrate: `512`, `1200`, `2400` | `2400` |
| `--tx-gain` | Ganancia RF HackRF (0 o 14 dB) | `0` |
| `--if-gain` | IF gain (0–40 dB, múltiplos de 8) | `3` |
| `--bb-gain` | BB gain (0–62 dB, múltiplos de 2) | `20` |
| `--repeat` | Repetir la transmisión N veces | `1` |
| `--repeat-delay` | Pausa entre repeticiones (segundos) | `2.0` |
| `--delay` | Espera antes del primer envío (s) | `0` |
| `--json-output` | Resultado en formato JSON | — |
| `--verbose` | Logging detallado (DEBUG) | — |
| `--quiet` | Solo errores | — |

### Ejemplos

```sh
# Mensaje alfanumérico básico
./pocsag_sender.py --RIC 1107305 --Text "Hola Mundo"

# Mensaje numérico
./pocsag_sender.py --RIC 1107305 --Text "123456" --mode numeric

# Tone-only (sin texto)
./pocsag_sender.py --RIC 1107305 --mode tone

# Repetir 3 veces con 3 segundos de pausa, ganancia IF aumentada
./pocsag_sender.py --RIC 1107305 --Text "Test" --repeat 3 --repeat-delay 3 --if-gain 24

# Salida JSON para integración con scripts
./pocsag_sender.py --RIC 1107305 --Text "Test" --json-output | python3 -m json.tool
```

---

## Frecuencias POCSAG comunes en España / Europa

| Frecuencia | Uso |
|---|---|
| **148.625 MHz** | Protección Civil España |
| **152.000 MHz** | Bípers industriales |
| **153.000 MHz** | Pruebas y desarrollo |
| **158.850 MHz** | Servicios de emergencia |
| **169.800 MHz** | POCSAG digital EU |
| **466.075 MHz** | POCSAG UHF (70 cm) |

---

## Arquitectura del proyecto

```
gr-pocsag/
├── pocsag_generator.py   # Bloque GNU Radio: genera la trama POCSAG
├── pocsag_sender.py      # CLI: grafo de transmisión + argparse
├── pocsag_gui.py         # GUI PyQt6 completa
├── config.py             # Persistencia: configuración, historial, perfiles
└── pocsagsend.grc        # Flujo original de GNU Radio Companion (referencia)
```

Los datos de usuario se guardan en `~/.pocsag_sender/`:
- `config.json` — última configuración y ajustes de ventana
- `history.json` — historial de mensajes (máx. 50)
- `profiles.json` — perfiles guardados

---

## Solución de problemas

| Problema | Solución |
|---|---|
| **HackRF no detectado** | Ejecuta `hackrf_info`. Comprueba cable USB y drivers. |
| **Error de permisos USB** | Añade tu usuario al grupo `plugdev`: `sudo usermod -aG plugdev $USER` |
| **GNU Radio no funciona** | `sudo apt install --reinstall gnuradio` |
| **Error de interfaz gráfica** | Instala `libxcb-cursor0` (Debian) o `xcb-util-cursor` (Arch) |
| **Mensaje no llega al bíper** | Verifica RIC, SubRIC y frecuencia. Prueba con `--if-gain 24 --bb-gain 32`. |
| **ImportError: bitstring** | `pip install bitstring` |
| **ImportError: PyQt6** | `pip install PyQt6` |

---

## Créditos

- Basado en el trabajo original de **ON1ARF** & **Tauebenuss**
- Mantenido y mejorado por [isifire](https://github.com/isifire)

## Licencia

GPL v3 — ver [LICENSE](LICENSE)
