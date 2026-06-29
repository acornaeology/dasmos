"""Hardware-register definitions shared between BBC-line variants.

Imported (privately) by the per-machine hardware Environments —
:mod:`dasmos.ext.environments.acorn_model_b_hardware` and
:mod:`dasmos.ext.environments.acorn_master_hardware`. Not itself
a registered Environment plug-in (note the leading underscore).

Each per-machine env starts from this shared base and adds its
own specifics. ``SHARED_LABELS`` is everything where the
register's address *and* meaning are stable across both machines
— the system / user VIAs, CRTC, ACIA, video ULA, ECONET ADLC,
Tube, base ROMSEL, and the Fred-bus SCSI / Winchester block.

Registers whose *address* differs between the machines are NOT in
``SHARED_LABELS``; they live in the machine-specific blocks the
per-machine envs add (see #31):

- The station-ID / NMI-control latch (&FE18) and the μPD7002 ADC
  (&FEC0) are Model-B/B+ placements — exported as
  ``MODEL_B_ONLY_LABELS``. On the Master, &FE18 *is* the ADC and
  the Econet NMI control moves to dedicated INTOFF/INTON latches;
  those Master placements are defined in
  :mod:`acorn_master_hardware`.
- ACCCON (&FE34) exists on the B+ and the Master but not the plain
  Model B — exported as ``ACCCON_LABELS`` for both machine envs to
  include (the env grouping lumps B with B+; a plain-B ROM simply
  never references &FE34, so the optional label never emits).

Floppy-disc-controller registers are deliberately NOT in this
shared block. The choice between the Intel 8271 and the WD1770
is independent of the machine model — Model Bs may have either,
the B+ and Master ship with the 1770, and the two chips share
overlapping addresses (&FE80, &FE84). FDC registers live in
their own composable envs (:mod:`acorn_fdc_8271` /
:mod:`acorn_fdc_1770`) and a driver pairs the appropriate one
with the machine env.
"""

from __future__ import annotations

# Each entry is ``(addr, name)``.

# 6845 CRTC
_CRTC: list[tuple[int, str]] = [
    (0xfe00, "crtc_address_register"),
    (0xfe01, "crtc_register_data"),
]

# 6850 ACIA Serial controller
_ACIA: list[tuple[int, str]] = [
    (0xfe08, "acia_control_or_status"),
    (0xfe09, "acia_data"),
]

# Serial ULA
_SERIAL_ULA: list[tuple[int, str]] = [
    (0xfe10, "serial_ula_set_baud_cassette_and_motor"),
]

# Station ID / NMI control — Model B / B+ only. On the Master,
# &FE18 is the ADC and the Econet NMI control is at &FE38/&FE3C
# (see acorn_master_hardware).
_STATION_ID: list[tuple[int, str]] = [
    (0xfe18, "station_id_disable_net_nmis"),
]

# ACCCON access-control register — present on the B+ and Master
# (shadow-RAM / ROM-banking / IRQ steering), absent on the plain
# Model B. Both machine envs include it (see module docstring).
_ACCCON: list[tuple[int, str]] = [
    (0xfe34, "acccon"),
]

# Video ULA
_VIDEO_ULA: list[tuple[int, str]] = [
    (0xfe20, "video_ula_control"),
    (0xfe21, "video_ula_palette"),
    (0xfe22, "video_ula_border_colour_and_palette_control"),
    (0xfe23, "video_ula_palette_selection"),
]

# ROMSEL (base form — Master extends the semantics, see
# acorn_master_hardware for the high-bit-toggles-internal-vs-
# external-slots variants).
_ROMSEL_BASE: list[tuple[int, str]] = [
    (0xfe30, "romsel"),
]


def _via_labels(base: int, name: str) -> list[tuple[int, str]]:
    """Register the 16 consecutive 6522 VIA register addresses with
    conventional names.
    """
    return [
        (base + 0,  f"{name}_via_orb_irb"),
        (base + 1,  f"{name}_via_ora_ira"),
        (base + 2,  f"{name}_via_ddrb"),
        (base + 3,  f"{name}_via_ddra"),
        (base + 4,  f"{name}_via_t1c_l"),
        (base + 5,  f"{name}_via_t1c_h"),
        (base + 6,  f"{name}_via_t1l_l"),
        (base + 7,  f"{name}_via_t1l_h"),
        (base + 8,  f"{name}_via_t2c_l"),
        (base + 9,  f"{name}_via_t2c_h"),
        (base + 10, f"{name}_via_sr"),
        (base + 11, f"{name}_via_acr"),
        (base + 12, f"{name}_via_pcr"),
        (base + 13, f"{name}_via_ifr"),
        (base + 14, f"{name}_via_ier"),
        (base + 15, f"{name}_via_ora_ira"),
    ]


_SYSTEM_VIA: list[tuple[int, str]] = _via_labels(0xfe40, "system")
_USER_VIA: list[tuple[int, str]] = _via_labels(0xfe60, "user")

# 6854 ADLC Econet controller
_ECONET: list[tuple[int, str]] = [
    (0xfea0, "econet_control1_or_status1"),
    (0xfea1, "econet_control23_or_status2"),
    (0xfea2, "econet_data_continue_frame"),
    (0xfea3, "econet_data_terminate_frame"),
]

def adc_labels(base: int) -> list[tuple[int, str]]:
    """The three μPD7002 ADC registers based at ``base``.

    The register *meaning* is identical across the BBC line; only
    the base address differs — &FEC0 on the Model B / B+, &FE18 on
    the Master. The machine env supplies the base (see #31).
    """
    return [
        (base + 0, "adc_start_conversion_or_status"),
        (base + 1, "adc_read_data_high_byte"),
        (base + 2, "adc_read_data_low_byte"),
    ]

# Tube control
_TUBE: list[tuple[int, str]] = [
    (0xfee0, "tube_status_1_and_tube_control"),
    (0xfee1, "tube_data_register_1"),
    (0xfee2, "tube_status_register_2"),
    (0xfee3, "tube_data_register_2"),
    (0xfee4, "tube_status_register_3"),
    (0xfee5, "tube_data_register_3"),
    (0xfee6, "tube_status_register_4_and_cpu_control"),
    (0xfee7, "tube_data_register_4"),
]

# CUBE Tube control
_CUBE: list[tuple[int, str]] = [
    (0xfef0, "cube_tube_data_out_from_host"),
    (0xfef1, "cube_tube_data_in_to_host"),
    (0xfefd, "cube_tube_status"),
]

# Fred-bus 1MHz peripheral page (&FC00-&FCFF). Most of Fred is
# expansion / aftermarket; only the Acorn SCSI / Winchester hard
# drive interface (&FC40-&FC43) has a stable meaning across BBC
# machines, used by ADFS and similar disk-controller ROMs. The four
# registers are the SCSI host adapter's data, status, select and
# interrupt-enable ports.
_FRED_SHARED: list[tuple[int, str]] = [
    (0xfc40, "scsi_data"),
    (0xfc41, "scsi_status"),
    (0xfc42, "scsi_select"),
    (0xfc43, "scsi_irq_enable"),
]


# The register set common to EVERY BBC-line machine (B, B+,
# Master) at the SAME address. Machine-specific placements
# (station ID, ADC, ACCCON) are deliberately excluded — see the
# module docstring and the exports below. Per-machine envs
# concatenate this with the blocks that apply to them.
SHARED_LABELS: list[tuple[int, str]] = (
    _CRTC + _ACIA + _SERIAL_ULA + _VIDEO_ULA + _ROMSEL_BASE
    + _SYSTEM_VIA + _USER_VIA + _ECONET
    + _TUBE + _CUBE + _FRED_SHARED
)

# Model B / B+ placements: the station-ID / NMI-control latch at
# &FE18 and the ADC at &FEC0. Added by acorn_model_b_hardware; the
# Master env puts the ADC at &FE18 instead (see #31).
MODEL_B_ONLY_LABELS: list[tuple[int, str]] = _STATION_ID + adc_labels(0xfec0)

# ACCCON (&FE34): included by both the Model-B/B+ env and the
# Master env (B+ and Master have it; plain Model B does not).
ACCCON_LABELS: list[tuple[int, str]] = _ACCCON
