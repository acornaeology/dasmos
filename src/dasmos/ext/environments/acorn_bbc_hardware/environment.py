"""BBC Micro hardware-register Environment for dasmos.

The BBC-default register set: CRTC, ACIA, serial ULA, station ID,
video ULA, ROMSEL, the two VIAs, the 8271/1770 floppy controllers,
the ALDC Econet controller, the ADC, and the Tube control registers.

All registered as :meth:`Disassembler.optional_label` — they emit
in the equate table only when actually referenced by the disassembled
code, so adding the environment doesn't pollute output for ROMs that
don't touch any hardware.

Master-only and Electron-only register sets are NOT included here
(this is the BBC B / B+ default). Future plug-ins (or a kwarg) can
flip the machine variant without changing this code's labels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.environment import Environment

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# Each tuple is (addr, name). BBC B / B+ branches only — Master and
# Electron variants are deliberately excluded.

# 6845 CRTC
_CRTC = [
    (0xfe00, "crtc_address_register"),
    (0xfe01, "crtc_register_data"),
]

# 6850 ACIA Serial controller
_ACIA = [
    (0xfe08, "acia_control_or_status"),
    (0xfe09, "acia_data"),
]

# Serial ULA
_SERIAL_ULA = [
    (0xfe10, "serial_ula_set_baud_cassette_and_motor"),
]

# Station ID / NMI control (BBC B, B+)
_STATION_ID = [
    (0xfe18, "station_id_disable_net_nmis"),
]

# Video ULA
_VIDEO_ULA = [
    (0xfe20, "video_ula_control"),
    (0xfe21, "video_ula_palette"),
    (0xfe22, "video_ula_border_colour_and_palette_control"),
    (0xfe23, "video_ula_palette_selection"),
]

# ROMSEL + (B+ also has ACCCON)
_ROMSEL = [
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


_SYSTEM_VIA = _via_labels(0xfe40, "system")
_USER_VIA = _via_labels(0xfe60, "user")

# 8271 / 1770 Floppy disk controller (BBC B, B+)
_FDC = [
    (0xfe80, "fdc_8271_command_or_status_or_1770_drive_control"),
    (0xfe81, "fdc_8271_parameter_or_result"),
    (0xfe82, "fdc_8271_reset"),
    (0xfe84, "fdc_8271_data_or_1770_command_or_status"),
    (0xfe85, "fdc_1770_track"),
    (0xfe86, "fdc_1770_sector"),
    (0xfe87, "fdc_1770_data"),
]

# Fred-bus 1MHz peripheral page (&FC00-&FCFF). Most of Fred is
# expansion / aftermarket — only a few addresses have stable
# meanings across BBC machines. The Acorn SCSI / Winchester hard
# drive interface (used by ADFS-1.30 and similar disk-controller
# ROMs) lives at &FC40-&FC43.
_FRED = [
    (0xfc40, "fred_hard_drive_0"),
    (0xfc41, "fred_hard_drive_1"),
    (0xfc42, "fred_hard_drive_2"),
    (0xfc43, "fred_hard_drive_3"),
]

# 6854 ADLC Econet controller
_ECONET = [
    (0xfea0, "econet_control1_or_status1"),
    (0xfea1, "econet_control23_or_status2"),
    (0xfea2, "econet_data_continue_frame"),
    (0xfea3, "econet_data_terminate_frame"),
]

# ADC (B / B+)
_ADC = [
    (0xfec0, "adc_start_conversion_or_status"),
    (0xfec1, "adc_read_data_high_byte"),
    (0xfec2, "adc_read_data_low_byte"),
]

# Tube control
_TUBE = [
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
_CUBE = [
    (0xfef0, "cube_tube_data_out_from_host"),
    (0xfef1, "cube_tube_data_in_to_host"),
    (0xfefd, "cube_tube_status"),
]


_ALL_LABELS: list[tuple[int, str]] = (
    _CRTC + _ACIA + _SERIAL_ULA + _STATION_ID + _VIDEO_ULA + _ROMSEL
    + _SYSTEM_VIA + _USER_VIA + _FDC + _FRED + _ECONET + _ADC + _TUBE + _CUBE
)


class AcornBbcHardwareEnvironment(Environment):
    """Acorn BBC Micro hardware-register Environment.

    Layered on top of (or instead of) :class:`AcornMosEnvironment`:
    the MOS env covers the OS / vector / workspace addresses, this
    one covers the memory-mapped hardware registers in &FE00-&FEFF.

    Activate via ``Disassembler.use_environment("acorn_bbc_hardware")``
    or ``environments=["acorn_bbc_hardware"]``.
    """

    def __init__(self, name: str = "acorn_bbc_hardware", **kwargs):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        for addr, label_name in _ALL_LABELS:
            disassembler.optional_label(addr, label_name)
