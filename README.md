# 📡 POCSAG Sender + HackRF One

Herramienta completa para enviar mensajes POCSAG a un bíper (busca) usando
**Python/NumPy** y un **HackRF One** como transmisor SDR, sin GNU Radio ni OsmoSDR.

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
- Python 3.10+
- Paquetes Python: `numpy`, `PyQt6`
- Herramientas HackRF (`hackrf_transfer` y `hackrf_info`)

---

## Instalación

### Debian / Ubuntu

```sh
sudo apt update && sudo apt install -y hackrf python3-numpy python3-pyqt6 libxcb-cursor0
```

### Arch Linux

```sh
sudo pacman -S hackrf python-numpy python-pyqt6 xcb-util-cursor
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

## Motor independiente

`pocsag_generator.py` construye las tramas con Python estándar. `native_tx.py`
genera I/Q int8 mediante FSK de fase continua, a 12 MS/s y desviación de ±4,5 kHz,
y entrega un archivo temporal a `hackrf_transfer`. El archivo se elimina al terminar.
No se requieren GNU Radio, OsmoSDR ni bitstring. El flujo `.grc` se conserva como referencia histórica.

`--if-gain` controla TX VGA (0–47 dB). `--tx-gain` activa el amplificador RF.
`--bb-gain` se acepta por compatibilidad y se ignora: no es una ganancia de TX.
Recepción del motor independiente confirmada con el busca de prueba a 2400 bps. La polaridad FSK se ha contrastado con la señal del motor original (bit 1: desviación negativa). Los modos numérico y tone-only y los otros bitrates aún necesitan validación física.

Pruebas sin transmisión: `python3 -m unittest -v test_native_tx`.

## Portable v2.1

En Windows, extrae el ZIP completo y abre **POCSAG-Sender.exe**, con el icono de busca verde.
La aplicación se abre sin consola; no se necesita VBS. Conserva `_internal` junto al ejecutable.

La interfaz muestra los mensajes de transmisión en su registro integrado.
El auxiliar CLI vive en `_internal/worker/POCSAG-CLI` y no hace falta abrirlo para usar la interfaz.

### GitHub Actions

El workflow **Build portable applications** se ejecuta al subir cambios a main o master, al crear una etiqueta v* o manualmente desde Actions.
Genera paquetes para Windows x64, Linux x64 y macOS Intel/Apple Silicon,
comprueba las pruebas de señal, la CLI congelada, Qt y las herramientas HackRF incluidas.
Los ZIP aparecen como artefactos del workflow. Una etiqueta `v*` también prepara una
Release en borrador con los ZIP; la validación de radio de cada plataforma se hace con hardware real.

Compilación local: `python scripts/build_portable.py`. Consulta [PORTABLE.md](PORTABLE.md).
