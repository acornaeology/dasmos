"""Disassembly driver for Acorn Econet Bridge version 1.

Configures py8dis to produce an annotated disassembly of the Econet
Bridge ROM.

Run via:
  uv run python versions/econet-bridge-variant_1/disassemble/disasm_econet_bridge_variant_1.py

The bridge contains an 8 KB ROM mapped at &E000-&FFFF on its own
6502 processor. The hardware vectors are the last six bytes of the
ROM:

  &FFFA/B  NMI   vector
  &FFFC/D  RESET vector
  &FFFE/F  IRQ/BRK vector
"""

import json
import os
import sys
from pathlib import Path

from py8dis.commands import *

init(assembler_name="beebasm", lower_case=True)

_script_dirpath = Path(__file__).resolve().parent
_version_dirpath = _script_dirpath.parent
# `fantasm disassemble VID` sets FANTASM_ROM / FANTASM_OUTPUT_DIR;
# direct `python <driver>` invocations fall back to the conventional
# paths under the version directory.
_rom_filepath = os.environ.get(
    "FANTASM_ROM",
    str(_version_dirpath / "rom" / "econet-bridge-variant_1.rom"),
)
_output_dirpath = Path(os.environ.get(
    "FANTASM_OUTPUT_DIR",
    str(_version_dirpath / "output"),
))

load(0xE000, _rom_filepath, "6502")

# =====================================================================
# Hardware vectors
# =====================================================================
# The reset vector at &FFFC tells us where execution begins; the IRQ
# vector at &FFFE tells us where interrupts are serviced. These are
# the primary entry points into the ROM.

_reset_lo = get_u8_binary(0xFFFC)
_reset_hi = get_u8_binary(0xFFFD)
_reset_addr = _reset_lo | (_reset_hi << 8)

_irq_lo = get_u8_binary(0xFFFE)
_irq_hi = get_u8_binary(0xFFFF)
_irq_addr = _irq_lo | (_irq_hi << 8)

_nmi_lo = get_u8_binary(0xFFFA)
_nmi_hi = get_u8_binary(0xFFFB)
_nmi_addr = _nmi_lo | (_nmi_hi << 8)

entry(_reset_addr)
label(_reset_addr, "reset")
comment(0xE000, "Enable IRQs (self-test button wired to ~IRQ)", inline=True)
comment(0xE001, "Clear decimal mode (6502 arithmetic in binary)", inline=True)
comment(0xE002, "Initialise reachable_via_a/b tables for routing", inline=True)
comment(0xE005, "Reset ADLC A through its full CR1/CR2/CR3/CR4 sequence", inline=True)
comment(0xE008, "Reset ADLC B through its full CR1/CR2/CR3/CR4 sequence", inline=True)

if 0xE000 <= _irq_addr <= 0xFFF9:
    entry(_irq_addr)
    label(_irq_addr, "self_test")
    # Hardware hint: the Bridge has a push-button pulling the 6502
    # ~IRQ line low (it's believed to be the only thing wired to that
    # pin). Pressing it enters the firmware's self-test routine – not
    # to be pressed while connected to a live network. So the IRQ
    # handler is effectively the self-test entry point, with BRK
    # sharing the same vector. The ADLC-generated interrupts that
    # drive Econet traffic are polled rather than vectored (see the
    # wait_adlc_*_irq helpers).

if 0xE000 <= _nmi_addr <= 0xFFF9:
    entry(_nmi_addr)
    label(_nmi_addr, "nmi_handler")

# Checksum-tuning byte at the top of the ROM-tail padding region.
# The self-test at &F04C checks that every byte of the ROM sums to
# &55 mod 256; without this byte, the sum would be &0F, and the
# value &46 at this address (and only this address, the rest of
# the tail being unwritten &FF filler) has been deliberately
# chosen by the firmware author to bring the total up by the
# required &46 to land on the expected &55. The specific value
# isn't meaningful, only its role in balancing the sum.
byte(0xFFF0)
comment(0xFFF0, "Checksum-tuning byte: balances the ROM sum to &55")
label(0xFFF0, "rom_checksum_adjust")

# &FF padding regions in the ROM tail. Declaring them as fills rather
# than letting them default to auto-byte classification collapses
# thousands of equb lines into three FOR loops in the beebasm output,
# while still round-tripping to byte-identical bytes at assembly time.
#   &E728-&EFFF  (2264 bytes) after wait_adlc_a_idle, before the
#                self-test ROM begins at &F000.
#   &F30B-&FFEF  (3301 bytes) after self_test_fail_spacer_delay's
#                JMP, before [`rom_checksum_adjust`](address:FFF0?hex).
#   &FFF1-&FFF9  (9 bytes)    between rom_checksum_adjust and the
#                three hardware vectors at &FFFA-&FFFF.
fill(0xE728, 2264)
fill(0xF30B, 3301)
fill(0xFFF1, 9)

# Subroutine-style banner for the first (and largest) padding region.
# Not a subroutine – py8dis's banner rendering is the cleanest way
# to put a visible section break into the listing between the main
# code body and the self-test ROM.
subroutine(0xE728, "rom_body_gap", hook=None,
    title="ROM body gap – unused space before the self-test",
    description="""\
2264 bytes of `&FF` padding between the end of the main code at
[`wait_adlc_a_idle_ready`](address:E71F) and the start of the
self-test entry at [`self_test`](address:F000?hex).

The region is simply the unused tail of the main-code half of the
ROM, before the self-test at the page-aligned `&F000`.""")

subroutine(0xFFF1, "rom_vector_gap", hook=None,
    title="ROM vector gap – unused bytes before the hardware vectors",
    description="""\
9 bytes of `&FF` padding between
[`rom_checksum_adjust`](address:FFF0?hex) at `&FFF0` and the 6502
hardware vector table at [`&FFFA`](address:FFFA?hex).

The firmware author had 10 bytes (`&FFF0-&FFF9`) to choose from for
the sum-balancing byte; they placed `&46` at `&FFF0` and left the
remaining nine as `&FF`.""")

# Hardware vector data declarations
word(0xFFFA)
if 0xE000 <= _nmi_addr <= 0xFFF9:
    expr(0xFFFA, "nmi_handler")
comment(0xFFFA, "NMI vector", inline=True)

word(0xFFFC)
expr(0xFFFC, "reset")
comment(0xFFFC, "RESET vector", inline=True)

word(0xFFFE)
if 0xE000 <= _irq_addr <= 0xFFF9:
    expr(0xFFFE, "self_test")
comment(0xFFFE, "IRQ/BRK vector", inline=True)

subroutine(0xFFFA, "hardware_vectors", hook=None,
    title="6502 hardware vector table",
    description="""\
The three addresses the 6502 fetches when an interrupt fires:

| Offset | Purpose | Target |
|--------|---------|--------|
| `&FFFA-&FFFB` | NMI vector | `&FFFF` (unused) |
| `&FFFC-&FFFD` | RESET vector | [`reset`](address:E000?hex) |
| `&FFFE-&FFFF` | IRQ/BRK vector | [`self_test`](address:F000?hex) |

NMI isn't wired to anything on the Bridge board, so the slot is
filled with `&FFFF` rather than a real handler. RESET enters the
main firmware at `&E000`. IRQ/BRK – the line the self-test
push-button pulls low – enters at `&F000`; pressing the button
therefore runs the self-test, and any `BRK` instruction anywhere
in the ROM would do the same thing.""")


# =====================================================================
# Hardware register map
# =====================================================================
# Outside the loaded ROM range, so declared with constant() rather
# than label(). Addresses confirmed by inspecting access patterns in
# the first-pass disassembly:
#
# - &C000 / &D000 are only ever read, consistent with the two
#   74LS244 buffers that expose the network-number selection links
#   (one per Econet port – each side of the Bridge has its own
#   network number, configured by jumpers/links on the board).
# - &C800-&C803 and &D800-&D803 are accessed with the exact pattern
#   of an MC6854 ADLC – CR1/SR1 at offset 0, CR2/SR2 at 1, TX/RX
#   FIFO at 2 and 3, with BIT reads of SR1 used to poll IRQ status
#   (the chip IRQ outputs are not wired to the 6502).
#
# Register semantics depend on the AC bit (Address Control) in CR1:
# when AC=0 the second-bank registers (CR2, SR2) are accessed at
# offsets 1; when AC=1 the fourth-bank registers (CR3, CR4) are
# accessed at offsets 0 and 1. The Acorn NFS disassembly uses the
# pre-AC names (cr1/cr2/tx/tx2) and we follow the same convention.

# Zero-page workspace used by the self-test's scanning loops. The
# self-test cannot rely on mem_ptr_lo/hi at &80/&81 because those
# sit in the RAM it is about to test; &00-&03 give it an independent
# parallel scratch zone. st_ptr_lo/hi plus st_page_count form a
# 16-bit pointer + page counter for the ROM checksum and RAM pattern
# scans; st_pass_phase is a pass-phase selector toggled each run.
label(0x0000, "st_ptr_lo",
    description="Low byte of the self-test scan pointer.\n"
                "Paired with [`st_ptr_hi`](address:0001) to form a "
                "16-bit indirect pointer walked by "
                "[`self_test_rom_checksum`](address:F04C) and "
                "[`self_test_ram_pattern`](address:F070).\n\n"
                "Also used as an anti-aliasing tripwire byte (the "
                "`INC $00`) in [`ram_test`](address:E00B), and as "
                "a scratch victim byte during "
                "[`self_test_zp`](address:F02F) when the zero-page "
                "itself is under test.",
    length=1, group="zero_page", access="rw")
label(0x0001, "st_ptr_hi",
    description="High byte of the self-test scan pointer.\n"
                "Paired with [`st_ptr_lo`](address:0000); incremented "
                "page by page as the scanning loops stride through "
                "each 256-byte block of ROM or RAM.\n\n"
                "Also a scratch victim byte during "
                "[`self_test_zp`](address:F02F).",
    length=1, group="zero_page", access="rw")
label(0x0002, "st_page_count",
    description="Page counter for the self-test scans.\n"
                "Pre-loaded with a hard-coded `&20` (32 pages = 8 KiB) "
                "at every site and decremented once per page by "
                "[`self_test_rom_checksum`](address:F04C), "
                "[`self_test_ram_pattern`](address:F070), and both "
                "phases of [`self_test_ram_incr`](address:F0A0). The "
                "self-test therefore always covers exactly the low 8 "
                "KiB of RAM (`&0000-&1FFF`) and the 8 KiB ROM "
                "(`&E000-&FFFF`), regardless of what the boot-time "
                "[`ram_test`](address:E00B) found: this counter is "
                "never loaded from [`top_ram_page`](address:0082).\n\n"
                "Also a scratch victim byte during "
                "[`self_test_zp`](address:F02F).",
    length=1, group="zero_page", access="rw")
label(0x0003, "st_pass_phase",
    description="Self-test pass-phase flag.\n"
                "Initialised by [`self_test`](address:F000) at entry "
                "and toggled by "
                "[`self_test_pass_done`](address:F264) at the end of "
                "each full pass; bit 7 then selects between a plain "
                "restart from [`self_test_reset_adlcs`](address:F005) "
                "and the alternate path through "
                "[`self_test_alt_pass`](address:F26F), which drives "
                "the ADLC control registers slightly differently to "
                "catch intermittent faults.",
    length=1, group="zero_page", access="rw")

# Zero-page workspace used by the main code. mem_ptr_lo and mem_ptr_hi
# form an indirect pointer scanned upward one page at a time;
# top_ram_page receives the last page that verified &AA/&55 patterns
# during ram_test and is used later by workspace init.
label(0x0080, "mem_ptr_lo",
    description="Low byte of the indirect pointer.\n"
                "Paired with [`mem_ptr_hi`](address:0081).\n\n"
                "Used by [`ram_test`](address:E00B) to scan memory "
                "upward one page at a time, and by the TX/RX byte "
                "loops in the frame handlers, e.g. "
                "[`transmit_frame_a`](address:E517).",
    length=1, group="zero_page", access="rw")
label(0x0081, "mem_ptr_hi",
    description="High byte of the indirect pointer.\n"
                "Paired with [`mem_ptr_lo`](address:0080).",
    length=1, group="zero_page", access="rw")
label(0x0082, "top_ram_page",
    description="Highest page that verified `&AA`/`&55` during "
                "[`ram_test`](address:E00B).\n"
                "Used later by workspace initialisation to decide "
                "how much RAM is safe to touch.",
    length=1, group="zero_page", access="rw")

label(0xC000, "net_num_a",
    description="Econet side A network number, read at `&C000`.\n"
                "Sourced from a bank of jumpered links buffered by a "
                "74LS244. 7-bit (range 1-127); the top link is always "
                "made, so bit 7 reads 0.\n\n"
                "The Bridge has no station number of its own – it "
                "sits on each Econet segment as a promiscuous receiver "
                "and broadcaster.",
    length=1, group="io_a", access="r")
label(0xD000, "net_num_b",
    description="Econet side B network number, read at `&D000`.\n"
                "Sourced from a bank of jumpered links buffered by a "
                "74LS244. 7-bit (range 1-127); the top link is always "
                "made, so bit 7 reads 0.\n\n"
                "Paired with [`net_num_a`](address:C000) on the "
                "opposite segment.",
    length=1, group="io_b", access="r")

label(0xC800, "adlc_a_cr1",
    description="ADLC A control/status port 0.\n\n"
                "**Write:** CR1 (or CR3 when AC=1 in CR1). "
                "**Read:** SR1.\n\n"
                "IRQ summary is in SR1 bit 7; "
                "[`wait_adlc_a_irq`](address:E3E4) spins on it.",
    length=1, group="io_a", access="rw")
label(0xC801, "adlc_a_cr2",
    description="ADLC A control/status port 1.\n\n"
                "**Write:** CR2 (or CR4 when AC=1). **Read:** SR2.",
    length=1, group="io_a", access="rw")
label(0xC802, "adlc_a_tx",
    description="ADLC A TX/RX FIFO port.\n\n"
                "**Write:** push a byte into the TX FIFO (frame "
                "continues). **Read:** pop a byte from the RX FIFO.",
    length=1, group="io_a", access="rw")
label(0xC803, "adlc_a_tx2",
    description="ADLC A TX-last-byte port.\n"
                "**Write:** push the final byte of a frame (chip "
                "closes the frame and appends the FCS + flag). Reading "
                "this port is not used by the Bridge.",
    length=1, group="io_a", access="w")

label(0xD800, "adlc_b_cr1",
    description="ADLC B control/status port 0.\n\n"
                "**Write:** CR1 (or CR3 when AC=1 in CR1). "
                "**Read:** SR1.\n\n"
                "IRQ summary is in SR1 bit 7; "
                "[`wait_adlc_b_irq`](address:E3EA) spins on it.\n\n"
                "CR3 bit 7 (reached via this port with AC=1) drives "
                "IC18's `~LOC/DTR` pin, which sources current to the "
                "front-panel status LED (anode tied to the pin, "
                "cathode to ground). The MC6854 inverts the bit when "
                "driving the pin, so CR3 bit 7 = 0 puts the pin HIGH "
                "and the LED LIT; CR3 bit 7 = 1 puts the pin LOW and "
                "the LED DARK. [`adlc_b_full_reset`](address:E40A) "
                "writes CR3 = &00 (LED on – the steady normal-"
                "operation state); "
                "[`self_test_reset_adlcs`](address:F005) writes "
                "CR3 = &80 (LED off – marks the start of a self-test "
                "pass).",
    length=1, group="io_b", access="rw")
label(0xD801, "adlc_b_cr2",
    description="ADLC B control/status port 1.\n\n"
                "**Write:** CR2 (or CR4 when AC=1). **Read:** SR2.",
    length=1, group="io_b", access="rw")
label(0xD802, "adlc_b_tx",
    description="ADLC B TX/RX FIFO port.\n\n"
                "**Write:** push a byte into the TX FIFO (frame "
                "continues). **Read:** pop a byte from the RX FIFO.",
    length=1, group="io_b", access="rw")
label(0xD803, "adlc_b_tx2",
    description="ADLC B TX-last-byte port.\n"
                "**Write:** push the final byte of a frame (chip "
                "closes the frame and appends the FCS + flag). Reading "
                "this port is not used by the Bridge.",
    length=1, group="io_b", access="w")


# =====================================================================
# ADLC polled-IRQ waits
# =====================================================================
# Each ADLC raises IRQ in SR1 bit 7 when attention is required. Since
# the 6502 ~IRQ line is used for the self-test button, the firmware
# polls SR1 for these helpers.

label(0xE3E4, "wait_adlc_a_irq")
subroutine(0xE3E4, "wait_adlc_a_irq", hook=None,
    title="Wait for ADLC A IRQ (polled)",
    description="""\
Spin reading SR1 of ADLC A until the IRQ bit (bit 7) is set. Called
from 19 sites where the code needs to wait for the ADLC to signal
an event (frame complete, RX data available, TX ready, etc.).

The Bridge does not route the ADLC `~IRQ` output to the 6502 `~IRQ`
line (that pin is used for the self-test push-button), so ADLC
attention is obtained by polling.""")

comment(0xE3E4, "Peek ADLC A status, testing the IRQ-summary bit", inline=True)
comment(0xE3E7, "Spin while the chip has nothing to report", inline=True)
comment(0xE3E9, "Event pending; return to caller to handle it", inline=True)

label(0xE3EA, "wait_adlc_b_irq")
subroutine(0xE3EA, "wait_adlc_b_irq", hook=None,
    title="Wait for ADLC B IRQ (polled)",
    description="""\
As [`wait_adlc_a_irq`](address:E3E4) but for ADLC B.""")

comment(0xE3EA, "Peek ADLC B status, testing the IRQ-summary bit", inline=True)
comment(0xE3ED, "Spin while the chip has nothing to report", inline=True)
comment(0xE3EF, "Event pending; return to caller to handle it", inline=True)


# =====================================================================
# ADLC full reset + enter listen
# =====================================================================
# Each pair (full_reset → listen) is called in sequence by the main
# reset handler at &E000 and from a few other paths that need to re-
# synchronise the chip. The two pairs are byte-for-byte mirrors --
# only the register addresses differ.
#
# Same ADLC initialisation sequence as Acorn NFS's adlc_full_reset +
# adlc_rx_listen (NFS 3.34 at &96DC / &96EB). This is the root of the
# shared-code region recorded in shared-code.json at &E3EF (matcher's
# alignment) / &E3F0 (actual subroutine start).

label(0xE3F0, "adlc_a_full_reset")
subroutine(0xE3F0, "adlc_a_full_reset", hook=None,
    title="ADLC A full reset, then enter RX listen",
    description="""\
Aborts all ADLC A activity and returns it to idle RX listen mode.
Falls through to [`adlc_a_listen`](address:E3FF). Called from the reset handler.""")

comment(0xE3F0, "Mask: reset TX and RX, unlock CR3/CR4 via AC=1", inline=True)
comment(0xE3F2, "Drop ADLC A into full reset", inline=True)
comment(0xE3F5, "Mask: 8-bit RX word length, abort-extend, NRZ", inline=True)
comment(0xE3F7, "Program CR4 (reached via tx2 slot while AC=1)", inline=True)
comment(0xE3FA, "Mask: no loopback, DTR released, NRZ encoding", inline=True)
comment(0xE3FC, "Program CR3 (reached via cr2 slot while AC=1); fall through", inline=True)

label(0xE3FF, "adlc_a_listen")
subroutine(0xE3FF, "adlc_a_listen", hook=None,
    title="Enter ADLC A RX listen mode",
    description="""\
TX held in reset, RX active. IRQs are generated internally by the
chip but the ~IRQ output is not wired; see [`wait_adlc_a_irq`](address:E3E4).""")

comment(0xE3FF, "Mask: keep TX in reset, enable RX IRQs, AC=0", inline=True)
comment(0xE401, "Commit CR1; subsequent cr2/tx writes hit CR2/TX again", inline=True)
comment(0xE404, "Mask: clear status flags, FC_TDRA, 2/1-byte, PSE", inline=True)
comment(0xE406, "Commit CR2; ADLC A now listening for incoming frames", inline=True)
comment(0xE409, "Return; Econet side A is idle-listen", inline=True)

label(0xE40A, "adlc_b_full_reset")
subroutine(0xE40A, "adlc_b_full_reset", hook=None,
    title="ADLC B full reset, then enter RX listen",
    description="""\
Byte-for-byte mirror of [`adlc_a_full_reset`](address:E3F0), targeting ADLC B's
register set at `&D800-&D803`. Falls through to
[`adlc_b_listen`](address:E419). `CR3=&00` puts the LOC/DTR pin
HIGH, sourcing current through the front-panel status LED – so the
LED is LIT throughout normal operation, the distinguishing feature
from [`self_test_reset_adlcs`](address:F005) which writes CR3 = &80
to extinguish it.""")

comment(0xE40A, "Mask: reset TX and RX, unlock CR3/CR4 via AC=1", inline=True)
comment(0xE40C, "Drop ADLC B into full reset", inline=True)
comment(0xE40F, "Mask: 8-bit RX word length, abort-extend, NRZ", inline=True)
comment(0xE411, "Program CR4 (reached via tx2 slot while AC=1)", inline=True)
comment(0xE414, "Mask: CR3 bit 7 clear → LOC/DTR pin high → status LED ON", inline=True)
comment(0xE416, "Program CR3; fall through into listen mode", inline=True)

label(0xE419, "adlc_b_listen")
subroutine(0xE419, "adlc_b_listen", hook=None,
    title="Enter ADLC B RX listen mode",
    description="""\
Mirror of [`adlc_a_listen`](address:E3FF) for ADLC B.""")

comment(0xE419, "Mask: keep TX in reset, enable RX IRQs, AC=0", inline=True)
comment(0xE41B, "Commit CR1; subsequent cr2/tx writes hit CR2/TX again", inline=True)
comment(0xE41E, "Mask: clear status flags, FC_TDRA, 2/1-byte, PSE", inline=True)
comment(0xE420, "Commit CR2; ADLC B now listening for incoming frames", inline=True)
comment(0xE423, "Return; Econet side B is idle-listen", inline=True)


# =====================================================================
# Inter-network routing tables
# =====================================================================
# Two 256-byte arrays indexed by destination
# NETWORK NUMBER (not station number). A non-zero entry means
# "this destination network is reachable from here".
#
#   reachable_via_b  at &025A  consulted by rx_frame_a.
#       Networks known to be accessible by forwarding an incoming
#       side-A frame out of side B. Initialised with net_num_b
#       (our own B-side network, directly reachable) and 255
#       (broadcast). Extended by bridge-announcement messages
#       received on side A.
#
#   reachable_via_a  at &035A  consulted by rx_frame_b.
#       Mirror.
#
# Naming note: the earlier provisional names `reachable_via_b` and
# `reachable_via_a` reflected which *handler* used them, not what they
# represented. Semantics resolved once the payload processing in
# rx_a_handle_80 revealed the map as a routing table.
label(0x025A, "reachable_via_b",
    description="256-byte routing table for forwarding out of side B.\n"
                "Indexed by destination **network** number; a non-zero "
                "entry means \"this network is reachable from here\".\n\n"
                "Consulted by [`rx_frame_a`](address:E0E2). Initialised "
                "with [`net_num_b`](address:D000) (our own side-B "
                "network, directly reachable) and 255 (broadcast), "
                "then extended by bridge-announcement messages "
                "received on side A.",
    length=256, group="ram_buffers", access="rw")
label(0x035A, "reachable_via_a",
    description="256-byte routing table for forwarding out of side A.\n"
                "Indexed by destination **network** number; a non-zero "
                "entry means \"this network is reachable from here\".\n\n"
                "Consulted by [`rx_frame_b`](address:E263). Initialised "
                "with [`net_num_a`](address:C000) (our own side-A "
                "network, directly reachable) and 255 (broadcast), "
                "then extended by bridge-announcement messages "
                "received on side B.",
    length=256, group="ram_buffers", access="rw")

# Multi-byte counter reused for different purposes by several
# routines. [`wait_adlc_a_idle`](address:E6DC?hex) uses all three bytes as a
# 24-bit timeout; [`stagger_delay`](address:E448?hex) uses only the low byte as
# an 8-bit delay counter. Byte-aligned rather than semantic names
# so the shared use is explicit.
label(0x0214, "ctr24_lo",
    description="Low byte of a 24-bit counter reused by several "
                "routines.\n"
                "[`wait_adlc_a_idle`](address:E6DC) uses all three "
                "bytes as a timeout; "
                "[`stagger_delay`](address:E448) uses this low byte "
                "alone as an 8-bit delay.",
    length=1, group="ram_workspace", access="rw")
label(0x0215, "ctr24_mid",
    description="Middle byte of the 24-bit counter.\n"
                "Rooted at [`ctr24_lo`](address:0214).",
    length=1, group="ram_workspace", access="rw")
label(0x0216, "ctr24_hi",
    description="High byte of the 24-bit counter.\n"
                "Rooted at [`ctr24_lo`](address:0214).",
    length=1, group="ram_workspace", access="rw")

# RX frame buffer. Inbound frames are drained from the ADLC's RX
# FIFO into this 20-byte region during the side-A and side-B
# handlers. The first six bytes are the Econet scout-frame header;
# bytes 6 onward are payload (max 14 bytes captured, enough for the
# Bridge-protocol message formats).
label(0x023C, "rx_dst_stn",
    description="RX frame buffer byte 0 – destination station number.\n"
                "First byte of the 20-byte RX staging area at "
                "`&023C-&024F` filled by "
                "[`rx_frame_a`](address:E0E2) / "
                "[`rx_frame_b`](address:E263).",
    length=1, group="ram_buffers", access="rw")
label(0x023D, "rx_dst_net",
    description="RX frame buffer byte 1 – destination network "
                "number.",
    length=1, group="ram_buffers", access="rw")
label(0x023E, "rx_src_stn",
    description="RX frame buffer byte 2 – source station number.",
    length=1, group="ram_buffers", access="rw")
label(0x023F, "rx_src_net",
    description="RX frame buffer byte 3 – source network number.",
    length=1, group="ram_buffers", access="rw")
label(0x0240, "rx_ctrl",
    description="RX frame buffer byte 4 – control byte.\n"
                "Bridge protocol uses `&80`..`&83`; see "
                "[`rx_frame_a_dispatch`](address:E14A).",
    length=1, group="ram_buffers", access="rw")
label(0x0241, "rx_port",
    description="RX frame buffer byte 5 – port number.\n"
                "The bridge-protocol port is `&9C`.",
    length=1, group="ram_buffers", access="rw")
# Payload bytes at &0242-&024F; named as they become understood.
# Byte 12 (&0248) holds a port number the querier wants the response
# on; byte 13 (&0249) holds a network number that ctrl=&83 queries
# ask about (the &83 path consults it against reachable_via_b, which
# is network-keyed).
label(0x0248, "rx_query_port",
    description="RX frame buffer byte 12 – port on which the querier "
                "wants the bridge to send its response.",
    length=1, group="ram_buffers", access="rw")
label(0x0249, "rx_query_net",
    description="RX frame buffer byte 13 – network number that a "
                "`ctrl=&83` (IsNet) query is asking about.\n"
                "Checked against [`reachable_via_b`](address:025A) / "
                "[`reachable_via_a`](address:035A) in the query "
                "handlers.",
    length=1, group="ram_buffers", access="rw")
label(0x0228, "rx_len",
    description="Byte count received into the RX frame buffer.\n"
                "Written by the drain loop once the ADLC reports "
                "end-of-frame; read back by the dispatch paths to "
                "decide how many payload bytes to process.",
    length=1, group="ram_workspace", access="rw")

# Event-driven re-announcement state. The Bridge does NOT re-
# announce on a periodic self-triggered timer – it only advertises
# itself (BridgeReply/ctrl=&81 frames) in response to hearing a
# BridgeReset (ctrl=&80) from another bridge. The entire state
# machine is therefore quiescent unless a peer has just reset.
#
# The flow is:
#
#   rx_?_handle_80   sets announce_flag to &40 (side A selected)
#                    or &80 (side B), announce_count to 10, and
#                    announce_tmr_lo/hi to net_num_?:00 (staggered
#                    from our own network number).
#
#   main_loop_idle   decrements the 16-bit timer on every idle
#                    iteration; when it reaches zero, re_announce
#                    runs.
#
#   re_announce      emits one BridgeReply, decrements
#                    announce_count, and re-arms the timer to
#                    &8000 for the next cycle.
#
#   re_announce_done fires when announce_count hits zero. Clears
#                    announce_flag; the idle path stops noticing
#                    until another BridgeReset arrives.
#
# A solo bridge with no peers is silent after its boot-time pair
# of BridgeReset scouts – there's nothing to trigger the flag.
# See docs/analysis/event-driven-reannouncement.md.
label(0x0229, "announce_flag",
    description="Event-driven re-announcement selector.\n\n"
                "Set by [`rx_a_handle_80`](address:E1D6) / "
                "[`rx_b_handle_80`](address:E357) to `&40` (side A "
                "selected) or `&80` (side B) when a peer bridge's "
                "`BridgeReset` scout arrives. Cleared in "
                "[`re_announce_done`](address:E0C2) once all ten "
                "`BridgeReply` frames have been emitted.\n\n"
                "Polled by [`main_loop_idle`](address:E089); the "
                "entire re-announcement state machine is quiescent "
                "while this byte is zero.",
    length=1, group="ram_workspace", access="rw")
label(0x022A, "announce_tmr_lo",
    description="Low byte of the 16-bit re-announcement countdown.\n"
                "Decremented every pass through "
                "[`main_loop_idle`](address:E089); fires "
                "[`re_announce`](address:E098) when it reaches zero.",
    length=1, group="ram_workspace", access="rw")
label(0x022B, "announce_tmr_hi",
    description="High byte of the 16-bit re-announcement countdown.\n"
                "Paired with [`announce_tmr_lo`](address:022A).",
    length=1, group="ram_workspace", access="rw")
label(0x022C, "announce_count",
    description="Remaining `BridgeReply` frames to emit in the "
                "current re-announcement burst.\n"
                "Initialised to 10 when a peer `BridgeReset` is "
                "heard, decremented in "
                "[`re_announce`](address:E098), and clears "
                "[`announce_flag`](address:0229) on reaching zero.",
    length=1, group="ram_workspace", access="rw")

# Outbound-frame control block at &045A-&0460. Populated by the
# frame-builder subroutines, then consumed by transmit_frame_a (via
# mem_ptr at &80/&81 = &045A). Names follow the Acorn Econet scout-
# frame convention – but Econet has both scout and data frames,
# and the two share a header layout only for the first four bytes
# (dst_stn, dst_net, src_stn, src_net). In a scout frame, bytes 4
# and 5 are ctrl and port; in a data frame, bytes 4 onward are
# pure payload with no ctrl/port. The same buffer serves both frame
# types in this firmware, with the caller choosing the semantics.
# See the WhatNet query-response code in rx_a_handle_82, where the
# "tx_ctrl" and "tx_port" slots are populated with data bytes for
# the data half of the 4-way handshake.
label(0x045A, "tx_dst_stn",
    description="TX frame buffer byte 0 – destination station number.\n"
                "First byte of the outbound frame staging area at "
                "`&045A-&0460+`, populated by the frame-builder "
                "subroutines and consumed by "
                "[`transmit_frame_a`](address:E517) / "
                "[`transmit_frame_b`](address:E4C0).",
    length=1, group="ram_buffers", access="rw")
label(0x045B, "tx_dst_net",
    description="TX frame buffer byte 1 – destination network "
                "number.",
    length=1, group="ram_buffers", access="rw")
label(0x045C, "tx_src_stn",
    description="TX frame buffer byte 2 – source station number.",
    length=1, group="ram_buffers", access="rw")
label(0x045D, "tx_src_net",
    description="TX frame buffer byte 3 – source network number.",
    length=1, group="ram_buffers", access="rw")
label(0x045E, "tx_ctrl",
    description="TX frame buffer byte 4 – control byte in a scout "
                "frame, or the first data byte in a data frame.\n"
                "The same buffer serves both frame types; the caller "
                "chooses the semantics.",
    length=1, group="ram_buffers", access="rw")
label(0x045F, "tx_port",
    description="TX frame buffer byte 5 – port in a scout frame, or "
                "the second data byte in a data frame.\n"
                "Pair with [`tx_ctrl`](address:045E).",
    length=1, group="ram_buffers", access="rw")
label(0x0460, "tx_data0",
    description="TX frame buffer byte 6 – first optional scout "
                "payload byte.\n"
                "For example, a queried network number in a "
                "`WhatNet` response.",
    length=1, group="ram_buffers", access="rw")

# Transmit end-pointer (16-bit, consumed by transmit_frame_a). The
# main TX loop sends byte pairs from mem_ptr upward and terminates
# once mem_ptr+Y reaches or passes (tx_end_hi:tx_end_lo). Builders
# for the "6-byte frame header" case write tx_end_lo=&06 and
# tx_end_hi=&04, corresponding to end address &0406 when combined
# with the buffer start at &045A (so the loop transmits up to Y=6,
# i.e. the 6 header bytes).
label(0x0200, "tx_end_lo",
    description="Low byte of the TX end-pointer, consumed by "
                "[`transmit_frame_a`](address:E517).\n"
                "The TX loop sends byte pairs from "
                "[`mem_ptr_lo`](address:0080) upward and terminates "
                "once the index reaches or passes this pointer.",
    length=1, group="ram_workspace", access="rw")
label(0x0201, "tx_end_hi",
    description="High byte of the TX end-pointer.\n"
                "Paired with [`tx_end_lo`](address:0200).",
    length=1, group="ram_workspace", access="rw")


# =====================================================================
# Initialise per-station tables
# =====================================================================

label(0xE424, "init_reachable_nets")
subroutine(0xE424, "init_reachable_nets", hook=None,
    title="Reset both routing tables to the directly-attached networks",
    description="""\
Zeroes the two 256-entry routing tables (`reachable_via_a` at `&035A`
and `reachable_via_b` at `&025A`), then writes `&FF` to four slots
that are true by virtue of the Bridge's immediate topology:

| slot                          | meaning                                   |
|-------------------------------|-------------------------------------------|
| `reachable_via_a[net_num_a]`  | side A's own network is reachable via A   |
| `reachable_via_b[net_num_b]`  | side B's own network is reachable via B   |
| `reachable_via_a[255]`        | broadcast network reachable via either    |
| `reachable_via_b[255]`        | side                                      |

Everything else starts at zero and is populated later by
bridge-protocol announcements learned in the rx handlers (see
[`rx_a_handle_80`](address:E1D6) / [`rx_b_handle_80`](address:E357)).

Called from the reset handler and also re-invoked from the two
`rx_?_handle_80` paths – receiving an initial bridge announcement
indicates a topology change that invalidates the learned state, so
the Bridge forgets everything and starts accumulating again.""")

comment(0xE424, "Y: walks every network number 0..255", inline=True)
comment(0xE426, "A = 0: 'route not known' marker", inline=True)
label(0xE428, "init_reachable_nets_clear")
comment(0xE428, "Clear side-A handler's entry for network Y", inline=True)
comment(0xE42B, "Clear side-B handler's entry for network Y", inline=True)
comment(0xE42E, "Step to next network number", inline=True)
comment(0xE42F, "Loop back until Y wraps through all 256 slots", inline=True)
comment(0xE431, "A = &FF: 'route known' marker for the writes below", inline=True)
comment(0xE433, "Y = net_num_a: our own side-A network number", inline=True)
comment(0xE436, "side-B handler can reach net_num_a via side A", inline=True)
comment(0xE439, "Y = net_num_b: our own side-B network number", inline=True)
comment(0xE43C, "side-A handler can reach net_num_b via side B", inline=True)
comment(0xE43F, "Y = 255: the Econet broadcast network", inline=True)
comment(0xE441, "Broadcasts reachable for side-A handler's traffic", inline=True)
comment(0xE444, "Broadcasts reachable for side-B handler's traffic", inline=True)
comment(0xE447, "Tables primed; return to caller", inline=True)


# =====================================================================
# RAM test
# =====================================================================
# Reached by fall-through from the reset handler after the two ADLCs
# have been initialised. Scans pages from &1800 upward, writing &AA
# and &55 patterns through an indirect pointer and reading them
# back. The highest page that verifies is stored in top_ram_page
# (&82) as the top-of-RAM marker used later by workspace init.
#
# The INC on zero-page &00 between each write and read disturbs zero
# page – a non-existent or aliased target page then cannot pass the
# test on data-bus residue from the last write. This is a deliberate
# anti-aliasing defence rather than a counter.

label(0xE00B, "ram_test")
subroutine(0xE00B, "ram_test", hook=None, is_entry_point=False,
    title="Scan pages from &1800 upward; record top of RAM",
    description="""\
Probes pages upward from `&1800` by writing `&AA` and `&55` patterns
through `mem_ptr_lo`/`mem_ptr_hi` (`&80`/`&81`) and verifying each.
The highest page that verifies is stored in `top_ram_page` (`&82`),
used downstream by workspace initialisation. The Bridge can be built
with either one 8 KiB 6264 chip or four 2 KiB 6116 chips (chosen by
soldered links), so RAM size must be discovered at power-on.

The routine looks like a textbook two-pattern memory test but is
considerably more robust than a naive STA/LDA/CMP would be. Three
independent mechanisms have to fail simultaneously for it to report
RAM where none exists:

1. The `INC` on zero-page `&00` between each write and its matching
   read is an **anti-bus-residue defence**. When the 6502 writes to
   an unmapped address, no chip latches the value, but the data-bus
   capacitance can hold the written byte long enough for the
   subsequent `LDA` to sample its own ghost. `INC $00` is a
   read-modify-write that drives the data bus three times with values
   unrelated to the test pattern (the cycle-4 dummy write is a
   classic NMOS 6502 quirk that is exploited here), clobbering any
   residue of `&AA` or `&55`.
2. The choice of `&00` specifically is an **alias tripwire**. If the
   address decoder is miswired and the target address aliases into
   zero page, the obvious alias landing point is `&00` – so
   disturbing `&00` between write and read forces any alias-based
   false-positive to fail the `CMP`.
3. The two patterns `&AA` and `&55` are **bitwise complements**: a
   stuck bit is detected on whichever pattern it contradicts, and a
   single-value bus residue cannot spoof both checks simultaneously.

See `docs/analysis/ram-test-anti-aliasing.md` for the full
cycle-level analysis.""")

comment(0xE00B, "Y = 0: ZP offset used by (mem_ptr_lo),Y throughout", inline=True)
comment(0xE00D, "Clear mem_ptr_lo so every probe is page-aligned", inline=True)
comment(0xE00F, "A = &17: seed for mem_ptr_hi (first probe will be page &18)", inline=True)
comment(0xE011, "Commit mem_ptr_hi; first INC at loop head advances to &18", inline=True)

label(0xE013, "ram_test_loop")
comment(0xE013, "Step up to the next candidate page", inline=True)
comment(0xE015, "Pattern 1: &AA (1010_1010) – half the bits set", inline=True)
comment(0xE017, "Write &AA to (mem_ptr_lo) indirect", inline=True)
comment(0xE019, "INC $00: read-modify-write disturbs the data bus…", inline=True)
comment(0xE01B, "…then read the probe byte back", inline=True)
comment(0xE01D, "Did &AA survive the disturbance?", inline=True)
comment(0xE01F, "Mismatch → this page isn't real RAM; back off", inline=True)
comment(0xE021, "Pattern 2: &55 (0101_0101) – exact complement of &AA", inline=True)
comment(0xE023, "Write &55 to (mem_ptr_lo) indirect", inline=True)
comment(0xE025, "INC $00 again – anti-aliasing tripwire", inline=True)
comment(0xE027, "Read pattern 2 back", inline=True)
comment(0xE029, "Did &55 survive?", inline=True)
comment(0xE02B, "Both patterns held – real RAM, try next page", inline=True)

label(0xE02D, "ram_test_done")
comment(0xE02D, "Step back one: last-probed page failed, prior page was OK", inline=True)
comment(0xE02F, "Read the highest-verified page number", inline=True)
comment(0xE031, "Save as top_ram_page; workspace init caps buffers here", inline=True)


# =====================================================================
# Reset-time dual broadcast of BridgeReset
# =====================================================================
# Falls through from ram_test. Seeds announce_flag = 0 so the main
# loop's idle path stays dormant until a peer triggers it, builds the
# BridgeReset template once, transmits it on side A (carrying
# net_num_b), then patches the single payload byte and retransmits on
# side B (carrying net_num_a). Falls through into main_loop – no RTS
# because this is still the reset path, not a callable routine.
#
# See docs/analysis/two-broadcasts-one-template.md and
# docs/analysis/event-driven-reannouncement.md for the protocol story.

label(0xE033, "reset_announce_broadcasts")
subroutine(0xE033, "reset_announce_broadcasts", hook=None,
    is_entry_point=False,
    title="Emit the boot-time BridgeReset pair on both Econet sides",
    description="""\
Second half of the reset handler. Clears `announce_flag` so the
idle-path re-announcer starts quiescent, then builds a single
BridgeReset template (`ctrl=&80`, `port=&9C`, `payload=net_num_b`)
via [`build_announce_b`](address:E458) and transmits it twice:
first on side A with `net_num_b` in the payload, then on side B
after patching the payload to `net_num_a`. The two
[`wait_adlc_a_idle`](address:E6DC) /
[`wait_adlc_b_idle`](address:E690) calls gate each transmit on
carrier-sense; either can escape to [`main_loop`](address:E051)
if the line never goes idle.

Falls through to [`main_loop`](address:E051) on success. A clean
reset therefore emits exactly two frames before steady-state
polling begins. See `docs/analysis/two-broadcasts-one-template.md`
for why one template suffices.""")

comment(0xE033, "A = 0: clear announce_flag (idle path stays quiet initially)", inline=True)
comment(0xE035, "Commit announce_flag = 0 to workspace", inline=True)
comment(0xE038, "Build the BridgeReset scout template into &045A-&0460", inline=True)
comment(0xE03B, "CSMA: wait for side A's line to go idle", inline=True)
comment(0xE03E, "Transmit first broadcast (announcing net_num_b to side A)", inline=True)
comment(0xE041, "Load net_num_a – the payload byte for the B-side broadcast", inline=True)
comment(0xE044, "Patch payload byte 0 of the template in-place", inline=True)
comment(0xE047, "A = &04: reset mem_ptr_hi to the template's base page…", inline=True)
comment(0xE049, "…so [`transmit_frame_b`](address:E4C0) re-reads from &045A", inline=True)
comment(0xE04B, "CSMA: wait for side B's line to go idle", inline=True)
comment(0xE04E, "Transmit second broadcast (announcing net_num_a to side B)", inline=True)


# =====================================================================
# Build bridge-announcement frame for Econet side B
# =====================================================================

label(0xE458, "build_announce_b")
subroutine(0xE458, "build_announce_b", hook=None,
    title="Build a BridgeReset scout carrying net_num_b as payload",
    description="""\
Populates the outbound frame control block at `&045A-&0460` with an
all-broadcast BridgeReset scout – `ctrl=&80`, `port=&9C`,
`payload=net_num_b`. At reset time this is transmitted via ADLC A
first (announcing "network `net_num_b` is reachable through me" to
side A's stations), then `tx_data0` is patched to `net_num_a` and
the same frame is re-transmitted via ADLC B.

| field        | value        | meaning                             |
|--------------|--------------|-------------------------------------|
| `tx_dst_stn` | `&FF`        | broadcast station                   |
| `tx_dst_net` | `&FF`        | broadcast network                   |
| `tx_src_stn` | `&18`        | firmware marker (see below)         |
| `tx_src_net` | `&18`        | firmware marker (see below)         |
| `tx_ctrl`    | `&80`        | initial-announcement ctrl           |
| `tx_port`    | `&9C`        | bridge-protocol port                |
| `tx_data0`   | `net_num_b`  | network number on side B            |

The `src_stn`/`src_net` fields are both set to the constant `&18`.
The Bridge has no station number of its own (only network numbers,
per the Installation Guide), so these fields are not real addresses.
Receivers do not use them for routing --
[`rx_a_handle_81`](address:E1EE) reads the payload starting at offset
6 and ignores bytes 2-3 entirely. The most plausible role for `&18`
is defensive redundancy: together with `dst=(&FF,&FF)`,
`ctrl=&80`/`&81` and `port=&9C` it gives a receiver multiple ways to
confirm that a received frame is a well-formed bridge announcement.

Also writes `&06` to `tx_end_lo` and `&04` to `tx_end_hi` (so the
transmit routine sends bytes `&045A..&0460` inclusive – 7 bytes
when X=1), loads X=1 (trailing-byte flag for
[`transmit_frame_a`](address:E517)), and points `mem_ptr` at the
frame block (`&045A`).

Called from the reset handler at [`&E038`](address:E038) and again
from [`&E098`](address:E098) (the main-loop periodic re-announce
path). A structurally identical cousin builder is
[`build_query_response`](address:E48D?hex), called from four sites;
it populates the same fields with values drawn from RAM variables
at `rx_src_stn` and `rx_query_net` rather than baked-in constants.""")

comment(0xE458, "Broadcast marker &FF for dst station AND network", inline=True)
comment(0xE45A, "Write dst_stn = 255 into the frame header", inline=True)
comment(0xE45D, "Write dst_net = 255 into the frame header", inline=True)
comment(0xE460, "Firmware marker &18 for src fields (no station id)", inline=True)
comment(0xE462, "Write src_stn = &18", inline=True)
comment(0xE465, "Write src_net = &18", inline=True)
comment(0xE468, "Bridge-protocol port number", inline=True)
comment(0xE46A, "Write port = &9C into the frame header", inline=True)
comment(0xE46D, "Control byte: &80 = BridgeReset (initial announcement)", inline=True)
comment(0xE46F, "Write ctrl = &80 into the frame header", inline=True)
comment(0xE472, "Payload: our side-B network number to announce", inline=True)
comment(0xE475, "Write as data byte 0 (trailing byte after header)", inline=True)
comment(0xE478, "X = 1: ask transmit_frame_? to send the trailing byte too", inline=True)
comment(0xE47A, "Low byte of tx-end: &06 == 6 header bytes", inline=True)
comment(0xE47C, "Store low byte of tx_end", inline=True)
comment(0xE47F, "High byte of tx-end: &04 matches mem_ptr_hi below", inline=True)
comment(0xE481, "Store high byte of tx_end (end pair = &0406)", inline=True)
comment(0xE484, "Low byte of mem_ptr: frame starts at &045A", inline=True)
comment(0xE486, "Store mem_ptr_lo", inline=True)
comment(0xE488, "High byte of mem_ptr: page &04", inline=True)
comment(0xE48A, "Store mem_ptr_hi (pointer = &045A)", inline=True)
comment(0xE48C, "Return; caller may now transmit the BridgeReset scout", inline=True)


# =====================================================================
# Main Bridge loop (post-reset dispatcher)
# =====================================================================

label(0xE051, "main_loop")
subroutine(0xE051, "main_loop", hook=None, is_entry_point=False,
    title="Main Bridge loop: re-arm ADLCs, poll for frames, re-announce",
    description="""\
The Bridge's continuous-operation entry point. Reached by fall-
through from the reset handler once startup completes, and by JMP
from fourteen other sites – every routine that takes an "escape to
main" path ([`wait_adlc_a_idle`](address:E6DC), [`transmit_frame_a`](address:E517)/[`transmit_frame_b`](address:E4C0), etc.)
lands here, so main_loop is the anchor of every packet-processing cycle.

The header (&E051-&E078) forces each ADLC into a known RX-listening
state: if SR2 bit 0 or 7 (AP or RDA) is already set from a partial
or aborted previous operation, CR1 is cycled through &C2 (reset TX,
leave RX running) before setting it to &82 (TX in reset, RX IRQs
enabled). CR2 is set to &67 – the standard listen-mode value used
throughout the firmware.

The inner poll loop at [`main_loop_poll`](address:E079?hex) tests SR1 bit 7 (IRQ
summary) on each ADLC in turn, with side B checked first. If either
chip has a pending IRQ, control jumps straight to the corresponding
frame handler; otherwise the idle path at [`main_loop_idle`](address:E089?hex)
runs the periodic re-announcement.

The re-announce scheme uses three bytes of workspace:

| byte                   | role                                                                                         |
|------------------------|----------------------------------------------------------------------------------------------|
| `announce_flag`        | enables re-announce; bit 7 additionally selects which side the re-announce goes out on       |
| `announce_tmr_lo/hi`   | 16-bit countdown, decremented every idle-path iteration; zero triggers the re-announce       |
| `announce_count`       | remaining re-announce cycles; when this hits zero, `announce_flag` is cleared and re-announce stops until something else re-enables it |

The re-announce path ([`re_announce`](address:E098)) rebuilds the
announcement frame, sets `tx_ctrl` to `&81` (distinguishing it from
the reset-time `&80` first announcement), then dispatches to side A
or side B based on `announce_flag` bit 7. The timer is re-armed to
`&8000` (32768 idle iterations) after each announce, giving a
roughly constant cadence regardless of how busy the ADLCs are with
other traffic.""")

comment(0xE051, "Read ADLC A's SR2", inline=True)
comment(0xE054, "Mask AP/RDA bits to test for any stale RX state", inline=True)
comment(0xE056, "Clean → skip the TX reset", inline=True)
comment(0xE058, "Mask: reset TX, leave RX running", inline=True)
comment(0xE05A, "Clear any stale TX state on ADLC A", inline=True)
label(0xE05D, "main_loop_arm_a")
comment(0xE05D, "X = &82: listen-mode CR1 (TX reset, RX IRQ)", inline=True)
comment(0xE05F, "Commit CR1 on ADLC A", inline=True)
comment(0xE062, "Y = &67: listen-mode CR2 (status-clear pattern)", inline=True)
comment(0xE064, "Commit CR2 on ADLC A", inline=True)
comment(0xE067, "Read ADLC B's SR2", inline=True)
comment(0xE06A, "Mask AP/RDA to test for any stale RX state", inline=True)
comment(0xE06C, "Clean → skip the TX reset on B", inline=True)
comment(0xE06E, "Mask: reset TX, leave RX running", inline=True)
comment(0xE070, "Clear any stale TX state on ADLC B", inline=True)
label(0xE073, "main_loop_arm_b")
comment(0xE073, "Commit CR1 on ADLC B (X still = &82)", inline=True)
comment(0xE076, "Commit CR2 on ADLC B (Y still = &67)", inline=True)


label(0xE0E2, "rx_frame_a")
subroutine(0xE0E2, "rx_frame_a", hook=None, is_entry_point=False,
    title="Drain and dispatch an inbound frame on ADLC A",
    description="""\
Reached from [`main_loop_poll`](address:E079) when ADLC A raises SR1 bit 7. Drains the
incoming scout frame from the RX FIFO into the `rx_*` buffer at
`&023C-&024F`, runs two levels of filtering, and then dispatches on the
control byte to per-message handlers.

1. **Addressing filter.** Expect SR2 bit 0 (AP: Address Present) – if
   missing, bail to [`main_loop`](address:E051) (spurious IRQ). Read byte 0
   (`rx_dst_stn`) and byte 1 (`rx_dst_net`). If `rx_dst_net` is zero
   (local net) or `reachable_via_b[rx_dst_net]` is zero (unknown
   network), jump to [`rx_a_not_for_us`](address:E13F?hex): ignore the frame,
   re-listen, drop back to `main_loop_poll` without a full
   `main_loop` re-init.

2. **Drain.** Read the rest of the frame in byte-pairs into
   `&023C+Y` up to `Y=20` (the Bridge only keeps the first 20
   bytes). After the drain, force `CR1=0` and `CR2=&84` to halt the
   chip and test SR2 bit 1 (FV, Frame Valid). If FV is clear, the
   frame was corrupt or short – bail to `main_loop`. If SR2 bit 7
   (RDA) is also set, read one trailing byte.

3. **Broadcast check.** Only frames with `dst_stn == dst_net == &FF`
   (full broadcast) proceed to the bridge-protocol dispatcher.
   Everything else falls to [`rx_a_forward`](address:E208?hex), the
   cross-network forwarding path.

4. **Dispatch on `rx_ctrl`** (after verifying `rx_port == &9C`, the
   bridge-protocol port):

   | ctrl  | handler                                   | role                            |
   |-------|-------------------------------------------|---------------------------------|
   | `&80` | [`rx_a_handle_80`](address:E1D6)          | initial bridge announcement     |
   | `&81` | [`rx_a_handle_81`](address:E1EE)          | re-announcement                 |
   | `&82` | [`rx_a_handle_82`](address:E19D)          | bridge query (tentative)        |
   | `&83` | [`rx_a_handle_83`](address:E195)          | bridge query, known-station     |
   | other | [`rx_a_forward`](address:E208)            | forward or discard              |

The side-B handler [`rx_frame_b`](address:E263?hex) is the mirror of this
routine.""")

comment(0xE0E2, "A = &01: mask SR2 bit 0 (AP = Address Present)", inline=True)
comment(0xE0E4, "BIT SR2 – confirm the IRQ was a frame start", inline=True)
comment(0xE0E7, "AP not set → spurious IRQ, return to [`main_loop`](address:E051)", inline=True)
comment(0xE0E9, "Read FIFO byte 0: destination station", inline=True)
comment(0xE0EC, "Stage dst_stn into the rx header buffer", inline=True)
comment(0xE0EF, "Block until ADLC A IRQs again (byte 1 ready)", inline=True)
comment(0xE0F2, "BIT SR2 – RDA still set for the next byte?", inline=True)
comment(0xE0F5, "RDA cleared: frame truncated before dst_net, bail", inline=True)
comment(0xE0F7, "Read byte 1 into Y: destination network", inline=True)
comment(0xE0FA, "dst_net == 0 means 'local net of sender' – not for us", inline=True)
comment(0xE0FC, "Probe reachable_via_b[dst_net] for a route via side B", inline=True)
comment(0xE0FF, "No route → frame isn't ours to drain, re-listen", inline=True)
comment(0xE101, "Commit dst_net now that it has passed filtering", inline=True)
comment(0xE104, "Y = 2: resume drain at offset 2 (after header)", inline=True)

label(0xE106, "rx_frame_a_drain")
comment(0xE106, "Wait for the next FIFO byte IRQ", inline=True)
comment(0xE109, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xE10C, "RDA cleared mid-body → go to FV check", inline=True)
comment(0xE10E, "Read byte Y of payload from TX/RX FIFO", inline=True)
comment(0xE111, "Store into rx_dst_stn+Y (buffer grows into rx_*)", inline=True)
comment(0xE114, "Advance Y to the next slot", inline=True)
comment(0xE115, "Read byte Y+1 (pair-read without an IRQ wait)", inline=True)
comment(0xE118, "Store the second byte of the pair", inline=True)
comment(0xE11B, "Advance Y past the pair", inline=True)
comment(0xE11C, "Cap at 20 bytes (6-byte header + up to 14 payload)", inline=True)
comment(0xE11E, "Under cap → keep draining", inline=True)

label(0xE120, "rx_frame_a_end")
comment(0xE120, "A = &00: halt ADLC A", inline=True)
comment(0xE122, "CR1 = 0: disable TX and RX IRQs", inline=True)
comment(0xE125, "A = &84: clear-RX-status + FV-clear bits", inline=True)
comment(0xE127, "Commit CR2: acknowledge end-of-frame", inline=True)
comment(0xE12A, "A = &02: mask SR2 bit 1 (FV: Frame Valid)", inline=True)
comment(0xE12C, "BIT SR2 – test FV and RDA", inline=True)
comment(0xE12F, "FV clear → frame corrupt or short, bail", inline=True)
comment(0xE131, "FV set + no RDA → clean end; go to dispatch", inline=True)
comment(0xE133, "FV + RDA: one trailing byte still in FIFO", inline=True)
comment(0xE136, "Store the odd trailing byte", inline=True)
comment(0xE139, "Advance Y to count that final byte", inline=True)
comment(0xE13A, "Unconditional: continue to dispatch", inline=True)

label(0xE13C, "rx_frame_a_bail")
comment(0xE13C, "Bail: restart from [`main_loop`](address:E051) (full ADLC re-init)", inline=True)

label(0xE13F, "rx_a_not_for_us")
comment(0xE13F, "A = &A2: RX on, IRQ enabled, TX in reset", inline=True)
comment(0xE141, "Re-arm ADLC A to listen for the next frame", inline=True)
comment(0xE144, "Skip [`main_loop`](address:E051) re-init; go straight back to polling", inline=True)

label(0xE147, "rx_a_to_forward")
comment(0xE147, "Out-of-range JMP to [`rx_a_forward`](address:E208) (JSR can't reach)", inline=True)

label(0xE14A, "rx_frame_a_dispatch")
comment(0xE14A, "Save final byte count (even if 0 bytes of payload)", inline=True)
comment(0xE14D, "Compare to 6 – minimum valid scout header", inline=True)
comment(0xE14F, "Shorter than header → bail", inline=True)
comment(0xE151, "Load src_net from the drained frame", inline=True)
comment(0xE154, "Non-zero → sender supplied src_net, keep it", inline=True)
comment(0xE156, "Sender left src_net = 0 ('my local net')", inline=True)
comment(0xE159, "…substitute our own A-side network number", inline=True)
label(0xE15C, "rx_a_src_net_resolved")
comment(0xE15C, "Load our B-side network number for comparison", inline=True)
comment(0xE15F, "Compare against the incoming dst_net", inline=True)
comment(0xE162, "Not for side B → skip the local rewrite", inline=True)
comment(0xE164, "dst_net names our B-side network…", inline=True)
comment(0xE166, "…normalise dst_net to 0 (local on B)", inline=True)
label(0xE169, "rx_a_broadcast_check")
comment(0xE169, "Load dst_stn for the broadcast test", inline=True)
comment(0xE16C, "AND with dst_net (both &FF only if full broadcast)", inline=True)
comment(0xE16F, "Compare result to &FF", inline=True)
comment(0xE171, "Not a full broadcast → forward path", inline=True)
comment(0xE173, "Broadcast: re-arm A's listen mode for any follow-up", inline=True)
comment(0xE176, "A = &C2: reset TX, enable RX", inline=True)
comment(0xE178, "Commit CR1 while we process the bridge-protocol frame", inline=True)
comment(0xE17B, "Load the port byte from the drained frame", inline=True)
comment(0xE17E, "Compare with &9C (bridge-protocol port)", inline=True)
comment(0xE180, "Not our port → drop into forward path", inline=True)
comment(0xE182, "Load ctrl byte for the per-type dispatch", inline=True)
comment(0xE185, "Test &81 (BridgeReply: re-announcement)", inline=True)
comment(0xE187, "Match → [`rx_a_handle_81`](address:E1EE)", inline=True)
comment(0xE189, "Test &80 (BridgeReset: initial announcement)", inline=True)
comment(0xE18B, "Match → [`rx_a_handle_80`](address:E1D6)", inline=True)
comment(0xE18D, "Test &82 (WhatNet: general query)", inline=True)
comment(0xE18F, "Match → [`rx_a_handle_82`](address:E19D)", inline=True)
comment(0xE191, "Test &83 (IsNet: targeted query)", inline=True)
comment(0xE193, "Unknown ctrl → forward path (fall through to [`rx_a_handle_83`](address:E195) on match)", inline=True)


label(0xE316, "rx_b_handle_83")
subroutine(0xE316, "rx_b_handle_83", hook=None, is_entry_point=False,
    title="Side-B IsNet query (ctrl=&83): targeted network lookup",
    description="""\
Mirror of [`rx_a_handle_83`](address:E195?hex) with A/B swapped: consults
reachable_via_a (not _b) because the frame arrived on side B.
Falls through to rx_b_handle_82 when the queried network is
known.""")

comment(0xE316, "Y = the queried network number", inline=True)
comment(0xE319, "Check if we have a route via the other side", inline=True)
comment(0xE31C, "Unknown → silently drop this IsNet query", inline=True)

label(0xE31E, "rx_b_handle_82")
subroutine(0xE31E, "rx_b_handle_82", hook=None, is_entry_point=False,
    title="Side-B WhatNet query (ctrl=&82); also IsNet response path",
    description="""\
Mirror of [`rx_a_handle_82`](address:E19D?hex) with A/B swapped throughout:
stagger seeded from net_num_a, transmit via ADLC B, tx_src_net
patched to net_num_a, response-data's first payload byte (at
the tx_ctrl slot) encodes net_num_b. See rx_a_handle_82 for the
full protocol description.""")

comment(0xE31E, "Re-arm ADLC B into listen mode before replying", inline=True)
comment(0xE321, "Build reply-scout template addressed at the querier", inline=True)
comment(0xE324, "Fetch our side-A network number", inline=True)
comment(0xE327, "Patch src_net so the scout names us by net_num_a", inline=True)
comment(0xE32A, "Copy it into the stagger-delay counter too", inline=True)
comment(0xE32D, "Busy-wait for (net_num_a * ~50us) + 160us", inline=True)
comment(0xE330, "CSMA wait on B", inline=True)
comment(0xE333, "Transmit the reply scout", inline=True)
comment(0xE336, "Wait for the querier's scout-ACK on B", inline=True)
comment(0xE339, "Rebuild template – next frame is the data response", inline=True)
comment(0xE33C, "Fetch net_num_a", inline=True)
comment(0xE33F, "Re-patch src_net", inline=True)
comment(0xE342, "Fetch net_num_b", inline=True)
comment(0xE345, "Write as data-frame payload byte 0", inline=True)
comment(0xE348, "Fetch the network the querier asked about", inline=True)
comment(0xE34B, "Write as data-frame payload byte 1", inline=True)
comment(0xE34E, "Transmit the data frame", inline=True)
comment(0xE351, "Wait for final data-ACK", inline=True)
label(0xE354, "rx_b_query_done")
comment(0xE354, "Transaction complete → back to [`main_loop`](address:E051)", inline=True)


label(0xE357, "rx_b_handle_80")
subroutine(0xE357, "rx_b_handle_80", hook=None, is_entry_point=False,
    title="Side-B BridgeReset (ctrl=&80): learn topology from scratch",
    description="""\
Mirror of [`rx_a_handle_80`](address:E1D6?hex): wipe
`reachable_via_*` via [`init_reachable_nets`](address:E424), seed
the re-announce timer's high byte from `net_num_a` (mirror of
A-side seeding from `net_num_b`), set `announce_count = 10` and
`announce_flag = &80` (bit 7 set = next outbound on side B). Falls
through to [`rx_b_handle_81`](address:E36F).

The other of the two places in the ROM that sets `announce_flag`
non-zero; all other writes to that byte clear it.""")

comment(0xE357, "Wipe all learned routing state (topology reset)", inline=True)
comment(0xE35A, "Fetch our side-A network number", inline=True)
comment(0xE35D, "Use as re-announce timer high byte (stagger)", inline=True)
comment(0xE360, "A = 0: timer low byte", inline=True)
comment(0xE362, "Store timer_lo; first fire in (net_num_a * 256) ticks", inline=True)
comment(0xE365, "A = 10: number of BridgeReplies to emit", inline=True)
comment(0xE367, "Store the burst count", inline=True)
comment(0xE36A, "A = &80: enable re-announce, bit 7 set = send via B", inline=True)
comment(0xE36C, "Set announce_flag; main loop will now schedule the burst", inline=True)

label(0xE36F, "rx_b_handle_81")
subroutine(0xE36F, "rx_b_handle_81", hook=None, is_entry_point=False,
    title="Side-B BridgeReply (ctrl=&81): learn and re-broadcast",
    description="""\
Mirror of [`rx_a_handle_81`](address:E1EE?hex): reads each payload byte from
offset 6 onward as a network number reachable via side B, marks
reachable_via_b[x] = &FF for each (mirror of the A-side writing
reachable_via_a). Appends net_num_b to the payload and falls
through to [`rx_b_forward`](address:E389) for re-broadcast onto side A.""")

comment(0xE36F, "Y = 6: skip past the 6-byte scout header", inline=True)
label(0xE371, "rx_b_learn_loop")
comment(0xE371, "Fetch next announced network number from payload", inline=True)
comment(0xE374, "X = the network to record", inline=True)
comment(0xE375, "A = &FF: 'route known' marker", inline=True)
comment(0xE377, "Remember that network X is reachable via side B", inline=True)
comment(0xE37A, "Advance to next payload byte", inline=True)
comment(0xE37B, "Have we reached the end of the payload?", inline=True)
comment(0xE37E, "No – keep learning", inline=True)
comment(0xE380, "Load our own side-B network number", inline=True)
comment(0xE383, "Append it to the payload for the onward broadcast", inline=True)
comment(0xE386, "Payload grew by one byte; record the new length", inline=True)


label(0xE263, "rx_frame_b")
subroutine(0xE263, "rx_frame_b", hook=None, is_entry_point=False,
    title="Drain and dispatch an inbound frame on ADLC B",
    description="""\
Byte-for-byte mirror of [`rx_frame_a`](address:E0E2?hex): same
three-stage structure (addressing filter, drain, broadcast +
bridge-protocol check), same control-byte dispatch, with
`adlc_a_*` replaced by `adlc_b_*`, `reachable_via_b` by
`reachable_via_a`, and the side-selector value swaps
(`net_num_a` &harr; `net_num_b`) where appropriate.

Bridge-protocol dispatch for this side:

| ctrl  | handler                              | role                        |
|-------|--------------------------------------|-----------------------------|
| `&80` | [`rx_b_handle_80`](address:E357)     | initial bridge announcement |
| `&81` | [`rx_b_handle_81`](address:E36F)     | re-announcement             |
| `&82` | [`rx_b_handle_82`](address:E31E)     | bridge query (shared &83)   |
| `&83` | [`rx_b_handle_83`](address:E316)     | bridge query, known-station |
| other | [`rx_b_forward`](address:E389)       | forward or discard          |

See [`rx_frame_a`](address:E0E2) for the full per-instruction
explanation.""")

comment(0xE263, "A = &01: mask SR2 bit 0 (AP = Address Present)", inline=True)
comment(0xE265, "BIT SR2 – confirm the IRQ was a frame start", inline=True)
comment(0xE268, "AP not set → spurious IRQ, return to [`main_loop`](address:E051)", inline=True)
comment(0xE26A, "Read FIFO byte 0: destination station", inline=True)
comment(0xE26D, "Stage dst_stn into the rx header buffer", inline=True)
comment(0xE270, "Block until ADLC B IRQs again (byte 1 ready)", inline=True)
comment(0xE273, "BIT SR2 – RDA still set for the next byte?", inline=True)
comment(0xE276, "RDA cleared: frame truncated before dst_net, bail", inline=True)
comment(0xE278, "Read byte 1 into Y: destination network", inline=True)
comment(0xE27B, "dst_net == 0 means 'local net of sender' – not for us", inline=True)
comment(0xE27D, "Probe reachable_via_a[dst_net] for a route via side A", inline=True)
comment(0xE280, "No route → frame isn't ours to drain, re-listen", inline=True)
comment(0xE282, "Commit dst_net now that it has passed filtering", inline=True)
comment(0xE285, "Y = 2: resume drain at offset 2 (after header)", inline=True)

label(0xE287, "rx_frame_b_drain")
comment(0xE287, "Wait for the next FIFO byte IRQ", inline=True)
comment(0xE28A, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xE28D, "RDA cleared mid-body → go to FV check", inline=True)
comment(0xE28F, "Read byte Y of payload from TX/RX FIFO", inline=True)
comment(0xE292, "Store into rx_dst_stn+Y (buffer grows into rx_*)", inline=True)
comment(0xE295, "Advance Y to the next slot", inline=True)
comment(0xE296, "Read byte Y+1 (pair-read without an IRQ wait)", inline=True)
comment(0xE299, "Store the second byte of the pair", inline=True)
comment(0xE29C, "Advance Y past the pair", inline=True)
comment(0xE29D, "Cap at 20 bytes (6-byte header + up to 14 payload)", inline=True)
comment(0xE29F, "Under cap → keep draining", inline=True)

label(0xE2A1, "rx_frame_b_end")
comment(0xE2A1, "A = &00: halt ADLC B", inline=True)
comment(0xE2A3, "CR1 = 0: disable TX and RX IRQs", inline=True)
comment(0xE2A6, "A = &84: clear-RX-status + FV-clear bits", inline=True)
comment(0xE2A8, "Commit CR2: acknowledge end-of-frame", inline=True)
comment(0xE2AB, "A = &02: mask SR2 bit 1 (FV: Frame Valid)", inline=True)
comment(0xE2AD, "BIT SR2 – test FV and RDA", inline=True)
comment(0xE2B0, "FV clear → frame corrupt or short, bail", inline=True)
comment(0xE2B2, "FV set + no RDA → clean end; go to dispatch", inline=True)
comment(0xE2B4, "FV + RDA: one trailing byte still in FIFO", inline=True)
comment(0xE2B7, "Store the odd trailing byte", inline=True)
comment(0xE2BA, "Advance Y to count that final byte", inline=True)
comment(0xE2BB, "Unconditional: continue to dispatch", inline=True)

label(0xE2BD, "rx_frame_b_bail")
comment(0xE2BD, "Bail: restart from [`main_loop`](address:E051) (full ADLC re-init)", inline=True)

label(0xE2C0, "rx_b_not_for_us")
comment(0xE2C0, "A = &A2: RX on, IRQ enabled, TX in reset", inline=True)
comment(0xE2C2, "Re-arm ADLC B to listen for the next frame", inline=True)
comment(0xE2C5, "Skip [`main_loop`](address:E051) re-init; go straight back to polling", inline=True)

label(0xE2C8, "rx_b_to_forward")
comment(0xE2C8, "Out-of-range JMP to [`rx_b_forward`](address:E389) (JSR can't reach)", inline=True)

label(0xE2CB, "rx_frame_b_dispatch")
comment(0xE2CB, "Save final byte count (even if 0 bytes of payload)", inline=True)
comment(0xE2CE, "Compare to 6 – minimum valid scout header", inline=True)
comment(0xE2D0, "Shorter than header → bail", inline=True)
comment(0xE2D2, "Load src_net from the drained frame", inline=True)
comment(0xE2D5, "Non-zero → sender supplied src_net, keep it", inline=True)
comment(0xE2D7, "Sender left src_net = 0 ('my local net')", inline=True)
comment(0xE2DA, "…substitute our own B-side network number", inline=True)
label(0xE2DD, "rx_b_src_net_resolved")
comment(0xE2DD, "Load our A-side network number for comparison", inline=True)
comment(0xE2E0, "Compare against the incoming dst_net", inline=True)
comment(0xE2E3, "Not for side A → skip the local rewrite", inline=True)
comment(0xE2E5, "dst_net names our A-side network…", inline=True)
comment(0xE2E7, "…normalise dst_net to 0 (local on A)", inline=True)
label(0xE2EA, "rx_b_broadcast_check")
comment(0xE2EA, "Load dst_stn for the broadcast test", inline=True)
comment(0xE2ED, "AND with dst_net (both &FF only if full broadcast)", inline=True)
comment(0xE2F0, "Compare result to &FF", inline=True)
comment(0xE2F2, "Not a full broadcast → forward path", inline=True)
comment(0xE2F4, "Broadcast: re-arm B's listen mode for any follow-up", inline=True)
comment(0xE2F7, "A = &C2: reset TX, enable RX", inline=True)
comment(0xE2F9, "Commit CR1 while we process the bridge-protocol frame", inline=True)
comment(0xE2FC, "Load the port byte from the drained frame", inline=True)
comment(0xE2FF, "Compare with &9C (bridge-protocol port)", inline=True)
comment(0xE301, "Not our port → drop into forward path", inline=True)
comment(0xE303, "Load ctrl byte for the per-type dispatch", inline=True)
comment(0xE306, "Test &81 (BridgeReply: re-announcement)", inline=True)
comment(0xE308, "Match → [`rx_b_handle_81`](address:E36F)", inline=True)
comment(0xE30A, "Test &80 (BridgeReset: initial announcement)", inline=True)
comment(0xE30C, "Match → [`rx_b_handle_80`](address:E357)", inline=True)
comment(0xE30E, "Test &82 (WhatNet: general query)", inline=True)
comment(0xE310, "Match → [`rx_b_handle_82`](address:E31E)", inline=True)
comment(0xE312, "Test &83 (IsNet: targeted query)", inline=True)
comment(0xE314, "Unknown ctrl → forward path (fall through to [`rx_b_handle_83`](address:E316) on match)", inline=True)


label(0xE56E, "handshake_rx_a")
subroutine(0xE56E, "handshake_rx_a", hook=None,
    title="Receive a handshake frame on ADLC A and stage it for forward",
    description="""\
The receive half of four-way-handshake bridging for the A side.
Enables RX on ADLC A, drains an inbound frame byte-by-byte into the
outbound buffer starting at `tx_dst_stn` (`&045A`), then sets up
`tx_end_lo`/`tx_end_hi` so the next call to
[`transmit_frame_b`](address:E4C0) transmits the just-received
frame out of the other port verbatim.

The drain is capped at `top_ram_page` (set by the boot RAM test) so
very long frames fill available RAM and no further.

After the drain, does three pieces of address fix-up on the
now-staged frame:

- If `tx_src_net` (byte 3 of the frame) is zero, fill it with
  `net_num_a`. Many Econet senders leave `src_net` as zero to mean
  "my local network"; the Bridge makes that explicit before
  forwarding.
- Reject the frame if `tx_dst_net` is zero (no destination network
  declared) or if `reachable_via_b` has no entry for that network
  (we don't know a route).
- If `tx_dst_net` equals `net_num_b` (our own B-side network),
  normalise it to zero – from side B's perspective the frame is
  now "local".

On any of the "reject" paths above, and on any sub-step that fails
(no AP/RDA, no Frame Valid, no response at all), takes the standard
escape-to-main-loop exit: `PLA/PLA/JMP` [`main_loop`](address:E051).

On success, return to the caller with `mem_ptr` / `tx_end_lo` /
`tx_end_hi` ready for [`transmit_frame_b`](address:E4C0) (or
[`transmit_frame_a`](address:E517) in the reverse direction for
queries).

Mirror-image pair with [`handshake_rx_b`](address:E5FF?hex): the two
routines share identical structure with `adlc_a_*` / `adlc_b_*` and
`net_num_a` / `net_num_b` swapped, and are used in complementary
roles depending on which side the next handshake frame is expected
to arrive from.

Called from five sites:

| site                          | in                                    | role                                                    |
|-------------------------------|---------------------------------------|---------------------------------------------------------|
| [`&E1B5`](address:E1B5)       | [`rx_a_handle_82`](address:E19D)      | drain the querier's scout-ACK on A                      |
| [`&E1D0`](address:E1D0)       | [`rx_a_handle_82`](address:E19D)      | drain the querier's final data-ACK on A                 |
| [`&E254`](address:E254)       | [`rx_a_forward`](address:E208)        | Stage 3 DATA drain from A (originator's data, A &rarr; B) |
| [`&E3CF`](address:E3CF)       | [`rx_b_forward`](address:E389)        | Stage 2 ACK1 drain from A (destination's scout-ACK, B &rarr; A) |
| [`&E3DB`](address:E3DB)       | [`rx_b_forward`](address:E389)        | Stage 4 ACK2 drain from A (destination's final ACK, B &rarr; A) |""")

comment(0xE56E, "A = &82: TX in reset, RX IRQs enabled", inline=True)
comment(0xE570, "Re-arm ADLC A for the incoming handshake frame", inline=True)
comment(0xE573, "A = &01: SR2 mask for AP (Address Present)", inline=True)
comment(0xE575, "Block until ADLC A raises its first IRQ", inline=True)
comment(0xE578, "BIT SR2 – test AP bit against mask in A", inline=True)
comment(0xE57B, "No AP: nothing arrived, escape to main", inline=True)
comment(0xE57D, "Read byte 0 of the handshake frame (dst_stn)", inline=True)
comment(0xE580, "Stage into tx buffer for onward transmission", inline=True)
comment(0xE583, "Wait for the second RX IRQ (next byte ready)", inline=True)
comment(0xE586, "BIT SR2 – RDA (bit 7) still set?", inline=True)
comment(0xE589, "RDA cleared mid-frame: truncated, escape", inline=True)
comment(0xE58B, "Read byte 1: destination network", inline=True)
comment(0xE58E, "Stage dst_net into the forward buffer", inline=True)
comment(0xE591, "Y = 2: start draining pair-payload into (mem_ptr_lo),Y", inline=True)
label(0xE593, "handshake_rx_a_pair_loop")
comment(0xE593, "Wait for the next RX byte", inline=True)
comment(0xE596, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xE599, "End-of-frame detected mid-pair – jump to FV check", inline=True)
comment(0xE59B, "Read even-indexed payload byte", inline=True)
comment(0xE59E, "Store into (mem_ptr_lo)+Y in the staging buffer", inline=True)
comment(0xE5A0, "Advance Y to odd slot", inline=True)
comment(0xE5A1, "Read odd-indexed payload byte (no IRQ wait: paired)", inline=True)
comment(0xE5A4, "Store into (mem_ptr_lo)+Y", inline=True)
comment(0xE5A6, "Advance Y; wraps to 0 after 256 bytes", inline=True)
comment(0xE5A7, "Y didn't wrap – stay in this page", inline=True)
comment(0xE5A9, "Y wrapped: advance mem_ptr_hi to next page", inline=True)
comment(0xE5AB, "Reload new page number for bounds test", inline=True)
comment(0xE5AD, "Compare against top_ram_page (set by boot RAM test)", inline=True)
comment(0xE5AF, "Still room – keep draining into the next page", inline=True)
label(0xE5B1, "handshake_rx_a_escape")
comment(0xE5B1, "Drop caller's return address (lo)", inline=True)
comment(0xE5B2, "Drop caller's return address (hi)", inline=True)
comment(0xE5B3, "Abandon handshake and rejoin [`main_loop`](address:E051)", inline=True)

label(0xE5B6, "handshake_rx_a_drained")
comment(0xE5B6, "A = &00: halt ADLC A", inline=True)
comment(0xE5B8, "CR1 = 0: disable TX and RX IRQs", inline=True)
comment(0xE5BB, "A = &84: clear-RX-status + FV-clear bits", inline=True)
comment(0xE5BD, "Commit CR2: acknowledge the end-of-frame", inline=True)
comment(0xE5C0, "A = &02: mask SR2 bit 1 (Frame Valid)", inline=True)
comment(0xE5C2, "BIT SR2 – test FV and RDA bits together", inline=True)
comment(0xE5C5, "FV clear → frame was corrupt/short, escape", inline=True)
comment(0xE5C7, "FV set but no RDA → clean end, finalise length", inline=True)
comment(0xE5C9, "FV+RDA both set: one trailing byte still pending", inline=True)
comment(0xE5CC, "Store the odd trailing byte into the staging buffer", inline=True)
comment(0xE5CE, "Advance Y to cover that final byte", inline=True)
label(0xE5CF, "handshake_rx_a_finalise_len")
comment(0xE5CF, "A = Y (current byte offset in page)", inline=True)
comment(0xE5D0, "X = A: preserve raw length for odd-length callers", inline=True)
comment(0xE5D1, "Mask low bit: round length DOWN to even", inline=True)
comment(0xE5D3, "Store rounded tx_end_lo", inline=True)
comment(0xE5D6, "Load src_net from the just-drained frame", inline=True)
comment(0xE5D9, "Non-zero → sender supplied src_net, keep it", inline=True)
comment(0xE5DB, "Sender left src_net as 0 ('my local net')", inline=True)
comment(0xE5DE, "Substitute our own A-side network number", inline=True)
label(0xE5E1, "handshake_rx_a_route_check")
comment(0xE5E1, "Load dst_net into Y for routing lookup", inline=True)
comment(0xE5E4, "dst_net = 0 (unspecified) → reject, escape", inline=True)
comment(0xE5E6, "Probe reachable_via_b[dst_net]", inline=True)
comment(0xE5E9, "No route via side B → reject, escape", inline=True)
comment(0xE5EB, "Compare dst_net with our B-side net number", inline=True)
comment(0xE5EE, "Not us → leave dst_net as-is, skip the rewrite", inline=True)
comment(0xE5F0, "Frame is for the B-side's local network…", inline=True)
comment(0xE5F2, "…normalise dst_net to 0 for the outbound header", inline=True)
label(0xE5F5, "handshake_rx_a_end")
comment(0xE5F5, "Read final mem_ptr_hi (last page written)", inline=True)
comment(0xE5F7, "Record as tx_end_hi (multi-page frames need this)", inline=True)
comment(0xE5FA, "A = &04: reset mem_ptr_hi back to &045A page…", inline=True)
comment(0xE5FC, "…so the transmit path walks the buffer from byte 0", inline=True)
comment(0xE5FE, "Return: frame staged, transmitter can send it verbatim", inline=True)


label(0xE5FF, "handshake_rx_b")
subroutine(0xE5FF, "handshake_rx_b", hook=None,
    title="Receive a handshake frame on ADLC B and stage it for forward",
    description="""\
The receive half of four-way-handshake bridging for the B side.
Enables RX on ADLC B, drains an inbound frame byte-by-byte into the
outbound buffer starting at `tx_dst_stn` (`&045A`), then sets up
`tx_end_lo`/`tx_end_hi` so the next call to
[`transmit_frame_a`](address:E517) transmits the just-received
frame out of the other port verbatim.

The drain is capped at `top_ram_page` (set by the boot RAM test) so
very long frames fill available RAM and no further.

After the drain, does three pieces of address fix-up on the
now-staged frame:

- If `tx_src_net` (byte 3 of the frame) is zero, fill it with
  `net_num_b`. Many Econet senders leave `src_net` as zero to mean
  "my local network"; the Bridge makes that explicit before
  forwarding.
- Reject the frame if `tx_dst_net` is zero (no destination network
  declared) or if `reachable_via_a` has no entry for that network
  (no route).
- If `tx_dst_net` equals `net_num_a` (our own A-side network),
  normalise it to zero – from side A's perspective the frame is
  now "local".

On any of the "reject" paths above, and on any sub-step that fails
(no AP/RDA, no Frame Valid, no response at all), takes the standard
escape-to-main-loop exit: `PLA/PLA/JMP` [`main_loop`](address:E051).

On success, return to the caller with `mem_ptr` / `tx_end_lo` /
`tx_end_hi` ready for [`transmit_frame_a`](address:E517) (or
[`transmit_frame_b`](address:E4C0) in the reverse direction for
queries).

Mirror-image pair with [`handshake_rx_a`](address:E56E?hex): the
two routines share identical structure with `adlc_a_*` /
`adlc_b_*` and `net_num_a` / `net_num_b` swapped, and are used in
complementary roles depending on which side the next handshake
frame is expected to arrive from.

Called from five sites:

| site                          | in                                    | role                                                        |
|-------------------------------|---------------------------------------|-------------------------------------------------------------|
| [`&E336`](address:E336)       | [`rx_b_handle_82`](address:E31E)      | drain the querier's scout-ACK on B                          |
| [`&E351`](address:E351)       | [`rx_b_handle_82`](address:E31E)      | drain the querier's final data-ACK on B                     |
| [`&E3D5`](address:E3D5)       | [`rx_b_forward`](address:E389)        | Stage 3 DATA drain from B (originator's data, B &rarr; A)   |
| [`&E24E`](address:E24E)       | [`rx_a_forward`](address:E208)        | Stage 2 ACK1 drain from B (destination's scout-ACK, A &rarr; B) |
| [`&E25A`](address:E25A)       | [`rx_a_forward`](address:E208)        | Stage 4 ACK2 drain from B (destination's final ACK, A &rarr; B) |""")

comment(0xE5FF, "A = &82: TX in reset, RX IRQs enabled", inline=True)
comment(0xE601, "Re-arm ADLC B for the incoming handshake frame", inline=True)
comment(0xE604, "A = &01: SR2 mask for AP (Address Present)", inline=True)
comment(0xE606, "Block until ADLC B raises its first IRQ", inline=True)
comment(0xE609, "BIT SR2 – test AP bit against mask in A", inline=True)
comment(0xE60C, "No AP: nothing arrived, escape to main", inline=True)
comment(0xE60E, "Read byte 0 of the handshake frame (dst_stn)", inline=True)
comment(0xE611, "Stage into tx buffer for onward transmission", inline=True)
comment(0xE614, "Wait for the second RX IRQ (next byte ready)", inline=True)
comment(0xE617, "BIT SR2 – RDA (bit 7) still set?", inline=True)
comment(0xE61A, "RDA cleared mid-frame: truncated, escape", inline=True)
comment(0xE61C, "Read byte 1: destination network", inline=True)
comment(0xE61F, "Stage dst_net into the forward buffer", inline=True)
comment(0xE622, "Y = 2: start draining pair-payload into (mem_ptr_lo),Y", inline=True)
label(0xE624, "handshake_rx_b_pair_loop")
comment(0xE624, "Wait for the next RX byte", inline=True)
comment(0xE627, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xE62A, "End-of-frame detected mid-pair – jump to FV check", inline=True)
comment(0xE62C, "Read even-indexed payload byte", inline=True)
comment(0xE62F, "Store into (mem_ptr_lo)+Y in the staging buffer", inline=True)
comment(0xE631, "Advance Y to odd slot", inline=True)
comment(0xE632, "Read odd-indexed payload byte (no IRQ wait: paired)", inline=True)
comment(0xE635, "Store into (mem_ptr_lo)+Y", inline=True)
comment(0xE637, "Advance Y; wraps to 0 after 256 bytes", inline=True)
comment(0xE638, "Y didn't wrap – stay in this page", inline=True)
comment(0xE63A, "Y wrapped: advance mem_ptr_hi to next page", inline=True)
comment(0xE63C, "Reload new page number for bounds test", inline=True)
comment(0xE63E, "Compare against top_ram_page (set by boot RAM test)", inline=True)
comment(0xE640, "Still room – keep draining into the next page", inline=True)
label(0xE642, "handshake_rx_b_escape")
comment(0xE642, "Drop caller's return address (lo)", inline=True)
comment(0xE643, "Drop caller's return address (hi)", inline=True)
comment(0xE644, "Abandon handshake and rejoin [`main_loop`](address:E051)", inline=True)

label(0xE647, "handshake_rx_b_drained")
comment(0xE647, "A = &00: halt ADLC B", inline=True)
comment(0xE649, "CR1 = 0: disable TX and RX IRQs", inline=True)
comment(0xE64C, "A = &84: clear-RX-status + FV-clear bits", inline=True)
comment(0xE64E, "Commit CR2: acknowledge the end-of-frame", inline=True)
comment(0xE651, "A = &02: mask SR2 bit 1 (Frame Valid)", inline=True)
comment(0xE653, "BIT SR2 – test FV and RDA bits together", inline=True)
comment(0xE656, "FV clear → frame was corrupt/short, escape", inline=True)
comment(0xE658, "FV set but no RDA → clean end, finalise length", inline=True)
comment(0xE65A, "FV+RDA both set: one trailing byte still pending", inline=True)
comment(0xE65D, "Store the odd trailing byte into the staging buffer", inline=True)
comment(0xE65F, "Advance Y to cover that final byte", inline=True)
label(0xE660, "handshake_rx_b_finalise_len")
comment(0xE660, "A = Y (current byte offset in page)", inline=True)
comment(0xE661, "X = A: preserve raw length for odd-length callers", inline=True)
comment(0xE662, "Mask low bit: round length DOWN to even", inline=True)
comment(0xE664, "Store rounded tx_end_lo", inline=True)
comment(0xE667, "Load src_net from the just-drained frame", inline=True)
comment(0xE66A, "Non-zero → sender supplied src_net, keep it", inline=True)
comment(0xE66C, "Sender left src_net as 0 ('my local net')", inline=True)
comment(0xE66F, "Substitute our own B-side network number", inline=True)
label(0xE672, "handshake_rx_b_route_check")
comment(0xE672, "Load dst_net into Y for routing lookup", inline=True)
comment(0xE675, "dst_net = 0 (unspecified) → reject, escape", inline=True)
comment(0xE677, "Probe reachable_via_a[dst_net]", inline=True)
comment(0xE67A, "No route via side A → reject, escape", inline=True)
comment(0xE67C, "Compare dst_net with our A-side net number", inline=True)
comment(0xE67F, "Not us → leave dst_net as-is, skip the rewrite", inline=True)
comment(0xE681, "Frame is for the A-side's local network…", inline=True)
comment(0xE683, "…normalise dst_net to 0 for the outbound header", inline=True)
label(0xE686, "handshake_rx_b_end")
comment(0xE686, "Read final mem_ptr_hi (last page written)", inline=True)
comment(0xE688, "Record as tx_end_hi (multi-page frames need this)", inline=True)
comment(0xE68B, "A = &04: reset mem_ptr_hi back to &045A page…", inline=True)
comment(0xE68D, "…so the transmit path walks the buffer from byte 0", inline=True)
comment(0xE68F, "Return: frame staged, transmitter can send it verbatim", inline=True)


label(0xE448, "stagger_delay")
subroutine(0xE448, "stagger_delay", hook=None,
    title="Fixed prelude + per-count delay scaled by ctr24_lo",
    description="""\
A calibrated busy-wait used by the query-response paths to stagger
their transmissions. Called from
[`rx_a_handle_82`](address:E19D) (at [`&E1AC`](address:E1AC)) and
[`rx_b_handle_82`](address:E31E) (at [`&E32D`](address:E32D)), in
each case with `ctr24_lo` pre-loaded with the bridge's opposite-side
network number (`net_num_b` for A-side responses, `net_num_a` for
B-side responses).

Two phases:

1. **Prelude** (~`&40` &times; `DEY/BNE` cycles): a fixed settling
   delay, the same regardless of caller. Roughly `&40 * 5 = 320`
   cycles = ~160 us at 2 MHz.
2. **Per-count loop** (`ctr24_lo` iterations &times; (`&14` &times;
   `DEY/BNE` + `DEC/BNE`) cycles): roughly `ctr24_lo * 110` cycles.
   For a typical network number of ~24, that's ~2600 cycles =
   ~1.3 ms.

For the range of network numbers permitted (1-127), the total delay
runs from ~215 us to ~7 ms. This spread means multiple bridges on
the same segment responding to a broadcast query (`ctrl=&82`)
transmit their responses at measurably different times, reducing
the chance of collisions on the shared medium. Bridges with higher
network numbers back off longer – a cheap deterministic priority
scheme that requires no coordination.""")

comment(0xE448, "Y = &40: seed for the fixed-length settling delay", inline=True)
label(0xE44A, "stagger_delay_prelude")
comment(0xE44A, "Tight DEY/BNE loop – burns ~160 us regardless of caller", inline=True)
comment(0xE44B, "Spin until the prelude counter hits zero", inline=True)
label(0xE44D, "stagger_delay_outer")
comment(0xE44D, "Y = &14: seed for one inner-loop iteration", inline=True)
label(0xE44F, "stagger_delay_inner")
comment(0xE44F, "Tight DEY/BNE – ~50 us per outer iteration", inline=True)
comment(0xE450, "Spin until the inner counter hits zero", inline=True)
comment(0xE452, "One tick of the caller's network-number count", inline=True)
comment(0xE455, "Loop until ctr24_lo reaches zero (net_num_? ticks)", inline=True)
comment(0xE457, "Delay complete; return so caller can transmit", inline=True)


label(0xE48D, "build_query_response")
subroutine(0xE48D, "build_query_response", hook=None,
    title="Build a reply template for WhatNet/IsNet query responses",
    description="""\
A second frame-builder (sibling of [`build_announce_b`](address:E458))
used by the bridge-query response path. Called *twice* per response:
once to build the reply scout (`ctrl=&80` + `reply_port` as the port),
then after the querier's scout-ACK has been received, called again to
rebuild the buffer as a data frame – the caller then patches bytes 4
and 5 (labelled `tx_ctrl` and `tx_port` but genuinely payload in a
data frame) with the routing answer. Where `build_announce_b` writes
a broadcast-addressed template, this one builds a unicast reply:

| field        | value            | notes                                     |
|--------------|------------------|-------------------------------------------|
| `tx_dst_stn` | `rx_src_stn`     | station that sent the query               |
| `tx_dst_net` | `0`              | local network                             |
| `tx_src_stn` | `0`              | Bridge has no station                     |
| `tx_src_net` | `0`              | *(caller patches to `net_num_?`)*         |
| `tx_ctrl`    | `&80`            | scout control byte                        |
| `tx_port`    | `rx_query_port`  | response port from byte 12 of query       |
| X register   | `0`              | no trailing payload                       |

Also writes `tx_end_lo=&06` / `tx_end_hi=&04` and points `mem_ptr` at
`&045A` so a subsequent `transmit_frame_?` sends the 6-byte scout.

Called from the two query-response paths ([`&E1A0`](address:E1A0) and
[`&E1B8`](address:E1B8) on side A; [`&E321`](address:E321) and
[`&E339`](address:E339) on side B). Each caller then patches a subset
of the fields before calling `transmit_frame_?` – the idiomatic
second call in particular overwrites `tx_ctrl` and `tx_port` to
carry the bridge's routing answer.""")

comment(0xE48D, "Load querier's station from the received scout", inline=True)
comment(0xE490, "Target the reply back at them as dst_stn", inline=True)
comment(0xE493, "A = 0: local network marker", inline=True)
comment(0xE495, "dst_net = 0: answer on the querier's local net", inline=True)
comment(0xE498, "A = 0: Bridge has no station identity", inline=True)
comment(0xE49A, "src_stn = 0 in the reply (unused by Econet routing)", inline=True)
comment(0xE49D, "src_net = 0 for now (caller patches to net_num_?)", inline=True)
comment(0xE4A0, "ctrl = &80: this is a scout, not a data frame", inline=True)
comment(0xE4A2, "Write ctrl into the frame header", inline=True)
comment(0xE4A5, "Fetch the reply_port the querier asked for", inline=True)
comment(0xE4A8, "Write it as the outbound scout's port", inline=True)
comment(0xE4AB, "X = 0: transmit_frame_? should send 6 bytes exactly", inline=True)
comment(0xE4AD, "Low byte of tx_end: 6-byte frame", inline=True)
comment(0xE4AF, "Store tx_end_lo", inline=True)
comment(0xE4B2, "High byte of tx_end: page &04", inline=True)
comment(0xE4B4, "Store tx_end_hi (end pair = &0406)", inline=True)
comment(0xE4B7, "Low byte of mem_ptr: &045A", inline=True)
comment(0xE4B9, "Store mem_ptr_lo", inline=True)
comment(0xE4BB, "High byte of mem_ptr: page &04", inline=True)
comment(0xE4BD, "Store mem_ptr_hi; pointer = &045A", inline=True)
comment(0xE4BF, "Return; caller patches src_net and ctrl/port as needed", inline=True)


label(0xE195, "rx_a_handle_83")
subroutine(0xE195, "rx_a_handle_83", hook=None, is_entry_point=False,
    title="Side-A IsNet query (ctrl=&83): targeted network lookup",
    description="""\
Called when a received frame on side A is broadcast + `port=&9C` +
`ctrl=&83` – the querier is asking "can you reach network X?",
where X is the byte at offset 13 of the payload (`rx_query_net`).

Consults `reachable_via_b[rx_query_net]`. If the entry is zero,
there is no route to that network so the query is silently dropped
(`JMP` [`main_loop`](address:E051) via
[`rx_a_query_done`](address:E1D3)). If non-zero, falls through to
the shared response body at [`rx_a_handle_82`](address:E19D) to
transmit the reply – so the targeted query is effectively the
general query with an up-front routing filter.""")

comment(0xE195, "Y = the queried network number", inline=True)
comment(0xE198, "Check if we have a route via the other side", inline=True)
comment(0xE19B, "Unknown → silently drop this IsNet query", inline=True)


label(0xE19D, "rx_a_handle_82")
subroutine(0xE19D, "rx_a_handle_82", hook=None, is_entry_point=False,
    title="Side-A WhatNet query (ctrl=&82); also the IsNet response path",
    description="""\
Called when a received frame on side A is broadcast + `port=&9C` +
`ctrl=&82` – a general bridge query asking "which networks do you
reach?" – or when [`rx_a_handle_83`](address:E195) has verified
that a specific IsNet queried network is in fact reachable via
side B and is re-using this response path.

The response is a complete four-way handshake transaction, which
the Bridge drives from the responder side as two transmissions
(scout, then data) with an inbound ACK after each:

1. Build a reply-scout template via
   [`build_query_response`](address:E48D), addressed back to the
   querier on its local network with `tx_src_net` patched to our
   `net_num_b`.
2. **Stagger** the scout transmission via
   [`stagger_delay`](address:E448), seeded from `net_num_b`.
   Multiple bridges on the same segment will all react to a
   broadcast query, and without the stagger their responses would
   overlap on the wire; seeding from the network number gives each
   bridge a deterministic but distinct delay.
3. CSMA, transmit the scout, then
   [`handshake_rx_a`](address:E56E) to receive the scout-ACK.
4. Rebuild the frame via [`build_query_response`](address:E48D)
   again – this time to be a *data* frame following the scout we
   just exchanged, not a new scout. The patches that follow
   populate the first two payload bytes of that data frame (at
   the byte positions labelled `tx_ctrl` and `tx_port`, but those
   names refer to scout semantics; in a data frame those slots
   are payload, not header):

   | slot          | value              | meaning                         |
   |---------------|--------------------|---------------------------------|
   | data byte 0   | `net_num_a`        | the Bridge's side-A network     |
   | data byte 1   | `rx_query_net`     | echo of the queried network     |

   The answer thus consists of the dst/src quad plus two payload
   bytes, packed into the smallest Econet frame that can carry it.
5. Transmit the data frame, then
   [`handshake_rx_a`](address:E56E) for the final data-ACK. `JMP`
   [`main_loop`](address:E051) on completion.

Either [`handshake_rx_a`](address:E56E) call can escape to
[`main_loop`](address:E051) if the querier doesn't keep up the
handshake, aborting the conversation cleanly.""")

comment(0xE19D, "Re-arm A for listen after the received query")
comment(0xE19D, "Re-arm ADLC A into listen mode before replying", inline=True)
comment(0xE1A0, "Build reply-scout template addressed at the querier", inline=True)
comment(0xE1A3, "Fetch our side-B network number", inline=True)
comment(0xE1A6, "Patch src_net so the scout names us by net_num_b", inline=True)
comment(0xE1A9, "Copy it into the stagger-delay counter too", inline=True)
comment(0xE1AC, "Busy-wait for (net_num_b * ~50us) + 160us", inline=True)
comment(0xE1AF, "CSMA wait on A so we don't collide with live traffic", inline=True)
comment(0xE1B2, "Transmit the reply scout", inline=True)
comment(0xE1B5, "Wait for the querier's scout-ACK on A", inline=True)
comment(0xE1B8, "Rebuild template – next frame is the data response", inline=True)
comment(0xE1BB, "Fetch net_num_b", inline=True)
comment(0xE1BE, "Re-patch src_net (rebuilt block needs it again)", inline=True)
comment(0xE1C1, "Fetch net_num_a", inline=True)
comment(0xE1C4, "Write it as data-frame payload byte 0 (tx_ctrl slot)", inline=True)
comment(0xE1C7, "Fetch the network the querier asked about", inline=True)
comment(0xE1CA, "Write it as data-frame payload byte 1 (tx_port slot)", inline=True)
comment(0xE1CD, "Transmit the data frame", inline=True)
comment(0xE1D0, "Wait for the querier's final data-ACK", inline=True)
label(0xE1D3, "rx_a_query_done")
comment(0xE1D3, "Transaction complete → back to [`main_loop`](address:E051)", inline=True)


label(0xE208, "rx_a_forward")
subroutine(0xE208, "rx_a_forward", hook=None, is_entry_point=False,
    title="Forward an A-side frame to B, completing the 4-way handshake",
    description="""\
Entry point for cross-network forwarding of frames received on side A.
Reached from three places:

- [`rx_a_to_forward`](address:E147?hex): the A-side frame is addressed
  to a remote station (not a full broadcast), and we have accepted it
  via the routing filter.
- [`rx_frame_a`](address:E0E2) ctrl dispatch fall-through (at
  [`&E193`](address:E193)): the frame is broadcast + port `&9C` but
  has a control byte outside the recognised bridge-protocol set
  (`&80`-`&83`).
- Fall-through from [`rx_a_handle_81`](address:E1EE) (at
  [`&E207`](address:E207)): we've learned from the announcement and
  appended `net_num_a` to the payload; now propagate it onward.

The routine bridges the complete Econet four-way handshake by
alternating direct-forward, receive-on-one-side, and re-transmit:

| stage | direction  | drain                                                 | retransmit                                       |
|-------|------------|-------------------------------------------------------|--------------------------------------------------|
| SCOUT | A &rarr; B | already in `rx_*` (done by [`rx_frame_a`](address:E0E2)) | push `rx_*` into `adlc_b_tx`, pair-at-a-time     |
| ACK1  | B &rarr; A | [`handshake_rx_b`](address:E5FF) into `&045A`         | [`transmit_frame_a`](address:E517)               |
| DATA  | A &rarr; B | [`handshake_rx_a`](address:E56E) into `&045A`         | [`transmit_frame_b`](address:E4C0)               |
| ACK2  | B &rarr; A | [`handshake_rx_b`](address:E5FF) into `&045A`         | [`transmit_frame_a`](address:E517)               |

Each `handshake_rx_?` call can escape to [`main_loop`](address:E051)
(PLA/PLA/JMP) if the expected frame doesn't arrive, cleanly aborting
the bridged conversation without further work on either side.

The A-B-A transmit pattern at the routine's tail is therefore the
natural shape of a bridged four-way handshake when the initial scout
came from side A: two frames travel A &rarr; B (scout and data) and
two travel B &rarr; A (two ACKs).""")

comment(0xE208, "Read rx_len into A", inline=True)
comment(0xE20B, "Preserve original length in X for odd-parity check", inline=True)
comment(0xE20C, "Mask low bit to round DOWN to even byte count", inline=True)
comment(0xE20E, "Store the rounded count for the pair loop", inline=True)
comment(0xE211, "CSMA wait on B before transmitting the forwarded scout", inline=True)
comment(0xE214, "Y = 0: start at byte 0 of the rx_* buffer", inline=True)
label(0xE216, "rx_a_forward_pair_loop")
comment(0xE216, "Wait for ADLC B's TDRA", inline=True)
comment(0xE219, "BIT SR1 – V ← bit 6 (TDRA)", inline=True)
comment(0xE21C, "TDRA clear → chip lost sync, escape to [`main_loop`](address:E051)", inline=True)
comment(0xE21E, "Load byte Y of the received scout", inline=True)
comment(0xE221, "Push it to ADLC B's TX FIFO", inline=True)
comment(0xE224, "Advance Y", inline=True)
comment(0xE225, "Load byte Y+1", inline=True)
comment(0xE228, "Push the second byte of the pair", inline=True)
comment(0xE22B, "Advance Y again", inline=True)
comment(0xE22C, "Have we reached the even-rounded length yet?", inline=True)
comment(0xE22F, "No → keep looping", inline=True)
comment(0xE231, "Recover original length from X for parity check", inline=True)
comment(0xE232, "ROR: carry ← bit 0 (= original length was odd?)", inline=True)
comment(0xE233, "Even → skip the trailing-byte path", inline=True)
comment(0xE235, "Odd: wait for TDRA once more for the last byte", inline=True)
comment(0xE238, "Load the trailing byte", inline=True)
comment(0xE23B, "Push it to the TX FIFO", inline=True)
label(0xE23E, "rx_a_forward_ack_round")
comment(0xE23E, "A = &3F: end-of-burst CR2 value", inline=True)
comment(0xE240, "Commit CR2 – ADLC B flushes the scout", inline=True)
comment(0xE243, "Wait for the frame-complete IRQ", inline=True)
comment(0xE246, "A = &5A: reset mem_ptr_lo for the handshake stages below", inline=True)
comment(0xE248, "Store mem_ptr_lo", inline=True)
comment(0xE24A, "A = 4: reset mem_ptr_hi", inline=True)
comment(0xE24C, "Store mem_ptr_hi – handshake_rx_? will write here", inline=True)
comment(0xE24E, "Stage 2: drain ACK1 from B into &045A…", inline=True)
comment(0xE251, "…and retransmit it on A so the originator hears its ACK", inline=True)
comment(0xE254, "Stage 3: drain DATA from A into &045A…", inline=True)
comment(0xE257, "…and retransmit it on B to the destination", inline=True)
comment(0xE25A, "Stage 4: drain ACK2 from B into &045A…", inline=True)
comment(0xE25D, "…and retransmit it on A as the final ACK", inline=True)
label(0xE260, "rx_a_forward_done")
comment(0xE260, "4-way handshake bridged; back to [`main_loop`](address:E051)", inline=True)


label(0xE389, "rx_b_forward")
subroutine(0xE389, "rx_b_forward", hook=None, is_entry_point=False,
    title="Forward a B-side frame to A, completing the 4-way handshake",
    description="""\
Byte-for-byte mirror of [`rx_a_forward`](address:E208?hex) with A
and B swapped throughout: the inbound scout is pushed via
`adlc_a_tx`, and the B-A-B tail bridges the four-way handshake the
other direction.

Reached from three places:

- [`rx_b_to_forward`](address:E2C8?hex): the B-side frame is
  addressed to a remote station (not a full broadcast), and we
  have accepted it via the routing filter.
- [`rx_frame_b`](address:E263) ctrl dispatch fall-through (at
  [`&E314`](address:E314)): the frame is broadcast + port `&9C`
  but has a control byte outside the recognised bridge-protocol
  set (`&80`-`&83`).
- Fall-through from [`rx_b_handle_81`](address:E36F) (at
  [`&E387`](address:E387)): we've learned from the announcement
  and appended `net_num_b` to the payload; now propagate it onward.

| stage | direction  | drain                                                 | retransmit                                       |
|-------|------------|-------------------------------------------------------|--------------------------------------------------|
| SCOUT | B &rarr; A | already in `rx_*` (done by [`rx_frame_b`](address:E263)) | push `rx_*` into `adlc_a_tx`, pair-at-a-time     |
| ACK1  | A &rarr; B | [`handshake_rx_a`](address:E56E) into `&045A`         | [`transmit_frame_b`](address:E4C0)               |
| DATA  | B &rarr; A | [`handshake_rx_b`](address:E5FF) into `&045A`         | [`transmit_frame_a`](address:E517)               |
| ACK2  | A &rarr; B | [`handshake_rx_a`](address:E56E) into `&045A`         | [`transmit_frame_b`](address:E4C0)               |

See [`rx_a_forward`](address:E208) for the full per-stage
explanation.""")

comment(0xE389, "Read rx_len into A", inline=True)
comment(0xE38C, "Preserve original length in X for odd-parity check", inline=True)
comment(0xE38D, "Mask low bit to round DOWN to even byte count", inline=True)
comment(0xE38F, "Store the rounded count for the pair loop", inline=True)
comment(0xE392, "CSMA wait on A before transmitting the forwarded scout", inline=True)
comment(0xE395, "Y = 0: start at byte 0 of the rx_* buffer", inline=True)
label(0xE397, "rx_b_forward_pair_loop")
comment(0xE397, "Wait for ADLC A's TDRA", inline=True)
comment(0xE39A, "BIT SR1 – V ← bit 6 (TDRA)", inline=True)
comment(0xE39D, "TDRA clear → chip lost sync, escape to [`main_loop`](address:E051)", inline=True)
comment(0xE39F, "Load byte Y of the received scout", inline=True)
comment(0xE3A2, "Push it to ADLC A's TX FIFO", inline=True)
comment(0xE3A5, "Advance Y", inline=True)
comment(0xE3A6, "Load byte Y+1", inline=True)
comment(0xE3A9, "Push the second byte of the pair", inline=True)
comment(0xE3AC, "Advance Y again", inline=True)
comment(0xE3AD, "Have we reached the even-rounded length yet?", inline=True)
comment(0xE3B0, "No → keep looping", inline=True)
comment(0xE3B2, "Recover original length from X for parity check", inline=True)
comment(0xE3B3, "ROR: carry ← bit 0 (= original length was odd?)", inline=True)
comment(0xE3B4, "Even → skip the trailing-byte path", inline=True)
comment(0xE3B6, "Odd: wait for TDRA once more for the last byte", inline=True)
comment(0xE3B9, "Load the trailing byte", inline=True)
comment(0xE3BC, "Push it to the TX FIFO", inline=True)
label(0xE3BF, "rx_b_forward_ack_round")
comment(0xE3BF, "A = &3F: end-of-burst CR2 value", inline=True)
comment(0xE3C1, "Commit CR2 – ADLC A flushes the scout", inline=True)
comment(0xE3C4, "Wait for the frame-complete IRQ", inline=True)
comment(0xE3C7, "A = &5A: reset mem_ptr_lo for the handshake stages below", inline=True)
comment(0xE3C9, "Store mem_ptr_lo", inline=True)
comment(0xE3CB, "A = 4: reset mem_ptr_hi", inline=True)
comment(0xE3CD, "Store mem_ptr_hi – handshake_rx_? will write here", inline=True)
comment(0xE3CF, "Stage 2: drain ACK1 from A into &045A…", inline=True)
comment(0xE3D2, "…and retransmit it on B so the originator hears its ACK", inline=True)
comment(0xE3D5, "Stage 3: drain DATA from B into &045A…", inline=True)
comment(0xE3D8, "…and retransmit it on A to the destination", inline=True)
comment(0xE3DB, "Stage 4: drain ACK2 from A into &045A…", inline=True)
comment(0xE3DE, "…and retransmit it on B as the final ACK", inline=True)
label(0xE3E1, "rx_b_forward_done")
comment(0xE3E1, "4-way handshake bridged; back to [`main_loop`](address:E051)", inline=True)


label(0xE1D6, "rx_a_handle_80")
subroutine(0xE1D6, "rx_a_handle_80", hook=None, is_entry_point=False,
    title="Side-A BridgeReset (ctrl=&80): learn topology from scratch",
    description="""\
Called when a received frame on side A is broadcast + `port=&9C` +
`ctrl=&80` – a bridge on the far side is advertising a fresh
topology, likely because it has itself just come up. The handler:

1. **Wipe** all learned routing state via
   [`init_reachable_nets`](address:E424). The topology may have
   changed non-monotonically, so accumulated `reachable_via_?`
   entries are suspect and the safe move is to discard them and
   relearn.
2. **Schedule** a burst of our own re-announcements: ten cycles
   with a staggered initial timer value seeded from `net_num_b`.
   Using the local network number as the timer's phase means
   bridges on different segments aren't all re-announcing at the
   same millisecond. `announce_flag` is set to `&40` (enable,
   bit 7 clear = next outbound on side A).
3. **Fall through** to [`rx_a_handle_81`](address:E1EE) (the same
   payload-processing loop runs for both BridgeReset and
   BridgeReply) to mark the sender's known networks as
   reachable-via-A.

This is one of only two places in the ROM that sets
`announce_flag` non-zero (the other is the mirror
[`rx_b_handle_80`](address:E357)). Receiving a BridgeReply
(`ctrl=&81`) does not trigger the burst; only receiving a
BridgeReset does. A solo bridge therefore stays silent after its
boot-time BridgeReset pair, because nothing comes back to trigger
a response. See `docs/analysis/event-driven-reannouncement.md`.""")

comment(0xE1D6, "Wipe all learned routing state (topology reset)", inline=True)
comment(0xE1D9, "Fetch our side-B network number", inline=True)
comment(0xE1DC, "Use it as the re-announce timer's high byte (stagger)", inline=True)
comment(0xE1DF, "A = 0: timer low byte", inline=True)
comment(0xE1E1, "Store timer_lo; first fire in (net_num_b * 256) idle ticks", inline=True)
comment(0xE1E4, "A = 10: number of BridgeReplies to emit", inline=True)
comment(0xE1E6, "Store the burst count", inline=True)
comment(0xE1E9, "A = &40: enable re-announce, bit 7 clear = send via A", inline=True)
comment(0xE1EB, "Set announce_flag; main loop will now schedule the burst", inline=True)

label(0xE1EE, "rx_a_handle_81")
subroutine(0xE1EE, "rx_a_handle_81", hook=None, is_entry_point=False,
    title="Side-A BridgeReply (ctrl=&81): learn and re-broadcast",
    description="""\
Reached either directly as the `ctrl=&81` handler (the
re-announcement that follows a BridgeReset) or via fall-through
from [`rx_a_handle_80`](address:E1D6) (which additionally wipes
routing state before the learn loop).

Processes the announcement payload: each byte from offset 6 up to
`rx_len` is a network number that the announcer says it can reach.
Since the announcer is on side A, those networks are reachable via
side A from here too – mark each in `reachable_via_a`.

After the learn loop, append our own `net_num_a` to the payload and
bump `rx_len`. Falling through to [`rx_a_forward`](address:E208)
re-broadcasts the augmented frame out of ADLC B, so any bridges
beyond us on that side hear about the announced networks plus us
as one further hop along the route. This is classic
distance-vector flooding.""")

comment(0xE1EE, "Y = 6: skip past the 6-byte scout header", inline=True)
label(0xE1F0, "rx_a_learn_loop")
comment(0xE1F0, "Fetch next announced network number from payload", inline=True)
comment(0xE1F3, "X = the network to record", inline=True)
comment(0xE1F4, "A = &FF: 'route known' marker", inline=True)
comment(0xE1F6, "Remember that network X is reachable via side A", inline=True)
comment(0xE1F9, "Advance to next payload byte", inline=True)
comment(0xE1FA, "Have we reached the end of the payload?", inline=True)
comment(0xE1FD, "No – keep learning", inline=True)
comment(0xE1FF, "Load our own side-A network number", inline=True)
comment(0xE202, "Append it to the payload for the onward broadcast", inline=True)
comment(0xE205, "Payload grew by one byte; record the new length", inline=True)


label(0xE079, "main_loop_poll")
comment(0xE079, "BIT ADLC B's SR1 – N ← bit 7 (IRQ summary)", inline=True)
comment(0xE07C, "B quiet → check A", inline=True)
comment(0xE07E, "B has an event → dispatch to [`rx_frame_b`](address:E263)", inline=True)
label(0xE081, "main_loop_poll_a")
comment(0xE081, "BIT ADLC A's SR1 – N ← bit 7 (IRQ summary)", inline=True)
comment(0xE084, "A quiet → nothing to do; maybe re-announce", inline=True)
comment(0xE086, "A has an event → dispatch to [`rx_frame_a`](address:E0E2)", inline=True)

label(0xE089, "main_loop_idle")
comment(0xE089, "Read announce_flag – is a re-announce burst pending?", inline=True)
comment(0xE08C, "No burst in progress → straight back to polling", inline=True)
comment(0xE08E, "Tick the 16-bit re-announce countdown, low byte", inline=True)
comment(0xE091, "Low byte didn't wrap → keep polling", inline=True)
comment(0xE093, "Low byte wrapped → tick the high byte too", inline=True)
comment(0xE096, "Timer hasn't expired yet → keep polling", inline=True)

label(0xE098, "re_announce")
subroutine(0xE098, "re_announce", hook=None, is_entry_point=False,
    title="Emit one BridgeReply in an in-progress response burst",
    description="""\
Reached from [`main_loop_idle`](address:E089) once the 16-bit
`announce_tmr` has ticked down to zero *and* `announce_flag` is
non-zero. Both conditions are only met after
[`rx_a_handle_80`](address:E1D6) or
[`rx_b_handle_80`](address:E357) has set the flag in response to a
BridgeReset received from another bridge. This routine is the
per-tick action of that response burst – it is *not* a
self-scheduled periodic announcement.

Rebuilds the outbound template via
[`build_announce_b`](address:E458) and patches `tx_ctrl` from `&80`
(the BridgeReset value the builder writes) to `&81` (BridgeReply),
distinguishing the follow-up announcements from the initial one
that triggered the burst.

Which side to transmit on is selected by `announce_flag` bit 7:

| `announce_flag` bit 7 | side    | notes                                                                                       |
|-----------------------|---------|---------------------------------------------------------------------------------------------|
| clear (`1..&7F`)      | ADLC A  | transmit directly                                                                           |
| set (`&80..&FF`)      | ADLC B  | patch `tx_data0` with `net_num_a` first, mirroring the reset-time dual-broadcast            |

Each invocation decrements `announce_count`. When it hits zero,
`announce_flag` is cleared ([`re_announce_done`](address:E0C2));
the burst is complete and the idle path goes quiet until another
BridgeReset arrives. Otherwise the timer is re-armed to `&8000`
and control returns to [`main_loop`](address:E051)
([`re_announce_rearm`](address:E0B5)).

Before transmitting on one side, the routine resets the *other*
ADLC's TX path (`CR1 = &C2`) to prevent the opposite side from
inadvertently transmitting a colliding frame while we're busy.""")

comment(0xE098, "Rebuild the frame template from scratch (ctrl=&80 default)", inline=True)
comment(0xE09B, "A = &81: the BridgeReply control byte", inline=True)
comment(0xE09D, "Patch tx_ctrl to &81 – this announcement is a reply", inline=True)
comment(0xE0A0, "Test announce_flag bit 7 via BIT", inline=True)
comment(0xE0A3, "Bit 7 set → send via ADLC B ([`re_announce_side_b`](address:E0CA))", inline=True)
comment(0xE0A5, "Side-A path: silence B's TX first", inline=True)
comment(0xE0A7, "Reset ADLC B's TX to avoid a cross-side collision", inline=True)
comment(0xE0AA, "CSMA wait on A before transmitting", inline=True)
comment(0xE0AD, "Send the BridgeReply on ADLC A", inline=True)
comment(0xE0B0, "Decrement burst-remaining count", inline=True)
comment(0xE0B3, "Count hit zero → clear announce_flag", inline=True)

label(0xE0B5, "re_announce_rearm")
comment(0xE0B5, "A = &80: reseed timer high byte", inline=True)
comment(0xE0B7, "Store new timer_hi", inline=True)
comment(0xE0BA, "A = 0: timer low byte", inline=True)
comment(0xE0BC, "Store timer_lo; next firing in ~&8000 idle iterations", inline=True)
comment(0xE0BF, "Continue the main loop", inline=True)

label(0xE0C2, "re_announce_done")
comment(0xE0C2, "A = 0: 'burst complete' marker", inline=True)
comment(0xE0C4, "Clear announce_flag; re-announce stops until next BridgeReset", inline=True)
comment(0xE0C7, "Continue the main loop", inline=True)

label(0xE0CA, "re_announce_side_b")
comment(0xE0CA, "Fetch our side-A network number", inline=True)
comment(0xE0CD, "Patch tx_data0: this frame announces net_num_a to side B", inline=True)
comment(0xE0D0, "Mask: reset TX, RX going", inline=True)
comment(0xE0D2, "Silence ADLC A's TX to avoid collision while we send on B", inline=True)
comment(0xE0D5, "CSMA wait on B", inline=True)
comment(0xE0D8, "Send the BridgeReply on ADLC B", inline=True)
comment(0xE0DB, "Decrement burst-remaining count", inline=True)
comment(0xE0DE, "Count hit zero → clear announce_flag", inline=True)
comment(0xE0E0, "Not exhausted → re-arm timer and continue (ALWAYS branch)", inline=True)


# =====================================================================
# Transmit a frame via ADLC A
# =====================================================================

label(0xE517, "transmit_frame_a")
subroutine(0xE517, "transmit_frame_a", hook=None,
    title="Send the frame at mem_ptr out through ADLC A's TX FIFO",
    description="""\
Sends the frame starting at `mem_ptr` (`&80`/`&81` – normally
pointing at the outbound control block `&045A`) through ADLC A's
TX FIFO. Termination is controlled by the 16-bit pointer
`tx_end_lo`/`tx_end_hi` (`&0200`/`&0201`): the loop sends byte pairs
until `mem_ptr + Y` reaches or passes `(tx_end_hi:tx_end_lo)`. X is
a flag – non-zero means send one extra trailing byte after the
terminator (used by builders that append a payload like
[`build_announce_b`](address:E458)'s `net_num_b` at `&0460`).

**On entry:**

| register / byte       | role                                                   |
|-----------------------|--------------------------------------------------------|
| `mem_ptr_lo/hi`       | start address of frame                                 |
| `tx_end_lo/hi`        | end address (exclusive pair)                           |
| X                     | `0` = no trailing byte, `1` = send one trailing byte   |
| *(ADLC A)*            | must already be primed by a frame builder              |

**On exit (normal RTS):**

- `mem_ptr_lo/hi` reset to `&045A`, ready for the next builder.
- ADLC A's TX FIFO flushed, `CR2 = &3F`.

**Abnormal exit**: if any of the three
[`wait_adlc_a_irq`](address:E3E4) polls returns with SR1's V-bit
clear instead of set (meaning the ADLC didn't reach the expected
TDRA state), the routine drops the caller's return address from
the stack and `JMP`'s into [`main_loop`](address:E051) – the same
escape-to-main pattern used by
[`wait_adlc_a_idle`](address:E6DC).

Called from seven sites: reset ([`&E03E`](address:E03E)),
[`&E0AD`](address:E0AD), [`&E1B2`](address:E1B2),
[`&E1CD`](address:E1CD), [`&E251`](address:E251),
[`&E25D`](address:E25D), [`&E3D8`](address:E3D8).""")

comment(0xE517, "A = &E7: prime CR2 for TX (FC_TDRA, 2/1-byte, PSE)", inline=True)
comment(0xE519, "Commit CR2 on ADLC A", inline=True)
comment(0xE51C, "A = &44: arm CR1 for TX (TX on, RX off for now)", inline=True)
comment(0xE51E, "Commit CR1 on ADLC A", inline=True)
comment(0xE521, "Y = 0: byte offset into the frame buffer", inline=True)
label(0xE523, "transmit_frame_a_pair_loop")
comment(0xE523, "Wait for ADLC A IRQ (TDRA = FIFO ready for bytes)", inline=True)
comment(0xE526, "BIT SR1 – V flag ← bit 6 (TDRA)", inline=True)
comment(0xE529, "TDRA set → FIFO has room, send the next pair", inline=True)
label(0xE52B, "transmit_frame_a_escape")
comment(0xE52B, "TDRA clear → ADLC state bad; drop return address…", inline=True)
comment(0xE52C, "…(second PLA completes the drop)", inline=True)
comment(0xE52D, "…and escape to [`main_loop`](address:E051)", inline=True)
label(0xE530, "transmit_frame_a_send_pair")
comment(0xE530, "Load frame byte at (mem_ptr),Y", inline=True)
comment(0xE532, "Push to ADLC A's TX FIFO", inline=True)
comment(0xE535, "Advance Y within page", inline=True)
comment(0xE536, "Load the next frame byte", inline=True)
comment(0xE538, "Push the second byte of the pair", inline=True)
comment(0xE53B, "Advance Y again", inline=True)
comment(0xE53C, "Non-zero Y → stay on current page", inline=True)
comment(0xE53E, "Y wrapped to zero → bump mem_ptr to next page", inline=True)
label(0xE540, "transmit_frame_a_end_check")
comment(0xE540, "Compare Y with tx_end_lo", inline=True)
comment(0xE543, "Still short of end-of-frame low byte → more to send", inline=True)
comment(0xE545, "Load current mem_ptr_hi", inline=True)
comment(0xE547, "Compare with tx_end_hi", inline=True)
comment(0xE54A, "Still on a lower page than the end → more to send", inline=True)
comment(0xE54C, "Recover X (trailing-byte flag) from before the loop", inline=True)
comment(0xE54D, "Rotate bit 0 into carry", inline=True)
comment(0xE54E, "X was even → no trailing byte, skip ahead", inline=True)
comment(0xE550, "X was odd → wait for TDRA once more", inline=True)
comment(0xE553, "BIT SR1 to test TDRA again", inline=True)
comment(0xE556, "TDRA clear → escape (mirror of [`&E52B`](address:E52B))", inline=True)
comment(0xE558, "Load the extra trailing byte (tx_data0 in announce frames)", inline=True)
comment(0xE55A, "Push trailing byte to TX FIFO", inline=True)
label(0xE55D, "transmit_frame_a_finish")
comment(0xE55D, "A = &3F: signal end-of-burst via CR2", inline=True)
comment(0xE55F, "Commit CR2 – ADLC flushes and flags frame-complete", inline=True)
comment(0xE562, "Wait for the frame-complete IRQ", inline=True)
comment(0xE565, "A = &5A: reset mem_ptr_lo to &045A base", inline=True)
comment(0xE567, "Store mem_ptr_lo", inline=True)
comment(0xE569, "A = 4: reset mem_ptr_hi to page &04", inline=True)
comment(0xE56B, "Store mem_ptr_hi – pointer ready for next builder", inline=True)
comment(0xE56D, "Return; the frame has left ADLC A", inline=True)


# =====================================================================
# Transmit a frame via ADLC B (mirror of transmit_frame_a)
# =====================================================================

label(0xE4C0, "transmit_frame_b")
subroutine(0xE4C0, "transmit_frame_b", hook=None,
    title="Send the frame at mem_ptr out through ADLC B's TX FIFO",
    description="""\
Byte-for-byte mirror of [`transmit_frame_a`](address:E517?hex) with
`adlc_a_*` replaced by `adlc_b_*`. Everything there applies here --
same entry conditions, same end-pointer semantics
(`tx_end_lo/hi`), same `X=0/1` trailing-byte flag, same
escape-to-main-loop on unexpected SR1 state, same normal exit that
resets `mem_ptr` to `&045A`.

Called from seven sites: reset ([`&E04E`](address:E04E)),
[`&E0D8`](address:E0D8), [`&E257`](address:E257),
[`&E333`](address:E333), [`&E34E`](address:E34E),
[`&E3D2`](address:E3D2), [`&E3DE`](address:E3DE).""")

comment(0xE4C0, "A = &E7: prime CR2 for TX (FC_TDRA, 2/1-byte, PSE)", inline=True)
comment(0xE4C2, "Commit CR2 on ADLC B", inline=True)
comment(0xE4C5, "A = &44: arm CR1 for TX (TX on, RX off for now)", inline=True)
comment(0xE4C7, "Commit CR1 on ADLC B", inline=True)
comment(0xE4CA, "Y = 0: byte offset into the frame buffer", inline=True)
label(0xE4CC, "transmit_frame_b_pair_loop")
comment(0xE4CC, "Wait for ADLC B IRQ (TDRA = FIFO ready for bytes)", inline=True)
comment(0xE4CF, "BIT SR1 – V flag ← bit 6 (TDRA)", inline=True)
comment(0xE4D2, "TDRA set → FIFO has room, send the next pair", inline=True)
label(0xE4D4, "transmit_frame_b_escape")
comment(0xE4D4, "TDRA clear → ADLC state bad; drop return address…", inline=True)
comment(0xE4D5, "…(second PLA completes the drop)", inline=True)
comment(0xE4D6, "…and escape to [`main_loop`](address:E051)", inline=True)
label(0xE4D9, "transmit_frame_b_send_pair")
comment(0xE4D9, "Load frame byte at (mem_ptr),Y", inline=True)
comment(0xE4DB, "Push to ADLC B's TX FIFO", inline=True)
comment(0xE4DE, "Advance Y within page", inline=True)
comment(0xE4DF, "Load the next frame byte", inline=True)
comment(0xE4E1, "Push the second byte of the pair", inline=True)
comment(0xE4E4, "Advance Y again", inline=True)
comment(0xE4E5, "Non-zero Y → stay on current page", inline=True)
comment(0xE4E7, "Y wrapped to zero → bump mem_ptr to next page", inline=True)
label(0xE4E9, "transmit_frame_b_end_check")
comment(0xE4E9, "Compare Y with tx_end_lo", inline=True)
comment(0xE4EC, "Still short of end-of-frame low byte → more to send", inline=True)
comment(0xE4EE, "Load current mem_ptr_hi", inline=True)
comment(0xE4F0, "Compare with tx_end_hi", inline=True)
comment(0xE4F3, "Still on a lower page than the end → more to send", inline=True)
comment(0xE4F5, "Recover X (trailing-byte flag) from before the loop", inline=True)
comment(0xE4F6, "Rotate bit 0 into carry", inline=True)
comment(0xE4F7, "X was even → no trailing byte, skip ahead", inline=True)
comment(0xE4F9, "X was odd → wait for TDRA once more", inline=True)
comment(0xE4FC, "BIT SR1 to test TDRA again", inline=True)
comment(0xE4FF, "TDRA clear → escape (mirror of [`&E4D4`](address:E4D4))", inline=True)
comment(0xE501, "Load the extra trailing byte", inline=True)
comment(0xE503, "Push trailing byte to TX FIFO", inline=True)
label(0xE506, "transmit_frame_b_finish")
comment(0xE506, "A = &3F: signal end-of-burst via CR2", inline=True)
comment(0xE508, "Commit CR2 – ADLC flushes and flags frame-complete", inline=True)
comment(0xE50B, "Wait for the frame-complete IRQ", inline=True)
comment(0xE50E, "A = &5A: reset mem_ptr_lo to &045A base", inline=True)
comment(0xE510, "Store mem_ptr_lo", inline=True)
comment(0xE512, "A = 4: reset mem_ptr_hi to page &04", inline=True)
comment(0xE514, "Store mem_ptr_hi – pointer ready for next builder", inline=True)
comment(0xE516, "Return; the frame has left ADLC B", inline=True)


# =====================================================================
# Poll ADLC B for activity, or escape to the main loop
#  (mirror of wait_adlc_a_idle)
# =====================================================================

label(0xE690, "wait_adlc_b_idle")
subroutine(0xE690, "wait_adlc_b_idle", hook=None,
    title="Wait for ADLC B's line to go idle (CSMA) or escape",
    description="""\
Byte-for-byte mirror of [`wait_adlc_a_idle`](address:E6DC?hex)
with `adlc_a_*` replaced by `adlc_b_*`. Same pre-transmit
carrier-sense semantics: wait for SR2 bit 2 (Rx Idle), back off
on AP/RDA, escape to [`main_loop`](address:E051) on ~131K-iteration
timeout.

Called from four sites: reset ([`&E04B`](address:E04B)),
[`&E0D5`](address:E0D5), [`&E211`](address:E211),
[`&E330`](address:E330).""")

comment(0xE690, "A = 0: seed the 24-bit timeout counter", inline=True)
comment(0xE692, "Clear timeout counter low byte", inline=True)
comment(0xE695, "Clear timeout counter mid byte", inline=True)
comment(0xE698, "A = &FE: seed for the high byte (~131K iterations)", inline=True)
comment(0xE69A, "Store timeout high; counter = &00_00_FE counting up", inline=True)
comment(0xE69D, "Read SR2 (result discarded; flags irrelevant here)", inline=True)
comment(0xE6A0, "Y = &E7: CR2 value to arm the chip on Rx-Idle exit", inline=True)
label(0xE6A2, "wait_adlc_b_idle_loop")
comment(0xE6A2, "A = &67: standard listen-mode CR2 value", inline=True)
comment(0xE6A4, "Re-prime CR2 – clears any stale status bits", inline=True)
comment(0xE6A7, "A = &04: mask for SR2 bit 2 (Rx Idle / line quiet)", inline=True)
comment(0xE6A9, "Test SR2 bit 2 via BIT", inline=True)
comment(0xE6AC, "Bit set → line idle; we can transmit (exit)", inline=True)
comment(0xE6AE, "Read SR2 into A for the mask test below", inline=True)
comment(0xE6B1, "Mask AP (bit 0) + RDA (bit 7) – someone else talking?", inline=True)
comment(0xE6B3, "Neither set → still quiet-ish, just increment counter", inline=True)
comment(0xE6B5, "Mask: reset TX, RX active", inline=True)
comment(0xE6B7, "Abort our pending TX on ADLC B (yield to other station)", inline=True)
comment(0xE6BA, "Mask: TX still reset, RX IRQ enabled", inline=True)
comment(0xE6BC, "Keep CR1 in TX-reset state for another pass", inline=True)
label(0xE6BF, "wait_adlc_b_idle_tick")
comment(0xE6BF, "Bump timeout counter (LSB first)", inline=True)
comment(0xE6C2, "Low byte didn't wrap → keep polling", inline=True)
comment(0xE6C4, "Bump mid byte", inline=True)
comment(0xE6C7, "Mid byte didn't wrap → keep polling", inline=True)
comment(0xE6C9, "Bump high byte", inline=True)
comment(0xE6CC, "High byte didn't wrap → keep polling", inline=True)
comment(0xE6CE, "Counter overflowed – drop caller's return address…", inline=True)
comment(0xE6CF, "…(second PLA completes the return-address drop)", inline=True)
comment(0xE6D0, "…and escape to [`main_loop`](address:E051) without returning", inline=True)

label(0xE6D3, "wait_adlc_b_idle_ready")
comment(0xE6D3, "STY: arm CR2 with &E7 (from Y) – TX-ready listen state", inline=True)
comment(0xE6D6, "Mask: arm CR1 for transmit (TX on, IRQ off)", inline=True)
comment(0xE6D8, "Commit CR1; ADLC B ready to send", inline=True)
comment(0xE6DB, "Normal return: caller transmits the frame", inline=True)


# =====================================================================
# Poll ADLC A for activity, or escape to the main loop
# =====================================================================

label(0xE6DC, "wait_adlc_a_idle")
subroutine(0xE6DC, "wait_adlc_a_idle", hook=None,
    title="Wait for ADLC A's line to go idle (CSMA) or escape",
    description="""\
Pre-transmit carrier-sense: polls ADLC A's SR2 until the Rx Idle
bit goes high (SR2 bit 2 = 15+ consecutive 1s received, i.e. the
line is quiet and it is safe to start a frame). A 24-bit timeout
counter at `ctr24_lo`/`mid`/`hi` (`&0214-&0216`) starts at
`&00_00_FE` and increments LSB-first; overflow takes ~131K
iterations, a few seconds at typical bus speeds.

Each iteration re-primes `CR2` with `&67` (clear TX/RX status,
FC_TDRA, 2/1-byte, PSE) then reads SR2. Three outcomes:

- **SR2 bit 2 set (Rx Idle)**: line is quiet. Arm `CR2=&E7` and
  `CR1=&44`, `RTS` – caller proceeds to transmit.
- **SR2 bit 0 or bit 7 set (AP or RDA)**: another station is
  sending into this ADLC. Back off by cycling `CR1` through
  `&C2` &rarr; `&82` (reset TX without touching RX) and keep
  polling. The Bridge is not the right place to assert on a busy
  line.
- **Timeout** (counter overflows without ever seeing Rx Idle):
  `PLA/PLA` discards the caller's saved return address from the
  stack and `JMP` [`main_loop`](address:E051) escapes into the
  main Bridge loop. The code between the caller's `JSR` and the
  main loop is skipped entirely. See
  `docs/analysis/escape-to-main-control-flow.md`.

Called from four sites, always immediately before a transmit:
reset ([`&E03B`](address:E03B), before
[`transmit_frame_a`](address:E517)), [`&E0AA`](address:E0AA),
[`&E1AF`](address:E1AF), [`&E392`](address:E392).""")

comment(0xE6DC, "A = 0: seed the 24-bit timeout counter", inline=True)
comment(0xE6DE, "Clear timeout counter low byte", inline=True)
comment(0xE6E1, "Clear timeout counter mid byte", inline=True)
comment(0xE6E4, "A = &FE: seed for the high byte (gives ~131K iterations)", inline=True)
comment(0xE6E6, "Store timeout high; counter = &00_00_FE counting up", inline=True)
comment(0xE6E9, "Read SR2 (result discarded; flags irrelevant here)", inline=True)
comment(0xE6EC, "Y = &E7: CR2 value arm the chip with on Rx-Idle exit", inline=True)
label(0xE6EE, "wait_adlc_a_idle_loop")
comment(0xE6EE, "A = &67: standard listen-mode CR2 value", inline=True)
comment(0xE6F0, "Re-prime CR2 – clears any stale status bits", inline=True)
comment(0xE6F3, "A = &04: mask for SR2 bit 2 (Rx Idle / line quiet)", inline=True)
comment(0xE6F5, "Test SR2 bit 2 via BIT", inline=True)
comment(0xE6F8, "Bit set → line idle; we can transmit (exit)", inline=True)
comment(0xE6FA, "Read SR2 into A for the mask test below", inline=True)
comment(0xE6FD, "Mask AP (bit 0) + RDA (bit 7) – someone else talking?", inline=True)
comment(0xE6FF, "Neither set → still quiet-ish, just increment counter", inline=True)
comment(0xE701, "Mask: reset TX, RX active", inline=True)
comment(0xE703, "Abort our pending TX on ADLC A (yield to the other station)", inline=True)
comment(0xE706, "Mask: TX still reset, RX IRQ enabled", inline=True)
comment(0xE708, "Keep CR1 in TX-reset state for another pass", inline=True)
label(0xE70B, "wait_adlc_a_idle_tick")
comment(0xE70B, "Bump timeout counter (LSB first)", inline=True)
comment(0xE70E, "Low byte didn't wrap → keep polling", inline=True)
comment(0xE710, "Bump mid byte", inline=True)
comment(0xE713, "Mid byte didn't wrap → keep polling", inline=True)
comment(0xE715, "Bump high byte", inline=True)
comment(0xE718, "High byte didn't wrap → keep polling", inline=True)
comment(0xE71A, "Counter overflowed – drop caller's return address…", inline=True)
comment(0xE71B, "…(second PLA completes the return-address drop)", inline=True)
comment(0xE71C, "…and escape to [`main_loop`](address:E051) without returning", inline=True)

label(0xE71F, "wait_adlc_a_idle_ready")
comment(0xE71F, "STY: arm CR2 with &E7 (from Y) – TX-ready listen state", inline=True)
comment(0xE722, "Mask: arm CR1 for transmit (TX on, IRQ off)", inline=True)
comment(0xE724, "Commit CR1; ADLC A ready to send", inline=True)
comment(0xE727, "Normal return: caller transmits the frame", inline=True)


# =====================================================================
# Self-test (IRQ/BRK vector target)
# =====================================================================
# Entered when the push-button on the 6502 ~IRQ line is pressed. The
# operator's guide warns not to press this while connected to a live
# network – consistent with a routine that drives the ADLCs for
# diagnostic purposes. The official self-test rig is a minimal
# Econet segment: a clock box (the original Acorn/SJ design supplies
# only the bit-clock, not biasing), a T-piece joining both Bridge
# ports to one cable to the clock box, and a single terminator on
# the clock box's other socket – the terminator does double duty as
# line terminator and DC-bias source. One terminator is enough to
# bias the line for the loopback to work, so the rig is not a "full
# single-segment Econet" (which would have a terminator at each end
# of the cable run). A passive port-to-port cable is not enough –
# without clock and without bias the loopback tests can never see a
# frame. See docs/self-test-connections.png for the manual's diagram.
#
# Structure (first half annotated here; deeper tests to follow):
#   &F000  entry – disable interrupts, clear &03, fall into…
#   &F005  forcibly reset and re-init both ADLCs (differs subtly
#          from the normal adlc_*_full_reset path: CR2 is set to
#          &80 then reprogrammed, used when the previous state is
#          unknown)
#   &F02F  zero-page integrity test (&00, &01, &02 with &55/&AA)
#   &F04C  ROM checksum – sum all 8192 bytes mod 256; expected &55
#   &F070  deeper RAM test (TBD)
#   &F2C7  common failure handler – error code in A, signalled via
#          ADLC A (probable blink code)

subroutine(0xF000, "self_test", hook=None,
    title="Self-test entry (IRQ/BRK vector target)",
    description="""\
Invoked by pressing the self-test push-button on the 6502 ~IRQ
line (and, implicitly, by any BRK instruction in the ROM). Runs
through a sequence of hardware checks, signalling any failure
via [`self_test_fail`](address:F2C7?hex) with an error code in A.

Not to be pressed while the Bridge is connected to a live
network: the self-test reconfigures the ADLCs and drives their
control registers in ways that will disturb any in-flight frames.

The official self-test rig is a *minimal* Econet segment, not a
full one. It comprises a clock box (which on the original
Acorn/SJ design provides only the bit-clock, not biasing), a
T-piece joining both Bridge ports to one cable to the clock box,
and a single terminator on the clock box's other socket. The
terminator does double duty: it terminates the line *and*
provides the DC bias that lets the differential pair carry data
at all. One terminator is enough to bias the line for the
loopback test to work, which is why the rig has just one – a
real two-station Econet segment would have a terminator at each
end of the cable run. A bare port-to-port patch cable will not
work: without clock and without bias the loopback tests can
never see a frame. See `docs/self-test-connections.png` for the
manual's diagram.""")

comment(0xF000, "Mask IRQs – this routine polls and must not re-enter", inline=True)
comment(0xF001, "A = 0: initial value for the scratch pass-phase flag", inline=True)
comment(0xF003, "&03 = pass-phase; toggled by [`self_test_pass_done`](address:F264)", inline=True)

label(0xF005, "self_test_reset_adlcs")
subroutine(0xF005, "self_test_reset_adlcs", hook=None,
    is_entry_point=False,
    title="Reset both ADLCs and extinguish the status LED",
    description="""\
Byte-for-byte identical to the adlc_*_full_reset pair except for
one crucial detail: CR3 is programmed to &80 (bit 7 set) instead
of &00. CR3 bit 7 is the MC6854's LOC/DTR control bit, and the pin
it drives is inverted relative to the bit – when the control bit
is HIGH, the pin output goes LOW. On ADLC B (IC18) that pin
sources current through the front-panel status LED (anode tied to
the pin, cathode to ground), so CR3 bit 7 = 1 leaves the LED
*dark*. The LED is therefore extinguished at the start of every
normal self-test pass, marking the transition out of
normal-operation steady-on. ADLC A's LOC/DTR pin is not wired and
gets the same write for code symmetry only.

The LED does not stay dark for the whole test pass: the loopback
tests at [`self_test_loopback_a_to_b`](address:F10A) and
[`self_test_loopback_b_to_a`](address:F1AB) each begin with a full
ADLC reset (CR1 = &C0 on both chips), and that reset clears CR3
bit 7 back to 0 – which lights the LED again for the rest of the
pass. The visible flash the operator sees during a healthy
self-test is the alternation between this dark "early-tests" phase
and the lit "loopback-and-after" phase, modulated by the two-pass
structure described at [`self_test_pass_done`](address:F264).

Re-entered at [`&F26C`](address:F26C) after each "normal" pass completes; the
alternate path at [`self_test_alt_pass`](address:F26F) deliberately skips this
routine on every other pass, leaving B's CR3 bit 7 cleared from
the previous loopback reset (so the alt-pass runs entirely in the
LED-lit state).""")

comment(0xF005, "Mask: reset TX+RX, AC=1 to reach CR3/CR4", inline=True)
comment(0xF007, "Drop ADLC A into full reset", inline=True)
comment(0xF00A, "Drop ADLC B into full reset", inline=True)
comment(0xF00D, "Mask: 8-bit RX, abort-extend, NRZ encoding", inline=True)
comment(0xF00F, "Program ADLC A's CR4 (via tx2 while AC=1)", inline=True)
comment(0xF012, "Program ADLC B's CR4", inline=True)
comment(0xF015, "Mask &80: CR3 bit 7 = drive LOC/DTR low → LED OFF", inline=True)
comment(0xF017, "Program ADLC A's CR3 (pin not wired; no effect)", inline=True)
comment(0xF01A, "Mask &80 again (separate load for symmetry)", inline=True)
comment(0xF01C, "Program ADLC B's CR3 – extinguishes the status LED", inline=True)
comment(0xF01F, "Mask: TX in reset, RX IRQ enabled, AC=0", inline=True)
comment(0xF021, "Release CR1 AC bit on ADLC A (CR3 value sticks)", inline=True)
comment(0xF024, "Release CR1 AC bit on ADLC B (CR3 value sticks)", inline=True)
comment(0xF027, "Mask: clear status, FC_TDRA, 2/1-byte, PSE", inline=True)
comment(0xF029, "Commit CR2 on ADLC A", inline=True)
comment(0xF02C, "Commit CR2 on ADLC B; falls through to ZP test", inline=True)

label(0xF02F, "self_test_zp")
subroutine(0xF02F, "self_test_zp", hook=None, is_entry_point=False,
    title="Zero-page integrity test (&00-&02)",
    description="""\
Writes `&55` to `&00`, `&01`, `&02` and reads them back; then
`&AA` and reads back. Failure jumps to
[`ram_test_fail`](address:F28C) (via
[`self_test_ram_fail_jump`](address:F09D), because RAM isn't
trustworthy enough at this point to use a countable blink).

Tests only the three ZP bytes that are used as scratch by the
later self-test stages (ROM checksum, RAM scan). A full ZP test
isn't needed – the main reset handler has already exercised ZP
indirectly via [`ram_test`](address:E00B).""")

comment(0xF02F, "First test pattern = &55 (0101_0101)", inline=True)
label(0xF031, "self_test_zp_write_read")
comment(0xF031, "Write pattern to scratch byte &00", inline=True)
comment(0xF033, "Write pattern to scratch byte &01", inline=True)
comment(0xF035, "Write pattern to scratch byte &02", inline=True)
comment(0xF037, "Check &00 still reads as pattern", inline=True)
comment(0xF039, "Mismatch → [`ram_test_fail`](address:F28C) (distinct blink pattern)", inline=True)
comment(0xF03B, "Check &01 still reads as pattern", inline=True)
comment(0xF03D, "Mismatch → [`ram_test_fail`](address:F28C)", inline=True)
comment(0xF03F, "Check &02 still reads as pattern", inline=True)
comment(0xF041, "Mismatch → [`ram_test_fail`](address:F28C)", inline=True)
comment(0xF043, "Was the pattern &AA? then both halves passed", inline=True)
comment(0xF045, "Yes → continue to ROM checksum", inline=True)
comment(0xF047, "Second test pattern = &AA (1010_1010)", inline=True)
comment(0xF049, "Loop back to rerun the three-byte check", inline=True)

label(0xF04C, "self_test_rom_checksum")
comment(0xF04C, "")  # separator for reader

subroutine(0xF04C, "self_test_rom_checksum", hook=None,
    is_entry_point=False,
    title="ROM checksum",
    description="""\
Sums every byte of the 8 KiB ROM modulo 256 using a running A
accumulator. Expected total is `&55`; on mismatch, jumps to
[`self_test_fail`](address:F2C7) with `A=2`.

Runtime pointer in `&00`/`&01` starts at `&E000`; `&02` holds the
page counter (32 pages = 8 KiB). The required total is balanced
on-disc by the [`rom_checksum_adjust`](address:FFF0) byte at
`&FFF0`, hand-tuned to make the ROM-wide sum land on `&55`.""")

comment(0xF04C, "A = 0: low byte of the ROM pointer", inline=True)
comment(0xF04E, "Store pointer_lo = 0", inline=True)
comment(0xF050, "A = &20: 32 pages remaining to sum", inline=True)
comment(0xF052, "Store page counter", inline=True)
comment(0xF054, "A = &E0: pointer_hi starts at [ROM base &E000](address:E000)", inline=True)
comment(0xF056, "Store pointer_hi = &E0", inline=True)
comment(0xF058, "Y = 0: within-page byte offset", inline=True)
comment(0xF05A, "A = 0: seed the running sum", inline=True)
label(0xF05B, "self_test_rom_checksum_loop")
comment(0xF05B, "Clear carry before the addition", inline=True)
comment(0xF05C, "Add next ROM byte at (pointer),Y into running sum", inline=True)
comment(0xF05E, "Advance to next byte within the page", inline=True)
comment(0xF05F, "Loop 256 times through the current page", inline=True)
comment(0xF061, "Roll the pointer to the next 256-byte page", inline=True)
comment(0xF063, "One page done; decrement the page counter", inline=True)
comment(0xF065, "Loop until all 32 ROM pages have been summed", inline=True)
comment(0xF067, "Compare running sum with the expected &55", inline=True)
comment(0xF069, "Match → ROM is intact, proceed to RAM test", inline=True)
comment(0xF06B, "Mismatch: load error code 2 (ROM checksum fail)", inline=True)
comment(0xF06D, "Jump to the countable-blink failure handler", inline=True)

label(0xF070, "self_test_ram_pattern")
subroutine(0xF070, "self_test_ram_pattern", hook=None,
    is_entry_point=False,
    title="RAM pattern test: write &55/&AA to every byte, verify",
    description="""\
Starting at address `&0004` (skipping the three zero-page bytes
reserved for the self-test workspace at `&00`/`&01`/`&02`),
iterates through the full 8 KiB of RAM and checks that each byte
can store both `&55` and `&AA`. Pointer in `(&00,&01) = &0000`, Y
starts at 4 and wraps, page count in `&02 = &20` (32 pages =
8 KiB).

On mismatch, jumps to [`ram_test_fail`](address:F28C?hex) – a
*different* failure handler from
[`self_test_fail`](address:F2C7), because a broken RAM cannot use
the normal blink-code loop which needs RAM workspace.""")

comment(0xF070, "A = 0: low byte of the RAM-test indirect pointer", inline=True)
comment(0xF072, "Store pointer_lo", inline=True)
comment(0xF074, "A = 0: high byte – start scanning at RAM base", inline=True)
comment(0xF076, "Store pointer_hi", inline=True)
comment(0xF078, "A = &20: 32 pages to cover (the full 8 KiB)", inline=True)
comment(0xF07A, "Store page counter", inline=True)
comment(0xF07C, "Y = 4: skip &0000-&0003 (self-test scratch)", inline=True)
label(0xF07E, "self_test_ram_pattern_loop")
comment(0xF07E, "First pattern = &55 (alternating 1-0 nibbles)", inline=True)
comment(0xF080, "Write pattern to the current RAM byte", inline=True)
comment(0xF082, "Read the same byte back", inline=True)
comment(0xF084, "Verify the cell held the written pattern", inline=True)
comment(0xF086, "Mismatch → [`ram_test_fail`](address:F28C) (unreliable storage)", inline=True)
comment(0xF088, "Second pattern = &AA (the bitwise complement)", inline=True)
comment(0xF08A, "Write complement to catch stuck-bit faults", inline=True)
comment(0xF08C, "Read it back", inline=True)
comment(0xF08E, "Verify", inline=True)
comment(0xF090, "Mismatch → [`ram_test_fail`](address:F28C)", inline=True)
comment(0xF092, "Advance to next byte within the page", inline=True)
comment(0xF093, "Loop 256 times through the current page", inline=True)
comment(0xF095, "Advance to the next page", inline=True)
comment(0xF097, "One page done; decrement the remaining-page count", inline=True)
comment(0xF099, "Continue until all 32 pages verified", inline=True)
comment(0xF09B, "All 8 KiB good – fall through to the incrementing test", inline=True)

label(0xF09D, "self_test_ram_fail_jump")
comment(0xF09D, "Any RAM check mismatch lands here; forward to blinker", inline=True)

label(0xF0A0, "self_test_ram_incr")
subroutine(0xF0A0, "self_test_ram_incr", hook=None,
    is_entry_point=False,
    title="RAM incrementing-pattern test: fill with X, read back",
    description="""\
Second RAM test. Fills the whole 8 KiB with an incrementing byte
pattern (X register cycles through 0..&FF and then reinitialised
each page with a different offset, giving a distinctive pattern
across the RAM that catches address-line faults). Then reads
back and verifies.

Catches failures that a plain &55/&AA pattern would miss:
particularly address-line shorts, where writing to (say) &0410
and &0420 would land at the same cell and produce the same bytes
under a uniform pattern but different bytes under this one.

On mismatch, jumps to [`ram_test_fail`](address:F28C?hex).""")

comment(0xF0A0, "A = 0: low byte of the pointer stays zero", inline=True)
comment(0xF0A2, "Reset pointer_hi to RAM base for the fill phase", inline=True)
comment(0xF0A4, "A = &20: full 32-page coverage again", inline=True)
comment(0xF0A6, "Store the page counter", inline=True)
comment(0xF0A8, "Y = 4: skip the self-test scratch bytes", inline=True)
comment(0xF0AA, "X = 0: seed the fill value", inline=True)
label(0xF0AC, "self_test_ram_incr_fill")
comment(0xF0AC, "A = X: the current fill value", inline=True)
comment(0xF0AD, "Write it to RAM via the indirect pointer", inline=True)
comment(0xF0AF, "Increment fill value (wraps naturally at 256)", inline=True)
comment(0xF0B0, "Advance to next byte in the page", inline=True)
comment(0xF0B1, "Loop 256 times through the page", inline=True)
comment(0xF0B3, "Advance to next page", inline=True)
comment(0xF0B5, "Bump fill value by one extra per page – different offset", inline=True)
comment(0xF0B6, "Decrement page counter", inline=True)
comment(0xF0B8, "Continue filling all 32 pages", inline=True)
comment(0xF0BA, "Fill done; now reset state for the verify phase", inline=True)
comment(0xF0BC, "pointer_hi back to RAM base", inline=True)
comment(0xF0BE, "A = &20: 32 pages again", inline=True)
comment(0xF0C0, "Store page counter", inline=True)
comment(0xF0C2, "Y = 4: skip scratch bytes", inline=True)
comment(0xF0C4, "X = 0: expected value follows the same sequence", inline=True)
label(0xF0C6, "self_test_ram_incr_verify")
comment(0xF0C6, "A = X: expected byte value", inline=True)
comment(0xF0C7, "Compare with what we actually wrote and read back", inline=True)
comment(0xF0C9, "Mismatch → [`ram_test_fail`](address:F28C) (via [`&F09D`](address:F09D))", inline=True)
comment(0xF0CB, "Step expected value", inline=True)
comment(0xF0CC, "Step byte offset", inline=True)
comment(0xF0CD, "Loop through the page", inline=True)
comment(0xF0CF, "Advance to next page", inline=True)
comment(0xF0D1, "Bump offset between pages (match fill pattern)", inline=True)
comment(0xF0D2, "One page verified; decrement", inline=True)
comment(0xF0D4, "Continue through all 32 pages; falls through on success", inline=True)

label(0xF0D6, "self_test_adlc_state")
subroutine(0xF0D6, "self_test_adlc_state", hook=None,
    is_entry_point=False,
    title="Verify both ADLCs' register state after reset",
    description="""\
Checks that both ADLCs show the expected register state after
[`self_test_reset_adlcs`](address:F005) has configured them. Tests
specific bits of SR1 and SR2 on each chip (ADLC A bits from
`&C800`/`&C801`, ADLC B bits from `&D800`/`&D801`).

| code | fail at                  | reason                          |
|------|--------------------------|---------------------------------|
| 3    | [`&F107`](address:F107)  | ADLC A register-state mismatch  |
| 4    | [`&F102`](address:F102)  | ADLC B register-state mismatch  |""")

comment(0xF0D6, "Mask bit 4 (CTS bit of SR1): expect 1 after reset", inline=True)
comment(0xF0D8, "Test on ADLC A", inline=True)
comment(0xF0DB, "CTS clear → ADLC A misconfigured (fail code 3)", inline=True)
comment(0xF0DD, "Mask bit 2 (OVRN bit of SR2): expect 1 (idle, no OVRN)", inline=True)
comment(0xF0DF, "Test on ADLC A", inline=True)
comment(0xF0E2, "Bit clear → unexpected state, fail", inline=True)
comment(0xF0E4, "Mask bit 5 (DCD of SR2): expect 0 (no carrier)", inline=True)
comment(0xF0E6, "Test on ADLC A", inline=True)
comment(0xF0E9, "Bit set → unexpected carrier; fail code 3", inline=True)
comment(0xF0EB, "Same CTS check for ADLC B", inline=True)
comment(0xF0ED, "Test on ADLC B", inline=True)
comment(0xF0F0, "Clear → fail code 4", inline=True)
comment(0xF0F2, "Same OVRN check for ADLC B", inline=True)
comment(0xF0F4, "Test on ADLC B", inline=True)
comment(0xF0F7, "Clear → fail code 4", inline=True)
comment(0xF0F9, "Same DCD check for ADLC B", inline=True)
comment(0xF0FB, "Test on ADLC B", inline=True)
comment(0xF0FE, "Clear → all checks passed, proceed to loopback test", inline=True)
label(0xF100, "self_test_fail_adlc_b")
comment(0xF100, "Fail code 4: ADLC B register state wrong", inline=True)
comment(0xF102, "Jump to countable-blink failure handler", inline=True)
label(0xF105, "self_test_fail_adlc_a")
comment(0xF105, "Fail code 3: ADLC A register state wrong", inline=True)
comment(0xF107, "Jump to countable-blink failure handler", inline=True)

label(0xF10A, "self_test_loopback_a_to_b")
subroutine(0xF10A, "self_test_loopback_a_to_b", hook=None,
    is_entry_point=False,
    title="Loopback test: transmit on ADLC A, receive on ADLC B",
    description="""\
Assumes the official self-test rig is wired up – clock box for
the bit-clock, T-piece across both Bridge ports, single
terminator on the clock box's other socket (which both
terminates the line and provides its DC bias). See
[`self_test`](address:F000) for the full rationale.
Reconfigures ADLC A for transmit (`CR1=&44`) and ADLC B for
receive (`CR1=&82`), then sends a 256-byte sequence
(`0,1,2,…,255`) out of A and verifies each byte is received on B
in order by incrementing X alongside the sender's Y.

Four phases:

1. **Pre-fill** the A TX FIFO with bytes 0-7 (`Y=0..7`) while B is
   still settling – priming the pipeline before any RX checks
   begin.
2. **Handshake opening**: wait for B's first RX IRQ, verify AP,
   read and match bytes 0 and 1. This is the special "opening"
   case because the AP/RDA transitions happen on the first two
   bytes only.
3. **Streaming loop**: repeatedly send a pair via A, read a pair
   via B, compare against X (increments in lockstep), and loop
   until Y wraps to 0 (256 bytes sent).
4. **End-of-frame flush**: program `CR2=&3F` on A to flush the
   final byte with an end-of-frame marker. Drain the remaining
   bytes on B (another 255 iterations to empty B's FIFO), then
   wait for the Frame Valid bit to confirm a clean end-of-frame.

Every mismatch or missing status bit jumps to the shared fail
target at [`loopback_a_to_b_fail`](address:F151) (`&F151`) which
loads code 5 and hands off to [`self_test_fail`](address:F2C7).
Falls through to [`self_test_loopback_b_to_a`](address:F1AB) on
success.""")

comment(0xF10A, "A = &C0: ADLC full reset", inline=True)
comment(0xF10C, "Reset ADLC A", inline=True)
comment(0xF10F, "Reset ADLC B", inline=True)
comment(0xF112, "A = &82: CR1 for receive (TX reset, RX IRQ enabled)", inline=True)
comment(0xF114, "B becomes the receiver", inline=True)
comment(0xF117, "A = &E7: CR2 for active TX (listen + IRQs armed)", inline=True)
comment(0xF119, "Program CR2 on ADLC A", inline=True)
comment(0xF11C, "A = &44: CR1 for active TX (TX on, IRQ off)", inline=True)
comment(0xF11E, "A becomes the transmitter", inline=True)
comment(0xF121, "Y = 0: outbound byte counter / data value", inline=True)
comment(0xF123, "X = 0: expected RX byte on B", inline=True)

label(0xF125, "loopback_a_to_b_prefill")
comment(0xF125, "Wait for A's TDRA IRQ", inline=True)
comment(0xF128, "BIT SR1 (read CR1 addr) – test V = TDRA (bit 6)", inline=True)
comment(0xF12B, "Not TDRA → A's TX stalled; fail", inline=True)
comment(0xF12D, "Push Y into A's TX FIFO (even byte of pair)", inline=True)
comment(0xF130, "Advance Y", inline=True)
comment(0xF131, "Push Y into A's TX FIFO (odd byte of pair)", inline=True)
comment(0xF134, "Advance Y past the pair", inline=True)
comment(0xF135, "Pre-filled 8 bytes yet?", inline=True)
comment(0xF137, "Keep prefilling", inline=True)

comment(0xF139, "Wait for B's first RX IRQ", inline=True)
comment(0xF13C, "A = &01: SR2 mask for AP (Address Present)", inline=True)
comment(0xF13E, "BIT SR2 – first byte should assert AP", inline=True)
comment(0xF141, "No AP on first byte → fail", inline=True)
comment(0xF143, "Compare B's FIFO byte against X (expect 0)", inline=True)
comment(0xF146, "Mismatch → fail", inline=True)
comment(0xF148, "Advance X past the first byte", inline=True)
comment(0xF149, "Wait for B's next RX IRQ", inline=True)
comment(0xF14C, "BIT SR2 – RDA (bit 7) asserted?", inline=True)
comment(0xF14F, "RDA set → good, compare second byte", inline=True)

label(0xF151, "loopback_a_to_b_fail")
comment(0xF151, "A = 5: error code for A-to-B loopback failure", inline=True)
comment(0xF153, "Hand off to countable-blink failure handler", inline=True)

label(0xF156, "loopback_a_to_b_head_ok")
comment(0xF156, "Compare B's second FIFO byte against X (expect 1)", inline=True)
comment(0xF159, "Mismatch → fail", inline=True)
comment(0xF15B, "Advance X past the second byte", inline=True)

label(0xF15C, "loopback_a_to_b_stream_loop")
comment(0xF15C, "Wait for A's TDRA IRQ (TX slot ready)", inline=True)
comment(0xF15F, "BIT SR1 – test V = TDRA", inline=True)
comment(0xF162, "TX stalled mid-stream → fail", inline=True)
comment(0xF164, "Push even byte (Y) into A's TX FIFO", inline=True)
comment(0xF167, "Advance Y", inline=True)
comment(0xF168, "Push odd byte (Y) into A's TX FIFO", inline=True)
comment(0xF16B, "Advance Y past the pair", inline=True)
comment(0xF16C, "Wait for B's RX IRQ (pair received)", inline=True)
comment(0xF16F, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xF172, "RDA cleared early → fail", inline=True)
comment(0xF174, "Compare B's even byte against X", inline=True)
comment(0xF177, "Mismatch → fail", inline=True)
comment(0xF179, "Advance X", inline=True)
comment(0xF17A, "Compare B's odd byte against X", inline=True)
comment(0xF17D, "Mismatch → fail", inline=True)
comment(0xF17F, "Advance X past the pair", inline=True)
comment(0xF180, "Y wrapped back to 0 → all 256 bytes sent", inline=True)
comment(0xF182, "Not done → keep streaming", inline=True)
comment(0xF184, "A = &3F: CR2 end-of-frame-with-flush", inline=True)
comment(0xF186, "Commit: A pushes the final byte and closes the frame", inline=True)

label(0xF189, "loopback_a_to_b_flush_loop")
comment(0xF189, "Wait for B's remaining RX IRQ", inline=True)
comment(0xF18C, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xF18F, "Drain interrupted → fail", inline=True)
comment(0xF191, "Compare B's residual byte against X", inline=True)
comment(0xF194, "Mismatch → fail", inline=True)
comment(0xF196, "Advance X", inline=True)
comment(0xF197, "Compare B's next residual byte against X", inline=True)
comment(0xF19A, "Mismatch → fail", inline=True)
comment(0xF19C, "Advance X past the pair", inline=True)
comment(0xF19D, "X wrapped to 0 → B has drained all 256 bytes", inline=True)
comment(0xF19F, "Not done → keep draining", inline=True)
comment(0xF1A1, "Wait for the trailing end-of-frame IRQ on B", inline=True)
comment(0xF1A4, "A = &02: SR2 mask for FV (Frame Valid)", inline=True)
comment(0xF1A6, "BIT SR2 – confirm FV is set", inline=True)
comment(0xF1A9, "FV missing → malformed frame, fail", inline=True)

label(0xF1AB, "self_test_loopback_b_to_a")
subroutine(0xF1AB, "self_test_loopback_b_to_a", hook=None,
    is_entry_point=False,
    title="Loopback test: transmit on ADLC B, receive on ADLC A",
    description="""\
Mirror of [`self_test_loopback_a_to_b`](address:F10A) with adlc_a_* and adlc_b_*
swapped: ADLC B becomes transmitter (CR1=&44), ADLC A the
receiver (CR1=&82), and the same 256-byte sequence is sent and
verified. Fail target loads code 6 (instead of 5). See
[`self_test_loopback_a_to_b`](address:F10A) for the four-phase breakdown.""")

comment(0xF1AB, "A = &C0: ADLC full reset", inline=True)
comment(0xF1AD, "Reset ADLC A", inline=True)
comment(0xF1B0, "Reset ADLC B", inline=True)
comment(0xF1B3, "A = &82: CR1 for receive (TX reset, RX IRQ enabled)", inline=True)
comment(0xF1B5, "A becomes the receiver", inline=True)
comment(0xF1B8, "A = &E7: CR2 for active TX (listen + IRQs armed)", inline=True)
comment(0xF1BA, "Program CR2 on ADLC B", inline=True)
comment(0xF1BD, "A = &44: CR1 for active TX (TX on, IRQ off)", inline=True)
comment(0xF1BF, "B becomes the transmitter", inline=True)
comment(0xF1C2, "Y = 0: outbound byte counter / data value", inline=True)
comment(0xF1C4, "X = 0: expected RX byte on A", inline=True)

label(0xF1C6, "loopback_b_to_a_prefill")
comment(0xF1C6, "Wait for B's TDRA IRQ", inline=True)
comment(0xF1C9, "BIT SR1 (read CR1 addr) – test V = TDRA (bit 6)", inline=True)
comment(0xF1CC, "Not TDRA → B's TX stalled; fail", inline=True)
comment(0xF1CE, "Push Y into B's TX FIFO (even byte of pair)", inline=True)
comment(0xF1D1, "Advance Y", inline=True)
comment(0xF1D2, "Push Y into B's TX FIFO (odd byte of pair)", inline=True)
comment(0xF1D5, "Advance Y past the pair", inline=True)
comment(0xF1D6, "Pre-filled 8 bytes yet?", inline=True)
comment(0xF1D8, "Keep prefilling", inline=True)

comment(0xF1DA, "Wait for A's first RX IRQ", inline=True)
comment(0xF1DD, "A = &01: SR2 mask for AP (Address Present)", inline=True)
comment(0xF1DF, "BIT SR2 – first byte should assert AP", inline=True)
comment(0xF1E2, "No AP on first byte → fail", inline=True)
comment(0xF1E4, "Compare A's FIFO byte against X (expect 0)", inline=True)
comment(0xF1E7, "Mismatch → fail", inline=True)
comment(0xF1E9, "Advance X past the first byte", inline=True)
comment(0xF1EA, "Wait for A's next RX IRQ", inline=True)
comment(0xF1ED, "BIT SR2 – RDA (bit 7) asserted?", inline=True)
comment(0xF1F0, "RDA set → good, compare second byte", inline=True)

label(0xF1F2, "loopback_b_to_a_fail")
comment(0xF1F2, "A = 6: error code for B-to-A loopback failure", inline=True)
comment(0xF1F4, "Hand off to countable-blink failure handler", inline=True)

label(0xF1F7, "loopback_b_to_a_head_ok")
comment(0xF1F7, "Compare A's second FIFO byte against X (expect 1)", inline=True)
comment(0xF1FA, "Mismatch → fail", inline=True)
comment(0xF1FC, "Advance X past the second byte", inline=True)

label(0xF1FD, "loopback_b_to_a_stream_loop")
comment(0xF1FD, "Wait for B's TDRA IRQ (TX slot ready)", inline=True)
comment(0xF200, "BIT SR1 – test V = TDRA", inline=True)
comment(0xF203, "TX stalled mid-stream → fail", inline=True)
comment(0xF205, "Push even byte (Y) into B's TX FIFO", inline=True)
comment(0xF208, "Advance Y", inline=True)
comment(0xF209, "Push odd byte (Y) into B's TX FIFO", inline=True)
comment(0xF20C, "Advance Y past the pair", inline=True)
comment(0xF20D, "Wait for A's RX IRQ (pair received)", inline=True)
comment(0xF210, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xF213, "RDA cleared early → fail", inline=True)
comment(0xF215, "Compare A's even byte against X", inline=True)
comment(0xF218, "Mismatch → fail", inline=True)
comment(0xF21A, "Advance X", inline=True)
comment(0xF21B, "Compare A's odd byte against X", inline=True)
comment(0xF21E, "Mismatch → fail", inline=True)
comment(0xF220, "Advance X past the pair", inline=True)
comment(0xF221, "Y wrapped back to 0 → all 256 bytes sent", inline=True)
comment(0xF223, "Not done → keep streaming", inline=True)
comment(0xF225, "A = &3F: CR2 end-of-frame-with-flush", inline=True)
comment(0xF227, "Commit: B pushes the final byte and closes the frame", inline=True)

label(0xF22A, "loopback_b_to_a_flush_loop")
comment(0xF22A, "Wait for A's remaining RX IRQ", inline=True)
comment(0xF22D, "BIT SR2 – RDA still asserted?", inline=True)
comment(0xF230, "Drain interrupted → fail", inline=True)
comment(0xF232, "Compare A's residual byte against X", inline=True)
comment(0xF235, "Mismatch → fail", inline=True)
comment(0xF237, "Advance X", inline=True)
comment(0xF238, "Compare A's next residual byte against X", inline=True)
comment(0xF23B, "Mismatch → fail", inline=True)
comment(0xF23D, "Advance X past the pair", inline=True)
comment(0xF23E, "X wrapped to 0 → A has drained all 256 bytes", inline=True)
comment(0xF240, "Not done → keep draining", inline=True)
comment(0xF242, "Wait for the trailing end-of-frame IRQ on A", inline=True)
comment(0xF245, "A = &02: SR2 mask for FV (Frame Valid)", inline=True)
comment(0xF247, "BIT SR2 – confirm FV is set", inline=True)
comment(0xF24A, "FV missing → malformed frame, fail", inline=True)

label(0xF24C, "self_test_check_netnums")
subroutine(0xF24C, "self_test_check_netnums", hook=None,
    is_entry_point=False,
    title="Verify jumper-set network numbers match self-test expectations",
    description="""\
Checks that `net_num_a == 1` and `net_num_b == 2`. The self-test
presumes a standard loopback-test configuration: the jumpers on
the bridge board should be set for 1 and 2 respectively before
the self-test button is pressed, so that the network numbers are
predictable and the loopback tests can complete without colliding
with anything else a tester might leave plugged in.

| code | condition         | fail at                     |
|------|-------------------|-----------------------------|
| 7    | `net_num_a != 1`  | [`&F255`](address:F255)     |
| 8    | `net_num_b != 2`  | [`&F261`](address:F261)     |""")

comment(0xF24C, "Fetch the side-A jumper setting", inline=True)
comment(0xF24F, "Expected self-test value = 1", inline=True)
comment(0xF251, "Match → move on to check side B", inline=True)
comment(0xF253, "Mismatch: load error code 7", inline=True)
comment(0xF255, "Jump to countable-blink failure handler", inline=True)
label(0xF258, "self_test_check_netnum_b")
comment(0xF258, "Fetch the side-B jumper setting", inline=True)
comment(0xF25B, "Expected self-test value = 2", inline=True)
comment(0xF25D, "Match → end-of-pass bookkeeping", inline=True)
comment(0xF25F, "Mismatch: load error code 8", inline=True)
comment(0xF261, "Jump to countable-blink failure handler", inline=True)

label(0xF264, "self_test_pass_done")
subroutine(0xF264, "self_test_pass_done", hook=None,
    is_entry_point=False,
    title="End-of-pass: toggle scratch flag and loop for another pass",
    description="""\
Reached when every test in a pass has succeeded. The self-test
doesn't stop – it loops indefinitely until reset. Toggles bit 7
of `&0003` (the self-test scratch byte) via `EOR #&FF`; if bit 7
is set after the toggle, JMPs to
[`self_test_reset_adlcs`](address:F005) for another full pass.
Otherwise falls through to [`self_test_alt_pass`](address:F26F),
which resets ADLCs differently before re-entering the ZP test.

The two-pass structure is what produces the "even mark-space"
flashing the operator sees during a healthy self-test. A "normal"
pass starts with [`self_test_reset_adlcs`](address:F005) writing
CR3 = &80 on ADLC B (LED dark), and the LED stays dark through
the ZP, ROM-checksum, and RAM tests. The first loopback test then
issues `CR1 = &C0` on B, which – per the MC6854 datasheet – clears
the LOC/DTR control bit, so the LED comes on for the rest of the
pass. The alt-pass runs the same tests over again but skips
[`self_test_reset_adlcs`](address:F005), so B's CR3 stays cleared
from the previous loopback reset and the LED stays *lit* for the
entire alt-pass. The cycle is therefore: short dark stretch (early
normal-pass tests) → long lit stretch (rest of normal pass + entire
alt-pass) → short dark stretch → … – a slow, asymmetric flash
whose mark and space the operator perceives as the "running"
indicator.""")

comment(0xF264, "Read the pass-phase flag at &03", inline=True)
comment(0xF266, "Invert it so we alternate between passes", inline=True)
comment(0xF268, "Store the flipped phase back", inline=True)
comment(0xF26A, "If bit 7 set, restart with full [`self_test_reset_adlcs`](address:F005) (LED goes dark)", inline=True)
comment(0xF26C, "Jump up to redo from the top", inline=True)
label(0xF26F, "self_test_alt_pass")
comment(0xF26F, "Alt-pass: partial reset on A only; B's CR3 carries over (LED stays lit)", inline=True)
comment(0xF271, "ADLC A CR1 = &C1 (reset + AC=1)", inline=True)
comment(0xF274, "A = 0: CR3=&00 for A only (B's CR3 untouched – stays cleared from last loopback)", inline=True)
comment(0xF276, "Program CR3 on A only this pass", inline=True)
comment(0xF279, "Mask: back to normal listen-mode CR1", inline=True)
comment(0xF27B, "Commit CR1 on ADLC A", inline=True)
comment(0xF27E, "Commit CR1 on ADLC B", inline=True)
comment(0xF281, "Mask: standard listen-mode CR2", inline=True)
comment(0xF283, "Commit CR2 on ADLC A", inline=True)
comment(0xF286, "Commit CR2 on ADLC B", inline=True)
comment(0xF289, "Enter the ZP test again (skip the ADLC reset)", inline=True)

label(0xF28C, "ram_test_fail")
subroutine(0xF28C, "ram_test_fail", hook=None,
    title="RAM-failure blink pattern (does not use RAM)",
    description="""\
Reached from any of the three RAM tests on failure – ZP test,
pattern RAM test, incrementing RAM test. This handler can't
use RAM for counting blinks (if RAM is broken, reading/writing
RAM is exactly what's untrustworthy), so it generates its blink
pattern from ROM-based DEC abs,X instructions that exercise the
CPU for timing without touching RAM.

Sets CR1=1 (AC=1) so writes to adlc_a_cr2 target CR3. Alternates
CR3 between &00 (LED on – LOC/DTR pin high) and &80 (LED off –
LOC/DTR pin driven low) in an infinite loop paced by DEX/DEY
delays and by seven DEC instructions that read-modify-write (but
actually just read, since writes to ROM are ignored) bytes in the
ROM starting at the reset vector.

Continues forever; the operator infers "the RAM is bad" from the
fact that the LED is blinking but no specific error code can be
counted out – distinct from the more structured blink patterns
produced by [`self_test_fail`](address:F2C7) with codes 2-8.""")

comment(0xF28C, "CR1 = 1: enable AC so cr2 writes hit CR3", inline=True)
comment(0xF28E, "Commit CR1 on ADLC A", inline=True)
label(0xF291, "ram_test_fail_loop")
comment(0xF291, "CR3 = 0 → LOC/DTR pin high → LED ON on ADLC B", inline=True)
comment(0xF293, "Commit CR3", inline=True)
comment(0xF296, "X = 0: inner delay counter", inline=True)
comment(0xF298, "Y = 0: outer delay counter", inline=True)
label(0xF29A, "ram_test_fail_short_delay")
comment(0xF29A, "Pure-register busy-wait (no RAM access)", inline=True)
comment(0xF29B, "Spin through X's 256 values", inline=True)
comment(0xF29D, "Bump Y", inline=True)
comment(0xF29E, "Spin through Y's 256 values", inline=True)
comment(0xF2A0, "CR3 = &80 → LOC/DTR pin driven low → LED OFF", inline=True)
comment(0xF2A2, "Commit CR3", inline=True)
comment(0xF2A5, "Y = 0 for the longer delay phase", inline=True)
comment(0xF2A7, "X = 0", inline=True)
label(0xF2A9, "ram_test_fail_long_delay")
comment(0xF2A9, "DEC of ROM (writes ignored); seven of them in a row…", inline=True)
comment(0xF2AC, "…pace the LED-off interval without RAM writes", inline=True)
comment(0xF2AF, "(all seven DECs hit the same RO address)", inline=True)
comment(0xF2B2, "DEC reset,X again – 4 cycles, no side effect", inline=True)
comment(0xF2B5, "DEC reset,X again – 4 cycles, no side effect", inline=True)
comment(0xF2B8, "DEC reset,X again – 4 cycles, no side effect", inline=True)
comment(0xF2BB, "Last of the seven; together they lengthen the inner tick", inline=True)
comment(0xF2BE, "Step X", inline=True)
comment(0xF2BF, "Spin through X's 256 values", inline=True)
comment(0xF2C1, "Step Y", inline=True)
comment(0xF2C2, "Spin through Y's 256 values", inline=True)
comment(0xF2C4, "Loop forever; LED alternates at an uncountable pace", inline=True)


label(0xF2C7, "self_test_fail")
subroutine(0xF2C7, "self_test_fail", hook=None,
    title="Self-test failure – signal error code via the LED",
    description="""\
Common failure exit for every non-RAM self-test stage. Called with
the error code in A. Saves two copies of the code in `&00`/`&01`
then enters an infinite loop that blinks the LED (via CR3 bit 7 on
ADLC B, which is the pin that drives the front-panel LED) a count
of times equal to the error code, separated by longer gaps.

Error codes:

| code | meaning                        | fail point                                          |
|------|--------------------------------|-----------------------------------------------------|
| 2    | ROM checksum mismatch          | [`self_test_rom_checksum`](address:F04C)            |
| 3    | ADLC A register state wrong    | `self_test_adlc_state` at [`&F107`](address:F107)   |
| 4    | ADLC B register state wrong    | `self_test_adlc_state` at [`&F102`](address:F102)   |
| 5    | A-to-B loopback fail           | [`self_test_loopback_a_to_b`](address:F10A) at [`&F153`](address:F153) |
| 6    | B-to-A loopback fail           | [`self_test_loopback_b_to_a`](address:F1AB) at [`&F1F4`](address:F1F4) |
| 7    | `net_num_a != 1`               | [`self_test_check_netnums`](address:F24C) at [`&F255`](address:F255) |
| 8    | `net_num_b != 2`               | [`self_test_check_netnums`](address:F24C) at [`&F261`](address:F261) |

Code 1 is not used: the zero-page integrity test's failure path
routes to [`ram_test_fail`](address:F28C) via
[`self_test_ram_fail_jump`](address:F09D?hex), not here, because
any failure of the first three RAM tests means normal counting
loops can't be trusted. [`ram_test_fail`](address:F28C?hex) uses a
distinct ROM-only blink instead.

**Blink pattern**: `CR1=1` sets the ADLC's AC bit so writes to
CR2's address hit CR3. The handler alternates `CR3=&00` (LED on
– LOC/DTR pin high) and `CR3=&80` (LED off – pin driven low) N
times, where N = error code held in `&01`. Each pulse pair runs
~1 s of LED-on followed by ~1 s of LED-off, so a burst of N pulses
contains N visible flashes. After the burst, the LED is left in
its OFF state (the last `CR3 = &80` write before the spacer runs)
and the spacer's 8× DEX/DEY iteration extends that OFF state to
~8 s before the next burst begins. The operator counts the LED-on
flashes inside each burst – distinguishing them from the long
~8 s LED-off gap that separates bursts – to identify the failed
test.""")

comment(0xF2C7, "Save error code to &00 (the restart value)", inline=True)
comment(0xF2C9, "…and to &01 (the per-burst countdown)", inline=True)
comment(0xF2CB, "X = 1: enable AC on ADLC A", inline=True)
comment(0xF2CD, "Commit CR1 so cr2 writes hit CR3 from here on", inline=True)
label(0xF2D0, "self_test_fail_pulse")
comment(0xF2D0, "X = 0: CR3 off → LOC/DTR pin high → LED LIT", inline=True)
comment(0xF2D2, "Commit CR3 = 0", inline=True)
comment(0xF2D5, "Y = 0: outer loop counter for the LED-lit phase", inline=True)
comment(0xF2D7, "X = 0: inner loop counter", inline=True)
label(0xF2D9, "self_test_fail_lit_delay")
comment(0xF2D9, "DEX – tick the inner counter", inline=True)
comment(0xF2DA, "Inner spin through X's 256 values", inline=True)
comment(0xF2DC, "Step Y", inline=True)
comment(0xF2DD, "Outer spin: Y cycles give ~65K iterations with LED lit", inline=True)
comment(0xF2DF, "X = &80: CR3 bit 7 set → LOC/DTR pin low → LED DARK", inline=True)
comment(0xF2E1, "Commit CR3 = &80", inline=True)
comment(0xF2E4, "Y = 0", inline=True)
comment(0xF2E6, "X = 0", inline=True)
label(0xF2E8, "self_test_fail_dark_delay")
comment(0xF2E8, "DEX – tick the inner counter", inline=True)
comment(0xF2E9, "Inner spin through X's 256 values (LED dark)", inline=True)
comment(0xF2EB, "Step Y", inline=True)
comment(0xF2EC, "Outer spin: Y cycles give the same length as the lit phase", inline=True)
comment(0xF2EE, "One pulse done; decrement the burst counter", inline=True)
comment(0xF2F0, "Loop until we've emitted N pulses", inline=True)
comment(0xF2F2, "A = 8: spacer count between bursts", inline=True)
comment(0xF2F4, "Seed the spacer loop counter", inline=True)
comment(0xF2F6, "Y = 0", inline=True)
comment(0xF2F8, "X = 0", inline=True)
label(0xF2FA, "self_test_fail_spacer_delay")
comment(0xF2FA, "DEX – tick the inner spacer counter", inline=True)
comment(0xF2FB, "Inner spin through X's 256 values (LED stays off after last pulse)", inline=True)
comment(0xF2FD, "Step Y", inline=True)
comment(0xF2FE, "Outer spin: 8x this pair keeps the gap audibly long", inline=True)
comment(0xF300, "Decrement spacer loop counter", inline=True)
comment(0xF302, "Repeat eight times total", inline=True)
comment(0xF304, "Reload the N-pulse counter with the saved error code", inline=True)
comment(0xF306, "Store into &01 for the next burst", inline=True)
comment(0xF308, "Jump back to start another N-pulse burst forever", inline=True)


# =====================================================================
# Generate output
# =====================================================================

output = go(print_output=False)

_output_dirpath.mkdir(parents=True, exist_ok=True)
output_filepath = _output_dirpath / "econet-bridge-variant_1.asm"
output_filepath.write_text(output)
print(f"Wrote {output_filepath}", file=sys.stderr)

try:
    structured = get_structured()
    json_filepath = _output_dirpath / "econet-bridge-variant_1.json"
    json_filepath.write_text(json.dumps(structured))
    print(f"Wrote {json_filepath}", file=sys.stderr)
except (AssertionError, Exception) as e:
    print(f"Warning: JSON output skipped: {e}", file=sys.stderr)
