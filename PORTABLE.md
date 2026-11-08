# POCSAG Studio · Portable web local

## Abrir

Extrae la carpeta completa y abre **POCSAG-Sender.exe** en Windows.
En Linux/macOS ejecuta **POCSAG-Sender**. El programa abre una pestaña en tu navegador.
Conserva `_internal` junto al ejecutable; contiene Python, NumPy, la interfaz web y las herramientas HackRF.
No requiere instalar Python, Qt, GNU Radio ni OsmoSDR.
Se necesita un navegador moderno y el controlador o los permisos USB correspondientes al sistema.

El servidor escucha únicamente en 127.0.0.1. No sube tus mensajes a ningún servicio.
Puedes cerrar una pestaña y volver a abrir la aplicación para recuperar la interfaz.
Usa **Cerrar aplicación** en la cabecera para detener el servidor local.

## Hardware

La opción **Ayuda USB** de la web contiene los enlaces e instrucciones.

Windows: controlador compatible con libusb/WinUSB para el HackRF.
Linux: permisos USB/udev. macOS: acceso al dispositivo y autorización de apertura si el paquete no está firmado.
La compatibilidad depende de la arquitectura y de la versión mínima del SO de compilación.

## Datos

La configuración, los perfiles y los últimos 50 intentos se guardan en ~/.pocsag_sender.
«Transmisión finalizada» confirma la entrega al transmisor; no confirma la recepción por el busca.

## CLI

_internal/worker/POCSAG-CLI/POCSAG-CLI --help (añade .exe en Windows).

## Compilar

Python 3.12, numpy, pyinstaller y hackrf en PATH.
Ejecuta python scripts/build_portable.py en el sistema destino.
GitHub Actions genera Windows x64, Linux x64 y macOS Intel/Apple Silicon.
Una etiqueta v* publica una Release; las etiquetas con guion son preliminares. También se puede compilar manualmente.

## Validación

Recepción física confirmada en el portable web de Windows: modo alfanumérico a 2400 bps.
El motor también se validó en Linux/WSL. macOS, otros modos y bitrates requieren validación física.

## Distribución

Revisa e incluye las licencias y avisos de Python, NumPy, HackRF, libusb y el código del proyecto antes de redistribuir.
