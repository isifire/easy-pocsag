# POCSAG Studio

Interfaz web local para enviar mensajes POCSAG con un **HackRF One**.
Motor Python/NumPy independiente de GNU Radio y OsmoSDR.

## Portable

Extrae el ZIP de tu sistema y abre **POCSAG-Sender.exe** (Windows) o **POCSAG-Sender** (Linux/macOS).
La interfaz se abre en el navegador. No hace falta instalar Python ni Qt.
Mantén la carpeta `_internal` junto al ejecutable.

Necesitas el controlador USB del HackRF en Windows, o los permisos USB de tu sistema.
Cierra el programa con **Cerrar aplicación** en la cabecera de la interfaz.

## Desde el código

En Debian/Ubuntu:

```sh
sudo apt install hackrf python3-numpy
python3 app.py
```

En otros sistemas: instala Python 3.12+, NumPy y las herramientas HackRF en PATH.
`python app.py --no-browser` inicia solo el servidor; la dirección queda en `~/.pocsag_sender/web-url.txt`.
El servidor se limita a 127.0.0.1 y los mensajes y perfiles se guardan en tu equipo.

## Funciones

- Mensajes de texto, numéricos y avisos de tono.
- RIC, Sub-RIC, frecuencia y bitrate configurables.
- Ganancia TX VGA (0–47 dB) y amplificador RF.
- Repetición con pausa, cancelación y registro de actividad.
- Historial de 50 intentos y perfiles reutilizables.

La interfaz distingue entre finalizar una transmisión y confirmar que el busca la recibe.
Recepción física validada en Windows portable web, texto a 2400 bps.
El motor se validó también en Linux/WSL; macOS y el resto de modos/bitrates necesitan pruebas físicas.

## CLI

```sh
python pocsag_sender.py --RIC 1107305 --Text "Hola Mundo"
python pocsag_sender.py --RIC 1107305 --Text "12345" --mode numeric
python pocsag_sender.py --RIC 1107305 --mode tone
python pocsag_sender.py --help
```

`--if-gain` controla TX VGA; `--tx-gain` activa el amplificador RF.
`--bb-gain` se conserva por compatibilidad y se ignora en transmisión.

## Compilación y GitHub Actions

```sh
python -m pip install numpy pyinstaller
python scripts/build_portable.py
```

Las herramientas `hackrf_info` y `hackrf_transfer` deben estar en PATH al compilar.
Los paquetes incluyen Python, NumPy, archivos web y herramientas/bibliotecas HackRF.
Cada sistema se compila en su propio entorno.

**Build portable applications** genera paquetes al subir a main/master, manualmente o con etiquetas v*.
Comprueba el motor, la API local y el auxiliar empaquetado. Una etiqueta v* crea una Release en borrador con los ZIP.
Consulta [PORTABLE.md](PORTABLE.md) para instrucciones de uso y distribución.

## Pruebas sin transmisión

```sh
python -m unittest -v test_native_tx test_web_app
```

## Arquitectura

- `web_ui/index.html`: interfaz HTML/CSS/JavaScript, sin recursos remotos.
- `web_app.py`: servidor local, validación y ejecución en segundo plano.
- `pocsag_generator.py`: tramas POCSAG con Python estándar.
- `native_tx.py`: I/Q int8, FSK de fase continua a 12 MS/s y ±4,5 kHz.
- `pocsag_sender.py`: CLI y transmisión mediante hackrf_transfer.
- `config.py`: configuración, perfiles e historial.
- `pocsagsend.grc`: flujo original, conservado como referencia histórica.

La polaridad del motor independiente se contrastó con la señal original: bit 1 con desviación negativa.

## Créditos

Basado en el trabajo original de ON1ARF y Tauebenuss.
Mantenido por [isifire](https://github.com/isifire).
Licencia indicada por el proyecto original: GPL v3.
