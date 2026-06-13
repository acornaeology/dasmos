"""BBC BASIC packed 5-byte floating-point format.

BBC BASIC (the 6502 versions) stores REAL values as five bytes:

- **byte 0** — exponent, excess-128. A value of ``0`` means the whole
  number is zero (the four mantissa bytes are then conventionally zero
  too).
- **bytes 1-4** — a 32-bit mantissa, most-significant byte first. The
  format is normalised with an *implied leading 1*, so the top bit of
  byte 1 (mantissa bit 31) does not store that 1 — it carries the
  **sign** instead (0 = positive, 1 = negative). The stored 31 bits are
  the fraction after the binary point.

Equivalently: ``value = ±(mantissa) × 2^(exponent − 128)`` with the
magnitude in ``[0.5, 1.0)`` once the implied leading 1 is restored.

This is *not* IEEE 754, and no assembler float literal re-assembles to
the exact five bytes — which is precisely why a typed-data region emits
the raw bytes and carries the decoded value only as an annotation (see
:class:`dasmos.core.data_type.DataType`).

The decode here is verified against the constants in the BBC BASIC II
ROM: ``&AAE4`` → e, ``&AA63`` → π/2, ``&A86E`` → ln 2, ``&A869`` →
log₁₀ e, ``&AA59`` → −π/2.
"""

from __future__ import annotations

from dasmos.core.data_type import DataType, DecodedValue


def decode_bbc_float5(raw: bytes) -> float:
    """Decode five packed BBC BASIC bytes into a Python ``float``.

    ``raw`` must be exactly five bytes (exponent + four mantissa bytes).
    The bytes are never mutated.
    """
    if len(raw) != 5:
        raise ValueError(
            f"bbc_float5 needs exactly 5 bytes; got {len(raw)}"
        )
    exponent = raw[0]
    if exponent == 0:
        # Zero is represented by a zero exponent byte.
        return 0.0
    mantissa = (raw[1] << 24) | (raw[2] << 16) | (raw[3] << 8) | raw[4]
    sign = -1.0 if (mantissa & 0x80000000) else 1.0
    # Restore the implied leading 1 (the bit the sign displaced); the
    # 32-bit value then represents the magnitude's fraction in [0.5, 1).
    magnitude = (mantissa | 0x80000000) / float(1 << 32)
    return sign * magnitude * 2.0 ** (exponent - 128)


class BbcFloat5(DataType):
    """The BBC BASIC packed 5-byte floating-point data type.

    Fixed width of 5 bytes; decodes to a ``float`` surfaced both as the
    structured ``value`` and as ``text``. The text is the **full**
    round-trippable decimal (``repr`` — the shortest decimal that maps
    back to the exact stored value), deliberately *not* rounded: a
    trimmed form like ``2.718281828`` would misleadingly read as true
    e, when the ROM constant is only an approximation
    (``2.718281827867031``). The 32-bit mantissa fits a 64-bit float
    exactly, so the ``float`` is the precise stored value.
    """

    @property
    def name(self) -> str:
        return "bbc_float5"

    @property
    def length(self) -> int:
        return 5

    def decode(self, raw: bytes) -> DecodedValue:
        value = decode_bbc_float5(raw)
        return DecodedValue(
            type_name="bbc_float5",
            text=repr(value),
            value=value,
        )
