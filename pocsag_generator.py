#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pocsag_generator.py — Bloque GNU Radio para generación de señales POCSAG.

Implementa el estándar POCSAG (Post Office Code Standardisation Advisory Group)
con soporte para mensajes alfanuméricos, numéricos y tone-only.

Créditos: basado en el trabajo de ON1ARF & Tauebenuss.
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
from bitstring import BitArray
from gnuradio import gr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes POCSAG (fijas por el estándar)
# ---------------------------------------------------------------------------
SYNC_PATTERN  = 0xAAAAAAAA   # Preámbulo: alternancia 1/0
SYNC_CODEWORD = 0x7CD215D8   # Palabra de sincronismo de batch
IDLE_PATTERN  = 0x7AC9C197   # Codeword de relleno (idle)

PREAMBLE_WORDS   = 18        # 18 × 32 bits = 576 bits de preámbulo (mínimo estándar)
CODEWORDS_PER_BATCH = 16     # 8 pares de codewords por batch

# Tabla de caracteres numéricos POCSAG (4 bits por dígito, LSB primero)
NUMERIC_CHARS = {
    '0': 0b0000, '1': 0b0001, '2': 0b0010, '3': 0b0011,
    '4': 0b0100, '5': 0b0101, '6': 0b0110, '7': 0b0111,
    '8': 0b1000, '9': 0b1001, ' ': 0b1010, '-': 0b1011,
    '(': 0b1100, ')': 0b1101, 'U': 0b1110, '*': 0b1111,
}

MsgMode = Literal["alpha", "numeric", "tone"]


# ---------------------------------------------------------------------------
# Bloque GNU Radio
# ---------------------------------------------------------------------------
class PocsagSender(gr.sync_block):
    """
    Bloque fuente GNU Radio que emite una trama POCSAG completa.

    El bloque produce exactamente ``msglen`` muestras (de tipo int8) y luego
    devuelve -1 para señalar el fin del flujo, lo que hace que GNU Radio
    detenga el grafo automáticamente.

    Args:
        number:    Número RIC del receptor (1 – 2 097 151).
        source:    SubRIC / fuente (0 – 3).
        sleeptime: Reservado (no usado, por compatibilidad).
        text:      Mensaje a transmitir.
        mode:      "alpha" (alfanumérico), "numeric" (solo dígitos) o "tone".
    """

    def __init__(
        self,
        number: int = 2060073,
        source: int = 0,
        sleeptime: int = 5,
        text: str = "ON1ARF pocsag Python gnuradio",
        mode: MsgMode = "alpha",
    ):
        gr.sync_block.__init__(
            self,
            name="pocsag generator",
            in_sig=[],
            out_sig=[np.int8],
        )

        self.sleeptime = sleeptime
        self.number    = int(number)
        self.source    = int(source)
        self.state     = 0
        self.mode      = mode

        logger.debug(
            "Creando trama POCSAG: RIC=%d subRIC=%d modo=%s texto='%s'",
            number, source, mode, text,
        )

        nbatch, psmsg = self._create_pocsag_message(number, source, text, mode)

        # Silencio proporcional al número de batches al inicio y al final
        silence_samples = 20 * nbatch
        samples: list[int] = [0] * silence_samples

        for word in psmsg:
            samples.extend(
                1 if bit == "1" else -1
                for bit in BitArray(uint=word, length=32).bin
            )

        samples.extend([0] * silence_samples)
        self.pocsagmsg = samples
        self.msglen    = len(samples)

        # output_multiple = msglen garantiza que GNU Radio pida exactamente
        # un bloque completo en la primera (y única) llamada a work()
        self.set_output_multiple(self.msglen)

        logger.info(
            "Trama lista: %d batches, %d muestras totales.", nbatch, self.msglen
        )

    # ------------------------------------------------------------------
    # Interfaz GNU Radio
    # ------------------------------------------------------------------
    def work(self, input_items, output_items):
        if self.state == 0:
            output_items[0][: self.msglen] = np.array(self.pocsagmsg, dtype=np.int8)
            self.state = 1
            return self.msglen
        return -1  # EOS → GNU Radio detiene el grafo

    # ------------------------------------------------------------------
    # Construcción de la trama POCSAG
    # ------------------------------------------------------------------
    @classmethod
    def _create_pocsag_message(
        cls,
        address: int,
        source: int,
        text: str,
        mode: MsgMode,
    ) -> tuple[int, list[int]]:
        """
        Construye la trama POCSAG completa (preámbulo + batches).

        Returns:
            Tupla (número_de_batches, lista_de_words_uint32).
        """
        cls._validate_params(address, source, text, mode)

        # --- Codificar el payload de texto ---
        if mode == "tone":
            textbits = ""
        elif mode == "numeric":
            textbits = cls._encode_numeric(text)
        else:
            textbits = cls._encode_alpha(text)

        # --- Calcular número de codewords de texto y batches necesarios ---
        ncw_text     = (len(textbits) + 19) // 20 if textbits else 0
        addr_cw_pos  = (address % 8) << 1                      # 0..14 (par)
        cw_in_first  = CODEWORDS_PER_BATCH - addr_cw_pos - 1   # disponibles tras address

        if ncw_text <= cw_in_first:
            nbatch = 1
        else:
            extra  = ncw_text - cw_in_first
            nbatch = 1 + (extra + CODEWORDS_PER_BATCH - 1) // CODEWORDS_PER_BATCH

        # --- Rellenar array de codewords con idle ---
        total_cw = nbatch * CODEWORDS_PER_BATCH
        codeword = [IDLE_PATTERN] * total_cw

        # Address codeword
        addressline      = (address >> 3) << 2 | source
        codeword[addr_cw_pos] = cls._calc_crc_parity(0, addressline)

        # Codewords de texto
        cwnum = addr_cw_pos + 1
        for i in range(ncw_text):
            chunk    = textbits[i * 20: (i + 1) * 20].ljust(20, "0")
            thiscw   = int(chunk, 2)
            if cwnum >= total_cw:
                # Salvaguarda (no debería ocurrir con el cálculo correcto)
                codeword.extend([IDLE_PATTERN] * CODEWORDS_PER_BATCH)
                total_cw += CODEWORDS_PER_BATCH
                nbatch   += 1
                logger.warning("Desbordamiento de batch detectado en codeword %d.", cwnum)
            codeword[cwnum] = cls._calc_crc_parity(1, thiscw)
            cwnum += 1

        # --- Construir trama final ---
        frame: list[int] = [SYNC_PATTERN] * PREAMBLE_WORDS
        for batch_idx in range(nbatch):
            frame.append(SYNC_CODEWORD)
            frame.extend(codeword[batch_idx * CODEWORDS_PER_BATCH:
                                   (batch_idx + 1) * CODEWORDS_PER_BATCH])

        return nbatch, frame

    # ------------------------------------------------------------------
    # Codificación de payload
    # ------------------------------------------------------------------
    @staticmethod
    def _encode_alpha(text: str) -> str:
        """Codifica texto alfanumérico como bits POCSAG (LSB primero por carácter, 7 bits)."""
        chars = [ord(c) % 128 for c in text] + [0x04]  # EOT al final
        return "".join(BitArray(uint=c, length=7).bin[::-1] for c in chars)

    @staticmethod
    def _encode_numeric(text: str) -> str:
        """
        Codifica texto numérico como bits POCSAG (4 bits por dígito, LSB primero).
        Caracteres no reconocidos se sustituyen por espacio numérico.
        """
        bits = ""
        for ch in text:
            nibble = NUMERIC_CHARS.get(ch.upper(), NUMERIC_CHARS[" "])
            bits += format(nibble, "04b")[::-1]  # LSB primero
        # EOT numérico = 0xF (1111, revertido = 1111)
        bits += "1111"
        return bits

    # ------------------------------------------------------------------
    # CRC y paridad POCSAG (BCH(31,21) + paridad par)
    # ------------------------------------------------------------------
    @staticmethod
    def _calc_crc_parity(datatype: int, data: int) -> int:
        """
        Calcula el CRC BCH(31,21) y el bit de paridad de un codeword POCSAG.

        Args:
            datatype: 0 = codeword de dirección, 1 = codeword de mensaje.
            data:     Los 21 bits de payload (sin desplazar).

        Returns:
            El codeword de 32 bits completo (payload + CRC + paridad).
        """
        cw = data << 11
        if datatype == 1:
            cw |= 0x80000000

        local_cw = cw
        for _ in range(21):
            if cw & 0x80000000:
                cw ^= 0xED200000
            cw <<= 1

        local_cw |= cw >> 21

        parity = bin(local_cw).count("1") % 2
        local_cw += parity

        return local_cw

    # ------------------------------------------------------------------
    # Validación de parámetros
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_params(address: int, source: int, text: str, mode: MsgMode) -> None:
        if not (0 < address <= 0x1FFFFF):
            raise ValueError(
                f"RIC inválido: {address}. Debe estar entre 1 y 2 097 151."
            )
        if not (0 <= source <= 3):
            raise ValueError(f"SubRIC inválido: {source}. Debe ser 0, 1, 2 o 3.")
        if mode not in ("alpha", "numeric", "tone"):
            raise ValueError(f"Modo inválido: '{mode}'. Usa 'alpha', 'numeric' o 'tone'.")
        if mode != "tone" and len(text) == 0:
            raise ValueError("El mensaje no puede estar vacío en modo alfanumérico/numérico.")
        if mode == "numeric":
            invalid = [c for c in text if c.upper() not in NUMERIC_CHARS]
            if invalid:
                logger.warning(
                    "Caracteres no válidos en modo numérico (se reemplazarán): %s",
                    invalid,
                )
