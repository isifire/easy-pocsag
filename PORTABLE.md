# POCSAG Sender portable

Extrae la carpeta completa antes de abrir POCSAG-Sender. No muevas el ejecutable separado de _internal.
Incluye Python, NumPy, PyQt6 y las herramientas y bibliotecas HackRF. No requiere GNU Radio ni WSL.

Windows: abre únicamente POCSAG-Sender.exe (icono de busca verde). No abre consola; no hay VBS. El dispositivo necesita un controlador USB compatible con libusb/WinUSB.
Linux: ejecuta ./POCSAG-Sender. Se requieren una sesiÃ³n grÃ¡fica y permisos USB/udev para el HackRF.
macOS: ejecuta POCSAG-Sender en una sesiÃ³n grÃ¡fica. Los paquetes sin firma pueden requerir autorizaciÃ³n del sistema.
La compatibilidad depende de la arquitectura y de la versiÃ³n mÃ­nima del SO usada para compilar.

CLI: _internal/worker/POCSAG-CLI/POCSAG-CLI --help (añade .exe en Windows)
Los datos se guardan en ~/.pocsag_sender y sobreviven a las actualizaciones del programa.

## Compilar
Instala Python 3.12, numpy, PyQt6, pyinstaller y hackrf (las herramientas deben estar en PATH).
Ejecuta python scripts/build_portable.py en el sistema destino.
Las compilaciones automÃ¡ticas de Windows, Linux y macOS estÃ¡n en .github/workflows/portable.yml.

## Estado
RecepciÃ³n fÃ­sica validada en Linux/WSL y en el portable nativo de Windows x64, alfanumÃ©rico a 2400 bps.
Cada binario debe probarse en su SO con un HackRF; compilar no demuestra recepciÃ³n fÃ­sica.
Antes de redistribuir, incluye las licencias y avisos de Python, NumPy, Qt/PyQt, HackRF/libusb y el cÃ³digo del proyecto.
PyQt6 y HackRF tienen obligaciones de licencia que tambiÃ©n aplican a paquetes portables.
