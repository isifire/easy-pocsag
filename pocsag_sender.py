#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pocsag_sender.py — CLI de transmisión POCSAG via HackRF One.

Uso básico:
    ./pocsag_sender.py --RIC 1107305 --Text "Hola Mundo"

Uso avanzado (repetición, ganancia personalizada):
    ./pocsag_sender.py --RIC 1107305 --Text "Test" --repeat 3 --repeat-delay 2.5 \\
                       --if-gain 24 --bb-gain 32 --verbose

Créditos: basado en el trabajo de ON1ARF & Tauebenuss.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time

from native_tx import PocsagTransmitter

import pocsag_generator


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _setup_logging(verbose: bool, quiet: bool) -> None:
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        format="[%(levelname)s] %(message)s",
        level=level,
        stream=sys.stderr,
    )


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sanitización de texto
# ---------------------------------------------------------------------------
def sanitize_text(text: str, mode: str) -> str:
    """
    Limpia el texto de entrada según el modo de mensaje.

    - Elimina caracteres de control.
    - Garantiza que termina con espacio (convención POCSAG).
    - En modo numérico, filtra caracteres no numéricos.
    """
    # Eliminar caracteres de control
    cleaned = "".join(c for c in text if ord(c) >= 0x20)
    cleaned = cleaned.replace("\n", " ").replace("\r", "").replace("\x04", "")
    cleaned = cleaned.strip()

    if not cleaned and mode != "tone":
        raise ValueError("El mensaje está vacío tras limpiar caracteres de control.")

    if mode == "numeric":
        valid_chars = set("0123456789 -()" )
        invalid = [c for c in cleaned if c.upper() not in valid_chars and c not in valid_chars]
        if invalid:
            logger.warning("Caracteres no numéricos eliminados: %s", list(set(invalid)))
            cleaned = "".join(c for c in cleaned if c in valid_chars)
        if not cleaned:
            raise ValueError("El mensaje numérico no contiene dígitos válidos.")

    # Añadir espacio final (convención POCSAG)
    if cleaned and not cleaned.endswith(" "):
        cleaned += " "

    return cleaned


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="POCSAG Sender via HackRF One",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s --RIC 1107305 --Text "Hola Mundo"
  %(prog)s --RIC 1107305 --Text "12345" --mode numeric
  %(prog)s --RIC 1107305 --mode tone
  %(prog)s --RIC 1107305 --Text "Test" --repeat 3 --repeat-delay 3 --if-gain 24
""",
    )

    # Parámetros POCSAG
    pager = parser.add_argument_group("Parámetros POCSAG")
    pager.add_argument("--RIC",            type=int,   default=1122551,   help="RIC del receptor (1-2097151)")
    pager.add_argument("--SubRIC",         type=int,   default=0,         help="SubRIC 0-3 (default: 0)")
    pager.add_argument("--Text",           type=str,   default="",        help="Mensaje a enviar")
    pager.add_argument("--pagerfreq",      type=int,   default=148_625_000, help="Frecuencia en Hz (default: 148625000)")
    pager.add_argument("--pocsagbitrate",  type=int,   default=2400,      choices=[512, 1200, 2400], help="Bitrate POCSAG")
    pager.add_argument("--mode",           type=str,   default="alpha",   choices=["alpha", "numeric", "tone"], help="Modo de mensaje")

    # Parámetros de ganancia HackRF
    rf = parser.add_argument_group("Ganancia HackRF")
    rf.add_argument("--tx-gain",  type=int, default=0,  choices=[0, 14],      help="RF gain dB (0 o 14, default: 0)")
    rf.add_argument("--if-gain",  type=int, default=3,                        help="Ganancia TX VGA (0-47 dB, default: 3)")
    rf.add_argument("--bb-gain",  type=int, default=20,                       help="BB gain dB (0-62, step 2, default: 20)")

    # Repetición
    rep = parser.add_argument_group("Repetición")
    rep.add_argument("--repeat",        type=int,   default=1,   help="Número de veces a transmitir (default: 1)")
    rep.add_argument("--repeat-delay",  type=float, default=2.0, help="Segundos entre transmisiones (default: 2.0)")
    rep.add_argument("--delay",         type=float, default=0.0, help="Segundos de espera antes del primer envío")

    # Salida
    out = parser.add_argument_group("Salida")
    out.add_argument("--json-output", action="store_true", help="Emitir resultado en formato JSON")
    out.add_argument("--verbose",     action="store_true", help="Logging detallado (DEBUG)")
    out.add_argument("--quiet",       action="store_true", help="Solo errores")

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_arguments()
    _setup_logging(args.verbose, args.quiet)

    # Sanear texto
    try:
        text = sanitize_text(args.Text, args.mode)
    except ValueError as e:
        logger.error("%s", e)
        if args.json_output:
            print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)

    # Validar SubRIC
    if not (0 <= args.SubRIC <= 3):
        msg = f"SubRIC debe estar entre 0 y 3, recibido: {args.SubRIC}"
        logger.error(msg)
        if args.json_output:
            print(json.dumps({"success": False, "error": msg}))
        sys.exit(1)

    # Pausa inicial
    if args.delay > 0:
        logger.info("Esperando %.1f segundos antes de transmitir...", args.delay)
        time.sleep(args.delay)

    # Bucle de transmisión
    results = []
    for attempt in range(1, args.repeat + 1):
        if args.repeat > 1:
            logger.info("Transmisión %d/%d", attempt, args.repeat)

        try:
            tb = PocsagTransmitter(
                ric=args.RIC,
                subric=args.SubRIC,
                text=text,
                pagerfreq=args.pagerfreq,
                pocsagbitrate=args.pocsagbitrate,
                tx_gain=args.tx_gain,
                if_gain=args.if_gain,
                bb_gain=args.bb_gain,
                mode=args.mode,
            )
            tb.start()
            tb.wait()
            logger.info("✓ Transmisión %d completada.", attempt)
            results.append({"attempt": attempt, "success": True})
        except Exception as e:
            logger.error("✗ Error en transmisión %d: %s", attempt, e)
            results.append({"attempt": attempt, "success": False, "error": str(e)})

        # Pausa entre intentos (no después del último)
        if attempt < args.repeat:
            logger.info("Esperando %.1f segundos antes del siguiente intento...", args.repeat_delay)
            time.sleep(args.repeat_delay)

    # Resultado final
    all_ok = all(r["success"] for r in results)
    if args.json_output:
        print(json.dumps({
            "success": all_ok,
            "ric": args.RIC,
            "subric": args.SubRIC,
            "text": text,
            "freq_hz": args.pagerfreq,
            "bitrate": args.pocsagbitrate,
            "mode": args.mode,
            "attempts": results,
        }, ensure_ascii=False))

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
