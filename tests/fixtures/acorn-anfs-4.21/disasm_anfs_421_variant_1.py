import os
from pathlib import Path

from py8dis.commands import *
import py8dis.acorn as acorn
import py8dis.trace as trace

init(assembler_name="beebasm", lower_case=True)

# ============================================================
# ANFS 4.21 (variant 1) — Acorn Advanced Network Filing System
# ============================================================
# 16KB service ROM (&8000-&BFFF). Successor to NFS 3.65.
# Incorporates filing system commands (previously on server),
# printer support, and other improvements.
# Authors: B Cockburn, J Dunn, B Robertson, J Wills.

# Paths are resolved relative to this script's location in the repo
_script_dirpath = Path(__file__).resolve().parent
_version_dirpath = _script_dirpath.parent
_rom_filepath = os.environ.get(
    "FANTASM_ROM",
    str(_version_dirpath / "rom" / "anfs-4.21_variant_1.rom"),
)
_output_dirpath = Path(os.environ.get(
    "FANTASM_OUTPUT_DIR",
    str(_version_dirpath / "output"),
))

load(0x8000, _rom_filepath, "65c02")
trace.cpu.default_subroutine_hook = None

# No relocated code blocks: this build keeps its filing-system
# workspace in HAZEL (Master 128 hidden RAM at &C000-&DFFF, paged
# over the MOS VDU drivers when ACCCON bit Y is set). ANFS uses
# the &C000-&C2FF slice for its FS workspace -- a 768-byte
# private region inside HAZEL's 8 KB extent. The 4.18 page-4-6
# relocated workspace in main MOS RAM is gone.

byte(0xBFC7)  # Force padding byte onto its own line for annotation

# Three explicit labels for the HAZEL-indexing-base trick at the
# end of the ROM image. HAZEL starts at &C000, so a label sitting
# N bytes before &C000, accessed as `LDA <label>,Y` with Y >= N,
# lands inside HAZEL. The auto-generated names `hazel_minus_1a / hazel_minus_2 /
# hazel_minus_1` give no hint of this, so name them by their offset before
# HAZEL.
label(0xBFE6, "hazel_minus_1a")
label(0xBFFE, "hazel_minus_2")
label(0xBFFF, "hazel_minus_1")

data_banner(0xBFC5, "rom_tail_padding",
    title="ROM-tail &FF padding (33 bytes positioning the HAZEL indexing bases)",
    description="""\
33 bytes of `&FF` filler between the last real instruction at
[`inx4`](address:BFC0) and the HAZEL indexing-base labels
starting at [`hazel_minus_1a`](address:BFE6).

These bytes exist purely to push the indexing-base labels to
specific addresses immediately before `&C000` (the start of
HAZEL). The labels themselves do the work -- see the
[`hazel_idx_bases`](address:BFE6) banner. The padding is never
read or written; it is whatever the assembler emitted to fill
the gap (the BeebAsm default of `&FF`).""")

data_banner(0xBFE6, "hazel_idx_bases",
    title="HAZEL Y-indexed access bases (3 labels at the ROM tail)",
    description="""\
Three labels positioned `&1A`, `2`, and `1` bytes before `&C000`
(the start of HAZEL), used as **indexing bases for reads and
writes into HAZEL**.

The trick: HAZEL begins at `&C000`, so an `LDA hazel_minus_2,Y`
/ `STA hazel_minus_2,Y` instruction with Y >= 2 lands at
`&BFFE + Y >= &C000` -- inside HAZEL. ANFS exploits this in
several places to copy fixed-size blocks between HAZEL workspace
and other buffers without burning a separate two-byte zero-page
pointer:

| Site / routine                | instruction                  | base             | Y range | Effective range            |
|-------------------------------|------------------------------|------------------|---------|----------------------------|
| `loop_copy_fs_ctx`            | `STA hazel_minus_2,Y`        | `hazel_minus_2`  | 9..2    | `&C007..&C000`             |
| `loop_restore_ctx`            | `LDA hazel_minus_2,Y`        | `hazel_minus_2`  | 9..2    | `&C007..&C000`             |
| `loop_copy_ws_to_pb`          | `LDA hazel_minus_2,Y`        | `hazel_minus_2`  | 4..6    | `&C002..&C004`             |
| `loop_copy_station`           | `LDA hazel_minus_1,Y`        | `hazel_minus_1`  | 2..1    | `&C001..&C000`             |
| `osword_13_set_station_body`  | `STA hazel_minus_1,Y`        | `hazel_minus_1`  | 2..1    | `&C001..&C000`             |
| `loop_copy_txcb_init`         | `LDA hazel_minus_1a,Y`       | `hazel_minus_1a` | >= &1A  | spans into HAZEL from `&C000` |

Each loop's CPY/BNE guard stops Y before it would land inside
the ROM tail, so the actual workspace data lives entirely in
HAZEL. The labels themselves never have their own bytes read --
the `&FF` byte at each label address is incidental, only the
address matters.""")

# acorn.bbc() provides OS vectors, entry points, zero page labels.
# acorn.is_sideways_rom() provides ROM header labels.
acorn.bbc()
acorn.is_sideways_rom()

# ============================================================
# Inline string subroutine hooks
# ============================================================
# print_inline (&9131) prints an inline string following the JSR, terminated
# by a byte with bit 7 set. The high-bit byte is the opcode of the next
# instruction — the routine jumps there via JMP (fs_error_ptr).
hook_subroutine(0x9261, "print_inline", stringhi_hook)

# print_inline_no_spool (&928A) follows the same calling convention as
# print_inline but routes characters through print_char_no_spool so they
# don't enter any active *SPOOL capture. Hooked so py8dis classifies the
# inline strings as data and resumes tracing at the high-bit terminator
# (which doubles as the next opcode).
hook_subroutine(0x928A, "print_inline_no_spool", stringhi_hook)

# error_inline (&96BE) builds a BRK error block from a null-terminated inline
# string following the JSR. The error number is passed in A. Never returns.
hook_subroutine(0x99C3, "error_inline", stringz_hook)

# error_inline_log (&96BB) is identical to error_inline but first logs the
# error code via cond_save_error_code. Never returns.
hook_subroutine(0x99C0, "error_inline_log", stringz_hook)

# error_bad_inline (&96A2) prepends "Bad " to the inline string before
# building the BRK error block. The error number is passed in A. Never returns.
hook_subroutine(0x99A7, "error_bad_inline", stringz_hook)


# ============================================================
# Hardware registers
# ============================================================
# Phase L0 (2026-05-02): hardware registers, MOS extended vectors,
# and MOS vector-table entries declared as label() with memory-map
# metadata (per AUTHORING.md §3) so they show up on the version's
# memory-map page and resolve cleanly when subroutine descriptions
# link to them via [name](address:HEX?hex).

# MC6854 ADLC registers (active at &FEA0-&FEA3 when active Econet station)
label(0xFEA0, "adlc_cr1",
    description="ADLC control register 1 / status register 1.\n"
                "Write: `CR1` (or `CR3` if `AC=1`). Read: `SR1`.\n\n"
                "`SR1` bits: `RDA` (b0), `S2RQ` (b1), `LOOP` (b2), "
                "`FD` (b3), `CTS` (b4), `TUF` (b5), `TDRA` (b6), "
                "`IRQ` (b7).",
    length=1, group="mmio", access="rw")
label(0xFEA1, "adlc_cr2",
    description="ADLC control register 2 / status register 2.\n"
                "Write: `CR2` (or `CR4` if `AC=1`). Read: `SR2`.\n\n"
                "`SR2` bits: `AP` (b0), `FV` (b1), `RX_IDLE` (b2), "
                "`RX_ABRT` (b3), `ERR` (b4), `DCD` (b5), `OVRN` (b6), "
                "`RDA` (b7).",
    length=1, group="mmio", access="rw")
label(0xFEA2, "adlc_tx",
    description="ADLC TX FIFO continue / RX FIFO read.\n"
                "Write: byte to TX FIFO with `LAST_DATA = 0` "
                "(continue frame).\n"
                "Read: next byte from RX FIFO.",
    length=1, group="mmio", access="rw")
label(0xFEA3, "adlc_tx2",
    description="ADLC TX FIFO terminate / RX FIFO read.\n"
                "Write: final byte of frame (`LAST_DATA = 1`; ADLC "
                "appends CRC + closing flag).\n"
                "Read: next byte from RX FIFO.",
    length=1, group="mmio", access="rw")

# Econet hardware on the 1MHz bus
label(0xFE18, "econet_station_id",
    description="Econet station ID register / INTOFF latch.\n"
                "Read: station DIP-switch byte (1..254) AND INTOFF "
                "side-effect (disables NMIs from /NMI input).\n\n"
                "ANFS reads this on every NMI entry as the first "
                "instruction of the shim, both to capture the "
                "station ID and to stop NMIs from re-firing during "
                "the body of the handler.",
    length=1, group="mmio", access="r")
label(0xFE20, "econet_nmi_enable",
    description="Econet NMI-enable register / INTON latch.\n"
                "Read: re-enables NMIs (INTON side-effect; the "
                "value read is ignored).\n\n"
                "Used by the NMI-exit shim before `RTI` so the next "
                "/NMI edge re-triggers the handler.",
    length=1, group="mmio", access="r")

# Tube ULA registers (&FEE0-&FEE7) — named by acorn.bbc()

# MOS extended-vector entry points (jumped to via the corresponding
# vec_* page-2 pointer; the MOS forwards the call through the ROM
# bank stored alongside the address).
label(0xFF1B, "ev_filev",
    description="FILEV extended-vector dispatcher (file operations: "
                "OSFILE, OSFIND).",
    length=3, group="ext_vectors", access="r")
label(0xFF1E, "ev_argsv",
    description="ARGSV extended-vector dispatcher (file argument "
                "operations: OSARGS).",
    length=3, group="ext_vectors", access="r")
label(0xFF21, "ev_bgetv",
    description="BGETV extended-vector dispatcher (single-byte read: "
                "OSBGET).",
    length=3, group="ext_vectors", access="r")
label(0xFF24, "ev_bputv",
    description="BPUTV extended-vector dispatcher (single-byte write: "
                "OSBPUT).",
    length=3, group="ext_vectors", access="r")
label(0xFF27, "ev_gbpbv",
    description="GBPBV extended-vector dispatcher (block transfer: "
                "OSGBPB).",
    length=3, group="ext_vectors", access="r")
label(0xFF2A, "ev_findv",
    description="FINDV extended-vector dispatcher (open / close: "
                "OSFIND).",
    length=3, group="ext_vectors", access="r")
label(0xFF2D, "ev_fscv",
    description="FSCV extended-vector dispatcher (filing-system "
                "control: OSFSC, *commands).",
    length=3, group="ext_vectors", access="r")

# MOS vector table entries (the ROM-vector slots in &0200..&02xx).
# Each is a 3-byte (lo, hi, rom_bank) tuple; the rom_bank slot lives
# at &0Dxx in extended-vector territory. ANFS patches its own
# extended-vector dispatchers into these slots during init.
label(0x0212, "vec_filev",
    description="FILEV pointer (lo, hi, rom). Patched to ANFS's "
                "FILE handler at init.",
    length=2, group="ram_workspace", access="rw")
label(0x0214, "vec_argsv",
    description="ARGSV pointer (lo, hi, rom). Patched to ANFS's "
                "ARGS handler at init.",
    length=2, group="ram_workspace", access="rw")
label(0x0216, "vec_bgetv",
    description="BGETV pointer (lo, hi, rom). Patched to ANFS's "
                "BGET handler at init.\n\n"
                "Note: standard layout (the alternate "
                "[`vec_bgetv_alt`](address:021A) slot is also used "
                "by some routines).",
    length=2, group="ram_workspace", access="rw")
label(0x0218, "vec_bputv",
    description="BPUTV pointer (lo, hi, rom). Patched to ANFS's "
                "BPUT handler at init.",
    length=2, group="ram_workspace", access="rw")
label(0x021A, "vec_bgetv_alt",
    description="Alternate BGETV slot (lo, hi, rom).\n"
                "Some ANFS routines use this in addition to the "
                "standard [`vec_bgetv`](address:0216) at "
                "&0216.",
    length=2, group="ram_workspace", access="rw")
label(0x021C, "vec_gbpbv",
    description="GBPBV pointer (lo, hi, rom). Patched to ANFS's "
                "GBPB handler at init.",
    length=2, group="ram_workspace", access="rw")
label(0x021E, "vec_fscv",
    description="FSCV pointer (lo, hi, rom). Patched to ANFS's "
                "FSC handler at init.",
    length=2, group="ram_workspace", access="rw")

# ============================================================
# Protocol constants
# ============================================================

# Econet port numbers
constant(0x99, "port_command")        # PCMND: command port
constant(0x90, "port_reply")          # PREPLY: reply port
constant(0x91, "port_save_ack")       # PSAACK: save acknowledge port
constant(0x92, "port_load_data")      # PLDATA: load data port
constant(0x93, "port_remote")         # PREMOT: remote operation port
constant(0xD1, "port_printer")        # PBLOCK: printer block port

# Econet error codes
constant(0xA0, "err_line_jammed")     # LINJAM
constant(0xA1, "err_net_error")       # NETER
constant(0xA2, "err_not_listening")   # NOLISE
constant(0xA3, "err_no_clock")        # NOCLK
constant(0xA4, "err_tx_cb_error")     # TXCBER
constant(0xA5, "err_no_reply")        # NOREPE
constant(0xA8, "err_fs_cutoff")       # ERRCUT: FS errors >= this

# Protocol flags
constant(0x80, "tx_flag")             # TXFLAG
constant(0x7F, "rx_ready")            # RXRDY

# FS handle base

# Control block template markers
constant(0xFE, "cb_stop")             # CBSTOP
constant(0xFD, "cb_skip")             # CBSKIP
constant(0xFC, "cb_fill")             # CBFILL

# ============================================================
# Named constants for OSBYTE/OS values
# ============================================================
constant(20,  "osbyte_explode_chars")
constant(120, "osbyte_write_keys_pressed")
constant(143, "osbyte_issue_service_request")
constant(168, "osbyte_read_rom_ptr_table_low")

# ============================================================
# Zero page — Econet workspace (&90-&A9)
# ============================================================

label(0x0097, "escapable",
    description="b7=respond to Escape flag",
    length=1, group="zero_page", access="rw")
label(0x0098, "need_release_tube",
    description="b7=need to release Tube",
    length=1, group="zero_page", access="rw")
label(0x0099, "prot_flags",
    description="PFLAGS: printer / protocol status flags.",
    length=1, group="zero_page", access="rw")
label(0x009A, "net_tx_ptr",
    description="NetTx control block pointer (low)",
    length=1, group="zero_page", access="rw")
label(0x009B, "net_tx_ptr_hi",
    description="NetTx control block pointer (high)",
    length=1, group="zero_page", access="rw")
label(0x009C, "net_rx_ptr",
    description="NetRx control blocks pointer (low byte). Pairs "
                "with [`net_rx_ptr_hi`](address:009D).",
    length=1, group="zero_page", access="rw")
label(0x009D, "net_rx_ptr_hi",
    description="NetRx control blocks pointer (high byte). Pairs "
                "with [`net_rx_ptr`](address:009C) (low).",
    length=1, group="zero_page", access="rw")
label(0x009E, "nfs_workspace",
    description="General NFS workspace pointer (low)",
    length=1, group="zero_page", access="rw")
label(0x009F, "nfs_workspace_hi",
    description="General NFS workspace pointer (high)",
    length=1, group="zero_page", access="rw")
label(0x00A0, "nmi_tx_block",
    description="NMI TX block pointer (low byte). Address of the "
                "TX control block currently being transmitted by "
                "the NMI handler.",
    length=1, group="zero_page", access="rw")
label(0x00A1, "nmi_tx_block_hi",
    description="Block to be transmitted (high)",
    length=1, group="zero_page", access="rw")
label(0x00A2, "port_buf_len",
    description="Open port buffer length (low)",
    length=1, group="zero_page", access="rw")
label(0x00A3, "port_buf_len_hi",
    description="Open port buffer length (high)",
    length=1, group="zero_page", access="rw")
label(0x00A4, "open_port_buf",
    description="Open port buffer address (low)",
    length=1, group="zero_page", access="rw")
label(0x00A5, "open_port_buf_hi",
    description="Open port buffer address (high)",
    length=1, group="zero_page", access="rw")
label(0x00A6, "port_ws_offset",
    description="Port workspace offset",
    length=1, group="zero_page", access="rw")
label(0x00A7, "rx_buf_offset",
    description="Receive buffer offset",
    length=1, group="zero_page", access="rw")
label(0x00A8, "ws_page",
    description="Multi-purpose workspace page",
    length=1, group="zero_page", access="rw")
label(0x00A9, "svc_state",
    description="Multi-purpose service state",
    length=1, group="zero_page", access="rw")
label(0x00AA, "osword_flag",
    description="OSWORD param byte",
    length=1, group="zero_page", access="rw")
label(0x00AB, "ws_ptr_lo",
    description="Workspace indirect pointer (lo)",
    length=1, group="zero_page", access="rw")
label(0x00AC, "ws_ptr_hi",
    description="Workspace indirect pointer (hi)",
    length=1, group="zero_page", access="rw")
label(0x00AD, "table_idx",
    description="OSBYTE/palette table index counter",
    length=1, group="zero_page", access="rw")
label(0x00AE, "work_ae",
    description="Indexed workspace (multi-purpose scratch)",
    length=1, group="zero_page", access="rw")
label(0x00AF, "addr_work",
    description="Address work byte for comparison (indexed)",
    length=1, group="zero_page", access="rw")

# ============================================================
# Zero page — Filing system workspace (&B0-&CF)
# ============================================================

label(0x00B0, "fs_load_addr",
    description="WORK: load/start address (4 bytes)",
    length=4, group="zero_page", access="rw")
label(0x00B1, "fs_load_addr_hi",
    length=1, group="zero_page", access="rw")
label(0x00B2, "fs_load_addr_2",
    length=1, group="zero_page", access="rw")
label(0x00B3, "fs_load_addr_3",
    length=1, group="zero_page", access="rw")
label(0x00B4, "fs_work_4",
    length=1, group="zero_page", access="rw")
label(0x00B5, "fs_work_5",
    description="FS scratch byte 5. Multi-purpose: "
                "*Wipe iteration counter, parsed FS station number, "
                "spool drive number, etc.",
    length=1, group="zero_page", access="rw")
label(0x00B6, "fs_work_6",
    description="FS scratch byte 6. Multi-purpose: "
                "*Wipe end-of-buffer offset, parsed FS network "
                "number, etc.",
    length=1, group="zero_page", access="rw")
label(0x00B7, "fs_work_7",
    length=1, group="zero_page", access="rw")
label(0x00B8, "fs_error_ptr",
    length=1, group="zero_page", access="rw")
label(0x00B9, "fs_crflag",
    length=1, group="zero_page", access="rw")
label(0x00BA, "fs_spool_handle",
    length=1, group="zero_page", access="rw")
label(0x00BB, "fs_options",
    length=1, group="zero_page", access="rw")
label(0x00BC, "fs_block_offset",
    length=1, group="zero_page", access="rw")
label(0x00BD, "fs_last_byte_flag",
    length=1, group="zero_page", access="rw")
label(0x00BE, "fs_crc_lo",
    length=1, group="zero_page", access="rw")
label(0x00BF, "fs_crc_hi",
    length=1, group="zero_page", access="rw")
label(0x00CC, "fs_ws_ptr",
    description="FS workspace page pointer (lo, always 0)",
    length=1, group="zero_page", access="rw")
label(0x00C0, "txcb_ctrl",
    length=1, group="zero_page", access="rw")
label(0x00C1, "txcb_port",
    length=1, group="zero_page", access="rw")
label(0x00C2, "txcb_dest",
    length=1, group="zero_page", access="rw")
label(0x00C4, "txcb_start",
    length=1, group="zero_page", access="rw")
label(0x00C7, "txcb_pos",
    length=1, group="zero_page", access="rw")
label(0x00C8, "txcb_end",
    length=1, group="zero_page", access="rw")
label(0x00CD, "nfs_temp",
    length=1, group="zero_page", access="rw")
label(0x00CE, "rom_svc_num",
    length=1, group="zero_page", access="rw")
label(0x00CF, "fs_spool0",
    length=1, group="zero_page", access="rw")
label(0x00D0, "vdu_status",
    description="VDU status register (OSBYTE &75)",
    length=1, group="zero_page", access="rw")

# Zero page — Additional OS locations
label(0x0000, "zp_ptr_lo",
    length=1, group="zero_page", access="rw")
label(0x0001, "zp_ptr_hi",
    length=1, group="zero_page", access="rw")
label(0x0002, "zp_work_2",
    length=1, group="zero_page", access="rw")
label(0x0003, "zp_work_3",
    length=1, group="zero_page", access="rw")
label(0x0010, "zp_temp_10",
    length=1, group="zero_page", access="rw")
label(0x0011, "zp_temp_11",
    length=1, group="zero_page", access="rw")
label(0x0012, "tube_data_ptr",
    length=1, group="zero_page", access="rw")
label(0x0013, "tube_data_ptr_hi",
    length=1, group="zero_page", access="rw")
label(0x0014, "tube_claim_flag",
    length=1, group="zero_page", access="rw")
label(0x0015, "tube_claimed_id",
    length=1, group="zero_page", access="rw")
label(0x0063, "zp_0063",
    description="(false ref from inline string data)",
    length=1, group="zero_page", access="rw")
label(0x0078, "zp_0078",
    description="(false ref from inline string data)",
    length=1, group="zero_page", access="rw")

# Zero page — MOS locations (&EF-&FF)
label(0x00EF, "osbyte_a_copy",
    length=1, group="zero_page", access="rw")
label(0x00F0, "osword_pb_ptr",
    length=1, group="zero_page", access="rw")
label(0x00F1, "osword_pb_ptr_hi",
    length=1, group="zero_page", access="rw")
label(0x00F3, "os_text_ptr_hi",
    length=1, group="zero_page", access="rw")
label(0x00F7, "osrdsc_ptr_hi",
    length=1, group="zero_page", access="rw")
label(0x00FD, "brk_ptr",
    length=1, group="zero_page", access="rw")
label(0x00FF, "escape_flag",
    length=1, group="zero_page", access="rw")

# Page 1 — Stack page

# Page 2 — OS workspace

# Page 3 — VDU variables

# Page 7 — String buffer

# Page &0C — NMI shim write base

# ============================================================
# Page &0D — NMI handler workspace (&0D00-&0DFF)
# ============================================================

label(0x0D07, "nmi_romsel",
    description="ROM-bank number patched into the NMI shim.\n"
                "The NMI handler runs in the active sideways slot, "
                "so the shim begins by paging in the NFS ROM bank "
                "(this byte) before dispatching to the body.",
    length=1, group="ram_workspace", access="rw")
label(0x0D0C, "nmi_jmp_lo",
    description="NMI dispatch JMP-target low byte.\n"
                "Patched by [`set_nmi_vector`](address:0D0E) and "
                "[`install_nmi_handler`](address:0D11). The NMI "
                "shim does `JMP (nmi_jmp_lo)` to reach the current "
                "handler.",
    length=1, group="ram_workspace", access="rw")
label(0x0D0D, "nmi_jmp_hi",
    description="NMI dispatch JMP-target high byte.\n"
                "Paired with [`nmi_jmp_lo`](address:0D0C). Only "
                "[`set_nmi_vector`](address:0D0E) writes this; "
                "[`install_nmi_handler`](address:0D11) leaves it "
                "alone (same-page optimisation).",
    length=1, group="ram_workspace", access="rw")
# NMI exit entry points (RAM shim, copied from rom_set_nmi_vector).
# All three converge on the INTON/RTI at &0D1C/&0D1F.
label(0x0D0E, "set_nmi_vector",
    description="NMI vector update (both bytes).\n"
                "`STY` [nmi_jmp_hi](address:0D0D) then `STA` "
                "[nmi_jmp_lo](address:0D0C), writing the full "
                "16-bit NMI handler address into the JMP-target "
                "slot. Falls through to "
                "[`nmi_rti`](address:0D14).",
    length=3, group="ram_workspace", access="r")
label(0x0D11, "install_nmi_handler",
    description="NMI vector update (low byte only).\n"
                "`STA` [nmi_jmp_lo](address:0D0C) only, leaving the "
                "existing high byte at [`nmi_jmp_hi`](address:0D0D) "
                "in place. Same-page optimisation used when the "
                "next handler is in the same page as the current "
                "one. Falls through to "
                "[`nmi_rti`](address:0D14).",
    length=3, group="ram_workspace", access="r")
label(0x0D14, "nmi_rti",
    description="NMI exit shim.\n"
                "Restores the previous ROM bank, pulls Y and A off "
                "the stack, reads `BIT econet_nmi_enable` (INTON, "
                "re-enables /NMI), and `RTI`s. Reached either as a "
                "fall-through from [`set_nmi_vector`](address:0D0E) "
                "/ [`install_nmi_handler`](address:0D11), or as "
                "a direct branch from any NMI handler that has "
                "finished early.",
    length=11, group="ram_workspace", access="r")
label(0x0D1A, "imm_param_base")       # Base for indexed imm-op TXCB param copy
label(0x0D1E, "tx_addr_base")         # Base for 4-byte TX transfer address

# Scout/acknowledge packet buffer (&0D20-&0D25)
label(0x0D20, "tx_dst_stn",
    description="Destination station for next TX scout/ACK frame.",
    length=1, group="ram_workspace", access="rw")
label(0x0D21, "tx_dst_net",
    description="Destination network for next TX scout/ACK frame.",
    length=1, group="ram_workspace", access="rw")
label(0x0D22, "tx_src_stn",
    description="Source-station byte (our station ID).\n"
                "Set during init from "
                "[`econet_station_id`](address:FE18).",
    length=1, group="ram_workspace", access="rw")
label(0x0D23, "tx_src_net",
    description="Source-network byte for outgoing scout/ACK "
                "frames (typically 0 for local network).",
    length=1, group="ram_workspace", access="rw")
label(0x0D24, "tx_ctrl_byte",
    description="Control byte for next TX scout frame.",
    length=1, group="ram_workspace", access="rw")
label(0x0D25, "tx_port",
    description="Destination port for next TX scout frame.",
    length=1, group="ram_workspace", access="rw")
label(0x0D26, "tx_data_start",
    description="Start of TX data buffer (used by scout/data frame "
                "construction).",
    length=1, group="ram_workspace", access="rw")

# TX control
label(0x0D2A, "tx_data_len",
    description="Length of the TX data buffer payload, used "
                "during scout/data frame construction.",
    length=1, group="ram_workspace", access="rw")

# RX scout buffer (&0D2E-&0D39)
label(0x0D2E, "scout_buf",
    description="Base of the 12-byte RX scout data buffer.\n"
                "Holds the most recently received scout frame "
                "during reception and ACK transmission.",
    length=12, group="ram_workspace", access="rw")
label(0x0D2F, "scout_src_net",
    description="Scout source network byte ([`scout_buf`](address:0D2E)+1).",
    length=1, group="ram_workspace", access="rw")
label(0x0D30, "scout_ctrl",
    description="Scout control byte ([`scout_buf`](address:0D2E)+2).\n"
                "Carries the immediate-op code (`&81`..`&88`) for "
                "port-0 scouts; checked by "
                "[`immediate_op`](address:8454).",
    length=1, group="ram_workspace", access="rw")
label(0x0D31, "scout_port",
    description="Scout port byte ([`scout_buf`](address:0D2E)+3).",
    length=1, group="ram_workspace", access="rw")
label(0x0D32, "scout_data",
    description="Scout data payload base ([`scout_buf`](address:0D2E)+4).\n"
                "Holds the 4-byte remote address for "
                "JSR / UserProc / OSProc immediate ops.",
    length=8, group="ram_workspace", access="rw")

# Received scout
label(0x0D3D, "rx_src_stn",
    description="Source station of the received scout frame.\n"
                "First address byte read by "
                "[`nmi_rx_scout`](address:809B) and validated "
                "against our station ID.",
    length=1, group="ram_workspace", access="rw")
label(0x0D3E, "rx_src_net",
    description="Source network of the received scout frame.\n"
                "Read by [`nmi_rx_scout_net`](address:80B8); "
                "used for the local-network match (0 = local, "
                "&FF = broadcast).",
    length=1, group="ram_workspace", access="rw")
label(0x0D3F, "rx_ctrl",
    description="Control byte of the received scout frame.",
    length=1, group="ram_workspace", access="rw")
label(0x0D40, "rx_port",
    description="Port byte of the received scout frame.\n"
                "Matched against the open RXCB list to find a "
                "listener (or the immediate-op port range "
                "&80..&88).",
    length=1, group="ram_workspace", access="rw")
label(0x0D41, "rx_remote_addr",
    description="Remote address byte for received TX setup.",
    length=1, group="ram_workspace", access="rw")
label(0x0D42, "rx_extra_byte",
    description="Extra trailing RX data byte.",
    length=1, group="ram_workspace", access="rw")
label(0x0D43, "saved_nmi_lo",
    description="Saved next NMI handler address (low byte).\n"
                "Written by [`ack_tx_write_dest`](address:82F8) "
                "from the (A=lo, Y=hi) pair on entry, then "
                "consumed when the next NMI fires.",
    length=1, group="ram_workspace", access="rw")
label(0x0D44, "saved_nmi_hi",
    description="Saved next NMI handler address (high byte).\n"
                "Paired with [`saved_nmi_lo`](address:0D43).",
    length=1, group="ram_workspace", access="rw")

# TX state
label(0x0D4A, "tx_flags",
    description="TX path control flags.\n"
                "Bit 7: TX path is active (used by "
                "[`nmi_error_dispatch`](address:8215) to choose "
                "between RX-error reset and TX-fail dispatch).\n"
                "Bit 0: handshake-data pending.\n"
                "Bit 1: data-RX into Tube buffer (selected by "
                "[`install_data_rx_handler`](address:81F7)).",
    length=1, group="ram_workspace", access="rw")
label(0x0D4B, "nmi_next_lo",
    description="Next NMI handler address (low byte).\n"
                "Saved by the scout / data-RX handler; consumed by "
                "[`ack_tx`](address:82DF) when installing the "
                "post-ACK NMI handler.",
    length=1, group="ram_workspace", access="rw")
label(0x0D4C, "nmi_next_hi",
    description="Next NMI handler address (high byte).\n"
                "Paired with [`nmi_next_lo`](address:0D4B).",
    length=1, group="ram_workspace", access="rw")
label(0x0D4F, "tx_index",
    description="Index into the TX buffer (current byte position).",
    length=1, group="ram_workspace", access="rw")
label(0x0D50, "tx_length",
    description="Total length of the TX data payload.",
    length=1, group="ram_workspace", access="rw")

# ANFS-specific workspace (identified from references in ROM)
label(0x0D60, "tx_complete_flag",
    description="TX completion semaphore.\n"
                "Bit 7 set by the NMI TX-completion handler; "
                "polled by `wait_net_tx_ack` to detect frame "
                "completion.",
    length=1, group="ram_workspace", access="rw")
label(0x0D61, "econet_flags",
    description="Econet control flags.\n"
                "Bit 7: port-list active. Bit 2: halt requested.",
    length=1, group="ram_workspace", access="rw")
label(0x0D62, "econet_init_flag",
    description="Econet-initialised flag.\n"
                "Bit 7 set when the NMI shim has been installed; "
                "checked at every NMI to reject pre-init "
                "interrupts.",
    length=1, group="ram_workspace", access="rw")
label(0x0D63, "tube_present",
    description="Tube co-processor presence flag.\n"
                "Probed at init via OSBYTE `&EA`; read by every "
                "TX/RX path that needs to forward data through "
                "the Tube.",
    length=1, group="ram_workspace", access="rw")
label(0x0D64, "ws_0d64",
    description="ANFS workspace byte (role TBD).",
    length=1, group="ram_workspace", access="rw")
label(0x0D65, "tx_op_type",
    description="Deferred-work / TX-operation type flag.\n"
                "Set by NMI handlers to mark pending work; "
                "polled by [`svc5_irq_check`](address:8028) "
                "as the dispatch trigger.",
    length=1, group="ram_workspace", access="rw")
label(0x0D66, "exec_addr_lo",
    description="Remote execution address (low byte).\n"
                "Stored by remote-JSR / immediate-op paths; "
                "consumed when the queued operation runs.",
    length=1, group="ram_workspace", access="rw")
label(0x0D67, "exec_addr_hi",
    description="Remote execution address (high byte).\n"
                "Paired with [`exec_addr_lo`](address:0D66).",
    length=1, group="ram_workspace", access="rw")
label(0x0D68, "ws_0d68",
    description="ANFS workspace byte (role TBD).",
    length=1, group="ram_workspace", access="rw")
label(0x0D69, "ws_0d69",
    description="ANFS workspace byte (role TBD).",
    length=1, group="ram_workspace", access="rw")
label(0x0D6A, "ws_0d6a",
    description="ANFS workspace byte (role TBD).",
    length=1, group="ram_workspace", access="rw")
label(0x0D6B, "spool_buf_idx",
    description="Spool / printer buffer write index.",
    length=1, group="ram_workspace", access="rw")
label(0x0D6C, "fs_flags",
    description="Filing-system status flags.\n"
                "Bit 7: NFS is currently the selected FS; cleared "
                "when another FS takes over.",
    length=1, group="ram_workspace", access="rw")
label(0x0D6D, "tx_retry_count",
    description="Transmit retry count (default `&FF` = 255).\n"
                "Settable via OSWORD `&13` PB[1].",
    length=1, group="ram_workspace", access="rw")
label(0x0D6E, "rx_wait_timeout",
    description="Receive wait timeout (default `&28` = 40).\n"
                "Settable via OSWORD `&13` PB[2].",
    length=1, group="ram_workspace", access="rw")
label(0x0D6F, "peek_retry_count",
    description="Machine peek retry count (default `&0A` = 10).\n"
                "Settable via OSWORD `&13` PB[3].",
    length=1, group="ram_workspace", access="rw")
label(0x0D72, "bridge_status",
    description="Bridge station number (`&FF` = no bridge).\n"
                "Set by the bridge-discovery scout reply; checked "
                "before any cross-network operation.",
    length=1, group="ram_workspace", access="rw")

# Page &0D — workspace pointers
label(0x0DE6, "txcb_default_base")    # Base for indexed read of default TXCB values
label(0x0DF0, "rom_ws_pages",
    description="MOS per-ROM workspace page table (16 bytes, one "
                "per sideways-ROM slot). Each entry is the high "
                "byte of the page allocated to that ROM's "
                "absolute workspace.",
    length=16, group="ram_workspace", access="r")
label(0x0DFA, "fs_context_save")      # Saved FS context block (station, handles)
label(0x0DFE, "osword_ws_base")       # Base for OSWORD &14 workspace-to-PB copy
label(0x0DFF, "fs_server_base")       # Base for Y-indexed file server stn/net

# ============================================================
# Page &0E — FS context workspace (&0E00-&0EFF)
# ============================================================

label(0x0E00, "fs_server_stn")        # Current file server station number
label(0x0E01, "fs_server_net")        # Current file server network number
label(0x0E02, "fs_urd_handle")        # URD handle / station byte for handle 1
label(0x0E03, "fs_csd_handle")        # CSD handle / station byte for handle 2
label(0x0E04, "fs_lib_handle")        # Library handle / station byte for handle 3
label(0x0E05, "fs_boot_option")       # Boot option / display flag
label(0x0E06, "fs_messages_flag")     # Display control / messages flag
label(0x0E07, "fs_eof_flags")         # Pending operation marker / FS state byte
label(0x0E09, "fs_last_error")        # Last error code
label(0x0E0A, "fs_cmd_context")       # Command tail pointer lo / reply data source
label(0x0E0B, "fs_context_hi")        # Command tail pointer hi
label(0x0E16, "fs_work_16")           # OSWORD parameter size storage
label(0x0E2F, "fs_filename_buf_m1")   # Byte before filename buffer (trim indexing)
label(0x0E30, "fs_filename_buf")      # Parsed filename buffer
label(0x0E31, "fs_filename_buf_1")    # fs_filename_buf + 1
label(0x0E32, "fs_filename_buf_2")    # fs_filename_buf + 2
label(0x0E38, "fs_filename_backup")   # Filename backup for library path retry
label(0x0EF7, "fs_reply_data")        # File info reply data

# ============================================================
# Page &0F — TX buffer / FS command workspace (&0F00-&0FFF)
# ============================================================

# TX buffer fields (&0F00-&0F16)
label(0x0F00, "txcb_reply_port")      # TXCB reply port / command type
label(0x0F01, "fs_cmd_y_param")       # TXCB function code / Y parameter
label(0x0F02, "fs_cmd_urd")           # TXCB station byte / URD / port number
label(0x0F03, "fs_cmd_csd",
    description="TXCB port byte / CSD (current selected directory) "
                "handle. Pre-HAZEL counterpart of "
                "[`hazel_txcb_network`](address:C103).",
    length=1, group="ram_workspace", access="rw")
label(0x0F04, "fs_cmd_lib")           # TXCB lib handle / terminator byte
label(0x0F05, "fs_cmd_data",
    description="TX buffer data start / FS reply data. "
                "Pre-HAZEL counterpart of "
                "[`hazel_txcb_data`](address:C105).",
    length=1, group="ram_workspace", access="rw")
label(0x0F06, "fs_func_code")         # Function code / direction flag / offset
label(0x0F07, "fs_data_count")        # Data count / lock flag / position byte
label(0x0F08, "fs_reply_cmd")         # Transfer size lo / result byte
label(0x0F09, "fs_load_vector")       # Transfer size hi / indirect dispatch vector
label(0x0F0A, "fs_handle_check")      # Handle validity check / BCD minutes
label(0x0F0B, "fs_load_upper")        # Tube transfer check / BCD seconds
label(0x0F0C, "fs_addr_check")        # Tube transfer check (second byte)
label(0x0F0D, "fs_file_len")          # File length / address offset buffer (4 bytes)
label(0x0F0E, "fs_file_attrs")        # File access/attributes byte
label(0x0F10, "fs_file_len_3")        # File length hi / offset copy source
label(0x0F11, "fs_obj_type")          # Object type / reply handle
label(0x0F12, "fs_access_level")      # Access level / owner-public flag
label(0x0F13, "fs_reply_stn")         # Reply station / cycle number
label(0x0F14, "fs_len_clear")         # Cleared workspace byte
label(0x0F16, "fs_boot_data")         # OSBPUT display flag copy

# Examine response offsets
label(0x0F2F, "fs_exam_attr_char")    # File attribute char in examine response
label(0x0F30, "fs_exam_dir_flag")     # Directory contents flag in examine response

# OSBPUT send buffer (&0FDC-&0FE0)
label(0x0FDC, "fs_putb_buf")          # OSBPUT send buffer (function code)
label(0x0FDD, "fs_getb_buf")          # OSBPUT reply port / reply status
label(0x0FDE, "fs_handle_mask")       # Reply port for addressing
label(0x0FDF, "fs_error_flags")       # Data byte in send buffer
label(0x0FE0, "fcb_xfer_count_lo")    # FCB transfer count lo (per-slot table)
label(0x0FF0, "fcb_xfer_count_mid")   # FCB transfer count mid (per-slot table)

# ============================================================
# Page &10 — Channel/FCB table workspace (&1000-&10FF)
# ============================================================

# FCB parallel arrays with &10-byte stride (16 entries each)
label(0x1000, "fcb_count_lo")         # Byte count / position lo; shadow ws base
label(0x1010, "fcb_attr_or_count_mid")  # Channel attribute / byte count mid
label(0x1020, "fcb_station_or_count_hi")  # Station number / byte count hi
label(0x1030, "fcb_net_or_port")      # Network number / reply port
label(0x1040, "fcb_flags")            # FCB flags (handle assignment, state)
label(0x1050, "fcb_net_num")          # FCB network number (station matching)
label(0x1060, "chan_status")           # Channel status flags (per-slot)

# Scalar handle/flag variables
label(0x1070, "cur_dir_handle")       # Current directory handle
label(0x1071, "fs_lib_flags")         # FS/library flags byte
label(0x1072, "handle_1_fcb")         # Handle 1 FCB index
label(0x1073, "handle_2_fcb")         # Handle 2 FCB index
label(0x1074, "handle_3_fcb")         # Handle 3 FCB index

# FCB station/buffer parallel arrays (&10-byte stride)
label(0x1078, "fcb_stn_lo")           # FCB station lo byte
label(0x1088, "fcb_stn_hi")           # FCB station hi byte (network)
label(0x1098, "fcb_buf_offset")       # FCB buffer offset (negated)
label(0x10A8, "fcb_attr_ref")         # FCB attribute reference
label(0x10B8, "fcb_status")           # FCB status flags

# FCB processing temporaries
label(0x10C8, "cur_fcb_index")        # Current FCB slot index
label(0x10C9, "cur_chan_attr")         # Current channel attribute
label(0x10CA, "cur_attr_ref")         # Current attribute reference
label(0x10CB, "xfer_count_lo")        # Byte counter lo (wipe/transfer)
label(0x10CC, "fcb_buf_page")         # Buffer page address hi byte
label(0x10CD, "xfer_sentinel_1")      # Sentinel byte 1 (wipe/transfer)
label(0x10CE, "xfer_sentinel_2")      # Sentinel byte 2 (wipe/transfer)
label(0x10CF, "xfer_offset")          # Offset counter (wipe/transfer)
label(0x10D0, "xfer_pass_count")      # Pass counter (wipe/transfer)
label(0x10D1, "xfer_counter")         # 3-byte counter array
label(0x10D4, "work_stn_lo")          # Working station lo byte
label(0x10D5, "work_stn_hi")          # Working station hi byte (network)
label(0x10D6, "xfer_flag")            # Transfer flag
label(0x10D7, "osbput_saved_byte")    # Saved data byte for OSBPUT
label(0x10D8, "quote_mode")           # Quote mode tracking flag
label(0x10D9, "fcb_ctx_save")         # FCB context save buffer (13 bytes)

# Display buffer
label(0x10F3, "filename_buf",
    description="Filename display buffer (12 bytes). Used by "
                "directory listing and *Info to format filenames.",
    length=12, group="ram_workspace", access="rw")

# Other

# ============================================================
# Entry points for relocated code
# ============================================================

# Zero-page relocated code entry points

# Page 4 entry points

# Page 5 entry points

# Page 6 entry points


# ============================================================
# Code label renames (Phase 3)
label(0x959A, "print_fs_ps_help")
label(0x95CD, "print_field_tail_s")
label(0x95E9, "dispatch_fs_ps_with_arg")
label(0x965F, "print_ps_address")
label(0x9670, "print_fs_address")
label(0x967F, "print_cmos_decimal_nl")
label(0x9689, "print_cmos_done")
# ============================================================

# Data and shared-tail label renames (Phase 3b)
label(0x8001, "rom_header_byte1")
label(0x8002, "rom_header_byte2")
label(0x806C, "econet_restore")
label(0x809A, "adlc_init_done")
label(0x83D4, "loop_count_rxcb_slot")
expr_label(0x83ED, "imm_op_dispatch_lo-&81")  # = &847E - &81
label(0x83FF, "return_from_discard_reset")
label(0x84AE, "jmp_send_data_rx_ack")
label(0x84BE, "set_rx_buf_len_hi")
expr_label(0x84B8, "tx_done_dispatch_lo-&83")  # = &853B - &83
expr_label(0x85FD, "tx_ctrl_dispatch_lo-&81")  # = &867E - &81
label(0x853A, "return_from_advance_buf")
label(0x85F8, "reload_inactive_mask")
label(0x87C4, "tx_check_tdra_ready")
label(0x87EF, "check_tdra_status")
label(0x8924, "check_tx_in_progress")
label(0x8A85, "clear_workspace_byte")
label(0x8A8A, "restore_rom_slot")
label(0x8A9A, "set_adlc_absent")
label(0x8AA1, "check_adlc_flag")
label(0x8AA9, "dispatch_svc_with_state")
label(0x8AD0, "dispatch_svc_index")
label(0x8AE1, "restore_svc_state")
label(0x8AE7, "restore_romsel_rts")
label(0x8B04, "loop_scan_key_range")
label(0x8B11, "clear_svc_and_ws")
label(0x8B22, "return_from_save_text_ptr")
label(0x8B2F, "loop_sum_rom_bytes")
label(0x8B60, "done_rom_checksum")
label(0x8B65, "loop_copy_fs_ctx")
label(0x8B78, "loop_set_vectors")
label(0x8BA4, "loop_copy_ws_page")
label(0x8BD2, "print_table_newline")
label(0x8BD8, "loop_next_entry")
label(0x8BE0, "print_indent")
label(0x8BF4, "loop_pad_spaces")
label(0x8C06, "loop_print_syntax")
label(0x8C16, "print_syntax_char")
label(0x8C1C, "done_entry_newline")
label(0x8C25, "done_print_table")
label(0x8C3A, "loop_indent_spaces")
label(0x8C41, "return_from_help_wrap")
label(0x8C64, "svc_return_unclaimed")
label(0x8C67, "check_help_topic")
label(0x8C71, "match_help_topic")
label(0x8C74, "loop_dispatch_help")
label(0x8C8C, "skip_if_no_match")
label(0x8C96, "version_string_cr")
label(0x8CC6, "return_from_setup_ws_ptr")
label(0x8CD7, "write_key_state")
label(0x8CDD, "select_net_fs")
label(0x8D04, "issue_svc_osbyte")
label(0x8D28, "loop_match_credits")
label(0x8D33, "done_credits_check")
label(0x8D39, "loop_emit_credits")
label(0x8D44, "return_from_credits_check")
label(0x8D45, "credits_keyword_start")
# ps_template_base is the indexed-addressing anchor used by copy_ps_data
# (LDA ps_template_base,X with X=&F8..&FF, reaching ps_template_data at
# &8E9F). It deliberately lands inside a JSR instruction's operand byte
# rather than at a free-standing address -- see docs/analysis/
# authors-easter-egg.md.
label(0x8DA7, "ps_template_base")
label(0x8DC0, "skip_no_fs_addr")
label(0x8DC7, "loop_copy_logon_cmd")
label(0x8DD8, "scan_pass_prompt")
label(0x8DDA, "loop_scan_colon")
label(0x8DEB, "read_pw_char")
label(0x8DFD, "loop_erase_pw")
label(0x8E04, "check_pw_special")
label(0x8E13, "send_pass_to_fs")
label(0x8E70, "dispatch_rts")
label(0x8ECD, "jmp_osbyte")
label(0x8EEF, "return_from_raise_y_to_c8")
label(0x8EF8, "done_cap_ws_count")
label(0x8F56, "loop_zero_workspace")
label(0x8F84, "loop_copy_init_data")
label(0x8FA9, "loop_alloc_handles")

# Split the 3 workspace init bytes into individual entries.
# ws_init_data label overlaps the JMP operand high byte at &8F48;
# the actual data bytes at &8F49-&8F4B are read via LDA ws_init_data,X
# with X=3..1 (X=0 never read due to BNE loop exit). The store base
# is fs_flags (&0D6C).
label(0x9066, "loop_restore_ctx")
label(0x9083, "loop_checksum_byte")
label(0x908D, "loop_copy_to_ws")
label(0x9090, "store_ws_byte")
label(0x909D, "return_from_fs_shutdown")
label(0x90A6, "loop_sum_ws")
label(0x90F4, "done_print_newline")
data_banner(0x90F8, "cmd_syntax_strings",
    title="*HELP / *SYNTAX argument strings (8 messages)",
    description="""\
Eight zero-terminated argument-syntax strings used by the *HELP
text builder. Each string describes the argument shape of a
particular command group; their offsets within this table are
stored in [`cmd_syntax_table`](address:91ED), keyed by command
index. Read by [`do_print_no_spool`](address:921D) when no command
argument was supplied.""")
# cmd_syntax_strings (above, banner only) and syn_opt_dir (below, beebasm label)
# are aliases at
# &90F8: the table's start coincides with the first entry's body.
label(0x90F8, "syn_opt_dir")     # "(<dir>)"
label(0x9100, "syn_iam")         # "(<stn. id.>) <user id.>..."
label(0x912D, "syn_object")      # "<object>"
label(0x9159, "syn_dir")         # "<dir>"
label(0x9170, "syn_password")    # "(:<CR>) <password>..."
label(0x91AA, "syn_access")      # "<object> (L)(W)(R)..."
label(0x91C6, "syn_rename")      # "<filename> <new filename>"
label(0x91E0, "syn_opt_stn")     # "(<stn. id.>)"
data_banner(0x91ED, "cmd_syntax_table",
    title="Argument-syntax offset table (12 entries)",
    description="""\
Twelve byte offsets indexing into
[`syn_opt_dir`](address:90F8). Each entry is computed as
`<syn_X> - syn_opt_dir - 1` so the print loop can `INY`
before `LDA` and still land on the first byte of the chosen
string. The byte at &91F9 immediately after the table is the
entry point of [`print_no_spool`](address:91F9).""")
# 12 entries (idx 0-11).
for i in range(12):
    byte(0x91ED + i)
# Symbolic expressions: offset = string_start - syn_opt_dir - 1
# (the print loop does INY before LDA, so offset points to byte before string)
expr(0x91ED, "syn_iam - syn_opt_dir - 2")
expr(0x91EF, "syn_iam - syn_opt_dir - 1")
expr(0x91F0, "syn_object - syn_opt_dir - 1")
expr(0x91F6, "syn_access - syn_opt_dir - 1")
expr(0x91F8, "syn_opt_stn - syn_opt_dir - 1")
label(0x9203, "save_regs_for_print_no_spool")  # shared body of print_*_no_spool
label(0x921D, "do_print_no_spool")              # PLP/PLA/PHA + OSASCI/OSWRCH branch
label(0x9227, "print_via_oswrch")               # OSWRCH branch from BVC at &9220
label(0x922A, "restore_spool_and_return")       # final OSBYTE 199 + register pull/RTS
label(0x9769, "always_set_v_byte")              # &FF byte used as `BIT $abs` to set V
label(0x9247, "add_ascii_base")
label(0x9269, "loop_next_char")
label(0x926F, "load_char")
label(0x9287, "resume_caller")
label(0x92BF, "next_hex_char")
label(0x92CA, "check_digit_range")
label(0x92DA, "skip_if_not_hex")
label(0x92DC, "extract_digit_value")
label(0x92F0, "next_dec_char")
label(0x931C, "done_parse_num")
label(0x9325, "validate_station")
label(0x933B, "return_parsed")
label(0x933D, "handle_dot_sep")
label(0x9353, "error_overflow")
label(0x936B, "error_bad_number")
label(0x9377, "error_bad_param")
label(0x9386, "error_bad_net_num")
label(0x93A8, "return_from_digit_test")
label(0x93A9, "not_a_digit")
label(0x93B9, "begin_prot_encode")
label(0x93BD, "loop_encode_prot")
label(0x93C5, "skip_clear_prot")
subroutine(0x93C8, "prot_bit_encode_table",
    title="Bit-permutation table for protection / access encoding",
    description="""\
11-byte lookup table used by [`get_prot_bits`](address:93B5) and
[`get_access_bits`](address:93AB) to map source bits (the raw 5-bit
or 6-bit access mask read from the directory entry) into the FS
protocol's 8-bit protection-flag layout. The encoder loop at
[`begin_prot_encode`](address:93B9) shifts each source bit out via
`LSR`; whenever the bit is 1 it ORs the corresponding entry into
the result, then advances `X`.

Two callers partition the table:

- [`get_prot_bits`](address:93B5) enters at index 0 with 5 source
  bits (raw protection mask, `AND #&1F`).
- [`get_access_bits`](address:93AB) enters at index 5 with 6 source
  bits (directory access byte, `AND #&3F`).

| idx | caller            | src bit | mask  | output bits |
| --- | ----------------- | ------- | ----- | ----------- |
|   0 | `get_prot_bits`   |       0 | `&50` | 6, 4        |
|   1 | `get_prot_bits`   |       1 | `&20` | 5           |
|   2 | `get_prot_bits`   |       2 | `&05` | 2, 0        |
|   3 | `get_prot_bits`   |       3 | `&02` | 1           |
|   4 | `get_prot_bits`   |       4 | `&88` | 7, 3        |
|   5 | `get_access_bits` |       0 | `&04` | 2           |
|   6 | `get_access_bits` |       1 | `&08` | 3           |
|   7 | `get_access_bits` |       2 | `&80` | 7           |
|   8 | `get_access_bits` |       3 | `&10` | 4           |
|   9 | `get_access_bits` |       4 | `&01` | 0           |
|  10 | `get_access_bits` |       5 | `&02` | 1           |""")
for i in range(11):
    byte(0x93C8 + i)
comment(0x93C8, "prot src bit 0 -> out bits 6,4", inline=True)
comment(0x93C9, "prot src bit 1 -> out bit 5", inline=True)
comment(0x93CA, "prot src bit 2 -> out bits 2,0", inline=True)
comment(0x93CB, "prot src bit 3 -> out bit 1", inline=True)
comment(0x93CC, "prot src bit 4 -> out bits 7,3", inline=True)
comment(0x93CD, "access src bit 0 -> out bit 2", inline=True)
comment(0x93CE, "access src bit 1 -> out bit 3", inline=True)
comment(0x93CF, "access src bit 2 -> out bit 7", inline=True)
comment(0x93D0, "access src bit 3 -> out bit 4", inline=True)
comment(0x93D1, "access src bit 4 -> out bit 0", inline=True)
comment(0x93D2, "access src bit 5 -> out bit 1", inline=True)
label(0x93E8, "loop_cmp_handle")
label(0x93F1, "return_from_cmp_handle")
label(0x93F2, "fscv_7_read_handles")
label(0x9464, "loop_scan_flag")
label(0x946D, "loop_copy_name")
label(0x9479, "append_space")
label(0x9482, "return_from_copy_cmd_name")
label(0x9489, "loop_skip_spaces")
label(0x9492, "check_open_quote")
label(0x949D, "loop_copy_arg_char")
label(0x94AB, "store_arg_char")
label(0x94D3, "loop_copy_rename")
label(0x94DA, "error_bad_rename")
label(0x94E6, "store_rename_char")
label(0x94F3, "skip_rename_spaces")
label(0x9523, "setup_fs_root")
label(0x9525, "loop_copy_fs_num")
label(0x953A, "check_fs_dot")
label(0x9541, "parse_fs_dot_dir")
label(0x9571, "dir_found_send")
label(0x9597, "dir_pass_simple")
label(0x974E, "loop_init_txcb")
label(0x975E, "skip_txcb_dest")
data_banner(0x9763, "txcb_init_template",
    title="TXCB initialisation template (12 bytes)",
    description="""\
Copied byte-for-byte by [`init_txcb`](address:974B) into the
TXCB workspace at `&00C0`. The Nth template byte (at `&9763 + N`)
ends up at TXCB offset N (`&00C0 + N`).

Bytes 2 and 3 (placeholders `&00 &00` here) are overwritten
during the copy: while writing TXCB[0] and TXCB[1] the loop also
copies `hazel_fs_station[0..1]` (HAZEL `&C000..&C001`) into
`txcb_dest` (`&00C2..&00C3`), so the runtime destination station
and network come from the live FS state rather than this
template.

The `&FF` byte at offset 6 ([`always_set_v_byte`](address:9769))
serves double duty: it is part of this template AND a `BIT $abs`
target used by 22 callers to set V and N flags without clobbering
`A`.""")
for i in range(12):
    byte(0x9763 + i)
label(0x976A, "bit_test_ff")
label(0x9791, "txcb_copy_carry_clr")
label(0x9792, "txcb_copy_carry_set")
label(0x9798, "loop_copy_vset_stn")
label(0x97B0, "use_lib_station")
label(0x97B6, "done_vset_station")
label(0x97D5, "loop_next_reply")
label(0x97DF, "process_reply_code")
label(0x97E1, "return_from_recv_reply")
label(0x97E2, "handle_disconnect")
label(0x97EB, "store_reply_status")
label(0x97F8, "check_data_loss")
label(0x9800, "loop_scan_channels")
label(0x9831, "build_error_block")
label(0x983B, "setup_error_copy")
label(0x983D, "loop_copy_error")
label(0x9850, "lang_1_remote_boot")
label(0x9856, "done_commit_state")
label(0x9859, "init_remote_session")
label(0x987E, "lang_3_exec_0100")
label(0x989F, "lang_4_validated")
label(0x98AF, "lang_0_insert_key")
label(0x98CF, "init_poll_counters")
label(0x98D5, "loop_poll_tx")
label(0x98F6, "done_poll_tx")
label(0x9908, "return_from_cond_save_err")
label(0x9909, "build_no_reply_error")
label(0x9919, "loop_copy_no_reply_msg")
label(0x9925, "done_no_reply_msg")
label(0x9938, "skip_if_not_a")
label(0x9940, "mask_error_class")
label(0x9957, "loop_copy_station_msg")
label(0x9963, "done_station_msg")
label(0x9975, "suffix_not_listening")
label(0x9977, "load_suffix_offset")
label(0x997B, "loop_copy_suffix")
label(0x9987, "done_suffix")
label(0x9989, "build_simple_error")
label(0x9998, "loop_copy_error_msg")
label(0x999E, "check_msg_terminator")
label(0x99B3, "loop_copy_bad_prefix")
label(0x99CC, "write_error_num_and_str")
label(0x99D6, "loop_copy_inline_str")
label(0x99E9, "trigger_brk")
label(0x99EC, "handle_net_error")
label(0x9A10, "close_spool_exec")
label(0x9A19, "done_close_files")
label(0x9A21, "loop_copy_channel_msg")
label(0x9A2D, "append_error_number")
label(0x9A54, "append_station_num")
label(0x9A81, "loop_count_digit")
label(0x9A91, "store_digit")
label(0x9A99, "return_from_store_digit")
data_banner(0x9A9A, "net_error_lookup_data",
    title="Net-error class -> error_msg_table offset (12 bytes)",
    description="""\
Maps Econet network-error classes to byte offsets into
[`error_msg_table`](address:9AA6).

- Indices 0-7 are keyed by error class (the reply byte AND `7`).
- Index 8 is used by `build_no_reply_error` to locate the
  '`No reply from station`' message head.
- Indices 9-11 point to the suffix strings appended after the
  station address in compound errors ('` not listening`',
  '` on channel`', '` not present`').

Each byte is computed as `<message-label> - error_msg_table` so the
table reflows automatically if a message string is edited.""")
# Each entry is computed as `<msg-label> - error_msg_table` so the
# table reflows automatically if a message string is edited. Entry 0
# is the table base itself, so its byte is left as a literal 0
# (`error_msg_table - error_msg_table` would assemble to the same).
for i in range(12):
    byte(0x9A9A + i)
expr(0x9A9B, "msg_net_error - error_msg_table")      # class 1: &A1 "Net error"
expr(0x9A9C, "msg_station - error_msg_table")        # class 2: &A2 "Station ..."
expr(0x9A9D, "msg_no_clock - error_msg_table")       # class 3: &A3 "No clock"
expr(0x9A9E, "msg_escape - error_msg_table")         # class 4: &11 "Escape"
expr(0x9A9F, "msg_escape - error_msg_table")         # class 5: &11 "Escape" (dup)
expr(0x9AA0, "msg_escape - error_msg_table")         # class 6: &11 "Escape" (dup)
expr(0x9AA1, "msg_bad_option - error_msg_table")     # class 7: &CB "Bad option"
expr(0x9AA2, "msg_no_reply - error_msg_table")       # index 8: &A5 "No reply from station"
expr(0x9AA3, "msg_not_listening - error_msg_table")  # index 9: " not listening"
expr(0x9AA4, "msg_on_channel - error_msg_table")     # index 10: " on channel"
expr(0x9AA5, "msg_not_present - error_msg_table")    # index 11: " not present"
data_banner(0x9AA6, "error_msg_table",
    title="Net-error message strings",
    description="""\
Body of error-text fragments referenced by
[`net_error_lookup_data`](address:9A9A). Two layouts coexist:

1. **Error entries** (offsets 0..&3F) — one byte holding the BRK
   error code, immediately followed by the null-terminated
   message string:

   ```
   <err_code> <message-bytes...> &00
   ```

2. **Suffix entries** (offsets &56, &65, &71) — bare
   null-terminated strings appended to a built-up error message;
   no leading error-code byte.

Per-byte inline comments below name each error code and message;
the bytes from this table are read by `build_simple_error` and
`build_no_reply_error` when classifying a network reply.""")
# Symbolic offsets into error_msg_table
label(0x9B33, "set_timeout")
label(0x9B3C, "start_tx_attempt")
label(0x9B52, "loop_retry_tx")
label(0x9B58, "loop_tx_delay")
label(0x9B60, "try_alternate_phase")
label(0x9B6B, "tx_send_error")
label(0x9B6F, "tx_success")
data_banner(0x9B75, "pass_txbuf_init_table",
    title="Pass-through TX buffer template (12 bytes)",
    description="""\
Overlaid onto the TX control block by
[`setup_pass_txbuf`](address:9B89) for pass-through operations.
The 12 bytes follow the Econet TXCB layout used elsewhere in this
ROM (compare [`bridge_rxcb_init_data`](address:ABDD)):

| Offset | Field |
|---|---|
| 0     | TX control byte (`&88` = immediate TX)        |
| 1     | TX port (`&00` = immediate op)                |
| 2-3   | dest station / network (`&FD` skip = preserve)|
| 4-5   | buffer start address (lo, hi)                  |
| 6-7   | extended-address fill (`&FF&FF`)               |
| 8-9   | buffer end address (lo, hi)                    |
| 10-11 | extended-address fill (`&FF&FF`)               |

The buffer spans [`&0D3A`..`&0D3E`](address:0D3D) -- the bytes
immediately preceding [`rx_src_stn`](address:0D3D) through
[`rx_src_net`](address:0D3E) -- so the same RX-area bytes are
echoed back as the TX payload (hence "pass-through"). The
`&FF&FF` filler bytes at offsets 6-7 and 10-11 are a software
convention left over from a 4-byte-address format the BBC
Econet driver anticipated; for main-RAM buffers they're left
as `&FF&FF`. Original TX buffer values are pushed on the stack
and restored after transmission.""")
for i in range(12):
    byte(0x9B75 + i)
label(0x9B8B, "loop_copy_template")
label(0x9B98, "skip_template_byte")
label(0x9BA5, "start_pass_tx")
label(0x9BB1, "done_pass_retries")
label(0x9BC6, "loop_poll_pass_tx")
label(0x9BCB, "restore_retry_state")
label(0x9BD8, "loop_pass_tx_delay")
label(0x9BE0, "pass_tx_success")
label(0x9BE5, "loop_restore_txbuf")
label(0x9BEF, "skip_restore_byte")
label(0x9BF7, "loop_copy_text_ptr")
label(0x9C08, "loop_gsread_char")
label(0x9C13, "terminate_buf")
label(0x9C39, "copy_arg_and_enum")
label(0x9C56, "copy_ws_then_fsopts")
label(0x9C5C, "setup_txcb_addrs")
label(0x9C5E, "loop_copy_addrs")
label(0x9C79, "loop_copy_offsets")
label(0x9C8E, "loop_swap_and_send")
label(0x9C90, "loop_copy_start_end")
label(0x9CA4, "loop_verify_addrs")
label(0x9CAF, "return_from_txcb_swap")
label(0x9CB0, "check_display_type")
label(0x9CB5, "setup_dir_display")
label(0x9CBA, "loop_compute_diffs")
label(0x9CD8, "loop_copy_fs_options")
label(0x9CF9, "send_info_request")
label(0x9D06, "setup_txcb_transfer")
label(0x9D0C, "recv_reply")
label(0x9D0F, "store_result")
label(0x9D1C, "loop_copy_file_info")
label(0x9D1F, "store_prot_byte")
label(0x9D2D, "loop_print_filename")
label(0x9D51, "loop_print_hex_byte")
label(0x9D61, "loop_copy_fsopts_byte")
label(0x9D70, "return_from_advance_y")
label(0x9D74, "loop_copy_ws_byte")
label(0x9D83, "discard_handle_match")
label(0x9D8D, "init_transfer_addrs")
label(0x9D98, "loop_copy_addr_offset")
label(0x9DAA, "loop_check_vs_limit")
label(0x9DB6, "clamp_end_to_limit")
label(0x9DB8, "loop_copy_limit")
label(0x9DBF, "set_port_and_ctrl")
label(0x9DDC, "dispatch_osword_op")
label(0x9DE8, "dispatch_ops_1_to_6")
label(0x9E00, "loop_copy_fsopts_4")
label(0x9E0D, "setup_save_access")
label(0x9E17, "loop_copy_fsopts_8")
label(0x9E22, "send_save_or_access")
label(0x9E29, "send_delete_request")
label(0x9E2E, "send_request_vset")
label(0x9E34, "skip_if_error")
label(0x9E39, "setup_write_access")
label(0x9E43, "read_cat_info")
label(0x9E65, "loop_copy_cat_info")
label(0x9E72, "loop_copy_ext_info")
label(0x9E7E, "return_with_handle")
label(0x9E7F, "done_osword_op")
label(0x9E89, "loop_copy_cmdline_char")
label(0x9E95, "pad_with_spaces")
label(0x9EA0, "loop_copy_buf_char")
label(0x9EA2, "copy_from_buf_entry")
label(0x9EBD, "validate_chan_close")
label(0x9EC2, "error_invalid_chan")
label(0x9EC5, "check_chan_range")
label(0x9ED5, "loop_copy_fcb_fields")
label(0x9EE5, "dispatch_osfind_op")
label(0x9EF0, "osfind_with_channel")
label(0x9F22, "loop_copy_zp_to_buf")
label(0x9F38, "done_return_flag")
label(0x9F3B, "osargs_read_op")
label(0x9F4A, "loop_copy_reply_to_zp")
label(0x9F57, "osargs_ptr_dispatch")
label(0x9F79, "osargs_write_ptr")
label(0x9F80, "loop_copy_ptr_to_buf")
label(0x9FB1, "close_all_fcbs")
label(0x9FC2, "osfind_close_or_open")
label(0x9FCD, "done_file_open")
label(0x9FCF, "clear_result")
label(0x9FD1, "shift_and_finalise")
label(0x9FD4, "alloc_fcb_for_open")
label(0xA00B, "loop_shift_filename")
label(0xA04C, "check_open_mode")
label(0xA05E, "alloc_fcb_with_flags")
label(0xA062, "store_fcb_flags")
label(0xA068, "done_osfind")
label(0xA06B, "close_all_channels")
label(0xA084, "close_specific_chan")
label(0xA08A, "send_close_request")
label(0xA09C, "done_close")
label(0xA09F, "clear_single_fcb")
label(0xA0A9, "fscv_0_opt_entry")
label(0xA0B3, "osargs_dispatch")
label(0xA0B6, "store_display_flag")
label(0xA0BB, "error_osargs")
label(0xA0C0, "send_osargs_request")
label(0xA10B, "fscv_1_eof")
label(0xA126, "mark_not_found")
label(0xA128, "restore_and_return")
label(0xA136, "loop_adjust_byte")
label(0xA142, "subtract_ws_byte")
label(0xA145, "store_adjusted_byte")
label(0xA15F, "skip_if_out_of_range")
label(0xA162, "valid_osgbpb_op")
label(0xA16D, "load_chan_handle")
label(0xA1AC, "set_write_active")
label(0xA1AF, "setup_gbpb_request")
label(0xA205, "loop_copy_opts_to_buf")
label(0xA210, "skip_struct_hole")
label(0xA219, "store_direction_flag")
label(0xA227, "store_port_and_send")
label(0xA244, "loop_setup_addr_bytes")
label(0xA25B, "loop_copy_offset")
label(0xA26F, "send_with_swap")
label(0xA272, "recv_and_update")
label(0xA28A, "send_osbput_data")
label(0xA29F, "write_block_entry")
label(0xA2AD, "store_station_result")
label(0xA2AF, "loop_copy_opts_to_ws")
label(0xA2C1, "handle_cat_update")
label(0xA2F5, "loop_copy_to_host")
label(0xA302, "tube_write_setup")
label(0xA30F, "set_tube_addr")
label(0xA314, "loop_write_to_tube")
label(0xA31D, "loop_tube_delay")
label(0xA32C, "update_cat_position")
label(0xA368, "clear_buf_after_write")
label(0xA36A, "loop_clear_buf")
label(0xA384, "loop_check_remaining")
label(0xA38D, "done_write_block")
label(0xA3B8, "print_current_fs")
label(0xA3DA, "store_station_lo")
label(0xA3E1, "skip_if_no_station")
label(0xA3FF, "net_1_read_handle")
label(0xA405, "net_2_read_entry")
label(0xA410, "return_zero_uninit")
label(0xA412, "store_pb_result")
label(0xA415, "net_3_close_handle")
label(0xA424, "mark_ws_uninit")
label(0xA44E, "dispatch_fs_cmd")
label(0xA45D, "restart_table_scan")
label(0xA465, "loop_match_char")
label(0xA474, "skip_entry_chars")
label(0xA480, "loop_skip_to_next")
label(0xA485, "check_separator")
label(0xA48B, "loop_check_sep_table")
label(0xA497, "sep_table_data")
label(0xA4A2, "loop_skip_trail_spaces")
label(0xA4A8, "skip_dot_and_spaces")
label(0xA4AC, "check_cmd_flags")
label(0xA4BD, "clear_v_flag")
label(0xA4BE, "clear_c_flag")
label(0xA4BF, "return_with_result")
label(0xA4C3, "loop_scan_past_word")
label(0xA4C4, "check_char_type")
label(0xA4D2, "skip_sep_spaces")
label(0xA4D9, "set_c_and_return")
label(0xA4E4, "fscv_2_star_run")
label(0xA4FF, "open_file_for_run")
label(0xA517, "loop_check_handles")
label(0xA51F, "alloc_run_fcb")
label(0xA53B, "done_run_dispatch")
label(0xA53E, "try_library_path")
label(0xA552, "loop_find_name_end")
label(0xA55A, "loop_shift_name_right")
label(0xA565, "loop_copy_lib_prefix")
label(0xA576, "retry_with_library")
label(0xA578, "restore_filename")
label(0xA57A, "loop_restore_name")
label(0xA58F, "library_tried")
label(0xA5AE, "check_exec_addr")
label(0xA5B0, "loop_check_exec_bytes")
label(0xA5C3, "alloc_run_channel")
label(0xA5D7, "library_dir_prefix")
label(0xA5E8, "loop_read_gs_string")
label(0xA5EE, "loop_skip_trailing")
label(0xA633, "dispatch_via_vector")
label(0xA63E, "fsreply_5_set_lib")
label(0xA647, "loop_search_stn_bit2")
label(0xA65D, "done_search_bit2")
label(0xA66B, "set_flags_bit2")
label(0xA672, "loop_search_stn_bit3")
label(0xA688, "done_search_bit3")
label(0xA696, "set_flags_bit3")
label(0xA6A9, "loop_search_stn_boot")
label(0xA6BF, "done_search_boot")
label(0xA6CD, "set_flags_boot")
label(0xA6CF, "store_stn_flags_restore")
label(0xA6D2, "jmp_restore_fs_ctx")
label(0xA6D5, "fsreply_1_boot")
label(0xA6E5, "fsreply_2_copy_handles")
label(0xA726, "check_auto_boot_flag")

# Split the 4-byte boot OSCLI address table into individual bytes.
# Low bytes of boot command string addresses in page &A3.
# Indexed by boot option (1-3); entry 0 is a don't-care (BEQ skips).
label(0xA7C9, "cmd_table_nfs_iam")
label(0xBEEB, "loop_copy_osword_data")
label(0xA870, "return_from_osword_setup")


# Mark OSWORD dispatch table entries as symbolic address pairs.


label(0xA874, "osword_0e_handler")
label(0xA890, "return_from_osword_0e")
label(0xA891, "save_txcb_and_convert")
label(0xA8DE, "loop_copy_bcd_to_pb")
label(0xA908, "loop_bcd_add")
label(0xA90E, "done_bcd_convert")
label(0xA910, "osword_10_handler")
label(0xA919, "setup_ws_rx_ptrs")
label(0xA93D, "loop_find_rx_slot")
label(0xA951, "store_rx_slot_found")
label(0xA956, "use_specified_slot")
label(0xA96C, "loop_copy_slot_data")
label(0xA96D, "copy_pb_and_mark")
label(0xA97A, "increment_and_retry")
label(0xA97F, "store_rx_result")
label(0xA981, "osword_11_done")
label(0xA985, "osword_12_handler")
label(0xA99A, "osword_13_dispatch")
label(0xA9A7, "return_from_osword_13")

# OSWORD &13 PHA/PHA/RTS dispatch table (18 entries, sub-codes 0-&11).
# Lo half at &A9A8, hi half at &A9BA. Each entry stores `target-1` so
# RTS lands on the handler.

# Entry points for handlers in the &A663-&A6EA region (currently data).
entry(0xAA72)   # Sub 12
entry(0xAA75)   # Sub 13

# Symbolic OSWORD &13 dispatch tables.
data_banner(0xA9A8, "osword_13_dispatch_lo",
    title="OSWORD &13 dispatch low-byte table (18 entries)",
    description="""\
Read by [`osword_13_dispatch`](address:A99A) as `LDA &A9A8,X`. Paired
with the high-byte half at [`osword_13_dispatch_hi`](address:A9BA).
Sub-codes 0..&11 cover read/set station, read/write workspace pair,
read/write protection, read/set handles, read RX flag/port/error,
read context, read/write CSD, read free buffers, read/write context
3, and bridge query.""")
for addr in range(0xA9A8, 0xA9BA):
    byte(addr)

data_banner(0xA9BA, "osword_13_dispatch_hi",
    title="OSWORD &13 dispatch high-byte table (18 entries)",
    description="""\
Read by [`osword_13_dispatch`](address:A99A) as `LDA &A9BA,X`. The
dispatcher pushes the hi byte first then the lo, so RTS lands on
`target` (the table stores `target-1`).""")
for addr in range(0xA9BA, 0xA9CC):
    byte(addr)

_netv_dispatch_entries = [
    (0x00, "dispatch_rts",          "no-op (RTS only)"),
    (0x01, "netv_print_data",       "NETV reason 1: print data"),
    (0x02, "netv_print_data",       "NETV reason 2: print data (alias)"),
    (0x03, "netv_print_data",       "NETV reason 3: print data (alias)"),
    (0x04, "osword_4_handler",      "NETV reason 4: OSWORD &04"),
    (0x05, "netv_spool_check",      "NETV reason 5: spool check"),
    (0x06, "dispatch_rts",          "no-op (RTS only)"),
    (0x07, "netv_claim_release",    "NETV reason 7: claim/release"),
    (0x08, "osword_8_handler",      "NETV reason 8: OSWORD &08"),
]

data_banner(0xAD20, "netv_dispatch_lo",
    title="NETV reason-code dispatch low-byte table (9 entries)",
    description="""\
Read by [`push_osword_handler_addr`](address:AD15) as
`LDA &AD20,X`. Paired with the high-byte half at
[`netv_dispatch_hi`](address:AD29). The wrapper at
[`netv_handler`](address:ACFC) reads the original A from the MOS
stack frame (`&0103,X` after TSX) and gates 9..&FF away to
[`return_6`](address:AD0E) before dispatching reasons 0..8.""")
for addr in range(0xAD20, 0xAD29):
    byte(addr)

data_banner(0xAD29, "netv_dispatch_hi",
    title="NETV reason-code dispatch high-byte table (9 entries)",
    description="""\
Read by [`push_osword_handler_addr`](address:AD15) as
`LDA &AD29,X`. The dispatcher pushes the hi byte first then the
lo, so RTS lands on `target` (the table stores `target-1`).""")
for addr in range(0xAD29, 0xAD32):
    byte(addr)

for idx, name, role in _netv_dispatch_entries:
    expr(0xAD20 + idx, "<(%s-1)" % name)
    expr(0xAD29 + idx, ">(%s-1)" % name)
    comment(0xAD20 + idx, "reason &%02X: %s (%s)" % (idx, name, role), inline=True)
    comment(0xAD29 + idx, "reason &%02X: %s" % (idx, name), inline=True)

_osword_13_entries = [
    (0x00, "osword_13_read_station",   "read FS station"),
    (0x01, "osword_13_set_station",    "set FS station"),
    (0x02, "osword_13_read_ws_pair",   "read workspace pair"),
    (0x03, "osword_13_write_ws_pair",  "write workspace pair"),
    (0x04, "osword_13_read_prot",      "read protection mask"),
    (0x05, "osword_13_write_prot",     "write protection mask"),
    (0x06, "osword_13_read_handles",   "read transfer handles"),
    (0x07, "osword_13_set_handles",    "set transfer handles"),
    (0x08, "osword_13_read_rx_flag",   "read RX flag"),
    (0x09, "osword_13_read_rx_port",   "read RX port"),
    (0x0A, "osword_13_read_error",     "read last error"),
    (0x0B, "osword_13_read_context",   "read context"),
    (0x0C, "osword_13_read_csd",       "read CSD"),
    (0x0D, "osword_13_write_csd",      "write CSD"),
    (0x0E, "osword_13_read_free_bufs", "read free buffers"),
    (0x0F, "osword_13_read_ctx_3",     "read context byte 3"),
    (0x10, "osword_13_write_ctx_3",    "write context byte 3"),
    (0x11, "osword_13_bridge_query",   "bridge query"),
]
for idx, name, role in _osword_13_entries:
    expr(0xA9A8 + idx, "<(%s-1)" % name)
    expr(0xA9BA + idx, ">(%s-1)" % name)
    comment(0xA9A8 + idx, "sub &%02X: %s (%s)" % (idx, name, role), inline=True)
    comment(0xA9BA + idx, "sub &%02X: %s" % (idx, name), inline=True)

label(0xA9CF, "read_station_bytes")
label(0xA9D1, "loop_copy_station")
label(0xA9E4, "loop_store_station")
label(0xA9FB, "scan_fcb_entry")
label(0xAA2A, "check_handle_2")
label(0xAA44, "check_handle_3")
label(0xAA5E, "store_updated_status")
label(0xAA62, "next_fcb_entry")
label(0xAA76, "setup_csd_copy")
label(0xAA88, "copy_ws_byte_to_pb")
label(0xAAB1, "return_from_write_ws_pair")
label(0xAAC7, "loop_copy_handles")
label(0xAAD3, "start_set_handles")
label(0xAAD5, "validate_handle")
label(0xAAE5, "handle_invalid")
label(0xAAEC, "check_handle_alloc")
label(0xAB12, "next_handle_slot")
label(0xAB19, "assign_handle_2")
label(0xAB30, "assign_handle_3")
label(0xAB47, "loop_scan_fcb_flags")
label(0xAB59, "no_flag_match")
label(0xAB5A, "clear_flag_bits")
label(0xAB62, "next_flag_entry")
label(0xAB82, "store_a_to_pb_1")
label(0xABBB, "bridge_found")
label(0xABC4, "compare_bridge_status")
label(0xABCB, "use_default_station")
label(0xABCE, "store_bridge_station")
label(0xABD0, "return_from_bridge_query")
label(0xABD1, "bridge_txcb_init_table")
label(0xABDD, "bridge_rxcb_init_data")
for i in range(4):
    byte(0xABD1 + i)
# bytes 4-9 are "BRIDGE" — leave as equs
label(0xABF9, "loop_copy_bridge_init")
label(0xAC0D, "loop_wait_ws_status")
label(0xAC21, "loop_wait_tx_done")
label(0xAC37, "bridge_responded")
label(0xAC46, "return_from_bridge_poll")
label(0xAC47, "osword_14_handler")
label(0xAC55, "loop_copy_txcb_init")
label(0xAC5D, "store_txcb_init_byte")
label(0xAC85, "loop_copy_ws_to_pb")
label(0xACB7, "handle_tx_request")
label(0xACCE, "loop_send_pb_chars")
label(0xACE4, "loop_bridge_tx_delay")
label(0xACED, "handle_burst_xfer")
label(0xAD0E, "restore_regs_return")

# OSWORD handler PHA/PHA/RTS dispatch table (9 entries, OSWORDs 0-8).
# Dispatched via push_osword_handler_addr (&A981). Each pair of lo/hi bytes
# encodes handler_address-1 for the PHA/PHA/RTS idiom.

label(0xAD64, "netv_claim_release")
label(0xAD7D, "process_match_result")
label(0xAD86, "save_tube_state")
label(0xAD88, "loop_save_tube_bytes")
label(0xAD9F, "loop_poll_ws_status")
label(0xADAC, "loop_restore_stack")
label(0xADB0, "store_stack_byte")
label(0xADB7, "return_from_claim_release")
label(0xADC0, "return_from_match_rx_code")
data_banner(0xADC1, "osword_claim_codes",
    title="OSWORD per-claim-code lookup table (18 bytes)",
    description="""\
Looked up by [`match_rx_code`](address:ADB8) when an Econet RX
event triggers an OSWORD-related claim. The X register selects an
18-byte slice; bytes encode the claim type (immediate-op,
broadcast, port-specific) used by the dispatcher to decide which
handler chain to install. Per-byte inline comments document each
entry.""")

for i in range(18):
    byte(0xADC1 + i)
label(0xADDD, "copy_pb_to_ws")
label(0xADE1, "loop_copy_pb_to_ws")
label(0xAE0C, "loop_copy_ws_template")
label(0xAE21, "store_tx_ptr_hi")
label(0xAE23, "select_store_target")
label(0xAE29, "store_via_rx_ptr")
label(0xAE2B, "advance_template_idx")
label(0xAE2F, "done_ws_template_copy")
data_banner(0xAE33, "ws_txcb_template_data",
    title="Workspace TXCB template (39 bytes, three overlapping regions)",
    description="""\
Three overlapping copy regions indexed by different callers:

| Caller | X / Y / V | Range | Destination |
|---|---|---|---|
| Wide   | `X=&0D`, `Y=&7C`, `V=1` | bytes 0..13  | `ws+&6F..&7C` via `net_rx_ptr` |
| Narrow | `X=&1A`, `Y=&17`, `V=0` | bytes 14..26 | `ws+&0C..&17` via `nfs_workspace` |
| Vclr   | `X=&26`, `Y=&20`, `V=0` | bytes 27..38 | `ws+&15..&20` via `nfs_workspace` |

Per-byte inline comments below describe each entry's role in the
TXCB it ends up in.""")

# Three overlapping regions indexed by different callers:
#   Wide  (X=&0D, Y=&7C, V=1): bytes [0..13]  → ws+&6F..&7C via net_rx_ptr
#   Narrow (X=&1A, Y=&17, V=0): bytes [14..26] → ws+&0C..&17 via nfs_workspace
#   Spool (X=&26, Y=&0B, V=0): bytes [27..38] → ws+&01..&0B via nfs_workspace
# Markers: &FE=terminate, &FD=skip, &FC=substitute page pointer.
for i in range(39):
    byte(0xAE33 + i)

label(0xAE5A, "netv_spool_check")
label(0xAE6E, "return_from_spool_reset")
label(0xAE6F, "netv_print_data")
label(0xAE7E, "loop_drain_printer_buf")
label(0xAEB5, "done_spool_ctrl")
label(0xAEF7, "check_spool_state")
label(0xAF06, "start_spool_retry")
label(0xAF0B, "loop_copy_spool_tx")
label(0xAF2A, "loop_copy_spool_rx")
label(0xAF37, "store_spool_rx_byte")
label(0xAF39, "advance_spool_rx_idx")
label(0xAF60, "spool_tx_succeeded")
label(0xAF75, "spool_tx_retry")
label(0xAFB2, "loop_scan_disconnect")
label(0xAFC1, "verify_stn_match")
label(0xAFCC, "send_disconnect_status")
label(0xAFE9, "store_tx_ctrl_byte")
label(0xAFF1, "loop_wait_disc_tx_ack")
data_banner(0xB002, "tx_econet_txcb_template",
    title="Spool / disconnect TX control-block template (12 bytes)",
    description="""\
12-byte Econet TXCB initialisation template used by the spool /
disconnect TX paths. Copied into the workspace TXCB at offsets
`&21..&2C` via `(net_rx_ptr),Y`. Destination station and network
are filled in afterwards by the caller. Per-byte inline comments
identify each TXCB field.""")

# Split the 12-byte spool TX control block template into individual bytes.
# Simple copy (no marker processing) to workspace offset &21..&2C via
# (net_rx_ptr),Y. Destination station/network filled in afterwards.
for i in range(12):
    byte(0xB002 + i)

data_banner(0xB00E, "rx_palette_txcb_template",
    title="Palette-RX control-block template (12 bytes)",
    description="""\
12-byte template used by the *PS / palette-RX paths. Copied with
marker processing: `&FD` skips the destination byte (preserving
the existing field), `&FC` substitutes `net_rx_ptr_hi` (the
caller's RX-buffer page). Filled in over the workspace TXCB by
the broadcast-RX setup before the request is dispatched.""")
for i in range(12):
    byte(0xB00E + i)
label(0xB01A, "lang_2_save_palette_vdu")
label(0xB031, "loop_read_palette")

# Split the 3-byte OSBYTE code table into individual bytes.
# Indexed by read_osbyte_to_ws to read display mode state.
label(0xB0B1, "parse_cdir_size")
label(0xB0BA, "loop_find_alloc_size")
label(0xB0C0, "done_cdir_size")
# &B0A3 is reached as a fall-through after the bizarre `JMP (cdir_unused_dispatch_table,X)`
# at &B0A0 -- we need an explicit entry() marker so py8dis decodes it
# as code rather than treating the JMP as a terminator and giving up.
entry(0xB0A3)

# Split the 27-byte *CDir allocation size threshold table into
# individual bytes for annotation. Table base (cdir_dispatch_col+2) overlaps
# with the JMP operand high byte; data bytes run &AD32-&AD4C.
for i in range(27):
    byte(0xB0D5 + i)

label(0xB107, "ex_set_lib_flag")
label(0xB118, "fscv_5_cat")
label(0xB121, "cat_set_lib_flag")
label(0xB12E, "setup_ex_request")
label(0xB14A, "store_owner_flags")
label(0xB17B, "print_public_label")
label(0xB1BF, "print_dir_header")
label(0xB1E7, "setup_ex_pagination")
label(0xB207, "loop_scan_entry_data")
label(0xB227, "jmp_osnewl")
label(0xB255, "loop_shift_str_left")
label(0xB263, "loop_trim_trailing")
label(0xB272, "done_strip_prefix")
label(0xB274, "return_from_strip_prefix")
label(0xB275, "check_hash_prefix")
label(0xB279, "error_bad_prefix")
label(0xB27C, "check_colon_prefix")
label(0xB28B, "set_fs_select_flag")
label(0xB298, "option_str_offset_data")
label(0xB2A4, "loop_copy_char")
label(0xB2B1, "restore_after_check")
label(0xB2B3, "advance_positions")
label(0xB2DD, "loop_scan_entries")
label(0xB33F, "loop_divide_digit")
label(0xB34F, "print_nonzero_digit")
label(0xB37E, "loop_advance_char")
label(0xB38B, "loop_skip_space_chars")
label(0xB3B6, "done_ps_available")
label(0xB3D9, "loop_copy_ps_tmpl")
label(0xB3E3, "no_ps_name_given")
label(0xB3E6, "save_ps_cmd_ptr")
label(0xB3F0, "loop_pad_ps_name")
label(0xB408, "loop_read_ps_char")
label(0xB416, "done_ps_name_parse")
label(0xB429, "loop_pop_ps_slot")
label(0xB44F, "done_ps_slot_mark")
label(0xB457, "done_ps_scan")
label(0xB46C, "print_ps_now")
label(0xB477, "store_ps_station")
label(0xB498, "print_server_is_suffix")
label(0xB4C6, "loop_scan_ps_slots")
label(0xB4D6, "skip_next_ps_slot")
label(0xB4DA, "reinit_ps_slot")
label(0xB502, "done_ps_slot_scan")
label(0xB511, "loop_ps_delay")
label(0xB52D, "loop_push_ps_name")
label(0xB537, "loop_pop_ps_name")
label(0xB549, "loop_copy_tx_hdr")
data_banner(0xB552, "ps_tx_header_template",
    title="Printer-server TX header template (4 bytes)",
    description="""\
Four bytes copied to the head of the printer-server transmit
buffer by [`reverse_ps_name_to_tx`](address:B52B): control byte
`&80` (immediate-TX request), port `&D1` (printer block port),
function-code stub, and reply-port byte. Filled-in destination
fields follow from the caller's PS slot.""")
for i in range(4):
    byte(0xB552 + i)

label(0xB566, "skip_if_local_net")
data_banner(0xB575, "ps_slot_txcb_template",
    title="Printer-server slot TXCB template (12 bytes)",
    description="""\
12-byte Econet TXCB template for printer-server slot buffers.
Copied by [`init_ps_slot_from_rx`](address:B6A6) into workspace
offsets `&78`-`&83` via indexed addressing from
`write_ps_slot_link_addr` (`write_ps_slot_hi_link+1`). Substitutes
`net_rx_ptr_hi` at offsets `&7D` and `&81` (the hi bytes of the
two buffer pointers) so they point into the current RX buffer
page.

Structure: 4-byte header (control, port, station, network)
followed by two 4-byte buffer descriptors (lo address, hi page,
end lo, end hi). End bytes `&FF` are placeholders filled in later
by the caller.""")

for i in range(12):
    byte(0xB575 + i)
label(0xB5C3, "no_poll_name_given")
label(0xB5C6, "skip_if_no_poll_arg")
label(0xB5CE, "loop_pad_poll_name")
label(0xB5E6, "loop_read_poll_char")
label(0xB5F4, "done_poll_name_parse")
label(0xB611, "loop_print_poll_name")
label(0xB61F, "done_poll_name_print")
label(0xB65A, "check_poll_jammed")
label(0xB65E, "print_poll_jammed")
label(0xB66A, "check_poll_busy")
label(0xB69A, "done_poll_status_line")
label(0xB69D, "done_poll_slot_mark")
label(0xB6A8, "loop_copy_slot_tmpl")
label(0xB6B3, "subst_rx_page_byte")
label(0xB6B5, "store_slot_tmpl_byte")
label(0xB6CB, "done_uppercase_store")
label(0xB6EE, "loop_match_prot_attr")
label(0xB703, "request_next_wipe")
label(0xB736, "check_wipe_attr")
label(0xB739, "loop_check_if_locked")
label(0xB73D, "skip_wipe_locked")
label(0xB742, "check_wipe_dir")
label(0xB74B, "show_wipe_prompt")
label(0xB74F, "loop_copy_wipe_name")
label(0xB773, "loop_print_wipe_info")
label(0xB787, "check_wipe_response")
label(0xB799, "loop_build_wipe_cmd")
label(0xB7A2, "skip_if_not_space")
label(0xB7A6, "set_wipe_cr_end")
label(0xB7A8, "store_wipe_tx_char")
label(0xB7B7, "skip_wipe_to_next")
label(0xB7BD, "use_wipe_leaf_name")
label(0xB7BE, "loop_copy_wipe_leaf")
label(0xB7E6, "loop_clear_chan_table")
label(0xB7F6, "loop_mark_chan_avail")
label(0xB80F, "error_chan_out_of_range")
label(0xB811, "return_chan_index")
label(0xB81D, "error_chan_not_found")
label(0xB85B, "error_chan_not_here")
label(0xB866, "loop_copy_chan_err_str")
label(0xB879, "loop_append_err_suffix")
label(0xB8AB, "loop_scan_fcb_slots")
label(0xB8B9, "done_found_free_slot")
label(0xB8F6, "return_alloc_success")
label(0xB8F9, "skip_set_carry")
label(0xB8FE, "loop_scan_fcb_down")
label(0xB902, "skip_if_slots_done")
label(0xB916, "done_check_station")
label(0xB93A, "loop_find_fcb")
label(0xB941, "skip_if_no_wrap")
label(0xB94B, "done_check_fcb_status")
label(0xB955, "done_select_fcb")
label(0xB956, "loop_scan_empty_fcb")
label(0xB95D, "done_test_empty_slot")
label(0xB96C, "skip_if_modified_fcb")
label(0xB989, "loop_clear_counters")
label(0xB9DA, "done_restore_offset")
label(0xBA00, "done_clear_fcb_active")
label(0xBA0B, "loop_save_tx_context")
label(0xBA1E, "done_save_context")
label(0xBA21, "loop_find_pending_fcb")
label(0xBA65, "done_init_wipe")
label(0xBA89, "done_calc_offset")
label(0xBAA8, "loop_clear_buffer")
label(0xBAAD, "done_set_fcb_active")
label(0xBAB7, "loop_restore_workspace")
label(0xBAC2, "loop_restore_tx_buf")
label(0xBACC, "loop_save_before_match")
label(0xBAD1, "loop_reload_attr")
label(0xBAD4, "loop_next_fcb_slot")
label(0xBAEE, "done_test_fcb_active")
label(0xBB27, "return_test_offset")
label(0xBB48, "loop_process_fcb")
label(0xBB53, "done_flush_fcb")
label(0xBB58, "done_advance_fcb")
label(0xBB87, "done_read_fcb_byte")
label(0xBBB1, "error_end_of_file")
label(0xBBC2, "done_load_from_buf")
label(0xBC14, "done_test_write_flag")
label(0xBC22, "done_find_write_fcb")
label(0xBC32, "done_check_buf_offset")
label(0xBC46, "done_set_dirty_flag")
label(0xBC65, "done_inc_byte_count")
label(0xBCEF, "loop_copy_wipe_err_msg")
label(0xBCFC, "done_terminate_wipe_err")
label(0xBD05, "done_toggle_station")


label(0x83E5, "discard_reset_rx")
label(0x83E8, "reset_adlc_rx_listen")
label(0x83EB, "set_nmi_rx_scout")
label(0x8512, "setup_sr_tx")
label(0x8549, "tx_done_econet_event")
label(0x8551, "tx_done_fire_event")
label(0x8B00, "scan_remote_keys")
label(0x8B18, "save_text_ptr")
label(0x8BBB, "help_print_nfs_cmds")
label(0x8BC6, "print_cmd_table")
label(0x8BD5, "print_cmd_table_loop")
label(0x8C29, "help_wrap_if_serial")
label(0x8C93, "print_version_header")
label(0x8CBD, "setup_ws_ptr")
label(0x8CFD, "notify_new_fs")
label(0x8CFF, "call_fscv")
label(0x8D02, "issue_svc_15")
label(0x8E21, "clear_if_station_match")
label(0x8E2C, "return_from_station_match")
label(0x8E38, "pass_send_cmd")
label(0x8E3C, "send_cmd_and_dispatch")
label(0x8E5B, "dir_op_dispatch")
label(0x8E6A, "push_dispatch_lo")
label(0x8EF0, "store_ws_page_count")
label(0x903C, "init_adlc_and_vectors")
label(0x904F, "write_vector_entry")
label(0x9064, "restore_fs_context")
label(0x9071, "fscv_6_shutdown")
label(0x909E, "verify_ws_checksum")
label(0x90B5, "error_net_checksum")
label(0x9236, "print_hex_byte")
label(0x923F, "print_hex_nybble")
label(0x934A, "err_bad_hex")
label(0x9357, "err_bad_station_num")
label(0x939A, "is_decimal_digit")
label(0x93A2, "is_dec_digit_only")
label(0x93AB, "get_access_bits")
label(0x93B5, "get_prot_bits")
label(0x93D3, "set_text_and_xfer_ptr")
label(0x93D7, "set_xfer_params")
label(0x93DD, "set_options_ptr")
label(0x93E1, "clear_escapable")
label(0x93E6, "cmp_5byte_handle")
label(0x93F7, "set_conn_active")
label(0x940D, "clear_conn_active")
label(0x9437, "error_bad_filename")
label(0x9446, "check_not_ampersand")
label(0x944E, "read_filename_char")
label(0x945E, "send_fs_request")
label(0x9483, "parse_quoted_arg")
label(0x973D, "init_txcb_bye")
label(0x973F, "init_txcb_port")
label(0x974B, "init_txcb")
label(0x976F, "send_request_nowrite")
label(0x9773, "send_request_write")
label(0x978A, "save_net_tx_cb")
label(0x978B, "save_net_tx_cb_vset")
label(0x97B7, "prep_send_tx_cb")
label(0x97CD, "recv_and_process_reply")
label(0x98BE, "wait_net_tx_ack")
label(0x9900, "cond_save_error_code")
label(0x9930, "fixup_reply_status_a")
label(0x993B, "load_reply_and_classify")
label(0x993D, "classify_reply_error")
label(0x99A2, "bad_str_anchor")
label(0x99DF, "check_net_error_code")
label(0x9A3A, "append_drv_dot_num")
label(0x9A5E, "append_space_and_num")
label(0x9A69, "append_decimal_num")
label(0x9A7A, "append_decimal_digit")
label(0x9B24, "init_tx_ptr_and_send")
label(0x9B2C, "send_net_packet")
label(0x9B81, "init_tx_ptr_for_pass")
label(0x9B89, "setup_pass_txbuf")
label(0x9BF5, "load_text_ptr_and_parse")
label(0x9C00, "gsread_to_buf")
label(0x9C3E, "do_fs_cmd_iteration")
label(0x9C85, "send_txcb_swap_addrs")
label(0x9D44, "print_load_exec_addrs")
label(0x9D4F, "print_5_hex_bytes")
label(0x9D5F, "copy_fsopts_to_zp")
label(0x9D6B, "skip_one_and_advance5")
label(0x9D6C, "advance_y_by_4")
label(0x9D71, "copy_workspace_to_fsopts")
label(0x9D7E, "retreat_y_by_4")
label(0x9D7F, "retreat_y_by_3")
label(0x9D87, "check_and_setup_txcb")
label(0x9E82, "format_filename_field")
label(0x9FB4, "return_with_last_flag")
label(0x9FB6, "finalise_and_return")
label(0xA12C, "update_addr_from_offset9")
label(0xA131, "update_addr_from_offset1")
label(0xA133, "add_workspace_to_fsopts")
label(0xA134, "adjust_fsopts_4bytes")
label(0xA1EF, "lookup_cat_entry_0")
label(0xA1F3, "lookup_cat_slot_data")
label(0xA1FA, "setup_transfer_workspace")
label(0xA2ED, "write_data_block")
label(0xA329, "tail_update_catalogue")
label(0xA390, "tube_claim_c3")
label(0xA3BB, "print_fs_info_newline")
label(0xA3E7, "get_pb_ptr_as_index")
label(0xA3E9, "byte_to_2bit_index")
label(0xA3FE, "return_from_2bit_index")
label(0xA42F, "fscv_3_star_cmd")
label(0xA440, "cmd_fs_reentry")
label(0xA442, "error_syntax")
label(0xA45B, "match_fs_cmd")
label(0xA638, "fsreply_3_set_csd")
label(0xA644, "find_station_bit2")
label(0xA66F, "find_station_bit3")
label(0xA6A6, "flip_set_station_boot")
label(0xA764, "boot_cmd_oscli")
label(0xA864, "osword_setup_handler")
label(0xA901, "bin_to_bcd")
label(0xAC67, "store_osword_pb_ptr")
label(0xACAD, "store_ptr_at_ws_y")
label(0xABE9, "init_bridge_poll")
label(0xACF8, "enable_irq_and_poll")
label(0xAD15, "push_osword_handler_addr")
label(0xAD40, "tx_econet_abort")
label(0xADFE, "init_ws_copy_wide")
label(0xAE07, "init_ws_copy_narrow")
label(0xAE0B, "ws_copy_vclr_entry")
label(0xAE64, "reset_spool_buf_state")
label(0xAE94, "append_byte_to_rxbuf")
label(0xAE9D, "handle_spool_ctrl_byte")
label(0xAF80, "err_printer_busy")
label(0xAFA6, "send_disconnect_reply")
label(0xB05F, "commit_state_byte")
label(0xB066, "serialise_palette_entry")
label(0xB081, "read_osbyte_to_ws_x0")
label(0xB083, "read_osbyte_to_ws")
label(0xB0D2, "cdir_dispatch_col")
label(0xB21A, "print_10_chars")
label(0xB22A, "parse_cmd_arg_y0")
label(0xB22C, "parse_filename_arg")
label(0xB22F, "parse_access_prefix")
label(0xB251, "strip_token_prefix")
label(0xB29F, "copy_arg_to_buf_x0")
label(0xB2A1, "copy_arg_to_buf")
label(0xB2A3, "copy_arg_validated")
label(0xB2CA, "return_from_copy_arg")
label(0xB2E4, "ex_print_col_sep")
label(0xB327, "print_num_no_leading")
label(0xB32A, "print_decimal_3dig")
label(0xB338, "print_decimal_digit")
label(0xB356, "return_from_print_digit")
label(0xB373, "save_ptr_to_os_text")
label(0xB37F, "skip_to_next_arg")
label(0xB392, "return_from_skip_arg")
label(0xB393, "save_ptr_to_spool_buf")
label(0xB39E, "init_spool_drive")
label(0xB3D5, "copy_ps_data_y1c")
label(0xB3D7, "copy_ps_data")
label(0xB483, "print_file_server_is")
label(0xB48D, "print_printer_server_is")
label(0xB4A8, "load_ps_server_addr")
label(0xB4B4, "pop_requeue_ps_scan")
label(0xB4FC, "write_ps_slot_hi_link")
label(0xB51C, "write_ps_slot_byte_ff")
label(0xB523, "write_two_bytes_inc_y")
label(0xB52B, "reverse_ps_name_to_tx")
label(0xB556, "print_station_addr")
label(0xB6A5, "return_from_poll_slots")
label(0xB6A6, "init_ps_slot_from_rx")
label(0xB6BD, "store_char_uppercase")
label(0xB7D3, "flush_and_read_char")
label(0xB7E3, "init_channel_table")
label(0xB805, "attr_to_chan_index")
label(0xB814, "check_chan_char")
label(0xB81C, "err_net_chan_invalid")
label(0xB81F, "err_net_chan_not_found")
label(0xB847, "lookup_chan_by_char")
label(0xB886, "store_result_check_dir")
label(0xB88C, "check_not_dir")
label(0xB8A8, "alloc_fcb_slot")
label(0xB8DC, "alloc_fcb_or_error")
label(0xB8F8, "close_all_net_chans")
label(0xB8FC, "scan_fcb_flags")
label(0xB925, "match_station_net")
label(0xB933, "return_from_match_stn")
label(0xB934, "find_open_fcb")
label(0xB977, "init_wipe_counters")
label(0xB99A, "start_wipe_pass")
label(0xBA09, "save_fcb_context")
label(0xBAC0, "restore_catalog_entry")
label(0xBACF, "find_matching_fcb")
label(0xBB2A, "inc_fcb_byte_count")
label(0xBB37, "return_from_inc_fcb_count")
label(0xBCBC, "send_wipe_request")
label(0xBD15, "send_and_receive")
label(0xBD25, "abort_if_escape")
label(0xBD2A, "error_escape_pressed")
label(0xBD48, "loop_push_zero_buf")
label(0xBD59, "loop_dump_line")
label(0xBD60, "loop_read_dump_byte")
label(0xBD72, "done_check_dump_eof")
label(0xBD79, "loop_pop_stack_buf")
label(0xBD80, "done_check_boundary")
label(0xBD8B, "done_start_dump_addr")
label(0xBD8D, "loop_print_addr_byte")
label(0xBD9E, "loop_inc_dump_addr")
label(0xBDB6, "loop_print_dump_hex")
label(0xBDBB, "loop_next_dump_col")
label(0xBDCF, "done_print_separator")
label(0xBDDA, "loop_print_dump_ascii")
label(0xBDE2, "skip_non_printable")
label(0xBDE4, "done_test_del")
label(0xBDF3, "done_end_dump_line")
label(0xBDFC, "done_dump_eof")
label(0xBE01, "print_dump_header")
label(0xBE37, "print_hex_and_space")
label(0xBF71, "close_ws_file")
label(0xBF78, "open_file_for_read")
label(0xBE40, "done_print_hex_space")
label(0xBFA6, "loop_skip_filename")
label(0xBFB1, "loop_skip_fn_spaces")
label(0xBE42, "parse_dump_range")
label(0xBE47, "loop_clear_hex_accum")
label(0xBE4E, "loop_parse_hex_digit")
label(0xBE6D, "done_mask_hex_digit")
label(0xBE74, "loop_shift_nibble")
label(0xBE77, "loop_rotate_hex_accum")
label(0xBE98, "error_hex_overflow")
label(0xBE9C, "error_bad_hex_value")
label(0xBEA2, "loop_skip_hex_spaces")
label(0xBEA3, "done_test_hex_space")
label(0xBEAB, "init_dump_buffer")
label(0xBEC4, "loop_cmp_file_length")
label(0xBED0, "done_check_outside")
label(0xBED6, "error_outside_file")
label(0xBEEB, "loop_copy_start_addr")
label(0xBEF0, "done_advance_start")
label(0xBF08, "loop_copy_osfile_ptr")
label(0xBF1B, "loop_shift_osfile_data")
label(0xBF2A, "loop_check_ff_addr")
label(0xBF37, "loop_zero_load_addr")
label(0xBF3E, "done_parse_disp_base")
label(0xBF53, "done_add_disp_base")
label(0xBF58, "loop_add_disp_bytes")
label(0xBF68, "loop_store_disp_addr")
label(0xBFBA, "advance_x_by_8")
label(0xBFBD, "advance_x_by_4")
label(0xBFC0, "inx4")

# ============================================================
# ROM entry points and subroutines
# ============================================================

entry(0x8028)
subroutine(0x8028, "svc5_irq_check",
    title="Service 5: unrecognised interrupt (Master 128 dispatch)",
    description="""\
Reads the deferred-work flag at `&0D65`; if zero, returns early via
`PLX`/`PLY`/`RTS`. Otherwise clears bit 7 of the Master 128 `ACCCON`
register at `&FE34` (`TRB`), zeros `&0D65`, then dispatches one of
two ways depending on bit 7 of the saved `Y`:

| Caller `Y` bit 7 | Action |
|---|---|
| Set | Dispatch via the `PHA`/`PHA`/`RTS` table at [`dispatch_svc5`](address:8048) |
| Clear | Fire Econet RX event `&FE` via [`generate_event`](address:8045), then `JMP` to [`tx_done_exit`](address:8582) |""",
    on_entry={"a": "5 (service call number)",
              "x": "ROM slot",
              "y": "parameter (high bit selects dispatch path)"})
subroutine(0x8045, "generate_event",
    title="Generate event via EVNTV",
    description="""\
Single-instruction `JMP (evntv)` that hands control to whatever
handler is hooked into the MOS event vector. Called via service
call &05 (`svc5_irq_check`) on a 'transmit complete' or 'receive
complete' edge so user/MOS code can react to network events.""",
    on_entry={"A": "event number"},
    on_exit={"A": "preserved", "X": "preserved", "Y": "preserved"})

subroutine(0x8048, "dispatch_svc5",
    title="Service-5 PHA/PHA/RTS dispatch tail",
    description="""\
Builds an `RTS`-target on the stack from the
[`tx_done_dispatch_lo`](address:84B8) low-byte table and a hard-
coded high byte of `&85`, then falls through into the shared
[`svc_5_unknown_irq`](address:804F) `RTS` to land on the matching
[`tx_done_dispatch_lo`](address:84B8)+`Y` page-`&85` handler.""",
    on_entry={"y": "tx_done_dispatch_lo offset (post-&83 base bias)"})

subroutine(0x804F, "svc_5_unknown_irq",
    title="Service-5 unknown-IRQ tail (PHA/PHA/RTS landing)",
    description="""\
Bare `RTS` reused as the final step of every
[`dispatch_svc5`](address:8048) entry. With the target's
high/low bytes already pushed by the caller, `RTS` jumps to the
selected handler. Also reached as the unclaimed-IRQ tail of the
service-5 prologue when no ANFS handler matches.""")

subroutine(0x8A54, "service_handler",
    title="Service call dispatch (Master 128)",
    description="""\
Handles service calls 1, 4, 8, 9, 13, 14, and 15.

| Call | Meaning                          |
|-----:|----------------------------------|
|    1 | Absolute workspace claim         |
|    4 | Unrecognised `*` command         |
|    8 | Unrecognised OSWORD              |
|    9 | `*HELP`                          |
|   13 | ROM initialisation               |
|   14 | ROM initialisation complete      |
|   15 | Vectors claimed                  |

On service 15 the ROM verifies the host OS via OSBYTE 0 with the
input `X=1`, which returns the OS version code:

| OSBYTE 1 value | Host                                |
|---------------:|-------------------------------------|
|              0 | OS 1.00 (early BBC B or Electron)   |
|              1 | OS 1.20 or American OS              |
|              2 | OS 2.00 (BBC B+)                    |
|              3 | OS 3.2 / 3.5 (Master 128)           |
|              4 | OS 4.0 (Master Econet Terminal)     |
|              5 | OS 5.0 (Master Compact)             |

Only Master 128 and Master Econet Terminal are supported. Any
other version gets a `Bad ROM <slot>` message printed and its
workspace byte cleared at `&02A0 + adjusted-slot`, effectively
rejecting the ROM.""",
    on_entry={"a": "service call number", "x": "ROM slot", "y": "parameter"})

# Suppress the py8dis OSBYTE-0/X=1 auto-comment at &8A61 -- the same
# table now lives in the service_handler banner.
no_automatic_comment(0x8A61)


# ============================================================
# Relocated code labels (from NFS 3.65 correspondence)
# ============================================================
# Pages 4-5 are 100% opcode-identical to NFS 3.65.
# Page 6 is 74% matching. Zero page block is 70% matching.

# tube_ctrl_values: 8-byte table of ULA control register values
# (writes to &FEE0) indexed by transfer type (0-7). The LSR/LSR/BCC
# sequence at tube_transfer_setup tests bit 2 of the ctrl byte to
# decide whether a 2-byte R3 FIFO flush is required before the final
# R4 trigger write. Bit 2 is set only for types 0 (&86) and 2 (&96),
# both parasite-to-host transfers -- the flush drains stale bytes
# from the 2-byte R3 FIFO before the parasite starts filling it.

# ============================================================
# ROM code labels (from NFS 3.65 correspondence)
# ============================================================
# About 27% of NFS 3.65 main ROM opcodes match in ANFS.

label(0x801A, "copyright_string")
label(0x8070, "init_nmi_workspace")
label(0x8072, "copy_nmi_shim")
label(0x80B3, "accept_frame")
label(0x80C6, "scout_reject")
label(0x80CE, "accept_local_net")
label(0x80D1, "accept_scout_net")
label(0x80E5, "scout_discard")
label(0x80ED, "scout_loop_rda")
label(0x80FD, "scout_loop_second")
label(0x8138, "scout_no_match")
label(0x813B, "scout_match_port")
label(0x8145, "scan_port_list")
label(0x814E, "scan_nfs_port_list")
label(0x8152, "check_port_slot")
label(0x8154, "scout_ctrl_check")
label(0x8166, "check_station_filter")
label(0x8170, "scout_port_match")
label(0x817A, "next_port_slot")
label(0x8187, "discard_no_match")
label(0x818A, "try_nfs_port_list")
label(0x8195, "port_match_found")
label(0x81A7, "send_data_rx_ack")
label(0x81B8, "data_rx_setup")
label(0x81D6, "nmi_data_rx_net")
label(0x81EC, "nmi_data_rx_skip")
label(0x81F7, "install_data_rx_handler")
label(0x820A, "install_tube_rx")
label(0x8215, "nmi_error_dispatch")
label(0x821D, "rx_error_reset")
label(0x8228, "data_rx_loop")
label(0x8241, "read_sr2_between_pairs")
label(0x8248, "read_second_rx_byte")
label(0x825C, "check_sr2_loop_again")
label(0x827F, "read_last_rx_byte")
label(0x828E, "send_ack")
label(0x8291, "nmi_data_rx_tube")
label(0x8294, "rx_tube_data")
label(0x82B1, "data_rx_tube_error")
label(0x82B4, "data_rx_tube_complete")
label(0x82EA, "ack_tx_configure")
label(0x82F8, "ack_tx_write_dest")
label(0x8339, "start_data_tx")
label(0x833C, "dispatch_nmi_error")
label(0x833F, "advance_rx_buffer_ptr")
label(0x834A, "add_rxcb_ptr")
label(0x8378, "inc_rxcb_ptr")
label(0x8383, "skip_tube_update")
label(0x8385, "return_rx_complete")
label(0x8395, "rx_complete_update_rxcb")
label(0x839A, "add_buf_to_base")
label(0x83A1, "inc_rxcb_buf_hi")
label(0x83A3, "store_buf_ptr_lo")
label(0x83A5, "store_rxcb_buf_ptr")
label(0x83AA, "store_rxcb_buf_hi")
label(0x83AC, "skip_buf_ptr_update")
label(0x8400, "copy_scout_to_buffer")
label(0x8406, "copy_scout_select")
label(0x8416, "copy_scout_bytes")
label(0x8424, "next_scout_byte")
label(0x842B, "scout_copy_done")
label(0x8436, "copy_scout_via_tube")
label(0x8448, "release_tube")
label(0x8451, "clear_release_flag")
label(0x846B, "rotate_prot_mask")
label(0x8471, "dispatch_imm_op")
label(0x847C, "scout_page_overflow")
label(0x8482, "check_scout_done")
label(0x8488, "imm_op_out_of_range")
label(0x84A5, "copy_addr_loop")
label(0x84B1, "svc5_dispatch_lo")
label(0x84E0, "set_tx_reply_flag")
label(0x84E8, "rx_imm_halt_cont")
label(0x84ED, "tx_cr2_setup")
label(0x84F2, "tx_nmi_setup")
label(0x84F9, "imm_op_build_reply")
label(0x8529, "imm_op_discard")
label(0x8573, "halt_spin_loop")
label(0x8582, "tx_done_exit")
label(0x8589, "tx_begin")
label(0x85A1, "tx_imm_op_setup")
label(0x85B5, "calc_peek_poke_size")
label(0x85CC, "tx_ctrl_range_check")
label(0x85D0, "check_imm_range")
label(0x85D6, "copy_imm_params")
label(0x85E0, "tx_line_idle_check")
label(0x85FA, "test_inactive_retry")
label(0x85FC, "intoff_test_inactive")
label(0x8602, "test_line_idle")
label(0x8616, "inactive_retry")
label(0x862C, "tx_bad_ctrl_error")
label(0x863C, "tx_no_clock_error")
label(0x863E, "store_tx_error")
label(0x8697, "add_bytes_loop")
label(0x8686, "tx_ctrl_machine_type")
label(0x86A9, "setup_data_xfer")
label(0x86BF, "copy_bcast_addr")
label(0x86CB, "setup_unicast_xfer")
label(0x86D0, "proc_op_status2")
label(0x86D2, "store_status_copy_ptr")
label(0x86D5, "skip_buf_setup")
label(0x86E0, "tx_ctrl_exit")
label(0x86ED, "tx_fifo_write")
label(0x870D, "tx_error")
label(0x8711, "tx_fifo_not_ready")
label(0x8718, "tx_store_error")
label(0x871B, "delay_nmi_disable")
label(0x873C, "check_handshake_bit")
label(0x8746, "install_reply_scout")
label(0x8773, "reject_reply")
label(0x87CE, "data_tx_begin")
label(0x87DC, "install_imm_data_nmi")
label(0x87F2, "data_tx_check_fifo")
label(0x880B, "write_second_tx_byte")
label(0x881F, "check_irq_loop")
label(0x882B, "data_tx_last")
label(0x883C, "install_saved_handler")
label(0x8845, "nmi_data_tx_tube")
label(0x8848, "tube_tx_fifo_write")
label(0x8860, "write_second_tube_byte")
label(0x886A, "tube_tx_inc_byte2")
label(0x886E, "tube_tx_inc_byte3")
label(0x8872, "tube_tx_inc_byte4")
label(0x8876, "check_tube_irq_loop")
label(0x887E, "tx_tdra_error")
label(0x88A6, "nmi_final_ack_net")
label(0x88D7, "check_fv_final_ack")
label(0x88E2, "tx_result_fail")
label(0x8935, "calc_transfer_size")
label(0x8965, "restore_x_and_return")
label(0x8968, "fallback_calc_transfer")
label(0x898B, "nmi_shim_rom_src")
label(0x89A6, "wait_idle_and_reset")
label(0x89AB, "poll_nmi_idle")
label(0x89C7, "reset_enter_listen")

# Entry points from NFS 3.65 correspondence
entry(0x804F)
entry(0x809B)
entry(0x80B8)
entry(0x80E8)
entry(0x81B8)
entry(0x81C2)
entry(0x81D6)
entry(0x81EC)
entry(0x8223)
entry(0x8291)
entry(0x8316)
entry(0x8360)
entry(0x8386)
entry(0x84F9)
entry(0x85F1)
entry(0x86E7)
entry(0x870D)
entry(0x8723)
entry(0x872F)
entry(0x874B)
entry(0x875F)
entry(0x8776)
entry(0x87BE)
entry(0x87E3)
entry(0x8845)
entry(0x8886)
entry(0x8892)
entry(0x88A6)
entry(0x88BA)
entry(0x88DE)
entry(0x88E4)
entry(0x8968)
entry(0x89CA)
entry(0x89D8)

# ============================================================
# Subroutines (from NFS 3.65 correspondence)
# ============================================================



comment(0x8000, """\
ANFS ROM 4.21 (variant 1) disassembly (Acorn Advanced Network Filing System)
============================================================================""")

subroutine(0x8050, "adlc_init",
    title="ADLC initialisation",
    description="""\
Initialise ADLC hardware and Econet workspace. Disables NMIs via
`BIT master_intoff` (the Master 128 INTOFF register at &FE38;
the Model-B equivalent reads econet_station_id at &FE18 for the
same side effect). Performs a full ADLC reset via
[`adlc_full_reset`](address:898C), then probes for a Tube
co-processor via OSBYTE `&EA` and stores the result in
[`tube_present`](address:0D63). Issues an NMI-claim service
request (OSBYTE `&8F`, `X=&0C`). Falls through to
[`init_nmi_workspace`](address:8070) to copy the NMI shim to
RAM.""")
subroutine(0x8070, "init_nmi_workspace",
    title="Initialise NMI workspace (skip service request)",
    description="""\
Copies 32 bytes of NMI shim code from ROM (`listen_jmp_hi`) to the
start of the NFS workspace RAM block, then patches the current ROM
bank number into the self-modifying code at `nmi_romsel` (`&0D07`).

The shim includes the INTOFF/INTON pair (`BIT
econet_station_id` at entry, `BIT econet_nmi_enable` before
`RTI`) that toggles the IC97 NMI-enable flip-flop, guaranteeing
edge re-triggering on /NMI.

Workspace fields written:

| Address / label | Value | Role |
|---|---|---|
| `tx_src_net`         | `0`    | clear |
| `need_release_tube`  | `0`    | clear |
| `tx_op_type`         | `0`    | clear |
| `tx_src_stn` (`&0D22`) | station ID | from `econet_station_id` |
| `tx_complete_flag`   | `&80`  | mark idle |
| `econet_init_flag`   | `&80`  | mark initialised |

Finally re-enables NMIs via INTON (`econet_nmi_enable` read).""")
subroutine(0x809B, "nmi_rx_scout",
    title="NMI RX scout handler (initial byte)",
    description="""\
Default NMI handler for incoming scout frames. Checks whether the
frame is addressed to us or is a broadcast. Installed as the NMI
target during idle RX listen mode.

Tests `SR2` bit 0 (`AP` = Address Present) to detect incoming
data. Reads the first byte (destination station) from the RX FIFO
and compares against our station ID. Reading `econet_station_id`
(`&FE18`) also disables NMIs (INTOFF side effect).""")
subroutine(0x80B8, "nmi_rx_scout_net",
    title="RX scout second byte handler",
    description="""\
Reads the second byte of an incoming scout (destination network).

| Value | Meaning | Action |
|---|---|---|
| `0`   | local network | accept |
| `&FF` | broadcast | accept and flag |
| other | foreign network | reject |

Installs [`copy_scout_to_buffer`](address:8400) as the
scout-data reading loop handler.""")
subroutine(0x80D8, "scout_error",
    title="Scout error/discard handler",
    description="""\
Handles scout reception errors and end-of-frame conditions. Reads
`SR2` and tests `AP|RDA` (bits 0 and 7):

- **Neither set** – the frame ended cleanly; simply discard.
- **Either set** – unexpected data is present; perform a full ADLC
  reset.

Also serves as the common discard path for address/network
mismatches from [`nmi_rx_scout`](address:809B) and
[`scout_complete`](address:8112) – reached by 5 branch sites
across the scout reception chain.""")
subroutine(0x8112, "scout_complete",
    title="Scout completion handler",
    description="""\
Processes a completed scout frame. Writes `CR1=&00` and `CR2=&84`
to disable `PSE` and suppress `FV`, then tests `SR2` for `FV`
(frame valid). If `FV` is set with `RDA`, reads the remaining
scout data bytes in pairs into the buffer at `&0D3D`.

Matches the port byte (`&0D40`) against open receive control
blocks to find a listener:

- **On match** – calculates the transfer size via
  [`tx_calc_transfer`](address:8900), sets up the data RX
  handler chain, and sends a scout ACK.
- **On no match or error** – discards the frame via
  [`scout_error`](address:80D8).""")
subroutine(0x8195, "port_match_found",
    title="Scout matched: arm data RX, ACK or discard",
    description="""\
Sets `scout_status=3` (match found) at `rx_port`, calls
[`tx_calc_transfer`](address:8900) to compute the transfer
parameters from the RXCB, then triages:

| Carry | `rx_src_net` (V) | Action |
|---|---|---|
| `C=0` | – | no Tube claimed → [`nmi_error_dispatch`](address:8215) (discard) |
| `C=1` | broadcast | discard (broadcasts get no ACK) |
| `C=1` | unicast   | [`send_data_rx_ack`](address:81A7) |

Four inbound refs (one `JSR` from `&84B9` and three branches from
the [`scout_complete`](address:8112) dispatch).""",
    on_exit={"a": "3 (scout_status)"})
subroutine(0x81A7, "send_data_rx_ack",
    title="Send scout ACK and arm data-RX continuation",
    description="""\
Switches the ADLC to TX mode for the scout ACK frame: writes
`CR1=&44` (`RX_RESET | TIE`), `CR2=&A7` (`RTS | CLR_TX_ST |
FC_TDRA | PSE`), then loads `(A,Y) = (&B8, &81)` – the address
of [`data_rx_setup`](address:81B8) – and `JMP`s to
[`ack_tx_write_dest`](address:82F8) which saves the pair into
`saved_nmi_lo`/`saved_nmi_hi` (so the NMI handler will install it
later) and writes the ACK destination address bytes to the TX
FIFO.

Two callers: the dispatch in [`scout_complete`](address:8112)
at `&81A2` and the immediate-op POKE path at `&84AE`
(`jmp_send_data_rx_ack`).""",
    on_exit={"a": "&B8 (low byte of data_rx_setup)",
             "y": "&81 (high byte of data_rx_setup)"})
subroutine(0x81B8, "data_rx_setup",
    title="NMI handler: switch ADLC to RX for the data frame",
    description="""\
NMI continuation entry installed by
[`send_data_rx_ack`](address:81A7) (which pushes
`(&81B8 - 1)` on the stack and routes it through
[`ack_tx_write_dest`](address:82F8)). When the next NMI fires,
this body writes `CR1 = &82` (`TX_RESET | RIE`) to switch the
ADLC from scout-ACK TX mode to data-frame RX mode, then `JMP`s to
`install_nmi_handler` to install
[`nmi_data_rx`](address:81C2) as the next NMI handler.""")
subroutine(0x81C2, "nmi_data_rx",
    title="Data frame RX handler (four-way handshake)",
    description="""\
Receives the data frame after the scout ACK has been sent. First
checks AP (Address Present) for the start of the data frame. Reads
and validates the first two address bytes (dest_stn, dest_net)
against our station address, then installs continuation handlers
to read the remaining data payload into the open port buffer.

Handler chain: this routine (AP + dest-stn check) →
[`nmi_data_rx_net`](address:81D6) (dest-net check) →
[`nmi_data_rx_skip`](address:81EC) (skip ctrl + port) →
[`nmi_data_rx_bulk`](address:8223) (bulk data read) →
[`data_rx_complete`](address:8268) (completion).""")
subroutine(0x81D6, "nmi_data_rx_net",
    title="NMI handler: validate dest-net byte of data frame",
    description="""\
NMI continuation entry installed by [`nmi_data_rx`](address:81C2)
once the AP and dest-station bytes have validated. Polls SR2
(`BIT econet_control23_or_status2`); on no RDA, branches to
[`nmi_error_dispatch`](address:8215). Otherwise reads the dest-
network byte from the ADLC FIFO and falls through to the
control/port skip step.""",
    on_exit={"a": "dest-network byte (validated against local)"})
subroutine(0x81EC, "nmi_data_rx_skip",
    title="NMI handler: skip control + port bytes",
    description="""\
NMI continuation entry that consumes the control and port bytes of
the data frame (already known from the scout) and proceeds to the
bulk-data-read continuation. Polls SR2 for RDA on entry; on no
RDA, branches to [`nmi_error_dispatch`](address:8215).""")
subroutine(0x81F7, "install_data_rx_handler",
    title="Install data RX bulk or Tube handler",
    description="""\
Selects between the normal bulk-RX handler at
[`nmi_data_rx_bulk`](address:8223) and the Tube RX handler at
[`nmi_data_rx_tube`](address:8291) based on bit 1 of
`rx_src_net` (`tx_flags`).

| `rx_src_net` bit 1 | Handler |
|---|---|
| clear | [`nmi_data_rx_bulk`](address:8223) (`A=&23`, `Y=&82`) |
| set   | [`nmi_data_rx_tube`](address:8291) (`A=&91`, `Y=&82`) |

In the bulk path, after loading the handler address, checks `SR1`
bit 7. If `IRQ` is already asserted (more data waiting), jumps
directly to [`nmi_data_rx_bulk`](address:8223) to avoid NMI
re-entry overhead. Otherwise installs the handler via
[`set_nmi_vector`](address:0D0E) (the `(A,Y)` pair becomes the
NMI dispatch target) and returns via `RTI`.""")
subroutine(0x8215, "nmi_error_dispatch",
    title="NMI error handler dispatch",
    description="""\
Common error/abort entry used by 11 call sites. The dispatch byte
at [`rx_src_net`](address:0D3E) doubles as a TX-state flag here:
bit 7 distinguishes whether the NMI handler reached this point on
an RX-error path or a TX not-listening path.

| `rx_src_net` bit 7 | Path |
|---|---|
| clear | RX error – full ADLC reset; return to idle listen |
| set   | TX not-listening – `JMP` [`tx_result_fail`](address:88E2) |""")
subroutine(0x8223, "nmi_data_rx_bulk",
    title="Data frame bulk read loop",
    description="""\
Reads data payload bytes from the RX FIFO and stores them into
the open port buffer at `(open_port_buf),Y`. Reads bytes in pairs
(like the scout data loop), checking SR2 between each pair.

- SR2 non-zero (FV or other) → completion via
  [`data_rx_complete`](address:8268).
- SR2 = 0 → RTI, wait for next NMI to continue.""")
subroutine(0x8268, "data_rx_complete",
    title="Data frame completion",
    description="""\
Reached when `SR2` non-zero during data RX (`FV` detected). Same
pattern as scout completion: disables `PSE` (`CR2=&84`, `CR1=&00`),
then tests `FV` and `RDA`. If `FV+RDA`, reads the last byte; if
extra data is available and buffer space remains, stores it.
Proceeds to send the final ACK via [`ack_tx`](address:82DF).""")
subroutine(0x8291, "nmi_data_rx_tube",
    title="NMI handler: data-frame RX into Tube buffer",
    description="""\
NMI continuation entry for the Tube data-RX path. Polls SR2 for
RDA, reads the next data byte from the ADLC RX FIFO, and writes it
to the Tube data register, advancing the Tube transfer pointer
each iteration. Tests for end-of-frame via FV and either continues
the tight inner loop or returns via `RTI`. Reached only via the
NMI vector after `install_tube_rx` configures the handler.""")
subroutine(0x82DF, "ack_tx",
    title="ACK transmission",
    description="""\
Sends a scout ACK or final ACK frame as part of the four-way
handshake. Tests bit 7 of [`rx_src_net`](address:0D3E) (used as
TX-flags here): if set this is a final ACK and completion runs
through [`tx_result_ok`](address:88DE). Otherwise configures
for TX (`CR1=&44`, `CR2=&A7`) and writes the ACK address frame:
destination station from [`scout_buf`](address:0D2E), destination
network from [`scout_src_net`](address:0D2F), source station
from the workspace copy [`tx_src_stn`](address:0D22), and
`src_net=0`. The ACK frame has no data payload -- just address
bytes.

After writing the address bytes to the TX FIFO, installs the next
NMI handler from `saved_nmi_lo`/`saved_nmi_hi` (saved by the
scout/data RX handler via [`ack_tx_write_dest`](address:82F8))
and sends `TX_LAST_DATA` (`CR2=&3F`) to close the frame.""")
subroutine(0x82F8, "ack_tx_write_dest",
    title="Begin ACK transmit: write destination address to ADLC",
    description="""\
First step of the four-byte ACK frame transmission. Saves the
caller-supplied `(A=lo, Y=hi)` next-NMI handler address into
`saved_nmi_lo` / `saved_nmi_hi`, loads the destination station
from [`scout_buf`](address:0D2E) and tests `SR1` bit 6 (`TDRA`,
TX Data Register Available) via `BIT adlc_cr1`. If `TDRA` is
clear the TX FIFO isn't ready and control branches to
[`dispatch_nmi_error`](address:833C) to abort.

When `TDRA` is set, writes the destination station and network
bytes (from [`scout_src_net`](address:0D2F)) into `adlc_tx`, then
installs [`nmi_ack_tx_src`](address:8316) as the next NMI handler
via [`set_nmi_vector`](address:0D0E) -- that handler will write
the source-address pair on the next NMI.

Two callers: [`send_data_rx_ack`](address:81A7)'s tail `JMP` and
[`imm_op_build_reply`](address:84F9).""",
    on_entry={"a": "low byte of next NMI handler",
              "y": "high byte of next NMI handler"})
subroutine(0x8316, "nmi_ack_tx_src",
    title="ACK TX continuation",
    description="""\
Continuation of ACK frame transmission, reached via NMI after
[`ack_tx_write_dest`](address:82F8) installed it as the next
handler. Reads our station ID from the workspace copy
[`tx_src_stn`](address:0D22), tests `TDRA` via `SR1`, and writes
`(station, network=0)` to the TX FIFO -- completing the 4-byte
ACK address header.

Then dispatches on [`rx_src_net`](address:0D3E) bit 7 (which the
caller uses as a TX-flags byte):

| Bit 7 | Action |
|---|---|
| set   | branch to `start_data_tx` to begin the data phase |
| clear | write `CR2=&3F` (TX_LAST_DATA) and fall through to [`post_ack_scout`](address:832D) |""")
subroutine(0x832D, "post_ack_scout",
    title="Post-ACK scout processing",
    description="""\
Called after the scout ACK has been transmitted. Processes the
received scout data stored in the buffer starting at
[`rx_src_stn`](address:0D3D) (scout-ACK destination
addresses). Checks the port byte at
[`rx_port`](address:0D40) against open receive blocks to find
a matching listener.

- **Match** – sets up the data-RX handler chain for the four-way-
  handshake data phase.
- **No match** – discards the frame.""")
subroutine(0x833F, "advance_rx_buffer_ptr",
    title="Advance RX buffer pointer after transfer",
    description="""\
Adds the transfer count to the RXCB buffer pointer (4-byte
addition). If a Tube transfer is active, re-claims the Tube
address and sends the extra RX byte via R3, incrementing the
Tube pointer by 1.

Reads:

- [`tx_flags`](address:0D4A) bit 1 – data transfer in progress
- [`tx_flags`](address:0D4A) bit 5 – Tube transfer
- 4-byte transfer count from `net_tx_ptr,Y` (`Y=8..&0B`)
- RXCB pointer at `(port_ws_offset),Y`

Updates the RXCB in place. Clobbers `A` and `Y`; preserves `X`
across the Tube branch (saved/restored via stack).""",
    on_exit={"a": "&FF when transfer was active, else preserved entry value"})
subroutine(0x8386, "nmi_post_ack_dispatch",
    title="Post-ACK frame-complete NMI handler",
    description="""\
Installed by `ack_tx_configure` via
[`saved_nmi_lo`](address:0D43) / [`saved_nmi_hi`](address:0D44).
Fires as an NMI after the ACK frame (CRC + closing flag) has been
fully transmitted by the ADLC. Dispatches on `scout_port`:

| `scout_port` | Control | Target |
|---|---|---|
| `≠ 0` | – | [`rx_complete_update_rxcb`](address:8395) (finalise data transfer, mark RXCB complete) |
| `0`   | `&82` (POKE) | [`rx_complete_update_rxcb`](address:8395) (same path) |
| `0`   | other | `imm_op_build_reply` |""")
subroutine(0x8395, "rx_complete_update_rxcb",
    title="Complete RX and update RXCB",
    description="""\
Called from [`nmi_post_ack_dispatch`](address:8386) after the
final ACK has been transmitted. Finalises the received data
transfer:

1. Calls [`advance_rx_buffer_ptr`](address:833F) to update the
   4-byte buffer pointer with the transfer count (and handle Tube
   re-claim if needed).
2. Stores the source station, network, and port into the RXCB.
3. ORs `&80` into the RXCB control byte (bit 7 = complete).

This is the **NMI-to-foreground synchronisation point**:
`wait_net_tx_ack` polls bit 7 of the RXCB control byte to detect
that the reply has arrived.

Falls through to [`discard_reset_rx`](address:83E5) to reset
the ADLC to idle RX-listen mode.""")
subroutine(0x83E5, "discard_reset_rx",
    title="Discard scout, reset ADLC, install RX-scout NMI",
    description="""\
Three-stage idle-restore chain:

1. [`discard_reset_listen`](address:83F2) – abandon any
   in-flight scout and release a held Tube claim.
2. [`reset_adlc_rx_listen`](address:83E8) – call
   `adlc_rx_listen` (reset `CR1`/`CR2` and re-arm RX).
3. [`set_nmi_rx_scout`](address:83EB) – install
   [`nmi_rx_scout`](address:809B) as the active NMI handler
   and `JMP` out via [`set_nmi_vector`](address:0D0E).

Used as the standard "something went wrong, get back to listening"
exit.""")
subroutine(0x83E8, "reset_adlc_rx_listen",
    title="Reset ADLC and install RX-scout NMI",
    description="""\
Tail of the [`discard_reset_rx`](address:83E5) chain entered
directly when no scout needs discarding. Calls `adlc_rx_listen`
to reset `CR1`/`CR2` to RX-only mode, then falls through to
[`set_nmi_rx_scout`](address:83EB).

Two inbound `JSR`s plus one fall-through (from
[`discard_reset_rx`](address:83E5)).""")
subroutine(0x83EB, "set_nmi_rx_scout",
    title="Install nmi_rx_scout as NMI handler",
    description="""\
Loads `(A=&9B, Y=&80)` -- the address of
[`nmi_rx_scout`](address:809B) -- and `JMP`s to
[`set_nmi_vector`](address:0D0E), which writes both bytes into
the NMI JMP-target slot at `nmi_jmp_lo`/`nmi_jmp_hi`. Tail of
the [`discard_reset_rx`](address:83E5) /
[`reset_adlc_rx_listen`](address:83E8) chain, used to put the
NMI vector back to scout-handling after a discard or reset.

Two callers: `&80CB` (after init) and `&80E2` (after error).""")
subroutine(0x83F2, "discard_reset_listen",
    title="Discard with Tube release",
    description="""\
Checks whether a Tube transfer is active by ANDing bit 1 of
[`tube_present`](address:0D63) with
[`rx_src_net`](address:0D3E) (`tx_flags`). If a Tube claim is
held, calls [`release_tube`](address:8448) to free it before
returning.

Used as the clean-up path after RXCB completion and after ADLC
reset to ensure no stale Tube claims persist.""")
subroutine(0x8400, "copy_scout_to_buffer",
    title="Copy scout data to port buffer (entry point)",
    description="""\
Five-instruction prologue that prepares to copy scout-payload
bytes (offsets `4..&0B`) from [`scout_buf`](address:0D2E) into the
open port buffer. Saves `X` on the stack, loads `X=4` (the first
scout-data offset) and `A=&02` (Tube-flag mask), then `BIT`s
[`rx_src_net`](address:0D3E) (`tx_flags`) so the immediately
following `BNE` in
[`save_acccon_for_shadow_ram`](address:8409) can dispatch:

| Bit 1 | Path |
|---|---|
| clear | fall through into `save_acccon_for_shadow_ram` (direct memory store via `(open_port_buf),Y`, with ACCCON saved/restored on Master 128) |
| set   | branch to [`copy_scout_via_tube`](address:8436) (Tube R3 write) |

Both paths walk the four-byte buffer pointer and end via
[`scout_copy_done`](address:842B) which restores `X` and returns.
Single caller: [`port_match_found`](address:8195) at `&81A4`.""")
subroutine(0x8448, "release_tube",
    title="Release Tube co-processor claim",
    description="""\
Tests bit 7 of [`prot_flags`](address:0099) -- the bit ANFS uses
to track whether the Tube is currently still claimed:

| Bit 7 | State | Action |
|---|---|---|
| set | already released | branch to `clear_release_flag` (skips the release call) |
| clear | claim held | `JSR tube_addr_data_dispatch` with `A=&82` to release the claim, then fall through |

Both paths end at `clear_release_flag` which `LSR`s `prot_flags`
(shifting bit 7 to 0) before returning.

Called after completed RX transfers and during discard paths to
ensure no stale Tube claims persist.

**Idempotent:** safe to call when the Tube has already been
released. Clobbers `A`; preserves `X` and `Y`.""",
    on_exit={"a": "clobbered"})
subroutine(0x8454, "immediate_op",
    title="Immediate operation handler (port = 0)",
    description="""\
Checks the control byte at [`scout_ctrl`](address:0D30) for
immediate-operation codes:

| Range | Op | Treatment |
|---|---|---|
| `< &81` or `> &88` | – | out of range; discarded |
| `&81`..`&86` | PEEK / POKE / JSR / UserProc / OSProc / HALT | gated by [`econet_flags`](address:0D61) immediate-op mask |
| `&87`..`&88` | CONTINUE / machine-type | bypass the mask check |

For `&81`..`&86`, converts the code to a 0-based index and tests
against the immediate-op mask at
[`econet_flags`](address:0D61) to determine whether this
station accepts the operation. If accepted, dispatches via
[`imm_op_dispatch_lo`](address:848B) (PHA/PHA/RTS).

Builds the reply by storing data length, station / network, and
control byte into the RX buffer header.""")

subroutine(0x848B, "imm_op_dispatch_lo",
    title="Immediate-op dispatch lo-byte table (8 entries)",
    description="""\
Eight low-byte entries at `&848B`-`&8492` indexed by the
immediate-op control byte (`&81`-`&88`) via
`LDA imm_op_dispatch_lo-&81,Y` at the dispatch site. Each entry is
the low byte of `(handler-1)` so PHA/PHA/RTS dispatch lands on the
handler. The high byte pushed by the dispatcher is constant
(`&84`), so all targets sit in `&84xx`. Per-entry inline comments
identify each control byte's handler.""")
for addr in range(0x848B, 0x8493):
    byte(addr)
expr(0x848B, "<(rx_imm_peek-1)")
expr(0x848C, "<(rx_imm_poke-1)")
expr(0x848D, "<(rx_imm_exec-1)")
expr(0x848E, "<(rx_imm_exec-1)")
expr(0x848F, "<(rx_imm_exec-1)")
expr(0x8490, "<(rx_imm_halt_cont-1)")
expr(0x8491, "<(rx_imm_halt_cont-1)")
expr(0x8492, "<(rx_imm_machine_type-1)")
comment(0x848B, "ctrl &81: PEEK", inline=True)
comment(0x848C, "ctrl &82: POKE", inline=True)
comment(0x848D, "ctrl &83: JSR", inline=True)
comment(0x848E, "ctrl &84: UserProc", inline=True)
comment(0x848F, "ctrl &85: OSProc", inline=True)
comment(0x8490, "ctrl &86: HALT", inline=True)
comment(0x8491, "ctrl &87: CONTINUE", inline=True)
comment(0x8492, "ctrl &88: machine-type", inline=True)

subroutine(0x8493, "rx_imm_exec",
    title="RX immediate: JSR / UserProc / OSProc setup",
    description="""\
Sets up the port buffer to receive remote-procedure data. Copies
the 2-byte remote address from [`scout_data`](address:0D32)
into the execution-address workspace at
[`exec_addr_lo`](address:0D66) / [`exec_addr_hi`](address:0D67),
then jumps to the common data-receive path at `&81C1`.

Used for operation types `&83` (JSR), `&84` (UserProc), and
`&85` (OSProc).""")
subroutine(0x84B1, "rx_imm_poke",
    title="RX immediate: POKE setup",
    description="""\
Sets up workspace offsets for receiving POKE data:
`port_ws_offset = &2E`, `rx_buf_offset = &0D`. Jumps to the
common data-receive path at `&81AF`.""")
subroutine(0x84BC, "rx_imm_machine_type",
    title="RX immediate: machine-type query",
    description="""\
Sets up the response buffer for a machine-type query immediate
operation (4-byte response: machine code + version digits). Falls
through to [`set_rx_buf_len_hi`](address:84BE) to configure
the buffer dimensions, then branches to `set_tx_reply_flag`.""")
subroutine(0x84CE, "rx_imm_peek",
    title="RX immediate: PEEK setup",
    description="""\
Writes `&0D2E` to `port_ws_offset` / `rx_buf_offset`, sets
`scout_status = 2`, then calls
[`tx_calc_transfer`](address:8900) to send the PEEK response
data back to the requesting station.""")
subroutine(0x8512, "setup_sr_tx",
    title="Save TX op type and update workspace ACR-format byte",
    description="""\
Stores the TX operation type in [`tx_op_type`](address:0D65).

| Op code | Path |
|---|---|
| `≥ &86` (HALT / CONTINUE / machine-type) | branch forward to the ACCCON IRR set; the workspace byte is left untouched |
| `< &86` | load [`ws_0d68`](address:0D68), copy it to [`ws_0d69`](address:0D69) (preserved for later restore), `ORA` in bits 2-4 (the SR-mode-2 mask in System-VIA ACR layout), write the modified value back to `ws_0d68` |

The byte at `ws_0d68` carries an ACR-format flag layout left over
from 4.18, which used the same op-code dispatch to update the
*live* System VIA ACR. In 4.21 the byte stays in workspace --
nothing in this ROM flushes it to the live VIA. Single caller
(`&83E2` in [`scout_complete`](address:8112)).""",
    on_entry={"a": "TX operation type"})
subroutine(0x852C, "advance_buffer_ptr",
    title="Increment 4-byte receive-buffer pointer",
    description="""\
Adds 1 to the 4-byte counter at `&A2..&A5` (`port_buf_len` lo/hi,
`open_port_buf` lo/hi), cascading overflow through all four
bytes. Called after each byte is stored during scout-data copy
and data-frame reception to track the current write position in
the receive buffer.

Preserves `A`, `X`, `Y` (uses `INC zp` throughout).""",
    on_exit={"a, x, y": "preserved (INC zp only)"})
subroutine(0x84F9, "imm_op_build_reply",
    title="Build immediate-operation reply header",
    description="""\
Writes the reply-frame header for a port-0 immediate operation
into the RX buffer at offsets `&7F..&81`:

| RX offset | Source | Meaning |
|---|---|---|
| `&7F` | `port_buf_len + &80` | reply data length (raw count + header offset) |
| `&80` | [`scout_buf`](address:0D2E) | requesting station |
| `&81` | [`scout_src_net`](address:0D2F) | requesting network |

Then loads the control byte from
[`scout_ctrl`](address:0D30) into `A` and falls through into
[`setup_sr_tx`](address:8512), which stores `A` as
[`tx_op_type`](address:0D65) and configures the ADLC for the SR
phase of the reply. Reached via the immediate-op dispatch path.""")
# Reached only via PHA/PHA/RTS dispatch from the tx_done_dispatch
# table; needs an explicit entry().
entry(0x8540)
subroutine(0x8540, "tx_done_jsr",
    title="TX done: remote JSR execution",
    description="""\
Pushes ([`tx_done_exit`](address:8582) ` - 1`) on the stack so
`RTS` returns to [`tx_done_exit`](address:8582) when the remote
routine completes, then does `JMP` indirect through
[`exec_addr_lo`](address:0D66) to call the remote-supplied JSR
target. When that routine returns via `RTS`, control resumes at
[`tx_done_exit`](address:8582) which tidies up TX state.""")
subroutine(0x8549, "tx_done_econet_event",
    title="TX done: fire Econet event",
    description="""\
Handler for TX operation type `&84`. Loads the remote address
from [`exec_addr_lo`](address:0D66) /
[`exec_addr_hi`](address:0D67) into `X` / `A` and sets `Y=8`
(Econet event number), then falls through to `tx_done_fire_event`
to call OSEVEN.

Reached only via `PHA`/`PHA`/`RTS` dispatch from
[`tx_done_dispatch_lo`](address:853B) / hi. The dispatcher
pushed the caller's `X` and `Y` onto the stack before
transferring control, and the shared
[`tx_done_exit`](address:8582) restores them via
`PLA`/`TAY`/`PLA`/`TAX` before returning `A=0`.""",
    on_exit={"a": "0 (success status)",
             "x, y": "restored from stack via tx_done_exit"})
subroutine(0x8557, "tx_done_os_proc",
    title="TX done: OSProc call",
    description="""\
Calls the ROM service entry point with
`X = `[`exec_addr_lo`](address:0D66)`, Y = `[`exec_addr_hi`](address:0D67).
This invokes an OS-level procedure on behalf of the remote
station, then exits via [`tx_done_exit`](address:8582).

Reached only via `PHA`/`PHA`/`RTS` dispatch from
[`tx_done_dispatch_lo`](address:853B) / hi.""",
    on_exit={"a": "0 (success status)",
             "x, y": "restored from stack via tx_done_exit"})
subroutine(0x8563, "tx_done_halt",
    title="TX done: HALT",
    description="""\
Sets bit 2 of [`econet_flags`](address:0D61), enables
interrupts, and spin-waits until bit 2 is cleared (by a CONTINUE
from the remote station). If bit 2 is already set, skips to exit.

Reached only via `PHA`/`PHA`/`RTS` dispatch from
[`tx_done_dispatch_lo`](address:853B) / hi. Falls through to
[`tx_done_continue`](address:857A) after the spin completes;
on the already-halted path it branches directly to
[`tx_done_exit`](address:8582).""",
    on_exit={"a": "0 (success status, set by tx_done_exit)",
             "i flag": "interrupts enabled (CLI inside the spin)",
             "x, y": "restored from stack via tx_done_exit"})
subroutine(0x857A, "tx_done_continue",
    title="TX done: CONTINUE",
    description="""\
Clears bit 2 of [`econet_flags`](address:0D61), releasing any
station that is halted and spinning in
[`tx_done_halt`](address:8563).

Reached either as a fall-through from
[`tx_done_halt`](address:8563) or directly via
`PHA`/`PHA`/`RTS` dispatch from
[`tx_done_dispatch_lo`](address:853B) / hi. Falls through to
[`tx_done_exit`](address:8582) which restores `X` and `Y`
from the stack and returns `A=0`.""",
    on_exit={"a": "0 (success status)",
             "x, y": "restored from stack via tx_done_exit"})
subroutine(0x8582, "tx_done_exit",
    title="Shared TX-done exit: restore X/Y, return A=0",
    description="""\
Common cleanup tail used by every entry in the
[`tx_done_dispatch_lo`](address:853B) table. Pulls the saved
`Y` and `X` off the stack (the dispatcher pushed them before the
`PHA`/`PHA`/`RTS` jump), loads `A=0` (success status), and `RTS`
to the caller.

Five inbound refs: a tail-jump from `&8042` (the SVC 5 IRQ-check
path in [`svc5_irq_check`](address:8028)), plus the JMPs at
`&8554`, `&8560`, `&8568`, and the fall-through at `&8578`.""",
    on_exit={"a": "0 (success status)",
             "x, y": "restored from stack"})
subroutine(0x8589, "tx_begin",
    title="Begin TX operation",
    description="""\
Main TX initiation entry point (called via the NETV trampoline).

1. Copies destination station / network from the TXCB to the
   scout buffer.
2. Dispatches: control byte `≥ &81` → immediate-op setup; else
   normal data transfer.
3. Calculates transfer sizes via
   [`tx_calc_transfer`](address:8900); copies extra
   parameters into the workspace.
4. Enters the INACTIVE polling loop at
   [`inactive_poll`](address:85F1).""")
subroutine(0x85F1, "inactive_poll",
    title="INACTIVE polling loop",
    description="""\
Entry point for the Econet line-idle detection loop.

1. Saves the TX index in [`rx_remote_addr`](address:0D41).
2. Pushes two timeout-counter bytes onto the stack.
3. Loads `Y = &E7` (CR2 value for TX preparation).
4. Loads the INACTIVE bit mask (`&04`) into `A`.
5. Falls through to [`intoff_test_inactive`](address:85FC)
   to begin polling `SR2` with interrupts disabled.""",
    on_exit={"y": "&E7 (CR2 value for tx_prepare)"})
subroutine(0x85FC, "intoff_test_inactive",
    title="Disable NMIs and test INACTIVE",
    description="""\
Disables NMIs via two `BIT` reads of
[`master_intoff`](address:FE38) (the Master 128 INTOFF register;
the Model-B equivalent reads `econet_station_id` at &FE18 for the
same side-effect), then polls `SR2` for the INACTIVE bit (bit 2):

| `SR2` INACTIVE | Action |
|---|---|
| set   | read `SR1`, write `CR2=&67` to clear status, then test `CTS` (`SR1` bit 4); if `CTS` present, branch to [`tx_prepare`](address:864A) |
| clear | re-enable NMIs via [`master_inton`](address:FE3C) (INTON) and decrement the 3-byte timeout counter on the stack |

On timeout, falls through to
[`tx_line_jammed`](address:8630).""",
    on_entry={"a": "&04 (INACTIVE bit mask)",
              "y": "&E7 (CR2 value for tx_prepare)"})
subroutine(0x862C, "tx_bad_ctrl_error",
    title="Raise TX 'Bad control byte' (&44) error",
    description="""\
Loads error code `&44` ("Bad control") and ALWAYS-branches to
`store_tx_error`, which records it in the TX control block and
finishes the TX attempt.

Reached from three early-validation sites in
[`tx_begin`](address:8589) (`&859E`, `&85CE`, `&85D2`) when the
operation type is out of range.""",
    on_exit={"a": "&44 (TX 'Bad control' error code)"})
subroutine(0x8630, "tx_line_jammed",
    title="TX timeout error handler (Line Jammed)",
    description="""\
Reached when the [`inactive_poll`](address:85F1) /
[`intoff_test_inactive`](address:85FC) loop times out without
detecting a quiet line.

1. Writes `CR2=&07` (`FC_TDRA | 2_1_BYTE | PSE`) to abort the TX
   attempt.
2. Pulls the 3-byte timeout state from the stack.
3. Stores error code `&40` ("Line Jammed") in the TX control
   block via `store_tx_error`.""")
subroutine(0x864A, "tx_prepare",
    title="TX preparation",
    description="""\
Configures the ADLC for frame transmission and dispatches to the
control-byte handler.

1. Writes `CR2 = Y` (`&E7`) and `CR1 = &44` to enable TX with
   interrupts (`RX_RESET` + transmit-IRQ enable).
2. Installs [`nmi_tx_data`](address:86E7) as the next NMI handler
   by writing `&E7,&86` directly into `nmi_jmp_lo` / `nmi_jmp_hi`.
3. Sets bit 7 of [`prot_flags`](address:0099) (Tube-claimed
   marker, paired with [`release_tube`](address:8448)) via
   `SEC` / `ROR prot_flags`.
4. `BIT master_inton` re-enables NMIs so `TDRA` can fire.

Then dispatches on [`tx_port`](address:0D25):

| `tx_port` | Path |
|---|---|
| non-zero | branch to `setup_data_xfer` (standard data transfer) |
| zero (immediate op) | look up `tx_flags` / `tx_length` from `tx_flags_table` / `tx_length_table` indexed by [`tx_ctrl_byte`](address:0D24), push `&86` (high byte) and `tx_ctrl_dispatch_lo[Y-&81]` (low byte) and `RTS` to the control-byte handler |

The 4-byte destination-address write to the TX FIFO happens in
the dispatched-to handler (e.g. `setup_data_xfer`,
[`tx_ctrl_machine_type`](address:8686), etc.), not here.""",
    on_entry={"y": "&E7 (CR2 prep value)"})
subroutine(0x8686, "tx_ctrl_machine_type",
    title="TX ctrl: machine-type query setup",
    description="""\
Handler for control byte `&88`. Sets `scout_status = 3` and
branches to `store_status_copy_ptr`, skipping the 4-byte address
addition (no address parameters needed for a machine-type query).

Reached only via `PHA`/`PHA`/`RTS` dispatch from
[`tx_ctrl_dispatch_lo`](address:867E) entry `&88`.""",
    on_exit={"a": "3 (scout_status for machine type query)"})
subroutine(0x868A, "tx_ctrl_peek",
    title="TX ctrl: PEEK transfer setup",
    description="""\
Sets `A=3` (scout_status for PEEK) and branches to
[`tx_ctrl_store_and_add`](address:8690) to store the status
and perform the 4-byte transfer-address addition.""",
    on_exit={"a": "3 (scout_status for PEEK)"})
subroutine(0x868E, "tx_ctrl_poke",
    title="TX ctrl: POKE transfer setup",
    description="""\
Sets `A=2` (scout_status for POKE) and falls through to
[`tx_ctrl_store_and_add`](address:8690) to store the status
and perform the 4-byte transfer-address addition.""",
    on_exit={"a": "2 (scout_status for POKE)"})
subroutine(0x8690, "tx_ctrl_store_and_add",
    title="TX ctrl: store status and add transfer address",
    description="""\
Shared path for PEEK (`A=3`) and POKE (`A=2`):

1. Stores `A` as the scout status byte at
   [`rx_port`](address:0D40).
2. Performs a 4-byte addition with carry propagation. For
   `Y=&0C..&0F` it adds `(nmi_tx_block),Y` (i.e. TXCB bytes
   12..15 from the block pointed to by
   [`nmi_tx_block`](address:00A0)) into `tx_addr_base,Y` --
   `tx_addr_base+&0C..&0F` is the 4-byte transfer-length
   workspace at [`tx_data_len`](address:0D2A)..&0D2D.
3. Falls through to [`tx_ctrl_proc`](address:86A2) which
   checks the loop boundary, then continues to
   [`tx_calc_transfer`](address:8900) and `tx_ctrl_exit`.""",
    on_entry={"a": "scout status (3=PEEK, 2=POKE)"})
subroutine(0x86A2, "tx_ctrl_proc",
    title="TX ctrl: tail of address-add loop + setup_data_xfer entry",
    description="""\
Tail of the 4-byte transfer-address addition loop that started in
[`tx_ctrl_store_and_add`](address:8690): `CPY #&10` ends the
loop when Y reaches `&10`, `PLP` restores the saved carry, and
`BNE` skips the buffer-setup code if the transfer size is zero.

Falls through (or is reached via the dispatch from
[`tx_prepare`](address:864A) when port != 0) to
`setup_data_xfer` at `&86A9`, which dispatches between broadcast
and unicast based on whether `tx_dst_stn` and `tx_dst_net` are
both `&FF`.""")
subroutine(0x86E7, "nmi_tx_data",
    title="NMI TX data handler",
    description="""\
Writes 2 bytes per NMI invocation to the TX FIFO at
[`adlc_tx`](address:FEA2). Uses `BIT`
[`adlc_cr1`](address:FEA0)
on `SR1` to test `TDRA` (`V` flag = bit 6) and `IRQ` (`N` flag =
bit 7).

After writing 2 bytes, checks if the frame is complete:

| `SR1` bit 7 (`IRQ`) | Action |
|---|---|
| set   | tight loop: write 2 more bytes without returning from NMI |
| clear | return via `RTI` and wait for the next NMI |""")
subroutine(0x8723, "tx_last_data",
    title="TX_LAST_DATA and frame completion",
    description="""\
Signals end of TX frame by writing `CR2=&3F` (TX_LAST_DATA), then
installs [`nmi_tx_complete`](address:872F) as the next NMI
handler.

`CR2=&3F` = `%0011_1111`, with each bit selecting an ADLC
control function:

| Bit | Mnemonic | Effect |
|-----|----------|--------|
| 7   | (RTS)    | **0** – drops RTS after frame |
| 6   | (CLR_TX_ST) | **0** – do *not* clear TX status |
| 5   | CLR_RX_ST | clears `fv_stored_` (prepares for RX of reply) |
| 4   | TX_LAST_DATA | tells the ADLC this is the final data byte |
| 3   | FLAG_IDLE | send flags / idle after the frame |
| 2   | FC_TDRA  | force clear TDRA |
| 1   | 2_1_BYTE | two-byte transfer mode |
| 0   | PSE      | prioritised status enable |

The routine exits via `JMP` to
[`set_nmi_vector`](address:0D0E), which installs
[`nmi_tx_complete`](address:872F) and falls through to
[`nmi_rti`](address:0D14). The `BIT` of
[`econet_nmi_enable`](address:FE20) (INTON) inside
[`nmi_rti`](address:0D14) creates the /NMI edge for the
frame-complete interrupt – essential because the ADLC IRQ may
transition atomically from TDRA to frame-complete without
de-asserting in between.""")
subroutine(0x872F, "nmi_tx_complete",
    title="TX completion: switch to RX mode",
    description="""\
Called via NMI after the frame (including CRC and closing flag)
has been fully transmitted. Writes `CR1=&82` (`TX_RESET | RIE`)
to clear `RX_RESET` and enable RX interrupts – the **TX-to-RX
pivot** in the four-way handshake. The scout ACK can only be
received after this point.

Full `CR1` sequence through a handshake:

| Step | `CR1` | Meaning |
|---|---|---|
| 1 | `&44` | scout TX |
| 2 | `&82` | await scout ACK |
| 3 | `&44` | data TX |
| 4 | `&82` | await data ACK |

Dispatches on [`rx_src_net`](address:0D3E) flags:

| Flag | Action |
|---|---|
| bit 6 set (broadcast) | jump to [`tx_result_ok`](address:88DE) |
| bit 0 set (handshake data pending) | jump to [`handshake_await_ack`](address:8886) |
| both clear | install [`nmi_reply_scout`](address:874B) for scout ACK reception |""")
subroutine(0x874B, "nmi_reply_scout",
    title="RX reply-scout handler",
    description="""\
NMI handler installed before the reply-scout reception phase.
Tests `SR2` bit 0 (`AP`) for an incoming address; on `AP` clear
falls through to `tx_error`. Otherwise reads the first RX byte
(destination station) and compares it against the workspace copy
[`tx_src_stn`](address:0D22). On mismatch branches to
[`reject_reply`](address:8773); on match installs
[`nmi_reply_cont`](address:875F) as the next NMI handler via
[`install_nmi_handler`](address:0D11) (low-byte only -- the high
byte stays at `&87`).""")
subroutine(0x875F, "nmi_reply_cont",
    title="RX reply continuation handler",
    description="""\
Reads the second byte of the reply scout (destination network)
and validates it is zero (local network). Loads `A=&76`, the low
byte of [`nmi_reply_validate`](address:8776), to install it as
the next NMI handler.

**Optimisation:** before installing, checks `SR1` bit 7 (`IRQ`
still asserted) via `BIT adlc_cr1` / `BMI`. When `IRQ` is still
set the next byte is already in the FIFO, so the routine falls
through directly to [`nmi_reply_validate`](address:8776) without
an intermediate `RTI`, avoiding NMI re-entry overhead for short
frames where all bytes arrive in quick succession.""")
subroutine(0x8773, "reject_reply",
    title="Abandon reply scout (1-instruction trampoline)",
    description="""\
Single `JMP` to [`tx_result_fail`](address:88E2). Acts as a
near-target for the `BPL`/`BNE` exits scattered through
[`nmi_reply_scout`](address:874B),
[`nmi_reply_validate`](address:8776), and
[`nmi_scout_ack_src`](address:87BE) that need to abort the
reply path – the unconditional `JMP` at `&8773` takes them to
[`tx_result_fail`](address:88E2) (which stores the error and
returns to idle).

Seven inbound refs in total (one `JSR` plus six branches).""")
subroutine(0x8776, "nmi_reply_validate",
    title="RX reply validation (Path 2 for FV/PSE interaction)",
    description="""\
Reads the source station and source network from the reply scout
and validates them against the original TX destination
([`tx_dst_stn`](address:0D20) /
[`tx_dst_net`](address:0D21)).

1. Check SR2 bit 7 (RDA) -- must see data available.
2. Read source station, compare to `tx_dst_stn`.
3. Read source network, compare to `tx_dst_net`.
4. Check SR2 bit 1 (FV) -- must see frame complete.

If all checks pass, the reply scout is valid and the ROM proceeds
to send the scout ACK (`CR2=&A7` for RTS, `CR1=&44` for TX mode).""")
subroutine(0x87BE, "nmi_scout_ack_src",
    title="TX scout ACK: write source address",
    description="""\
Continuation of the TX-side scout ACK. Reads our station ID from
the workspace copy [`tx_src_stn`](address:0D22), tests `TDRA`
via `SR1`, and writes `(station, network=0)` to the TX FIFO.

Then dispatches on bit 1 of [`rx_src_net`](address:0D3E) to
select the next NMI handler:

| Bit 1 | Handler |
|---|---|
| set   | immediate-op data NMI handler |
| clear | normal [`nmi_tx_data`](address:86E7) |

Installs the chosen handler via
[`set_nmi_vector`](address:0D0E). Shares the
[`tx_check_tdra_ready`](address:87C4) entry with
[`ack_tx`](address:82DF).""")
subroutine(0x87CE, "data_tx_begin",
    title="Begin data-frame TX: install nmi_data_tx or alt",
    description="""\
Tests bit 1 of [`rx_src_net`](address:0D3E)
([`tx_flags`](address:0D4A)):

| Bit 1 | Path |
|---|---|
| set (immediate-op) | branch to `install_imm_data_nmi` to use the alternative handler |
| clear | install the [`nmi_data_tx`](address:87E3) alt-entry at `&87EB` (lo=`&EB`, hi=`&87`) into the NMI vector. The alt-entry skips the page-counter check and goes straight to the byte-count load |

Single caller (`&8339` inside [`ack_tx`](address:82DF)).""")
subroutine(0x87E3, "nmi_data_tx",
    title="TX data phase: send payload",
    description="""\
NMI handler that transmits the data payload of a four-way
handshake. Loads bytes from `(open_port_buf),Y` (or from Tube
R3 in the immediate-op variant), writing pairs to the TX FIFO.
After each pair, decrements the byte counters
(`port_buf_len`/`port_buf_len_hi`):

| Condition | Action |
|---|---|
| `port_buf_len_hi = 0` (final partial page) | branch to `data_tx_last` (internal label) to send the remaining bytes and tail-call [`tx_last_data`](address:8723) |
| count > 0, `SR1` IRQ still set | tight loop: write another pair without returning from NMI |
| count > 0, `SR1` IRQ clear | return via `RTI` and wait for next NMI |

The alt-entry at `&87EB` (used by
[`data_tx_begin`](address:87CE)) skips the page-counter check
and starts at the byte-count load.""")
subroutine(0x8845, "nmi_data_tx_tube",
    title="NMI handler: TX FIFO write from Tube buffer",
    description="""\
NMI continuation handler used during TX of a Tube-sourced data
frame. Tests SR1 TDRA via `BIT
econet_control1_or_status1`, writes the next pair of bytes from
the Tube buffer to the ADLC TX FIFO (the `tube_tx_fifo_write`
shared body at `&8848`), and either continues the tight inner loop
on a continuing IRQ or returns via `RTI`. Reached only via the NMI
vector after [`tx_prepare`](address:864A) installs it.""")
subroutine(0x8886, "handshake_await_ack",
    title="Four-way handshake: switch to RX for final ACK",
    description="""\
Called via JMP from [`nmi_tx_complete`](address:872F) when bit 0
of [`tx_flags`](address:0D4A) is set (four-way handshake in
progress). Writes `CR1=&82` (`TX_RESET|RIE`) to switch the ADLC
from TX mode to RX mode, listening for the final ACK from the
remote station. Installs [`nmi_final_ack`](address:8892) as the
next NMI handler via [`set_nmi_vector`](address:0D0E).""")
subroutine(0x8892, "nmi_final_ack",
    title="RX final ACK handler",
    description="""\
Receives the final ACK in a four-way handshake. Same validation
pattern as [`nmi_reply_validate`](address:8776):

1. Check AP, read dest_stn, compare to our station.
2. Check RDA, read dest_net, validate = 0.
3. Check RDA, read src_stn / src_net, compare to TX dest.
4. Check FV for frame completion.

On success, stores result=0 via
[`tx_result_ok`](address:88DE). On failure, error &41.""")
subroutine(0x88A6, "nmi_final_ack_net",
    title="NMI handler: final-ACK source-net validation",
    description="""\
NMI continuation entry installed by `nmi_final_ack`. Polls SR2 for
RDA, reads the source-network byte from the ADLC RX FIFO, and
compares with the original TX destination network (`tx_dst_net`,
`&0D21`). On mismatch, branches to
[`tx_result_fail`](address:88E2). On match, falls through into
[`nmi_final_ack_validate`](address:88BA) for the source-station
check. Reached only via the NMI vector (no static caller).""",
    on_exit={"a": "source-network byte read from FIFO"})
subroutine(0x88BA, "nmi_final_ack_validate",
    title="Final ACK validation",
    description="""\
Continuation of [`nmi_final_ack`](address:8892). Tests `SR2`
for `RDA`, then reads the source station and source network
bytes from the RX FIFO, comparing each against the original TX
destination at [`tx_dst_stn`](address:0D20) and
[`tx_dst_net`](address:0D21). Finally tests `SR2` bit 1
(`FV`) for frame completion.

Any mismatch or missing `FV` branches to
[`tx_result_fail`](address:88E2). On success, falls through
to [`tx_result_ok`](address:88DE).""")
subroutine(0x88DE, "tx_result_ok",
    title="TX completion handler",
    description="""\
Loads `A=0` (success) and branches unconditionally to
[`tx_store_result`](address:88E4) (`BEQ` is always taken since
A=0, skipping the `tx_result_fail` body at &88E2). This two-
instruction entry point exists so that `JMP` sites can target
the success path without needing to set `A`. Called from
[`ack_tx`](address:82DF) for final-ACK completion and from
[`nmi_tx_complete`](address:872F) for immediate-op completion
where no ACK is expected.""",
    on_exit={"a": "0 (TX success)"})
subroutine(0x88E2, "tx_result_fail",
    title="TX failure: not listening",
    description="""\
Loads error code `&41` ("not listening") and falls through to
[`tx_store_result`](address:88E4). The most common TX-error
path – reached from 11 sites across the final-ACK validation
chain when the remote station doesn't respond or the frame is
malformed.""",
    on_exit={"a": "&41 ('not listening' TX error)"})
subroutine(0x88E4, "tx_store_result",
    title="TX result store and completion",
    description="""\
Stores the TX result code (in `A`) at offset 0 of the TX control
block via `(nmi_tx_block),Y=0`. Sets
[`tx_complete_flag`](address:0D60) to `&80` to signal TX
completion to the foreground polling loop. Then jumps to
[`discard_reset_rx`](address:83E5) for a full ADLC reset and
return to idle RX-listen mode.""",
    on_entry={"a": "result code (0=success, &40=jammed, &41=not listening)"})
subroutine(0x8900, "tx_calc_transfer",
    title="Calculate transfer size and reclaim Tube buffer",
    description="""\
Inspects `RXCB[6..7]` (buffer end address byte 2 and high) to
detect a Tube buffer (high=`&FF`, byte 2 in `[&FE, &FF]`).

| Buffer type | Action |
|---|---|
| Tube | compute 4-byte transfer size by subtracting `RXCB[8..&B]` (start) from `RXCB[4..7]` (end); store via `(port_ws_offset),Y`; re-claim Tube via `JSR &0406` with claim type `&C2` |
| Non-Tube | fall through to `fallback_calc_transfer` for a 1-byte size subtraction without the Tube reclaim |

Three callers: [`scout_complete`](address:8112) (`&819A`),
[`rx_imm_peek`](address:84CE) (`&84DB`),
[`tx_ctrl_proc`](address:86A2) (`&86DD`).""",
    on_entry={"y": "0 -- caller convention"},
    on_exit={"a": "transfer status",
             "c": "set if Tube address claimed, clear otherwise"})
subroutine(0x898C, "adlc_full_reset",
    title="ADLC full reset",
    description="""\
Performs a full ADLC hardware reset:

1. Writes `CR1=&C1` (`TX_RESET | RX_RESET | AC`) to put both TX
   and RX sections in reset with address-control enabled.
2. Configures `CR4=&1E` (8-bit RX word, abort extend, NRZ
   encoding).
3. Configures `CR3=&00` (no loopback, no AEX, NRZ, no DTR).
4. Falls through to [`adlc_rx_listen`](address:899B) to
   re-enter RX-listen mode.""",
    on_entry={},
    on_exit={"a, x, y": "clobbered"})
subroutine(0x899B, "adlc_rx_listen",
    title="Enter RX-listen mode",
    description="""\
Configures the ADLC for passive RX-listen mode:

| Register | Value | Meaning |
|---|---|---|
| `CR1` | `&82` | `TX_RESET \\| RIE` – TX section held in reset, RX interrupts enabled |
| `CR2` | `&67` | `CLR_TX_ST \\| CLR_RX_ST \\| FC_TDRA \\| 2_1_BYTE \\| PSE` – clear all pending status, enable prioritised status |

This is the idle state where the ADLC listens for incoming scout
frames via NMI.""",
    on_entry={},
    on_exit={"a, x": "clobbered (control byte writes)",
             "y": "preserved"})
subroutine(0x89A6, "wait_idle_and_reset",
    title="Wait for idle NMI state and reset Econet",
    description="""\
Service-13 (`&0D`) handler -- the post-hard-reset Econet
shutdown path. Reached via
[`svc_dispatch`](address:8E61) slot &0D. Checks
[`econet_init_flag`](address:0D62) to see if Econet has been
initialised; if not, skips straight to
[`adlc_rx_listen`](address:899B). Otherwise spins in a tight
loop comparing the NMI handler vector at
[`nmi_jmp_lo`](address:0D0C) /
[`nmi_jmp_hi`](address:0D0D) against the address of
[`nmi_rx_scout`](address:809B) to wait until the in-flight
NMI handler chain has unwound back to scout-listening.

When the NMI vector matches `nmi_rx_scout` again, falls through
to [`save_econet_state`](address:89B9) to clear the initialised
flags and re-enter RX-listen mode. (Service &0B 'NMI release'
is handled by the separate [`econet_restore`](address:806C).)""",
    on_entry={"a": "13 (service call number, &0D)"},
    on_exit={"a, x, y": "clobbered"})
subroutine(0x89B9, "save_econet_state",
    title="Reset Econet flags and enter RX-listen",
    description="""\
Disables NMIs via `BIT master_intoff` (the Master 128 dedicated
INTOFF at &FE38), then clears
[`tx_complete_flag`](address:0D60) and
[`econet_init_flag`](address:0D62) by storing the current `A`
value. Sets `Y=5` (service-call workspace page) and jumps to
[`adlc_rx_listen`](address:899B) to configure the ADLC for
passive listening.

Used during the wait-idle-and-reset path (svc &0D) to safely
tear down the Econet state before another ROM can claim the
NMI workspace.""",
    on_entry={"a": "value to store into tx_complete_flag / "
              "econet_init_flag (typically 0 to clear)"},
    on_exit={"y": "5 (service-call workspace page)"})
subroutine(0x89CA, "nmi_bootstrap_entry",
    title="Bootstrap NMI entry point (in ROM)",
    description="""\
An alternate NMI handler that lives in the ROM itself rather than
in the RAM shim at the start of the NFS workspace block. Unlike
the RAM shim (which uses a self-modifying `JMP` to dispatch to
different handlers), this one hardcodes
`JMP `[`nmi_rx_scout`](address:809B). Used as the initial
NMI handler before the workspace has been properly set up during
initialisation.

Same sequence as the RAM shim:

```6502
BIT master_intoff      ; INTOFF (Master 128 dedicated register)
PHA
TYA
PHA
LDA #romsel-bank
STA romsel
JMP nmi_rx_scout
```

The `BIT` of [`econet_station_id`](address:FE18) (INTOFF) at
entry and `BIT` of [`econet_nmi_enable`](address:FE20) (INTON)
before `RTI` in [`nmi_rti`](address:0D14) are essential for
edge-triggered NMI re-delivery.

The 6502 /NMI is falling-edge triggered; the Econet NMI-enable
flip-flop (IC97) gates the ADLC IRQ onto /NMI. INTOFF clears the
flip-flop, forcing /NMI high; INTON sets it, allowing the ADLC
IRQ through. This creates a guaranteed high-to-low edge on /NMI
even when the ADLC IRQ is continuously asserted (e.g. when it
transitions atomically from TDRA to frame-complete without
de-asserting). Without this mechanism,
[`nmi_tx_complete`](address:872F) would never fire after
[`tx_last_data`](address:8723).""")
subroutine(0x89D8, "rom_set_nmi_vector",
    title="ROM copy of set_nmi_vector + nmi_rti",
    description="""\
ROM-resident version of the NMI-exit sequence; also the source
for the initial copy to RAM at
[`set_nmi_vector`](address:0D0E).

| RAM target | Function |
|---|---|
| [`set_nmi_vector`](address:0D0E) | writes both hi and lo bytes of the `JMP` target at [`nmi_jmp_lo`](address:0D0C) / [`nmi_jmp_hi`](address:0D0D) |
| [`nmi_rti`](address:0D14) | restores the original ROM bank, pulls `Y` and `A` from the stack, then `BIT` of [`econet_nmi_enable`](address:FE20) (INTON) to re-enable the NMI flip-flop before `RTI` |

The INTON creates a guaranteed falling edge on /NMI if the ADLC
IRQ is already asserted, ensuring the next handler fires
immediately.""")
subroutine(0x8B00, "scan_remote_keys",
    title="Scan keyboard for remote-operation keys",
    description="""\
Uses OSBYTE `&7A` with `Y=&7F` to check whether remote-operation
keys (`&CE`..`&CF`) are currently pressed. If neither key is
detected, clears `svc_state` and `nfs_workspace` to zero via the
`clear_svc_and_ws` entry point (also used directly by
[`cmd_roff`](address:8AEA)). Called by `check_escape`.

`X` is saved into `nfs_workspace` across the OSBYTE call and
restored each iteration – the loop reuses `A` as the key-code
counter without needing `X`. `clear_svc_and_ws` is also entered
directly (label) by [`cmd_roff`](address:8AEA) with no
register pre-conditions.""",
    on_entry={"x": "preserved by being saved to nfs_workspace and "
              "reloaded each iteration (no other preconditions)"},
    on_exit={"a": "0 (when no key pressed -- the cleared path)",
             "x": "may be modified by OSBYTE",
             "y": "&7F (left over from OSBYTE call setup)"})
subroutine(0x8B18, "save_text_ptr",
    title="Save OS text pointer for later retrieval",
    description="""\
Copies `&F2`/`&F3` (`os_text_ptr`) into `fs_crc_lo` /
`fs_crc_hi`. Called by [`svc_4_star_command`](address:8C42)
and [`svc_9_help`](address:8C51) before attempting command
matches, and by `match_fs_cmd` during iterative help-topic
matching. Preserves `A` via `PHA`/`PLA`.""",
    on_exit={"a": "preserved"})
subroutine(0x8BBB, "help_print_nfs_cmds",
    title="*HELP NFS topic: print NFS-specific commands",
    description="""\
Loads `X=&35` (the offset of the first NFS-specific command in
`cmd_table_fs`) and tail-falls into
[`print_cmd_table`](address:8BC6) to emit the listing. Single
caller (the `*HELP` topic dispatch at `&8C6E`).""",
    on_exit={"x": "&35 + advance through the table"})
subroutine(0x8BC6, "print_cmd_table",
    title="Print *HELP command listing with optional header",
    description="""\
| `V` flag | Action |
|---|---|
| set   | save `X`/`Y`, call [`print_version_header`](address:8C93) to show the ROM version string and station number, restore `X`/`Y` |
| clear | output a newline only |

Either path then falls through to
[`print_cmd_table_loop`](address:8BD5) to enumerate
commands.""",
    on_entry={"x": "offset into cmd_table_fs",
              "v": "set=print version header, clear=newline only"})
subroutine(0x8BD5, "print_cmd_table_loop",
    title="Enumerate and print command table entries",
    description="""\
Walks the ANFS command table from offset `X`, printing each
command name padded to 9 characters followed by its syntax
description.

| Entry byte bit 7 | Treatment |
|---|---|
| clear | print this entry |
| set   | mark end-of-table |

The syntax descriptor byte's low 5 bits index into
`cmd_syntax_table`; index `&0E` triggers special handling that
lists shared command names in parentheses. Calls
[`help_wrap_if_serial`](address:8C29) to handle line
continuation on serial output streams. Preserves `Y`.""",
    on_entry={"x": "offset into cmd_table_fs"})
subroutine(0x8BD8, "loop_next_entry",
    title="*HELP table walker per-entry body",
    description="""\
Loads `cmd_table_fs,X` (entry byte at offset `X`):

| Bit 7 | Target |
|---|---|
| clear | `print_indent` (continue with this entry) |
| set   | `JMP done_print_table` (end of table reached) |

Single caller (the `BNE` retry at `&8C22` in
[`print_cmd_table`](address:8BC6)'s outer loop).""",
    on_entry={"x": "current cmd_table_fs offset"})
subroutine(0x8C06, "loop_print_syntax",
    title="Per-character body of *HELP syntax string emit",
    description="""\
`INY` / load `syn_opt_dir,Y` / detect terminator or
line-break:

| Byte | Action |
|---|---|
| `0`  | terminator – stop |
| `CR` (`&0D`) | line-break – wrap |
| other | print the character |

Two callers: the `BNE` at `&8C13` (continue with current char)
and the `BEQ` at `&8C19` (fall-through from the line-wrap
path).""",
    on_entry={"y": "current index into syn_opt_dir"})
subroutine(0x8C25, "done_print_table",
    title="Cleanup epilogue for print_cmd_table",
    description="""\
Pops the saved `P` and `Y` registers off the stack and `RTS`.
Used as the shared exit for [`print_cmd_table`](address:8BC6)
after it has emitted a help listing or detected end-of-table.
Single caller (the `BEQ` at `&8BDD` in
[`print_cmd_table`](address:8BC6) when `V` was set on entry,
indicating the saved state needs restoring).""",
    on_exit={"y": "restored from stack",
             "p (flags)": "restored from stack"})
subroutine(0x8C29, "help_wrap_if_serial",
    title="Wrap *HELP syntax lines for serial output",
    description="""\
Checks the output destination via [`vdu_mode`](address:0355):

| Stream | Action |
|---|---|
| 0 (VDU) | return immediately |
| 3 (printer) | return immediately |
| serial | output newline + 12 spaces of indentation to align continuation lines with the syntax-description column |""",
    on_exit={"y": "preserved (saved/restored via PHY/PLY)",
             "a": "clobbered (last char written via OSWRCH)"})
subroutine(0x8C64, "svc_return_unclaimed",
    title="Restore Y and return service-call unclaimed",
    description="""\
Reloads `Y` from `ws_page` (the saved command-line offset) and
`RTS` to the caller without clearing `A` – preserving the
original service number so the next ROM in the chain sees the
unclaimed call.

Reached from the four service-handler escape paths at `&8C4C`,
`&8C91`, `&8CD5`, and `&95BE` that hand a request back to MOS
without acting on it.""",
    on_exit={"y": "ws_page (restored command-line offset)"})
subroutine(0x8C93, "print_version_header",
    title="Print ANFS version string and station number",
    description="""\
Uses an inline string after `JSR` to
[`print_inline`](address:9261): `CR + "Advanced NFS 4.21" +
CR`. After the inline string, `JMP`s to
[`print_station_id`](address:90C7) to append the local Econet
station number.""",
    on_entry={},
    on_exit={"a, x, y": "clobbered (print_inline + print_station_id)"})
subroutine(0x8CAD, "get_ws_page",
    title="Read workspace page number for current ROM slot",
    description="""\
Indexes into the MOS per-ROM workspace table
[`rom_ws_pages`](address:0DF0) using `romsel_copy` (`&F4`) as
the ROM slot. Holds a copy of the slot byte in `Y`, then runs a
`ROL` / `PHP` / `ROR` / `PLP` sequence at `&8CB3`–`&8CB6` that
restores `A` to the original byte while leaving the saved-flags
register reflecting bit 6 of the original byte (the ADLC-absent
flag). Falls through to whichever caller-specific tail follows.""",
    on_exit={"a": "workspace page byte (preserved through ROL/ROR)",
             "y": "same byte (set by `TAY` before the rotate trick)",
             "n": "set to bit 6 of the original byte (ADLC-absent flag)"})
subroutine(0x8CBD, "setup_ws_ptr",
    title="Set up zero-page pointer to workspace page",
    description="""\
Calls [`get_ws_page`](address:8CAD) to read the page number,
stores it as the high byte in `nfs_temp` (`&CD`), and clears the
low byte at `&CC` to zero. This gives a page-aligned pointer used
by FS initialisation and [`cmd_net_fs`](address:8B23) to
access the private workspace.""",
    on_exit={"a": "0",
             "y": "workspace page number"})
subroutine(0x8CFD, "notify_new_fs",
    title="Notify OS of filing-system selection",
    description="""\
Loads `A=6` (FSCV reason: filing system change) and falls
through to [`call_fscv`](address:8CFF), which `JMP`-indirects
through `vec_fscv` to invoke the FSCV vector. The FSCV handler
returns to whatever invoked `notify_new_fs` -- this is a
fire-and-forget notification, not a return-to-caller call.

Single caller (&8b60 inside the FS-selection sequence).""",
    on_entry={},
    on_exit={"a": "6 (clobbered by FSCV handler)"})
subroutine(0x8CFF, "call_fscv",
    title="Dispatch to filing-system control vector (FSCV)",
    description="""\
Indirect `JMP` through `FSCV` at [`vec_fscv`](address:021E),
providing OS-level filing-system services such as FS-selection
notification (`A=6`) and `*RUN` handling.

Also contains [`issue_svc_15`](address:8D02) and
`issue_svc_osbyte` entry points that issue paged-ROM service
requests via OSBYTE `&8F`.""",
    on_entry={"a": "FSCV reason code"})
subroutine(0x8D09, "svc_dispatch_idx_2",
    title="svc_dispatch table[2] handler",
    description="""\
Reached only via PHA/PHA/RTS dispatch from the
[`svc_dispatch`](address:89ED) table at index 2. Pushes `Y`
onto the stack via `PHY`, sets `X=&11` (CMOS RAM offset for the
Econet station-flags byte), calls [`osbyte_a1`](address:8E9A) to
read it, then ANDs the result with `&01` (bit 0 = "use page &0B
fallback") and pulls `Y` back. Used by the workspace-allocation
path to discover whether the user has overridden the default
private workspace base.""",
    on_exit={"a": "0 or 1 (CMOS bit 0 of station-flags byte)"})
subroutine(0x8D24, "check_credits_easter_egg",
    title="Easter egg: match *HELP keyword to author credits",
    description="""\
Matches the `*HELP` argument against a keyword embedded in the
credits data at `credits_keyword_start`. Starts matching from
offset 5 in the data (`X=5`) and checks each byte against the
command-line text until a mismatch or `X` reaches `&0D`.

On a full match, prints the ANFS author credits:

- B Cockburn
- J Dunn
- B Robertson
- J Wills

Each name is terminated by `CR`.""")
subroutine(0x8E21, "clear_if_station_match",
    title="Clear hazel_fs_network if it matches the bridge status byte",
    description="""\
Calls [`init_bridge_poll`](address:ABE9) (returning the
[`spool_control_flag`](address:0D71) bridge status byte in `A`,
either freshly populated or already cached from a previous
invocation) and EORs it with
[`hazel_fs_network`](address:C001). When the two match (`EOR`
result is zero), zeroes `hazel_fs_network` so subsequent FS
operations fall back to the local network.

Called by [`cmd_iam`](address:8D91) and
[`osword_13_set_station`](address:A9EC) when reconciling a
parsed file-server station address against the bridge state.""",
    on_exit={"a": "0 if cleared (match), bridge-XOR-network otherwise"})
subroutine(0x8E2D, "check_urd_prefix",
    title="Branch to *RUN handler if first arg char is '&'",
    description="""\
Reads the first character of the parsed command text via
`(fs_crc_lo),Y`:

| First char | Path |
|---|---|
| `'&'` (URD prefix marker) | `JMP cmd_run_via_urd` |
| any other | fall through to `pass_send_cmd` (send as normal FS request) |

Single caller (the FS command-name post-match path at
`&9597`).""")
subroutine(0x8E3C, "send_cmd_and_dispatch",
    title="Send FS command and dispatch the reply",
    description="""\
1. `JSR save_net_tx_cb` to set up and transmit the command.
2. Read the reply function code from
   [`hazel_txcb_network`](address:C103).

| Reply code | Action |
|---|---|
| `0`     | branch to the no-reply path (`dispatch_rts`) |
| non-zero | load [`hazel_txcb_data`](address:C105) (first reply byte), `Y=&25` (dispatch offset for the standard reply table), continue into the reply-dispatch chain |

Two callers: the fall-through from
[`check_urd_prefix`](address:8E2D) (`&8E1F` via
`pass_send_cmd`) and the `JMP` from `send_fs_request` (`&9460`).""",
    on_entry={"y": "extra dispatch offset (0 from send_fs_request, "
              "non-zero for some specialised paths)"})
subroutine(0x8E5B, "dir_op_dispatch",
    title="Dispatch directory operation via PHA/PHA/RTS",
    description="""\
Validates `X < 5` and sets `Y = &18` as the dispatch offset,
then falls through into [`svc_dispatch`](address:8E61). The
`INX`/`DEY`/`BPL` loop in
[`svc_dispatch`](address:8E61) then settles `X_final =
X_caller + Y + 1`, landing on indices `&19..&1D` of the
[`svc_dispatch_lo`](address:89ED) /
[`svc_dispatch_hi`](address:8A20) tables. Those slots map to
the language-reply handlers `lang_0_insert_key`
(idx `&19`) through `lang_4_validated` (idx `&1D`).

(In 4.18 the offset was `&0E`, reaching indices 15..19. The 4.21
shift to `&18` puts the targets ten slots higher in the rebuilt
dispatch table.)""",
    on_entry={"x": "directory operation code (0-4)"})
subroutine(0x8E98, "read_cmos_byte_0",
    title="Read CMOS RAM byte 0 (Master 128)",
    description="""\
Sets `X=0` and falls through to [`osbyte_a1`](address:8E9A),
which issues OSBYTE `&A1` to read CMOS RAM byte 0 – the
file-system / language byte holding the default boot mode and FS
selection.

Single caller (`&8FBB`, inside
[`nfs_init_body`](address:8F38)'s CMOS-read sequence).""",
    on_exit={"y": "CMOS byte 0 (returned by OSBYTE &A1)"})
subroutine(0x8ED2, "osbyte_x0_y0",
    title="OSBYTE wrapper with X=0, Y=0",
    description="""\
Sets `X=0` and `Y=0` then branches to `jmp_osbyte`. Called from
the Econet OSBYTE dispatch chain to handle OSBYTEs that require
both `X` and `Y` cleared. The unconditional `BEQ` (after `LDY
#0` sets `Z`) reaches the `JMP osbyte` instruction.""",
    on_entry={"a": "OSBYTE number"},
    on_exit={"x": "0", "y": "0"})
subroutine(0x8EF0, "store_ws_page_count",
    title="Record workspace page count (capped at &D3)",
    description="""\
Stores the workspace allocation from service 1 into offset `&0B` of
the receive control block, capping the value at `&D3` to prevent
overflow into adjacent workspace areas. Called by
[`svc_2_priv_ws`](address:8F10) after issuing the
absolute workspace claim service call.""",
    on_entry={"y": "workspace page count from service 1"})
# Three PHA/PHA/RTS dispatch targets in this area, each reached only
# via the svc_dispatch table at &89ED (lo) / &8A20 (hi). All three
# need explicit entry() because PHA/PHA/RTS dispatch leaves no
# code-flow trace for py8dis to follow.
#
#   &8EFE  -- workspace-page record helper. Also reached by a
#             backward BCS at &8F35 inside the routine immediately
#             below, which is what makes it useful: the BCS lets the
#             page-allocation code share code with the dispatch
#             entry point at &8EFE.
#   &8F10  -- the page-allocation portion of ANFS init (sets up
#             net_rx_ptr_hi / nfs_workspace_hi, clears their lo
#             bytes, calls get_ws_page).
#   &8F38  -- the FULL ANFS init body: clears workspace, reads CMOS
#             station ID, calls cmd_net_fs to select ANFS, then
#             init_adlc_and_vectors to hook FILEV / ARGSV / NETV /
#             FSCV / etc. Returns via RTS at &903B.
#
# Open question (Phase C continuation): exactly which dispatch path
# invokes &8F38, and how the page-allocation work at &8F10 is
# composed with it. Pinning down the precise svc_dispatch (X, Y) pair
# that picks index 22 is left as future work (OPEN-ISSUES O-1); for
# now both halves are decoded as code with conservative names.
entry(0x8EFE)
entry(0x8F10)
entry(0x8F38)
subroutine(0x8F10, "svc_2_priv_ws",
    title="Service-2 page-allocation prologue",
    description="""\
Reads CMOS byte `&11` to test bit 2 of the saved Econet status;
either advances the caller's first-available-page (`Y`) by 2 and
uses it, or forces page `&0B` as a fallback. Sets `net_rx_ptr_hi` /
`nfs_workspace_hi` to the chosen page pair, clears the corresponding
lo bytes, and calls [`get_ws_page`](address:8CAD). If the resulting
page is `>= &DC`, branches to the helper at
[`&8EFE`](address:8EFE) which publishes the page into
`rom_ws_pages[romsel_copy]` with bit 7 masked off.

This routine handles only the workspace-page allocation half of
service 2. The bring-up remainder (station ID, FS workspace zero,
`cmd_net_fs`, [`init_adlc_and_vectors`](address:903C)) lives at
[`nfs_init_body`](address:8F38) and is dispatched separately – see
the comment block above.""",
    on_entry={"y": "first available private workspace page"})
subroutine(0x8F38, "nfs_init_body",
    title="ANFS initialisation body",
    description="""\
Reached only via PHA/PHA/RTS dispatch (table index 22 in the
svc_dispatch table at `&89ED` / `&8A20`). Carries out the bring-up
sequence after page allocation:

- Clears `ws_page` / `tx_complete_flag` and the receive-block
  remote-op flag.
- On warm reset (`last_break_type` non-zero) and `fs_flags` bit 4
  set, calls [`setup_ws_ptr`](address:8CBD) and zeroes the FS
  workspace page in a 256-byte loop.
- Calls [`copy_ps_data_y1c`](address:B3D5) to install the printer-
  server template.
- Reads CMOS bytes `&01..&04` via `osbyte_a1`, storing each into
  the workspace identity block at `nfs_workspace+{0..3}`.
- Reads CMOS byte `&11` (Econet station): if zero, prints
  `Station number in CMOS RAM invalid. Using 1 instead!` and
  defaults to station 1.
- Stores station ID into the receive block.
- Calls `cmd_net_fs` to select ANFS as the active filing system,
  then [`init_adlc_and_vectors`](address:903C) to install NETV /
  FSCV / etc., `handle_spool_ctrl_byte` and `init_bridge_poll`
  for protection setup.

Returns via `RTS` at `&903B`.

Reached via Master 128 service call `&27` (= 39 decimal),
documented in the *Advanced Reference Manual for the BBC Master*:

> Reset has occurred. Call made after hard reset. Mainly for
> Econet Filing system so that it can claim NMIs. This call is
> now required since the MOS no longer offers workspace on a
> soft BREAK. A Sideways ROM should therefore re-initialise
> itself.

The full set of Master 128 service calls ANFS handles, dispatched
via the CMP/SBC normalisation chain in
[`service_handler`](address:8A54):

| svc        | idx   | handler                   | purpose                |
| ---------- | ----- | ------------------------- | ---------------------- |
| `&00..&0C` | 1..13 | (svc-1..12 handlers)      | service-1 .. service-12 |
| `&12`      | 14    | `svc_18_fs_select`        | FS select              |
| `&18`      | 15    | `match_on_suffix`         | Interactive HELP       |
| `&21`      | 16    | `raise_y_to_c8`           | static ws claim        |
| `&22`      | 17    | `set_rom_ws_page`         | dynamic ws offer       |
| `&23`      | 18    | `store_ws_page_count`     | top-of-static-ws       |
| `&24`      | 19    | `noop_dey_rts`            | dynamic ws claim (1 pg) |
| `&25`      | 20    | `copy_template_to_zp`     | FS name + info reply   |
| `&26`      | 21    | `svc_26_close_all_files`  | close all files        |
| `&27`      | 22    | `nfs_init_body` (this)    | reset re-init          |
| `&28`      | 23    | `print_fs_ps_help` | *CONFIGURE option      |
| `&29`      | 24    | `svc_29_status`   | *STATUS option         |

Everything else (svc `&0D..&11`, `&13..&17`, `&19..&20`, `&2A+`)
falls through to
[`dispatch_svc_state_check`](address:8ACE) with `A := 0` and
dispatches to idx 1 = `dispatch_rts` (no-op) – deliberately
ignoring svc `&15` (100 Hz poll), svc `&2A` (language ROM
startup), etc.""")
label(0x8FB8, "done_alloc_handles")
subroutine(0x903C, "init_adlc_and_vectors",
    title="Initialise ADLC and install extended vectors",
    description="""\
Reads the ROM pointer table via OSBYTE `&A8`, writes vector
addresses and ROM ID into the extended vector table for `NETV`
and one additional vector, then restores any previous FS context
via [`restore_fs_context`](address:9064). Falls through into
[`write_vector_entry`](address:904F).""",
    on_exit={"a, x, y": "clobbered (falls through into write_vector_entry)"})
subroutine(0x904F, "write_vector_entry",
    title="Install extended-vector table entries",
    description="""\
Copies vector addresses from the dispatch table at
`svc_dispatch_lo_offset+Y` into the MOS extended-vector table
pointed to by `fs_error_ptr`. For each entry, writes address low,
high, then the current ROM ID from `romsel_copy` (`&F4`). Loops
`X` times.

After the loop, stores `&FF` at
[`bridge_status`](address:0D72) as an installed flag, calls
`deselect_fs_if_active` and [`get_ws_page`](address:8CAD) to
restore FS state.""",
    on_entry={"x": "number of vectors to install",
              "y": "starting offset in extended vector table"},
    on_exit={"y": "workspace page number + 1"})
subroutine(0x9064, "restore_fs_context",
    title="Restore FS context from HAZEL into RX block",
    description="""\
Copies 8 bytes (offsets 2..9) from the HAZEL FS state block into
the receive control block at `(net_rx_ptr)+Y`. The source uses
the [`hazel_minus_2`](address:BFFE) indexing-base trick:
`LDA hazel_minus_2,Y` with `Y` running 9 down to 2 lands at
`&C007..&C000` (the [`hazel_fs_station`](address:C000) block --
station, network, saved station, CSD/lib slots, FS flags, etc.).
Restores those bytes into the RX control block when the caller
needs to re-publish the FS context (e.g. after a flip-set boot).

Called by [`svc_2_priv_ws`](address:8F10) during init,
`deselect_fs_if_active` during FS teardown, and
`flip_set_station_boot`.""",
    on_exit={"a, y": "clobbered (loop counter / data byte)"})
subroutine(0x9071, "fscv_6_shutdown",
    title="Deselect filing system and save workspace",
    description="""\
If the filing system is currently selected (bit 7 of
[`fs_flags`](address:0D6C) set):

1. Closes all open FCBs.
2. Closes `*SPOOL`/`*EXEC` files via OSBYTE `&77`.
3. Saves the FS workspace to page `&10` shadow with checksum.
4. Clears the selected flag.""")
subroutine(0x909E, "verify_ws_checksum",
    title="Verify workspace checksum integrity",
    description="""\
Sums bytes 0..`&76` of the workspace page via the zero-page
pointer at `&CC`/`&CD` and compares with the stored value at
offset `&77`. On mismatch, raises a 'net sum' error (`&AA`) via
[`error_net_checksum`](address:90B5).

The checksummed page holds open-file information (preserved when
ANFS is not the current filing system) and the current printer
type. Can only be reset by a control-BREAK.

Preserves `A`, `Y`, and processor flags using `PHP`/`PHA`. Called
by 5 sites across `format_filename_field`, `adjust_fsopts_4bytes`,
and `start_wipe_pass` before workspace access.""",
    on_exit={"a": "preserved (PHA/PLA)",
             "y": "preserved",
             "p (flags)": "preserved (PHP/PLP)"})
subroutine(0x90B5, "error_net_checksum",
    title="Raise 'net checksum' BRK error",
    description="""\
Loads error code `&AA` and tail-calls `error_bad_inline` with the
inline string 'net checksum'. Reached when
[`ensure_fs_selected`](address:8B4D) (auto-select path)
cannot bring ANFS up, or when
[`verify_ws_checksum`](address:909E) detects that the saved
workspace checksum at offset `&77` doesn't match the live sum –
only resettable by a control-BREAK. Never returns.""")
subroutine(0x90C7, "print_station_id",
    title="Print Econet station number and clock status",
    description="""\
Uses [`print_inline`](address:9261) to output `'Econet
Station '`, then reads the station ID from offset 1 of the
receive control block and prints it as a decimal number via
`print_num_no_leading`. Tests ADLC status register 2
([`adlc_cr2`](address:FEA1)) to detect the Econet clock; if
absent, appends `' No Clock'` via a second inline string.
Finishes with `OSNEWL`.

Called by [`print_version_header`](address:8C93) and
[`svc_3_autoboot`](address:8CC7).""",
    on_exit={"a, x, y": "clobbered (print_inline + print_num_no_leading "
             "+ OSNEWL)"})
subroutine(0x91F9, "print_newline_no_spool",
    title="Print CR via OSASCI, bypassing any open *SPOOL file",
    description="""\
Loads `A=&0D` and falls into
[`print_char_no_spool`](address:91FB). The underlying
mechanism temporarily writes `0` to the `*SPOOL` file handle
(OSBYTE `&C7` with `X=0`, `Y=0`) so the printed `CR` is not
captured by spool, then restores the previous handle on exit.

Called from [`service_handler`](address:8A54) (`&8A7C`) after
the `'Bad ROM <slot>'` message, and from two other diagnostic
sites (`&8E10`, `&9D3E`).""",
    on_entry={},
    on_exit={"a, x, y, p": "preserved (print_char_no_spool brackets the call "
             "with full register save/restore via PHA/PHP/PLP/PLA)"})

subroutine(0x91FB, "print_char_no_spool",
    title="Print A via OSASCI, bypassing any open *SPOOL file",
    description="""\
Pushes the caller's flags, then forces `V=1` via the `BIT &9769`
/ `BVS` trick (`&9769` is a constant `&FF` byte in ROM). Saves
`X`, `Y`, `A` and a copy of the (now `V=1`) flags.

1. Calls OSBYTE `&C7` with `X=0`, `Y=0` to write `0` to the
   `*SPOOL` file handle, returning the previous handle in `X`.
2. If the previous handle was in the NFS-issued range
   `&21..&2F`, calls OSBYTE `&C7` again with `X=OLD`, `Y=0` to
   **restore** the spool *before* the print (so the print is
   captured); otherwise leaves spool closed for the duration of
   the print.
3. `PLP`s the inner `P`, then routes to OSASCI (the `BIT` trick
   set `V=1`, so the `BVC` at `&9220` is not taken).
4. Final OSBYTE `&C7` with `Y=&FF` either no-ops (if spool
   already restored) or writes `OLD` back (if it was deferred).
5. Pulls `A`, `Y`, `X`, `P` and returns.

Eight inner-ROM callers: `&925F`, `&92A4`, `&9D30`, `&9D5C`,
`&B21F`, `&B2F9`, `&B321`, `&B752`.""",
    on_entry={"a": "byte to print as ASCII char (CR is translated by OSASCI)"})

subroutine(0x9201, "print_byte_no_spool",
    title="Print A via OSWRCH (raw, no CR translation), bypass *SPOOL",
    description="""\
As [`print_char_no_spool`](address:91FB) but the inner
`PHP`/`CLV` at `&9201` forces `V=0` in the saved flags, so the
`BVC` at `&9220` takes the `OSWRCH` branch instead of `OSASCI`.

Used when the caller wants to emit a raw byte (e.g. a VDU
control code) without `CR` translation. Sole caller in this ROM
is at `&8DE6`.""",
    on_entry={"a": "raw byte to print via OSWRCH"})

subroutine(0x9236, "print_hex_byte",
    title="Print A as two hexadecimal digits",
    description="""\
Saves `A` on the stack, shifts right four times to isolate the
high nybble, calls [`print_hex_nybble`](address:923F) to
print it, then restores the full byte and falls through to
[`print_hex_nybble`](address:923F) for the low nybble.

Callers: `print_5_hex_bytes`, [`cmd_ex`](address:B103),
[`cmd_dump`](address:BD41), and `print_dump_header`.""",
    on_entry={"a": "byte to print"},
    on_exit={"a": "original byte value"})
subroutine(0x923F, "print_hex_nybble",
    title="Print low nybble of A as hex digit",
    description="""\
Masks `A` to the low 4 bits, then converts to ASCII:

1. Adds 7 for letters `A`..`F` (via `ADC #6` with carry set from
   the `CMP`).
2. `ADC #&30` for the final `'0'`..`'F'` character.
3. Outputs via `JMP OSASCI`.""",
    on_entry={"a": "value (low nybble used)"})
subroutine(0x9269, "loop_next_char",
    title="print_inline pointer-advance step",
    description="""\
`INC fs_error_ptr` (lo); on overflow `INC fs_crflag` (hi). Single
caller (the loop tail at `&9284` inside
[`print_inline`](address:9261)). Falls through to `load_char`
which reads the next inline-string byte.""")
subroutine(0x92B2, "parse_addr_arg",
    title="Parse decimal or hex station address argument",
    description="""\
Reads characters from the command argument at `(fs_crc_lo),Y`.
Supports `&` prefix for hex, `.` separator for net.station
addresses, and plain decimal. Returns the result in `fs_load_addr_2`
(and `A`). Raises [`Bad hex`](address:934A), `Bad number`,
[`Bad station number`](address:9357), and overflow errors as
appropriate. The body uses the standard 6502 idioms: `ASL ASL ASL
ASL` + `ADC` for hex-digit accumulation, and `result*2 + result*8`
for decimal `*10`. Two named callers: from `&A3C9` and `&A3DE`.""",
    on_entry={
        "y": "index into command-string buffer at (fs_crc_lo),Y",
        "a": "ignored",
    },
    on_exit={"c": "set if a number was parsed"})
subroutine(0x934A, "err_bad_hex",
    title="Raise 'Bad hex' BRK error",
    description="""\
Loads error code `&F1` and tail-calls `error_bad_inline` with
the inline string `'hex'` – `error_bad_inline` prepends `'Bad '`
to produce the final `'Bad hex'` message. Called from
[`parse_addr_arg`](address:92B2) and the `*DUMP` / `*LIST`
hex parsers when a digit is out of range. Never returns.""")
subroutine(0x939A, "is_decimal_digit",
    title="Test for digit, '&', or '.' separator",
    description="""\
Compares `A` against `'&'` and `'.'` first; if either matches,
returns with carry set via the shared `return_from_digit_test` exit.
Otherwise falls through to
[`is_dec_digit_only`](address:93A2) for the `'0'`..`'9'`
range test.

Called by [`cmd_iam`](address:8D91),
[`cmd_ps`](address:B3AC), and
[`cmd_pollps`](address:B581) when parsing station
addresses.""",
    on_entry={"a": "character to test"},
    on_exit={"c": "set if digit/&/., clear otherwise"})
subroutine(0x93A2, "is_dec_digit_only",
    title="Test for decimal digit '0'..'9'",
    description="""\
Uses two `CMP`s to bracket-test `A` against the range
`&30..&39`:

1. `CMP #&3A` sets carry if `A >= ':'` (above digits).
2. `CMP #&30` sets carry if `A >= '0'`.

The net effect: carry set only for `'0'..'9'`. Called by
[`parse_addr_arg`](address:92B2).""",
    on_entry={"a": "character to test"},
    on_exit={"c": "set if '0'-'9', clear otherwise"})
subroutine(0x93AB, "get_access_bits",
    title="Read and encode directory entry access byte",
    description="""\
Loads the access byte from offset &0E of the directory entry via
`(fs_options),Y`, masks to 6 bits (`AND #&3F`), then sets `X=4`
and branches to [`begin_prot_encode`](address:93B9) to map through
[`prot_bit_encode_table`](address:93C8). Called by
[`check_and_setup_txcb`](address:9D87) for owner and public
access.""",
    on_exit={"a": "encoded access flags",
             "x": "&FF + bits-set (left in this state by get_prot_bits "
             "fall-through)"})
subroutine(0x93B5, "get_prot_bits",
    title="Encode protection bits via lookup table",
    description="""\
Masks `A` to 5 bits (`AND #&1F`), sets `X=&FF` to start at table
index 0, then enters the shared encoding loop at
[`begin_prot_encode`](address:93B9). Shifts out each source bit
and ORs in the corresponding value from
[`prot_bit_encode_table`](address:93C8). Called by
[`send_txcb_swap_addrs`](address:9C85) and
[`check_and_setup_txcb`](address:9D87).""",
    on_entry={"a": "raw protection bits (low 5 used)"},
    on_exit={"a": "encoded protection flags"})
subroutine(0x93D3, "set_text_and_xfer_ptr",
    title="Set OS text pointer then transfer parameters",
    description="""\
Stores `X`/`Y` into the MOS text pointer at `os_text_ptr` /
`os_text_ptr_hi` (`&F2`/`&F3`), then falls through to
[`set_xfer_params`](address:93D7) and
[`set_options_ptr`](address:93DD) to configure the full FS
transfer context. Two callers:
[`fscv_3_star_cmd`](address:A42F) (FSCV reason 3) and
[`ps_scan_resume`](address:B0FE) (PS scan tail).""",
    on_entry={"x": "text pointer low byte",
              "y": "text pointer high byte"})
subroutine(0x93D7, "set_xfer_params",
    title="Set FS transfer byte count and source pointer",
    description="""\
Stores `A` into `fs_last_byte_flag` (`&BD`) as the transfer byte
count, and `X`/`Y` into `fs_crc_lo`/`hi` (`&BE`/`&BF`) as the
source-data pointer. Falls through to
[`set_options_ptr`](address:93DD) to complete the
transfer-context setup.

Called by 5 sites across [`cmd_ex`](address:B103),
`format_filename_field`, and `gsread_to_buf`.""",
    on_entry={"a": "transfer byte count",
              "x": "source pointer low",
              "y": "source pointer high"})
subroutine(0x93DD, "set_options_ptr",
    title="Set FS options pointer and clear escape flag",
    description="""\
Stores `X`/`Y` into `fs_options`/`fs_block_offset` (`&BB`/`&BC`)
as the options-block pointer. Then enters
[`clear_escapable`](address:93E1) which uses
`PHP`/`LSR`/`PLP` to clear bit 0 of the escape flag at `&97`
without disturbing processor flags.

Called by `format_filename_field` and `send_and_receive`.""",
    on_entry={"x": "options pointer low",
              "y": "options pointer high"})
subroutine(0x93E1, "clear_escapable",
    title="Clear bit 0 of need_release_tube preserving flags",
    description="""\
PHP / LSR need_release_tube / PLP / RTS. Shifts bit 0 of
need_release_tube into carry while clearing it, then restores the
caller's flags so the operation is invisible to NZC-sensitive
code. Single caller (&9B72 in the recv-and-classify reply path).""")
subroutine(0x93E6, "cmp_5byte_handle",
    title="Compare 5-byte handle buffers for equality",
    description="""\
Loops `X` from 4 down to 1, comparing each byte of
`addr_work+X` with `fs_load_addr_3+X` using `EOR`. Returns on
the first mismatch (`Z=0`) or after all 5 bytes match (`Z=1`).

Called by `send_txcb_swap_addrs` and `check_and_setup_txcb` to
verify station/handle identity.""",
    on_exit={"z": "set if bytes 1..4 match (byte 0 is not compared)",
             "a": "EOR of last compared bytes",
             "x": "0 if all matched, else mismatch index"})
subroutine(0x93F2, "fscv_7_read_handles",
    title="FSCV reason 7: report FCB handle range",
    description="""\
Returns the FCB handle range to the caller: `X=&20` (lowest valid
handle) and `Y=&2F` (highest valid handle), then `RTS`. Reached
via the FSCV vector with reason code 7. Used by the OS to discover
which handle values this filing system claims.""",
    on_exit={"x": "&20 (first valid FCB handle)",
             "y": "&2F (last valid FCB handle)"})
subroutine(0x93F7, "set_conn_active",
    title="Set connection-active flag in channel table",
    description="""\
Saves registers on the stack, recovers the original `A` from the
stack via `TSX`/`LDA &0102,X`, then calls `attr_to_chan_index` to
find the channel slot. `ORA`s bit 6 (`&40`) into the channel
status byte at [`hazel_fcb_status`](address:C260)`+X`.
Preserves `A`, `X`, and processor flags via
`PHP`/`PHA`/`PLA`/`PLP`.

Called by `format_filename_field` and `adjust_fsopts_4bytes`.""",
    on_entry={"a": "channel attribute byte"})
subroutine(0x940D, "clear_conn_active",
    title="Clear connection-active flag in channel table",
    description="""\
Mirror of [`set_conn_active`](address:93F7) but `AND`s the
channel status byte with `&BF` (bit-6 clear mask) instead of
`ORA`ing. Uses the same register-preservation pattern:
`PHP`/`PHA`/`TSX` to recover `A`, then `attr_to_chan_index` to
find the slot. Shares the `done_conn_flag` exit with
[`set_conn_active`](address:93F7).""",
    on_entry={"a": "channel attribute byte"})
subroutine(0x9437, "error_bad_filename",
    title="Raise 'Bad file name' BRK error",
    description="""\
Loads error code `&CC` and tail-calls `error_bad_inline` with
the inline string `'file name'` – `error_bad_inline` prepends
`'Bad '` to produce the final `'Bad file name'` message. Used
by [`check_not_ampersand`](address:9446) and other filename
validators. Never returns.""")
subroutine(0x9446, "check_not_ampersand",
    title="Reject '&' as filename character",
    description="""\
Loads the first character from the parse buffer at `&0E30` and
compares with `'&'` (`&26`). Branches to
[`error_bad_filename`](address:9437) if matched, otherwise
returns.

Also contains [`read_filename_char`](address:944E) which
loops reading characters from the command line into the TX
buffer at `hazel_txcb_data` (`&C105`), calling
`strip_token_prefix` on each byte and terminating on `CR`. Used
by [`cmd_fs_operation`](address:9425) and
[`cmd_rename`](address:94C5).""",
    on_exit={"a": "first byte of parse buffer (preserved unchanged on the "
             "non-error path)"})
subroutine(0x944E, "read_filename_char",
    title="Loop reading filename chars into TX buffer",
    description="""\
Per-character loop body of the filename-copy logic in
[`check_not_ampersand`](address:9446):

1. `JSR` to [`check_not_ampersand`](address:9446) to reject `'&'`.
2. Store the byte at [`hazel_txcb_data`](address:C105)`+X`
   (TX buffer area).
3. Increment `X`.
4. Branch to [`send_fs_request`](address:945E) on `CR`, or
   strip a BASIC token prefix via `strip_token_prefix` and
   re-enter the loop.

Three callers: the loop's own `BRA` at `&945C`, plus `&9435`
([`cmd_rename`](address:94C5)'s first-arg copy) and `&950F`
([`cmd_fs_operation`](address:9425)'s filename pickup).""",
    on_entry={"a": "current character to copy",
              "x": "TX-buffer write index"},
    on_exit={"x": "advanced past the CR terminator"})
subroutine(0x945E, "send_fs_request",
    title="Send FS command with no extra dispatch offset",
    description="""\
Loads `Y=0` (so dispatch lookups don't add an offset) and
tail-jumps to [`send_cmd_and_dispatch`](address:8E3C). Two
callers: [`read_filename_char`](address:944E)'s `BEQ` on
`CR` (`&9457`) and the `*RUN` argument-handling tail at
`&9537`.""")
subroutine(0x9463, "copy_fs_cmd_name",
    title="Copy matched command name to TX buffer",
    description="""\
Scans backwards in `cmd_table_fs` from the current position to find
the bit-7 flag byte marking the start of the command name. Copies
each character forward into the TX buffer at `&C105` until the next
bit-7 byte (end of name), then appends a space separator.""",
    on_entry={"x": "byte offset within cmd_table_fs (just past the matched "
              "command's last name char)",
              "y": "current command-line offset (saved/restored)"},
    on_exit={"x": "TX buffer offset past name+space",
             "y": "command line offset (restored)",
             "a": "clobbered"})
subroutine(0x9483, "parse_quoted_arg",
    title="Parse possibly-quoted filename argument",
    description="""\
Reads from the command line at `(fs_crc_lo),Y` (`&BE`). Handles
double-quote delimiters and stores the result in the parse
buffer at `&0E30`. Raises `'Bad string'` on unbalanced quotes.""",
    on_entry={"y": "current offset within the command line"},
    on_exit={"y": "advanced past the parsed argument",
             "a": "clobbered (last byte read)"})
subroutine(0x973D, "init_txcb_bye",
    title="Set up open receive for FS reply on port &90",
    description="""\
Loads `A=&90` (the FS command/reply port) and falls through to
[`init_txcb_port`](address:973F), which creates an open
receive control block: the template sets `txcb_ctrl` to `&80`,
then `DEC` makes it `&7F` (bit 7 clear = awaiting reply). The
NMI RX handler sets bit 7 when a reply arrives on this port,
which [`wait_net_tx_ack`](address:98BE) polls for.""",
    on_entry={})
subroutine(0x973F, "init_txcb_port",
    title="Create open receive control block on specified port",
    description="""\
Calls [`init_txcb`](address:974B) to copy the 12-byte
template into the TXCB workspace at `&00C0`, then stores `A` as
the port (`txcb_port` at `&C1`) and sets `txcb_start` to 3. The
`DEC txcb_ctrl` changes the control byte from `&80` to `&7F`
(bit 7 clear), creating an open receive: the NMI RX handler
will set bit 7 when a reply frame arrives on this port, which
[`wait_net_tx_ack`](address:98BE) polls for.""",
    on_entry={"a": "port number"})
subroutine(0x974B, "init_txcb",
    title="Initialise TX control block from ROM template",
    description="""\
Copies 12 bytes from [`txcb_init_template`](address:9763) into the
TXCB workspace at `&00C0`. For the first two bytes (`Y=0,1`),
also copies the destination station/network from `&0E00` into
`txcb_dest` (`&C2`). Preserves `A` via `PHA`/`PLA`.

Called by 4 sites including [`cmd_pass`](address:8DD5),
[`init_txcb_port`](address:973F),
[`prep_send_tx_cb`](address:97B7), and `send_wipe_request`.""",
    on_exit={"a": "preserved",
             "x, y": "clobbered (Y left at &FF on loop exit)"})
subroutine(0x976F, "send_request_nowrite",
    title="Send read-only FS request (carry set)",
    description="""\
Pushes `A` and sets carry to indicate no-write mode, then
branches to `txcb_copy_carry_set` to enter the common TXCB copy,
send, and reply-processing path. The carry flag controls whether
a disconnect is sent on certain reply codes. Called by
`setup_transfer_workspace`.""",
    on_entry={"y": "FS function code (stored as TX[1] = txcb_func by "
              "txcb_copy_carry_set)",
              "a": "saved on stack at entry (consumed by the txcb "
              "send/receive path)"})
subroutine(0x9773, "send_request_write",
    title="Send read-write FS request (V clear)",
    description="""\
Clears `V` flag and branches unconditionally to
`txcb_copy_carry_clr` (via `BVC`, always taken after `CLV`) to
enter the common TXCB copy, send, and reply-processing path with
carry clear (write mode). Called by `do_fs_cmd_iteration` and
`send_txcb_swap_addrs`.""",
    on_entry={"y": "FS function code (stored as TX[1] = txcb_func by "
              "txcb_copy_carry_clr)",
              "a": "request payload byte (used by the txcb send path)"})
subroutine(0x978A, "save_net_tx_cb",
    title="Save FS state and send command to file server",
    description="""\
Copies station address and function code (`Y`) to the TX buffer,
builds the TXCB via [`init_txcb`](address:974B), sends the
packet through [`prep_send_tx_cb`](address:97B7), and waits
for the reply via [`recv_and_process_reply`](address:97CD).
`V` is clear for standard mode.""",
    on_entry={"y": "FS function code (becomes TX[1] = txcb_func)",
              "x": "TX buffer payload length "
              "(prep_send_tx_cb uses X+5 as txcb_end)"},
    on_exit={"a": "FS reply status"})
subroutine(0x978B, "save_net_tx_cb_vset",
    title="Save and send TXCB with V flag set",
    description="""\
Variant of [`save_net_tx_cb`](address:978A) for callers that
have already set `V`. Copies the FS station address from `&0E02`
to `&0F02`, then falls through to `txcb_copy_carry_clr` which
clears carry and enters the common TXCB copy, send, and reply
path.

Called by `check_and_setup_txcb`, `format_filename_field`, and
`cmd_remove`.""",
    on_entry={"y": "FS function code",
              "x": "TX buffer payload length",
              "v flag": "set by caller (selects this variant via the "
              "'no CLV' fall-through from save_net_tx_cb)"},
    on_exit={"a": "FS reply status"})
subroutine(0x97B7, "prep_send_tx_cb",
    title="Build TXCB from scratch, send, and receive reply",
    description="""\
Full send/receive cycle comprising two separate Econet
transactions:

1. Save flags, set reply port `&90`.
2. Call [`init_txcb`](address:974B), compute `txcb_end =
   X + 5`.
3. Dispatch on carry:

   | `C` | Path |
   |---|---|
   | set   | `handle_disconnect` |
   | clear | `init_tx_ptr_and_send` for a client-initiated four-way handshake (scout, ACK, data, ACK) to deliver the command |

4. After TX completes, the ADLC returns to idle RX-listen.
5. Falls through to [`recv_and_process_reply`](address:97CD)
   which waits for the server to independently initiate a new
   four-way handshake with the reply on port `&90`. There is no
   reply data in the original ACK payload.""",
    on_entry={"x": "TX buffer payload length (txcb_end = X + 5)",
              "y": "FS function code (already stashed by the txcb-copy "
              "entry path)",
              "c flag": "set = disconnect path (handle_disconnect); "
              "clear = normal four-way handshake send"},
    on_exit={"a": "FS reply status (or doesn't return on error)"})
subroutine(0x97CD, "recv_and_process_reply",
    title="Receive FS reply and dispatch on status codes",
    description="""\
Waits for a server-initiated reply transaction. After the
command TX completes (a separate client-initiated four-way
handshake), calls [`init_txcb_bye`](address:973D) to set up
an open receive on port `&90` (`txcb_ctrl = &7F`). The server
independently initiates a new four-way handshake to deliver the
reply; the NMI RX handler matches the incoming scout against
this RXCB and sets bit 7 on completion.
[`wait_net_tx_ack`](address:98BE) polls for this.

Iterates over reply bytes:

| Byte / state | Action |
|---|---|
| `0` | terminates |
| `V` set | adjust by `+&2B` |
| non-zero, `V` clear | dispatch to `store_reply_status` |

Handles disconnect requests (`C` set from
[`prep_send_tx_cb`](address:97B7)) and `'Data Lost'`
warnings when channel status bits indicate pending writes were
interrupted.""",
    on_entry={"c flag": "set = disconnect mode (caller sent a disconnect "
              "scout; handle the server's matching reply)"},
    on_exit={"a": "FS reply status byte"})
subroutine(0x9850, "lang_1_remote_boot",
    title="Language reply 1: remote-boot init / continue",
    description="""\
Reads the reply byte at `(net_rx_ptr),0`. If zero, branches to
[`init_remote_session`](address:9859) to (re)initialise the
remote session. Otherwise falls through to `done_commit_state`
which finalises the boot state byte for the active session.""")
subroutine(0x987E, "lang_3_exec_0100",
    title="Language reply 3: raise 'Remoted' error at &0100",
    description="""\
Calls [`commit_state_byte`](address:B05F) to record the new state,
loads `A=0` and tail-calls [`error_inline_log`](address:99C0) with
the inline string `Remoted` followed by `&07` (BEL). Used by
remote-language replies that need to abort the current operation
with a terminal beep + error. Never returns.""")
subroutine(0x9895, "raise_escape_error",
    title="Acknowledge escape and raise classified error",
    description="""\
Issues OSBYTE &7E (acknowledge_escape -- clears the escape condition
and runs any registered escape effects), loads A=6, and tail-jumps to
classify_reply_error which builds the Escape error. Reached from
&98EF (after recv_and_process_reply detects escape) and &B7DF
(cmd_wipe's per-iteration escape check). Never returns -- the
classify_reply_error path triggers BRK.""",
    on_exit={"a": "6 (Escape error code passed to classify_reply_error)"})
subroutine(0x989F, "lang_4_validated",
    title="Language reply 4: validate remote session and apply",
    description="""\
Reads the first reply byte at `(net_rx_ptr),0`. If zero, branches
to [`init_remote_session`](address:9859) to set up a fresh remote
session. Otherwise reads the validation byte at offset `&80` and
the local stored value at workspace offset `&0E`; on mismatch,
the remote session is rejected.""")
subroutine(0x98AF, "lang_0_insert_key",
    title="Language reply 0: insert remote keypress",
    description="""\
Reads the keycode from the reply at `(net_rx_ptr),&82` into `Y`,
sets `X=0`, calls [`commit_state_byte`](address:B05F) to record
the state change, and issues `OSBYTE &99` (insert into keyboard
buffer) to deliver the keypress to the local machine.""",
    on_entry={"a": "ignored (entry from reply dispatch)"})
subroutine(0x98BE, "wait_net_tx_ack",
    title="Wait for reply on open receive with timeout",
    description="""\
Despite the name, this does **not** wait for a TX acknowledgment.
It polls an open receive control block (bit 7 of `txcb_ctrl`,
set to `&7F` by [`init_txcb_port`](address:973F)) until the
NMI RX handler delivers a reply frame and sets bit 7.

Uses a three-level nested polling loop:

| Loop | Source | Default | Iterations |
|---|---|---|---|
| inner  | wraps from 0 | – | 256 |
| middle | wraps from 0 | – | 256 |
| outer  | [`rx_wait_timeout`](address:0D6E) | `&28` (40) | 40 |

Total: `256 × 256 × 40 = 2,621,440` poll iterations. At ~17
cycles per poll on a 2 MHz 6502, the default gives ~22 seconds.

On timeout, branches to `build_no_reply_error` to raise
`'No reply'`. Called by 6 sites across the protocol stack.""")
subroutine(0x9900, "cond_save_error_code",
    title="Conditionally store error code to workspace",
    description="""\
Tests bit 7 of [`fs_flags`](address:0D6C) (FS-selected
flag):

| Bit 7 | Action |
|---|---|
| clear | return immediately |
| set   | store `A` into `hazel_fs_last_error` (`&0E09`) |

This guards against writing error state when no filing system
is active. Called internally by the error-classification chain
and by `error_inline_log`.""",
    on_entry={"a": "error code to store"})
subroutine(0x9930, "fixup_reply_status_a",
    title="Substitute 'B' for 'A' in reply status byte",
    description="""\
Reads the FS reply status byte at (net_tx_ptr,X). If it is 'A'
(Acknowledge with no error), substitutes 'B' so downstream code
treats it as a soft error. CLV before falling through into
mask_error_class to ensure the no-extended-error path is taken.""",
    on_entry={"x": "indirect index into net_tx_ptr"},
    on_exit={"a": "reply status byte (with A->B substitution)",
             "v": "0 (clear)"})
subroutine(0x993B, "load_reply_and_classify",
    title="Load reply byte and classify error",
    description="""\
Single-byte prologue to
[`classify_reply_error`](address:993D): `LDA (net_tx_ptr,X)`
reads the FS reply status byte, then falls through. Single
caller (`&9B6C`, after a recv-and-classify path that already
has `X` set).""",
    on_entry={"x": "indirect index into net_tx_ptr"})
subroutine(0x993D, "classify_reply_error",
    title="Classify FS reply error code",
    description="""\
Forces `V=1` via `BIT always_set_v_byte` (signals the
extended-error path), masks the error code in `A` to 3 bits (the
error class 0..7), saves the class on the stack, and dispatches:

| Class | Path |
|---|---|
| 2 (station-related) | multi-line `build_no_reply_error` |
| other | `build_simple_error` |

Two callers: [`raise_escape_error`](address:9895) (with
`A=6`) and the FS reply dispatch at `&A0BD`.""",
    on_entry={"a": "error code byte"})
subroutine(0x99DF, "check_net_error_code",
    title="Translate net error: 'OK' → return, 'FS error' → append",
    description="""\
Reads the receive-attribute byte:

| Receive attribute | Action |
|---|---|
| non-zero | network error – branch to `handle_net_error` |
| zero, saved error = `&DE` (FS error code) | branch to `append_error_number` to add the FS-specific code to the error text |
| zero, saved error other | tail-jump to `&0100` (BRK error block) to trigger BRK and let MOS dispatch |""")
subroutine(0x9A3A, "append_drv_dot_num",
    title="Append 'net.station' decimal string to error text",
    description="""\
Reads network and station numbers from the TX control block at
offsets 3 and 2. Writes:

1. A space separator.
2. The network number as decimal (if non-zero).
3. A dot (`'.'`).
4. The station number as decimal digits.

into the error-text buffer at the current position.""",
    on_entry={"x": "error text buffer index"},
    on_exit={"x": "updated buffer index past appended text"})
subroutine(0x9A5E, "append_space_and_num",
    title="Append space and decimal number to error text",
    description="Writes a space character to the error text buffer\n"
    "at the current position (fs_load_addr_2), then falls\n"
    "through to append_decimal_num to convert the value\n"
    "in A to decimal digits with leading zero suppression.",
    on_entry={"a": "number to append (0-255)"})
subroutine(0x9A69, "append_decimal_num",
    title="Convert byte to decimal and append to error text",
    description="Extracts hundreds, tens and units digits by three\n"
    "successive calls to append_decimal_digit. Uses the\n"
    "V flag to suppress leading zeros — hundreds and tens\n"
    "are skipped when zero, but the units digit is always\n"
    "emitted.",
    on_entry={"a": "number to convert (0-255)"})
subroutine(0x9A7A, "append_decimal_digit",
    title="Extract and append one decimal digit",
    description="Divides Y by A using repeated subtraction to extract\n"
    "a single decimal digit. Stores the ASCII digit in the\n"
    "error text buffer at fs_load_addr_2 unless V is set\n"
    "and the quotient is zero (leading zero suppression).\n"
    "Returns the remainder in Y for subsequent digit\n"
    "extraction.",
    on_entry={"a": "divisor (100, 10, or 1)",
              "y": "number to divide",
              "v": "set to suppress leading zero"},
    on_exit={"y": "remainder after division",
             "v": "clear once a non-zero digit is emitted"})
subroutine(0x9B24, "init_tx_ptr_and_send",
    title="Point TX at zero-page TXCB and send",
    description="Sets net_tx_ptr/net_tx_ptr_hi to &00C0 (the\n"
    "standard TXCB location in zero page), then falls\n"
    "through to send_net_packet for transmission with\n"
    "retry logic.",
    on_exit={"a": "TX result code (0 = success; &40 jammed; &41 not "
             "listening; etc.) -- see send_net_packet"})
subroutine(0x9B2C, "send_net_packet",
    title="Transmit Econet packet with retry",
    description="""\
Two-phase transmit with retry. Loads retry count from
[`tx_retry_count`](address:0D6D) (default `&FF` = 255; 0
means retry forever). Each failed attempt waits in a nested
delay loop: `X` = TXCB control byte (typically `&80`), `Y` =
`&60`; total ~61 ms at 2 MHz (ROM-only fetches, unaffected by
video mode).

| Phase | Activation | Behaviour |
|---|---|---|
| 1 | always | runs the full count with escape disabled |
| 2 | only when `tx_retry_count = 0` | sets `need_release_tube` to enable escape checking, retries indefinitely |

With default `&FF`, phase 2 is never entered. Failures go to
[`load_reply_and_classify`](address:993B) (`'Line jammed'`,
`'Net error'`, etc.), distinct from the `'No reply'` timeout in
[`wait_net_tx_ack`](address:98BE).""",
    on_exit={"a": "TX result (0 = success; non-zero = error class "
             "consumed by the BRK path)"})
subroutine(0x9B81, "init_tx_ptr_for_pass",
    title="Set up TX pointer and send pass-through packet",
    description="Copies the template into the TX buffer (skipping\n"
    "&FD markers), saves original values on stack,\n"
    "then polls the ADLC and retries until complete.",
    on_exit={"a": "TX result (from poll_adlc_tx_status)"})
subroutine(0x9B89, "setup_pass_txbuf",
    title="Initialise TX buffer from pass-through template",
    description="Copies 12 bytes from pass_txbuf_init_table into the\n"
    "TX control block, pushing the original values on the\n"
    "stack for later restoration. Skips offsets marked &FD\n"
    "in the template. Starts transmission via\n"
    "poll_adlc_tx_status and retries on failure, restoring\n"
    "the original TX buffer contents when done.",
    on_exit={"a": "TX result (from poll_adlc_tx_status)"})
subroutine(0x9BB6, "poll_adlc_tx_status",
    title="Wait for TX ready, then start new transmission",
    description="""\
1. Polls [`tx_complete_flag`](address:0D60) via `ASL`
   (testing bit 7) until set, indicating any previous TX
   operation has completed and the ADLC is back in idle
   RX-listen mode.
2. Copies the TX control-block pointer from `net_tx_ptr` to
   `nmi_tx_block`.
3. Calls [`tx_begin`](address:8589), which performs a
   complete transmission from scratch (copies destination from
   TXCB to scout buffer, polls for INACTIVE, configures ADLC
   `CR1=&44 RX_RESET|TIE`, `CR2=&E7 RTS|CLR`, runs the full
   four-way handshake via NMI).
4. After [`tx_begin`](address:8589) returns, polls the TXCB
   first byte until bit 7 clears (NMI handler stores result
   there).

Result in `A`:

| Code | Meaning |
|---|---|
| `&00` | success |
| `&40` | jammed |
| `&41` | not listening |
| `&43` | no clock |
| `&44` | bad control byte |""",
    on_exit={"a": "TX result (&00 success / &40 jammed / &41 not "
             "listening / &43 no clock / &44 bad control byte)"})
subroutine(0x9BF5, "load_text_ptr_and_parse",
    title="Copy text pointer from FS options and parse string",
    description="Reads a 2-byte address from (fs_options)+0/1 into\n"
    "os_text_ptr (&00F2), resets Y to zero, then falls\n"
    "through to gsread_to_buf to parse the string at that\n"
    "address into the &0E30 buffer.",
    on_exit={"y": "0 (reset before GSINIT)"})
subroutine(0x9C00, "gsread_to_buf",
    title="Parse command line via GSINIT/GSREAD into hazel_parse_buf",
    description="""\
Calls GSINIT to initialise string reading, then loops calling
GSREAD to copy characters into [`hazel_parse_buf`](address:C030)
until end-of-string. Appends a CR terminator and sets
`fs_crc_lo`/`hi` to point at the buffer for subsequent parsing
routines. (Pre-HAZEL ROMs used `fs_filename_buf` at &0E30; the
4.21 build uses HAZEL.)""",
    on_entry={"y": "current command-line offset (consumed by GSINIT)"},
    on_exit={"y": "advanced past the parsed source"})
subroutine(0x9C22, "filev_handler",
    title="FILEV vector handler: OSFILE",
    description="""\
Reached via the FILEV vector at `&0212`. Sets up transfer
parameters via [`set_xfer_params`](address:93D7), loads the OS text
pointer and parses the filename via
[`load_text_ptr_and_parse`](address:9BF5),
[`mask_owner_access`](address:B2CF) clears the FS-selection bits,
and [`parse_access_prefix`](address:B22F) records any access-byte
prefix. Routes by `fs_last_byte_flag` bit: positive (read /
display) goes to `check_display_type`; negative (write / save)
falls into the create-new-file path.""",
    on_entry={"a": "OSFILE function code",
              "x, y": "control-block pointer (low, high)"})
subroutine(0x9C3E, "do_fs_cmd_iteration",
    title="Execute one iteration of a multi-step FS command",
    description="Called by match_fs_cmd for commands that enumerate\n"
    "directory entries. Sets port &92, sends the initial\n"
    "request via send_request_write, then synchronises the\n"
    "FS options and workspace state (order depends on the\n"
    "cycle flag at offset 6). Copies 4 address bytes,\n"
    "formats the filename field, sends via\n"
    "send_txcb_swap_addrs, and receives the reply.",
    on_entry={"y": "FS function code (matches send_request_write contract)"},
    on_exit={"a": "FS reply status"})
subroutine(0x9C85, "send_txcb_swap_addrs",
    title="Send TXCB and swap start/end addresses",
    description="If the 5-byte handle matches, returns\n"
    "immediately. Otherwise sets port &92, copies\n"
    "addresses, sends, waits for acknowledgment,\n"
    "and retries on address mismatch.",
    on_exit={"a": "FS reply status (or unchanged if handles matched -- "
             "the routine returns early when no work is needed)"})
subroutine(0x9CB5, "setup_dir_display",
    title="Compute display deltas and prep FS info request",
    description="""\
Iterates 4 times over paired (lo, hi) address words in the FS options
block at offsets &0E and &0A (loop body advances Y by 5 each pass).
For each pair, computes (high - low), saves both originals to
workspace at &00A6+Y (port_ws_offset region), and overwrites the
options entry with the difference so the caller can render 'load
addr', 'exec addr', 'length', etc. without redoing the subtraction.
Then copies 9 bytes of FS-options metadata into the TX buffer at
&C103, sets need_release_tube as the escapable flag, and stores FS
port &91 (info request) at &C102. Final tail-call dispatches the
request via send_request_write.""",
    on_exit={"a": "&91 (FS port for info request)",
             "x, y": "clobbered"})
subroutine(0x9D44, "print_load_exec_addrs",
    title="Print exec address and file length in hex",
    description="Prints the exec address as 5 hex bytes from\n"
    "(fs_options) offset 9 downwards, then the file\n"
    "length as 3 hex bytes from offset &0C. Each group\n"
    "is followed by a space separator via OSASCI.",
    on_exit={"a, x, y": "clobbered (print_hex_byte + OSASCI)"})
subroutine(0x9D4F, "print_5_hex_bytes",
    title="Print hex byte sequence from FS options",
    description="""\
Outputs `X+1` bytes from `(fs_options)` starting at offset `Y`,
decrementing `Y` for each byte (big-endian display order). Each
byte is printed as two hex digits via
[`print_hex_byte`](address:9236). Finishes with a trailing
space via OSASCI.

The default entry with `X=4` prints 5 bytes (a full 32-bit
address plus extent).""",
    on_entry={"x": "byte count minus 1 (default 4 for 5 bytes)",
              "y": "starting offset in (fs_options)"})
subroutine(0x9D5F, "copy_fsopts_to_zp",
    title="Copy FS options address bytes to zero page",
    description="Copies 4 bytes from (fs_options) at offsets 2-5\n"
    "into zero page at &00AE+Y. Used by\n"
    "do_fs_cmd_iteration to preserve the current address\n"
    "state. Falls through to skip_one_and_advance5 to\n"
    "advance Y past the copied region.",
    on_entry={"y": "destination offset within the &00AE.. zero-page "
              "region (also indexes the source via (fs_options),Y)"},
    on_exit={"y": "advanced by 5 (via skip_one_and_advance5 fall-through)",
             "a": "clobbered"})
subroutine(0x9D6B, "skip_one_and_advance5",
    title="Advance Y by 5",
    description="Entry point one INY before advance_y_by_4, giving\n"
    "a total Y increment of 5. Used to skip past a\n"
    "5-byte address/length structure in the FS options\n"
    "block.",
    on_entry={"y": "current offset"},
    on_exit={"y": "offset + 5",
             "a, x": "preserved"})
subroutine(0x9D6C, "advance_y_by_4",
    title="Advance Y by 4",
    description="Four consecutive INY instructions. Used as a\n"
    "subroutine to step Y past a 4-byte address field\n"
    "in the FS options or workspace structure.",
    on_entry={"y": "current offset"},
    on_exit={"y": "offset + 4"})
subroutine(0x9D71, "copy_workspace_to_fsopts",
    title="Copy workspace reply data to FS options",
    description="Copies bytes from the reply buffer at &0F02+Y\n"
    "into (fs_options) at offsets &0D down to 2. Used\n"
    "to update the FS options block with data returned\n"
    "from the file server. Falls through to\n"
    "retreat_y_by_4.",
    on_entry={"y": "current offset (controls how many bytes are copied "
              "before the loop terminates)"},
    on_exit={"y": "decremented by 4 (via retreat_y_by_4 fall-through)",
             "a": "clobbered"})
subroutine(0x9D7E, "retreat_y_by_4",
    title="Retreat Y by 4",
    description="Four consecutive DEY instructions. Companion to\n"
    "advance_y_by_4 for reverse traversal of address\n"
    "structures.",
    on_entry={"y": "current offset"},
    on_exit={"y": "offset - 4"})
subroutine(0x9D7F, "retreat_y_by_3",
    title="Retreat Y by 3",
    description="Three consecutive DEY instructions. Used by\n"
    "setup_transfer_workspace to step back through\n"
    "interleaved address pairs in the FS options block.",
    on_entry={"y": "current offset"},
    on_exit={"y": "offset - 3"})
subroutine(0x9D87, "check_and_setup_txcb",
    title="Set up data-transfer TXCB and dispatch reply",
    description="""\
Compares the 5-byte handle via
[`cmp_5byte_handle`](address:93E6); if unchanged, returns.
Otherwise:

1. Computes start / end addresses with overflow clamping.
2. Sets the port and control byte.
3. Sends the packet.
4. Dispatches on the reply sub-operation code.""",
    on_exit={"a": "FS reply sub-operation code (drives downstream "
             "dispatch)"})
subroutine(0x9DDC, "dispatch_osword_op",
    title="OSWORD &13 sub-operation triage (1-7)",
    description="""\
Stores the sub-operation code in
[`hazel_txcb_data`](address:C105) and triages by value:

| Value | Target |
|---|---|
| `0..6` | `dispatch_ops_1_to_6` |
| `7`    | [`setup_dir_display`](address:9CB5) (`*INFO` expansion) |
| `> 7`  | `skip_if_error` (routes through [`finalise_and_return`](address:9FB6)) |

Single caller (`&9CB2` in the OSWORD `&13` handler entry).""",
    on_entry={"a": "OSWORD sub-op code"})
subroutine(0x9E82, "format_filename_field",
    title="Format filename into fixed-width display field",
    description="Builds a 12-character space-padded filename at\n"
    "[`filename_buf`](address:10F3) for directory listing\n"
    "output. Sources the name from either the command line\n"
    "or the [`fs_cmd_data`](address:0F05) reply buffer\n"
    "depending on the value in [`fs_cmd_csd`](address:0F03).\n"
    "Truncates or pads to exactly 12 characters.",
    on_exit={"a, x, y": "clobbered"})
subroutine(0x9FB1, "close_all_fcbs",
    title="Close all FCBs (process_all_fcbs + finalise)",
    description="""\
Single-instruction wrapper: JSR process_all_fcbs to walk every FCB
slot and close each open file in turn, then fall through to
return_with_last_flag (which loads fs_last_byte_flag and finalises
caller state). Single caller (the OSFIND close-all path at &9EBA).""",
    on_exit={"a": "fs_last_byte_flag (loaded by return_with_last_flag)"})
subroutine(0x9FB4, "return_with_last_flag",
    title="Load last-byte flag and finalise",
    description="""\
Loads fs_last_byte_flag (&BD) into A and falls through to
finalise_and_return, which clears the receive-attribute byte and
restores caller's X/Y. The 12 inbound refs are mostly fall-through
exits from FS reply handlers that need to return the last-byte
status to their caller; only one site (&9FAE) reaches it via JSR.""",
    on_exit={"a": "fs_last_byte_flag",
             "x": "fs_options (restored by finalise_and_return)",
             "y": "fs_block_offset (restored by finalise_and_return)"})
subroutine(0x9FB6, "finalise_and_return",
    title="Clear receive-attribute and restore caller's X/Y",
    description="Common 7-byte exit sequence used at the end of "
    "format_filename_field, several FS reply handlers, and "
    "match_fs_cmd. Saves A across a call to store_rx_attribute(0) "
    "(which clears the receive-attribute byte), then restores X "
    "from fs_options and Y from fs_block_offset before returning. "
    "Effectively: 'finish processing, clear network state, restore "
    "caller's pointers'.\n"
    "\n"
    "One JSR caller (match_fs_cmd at &A599) plus 6 branch entries "
    "from format_filename_field's various exit paths.",
    on_entry={"a": "result code to return"},
    on_exit={"a": "preserved",
             "x": "fs_options low byte",
             "y": "fs_block_offset low byte"})

subroutine(0x9EAB, "argsv_handler",
    title="ARGSV vector handler: OSARGS",
    description="""\
Reached via the ARGSV vector at `&0214`. Verifies the FS workspace
checksum, stores the result as the last-byte flag, and sets the FS
options pointer. Routes by `A`: positive (`bit 7 clear`) dispatches
to a sub-operation table; bit 6 vs bit 5 of `A` then selects
between read-and-write paths via further branching.""",
    on_entry={"a": "OSARGS function code",
              "x": "control-block low byte",
              "y": "channel handle"})
subroutine(0x9FC2, "osfind_close_or_open",
    title="OSFIND dispatch: close-all, close-one, or open",
    description="""\
Triages the OSFIND function code in `A`:

| `A` | Meaning | Path |
|---|---|---|
| `≥ 2` | open for input / output / update | branch to `done_file_open` |
| `1`   | close one channel | go to `done_file_open` |
| `0`   | close all channels | load `A=5` (close-all return code) and fall through |

Single caller (the OSFIND vector table at `&9EED`).""",
    on_entry={"a": "OSFIND function code (0=close-all, 1=close-one, "
              ">=2 = open variants)"})
subroutine(0x9FCF, "clear_result",
    title="Set A=0 and finalise",
    description="""\
Loads A=0 and falls through to shift_and_finalise (LSR A / BPL
finalise_and_return). The LSR-then-BPL is the standard FS-handler
'success exit with carry clear' idiom. Two callers: the post-
return path at &9FD6 and the catalogue tail at tail_update_
catalogue (&A329).""",
    on_exit={"a": "0",
             "c": "0 (LSR of 0)"})
subroutine(0x9D0C, "recv_reply",
    title="Receive FS reply and stash result byte",
    description="""\
JSRs recv_and_process_reply, then falls through to store_result
(STX hazel_txcb_result; LDY #&0E to point at the protection-bits offset).
Single caller (the dispatch at &9C82).""",
    on_exit={"x": "FS result byte (also written to hazel_txcb_result)",
             "y": "&0E (FS options offset for protection)"})
subroutine(0xA0A9, "fscv_0_opt_entry",
    title="FSCV reason 0: read OSARGS",
    description="""\
Handles OSARGS via the FSCV vector. If `A=0` (initialise dot-seen
flag) clears the flag and proceeds. Compares `X` against 4 (number
of args): out-of-range exits via the OSARGS dispatch chain to a
shared error path; otherwise dispatches to the per-argument
handler. Reached via the FSCV vector with reason code 0.""",
    on_entry={"a": "OSARGS sub-function (0 = initialise)",
              "x": "argument index (0-3)"})
subroutine(0xA10B, "fscv_1_eof",
    title="FSCV reason 1: EOF check",
    description="""\
Verifies the FS workspace checksum, then loads the channel's
block-offset byte (`fs_block_offset`, `&BC`), pushes it on the
stack and stores the per-channel attribute reference in `hazel_chan_attr`.
The body proceeds to compare the buffer byte count with the file
length to decide whether the channel is at EOF. Reached via the
FSCV vector with reason code 1.""",
    on_entry={"y": "channel handle"},
    on_exit={"a": "0 = not at EOF, non-zero = EOF"})
subroutine(0xA12C, "update_addr_from_offset9",
    title="Update both address fields in FS options",
    description="""\
Calls [`add_workspace_to_fsopts`](address:A133) for offset
9 (the high address / exec address field), then falls through to
[`update_addr_from_offset1`](address:A131) to process offset
1 (the low address / load address field).""",
    on_exit={"a, x, y, c flag": "clobbered (4-byte arithmetic loop)"})
subroutine(0xA131, "update_addr_from_offset1",
    title="Update low address field in FS options",
    description="Sets Y=1 and falls through to\n"
    "add_workspace_to_fsopts to add the workspace\n"
    "adjustment bytes to the load address field at\n"
    "offset 1 in the FS options block.",
    on_entry={"c": "carry state passed to add_workspace_to_fsopts"})
subroutine(0xA133, "add_workspace_to_fsopts",
    title="Add workspace bytes to FS options with clear carry",
    description="Clears carry and falls through to\n"
    "adjust_fsopts_4bytes. Provides a convenient entry\n"
    "point when the caller needs addition without a\n"
    "preset carry.",
    on_entry={"y": "FS options offset for first byte"})
subroutine(0xA134, "adjust_fsopts_4bytes",
    title="Add or subtract 4 workspace bytes from FS options",
    description="""\
Processes 4 consecutive bytes at `(fs_options)+Y`, adding or
subtracting the corresponding 4-byte transfer-address record
from ANFS workspace.

The direction is controlled by bit 7 of `fs_load_addr_2`:

| Bit 7 | Operation |
|---|---|
| set   | subtract |
| clear | add |

Carry propagates across all 4 bytes for correct multi-byte
arithmetic.""",
    on_entry={"y": "FS options offset for first byte",
              "c": "carry input for first byte"})
label(0xA1EA, "return_success")
subroutine(0xA145, "store_adjusted_byte",
    title="Store adjusted byte and step the loop",
    description="""\
Tail of the address-adjustment 4-byte loop: STA (fs_options),Y /
INY / INX / BNE loop_adjust_byte / RTS. The BNE retries until X
has cycled through all 4 bytes; once X overflows back to 0 the
loop exits and the RTS returns. Single caller (the loop-body fall-
through at &A13F).""",
    on_entry={"a": "byte to store",
              "y": "current FS-options index",
              "x": "remaining-byte counter"})
subroutine(0xA14C, "gbpbv_handler",
    title="GBPBV vector handler: OSGBPB",
    description="""\
Reached via the GBPBV vector at
[`vec_gbpbv`](address:021C) after the
[`fs_vector_table`](address:8EA7) has copied the entry.
Verifies the FS workspace checksum, sets up transfer parameters,
masks the access prefix, and dispatches the OSGBPB sub-operation
in `A`:

| `A` | Operation |
|---|---|
| `1` | PUT bytes with pointer |
| `2` | PUT bytes |
| `3` | GET bytes with pointer |
| `4` | GET bytes |
| `5` | read disc title |
| `6` | read CSD |
| `7` | read library |
| `8` | read files in CSD |""",
    on_entry={"a": "OSGBPB function code (1-8)",
              "x, y": "control-block pointer (low, high)"})
subroutine(0xA1EF, "lookup_cat_entry_0",
    title="Look up channel from FS options offset 0",
    description="Loads the channel handle from (fs_options) at\n"
    "offset 0, then falls through to lookup_cat_slot_data\n"
    "to find the corresponding FCB entry.",
    on_exit={"a": "FCB flag byte from &1030+X",
             "x": "channel slot index"})
subroutine(0xA1F3, "lookup_cat_slot_data",
    title="Look up channel and return FCB flag byte",
    description="""\
Calls [`lookup_chan_by_char`](address:B847) to find the channel
slot for handle `A` in the channel table, then loads the FCB
slot-attribute byte from
[`hazel_fcb_slot_attr`](address:C230)+`X`. (Pre-HAZEL ROMs read
from &1030+X.)""",
    on_entry={"a": "channel handle"},
    on_exit={"a": "FCB slot-attribute byte",
             "x": "channel slot index"})
subroutine(0xA1FA, "setup_transfer_workspace",
    title="Prepare workspace for OSGBPB data transfer",
    description="""\
Orchestrates the setup for OSGBPB (get/put multiple bytes)
operations:

1. Look up the channel.
2. Copy the 6-byte address structure from FS options (skipping
   the hole at offset 8).
3. Determine transfer direction from the operation code:

   | Operation code parity | Direction | FS port |
   |---|---|---|
   | even | read  | `&91` |
   | odd  | write | `&92` |

4. Send the FS request.
5. Configure the TXCB address pairs for the actual
   data-transfer phase.
6. Dispatch to the appropriate handler.""",
    on_exit={"a": "FS reply status from the data-transfer phase"})
subroutine(0xA284, "recv_reply_preserve_flags",
    title="Receive and process reply, preserving flags",
    description="Wrapper around recv_and_process_reply that\n"
    "saves and restores the processor status register,\n"
    "so the caller\'s flag state is not affected by\n"
    "the reply processing.",
    on_exit={"a": "FS reply status",
             "p (flags)": "preserved across the call (PHP/PLP)"})
subroutine(0xA28A, "send_osbput_data",
    title="Send OSBPUT data block to file server",
    description="""\
Sets `Y=&15` (TX buffer size for OSBPUT data) and calls
[`save_net_tx_cb`](address:978A) to dispatch the TX. Then copies
the display flag from `hazel_fs_flags` to `hazel_txcb_byte_16` (TX header continuation).
Single caller in the OSBPUT-buffered-write path.""")
subroutine(0xA29F, "write_block_entry",
    title="Pre-write Tube-station check, fall into write_data_block",
    description="""\
Y=4 (FS-options offset for station). If tube_present is zero
(no Tube co-pro), branch forward to store_station_result and skip
the next compare; otherwise CMP (fs_options),Y to validate the
caller's station matches the saved Tube station. Falls through to
write_data_block. Single caller (&A16A in the OSWORD write path).""",
    on_entry={"y": "ignored (forced to 4)"})
subroutine(0xA2ED, "write_data_block",
    title="Write data block to destination or Tube",
    description="""\
| `tube_present` | Action |
|---|---|
| zero (no Tube) | copy directly from the `fs_cmd_data` buffer via `(fs_crc_lo)` |
| non-zero       | claim the Tube, set up the transfer address, write via R3 |""",
    on_exit={"a, x, y": "clobbered"})
subroutine(0xA329, "tail_update_catalogue",
    title="Catalogue-update exit (JMP clear_result)",
    description="""\
Single-instruction tail: JMP clear_result -- shared exit for the
catalogue-update paths after they have finished writing the new
entry. Two callers: &A300 (the success path) and &A38D (the
no-change path). Never returns directly (clear_result loads A=0
and tail-falls into finalise_and_return).""")
subroutine(0xA390, "tube_claim_c3",
    title="Claim the Tube via protocol &C3",
    description="Loops calling tube_addr_data_dispatch with\n"
    "protocol byte &C3 until the claim succeeds\n"
    "(carry set on return). Used before Tube data\n"
    "transfers to ensure exclusive access to the\n"
    "Tube co-processor interface.",
    on_entry={},
    on_exit={"a": "&C3 (the claim protocol byte left in A)",
             "c flag": "set (the claim succeeded -- this is the loop "
             "termination condition)"})
subroutine(0xA3BB, "print_fs_info_newline",
    title="Print station address and newline",
    description="Sets V (suppressing leading-zero padding on\n"
    "the network number) then prints the station\n"
    "address followed by a newline via OSNEWL.\n"
    "Used by *FS and *PS output formatting.",
    on_exit={"a, x, y": "clobbered (print_station_addr + OSNEWL)"})
subroutine(0xA3C4, "parse_fs_ps_args",
    title="Parse station address from *FS/*PS arguments",
    description="""\
Reads a station address in `net.station` format from the command
line, with the network number optional (defaults to local network).
Calls [`init_bridge_poll`](address:ABE9) to ensure the bridge
routing table is populated, then validates the parsed address
against known stations. The parsed-station value is stored in
`fs_work_7` (`&B7`).""",
    on_entry={"y": "current command-line offset"},
    on_exit={"x, y": "preserved (saved/restored via PHX/PHY)"})
subroutine(0xA3E7, "get_pb_ptr_as_index",
    title="Convert parameter block pointer to table index",
    description="Reads the first byte from the OSWORD parameter\n"
    "block pointer and falls through to\n"
    "byte_to_2bit_index to produce a 12-byte-aligned\n"
    "table index in Y.",
    on_exit={"a": "PB[0] (preserved through byte_to_2bit_index)",
             "y": "byte offset (0, 6, 12, ... up to &42)"})
subroutine(0xA3E9, "byte_to_2bit_index",
    title="Convert byte to 12-byte-aligned table index",
    description="Computes Y = A * 6 (via A*12/2) for indexing\n"
    "into the OSWORD handler workspace tables.\n"
    "Clamps Y to zero if the result exceeds &48,\n"
    "preventing out-of-bounds access.",
    on_entry={"a": "table entry number"},
    on_exit={"y": "byte offset (0, 6, 12, ... up to &42)"})
subroutine(0xA3FF, "net_1_read_handle",
    title="FS reply: read handle byte (no workspace lookup)",
    description="""\
Reads the inline handle byte directly from the RX buffer at
`(net_rx_ptr),Y` with `Y=&6F`, then branches into the shared
PB-store path. Used when the caller wants the raw handle byte from
the FS reply rather than the workspace-tracked value.""",
    on_exit={"a": "handle byte from RX buffer"})
subroutine(0xA405, "net_2_read_entry",
    title="FS reply: read handle byte from workspace table",
    description="""\
Calls [`get_pb_ptr_as_index`](address:A3E7) to convert the OSWORD
parameter-block pointer to a workspace-table index. On out-of-range
(`C=1`), returns zero. Otherwise reads the handle byte from
`nfs_workspace,Y`; if the slot is `?` (uninitialised marker), falls
through to the zero-return path; otherwise stores the real handle
into PB[0].""")
subroutine(0xA415, "net_3_close_handle",
    title="FS reply: close handle entry",
    description="""\
Calls [`get_pb_ptr_as_index`](address:A3E7) to look up the
workspace slot. On out-of-range, marks the workspace as
uninitialised. Otherwise rotates `fs_flags` bit 0 into carry (state
save), reads PB[0] (the handle to close), and proceeds with the
close path.""")
subroutine(0xA42F, "fscv_3_star_cmd",
    title="FSCV reason 3: process *<command> via FS",
    description="""\
Sets up text and transfer pointers via set_text_and_xfer_ptr, marks
spool / Tube state as inactive (fs_spool_handle = need_release_tube
= &FF), then calls match_fs_cmd with X=&35, Y=0 to look up the user's
text in the FS command table. The match-or-error result feeds into
the FS dispatch chain that follows. Single caller (the FSCV vector
table at &8CFA).""")
subroutine(0xA440, "cmd_fs_reentry",
    title="FS-command re-entry guard (BVC dispatch_fs_cmd)",
    description="""\
Single-instruction prologue: BVC dispatch_fs_cmd. Reached as the
fall-through target after a *RUN failure -- if V is clear (the
re-entry path is permitted) it branches into dispatch_fs_cmd to
re-attempt the command; otherwise falls through to error_syntax to
raise 'Syntax'. Single caller (the FS dispatch table at &8C4E).""")
subroutine(0xA45B, "match_fs_cmd",
    title="Match command name against FS command table",
    description="""\
Case-insensitive compare of the command line against
`cmd_table_fs` entries with bit-7-terminated names. Returns with
the matched entry address on success.""",
    on_entry={"x": "starting offset within cmd_table_fs (selects which "
              "sub-table is searched: NFS commands, FS commands, etc.)"},
    on_exit={"x": "byte offset just past the matched command name in "
             "cmd_table_fs (or end-of-table if no match)",
             "y": "command-line offset of the first non-name character "
             "(typically the argument start)",
             "z flag": "set on match, clear on no-match"})
subroutine(0xA4A2, "loop_skip_trail_spaces",
    title="Skip trailing spaces from FS command-line args",
    description="""\
Reads (fs_crc_lo),Y; on space, falls through to the per-char
advance; non-space exits to check_cmd_flags. Shared body with
skip_dot_and_spaces at &A4A8 (alt-entry that also accepts dots).
Single caller (the BNE retry at &A4A9).""",
    on_entry={"y": "current command-line offset"})
subroutine(0xA4E4, "fscv_2_star_run",
    title="FSCV reason 2: handle *RUN",
    description="""\
Saves the OS text pointer via
[`save_ptr_to_os_text`](address:B373), calls
[`mask_owner_access`](address:B2CF) to clear the FS-selection bit,
ORs in bit 1 (the *RUN-in-progress flag), and stores back to
[`hazel_fs_lib_flags`](address:C271). Falls through to the run-handling chain
that opens the file and starts execution. Reached via the FSCV
vector dispatch with reason code 2.""")
subroutine(0xA4F1, "cmd_run_via_urd",
    title="*RUN entry for URD-prefixed argument",
    description="""\
Reached from cmd_fs_operation at &8E35 when the first character of
the *RUN argument is '&' (the URD = User Root Directory prefix).
Saves the OS text pointer via save_ptr_to_os_text, masks the access
bits via mask_owner_access, clears bit 1 of the result, and stores
into hazel_fs_lib_flags. Falls through to cmd_run_load_mask which calls
parse_cmd_arg_y0 to begin parsing the rest of the *RUN argument.
Single caller; never returns directly (continues into the run
flow).""")
subroutine(0xA5A1, "error_bad_command",
    title="Raise 'Bad command' BRK error",
    description="""\
Loads error code &FE and tail-calls error_bad_inline with the inline
string 'command' -- error_bad_inline prepends 'Bad ' to produce the
final 'Bad command' message. Used by the FS command parser when no
table entry matches the user's input. Never returns.""")
subroutine(0xA5AE, "check_exec_addr",
    title="Validate exec address is non-zero",
    description="""\
Iterates X = 3..0 over the 4-byte exec-address copy at hazel_txcb_flag..hazel_exec_addr,
incrementing each byte. If any byte becomes non-zero (BNE),
branches forward to library_path_string (the OSCLI dispatch path). When all four
INC operations leave a zero result the address was &FFFFFFFF + 1 =
0 -- not a valid exec address -- and the routine falls through to
the no-exec-address handler. Single caller (&A51C in the *RUN
handler).""",
    on_entry={"a": "exec address bytes already in hazel_txcb_flag..hazel_exec_addr"},
    on_exit={"x": "0 if no valid exec; non-zero branch otherwise"})
subroutine(0xA5C3, "alloc_run_channel",
    title="Allocate FCB slot for *RUN target file",
    description="""\
Loads the saved OSWORD parameter byte at hazel_txcb_data, calls alloc_fcb_slot
to obtain a free channel index in A, transfers it into Y, then
clears the per-channel attribute byte at hazel_fcb_status,X. Used by the
*RUN argument-handling path at &A538 once the file is opened, to
reserve a channel for the running program.""",
    on_exit={"a": "channel attribute byte (cleared to 0)",
             "x": "FCB slot index",
             "y": "FCB slot index (copy of X)"})
subroutine(0xA638, "fsreply_3_set_csd",
    title="FS reply handler: select CSD station",
    description="""\
Single-instruction wrapper: JSR find_station_bit3 to record the
new current-selected-directory (CSD) station in the table, then
JMP return_with_last_flag to clean up and return. Single caller
(the FS reply dispatch at &9594).""",
    on_exit={"a": "fs_last_byte_flag (loaded by return_with_last_flag)"})
subroutine(0xA63E, "fsreply_5_set_lib",
    title="FS reply handler: set library station",
    description="""\
Two-instruction wrapper: `JSR
`[`flip_set_station_boot`](address:A6A6) to record the new library
station, then `JMP`
[`return_with_last_flag`](address:9FB4). Reached only via the FS
reply dispatch table.""")
subroutine(0xA644, "find_station_bit2",
    title="Find printer server station in table (bit 2)",
    description="Scans the 16-entry station table for a slot\n"
    "matching the current station/network address\n"
    "with bit 2 set (printer server active). Sets V\n"
    "if found, clears V if not. Falls through to\n"
    "allocate or update the matching slot with the\n"
    "new station address and status flags.",
    on_exit={"v flag": "set if matching slot already had bit 2; clear if "
             "newly allocated",
             "x": "table slot index of the matched/allocated entry"})
subroutine(0xA66F, "find_station_bit3",
    title="Find file server station in table (bit 3)",
    description="Scans the 16-entry station table for a slot\n"
    "matching the current station/network address\n"
    "with bit 3 set (file server active). Sets V\n"
    "if found, clears V if not. Falls through to\n"
    "allocate or update the matching slot with the\n"
    "new station address and status flags.",
    on_exit={"v flag": "set if matching slot already had bit 3; clear if "
             "newly allocated",
             "x": "table slot index of the matched/allocated entry"})
subroutine(0xA6A6, "flip_set_station_boot",
    title="Set boot option for a station in the table",
    description="Scans up to 16 station table entries for one\n"
    "matching the current address with bit 4 set\n"
    "(boot-eligible). Stores the requested boot type\n"
    "in the matching entry and calls\n"
    "restore_fs_context to re-establish the filing\n"
    "system state.",
    on_entry={"a": "boot type code to store"},
    on_exit={"a, x, y": "clobbered"})
subroutine(0xA6D5, "fsreply_1_boot",
    title="FS reply 1: copy boot handles + flag boot pending",
    description="""\
Closes all network channels via
[`close_all_net_chans`](address:B8F8), sets bit 6 of `fs_flags`
(`TSB &0D6C`, marking the boot-pending state), then loads the
boot type from the FS reply at `hazel_txcb_result` and stores it into both the
current-boot-type slot (`hazel_fs_flags`) and the FCB-flags table. Pushes
the boot type for the fall-through into `fsreply_2_copy_handles`
which copies the per-handle table.""")
subroutine(0xA6E5, "fsreply_2_copy_handles",
    title="FS reply 2: install handles and (optionally) boot",
    description="""\
Records the file-server / printer-server / library handles from
the I-AM reply into the station table by calling
[`find_station_bit2`](address:A644),
[`find_station_bit3`](address:A66F), and
[`flip_set_station_boot`](address:A6A6) in turn with the three
handle bytes loaded from the TXCB reply
([`hazel_txcb_data`](address:C105),
[`hazel_txcb_flag`](address:C106),
[`hazel_txcb_count`](address:C107)). PHP/PLP carry a flag across
the calls: when Carry is clear on entry the routine returns via
[`return_with_last_flag`](address:9FB4); when Carry is set it
continues into the boot path at
[`fsreply_2_handle_loop`](address:A70B), which OSCLIs
`-NET-FindLib`, optionally calls OSBYTE `&6D` to make the filing
system permanent, clears the auto-boot flag in
[`hazel_fs_lib_flags`](address:C271), and (unless CTRL is held)
falls through to [`boot_suffix_string`](address:A75F) to execute
the !Boot command. Reached only via the FS reply dispatch
table.""",
    on_entry={"a": "boot-type byte (saved on stack at entry)",
              "carry": "set when boot processing should follow"})
subroutine(0xA764, "boot_cmd_oscli",
    title="Look up boot command in boot_prefix_string table and OSCLI it",
    description="""\
Loads X = boot_prefix_string,Y (the low byte of the boot-command address),
sets Y=&A7 (high byte = &A7xx area where the boot strings live),
then JMPs to oscli with (X,Y) pointing at a CR-terminated command
string. Single caller (&A5D4 in the *RUN-then-* boot dispatch).""",
    on_entry={"y": "boot-command index"})
subroutine(0xA864, "osword_setup_handler",
    title="Push OSWORD handler address for RTS dispatch",
    description="Indexes the OSWORD dispatch table by X to\n"
    "push a handler address (hi then lo) onto the\n"
    "stack. Copies 3 bytes from the osword_flag\n"
    "workspace into the RX buffer, loads PB byte 0\n"
    "(the OSWORD sub-code), and clears svc_state.\n"
    "The subsequent RTS dispatches to the pushed\n"
    "handler address.",
    on_entry={"x": "OSWORD handler index (0-6)"})
subroutine(0xA901, "bin_to_bcd",
    title="Convert binary byte to BCD",
    description="Uses decimal mode (SED) with a count-up loop:\n"
    "starts at BCD 0 and adds 1 in decimal mode for\n"
    "each decrement of the binary input. Saves and\n"
    "restores the processor flags to avoid leaving\n"
    "decimal mode active. Called 6 times by\n"
    "save_txcb_and_convert for clock date/time\n"
    "conversion.",
    on_entry={"a": "binary value (0-99)"},
    on_exit={"a": "BCD equivalent"})
subroutine(0xAC47, "osword_14_handler",
    title="OSWORD &14 handler: bridge poll / station status",
    description="""\
Triages by `A`: `A >= 1` branches via `BCS` to
[`handle_tx_request`](address:ACB7) which reads the station and
network from `PB[1]`/`PB[2]` into the RX-block destination slots
and falls through to the burst-transfer body. `A = 0` (the
bridge-poll sub-code) falls through here: pushes `A`, calls
[`ensure_fs_selected`](address:8B4D) to bring ANFS up if needed,
pulls `A` back, sets `Y=&23` and calls
[`mask_owner_access`](address:B2CF) to clear FS-selection bits,
then runs the bridge-poll body.""",
    on_entry={"a": "OSWORD &14 sub-function code",
              "x, y": "OSWORD parameter block pointer (low, high)"})

subroutine(0xACED, "handle_burst_xfer",
    title="OSWORD &14 burst-transfer path: extend buffer end and TX",
    description="""\
Reached from [`handle_tx_request`](address:ACB7)'s `BNE` at
`&ACCC`. Calls [`init_ws_copy_wide`](address:ADFE) to copy the
workspace TXCB template into the wide-mode workspace slot, then
extends the buffer end-byte at `(net_rx_ptr)+&7B` by `3` to
account for the 3-byte burst header before falling through into
[`enable_irq_and_poll`](address:ACF8), which re-enables IRQs and
tail-jumps to [`send_net_packet`](address:9B2C).""",
    on_entry={"net_rx_ptr": "set up by handle_tx_request "
              "(dest station/network already stored at +&71/&72)"})

subroutine(0xACB7, "handle_tx_request",
    title="Sub-code 0: copy PB station/network into RX block, "
          "dispatch burst",
    description="""\
Sub-code-0 path of [`osword_14_handler`](address:AC47), reached
via the `BCC handle_tx_request` at `&AC49` when the caller's `A`
is 0. Reads two bytes from the OSWORD parameter block:

| Reg setup | Source     | Stored at        |
| --------- | ---------- | ---------------- |
| `Y=1`     | `PB[1]`    | (parked in `X`)  |
| `Y=2`     | `PB[2]`    | `(net_rx_ptr)+&72` (dest network) |
| `Y=3`     | (saved as `osword_flag` for the next byte read) | |
| `Y=&71`   | `X` (PB[1])| `(net_rx_ptr)+&71` (dest station) |

Wraps the body in `PHP`/`PLP` so the entry flags (carry clear from
the `BCC`) survive the workspace stores; the `BNE` after `PLP`
then dispatches to [`handle_burst_xfer`](address:ACED) when the
caller's `A` was non-zero (a defensive branch -- the `BCC` entry
guarantees `A=0` in 4.21, but the same body is the entry point
the burst path piggy-backs on).""",
    on_entry={"a": "OSWORD &14 sub-function code (caller's A; 0 via "
              "the BCC entry from osword_14_handler)",
              "ws_ptr_hi": "OSWORD parameter-block high byte"})
subroutine(0xAC67, "store_osword_pb_ptr",
    title="Store workspace pointer+1 to NFS workspace",
    description="Computes ws_ptr_hi + 1 and stores the resulting\n"
    "16-bit address at workspace offset &1C via\n"
    "store_ptr_at_ws_y. Then reads PB byte 1 (the\n"
    "transfer length) and adds ws_ptr_hi to compute\n"
    "the buffer end pointer, stored at workspace\n"
    "offset &20.")
subroutine(0xACAD, "store_ptr_at_ws_y",
    title="Store 16-bit pointer at workspace offset Y",
    description="Writes a 16-bit address to (nfs_workspace)+Y.\n"
    "The low byte comes from A; the high byte is\n"
    "computed from table_idx plus carry,\n"
    "supporting pointer arithmetic across page\n"
    "boundaries.",
    on_entry={"a": "pointer low byte",
              "y": "workspace offset",
              "c": "carry for high byte addition"})
subroutine(0xAA82, "copy_pb_byte_to_ws",
    title="Conditionally copy parameter block byte to workspace",
    description="If carry is set, loads a byte from the OSWORD\n"
    "parameter block at offset Y; if clear, uses\n"
    "the value already in A. Stores the result to\n"
    "workspace at the current offset. Decrements X\n"
    "and loops until the requested byte count is\n"
    "transferred.",
    on_entry={"c": "set to load from PB, clear to use A",
              "x": "byte count",
              "y": "PB source offset"})
subroutine(0xA910, "osword_10_handler",
    title="OSWORD &10 handler: send network packet",
    description="""\
ASL on [`tx_complete_flag`](address:0D60) shifts the old bit 7
into Carry. When that bit was clear (`C=0`, TX in progress) the
handler stores Y back through the parameter-block pointer at
`(ws_ptr_hi),Y` and RTS, leaving the caller a status byte. When
it was set (`C=1`, TX idle) execution falls through to the start
path at [`setup_ws_rx_ptrs`](address:A919), which seeds the
workspace pointers from [`net_rx_ptr_hi`](address:009D)/`#&6F`,
copies 16 bytes of the parameter block into the workspace via
[`copy_pb_byte_to_ws`](address:AA82) and JMPs to
[`tx_begin`](address:8589) to launch the transmission.""",
    on_entry={"x, y": "OSWORD parameter block pointer (low, high)"})
subroutine(0xA92D, "osword_11_handler",
    title="OSWORD &11 handler: receive network packet",
    description="""\
Reached via the OSWORD dispatch as well as via fall-through from
[`osword_10_handler`](address:A910). Configures the workspace
pointer from `nfs_workspace_hi`, saves the Econet interrupt state
via `ROR econet_flags`, and either uses the slot specified by the
caller (Y non-zero) or scans from slot 3 onwards via
[`byte_to_2bit_index`](address:A3E9) to find a free slot. Stores
the resulting status byte and the copied PB bytes back into the
caller's parameter block.""",
    on_entry={"x, y": "OSWORD parameter block pointer (low, high)"})

subroutine(0xA985, "osword_12_handler",
    title="OSWORD &12 handler: receive packet from workspace",
    description="""\
Reads `net_rx_ptr_hi` into `ws_ptr_lo`, sets `Y=&7F` and reads the
status byte from the RX block, then `Y=&80` to flag the packet as
processed. The body proceeds to copy the packet payload from the
RX buffer into the OSWORD parameter block via
[`copy_pb_byte_to_ws`](address:AA82).""",
    on_entry={"x, y": "OSWORD parameter block pointer (low, high)"})
entry(0xA9CC)
subroutine(0xA9CC, "osword_13_read_station",
    title="OSWORD &13 sub 0: read file server station",
    description="""\
Returns the current file server station and network numbers in
`PB[1..2]`. If ANFS is not active,
[`ensure_fs_selected`](address:8B4D) auto-selects it (raising `net
checksum` on failure) before the body runs.""")
entry(0xA9DA)
subroutine(0xA9DA, "osword_13_set_station",
    title="OSWORD &13 sub 1: set file server station",
    description="""\
Sets the file server station and network numbers from `PB[1..2]`.
The prologue at `&A9DA` calls
[`ensure_fs_selected`](address:8B4D) to verify ANFS is active
(auto-selecting it if not), then the body at
[`osword_13_set_station_body`](address:A9DD) processes all FCBs
and scans the 16-entry FCB table to reassign handles matching the
new station.""")
label(0xA9DD, "osword_13_set_station_body")

# Shared FS-selection prologue used by all OSWORD &13 sub-handlers.
# 5 callers: &A9CC (read_station), &A9DA (set_station), &AAC2
# (read_handles), &AAD0 (set_handles), &AC4C (init_bridge_poll site).
subroutine(0x8B4D, "ensure_fs_selected",
    title="Ensure ANFS is the active filing system",
    description="""\
If bit 7 of `fs_flags` is set (ANFS already active), `RTS` via
`return_from_save_text_ptr`. Otherwise calls `cmd_net_fs` to select
ANFS now; on failure, `JMP`s to
[`error_net_checksum`](address:90B5) to raise the `net checksum`
error. After successful selection, falls through to the body at
`&8B5A` which sets up the OSWORD parameter block pointer and
continues the caller's work.""",
    on_entry={"x, y": "OSWORD parameter block pointer (preserved across "
              "the cmd_net_fs call when selection happens)"})
subroutine(0xAA72, "osword_13_read_csd",
    title="OSWORD &13 sub 12: read CSD path",
    description="Reads 5 current selected directory path bytes\n"
    "from the RX workspace at offset &17 into\n"
    "PB[1..5]. Sets carry clear to select the\n"
    "workspace-to-PB copy direction.")
subroutine(0xAA75, "osword_13_write_csd",
    title="OSWORD &13 sub 13: write CSD path",
    description="Writes 5 current selected directory path bytes\n"
    "from PB[1..5] into the RX workspace at offset\n"
    "&17. Sets carry to select the PB-to-workspace\n"
    "copy direction.")
subroutine(0xAA91, "osword_13_read_ws_pair",
    title="OSWORD &13 sub 2: read workspace byte pair",
    description="Reads 2 bytes from the NFS workspace page\n"
    "starting at offset 1 into PB[1..2]. Uses\n"
    "nfs_workspace_hi as the page and\n"
    "copy_pb_byte_to_ws with carry clear for the\n"
    "workspace-to-PB direction.")
subroutine(0xAA9D, "osword_13_write_ws_pair",
    title="OSWORD &13 sub 3: write workspace byte pair",
    description="Writes 2 bytes from PB[1..2] into the NFS\n"
    "workspace at offsets 2 and 3. Then calls\n"
    "init_bridge_poll and conditionally clears\n"
    "the workspace byte if the bridge status\n"
    "changed.")
subroutine(0xAAB2, "osword_13_read_prot",
    title="OSWORD &13 sub 4: read protection mask",
    description="Returns the current protection mask (ws_0d68)\n"
    "in PB[1].")
subroutine(0xAAB8, "osword_13_write_prot",
    title="OSWORD &13 sub 5: write protection mask",
    description="""\
Loads the new protection mask from `PB[1]` and falls through into
[`set_ws_pair_0d68_0d69`](address:AABB) which mirrors it into the
ACR/SR-format byte pair at `&0D68` / `&0D69` that ANFS uses for its
own state tracking.""")
subroutine(0xAABB, "set_ws_pair_0d68_0d69",
    title="Store A in both ws_0d68 and ws_0d69",
    description="""\
Copies `A` to both [`ws_0d68`](address:0D68) and
[`ws_0d69`](address:0D69), then `RTS`. The bytes carry ACR/SR-style
flag layouts that ANFS uses internally; nothing in this ROM flushes
them to the live System VIA. Two callers:
[`nfs_init_body`](address:8F38) at `&8FA6` (where A is `0` or
`&FF` based on FS-options bit 6) and
[`cmd_prot`](address:B6D2) at `&B6D9` (the *Prot path).
A 2-store-and-return convenience to keep both call sites flat.""",
    on_entry={"a": "value to mirror into both workspace bytes"})
entry(0xAAC2)
subroutine(0xAAC2, "osword_13_read_handles",
    title="OSWORD &13 sub 6: read FCB handle info",
    description="""\
Returns the 3-byte FCB handle/port data from the workspace at
`C271[1..3]` into `PB[1..3]`. If ANFS is not active,
[`ensure_fs_selected`](address:8B4D) auto-selects it before the
body runs.""")
entry(0xAAD0)
subroutine(0xAAD0, "osword_13_set_handles",
    title="OSWORD &13 sub 7: set FCB handles",
    description="Validates and assigns up to 3 FCB handles\n"
    "from PB[1..3]. Each handle value (&20-&2F)\n"
    "indexes the channel tables. For valid handles\n"
    "with the appropriate flag bit, stores the\n"
    "station and FCB index, then updates flag bits\n"
    "across all FCB entries via update_fcb_flag_bits.")
subroutine(0xAB43, "update_fcb_flag_bits",
    title="Update FCB flag bits across all entries",
    description="Scans all 16 FCB entries in hazel_fcb_status. For each\n"
    "entry with bit 6 set, tests the Y-specified\n"
    "bit mask: if matching, ORs bit 5 into the\n"
    "flags; if not, leaves bit 5 clear. In both\n"
    "cases, inverts and clears the tested bits.\n"
    "Preserves X.",
    on_entry={"y": "flag bit mask to test",
              "x": "current FCB index (preserved)"})
subroutine(0xAB68, "osword_13_read_rx_flag",
    title="OSWORD &13 sub 8: read RX control block flag",
    description="Returns byte 1 of the current RX control\n"
    "block in PB[1].")
subroutine(0xAB71, "osword_13_read_rx_port",
    title="OSWORD &13 sub 9: read RX port byte",
    description="Returns byte &7F of the current RX control\n"
    "block in PB[1], and stores &80 in PB[2].")
subroutine(0xAB7F, "osword_13_read_error",
    title="OSWORD &13 sub 10: read error flag",
    description="""\
Returns the latched FS last-error byte
([`hazel_fs_last_error`](address:C009)) in `PB[1]`. Falls through
into [`store_a_to_pb_1`](address:AB82).""")
subroutine(0xAB82, "store_a_to_pb_1",
    title="Store A to OSWORD parameter block at offset 1",
    description="Increments Y to 1 and stores A into the\n"
    "OSWORD parameter block via (ws_ptr_hi),Y.\n"
    "Used by OSWORD 13 sub-handlers to return a\n"
    "single result byte.",
    on_entry={"A": "value to store"},
    on_exit={"Y": "1"})
subroutine(0xAB86, "osword_13_read_context",
    title="OSWORD &13 sub 11: read context byte",
    description="""\
Returns the FS context/error code
([`hazel_fs_error_code`](address:C008)) in `PB[1]` when bit 7 is
clear; if bit 7 is set the value is left alone (the BPL skips the
store). Tail-merges into [`store_a_to_pb_1`](address:AB82).""")
subroutine(0xAB8B, "osword_13_read_free_bufs",
    title="OSWORD &13 sub 14: read printer buffer free space",
    description="Returns the number of free bytes remaining in\n"
    "the printer spool buffer (&6F minus spool_buf_idx)\n"
    "in PB[1]. The buffer starts at offset &25 and can\n"
    "hold up to &4A bytes of spool data.")
subroutine(0xAB93, "osword_13_read_ctx_3",
    title="OSWORD &13 sub 15: read retry counts",
    description="Returns the three retry count values in\n"
    "PB[1..3]: PB[1] = transmit retry count\n"
    "(default &FF = 255), PB[2] = receive poll\n"
    "count (default &28 = 40), PB[3] = machine\n"
    "peek retry count (default &0A = 10). Setting\n"
    "transmit retries to 0 means retry forever.")
subroutine(0xAB9E, "osword_13_write_ctx_3",
    title="OSWORD &13 sub 16: write retry counts",
    description="Sets the three retry count values from\n"
    "PB[1..3]: PB[1] = transmit retry count,\n"
    "PB[2] = receive poll count, PB[3] = machine\n"
    "peek retry count.")
subroutine(0xABA9, "osword_13_bridge_query",
    title="OSWORD &13 sub 17: query bridge status",
    description="Calls init_bridge_poll, then returns the\n"
    "bridge status. If bridge_status is &FF (no bridge),\n"
    "stores 0 in PB[0]. Otherwise stores bridge_status\n"
    "in PB[1] and conditionally updates PB[3]\n"
    "based on station comparison.")
subroutine(0xABE9, "init_bridge_poll",
    title="Initialise Econet bridge routing table",
    description="Checks the bridge status byte: if &FF\n"
    "(uninitialised), broadcasts a bridge query\n"
    "packet and polls for replies. Each reply\n"
    "adds a network routing entry to the bridge\n"
    "table. Skips the broadcast if the table has\n"
    "already been populated from a previous call.",
    on_exit={"a, x, y": "clobbered when the broadcast path runs"})
subroutine(0xACF8, "enable_irq_and_poll",
    title="Enable interrupts and send Econet packet",
    description="Executes CLI to re-enable interrupts, then\n"
    "falls through to send_net_packet. Used after\n"
    "a sequence that ran with interrupts disabled\n"
    "to ensure the packet is sent with normal\n"
    "interrupt handling active.",
    on_entry={"i flag": "may be set (caller had IRQs off); CLI clears it"},
    on_exit={"i flag": "clear (interrupts enabled)"})
subroutine(0xACFC, "netv_handler",
    title="NETV handler: OSWORD dispatch",
    description="""\
Installed as the NETV handler via `write_vector_entry`. Saves all
registers, reads the OSWORD number from the stack, and dispatches
OSWORDs 0-8 via [`push_osword_handler_addr`](address:AD15).
OSWORDs `>= 9` are ignored (registers restored, RTS returns to
MOS). The handler's address lives in the extended vector data
area together with the other [`fs_vector_table`](address:8EA7)
entries.""",
    on_entry={"a": "OSWORD number (read from stacked A on entry)",
              "x, y": "PB pointer low/high (per OSWORD calling convention)"},
    on_exit={"a, x, y, p": "restored from stack"})
subroutine(0xAD15, "push_osword_handler_addr",
    title="Push OSWORD handler address for RTS dispatch",
    description="Indexes the OSWORD handler dispatch table\n"
    "using the current OSWORD number to push the\n"
    "handler's address (hi/lo) onto the stack.\n"
    "Reloads the OSWORD number from osbyte_a_copy\n"
    "so the dispatched handler can identify the\n"
    "specific call.",
    on_entry={"a": "OSWORD number (0-8) -- table index"},
    on_exit={"a": "OSWORD number (re-loaded for the handler's use)"})
entry(0xAD32)
subroutine(0xAD32, "osword_4_handler",
    title="OSWORD &04 handler: clear C, send abort",
    description="""\
Reaches the stack via `TSX`, clears bit 0 of the stacked processor
status (`ROR stack_page_6,X` then `ASL stack_page_6,X` -- a
read-modify cycle that lands the carry-out where bit 0 of the
saved P was), so the caller resumes with `C=0`. Stores the
caller's `Y` into NFS workspace at offset `&DA`, then falls
through to [`tx_econet_abort`](address:AD40) with `A=0` to
transmit a clean disconnect packet.""",
    on_entry={"y": "OSWORD parameter byte (saved into nfs_workspace+&DA)"})
subroutine(0xAD40, "tx_econet_abort",
    title="Send Econet abort/disconnect packet",
    description="Stores the abort code in workspace, configures\n"
    "the TX control block with control byte &80\n"
    "(immediate operation flag), and transmits the\n"
    "abort packet. Used to cleanly disconnect from\n"
    "a remote station during error recovery.",
    on_entry={"a": "abort code (stored in workspace before TX)"})
subroutine(0xAD64, "netv_claim_release",
    title="OSWORD 7 handler: claim/release network resources",
    description="Handles OSWORD 7 (SOUND) intercepted via NETV.\n"
    "Searches the claim code table in two passes:\n"
    "first 11 entries (state 2), then all 18 (state\n"
    "3). On match, saves 3 tube state bytes to\n"
    "workspace and sends an abort with the state\n"
    "code. For state 3 matches, also polls workspace\n"
    "for a response and restores the caller's stack\n"
    "frame from the saved bytes.",
    on_entry={"a": "OSWORD 7 number (validated by caller)"})
subroutine(0xADB8, "match_rx_code",
    title="Search receive code table for match",
    description="Scans a table of receive operation codes\n"
    "starting at index X, comparing each against A.\n"
    "Returns with Z set if a match is found, Z clear\n"
    "if the end-of-table marker is reached.",
    on_entry={"a": "receive code to match",
              "x": "starting table index"},
    on_exit={"z": "set if match found"})
subroutine(0xADD3, "osword_8_handler",
    title="OSWORD 7/8 handler: copy PB to workspace and abort",
    description="Handles OSWORD 7 or 8 by copying 15 bytes from\n"
    "the parameter block to workspace at offset &DB,\n"
    "storing the OSWORD number at offset &DA, setting\n"
    "control value &E9, and sending an abort packet.\n"
    "Returns via tx_econet_abort. Rejects other\n"
    "OSWORD numbers by returning immediately.",
    on_entry={"a": "OSWORD number (must be 7 or 8 to be processed)"})
subroutine(0xADFE, "init_ws_copy_wide",
    title="Initialise workspace copy in wide mode (14 bytes)",
    description="Copies 14 bytes to workspace offset &7C.\n"
    "Falls through to the template-driven copy\n"
    "loop which handles &FD (skip), &FE (end),\n"
    "and &FC (page pointer) markers.",
    on_entry={"x": "template source offset (within ws_txcb_template_data)"})
subroutine(0xAE07, "init_ws_copy_narrow",
    title="Initialise workspace copy in narrow mode (27 bytes)",
    description="Sets up a 27-byte copy to workspace offset &17,\n"
    "then falls through to ws_copy_vclr_entry for\n"
    "the template-driven copy loop. Used for the\n"
    "compact workspace initialisation variant.",
    on_entry={"x": "template source offset"})
subroutine(0xAE0B, "ws_copy_vclr_entry",
    title="Template-driven workspace copy with V clear",
    description="Processes a template byte array to initialise\n"
    "workspace. Special marker bytes: &FE terminates\n"
    "the copy, &FD skips the current offset, and &FC\n"
    "substitutes the workspace page pointer. All\n"
    "other values are stored directly to the\n"
    "workspace at the current offset.",
    on_entry={"x": "template source offset",
              "y": "destination offset within NFS workspace",
              "v flag": "clear (controls a downstream branch in the "
              "shared body; init_ws_copy_wide / _narrow enter with V=0)"},
    on_exit={"a, x, y": "clobbered"})
subroutine(0xAE5A, "netv_spool_check",
    title="OSWORD 5 handler: check spool PB and reset buffer",
    description="Handles OSWORD 5 intercepted via NETV. Checks\n"
    "if X-1 matches osword_pb_ptr and bit 0 of\n"
    "&00D0 is clear. If both conditions are met,\n"
    "falls through to reset_spool_buf_state to\n"
    "reinitialise the spool buffer for new data.",
    on_entry={"x": "OSWORD parameter block low byte (X-1 compared "
              "against osword_pb_ptr)"})
subroutine(0xAE6F, "netv_print_data",
    title="OSWORD 1-3 handler: drain printer buffer",
    description="Handles OSWORDs 1-3 intercepted via NETV.\n"
    "When X=1, drains the printer buffer (OSBYTE\n"
    "&91, buffer 3) into the receive buffer, sending\n"
    "packets via process_spool_data when the buffer\n"
    "exceeds &6E bytes. When X>1, routes to\n"
    "handle_spool_ctrl_byte for spool state control.",
    on_entry={"x": "1 = drain printer buffer; >1 = control byte path"})
subroutine(0xAE64, "reset_spool_buf_state",
    title="Reset spool buffer to initial state",
    description="Sets the spool buffer pointer (`spool_buf_idx`)\n"
    "to `&21` and the control byte (`ws_0d6a`) to `&41`\n"
    "(ready for new data). Called after processing a\n"
    "complete spool data block.",
    on_entry={},
    on_exit={"a, y": "clobbered"})
subroutine(0xAE94, "append_byte_to_rxbuf",
    title="Append byte to receive buffer",
    description="Stores A in the receive buffer at the current\n"
    "buffer index (ws_ptr_lo), then increments the\n"
    "index. Used to accumulate incoming spool data\n"
    "bytes before processing.",
    on_entry={"a": "byte to append"})
subroutine(0xAE9D, "handle_spool_ctrl_byte",
    title="Handle spool control byte and flush buffer",
    description="Rotates bit 0 of the control byte into carry\n"
    "for mode selection (print vs spool), appends\n"
    "the byte to the buffer, calls process_spool_data\n"
    "to transmit the accumulated data, and resets\n"
    "the buffer state ready for the next block.",
    on_entry={"a": "control byte (bit 0 selects mode: 0 = print, "
              "1 = spool)"},
    on_exit={"a, x, y": "clobbered"})
subroutine(0xAEB8, "process_spool_data",
    title="Transmit accumulated spool buffer data",
    description="Copies the workspace state to the TX control\n"
    "block, sends a disconnect reply if the previous\n"
    "transfer requires acknowledgment, then handles\n"
    "the spool output sequence by setting up and\n"
    "sending the pass-through TX buffer.",
    on_exit={"a": "TX result (from setup_pass_txbuf)"})
subroutine(0xAF80, "err_printer_busy",
    title="Raise 'Printer busy' error",
    description="""\
Loads error code &A6 and tail-calls error_inline_log with the inline
string 'Printer busy'. Called when an attempt is made to enable a
printer server while one is already active. Never returns.""")
subroutine(0xAFA6, "send_disconnect_reply",
    title="Send Econet disconnect reply packet",
    description="Sets up the TX pointer, copies station\n"
    "addresses, matches the station in the table,\n"
    "and sends the response. Waits for\n"
    "acknowledgment before returning.",
    on_exit={"a": "TX result code"})
subroutine(0xB01A, "lang_2_save_palette_vdu",
    title="Language reply 2: save palette / VDU state",
    description="""\
Reached via the language-reply dispatch table when a remote sends
reply code 2 ('save palette and VDU state'). Saves the current
template byte from `osword_flag` on the stack, sets up the
workspace pointer (`nfs_workspace`) to the appropriate offset, and
copies the palette / VDU state from MOS workspace at `&0350` into
the workspace transmit buffer for forwarding back to the
station.""")
subroutine(0xB05F, "commit_state_byte",
    title="Copy current state byte to committed state",
    description="Reads the working state byte from workspace and\n"
    "stores it to the committed state location. Used\n"
    "to finalise a state transition after all related\n"
    "workspace fields have been updated.",
    on_exit={"a": "= the committed value"})
subroutine(0xB066, "serialise_palette_entry",
    title="Serialise palette register to workspace",
    description="Reads the current logical colour for a palette\n"
    "register via OSBYTE &0B and stores both the\n"
    "palette value and the display mode information\n"
    "in the workspace block. Used during remote\n"
    "screen state capture.",
    on_entry={"x": "palette register index (0-15)",
              "y": "destination workspace offset (palette + mode pair)"},
    on_exit={"y": "advanced past the 2-byte pair",
             "a, x": "clobbered (OSBYTE)"})
subroutine(0xB081, "read_osbyte_to_ws_x0",
    title="Read OSBYTE with X=0 and store to workspace",
    description="Sets X=0 then falls through to read_osbyte_to_ws\n"
    "to issue the OSBYTE call and store the result.\n"
    "Used when the OSBYTE parameter X must be zero.",
    on_entry={"y": "destination workspace offset"},
    on_exit={"y": "incremented past the stored byte",
             "a, x": "clobbered (OSBYTE)"})
subroutine(0xB083, "read_osbyte_to_ws",
    title="Issue OSBYTE from table and store result",
    description="Loads the OSBYTE function code from the next\n"
    "entry in the OSBYTE table, issues the call, and\n"
    "stores the Y result in workspace at the current\n"
    "offset. Advances the table pointer for the next\n"
    "call.",
    on_entry={"x": "OSBYTE X parameter",
              "y": "destination workspace offset"},
    on_exit={"y": "incremented past the stored byte",
             "a, x": "clobbered"})

# --- cmd_ex subroutines ---

subroutine(0xB118, "fscv_5_cat",
    title="FSCV reason 5: catalogue (*CAT)",
    description="""\
Sets up transfer parameters via [`set_xfer_params`](address:93D7),
clears the library bit in `hazel_fs_lib_flags` via the
`ROR`/`CLC`/`ROL` idiom that uses carry to preserve other flags,
and falls through to `cat_set_lib_flag` to issue the FS examine
request. Reached via the FSCV vector with reason code 5.""")
subroutine(0xB21A, "print_10_chars",
    title="Print 10 characters from reply buffer",
    description="Sets Y=10 and falls through to\n"
    "print_chars_from_buf. Used by cmd_ex to print\n"
    "fixed-width directory title, directory name, and\n"
    "library name fields.",
    on_entry={"x": "buffer offset to start printing from"})
subroutine(0xB21C, "print_chars_from_buf",
    title="Print Y characters from buffer via OSASCI",
    description="Loops Y times, loading each byte from fs_cmd_data+X\n"
    "and printing it via OSASCI. Advances X after\n"
    "each character, leaving X pointing past the\n"
    "last printed byte.",
    on_entry={"x": "buffer offset", "y": "character count"})
subroutine(0xB22A, "parse_cmd_arg_y0",
    title="Parse command argument from offset zero",
    description="Sets Y=0 and falls through to parse_filename_arg\n"
    "for GSREAD-based filename parsing with prefix\n"
    "character handling.",
    on_exit={"y": "advanced past the parsed argument"})
subroutine(0xB22C, "parse_filename_arg",
    title="Parse filename via GSREAD with prefix handling",
    description="""\
Calls [`gsread_to_buf`](address:9C00) to read the command-line
string into [`hazel_parse_buf`](address:C030) (the 4.21 HAZEL
parse buffer at &C030), then falls through to
[`parse_access_prefix`](address:B22F) to process `'&'`, `':'`,
`'.'` and `'#'` prefix characters.""",
    on_entry={"y": "current command-line offset (consumed by gsread_to_buf)"},
    on_exit={"y": "advanced past the parsed argument"})
subroutine(0xB22F, "parse_access_prefix",
    title="Parse access and FS selection prefix characters",
    description="Examines the first character(s) of the parsed\n"
    "buffer at &C030 for prefix characters: '&' sets\n"
    "the FS selection flag (bit 6 of hazel_fs_lib_flags) and\n"
    "strips the prefix, ':' with '.' also triggers FS\n"
    "selection, '#' is accepted as a channel prefix.\n"
    "Raises 'Bad file name' for invalid combinations\n"
    "like '&.' followed by CR.")
subroutine(0xB251, "strip_token_prefix",
    title="Strip first character from parsed token buffer",
    description="Shifts all bytes in the &C030 buffer left by\n"
    "one position (removing the first character),\n"
    "then trims any trailing spaces by replacing\n"
    "them with CR terminators. Used after consuming\n"
    "a prefix character like '&' or ':'.",
    on_exit={"x": "preserved (saved/restored via PHA/PLA)",
             "a": "clobbered"})
subroutine(0xB29F, "copy_arg_to_buf_x0",
    title="Copy argument to TX buffer from offset zero",
    description="Sets X=0 and falls through to copy_arg_to_buf\n"
    "then copy_arg_validated. Provides the simplest\n"
    "entry point for copying a single parsed argument\n"
    "into the TX buffer at position zero.",
    on_exit={"x": "TX buffer offset just past the copied argument",
             "y": "advanced past the source argument"})
subroutine(0xB2A1, "copy_arg_to_buf",
    title="Copy argument to TX buffer with Y=0",
    description="Sets Y=0 and falls through to copy_arg_validated\n"
    "with carry set, enabling '&' character validation.\n"
    "X must already contain the destination offset\n"
    "within the TX buffer.",
    on_entry={"x": "destination offset within the TX buffer"},
    on_exit={"x": "TX buffer offset just past the copied argument",
             "y": "advanced past the source argument"})
subroutine(0xB2A3, "copy_arg_validated",
    title="Copy command line characters to TX buffer",
    description="Copies characters from (fs_crc_lo)+Y to fs_cmd_data+X\n"
    "until a CR terminator is reached. With carry set,\n"
    "validates each character against '&' — raising\n"
    "'Bad file name' if found — to prevent FS selector\n"
    "characters from being embedded in filenames.",
    on_entry={"x": "TX buffer destination offset",
              "y": "command line source offset",
              "c": "set to enable '&' validation"})
label(0xB2C8, "done_trim_spaces")
subroutine(0xB2CF, "mask_owner_access",
    title="Clear FS selection flags from options word",
    description="""\
`AND`s the `&C271` (`hazel_fs_lib_flags`) byte with `&1F`, clearing the
FS selection flag (bit 6) and other high bits to retain only the
5-bit owner-access mask. Called before parsing to reset the prefix
state from a previous command. 12 callers.""",
    on_exit={"a": "masked value"})
subroutine(0xB2E4, "ex_print_col_sep",
    title="Print column separator or newline for *Ex/*Cat",
    description="In *Cat mode, increments a column counter modulo 4\n"
    "and prints a two-space separator between entries,\n"
    "with a newline at the end of each row. In *Ex\n"
    "mode (fs_spool_handle negative), prints a newline\n"
    "after every entry. Scans the entry data and loops\n"
    "back to print the next entry's characters.")

# --- cmd_remove subroutines ---

subroutine(0xB327, "print_num_no_leading",
    title="Print decimal number with leading zero suppression",
    description="""\
Sets `V=1` via `BIT always_set_v_byte` (the `&FF` constant at
&9769, whose bit 6 sets V) to enable leading-zero suppression
in [`print_decimal_3dig`](address:B32A), then falls through to
that routine. Used by [`print_station_id`](address:90C7) for
compact station number display.""",
    on_entry={"a": "number to print (0-255)"})
subroutine(0xB32A, "print_decimal_3dig",
    title="Print byte as 3-digit decimal via OSASCI",
    description="Extracts hundreds, tens and units digits by\n"
    "successive calls to print_decimal_digit. The V\n"
    "flag controls leading zero suppression: if set,\n"
    "zero digits are skipped until a non-zero digit\n"
    "appears. V is always cleared before the units\n"
    "digit to ensure at least one digit is printed.",
    on_entry={"a": "number to print (0-255)",
              "v": "set to suppress leading zeros"})
subroutine(0xB338, "print_decimal_digit",
    title="Print one decimal digit by repeated subtraction",
    description="Initialises X to '0'-1 and loops, incrementing X\n"
    "while subtracting the divisor from Y. On underflow,\n"
    "adds back the divisor to get the remainder in Y.\n"
    "If V is set, suppresses leading zeros by skipping\n"
    "the OSASCI call when the digit is '0'.",
    on_entry={"a": "divisor", "y": "value to divide"},
    on_exit={"y": "remainder after division"})
subroutine(0xB357, "cmd_info_dispatch",
    title="*Info command handler",
    description="""\
Dispatched from the star-command table at index &28. Clears the
owner-only access bits via [`mask_owner_access`](address:B2CF),
then writes the two-byte FS command prefix `'i' '.'` into
[`hazel_txcb_data`](address:C105)/[`hazel_txcb_flag`](address:C106),
saves the command-line pointer with
[`save_ptr_to_os_text`](address:B373), parses the *Info argument
via [`parse_cmd_arg_y0`](address:B22A), copies it into the TX
buffer at offset 2 with [`copy_arg_to_buf`](address:B2A1), and
JMPs to [`send_cmd_and_dispatch`](address:8E3C) to send the
request to the file server.""",
    on_entry={"y": "command-line offset in text pointer"})
subroutine(0xB373, "save_ptr_to_os_text",
    title="Copy text pointer to OS text pointer workspace",
    description="Saves fs_crc_lo/hi into the MOS text pointer\n"
    "locations at &00F2/&00F3. Preserves A on the\n"
    "stack. Called before GSINIT/GSREAD sequences\n"
    "that need to parse from the current command\n"
    "line position.",
    on_exit={"a": "preserved (PHA/PLA)"})
subroutine(0xB37F, "skip_to_next_arg",
    title="Advance past spaces to the next command argument",
    description="Scans (fs_crc_lo)+Y for space characters,\n"
    "advancing Y past each one. Returns with A\n"
    "holding the first non-space character, or CR\n"
    "if the end of line is reached. Used by *CDir\n"
    "and *Remove to detect extra arguments.",
    on_entry={"y": "starting offset (where to begin scanning)"},
    on_exit={"a": "first non-space character or CR",
             "y": "offset of that character"})
subroutine(0xB393, "save_ptr_to_spool_buf",
    title="Copy text pointer to spool buffer pointer",
    description="Saves fs_crc_lo/hi into fs_options/fs_block_offset\n"
    "for use as the spool buffer pointer. Preserves A\n"
    "on the stack. Called by *PS and *PollPS before\n"
    "parsing their arguments.",
    on_exit={"a": "preserved (PHA/PLA)"})
subroutine(0xB39E, "init_spool_drive",
    title="Initialise spool drive page pointers",
    description="Calls get_ws_page to read the workspace page\n"
    "number for the current ROM slot, stores it as\n"
    "the spool drive page high byte (addr_work), and\n"
    "clears the low byte (work_ae) to zero. Preserves\n"
    "Y on the stack.",
    on_exit={"a": "0",
             "y": "preserved (PHY/PLY)"})

# --- cmd_ps subroutines ---

subroutine(0xB3D5, "copy_ps_data_y1c",
    title="Copy printer server template at offset &18",
    description="Sets Y=&18 and falls through to copy_ps_data.\n"
    "Called during workspace initialisation\n"
    "(svc_2_private_workspace) to set up the printer\n"
    "server template at the standard offset.",
    on_exit={"y": "&20 (advanced past the copied 8 bytes)"})
subroutine(0xB3D7, "copy_ps_data",
    title="Copy 8-byte printer server template to RX buffer",
    description="""\
Copies 8 bytes of default printer server data into the RX buffer
at the current `Y` offset. Uses indexed addressing: `LDA
ps_template_base,X` with `X` starting at `&F8`, so the effective
read address is `ps_template_base+&F8 = ps_template_data`
([`&8E9F`](address:8E9F)). The 6502 trick reaches data 248
bytes past the base label in a single instruction; the base
address (`ps_template_base`) deliberately falls inside the operand
byte of a JSR instruction at `&8DA6` -- see
docs/analysis/authors-easter-egg.md.""",
    on_entry={"y": "destination offset within the RX buffer"},
    on_exit={"y": "advanced by 8",
             "x": "0 (loop terminator)",
             "a": "last template byte"})
label(0xB441, "read_ps_station_addr")
subroutine(0xB477, "store_ps_station",
    title="Write printer-server station number into NFS workspace",
    description="""\
Stores fs_work_5/fs_work_6 (the parsed station/network bytes) into
nfs_workspace offsets 2 and 3 (the printer-server slot's station/
net pair). Single caller (cmd_ps's parse-success path at &B3D2).""")
subroutine(0xB483, "print_file_server_is",
    title="Print 'File server ' prefix",
    description="Uses print_inline to output 'File' then falls through\n"
    "to the shared ' server is ' suffix at\n"
    "print_printer_server_is.",
    on_entry={},
    on_exit={"a, x, y": "clobbered (OSASCI via print_inline)"})
subroutine(0xB48D, "print_printer_server_is",
    title="Print 'Printer server is ' prefix",
    description="Uses print_inline to output the full label\n"
    "'Printer server is ' with trailing space.",
    on_entry={},
    on_exit={"a, x, y": "clobbered (OSASCI via print_inline)"})
subroutine(0xB4A8, "load_ps_server_addr",
    title="Load printer server address from workspace",
    description="Reads the station and network bytes from workspace\n"
    "offsets 2 and 3 into the station/network variables.",
    on_exit={"a, y": "clobbered"})
subroutine(0xB4B4, "pop_requeue_ps_scan",
    title="Pop return address and requeue PS slot scan",
    description="Converts the PS slot flags to a workspace index,\n"
    "writes slot data, and jumps back into the PS scan\n"
    "loop to continue processing.",
    on_entry={"a": "PS slot flags byte to convert into a workspace index"})
subroutine(0xB4D6, "skip_next_ps_slot",
    title="Advance to next PS slot, wrap if all 256 done",
    description="""\
INX / TXA / BNE loop_scan_ps_slots. Slot index in X advances; the
BNE re-enters the scan unless X has wrapped to zero (all 256
slots scanned). Single caller (the no-match path at &B4FF in the
PS slot scanner).""",
    on_entry={"x": "current slot index"})
subroutine(0xB51C, "write_ps_slot_byte_ff",
    title="Write buffer page byte and two &FF markers",
    description="Stores the buffer page byte at the current Y offset\n"
    "in workspace, followed by two &FF sentinel bytes.\n"
    "Advances Y after each write.",
    on_entry={"a": "buffer page byte to store at workspace+Y",
              "y": "starting workspace offset"},
    on_exit={"a": "&FF (the sentinel value left in A)",
             "y": "workspace offset advanced by 3 (one byte + two markers)"})
subroutine(0xB523, "write_two_bytes_inc_y",
    title="Write A to two consecutive workspace bytes",
    description="Stores A at the current Y offset via (nfs_workspace),Y\n"
    "then again at Y+1, advancing Y after each write.",
    on_entry={"a": "byte to store", "y": "workspace offset"})
subroutine(0xB52B, "reverse_ps_name_to_tx",
    title="Reverse-copy printer server name to TX buffer",
    description="""\
Copies 8 bytes from the RX buffer at offsets `&18..&1F`
(`(net_rx_ptr)+&18..+&1F`) to the TX buffer at offsets
`&10..&17` (`(net_rx_ptr)+&10..+&17`) in reversed byte order.
Implementation: pushes the 8 RX bytes onto the stack, then pops
them back to the TX area; the LIFO order achieves the reversal.""",
    on_exit={"a, x, y": "clobbered"})
subroutine(0xB556, "print_station_addr",
    title="Print station address as decimal net.station",
    description="If the network number is zero, prints only the\n"
    "station number. Otherwise prints network.station\n"
    "separated by a dot. V flag controls padding with\n"
    "leading spaces for column alignment.",
    on_entry={"v flag": "set = no leading-space padding; "
              "clear = pad to align in a column"},
    on_exit={"a, x, y": "clobbered (print_decimal_3dig and OSASCI)"})

# --- cmd_pollps subroutines ---

subroutine(0xB6A6, "init_ps_slot_from_rx",
    title="Initialise PS slot buffer from template data",
    description="""\
Copies the 12-byte
[`ps_slot_txcb_template`](address:B575) into workspace at
offsets &78-&83 via indexed addressing from
`write_ps_slot_link_addr` (`write_ps_slot_hi_link+1`).
Substitutes `net_rx_ptr_hi` at offsets &7D and &81 (the hi bytes
of the two buffer pointers) so they point into the current RX
buffer page.""",
    on_exit={"a, x, y": "clobbered"})
subroutine(0xB6BD, "store_char_uppercase",
    title="Convert to uppercase and store in RX buffer",
    description="If the character in A is lowercase (&61-&7A), converts\n"
    "to uppercase by clearing bit 5. Stores the result in\n"
    "the RX buffer at the current position, advances the\n"
    "buffer pointer, and decrements the character count.",
    on_entry={"a": "character to store"})

# --- cmd_wipe subroutines ---

subroutine(0xB703, "request_next_wipe",
    title="Build 'examine directory' TXCB for next wipe iteration",
    description="""\
Issues FS function-code 1 ('examine directory entry') for the
current iteration in fs_work_5. Writes the function code into
TXCB[5] and TXCB[7], copies the iteration index to TXCB[6], and
falls through to the TXCB-build / send sequence. Single caller
(the BNE retry at &B73F that loops cmd_wipe over each match).""")
subroutine(0xB7D3, "flush_and_read_char",
    title="Flush keyboard buffer and read one character",
    description="Calls OSBYTE &0F to flush the input buffer, then\n"
    "OSRDCH to read a single character. Raises an escape\n"
    "error if escape was pressed (carry set on return).",
    on_entry={},
    on_exit={"a": "character read from keyboard",
             "x, y": "clobbered (OSBYTE/OSRDCH)"})
subroutine(0xB7E3, "init_channel_table",
    title="Initialise channel allocation table",
    description="Clears all 256 bytes of the table, then marks\n"
    "available channel slots based on the count from\n"
    "the receive buffer. Sets the first slot to &C0\n"
    "(active channel marker).",
    on_exit={"a, x, y": "clobbered"})
subroutine(0xB805, "attr_to_chan_index",
    title="Convert channel attribute to table index",
    description="Subtracts &20 from the attribute byte and clamps\n"
    "to the range 0-&0F. Returns &FF if out of range.\n"
    "Preserves processor flags via PHP/PLP.",
    on_entry={"a": "channel attribute byte"},
    on_exit={"a": "table index (0-&0F) or &FF if invalid"})
subroutine(0xB814, "check_chan_char",
    title="Validate channel character and look up entry",
    description="Characters below '0' are looked up directly in\n"
    "the channel table. Characters '0' and above are\n"
    "converted to a table index via attr_to_chan_index.\n"
    "Raises 'Net channel' error if invalid.",
    on_entry={"a": "channel character"})
subroutine(0xB81C, "err_net_chan_invalid",
    title="Raise 'Net channel' error (saving channel char on stack)",
    description="""\
Pushes the bad channel character on the stack, then falls through to
error_chan_not_found which loads error code &DE and tail-calls
error_inline_log with the inline string 'Net channel'. The PHA at
entry differs from the &B81D error_chan_not_found alt-entry: this
form is reached when the caller has the channel character in A and
wants it preserved on the stack for the error handler to inspect.
Never returns -- error_inline_log triggers a BRK.""",
    on_entry={"a": "channel character (saved on stack)"})
subroutine(0xB847, "lookup_chan_by_char",
    title="Look up channel by character code",
    description="""\
Subtracts `&20` from the character to produce a table index
(inlining the same arithmetic as
[`attr_to_chan_index`](address:B805) without the bounds check),
loads the channel slot's `hazel_fcb_slot_attr` byte; on zero
raises `error_chan_not_found`. Otherwise verifies station/network
via [`match_station_net`](address:B925) and returns the slot's
flags in `A`.""",
    on_entry={"a": "channel character"},
    on_exit={"a": "channel flags"})
subroutine(0xB886, "store_result_check_dir",
    title="Store channel attribute and check not directory",
    description="Writes the current channel attribute to the receive\n"
    "buffer, then tests the directory flag (bit 1). Raises\n"
    "'Is a dir.' error if the attribute refers to a\n"
    "directory rather than a file.",
    on_entry={"a": "channel attribute byte to store and check"})
subroutine(0xB88C, "check_not_dir",
    title="Validate channel is not a directory",
    description="Calls check_chan_char to validate the channel, then\n"
    "tests the directory flag (bit 1). Raises 'Is a dir.'\n"
    "error if the channel refers to a directory.",
    on_entry={"a": "channel character (validated by check_chan_char)"})
subroutine(0xB8A8, "alloc_fcb_slot",
    title="Allocate a free file control block slot",
    description="Scans FCB slots &20-&2F for an empty entry.\n"
    "Returns Z=0 with X=slot index on success, or\n"
    "Z=1 with A=0 if all slots are occupied.",
    on_exit={"x": "slot index (if Z=0)", "z": "0=success, 1=no free slot"})
subroutine(0xB8DC, "alloc_fcb_or_error",
    title="Allocate FCB slot or raise error",
    description="Calls alloc_fcb_slot and raises 'No more FCBs'\n"
    "if no free slot is available. Preserves the\n"
    "caller's argument on the stack.",
    on_entry={"a": "caller's argument byte (saved/restored via PHA/PLA "
              "across the alloc call)"},
    on_exit={"x": "newly allocated FCB slot index (&20-&2F)",
             "a": "preserved"})
subroutine(0xB8F8, "close_all_net_chans",
    title="Close all network channels for current station",
    description="Scans FCB slots &0F down to 0, closing those\n"
    "matching the current station. C=0 closes all\n"
    "matching entries; C=1 closes with write-flush.",
    on_entry={"c": "0=close all, 1=close with write-flush"})
subroutine(0xB8FC, "scan_fcb_flags",
    title="Scan FCB slot flags from &10 downward",
    description="Iterates through FCB slots starting at &10,\n"
    "checking each slot's flags byte. Returns when\n"
    "all slots have been processed.",
    on_exit={"x": "last scanned FCB index",
             "z flag": "set if a matching slot was found "
             "(via fall-through into match_station_net)"})
subroutine(0xB925, "match_station_net",
    title="Check FCB slot matches current station/network",
    description="Compares the station and network numbers in the\n"
    "FCB at slot X against the current values using\n"
    "EOR. Returns Z=1 if both match, Z=0 if either\n"
    "differs.",
    on_entry={"x": "FCB slot index"},
    on_exit={"z": "1=match, 0=no match"})
subroutine(0xB934, "find_open_fcb",
    title="Find next open FCB slot for current connection",
    description="Scans from the current index, wrapping around at\n"
    "the end. On the first pass finds active entries\n"
    "matching the station; on the second pass finds\n"
    "empty slots for new allocations.",
    on_entry={"x": "starting FCB index (search wraps)"},
    on_exit={"x": "FCB slot index of the matched (active) or first "
             "empty slot",
             "z flag": "match status (set when an entry was found)"})
subroutine(0xB977, "init_wipe_counters",
    title="Initialise byte counters for wipe/transfer",
    description="""\
Sets `hazel_pass_counter` to 1 and clears
`hazel_byte_counter_lo`, `hazel_offset_counter` and
`hazel_transfer_flag`. Then stores `&FF` sentinels in
[`hazel_sentinel_cd`](address:C2CD) /
[`hazel_sentinel_ce`](address:C2CE). The HAZEL FS-state region
is at &C2xx in the 4.21 build.""",
    on_entry={},
    on_exit={"x": "small loop counter (last DEX value)",
             "y": "0 (cleared by the TYA path)"})
subroutine(0xB99A, "start_wipe_pass",
    title="Start wipe pass for current FCB",
    description="Verifies the workspace checksum, saves the station\n"
    "context (pushing station low/high), initialises\n"
    "transfer counters via init_wipe_counters, and sends\n"
    "the initial request via send_and_receive. Clears the\n"
    "active and offset flags on completion.",
    on_entry={"x": "FCB slot index"})
subroutine(0xBA09, "save_fcb_context",
    title="Save FCB context and process pending slots",
    description="Copies 13 bytes from the TX buffer (&0F00) and\n"
    "fs_load_addr workspace to temporary storage at\n"
    "&10D9. If Y=0, skips to the restore loop. Otherwise\n"
    "scans for pending FCB slots (bits 7+6 set), flushes\n"
    "each via start_wipe_pass, allocates new slots via\n"
    "find_open_fcb, and sends directory requests. Falls\n"
    "through to restore_catalog_entry.",
    on_entry={"y": "filter attribute (0=process all)"})
subroutine(0xBAB7, "loop_restore_workspace",
    title="Pop 13 saved workspace bytes back to fs_load_addr+",
    description="""\
Y=0..&0C loop: PLA / STA fs_load_addr,Y / INY / CPY #&0D / BNE.
Restores the 13-byte FS-options block that save_fcb_context pushed
on the stack, undoing the protection the wipe/scan path put in
place. Two callers: the JMP at &BA1B (close-and-restore exit) and
the BNE retry at &BABE.""")
subroutine(0xBAC0, "restore_catalog_entry",
    title="Restore saved catalog entry to TX buffer",
    description="""\
Copies 13 bytes (Y=&0C..0) from
[`hazel_ctx_buffer`](address:C2D9) back to the TX buffer
starting at [`hazel_txcb_port`](address:C100). Falls through to
`find_matching_fcb`. (Pre-HAZEL ROMs read from `&10D9` and wrote
to `&0F00`; the 4.21 build relocates both to HAZEL.)""")
subroutine(0xBACC, "loop_save_before_match",
    title="Save FCB context, fall into find_matching_fcb",
    description="""\
Single-instruction wrapper at the top of the per-iteration FCB
search retry: JSR save_fcb_context to preserve the current attempt's
state (offset, station, network), then fall through into
find_matching_fcb. Single caller (the BNE retry at &BAEB). Used
once the first scan past slot &0F has failed and the search needs
to restart from slot 0 with the saved context restored.""")
subroutine(0xBACF, "find_matching_fcb",
    title="Find FCB slot matching channel attribute",
    description="Scans FCB slots 0-&0F for an active entry whose\n"
    "attribute reference matches hazel_chan_attr. Converts the\n"
    "attribute to a channel index, then verifies the\n"
    "station and network numbers. On the first scan\n"
    "past slot &0F, saves context via save_fcb_context\n"
    "and restarts. Returns Z=0 if the FCB has saved\n"
    "offset data (bit 5 set).",
    on_exit={"x": "matching FCB index", "z": "0=has offset data, 1=no offset"})
subroutine(0xBB2A, "inc_fcb_byte_count",
    title="Increment 3-byte FCB transfer count",
    description="Increments hazel_fcb_addr_lo+X (low), cascading overflow to\n"
    "hazel_fcb_addr_mid+X (mid) and hazel_fcb_addr_hi+X (high).",
    on_entry={"x": "FCB slot index"})
subroutine(0xBB38, "process_all_fcbs",
    title="Process all active FCB slots",
    description="""\
Saves 9 zero-page bytes (`&00B4`–`&00BC`, i.e. `fs_work_4`+0..+8)
on the stack via a `PHX`/`PHY`/loop preamble using the `&FFBD,X`
indexing-wrap trick (X = `&F7`..`&FF` wraps to `&00B4`..`&00BC`),
then scans FCB slots `&0F` down to 0.
Calls [`start_wipe_pass`](address:B99A) for each active entry
matching the filter attribute in `Y` (`0` = match all). Restores
all saved context on completion. Also contains the OSBGET/OSBPUT
inline logic for reading and writing bytes through file
channels.""",
    on_entry={"y": "filter attribute (0=process all)"})
subroutine(0xBB68, "bgetv_handler",
    title="BGETV vector handler: read byte from open file",
    description="""\
Reached via the BGETV vector at `&021A`, which the
[`fs_vector_table`](address:8EA7) entries copy into the MOS extended
vector area. Saves caller's `Y` in `hazel_chan_attr` (channel attribute slot),
pushes `X`, calls
[`store_result_check_dir`](address:B886) to validate the channel,
then either reads a byte from the FCB buffer (returning it in `A`
with `C=0`) or signals end-of-file (`C=1`).""",
    on_entry={"y": "channel handle"},
    on_exit={"a": "byte read (when C=0)",
             "c": "0 = byte returned, 1 = EOF / error"})
subroutine(0xBBE7, "bputv_handler",
    title="BPUTV vector handler: write byte to open file",
    description="""\
Reached via the BPUTV vector at `&0218`. Saves caller's `Y` in
`hazel_chan_attr`, pushes the data byte and `X`, then routes to the FCB
buffer-write path: stores the byte in the channel's transmit
buffer, increments the byte count via
[`inc_fcb_byte_count`](address:BB2A), and exits via
[`done_inc_byte_count`](address:BC65).""",
    on_entry={"a": "byte to write",
              "y": "channel handle"},
    on_exit={"c": "0 = written, 1 = error"})
subroutine(0xBC65, "done_inc_byte_count",
    title="Increment FCB byte count, clear rx attr, restore caller",
    description="""\
JSRs inc_fcb_byte_count for the active FCB, then A=0 / JSR
store_rx_attribute (clears the receive-attribute byte). Pulls
saved X back into X (caller's value), discards the saved data byte
on the stack and returns. Single caller (the OSBPUT/PRINT path at
&BC1F).""")
subroutine(0xBC74, "flush_fcb_if_station_known",
    title="Flush FCB byte count to server if station is set",
    description="Saves all registers, checks if the FCB has a\n"
    "known station. If yes, sends the accumulated byte\n"
    "count as a flush request to the file server. If no\n"
    "station is set, falls through to flush_fcb_with_init\n"
    "which saves FCB context first.",
    on_entry={"Y": "channel index (FCB slot)"},
    on_exit={"A": "preserved", "X": "preserved", "Y": "preserved"})
subroutine(0xBC7C, "flush_fcb_with_init",
    title="Save FCB context and flush byte count to server",
    description="Saves all registers and the current FCB context,\n"
    "copies the FCB byte count into the TX command buffer,\n"
    "and sends a flush/close request to the file server.\n"
    "Restores the catalog entry and all registers on return.",
    on_entry={"Y": "channel index (FCB slot)"},
    on_exit={"A": "preserved", "X": "preserved", "Y": "preserved"})
label(0xBC89, "store_station_and_flush")
subroutine(0xBCBC, "send_wipe_request",
    title="Send wipe/close request packet",
    description="Sets up the TX control block with function code\n"
    "&90, the reply port from Y, and the data byte from\n"
    "A. Sends via send_disconnect_reply, then checks the\n"
    "error code — raises the server error if non-zero.",
    on_entry={"a": "data byte to send", "y": "reply port"})
subroutine(0xBD15, "send_and_receive",
    title="Set up FS options and transfer workspace",
    description="Calls set_options_ptr to configure the FS options\n"
    "pointer, then jumps to setup_transfer_workspace to\n"
    "initialise the transfer and send the request.",
    on_entry={"a": "transfer mode", "x": "workspace offset low", "y": "workspace page"})
subroutine(0xBD1B, "read_rx_attribute",
    title="Read receive attribute byte from RX buffer",
    description="Reads byte at offset &0A in the network receive\n"
    "control block, used to track which channel owns the\n"
    "current receive buffer.",
    on_entry={},
    on_exit={"A": "receive attribute byte", "Y": "&0A"})
subroutine(0xBD20, "store_rx_attribute",
    title="Store receive attribute byte to RX buffer",
    description="Writes A to offset &0A in the network receive\n"
    "control block, marking which channel owns the\n"
    "current receive buffer.",
    on_entry={"A": "attribute byte to store"},
    on_exit={"Y": "&0A"})

# --- cmd_print subroutines ---

subroutine(0xBD25, "abort_if_escape",
    title="Test escape flag and abort if pressed",
    description="Checks the escape flag byte; returns immediately\n"
    "if bit 7 is clear. If escape has been pressed,\n"
    "falls through to the escape abort handler which\n"
    "acknowledges the escape via OSBYTE &7E.")

# --- cmd_dump subroutines ---

subroutine(0xBD59, "loop_dump_line",
    title="*DUMP per-line read loop",
    description="""\
Body of cmd_dump's outer line loop. Calls abort_if_escape, then
reads up to 16 bytes from the open file via OSBGET into the line
buffer at (work_ae). On EOF mid-line, breaks to clean-up; on a
full line, falls through to the formatting and print stage.
Reachable from the alignment branch at &BD54 and the per-line tail
at &BDF9.""")
subroutine(0xBD79, "loop_pop_stack_buf",
    title="Drain saved bytes off stack and close",
    description="""\
Pulls X+1 bytes off the 6502 stack (clearing the temporary 21-byte
buffer cmd_dump uses to render each line) and tail-jumps to
close_ws_file. Reached from the in-line BPL at &BD7B and the
fall-through tail at &BDFE.""",
    on_entry={"x": "stack-byte count - 1 (caller sets it to &14 or &15)"})
subroutine(0xBDBB, "loop_next_dump_col",
    title="*DUMP per-column advance and end-of-line check",
    description="""\
INY (next buffer offset), CPY #&10. End -> done_print_separator.
Otherwise DEX (decrement byte counter); BPL loop_print_dump_hex
to print the next byte. Single caller (the BPL at &BDCC after
short-line padding).""",
    on_entry={"x": "remaining bytes - 1",
              "y": "buffer offset"})
subroutine(0xBE01, "print_dump_header",
    title="Print hex dump column header line",
    description="Outputs the starting address followed by 16 hex\n"
    "column numbers (00-0F), each separated by a space.\n"
    "Provides the column alignment header for *Dump\n"
    "output.",
    on_exit={"a, x, y": "clobbered (print_hex_byte + OSASCI loop)"})
subroutine(0xBE37, "print_hex_and_space",
    title="Print hex byte followed by space",
    description="Saves A, prints it as a 2-digit hex value via\n"
    "print_hex_byte, outputs a space character, then\n"
    "restores A from the stack. Used by cmd_dump and\n"
    "print_dump_header for column-aligned hex output.",
    on_entry={"a": "byte value to print"})
subroutine(0xBF71, "close_ws_file",
    title="Close file handle stored in workspace",
    description="Loads the file handle from ws_page and closes it\n"
    "via OSFIND with A=0.",
    on_exit={"a, x, y": "clobbered (OSFIND)"})
subroutine(0xBF78, "open_file_for_read",
    title="Open file for reading via OSFIND",
    description="Computes the filename address from the command text\n"
    "pointer plus the Y offset, calls OSFIND with A=&40\n"
    "(open for input). Stores the handle in ws_page.\n"
    "Raises 'Not found' if the returned handle is zero.",
    on_entry={"y": "offset within the command line of the filename to open"},
    on_exit={"a, x, y": "clobbered"})
label(0xBF9E, "restore_text_ptr")
label(0xBFB8, "done_skip_filename")
subroutine(0xBE42, "parse_dump_range",
    title="Parse hex address for dump range",
    description="Reads up to 4 hex digits from the command line\n"
    "into a 4-byte accumulator, stopping at CR or\n"
    "space. Each digit shifts the accumulator left\n"
    "by 4 bits before ORing in the new nybble.",
    on_entry={"y": "current command-line offset"},
    on_exit={"y": "advanced past the parsed digits",
             "a": "first non-hex character (CR or space)"})
subroutine(0xBE4E, "loop_parse_hex_digit",
    title="*DUMP / *LIST hex-address parser per-character body",
    description="""\
Reload command-line offset from X, INX (step cursor), TAY (use as
indirect index), read (os_text_ptr),Y. Branches: CR -> done; space
-> end of token; otherwise validate hex digit and shift it into the
4-byte accumulator. Single caller (the BNE retry at &BE95).""",
    on_entry={"x": "current command-line offset"})
subroutine(0xBEAB, "init_dump_buffer",
    title="Initialise dump buffer and parse address range",
    description="Parses the start and end addresses from the command\n"
    "line via parse_dump_range. If no end address is given,\n"
    "defaults to the file extent. Validates both addresses\n"
    "against the file size, raising 'Outside file' if either\n"
    "exceeds the extent.",
    on_entry={"y": "command-line offset of the address arguments"})
subroutine(0xBFBA, "advance_x_by_8",
    title="Advance X by 16 via nested JSR + fall-through",
    description="""\
**Note:** the name is historical and misleading -- this routine
actually advances `X` by 16, not 8.

`JSR advance_x_by_4` followed by no `RTS`, so control falls
through into [`advance_x_by_4`](address:BFBD) itself for a
second pass. Each pass through `advance_x_by_4` runs `inx4`
twice (8 INXs), so two passes give 16 INXs in total.""",
    on_entry={"x": "value to advance"},
    on_exit={"x": "input + 16",
             "a, y": "preserved"})
subroutine(0xBFBD, "advance_x_by_4",
    title="Advance X by 8 via JSR and fall-through",
    description="""\
**Note:** the name is historical and misleading -- this routine
actually advances `X` by 8, not 4.

`JSR inx4` (4 INXs); the JSR's RTS lands at &BFC0 which is
[`inx4`](address:BFC0)'s entry, so a second pass runs by fall-
through (4 more INXs). Total: 8 INXs.""",
    on_entry={"x": "value to advance"},
    on_exit={"x": "input + 8",
             "a, y": "preserved"})
subroutine(0xBFC0, "inx4",
    title="Increment X four times",
    description="Four consecutive INX instructions. Used as a\n"
    "building block by advance_x_by_4 and\n"
    "advance_x_by_8 via JSR/fall-through chaining.",
    on_entry={"x": "value to advance"},
    on_exit={"x": "input + 4",
             "a, y": "preserved",
             "n, z flags": "reflect new X"})

# ============================================================
# Inline comments (from NFS 3.65 correspondence)
# ============================================================

comment(0x8006, "ROM type: service + language", inline=True)
comment(0x8019, "Null terminator before copyright", inline=True)
comment(0x803A, "Copy to A for sign test", inline=True)
comment(0x803B, "Bit 7 set: dispatch via table", inline=True)
comment(0x803D, "A=&FE: Econet receive event", inline=True)
comment(0x8042, "Fire event (enable: *FX52,150)", inline=True)
comment(0x8045, "Dispatch through event vector", inline=True)
comment(0x803F, "Call event vector handler", inline=True)
comment(0x8048, "Push return addr high (&85)", inline=True)
comment(0x804A, "High byte on stack for RTS", inline=True)
comment(0x804B, "Load dispatch target low byte", inline=True)
comment(0x804E, "Low byte on stack for RTS", inline=True)
comment(0x804F, "RTS = dispatch to PHA'd address", inline=True)
comment(0x8050, "INTOFF: read station ID, disable NMIs", inline=True)
comment(0x8053, "Full ADLC hardware reset", inline=True)
comment(0x8056, "OSBYTE &EA: check Tube co-processor", inline=True)
comment(0x8058, "X=0 for OSBYTE", inline=True)
comment(0x805A, "Clear Econet init flag before setup", inline=True)
comment(0x8063, "OSBYTE &8F: issue service request", inline=True)
comment(0x8065, "X=&0C: NMI claim service", inline=True)
comment(0x805D, "Check Tube presence via OSBYTE &EA", inline=True)
comment(0x8060, "Store Tube presence flag from OSBYTE &EA", inline=True)
comment(0x8067, "Issue NMI claim service request", inline=True)
comment(0x806A, "Y=5: NMI claim service number", inline=True)
comment(0x806C, "Check if NMI service was claimed (Y changed)", inline=True)
comment(0x806E, "Service claimed by other ROM: skip init", inline=True)
comment(0x8070, "Copy NMI shim from ROM to &0D0C area", inline=True)
comment(0x8072, "Read byte from NMI shim ROM source", inline=True)
comment(0x8075, "Write to NMI shim RAM (start of NFS workspace)", inline=True)
comment(0x8078, "Next byte (descending)", inline=True)
comment(0x8079, "Loop until all 32 bytes copied", inline=True)
comment(0x807B, "Patch current ROM bank into NMI shim", inline=True)
comment(0x807D, "Self-modifying code: ROM bank at &0D07", inline=True)
comment(0x8080, "Clear source network (Y=0 from copy loop)", inline=True)
comment(0x8083, "Clear Tube release flag", inline=True)
comment(0x8085, "Clear TX operation type", inline=True)
comment(0x808F, "&80 = Econet initialised", inline=True)
comment(0x8091, "Mark TX as complete (ready)", inline=True)
comment(0x8094, "Mark Econet as initialised", inline=True)
comment(0x8097, "INTON: re-enable NMIs (&FE20 read side effect)", inline=True)
comment(0x809A, "Return", inline=True)
comment(0x809B, "A=&01: mask for SR2 bit0 (AP = Address Present)", inline=True)
comment(0x809D, "Z = A AND SR2 -- tests if AP is set", inline=True)
comment(0x80A0, "AP not set, no incoming data -- check for errors", inline=True)
comment(0x80A2, "Read first RX byte (destination station address)", inline=True)
comment(0x80A5, "Compare to our station ID (&FE18 read = INTOFF, disables NMIs)", inline=True)
comment(0x80A8, "Match -- accept frame", inline=True)
comment(0x80AA, "Check for broadcast address (&FF)", inline=True)
comment(0x80AC, "Neither our address nor broadcast -- reject frame", inline=True)
comment(0x80AE, "Flag &40 = broadcast frame", inline=True)
comment(0x80B0, "Store broadcast flag in rx_src_net", inline=True)
comment(0x80B3, "Install nmi_rx_scout_net NMI handler", inline=True)
comment(0x80B5, "Install next handler", inline=True)
comment(0x80B8, "Test SR2 for RDA (bit7 = data available)", inline=True)
comment(0x80BB, "No RDA -- check errors", inline=True)
comment(0x80BD, "Read destination network byte", inline=True)
comment(0x80C0, "Network = 0 -- local network, accept", inline=True)
comment(0x80C2, "Test if network = &FF (broadcast)", inline=True)
comment(0x80C4, "Broadcast network -- accept", inline=True)
comment(0x80C6, "Reject: wrong network. CR1=&A2: RIE|RX_DISCONTINUE", inline=True)
comment(0x80C8, "Write CR1 to discontinue RX", inline=True)
comment(0x80CB, "Return to idle scout listening", inline=True)
comment(0x80CE, "Network = 0 (local): clear tx_flags", inline=True)
comment(0x80D1, "Store Y offset for scout data buffer", inline=True)
comment(0x80D3, "Install scout data handler", inline=True)
comment(0x80D5, "Install scout data loop", inline=True)
comment(0x80D8, "Read SR2", inline=True)
comment(0x80DB, "Test AP (b0) | RDA (b7)", inline=True)
comment(0x80DD, "Neither set -- clean end, discard frame", inline=True)
comment(0x80DF, "Unexpected data/status: full ADLC reset", inline=True)
comment(0x80E2, "Discard and return to idle", inline=True)
comment(0x80E5, "Gentle discard: RX_DISCONTINUE", inline=True)
comment(0x80E8, "Y = buffer offset", inline=True)
comment(0x80EA, "Read SR2", inline=True)
comment(0x80ED, "No RDA -- error handler", inline=True)
comment(0x80EF, "Read data byte from RX FIFO", inline=True)
comment(0x80F2, "Store at &0D3D+Y (scout buffer)", inline=True)
comment(0x80F5, "Advance buffer index", inline=True)
comment(0x80F6, "Read SR2 again (FV detection point)", inline=True)
comment(0x80F9, "RDA set -- more data, read second byte", inline=True)
comment(0x80FB, "SR2 non-zero (FV or other) -- scout completion", inline=True)
comment(0x80FD, "Read second byte of pair", inline=True)
comment(0x8100, "Store at &0D3D+Y", inline=True)
comment(0x8103, "Advance and check buffer limit", inline=True)
comment(0x8104, "Copied all 12 scout bytes?", inline=True)
comment(0x8106, "Buffer full (Y=12) -- force completion", inline=True)
comment(0x8108, "Save final buffer offset", inline=True)
comment(0x810A, "Read SR2 for next pair", inline=True)
comment(0x810D, "SR2 non-zero -- loop back for more bytes", inline=True)
comment(0x810F, "SR2 = 0 -- wait for next NMI", inline=True)
comment(0x8112, "Save Y for next iteration", inline=True)
comment(0x8114, "Write CR1", inline=True)
comment(0x8117, "CR2=&84: disable PSE, enable RDA_SUPPRESS_FV", inline=True)
comment(0x8119, "Write CR2", inline=True)
comment(0x811C, "A=&02: FV mask for SR2 bit1", inline=True)
comment(0x811E, "Test SR2 FV (Z) and RDA (N)", inline=True)
comment(0x8121, "No FV -- not a valid frame end, error", inline=True)
comment(0x8123, "FV set but no RDA -- missing last byte, error", inline=True)
comment(0x8125, "Read last byte from RX FIFO", inline=True)
comment(0x8128, "Store last byte at &0D3D+Y", inline=True)
comment(0x812B, "CR1=&44: RX_RESET | TIE (switch to TX for ACK)", inline=True)
comment(0x812D, "Write CR1: switch to TX mode", inline=True)
comment(0x8130, "Set bit7 of need_release_tube flag", inline=True)
comment(0x8131, "Rotate C=1 into bit7: mark Tube release needed", inline=True)
comment(0x8133, "Check port byte: 0 = immediate op, non-zero = data transfer", inline=True)
comment(0x8136, "Port non-zero -- look for matching receive block", inline=True)
comment(0x8138, "Port = 0 -- immediate operation handler", inline=True)
comment(0x813B, "Check if broadcast (bit6 of tx_flags)", inline=True)
comment(0x813E, "Not broadcast -- skip CR2 setup", inline=True)
comment(0x8140, "CR2=&07: broadcast prep", inline=True)
comment(0x8142, "Write CR2: broadcast frame prep", inline=True)
comment(0x8145, "Check if RX port list active (bit7)", inline=True)
comment(0x8148, "No active ports -- try NFS workspace", inline=True)
comment(0x814A, "Start scanning port list at page &C0", inline=True)
comment(0x814C, "Y=0: start offset within each port slot", inline=True)
comment(0x814E, "Store page to workspace pointer low", inline=True)
comment(0x8150, "Store page high byte for slot scanning", inline=True)
comment(0x8152, "Y=0: read control byte from start of slot", inline=True)
comment(0x8154, "Read port control byte from slot", inline=True)
comment(0x8156, "Zero = end of port list, no match", inline=True)
comment(0x8158, "&7F = any-port wildcard", inline=True)
comment(0x815A, "Not wildcard -- check specific port match", inline=True)
comment(0x815C, "Y=1: advance to port byte in slot", inline=True)
comment(0x815D, "Read port number from slot (offset 1)", inline=True)
comment(0x815F, "Zero port in slot = match any port", inline=True)
comment(0x8161, "Check if port matches this slot", inline=True)
comment(0x8164, "Port mismatch -- try next slot", inline=True)
comment(0x8166, "Y=2: advance to station byte", inline=True)
comment(0x8167, "Read station filter from slot (offset 2)", inline=True)
comment(0x8169, "Zero station = match any station, accept", inline=True)
comment(0x816B, "Check if source station matches", inline=True)
comment(0x816E, "Station mismatch -- try next slot", inline=True)
comment(0x8170, "Y=3: advance to network byte", inline=True)
comment(0x8171, "Read network filter from slot (offset 3)", inline=True)
comment(0x8173, "Zero = accept any network", inline=True)
comment(0x8175, "Check if source network matches", inline=True)
comment(0x8178, "Network matches or zero = accept", inline=True)
comment(0x817A, "Check if NFS workspace search pending", inline=True)
comment(0x817C, "No NFS workspace -- try fallback path", inline=True)
comment(0x817E, "Load current slot base address", inline=True)
comment(0x8180, "For 12-byte slot advance", inline=True)
comment(0x8181, "Advance to next 12-byte port slot", inline=True)
comment(0x8183, "Update workspace pointer to next slot", inline=True)
comment(0x8185, "Always branches (page &C0 won't overflow)", inline=True)
comment(0x8187, "No match found -- discard frame", inline=True)
comment(0x818A, "Try NFS workspace if paged list exhausted", inline=True)
comment(0x818D, "No NFS workspace RX (bit6 clear) -- discard", inline=True)
comment(0x818F, "NFS workspace starts at offset 0 in page", inline=True)
comment(0x8191, "NFS workspace high byte for port list", inline=True)
comment(0x8193, "Scan NFS workspace port list", inline=True)
comment(0x8195, "Match found: set scout_status = 3", inline=True)
comment(0x8197, "Record match for completion handler", inline=True)
comment(0x819A, "Calculate transfer parameters", inline=True)
comment(0x819D, "C=0: no Tube claimed -- discard", inline=True)
comment(0x819F, "Check broadcast flag for ACK path", inline=True)
comment(0x81A2, "Not broadcast -- normal ACK path", inline=True)
comment(0x81A4, "Broadcast: different completion path", inline=True)
comment(0x81A7, "CR1=&44: RX_RESET | TIE", inline=True)
comment(0x81A9, "Write CR1: TX mode for ACK", inline=True)
comment(0x81AC, "CR2=&A7: RTS | CLR_TX_ST | FC_TDRA | PSE", inline=True)
comment(0x81AE, "Write CR2: enable TX with PSE", inline=True)
comment(0x81B1, "Install data_rx_setup at &81B8", inline=True)
comment(0x81B3, "High byte of data_rx_setup handler", inline=True)
comment(0x81B5, "Send ACK with data_rx_setup as next NMI", inline=True)
comment(0x81B8, "CR1=&82: TX_RESET | RIE (switch to RX for data frame)", inline=True)
comment(0x81BA, "Write CR1: switch to RX for data frame", inline=True)
comment(0x81BD, "Install nmi_data_rx at &81E7", inline=True)
comment(0x81BF, "Install nmi_data_rx and return from NMI", inline=True)
comment(0x81C2, "A=1: AP mask for SR2 bit test", inline=True)
comment(0x81C4, "Test SR2 AP bit", inline=True)
comment(0x81C7, "No AP: wrong frame or error", inline=True)
comment(0x81C9, "Read first byte (dest station)", inline=True)
comment(0x81CC, "Compare to our station ID (INTOFF)", inline=True)
comment(0x81CF, "Not for us: error path", inline=True)
comment(0x81D1, "Install nmi_data_rx_net check handler", inline=True)
comment(0x81D3, "Set NMI vector via RAM shim", inline=True)
comment(0x81D6, "Validate source network = 0", inline=True)
comment(0x81D9, "SR2 bit7 clear: no data ready -- error", inline=True)
comment(0x81DB, "Read dest network byte", inline=True)
comment(0x81DE, "Network != 0: wrong network -- error", inline=True)
comment(0x81E0, "Install skip handler at &8211", inline=True)
comment(0x81E2, "High byte of &8211 handler", inline=True)
comment(0x81E4, "SR1 bit7: IRQ, data already waiting", inline=True)
comment(0x81E7, "Data ready: skip directly, no return", inline=True)
comment(0x81E9, "Install handler and return", inline=True)
comment(0x81EC, "Test SR2 RDA (RX data byte ready)", inline=True)
comment(0x81EF, "SR2 bit7 clear: error", inline=True)
comment(0x81F1, "Discard control byte", inline=True)
comment(0x81F4, "Discard port byte", inline=True)
comment(0x81F7, "A=2: Tube transfer flag mask", inline=True)
comment(0x81F9, "Check if Tube transfer active", inline=True)
comment(0x81FC, "Tube active: use Tube RX path", inline=True)
comment(0x81FE, "A=&23: low byte of nmi_data_rx_bulk (&8223)", inline=True)
comment(0x8200, "Y=&82: high byte of nmi_data_rx_bulk", inline=True)
comment(0x8202, "SR1 bit7: more data already waiting?", inline=True)
comment(0x8205, "Yes: enter bulk read directly", inline=True)
comment(0x8207, "No: install handler", inline=True)
comment(0x820A, "A=&91: low byte of nmi_data_rx_tube (&8291)", inline=True)
comment(0x820C, "Y=&82: high byte of nmi_data_rx_tube", inline=True)
comment(0x820E, "Install Tube handler", inline=True)
comment(0x8211, """\
Page-overflow exit from nmi_data_rx_bulk: restores the Master 128 ACCCON
that was saved at &822A before falling through to the RXCB-update path.""")
comment(0x8211, "Pull saved ACCCON from stack", inline=True)
comment(0x8212, "Restore caller's ACCCON on page-overflow exit", inline=True)
comment(0x8215, "Check tx_flags for error path", inline=True)
comment(0x8218, "Bit7 clear: RX error path", inline=True)
comment(0x821A, "Bit7 set: TX result = not listening", inline=True)
comment(0x821D, "Full ADLC reset on RX error", inline=True)
comment(0x8220, "Discard and return to idle listen", inline=True)
comment(0x8223, "Y = buffer offset, resume from last position", inline=True)
comment(0x8225, "Read SR2 for next pair", inline=True)
comment(0x8228, "SR2 bit7 clear: frame complete (FV)", inline=True)
comment(0x822A, """\
4.21 Master 128: save/restore ACCCON across the (open_port_buf),Y stores
in this bulk-read loop. Same idiom as in copy_scout_to_buffer; workspace
&97 holds the desired ACCCON value pre-loaded by the caller.""")
comment(0x822A, "Save current ACCCON on stack (Master 128)", inline=True)
comment(0x822D, "Push ACCCON snapshot", inline=True)
comment(0x822E, "Load desired ACCCON from workspace &97", inline=True)
comment(0x8230, "Set ACCCON for the upcoming buffer stores", inline=True)
comment(0x8233, "Read first byte of pair from RX FIFO", inline=True)
comment(0x8236, "Store byte to buffer", inline=True)
comment(0x8238, "Advance buffer offset", inline=True)
comment(0x8239, "Y != 0: no page boundary crossing", inline=True)
comment(0x823B, "Crossed page: increment buffer high byte", inline=True)
comment(0x823D, "Decrement remaining page count", inline=True)
comment(0x823F, "No pages left: handle as complete", inline=True)
comment(0x8241, "Read SR2 between byte pairs", inline=True)
comment(0x8244, "SR2 bit7 set: more data available", inline=True)
comment(0x8246, "SR2 non-zero, bit7 clear: frame done", inline=True)
comment(0x8248, "Read second byte of pair from RX FIFO", inline=True)
comment(0x824B, "Store byte to buffer", inline=True)
comment(0x824D, "Advance buffer offset", inline=True)
comment(0x824E, "Save updated buffer position", inline=True)
comment(0x8250, "Y != 0: no page boundary crossing", inline=True)
comment(0x8252, "Crossed page: increment buffer high byte", inline=True)
comment(0x8254, "Decrement remaining page count", inline=True)
comment(0x8256, "No pages left: frame complete", inline=True)
comment(0x825C, "Re-poll ADLC SR2 for next byte pair", inline=True)
comment(0x825F, "More data: loop back to data_rx_loop", inline=True)
comment(0x8261, "No more data: return from NMI", inline=True)
comment(0x8258, "Pull saved ACCCON from stack", inline=True)
comment(0x8259, "Restore caller's ACCCON between byte pairs", inline=True)
comment(0x8264, "Pull saved ACCCON (frame-complete path)", inline=True)
comment(0x8265, "Restore caller's ACCCON before completion", inline=True)
comment(0x8268, "A=&84: CR2 value (disable PSE)", inline=True)
comment(0x826A, "Write CR2 = &84 to disable PSE for bit testing", inline=True)
comment(0x826D, "A=0: CR1 value (disable all interrupts)", inline=True)
comment(0x826F, "Write CR1 = 0 to disable all interrupts", inline=True)
comment(0x8272, "Save Y (byte count from data RX loop)", inline=True)
comment(0x8274, "A=&02: FV mask", inline=True)
comment(0x8276, "Test SR2 FV (Z) and RDA (N)", inline=True)
comment(0x8279, "No FV -- error", inline=True)
comment(0x827B, "FV set, no RDA -- proceed to ACK", inline=True)
comment(0x827D, "Check if buffer space remains", inline=True)
comment(0x827F, "No buffer space: error/discard frame", inline=True)
comment(0x8281, "FV+RDA: read and store last data byte", inline=True)
comment(0x8284, "Y = current buffer write offset", inline=True)
comment(0x8286, "Store last byte in port receive buffer", inline=True)
comment(0x8288, "Advance buffer write offset", inline=True)
comment(0x828A, "No page wrap: proceed to send ACK", inline=True)
comment(0x828C, "Page boundary: advance buffer page", inline=True)
comment(0x828E, "Send ACK frame to complete handshake", inline=True)
comment(0x8291, "Read SR2 for Tube data receive path", inline=True)
comment(0x8294, "RDA clear: no more data, frame complete", inline=True)
comment(0x8296, "Read data byte from ADLC RX FIFO", inline=True)
comment(0x8299, "Check buffer limits and transfer size", inline=True)
comment(0x829C, "Zero: buffer full, handle as error", inline=True)
comment(0x829E, "Send byte to Tube data register 3", inline=True)
comment(0x82A1, "Read second data byte (paired transfer)", inline=True)
comment(0x82A4, "Send second byte to Tube", inline=True)
comment(0x82A7, "Check limits after byte pair", inline=True)
comment(0x82AA, "Zero: Tube transfer complete", inline=True)
comment(0x82AC, "Re-read SR2 for next byte pair", inline=True)
comment(0x82AF, "More data available: continue loop", inline=True)
comment(0x82B1, "Unexpected end: return from NMI", inline=True)
comment(0x82B4, "CR1=&00: disable all interrupts", inline=True)
comment(0x82B6, "Write CR1 for individual bit testing", inline=True)
comment(0x82B9, "CR2=&84: disable PSE", inline=True)
comment(0x82BB, "Write CR2: same pattern as main path", inline=True)
comment(0x82BE, "A=&02: FV mask for Tube completion", inline=True)
comment(0x82C0, "Test SR2 FV (Z) and RDA (N)", inline=True)
comment(0x82C3, "No FV: incomplete frame, error", inline=True)
comment(0x82C5, "FV set, no RDA: proceed to ACK", inline=True)
comment(0x82C7, "Check if any buffer was allocated", inline=True)
comment(0x82C9, "OR all 4 buffer pointer bytes together", inline=True)
comment(0x82CB, "Check buffer low byte", inline=True)
comment(0x82CD, "Check buffer high byte", inline=True)
comment(0x82CF, "All zero (null buffer): error", inline=True)
comment(0x82D1, "Read extra trailing byte from FIFO", inline=True)
comment(0x82D4, "Save extra byte in workspace for later use", inline=True)
comment(0x82D7, "Bit5 = extra data byte available flag", inline=True)
comment(0x82D9, "Set extra byte flag in tx_flags", inline=True)
comment(0x82DC, "Store updated flags", inline=True)
comment(0x82DF, "Load TX flags to check ACK type", inline=True)
comment(0x82E2, "Bit7 clear: normal scout ACK", inline=True)
comment(0x82E4, "Final ACK: call completion handler", inline=True)
comment(0x82E7, "Jump to TX success result", inline=True)
comment(0x82EA, "CR1=&44: RX_RESET | TIE (switch to TX mode)", inline=True)
comment(0x82EC, "Write CR1: switch to TX mode", inline=True)
comment(0x82EF, "CR2=&A7: RTS|CLR_TX_ST|FC_TDRA|2_1_BYTE|PSE", inline=True)
comment(0x82F1, "Write CR2: enable TX with status clear", inline=True)
comment(0x82F4, "Install saved next handler (scout ACK path)", inline=True)
comment(0x82F6, "High byte of post-ACK handler", inline=True)
comment(0x82F8, "Store next handler low byte", inline=True)
comment(0x82FB, "Store next handler high byte", inline=True)
comment(0x82FE, "Load dest station from RX scout buffer", inline=True)
comment(0x8301, "Test SR1 TDRA (V=bit6)", inline=True)
comment(0x8304, "TDRA not ready -- error", inline=True)
comment(0x8306, "Write dest station to TX FIFO", inline=True)
comment(0x8309, "Load dest network from RX scout buffer", inline=True)
comment(0x830C, "Write dest net byte to FIFO", inline=True)
comment(0x830F, "A=&16: low byte of nmi_ack_tx_src (&8316)", inline=True)
comment(0x8311, "High byte of nmi_ack_tx_src", inline=True)
comment(0x8313, "Set NMI vector to ack_tx_src handler", inline=True)
comment(0x8316, "Load our station ID from workspace copy", inline=True)
comment(0x8319, "Test SR1 TDRA", inline=True)
comment(0x831C, "TDRA not ready -- error", inline=True)
comment(0x831E, "Write our station to TX FIFO", inline=True)
comment(0x8321, "Write network=0 to TX FIFO", inline=True)
comment(0x8323, "Write network=0 (local) to TX FIFO", inline=True)
comment(0x8326, "Check tx_flags for data phase", inline=True)
comment(0x8329, "bit7 set: start data TX phase", inline=True)
comment(0x832B, "CR2=&3F: TX_LAST_DATA | CLR_RX_ST | FLAG_IDLE | FC_TDRA | 2_1_BYTE | PSE", inline=True)
comment(0x832D, "Write CR2 to clear status after ACK TX", inline=True)
comment(0x8330, "Install saved handler from &0D4B/&0D4C", inline=True)
comment(0x8333, "Load saved next handler high byte", inline=True)
comment(0x8336, "Install next NMI handler", inline=True)
comment(0x8339, "Jump to start data TX phase", inline=True)
comment(0x833C, "Jump to error handler", inline=True)
comment(0x833F, "A=2: test bit1 of tx_flags", inline=True)
comment(0x8341, "Check tx_flags data-transfer bit", inline=True)
comment(0x8344, "Bit1 clear: no transfer -- return", inline=True)
comment(0x8346, "Init carry for 4-byte add", inline=True)
comment(0x8347, "Save carry on stack for loop", inline=True)
comment(0x8348, "Y=8: start at byte 0 of the 4-byte RXCB pointer", inline=True)
comment(0x834A, "Load RXCB[Y] (buffer pointer byte)", inline=True)
comment(0x834C, "Restore carry from stack", inline=True)
comment(0x834D, "Add transfer count byte", inline=True)
comment(0x8350, "Store updated pointer back to RXCB", inline=True)
comment(0x8352, "Next byte", inline=True)
comment(0x8353, "Save carry for next iteration", inline=True)
comment(0x8354, "Done 4 bytes? (Y reaches &0C)", inline=True)
comment(0x8356, "No: continue adding", inline=True)
comment(0x8358, "Discard final carry", inline=True)
comment(0x8359, "A=&20: test bit5 of tx_flags", inline=True)
comment(0x835B, "Check tx_flags Tube bit", inline=True)
comment(0x835E, "No Tube: skip Tube update", inline=True)
comment(0x8360, "Save X on stack", inline=True)
comment(0x8361, "Push X", inline=True)
comment(0x8362, "A=8: offset for Tube address", inline=True)
comment(0x8364, "For address calculation", inline=True)
comment(0x8365, "Add workspace base offset", inline=True)
comment(0x8367, "X = address low for Tube claim", inline=True)
comment(0x8368, "Y = address high for Tube claim", inline=True)
comment(0x836A, "A=1: Tube claim type (read)", inline=True)
comment(0x836C, "Claim Tube address for transfer", inline=True)
comment(0x836F, "Load extra RX data byte", inline=True)
comment(0x8372, "Send to Tube via R3", inline=True)
comment(0x8375, "Init carry for increment", inline=True)
comment(0x8376, "Y=8: start at byte 0 of the 4-byte RXCB pointer", inline=True)
comment(0x8378, "A=0: add carry only (increment)", inline=True)
comment(0x837A, "Add carry to pointer byte", inline=True)
comment(0x837C, "Store back to RXCB", inline=True)
comment(0x837E, "Next byte", inline=True)
comment(0x837F, "Keep going while carry propagates", inline=True)
comment(0x8381, "Restore X from stack", inline=True)
comment(0x8382, "Transfer to X register", inline=True)
comment(0x8383, "A=&FF: return value (transfer done)", inline=True)
comment(0x8385, "Return", inline=True)
comment(0x8386, "Load received port byte", inline=True)
comment(0x8389, "Port != 0: data transfer frame", inline=True)
comment(0x838B, "Port=0: load control byte", inline=True)
comment(0x838E, "Ctrl = &82 (POKE)?", inline=True)
comment(0x8390, "Yes: POKE also needs data transfer", inline=True)
comment(0x8392, "Other port-0 ops: immediate dispatch", inline=True)
comment(0x8395, "Update buffer pointer and check for Tube", inline=True)
comment(0x8398, "Transfer not done: skip buffer update", inline=True)
comment(0x839A, "Load buffer bytes remaining", inline=True)
comment(0x839C, "For address add", inline=True)
comment(0x839D, "Add to buffer base address", inline=True)
comment(0x839F, "No carry: skip high byte increment", inline=True)
comment(0x83A1, "Carry: increment buffer high byte", inline=True)
comment(0x83A3, "Y=8: store updated buffer position", inline=True)
comment(0x83A5, "Store updated low byte to RXCB", inline=True)
comment(0x83A7, "Y=9: buffer high byte offset", inline=True)
comment(0x83A8, "Load updated buffer high byte", inline=True)
comment(0x83AA, "Store high byte to RXCB", inline=True)
comment(0x83AC, "Check port byte again", inline=True)
comment(0x83AF, "Port=0: immediate op, discard+listen", inline=True)
comment(0x83B1, "Load source network from scout buffer", inline=True)
comment(0x83B4, "Y=3: RXCB source network offset", inline=True)
comment(0x83B6, "Store source network to RXCB", inline=True)
comment(0x83B8, "Y=2: source station offset", inline=True)
comment(0x83B9, "Load source station from scout buffer", inline=True)
comment(0x83BC, "Store source station to RXCB", inline=True)
comment(0x83BE, "Y=1: port byte offset", inline=True)
comment(0x83BF, "Load port byte", inline=True)
comment(0x83C2, "Store port to RXCB", inline=True)
comment(0x83C4, "Y=0: control/flag byte offset", inline=True)
comment(0x83C5, "Load control byte from scout", inline=True)
comment(0x83C8, "Set bit7: signals wait_net_tx_ack that reply arrived", inline=True)
comment(0x83CA, "Store to RXCB byte 0 (bit 7 set = complete)", inline=True)
comment(0x83CC, "Load callback event flags", inline=True)
comment(0x83CF, "Shift bit 0 into carry", inline=True)
comment(0x83D0, "Bit 0 clear: no callback, skip to reset", inline=True)
comment(0x83D2, "Load RXCB workspace pointer low byte (carry set on entry)", inline=True)
comment(0x83D4, "Count slots", inline=True)
comment(0x83D5, "Subtract 12 bytes per RXCB slot", inline=True)
comment(0x83D7, "Loop until pointer exhausted", inline=True)
comment(0x83D9, "Adjust for off-by-one", inline=True)
comment(0x83DA, "Check slot index >= 3", inline=True)
comment(0x83DC, "Slot < 3: no callback, skip to reset", inline=True)
comment(0x83DE, "Discard scout and reset listen state", inline=True)
comment(0x83E1, "Pass slot index as callback parameter", inline=True)
comment(0x83E2, "Jump to TX completion with slot index", inline=True)
comment(0x83E5, "Discard scout and reset RX listen", inline=True)
comment(0x83E8, "Reset ADLC and return to RX listen", inline=True)
comment(0x83EB, "A=&9B: low byte of nmi_rx_scout", inline=True)
comment(0x83ED, "Y=&80: high byte of nmi_rx_scout", inline=True)
comment(0x83EF, "Install nmi_rx_scout as NMI handler", inline=True)
comment(0x83F2, "Tube flag bit 1 AND tx_flags bit 1", inline=True)
comment(0x83F4, "Check if Tube transfer active", inline=True)
comment(0x83F7, "Test tx_flags for Tube transfer", inline=True)
comment(0x83FA, "No Tube transfer active -- skip release", inline=True)
comment(0x83FC, "Release Tube claim before discarding", inline=True)
comment(0x83FF, "Return", inline=True)
comment(0x8400, "Save X on stack", inline=True)
comment(0x8401, "Push X", inline=True)
comment(0x8402, "X=4: start at scout byte offset 4", inline=True)
comment(0x8404, "A=2: Tube transfer check mask", inline=True)
comment(0x8406, "Check tx_flags Tube bit", inline=True)
comment(0x8409, "Tube active: use R3 write path", inline=True)
comment(0x840B, """\
4.21 Master 128: save/restore ACCCON across the (open_port_buf),Y stores.
The destination port buffer may live in shadow RAM; bit 0 of ACCCON (D)
controls whether (zp),Y addressing hits shadow vs main RAM. Workspace &97
holds the desired ACCCON value pre-loaded by the caller.""")
comment(0x840B, "Save current ACCCON on stack (4.21 Master 128)", inline=True)
comment(0x840E, "Push ACCCON snapshot", inline=True)
comment(0x840F, "Load desired ACCCON from workspace &97", inline=True)
comment(0x8411, "Set ACCCON for the upcoming (open_port_buf),Y stores", inline=True)
comment(0x8414, "Y = current buffer position", inline=True)
comment(0x8416, "Load scout data byte", inline=True)
comment(0x8419, "Store to port buffer", inline=True)
comment(0x841B, "Advance buffer pointer", inline=True)
comment(0x841C, "No page crossing", inline=True)
comment(0x841E, "Page crossing: inc buffer high byte", inline=True)
comment(0x8420, "Decrement remaining page count", inline=True)
comment(0x8422, "No pages left: overflow", inline=True)
comment(0x8424, "Next scout data byte", inline=True)
comment(0x8425, "Save updated buffer position", inline=True)
comment(0x8427, "Done all scout data? (X reaches &0C)", inline=True)
comment(0x8429, "No: continue copying", inline=True)
comment(0x842B, "Pull saved ACCCON from stack", inline=True)
comment(0x842C, "Restore caller's ACCCON before continuing", inline=True)
comment(0x842F, "Pull saved X from stack", inline=True)
comment(0x8431, "Tail-jump to rx_complete_update_rxcb", inline=True)
comment(0x8434, "Reset ADLC if carry set", inline=True)
comment(0x8436, "Tube path: load scout data byte", inline=True)
comment(0x8439, "Send byte to Tube via R3", inline=True)
comment(0x843C, "Increment buffer position counters", inline=True)
comment(0x843F, "Counter overflow: handle end of buffer", inline=True)
comment(0x8441, "Next scout data byte", inline=True)
comment(0x8442, "Done all scout data?", inline=True)
comment(0x8444, "No: continue Tube writes", inline=True)
comment(0x8448, "Check if Tube needs releasing", inline=True)
comment(0x844A, "Bit7 set: already released", inline=True)
comment(0x844C, "A=&82: Tube release claim type", inline=True)
comment(0x844E, "Release Tube address claim", inline=True)
comment(0x8451, "Clear release flag (LSR clears bit7)", inline=True)
comment(0x8453, "Return", inline=True)
comment(0x8454, "Control byte &81-&88 range check", inline=True)
comment(0x8457, "Below &81: not an immediate op", inline=True)
comment(0x8459, "Out of range low: jump to discard", inline=True)
comment(0x845B, "Above &88: not an immediate op", inline=True)
comment(0x845D, "Out of range high: jump to discard", inline=True)
comment(0x845F, "HALT(&87)/CONTINUE(&88) skip protection", inline=True)
comment(0x8461, "Ctrl >= &87: dispatch without mask check", inline=True)
comment(0x8463, "Convert ctrl byte to 0-based index for mask", inline=True)
comment(0x8464, "For subtract", inline=True)
comment(0x8465, "A = ctrl - &81 (0-based operation index)", inline=True)
comment(0x8467, "Y = index for mask rotation count", inline=True)
comment(0x8468, "Load protection mask from LSTAT", inline=True)
comment(0x846B, "Rotate mask right by control byte index", inline=True)
comment(0x846C, "Decrement rotation counter", inline=True)
comment(0x846D, "Loop until bit aligned", inline=True)
comment(0x846F, "Bit set = operation disabled, discard", inline=True)
comment(0x8471, "Reload ctrl byte for dispatch table", inline=True)
comment(0x8474, "Hi byte: all handlers are in page &84", inline=True)
comment(0x8476, "Push hi byte for PHA/PHA/RTS dispatch", inline=True)
comment(0x8477, "Load handler low byte from jump table", inline=True)
comment(0x847A, "Push handler low byte", inline=True)
comment(0x847B, "RTS dispatches to handler", inline=True)
comment(0x847C, "Increment port buffer length", inline=True)
comment(0x847E, """\
Tube-path overflow exit from copy_scout_to_buffer: restores the Master 128
ACCCON that was saved at &840B before re-joining the scout-done path.""")
comment(0x847E, "Pull saved ACCCON from stack", inline=True)
comment(0x847F, "Restore caller's ACCCON on Tube-overflow exit", inline=True)
comment(0x8482, "Check if scout data index reached 11", inline=True)
comment(0x8484, "Yes: loop back to continue reading", inline=True)
comment(0x8486, "Restore A from stack", inline=True)
comment(0x8487, "Transfer to X", inline=True)
comment(0x8488, "Jump to discard handler", inline=True)
comment(0x8493, "A=0: port buffer lo at page boundary", inline=True)
comment(0x8495, "Set port buffer lo", inline=True)
comment(0x8497, "Buffer length lo = &82", inline=True)
comment(0x8499, "Set buffer length lo", inline=True)
comment(0x849B, "Buffer length hi = 1", inline=True)
comment(0x849D, "Set buffer length hi", inline=True)
comment(0x849F, "Load RX page hi for buffer", inline=True)
comment(0x84A1, "Set port buffer hi", inline=True)
comment(0x84A3, "Y=1: copy 2 bytes (1 down to 0)", inline=True)
comment(0x84A5, "Load remote address byte", inline=True)
comment(0x84A8, "Store to exec address workspace", inline=True)
comment(0x84AB, "Next byte (descending)", inline=True)
comment(0x84AC, "Loop until all 4 bytes copied", inline=True)
comment(0x84AE, "Enter common data-receive path", inline=True)
comment(0x84B1, "Port workspace offset = &2E", inline=True)
comment(0x84B3, "Store as port_ws_offset", inline=True)
comment(0x84B5, "RX buffer page = &0D", inline=True)
comment(0x84B7, "Store as rx_buf_offset", inline=True)
comment(0x84B9, "Enter POKE data-receive path", inline=True)
comment(0x84BC, "Buffer length hi = 1", inline=True)
comment(0x84BE, "Set buffer length hi", inline=True)
comment(0x84C0, "Buffer length lo = &FC", inline=True)
comment(0x84C2, "Set buffer length lo", inline=True)
comment(0x84C4, "Buffer start lo = &EE", inline=True)
comment(0x84C6, "Set port buffer lo", inline=True)
comment(0x84C8, "Buffer hi = &88 (response goes to &88EE area)", inline=True)
comment(0x84CA, "Set port buffer hi", inline=True)
comment(0x84CE, "Port workspace offset = &3D", inline=True)
comment(0x84D0, "Store workspace offset lo", inline=True)
comment(0x84D2, "RX buffer page = &0D", inline=True)
comment(0x84D4, "Store workspace offset hi", inline=True)
comment(0x84D6, "Scout status = 2 (PEEK response)", inline=True)
comment(0x84D8, "Store scout status", inline=True)
comment(0x84DB, "Calculate transfer size for response", inline=True)
comment(0x84DE, "C=0: transfer not set up, discard", inline=True)
comment(0x84E0, "Mark TX flags bit 7 (reply pending)", inline=True)
comment(0x84E3, "Set reply pending flag", inline=True)
comment(0x84E5, "Store updated TX flags", inline=True)
comment(0x84E8, "CR1=&44: TIE | TX_LAST_DATA", inline=True)
comment(0x84EA, "Write CR1: enable TX interrupts", inline=True)
comment(0x84ED, "CR2=&A7: RTS|CLR_RX_ST|FC_TDRA|PSE", inline=True)
comment(0x84EF, "Write CR2 for TX setup", inline=True)
comment(0x84F2, "NMI handler lo byte (self-modifying)", inline=True)
comment(0x84F4, "Y=&85: NMI handler high byte", inline=True)
comment(0x84F6, "Acknowledge and write TX dest", inline=True)
comment(0x84F9, "Get buffer position for reply header", inline=True)
comment(0x84FB, "Clear carry for offset addition", inline=True)
comment(0x84FC, "Data offset = buf_len + &80 (past header)", inline=True)
comment(0x84FE, "Y=&7F: reply data length slot", inline=True)
comment(0x8500, "Store reply data length in RX buffer", inline=True)
comment(0x8502, "Y=&80: source station slot", inline=True)
comment(0x8504, "Load requesting station number", inline=True)
comment(0x8507, "Store source station in reply header", inline=True)
comment(0x850A, "Load requesting network number", inline=True)
comment(0x850D, "Store source network in reply header", inline=True)
comment(0x850F, "Load control byte from received frame", inline=True)
comment(0x8512, "Save TX operation type for SR dispatch", inline=True)
comment(0x8515, "Op codes >= &86 (HALT/CONTINUE/machine-type) skip "
                "the SR setup", inline=True)
comment(0x8517, "Skip ahead to the ACCCON IRR set", inline=True)
comment(0x8519, "Load workspace ACR-format byte", inline=True)
comment(0x851C, "Stash a copy in ws_0d69 for later restore", inline=True)
comment(0x851F, "In shift-register mode-2 control bits", inline=True)
comment(0x8521, "Write updated workspace byte back to ws_0d68",
    inline=True)
comment(0x8524, "A=&80: ACCCON bit 7 (IRR -- raise interrupt)", inline=True)
comment(0x8526, "Set ACCCON IRR to flag a pending interrupt to MOS",
        inline=True)
comment(0x8529, "Return to idle listen mode", inline=True)
comment(0x852C, "Increment buffer length low byte", inline=True)
comment(0x852E, "No overflow: done", inline=True)
comment(0x8530, "Increment buffer length high byte", inline=True)
comment(0x8532, "No overflow: done", inline=True)
comment(0x8534, "Increment buffer pointer low byte", inline=True)
comment(0x8536, "No overflow: done", inline=True)
comment(0x8538, "Increment buffer pointer high byte", inline=True)
comment(0x853A, "Return", inline=True)
comment(0x8542, "Push hi byte on stack", inline=True)
comment(0x8543, "A=&81: low byte of tx_done_exit-1 (&8581)", inline=True)
comment(0x8545, "Push lo byte on stack", inline=True)
comment(0x8546, "Call remote JSR; RTS to tx_done_exit", inline=True)

subroutine(0x853B, "tx_done_dispatch_lo",
    title="TX done dispatch lo-byte table (5 entries)",
    description="""\
Low bytes of PHA/PHA/RTS dispatch targets for TX operation types
`&83`-`&87`. Read by the dispatch at
[`dispatch_svc5`](address:8048) via
`LDA tx_done_dispatch_lo-&83,Y` (the operand lands mid-instruction
inside [`set_rx_buf_len_hi`](address:84BE)). The dispatch
trampoline pushes `&85` as the high byte, so targets are
`&85xx+1`. Entries for `Y < &83` read from preceding code bytes
and are not valid operation types. Per-entry inline comments
identify each TX operation type's handler.""")

# tx_done_econet_event (&8542): TX operation type &84 handler.
comment(0x8549, "X = remote address lo from exec_addr_lo", inline=True)
comment(0x854C, "A = remote address hi from exec_addr_hi", inline=True)
comment(0x854F, "Y = 8: Econet event number", inline=True)

comment(0x8554, "Exit TX done handler", inline=True)
comment(0x8557, "X = remote address lo", inline=True)
comment(0x855A, "Y = remote address hi", inline=True)
comment(0x855D, "Call ROM entry point at &8000", inline=True)
comment(0x8560, "Exit TX done handler", inline=True)
comment(0x8563, "A=&04: bit 2 mask (halt flag in econet_flags)", inline=True)
comment(0x8565, "Test if already halted", inline=True)
comment(0x8568, "Already halted: skip to exit", inline=True)
comment(0x856A, "Set bit 2 in econet_flags (halt)", inline=True)
comment(0x856D, "Store halt flag", inline=True)
comment(0x8570, "A=4: re-load halt bit mask", inline=True)
comment(0x8572, "Enable interrupts during halt wait", inline=True)
comment(0x8573, "Test halt flag", inline=True)
comment(0x8576, "Still halted: keep spinning", inline=True)
comment(0x857A, "Load current econet_flags", inline=True)
comment(0x857D, "Clear bit 2: release halted station", inline=True)
comment(0x857F, "Store updated flags", inline=True)
comment(0x8582, "Restore Y from stack", inline=True)
comment(0x8583, "Transfer to Y register", inline=True)
comment(0x8584, "Restore X from stack", inline=True)
comment(0x8585, "Transfer to X register", inline=True)
comment(0x8586, "A=0: success status", inline=True)
comment(0x8588, "Return with A=0 (success)", inline=True)
comment(0x8589, "Save X on stack", inline=True)
comment(0x858A, "Push X", inline=True)
comment(0x858B, "Y=2: TXCB offset for dest station", inline=True)
comment(0x858D, "Load dest station from TX control block", inline=True)
comment(0x858F, "Store to TX scout buffer", inline=True)
comment(0x8593, "Load dest network from TX control block", inline=True)
comment(0x8595, "Store to TX scout buffer", inline=True)
comment(0x8598, "Y=0: first byte of TX control block", inline=True)
comment(0x859A, "Load control/flag byte", inline=True)
comment(0x859C, "Bit7 set: immediate operation ctrl byte", inline=True)
comment(0x859E, "Bit7 clear: normal data transfer", inline=True)
comment(0x85A1, "Store control byte to TX scout buffer", inline=True)
comment(0x85A4, "X = control byte for range checks", inline=True)
comment(0x85A5, "Y=1: port byte offset", inline=True)
comment(0x85A6, "Load port byte from TX control block", inline=True)
comment(0x85A8, "Store port byte to TX scout buffer", inline=True)
comment(0x85AB, "Port != 0: skip immediate op setup", inline=True)
comment(0x85AD, "Ctrl < &83: PEEK/POKE need address calc", inline=True)
comment(0x85AF, "Ctrl >= &83: skip to range check", inline=True)
comment(0x85B1, "Init borrow for 4-byte subtract", inline=True)
comment(0x85B2, "Save carry on stack for loop", inline=True)
comment(0x85B3, "Y=8: high pointer offset in TXCB", inline=True)
comment(0x85B5, "Load TXCB[Y] (end addr byte)", inline=True)
comment(0x85B7, "Y -= 4: back to start addr offset", inline=True)
comment(0x85B8, "(continued)", inline=True)
comment(0x85B9, "(continued)", inline=True)
comment(0x85BA, "(continued)", inline=True)
comment(0x85BB, "Restore borrow from stack", inline=True)
comment(0x85BC, "end - start = transfer size byte", inline=True)
comment(0x85BE, "Store result to tx_data_start", inline=True)
comment(0x85C1, "Y += 5: advance to next end byte", inline=True)
comment(0x85C2, "(continued)", inline=True)
comment(0x85C3, "(continued)", inline=True)
comment(0x85C4, "(continued)", inline=True)
comment(0x85C5, "(continued)", inline=True)
comment(0x85C6, "Save borrow for next byte", inline=True)
comment(0x85C7, "Done all 4 bytes? (Y reaches &0C)", inline=True)
comment(0x85C9, "No: next byte pair", inline=True)
comment(0x85CB, "Discard final borrow", inline=True)
comment(0x85CC, "Ctrl < &81: not an immediate op", inline=True)
comment(0x85CE, "Below range: normal data transfer", inline=True)
comment(0x85D0, "Ctrl >= &89: out of immediate range", inline=True)
comment(0x85D2, "Above range: normal data transfer", inline=True)
comment(0x85D4, "Y=&0C: start of extra data in TXCB", inline=True)
comment(0x85D6, "Load extra parameter byte from TXCB", inline=True)
comment(0x85D8, "Copy to NMI shim workspace at &0D1A+Y", inline=True)
comment(0x85DB, "Next byte", inline=True)
comment(0x85DC, "Done 4 bytes? (Y reaches &10)", inline=True)
comment(0x85DE, "No: continue copying", inline=True)
comment(0x85E0, "A=&20: mask for SR2 INACTIVE bit", inline=True)
comment(0x85E2, "Test SR2 if line is idle", inline=True)
comment(0x85E5, "Line not idle: handle as line jammed", inline=True)
comment(0x85E7, "A=&FD: high byte of timeout counter", inline=True)
comment(0x85E9, "Push timeout high byte to stack", inline=True)
comment(0x85EA, "Scout frame = 6 address+ctrl bytes", inline=True)
comment(0x85EC, "Store scout frame length", inline=True)
comment(0x85EF, "A=0: init low byte of timeout counter", inline=True)
comment(0x85F1, "Save TX index", inline=True)
comment(0x85F4, "Push timeout byte 1 on stack", inline=True)
comment(0x85F5, "Push timeout byte 2 on stack", inline=True)
comment(0x85F6, "Y=&E7: CR2 value for TX prep (RTS|CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)", inline=True)
comment(0x85F8, "A=&04: INACTIVE bit mask for SR2 test", inline=True)
comment(0x85FA, "Save interrupt state", inline=True)
comment(0x85FB, "Disable interrupts for ADLC access", inline=True)
comment(0x85FC, "INTOFF -- disable NMIs", inline=True)
comment(0x85FF, "INTOFF again (belt-and-braces)", inline=True)
comment(0x8602, "Z = &04 AND SR2 -- tests INACTIVE", inline=True)
comment(0x8605, "INACTIVE not set -- re-enable NMIs and loop", inline=True)
comment(0x8607, "Read SR1 (acknowledge pending interrupt)", inline=True)
comment(0x860A, "CR2=&67: CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE", inline=True)
comment(0x860C, "Write CR2: clear status, prepare TX", inline=True)
comment(0x860F, "A=&10: CTS mask for SR1 bit4", inline=True)
comment(0x8611, "Test SR1 CTS present", inline=True)
comment(0x8614, "CTS set -- clock hardware detected, start TX", inline=True)
comment(0x8616, "INTON -- re-enable NMIs (&FE20 read)", inline=True)
comment(0x8619, "Restore interrupt state", inline=True)
comment(0x861A, "3-byte timeout counter on stack", inline=True)
comment(0x861B, "Increment timeout counter byte 1", inline=True)
comment(0x861E, "Not overflowed: retry INACTIVE test", inline=True)
comment(0x8620, "Increment timeout counter byte 2", inline=True)
comment(0x8623, "Not overflowed: retry INACTIVE test", inline=True)
comment(0x8625, "Increment timeout counter byte 3", inline=True)
comment(0x8628, "Not overflowed: retry INACTIVE test", inline=True)
comment(0x862C, "Error &44: control byte out of valid range", inline=True)
comment(0x8630, "CR2=&07: FC_TDRA | 2_1_BYTE | PSE (abort TX)", inline=True)
comment(0x8632, "Write CR2 to abort TX", inline=True)
comment(0x8635, "Clean 3 bytes of timeout loop state", inline=True)
comment(0x8636, "Pop saved register", inline=True)
comment(0x8637, "Pop saved register", inline=True)
comment(0x8638, "Error &40 = 'Line Jammed'", inline=True)
comment(0x863A, "ALWAYS branch to shared error handler", inline=True)
comment(0x863C, "Error &43 = 'No Clock'", inline=True)
comment(0x863E, "Offset 0 = error byte in TX control block", inline=True)
comment(0x8640, "Store error code in TX CB byte 0", inline=True)
comment(0x8642, "&80 = TX complete flag", inline=True)
comment(0x8644, "Signal TX operation complete", inline=True)
comment(0x8647, "Restore X saved by caller", inline=True)
comment(0x8648, "Move to X register", inline=True)
comment(0x8649, "Return to TX caller", inline=True)
comment(0x864A, "Write CR2 = Y (&E7: RTS|CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)", inline=True)
comment(0x864D, "CR1=&44: RX_RESET | TIE (TX active, TX interrupts enabled)", inline=True)
comment(0x864F, "Write to ADLC CR1", inline=True)
comment(0x8652, "X=&E7: low byte of nmi_tx_data (&86E7)", inline=True)
comment(0x8654, "High byte of NMI handler address", inline=True)
comment(0x8656, "Write NMI vector low byte directly", inline=True)
comment(0x8659, "Write NMI vector high byte directly", inline=True)
comment(0x865C, "SEC: prepare carry for ROR into bit 7", inline=True)
comment(0x865D, "Rotate carry into bit 7 of prot_flags (Tube-claimed)", inline=True)
comment(0x865F, "INTON -- NMIs now fire for TDRA (&FE20 read)", inline=True)
comment(0x8662, "Load destination port number", inline=True)
comment(0x8665, "Port != 0: standard data transfer", inline=True)
comment(0x8667, "Port 0: load control byte for table lookup", inline=True)
comment(0x866A, "Look up tx_flags from table", inline=True)
comment(0x866D, "Store operation flags", inline=True)
comment(0x8670, "Look up tx_length from table", inline=True)
comment(0x8673, "Store expected transfer length", inline=True)
comment(0x8676, "A=&86: high byte of tx_ctrl_* dispatch target", inline=True)
comment(0x8678, "Push high byte for PHA/PHA/RTS dispatch", inline=True)
comment(0x8679, "Look up handler address low from table", inline=True)
comment(0x867C, "Push low byte for PHA/PHA/RTS dispatch", inline=True)
comment(0x867D, "RTS dispatches to control-byte handler", inline=True)

subroutine(0x867E, "tx_ctrl_dispatch_lo",
    title="TX ctrl dispatch lo-byte table (8 entries)",
    description="""\
Low bytes of PHA/PHA/RTS dispatch targets for TX control byte
types `&81`-`&88`. Read by the dispatch at `&8679` via
`LDA tx_ctrl_dispatch_lo-&81,Y` (the operand lands mid-
instruction inside
[`intoff_test_inactive`](address:85FC)). High byte pushed by
the dispatcher is always `&86`, so targets are `&86xx+1`. Last
entry (`&88`) dispatches to
[`tx_ctrl_machine_type`](address:8686), the 4 bytes immediately
after the table.""")
comment(0x8686, "A=3: scout_status for machine type query", inline=True)
comment(0x8688, "Skip address addition, store status", inline=True)
comment(0x868A, "A=3: scout_status for PEEK op", inline=True)
comment(0x868E, "Scout status = 2 (POKE transfer)", inline=True)
comment(0x8690, "Store scout status", inline=True)
comment(0x8693, "Clear carry for 4-byte addition", inline=True)
comment(0x8694, "Save carry on stack", inline=True)
comment(0x8695, "Y=&0C: start at offset 12", inline=True)
comment(0x8697, "Load workspace address byte", inline=True)
comment(0x869A, "Restore carry from previous byte", inline=True)
comment(0x869B, "Add TXCB address byte", inline=True)
comment(0x869D, "Store updated address byte", inline=True)
comment(0x86A0, "Next byte", inline=True)
comment(0x86A1, "Save carry for next addition", inline=True)
comment(0x86A2, "Compare Y with 16-byte boundary", inline=True)
comment(0x86A4, "Below boundary: continue addition", inline=True)
comment(0x86A6, "Restore processor flags", inline=True)
comment(0x86A7, "Skip buffer setup if transfer size is zero", inline=True)
comment(0x86A9, "Load dest station for broadcast check", inline=True)
comment(0x86AC, "AND with dest network", inline=True)
comment(0x86AF, "Both &FF = broadcast address?", inline=True)
comment(0x86B1, "Not broadcast: unicast path", inline=True)
comment(0x86B3, "Broadcast scout: 14 bytes total", inline=True)
comment(0x86B5, "Store broadcast scout length", inline=True)
comment(0x86B8, "A=&40: broadcast flag", inline=True)
comment(0x86BA, "Set broadcast flag in tx_flags", inline=True)
comment(0x86BD, "Y=4: start of address data in TXCB", inline=True)
comment(0x86BF, "Copy TXCB address bytes to scout buffer", inline=True)
comment(0x86C1, "Store to TX source/data area", inline=True)
comment(0x86C4, "Next byte", inline=True)
comment(0x86C5, "Done 8 bytes? (Y reaches &0C)", inline=True)
comment(0x86C7, "No: continue copying", inline=True)
comment(0x86CB, "A=0: clear flags for unicast", inline=True)
comment(0x86CD, "Clear tx_flags", inline=True)
comment(0x86D0, "scout_status=2: data transfer pending", inline=True)
comment(0x86D2, "Store scout status", inline=True)
comment(0x86D5, "Copy TX block pointer to workspace ptr", inline=True)
comment(0x86D7, "Store low byte", inline=True)
comment(0x86D9, "Copy TX block pointer high byte", inline=True)
comment(0x86DB, "Store high byte", inline=True)
comment(0x86DD, "Calculate transfer size from RXCB", inline=True)
comment(0x86E0, "Restore processor status from stack", inline=True)
comment(0x86E1, "Restore stacked registers (4 PLAs)", inline=True)
comment(0x86E5, "Restore X from A", inline=True)
comment(0x86E6, "Return to caller", inline=True)
comment(0x86E7, "Load TX buffer index", inline=True)
comment(0x86EA, "SR1: V=bit6(TDRA), N=bit7(IRQ)", inline=True)
comment(0x86ED, "TDRA not set -- TX error", inline=True)
comment(0x86EF, "Load byte from TX buffer", inline=True)
comment(0x86F2, "Write to TX_DATA (continue frame)", inline=True)
comment(0x86F5, "Next TX buffer byte", inline=True)
comment(0x86F6, "Load second byte from TX buffer", inline=True)
comment(0x86F9, "Advance TX index past second byte", inline=True)
comment(0x86FA, "Save updated TX buffer index", inline=True)
comment(0x86FD, "Write second byte to TX_DATA", inline=True)
comment(0x8700, "Compare index to TX length", inline=True)
comment(0x8703, "Frame complete -- go to TX_LAST_DATA", inline=True)
comment(0x8705, "Check if we can send another pair", inline=True)
comment(0x8708, "IRQ set -- send 2 more bytes (tight loop)", inline=True)
comment(0x870A, "Wait for next NMI", inline=True)
comment(0x870D, "Error &42", inline=True)
comment(0x8711, "CR2=&67: clear status, return to listen", inline=True)
comment(0x8713, "Write CR2: clear status, idle listen", inline=True)
comment(0x8716, "Error &41 (TDRA not ready)", inline=True)
comment(0x8718, "INTOFF (also loads station ID)", inline=True)
comment(0x871B, "PHA/PLA delay loop (256 iterations for NMI disable)", inline=True)
comment(0x871C, "PHA/PLA delay (~7 cycles each)", inline=True)
comment(0x871D, "Increment delay counter", inline=True)
comment(0x871E, "Loop 256 times for NMI disable", inline=True)
comment(0x8720, "Store error and return to idle", inline=True)
comment(0x8723, "CR2=&3F: TX_LAST_DATA | CLR_RX_ST | FLAG_IDLE | FC_TDRA | 2_1_BYTE | PSE", inline=True)
comment(0x8725, "Write to ADLC CR2", inline=True)
comment(0x8728, "Install NMI handler at &8728 (TX completion)", inline=True)
comment(0x872A, "High byte of handler address", inline=True)
comment(0x872C, "Install and return via set_nmi_vector", inline=True)
comment(0x872F, "Jump to error handler", inline=True)
comment(0x8731, "Write CR1 to switch from TX to RX", inline=True)
comment(0x8734, "Test workspace flags", inline=True)
comment(0x8737, "bit6 not set -- check bit0", inline=True)
comment(0x8739, "bit6 set -- TX completion", inline=True)
comment(0x873C, "A=1: mask for bit0 test", inline=True)
comment(0x873E, "Test tx_flags bit0 (handshake)", inline=True)
comment(0x8741, "bit0 clear: install reply handler", inline=True)
comment(0x8743, "bit0 set -- four-way handshake data phase", inline=True)
comment(0x8746, "Install nmi_reply_validate at &874B", inline=True)
comment(0x8748, "Install handler", inline=True)
comment(0x874B, "A=&01: AP mask for SR2", inline=True)
comment(0x874D, "Test SR2 AP (Address Present)", inline=True)
comment(0x8750, "No AP -- error", inline=True)
comment(0x8752, "Read first RX byte (destination station)", inline=True)
comment(0x8755, "Compare to our station ID (workspace copy)", inline=True)
comment(0x8758, "Not our station -- error/reject", inline=True)
comment(0x875A, "Install next handler at &8758 (reply continuation)", inline=True)
comment(0x875C, "Install continuation handler", inline=True)
comment(0x875F, "Read RX byte (destination station)", inline=True)
comment(0x8762, "No RDA -- error", inline=True)
comment(0x8764, "Read destination network byte", inline=True)
comment(0x8767, "Non-zero -- network mismatch, error", inline=True)
comment(0x8769, "A=&76: low byte of nmi_reply_validate (&8776)", inline=True)
comment(0x876B, "Test SR1 IRQ (N=bit7) -- more data ready?", inline=True)
comment(0x876E, "IRQ set -- fall through to &8779", inline=True)
comment(0x8770, "IRQ not set -- install handler", inline=True)
comment(0x8773, "Store error and return to idle", inline=True)
comment(0x8776, "Test SR2 RDA (bit7). Must be set for valid reply.", inline=True)
comment(0x8779, "No RDA -- error (FV masking RDA via PSE would cause this)", inline=True)
comment(0x877B, "Read source station", inline=True)
comment(0x877E, "Compare to original TX destination station (&0D20)", inline=True)
comment(0x8781, "Mismatch -- not the expected reply, error", inline=True)
comment(0x8783, "Read source network", inline=True)
comment(0x8786, "Compare to original TX destination network (&0D21)", inline=True)
comment(0x8789, "Mismatch -- error", inline=True)
comment(0x878B, "A=&02: FV mask for SR2 bit1", inline=True)
comment(0x878D, "Test SR2 FV -- frame must be complete", inline=True)
comment(0x8790, "No FV -- incomplete frame, error", inline=True)
comment(0x8792, "CR2=&A7: RTS|CLR_TX_ST|FC_TDRA|2_1_BYTE|PSE (TX in handshake)", inline=True)
comment(0x8794, "Write CR2: enable RTS for TX handshake", inline=True)
comment(0x8797, "CR1=&44: RX_RESET | TIE (TX active for scout ACK)", inline=True)
comment(0x8799, "Write CR1: reset RX, enable TX interrupt", inline=True)
comment(0x879C, "Install handshake_await_ack into &0D43/&0D44 (four-way data phase)", inline=True)
comment(0x879E, "High byte &88 of next handler address", inline=True)
comment(0x87A0, "Store low byte to nmi_next_lo", inline=True)
comment(0x87A3, "Store high byte to nmi_next_hi", inline=True)
comment(0x87A6, "Load dest station for scout ACK TX", inline=True)
comment(0x87A9, "Test SR1 TDRA (V=bit6)", inline=True)
comment(0x87AC, "TDRA not ready -- error", inline=True)
comment(0x87AE, "Write dest station to TX FIFO", inline=True)
comment(0x87B1, "Write dest network to TX FIFO", inline=True)
comment(0x87B4, "Write dest network to TX FIFO", inline=True)
comment(0x87B7, "Install handler at &87B7 (write src addr for scout ACK)", inline=True)
comment(0x87B9, "High byte &87 of handler address", inline=True)
comment(0x87BB, "Set NMI vector and return", inline=True)
comment(0x87BE, "Load our station ID from workspace copy", inline=True)
comment(0x87C1, "Test SR1 TDRA", inline=True)
comment(0x87C4, "TDRA not ready -- error", inline=True)
comment(0x87C6, "Write our station to TX FIFO", inline=True)
comment(0x87C9, "Write network=0 to TX FIFO", inline=True)
comment(0x87CB, "Write network byte to TX FIFO", inline=True)
comment(0x87CE, "Test bit 1 of tx_flags", inline=True)
comment(0x87D0, "Check if immediate-op or data-transfer", inline=True)
comment(0x87D3, "Bit 1 set: immediate op, use alt handler", inline=True)
comment(0x87D5, "A=&EB: low byte of nmi_data_tx alt-entry (&87EB)", inline=True)
comment(0x87D7, "Y=&87: high byte of nmi_data_tx", inline=True)
comment(0x87D9, "Install and return via set_nmi_vector", inline=True)
comment(0x87DC, "Install nmi_imm_data at &8837", inline=True)
comment(0x87DE, "High byte of handler address", inline=True)
comment(0x87E0, "Install and return via set_nmi_vector", inline=True)
comment(0x87E3, "Y = buffer offset, resume from last position", inline=True)
comment(0x87E5, "No pages left: send final partial page", inline=True)
comment(0x87E7, "Load remaining byte count", inline=True)
comment(0x87E9, "Zero bytes left: skip to TDRA check", inline=True)
comment(0x87EB, "Load remaining byte count (alt entry)", inline=True)
comment(0x87ED, "Zero: loop back to top of handler", inline=True)
comment(0x87EF, "Test SR1 TDRA (V=bit6)", inline=True)
comment(0x87F2, "TDRA not ready -- error", inline=True)
comment(0x87F4, """\
4.21 Master 128: save/restore ACCCON across the (open_port_buf),Y reads
in this TX FIFO loop. Same idiom as copy_scout_to_buffer / nmi_data_rx_bulk;
workspace &97 holds the desired ACCCON value pre-loaded by the caller.""")
comment(0x87F4, "Save current ACCCON on stack (Master 128)", inline=True)
comment(0x87F7, "Push ACCCON snapshot", inline=True)
comment(0x87F8, "Load desired ACCCON from workspace &97", inline=True)
comment(0x87FA, "Set ACCCON for the upcoming buffer reads", inline=True)
comment(0x87FD, "Write data byte to TX FIFO", inline=True)
comment(0x87FF, "Write first byte of pair to FIFO", inline=True)
comment(0x8802, "Advance buffer offset", inline=True)
comment(0x8803, "No page crossing", inline=True)
comment(0x8805, "Page crossing: decrement page count", inline=True)
comment(0x8807, "No pages left: send last data", inline=True)
comment(0x8809, "Increment buffer high byte", inline=True)
comment(0x880B, "Load second byte of pair", inline=True)
comment(0x880D, "Write second byte to FIFO", inline=True)
comment(0x8810, "Advance buffer offset", inline=True)
comment(0x8811, "Save updated buffer position", inline=True)
comment(0x8813, "No page crossing", inline=True)
comment(0x8815, "Page crossing: decrement page count", inline=True)
comment(0x8817, "No pages left: send last data", inline=True)
comment(0x881F, "Test ADLC SR1 IRQ flag for next byte pair", inline=True)
comment(0x8822, "IRQ still set: more bytes to send", inline=True)
comment(0x8824, "IRQ cleared: return from NMI", inline=True)
comment(0x8819, "Increment buffer high byte", inline=True)
comment(0x881B, "Pull saved ACCCON from stack", inline=True)
comment(0x881C, "Restore caller's ACCCON between byte pairs", inline=True)
comment(0x8827, "Pull saved ACCCON (frame-end path)", inline=True)
comment(0x8828, "Restore caller's ACCCON before TX_LAST_DATA", inline=True)
comment(0x882B, "CR2=&3F: TX_LAST_DATA (close data frame)", inline=True)
comment(0x882D, "Write CR2 to close frame", inline=True)
comment(0x8830, "Check tx_flags for next action", inline=True)
comment(0x8833, "Bit7 clear: error, install saved handler", inline=True)
comment(0x8835, "Install discard_reset_listen at &83F2", inline=True)
comment(0x8837, "High byte of &83F2 handler", inline=True)
comment(0x8839, "Set NMI vector and return", inline=True)
comment(0x883C, "Load saved next handler low byte", inline=True)
comment(0x883F, "Load saved next handler high byte", inline=True)
comment(0x8842, "Install saved handler and return", inline=True)
comment(0x8845, "Tube TX: test SR1 TDRA", inline=True)
comment(0x8848, "TDRA not ready -- error", inline=True)
comment(0x884A, "Read byte from Tube R3", inline=True)
comment(0x884D, "Write to TX FIFO", inline=True)
comment(0x8850, "Increment 4-byte buffer counter", inline=True)
comment(0x8852, "Low byte didn't wrap", inline=True)
comment(0x8854, "Carry into second byte", inline=True)
comment(0x8856, "No further carry", inline=True)
comment(0x8858, "Carry into third byte", inline=True)
comment(0x885A, "No further carry", inline=True)
comment(0x885C, "Carry into fourth byte", inline=True)
comment(0x885E, "Counter wrapped to zero: last data", inline=True)
comment(0x8860, "Read second Tube byte from R3", inline=True)
comment(0x8863, "Write second byte to TX FIFO", inline=True)
comment(0x8866, "Increment 4-byte counter (second byte)", inline=True)
comment(0x8868, "Low byte didn't wrap", inline=True)
comment(0x886A, "Carry into second byte", inline=True)
comment(0x886C, "No further carry", inline=True)
comment(0x886E, "Carry into third byte", inline=True)
comment(0x8870, "No further carry", inline=True)
comment(0x8872, "Carry into fourth byte", inline=True)
comment(0x8874, "Counter wrapped to zero: last data", inline=True)
comment(0x8876, "Test SR1 IRQ for tight loop", inline=True)
comment(0x8879, "IRQ still set: write 2 more bytes", inline=True)
comment(0x887B, "No IRQ: return, wait for next NMI", inline=True)
comment(0x887E, "TX error: check flags for path", inline=True)
comment(0x8881, "Bit7 clear: TX result = not listening", inline=True)
comment(0x8883, "Bit7 set: discard and return to listen", inline=True)
comment(0x8886, "CR1=&82: TX_RESET | RIE (switch to RX for final ACK)", inline=True)
comment(0x8888, "Write to ADLC CR1", inline=True)
comment(0x888B, "Install nmi_final_ack handler", inline=True)
comment(0x888D, "High byte of handler address", inline=True)
comment(0x888F, "Install and return via set_nmi_vector", inline=True)
comment(0x8892, "A=&01: AP mask", inline=True)
comment(0x8894, "Test SR2 AP", inline=True)
comment(0x8897, "No AP -- error", inline=True)
comment(0x8899, "Read dest station", inline=True)
comment(0x889C, "Compare to our station (workspace copy)", inline=True)
comment(0x889F, "Not our station -- error", inline=True)
comment(0x88A1, "A=&A6: low byte of nmi_final_ack_net (&88A6)", inline=True)
comment(0x88A3, "Install continuation handler", inline=True)
comment(0x88A6, "Test SR2 RDA", inline=True)
comment(0x88A9, "No RDA -- error", inline=True)
comment(0x88AB, "Read dest network", inline=True)
comment(0x88AE, "Non-zero -- network mismatch, error", inline=True)
comment(0x88B0, "Install nmi_final_ack_validate handler", inline=True)
comment(0x88B2, "Test SR1 IRQ -- more data ready?", inline=True)
comment(0x88B5, "IRQ set -- fall through to validate", inline=True)
comment(0x88B7, "Install handler", inline=True)
comment(0x88BA, "Test SR2 RDA", inline=True)
comment(0x88BD, "No RDA -- error", inline=True)
comment(0x88BF, "Read source station", inline=True)
comment(0x88C2, "Compare to TX dest station (&0D20)", inline=True)
comment(0x88C5, "Mismatch -- error", inline=True)
comment(0x88C7, "Read source network", inline=True)
comment(0x88CA, "Compare to TX dest network (&0D21)", inline=True)
comment(0x88CD, "Mismatch -- error", inline=True)
comment(0x88CF, "Load TX flags for next action", inline=True)
comment(0x88D2, "bit7 clear: no data phase", inline=True)
comment(0x88D4, "Install data RX handler", inline=True)
comment(0x88D7, "A=&02: FV mask for SR2 bit1", inline=True)
comment(0x88D9, "Test SR2 FV -- frame must be complete", inline=True)
comment(0x88DC, "No FV -- error", inline=True)
comment(0x88DE, "A=0: success result code", inline=True)
comment(0x88E0, "Always taken (A=0)", inline=True)
comment(0x88E2, "A=&41: not listening error code", inline=True)
comment(0x88E4, "Y=0: index into TX control block", inline=True)
comment(0x88E6, "Store result/error code at (nmi_tx_block),0", inline=True)
comment(0x88E8, "A=&80: TX-complete signal for tx_complete_flag", inline=True)
comment(0x88EA, "Signal TX complete", inline=True)
comment(0x88ED, "Full ADLC reset and return to idle listen", inline=True)
label(0x88F0, "rom_gap_88f0")
data_banner(0x88F0, "rom_gap_88f0",
    title="Purpose unknown. Unreferenced, unreachable.")
comment(0x8909, "Read RXCB[7] (buffer addr high byte)", inline=True)
comment(0x890B, "Compare to &FF", inline=True)
comment(0x890D, "Not &FF: normal buffer, skip Tube check", inline=True)
comment(0x8910, "Read RXCB[6] (buffer addr byte 2)", inline=True)
comment(0x8912, "Check if addr byte 2 >= &FE (Tube range)", inline=True)
comment(0x8924, "Transmit in progress?", inline=True)
comment(0x8927, "No: fallback path", inline=True)
comment(0x8929, "Load TX flags for transfer setup", inline=True)
comment(0x892C, "Set bit 1 (transfer complete)", inline=True)
comment(0x892E, "Store with bit 1 set (Tube xfer)", inline=True)
comment(0x8931, "Init borrow for 4-byte subtract", inline=True)
comment(0x8932, "Save carry on stack", inline=True)
comment(0x8933, "Y=4: start at RXCB offset 4", inline=True)
comment(0x8935, "Load RXCB[Y] (current ptr byte)", inline=True)
comment(0x8937, "Y += 4: advance to RXCB[Y+4]", inline=True)
comment(0x8938, "(continued)", inline=True)
comment(0x8939, "(continued)", inline=True)
comment(0x893A, "(continued)", inline=True)
comment(0x893B, "Restore borrow from previous byte", inline=True)
comment(0x893C, "Subtract RXCB[Y+4] (start ptr byte)", inline=True)
comment(0x893E, "Store result byte", inline=True)
comment(0x8941, "Y -= 3: next source byte", inline=True)
comment(0x8942, "(continued)", inline=True)
comment(0x8943, "(continued)", inline=True)
comment(0x8944, "Save borrow for next byte", inline=True)
comment(0x8945, "Done all 4 bytes?", inline=True)
comment(0x8947, "No: next byte pair", inline=True)
comment(0x8949, "Discard final borrow", inline=True)
comment(0x894A, "Save X", inline=True)
comment(0x894B, "Save X", inline=True)
comment(0x894C, "Compute address of RXCB+4", inline=True)
comment(0x894E, "For base pointer addition", inline=True)
comment(0x894F, "Add RXCB base to get RXCB+4 addr", inline=True)
comment(0x8951, "X = low byte of RXCB+4", inline=True)
comment(0x8952, "Y = high byte of RXCB ptr", inline=True)
comment(0x8954, "Tube claim type &C2", inline=True)
comment(0x8956, "Claim Tube transfer address", inline=True)
comment(0x8959, "No Tube: skip reclaim", inline=True)
comment(0x895B, "Tube: reclaim with scout status", inline=True)
comment(0x895E, "Reclaim with scout status type", inline=True)
comment(0x8961, "Release Tube claim after reclaim", inline=True)
comment(0x8964, "C=1: Tube address claimed", inline=True)
comment(0x8965, "Restore X", inline=True)
comment(0x8966, "Restore X from stack", inline=True)
comment(0x8967, "Return with C = transfer status", inline=True)
comment(0x8968, "Y=4: RXCB current pointer offset", inline=True)
comment(0x896A, "Load RXCB[4] (current ptr lo)", inline=True)
comment(0x896C, "Y=8: RXCB start address offset", inline=True)
comment(0x896E, "Set carry for subtraction", inline=True)
comment(0x896F, "Subtract RXCB[8] (start ptr lo)", inline=True)
comment(0x8971, "Store transfer size lo", inline=True)
comment(0x8973, "Y=5: current ptr hi offset", inline=True)
comment(0x8975, "Load RXCB[5] (current ptr hi)", inline=True)
comment(0x8977, "Propagate borrow only", inline=True)
comment(0x8979, "Temp store of adjusted hi byte", inline=True)
comment(0x897B, "Y=8: start address lo offset", inline=True)
comment(0x897D, "Copy RXCB[8] to open port buffer lo", inline=True)
comment(0x897F, "Store to scratch (side effect)", inline=True)
comment(0x8981, "Y=9: start address hi offset", inline=True)
comment(0x8983, "Load RXCB[9]", inline=True)
comment(0x8985, "Set carry for subtraction", inline=True)
comment(0x8986, "Subtract adjusted hi byte", inline=True)
comment(0x8988, "Store transfer size hi", inline=True)
comment(0x898A, "Return with C=1", inline=True)
comment(0x898B, "Return with C=1 (success)", inline=True)
comment(0x898C, "CR1=&C1: TX_RESET | RX_RESET | AC (both sections in reset, address control set)", inline=True)
comment(0x898E, "Write CR1 to ADLC register 0", inline=True)
comment(0x8991, "CR4=&1E (via AC=1): 8-bit RX word length, abort extend enabled, NRZ encoding", inline=True)
comment(0x8993, "Write CR4 to ADLC register 3", inline=True)
comment(0x8996, "CR3=&00 (via AC=1): no loop-back, no AEX, NRZ, no DTR", inline=True)
comment(0x8998, "Write CR3 to ADLC register 1", inline=True)
comment(0x899B, "CR1=&82: TX_RESET | RIE (TX in reset, RX interrupts enabled)", inline=True)
comment(0x899D, "Write to ADLC CR1", inline=True)
comment(0x89A0, "CR2=&67: CLR_TX_ST | CLR_RX_ST | FC_TDRA | 2_1_BYTE | PSE", inline=True)
comment(0x89A2, "Write to ADLC CR2", inline=True)
comment(0x89A5, "Return; ADLC now in RX listen mode", inline=True)
comment(0x89A6, "Check if Econet has been initialised", inline=True)
comment(0x89A9, "Not initialised: skip to RX listen", inline=True)
comment(0x89AB, "Read current NMI handler low byte", inline=True)
comment(0x89AE, "Expected: &B3 (nmi_rx_scout low)", inline=True)
comment(0x89B0, "Not idle: spin and wait", inline=True)
comment(0x89B2, "Read current NMI handler high byte", inline=True)
comment(0x89B5, "Test if high byte = &80 (page of nmi_rx_scout)", inline=True)
comment(0x89B7, "Not idle: spin and wait", inline=True)
comment(0x89B9, "INTOFF: disable NMIs", inline=True)
comment(0x89BC, "INTOFF again (belt-and-braces)", inline=True)
comment(0x89BF, "TX not in progress", inline=True)
comment(0x89C2, "Econet not initialised", inline=True)
comment(0x89C5, "Y=5: service call workspace page", inline=True)
comment(0x89C7, "Set ADLC to RX listen mode", inline=True)
comment(0x89CA, "INTOFF: force /NMI high (IC97 flip-flop clear)", inline=True)
comment(0x89CD, "Save A", inline=True)
comment(0x89CE, "Transfer Y to A", inline=True)
comment(0x89CF, "Save Y (via A)", inline=True)
comment(0x89D0, "ROM bank 0 (patched during init for actual bank)", inline=True)
comment(0x89D2, "Select Econet ROM bank via ROMSEL", inline=True)
comment(0x89D5, "Jump to scout handler in ROM", inline=True)
comment(0x89D8, "Store handler high byte at &0D0D", inline=True)
comment(0x89DB, "Store handler low byte at &0D0C", inline=True)
comment(0x89DE, "Restore NFS ROM bank", inline=True)
comment(0x89E0, "Page in via hardware latch", inline=True)
comment(0x89E3, "Restore Y from stack", inline=True)
comment(0x89E4, "Transfer ROM bank to Y", inline=True)
comment(0x89E5, "Restore A from stack", inline=True)
comment(0x89E6, "INTON: guaranteed /NMI edge if ADLC IRQ asserted", inline=True)
comment(0x89E9, "Return from interrupt", inline=True)

# Dead data between rom_set_nmi_vector RTI and svc_dispatch_lo.
# The NMI shim copy (Y=1..&20) ends at &89C6; these 3 bytes at
# &89BD-&89BF are outside the copy range and unreferenced.

# Inline comments: service/infrastructure layer (&8A0B-&9130)
comment(0x8A5A, "OSBYTE 0: read OS version", inline=True)
comment(0x8A5C, "X=1 to request version number", inline=True)
comment(0x8A61, "OS 3.2/3.5 (Master 128)?", inline=True)
comment(0x8A63, "Yes: target OS, skip Bad ROM message", inline=True)
comment(0x8A65, "OS 4.0 (Master Econet Terminal)?", inline=True)
comment(0x8A67, "Yes: target OS, skip Bad ROM message", inline=True)
comment(0x8A69, "Transfer OS version to A", inline=True)
comment(0x8A6A, "Save flags (Z set if OS 1.00) across print", inline=True)
comment(0x8A6B, "Print '<CR>Bad ROM ' to mark non-Master OS", inline=True)
comment(0x8A77, "Load this ROM's slot number", inline=True)
comment(0x8A79, "Print slot number as decimal", inline=True)
comment(0x8A7C, "Print trailing newline, bypassing *SPOOL", inline=True)
comment(0x8A7F, "Reload ROM slot for workspace clearing", inline=True)
comment(0x8A81, "Restore flags", inline=True)
comment(0x8A82, "OS 1.00: skip INX (table starts at slot 0)", inline=True)
comment(0x8A84, "Adjust index for OS 1.20/2.00/5.00 layout", inline=True)
comment(0x8A85, "A=0", inline=True)
comment(0x8A87, "Clear workspace byte for this ROM", inline=True)
comment(0x8A54, "Save service call number", inline=True)
comment(0x8A55, "Service call &0F (vectors claimed)?", inline=True)
comment(0x8A57, "No: skip vectors-claimed handling", inline=True)
comment(0x8A8A, "Restore ROM slot to X", inline=True)
comment(0x8A8D, "Pop service call number into A", inline=True)
comment(0x8A8E, "Re-save service call number", inline=True)

# svc_18_fs_select inline comments (4 items)
comment(0x8B45, "Service 18 carries FS number in Y; Econet is FS 5", inline=True)
comment(0x8B47, "Not us: pass the call on (RTS via shared return)", inline=True)
comment(0x8B49, "A=0 to claim the service", inline=True)
comment(0x8B4B, "Clear svc_state and fall into ensure_fs_selected", inline=True)

# osbyte_x0 inline comment (1 item)
comment(0x8ECB, "Y=&FF: 'read' parameter for OSBYTE", inline=True)
comment(0x8ECD, "Tail-call OSBYTE", inline=True)
comment(0x8EC9, "X=0 then fall through into osbyte_yff", inline=True)

# is_decimal_digit inline comments (4 items)
comment(0x939A, "Hex prefix '&'?", inline=True)
comment(0x939C, "Yes: treat as digit-like (carry set on exit)", inline=True)
comment(0x939E, "Network/station separator '.'?", inline=True)
comment(0x93A0, "Yes: also digit-like; else fall through to decimal test",
        inline=True)

# is_dec_digit_only inline comments (6 items)
comment(0x93A2, "Above '9'? (CMP #':')", inline=True)
comment(0x93A4, "Yes: not a digit -- jump to clear-carry exit", inline=True)
comment(0x93A6, "Below '0'? (CMP sets carry if A >= '0')", inline=True)
comment(0x93A8, "Carry now reflects '0'-'9' membership; return", inline=True)
comment(0x93A9, "Out-of-range exit: clear carry to signal not-a-digit",
        inline=True)
comment(0x93AA, "Return", inline=True)

# get_access_bits inline comments (5 items)
comment(0x93AB, "Y=&0E: directory entry access byte offset", inline=True)
comment(0x93AD, "Read access byte through fs_options pointer", inline=True)
comment(0x93AF, "Mask to 6 protection bits (clears the unused top two)",
        inline=True)
comment(0x93B1, "X=4: encode-table column index for owner-access bits",
        inline=True)
comment(0x93B3, "Always taken: LDX #4 cleared Z, so BNE is "
        "unconditional", inline=True)

# get_prot_bits / begin_prot_encode inline comments (10 items)
comment(0x93B5, "Mask to 5 protection bits (low 5)", inline=True)
comment(0x93B7, "X=&FF; INX inside the loop bumps to 0 for column 0",
        inline=True)
comment(0x93B9, "Park source bits in fs_error_ptr -- the LSR target",
        inline=True)
comment(0x93BB, "A=0: accumulator for encoded result", inline=True)
comment(0x93BD, "Advance table column index", inline=True)
comment(0x93BE, "Shift next source bit into carry", inline=True)
comment(0x93C0, "Source bit was 0: skip the OR for this column", inline=True)
comment(0x93C2, "Source bit was 1: OR in this column's encoded mask",
        inline=True)
comment(0x93C5, "Continue while either fs_error_ptr or A is non-zero "
        "(loop ends when source exhausted and result still 0)", inline=True)
comment(0x93C7, "Return with encoded value in A", inline=True)

# set_text_and_xfer_ptr inline comments (2 items)
comment(0x93D3, "Save text pointer low byte (where caller wants OS to "
        "scan from)", inline=True)
comment(0x93D5, "Save text pointer high byte; fall through to "
        "set_xfer_params", inline=True)

# set_xfer_params inline comments (3 items)
comment(0x93D7, "Stash transfer byte count (in A)", inline=True)
comment(0x93D9, "Source pointer low byte", inline=True)
comment(0x93DB, "Source pointer high byte; fall through to set_options_ptr",
        inline=True)

# set_options_ptr / clear_escapable inline comments (4 items shared)
comment(0x93DD, "Options pointer low byte (parameter block base)",
        inline=True)
comment(0x93DF, "Options pointer high byte; fall through to clear_escapable",
        inline=True)
comment(0x93E1, "Save flags so the LSR doesn't disturb caller's NZC",
        inline=True)
comment(0x93E2, "Shift bit 0 of need_release_tube into carry, clearing "
        "the bit", inline=True)
comment(0x93E4, "Restore caller's flags", inline=True)
comment(0x93E5, "Return", inline=True)

# cmp_5byte_handle inline comments (7 items)
comment(0x93E6, "X=4: loop from offset 4 down to 1 (skips offset 0)",
        inline=True)
comment(0x93E8, "Load saved-handle byte from addr_work[X]", inline=True)
comment(0x93EA, "EOR with parsed handle byte; Z set iff bytes match",
        inline=True)
comment(0x93EC, "Mismatch: bail out with Z clear", inline=True)
comment(0x93EE, "Decrement to next byte", inline=True)
comment(0x93EF, "Loop while X != 0 (offset 0 is intentionally not "
        "compared)", inline=True)
comment(0x93F1, "Return; Z reflects last EOR (set = match, clear = "
        "mismatch)", inline=True)

# get_pb_ptr_as_index inline comments (1 item)
comment(0xA3E7, "Read PB[0] (the OSWORD sub-function code in most calls); "
        "fall into byte_to_2bit_index", inline=True)

# push_osword_handler_addr inline comments (6 items)
comment(0xAD15, "Load handler high byte from hi-table column X", inline=True)
comment(0xAD18, "Push for the eventual RTS dispatch", inline=True)
comment(0xAD19, "Load handler low byte from lo-table column X", inline=True)
comment(0xAD1C, "Push lo so RTS pulls (lo, hi)+1 -> handler entry",
        inline=True)
comment(0xAD1D, "Reload original OSWORD number into A for the handler",
        inline=True)
comment(0xAD1F, "RTS jumps to handler with A=OSWORD number", inline=True)

# match_rx_code inline comments (5 items, including loop)
comment(0xADB8, "Compare A with table entry at index X", inline=True)
comment(0xADBB, "Match: return with Z set", inline=True)
comment(0xADBD, "Step to next earlier table entry", inline=True)
comment(0xADBE, "Loop while X >= 0 (table walked top-down)", inline=True)
comment(0xADC0, "Return; Z reflects last CMP", inline=True)

# init_ws_copy_wide inline comments (4 items)
comment(0xADFE, "X=&0D: 14 template bytes to process", inline=True)
comment(0xAE00, "Y=&7C: workspace destination offset for wide variant",
        inline=True)
comment(0xAE02, "BIT &FF unconditionally sets V (the always_set_v_byte "
        "trick)", inline=True)
comment(0xAE05, "V=1 always: skip the narrow-mode prologue and CLV",
        inline=True)

# init_ws_copy_narrow inline comments (2 items)
comment(0xAE07, "Y=&17: workspace destination offset for narrow variant",
        inline=True)
comment(0xAE09, "X=&1A: 27 template bytes to process; fall into "
        "ws_copy_vclr_entry which CLVs", inline=True)

# ws_copy_vclr_entry / loop_copy_ws_template inline comments (16 items)
comment(0xAE0B, "Clear V: narrow mode (writes via nfs_workspace pointer)",
        inline=True)
comment(0xAE0C, "Read next template byte", inline=True)
comment(0xAE0F, "&FE: end-of-template marker?", inline=True)
comment(0xAE11, "Yes: finalise and return", inline=True)
comment(0xAE13, "&FD: skip-this-offset marker?", inline=True)
comment(0xAE15, "Yes: advance index without storing", inline=True)
comment(0xAE17, "&FC: substitute-workspace-page-pointer marker?",
        inline=True)
comment(0xAE19, "No special marker: store this byte verbatim", inline=True)
comment(0xAE1B, "Wide path: page pointer is net_rx_ptr's high byte",
        inline=True)
comment(0xAE1D, "V=1 (wide): keep the rx_ptr high byte", inline=True)
comment(0xAE1F, "V=0 (narrow): use nfs_workspace high byte instead",
        inline=True)
comment(0xAE21, "Stash whichever page byte we picked into net_tx_ptr_hi",
        inline=True)
comment(0xAE23, "V=1 (wide): store via net_rx_ptr,Y", inline=True)
comment(0xAE25, "V=0 (narrow): store via nfs_workspace,Y", inline=True)
comment(0xAE27, "Always branch: V is still clear here", inline=True)
comment(0xAE29, "Wide-mode store via net_rx_ptr", inline=True)
comment(0xAE2B, "Step Y down (workspace offset)", inline=True)
comment(0xAE2C, "Step X down (template index)", inline=True)
comment(0xAE2D, "Loop while X >= 0", inline=True)
comment(0xAE2F, "Bump Y back to first written offset", inline=True)
comment(0xAE30, "Save it as net_tx_ptr low for the caller", inline=True)
comment(0xAE32, "Return", inline=True)

# print_10_chars / print_chars_from_buf inline comments
comment(0xB21A, "Y=10: ten characters to print (fixed-width field)",
        inline=True)
comment(0xB21C, "Read next character from reply buffer at offset X",
        inline=True)
comment(0xB21F, "Print via OSASCI, bypassing the *SPOOL file", inline=True)
comment(0xB222, "Step buffer offset", inline=True)
comment(0xB223, "Step character counter", inline=True)
comment(0xB224, "Loop until Y=0", inline=True)
comment(0xB226, "Return; X points just past the last printed byte",
        inline=True)

# parse_cmd_arg_y0 inline comment (1 item)
comment(0xB22A, "Y=0: scan from start of command line", inline=True)

# strip_token_prefix inline comments (16 items)
comment(0xB251, "Save caller's X (TX buffer offset)", inline=True)
comment(0xB252, "Push it", inline=True)
comment(0xB253, "X=&FF: INX in loop bumps to 0 for first byte", inline=True)
comment(0xB255, "Step to next byte position", inline=True)
comment(0xB256, "Read byte X+1 (the next character)", inline=True)
comment(0xB259, "Store it back at byte X (shifting left by one)",
        inline=True)
comment(0xB25C, "EOR with CR; Z set if we just shifted the terminator",
        inline=True)
comment(0xB25E, "More to shift: continue", inline=True)
comment(0xB260, "X is now the buffer length (excluding CR)", inline=True)
comment(0xB261, "Empty after shift: skip trim, restore X, return",
        inline=True)
comment(0xB263, "Read last buffer byte (X-1 because we count from 0)",
        inline=True)
comment(0xB266, "EOR with space; Z set iff it's a trailing space",
        inline=True)
comment(0xB268, "Not a space: trim done, restore X, return", inline=True)
comment(0xB26A, "It is a space: replace with CR (truncate the string)",
        inline=True)
comment(0xB26C, "Store CR at the now-trimmed position", inline=True)
comment(0xB26F, "Step backwards", inline=True)
comment(0xB270, "Loop while X > 0", inline=True)
comment(0xB272, "Restore caller's TX buffer offset", inline=True)
comment(0xB273, "Transfer back to X", inline=True)
comment(0xB274, "Return", inline=True)

# copy_arg_to_buf_x0 inline comment (1 item)
comment(0xB29F, "X=0: place the argument at the start of the TX buffer; "
        "fall into copy_arg_to_buf", inline=True)

# get_ws_page: complete the existing partial annotation
comment(0x8CAF, "Load workspace page byte for this ROM slot",
    inline=True)
comment(0x8CAD, "Y = current ROM slot number from MOS copy at &F4",
        inline=True)
comment(0x8CB2, "Hold a copy of the slot byte in Y while we test bit 6",
        inline=True)
comment(0x8CB3, "ROL puts pre-ROL bit 6 into the post-ROL N flag (and "
        "pre-ROL bit 7 into C)", inline=True)
comment(0x8CB4, "Save those flags so the upcoming ROR doesn't lose N",
        inline=True)
comment(0x8CB5, "ROR restores A to its original value (using the saved "
        "C)", inline=True)
comment(0x8CB6, "Restore the ROL flags: N is now pre-ROL bit 6", inline=True)
comment(0x8CB7, "Bit 6 clear: skip the OR (no ADLC-absent flag)",
        inline=True)
comment(0x8CB9, "Bit 6 set: re-set bit 7 in the returned page byte (the "
        "ADLC-absent flag uses bit 7 in callers)", inline=True)

# mask_owner_access inline comments (4 items)
comment(0xB2CF, "Read fs_lib_flags (now at &C271 in 4.21)", inline=True)
comment(0xB2D2, "Keep only the 5-bit owner access mask", inline=True)
comment(0xB2D4, "Store back, clearing FS-selection and other high bits",
        inline=True)
comment(0xB2D7, "Return", inline=True)

# prompt_yn inline comments (3 items)
comment(0xB7CB, "Print 'Y/N) ' via the inline-string helper", inline=True)
comment(0xB7CE, "Inline string body — bytes consumed by print_inline_no_spool (above)",
        inline=True)
# &B7D1 is mid-inline-string; the 4.18 'Force lower-case' (AND #&20)
# instruction lived at this address but no longer exists in 4.21.


# close_ws_file inline comments (3 items)
comment(0xBF71, "Y = saved file handle from ws_page", inline=True)
comment(0xBF73, "A=0: OSFIND close", inline=True)
comment(0xBF75, "Tail-call OSFIND to close the handle", inline=True)

# advance_x_by_8 / advance_x_by_4 / inx4 inline comments
comment(0xBFBA, "First INX-by-4 via JSR; falls into advance_x_by_4 for "
        "the second four", inline=True)
comment(0xBFBD, "JSR inx4 (4 INX); RTS returns here, then falls into "
        "inx4 again for the implicit second four", inline=True)
comment(0xBFC1, "(continued)", inline=True)
comment(0xBFC2, "(continued)", inline=True)
comment(0xBFC3, "(continued)", inline=True)
comment(0xBFC4, "Return; caller is either an explicit JSR (so X has "
        "advanced by 4) or advance_x_by_8's fall-through (so X has "
        "advanced by 8 total)", inline=True)

# copy_arg_to_buf inline comment (1 item)
comment(0xB2A1, "Y=0: scan from start of command line (CLC entry skips "
        "'&' validation)", inline=True)

# copy_arg_validated inline comments (15 items in body)
comment(0xB2A3, "Set C: this entry validates against '&'", inline=True)
comment(0xB2A4, "Read next source byte through fs_crc_lo pointer",
        inline=True)
comment(0xB2A6, "Store into TX buffer at offset X", inline=True)
comment(0xB2A9, "Validation off (C clear): just advance positions",
        inline=True)
comment(0xB2AB, "Test against '!' to bias the EOR comparison", inline=True)
comment(0xB2AD, "EOR with '&'; Z set iff source byte was '&'", inline=True)
comment(0xB2AF, "'&' inside the argument is illegal: raise 'Bad filename'",
        inline=True)
comment(0xB2B1, "Restore A by undoing the EOR (so the loop terminator "
        "test below sees the original byte)", inline=True)
comment(0xB2B3, "Advance TX buffer offset", inline=True)
comment(0xB2B4, "Advance command-line offset", inline=True)
comment(0xB2B5, "EOR with CR; Z set iff we just stored the terminator",
        inline=True)
comment(0xB2B7, "More to copy: continue", inline=True)
# Trailing-space trim (4.21 addition)
comment(0xB2B9, "Look at the byte just before the CR we stopped on",
        inline=True)
comment(0xB2BC, "EOR with space; Z set iff that byte was a trailing space",
        inline=True)
comment(0xB2BE, "Not a space: trim done", inline=True)
comment(0xB2C0, "Step back over the space", inline=True)
comment(0xB2C1, "A=&0D: replace the trailing space with CR", inline=True)
comment(0xB2C3, "Store CR at the now-truncated end", inline=True)
comment(0xB2C6, "Always taken (A=&0D from LDA #&0D so Z is clear); look "
        "at the next byte back", inline=True)
comment(0xB2C8, "All trailing spaces consumed (or none present)",
        inline=True)
comment(0xB2CA, "Return", inline=True)

# copy_ps_data_y1c inline comment (1 item)
comment(0xB3D5, "Y=&18: standard offset for the PS template; fall into "
        "copy_ps_data", inline=True)

# load_ps_server_addr inline comments (6 items)
comment(0xB4A8, "Y=2: workspace offset of PS station byte", inline=True)
comment(0xB4AA, "Read station byte", inline=True)
comment(0xB4AC, "Stash in fs_work_5 (PS station)", inline=True)
comment(0xB4AE, "Y=3: workspace offset of PS network byte", inline=True)
comment(0xB4AF, "Read network byte", inline=True)
comment(0xB4B1, "Stash in fs_work_6 (PS network)", inline=True)

# write_ps_slot_byte_ff inline comments (4 items)
comment(0xB51C, "Step Y to next workspace slot byte", inline=True)
comment(0xB51D, "Load buffer page byte from addr_work", inline=True)
comment(0xB51F, "Write at offset Y", inline=True)
comment(0xB521, "A=&FF: sentinel; fall into write_two_bytes_inc_y to "
        "store two of them", inline=True)

# write_two_bytes_inc_y inline comments (5 items)
comment(0xB523, "Step Y to next destination", inline=True)
comment(0xB524, "Write A at workspace offset Y", inline=True)
comment(0xB526, "Step Y again", inline=True)
comment(0xB527, "Write A at the next offset (two consecutive copies)",
        inline=True)
comment(0xB529, "Final INY leaves Y pointing past the second write",
        inline=True)

# reverse_ps_name_to_tx inline comments (16 items)
comment(0xB52B, "Y=&18: source offset (start of PS name in RX buffer)",
        inline=True)
comment(0xB52D, "Read RX byte at offset Y", inline=True)
comment(0xB52F, "Push it (the stack reverses the order)", inline=True)
comment(0xB530, "Step source", inline=True)
comment(0xB531, "Reached &20 (one past the 8-byte name)?", inline=True)
comment(0xB533, "No: continue pushing", inline=True)
comment(0xB535, "Y=&17: destination offset for the reversed name",
        inline=True)
comment(0xB537, "Pull next pushed byte (LIFO -> reversed order)",
        inline=True)
comment(0xB538, "Store at destination offset Y", inline=True)
comment(0xB53A, "Step destination back", inline=True)
comment(0xB53B, "Reached &0F (one before the destination range)?",
        inline=True)
comment(0xB53D, "No: continue popping", inline=True)
comment(0xB53F, "Copy net_rx_ptr_hi as the TX page (TX shares the same "
        "page as RX for this packet)", inline=True)
comment(0xB541, "Set net_tx_ptr_hi", inline=True)
comment(0xB543, "TX low byte = &0C: skip past the TX header to where "
        "the reversed name lives", inline=True)
comment(0xB545, "Set net_tx_ptr lo", inline=True)
comment(0xB547, "Y=3: copy 4-byte TX header (offsets 3..0)", inline=True)
comment(0xB549, "Read template byte", inline=True)
comment(0xB54C, "Write to TX buffer at offset Y", inline=True)
comment(0xB54E, "Step backwards", inline=True)
comment(0xB54F, "Loop while Y >= 0", inline=True)
comment(0xB551, "Return", inline=True)

# save_net_tx_cb inline comment (1 item)
comment(0x978A, "Clear V: standard send mode (callers set V via "
        "save_net_tx_cb_vset for the lib-flag variant)", inline=True)

# save_net_tx_cb_vset inline comments (15 items, including shared body)
comment(0x978B, "Read FS station from &C002 (saved from selection time)",
        inline=True)
comment(0x978E, "Copy into TX buffer at &C102 (dest station for header)",
        inline=True)
comment(0x9791, "Clear C: caller wants four-way handshake (not "
        "disconnect)", inline=True)
comment(0x9792, "Save flags so we can keep V across the loop", inline=True)
comment(0x9793, "Save Y -- the entry function code -- into TX[1]",
        inline=True)
comment(0x9796, "Y=1: copy 2 bytes (network/control) starting at index 1",
        inline=True)
comment(0x9798, "Read source byte at &C003+Y", inline=True)
comment(0x979B, "Write to TX buffer at &C103+Y", inline=True)
comment(0x979E, "Step backwards", inline=True)
comment(0x979F, "Loop while Y >= 0 (covers indices 1, 0)", inline=True)
comment(0x97A1, "Test fs_lib_flags: bit 6 = use library, bit 7 = "
        "*-prefix-stripped", inline=True)
comment(0x97A4, "V (bit 6) set: use the library station instead",
        inline=True)
comment(0x97A6, "Neither bit set: leave the FS station copy intact",
        inline=True)
comment(0x97A8, "Bit 7 (FS-prefix) set: substitute the saved-prefix "
        "station from &C004", inline=True)
comment(0x97AB, "Override TX[3]'s station byte", inline=True)
comment(0x97AE, "Always taken: V was clear when we entered (BVS at "
        "&97A4 didn't fire)", inline=True)
comment(0x97B0, "use_lib_station: substitute the library station from "
        "&C002 (the original FS station, but bit 6 of fs_lib_flags "
        "redirects via lib path)", inline=True)
comment(0x97B3, "Override TX[3] with the library station byte",
        inline=True)
comment(0x97B6, "Restore the saved flags (V/C control downstream "
        "init_txcb behaviour)", inline=True)

# wait_net_tx_ack inline comments (28 items in body)
comment(0x98BE, "Read the configurable rx-wait timeout (&0D6E, default "
        "&28 = ~22s on 2 MHz)", inline=True)
comment(0x98C1, "Push it as the outermost counter (read back via "
        "stack-X indexing later)", inline=True)
comment(0x98C2, "Read econet_flags so we can preserve it across the wait",
        inline=True)
comment(0x98C5, "Push it (we'll temporarily set bit 7 to mark waiting)",
        inline=True)
comment(0x98C6, "Check whether net_tx_ptr_hi is non-zero (TX in flight?)",
        inline=True)
comment(0x98C8, "Yes: skip the flag-set; counters initialise either way",
        inline=True)
comment(0x98CA, "TX idle: set bit 7 of econet_flags (signal RX-only wait)",
        inline=True)
comment(0x98CC, "Write the modified flags back", inline=True)
comment(0x98CF, "A=0: initial value for inner+middle counters", inline=True)
comment(0x98D1, "Push it -- middle counter at stack[X+2]", inline=True)
comment(0x98D2, "Push it again -- inner counter at stack[X+1]",
        inline=True)
comment(0x98D3, "Y=0: indirect index for net_tx_ptr poll", inline=True)
comment(0x98D4, "Capture S into X so we can address the stack counters",
        inline=True)
comment(0x98D5, "Read RX/TX flags through net_tx_ptr -- bit 7 set means "
        "complete", inline=True)
comment(0x98D7, "Bit 7 set: reply received, exit poll", inline=True)
comment(0x98D9, "Decrement inner counter at stack[X+1]", inline=True)
comment(0x98DC, "Inner not zero yet: poll again", inline=True)
comment(0x98DE, "Inner wrapped: decrement middle at stack[X+2]",
        inline=True)
comment(0x98E1, "Middle not zero: poll again", inline=True)
comment(0x98E3, "Middle wrapped: decrement outer at stack[X+4] (the "
        "saved timeout value)", inline=True)
comment(0x98E6, "Outer not zero: poll again", inline=True)
comment(0x98E8, "Reload the original timeout to test for timeout=0 mode",
        inline=True)
comment(0x98EB, "Configured timeout was non-zero: declare timeout",
        inline=True)
comment(0x98ED, "Timeout=0 (poll forever): check escape flag", inline=True)
comment(0x98EF, "Escape pressed: jump to escape handler at &9895",
        inline=True)
comment(0x98F1, "Reset outer counter so we keep polling", inline=True)
comment(0x98F4, "Always taken (INC's result is always non-zero here): "
        "back to inner", inline=True)
comment(0x98F6, "done_poll_tx: discard inner counter", inline=True)
comment(0x98F7, "Discard middle counter", inline=True)
comment(0x98F8, "Pull saved econet_flags", inline=True)
comment(0x98F9, "Restore them (clearing bit 7 if we set it)", inline=True)
comment(0x98FC, "Pull saved rx_wait_timeout into A", inline=True)
comment(0x98FD, "If timeout reached zero, raise 'No reply'", inline=True)
comment(0x98FF, "Reply received normally: return", inline=True)

# set_conn_active inline comments (11 items)
comment(0x93F7, "Save flags so the rest of the routine is transparent",
        inline=True)
comment(0x93F8, "Save A (the attribute byte we need to recover via stack)",
        inline=True)
comment(0x93F9, "Save X", inline=True)
comment(0x93FA, "Capture S into X to address stack from below",
        inline=True)
comment(0x93FB, "Re-read the original A from stack[X+2] (above PHX/PHA)",
        inline=True)
comment(0x93FE, "Convert attribute byte to channel-table index", inline=True)
comment(0x9401, "No matching channel: skip the flag set, just restore",
        inline=True)
comment(0x9403, "A=&40: bit 6 = connection-active mask", inline=True)
comment(0x9405, "OR with current status byte for this channel",
        inline=True)
comment(0x9408, "Write back the updated status", inline=True)
comment(0x940B, "Always taken (A is non-zero after the OR with &40); "
        "join shared exit", inline=True)

# clear_conn_active inline comments (8 body items, shares clear_channel_flag exit)
comment(0x940D, "Save flags", inline=True)
comment(0x940E, "Save A", inline=True)
comment(0x940F, "Save X", inline=True)
comment(0x9410, "Capture S into X for stack-relative reads", inline=True)
comment(0x9411, "Re-read the attribute byte from stack[X+2]", inline=True)
comment(0x9414, "Convert attribute to channel index", inline=True)
comment(0x9417, "No matching channel: just restore", inline=True)
comment(0x9419, "A=&BF: bit 6 clear mask", inline=True)
comment(0x941E, "Write back the updated status", inline=True)

# Shared exit at clear_channel_flag (4 items)
comment(0x9421, "Restore X (saved at PHX)", inline=True)
comment(0x9422, "Restore A", inline=True)
comment(0x9423, "Restore flags", inline=True)
comment(0x9424, "Return; A and X preserved across the call", inline=True)

# prep_send_tx_cb inline comments (12 items)
comment(0x97B7, "Save flags so C survives the init_txcb call", inline=True)
comment(0x97B8, "Reply port = &90 (FS reply port)", inline=True)
comment(0x97BA, "Stash port in TXCB[0]", inline=True)
comment(0x97BD, "Build the rest of the TXCB (control, dest stn/net, "
        "etc.)", inline=True)
comment(0x97C0, "Move TX-buffer end pointer (returned in X) into A",
        inline=True)
comment(0x97C1, "Add 5 bytes of slack for trailing reply data", inline=True)
comment(0x97C3, "Stash the resulting end-of-buffer offset", inline=True)
comment(0x97C5, "Restore the original C flag from caller", inline=True)
comment(0x97C6, "C set: this is a disconnect; jump to handle_disconnect",
        inline=True)
comment(0x97C8, "Save flags again across the actual TX (TX clobbers them)",
        inline=True)
comment(0x97C9, "Send the four-way-handshake-initiated command packet",
        inline=True)
comment(0x97CC, "Restore caller's flags before falling into "
        "recv_and_process_reply", inline=True)

# parse_access_prefix inline comments (15 items)
comment(0xB22F, "Read first parsed-buffer character (the candidate prefix)",
        inline=True)
comment(0xB232, "EOR with '&'; Z set iff the byte was '&'", inline=True)
comment(0xB234, "Not '&': try ':' (and '#') instead", inline=True)
comment(0xB236, "Read fs_lib_flags", inline=True)
comment(0xB239, "Set bit 6 (URD-relative resolution flag)", inline=True)
comment(0xB23B, "Write back updated flags", inline=True)
comment(0xB23E, "Strip the '&' from the buffer (shift left + trim)",
        inline=True)
comment(0xB241, "Step caller's X back to account for the consumed "
        "character", inline=True)
comment(0xB242, "Re-read the (now first) buffer byte after the strip",
        inline=True)
comment(0xB245, "EOR with '.'; Z set iff '&.' pair (URD root)", inline=True)
comment(0xB247, "Not '&.': just '&' alone -- check for trailing '#'",
        inline=True)
comment(0xB249, "It was '&.': peek the byte after the dot", inline=True)
comment(0xB24C, "EOR with CR; Z set iff '&.<CR>' (illegal: dot needs a "
        "name to follow)", inline=True)
comment(0xB24E, "'&.<CR>' is invalid: raise 'Bad filename'", inline=True)
comment(0xB250, "Valid '&.<name>': step X back for the dot too", inline=True)

# print_file_server_is inline comments (3 items)
comment(0xB483, "Print 'File' via inline string", inline=True)
comment(0xB48A, "Clear V so the BVC below is taken", inline=True)
comment(0xB48B, "Always taken (V was just cleared); skip the 'Printer' "
        "prologue and reach the shared ' server is ' suffix",
        inline=True)

# print_printer_server_is inline comments (3 items)
comment(0xB48D, "Print 'Printer' via inline string", inline=True)
# 0xB497 is the inline-string terminator NOP that print_inline jumps
# back to; it consumes 1 cycle and then falls into the suffix
comment(0xB497, "NOP -- bit-7 terminator + harmless resume opcode",
        inline=True)

# print_server_is_suffix inline comments (3 items)
comment(0xB498, "Print ' server is ' via inline string", inline=True)
comment(0xB4A6, "NOP -- bit-7 terminator + harmless resume opcode", inline=True)
comment(0xB4A7, "Return; caller now prints the actual server "
        "(file or printer) address", inline=True)

# print_hex_and_space inline comments (5 items)
comment(0xBE37, "Save A so the caller can re-use the value", inline=True)
comment(0xBE38, "Print A as two hex digits", inline=True)
comment(0xBE3B, "A=' ': trailing column separator", inline=True)
comment(0xBE3D, "Print the space via OSASCI", inline=True)
comment(0xBE40, "Restore caller's A", inline=True)
comment(0xBE41, "Return", inline=True)

# print_fs_info_newline inline comments (3 items)
comment(0xA3BB, "Set V so print_station_addr suppresses the leading "
        "'0.' when the network number is zero", inline=True)
comment(0xA3BE, "Print the station/network address", inline=True)
comment(0xA3C1, "Tail-call OSNEWL for the trailing CR/LF", inline=True)

# parse_filename_arg inline comment (1 item)
comment(0xB22C, "Read the GSREAD-style filename argument into the "
        "&C030 buffer, then fall into parse_access_prefix",
        inline=True)

# print_station_addr inline comments (12 items)
comment(0xB556, "Save caller's V (controls leading-zero padding via the "
        "BVS at &B566)", inline=True)
comment(0xB557, "Read network number (fs_work_6)", inline=True)
comment(0xB559, "Network 0 means local: skip the 'NN.' prefix", inline=True)
comment(0xB55B, "Network non-zero: print as 3-digit decimal", inline=True)
comment(0xB55E, "A='.': separator between network and station",
        inline=True)
comment(0xB560, "Print the dot", inline=True)
comment(0xB563, "Set V so the next BVS branches over the padding "
        "(we just printed digits, no padding needed)", inline=True)
comment(0xB566, "V set: skip leading-space padding", inline=True)
comment(0xB568, "V clear (caller wanted padding): print 4 leading spaces "
        "via inline string", inline=True)
comment(0xB56F, "Read station number (fs_work_5)", inline=True)
comment(0xB571, "Restore caller's V (so print_decimal_3dig honours its "
        "own leading-zero suppression)", inline=True)
comment(0xB572, "Tail-call print_decimal_3dig for the station number",
        inline=True)

# print_version_header inline comments (3 items)
# 0x8C93 already has 'Print version string via inline' inline comment
comment(0x8CA9, "NOP -- bit-7 terminator + harmless resume opcode",
        inline=True)
comment(0x8CAA, "Tail-call print_station_id to append ' Econet "
        "Station <n>' (and ' No Clock' if appropriate)", inline=True)

# ex_print_col_sep inline comments (8 items in body)
comment(0xB2E4, "Read fs_spool_handle (also column counter in *Cat mode)",
        inline=True)
comment(0xB2E6, "Negative: *Ex mode (one-per-line) -- skip column logic, "
        "just print newline", inline=True)
comment(0xB2E8, "Bump column counter", inline=True)
comment(0xB2E9, "Get the new value into A", inline=True)
comment(0xB2EA, "Wrap to 0..3 (4 columns per row)", inline=True)
comment(0xB2EC, "Save the new column index", inline=True)
comment(0xB2EE, "Wrapped to 0: end of row, print newline", inline=True)
comment(0xB2F0, "Mid-row: print 2-space column separator via inline",
        inline=True)

# print_decimal_3dig inline comments (5 items)
comment(0xB303, "Y = value to convert (digits read off via successive "
        "divisions)", inline=True)
comment(0xB304, "Divisor for hundreds digit", inline=True)
comment(0xB306, "Print hundreds digit", inline=True)
comment(0xB309, "Divisor for tens digit", inline=True)
comment(0xB30B, "Print tens digit", inline=True)
comment(0xB30E, "Divisor for units digit (always print at least the "
        "units to avoid the empty 0 case)", inline=True)

# print_decimal_digit inline comments (the body at &B310-&B326)
comment(0xB310, "Stash divisor in fs_error_ptr (the SBC target below)",
        inline=True)
# &B312 was previously misnamed cmd_remove; it's actually TYA
comment(0xB313, "X = '0'-1: digit counter, INX in the loop steps to '0' "
        "first", inline=True)
comment(0xB315, "Set carry", inline=True)
comment(0xB316, "Step quotient digit", inline=True)
comment(0xB317, "Subtract divisor", inline=True)
comment(0xB319, "No underflow: keep dividing", inline=True)
comment(0xB31B, "Underflow: add divisor back to recover the remainder",
        inline=True)
comment(0xB31D, "Remainder -> Y, ready for the next digit", inline=True)
comment(0xB31E, "Move digit ('0'-'9') from X into A for printing",
        inline=True)
comment(0xB31F, "Save divisor in X across the print (print_char_no_spool "
        "preserves X is not guaranteed)", inline=True)
comment(0xB321, "Print the digit, bypassing *SPOOL", inline=True)
comment(0xB324, "Restore divisor from X", inline=True)
comment(0xB326, "Return", inline=True)

# open_file_for_read inline comments (~28 items)
comment(0xBF78, "Save flags so caller's NZC survive", inline=True)
comment(0xBF79, "Move command-line offset Y into A for the add",
        inline=True)
comment(0xBF7A, "Clear C for the 16-bit add", inline=True)
comment(0xBF7B, "A = os_text_ptr_lo + Y (filename address low byte)",
        inline=True)
comment(0xBF7D, "Push it (we need to restore os_text_ptr after OSFIND)",
        inline=True)
comment(0xBF7E, "Move filename low into X (OSFIND wants the address in X/Y)",
        inline=True)
comment(0xBF7F, "A=0: zero high byte before the carry-add", inline=True)
comment(0xBF81, "Add os_text_ptr_hi with carry from the low add",
        inline=True)
comment(0xBF83, "Push filename high byte for the restore", inline=True)
comment(0xBF84, "Move filename high into Y", inline=True)
comment(0xBF85, "A=&40: OSFIND open-for-input mode", inline=True)
comment(0xBF87, "Open the file; returns handle in A (zero on failure)",
        inline=True)
comment(0xBF8A, "Copy returned handle into Y (also sets Z if zero)",
        inline=True)
comment(0xBF8B, "Stash the handle in ws_page for later close", inline=True)
comment(0xBF8D, "Non-zero: open succeeded, skip error path", inline=True)
comment(0xBF8F, "A=&D6: 'Not found' error code", inline=True)
comment(0xBF91, "Raise the error with the inline string below; never "
        "returns", inline=True)
# &BF94 inline string body
comment(0xBF9E, "Restore the saved filename high byte into "
        "os_text_ptr_hi -- but wait, this writes the FILENAME "
        "address into os_text_ptr; the caller intentionally moves "
        "os_text_ptr to scan past the filename below", inline=True)
comment(0xBFA1, "Restore filename low byte into os_text_ptr_lo (so "
        "(os_text_ptr) now points at the filename)", inline=True)
comment(0xBFA4, "Y=0: scan from start of filename", inline=True)
comment(0xBFA6, "Step to next byte", inline=True)
comment(0xBFA7, "Read filename byte", inline=True)
comment(0xBFA9, "Hit CR? End of command line", inline=True)
comment(0xBFAB, "Yes: filename ended at CR (no trailing spaces)",
        inline=True)
comment(0xBFAD, "Hit space? End of filename", inline=True)
comment(0xBFAF, "No (still inside filename): keep scanning", inline=True)
comment(0xBFB1, "Step past spaces", inline=True)
comment(0xBFB2, "Read next byte", inline=True)
comment(0xBFB4, "Still a space?", inline=True)
comment(0xBFB6, "Yes: keep skipping", inline=True)
comment(0xBFB8, "Done: Y points just past the filename and any spaces",
        inline=True)
comment(0xBFB9, "Restore caller's flags", inline=True)

# tx_econet_abort inline comments (~16 items)
comment(0xAD40, "Y=&D9: workspace offset for the abort code byte",
        inline=True)
comment(0xAD42, "Store the abort code (passed in A) at workspace[&D9]",
        inline=True)
comment(0xAD44, "A=&80: control = immediate-operation flag", inline=True)
comment(0xAD46, "Y=&0C: TXCB control-byte offset", inline=True)
comment(0xAD48, "Set TXCB[&0C] = &80 (immediate / abort)", inline=True)
comment(0xAD4A, "Save current net_tx_ptr low (we'll repoint TX at the "
        "abort packet)", inline=True)
comment(0xAD4C, "Push it for restore on exit", inline=True)
comment(0xAD4D, "Save net_tx_ptr high too", inline=True)
comment(0xAD4F, "Push it", inline=True)
comment(0xAD50, "TX low = &0C (abort packet starts at workspace[&0C])",
        inline=True)
comment(0xAD52, "Get nfs_workspace high byte", inline=True)
comment(0xAD54, "TX high = workspace page (so net_tx_ptr now points at "
        "the abort packet in workspace)", inline=True)
comment(0xAD56, "Send the abort packet via the standard TX path",
        inline=True)
comment(0xAD59, "A=&3F: TXCB status = abort-complete sentinel",
        inline=True)
comment(0xAD5B, "Write status via (net_tx_ptr,X) -- mark TX done",
        inline=True)
comment(0xAD5D, "Pull saved net_tx_ptr high", inline=True)
comment(0xAD5E, "Restore", inline=True)
comment(0xAD60, "Pull saved net_tx_ptr low", inline=True)
comment(0xAD61, "Restore -- caller's TX state intact", inline=True)
comment(0xAD63, "Return", inline=True)

# print_dump_header inline comments (14 items)
comment(0xBE01, "Read low nibble of starting address from (work_ae),Y",
        inline=True)
comment(0xBE03, "Save it (we'll print it 16 times incrementing each "
        "iteration)", inline=True)
comment(0xBE04, "Print '<CR>Address  : ' header via inline string",
        inline=True)
comment(0xBE13, "X=&0F: print 16 column-number digits", inline=True)
comment(0xBE15, "Pull the starting low nibble back into A", inline=True)
comment(0xBE16, "Print A as two hex digits + space", inline=True)
comment(0xBE19, "Set C ready for the increment", inline=True)
comment(0xBE1A, "A += 1 (column index increments, with C set on entry)",
        inline=True)
comment(0xBE1C, "Wrap to nibble (0..15)", inline=True)
comment(0xBE1E, "Step column counter", inline=True)
comment(0xBE1F, "Loop while X >= 0 (16 iterations)", inline=True)
comment(0xBE21, "Print ':    ASCII data<CR><CR>' trailer via inline",
        inline=True)
comment(0xBE35, "NOP -- bit-7 terminator + harmless resume opcode", inline=True)
comment(0xBE36, "Return", inline=True)

# parse_dump_range inline comments (~52 items)
# Phase 1: clear the 4-byte accumulator at (work_ae)
comment(0xBE42, "Move command-line offset Y into A for the X copy",
        inline=True)
comment(0xBE43, "X = current command-line offset (live cursor)",
        inline=True)
comment(0xBE44, "A=0: zero-fill value", inline=True)
comment(0xBE46, "Y=0: accumulator index", inline=True)
comment(0xBE47, "Zero accumulator byte at (work_ae)+Y", inline=True)
comment(0xBE49, "Step accumulator", inline=True)
comment(0xBE4A, "Done all 4 bytes?", inline=True)
comment(0xBE4C, "No: continue clearing", inline=True)
# Phase 2: read next character
comment(0xBE4E, "Reload command-line offset", inline=True)
comment(0xBE4F, "Step cursor", inline=True)
comment(0xBE50, "Y = stepped cursor (for the indirect read)", inline=True)
comment(0xBE51, "Read next command-line byte", inline=True)
comment(0xBE53, "CR? (end of address)", inline=True)
comment(0xBE55, "Yes: range parsed -- exit via space-skip", inline=True)
comment(0xBE57, "Space?", inline=True)
comment(0xBE59, "Yes: also a separator -- exit", inline=True)
comment(0xBE5B, "Below '0'?", inline=True)
comment(0xBE5D, "Yes: not hex -- raise 'Bad hex'", inline=True)
comment(0xBE5F, "Above '9'?", inline=True)
comment(0xBE61, "No: it's '0'-'9' -- skip the letter handling",
        inline=True)
comment(0xBE63, "Force uppercase via AND #&5F", inline=True)
comment(0xBE65, "Add &B8: 'A' (=&41) becomes &F9 with C set; 'F' becomes "
        "&FE; this maps 'A'-'F' to &FA-&FF in C", inline=True)
comment(0xBE67, "Carry out of ADC: digit was below 'A' -> bad hex",
        inline=True)
comment(0xBE69, "Below &FA? (i.e. before 'A' in mapped range)",
        inline=True)
comment(0xBE6B, "Yes (out of [&FA,&FF]): bad hex", inline=True)
# Mask to nibble and rotate accumulator
comment(0xBE6D, "Keep low nibble (0-15)", inline=True)
comment(0xBE6F, "Push the new nibble", inline=True)
comment(0xBE70, "Push X (current command-line offset)", inline=True)
comment(0xBE72, "X=4: rotate the 4-byte accumulator left 4 times",
        inline=True)
comment(0xBE74, "Y=0: byte index for the rotate", inline=True)
comment(0xBE76, "A=0 (and C clear from TYA's flags)", inline=True)
comment(0xBE77, "Save A onto stack so we can use PHP/PLP to round-trip "
        "carry through the rotate", inline=True)
comment(0xBE78, "Pull flags (effectively C clear from the TYA above; on "
        "later iterations C carries the bit shifted out)", inline=True)
comment(0xBE79, "Read next accumulator byte", inline=True)
comment(0xBE7B, "Shift in C from below, shift out top bit to C",
        inline=True)
comment(0xBE7C, "Write back", inline=True)
comment(0xBE7E, "Save the new C", inline=True)
comment(0xBE7F, "Pull A back (PHA earlier)", inline=True)
comment(0xBE80, "Step accumulator byte", inline=True)
comment(0xBE81, "Done all 4 bytes?", inline=True)
comment(0xBE83, "No: rotate next byte", inline=True)
comment(0xBE85, "PHA/PLP: bring saved C into flag register", inline=True)
comment(0xBE87, "C set: a bit fell off the top -- overflow",
        inline=True)
comment(0xBE89, "Step rotate counter", inline=True)
comment(0xBE8A, "Loop while X != 0 (4 rotates total)", inline=True)
# OR new nibble into accumulator low byte
comment(0xBE8C, "Pull saved X (command-line offset)", inline=True)
comment(0xBE8D, "Restore X", inline=True)
comment(0xBE8E, "Pull saved nibble into A", inline=True)
comment(0xBE8F, "Y=0: low byte of accumulator", inline=True)
comment(0xBE91, "OR new nibble into accumulator[0]", inline=True)
comment(0xBE93, "Write back", inline=True)
comment(0xBE95, "Loop for next hex digit", inline=True)
# Overflow exit
comment(0xBE98, "Discard saved nibble", inline=True)
comment(0xBE99, "Discard saved X", inline=True)
comment(0xBE9A, "Set C: signal overflow to caller", inline=True)
comment(0xBE9B, "Return with C=1", inline=True)
# Bad-hex error path
comment(0xBE9C, "Close the dump file before raising the error",
        inline=True)
comment(0xBE9F, "Raise 'Bad hex' error; never returns", inline=True)
# Trailing-space skip
comment(0xBEA2, "Step past current space", inline=True)
comment(0xBEA3, "Read next byte", inline=True)
comment(0xBEA5, "Still a space?", inline=True)
comment(0xBEA7, "Yes: keep skipping", inline=True)
comment(0xBEA9, "Clear C: signal success", inline=True)
comment(0xBEAA, "Return", inline=True)

# svc5_irq_check inline comments (complete the partial)
comment(0x8028, "Save X (the ROM slot we're being called on behalf of)",
        inline=True)
comment(0x8029, "Save Y (the dispatch-path selector via its high bit)",
        inline=True)
comment(0x802A, "Read deferred-work flag at &0D65 (set by NMI when work "
        "queued)", inline=True)
comment(0x802D, "Non-zero: there's work to dispatch", inline=True)
comment(0x802F, "Zero: no work; restore Y", inline=True)
comment(0x8030, "Restore X", inline=True)
comment(0x8031, "Return to MOS (service unclaimed)", inline=True)
comment(0x8032, "A=&80: bit 7 -- the bit to clear in ACCCON", inline=True)
comment(0x8034, "Clear ACCCON bit 7 (release IRR mask)",
        inline=True)
comment(0x8037, "Zero the deferred-work flag (we're handling it now)",
        inline=True)
comment(0x803A, "Bring saved Y back into A so BMI can test bit 7",
        inline=True)
comment(0x803B, "Bit 7 of caller's Y set: dispatch via PHA/PHA/RTS table",
        inline=True)
comment(0x8042, "Tail-jump to tx_done_exit which restores X/Y and "
        "claims the service", inline=True)

# osword_8_handler inline comments (~22 items)
comment(0xADD3, "Y=&0E: scan 15 bytes (offsets 14..0) of the PB",
        inline=True)
comment(0xADD5, "Is the OSWORD number 7?", inline=True)
comment(0xADD7, "Yes: handle as either 7 or 8 -- both copy PB to ws",
        inline=True)
comment(0xADD9, "Is the OSWORD number 8?", inline=True)
comment(0xADDB, "Neither 7 nor 8: return early (other OSWORDs handled "
        "elsewhere)", inline=True)
comment(0xADDD, "X=&DB: workspace offset for the PB copy",
        inline=True)
comment(0xADDF, "Temporarily reuse nfs_workspace as the destination "
        "low byte (high byte already points at the workspace page)",
        inline=True)
comment(0xADE1, "Read PB[Y]", inline=True)
comment(0xADE3, "Write to (nfs_workspace),Y -- effectively writes to "
        "workspace[&DB+Y]", inline=True)
comment(0xADE5, "Step backwards through the 15 bytes", inline=True)
comment(0xADE6, "Loop while Y >= 0", inline=True)
comment(0xADE8, "Bring Y back to 0 for the next single-byte write",
        inline=True)
comment(0xADE9, "Decrement nfs_workspace low byte: now points at "
        "workspace[&DA] (one before the copied region)", inline=True)
comment(0xADEB, "Read original OSWORD number from osbyte_a_copy",
        inline=True)
comment(0xADED, "Store at workspace[&DA] -- so the abort packet header "
        "carries the OSWORD number", inline=True)
comment(0xADEF, "Restore nfs_workspace to its proper low byte (Y=0)",
        inline=True)
comment(0xADF1, "Y=&14: TXCB control offset", inline=True)
comment(0xADF3, "A=&E9: status code for OSWORD-passthrough abort",
        inline=True)
comment(0xADF5, "Store status at TXCB[&14]", inline=True)
comment(0xADF7, "A=1: abort code for tx_econet_abort", inline=True)
comment(0xADF9, "Send the abort packet", inline=True)
comment(0xADFC, "Restore nfs_workspace from X (X is unchanged across "
        "tx_econet_abort)", inline=True)

# parse_fs_ps_args inline comments (~17 items)
comment(0xA3C4, "Save caller's X (command-line offset cursor)",
        inline=True)
comment(0xA3C5, "A=0: clear the dot-seen flag for parse_addr_arg",
        inline=True)
comment(0xA3C7, "Store cleared dot-seen flag", inline=True)
comment(0xA3C9, "Parse first number (network or standalone station)",
        inline=True)
comment(0xA3CC, "C set: parse_addr_arg saw an empty argument -- skip "
        "station storage", inline=True)
comment(0xA3CE, "Save the network number in fs_work_7", inline=True)
comment(0xA3D0, "Save Y (current command-line cursor) for after the "
        "bridge poll", inline=True)
comment(0xA3D1, "Populate the bridge routing table -- returns local "
        "network number in A", inline=True)
comment(0xA3D4, "EOR with parsed network: Z set iff parse matched local",
        inline=True)
comment(0xA3D6, "Match: keep A=0 to mark local network", inline=True)
comment(0xA3D8, "Mismatch: A = parsed network number", inline=True)
comment(0xA3DA, "Store network number into fs_work_6 (the canonical "
        "form: 0=local, non-zero=remote)", inline=True)
comment(0xA3DC, "Restore Y", inline=True)
comment(0xA3DD, "Step Y past the dot separator", inline=True)
comment(0xA3DE, "Parse station number after the dot", inline=True)
comment(0xA3E1, "C set: no station after dot -- leave fs_work_5 alone",
        inline=True)
comment(0xA3E3, "Store parsed station in fs_work_5", inline=True)
comment(0xA3E5, "Restore caller's X", inline=True)
comment(0xA3E6, "Return", inline=True)

# cmd_bye inline comments (8 items)
comment(0x9776, "Y=0: process_all_fcbs filter (0 = all FCBs)",
        inline=True)
comment(0x9778, "Walk all 16 FCB slots, calling start_wipe_pass on each",
        inline=True)
comment(0x977B, "OSBYTE &77 = close *SPOOL and *EXEC files", inline=True)
comment(0x977D, "Close any open *SPOOL/*EXEC handles", inline=True)
comment(0x9780, "A=&40: bit 6 of fs_flags = 'FS in active session'",
        inline=True)
comment(0x9782, "Clear bit 6: mark FS session inactive", inline=True)
comment(0x9785, "Close every Econet client channel", inline=True)
comment(0x9788, "Y=&17: FS function code 'Bye' (logoff request)",
        inline=True)

# cmd_fs inline comments (~14 items)
comment(0xA398, "Read current FS station from workspace", inline=True)
comment(0xA39B, "Save in fs_work_5 (so 'no-arg' path can print it)",
        inline=True)
comment(0xA39D, "Read current FS network", inline=True)
comment(0xA3A0, "Save in fs_work_6", inline=True)
comment(0xA3A2, "Look at the first command-line byte", inline=True)
comment(0xA3A4, "Is it CR (no argument)?", inline=True)
comment(0xA3A6, "Yes: print the current FS address", inline=True)
comment(0xA3A8, "Parse 'net.station' arg into fs_work_5/6", inline=True)
comment(0xA3AB, "A=1: OSWORD &13 sub-function 1 = set file server "
        "station", inline=True)
comment(0xA3AD, "Store sub-function in PB[0]", inline=True)
comment(0xA3AF, "A=&13: OSWORD &13", inline=True)
comment(0xA3B1, "X = lo of PB pointer (fs_work_4 = &B4)", inline=True)
comment(0xA3B3, "Y = hi of PB pointer (=0, since fs_work_4 is in "
        "zero page)", inline=True)
comment(0xA3B5, "Tail-jump into OSWORD; the OS routes us back through "
        "osword_13_set_station", inline=True)

# parse_addr_arg inline comments (~73 items)
# Prologue: detect '&' (hex prefix) vs digit
comment(0x92B2, "Zero the accumulator (fs_load_addr_2)", inline=True)
comment(0x92B4, "Read first command-line byte", inline=True)
comment(0x92B6, "Hex prefix '&'?", inline=True)
comment(0x92B8, "No: try decimal path", inline=True)
comment(0x92BA, "Yes: skip the '&'", inline=True)
comment(0x92BB, "Read first hex digit", inline=True)
comment(0x92BD, "Always taken (CMP #'&' set C if A>='&'); jump into "
        "the hex digit-range check", inline=True)
# Hex digit loop
comment(0x92BF, "Step to next character", inline=True)
comment(0x92C0, "Read next hex digit candidate", inline=True)
comment(0x92C2, "Dot? Net.station separator", inline=True)
comment(0x92C4, "Yes: switch to station-parsing mode", inline=True)
comment(0x92C6, "Below '!' (CR/space)? End of argument", inline=True)
comment(0x92C8, "Yes: number complete", inline=True)
# Hex digit range validation
comment(0x92CA, "Below '0'?", inline=True)
comment(0x92CC, "Yes: not a hex digit", inline=True)
comment(0x92CE, "Above '9'? (CMP #':')", inline=True)
comment(0x92D0, "No (it's '0'-'9'): straight to digit extraction",
        inline=True)
comment(0x92D2, "Force uppercase via AND #&5F", inline=True)
comment(0x92D4, "Map 'A'-'F' to &FA-&FF (ADC #&B8 with C from earlier "
        "CMP #':' which set C)", inline=True)
comment(0x92D6, "Carry out of ADC: was below 'A' -- bad hex", inline=True)
comment(0x92D8, "Below &FA? (digit > 'F' overflowed past)", inline=True)
comment(0x92DA, "Yes: bad hex (out of [&FA,&FF])", inline=True)
# Extract and accumulate hex digit
comment(0x92DC, "Mask to nibble", inline=True)
comment(0x92DE, "Stash digit value in fs_load_addr_3", inline=True)
comment(0x92E0, "Load accumulator", inline=True)
comment(0x92E2, "Above 16? (would overflow when shifted left 4)",
        inline=True)
comment(0x92E4, "Yes: overflow", inline=True)
comment(0x92E6, "Shift accumulator left 4 (multiply by 16)", inline=True)
comment(0x92E7, "(shift 2)", inline=True)
comment(0x92E8, "(shift 3)", inline=True)
comment(0x92E9, "(shift 4)", inline=True)
comment(0x92EA, "Add new nibble", inline=True)
comment(0x92EC, "Save updated accumulator", inline=True)
comment(0x92EE, "No carry: continue (always taken since accumulator "
        "was checked < 16 above)", inline=True)
# Decimal digit loop
comment(0x92F0, "Read next decimal-digit candidate", inline=True)
comment(0x92F2, "Dot? Net.station separator", inline=True)
comment(0x92F4, "Yes: switch to station-parsing mode", inline=True)
comment(0x92F6, "Below '!' (CR/space)?", inline=True)
comment(0x92F8, "Yes: number complete", inline=True)
comment(0x92FA, "Test for '0'-'9' and reject '&'/'.'", inline=True)
comment(0x92FD, "Not a decimal digit: bad number", inline=True)
comment(0x92FF, "Mask to nibble", inline=True)
comment(0x9301, "Stash digit", inline=True)
comment(0x9303, "Accumulator * 2", inline=True)
comment(0x9305, "Overflowed: too big for byte", inline=True)
comment(0x9307, "Reload doubled value", inline=True)
comment(0x9309, "* 2 again (now * 4)", inline=True)
comment(0x930A, "Overflow check", inline=True)
comment(0x930C, "* 2 again (now * 8)", inline=True)
comment(0x930D, "Overflow check", inline=True)
comment(0x930F, "+ accumulator (now * 8 + * 2 = * 10)", inline=True)
comment(0x9311, "Overflow check", inline=True)
comment(0x9313, "+ new digit", inline=True)
comment(0x9315, "Overflow check", inline=True)
comment(0x9317, "Save * 10 + digit", inline=True)
comment(0x9319, "Step input cursor", inline=True)
comment(0x931A, "Always taken (Y wraps at 256, never zero in practice)",
        inline=True)
# Termination / validation
comment(0x931C, "Read mode flag", inline=True)
comment(0x931E, "Bit 7 clear: in net.station mode -- validate result",
        inline=True)
comment(0x9320, "Decimal-only mode: get result", inline=True)
comment(0x9322, "Result is zero: bad parameter", inline=True)
comment(0x9324, "Return with parsed result in A (decimal-only path)",
        inline=True)
# Station validation
comment(0x9325, "Reload result", inline=True)
comment(0x9327, "Station 255 is reserved (broadcast)", inline=True)
comment(0x9329, "Yes: bad station number", inline=True)
comment(0x932B, "Reload result for the next test", inline=True)
comment(0x932D, "Non-zero: valid station, return", inline=True)
comment(0x932F, "Zero result: must have followed a dot to be valid",
        inline=True)
comment(0x9331, "No dot was seen: bad station number", inline=True)
comment(0x9333, "Dot seen: peek the byte before current cursor",
        inline=True)
comment(0x9334, "Read previous byte", inline=True)
comment(0x9336, "Restore Y", inline=True)
comment(0x9337, "Was previous char '.'?", inline=True)
comment(0x9339, "No: bad station number", inline=True)
comment(0x933B, "All checks passed: C=1 marks 'parsed successfully'",
        inline=True)
comment(0x933C, "Return", inline=True)
# Dot separator handler
comment(0x933D, "Dot already seen?", inline=True)
comment(0x933F, "Yes: 'Bad number' (multiple dots)", inline=True)
comment(0x9341, "Set dot-seen flag", inline=True)
comment(0x9343, "Get parsed network number (before dot)", inline=True)
comment(0x9345, "Network 255 is reserved", inline=True)
comment(0x9347, "Yes: 'Bad network number'", inline=True)
comment(0x9349, "Return; caller continues parsing the station", inline=True)

# netv_claim_release inline comments (~37 items)
comment(0xAD64, "Y = OSWORD parameter-block pointer high byte (used as "
        "an 'unrecognised' sentinel below)", inline=True)
comment(0xAD66, "Code &81? (compatibility shortcut for one specific "
        "claim type)", inline=True)
comment(0xAD68, "Yes: skip table scan, use match-result with Y already "
        "set non-zero", inline=True)
comment(0xAD6A, "Y=1: state 2 marker", inline=True)
comment(0xAD6C, "X=&0A: scan first 11 entries (table indices 0..&0A)",
        inline=True)
comment(0xAD6E, "Look up A in the claim code table", inline=True)
comment(0xAD71, "Match: handle as state 2", inline=True)
comment(0xAD73, "DEY: Y=0 (state 3 marker, two DEYs from 1)", inline=True)
comment(0xAD75, "X=&11: scan all 18 entries (state 3 also accepts "
        "the extended range)", inline=True)
comment(0xAD77, "Look up A again with extended range", inline=True)
comment(0xAD7A, "Match: handle as state 3", inline=True)
comment(0xAD7C, "Y=1 again (no match found, will return below)",
        inline=True)
# process_match_result
comment(0xAD7D, "X=2: default state code passed to tx_econet_abort",
        inline=True)
comment(0xAD7F, "Move match marker (Y) into A for the BEQ test",
        inline=True)
comment(0xAD80, "Y=0 (no match): return without action", inline=True)
comment(0xAD82, "Save flags so we can branch later on Y's sign",
        inline=True)
comment(0xAD83, "Y > 0 (state 2): skip the X bump", inline=True)
comment(0xAD85, "State 3: X=3 (different abort code)", inline=True)
# save_tube_state
comment(0xAD86, "Y=&DC: workspace offset for tube state bytes",
        inline=True)
comment(0xAD88, "Read tube_claimed_id,Y", inline=True)
comment(0xAD8B, "Save in workspace[&DC..]", inline=True)
comment(0xAD8D, "Step backwards", inline=True)
comment(0xAD8E, "Done at &DA?", inline=True)
comment(0xAD90, "Loop while Y > &DA (saves &DA, &DB, &DC -- 3 bytes)",
        inline=True)
comment(0xAD92, "Move state code (2 or 3) into A for the abort",
        inline=True)
comment(0xAD93, "Send abort with the state code", inline=True)
comment(0xAD96, "Restore the saved flags (Y's sign)", inline=True)
comment(0xAD97, "Y was positive (state 2): just return", inline=True)
# State 3 polling path
comment(0xAD99, "A=&7F: 'pending response' control value", inline=True)
comment(0xAD9B, "Y=&0C: TXCB control offset", inline=True)
comment(0xAD9D, "Mark TXCB as pending", inline=True)
comment(0xAD9F, "Read TXCB status byte", inline=True)
comment(0xADA1, "Bit 7 still clear: keep polling for response",
        inline=True)
comment(0xADA3, "Capture S so we can patch the caller's stack frame",
        inline=True)
comment(0xADA4, "Y=&DD: highest workspace offset for the response copy",
        inline=True)
comment(0xADA6, "Read first response byte (workspace[&DD])", inline=True)
comment(0xADAA, "Always taken (after ORA result is non-zero); store "
        "into stack[&106+X] then walk down", inline=True)
# Restore-stack loop
comment(0xADAC, "Step Y down", inline=True)
comment(0xADAD, "Step X down (stack offset)", inline=True)
comment(0xADAE, "Read next workspace byte", inline=True)
comment(0xADB0, "Patch caller's stack frame at &106+X", inline=True)
comment(0xADB3, "Reached &DA (lower workspace bound)?", inline=True)
comment(0xADB5, "No: keep restoring", inline=True)
comment(0xADB7, "Return", inline=True)

# cmd_wipe inline comments (~30 items in classified body)
comment(0xB6F3, "Reset access flags before parsing the new argument",
        inline=True)
comment(0xB6F6, "A=0: clear the file-iteration counter", inline=True)
comment(0xB6F8, "Store iteration counter (steps to next file each loop)",
        inline=True)
comment(0xB6FA, "Save text pointer for re-reading the wildcard each "
        "iteration", inline=True)
comment(0xB6FD, "Parse the wildcard filename into the &C030 buffer",
        inline=True)
comment(0xB700, "Step X past the CR terminator (so X = filename length+1)",
        inline=True)
comment(0xB701, "Save end-of-buffer offset", inline=True)
# request_next_wipe
comment(0xB703, "FS function code byte 0 = 1 (examine)", inline=True)
comment(0xB705, "TXCB[5] = 1: 'examine directory entry'", inline=True)
comment(0xB708, "TXCB[7] = 1: ditto for the second buffer slot",
        inline=True)
comment(0xB70B, "Load current iteration index", inline=True)
comment(0xB70D, "TXCB[6] = iteration index (which directory entry)",
        inline=True)
comment(0xB710, "X=3: copy starting at TX[3] (after the FS header bytes)",
        inline=True)
comment(0xB712, "Copy the parsed filename into the TX buffer", inline=True)
comment(0xB715, "Y=3: FS function code 'Examine'", inline=True)
comment(0xB717, "A=&80: set bit 7 of need_release_tube to flag long-lived "
        "TX", inline=True)
comment(0xB719, "Store flag", inline=True)
comment(0xB71B, "Send the examine request and wait for reply",
        inline=True)
comment(0xB71E, "Read FS reply byte 0 (status code)", inline=True)
comment(0xB721, "Non-zero status: process the response", inline=True)
# No-more-files exit path
comment(0xB723, "OSBYTE &0F: flush input buffer class", inline=True)
comment(0xB725, "X=1: flush keyboard buffer", inline=True)
comment(0xB727, "Flush keyboard buffer (clear pending Y/N keypress)",
        inline=True)
comment(0xB72A, "OSBYTE &7A: scan keyboard from key 16 (clear keypress "
        "queue)", inline=True)
comment(0xB72C, "Run the scan", inline=True)
comment(0xB72F, "Y=0: no key", inline=True)
comment(0xB731, "OSBYTE &78: write keys-pressed state", inline=True)
comment(0xB733, "Tail-call OSBYTE: clean up and return", inline=True)
# check_wipe_attr loop
comment(0xB736, "Read attribute byte from FS reply (TXCB[&2F])",
        inline=True)
comment(0xB739, "Is it 'L' (locked)?", inline=True)
comment(0xB73B, "Not locked: check for directory", inline=True)
comment(0xB73D, "Locked: skip this file, advance to next", inline=True)
comment(0xB73F, "Loop back to request the next directory entry",
        inline=True)
comment(0xB742, "Is it 'D' (directory)?", inline=True)
comment(0xB744, "Not a directory: prompt the user", inline=True)
comment(0xB746, "Directory: check second attribute byte (size)",
        inline=True)
comment(0xB749, "Loop back to attribute test (re-checks if non-empty)",
        inline=True)
# Display filename + Y/N prompt
comment(0xB74B, "X=1: scan name starting at TX[1]", inline=True)
comment(0xB74D, "Y = end-of-buffer offset (saved earlier in fs_work_6)",
        inline=True)
comment(0xB74F, "Read filename byte from TX[6+X]", inline=True)
comment(0xB752, "Print via *SPOOL-bypassing OSASCI", inline=True)
comment(0xB755, "Also store into the parse buffer for later use",
        inline=True)
comment(0xB758, "Step parse-buffer offset", inline=True)
comment(0xB759, "Step TX-buffer offset", inline=True)
comment(0xB75A, "Reached &0C (12 chars)?", inline=True)
comment(0xB75C, "No: continue copying", inline=True)
comment(0xB75E, "Print '(?/' prompt prefix and read response", inline=True)
comment(0xB761, "Inline string '(?/' is read by the hook above", inline=True)

# request_next_wipe response-handling tail (&B764..&B7C7). Reached
# after print_inline_no_spool returns from the '(?/' prompt at &B75E
# with A holding the user keypress.
comment(0xB764, "NOP -- bit-7 terminator + resume opcode for the '(?/' "
    "stringhi", inline=True)
comment(0xB765, "Print 'Y/N) ' via prompt_yn (reads keypress)", inline=True)
comment(0xB768, "Was the keypress '?' (help)?", inline=True)
comment(0xB76A, "Not '?': process Y/N response", inline=True)
comment(0xB76C, "'?': print CR before help text", inline=True)
comment(0xB76E, "Print CR character", inline=True)
comment(0xB771, "X=2: start of name in TX[2]", inline=True)
comment(0xB773, "Read name byte from TX[5+X] (FS reply)", inline=True)
comment(0xB776, "Print name char (no spool)", inline=True)
comment(0xB779, "Advance index", inline=True)
comment(0xB77A, "End of TX[5+X] name field at offset &3E?", inline=True)
comment(0xB77C, "No: continue printing", inline=True)
comment(0xB77E, "Print 'Wipe? ' help suffix via inline string", inline=True)
comment(0xB783, "Bit-7 terminator + resume", inline=True)
comment(0xB784, "Re-prompt user with prompt_yn", inline=True)
comment(0xB787, "Mask to upper-case ('A'..'Z' map to themselves)", inline=True)
comment(0xB789, "Was the response 'Y'?", inline=True)
comment(0xB78B, "No: skip this entry, advance to next", inline=True)
comment(0xB78D, "Yes: echo the keypress", inline=True)
comment(0xB790, "X=0: start scanning the parse-buffer name", inline=True)
comment(0xB792, "Read first parse-buffer byte at hazel_parse_buf", inline=True)
comment(0xB795, "Is it CR (no path component)?", inline=True)
comment(0xB797, "Yes: use leaf-name only path at &B7BD", inline=True)
comment(0xB799, "Read parse-buffer byte at hazel_parse_buf+X", inline=True)
comment(0xB79C, "Is it CR (end of name)?", inline=True)
comment(0xB79E, "No: check for space separator", inline=True)
comment(0xB7A0, "CR: substitute '.' so the dir prefix terminates "
    "with a separator", inline=True)
comment(0xB7A2, "Is it space?", inline=True)
comment(0xB7A4, "No: store byte as-is", inline=True)
comment(0xB7A6, "Yes: substitute CR (end-of-cmd)", inline=True)
comment(0xB7A8, "Store byte into TX[5+X] (delete-command buffer)", inline=True)
comment(0xB7AB, "Advance index", inline=True)
comment(0xB7AC, "Was that byte CR (just stored)?", inline=True)
comment(0xB7AE, "No: continue copying", inline=True)
comment(0xB7B0, "Y=&14: FS function code &14 = delete", inline=True)
comment(0xB7B2, "Send the delete request and wait for reply", inline=True)
comment(0xB7B5, "Decrement iteration counter so we re-examine the "
    "now-shifted-up slot", inline=True)
comment(0xB7B7, "Print newline before next entry", inline=True)
comment(0xB7BA, "Loop back to skip_wipe_locked (= request next entry)", inline=True)
comment(0xB7BD, "DEX: pre-decrement before the INX in the loop", inline=True)
comment(0xB7BE, "Advance index", inline=True)
comment(0xB7BF, "Read parse-buffer byte at hazel_parse_buf_1+X (skip CR at "
    "hazel_parse_buf)", inline=True)
comment(0xB7C2, "Store into TX[5+X] (delete-command buffer)", inline=True)
comment(0xB7C5, "Reached space (end-of-leaf)?", inline=True)
comment(0xB7C7, "No: continue copying", inline=True)

# &959A..&95E8: *FS/*PS no-argument syntax-help printer + shared
# print-inline tails. print_fs_ps_help (&959A) checks for an
# argument after the command; if absent (CR), it prints a four-line
# syntax block by chaining print_fs_station / print_dir_syntax /
# print_station_low / print_dir_syntax / inline 'Space\rNoSpace\r'.
# print_fs_station and print_station_low both fall into a shared
# 'S       ' tail at &95CD, so they emit 'FS       ' and 'PS       '
# respectively. The NOP/CLV bytes are bit-7 terminators for the
# preceding inline strings and double as resume opcodes.
comment(0x959A, "Read first command-line char at (os_text_ptr),Y", inline=True)
comment(0x959C, "Is it CR (no argument supplied)?", inline=True)
comment(0x959E, "Non-CR: argument present -- exit via "
    "dispatch_fs_ps_with_arg (X=&A0)", inline=True)
comment(0x95A0, "CR: print 'FS       ' header", inline=True)
comment(0x95A3, "Print '[<D>.]<D>\\r'", inline=True)
comment(0x95A6, "Print 'PS       ' header", inline=True)
comment(0x95A9, "Print '[<D>.]<D>\\r' again", inline=True)
comment(0x95AC, "Print final 'Space\\rNoSpace\\r' lines", inline=True)
comment(0x95BD, "NOP -- bit-7 terminator + resume opcode for the "
    "preceding inline string", inline=True)
comment(0x95C1, "Print 'P' prefix", inline=True)
comment(0x95C5, "CLV -- bit-7 terminator + resume (V flag is "
    "irrelevant here, used as 1-byte resume opcode)", inline=True)
comment(0x95C6, "BVC: V was just cleared -> always taken; falls "
    "into the shared 'S       ' tail at &95CD", inline=True)
comment(0x95C8, "Print 'F' prefix", inline=True)
comment(0x95CC, "NOP -- bit-7 terminator; falls through into the "
    "shared 'S       ' tail at &95CD", inline=True)
comment(0x95CD, "Print 'S       ' (S + 7 spaces) -- the shared "
    "8-char field used by both 'FS' and 'PS' callers", inline=True)
comment(0x95D8, "Bit-7 terminator", inline=True)
comment(0x95D9, "Return", inline=True)
comment(0x95DA, "Print '[<D>.]<D>\\r' (file-name syntax fragment, "
    "shared between *FS/*PS no-arg help and *Dir)", inline=True)
comment(0x95E7, "Bit-7 terminator", inline=True)
comment(0x95E8, "Return", inline=True)
comment(0x95E9, "X=&A0: index into svc4 dispatch table (no-arg path)",
    inline=True)
comment(0x95EB, "Tail-jump to svc4_dispatch_lookup with X=&A0", inline=True)

# &A5FB..&A604: tail of os_text_ptr+Y -> fs_crc 16-bit pointer add.
comment(0xA5FB, "Store low byte of (os_text_ptr + Y) -> fs_crc_lo "
    "(repurposed as a generic pointer)", inline=True)
comment(0xA5FD, "Load os_text_ptr_hi for the high-byte add", inline=True)
comment(0xA5FF, "Add carry from low add (no extra increment)", inline=True)
comment(0xA601, "Store result high byte -> fs_crc_hi", inline=True)

# &A9EF..&A9F6: FS-flags update after handle clearing in the FS-state
# transition. fs_flags is &0D6C; the helper sets bits &0E (3..1) and
# clears bit &40 (FS-active flag) in one read-modify-write pass.
comment(0xA9EF, "A=&0E: bits 1..3 (FS-state mask)", inline=True)
comment(0xA9F1, "Set fs_flags bits 1..3", inline=True)
comment(0xA9F4, "A=&40: FS-active flag bit", inline=True)
comment(0xA9F6, "Clear FS-active flag (bit 6)", inline=True)
comment(0xA9F9, "X=&0F: scan all 16 FCB slots (X = 15 down to 0)",
    inline=True)

# &AABB..&AAC1: set_via_shadow_pair body.
comment(0xAABB, "Mirror A into ws_0d68 (ACR-format byte)", inline=True)
comment(0xAABE, "Mirror A into ws_0d69 (IER-format byte)", inline=True)
comment(0xAAC1, "Return", inline=True)

# cmd_pollps gap-fill (8 items).
comment(0xB60F, "Y=&18: name field offset in RX buffer", inline=True)
comment(0xB624, "Bit-7 terminator from preceding stringhi", inline=True)
comment(0xB625, "Pop saved slot index", inline=True)
comment(0xB649, "X=0: indexed-indirect access mode", inline=True)
comment(0xB657, "Ensure V clear so next BVC always taken", inline=True)
comment(0xB675, "Advance work_ae to next status byte (lo)", inline=True)
comment(0xB68E, "Advance work_ae to next status byte (lo)", inline=True)
comment(0xB690, "Read network number byte via (work_ae,X)", inline=True)

# init_dump_buffer tail: 32-bit add + store-back loop (&BF58..&BF70).
# Adds the workspace 4-byte word at (work_ae)+0..3 to the same offset
# in osword_flag scratch, then stores the result into (work_ae)+&10..&13.
# This computes the absolute end address for the *Dump range.
comment(0xBF58, "Read low byte of address from (work_ae)+Y", inline=True)
comment(0xBF5A, "Add osword_flag+Y (low byte of length, with carry "
    "propagating)", inline=True)
comment(0xBF5D, "Store sum back to osword_flag+Y", inline=True)
comment(0xBF60, "Advance to next byte", inline=True)
comment(0xBF61, "Decrement byte counter", inline=True)
comment(0xBF62, "Loop until 4 bytes added", inline=True)
comment(0xBF64, "Y=&14: target offset = workspace+&13 (top of end-addr "
    "field, stored hi-byte-first)", inline=True)
comment(0xBF66, "X=3: source = osword_flag+3 (top byte of sum)", inline=True)
comment(0xBF68, "Pre-decrement Y (so first store is to offset &13)", inline=True)
comment(0xBF69, "Read sum byte from osword_flag+X", inline=True)
comment(0xBF6B, "Store at (work_ae)+Y", inline=True)
comment(0xBF6D, "Decrement source index", inline=True)
comment(0xBF6E, "Loop until X wraps below 0", inline=True)
comment(0xBF70, "Return", inline=True)

# tx_calc_transfer head (&8900..&8922). Master 128 ACCCON-aware
# transfer-mode setup: read &FE34 (ACCCON), set bit 3 of escapable,
# and decide on a Tube vs RAM transfer path.
comment(0x8900, "Read ACCCON (Master 128 access-control register)", inline=True)
comment(0x8903, "Set bit 3 of A (transfer-mode flag)", inline=True)
comment(0x8905, "Store as escapable mode", inline=True)
comment(0x8907, "Y=7: scout-bytes counter", inline=True)
comment(0x8914, "C clear: no Tube, plain transfer path", inline=True)
comment(0x8916, "Z clear (other state set): use fallback path", inline=True)
comment(0x8918, "Z set: re-read ACCCON for second decision", inline=True)
comment(0x891B, "Rotate bit 0 (E flag) into C", inline=True)
comment(0x891C, "C clear: shadow not enabled, fallback path", inline=True)
comment(0x891E, "Shadow enabled: set bit 2 of escapable", inline=True)
comment(0x8920, "Atomic bit-set on escapable", inline=True)
comment(0x8922, "Branch to fallback_calc_transfer (always)", inline=True)

# service_handler gap-fill: PHY/PLY around the body's stack-frame
# manipulation, plus the cascaded SBC/CMP gate that maps service-call
# numbers to dispatch indices.
comment(0x8A59, "Save Y on stack across the version-check", inline=True)
comment(0x8A8C, "Restore Y from stack", inline=True)
comment(0x8ABA, "C clear: service number was below the prior CMP "
    "threshold, take dispatch fall-through", inline=True)
comment(0x8ABC, "Subtract 5 to remap service range", inline=True)
comment(0x8ABE, "Compare with &0E", inline=True)
comment(0x8AC0, "Equal: dispatch directly", inline=True)
comment(0x8AC2, "Below: take dispatch fall-through", inline=True)
comment(0x8AC4, "Subtract 8 to remap further", inline=True)
comment(0x8AC6, "Compare with &0F", inline=True)
comment(0x8AC8, "Below: dispatch fall-through", inline=True)
comment(0x8ACA, "Compare with &18", inline=True)
comment(0x8ACC, "Below: dispatch index now in A", inline=True)

# lang_4_validated (&989F): validates a remote-validated
# language reply -- checks RX buffer offset 0 (status byte) and the
# session ID at offset &80 against the stored copy at workspace+&0E.
comment(0x989F, "Y=0: status byte offset", inline=True)
comment(0x98A1, "Read RX status byte", inline=True)
comment(0x98A3, "Zero status: re-init the session", inline=True)
comment(0x98A5, "Y=&80: session-ID byte offset in RX", inline=True)
comment(0x98A7, "Read remote session-ID", inline=True)
comment(0x98A9, "Y=&0E: stored session-ID offset in workspace", inline=True)
comment(0x98AB, "Compare with stored ID", inline=True)
comment(0x98AD, "Mismatch: skip the commit (treat as foreign)", inline=True)

# osword_4_handler (&AD32): NETV reason 4 -- adjusts caller flags
# stored on the MOS stack, stores Y as workspace[&DA], and falls
# into tx_econet_abort.
comment(0xAD32, "Read the MOS stack frame holding caller flags", inline=True)
comment(0xAD33, "Shift carry out of caller P (stack[&106+X])", inline=True)
comment(0xAD36, "Carry is now cleared in caller P", inline=True)
comment(0xAD3A, "Y=&DA: workspace osword-4 result offset", inline=True)
comment(0xAD3C, "Store Y at (nfs_workspace)+&DA", inline=True)
comment(0xAD3E, "A=0: clear A for the abort path", inline=True)

# find_station_bit2 / find_station_bit3 (&A644 / &A66F): scan the
# 16-entry station table at hazel_fcb_status for an entry whose bit 2 / bit 3
# is set, optionally allocating a new FCB slot via alloc_fcb_slot
# when no match is found.
comment(0xA644, "X=&10: scan 16 entries", inline=True)
comment(0xA646, "Clear V (no-match marker)", inline=True)
comment(0xA647, "Step to previous entry", inline=True)
comment(0xA648, "Below 0: scan complete", inline=True)
comment(0xA64A, "Compare entry X's stn/net with caller's", inline=True)
comment(0xA64D, "No match: continue", inline=True)
comment(0xA64F, "Match: read entry's flag byte at hazel_fcb_status+X", inline=True)
comment(0xA652, "Mask bit 2", inline=True)
comment(0xA654, "Bit 2 clear: keep scanning", inline=True)
comment(0xA656, "Bit 2 set: A = matched entry index (Y)", inline=True)
comment(0xA657, "Store Y at hazel_fcb_slot_attr+X (link entry to slot)", inline=True)
comment(0xA65A, "BIT always_set_v_byte: V <- 1 (match found)", inline=True)
comment(0xA65D, "Save Y at hazel_fs_saved_station (matched entry index)", inline=True)
comment(0xA660, "V set: skip new-slot alloc", inline=True)
comment(0xA662, "A = caller's index", inline=True)
comment(0xA663, "Allocate a fresh FCB slot", inline=True)
comment(0xA666, "Save FCB slot index at hazel_fcb_slot_1", inline=True)
comment(0xA669, "Z set: alloc failed -> restore FS context", inline=True)
comment(0xA66B, "A=&26: workspace flag for bit 2 search", inline=True)

comment(0xA66F, "X=&10: scan 16 entries", inline=True)
comment(0xA671, "Clear V (no-match marker)", inline=True)
comment(0xA672, "Step to previous entry", inline=True)
comment(0xA673, "Below 0: scan complete", inline=True)
comment(0xA675, "Compare entry's stn/net with caller's", inline=True)
comment(0xA678, "No match: continue", inline=True)
comment(0xA67A, "Match: read entry's flag byte at hazel_fcb_status+X", inline=True)
comment(0xA67D, "Mask bit 3", inline=True)
comment(0xA67F, "Bit 3 clear: keep scanning", inline=True)
comment(0xA681, "Bit 3 set: A = matched entry index (Y)", inline=True)
comment(0xA682, "Store Y at hazel_fcb_slot_attr+X (link entry to slot)", inline=True)
comment(0xA685, "BIT always_set_v_byte: V <- 1 (match found)", inline=True)
comment(0xA688, "Save Y at hazel_fs_context_copy (matched entry index)", inline=True)
comment(0xA68B, "V set: skip new-slot alloc", inline=True)
comment(0xA68D, "A = caller's index", inline=True)
comment(0xA68E, "Allocate a fresh FCB slot", inline=True)
comment(0xA691, "Save FCB slot index at hazel_fcb_slot_2", inline=True)
comment(0xA694, "Z set: alloc failed -> restore FS context", inline=True)
comment(0xA696, "A=&2A: workspace flag for bit 3 search", inline=True)

# fscv_3_star_cmd (&A42F): FSCV reason 3 -- handle *<command>.
comment(0xA42F, "Set text/transfer pointers from FS context", inline=True)
comment(0xA432, "Y=&FF -- mark spool/Tube state inactive", inline=True)
comment(0xA434, "Store fs_spool_handle = &FF", inline=True)
comment(0xA436, "Store need_release_tube = &FF", inline=True)
comment(0xA439, "X=&35: NFS-commands sub-table offset", inline=True)
comment(0xA43B, "Match against the NFS sub-table", inline=True)
comment(0xA43E, "C set: no match -> dispatch via fall-through", inline=True)

# lang_0_insert_key (&98AF): take remote keypress, insert
# into local keyboard buffer.
comment(0x98AF, "Y=&82: keypress byte offset in RX", inline=True)
comment(0x98B1, "Read remote keypress code", inline=True)
comment(0x98B3, "Y = key code", inline=True)
comment(0x98B4, "X=0: keyboard buffer ID", inline=True)
comment(0x98B6, "Commit the language-reply state", inline=True)
comment(0x98B9, "OSBYTE &99: insert byte into input buffer", inline=True)

# store_ps_station (&B477): store current FS work_5/6 (station/net)
# at workspace+2 and return.
comment(0xB477, "Y=2: workspace offset for stored station", inline=True)
comment(0xB479, "Load station number", inline=True)
comment(0xB47B, "Store at (nfs_workspace)+2", inline=True)
comment(0xB47E, "Load network number", inline=True)
comment(0xB480, "Store at (nfs_workspace)+3", inline=True)
comment(0xB482, "Return", inline=True)

# err_bad_hex group (&934A..&9388): error-raising stubs that each
# load a specific error code and call error_bad_inline.
comment(0x9353, "Test fs_work_4 bit 7", inline=True)
comment(0x9355, "Bit 7 set: redirect to error_bad_param", inline=True)
comment(0x9357, "A=&D0: 'Bad station' error code", inline=True)
comment(0x9359, "Raise via error_bad_inline (never returns)", inline=True)
comment(0x936B, "A=&F0: 'Bad number' error code", inline=True)
comment(0x936D, "Raise via error_bad_inline (never returns)", inline=True)
comment(0x9377, "A=&94: 'Bad parameter' error code", inline=True)
comment(0x9379, "Raise via error_bad_inline (never returns)", inline=True)
comment(0x9386, "A=&D1: 'Bad net number' error code", inline=True)
comment(0x9388, "Raise via error_bad_inline (never returns)", inline=True)

# fscv_2_star_run (&A4E4): FSCV reason 2 -- *RUN.
comment(0xA4E4, "Save text pointer (for GSREAD-driven parsing)", inline=True)
comment(0xA4E7, "Reset fs_lib_flags low bits to 5-bit access mask", inline=True)
comment(0xA4EA, "Set bit 1 of A (mark *RUN-style invocation)", inline=True)

# cmd_fs_reentry / dispatch_fs_cmd (&A44E): PHA/PHA/RTS dispatch
# using the NFS-commands table at cmd_dispatch_lo_table/cmd_dispatch_hi_table indexed by X.
comment(0xA44E, "A=0: clear svc_state", inline=True)
comment(0xA450, "Store -> svc_state", inline=True)
comment(0xA452, "Load dispatch hi byte from cmd_dispatch_hi_table+X", inline=True)
comment(0xA455, "Push hi for RTS dispatch", inline=True)
comment(0xA456, "Load dispatch lo byte from cmd_dispatch_lo_table+X", inline=True)
comment(0xA459, "Push lo for RTS dispatch", inline=True)
comment(0xA45A, "RTS -> dispatched command handler", inline=True)

# svc_2_priv_ws (&8F10): allocate workspace pages
# for the NFS ROM. Tests CMOS &11 bit 2 to choose how many pages.
comment(0x8F10, "Save Y on stack (caller's claim)", inline=True)
comment(0x8F11, "X=&11: CMOS RAM byte index", inline=True)
comment(0x8F13, "Read CMOS &11 via osbyte_a1", inline=True)
comment(0x8F16, "A = CMOS &11 value", inline=True)
comment(0x8F17, "Mask bit 2 (workspace-size flag)", inline=True)
comment(0x8F19, "Bit 2 set: keep caller's Y, advance by 2", inline=True)
comment(0x8F1B, "Bit 2 clear: A=&0B (use 11-page minimum)", inline=True)
comment(0x8F1D, "BRA to common tail", inline=True)
comment(0x8F1F, "Bit-2-set path: restore Y", inline=True)
comment(0x8F20, "TYA / INY / INY -- raise Y by 2 pages", inline=True)
comment(0x8F21, "Y += 1", inline=True)
comment(0x8F22, "Y += 1 again (total +2)", inline=True)
comment(0x8F23, "Push raised Y", inline=True)
comment(0x8F24, "Store final page count high to net_rx_ptr_hi", inline=True)
comment(0x8F26, "Increment for nfs_workspace_hi", inline=True)
comment(0x8F27, "Store workspace high page", inline=True)
comment(0x8F29, "A=0: clear-byte for the lo halves below", inline=True)
comment(0x8F2B, "Clear net_rx_ptr_lo (page-aligned)", inline=True)
comment(0x8F2D, "Clear nfs_workspace_lo (page-aligned)", inline=True)
comment(0x8F2F, "Compute workspace start page via get_ws_page", inline=True)
comment(0x8F32, "Y >= &DC?", inline=True)
comment(0x8F34, "Restore Y from stack", inline=True)
comment(0x8F35, "Yes: jump to set_rom_ws_page (error path)", inline=True)
comment(0x8F37, "Return", inline=True)

# lang_1_remote_boot (&9850): handle remote-fired *BOOT request.
comment(0x9850, "Y=0: status byte offset", inline=True)
comment(0x9852, "Read RX status byte", inline=True)
comment(0x9854, "Zero: re-init the session", inline=True)
comment(0x9856, "Non-zero: commit state and continue", inline=True)
comment(0x9859, "Mark session as 'remote boot'", inline=True)
comment(0x985B, "Store updated status byte back to RX[0]", inline=True)
comment(0x985D, "X=&80: caller machine-id byte offset", inline=True)
comment(0x985F, "Y=&80: same offset", inline=True)
comment(0x9861, "Read remote machine ID", inline=True)
comment(0x9863, "Push -- save across the workspace store", inline=True)
comment(0x9865, "Re-read for the second store target", inline=True)
comment(0x9867, "Y=&0F: workspace machine-ID lo offset", inline=True)
comment(0x9869, "Store at (nfs_workspace)+&0F", inline=True)
comment(0x986C, "Pop saved machine ID", inline=True)
comment(0x986D, "Store at (nfs_workspace)+&0F (reuse)", inline=True)
comment(0x986F, "Scan remote-key flags", inline=True)
comment(0x9872, "Initialise narrow workspace template", inline=True)
comment(0x9875, "X=1: enable Econet keyboard", inline=True)
comment(0x9877, "Y=0", inline=True)
comment(0x9879, "OSBYTE &C9: read/write Econet keyboard disable", inline=True)

# strip_token_prefix tail (&B275..&B297): handle '#'/':' filename
# prefixes (Master 128 syntax for FS-select).
comment(0xB275, "Test for '#' prefix (3 ^ &23 = 0)", inline=True)
comment(0xB277, "Equal: '#' was the prefix, return", inline=True)
comment(0xB279, "Other: not a recognised prefix -> error", inline=True)
comment(0xB27C, "Test for ':' (&3F ^ &1C)", inline=True)
comment(0xB27E, "Different: caller had no prefix, return", inline=True)
comment(0xB280, "':' confirmed -- read next char from parse buffer", inline=True)
comment(0xB283, "Test for '.' (path separator)", inline=True)
comment(0xB285, "Equal: ':.' qualified prefix", inline=True)
comment(0xB287, "Test for '#'", inline=True)
comment(0xB289, "Other: no recognised tail prefix, return", inline=True)
comment(0xB28B, "Recognised: load fs_lib_flags", inline=True)
comment(0xB28E, "Set bit 6 (FS-select pending)", inline=True)
comment(0xB290, "Store updated fs_lib_flags", inline=True)
comment(0xB293, "Recurse to strip the trailing component", inline=True)
comment(0xB296, "Decrement X (consume processed char)", inline=True)
comment(0xB297, "Return", inline=True)

# alloc_run_channel partial gap-fill (most already commented).
comment(0xA5C9, "A = parsed character", inline=True)
comment(0xA5D2, "Y=3: skip past 3-byte FS header", inline=True)
comment(0xA5E4, "For the loop entry", inline=True)
comment(0xA5EB, "Always (BCC after CLC) loop back", inline=True)
comment(0xA5EE, "Advance Y past trailing space", inline=True)
comment(0xA5F5, "Test for CR (terminator)", inline=True)
comment(0xA5F7, "Clear C for arithmetic", inline=True)
comment(0xA606, "X=&C0: pointer-to-options high byte", inline=True)
comment(0xA60C, "Store as fs_options", inline=True)
comment(0xA62C, "Y=&C1: high byte of TX buffer pointer", inline=True)
comment(0xA62E, "A=4: option byte for *RUN", inline=True)
comment(0xA630, "Relocated execute path", inline=True)
comment(0xA633, "A=1: dispatch flag", inline=True)
comment(0xA635, "Indirect jump via workspace vector", inline=True)

# osword_setup_handler partial gap-fill.
comment(0xA867, "Push for stack frame manipulation", inline=True)
comment(0xA86B, "Push again", inline=True)
comment(0xA879, "A = sub-code", inline=True)
comment(0xA884, "Compare with &04", inline=True)
comment(0xA871, "PB-ready / parameter table (3 bytes) read by "
    "osword_setup_handler at &A868 via LDA osword_pb_ready,X",
    inline=True)
comment(0xA874, "BIT $abs -- 3-byte skip-trick that jumps over the "
    "extract_osword_subcode prologue when called via &A874",
    inline=True)
comment(0xA877, "Shift ws_page right -- splits parameter byte "
    "into upper / lower nibbles", inline=True)
comment(0xA87A, "LDA #&A9 -- 2-byte BIT-trick filler "
    "(skipped when entered at &A87E)", inline=True)
comment(0xA87C, "LDA #&A9 -- 2-byte BIT-trick filler", inline=True)
comment(0xA87E, "Load template source pointer", inline=True)
comment(0xA886, "Equal: take save_txcb_and_convert path", inline=True)
comment(0xA88A, "Equal: take save_txcb_done path", inline=True)
comment(0xA8C6, "Push current A", inline=True)
comment(0xA8CF, "Pop saved value", inline=True)
comment(0xA8D1, "Divide by 4", inline=True)
comment(0xA8D2, "(continued)", inline=True)
comment(0xA8D4, "Add &51 (offset base)", inline=True)
comment(0xA8E6, "Return", inline=True)
comment(0xA8E7, "Convert TXCB date/time bytes to BCD", inline=True)
comment(0xA8EA, "Y=7: copy 8 bytes (Y=7 down to 0)", inline=True)
comment(0xA8EC, "Load BCD byte from TXCB area "
    "(hazel_txcb_lib + Y)", inline=True)
comment(0xA8EF, "Store to PB[Y]", inline=True)
comment(0xA8F1, "Decrement Y (advance backwards)", inline=True)
comment(0xA8F2, "Loop until Y wraps", inline=True)
comment(0xA8F4, "A=2: PB[0] parameter for OSWORD &0E "
    "(seconds-since-midnight format)", inline=True)
comment(0xA8F6, "Store parameter at PB[0]", inline=True)
comment(0xA8F8, "A=&0E: OSWORD &0E (read CMOS RTC)", inline=True)
comment(0xA8FA, "X = PB pointer low", inline=True)
comment(0xA8FC, "Y = PB pointer high (via table_idx scratch)",
    inline=True)

# osword_13_set_handles partial gap-fill.
comment(0xAAE5, "A=0: invalid-handle marker", inline=True)
comment(0xAB01, "Save Y for processing", inline=True)
comment(0xAB02, "Push Y", inline=True)
comment(0xAB08, "Pop saved Y", inline=True)
comment(0xAB13, "Compare with 4", inline=True)
comment(0xAB18, "Return", inline=True)
comment(0xAB1D, "Save current Y", inline=True)
comment(0xAB1F, "Y=8 (handle-bit shift index)", inline=True)
comment(0xAB29, "Set bits 3 and 5", inline=True)
comment(0xAB31, "Push for save/restore", inline=True)
comment(0xAB37, "Pop saved value", inline=True)

# store_ptr_at_ws_y partial gap-fill (NETV path).
comment(0xACB6, "Return", inline=True)
comment(0xACB8, "Y=1: workspace offset", inline=True)
comment(0xACD6, "Y=&7D: workspace pointer offset", inline=True)
comment(0xACDE, "Set carry", inline=True)
comment(0xACE5, "Loop while X != 0", inline=True)
comment(0xACEA, "Loop while not CR", inline=True)
comment(0xACF0, "Y=&7B: end-byte offset", inline=True)
comment(0xACF4, "Add 3 (end-of-buffer adjust)", inline=True)

# cmd_run_via_urd gap-fill (&A4F1 mid-body, ~19 items).
comment(0xA504, "A=2: open-input mode for OSFIND", inline=True)
comment(0xA509, "Y=&12: cmd code for *RUN", inline=True)
comment(0xA50B, "Send the request and wait for reply", inline=True)
comment(0xA50E, "Read reply status from TX[5]", inline=True)
comment(0xA511, "Compare with 1 (not-found)", inline=True)
comment(0xA51F, "Decrement X (post-find adjustment)", inline=True)
comment(0xA525, "X=1: target offset for the *RUN-channel command", inline=True)
comment(0xA527, "Store X to hazel_txcb_data (cmd byte)", inline=True)
comment(0xA52A, "Store X to hazel_txcb_flag (cmd flag)", inline=True)
comment(0xA52E, "Copy filename arg into TX buffer", inline=True)
comment(0xA54A, "Shift bit 7 into carry", inline=True)
comment(0xA550, "X=&FF -- start scan from end", inline=True)
comment(0xA556, "Compare with CR (terminator)", inline=True)
comment(0xA560, "Decrement scan index", inline=True)
comment(0xA56B, "Decrement scan index", inline=True)
comment(0xA571, "Mark byte as 'argument'", inline=True)
comment(0xA578, "X=&FF -- restart scan from end", inline=True)
comment(0xA588, "Mark caller's flags", inline=True)

# init_bridge_poll tail (&AC25..&AC46) -- the body inlines for &ABF1..&AC23
# live in the deliberate review block lower down.
comment(0xAC25, "Push X (saved across delay)", inline=True)
comment(0xAC2C, "Y=&18: status-byte offset", inline=True)
comment(0xAC3C, "Result byte to Y", inline=True)
comment(0xAC41, "Invert (presence -> absence)", inline=True)
comment(0xAC46, "Return", inline=True)

# copy_ps_data gap-fill (&B3D7, ~36 items).
comment(0xB3E6, "Save Y at ws_ptr_hi", inline=True)
comment(0xB3F2, "Advance Y past padding", inline=True)
comment(0xB3F4, "Loop while Y wraps", inline=True)
comment(0xB3F9, "Restore Y from ws_ptr_hi", inline=True)
comment(0xB400, "X=6: scan up to 6 PS slots", inline=True)
comment(0xB40F, "C set: end of slots", inline=True)
comment(0xB429, "Pop saved slot index", inline=True)
comment(0xB42C, "Push it back (for retry)", inline=True)
comment(0xB432, "Advance Y by 4 (next slot)", inline=True)
comment(0xB435, "Read ws byte at (nfs_workspace)+Y", inline=True)
comment(0xB437, "Save as work_ae lo", inline=True)
comment(0xB439, "Read indirect via (work_ae,X)", inline=True)
comment(0xB43B, "Z set: zero -> read station addr", inline=True)
comment(0xB43D, "Compare with 3", inline=True)
comment(0xB43F, "Other than 3: skip slot mark", inline=True)
comment(0xB441, "Back up to network byte", inline=True)
comment(0xB442, "Read network byte", inline=True)
comment(0xB444, "Save as fs_work_6", inline=True)
comment(0xB446, "Back up to station byte", inline=True)
comment(0xB447, "Read station byte", inline=True)
comment(0xB449, "Save as fs_work_5", inline=True)
comment(0xB44B, "Y=&20: PS marker offset", inline=True)
comment(0xB44D, "Store station to (net_rx_ptr)+&20", inline=True)
comment(0xB44F, "Pop saved slot index", inline=True)
comment(0xB451, "A=&3F: 'processed' marker", inline=True)
comment(0xB453, "Mark slot as processed", inline=True)
comment(0xB457, "Print 'Printer server is ' fragment", inline=True)
comment(0xB45A, "Y=&20: marker offset", inline=True)
comment(0xB45C, "Read marker byte", inline=True)
comment(0xB45E, "Non-zero: print 'now <stn>'", inline=True)
comment(0xB460, "Print 'still ' fragment", inline=True)
comment(0xB469, "Bit-7 terminator (next opcode)", inline=True)
comment(0xB46C, "Print 'now ' fragment", inline=True)
comment(0xB473, "Bit-7 terminator", inline=True)
comment(0xB474, "Print station number and newline", inline=True)

# fscv_5_cat partial gap-fill (&B118, ~37 items in deeper body).
comment(0xB188, "Push for stack-based saves", inline=True)
comment(0xB1B7, "Bit 7 of A set (negative): print directory header", inline=True)
comment(0xB1B9, "Print char (no spool)", inline=True)
comment(0xB1BC, "Advance Y", inline=True)
comment(0xB1BD, "Loop until Y wraps", inline=True)
comment(0xB1BF, "Print ')\\rDir. ' header for the directory listing",
    inline=True)
comment(0xB1C9, "X=&11: filename offset in TX buffer", inline=True)
comment(0xB1CB, "Print 10-char filename", inline=True)
comment(0xB1CE, "Print inline 'attr-bits' fragment", inline=True)
comment(0xB1DB, "X=&1B: extension offset in TX buffer", inline=True)
comment(0xB1DD, "Print 10-char extension", inline=True)
comment(0xB1E0, "Print newline", inline=True)
comment(0xB1E3, "Pop saved counter", inline=True)
comment(0xB1E4, "Store as fs_lib_flags", inline=True)
comment(0xB1E7, "Save Y as hazel_txcb_flag (next-entry index)", inline=True)
comment(0xB1EA, "Save Y as fs_work_4", inline=True)
comment(0xB1EC, "Load fs_work_5 (page count)", inline=True)
comment(0xB1EE, "Store at hazel_txcb_count", inline=True)
comment(0xB1F1, "Load fs_work_7", inline=True)
comment(0xB1F3, "Store at hazel_txcb_data", inline=True)
comment(0xB1F6, "X=3: TX[3] is start of arg buffer", inline=True)
comment(0xB1F8, "Copy filename arg", inline=True)
comment(0xB1FB, "Y=3: cmd code 3 (catalog)", inline=True)
comment(0xB1FD, "Send TX request", inline=True)
comment(0xB200, "X advances entry counter", inline=True)
comment(0xB201, "Read reply status", inline=True)
comment(0xB204, "Z: empty reply -> exit cat", inline=True)
comment(0xB206, "Push reply status", inline=True)
comment(0xB207, "Advance Y", inline=True)
comment(0xB208, "Read entry byte from hazel_txcb_data+Y", inline=True)
comment(0xB20B, "Bit 7 clear: keep scanning", inline=True)
comment(0xB20D, "Store with high-bit clear at hazel_txcb_lib+Y", inline=True)
comment(0xB210, "Print column separator", inline=True)
comment(0xB213, "Pop saved status", inline=True)
comment(0xB214, "Clear carry for the ADC below", inline=True)
comment(0xB215, "Add fs_work_4 (page accumulator)", inline=True)
comment(0xB217, "New index", inline=True)
comment(0xB218, "Non-zero: continue paging", inline=True)

# fsreply_2_copy_handles partial gap-fill.
comment(0xA70B, "X=&11: CMOS RAM byte index", inline=True)
comment(0xA70D, "Read CMOS &11 via osbyte_a1", inline=True)
comment(0xA710, "Result to A", inline=True)
comment(0xA711, "Mask bit 1 (auto-CLI flag)", inline=True)
comment(0xA713, "Bit clear: skip auto-CLI", inline=True)
comment(0xA715, "X = lo of fsreply_2_skip_handles (boot-cmd string ptr)", inline=True)
comment(0xA717, "Y = hi of fsreply_2_skip_handles", inline=True)
comment(0xA719, "OSCLI to execute boot command", inline=True)
comment(0xA71C, "Pop saved A", inline=True)
comment(0xA71D, "Compare with 2", inline=True)
comment(0xA71F, "Below: skip making FS permanent", inline=True)
comment(0xA721, "OSBYTE &6D: make filing system permanent", inline=True)
comment(0xA75F, "Read hazel_fs_flags (boot-state flag)", inline=True)
comment(0xA762, "Z: take boot_load_cmd path", inline=True)

# select_fs_via_cmd_net_fs gap-fill (mid-body OSWORD PB save/restore).
comment(0x8B5A, "Read osword_pb_ptr_hi", inline=True)
comment(0x8B5C, "Push it", inline=True)
comment(0x8B5D, "Read osword_pb_ptr lo", inline=True)
comment(0x8B5F, "Push it", inline=True)
comment(0x8BAE, "Set bit 0 of fs_flags (= NFS active)", inline=True)
comment(0x8BB1, "Issue Master service call &0F (vector update)", inline=True)
comment(0x8BB4, "Pop saved osword_pb_ptr lo", inline=True)
comment(0x8BB5, "Restore osword_pb_ptr lo", inline=True)
comment(0x8BB7, "Pop saved osword_pb_ptr hi", inline=True)
comment(0x8BB8, "Restore osword_pb_ptr hi", inline=True)
comment(0x8BBA, "Return", inline=True)

# loop_next_char gap-fill (print_inline body).
comment(0x926B, "Z clear: continue with this char", inline=True)
comment(0x926D, "Z set (CR): increment fs_crflag", inline=True)
comment(0x9273, "Read fs_error_ptr (saved across OSASCI)", inline=True)
comment(0x9275, "Push it", inline=True)
comment(0x9276, "Read fs_crflag", inline=True)
comment(0x9278, "Push it", inline=True)
comment(0x927E, "Pop saved fs_crflag", inline=True)
comment(0x927F, "Restore fs_crflag", inline=True)
comment(0x9281, "Pop saved fs_error_ptr", inline=True)
comment(0x9282, "Restore fs_error_ptr", inline=True)
comment(0x9284, "Loop back", inline=True)

# osword_13_set_station gap-fill.
comment(0xA9E9, "Step back to previous byte", inline=True)
comment(0xAA03, "Entry index to A", inline=True)
comment(0xAA04, "Mask bit 5", inline=True)
comment(0xAA0F, "Clear carry", inline=True)
comment(0xAA5E, "A = Y for store", inline=True)
comment(0xAA62, "Decrement entry counter", inline=True)
comment(0xAA59, "A=8: fs_flags bit 3 (FS-error pending)", inline=True)
comment(0xAA5B, "Clear FS-error-pending flag", inline=True)
comment(0xAA5F, "Store updated status into hazel_fcb_status[X]",
    inline=True)
comment(0xAA63, "Loop while X >= 0 (scan all FCBs)", inline=True)
comment(0xAA65, "A=&0E: status flag value", inline=True)
comment(0xAA67, "Test fs_flags bits 1..3", inline=True)
comment(0xAA6A, "Non-zero: skip the FS-active set", inline=True)
comment(0xAA6C, "A=&40: FS-active flag bit", inline=True)
comment(0xAA71, "Return -- FCB-status update complete", inline=True)
comment(0xAA6E, "Set FS-active flag (bit 6 of fs_flags)", inline=True)

# match_fs_cmd gap-fill.
comment(0xA45C, "Push for save/restore", inline=True)
comment(0xA481, "(continued)", inline=True)
comment(0xA482, "(continued)", inline=True)
comment(0xA486, "Push for stack-based comparison", inline=True)
comment(0xA494, "A = matched offset, save in Y", inline=True)
comment(0xA497, "Dispatch helper (sep_table_data path)", inline=True)
comment(0xA49A, "Check separator flag (zp_0026)", inline=True)
comment(0xA49E, "Effective unconditional jump", inline=True)

# fscv_0_opt_entry gap-fill.
comment(0xA0E1, "X=&11: CMOS RAM byte index", inline=True)
comment(0xA0E7, "Read CMOS &11 result to A", inline=True)
comment(0xA0EC, "Push CMOS value", inline=True)
comment(0xA0F0, "Value to X", inline=True)
comment(0xA0F2, "Shift CMOS bits", inline=True)
comment(0xA0F8, "Pop saved value", inline=True)

# osword_10_handler gap-fill.
comment(0xA919, "Read net_rx_ptr_hi", inline=True)
comment(0xA942, "Divide by 2", inline=True)
comment(0xA944, "Index to X", inline=True)
comment(0xA94D, "Step to next slot", inline=True)
comment(0xA951, "Found slot index", inline=True)
comment(0xA95B, "Back up scan", inline=True)
comment(0xA960, "Y=1: result-byte offset", inline=True)
comment(0xA96C, "For the ADC chain", inline=True)

# netv_handler entry preamble.
comment(0xAD13, "Restore flags", inline=True)
comment(0xAD14, "Return", inline=True)

# store_ws_page_count gap-fill.
comment(0x8EF1, "Push for save", inline=True)
comment(0x8EFC, "Pop -- save Y temporarily", inline=True)
comment(0x8F01, "Push restored value", inline=True)
comment(0x8F02, "Mask bit 7 (workspace flag)", inline=True)
comment(0x8F0A, "Read &FE28 (Master ROMSEL shadow)", inline=True)
comment(0x8F0D, "Pop saved Y", inline=True)
comment(0x8F0E, "Increment for next page", inline=True)
comment(0x8F0F, "Return", inline=True)

# ex_print_col_sep gap-fill.
comment(0xB2F5, "Non-zero: take col_sep_print_char tail", inline=True)
comment(0xB2F7, "A=&0D: CR character", inline=True)
comment(0xB2F9, "Print CR (no spool)", inline=True)
comment(0xB2FC, "Next entry", inline=True)
comment(0xB2FD, "Loop until X wraps", inline=True)

# check_credits_easter_egg / cmd_iam_save_ctx prologue.
comment(0x8D24, "Y = ws_page (workspace high page)", inline=True)
comment(0x8D87, "Save caller Y", inline=True)
comment(0x8D88, "Read fs_last_byte_flag (work_bd)", inline=True)
comment(0x8D8A, "Read fs_options (work_bb)", inline=True)
comment(0x8D8C, "Read fs_block_offset (work_bc)", inline=True)
comment(0x8D8E, "Push fs_last_byte_flag for restore on return",
    inline=True)

# update_fcb_flag_bits gap-fill.
comment(0xAB43, "A = caller X", inline=True)
comment(0xAB45, "X=&0F: scan all 16 FCB slots", inline=True)
comment(0xAB4B, "Shift bit into carry for test", inline=True)
comment(0xAB62, "Decrement FCB index", inline=True)
comment(0xAB67, "Return", inline=True)

# cmd_net_fs prologue (RTS terminator + cmd_net_check_hw entry).
comment(0x8B38, "Return -- last instruction of cmd_net_fs body", inline=True)
comment(0x8B39, "A=&20: ADLC IRQ-status mask (CR2 bit 5)", inline=True)
comment(0x8B3B, "Read ADLC CR2/SR2 (&FEA1)", inline=True)
comment(0x8B3E, "Z set (no carrier): proceed to FS-select", inline=True)
comment(0x8B40, "A=3: 'ROM has no NFS' error code", inline=True)
comment(0x8B42, "Raise via build_simple_error (never returns)", inline=True)

# osbyte_a2 region (&9612..&973C). The osbyte_a2 stub itself (&9612-&8)
# is followed by recovered code reached only via PHA/PHA/RTS dispatch:
#   &9619: bit-0 SET helper (no static callers found -- likely 4.18
#                            carry-over from before CMOS protection moved)
#   &9623: bit-0 CLEAR helper (ditto)
#   &9630: svc_29_status (svc_dispatch idx &18)
#   &965F/&9670: print_ps_address / print_fs_address -- helpers shared
#               with svc_29_status
#   help_dispatch_setup: dispatch tail
#   &969A: match_on_suffix (svc_dispatch idx &0F)
#   &96BB..&973C: filename-walker + *TYPE-style file-print loop reached
#                 via match_on_suffix's tail
comment(0x9612, "A=&A2: write CMOS RAM byte via OSBYTE", inline=True)
comment(0x9617, "BRA -91 -> bra_target_svc_return", inline=True)

# CMOS bit-0 SET helper (&9619). Reads CMOS &11, sets bit 0, falls
# into the osbyte_a2_value_tya shared tail to write back.
comment(0x9619, "X=&11: CMOS RAM byte index", inline=True)
comment(0x961B, "Read CMOS &11 via osbyte_a1", inline=True)
comment(0x961E, "A = current CMOS &11 value", inline=True)
comment(0x961F, "Set bit 0 in A", inline=True)
comment(0x9621, "BRA osbyte_a2_value_tya: shared write-back tail", inline=True)

# CMOS bit-0 CLEAR helper (&9623). Reads CMOS &11, clears bit 0,
# falls through to osbyte_a2_value_tya.
comment(0x9623, "X=&11: CMOS RAM byte index", inline=True)
comment(0x9625, "Read CMOS &11 via osbyte_a1", inline=True)
comment(0x9628, "A = current CMOS &11 value", inline=True)
comment(0x9629, "Clear bit 0 in A", inline=True)

# Shared CMOS write-back tail (osbyte_a2_value_tya).
comment(0x962B, "New CMOS value to Y", inline=True)
comment(0x962C, "X=&11: CMOS RAM byte index", inline=True)
comment(0x962E, "BRA osbyte_a2: write CMOS &11 = Y", inline=True)

# svc_29_status (&9630): scans (os_text_ptr),Y for CR; if
# at end-of-line, prints all CMOS settings (port number / station
# / network / FS-state) and returns; otherwise jumps to the
# argument-parser at help_dispatch_setup.
comment(0x9630, "Read first command-line char", inline=True)
comment(0x9632, "Is it CR (no argument)?", inline=True)
comment(0x9634, "Non-CR: parse the argument at help_dispatch_setup", inline=True)
comment(0x9636, "Print 'FS       ' header", inline=True)
comment(0x9639, "Print FS network.station from CMOS &02/&01", inline=True)
comment(0x963C, "Print 'PS       ' header", inline=True)
comment(0x963F, "Print PS network.station from CMOS &04/&03", inline=True)
comment(0x9642, "X=&11: CMOS RAM byte index", inline=True)
comment(0x9644, "Read CMOS &11 (FS state)", inline=True)
comment(0x9647, "A = CMOS &11", inline=True)
comment(0x9648, "Mask bit 0 (FS-active flag)", inline=True)
comment(0x964A, "Bit set: skip 'No ' prefix", inline=True)
comment(0x964C, "Print 'No ' prefix via inline", inline=True)
comment(0x9652, "Bit-7 terminator + resume", inline=True)
comment(0x9653, "Print 'Space        ' or similar via inline", inline=True)
comment(0x965C, "Bit-7 terminator + resume opcode", inline=True)

# print_num_no_leading siblings (&965F, &9670). Each loads a
# specific CMOS index and prints the value, then prints a separator,
# then falls into the next.
comment(0x965F, "X=4: CMOS RAM byte 4 (network number)", inline=True)
comment(0x9661, "Read CMOS &04 via osbyte_a1", inline=True)
comment(0x9664, "A = CMOS &04 value", inline=True)
comment(0x9665, "Print as decimal (no leading zeros)", inline=True)
comment(0x9668, "Print '.' separator via inline", inline=True)
comment(0x966C, "X=3: CMOS &03 (PS station)", inline=True)
comment(0x966E, "BRA print_cmos_decimal_nl: shared print-and-trail", inline=True)

comment(0x9670, "X=2: CMOS &02 (FS network)", inline=True)
comment(0x9672, "Read CMOS &02 via osbyte_a1", inline=True)
comment(0x9675, "A = CMOS &02", inline=True)
comment(0x9676, "Print as decimal", inline=True)
comment(0x9679, "Print '.' separator via inline", inline=True)
comment(0x967D, "X=1: CMOS &01 (port)", inline=True)
comment(0x967F, "Read CMOS X via osbyte_a1", inline=True)
comment(0x9682, "A = CMOS value", inline=True)
comment(0x9683, "Print as decimal", inline=True)
comment(0x9689, "JMP svc_return_unclaimed (release service call)", inline=True)

# Argument-parsing dispatcher (help_dispatch_setup). When the user supplied
# arg(s) past the leading CR, X=&BD selects the first action.
comment(0x968C, "X=&BD: setup index for the dispatch chain", inline=True)
comment(0x968E, "JMP svc4_dispatch_lookup -- shared parser dispatch", inline=True)

# match_on_suffix (&969A): copies os_text_ptr to (work_ae), then
# walks the 3-byte 'ON ' pattern at on_suffix_pattern, EOR-comparing each byte
# (with bit-5 mask = case-insensitive) against the next chars in
# the user's text. Returns to match_char_process on match (= execute help
# topic), to match_char_loop_cmp on no-match (= return without help).
comment(0x969B, "Copy os_text_ptr lo to work_ae", inline=True)
comment(0x969D, "Store -> work_ae", inline=True)
comment(0x969F, "Copy os_text_ptr hi", inline=True)
comment(0x96A1, "Store -> addr_work", inline=True)
comment(0x96A3, "Restore caller Y", inline=True)
comment(0x96A4, "Save Y again (preserve across loop)", inline=True)
comment(0x96A5, "X=0: pattern offset starts at 0", inline=True)
comment(0x96A7, "Read text byte at (work_ae)+Y", inline=True)
comment(0x96AC, "Mask bit 5 -- case-insensitive comparison", inline=True)
comment(0x96AE, "Equal: continue checking pattern", inline=True)
comment(0x96B1, "Return (no match)", inline=True)
comment(0x96B2, "Advance text index", inline=True)
comment(0x96B3, "Advance pattern index", inline=True)
comment(0x96B4, "Done all 3 chars?", inline=True)
comment(0x96B6, "No: continue", inline=True)
comment(0x96B8, "Match: save Y", inline=True)
comment(0x96B9, "Ensure NFS is selected (auto-select if needed)", inline=True)

# Filename-walker (&96BD..&96D2). After 'ON ' match, scan past
# space-or-CR to find the start of the help-topic filename.
comment(0x96BD, "Advance Y to next char", inline=True)
comment(0x96BE, "Read text byte at (work_ae)+Y", inline=True)
comment(0x96C0, "Is it CR (end-of-line)?", inline=True)
comment(0x96C2, "Yes: nothing to load -> return", inline=True)
comment(0x96C4, "Is it space?", inline=True)
comment(0x96C6, "No: continue scanning past non-space", inline=True)
comment(0x96C8, "Skip space char", inline=True)
comment(0x96C9, "Read next byte", inline=True)
comment(0x96CB, "Is it space?", inline=True)
comment(0x96CD, "Yes: keep skipping spaces", inline=True)
comment(0x96CF, "Is it CR?", inline=True)
comment(0x96D1, "Yes: nothing past spaces -> return", inline=True)

# Build the load-command at hazel_txcb_data: prefix from &968F template +
# topic from text buffer.
comment(0x96D3, "Save Y as hazel_txcb_data (cmd buffer ptr)", inline=True)
comment(0x96D6, "Save Y as hazel_txcb_flag (cmd flag)", inline=True)
comment(0x96D9, "X=1: index for template walk", inline=True)
comment(0x96DB, "Advance template index", inline=True)
comment(0x96DC, "Read template byte from help_topic_template+X", inline=True)
comment(0x96DF, "Store at hazel_txcb_data+X", inline=True)
comment(0x96E2, "Compare with '.' (template terminator)", inline=True)
comment(0x96E4, "Not '.': continue copying template", inline=True)
comment(0x96E6, "Save text-buffer index", inline=True)

# Append topic name (until space or CR) onto the load-command.
comment(0x96E7, "Advance dest index", inline=True)
comment(0x96E8, "Read topic char at (work_ae),Y", inline=True)
comment(0x96EA, "Advance source", inline=True)
comment(0x96EB, "Store at hazel_txcb_data+X", inline=True)
comment(0x96EE, "CR? (end of name)", inline=True)
comment(0x96F0, "Yes: take start_help_file_load path (open file)", inline=True)
comment(0x96F2, "Space? (terminator)", inline=True)
comment(0x96F4, "No: continue copying", inline=True)
comment(0x96F6, "A=&0D: replace space with CR", inline=True)
comment(0x96F8, "BRA back to store the CR", inline=True)

# Open-and-print-file path (start_help_file_load..&973C). Set up CMOS-bit flag,
# call send_open_file_request, read bytes via OSBGET, write
# via OSWRCH; close on EOF; respect Escape.
comment(0x96FA, "Account for last char", inline=True)
comment(0x96FB, "Read fs_lib_flags (hazel_fs_lib_flags)", inline=True)
comment(0x96FE, "Preserve low bits, clear high bits", inline=True)
comment(0x9700, "Set bit 7 (load-pending flag)", inline=True)
comment(0x9702, "Store back to fs_lib_flags", inline=True)
comment(0x9705, "A=&40: load mode flag", inline=True)
comment(0x9707, "Store as fs_last_byte_flag", inline=True)
comment(0x9709, "Open the help-topic file", inline=True)
comment(0x970D, "Y=0: open failed -> return", inline=True)
comment(0x9712, "C clear: byte read OK -> print it", inline=True)
comment(0x9714, "A=0: OSFIND close mode", inline=True)
comment(0x971C, "BRA back to match_char_process (return)", inline=True)
comment(0x9720, "Bit 7 clear: not escaping, continue", inline=True)
comment(0x9722, "Escape: jump to error path escape_error_close", inline=True)
comment(0x9725, "Compare with CR", inline=True)
comment(0x9727, "Z: CR -- handle line-end (newline)", inline=True)
comment(0x972C, "BRA back to read next byte", inline=True)
comment(0x972E, "Save file handle", inline=True)
comment(0x972F, "A=&DA: OSBYTE &DA = read paged-mode flag", inline=True)
comment(0x9731, "Issue OSBYTE &DA (X=0)", inline=True)
comment(0x9734, "Restore handle", inline=True)
comment(0x9735, "Result to A", inline=True)
comment(0x9736, "Non-zero: paged mode pending -> handle Escape", inline=True)
comment(0x973B, "BRA back to read next byte", inline=True)

# osword_12_handler tail (PHA/PHA/RTS dispatcher).
comment(0xA99F, "Read dispatch hi from osword_13_dispatch_hi+X", inline=True)
comment(0xA9A2, "Push hi for RTS dispatch", inline=True)
comment(0xA9A3, "Read dispatch lo from osword_13_dispatch_lo+X", inline=True)
comment(0xA9A6, "Push lo for RTS dispatch", inline=True)
comment(0xA9A7, "RTS -> dispatched OSWORD &13 sub-handler", inline=True)

# netv_print_data gap-fill.
comment(0xAE71, "Non-zero: nothing to print, return", inline=True)
comment(0xAE74, "Step counter back", inline=True)
comment(0xAE77, "Read MOS stack frame", inline=True)
comment(0xAE85, "C set: return path", inline=True)
comment(0xAE8F, "Print accumulated spool data", inline=True)

# lang_2_save_palette_vdu PHA/PLA save/restore frame.
comment(0xB01C, "Save state byte", inline=True)
comment(0xB02F, "Save another byte", inline=True)
comment(0xB03C, "Restore inner saved", inline=True)
comment(0xB052, "Restore outer saved", inline=True)
comment(0xB05C, "Restore final saved", inline=True)

# cmd_ps body gap-fill.
comment(0xB3BC, "Read fs_options[Y]", inline=True)
comment(0xB3C6, "C clear: save ptr and continue", inline=True)
comment(0xB3C8, "A = current Y", inline=True)

# cmd_iam tail.
comment(0x8DA0, "Clear hazel_fs_pending_state (connection-attempt flag)", inline=True)
comment(0x8DA5, "Pop and discard saved fs_last_byte_flag", inline=True)
comment(0x8DA6, "Set up transfer parameters", inline=True)

# process_spool_data (&AEB8): copy workspace state into the TX
# control block, send a disconnect reply if the previous transfer
# still requires acknowledgment, then drop into the spool output
# sequence by setting up and sending the pass-through TX buffer.
comment(0xAEB8, "Y=8: buf_start_lo TXCB offset", inline=True)
comment(0xAEBA, "Load current spool-buffer index", inline=True)
comment(0xAEBD, "Store at workspace+8 (buf_start_lo)", inline=True)
comment(0xAEBF, "Load RX page (= net_rx_ptr_hi)", inline=True)
comment(0xAEC2, "Store at workspace+9 (buf_start_hi)", inline=True)
comment(0xAEC4, "Y=5: alt buf_start_hi offset", inline=True)
comment(0xAEC6, "Store at workspace+5 (also buf-start hi)", inline=True)
comment(0xAEC8, "Y=&0B: TXCB offset for following copy", inline=True)
comment(0xAECA, "X=&26: template offset for vclr region", inline=True)
comment(0xAECC, "Copy 12-byte ws-template region (V-clear)", inline=True)
comment(0xAECF, "Step back to offset &0A", inline=True)
comment(0xAED0, "Read shadow ACR (ws_0d6a)", inline=True)
comment(0xAED4, "Shift bit 7 into C", inline=True)
comment(0xAED6, "Toggle bit 7", inline=True)
comment(0xAED8, "Store updated shadow back to ws_0d6a", inline=True)
comment(0xAEDB, "Shift bit 0 into bit 1", inline=True)
comment(0xAEDC, "Store at workspace+&0A", inline=True)
comment(0xAEDE, "Read vdu_status", inline=True)
comment(0xAEE1, "Clear bit 0 of vdu_status", inline=True)
comment(0xAEE3, "Store updated", inline=True)
comment(0xAEE5, "Y=&21: spool_buf_idx reset value", inline=True)
comment(0xAEE7, "Reset spool_buf_idx", inline=True)
comment(0xAEEA, "A=0", inline=True)
comment(0xAEED, "Y = workspace high page", inline=True)
comment(0xAEEF, "Re-enable IRQs (NMI window over)", inline=True)
comment(0xAEF0, "Send disconnect reply", inline=True)
comment(0xAEF3, "Restore vdu_status", inline=True)
comment(0xAEF4, "Restore vdu_status", inline=True)
comment(0xAEF6, "Return", inline=True)

# check_spool_state (&AEF7): test bit 0 of ws_0d6a (shadow ACR);
# if clear, JMP back to process_spool_data; otherwise send the
# pass-through TX buffer.
comment(0xAEF7, "Read shadow ACR", inline=True)
comment(0xAEFA, "Shift bit 0 into C", inline=True)
comment(0xAEFB, "C clear: re-process spool data", inline=True)
comment(0xAEFD, "Read vdu_status", inline=True)
comment(0xAF00, "Clear bit 0 of vdu_status", inline=True)
comment(0xAF02, "Store updated", inline=True)
comment(0xAF04, "A=&14: TX command byte", inline=True)
comment(0xAF06, "Save TX command", inline=True)
comment(0xAF07, "X=&0B: tx_econet_txcb_template offset", inline=True)
comment(0xAF09, "Y=&2C: dest TXCB offset", inline=True)
comment(0xAF0B, "Read template byte at tx_econet_txcb_template+X", inline=True)
comment(0xAF0E, "Store at (net_rx_ptr)+Y", inline=True)
comment(0xAF10, "Decrement Y", inline=True)
comment(0xAF11, "Decrement X", inline=True)
comment(0xAF12, "Loop until X wraps below 0", inline=True)
comment(0xAF14, "Store X (= &FF) as need_release_tube", inline=True)
comment(0xAF16, "Y=2: workspace offset for source", inline=True)
comment(0xAF18, "Read (nfs_workspace)+2", inline=True)
comment(0xAF1B, "Y=3", inline=True)
comment(0xAF1C, "Read (nfs_workspace)+3", inline=True)
comment(0xAF1E, "Y=&24: dest offset in TXCB", inline=True)
comment(0xAF20, "Store at (net_rx_ptr)+Y", inline=True)
comment(0xAF22, "Y=&23", inline=True)
comment(0xAF24, "Store at (net_rx_ptr)+Y", inline=True)
comment(0xAF26, "X=&0B: rx_palette_txcb_template offset", inline=True)
comment(0xAF28, "Y=&0B: dest offset in workspace", inline=True)
comment(0xAF2A, "Read template byte at rx_palette_txcb_template+X", inline=True)
comment(0xAF2D, "Compare with &FD (skip-byte marker)", inline=True)
comment(0xAF2F, "Equal: skip this byte", inline=True)
comment(0xAF31, "Compare with &FC (page-ptr marker)", inline=True)
comment(0xAF33, "Not &FC: store as-is", inline=True)
comment(0xAF35, "&FC: substitute net_rx_ptr_hi", inline=True)
comment(0xAF37, "Store at (nfs_workspace)+Y", inline=True)
comment(0xAF39, "Next dest", inline=True)
comment(0xAF3A, "Next source", inline=True)
comment(0xAF3B, "Loop until X wraps", inline=True)
comment(0xAF3D, "A=&21: TXCB control byte", inline=True)
comment(0xAF3F, "Store at net_tx_ptr lo", inline=True)
comment(0xAF41, "Read net_rx_ptr_hi", inline=True)
comment(0xAF43, "Store as net_tx_ptr hi", inline=True)
comment(0xAF45, "Set up the pass-through TX buffer", inline=True)
comment(0xAF48, "Send the TX packet", inline=True)
comment(0xAF4B, "A=0: clear net_tx_ptr lo", inline=True)
comment(0xAF4D, "Store -> net_tx_ptr lo", inline=True)
comment(0xAF4F, "Read nfs_workspace_hi", inline=True)
comment(0xAF51, "Store -> net_tx_ptr hi", inline=True)
comment(0xAF53, "Wait for TX ack", inline=True)
comment(0xAF56, "Y=&2D: spool result-byte offset", inline=True)
comment(0xAF58, "Read result via (net_rx_ptr)+Y", inline=True)
comment(0xAF5A, "Z: success path", inline=True)
comment(0xAF5C, "Compare with 3 (retry threshold)", inline=True)
comment(0xAF5E, "Other: take retry path", inline=True)
comment(0xAF60, "Discard saved TX cmd", inline=True)
comment(0xAF61, "Restore vdu_status", inline=True)
comment(0xAF62, "Restore vdu_status", inline=True)
comment(0xAF64, "A=0: success-return code", inline=True)
comment(0xAF66, "Append byte to RX buffer", inline=True)
comment(0xAF69, "Recurse: process_spool_data", inline=True)
comment(0xAF6C, "Read shadow ACR", inline=True)
comment(0xAF6F, "Mask high nibble", inline=True)
comment(0xAF71, "Store updated shadow", inline=True)
comment(0xAF74, "Return", inline=True)
comment(0xAF75, "Save retry counter", inline=True)
comment(0xAF76, "Pop saved TX cmd", inline=True)
comment(0xAF77, "Set carry", inline=True)
comment(0xAF78, "Decrement retry", inline=True)
comment(0xAF7A, "Non-zero: retry from start_spool_retry", inline=True)
comment(0xAF7C, "Check the saved retry counter", inline=True)
comment(0xAF7E, "Not 1: take printer_busy_msg path", inline=True)

# handle_spool_ctrl_byte (&AE9D): branch on RX cmd byte (cb_fill /
# cb_skip / cb_stop) deciding what to do with the next spool entry.
comment(0xAEA2, "Equal: take fill path", inline=True)
comment(0xAEAC, "Stop: process_spool_data and return", inline=True)
comment(0xAE9E, "C clear: take check_spool_state path", inline=True)
comment(0xAEA3, "Save state byte", inline=True)
comment(0xAEAD, "A=3: spool-data result code", inline=True)
comment(0xAEAF, "Append result to RX buffer", inline=True)
comment(0xAEB2, "Process the accumulated spool data", inline=True)
comment(0xAEB5, "Reset spool buffer state", inline=True)

# lang_2_save_palette_vdu (&B01A): save the current MOS palette
# (16 entries) and VDU state into the workspace TX buffer for
# forwarding back to the remote. Uses osword_flag as a counter.
comment(0xB01A, "Read osword_flag (preserved across the dispatch)", inline=True)
comment(0xB01D, "A=&E9: workspace start lo for palette save", inline=True)
comment(0xB01F, "Store as nfs_workspace lo", inline=True)
comment(0xB021, "Y=0", inline=True)
comment(0xB023, "Reset osword_flag = 0", inline=True)
comment(0xB025, "Read vdu_screen_mode (MOS state byte)", inline=True)
comment(0xB028, "Store at (nfs_workspace)+0", inline=True)
comment(0xB02A, "Advance nfs_workspace lo", inline=True)
comment(0xB02C, "Read vdu_display_start_hi (next MOS byte)", inline=True)
comment(0xB031, "Store at (nfs_workspace)", inline=True)
comment(0xB033, "Read updated nfs_workspace lo", inline=True)
comment(0xB035, "Read nfs_workspace hi", inline=True)
comment(0xB037, "A=&0B: OSWORD &0B = read palette entry", inline=True)
comment(0xB03D, "Y=0", inline=True)
comment(0xB03F, "Store palette result at workspace", inline=True)
comment(0xB042, "Re-read palette result", inline=True)
comment(0xB045, "Read updated workspace lo", inline=True)
comment(0xB047, "Advance workspace", inline=True)
comment(0xB049, "Increment osword_flag (palette index)", inline=True)
comment(0xB04C, "Read updated osword_flag", inline=True)
comment(0xB04E, "Compare with &F9 (last palette entry)", inline=True)
comment(0xB050, "Not done: loop", inline=True)
comment(0xB053, "Reset osword_flag = 0 after palette loop", inline=True)
comment(0xB055, "Advance workspace", inline=True)
comment(0xB057, "Serialise the next palette entry", inline=True)
comment(0xB05A, "Advance workspace", inline=True)
comment(0xB05D, "Save osword_flag", inline=True)

# serialise_palette_entry (&B066): read MOS palette entry slot
# (controlled by vdu_mode) and append to workspace TX buffer.
comment(0xB066, "Read vdu_mode (current palette index)", inline=True)
comment(0xB069, "Mark as palette entry", inline=True)
comment(0xB06B, "Store at (nfs_workspace)+Y", inline=True)
comment(0xB06D, "Read vdu_mode", inline=True)
comment(0xB070, "Advance workspace", inline=True)
comment(0xB072, "A = current Y (= 0)", inline=True)
comment(0xB073, "Store 0 at (nfs_workspace)+Y", inline=True)
comment(0xB075, "Read lookup byte from read_osbyte_table+X", inline=True)
comment(0xB078, "X=0: indexed-indirect mode", inline=True)
comment(0xB07A, "Advance workspace", inline=True)
comment(0xB07C, "Store at (nfs_workspace,X)", inline=True)
comment(0xB07E, "Read OSBYTE result via x=0 helper", inline=True)

# read_osbyte_to_ws (&B083): issue OSBYTE A from read_osbyte_return[Y] and store
# the result at the next workspace slot. Used for batched OSBYTE
# state-saves during the palette/VDU snapshot.
comment(0xB083, "Y = osword_flag (OSBYTE-table index)", inline=True)
comment(0xB085, "Increment osword_flag for next call", inline=True)
comment(0xB087, "Advance nfs_workspace", inline=True)
comment(0xB089, "Load OSBYTE number from read_osbyte_return+Y", inline=True)
comment(0xB08C, "Y=&FF -- OSBYTE arg (read mode)", inline=True)
comment(0xB08E, "Issue OSBYTE", inline=True)
comment(0xB091, "Result to A", inline=True)
comment(0xB092, "X=0: indexed-indirect mode", inline=True)
comment(0xB094, "Store at (nfs_workspace,X)", inline=True)
comment(0xB096, "Return", inline=True)
comment(0xB0A0, "JMP (cdir_unused_dispatch_table,X) -- never executed; see cmd_cdir", inline=True)

# Final small-routine sweep: the long tail of 1-4 uncommented items
# spread across mid-tier helpers.
comment(0xA83B, "BRA osword_store_svc_state -- skip past 22-byte caller-cleanup frame", inline=True)
comment(0xA84A, "Read svc_state[Y] (frame slot)", inline=True)
comment(0xA854, "Next slot", inline=True)
comment(0xA855, "Loop until Y wraps", inline=True)

comment(0x90C7, "Print 'Station ' inline string", inline=True)
comment(0x90D9, "Y=1: PB station-byte offset", inline=True)
comment(0x90DB, "Read RX[1] = station number", inline=True)
comment(0x90DD, "Print as decimal (no leading zeros)", inline=True)

comment(0x8BC8, "Save X (cmd-table offset)", inline=True)
comment(0x8BCA, "Print the version-banner header", inline=True)
comment(0x8BC9, "Save Y (text-pointer offset)", inline=True)

comment(0xB2DB, "X=0: scan from start of TX entry", inline=True)
comment(0xB2DD, "Read entry byte at hazel_txcb_data+X", inline=True)
comment(0xB2E0, "Bit 7 set: end-of-entries -> return", inline=True)
comment(0xB2E2, "Non-printable: take CR-newline path at col_sep_print_cr", inline=True)

comment(0xAF80, "A=&A6: 'Printer busy' error code", inline=True)
comment(0xAF82, "Raise via error_inline_log (never returns)", inline=True)
comment(0xAF92, "A=&A7: 'Printer jammed' error code", inline=True)
comment(0xAF94, "Raise via error_inline_log (never returns)", inline=True)

comment(0xA901, "Save caller flags (D may be in any state)", inline=True)
comment(0xA902, "Save A across decimal-mode arithmetic", inline=True)
comment(0xA905, "Enter decimal mode", inline=True)
comment(0xA90E, "Restore caller flags (incl. D)", inline=True)

comment(0xAE94, "Y = spool_buf_idx", inline=True)
comment(0xAE97, "Store A at (net_rx_ptr)+Y", inline=True)
comment(0xAE99, "Advance spool_buf_idx", inline=True)
comment(0xAE9C, "Return", inline=True)

comment(0x9895, "A=&7E: OSBYTE &7E = acknowledge Escape", inline=True)
comment(0x989A, "A=6: error class for 'Escape'", inline=True)
comment(0x989C, "JMP classify_reply_error (never returns)", inline=True)

comment(0x9262, "Store as fs_error_ptr (return-addr saved)", inline=True)
comment(0x9265, "Store as fs_crflag (entry flag)", inline=True)
comment(0x9267, "Y=0: start scanning at offset 0", inline=True)

comment(0x924E, "LSR / LSR / LSR -- shift hi nibble down to lo", inline=True)
comment(0x924F, "(continued)", inline=True)
comment(0x9250, "(continued)", inline=True)

comment(0xABBE, "Advance Y", inline=True)
comment(0xABC7, "Non-zero: take return path", inline=True)
comment(0xABD0, "Return", inline=True)

comment(0xA4DC, "Test fs_flags bit 6", inline=True)
comment(0xA4DF, "Bit 6 set: take fscv_2_star_run", inline=True)
comment(0xA4E1, "Bit 6 clear: raise 'Bad command'", inline=True)

comment(0x987E, "Commit the language-reply state byte", inline=True)
comment(0x9881, "A=0: 'Bad' error code", inline=True)
comment(0x9883, "Raise via error_inline_log (never returns)", inline=True)

comment(0x8088, "Y=1: tx_src_stn offset in NMI block", inline=True)
comment(0x808A, "Read TX source station from (net_rx_ptr)+1", inline=True)
comment(0x808C, "Store as tx_src_stn", inline=True)

# nfs_init_body (&8F38): full ANFS bring-up. Reachable only via
# PHA/PHA/RTS dispatch (svc_dispatch_lo[&16] / hi[&16]). The static
# trigger is OPEN-ISSUES O-1 -- no caller has been identified, but
# the dispatch table entry is real and the body is genuine init code.
comment(0x8F38, "A=0: clear-byte for the next four stores", inline=True)
comment(0x8F3A, "Clear ws_page (workspace page count)", inline=True)
comment(0x8F3C, "Clear tx_complete_flag", inline=True)
comment(0x8F3F, "Y=0: receive-block offset 0 (remote-op flag)",
    inline=True)
comment(0x8F41, "Clear remote-op flag at (net_rx_ptr)+0", inline=True)
comment(0x8F48, "A=&10: fs_flags bit 4 mask "
    "(checks 'workspace already set up')", inline=True)
comment(0x8F43, "Read l028D (current ROM number)", inline=True)
comment(0x8F46, "Non-zero (re-init): take nfs_init_check_fs_flags path", inline=True)
comment(0x8F5B, "Copy initial PS template (1C bytes) into ws", inline=True)
comment(0x8F5E, "X=1: CMOS &01 = port number", inline=True)
comment(0x8F60, "Read CMOS &01", inline=True)
comment(0x8F63, "Store at hazel_fs_station (workspace+0)", inline=True)
comment(0x8F66, "X=2: CMOS &02 = network number", inline=True)
comment(0x8F68, "Read CMOS &02", inline=True)
comment(0x8F6B, "Store at hazel_fs_network", inline=True)
comment(0x8F6E, "X=3: CMOS &03 = FS station", inline=True)
comment(0x8F70, "Read CMOS &03", inline=True)
comment(0x8F73, "A = FS station", inline=True)
comment(0x8F78, "X=4: CMOS &04 = FS network", inline=True)
comment(0x8F7D, "A = FS network", inline=True)
comment(0x8F9A, "X=&11: CMOS &11 (ANFS settings)", inline=True)
comment(0x8F9C, "Read CMOS &11", inline=True)
comment(0x8F9F, "A = settings byte", inline=True)
comment(0x8FA0, "Mask bit 6 (CMOS protection-state flag)", inline=True)
comment(0x8FA2, "Bit clear: skip the &FF substitution", inline=True)
comment(0x8FA4, "A=&FF -- enable protection", inline=True)
comment(0x8FA6, "Set ws_0d68/ws_0d69 pair", inline=True)
comment(0x8FBB, "Read CMOS &00 (= station ID byte)", inline=True)
comment(0x8FBE, "Y (CMOS value) into A", inline=True)
comment(0x8FBF, "Non-zero: station ID valid -> alloc_common_entry",
    inline=True)
comment(0x9000, "INY wrapped past 0 (station=&FF then INY=&00): "
    "report 'CMOS RAM invalid' and default to 1", inline=True)
comment(0x9004, "Y=1: net_rx_ptr offset for station-ID byte", inline=True)
comment(0x9006, "Store station ID into (net_rx_ptr)+1", inline=True)
comment(0x9008, "X=&40: econet_flags init value", inline=True)
comment(0x900A, "Initialise econet_flags", inline=True)
comment(0x901D, "A=3: spool-ctrl byte 'init'", inline=True)
comment(0x901F, "Initialise *SPOOL handle in workspace", inline=True)
comment(0x8FC1, "Print 'Station number in CMOS RAM invalid...' warning", inline=True)
comment(0x8FFB, "A=1: default station ID", inline=True)
comment(0x8FFD, "BRA to alloc_store_station_id with default", inline=True)
comment(0x8FFF, "Check next byte (CMOS station ID hi?)", inline=True)
comment(0x9002, "BRA to alloc_store_station_id (always)", inline=True)
comment(0x900D, "Call cmd_net_fs to select NFS", inline=True)
comment(0x9010, "Z: selection succeeded", inline=True)
comment(0x9012, "A=&10: bit 4 marker for fs_flags", inline=True)
comment(0x9017, "Store updated fs_flags", inline=True)
comment(0x901A, "Initialise ADLC and FILEV/ARGSV/...vectors", inline=True)
comment(0x9022, "Send a bridge-discovery packet and poll", inline=True)
comment(0x9025, "Save current bridge byte", inline=True)
comment(0x9026, "With stored hazel_fs_network (network number)", inline=True)
comment(0x9029, "Different: take verify_copy_station_id path", inline=True)
comment(0x902B, "Same: store as new hazel_fs_network", inline=True)
comment(0x902E, "Y=3: net_rx_ptr offset 3", inline=True)
comment(0x9030, "Store at (net_rx_ptr)+3", inline=True)
comment(0x9032, "Restore saved byte", inline=True)
comment(0x9033, "Y=3: workspace offset", inline=True)
comment(0x9037, "Mismatch: skip store", inline=True)
comment(0x9039, "Match: store at (nfs_workspace)+3", inline=True)
comment(0x903B, "Return", inline=True)

# Final residual gap-fill -- ~80 isolated 1-3-item gaps across
# mid-tier helpers. Mostly stack save/restore frames, OSBYTE A
# loads, and one-line entry stubs.
comment(0x8540, "A=&85: high byte of tx_done_exit-1 (&8581)", inline=True)
comment(0x8BE5, "Y=9: cmd_table_fs sub-table 1 offset", inline=True)
comment(0x8BE7, "Read cmd_table_fs+X (entry name byte)", inline=True)
comment(0x8C32, "Save Y across OS call", inline=True)
comment(0x8CE0, "A=0: clear svc_state marker", inline=True)
comment(0x8CE2, "Store -> svc_state", inline=True)
comment(0x8DE6, "Print byte no-spool", inline=True)
comment(0x8E10, "Print newline no-spool", inline=True)
comment(0x8E98, "X=0: CMOS RAM index 0 (station ID)", inline=True)
comment(0x8E9A, "A=&A1: OSBYTE &A1 = read CMOS RAM", inline=True)
comment(0x8ED2, "X=0: clear OSBYTE X arg", inline=True)
comment(0x8EE1, "Clear svc_state", inline=True)
comment(0x9078, "Close all FCBs (process_all_fcbs)", inline=True)
comment(0x93F2, "X=&20: handle-table base offset", inline=True)
comment(0x93F4, "Y=&2F: handle count + flag", inline=True)
comment(0x93F6, "Return", inline=True)
comment(0x945C, "BRA back to read_filename_char", inline=True)
comment(0x9463, "Save Y on entry", inline=True)
comment(0x988F, "Read escape_flag", inline=True)
comment(0x9891, "Mask with need_release_tube (escape-disable)", inline=True)
comment(0x9893, "Bit 7 clear: not escaping, return", inline=True)
comment(0x995F, "Advance Y", inline=True)
comment(0x9960, "Advance X", inline=True)
comment(0x9961, "Loop until X wraps", inline=True)
comment(0xA3B8, "Print 'File server is ' fragment", inline=True)
comment(0xA5B8, "A=&93: error code 'Bad command'", inline=True)
comment(0xA638, "Find station-bit-3 entry", inline=True)
comment(0xA63E, "Record library station in station table", inline=True)
comment(0xA6D8, "A=&40: protection-level marker", inline=True)
comment(0xA6E4, "Save state", inline=True)
comment(0xA9D6, "Step back", inline=True)
comment(0xAA72, "WS-to-PB direction (read)", inline=True)
comment(0xAA78, "Save A as osword_flag (counter)", inline=True)
comment(0xAA8C, "Next byte", inline=True)
comment(0xAA90, "Return", inline=True)
comment(0xAA96, "A = current byte index", inline=True)
comment(0xAA9A, "WS-to-PB direction", inline=True)
comment(0xAAA0, "Next byte", inline=True)
comment(0xAB68, "Y=1: PB[1] = RX flag location", inline=True)
comment(0xAB8D, "PB-to-WS direction (write)", inline=True)
comment(0xAB93, "Next ctx byte", inline=True)
comment(0xAB9D, "Return", inline=True)
comment(0xAC4B, "Save state", inline=True)
comment(0xAC64, "Next byte", inline=True)
comment(0xAC74, "Y=&20: TXCB offset", inline=True)
comment(0xAC8F, "Read nfs_workspace_hi", inline=True)
comment(0xACF8, "Re-enable IRQs", inline=True)
comment(0xAE5A, "Step counter", inline=True)
comment(0xAE61, "Shift bit 0 into C", inline=True)
comment(0xB05F, "Read saved copy of ws_0d68 from ws_0d69", inline=True)
comment(0xB062, "Store back to ws_0d68", inline=True)
comment(0xB065, "Return", inline=True)
comment(0xB081, "X=0: zero-arg helper entry", inline=True)
comment(0xB357, "Clear owner-only access bits before "
    "checking the URD", inline=True)
comment(0xB35A, "A=&69: 'i' character (info prefix)", inline=True)
comment(0xB35C, "Store 'i' as start of FS command name "
    "in the TX buffer", inline=True)
comment(0xB35F, "A='.': abbreviation terminator", inline=True)
comment(0xB361, "Store '.' as command-name terminator", inline=True)
comment(0xB364, "Save the command-line pointer for the dispatcher",
    inline=True)
comment(0xB367, "Parse the *Info argument from the command line",
    inline=True)
comment(0xB36A, "X=2: TX-buffer offset to copy the arg into "
    "(after 'i.')", inline=True)
comment(0xB36C, "Append parsed argument to the TX command buffer",
    inline=True)
comment(0xB370, "Send the FS command and dispatch the reply",
    inline=True)
comment(0xB36F, "A = next index", inline=True)
comment(0xB4B3, "Return", inline=True)
comment(0xB52A, "Return", inline=True)
comment(0xB831, "Clear tx_buffer_scratch+X scratch", inline=True)
comment(0xB8A7, "Return", inline=True)
comment(0xBB38, "Save X on entry", inline=True)
comment(0xBF9F, "Store as os_text_ptr_hi", inline=True)
comment(0xBFA2, "Store as os_text_ptr lo", inline=True)

# Selective rename of auto-generated cXXXX labels at routine
# junction points where a semantic name aids understanding.
# Originally only the handful below were named; Phase K (see
# PHASE-K-LABEL-RENAME.md) extended this to cover every remaining
# auto-generated lXXXX / cXXXX label so the disassembly has 0
# meaningless hex names.
label(0x8EFE, "set_rom_ws_page")
label(0x8F24, "commit_workspace_pages")
label(0x901A, "complete_nfs_init")
label(0x96FA, "start_help_file_load")
label(0x970F, "loop_print_help_byte")
label(0x972E, "handle_help_paged_mode")
label(0xA0DF, "osopt_check_cmos_protect")
label(0xB625, "loop_pollps_next_slot")

# Phase K (2026-05-02): rename remaining 78 auto-generated labels
# (13 lXXXX + 65 cXXXX). Names devised by examining each in context
# in the ASM output; reusing 4.18 names verbatim where the
# equivalent code survives. Tracked in PHASE-K-LABEL-RENAME.md.
label(0x8032, "irq_check_dispatch")
label(0x8211, "page_boundary_restore")
label(0x8258, "byte_pair_restore")
label(0x8264, "frame_complete_restore")
label(0x842F, "scout_done_restore_x")
label(0x8434, "dispatch_imm_op_fail")
label(0x847E, "tube_overflow_restore")
label(0x8524, "enable_irq_pending")
label(0x881B, "check_fifo_loop")
label(0x8827, "frame_end_restore")
label(0x8922, "shadow_enable_flag")
label(0x8A8D, "restore_rom_slot_entry")
label(0x8ACE, "dispatch_svc_state_check")
label(0x8B5A, "select_fs_cmd_net_fs")
label(0x8C46, "svc4_dispatch_lookup")
label(0x8CBB, "get_ws_page_loop")
label(0x8E7E, "fs_template_done")  # shared RTS at end of copy_template_to_zp;
                                   # also reused by svc_26_close_all_files's BVC
data_banner(0x8E7F, "fs_info_template",
    title="FS-name reply template (11 bytes, byte-reversed)",
    description="""\
Source data for the byte-reverse copy in
[`copy_template_to_zp`](address:8E73). When stored at
`(os_text_ptr),Y` in reverse order the destination reads
`"NET" + 6 spaces + "/" + length-byte 5`, which is the FS name
the ROM reports for service &25 (FS name + info reply).""")
label(0x8F1F, "private_ws_set_bit")
label(0x8F4F, "nfs_init_check_fs_flags")
label(0x8FA6, "init_copy_skip_cmos")
label(0x8FBB, "alloc_post_restore_check")
label(0x8FC1, "alloc_error_overflow")
label(0x8FFF, "alloc_common_entry")
label(0x9004, "alloc_store_station_id")
label(0x9032, "verify_copy_station_id")
label(0x925D, "print_nybble_leading_zero")
label(0x9298, "print_next_string_char")
label(0x92AF, "print_char_terminator")
label(0x9421, "clear_channel_flag")
label(0x95BE, "bra_target_svc_return")
label(0x9653, "parse_object_space_print")
label(0x968C, "help_dispatch_setup")
label(0x9697, "on_suffix_pattern")
label(0x96B0, "match_char_loop_cmp")
label(0x96B2, "match_char_found")
label(0x96BC, "match_char_process")
label(0x971E, "help_print_start")
label(0x9725, "help_print_char_check")
label(0x9827, "scan_channel_store_reply")
label(0x9984, "suffix_copy_loop")
label(0x9A0D, "net_error_close_spool")
label(0xA0CF, "osargs_store_ptr_lo")
label(0xA0DB, "osargs_check_length")
data_banner(0xA103, "cmos_opt_mask_table",
    title="CMOS &11 bit-field masks for OSARGS / *OPT 4 (8 bytes)",
    description="""\
Used by the OSARGS-via-FSCV / *OPT 4 path
([`osopt_check_cmos_protect`](address:A0DF)) to read or update bit
fields inside CMOS RAM byte `&11` (the Econet status byte holding
the auto-boot type and printer/messages flags).

- **Indices 0-3** are extraction masks: `AND CMOS_&11` with
  `&01`, `&02`, `&04`, `&06` returns bit 0, bit 1, bit 2 or
  bits 1+2 respectively.
- **Indices 4-7** are clear masks: `AND CMOS_&11` with `&FD`,
  `&F3`, `&CF`, `&3F` zeroes bits 1, 2-3, 4-5 or 6-7 in turn,
  before OR-ing the new value back in.

A second indexed-base trick reads the same eight bytes through
[`cmos_attr_table`](address:A0FF) (this label - 4): for write
sub-codes 4-7 the read-masks at indices 0-3 (1, 2, 4, 6) double
as the bit-shift counts that left-align the new value into its
target field.""")
# Force per-byte rendering so each AND mask carries an inline comment.
for _i in range(8):
    byte(0xA103 + _i)
del _i
comment(0xA103, "Idx 0: AND mask = &01 (extract CMOS &11 bit 0)",
    inline=True)
comment(0xA104, "Idx 1: AND mask = &02 (extract CMOS &11 bit 1)",
    inline=True)
comment(0xA105, "Idx 2: AND mask = &04 (extract CMOS &11 bit 2)",
    inline=True)
comment(0xA106, "Idx 3: AND mask = &06 (extract CMOS &11 bits 1,2)",
    inline=True)
comment(0xA107, "Idx 4: AND mask = &FD (clear CMOS &11 bit 1)",
    inline=True)
comment(0xA108, "Idx 5: AND mask = &F3 (clear CMOS &11 bits 2,3)",
    inline=True)
comment(0xA109, "Idx 6: AND mask = &CF (clear CMOS &11 bits 4,5)",
    inline=True)
comment(0xA10A, "Idx 7: AND mask = &3F (clear CMOS &11 bits 6,7)",
    inline=True)
label(0xA3E5, "no_station_loop")
label(0xA4A0, "separator_char_table")
label(0xA4FC, "cmd_run_load_mask")
label(0xA5DF, "library_path_string")
label(0xA6FE, "fsreply_2_skip_handles")
label(0xA70B, "fsreply_2_handle_loop")
label(0xA71C, "fsreply_2_store_handle")
label(0xA75B, "boot_prefix_string")
label(0xA75F, "boot_suffix_string")
label(0xA855, "osword_store_svc_state")
label(0xA871, "osword_pb_ready")
label(0xA8E7, "save_txcb_done")
label(0xAF92, "printer_busy_msg")
label(0xB097, "read_osbyte_return")
label(0xB099, "read_osbyte_table")
label(0xB0EE, "cdir_size_done")
# &B0F0 and &B0F1 weren't part of the 27-byte threshold table
# loop above; declare them so the init-data tail also gets rendered
# byte-by-byte with comments. (&B0EE and &B0EF are already covered.)
byte(0xB0F0)
byte(0xB0F1)
comment(0xB0EE, "Index 26: threshold &F6 (246) -- last cdir-size "
    "threshold; doubles as cdir_size_done[0] (unread by init loop)",
    inline=True)
comment(0xB0EF, "cdir_size_done[1] = &FF -> tx_retry_count "
    "(retry counter init)", inline=True)
comment(0xB0F0, "cdir_size_done[2] = &28 -> rx_wait_timeout "
    "(40 retries)", inline=True)
comment(0xB0F1, "cdir_size_done[3] = &0A -> peek_retry_count "
    "(10 retries)", inline=True)
label(0xB185, "cat_after_label_print")
label(0xB29C, "option_offset_table")
label(0xB2F7, "col_sep_eol_check")
label(0xB2F9, "col_sep_print_cr")
label(0xB2FC, "col_sep_print_char")
label(0xB474, "print_ps_padding")
label(0xB56F, "local_net_prefix")
label(0xB6D8, "unprot_clear")
label(0xB6E9, "unprot_check")
label(0xB6EB, "unprot_apply")
label(0xBD2D, "escape_error_close")
label(0xC109, "hazel_exec_addr")

# Phase K2 (2026-05-02): declare 31 routines that py8dis previously
# auto-discovered with sub_cXXXX / loop_cXXXX placeholder names.
# These are JSR targets and routine-shaped branch targets that
# existed in the assembly output but were never declared in the
# driver, so the audit tooling (which only sees declared subs)
# missed them. Names devised by examining each in context.
subroutine(0x8409, "save_acccon_for_shadow_ram",
    title="Save ACCCON across scout-buffer access",
    description="""\
Saves the current [`acccon`](address:FE34) value, sets ACCCON
for the upcoming `(open_port_buf),Y` stores (so writes go to the
right shadow / main RAM bank on the Master 128), performs the
copy, then restores the saved ACCCON before returning. Wraps the
inner copy loop with shadow-RAM gating so scout-buffer writes
land in the caller's address space rather than the FS-private
HAZEL window.""")
label(0x8BEA, "loop_print_cmd_name")
subroutine(0x8DA6, "load_transfer_params",
    title="Set FS transfer parameters via set_xfer_params",
    description="""\
3-byte trampoline that calls
[`set_xfer_params`](address:93D7) and falls through into
[`cmd_pass`](address:8DD5)'s argument-parse prologue. Reached
from `init_txcb_and_load_xfer` at `&B3D9` to install the FS
transfer context (byte count + source pointer in `fs_last_byte_flag`
/ `fs_crc_lo`/`hi`) before continuing into the *I am / *Pass
station-and-credential parser.""")
label(0x8E75, "loop_copy_return_template")
label(0x9292, "loop_print_inline_string")
subroutine(0x95C1, "print_station_low",
    title="Print 'PS       ' 9-column header",
    description="""\
Calls [`print_inline`](address:9261) with `'P'` then falls
through (via the 1-byte CLV terminator and BVC) into
[`print_field_tail_s`](address:95CD), so the combined output is
`'PS       '` -- the 9-column 'PS' field used in the `*FS`/`*PS`
no-arg help and `*STATUS` displays.""")
subroutine(0x95C8, "print_fs_station",
    title="Print 'FS       ' 9-column header",
    description="""\
Calls [`print_inline`](address:9261) with `'F'` then falls
through (via the 1-byte NOP terminator) into
[`print_field_tail_s`](address:95CD), so the combined output is
`'FS       '` -- the 9-column 'FS' field used in the `*FS`/`*PS`
no-arg help and `*STATUS` displays.""")
subroutine(0x95DA, "print_dir_syntax",
    title="Print '[<D>.]<D>\\\\r' directory-name syntax fragment",
    description="""\
3-byte JSR + inline `'[<D>.]<D>'` + CR + NOP terminator. Used as
a shared fragment by both `*Dir`'s syntax help and the `*FS`/`*PS`
no-argument help via [`print_fs_ps_help`](address:959A).""")
subroutine(0x965F, "print_ps_address",
    title="Print printer-server address from CMOS",
    description="""\
Reads the printer-server's saved network number from CMOS byte
&04, prints it as decimal (no leading zeros), prints a `.`
separator, then sets `X=3` and falls into
[`print_cmos_decimal_nl`](address:967F) to read CMOS &03 and
print the printer-server station with a trailing newline.
Returns via the [`print_cmos_done`](address:9689) trampoline.""")
subroutine(0x9670, "print_fs_address",
    title="Print file-server address from CMOS",
    description="""\
Reads the file-server's saved network number from CMOS byte
&02, prints it as decimal (no leading zeros), prints a `.`
separator, then sets `X=1` and falls into
[`print_cmos_decimal_nl`](address:967F) to read CMOS &01 and
print the file-server station with a trailing newline. Returns
via the [`print_cmos_done`](address:9689) trampoline.""")
subroutine(0x968E, "dispatch_help_command",
    title="Dispatch *HELP-style argument via svc4_dispatch_lookup",
    description="""\
3-byte trampoline: `JMP svc4_dispatch_lookup` with `X = &BD` from
the caller. Used by [`svc_29_status`](address:9630)'s
non-CR path so an argument after `*STATUS` (or similar *HELP-like
cmd) gets parsed and dispatched through the same shared parser as
the regular cmd-table dispatch. Note the `'!Help.'` bytes
immediately following are an unrelated inline string used by the
filename walker, not part of this routine's body.""")
label(0x96A7, "loop_match_on_suffix")
label(0x96BD, "loop_skip_non_spaces")
label(0x96C8, "loop_help_skip_spaces")
label(0x96DB, "loop_copy_command_suffix")
label(0x96E7, "loop_copy_topic_name")
label(0x96EB, "loop_store_topic_char")
subroutine(0x9FEE, "send_open_file_request",
    description="Send file open request with V flag set for directory check.")
label(0xA0F2, "loop_extract_attribute_bits")
label(0xA84A, "loop_save_osword_workspace")
label(0xA85C, "loop_restore_osword_workspace")
subroutine(0xA877, "extract_osword_subcode",
    title="Decode OSWORD &0E parameter byte and branch to handler",
    description="""\
Right-shifts `ws_page` (PB[0]) into `A`, transfers it to `Y` for
the dispatcher, then runs an EOR/CMP chain against
`ws_precomputed_value` to classify the requested sub-code:

| Test          | Path                              |
| ------------- | --------------------------------- |
| `CMP #4` =    | `save_txcb_and_convert` (clock)   |
| `CMP #3` =    | `save_txcb_done` (write back)     |
| anything else | set `svc_state = 8` and `RTS`     |

The two `LDA #&A9` filler bytes preceding the EOR are a 4-byte
BIT-trick skip used when the alternate entry [`osword_0e_handler`
](address:A874) is taken via the `BIT $abs` at `&A874`. Reached
only via the OSWORD `&0E` (CMOS clock read) handler chain.""")
label(0xA8EC, "loop_copy_pbytes_to_workspace")
# &B0A0 is the dead JMP (cdir_unused_dispatch_table,X) at the cmd_cdir dispatch boundary;
# never executed but py8dis follows the entry() declaration so it
# needs a non-placeholder name.
label(0xB0A0, "cmd_cdir_indirect_dispatch")
label(0xB1B4, "loop_print_dir_format")
label(0xB2B9, "loop_trim_trailing_spaces")
label(0xB316, "loop_divide_decimal_digit")
label(0xBB3C, "loop_save_fcb_workspace")
label(0xBB5F, "loop_restore_fcb_workspace")
label(0xBE16, "loop_print_hex_row")

# Phase K3 (2026-05-02): rename all 110 workspace external symbols.
# py8dis emits `lXXXX = &XXXX` declarations for any address outside
# the ROM that the code references but the driver hasn't named.
# Distribution: 81 HAZEL workspace bytes (&C001..&C2F3), 7 MOS
# hardware registers, 14 standard MOS workspace addresses (ZP, page-1
# stack save area, vectors), 8 misc RAM addresses. Names reuse 4.18
# verbatim where possible (error_block, stack_page_*, vdu_*,
# last_break_type, etc.); HAZEL bytes named by examining each use
# site. Tracked in PHASE-K-LABEL-RENAME.md.
#
# Phase K4 (2026-05-02): refined the &C200..&C2F3 region from
# the K3 hazel_shadow_XX placeholders. The region turns out to be
# a per-channel FCB (file control block) parallel-array layout:
# &C200..&C2BF holds 12 fields x 16 channels (file position lo/mid/hi,
# link, handle, network, status, station lo/hi, offset save, attr
# ref, flags); &C2C0..&C2F3 are individual working-state bytes.
# Names now reflect each field's role. A few names (sentinel_cd/ce,
# pass_counter, ctx_buffer) are still best-effort.
label(0x0020, "tx_buffer_scratch",
    length=1, group="zero_page", access="rw")
label(0x0026, "parse_separator_flag",
    length=1, group="zero_page", access="rw")
label(0x00ED, "tx_imm_idx_base",
    length=1, group="zero_page", access="rw")
label(0x0100, "error_block")
label(0x0101, "error_text")
label(0x0102, "stack_page_2")
label(0x0103, "stack_page_3")
label(0x0104, "stack_page_4")
label(0x0106, "stack_page_6")
label(0x028D, "last_break_type")
label(0x02A0, "rom_type_table")
label(0x0350, "vdu_screen_mode",
    description="VDU screen mode set by the OS.",
    length=1, group="ram_workspace", access="r")
label(0x0351, "vdu_display_start_hi",
    description="VDU display start address (high byte).",
    length=1, group="ram_workspace", access="r")
label(0x0355, "vdu_mode",
    description="VDU current output stream selector.\n"
                "Determines whether `OSWRCH` writes to the screen, "
                "printer, serial port, etc. ANFS reads this to decide "
                "whether to wrap *HELP syntax lines for serial output.",
    length=1, group="ram_workspace", access="r")
label(0x0406, "tube_addr_data_dispatch")
label(0x0CFF, "nmi_code_base")
label(0x0D71, "spool_control_flag",
    description="Multi-purpose: spool-buffer control flag (printer "
                "spooling); also doubles as the bridge-routing-table "
                "status byte read by "
                "[`init_bridge_poll`](address:ABE9) (`&FF` = "
                "uninitialised, anything else = bridge already "
                "polled).",
    length=1, group="ram_workspace", access="rw")
label(0x2048, "ws_template_source")
label(0x2322, "separator_parse_dispatch")
label(0x4898, "cdir_unused_dispatch_table")
label(0x688B, "ws_precomputed_value")
label(0x6F6E, "false_ref_6f6e")
label(0xC000, "hazel_fs_station",
    description="Filing-system state block (`&C000`–`&C00A`).\n\n"
                "Eleven bytes of currently-selected-FS context kept "
                "in HAZEL: station / network of the FS, saved prefix "
                "station, multi-purpose CSD/library/boot-type slots, "
                "FS flags, messages flag, pending-state, error code, "
                "last-error, and `*OPT` addend. The first two bytes "
                "(`hazel_fs_station`, `hazel_fs_network`) are the FS "
                "address used for every TX scout.",
    length=11, group="hazel", access="rw")
label(0xC001, "hazel_fs_network",
    description="FS network number (sub-byte of the &C000 FS "
                "context block).",
    length=1, group="hazel", access="rw")
label(0xC002, "hazel_fs_saved_station")
label(0xC003, "hazel_fs_context_copy",
    description="Multi-purpose sub-byte of the &C000 block: CSD "
                "handle / matched-entry index / Y-indexed base "
                "into FS context block.",
    length=1, group="hazel", access="rw")
label(0xC004, "hazel_fs_prefix_stn",
    description="Multi-purpose sub-byte of the &C000 block: "
                "saved-prefix station / library handle / boot type.",
    length=1, group="hazel", access="rw")
label(0xC005, "hazel_fs_flags")
label(0xC006, "hazel_fs_messages_flag")
label(0xC007, "hazel_fs_pending_state")
label(0xC008, "hazel_fs_error_code",
    description="FS error code (sub-byte of the &C000 block).",
    length=1, group="hazel", access="rw")
label(0xC009, "hazel_fs_last_error",
    description="Last FS error byte (sub-byte of the &C000 block).",
    length=1, group="hazel", access="rw")
label(0xC00A, "hazel_fs_opts_addend")
label(0xC014, "hazel_retry_counter",
    description="Retry counter for the current Econet TX/RX cycle.",
    length=1, group="hazel", access="rw")
label(0xC02F, "hazel_parse_buf_m1")
label(0xC030, "hazel_parse_buf",
    description="Three-byte parse-buffer used for command-line "
                "matching (e.g. `*OPT`, `*FS`).",
    length=3, group="hazel", access="rw")
label(0xC031, "hazel_parse_buf_1")
label(0xC032, "hazel_parse_buf_2")
label(0xC038, "hazel_rtc_buffer",
    description="OSWORD `&0E` real-time-clock result buffer.",
    length=25, group="hazel", access="rw")
label(0xC0F7, "hazel_fs_reply_byte",
    description="Latched first byte of the most recent FS reply.",
    length=1, group="hazel", access="rw")
label(0xC100, "hazel_txcb_port",
    description="TXCB byte 0: port number for the next TX scout.",
    length=1, group="hazel", access="rw")
label(0xC101, "hazel_txcb_func_code",
    description="TXCB byte 1: function code (FS command number).",
    length=1, group="hazel", access="rw")
label(0xC102, "hazel_txcb_station",
    description="TXCB byte 2: destination station.",
    length=1, group="hazel", access="rw")
label(0xC103, "hazel_txcb_network",
    description="TXCB byte 3: multi-purpose.\n"
                "TXCB destination network (TX setup) / reply "
                "function code (RX context) / `fs_cmd_csd` buffer "
                "base (other paths).",
    length=1, group="hazel", access="rw")
label(0xC104, "hazel_txcb_lib",
    description="TXCB byte 4: library handle terminator / "
                "transfer-length param 1.",
    length=1, group="hazel", access="rw")
label(0xC105, "hazel_txcb_data",
    description="TXCB byte 5: first reply-data byte / data start.",
    length=1, group="hazel", access="rw")
label(0xC106, "hazel_txcb_flag",
    description="TXCB byte 6: direction flag.",
    length=1, group="hazel", access="rw")
label(0xC107, "hazel_txcb_count",
    description="TXCB byte 7: data count / lock flag.",
    length=1, group="hazel", access="rw")
label(0xC108, "hazel_txcb_result",
    description="TXCB byte 8: result / transfer-size lo.",
    length=1, group="hazel", access="rw")
label(0xC10A, "hazel_txcb_size_hi")
label(0xC10B, "hazel_txcb_tx_status")
label(0xC10C, "hazel_txcb_osword_flag")
label(0xC10D, "hazel_txcb_addr_lo")
label(0xC10E, "hazel_txcb_access")
label(0xC110, "hazel_txcb_addr_hi")
label(0xC111, "hazel_txcb_len")
label(0xC112, "hazel_txcb_type")
label(0xC113, "hazel_txcb_objtype")
label(0xC114, "hazel_txcb_cycle")
label(0xC116, "hazel_txcb_byte_16")
label(0xC12F, "hazel_txcb_end")
label(0xC130, "hazel_examine_attr")
label(0xC1C8, "hazel_chan_status")
label(0xC1DC, "hazel_net_reply_buf_0")
label(0xC1DD, "hazel_net_reply_buf_1")
label(0xC1DE, "hazel_net_reply_buf_2")
label(0xC1DF, "hazel_net_reply_buf_3")
label(0xC1E0, "hazel_fcb_addr_lo_minus20")
label(0xC1F0, "hazel_fcb_addr_mid_minus20")
label(0xC1FF, "hazel_display_buf_minusF4")
label(0xC200, "hazel_fcb_addr_lo",
    description="FCB parallel array (16 entries): file position byte 0 (low).\n"
                "Indexed by channel `0..15`; cleared by "
                "[`alloc_fcb_slot`](address:B8A8) on FCB allocation.",
    length=16, group="hazel", access="rw")
label(0xC210, "hazel_fcb_addr_mid",
    description="FCB parallel array (16 entries): file position byte 1 (mid).",
    length=16, group="hazel", access="rw")
label(0xC220, "hazel_fcb_addr_hi",
    description="FCB parallel array (16 entries): file position byte 2 (high).",
    length=16, group="hazel", access="rw")
label(0xC230, "hazel_fcb_slot_attr",
    description="FCB parallel array (16 entries): slot occupancy + channel attribute.\n"
                "Tested for zero by [`alloc_fcb_slot`](address:B8A8) "
                "as the slot-free check; set non-zero on allocation.",
    length=16, group="hazel", access="rw")
label(0xC240, "hazel_fcb_state_byte",
    description="FCB parallel array (16 entries): multi-purpose state byte.\n"
                "Holds station number for non-OSFIND channels, or "
                "open-mode flags for channels created by OSFIND.",
    length=16, group="hazel", access="rw")
label(0xC250, "hazel_fcb_network",
    description="FCB parallel array (16 entries): network number per channel.",
    length=16, group="hazel", access="rw")
label(0xC260, "hazel_fcb_status",
    description="FCB parallel array (16 entries): per-channel status flags.\n"
                "Heavily used: bit 6 = connection active "
                "(`set_conn_active` / `clear_conn_active` toggle).",
    length=16, group="hazel", access="rw")
label(0xC270, "hazel_cur_dir_handle")
label(0xC271, "hazel_fs_lib_flags",
    description="FS library / option flags. Bit 2 = auto-boot, "
                "bit 7 = library-directory pending. Cleared / "
                "tested by *Cat / *Lcat / *Ex / *Lex paths.",
    length=1, group="hazel", access="rw")
label(0xC272, "hazel_fcb_slot_1")
label(0xC273, "hazel_fcb_slot_2")
label(0xC274, "hazel_fcb_slot_3")
label(0xC278, "hazel_fcb_station_lo")
label(0xC288, "hazel_fcb_station_hi")
label(0xC298, "hazel_fcb_offset_save")
label(0xC2A8, "hazel_fcb_attr_ref")
label(0xC2B8, "hazel_fcb_flags")
label(0xC2C8, "hazel_cur_fcb_index",
    description="Current FCB index used by the FCB-scan loop in "
                "[`process_all_fcbs`](address:BB38). Followed by the "
                "channel attribute / reference, byte-counter, "
                "buffer pointer and a small block of transfer-state "
                "scratch bytes used during file I/O.",
    length=1, group="hazel", access="rw")
label(0xC2C9, "hazel_chan_attr")
label(0xC2CA, "hazel_chan_ref")
label(0xC2CB, "hazel_byte_counter_lo")
label(0xC2CC, "hazel_buf_addr_hi")
label(0xC2CD, "hazel_sentinel_cd",
    description="Sentinel/scratch byte at HAZEL+&CD, used by the "
                "FCB-scan loop in "
                "[`process_all_fcbs`](address:BB38).",
    length=1, group="hazel", access="rw")
label(0xC2CE, "hazel_sentinel_ce",
    description="Sentinel/scratch byte at HAZEL+&CE, used by the "
                "FCB-scan loop in "
                "[`process_all_fcbs`](address:BB38).",
    length=1, group="hazel", access="rw")
label(0xC2CF, "hazel_offset_counter")
label(0xC2D0, "hazel_pass_counter")
label(0xC2D1, "hazel_xfer_init_zeros")
label(0xC2D4, "hazel_station_lo")
label(0xC2D5, "hazel_station_hi")
label(0xC2D6, "hazel_transfer_flag")
label(0xC2D7, "hazel_saved_byte")
label(0xC2D8, "hazel_quote_mode")
label(0xC2D9, "hazel_ctx_buffer",
    description="HAZEL context buffer (saved register / state "
                "block used during FCB processing).",
    length=1, group="hazel", access="rw")
label(0xC2F3, "hazel_display_buf")
label(0xFE28, "master_romsel_shadow",
    description="Master 128 ROMSEL shadow register.\n"
                "Read-only mirror of the current sideways-ROM "
                "selection (the actual ROMSEL is at `&FE30`).",
    length=1, group="mmio", access="r")
label(0xFE2B, "master_break_type_shadow",
    description="Master 128 last-break-type hardware shadow.\n"
                "Reflects the value left by the last reset (cold "
                "/ warm / power-on).",
    length=1, group="mmio", access="r")
label(0xFE34, "acccon",
    description="Master 128 ACCCON access-control register.\n\n"
                "Bit-by-bit (write-only):\n\n"
                "| Bit | Name | Effect when set |\n"
                "|---|---|---|\n"
                "| 7 | IRR | IRQ-on-VSYNC mask |\n"
                "| 6 | TST | Test mode |\n"
                "| 5 | IFJ | I/O is JIM |\n"
                "| 4 | ITU | Internal Tube |\n"
                "| 3 | Y   | HAZEL paged in (`&C000-&DFFF` is hidden RAM) |\n"
                "| 2 | X   | LYNNE paged in (`&3000-&7FFF` is shadow RAM) |\n"
                "| 1 | E   | shadow RAM owns screen |\n"
                "| 0 | D   | shadow RAM for the OS display |\n\n"
                "ANFS uses bit 7 (IRR) as a deferred-work latch via "
                "`TRB`/`TSB`.",
    length=1, group="mmio", access="rw")
label(0xFE38, "master_intoff",
    description="Master 128 INTOFF mirror (NMI-disable side effect).\n"
                "Reading any byte here disables /NMI re-entry; the "
                "byte value itself is irrelevant.",
    length=1, group="mmio", access="r")
label(0xFE3C, "master_inton",
    description="Master 128 INTON mirror (NMI-enable side effect).\n"
                "Reading any byte here re-enables /NMI; the byte "
                "value itself is irrelevant.",
    length=1, group="mmio", access="r")
label(0xFFB0, "nmi_buf_idx_base",
    description="NMI buffer indexing-base.\n"
                "Used by the NMI RX setup as `STA nmi_buf_idx_base,Y` "
                "with Y values that wrap into low memory; the bytes "
                "at `&FFB0` themselves aren't read or written.",
    length=1, group="idx_base", access="r")
label(0xFFBD, "fcb_workspace_idx_base",
    description="FCB-workspace indexing-base (wraps into ZP).\n"
                "Used by `loop_save_fcb_workspace` as the base of "
                "`LDA &FFBD,X` with X=`&F7`..`&FF`; the effective "
                "address wraps to `&00B4`..`&00BC` (= `fs_work_4`+"
                "0..+8). The byte at `&FFBD` itself is never read.",
    length=1, group="idx_base", access="r")

# 14 indexing-base aliases that py8dis emitted as `lXXXX = symbol+offset`
# because the code uses `LDA somelabel,X/Y` with a base that lies inside
# an existing labelled routine. Naming the base address explicitly
# replaces the auto-generated alias with a domain name. Same Phase K3
# scope: ensure 0 hex-tail names anywhere in the asm output.
label(0x840A, "imm_op_handler_lo_table")
label(0x886F, "tx_length_table")
label(0x8877, "tx_flags_table")
label(0x89C9, "nmi_shim_source")
label(0x968F, "help_topic_template")
label(0x99A3, "bad_prefix_table")
# &A0FF is mid-instruction (operand byte of the JSR at &A0FE) so it
# can't carry its own beebasm label -- py8dis instead emits an equate
# `cmos_attr_table = osopt_cmos_writeback_jsr + 1`. Naming both
# addresses keeps the equate readable (otherwise py8dis falls back to
# auto-generated sub_cA0FE / la0ff names) and lets the indexed-base
# trick `lda cmos_attr_table,X` (X=4..7) reach the read-masks at
# offset -4 of the underlying cmos_opt_mask_table.
label(0xA0FE, "osopt_cmos_writeback_jsr")
label(0xA0FF, "cmos_attr_table",
    description="Indexing-base alias of "
                "[`cmos_opt_mask_table`](address:A103) - 4.\n"
                "`LDA cmos_attr_table,X` at &A0ED with X=4..7 reads "
                "the read-masks 1, 2, 4, 6 from the underlying table; "
                "those values double as bit-shift counts that left-"
                "align the new field into CMOS &11. The byte at "
                "&A0FF is inside the operand of the JSR at &A0FE "
                "and is never read directly.",
    length=1, group="idx_base", access="r")
label(0xA76D, "cmd_dispatch_lo_table")
label(0xA76E, "cmd_dispatch_hi_table")
label(0xA878, "osword_subcode_dispatch")
label(0xABC5, "bridge_err_table")
label(0xB0D4, "cdir_size_thresholds")
label(0xB4FD, "ps_print_template")
label(0xB821, "net_chan_err_strings")

# Boot-command strings used by fsreply_1_boot via OSCLI.
# &A741: 'L.-NET-!Boot' (Load and run !Boot file from NET partition).
# &A74E: 'E.-NET-!Boot' (Exec the !Boot file -- alternate variant).
# Each string is 12 chars + a 0x0D CR terminator at &A74D / &A75A.
comment(0xA741, "Boot command 'L.-NET-!Boot' (Load !Boot)", inline=True)
comment(0xA74D, "CR terminator", inline=True)
comment(0xA74E, "Boot command 'E.-NET-!Boot' (Exec !Boot)", inline=True)
comment(0xA75A, "CR terminator", inline=True)
comment(0xA75B, "Boot command low-byte index table -- 4 bytes "
    "spelling 'ZAHN', each the low byte of a boot-command address "
    "in the &A7xx page (Z=&5A, A=&41, H=&48, N=&4E)",
    inline=True)
comment(0xA764, "Load boot-command low byte from "
    "boot_prefix_string[Y]", inline=True)
comment(0xA767, "Y=&A7: high byte (boot strings live in &A7xx)",
    inline=True)
comment(0xA769, "Tail-jump to OSCLI to execute the boot command",
    inline=True)
# &A83D: 13-byte block of OSWORD-related state bytes used by
# svc_8_osword's setup. Mostly small constants and offsets.
comment(0xA83D, "OSWORD setup state (13 bytes -- constants and "
    "offsets used by svc_8_osword)", inline=True)

# byte_to_2bit_index inline comments (12 items)
# This computes A * 12 with overflow clamping. The PHA/TSX/PHP/ADC
# stack-X trick is the standard 6502 idiom for adding a saved value
# without using zero-page scratch.
comment(0xA3E9, "Multiply A by 2", inline=True)
comment(0xA3EA, "Multiply A by 2 again -- A is now A_orig * 4",
        inline=True)
comment(0xA3EB, "Stash A_orig * 4 on the stack", inline=True)
comment(0xA3EC, "Multiply A by 2 -- A is now A_orig * 8 (C = bit 7 of "
        "A_orig*4)", inline=True)
comment(0xA3ED, "Capture S so we can read the just-pushed value",
        inline=True)
comment(0xA3EE, "Save the C flag from the third ASL", inline=True)
comment(0xA3EF, "ADC stack[X+1] = A_orig*4 (with C from the ASL): "
        "A = A_orig*8 + A_orig*4 + C = A_orig*12 + C", inline=True)
comment(0xA3F2, "Halve the result, putting the new C as bit 7",
        inline=True)
comment(0xA3F3, "Restore the saved C (from the third ASL)", inline=True)
comment(0xA3F4, "ASL doubles the halved value (effectively undoes the "
        "ROR's divide while reusing C)", inline=True)
comment(0xA3F5, "Y = A_orig * 12 (the 12-byte-aligned index)",
        inline=True)
comment(0xA3F6, "Recover A_orig * 4 (left on the stack at &A3EB)",
        inline=True)
comment(0xA3F7, "Above &48 (i.e. A_orig * 4 >= 72, A_orig >= 18)?",
        inline=True)
comment(0xA3F9, "No: keep computed Y", inline=True)
comment(0xA3FB, "Yes: clamp Y to 0 (out of range)", inline=True)
comment(0xA3FD, "Mirror Y -> A so callers can test Z", inline=True)
comment(0xA3FE, "Return; Y holds 12-byte-aligned offset, A is "
        "non-zero on success", inline=True)

# copy_ps_data inline comments (5 items)
comment(0xB3D7, "X=&F8: walks 0..7 via wraparound (loads from "
        "ps_template_base+&F8 = ps_template_data &8E9F)",
        inline=True)
comment(0xB3D9, "Read template byte from ps_template_data + (X-&F8)",
        inline=True)
comment(0xB3DC, "Store into RX buffer at offset Y", inline=True)
comment(0xB3DE, "Step destination", inline=True)
comment(0xB3DF, "Step source -- wraps from &FF to &00 to terminate",
        inline=True)
comment(0xB3E0, "Loop while X != 0 (8 iterations: &F8..&FF)", inline=True)
comment(0xB3E2, "Return", inline=True)

# init_dump_buffer inline comments (~50 items)
comment(0xBEAB, "Step Y past the *Dump command name into the argument",
        inline=True)
comment(0xBEAC, "Save the cursor offset", inline=True)
comment(0xBEAE, "Set bit 0 of addr_work to 1 -- 'mode' flag for "
        "parse_dump_range below", inline=True)
comment(0xBEB0, "Save mode flag", inline=True)
comment(0xBEB2, "Parse the start address (max 4 hex digits)",
        inline=True)
comment(0xBEB5, "Overflow: too many digits", inline=True)
comment(0xBEB7, "Save current Y (cursor after start address)",
        inline=True)
comment(0xBEB8, "Push it", inline=True)
comment(0xBEB9, "Y = file handle saved in ws_page", inline=True)
comment(0xBEBB, "X=&AA: zero-page address for OSARGS result", inline=True)
comment(0xBEBD, "A=2: OSARGS sub-fn 2 = read sequential file extent",
        inline=True)
comment(0xBEBF, "Get file size into 4 bytes at &AA", inline=True)
comment(0xBEC2, "Y=3: compare 4-byte values (high to low)", inline=True)
comment(0xBEC4, "Read file size byte at &AA+Y", inline=True)
comment(0xBEC7, "Compare with parsed start address (work_ae+Y)",
        inline=True)
comment(0xBEC9, "Mismatch: branch decides which is bigger", inline=True)
comment(0xBECB, "Step to next byte", inline=True)
comment(0xBECC, "Loop while Y >= 0 (covers indices 3, 2, 1, 0)",
        inline=True)
comment(0xBECE, "All bytes equal: start = extent (allowed); jump to "
        "the post-validation path", inline=True)
comment(0xBED0, "C clear: parsed_start > file_size -- reject",
        inline=True)
comment(0xBED2, "Y=&FF: signal 'no copy needed' to the loop below",
        inline=True)
comment(0xBED4, "Always taken: skip directly to advance phase",
        inline=True)
# Outside-file error
comment(0xBED6, "Close the file before raising", inline=True)
comment(0xBED9, "A=&B7: 'Outside file' error code", inline=True)
comment(0xBEDB, "Raise via inline string; never returns", inline=True)
# Copy/advance phase
comment(0xBEEB, "Copy file-extent byte from osword_flag to (work_ae)",
        inline=True)
comment(0xBEED, "Store it (used as default end address)", inline=True)
comment(0xBEF0, "Step Y", inline=True)
comment(0xBEF1, "Done all 4 bytes?", inline=True)
comment(0xBEF3, "No: continue copying", inline=True)
comment(0xBEF5, "X=&AA: zero-page source for the OSARGS write-back",
        inline=True)
comment(0xBEF7, "Y = file handle", inline=True)
comment(0xBEF9, "A=1: OSARGS sub-fn 1 = write sequential file pointer",
        inline=True)
comment(0xBEFB, "Set the file's read pointer to the parsed start",
        inline=True)
comment(0xBEFE, "Pull saved cursor offset", inline=True)
comment(0xBEFF, "Restore into Y", inline=True)
# Optional second argument or default-base setup
comment(0xBF00, "Read next command-line byte", inline=True)
comment(0xBF02, "CR (end of args)?", inline=True)
comment(0xBF04, "No: there's a second arg -- handle below", inline=True)
comment(0xBF06, "Y=1: copy os_text_ptr (2 bytes) to work_ae as a "
        "displacement-base hint", inline=True)
comment(0xBF08, "Read os_text_ptr+Y", inline=True)
comment(0xBF0B, "Save in work_ae+Y", inline=True)
comment(0xBF0D, "Step backwards", inline=True)
comment(0xBF0E, "Loop while Y >= 0", inline=True)
comment(0xBF10, "A=5: OSFILE sub-fn 5 = read catalogue info", inline=True)
comment(0xBF12, "X = filename pointer low (work_ae)", inline=True)
comment(0xBF14, "Y = filename pointer high (addr_work)", inline=True)
comment(0xBF16, "Read load address into work_ae+0..3", inline=True)
# Shift OSFILE returned data
comment(0xBF19, "Y=2: shift 3 bytes down 2 positions to drop the "
        "first 2 bytes (action code + a flag)", inline=True)
comment(0xBF1B, "Read source byte", inline=True)
comment(0xBF1D, "Y -= 2 (destination)", inline=True)
comment(0xBF1F, "Store at destination", inline=True)
comment(0xBF21, "Y += 3 to advance to next source", inline=True)
comment(0xBF22, "(continued)", inline=True)
comment(0xBF23, "(continued)", inline=True)
comment(0xBF24, "Done 6 bytes shifted?", inline=True)
comment(0xBF26, "No: continue", inline=True)
# Detect &FF-pad load address
comment(0xBF28, "Y -= 2: position at high byte of load address",
        inline=True)
comment(0xBF2A, "Read load-address byte at Y", inline=True)
comment(0xBF2C, "Is it &FF (signals no real load address)?", inline=True)
comment(0xBF2E, "No: have a real load address; add it as displacement",
        inline=True)
comment(0xBF30, "Yes: step back to next higher byte", inline=True)
comment(0xBF31, "Loop until Y=0", inline=True)
comment(0xBF33, "All four bytes were &FF: zero out the load address",
        inline=True)
comment(0xBF35, "A=0", inline=True)
comment(0xBF37, "Zero work_ae+Y", inline=True)
comment(0xBF39, "Step backwards", inline=True)
comment(0xBF3A, "Loop while Y >= 0", inline=True)
comment(0xBF3C, "Always taken (after BPL drops out): skip second-arg "
        "path", inline=True)
# Second-argument path
comment(0xBF3E, "Parse end-address argument", inline=True)
comment(0xBF41, "Success: continue with displacement-add", inline=True)
comment(0xBF43, "Parse error: close file then raise 'Bad address'",
        inline=True)
comment(0xBF46, "A=&FC: 'Bad address' error code", inline=True)
comment(0xBF48, "Raise; never returns", inline=True)
# Add displacement base
comment(0xBF53, "Y=0: start of work_ae", inline=True)
comment(0xBF55, "X=4: 4-byte add", inline=True)
comment(0xBF57, "Clear C for the add", inline=True)

# cmd_dump inline comments (~80 items)
# Setup
comment(0xBD41, "Open the file (handle stored in ws_page)", inline=True)
comment(0xBD44, "X=&14: 21-byte stack buffer for dump line state",
        inline=True)
comment(0xBD46, "A=0: zero-fill", inline=True)
comment(0xBD48, "Push zero", inline=True)
comment(0xBD49, "Step counter", inline=True)
comment(0xBD4A, "Loop while X >= 0 (21 zeros)", inline=True)
comment(0xBD4C, "Capture stack pointer for later restore", inline=True)
comment(0xBD4D, "Parse address range and validate against file extent",
        inline=True)
comment(0xBD50, "Read low nibble of starting address", inline=True)
comment(0xBD52, "Mask high nibble (top 4 bits)", inline=True)
comment(0xBD54, "Aligned (high nibble zero): skip the header print",
        inline=True)
comment(0xBD56, "Print 'Address: 00 01 ... 0F: ASCII data' header",
        inline=True)
# Outer line loop
comment(0xBD59, "Test escape and abort if pressed", inline=True)
comment(0xBD5C, "A=&FF: count counter starts here so first INC -> 0",
        inline=True)
comment(0xBD5E, "Save counter (-1)", inline=True)
comment(0xBD60, "Y = file handle", inline=True)
comment(0xBD62, "Read one byte via OSBGET (C set on EOF)", inline=True)
comment(0xBD65, "EOF: finish off this line then exit", inline=True)
comment(0xBD67, "Increment count counter", inline=True)
comment(0xBD69, "Y = current count (also buffer offset)", inline=True)
comment(0xBD6B, "Store byte in 16-byte line buffer at (work_ae)+Y",
        inline=True)
comment(0xBD6D, "Done all 16 bytes?", inline=True)
comment(0xBD6F, "No: read next byte", inline=True)
comment(0xBD71, "C clear: not EOF (clean line)", inline=True)
# Test for early exit
comment(0xBD72, "Save the EOF/clean flag", inline=True)
comment(0xBD73, "Reload counter byte", inline=True)
comment(0xBD75, "Bit 7 clear (counter is 0..&7F): bytes were read",
        inline=True)
comment(0xBD77, "EOF and no bytes: clean up and exit", inline=True)
comment(0xBD79, "Restore one stack byte", inline=True)
comment(0xBD7A, "Step", inline=True)
comment(0xBD7B, "Loop while X >= 0 (22 pulls)", inline=True)
comment(0xBD7D, "Tail-jump to close_ws_file", inline=True)
# Header on 256-byte boundary
comment(0xBD80, "Y=&10: read displayed-address byte 0", inline=True)
comment(0xBD82, "Read low byte", inline=True)
comment(0xBD84, "Top nibble", inline=True)
comment(0xBD86, "Non-zero: not a 256-byte boundary, skip header",
        inline=True)
comment(0xBD88, "Boundary: print column header", inline=True)
# Print 4-byte hex address
comment(0xBD8B, "Y=&13: highest byte of 4-byte address", inline=True)
comment(0xBD8D, "Read address byte (highest first)", inline=True)
comment(0xBD8F, "Save it (print_hex_byte clobbers A)", inline=True)
comment(0xBD90, "Print as 2 hex digits", inline=True)
comment(0xBD93, "Restore A", inline=True)
comment(0xBD94, "Step backwards", inline=True)
comment(0xBD95, "Reached low byte (offset &0F)?", inline=True)
comment(0xBD97, "No: continue printing", inline=True)
# Increment 4-byte address by 16
comment(0xBD99, "Y=&10: low byte of address", inline=True)
comment(0xBD9A, "Clear C", inline=True)
comment(0xBD9B, "Bump address by 16 bytes for next line",
        inline=True)
comment(0xBD9D, "Save C from the add", inline=True)
comment(0xBD9E, "Restore C from previous step", inline=True)
comment(0xBD9F, "Store updated address byte", inline=True)
comment(0xBDA1, "Step Y up", inline=True)
comment(0xBDA2, "Read next byte", inline=True)
comment(0xBDA4, "Add carry from below", inline=True)
comment(0xBDA6, "Save C", inline=True)
comment(0xBDA7, "Done all 4 bytes (Y=&14)?", inline=True)
comment(0xBDA9, "No: continue propagating", inline=True)
comment(0xBDAB, "Restore final C", inline=True)
comment(0xBDAC, "Print ' : ' separator before hex byte field",
        inline=True)
# Print 16 hex bytes
comment(0xBDB2, "Y=0: start of buffer", inline=True)
comment(0xBDB4, "X = byte counter (-1 initially, INC'd to 0..&0F)",
        inline=True)
comment(0xBDB6, "Read byte from buffer", inline=True)
comment(0xBDB8, "Print as hex + space", inline=True)
comment(0xBDBB, "Step buffer offset", inline=True)
comment(0xBDBC, "Done all 16?", inline=True)
comment(0xBDBE, "Yes: print separator before ASCII field", inline=True)
comment(0xBDC0, "Step counter (Y was off-by-one from line read)",
        inline=True)
comment(0xBDC1, "Have a real byte? Print it", inline=True)
comment(0xBDC3, "End of partial line: pad with 3 spaces", inline=True)
comment(0xBDC4, "Print '   ' inline", inline=True)
comment(0xBDCA, "NOP -- bit-7 terminator + harmless resume opcode", inline=True)
comment(0xBDCB, "Restore Y", inline=True)
comment(0xBDCC, "Continue padding the rest of the hex column",
        inline=True)
# Separator + ASCII field
comment(0xBDCF, "Counter has finished -- step it once more for the "
        "ASCII test", inline=True)
comment(0xBDD0, "Print ': ' inline (ASCII field separator)", inline=True)
comment(0xBDD5, "Y=0: rewind to start of line buffer", inline=True)
comment(0xBDD7, "Skip 8 padding spaces if needed (advance_x_by_8)",
        inline=True)
comment(0xBDDA, "Read line buffer byte", inline=True)
comment(0xBDDC, "Mask off bit 7 (DEL/inverted)", inline=True)
comment(0xBDDE, "Below ' '? (control char)", inline=True)
comment(0xBDE0, "Yes: skip to substitution", inline=True)
comment(0xBDE2, "Substitute '.' for non-printables", inline=True)
comment(0xBDE4, "Compare with DEL", inline=True)
comment(0xBDE6, "Equal: also non-printable, substitute '.'", inline=True)
comment(0xBDE8, "Print the (possibly substituted) character", inline=True)
comment(0xBDEB, "Step Y", inline=True)
comment(0xBDEC, "Done 16 chars?", inline=True)
comment(0xBDEE, "Yes: end this line", inline=True)
comment(0xBDF0, "Step counter back", inline=True)
comment(0xBDF1, "Loop while X >= 0", inline=True)
comment(0xBDF3, "Print newline at end of line", inline=True)
comment(0xBDF6, "Restore EOF flag", inline=True)
comment(0xBDF7, "EOF: tidy up and exit", inline=True)
comment(0xBDF9, "More to dump: jump to next line", inline=True)
comment(0xBDFC, "X=&14: balance the loop_pop_stack_buf counter",
        inline=True)
comment(0xBDFE, "Tail-jump to clean up the 21-byte stack buffer and "
        "close the file", inline=True)

# pop_requeue_ps_scan inline comments (~50 items)
# Restore caller's stack-saved state and prepare to walk PS slots
comment(0xB4B4, "Pull saved upper byte of ws_ptr_lo+osword_flag pair",
        inline=True)
comment(0xB4B5, "Save into osword_flag", inline=True)
comment(0xB4B7, "Pull lower byte", inline=True)
comment(0xB4B8, "Save into ws_ptr_lo", inline=True)
comment(0xB4BA, "Push 0 -- placeholder, will be the stacked return "
        "marker", inline=True)
comment(0xB4BC, "Push it", inline=True)
comment(0xB4BD, "ws_ptr_hi base = &84 (start of PS slot table area)",
        inline=True)
comment(0xB4BF, "Save base", inline=True)
comment(0xB4C1, "Shift bit 0 of econet_flags into C (saved scan state)",
        inline=True)
comment(0xB4C4, "A=3: PS slot index counter", inline=True)
# Slot scan loop
comment(0xB4C6, "Convert slot index to 12-byte-aligned table offset",
        inline=True)
comment(0xB4C9, "Out of range (clamped to 0): all slots scanned",
        inline=True)
comment(0xB4CB, "A /= 2 (shift down)", inline=True)
comment(0xB4CC, "A /= 2 again (now slot index * 4 / 4 = slot index)",
        inline=True)
comment(0xB4CD, "X = slot index", inline=True)
comment(0xB4CE, "Read slot's status byte at workspace[Y]", inline=True)
comment(0xB4D0, "Slot empty (0): scan done", inline=True)
comment(0xB4D2, "Slot is '?' (uninitialised marker)?", inline=True)
comment(0xB4D4, "Yes: re-init this slot's data", inline=True)
# Skip-next-slot
comment(0xB4D6, "Step slot index", inline=True)
comment(0xB4D7, "Move to A for next iteration", inline=True)
comment(0xB4D8, "Loop while X != 0 (wraps when all slots done)",
        inline=True)
# Re-init '?' slot
comment(0xB4DA, "Save Y (slot table offset)", inline=True)
comment(0xB4DB, "Push it", inline=True)
comment(0xB4DC, "A=&7F: slot status 'busy/active'", inline=True)
comment(0xB4DE, "Mark slot active", inline=True)
comment(0xB4E0, "Step Y to control byte", inline=True)
comment(0xB4E1, "A=&9E: control byte (Master 128 PS-init pattern)",
        inline=True)
comment(0xB4E3, "Store control byte", inline=True)
comment(0xB4E5, "A=0: zero-fill the next two bytes", inline=True)
comment(0xB4E7, "Write two zeros, advance Y", inline=True)
comment(0xB4EA, "Read current ws_ptr_hi", inline=True)
comment(0xB4EC, "Store as buffer-link low byte", inline=True)
comment(0xB4EE, "Clear C ready for the +3", inline=True)
comment(0xB4EF, "Save flags so the ADC's C doesn't leak", inline=True)
comment(0xB4F0, "Bump ws_ptr_hi by 3 (next slot's base)", inline=True)
comment(0xB4F2, "Restore flags", inline=True)
comment(0xB4F3, "Save updated ws_ptr_hi", inline=True)
comment(0xB4F5, "Write buffer page + two &FF sentinels", inline=True)
comment(0xB4F8, "Read ws_ptr_hi (now updated)", inline=True)
comment(0xB4FA, "Store as second-link byte", inline=True)
comment(0xB4FC, "Write another buffer page + two &FF sentinels",
        inline=True)
comment(0xB4FF, "Continue scanning slots", inline=True)
# Done scanning -- delay loop
comment(0xB502, "Restore bit 0 of econet_flags via ASL (recovers from "
        "the LSR at &B4C1)", inline=True)
comment(0xB505, "Pull saved ws_ptr_lo", inline=True)
comment(0xB507, "Push it back (the caller's return-resume sequence)",
        inline=True)
comment(0xB508, "Pull saved osword_flag", inline=True)
comment(0xB50A, "Push it back", inline=True)
comment(0xB50B, "A=&0A: outer counter", inline=True)
comment(0xB50D, "Y=&0A: inner counter", inline=True)
comment(0xB50E, "X=&0A: middle counter", inline=True)
comment(0xB50F, "Save outer in fs_work_4", inline=True)
comment(0xB511, "Decrement inner counter", inline=True)
comment(0xB512, "Inner not zero: keep delaying", inline=True)
comment(0xB514, "Decrement middle", inline=True)
comment(0xB515, "Middle not zero: refresh inner and continue",
        inline=True)
comment(0xB517, "Decrement outer in fs_work_4", inline=True)
comment(0xB519, "Outer not zero: another full sweep (~1000 cycles)",
        inline=True)
comment(0xB51B, "Return", inline=True)

# cond_save_error_code inline comments (4 items)
comment(0x9900, "Test bit 7 of fs_flags (FS-active flag)", inline=True)
comment(0x9903, "FS not active: skip the save", inline=True)
comment(0x9905, "FS active: store error code at &C009 (last-error byte)",
        inline=True)
comment(0x9908, "Return", inline=True)

# build_no_reply_error inline comments (~15 items)
comment(0x9909, "X=8: net_error_lookup_data offset for 'No reply' "
        "message", inline=True)
comment(0x990B, "Y = message offset within the string table (&9AA6 "
        "base)", inline=True)
comment(0x990E, "X=0: error-text buffer index", inline=True)
comment(0x9910, "Zero the &0100 length byte (length will be filled in "
        "later)", inline=True)
comment(0x9913, "Read first message byte (the error code)", inline=True)
comment(0x9916, "Conditionally save it as last-error", inline=True)
comment(0x9919, "Read next message byte", inline=True)
comment(0x991C, "Append to error-text buffer at &0101+X", inline=True)
comment(0x991F, "Null terminator: message done", inline=True)
comment(0x9921, "Step buffer index", inline=True)
comment(0x9922, "Step source offset", inline=True)
comment(0x9923, "Loop while Y != 0 (Y wraps at 256, not expected)",
        inline=True)
comment(0x9925, "Append ' on drive <num>' or similar context",
        inline=True)
comment(0x9928, "A=0: null terminator", inline=True)
comment(0x992A, "Store at end of message", inline=True)
comment(0x992D, "Tail-jump to dispatch the BRK error", inline=True)

# fixup_reply_status_a inline comments (5 items)
comment(0x9930, "Read FS reply status byte at (net_tx_ptr,X)",
        inline=True)
comment(0x9932, "Status 'A'? (Acknowledge with no error)", inline=True)
comment(0x9934, "Not 'A': pass through unchanged", inline=True)
comment(0x9936, "Substitute 'B' for 'A' (handle ACK as a soft error)",
        inline=True)
comment(0x9938, "Clear V to take the standard mask path", inline=True)
comment(0x9939, "Always taken: use the standard masked-error path",
        inline=True)

# classify_reply_error inline comments (~15 items)
comment(0x993B, "Read FS reply status byte", inline=True)
comment(0x993D, "BIT $always_set_v_byte: force V=1 (extended-error "
        "path)", inline=True)
comment(0x9940, "Mask to 3 bits (error class 0..7)", inline=True)
comment(0x9942, "Save error class on stack", inline=True)
comment(0x9943, "Class 2 = 'station-related' family?", inline=True)
comment(0x9945, "No: build a simple one-line error", inline=True)
comment(0x9947, "Class 2 yes: save flags so we can branch on V later",
        inline=True)
comment(0x9948, "X = error class (=2)", inline=True)
comment(0x9949, "Y = lookup-table offset", inline=True)
comment(0x994C, "Read first message byte (error code)", inline=True)
comment(0x994F, "Conditionally save it", inline=True)
comment(0x9952, "X=0: text-buffer index", inline=True)
comment(0x9954, "Zero length byte", inline=True)
comment(0x9957, "Read message byte", inline=True)
comment(0x995A, "Append to buffer", inline=True)
comment(0x995D, "Null terminator -- station message done", inline=True)
comment(0x9963, "Append ' on drive <num>' suffix", inline=True)
comment(0x9966, "Restore the saved class flags", inline=True)
comment(0x9967, "V was set: use 'not listening' suffix", inline=True)
comment(0x9969, "A=&A4: 'station <n> not available' error code",
        inline=True)
comment(0x996B, "Save the alternative error code", inline=True)
comment(0x996E, "Patch error-text buffer length byte", inline=True)
comment(0x9971, "Y=&0B: lookup index for the listening-station suffix",
        inline=True)
comment(0x9973, "Always taken (Y is non-zero); jump to load_suffix_offset",
        inline=True)
comment(0x9975, "V was clear: 'not listening' suffix variant",
        inline=True)
comment(0x9977, "Read suffix offset from lookup", inline=True)
comment(0x997A, "Y = suffix offset", inline=True)
comment(0x997B, "Read suffix byte", inline=True)
comment(0x997E, "Append", inline=True)
comment(0x9981, "Null: suffix done", inline=True)
comment(0x9983, "Step Y", inline=True)
comment(0x9984, "Step X", inline=True)
comment(0x9985, "Loop while X != 0 (max 255 chars)", inline=True)
comment(0x9987, "Always taken (Z still set from BEQ): final terminator "
        "check", inline=True)

# build_simple_error inline comments
comment(0x9989, "X = error class", inline=True)
comment(0x998A, "Y = lookup-table offset", inline=True)
comment(0x998D, "X=0: buffer index", inline=True)
comment(0x998F, "Zero length", inline=True)
comment(0x9992, "Read first message byte (error code)", inline=True)
comment(0x9995, "Conditionally save it", inline=True)
comment(0x9998, "Read next message byte", inline=True)
comment(0x999B, "Append to buffer", inline=True)
comment(0x999E, "Null terminator -> dispatch", inline=True)
comment(0x99A0, "Step Y", inline=True)
comment(0x99A1, "Step X", inline=True)
comment(0x99A2, "Loop while X != 0", inline=True)

# send_disconnect_reply inline comments (~50 items in body)
comment(0xAFA6, "X = caller's TX-ptr low byte", inline=True)
comment(0xAFA8, "Y = caller's TX-ptr high byte", inline=True)
comment(0xAFAA, "Save A (the disconnect status to send)", inline=True)
comment(0xAFAB, "Test if A=0 (broadcast disconnect)", inline=True)
comment(0xAFAD, "Yes: skip the per-station scan", inline=True)
comment(0xAFAF, "X=&FF: scan counter -- INX in loop bumps to 0",
        inline=True)
comment(0xAFB1, "Y=A: status code (also used as station-table key)",
        inline=True)
comment(0xAFB2, "Restore status into A for the compare", inline=True)
comment(0xAFB3, "Step station-table index", inline=True)
comment(0xAFB4, "Compare with table[X] at &C230 (per-station status)",
        inline=True)
comment(0xAFB7, "Match: verify station address still matches", inline=True)
comment(0xAFB9, "Reached end of 16-slot table?", inline=True)
comment(0xAFBB, "No: keep scanning", inline=True)
comment(0xAFBD, "All slots tested, no match: A=0", inline=True)
comment(0xAFBF, "Always taken: jump to send-status", inline=True)
# verify_stn_match
comment(0xAFC1, "Y = matching index", inline=True)
comment(0xAFC2, "Verify station/network at this slot still matches "
        "caller", inline=True)
comment(0xAFC5, "Mismatch: station moved, keep scanning", inline=True)
comment(0xAFC7, "Read connection-active flag at &C260+X", inline=True)
comment(0xAFCA, "Mask to bit 0 (active flag)", inline=True)
# Send the status
comment(0xAFCC, "Y=0: TX[0] = control byte", inline=True)
comment(0xAFCE, "OR active-flag bit into the status", inline=True)
comment(0xAFD0, "Save the combined status", inline=True)
comment(0xAFD1, "Write it to TX[0]", inline=True)
comment(0xAFD3, "Send the disconnect packet via four-way handshake",
        inline=True)
comment(0xAFD6, "A=&FF: sentinel", inline=True)
comment(0xAFD8, "Y=8: TX[8] / TX[9] = packet trailer markers", inline=True)
comment(0xAFDA, "Write &FF at TX[8]", inline=True)
comment(0xAFDC, "Step Y", inline=True)
comment(0xAFDD, "Write &FF at TX[9]", inline=True)
comment(0xAFDF, "Pull the saved status", inline=True)
comment(0xAFE0, "Move into X for the test", inline=True)
comment(0xAFE1, "Y=&D1: control byte for ack-mode TXCB[1]", inline=True)
comment(0xAFE3, "Pull caller's original A again (was double-saved)",
        inline=True)
comment(0xAFE4, "Push it back", inline=True)
comment(0xAFE5, "A=0: skip the override", inline=True)
comment(0xAFE7, "Non-zero: use Y=&90 (FS reply port instead)",
        inline=True)
# store_tx_ctrl_byte
comment(0xAFE9, "Move chosen control/port into A", inline=True)
comment(0xAFEA, "Y=1: TX[1] is the port byte", inline=True)
comment(0xAFEC, "Write to TX[1]", inline=True)
comment(0xAFEE, "Move saved status into A", inline=True)
comment(0xAFEF, "Y=0: TX[0] for ack poll", inline=True)
comment(0xAFF0, "Push the status (we'll EOR with reply below)",
        inline=True)
# Wait for ACK with bit-flip detection
comment(0xAFF1, "A=&7F: marker pattern", inline=True)
comment(0xAFF3, "Write to TX[0]", inline=True)
comment(0xAFF5, "Wait for the TX/RX flip", inline=True)
comment(0xAFF8, "Pull saved status (peek without consuming)",
        inline=True)
comment(0xAFF9, "Push it back", inline=True)
comment(0xAFFA, "EOR with TX[0]: zero iff reply matches saved",
        inline=True)
comment(0xAFFC, "Rotate result; C set if bit 0 differs",
        inline=True)
comment(0xAFFD, "C set: keep waiting", inline=True)
comment(0xAFFF, "Discard saved status", inline=True)
comment(0xB000, "Discard caller's saved A", inline=True)
comment(0xB001, "Return", inline=True)

# net_1_read_handle / net_2_read_entry inline comments
comment(0xA3FF, "Y=&6F: net_rx_ptr offset for the 'inline' handle byte",
        inline=True)
comment(0xA401, "Read handle byte directly from RX buffer", inline=True)
comment(0xA403, "C clear: read-handle path -- store directly to PB",
        inline=True)
# net_2_read_entry
comment(0xA405, "Convert PB pointer to workspace table offset",
        inline=True)
comment(0xA408, "Out of range: return zero (uninitialised)", inline=True)
comment(0xA40A, "Read workspace handle byte", inline=True)
comment(0xA40C, "Slot marked '?' (uninitialised)?", inline=True)
comment(0xA40E, "Has a real handle: keep it and store", inline=True)
comment(0xA410, "Force result to zero (uninitialised marker)",
        inline=True)
comment(0xA412, "Write into PB[0] (handle return slot)", inline=True)
comment(0xA414, "Return", inline=True)

# net_3_close_handle inline comments
comment(0xA415, "Convert PB pointer to workspace table offset",
        inline=True)
comment(0xA418, "Out of range: mark as uninitialised", inline=True)
comment(0xA41A, "Shift bit 0 of fs_flags into C (save state)",
        inline=True)
comment(0xA41D, "Read PB[0] (the handle to close)", inline=True)
comment(0xA41F, "Shift bit 7 of A into C", inline=True)
comment(0xA420, "Restore C into bit 0 of fs_flags", inline=True)
comment(0xA423, "Return; the close action is dispatched elsewhere "
        "based on the saved C state", inline=True)

# mark_ws_uninit inline comments
comment(0xA424, "Save bit 0 of econet_flags", inline=True)
comment(0xA427, "A='?': uninitialised marker", inline=True)
comment(0xA429, "Write '?' to workspace[Y] (the slot is now free)",
        inline=True)
comment(0xA42B, "Restore bit 0 of econet_flags", inline=True)
comment(0xA42E, "Return", inline=True)

# recv_and_process_reply inline comments (~70 items)
# Setup
comment(0x97CD, "Save flags so caller's V/C survive the receive",
        inline=True)
comment(0x97CE, "Set up open RX on port &90 for the FS reply (TXCB[0] "
        "= &90, ctrl = &7F)", inline=True)
comment(0x97D1, "Wait for the reply via the 3-level stack timer",
        inline=True)
comment(0x97D4, "Restore caller's flags", inline=True)
# Reply byte iteration
comment(0x97D5, "Step Y to next reply byte", inline=True)
comment(0x97D6, "Read reply byte at txcb_start+Y", inline=True)
comment(0x97D8, "Stash for the dispatch tests below", inline=True)
comment(0x97D9, "Zero terminates: return", inline=True)
comment(0x97DB, "V clear (caller's V): use code as-is", inline=True)
comment(0x97DD, "V set: shift the code by +&2A (extended-error mapping)",
        inline=True)
comment(0x97DF, "Non-zero: dispatch as an error", inline=True)
comment(0x97E1, "Return", inline=True)
# handle_disconnect
comment(0x97E2, "Pull caller's pushed return state", inline=True)
comment(0x97E3, "X=&C0: 'remote disconnect' status", inline=True)
comment(0x97E5, "Step Y past the disconnect byte", inline=True)
comment(0x97E6, "Send disconnect notification to remote", inline=True)
comment(0x97E9, "C clear (success): continue scanning replies",
        inline=True)
# store_reply_status
comment(0x97EB, "Save the error code into &C009", inline=True)
comment(0x97EE, "Read FS state byte at &C007", inline=True)
comment(0x97F1, "Save flags so we can branch later", inline=True)
comment(0x97F2, "FS state non-zero: data-loss check needed", inline=True)
comment(0x97F4, "Reply was &BF (special: not a real error)?",
        inline=True)
comment(0x97F6, "No: build error block", inline=True)
# check_data_loss path
comment(0x97F8, "A=&40: 'channel-active' bitmask", inline=True)
comment(0x97FA, "Push it onto the OR-accumulator", inline=True)
comment(0x97FB, "Clear the FS-active bit (we're losing the connection)",
        inline=True)
comment(0x97FE, "X=&F0: scan from channel offset &F0 upwards",
        inline=True)
# loop_scan_channels
comment(0x9800, "Pull current OR accumulator", inline=True)
comment(0x9801, "OR with channel status byte at &C1C8+X", inline=True)
comment(0x9804, "Push back updated accumulator", inline=True)
comment(0x9805, "Reload channel byte", inline=True)
comment(0x9808, "Mask to top 2 bits (preserve TX/RX state)",
        inline=True)
comment(0x980A, "Write back trimmed status", inline=True)
comment(0x980D, "Step channel index", inline=True)
comment(0x980E, "Loop while X bit 7 set (covers &F0..&FF)", inline=True)
comment(0x9810, "Clear the FS state byte (no longer active)",
        inline=True)
comment(0x9813, "Force-close all client channels", inline=True)
comment(0x9816, "Pull final OR accumulator", inline=True)
comment(0x9817, "Bit 0 (was bit 6 of any &40 byte) -> C",
        inline=True)
comment(0x9818, "Any channel was active: skip the warning", inline=True)
comment(0x981A, "No active channels were lost: print 'Data Lost' "
        "warning via inline string", inline=True)
# After warning / data-loss return
comment(0x9827, "Reload error code from &C009", inline=True)
comment(0x982A, "Restore saved flags (was bit 7 of fs_flags)",
        inline=True)
comment(0x982B, "Z set (no error): build the error block anyway",
        inline=True)
comment(0x982D, "Pull caller's saved return state (3 bytes from PHP "
        "earlier)", inline=True)
comment(0x9830, "Return -- caller dispatched on a non-error reply",
        inline=True)
# build_error_block
comment(0x9831, "Y=1: skip past the leading TXCB control byte",
        inline=True)
comment(0x9833, "Error code below &A8 (extended)?", inline=True)
comment(0x9835, "No (>= &A8): proceed to copy", inline=True)
comment(0x9837, "Yes: clamp to &A8 (truncate range)", inline=True)
comment(0x9839, "Write clamped code back into TXCB", inline=True)
comment(0x983B, "Y=&FF: INY in loop bumps to 0", inline=True)
comment(0x983D, "Step Y", inline=True)
comment(0x983E, "Read TXCB byte (error block content)", inline=True)
comment(0x9840, "Copy to BRK error block at &0100+Y", inline=True)
comment(0x9843, "EOR with CR; Z set when we just copied the terminator",
        inline=True)
comment(0x9845, "Not yet at CR: continue copying", inline=True)
comment(0x9847, "Write the CR terminator (Z still set so A=0; ensures "
        "cleanly terminated)", inline=True)
comment(0x984A, "Step Y back so it points at the CR position",
        inline=True)
comment(0x984B, "Move Y into A for the BRK", inline=True)
comment(0x984C, "Move Y into X (caller convention)", inline=True)
comment(0x984D, "Tail-jump into the BRK-dispatch error path",
        inline=True)
comment(0x8A8F, "Service call &24 (Dynamic Workspace requirements)?", inline=True)
comment(0x8A91, "No: skip ADLC check", inline=True)
comment(0x8A93, "Read ADLC status register 1", inline=True)
comment(0x8A96, "Mask relevant status bits", inline=True)
comment(0x8A98, "Non-zero: ADLC absent, set flag", inline=True)
comment(0x8A9A, "Shift bit 7 into carry", inline=True)
comment(0x8A9D, "Set carry to mark ADLC absent", inline=True)
comment(0x8A9E, "Rotate carry into bit 7 of slot flag", inline=True)
comment(0x8AA1, "Load ROM slot flag byte", inline=True)
comment(0x8AA4, "Shift bit 7 (ADLC absent) into carry", inline=True)
comment(0x8AA5, "Restore service call number", inline=True)
comment(0x8AA6, "ADLC present: continue dispatch", inline=True)
comment(0x8AA8, "ADLC absent: decline service, return", inline=True)
comment(0x8AA9, "Transfer service number to X", inline=True)
comment(0x8AAA, "Save current service state", inline=True)
comment(0x8AAC, "Push old state", inline=True)
comment(0x8AAD, "Restore service number to A", inline=True)
comment(0x8AAE, "Store as current service state", inline=True)
comment(0x8AB0, "Service < 13?", inline=True)
comment(0x8AB2, "Yes: use as dispatch index directly", inline=True)
comment(0x8AB4, "Subtract 5 (map 13-17 to 8-12)", inline=True)
comment(0x8AB6, "Mapped value = 13? (original was 18)", inline=True)
comment(0x8AB8, "Yes: valid service 18 (FS select)", inline=True)
comment(0x8ACE, "Unknown service: set index to 0", inline=True)
comment(0x8AD0, "Transfer dispatch index to X", inline=True)
comment(0x8AD1, "Index 0: unhandled service, skip", inline=True)
comment(0x8AD3, "Save current workspace page", inline=True)
comment(0x8AD5, "Push old page", inline=True)
comment(0x8AD6, "Set workspace page from Y parameter", inline=True)
comment(0x8AD8, "Transfer Y to A", inline=True)
comment(0x8AD9, "Y=0 for dispatch offset", inline=True)
comment(0x8ADB, "Dispatch to service handler via table", inline=True)
comment(0x8ADE, "Restore old workspace page", inline=True)
comment(0x8ADF, "Store it back", inline=True)
comment(0x8AE1, "Get service state (return code)", inline=True)
comment(0x8AE3, "Restore old service state", inline=True)
comment(0x8AE4, "Store it back", inline=True)
comment(0x8AE6, "Transfer return code to A", inline=True)
comment(0x8AE7, "Restore ROM slot to X", inline=True)
comment(0x8AE9, "Return to MOS", inline=True)
comment(0x8AEA, "Offset 0 in receive block", inline=True)
comment(0x8AEC, "Load remote operation flag", inline=True)
comment(0x8AEE, "Zero: already off, skip to cleanup", inline=True)
comment(0x8AF0, "A=0", inline=True)
comment(0x8AF3, "Clear remote operation flag", inline=True)
comment(0x8AF6, "OSBYTE &C9: keyboard disable", inline=True)
comment(0x8AFB, "A=&0A: workspace init parameter", inline=True)
comment(0x8AFD, "Initialise workspace area", inline=True)
comment(0x8B00, "Save X in workspace", inline=True)
comment(0x8B02, "A=&CE: start of key range", inline=True)
comment(0x8B04, "Restore X from workspace", inline=True)
comment(0x8B06, "Y=&7F: OSBYTE scan parameter", inline=True)
comment(0x8B08, "OSBYTE: scan keyboard", inline=True)
comment(0x8B0B, "Advance to next key code", inline=True)
comment(0x8B0D, "Reached &D0?", inline=True)
comment(0x8B0F, "No: loop back (scan &CE and &CF)", inline=True)
comment(0x8B11, "A=0", inline=True)
comment(0x8B13, "Clear service state", inline=True)
comment(0x8B15, "Clear workspace byte", inline=True)
comment(0x8B17, "Return", inline=True)
comment(0x8B18, "Save A", inline=True)
comment(0x8B19, "Copy OS text pointer low", inline=True)
comment(0x8B1B, "to fs_crc_lo", inline=True)
comment(0x8B1D, "Copy OS text pointer high", inline=True)
comment(0x8B1F, "to fs_crc_hi", inline=True)
comment(0x8B21, "Restore A", inline=True)
comment(0x8B22, "Return", inline=True)
comment(0x8B23, "Get workspace page for this ROM slot", inline=True)
comment(0x8B26, "Store as high byte of load address", inline=True)
comment(0x8B28, "A=0", inline=True)
comment(0x8B2A, "Clear low byte of load address", inline=True)
comment(0x8B2C, "Clear carry for addition", inline=True)
comment(0x8B2D, "Y=&76: checksum range end", inline=True)
comment(0x8B2F, "Add byte to running checksum", inline=True)
comment(0x8B31, "Decrement index", inline=True)
comment(0x8B32, "Loop until all bytes summed", inline=True)
comment(0x8B34, "Y=&77: checksum storage offset", inline=True)
comment(0x8B36, "Compare with stored checksum", inline=True)
comment(0x8B4D, "Test fs_flags bit 7 (ANFS active)", inline=True)
comment(0x8B50, "Already active: tail-RTS via shared exit",
        inline=True)
comment(0x8B52, "Auto-select ANFS via the *NFS handler",
        inline=True)
comment(0x8B55, "Z=1 (A=0): selection succeeded", inline=True)
comment(0x8B57, "Otherwise raise 'net checksum' error",
        inline=True)
comment(0x8B60, "Call FSCV with A=6 (new FS)", inline=True)
comment(0x8B63, "Y=9: end of FS context block", inline=True)
comment(0x8B65, "Load byte from receive block", inline=True)
comment(0x8B67, "Store into FS workspace", inline=True)
comment(0x8B6A, "Decrement index", inline=True)
comment(0x8B6B, "Reached offset 1?", inline=True)
comment(0x8B6D, "No: continue copying", inline=True)
comment(0x8B6F, "Shift bit 7 of FS flags into carry", inline=True)
comment(0x8B72, "Clear carry", inline=True)
comment(0x8B73, "Clear bit 7 of FS flags", inline=True)
comment(0x8B76, "Y=&0D: vector table size - 1", inline=True)
comment(0x8B78, "Load FS vector address", inline=True)
comment(0x8B7B, "Store into FILEV vector table", inline=True)
comment(0x8B7E, "Decrement index", inline=True)
comment(0x8B7F, "Loop until all vectors installed", inline=True)
comment(0x8B81, "Initialise ADLC and NMI workspace", inline=True)
comment(0x8B84, "Y=&1B: extended vector offset", inline=True)
comment(0x8B86, "X=7: two more vectors to set up", inline=True)
comment(0x8B88, "Set up extended vectors", inline=True)
comment(0x8B8B, "A=0", inline=True)
comment(0x8B8D, "Clear FS state byte", inline=True)
comment(0x8B90, "Clear workspace byte", inline=True)
comment(0x8B93, "Clear workspace byte", inline=True)
comment(0x8B96, "Clear receive attribute byte", inline=True)
comment(0x8B99, "Clear workspace byte", inline=True)
comment(0x8B9C, "Set up workspace pointers", inline=True)
comment(0x8B9F, "Initialise FS state", inline=True)
comment(0x8BA2, "Y=&77: workspace block size - 1", inline=True)
comment(0x8BA4, "Load byte from source workspace", inline=True)
comment(0x8BA6, "Store to page &10 shadow copy", inline=True)
comment(0x8BA9, "Decrement index", inline=True)
comment(0x8BAA, "Loop until all bytes copied", inline=True)
comment(0x8BAC, "A=&80: FS selected flag", inline=True)
comment(0x8BBB, "X=&35: NFS command table offset", inline=True)
comment(0x8BBD, "Print help for NFS commands", inline=True)
comment(0x8BC0, "X=0: utility command table offset", inline=True)
comment(0x8BC4, "X=&35: NFS command table offset", inline=True)
comment(0x8BC6, "V clear: take newline-only path (skip version header)", inline=True)
comment(0x8BCF, "Clear overflow flag", inline=True)
comment(0x8BD5, "Save Y (command line offset)", inline=True)
comment(0x8BD6, "Push it", inline=True)
comment(0x8BD7, "Save processor status", inline=True)
comment(0x8BD8, "Load byte from command table", inline=True)
comment(0x8BDB, "Bit 7 clear: valid entry, continue", inline=True)
comment(0x8BDD, "End of table: finish up", inline=True)
comment(0x8BE0, "Print two-space indent", inline=True)
comment(0x8BED, "Advance table pointer", inline=True)
comment(0x8BEE, "Decrement padding counter", inline=True)
comment(0x8BEF, "Load next character", inline=True)
comment(0x8BF2, "Bit 7 clear: more chars, continue", inline=True)
comment(0x8BF4, "Pad with spaces", inline=True)
comment(0x8BF9, "Decrement remaining pad count", inline=True)
comment(0x8BFA, "More padding needed: loop", inline=True)
comment(0x8BFC, "Load syntax descriptor byte", inline=True)
comment(0x8BFF, "Mask to get syntax string index", inline=True)
comment(0x8C01, "Use index as Y", inline=True)
comment(0x8C02, "Look up syntax string offset", inline=True)
comment(0x8C05, "Transfer offset to Y", inline=True)
comment(0x8C06, "Advance to next character", inline=True)
comment(0x8C07, "Load syntax string character", inline=True)
comment(0x8C0A, "Zero terminator: end of syntax", inline=True)
comment(0x8C0C, "Carriage return: line continuation", inline=True)
comment(0x8C0E, "No: print the character", inline=True)
comment(0x8C10, "Handle line wrap in syntax output", inline=True)
comment(0x8C13, "Continue with next character", inline=True)
comment(0x8C19, "Continue with next character", inline=True)
comment(0x8C1F, "X += 3: skip syntax descriptor and address", inline=True)
comment(0x8C20, "(continued)", inline=True)
comment(0x8C21, "(continued)", inline=True)
comment(0x8C22, "Loop for next command", inline=True)
comment(0x8C25, "Restore processor status", inline=True)
comment(0x8C26, "Restore Y", inline=True)
comment(0x8C27, "Transfer to Y", inline=True)
comment(0x8C28, "Return", inline=True)
comment(0x8C29, "Read output stream type", inline=True)
comment(0x8C2C, "Stream 0 (VDU): no wrapping", inline=True)
comment(0x8C2E, "Stream 3 (printer)?", inline=True)
comment(0x8C30, "Yes: no wrapping", inline=True)
comment(0x8C36, "Y=&0B: indent width - 1", inline=True)
comment(0x8C38, "Space character", inline=True)
comment(0x8C3D, "Decrement indent counter", inline=True)
comment(0x8C3E, "More spaces needed: loop", inline=True)
comment(0x8C41, "Return", inline=True)
comment(0x8C42, "X=0: start of utility command table", inline=True)
comment(0x8C44, "Get command line offset", inline=True)
comment(0x8C46, "Save text pointer to fs_crc", inline=True)
comment(0x8C49, "Try to match command in table", inline=True)
comment(0x8C4C, "No match: return to caller", inline=True)
comment(0x8C4E, "Match found: execute command", inline=True)
comment(0x8C51, "Check for credits Easter egg", inline=True)
comment(0x8C54, "Get command line offset", inline=True)
comment(0x8C56, "Load character at offset", inline=True)
comment(0x8C58, "Is it CR (bare *HELP)?", inline=True)
comment(0x8C5A, "No: check for specific topic", inline=True)
comment(0x8C5C, "Print version string", inline=True)
comment(0x8C5F, "X=&91: start of help command list", inline=True)
comment(0x8C61, "Print command list from table", inline=True)
comment(0x8C64, "Restore Y (command line offset)", inline=True)
comment(0x8C66, "Return unclaimed", inline=True)
comment(0x8C67, "Test for topic match (sets flags)", inline=True)
comment(0x8C6A, "Is first char '.' (abbreviation)?", inline=True)
comment(0x8C6C, "No: try topic-specific help", inline=True)
comment(0x8C6E, "'.' found: show full command list", inline=True)
comment(0x8C71, "Save text pointer to fs_crc", inline=True)
comment(0x8C74, "Save flags", inline=True)
comment(0x8C75, "X=&91: help command table start", inline=True)
comment(0x8C77, "Try to match help topic in table", inline=True)
comment(0x8C7A, "No match: try next topic", inline=True)
comment(0x8C7C, "Restore flags", inline=True)
comment(0x8C7D, "Push return address high (&8C)", inline=True)
comment(0x8C7F, "Push it for RTS dispatch", inline=True)
comment(0x8C80, "Push return address low (&74)", inline=True)
comment(0x8C82, "Push it for RTS dispatch", inline=True)
comment(0x8C83, "Load dispatch address high", inline=True)
comment(0x8C86, "Push dispatch high for RTS", inline=True)
comment(0x8C87, "Load dispatch address low", inline=True)
comment(0x8C8A, "Push dispatch low for RTS", inline=True)
comment(0x8C8B, "Dispatch via RTS (returns to &8C80)", inline=True)
comment(0x8C8C, "Restore flags from before match", inline=True)
comment(0x8C8D, "End of command line?", inline=True)
comment(0x8C8F, "No: try matching next topic", inline=True)
comment(0x8C93, "Print version string via inline", inline=True)
comment(0x8CBB, "Transfer to Y", inline=True)
comment(0x8CBC, "Return with page in A and Y", inline=True)
comment(0x8CBD, "Get workspace page for ROM slot", inline=True)
comment(0x8CC0, "Store page in nfs_temp", inline=True)
comment(0x8CC2, "A=0", inline=True)
comment(0x8CC4, "Clear low byte of pointer", inline=True)
comment(0x8CC6, "Return", inline=True)
comment(0x8CC7, "OSBYTE &7A: scan keyboard from key 16", inline=True)
comment(0x8CCD, "No key pressed: select Net FS", inline=True)
comment(0x8CCF, "Key &19 (N)?", inline=True)
comment(0x8CD1, "Yes: write key state and boot", inline=True)
comment(0x8CD3, "EOR with &55: maps to zero if 'N'", inline=True)
comment(0x8CD5, "Not N key: return unclaimed", inline=True)
comment(0x8CD8, "OSBYTE &78: write keys pressed", inline=True)
comment(0x8CDD, "Select NFS as current filing system", inline=True)
comment(0x8CE4, "Print station number", inline=True)
comment(0x8CEA, "Get workspace page", inline=True)
comment(0x8CEC, "Non-zero: already initialised, return", inline=True)
comment(0x8CEE, "Load boot flags", inline=True)
comment(0x8CF1, "Set bit 2 (auto-boot in progress)", inline=True)
comment(0x8CF3, "Store updated boot flags", inline=True)
comment(0x8CF6, "X=&1C: boot filename address low", inline=True)
comment(0x8CF8, "Y=&8D: boot filename address high", inline=True)
comment(0x8CFA, "Execute boot file", inline=True)
comment(0x8CFF, "Tail-jump via FSCV vector "
    "(filing-system change service)", inline=True)
comment(0x8D02, "X=&0F: service 15 (vectors claimed)",
    inline=True)
comment(0x8D04, "A=&8F: OSBYTE 'Issue paged-ROM service request'",
    inline=True)
comment(0x8CFD, "A=6: notify new filing system", inline=True)
comment(0x8D26, "X=5: start of credits keyword", inline=True)
comment(0x8D28, "Load character from command line", inline=True)
comment(0x8D2A, "Compare with credits keyword", inline=True)
comment(0x8D2D, "Mismatch: check if keyword complete", inline=True)
comment(0x8D2F, "Advance command line pointer", inline=True)
comment(0x8D30, "Advance keyword pointer", inline=True)
comment(0x8D31, "Continue matching", inline=True)
comment(0x8D33, "Reached end of keyword (X=&0D)?", inline=True)
comment(0x8D35, "No: keyword not fully matched, return", inline=True)
comment(0x8D37, "X=0: start of credits text", inline=True)
comment(0x8D39, "Load character from credits string", inline=True)
comment(0x8D3C, "Zero terminator: done printing", inline=True)
comment(0x8D41, "Advance string pointer", inline=True)
comment(0x8D42, "Continue printing", inline=True)
comment(0x8D44, "Return", inline=True)
comment(0x8D91, "OSBYTE &77: close SPOOL/EXEC", inline=True)
comment(0x8D93, "Store as pending operation marker", inline=True)
comment(0x8D99, "Y=0", inline=True)
comment(0x8D9B, "Clear password entry flag", inline=True)
comment(0x8D9D, "Reset FS connection state", inline=True)
comment(0x8DAA, "Load first option byte", inline=True)
comment(0x8DAC, "Parse station number if present", inline=True)
comment(0x8DAF, "Not a digit: skip to password entry", inline=True)
comment(0x8DB1, "Parse user ID string", inline=True)
comment(0x8DB4, "No user ID: go to password", inline=True)
comment(0x8DC0, "No FS address: skip to password", inline=True)
comment(0x8DB6, "Store file server station low", inline=True)
comment(0x8DB9, "Check and store FS network", inline=True)
comment(0x8DBC, "Skip separator", inline=True)
comment(0x8DBD, "Parse next argument", inline=True)
comment(0x8DC2, "Store file server station high", inline=True)
comment(0x8DC5, "X=&FF: pre-decrement for loop", inline=True)
comment(0x8DC7, "Advance index", inline=True)
comment(0x8DC8, "Load logon command template byte", inline=True)
comment(0x8DCB, "Store into transmit buffer", inline=True)
comment(0x8DCE, "Bit 7 clear: more bytes, loop", inline=True)
comment(0x8DD0, "Send logon with file server lookup", inline=True)
comment(0x8DD3, "Success: skip to password entry", inline=True)
comment(0x8DD5, "Build FS command packet", inline=True)
comment(0x8DD8, "Y=&FF: pre-increment for loop", inline=True)
comment(0x8DDA, "Advance to next byte", inline=True)
comment(0x8DDB, "Load byte from reply buffer", inline=True)
comment(0x8DDE, "Is it CR (end of prompt)?", inline=True)
comment(0x8DE0, "Yes: no colon found, skip to send", inline=True)
comment(0x8DE2, "Is it ':' (password prompt)?", inline=True)
comment(0x8DE4, "No: keep scanning", inline=True)
comment(0x8DE9, "Save position of colon", inline=True)
comment(0x8DEB, "A=&FF: mark as escapable", inline=True)
comment(0x8DED, "Set escape flag", inline=True)
comment(0x8DEF, "Check for escape condition", inline=True)
comment(0x8DF7, "Not NAK (&15): check other chars", inline=True)
comment(0x8DF9, "Restore colon position", inline=True)
comment(0x8DFB, "Non-zero: restart from colon", inline=True)
comment(0x8DFD, "At colon position?", inline=True)
comment(0x8DFF, "Yes: restart password input", inline=True)
comment(0x8E01, "Backspace: move back one character", inline=True)
comment(0x8E02, "If not at start: restart input", inline=True)
comment(0x8E04, "Delete key (&7F)?", inline=True)
comment(0x8E06, "Yes: handle backspace", inline=True)
comment(0x8E08, "Store character in password buffer", inline=True)
comment(0x8E0B, "Advance buffer pointer", inline=True)
comment(0x8E0C, "Is it CR (end of password)?", inline=True)
comment(0x8E0E, "No: read another character", inline=True)
comment(0x8E13, "Transfer string length to A", inline=True)
comment(0x8E14, "Save string length", inline=True)
comment(0x8E15, "Set up transmit control block", inline=True)
comment(0x8E18, "Send to file server and get reply", inline=True)
comment(0x8E1C, "Include terminator", inline=True)
comment(0x8E1D, "Y=0", inline=True)
comment(0x8E21, "Ensure bridge initialised; A=spool_control_flag (bridge status)", inline=True)
comment(0x8E24, "EOR with hazel_fs_network: zero result if equal", inline=True)
comment(0x8E27, "Different: return without clearing", inline=True)
comment(0x8E29, "Same: clear station byte", inline=True)
comment(0x8E2C, "Return", inline=True)
comment(0x8E2D, "Y=0: first character offset", inline=True)
comment(0x8E38, "Build FS command packet", inline=True)
comment(0x8E2F, "Load first character of command text", inline=True)
comment(0x8E3B, "Transfer result to Y", inline=True)
comment(0x8E31, "Is it '&' (URD prefix)?", inline=True)
comment(0x8E3C, "Set up command and send to FS", inline=True)
comment(0x8E33, "No: send as normal FS command", inline=True)
comment(0x8E3F, "Load reply function code", inline=True)
comment(0x8E35, "Yes: route via *RUN for URD prefix handling", inline=True)
comment(0x8E42, "Zero: no reply, return", inline=True)
comment(0x8E44, "Load first reply byte", inline=True)
comment(0x8E47, "Y=&25: logon dispatch offset", inline=True)
comment(0x8E4B, "Parse reply as decimal number", inline=True)
comment(0x8E4E, "Result >= 8?", inline=True)
comment(0x8E50, "Yes: out of range, return", inline=True)
comment(0x8E52, "Transfer handle to X", inline=True)
comment(0x8E53, "Look up in open files table", inline=True)
comment(0x8E56, "Transfer result to A", inline=True)
comment(0x8E57, "Y=&1D: handle dispatch offset", inline=True)
comment(0x8E5B, "Handle >= 5?", inline=True)
comment(0x8E5D, "Yes: out of range, return", inline=True)
comment(0x8E5F, "Y=&18: settles X_final to &19..&1D (lang reply 0..4)", inline=True)
comment(0x8E61, "Advance X to target index", inline=True)
comment(0x8E63, "Y still positive: continue counting", inline=True)
comment(0x8E62, "Decrement Y offset counter", inline=True)
comment(0x8E65, "Y=&FF: will be ignored by caller", inline=True)
comment(0x8E66, "Load dispatch address high byte", inline=True)
comment(0x8E69, "Push high byte for RTS dispatch", inline=True)
comment(0x8E6A, "Load dispatch address low byte", inline=True)
comment(0x8E6D, "Push low byte for RTS dispatch", inline=True)
comment(0x8E6E, "Load FS options pointer", inline=True)
comment(0x8E70, "Dispatch via RTS", inline=True)

# noop_dey_rts (&8E71) -- Master 128 service &24 handler:
# "Dynamic Workspace requirements". The doc reads: "Y contains
# current bottom of dynamic allocation and should be decremented
# by required number of pages". ANFS claims 1 page of dynamic
# workspace -- DEY decrements Y by 1, RTS returns the new bottom.
comment(0x8E71, "Claim 1 page (DEY = decrement Y by 1)", inline=True)
comment(0x8E72, "Return", inline=True)

# copy_template_to_zp (&8E73) -- Master 128 service &25 handler:
# "Inform MOS of filing system name and info". Copies the 11-byte
# template at &8E7F..&8E89 into the caller's workspace pointed at
# by (&F2),Y, X-counted down from 10 to 0.
comment(0x8E73, "X = 10 (top of 11-byte template)", inline=True)
comment(0x8E75, "Load template byte X from &8E7F+X", inline=True)
comment(0x8E78, "Store at (&F2),Y", inline=True)
comment(0x8E7A, "Advance destination cursor", inline=True)
comment(0x8E7B, "Step to previous template byte", inline=True)
comment(0x8E7C, "Loop until X has wrapped past 0", inline=True)
comment(0x8E7E, "Return", inline=True)
comment(0x8E80, "11-byte template (length 5 in [0], then '       TEN'); "
    "copied to (&F2),Y by copy_template_to_zp", inline=True)

# svc_26_close_all_files (&8E8A) -- Master 128 service &26 handler:
# "Close all files". Tests bit 6 of fs_flags (&0D6C); when clear
# (NFS not currently selected), returns without acting. When set,
# ensures NFS is selected (since the doc requires "filing systems
# should select themselves, close open files and then de-select"),
# clears A/Y and tail-jumps to findv_handler with Y=0 -- the
# FILEV "close all files" sub-call.
comment(0x8E8A, "Test bit 6 of fs_flags (NFS currently selected?)", inline=True)
comment(0x8E8D, "Clear: return without acting", inline=True)
comment(0x8E8F, "Ensure NFS is the selected FS", inline=True)
comment(0x8E92, "A=0", inline=True)
comment(0x8E94, "Y=0 -- FILEV 'close all files' sub-call", inline=True)
comment(0x8E95, "Tail-call findv_handler (= FILEV)", inline=True)

# Printer server template data (8 bytes). Read indirectly by
# copy_ps_data via LDA ps_template_base,X with X=&F8..&FF,
# reaching ps_template_base+&F8 = &8E9F. Default PS name
# "PRINT " followed by status bytes &01, &00.
comment(0x8E9F, "Printer server template (8 bytes)\n"
    "\n"
    "Default printer server configuration data, read\n"
    "indirectly by copy_ps_data via LDA ps_template_base,X\n"
    "with X=&F8..&FF (reaching ps_template_base+&F8 =\n"
    "&8E9F). Contains \"PRINT \" (6 bytes) as the default\n"
    "printer server name, followed by &01 and &00 as\n"
    "default status bytes. Absent from NFS versions;\n"
    "unique to ANFS.")
comment(0x8E9F, "PS template: default name \"PRINT \"", inline=True)


# NETV handler address pair at &8E8A. Read by write_vector_entry
# via LDA svc_dispatch_lo_offset,Y at Y=&36/&37. Interleaved
# with OSBYTE wrapper code at svc_dispatch_lo_offset + &30..&35.

comment(0x8ED4, "Y=0", inline=True)
comment(0x8ED8, "Get original OSBYTE A parameter", inline=True)
comment(0x8EDA, "Subtract &31 (map &32-&35 to 1-4)", inline=True)
comment(0x8EDC, "In range 0-3?", inline=True)
comment(0x8EDE, "No: not ours, return unclaimed", inline=True)
comment(0x8EE0, "Transfer to X as dispatch index", inline=True)
comment(0x8EE3, "Transfer Y to A (OSBYTE Y param)", inline=True)
comment(0x8EE4, "Y=&2F: OSBYTE dispatch offset", inline=True)
comment(0x8EE6, "Dispatch to OSBYTE handler via table", inline=True)
comment(0x8EE9, "Y already >= &C8?", inline=True)
comment(0x8EEB, "Yes: return Y unchanged", inline=True)
comment(0x8EED, "No: raise Y to &C8", inline=True)
comment(0x8EEF, "Return", inline=True)
comment(0x8EF0, "Transfer Y to A", inline=True)
comment(0x8EF2, "Y >= &D3?", inline=True)
comment(0x8EF4, "No: use Y as-is", inline=True)
comment(0x8EF6, "Cap at &D3", inline=True)
comment(0x8EF8, "Offset &0B in receive block", inline=True)
comment(0x8EFA, "Store workspace page count", inline=True)
comment(0x8EFD, "Return -- ws_page count saved", inline=True)
comment(0x8EFE, "Caller's page (in Y) into A", inline=True)
comment(0x8EFF, "Y = current ROM slot from romsel_copy", inline=True)
comment(0x8F04, "Publish page into rom_ws_pages[slot] "
    "(bit 7 cleared = workspace claimed)", inline=True)
comment(0x8F07, "Read Master break-type shadow (&FE2B)", inline=True)
comment(0x8F4D, "Zero: first ROM init, skip FS setup", inline=True)
comment(0x8F4F, "Set up workspace pointers", inline=True)
comment(0x8F52, "Clear FS flags", inline=True)
comment(0x8F55, "A=0, transfer to Y", inline=True)
comment(0x8F56, "Clear byte in FS workspace", inline=True)
comment(0x8F58, "Next workspace byte", inline=True)
comment(0x8F59, "Loop until full page (256 bytes) cleared", inline=True)
comment(0x8F74, "Y=2: nfs_workspace offset for FS station", inline=True)
comment(0x8F76, "Store FS station at (nfs_workspace)+2", inline=True)
comment(0x8F7A, "Read CMOS &04 (FS network)", inline=True)
comment(0x8F7E, "Y=3: nfs_workspace offset for FS network",
    inline=True)
comment(0x8F80, "Store at NFS workspace offset 2", inline=True)
comment(0x8F82, "X=3: init data byte count", inline=True)
comment(0x8F84, "Load initialisation data byte", inline=True)
comment(0x8F87, "Store in workspace", inline=True)
comment(0x8F8A, "Decrement counter", inline=True)
comment(0x8F8B, "More bytes: loop", inline=True)
comment(0x8F8D, "Clear workspace flag", inline=True)
comment(0x8F90, "Clear workspace byte", inline=True)
# ws_init_data (&8F48): 3 workspace initialisation bytes.
# Label overlaps last byte of JMP at &8F46 (classic 6502 trick).
# Loop reads ws_init_data+X with X=3,2,1, storing to fs_flags+X.
comment(0x8F93, "Initialise ADLC protection table", inline=True)
comment(0x8F96, "X=&FF (underflow from X=0)", inline=True)
comment(0x8FA9, "Get current workspace page", inline=True)
comment(0x8F97, "Initialise workspace flag to &FF", inline=True)
comment(0x8FAB, "Allocate FS handle page", inline=True)
comment(0x8FAE, "Allocation failed: finish init", inline=True)
comment(0x8FB0, "A=&3F: default handle permissions", inline=True)
comment(0x8FB2, "Store handle permissions", inline=True)
comment(0x8FB4, "Advance to next page", inline=True)
comment(0x8FB6, "Continue allocating: loop", inline=True)
comment(0x8FB8, "Restore FS context from saved state", inline=True)
comment(0x903C, "Initialise ADLC hardware", inline=True)
comment(0x903F, "OSBYTE &A8: read ROM pointer table", inline=True)
comment(0x9041, "Read ROM pointer table address", inline=True)
comment(0x9044, "Store table pointer low", inline=True)
comment(0x9046, "Store table pointer high", inline=True)
comment(0x9048, "Y=&36: NETV vector offset", inline=True)
comment(0x904A, "Set NETV address", inline=True)
comment(0x904D, "X=1: one more vector pair to set", inline=True)
comment(0x904F, "Load vector address low byte", inline=True)
comment(0x9052, "Store into extended vector table", inline=True)
comment(0x9054, "Advance to high byte", inline=True)
comment(0x9055, "Load vector address high byte", inline=True)
comment(0x9058, "Store into extended vector table", inline=True)
comment(0x905A, "Advance to ROM ID byte", inline=True)
comment(0x905B, "Load current ROM slot number", inline=True)
comment(0x905D, "Store ROM ID in extended vector", inline=True)
comment(0x905F, "Advance to next vector entry", inline=True)
comment(0x9060, "Decrement vector counter", inline=True)
comment(0x9061, "More vectors to set: loop", inline=True)
comment(0x9063, "Return", inline=True)
comment(0x9064, "Y=9: end of FS context block", inline=True)
comment(0x9066, "Load FS context byte", inline=True)
comment(0x9069, "Store into receive block", inline=True)
comment(0x906B, "Decrement index", inline=True)
comment(0x906C, "Reached offset 1?", inline=True)
comment(0x906E, "No: continue copying", inline=True)
comment(0x9070, "Return", inline=True)
comment(0x9071, "FS currently selected?", inline=True)
comment(0x9074, "No (bit 7 clear): return", inline=True)
comment(0x9076, "Y=0", inline=True)
comment(0x907B, "Restore FS context to receive block", inline=True)
comment(0x907E, "Y=&76: checksum range end", inline=True)
comment(0x9080, "A=0: checksum accumulator", inline=True)
comment(0x9082, "Clear carry for addition", inline=True)
comment(0x9083, "Add byte from page &10 shadow", inline=True)
comment(0x9086, "Decrement index", inline=True)
comment(0x9087, "Loop until all bytes summed", inline=True)
comment(0x9089, "Y=&77: checksum storage offset", inline=True)
comment(0x908D, "Load byte from page &10 shadow", inline=True)
comment(0x9090, "Copy to FS workspace", inline=True)
comment(0x9092, "Decrement index", inline=True)
comment(0x9093, "Loop until all bytes copied", inline=True)
comment(0x9095, "Load FS flags", inline=True)
comment(0x9098, "Clear bit 7 (FS no longer selected)", inline=True)
comment(0x909A, "Store updated flags", inline=True)
comment(0x909D, "Return", inline=True)
comment(0x909E, "Save processor status", inline=True)
comment(0x909F, "Save A", inline=True)
comment(0x90A1, "Y=&76: checksum range end", inline=True)
comment(0x90A3, "A=0: checksum accumulator", inline=True)
comment(0x90A5, "Clear carry for addition", inline=True)
comment(0x90A6, "Add byte from FS workspace", inline=True)
comment(0x90A8, "Decrement index", inline=True)
comment(0x90A9, "Loop until all bytes summed", inline=True)
comment(0x90AB, "Y=&77: checksum storage offset", inline=True)
comment(0x90AD, "Compare with stored checksum", inline=True)
comment(0x90AF, "Mismatch: raise checksum error", inline=True)
comment(0x90B2, "Restore A", inline=True)
comment(0x90B3, "Restore processor status", inline=True)
comment(0x90B4, "Return (checksum valid)", inline=True)
comment(0x90B5, "Error number &AA", inline=True)
comment(0x90B7, "Raise 'net checksum' error", inline=True)
comment(0x90CC, "Print 'Econet Station ' via inline", inline=True)
comment(0x90E0, "Space character", inline=True)
comment(0x90E2, "Check ADLC status register 2", inline=True)
comment(0x90E5, "Clock present: skip warning", inline=True)
comment(0x90E7, "Print ' No Clock' via inline", inline=True)
comment(0x90F3, "String terminator", inline=True)
comment(0x90F7, "Return", inline=True)

# syn_opt_dir (&9022-&910D): null-terminated *HELP syntax
# strings. Multi-line strings use &0D as a line break. Indexed
# via cmd_syntax_table offsets from the low 5 bits of each
# command table syntax descriptor byte.
comment(0x90F8, "*HELP command syntax strings\n"
    "\n"
    "13 null-terminated syntax help strings displayed\n"
    "by *HELP after each command name. Multi-line\n"
    "entries use &0D as a line break. Indexed by\n"
    "cmd_syntax_table via the low 5 bits of each\n"
    "command's syntax descriptor byte.")
comment(0x90F8, "Syn 1: *Dir, *LCat, *LEx, *Wipe", inline=True)
comment(0x9118, "Line break", inline=True)
comment(0x914C, "Syn 4 continued: address clause", inline=True)
comment(0x9158, "Null terminator", inline=True)
comment(0x9159, "Syn 5: *Lib", inline=True)
comment(0x9170, "Syn 7: *Pass", inline=True)
comment(0x91DF, "Null terminator", inline=True)
comment(0x91E0, "Syn 11: (station id. argument)", inline=True)

# cmd_syntax_table (&910E): 13-entry offset table for *HELP syntax.
# Each byte is an offset into syn_opt_dir (&9022). The print
# loop does INY before LDA, so the offset points to the byte before
# the first character of each syntax string.
comment(0x91ED, "Command syntax string offset table\n"
    "\n"
    "13 offsets into syn_opt_dir (&9022).\n"
    "Indexed by the low 5 bits of each command table\n"
    "syntax descriptor byte. Index &0E is handled\n"
    "separately as a shared-commands list. The print\n"
    "loop at &8BD5 does INY before LDA, so each offset\n"
    "points to the byte before the first character.")

comment(0x9236, "Save full byte", inline=True)
comment(0x9237, "Shift high nybble to low", inline=True)
comment(0x9238, "Continue shifting", inline=True)
comment(0x9239, "Continue shifting", inline=True)
comment(0x923A, "High nybble now in bits 0-3", inline=True)
comment(0x923B, "Print high nybble as hex digit", inline=True)
comment(0x923E, "Restore full byte", inline=True)
comment(0x923F, "Mask to low nybble", inline=True)
comment(0x9241, "Digit >= &0A?", inline=True)
comment(0x9243, "No: skip letter adjustment", inline=True)
comment(0x9245, "Add 7 to get 'A'-'F' (6 + carry)", inline=True)
comment(0x9247, "Add &30 for ASCII '0'-'9' or 'A'-'F'", inline=True)
comment(0x9763, "Offset 0: txcb_ctrl = &80 (TX command)", inline=True)
comment(0x9764, "Offset 1: txcb_port = &99 (FS command port)", inline=True)
comment(0x9765, "Offset 2: txcb_dest lo placeholder "
    "(overwritten with hazel_fs_station[0])", inline=True)
comment(0x9766, "Offset 3: txcb_dest hi placeholder "
    "(overwritten with hazel_fs_station[1])", inline=True)
comment(0x9767, "Offset 4: txcb_start lo = 0", inline=True)
comment(0x9768, "Offset 5: txcb_start hi = &C1 (data buffer "
    "starts at &C100 in HAZEL)", inline=True)
comment(0x9769, "Offset 6: padding &FF; doubles as the "
    "always_set_v_byte BIT $abs target", inline=True)
comment(0x976A, "Offset 7: txcb_pos = &FF "
    "(also labelled bit_test_ff)", inline=True)
comment(0x976B, "Offset 8: txcb_end lo = &FF", inline=True)
comment(0x976C, "Offset 9: txcb_end hi = &C1 "
    "(buffer end &C1FF)", inline=True)
comment(0x976D, "Offset 10: extended-addr fill (&FF)", inline=True)
comment(0x976E, "Offset 11: extended-addr fill (&FF)", inline=True)

# ============================================================
# Service dispatch table entry points (&89ED / &8A20)
# ============================================================
# The PHA/PHA/RTS dispatch table itself is declared further below as
# svc_dispatch_lo / svc_dispatch_hi (with one symbolic equb per entry);
# this section just registers entry() points for targets reached only
# via that dispatch (no other code path leads to them, so py8dis can't
# trace them statically).
entry(0x8D09)   # idx  2  workspace claim helper (CMOS bit 0)
# entry(0x8F10) declared above (svc_2 page-allocation prologue)
entry(0x8CC7)   # idx  4  svc_3 auto-boot
entry(0x8C42)   # idx  5  svc_4 unrecognised star command
entry(0x8ED8)   # idx  8  svc_7 unrecognised OSBYTE
entry(0x8C51)   # idx 10  svc_9 *HELP
# entry(0x8F38) declared above (nfs_init_body)
entry(0x8EE9)   # idx 16  raise_y_to_c8 (was: svc_1_abs_workspace, see O-2)

label(0x8EE9, "raise_y_to_c8")
label(0x8CC7, "svc_3_autoboot")
label(0x8C42, "svc_4_star_command")
label(0x8ED8, "svc_7_osbyte")
label(0x8C51, "svc_9_help")
# Labels for the dispatch targets recovered via the &89ED/&8A20 lo/hi
# decode. Names are best-effort; refine as routines are walked.
label(0xA83C, "svc_8_osword_disp")    # idx  9: alt entry to svc_8_osword
                                      #   (skips the BRA-from-elsewhere path)
label(0x969A, "match_on_suffix")      # idx 15 = Master svc &18 (Interactive HELP):
                                      # 'ON ' keyword matcher, runs file loader on match
# svc_dispatch slots &13/&14/&15 are short Master service handlers
# that all live in the gap between svc_dispatch's own RTS (&8E70) and
# svc_26_close_all_files's tail-call (&8E95). Declared as subroutines
# (further down) so each gets its own banner in the listing rather
# than reading like one confused fall-through region.
label(0xB0FE, "ps_scan_resume")           # idx 39: tail of pop_requeue_ps_scan
label(0xB357, "cmd_info_dispatch")        # idx 40: builds 'i.' prefix, JMPs &8E3C
label(0xA4DC, "check_urd_present")        # idx 41: BIT &0D6C / BVC ... / JMP &A5A1
label(0xB2DB, "ex_init_scan_x0")          # idx 42: LDX #0 -> loop_scan_entries

# ============================================================
# Symbolic svc_dispatch lo/hi tables (&89ED / &8A20)
# ============================================================
# Replaces the auto-classified bytes/strings (the original "A'o" /
# ";Pok" "strings" were just runs of printable lo bytes that py8dis's
# string heuristic latched onto). Each lo entry expands to <(target-1)
# and each hi entry to >(target-1) so PHA/PHA/RTS lands on `target`.
data_banner(0x89ED, "svc_dispatch_lo",
    title="svc_dispatch low-byte table (51 entries)",
    description="""\
Low-byte half of the `PHA`/`PHA`/`RTS` dispatch table read by
[`svc_dispatch`](address:8E61) as `LDA &89ED,X`. Paired with
the high-byte half at [`svc_dispatch_hi`](address:8A20).

Index 0 is a placeholder (target value unused – never reached);
indices 1..50 cover:

- service handlers
- language reply handlers
- FSCV reasons
- FS reply handlers
- net-handle / OSWORD `&13` trampolines

Per-entry inline comments give the index and the call/reply each
slot dispatches.""")
for addr in range(0x89ED, 0x8A20):
    byte(addr)

data_banner(0x8A20, "svc_dispatch_hi",
    title="svc_dispatch high-byte table (51 entries + 1 padding)",
    description="""\
High-byte half of the `PHA`/`PHA`/`RTS` dispatch table read by
[`svc_dispatch`](address:8E61) as `LDA &8A20,X`. The
dispatcher pushes the hi byte first then the lo, so `RTS` lands
on `target` (the table stores `target-1`). The trailing byte at
`&8A53` is 1-byte padding – there are only 51 valid entries
(0..50).""")
for addr in range(0x8A20, 0x8A54):
    byte(addr)

# Per-entry symbolic addresses (target-1, RTS-relative).
_svc_dispatch_entries = [
    # (idx,    target,   name,                            description)
    (0x00,  0xE905,  None,                            "placeholder (never reached)"),
    (0x01,  0x8E70,  "dispatch_rts",                  "no-op (RTS only)"),
    (0x02,  0x8D09,  "svc_dispatch_idx_2",            "workspace claim helper (CMOS bit 0)"),
    (0x03,  0x8F10,  "svc_2_priv_ws", "svc &02: private workspace pages"),
    (0x04,  0x8CC7,  "svc_3_autoboot",                "svc &03: auto-boot"),
    (0x05,  0x8C42,  "svc_4_star_command",            "svc &04: unrecognised *command"),
    (0x06,  0x8028,  "svc5_irq_check",                "svc &05: IRQ check"),
    (0x07,  0x8E70,  "dispatch_rts",                  "no-op (RTS only)"),
    (0x08,  0x8ED8,  "svc_7_osbyte",                  "svc &07: unrecognised OSBYTE"),
    (0x09,  0xA83C,  "svc_8_osword_disp",             "svc &08: OSWORD dispatch"),
    (0x0A,  0x8C51,  "svc_9_help",                    "svc &09: *HELP"),
    (0x0B,  0x8E70,  "dispatch_rts",                  "no-op (RTS only)"),
    (0x0C,  0x806C,  "econet_restore",                "svc &0B: NMI release"),
    (0x0D,  0x89A6,  "wait_idle_and_reset",           "svc &0D: wait idle and reset"),
    (0x0E,  0x8B45,  "svc_18_fs_select",              "svc &12: FS select"),
    (0x0F,  0x969A,  "match_on_suffix",               "svc &18: interactive HELP 'ON ' matcher"),
    (0x10,  0x8EE9,  "raise_y_to_c8",                 "svc &21: static workspace claim"),
    (0x11,  0x8EFE,  "set_rom_ws_page",               "svc &22: dynamic workspace offer"),
    (0x12,  0x8EF0,  "store_ws_page_count",           "svc &23: top-of-static-workspace"),
    (0x13,  0x8E71,  "noop_dey_rts",                  "svc &24: dynamic workspace claim"),
    (0x14,  0x8E73,  "copy_template_to_zp",           "svc &25: FS name + info reply"),
    (0x15,  0x8E8A,  "svc_26_close_all_files",        "svc &26: close all files"),
    (0x16,  0x8F38,  "nfs_init_body",                 "svc &27: post-hard-reset re-init"),
    (0x17,  0x959A,  "print_fs_ps_help",       "svc &28: print *FS/*PS no-arg syntax help"),
    (0x18,  0x9630,  "svc_29_status",         "svc &29: *STATUS handler"),
    (0x19,  0x98AF,  "lang_0_insert_key",      "language reply 0: insert remote key"),
    (0x1A,  0x9850,  "lang_1_remote_boot",            "language reply 1: remote boot"),
    (0x1B,  0xB01A,  "lang_2_save_palette_vdu",       "language reply 2: save palette/VDU"),
    (0x1C,  0x987E,  "lang_3_exec_0100",        "language reply 3: execute at &0100"),
    (0x1D,  0x989F,  "lang_4_validated",       "language reply 4: remote validated"),
    (0x1E,  0xA0A9,  "fscv_0_opt_entry",              "FSCV 0: *OPT"),
    (0x1F,  0xA10B,  "fscv_1_eof",                    "FSCV 1: EOF"),
    (0x20,  0xA4F1,  "cmd_run_via_urd",               "FSCV 2: *RUN"),
    (0x21,  0xA42F,  "fscv_3_star_cmd",               "FSCV 3: *command"),
    (0x22,  0xA4F1,  "cmd_run_via_urd",               "FSCV 4: *RUN (alias)"),
    (0x23,  0xB118,  "fscv_5_cat",                    "FSCV 5: *CAT"),
    (0x24,  0x9071,  "fscv_6_shutdown",               "FSCV 6: shutdown"),
    (0x25,  0x93F2,  "fscv_7_read_handles",           "FSCV 7: read handles"),
    (0x26,  0x8E70,  "dispatch_rts",                  "no-op (RTS only)"),
    (0x27,  0xB0FE,  "ps_scan_resume",                "PS scan tail (after pop_requeue)"),
    (0x28,  0xB357,  "cmd_info_dispatch",             "*Info dispatch"),
    (0x29,  0xA4DC,  "check_urd_present",             "URD-present check"),
    (0x2A,  0xB2DB,  "ex_init_scan_x0",               "*Ex scan init"),
    (0x2B,  0xA6D5,  "fsreply_1_boot",   "FS reply 1: copy handles + boot"),
    (0x2C,  0xA6E5,  "fsreply_2_copy_handles",        "FS reply 2: copy handles"),
    (0x2D,  0xA638,  "fsreply_3_set_csd",             "FS reply 3: set CSD"),
    (0x2E,  0xA4F1,  "cmd_run_via_urd",               "FS reply 4: *RUN (alias)"),
    (0x2F,  0xA63E,  "fsreply_5_set_lib",             "FS reply 5: set library"),
    (0x30,  0xA3FF,  "net_1_read_handle",             "net handle 1: read handle"),
    (0x31,  0xA405,  "net_2_read_entry",       "net handle 2: read handle entry"),
    (0x32,  0xA415,  "net_3_close_handle",            "net handle 3: close handle"),
]
for idx, target, name, desc in _svc_dispatch_entries:
    if name is not None:
        expr(0x89ED + idx, "<(%s-1)" % name)
        expr(0x8A20 + idx, ">(%s-1)" % name)
    comment(0x89ED + idx, "&%02X: %s" % (idx, desc), inline=True)
    comment(0x8A20 + idx, "&%02X: %s" % (idx, desc), inline=True)
comment(0x8A53, "padding (table has only 51 entries)", inline=True)

subroutine(0x8EE9, "raise_y_to_c8",
    title="Master 128 service &21 handler: claim static hidden-RAM workspace",
    description="""\
Four-instruction stub: `CPY #&C8 / BCS return / LDY #&C8 / RTS`.
Reached when MOS issues service call `&21` ("Offer Static Workspace
in Hidden RAM") to all sideways ROMs at reset. Per the *Advanced
Reference Manual for the BBC Master*, hidden-RAM static workspace
runs from page `&C0` up to page `&DB`; each filing-system ROM that
wants a slice raises Y to its required base page. ANFS demands its
static workspace base at page `&C8`, so it raises Y to `&C8` if a
previous ROM hasn't already.""",
    on_entry={"y": "current bottom of static workspace claim "
              "(some page in &C0..&DB)"},
    on_exit={"y": ">= &C8 (ANFS static workspace base)"})
subroutine(0x8CC7, "svc_3_autoboot",
    title="Service 3: auto-boot on reset",
    description="Scans the keyboard via OSBYTE &7A for the 'N' key\n"
    "(&19 or &55 EOR'd with &55). If pressed, records\n"
    "the key state via OSBYTE &78. Selects the network\n"
    "filing system by calling cmd_net_fs, prints the\n"
    "station ID, then checks if this is the first boot\n"
    "(ws_page = 0). If so, sets the auto-boot flag in\n"
    "&1071 and JMPs to cmd_fs_entry to execute the boot\n"
    "file.",
    on_entry={"a": "3 (service call number)",
              "x": "ROM slot",
              "y": "parameter (Master 128 service-call dispatch)"})
subroutine(0x8C42, "svc_4_star_command",
    title="Service 4: unrecognised star command",
    description="Saves the OS text pointer, then calls match_fs_cmd\n"
    "to search the command table starting at offset 0\n"
    "(all command sub-tables). If no match is found (carry\n"
    "set), returns with the service call unclaimed. On\n"
    "a match, JMPs to cmd_fs_reentry to execute the\n"
    "matched command handler via the PHA/PHA/RTS\n"
    "dispatch mechanism.",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0x8ED8, "svc_7_osbyte",
    title="Service 7: unrecognised OSBYTE",
    description="Maps Econet OSBYTE codes &32-&35 to dispatch\n"
    "indices 0-3 by subtracting &31 (with carry from\n"
    "a preceding SBC). Returns unclaimed if the OSBYTE\n"
    "number is outside this range. For valid codes,\n"
    "claims the service (sets svc_state to 0) and\n"
    "JMPs to svc_dispatch with Y=&21 to reach the\n"
    "Econet OSBYTE handler table.",
    on_entry={"a": "OSBYTE number (from osbyte_a_copy at &EF)"})
# Reached via PHA/PHA/RTS dispatch.
entry(0xA83B)
subroutine(0xA83B, "svc_8_osword",
    title="Service 8: unrecognised OSWORD",
    description="Handles MOS service call 8 (unrecognised OSWORD).\n"
    "Filters OSWORD codes &0E-&14 by subtracting &0E (via\n"
    "CLC/SBC &0D) and rejecting values outside 0-6. For\n"
    "valid codes, calls osword_setup_handler to push the\n"
    "dispatch address, then copies 3 bytes from the RX\n"
    "buffer to osword_flag workspace.",
    on_entry={"a": "OSWORD number (from osbyte_a_copy)",
              "y": "parameter passed by service-call dispatch"})
subroutine(0x8C51, "svc_9_help",
    title="Service 9: *HELP",
    description="Handles MOS service call 9 (*HELP). First checks\n"
    "for the credits Easter egg. For bare *HELP (CR\n"
    "at text pointer), prints the version header and\n"
    "full command list starting at table offset &91.\n"
    "For *HELP with an argument, handles '.' as a\n"
    "shortcut to list all NFS commands, otherwise\n"
    "iterates through help topics using PHA/PHA/RTS\n"
    "dispatch to print matching command groups.\n"
    "Returns with Y = ws_page (unclaimed).",
    on_entry={"a": "9 (service call number)",
              "y": "command-line offset of *HELP argument"},
    on_exit={"y": "ws_page (workspace page) -- the service call is left "
             "UNCLAIMED so MOS continues to the next ROM"})
# Reached via PHA/PHA/RTS dispatch from the service table; needs an
# explicit entry() because there is no JSR/JMP source for py8dis to
# follow.
entry(0x8B45)
subroutine(0x8B52, "select_fs_via_cmd_net_fs",
    title="Force ANFS selection (raise net checksum on failure)",
    description="""\
Tail-fragment of [`ensure_fs_selected`](address:8B4D) used directly
by `svc_3_autoboot` when an autoboot needs to force-select ANFS as
the active filing system. Calls `cmd_net_fs` to perform the actual
selection; on failure (`BEQ` not taken), `JMP`s to
[`error_net_checksum`](address:90B5) to raise the `net checksum`
error. Used when there is no clean `BIT fs_flags` / `BMI` shortcut
for early-return.""",
    on_entry={"x, y": "preserved across cmd_net_fs (as per the "
              "ensure_fs_selected calling contract)"},
    on_exit={"a": "current FS state byte if selection succeeded"})

subroutine(0x924C, "print_hex_byte_no_spool",
    title="Print A as two hex digits, *SPOOL-bypassing",
    description="""\
As [`print_hex_byte`](address:9236) but emits each digit via
[`print_char_no_spool`](address:91FB) (the *SPOOL-bypassing OSASCI
wrapper), so the digits don't appear in any active spool capture.
Saves `A`, extracts the high nibble (`LSR` x4), prints it via
[`print_hex_nybble_no_spool`](address:9255), then restores `A` and
falls through for the low nibble. Sole caller:
[`print_5_hex_bytes`](address:9D4F) at `&9D53`.""",
    on_entry={"a": "byte to print"},
    on_exit={"a": "preserved"})

subroutine(0x9255, "print_hex_nybble_no_spool",
    title="Print low nybble of A as one hex digit, *SPOOL-bypassing",
    description="As print_hex_nybble (&923F) but emits via the "
    "print_char_no_spool tail-call instead of OSASCI directly, so the "
    "digit is not captured by any active *SPOOL file. Standard "
    "AND #&0F / CMP #&0A / +6-or-not / + #&30 mapping for hex "
    "digits 0-9 / A-F. Tail-jumps to print_char_no_spool via BRA.",
    on_entry={"a": "value (low nybble used)"})

subroutine(0x95EE, "set_fs_or_ps_cmos_station",
    title="Write FS/PS station+network to Master 128 CMOS RAM",
    description="""\
Reached via PHA/PHA/RTS dispatch from cmd_table_fs sub-table 4
(`*FS` at [`&A80F`](address:A80F), `*PS` at
[`&A814`](address:A814)) when the caller supplies a `<net>.<stn>`
argument or wants to inspect/update the saved address.

The flag byte's low 6 bits (`AND #&3F`) double as the CMOS byte
index for the relevant station:

| command | flag | idx | CMOS bytes      |
| ------- | ---- | --- | --------------- |
| `*FS`   | `&C1` | 1   | 1 = FS station, 2 = FS network |
| `*PS`   | `&C3` | 3   | 3 = PS station, 4 = PS network |

Pre-reads existing CMOS[idx] and CMOS[idx+1] into `fs_work_5` /
`fs_work_6` so that the no-argument path leaves the saved values
unchanged. Calls
[`parse_fs_ps_args`](address:A3C4) which conditionally overwrites
`fs_work_5` (station), `fs_work_6` (canonical network: 0=local,
non-zero=remote) and `fs_work_7` (raw parsed network).

Writes the station via [`osbyte_a2`](address:9612), then falls
through into `osbyte_a2` itself to write the raw network at
CMOS[idx+1]. Final `BRA` inside `osbyte_a2` returns via
[`svc_return_unclaimed`](address:8C64).""",
    on_entry={"x": "offset in cmd_table_fs of the matched entry's "
              "flag byte"})

subroutine(0x9612, "osbyte_a2",
    title="OSBYTE &A2 (write Master CMOS RAM byte)",
    description="""\
Three instructions: `LDA #&A2 / JSR OSBYTE / BRA &95BE`. Writes
the Master 128 CMOS RAM byte indexed by `X` with the value in `Y`.
The trailing `BRA` lands on
[`bra_target_svc_return`](address:95BE) (a 3-byte `JMP` trampoline
to [`svc_return_unclaimed`](address:8C64), reached this way
because `BRA`'s 8-bit displacement can't span &9617 → &8C64).

`osbyte_a2` ends at &9618 (3 instructions, 8 bytes); the next
labelled routine is [`cmd_space`](address:9619). Counterpart of
[`osbyte_a1`](address:8E9A) (read).

Callers: [`set_fs_or_ps_cmos_station`](address:95EE) (once via
`JSR`, once via fall-through), the `BRA` shortcut at
[`&962E`](address:962E) inside [`cmd_nospace`](address:9623), and
an `OSARGS`-related read-modify-write of CMOS byte &11 ending at
[`osopt_cmos_writeback_jsr`](address:A0FE).""",
    on_entry={"x": "CMOS RAM byte index", "y": "value to write"})

subroutine(0x9619, "cmd_space",
    title="*Space command: enable space-remaining display",
    description="""\
Reached via the [`cmd_table_fs`](address:A4D6) dispatch entry for
`*Space`. Reads CMOS byte &11 with [`osbyte_a1`](address:8E9A),
sets bit 0 of the value, then `BRA`s to the shared write-back tail
at [`osbyte_a2_value_tya`](address:962B).""")

subroutine(0x9623, "cmd_nospace",
    title="*NoSpace command: disable space-remaining display",
    description="""\
Reached via the [`cmd_table_fs`](address:A4D6) dispatch entry for
`*NoSpace`. Reads CMOS byte &11 with [`osbyte_a1`](address:8E9A),
clears bit 0 of the value, falls through to
[`osbyte_a2_value_tya`](address:962B), and `BRA`s back into
[`osbyte_a2`](address:9612) to write CMOS &11 = `Y`.""")

subroutine(0x962B, "osbyte_a2_value_tya",
    title="Shared CMOS write-back tail",
    description="""\
Common tail used by [`cmd_space`](address:9619) (via `BRA` from
&9621 with the new value already in `A`) and
[`cmd_nospace`](address:9623) (fall-through with the new value in
`A`). `TAY` moves the byte to `Y`, then `LDX #&11` reloads the
CMOS index and `BRA osbyte_a2` performs the write.""")

subroutine(0x9630, "svc_29_status",
    title="Service &29: *STATUS handler",
    description="""\
Reached via `svc_dispatch` slot &18. With no argument on the
command line (first byte = `CR`) prints the FS and PS station
addresses from CMOS &01-&04, then a single FS-active flag drawn
from bit 0 of CMOS &11 (the same bit that
[`cmd_space`](address:9619) / [`cmd_nospace`](address:9623) set
and clear). With an argument, branches to
[`help_dispatch_setup`](address:968C) to parse it.""")

subroutine(0x8B45, "svc_18_fs_select",
    title="Service 18: filing-system selection request",
    description="""\
Service-18 entry point.

| Condition | Action |
|---|---|
| `Y ≠ 5`   | return unclaimed (not the Econet FS) |
| Bit 7 of [`fs_flags`](address:0D6C) set | return (FS already selected) |
| else | fall through to [`cmd_net_fs`](address:8B23) for the full network-FS selection sequence |""",
    on_entry={"y": "filing system number requested"})

# Extended dispatch table entries (indices 15-36).
# These may be reached via FS command dispatch or OSWORD dispatch
# with non-zero Y offsets through &8E33.
entry(0x98AF)
entry(0x9850)
entry(0xB01A)
entry(0x987E)
entry(0x989F)
entry(0xA0A9)
entry(0x9E7F)
entry(0xA10B)
entry(0xA4E4)
entry(0xA42F)
entry(0xB118)
entry(0x9071)
entry(0x93F2)
entry(0xA6D5)
entry(0xA6E5)
entry(0xA638)
entry(0xA63E)
entry(0xA3FF)
entry(0xA405)
entry(0xA415)


# ============================================================
# cmd_table_fs (&A76C..&A832) -- ANFS *command dispatch tables
# ============================================================
# Five concatenated sub-tables of *command dispatch entries. Each
# entry is:
#
#   <name chars (no bit 7)> <flag byte (bit 7 set)> <addr-1 lo> <addr-1 hi>
#
# Bit 7 of the flag byte marks end-of-name (also serves as sub-table
# end-marker if the walker hits it before a name char). Bit 6 = "set
# V if no arg". Bits 0-4 = syntax string index into cmd_syntax_table.
#
# The walker (loop_next_entry at &8BD8) reads cmd_table_fs+X; bit 7 set
# stops the walk. match_fs_cmd starts the walk at a caller-supplied
# X offset, so X picks which sub-table is searched:
#
#   X = 0     -> sub-table 1: utility commands (&A76C..&A7A0)
#   X = &35   -> sub-table 2: NFS commands     (&A7A1..&A7FC)
#   X = &91   -> sub-table 3: *HELP topics     (&A7FD..&A80B)
#   (sub-tables 4 / 5 -- syntax-error helpers at &A80C..&A832 --
#    aren't reached by match_fs_cmd; their targets &95EE / &9619 /
#    &9623 / &965F / &9670 are routines that themselves walk the
#    table for context-specific syntax-help printing.)
#
# Each sub-table is terminated by a single &80 byte (an empty-name
# entry whose bit-7 flag the walker reads as end-of-table). The
# trailing &80 padding may align with the next sub-table's start
# byte where the "&80 &80" double appears; the walker only cares
# about the first one.

label(0xA7A1, "cmd_table_nfs")
label(0xA7FD, "cmd_table_help_topics")
label(0xA80C, "cmd_table_syntax_help")

# Targets that need an entry() because they're reached only via
# PHA/PHA/RTS dispatch from this table. Most have existing
# subroutine() declarations; the ones added here are alt-entries
# specific to the dispatch.
entry(0x8B39)   # *Net  (Econet hardware check, falls into cmd_net_fs)
label(0x8B39, "cmd_net_check_hw")
entry(0x8D87)   # *I am (10-byte ws-state save prologue, falls into cmd_iam at &8D91)
label(0x8D87, "cmd_iam_save_ctx")
entry(0xB581)   # *Pollps
entry(0xB6D2)   # *Prot
entry(0xB3AC)   # *PS
entry(0x8AEA)   # *Roff
entry(0xB6D6)   # *Unprot (alias of *Prot, falls into shared body)
entry(0xBD41)   # *Wdump (alias of *Dump)

data_banner(0xA76C, "cmd_table_fs",
    title="ANFS *command dispatch tables (5 concatenated sub-tables)",
    description="""\
See the comment block immediately above the
[`cmd_table_fs`](address:A76C) declaration in the driver for the
sub-table layout, walker contract, and flag-byte encoding. Each
entry's two-byte dispatch word stores `target-1`; PHA/PHA/RTS
arrives at `target`. Per-entry inline comments below name the
command, syntax-template index, and dispatch target.""")

# Each entry: (name_addr, name, flag_addr, flag_byte, lo_addr,
#              target_label, syntax_role).
# 'name' is the visible *command name (without the leading *).
# 'flag_byte' is the flag byte's value at flag_addr; bit 7 is the
# end-of-name marker, bit 6 = "V if no arg", bits 0-4 = syntax index.
# 'target_label' may be None for syntax-help-only entries whose target
# has no semantic label.
_cmd_table_fs_entries = [
    # --- Sub-table 1: utility commands ---
    (0xA76C, "Net",     0xA76F, 0x80, 0xA770, "cmd_net_check_hw", "Econet HW check + select NFS"),
    (0xA772, "Pollps",  0xA778, 0x88, 0xA779, "cmd_pollps",       "syn 8: (<stn. id.>|<ps type>)"),
    (0xA77B, "Prot",    0xA77F, 0x80, 0xA780, "cmd_prot",         "toggle CMOS protection bit"),
    (0xA782, "PS",      0xA784, 0x88, 0xA785, "cmd_ps",           "syn 8: (<stn. id.>|<ps type>)"),
    (0xA787, "Roff",    0xA78B, 0x80, 0xA78C, "cmd_roff",         "printer offline"),
    (0xA78E, "Unprot",  0xA794, 0x80, 0xA795, "cmd_unprot",       "toggle CMOS protection bit"),
    (0xA797, "Wdump",   0xA79C, 0xC4, 0xA79D, "cmd_dump",         "syn 4 -- *DUMP alias"),
    # sub-table 1 sentinel at &A79F, padding at &A7A0
    # --- Sub-table 2: NFS commands ---
    (0xA7A1, "Access",  0xA7A7, 0xC9, 0xA7A8, "cmd_fs_operation", "syn 9: <obj> (L)(W)(R)..."),
    (0xA7AA, "Bye",     0xA7AD, 0x80, 0xA7AE, "cmd_bye",          "log off FS"),
    (0xA7B0, "Cdir",    0xA7B4, 0xC6, 0xA7B5, "cmd_cdir",         "syn 6 -- create directory"),
    (0xA7B7, "Dir",     0xA7BA, 0x81, 0xA7BB, "cmd_dir",          "syn 1: (<dir>)"),
    (0xA7BD, "Flip",    0xA7C1, 0x80, 0xA7C2, "cmd_flip",         "swap fs/private workspace"),
    (0xA7C4, "FS",      0xA7C6, 0x8B, 0xA7C7, "cmd_fs",           "syn &B -- file-server selection"),
    (0xA7C9, "I am",    0xA7CD, 0xC2, 0xA7CE, "cmd_iam_save_ctx", "syn 2: (<stn>) <user>..."),
    (0xA7D0, "Lcat",    0xA7D4, 0x81, 0xA7D5, "cmd_lcat",         "syn 1: (<dir>) -- *CAT of library"),
    (0xA7D7, "Lex",     0xA7DA, 0x81, 0xA7DB, "cmd_lex",          "syn 1: (<dir>) -- *EX of library"),
    (0xA7DD, "Lib",     0xA7E0, 0xC5, 0xA7E1, "cmd_fs_operation", "syn 5: <dir> -- set library"),
    (0xA7E3, "Pass",    0xA7E7, 0xC7, 0xA7E8, "cmd_pass",         "syn 7: <pass> ..."),
    (0xA7EA, "Rename",  0xA7F0, 0xCA, 0xA7F1, "cmd_rename",       "syn &A: <old> <new>"),
    (0xA7F3, "Wipe",    0xA7F7, 0x81, 0xA7F8, "cmd_wipe",         "syn 1: (<dir>) -- delete with confirm"),
    # sub-table 2 sentinel at &A7FA, padding bytes at &A7FB-&A7FC
    # --- Sub-table 3: *HELP topics ---
    (0xA7FD, "Net",     0xA800, 0x80, 0xA801, "help_net",         "*HELP NET"),
    (0xA803, "Utils",   0xA808, 0x80, 0xA809, "help_utils",       "*HELP UTILS"),
    # sub-table 3 sentinel at &A80B
    # --- Sub-tables 4+5: syntax-error helpers, called by &95EE / &9619 / &9623 / &965F / &9670 ---
    (0xA80C, "FS",      0xA80E, 0xC1, 0xA80F, "set_fs_or_ps_cmos_station", "FS not selected"),
    (0xA811, "PS",      0xA813, 0xC3, 0xA814, "set_fs_or_ps_cmos_station", "PS not selected"),
    (0xA816, "NoSpace", 0xA81D, 0x80, 0xA81E, None,               "caller &9623"),
    (0xA820, "Space",   0xA825, 0x80, 0xA826, None,               "caller &9619"),
    # sentinel at &A828
    (0xA829, "FS",      0xA82B, 0x81, 0xA82C, "print_fs_address",          "caller &9670"),
    (0xA82E, "PS",      0xA830, 0x83, 0xA831, "print_ps_address",          "caller &965F"),
    # sub-tables 4/5 final entry
    (0xA833, "Space",   0xA838, 0x80, 0xA839, None,               "caller &9641"),
]

# Lock each entry's name as a string, flag as a byte (with decoded
# inline annotation), and address as a word with symbolic expr.
for (name_addr, name, flag_addr, flag_byte, lo_addr, target_label, role) in _cmd_table_fs_entries:
    name_len = flag_addr - name_addr
    if name_len > 1:
        string(name_addr, name_len)
    else:
        byte(name_addr)
    byte(flag_addr)
    word(lo_addr)
    if target_label is not None:
        # The walker arrives at PHA/PHA/RTS so the stored word is target-1.
        expr(lo_addr, "%s-1" % target_label)
    # Inline comment on the name byte: just the role.
    comment(name_addr, role, inline=True)
    # Inline comment on the flag byte: decode bits 0-4 (syn idx) and 6 (V).
    syn_idx = flag_byte & 0x1F
    flag_parts = ["no syn"] if syn_idx == 0 else ["syn &%X" % syn_idx]
    if flag_byte & 0x40:
        flag_parts.append("V if no arg")
    comment(flag_addr, ", ".join(flag_parts), inline=True)

# Sentinel / padding bytes between sub-tables. Each is &80 (a flag
# byte with no following address; the walker stops on bit 7 set).
byte(0xA79F)   # sub-table 1 end sentinel
byte(0xA7A0)   # alignment padding before cmd_table_nfs
byte(0xA7FA)   # sub-table 2 end sentinel
byte(0xA7FB)   # see below: the &2C 8E word at &A7FB-&A7FC happens to
byte(0xA7FC)   # encode the address &8E2D (= check_urd_prefix) but the
               # walker doesn't read past the &A7FA sentinel, so this
               # is effectively dead padding -- leave as raw bytes.
byte(0xA80B)   # sub-table 3 end sentinel
byte(0xA828)   # sub-tables 4/5 separator

comment(0xA79F, "Sub-table 1 end (walker reads &80 -> stop)", inline=True)
comment(0xA7A0, "Padding (alignment before sub-table 2)", inline=True)
comment(0xA7FA, "Sub-table 2 end (walker reads &80 -> stop)", inline=True)
comment(0xA7FB, "Padding -- &2C 8E happens to spell &8E2D = "
    "check_urd_prefix but is never read", inline=True)
comment(0xA7FC, "Padding (continued)", inline=True)
comment(0xA80B, "Sub-table 3 end (walker reads &80 -> stop)", inline=True)
comment(0xA828, "Sub-tables 4/5 separator", inline=True)

label(0xBD41, "cmd_dump")
label(0x8B23, "cmd_net_fs")
label(0xB581, "cmd_pollps")
label(0xB3AC, "cmd_ps")
label(0x8AEA, "cmd_roff")

subroutine(0xBD41, "cmd_dump",
    title="*Dump command handler",
    description="Opens the file via open_file_for_read, allocates a\n"
    "21-byte buffer on the stack, and parses the address\n"
    "range via init_dump_buffer. Loops reading 16 bytes\n"
    "per line, printing each as a 4-byte hex address,\n"
    "16 hex bytes with spaces, and a 16-character ASCII\n"
    "column (non-printable chars shown as '.'). Prints\n"
    "a column header at every 256-byte boundary.",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0x8B23, "cmd_net_fs",
    title="Select Econet network filing system",
    description="""\
Computes a checksum over the first `&77` bytes of the workspace
page and verifies against the stored value; raises an error on
mismatch. On success:

1. Notifies the OS via FSCV reason 6
   ([`notify_new_fs`](address:8CFD)).
2. Copies the FS context block from the receive block to the
   HAZEL FS state at [`hazel_fs_station`](address:C000)
   (offsets 0..9), via the `hazel_minus_2,Y` indexing-base
   trick.
3. Installs 7 filing-system vectors (FILEV etc.) from
   [`fs_vector_table`](address:8EA7).
4. Initialises the ADLC and extended vectors.
5. Sets up the channel table.
6. Sets bit 7 of [`fs_flags`](address:0D6C) to mark the FS as
   selected.
7. Issues service call 15 (vectors claimed) via
   [`issue_svc_15`](address:8D02).""",
    on_entry={"y": "command line offset in text pointer "
              "(unused for *NET FS but supplied by star-cmd dispatch)"},
    on_exit={"a, x, y": "clobbered"})
subroutine(0xB581, "cmd_pollps",
    title="*Pollps command handler",
    description="Initialises the spool drive, copies the PS name to\n"
    "the TX buffer, and parses an optional station number\n"
    "or PS name argument. Sends a poll request, then\n"
    "prints the server address and name. Iterates through\n"
    "PS slots, displaying each station's status as\n"
    "'ready', 'busy' (with client station), or 'jammed'.\n"
    "Marks processed slots with &3F.",
    on_entry={"y": "command line offset in text pointer"})
# cmd_prot at &B6D2 / cmd_unprot at &B6D6 are dispatched via the
# star-cmd table at &A77F (Prot) and &A794 (Unprot). They share a
# common body starting at &B6D8. Both need entry() because the
# PHA/PHA/RTS dispatch leaves no static caller for py8dis.
entry(0xB6D2)
entry(0xB6D6)
subroutine(0xB6D2, "cmd_prot",
    title="*Prot command handler",
    description="""\
Loads `A=&FF` (full protection mask) and falls through (via an
always-taken `BNE`) to the shared protection-update body at
`&B6D8`, which:

1. Saves the new flag (`Z=0` for *Prot, `Z=1` for *Unprot) on the
   stack via `PHP`.
2. Calls [`set_via_shadow_pair`](address:AABB) to mirror `A` into
   the workspace shadow ACR (`ws_0d68`) and shadow IER
   (`ws_0d69`).
3. Reads CMOS RAM byte `&11` (Econet station/protection flags)
   via [`osbyte_a1`](address:8E9A) into `Y`, copies to `A`.
4. Restores the saved flag and selects:
   - *Prot path: `ORA #&40` (set bit 6 = protection on).
   - *Unprot path: `AND #&BF` (clear bit 6).
5. Writes the updated byte back to CMOS via OSBYTE `&A2`
   (write CMOS RAM).

The ANFS protection state lives in CMOS bit 6 of byte `&11`, so it
survives BREAK and power-cycle until explicitly toggled.""",
    on_entry={"y": "command line offset (unused; *Prot takes no args)"})
subroutine(0xB6D6, "cmd_unprot",
    title="*Unprot command handler",
    description="""\
Loads `A=&00` (no protection) and falls through to the shared
protection-update body at `&B6D8`, which clears bit 6 of CMOS RAM
byte `&11` (the Econet protection flag). See
[`cmd_prot`](address:B6D2) for the full body description.""",
    on_entry={"y": "command line offset (unused; *Unprot takes no args)"})
subroutine(0xB3AC, "cmd_ps",
    title="*PS command handler",
    description="Checks the printer server availability flag; raises\n"
    "'Printer busy' if unavailable. Initialises the spool\n"
    "drive and buffer pointer, then dispatches on argument\n"
    "type: no argument branches to no_ps_name_given, a\n"
    "leading digit branches to save_ps_cmd_ptr as a station\n"
    "number, otherwise parses a named PS address via\n"
    "load_ps_server_addr and parse_fs_ps_args.",
    on_entry={"y": "command line offset in text pointer"})
# cmd_close, cmd_type, cmd_print are not present in this build --
# the Master 128 standard MOS provides those star commands directly,
# so the NFS ROM no longer wraps them.
subroutine(0x8AEA, "cmd_roff",
    title="*ROFF command handler",
    description="""\
Disables remote operation by clearing the flag at offset 0 in the
receive block. If remote operation was active, re-enables the
keyboard via OSBYTE `&C9` (with `X=0`, `Y=0`) and calls
`tx_econet_abort` with `A=&0A` to reinitialise the workspace
area. Falls through to [`scan_remote_keys`](address:8B00)
which clears `svc_state` and `nfs_workspace`.""",
    on_entry={"y": "command line offset (unused -- *ROFF takes no args)"},
    on_exit={"a, x, y": "clobbered"})

# Sub-table 2: NFS commands
entry(0x9425)   # *Access, *Delete, *Info, *Lib (shared entry)
entry(0x9776)   # *Bye
entry(0x9512)   # *Dir
entry(0xB103)   # *Ex
entry(0xA69A)   # *Flip
entry(0xA398)   # *FS
entry(0xB0F2)   # *Lcat
entry(0xB0F8)   # *Lex
entry(0x8DD5)   # *Pass
entry(0xB312)   # *Remove
entry(0x94C5)   # *Rename
entry(0xB6F3)   # *Wipe

label(0x9425, "cmd_fs_operation")
label(0x9776, "cmd_bye")
label(0x9512, "cmd_dir")
label(0xB103, "cmd_ex")
label(0xA69A, "cmd_flip")
label(0xA398, "cmd_fs")
label(0xB0F2, "cmd_lcat")
label(0xB0F8, "cmd_lex")
label(0x8DD5, "cmd_pass")
# cmd_remove location pending fingerprint -- &B312 is print_decimal_
# digit's body, not cmd_remove.
label(0x94C5, "cmd_rename")
label(0xB6F3, "cmd_wipe")

subroutine(0x9425, "cmd_fs_operation",
    title="Shared *Access / *Delete / *Info / *Lib command handler",
    description="""\
Copies the command name to the TX buffer, parses a quoted
filename argument via [`parse_quoted_arg`](address:9483), and
checks the access prefix. Validates the filename does not start
with `'&'`, then falls through to
[`read_filename_char`](address:944E) to copy remaining
characters and send the request. Raises
[`Bad file name`](address:9437) if a bare `CR` is found where
a filename was expected.""",
    on_entry={"y": "command line offset in text pointer",
              "x": "byte offset within cmd_table_fs identifying which "
              "of the four shared commands was matched (Access, Delete, "
              "Info, or Lib)"})
subroutine(0x9776, "cmd_bye",
    title="*Bye command handler",
    description="Closes all open file control blocks via\n"
    "process_all_fcbs, shuts down any *SPOOL/*EXEC files\n"
    "with OSBYTE &77, and closes all network channels.\n"
    "Falls through to save_net_tx_cb with function code\n"
    "&17 to send the bye request to the file server.")
# Reached via PHA/PHA/RTS dispatch from the star-command table; needs
# an explicit entry().
# cmd_cdir's *real* dispatch entry is at &B0A1, not &B0A0. The byte at
# &B0A0 is the lo byte of the dispatch table value (&A0) interpreted by
# py8dis -- because of `entry(0xB0A0)` -- as a `JMP (cdir_unused_dispatch_table,X)` opcode;
# the bytes are valid code but unreachable. PHA/PHA/RTS dispatch via
# cmd_table_fs lands at &B0A1 (TYA / PHA / JSR mask_owner_access / ...)
# which is the actual command body.
entry(0xB0A0)
entry(0xB0A1)
subroutine(0xB0A1, "cmd_cdir",
    title="*CDir command handler",
    description="""\
Parses an optional allocation size argument: if absent, defaults to
index 2 (standard 19-entry directory, `&200` bytes); if present,
parses the decimal value and searches a 26-entry threshold table to
find the matching allocation size index. Parses the directory name
via `parse_filename_arg`, copies it to the TX buffer, and sends FS
command code `&1B` to create the directory.

Reached via PHA/PHA/RTS dispatch from `cmd_table_fs` entry
[`*Cdir`](address:A7B0); the byte at the entry-1 address `&B0A0`
happens to decode as `JMP (cdir_unused_dispatch_table,X)` but is never executed.""",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0x9512, "cmd_dir",
    title="*Dir command handler",
    description="""\
Handles three argument syntaxes:

| Argument | Action |
|---|---|
| plain path        | delegates to `pass_send_cmd` |
| `'&'` alone       | root directory |
| `'&N.dir'`        | cross-filesystem directory change |

The cross-FS form sends a file-server selection command (code
`&12`) to locate the target server, raising `'Not found'` on
failure, then sends the directory change (code 6) and calls
`find_fs_and_exit` to update the active FS context.""",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0xB103, "cmd_ex",
    title="*Ex command handler",
    description="Unified handler for *Ex, *LCat, and *LEx. Sets the\n"
    "library flag from carry (CLC for current, SEC for library).\n"
    "Configures column format: 1 entry per line for Ex\n"
    "(command 3), 3 per column for Cat (command &0B). Sends the\n"
    "examine request (code &12), then prints the directory\n"
    "header: title, cycle number, Owner/Public label, option\n"
    "name, Dir. and Lib. paths. Paginates through entries,\n"
    "printing each via ex_print_col_sep until the server\n"
    "returns zero entries.",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0xA69A, "cmd_flip",
    title="*Flip command handler",
    description="""\
Exchanges the CSD and CSL (library) handles. Saves the current
CSD handle from [`hazel_fs_context_copy`](address:C003), loads
the library handle from [`hazel_fs_prefix_stn`](address:C004)
into Y, and calls [`find_station_bit3`](address:A66F) to install
it as the new CSD. Restores the original CSD handle and falls
through to [`flip_set_station_boot`](address:A6A6) to install
it as the new library. Useful when files to be LOADed are in
the library and *DIR/*LIB would be inconvenient.""",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0xA398, "cmd_fs",
    title="*FS command handler",
    description="Saves the current file server station address, then\n"
    "checks for a command-line argument. With no argument,\n"
    "falls through to print_current_fs to display the active\n"
    "server. With an argument, parses the station number via\n"
    "parse_fs_ps_args and issues OSWORD &13 (sub-function 1)\n"
    "to select the new file server.",
    on_entry={"y": "command line offset in text pointer"})
# Reached via PHA/PHA/RTS dispatch; needs an explicit entry().
entry(0x8D91)
subroutine(0x8D91, "cmd_iam",
    title="*I AM command handler (file server logon)",
    description="Closes any *SPOOL/*EXEC files via OSBYTE &77,\n"
    "resets all file control blocks via\n"
    "process_all_fcbs, then parses the command line\n"
    "for an optional station number and file server\n"
    "address. If a station number is present, stores\n"
    "it and calls clear_if_station_match to validate.\n"
    "Copies the logon command template from\n"
    "cmd_table_nfs_iam into the transmit buffer and\n"
    "sends via copy_arg_validated. Falls through to\n"
    "cmd_pass for password entry.",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0xB0F2, "cmd_lcat",
    title="*LCat command handler",
    description="""\
Rotates the caller's carry into bit 7 of
[`hazel_fs_lib_flags`](address:C271) (the dispatch path enters
with C=1 so this sets the 'library' flag), then `SEC` / `BCS`
unconditionally jumps to `cat_set_lib_flag` inside
[`cmd_ex`](address:B103) to catalogue the library directory
with three entries per column.""",
    on_entry={"y": "command line offset in text pointer",
              "c": "1 (set by the cmd_table_fs dispatch path)"})
subroutine(0xB0F8, "cmd_lex",
    title="*LEx command handler",
    description="""\
Rotates the caller's carry into bit 7 of
[`hazel_fs_lib_flags`](address:C271) (the dispatch path enters
with C=1 so this sets the 'library' flag), then jumps to
`ex_set_lib_flag` inside [`cmd_ex`](address:B103) to examine
the library directory with one entry per line.""",
    on_entry={"y": "command line offset in text pointer",
              "c": "1 (set by the cmd_table_fs dispatch path)"})
subroutine(0x8D02, "issue_svc_15",
    title="Issue OSBYTE 143 service 15 (vectors-claimed) request",
    description="Tail-call wrapper that loads X=&0F (service number 15) "
    "and tail-jumps to OSBYTE 143 (issue paged ROM service request), "
    "which broadcasts service 15 to all sideways ROMs. ANFS calls "
    "this from svc_2_private_workspace after claiming its workspace, "
    "to give other ROMs a chance to react.",
    on_entry={"a": "OSBYTE result is irrelevant -- this is fire-and-forget"})

subroutine(0x8E9A, "osbyte_a1",
    title="OSBYTE &A1 (read Master CMOS RAM byte)",
    description="""\
Loads `A=&A1` and tail-jumps to `OSBYTE` – reads the Master 128
CMOS RAM byte indexed by `X`. Two callers:
[`format_filename_field`](address:A0E3) and
[`flip_set_station_boot`](address:A70D).

**Dual-use trick:** the 5 bytes `A9 A1 4C F4 FF` also serve as
the leading slot of the vector-dispatch table that
[`write_vector_entry`](address:904F) reads via
`LDA osbyte_a1,Y` – a deliberate overlap so the routine's body
doubles as table data.""",
    on_entry={"x": "CMOS RAM byte index"},
    on_exit={"y": "CMOS byte read", "x": "preserved"})

subroutine(0x988F, "check_escape_and_classify",
    title="Acknowledge escape (if pressed) and classify reply",
    description="If escape_flag bit 7 is clear OR need_release_tube bit "
    "7 is clear (so AND result has bit 7 clear), returns immediately "
    "via return_1. Otherwise acknowledges escape via OSBYTE &7E "
    "(clears the escape condition and runs escape effects), loads "
    "A=6 (a synthesized 'Escape' error class), and tail-jumps to "
    "classify_reply_error to build the 'Escape' BRK error block.\n"
    "\n"
    "Two callers: cmd_pass (&8DEF) for password-entry escape, and "
    "send_net_packet (&9B48) for in-flight TX escape.",
    on_entry={},
    on_exit={"a": "preserved (return) or never returns (escape path)"})

subroutine(0x8DD5, "cmd_pass",
    title="*PASS command handler (change password)",
    description="Builds the FS command packet via copy_arg_to_buf_x0,\n"
    "then scans the reply buffer for a ':' separator\n"
    "indicating a password prompt. If found, reads\n"
    "characters from the keyboard without echo, handling\n"
    "Delete (&7F) for backspace and NAK (&15) to restart\n"
    "from the colon position. Sends the completed\n"
    "password to the file server via save_net_tx_cb and\n"
    "branches to send_cmd_and_dispatch for the reply.",
    on_entry={"y": "command line offset in text pointer "
              "(also the entry point for cmd_iam fall-through)"})
# &B312 is print_decimal_digit's body, not cmd_remove. The actual
# *Remove handler lives at a yet-to-be-located address.

# Two copies of the print-decimal pair: an OSASCI version at &B32A /
# &B338 with leading-zero suppression, and a no-spool variant at
# &B303 / &B310 that uses print_char_no_spool so status output
# bypasses any open *SPOOL file. The no-spool variant has no
# leading-zero suppression.
subroutine(0xB303, "print_decimal_3dig_no_spool",
    title="Print 3-digit decimal via *SPOOL-bypassing print",
    description="As print_decimal_3dig (&B32A) but each digit is "
    "emitted via print_char_no_spool, which closes the *SPOOL "
    "handle around OSASCI so the digit doesn't appear in any "
    "active capture. Always prints all three digits (no "
    "leading-zero suppression).",
    on_entry={"a": "value 0-255"})
subroutine(0xB310, "print_decimal_digit_no_spool",
    title="Print one decimal digit, *SPOOL-bypassing",
    description="As print_decimal_digit (&B338) but emits via "
    "print_char_no_spool. fs_error_ptr is used as scratch "
    "storage for the divisor and is preserved across the print.",
    on_entry={"a": "divisor (100, 10, or 1)",
              "y": "value to divide"},
    on_exit={"y": "remainder after division"})
subroutine(0x94C5, "cmd_rename",
    title="*Rename command handler",
    description="""\
Parses two space-separated filenames from the command line, each
with its own access prefix. Sets the owner-only access mask
before parsing each name. Validates that both names resolve to
the same file server by comparing the FS-options word – raises
`'Bad rename'` if they differ. Falls through to
[`read_filename_char`](address:944E) to copy the second
filename into the TX buffer and send the request.""",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0xB6F3, "cmd_wipe",
    title="*Wipe command handler",
    description="""\
Setup half of *Wipe. Masks owner access via
[`mask_owner_access`](address:B2CF), zeroes the file-iteration
counter [`fs_work_5`](address:00B5), preserves the command-line
pointer with [`save_ptr_to_os_text`](address:B373), parses the
wildcard filename via [`parse_filename_arg`](address:B22C), and
records the end-of-argument offset (X+1) in
[`fs_work_6`](address:00B6). Falls through to
[`request_next_wipe`](address:B703), which drives the per-file
examine/prompt/delete loop until the wildcard is exhausted.""",
    on_entry={"y": "command line offset in text pointer"})
subroutine(0xB7CB, "prompt_yn",
    title="Print Y/N prompt and read user response",
    description="Prints \'Y/N) \' via inline string, flushes\n"
    "the input buffer, and reads a single character\n"
    "from the keyboard.",
    on_entry={},
    on_exit={"A": "character read from keyboard (after the 'Y/N) ' prompt)"})

# Sub-table 3: help topic handlers
entry(0x8BC4)   # *Net (second variant)
entry(0x8BC0)   # *Utils

label(0x8BC4, "help_net")
label(0x8BC0, "help_utils")

subroutine(0x8BC4, "help_net",
    title="*HELP NET topic handler",
    description="""\
Sets `X = &35` (the NFS command sub-table offset) and falls
through to [`print_cmd_table`](address:8BC6) to display the
NFS command list with version header.""",
    on_entry={"y": "command-line offset (PHA/PHA/RTS dispatch contract)"},
    on_exit={"a, x, y": "clobbered (print_cmd_table)"})
subroutine(0x8BC0, "help_utils",
    title="*HELP UTILS topic handler",
    description="""\
Sets `X = 0` to select the utility command sub-table and branches
to [`print_cmd_table`](address:8BC6) to display the command
list. Prints the version header followed by all utility
commands.""",
    on_entry={"y": "command-line offset (PHA/PHA/RTS dispatch contract)"},
    on_exit={"a, x, y": "clobbered"})


# ============================================================
# Additional code entry points (undecoded blocks)
# ============================================================
# These blocks follow decoded code (usually after an RTS or inline
# data) and start with valid 6502 opcodes. Adding entry points
# causes py8dis to trace execution from these addresses.

entry(0x8C29)   # After svc_9_help return
entry(0x93F7)   # After cmd_fs_operation utility code
entry(0x9C22)   # Referenced from FS option handler table
entry(0x9EAB)   # Large undecoded block (266 bytes)
entry(0x9FC2)   # After &9CB8 block
entry(0xA14C)   # Large undecoded block (157 bytes)
entry(0xA28A)   # Large undecoded block (203 bytes)
entry(0xAC47)   # Large undecoded block (220 bytes)
entry(0xAD64)   # After &A9CF code
entry(0xAE6F)   # After &AACF data table
entry(0xBB68)   # File operation handler
# entry(0xB865) removed — was mid-instruction; &B865 is byte 2 of
# LDA #&C1 at &B864, part of the inline error call to error_inline_log.

# TX done dispatch table (5 bytes) and event handler (8 bytes)
entry(0x8549)   # tx_done_econet_event: TX operation type &84 handler
for i in range(5):
    byte(0x853B + i)

# Use symbolic label expressions for PHA/PHA/RTS dispatch lo bytes.
expr(0x853B, "<(tx_done_jsr-1)")
expr(0x853C, "<(tx_done_econet_event-1)")
expr(0x853D, "<(tx_done_os_proc-1)")
expr(0x853E, "<(tx_done_halt-1)")
expr(0x853F, "<(tx_done_continue-1)")
comment(0x853B, "op &83: remote JSR", inline=True)
comment(0x853C, "op &84: fire Econet event", inline=True)
comment(0x853D, "op &85: OSProc call", inline=True)
comment(0x853E, "op &86: HALT", inline=True)
comment(0x853F, "op &87: CONTINUE", inline=True)

# TX ctrl dispatch table (8 bytes at &867E) and machine type handler
# (4 bytes at &8686).
entry(0x8686)   # tx_ctrl_machine_type: ctrl &88 handler
for i in range(8):
    byte(0x867E + i)

# Use symbolic label expressions for PHA/PHA/RTS dispatch lo bytes.
expr(0x867E, "<(tx_ctrl_peek-1)")
expr(0x867F, "<(tx_ctrl_poke-1)")
expr(0x8680, "<(proc_op_status2-1)")
expr(0x8681, "<(proc_op_status2-1)")
expr(0x8682, "<(proc_op_status2-1)")
expr(0x8683, "<(tx_ctrl_exit-1)")
expr(0x8684, "<(tx_ctrl_exit-1)")
expr(0x8685, "<(tx_ctrl_machine_type-1)")
comment(0x867E, "ctrl &81: PEEK", inline=True)
comment(0x867F, "ctrl &82: POKE", inline=True)
comment(0x8680, "ctrl &83: JSR", inline=True)
comment(0x8681, "ctrl &84: UserProc", inline=True)
comment(0x8682, "ctrl &85: OSProc", inline=True)
comment(0x8683, "ctrl &86: HALT", inline=True)
comment(0x8684, "ctrl &87: CONTINUE", inline=True)
comment(0x8685, "ctrl &88: machine type", inline=True)

# Dead data between tx_store_result and tx_calc_transfer (16 bytes).
# Unreferenced and unreachable; collapsed to a single EQUB block
# since the byte values have no documented meaning.
byte(0x88F0, 16, cols=16)

# Dead data between rom_set_nmi_vector RTI and svc_dispatch_lo (3 bytes)

# Smaller undecoded blocks with valid first opcodes
entry(0x84BE)   # After dispatch table data
entry(0x84CE)   # After &84BB block
entry(0x88F0)   # 16 bytes after NMI code
entry(0xA874)   # osword_0e_handler — reached via OSWORD dispatch table
entry(0xA910)   # 118-byte undecoded block
entry(0xA92D)   # osword_11_handler — reached via OSWORD dispatch table
entry(0xA985)   # 552-byte undecoded block (largest remaining)
entry(0xA99A)   # osword_13_dispatch — reached via OSWORD dispatch table
entry(0xB357)   # 28-byte block, JSRs into mask_owner_access / parse_cmd_arg_y0 / copy_arg_to_buf, JMPs to &8E3C
entry(0x9619)   # CMOS-bit setter helpers — reached via *Spool/*Spooloff style dispatch
entry(0x9623)   # second entry of the &9619 helper (clear bit 0 of CMOS &11)
entry(0x9630)   # 31-byte block: command-line walker that JSRs &95C8/&9670/&95C1/&965F
entry(0x959A)   # 21-byte block: LDA(&F2),Y / CMP #&0D loop with JSRs to &95C8/&95DA/&95C1
entry(0x95EE)   # 36-byte CMOS-write helper: LDA &A76C,X / parse_network_station / writes station+network back to CMOS via osbyte_a2 fall-through
# entry(0x96BD) and entry(0x96F5) removed: now reached naturally via the
# &969A dispatch entry, which traces the whole &969A..&973C body as code.
# svc_dispatch table targets: PHA/PHA/RTS dispatch from &89ED/&8A20 reaches each
# of these without leaving a code-flow trace py8dis can follow.
entry(0x8E71)   # idx &13: DEY/RTS 2-byte stub (and continues into copy routine at &8E73)
entry(0x8E73)   # idx &14: copy 11-byte template &8E7F..&8E89 -> (&F2),Y
entry(0x8E8A)   # idx &15: BIT &0D6C / BVC &8E80 / JSR &8B4D / LDA #0 / TAY / JMP &A02F
entry(0xB2DB)   # idx &2A: LDX #0 then falls into loop_scan_entries (&B2DD)
entry(0x969A)   # idx &0F: PHY then 'ON ' suffix matcher; dual-purpose with the
                #   "!Help.ON Z" 10-byte string at &9691 -- the trailing 'Z' (&5A)
                #   serves as both string char and the matcher's first opcode (PHY).
entry(0xACFC)   # 68-byte undecoded block
# entry(0xAA9F) removed — classified as data via byte() declarations
entry(0xBBE7)   # 21-byte file handler block

# Page 5 relocated code — ANFS-specific entry points
# Runtime addresses for undecoded blocks in page 5 source (&BC90)


# ============================================================
# Data tables in main ROM
# ============================================================

# ============================================================
# FS vector dispatch and handler addresses (&8E61)
# ============================================================
subroutine(0x8EA7, "fs_vector_table",
    title="FS vector dispatch and handler addresses (34 bytes)",
    description="""\
Bytes 0-13: extended vector dispatch addresses, copied to
FILEV-FSCV (&0212) by loop_set_vectors. Each 2-byte pair is
a dispatch address (&FF1B-&FF2D) that the MOS uses to look up
the handler in the extended vector table.

Bytes 14-33: handler address pairs read by write_vector_entry.
Each entry has addr_lo, addr_hi, then a padding byte that is
not read at runtime (write_vector_entry writes the current ROM
bank number instead). The last entry (FSCV) has no padding
byte.""")

# Add labels for the handler targets that don't already have a sub
# declaration (so the symbolic equw renders as a name).
label(0xA02F, "findv_handler")
label(0x8E4B, "fscv_handler")

# Part 1: extended vector dispatch addresses (7 x 2 bytes)
# Each value is &FF1B, &FF1E, &FF21, ... &FF2D — the MOS extended
# vector dispatch entries. These get installed at &0212-&021F by
# loop_set_vectors and route filing-system OS calls into the per-ROM
# extended vector table at &0D9F+, where ANFS plants the real handlers.
_ev_dispatch = ["ev_filev", "ev_argsv", "ev_bgetv", "ev_bputv",
                "ev_gbpbv", "ev_findv", "ev_fscv"]
for i, ev in enumerate(_ev_dispatch):
    addr = 0x8EA7 + i * 2
    word(addr)
    expr(addr, ev)
    comment(addr, "%s dispatch" % ev[3:].upper(), inline=True)

# Part 2: handler address entries (7 x {lo, hi, pad}).
# write_vector_entry (&904F) reads bytes from &8E9A+Y starting at
# Y=&1B, so the table starts at &8E9A+&1B = &8EB5.
handler_names = [
    ("FILEV",  "filev_handler"),
    ("ARGSV",  "argsv_handler"),
    ("BGETV",  "bgetv_handler"),
    ("BPUTV",  "bputv_handler"),
    ("GBPBV",  "gbpbv_handler"),
    ("FINDV",  "findv_handler"),
    ("FSCV",   "fscv_handler"),
]
for i, (name, handler_label) in enumerate(handler_names):
    base_addr = 0x8EB5 + i * 3
    word(base_addr)
    expr(base_addr, handler_label)
    comment(base_addr, "%s handler" % name, inline=True)
    if i < 6:  # pad byte for all but last entry
        byte(base_addr + 2, 1)
        comment(base_addr + 2, "(ROM bank — not read)", inline=True)

data_banner(0x8E9F, "ps_template_data",
    title="Printer-server name template (8 bytes)",
    description="""\
Eight bytes (`"PRINT "` then `&01 &00`) read by
[`copy_ps_data`](address:B3D5) via the indexed-base trick
`LDA ps_template_base+X` with `X=&F8..&FF`. The base label
`ps_template_base` resolves to `ps_template_data - &F8` so the
indexed access lands on the bytes here. Default contents installed
into the Printer-Server name slot during ANFS initialisation.""")

# NETV handler address pair at &8E8A (read by write_vector_entry)
label(0xACFC, "netv_handler")

# Error message table entries
label(0x9AB3, "msg_net_error")
label(0x9ABE, "msg_station")
label(0x9AC7, "msg_no_clock")
label(0x9AD1, "msg_escape")
label(0x9AD9, "msg_bad_option")
label(0x9AE5, "msg_no_reply")
label(0x9AFC, "msg_not_listening")
label(0x9B0B, "msg_on_channel")
label(0x9B17, "msg_not_present")

# Inline messages emitted via JSR print_inline / print_inline_no_spool /
# error_inline. Each is a high-bit-terminated ASCII run that lives
# right after the JSR; the print routine pops the JSR's return
# address, walks bytes until bit 7 set, and resumes execution at
# the high-bit byte (which doubles as the next opcode). Labels +
# comments here describe each fragment's role in the user-visible
# message stream.
comment(0x8A6E, "svc 13 fail path", inline=True)
comment(0x9119, "syntax help for *Pass / *I am", inline=True)
comment(0x9193, "syntax help for *PS / *Pollps", inline=True)
comment(0x9AA7, "err_line_jammed = &A0", inline=True)
comment(0x9AB4, "err_net_error = &A1", inline=True)
comment(0xB1D1, "label for *Ex output", inline=True)
comment(0xB49B, "fragment for 'File/Printer server is ...' "
    "messages", inline=True)
comment(0xBE07, "*Dump column header", inline=True)
comment(0xBE24, "*Dump trailer", inline=True)
comment(0xBEDE, "*Dump range error", inline=True)
comment(0x9691, "'!Help.' prefix bytes (not used by the matcher; "
    "may be visible as a fallback help-message head)", inline=True)
comment(0x9697, "'ON ' -- 3-char pattern read by match_on_suffix at "
    "&969A via EOR &9697,X with X=0..2 to detect "
    "'... ON ' help-line suffix", inline=True)

# Per-byte annotation for ps_slot_txcb_template (&B575). The
# data_banner above describes the structure; these 12 inline
# comments name each TXCB field that init_ps_slot_from_rx copies
# from this template into the workspace TXCB.
comment(0xB575, "Offset 0: txcb_ctrl = &80 (standard)", inline=True)
comment(0xB576, "Offset 1: txcb_port = &9F (PS port)", inline=True)
comment(0xB577, "Offset 2: dest station (placeholder, &00)", inline=True)
comment(0xB578, "Offset 3: dest network (placeholder, &00)", inline=True)
comment(0xB579, "Offset 4: buf1 start lo = &10", inline=True)
comment(0xB57A, "Offset 5: buf1 start hi (page from net_rx_ptr)", inline=True)
comment(0xB57B, "Offset 6: buf1 end lo placeholder = &FF", inline=True)
comment(0xB57C, "Offset 7: buf1 end hi placeholder = &FF", inline=True)
comment(0xB57D, "Offset 8: buf2 start lo = &18", inline=True)
comment(0xB57E, "Offset 9: buf2 start hi (page from net_rx_ptr)", inline=True)
comment(0xB57F, "Offset 10: buf2 end lo placeholder = &FF", inline=True)
comment(0xB580, "Offset 11: buf2 end hi placeholder = &FF", inline=True)

# Per-region annotation for the rom_tail_padding (&BFC5) and
# hazel_idx_bases (&BFE6) banners. The banners explain what the
# regions ARE; these inline comments distinguish the inert
# padding from the live indexing-base addresses.
comment(0xBFC5, "ROM-tail padding (2 bytes &FF)", inline=True)
comment(0xBFC7, "ROM-tail padding (1 byte &FF; on its own line "
    "for annotation)", inline=True)
comment(0xBFC8, "ROM-tail padding (30 bytes &FF)", inline=True)
comment(0xBFE6, "Base for `hazel_minus_1a,Y` reads in "
    "loop_copy_txcb_init -- `&BFE6 + Y` reaches into HAZEL "
    "for Y >= &1A", inline=True)
comment(0xBFFE, "Base for `hazel_minus_2,Y` reads/writes -- "
    "`&BFFE + Y` reaches into HAZEL for Y >= 2 "
    "(used by loop_copy_fs_ctx, loop_restore_ctx, loop_copy_ws_to_pb)", inline=True)
comment(0xBFFF, "Base for `hazel_minus_1,Y` reads/writes -- "
    "`&BFFF + Y` reaches into HAZEL for Y >= 1 "
    "(used by loop_copy_station, osword_13_set_station)", inline=True)
# Force null-terminator and error-code bytes inside error_msg_table
# onto their own lines so per-byte annotations attach cleanly.
# Bytes labelled 'N' inside message strings ('No clock',
# 'No reply from station') are deliberately NOT split so py8dis
# folds them into the following EQUS run.
byte(0x9AD0)   # null
byte(0x9AD1)   # error &11
byte(0x9AD9)   # error &CB
byte(0x9B0A)   # null
byte(0x9B16)   # null

# Credits string — force each CR (&0D) onto its own line and
# ensure "nn" (end of "J Dunn") displays as equs not equb.
byte(0x8D45)
comment(0x8D45, "CR", inline=True)
byte(0x8D5E)
comment(0x8D5E, "CR", inline=True)
string(0x8D6E, 2)
byte(0x8D84)
comment(0x8D84, "CR", inline=True)

# Boot command strings
label(0xA740, "boot_load_cmd")


# ============================================================
# Additional ROM subroutines (from code analysis)
# ============================================================

# Subroutine at &8E33: PHA/PHA/RTS dispatch via svc_dispatch tables.
# On entry: X=base index, Y=offset. Dispatches to table[X+Y+1].
subroutine(0x8E61, "svc_dispatch",
    title="PHA/PHA/RTS table dispatch",
    description="""\
Computes a target index by incrementing `X` and decrementing `Y`
until `Y` goes negative, effectively calculating `X+Y+1`. Pushes
the target address (high then low byte) from
[`svc_dispatch_lo`](address:89ED) /
[`svc_dispatch_hi`](address:8A20) onto the stack, loads
`fs_options` into `X`, then `RTS` jumps to the target
subroutine. Used for all service dispatch, FS command execution,
and OSBYTE handler routing.

Routine extent is &8E61-&8E70 (the `RTS` is the dispatch). The
short Master service handlers at
[`noop_dey_rts`](address:8E71) (svc &24),
[`copy_template_to_zp`](address:8E73) (svc &25) and
[`svc_26_close_all_files`](address:8E8A) sit immediately after.""",
    on_entry={"x": "base dispatch index",
              "y": "additional offset"},
    on_exit={"x": "fs_options value"})

subroutine(0x8E71, "noop_dey_rts",
    title="Service &24: dynamic workspace claim (1 page)",
    description="""\
Two-byte handler reached via [`svc_dispatch`](address:8E61) slot
&13. `DEY` decrements the caller's first-available-page count by 1
to claim a single workspace page; `RTS` returns to the dispatcher.""")

subroutine(0x8E73, "copy_template_to_zp",
    title="Service &25: FS name + info reply",
    description="""\
Reached via [`svc_dispatch`](address:8E61) slot &14. Copies the
11-byte template at [`fs_info_template`](address:8E7F) into the
caller's workspace at `(os_text_ptr),Y`. The loop counts `X`
down from 10 to 0 reading from `template[X]`, while `Y`
increments from the caller's value, so the destination ends up
holding the template byte-reversed (`'NET      /' + length-byte`).
Returns via the shared `RTS` at
[`fs_template_done`](address:8E7E).""")

subroutine(0x8E8A, "svc_26_close_all_files",
    title="Service &26: close all files (FILEV via Y=0)",
    description="""\
Reached via [`svc_dispatch`](address:8E61) slot &15. Tests bit 6
of [`fs_flags`](address:0D6C) (NFS-active flag). If clear, branches
back to the shared `RTS` at [`fs_template_done`](address:8E7E)
without acting. Otherwise calls
[`ensure_fs_selected`](address:8B4D) to make NFS the current
filing system, sets `A=Y=0` and tail-calls
[`findv_handler`](address:A02F) — the FILEV `Y=0` path closes all
open NFS channels.""")

subroutine(0x8EC9, "osbyte_x0",
    title="OSBYTE wrapper with X=0, Y=&FF",
    description="Sets X=0 and falls through to osbyte_yff to also\n"
    "set Y=&FF. Provides a single call to execute\n"
    "OSBYTE with A as the function code. Used by\n"
    "adlc_init, init_adlc_and_vectors, and Econet\n"
    "OSBYTE handling.",
    on_entry={"a": "OSBYTE function code"},
    on_exit={"x": "0", "y": "&FF"})
subroutine(0x8ECB, "osbyte_yff",
    title="OSBYTE wrapper with Y=&FF",
    description="Sets Y=&FF and JMPs to the MOS OSBYTE entry\n"
    "point. X must already be set by the caller. The\n"
    "osbyte_x0 entry point falls through to here after\n"
    "setting X=0.",
    on_entry={"a": "OSBYTE function code",
              "x": "OSBYTE X parameter"},
    on_exit={"y": "&FF"})
label(0x8EC9, "osbyte_x0")
label(0x8ECB, "osbyte_yff")


# ============================================================
# Inline string subroutines — descriptions and comments
# ============================================================
# Label and code-tracing hooks created by hook_subroutine() above.

subroutine(0x9261, "print_inline",
    title="Print inline string, high-bit terminated",
    description="""\
Pops the return address from the stack, prints each byte via
`OSASCI` until a byte with bit 7 set is found, then jumps to that
address. The high-bit byte serves as both the string terminator
and the opcode of the first instruction after the string.

Common terminators:

| Byte | Opcode | Effect |
|---|---|---|
| `&EA` | `NOP`  | fall-through |
| `&B8` | `CLV`  | followed by `BVC` for an unconditional forward branch |""",
    on_exit={"a": "terminator byte (bit 7 set, also next opcode)",
             "x": "corrupted (by OSASCI)",
             "y": "0"})

subroutine(0x928A, "print_inline_no_spool",
    title="Print inline string, high-bit terminated, *SPOOL-bypassing",
    description="""\
As [`print_inline`](address:9261), but each character is
emitted via [`print_char_no_spool`](address:91FB) instead of
`OSASCI` directly, so the printed text does not appear in any
active `*SPOOL` capture.

Used by status output that should not be saved to a spool file
(e.g. `*Wipe` `'(Y/N) '` prompts, `*Ex` column separators, the
`'Bad ROM'` service-handler message via the
`recv_and_process_reply` `'Data Lost'` warning, and inline-string
arguments inside [`cmd_ex`](address:B103)'s directory
listing).

Six callers: `&981A` (`recv_and_process_reply`), `&B158`/`&B162`
([`cmd_ex`](address:B103)), `&B2F0` (`ex_print_col_sep`),
`&B75E` ([`cmd_wipe`](address:B6F3)), `&B7CB`
(`prompt_yn`).""",
    on_exit={"a": "terminator byte (bit 7 set, also next opcode)",
             "x": "corrupted (by print_char_no_spool)",
             "y": "0"})

comment(0x9261, "Pop return address (low) — points to last byte of JSR", inline=True)
comment(0x9264, "Pop return address (high)", inline=True)
comment(0x9269, "Advance pointer to next character", inline=True)
comment(0x926F, "Load next byte from inline string", inline=True)
comment(0x9271, "Bit 7 set? Done — this byte is the next opcode", inline=True)
comment(0x9279, "Reload character (pointer may have been clobbered)", inline=True)
comment(0x927B, "Print character via OSASCI", inline=True)
comment(0x9287, "Jump to address of high-bit byte (resumes code)", inline=True)

subroutine(0x99C3, "error_inline",
    title="Generate BRK error from inline string",
    description="""\
Pops the return address from the stack and copies the null-terminated
inline string into the error block at &0100. The error number is
passed in A. Never returns — triggers the error via JMP error_block.""",
    on_entry={"a": "error number (stored in error block at &0101)"})

comment(0x99C3, "Save error number in Y", inline=True)
comment(0x99C4, "Pop return address (low) — points to last byte of JSR", inline=True)
comment(0x99C7, "Pop return address (high)", inline=True)

subroutine(0x99C0, "error_inline_log",
    title="Generate BRK error from inline string (with logging)",
    description="""\
Like error_inline, but first conditionally logs the error code to
workspace via cond_save_error_code before building the error block.""",
    on_entry={"a": "error number"})

comment(0x99C0, "Conditionally log error code to workspace", inline=True)

subroutine(0x99A7, "error_bad_inline",
    title="Generate 'Bad ...' BRK error from inline string",
    description="""\
Like error_inline, but prepends 'Bad ' to the error message. Copies
the prefix from a lookup table, then appends the null-terminated
inline string. The error number is passed in A. Never returns.""",
    on_entry={"a": "error number"})

comment(0x99A7, "Conditionally log error code to workspace", inline=True)
comment(0x99AA, "Save error number in Y", inline=True)
comment(0x99AB, "Pop return address (low) — points to last byte of JSR", inline=True)
comment(0x99AC, "Store return address low", inline=True)
comment(0x99AE, "Pop return address (high)", inline=True)
comment(0x99AF, "Store return address high", inline=True)
comment(0x99B1, "X=0: start of prefix string", inline=True)
comment(0x99B3, "Copy 'Bad ' prefix from lookup table", inline=True)
comment(0x99B4, "Get next prefix character", inline=True)
comment(0x99B7, "Store in error text buffer", inline=True)
comment(0x99BA, "Is it space (end of 'Bad ')?", inline=True)
comment(0x99BC, "No: copy next prefix character", inline=True)
comment(0x99CC, "Store error number in error block", inline=True)
comment(0x99D3, "Zero the BRK byte at &0100", inline=True)
comment(0x99D6, "Copy inline string into error block", inline=True)
comment(0x99D8, "Read next byte from inline string", inline=True)
comment(0x99DD, "Loop until null terminator", inline=True)
comment(0x99DF, "Read receive attribute byte", inline=True)

# "Bad " prefix table


# ============================================================
# FS command inline comments (Phase 4)
# ============================================================

# cmd_cdir (&ACFE) — *CDir: create directory
comment(0xB0A3, "Set owner-only access mask", inline=True)
comment(0xB0A6, "Skip to optional size argument", inline=True)
comment(0xB0A9, "End of line?", inline=True)
comment(0xB0AB, "No: parse size argument", inline=True)
comment(0xB0AD, "Default allocation size index = 2", inline=True)
comment(0xB0B1, "A=&FF: mark as decimal parse", inline=True)
comment(0xB0B3, "Store decimal parse flag", inline=True)
comment(0xB0B5, "Parse numeric size argument", inline=True)
comment(0xB0B8, "X=&1B: top of 26-entry size table", inline=True)
comment(0xB0BA, "Try next lower index", inline=True)
comment(0xB0BB, "Compare size with threshold", inline=True)
comment(0xB0BE, "A < threshold: keep searching", inline=True)
comment(0xB0C0, "Store allocation size index", inline=True)
comment(0xB0C3, "Restore command line offset", inline=True)
comment(0xB0C4, "Transfer to Y", inline=True)
comment(0xB0C5, "Save text pointer for filename parse", inline=True)
comment(0xB0C8, "Parse directory name argument", inline=True)
comment(0xB0CB, "X=1: one argument to copy", inline=True)
comment(0xB0CD, "Copy directory name to TX buffer", inline=True)
comment(0xB0D0, "Y=&1B: *CDir FS command code", inline=True)
comment(0xB0D2, "Send command to file server", inline=True)

data_banner(0xB0D5, "cdir_alloc_size_table",
    title="*CDir allocation size threshold table (26 entries)",
    description="""\
26 thresholds dividing 0-255 into size classes for the *CDir
directory-size argument. Table base is at `cdir_dispatch_col+2`
(overlapping the JMP operand high byte just before the table); the search
loop (`LDX #&1B` / `DEX` / `CMP table,X` / `BCC`) scans indices
26 down to 0. Index 0 reads `&94` from the JMP and is unreachable
because index 1 (threshold `&00`) always matches first. The
resulting `X` (1-26) is the allocation size class sent to the
file server. Default when no size argument is given: index 2.""")
comment(0xB0D5, "Index 1: threshold 0 (catch-all)", inline=True)
comment(0xB0D6, "Index 2: threshold 10 (default)", inline=True)
comment(0xB0D7, "Index 3: threshold 20", inline=True)
comment(0xB0DC, "Index 8: threshold 69", inline=True)
comment(0xB0DE, "Index 10: threshold 88", inline=True)
comment(0xB0DF, "Index 11: threshold 98", inline=True)
comment(0xB0E0, "Index 12: threshold 108", inline=True)
comment(0xB0E3, "Index 15: threshold 138", inline=True)
comment(0xB0E4, "Index 16: threshold 148", inline=True)
comment(0xB0E6, "Index 18: threshold 167", inline=True)
comment(0xB0E7, "Index 19: threshold 177", inline=True)
comment(0xB0E9, "Index 21: threshold 197", inline=True)
comment(0xB0EB, "Index 23: threshold 216", inline=True)
comment(0xB0EC, "Index 24: threshold 226", inline=True)
comment(0xB0ED, "Index 25: threshold 236", inline=True)

# cmd_lcat (&AD4D) — *LCat: library catalogue
comment(0xB0F2, "Rotate carry into lib flag bit 7", inline=True)
comment(0xB0F5, "Set carry (= library directory)", inline=True)

# cmd_lex (&AD53) — *LEx: library examine
comment(0xB0F8, "Rotate carry into lib flag bit 7", inline=True)
comment(0xB0FB, "Set carry (= library directory)", inline=True)

# cmd_prot (&B6D2) and cmd_unprot (&B6D6) — Master 128 protection
# state lives in CMOS RAM byte &11 bit 6 (not in workspace as in
# the BBC B build). The body at &B6D8 mirrors A into the shadow
# ACR/IER pair, then OSBYTE &A2-writes the new flag byte back to
# CMOS so the protection survives BREAK / power-cycle.
comment(0xB6D2, "Load &FF (protect)", inline=True)
comment(0xB6D6, "Load &00 (unprotect)", inline=True)
comment(0xB6D8, "Save Z flag (1 = unprot, 0 = prot) for later",
        inline=True)
comment(0xB6D9, "Mirror A into ws_0d68 / ws_0d69 pair", inline=True)
comment(0xB6DC, "X=&11: CMOS offset for Econet flags", inline=True)
comment(0xB6DE, "OSBYTE &A1 reads CMOS byte &11 -> Y", inline=True)
comment(0xB6E1, "A = current CMOS byte", inline=True)
comment(0xB6E2, "Restore the saved Z flag", inline=True)
comment(0xB6E3, "Z=1: unprot path", inline=True)
comment(0xB6E5, "Set bit 6 (protection on)", inline=True)
comment(0xB6E7, "ALWAYS branch to write-back", inline=True)
comment(0xB6E9, "Clear bit 6 (protection off)", inline=True)
comment(0xB6EB, "Y = new flag byte", inline=True)
comment(0xB6EC, "OSBYTE &A2: write CMOS byte", inline=True)
comment(0xB6EE, "X=&11: CMOS offset for Econet flags", inline=True)
comment(0xB6F0, "Tail-call OSBYTE", inline=True)

# cmd_fs_operation (&92D2) — shared handler for *Access, *Delete, *Info, *Lib
comment(0x9425, "Copy command name 'Access'/'Delete'/'Info'/"
    "'Lib' to TX buffer", inline=True)
comment(0x9429, "Parse quoted filename argument from command line",
    inline=True)
comment(0x942C, "Parse the access prefix (e.g. L,W,R) into a "
    "bitmask", inline=True)
comment(0x9430, "Reject '&' character in filename", inline=True)
comment(0x9433, "End of line?", inline=True)
comment(0x9435, "No: copy filename chars to buffer", inline=True)
comment(0x9437, "Error number &CC", inline=True)
comment(0x9439, "Raise 'Bad file name' error", inline=True)
comment(0x9446, "Load first parsed character", inline=True)
comment(0x9449, "Is it '&'?", inline=True)
comment(0x944B, "Yes: invalid filename", inline=True)
comment(0x944D, "Return", inline=True)
comment(0x944E, "Reject '&' in current char", inline=True)
comment(0x9451, "Store character in TX buffer", inline=True)
comment(0x9454, "Advance buffer pointer", inline=True)
comment(0x9455, "End of line?", inline=True)
comment(0x9457, "Yes: send request to file server", inline=True)
comment(0x9459, "Strip BASIC token prefix byte", inline=True)
comment(0x9464, "Scan backwards in command table", inline=True)
comment(0x9465, "Load table byte", inline=True)
comment(0x9468, "Bit 7 clear: keep scanning", inline=True)
comment(0x946A, "Point past flag byte to name start", inline=True)
comment(0x946B, "Y=0: TX buffer offset", inline=True)
comment(0x946D, "Load command name character", inline=True)
comment(0x9470, "Bit 7 set: end of name", inline=True)
comment(0x9472, "Store character in TX buffer", inline=True)
comment(0x9475, "Advance table pointer", inline=True)
comment(0x9476, "Advance buffer pointer", inline=True)
comment(0x9477, "Continue copying name", inline=True)
comment(0x9479, "Space separator", inline=True)
comment(0x947B, "Append space after command name", inline=True)
comment(0x947E, "Advance buffer pointer", inline=True)
comment(0x947F, "Transfer length to A", inline=True)
comment(0x9480, "And to X (buffer position)", inline=True)
comment(0x9482, "Return", inline=True)
comment(0x9483, "A=0: no quote mode", inline=True)
comment(0x9486, "Clear quote tracking flag", inline=True)
comment(0x9489, "Load char from command line", inline=True)
comment(0x948B, "Space?", inline=True)
comment(0x948D, "No: check for opening quote", inline=True)
comment(0x948F, "Skip leading space", inline=True)
comment(0x9490, "Continue skipping spaces", inline=True)
comment(0x9492, "Double-quote character?", inline=True)
comment(0x9494, "No: start reading filename", inline=True)
comment(0x9496, "Skip opening quote", inline=True)
comment(0x9497, "Toggle quote mode flag", inline=True)
comment(0x949A, "Store updated quote mode", inline=True)
comment(0x949D, "Load char from command line", inline=True)
comment(0x949F, "Double-quote?", inline=True)
comment(0x94A1, "No: store character as-is", inline=True)
comment(0x94A3, "Toggle quote mode", inline=True)
comment(0x94A6, "Store updated quote mode", inline=True)
comment(0x94A9, "Replace closing quote with space", inline=True)
comment(0x94AB, "Store character in parse buffer", inline=True)
comment(0x94AE, "Advance command line pointer", inline=True)
comment(0x94AF, "Advance buffer pointer", inline=True)
comment(0x94B0, "End of line?", inline=True)
comment(0x94B2, "No: continue parsing", inline=True)
comment(0x94B4, "Check quote balance flag", inline=True)
comment(0x94B7, "Balanced: return OK", inline=True)
comment(0x94B9, "Unbalanced: use BRK ptr for error", inline=True)
comment(0x94BB, "Raise 'Bad string' error", inline=True)

# cmd_rename (&9377) — *Rename: rename file on server
comment(0x94D3, "Load next parsed character", inline=True)
comment(0x94D6, "End of line?", inline=True)
comment(0x94D8, "No: store character", inline=True)
comment(0x94DA, "Error number &B0", inline=True)
comment(0x94DC, "Raise 'Bad rename' error", inline=True)
comment(0x94E6, "Store character in TX buffer", inline=True)
comment(0x94E9, "Advance buffer pointer", inline=True)
comment(0x94EA, "Space (name separator)?", inline=True)
comment(0x94EC, "Yes: first name complete", inline=True)
comment(0x94EE, "Strip BASIC token prefix byte", inline=True)
comment(0x94F3, "Strip token from next char", inline=True)
comment(0x94F6, "Load next parsed character", inline=True)
comment(0x94F9, "Still a space?", inline=True)
comment(0x94FB, "Yes: skip multiple spaces", inline=True)
comment(0x94FD, "Save current FS options", inline=True)
comment(0x9500, "Push them", inline=True)
comment(0x9501, "Reset access mask for second name", inline=True)
comment(0x9509, "Restore original FS options", inline=True)
comment(0x950A, "Options changed (cross-FS)?", inline=True)
comment(0x950D, "Yes: error (can't rename across FS)", inline=True)
comment(0x950F, "Copy second filename and send", inline=True)

# cmd_dir (&93C9) — *Dir: set current directory
comment(0x9512, "Get first char of argument", inline=True)
comment(0x9514, "Is it '&' (FS selector prefix)?", inline=True)
comment(0x9516, "No: simple dir change", inline=True)
comment(0x9518, "Skip '&'", inline=True)
comment(0x9519, "Get char after '&'", inline=True)
comment(0x951B, "End of line?", inline=True)
comment(0x951D, "Yes: '&' alone (root directory)", inline=True)
comment(0x951F, "Space?", inline=True)
comment(0x9521, "No: check for '.' separator", inline=True)
comment(0x9523, "Y=&FF: pre-increment for loop", inline=True)
comment(0x9525, "Advance index", inline=True)
comment(0x9526, "Load char from command line", inline=True)
comment(0x9528, "Copy to TX buffer", inline=True)
comment(0x952B, "Is it '&' (end of FS path)?", inline=True)
comment(0x952D, "No: keep copying", inline=True)
comment(0x952F, "Replace '&' with CR terminator", inline=True)
comment(0x9531, "Store CR in buffer", inline=True)
comment(0x9534, "Point past CR", inline=True)
comment(0x9535, "Transfer length to A", inline=True)
comment(0x9536, "And to X (byte count)", inline=True)
comment(0x9537, "Send directory request to server", inline=True)
comment(0x953A, "Is char after '&' a dot?", inline=True)
comment(0x953C, "Yes: &FS.dir format", inline=True)
comment(0x953E, "No: invalid syntax", inline=True)
comment(0x9541, "Skip '.'", inline=True)
comment(0x9542, "Save dir path start position", inline=True)
comment(0x9544, "FS command 4: examine directory", inline=True)
comment(0x9546, "Store in TX buffer", inline=True)
comment(0x9549, "Load FS flags", inline=True)
comment(0x954C, "Set bit 6 (FS selection active)", inline=True)
comment(0x954E, "Store updated flags", inline=True)
comment(0x9551, "X=1: buffer offset", inline=True)
comment(0x9553, "Copy FS number to buffer", inline=True)
comment(0x9556, "Y=&12: select FS command code", inline=True)
comment(0x9558, "Send FS selection command", inline=True)
comment(0x955B, "Load reply status", inline=True)
comment(0x955E, "Status 2 (found)?", inline=True)
comment(0x9560, "Yes: proceed to dir change", inline=True)
comment(0x9562, "Error number &D6", inline=True)
comment(0x9564, "Raise 'Not found' error", inline=True)
comment(0x9571, "Load current FS station byte", inline=True)
comment(0x9574, "Store in TX buffer", inline=True)
comment(0x9577, "X=1: buffer offset", inline=True)
comment(0x9579, "Y=7: change directory command code", inline=True)
comment(0x957B, "Send directory change request", inline=True)
comment(0x957E, "X=1", inline=True)
comment(0x9580, "Store start marker in buffer", inline=True)
comment(0x9583, "Store start marker in buffer+1", inline=True)
comment(0x9587, "Restore dir path start position", inline=True)
comment(0x9589, "Copy directory path to buffer", inline=True)
comment(0x958C, "Y=6: set directory command code", inline=True)
comment(0x958E, "Send set directory command", inline=True)
comment(0x9591, "Load reply handle", inline=True)
comment(0x9594, "Select FS and return", inline=True)
comment(0x9597, "Simple: pass command to FS", inline=True)

# init_txcb_bye / init_txcb_port / init_txcb (&9451-&9476)
comment(0x973D, "A=&90: bye command port", inline=True)
comment(0x973F, "Initialise TXCB from template", inline=True)
comment(0x9742, "Set transmit port", inline=True)
comment(0x9744, "A=3: data start offset", inline=True)
comment(0x9746, "Set TXCB start offset", inline=True)
comment(0x9748, "Open receive: &80->&7F (bit 7 clear = awaiting reply)", inline=True)
comment(0x974A, "Return", inline=True)
comment(0x974B, "Save A", inline=True)
comment(0x974C, "Y=&0B: template size - 1", inline=True)
comment(0x974E, "Load byte from TXCB template", inline=True)
comment(0x9751, "Store to TXCB workspace", inline=True)
comment(0x9754, "Index >= 2?", inline=True)
comment(0x9756, "Yes: skip dest station copy", inline=True)
comment(0x9758, "Load dest station byte", inline=True)
comment(0x975B, "Store to TXCB destination", inline=True)
comment(0x975E, "Decrement index", inline=True)
comment(0x975F, "More bytes: continue", inline=True)
comment(0x9761, "Restore A", inline=True)
comment(0x9762, "Return", inline=True)

# send_request_nowrite / send_request_write (&9483-&9488)
comment(0x976F, "Save A", inline=True)
comment(0x9770, "Set carry (read-only mode)", inline=True)
comment(0x9773, "Clear V", inline=True)

# cmd_flip (&A33E) — *Flip: toggle auto-boot configuration
comment(0xA69A, "Load current CSD handle", inline=True)
comment(0xA69D, "Save CSD handle", inline=True)
comment(0xA69E, "Load library handle into Y", inline=True)
comment(0xA6A1, "Install library as new CSD", inline=True)
comment(0xA6A4, "Restore original CSD handle", inline=True)
comment(0xA6A5, "Y = original CSD (becomes library)", inline=True)
comment(0xA6A6, "X=&10: max 16 station entries", inline=True)
comment(0xA6A8, "Clear V (no match found yet)", inline=True)
comment(0xA6A9, "Decrement station index", inline=True)
comment(0xA6AA, "All searched: exit loop", inline=True)
comment(0xA6AC, "Check if station[X] matches", inline=True)
comment(0xA6AF, "No match: try next station", inline=True)
comment(0xA6B1, "Load station flags byte", inline=True)
comment(0xA6B4, "Test bit 4 (active flag)", inline=True)
comment(0xA6B6, "Not active: try next station", inline=True)
comment(0xA6B8, "Transfer boot type to A", inline=True)
comment(0xA6B9, "Store boot setting for station", inline=True)
comment(0xA6BC, "Set V flag (station match found)", inline=True)
comment(0xA6BF, "Store boot type", inline=True)
comment(0xA6C2, "V set (matched): skip allocation", inline=True)
comment(0xA6C4, "Boot type to A", inline=True)
comment(0xA6C5, "Allocate FCB slot for new entry", inline=True)
comment(0xA6C8, "Store allocation result", inline=True)
comment(0xA6CB, "Zero: allocation failed, exit", inline=True)
comment(0xA6CD, "A=&32: station flags (active+boot)", inline=True)
comment(0xA6CF, "Store station flags", inline=True)
comment(0xA6D2, "Restore FS context and return", inline=True)
comment(0xA6D5, "Close all network channels", inline=True)
comment(0xA6E5, "Save processor status", inline=True)
comment(0xA6E6, "Load station number from reply", inline=True)
comment(0xA6E9, "Find station entry with bit 2", inline=True)
comment(0xA6EC, "Load network number from reply", inline=True)
comment(0xA6EF, "Find station entry with bit 3", inline=True)
comment(0xA6F2, "Load boot type from reply", inline=True)
comment(0xA6F5, "Set boot config for station", inline=True)
comment(0xA6F8, "Restore processor status", inline=True)
comment(0xA6F9, "Carry set: proceed with boot", inline=True)
comment(0xA6FB, "Return with last flag", inline=True)
comment(0xA726, "Load config flags", inline=True)
comment(0xA729, "Save copy in X", inline=True)
comment(0xA72A, "Test bit 2 (auto-boot flag)", inline=True)
comment(0xA72C, "Save bit 2 test result", inline=True)
comment(0xA72D, "Restore full flags", inline=True)
comment(0xA72E, "Clear bit 2 (consume flag)", inline=True)
comment(0xA730, "Store cleared flags", inline=True)
comment(0xA733, "Restore bit 2 test result", inline=True)
comment(0xA734, "Bit 2 was set: skip to boot cmd", inline=True)
comment(0xA736, "OSBYTE &79: scan keyboard", inline=True)
comment(0xA73E, "CTRL not pressed: proceed to boot", inline=True)
comment(0xA740, "CTRL pressed: cancel boot, return", inline=True)
# boot_oscli_lo_table (&A3C7): 4-byte boot command address table.
# Low bytes of OSCLI string addresses (all in page &A3).
# Entry 0 is never used (BEQ at &A3CE exits before lookup).
# Entry 2 cleverly points into "L.!BOOT" at &A3B9 = "!BOOT"
# which MOS treats as *RUN !BOOT.

# cmd_remove (&AF46) — *Remove: delete file from server
comment(0xB312, "Convert remaining value to A", inline=True)

# print_num_no_leading / print_decimal_3dig / print_decimal_digit
# Decimal number printing utility (&AF65-&AF94)
comment(0xB327, "Set V (suppress leading zeros)", inline=True)
comment(0xB32A, "Transfer value to Y (remainder)", inline=True)
comment(0xB32B, "A=100: hundreds divisor", inline=True)
comment(0xB32D, "Print hundreds digit", inline=True)
comment(0xB330, "A=10: tens divisor", inline=True)
comment(0xB332, "Print tens digit", inline=True)
comment(0xB335, "Clear V (always print units)", inline=True)
comment(0xB336, "A=1: units divisor", inline=True)
comment(0xB338, "Store divisor", inline=True)
comment(0xB33A, "Get remaining value", inline=True)
comment(0xB33B, "X='0'-1: digit counter", inline=True)
comment(0xB33D, "Set carry for subtraction", inline=True)
comment(0xB33E, "Save V flag for leading zero check", inline=True)
comment(0xB33F, "Count quotient digit", inline=True)
comment(0xB340, "Subtract divisor", inline=True)
comment(0xB342, "No underflow: continue dividing", inline=True)
comment(0xB344, "Add back divisor (get remainder)", inline=True)
comment(0xB346, "Remainder to Y for next digit", inline=True)
comment(0xB347, "Digit character to A", inline=True)
comment(0xB348, "Restore V flag", inline=True)
comment(0xB349, "V clear: always print digit", inline=True)
comment(0xB34B, "V set: is digit '0'?", inline=True)
comment(0xB34D, "Yes: suppress leading zero", inline=True)
comment(0xB34F, "Save divisor across OSASCI call", inline=True)
comment(0xB354, "Restore divisor", inline=True)
comment(0xB356, "Return", inline=True)

# save_ptr_to_os_text (&AF95-&AF9F)
comment(0xB373, "Save A", inline=True)
comment(0xB374, "Copy text pointer low byte", inline=True)
comment(0xB376, "To OS text pointer low", inline=True)
comment(0xB378, "Copy text pointer high byte", inline=True)
comment(0xB37A, "To OS text pointer high", inline=True)
comment(0xB37C, "Restore A", inline=True)
comment(0xB37D, "Return", inline=True)

# skip_to_next_arg (&AFA0-&AFB4)
comment(0xB37E, "Advance past current character", inline=True)
comment(0xB37F, "Load char from command line", inline=True)
comment(0xB381, "Space?", inline=True)
comment(0xB383, "Yes: skip trailing spaces", inline=True)
comment(0xB385, "CR (end of line)?", inline=True)
comment(0xB387, "Yes: return (at end)", inline=True)
comment(0xB38B, "Advance past space", inline=True)
comment(0xB38C, "Load next character", inline=True)
comment(0xB38E, "Still a space?", inline=True)
comment(0xB390, "Yes: skip multiple spaces", inline=True)
comment(0xB392, "Return (at next argument)", inline=True)

# save_ptr_to_spool_buf (&AFB5-&AFBF)
comment(0xB393, "Save A", inline=True)
comment(0xB394, "Copy text pointer low byte", inline=True)
comment(0xB396, "To spool buffer pointer low", inline=True)
comment(0xB398, "Copy text pointer high byte", inline=True)
comment(0xB39A, "To spool buffer pointer high", inline=True)
comment(0xB39C, "Restore A", inline=True)
comment(0xB39D, "Return", inline=True)

# init_spool_drive (&AFC0-&AFCD)
comment(0xB39E, "Save Y", inline=True)
comment(0xB39F, "Push it", inline=True)
comment(0xB3A0, "Get workspace page number", inline=True)
comment(0xB3A3, "Store as spool drive page high", inline=True)
comment(0xB3A5, "Restore Y", inline=True)
comment(0xB3A6, "Transfer to Y", inline=True)
comment(0xB3A7, "A=0", inline=True)
comment(0xB3A9, "Clear spool drive page low", inline=True)
comment(0xB3AB, "Return", inline=True)

# cmd_close (&B97F) — *Close: close all files

# cmd_type (&B985) — *Type: display file contents

# cmd_print (&B988) — *Print: send file to printer

# open_and_read_file (&B98B) — shared entry for Print/Type

# Process character

# Output character

# CR/LF handling in type mode

# Line ending normalisation (table_idx tracks previous char)

# Previous was CR — check for CR+LF pair

# Previous was LF — check for LF+CR pair

# Consume paired character

# abort_if_escape (&B9EA) — abort file read on Escape
comment(0xBD25, "Test bit 7 of escape flag", inline=True)
comment(0xBD27, "Escape pressed: handle abort", inline=True)
comment(0xBD29, "No escape: return", inline=True)
comment(0xBD2A, "Close the open file", inline=True)
comment(0xBD30, "Acknowledge escape condition", inline=True)
comment(0xBD35, "Error number &11", inline=True)
comment(0xBD37, "Generate 'Escape' BRK error", inline=True)

# cmd_pollps (&B19F) — *PollPS: poll printer server status
# Entry and setup
comment(0xB581, "Save command line pointer high", inline=True)
comment(0xB583, "Initialise spool/print drive", inline=True)
comment(0xB586, "Save spool drive number", inline=True)
comment(0xB588, "Copy PS name to TX buffer", inline=True)
comment(0xB58B, "Init PS slot from RX data", inline=True)
comment(0xB58E, "Restore command line pointer", inline=True)
comment(0xB590, "Save pointer to spool buffer", inline=True)
comment(0xB593, "Get first argument character", inline=True)
comment(0xB595, "End of command line?", inline=True)
comment(0xB597, "Yes: no argument given", inline=True)

# Argument parsing: check if PS name or station number
comment(0xB599, "Clear V (= explicit PS name given)", inline=True)
comment(0xB59A, "Is first char a decimal digit?", inline=True)
comment(0xB59D, "Yes: station number, skip PS name", inline=True)
comment(0xB59F, "PS name follows", inline=True)
comment(0xB5A0, "Save Y", inline=True)
comment(0xB5A1, "Load PS server address", inline=True)
comment(0xB5A4, "Restore Y", inline=True)
comment(0xB5A5, "Back to Y register", inline=True)
comment(0xB5A6, "Parse FS/PS arguments", inline=True)
comment(0xB5A9, "Offset &7A in slot buffer", inline=True)
comment(0xB5AB, "Get parsed station low", inline=True)
comment(0xB5AD, "Store station number low", inline=True)
comment(0xB5B0, "Get parsed network number", inline=True)
comment(0xB5B2, "Store station number high", inline=True)
comment(0xB5B4, "Offset &14 in TX buffer", inline=True)
comment(0xB5B6, "Copy PS data to TX buffer", inline=True)
comment(0xB5B9, "Get buffer page high", inline=True)
comment(0xB5BB, "Set TX pointer high byte", inline=True)
comment(0xB5BD, "Offset &78 in buffer", inline=True)
comment(0xB5BF, "Set TX pointer low byte", inline=True)

# No argument path: set V flag
comment(0xB5C3, "Set V (= no explicit PS name)", inline=True)

# Station number path: fill PS name buffer
comment(0xB5C6, "V set (no arg): skip to send", inline=True)
comment(0xB5C8, "Max 6 characters for PS name", inline=True)
comment(0xB5CA, "Buffer offset for PS name", inline=True)
comment(0xB5CC, "Space character", inline=True)
comment(0xB5CE, "Fill buffer position with space", inline=True)
comment(0xB5D0, "Next position", inline=True)
comment(0xB5D1, "Count down", inline=True)
comment(0xB5D2, "Loop until 6 spaces filled", inline=True)
comment(0xB5D4, "Save pointer to OS text", inline=True)
comment(0xB5D7, "Restore command line pointer", inline=True)
comment(0xB5D9, "Initialise string reading", inline=True)
comment(0xB5DC, "Empty string: skip to send", inline=True)
comment(0xB5DE, "Max 6 characters", inline=True)
comment(0xB5E0, "Save updated string pointer", inline=True)
comment(0xB5E2, "Buffer offset for PS name", inline=True)
comment(0xB5E4, "Save buffer position", inline=True)

# Copy PS name from command line, uppercased
comment(0xB5E6, "Restore string pointer", inline=True)
comment(0xB5E8, "Read next char from string", inline=True)
comment(0xB5EB, "Save updated string pointer", inline=True)
comment(0xB5ED, "End of string: go to send", inline=True)
comment(0xB5EF, "Store char uppercased in buffer", inline=True)
comment(0xB5F2, "Loop if more chars to copy", inline=True)

# Send poll request and display header
comment(0xB5F4, "Enable escape checking", inline=True)
comment(0xB5F6, "Set escapable flag", inline=True)
comment(0xB5F8, "Send the poll request packet", inline=True)
comment(0xB5FB, "Pop and requeue PS scan", inline=True)
comment(0xB5FE, "Print 'Printer server '", inline=True)
comment(0xB601, "Load PS server address", inline=True)
comment(0xB604, "Set V and N flags", inline=True)
comment(0xB607, "Print station address", inline=True)
comment(0xB60A, "Print ' \"'", inline=True)

# Display PS name from RX buffer
comment(0xB611, "Get character from name field", inline=True)
comment(0xB613, "Is it a space?", inline=True)
comment(0xB615, "Yes: end of name", inline=True)
comment(0xB61A, "Next character", inline=True)
comment(0xB61B, "Past end of name field?", inline=True)
comment(0xB61D, "No: continue printing name", inline=True)
comment(0xB61F, "Print '\"' + CR", inline=True)

# Poll each printer slot
comment(0xB626, "Zero: all slots done, return", inline=True)
comment(0xB628, "Save slot offset", inline=True)
comment(0xB629, "Transfer to Y", inline=True)
comment(0xB62A, "Read slot status byte", inline=True)
comment(0xB62C, "Bit 7 clear: slot inactive", inline=True)
comment(0xB62E, "Advance to station number", inline=True)
comment(0xB62F, "Offset+2 in slot", inline=True)
comment(0xB630, "Read station number low", inline=True)
comment(0xB632, "Store station low", inline=True)
comment(0xB634, "Next byte (offset+3)", inline=True)
comment(0xB635, "Read network number", inline=True)
comment(0xB637, "Store network number", inline=True)
comment(0xB639, "Next byte (offset+4)", inline=True)
comment(0xB63A, "Read status page pointer", inline=True)
comment(0xB63C, "Store pointer low", inline=True)
comment(0xB63E, "Clear V flag", inline=True)
comment(0xB63F, "Print station address (V=0)", inline=True)
comment(0xB642, "Print ' is '", inline=True)

# Display printer status
comment(0xB64B, "Read printer status byte", inline=True)
comment(0xB64D, "Non-zero: not ready", inline=True)
comment(0xB64F, "Print 'ready'", inline=True)
comment(0xB65A, "Status = 2?", inline=True)
comment(0xB65C, "No: check for busy", inline=True)
comment(0xB65E, "Print 'jammed'", inline=True)
comment(0xB667, "Clear V", inline=True)
comment(0xB66A, "Status = 1?", inline=True)
comment(0xB66C, "Not 1 or 2: default to jammed", inline=True)
comment(0xB66E, "Print 'busy'", inline=True)

# Display client station for busy printer
comment(0xB677, "Read client station number", inline=True)
comment(0xB679, "Store station low", inline=True)
comment(0xB67B, "Zero: no client info, skip", inline=True)
comment(0xB67D, "Print ' with station '", inline=True)
comment(0xB692, "Store network number", inline=True)
comment(0xB694, "Set V flag", inline=True)
comment(0xB697, "Print client station address", inline=True)

# Advance to next slot
comment(0xB69D, "Retrieve slot offset", inline=True)
comment(0xB69E, "Transfer to Y", inline=True)
comment(0xB69F, "Mark slot as processed (&3F)", inline=True)
comment(0xB6A1, "Write marker to workspace", inline=True)
comment(0xB6A5, "Return", inline=True)

# init_ps_slot_from_rx (&B2C4) — initialise PS slot from RX data
comment(0xB6A6, "Start at offset &78", inline=True)
comment(0xB6A8, "Load template byte", inline=True)
comment(0xB6AB, "At offset &7D?", inline=True)
comment(0xB6AD, "Yes: substitute RX page", inline=True)
comment(0xB6AF, "At offset &81?", inline=True)
comment(0xB6B1, "No: use template byte", inline=True)
comment(0xB6B3, "Use RX buffer page instead", inline=True)
comment(0xB6B5, "Store byte in slot buffer", inline=True)
comment(0xB6B7, "Next offset", inline=True)
comment(0xB6B8, "Past end of slot (&84)?", inline=True)
comment(0xB6BA, "No: continue copying", inline=True)
comment(0xB6BC, "Return", inline=True)

# store_char_uppercase (&B2DB) — store char to buffer, uppercased
comment(0xB6BD, "Y = current buffer position", inline=True)
comment(0xB6BF, "Strip high bit", inline=True)
comment(0xB6C1, "Is it lowercase 'a' or above?", inline=True)
comment(0xB6C3, "Below 'a': not lowercase", inline=True)
comment(0xB6C5, "Above 'z'?", inline=True)
comment(0xB6C7, "Yes: not lowercase", inline=True)
comment(0xB6C9, "Convert to uppercase", inline=True)
comment(0xB6CB, "Store in RX buffer", inline=True)
comment(0xB6CD, "Next buffer position", inline=True)
comment(0xB6CE, "Update buffer position", inline=True)
comment(0xB6D0, "Decrement character count", inline=True)
comment(0xB6D1, "Return (Z set if count=0)", inline=True)

# cmd_ex (&AD59) — *Ex: examine directory listing
# Entry: set up for Ex mode (1 entry per line, FS code 3)
comment(0xB103, "Rotate carry into lib flag bit 7", inline=True)
comment(0xB106, "Clear carry (= current directory)", inline=True)
comment(0xB107, "Rotate carry back, clearing bit 7", inline=True)
comment(0xB10A, "A=&FF: initial column counter", inline=True)
comment(0xB10C, "Store column counter", inline=True)
comment(0xB10E, "One entry per line (Ex format)", inline=True)
comment(0xB110, "Store entries per page", inline=True)
comment(0xB112, "FS command code 3: Examine", inline=True)
comment(0xB114, "Store command code", inline=True)

# Cat entry (&AD6E) — *Cat: catalogue directory
comment(0xB118, "Set transfer parameters", inline=True)
comment(0xB11B, "Y=0: start from entry 0", inline=True)
comment(0xB11D, "Rotate carry into lib flag", inline=True)
comment(0xB120, "Clear carry (= current directory)", inline=True)
comment(0xB121, "Rotate carry back, clearing bit 7", inline=True)
comment(0xB124, "Three entries per column (Cat)", inline=True)
comment(0xB126, "Store column counter", inline=True)
comment(0xB128, "Store entries per page", inline=True)
comment(0xB12A, "FS command code &0B: Catalogue", inline=True)
comment(0xB12C, "Store command code", inline=True)

# Shared Ex/Cat setup
comment(0xB12E, "Save text pointer", inline=True)
comment(0xB131, "A=&FF: enable escape checking", inline=True)
comment(0xB133, "Set escapable flag", inline=True)
comment(0xB135, "Command code 6", inline=True)
comment(0xB137, "Store in TX buffer", inline=True)
comment(0xB13A, "Parse directory argument", inline=True)
comment(0xB13D, "X=1: offset in buffer", inline=True)
comment(0xB13F, "Copy argument to TX buffer", inline=True)
comment(0xB142, "Get library/FS flags", inline=True)
comment(0xB145, "Shift bit 0 to carry", inline=True)
comment(0xB146, "Bit 0 clear: skip", inline=True)
comment(0xB148, "Set bit 6 (owner access flag)", inline=True)
comment(0xB14A, "Rotate back", inline=True)
comment(0xB14B, "Store modified flags", inline=True)
comment(0xB14E, "Y=&12: FS command for examine", inline=True)
comment(0xB150, "Send request to file server", inline=True)
comment(0xB153, "X=3: offset to directory title", inline=True)
comment(0xB155, "Print directory title (10 chars)", inline=True)
comment(0xB158, "Print '('", inline=True)
comment(0xB15C, "Load FS object-type code from "
    "hazel_txcb_objtype (file/dir/etc)", inline=True)
comment(0xB162, "Print ')     ' to close the type-code field",
    inline=True)

# Directory header: cycle number and access
comment(0xB170, "Print 'Owner' + CR", inline=True)
comment(0xB17B, "Print 'Public' + CR", inline=True)

# Directory info: option, dir name, lib name
comment(0xB189, "Mask owner access bits", inline=True)
comment(0xB18C, "Y=&15: FS command for dir info", inline=True)
comment(0xB18E, "Send request to file server", inline=True)
comment(0xB191, "Advance X past header", inline=True)
comment(0xB192, "Y=&10: print 16 chars", inline=True)
comment(0xB194, "Print file entry", inline=True)
comment(0xB197, "Print '    Option '", inline=True)
comment(0xB1A8, "Transfer to X for table lookup", inline=True)
comment(0xB1A9, "Print option as hex", inline=True)
comment(0xB1AC, "Print ' ('", inline=True)

# Scan for end-of-entry marker

# print_10_chars (&AE70) — print 10 chars from buffer at X

# parse_cmd_arg_y0 (&AE80)

# parse_filename_arg (&AE82)

# NOTE: A larger block of stale 4.18 cmd_ps / PS-scan / PS-template
# inline commentary covering &B0C5..&B1C2 was deleted here. Those
# 4.18 routines (print_file_server_is, print_printer_server_is,
# load_ps_server_addr, pop_requeue_ps_scan, slot-scan loop,
# write_ps_slot_byte_ff, reverse_ps_name_to_tx, ps_tx_header_template,
# print_station_addr) shifted address in 4.21 and now collide with
# cmd_cdir / cmd_lcat / cmd_lex / cmd_ex / fscv_5_cat. Each of those
# 4.21 routines has its own correct inline block elsewhere.

# cmd_bye (&948A) — *Bye: logoff from file server

# save_net_tx_cb (&9499) — save state and build TX control block
comment(0x94BE, "Store to TXCB", inline=True)

# prep_send_tx_cb (&94C6) — prepare TXCB and send
comment(0x94E4, "Add 5 for header size", inline=True)

# recv_and_process_reply (&94DC) — wait for reply and dispatch

# Disconnect path — send disconnect if carry was set

# Process reply status — handle reply code and data loss

# Build server error — copy error from server reply
comment(0x9567, "Store null terminator (A=0 from EOR)", inline=True)
comment(0x956A, "Get message length", inline=True)
comment(0x956D, "Go to error dispatch", inline=True)

# check_escape (&955A) — test for escape condition

# raise_escape_error (&9560) — acknowledge and raise escape error

# Remote station handler (&956A) — handle Econet remote control
comment(0x9586, "Non-zero: commit state and return", inline=True)

# Remote key injection (&95A8)

# set_fs_or_ps_cmos_station (&95EE) — write FS/PS station+network to CMOS RAM
comment(0x95EE, "Read flag byte for matched cmd entry "
    "(syntax idx in bits 0..4)", inline=True)
comment(0x95F1, "Mask off end-marker (bit 7) and "
    "V-if-no-arg flag (bit 6)", inline=True)
comment(0x95F3, "X = CMOS byte index (1=FS stn, 3=PS stn)",
    inline=True)
comment(0x95F4, "Save CMOS index", inline=True)
comment(0x95F5, "Save caller's command-line cursor", inline=True)
comment(0x95F6, "Save CMOS index again "
    "(consumed by first PLX below)", inline=True)
comment(0x95F7, "Read existing CMOS[idx] (current station)",
    inline=True)
comment(0x95FA, "Default station if user gives no args",
    inline=True)
comment(0x95FC, "Recover CMOS index from stack", inline=True)
comment(0x95FD, "X+=1: advance to network byte", inline=True)
comment(0x95FE, "Read existing CMOS[idx+1] (current network)",
    inline=True)
comment(0x9601, "Default network if user gives no args",
    inline=True)
comment(0x9603, "Restore command-line cursor", inline=True)
comment(0x9604, "Parse '<net>.<stn>'; updates "
    "fs_work_5/6/7 if args present", inline=True)
comment(0x9607, "Recover CMOS index from stack", inline=True)
comment(0x9608, "Re-save CMOS index for second write",
    inline=True)
comment(0x9609, "Y = station (parsed or pre-read default)",
    inline=True)
comment(0x960B, "Write CMOS[idx] = station", inline=True)
comment(0x960E, "Recover CMOS index from stack", inline=True)
comment(0x960F, "X+=1: advance to network byte", inline=True)
comment(0x9610, "Y = raw parsed network (NOT canonical "
    "fs_work_6); fall through into osbyte_a2 to write CMOS[idx+1]",
    inline=True)


# cmd_fs (&A063) — *FS: select file server by number
comment(0xA07E, "Save to fs_work_5", inline=True)
comment(0xA080, "Load current FS station low", inline=True)
comment(0xA083, "Save to fs_work_6", inline=True)
comment(0xA087, "Is it CR (no argument)?", inline=True)
comment(0xA094, "Parameter block low", inline=True)
comment(0xA096, "Parameter block high", inline=True)

# Print current FS info
comment(0xA0A1, "Clear hazel_fcb_addr_mid for slot Y", inline=True)

# parse_fs_ps_args (&A08F) — parse net.station arguments for FS/PS
comment(0xA0A7, "Z still set from LDA #0: always branch to done_close", inline=True)
comment(0xA0A9, "A=0 (init sub-code): jump to store_display_flag", inline=True)
comment(0xA0AB, "Non-zero A: X==4? (read OSARGS args)", inline=True)
comment(0xA0AD, "X != 4: take normal OSARGS dispatch", inline=True)
comment(0xA0B3, "X-- (osargs_dispatch entry): step sub-code down", inline=True)
comment(0xA0B4, "X != 1: take store-ptr-lo path", inline=True)
comment(0xA0B9, "Tail-branch to done_close", inline=True)
comment(0xA0BB, "A=7: error code (out-of-range OSARGS sub-code)", inline=True)
comment(0xA0BD, "Raise BRK error", inline=True)
comment(0xA0C0, "Store Y as TXCB data byte (OSARGS payload)", inline=True)
comment(0xA0C5, "Send OSARGS request via TX control block", inline=True)
comment(0xA0CA, "Update hazel_fs_flags from OSARGS reply", inline=True)

# OSARGS sub-code dispatcher (&A0CF..&A101): osargs_store_ptr_lo
# routes by sub-code. X = OSARGS sub-code (0..7), Y = OSARGS arg.
# Sub-code 4 takes the fast read path (osargs_check_length); sub-codes
# 0..3 with low Y go to osopt_check_cmos_protect; sub-codes 5..7 fall
# through into the same. Out-of-range -> error_osargs.
comment(0xA0CF, "X >= 8?", inline=True)
comment(0xA0D1, "Yes: out-of-range OSARGS sub-code", inline=True)
comment(0xA0D3, "X == 4?", inline=True)
comment(0xA0D5, "Yes: take fast read path (osargs_check_length)",
    inline=True)
comment(0xA0D7, "Y < 4?", inline=True)
comment(0xA0D9, "Yes: take CMOS-protect path", inline=True)
comment(0xA0DB, "Y >= 2?", inline=True)
comment(0xA0DD, "Yes: argument out of range", inline=True)
comment(0xA0E0, "Save sub-code across the CMOS read", inline=True)
comment(0xA0E3, "Read CMOS &11 (Econet status) -> Y", inline=True)
comment(0xA0E6, "Restore sub-code", inline=True)
comment(0xA0E8, "Mask CMOS &11 with cmos_opt_mask_table[X]", inline=True)
comment(0xA0ED, "Load shift count from cmos_attr_table[X]", inline=True)
comment(0xA0F1, "Caller's Y back to A as the value to shift",
    inline=True)
comment(0xA0F3, "Count down shift iterations", inline=True)
comment(0xA0F4, "Loop until X reaches 0", inline=True)
comment(0xA0F6, "Stash shifted value in fs_load_addr scratch", inline=True)
comment(0xA0F9, "OR with the CMOS-masked value", inline=True)
comment(0xA0FC, "X=&11: target CMOS byte for write-back", inline=True)
comment(0xA101, "Tail-branch into the OSARGS done path", inline=True)

# cmd_fs_reentry (&A10D)
# error_syntax (&A10F)
comment(0xA129, "Generate 'Syntax' error", inline=True)

# Dispatch matched command (&A11B)
comment(0xA133, "Clear carry for the upcoming 4-byte add", inline=True)
comment(0xA13A, "Push high byte", inline=True)
comment(0xA13F, "RTS dispatches to command handler", inline=True)

# match_fs_cmd (&A45B) — case-insensitive command-name matcher.
# Walks cmd_table_fs entries (bit-7-terminated names + 3-byte
# trailers), returning Z=1 with X past the match's name on success.
comment(0xA45B, "Save command-line offset Y on stack", inline=True)
comment(0xA45D, "Reload saved Y (peek without popping)", inline=True)
comment(0xA45E, "Push it back to keep on stack", inline=True)
comment(0xA45F, "Y = saved command-line offset", inline=True)
comment(0xA460, "First char of current entry name", inline=True)
comment(0xA463, "Bit 7 set already: end of table",
        inline=True)
comment(0xA465, "Next char from table", inline=True)
comment(0xA468, "Bit 7 set: name fully matched", inline=True)
comment(0xA46C, "Mask off case bit (5)", inline=True)
comment(0xA46E, "Mismatch (after case mask): skip entry",
        inline=True)
comment(0xA470, "Advance command-line offset", inline=True)
comment(0xA471, "Advance table offset", inline=True)
comment(0xA472, "ALWAYS branch: continue matching",
        inline=True)
comment(0xA474, "Skip remaining name chars", inline=True)
comment(0xA475, "Load next table byte", inline=True)
comment(0xA478, "Bit 7 clear: continue skipping", inline=True)
comment(0xA47A, "Char on command line at current Y",
        inline=True)
comment(0xA47C, "Is it `.` (abbreviation)?", inline=True)
comment(0xA47E, "Yes: accept abbreviated match", inline=True)
comment(0xA480, "Skip 3-byte handler trailer (flag, lo, hi)",
        inline=True)
comment(0xA483, "ALWAYS branch: try next entry", inline=True)
comment(0xA485, "Save matched-name length on stack", inline=True)
comment(0xA487, "Char on command line just past name",
        inline=True)
comment(0xA489, "Y=9: separator-table size - 1", inline=True)
comment(0xA48B, "Compare with separator", inline=True)
comment(0xA48E, "Match: valid command boundary", inline=True)
comment(0xA490, "Try next separator", inline=True)
comment(0xA491, "Loop through 10 separators", inline=True)
comment(0xA493, "Restore matched-name length", inline=True)
comment(0xA495, "ALWAYS branch: try next entry", inline=True)
comment(0xA4A0, "Restore matched-name length", inline=True)
comment(0xA4A1, "Y = matched-name length", inline=True)

# loop_skip_trail_spaces / check_cmd_flags / loop_scan_past_word
# (&A4A2..&A4DC) — match_fs_cmd's tail: skip spaces or `.` after a
# matched name, validate the entry's no-arg flag against the line
# end, and either return Z=1 (match, C reflects whether arguments
# follow) or restart the table scan.
comment(0xA4A2, "Char on command line at current Y", inline=True)
comment(0xA4A4, "Is it space?", inline=True)
comment(0xA4A6, "No: check the entry's no-arg flag", inline=True)
comment(0xA4A8, "Advance past the space (or `.`)", inline=True)
comment(0xA4A9, "Loop: keep skipping", inline=True)
comment(0xA4AC, "Load entry's flag byte (post-name)", inline=True)
comment(0xA4AF, "Shift bit 7 into C: the no-arg bit",
        inline=True)
comment(0xA4B0, "C=0: entry allows arguments", inline=True)
comment(0xA4B2, "Char on command line", inline=True)
comment(0xA4B4, "Is it CR (no argument)?", inline=True)
comment(0xA4B6, "Argument present, V clear", inline=True)
comment(0xA4B8, "Force V=1: entry validated as match",
        inline=True)
comment(0xA4BB, "V set: skip the CLV", inline=True)
comment(0xA4BD, "Clear V (no-arg flag not asserted)",
        inline=True)
comment(0xA4BE, "Clear C (no error / no-arg path)",
        inline=True)
comment(0xA4BF, "Discard saved Y on stack", inline=True)
comment(0xA4C0, "A = current command-line char", inline=True)
comment(0xA4C2, "Return (Z=1 on match, C and V set per "
        "result)", inline=True)

# loop_scan_past_word / check_char_type at &A4C3 / &A4C4: reached
# from the `BMI check_char_type` at &A463 when the table entry's
# first byte is already the bit-7 terminator (the unnamed
# end-of-table sentinel). Scans forward in the command line to the
# next word boundary.
comment(0xA4C3, "Advance command-line offset", inline=True)
comment(0xA4C4, "Char on command line", inline=True)
comment(0xA4C6, "Is it CR (end of input)?", inline=True)
comment(0xA4C8, "Yes: set C and return (no match)", inline=True)
comment(0xA4CA, "Is it `.`?", inline=True)
comment(0xA4CC, "Yes: skip separator spaces", inline=True)
comment(0xA4CE, "Is it space?", inline=True)
comment(0xA4D0, "No: keep scanning past word", inline=True)
comment(0xA4D2, "Advance past space", inline=True)
comment(0xA4D3, "Load next char", inline=True)
comment(0xA4D5, "Still space?", inline=True)
comment(0xA4D7, "Yes: keep skipping", inline=True)
comment(0xA4D9, "Set C: signal no-match return path",
        inline=True)
comment(0xA4DA, "ALWAYS branch to common return", inline=True)

# svc_dispatch_idx_2 (&8D09)
comment(0x8D09, "Save Y on stack", inline=True)
comment(0x8D0A, "X=&11: CMOS offset for Econet station-flags",
        inline=True)
comment(0x8D0C, "Read CMOS byte: result in Y", inline=True)
comment(0x8D0F, "A = CMOS byte", inline=True)
comment(0x8D10, "Restore caller's Y", inline=True)
comment(0x8D11, "Isolate bit 0 (page-&0B fallback flag)",
        inline=True)
comment(0x8D13, "Bit clear: keep caller's Y", inline=True)
comment(0x8D15, "Caller's Y already >= &10?", inline=True)
comment(0x8D17, "Yes: keep it", inline=True)
comment(0x8D19, "Y < &10 with bit set: clamp to &10",
        inline=True)
comment(0x8D1B, "Return", inline=True)

# err_bad_hex (&934A)
comment(0x934A, "Error code &F1", inline=True)
comment(0x934C, "Raise 'Bad hex' error", inline=True)

# cmd_fs_reentry (&A440)
comment(0xA440, "V clear: re-enter dispatch_fs_cmd", inline=True)

# error_syntax (&A442) — falls through from cmd_fs_reentry on V set
comment(0xA442, "Error code &DC", inline=True)
comment(0xA444, "Raise 'Syntax' error", inline=True)

# find_station_bit2 (&A2E8) — find station with bit 2 set
comment(0xA300, "X=&10: scan 16 slots (15 to 0)", inline=True)
comment(0xA302, "Clear V", inline=True)
comment(0xA309, "No match: try next", inline=True)
comment(0xA30B, "Load slot status byte", inline=True)
comment(0xA30E, "Test bit 2 (PS active flag)?", inline=True)
comment(0xA312, "Transfer Y to A", inline=True)
comment(0xA319, "Store Y to fs_urd_handle", inline=True)
comment(0xA31E, "Transfer Y to A", inline=True)
comment(0xA322, "Store allocation result", inline=True)

# find_station_bit3 (&A313) — find station with bit 3 set
comment(0xA32E, "Try next slot", inline=True)
comment(0xA341, "Set V (found match)", inline=True)
comment(0xA344, "Store Y to fs_csd_handle", inline=True)
comment(0xA347, "V set: found, skip allocation", inline=True)
comment(0xA34A, "Allocate FCB slot", inline=True)

# print_inline gaps (&9132-&9154) — fill remaining items
comment(0x9146, "Store as string pointer low", inline=True)
comment(0x9149, "Store as string pointer high", inline=True)

# &916E-&91F8 is entirely syntax-string data and the cmd_syntax_table
# -- no parse_addr_arg routine here.

# ============================================================
# print_*_no_spool inline comments (&91F9-&9235)
# ============================================================
comment(0x91F9, "A=&0D (CR) for OSASCI translation; fall through", inline=True)
comment(0x91FB, "Save caller's flags (V from caller is irrelevant — see &91FC)", inline=True)
comment(0x91FC, "Unconditionally sets V=1 (bit 6 of operand &FF)", inline=True)
comment(0x91FF, "V=1 always, branch always taken (skips the CLV path)", inline=True)
comment(0x9201, "Alt entry: save caller's flags BEFORE forcing V=0", inline=True)
comment(0x9202, "Force V=0 -> OSWRCH path at &9220 (raw byte)", inline=True)
comment(0x9203, "Save X", inline=True)
comment(0x9204, "Save Y", inline=True)
comment(0x9205, "Save A (the byte to print)", inline=True)
comment(0x9206, "Save inner P — V here picks OSASCI vs OSWRCH later", inline=True)
comment(0x9207, "OSBYTE 199 (read/write *SPOOL file handle)", inline=True)
comment(0x9209, "X=0: handle value to write", inline=True)
comment(0x920B, "Y=0: write mode (NEW = (OLD AND 0) EOR X = X = 0)", inline=True)
comment(0x920D, "Closes spool; X returns OLD handle", inline=True)
comment(0x9210, "OLD < ' '? (likely 0 = was already closed)", inline=True)
comment(0x9212, "Yes: leave spool closed for the print", inline=True)
comment(0x9214, "OLD >= '0'?", inline=True)
comment(0x9216, "Yes (>= &30): leave spool closed", inline=True)
comment(0x9218, "OLD in [&20,&2F] (NFS handle range): re-open spool with X=OLD", inline=True)
comment(0x921B, "Clear X for the post-print restore", inline=True)
comment(0x921D, "Restore inner P (V=1 OSASCI / V=0 OSWRCH)", inline=True)
comment(0x921E, "Pull A (the byte)", inline=True)
comment(0x921F, "Push it back so the final epilogue PLA still works", inline=True)
comment(0x9220, "V=0 -> OSWRCH (raw); V=1 -> OSASCI (CR translation)", inline=True)
comment(0x9222, "OSASCI: writes A, translating CR to CR/LF", inline=True)
comment(0x9225, "Skip OSWRCH branch", inline=True)
comment(0x9227, "OSWRCH: writes A as a raw byte", inline=True)
comment(0x922A, "OSBYTE 199 again to restore spool state", inline=True)
comment(0x922C, "Y=&FF (read mode): NEW = OLD EOR X", inline=True)
comment(0x922E, "X=0 -> no change; X=OLD -> writes OLD back", inline=True)
comment(0x9231, "Pull A (preserved across the call)", inline=True)
comment(0x9232, "Pull Y", inline=True)
comment(0x9233, "Pull X", inline=True)
comment(0x9234, "Pull caller's original flags", inline=True)
comment(0x9235, "Return", inline=True)

# print_hex_byte_no_spool (&924C) — *SPOOL-bypassing two-digit hex print
comment(0x924C, "Save full byte", inline=True)
comment(0x924D, "Shift high nybble to low (LSR x4)", inline=True)
comment(0x9251, "Print high nybble as hex digit", inline=True)
comment(0x9254, "Restore full byte; fall through for low nybble",
        inline=True)

# print_hex_nybble_no_spool (&9255) — *SPOOL-bypassing single hex digit
comment(0x9255, "Mask to low nybble", inline=True)
comment(0x9257, "Digit >= &0A?", inline=True)
comment(0x9259, "No: skip letter adjustment", inline=True)
comment(0x925B, "Add 7 to get 'A'-'F' (6 + carry)", inline=True)
comment(0x925D, "Add &30 for ASCII '0'-'9' or 'A'-'F'", inline=True)
comment(0x925F, "Tail-jump to *SPOOL-bypassing print", inline=True)

# &9261-&9290: print_inline body. Inline comments live with the
# subroutine declaration earlier in the file.

# print_inline_no_spool inline comments (~22 items)
comment(0x928A, "Pop return-addr low byte (-> string pointer low)",
        inline=True)
comment(0x928B, "Save in fs_error_ptr (the loop's pointer low)",
        inline=True)
comment(0x928D, "Pop return-addr high byte", inline=True)
comment(0x928E, "Save in fs_crflag (the loop's pointer high)",
        inline=True)
comment(0x9290, "Y=0: indirect index for (fs_error_ptr),Y", inline=True)
comment(0x9292, "Step pointer low byte to next char", inline=True)
comment(0x9294, "No carry: skip high-byte INC", inline=True)
comment(0x9296, "Page wrap: bump pointer high", inline=True)
comment(0x9298, "Read next character from inline string", inline=True)
comment(0x929A, "Bit 7 set: terminator -- this byte is the next opcode",
        inline=True)
comment(0x929C, "Save pointer low (print_char_no_spool may clobber)",
        inline=True)
comment(0x929E, "Push it", inline=True)
comment(0x929F, "Save pointer high", inline=True)
comment(0x92A1, "Push it", inline=True)
comment(0x92A2, "Reload the character we're about to print", inline=True)
comment(0x92A4, "Print it via the *SPOOL-bypassing OSASCI wrapper",
        inline=True)
comment(0x92A7, "Pop pointer high back", inline=True)
comment(0x92A8, "Restore", inline=True)
comment(0x92AA, "Pop pointer low back", inline=True)
comment(0x92AB, "Restore", inline=True)
comment(0x92AD, "Always taken (BRA-style; A is non-zero from print)",
        inline=True)
comment(0x92AF, "Resume execution at the terminator byte's address "
        "(JMP indirect via fs_error_ptr)", inline=True)

# set_conn_active (&92A1) — set channel connection active flag
comment(0x92BD, "Convert to channel index", inline=True)

# clear_conn_active (&92B8) — clear channel connection active flag
comment(0x92D0, "Get stack pointer", inline=True)
comment(0x92D4, "Convert to channel index", inline=True)

# Shared exit for set/clear_conn_active
comment(0x92E2, "Transfer back to X", inline=True)

# svc_8_osword (&A4D6): Service 8 — OSWORD dispatch
# Handles OSWORD &0E-&14: clock read, transmit, receive, etc.
# Primary dispatch via PHA/PHA/RTS from tables at &A508/&A50F

# Entry: validate OSWORD number and dispatch
comment(0xA4F1, "Save current OS text pointer", inline=True)
comment(0xA4F4, "Mask access bits", inline=True)
comment(0xA4F7, "Clear bit 1 of mask", inline=True)
comment(0xA4F9, "Save into fs_lib_flags", inline=True)
comment(0xA4FC, "Begin parsing the *RUN argument", inline=True)
comment(0xA4FF, "X=1: TX-buffer write index for argument", inline=True)
comment(0xA501, "Copy argument to TX buffer", inline=True)
comment(0xA515, "Return from svc_8_osword", inline=True)
comment(0xA513, "Loop until all 6 restored", inline=True)
comment(0xA506, "Next byte down", inline=True)

# osword_setup_handler: push handler address and save state
comment(0xA51A, "Load handler address low byte", inline=True)

# Save osword_flag to RX buffer (reverse of return copy)
comment(0xA520, "Loop while X >= 0 (scan all 4 handle slots)", inline=True)
comment(0xA522, "RTS dispatches to pushed handler", inline=True)

# Dispatch tables at &A508 (lo) and &A50F (hi) are handled by
# rts_code_ptr() calls which produce symbolic label expressions.

# OSWORD &0E handler (&A516): read clock
# Copies clock data and converts binary to BCD
comment(0xA531, "Test station active flag", inline=True)
comment(0xA536, "C set: error from save_net_tx_cb -- abort *RUN", inline=True)
comment(0xA538, "Yes: handle clock read", inline=True)
comment(0xA53E, "Return", inline=True)

# Clock read handler (&A526): read time from workspace, convert to BCD
comment(0xA541, "Y=&10: length of TXCB to save", inline=True)
comment(0xA543, "Save current TX control block", inline=True)
comment(0xA54C, "Store BCD seconds", inline=True)
comment(0xA552, "Convert binary to BCD", inline=True)
comment(0xA558, "Load hours from clock workspace", inline=True)
comment(0xA561, "Clear hours high position", inline=True)
comment(0xA563, "Store zero", inline=True)
comment(0xA573, "Restore day+month byte", inline=True)
comment(0xA57A, "Store BCD month", inline=True)
comment(0xA57E, "Shift high nibble down", inline=True)
comment(0xA581, "4th shift: isolate high nibble", inline=True)
comment(0xA58A, "Copy 7 bytes (Y=6 down to 0)", inline=True)

# Copy BCD result to OSWORD parameter block
comment(0xA58F, "Store to parameter block", inline=True)
comment(0xA592, "Loop for all 7 bytes", inline=True)

# bin_to_bcd: convert binary value in A to BCD
comment(0xA5A1, "Error code &FE", inline=True)
comment(0xA5A3, "Raise 'Bad command' error", inline=True)

# OSWORD &10 handler (&A58B): transmit

# Transmit active: set up and begin
comment(0xA5B3, "Low byte = &6F", inline=True)
comment(0xA5B5, "Set osword_flag", inline=True)
comment(0xA5C3, "Set workspace pointer high", inline=True)
comment(0xA5CA, "Y=OSWORD flag (slot specifier)", inline=True)
comment(0xA5CF, "A=3: start searching from slot 3", inline=True)
comment(0xA5D4, "C set: slot invalid, store result", inline=True)
comment(0xA5D7, "Continue shift", inline=True)
comment(0xA5E5, "Transfer found slot to A", inline=True)
comment(0xA5E8, "Store slot number to PB byte 0", inline=True)
comment(0xA5ED, "C set: slot invalid, store result", inline=True)
comment(0xA5EF, "Y=Y-1: adjust workspace offset", inline=True)
comment(0xA5F8, "Compare Y with OSWORD flag", inline=True)
comment(0xA608, "Y=1: workspace flag offset", inline=True)
comment(0xA60A, "Store pending marker to workspace", inline=True)
comment(0xA60E, "Increment retry counter", inline=True)
comment(0xA613, "Store result A to PB via Y", inline=True)
comment(0xA615, "Rotate Econet flags back (restore state)", inline=True)
comment(0xA618, "Return from OSWORD 11 handler", inline=True)

# store_osword_pb_ptr: store parameter block pointers to workspace

# store_ptr_at_ws_y: store 16-bit pointer to workspace

# OSWORD &12 handler (&A61C): receive setup
comment(0xA61B, "Store to ws_ptr_lo", inline=True)
comment(0xA61D, "Y=&7F: last byte of RX buffer", inline=True)
comment(0xA625, "X-1: adjust count", inline=True)

# === Backfilled from 4.18 via fantasm backfill (threshold 50) ===
# 1914 comments propagated for 4.21 &A800-&BFFF region
comment(0xA903, "Zero: result is 0, skip loop", inline=True)
comment(0xA906, "Start BCD result at 0", inline=True)
comment(0xA908, "Clear carry for BCD add", inline=True)
comment(0xA909, "Add 1 in decimal mode", inline=True)
comment(0xA90B, "Count down binary value", inline=True)
comment(0xA90C, "Loop until zero", inline=True)
comment(0xA90F, "Return with BCD result in A", inline=True)
comment(0xA910, "ASL tx_complete_flag: old bit 7 -> C", inline=True)
comment(0xA913, "A = Y (saved index)", inline=True)
comment(0xA914, "C=1 (TX idle): start new transmission", inline=True)
comment(0xA916, "C=0 (TX busy): write status byte back to PB", inline=True)
comment(0xA918, "Return (TX still in progress)", inline=True)
comment(0xA91B, "Copy to ws_ptr_lo", inline=True)
comment(0xA91D, "Also set as NMI TX block high", inline=True)
comment(0xA91F, "Low byte = &6F", inline=True)
comment(0xA921, "Set osword_flag", inline=True)
comment(0xA923, "Set NMI TX block low", inline=True)
comment(0xA925, "X=&0F: byte count for copy", inline=True)
comment(0xA927, "Copy data and begin transmission", inline=True)
comment(0xA92A, "Jump to begin Econet transmission", inline=True)
comment(0xA92D, "Load NFS workspace page high byte", inline=True)
comment(0xA92F, "Set workspace pointer high", inline=True)
comment(0xA931, "Set workspace pointer low from Y", inline=True)
comment(0xA933, "Rotate Econet flags (save interrupt state)", inline=True)
comment(0xA936, "Y=OSWORD flag (slot specifier)", inline=True)
comment(0xA937, "Store OSWORD flag", inline=True)
comment(0xA939, "Non-zero: use specified slot", inline=True)
comment(0xA93B, "A=3: start searching from slot 3", inline=True)
comment(0xA93D, "Convert slot to 2-bit workspace index", inline=True)
comment(0xA940, "C set: slot invalid, store result", inline=True)
comment(0xA943, "Continue shift", inline=True)
comment(0xA945, "Load workspace byte at offset", inline=True)
comment(0xA947, "Zero: slot empty, store result", inline=True)
comment(0xA949, "Compare with &3F ('?' marker)", inline=True)
comment(0xA94B, "Match: slot found for receive", inline=True)
comment(0xA94E, "Transfer back to A", inline=True)
comment(0xA94F, "Loop back (A != 0)", inline=True)
comment(0xA952, "X=0: index for indirect store", inline=True)
comment(0xA954, "Store slot number to PB byte 0", inline=True)
comment(0xA956, "Convert specified slot to workspace index", inline=True)
comment(0xA959, "C set: slot invalid, store result", inline=True)
comment(0xA95C, "Update workspace pointer low", inline=True)
comment(0xA95E, "A=&C0: slot active marker", inline=True)
comment(0xA962, "X=&0B: byte count for PB copy", inline=True)
comment(0xA964, "Compare Y with OSWORD flag", inline=True)
comment(0xA966, "Add workspace byte (check slot state)", inline=True)
comment(0xA968, "Zero: slot ready, copy PB and mark", inline=True)
comment(0xA96A, "Negative: slot busy, increment and retry", inline=True)
comment(0xA96D, "Copy PB byte to workspace slot", inline=True)
comment(0xA970, "C set: copy done, finish", inline=True)
comment(0xA972, "A=&3F: mark slot as pending ('?')", inline=True)
comment(0xA974, "Y=1: workspace flag offset", inline=True)
comment(0xA976, "Store pending marker to workspace", inline=True)
comment(0xA97A, "Increment retry counter", inline=True)
comment(0xA97C, "Non-zero: retry copy loop", inline=True)
comment(0xA97E, "Decrement Y (adjust offset)", inline=True)
comment(0xA97F, "Store result A to PB via Y", inline=True)
comment(0xA981, "Rotate Econet flags back (restore state)", inline=True)
comment(0xA984, "Return from OSWORD 11 handler", inline=True)
comment(0xA985, "Set workspace from RX ptr high", inline=True)
comment(0xA987, "Store to ws_ptr_lo", inline=True)
comment(0xA989, "Y=&7F: last byte of RX buffer", inline=True)
comment(0xA98B, "Load port/count from RX buffer", inline=True)
comment(0xA98D, "Y=&80: set workspace pointer", inline=True)
comment(0xA98E, "Store as osword_flag", inline=True)
comment(0xA990, "X = port/count value", inline=True)
comment(0xA991, "X-1: adjust count", inline=True)
comment(0xA992, "Y=0 for copy", inline=True)
comment(0xA994, "Copy workspace data", inline=True)
comment(0xA997, "Update state and return", inline=True)
comment(0xA99A, "X = sub-code", inline=True)
comment(0xA99B, "Sub-code < &13?", inline=True)
comment(0xA99D, "Out of range: return", inline=True)
comment(0xAAD3, "Y=1: first handle in PB", inline=True)
comment(0xAAD5, "Load handle value from PB[Y]", inline=True)
comment(0xAAD7, "Must be >= &20", inline=True)
comment(0xAAD9, "Below range: invalid", inline=True)
comment(0xAADB, "Must be < &30", inline=True)
comment(0xAADD, "Above range: invalid", inline=True)
comment(0xAADF, "X = handle value", inline=True)
comment(0xAAE0, "Load fcb_attr_or_count_mid[handle]", inline=True)
comment(0xAAE3, "Non-zero: FCB exists", inline=True)
comment(0xAAE8, "Clear PB[0] status", inline=True)
comment(0xAAEA, "Skip to next handle", inline=True)
comment(0xAAEC, "Load fcb_flags[handle] flags", inline=True)
comment(0xAAEF, "Test bit 1 (allocated?)", inline=True)
comment(0xAAF1, "Not allocated: invalid", inline=True)
comment(0xAAF3, "X = handle value", inline=True)
comment(0xAAF4, "Store handle to fs_lib_flags+Y", inline=True)
comment(0xAAF7, "Load station from fcb_attr_or_count_mid", inline=True)
comment(0xAAFA, "Store station to fs_server_net+Y", inline=True)
comment(0xAAFD, "Is this handle 1 (Y=1)?", inline=True)
comment(0xAAFF, "No: check handle 2", inline=True)
comment(0xAB03, "Bit mask &04 for handle 1", inline=True)
comment(0xAB05, "Update flags across all FCBs", inline=True)
comment(0xAB09, "Back to Y", inline=True)
comment(0xAB0A, "Reload fcb_flags flags", inline=True)
comment(0xAB0D, "Set bits 2+5 (active+updated)", inline=True)
comment(0xAB0F, "Store updated flags", inline=True)
comment(0xAB12, "Next handle slot", inline=True)
comment(0xAB15, "No: process next handle", inline=True)
comment(0xAB17, "Y=3 for return", inline=True)
comment(0xAB19, "Is this handle 2 (Y=2)?", inline=True)
comment(0xAB1B, "No: must be handle 3", inline=True)
comment(0xAB1E, "Push Y", inline=True)
comment(0xAB21, "Update flags across all FCBs", inline=True)
comment(0xAB24, "Restore Y", inline=True)
comment(0xAB25, "Back to Y", inline=True)
comment(0xAB26, "Reload fcb_flags flags", inline=True)
comment(0xAB2B, "Store updated flags", inline=True)
comment(0xAB2E, "Next handle slot", inline=True)
comment(0xAB30, "Handle 3: save Y", inline=True)
comment(0xAB32, "Bit mask &10 for handle 3", inline=True)
comment(0xAB34, "Update flags across all FCBs", inline=True)
comment(0xAB38, "Back to Y", inline=True)
comment(0xAB39, "Reload fcb_flags flags", inline=True)
comment(0xAB3C, "Set bits 4+5 (active+updated)", inline=True)
comment(0xAB3E, "Store updated flags", inline=True)
comment(0xAB41, "Next handle slot", inline=True)
comment(0xAB44, "Push X", inline=True)
comment(0xAB47, "Load FCB flags", inline=True)
comment(0xAB4A, "Shift bits 6-7 into bits 7-0", inline=True)
comment(0xAB4C, "Bit 6 clear: skip entry", inline=True)
comment(0xAB4E, "Restore Y (bit mask)", inline=True)
comment(0xAB4F, "Test mask bits against flags", inline=True)
comment(0xAB52, "Zero: no matching bits", inline=True)
comment(0xAB54, "Matching: restore Y", inline=True)
comment(0xAB55, "Set bit 5 (updated)", inline=True)
comment(0xAB57, "Skip clear path", inline=True)
comment(0xAB59, "No match: restore Y", inline=True)
comment(0xAB5A, "Invert all bits", inline=True)
comment(0xAB5C, "Clear tested bits in flags", inline=True)
comment(0xAB5F, "Store updated flags", inline=True)
comment(0xAB63, "Loop for all 16 entries", inline=True)
comment(0xAB65, "Restore original X", inline=True)
comment(0xAB66, "Back to X", inline=True)
comment(0xAB6A, "Load (net_rx_ptr)+1", inline=True)
comment(0xAB6C, "Y=0", inline=True)
comment(0xAB6E, "Store to PB[1] and return", inline=True)
comment(0xAB71, "Y=&7F: port byte offset", inline=True)
comment(0xAB73, "Load (net_rx_ptr)+&7F", inline=True)
comment(0xAB75, "Y=1", inline=True)
comment(0xAB77, "Store to PB[1]", inline=True)
comment(0xAB7A, "A=&80", inline=True)
comment(0xAB7C, "Store &80 to PB[2]", inline=True)
comment(0xAB7E, "Return", inline=True)
comment(0xAB7F, "Load error flag", inline=True)
comment(0xAB82, "Y=1: parameter block offset 1", inline=True)
comment(0xAB83, "Store result to PB[1]", inline=True)
comment(0xAB85, "Return", inline=True)
comment(0xAB86, "Load context byte", inline=True)
comment(0xAB89, "Bit 7 clear: store context to PB", inline=True)
comment(0xAB8B, "Total buffers = &6F", inline=True)
comment(0xAB8E, "Free = &6F - spool_buf_idx", inline=True)
comment(0xAB91, "Non-negative: store free count to PB", inline=True)
comment(0xAB94, "Return", inline=True)
comment(0xAB97, "Store to PB[Y]", inline=True)
comment(0xAB99, "Done 3 bytes?", inline=True)
comment(0xAB9B, "No: loop", inline=True)
comment(0xAB9E, "Next byte offset", inline=True)
comment(0xAB9F, "Load PB[Y]", inline=True)
comment(0xABA1, "Store to tx_retry_count[Y]", inline=True)
comment(0xABA4, "Done 3 bytes?", inline=True)
comment(0xABA6, "No: loop", inline=True)
comment(0xABA8, "Return", inline=True)
comment(0xABA9, "Poll for bridge", inline=True)
comment(0xABAC, "Y=0", inline=True)
comment(0xABAE, "Load bridge status", inline=True)
comment(0xABB1, "Is it &FF (no bridge)?", inline=True)
comment(0xABB3, "No: bridge found", inline=True)
comment(0xABB6, "PB[0] = 0 (no bridge)", inline=True)
comment(0xABBB, "Y=1", inline=True)
comment(0xABBC, "PB[1] = bridge status", inline=True)
comment(0xABBF, "Y=3", inline=True)
comment(0xABC0, "Load PB[3] (caller value)", inline=True)
comment(0xABC2, "Zero: use default station", inline=True)
comment(0xABC4, "Compare with bridge status", inline=True)
comment(0xABC9, "Same: confirm station", inline=True)
comment(0xABCB, "Load default from fs_server_net", inline=True)
comment(0xABCE, "Store to PB[3]", inline=True)
comment(0xABD1, "TX 0: ctrl = &82 (immediate mode)", inline=True)
comment(0xABD2, "TX 1: port = &9C (bridge discovery)", inline=True)
comment(0xABD3, "TX 2: dest station = &FF (broadcast)", inline=True)
comment(0xABD4, "TX 3: dest network = &FF (all nets)", inline=True)
comment(0xABD5, "TX 4-9: immediate data payload", inline=True)
comment(0xABDC, "TX 11: &00 (terminator)", inline=True)
comment(0xABDD, "RX 0: ctrl = &7F (receive)", inline=True)
comment(0xABDE, "RX 1: port = &9C (bridge discovery)", inline=True)
comment(0xABDF, "RX 2: station = &00 (any)", inline=True)
comment(0xABE0, "RX 3: network = &00 (any)", inline=True)
comment(0xABE3, "RX 6: extended addr fill (&FF)", inline=True)
comment(0xABE4, "RX 7: extended addr fill (&FF)", inline=True)
comment(0xABE6, "RX 9: buf end hi (&0D) -> &0D74", inline=True)
comment(0xABE9, "Check bridge status", inline=True)
comment(0xABEC, "Is it &FF (uninitialised)?", inline=True)
comment(0xABEE, "No: bridge already active, return", inline=True)
comment(0xABF0, "Save Y", inline=True)
comment(0xABF1, "Preserve Y on stack", inline=True)
comment(0xABF2, "Y=&18: workspace offset for init", inline=True)
comment(0xABF4, "X=&0B: 12 bytes to copy", inline=True)
comment(0xABF6, "Rotate econet_flags right (save flag)", inline=True)
comment(0xABF9, "Load init data byte", inline=True)
comment(0xABFC, "Store to workspace", inline=True)
comment(0xABFE, "Load TXCB template byte", inline=True)
comment(0xAC01, "Store to TX control block", inline=True)
comment(0xAC03, "Next workspace byte", inline=True)
comment(0xAC04, "Next template byte", inline=True)
comment(0xAC05, "Loop for all 12 bytes", inline=True)
comment(0xAC07, "Store X (-1) as bridge counter", inline=True)
comment(0xAC0A, "Restore econet_flags flag", inline=True)
comment(0xAC0D, "Shift ws_0d60 left (check status)", inline=True)
comment(0xAC10, "C=0: status clear, retry", inline=True)
comment(0xAC12, "Control byte &82 for TX", inline=True)
comment(0xAC14, "Set in TX control block", inline=True)
comment(0xAC16, "Data block at &00C0", inline=True)
comment(0xAC18, "Set NMI TX block low", inline=True)
comment(0xAC1A, "High byte = 0 (page 0)", inline=True)
comment(0xAC1C, "Set NMI TX block high", inline=True)
comment(0xAC1E, "Begin Econet transmission", inline=True)
comment(0xAC21, "Test TX control block bit 7", inline=True)
comment(0xAC23, "Negative: TX still in progress", inline=True)
comment(0xAC50, "Y=&23: workspace offset for params", inline=True)
comment(0xAC52, "Set owner access mask", inline=True)
comment(0xAC55, "Load TXCB init byte", inline=True)
comment(0xAC58, "Non-zero: use template value", inline=True)
comment(0xAC5A, "Zero: use workspace default value", inline=True)
comment(0xAC5D, "Store to workspace", inline=True)
comment(0xAC5F, "Next byte down", inline=True)
comment(0xAC60, "Until Y reaches &17", inline=True)
comment(0xAC62, "Loop for all bytes", inline=True)
comment(0xAC65, "Set net_tx_ptr low byte", inline=True)
comment(0xAC67, "Y=&1C: workspace offset for PB pointer", inline=True)
comment(0xAC69, "Load PB page number", inline=True)
comment(0xAC6B, "PB starts at next page boundary (+1)", inline=True)
comment(0xAC6D, "Store PB start pointer at ws[&1C]", inline=True)
comment(0xAC70, "Y=1: PB byte 1 (transfer length)", inline=True)
comment(0xAC72, "Load transfer length from PB", inline=True)
comment(0xAC76, "Add PB base for buffer end address", inline=True)
comment(0xAC78, "Store PB pointer to workspace", inline=True)
comment(0xAC7B, "Y=2: parameter offset", inline=True)
comment(0xAC7D, "Control byte &90", inline=True)
comment(0xAC7F, "Set escapable flag", inline=True)
comment(0xAC81, "Store control byte to PB", inline=True)
comment(0xAC85, "Load workspace data", inline=True)
comment(0xAC88, "Store to parameter block", inline=True)
comment(0xAC8A, "Next byte", inline=True)
comment(0xAC8B, "Until Y reaches 7", inline=True)
comment(0xAC8D, "Loop for 3 bytes (Y=4,5,6)", inline=True)
comment(0xAC91, "Store to net_tx_ptr_hi", inline=True)
comment(0xAC93, "Enable interrupts", inline=True)
comment(0xAC96, "Y=&20: workspace offset", inline=True)
comment(0xAC98, "Set to &FF (pending)", inline=True)
comment(0xAC9A, "Mark send pending in workspace", inline=True)
comment(0xAC9D, "Also mark offset &21", inline=True)
comment(0xAC9F, "Y=&19: control offset", inline=True)
comment(0xACA1, "Control byte &90", inline=True)
comment(0xACA3, "Store to workspace", inline=True)
comment(0xACA5, "Y=&18: RX control offset", inline=True)
comment(0xACA6, "Control byte &7F", inline=True)
comment(0xACA8, "Store RX control", inline=True)
comment(0xACAA, "Wait for TX acknowledgement", inline=True)
comment(0xACAD, "Store address low byte at ws[Y]", inline=True)
comment(0xACAF, "Advance to high byte offset", inline=True)
comment(0xACB0, "Load high byte base (table_idx)", inline=True)
comment(0xACB2, "Add carry for page crossing", inline=True)
comment(0xACB4, "Store address high byte at ws[Y+1]", inline=True)
comment(0xACB7, "Save processor flags", inline=True)
comment(0xACBA, "Load station number from PB", inline=True)
comment(0xACBC, "X = station number", inline=True)
comment(0xACBE, "Load network number from PB", inline=True)
comment(0xACC0, "Y=3: workspace start offset", inline=True)
comment(0xACC1, "Store Y as ws_ptr_lo", inline=True)
comment(0xACC3, "Y=&72: workspace offset for dest", inline=True)
comment(0xACC5, "Store network to workspace", inline=True)
comment(0xACC7, "Y=&71", inline=True)
comment(0xACC8, "A = station (from X)", inline=True)
comment(0xACC9, "Store station to workspace", inline=True)
comment(0xACCB, "Restore flags from PHP", inline=True)
comment(0xACCC, "Non-zero sub-code: handle burst", inline=True)
comment(0xACCE, "Load current offset", inline=True)
comment(0xACD0, "Advance offset for next byte", inline=True)
comment(0xACD2, "Load next char from PB", inline=True)
comment(0xACD4, "Zero: end of data, return", inline=True)
comment(0xACD8, "Store char to RX buffer", inline=True)
comment(0xACDA, "Save char for later test", inline=True)
comment(0xACDB, "Init workspace copy for wide xfer", inline=True)
comment(0xACDF, "Set bit 7: Tube needs release", inline=True)
comment(0xACE1, "Enable IRQ and send packet", inline=True)
comment(0xACE4, "Delay countdown", inline=True)
comment(0xACE7, "Restore char", inline=True)
comment(0xACE8, "Test if char was CR (&0D)", inline=True)
comment(0xACEC, "CR sent: return", inline=True)
comment(0xACED, "Init workspace for wide copy", inline=True)
comment(0xACF2, "Load buffer size", inline=True)
comment(0xACF6, "Store adjusted size", inline=True)
comment(0xACF9, "Send packet and return", inline=True)
comment(0xACFC, "Save processor flags", inline=True)
comment(0xACFD, "Save A", inline=True)
comment(0xACFE, "Save X", inline=True)
comment(0xACFF, "Push X", inline=True)
comment(0xAD00, "Save Y", inline=True)
comment(0xAD01, "Push Y", inline=True)
comment(0xAD02, "Get stack pointer", inline=True)
comment(0xAD03, "Read OSWORD number from stack", inline=True)
comment(0xAD06, "OSWORD >= 9?", inline=True)
comment(0xAD08, "Yes: out of range, restore + return", inline=True)
comment(0xAD0A, "X = OSWORD number", inline=True)
comment(0xAD0B, "Push handler address for dispatch", inline=True)
comment(0xAD0E, "Restore Y", inline=True)
comment(0xAD0F, "Back to Y", inline=True)
comment(0xAD10, "Restore X", inline=True)
comment(0xAD11, "Back to X", inline=True)
comment(0xAD12, "Restore A", inline=True)
comment(0xAD1D, "Reload OSWORD number for handler", inline=True)
comment(0xAD2F, "hi OSWORD 6: no-op (RTS)", inline=True)
comment(0xAD39, "A = original Y", inline=True)
comment(0xAD40, "Y=&D9: workspace abort offset", inline=True)
comment(0xAD42, "Store abort code to workspace", inline=True)
comment(0xAD4A, "Save current TX ptr low", inline=True)
comment(0xAD50, "Set TX ptr to workspace offset", inline=True)
comment(0xAD54, "Set TX ptr high", inline=True)
comment(0xAD56, "Send the abort packet", inline=True)
comment(0xAD59, "Set status to &3F (complete)", inline=True)
comment(0xAD5B, "Store at TX ptr offset 0", inline=True)
comment(0xAD64, "Load PB pointer high", inline=True)
comment(0xAD66, "Compare with &81 (special case)", inline=True)
comment(0xAD68, "Match: skip to processing", inline=True)
comment(0xAD6C, "X=&0A: 11 codes to check", inline=True)
comment(0xAD74, "Y=-1: flag second range", inline=True)
comment(0xAD75, "X=&11: 18 codes to check", inline=True)
comment(0xAD7C, "Not found: increment Y", inline=True)
comment(0xAD7D, "X=2: default state", inline=True)
comment(0xAD7F, "A = Y (search result)", inline=True)
comment(0xAD82, "Save result flags", inline=True)
comment(0xAD86, "Y=&DC: workspace offset for save", inline=True)
comment(0xAD90, "Loop for 3 bytes", inline=True)
comment(0xAD92, "A = state (2 or 3)", inline=True)
comment(0xADA1, "Positive: keep waiting", inline=True)
comment(0xADA3, "Get stack pointer", inline=True)
comment(0xADA4, "Y=&DD: workspace result offset", inline=True)
comment(0xADA8, "Set bit 6 and bit 2", inline=True)
comment(0xADAA, "Always branch (NZ from ORA)", inline=True)
comment(0xADC1, "Range 1+2: OSWORD &04", inline=True)
comment(0xADC2, "Range 1+2: OSWORD &09", inline=True)
comment(0xADC4, "Range 1+2: OSWORD &14", inline=True)
comment(0xADC5, "Range 1+2: OSWORD &15", inline=True)
comment(0xADC7, "Range 1+2: OSWORD &9B", inline=True)
comment(0xADC8, "Range 1+2: OSWORD &E1", inline=True)
comment(0xADCA, "Range 1+2: OSWORD &E3", inline=True)
comment(0xADCB, "Range 1+2: OSWORD &E4", inline=True)
comment(0xADCD, "Range 2 only: OSWORD &0C", inline=True)
comment(0xADCE, "Range 2 only: OSWORD &0F", inline=True)
comment(0xADCF, "Range 2 only: OSWORD &79", inline=True)
comment(0xADD2, "Range 2 only: OSWORD &87", inline=True)
comment(0xADD3, "Y=&0E: copy 15 bytes (0-14)", inline=True)
comment(0xADD7, "Yes: handle", inline=True)
comment(0xADDB, "No: return", inline=True)
comment(0xADDD, "Workspace low = &DB", inline=True)
comment(0xADDF, "Set nfs_workspace low byte", inline=True)
comment(0xADE3, "Store to workspace[Y]", inline=True)
comment(0xADE8, "Y=0", inline=True)
comment(0xADE9, "Workspace low = &DA", inline=True)
comment(0xADEB, "Load OSWORD number", inline=True)
comment(0xADED, "Store at workspace+0 (= &DA)", inline=True)
comment(0xADEF, "Workspace low = 0 (restore)", inline=True)
comment(0xADF3, "Control value &E9", inline=True)
comment(0xADFC, "Restore nfs_workspace low", inline=True)
comment(0xAE00, "Y=&7C: workspace destination offset", inline=True)
comment(0xAE02, "Test bit 6 (V flag check)", inline=True)
comment(0xAE05, "V=1: skip to wide mode copy", inline=True)
comment(0xAE07, "Y=&17: narrow mode dest offset", inline=True)
comment(0xAE09, "X=&1A: 27 bytes to copy", inline=True)
comment(0xAE0B, "Clear V flag for narrow mode", inline=True)
comment(0xAE17, "Is it &FC? (page ptr marker)", inline=True)
comment(0xAE1B, "&FC: load RX buffer page", inline=True)
comment(0xAE1F, "V=0: use nfs_workspace_hi", inline=True)
comment(0xAE21, "Store as TX ptr high", inline=True)
comment(0xAE33, "Wide &6F: ctrl=&85", inline=True)
comment(0xAE35, "Wide &71: skip (dest station)", inline=True)
comment(0xAE38, "Wide &74: buf start hi=page ptr", inline=True)
comment(0xAE39, "Wide &75: buf start ext lo", inline=True)
comment(0xAE3A, "Wide &76: buf start ext hi", inline=True)
comment(0xAE3B, "Wide &77: buf end lo=&7E", inline=True)
comment(0xAE3E, "Wide &7A: buf end ext hi", inline=True)
comment(0xAE3F, "Wide &7B: zero", inline=True)
comment(0xAE40, "Wide &7C: zero", inline=True)
comment(0xAE41, "Narrow stop (&FE terminator)", inline=True)
comment(0xAE44, "Narrow &0E: skip (dest station)", inline=True)
comment(0xAE47, "Narrow &11: buf start hi=page ptr", inline=True)
comment(0xAE48, "Narrow &12: buf start ext lo", inline=True)
comment(0xAE49, "Narrow &13: buf start ext hi", inline=True)
comment(0xAE4A, "Narrow &14: buf end lo=&DE", inline=True)
comment(0xAE4D, "Narrow &17: buf end ext hi", inline=True)
comment(0xAE4E, "Spool stop (&FE terminator)", inline=True)
comment(0xAE51, "Spool &03: skip (dest network)", inline=True)
comment(0xAE54, "Spool &06: buf start ext lo", inline=True)
comment(0xAE55, "Spool &07: buf start ext hi", inline=True)
comment(0xAE56, "Spool &08: skip (buf end lo)", inline=True)
comment(0xAE59, "Spool &0B: buf end ext hi", inline=True)
comment(0xAE5B, "Match osword_pb_ptr?", inline=True)
comment(0xAE5D, "No: return (not our PB)", inline=True)
comment(0xAE5F, "Load spool state byte", inline=True)
comment(0xAE62, "C=1: already active, return", inline=True)
comment(0xAE64, "Buffer start offset = &21", inline=True)
comment(0xAE66, "Store as buffer pointer", inline=True)
comment(0xAE69, "Control state &41", inline=True)
comment(0xAE6B, "Store as spool control state", inline=True)
comment(0xAE6E, "Return", inline=True)
comment(0xAE6F, "Check Y == 4", inline=True)
comment(0xAE73, "A = X (control byte)", inline=True)
comment(0xAE75, "Non-zero: handle spool ctrl byte", inline=True)
comment(0xAE78, "OR with stack value", inline=True)
comment(0xAE7B, "Store back to stack", inline=True)
comment(0xAE7E, "OSBYTE &91: read buffer", inline=True)
comment(0xAE80, "X=3: printer buffer", inline=True)
comment(0xAE82, "Read character from buffer", inline=True)
comment(0xAE87, "A = extracted character", inline=True)
comment(0xAE88, "Add byte to RX buffer", inline=True)
comment(0xAE8B, "Buffer past &6E limit?", inline=True)
comment(0xAE8D, "No: read more from buffer", inline=True)
comment(0xAE92, "More room: continue reading", inline=True)
comment(0xAE9D, "Rotate bit 0 into carry", inline=True)
comment(0xAEA0, "Load spool control state", inline=True)
comment(0xAEA4, "Rotate bit 0 into carry", inline=True)
comment(0xAEA5, "Restore state", inline=True)
comment(0xAEA6, "C=1: already started, reset", inline=True)
comment(0xAEA8, "Set bits 0-1 (active + pending)", inline=True)
comment(0xAEAA, "Store updated state", inline=True)
comment(0xAED3, "Save state", inline=True)
comment(0xAED5, "Restore state", inline=True)
comment(0xAEE0, "Push for later restore", inline=True)
comment(0xAEEC, "X=0", inline=True)
comment(0xAEFF, "Push for restore", inline=True)
comment(0xAF1A, "Save station", inline=True)
comment(0xAF23, "Restore station", inline=True)
comment(0xAFAF, "X=&FF: start search from -1", inline=True)
comment(0xAFB1, "Y = disconnect code", inline=True)
comment(0xAFB4, "Compare with station table entry", inline=True)
comment(0xAFC2, "Check station and network match", inline=True)
comment(0xAFD3, "Send the packet", inline=True)
comment(0xAFE3, "Check original disconnect code", inline=True)
comment(0xAFE7, "Non-zero: use &90 control", inline=True)
comment(0xAFF0, "Save status on stack", inline=True)
comment(0xAFF8, "Restore status", inline=True)
comment(0xAFFA, "Compare with current TX buffer", inline=True)
comment(0xAFFC, "Rotate result bit 0 to carry", inline=True)
comment(0xB002, "ctrl=&80 (standard TX)", inline=True)
comment(0xB003, "port=&9F", inline=True)
comment(0xB004, "dest station=&00 (filled later)", inline=True)
comment(0xB005, "dest network=&00 (filled later)", inline=True)
comment(0xB006, "buf start lo (&9F)", inline=True)
comment(0xB007, "buf start hi (&8E); start = &8E9F", inline=True)
comment(0xB008, "buf start ext lo=&FF", inline=True)
comment(0xB009, "buf start ext hi=&FF", inline=True)
comment(0xB00A, "buf end lo (&A7)", inline=True)
comment(0xB00B, "buf end hi (&8E); end = &8EA7", inline=True)
comment(0xB00C, "buf end ext lo=&FF", inline=True)
comment(0xB00D, "buf end ext hi=&FF", inline=True)
comment(0xB00E, "ctrl=&7F (RX listen)", inline=True)
comment(0xB00F, "port=&9E", inline=True)
comment(0xB010, "skip: preserve dest station", inline=True)
comment(0xB013, "buf start hi=page ptr (&FC)", inline=True)
comment(0xB014, "buf start ext lo=&FF", inline=True)
comment(0xB015, "buf start ext hi=&FF", inline=True)
comment(0xB018, "buf end ext lo=&FF", inline=True)
comment(0xB019, "buf end ext hi=&FF", inline=True)
# &B01A-&B05D inlines: see deliberate review block above (lang_2_save_palette_vdu)
comment(0xB030, "A=0 for first palette entry", inline=True)
comment(0xB039, "Read palette entry", inline=True)
comment(0xB041, "Y=1: physical colour offset", inline=True)
comment(0xB044, "Save for next iteration", inline=True)
comment(0xB04B, "Y=0", inline=True)
comment(0xB298, "Data: option string offset table", inline=True)
comment(0xB29F, "X=0: start of buffer", inline=True)
comment(0xB2A1, "Y=0: start of argument", inline=True)
comment(0xB2A4, "Get character from command line", inline=True)
comment(0xB2A9, "Carry clear: skip validation", inline=True)
comment(0xB2AF, "Yes: '&' not allowed in filenames", inline=True)
comment(0xB2B1, "'&' in filename: bad filename", inline=True)
comment(0xB2B5, "Is it CR (end of line)?", inline=True)
comment(0xB2B9, "Load character from end of buffer", inline=True)
comment(0xB2BC, "Test for space (&20)", inline=True)
comment(0xB2C6, "ALWAYS: trim next character back", inline=True)
comment(0xB2C8, "A=0: success return code", inline=True)
comment(0xB2D4, "Store masked flags", inline=True)
# &B2E0..&B2F0 inlines covered by the deliberate review block above
# (loop_scan_entries / ex_print_col_sep).
comment(0xB3AC, "A=1: check printer ready", inline=True)
comment(0xB3AE, "Test printer server workspace flag", inline=True)
comment(0xB3B1, "Non-zero: printer available", inline=True)
comment(0xB3B3, "Printer not available: error", inline=True)
comment(0xB3B6, "Initialise spool drive", inline=True)
comment(0xB3B9, "Save pointer to spool buffer", inline=True)
comment(0xB3BE, "End of command line?", inline=True)
comment(0xB3C0, "Yes: no argument given", inline=True)
comment(0xB3C2, "Clear V (= explicit PS name given)", inline=True)
comment(0xB3C3, "Is first char a decimal digit?", inline=True)
comment(0xB3C9, "Save Y", inline=True)
comment(0xB3CA, "Load PS server address", inline=True)
comment(0xB3CD, "Restore Y", inline=True)
comment(0xB3CE, "Back to Y register", inline=True)
comment(0xB3CF, "Parse FS/PS arguments", inline=True)
comment(0xB3D2, "Jump to store station address", inline=True)
comment(0xB3D5, "Start at offset &18", inline=True)
comment(0xB3D7, "X=&F8: offset into template", inline=True)
comment(0xB3D9, "Get template byte", inline=True)
comment(0xB3DF, "Next source offset", inline=True)
comment(0xB3E3, "Set V (= no explicit PS name)", inline=True)
comment(0xB3E8, "V set: skip PS name parsing", inline=True)
comment(0xB3EA, "Max 6 characters for PS name", inline=True)
comment(0xB3EC, "Buffer offset &1C for PS name", inline=True)
comment(0xB3EE, "Space character", inline=True)
comment(0xB3F0, "Fill buffer with space", inline=True)
comment(0xB3F3, "Count down", inline=True)
comment(0xB3F6, "Save text pointer", inline=True)
comment(0xB3FB, "Initialise string reading", inline=True)
comment(0xB3FE, "Empty string: skip to send", inline=True)
comment(0xB402, "Save updated string pointer", inline=True)
comment(0xB404, "Buffer offset for PS name", inline=True)
comment(0xB406, "Save buffer position", inline=True)
comment(0xB408, "Restore string pointer", inline=True)
comment(0xB40A, "Read next character", inline=True)
comment(0xB40D, "Save updated pointer", inline=True)
comment(0xB411, "Store char uppercased in buffer", inline=True)
comment(0xB414, "Loop for more characters", inline=True)
comment(0xB416, "Copy reversed PS name to TX", inline=True)
comment(0xB419, "Send PS status request", inline=True)
comment(0xB41C, "Pop and requeue PS scan", inline=True)
comment(0xB41F, "Load PS server address", inline=True)
comment(0xB422, "A=0", inline=True)
comment(0xB425, "Offset &24 in buffer", inline=True)
comment(0xB427, "Clear PS status byte", inline=True)
comment(0xB42A, "Zero: all slots done", inline=True)
comment(0xB42D, "Transfer to Y", inline=True)
comment(0xB42E, "Read slot status", inline=True)
comment(0xB430, "Bit 7 clear: slot inactive", inline=True)
comment(0xB450, "Transfer to Y", inline=True)
# &B497 inline covered by deliberate review block above.
comment(0xB4B4, "Pop return address low", inline=True)
comment(0xB4BA, "Push 0 as end-of-list marker", inline=True)
comment(0xB4BD, "Start scanning from offset &84", inline=True)
comment(0xB4C1, "Shift PS slot flags right", inline=True)
comment(0xB4C6, "Convert to 2-bit workspace index", inline=True)
comment(0xB4C9, "Carry set: no more slots", inline=True)
comment(0xB4CC, "To get slot offset", inline=True)
comment(0xB4D8, "Loop for more slots", inline=True)
comment(0xB4E1, "Low byte: workspace page", inline=True)
comment(0xB4FC, "Write another page + &FF bytes", inline=True)
comment(0xB502, "Shift PS slot flags back", inline=True)
comment(0xB507, "Push onto stack", inline=True)
comment(0xB515, "Middle loop: 10 iterations", inline=True)
comment(0xB519, "Outer loop: ~1000 delay cycles", inline=True)
comment(0xB521, "A=&FF", inline=True)
comment(0xB527, "Write byte to workspace", inline=True)
comment(0xB529, "Advance Y", inline=True)
comment(0xB52B, "Start of PS name at offset &1C", inline=True)
comment(0xB535, "End of TX name field at &1B", inline=True)
comment(0xB537, "Pop byte (reversed order)", inline=True)
comment(0xB53B, "Start of TX field (&0F)?", inline=True)
comment(0xB53F, "Copy RX page to TX", inline=True)
comment(0xB543, "TX offset &10", inline=True)
comment(0xB552, "Control byte &80 (immediate TX)", inline=True)
comment(0xB553, "Port &9F (printer server)", inline=True)
comment(0xB554, "Station &FF (any)", inline=True)
comment(0xB555, "Network &FF (any)", inline=True)
comment(0xB556, "Save V flag (controls padding)", inline=True)
comment(0xB55E, "'.' separator", inline=True)
comment(0xB563, "Set V (suppress station padding)", inline=True)
comment(0xB568, "Print 4 spaces (padding)", inline=True)
comment(0xB571, "Restore flags", inline=True)
comment(0xB572, "Print station as 3 digits", inline=True)
# &B6F3..&B701 inlines covered by the deliberate review block above (cmd_wipe).
# &B703..&B7C9 inlines covered by deliberate review block above (request_next_wipe).
# &B7CB inline covered by deliberate review block (prompt_yn).
comment(0xB7D3, "OSBYTE &0F: flush buffer class", inline=True)
comment(0xB7D5, "X=1: flush input buffers", inline=True)
comment(0xB7D7, "Flush keyboard buffer before read", inline=True)
comment(0xB7DA, "Read character from input stream", inline=True)
comment(0xB7DD, "C clear: character read OK", inline=True)
comment(0xB7DF, "Escape pressed: raise error", inline=True)
comment(0xB7E2, "Return with character in A", inline=True)
comment(0xB7E3, "A=0: clear value", inline=True)
comment(0xB7E5, "Y=0: start index", inline=True)
comment(0xB7E6, "Clear channel table entry", inline=True)
comment(0xB7E9, "Next entry", inline=True)
comment(0xB7EA, "Loop until all 256 bytes cleared", inline=True)
comment(0xB7EC, "Offset &0F in receive buffer", inline=True)
comment(0xB7EE, "Get number of available channels", inline=True)
comment(0xB7F0, "Prepare subtraction", inline=True)
comment(0xB7F1, "Subtract 'Z' to get negative count", inline=True)
comment(0xB7F3, "Y = negative channel count (index)", inline=True)
comment(0xB7F4, "Channel marker &40 (available)", inline=True)
comment(0xB7F6, "Mark channel slot as available", inline=True)
comment(0xB7F9, "Previous channel slot", inline=True)
comment(0xB7FA, "Reached start of channel range?", inline=True)
comment(0xB7FC, "No: continue marking channels", inline=True)
comment(0xB7FE, "Point to first channel slot", inline=True)
comment(0xB7FF, "Active channel marker &C0", inline=True)
comment(0xB801, "Mark first channel as active", inline=True)
comment(0xB804, "Return", inline=True)
comment(0xB805, "Save flags", inline=True)
comment(0xB806, "Prepare subtraction", inline=True)
comment(0xB807, "Subtract &20 to get table index", inline=True)
comment(0xB809, "Negative: out of valid range", inline=True)
comment(0xB80B, "Above maximum channel index &0F?", inline=True)
comment(0xB80D, "In range: valid index", inline=True)
comment(0xB80F, "Out of range: return &FF (invalid)", inline=True)
comment(0xB811, "Restore flags", inline=True)
comment(0xB812, "X = channel index (or &FF)", inline=True)
comment(0xB813, "Return", inline=True)
comment(0xB814, "Below space?", inline=True)
comment(0xB816, "Yes: invalid channel character", inline=True)
comment(0xB818, "Below '0'?", inline=True)
comment(0xB81A, "In range &20-&2F: look up channel", inline=True)
comment(0xB81C, "Save channel character", inline=True)
comment(0xB81D, "Error code &DE", inline=True)
comment(0xB81F, "Generate 'Net channel' error", inline=True)
comment(0xB82E, "Error string continuation (unreachable)", inline=True)
comment(0xB847, "Save channel character", inline=True)
comment(0xB848, "Prepare subtraction", inline=True)
comment(0xB849, "Convert char to table index", inline=True)
comment(0xB84B, "X = channel table index", inline=True)
comment(0xB84C, "Look up network number for channel", inline=True)
comment(0xB84F, "Zero: channel not found, raise error", inline=True)
comment(0xB851, "Check station/network matches current", inline=True)
comment(0xB854, "No match: build detailed error msg", inline=True)
comment(0xB856, "Discard saved channel character", inline=True)
comment(0xB857, "Load channel status flags", inline=True)
comment(0xB85A, "Return; A = channel flags", inline=True)
comment(0xB85B, "Error code &DE", inline=True)
comment(0xB85D, "Store error code in error block", inline=True)
comment(0xB860, "BRK opcode", inline=True)
comment(0xB862, "Store BRK at start of error block", inline=True)
comment(0xB865, "X=0: copy index", inline=True)
comment(0xB866, "Advance copy position", inline=True)
comment(0xB867, "Load 'Net channel' string byte", inline=True)
comment(0xB86A, "Copy to error text", inline=True)
comment(0xB86D, "Continue until NUL terminator", inline=True)
comment(0xB86F, "Save end-of-string position", inline=True)
comment(0xB871, "Save for suffix append", inline=True)
comment(0xB873, "Retrieve channel character", inline=True)
comment(0xB874, "Append ' N' (channel number)", inline=True)
comment(0xB877, "Load 'Net channel' end position", inline=True)
comment(0xB879, "Skip past NUL to suffix string", inline=True)
comment(0xB87A, "Advance destination position", inline=True)
comment(0xB87B, "Load ' not on this...' suffix byte", inline=True)
comment(0xB87E, "Append to error message", inline=True)
comment(0xB881, "Continue until NUL", inline=True)
comment(0xB883, "Raise the constructed error", inline=True)
comment(0xB886, "Load current channel attribute", inline=True)
comment(0xB889, "Store channel attribute to RX buffer", inline=True)
comment(0xB88C, "Validate and look up channel", inline=True)
comment(0xB88F, "Test directory flag (bit 1)", inline=True)
comment(0xB891, "Not a directory: return OK", inline=True)
comment(0xB893, "Error code &A8", inline=True)
comment(0xB895, "Generate 'Is a dir.' error", inline=True)
comment(0xB8A8, "Save channel attribute", inline=True)
comment(0xB8A9, "Start scanning from FCB slot &20", inline=True)
comment(0xB8AB, "Load FCB station byte", inline=True)
comment(0xB8AE, "Zero: slot is free, use it", inline=True)
comment(0xB8B0, "Try next slot", inline=True)
comment(0xB8B1, "Past last FCB slot &2F?", inline=True)
comment(0xB8B3, "No: check next slot", inline=True)
comment(0xB8B5, "No free slot: discard saved attribute", inline=True)
comment(0xB8B6, "A=0: return failure (Z set)", inline=True)
comment(0xB8B8, "Return", inline=True)
comment(0xB8B9, "Restore channel attribute", inline=True)
comment(0xB8BA, "Store attribute in FCB slot", inline=True)
comment(0xB8BD, "A=0: clear value", inline=True)
comment(0xB8BF, "Clear FCB transfer count low", inline=True)
comment(0xB8C2, "Clear FCB transfer count mid", inline=True)
comment(0xB8C5, "Clear FCB transfer count high", inline=True)
comment(0xB8C8, "Load current station number", inline=True)
comment(0xB8CB, "Store station in FCB", inline=True)
comment(0xB8CE, "Load current network number", inline=True)
comment(0xB8D1, "Store network in FCB", inline=True)
comment(0xB8D4, "Get FCB slot index", inline=True)
comment(0xB8D5, "Save slot index", inline=True)
comment(0xB8D6, "Prepare subtraction", inline=True)
comment(0xB8D7, "Convert slot to channel index (0-&0F)", inline=True)
comment(0xB8D9, "X = channel index", inline=True)
comment(0xB8DA, "Restore A = FCB slot index", inline=True)
comment(0xB8DB, "Return; A=slot, X=channel, Z clear", inline=True)
comment(0xB8DC, "Save argument", inline=True)
comment(0xB8DD, "A=0: allocate any available slot", inline=True)
comment(0xB8DF, "Try to allocate an FCB slot", inline=True)
comment(0xB8E2, "Success: slot allocated", inline=True)
comment(0xB8E4, "Error code &C0", inline=True)
comment(0xB8E6, "Generate 'No more FCBs' error", inline=True)
comment(0xB8F6, "Restore argument", inline=True)
comment(0xB8F7, "Return", inline=True)
comment(0xB8F8, "C=0: close all matching channels", inline=True)
comment(0xB8F9, "Branch always to scan entry", inline=True)
comment(0xB8FC, "Start from FCB slot &10", inline=True)
comment(0xB8FE, "Previous FCB slot", inline=True)
comment(0xB8FF, "More slots to check", inline=True)
comment(0xB901, "All FCB slots processed, return", inline=True)
comment(0xB902, "Load channel flags for this slot", inline=True)
comment(0xB905, "Save flags in Y", inline=True)
comment(0xB906, "Test active flag (bit 1)", inline=True)
comment(0xB908, "Not active: check station match", inline=True)
comment(0xB90A, "V clear (close all): next slot", inline=True)
comment(0xB90C, "C clear: check station match", inline=True)
comment(0xB90E, "Restore original flags", inline=True)
comment(0xB90F, "Clear write-pending flag (bit 5)", inline=True)
comment(0xB911, "Update channel flags", inline=True)
comment(0xB914, "Next slot (V always set here)", inline=True)
comment(0xB916, "Check if channel belongs to station", inline=True)
comment(0xB919, "No match: skip to next slot", inline=True)
comment(0xB91B, "A=0: clear channel", inline=True)
comment(0xB91D, "Clear channel flags (close it)", inline=True)
comment(0xB920, "Clear network number", inline=True)
comment(0xB923, "Continue to next slot", inline=True)
comment(0xB925, "Load FCB station number", inline=True)
comment(0xB928, "Compare with current station", inline=True)
comment(0xB92B, "Different: Z=0, no match", inline=True)
comment(0xB92D, "Load FCB network number", inline=True)
comment(0xB930, "Compare with current network", inline=True)
comment(0xB933, "Return; Z=1 if match, Z=0 if not", inline=True)
comment(0xB934, "Load current FCB index", inline=True)
comment(0xB937, "Set V flag (first pass marker)", inline=True)
comment(0xB93A, "Next FCB slot", inline=True)
comment(0xB93B, "Past end of table (&10)?", inline=True)
comment(0xB93D, "No: continue checking", inline=True)
comment(0xB93F, "Wrap around to slot 0", inline=True)
comment(0xB941, "Back to starting slot?", inline=True)
comment(0xB944, "No: check this slot", inline=True)
comment(0xB946, "V clear (second pass): scan empties", inline=True)
comment(0xB948, "Clear V for second pass", inline=True)
comment(0xB949, "Continue scanning", inline=True)
comment(0xB94B, "Load FCB status flags", inline=True)
comment(0xB94E, "Shift bit 7 (in-use) into carry", inline=True)
comment(0xB94F, "Not in use: skip", inline=True)
comment(0xB951, "Test bit 2 (modified flag)", inline=True)
comment(0xB953, "Modified: check further conditions", inline=True)
comment(0xB955, "Adjust for following INX", inline=True)
comment(0xB956, "Next FCB slot", inline=True)
comment(0xB957, "Past end of table?", inline=True)
comment(0xB959, "No: continue", inline=True)
comment(0xB95B, "Wrap around to slot 0", inline=True)
comment(0xB95D, "Load FCB status flags", inline=True)
comment(0xB960, "Shift bit 7 into carry", inline=True)
comment(0xB961, "Not in use: continue scanning", inline=True)
comment(0xB963, "Set carry", inline=True)
comment(0xB964, "Restore original flags", inline=True)
comment(0xB965, "Save flags back (mark as found)", inline=True)
comment(0xB968, "Restore original FCB index", inline=True)
comment(0xB96B, "Return with found slot in X", inline=True)
comment(0xB96C, "V set (first pass): skip modified", inline=True)
comment(0xB96E, "Load FCB status flags", inline=True)
comment(0xB971, "Test bit 5 (offset pending)", inline=True)
comment(0xB973, "Bit 5 set: skip this slot", inline=True)
comment(0xB975, "Use this slot", inline=True)
comment(0xB977, "Initial pass count = 1", inline=True)
comment(0xB979, "Store pass counter", inline=True)
comment(0xB97C, "Y=0", inline=True)
comment(0xB97D, "Clear byte counter low", inline=True)
comment(0xB980, "Clear offset counter", inline=True)
comment(0xB983, "Clear transfer flag", inline=True)
comment(0xB986, "A=0", inline=True)
comment(0xB987, "Clear 3 counter bytes", inline=True)
comment(0xB989, "Clear counter byte", inline=True)
comment(0xB98C, "Next byte", inline=True)
comment(0xB98D, "Loop for indices 2, 1, 0", inline=True)
comment(0xB98F, "Store &FF as sentinel in xfer_sentinel_1", inline=True)
comment(0xB992, "Store &FF as sentinel in xfer_sentinel_2", inline=True)
comment(0xB995, "X=&CA: workspace offset", inline=True)
comment(0xB997, "Y=&10: page &10", inline=True)
comment(0xB999, "Return; X/Y point to &10CA", inline=True)
comment(0xB99A, "Verify workspace checksum integrity", inline=True)
comment(0xB99D, "Save current FCB index", inline=True)
comment(0xB9A0, "Load FCB status flags", inline=True)
comment(0xB9A3, "Shift bit 0 (active) into carry", inline=True)
comment(0xB9A4, "Not active: clear status and return", inline=True)
comment(0xB9A6, "Save current station low to stack", inline=True)
comment(0xB9A9, "Push station low", inline=True)
comment(0xB9AA, "Save current station high", inline=True)
comment(0xB9AD, "Push station high", inline=True)
comment(0xB9AE, "Load FCB station low", inline=True)
comment(0xB9B1, "Set as working station low", inline=True)
comment(0xB9B4, "Load FCB station high", inline=True)
comment(0xB9B7, "Set as working station high", inline=True)
comment(0xB9BA, "Reset transfer counters", inline=True)
comment(0xB9BD, "Set offset to &FF (no data yet)", inline=True)
comment(0xB9C0, "Set pass counter to 0 (flush mode)", inline=True)
comment(0xB9C3, "Reload FCB index", inline=True)
comment(0xB9C6, "Transfer to A", inline=True)
comment(0xB9C7, "Prepare addition", inline=True)
comment(0xB9C8, "Add &11 for buffer page offset", inline=True)
comment(0xB9CA, "Store buffer address high byte", inline=True)
comment(0xB9CD, "Load FCB status flags", inline=True)
comment(0xB9D0, "Test bit 5 (has saved offset)", inline=True)
comment(0xB9D2, "No offset: skip restore", inline=True)
comment(0xB9D4, "Load saved byte offset", inline=True)
comment(0xB9D7, "Restore offset counter", inline=True)
comment(0xB9DA, "Load FCB attribute reference", inline=True)
comment(0xB9DD, "Store as current reference", inline=True)
comment(0xB9E0, "Transfer to X", inline=True)
comment(0xB9E1, "Read saved receive attribute", inline=True)
comment(0xB9E4, "Push to stack", inline=True)
comment(0xB9E5, "Restore attribute to A", inline=True)
comment(0xB9E6, "Set attribute in receive buffer", inline=True)
comment(0xB9E8, "X=&CA: workspace offset", inline=True)
comment(0xB9EA, "Y=&10: page &10", inline=True)
comment(0xB9EC, "A=0: standard transfer mode", inline=True)
comment(0xB9EE, "Send data and receive response", inline=True)
comment(0xB9F1, "Reload FCB index", inline=True)
comment(0xB9F4, "Restore saved receive attribute", inline=True)
comment(0xB9F5, "Restore receive attribute", inline=True)
comment(0xB9F8, "Restore station high", inline=True)
comment(0xB9F9, "Store station high", inline=True)
comment(0xB9FC, "Restore station low", inline=True)
comment(0xB9FD, "Store station low", inline=True)
comment(0xBA00, "Mask &DC: clear bits 0, 1, 5", inline=True)
comment(0xBA02, "Clear active and offset flags", inline=True)
comment(0xBA05, "Update FCB status", inline=True)
comment(0xBA08, "Return", inline=True)
comment(0xBA09, "Copy 13 bytes (indices 0 to &0C)", inline=True)
comment(0xBA0B, "Load TX buffer byte", inline=True)
comment(0xBA0E, "Save to context buffer at &10D9", inline=True)
comment(0xBA11, "Load workspace byte from fs_load_addr", inline=True)
comment(0xBA13, "Save to stack", inline=True)
comment(0xBA14, "Next byte down", inline=True)
comment(0xBA15, "Loop for all 13 bytes", inline=True)
comment(0xBA17, "Y=0? (no FCB to process)", inline=True)
comment(0xBA19, "Non-zero: scan and process FCBs", inline=True)
comment(0xBA1B, "Y=0: skip to restore workspace", inline=True)
comment(0xBA1E, "Save flags", inline=True)
comment(0xBA1F, "X=&FF: start scanning from -1", inline=True)
comment(0xBA21, "Next FCB slot", inline=True)
comment(0xBA22, "Load FCB status flags", inline=True)
comment(0xBA25, "Bit 7 clear: not pending, skip", inline=True)
comment(0xBA27, "Shift bit 6 to bit 7", inline=True)
comment(0xBA28, "Bit 6 clear: skip", inline=True)
comment(0xBA2A, "Flush this FCB's pending data", inline=True)
comment(0xBA2D, "Pending marker &40", inline=True)
comment(0xBA2F, "Mark FCB as pending-only", inline=True)
comment(0xBA32, "Save flags", inline=True)
comment(0xBA33, "Find next available FCB slot", inline=True)
comment(0xBA36, "Restore flags", inline=True)
comment(0xBA37, "Load current channel attribute", inline=True)
comment(0xBA3A, "Store as current reference", inline=True)
comment(0xBA3D, "Save attribute", inline=True)
comment(0xBA3E, "Prepare attribute-to-channel conversion", inline=True)
comment(0xBA3F, "Convert attribute (&20+) to channel index", inline=True)
comment(0xBA41, "Y = attribute index", inline=True)
comment(0xBA42, "Load station for this attribute", inline=True)
comment(0xBA45, "Store station in TX buffer", inline=True)
comment(0xBA48, "Restore attribute", inline=True)
comment(0xBA49, "Store attribute in FCB slot", inline=True)
comment(0xBA4C, "Load working station low", inline=True)
comment(0xBA4F, "Store in TX buffer", inline=True)
comment(0xBA52, "Load working station high", inline=True)
comment(0xBA55, "Store in TX buffer", inline=True)
comment(0xBA58, "Get FCB slot index", inline=True)
comment(0xBA59, "Prepare addition", inline=True)
comment(0xBA5A, "Add &11 for buffer page offset", inline=True)
comment(0xBA5C, "Store buffer address high byte", inline=True)
comment(0xBA5F, "Restore flags", inline=True)
comment(0xBA60, "V clear: skip directory request", inline=True)
comment(0xBA62, "Command byte = 0", inline=True)
comment(0xBA65, "Reset transfer counters", inline=True)
comment(0xBA68, "Read saved receive attribute", inline=True)
comment(0xBA6B, "Function code &0D", inline=True)
comment(0xBA6C, "Load current reference", inline=True)
comment(0xBA6F, "Set in receive buffer", inline=True)
comment(0xBA71, "Y=&10: page &10", inline=True)
comment(0xBA73, "A=2: transfer mode 2", inline=True)
comment(0xBA75, "Send and receive data", inline=True)
comment(0xBA78, "Restore receive attribute", inline=True)
comment(0xBA79, "Restore receive attribute", inline=True)
comment(0xBA7C, "Reload FCB index", inline=True)
comment(0xBA7F, "Load pass counter", inline=True)
comment(0xBA82, "Non-zero: data received, calc offset", inline=True)
comment(0xBA84, "Load offset counter", inline=True)
comment(0xBA87, "Zero: no data received at all", inline=True)
comment(0xBA89, "Load offset counter", inline=True)
comment(0xBA8C, "Negate (ones complement)", inline=True)
comment(0xBA8E, "Clear carry for add", inline=True)
comment(0xBA8F, "Complete twos complement negation", inline=True)
comment(0xBA91, "Store negated offset in FCB", inline=True)
comment(0xBA94, "Set bit 5 (has saved offset)", inline=True)
comment(0xBA96, "Add to FCB flags", inline=True)
comment(0xBA99, "Update FCB status", inline=True)
comment(0xBA9C, "Load buffer address high byte", inline=True)
comment(0xBA9F, "Set pointer high byte", inline=True)
comment(0xBAA1, "A=0: pointer low byte and clear val", inline=True)
comment(0xBAA3, "Set pointer low byte", inline=True)
comment(0xBAA5, "Load negated offset (start of clear)", inline=True)
comment(0xBAA8, "Clear buffer byte", inline=True)
comment(0xBAAA, "Next byte", inline=True)
comment(0xBAAB, "Loop until page boundary", inline=True)
comment(0xBAAD, "Set bit 1 (active flag)", inline=True)
comment(0xBAAF, "Add active flag to status", inline=True)
comment(0xBAB2, "Update FCB status", inline=True)
comment(0xBAB5, "Y=0: start restoring workspace", inline=True)
comment(0xBAB7, "Restore workspace byte from stack", inline=True)
comment(0xBAB8, "Store to fs_load_addr workspace", inline=True)
comment(0xBABB, "Next byte", inline=True)
comment(0xBABC, "Restored all 13 bytes?", inline=True)
comment(0xBABE, "No: continue restoring", inline=True)
comment(0xBAC0, "Copy 13 bytes (indices 0 to &0C)", inline=True)
comment(0xBAC2, "Load saved catalog byte from &10D9", inline=True)
comment(0xBAC5, "Restore to TX buffer", inline=True)
comment(0xBAC8, "Next byte down", inline=True)
comment(0xBAC9, "Loop for all bytes", inline=True)
comment(0xBACB, "Return", inline=True)
comment(0xBACC, "Save current context first", inline=True)
comment(0xBACF, "X=&FF: start scanning from -1", inline=True)
comment(0xBAD1, "Load channel attribute to match", inline=True)
comment(0xBAD4, "Next FCB slot", inline=True)
comment(0xBAD5, "Past end of table (&10)?", inline=True)
comment(0xBAD7, "No: check this slot", inline=True)
comment(0xBAD9, "Load channel attribute", inline=True)
comment(0xBADC, "Convert to channel index", inline=True)
comment(0xBADF, "Load station for this channel", inline=True)
comment(0xBAE2, "Store as match target station high", inline=True)
comment(0xBAE5, "Load port for this channel", inline=True)
comment(0xBAE8, "Store as match target station low", inline=True)
comment(0xBAEB, "Save context and rescan from start", inline=True)
comment(0xBAEE, "Load FCB status flags", inline=True)
comment(0xBAF1, "Test active flag (bit 1)", inline=True)
comment(0xBAF3, "Not active: skip to next", inline=True)
comment(0xBAF5, "Get attribute to match", inline=True)
comment(0xBAF6, "Compare with FCB attribute ref", inline=True)
comment(0xBAF9, "No attribute match: skip", inline=True)
comment(0xBAFB, "Save matching FCB index", inline=True)
comment(0xBAFE, "Save flags from attribute compare", inline=True)
comment(0xBAFF, "Prepare subtraction", inline=True)
comment(0xBB00, "Convert attribute to channel index", inline=True)
comment(0xBB02, "Restore flags from attribute compare", inline=True)
comment(0xBB03, "Y = channel index", inline=True)
comment(0xBB04, "Reload FCB index", inline=True)
comment(0xBB07, "Load channel station byte", inline=True)
comment(0xBB0A, "Compare with FCB station", inline=True)
comment(0xBB0D, "Station mismatch: try next", inline=True)
comment(0xBB0F, "Load channel network byte", inline=True)
comment(0xBB12, "Compare with FCB network", inline=True)
comment(0xBB15, "Network mismatch: try next", inline=True)
comment(0xBB17, "Load FCB flags", inline=True)
comment(0xBB1A, "Bit 7 clear: no pending flush", inline=True)
comment(0xBB1C, "Clear pending flag (bit 7)", inline=True)
comment(0xBB1E, "Update FCB status", inline=True)
comment(0xBB21, "Find new open FCB slot", inline=True)
comment(0xBB24, "Reload FCB flags", inline=True)
comment(0xBB27, "Test bit 5 (has offset data)", inline=True)
comment(0xBB29, "Return; Z=1 no offset, Z=0 has data", inline=True)
comment(0xBB2A, "Increment byte count low", inline=True)
comment(0xBB2D, "No overflow: done", inline=True)
comment(0xBB2F, "Increment byte count mid", inline=True)
comment(0xBB32, "No overflow: done", inline=True)
comment(0xBB34, "Increment byte count high", inline=True)
comment(0xBB37, "Return", inline=True)
comment(0xBB67, "Return", inline=True)
comment(0xBB68, "Save channel attribute", inline=True)
comment(0xBB6B, "Save caller's X", inline=True)
comment(0xBB6C, "Push X", inline=True)
comment(0xBB6D, "Store result and check not directory", inline=True)
comment(0xBB70, "Load channel flags", inline=True)
comment(0xBB73, "Test write-only flag (bit 5)", inline=True)
comment(0xBB75, "Not write-only: proceed with read", inline=True)
comment(0xBB77, "Error code &D4", inline=True)
comment(0xBB79, "Generate 'Write only' error", inline=True)
comment(0xBB87, "Clear V (first-pass matching)", inline=True)
comment(0xBB88, "Find FCB matching this channel", inline=True)
comment(0xBB8B, "No offset: read byte from buffer", inline=True)
comment(0xBB8D, "Load byte count for matching FCB", inline=True)
comment(0xBB90, "Compare with buffer offset limit", inline=True)
comment(0xBB93, "Below offset: data available", inline=True)
comment(0xBB95, "Load channel flags for FCB", inline=True)
comment(0xBB98, "Transfer to X for testing", inline=True)
comment(0xBB99, "Test bit 6 (EOF already signalled)", inline=True)
comment(0xBB9B, "EOF already set: raise error", inline=True)
comment(0xBB9D, "Restore flags", inline=True)
comment(0xBB9E, "Set EOF flag (bit 6)", inline=True)
comment(0xBBA0, "Update channel flags with EOF", inline=True)
comment(0xBBA3, "A=0: clear receive attribute", inline=True)
comment(0xBBA5, "Clear receive attribute (A=0)", inline=True)
comment(0xBBA8, "Restore caller's X", inline=True)
comment(0xBBA9, "X restored", inline=True)
comment(0xBBAA, "A=&FE: EOF marker byte", inline=True)
comment(0xBBAC, "Restore channel attribute", inline=True)
comment(0xBBAF, "C=1: end of file", inline=True)
comment(0xBBB0, "Return", inline=True)
comment(0xBBB1, "Error code &DF", inline=True)
comment(0xBBB3, "Generate 'End of file' error", inline=True)
comment(0xBBC2, "Load current byte count (= offset)", inline=True)
comment(0xBBC5, "Save byte count", inline=True)
comment(0xBBC6, "Get FCB slot index", inline=True)
comment(0xBBC7, "X = FCB slot for byte count inc", inline=True)
comment(0xBBC8, "A=0: clear receive attribute", inline=True)
comment(0xBBCA, "Clear receive attribute (A=0)", inline=True)
comment(0xBBCD, "Increment byte count for this FCB", inline=True)
comment(0xBBD0, "Restore byte count (= buffer offset)", inline=True)
comment(0xBBD1, "Y = offset into data buffer", inline=True)
comment(0xBBD2, "Load current FCB index", inline=True)
comment(0xBBD5, "Prepare addition", inline=True)
comment(0xBBD6, "Add &11 for buffer page offset", inline=True)
comment(0xBBD8, "Set pointer high byte", inline=True)
comment(0xBBDA, "A=0: pointer low byte", inline=True)
comment(0xBBDC, "Set pointer low byte", inline=True)
comment(0xBBDE, "Restore caller's X", inline=True)
comment(0xBBDF, "X restored", inline=True)
comment(0xBBE0, "Read data byte from buffer", inline=True)
comment(0xBBE2, "Restore channel attribute", inline=True)
comment(0xBBE5, "C=0: byte read successfully", inline=True)
comment(0xBBE6, "Return; A = data byte", inline=True)
comment(0xBBE7, "Save channel attribute", inline=True)
comment(0xBBEA, "Save data byte", inline=True)
comment(0xBBEB, "Y = data byte", inline=True)
comment(0xBBEC, "Save caller's X", inline=True)
comment(0xBBED, "Push X", inline=True)
comment(0xBBEE, "Restore data byte to A", inline=True)
comment(0xBBEF, "Push data byte for later", inline=True)
comment(0xBBF0, "Save data byte in workspace", inline=True)
comment(0xBBF3, "Store result and check not directory", inline=True)
comment(0xBBF6, "Load channel flags", inline=True)
comment(0xBBF9, "Bit 7 set: channel open, proceed", inline=True)
comment(0xBBFB, "Error &C1: Not open for update", inline=True)
comment(0xBBFD, "Raise error with inline string", inline=True)
comment(0xBC14, "Test write flag (bit 5)", inline=True)
comment(0xBC16, "Not write-capable: use buffer path", inline=True)
comment(0xBC18, "Load reply port for this channel", inline=True)
comment(0xBC1B, "Restore data byte", inline=True)
comment(0xBC1C, "Send byte directly to server", inline=True)
comment(0xBC1F, "Update byte count and return", inline=True)
comment(0xBC22, "Set V flag (alternate match mode)", inline=True)
comment(0xBC25, "Find matching FCB for channel", inline=True)
comment(0xBC28, "Load byte count for FCB", inline=True)
comment(0xBC2B, "Buffer full (&FF bytes)?", inline=True)
comment(0xBC2D, "No: store byte in buffer", inline=True)
comment(0xBC2F, "Save X", inline=True)
comment(0xBC32, "Push Y", inline=True)
comment(0xBC35, "Below offset: skip offset update", inline=True)
comment(0xBC37, "Carry set from BCS/BCC above", inline=True)
comment(0xBC39, "Update buffer offset in FCB", inline=True)
comment(0xBC3C, "Non-zero: keep offset flag", inline=True)
comment(0xBC3E, "Mask &DF: clear bit 5", inline=True)
comment(0xBC40, "Clear offset flag", inline=True)
comment(0xBC43, "Update FCB status", inline=True)
comment(0xBC46, "Set bit 0 (dirty/active)", inline=True)
comment(0xBC48, "Add to FCB flags", inline=True)
comment(0xBC4B, "Update FCB status", inline=True)
comment(0xBC4E, "Load byte count (= write position)", inline=True)
comment(0xBC51, "Save count", inline=True)
comment(0xBC52, "Get FCB slot index", inline=True)
comment(0xBC53, "X = FCB slot", inline=True)
comment(0xBC54, "Restore byte count", inline=True)
comment(0xBC55, "Y = buffer write offset", inline=True)
comment(0xBC56, "Load current FCB index", inline=True)
comment(0xBC59, "Prepare addition", inline=True)
comment(0xBC5A, "Add &11 for buffer page offset", inline=True)
comment(0xBC5C, "Set pointer high byte", inline=True)
comment(0xBC5E, "A=0: pointer low byte", inline=True)
comment(0xBC60, "Set pointer low byte", inline=True)
comment(0xBC62, "Restore data byte", inline=True)
comment(0xBC63, "Write data byte to buffer", inline=True)
comment(0xBC65, "Increment byte count for this FCB", inline=True)
comment(0xBC68, "A=0: clear receive attribute", inline=True)
comment(0xBC6A, "Clear receive attribute (A=0)", inline=True)
comment(0xBC6D, "Restore caller's X", inline=True)
comment(0xBC6E, "X restored", inline=True)
comment(0xBC6F, "Discard saved data byte", inline=True)
comment(0xBC70, "Restore channel attribute", inline=True)
comment(0xBC73, "Return", inline=True)
comment(0xBC74, "Save A", inline=True)
comment(0xBC75, "Save X", inline=True)
comment(0xBC77, "Read FCB slot attribute byte", inline=True)
comment(0xBC7A, "Non-zero: station known -> "
    "store_station_and_flush", inline=True)
comment(0xBC7C, "Save attribute byte (saved-station-test path)",
    inline=True)
comment(0xBC7D, "Save X again", inline=True)
comment(0xBC7E, "Save Y", inline=True)
comment(0xBCBA, "Restore A", inline=True)
comment(0xBCBB, "Return", inline=True)
comment(0xBCBC, "Store reply port", inline=True)
comment(0xBCBF, "Store data byte", inline=True)
comment(0xBCC2, "Save Y", inline=True)
comment(0xBCC3, "Push Y to stack", inline=True)
comment(0xBCC4, "Save X", inline=True)
comment(0xBCC5, "Push X to stack", inline=True)
comment(0xBCC6, "Function code &90", inline=True)
comment(0xBCC8, "Store in send buffer", inline=True)
comment(0xBCCB, "Initialise TX control block", inline=True)
comment(0xBCCE, "TX start address low = &DC", inline=True)
comment(0xBCD0, "Set TX start in control block", inline=True)
comment(0xBCD2, "TX end address low = &E0", inline=True)
comment(0xBCD4, "Set TX end in control block", inline=True)
comment(0xBCD6, "Expected reply port = 9", inline=True)
comment(0xBCD8, "Store reply port in buffer", inline=True)
comment(0xBCDB, "TX control = &C0", inline=True)
comment(0xBCDD, "Y=0: no timeout", inline=True)
comment(0xBCDF, "Load reply port for addressing", inline=True)
comment(0xBCE2, "Send packet to server", inline=True)
comment(0xBCE5, "Load reply status", inline=True)
comment(0xBCE8, "Zero: success", inline=True)
comment(0xBCEA, "Store error code", inline=True)
comment(0xBCED, "X=0: copy index", inline=True)
comment(0xBCEF, "Load error message byte", inline=True)
comment(0xBCF2, "Copy to error block", inline=True)
comment(0xBCF5, "Is it CR (end of message)?", inline=True)
comment(0xBCF7, "Yes: terminate string", inline=True)
comment(0xBCF9, "Next byte", inline=True)
comment(0xBCFA, "Continue copying error message", inline=True)
comment(0xBCFC, "NUL terminator", inline=True)
comment(0xBCFE, "Terminate error string in block", inline=True)
comment(0xBD01, "Back up position for error check", inline=True)
comment(0xBD02, "Process and raise network error", inline=True)
comment(0xBD05, "Load channel attribute index", inline=True)
comment(0xBD08, "Load station number for channel", inline=True)
comment(0xBD0B, "Toggle bit 0 (alternate station)", inline=True)
comment(0xBD0D, "Update station number", inline=True)
comment(0xBD10, "Restore X", inline=True)
comment(0xBD11, "X restored", inline=True)
comment(0xBD12, "Restore Y", inline=True)
comment(0xBD13, "Y restored", inline=True)
comment(0xBD14, "Return", inline=True)
comment(0xBD15, "Set up FS options pointer", inline=True)
comment(0xBD18, "Set up transfer workspace and return", inline=True)
comment(0xBD1B, "Y=&0A: receive attribute offset", inline=True)
comment(0xBD1D, "Read byte from receive buffer", inline=True)
comment(0xBD1F, "Return", inline=True)
comment(0xBD20, "Y=&0A: receive attribute offset", inline=True)
comment(0xBD22, "Store byte to receive buffer", inline=True)
comment(0xBD24, "Return", inline=True)
comment(0xBD44, "21 bytes to push (0-&14)", inline=True)
comment(0xBD4D, "Set up buffer pointer and parse args", inline=True)
comment(0xBD54, "Skip header if 16-byte aligned", inline=True)
comment(0xBD56, "Print column header for offset start", inline=True)
# &BD59..&BD77 inlines covered by deliberate review block (loop_dump_line).
comment(0xBD86, "Non-zero: header already current", inline=True)
comment(0xBD9B, "Add 16 to lowest address byte", inline=True)
comment(0xBDAC, "Print address/data separator", inline=True)
comment(0xBDB4, "X = bytes read (counter for display)", inline=True)
comment(0xBDC0, "Decrement remaining data bytes", inline=True)
# &BE37..&BE41 inlines covered by deliberate review block (print_hex_and_space).
comment(0xBE42, "Save command line offset to X", inline=True)
comment(0xBE43, "X tracks current position", inline=True)
comment(0xBE61, "Yes: is a decimal digit", inline=True)
comment(0xBE65, "Map 'A'-'F' → &FA-&FF (C=0 here)", inline=True)
comment(0xBE67, "Carry set: char > 'F', error", inline=True)
comment(0xBE69, "Below &FA? (i.e. was < 'A')", inline=True)
comment(0xBE71, "Preserve on stack", inline=True)
comment(0xBE72, "4 bits to shift in", inline=True)
comment(0xBE77, "Transfer carry bit to flags via stack", inline=True)
comment(0xBE78, "C = bit shifted out of prev iter", inline=True)
comment(0xBE7B, "Rotate left through carry", inline=True)
comment(0xBE86, "C = overflow bit", inline=True)
comment(0xBE87, "Overflow: address too large", inline=True)
comment(0xBE9C, "Close open file before error", inline=True)
comment(0xBEAB, "X+1: first byte of buffer", inline=True)
comment(0xBEAE, "Buffer is on stack in page 1", inline=True)
comment(0xBEB2, "Parse start offset from command line", inline=True)
comment(0xBEB7, "A = command line offset after parse", inline=True)
comment(0xBEBD, "A=2: read file extent (length)", inline=True)
comment(0xBEC7, "Compare with start offset byte", inline=True)
comment(0xBECC, "More bytes to compare", inline=True)
comment(0xBECE, "All equal: start = length, within file", inline=True)
comment(0xBED0, "Length < start: outside file", inline=True)
comment(0xBED2, "Y=&FF: length > start, flag for later", inline=True)
comment(0xBED4, "Continue to copy start address", inline=True)
comment(0xBEEB, "Load start address byte from buffer", inline=True)
comment(0xBEF9, "A=1: write file pointer", inline=True)
comment(0xBEFB, "OSARGS: set file pointer", inline=True)
comment(0xBF06, "Copy 2 bytes: os_text_ptr to buffer", inline=True)
comment(0xBF19, "Start at OSFILE +2 (load addr byte 0)", inline=True)
comment(0xBF1E, "Continue decrement", inline=True)
comment(0xBF28, "Y=6 after loop exit", inline=True)
comment(0xBF29, "Y=4: check from buf[4] downward", inline=True)
comment(0xBF2E, "No: valid load address, use it", inline=True)
comment(0xBF33, "Clear all 4 bytes", inline=True)
comment(0xBF3C, "Continue to compute display address", inline=True)
comment(0xBF43, "Invalid: close file before error", inline=True)
comment(0xBF5A, "Add start offset byte", inline=True)
comment(0xBF64, "Point past end of address area", inline=True)
comment(0xBF79, "A=filename offset from Y", inline=True)
comment(0xBF7B, "Add text pointer low byte", inline=True)
comment(0xBF7D, "Save filename address low", inline=True)
comment(0xBF7E, "X=filename address low (for OSFIND)", inline=True)
comment(0xBF81, "Add text pointer high byte + carry", inline=True)
comment(0xBF91, "Raise 'Not found' error", inline=True)
comment(0xBF9E, "Restore text pointer high from stack", inline=True)
comment(0xBFA1, "Restore text pointer low from stack", inline=True)
comment(0xBFAB, "Yes: finished parsing filename", inline=True)
comment(0xBFB8, "Restore caller flags", inline=True)
comment(0xBFBA, "JSR+fall-through: 8+8=16 INXs total", inline=True)
comment(0xBFBD, "JSR+fall-through: 4+4=8 INXs", inline=True)
comment(0xBFC0, "X += 4", inline=True)
comment(0xBFC4, "Return", inline=True)
comment(0xBFC7, "Padding; next byte is reloc_p5_src", inline=True)


# === Backfilled from 4.18 via fantasm backfill (threshold 5, post-issue-10 anchored-only map) ===
# 1386 comments propagated
comment(0x9100, "Syn 2: *I Am (login)", inline=True)
comment(0x912D, "Syn 3: *Delete, *FS, *Remove", inline=True)
comment(0x9184, "Syn 7 continued: new password", inline=True)
comment(0x91AA, "Syn 9: *Access", inline=True)
comment(0x91C5, "Null terminator", inline=True)
comment(0x91C6, "Syn 10: *Rename", inline=True)
comment(0x91EC, "Null terminator", inline=True)
comment(0x91ED, "Idx 0: 'opt_dir' (offset -2 variant for *Dir's "
    "INY-twice walker)", inline=True)
comment(0x91EE, "Idx 1: &FF = no syntax string for this index",
    inline=True)
comment(0x91EF, "Idx 2: \\\"(<stn.id.>) <user id.>...\\\"", inline=True)
comment(0x91F0, "Idx 3: \\\"<object>\\\"", inline=True)
comment(0x91F1, "Idx 4: \\\"<filename> (<offset>...)\\\"", inline=True)
comment(0x91F2, "Idx 5: '<dir>' (offset 0x60 = syn_dir)", inline=True)
comment(0x91F3, "Idx 6: continued <dir> string region", inline=True)
comment(0x91F4, "Idx 7: \\\"(:<CR>) <password>...\\\"", inline=True)
comment(0x91F5, "Idx 8: \\\"(<stn.id.>|<ps type>)\\\"", inline=True)
comment(0x91F6, "Idx 9: \\\"<object> (L)(W)(R)...\\\"", inline=True)
comment(0x91F7, "Idx 10: '<filename> <new filename>' "
    "(syn_rename)", inline=True)
comment(0x91F8, "Idx 11: \\\"(<stn. id.>)\\\"", inline=True)
comment(0x94C5, "Copy 'Rename ' to TX buffer", inline=True)
comment(0x986B, "Y=&0E", inline=True)
comment(0x99C5, "Store return address low", inline=True)
comment(0x99C8, "Store return address high", inline=True)
comment(0x99CA, "X=0: error text index", inline=True)
comment(0x99CF, "Copy error number to A", inline=True)
comment(0x99D0, "Push error number on stack", inline=True)
comment(0x99D1, "Y=0: inline string index", inline=True)
comment(0x99D7, "Advance string index", inline=True)
comment(0x99DA, "Store byte in error block", inline=True)
comment(0x99E2, "Non-zero: network returned an error", inline=True)
comment(0x99E4, "Pop saved error number", inline=True)
comment(0x99E5, "Was it &DE (file server error)?", inline=True)
comment(0x99E7, "Yes: append error number and trigger BRK", inline=True)
comment(0x99E9, "Jump to BRK via error block", inline=True)
comment(0x99EC, "Store error code in workspace", inline=True)
comment(0x99EF, "Push error code", inline=True)
comment(0x99F0, "Save X (error text index)", inline=True)
comment(0x99F1, "Push X", inline=True)
comment(0x99F2, "Read receive attribute byte", inline=True)
comment(0x99F5, "Save to fs_load_addr as spool handle", inline=True)
comment(0x99F7, "A=0: clear error code in RX buffer", inline=True)
comment(0x99F9, "Zero the error code byte in buffer", inline=True)
comment(0x99FB, "A=&C6: OSBYTE read spool handle", inline=True)
comment(0x99FD, "Read current spool file handle", inline=True)
comment(0x9A00, "Compare Y result with saved handle", inline=True)
comment(0x9A02, "Match: close the spool file", inline=True)
comment(0x9A04, "Compare X result with saved handle", inline=True)
comment(0x9A06, "No match: skip spool close", inline=True)
comment(0x9A08, "Push A (preserved)", inline=True)
comment(0x9A09, "A=&C6: disable spool with OSBYTE", inline=True)
comment(0x9A0B, "ALWAYS branch to close spool", inline=True)
comment(0x9A14, "A=0: close file", inline=True)
comment(0x9A16, "Close the spool/exec file", inline=True)
comment(0x9A19, "Pull saved X (error text index)", inline=True)
comment(0x9A1A, "Restore X", inline=True)
comment(0x9A1B, "Y=&0A: lookup index for 'on channel'", inline=True)
comment(0x9A1D, "Load message offset from lookup table", inline=True)
comment(0x9A20, "Transfer offset to Y", inline=True)
comment(0x9A21, "Load error message byte", inline=True)
comment(0x9A24, "Append to error text buffer", inline=True)
comment(0x9A27, "Null terminator: done copying", inline=True)
comment(0x9A29, "Advance error text index", inline=True)
comment(0x9A2A, "Advance message index", inline=True)
comment(0x9A2B, "Loop until full message copied", inline=True)
comment(0x9A2D, "Save error text end position", inline=True)
comment(0x9A2F, "Pull saved error number", inline=True)
comment(0x9A30, "Append ' nnn' error number suffix", inline=True)
comment(0x9A33, "A=0: null terminator", inline=True)
comment(0x9A35, "Terminate error text string", inline=True)
comment(0x9A38, "ALWAYS branch to trigger BRK error", inline=True)
comment(0x9A3A, "A=' ': space separator", inline=True)
comment(0x9A3C, "Append space to error text", inline=True)
comment(0x9A3F, "Advance error text index", inline=True)
comment(0x9A40, "Save position for number formatting", inline=True)
comment(0x9A42, "Y=3: offset to network number in TX CB", inline=True)
comment(0x9A44, "Load network number", inline=True)
comment(0x9A46, "Zero: skip network part (local)", inline=True)
comment(0x9A48, "Append network number as decimal", inline=True)
comment(0x9A4B, "Reload error text position", inline=True)
comment(0x9A4D, "A='.': dot separator", inline=True)
comment(0x9A4F, "Append dot to error text", inline=True)
comment(0x9A52, "Advance past dot", inline=True)
comment(0x9A54, "Y=2: offset to station number in TX CB", inline=True)
comment(0x9A56, "Load station number", inline=True)
comment(0x9A58, "Append station number as decimal", inline=True)
comment(0x9A5B, "Reload error text position", inline=True)
comment(0x9A5D, "Return", inline=True)
comment(0x9A5E, "Save number in Y", inline=True)
comment(0x9A5F, "A=' ': space prefix", inline=True)
comment(0x9A61, "Load current error text position", inline=True)
comment(0x9A63, "Append space to error text", inline=True)
comment(0x9A66, "Advance position past space", inline=True)
comment(0x9A68, "Restore number to A", inline=True)
comment(0x9A69, "Save number in Y for division", inline=True)
comment(0x9A6A, "Set V: suppress leading zeros", inline=True)
comment(0x9A6D, "A=100: hundreds digit divisor", inline=True)
comment(0x9A6F, "Extract and append hundreds digit", inline=True)
comment(0x9A72, "A=10: tens digit divisor", inline=True)
comment(0x9A74, "Extract and append tens digit", inline=True)
comment(0x9A77, "A=1: units digit (remainder)", inline=True)
comment(0x9A79, "Clear V: always print units digit", inline=True)
comment(0x9A7A, "Store divisor", inline=True)
comment(0x9A7C, "Copy number to A for division", inline=True)
comment(0x9A7D, "X='0'-1: digit counter (ASCII offset)", inline=True)
comment(0x9A7F, "Save V flag (leading zero suppression)", inline=True)
comment(0x9A80, "Set carry for subtraction", inline=True)
comment(0x9A81, "Increment digit counter", inline=True)
comment(0x9A82, "Subtract divisor", inline=True)
comment(0x9A84, "Not negative yet: continue counting", inline=True)
comment(0x9A86, "Add back divisor (restore remainder)", inline=True)
comment(0x9A88, "Restore V flag", inline=True)
comment(0x9A89, "Save remainder back to Y", inline=True)
comment(0x9A8A, "Digit counter to A (ASCII digit)", inline=True)
comment(0x9A8B, "Is digit '0'?", inline=True)
comment(0x9A8D, "Non-zero: always print", inline=True)
comment(0x9A8F, "V set (suppress leading zeros): skip", inline=True)
comment(0x9A91, "Clear V: first non-zero digit seen", inline=True)
comment(0x9A92, "Load current text position", inline=True)
comment(0x9A94, "Store ASCII digit in error text", inline=True)
comment(0x9A97, "Advance text position", inline=True)
comment(0x9A99, "Return", inline=True)
comment(0x9AB2, "Null terminator", inline=True)
comment(0x9AB3, "Error &A1: Net error", inline=True)
comment(0x9ABD, "Null terminator", inline=True)
comment(0x9ABE, "Error &A2: Station", inline=True)
comment(0x9AD0, "Null terminator", inline=True)
comment(0x9AD1, "Error &11: Escape", inline=True)
comment(0x9AD9, "Error &CB: Bad option", inline=True)
comment(0x9AE4, "Null terminator + Error &A5: No reply from station",
    inline=True)
comment(0x9AE6, "err_no_reply = &A5 message body", inline=True)
comment(0x9AFB, "Null terminator", inline=True)
comment(0x9AFC, "Suffix string (offset &56 in lookup)", inline=True)
comment(0x9B0A, "Null terminator", inline=True)
comment(0x9B0B, "Suffix: \\\" on channel\\\"", inline=True)
comment(0x9B16, "Null terminator", inline=True)
comment(0x9B17, "Suffix: \\\" not present\\\"", inline=True)
comment(0x9B23, "Null terminator", inline=True)
comment(0x9B24, "X=&C0: TX control block base (low)", inline=True)
comment(0x9B26, "Set TX pointer low", inline=True)
comment(0x9B28, "X=0: TX control block base (high)", inline=True)
comment(0x9B2A, "Set TX pointer high (page 0)", inline=True)
comment(0x9B2C, "Load retry count from workspace", inline=True)
comment(0x9B2F, "Non-zero: use configured retry count", inline=True)
comment(0x9B31, "A=&FF: default retry count (255)", inline=True)
comment(0x9B33, "Y=&60: timeout value", inline=True)
comment(0x9B35, "Push retry count", inline=True)
comment(0x9B36, "A=&60: copy timeout to A", inline=True)
comment(0x9B37, "Push timeout", inline=True)
comment(0x9B38, "X=0: TX pointer index", inline=True)
comment(0x9B3A, "Load first byte of TX control block", inline=True)
comment(0x9B3C, "Restore control byte (overwritten by result code on retry)", inline=True)
comment(0x9B3E, "Push control byte", inline=True)
comment(0x9B3F, "Poll ADLC until line idle", inline=True)
comment(0x9B42, "Bit 6 (error flag) into N", inline=True)
comment(0x9B43, "N=0 (bit 6 clear): success", inline=True)
comment(0x9B45, "Shift away error flag, keep error type", inline=True)
comment(0x9B46, "Z=1 (no type bits): fatal; Z=0: retryable", inline=True)
comment(0x9B48, "Check for escape condition", inline=True)
comment(0x9B4B, "Pull control byte", inline=True)
comment(0x9B4C, "Restore to X", inline=True)
comment(0x9B4D, "Pull timeout", inline=True)
comment(0x9B4E, "Restore to Y", inline=True)
comment(0x9B4F, "Pull retry count", inline=True)
comment(0x9B50, "Zero retries remaining: try alternate", inline=True)
comment(0x9B52, "Decrement retry counter", inline=True)
comment(0x9B54, "Push updated retry count", inline=True)
comment(0x9B55, "Copy timeout to A", inline=True)
comment(0x9B56, "Push timeout for delay loop", inline=True)
comment(0x9B57, "Copy control byte to A", inline=True)
comment(0x9B58, "Inner delay: decrement X", inline=True)
comment(0x9B59, "Loop until X=0", inline=True)
comment(0x9B5B, "Decrement outer counter Y", inline=True)
comment(0x9B5C, "Loop until Y=0", inline=True)
comment(0x9B5E, "ALWAYS branch: retry transmission", inline=True)
comment(0x9B60, "Compare retry count with alternate", inline=True)
comment(0x9B63, "Different: go to error handling", inline=True)
comment(0x9B65, "A=&80: set escapable flag", inline=True)
comment(0x9B67, "Mark as escapable for second phase", inline=True)
comment(0x9B69, "ALWAYS branch: retry with escapable", inline=True)
comment(0x9B6B, "Result code to X", inline=True)
comment(0x9B6C, "Jump to classify reply and return", inline=True)
comment(0x9B6F, "Pull control byte", inline=True)
comment(0x9B70, "Pull timeout", inline=True)
comment(0x9B71, "Pull retry count", inline=True)
comment(0x9B72, "Clear escapable flag and return", inline=True)
comment(0x9B75, "Offset 0: ctrl = &88 (immediate TX)", inline=True)
comment(0x9B76, "Offset 1: port = &00 (immediate op)", inline=True)
comment(0x9B77, "Offset 2: &FD skip (preserve dest stn)", inline=True)
comment(0x9B78, "Offset 3: &FD skip (preserve dest net)", inline=True)
comment(0x9B79, "Offset 4: buf start lo (&3A) -> &0D3A", inline=True)
comment(0x9B7A, "Offset 5: buf start hi (&0D) -> &0D3A", inline=True)
comment(0x9B7B, "Offset 6: extended-addr fill (&FF)", inline=True)
comment(0x9B7C, "Offset 7: extended-addr fill (&FF)", inline=True)
comment(0x9B7D, "Offset 8: buf end lo (&3E) -> &0D3E", inline=True)
comment(0x9B7E, "Offset 9: buf end hi (&0D) -> &0D3E", inline=True)
comment(0x9B7F, "Offset 10: extended-addr fill (&FF)", inline=True)
comment(0x9B80, "Offset 11: extended-addr fill (&FF)", inline=True)
comment(0x9B81, "Y=&C0: TX control block base (low)", inline=True)
comment(0x9B83, "Set TX pointer low byte", inline=True)
comment(0x9B85, "Y=0: TX control block base (high)", inline=True)
comment(0x9B87, "Set TX pointer high byte", inline=True)
comment(0x9B89, "Y=&0B: 12 bytes to process (0-11)", inline=True)
comment(0x9B8B, "Load template byte for this offset", inline=True)
comment(0x9B8E, "Is it &FD (skip marker)?", inline=True)
comment(0x9B90, "Yes: skip this offset, don't modify", inline=True)
comment(0x9B92, "Load existing TX buffer byte", inline=True)
comment(0x9B94, "Save original value on stack", inline=True)
comment(0x9B95, "Copy template value to A", inline=True)
comment(0x9B96, "Store template value to TX buffer", inline=True)
comment(0x9B98, "Next offset (descending)", inline=True)
comment(0x9B99, "Loop until all 12 bytes processed", inline=True)
comment(0x9B9B, "Load pass-through control value", inline=True)
comment(0x9B9E, "Push control value", inline=True)
comment(0x9B9F, "A=&FF (Y is &FF after loop)", inline=True)
comment(0x9BA0, "Push &FF as timeout", inline=True)
comment(0x9BA1, "X=0: TX pointer index", inline=True)
comment(0x9BA3, "Load control byte from TX CB", inline=True)
comment(0x9BA5, "Write control byte to start TX", inline=True)
comment(0x9BA7, "Save control byte on stack", inline=True)
comment(0x9BA8, "Poll ADLC until line idle", inline=True)
comment(0x9BAB, "Shift result: check bit 6 (success)", inline=True)
comment(0x9BAC, "Bit 6 clear: transmission complete", inline=True)
comment(0x9BAE, "Shift result: check bit 5 (fatal)", inline=True)
comment(0x9BAF, "Non-zero (not fatal): retry", inline=True)
comment(0x9BB1, "X=0: clear error status", inline=True)
comment(0x9BB3, "Jump to fix up reply status", inline=True)
comment(0x9BB6, "Shift ws_0d60 left to poll ADLC", inline=True)
comment(0x9BB9, "Bit not set: keep polling", inline=True)
comment(0x9BBB, "Copy TX pointer low to NMI TX block", inline=True)
comment(0x9BBD, "Store in NMI TX block low", inline=True)
comment(0x9BBF, "Copy TX pointer high", inline=True)
comment(0x9BC1, "Store in NMI TX block high", inline=True)
comment(0x9BC3, "Begin Econet frame transmission", inline=True)
comment(0x9BC6, "Read TX status byte", inline=True)
comment(0x9BC8, "Bit 7 set: still transmitting", inline=True)
comment(0x9BCA, "Return with result in A", inline=True)
comment(0x9BCB, "Pull control byte", inline=True)
comment(0x9BCC, "Restore to X", inline=True)
comment(0x9BCD, "Pull timeout", inline=True)
comment(0x9BCE, "Restore to Y", inline=True)
comment(0x9BCF, "Pull retry count", inline=True)
comment(0x9BD0, "Zero retries: go to error handling", inline=True)
comment(0x9BD2, "Decrement retry counter", inline=True)
comment(0x9BD4, "Push updated retry count", inline=True)
comment(0x9BD5, "Copy timeout to A", inline=True)
comment(0x9BD6, "Push timeout", inline=True)
comment(0x9BD7, "Copy control byte to A", inline=True)
comment(0x9BD8, "Inner delay loop: decrement X", inline=True)
comment(0x9BD9, "Loop until X=0", inline=True)
comment(0x9BDB, "Decrement outer counter Y", inline=True)
comment(0x9BDC, "Loop until Y=0", inline=True)
comment(0x9BDE, "ALWAYS branch: retry transmission", inline=True)
comment(0x9BE0, "Pull control byte (discard)", inline=True)
comment(0x9BE1, "Pull timeout (discard)", inline=True)
comment(0x9BE2, "Pull retry count (discard)", inline=True)
comment(0x9BE3, "Y=0: start restoring from offset 0", inline=True)
comment(0x9BE5, "Load template byte for this offset", inline=True)
comment(0x9BE8, "Is it &FD (skip marker)?", inline=True)
comment(0x9BEA, "Yes: don't restore this offset", inline=True)
comment(0x9BEC, "Pull original value from stack", inline=True)
comment(0x9BED, "Restore original TX buffer byte", inline=True)
comment(0x9BEF, "Next offset (ascending)", inline=True)
comment(0x9BF0, "Processed all 12 bytes?", inline=True)
comment(0x9BF2, "No: continue restoring", inline=True)
comment(0x9BF4, "Return with TX buffer restored", inline=True)
comment(0x9BF5, "Y=1: start at second byte of pointer", inline=True)
comment(0x9BF7, "Load pointer byte from FS options", inline=True)
comment(0x9BF9, "Store in OS text pointer", inline=True)
comment(0x9BFC, "Decrement index", inline=True)
comment(0x9BFD, "Loop until both bytes copied", inline=True)
comment(0x9BFF, "Y=0: reset index for string reading", inline=True)
comment(0x9C00, "X=&FF: pre-increment for buffer index", inline=True)
comment(0x9C02, "C=0: initialise for string input", inline=True)
comment(0x9C03, "GSINIT: initialise string reading", inline=True)
comment(0x9C06, "Z set (empty string): store terminator", inline=True)
comment(0x9C08, "GSREAD: read next character", inline=True)
comment(0x9C0B, "C set: end of string reached", inline=True)
comment(0x9C0D, "Advance buffer index", inline=True)
comment(0x9C0E, "Store character in fs_filename_buf buffer", inline=True)
comment(0x9C11, "ALWAYS branch: read next character", inline=True)
comment(0x9C13, "Advance past last character", inline=True)
comment(0x9C14, "A=CR: terminate filename", inline=True)
comment(0x9C16, "Store CR terminator in buffer", inline=True)
comment(0x9C19, "A=&30: low byte of fs_filename_buf buffer", inline=True)
comment(0x9C1B, "Set command text pointer low", inline=True)
comment(0x9C1D, "A=&0E: high byte of fs_filename_buf buffer", inline=True)
comment(0x9C1F, "Set command text pointer high", inline=True)
comment(0x9C21, "Return with buffer filled", inline=True)
comment(0x9C22, "Set up transfer parameters", inline=True)
comment(0x9C25, "Load text pointer and parse filename", inline=True)
comment(0x9C28, "Set owner-only access mask", inline=True)
comment(0x9C2B, "Parse access prefix from filename", inline=True)
comment(0x9C2E, "Load last byte flag", inline=True)
comment(0x9C30, "Positive (not last): display file info", inline=True)
comment(0x9C32, "Is it &FF (last entry)?", inline=True)
comment(0x9C34, "Yes: copy arg and iterate", inline=True)
comment(0x9C36, "Other value: return with flag", inline=True)
comment(0x9C39, "Copy argument to buffer at X=0", inline=True)
comment(0x9C3C, "Y=2: enumerate directory command", inline=True)
comment(0x9C3E, "A=&92: FS port number", inline=True)
comment(0x9C40, "Set escapable flag to &92", inline=True)
comment(0x9C42, "Store port number in TX buffer", inline=True)
comment(0x9C45, "Send request to file server", inline=True)
comment(0x9C48, "Y=6: offset to response cycle flag", inline=True)
comment(0x9C4A, "Load cycle flag from FS options", inline=True)
comment(0x9C4C, "Non-zero: already initialised", inline=True)
comment(0x9C4E, "Copy FS options to zero page first", inline=True)
comment(0x9C51, "Then copy workspace to FS options", inline=True)
comment(0x9C54, "Branch to continue (C clear from JSR)", inline=True)
comment(0x9C56, "Copy workspace to FS options first", inline=True)
comment(0x9C59, "Then copy FS options to zero page", inline=True)
comment(0x9C5C, "Y=4: loop counter", inline=True)
comment(0x9C5E, "Load address byte from zero page", inline=True)
comment(0x9C60, "Save to TXCB end pointer", inline=True)
comment(0x9C62, "Add offset from buffer", inline=True)
comment(0x9C65, "Store sum in fs_work area", inline=True)
comment(0x9C67, "Advance to next byte", inline=True)
comment(0x9C68, "Decrement counter", inline=True)
comment(0x9C69, "Loop for all 4 bytes", inline=True)
comment(0x9C6B, "Set carry for subtraction", inline=True)
comment(0x9C6C, "Subtract high offset", inline=True)
comment(0x9C6F, "Store result in fs_work_7", inline=True)
comment(0x9C71, "Format filename for display", inline=True)
comment(0x9C74, "Send TXCB and swap addresses", inline=True)
comment(0x9C77, "X=2: copy 3 offset bytes", inline=True)
comment(0x9C79, "Load offset byte from fs_file_len_3", inline=True)
comment(0x9C7C, "Store in fs_cmd_data for next iteration", inline=True)
comment(0x9C7F, "Decrement counter", inline=True)
comment(0x9C80, "Loop until all bytes copied", inline=True)
comment(0x9C82, "Jump to receive and process reply", inline=True)
comment(0x9C85, "Compare 5-byte handle with current", inline=True)
comment(0x9C88, "Match: no need to send, return", inline=True)
comment(0x9C8A, "A=&92: FS reply port number", inline=True)
comment(0x9C8C, "Set TXCB port", inline=True)
comment(0x9C8E, "X=3: copy 4 bytes", inline=True)
comment(0x9C90, "Load TXCB end pointer byte", inline=True)
comment(0x9C92, "Store in TXCB start pointer", inline=True)
comment(0x9C94, "Load new end address from fs_work", inline=True)
comment(0x9C96, "Store in TXCB end pointer", inline=True)
comment(0x9C98, "Decrement counter", inline=True)
comment(0x9C99, "Loop for all 4 bytes", inline=True)
comment(0x9C9B, "A=&7F: control byte for data transfer", inline=True)
comment(0x9C9D, "Set TXCB control byte", inline=True)
comment(0x9C9F, "Wait for network TX acknowledgement", inline=True)
comment(0x9CA2, "Y=3: compare 4 bytes", inline=True)
comment(0x9CA4, "Load TXCB end byte", inline=True)
comment(0x9CA7, "Compare with expected end address", inline=True)
comment(0x9CAA, "Mismatch: resend from start", inline=True)
comment(0x9CAC, "Decrement counter", inline=True)
comment(0x9CAD, "Loop until all 4 bytes match", inline=True)
comment(0x9CAF, "Return (all bytes match)", inline=True)
comment(0x9CB0, "Z set: directory entry display", inline=True)
comment(0x9CB2, "Non-zero: jump to OSWORD dispatch", inline=True)
comment(0x9CB5, "X=4: loop counter for 4 iterations", inline=True)
comment(0x9CB7, "Y=&0E: FS options offset for addresses", inline=True)
comment(0x9CB9, "Set carry for subtraction", inline=True)
comment(0x9CBA, "Load address byte from FS options", inline=True)
comment(0x9CBC, "Save to workspace (port_ws_offset)", inline=True)
comment(0x9CBF, "Y -= 4 to point to paired offset", inline=True)
comment(0x9CC2, "Subtract paired value", inline=True)
comment(0x9CC4, "Store difference in fs_cmd_csd buffer", inline=True)
comment(0x9CC7, "Push difference", inline=True)
comment(0x9CC8, "Load paired value from FS options", inline=True)
comment(0x9CCA, "Save to workspace", inline=True)
comment(0x9CCD, "Pull difference back", inline=True)
comment(0x9CCE, "Store in FS options for display", inline=True)
comment(0x9CD0, "Advance Y by 5 for next field", inline=True)
comment(0x9CD3, "Decrement loop counter", inline=True)
comment(0x9CD4, "Loop for all 4 address pairs", inline=True)
comment(0x9CD6, "Y=9: copy 9 bytes of options data", inline=True)
comment(0x9CD8, "Load FS options byte", inline=True)
comment(0x9CDA, "Store in fs_cmd_csd buffer", inline=True)
comment(0x9CDD, "Decrement index", inline=True)
comment(0x9CDE, "Loop until all 9 bytes copied", inline=True)
comment(0x9CE0, "A=&91: FS port for info request", inline=True)
comment(0x9CE2, "Set escapable flag", inline=True)
comment(0x9CE4, "Store port in TX buffer", inline=True)
comment(0x9CE7, "Store in fs_error_ptr", inline=True)
comment(0x9CE9, "X=&0B: copy argument at offset 11", inline=True)
comment(0x9CEB, "Copy argument to TX buffer", inline=True)
comment(0x9CEE, "Y=1: info sub-command", inline=True)
comment(0x9CF0, "Load last byte flag", inline=True)
comment(0x9CF2, "Is it 7 (catalogue info)?", inline=True)
comment(0x9CF4, "Save comparison result", inline=True)
comment(0x9CF5, "Not 7: keep Y=1", inline=True)
comment(0x9CF7, "Y=&1D: extended info command", inline=True)
comment(0x9CF9, "Send request to file server", inline=True)
comment(0x9CFC, "Format filename for display", inline=True)
comment(0x9CFF, "Restore comparison flags", inline=True)
comment(0x9D00, "Not catalogue info: show short format", inline=True)
comment(0x9D02, "X=0: start at first byte", inline=True)
comment(0x9D04, "ALWAYS branch to store and display", inline=True)
comment(0x9D06, "Load file handle from fs_cmd_data", inline=True)
comment(0x9D09, "Check and set up TXCB for transfer", inline=True)
comment(0x9D0C, "Receive and process reply", inline=True)
comment(0x9D0F, "Store result byte in fs_reply_cmd", inline=True)
comment(0x9D12, "Y=&0E: protection bits offset", inline=True)
comment(0x9D14, "Load access byte from fs_cmd_data", inline=True)
comment(0x9D17, "Extract protection bit flags", inline=True)
comment(0x9D1A, "Zero: use reply buffer data", inline=True)
comment(0x9D1C, "Load file info byte from fs_reply_data", inline=True)
comment(0x9D1F, "Store in FS options at offset Y", inline=True)
comment(0x9D21, "Advance to next byte", inline=True)
comment(0x9D22, "Y=&12: end of protection fields?", inline=True)
comment(0x9D24, "No: copy next byte", inline=True)
comment(0x9D26, "Load display flag from fs_messages_flag", inline=True)
comment(0x9D29, "Zero: skip display, return", inline=True)
comment(0x9D2B, "Y=&F4: index into hazel_display_buf for filename", inline=True)
comment(0x9D2D, "Load filename character from filename_buf", inline=True)
comment(0x9D30, "Print character via OSASCI", inline=True)
comment(0x9D33, "Advance to next character", inline=True)
comment(0x9D34, "Printed all 12 characters?", inline=True)
comment(0x9D36, "Y=5: offset for access string", inline=True)
comment(0x9D38, "Print 5 hex bytes (access info)", inline=True)
comment(0x9D3B, "Print load and exec addresses", inline=True)
comment(0x9D3E, "Print newline", inline=True)
comment(0x9D41, "Jump to return with last flag", inline=True)
comment(0x9D44, "Y=9: offset for exec address", inline=True)
comment(0x9D46, "Print 5 hex bytes (exec address)", inline=True)
comment(0x9D49, "Y=&0C: offset for length (3 bytes)", inline=True)
comment(0x9D4B, "X=3: print 3 bytes only", inline=True)
comment(0x9D4D, "ALWAYS branch to print routine", inline=True)
comment(0x9D4F, "X=4: print 5 bytes (4 to 0)", inline=True)
comment(0x9D51, "Load byte from FS options at offset Y", inline=True)
comment(0x9D53, "Print as 2-digit hex", inline=True)
comment(0x9D56, "Decrement byte offset", inline=True)
comment(0x9D57, "Decrement byte count", inline=True)
comment(0x9D58, "Loop until all bytes printed", inline=True)
comment(0x9D5A, "A=' ': space separator", inline=True)
comment(0x9D5C, "Print space via OSASCI and return", inline=True)
comment(0x9D5F, "Y=5: copy 4 bytes (offsets 2-5)", inline=True)
comment(0x9D61, "Load byte from FS options", inline=True)
comment(0x9D63, "Store in zero page at work_ae+Y", inline=True)
comment(0x9D66, "Decrement index", inline=True)
comment(0x9D67, "Below offset 2?", inline=True)
comment(0x9D69, "No: copy next byte", inline=True)
comment(0x9D6B, "Y += 5", inline=True)
comment(0x9D6C, "Y += 4", inline=True)
comment(0x9D6D, "(continued)", inline=True)
comment(0x9D6E, "(continued)", inline=True)
comment(0x9D6F, "(continued)", inline=True)
comment(0x9D70, "Return", inline=True)
comment(0x9D71, "Y=&0D: copy bytes from offset &0D down", inline=True)
comment(0x9D73, "Transfer X to A", inline=True)
comment(0x9D74, "Store byte in FS options at offset Y", inline=True)
comment(0x9D76, "Load next workspace byte from fs_cmd_urd+Y", inline=True)
comment(0x9D79, "Decrement index", inline=True)
comment(0x9D7A, "Below offset 2?", inline=True)
comment(0x9D7C, "No: copy next byte", inline=True)
comment(0x9D7E, "Y -= 4", inline=True)
comment(0x9D7F, "Y -= 3", inline=True)
comment(0x9D80, "(continued)", inline=True)
comment(0x9D81, "(continued)", inline=True)
comment(0x9D82, "Return", inline=True)
comment(0x9D83, "Discard stacked value", inline=True)
comment(0x9D84, "Restore Y from fs_block_offset", inline=True)
comment(0x9D86, "Return (handle already matches)", inline=True)
comment(0x9D87, "Save port/sub-function on stack", inline=True)
comment(0x9D88, "Compare 5-byte handle with current", inline=True)
comment(0x9D8B, "Match: discard port and return", inline=True)
comment(0x9D8D, "X=0: loop start", inline=True)
comment(0x9D8F, "Y=4: copy 4 bytes", inline=True)
comment(0x9D91, "Clear fs_reply_cmd (transfer size low)", inline=True)
comment(0x9D94, "Clear fs_load_vector (transfer size high)", inline=True)
comment(0x9D97, "Clear carry for addition", inline=True)
comment(0x9D98, "Load address byte from zero page", inline=True)
comment(0x9D9A, "Store in TXCB start pointer", inline=True)
comment(0x9D9C, "Add offset from fs_func_code", inline=True)
comment(0x9D9F, "Store sum in TXCB end pointer", inline=True)
comment(0x9DA1, "Also update load address", inline=True)
comment(0x9DA3, "Advance to next byte", inline=True)
comment(0x9DA4, "Decrement counter", inline=True)
comment(0x9DA5, "Loop for all 4 bytes", inline=True)
comment(0x9DA7, "Carry set: overflow, use limit", inline=True)
comment(0x9DA9, "Set carry for subtraction", inline=True)
comment(0x9DAA, "Load computed end address", inline=True)
comment(0x9DAD, "Subtract maximum from fs_work_4", inline=True)
comment(0x9DB0, "Advance to next byte", inline=True)
comment(0x9DB1, "Decrement counter", inline=True)
comment(0x9DB2, "Loop for all bytes", inline=True)
comment(0x9DB4, "Below limit: keep computed end", inline=True)
comment(0x9DB6, "X=3: copy 4 bytes of limit", inline=True)
comment(0x9DB8, "Load limit from fs_work_4", inline=True)
comment(0x9DBA, "Store as TXCB end", inline=True)
comment(0x9DBC, "Decrement counter", inline=True)
comment(0x9DBD, "Loop for all 4 bytes", inline=True)
comment(0x9DBF, "Pull port from stack", inline=True)
comment(0x9DC0, "Push back (keep for later)", inline=True)
comment(0x9DC1, "Save flags (carry = overflow state)", inline=True)
comment(0x9DC2, "Set TXCB port number", inline=True)
comment(0x9DC4, "A=&80: control byte for data request", inline=True)
comment(0x9DC6, "Set TXCB control byte", inline=True)
comment(0x9DC8, "Init TX pointer and send packet", inline=True)
comment(0x9DCB, "Load error pointer", inline=True)
comment(0x9DCD, "Init TXCB port from error pointer", inline=True)
comment(0x9DD0, "Restore overflow flags", inline=True)
comment(0x9DD1, "Carry set: discard and return", inline=True)
comment(0x9DD3, "A=&91: FS reply port", inline=True)
comment(0x9DD5, "Set TXCB port for reply", inline=True)
comment(0x9DD7, "Wait for TX acknowledgement", inline=True)
comment(0x9DDA, "Non-zero (not done): retry send", inline=True)
comment(0x9DDC, "Store sub-operation code", inline=True)
comment(0x9DDF, "Compare with 7", inline=True)
comment(0x9DE1, "Below 7: handle operations 1-6", inline=True)
comment(0x9DE3, "Above 7: jump to handle via finalise", inline=True)
comment(0x9DE5, "Equal to 7: jump to directory display", inline=True)
comment(0x9DE8, "Compare with 6", inline=True)
comment(0x9DEA, "6: delete file operation", inline=True)
comment(0x9DEC, "Compare with 5", inline=True)
comment(0x9DEE, "5: read catalogue info", inline=True)
comment(0x9DF0, "Compare with 4", inline=True)
comment(0x9DF2, "4: write file attributes", inline=True)
comment(0x9DF4, "Compare with 1", inline=True)
comment(0x9DF6, "1: read file info", inline=True)
comment(0x9DF8, "Shift left twice: A*4", inline=True)
comment(0x9DF9, "A*4", inline=True)
comment(0x9DFA, "Copy to Y as index", inline=True)
comment(0x9DFB, "Y -= 3 to get FS options offset", inline=True)
comment(0x9DFE, "X=3: copy 4 bytes", inline=True)
comment(0x9E00, "Load byte from FS options at offset Y", inline=True)
comment(0x9E02, "Store in fs_func_code buffer", inline=True)
comment(0x9E05, "Decrement source offset", inline=True)
comment(0x9E06, "Decrement byte count", inline=True)
comment(0x9E07, "Loop for all 4 bytes", inline=True)
comment(0x9E09, "X=5: copy arg to buffer at offset 5", inline=True)
comment(0x9E0B, "ALWAYS branch to copy and send", inline=True)
comment(0x9E0D, "Get access bits for file", inline=True)
comment(0x9E10, "Store access byte in fs_file_attrs", inline=True)
comment(0x9E13, "Y=9: source offset in FS options", inline=True)
comment(0x9E15, "X=8: copy 8 bytes to buffer", inline=True)
comment(0x9E17, "Load FS options byte", inline=True)
comment(0x9E19, "Store in fs_cmd_data buffer", inline=True)
comment(0x9E1C, "Decrement source offset", inline=True)
comment(0x9E1D, "Decrement byte count", inline=True)
comment(0x9E1E, "Loop for all 8 bytes", inline=True)
comment(0x9E20, "X=&0A: buffer offset for argument", inline=True)
comment(0x9E22, "Copy argument to buffer", inline=True)
comment(0x9E25, "Y=&13: OSWORD &13 (NFS operation)", inline=True)
comment(0x9E27, "ALWAYS branch to send request", inline=True)
comment(0x9E29, "Copy argument to buffer at X=0", inline=True)
comment(0x9E2C, "Y=&14: delete file command", inline=True)
comment(0x9E2E, "Set V flag (no directory check)", inline=True)
comment(0x9E31, "Send request with V set", inline=True)
comment(0x9E34, "Carry set: error, jump to finalise", inline=True)
comment(0x9E36, "No error: return with last flag", inline=True)
comment(0x9E39, "Get access bits for file", inline=True)
comment(0x9E3C, "Store in fs_func_code", inline=True)
comment(0x9E3F, "X=2: buffer offset", inline=True)
comment(0x9E41, "ALWAYS branch to copy and send", inline=True)
comment(0x9E43, "X=1: buffer offset", inline=True)
comment(0x9E45, "Copy argument to buffer", inline=True)
comment(0x9E48, "Y=&12: open file command", inline=True)
comment(0x9E4A, "Send open file request", inline=True)
comment(0x9E4D, "Load reply handle from fs_obj_type", inline=True)
comment(0x9E50, "Clear fs_obj_type", inline=True)
comment(0x9E53, "Clear fs_len_clear", inline=True)
comment(0x9E56, "Get protection bits", inline=True)
comment(0x9E59, "Load file handle from fs_cmd_data", inline=True)
comment(0x9E5C, "Zero: file not found, return", inline=True)
comment(0x9E5E, "Y=&0E: store access bits", inline=True)
comment(0x9E60, "Store access byte in FS options", inline=True)
comment(0x9E62, "Y=&0D", inline=True)
comment(0x9E63, "X=&0C: copy 12 bytes of file info", inline=True)
comment(0x9E65, "Load reply byte from fs_cmd_data+X", inline=True)
comment(0x9E68, "Store in FS options at offset Y", inline=True)
comment(0x9E6A, "Decrement destination offset", inline=True)
comment(0x9E6B, "Decrement source counter", inline=True)
comment(0x9E6C, "Loop for all 12 bytes", inline=True)
comment(0x9E6E, "X=1 (INX from 0)", inline=True)
comment(0x9E6F, "X=2", inline=True)
comment(0x9E70, "Y=&11: FS options offset", inline=True)
comment(0x9E72, "Load extended info byte from fs_access_level", inline=True)
comment(0x9E75, "Store in FS options", inline=True)
comment(0x9E77, "Decrement destination offset", inline=True)
comment(0x9E78, "Decrement source counter", inline=True)
comment(0x9E79, "Loop until all copied", inline=True)
comment(0x9E7B, "Reload file handle", inline=True)
comment(0x9E7E, "Transfer to A", inline=True)
comment(0x9E7F, "Jump to finalise and return", inline=True)
comment(0x9E82, "Y=0: start writing at filename_buf[0]", inline=True)
comment(0x9E84, "Load source offset from fs_cmd_csd", inline=True)
comment(0x9E87, "Non-zero: copy from fs_cmd_data buffer", inline=True)
comment(0x9E89, "Load character from command line", inline=True)
comment(0x9E8B, "Below '!' (control/space)?", inline=True)
comment(0x9E8D, "Yes: pad with spaces", inline=True)
comment(0x9E8F, "Store printable character in filename_buf", inline=True)
comment(0x9E92, "Advance to next character", inline=True)
comment(0x9E93, "Loop for more characters", inline=True)
comment(0x9E95, "A=' ': space for padding", inline=True)
comment(0x9E97, "Store space in display buffer", inline=True)
comment(0x9E9A, "Advance index", inline=True)
comment(0x9E9B, "Filled all 12 characters?", inline=True)
comment(0x9E9D, "No: pad more spaces", inline=True)
comment(0x9E9F, "Return with field formatted", inline=True)
comment(0x9EA0, "Advance source and destination", inline=True)
comment(0x9EA2, "Load byte from fs_cmd_data buffer", inline=True)
comment(0x9EA5, "Store in filename_buf", inline=True)
comment(0x9EA8, "Bit 7 clear: more characters", inline=True)
comment(0x9EAA, "Return (bit 7 set = terminator)", inline=True)
comment(0x9EAB, "Verify workspace checksum", inline=True)
comment(0x9EAE, "Store result as last byte flag", inline=True)
comment(0x9EB0, "Set FS options pointer", inline=True)
comment(0x9EB3, "OR with 0 to set flags", inline=True)
comment(0x9EB5, "Positive: handle sub-operations", inline=True)
comment(0x9EB7, "Shift left to check bit 6", inline=True)
comment(0x9EB8, "Zero (was &80): close channel", inline=True)
comment(0x9EBA, "Other: process all FCBs first", inline=True)
comment(0x9EBD, "Transfer Y to A", inline=True)
comment(0x9EBE, "Compare with &20 (space)", inline=True)
comment(0x9EC0, "Above &20: check further", inline=True)
comment(0x9EC2, "Below &20: invalid channel char", inline=True)
comment(0x9EC5, "Compare with '0'", inline=True)
comment(0x9EC7, "Above '0': invalid channel char", inline=True)
comment(0x9EC9, "Process all matching FCBs", inline=True)
comment(0x9ECC, "Transfer Y to A (FCB index)", inline=True)
comment(0x9ECD, "Push FCB index", inline=True)
comment(0x9ECE, "Copy to X", inline=True)
comment(0x9ECF, "Y=0: clear counter", inline=True)
comment(0x9ED1, "Clear last byte flag", inline=True)
comment(0x9ED3, "Clear block offset", inline=True)
comment(0x9ED5, "Load channel data from fcb_attr_or_count_mid+X", inline=True)
comment(0x9ED8, "Store in FS options at Y", inline=True)
comment(0x9EDA, "Advance X by 8 (next FCB field)", inline=True)
comment(0x9EDD, "Advance destination index", inline=True)
comment(0x9EDE, "Copied all 4 channel fields?", inline=True)
comment(0x9EE0, "No: copy next field", inline=True)
comment(0x9EE2, "Pull saved FCB index", inline=True)
comment(0x9EE3, "Restore to fs_block_offset", inline=True)
comment(0x9EE5, "Compare with 5", inline=True)
comment(0x9EE7, "5 or above: return with last flag", inline=True)
comment(0x9EE9, "Compare Y with 0", inline=True)
comment(0x9EEB, "Non-zero: handle OSFIND with channel", inline=True)
comment(0x9EED, "Y=0 (close): jump to OSFIND open", inline=True)
comment(0x9EF0, "Push sub-function", inline=True)
comment(0x9EF1, "Transfer X to A", inline=True)
comment(0x9EF2, "Push X (FCB slot)", inline=True)
comment(0x9EF3, "Transfer Y to A", inline=True)
comment(0x9EF4, "Push Y (channel char)", inline=True)
comment(0x9EF5, "Check file is not a directory", inline=True)
comment(0x9EF8, "Pull channel char", inline=True)
comment(0x9EF9, "Store channel char as receive attribute", inline=True)
comment(0x9EFC, "Load FCB flag byte from fcb_net_or_port", inline=True)
comment(0x9EFF, "Store in fs_cmd_data", inline=True)
comment(0x9F02, "Pull X (FCB slot)", inline=True)
comment(0x9F03, "Restore X", inline=True)
comment(0x9F04, "Pull sub-function", inline=True)
comment(0x9F05, "Shift right: check bit 0", inline=True)
comment(0x9F06, "Zero (OSFIND close): handle close", inline=True)
comment(0x9F08, "Save flags (carry from LSR)", inline=True)
comment(0x9F09, "Push sub-function", inline=True)
comment(0x9F0A, "Load FS options pointer low", inline=True)
comment(0x9F0C, "Load block offset", inline=True)
comment(0x9F0E, "Process all matching FCBs", inline=True)
comment(0x9F11, "Load updated data from fcb_attr_or_count_mid", inline=True)
comment(0x9F14, "Store in fs_cmd_data", inline=True)
comment(0x9F17, "Pull sub-function", inline=True)
comment(0x9F18, "Store in fs_func_code", inline=True)
comment(0x9F1B, "Restore flags", inline=True)
comment(0x9F1C, "Transfer Y to A", inline=True)
comment(0x9F1D, "Push Y (offset)", inline=True)
comment(0x9F1E, "Carry clear: read operation", inline=True)
comment(0x9F20, "Y=3: copy 4 bytes", inline=True)
comment(0x9F22, "Load zero page data", inline=True)
comment(0x9F24, "Store in fs_data_count buffer", inline=True)
comment(0x9F27, "Decrement source", inline=True)
comment(0x9F28, "Decrement counter", inline=True)
comment(0x9F29, "Loop for all 4 bytes", inline=True)
comment(0x9F2B, "Y=&0D: TX buffer size", inline=True)
comment(0x9F2D, "X=5: argument offset", inline=True)
comment(0x9F2F, "Send TX control block to server", inline=True)
comment(0x9F32, "Store X in last byte flag", inline=True)
comment(0x9F34, "Pull saved offset", inline=True)
comment(0x9F35, "Set connection active flag", inline=True)
comment(0x9F38, "Return with last flag", inline=True)
comment(0x9F3B, "Y=&0C: TX buffer size (smaller)", inline=True)
comment(0x9F3D, "X=2: argument offset", inline=True)
comment(0x9F3F, "Send TX control block", inline=True)
comment(0x9F42, "Store A in last byte flag", inline=True)
comment(0x9F44, "Load FS options pointer low", inline=True)
comment(0x9F46, "Y=2: zero page offset", inline=True)
comment(0x9F48, "Store A in zero page", inline=True)
comment(0x9F4A, "Load buffer byte from fs_cmd_data+Y", inline=True)
comment(0x9F4D, "Store in zero page at offset", inline=True)
comment(0x9F4F, "Decrement source X", inline=True)
comment(0x9F50, "Decrement counter Y", inline=True)
comment(0x9F51, "Loop until all bytes copied", inline=True)
comment(0x9F53, "Pull saved offset", inline=True)
comment(0x9F54, "Return with last flag", inline=True)
comment(0x9F57, "Carry set: write file pointer", inline=True)
comment(0x9F59, "Load block offset", inline=True)
comment(0x9F5B, "Convert attribute to channel index", inline=True)
comment(0x9F5E, "Load FS options pointer", inline=True)
comment(0x9F60, "Load FCB low byte from fcb_count_lo", inline=True)
comment(0x9F63, "Store in zero page pointer low", inline=True)
comment(0x9F66, "Load FCB high byte from fcb_attr_or_count_mid", inline=True)
comment(0x9F69, "Store in zero page pointer high", inline=True)
comment(0x9F6C, "Load FCB extent from fcb_station_or_count_hi", inline=True)
comment(0x9F6F, "Store in zero page work area", inline=True)
comment(0x9F72, "A=0: clear high byte", inline=True)
comment(0x9F74, "Store zero in work area high", inline=True)
comment(0x9F77, "ALWAYS branch to return with flag", inline=True)
comment(0x9F79, "Store write value in fs_func_code", inline=True)
comment(0x9F7C, "Transfer X to A", inline=True)
comment(0x9F7D, "Push X (zero page offset)", inline=True)
comment(0x9F7E, "Y=3: copy 4 bytes", inline=True)
comment(0x9F80, "Load zero page data at offset", inline=True)
comment(0x9F82, "Store in fs_data_count buffer", inline=True)
comment(0x9F85, "Decrement source", inline=True)
comment(0x9F86, "Decrement counter", inline=True)
comment(0x9F87, "Loop for all 4 bytes", inline=True)
comment(0x9F89, "Y=&0D: TX buffer size", inline=True)
comment(0x9F8B, "X=5: argument offset", inline=True)
comment(0x9F8D, "Send TX control block", inline=True)
comment(0x9F90, "Store X in last byte flag", inline=True)
comment(0x9F92, "Pull saved zero page offset", inline=True)
comment(0x9F93, "Transfer to Y", inline=True)
comment(0x9F94, "Load block offset (attribute)", inline=True)
comment(0x9F96, "Clear connection active flag", inline=True)
comment(0x9F99, "Convert attribute to channel index", inline=True)
comment(0x9F9C, "Load zero page pointer low", inline=True)
comment(0x9F9F, "Store back to FCB fcb_count_lo", inline=True)
comment(0x9FA2, "Load zero page pointer high", inline=True)
comment(0x9FA5, "Store back to FCB fcb_attr_or_count_mid", inline=True)
comment(0x9FA8, "Load zero page work byte", inline=True)
comment(0x9FAB, "Store back to FCB fcb_station_or_count_hi", inline=True)
comment(0x9FAE, "Return with last flag", inline=True)
comment(0x9FB1, "Process all matching FCBs first", inline=True)
comment(0x9FB4, "Load last byte flag", inline=True)
comment(0x9FB6, "Push result on stack", inline=True)
comment(0x9FB7, "A=0: clear error flag", inline=True)
comment(0x9FB9, "Clear receive attribute (A=0)", inline=True)
comment(0x9FBC, "Pull result back", inline=True)
comment(0x9FBD, "Restore X from FS options pointer", inline=True)
comment(0x9FBF, "Restore Y from block offset", inline=True)
comment(0x9FC1, "Return to caller", inline=True)
comment(0x9FC2, "Compare with 2 (open for output)", inline=True)
comment(0x9FC4, "2 or above: handle file open", inline=True)
comment(0x9FC6, "Transfer to Y (Y=0 or 1)", inline=True)
comment(0x9FC7, "Non-zero (1 = read pointer): copy data", inline=True)
comment(0x9FC9, "A=5: return code for close-all", inline=True)
comment(0x9FCB, "ALWAYS branch to finalise", inline=True)
comment(0x9FCD, "Z set: jump to clear A and return", inline=True)
comment(0x9FCF, "A=0: clear result", inline=True)
comment(0x9FD1, "Shift right (always positive)", inline=True)
comment(0x9FD2, "Positive: jump to finalise", inline=True)
comment(0x9FD4, "Mask to 6-bit access value", inline=True)
comment(0x9FD6, "Non-zero: clear A and finalise", inline=True)
comment(0x9FD8, "Transfer X to A (options pointer)", inline=True)
comment(0x9FD9, "Allocate FCB slot or raise error", inline=True)
comment(0x9FDC, "Toggle bit 7", inline=True)
comment(0x9FDE, "Shift left: build open mode", inline=True)
comment(0x9FDF, "Store open mode in fs_cmd_data", inline=True)
comment(0x9FE2, "Rotate to complete mode byte", inline=True)
comment(0x9FE3, "Store in fs_func_code", inline=True)
comment(0x9FE6, "Parse command argument (Y=0)", inline=True)
comment(0x9FE9, "X=2: buffer offset", inline=True)
comment(0x9FEB, "Copy argument to TX buffer", inline=True)
comment(0x9FEE, "Y=6: open file command", inline=True)
comment(0x9FF0, "Set V flag (skip directory check)", inline=True)
comment(0x9FF3, "Set carry", inline=True)
comment(0x9FF4, "Rotate carry into escapable flag bit 7", inline=True)
comment(0x9FF6, "Send open request with V set", inline=True)
comment(0x9FF9, "Carry set (error): jump to finalise", inline=True)
comment(0x9FFB, "A=&FF: mark as newly opened", inline=True)
comment(0x9FFD, "Store &FF as receive attribute", inline=True)
comment(0xA000, "Load handle from fs_cmd_data", inline=True)
comment(0xA003, "Push handle", inline=True)
comment(0xA004, "A=4: file info sub-command", inline=True)
comment(0xA006, "Store sub-command", inline=True)
comment(0xA009, "X=1: shift filename", inline=True)
comment(0xA00B, "Load filename byte from fs_func_code+X", inline=True)
comment(0xA00E, "Shift down to fs_cmd_data+X", inline=True)
comment(0xA011, "Advance source index", inline=True)
comment(0xA012, "Is it CR (end of filename)?", inline=True)
comment(0xA014, "No: continue shifting", inline=True)
comment(0xA016, "Y=&12: file info request", inline=True)
comment(0xA018, "Send file info request", inline=True)
comment(0xA01B, "Load last byte flag", inline=True)
comment(0xA01D, "Clear bit 6 (read/write bits)", inline=True)
comment(0xA01F, "OR with reply access byte", inline=True)
comment(0xA022, "Set bit 0 (file is open)", inline=True)
comment(0xA024, "Transfer to Y (access flags)", inline=True)
comment(0xA025, "Check bit 1 (write access)", inline=True)
comment(0xA027, "No write access: check read-only", inline=True)
comment(0xA029, "Pull handle from stack", inline=True)
comment(0xA02A, "Allocate FCB slot for channel", inline=True)
comment(0xA02D, "Non-zero: FCB allocated, store flags", inline=True)
comment(0xA02F, "Verify workspace checksum", inline=True)
comment(0xA032, "Set up transfer parameters", inline=True)
comment(0xA035, "Transfer A to X", inline=True)
comment(0xA036, "Set owner-only access mask", inline=True)
comment(0xA039, "Transfer X back to A", inline=True)
comment(0xA03A, "Zero: close file, process FCBs", inline=True)
comment(0xA03C, "Save text pointer for OS", inline=True)
comment(0xA03F, "Load current directory handle", inline=True)
comment(0xA042, "Zero: allocate new FCB", inline=True)
comment(0xA044, "Transfer Y to A", inline=True)
comment(0xA045, "X=0: clear directory handle", inline=True)
comment(0xA047, "Store zero (clear handle)", inline=True)
comment(0xA04A, "ALWAYS branch to finalise", inline=True)
comment(0xA04C, "Load access/open mode byte", inline=True)
comment(0xA04F, "Rotate right: check bit 0", inline=True)
comment(0xA050, "Carry set (bit 0): check read permission", inline=True)
comment(0xA052, "Rotate right: check bit 1", inline=True)
comment(0xA053, "Carry clear (no write): skip", inline=True)
comment(0xA055, "Test bit 7 of fs_data_count (lock flag)", inline=True)
comment(0xA058, "Not locked: skip", inline=True)
comment(0xA05A, "Transfer Y to A (flags)", inline=True)
comment(0xA05B, "Set bit 5 (locked file flag)", inline=True)
comment(0xA05D, "Transfer back to Y", inline=True)
comment(0xA05E, "Pull handle from stack", inline=True)
comment(0xA05F, "Allocate FCB slot for channel", inline=True)
comment(0xA062, "Transfer to X", inline=True)
comment(0xA063, "Transfer Y to A (flags)", inline=True)
comment(0xA064, "Store flags in FCB table fcb_flags", inline=True)
comment(0xA067, "Transfer X back to A (handle)", inline=True)
comment(0xA068, "Jump to finalise and return", inline=True)
comment(0xA06B, "Process all matching FCBs", inline=True)
comment(0xA06E, "Transfer Y to A", inline=True)
comment(0xA06F, "Non-zero channel: close specific", inline=True)
comment(0xA071, "Load FS options pointer low", inline=True)
comment(0xA073, "Push (save for restore)", inline=True)
comment(0xA074, "A=&77: OSBYTE close spool/exec files", inline=True)
comment(0xA076, "Close any *SPOOL and *EXEC files", inline=True)
comment(0xA079, "Pull saved options pointer", inline=True)
comment(0xA07A, "Restore FS options pointer", inline=True)
comment(0xA07C, "A=0: clear flags", inline=True)
comment(0xA082, "ALWAYS branch to send close request", inline=True)
comment(0xA084, "Validate channel character", inline=True)
comment(0xA08A, "Store as fs_cmd_data (file handle)", inline=True)
comment(0xA08D, "X=1: argument size", inline=True)
comment(0xA08F, "Y=7: close file command", inline=True)
comment(0xA091, "Send close file request", inline=True)
comment(0xA098, "Clear V flag", inline=True)
comment(0xA099, "Scan and clear all FCB flags", inline=True)
comment(0xA09C, "Return with last flag", inline=True)
comment(0xA09F, "A=0: clear FCB entry", inline=True)
comment(0xA0A4, "Clear hazel_fcb_state_byte for slot Y", inline=True)
comment(0xA0AF, "X==4 path: Y < 4?", inline=True)
comment(0xA0B1, "Yes: send OSARGS request via TXCB", inline=True)
comment(0xA0B6, "Store Y as hazel_fs_messages_flag (display control)", inline=True)
comment(0xA0C3, "Y=&16: TXCB function code (OSARGS request)", inline=True)
comment(0xA0C8, "Reload Y from fs_block_offset", inline=True)
comment(0xA0CD, "No error (positive): tail to done_close", inline=True)
comment(0xA10B, "Verify workspace checksum", inline=True)
comment(0xA10E, "Push checksum-verify result -- preserve it across "
    "the FCB lookups below", inline=True)
comment(0xA10F, "Load block offset", inline=True)
comment(0xA111, "Push block offset", inline=True)
comment(0xA112, "Store X in cur_chan_attr", inline=True)
comment(0xA115, "Find matching FCB entry", inline=True)
comment(0xA118, "Zero: no match found", inline=True)
comment(0xA11A, "Load FCB low byte from fcb_count_lo", inline=True)
comment(0xA11D, "Compare with stored offset fcb_buf_offset", inline=True)
comment(0xA120, "FCB lo-byte below stored offset -> not the matching "
    "FCB; mark_not_found", inline=True)
comment(0xA122, "X=&FF: mark as found (all bits set)", inline=True)
comment(0xA124, "ALWAYS branch (negative)", inline=True)
comment(0xA126, "X=0: mark as not found", inline=True)
comment(0xA128, "Restore block offset from stack", inline=True)
comment(0xA12A, "Restore result from stack", inline=True)
comment(0xA12B, "Return", inline=True)
comment(0xA12C, "Y=9: FS options offset for high address", inline=True)
comment(0xA12E, "Add workspace values to FS options", inline=True)
comment(0xA131, "Y=1: FS options offset for low address", inline=True)
comment(0xA134, "X=&FC: loop counter (-4 to -1)", inline=True)
comment(0xA136, "Load FS options byte at offset Y", inline=True)
comment(0xA138, "Test fs_load_addr_2 bit 7 (add/subtract)", inline=True)
comment(0xA13C, "Add workspace byte to FS options", inline=True)
comment(0xA142, "Subtract workspace byte from FS options", inline=True)
comment(0xA145, "Store result back to FS options", inline=True)
comment(0xA147, "Advance to next byte", inline=True)
comment(0xA148, "Advance counter", inline=True)
comment(0xA149, "Loop until 4 bytes processed", inline=True)
comment(0xA14B, "Return", inline=True)
comment(0xA14C, "Verify workspace checksum", inline=True)
comment(0xA14F, "Set up transfer parameters", inline=True)
comment(0xA152, "Push transfer type on stack", inline=True)
comment(0xA153, "Set owner-only access mask", inline=True)
comment(0xA156, "Pull transfer type", inline=True)
comment(0xA157, "Transfer to X", inline=True)
comment(0xA158, "Zero: no valid operation, return", inline=True)
comment(0xA15A, "Decrement (convert 1-based to 0-based)", inline=True)
comment(0xA15B, "Compare with 8 (max operation)", inline=True)
comment(0xA15D, "Below 8: valid operation", inline=True)
comment(0xA15F, "Out of range: return with flag", inline=True)
comment(0xA162, "Transfer operation code to A", inline=True)
comment(0xA163, "Y=0: buffer offset", inline=True)
comment(0xA165, "Push operation code", inline=True)
comment(0xA166, "Compare with 4 (write operations)", inline=True)
comment(0xA168, "Below 4: read operation", inline=True)
comment(0xA16A, "4 or above: write data block", inline=True)
comment(0xA16D, "Load channel handle from FS options", inline=True)
comment(0xA16F, "Push handle", inline=True)
comment(0xA170, "Check file is not a directory", inline=True)
comment(0xA173, "Pull handle", inline=True)
comment(0xA174, "Transfer to Y", inline=True)
comment(0xA175, "Process all matching FCBs", inline=True)
comment(0xA178, "Load FCB flag byte from fcb_net_or_port", inline=True)
comment(0xA17B, "Store file handle in fs_cmd_data", inline=True)
comment(0xA17E, "A=0: clear direction flag", inline=True)
comment(0xA180, "Store in fs_func_code", inline=True)
comment(0xA183, "Load FCB low byte (position)", inline=True)
comment(0xA186, "Store in fs_data_count", inline=True)
comment(0xA189, "Load FCB high byte", inline=True)
comment(0xA18C, "Store in fs_reply_cmd", inline=True)
comment(0xA18F, "Load FCB extent byte", inline=True)
comment(0xA192, "Store in fs_load_vector", inline=True)
comment(0xA195, "Y=&0D: TX buffer size", inline=True)
comment(0xA197, "X=5: argument count", inline=True)
comment(0xA199, "Send TX control block to server", inline=True)
comment(0xA19C, "Pull operation code", inline=True)
comment(0xA19D, "Set up transfer workspace", inline=True)
comment(0xA1A0, "Save flags (carry from setup)", inline=True)
comment(0xA1A1, "Y=0: index for channel handle", inline=True)
comment(0xA1A3, "Load channel handle from FS options", inline=True)
comment(0xA1A5, "Carry set (write): set active", inline=True)
comment(0xA1A7, "Read: clear connection active", inline=True)
comment(0xA1AA, "Branch to continue (always positive)", inline=True)
comment(0xA1AC, "Write: set connection active", inline=True)
comment(0xA1AF, "Clear fs_func_code (Y=0)", inline=True)
comment(0xA1B2, "Look up channel slot data", inline=True)
comment(0xA1B5, "Store flag byte in fs_cmd_data", inline=True)
comment(0xA1B8, "Y=&0C: TX buffer size (short)", inline=True)
comment(0xA1BA, "X=2: argument count", inline=True)
comment(0xA1BC, "Send TX control block", inline=True)
comment(0xA1BF, "Look up channel entry at Y=0", inline=True)
comment(0xA1C2, "Y=9: FS options offset for position", inline=True)
comment(0xA1C4, "Load new position low from fs_cmd_data", inline=True)
comment(0xA1C7, "Update FCB low byte in fcb_count_lo", inline=True)
comment(0xA1CA, "Store in FS options at Y=9", inline=True)
comment(0xA1CC, "Y=&0A", inline=True)
comment(0xA1CD, "Load new position high from fs_func_code", inline=True)
comment(0xA1D0, "Update FCB high byte in fcb_attr_or_count_mid", inline=True)
comment(0xA1D3, "Store in FS options at Y=&0A", inline=True)
comment(0xA1D5, "Y=&0B", inline=True)
comment(0xA1D6, "Load new extent from fs_data_count", inline=True)
comment(0xA1D9, "Update FCB extent in fcb_station_or_count_hi", inline=True)
comment(0xA1DC, "Store in FS options at Y=&0B", inline=True)
comment(0xA1DE, "A=0: clear high byte of extent", inline=True)
comment(0xA1E0, "Y=&0C", inline=True)
comment(0xA1E1, "Store zero in FS options at Y=&0C", inline=True)
comment(0xA1E3, "Restore flags", inline=True)
comment(0xA1E4, "Carry clear: skip last-byte check", inline=True)
comment(0xA1E6, "Load last-byte-of-transfer flag", inline=True)
comment(0xA1E8, "Is transfer still pending (flag=3)?", inline=True)
comment(0xA1EA, "A=0: success", inline=True)
comment(0xA1EC, "Jump to finalise and return", inline=True)
comment(0xA1EF, "Y=0: offset for channel handle", inline=True)
comment(0xA1F1, "Load channel handle from FS options", inline=True)
comment(0xA1F3, "Look up channel by character", inline=True)
comment(0xA1F6, "Load slot-attribute byte from hazel_fcb_slot_attr,X", inline=True)
comment(0xA1F9, "Return with flag in A", inline=True)
comment(0xA1FA, "Push operation code on stack", inline=True)
comment(0xA1FB, "Look up channel entry at Y=0", inline=True)
comment(0xA1FE, "Store flag byte in fs_cmd_data", inline=True)
comment(0xA201, "Y=&0B: source offset in FS options", inline=True)
comment(0xA203, "X=6: copy 6 bytes", inline=True)
comment(0xA205, "Load FS options byte", inline=True)
comment(0xA207, "Store in fs_func_code buffer", inline=True)
comment(0xA20A, "Decrement source index", inline=True)
comment(0xA20B, "Skip offset 8?", inline=True)
comment(0xA20D, "No: continue copy", inline=True)
comment(0xA20F, "Skip offset 8 (hole in structure)", inline=True)
comment(0xA210, "Decrement destination counter", inline=True)
comment(0xA211, "Loop until all 6 bytes copied", inline=True)
comment(0xA213, "Pull operation code", inline=True)
comment(0xA214, "Shift right: check bit 0 (direction)", inline=True)
comment(0xA215, "Push updated code", inline=True)
comment(0xA216, "Carry clear: OSBGET (read)", inline=True)
comment(0xA218, "Carry set: OSBPUT (write), X=1", inline=True)
comment(0xA219, "Store direction flag in fs_func_code", inline=True)
comment(0xA21C, "Y=&0B: TX buffer size", inline=True)
comment(0xA21E, "X=&91: port for OSBGET", inline=True)
comment(0xA220, "Pull operation code", inline=True)
comment(0xA221, "Push back (keep on stack)", inline=True)
comment(0xA222, "Zero (OSBGET): keep port &91", inline=True)
comment(0xA224, "X=&92: port for OSBPUT", inline=True)
comment(0xA226, "Y=&0A: adjusted buffer size", inline=True)
comment(0xA227, "Store port in fs_cmd_urd", inline=True)
comment(0xA22A, "Store port in fs_error_ptr", inline=True)
comment(0xA22C, "X=8: argument count", inline=True)
comment(0xA22E, "Load file handle from fs_cmd_data", inline=True)
comment(0xA231, "Send request (no write data)", inline=True)
comment(0xA234, "X=0: index", inline=True)
comment(0xA236, "Load channel handle from FS options", inline=True)
comment(0xA238, "Transfer to X as index", inline=True)
comment(0xA239, "Load FCB flags from fcb_flags", inline=True)
comment(0xA23C, "Toggle bit 0 (transfer direction)", inline=True)
comment(0xA23E, "Store updated flags", inline=True)
comment(0xA241, "Clear carry for addition", inline=True)
comment(0xA242, "X=4: process 4 address bytes", inline=True)
comment(0xA244, "Load FS options address byte", inline=True)
comment(0xA246, "Store in zero page address area", inline=True)
comment(0xA249, "Store in TXCB position", inline=True)
comment(0xA24C, "Advance Y by 4", inline=True)
comment(0xA24F, "Add offset from FS options", inline=True)
comment(0xA251, "Store computed end address", inline=True)
comment(0xA254, "Retreat Y by 3 for next pair", inline=True)
comment(0xA257, "Decrement byte counter", inline=True)
comment(0xA258, "Loop for all 4 address bytes", inline=True)
comment(0xA25A, "X=1 (INX from 0)", inline=True)
comment(0xA25B, "Load offset from fs_cmd_csd", inline=True)
comment(0xA25E, "Copy to fs_func_code", inline=True)
comment(0xA261, "Decrement counter", inline=True)
comment(0xA262, "Loop until both bytes copied", inline=True)
comment(0xA264, "Pull operation code", inline=True)
comment(0xA265, "Non-zero (OSBPUT): swap addresses", inline=True)
comment(0xA267, "Load port from fs_cmd_urd", inline=True)
comment(0xA26A, "Check and set up TXCB", inline=True)
comment(0xA26D, "Carry set: skip swap", inline=True)
comment(0xA26F, "Send TXCB and swap start/end addresses", inline=True)
comment(0xA272, "Receive and process reply", inline=True)
comment(0xA275, "Store result in fs_load_addr_2", inline=True)
comment(0xA277, "Update addresses from offset 9", inline=True)
comment(0xA27A, "Decrement fs_load_addr_2", inline=True)
comment(0xA27C, "Set carry for subtraction", inline=True)
comment(0xA27D, "Adjust FS options by 4 bytes", inline=True)
comment(0xA280, "Shift fs_cmd_data left (update status)", inline=True)
comment(0xA283, "Return", inline=True)
comment(0xA284, "Save flags before reply processing", inline=True)
comment(0xA285, "Process server reply", inline=True)
comment(0xA288, "Restore flags after reply processing", inline=True)
comment(0xA289, "Return", inline=True)
comment(0xA28A, "Y=&15: TX buffer size for OSBPUT data", inline=True)
comment(0xA28C, "Send TX control block", inline=True)
comment(0xA28F, "Load display flag from hazel_fs_flags", inline=True)
comment(0xA292, "Store in hazel_txcb_byte_16", inline=True)
comment(0xA295, "Clear fs_load_addr (X=0)", inline=True)
comment(0xA297, "Clear fs_load_addr_hi", inline=True)
comment(0xA299, "A=&12: byte count for data block", inline=True)
comment(0xA29B, "Store in fs_load_addr_2", inline=True)
comment(0xA29D, "ALWAYS branch to write data block", inline=True)
comment(0xA29F, "Y=4: offset for station comparison", inline=True)
comment(0xA2A1, "Load stored station from tube_present", inline=True)
comment(0xA2A4, "Zero: skip station check", inline=True)
comment(0xA2A6, "Compare with FS options station", inline=True)
comment(0xA2A8, "Mismatch: skip subtraction", inline=True)
comment(0xA2AA, "Y=3", inline=True)
comment(0xA2AB, "Subtract FS options value", inline=True)
comment(0xA2AD, "Store result in svc_state", inline=True)
comment(0xA2AF, "Load FS options byte at Y", inline=True)
comment(0xA2B1, "Store in workspace at fs_last_byte_flag+Y", inline=True)
comment(0xA2B4, "Decrement index", inline=True)
comment(0xA2B5, "Loop until all bytes copied", inline=True)
comment(0xA2B7, "Pull operation code", inline=True)
comment(0xA2B8, "Mask to 2-bit sub-operation", inline=True)
comment(0xA2BA, "Zero: send OSBPUT data", inline=True)
comment(0xA2BC, "Shift right: check bit 0", inline=True)
comment(0xA2BD, "Zero (bit 0 clear): handle read", inline=True)
comment(0xA2BF, "Carry set: handle catalogue update", inline=True)
comment(0xA2C1, "Transfer to Y (Y=0)", inline=True)
comment(0xA2C2, "Load data byte from fs_csd_handle", inline=True)
comment(0xA2C5, "Store in fs_cmd_csd", inline=True)
comment(0xA2C8, "Load high data byte from fs_lib_handle", inline=True)
comment(0xA2CB, "Store in fs_cmd_lib", inline=True)
comment(0xA2CE, "Load port from fs_urd_handle", inline=True)
comment(0xA2D1, "Store in fs_cmd_urd", inline=True)
comment(0xA2D4, "X=&12: buffer size marker", inline=True)
comment(0xA2D6, "Store in fs_cmd_y_param", inline=True)
comment(0xA2D9, "A=&0D: count value", inline=True)
comment(0xA2DB, "Store in fs_func_code", inline=True)
comment(0xA2DE, "Store in fs_load_addr_2", inline=True)
comment(0xA2E0, "Shift right (A=6)", inline=True)
comment(0xA2E1, "Store in fs_cmd_data", inline=True)
comment(0xA2E4, "Clear carry for addition", inline=True)
comment(0xA2E5, "Prepare and send TX control block", inline=True)
comment(0xA2E8, "Store X in fs_load_addr_hi (X=0)", inline=True)
comment(0xA2EA, "X=1 (after INX)", inline=True)
comment(0xA2EB, "Store X in fs_load_addr", inline=True)
comment(0xA2ED, "Load svc_state (tube flag)", inline=True)
comment(0xA2EF, "Non-zero: write via tube", inline=True)
comment(0xA2F1, "Load source index from fs_load_addr", inline=True)
comment(0xA2F3, "Load destination index from fs_load_addr_hi", inline=True)
comment(0xA2F5, "Load data byte from fs_cmd_data buffer", inline=True)
comment(0xA2F8, "Store to destination via fs_crc pointer", inline=True)
comment(0xA2FA, "Advance source index", inline=True)
comment(0xA2FB, "Advance destination index", inline=True)
comment(0xA2FC, "Decrement byte counter", inline=True)
comment(0xA2FE, "Loop until all bytes transferred", inline=True)
comment(0xA305, "A=1: tube transfer type (write)", inline=True)
comment(0xA307, "Load destination low from fs_options", inline=True)
comment(0xA30C, "No wrap: skip high increment", inline=True)
comment(0xA30F, "Set up tube transfer address", inline=True)
comment(0xA314, "Load data byte from buffer", inline=True)
comment(0xA317, "Write to tube data register 3", inline=True)
comment(0xA31A, "Advance source index", inline=True)
comment(0xA31B, "Y=6: tube write delay", inline=True)
comment(0xA31D, "Delay loop: decrement Y", inline=True)
comment(0xA320, "Decrement byte counter", inline=True)
comment(0xA324, "A=&83: release tube claim", inline=True)
comment(0xA326, "Release tube", inline=True)
comment(0xA329, "Jump to clear A and finalise return", inline=True)
comment(0xA32C, "Y=9: offset for position byte", inline=True)
comment(0xA330, "Store in fs_func_code", inline=True)
comment(0xA333, "Y=5: offset for extent byte", inline=True)
comment(0xA335, "Load extent byte from FS options", inline=True)
comment(0xA337, "Store in fs_data_count", inline=True)
comment(0xA33A, "X=&0D: byte count", inline=True)
comment(0xA33C, "Store in fs_reply_cmd", inline=True)
comment(0xA33F, "Y=2: command sub-type", inline=True)
comment(0xA343, "Store in fs_cmd_data", inline=True)
comment(0xA346, "Y=3: TX buffer command byte", inline=True)
comment(0xA34C, "Load data offset from fs_func_code", inline=True)
comment(0xA34F, "Store as first byte of FS options", inline=True)
comment(0xA351, "Load data count from fs_cmd_data", inline=True)
comment(0xA354, "Y=9: position offset in FS options", inline=True)
comment(0xA356, "Add to current position", inline=True)
comment(0xA358, "Store updated position", inline=True)
comment(0xA35A, "Load TXCB end byte", inline=True)
comment(0xA35C, "Subtract 7 (header overhead)", inline=True)
comment(0xA35E, "Store remaining data size", inline=True)
comment(0xA361, "Store in fs_load_addr_2 (byte count)", inline=True)
comment(0xA363, "Zero bytes: skip write", inline=True)
comment(0xA365, "Write data block to host/tube", inline=True)
comment(0xA368, "X=2: clear 3 bytes (indices 0-2)", inline=True)
comment(0xA36A, "Clear fs_data_count+X", inline=True)
comment(0xA36D, "Decrement index", inline=True)
comment(0xA36E, "Loop until all cleared", inline=True)
comment(0xA370, "Update addresses from offset 1", inline=True)
comment(0xA373, "Set carry for subtraction", inline=True)
comment(0xA374, "Decrement fs_load_addr_2", inline=True)
comment(0xA376, "Load data count from fs_cmd_data", inline=True)
comment(0xA379, "Copy to fs_func_code", inline=True)
comment(0xA37C, "Adjust FS options by 4 bytes (subtract)", inline=True)
comment(0xA37F, "X=3: check 4 bytes", inline=True)
comment(0xA381, "Y=5: starting offset", inline=True)
comment(0xA383, "Set carry for comparison", inline=True)
comment(0xA384, "Load FS options byte", inline=True)
comment(0xA386, "Non-zero: more data remaining", inline=True)
comment(0xA388, "Advance to next byte", inline=True)
comment(0xA389, "Decrement counter", inline=True)
comment(0xA38A, "Loop until all bytes checked", inline=True)
comment(0xA38C, "All zero: clear carry (transfer complete)", inline=True)
comment(0xA38D, "Jump to update catalogue and return", inline=True)
comment(0xA390, "A=&C3: tube claim protocol", inline=True)
comment(0xA392, "Dispatch tube address/data claim", inline=True)
comment(0xA395, "Carry clear: claim failed, retry", inline=True)
comment(0xA397, "Return (tube claimed)", inline=True)
comment(0xA49F, "CR (carriage return)", inline=True)
comment(0xA517, "Increment handle byte", inline=True)
comment(0xA51C, "Non-zero: handle valid, execute", inline=True)
comment(0xA52D, "X=2", inline=True)
comment(0xA533, "Send re-open request", inline=True)
comment(0xA53B, "Jump to finalise and return", inline=True)
comment(0xA545, "Load library flag byte", inline=True)
comment(0xA548, "Bit 7 set: library already tried", inline=True)
comment(0xA54E, "Carry set: bad command", inline=True)
comment(0xA553, "Load filename byte", inline=True)
comment(0xA55A, "Shift filename right by 8 bytes", inline=True)
comment(0xA55D, "Store shifted byte", inline=True)
comment(0xA565, "Copy 'Library.' prefix", inline=True)
comment(0xA568, "Store prefix byte", inline=True)
comment(0xA56C, "Loop until prefix copied", inline=True)
comment(0xA56E, "Load library flag", inline=True)
comment(0xA576, "Retry file open with library path", inline=True)
comment(0xA57B, "Load backup byte", inline=True)
comment(0xA583, "No: continue restoring", inline=True)
comment(0xA585, "Set owner-only access mask", inline=True)
comment(0xA5AE, "X=3: check 4 execution bytes", inline=True)
comment(0xA5B0, "Increment execution address byte", inline=True)
comment(0xA5B6, "Loop until all checked", inline=True)
comment(0xA5BA, "Generate 'No!' error", inline=True)
comment(0xA5C6, "Allocate FCB slot", inline=True)
comment(0xA5CC, "Clear status in channel table", inline=True)
comment(0xA5E2, "Y=0", inline=True)
comment(0xA5F1, "Is it space?", inline=True)
comment(0xA5F3, "Yes: skip it", inline=True)
comment(0xA5F9, "Add to text pointer low", inline=True)
comment(0xA603, "Save text pointer for later", inline=True)
comment(0xA611, "X=&4A: FS command table offset", inline=True)
comment(0xA623, "All &FF?", inline=True)
comment(0xA627, "Claim tube for data transfer", inline=True)
comment(0xA62A, "X=9: parameter count", inline=True)
comment(0xA7A1, "*Access", inline=True)
comment(0xA7A7, "V no arg; syn 9: <obj> (L)(W)(R)...", inline=True)
comment(0xA83C, "CLC so SBC subtracts value+1", inline=True)
comment(0xA83F, "A = OSWORD - &0E (CLC+SBC = -&0E)", inline=True)
comment(0xA841, "Below &0E: not ours, return", inline=True)
comment(0xA843, "Index >= 7? (OSWORD > &14)", inline=True)
comment(0xA845, "Above &14: not ours, return", inline=True)
comment(0xA847, "X=OSWORD handler index (0-6)", inline=True)
comment(0xA848, "Y=6: save 6 workspace bytes", inline=True)
comment(0xA84D, "Save on stack", inline=True)
comment(0xA84E, "Load OSWORD parameter byte", inline=True)
comment(0xA851, "Copy parameter to workspace", inline=True)
comment(0xA857, "Set up dispatch and save state", inline=True)
comment(0xA85A, "Y=&FA: restore 6 workspace bytes", inline=True)
comment(0xA85C, "Restore saved workspace byte", inline=True)
comment(0xA85D, "Store to osword_flag workspace", inline=True)
comment(0xA860, "Next byte", inline=True)
comment(0xA861, "Loop until all 6 restored", inline=True)
comment(0xA863, "Return from svc_8_osword", inline=True)
comment(0xA864, "X = OSWORD index (0-6)", inline=True)
comment(0xA868, "Load handler address low byte", inline=True)
comment(0xA86C, "Copy 3 bytes (Y=2,1,0)", inline=True)
comment(0xA86E, "Load from osword_flag workspace", inline=True)
comment(0xA870, "RTS dispatches to pushed handler", inline=True)
comment(0xA888, "Restore A (OSWORD sub-code)", inline=True)
comment(0xA88C, "Other sub-codes: set state = 8", inline=True)
comment(0xA88E, "Store service state", inline=True)
comment(0xA890, "Return", inline=True)
comment(0xA891, "X=0: start of TX control block", inline=True)
comment(0xA893, "Y=&10: length of TXCB to save", inline=True)
comment(0xA895, "Save current TX control block", inline=True)
comment(0xA898, "Load seconds from clock workspace", inline=True)
comment(0xA89B, "Convert binary to BCD", inline=True)
comment(0xA89E, "Store BCD seconds", inline=True)
comment(0xA8A1, "Load minutes from clock workspace", inline=True)
comment(0xA8A4, "Convert binary to BCD", inline=True)
comment(0xA8A7, "Store BCD minutes", inline=True)
comment(0xA8AA, "Load hours from clock workspace", inline=True)
comment(0xA8AD, "Convert binary to BCD", inline=True)
comment(0xA8B0, "Store BCD hours", inline=True)
comment(0xA8B3, "Clear hours high position", inline=True)
comment(0xA8B5, "Store zero", inline=True)
comment(0xA8B8, "Load day+month byte", inline=True)
comment(0xA8BB, "Save for later high nibble extract", inline=True)
comment(0xA8BC, "Load day value", inline=True)
comment(0xA8BF, "Convert day to BCD", inline=True)
comment(0xA8C2, "Store BCD day", inline=True)
comment(0xA8C5, "Restore day+month byte", inline=True)
comment(0xA8C7, "Mask low nibble (month low bits)", inline=True)
comment(0xA8C9, "Convert to BCD", inline=True)
comment(0xA8CC, "Store BCD month", inline=True)
comment(0xA8D0, "Shift high nibble down", inline=True)
comment(0xA8D3, "4th shift: isolate high nibble", inline=True)
comment(0xA8D6, "Convert year to BCD", inline=True)
comment(0xA8D9, "Store BCD year", inline=True)
comment(0xA8DC, "Copy 7 bytes (Y=6 down to 0)", inline=True)
comment(0xA8DE, "Load BCD byte from workspace", inline=True)
comment(0xA8E1, "Store to parameter block", inline=True)
comment(0xA8E3, "Next byte down", inline=True)
comment(0xA8E4, "Loop for all 7 bytes", inline=True)
comment(0xA9CF, "Y=2: copy 2 bytes", inline=True)
comment(0xA9D1, "Load station byte", inline=True)
comment(0xA9D4, "Store to PB[Y]", inline=True)
comment(0xA9D7, "Loop for bytes 2..1", inline=True)
comment(0xA9D9, "Return", inline=True)
comment(0xA9DD, "Y=0 for process_all_fcbs", inline=True)
comment(0xA9DF, "Close all open FCBs", inline=True)
comment(0xA9E2, "Y=2: copy 2 bytes", inline=True)
comment(0xA9E4, "Load new station byte from PB", inline=True)
comment(0xA9E6, "Store to fs_server_base", inline=True)
comment(0xA9EA, "Loop for bytes 2..1", inline=True)
comment(0xA9EC, "Clear handles if station matches", inline=True)
comment(0xA9FB, "Load FCB flags", inline=True)
comment(0xA9FE, "Save flags in Y", inline=True)
comment(0xA9FF, "Test bit 1 (FCB allocated?)", inline=True)
comment(0xAA01, "No: skip to next entry", inline=True)
comment(0xAA06, "Store updated flags", inline=True)
comment(0xAA09, "Save in Y", inline=True)
comment(0xAA0A, "Does FCB match new station?", inline=True)
comment(0xAA0D, "No match: skip to next", inline=True)
comment(0xAA10, "Restore flags", inline=True)
comment(0xAA11, "Test bit 2 (handle 1 active?)", inline=True)
comment(0xAA13, "No: check handle 2", inline=True)
comment(0xAA15, "Restore flags", inline=True)
comment(0xAA16, "Set bit 5 (handle reassigned)", inline=True)
comment(0xAA19, "Get FCB high byte", inline=True)
comment(0xAA1C, "Store as handle 1 station", inline=True)
comment(0xAA1F, "FCB index", inline=True)
comment(0xAA20, "Add &20 for FCB table offset", inline=True)
comment(0xAA22, "Store as handle 1 FCB index", inline=True)
comment(0xAA2A, "Y still holds the saved FCB status -- TYA so we "
    "can re-test bit 3 (handle-2 active flag)", inline=True)
comment(0xAA2B, "Test bit 3 (handle 2 active?)", inline=True)
comment(0xAA2D, "No: check handle 3", inline=True)
comment(0xAA30, "Set bit 5", inline=True)
comment(0xAA33, "Get FCB high byte", inline=True)
comment(0xAA36, "Store as handle 2 station", inline=True)
comment(0xAA39, "FCB index", inline=True)
comment(0xAA3A, "Add &20 for FCB table offset", inline=True)
comment(0xAA3C, "Store as handle 2 FCB index", inline=True)
comment(0xAA45, "Test bit 4 (handle 3 active?)", inline=True)
comment(0xAA47, "No: store final flags", inline=True)
comment(0xAA49, "Restore flags", inline=True)
comment(0xAA4A, "Set bit 5", inline=True)
comment(0xAA4C, "Save updated flags", inline=True)
comment(0xAA4D, "Get FCB high byte", inline=True)
comment(0xAA50, "Store as handle 3 station", inline=True)
comment(0xAA53, "FCB index", inline=True)
comment(0xAA54, "Add &20 for FCB table offset", inline=True)
comment(0xAA56, "Store as handle 3 FCB index", inline=True)
comment(0xAA73, "Skip SEC", inline=True)
comment(0xAA75, "C=1: PB-to-workspace direction", inline=True)
comment(0xAA76, "Workspace offset &17", inline=True)
comment(0xAA7A, "Page from RX pointer high byte", inline=True)
comment(0xAA7C, "Set ws_ptr_hi", inline=True)
comment(0xAA7E, "Y=1: first PB data byte", inline=True)
comment(0xAA80, "X=5: copy 5 bytes", inline=True)
comment(0xAA82, "C=0: skip PB-to-WS copy", inline=True)
comment(0xAA84, "C=1: load from parameter block", inline=True)
comment(0xAA86, "Store to workspace", inline=True)
comment(0xAA88, "Load from workspace", inline=True)
comment(0xAA8A, "Store to parameter block", inline=True)
comment(0xAA8D, "Count down", inline=True)
comment(0xAA8E, "Loop for all bytes", inline=True)
comment(0xAA91, "Load workspace page high byte", inline=True)
comment(0xAA93, "Set ws_ptr_hi", inline=True)
comment(0xAA95, "Y=1", inline=True)
comment(0xAA97, "Set ws_ptr_lo = 1", inline=True)
comment(0xAA99, "X=1: copy 2 bytes", inline=True)
comment(0xAA9B, "Copy via copy_pb_byte_to_ws", inline=True)
comment(0xAA9D, "Y=1: first PB data byte", inline=True)
comment(0xAA9E, "Load PB[1]", inline=True)
comment(0xAAA1, "Store to (nfs_workspace)+2", inline=True)
comment(0xAAA3, "Load PB[2]", inline=True)
comment(0xAAA5, "Y=3", inline=True)
comment(0xAAA6, "Store to (nfs_workspace)+3", inline=True)
comment(0xAAA8, "Reinitialise bridge routing", inline=True)
comment(0xAAAB, "Compare result with workspace", inline=True)
comment(0xAAAD, "Different: leave unchanged", inline=True)
comment(0xAAAF, "Same: clear workspace byte", inline=True)
comment(0xAAB1, "Return", inline=True)
comment(0xAAB2, "Load protection mask", inline=True)
comment(0xAAB5, "Store to PB[1] and return", inline=True)
comment(0xAAB8, "Y=1: PB data offset", inline=True)
comment(0xAAB9, "Load new mask from PB[1]", inline=True)
comment(0xAAC5, "Y=3: copy 3 bytes", inline=True)
comment(0xAAC7, "Load handle byte", inline=True)
comment(0xAACA, "Store to PB[Y]", inline=True)
comment(0xAACC, "Previous byte", inline=True)
comment(0xAACD, "Loop for bytes 3..1", inline=True)
comment(0xAACF, "Return", inline=True)
comment(0xAC2E, "Load bridge response", inline=True)
comment(0xAC30, "Negative: bridge responded", inline=True)
comment(0xAC32, "Advance retry counter by 8", inline=True)
comment(0xAC35, "Positive: retry poll loop", inline=True)
comment(0xAC37, "Set response to &3F (OK)", inline=True)
comment(0xAC39, "Store to workspace", inline=True)
comment(0xAC3B, "Restore saved Y", inline=True)
comment(0xAC3D, "Load bridge status", inline=True)
comment(0xAC40, "X = bridge status", inline=True)
comment(0xAC43, "Status was &FF: return (no bridge)", inline=True)
comment(0xAC45, "Return bridge station in A", inline=True)
comment(0xAC47, "Compare sub-code with 1", inline=True)
comment(0xAC49, "Sub-code >= 1: handle TX request", inline=True)
comment(0xB0A1, "Save command line offset", inline=True)
comment(0xB0A2, "Push onto stack", inline=True)
comment(0xB0D8, "Index 4: threshold 29", inline=True)
comment(0xB0DB, "Index 7: threshold 59", inline=True)
comment(0xBB3A, "X=&F7: save 9 workspace bytes (&F7..&FF)", inline=True)
comment(0xBB3C, "Load workspace byte", inline=True)
comment(0xBB3F, "Push fs_options", inline=True)
comment(0xBB40, "Next byte", inline=True)
comment(0xBB41, "X<0: more bytes to save", inline=True)
comment(0xBB43, "Start from FCB slot &0F", inline=True)
comment(0xBB45, "Store as current FCB index", inline=True)
comment(0xBB48, "Load current FCB index", inline=True)
comment(0xBB4B, "Get filter attribute", inline=True)
comment(0xBB4C, "Zero: process all FCBs", inline=True)
comment(0xBB4E, "Compare with FCB attribute ref", inline=True)
comment(0xBB51, "No match: skip this FCB", inline=True)
comment(0xBB53, "Save filter attribute", inline=True)
comment(0xBB54, "Flush pending data for this FCB", inline=True)
comment(0xBB58, "Previous FCB index", inline=True)
comment(0xBB5B, "More slots: continue loop", inline=True)
comment(0xBB5D, "X=8: restore 9 workspace bytes", inline=True)
comment(0xBB5F, "Restore fs_block_offset", inline=True)
comment(0xBB60, "Restore workspace byte", inline=True)
comment(0xBB62, "Next byte down", inline=True)
comment(0xBB63, "More bytes: continue restoring", inline=True)
comment(0xBC7F, "Load station for this channel", inline=True)
comment(0xBC82, "Save station on stack", inline=True)
comment(0xBC83, "Y=0: reset index", inline=True)
comment(0xBC85, "Save current FCB context", inline=True)
comment(0xBC88, "Restore station from stack", inline=True)
comment(0xBC89, "Store station in command buffer", inline=True)
comment(0xBC8E, "Save station for later restore", inline=True)
comment(0xBC8F, "X=0", inline=True)
comment(0xBC91, "Clear function code", inline=True)
comment(0xBC94, "Load byte count lo from FCB", inline=True)
comment(0xBC97, "Store as data byte count", inline=True)
comment(0xBC9A, "Load byte count mid from FCB", inline=True)
comment(0xBC9D, "Store as reply command byte", inline=True)
comment(0xBCA0, "Load byte count hi from FCB", inline=True)
comment(0xBCA3, "Store as load vector field", inline=True)
comment(0xBCA6, "Y=&0D: TX command byte offset", inline=True)
comment(0xBCA8, "X=5: send 5 bytes", inline=True)
comment(0xBCAA, "Send flush request to server", inline=True)
comment(0xBCAD, "Restore station from stack", inline=True)
comment(0xBCAE, "Y=station for wipe request", inline=True)
comment(0xBCAF, "Load saved data byte", inline=True)
comment(0xBCB2, "Send close/wipe request to server", inline=True)
comment(0xBCB5, "Restore catalog state after flush", inline=True)

# Final bulk gap-cleanup additions (small-count remaining gaps).
comment(0x945E, "Y=0: ensure offset starts from beginning of "
    "TX command buffer", inline=True)
comment(0x9460, "Send the FS command and dispatch the reply",
    inline=True)
comment(0x94C9, "Clear owner-only access bits before parsing",
    inline=True)
comment(0x94CC, "Parse the quoted source filename", inline=True)
comment(0x94CF, "Parse access prefix on the source filename",
    inline=True)
comment(0x94F1, "BRA back to loop_copy_rename", inline=True)
comment(0x9504, "Save loop index across the access parse",
    inline=True)
comment(0x9505, "Parse access prefix on the second filename",
    inline=True)
comment(0x9508, "Restore loop index", inline=True)
comment(0x95BE, "JMP to svc_return_unclaimed (long-distance via "
    "this 3-byte trampoline)", inline=True)
comment(0x9A0E, "A=&C7: OSBYTE 'flush input buffer'", inline=True)
comment(0x9A10, "Tail-call OSBYTE with X=0/Y=0", inline=True)
comment(0xA0FE, "Write CMOS RAM byte (Y) to byte index (X)",
    inline=True)
comment(0xA4EC, "Update hazel_fs_lib_flags with the result", inline=True)
comment(0xA594, "Test hazel_fs_lib_flags bits 6 / 7", inline=True)
comment(0xA597, "Either bit set: this is an invalid command path",
    inline=True)
comment(0xA599, "Otherwise finalise and return", inline=True)
comment(0xA59C, "A=&0B: FSCV reason 11 (filing-system change)",
    inline=True)
comment(0xA59E, "Tail-call FSCV", inline=True)
comment(0xA5DF, "Copy parsed arg to TX buffer with X=0", inline=True)
comment(0xA6DD, "Mark this path as 'success' for the caller",
    inline=True)
comment(0xA6DE, "Load TX result code from hazel_txcb_result",
    inline=True)
comment(0xA6E1, "Store as hazel_fs_flags", inline=True)
comment(0xA9CC, "Ensure NFS is currently the selected FS", inline=True)
comment(0xA9DA, "Ensure NFS is currently the selected FS", inline=True)
comment(0xAA25, "A=2: fs_flags bit 1 mask", inline=True)
comment(0xAA27, "Clear fs_flags bit 1", inline=True)
comment(0xAA3F, "A=4: fs_flags bit 2 mask", inline=True)
comment(0xAA44, "Y still holds the saved FCB status -- TYA so we "
    "can re-test bit 4 (handle-3 active flag)", inline=True)
comment(0xAA41, "Clear fs_flags bit 2", inline=True)
comment(0xAAC2, "Ensure NFS is currently the selected FS", inline=True)
comment(0xAAD0, "Ensure NFS is currently the selected FS", inline=True)
comment(0xAC26, "A=&13: OSBYTE 'wait for VSYNC'", inline=True)
comment(0xAC2B, "Restore caller's X", inline=True)
comment(0xAC4C, "Ensure NFS is currently the selected FS", inline=True)
comment(0xAC4F, "Pop saved A from the stack frame", inline=True)
comment(0xB0FE, "Set OS text pointer and FS-options transfer ptr",
    inline=True)
comment(0xB101, "Y=0: TX-buffer offset for the first byte", inline=True)
comment(0xB16B, "Read hazel_txcb_type (FS reply opcode)", inline=True)
comment(0xB16E, "Non-zero (private library): take the public-label "
    "branch", inline=True)
comment(0xB179, "Non-zero: branch to cat_after_label_print", inline=True)
comment(0xB185, "Read hazel_fs_lib_flags", inline=True)
comment(0xB1A5, "Read hazel_fs_flags", inline=True)
comment(0xB1B1, "Look up option-string offset for index X", inline=True)
comment(0xB1B4, "Look up option byte at the resolved offset",
    inline=True)
comment(0xBB39, "Save Y across the body", inline=True)
comment(0xBC8D, "Save Y again for the next iteration",
    inline=True)

# ============================================================
# Generate disassembly
# ============================================================

import json
import sys

output = go(print_output=False)

_output_dirpath.mkdir(parents=True, exist_ok=True)
output_filepath = _output_dirpath / "anfs-4.21_variant_1.asm"
output_filepath.write_text(output)
print(f"Wrote {output_filepath}", file=sys.stderr)

structured = get_structured()
json_filepath = _output_dirpath / "anfs-4.21_variant_1.json"
json_filepath.write_text(json.dumps(structured))
print(f"Wrote {json_filepath}", file=sys.stderr)
