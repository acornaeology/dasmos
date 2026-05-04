import os
from pathlib import Path

from py8dis.commands import *
import py8dis.acorn as acorn

init(assembler_name="beebasm", lower_case=True)

# Paths are resolved relative to this script's location in the repo
_script_dirpath = Path(__file__).resolve().parent
_version_dirpath = _script_dirpath.parent
_rom_filepath = os.environ.get(
    "FANTASM_ROM",
    str(_version_dirpath / "rom" / "nfs-3.34.rom"),
)
_output_dirpath = Path(os.environ.get(
    "FANTASM_OUTPUT_DIR",
    str(_version_dirpath / "output"),
))

load(0x8000, _rom_filepath, "6502")

# ============================================================
# Relocated code blocks
# ============================================================
# The NFS ROM copies code from ROM into RAM at initialisation (&80C8-&8119).
# These blocks execute at different addresses than their storage locations.
# move(dest, src, length) tells py8dis the runtime address for each block.
#
# The page copy loop (&80F9) starts with Y=0, DEY/BNE wraps through
# &FF..&01 — all 256 bytes of each page are copied.
#
# The workspace init (&8113) copies X=&60 downto 0 (BPL) = 97 bytes.
#
# Vectors set up during init:
#   BRKV  = &0016 (in workspace block — BRK/error handler)
#   RDCHV = &04E7 (in page 4 — RDCH handler)
#   WRCHV = &051C (in page 5 — WRCH handler)
#   EVNTV = &06E8 (in page 6 — event handler)

# BRK handler + NMI workspace init code (&9307 → &0016-&0076)
move(0x0016, 0x9307, 0x61)

# NMI handler / CLI command code (&934C/&944C/&954C → pages &04/&05/&06)
move(0x0400, 0x934C, 0x100)
move(0x0500, 0x944C, 0x100)
move(0x0600, 0x954C, 0x100)

# acorn.bbc() provides: os_text_ptr (&F2), romsel_copy (&F4), osrdsc_ptr (&F6),
# all OS vectors (brkv, wrchv, ..., netv), all OS entry points (osasci, osbyte, ...),
# plus hooks for automatic OSBYTE/OSWORD annotation.
# acorn.is_sideways_rom() provides: rom_header, language_entry, service_entry,
# rom_type, copyright_offset, binary_version, title, language_handler, service_handler.
acorn.bbc()
acorn.is_sideways_rom()

# Split the copyright string classification so the null terminator
# at &8014 becomes a separate item.  This lets error_offsets have its
# own label line rather than being expressed as copyright_string+7.
from py8dis import classification as _cls, disassembly as _disasm
from py8dis.memorymanager import RuntimeAddr as _RuntimeAddr
from py8dis.movemanager import r2b as _r2b
_copyright_bin = _r2b(_RuntimeAddr(0x800D))[0]
_disasm.classifications[_copyright_bin] = _cls.String(7)       # "(C)ROFF"
_disasm.classifications[_copyright_bin + 7] = _cls.Byte(1)     # null terminator

# ============================================================
# Hardware registers
# ============================================================

# MC6854 ADLC registers (active at &FEA0-&FEA3 when active Econet station)
constant(0xFEA0, "adlc_cr1")   # Write: CR1 (or CR3 if AC=1). Read: SR1
constant(0xFEA1, "adlc_cr2")   # Write: CR2 (or CR4 if AC=1). Read: SR2
constant(0xFEA2, "adlc_tx")    # Write: TX FIFO (continue frame). Read: RX FIFO
constant(0xFEA3, "adlc_tx2")   # Write: TX FIFO (last byte, terminates frame). Read: RX FIFO

# Econet hardware on the 1MHz bus
constant(0xFE18, "econet_station_id")  # Read: station DIP switches AND INTOFF (disable NMIs)
constant(0xFE20, "econet_nmi_enable")  # Read: INTON (re-enable NMIs). Any read &FE20-&FE23.

# Tube ULA registers (&FEE0-&FEE7) — named by acorn.bbc()
# R1 (&FEE0/&FEE1): events and escape signalling (host↔parasite)
# R2 (&FEE2/&FEE3): command bytes and general data transfer
# R4 (&FEE6/&FEE7): one-byte transfers (error codes, BRK signalling)

# Key ADLC register values (from original disassembly annotations):
#   CR1=&C1: full reset (TX_RESET|RX_RESET|AC)
#   CR1=&82: RX listen (TX_RESET|RIE)
#   CR1=&44: TX active (RX_RESET|TIE)
#   CR2=&67: clear all status (CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)
#   CR2=&E7: TX prepare (RTS|CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)
#   CR2=&3F: TX last data (CLR_RX_ST|TX_LAST_DATA|FLAG_IDLE|FC_TDRA|2_1_BYTE|PSE)
#   CR2=&A7: TX in handshake (RTS|CLR_TX_ST|FC_TDRA|2_1_BYTE|PSE)

# ============================================================
# Protocol constants from DNFS 3.60 reference (NFS00)
# ============================================================

# Econet port numbers (FS protocol version 2)
# Ports are allocated above &B0 to leave &01-&AA free for user applications.
# The low 3 bits of the TXCB flag byte encode error reasons and index into
# the error message table (ERRTAB) at &84AF.
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
constant(0xA4, "err_tx_cb_error")     # TXCBER: TX control block error
constant(0xA5, "err_no_reply")        # NOREPE: no reply from server
constant(0xA8, "err_fs_cutoff")       # ERRCUT: FS errors >= this are FS-specific

# Protocol flags
constant(0x80, "tx_flag")             # TXFLAG: OR with flag byte before transmit
constant(0x7F, "rx_ready")            # RXRDY: flag byte value for reception ready

# FS handle base and retry count
constant(0x20, "handle_base")         # HAND: base value for file handles (&20-&27)

# Control block template markers
constant(0xFE, "cb_stop")             # CBSTOP: stop copying in ctrl_block_setup
constant(0xFD, "cb_skip")             # CBSKIP: skip this byte (leave unchanged)
constant(0xFC, "cb_fill")             # CBFILL: substitute page byte of pointer

# ============================================================
# Inline string subroutine hook
# ============================================================
# print_inline (&853B) prints an inline string following the JSR, terminated by a
# byte with bit 7 set. The high-bit byte is the opcode of the next
# instruction — the routine jumps there via JMP (fs_load_addr).
hook_subroutine(0x853b, "print_inline", stringhi_hook)

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
# From J.G. Harston's NFSWorkSp and mdfs.net/Docs/Comp/BBC/AllMem

label(0x97, "escapable")           # b7=respond to Escape flag
label(0x98, "need_release_tube")   # b7=need to release Tube
label(0x9A, "net_tx_ptr")          # NetTx control block pointer (low)
label(0x9B, "net_tx_ptr_hi")       # NetTx control block pointer (high)
label(0x9C, "net_rx_ptr")          # NetRx control blocks pointer (low)
label(0x9D, "net_rx_ptr_hi")       # NetRx control blocks pointer (high)
label(0x9E, "nfs_workspace")       # General NFS workspace pointer (low)
label(0x9F, "nfs_workspace_hi")    # General NFS workspace pointer (high)
label(0xA0, "nmi_tx_block")        # Block to be transmitted (low)
label(0xA1, "nmi_tx_block_hi")     # Block to be transmitted (high)
label(0xA2, "port_buf_len")        # Open port buffer length (low)
label(0xA3, "port_buf_len_hi")     # Open port buffer length (high)
label(0xA4, "open_port_buf")       # Open port buffer address (low)
label(0xA5, "open_port_buf_hi")    # Open port buffer address (high)
label(0xA6, "port_ws_offset")      # Port workspace offset
label(0xA7, "rx_buf_offset")       # Receive buffer offset

# ============================================================
# Zero page — Filing system workspace (&B0-&CF)
# ============================================================
# NFS zero-page layout from DNFS 3.60 source (NFS00):
#   &B0-&B3  WORK    4-byte variable workspace (load/exec/size)
#   &B4-&B7  (WORK+4) additional workspace (address compare target)
#   &B8      JWORK   3 bytes for timing (also CRFLAG at &B9, SPOOL1 at &BA)
#   &BB      TEMPX   register save: X (also used as options pointer low)
#   &BC      TEMPY   register save: Y (also options pointer high)
#   &BD      TEMPA   register save: A (also last-byte flag)
#   &BE-&BF  POINTR  generic 2-byte pointer (filename, workspace)
#   &C0-&CE  TXCB/RXCB overlapping TX/RX control blocks (15 bytes)
#   &CF      SPOOL0  spool file handle
# NB: &CD-&CE noted as "two bytes free" in original source.

label(0xB0, "fs_load_addr")        # WORK: load/start address (4 bytes)
label(0xB1, "fs_load_addr_hi")
label(0xB2, "fs_load_addr_2")
label(0xB8, "fs_error_ptr")        # JWORK: error pointer / timing workspace
label(0xBB, "fs_options")          # TEMPX: options/control block pointer (low)
label(0xBC, "fs_block_offset")     # TEMPY: block offset / control block pointer (high)
label(0xBD, "fs_last_byte_flag")   # TEMPA: b7=last byte from block / saved A
label(0xBE, "fs_crc_lo")           # POINTR: generic pointer (low)
label(0xBF, "fs_crc_hi")           # POINTR+1: generic pointer (high)
label(0xCD, "nfs_temp")             # General-purpose NFS temporary (free zero-page byte)
label(0xCE, "rom_svc_num")         # ROM service number (7=osbyte, 8=osword)

# Zero page — Additional OS locations
label(0x10, "zp_temp_10")          # Temporary storage (Y save during service calls)
label(0x11, "zp_temp_11")          # Temporary storage (X save during service calls)
label(0x16, "nmi_workspace_start") # Start of NMI workspace area (&0016-&0076)
label(0x63, "zp_63")               # Used by NFS

# ============================================================
# Page &0D — NMI handler workspace (&0D00-&0D67)
# ============================================================
# The NMI shim code occupies &0D00-&0D1F. Workspace follows at &0D20.
# From J.G. Harston's PageD (mdfs.net/Misc/Source/Acorn/NFS/PageD)

# NMI shim internal addresses (label not constant — these are memory refs)
label(0x0D0C, "nmi_jmp_lo")         # JMP target low byte (self-modifying)
label(0x0D0D, "nmi_jmp_hi")         # JMP target high byte (self-modifying)
label(0x0D0E, "set_nmi_vector")     # Subroutine: set NMI handler (A=low, Y=high)
label(0x0D14, "nmi_rti")            # NMI return: restore ROM bank, PLA, BIT INTON, RTI
label(0x0D1A, "nmi_shim_1a")        # Referenced by NMI workspace init

# Scout/acknowledge packet buffer (&0D20-&0D25)
label(0x0D20, "tx_dst_stn")         # TX: Destination station
label(0x0D21, "tx_dst_net")         # TX: Destination network
label(0x0D22, "tx_src_stn")         # TX: Source station
label(0x0D23, "tx_src_net")         # TX: Source network
label(0x0D24, "tx_ctrl_byte")       # TX: Control byte
label(0x0D25, "tx_port")            # TX: Port number
label(0x0D26, "tx_data_start")      # TX: Start of data area

# TX control
label(0x0D2A, "tx_data_len")        # Length of data in open port block
label(0x0D3A, "tx_ctrl_status")     # TX control/status byte (shifted by ASL at &8E33)

# Received scout (&0D3D-&0D48)
# &0D3D is also the base of the scout buffer for indexed access (STA &0D3D,Y)
label(0x0D3D, "rx_src_stn")         # RX: Source station (scout buffer base)
label(0x0D3E, "rx_src_net")         # RX: Source network
label(0x0D3F, "rx_ctrl")            # RX: Control byte
label(0x0D40, "rx_port")            # RX: Port number
label(0x0D41, "rx_remote_addr")     # RX: Remote address (4 bytes) / broadcast data (8 bytes)

# TX state
label(0x0D4A, "tx_flags")           # TX workspace flags (b0=four-way, b6=completion)
label(0x0D4B, "nmi_next_lo")        # Next NMI handler address (low)
label(0x0D4C, "nmi_next_hi")        # Next NMI handler address (high)
label(0x0D4F, "tx_index")           # Current TX buffer index
label(0x0D50, "tx_length")          # TX frame length
label(0x0D51, "tx_work_51")         # TX workspace (possibly retry count or flags)
label(0x0D57, "tx_work_57")         # TX workspace (possibly timeout or state)

# RX/status
label(0x0D07, "nmi_shim_07")        # NMI shim workspace
label(0x0D38, "rx_status_flags")    # RX status/mode flags
label(0x0D3B, "rx_ctrl_copy")       # Copy of received control byte
label(0x0D52, "tx_in_progress")     # Referenced by NMI handlers
label(0x0D5C, "scout_status")       # Scout/packet status indicator
label(0x0D5D, "rx_extra_byte")      # Extra byte read after data frame completion

# Econet state (&0D60-&0D67) — reference: NFS00 PBUFFP-TBFLAG
label(0x0D61, "printer_buf_ptr")    # PBUFFP: printer buffer pointer
label(0x0D62, "tx_clear_flag")      # TXCLR: b7=Transmission in progress
label(0x0D63, "prot_status")        # LSTAT: protection mask — b0=PEEK, b1=POKE, b2=HALT, b3=JSR, b4=PROC
label(0x0D64, "rx_flags")           # LFLAG: b7=system Rx (into page-zero CB), b6=user Rx, b2=Halted
label(0x0D65, "saved_jsr_mask")     # OLDJSR: old copy of JSR buffer protection bits
label(0x0D66, "econet_init_flag")   # b7=Econet using NMI code (&00=no, &80=yes)
label(0x0D67, "tube_flag")          # TBFLAG: b7=Tube present (&00=no, &FF=yes)

# ============================================================
# Page &0E — Filing system context (reference: NFS00 FSLOCN-CMNDP)
# ============================================================
# Layout from the original source (NFS00):
#   &0E00  FSLOCN   File server station (2 bytes: station + network)
#   &0E02  URD      User root directory handle
#   &0E03  CSD      Current selected directory handle
#   &0E04  LIB      Library directory handle
#   &0E05  OPT      AUTOBOOT option number (*OPT 4,n)
#   &0E06  MESS     Messages on/off flag
#   &0E07  EOF      End-of-file flags
#   &0E08  SEQNOS   Byte stream sequence numbers
#   &0E09  ERROR    Slot for last unknown error code
#   &0E0A  SPARE    (also JCMNDP)
#   &0E0D  RSTAT    Status byte
#   &0E0E  TARGET   Target station (2 bytes)
#   &0E10  CMNDP    Pointer to rest of command line
label(0x0E00, "fs_server_stn")      # FSLOCN: file server station number
label(0x0E01, "fs_server_net")      # FSLOCN+1: file server network number
label(0x0E02, "fs_urd_handle")      # URD: user root directory handle
label(0x0E03, "fs_csd_handle")      # CSD: current selected directory handle
label(0x0E04, "fs_lib_handle")      # LIB: library directory handle
label(0x0E05, "fs_boot_option")     # OPT: AUTOBOOT option number
label(0x0E06, "fs_messages_flag")   # MESS: messages on/off flag
label(0x0E07, "fs_eof_flags")       # EOF: end-of-file flags
label(0x0E08, "fs_sequence_nos")    # SEQNOS: byte stream sequence numbers
label(0x0E09, "fs_last_error")      # ERROR: slot for last unknown error code
label(0x0E0A, "fs_cmd_context")     # SPARE/JCMNDP: command context
label(0x0E0D, "fs_reply_status")    # RSTAT: b0=remote ok, b1=view ok, b2=notify ok, b3=remoted, b7=FS selected
label(0x0E0E, "fs_target_stn")      # TARGET: target station for remote ops (2 bytes)
label(0x0E10, "fs_cmd_ptr")         # CMNDP: pointer to rest of command line

# Other workspace used by NFS
# Relocated code — Tube host zero-page code (BRKV = &0016)
# Reference: NFS11 (NEWBR, TSTART, MAIN)
label(0x0029, "tube_brk_send_loop")  # Loop: send error message bytes via R2 until zero terminator
label(0x0032, "tube_reset_stack")    # Reset SP=&FF, CLI, fall through to main loop
label(0x003A, "tube_main_loop")      # Poll R1 (WRCH) and R2 (commands), dispatch via table
label(0x003F, "tube_handle_wrch")    # R1 data ready: read byte, call OSWRITCH (&FFCB)
label(0x0045, "tube_poll_r2")        # Poll R2 status; if ready, read command and dispatch
label(0x0054, "tube_dispatch_cmd")   # JMP (&0500) — dispatch to handler via table
label(0x0057, "tube_transfer_addr")  # 4-byte transfer start address (written by address claim)
entry(0x0016)
entry(0x0032)
entry(0x003A)

# Relocated code — page 4 (Tube address claim, RDCH, data transfer)
# Reference: NFS12 (BEGIN, ADRR, SENDW, TADDR, SETADR)
label(0x0403, "tube_escape_entry")   # JMP to tube_escape_check (&06E2)
label(0x0406, "tube_addr_claim")     # Tube address claim protocol (ADRR in reference)
label(0x0414, "tube_post_init")      # Called after ROM→RAM copy; initial Tube setup
label(0x0425, "return_tube_init")    # Return from tube_post_init path
label(0x0472, "return_tube_xfer")   # Return from tube transfer/setup
label(0x04E0, "tube_setup_transfer")  # Set Y=0, X=&57 (tube_transfer_addr), JMP tube_addr_claim
label(0x04E7, "tube_rdch_handler")   # RDCHV target — send &01 via R2, enter main loop
label(0x04EF, "tube_restore_regs")   # Restore X,Y from &10/&11 (dispatch entry 6)
label(0x04F7, "tube_read_r2")        # Wait for R2 data ready, read byte to A
entry(0x0400)
entry(0x0403)
entry(0x0406)
entry(0x0414)
entry(0x04E0)
entry(0x04E7)
entry(0x04EF)
entry(0x04F7)

# Relocated code — page 5 (Tube dispatch table, WRCH, file I/O handlers)
# Reference: NFS13 (TASKS table, BPUT, BGET, RDCHZ, FIND, ARGS, STRNG, CLI, FILE)
#
# &0500-&051B: 14-entry dispatch table of word addresses.
# JMP (&0500) at &0054 dispatches Tube commands; the address claim
# protocol at &0406 patches &0500-&0501 with the target handler address.
#
# Tube cmd  Entry  Addr   Handler
# ────────  ─────  ─────  ─────────────────────────────
#   &00       0    &055B  tube_osrdch (OSRDCH)
#   &01       1    &05C5  tube_oscli (OSCLI)
#   &02       2    &0626  tube_osbyte_short (2-param, X result)
#   &03       3    &063B  tube_osbyte_long (3-param, X+Y results)
#   &04       4    &065D  tube_osword (variable-length)
#   &05       5    &06A3  tube_osword_rdln (OSWORD 0, read line)
#   &06       6    &04EF  tube_restore_regs (release/no-op)
#   &07       7    &053D  tube_release_return (restore regs, RTS)
#   &08       8    &058C  tube_osargs (OSARGS)
#   &09       9    &0550  tube_osbget (OSBGET)
#   &0A      10    &0543  tube_osbput (OSBPUT)
#   &0B      11    &0569  tube_osfind (OSFIND open)
#   &0C      12    &05D8  tube_osfile (OSFILE)
#   &0D      13    &0602  tube_osgbpb (OSGBPB)
label(0x051C, "tube_wrch_handler")    # WRCHV target — write character via Tube
label(0x051F, "tube_send_and_poll")   # Send byte via R2, poll R2/R1 for reply
label(0x0527, "tube_poll_r1_wrch")    # Service R1 WRCH requests while waiting for R2
label(0x0532, "tube_resume_poll")     # JMP back to R2 poll loop after servicing R1
label(0x053D, "tube_release_return")  # Restore X,Y from &10/&11, PLA, RTS
label(0x0543, "tube_osbput")          # OSBPUT: read channel+byte from R2, call &FFD4
label(0x0550, "tube_osbget")          # OSBGET: read channel from R2, call &FFD7
label(0x055B, "tube_osrdch")          # OSRDCH: call &FFC8, send carry+byte reply
label(0x0561, "tube_rdch_reply")      # Send carry in bit 7 + data byte as reply
label(0x0569, "tube_osfind")          # OSFIND open: read arg+filename, call &FFCE
label(0x0580, "tube_osfind_close")    # OSFIND close: read handle, call &FFCE with A=0
label(0x058C, "tube_osargs")          # OSARGS: read handle+4 bytes+reason, call &FFDA
label(0x0590, "tube_read_params")     # Read parameter bytes from R2 into zero page
label(0x05B1, "tube_read_string")     # Read CR-terminated string from R2 into &0700
label(0x05C5, "tube_oscli")           # OSCLI: read command string, call &FFF7
label(0x05CB, "tube_reply_ack")       # Send &7F acknowledge, return to main loop
label(0x05CD, "tube_reply_byte")      # Poll R2, send byte in A, return to main loop
label(0x05D8, "tube_osfile")          # OSFILE: read 16 params+filename+reason, call &FFDD
entry(0x051C)
# Dispatch table entry points
for addr in [0x055B, 0x05C5, 0x0626, 0x063B, 0x065D, 0x06A3,
             0x04EF, 0x053D, 0x058C, 0x0550, 0x0543, 0x0569,
             0x05D8, 0x0602]:
    entry(addr)

# Tube R2 command dispatch table: 14 entries mapping Tube command
# codes 0-13 to handler addresses in pages 4-6.
_tube_r2_entries = [
    (0x0500, "tube_osrdch",        "cmd 0: OSRDCH"),
    (0x0502, "tube_oscli",         "cmd 1: OSCLI"),
    (0x0504, "tube_osbyte_short",  "cmd 2: OSBYTE (2-param)"),
    (0x0506, "tube_osbyte_long",   "cmd 3: OSBYTE (3-param)"),
    (0x0508, "tube_osword",        "cmd 4: OSWORD"),
    (0x050A, "tube_osword_rdln",   "cmd 5: OSWORD 0 (read line)"),
    (0x050C, "tube_restore_regs",  "cmd 6: release/restore regs"),
    (0x050E, "tube_release_return", "cmd 7: restore regs, RTS"),
    (0x0510, "tube_osargs",        "cmd 8: OSARGS"),
    (0x0512, "tube_osbget",        "cmd 9: OSBGET"),
    (0x0514, "tube_osbput",        "cmd 10: OSBPUT"),
    (0x0516, "tube_osfind",        "cmd 11: OSFIND"),
    (0x0518, "tube_osfile",        "cmd 12: OSFILE"),
    (0x051A, "tube_osgbpb",        "cmd 13: OSGBPB"),
]
for addr, target_label, desc in _tube_r2_entries:
    word(addr)
    expr(addr, target_label)
    comment(addr, desc, inline=True)

# Relocated code — page 6 (OSGBPB, OSBYTE, OSWORD, RDLN, event handler)
# Reference: NFS13 (GBPB, SBYTE, BYTE, WORD, RDLN, RDCHA, WRIFOR, ESCAPE, EVENT, ESCA)
label(0x0602, "tube_osgbpb")          # OSGBPB: read 13 params+reason, call &FFD1
label(0x0626, "tube_osbyte_short")    # OSBYTE 2-param: read X+A, call &FFF4, return X
label(0x0630, "tube_osbyte_send_x")   # Poll R2, send X result
label(0x063B, "tube_osbyte_long")     # OSBYTE 3-param: read X+Y+A, call &FFF4, return carry+Y+X
label(0x0653, "tube_osbyte_send_y")   # Poll R2, send Y result, then fall through to send X
label(0x065D, "tube_osword")          # OSWORD variable-length: read A+params, call &FFF1
label(0x0661, "tube_osword_read")     # Poll R2 for param block length, read params
label(0x066C, "tube_osword_read_lp")  # Read param block bytes from R2 into &0130
label(0x0692, "tube_osword_write")    # Write param block bytes from &0130 back to R2
label(0x0695, "tube_osword_write_lp") # Poll R2, send param block byte
label(0x06A0, "tube_return_main")     # JMP tube_main_loop
label(0x06A3, "tube_osword_rdln")     # OSWORD 0 (read line): read 5 params, call &FFF1
label(0x06BB, "tube_rdln_send_line")  # Send input line bytes from &0700 back to Tube
label(0x06C2, "tube_rdln_send_loop")  # Load byte from &0700+X
label(0x06C5, "tube_rdln_send_byte")  # Send byte via R2, loop until CR
label(0x06E2, "tube_escape_check")    # Check &FF escape flag, forward to Tube via R1
label(0x06E8, "tube_event_handler")   # EVNTV target: forward event (A,X,Y) to Tube via R1
label(0x06F7, "tube_send_r1")         # Poll R1 status, write A to R1 data (ESCA in reference)
entry(0x0600)
entry(0x0602)
entry(0x0626)
entry(0x063B)
entry(0x065D)
entry(0x06A3)
entry(0x06E2)
entry(0x06E8)
entry(0x06F7)
label(0x0DEB, "fs_state_deb")        # Filing system state

# ============================================================
# Named labels for dispatch table and key routines
# ============================================================

# ROM header: copyright string doubles as *ROFF command text
# The copyright string "(C)ROFF" serves double duty: the MOS requires
# a valid (C) marker for ROM recognition, and the "ROFF" suffix is
# reused by the star command matcher (svc_4_star_command) as the command
# text for *ROFF (Remote Off). This saves 4 bytes by avoiding a
# separate "ROFF" entry in the command table.
comment(0x800D, """\
The 'ROFF' suffix at copyright_string+3 is reused by
the *ROFF command matcher (svc_4_star_command) — a
space-saving trick that shares ROM bytes between the
copyright string and the star command table.""")

# ROM header: copyright string and error offset table
label(0x800D, "copyright_string")
label(0x8014, "error_offsets")

# Error message offset table (9 entries, indices 0-8).
# The copyright null terminator doubles as entry 0.
# Indexed by TXCB status: AND #7 for codes 0-7, or hardcoded 8.
# Each value is a Y offset into error_msg_table; the code loads
# error_msg_table,Y to copy the selected error string.
comment(0x8014, """\
Error message offset table (9 entries).
Each byte is a Y offset into error_msg_table.
Entry 0 (Y=0, "Line Jammed") doubles as the
copyright string null terminator.
Indexed by TXCB status (AND #7), or hardcoded 8.""")
comment(0x8014, '"Line Jammed"', inline=True)
for addr in range(0x8015, 0x801D):
    byte(addr)
comment(0x8015, '"Net Error"', inline=True)
comment(0x8016, '"Not listening"', inline=True)
comment(0x8017, '"No Clock"', inline=True)
comment(0x8018, '"Bad Txcb"', inline=True)
comment(0x8019, '"Escape"', inline=True)
comment(0x801A, '"Escape"', inline=True)
comment(0x801B, '"Bad Option"', inline=True)
comment(0x801C, '"No reply"', inline=True)

# Unreferenced padding between error offsets and dispatch table
comment(0x801D, "Four bytes with unknown purpose.")
for addr in range(0x801D, 0x8021):
    byte(addr)
comment(0x801D, "Purpose unknown", inline=True)
comment(0x801E, "Purpose unknown", inline=True)
comment(0x801F, "Purpose unknown", inline=True)
comment(0x8020, "Purpose unknown", inline=True)

# Dispatch tables: split low/high byte address tables
label(0x8021, "dispatch_0_lo")          # First low byte entry (Svc 0)
label(0x8045, "dispatch_0_hi")          # First high byte entry (Svc 0)
expr_label(0x8020, "dispatch_0_lo-1")   # Code operand expression
expr_label(0x8044, "dispatch_0_hi-1")   # Code operand expression

# Dispatcher and dispatch callers
# Note: &8099 is already labelled "language_handler" by acorn.is_sideways_rom()

# Filing system OSWORD dispatch (&8DF7-&8E01)
label(0x8E18, "fs_osword_tbl_lo")      # Low bytes of FS OSWORD handler table
label(0x8E1D, "fs_osword_tbl_hi")      # High bytes of FS OSWORD handler table

# FS OSWORD handler routines
# osword_0f_handler label created by subroutine() call below.
label(0x8E6A, "read_args_size")        # READRB: get args buffer size from RX block offset &7F
# osword_10_handler label created by subroutine() call below.

# Econet TX/RX handler and OSWORD dispatch
label(0x8F68, "store_16bit_at_y")     # Store 16-bit value at (nfs_workspace)+Y
# osword_dispatch label created by subroutine() call below.
label(0x9020, "osword_trampoline")     # PHA/PHA/RTS trampoline
label(0x902B, "osword_tbl_lo")         # Dispatch table low bytes
label(0x9034, "osword_tbl_hi")         # Dispatch table high bytes
# net_write_char label created by subroutine() call below.

# Remote operation function handlers (dispatched via osword_tbl)
# (net_write_char subroutine defined above)
label(0x90BD, "return_match_osbyte") # Return from match_osbyte_code
label(0x90FB, "return_remote_cmd")   # Return from remote command data handler

# Control block setup
label(0x9166, "ctrl_block_setup_clv") # CLV entry: same setup but clears V flag

# Remote printer and display handlers (fn 1/2/3/5)

# Network transmit

# JSR buffer protection
label(0x92D6, "clear_jsr_protection") # CLRJSR: reset JSR buffer protection bits (4 refs)

# Palette/VDU state save
label(0x92EE, "read_vdu_osbyte_x0")  # Read next VDU OSBYTE with X=0 parameter
label(0x92F0, "read_vdu_osbyte")     # Read next OSBYTE from table, store result in workspace

# ADLC initialisation and state management

# Tube co-processor I/O subroutines (in relocated page 6)
# Reference: RDCHA (R2 write), WRIFOR (R4 write), ESCA (R1 write)
label(0x06D0, "tube_send_r2")       # Poll R2 status, write A to R2 data (RDCHA in reference)
label(0x06D9, "tube_send_r4")       # Poll R4 status, write A to R4 data (WRIFOR in reference)

# ============================================================
# Service call handler labels (&8000-&84FF)
# ============================================================
# Service call numbers and their dispatch table indices:
#   svc 0  → index 1  → return_2 (no-op)
#   svc 1  → index 2  → svc_1_abs_workspace (&826F)
#   svc 2  → index 3  → svc_2_private_workspace (&8278)
#   svc 3  → index 4  → svc_3_autoboot (&81D1)
#   svc 4  → index 5  → svc_4_star_command (&8172)
#   svc 5  → index 6  → svc_5_unknown_irq (&966C) → JMP c9b52
#   svc 6  → index 7  → return_2 (BRK — no action)
#   svc 7  → index 8  → dispatch_net_cmd (&8069) (unrecognised OSBYTE)
#   svc 8  → index 9  → svc_8_osword (&8DF7) (unrecognised OSWORD)
#   svc 9  → index 10 → svc_9_help (&81BC)
#   svc 10 → index 11 → return_2 (no action)
#   svc 11 → index 12 → svc_11_nmi_claim (&9669) → JMP restore_econet_state
#   svc 12 → index 13 → svc_12_nmi_release (&9666) → JMP save_econet_state
#
# Special service handling (outside dispatch table):
#   svc &12 (18) with Y=5 → select_nfs (&8184)
#   svc &FE → Tube init (explode character definitions)
#   svc &FF → init_vectors_and_copy (&80C8)

label(0x80AE, "return_1")
label(0x8145, "return_2")
label(0x8275, "return_3")

# --- Service call handlers ---

# --- Trampoline JMPs near ADLC init (&9660-&966C) ---
label(0x9660, "trampoline_tx_setup")    # JMP c9be4 (TX control block setup)
label(0x9663, "trampoline_adlc_init")   # JMP adlc_init (&966F)
label(0x9666, "svc_12_nmi_release")        # Svc 12: JMP save_econet_state (&969D)
label(0x9669, "svc_11_nmi_claim")          # Svc 11: JMP restore_econet_state (&96B4)
label(0x966C, "svc_5_unknown_irq")        # Svc 5: JMP c9b52 (unknown interrupt handler)
entry(0x9660)
entry(0x9663)

# --- Init and vector setup ---
label(0x824D, "fs_vector_addrs")        # FS vector dispatch and handler addresses (34 bytes)

# --- FSCV handler and dispatch ---
# FSCV (&808C) dispatches via secondary indices 19-26:
#   FSCV 0 (*OPT)               → index 19 → fscv_0_opt (&89A1)
#   FSCV 1 (EOF)                → index 20 → fscv_1_eof (&881F)
#   FSCV 2 (*/ run)             → index 21 → fscv_3_star_cmd (match known FS commands)
#   FSCV 3 (unrecognised *)     → index 22 → fscv_3_star_cmd (match known FS commands)
#   FSCV 4 (*RUN)               → index 23 → fscv_3_star_cmd (match known FS commands)
#   FSCV 5 (*CAT)               → index 24 → fscv_5_cat (&8BFD)
#   FSCV 6 (shut down)          → index 25 → fscv_6_shutdown (&82FD)
#   FSCV 7 (read handles/info)  → index 26 → fscv_7_read_handles (&85DA)
#
# Extended dispatch table entries (indices 27-36):
# These appear to be used by FS reply processing and *NET sub-commands.
#   index 27 → fsreply_0_print_dir (&8D73)        (print directory path)
#   index 28 → fsreply_1_copy_handles_boot (&8D1F) (copy handles + run boot command)
#   index 29 → fsreply_2_copy_handles (&8D20)          (copy handles only)
#   index 30 → fsreply_3_set_csd (&8CFC)        (update CSD handle)
#   index 31 → fsreply_4_notify_exec (&8D84)       (send FS notify, execute response)
#   index 32 → fsreply_5_set_lib (&8CF7)        (update library handle)
#
# *NET sub-commands (base Y=&20, indices 33-36):
#   *NET1 → index 33 → net_1_read_handle (&8DAF)
#   *NET2 → index 34 → net_2_read_handle_entry (&8DC9)
#   *NET3 → index 35 → net_3_close_handle (&8DDF)
#   *NET4 → index 36 → net_4_resume_remote (&8DF2)
# --- Filing system vector entry points ---
# Extended vector table entries set up at init (&82E5):
#   FILEV → &8694    ARGSV → &88E1    BGETV → &8485
#   BPUTV → &83A2    GBPBV → &89EA    FINDV → &8949
#   FSCV  → &808C
# Labels and entry points for FSCV, FILEV, ARGSV, FINDV, GBPBV
# are created by subroutine() calls below in the comment sections.
label(0x8485, "bgetv_handler")          # BGETV entry: SEC then JSR handle_bput_bget
label(0x83A2, "bputv_handler")          # BPUTV entry: CLC then fall into handle_bput_bget
entry(0x8485)
entry(0x83A2)

# --- Helper routines in header/init section ---
label(0x81AC, "cmd_name_matched")       # MATCH2: full name matched, check terminator byte
label(0x81B3, "skip_cmd_spaces")         # SKPSP: skip spaces in command text; Z=1 if CR follows
label(0x82E5, "store_rom_ptr_pair")     # Write 2-byte address + ROM bank to ROM pointer table

# --- TX control block and FS command setup ---
label(0x830E, "init_tx_ctrl_data")      # Init TX control block for data port (&90)
label(0x8310, "init_tx_ctrl_port")      # Init TX control block with port in A (2 JSR refs)
label(0x8340, "prepare_cmd_with_flag")  # Prepare FS command with '*' flag and carry set
label(0x8346, "prepare_cmd_clv")        # Prepare FS command with V cleared
# prepare_fs_cmd and build_send_fs_cmd labels created by subroutine() calls below.
label(0x8351, "prepare_fs_cmd_v")       # Prepare FS command, V flag preserved
label(0x8380, "send_fs_reply_cmd")      # Send FS command with reply processing

# --- Byte I/O and escape ---
# handle_bput_bget label created by subroutine() call below.
label(0x83CB, "store_retry_count")      # RAND1: store retry count to &0FDD, initiate TX
label(0x841B, "update_sequence_return") # RAND3: update sequence numbers and pull A/Y/X/return
label(0x842C, "set_listen_offset")      # NLISN2: use reply code as table offset for listen
label(0x8448, "send_to_fs_star")        # Send '*' command to fileserver
label(0x8470, "fs_wait_cleanup")        # WAITEX: tidy stack, restore rx_status_flags

# --- Pointer arithmetic helpers ---
label(0x84A3, "return_bget")             # Return from BGET/BPUT handler
label(0x84A4, "add_5_to_y")             # INY * 5; RTS
label(0x84A5, "add_4_to_y")             # INY * 4; RTS
label(0x84AA, "sub_4_from_y")           # DEY * 4; RTS
label(0x84AB, "sub_3_from_y")           # DEY * 3; RTS

# --- Error messages and data tables ---
label(0x815C, "clear_osbyte_ce_cf")     # Reset OSBYTE &CE/&CF intercept masks to &7F (restore MOS vectors)

# --- * command forwarding and BYE ---

# --- Page &0F workspace (FS command buffer) ---
# NFS00 layout: BIGBUF=&0F00, TXBUF/RXBUF=&0F05, RXBUFE=&0FFF
#   &0F00 HDRREP: reply header / command type
#   &0F01 HDRFN:  function code
#   &0F02 HDRURD: URD handle slot
#   &0F03 HDRCSD/RXCC: CSD slot / RX control code
#   &0F04 HDRLIB/RXRC: LIB slot / RX return code
#   &0F05 TXBUF/RXBUF: start of TX/RX data area
#   &0FDC PUTB/PUTB1: single-byte random access buffer (4 bytes)
#   &0FDD PUTB2/GETB2: shared GET/PUT byte workspace
label(0x0F00, "fs_cmd_type")            # HDRREP: reply header / command type
label(0x0F01, "fs_cmd_y_param")         # HDRFN: function code
label(0x0F02, "fs_cmd_urd")             # HDRURD: URD handle slot
label(0x0F03, "fs_cmd_csd")             # HDRCSD: CSD handle / RX control code
label(0x0F04, "fs_cmd_lib")             # HDRLIB/RXRC: LIB slot / RX return code
label(0x0F05, "fs_cmd_data")            # TXBUF/RXBUF: start of TX/RX data area
label(0x0FDC, "fs_putb_buf")            # PUTB: single-byte random access buffer (4 bytes)
label(0x0FDD, "fs_getb_buf")            # PUTB2/GETB2: shared GET/PUT byte workspace

# ============================================================
# Filing system protocol client (&8500-&86FF)
# ============================================================
# Core routines shared by all FS commands: argument saving,
# file handle conversion, number parsing/printing, TX/RX,
# file info display, and attribute decoding.

# --- Argument save and file handle conversion ---
label(0x8530, "access_bit_table")       # Lookup table for attribute bit mapping (11 bytes)

# --- Decimal number parser (&8560-&8587) ---
# parse_decimal label created by subroutine() call below.

# --- File handle ↔ bitmask conversion ---
# handle_to_mask_a, handle_to_mask_clc, handle_to_mask and mask_to_handle
# labels created by subroutine() calls below.

# --- Number and hex printing ---
label(0x85F6, "print_hex_nibble")       # Print low nibble of A as hex digit

# --- Address comparison ---
# compare_addresses label created by subroutine() call below.
label(0x85D9, "return_compare")          # Return from compare_addresses (not equal)

# --- FSCV 7: read FS handles ---
label(0x85DA, "fscv_7_read_handles")      # Return X=&20 (base handle), Y=&27 (top handle)
label(0x85DE, "return_fscv_handles")    # Return from fscv_7_read_handles

# --- FS flags manipulation ---

# --- File info display ---
label(0x8617, "pad_filename_spaces")    # MONL2: pad filename display to 12 chars with spaces
label(0x862A, "print_exec_and_len")     # Print exec address (4 bytes) and length (3 bytes)
label(0x8635, "print_hex_bytes")        # Print X bytes from (fs_options)+Y as hex (high→low)
label(0x8640, "print_space")            # Print a space character via OSASCI

# --- TX control and transmission ---
label(0x864E, "tx_poll_timeout")        # Transmit with Y=&60 (specified timeout)
# tx_poll_core label created by subroutine() call below.
label(0x8684, "delay_1ms")              # MSDELY: 1ms delay loop (nested DEX/DEY)

# ============================================================
# File operations: FILEV, ARGSV, FINDV, GBPBV (&8694-&8B91)
# ============================================================
# The FS vector handlers for file I/O. Each handler saves
# args via save_fscv_args, processes the request by building
# FS commands and sending them to the fileserver, then restores
# args and returns via restore_args_return (&892C).

# --- FILEV handler (&8694) and helpers ---

# --- FSCV 1: EOF handler (&881F) ---

# --- FILEV attribute dispatch (&8844) ---
label(0x886E, "get_file_protection")  # CHA1: decode attribute byte for protection status
label(0x8883, "copy_filename_to_cmd") # CHASK2: copy filename string into FS command buffer
label(0x88C5, "copy_fs_reply_to_cb")  # COPYFS: copy FS reply buffer data to control block

# --- Common return point (&892C) ---
label(0x8912, "save_args_handle")      # SETARG: save handle for OSARGS operation

# --- FSCV 0: *OPT handler (&89A1) ---
label(0x898F, "close_single_handle")   # CLOSE1: send close command for specific handle to FS

# --- Address adjustment helpers (&89CA-&89E9) ---
label(0x89CA, "adjust_addrs_9")        # Adjust 4-byte addresses at param block offset 9
label(0x89CF, "adjust_addrs_1")        # Adjust 4-byte addresses at param block offset 1
label(0x89D1, "adjust_addrs_clc")      # CLC entry: clear carry before address adjustment
label(0x8AFB, "copy_reply_to_caller") # Copy FS reply data to caller buffer (direct or via Tube)
label(0x8B8A, "tube_claim_loop")      # TCLAIM: claim Tube with &C3, retry until acquired

# ============================================================
# *-Command handlers and FSCV dispatch (&8B92-&8DFF)
# ============================================================
# FSCV 2/3/4 (unrecognised *) routes through fscv_3_star_cmd
# which matches against known FS commands before forwarding.
# The *CAT/*EX handlers display directory listings.
# *NET1-4 sub-commands manage file handles in local workspace.

# --- FSCV unrecognised * and command matching ---

# --- *EX and *CAT handlers ---

# --- Boot command strings and option tables ---
label(0x8D51, "print_reply_counted")   # STRIN1: sub-entry of print_reply_bytes with caller-supplied Y count
label(0x8D67, "copy_string_from_offset") # COPLP1: sub-entry of copy_string_to_cmd with caller-supplied Y offset
label(0x8D72, "return_copy_string")   # Return from copy_string_to_cmd
label(0x8D75, "print_dir_from_offset") # INFOLP: sub-entry of fsreply_0_print_dir with caller-supplied X offset

# --- *NET sub-command handlers ---

# ============================================================
# Named labels for ADLC NMI handler routines
# ============================================================
# These replace auto-generated c/sub_ prefixed labels with
# descriptive names based on analysis of the NFS ROM's ADLC
# interaction and four-way handshake state machine.

# --- ADLC control (BRIAN entry points: NFS02) ---
# BRIANX=+&0000 (transmit), BRIANP=+&0003 (power up),
# BRIANC=+&0006 (relinquish NMI), BRIANQ=+&0009 (reclaim NMI),
# BRIANI=+&000C (unknown interrupt handler)

# --- RX scout reception (inbound) ---
label(0x9723, "scout_reject")          # Reject: wrong network (RX_DISCONTINUE)
label(0x9744, "scout_discard")         # Clean discard via &9A40
label(0x974C, "scout_loop_rda")        # Scout data loop: check RDA
label(0x975C, "scout_loop_second")     # Scout data loop: read second byte of pair
label(0x9797, "scout_no_match")        # Scout port/station mismatch (3 refs)
label(0x979A, "scout_match_port")      # Port non-zero: look for matching RX block

# --- Data frame RX (inbound four-way handshake) ---
label(0x982D, "data_rx_setup")         # Switch to RX mode, install data RX handler
label(0x984F, "nmi_data_rx_net")       # Data frame: validate dest_net = 0
label(0x9865, "nmi_data_rx_skip")      # Data frame: skip ctrl/port (already from scout)
label(0x988A, "rx_error")              # RX error dispatcher (13 refs -- most referenced!)
label(0x9894, "rx_error_reset")        # Full reset and discard
label(0x98F7, "nmi_data_rx_tube")      # Data frame: Tube co-processor variant

# --- Data frame completion and FV validation ---
label(0x9933, "data_rx_tube_complete") # Tube data frame completion
label(0x9930, "data_rx_tube_error")    # Tube data frame error (3 refs)

# --- ACK transmission ---
label(0x9966, "ack_tx_configure")      # Configure CR1/CR2 for TX
label(0x9974, "ack_tx_write_dest")     # Write dest addr to TX FIFO

# --- Discard and idle ---

# --- TX path ---
label(0x9C84, "tx_active_start")       # Begin TX (CR1=&44)
label(0x9D72, "tx_error")              # TX error path

# --- RX reply scout (outbound handshake) ---
label(0x9DDE, "reply_error")           # Reply error: store &41 (8 refs)

# --- TX scout ACK + data phase ---
label(0x9E3B, "data_tx_begin")         # Begin data frame TX
label(0x9E7D, "data_tx_last")          # TX_LAST_DATA for data frame (5 refs)
label(0x9E8E, "data_tx_error")         # Data TX error (5 refs)
label(0x9E9B, "install_saved_handler") # Install handler from &0D4B/&0D4C
label(0x9EA4, "nmi_data_tx_tube")      # NMI: send data from Tube

# --- Four-way handshake: RX final ACK ---
label(0x9EFF, "nmi_final_ack_net")     # Read dest_net, validate

# --- Completion and error ---

# --- NMI shim at end of ROM ---
label(0x9FCA, "nmi_shim_rom_src")      # Source for 32-byte copy to &0D00
label(0x9FEB, "rom_nmi_tail")          # TX flags update + address calc (purpose unclear)

# ============================================================
# Labels from DNFS 3.60 source correspondence
# ============================================================
# These labels were identified by opcode fingerprint matching between
# the NFS 3.34 ROM and the original Acorn DNFS 3.60 source code
# (NFS00-NFS13). Each replaces a py8dis auto-generated label with
# the name used in the Acorn reference source.

# --- Relocated Tube code (pages 4-6) ---
label(0x04AE, "begink")               # NFS12: Tube begin
label(0x04BA, "beginr")               # NFS12: Tube begin return
label(0x05B5, "strnh")                # NFS13: string handling
label(0x05D5, "mj")                   # NFS13: conditional jump
label(0x05DA, "argsw")                # NFS13: OSARGS workspace
label(0x0638, "bytex")                # NFS13: byte transfer

# --- Service call init (&80xx) ---
label(0x80F9, "cloop")                # NFS01: copy loop (page copy)
label(0x818F, "initl")                # NFS01: init loop
label(0x81B2, "skpspi")               # NFS01: skip SPI

# --- FS command dispatch (&82xx-&83xx) ---
label(0x8219, "dofsl1")               # NFS03: do FS loop 1
label(0x82FF, "fsdiel")               # NFS01: FS die loop
label(0x831F, "fstxl1")               # NFS03: FS TX loop 1
label(0x832F, "fstxl2")               # NFS03: FS TX loop 2
label(0x838A, "dofsl7")               # NFS03: do FS loop 7
label(0x8396, "return_dofsl7")        # NFS03: return from FS loop 7
label(0x8397, "dofsl5")               # NFS03: do FS loop 5
label(0x83DD, "error1")               # NFS03: error handler 1

# --- Net list / pointer arithmetic (&84xx-&85xx) ---
label(0x8428, "nlistn")               # NFS03: net list entry
label(0x842A, "nlisne")               # NFS03: net list next entry
label(0x845A, "incpx")                # NFS04: increment pointer X
label(0x8592, "y2fsl5")               # NFS04: Y-to-FS loop 5
label(0x8598, "y2fsl2")               # NFS04: Y-to-FS loop 2
label(0x85A7, "fs2al1")               # NFS04: FS-to-A loop 1

# --- Number formatting and file info (&86xx) ---
label(0x8637, "num01")                # NFS07: number print entry
label(0x866A, "poll_txcb_status")     # NFS03: net TX polling loop
label(0x8699, "file1")                # NFS05: FILEV entry 1
label(0x86A8, "quote1")               # NFS05: filename quote loop
label(0x86CB, "loadop")               # NFS05: load operation
label(0x86E8, "lodfil")               # NFS05: load file

# --- FILEV, load/save size (&87xx) ---
label(0x870B, "floop")                # NFS01: FS loop
label(0x8735, "lodchk")               # NFS05: load check
label(0x8740, "return_lodchk")        # NFS05: return from load check
label(0x8741, "saveop")               # NFS05: save operation
label(0x874A, "savsiz")               # NFS05: save size handling
label(0x87AF, "lodrl1")               # NFS05: load reply loop 1
label(0x87BD, "lodrl2")               # NFS05: load reply loop 2
label(0x87EB, "savchk")               # NFS05: save check

# --- Channel/attribute handling (&88xx-&89xx) ---
label(0x8861, "chalp1")               # NFS05: channel loop 1
label(0x8878, "chalp2")               # NFS05: channel loop 2
label(0x888A, "cha6")                  # NFS05: channel handler 6
label(0x8899, "cha4")                  # NFS05: channel handler 4
label(0x88A3, "cha5")                  # NFS05: channel handler 5
label(0x88D2, "cha5lp")               # NFS05: channel 5 loop
label(0x893D, "osarg1")               # NFS05: OSARGS handler 1
label(0x89B6, "opter1")               # NFS05: *OPT error 1
label(0x89BB, "optl1")                # NFS05: *OPT loop 1

# --- GBPB handler (&89xx-&8Axx) ---
label(0x89E3, "gbpbx")                # NFS05: GBPB dispatch
label(0x89F5, "gbpbx0")               # NFS05: GBPB dispatch 0
label(0x89F8, "gbpbx1")               # NFS05: GBPB dispatch 1
label(0x8A03, "gbpbe1")               # NFS05: GBPB EOF 1
label(0x8A0F, "gbpbf1")               # NFS05: GBPB forward 1
label(0x8A1A, "gbpbf2")               # NFS05: GBPB forward 2
label(0x8A23, "gbpbl1")               # NFS05: GBPB loop 1
label(0x8A45, "gbpbl3")               # NFS05: GBPB loop 3
label(0x8A5C, "gbpbf3")               # NFS05: GBPB forward 3

# --- *INFO and decimal print (&8Axx-&8Bxx) ---
label(0x8ABD, "info2")                # NFS06: *INFO loop 2
label(0x8B22, "tbcop1")               # NFS06: Tube copy loop 1
label(0x8B99, "decfir")               # NFS07: decimal first digit
label(0x8B9B, "decmor")               # NFS07: decimal more digits
label(0x8BA7, "decmin")               # NFS07: decimal minimum

# --- Logon and *NET (&8Dxx) ---
label(0x8D24, "logon2")               # NFS07: logon handler 2
label(0x8D2A, "logon3")               # NFS07: logon handler 3
label(0x8D7E, "infol2")               # NFS07: info loop 2

# --- File I/O: save, read, open (&8Dxx-&8Fxx) ---
label(0x8DD6, "rxpol2")               # NFS08: RX poll loop 2
label(0x8E0C, "save1")                # NFS08: save handler 1
label(0x8E2E, "copyl3")               # NFS08: copy loop 3
label(0x8E75, "readry")               # NFS08: read ready
label(0x8E9B, "rssl1")                # NFS08: read size/status loop 1
label(0x8EA6, "rssl2")                # NFS08: read size/status loop 2
label(0x8EB7, "rsl1")                 # NFS08: read status loop 1
label(0x8EE3, "readc1")               # NFS08: read char 1
label(0x8F01, "scan0")                # NFS08: scan entry 0
label(0x8F15, "scan1")                # NFS08: scan entry 1
label(0x8F31, "openl6")               # NFS08: open loop 6
label(0x8F3E, "openl7")               # NFS08: open loop 7
label(0x8F43, "openl4")               # NFS08: open loop 4
label(0x8F4E, "rest1")                # NFS08: restore 1
label(0x8F78, "dofs01")               # NFS08: do FS 01
label(0x8FF5, "dofs2")                # NFS08: do FS 2

# --- OSWORD and remote ops (&90xx-&91xx) ---
label(0x9019, "entry1")               # NFS09: OSWORD entry 1
label(0x9085, "nbyte6")               # NFS09: net byte handler 6
label(0x9087, "nbyte1")               # NFS09: net byte handler 1
label(0x90A9, "nbyte4")               # NFS09: net byte handler 4
label(0x90AD, "nbyte5")               # NFS09: net byte handler 5
label(0x90B4, "return_nbyte")         # NFS09: return from net byte handler
label(0x9102, "rchex")                # NFS03: receive hex
label(0x9105, "remot1")               # NFS03: remote handler 1
label(0x9167, "cbset2")               # NFS09: control block set 2
label(0x917E, "cbset3")               # NFS09: control block set 3
label(0x9184, "cbset4")               # NFS09: control block set 4
label(0x91C3, "setup1")               # NFS09: setup 1
label(0x91C6, "return_printer_select") # NFS09: return from printer_select_handler
label(0x91D6, "prlp1")                # NFS09: printer loop 1

# --- Broadcast/station search (&92xx) ---
label(0x9254, "bsxl1")                # NFS09: broadcast search loop 1
label(0x9271, "bspsx")                # NFS09: broadcast search parse exit
label(0x9279, "bsxl0")                # NFS09: broadcast search loop 0
label(0x9290, "return_bspsx")         # NFS09: return from broadcast search area

# ============================================================
# File header / overview comment (placed at &8000, first in code)
# ============================================================
comment(0x8000, """\
NFS ROM 3.34 disassembly (Acorn Econet filing system)
====================================================""")
comment(0x8000, "JMP language_handler", inline=True)
comment(0x8003, "JMP service_handler", inline=True)

# ============================================================
# Dispatch table at &8020 (low bytes) / &8044 (high bytes)
# ============================================================
# Used via the PHA/PHA/RTS dispatch trick at &809F-&80AE.
#
# This is a standard 6502 computed-jump technique. The table stores
# handler addresses minus 1, split into separate low-byte and high-byte
# arrays. The dispatcher at &809F pushes the high byte then the low
# byte onto the stack. When RTS executes, it pops the address and adds
# 1, jumping to the handler.
#
# Multiple callers share this single table using different base offsets
# in Y. The dispatcher loop at &809F adds Y to X (the command index),
# so each caller maps its index into a different region of the table:
#
#   Caller              Y (base)  X (index)         Table indices
#   ─────────────────   ────────  ────────────────  ─────────────
#   Service calls        &00      svc_num            1-13
#   Language entry       &0D      reason             14-18
#   FSCV                 &12      fscv_code          19-26
#   FS reply             &16      reply_code         27-32
#   *NET1-4 commands     &20      char-'1'           33-36
#
# Index 0 and unused indices point to an RTS (null handler), so
# unrecognised service calls or out-of-range values fall through
# harmlessly.
#
# rts_code_ptr(lo_addr, hi_addr) decodes the address and adds entry().

# Service call handlers (indices 1-13)
for i in range(1, 14):
    rts_code_ptr(0x8020 + i, 0x8044 + i)

# Language entry handlers (indices 14-18)
for i in range(14, 19):
    rts_code_ptr(0x8020 + i, 0x8044 + i)

# FSCV handlers (indices 19-26, codes 0-7, base Y=&12)
for i in range(19, 27):
    rts_code_ptr(0x8020 + i, 0x8044 + i)

# FS reply handlers (indices 27-32)
# Dispatched by forward_star_cmd with base Y=&16 using the
# fileserver's reply code as the index.
for i in range(27, 33):
    rts_code_ptr(0x8020 + i, 0x8044 + i)

# *NET command handlers (indices 33-36)
# Index 36 overlaps: low byte at &8044 (= high table[0])
for i in range(33, 37):
    rts_code_ptr(0x8020 + i, 0x8044 + i)

# ============================================================
# Filing system OSWORD dispatch table at &8E18/&8E1D
# ============================================================
# Used by the PHA/PHA/RTS dispatch at &8E01 (entered from svc_8_osword).
# svc_8_osword subtracts &0F from the command code in &EF, giving a
# 0-4 index for OSWORD calls &0F-&13 (15-19).
#
# Index  OSWORD  Target   Purpose
# ─────  ──────  ───────  ────────────────────────────
#   0      &0F   &8E33    Protection/status control
#   1      &10   &8EF0    RX block read/setup
#   2      &11   &8E53    Data block copy
#   3      &12   &8E7B    FS server station lookup
#   4      &13   &8F72    Econet TX/RX handler
for i in range(5):
    rts_code_ptr(0x8E18 + i, 0x8E1D + i)

# ============================================================
# NMI handler chain entry points
# ============================================================
# These are installed via self-modifying JMP at &0D0C/&0D0D,
# so py8dis cannot trace them automatically.

# --- ADLC init and idle listen ---
entry(0x96F0)   # ADLC init / reset entry
entry(0x96F6)   # RX scout (idle listen) - default NMI handler

# --- TX path: polling, data, completion ---
entry(0x9C48)   # INACTIVE polling loop (pre-TX)
entry(0x9D4C)   # NMI TX data handler (2 bytes per NMI)
entry(0x9D72)   # TX error path
entry(0x9D88)   # TX_LAST_DATA and frame completion
entry(0x9D94)   # TX completion: switch to RX mode

# --- RX reply handlers ---
entry(0x9DB2)   # RX reply scout handler
entry(0x9DC8)   # RX reply continuation handler
entry(0x9DE3)   # RX reply next handler

# --- Four-way handshake (outbound data phase) ---
entry(0x9EDD)   # Four-way handshake: switch to RX for final ACK
entry(0x9EE9)   # Four-way handshake: RX final ACK (check AP, dest_stn)
entry(0x9EFF)   # Four-way handshake: RX final ACK continuation (dest_net=0)

# --- Completion / error ---
entry(0x9F39)   # Completion handler (store result=0 to tx_block)
entry(0x9F3F)   # Error handler (store error code to tx_block)
entry(0x9F15)   # Four-way handshake: validate final ACK src addr

# --- Discovered via JMP &0D0E scan (NMI handler installations) ---
entry(0x9715)   # RX scout second byte handler (dest network)
entry(0x9747)   # Scout data reading loop (reads body in pairs)
entry(0x9839)   # Data frame RX handler (four-way handshake)
entry(0x984F)   # Data frame: validate source network = 0
entry(0x9865)   # Data frame: skip ctrl/port bytes
entry(0x989A)   # Data frame: bulk data read loop
entry(0x98F7)   # Data frame: Tube co-processor RX handler
entry(0x9992)   # ACK TX continuation (write src addr, TX_LAST_DATA)

# --- NMI shim at end of ROM (&9FCA-&9FFF) ---
# Bootstrap NMI handler and ROM copies of workspace routines.
# &9FCA is the source for the 32-byte copy to &0D00 by install_nmi_shim.
entry(0x9FCB)   # Bootstrap NMI entry (hardcoded JMP nmi_rx_scout, no self-mod)
entry(0x9FD9)   # ROM copy of set_nmi_vector + nmi_rti
entry(0x9FEB)   # TX flags update + address calculation

# --- Data RX NMI handlers (four-way handshake data phase) ---
entry(0x9E2B)   # Data phase RX first byte
entry(0x9E50)   # Data phase RX continuation
entry(0x9EA4)   # Data phase RX bulk transfer

# ============================================================
# Additional known entry points
# ============================================================
entry(0x81D0)
entry(0x81E0)
entry(0x81FE)
entry(0x8200)

# ============================================================
# Code regions identified by manual inspection of equb data
# ============================================================
# These are preceded by RTS and start with valid opcodes, but
# are not reachable via JSR/JMP from already-traced code (their
# callers are themselves in equb regions -- cascading resolution).

entry(0x84A4)   # INY*5; RTS (pointer arithmetic helper)
entry(0x84AA)   # DEY*4; RTS (pointer arithmetic helper)
entry(0x87C8)   # PHA; JSR ... (called from &8789 and &8A6B)
entry(0x8844)   # STA abs; CMP#; ... (called from &8743)
entry(0x8933)   # TAY; BNE; ... (preceded by RTS, standalone entry)
entry(0x89EA)   # JSR &8508; ... (preceded by RTS, standalone entry)
# entry(0x8E33) created by subroutine() call below
entry(0x9063)   # LDY zp; CMP#; ... (preceded by RTS, standalone entry)
entry(0x99BB)   # Post-ACK: process received scout (check port, match RX block)

# --- Econet TX/RX handler and OSWORD dispatch (&8F72-&904A) ---
# &8F72: Main transmit/receive handler entry (A=0: set up and send, A>=1: handle result)
# &9007: OSWORD-style dispatch handler (function codes 0-8, PHA/PHA/RTS)
entry(0x8F72)   # Econet TX/RX handler (CMP #1; BCS)
# entry(0x9007) and entry(0x903D) created by subroutine() calls below
entry(0x9020)   # Dispatch trampoline (PHA/PHA/RTS into table at &902B/&9034)

# Dispatch table at &902B (low bytes) / &9034 (high bytes)
# 9 entries for function codes 0-8, used via PHA/PHA/RTS at &9020.
# Targets: 0=&8145(RTS), 1-3=&91C7, 4=&903D, 5=&91B5, 6=&8145(RTS), 7=&9063, 8=&90CD
for i in range(9):
    rts_code_ptr(0x902B + i, 0x9034 + i)

# ============================================================
# Immediate operation dispatch table at &9A0E/&9A16
# ============================================================
# Used by the PHA/PHA/RTS dispatch at &9A86 (immediate_op handler).
# Y = rx_ctrl (&81-&88), so table entries are at base+&81..base+&88.
# The control byte determines the remote operation type:
#
# Y   Operation   Target
# ──   ─────────   ──────
# &81  PEEK        &9ADB
# &82  POKE        &9ABD
# &83  JSR         &9A9F
# &84  UserProc    &9A9F
# &85  OSProc      &9A9F
# &86  HALT        &9B01
# &87  CONTINUE    &9B01
# &88  (machine type query)  &9AC8
for y in range(0x81, 0x89):
    rts_code_ptr(0x9A0E + y, 0x9A16 + y)

# ============================================================
# TX completion dispatch table at &9B0E/&9B13
# ============================================================
# Used by the PHA/PHA/RTS dispatch at &9B88.
# Y = tx_work_57 (the Econet operation type being sent).
# Table entries for Y=&81/&82 overlap with the PHA/RTS code
# itself and are not valid — those operation types (PEEK/POKE)
# are response-only and never initiated via TX.
#
# Y   Operation   Target
# ──   ─────────   ──────
# &83  JSR         &9B9B  (remote JSR initiation)
# &84  UserProc    &9BA4  (user procedure initiation)
# &85  OSProc      &9BB2  (OS procedure initiation)
# &86  HALT        &9BBE  (HALT completion)
# &87  CONTINUE    &9BD5  (CONTINUE completion)
for y in range(0x83, 0x88):
    rts_code_ptr(0x9B0E + y, 0x9B13 + y)

# ============================================================
# TX ctrl byte dispatch table at &9C53/&9C5B
# ============================================================
# Used by the PHA/PHA/RTS dispatch at &9CCB.
# Y = tx_ctrl_byte (&81-&88), selects the transmit handler for
# each Econet operation type.
#
# Y   Target
# ──   ──────
# &81  &9CE8
# &82  &9CEC
# &83  &9D0B  (JSR/UserProc/OSProc share handler)
# &84  &9D0B
# &85  &9D0B
# &86  &9D45  (HALT/CONTINUE share handler)
# &87  &9D45
# &88  &9CE4
for y in range(0x81, 0x89):
    rts_code_ptr(0x9C53 + y, 0x9C5B + y)

# ============================================================
# Immediate operation RX handler labels (&9A9F-&9ADB)
# ============================================================
# Targets of dispatch table 1 at &9A0E/&9A16.

label(0x9A9F, "rx_imm_exec")
subroutine(0x9A9F, "rx_imm_exec", hook=None,
    title="RX immediate: JSR/UserProc/OSProc setup",
    description="""\
Sets up the port buffer to receive remote procedure data.
Copies the 4-byte remote address from rx_remote_addr into
the execution address workspace, then jumps to the common
receive path. Used for operation types &83-&85.""")

label(0x9ABD, "rx_imm_poke")
subroutine(0x9ABD, "rx_imm_poke", hook=None,
    title="RX immediate: POKE setup",
    description="""\
Sets up workspace offsets for receiving POKE data, then
jumps to the common data-receive path.""")

label(0x9AC8, "rx_imm_machine_type")
subroutine(0x9AC8, "rx_imm_machine_type", hook=None,
    title="RX immediate: machine type query",
    description="""\
Sets up a buffer just below the screen (length &01FC) for
the machine type query response. Returns system
identification data to the remote station.""")

label(0x9ADB, "rx_imm_peek")
subroutine(0x9ADB, "rx_imm_peek", hook=None,
    title="RX immediate: PEEK setup",
    description="""\
Saves the current TX block pointer, replaces it with a
pointer to the workspace, and prepares to send the PEEK
response data back to the requesting station.""")

# ============================================================
# TX completion handler labels (&9B9B-&9BDD)
# ============================================================
# Targets of dispatch table 2 at &9B0E/&9B13.

label(0x9B9B, "tx_done_jsr")
subroutine(0x9B9B, "tx_done_jsr", hook=None,
    title="TX done: remote JSR execution",
    description="""\
Pushes a return address on the stack (pointing to
tx_done_exit), then does JMP indirect to call the remote
JSR target routine. When that routine returns via RTS,
control resumes at tx_done_exit.""")

label(0x9BA4, "tx_done_user_proc")
subroutine(0x9BA4, "tx_done_user_proc", hook=None,
    title="TX done: UserProc event",
    description="""\
Generates a network event (event 8) via OSEVEN with the
remote address. This notifies the user program that a
UserProc operation has completed.""")

label(0x9BB2, "tx_done_os_proc")
subroutine(0x9BB2, "tx_done_os_proc", hook=None,
    title="TX done: OSProc call",
    description="""\
Calls the ROM entry point at &8000 (rom_header) with
X/Y from the remote address workspace. This invokes an
OS-level procedure on behalf of the remote station.""")

label(0x9BBE, "tx_done_halt")
subroutine(0x9BBE, "tx_done_halt", hook=None,
    title="TX done: HALT",
    description="""\
Sets bit 2 of rx_flags, enables interrupts, and spin-waits
until bit 2 is cleared (by a CONTINUE from the remote
station). If bit 2 is already set, skips to exit.""")

label(0x9BD5, "tx_done_continue")
subroutine(0x9BD5, "tx_done_continue", hook=None,
    title="TX done: CONTINUE",
    description="""\
Clears bit 2 of rx_flags, releasing any station that is
halted and spinning in tx_done_halt.""")

label(0x9BDD, "tx_done_exit")

# ============================================================
# TX ctrl byte handler labels (&9CE8-&9D45)
# ============================================================
# Targets of dispatch table 3 at &9C53/&9C5B.

label(0x9CE8, "tx_ctrl_peek")
subroutine(0x9CE8, "tx_ctrl_peek", hook=None,
    title="TX ctrl: PEEK transfer setup",
    description="""\
Sets scout_status=3, then performs a 4-byte addition of
bytes from the TX block into the transfer parameter
workspace (with carry propagation). Calls tx_calc_transfer
to finalise, then exits via tx_ctrl_exit.""")

label(0x9CEC, "tx_ctrl_poke")
subroutine(0x9CEC, "tx_ctrl_poke", hook=None,
    title="TX ctrl: POKE transfer setup",
    description="""\
Sets scout_status=2 and shares the 4-byte addition and
transfer calculation path with tx_ctrl_peek.""")

label(0x9D0B, "tx_ctrl_proc")
subroutine(0x9D0B, "tx_ctrl_proc", hook=None,
    title="TX ctrl: JSR/UserProc/OSProc setup",
    description="""\
Sets scout_status=2 and calls tx_calc_transfer directly
(no 4-byte address addition needed for procedure calls).
Shared by operation types &83-&85.""")

label(0x9D45, "tx_ctrl_exit")

# Alternate entry into ctrl_block_setup (&9162)
entry(0x9159)   # ADLC setup: LDX #&0D; LDY #&7C; BIT &833A; BVS c9167

# Dispatch targets found in equb data regions
# These are the bodies of the econet function dispatch handlers.
# Functions 1-3 share a handler (&91C7) — possibly different
# sub-operations that share setup logic. Function 5 (&91B5) and
# function 8 (&90CD) are distinct. The exact purpose of each
# function code hasn't been fully determined yet.
entry(0x91B5)   # Function 5 handler
entry(0x91C7)   # Function 1/2/3 handler (shared)
entry(0x90CD)   # Function 8 handler

# --- Code found in third-pass remaining equb regions ---
entry(0x8741)   # BEQ +3; JMP &8844 (called from &8743 region)
entry(0x8E7B)   # CMP #6; BCS ... (after 2-byte inline data table at &8E79)
entry(0x8F57)   # LDY #&28; ... (preceded by RTS, standalone entry)

# --- Code found in fourth-pass small equb regions ---
entry(0x8D5C)   # JSR ... (preceded by RTS, standalone entry)

# --- Dispatch targets from fs_cmd_match_table (PHA/PHA/RTS) ---
entry(0x8BF2)   # *EX handler (dispatch from command match table)
entry(0x8D06)   # "I AM" handler (dispatch from command match table)
entry(0x982D)   # LDA #&82; STA &FEA0; installs NMI handler &9839

# ============================================================
# Inline comments for key instructions
# ============================================================
# Note: acorn.bbc()'s hooks auto-annotate OSBYTE/OSWORD calls, so
# we only add comments where the auto-annotations don't reach.

# ============================================================
# Save FSCV arguments (&8508)
# ============================================================
subroutine(0x8508, "save_fscv_args", hook=None,
    title="Save FSCV/vector arguments",
    description="""\
Stores A, X, Y into the filing system workspace. Called at the
start of every FS vector handler (FILEV, ARGSV, BGETV, BPUTV,
GBPBV, FINDV, FSCV). NFS repurposes CFS/RFS workspace locations:
  &BD (fs_last_byte_flag) = A (function code / command)
  &BB (fs_options)        = X (control block ptr low)
  &BC (fs_block_offset)   = Y (control block ptr high)
  &BE/&BF (fs_crc_lo/hi)  = X/Y (duplicate for indexed access)""",
    on_entry={"a": "function code", "x": "control block pointer low", "y": "control block pointer high"})

# ============================================================
# Attribute decoding (&8513 / &851D)
# ============================================================
subroutine(0x8513, "decode_attribs_6bit", hook=None,
    title="Decode file attributes: FS → BBC format (FSBBC, 6-bit variant)",
    description="""\
Reads attribute byte at offset &0E from the parameter block,
masks to 6 bits, then falls through to the shared bitmask
builder. Converts fileserver protection format (5-6 bits) to
BBC OSFILE attribute format (8 bits) via the lookup table at
&8530. The two formats use different bit layouts for file
protection attributes.""")

subroutine(0x851D, "decode_attribs_5bit", hook=None,
    title="Decode file attributes: BBC → FS format (BBCFS, 5-bit variant)",
    description="""\
Masks A to 5 bits and builds an access bitmask via the
lookup table at &8530. Each input bit position maps to a
different output bit via the table. The conversion is done
by iterating through the source bits and OR-ing in the
corresponding destination bits from the table, translating
between BBC (8-bit) and fileserver (5-bit) protection formats.""",
    on_entry={"a": "BBC attribute byte (bits 0-4 used)"},
    on_exit={"a": "FS attribute bitmask (5-bit)", "x": "corrupted"})

# ============================================================
# Skip spaces (&8555)
# ============================================================
subroutine(0x8555, "skip_spaces", hook=None,
    title="Skip leading spaces in parameter block",
    description="""\
Advances Y past space characters in (fs_options),Y.
Returns with the first non-space character in A.
Sets carry if the character is >= 'A' (alphabetic).""")

# ============================================================
# Decimal number parser (&8560)
# ============================================================
subroutine(0x8560, "parse_decimal",
    title="Parse decimal number from (fs_options),Y (DECIN)",
    description="""\
Reads ASCII digits and accumulates in &B2 (fs_load_addr_2).
Multiplication by 10 uses the identity: n*10 = n*8 + n*2,
computed as ASL &B2 (x2), then A = &B2*4 via two ASLs,
then ADC &B2 gives x10.
Terminates on "." (pathname separator), control chars, or space.
The delimiter handling was revised to support dot-separated path
components (e.g. "1.$.PROG",
    on_entry={"y": "offset into (fs_options) buffer"},
    on_exit={"a": "parsed value (accumulated in &B2)", "x": "preserved", "y": "offset past last digit parsed"})
>= &40 (any letter), but the revision allows numbers followed
by dots.""",
    on_entry={"y": "offset into (fs_options) buffer"},
    on_exit={"a": "parsed value (accumulated in &B2)",
             "x": "initial A value (saved by TAX)",
             "y": "offset past last digit parsed"})
comment(0x8560, "Save A in X for caller", inline=True)
comment(0x8561, "Zero accumulator", inline=True)
comment(0x8565, "Load next char from buffer", inline=True)
comment(0x8567, "Letter or above?", inline=True)
comment(0x8569, "Yes: not a digit, done", inline=True)
comment(0x856B, "Dot separator?", inline=True)
comment(0x856D, "Yes: exit with C=1 (dot found)", inline=True)
comment(0x856F, "Control char or space: done", inline=True)
comment(0x8571, "Mask ASCII digit to 0-9", inline=True)
comment(0x8573, "Save new digit", inline=True)
comment(0x8575, "Running total * 2", inline=True)
comment(0x8577, "A = running total * 2", inline=True)
comment(0x8579, "A = running total * 4", inline=True)
comment(0x857A, "A = running total * 8", inline=True)
comment(0x857B, "+ total*2 = total * 10", inline=True)
comment(0x857D, "+ digit = total*10 + digit", inline=True)
comment(0x857F, "Store new running total", inline=True)
comment(0x8581, "Advance to next char", inline=True)
comment(0x8582, "Loop (always: Y won't wrap to 0)", inline=True)
comment(0x8584, "No dot found: C=0", inline=True)
comment(0x8585, "Return result in A", inline=True)

# ============================================================
# File handle conversion (&8588-&858A)
# ============================================================
subroutine(0x8588, "handle_to_mask_a", hook=None,
    title="Convert handle in A to bitmask",
    description="""\
Transfers A to Y via TAY, then falls through to
handle_to_mask_clc to clear carry and convert.""",
    on_entry={"a": "file handle number (&20-&27, or 0)"},
    on_exit={"a": "preserved", "x": "preserved", "y": "bitmask (single bit set) or &FF if invalid"})

subroutine(0x8589, "handle_to_mask_clc", hook=None,
    title="Convert handle to bitmask (carry cleared)",
    description="""\
Clears carry to ensure handle_to_mask converts
unconditionally. Falls through to handle_to_mask.""",
    on_entry={"y": "file handle number (&20-&27, or 0)"},
    on_exit={"a": "preserved", "x": "preserved", "y": "bitmask (single bit set) or &FF if invalid"})

subroutine(0x858A, "handle_to_mask",
    title="Convert file handle to bitmask (Y2FS)",
    description="""\
Converts fileserver handles to single-bit masks segregated inside
the BBC. NFS handles occupy the &20-&27 range (base HAND=&20),
which cannot collide with local filing system or cassette handles
-- the MOS routes OSFIND/OSBGET/OSBPUT to the correct filing
system based on the handle value alone. The power-of-two encoding
allows the EOF hint byte to track up to 8 files simultaneously
with one bit per file, and enables fast set operations (ORA to
add, EOR to toggle, AND to test) without loops. Handle 0 passes
through unchanged (means "no file",
    on_entry={"y": "handle number", "c": "0: convert, 1 with Y=0: skip, 1 with Y!=0: convert"},
    on_exit={"a": "preserved", "x": "preserved", "y": "bitmask (single bit set) or &FF if handle invalid"})
has a built-in validity check: if the handle is out of range, the
repeated ASL shifts all bits out, leaving A=0, which is converted
to Y=&FF as a sentinel -- bad handles fail gracefully rather than
indexing into garbage.
Callers needing to move the handle from A use handle_to_mask_a;
callers needing carry cleared use handle_to_mask_clc.""",
    on_entry={"y": "handle number",
              "c": "0: convert, 1 with Y=0: skip, 1 with Y!=0: convert"},
    on_exit={"a": "preserved",
             "x": "preserved",
             "y": "bitmask (single bit set) or &FF if handle invalid"})
comment(0x858A, "Save A (will be restored on exit)", inline=True)
comment(0x858B, "Save X (will be restored on exit)", inline=True)
comment(0x858C, "  (second half of X save)", inline=True)
comment(0x858D, "A = handle from Y", inline=True)
comment(0x858E, "C=0: always convert", inline=True)
comment(0x8590, "C=1 and Y=0: skip (handle 0 = none)", inline=True)
comment(0x8592, "C=1 and Y!=0: convert", inline=True)
comment(0x8593, "A = handle - &1F (1-based bit position)", inline=True)
comment(0x8595, "X = shift count", inline=True)
comment(0x8596, "Start with bit 0 set", inline=True)
comment(0x8598, "Shift bit left", inline=True)
comment(0x8599, "Count down", inline=True)
comment(0x859A, "Loop until correct position", inline=True)
comment(0x859C, "Undo final extra shift", inline=True)
comment(0x859D, "Y = resulting bitmask", inline=True)
comment(0x859E, "Non-zero: valid mask, skip to exit", inline=True)
comment(0x85A0, "Zero: invalid handle, set Y=&FF", inline=True)
comment(0x85A1, "Restore X", inline=True)
comment(0x85A3, "Restore A", inline=True)

# ============================================================
# Mask to handle (&85A5)
# ============================================================
subroutine(0x85A5, "mask_to_handle",
    title="Convert bitmask to handle number (FS2A)",
    description="""\
Inverse of Y2FS. Converts from the power-of-two FS format
back to a sequential handle number by counting right shifts
until A=0. Adds &1E to convert the 1-based bit position to
a handle number (handles start at &1F+1 = &20). Used when
receiving handle values from the fileserver in reply packets.""",
    on_entry={"a": "single-bit bitmask"},
    on_exit={"a": "handle number (&20-&27)",
             "x": "corrupted",
             "y": "preserved"})
comment(0x85A5, "X = 0 (bit position counter)", inline=True)
comment(0x85A7, "Count this bit position", inline=True)
comment(0x85A8, "Shift mask right; C=0 when done", inline=True)
comment(0x85A9, "Loop until all bits shifted out", inline=True)
comment(0x85AB, "A = bit position (1-based)", inline=True)
comment(0x85AC, "Add &1E+C(=0) = &1E; handle=&1F+pos", inline=True)

# ============================================================
# Print decimal number (&85AF)
# ============================================================
subroutine(0x85AF, "print_decimal", hook=None,
    title="Print byte as 3-digit decimal number",
    description="""\
Prints A as a decimal number using repeated subtraction
for each digit position (100, 10, 1). Leading zeros are
printed (no suppression). Used to display station numbers.""",
    on_entry={"a": "byte value to print"},
    on_exit={"a": "last digit character", "x": "corrupted", "y": "0 (remainder after last division)"})

subroutine(0x85BC, "print_decimal_digit", hook=None,
    title="Print one decimal digit by repeated subtraction",
    description="""\
Divides Y by A using repeated subtraction. Prints the
quotient as an ASCII digit ('0'-'9'). Returns with the
remainder in Y. X starts at &2F ('0'-1) and increments
once per subtraction, giving the ASCII digit directly.""",
    on_entry={"a": "divisor (stored to &B8)", "y": "dividend"},
    on_exit={"y": "remainder"})

# ============================================================
# Address comparison (&85CE)
# ============================================================
subroutine(0x85CE, "compare_addresses",
    title="Compare two 4-byte addresses",
    description="""\
Compares bytes at &B0-&B3 against &B4-&B7 using EOR.
Used by the OSFILE save handler to compare the current
transfer address (&C8-&CB, copied to &B0) against the end
address (&B4-&B7) during multi-block file data transfers.""",
    on_exit={"a": "corrupted (EOR result)",
             "x": "corrupted",
             "y": "preserved"})

# ============================================================
# FS flags (&85DF / &85E4)
# ============================================================
subroutine(0x85DF, "clear_fs_flag", hook=None,
    title="Clear bit(s) in FS flags (&0E07)",
    description="""\
Inverts A (EOR #&FF), then ANDs into fs_work_0e07 to clear
the specified bits. Falls through to set_fs_flag to store.""",
    on_entry={"a": "bitmask of bits to clear"},
    on_exit={"a": "updated fs_eof_flags value"})

subroutine(0x85E4, "set_fs_flag", hook=None,
    title="Set bit(s) in FS flags (&0E07)",
    description="""\
ORs A into fs_work_0e07 (EOF hint byte). Each bit represents
one of up to 8 open file handles. When clear, the file is
definitely NOT at EOF. When set, the fileserver must be queried
to confirm EOF status. This negative-cache optimisation avoids
expensive network round-trips for the common case. The hint is
cleared when the file pointer is updated (since seeking away
from EOF invalidates the hint) and set after BGET/OPEN/EOF
operations that might have reached the end.""",
    on_entry={"a": "bitmask of bits to set"},
    on_exit={"a": "updated fs_eof_flags value"})

# ============================================================
# Print file info (&8600)
# ============================================================
subroutine(0x8600, "print_file_info", hook=None,
    title="Print file catalogue line",
    description="""\
Displays a formatted catalogue entry: filename (padded to 12
chars with spaces), load address (4 hex bytes at offset 5-2),
exec address (4 hex bytes at offset 9-6), and file length
(3 hex bytes at offset &0C-&0A), followed by a newline.
Data is read from (fs_crc_lo) for the filename and from
(fs_options) for the numeric fields. Returns immediately
if fs_messages_flag is zero (no info available).""")

# ============================================================
# Hex printing (&85EB / &85F6)
# ============================================================
subroutine(0x85EB, "print_hex", hook=None,
    title="Print byte as two hex digits",
    description="""\
Prints the high nibble first (via 4× LSR), then the low
nibble. Each nibble is converted to ASCII '0'-'9' or 'A'-'F'
and output via OSASCI.""",
    on_entry={"a": "byte to print as two hex digits"},
    on_exit={"a": "preserved (original byte)", "x": "corrupted (by OSASCI)"})

# ============================================================
# TX control (&8644-&8650)
# ============================================================
subroutine(0x8644, "setup_tx_ptr_c0", hook=None,
    title="Set up TX pointer to control block at &00C0",
    description="""\
Points net_tx_ptr to &00C0 where the TX control block has
been built by init_tx_ctrl_block. Falls through to tx_poll_ff
to initiate transmission with full retry.""")

subroutine(0x864C, "tx_poll_ff", hook=None,
    title="Transmit and poll for result (full retry)",
    description="""\
Sets A=&FF (retry count) and Y=&60 (timeout parameter).
Falls through to tx_poll_core.""")

subroutine(0x8650, "tx_poll_core",
    title="Core transmit and poll routine (XMIT)",
    description="""\
Claims the TX semaphore (tx_ctrl_status) via ASL -- a busy-wait
spinlock where carry=0 means the semaphore is held by another
operation. Only after claiming the semaphore is the TX pointer
copied to nmi_tx_block, ensuring the low-level transmit code
sees a consistent pointer. Then calls the ADLC TX setup routine
and polls the control byte for completion:
  bit 7 set = still busy (loop)
  bit 6 set = error (check escape or report)
  bit 6 clear = success (clean return)
On error, checks for escape condition and handles retries.
Two entry points: setup_tx_ptr_c0 (&8644) always uses the
standard TXCB; tx_poll_core (&8650) is general-purpose.""",
    on_entry={"a": "retry count (&FF = full retry)",
              "y": "timeout parameter (&60 = standard)"},
    on_exit={"a": "entry A (retry count, restored from stack)",
             "x": "0",
             "y": "0"})

# ============================================================
# print_inline subroutine (&853B)
# ============================================================
# Label and code-tracing hook created by hook_subroutine() above.
subroutine(0x853B, "print_inline", hook=None,
    title="Print inline string, high-bit terminated (VSTRNG)",
    description="""\
Pops the return address from the stack, prints each byte via OSASCI
until a byte with bit 7 set is found, then jumps to that address.
The high-bit byte serves as both the string terminator and the opcode
of the first instruction after the string. N.B. Cannot be used for
BRK error messages -- the stack manipulation means a BRK in the
inline data would corrupt the stack rather than invoke the error
handler.""",
    on_exit={"a": "terminator byte (bit 7 set, also next opcode)",
             "x": "corrupted (by OSASCI)",
             "y": "0"})

comment(0x853B, "Pop return address (low) — points to last byte of JSR", inline=True)
comment(0x853E, "Pop return address (high)", inline=True)
comment(0x8543, "Advance pointer past return address / to next char", inline=True)
comment(0x8549, "Load next byte from inline string", inline=True)
comment(0x854B, "Bit 7 set? Done — this byte is the next opcode", inline=True)
comment(0x8552, "Jump to address of high-bit byte (resumes code after string)", inline=True)

# ============================================================
# Dispatch table comments (&8021-&8068)
# ============================================================
comment(0x8021, """\
Dispatch table: low bytes of (handler_address - 1)
Each entry stores the low byte of a handler address minus 1,
for use with the PHA/PHA/RTS dispatch trick at &809F.
See dispatch_0_hi (&8045) for the corresponding high bytes.

Five callers share this table via different Y base offsets:
  Y=&00  Service calls 0-12       (indices 1-13)
  Y=&0D  Language entry reasons    (indices 14-18)
  Y=&12  FSCV codes 0-7           (indices 19-26)
  Y=&16  FS reply handlers        (indices 27-32)
  Y=&20  *NET1-4 sub-commands     (indices 33-36)""")

comment(0x8045, """\
Dispatch table: high bytes of (handler_address - 1)
Paired with dispatch_0_lo (&8021). Together they form a table
of 37 handler addresses, used via the PHA/PHA/RTS trick at
&809F.""")

# Dispatch table inline comments (lo and hi bytes).
# The comment bodies are defined once and emitted for both halves so
# they stay in sync.
dispatch_comments = [
    # Service call handlers (Y=&00, indices 1-13)
    "Svc 0: already claimed (no-op)",
    "Svc 1: absolute workspace",
    "Svc 2: private workspace",
    "Svc 3: auto-boot",
    "Svc 4: unrecognised star command",
    "Svc 5: unrecognised interrupt",
    "Svc 6: BRK (no-op)",
    "Svc 7: unrecognised OSBYTE",
    "Svc 8: unrecognised OSWORD",
    "Svc 9: *HELP",
    "Svc 10: static workspace (no-op)",
    "Svc 11: NMI release (reclaim NMIs)",
    "Svc 12: NMI claim (save NMI state)",
    # Language entry handlers (Y=&0D, indices 14-18)
    "Lang 0: no language / Tube",
    "Lang 1: normal startup",
    "Lang 2: softkey byte (Electron)",
    "Lang 3: softkey length (Electron)",
    "Lang 4: remote validated",
    # FSCV handlers (Y=&12, indices 19-26)
    "FSCV 0: *OPT",
    "FSCV 1: EOF check",
    "FSCV 2: */ (run)",
    "FSCV 3: unrecognised star command",
    "FSCV 4: *RUN",
    "FSCV 5: *CAT",
    "FSCV 6: shutdown",
    "FSCV 7: read handle range",
    # FS reply handlers (Y=&16, indices 27-32)
    "FS reply: print directory name",
    "FS reply: copy handles + boot",
    "FS reply: copy handles",
    "FS reply: set CSD handle",
    "FS reply: notify + execute",
    "FS reply: set library handle",
    # *NET sub-command handlers (Y=&20, indices 33-36)
    "*NET1: read handle from packet",
    "*NET2: read handle from workspace",
    "*NET3: close handle",
    "*NET4: resume remote",
]
for i, body in enumerate(dispatch_comments):
    comment(0x8021 + i, f"lo - {body}", inline=True)
    comment(0x8045 + i, f"hi - {body}", inline=True)

# ============================================================
# *NET command dispatch (&8069)
# ============================================================
subroutine(0x8069, "dispatch_net_cmd", hook=None,
    title="*NET command dispatcher",
    description="""\
Parses the character after *NET as '1'-'4', maps to table
indices 33-36 via base offset Y=&20, and dispatches via &809F.
Characters outside '1'-'4' fall through to return_1 (RTS).

These are internal sub-commands used only by the ROM itself,
not user-accessible star commands. The MOS command parser
requires a space or terminator after 'NET', so *NET1 typed
at the command line does not match; these are reached only
via OSCLI calls within the ROM.

*NET1 (&8DAF): read file handle from received
packet (net_1_read_handle)

*NET2 (&8DC9): read handle entry from workspace
(net_2_read_handle_entry)

*NET3 (&8DDF): close handle / mark as unused
(net_3_close_handle)

*NET4 (&8DF2): resume after remote operation
(net_4_resume_remote)""")

comment(0x8069, "Read command character following *NET", inline=True)
comment(0x806B, "Subtract ASCII '1' to get 0-based command index", inline=True)
comment(0x8075, "Y=&20: base offset for *NET commands (index 33+)", inline=True)

# ============================================================
# PHA/PHA/RTS dispatcher (&809F)
# ============================================================
subroutine(0x809F, "dispatch", hook=None,
    title="PHA/PHA/RTS computed dispatch",
    description="""\
X = command index within caller's group (e.g. service number)
Y = base offset into dispatch table (0, &0D, &20, etc.)
The loop adds Y+1 to X, so final X = command index + base + 1.
Then high and low bytes of (handler-1) are pushed onto the stack,
and RTS pops them and jumps to handler_address.

This is a standard 6502 trick: RTS increments the popped address
by 1 before jumping, so the table stores (address - 1) to
compensate. Multiple callers share one table via different Y
base offsets.""")

comment(0x809F, "Add base offset Y to index X (loop: X += Y+1)", inline=True)
comment(0x80A4, "Load high byte of (handler - 1) from table", inline=True)
comment(0x80A7, "Push high byte onto stack", inline=True)
comment(0x80A8, "Load low byte of (handler - 1) from table", inline=True)
comment(0x80AB, "Push low byte onto stack", inline=True)
comment(0x80AC, "Restore X (fileserver options) for use by handler", inline=True)
comment(0x80AE, "RTS pops address, adds 1, jumps to handler", inline=True)

# ============================================================
# Language entry dispatch (&8099)
# ============================================================
subroutine(0x8099, "lang_entry_dispatch", hook=None,
    title="Language entry dispatcher",
    description="""\
Called when the NFS ROM is entered as a language. Although rom_type
(&82) does not set the language bit, the MOS enters this point
after NFS claims service &FE (Tube post-init). X = reason code
(0-4). Dispatches via table indices 14-18 (base offset Y=&0D).""")

comment(0x809D, "Y=&0D: base offset for language handlers (index 14+)", inline=True)

# ============================================================
# Service call dispatch (&8127)
# ============================================================
subroutine(0x8127, "dispatch_service", hook=None,
    title="Service call dispatcher",
    description="""\
Dispatches MOS service calls 0-12 via the shared dispatch table.
Uses base offset Y=0, so table index = service number + 1.
Service numbers >= 13 are ignored (branch to return_2).
Called via JSR &809F rather than fall-through, so it returns
to &813C to restore saved registers.""")

comment(0x8137, "Y=0: base offset for service calls (index 1+)", inline=True)

# ============================================================
# Service handler entry (&80AF)
# ============================================================
subroutine(0x80AF, "service_handler_entry", hook=None,
    title="Service handler entry",
    description="""\
Intercepts three special service calls before normal dispatch:
  &FE: Tube init — explode character definitions (OSBYTE &14, X=6)
  &FF: Full init — set up WRCHV/RDCHV/BRKV/EVNTV, copy NMI handler
       code from ROM to RAM pages &04-&06, copy workspace init to
       &0016-&0076, then fall through to select NFS.
  &12 with Y=5: Select NFS as active filing system.
All other service calls dispatch via dispatch_service (&8127).""")

# ============================================================
# Init: set up vectors and copy code (&80C8)
# ============================================================
subroutine(0x80C8, "init_vectors_and_copy", hook=None,
    title="NFS initialisation (service &FF: full reset)",
    description="""\
Sets up OS vectors for Tube co-processor support:
  WRCHV = &051C (page 5 — WRCH handler)
  RDCHV = &04E7 (page 4 — RDCH handler)
  BRKV  = &0016 (workspace — BRK/error handler)
  EVNTV = &06E8 (page 6 — event handler)
Writes &8E to Tube control register (&FEE0).
Then copies 3 pages of Tube host code from reloc_p4_src
to RAM (&0400/&0500/&0600), calls tube_post_init (&0414),
and copies 97 bytes of workspace init from reloc_zp_src
to &0016-&0076.""")

comment(0x80C8, "Set WRCHV = &051C (Tube WRCH handler)", inline=True)
comment(0x80D2, "Set RDCHV = &04E7 (Tube RDCH handler)", inline=True)
comment(0x80DC, "Set BRKV = &0016 (BRK handler in workspace)", inline=True)
comment(0x80E6, "Set EVNTV = &06E8 (event handler in page 6)", inline=True)
comment(0x80F0, "Write &8E to Tube control register", inline=True)

# ============================================================
# Select NFS as active filing system (&8184)
# ============================================================
subroutine(0x8184, "select_nfs", hook=None,
    title="Select NFS as active filing system (INIT)",
    description="""\
Reached from service &12 (select FS) with Y=5, or when *NET command
selects NFS. Notifies the current FS of shutdown via FSCV A=6 —
this triggers the outgoing FS to save its context back to its
workspace page, allowing restoration if re-selected later (the
FSDIE handoff mechanism). Then sets up the standard OS vector
indirections (FILEV through FSCV) to NFS entry points, claims the
extended vector table entries, and issues service &0F (vectors
claimed) to notify other ROMs. If nfs_temp is zero (auto-boot
not inhibited), injects the synthetic command "I .BOOT" through
the command decoder to trigger auto-boot login.""")

# ============================================================
# Print station identification (&81E6)
# ============================================================
subroutine(0x81E6, "print_station_info", hook=None,
    title="Print station identification",
    description="""\
Prints "Econet Station <n>" using the station number from the net
receive buffer, then tests ADLC SR2 for the network clock signal —
prints " No Clock" if absent. Falls through to init_fs_vectors.""")

# ============================================================
# Initialise filing system vectors (&8217)
# ============================================================
subroutine(0x8217, "init_fs_vectors", hook=None,
    title="Initialise filing system vectors",
    description="""\
Copies 14 bytes from fs_vector_addrs (&824D) into FILEV-FSCV (&0212),
setting all 7 filing system vectors to the extended vector dispatch
addresses (&FF1B-&FF2D). Calls setup_rom_ptrs_netv to install the
ROM pointer table entries with the actual NFS handler addresses. Also
reached directly from select_nfs, bypassing the station display.
Falls through to issue_vectors_claimed.""")

comment(0x8217, "Copy 14 bytes: FS vector addresses → FILEV-FSCV", inline=True)

# ============================================================
# FS vector dispatch and handler addresses (&824D)
# ============================================================
subroutine(0x824D, "fs_vector_addrs", hook=None,
    title="FS vector dispatch and handler addresses (34 bytes)",
    description="""\
Bytes 0-13: extended vector dispatch addresses, copied to
FILEV-FSCV (&0212) by init_fs_vectors. Each 2-byte pair is
a dispatch address (&FF1B-&FF2D) that the MOS uses to look up
the handler in the ROM pointer table.

Bytes 14-33: handler address pairs read by store_rom_ptr_pair.
Each entry has addr_lo, addr_hi, then a padding byte that is
overwritten with the current ROM bank number at runtime. The
last entry (FSCV) has no padding byte.""")

# Part 1: extended vector dispatch addresses (7 x 2 bytes)
byte(0x824D, 1)
comment(0x824D, "FILEV dispatch lo", inline=True)
byte(0x824E, 1)
comment(0x824E, "FILEV dispatch hi", inline=True)
byte(0x824F, 1)
comment(0x824F, "ARGSV dispatch lo", inline=True)
byte(0x8250, 1)
comment(0x8250, "ARGSV dispatch hi", inline=True)
byte(0x8251, 1)
comment(0x8251, "BGETV dispatch lo", inline=True)
byte(0x8252, 1)
comment(0x8252, "BGETV dispatch hi", inline=True)
byte(0x8253, 1)
comment(0x8253, "BPUTV dispatch lo", inline=True)
byte(0x8254, 1)
comment(0x8254, "BPUTV dispatch hi", inline=True)
byte(0x8255, 1)
comment(0x8255, "GBPBV dispatch lo", inline=True)
byte(0x8256, 1)
comment(0x8256, "GBPBV dispatch hi", inline=True)
byte(0x8257, 1)
comment(0x8257, "FINDV dispatch lo", inline=True)
byte(0x8258, 1)
comment(0x8258, "FINDV dispatch hi", inline=True)
byte(0x8259, 1)
comment(0x8259, "FSCV dispatch lo", inline=True)
byte(0x825A, 1)
comment(0x825A, "FSCV dispatch hi", inline=True)

# Part 2: handler address entries (7 x {lo, hi, pad})
byte(0x825B, 1)
comment(0x825B, "FILEV handler lo (&8694)", inline=True)
byte(0x825C, 1)
comment(0x825C, "FILEV handler hi", inline=True)
byte(0x825D, 1)
comment(0x825D, "(ROM bank — overwritten)", inline=True)
byte(0x825E, 1)
comment(0x825E, "ARGSV handler lo (&88E1)", inline=True)
byte(0x825F, 1)
comment(0x825F, "ARGSV handler hi", inline=True)
byte(0x8260, 1)
comment(0x8260, "(ROM bank — overwritten)", inline=True)
byte(0x8261, 1)
comment(0x8261, "BGETV handler lo (&8485)", inline=True)
byte(0x8262, 1)
comment(0x8262, "BGETV handler hi", inline=True)
byte(0x8263, 1)
comment(0x8263, "(ROM bank — overwritten)", inline=True)
byte(0x8264, 1)
comment(0x8264, "BPUTV handler lo (&83A2)", inline=True)
byte(0x8265, 1)
comment(0x8265, "BPUTV handler hi", inline=True)
byte(0x8266, 1)
comment(0x8266, "(ROM bank — overwritten)", inline=True)
byte(0x8267, 1)
comment(0x8267, "GBPBV handler lo (&89EA)", inline=True)
byte(0x8268, 1)
comment(0x8268, "GBPBV handler hi", inline=True)
byte(0x8269, 1)
comment(0x8269, "(ROM bank — overwritten)", inline=True)
byte(0x826A, 1)
comment(0x826A, "FINDV handler lo (&8949)", inline=True)
byte(0x826B, 1)
comment(0x826B, "FINDV handler hi", inline=True)
byte(0x826C, 1)
comment(0x826C, "(ROM bank — overwritten)", inline=True)
byte(0x826D, 1)
comment(0x826D, "FSCV handler lo (&808C)", inline=True)
byte(0x826E, 1)
comment(0x826E, "FSCV handler hi", inline=True)

# ============================================================
# Service 1: claim absolute workspace (&826F)
# ============================================================
subroutine(0x826F, "svc_1_abs_workspace", hook=None,
    title="Service 1: claim absolute workspace",
    description="""\
Claims pages up to &10 for NMI workspace (&0D), FS state (&0E),
and FS command buffer (&0F). If Y >= &10, workspace already
allocated — returns unchanged.""",
    on_entry={"y": "current top of absolute workspace"},
    on_exit={"y": "updated top of absolute workspace (max of input and &10)"})

# ============================================================
# Service 2: claim private workspace (&8278)
# ============================================================
subroutine(0x8278, "svc_2_private_workspace", hook=None,
    title="Service 2: claim private workspace and initialise NFS",
    description="""\
Y = next available workspace page on entry.
Sets up net_rx_ptr (Y) and nfs_workspace (Y+1) page pointers.
On soft break (OSBYTE &FD returns 0): skips FS state init,
preserving existing login state, file server selection, and
control block configuration — this is why pressing BREAK
keeps the user logged in.
On power-up/CTRL-BREAK (result non-zero):
  - Sets FS server station to &FE (FS, the default; no server)
  - Sets printer server to &EB (PS, the default)
  - Clears FS handles, OPT byte, message flag, SEQNOS
  - Initialises all RXCBs with &3F flag (available)
In both cases: reads station ID from &FE18 (only valid during
reset), calls adlc_init, enables user-level RX (LFLAG=&40).""",
    on_entry={"y": "next available workspace page"},
    on_exit={"y": "next available workspace page after NFS (input + 2)"})

comment(0x828F, "OSBYTE &FD: read type of last reset", inline=True)
comment(0x8295, "Soft break (X=0): skip FS init", inline=True)
comment(0x829B, "Station &FE = no server selected", inline=True)
comment(0x82C3, "Read station ID (also INTOFF)", inline=True)
comment(0x82C9, "Initialise ADLC hardware", inline=True)

# ============================================================
# Service 3: auto-boot (&81D1)
# ============================================================
subroutine(0x81D1, "svc_3_autoboot", hook=None,
    title="Service 3: auto-boot",
    description="""\
Notifies current FS of shutdown via FSCV A=6. Scans keyboard
(OSBYTE &7A): if the 'N' key is pressed (matrix address &55),
the keypress is forgotten via OSBYTE &78 and auto-boot proceeds.
Any other key causes the auto-boot to be declined. If no key is
pressed, auto-boot proceeds directly. Falls through to
print_station_info, then init_fs_vectors.""")

# ============================================================
# Service 4: unrecognised * command (&8172)
# ============================================================
subroutine(0x8172, "svc_4_star_command", hook=None,
    title="Service 4: unrecognised * command",
    description="""\
Matches the command text against ROM string table entries.
Both entries reuse bytes from the ROM header to save space:

  X=8: matches "ROFF" at copyright_string+3 — the suffix
       of "(C)ROFF" → *ROFF (Remote Off, end remote
       session) — jumps to resume_after_remote

  X=1: matches "NET" at &8009 — the ROM title string
       → *NET (select NFS) — falls through to select_nfs

If neither matches, returns with the service call
unclaimed.""")

# ============================================================
# Service 9: *HELP (&81BC)
# ============================================================
subroutine(0x81BC, "svc_9_help", hook=None,
    title="Service 9: *HELP",
    description="""\
Prints the ROM identification string using print_inline.""")

# ============================================================
# Match ROM string (&819B)
# ============================================================
subroutine(0x819B, "match_rom_string", hook=None,
    title="Match command text against ROM string table",
    description="""\
Compares characters from (os_text_ptr)+Y against bytes starting
at binary_version+X (&8008+X). Input is uppercased via AND &DF.
Returns with Z=1 if the ROM string's NUL terminator was reached
(match), or Z=0 if a mismatch was found. On match, Y points
past the matched text; on return, skips trailing spaces.""")
comment(0x819B, "Y = saved text pointer offset", inline=True)
comment(0x819D, "Load next input character", inline=True)
comment(0x819F, "Force uppercase (clear bit 5)", inline=True)
comment(0x81A1, "Input char is NUL/space: check ROM byte", inline=True)
comment(0x81A3, "Compare with ROM string byte", inline=True)
comment(0x81A6, "Mismatch: check if ROM string ended", inline=True)
comment(0x81A8, "Advance input pointer", inline=True)
comment(0x81A9, "Advance ROM string pointer", inline=True)
comment(0x81AA, "Continue matching (always taken)", inline=True)
comment(0x81AC, "Load ROM string byte at match point", inline=True)
comment(0x81AF, "Zero = end of ROM string = full match", inline=True)
comment(0x81B1, "Non-zero = partial/no match; Z=0", inline=True)
comment(0x81B2, "Skip this space", inline=True)
comment(0x81B3, "Load next input character", inline=True)
comment(0x81B5, "Is it a space?", inline=True)
comment(0x81B7, "Yes: keep skipping", inline=True)
comment(0x81B9, "XOR with CR: Z=1 if end of line", inline=True)

# ============================================================
# Call FSCV shutdown (&81CC)
# ============================================================
subroutine(0x81CC, "call_fscv_shutdown", hook=None,
    title="Notify filing system of shutdown",
    description="""\
Loads A=6 (FS shutdown notification) and JMP (FSCV).
The FSCV handler's RTS returns to the caller of this routine
(JSR/JMP trick saves one level of stack).""")

# ============================================================
# Issue service: vectors claimed (&822E)
# ============================================================
subroutine(0x822E, "issue_vectors_claimed", hook=None,
    title="Issue 'vectors claimed' service and optionally auto-boot",
    description="""\
Issues service &0F (vectors claimed) via OSBYTE &8F, then
service &0A. If nfs_temp is zero (auto-boot not inhibited),
sets up the command string "I .BOOT" at &8245 and jumps to
the FSCV 3 unrecognised-command handler (which matches against
the command table at &8BD6). The "I." prefix triggers the
catch-all entry which forwards the command to the fileserver.
Falls through to run_fscv_cmd.""")

# ============================================================
# Run FSCV command from ROM (&8240)
# ============================================================
subroutine(0x8240, "run_fscv_cmd", hook=None,
    title="Run FSCV command from ROM",
    description="""\
Sets Y to the ROM page high byte (&82) and jumps to fscv_3_star_cmd
to execute the command string at (X, Y). X is pre-loaded by the
caller with the low byte of the string address. Also used as a
data base address by store_rom_ptr_pair for Y-indexed access to
the handler address table.""")

# ============================================================
# Auto-boot command string (&8245)
# ============================================================
string(0x8245, 8)
comment(0x8245, """\
Synthetic auto-boot command string. "I " does not match any
entry in NFS's local command table — "I." requires a dot, and
"I AM" requires 'A' after the space — so fscv_3_star_cmd
forwards the entire string to the fileserver, which executes
the .BOOT file.""")

# ============================================================
# Set up ROM pointer table and NETV (&82D1)
# ============================================================
subroutine(0x82D1, "setup_rom_ptrs_netv", hook=None,
    title="Set up ROM pointer table and NETV",
    description="""\
Reads the ROM pointer table base address via OSBYTE &A8, stores
it in osrdsc_ptr (&F6). Sets NETV low byte to &36. Then copies
one 3-byte extended vector entry (addr=&9007, rom=current) into
the ROM pointer table at offset &36, installing osword_dispatch
as the NETV handler.""")

# ============================================================
# FSCV shutdown: save FS state (&82FD)
# ============================================================
subroutine(0x82FD, "fscv_6_shutdown", hook=None,
    title="FSCV 6: Filing system shutdown / save state (FSDIE)",
    description="""\
Called when another filing system (e.g. DFS) is selected. Saves
the current NFS context (FSLOCN station number, URD/CSD/LIB
handles, OPT byte, etc.) from page &0E into the dynamic workspace
backup area. This allows the state to be restored when *NET is
re-issued later, without losing the login session. Finally calls
OSBYTE &7B (printer driver going dormant) to release the
Econet network printer on FS switch.""")

# ============================================================
# Init TX control block (&831C)
# ============================================================
subroutine(0x831C, "init_tx_ctrl_block", hook=None,
    title="Initialise TX control block at &00C0 from template",
    description="""\
Copies 12 bytes from tx_ctrl_template (&8334) to &00C0.
For the first 2 bytes (Y=0,1), also copies the fileserver
station/network from &0E00/&0E01 to &00C2/&00C3.
The template sets up: control=&80, port=&99 (FS command port),
command data length=&0F, plus padding bytes.""")

subroutine(0x8334, "tx_ctrl_template", hook=None,
    title="TX control block template (TXTAB, 12 bytes)",
    description="""\
12-byte template copied to &00C0 by init_tx_ctrl. Defines the
TX control block for FS commands: control flag, port, station/
network, and data buffer pointers (&0F00-&0FFF). The 4-byte
Econet addresses use only the low 2 bytes; upper bytes are &FF.""")
byte(0x8334, 1)
comment(0x8334, "Control flag", inline=True)
byte(0x8335, 1)
comment(0x8335, "Port (FS command = &99)", inline=True)
byte(0x8336, 1)
comment(0x8336, "Station (filled at runtime)", inline=True)
byte(0x8337, 1)
comment(0x8337, "Network (filled at runtime)", inline=True)
byte(0x8338, 1)
comment(0x8338, "Buffer start low", inline=True)
byte(0x8339, 1)
comment(0x8339, "Buffer start high (page &0F)", inline=True)
byte(0x833A, 1)
comment(0x833A, "Buffer start pad (4-byte Econet addr)", inline=True)
byte(0x833B, 1)
comment(0x833B, "Buffer start pad", inline=True)
byte(0x833C, 1)
comment(0x833C, "Buffer end low", inline=True)
byte(0x833D, 1)
comment(0x833D, "Buffer end high (page &0F)", inline=True)
byte(0x833E, 1)
comment(0x833E, "Buffer end pad", inline=True)
byte(0x833F, 1)
comment(0x833F, "Buffer end pad", inline=True)

subroutine(0x8340, "prepare_cmd_with_flag", hook=None,
    title="Prepare FS command with carry set",
    description="""\
Alternate entry to prepare_fs_cmd that pushes A, loads &2A
into fs_error_ptr, and enters with carry set (SEC). The carry
flag is later tested by build_send_fs_cmd to select the
byte-stream (BSXMIT) transmission path.""",
    on_entry={"a": "flag byte to include in FS command", "y": "function code for FS header"})

# ============================================================
# Prepare FS command (&8350)
# ============================================================
subroutine(0x8350, "prepare_fs_cmd",
    title="Prepare FS command buffer (12 references)",
    description="""\
Builds the 5-byte FS protocol header at &0F00:
  &0F00 HDRREP = reply port (set downstream, typically &90/PREPLY)
  &0F01 HDRFN  = Y parameter (function code)
  &0F02 HDRURD = URD handle (from &0E02)
  &0F03 HDRCSD = CSD handle (from &0E03)
  &0F04 HDRLIB = LIB handle (from &0E04)
Command-specific data follows at &0F05 (TXBUF). Also clears V flag.
Called before building specific FS commands for transmission.""",
    on_entry={"y": "function code for HDRFN",
              "x": "preserved through header build"},
    on_exit={"a": "0 on success (from build_send_fs_cmd)",
             "x": "0 on success, &D6 on not-found",
             "y": "1 (offset past command code in reply)"})

# ============================================================
# Build and send FS command (&836A)
# ============================================================
subroutine(0x836A, "build_send_fs_cmd",
    title="Build and send FS command (DOFSOP)",
    description="""\
Sets reply port to &90 (PREPLY) at &0F00, initialises the TX
control block, then adjusts TXCB's high pointer (HPTR) to X+5
-- the 5-byte FS header (reply port, function code, URD, CSD,
LIB) plus the command data -- so only meaningful bytes are
transmitted, conserving Econet bandwidth. If carry is set on
entry (DOFSBX byte-stream path), takes the alternate path
through econet_tx_retry for direct BSXMIT transmission.
Otherwise sets up the TX pointer via setup_tx_ptr_c0 and falls
through to send_fs_reply_cmd for reply handling. The carry flag
is the sole discriminator between byte-stream and standard FS
protocol paths -- set by SEC at the BPUTV/BGETV entry points.
On return from WAITFS/BSXMIT, Y=0; INY advances past the
command code to read the return code. Error &D6 ("not found",
    on_entry={"x": "buffer extent (command-specific data bytes)", "y": "function code", "c": "0 for standard FS path, 1 for byte-stream (BSXMIT)"},
    on_exit={"a": "0 on success", "x": "0 on success, &D6 on not-found", "y": "1 (offset past command code in reply)"})
is detected via ADC #(&100-&D6) with C=0 -- if the return code
was exactly &D6, the result wraps to zero (Z=1). This is a
branchless comparison returning C=1, A=0 as a soft error that
callers can handle, vs hard errors which go through FSERR.""",
    on_entry={"x": "buffer extent (command-specific data bytes)",
              "y": "function code",
              "a": "timeout period for FS reply",
              "c": "0 for standard FS path, 1 for byte-stream (BSXMIT)"},
    on_exit={"a": "0 on success",
             "x": "0 on success, &D6 on not-found",
             "y": "1 (offset past command code in reply)"})

# ============================================================
# FS error handler (&8402)
# ============================================================
subroutine(0x8402, "store_fs_error", hook=None,
    title="Handle fileserver error replies (FSERR)",
    description="""\
The fileserver returns errors as: zero command code + error number +
CR-terminated message string. This routine converts the reply buffer
in-place to a standard MOS BRK error packet by:
  1. Storing the error code at fs_last_error (&0E09)
  2. Normalizing error codes below &A8 to &A8 (the standard FS error
     number), since the MOS error space below &A8 has other meanings
  3. Scanning for the CR terminator and replacing it with &00
  4. JMPing indirect through (l00c4) to execute the buffer as a BRK
     instruction — the zero command code serves as the BRK opcode
N.B. This relies on the fileserver always returning a zero command
code in position 0 of the reply buffer.""")

# ============================================================
# Handle BPUT/BGET (&83A3)
# ============================================================
subroutine(0x83A3, "handle_bput_bget",
    title="Handle BPUT/BGET file byte I/O",
    description="""\
BPUTV enters at &83A2 (CLC; fall through) and BGETV enters
at &8485 (SEC; JSR here). The carry flag is preserved via
PHP/PLP through the call chain and tested later (BCS) to
select byte-stream transmission (BSXMIT) vs normal FS
transmission (FSXMIT) -- a control-flow encoding using
processor flags to avoid an extra flag variable.

BSXMIT uses handle=0 for print stream transactions (which
sidestep the SEQNOS sequence number manipulation) and non-zero
handles for file operations. After transmission, the high
pointer bytes of the CB are reset to &FF -- "The BGET/PUT byte
fix" which prevents stale buffer pointers corrupting subsequent
byte-level operations.""",
    on_entry={"c": "0 for BPUT (write byte), 1 for BGET (read byte)",
              "a": "byte to write (BPUT only)",
              "y": "file handle"},
    on_exit={"a": "preserved",
             "x": "preserved",
             "y": "preserved"})

# ============================================================
# Send command to fileserver (&844A)
# ============================================================
subroutine(0x844A, "send_to_fs", hook=None,
    title="Send command to fileserver and handle reply (WAITFS)",
    description="""\
Performs a complete FS transaction: transmit then wait for reply.
Sets bit 7 of rx_status_flags (mark FS transaction in progress),
builds a TX frame from the data at (net_tx_ptr), and transmits
it. The system RX flag (LFLAG bit 7) is only set when receiving
into the page-zero control block — if RXCBP's high byte is
non-zero, setting the system flag would interfere with other RX
operations. The timeout counter uses the stack (indexed via TSX)
rather than memory to avoid bus conflicts with Econet hardware
during the tight polling loop. Handles multi-block replies and
checks for escape conditions between blocks.""")

# ============================================================
# Check escape (&847A)
# ============================================================
subroutine(0x847A, "check_escape", hook=None,
    title="Check and handle escape condition (ESC)",
    description="""\
Two-level escape gating: the MOS escape flag (&FF bit 7) is ANDed
with the software enable flag ESCAP. Both must have bit 7 set for
escape to fire. ESCAP is set non-zero during data port operations
(LOADOP stores the data port &90, serving double duty as both the
port number and the escape-enable flag). ESCAP is disabled via LSR
in the ENTER routine, which clears bit 7 — PHP/PLP around the LSR
preserves the carry flag since ENTER is called from contexts where
carry has semantic meaning (e.g., PUTBYT vs BGET distinction).
This architecture allows escape between retransmission attempts
but prevents interruption during critical FS transactions. If
escape fires: acknowledges via OSBYTE &7E, then checks whether
the failing handle is the current SPOOL or EXEC handle (OSBYTE
&C6/&C7); if so, issues "*SP." or "*E." via OSCLI to gracefully
close the channel before raising the error — preventing the system
from continuing to spool output to a broken file handle.""")

# ============================================================
# Error message table (&84AF)
# ============================================================
# N.B. This is data, not code — we use label() not subroutine()
# to avoid entry() tracing from &84AF, where the &A0 error code
# byte would be misinterpreted as LDY #imm.
label(0x84AF, "error_msg_table")
comment(0x84AF, """\
Econet error message table (ERRTAB, 8 entries).
Each entry: error number byte followed by NUL-terminated string.
  &A0: "Line Jammed"     &A1: "Net Error"
  &A2: "Not listening"   &A3: "No Clock"
  &A4: "Bad Txcb"        &11: "Escape"
  &CB: "Bad Option"      &A5: "No reply"
Indexed by the low 3 bits of the TXCB flag byte (AND #&07),
which encode the specific Econet failure reason. The NREPLY
and NLISTN routines build a MOS BRK error block at &100 on the
stack page: NREPLY fires when the fileserver does not respond
within the timeout period; NLISTN fires when the destination
station actively refused the connection.
Indexed via the error dispatch at c8424/c842c.""")

# Mark each error table entry as data: error code byte + NUL-terminated string.
# Without this, the first entry's &A0 byte is traced as code (LDY #imm).
addr = 0x84AF
for _ in range(8):
    byte(addr, 1)           # error number byte
    addr = stringz(addr + 1)  # NUL-terminated message string

# ============================================================
# Resume after remote operation (&8146)
# ============================================================
subroutine(0x8146, "resume_after_remote", hook=None,
    title="Resume after remote operation / *ROFF handler (NROFF)",
    description="""\
Checks byte 4 of (net_rx_ptr): if non-zero, the keyboard was
disabled during a remote operation (peek/poke/boot). Clears
the flag, re-enables the keyboard via OSBYTE &C9, and sends
function &0A to notify completion. Also handles *ROFF and the
triple-plus escape sequence (+++), which resets system masks
via OSBYTE &CE and returns control to the MOS, providing an
escape route when a remote session becomes unresponsive.""")

# ============================================================
# FSCV handler (&808C)
# ============================================================
subroutine(0x808C, "fscv_handler",
    title="FSCV dispatch entry",
    description="""\
Entered via the extended vector table when the MOS calls FSCV.
Stores A/X/Y via save_fscv_args, compares A (function code) against 8,
and dispatches codes 0-7 via the shared dispatch table at &8020
with base offset Y=&12 (table indices 19-26).
Function codes: 0=*OPT, 1=EOF, 2=*/, 3=unrecognised *,
4=*RUN, 5=*CAT, 6=shutdown, 7=read handles.""",
    on_entry={"a": "function code (0-7)",
              "x": "depends on function",
              "y": "depends on function"},
    on_exit={"a": "depends on handler (preserved if A >= 8)",
             "x": "depends on handler (preserved if A >= 8)",
             "y": "depends on handler (preserved if A >= 8)"})

comment(0x808C, "Store A/X/Y in FS workspace", inline=True)
comment(0x808F, "Function code >= 8? Return (unsupported)", inline=True)
comment(0x8095, "Y=&12: base offset for FSCV dispatch (indices 19+)", inline=True)

# ============================================================
# FILEV handler (&8694)
# ============================================================
subroutine(0x8694, "filev_handler",
    title="FILEV handler (OSFILE entry point)",
    description="""\
Saves A/X/Y, copies the filename pointer from the parameter block
to os_text_ptr, then uses GSINIT/GSREAD to parse the filename into
&0FC5+. Sets fs_crc_lo/hi to point at the parsed filename buffer.
Dispatches by function code A:
  A=&FF: load file (send_fs_examine at &86D0)
  A=&00: save file (filev_save at &8746)
  A=&01-&06: attribute operations (filev_attrib_dispatch at &8844)
  Other: restore_args_return (unsupported, no-op)""",
    on_entry={"a": "function code (&FF=load, &00=save, &01-&06=attrs)",
              "x": "parameter block address low byte",
              "y": "parameter block address high byte"},
    on_exit={"a": "restored",
             "x": "restored",
             "y": "restored"})

subroutine(0x86D0, "send_fs_examine", hook=None,
    title="Send FS examine command",
    description="""\
Sends FS command &03 (FCEXAM: examine file) to the fileserver.
Sets &0F02=&03 and error pointer to '*'. Called for OSFILE &FF
(load file) with the filename already in the command buffer.
The FS reply contains load/exec addresses and file length which
are used to set up the data transfer. The header URD field
is repurposed to carry the Econet data port number (PLDATA=&92)
for the subsequent block data transfer.""",
    on_entry={"y": "FS function code (2=load, 5=examine)", "x": "TX buffer extent"})

subroutine(0x8716, "send_data_blocks", hook=None,
    title="Send file data in multi-block chunks",
    description="""\
Repeatedly sends &80-byte (128-byte) blocks of file data to the
fileserver using command &7F. Compares current address (&C8-&CB)
against end address (&B4-&B7) via compare_addresses, and loops
until the entire file has been transferred. Each block is sent
via send_to_fs_star.""")

subroutine(0x8746, "filev_save", hook=None,
    title="OSFILE save handler (A=&00)",
    description="""\
Copies 4-byte load/exec/length addresses from the parameter block
to the FS command buffer, along with the filename. Sends FS
command &91 with function &14 to initiate the save, then
calls print_file_info to display the filename being saved.
Handles both host and Tube-based data sources.
When receiving the save acknowledgement, the RX low pointer is
incremented by 1 to skip the command code (CC) byte, which
indicates the FS type and must be preserved. N.B. this assumes
the RX buffer does not cross a page boundary.""")

subroutine(0x87AD, "copy_load_addr_from_params", hook=None,
    title="Copy load address from parameter block",
    description="""\
Copies 4 bytes from (fs_options)+2..5 (the load address in the
OSFILE parameter block) to &AE-&B3 (local workspace).""")

subroutine(0x87BA, "copy_reply_to_params", hook=None,
    title="Copy FS reply data to parameter block",
    description="""\
Copies bytes from the FS command reply buffer (&0F02+) into the
parameter block at (fs_options)+2..13. Used to fill in the OSFILE
parameter block with information returned by the fileserver.""",
    on_entry={"x": "attribute byte (stored first at offset &0D)"})

subroutine(0x87C8, "transfer_file_blocks", hook=None,
    title="Multi-block file data transfer",
    description="""\
Manages the transfer of file data in chunks between the local
machine and the fileserver. Entry conditions: WORK (&B0-&B3) and
WORK+4 (&B4-&B7) hold the low and high addresses of the data
being sent/received. Sets up source (&C4-&C7) and destination
(&C8-&CB) from the FS reply, sends &80-byte (128-byte) blocks
with command &91, and continues until all data has been
transferred. Handles address overflow and Tube co-processor
transfers. For SAVE, WORK+8 holds the port on which to receive
byte-level ACKs for each data block (flow control).""")

subroutine(0x881F, "fscv_1_eof", hook=None,
    title="FSCV 1: EOF handler",
    description="""\
Checks whether a file handle has reached end-of-file. Converts
the handle via handle_to_mask_clc, tests the result against the
EOF hint byte (&0E07). If the hint bit is clear, returns X=0
immediately (definitely not at EOF — no network call needed).
If the hint bit is set, sends FS command &11 (FCEOF) to query
the fileserver for definitive EOF status. Returns X=&FF if at
EOF, X=&00 if not. This two-level check avoids an expensive
network round-trip when the file is known to not be at EOF.""",
    on_entry={"x": "file handle to check"},
    on_exit={"x": "&FF if at EOF, &00 if not"})

subroutine(0x8844, "filev_attrib_dispatch", hook=None,
    title="FILEV attribute dispatch (A=1-6)",
    description="""\
Dispatches OSFILE operations by function code:
  A=1: write catalogue info (load/exec/length/attrs) — FS &14
  A=2: write load address only
  A=3: write exec address only
  A=4: write file attributes
  A=5: read catalogue info, returns type in A — FS &12
  A=6: delete named object — FS &14 (FCDEL)
  A>=7: falls through to restore_args_return (no-op)
Each handler builds the appropriate FS command, sends it to
the fileserver, and copies the reply into the parameter block.
The control block layout uses dual-purpose fields: the 'data
start' field doubles as 'length' and 'data end' doubles as
'protection' depending on whether reading or writing attrs.""",
    on_entry={"a": "function code (1-6)"},
    on_exit={"a": "object type (A=5 read info) or restored"})

subroutine(0x892C, "restore_args_return", hook=None,
    title="Restore arguments and return",
    description="""\
Common exit point for FS vector handlers. Reloads A from
fs_last_byte_flag (&BD), X from fs_options (&BB), and Y from
fs_block_offset (&BC) — the values saved at entry by
save_fscv_args — and returns to the caller.""")

subroutine(0x89A1, "fscv_0_opt", hook=None,
    title="FSCV 0: *OPT handler (OPTION)",
    description="""\
Handles *OPT X,Y to set filing system options:
  *OPT 1,Y (Y=0/1): set local user option in &0E06 (OPT)
  *OPT 4,Y (Y=0-3): set boot option via FS command &16 (FCOPT)
Other combinations generate error &CB (OPTER: "bad option").""",
    on_entry={"x": "option number (1 or 4)", "y": "option value"})

subroutine(0x89D2, "adjust_addrs", hook=None,
    title="Bidirectional 4-byte address adjustment",
    description="""\
Adjusts a 4-byte value in the parameter block at (fs_options)+Y:
  If fs_load_addr_2 (&B2) is positive: adds fs_lib_handle+X values
  If fs_load_addr_2 (&B2) is negative: subtracts fs_lib_handle+X
Starting offset X=&FC means it reads from &0E06-&0E09 area.
Used to convert between absolute and relative file positions.""",
    on_entry={"y": "starting offset into (fs_options) parameter block"},
    on_exit={"a": "corrupted (last adjusted byte)", "x": "0", "y": "entry Y + 4"})
comment(0x89D2, "X=&FC: index into &0E06 area (wraps to 0)", inline=True)
comment(0x89D4, "Load byte from param block", inline=True)
comment(0x89D6, "Test sign of adjustment direction", inline=True)
comment(0x89D8, "Negative: subtract instead", inline=True)
comment(0x89DA, "Add adjustment value", inline=True)
comment(0x89DD, "Skip to store result", inline=True)
comment(0x89E0, "Subtract adjustment value", inline=True)
comment(0x89E3, "Store adjusted byte back", inline=True)
comment(0x89E5, "Next param block byte", inline=True)
comment(0x89E6, "Next adjustment byte (X wraps &FC->&00)", inline=True)
comment(0x89E7, "Loop 4 times (X=&FC,&FD,&FE,&FF,done)", inline=True)

# ============================================================
# ARGSV handler (&88E1)
# ============================================================
subroutine(0x88E1, "argsv_handler",
    title="ARGSV handler (OSARGS entry point)",
    description="""\
  A=0, Y=0: return filing system number (10 = network FS)
  A=0, Y>0: read file pointer via FS command &0A (FCRDSE)
  A=1, Y>0: write file pointer via FS command &14 (FCWRSE)
  A>=3 (ensure): silently returns -- NFS has no local write buffer
     to flush, since all data is sent to the fileserver immediately
The handle in Y is converted via handle_to_mask_clc. For writes
(A=1), the carry flag from the mask conversion is used to branch
to save_args_handle, which records the handle for later use.""",
    on_entry={"a": "function code (0=query, 1=write ptr, >=3=ensure)",
              "y": "file handle (0=FS-level query, >0=per-file)"},
    on_exit={"a": "filing system number if A=0/Y=0 query, else restored",
             "x": "restored",
             "y": "restored"})

# ============================================================
# FINDV handler (&8949)
# ============================================================
subroutine(0x8949, "findv_handler",
    title="FINDV handler (OSFIND entry point)",
    description="""\
  A=0: close file -- delegates to close_handle (&8985)
  A>0: open file -- modes &40=read, &80=write/update, &C0=read/write
For open: the mode byte is converted to the fileserver's two-flag
format by flipping bit 7 (EOR #&80) and shifting. This produces
Flag 1 (read/write direction) and Flag 2 (create/existing),
matching the fileserver protocol. After a successful open, the
new handle's bit is OR'd into the EOF hint byte (marks it as
"might be at EOF, query the server",
    on_entry={"a": "operation (0=close, &40=read, &80=write, &C0=R/W)", "x": "filename pointer low (open)", "y": "file handle (close) or filename pointer high (open)"},
    on_exit={"a": "handle on open, 0 on close-all, restored on close-one", "x": "restored", "y": "restored"})
number tracking byte for the byte-stream protocol.""",
    on_entry={"a": "operation (0=close, &40=read, &80=write, &C0=R/W)",
              "x": "filename pointer low (open)",
              "y": "file handle (close) or filename pointer high (open)"},
    on_exit={"a": "handle on open, 0 on close-all, restored on close-one",
             "x": "restored",
             "y": "restored"})

# ============================================================
# CLOSE handler (&8985)
# ============================================================
subroutine(0x8985, "close_handle", hook=None,
    title="Close file handle(s) (CLOSE)",
    description="""\
  Y=0: close all files — first calls OSBYTE &77 (close SPOOL and
       EXEC files) to coordinate with the MOS before sending the
       close-all command to the fileserver. This ensures locally-
       managed file handles are released before the server-side
       handles are invalidated, preventing the MOS from writing to
       a closed spool file.
  Y>0: close single handle — sends FS close command and clears
       the handle's bit in both the EOF hint byte and the sequence
       number tracking byte.""",
    on_entry={"y": "file handle (0=close all, >0=close single)"})

# ============================================================
# GBPBV handler (&89EA)
# ============================================================
subroutine(0x89EA, "gbpbv_handler",
    title="GBPBV handler (OSGBPB entry point)",
    description="""\
  A=1-4: file read/write operations (handle-based)
  A=5-8: info queries (disc title, current dir, lib, filenames)
Calls 1-4 are standard file data transfers via the fileserver.
Calls 5-8 were a late addition to the MOS spec and are the only
NFS operations requiring Tube data transfer -- described in the
original source as "untidy but useful in theory." The data format
uses length-prefixed strings (<name length><object name>) rather
than the CR-terminated strings used elsewhere in the FS.""",
    on_entry={"a": "call number (1-8)",
              "x": "parameter block address low byte",
              "y": "parameter block address high byte"},
    on_exit={"a": "0 after FS operation, else restored",
             "x": "restored",
             "y": "restored"})

# ============================================================
# OSGBPB info handler (&8AAD)
# ============================================================
subroutine(0x8AAD, "osgbpb_info", hook=None,
    title="OSGBPB 5-8 info handler (OSINFO)",
    description="""\
Handles the "messy interface tacked onto OSGBPB" (original source).
Checks whether the destination address is in Tube space by comparing
the high bytes against TBFLAG. If in Tube space, data must be
copied via the Tube FIFO registers (with delays to accommodate the
slow 16032 co-processor) instead of direct memory access.""")

# ============================================================
# Forward unrecognised * command to fileserver (&8079)
# ============================================================
subroutine(0x8079, "forward_star_cmd", hook=None,
    title="Forward unrecognised * command to fileserver (COMERR)",
    description="""\
Copies command text from (fs_crc_lo) to &0F05+ via copy_filename,
prepares an FS command with function code 0, and sends it to the
fileserver to request decoding. The server returns a command code
indicating what action to take (e.g. code 4=INFO, 7=DIR, 9=LIB,
5=load-as-command). This mechanism allows the fileserver to extend
the client's command set without ROM updates. Called from the "I."
and catch-all entries in the command match table at &8BD6, and
from FSCV 2/3/4 indirectly. If CSD handle is zero (not logged
in), returns without sending.""")

# ============================================================
# *BYE handler (&8349)
# ============================================================
subroutine(0x8349, "bye_handler", hook=None,
    title="*BYE handler (logoff)",
    description="""\
Closes any open *SPOOL and *EXEC files via OSBYTE &77 (FXSPEX),
then falls into prepare_fs_cmd with Y=&17 (FCBYE: logoff code).
Dispatched from the command match table at &8BD6 for "BYE".""")

# ============================================================
# FSCV unrecognised * handler (&8B92)
# ============================================================
subroutine(0x8B92, "fscv_3_star_cmd", hook=None,
    title="FSCV 2/3/4: unrecognised * command handler (DECODE)",
    description="""\
CLI parser originally by Sophie Wilson (co-designer of ARM). Matches command text against the table
at &8BD6 using case-insensitive comparison with abbreviation
support — commands can be shortened with '.' (e.g. "I." for
"INFO"). The "I." entry is a special fudge placed first in the
table: since "I." could match multiple commands, it jumps to
forward_star_cmd to let the fileserver resolve the ambiguity.

The matching loop compares input characters against table
entries. On mismatch, it skips to the next entry. On match
of all table characters, or when '.' abbreviation is found,
it dispatches via PHA/PHA/RTS to the entry's handler address.

After matching, adjusts fs_crc_lo/fs_crc_hi to point past
the matched command text.""")

subroutine(0x8BD6, "fs_cmd_match_table", hook=None,
    title="FS command match table (COMTAB)",
    description="""\
Format: command letters (bit 7 clear), then dispatch address
as two bytes: high|(bit 7 set), low. The PHA/PHA/RTS trick
adds 1 to the stored (address-1). Matching is case-insensitive
(AND &DF) and supports '.' abbreviation (standard Acorn pattern).

Entries:
  "I."     → &8079 (forward_star_cmd) — placed first as a fudge
             to catch *I. abbreviation before matching *I AM
  "I AM"   → &8D06 (i_am_handler: parse station.net, logon)
  "EX "    → &8BF2 (ex_handler: extended catalogue)
  "EX"\\r   → &8BF2 (same, exact match at end of line)
  "BYE"\\r  → &8349 (bye_handler: logoff)
  <catch-all> → &8079 (forward anything else to FS)""")

# ============================================================
# *EX and *CAT handlers (&8BF2 / &8BFD)
# ============================================================
subroutine(0x8BF2, "ex_handler", hook=None,
    title="*EX handler (extended catalogue)",
    description="""\
Sets column width &B6=&50 (80 columns, one file per line with
full details) and &B7=&01, then branches into fscv_5_cat at
&8C07, bypassing fscv_5_cat's default 20-column setup.""")

subroutine(0x8BFD, "fscv_5_cat", hook=None,
    title="*CAT handler (directory catalogue)",
    description="""\
Sets column width &B6=&14 (20 columns, four files per 80-column
line) and &B7=&03. The catalogue protocol is multi-step: first
sends FCUSER (&15: read user environment) to get CSD, disc, and
library names, then sends FCREAD (&12: examine) repeatedly to
fetch entries in batches until zero are returned (end of dir).
The receive buffer abuts the examine request buffer and ends at
RXBUFE, allowing seamless data handling across request cycles.

The command code byte in the fileserver reply indicates FS type:
zero means an old-format FS (client must format data locally),
non-zero means new-format (server returns pre-formatted strings).
This enables backward compatibility with older Acorn fileservers.

Display format:
  - Station number in parentheses
  - "Owner" or "Public" access level
  - Boot option with name (Off/Load/Run/Exec)
  - Current directory and library paths
  - Directory entries: CRFLAG (&CF) cycles 0-3 for multi-column
    layout; at count 0 a newline is printed, others get spaces.
    *EX sets CRFLAG=&FF to force one entry per line.""")

# ============================================================
# Boot command strings (&8CEA)
# ============================================================
subroutine(0x8CEA, "boot_cmd_strings", hook=None,
    title="Boot command strings for auto-boot",
    description="""\
The four boot options use OSCLI strings at offsets within page &8C:
  Option 0 (Off):  offset &F6 → &8CF6 = bare CR (empty command)
  Option 1 (Load): offset &E7 → &8CE7 = "L.!BOOT" (dual-purpose:
      the JMP &212E instruction at &8CE7 has opcode &4C='L' and
      operand bytes &2E='.' &21='!', forming the string "L.!")
  Option 2 (Run):  offset &E9 → boot_cmd_strings-1 = "!BOOT" (*RUN)
  Option 3 (Exec): offset &EF → &8CEF = "E.!BOOT"

This is a classic BBC ROM space optimisation: the JMP instruction's
bytes serve double duty as both executable code and ASCII text.""")

# ============================================================
# Handle workspace management (&8CF7-&8CFF)
# ============================================================
subroutine(0x8CF7, "fsreply_5_set_lib", hook=None,
    title="Set library handle",
    description="""\
Stores Y into &0E04 (library directory handle in FS workspace).
Falls through to set_handle_return (JMP restore_args_return) if Y is non-zero.""",
    on_entry={"y": "library handle from FS reply"})

subroutine(0x8CFC, "fsreply_3_set_csd", hook=None,
    title="Set CSD handle",
    description="""\
Stores Y into &0E03 (current selected directory handle).
Falls through to set_handle_return (JMP restore_args_return).""",
    on_entry={"y": "CSD handle from FS reply"})

# ============================================================
# Boot option table and "I AM" handler (&8D02-&8D1E)
# ============================================================
subroutine(0x8D02, "boot_option_offsets", hook=None,
    title="Boot option → OSCLI string offset table",
    description="""\
Four bytes indexed by the boot option value (0-3). Each byte
is the low byte of a pointer into page &8C, where the OSCLI
command string for that boot option lives. See boot_cmd_strings.""")
byte(0x8D02, 1)
comment(0x8D02, "Opt 0 (Off): bare CR", inline=True)
byte(0x8D03, 1)
comment(0x8D03, "Opt 1 (Load): L.!BOOT", inline=True)
byte(0x8D04, 1)
comment(0x8D04, "Opt 2 (Run): !BOOT", inline=True)
byte(0x8D05, 1)
comment(0x8D05, "Opt 3 (Exec): E.!BOOT", inline=True)

subroutine(0x8D06, "i_am_handler", hook=None,
    title="\"I AM\" command handler",
    description="""\
Dispatched from the command match table when the user types
"*I AM <station>" or "*I AM <network>.<station>".
Skips leading spaces via skip_spaces, then calls parse_decimal
twice if a dot separator is present. The first number becomes the
network (&0E01, via TAX pass-through in parse_decimal) and the
second becomes the station (&0E00). With a single number, it is
stored as the station and the network defaults to 0 (local).
Then forwards the command to the fileserver via forward_star_cmd.""")

# ============================================================
# Copy handles and boot (&8D1F / &8D20)
# ============================================================
subroutine(0x8D1F, "fsreply_1_copy_handles_boot", hook=None,
    title="Copy FS reply handles to workspace and execute boot command",
    description="""\
SEC entry (LOGIN): copies 4 bytes from &0F05-&0F08 (FS reply) to
&0E02-&0E05 (URD, CSD, LIB handles and boot option), then
looks up the boot option in boot_option_offsets to get the
OSCLI command string and executes it via JMP oscli.
The carry flag distinguishes LOGIN (SEC) from SDISC (CLC) — both
share the handle-copying code, but only LOGIN executes the boot
command. This use of the carry flag to select behaviour between
two callers avoids duplicating the handle-copy loop.""")

subroutine(0x8D20, "fsreply_2_copy_handles", hook=None,
    title="Copy FS reply handles to workspace (no boot)",
    description="""\
CLC entry (SDISC): copies handles only, then jumps to set_handle_return.
Called when the FS reply contains updated handle values
but no boot action is needed.""")

# ============================================================
# Option name display (&8D3A-&8D4E)
# ============================================================
subroutine(0x8D3A, "option_name_strings", hook=None,
    title="Option name strings",
    description="""\
Null-terminated strings for the four boot option names:
  "Off", "Load", "Run", "Exec"
Used by fscv_5_cat to display the current boot option setting.""")

subroutine(0x8D4B, "option_name_offsets", hook=None,
    title="Option name offsets",
    description="""\
Four-byte table of offsets into option_name_strings:
  0, 4, 9, &0D — one per boot option value (0-3).""")

# ============================================================
# Reply buffer display helpers (&8D4F-&8D72)
# ============================================================
subroutine(0x8D4F, "print_reply_bytes", hook=None,
    title="Print reply buffer bytes",
    description="""\
Prints Y characters from the FS reply buffer (&0F05+X) to
the screen via OSASCI. X = starting offset, Y = count.
Used by fscv_5_cat to display directory and library names.""")

subroutine(0x8D5C, "print_spaces", hook=None,
    title="Print spaces",
    description="""\
Prints X space characters via print_space. Used by fscv_5_cat
to align columns in the directory listing.""")

# ============================================================
# Filename copy helpers (&8D63-&8D72)
# ============================================================
subroutine(0x8D63, "copy_filename", hook=None,
    title="Copy filename to FS command buffer",
    description="""\
Entry with X=0: copies from (fs_crc_lo),Y to &0F05+X until CR.
Used to place a filename into the FS command buffer before
sending to the fileserver. Falls through to copy_string_to_cmd.""")

subroutine(0x8D65, "copy_string_to_cmd", hook=None,
    title="Copy string to FS command buffer",
    description="""\
Entry with X and Y specified: copies bytes from (fs_crc_lo),Y
to &0F05+X, stopping when a CR (&0D) is encountered. The CR
itself is also copied. Returns with X pointing past the last
byte written.""",
    on_entry={"x": "destination offset in fs_cmd_data (&0F05+X)"},
    on_exit={"x": "next free position past CR", "y": "string length (incl CR)", "a": "0 (from EOR &0D with final CR)"})
comment(0x8D65, "Start copying from offset 0", inline=True)
comment(0x8D67, "Load next byte from source string", inline=True)
comment(0x8D69, "Store to command buffer", inline=True)
comment(0x8D6C, "Advance write position", inline=True)
comment(0x8D6D, "Advance read position", inline=True)
comment(0x8D6E, "XOR with CR: result=0 if byte was CR", inline=True)
comment(0x8D70, "Loop until CR copied", inline=True)

# ============================================================
# Print directory name (&8D73)
# ============================================================
subroutine(0x8D73, "fsreply_0_print_dir", hook=None,
    title="Print directory name from reply buffer",
    description="""\
Prints characters from the FS reply buffer (&0F05+X onwards).
Null bytes (&00) are replaced with CR (&0D) for display.
Stops when a byte with bit 7 set is encountered (high-bit
terminator). Used by fscv_5_cat to display Dir. and Lib. paths.""")

# ============================================================
# Notify and execute (&8D84)
# ============================================================
subroutine(0x8D84, "fsreply_4_notify_exec", hook=None,
    title="Send FS load-as-command and execute response",
    description="""\
Sets up an FS command with function code &05 (FCCMND: load as
command) using send_fs_examine. If a Tube co-processor is
present (tx_in_progress != 0), transfers the response data
to the Tube via tube_addr_claim. Otherwise jumps via the
indirect pointer at (&0F09) to execute at the load address.""")

# ============================================================
# *NET sub-command handlers (&8DAF-&8DF5)
# ============================================================
subroutine(0x8DAF, "net_1_read_handle", hook=None,
    title="*NET1: read file handle from received packet",
    description="""\
Reads a file handle byte from offset &6F in the RX buffer
(net_rx_ptr), stores it in &F0, then falls through to the
common handle workspace cleanup at clear_svc_return.""")

subroutine(0x8DB7, "calc_handle_offset", hook=None,
    title="Calculate handle workspace offset",
    description="""\
Converts a file handle number (in A) to a byte offset (in Y)
into the NFS handle workspace. The calculation is A*12:
  ASL A (A*2), ASL A (A*4), PHA, ASL A (A*8),
  ADC stack (A*8 + A*4 = A*12).
Validates that the offset is < &48 (max 6 handles × 12 bytes
per handle entry = 72 bytes). If invalid (>= &48), returns
with C set and Y=0, A=0 as an error indicator.""",
    on_entry={"a": "file handle number"},
    on_exit={"a": "handle*12 or 0 if invalid", "y": "workspace offset or 0 if invalid", "c": "clear if valid, set if invalid"})
comment(0x8DB7, "A = handle * 2", inline=True)
comment(0x8DB8, "A = handle * 4", inline=True)
comment(0x8DB9, "Push handle*4 onto stack", inline=True)
comment(0x8DBA, "A = handle * 8", inline=True)
comment(0x8DBB, "X = stack pointer", inline=True)
comment(0x8DBC, "A = handle*8 + handle*4 = handle*12", inline=True)
comment(0x8DBF, "Y = offset into handle workspace", inline=True)
comment(0x8DC0, "Clean stack (discard handle*4)", inline=True)
comment(0x8DC1, "Offset >= &48 (6 handles max)?", inline=True)
comment(0x8DC3, "No: valid handle, return with C=0", inline=True)
comment(0x8DC5, "Y=0: invalid handle error sentinel", inline=True)

label(0x8DC8, "return_calc_handle")      # Return from calc_handle_offset (invalid)

subroutine(0x8DC9, "net_2_read_handle_entry", hook=None,
    title="*NET2: read handle entry from workspace",
    description="""\
Looks up the handle in &F0 via calc_handle_offset. If the
workspace slot contains &3F ('?', meaning unused/closed),
returns 0. Otherwise returns the stored handle value.
Clears rom_svc_num on exit.""")

subroutine(0x8DDF, "net_3_close_handle", hook=None,
    title="*NET3: close handle (mark as unused)",
    description="""\
Looks up the handle in &F0 via calc_handle_offset. Writes
&3F ('?') to mark the handle slot as closed in the NFS
workspace. Preserves the carry flag state across the write
using ROL/ROR on rx_status_flags. Clears rom_svc_num on exit.""")

subroutine(0x8DF2, "net_4_resume_remote", hook=None,
    title="*NET4: resume after remote operation",
    description="""\
Calls resume_after_remote (&8146) to re-enable the keyboard
and send a completion notification. The BVC always branches
to clear_svc_return since resume_after_remote
returns with V clear (from CLV in prepare_cmd_clv).""")

# NMI handler init — ROM code copies to page &04/&05/&06
# ============================================================
# Filing system OSWORD dispatch (&8DF7 / &8E01)
# ============================================================
subroutine(0x8DF7, "svc_8_osword", hook=None,
    title="Filing system OSWORD entry",
    description="""\
Subtracts &0F from the command code in &EF, giving a 0-4 index
for OSWORD calls &0F-&13 (15-19). Falls through to the
PHA/PHA/RTS dispatch at &8E01.""")

comment(0x8DF7, "Command code from &EF", inline=True)
comment(0x8DF9, "Subtract &0F: OSWORD &0F-&13 become indices 0-4", inline=True)

subroutine(0x8E01, "fs_osword_dispatch", hook=None,
    title="PHA/PHA/RTS dispatch for filing system OSWORDs",
    description="""\
X = OSWORD number - &0F (0-4). Dispatches via the 5-entry table
at &8E18 (low) / &8E1D (high).""")

comment(0x8E18, "Dispatch table: low bytes for OSWORD &0F-&13 handlers", inline=True)
comment(0x8E1D, "Dispatch table: high bytes for OSWORD &0F-&13 handlers", inline=True)

comment(0x80F9, "Copy NMI handler code from ROM to RAM pages &04-&06")
comment(0x8113, "Copy NMI workspace initialiser from ROM to &0016-&0076")

# ============================================================
# Econet TX/RX handler (&8F72)
# ============================================================
subroutine(0x8F72, "econet_tx_rx", hook=None,
    title="Econet transmit/receive handler",
    description="""\
A=0: Initialise TX control block from ROM template at &8310
     (zero entries substituted from NMI workspace &0DDA), transmit
     it, set up RX control block, and receive reply.
A>=1: Handle transmit result (branch to cleanup at &8F48).""",
    on_entry={"a": "0=set up and transmit, >=1=handle TX result"})

comment(0x8F72, "A=0: set up and transmit; A>=1: handle result", inline=True)
comment(0x8F78, "Load from ROM template (zero = use NMI workspace value)", inline=True)
comment(0x8FA3, "Enable interrupts before transmit", inline=True)
comment(0x8FBB, "Initiate receive with timeout", inline=True)
comment(0x8FBE, "Non-zero = error/timeout: jump to cleanup", inline=True)

# Data transfer loop (&8FD7-&8FF3)
comment(0x8FEF, "Test for end-of-data marker (&0D)", inline=True)

# ============================================================
# OSWORD-style function dispatch (&9007)
# ============================================================
subroutine(0x9007, "osword_dispatch",
    title="NETVEC dispatch handler (ENTRY)",
    description="""\
Indirected from NETVEC at &0224. Saves all registers and flags,
retrieves the reason code from the stacked A, and dispatches to
one of 9 handlers (codes 0-8) via the PHA/PHA/RTS trampoline at
&9020. Reason codes >= 9 are ignored.

Dispatch targets (from NFS09):
  0:   no-op (RTS)
  1-3: PRINT -- chars in printer buffer / Ctrl-B / Ctrl-C
  4:   NWRCH -- write character to screen (net write char)
  5:   SELECT -- printer selection changed
  6:   no-op (net read char -- not implemented)
  7:   NBYTE -- remote OSBYTE call
  8:   NWORD -- remote OSWORD call""",
    on_entry={"a": "reason code (0-8)"},
    on_exit={"a": "preserved",
             "x": "preserved",
             "y": "preserved"})

comment(0x9020, "PHA/PHA/RTS trampoline: push handler addr-1, RTS jumps to it", inline=True)

# ============================================================
# NWRCH: net write character (&903D)
# ============================================================
subroutine(0x903D, "net_write_char",
    title="Fn 4: net write character (NWRCH)",
    description="""\
Writes a character (passed in Y) to the screen via OSWRITCH.
Before the write, uses TSX to reach into the stack and zero the
carry flag in the caller's saved processor status byte -- ROR
followed by ASL on the stacked P byte (&0106,X) shifts carry
out and back in as zero. This ensures the calling code's PLP
restores carry=0, signalling "character accepted" without needing
a separate CLC/PHP sequence. A classic 6502 trick for modifying
return flags without touching the actual processor status.""",
    on_entry={"y": "character to write"},
    on_exit={"a": "&3F",
             "x": "0",
             "y": "0"})

comment(0x903E, "ROR/ASL on stacked P: zeros carry to signal success", inline=True)

# ============================================================
# Setup TX and send (&904B)
# ============================================================
subroutine(0x904B, "setup_tx_and_send", hook=None,
    title="Set up TX control block and send",
    description="""\
Builds a TX control block at (nfs_workspace)+&0C from the current
workspace state, then initiates transmission via the ADLC TX path.
This is the common send routine used after command data has been
prepared. The exact control block layout and field mapping need
further analysis.""",
    on_entry={"a": "command type byte"})

# ============================================================
# Control block setup routine (&9159 / &9162)
# ============================================================
subroutine(0x9159, "ctrl_block_setup_alt", hook=None,
    title="Alternate entry into control block setup",
    description="""\
Sets X=&0D, Y=&7C. Tests bit 6 of &833A to choose target:
  V=0 (bit 6 clear): stores to (nfs_workspace)
  V=1 (bit 6 set):   stores to (net_rx_ptr)""")

subroutine(0x9162, "ctrl_block_setup", hook=None,
    title="Control block setup — main entry",
    description="""\
Sets X=&1A, Y=&17, clears V (stores to nfs_workspace).
Reads the template table at &918E indexed by X, storing each
value into the target workspace at offset Y. Both X and Y
are decremented on each iteration.

Template sentinel values:
  &FE = stop (end of template for this entry path)
  &FD = skip (leave existing value unchanged)
  &FC = use page high byte of target pointer""")

comment(0x9167, "Load template byte from ctrl_block_template[X]", inline=True)

subroutine(0x918E, "ctrl_block_template", hook=None,
    title="Control block initialisation template",
    description="""\
Read by the loop at &9167, indexed by X from a starting value
down to 0. Values are stored into either (nfs_workspace) or
(net_rx_ptr) at offset Y, depending on the V flag.

Two entry paths read different slices of this table:
  ctrl_block_setup:   X=&1A (26) down, Y=&17 (23) down, V=0
  ctrl_block_setup_alt: X=&0D (13) down, Y=&7C (124) down, V from BIT &833A

Sentinel values:
  &FE = stop processing
  &FD = skip this offset (decrement Y but don't store)
  &FC = substitute the page byte (net_rx_ptr_hi or nfs_workspace_hi)""")
byte(0x918E, 1)
comment(0x918E, "Alt-path only → Y=&6F", inline=True)
byte(0x918F, 1)
comment(0x918F, "Alt-path only → Y=&70", inline=True)
byte(0x9190, 1)
comment(0x9190, "SKIP", inline=True)
byte(0x9191, 1)
comment(0x9191, "SKIP", inline=True)
byte(0x9192, 1)
comment(0x9192, "→ Y=&01 / Y=&73", inline=True)
byte(0x9193, 1)
comment(0x9193, "PAGE byte → Y=&02 / Y=&74", inline=True)
byte(0x9194, 1)
comment(0x9194, "→ Y=&03 / Y=&75", inline=True)
byte(0x9195, 1)
comment(0x9195, "→ Y=&04 / Y=&76", inline=True)
byte(0x9196, 1)
comment(0x9196, "→ Y=&05 / Y=&77", inline=True)
byte(0x9197, 1)
comment(0x9197, "PAGE byte → Y=&06 / Y=&78", inline=True)
byte(0x9198, 1)
comment(0x9198, "→ Y=&07 / Y=&79", inline=True)
byte(0x9199, 1)
comment(0x9199, "→ Y=&08 / Y=&7A", inline=True)
byte(0x919A, 1)
comment(0x919A, "→ Y=&09 / Y=&7B", inline=True)
byte(0x919B, 1)
comment(0x919B, "→ Y=&0A / Y=&7C", inline=True)
byte(0x919C, 1)
comment(0x919C, "STOP — main-path boundary", inline=True)
byte(0x919D, 1)
comment(0x919D, "→ Y=&0C (main only)", inline=True)
byte(0x919E, 1)
comment(0x919E, "→ Y=&0D (main only)", inline=True)
byte(0x919F, 1)
comment(0x919F, "SKIP (main only)", inline=True)
byte(0x91A0, 1)
comment(0x91A0, "SKIP (main only)", inline=True)
byte(0x91A1, 1)
comment(0x91A1, "→ Y=&10 (main only)", inline=True)
byte(0x91A2, 1)
comment(0x91A2, "PAGE byte → Y=&11 (main only)", inline=True)
byte(0x91A3, 1)
comment(0x91A3, "→ Y=&12 (main only)", inline=True)
byte(0x91A4, 1)
comment(0x91A4, "→ Y=&13 (main only)", inline=True)
byte(0x91A5, 1)
comment(0x91A5, "→ Y=&14 (main only)", inline=True)
byte(0x91A6, 1)
comment(0x91A6, "PAGE byte → Y=&15 (main only)", inline=True)
byte(0x91A7, 1)
comment(0x91A7, "→ Y=&16 (main only)", inline=True)
byte(0x91A8, 1)
comment(0x91A8, "→ Y=&17 (main only)", inline=True)

# ============================================================
# Bidirectional block copy (&8E22)
# ============================================================
subroutine(0x8E22, "copy_param_block", hook=None,
    title="Bidirectional block copy between OSWORD param block and workspace.",
    description="""\
C=1: copy X+1 bytes from (&F0),Y to (fs_crc_lo),Y (param to workspace)
C=0: copy X+1 bytes from (fs_crc_lo),Y to (&F0),Y (workspace to param)""")
comment(0x8E22, "C=0: workspace to param direction", inline=True)
comment(0x8E24, "Load byte from param block", inline=True)
comment(0x8E26, "Store to workspace", inline=True)
comment(0x8E28, "Always taken (C still set)", inline=True)
comment(0x8E2A, "Load byte from workspace", inline=True)
comment(0x8E2E, "Advance to next byte", inline=True)
comment(0x8E2F, "Decrement byte counter", inline=True)
comment(0x8E30, "Loop while X >= 0", inline=True)

# ============================================================
# OSWORD handler block comments
# ============================================================
label(0x8E32, "return_copy_param")       # Return from copy_param_block

subroutine(0x8E33, "osword_0f_handler",
    title="OSWORD &0F handler: initiate transmit (CALLTX)",
    description="""\
Checks the TX semaphore (TXCLR at &0D62) via ASL -- if carry is
clear, a TX is already in progress and the call returns an error,
preventing user code from corrupting a system transmit. Otherwise
copies 16 bytes from the caller's OSWORD parameter block into the
user TX control block (UTXCB) in static workspace. The TXCB
pointer is copied to LTXCBP only after the semaphore is claimed,
ensuring the low-level transmit code (BRIANX) sees a consistent
pointer -- if copied before claiming, another transmitter could
modify TXCBP between the copy and the claim.""",
    on_entry={"x": "parameter block address low byte",
              "y": "parameter block address high byte"},
    on_exit={"a": "corrupted",
             "x": "corrupted",
             "y": "&FF"})

subroutine(0x8E53, "osword_11_handler", hook=None,
    title="OSWORD &11 handler: read JSR arguments (READRA)",
    description="""\
Copies the JSR (remote procedure call) argument buffer from the
static workspace page back to the caller's OSWORD parameter block.
Reads the buffer size from workspace offset JSRSIZ, then copies
that many bytes. After the copy, clears the old LSTAT byte via
CLRJSR to reset the protection status. Also provides READRB as
a sub-entry (&8E6A) to return just the buffer size and args size
without copying the data.""")

subroutine(0x8E7B, "osword_12_handler", hook=None,
    title="OSWORD &12 handler: read/set state information (RS)",
    description="""\
Dispatches on the sub-function code (0-9):
  0: read FS station (FSLOCN at &0E00)
  1: set FS station
  2: read printer server station (PSLOCN)
  3: set printer server station
  4: read protection masks (LSTAT at &D63)
  5: set protection masks
  6: read context handles (URD/CSD/LIB, converted from
     internal single-bit form back to handle numbers)
  7: set context handles (converted to internal form)
  8: read local station number
  9: read JSR arguments buffer size
Even-numbered sub-functions read; odd-numbered ones write.
Uses the bidirectional copy at &8E22 for station read/set.""")

subroutine(0x8EF0, "osword_10_handler",
    title="OSWORD &10 handler: open/read RX control block (OPENRX)",
    description="""\
If the first byte of the caller's parameter block is zero, scans
for a free RXCB (flag byte = &3F = deleted) starting from RXCB #3
(RXCBs 0-2 are dedicated: printer, remote, FS). Returns the RXCB
number in the first byte, or zero if none free. If the first byte
is non-zero, reads the specified RXCB's data back into the caller's
parameter block (12 bytes) and then deletes the RXCB by setting
its flag byte to &3F -- a consume-once semantic so user code reads
received data and frees the CB in a single atomic operation,
preventing double-reads. The low-level user RX flag (LFLAG) is
temporarily disabled via ROR/ROL during the operation to prevent
the interrupt-driven receive code from modifying a CB that is
being read or opened.""",
    on_entry={"x": "parameter block address low byte",
              "y": "parameter block address high byte"},
    on_exit={"a": "corrupted",
             "x": "corrupted",
             "y": "&FF"})

# ============================================================
# Remote operation handlers (&90FC / &912A / &913A / &914A)
# ============================================================
subroutine(0x90FC, "lang_1_remote_boot", hook=None,
    title="Remote boot/execute handler",
    description="""\
Validates byte 4 of the RX control block (must be zero), copies the
2-byte execution address from RX offsets &80/&81 into NFS workspace,
sets up a control block, disables keyboard (OSBYTE &C9), then falls
through to lang_3_execute_at_0100.""")

subroutine(0x912A, "lang_3_execute_at_0100", hook=None,
    title="Execute downloaded code at &0100",
    description="""\
Zeroes &0100-&0102 (safe BRK default), restores the protection mask,
and JMP &0100 to execute code received over the network.""")

subroutine(0x913A, "lang_4_remote_validated", hook=None,
    title="Remote operation with source validation (REMOT)",
    description="""\
Validates that the source station/network in the received packet
matches the controlling station stored in the remote RXCB. This
ensures that only the station that initiated the remote session
can send commands — characters from other stations are rejected.
Full init sequence: 1) disable keyboard, 2) set workspace ptr,
3) set status busy, 4) set R/W/byte/word masks, 5) set up CB,
6) set MODE 7 (the only mode guaranteed for terminal emulation),
7) set auto repeat rates, 8) enter current language. This is
essentially a "thin terminal" setup — the local machine becomes
a remote display/keyboard for the controlling station.
Bit 0 of the status byte disallows further remote takeover
attempts (preventing re-entrant remote control), while bit 3
marks the machine as currently remoted.""")

subroutine(0x914A, "lang_0_insert_remote_key", hook=None,
    title="Insert remote keypress",
    description="""\
Reads a character from RX block offset &82 and inserts it into
keyboard input buffer 0 via OSBYTE &99.""")

# ============================================================
# Remote operation support routines (&8F57-&92F0)
# ============================================================
subroutine(0x8F57, "setup_rx_buffer_ptrs", hook=None,
    title="Set up RX buffer pointers in NFS workspace",
    description="""\
Calculates the start address of the RX data area (&F0+1) and stores
it at workspace offset &28. Also reads the data length from (&F0)+1
and adds it to &F0 to compute the end address at offset &2C.""",
    on_entry={"c": "clear for ADC"})

subroutine(0x9063, "remote_cmd_dispatch", hook=None,
    title="Fn 7: remote OSBYTE handler (NBYTE)",
    description="""\
Full RPC mechanism for OSBYTE calls across the network. When a
machine is remoted, OSBYTE/OSWORD calls that affect terminal-side
hardware (keyboard scanning, flash rates, etc.) must be indirected
across the net. OSBYTE calls are classified into three categories:
  Y>0 (NCTBPL table): executed on BOTH machines (flash rates etc.)
  Y<0 (NCTBMI table): executed on terminal only, result sent back
  Y=0: not recognised, passed through unhandled
Results returned via stack manipulation: the saved processor status
byte at &0106 has V-flag (bit 6) forced on to tell the MOS the
call was claimed (preventing dispatch to other ROMs), and the I-bit
(bit 2) forced on to disable interrupts during register restoration,
preventing race conditions. The carry flag in the saved P is also
manipulated via ROR/ASL to zero it, signaling success to the caller.
OSBYTE &81 (INKEY) gets special handling as it must read the
terminal's keyboard.""")

subroutine(0x90B5, "match_osbyte_code", hook=None,
    title="Search remote OSBYTE table for match (NCALLP)",
    description="""\
Searches remote_osbyte_table for OSBYTE code A. X indexes the
last entry to check (table is scanned X..0). Returns Z=1 if
found. Called twice by remote_cmd_dispatch:

  X=7  -> first 8 entries (NCTBPL: execute on both machines)
  X=14 -> all 15 entries (NCTBMI: execute on terminal only)

The last 7 entries (&0B, &0C, &0F, &79, &7A, &E3, &E4) are terminal-only
because they affect the local keyboard, buffers, or function keys.

On entry: A = OSBYTE code, X = table size - 1
On exit:  Z=1 if match found, Z=0 if not""")

subroutine(0x90CD, "remote_cmd_data", hook=None,
    title="Fn 8: remote OSWORD handler (NWORD)",
    description="""\
Only intercepts OSWORD 7 (make a sound) and OSWORD 8 (define an
envelope). Unlike NBYTE which returns results, NWORD is entirely
fire-and-forget — no return path is implemented. The developer
explicitly noted this was acceptable since sound/envelope commands
don't return meaningful results. Copies up to 14 parameter bytes
from the RX buffer to workspace, tags the message as RWORD, and
transmits.""")

subroutine(0x91B5, "printer_select_handler", hook=None,
    title="Fn 5: printer selection changed (SELECT)",
    description="""\
Called when the printer selection changes. Compares the new
selection (in PARMX) against the network printer (buffer 4).
If it matches, initialises the printer buffer pointer (PBUFFP)
and sets the initial flag byte (&41). Otherwise just updates
the printer status flags (PFLAGS).""",
    on_entry={"x": "1-based buffer number"})

subroutine(0x91C7, "remote_print_handler", hook=None,
    title="Fn 1/2/3: network printer handler (PRINT)",
    description="""\
Handles network printer output. Reason 1 = chars in buffer (extract
from MOS buffer 3 and accumulate), reason 2 = Ctrl-B (start print),
reason 3 = Ctrl-C (end print). The printer status byte PFLAGS uses:
  bit 7 = sequence number (toggles per packet for dup detection)
  bit 6 = always 1 (validity marker)
  bit 0 = 0 when print active
Print streams reuse the BSXMIT (byte-stream transmit) code with
handle=0, which causes the AND SEQNOS to produce zero and sidestep
per-file sequence tracking. After transmission, TXCB pointer bytes
are filled with &FF to prevent stale values corrupting subsequent
BGET/BPUT operations (a historically significant bug fix).
N.B. The printer and REMOTE facility share the same dynamically
allocated static workspace page via WORKP1 (&9E,&9F) — care must
be taken to never leave the pointer corrupted, as corruption would
cause one subsystem to overwrite the other's data.
Only handles buffer 4 (network printer); others are ignored.""",
    on_entry={"x": "reason code (1=chars, 2=Ctrl-B, 3=Ctrl-C)", "y": "buffer number (must be 4 for network printer)"})

subroutine(0x91EC, "store_output_byte", hook=None,
    title="Store output byte to network buffer",
    description="""\
Stores byte A at the current output offset in the RX buffer
pointed to by (net_rx_ptr). Advances the offset counter and
triggers a flush if the buffer is full.""",
    on_entry={"a": "byte to store"},
    on_exit={"y": "buffer offset before store"})

subroutine(0x9217, "flush_output_block", hook=None,
    title="Flush output block",
    description="""\
Sends the accumulated output block over the network, resets the
buffer pointer, and prepares for the next block of output data.""")

subroutine(0x92DD, "save_vdu_state", hook=None,
    title="Save VDU workspace state",
    description="""\
Stores the cursor position value from &0355 into NFS workspace,
then reads cursor position (OSBYTE &85), shadow RAM (OSBYTE &C2),
and screen start (OSBYTE &C3) via read_vdu_osbyte, storing
each result into consecutive workspace bytes.""")

# ============================================================
# ADLC initialisation (&966F)
# ============================================================
subroutine(0x966F, "adlc_init", hook=None,
    title="ADLC initialisation",
    description="""\
Reads station ID (INTOFF side effect), performs full ADLC reset,
checks for Tube presence (OSBYTE &EA), then falls through to
adlc_init_workspace.""")

subroutine(0x9681, "adlc_init_workspace", hook=None,
    title="Initialise NMI workspace",
    description="""\
Copies NMI shim from ROM to &0D00, stores current ROM bank number
into shim self-modifying code, sets TX status to &80 (idle/complete),
saves station ID from &FE18 into TX scout buffer, re-enables NMIs
by reading &FE20.""")

subroutine(0x969D, "save_econet_state", hook=None,
    title="Save Econet state to RX control block",
    description="""\
Stores rx_status_flags, protection_mask, and tx_in_progress
to (net_rx_ptr) at offsets 8-10. INTOFF side effect on entry.""")

subroutine(0x96B4, "restore_econet_state", hook=None,
    title="Restore Econet state from RX control block",
    description="""\
Loads rx_status_flags, protection_mask, and tx_in_progress
from (net_rx_ptr) at offsets 8-10, then reinitialises via
adlc_init_workspace.""")

subroutine(0x96CD, "install_nmi_shim", hook=None,
    title="Copy NMI shim from ROM (&9FCA) to RAM (&0D00)",
    description="""\
Copies 32 bytes. Interrupts are enabled during the copy.""")

# ============================================================
# Relocated code block comments
# ============================================================
subroutine(0x0016, "tube_brk_handler", hook=None,
    title="Tube BRK handler (BRKV target) — reference: NFS11 NEWBR",
    description="""\
Sends error information to the Tube co-processor via R2 and R4:
  1. Sends &FF to R4 (WRIFOR) to signal error
  2. Reads R2 data (flush any pending byte)
  3. Sends &00 via R2, then error number from (&FD),0
  4. Loops sending error string bytes via R2 until zero terminator
  5. Falls through to tube_reset_stack → tube_main_loop
The main loop continuously polls R1 for WRCH requests (forwarded
to OSWRITCH &FFCB) and R2 for command bytes (dispatched via the
14-entry table at &0500). The R2 command byte is stored at &55
before dispatch via JMP (&0500).""")

subroutine(0x0400, "tube_code_page4", hook=None,
    title="Tube host code page 4 — reference: NFS12 (BEGIN, ADRR, SENDW)",
    description="""\
Copied from ROM at reloc_p4_src during init. The first 28 bytes
(&0400-&041B) overlap with the end of the ZP block (the same ROM
bytes serve both the ZP copy at &005B-&0076 and this page). Contains:
  &0400: JMP &0473 (BEGIN — CLI parser / startup entry)
  &0403: JMP &06E2 (tube_escape_check)
  &0406: tube_addr_claim — Tube address claim protocol (ADRR)
  &0414: tube_post_init — called after ROM→RAM copy
  &0473: BEGIN — startup/CLI entry, break type check
  &04E7: tube_rdch_handler — RDCHV target
  &04EF: tube_restore_regs — restore X,Y, dispatch entry 6
  &04F7: tube_read_r2 — poll R2 status, read data byte to A""")

subroutine(0x0500, "tube_dispatch_table", hook=None,
    title="Tube host code page 5 — reference: NFS13 (TASKS, BPUT-FILE)",
    description="""\
Copied from ROM at reloc_p4_src+&100 during init. Contains:
  &0500: tube_dispatch_table — 14-entry handler address table
  &051C: tube_wrch_handler — WRCHV target
  &051F: tube_send_and_poll — send byte via R2, poll for reply
  &0527: tube_poll_r1_wrch — service R1 WRCH while waiting for R2
  &053D: tube_release_return — restore regs and RTS
  &0543: tube_osbput — write byte to file
  &0550: tube_osbget — read byte from file
  &055B: tube_osrdch — read character
  &0569: tube_osfind — open file
  &0580: tube_osfind_close — close file (A=0)
  &058C: tube_osargs — file argument read/write
  &05B1: tube_read_string — read CR-terminated string into &0700
  &05C5: tube_oscli — execute * command
  &05CB: tube_reply_ack — send &7F acknowledge
  &05CD: tube_reply_byte — send byte and return to main loop
  &05D8: tube_osfile — whole file operation""")

subroutine(0x0600, "tube_code_page6", hook=None,
    title="Tube host code page 6 — reference: NFS13 (GBPB-ESCA)",
    description="""\
Copied from ROM at reloc_p4_src+&200 during init. &0600-&0601 is the tail
of tube_osfile (BEQ to tube_reply_byte when done). Contains:
  &0602: tube_osgbpb — multi-byte file I/O
  &0626: tube_osbyte_short — 2-param OSBYTE (returns X)
  &063B: tube_osbyte_long — 3-param OSBYTE (returns carry+Y+X)
  &065D: tube_osword — variable-length OSWORD (buffer at &0130)
  &06A3: tube_osword_rdln — OSWORD 0 (read line, 5-byte params)
  &06BB: tube_rdln_send_line — send input line from &0700
  &06D0: tube_send_r2 — poll R2 status, write A to R2 data
  &06D9: tube_send_r4 — poll R4 status, write A to R4 data
  &06E2: tube_escape_check — check &FF, forward escape to R1
  &06E8: tube_event_handler — EVNTV: forward event (A,X,Y) via R1
  &06F7: tube_send_r1 — poll R1 status, write A to R1 data""")

# ============================================================
# OSBYTE code table for VDU state save (&9304)
# ============================================================
label(0x9304, "osbyte_vdu_table")
comment(0x9304, "3-entry OSBYTE table for lang_2_save_palette_vdu (&9291)")
byte(0x9304, 1)
comment(0x9304, "OSBYTE &85: read cursor position", inline=True)
byte(0x9305, 1)
comment(0x9305, "OSBYTE &C2: read shadow RAM allocation", inline=True)
byte(0x9306, 1)
comment(0x9306, "OSBYTE &C3: read screen start address", inline=True)

# ============================================================
# Relocated code block sources (&9307, &934C, &944C, &954C)
# ============================================================
# These labels mark the ROM storage addresses. The code is
# disassembled at its runtime addresses via move() declarations
# near the top of this file. See the preamble for addresses.

# ============================================================
# Econet TX retry (&9248)
# ============================================================
subroutine(0x9248, "econet_tx_retry", hook=None,
    title="Transmit with retry loop (XMITFS/XMITFY)",
    description="""\
Calls the low-level transmit routine (BRIANX) with FSTRY (&FF = 255)
retries and FSDELY (&60 = 96) ms delay between attempts. On each
iteration, checks the result code: zero means success, non-zero
means retry. After all retries exhausted, reports a 'Net error'.
Entry point XMITFY allows a custom delay in Y.""",
    on_entry={"a": "handle bitmask (0=printer, non-zero=file)", "x": "TX control block address low", "y": "TX control block address high"})

# ============================================================
# Save palette and VDU state (&9291)
# ============================================================
subroutine(0x9291, "lang_2_save_palette_vdu", hook=None,
    title="Save palette and VDU state (CVIEW)",
    description="""\
Part of the VIEW facility (second iteration, started 27/7/82).
Uses dynamically allocated buffer store. The WORKP1 pointer
(&9E,&9F) serves double duty: non-zero indicates data ready AND
provides the buffer address — an efficient use of scarce zero-
page space. This code must be user-transparent as the NFS may not
be the dominant filing system.
Reads all 16 palette entries using OSWORD &0B (read palette) and
stores the results. Then reads cursor position (OSBYTE &85),
shadow RAM allocation (OSBYTE &C2), and screen start address
(OSBYTE &C3) using the 3-entry table at &9304 (osbyte_vdu_table).
On completion, restores the JSR buffer protection bits (LSTAT)
from OLDJSR to re-enable JSR reception, which was disabled during
the screen data capture to prevent interference.""")

# ============================================================
# Post-ACK scout processing (&99BB)
# ============================================================
subroutine(0x99BB, "post_ack_scout", hook=None,
    title="Post-ACK scout processing",
    description="""\
Called after the scout ACK has been transmitted. Processes the
received scout data stored in the buffer at &0D3D-&0D48.
Checks the port byte (&0D40) against open receive blocks to
find a matching listener. If a match is found, sets up the
data RX handler chain for the four-way handshake data phase.
If no match, discards the frame.""")

# ============================================================
# Immediate operation handler (&9A59)
# ============================================================
subroutine(0x9A59, "immediate_op", hook=None,
    title="Immediate operation handler (port = 0)",
    description="""\
Handles immediate (non-data-transfer) operations received via
scout frames with port byte = 0. The control byte (&0D3F)
determines the operation type:
  &81 = PEEK (read memory)
  &82 = POKE (write memory)
  &83 = JSR (remote procedure call)
  &84 = user procedure
  &85 = OS procedure
  &86 = HALT
  &87 = CONTINUE
The protection mask (LSTAT at &D63) controls which operations
are permitted — each bit enables or disables an operation type.
If the operation is not permitted by the mask, it is silently
ignored. LSTAT can be read/set via OSWORD &12 sub-functions 4/5.""")

# ============================================================
# Discard paths (&9A34 / &9A40 / &9A43)
# ============================================================
subroutine(0x9A34, "discard_reset_listen", hook=None,
    title="Discard with full ADLC reset",
    description="""\
Performs adlc_full_reset (CR1=&C1, reset both TX and RX sections),
then falls through to discard_after_reset. Used when the ADLC is
in an unexpected state and needs a hard reset before returning
to idle listen mode. 5 references — the main error recovery path.""")

subroutine(0x9A40, "discard_listen", hook=None,
    title="Discard frame (gentle)",
    description="""\
Sends RX_DISCONTINUE (CR1=&A2: RIE|RX_DISCONTINUE) to abort the
current frame reception without a full reset, then falls through
to discard_after_reset. Used for clean rejection of frames that
are correctly formatted but not for us (wrong station/network).""")

subroutine(0x9A43, "discard_after_reset", hook=None,
    title="Return to idle listen after reset/discard",
    description="""\
Just calls adlc_rx_listen (CR1=&82, CR2=&67) to re-enter idle
RX mode, then RTI. The simplest of the three discard paths —
used as the tail of both discard_reset_listen and discard_listen.""")

# ============================================================
# Unreferenced data block (&9F4B-&9F5A)
# ============================================================
# 16 bytes of unreferenced data between tx_store_result and
# tx_calc_transfer. No code in any NFS version references this
# block. The byte pattern suggests two 8-entry lookup tables
# (possibly ADLC control register values), but their original
# purpose is unknown.
comment(0x9F4B, "Unreferenced data block (purpose unknown)")
byte(0x9F4B, 16)

# ============================================================
# Transfer size calculation (&9F5B)
# ============================================================
subroutine(0x9F5B, "tx_calc_transfer", hook=None,
    title="Calculate transfer size",
    description="""\
Computes the number of bytes actually transferred during a data
frame reception. Subtracts the low pointer (LPTR, offset 4 in
the RXCB) from the current buffer position to get the byte count,
and stores it back into the RXCB's high pointer field (HPTR,
offset 8). This tells the caller how much data was received.""")
# Buffer validity check
comment(0x9F5B, "Load RXCB[6] (buffer addr byte 2)", inline=True)
comment(0x9F60, "AND with TX block[7] (byte 3)", inline=True)
comment(0x9F62, "Both &FF = no buffer?", inline=True)
comment(0x9F64, "Yes: fallback path", inline=True)
comment(0x9F66, "Transmit in progress?", inline=True)
comment(0x9F69, "No: fallback path", inline=True)
# Set transfer-complete flag
comment(0x9F6E, "Set bit 1 (transfer complete)", inline=True)
# 4-byte subtraction: RXCB[4:7] - RXCB[8:11] → workspace
comment(0x9F73, "Init borrow for 4-byte subtract", inline=True)
comment(0x9F74, "Save carry on stack", inline=True)
comment(0x9F75, "Y=4: start at RXCB offset 4", inline=True)
comment(0x9F77, "Load RXCB[Y] (current ptr byte)", inline=True)
comment(0x9F79, "Y += 4: advance to RXCB[Y+4]", inline=True)
comment(0x9F7D, "Restore borrow from previous byte", inline=True)
comment(0x9F7E, "Subtract RXCB[Y+4] (start ptr byte)", inline=True)
comment(0x9F80, "Store result byte", inline=True)
comment(0x9F83, "Y -= 3: next source byte", inline=True)
comment(0x9F86, "Save borrow for next byte", inline=True)
comment(0x9F87, "Done all 4 bytes?", inline=True)
comment(0x9F89, "No: next byte pair", inline=True)
comment(0x9F8B, "Discard final borrow", inline=True)
# Tube address claim
comment(0x9F8E, "Compute address of RXCB+4", inline=True)
comment(0x9F93, "X = low byte of RXCB+4", inline=True)
comment(0x9F94, "Y = high byte of RXCB ptr", inline=True)
comment(0x9F96, "Tube claim type &C2", inline=True)
comment(0x9F9B, "No Tube: skip reclaim", inline=True)
comment(0x9F9D, "Tube: reclaim with scout status", inline=True)
comment(0x9FA3, "C=1: Tube address claimed", inline=True)
comment(0x9FA4, "Restore X", inline=True)
# Fallback: 2-byte size when no active TX
comment(0x9FA9, "Load RXCB[4] (current ptr lo)", inline=True)
comment(0x9FAE, "Subtract RXCB[8] (start ptr lo)", inline=True)
comment(0x9FB0, "Store transfer size lo", inline=True)
comment(0x9FB4, "Load RXCB[5] (current ptr hi)", inline=True)
comment(0x9FBC, "Copy RXCB[8] to open port buffer lo", inline=True)
comment(0x9FC7, "Store transfer size hi", inline=True)
comment(0x9FC9, "Return with C=1", inline=True)

# ============================================================
# NMI shim at end of ROM (&9FCA-&9FFF)
# ============================================================
subroutine(0x9FCB, "nmi_bootstrap_entry", hook=None,
    title="Bootstrap NMI entry point (in ROM)",
    description="""\
An alternate NMI handler that lives in the ROM itself rather than
in the RAM workspace at &0D00. Unlike the RAM shim (which uses a
self-modifying JMP to dispatch to different handlers), this one
hardcodes JMP nmi_rx_scout (&96F6). Used as the initial NMI handler
before the workspace has been properly set up during initialisation.
Same sequence as the RAM shim: BIT &FE18 (INTOFF), PHA, TYA, PHA,
LDA romsel, STA &FE30, JMP &96F6.""")

subroutine(0x9FD9, "rom_set_nmi_vector", hook=None,
    title="ROM copy of set_nmi_vector + nmi_rti",
    description="""\
A version of the NMI vector-setting subroutine and RTI sequence
that lives in ROM. The RAM workspace copy at &0D0E/&0D14 is the
one normally used at runtime; this ROM copy is used during early
initialisation before the RAM workspace has been set up, and as
the source for the initial copy to RAM.""")

# ============================================================
# Secondary dispatch entries (indices 19-32)
# ============================================================
# These are accessed via callers at &8079 and &808C which set
# different Y base offsets. They handle *-command parsing and
# filing system operations. The exact mapping of indices to
# handlers hasn't been fully traced yet.

# ============================================================
# OSWORD &12 handler detail
# ============================================================
# OSWORD &12 (RS) dispatches on sub-function codes 0-9:
# read/set FS station, printer station, protection masks,
# context handles (URD/CSD/LIB), local station, JSR buffer size.
# Uses the bidirectional copy at &8E22 to transfer data between
# the OSWORD parameter block and the FS workspace.

# ============================================================
# ADLC full reset (&96DC)
# ============================================================
subroutine(0x96DC, "adlc_full_reset", hook=None,
    title="ADLC full reset",
    description="""\
Aborts all activity and returns to idle RX listen mode.""")

comment(0x96DC, "CR1=&C1: TX_RESET | RX_RESET | AC (both sections in reset, address control set)", inline=True)
comment(0x96E1, "CR4=&1E (via AC=1): 8-bit RX word length, abort extend enabled, NRZ encoding", inline=True)
comment(0x96E6, "CR3=&00 (via AC=1): no loop-back, no AEX, NRZ, no DTR", inline=True)

# ============================================================
# Enter RX listen mode (&96EB)
# ============================================================
subroutine(0x96EB, "adlc_rx_listen", hook=None,
    title="Enter RX listen mode",
    description="""\
TX held in reset, RX active with interrupts. Clears all status.""")

comment(0x96EB, "CR1=&82: TX_RESET | RIE (TX in reset, RX interrupts enabled)", inline=True)
comment(0x96F0, "CR2=&67: CLR_TX_ST | CLR_RX_ST | FC_TDRA | 2_1_BYTE | PSE", inline=True)

# ============================================================
# NMI RX scout handler (&96F6) — idle listen
# ============================================================
subroutine(0x96F6, "nmi_rx_scout", hook=None,
    title="NMI RX scout handler (initial byte)",
    description="""\
Default NMI handler for incoming scout frames. Checks if the frame
is addressed to us or is a broadcast. Installed as the NMI target
during idle RX listen mode.
Tests SR2 bit0 (AP = Address Present) to detect incoming data.
Reads the first byte (destination station) from the RX FIFO and
compares against our station ID. Reading &FE18 also disables NMIs
(INTOFF side effect).""")

comment(0x96F6, "A=&01: mask for SR2 bit0 (AP = Address Present)", inline=True)
comment(0x96F8, "BIT SR2: Z = A AND SR2 -- tests if AP is set", inline=True)
comment(0x96FB, "AP not set, no incoming data -- check for errors", inline=True)
comment(0x96FD, "Read first RX byte (destination station address)", inline=True)
comment(0x9700, "Compare to our station ID (&FE18 read = INTOFF, disables NMIs)", inline=True)
comment(0x9703, "Match -- accept frame", inline=True)
comment(0x9705, "Check for broadcast address (&FF)", inline=True)
comment(0x9707, "Neither our address nor broadcast -- reject frame", inline=True)
comment(0x9709, "Flag &40 = broadcast frame", inline=True)
comment(0x970E, "Install next NMI handler at &9715 (RX scout second byte)", inline=True)

# ============================================================
# RX scout second byte handler (&9715)
# ============================================================
subroutine(0x9715, "nmi_rx_scout_net", hook=None,
    title="RX scout second byte handler",
    description="""\
Reads the second byte of an incoming scout (destination network).
Checks for network match: 0 = local network (accept), &FF = broadcast
(accept and flag), anything else = reject.
Installs the scout data reading loop handler at &9747.""")

comment(0x9715, "BIT SR2: test for RDA (bit7 = data available)", inline=True)
comment(0x9718, "No RDA -- check errors", inline=True)
comment(0x971A, "Read destination network byte", inline=True)
comment(0x971D, "Network = 0 -- local network, accept", inline=True)
comment(0x971F, "EOR &FF: test if network = &FF (broadcast)", inline=True)
comment(0x9721, "Broadcast network -- accept", inline=True)
comment(0x9723, "Reject: wrong network. CR1=&A2: RIE|RX_DISCONTINUE", inline=True)

comment(0x972E, "Store Y offset for scout data buffer", inline=True)
comment(0x9730, "Install scout data reading loop at &9747", inline=True)

# ============================================================
# Error/discard path (&9737)
# ============================================================
subroutine(0x9737, "scout_error", hook=None,
    title="Scout error/discard handler",
    description="""\
Reached when the scout data loop sees no RDA (BPL at &974C) or
when scout completion finds unexpected SR2 state.
If SR2 & &81 is non-zero (AP or RDA still active), performs full
ADLC reset and discards. If zero (clean end), discards via &9A40.
This path is a common landing for any unexpected ADLC state during
scout reception.""")

comment(0x9737, "Read SR2", inline=True)
comment(0x973A, "Test AP (b0) | RDA (b7)", inline=True)
comment(0x973C, "Neither set -- clean end, discard via &9744", inline=True)
comment(0x973E, "Unexpected data/status: full ADLC reset", inline=True)
comment(0x9741, "Discard and return to idle", inline=True)

# ============================================================
# Scout data reading loop (&9747-&976E)
# ============================================================
# This is the critical Path 1 code for ADLC FV/PSE interaction.
# The loop reads scout body bytes two at a time, storing them at
# &0D3D+Y. Between each pair, it checks SR2 to detect frame
# completion (FV set) or errors.
#
# ADLC timing requirement: after the CPU reads the penultimate byte,
# FV must be visible in SR2 before the next SR2 check. Beebium's
# inline refill + byte timer reset ensures this: reading the
# penultimate byte triggers inline refill of the last byte, which
# sets FV immediately (push-time FV). The byte timer reset prevents
# the timer from firing mid-loop.
subroutine(0x9747, "scout_data_loop", hook=None,
    title="Scout data reading loop",
    description="""\
Reads the body of a scout frame, two bytes per iteration. Stores
bytes at &0D3D+Y (scout buffer: src_stn, src_net, ctrl, port, ...).
Between each pair it checks SR2:
  - At entry (&9749): LDA SR2, BPL tests RDA (bit7)
    - No RDA (BPL) -> error (&9737)
    - RDA set (BMI) -> read byte
  - After first byte (&9755): LDA SR2
    - RDA set (BMI) -> read second byte
    - SR2 non-zero (BNE) -> scout completion (&9771)
      This is the FV detection point: when FV is set (by inline refill
      of the last byte during the preceding RX FIFO read), SR2 is
      non-zero and the branch is taken.
    - SR2 = 0 -> RTI, wait for next NMI
  - After second byte (&9769): LDA SR2
    - SR2 non-zero (BNE) -> loop back to &974C
    - SR2 = 0 -> RTI, wait for next NMI
The loop ends at Y=&0C (12 bytes max in scout buffer).""")

comment(0x9747, "Y = buffer offset", inline=True)
comment(0x9749, "Read SR2", inline=True)
comment(0x974C, "No RDA -- error handler &9737", inline=True)
comment(0x974E, "Read data byte from RX FIFO", inline=True)
comment(0x9751, "Store at &0D3D+Y (scout buffer)", inline=True)
comment(0x9754, "Advance buffer index", inline=True)
comment(0x9755, "Read SR2 again (FV detection point)", inline=True)
comment(0x9758, "RDA set -- more data, read second byte", inline=True)
comment(0x975A, "SR2 non-zero (FV or other) -- scout completion", inline=True)
comment(0x975C, "Read second byte of pair", inline=True)
comment(0x975F, "Store at &0D3D+Y", inline=True)
comment(0x9762, "Advance and check buffer limit", inline=True)
comment(0x9765, "Buffer full (Y=12) -- force completion", inline=True)
comment(0x9769, "Read SR2 for next pair", inline=True)
comment(0x976C, "SR2 non-zero -- loop back for more bytes", inline=True)
comment(0x976E, "SR2 = 0 -- RTI, wait for next NMI", inline=True)

# ============================================================
# Scout completion (&9771-&978F)
# ============================================================
subroutine(0x9771, "scout_complete", hook=None,
    title="Scout completion handler",
    description="""\
Reached from the scout data loop when SR2 is non-zero (FV detected).
Disables PSE to allow individual SR2 bit testing:
  CR1=&00 (clear all enables)
  CR2=&84 (RDA_SUPPRESS_FV | FC_TDRA) -- no PSE, no CLR bits
Then checks FV (bit1) and RDA (bit7):
  - No FV (BEQ) -> error &9737 (not a valid frame end)
  - FV set, no RDA (BPL) -> error &9737 (missing last byte)
  - FV set, RDA set -> read last byte, process scout
After reading the last byte, the complete scout buffer (&0D3D-&0D48)
contains: src_stn, src_net, ctrl, port [, extra_data...].
The port byte at &0D40 determines further processing:
  - Port = 0 -> immediate operation (&9A59)
  - Port non-zero -> check if it matches an open receive block""")

comment(0x9771, "CR1=&00: disable all interrupts", inline=True)
comment(0x9776, "CR2=&84: disable PSE, enable RDA_SUPPRESS_FV", inline=True)
comment(0x977B, "A=&02: FV mask for SR2 bit1", inline=True)
comment(0x977D, "BIT SR2: test FV (Z) and RDA (N)", inline=True)
comment(0x9780, "No FV -- not a valid frame end, error", inline=True)
comment(0x9782, "FV set but no RDA -- missing last byte, error", inline=True)
comment(0x9784, "Read last byte from RX FIFO", inline=True)
comment(0x9787, "Store last byte at &0D3D+Y", inline=True)
comment(0x978A, "CR1=&44: RX_RESET | TIE (switch to TX for ACK)", inline=True)
comment(0x978F, "Check port byte: 0 = immediate op, non-zero = data transfer", inline=True)
comment(0x9792, "Port non-zero -- look for matching receive block", inline=True)
comment(0x9794, "Port = 0 -- immediate operation handler", inline=True)

# ============================================================
# Data RX handler (&9839-&98CE)
# ============================================================
# This handler chain receives the data frame in a four-way handshake.
# After sending the scout ACK, the ROM installs &9839 to receive
# the incoming data frame.
subroutine(0x9839, "nmi_data_rx", hook=None,
    title="Data frame RX handler (four-way handshake)",
    description="""\
Receives the data frame after the scout ACK has been sent.
First checks AP (Address Present) for the start of the data frame.
Reads and validates the first two address bytes (dest_stn, dest_net)
against our station address, then installs continuation handlers
to read the remaining data payload into the open port buffer.

Handler chain: &9839 (AP+addr check) -> &984F (net=0 check) ->
&9865 (skip ctrl+port) -> &989A (bulk data read) -> &98CE (completion)""")

comment(0x982D, "CR1=&82: TX_RESET | RIE (switch to RX for data frame)", inline=True)
comment(0x984F, "Validate source network = 0", inline=True)
comment(0x9865, "Skip control and port bytes (already known from scout)", inline=True)
comment(0x986A, "Discard control byte", inline=True)
comment(0x986D, "Discard port byte", inline=True)

# ============================================================
# Data frame bulk read (&989A-&98CE)
# ============================================================
subroutine(0x989A, "nmi_data_rx_bulk", hook=None,
    title="Data frame bulk read loop",
    description="""\
Reads data payload bytes from the RX FIFO and stores them into
the open port buffer at (open_port_buf),Y. Reads bytes in pairs
(like the scout data loop), checking SR2 between each pair.
SR2 non-zero (FV or other) -> frame completion at &98CE.
SR2 = 0 -> RTI, wait for next NMI to continue.""")

comment(0x989A, "Y = buffer offset, resume from last position", inline=True)
comment(0x989C, "Read SR2 for next pair", inline=True)

# ============================================================
# Data frame completion (&98CE-&98F4)
# ============================================================
subroutine(0x98CE, "data_rx_complete", hook=None,
    title="Data frame completion",
    description="""\
Reached when SR2 non-zero during data RX (FV detected).
Same pattern as scout completion (&9771): disables PSE (CR1=&00,
CR2=&84), then tests FV and RDA. If FV+RDA, reads the last byte.
If extra data available and buffer space remains, stores it.
Proceeds to send the final ACK via &995E.""")

comment(0x98DA, "A=&02: FV mask", inline=True)
comment(0x98DC, "BIT SR2: test FV (Z) and RDA (N)", inline=True)
comment(0x98DF, "No FV -- error", inline=True)
comment(0x98E1, "FV set, no RDA -- proceed to ACK", inline=True)
comment(0x98E7, "FV+RDA: read and store last data byte", inline=True)

# ============================================================
# Scout ACK / Final ACK TX (&995E-&99B5)
# ============================================================
subroutine(0x995E, "ack_tx", hook=None,
    title="ACK transmission",
    description="""\
Sends a scout ACK or final ACK frame as part of the four-way handshake.
If bit7 of &0D4A is set, this is a final ACK -> completion (&9F39).
Otherwise, configures for TX (CR1=&44, CR2=&A7) and sends the ACK
frame (dst_stn, dst_net from &0D3D, src_stn from &FE18, src_net=0).
The ACK frame has no data payload -- just address bytes.

After writing the address bytes to the TX FIFO, installs the next
NMI handler from &0D4B/&0D4C (saved by the scout/data RX handler)
and sends TX_LAST_DATA (CR2=&3F) to close the frame.""")

comment(0x9966, "CR1=&44: RX_RESET | TIE (switch to TX mode)", inline=True)
comment(0x996B, "CR2=&A7: RTS|CLR_TX_ST|FC_TDRA|2_1_BYTE|PSE", inline=True)
comment(0x9970, "Install saved next handler (&99BB for scout ACK)", inline=True)
comment(0x997A, "Load dest station from RX scout buffer", inline=True)
comment(0x997D, "BIT SR1: test TDRA (V=bit6)", inline=True)
comment(0x9980, "TDRA not ready -- error", inline=True)
comment(0x9982, "Write dest station to TX FIFO", inline=True)
comment(0x9985, "Write dest network to TX FIFO", inline=True)
comment(0x998B, "Install handler at &9992 (write src addr)", inline=True)

subroutine(0x9992, "nmi_ack_tx_src", hook=None,
    title="ACK TX continuation",
    description="""\
Writes source station and network to TX FIFO, completing the 4-byte
ACK frame. Then sends TX_LAST_DATA (CR2=&3F) to close the frame.""")
comment(0x9992, "Load our station ID (also INTOFF)", inline=True)
comment(0x9995, "BIT SR1: test TDRA", inline=True)
comment(0x9998, "TDRA not ready -- error", inline=True)
comment(0x999A, "Write our station to TX FIFO", inline=True)
comment(0x999D, "Write network=0 to TX FIFO", inline=True)
comment(0x99A7, "CR2=&3F: TX_LAST_DATA | CLR_RX_ST | FLAG_IDLE | FC_TDRA | 2_1_BYTE | PSE", inline=True)
comment(0x99AC, "Install saved handler from &0D4B/&0D4C", inline=True)

# ============================================================
# INACTIVE polling loop (&9C48)
# ============================================================
subroutine(0x9C48, "inactive_poll", hook=None,
    title="INACTIVE polling loop",
    description="""\
Polls SR2 for INACTIVE (bit2) to confirm the network line is idle before
attempting transmission. Uses a 3-byte timeout counter on the stack.
The timeout (~256^3 iterations) generates "Line Jammed" if INACTIVE
never appears.
The CTS check at &9C66-&9C6B works because CR2=&67 has RTS=0, so
cts_input_ is always true, and SR1_CTS reflects presence of clock hardware.""")

comment(0x9C4D, "Y=&E7: CR2 value for TX prep (RTS|CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)", inline=True)
comment(0x9C4F, "A=&04: INACTIVE mask for SR2 bit2", inline=True)
comment(0x9C53, "INTOFF -- disable NMIs", inline=True)
comment(0x9C56, "INTOFF again (belt-and-braces)", inline=True)
comment(0x9C59, "BIT SR2: Z = &04 AND SR2 -- tests INACTIVE", inline=True)
comment(0x9C5C, "INACTIVE not set -- re-enable NMIs and loop", inline=True)
comment(0x9C5E, "Read SR1 (acknowledge pending interrupt)", inline=True)
comment(0x9C61, "CR2=&67: CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE", inline=True)
comment(0x9C66, "A=&10: CTS mask for SR1 bit4", inline=True)
comment(0x9C68, "BIT SR1: tests CTS present", inline=True)
comment(0x9C6B, "CTS set -- clock hardware detected, start TX", inline=True)
comment(0x9C6D, "INTON -- re-enable NMIs (&FE20 read)", inline=True)
comment(0x9C71, "3-byte timeout counter on stack", inline=True)

# ============================================================
# Timeout error (&9C88) and TX setup (&9C84)
# ============================================================
comment(0x9C84, "TX_ACTIVE branch (A=&44 = CR1 value for TX active)")
subroutine(0x9C88, "tx_line_jammed", hook=None,
    title="TX timeout error handler (Line Jammed)",
    description="""\
Writes CR2=&07 to abort TX, cleans 3 bytes from stack (the
timeout loop's state), then stores error code &40 ("Line
Jammed") into the TX control block and signals completion.""")

comment(0x9C88, "CR2=&07: FC_TDRA | 2_1_BYTE | PSE (abort TX)", inline=True)
comment(0x9C90, "Error &40 = 'Line Jammed'", inline=True)

# ============================================================
# TX preparation (&9CA2)
# ============================================================
subroutine(0x9CA2, "tx_prepare", hook=None,
    title="TX preparation",
    description="""\
Configures ADLC for transmission: asserts RTS via CR2, enables TIE via CR1,
installs NMI TX handler at &9D4C, and re-enables NMIs.""")

comment(0x9CA2, "Write CR2 = Y (&E7: RTS|CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)", inline=True)
comment(0x9CA5, "CR1=&44: RX_RESET | TIE (TX active, TX interrupts enabled)", inline=True)
comment(0x9CAA, "Install NMI handler at &9D4C (TX data handler)", inline=True)
comment(0x9CB4, "INTON -- NMIs now fire for TDRA (&FE20 read)", inline=True)

# ============================================================
# NMI TX data handler (&9D4C)
# ============================================================
subroutine(0x9D4C, "nmi_tx_data", hook=None,
    title="NMI TX data handler",
    description="""\
Writes 2 bytes per NMI invocation to the TX FIFO at &FEA2. Uses the
BIT instruction on SR1 to test TDRA (V flag = bit6) and IRQ (N flag = bit7).
After writing 2 bytes, checks if the frame is complete. If more data,
tests SR1 bit7 (IRQ) via BMI -- if IRQ still asserted, writes 2 more bytes
without returning from NMI (tight loop). Otherwise returns via RTI.""")

comment(0x9D4C, "Load TX buffer index", inline=True)
comment(0x9D4F, "BIT SR1: V=bit6(TDRA), N=bit7(IRQ)", inline=True)
comment(0x9D52, "TDRA not set -- TX error", inline=True)
comment(0x9D54, "Load byte from TX buffer", inline=True)
comment(0x9D57, "Write to TX_DATA (continue frame)", inline=True)
comment(0x9D62, "Write second byte to TX_DATA", inline=True)
comment(0x9D65, "Compare index to TX length", inline=True)
comment(0x9D68, "Frame complete -- go to TX_LAST_DATA", inline=True)
comment(0x9D6A, "Check if we can send another pair", inline=True)
comment(0x9D6D, "IRQ set -- send 2 more bytes (tight loop)", inline=True)
comment(0x9D6F, "RTI -- wait for next NMI", inline=True)

# TX error path (&9D72-&9D85)
comment(0x9D72, "TX error path")
comment(0x9D72, "Error &42", inline=True)
comment(0x9D76, "CR2=&67: clear status, return to listen", inline=True)
comment(0x9D7B, "Error &41 (TDRA not ready)", inline=True)
comment(0x9D7D, "INTOFF (also loads station ID)", inline=True)
comment(0x9D80, "PHA/PLA delay loop (256 iterations for NMI disable)", inline=True)

# ============================================================
# TX_LAST_DATA and frame completion (&9D88)
# ============================================================
subroutine(0x9D88, "tx_last_data", hook=None,
    title="TX_LAST_DATA and frame completion",
    description="""\
Signals end of TX frame by writing CR2=&3F (TX_LAST_DATA). Then installs
the TX completion NMI handler at &9D94 which switches to RX mode.
CR2=&3F = 0011_1111:
  bit5: CLR_RX_ST -- clears fv_stored_ (prepares for RX of reply)
  bit4: TX_LAST_DATA -- tells ADLC this is the final data byte
  bit3: FLAG_IDLE -- send flags/idle after frame
  bit2: FC_TDRA -- force clear TDRA
  bit1: 2_1_BYTE -- two-byte transfer mode
  bit0: PSE -- prioritised status enable
Note: NO CLR_TX_ST (bit6=0), NO RTS (bit7=0 -- drops RTS after frame)""")

comment(0x9D88, "CR2=&3F: TX_LAST_DATA | CLR_RX_ST | FLAG_IDLE | FC_TDRA | 2_1_BYTE | PSE", inline=True)
comment(0x9D8D, "Install NMI handler at &9D94 (TX completion)", inline=True)

# ============================================================
# TX completion: switch to RX mode (&9D94)
# ============================================================
subroutine(0x9D94, "nmi_tx_complete", hook=None,
    title="TX completion: switch to RX mode",
    description="""\
Called via NMI after the frame (including CRC and closing flag) has been
fully transmitted. Switches from TX mode to RX mode by writing CR1=&82.
CR1=&82 = 1000_0010: TX_RESET | RIE (listen for reply).
Checks workspace flags to decide next action:
  - bit6 set at &0D4A -> completion at &9F39
  - bit0 set at &0D4A -> four-way handshake data phase at &9EDD
  - Otherwise -> install RX reply handler at &9DB2""")

comment(0x9D94, "CR1=&82: TX_RESET | RIE (now in RX mode)", inline=True)
comment(0x9D99, "Test workspace flags", inline=True)
comment(0x9D9C, "bit6 not set -- check bit0", inline=True)
comment(0x9D9E, "bit6 set -- TX completion", inline=True)
comment(0x9DA8, "bit0 set -- four-way handshake data phase", inline=True)
comment(0x9DAB, "Install RX reply handler at &9DB2", inline=True)

# ============================================================
# RX reply scout handler (&9DB2)
# ============================================================
subroutine(0x9DB2, "nmi_reply_scout", hook=None,
    title="RX reply scout handler",
    description="""\
Handles reception of the reply scout frame after transmission.
Checks SR2 bit0 (AP) for incoming data, reads the first byte
(destination station) and compares to our station ID via &FE18
(which also disables NMIs as a side effect).""")

comment(0x9DB2, "A=&01: AP mask for SR2", inline=True)
comment(0x9DB4, "BIT SR2: test AP (Address Present)", inline=True)
comment(0x9DB7, "No AP -- error", inline=True)
comment(0x9DBC, "Compare to our station ID (INTOFF side effect)", inline=True)
comment(0x9DBF, "Not our station -- error/reject", inline=True)
comment(0x9DC1, "Install next handler at &9DC8 (reply continuation)", inline=True)

# ============================================================
# RX reply continuation handler (&9DC8)
# ============================================================
subroutine(0x9DC8, "nmi_reply_cont", hook=None,
    title="RX reply continuation handler",
    description="""\
Reads the second byte of the reply scout (destination network) and
validates it is zero (local network). Installs &9DE3 for the
remaining two bytes (source station and network).
Optimisation: checks SR1 bit7 (IRQ still asserted) via BMI at &9DD9.
If IRQ is still set, falls through directly to &9DE3 without an RTI,
avoiding NMI re-entry overhead for short frames where all bytes arrive
in quick succession.""")

comment(0x9DC8, "BIT SR2: test for RDA (bit7 = data available)", inline=True)
comment(0x9DCB, "No RDA -- error", inline=True)
comment(0x9DCD, "Read destination network byte", inline=True)
comment(0x9DD0, "Non-zero -- network mismatch, error", inline=True)
comment(0x9DD2, "Install next handler at &9DE3 (reply validation)", inline=True)
comment(0x9DD6, "BIT SR1: test IRQ (N=bit7) -- more data ready?", inline=True)
comment(0x9DD9, "IRQ set -- fall through to &9DE3 without RTI", inline=True)
comment(0x9DDB, "IRQ not set -- install handler and RTI", inline=True)

# ============================================================
# RX reply validation handler (&9DE3)
# ============================================================
# This is the critical Path 2 code for ADLC FV/PSE interaction.
# The handler reads two bytes (source station and network) and
# then checks for FV. The key requirement is that RDA must be
# visible at &9DE3 even if FV has been latched.
#
# With Beebium's inline refill model, this works because the
# inline refill chain feeds bytes in rapid succession: each FIFO
# read refills the next byte. For a 4-byte reply scout:
#   Read byte 0 at &9DB9 -> refills byte 1 (RDA visible at &9DC8)
#   Read byte 1 at &9DCD -> refills byte 2 (RDA visible at &9DE3)
#   Read byte 2 at &9DE8 -> refills byte 3/LAST (FV set)
#   Read byte 3 at &9DF1 -> FIFO empty
#   Check FV at &9DFA -> FV is set
subroutine(0x9DE3, "nmi_reply_validate", hook=None,
    title="RX reply validation (Path 2 for FV/PSE interaction)",
    description="""\
Reads the source station and source network from the reply scout and
validates them against the original TX destination (&0D20/&0D21).
Sequence:
  1. Check SR2 bit7 (RDA) at &9DE3 -- must see data available
  2. Read source station at &9DE8, compare to &0D20 (tx_dst_stn)
  3. Read source network at &9DF0, compare to &0D21 (tx_dst_net)
  4. Check SR2 bit1 (FV) at &9DFA -- must see frame complete
If all checks pass, the reply scout is valid and the ROM proceeds
to send the scout ACK (CR2=&A7 for RTS, CR1=&44 for TX mode).""")

comment(0x9DE3, "BIT SR2: test RDA (bit7). Must be set for valid reply.", inline=True)
comment(0x9DE6, "No RDA -- error (FV masking RDA via PSE would cause this)", inline=True)
comment(0x9DE8, "Read source station", inline=True)
comment(0x9DEB, "Compare to original TX destination station (&0D20)", inline=True)
comment(0x9DEE, "Mismatch -- not the expected reply, error", inline=True)
comment(0x9DF0, "Read source network", inline=True)
comment(0x9DF3, "Compare to original TX destination network (&0D21)", inline=True)
comment(0x9DF6, "Mismatch -- error", inline=True)
comment(0x9DF8, "A=&02: FV mask for SR2 bit1", inline=True)
comment(0x9DFA, "BIT SR2: test FV -- frame must be complete", inline=True)
comment(0x9DFD, "No FV -- incomplete frame, error", inline=True)
comment(0x9DFF, "CR2=&A7: RTS|CLR_TX_ST|FC_TDRA|2_1_BYTE|PSE (TX in handshake)", inline=True)
comment(0x9E04, "CR1=&44: RX_RESET | TIE (TX active for scout ACK)", inline=True)
comment(0x9E09, "Install next handler at &9EDD (four-way data phase) into &0D4B/&0D4C", inline=True)
comment(0x9E13, "Load dest station for scout ACK TX", inline=True)
comment(0x9E16, "BIT SR1: test TDRA (V=bit6)", inline=True)
comment(0x9E19, "TDRA not ready -- error", inline=True)
comment(0x9E1B, "Write dest station to TX FIFO", inline=True)
comment(0x9E24, "Install handler at &9E2B (write src addr for scout ACK)", inline=True)

# ============================================================
# TX data phase: write src address (&9E2B)
# ============================================================
subroutine(0x9E2B, "nmi_scout_ack_src", hook=None,
    title="TX scout ACK: write source address",
    description="""\
Writes our station ID and network=0 to TX FIFO, completing the
4-byte scout ACK frame. Then proceeds to send the data frame.""")
comment(0x9E2B, "Load our station ID (also INTOFF)", inline=True)
comment(0x9E33, "Write our station to TX FIFO", inline=True)

# ============================================================
# TX data phase: send data payload (&9E50)
# ============================================================
subroutine(0x9E50, "nmi_data_tx", hook=None,
    title="TX data phase: send payload",
    description="""\
Sends the data frame payload from (open_port_buf),Y in pairs per NMI.
Same pattern as the NMI TX handler at &9D4C but reads from the port
buffer instead of the TX workspace. Writes two bytes per iteration,
checking SR1 IRQ between pairs for tight looping.""")
comment(0x9E50, "Y = buffer offset, resume from last position", inline=True)
comment(0x9E52, "BIT SR1: test TDRA (V=bit6)", inline=True)
comment(0x9E55, "TDRA not ready -- error", inline=True)
comment(0x9E57, "Write data byte to TX FIFO", inline=True)
comment(0x9E7D, "CR2=&3F: TX_LAST_DATA (close data frame)", inline=True)

# ============================================================
# Four-way handshake: switch to RX for final ACK (&9EDD)
# ============================================================
subroutine(0x9EDD, "handshake_await_ack", hook=None,
    title="Four-way handshake: switch to RX for final ACK",
    description="""\
After the data frame TX completes, switches to RX mode (CR1=&82)
and installs &9EE9 to receive the final ACK from the remote station.""")
comment(0x9EDD, "CR1=&82: TX_RESET | RIE (switch to RX for final ACK)", inline=True)
comment(0x9EE2, "Install handler at &9EE9 (RX final ACK)", inline=True)

# ============================================================
# Four-way handshake: RX final ACK (&9EE9-&9F3D)
# ============================================================
# Same pattern as &9DB2/&9DC8/&9DE3 but for the final ACK.
# Validates that the final ACK is from the expected station.
subroutine(0x9EE9, "nmi_final_ack", hook=None,
    title="RX final ACK handler",
    description="""\
Receives the final ACK in a four-way handshake. Same validation
pattern as the reply scout handler (&9DB2-&9DE3):
  &9EE9: Check AP, read dest_stn, compare to our station
  &9EFF: Check RDA, read dest_net, validate = 0
  &9F15: Check RDA, read src_stn/net, compare to TX dest
  &9F32: Check FV for frame completion
On success, stores result=0 at &9F39. On any failure, error &41.""")

comment(0x9EE9, "A=&01: AP mask", inline=True)
comment(0x9EEB, "BIT SR2: test AP", inline=True)
comment(0x9EEE, "No AP -- error", inline=True)
comment(0x9EF0, "Read dest station", inline=True)
comment(0x9EF3, "Compare to our station (INTOFF side effect)", inline=True)
comment(0x9EF6, "Not our station -- error", inline=True)
comment(0x9EF8, "Install handler at &9EFF (final ACK continuation)", inline=True)

comment(0x9EFF, "BIT SR2: test RDA", inline=True)
comment(0x9F02, "No RDA -- error", inline=True)
comment(0x9F04, "Read dest network", inline=True)
comment(0x9F07, "Non-zero -- network mismatch, error", inline=True)
comment(0x9F09, "Install handler at &9F15 (final ACK validation)", inline=True)
comment(0x9F0D, "BIT SR1: test IRQ -- more data ready?", inline=True)
comment(0x9F10, "IRQ set -- fall through to &9F15 without RTI", inline=True)

subroutine(0x9F15, "nmi_final_ack_validate", hook=None,
    title="Final ACK validation",
    description="""\
Reads and validates src_stn and src_net against original TX dest.
Then checks FV for frame completion.""")
comment(0x9F15, "BIT SR2: test RDA", inline=True)
comment(0x9F18, "No RDA -- error", inline=True)
comment(0x9F1A, "Read source station", inline=True)
comment(0x9F1D, "Compare to TX dest station (&0D20)", inline=True)
comment(0x9F20, "Mismatch -- error", inline=True)
comment(0x9F22, "Read source network", inline=True)
comment(0x9F25, "Compare to TX dest network (&0D21)", inline=True)
comment(0x9F28, "Mismatch -- error", inline=True)
comment(0x9F32, "A=&02: FV mask for SR2 bit1", inline=True)
comment(0x9F34, "BIT SR2: test FV -- frame must be complete", inline=True)
comment(0x9F37, "No FV -- error", inline=True)

# ============================================================
# Completion and error handlers (&9F39-&9F48)
# ============================================================
subroutine(0x9F39, "tx_result_ok", hook=None,
    title="TX completion handler",
    description="""\
Stores result code 0 (success) into the first byte of the TX control
block (nmi_tx_block),Y=0. Then sets &0D3A bit7 to signal completion
and calls full ADLC reset + idle listen via &9A34.""")
comment(0x9F39, "A=0: success result code", inline=True)
comment(0x9F3B, "BEQ: always taken (A=0)", inline=True)

subroutine(0x9F3F, "tx_store_result", hook=None,
    title="TX error handler",
    description="""\
Stores error code (A) into the TX control block, sets &0D3A bit7
for completion, and returns to idle via &9A34.
Error codes: &00=success, &40=line jammed, &41=not listening,
&42=net error.""")
comment(0x9F3F, "Y=0: index into TX control block", inline=True)
comment(0x9F41, "Store result/error code at (nmi_tx_block),0", inline=True)
comment(0x9F43, "&80: completion flag for &0D3A", inline=True)
comment(0x9F45, "Signal TX complete", inline=True)
comment(0x9F48, "Full ADLC reset and return to idle listen", inline=True)


# ============================================================
# Annotations back-propagated from NFS 3.60
# ============================================================
label(0x0000, "zp_ptr_lo")           # General-purpose ZP indirect pointer (lo) / indexed base
label(0x0001, "zp_ptr_hi")           # General-purpose ZP pointer (hi) / page counter
label(0x0002, "zp_work_2")           # Indexed scratch (control block access via X)
label(0x0003, "zp_work_3")           # Indexed scratch (control block access via X)
label(0x0012, "tube_data_ptr")       # Tube host: indirect pointer to transfer data (lo)
label(0x0013, "tube_data_ptr_hi")    # Tube host: indirect pointer to transfer data (hi)
label(0x0014, "tube_claim_flag")     # Tube host: address claim in progress flag
label(0x0015, "tube_claimed_id")     # Tube host: currently-claimed address (&80=none)
comment(0x0016, "A=&FF: signal error to co-processor via R4", inline=True)
comment(0x0018, "Send &FF error signal to Tube R4", inline=True)
comment(0x001B, "Flush any pending R2 byte", inline=True)
comment(0x001E, "A=0: send zero prefix to R2", inline=True)
comment(0x0020, "Send zero prefix byte via R2", inline=True)
comment(0x0023, "Y=0: start of error block at (&FD)", inline=True)
comment(0x0024, "Load error number from (&FD),0", inline=True)
comment(0x0026, "Send error number via R2", inline=True)
comment(0x0029, "Advance to next error string byte", inline=True)
label(0x002A, "tube_send_error_byte") # Load next error byte and send via R2 (alt entry)
comment(0x002A, "Load next error string byte", inline=True)
comment(0x002C, "Send error string byte via R2", inline=True)
comment(0x002F, "Zero byte = end of error string", inline=True)
comment(0x0030, "Loop until zero terminator sent", inline=True)
comment(0x0032, "Reset stack pointer to top", inline=True)
comment(0x0034, "TXS: set stack pointer from X", inline=True)
comment(0x0035, "Enable interrupts for main loop", inline=True)
comment(0x003A, "BIT R1 status: check WRCH request", inline=True)
comment(0x003D, "R1 not ready: check R2 instead", inline=True)
comment(0x003F, "Read character from Tube R1 data", inline=True)
comment(0x0045, "BIT R2 status: check command byte", inline=True)
comment(0x0048, "R2 not ready: loop back to R1 check", inline=True)
comment(0x004A, "Re-check R1: WRCH has priority over R2", inline=True)
comment(0x004D, "R1 ready: handle WRCH first", inline=True)
comment(0x004F, "Read command byte from Tube R2 data", inline=True)
comment(0x0052, "Self-modify JMP low byte for dispatch", inline=True)
comment(0x0054, "Dispatch to handler via indirect JMP", inline=True)
label(0x0058, "tube_xfer_page")      # Transfer source page high byte (&80 default)
label(0x0059, "tube_xfer_addr_2")    # Transfer address byte 2
label(0x005A, "tube_xfer_addr_3")    # Transfer address byte 3
label(0x0099, "prot_flags")          # PFLAGS: printer/protocol status flags
label(0x00A8, "ws_page")             # Multi-purpose: workspace page / RXCB counter / loop counter
label(0x00A9, "svc_state")           # Multi-purpose: service state / Tube flag / workspace offset
label(0x00AA, "osword_flag")         # OSWORD param byte / open-vs-read flag
label(0x00AB, "ws_ptr_lo")           # Workspace indirect pointer (lo)
label(0x00AC, "ws_ptr_hi")           # Workspace indirect pointer (hi)
label(0x00AD, "table_idx")           # OSBYTE/palette table index counter
label(0x00AE, "work_ae")             # Indexed workspace (single-use scratch)
label(0x00AF, "addr_work")           # Address work byte for comparison (indexed)
label(0x00B3, "fs_load_addr_3")     # WORK+3: load address byte 3
label(0x00B4, "fs_work_4")          # WORK+4: end address / compare target (lo)
label(0x00B5, "fs_work_5")          # WORK+5: examine arg count / end address (hi)
label(0x00B7, "fs_work_7")          # WORK+7: column count / end address byte 3
label(0x00B9, "fs_crflag")          # CRFLAG: carriage return / column flag
label(0x00BA, "fs_spool_handle")    # SPOOL1: saved spool file handle for comparison
label(0x00C0, "txcb_ctrl")          # TXCB control byte
label(0x00C1, "txcb_port")          # TXCB command/port byte
label(0x00C2, "txcb_dest")          # TXCB destination station (Y-indexed)
label(0x00C4, "txcb_start")         # TXCB data start address (lo) / reply buffer ptr
label(0x00C7, "txcb_pos")           # TXCB current transfer position (indexed)
label(0x00C8, "txcb_end")           # TXCB data end address (lo) / dest address
label(0x00CF, "fs_spool0")          # SPOOL0: handle bitmask / BGET result byte
label(0x00EF, "osbyte_a_copy")       # MOS copy of OSBYTE A parameter / command code
label(0x00F0, "osword_pb_ptr")       # OSBYTE/OSWORD parameter block pointer (lo)
label(0x00F1, "osword_pb_ptr_hi")    # OSBYTE/OSWORD parameter block pointer (hi)
label(0x00F3, "os_text_ptr_hi")      # GS text pointer (hi), paired with os_text_ptr at &F2
label(0x00F7, "osrdsc_ptr_hi")       # OSRDSC pointer (hi), paired with osrdsc_ptr at &F6
label(0x00FD, "brk_ptr")             # MOS BRK error pointer (lo), set after BRK instruction
label(0x00FF, "escape_flag")         # MOS escape flag: b7=escape condition active
comment(0x0400, "JMP to BEGIN startup entry", inline=True)
comment(0x0403, "JMP to tube_escape_check (&06A7)", inline=True)
comment(0x0406, "A>=&80: address claim; A<&80: data transfer", inline=True)
comment(0x0408, "A<&80: data transfer setup (SENDW)", inline=True)
comment(0x040A, "A>=&C0: new address claim from another host", inline=True)
comment(0x040C, "C=1: external claim, check ownership", inline=True)
comment(0x040E, "Map &80-&BF range to &C0-&FF for comparison", inline=True)
comment(0x0410, "Is this for our currently-claimed address?", inline=True)
comment(0x0412, "Not our address: return", inline=True)
comment(0x0416, "Store to claim-in-progress flag", inline=True)
comment(0x0418, "Return from tube_post_init", inline=True)
label(0x0419, "addr_claim_external")  # External address claim check (another host)
comment(0x0419, "Another host claiming; check if we're owner", inline=True)
comment(0x041B, "C=1: we have an active claim", inline=True)
comment(0x041D, "Compare with our claimed address", inline=True)
comment(0x041F, "Match: return (we already have it)", inline=True)
comment(0x0421, "Not ours: CLC = we don't own this address", inline=True)
comment(0x0422, "Return with C=0 (claim denied)", inline=True)
label(0x0423, "accept_new_claim")    # BCS: active claim exists, store incoming address
comment(0x0423, "Accept new claim: update our address", inline=True)
comment(0x0425, "Return with address updated", inline=True)
comment(0x0426, "Save 16-bit transfer address from (X,Y)", inline=True)
comment(0x0428, "Store address pointer low byte", inline=True)
comment(0x042A, "Send transfer type byte to co-processor", inline=True)
comment(0x042D, "X = transfer type for table lookup", inline=True)
comment(0x042E, "Y=3: send 4 bytes (address + claimed addr)", inline=True)
label(0x0430, "send_xfer_addr_bytes") # Send 4-byte transfer address to co-processor via R4
comment(0x0430, "Load transfer address byte from (X,Y)", inline=True)
comment(0x0432, "Send address byte to co-processor via R4", inline=True)
comment(0x0435, "Previous byte (big-endian: 3,2,1,0)", inline=True)
comment(0x0436, "Loop for all 4 address bytes", inline=True)
comment(0x0459, "Not SENDW type: skip release path", inline=True)
comment(0x0461, "Restart Tube main loop", inline=True)
comment(0x047A, "Init: start sending from &8000", inline=True)
comment(0x047C, "Store &80 as source page high byte", inline=True)
comment(0x047E, "Store &80 as page counter initial value", inline=True)
comment(0x0480, "A=&20: bit 5 mask for ROM type check", inline=True)
comment(0x0482, "ROM type bit 5: reloc address in header?", inline=True)
comment(0x0485, "No reloc addr: use defaults", inline=True)
comment(0x0487, "Skip past copyright string to find reloc addr", inline=True)
label(0x048A, "scan_copyright_end")  # Scan past null-terminated copyright string in ROM header
comment(0x048A, "Skip past null-terminated copyright string", inline=True)
comment(0x048B, "Load next byte from ROM header", inline=True)
comment(0x048E, "Loop until null terminator found", inline=True)
comment(0x0490, "Read 4-byte reloc address from ROM header", inline=True)
comment(0x0493, "Store reloc addr byte 1 as transfer addr", inline=True)
comment(0x0495, "Load reloc addr byte 2", inline=True)
comment(0x0498, "Store as source page start", inline=True)
comment(0x049A, "Load reloc addr byte 3", inline=True)
comment(0x049D, "Load reloc addr byte 4 (highest)", inline=True)
label(0x04A0, "store_xfer_end_addr") # BEQ: no reloc flag, store default end address
comment(0x04A0, "Store high byte of end address", inline=True)
comment(0x04A2, "Store byte 3 of end address", inline=True)
comment(0x0546, "Y=channel handle from R2", inline=True)
comment(0x0547, "Read data byte from R2 for BPUT", inline=True)
comment(0x054D, "BPUT done: send acknowledge, return", inline=True)
comment(0x0553, "Y=channel handle for OSBGET", inline=True)
comment(0x0566, "Return to Tube main loop", inline=True)
comment(0x056C, "A=0: close file, else open with filename", inline=True)
comment(0x056E, "Save open mode while reading filename", inline=True)
comment(0x056F, "Read filename string from R2 into &0700", inline=True)
comment(0x0572, "Recover open mode from stack", inline=True)
comment(0x057D, "Send file handle result to co-processor", inline=True)
comment(0x0580, "OSFIND close: read handle from R2", inline=True)
comment(0x0583, "Y=handle to close", inline=True)
comment(0x0584, "A=0: close command for OSFIND", inline=True)
comment(0x0589, "Close done: send acknowledge, return", inline=True)
comment(0x058F, "Y=file handle for OSARGS", inline=True)
comment(0x0590, "Read 4-byte arg + reason from R2 into ZP", inline=True)
label(0x0592, "read_osargs_params")  # Read 4 OSARGS parameter bytes from R2 into zero page
comment(0x0592, "Read next param byte from R2", inline=True)
comment(0x0595, "Params stored at &00-&03 (little-endian)", inline=True)
comment(0x0597, "Decrement byte counter", inline=True)
comment(0x059B, "Read OSARGS reason code from R2", inline=True)
comment(0x05A1, "Send result A back to co-processor", inline=True)
comment(0x05A4, "Return 4-byte result from ZP &00-&03", inline=True)
label(0x05A6, "send_osargs_result")  # Send 4 OSARGS result bytes back to co-processor via R2
comment(0x05A6, "Load result byte from zero page", inline=True)
comment(0x05A8, "Send byte to co-processor via R2", inline=True)
comment(0x05AB, "Previous byte (count down)", inline=True)
comment(0x05AC, "Loop for all 4 bytes", inline=True)
comment(0x05AE, "Return to Tube main loop", inline=True)
comment(0x05B1, "X=0: initialise string buffer index", inline=True)
comment(0x05B3, "Y=0: string buffer offset 0", inline=True)
comment(0x05B5, "Read next string byte from R2", inline=True)
comment(0x05B8, "Store byte in string buffer at &0700+Y", inline=True)
comment(0x05BB, "Next buffer position", inline=True)
comment(0x05BC, "Y overflow: string too long, truncate", inline=True)
comment(0x05BE, "Check for CR terminator", inline=True)
comment(0x05C0, "Not CR: continue reading string", inline=True)
label(0x05C2, "string_buf_done")     # BEQ: overflow or CR found, set XY=&0700/RTS
comment(0x05C2, "Y=7: set XY=&0700 for OSCLI/OSFIND", inline=True)
comment(0x05C4, "Return with XY pointing to &0700", inline=True)
comment(0x05C8, "Execute * command via OSCLI", inline=True)
comment(0x05CB, "&7F = success acknowledgement", inline=True)
comment(0x05CD, "Poll R2 status until ready", inline=True)
comment(0x05D0, "Bit 6 clear: not ready, loop", inline=True)
comment(0x05D2, "Write byte to R2 data register", inline=True)
comment(0x05D5, "Return to Tube main loop", inline=True)
comment(0x05DA, "Read next control block byte from R2", inline=True)
comment(0x05DD, "Store at &01+X (descending)", inline=True)
comment(0x05DF, "Decrement byte counter", inline=True)
comment(0x05E0, "Loop for all 16 bytes", inline=True)
comment(0x05E2, "Read filename string from R2 into &0700", inline=True)
comment(0x05E5, "XY=&0700: filename pointer for OSFILE", inline=True)
comment(0x05E7, "Store Y=7 as pointer high byte", inline=True)
comment(0x05E9, "Y=0 for OSFILE control block offset", inline=True)
comment(0x05EB, "Read OSFILE reason code from R2", inline=True)
comment(0x05EE, "Execute OSFILE operation", inline=True)
comment(0x05F3, "Send result A (object type) to co-processor", inline=True)
comment(0x05F6, "Return 16-byte control block to co-processor", inline=True)
label(0x05F8, "send_osfile_ctrl_blk") # Send 16-byte OSFILE control block to co-processor via R2
comment(0x05F8, "Load control block byte", inline=True)
comment(0x05FA, "Send byte to co-processor via R2", inline=True)
comment(0x05FD, "Decrement byte counter", inline=True)
comment(0x05FE, "Loop for all 16 bytes", inline=True)
comment(0x0635, "Send X result for 2-param OSBYTE", inline=True)
comment(0x0649, "Test for OSBYTE &9D (fast Tube BPUT)", inline=True)
comment(0x064B, "OSBYTE &9D (fast Tube BPUT): no result needed", inline=True)
comment(0x064F, "Encode carry (error flag) into bit 7", inline=True)
comment(0x0658, "Send Y result, then fall through to send X", inline=True)
comment(0x0666, "Read param block length from R2", inline=True)
comment(0x0669, "DEX: length 0 means no params to read", inline=True)
comment(0x0674, "Store param bytes into block at &0130", inline=True)
comment(0x067A, "Restore OSWORD number from Y", inline=True)
label(0x067B, "skip_param_read")     # BMI: zero-length params, skip R2 read loop
comment(0x067B, "XY=&0130: param block address for OSWORD", inline=True)
label(0x0687, "poll_r2_osword_result") # Poll R2 status waiting for OSWORD result data
comment(0x068C, "Read result block length from R2", inline=True)
comment(0x0690, "No results to send: return to main loop", inline=True)
comment(0x0692, "Send result block bytes from &0128 via R2", inline=True)
label(0x06A5, "read_rdln_ctrl_block") # Read 5-byte OSWORD 0 control block from R2
comment(0x06AD, "X=0 after loop, A=0 for OSWORD 0 (read line)", inline=True)
comment(0x06B4, "C=0: line read OK; C=1: escape pressed", inline=True)
comment(0x06B6, "&FF = escape/error signal to co-processor", inline=True)
comment(0x06BD, "&7F = line read successfully", inline=True)
comment(0x06C9, "Check for CR terminator", inline=True)
comment(0x06E2, "Check OS escape flag at &FF", inline=True)
comment(0x06E4, "SEC+ROR: put bit 7 of &FF into carry+bit 7", inline=True)
comment(0x06E6, "Escape set: forward to co-processor via R1", inline=True)
comment(0x06E8, "EVNTV: forward event A, Y, X to co-processor", inline=True)
comment(0x06E9, "Send &00 prefix (event notification)", inline=True)
label(0x0D11, "install_nmi_handler") # Entry: A=handler offset, installs NMI vector
label(0x0DE6, "nmi_sub_table")      # NMI substitution data (Y-indexed lookup)
label(0x0DF0, "rom_ws_table")       # ROM workspace pointer table (16 bytes, X=ROM#)
label(0x0DFE, "fs_context_base")    # Base for Y-indexed access to FS context at &0E00+
label(0x0E0B, "fs_context_hi")      # Command context high byte
label(0x0E16, "fs_work_16")         # FS workspace byte at offset &16
label(0x0E30, "fs_filename_buf")    # Parsed filename buffer
label(0x0EF7, "fs_reply_data")      # FS reply data area
label(0x0F06, "fs_func_code")           # Data byte 1: function code / direction flag / reply count
label(0x0F07, "fs_data_count")          # Data byte 2: block size (hi) / entry count
label(0x0F08, "fs_reply_cmd")           # Data byte 3: reply command / extent
label(0x0F09, "fs_load_vector")         # Data byte 4: indirect JMP target (load address lo)
label(0x0F0B, "fs_load_upper")          # Data byte 6: load address upper byte check
label(0x0F0C, "fs_addr_check")          # Data byte 7: address range validation byte
label(0x0F0D, "fs_file_len")            # Data byte 8: file length byte (indexed)
label(0x0F0E, "fs_file_attrs")          # Data byte 9: encoded file attributes
label(0x0F10, "fs_file_len_3")          # Data byte &0B: file length byte 3
label(0x0F11, "fs_obj_type")            # Data byte &0C: object type from FS reply
label(0x0F12, "fs_access_level")        # Data byte &0D: access level / length high
label(0x0F13, "fs_reply_stn")           # Data byte &0E: station number from FS reply
label(0x0F14, "fs_len_clear")           # Data byte &0F: length high (cleared on success)
label(0x0F16, "fs_boot_data")           # Data byte &11: boot option in reply area
label(0x0FDE, "fs_handle_mask")         # Handle bitmask for sequence tracking
label(0x0FDF, "fs_error_flags")         # BSXMIT error/status flags
label(0x0FE0, "fs_error_buf")           # Error buffer at end of FS page
comment(0x806F, "Command index >= 4: invalid *NET sub-command", inline=True)
comment(0x8071, "Out of range: return via c80e3/RTS", inline=True)
comment(0x8073, "X = command index (0-3)", inline=True)
label(0x807D, "prepare_cmd_dispatch")   # Prepare FS command and dispatch recognised *command
comment(0x8091, "Function code >= 8? Return (unsupported)", inline=True)
comment(0x8099, "X >= 5: invalid reason code, return", inline=True)
label(0x809B, "svc_dispatch_range")     # Service dispatch range check (out of range: return)
comment(0x809B, "Out of range: return via RTS", inline=True)
comment(0x80A0, "Decrement base offset counter", inline=True)
comment(0x80A1, "Loop until Y exhausted", inline=True)
comment(0x80A3, "Y=&FF (no further use)", inline=True)
label(0x80AF, "check_svc_high")         # Test service >= &FE (high-priority dispatch)
comment(0x80AF, "Service >= &FE?", inline=True)
comment(0x80B1, "Service < &FE: skip to &12/dispatch check", inline=True)
comment(0x80B3, "Service &FF: full init (vectors + RAM copy)", inline=True)
comment(0x80B5, "Service &FE: Y=0?", inline=True)
comment(0x80B7, "Y=0: no Tube data, skip to &12 check", inline=True)
comment(0x80F9, "Load ROM byte from page &93", inline=True)
comment(0x80FC, "Store to page &04 (Tube code)", inline=True)
comment(0x80FF, "Load ROM byte from page &94", inline=True)
comment(0x8102, "Store to page &05 (dispatch table)", inline=True)
comment(0x8105, "Load ROM byte from page &95", inline=True)
comment(0x8108, "Store to page &06", inline=True)
comment(0x810B, "DEY wraps 0 -> &FF on first iteration", inline=True)
comment(0x810C, "Loop until 256 bytes copied per page", inline=True)
comment(0x810E, "Run post-init routine in copied code", inline=True)
comment(0x8111, "X=&60: copy 97 bytes (&60..&00)", inline=True)
label(0x8113, "copy_nmi_workspace")  # Copy 97 bytes of NMI workspace init data from ROM
comment(0x8113, "Load NMI workspace init byte from ROM", inline=True)
comment(0x8116, "Store to zero page &16+X", inline=True)
comment(0x8118, "Next byte", inline=True)
comment(0x8119, "Loop until all workspace bytes copied", inline=True)
label(0x8127, "not_svc_12_nfs")        # BNE: not service &12 or not NFS (Y!=5)
comment(0x8127, "Service >= &0D?", inline=True)
label(0x8129, "svc_unhandled_return")   # Unhandled service (>= &0D): return unclaimed
comment(0x8129, "Service >= &0D: not handled, return", inline=True)
label(0x812B, "do_svc_dispatch")        # BNE: entry to TAX/workspace save/dispatch
comment(0x812B, "X = service number (dispatch index)", inline=True)
comment(0x812C, "Save &A9 (current service state)", inline=True)
comment(0x812E, "Push saved &A9", inline=True)
comment(0x812F, "Save &A8 (workspace page number)", inline=True)
comment(0x8131, "Push saved &A8", inline=True)
comment(0x8132, "Store service number to &A9", inline=True)
comment(0x8134, "Store Y (page number) to &A8", inline=True)
comment(0x8136, "A = Y for dispatch table offset", inline=True)
comment(0x8139, "Dispatch to service handler", inline=True)
comment(0x813C, "Recover service claim status from &A9", inline=True)
comment(0x813E, "Restore saved &A8 from stack", inline=True)
comment(0x813F, "Write back &A8", inline=True)
subroutine(0x8141, "svc_dispatch_epilogue", hook=None,
    title="Service dispatch epilogue",
    description="""\
Common return path for all dispatched service handlers.
Restores rom_svc_num from the stack (pushed by dispatch_service),
transfers X (ROM number) to A, then returns via RTS.""")
comment(0x8141, "Restore saved A from service dispatch", inline=True)
comment(0x8142, "Save to workspace &A9", inline=True)
comment(0x8144, "Return ROM number in A", inline=True)
comment(0x8146, "Y=4: offset of keyboard disable flag", inline=True)
comment(0x8148, "Read flag from RX buffer", inline=True)
comment(0x814A, "Zero: keyboard not disabled, skip", inline=True)
comment(0x814C, "A=0: value to clear flag and re-enable", inline=True)
comment(0x814F, "Clear keyboard disable flag in buffer", inline=True)
comment(0x8152, "OSBYTE &C9: Econet keyboard disable", inline=True)
comment(0x8154, "Re-enable keyboard (X=0, Y=0)", inline=True)
comment(0x8157, "Function &0A: remote operation complete", inline=True)
comment(0x8159, "Send notification to controlling station", inline=True)
comment(0x815C, "Save X (return value from TX)", inline=True)
comment(0x815E, "OSBYTE &CE: first system mask to reset", inline=True)
label(0x8160, "clear_osbyte_masks")   # Loop clearing OSBYTE mask bytes with AND &7F
comment(0x8160, "Restore X for OSBYTE call", inline=True)
comment(0x8162, "Y=&7F: AND mask (clear bit 7)", inline=True)
comment(0x8164, "Reset system mask byte", inline=True)
comment(0x8167, "Advance to next OSBYTE (&CE -> &CF)", inline=True)
comment(0x8169, "Reached &D0? (past &CF)", inline=True)
comment(0x816B, "No: reset &CF too", inline=True)
label(0x816D, "skip_kbd_reenable")      # BEQ: keyboard not disabled, skip re-enable
comment(0x816D, "A=0: clear remote state", inline=True)
comment(0x816F, "Clear &A9 (service dispatch state)", inline=True)
label(0x817D, "match_net_cmd")          # Try matching *NET command text
comment(0x817D, "X=1: ROM offset for \"NET\" match", inline=True)
comment(0x817F, "Try matching *NET command", inline=True)
comment(0x8182, "No match: return unclaimed", inline=True)
comment(0x8184, "Notify current FS of shutdown (FSCV A=6)", inline=True)
comment(0x8187, "C=1 for ROR", inline=True)
comment(0x8188, "Set bit 7 of l00a8 (inhibit auto-boot)", inline=True)
comment(0x818A, "Claim OS vectors, issue service &0F", inline=True)
comment(0x818D, "Y=&1D: top of FS state range", inline=True)
comment(0x818F, "Copy FS state from RX buffer...", inline=True)
comment(0x8191, "...to workspace (offsets &15-&1D)", inline=True)
comment(0x8194, "Next byte (descending)", inline=True)
comment(0x8195, "Loop until offset &14 done", inline=True)
comment(0x8197, "Continue loop", inline=True)
comment(0x8199, "ALWAYS branch to init_fs_vectors", inline=True)
comment(0x81CB, "Return (service not claimed)", inline=True)
comment(0x81CC, "FSCV reason 6 = FS shutdown", inline=True)
comment(0x81CE, "Tail-call via filing system control vector", inline=True)
comment(0x81D1, "Notify current FS of shutdown", inline=True)
comment(0x81D4, "OSBYTE &7A: scan keyboard", inline=True)
comment(0x81DA, "No key pressed: proceed with auto-boot", inline=True)
subroutine(0x81DC, "check_boot_key", hook=None,
    title="Check boot key",
    description="""\
Checks if the pressed key (in A) is 'N' (matrix address &55). If
not 'N', returns to the MOS without claiming the service call
(another ROM may boot instead). If 'N', forgets the keypress via
OSBYTE &78 and falls through to print_station_info.""")
comment(0x81DC, "XOR with &55: result=0 if key is 'N'", inline=True)
comment(0x81DE, "Not 'N': return without claiming", inline=True)
comment(0x81E1, "OSBYTE &78: clear key-pressed state", inline=True)
comment(0x81E6, "Print 'Econet Station ' banner", inline=True)
comment(0x8205, "Print ' No Clock' warning", inline=True)
comment(0x8211, "NOP (padding after inline string)", inline=True)
label(0x8212, "skip_no_clock_msg")     # BEQ: clock present, skip "No Clock" message
comment(0x8212, "Print two CRs (blank line)", inline=True)
comment(0x821C, "Write to FILEV-FSCV vector table", inline=True)
comment(0x821F, "Next byte (descending)", inline=True)
comment(0x8220, "Loop until all 14 bytes copied", inline=True)
comment(0x8222, "Read ROM ptr table addr, install NETV", inline=True)
comment(0x8225, "Install 7 handler entries in ROM ptr table", inline=True)
comment(0x8227, "7 FS vectors to install", inline=True)
comment(0x8229, "Install each 3-byte vector entry", inline=True)
comment(0x822C, "X=0 after loop; store as workspace offset", inline=True)
comment(0x8237, "Issue service &0A", inline=True)
comment(0x823A, "Non-zero after hard reset: skip auto-boot", inline=True)
comment(0x823E, "X = lo byte of auto-boot string at &8245", inline=True)
comment(0x824B, "Auto-boot string tail / NETV handler data", inline=True)
comment(0x827D, "A=0 for clearing workspace", inline=True)
comment(0x827F, "Y=4: remote status offset", inline=True)
comment(0x8281, "Clear status byte in net receive buffer", inline=True)
comment(0x8283, "Y=&FF: used for later iteration", inline=True)
comment(0x8285, "Clear RX ptr low byte", inline=True)
comment(0x8287, "Clear workspace ptr low byte", inline=True)
comment(0x8289, "Clear RXCB iteration counter", inline=True)
comment(0x828B, "Clear TX semaphore (no TX in progress)", inline=True)
comment(0x828E, "X=0 for OSBYTE", inline=True)
comment(0x8294, "X = break type from OSBYTE result", inline=True)
comment(0x8297, "Y=&15: printer station offset in RX buffer", inline=True)
comment(0x8299, "&FE = no server selected", inline=True)
comment(0x829E, "Store &FE at printer station offset", inline=True)
label(0x82B4, "init_rxcb_entries")   # Mark all RXCBs as available (&3F) in NFS workspace
comment(0x82B4, "Load RXCB counter", inline=True)
comment(0x82B6, "Convert to workspace byte offset", inline=True)
comment(0x82B9, "C=1: past max handles, done", inline=True)
comment(0x82BB, "Mark RXCB as available", inline=True)
comment(0x82BD, "Write &3F flag to workspace", inline=True)
comment(0x82BF, "Next RXCB number", inline=True)
comment(0x82C1, "Loop for all RXCBs", inline=True)
label(0x82C3, "read_station_id")       # BEQ/BCS: soft break or RXCBs done, read &FE18
comment(0x82CC, "Enable user-level RX (LFLAG=&40)", inline=True)
comment(0x82CE, "Store to rx_flags", inline=True)
comment(0x82D1, "OSBYTE &A8: read ROM pointer table address", inline=True)
comment(0x82D3, "X=0: read low byte", inline=True)
comment(0x82D5, "Y=&FF: read high byte", inline=True)
comment(0x82D7, "Returns table address in X (lo) Y (hi)", inline=True)
comment(0x82DA, "Store table base address low byte", inline=True)
comment(0x82DC, "Store table base address high byte", inline=True)
comment(0x82DE, "NETV extended vector offset in ROM ptr table", inline=True)
comment(0x82E0, "Set NETV low byte = &36 (vector dispatch)", inline=True)
comment(0x82E3, "Install 1 entry (NETV) in ROM ptr table", inline=True)
comment(0x82E5, "Load handler address low byte from table", inline=True)
comment(0x82E8, "Store to ROM pointer table", inline=True)
comment(0x82EA, "Next byte", inline=True)
comment(0x82EB, "Load handler address high byte from table", inline=True)
comment(0x82EE, "Store to ROM pointer table", inline=True)
comment(0x82F0, "Next byte", inline=True)
comment(0x82F1, "Write current ROM bank number", inline=True)
comment(0x82F3, "Store ROM number to ROM pointer table", inline=True)
comment(0x82F5, "Advance to next entry position", inline=True)
comment(0x82F6, "Count down entries", inline=True)
comment(0x82F7, "Loop until all entries installed", inline=True)
comment(0x82F9, "Y = next workspace page for MOS", inline=True)
comment(0x82FB, "Advance past workspace page", inline=True)
comment(0x82FC, "Return; Y = page after NFS workspace", inline=True)
comment(0x82FD, "Copy 10 bytes: FS state to workspace backup", inline=True)
comment(0x8305, "Offsets &15-&1D: server, handles, OPT, etc.", inline=True)
subroutine(0x830E, "init_tx_reply_port", hook=None,
    title="Initialise TX control block for FS reply on port &90",
    description="""\
Loads port &90 (PREPLY) into A, calls init_tx_ctrl_block to set
up the TX control block, stores the port and control bytes, then
decrements the control flag. Used by send_fs_reply_cmd to prepare
for receiving the fileserver's reply.""")
comment(0x830E, "A=&90: FS reply port (PREPLY)", inline=True)
comment(0x8310, "Init TXCB from template", inline=True)
comment(0x8313, "Store port number in TXCB", inline=True)
comment(0x8315, "Control byte: 3 = transmit", inline=True)
comment(0x8317, "Store control byte in TXCB", inline=True)
comment(0x8319, "Decrement TXCB flag to arm TX", inline=True)
comment(0x831C, "Preserve A across call", inline=True)
comment(0x831D, "Copy 12 bytes (Y=11..0)", inline=True)
comment(0x831F, "Load template byte", inline=True)
comment(0x8322, "Store to TX control block at &00C0", inline=True)
comment(0x8325, "Y < 2: also copy FS server station/network", inline=True)
comment(0x8327, "Skip station/network copy for Y >= 2", inline=True)
comment(0x8329, "Load FS server station (Y=0) or network (Y=1)", inline=True)
comment(0x832C, "Store to dest station/network at &00C2", inline=True)
comment(0x832F, "Next byte (descending)", inline=True)
comment(0x8330, "Loop until all 12 bytes copied", inline=True)
comment(0x8332, "Restore A", inline=True)
comment(0x8333, "Return", inline=True)
label(0x833A, "tx_ctrl_upper")       # TX control template upper half (high bytes/masks)
comment(0x8340, "Save flag byte for command", inline=True)
comment(0x8343, "C=1: include flag in FS command", inline=True)
comment(0x8344, "ALWAYS branch to prepare_fs_cmd", inline=True)
comment(0x8346, "V=0: command has no flag byte", inline=True)
comment(0x8347, "ALWAYS branch to prepare_fs_cmd", inline=True)
comment(0x8350, "V=0: standard FS command path", inline=True)
comment(0x8351, "Copy URD handle from workspace to buffer", inline=True)
comment(0x8354, "Store URD at &0F02", inline=True)
comment(0x835F, "Y=1: copy CSD (offset 1) then LIB (offset 0)", inline=True)
label(0x8361, "copy_dir_handles")       # Copy CSD and LIB handles into FS command header
comment(0x8361, "Copy CSD and LIB handles to command buffer", inline=True)
comment(0x8364, "Store at &0F03 (CSD) and &0F04 (LIB)", inline=True)
comment(0x8367, "Y=function code", inline=True)
comment(0x8368, "Loop for both handles", inline=True)
comment(0x836A, "Save carry (FS path vs byte-stream)", inline=True)
comment(0x836B, "Reply port &90 (PREPLY)", inline=True)
comment(0x836D, "Store at &0F00 (HDRREP)", inline=True)
comment(0x8370, "Copy TX template to &00C0", inline=True)
comment(0x8373, "A = X (buffer extent)", inline=True)
comment(0x8374, "HPTR = header (5) + data (X) bytes to send", inline=True)
comment(0x8376, "Store to TXCB end-pointer low", inline=True)
comment(0x8378, "Restore carry flag", inline=True)
comment(0x8379, "C=1: byte-stream path (BSXMIT)", inline=True)
comment(0x837B, "Save flags for send_fs_reply_cmd", inline=True)
comment(0x837C, "Point net_tx_ptr to &00C0; transmit", inline=True)
comment(0x837F, "Restore flags", inline=True)
comment(0x8380, "Save flags (V flag state)", inline=True)
comment(0x8381, "Set up RX wait for FS reply", inline=True)
comment(0x8386, "Transmit and wait (BRIANX)", inline=True)
comment(0x8389, "Restore flags", inline=True)
comment(0x838A, "Y=1: skip past command code byte", inline=True)
comment(0x838B, "Load return code from FS reply", inline=True)
comment(0x838D, "X = return code", inline=True)
comment(0x838E, "Zero: success, return", inline=True)
comment(0x8390, "V=0: standard path, error is fatal", inline=True)
comment(0x8392, "ADC #&2A: test for &D6 (not found)", inline=True)
label(0x8394, "check_fs_error")        # BVC: standard path, BNE to store_fs_error
comment(0x8394, "Non-zero: hard error, go to FSERR", inline=True)
comment(0x8396, "Return (success or soft &D6 error)", inline=True)
comment(0x8397, "Discard saved flags from stack", inline=True)
comment(0x8398, "X=&C0: TXCB address for byte-stream TX", inline=True)
comment(0x839A, "Y++ past command code", inline=True)
comment(0x839B, "Byte-stream transmit with retry", inline=True)
comment(0x839E, "Store result to &B3", inline=True)
comment(0x83A0, "C=0: success, check reply code", inline=True)
comment(0x83A3, "Save A (BPUT byte) on stack", inline=True)
comment(0x83A4, "Also save byte at &0FDF for BSXMIT", inline=True)
comment(0x83A7, "Transfer X for stack save", inline=True)
comment(0x83A8, "Save X on stack", inline=True)
comment(0x83A9, "Transfer Y (handle) for stack save", inline=True)
comment(0x83AA, "Save Y (handle) on stack", inline=True)
comment(0x83AB, "Save P (C = BPUT/BGET selector) on stack", inline=True)
comment(0x83AC, "Convert handle Y to single-bit mask", inline=True)
comment(0x83AF, "Store handle bitmask at &0FDE", inline=True)
comment(0x83B2, "Store handle bitmask for sequence tracking", inline=True)
comment(0x83B4, "&90 = data port (PREPLY)", inline=True)
comment(0x83B6, "Store reply port in command buffer", inline=True)
comment(0x83B9, "Set up 12-byte TXCB from template", inline=True)
comment(0x83BC, "CB reply buffer at &0FDC", inline=True)
comment(0x83BE, "Store reply buffer ptr low in TXCB", inline=True)
comment(0x83C0, "Error buffer at &0FE0", inline=True)
comment(0x83C2, "Store error buffer ptr low in TXCB", inline=True)
comment(0x83C4, "Y=1 (from init_tx_ctrl_block exit)", inline=True)
comment(0x83C5, "X=9: BPUT function code", inline=True)
comment(0x83C7, "Restore C: selects BPUT (0) vs BGET (1)", inline=True)
comment(0x83C8, "C=0 (BPUT): keep X=9", inline=True)
comment(0x83CB, "Store function code at &0FDD", inline=True)
comment(0x83D1, "X=&C0: TXCB address for econet_tx_retry", inline=True)
comment(0x83D3, "Transmit via byte-stream protocol", inline=True)
comment(0x83D6, "Load reply byte from buffer", inline=True)
comment(0x83D9, "Zero reply = success, skip error handling", inline=True)
comment(0x83DB, "Copy 32-byte reply to error buffer at &0FE0", inline=True)
comment(0x83DD, "Load reply byte at offset Y", inline=True)
comment(0x83E0, "Store to error buffer at &0FE0+Y", inline=True)
comment(0x83E3, "Next byte (descending)", inline=True)
comment(0x83E4, "Loop until all 32 bytes copied", inline=True)
comment(0x83E7, "A=&C7: read *SPOOL file handle", inline=True)
comment(0x83F6, "Y=&85: high byte of OSCLI string in ROM", inline=True)
comment(0x83F8, "Close SPOOL/EXEC via \"*SP.\" or \"*E.\"", inline=True)
label(0x83FB, "dispatch_fs_error")     # BNE: no handle match, reset ptr for FSERR
comment(0x83FB, "Reset CB pointer to error buffer at &0FE0", inline=True)
comment(0x83FD, "Reset reply ptr to error buffer", inline=True)
comment(0x83FF, "Reload reply byte for error dispatch", inline=True)
comment(0x8402, "Remember raw FS error code", inline=True)
comment(0x8405, "Y=1: point to error number byte in reply", inline=True)
comment(0x8407, "Clamp FS errors below &A8 to standard &A8", inline=True)
comment(0x8409, "Error >= &A8: keep original value", inline=True)
comment(0x840B, "Error < &A8: override with standard &A8", inline=True)
comment(0x840D, "Write clamped error number to reply buffer", inline=True)
comment(0x841B, "Save updated sequence number", inline=True)
comment(0x841E, "Restore Y from stack", inline=True)
comment(0x8420, "Restore X from stack", inline=True)
comment(0x8422, "Restore A from stack", inline=True)
comment(0x8423, "Return to caller", inline=True)
label(0x8424, "error_not_listening")     # Error code 8: "Not listening"
comment(0x8424, "Error code 8: \"Not listening\" error", inline=True)
comment(0x8426, "ALWAYS branch to set_listen_offset", inline=True)
comment(0x8428, "Load TX status byte for error lookup", inline=True)
comment(0x842A, "Mask to 3-bit error code (0-7)", inline=True)
comment(0x842C, "X = error code index", inline=True)
comment(0x842D, "Look up error message offset from table", inline=True)
comment(0x8430, "X=0: start writing at &0101", inline=True)
comment(0x8432, "Store BRK opcode at &0100", inline=True)
label(0x8435, "copy_error_message")     # Copy Econet error message string into BRK block
comment(0x8435, "Load error message byte", inline=True)
comment(0x8438, "Build error message at &0101+", inline=True)
comment(0x843B, "Zero byte = end of message; go execute BRK", inline=True)
comment(0x844A, "Save function code on stack", inline=True)
comment(0x844B, "Load current rx_flags", inline=True)
comment(0x844E, "Save rx_flags on stack for restore", inline=True)
comment(0x844F, "Set bit7: FS transaction in progress", inline=True)
comment(0x8451, "Write back updated rx_flags", inline=True)
label(0x8454, "skip_rx_flag_set")       # BNE: non-zero TX hi byte, skip bit-7 set
comment(0x8454, "Push two zero bytes as timeout counters", inline=True)
comment(0x8456, "First zero for timeout", inline=True)
comment(0x8457, "Second zero for timeout", inline=True)
comment(0x8458, "Y=0: index for flag byte check", inline=True)
comment(0x8459, "TSX: index stack-based timeout via X", inline=True)
comment(0x8461, "Three-stage nested timeout: inner loop", inline=True)
comment(0x8464, "Inner not expired: keep polling", inline=True)
comment(0x8466, "Middle timeout loop", inline=True)
comment(0x8469, "Middle not expired: keep polling", inline=True)
comment(0x846B, "Outer timeout loop (slowest)", inline=True)
comment(0x846E, "Outer not expired: keep polling", inline=True)
comment(0x8470, "Pop first timeout byte", inline=True)
comment(0x8471, "Pop second timeout byte", inline=True)
comment(0x8472, "Pop saved rx_flags into A", inline=True)
comment(0x8473, "Restore saved rx_flags from stack", inline=True)
comment(0x8476, "Pop saved function code", inline=True)
comment(0x8477, "A=saved func code; zero would mean no reply", inline=True)
comment(0x8479, "Return to caller", inline=True)
comment(0x8485, "C=1: flag for BGET mode", inline=True)
comment(0x8486, "Handle BGET via FS command", inline=True)
comment(0x8489, "SEC: set carry for error check", inline=True)
comment(0x848A, "A=&FE: mask for EOF check", inline=True)
comment(0x848C, "BIT l0fdf: test error flags", inline=True)
comment(0x848F, "V=1: error, return early", inline=True)
comment(0x8491, "CLC: no error", inline=True)
label(0x84AE, "return_4")
comment(0x8513, "Y=&0E: attribute byte offset in param block", inline=True)
comment(0x8515, "Load FS attribute byte", inline=True)
comment(0x8517, "Mask to 6 bits (FS → BBC direction)", inline=True)
comment(0x8519, "X=4: skip first 4 table entries (BBC→FS half)", inline=True)
comment(0x851B, "ALWAYS branch to shared bitmask builder", inline=True)
comment(0x851D, "Mask to 5 bits (BBC → FS direction)", inline=True)
comment(0x851F, "X=&FF: INX makes 0; start from table index 0", inline=True)
label(0x8521, "attrib_shift_bits")      # Attribute bitmask conversion (shared tail)
comment(0x8521, "Temp storage for source bitmask to shift out", inline=True)
comment(0x8523, "A=0: accumulate destination bits here", inline=True)
label(0x8525, "map_attrib_bits")         # Map source attribute bits via access_bit_table lookup
comment(0x8525, "Next table entry", inline=True)
comment(0x8526, "Shift out source bits one at a time", inline=True)
comment(0x8528, "Bit was 0: skip this destination bit", inline=True)
comment(0x852A, "OR in destination bit from lookup table", inline=True)
label(0x852D, "skip_set_attrib_bit")   # BCC: source bit was 0, don't OR destination
comment(0x852D, "Loop while source bits remain (A != 0)", inline=True)
comment(0x852F, "Return; A = converted attribute bitmask", inline=True)
label(0x8543, "print_inline_char")     # Print inline string bytes via OSASCI until bit-7 terminator
label(0x8549, "print_next_char")      # INC lo-byte of pointer, load and print next char
label(0x8584, "no_dot_exit")          # BCC: char < '.', CLC then RTS (no dot found)
label(0x8585, "parse_decimal_rts")    # BEQ: char = '.', LDA result/RTS
comment(0x8588, "Handle number to Y for conversion", inline=True)
comment(0x8589, "Force unconditional conversion", inline=True)
label(0x85A1, "handle_mask_exit")     # BEQ/BNE: PLA/TAX/PLA/RTS exit restoring X and A
comment(0x85CE, "Compare 4 bytes (index 4,3,2,1)", inline=True)
label(0x85D0, "compare_addr_byte")     # EOR bytes of two 4-byte addresses checking for mismatch
comment(0x85D0, "Load byte from first address", inline=True)
comment(0x85D2, "XOR with corresponding byte", inline=True)
comment(0x85D4, "Mismatch: Z=0, return unequal", inline=True)
comment(0x85D7, "Continue comparing", inline=True)
comment(0x85DA, "X=first handle (&20)", inline=True)
comment(0x85DC, "Y=last handle (&27)", inline=True)
comment(0x8697, "Y=1: copy 2 bytes (high then low)", inline=True)
comment(0x8699, "Load filename ptr from control block", inline=True)
comment(0x869B, "Store to MOS text pointer (&F2/&F3)", inline=True)
comment(0x869E, "Next byte (descending)", inline=True)
comment(0x869F, "Loop for both bytes", inline=True)
comment(0x86A8, "Read next character via GSREAD", inline=True)
comment(0x86AB, "C=1 from GSREAD: end of string reached", inline=True)
comment(0x86AD, "Advance buffer index", inline=True)
comment(0x86AE, "Store parsed character to &0E30+X", inline=True)
comment(0x86B1, "ALWAYS loop (GSREAD clears C on success)", inline=True)
comment(0x86B3, "CR = &0D", inline=True)
comment(0x86B5, "Store CR terminator at end of string", inline=True)
comment(0x86B8, "Point fs_crc_lo/hi at &0E30 parse buffer", inline=True)
comment(0x86BA, "fs_crc_lo = &30", inline=True)
comment(0x86BC, "fs_crc_hi = &0E → buffer at &0E30", inline=True)
comment(0x86BE, "Store high byte", inline=True)
comment(0x86C0, "Recover function code from saved A", inline=True)
comment(0x86C2, "A >= 0: save (&00) or attribs (&01-&06)", inline=True)
comment(0x86C4, "A=&FF? Only &FF is valid for load", inline=True)
comment(0x86C8, "Unknown negative code: no-op return", inline=True)
comment(0x86D0, "Port &92 = PLDATA (data transfer port)", inline=True)
comment(0x86D2, "Overwrite URD field with data port number", inline=True)
comment(0x86D7, "Build FS header (V=1: CLV path)", inline=True)
comment(0x86DA, "Y=6: param block byte 6", inline=True)
comment(0x86DC, "Byte 6: use file's own load address?", inline=True)
comment(0x86DE, "Non-zero: use FS reply address (lodfil)", inline=True)
comment(0x86E0, "Zero: copy caller's load addr first", inline=True)
comment(0x86E3, "Then copy FS reply to param block", inline=True)
comment(0x86E6, "Carry clear from prepare_cmd_clv: skip lodfil", inline=True)
comment(0x86E8, "Copy FS reply addresses to param block", inline=True)
comment(0x86EB, "Then copy load addr from param block", inline=True)
label(0x86EE, "skip_lodfil")           # BCC: skip lodfil block, proceed to compute end addr
comment(0x86EE, "Compute end address = load + file length", inline=True)
label(0x86F0, "copy_load_end_addr")    # Copy 4 load-address bytes and compute end address
comment(0x86F0, "Load address byte", inline=True)
comment(0x86F2, "Store as current transfer position", inline=True)
comment(0x86F4, "Add file length byte", inline=True)
comment(0x86F7, "Store as end position", inline=True)
comment(0x86F9, "Next address byte", inline=True)
comment(0x86FA, "Decrement byte counter", inline=True)
comment(0x86FB, "Loop for all 4 address bytes", inline=True)
comment(0x86FD, "Adjust high byte for 3-byte length overflow", inline=True)
comment(0x86FE, "Subtract 4th length byte from end addr", inline=True)
comment(0x8701, "Store adjusted end address high byte", inline=True)
comment(0x8706, "Transfer file data in &80-byte blocks", inline=True)
comment(0x8709, "Copy 3-byte file length to FS reply cmd buffer", inline=True)
comment(0x870B, "Load file length byte", inline=True)
comment(0x870E, "Store in FS command data buffer", inline=True)
comment(0x8711, "Next byte (count down)", inline=True)
comment(0x8712, "Loop for 3 bytes (X=2,1,0)", inline=True)
comment(0x8714, "ALWAYS branch", inline=True)
comment(0x8719, "Addresses match: transfer complete", inline=True)
comment(0x871B, "Port &92 for data block transfer", inline=True)
comment(0x871D, "Store port to TXCB command byte", inline=True)
label(0x871F, "send_block_loop")       # Outer loop: set up and send each 128-byte block
comment(0x871F, "Set up next &80-byte block for transfer", inline=True)
label(0x8721, "copy_block_addrs")      # Inner loop: swap 4-byte current/end addresses
comment(0x8721, "Swap: current addr -> source, end -> current", inline=True)
comment(0x8723, "Source addr = current position", inline=True)
comment(0x8725, "Load end address byte", inline=True)
comment(0x8727, "Dest = end address (will be clamped)", inline=True)
comment(0x8729, "Next address byte", inline=True)
comment(0x872A, "Loop for all 4 bytes", inline=True)
comment(0x872C, "Command &7F = data block transfer", inline=True)
comment(0x872E, "Store to TXCB control byte", inline=True)
comment(0x8730, "Send this block to the fileserver", inline=True)
comment(0x8733, "Y=3: compare 4 bytes (3..0)", inline=True)
comment(0x8735, "Compare current vs end address (4 bytes)", inline=True)
comment(0x8738, "XOR with end address byte", inline=True)
comment(0x873B, "Not equal: more blocks to send", inline=True)
comment(0x873D, "Next byte", inline=True)
comment(0x873E, "Loop for all 4 address bytes", inline=True)
comment(0x8740, "All equal: transfer complete", inline=True)
comment(0x8741, "A=0: SAVE handler", inline=True)
comment(0x8743, "A!=0: attribute dispatch (A=1-6)", inline=True)
comment(0x8746, "Process 4 address bytes (load/exec/start/end)", inline=True)
comment(0x8748, "Y=&0E: start from end-address in param block", inline=True)
comment(0x874A, "Read end-address byte from param block", inline=True)
comment(0x874C, "Save to port workspace for transfer setup", inline=True)
comment(0x874F, "Y = Y-4: point to start-address byte", inline=True)
comment(0x8752, "end - start = transfer length byte", inline=True)
comment(0x8754, "Store length byte in FS command buffer", inline=True)
comment(0x8757, "Save length byte for param block restore", inline=True)
comment(0x8758, "Read corresponding start-address byte", inline=True)
comment(0x875A, "Save to port workspace", inline=True)
comment(0x875D, "Restore length byte from stack", inline=True)
comment(0x875E, "Replace param block entry with length", inline=True)
comment(0x8760, "Y = Y+5: advance to next address group", inline=True)
comment(0x8763, "Decrement address byte counter", inline=True)
comment(0x8764, "Loop for all 4 address bytes", inline=True)
comment(0x8766, "Copy load/exec addresses to FS command buffer", inline=True)
label(0x8768, "copy_save_params")      # Copy 9 bytes of load/exec address into FS command buffer
comment(0x8768, "Read load/exec address byte from params", inline=True)
comment(0x876A, "Copy to FS command buffer", inline=True)
comment(0x876D, "Next byte (descending)", inline=True)
comment(0x876E, "Loop for bytes 9..1", inline=True)
comment(0x8770, "Port &91 for save command", inline=True)
comment(0x8772, "Overwrite URD field with port number", inline=True)
comment(0x8775, "Save port &91 for flow control ACK", inline=True)
comment(0x8777, "Append filename at offset &0B in cmd buffer", inline=True)
comment(0x8779, "Append filename to cmd buffer at offset X", inline=True)
comment(0x877C, "Y=1: function code for save", inline=True)
label(0x8793, "skip_catalogue_msg")   # BEQ: messages flag=0, skip display
comment(0x8793, "Store reply command for attr decode", inline=True)
comment(0x8796, "Y=&0E: access byte offset in param block", inline=True)
comment(0x8798, "Load access byte from FS reply", inline=True)
comment(0x879B, "Convert FS access to BBC attribute format", inline=True)
comment(0x87A6, "Copied all 4 bytes? (Y=&0E..&11)", inline=True)
comment(0x87A8, "Loop for 4 attribute bytes", inline=True)
comment(0x87AA, "Restore A/X/Y and return to caller", inline=True)
comment(0x87AD, "Start at offset 5 (top of 4-byte addr)", inline=True)
comment(0x87AF, "Read from parameter block", inline=True)
comment(0x87B1, "Store to local workspace", inline=True)
comment(0x87B4, "Next byte (descending)", inline=True)
comment(0x87B5, "Copy offsets 5,4,3,2 (4 bytes)", inline=True)
comment(0x87B7, "Loop while Y >= 2", inline=True)
comment(0x87B9, "Return", inline=True)
comment(0x87BA, "Start at offset &0D (top of range)", inline=True)
comment(0x87BC, "First store uses X (attrib byte)", inline=True)
comment(0x87BD, "Write to parameter block", inline=True)
comment(0x87BF, "Read next byte from reply buffer", inline=True)
comment(0x87C3, "Copy offsets &0D down to 2", inline=True)
comment(0x87C8, "Save FS command byte on stack", inline=True)
comment(0x87CC, "Addresses equal: nothing to transfer", inline=True)
comment(0x87E0, "Store dest address byte", inline=True)
comment(0x87E2, "Advance current position", inline=True)
comment(0x87E4, "Next address byte", inline=True)
comment(0x87E5, "Decrement byte counter", inline=True)
comment(0x87E6, "Loop for all 4 bytes", inline=True)
comment(0x87EA, "SEC for SBC in overshoot check", inline=True)
comment(0x87EB, "Check if new pos overshot end addr", inline=True)
comment(0x87EE, "Subtract end address byte", inline=True)
comment(0x87F1, "Next byte", inline=True)
comment(0x87F2, "Decrement counter", inline=True)
comment(0x87F3, "Loop for 4-byte comparison", inline=True)
comment(0x87F5, "C=0: no overshoot, proceed", inline=True)
comment(0x87F7, "Overshot: clamp dest to end address", inline=True)
label(0x87F9, "clamp_dest_addr")       # Clamp dest addr when block overshoots transfer end
comment(0x87F9, "Load end address byte", inline=True)
comment(0x87FB, "Replace dest with end address", inline=True)
comment(0x87FD, "Next byte", inline=True)
comment(0x87FE, "Loop for all 4 bytes", inline=True)
label(0x8800, "send_block")           # BCC: no overshoot, skip clamp, send block
comment(0x8800, "Recover original FS command byte", inline=True)
comment(0x8801, "Re-push for next iteration", inline=True)
comment(0x8802, "Save processor flags (C from cmp)", inline=True)
comment(0x8803, "Store command byte in TXCB", inline=True)
comment(0x8805, "128-byte block size for data transfer", inline=True)
comment(0x8807, "Store size in TXCB control byte", inline=True)
comment(0x8809, "Point TX ptr to &00C0; transmit", inline=True)
comment(0x880C, "ACK port for flow control", inline=True)
comment(0x880E, "Set reply port for ACK receive", inline=True)
comment(0x8811, "Restore flags (C=overshoot status)", inline=True)
comment(0x8812, "C=1: all data sent (overshot), done", inline=True)
comment(0x8814, "Command &91 = data block transfer", inline=True)
comment(0x8816, "Store command &91 in TXCB", inline=True)
comment(0x881A, "Transmit block and wait (BRIANX)", inline=True)
comment(0x881D, "More blocks? Loop back", inline=True)
comment(0x881F, "Save A (function code)", inline=True)
comment(0x8822, "Convert handle to bitmask in A", inline=True)
comment(0x8825, "Y = handle bitmask from conversion", inline=True)
comment(0x8826, "Local hint: is EOF possible for this handle?", inline=True)
comment(0x8829, "X = result of AND (0 = not at EOF)", inline=True)
comment(0x882A, "Hint clear: definitely not at EOF", inline=True)
comment(0x882C, "Save bitmask for clear_fs_flag", inline=True)
comment(0x882D, "Handle byte in FS command buffer", inline=True)
comment(0x8830, "Y=&11: FS function code FCEOF", inline=True)
comment(0x8837, "Restore bitmask", inline=True)
comment(0x8838, "FS reply: non-zero = at EOF", inline=True)
comment(0x883B, "At EOF: skip flag clear", inline=True)
comment(0x883D, "Not at EOF: clear the hint bit", inline=True)
label(0x8840, "restore_ay_return")      # Restore A and Y registers, return
comment(0x8840, "Restore A", inline=True)
comment(0x8841, "Restore Y", inline=True)
comment(0x8843, "Return; X=0 (not EOF) or X=&FF (EOF)", inline=True)
comment(0x8844, "Store function code in FS cmd buffer", inline=True)
comment(0x8847, "A=6? (delete)", inline=True)
comment(0x8849, "Yes: jump to delete handler", inline=True)
comment(0x884B, "A>=7: unsupported, fall through to return", inline=True)
comment(0x884D, "A=5? (read catalogue info)", inline=True)
comment(0x884F, "Yes: jump to read info handler", inline=True)
comment(0x8851, "A=4? (write attributes only)", inline=True)
comment(0x8853, "Yes: jump to write attrs handler", inline=True)
comment(0x8855, "A=1? (write all catalogue info)", inline=True)
comment(0x8857, "Yes: jump to write-all handler", inline=True)
comment(0x8859, "A=2 or 3: convert to param block offset", inline=True)
comment(0x885A, "A*4: 2->8, 3->12", inline=True)
comment(0x885B, "Y = A*4", inline=True)
comment(0x885C, "Y = A*4 - 3 (load addr offset for A=2)", inline=True)
comment(0x885F, "X=3: copy 4 bytes", inline=True)
comment(0x8861, "Load address byte from param block", inline=True)
comment(0x8863, "Store to FS cmd data area", inline=True)
comment(0x8866, "Next source byte (descending)", inline=True)
comment(0x8867, "Next dest byte", inline=True)
comment(0x8868, "Loop for 4 bytes", inline=True)
comment(0x886A, "X=5: data extent for filename copy", inline=True)
comment(0x886E, "A=1: encode protection from param block", inline=True)
comment(0x8871, "Store encoded attrs at &0F0E", inline=True)
comment(0x8874, "Y=9: source offset in param block", inline=True)
comment(0x8876, "X=8: dest offset in cmd buffer", inline=True)
comment(0x8878, "Load byte from param block", inline=True)
comment(0x887A, "Store to FS cmd buffer", inline=True)
comment(0x887D, "Next source byte (descending)", inline=True)
comment(0x887E, "Next dest byte", inline=True)
comment(0x887F, "Loop until X=0 (8 bytes copied)", inline=True)
comment(0x8881, "X=&0A: data extent past attrs+addrs", inline=True)
comment(0x8883, "Append filename to cmd buffer", inline=True)
comment(0x8886, "Y=&13: fn code for FCSAVE (write attrs)", inline=True)
comment(0x8888, "ALWAYS branch to send command", inline=True)
comment(0x888A, "A=6: copy filename (delete)", inline=True)
comment(0x888D, "Y=&14: fn code for FCDEL (delete)", inline=True)
label(0x888F, "send_fs_cmd_v1")       # BNE: after copy_filename, BIT tx_ctrl_upper
comment(0x888F, "Set V=1 (BIT trick: &B3 has bit 6 set)", inline=True)
comment(0x8892, "Send via prepare_fs_cmd_v (V=1 path)", inline=True)
label(0x8895, "check_attrib_result")  # BCS: A>=7 unsupported, dispatch to error/return
comment(0x8895, "C=1: &D6 not-found, skip to return", inline=True)
comment(0x8897, "C=0: success, copy reply to param block", inline=True)
comment(0x8899, "A=4: encode attrs from param block", inline=True)
comment(0x889C, "Store encoded attrs at &0F06", inline=True)
comment(0x889F, "X=2: data extent (1 attr byte + fn)", inline=True)
comment(0x88A1, "ALWAYS branch to append filename", inline=True)
comment(0x88A3, "X=1: filename only, no data extent", inline=True)
comment(0x88A5, "Copy filename to cmd buffer", inline=True)
comment(0x88A8, "Y=&12: fn code for FCEXAM (read info)", inline=True)
comment(0x88AD, "Save object type from FS reply", inline=True)
comment(0x88B0, "Clear reply byte (X=0 on success)", inline=True)
comment(0x88B3, "Clear length high byte in reply", inline=True)
comment(0x88B6, "Decode 5-bit access byte from FS reply", inline=True)
comment(0x88BE, "Y=&0E: attrs offset in param block", inline=True)
comment(0x88C0, "Store decoded attrs at param block +&0E", inline=True)
comment(0x88C2, "Y=&0D: start copy below attrs", inline=True)
comment(0x88C3, "X=&0C: copy from reply offset &0C down", inline=True)
comment(0x88C5, "Load reply byte (load/exec/length)", inline=True)
comment(0x88C8, "Store to param block", inline=True)
comment(0x88CA, "Next dest byte (descending)", inline=True)
comment(0x88CB, "Next source byte", inline=True)
comment(0x88CC, "Loop until X=0 (12 bytes copied)", inline=True)
comment(0x88CE, "X=0 -> X=2 for length high copy", inline=True)
comment(0x88CF, "INX again: X=2", inline=True)
comment(0x88D0, "Y=&11: length high dest in param block", inline=True)
comment(0x88D2, "Load length high byte from reply", inline=True)
comment(0x88D5, "Store to param block", inline=True)
comment(0x88D7, "Next dest byte (descending)", inline=True)
comment(0x88D8, "Next source byte", inline=True)
comment(0x88D9, "Loop for 3 length-high bytes", inline=True)
label(0x88DF, "attrib_error_exit")    # BCS: not-found/error, BPL restore_xy_return
comment(0x88DF, "A>=0: branch to restore_args_return", inline=True)
comment(0x88E1, "Save A/X/Y registers for later restore", inline=True)
comment(0x88E4, "Function >= 3?", inline=True)
comment(0x88E6, "A>=3 (ensure/flush): no-op for NFS", inline=True)
comment(0x88E8, "Test file handle", inline=True)
comment(0x88EA, "Y=0: FS-level query, not per-file", inline=True)
comment(0x88EC, "Convert handle to bitmask", inline=True)
comment(0x88EF, "Store bitmask as first cmd data byte", inline=True)
comment(0x88F2, "LSR splits A: C=1 means write (A=1)", inline=True)
comment(0x88F3, "Store function code to cmd data byte 2", inline=True)
comment(0x88F6, "C=1: write path, copy ptr from caller", inline=True)
comment(0x88F8, "Y=&0C: FCRDSE (read sequential pointer)", inline=True)
comment(0x88FA, "X=2: 3 data bytes in command", inline=True)
comment(0x88FC, "Build and send FS command", inline=True)
comment(0x88FF, "Clear last-byte flag on success", inline=True)
comment(0x8901, "X = saved control block ptr low", inline=True)
comment(0x8903, "Y=2: copy 3 bytes of file pointer", inline=True)
comment(0x8905, "Zero high byte of 3-byte pointer", inline=True)
label(0x8907, "copy_fileptr_reply")    # Copy 3-byte file pointer from FS reply data
comment(0x8907, "Read reply byte from FS cmd data", inline=True)
comment(0x890A, "Store to caller's control block", inline=True)
comment(0x890C, "Next byte (descending)", inline=True)
comment(0x890D, "Next source byte", inline=True)
comment(0x890E, "Loop for all 3 bytes", inline=True)
label(0x8910, "argsv_check_return")    # Conditional return after ARGSV file pointer op
comment(0x8910, "C=0 (read): return to caller", inline=True)
comment(0x8912, "Save bitmask for set_fs_flag later", inline=True)
comment(0x8913, "Push bitmask", inline=True)
comment(0x8914, "Y=3: copy 4 bytes of file pointer", inline=True)
label(0x8916, "copy_fileptr_to_cmd")  # Copy 4-byte file pointer into FS command area
comment(0x8916, "Read caller's pointer byte", inline=True)
comment(0x8918, "Store to FS command data area", inline=True)
comment(0x891B, "Next source byte", inline=True)
comment(0x891C, "Next destination byte", inline=True)
comment(0x891D, "Loop for all 4 bytes", inline=True)
comment(0x891F, "Y=&0D: FCWRSE (write sequential pointer)", inline=True)
comment(0x8921, "X=5: 6 data bytes in command", inline=True)
comment(0x8923, "Build and send FS command", inline=True)
comment(0x8926, "Save not-found status from X", inline=True)
comment(0x8928, "Recover bitmask for EOF hint update", inline=True)
comment(0x8929, "Set EOF hint bit for this handle", inline=True)
comment(0x892C, "A = saved function code / command", inline=True)
label(0x892E, "restore_xy_return")     # Restore X and Y from workspace, return
comment(0x892E, "X = saved control block ptr low", inline=True)
comment(0x8930, "Y = saved control block ptr high", inline=True)
comment(0x8932, "Return to MOS with registers restored", inline=True)
label(0x893A, "halve_args_a")         # BEQ: A=2, LSR A then dispatch
comment(0x893A, "Shared: halve A (A=0 or A=2 paths)", inline=True)
comment(0x893B, "Return with A = FS number or 1", inline=True)
comment(0x893D, "Copy command context to caller's block", inline=True)
comment(0x8940, "Store to caller's parameter block", inline=True)
comment(0x8942, "Next byte (descending)", inline=True)
comment(0x8943, "Loop until all bytes copied", inline=True)
comment(0x8949, "Save A/X/Y and set up pointers", inline=True)
comment(0x894C, "SEC distinguishes open (A>0) from close", inline=True)
comment(0x8951, "A=0: close file(s)", inline=True)
comment(0x8953, "Valid open modes: &40, &80, &C0 only", inline=True)
comment(0x8955, "Invalid mode bits: return", inline=True)
comment(0x8957, "A = original mode byte", inline=True)
comment(0x8958, "Convert MOS mode to FS protocol flags", inline=True)
comment(0x895A, "ASL: shift mode bits left", inline=True)
comment(0x895B, "Flag 1: read/write direction", inline=True)
comment(0x895E, "ROL: Flag 2 into bit 0", inline=True)
comment(0x895F, "Flag 2: create vs existing file", inline=True)
comment(0x8962, "X=2: copy after 2-byte flags", inline=True)
comment(0x8964, "Copy filename to FS command buffer", inline=True)
comment(0x8967, "Y=6: FS function code FCOPEN", inline=True)
comment(0x8969, "Set V flag from l83b3 bit 6", inline=True)
comment(0x896C, "Build and send FS open command", inline=True)
comment(0x896F, "Error: restore and return", inline=True)
comment(0x8971, "Load reply handle from FS", inline=True)
comment(0x8974, "X = new file handle", inline=True)
comment(0x8975, "Set EOF hint + sequence bits", inline=True)
comment(0x8983, "ALWAYS branch to restore and return", inline=True)
comment(0x8985, "A = handle (Y preserved in A)", inline=True)
comment(0x8986, "Y>0: close single file", inline=True)
comment(0x8988, "Close SPOOL/EXEC before FS close-all", inline=True)
comment(0x898D, "Y=0: close all handles on server", inline=True)
comment(0x898F, "Handle byte in FS command buffer", inline=True)
comment(0x8999, "Reply handle for flag update", inline=True)
comment(0x899C, "Update EOF/sequence tracking bits", inline=True)
label(0x899F, "close_opt_return")      # Conditional return after close/opt handler
comment(0x899F, "C=0: restore A/X/Y and return", inline=True)
comment(0x89A1, "Is it *OPT 4,Y?", inline=True)
comment(0x89A3, "No: check for *OPT 1", inline=True)
comment(0x89A5, "Y must be 0-3 for boot option", inline=True)
comment(0x89A7, "Y < 4: valid boot option", inline=True)
label(0x89B1, "set_messages_flag")     # Set *OPT 1 local messages flag from Y
comment(0x89B1, "Set local messages flag (*OPT 1,Y)", inline=True)
comment(0x89B4, "Return via restore_args_return", inline=True)
comment(0x89B6, "Error index 7 (Bad option)", inline=True)
comment(0x89B8, "Generate BRK error", inline=True)
comment(0x89BB, "Boot option value in FS command", inline=True)
comment(0x89BE, "Y=&16: FS function code FCOPT", inline=True)
comment(0x89C3, "Restore Y from saved value", inline=True)
comment(0x89C5, "Cache boot option locally", inline=True)
label(0x89C8, "opt_return")           # BCC: *OPT 1 done, to close_opt_return
comment(0x89C8, "Return via restore_args_return", inline=True)
comment(0x89CA, "Y=9: adjust 9 address bytes", inline=True)
comment(0x89CC, "Adjust with carry clear", inline=True)
comment(0x89CF, "Y=1: adjust 1 address byte", inline=True)
comment(0x89D1, "C=0 for address adjustment", inline=True)
label(0x89D4, "adjust_addr_byte")      # Add or subtract one adjustment byte per iteration (4 total)
label(0x89E0, "subtract_adjust")      # BMI: fs_load_addr_2 negative, SBC instead of ADC
comment(0x89EA, "Save A/X/Y to FS workspace", inline=True)
comment(0x89ED, "X = call number for range check", inline=True)
comment(0x89EE, "A=0: invalid, restore and return", inline=True)
comment(0x89F0, "Convert to 0-based (A=0..7)", inline=True)
comment(0x89F1, "Range check: must be 0-7", inline=True)
comment(0x89F3, "In range: continue to handler", inline=True)
comment(0x89F5, "Out of range: restore args and return", inline=True)
comment(0x89F8, "Recover 0-based function code", inline=True)
comment(0x89F9, "Y=0: param block byte 0 (file handle)", inline=True)
comment(0x89FB, "Save function code on stack", inline=True)
comment(0x89FC, "A>=4: info queries, dispatch separately", inline=True)
comment(0x89FE, "A<4: file read/write operations", inline=True)
comment(0x8A00, "Dispatch to OSGBPB 5-8 info handler", inline=True)
comment(0x8A03, "Get file handle from param block byte 0", inline=True)
comment(0x8A05, "Convert handle to bitmask for EOF flags", inline=True)
comment(0x8A08, "Store handle in FS command data", inline=True)
comment(0x8A0B, "Y=&0B: start at param block byte 11", inline=True)
comment(0x8A0D, "X=6: copy 6 bytes of transfer params", inline=True)
comment(0x8A0F, "Load param block byte", inline=True)
comment(0x8A11, "Store to FS command buffer at &0F06+X", inline=True)
comment(0x8A14, "Previous param block byte", inline=True)
comment(0x8A15, "Skip param block offset 8 (the handle)", inline=True)
comment(0x8A17, "Not at handle offset: continue", inline=True)
comment(0x8A19, "Extra DEY to skip handle byte", inline=True)
comment(0x8A1A, "Decrement copy counter", inline=True)
comment(0x8A1B, "Loop for all 6 bytes", inline=True)
comment(0x8A1D, "Recover function code from stack", inline=True)
comment(0x8A1E, "LSR: odd=read (C=1), even=write (C=0)", inline=True)
comment(0x8A1F, "Save function code again (need C later)", inline=True)
comment(0x8A20, "Even (write): X stays 0", inline=True)
comment(0x8A22, "Odd (read): X=1", inline=True)
comment(0x8A23, "Store FS direction flag", inline=True)
comment(0x8A26, "Y=&0B: command data extent", inline=True)
comment(0x8A28, "Command &91=put, &92=get", inline=True)
comment(0x8A2A, "Recover function code", inline=True)
comment(0x8A2B, "Save again for later direction check", inline=True)
comment(0x8A2C, "Even (write): keep &91 and Y=&0B", inline=True)
comment(0x8A2E, "Odd (read): use &92 (get) instead", inline=True)
comment(0x8A30, "Read: one fewer data byte in command", inline=True)
label(0x8A31, "gbpb_write_path")      # BEQ: A=0 write, keeps X=&91/Y=&0B
comment(0x8A31, "Store port to FS command URD field", inline=True)
comment(0x8A34, "Save port for error recovery", inline=True)
comment(0x8A36, "X=8: command data bytes", inline=True)
comment(0x8A38, "Load handle from FS command data", inline=True)
comment(0x8A3B, "Build FS command with handle+flag", inline=True)
comment(0x8A3E, "Save seq# for byte-stream flow control", inline=True)
comment(0x8A40, "Store to FS sequence number workspace", inline=True)
comment(0x8A43, "X=4: copy 4 address bytes", inline=True)
comment(0x8A45, "Set up source/dest from param block", inline=True)
comment(0x8A47, "Store as source address", inline=True)
comment(0x8A4A, "Store as current transfer position", inline=True)
comment(0x8A4D, "Skip 4 bytes to reach transfer length", inline=True)
comment(0x8A50, "Dest = source + length", inline=True)
comment(0x8A52, "Store as end address", inline=True)
comment(0x8A55, "Back 3 to align for next iteration", inline=True)
comment(0x8A58, "Decrement byte counter", inline=True)
comment(0x8A59, "Loop for all 4 address bytes", inline=True)
comment(0x8A5B, "X=1 after loop", inline=True)
comment(0x8A5C, "Copy CSD data to command buffer", inline=True)
comment(0x8A5F, "Store at &0F06+X", inline=True)
comment(0x8A62, "Decrement counter", inline=True)
comment(0x8A63, "Loop for X=1,0", inline=True)
comment(0x8A65, "Odd (read): send data to FS first", inline=True)
comment(0x8A66, "Non-zero: skip write path", inline=True)
comment(0x8A68, "Load port for transfer setup", inline=True)
comment(0x8A6B, "Transfer data blocks to fileserver", inline=True)
label(0x8A77, "wait_fs_reply")        # BCS/fall: post-transfer, JSR send_fs_reply_cmd
comment(0x8A77, "Wait for FS reply command", inline=True)
comment(0x8A7A, "Load handle mask for EOF flag update", inline=True)
comment(0x8A7C, "Check FS reply: bit 7 = not at EOF", inline=True)
comment(0x8A7F, "Bit 7 set: not EOF, skip clear", inline=True)
comment(0x8A81, "At EOF: clear EOF hint for this handle", inline=True)
label(0x8A84, "skip_clear_flag")      # BMI: reply bit 7 set (not EOF), skip clear_fs_flag
comment(0x8A84, "Set EOF hint flag (may be at EOF)", inline=True)
comment(0x8A87, "Direction=0: forward adjustment", inline=True)
comment(0x8A89, "Adjust param block addrs by +9 bytes", inline=True)
comment(0x8A8C, "Direction=&FF: reverse adjustment", inline=True)
comment(0x8A8E, "SEC for reverse subtraction", inline=True)
comment(0x8A8F, "Adjust param block addrs (reverse)", inline=True)
comment(0x8A92, "Shift bit 7 into C for return flag", inline=True)
comment(0x8A95, "Return via restore_args path", inline=True)
label(0x8A98, "get_disc_title")        # Request disc title via FS function code &15
comment(0x8A98, "Y=&15: function code for disc title", inline=True)
comment(0x8A9A, "Build and send FS command", inline=True)
comment(0x8A9D, "Load boot option from FS workspace", inline=True)
comment(0x8AA0, "Store boot option in reply area", inline=True)
comment(0x8AA3, "X=0: reply data start offset", inline=True)
comment(0x8AA5, "Clear reply buffer high byte", inline=True)
comment(0x8AA7, "A=&12: 18 bytes of reply data", inline=True)
comment(0x8AA9, "Store as byte count for copy", inline=True)
comment(0x8AAB, "ALWAYS branch to copy_reply_to_caller", inline=True)
comment(0x8AAD, "Y=4: check param block byte 4", inline=True)
comment(0x8AAF, "Check if destination is in Tube space", inline=True)
comment(0x8AB2, "No Tube: skip Tube address check", inline=True)
comment(0x8AB4, "Compare Tube flag with addr byte 4", inline=True)
comment(0x8AB6, "Mismatch: not Tube space", inline=True)
comment(0x8AB9, "Y=3: subtract addr byte 3 from flag", inline=True)
label(0x8ABB, "store_tube_flag")      # BEQ/BNE: store Tube-transfer flag to l00a9
comment(0x8ABB, "Non-zero = Tube transfer required", inline=True)
comment(0x8ABD, "Copy param block bytes 1-4 to workspace", inline=True)
comment(0x8ABF, "Store to &BD+Y workspace area", inline=True)
comment(0x8AC2, "Previous byte", inline=True)
comment(0x8AC3, "Loop for bytes 3,2,1", inline=True)
comment(0x8AC5, "Sub-function: AND #3 of (original A - 4)", inline=True)
comment(0x8AC6, "Mask to 0-3 (OSGBPB 5-8 → 0-3)", inline=True)
comment(0x8AC8, "A=0 (OSGBPB 5): read disc title", inline=True)
comment(0x8ACA, "LSR: A=0 (OSGBPB 6) or A=1 (OSGBPB 7)", inline=True)
comment(0x8ACB, "A=0 (OSGBPB 6): read CSD/LIB name", inline=True)
comment(0x8ACD, "C=1 (OSGBPB 8): read filenames from dir", inline=True)
label(0x8ACF, "gbpb6_read_name")      # BEQ: A=0 OSGBPB 6, load CSD/LIB/URD handle
comment(0x8ACF, "Y=0 for CSD or carry for fn code select", inline=True)
comment(0x8AD0, "Get CSD/LIB/URD handles for FS command", inline=True)
comment(0x8AD3, "Store CSD handle in command buffer", inline=True)
comment(0x8AD6, "Load LIB handle from workspace", inline=True)
comment(0x8AD9, "Store LIB handle in command buffer", inline=True)
comment(0x8ADC, "Load URD handle from workspace", inline=True)
comment(0x8ADF, "Store URD handle in command buffer", inline=True)
comment(0x8AE2, "X=&12: buffer extent for command data", inline=True)
comment(0x8AE4, "Store X as function code in header", inline=True)
comment(0x8AE7, "&0D = 13 bytes of reply data expected", inline=True)
comment(0x8AE9, "Store reply length in command buffer", inline=True)
comment(0x8AEC, "Store as byte count for copy loop", inline=True)
comment(0x8AEE, "LSR: &0D >> 1 = 6", inline=True)
comment(0x8AEF, "Store as command data byte", inline=True)
comment(0x8AF2, "CLC for standard FS path", inline=True)
comment(0x8AF8, "INX: X=1 after build_send_fs_cmd", inline=True)
comment(0x8AF9, "Store X as reply start offset", inline=True)
comment(0x8AFB, "Copy FS reply to caller's buffer", inline=True)
comment(0x8AFD, "Non-zero: use Tube transfer path", inline=True)
comment(0x8AFF, "X = reply start offset", inline=True)
comment(0x8B01, "Y = reply buffer high byte", inline=True)
label(0x8B03, "copy_reply_bytes")     # Copy N bytes of FS reply data to caller buffer
comment(0x8B03, "Load reply data byte", inline=True)
comment(0x8B06, "Store to caller's buffer", inline=True)
comment(0x8B08, "Next source byte", inline=True)
comment(0x8B09, "Next destination byte", inline=True)
comment(0x8B0A, "Decrement remaining bytes", inline=True)
comment(0x8B0C, "Loop until all bytes copied", inline=True)
comment(0x8B0E, "ALWAYS branch to exit", inline=True)
label(0x8B10, "tube_transfer")        # BNE: l00a9 non-zero, claim Tube and send via R3
comment(0x8B10, "Claim Tube transfer channel", inline=True)
comment(0x8B13, "A=1: Tube claim type 1 (write)", inline=True)
comment(0x8B15, "X = param block address low", inline=True)
comment(0x8B17, "Y = param block address high", inline=True)
comment(0x8B19, "INX: advance past byte 0", inline=True)
comment(0x8B1A, "No page wrap: keep Y", inline=True)
comment(0x8B1C, "Page wrap: increment high byte", inline=True)
label(0x8B1D, "no_page_wrap")         # BNE: no page boundary crossed in copy
comment(0x8B1D, "Claim Tube address for transfer", inline=True)
comment(0x8B20, "X = reply data start offset", inline=True)
comment(0x8B22, "Load reply data byte", inline=True)
comment(0x8B25, "Send byte to Tube via R3", inline=True)
comment(0x8B28, "Next source byte", inline=True)
comment(0x8B29, "Decrement remaining bytes", inline=True)
comment(0x8B2B, "Loop until all bytes sent to Tube", inline=True)
comment(0x8B2D, "Release Tube after transfer complete", inline=True)
comment(0x8B2F, "Release Tube address claim", inline=True)
label(0x8B32, "gbpb_done")            # BEQ: copy/adjust done, JMP return_a_zero
comment(0x8B32, "Return via restore_args path", inline=True)
label(0x8B35, "gbpb8_read_dir")       # BCS: C=1 OSGBPB 8, read dir entries
comment(0x8B35, "OSGBPB 8: read filenames from dir", inline=True)
comment(0x8B37, "Byte 9: number of entries to read", inline=True)
comment(0x8B39, "Store as reply count in command buffer", inline=True)
comment(0x8B3C, "Y=5: byte 5 = starting entry number", inline=True)
comment(0x8B3E, "Load starting entry number", inline=True)
comment(0x8B40, "Store in command buffer", inline=True)
comment(0x8B43, "X=&0D: command data extent", inline=True)
comment(0x8B45, "Store extent in command buffer", inline=True)
comment(0x8B48, "Y=2: function code for dir read", inline=True)
comment(0x8B4A, "Store 2 as reply data start offset", inline=True)
comment(0x8B4C, "Store 2 as command data byte", inline=True)
comment(0x8B4F, "Y=3: function code for header read", inline=True)
comment(0x8B53, "X=0 after FS command completes", inline=True)
comment(0x8B55, "Load reply entry count", inline=True)
comment(0x8B58, "Store at param block byte 0 (X=0)", inline=True)
comment(0x8B5A, "Load entries-read count from reply", inline=True)
comment(0x8B5D, "Y=9: param block byte 9", inline=True)
comment(0x8B5F, "Add to starting entry number", inline=True)
comment(0x8B61, "Update param block with new position", inline=True)
comment(0x8B63, "Load total reply length", inline=True)
comment(0x8B65, "Subtract header (7 bytes) from reply len", inline=True)
comment(0x8B67, "Store adjusted length in command buffer", inline=True)
comment(0x8B6A, "Store as byte count for copy loop", inline=True)
comment(0x8B6C, "Zero bytes: skip copy", inline=True)
comment(0x8B6E, "Copy reply data to caller's buffer", inline=True)
label(0x8B71, "skip_copy_reply")      # BEQ: zero byte count, skip copy_reply_to_caller
comment(0x8B71, "X=2: clear 3 bytes", inline=True)
label(0x8B73, "zero_cmd_bytes")       # Zero 3 bytes of &0F07 area before address adjustment
comment(0x8B73, "Zero out &0F07+X area", inline=True)
comment(0x8B76, "Next byte", inline=True)
comment(0x8B77, "Loop for X=2,1,0", inline=True)
comment(0x8B79, "Adjust pointer by +1 (one filename read)", inline=True)
comment(0x8B7C, "SEC for reverse adjustment", inline=True)
comment(0x8B7D, "Reverse adjustment for updated counter", inline=True)
comment(0x8B7F, "Load entries-read count", inline=True)
comment(0x8B82, "Store in command buffer", inline=True)
comment(0x8B85, "Adjust param block addresses", inline=True)
comment(0x8B88, "Z=1: all done, exit", inline=True)
comment(0x8B8A, "A=&C3: Tube claim with retry", inline=True)
comment(0x8B8C, "Request Tube address claim", inline=True)
comment(0x8B8F, "C=0: claim failed, retry", inline=True)
comment(0x8B91, "Tube claimed successfully", inline=True)
comment(0x8B92, "Save A/X/Y and set up command ptr", inline=True)
comment(0x8B95, "X=&FF: table index (pre-incremented)", inline=True)
label(0x8B97, "scan_cmd_table")        # Outer command-table search loop for * command match
comment(0x8B97, "Y=&FF: input index (pre-incremented)", inline=True)
comment(0x8B99, "Advance input pointer", inline=True)
comment(0x8B9A, "Advance table pointer", inline=True)
comment(0x8B9B, "Load table character", inline=True)
comment(0x8B9E, "Bit 7: end of name, dispatch", inline=True)
comment(0x8BA0, "XOR input char with table char", inline=True)
comment(0x8BA2, "Case-insensitive (clear bit 5)", inline=True)
comment(0x8BA4, "Match: continue comparing", inline=True)
comment(0x8BA6, "Mismatch: back up table pointer", inline=True)
comment(0x8BA7, "Skip to end of table entry", inline=True)
comment(0x8BA8, "Load table byte", inline=True)
comment(0x8BAB, "Loop until bit 7 set (end marker)", inline=True)
comment(0x8BAD, "Check input for '.' abbreviation", inline=True)
comment(0x8BAF, "Skip past handler high byte", inline=True)
comment(0x8BB0, "Is input '.' (abbreviation)?", inline=True)
comment(0x8BB2, "No: try next table entry", inline=True)
comment(0x8BB4, "Yes: skip '.' in input", inline=True)
comment(0x8BB5, "Back to handler high byte", inline=True)
comment(0x8BB6, "ALWAYS branch; dispatch via BMI", inline=True)
label(0x8BB8, "dispatch_cmd")         # BMI: end-of-name marker, push handler addr/dispatch
comment(0x8BB8, "Push handler address high byte", inline=True)
comment(0x8BB9, "Load handler address low byte", inline=True)
comment(0x8BBC, "Push handler address low byte", inline=True)
comment(0x8C11, "X=1: copy dir name at cmd offset 1", inline=True)
comment(0x8C13, "Copy directory name to command buffer", inline=True)
comment(0x8C1B, "X=3: start printing from reply offset 3", inline=True)
comment(0x8C1D, "Print directory title (10 chars)", inline=True)
comment(0x8C20, "Print '('", inline=True)
comment(0x8C24, "Load station number from FS reply", inline=True)
comment(0x8C27, "Print station number as decimal", inline=True)
comment(0x8C2A, "Print ')     '", inline=True)
comment(0x8C36, "Non-zero: Public access", inline=True)
comment(0x8C38, "Print 'Owner' + CR", inline=True)
label(0x8C43, "print_public")          # BNE: access non-zero (public), print "Public"+CR
comment(0x8C43, "Print 'Public' + CR", inline=True)
comment(0x8C52, "X=1: past command code byte", inline=True)
comment(0x8C53, "Y=&10: print 16 characters", inline=True)
comment(0x8C55, "Print disc/CSD name from reply", inline=True)
comment(0x8C6A, "X = boot option for name table lookup", inline=True)
comment(0x8C6B, "Print boot option as hex digit", inline=True)
comment(0x8C6E, "Print ' ('", inline=True)
comment(0x8C7E, "Next character", inline=True)
comment(0x8C7F, "Continue printing option name", inline=True)
label(0x8C81, "done_option_name")      # BMI: bit 7 set, option name printing complete
comment(0x8C81, "Print ')' + CR + 'Dir. '", inline=True)
comment(0x8C9F, "Print library name", inline=True)
comment(0x8CAA, "Save start offset in zero page for loop", inline=True)
comment(0x8CBC, "Load column count for display format", inline=True)
comment(0x8CBE, "Store column count in command data", inline=True)
comment(0x8CC1, "X=3: copy directory name at offset 3", inline=True)
comment(0x8CC3, "Append directory name to examine command", inline=True)
label(0x8D1C, "jmp_restore_args")      # JMP restore_args_return (common FS reply exit)
comment(0x8D1C, "Restore A/X/Y and return to caller", inline=True)
comment(0x8D1F, "Set carry: LOGIN path (copy + boot)", inline=True)
comment(0x8D20, "Copy 4 bytes: boot option + 3 handles", inline=True)
comment(0x8D22, "SDISC: skip boot option, copy handles only", inline=True)
comment(0x8D24, "Load from FS reply (&0F05+X)", inline=True)
comment(0x8D27, "Store to handle workspace (&0E02+X)", inline=True)
comment(0x8D2A, "Next handle (descending)", inline=True)
comment(0x8D2B, "Loop while X >= 0", inline=True)
comment(0x8D2D, "SDISC: done, restore args and return", inline=True)
subroutine(0x8D2F, "boot_cmd_execute", hook=None,
    title="Execute boot command via OSCLI",
    description="""\
Reached from fsreply_1_copy_handles_boot when carry is set (LOGIN
path). Reads the boot option from fs_boot_option (&0E05),
looks up the OSCLI command string offset from boot_option_offsets+1,
and executes the boot command via JMP oscli with page &8D.""")
comment(0x8D2F, "Y = boot option from FS workspace", inline=True)
comment(0x8D32, "X = command string offset from table", inline=True)
comment(0x8D35, "Y = &8D (high byte of command address)", inline=True)
comment(0x8D37, "Execute boot command string via OSCLI", inline=True)
comment(0x8DC7, "A=0, C set = error indicator", inline=True)
comment(0x8DCB, "Look up handle &F0 in workspace", inline=True)
comment(0x8DCE, "Invalid handle: return 0", inline=True)
comment(0x8DD0, "Load stored handle value", inline=True)
comment(0x8DD2, "&3F = unused/closed slot marker", inline=True)
comment(0x8DD4, "Slot in use: return actual value", inline=True)
comment(0x8DD6, "Return 0 for closed/invalid handle", inline=True)
label(0x8DD8, "store_handle_return")   # Store handle result to &F0, return
comment(0x8DD8, "Store result back to &F0", inline=True)
comment(0x8DE1, "Look up handle &F0 in workspace", inline=True)
comment(0x8DE4, "Invalid handle: return 0", inline=True)
comment(0x8DFD, "Only OSWORDs &0F-&13 (index 0-4)", inline=True)
comment(0x8DFF, "Index >= 5: not ours, return", inline=True)
comment(0x8E02, "Load handler address high byte from table", inline=True)
comment(0x8E05, "Push high byte for RTS dispatch", inline=True)
comment(0x8E06, "Load handler address low byte from table", inline=True)
comment(0x8E09, "Dispatch table: low bytes for OSWORD &0F-&13 handlers", inline=True)
comment(0x8E0A, "Y=2: save 3 bytes (&AA-&AC)", inline=True)
comment(0x8E0C, "Load param block pointer byte", inline=True)
comment(0x8E0F, "Save to NFS workspace via (net_rx_ptr)", inline=True)
comment(0x8E11, "Next byte (descending)", inline=True)
comment(0x8E12, "Loop for all 3 bytes", inline=True)
comment(0x8E14, "Y=0 after BPL exit; INY makes Y=1", inline=True)
comment(0x8E15, "Read sub-function code from (&F0)+1", inline=True)
comment(0x8E38, "User TX CB in workspace page (high byte)", inline=True)
comment(0x8E3A, "Set param block high byte", inline=True)
comment(0x8E3C, "Set LTXCBP high byte for low-level TX", inline=True)
comment(0x8E3E, "&6F: offset into workspace for user TXCB", inline=True)
comment(0x8E40, "Set param block low byte", inline=True)
comment(0x8E42, "Set LTXCBP low byte for low-level TX", inline=True)
comment(0x8E44, "X=15: copy 16 bytes (OSWORD param block)", inline=True)
comment(0x8E46, "Copy param block to user TX control block", inline=True)
comment(0x8E53, "Set source high byte from workspace page", inline=True)
comment(0x8E55, "Store as copy source high byte in &BF", inline=True)
comment(0x8E57, "JSRSIZ at workspace offset &7F", inline=True)
comment(0x8E59, "Load buffer size from workspace", inline=True)
comment(0x8E5B, "Y=&80: start of JSR argument data", inline=True)
comment(0x8E5C, "Store &80 as copy source low byte", inline=True)
comment(0x8E5E, "X = buffer size (loop counter)", inline=True)
comment(0x8E5F, "X = size-1 (0-based count for copy)", inline=True)
comment(0x8E60, "Y=0: start of destination param block", inline=True)
comment(0x8E62, "Copy X+1 bytes from workspace to param", inline=True)
comment(0x8E6A, "Y=&7F: JSRSIZ offset (READRB entry)", inline=True)
comment(0x8E6C, "Load buffer size from workspace", inline=True)
comment(0x8E6E, "Y=1: param block offset for size byte", inline=True)
comment(0x8E70, "Store buffer size to (&F0)+1", inline=True)
comment(0x8E72, "Y=2: param block offset for args size", inline=True)
comment(0x8E73, "A=&80: argument data starts at offset &80", inline=True)
comment(0x8E75, "Store args start offset to (&F0)+2", inline=True)
comment(0x8E81, "Sub-function 4 or 5: read/set protection", inline=True)
comment(0x8E83, "LSR: 0->0, 1->0, 2->1, 3->1", inline=True)
comment(0x8E84, "X=&0D: default to static workspace page", inline=True)
comment(0x8E86, "Transfer LSR result to Y for indexing", inline=True)
comment(0x8E87, "Y=0 (sub 0-1): use page &0D", inline=True)
comment(0x8E89, "Y=1 (sub 2-3): use dynamic workspace", inline=True)
label(0x8E8B, "set_workspace_page")   # Sub-fn 0-1: use static page &0D, store to &AC
comment(0x8E8B, "Store workspace page in &BF (hi byte)", inline=True)
comment(0x8E8D, "Load offset: &FF (sub 0-1) or &01 (sub 2-3)", inline=True)
comment(0x8E90, "Store offset in &BE (lo byte)", inline=True)
comment(0x8E92, "X=1: copy 2 bytes", inline=True)
comment(0x8E94, "Y=1: start at param block offset 1", inline=True)
comment(0x8E9B, "LSR A: test bit 0 of sub-function", inline=True)
comment(0x8E9C, "Y=1: offset for protection byte", inline=True)
comment(0x8E9D, "Load protection byte from param block", inline=True)
comment(0x8E9F, "C=1 (odd sub): set protection", inline=True)
comment(0x8EA1, "C=0 (even sub): read current status", inline=True)
comment(0x8EA4, "Return current value to param block", inline=True)
comment(0x8EA6, "Update protection status", inline=True)
comment(0x8EA9, "Also save as JSR mask backup", inline=True)
comment(0x8EB7, "Sub-function 8: read local station number", inline=True)
comment(0x8EB9, "Match: read cached station ID from RX buffer", inline=True)
comment(0x8EBB, "Sub-function 9: read args size", inline=True)
comment(0x8EBD, "Match: read ARGS buffer info", inline=True)
comment(0x8EBF, "Sub >= 10 (bit 7 clear): read error", inline=True)
comment(0x8EC1, "Y=3: start from handle 3 (descending)", inline=True)
comment(0x8EC3, "LSR: test read/write bit", inline=True)
comment(0x8EC4, "C=0: read handles from workspace", inline=True)
comment(0x8EC6, "Init loop counter at Y=3", inline=True)
label(0x8EC8, "copy_handles_to_ws")   # Convert handles to bitmasks and store to workspace
comment(0x8EC8, "Reload loop counter", inline=True)
comment(0x8ECA, "Read handle from caller's param block", inline=True)
comment(0x8ECC, "Convert handle number to bitmask", inline=True)
comment(0x8ECF, "TYA: get bitmask result", inline=True)
comment(0x8ED0, "Reload loop counter", inline=True)
comment(0x8ED2, "Store bitmask to FS server table", inline=True)
comment(0x8ED5, "Next handle (descending)", inline=True)
comment(0x8ED7, "Loop for handles 3,2,1", inline=True)
comment(0x8EEB, "Next handle (descending)", inline=True)
comment(0x8EEC, "Loop for handles 3,2,1", inline=True)
comment(0x8EF0, "Workspace page high byte", inline=True)
comment(0x8EF2, "Set up pointer high byte in &AC", inline=True)
comment(0x8EF4, "Save param block high byte in &AB", inline=True)
comment(0x8EF6, "Disable user RX during CB operation", inline=True)
comment(0x8EF9, "Read first byte of param block", inline=True)
comment(0x8EFB, "Save: 0=open new, non-zero=read RXCB", inline=True)
comment(0x8EFD, "Non-zero: read specified RXCB", inline=True)
comment(0x8EFF, "Start scan from RXCB #3 (0-2 reserved)", inline=True)
comment(0x8F01, "Convert RXCB number to workspace offset", inline=True)
comment(0x8F04, "Invalid RXCB: return zero", inline=True)
comment(0x8F06, "LSR twice: byte offset / 4", inline=True)
comment(0x8F07, "Yields RXCB number from offset", inline=True)
comment(0x8F08, "X = RXCB number for iteration", inline=True)
comment(0x8F09, "Read flag byte from RXCB workspace", inline=True)
comment(0x8F0B, "Zero = end of CB list", inline=True)
comment(0x8F0D, "&3F = deleted slot, free for reuse", inline=True)
comment(0x8F0F, "Found free slot", inline=True)
comment(0x8F11, "Try next RXCB", inline=True)
comment(0x8F12, "A = next RXCB number", inline=True)
comment(0x8F13, "Continue scan (always branches)", inline=True)
comment(0x8F15, "A = free RXCB number", inline=True)
comment(0x8F16, "X=0 for indexed indirect store", inline=True)
comment(0x8F18, "Return RXCB number to caller's byte 0", inline=True)
label(0x8F1A, "read_rxcb")            # BNE: non-zero RXCB param, skip free-slot scan
comment(0x8F1A, "Convert RXCB number to workspace offset", inline=True)
comment(0x8F1D, "Invalid: write zero to param block", inline=True)
comment(0x8F1F, "Y = offset-1: points to flag byte", inline=True)
comment(0x8F20, "Set &AB = workspace ptr low byte", inline=True)
comment(0x8F22, "&C0: test mask for flag byte", inline=True)
comment(0x8F24, "Y=1: flag byte offset in RXCB", inline=True)
comment(0x8F26, "X=11: copy 12 bytes from RXCB", inline=True)
comment(0x8F28, "Compare Y(1) with saved byte (open/read)", inline=True)
comment(0x8F2A, "ADC flag: test if slot is in use", inline=True)
comment(0x8F2C, "Zero: slot open, do copy", inline=True)
comment(0x8F2E, "Negative: slot has received data", inline=True)
label(0x8F30, "copy_rxcb_to_param")   # Copy RXCB data from workspace to param block
comment(0x8F30, "C=0: workspace-to-param direction", inline=True)
comment(0x8F31, "Copy RXCB data to param block", inline=True)
comment(0x8F34, "Done: skip deletion on error", inline=True)
comment(0x8F36, "Mark CB as consumed (consume-once)", inline=True)
comment(0x8F38, "Y=1: flag byte offset", inline=True)
comment(0x8F3A, "Write &3F to mark slot deleted", inline=True)
comment(0x8F3C, "Branch to exit (always taken)", inline=True)
comment(0x8F3E, "Advance through multi-byte field", inline=True)
comment(0x8F40, "Loop until all bytes processed", inline=True)
comment(0x8F42, "Y=-1 → Y=0 after STA below", inline=True)
comment(0x8F43, "Return zero (no free RXCB found)", inline=True)
label(0x8F45, "reenable_rx")          # Common exit: ROL rx_flags, RTS
comment(0x8F45, "Re-enable user RX", inline=True)
comment(0x8F4C, "Y=2: copy 3 bytes (indices 2,1,0)", inline=True)
comment(0x8F59, "A = base address low byte", inline=True)
comment(0x8F5B, "A = base + 1 (skip length byte)", inline=True)
comment(0x8F5D, "Store 16-bit start addr at ws+&1C/&1D", inline=True)
comment(0x8F60, "Read data length from (&F0)+1", inline=True)
comment(0x8F62, "A = data length byte", inline=True)
comment(0x8F64, "Workspace offset &20 = RX data end", inline=True)
comment(0x8F66, "A = base + length = end address low", inline=True)
comment(0x8F68, "Store low byte of 16-bit address", inline=True)
comment(0x8F6A, "Advance to high byte offset", inline=True)
comment(0x8F6B, "A = high byte of base address", inline=True)
comment(0x8F6D, "Add carry for 16-bit addition", inline=True)
comment(0x8F6F, "Store high byte", inline=True)
comment(0x8F71, "Return", inline=True)
comment(0x8F74, "A >= 1: handle TX result", inline=True)
comment(0x8F76, "Y=&2F: start of template (descending)", inline=True)
comment(0x8F7B, "Non-zero = use ROM template byte as-is", inline=True)
comment(0x8F7D, "Zero = substitute from NMI workspace", inline=True)
label(0x8F80, "store_txcb_byte")      # BNE: non-zero template byte, skip substitution
comment(0x8F80, "Store to dynamic workspace", inline=True)
comment(0x8F82, "Descend through template", inline=True)
comment(0x8F83, "Stop at offset &17", inline=True)
comment(0x8F85, "Loop until all bytes copied", inline=True)
comment(0x8F87, "Y=&18: TX block starts here", inline=True)
comment(0x8F88, "Point net_tx_ptr at workspace+&18", inline=True)
comment(0x8F8A, "Set up RX buffer start/end pointers", inline=True)
comment(0x8F8D, "Y=2: port byte offset in RXCB", inline=True)
comment(0x8F8F, "A=&90: FS reply port", inline=True)
comment(0x8F91, "Store port &90 at (&F0)+2", inline=True)
label(0x8F95, "copy_fs_addr")          # Copy 3-byte FS station address into RX param block
comment(0x8F95, "Copy FS station addr from workspace", inline=True)
comment(0x8F98, "Store to RX param block", inline=True)
comment(0x8F9A, "Next byte", inline=True)
comment(0x8F9B, "Done 3 bytes (Y=4,5,6)?", inline=True)
comment(0x8F9D, "No: continue copying", inline=True)
comment(0x8F9F, "High byte of workspace for TX ptr", inline=True)
comment(0x8FA1, "Store as TX pointer high byte", inline=True)
comment(0x8FA4, "Transmit with full retry", inline=True)
comment(0x8FA7, "Y=&2C: RX end address offset", inline=True)
comment(0x8FA9, "Set RX end address to &FFFF (accept any length)", inline=True)
comment(0x8FAB, "Store end address low byte (&FF)", inline=True)
comment(0x8FAE, "Store end address high byte (&FF)", inline=True)
comment(0x8FB0, "Y=&25: port byte in workspace RXCB", inline=True)
comment(0x8FB2, "A=&90: FS reply port", inline=True)
comment(0x8FB4, "Store port to workspace RXCB", inline=True)
comment(0x8FB7, "A=&7F: flag byte = waiting for reply", inline=True)
comment(0x8FB9, "Store flag byte to workspace RXCB", inline=True)
label(0x8FC0, "handle_tx_result")     # BCS: A>=1, save flags and load RX result
comment(0x8FC0, "Save processor flags", inline=True)
comment(0x8FC1, "Y=1: first data byte offset", inline=True)
comment(0x8FC3, "Load first data byte from RX buffer", inline=True)
comment(0x8FC5, "X = first data byte (command code)", inline=True)
comment(0x8FC6, "Advance to next data byte", inline=True)
comment(0x8FC7, "Load station address high byte", inline=True)
comment(0x8FC9, "Advance past station addr", inline=True)
comment(0x8FCA, "Save Y as data index", inline=True)
comment(0x8FCC, "Store station addr hi at (net_rx_ptr)+&72", inline=True)
comment(0x8FCE, "Store to workspace", inline=True)
comment(0x8FD1, "A = command code (from X)", inline=True)
comment(0x8FD2, "Store station addr lo at (net_rx_ptr)+&71", inline=True)
comment(0x8FD4, "Restore flags from earlier PHP", inline=True)
comment(0x8FD5, "First call: adjust data length", inline=True)
label(0x8FD7, "send_data_bytes")       # Outer loop: fetch and TX successive data bytes
comment(0x8FD7, "Reload data index", inline=True)
comment(0x8FD9, "Advance data index for next iteration", inline=True)
comment(0x8FDB, "Load next data byte", inline=True)
comment(0x8FF1, "Not &0D: continue with next byte", inline=True)
comment(0x8FF5, "First-packet: set up control block", inline=True)
comment(0x8FF8, "Y=&7B: data length offset", inline=True)
comment(0x8FFA, "Load current data length", inline=True)
comment(0x8FFC, "Adjust data length by 3 for header bytes", inline=True)
comment(0x8FFE, "Store adjusted length", inline=True)
comment(0x9000, "Enable interrupts", inline=True)
comment(0x9004, "Transmit via tx_poll_ff", inline=True)
comment(0x9007, "Save processor status", inline=True)
comment(0x9008, "Save A (reason code)", inline=True)
comment(0x9009, "Save X", inline=True)
comment(0x900A, "Push X to stack", inline=True)
comment(0x900B, "Save Y", inline=True)
comment(0x900C, "Push Y to stack", inline=True)
comment(0x900D, "Get stack pointer for indexed access", inline=True)
comment(0x900E, "Retrieve original A (reason code) from stack", inline=True)
comment(0x9011, "Reason codes 0-8 only", inline=True)
comment(0x9013, "Code >= 9: skip dispatch, restore regs", inline=True)
comment(0x9015, "X = reason code for table lookup", inline=True)
comment(0x9016, "Dispatch to handler via trampoline", inline=True)
comment(0x9019, "Restore Y", inline=True)
comment(0x901A, "Transfer to Y register", inline=True)
comment(0x901B, "Restore X", inline=True)
comment(0x901C, "Transfer to X register", inline=True)
comment(0x901D, "Restore A", inline=True)
comment(0x901E, "Restore processor status flags", inline=True)
comment(0x901F, "Return with all registers preserved", inline=True)
comment(0x9023, "Push high byte of handler address", inline=True)
comment(0x9024, "Load handler low byte from table", inline=True)
comment(0x9027, "Push low byte of handler address", inline=True)
comment(0x9028, "Load workspace byte &EF for handler", inline=True)
comment(0x902A, "RTS dispatches to pushed handler", inline=True)
comment(0x9041, "ASL: restore P after ROR zeroed carry", inline=True)
comment(0x9044, "Y = character to write", inline=True)
comment(0x9045, "Store character at workspace offset &DA", inline=True)
comment(0x9047, "Store char at workspace offset &DA", inline=True)
comment(0x9049, "A=0: command type for net write char", inline=True)
comment(0x904B, "Y=&D9: command type offset", inline=True)
comment(0x904D, "Store command type at ws+&D9", inline=True)
comment(0x904F, "Mark TX control block as active (&80)", inline=True)
comment(0x9051, "Y=&0C: TXCB start offset", inline=True)
comment(0x9053, "Set TX active flag at ws+&0C", inline=True)
comment(0x9055, "Redirect net_tx_ptr low to workspace", inline=True)
comment(0x9057, "Load workspace page high byte", inline=True)
comment(0x9059, "Complete ptr redirect", inline=True)
comment(0x905B, "Transmit with full retry", inline=True)
comment(0x905E, "Mark TXCB as deleted (&3F) after transmit", inline=True)
comment(0x9060, "Write &3F to TXCB byte 0", inline=True)
comment(0x9062, "Return", inline=True)
comment(0x9063, "Load original Y (OSBYTE secondary param)", inline=True)
comment(0x9065, "OSBYTE &81 (INKEY): always forward to terminal", inline=True)
comment(0x9067, "Forward &81 to terminal for keyboard read", inline=True)
comment(0x9069, "Y=1: search NCTBPL table (execute on both)", inline=True)
comment(0x906B, "X=7: 8-entry NCTBPL table size", inline=True)
comment(0x906D, "Search for OSBYTE code in NCTBPL table", inline=True)
comment(0x9070, "Match found: dispatch with Y=1 (both)", inline=True)
comment(0x9072, "Y=-1: search NCTBMI table (terminal only)", inline=True)
comment(0x9073, "Second DEY: Y=&FF (from 1 via 0)", inline=True)
comment(0x9074, "X=&0E: 15-entry NCTBMI table size", inline=True)
comment(0x9076, "Search for OSBYTE code in NCTBMI table", inline=True)
comment(0x9079, "Match found: dispatch with Y=&FF (terminal)", inline=True)
comment(0x907B, "Y=0: OSBYTE not recognised, ignore", inline=True)
label(0x907C, "dispatch_remote_osbyte") # Common target for OSBYTE dispatch setup
comment(0x907C, "X=2 bytes to copy (default for RBYTE)", inline=True)
comment(0x907E, "A=Y: check table match result", inline=True)
comment(0x907F, "Y=0: not recognised, return unhandled", inline=True)
comment(0x9081, "Y>0 (NCTBPL): send only, no result expected", inline=True)
comment(0x9082, "Y>0 (NCTBPL): no result expected, skip RX", inline=True)
comment(0x9084, "Y<0 (NCTBMI): X=3 bytes (result + P flags)", inline=True)
comment(0x9085, "Y=&DC: top of 3-byte stack frame region", inline=True)
comment(0x9087, "Copy OSBYTE args from stack frame to workspace", inline=True)
comment(0x908A, "Store to NFS workspace for transmission", inline=True)
comment(0x908C, "Next byte (descending)", inline=True)
comment(0x908D, "Copied all 3 bytes? (&DC, &DB, &DA)", inline=True)
comment(0x908F, "Loop for remaining bytes", inline=True)
comment(0x9091, "A = byte count for setup_tx_and_send", inline=True)
comment(0x9092, "Build TXCB and transmit to terminal", inline=True)
comment(0x9095, "Restore N flag from table match type", inline=True)
comment(0x9096, "Y was positive (NCTBPL): done, no result", inline=True)
comment(0x9098, "Set up RX control block to wait for reply", inline=True)
comment(0x909E, "Bit7 clear: still waiting, poll again", inline=True)
comment(0x90A0, "X = stack pointer for register restoration", inline=True)
comment(0x90A1, "Y=&DD: saved P byte offset in workspace", inline=True)
comment(0x90A3, "Load remote processor status from reply", inline=True)
comment(0x90A5, "Force V=1 (claimed) and I=1 (no IRQ) in saved P", inline=True)
comment(0x90A7, "ALWAYS branch (ORA #&44 never zero)", inline=True)
comment(0x90A9, "Previous workspace offset", inline=True)
comment(0x90AA, "Previous stack register slot", inline=True)
comment(0x90AB, "Load next result byte (X, then Y)", inline=True)
comment(0x90AD, "Write result bytes to stacked registers", inline=True)
comment(0x90B0, "Copied all result bytes? (P at &DA)", inline=True)
comment(0x90B2, "Loop for remaining result bytes", inline=True)
comment(0x90B4, "Return to OSBYTE dispatcher", inline=True)
comment(0x90B5, "Compare OSBYTE code with table entry", inline=True)
comment(0x90B8, "Match found: return with Z=1", inline=True)
comment(0x90BA, "Next table entry (descending)", inline=True)
comment(0x90BB, "Loop for remaining entries", inline=True)
comment(0x90BD, "Return; Z=1 if match, Z=0 if not", inline=True)
label(0x90BE, "remote_osbyte_table") # OSBYTE codes accepted for remote execution
for addr in range(0x90BE, 0x90CD):
    byte(addr)
comment(0x90BE, "OSBYTE &04: cursor key status", inline=True)
comment(0x90BF, "OSBYTE &09: flash duration (1st colour)", inline=True)
comment(0x90C0, "OSBYTE &0A: flash duration (2nd colour)", inline=True)
comment(0x90C1, "OSBYTE &14: explode soft character RAM", inline=True)
comment(0x90C2, "OSBYTE &9A: video ULA control register", inline=True)
comment(0x90C3, "OSBYTE &9B: video ULA palette", inline=True)
comment(0x90C4, "OSBYTE &9C: ACIA control register", inline=True)
comment(0x90C5, "OSBYTE &E2: function key &D0-&DF", inline=True)
comment(0x90C6, "OSBYTE &0B: auto-repeat delay", inline=True)
comment(0x90C7, "OSBYTE &0C: auto-repeat rate", inline=True)
comment(0x90C8, "OSBYTE &0F: flush buffer class", inline=True)
comment(0x90C9, "OSBYTE &79: keyboard scan from X", inline=True)
comment(0x90CA, "OSBYTE &7A: keyboard scan from &10", inline=True)
comment(0x90CB, "OSBYTE &E3: function key &E0-&EF", inline=True)
comment(0x90CC, "OSBYTE &E4: function key &F0-&FF", inline=True)
comment(0x90D1, "OSWORD 7 (sound): handle via common path", inline=True)
comment(0x90D3, "OSWORD 8 = define an envelope", inline=True)
comment(0x90D5, "Not OSWORD 7 or 8: ignore (BNE exits)", inline=True)
label(0x90D7, "copy_params_rword")     # Copy param bytes and tag as RWORD message
comment(0x90D7, "Point workspace to offset &DB for params", inline=True)
comment(0x90D9, "Store workspace ptr offset &DB", inline=True)
label(0x90DB, "copy_osword_params")    # Copy OSWORD parameter bytes from RX buffer to workspace
comment(0x90DB, "Load param byte from OSWORD param block", inline=True)
comment(0x90DD, "Write param byte to workspace", inline=True)
comment(0x90DF, "Next byte (descending)", inline=True)
comment(0x90E0, "Loop for all parameter bytes", inline=True)
comment(0x90E2, "Y=0 after loop", inline=True)
comment(0x90E3, "Point workspace to offset &DA", inline=True)
comment(0x90E5, "Load original OSWORD code", inline=True)
comment(0x90E7, "Store OSWORD code at ws+0", inline=True)
comment(0x90E9, "Reset workspace ptr to base", inline=True)
comment(0x90EB, "Y=&14: command type offset", inline=True)
comment(0x90ED, "Tag as RWORD (port &E9)", inline=True)
comment(0x90EF, "Store port tag at ws+&14", inline=True)
comment(0x90F1, "A=1: single-byte TX", inline=True)
comment(0x90F3, "Transmit via workspace TXCB", inline=True)
comment(0x90F6, "Restore workspace ptr", inline=True)
comment(0x9159, "X=&0D: template offset for alt entry", inline=True)
comment(0x915B, "Y=&7C: target workspace offset for alt entry", inline=True)
comment(0x915D, "BIT test: V flag = bit 6 of &833A", inline=True)
comment(0x9160, "V=1: store to (net_rx_ptr) instead", inline=True)
comment(0x9162, "Y=&17: workspace target offset (main entry)", inline=True)
comment(0x9164, "X=&1A: template table index (main entry)", inline=True)
comment(0x9166, "V=0: target is (nfs_workspace)", inline=True)
comment(0x916A, "&FE = stop sentinel", inline=True)
comment(0x916C, "End of template: jump to exit", inline=True)
comment(0x916E, "&FD = skip sentinel", inline=True)
comment(0x9170, "Skip: don't store, just decrement Y", inline=True)
comment(0x9172, "&FC = page byte sentinel", inline=True)
comment(0x9174, "Not sentinel: store template value directly", inline=True)
comment(0x917C, "PAGE byte → Y=&02 / Y=&74", inline=True)
comment(0x917E, "→ Y=&04 / Y=&76", inline=True)
comment(0x9180, "PAGE byte → Y=&06 / Y=&78", inline=True)
comment(0x9182, "→ Y=&08 / Y=&7A", inline=True)
comment(0x9184, "Alt-path only → Y=&70", inline=True)
label(0x9186, "cb_template_main_start") # Control block template: main-path section
comment(0x9186, "→ Y=&0C (main only)", inline=True)
comment(0x9187, "→ Y=&0D (main only)", inline=True)
label(0x918A, "cb_template_tail")    # Control block template: tail section
comment(0x918A, "→ Y=&10 (main only)", inline=True)
comment(0x918D, "→ Y=&07 / Y=&79", inline=True)
comment(0x91B7, "X-1: convert 1-based buffer to 0-based", inline=True)
comment(0x91B8, "Is this the network printer buffer?", inline=True)
comment(0x91BA, "No: skip printer init", inline=True)
comment(0x91BC, "&1F = initial buffer pointer offset", inline=True)
comment(0x91BE, "Reset printer buffer write position", inline=True)
comment(0x91C1, "&41 = initial PFLAGS (bit 6 set, bit 0 set)", inline=True)
comment(0x91C6, "Return", inline=True)
comment(0x91C7, "Only handle buffer 4 (network printer)", inline=True)
comment(0x91C9, "Not buffer 4: ignore", inline=True)
comment(0x91CB, "A = reason code", inline=True)
comment(0x91CC, "Reason 1? (DEX: 1->0)", inline=True)
comment(0x91CD, "Not reason 1: handle Ctrl-B/C", inline=True)
comment(0x91CF, "Get stack pointer for P register", inline=True)
comment(0x91D0, "Force I flag in stacked P to block IRQs", inline=True)
comment(0x91D3, "Write back modified P register", inline=True)
comment(0x91D6, "OSBYTE &91: extract char from MOS buffer", inline=True)
comment(0x91D8, "X=3: printer buffer number", inline=True)
comment(0x91DD, "Buffer empty: return", inline=True)
comment(0x91DF, "Y = extracted character", inline=True)
comment(0x91E0, "Store char in output buffer", inline=True)
comment(0x91E3, "Buffer nearly full? (&6E = threshold)", inline=True)
comment(0x91E5, "Not full: get next char", inline=True)
comment(0x91E7, "Buffer full: flush to network", inline=True)
comment(0x91EC, "Load current buffer offset", inline=True)
comment(0x91EF, "Store byte at current position", inline=True)
comment(0x91F1, "Advance buffer pointer", inline=True)
comment(0x91F4, "Return; Y = buffer offset", inline=True)
label(0x91F5, "toggle_print_flag")    # Toggle print-active flag and update PFLAGS
comment(0x91F5, "Save reason code", inline=True)
comment(0x9216, "Return", inline=True)
comment(0x9217, "Store buffer length at workspace offset &08", inline=True)
comment(0x9219, "Current buffer fill position", inline=True)
comment(0x921C, "Write to workspace offset &08", inline=True)
comment(0x921E, "Store page high byte at offset &09", inline=True)
comment(0x9220, "Y=&09", inline=True)
comment(0x9221, "Write page high byte at offset &09", inline=True)
comment(0x9223, "Also store at offset &05", inline=True)
comment(0x9225, "(end address high byte)", inline=True)
comment(0x9227, "Y=&0B: flag byte offset", inline=True)
comment(0x9229, "X=&26: start from template entry &26", inline=True)
comment(0x922B, "Reuse ctrl_block_setup with CLV entry", inline=True)
comment(0x922E, "Y=&0A: sequence flag byte offset", inline=True)
comment(0x923A, "Old sequence bit into bit 0", inline=True)
comment(0x923B, "Store sequence flag at offset &0A", inline=True)
comment(0x923D, "Y=&1F: buffer start offset", inline=True)
comment(0x923F, "Reset printer buffer to start (&1F)", inline=True)
comment(0x9242, "A=0: printer output flag", inline=True)
comment(0x9244, "X=0: workspace low byte", inline=True)
comment(0x9245, "Y = workspace page high byte", inline=True)
comment(0x9247, "Enable interrupts before TX", inline=True)
comment(0x9248, "Set TX control block ptr low byte", inline=True)
comment(0x924A, "Set TX control block ptr high byte", inline=True)
comment(0x924C, "Save A (handle bitmask) for later", inline=True)
comment(0x924D, "Compute sequence bit from handle", inline=True)
comment(0x9250, "Zero: no sequence bit set", inline=True)
comment(0x9252, "Non-zero: normalise to bit 0", inline=True)
comment(0x9254, "Y=0: flag byte offset in TXCB", inline=True)
comment(0x9256, "Merge sequence into existing flag byte", inline=True)
comment(0x9258, "Save merged flag byte", inline=True)
comment(0x9259, "Write flag+sequence to TXCB byte 0", inline=True)
comment(0x925B, "Transmit with full retry", inline=True)
comment(0x925E, "End address &FFFF = unlimited data length", inline=True)
comment(0x9260, "Y=8: end address low offset in TXCB", inline=True)
comment(0x9262, "Store &FF to end addr low", inline=True)
comment(0x9265, "Store &FF to end addr high (Y=9)", inline=True)
comment(0x9267, "Recover merged flag byte", inline=True)
comment(0x9268, "Save in X for sequence compare", inline=True)
comment(0x9269, "Y=&D1: printer port number", inline=True)
comment(0x926B, "Recover saved handle bitmask", inline=True)
comment(0x926C, "Re-save for later consumption", inline=True)
comment(0x926D, "A=0: port &D1 (print); A!=0: port &90 (FS)", inline=True)
comment(0x926F, "Y=&90: FS data port", inline=True)
comment(0x9271, "A = selected port number", inline=True)
comment(0x9272, "Y=1: port byte offset in TXCB", inline=True)
comment(0x9274, "Write port to TXCB byte 1", inline=True)
comment(0x9276, "A = saved flag byte (expected sequence)", inline=True)
comment(0x9278, "Push expected sequence for retry loop", inline=True)
comment(0x9279, "Flag byte &7F = waiting for reply", inline=True)
comment(0x927B, "Write to TXCB flag byte (Y=0)", inline=True)
comment(0x927D, "Transmit and wait for reply (BRIANX)", inline=True)
comment(0x9280, "Recover expected sequence", inline=True)
comment(0x9281, "Keep on stack for next iteration", inline=True)
comment(0x9282, "Check if TX result matches expected sequence", inline=True)
comment(0x9284, "Bit 0 to carry (sequence mismatch?)", inline=True)
comment(0x9285, "C=1: mismatch, retry transmit", inline=True)
comment(0x9287, "Clean up: discard expected sequence", inline=True)
comment(0x9288, "Discard saved handle bitmask", inline=True)
comment(0x928D, "Toggle sequence bit on success", inline=True)
comment(0x9290, "Return", inline=True)
comment(0x9291, "Save current table index", inline=True)
comment(0x9293, "Push for later restore", inline=True)
comment(0x9294, "Point workspace to palette save area (&E9)", inline=True)
comment(0x9296, "Set workspace low byte", inline=True)
comment(0x9298, "Y=0: first palette entry", inline=True)
comment(0x929A, "Clear table index counter", inline=True)
comment(0x929C, "Save current screen MODE to workspace", inline=True)
comment(0x929F, "Store MODE at workspace[0]", inline=True)
comment(0x92A1, "Advance workspace pointer past MODE byte", inline=True)
comment(0x92A3, "Read colour count (from &0351)", inline=True)
comment(0x92A6, "Push for iteration count tracking", inline=True)
comment(0x92A7, "A=0: logical colour number for OSWORD", inline=True)
label(0x92A8, "save_palette_entry")    # Per-entry OSWORD &0B palette read and workspace store
comment(0x92A8, "Store logical colour at workspace[0]", inline=True)
comment(0x92AA, "X = workspace ptr low (param block addr)", inline=True)
comment(0x92AC, "Y = workspace ptr high", inline=True)
comment(0x92AE, "OSWORD &0B: read palette for logical colour", inline=True)
comment(0x92B3, "Recover colour count", inline=True)
comment(0x92B4, "Y=0: access workspace[0]", inline=True)
comment(0x92B6, "Write colour count back to workspace[0]", inline=True)
comment(0x92B8, "Y=1: access workspace[1] (palette result)", inline=True)
comment(0x92B9, "Read palette value returned by OSWORD", inline=True)
comment(0x92BB, "Push palette value for next iteration", inline=True)
comment(0x92BC, "X = current workspace ptr low", inline=True)
comment(0x92BE, "Advance workspace pointer", inline=True)
comment(0x92C0, "Increment table index", inline=True)
comment(0x92C2, "Y=0 for next store", inline=True)
comment(0x92C3, "Load table index as logical colour", inline=True)
comment(0x92C5, "Loop until workspace wraps past &F9", inline=True)
comment(0x92C7, "Continue for all 16 palette entries", inline=True)
comment(0x92C9, "Discard last palette value from stack", inline=True)
comment(0x92CA, "Reset table index to 0", inline=True)
comment(0x92CC, "Advance workspace past palette data", inline=True)
comment(0x92CE, "Save cursor pos and OSBYTE state values", inline=True)
comment(0x92D1, "Advance workspace past VDU state data", inline=True)
comment(0x92D3, "Recover saved table index", inline=True)
comment(0x92D4, "Restore table index", inline=True)
comment(0x92D6, "Restore LSTAT from saved OLDJSR value", inline=True)
comment(0x92D9, "Write to protection status", inline=True)
comment(0x92DC, "Return", inline=True)
comment(0x92DD, "Read cursor editing state", inline=True)
comment(0x92E0, "Store to workspace[Y]", inline=True)
comment(0x92E2, "Preserve in X for OSBYTE", inline=True)
comment(0x92E3, "OSBYTE &85: read cursor position", inline=True)
comment(0x92E6, "Advance workspace pointer", inline=True)
comment(0x92E8, "Y result from OSBYTE &85", inline=True)
comment(0x92E9, "Store Y pos to workspace (X=0)", inline=True)
comment(0x92EB, "Self-call trick: executes twice", inline=True)
comment(0x92EE, "X=0 for (zp,X) addressing", inline=True)
comment(0x92F0, "Index into OSBYTE number table", inline=True)
comment(0x92F2, "Next table entry next time", inline=True)
comment(0x92F4, "Advance workspace pointer", inline=True)
comment(0x92F6, "Read OSBYTE number from table", inline=True)
comment(0x92F9, "Y=&FF: read current value", inline=True)
comment(0x92FB, "Call OSBYTE", inline=True)
comment(0x92FE, "Result in X to A", inline=True)
comment(0x92FF, "X=0 for indexed indirect store", inline=True)
comment(0x9301, "Store result to workspace", inline=True)
label(0x9307, "reloc_zp_src")        # ROM source of zero-page relocated code
label(0x934C, "reloc_p4_src")        # ROM source of Tube host page 4 code
comment(0x966F, "INTOFF: read station ID, disable NMIs", inline=True)
comment(0x9672, "Full ADLC hardware reset", inline=True)
comment(0x9675, "OSBYTE &EA: check Tube co-processor", inline=True)
comment(0x9677, "X=0 for OSBYTE", inline=True)
comment(0x9679, "Y=&FF for OSBYTE", inline=True)
comment(0x968B, "Mark Econet as initialised", inline=True)
comment(0x968E, "Read station ID (&FE18 = INTOFF side effect)", inline=True)
comment(0x9691, "Store our station ID in TX scout", inline=True)
comment(0x96F5, "Return", inline=True)
label(0x970E, "accept_frame")         # Station ID matched, install next NMI handler
label(0x972B, "accept_local_net")     # Network=0: clear broadcast marker
comment(0x972B, "Network = 0 (local): clear tx_flags", inline=True)
label(0x972E, "accept_scout_net")     # Common accept for local/broadcast frames
comment(0x9773, "Write CR1", inline=True)
comment(0x9778, "Write CR2", inline=True)
comment(0x978C, "Write CR1: switch to TX mode", inline=True)
comment(0x9797, "Port = 0 -- immediate operation handler", inline=True)
comment(0x979A, "Check if broadcast (bit6 of tx_flags)", inline=True)
comment(0x979D, "Not broadcast -- skip CR2 setup", inline=True)
comment(0x979F, "CR2=&07: broadcast prep", inline=True)
comment(0x97A1, "Write CR2: broadcast frame prep", inline=True)
label(0x97A4, "scan_port_list")        # Non-broadcast: skip CR2 setup, begin port scan
comment(0x97A4, "Check if RX port list active (bit7)", inline=True)
comment(0x97A7, "No active ports -- try NFS workspace", inline=True)
comment(0x97A9, "Start scanning port list at page &C0", inline=True)
label(0x97B1, "check_port_slot")      # Loop: read port control byte, zero=end
comment(0x97B1, "Y=0: read control byte from start of slot", inline=True)
comment(0x97B3, "Read port control byte from slot", inline=True)
comment(0x97B5, "Zero = end of port list, no match", inline=True)
comment(0x97B7, "&7F = any-port wildcard", inline=True)
comment(0x97B9, "Not wildcard -- check specific port match", inline=True)
comment(0x97BC, "Read port number from slot (offset 1)", inline=True)
comment(0x97BE, "Zero port in slot = match any port", inline=True)
comment(0x97C0, "Check if port matches this slot", inline=True)
comment(0x97C3, "Port mismatch -- try next slot", inline=True)
label(0x97C5, "check_station_filter") # Port matched: advance to station filter check
comment(0x97C5, "Y=2: advance to station byte", inline=True)
comment(0x97C6, "Read station filter from slot (offset 2)", inline=True)
comment(0x97C8, "Zero station = match any station, accept", inline=True)
comment(0x97CA, "Check if source station matches", inline=True)
comment(0x97CD, "Station mismatch -- try next slot", inline=True)
comment(0x97CF, "Y=3: advance to network byte", inline=True)
comment(0x97D0, "Read network filter from slot (offset 3)", inline=True)
comment(0x97D2, "Check if source network matches", inline=True)
comment(0x97D5, "Network matches or zero = accept", inline=True)
label(0x97D7, "next_port_slot")        # Mismatch: advance pointer by 12 for next slot
comment(0x97D7, "Check if NFS workspace search pending", inline=True)
comment(0x9819, "Broadcast: different completion path", inline=True)
label(0x981C, "send_data_rx_ack")     # Non-broadcast: set up CR1/CR2 for TX ACK
comment(0x981C, "CR1=&44: RX_RESET | TIE", inline=True)
comment(0x981E, "Write CR1: TX mode for ACK", inline=True)
comment(0x9821, "CR2=&A7: RTS | CLR_TX_ST | FC_TDRA | PSE", inline=True)
comment(0x9823, "Write CR2: enable TX with PSE", inline=True)
comment(0x9826, "Install data_rx_setup at &97DC", inline=True)
comment(0x9828, "High byte of data_rx_setup handler", inline=True)
comment(0x982A, "Send ACK with data_rx_setup as next NMI", inline=True)
comment(0x982F, "Write CR1: switch to RX for data frame", inline=True)
comment(0x9832, "Install nmi_data_rx at &9839", inline=True)
comment(0x9836, "Install nmi_data_rx and return from NMI", inline=True)
comment(0x9839, "A=&01: mask for AP (Address Present)", inline=True)
comment(0x983B, "BIT SR2: test AP bit", inline=True)
comment(0x983E, "No AP: wrong frame or error", inline=True)
comment(0x9840, "Read first byte (dest station)", inline=True)
comment(0x9843, "Compare to our station ID (INTOFF)", inline=True)
comment(0x9846, "Not for us: error path", inline=True)
comment(0x9848, "Install net check handler at &984F", inline=True)
comment(0x984C, "Set NMI vector via RAM shim", inline=True)
comment(0x9852, "SR2 bit7 clear: no data ready -- error", inline=True)
comment(0x9854, "Read dest network byte", inline=True)
comment(0x9857, "Network != 0: wrong network -- error", inline=True)
comment(0x9859, "Install skip handler at &9865", inline=True)
comment(0x985B, "High byte of &9865 handler", inline=True)
comment(0x985D, "SR1 bit7: IRQ, data already waiting", inline=True)
comment(0x9860, "Data ready: skip directly, no RTI", inline=True)
comment(0x9862, "Install handler and return via RTI", inline=True)
comment(0x9868, "SR2 bit7 clear: error", inline=True)
comment(0x9870, "A=2: Tube transfer flag mask", inline=True)
comment(0x9872, "Check if Tube transfer active", inline=True)
comment(0x9875, "Tube active: use Tube RX path", inline=True)
comment(0x9877, "Install bulk read at &9843", inline=True)
comment(0x9879, "High byte of &9843 handler", inline=True)
comment(0x987B, "SR1 bit7: more data already waiting?", inline=True)
comment(0x987E, "Yes: enter bulk read directly", inline=True)
comment(0x9880, "No: install handler and RTI", inline=True)
label(0x9883, "install_tube_rx")      # BNE: Tube active, install Tube RX handler
comment(0x9883, "Tube: install Tube RX at &98F7", inline=True)
comment(0x9885, "High byte of &98F7 handler", inline=True)
comment(0x9887, "Install Tube handler and RTI", inline=True)
subroutine(0x988A, "nmi_error_dispatch", hook=None,
    title="NMI error handler dispatch",
    description="""\
Common error/abort entry used by 12 call sites. Checks
tx_flags bit 7: if clear, does a full ADLC reset and returns
to idle listen (RX error path); if set, jumps to tx_result_fail
(TX not-listening path).""")
comment(0x988A, "Check tx_flags for error path", inline=True)
comment(0x988D, "Bit7 clear: RX error path", inline=True)
comment(0x9891, "Bit7 set: TX result = not listening", inline=True)
comment(0x9894, "Full ADLC reset on RX error", inline=True)
comment(0x9897, "Discard and return to idle listen", inline=True)
label(0x989F, "data_rx_loop")          # Loop: check SR2, if RDA continue reading byte pairs
comment(0x989F, "SR2 bit7 clear: frame complete (FV)", inline=True)
comment(0x98A1, "Read first byte of pair from RX FIFO", inline=True)
comment(0x98A4, "Store byte to buffer", inline=True)
comment(0x98A6, "Advance buffer offset", inline=True)
comment(0x98A7, "Y != 0: no page boundary crossing", inline=True)
comment(0x98A9, "Crossed page: increment buffer high byte", inline=True)
comment(0x98AB, "Decrement remaining page count", inline=True)
comment(0x98AD, "No pages left: handle as complete", inline=True)
label(0x98AF, "read_sr2_between_pairs") # After page boundary, read SR2 before second byte
comment(0x98AF, "Read SR2 between byte pairs", inline=True)
comment(0x98B2, "SR2 bit7 set: more data available", inline=True)
comment(0x98B4, "SR2 non-zero, bit7 clear: frame done", inline=True)
label(0x98B6, "read_second_rx_byte")  # BMI: SR2 bit7 set, read second byte from FIFO
comment(0x98B6, "Read second byte of pair from RX FIFO", inline=True)
comment(0x98B9, "Store byte to buffer", inline=True)
comment(0x98BB, "Advance buffer offset", inline=True)
comment(0x98BC, "Save updated buffer position", inline=True)
comment(0x98BE, "Y != 0: no page boundary crossing", inline=True)
comment(0x98C0, "Crossed page: increment buffer high byte", inline=True)
comment(0x98C2, "Decrement remaining page count", inline=True)
comment(0x98C4, "No pages left: frame complete", inline=True)
label(0x98C6, "check_sr2_loop_again") # After page boundary on second byte, check SR2
comment(0x98C6, "Read SR2 for next iteration", inline=True)
comment(0x98C9, "SR2 non-zero: more data, loop back", inline=True)
comment(0x98CB, "SR2=0: no more data yet, wait for NMI", inline=True)
comment(0x98CE, "CR1=&00: disable all interrupts", inline=True)
comment(0x98D0, "Write CR1", inline=True)
comment(0x98D3, "CR2=&84: disable PSE for individual bit testing", inline=True)
comment(0x98D5, "Write CR2", inline=True)
comment(0x98D8, "Save Y (byte count from data RX loop)", inline=True)
comment(0x98E3, "Check if buffer space remains", inline=True)
label(0x98E5, "read_last_rx_byte")    # Multi-source: check buffer then read trailing byte
comment(0x98E5, "No buffer space: error/discard frame", inline=True)
comment(0x98EA, "Y = current buffer write offset", inline=True)
comment(0x98EC, "Store last byte in port receive buffer", inline=True)
comment(0x98EE, "Advance buffer write offset", inline=True)
comment(0x98F0, "No page wrap: proceed to send ACK", inline=True)
comment(0x98F2, "Page boundary: advance buffer page", inline=True)
label(0x98F4, "send_ack")             # No more data: unconditional JMP ack_tx
comment(0x98F4, "Send ACK frame to complete handshake", inline=True)
comment(0x98F7, "Read SR2 for Tube data receive path", inline=True)
label(0x98FA, "rx_tube_data")         # Poll SR2 RDA and forward byte pairs to Tube R3
comment(0x98FA, "RDA clear: no more data, frame complete", inline=True)
comment(0x98FC, "Read data byte from ADLC RX FIFO", inline=True)
comment(0x9930, "Unexpected end: return from NMI", inline=True)
comment(0x9933, "CR1=&00: disable all interrupts", inline=True)
comment(0x9935, "Write CR1 for individual bit testing", inline=True)
comment(0x9938, "CR2=&84: disable PSE", inline=True)
comment(0x993A, "Write CR2: same pattern as main path", inline=True)
comment(0x993D, "A=&02: FV mask for Tube completion", inline=True)
comment(0x993F, "BIT SR2: test FV (Z) and RDA (N)", inline=True)
comment(0x9942, "No FV: incomplete frame, error", inline=True)
comment(0x9944, "FV set, no RDA: proceed to ACK", inline=True)
comment(0x9946, "Check if any buffer was allocated", inline=True)
comment(0x9948, "OR all 4 buffer pointer bytes together", inline=True)
comment(0x994A, "Check buffer low byte", inline=True)
comment(0x994C, "Check buffer high byte", inline=True)
comment(0x994E, "All zero (null buffer): error", inline=True)
comment(0x9950, "Read extra trailing byte from FIFO", inline=True)
comment(0x9953, "Save extra byte at &0D5D for later use", inline=True)
comment(0x9956, "Bit5 = extra data byte available flag", inline=True)
comment(0x9958, "Set extra byte flag in tx_flags", inline=True)
comment(0x995B, "Store updated flags", inline=True)
comment(0x995E, "Load TX flags to check ACK type", inline=True)
comment(0x9961, "Bit7 clear: normal scout ACK", inline=True)
comment(0x9963, "Jump to TX success result", inline=True)
comment(0x9968, "Write CR1: switch to TX mode", inline=True)
comment(0x996D, "Write CR2: enable TX with status clear", inline=True)
comment(0x9972, "High byte of post-ACK handler", inline=True)
comment(0x9974, "Store next handler low byte", inline=True)
comment(0x9977, "Store next handler high byte", inline=True)
comment(0x9988, "Write dest net byte to FIFO", inline=True)
comment(0x998D, "High byte of nmi_ack_tx_src", inline=True)
comment(0x998F, "Set NMI vector to ack_tx_src handler", inline=True)
comment(0x99A9, "Write CR2 to clear status after ACK TX", inline=True)
comment(0x99AF, "Load saved next handler high byte", inline=True)
comment(0x99B2, "Install next NMI handler", inline=True)
label(0x99B5, "start_data_tx")          # Start data TX phase of four-way handshake
comment(0x99B5, "Jump to start data TX phase", inline=True)
label(0x99C0, "dispatch_nmi_error")    # JMP nmi_error_dispatch for TX failures
comment(0x99C0, "Jump to error handler", inline=True)
comment(0x99C3, "A=2: test bit1 of tx_flags", inline=True)
comment(0x99C5, "BIT tx_flags: check data transfer bit", inline=True)
comment(0x99C8, "Bit1 clear: no transfer -- return", inline=True)
comment(0x99CA, "CLC: init carry for 4-byte add", inline=True)
comment(0x99CB, "Save carry on stack for loop", inline=True)
comment(0x99CC, "Y=8: RXCB high pointer offset", inline=True)
label(0x99CE, "add_rxcb_ptr")         # 4-byte multi-precision add to RXCB buffer pointer
comment(0x99CE, "Load RXCB[Y] (buffer pointer byte)", inline=True)
comment(0x99D0, "Restore carry from stack", inline=True)
comment(0x99D1, "Add transfer count byte", inline=True)
comment(0x99D4, "Store updated pointer back to RXCB", inline=True)
comment(0x99D6, "Next byte", inline=True)
comment(0x99D7, "Save carry for next iteration", inline=True)
comment(0x99D8, "Done 4 bytes? (Y reaches &0C)", inline=True)
comment(0x99DA, "No: continue adding", inline=True)
comment(0x99DC, "Discard final carry", inline=True)
comment(0x99DD, "A=&20: test bit5 of tx_flags", inline=True)
comment(0x99DF, "BIT tx_flags: check Tube bit", inline=True)
comment(0x99E2, "No Tube: skip Tube update", inline=True)
comment(0x99E4, "Save X on stack", inline=True)
comment(0x99E5, "Push X", inline=True)
comment(0x99E6, "A=8: offset for Tube address", inline=True)
comment(0x99E8, "CLC for address calculation", inline=True)
comment(0x99E9, "Add workspace base offset", inline=True)
comment(0x99EB, "X = address low for Tube claim", inline=True)
comment(0x99EC, "Y = address high for Tube claim", inline=True)
comment(0x99EE, "A=1: Tube claim type (read)", inline=True)
comment(0x99F0, "Claim Tube address for transfer", inline=True)
comment(0x99F3, "Load extra RX data byte", inline=True)
comment(0x99F6, "Send to Tube via R3", inline=True)
comment(0x9A07, "Load buffer bytes remaining", inline=True)
comment(0x9A09, "CLC for address add", inline=True)
comment(0x9A0A, "Add to buffer base address", inline=True)
comment(0x9A0C, "No carry: skip high byte increment", inline=True)
comment(0x9A0E, "Carry: increment buffer high byte", inline=True)
label(0x9A10, "store_buf_ptr_lo")     # BCC: no carry, store updated buffer low byte
comment(0x9A10, "Y=8: store updated buffer position", inline=True)
comment(0x9A12, "Store updated low byte to RXCB", inline=True)
comment(0x9A14, "Y=9: buffer high byte offset", inline=True)
comment(0x9A15, "Load updated buffer high byte", inline=True)
comment(0x9A17, "Store high byte to RXCB", inline=True)
comment(0x9A19, "Load source network from scout buffer", inline=True)
comment(0x9A1C, "Y=3: RXCB source network offset", inline=True)
comment(0x9A1E, "Store source network to RXCB", inline=True)
comment(0x9A20, "Y=2: source station offset", inline=True)
comment(0x9A21, "Load source station from scout buffer", inline=True)
comment(0x9A24, "Store source station to RXCB", inline=True)
comment(0x9A26, "Y=1: port byte offset", inline=True)
comment(0x9A27, "Load port byte", inline=True)
comment(0x9A2A, "Store port to RXCB", inline=True)
comment(0x9A2C, "Y=0: control/flag byte offset", inline=True)
comment(0x9A2D, "Load control byte from scout", inline=True)
comment(0x9A30, "Set bit7 = reception complete flag", inline=True)
comment(0x9A32, "Store to RXCB (marks CB as complete)", inline=True)
comment(0x9A34, "Tube flag bit 1 AND tx_flags bit 1", inline=True)
comment(0x9A39, "No Tube transfer active -- skip release", inline=True)
comment(0x9A3D, "Release Tube claim before discarding", inline=True)
comment(0x9A40, "Re-enter idle RX listen mode", inline=True)
label(0x9A43, "install_rx_scout_handler") # Install RX scout NMI handler
comment(0x9A43, "Install nmi_rx_scout (&96F6) as NMI handler", inline=True)
comment(0x9A45, "High byte of nmi_rx_scout", inline=True)
comment(0x9A47, "Set NMI vector and return", inline=True)
comment(0x9A59, "Control byte &81-&88 range check", inline=True)
comment(0x9A5C, "Below &81: not an immediate op", inline=True)
comment(0x9A5E, "Out of range low: jump to discard", inline=True)
comment(0x9A60, "Above &88: not an immediate op", inline=True)
comment(0x9A62, "Out of range high: jump to discard", inline=True)
comment(0x9A64, "HALT(&87)/CONTINUE(&88) skip protection", inline=True)
comment(0x9A66, "Ctrl >= &87: dispatch without mask check", inline=True)
comment(0x9A6F, "Convert ctrl byte to 0-based index for mask", inline=True)
comment(0x9A70, "SEC for subtract", inline=True)
comment(0x9A71, "A = ctrl - &81 (0-based operation index)", inline=True)
comment(0x9A73, "Y = index for mask rotation count", inline=True)
comment(0x9A74, "Load protection mask from LSTAT", inline=True)
label(0x9A77, "rotate_prot_mask")      # Rotate protection mask right to align permission bit
comment(0x9A77, "Rotate mask right by control byte index", inline=True)
comment(0x9A78, "Decrement rotation counter", inline=True)
comment(0x9A79, "Loop until bit aligned", inline=True)
subroutine(0x9AE1, "rx_imm_peek_setup", hook=None,
    title="RX immediate: PEEK setup",
    description="""\
Writes &0D3D to port_ws_offset/rx_buf_offset, sets
scout_status=2, then calls tx_calc_transfer to send the
PEEK response data back to the requesting station.
Uses workspace offsets (&A6/&A7) for nmi_tx_block.""")
comment(0x9B19, "Get buffer position for reply header", inline=True)
comment(0x9B1B, "Clear carry for offset addition", inline=True)
comment(0x9B1C, "Data offset = buf_len + &80 (past header)", inline=True)
comment(0x9B1E, "Y=&7F: reply data length slot", inline=True)
comment(0x9B20, "Store reply data length in RX buffer", inline=True)
comment(0x9B22, "Y=&80: source station slot", inline=True)
comment(0x9B24, "Load requesting station number", inline=True)
comment(0x9B27, "Store source station in reply header", inline=True)
comment(0x9B2A, "Load requesting network number", inline=True)
comment(0x9B2D, "Store source network in reply header", inline=True)
comment(0x9B2F, "Load control byte from received frame", inline=True)
comment(0x9B32, "Save ctrl byte for TX response", inline=True)
comment(0x9B35, "IER bit 2: disable SR interrupt", inline=True)
comment(0x9B37, "Write IER to disable SR", inline=True)
comment(0x9B3A, "Read ACR for shift register config", inline=True)
comment(0x9B3D, "Isolate shift register mode bits (2-4)", inline=True)
comment(0x9B3F, "Save original SR mode for later restore", inline=True)
comment(0x9B42, "Reload ACR for modification", inline=True)
comment(0x9B45, "Clear SR mode bits (keep other bits)", inline=True)
comment(0x9B47, "SR mode 2: shift in under φ2", inline=True)
comment(0x9B49, "Apply new shift register mode", inline=True)
comment(0x9B4C, "Read SR to clear pending interrupt", inline=True)
comment(0x9B4F, "Return to idle listen mode", inline=True)
comment(0x9BE4, "Save X on stack", inline=True)
comment(0x9BE5, "Push X", inline=True)
comment(0x9BE6, "Y=2: TXCB offset for dest station", inline=True)
comment(0x9BE8, "Load dest station from TX control block", inline=True)
comment(0x9BEA, "Store to TX scout buffer", inline=True)
comment(0x9BEE, "Load dest network from TX control block", inline=True)
comment(0x9BF0, "Store to TX scout buffer", inline=True)
comment(0x9BF3, "Y=0: first byte of TX control block", inline=True)
comment(0x9BF5, "Load control/flag byte", inline=True)
comment(0x9BF7, "Bit7 set: immediate operation ctrl byte", inline=True)
comment(0x9BF9, "Bit7 clear: normal data transfer", inline=True)
label(0x9BFC, "tx_imm_op_setup")       # BMI: TXCB bit7 set, store ctrl byte for imm op
comment(0x9BFC, "Store control byte to TX scout buffer", inline=True)
comment(0x9BFF, "X = control byte for range checks", inline=True)
comment(0x9C00, "Y=1: port byte offset", inline=True)
comment(0x9C01, "Load port byte from TX control block", inline=True)
comment(0x9C03, "Store port byte to TX scout buffer", inline=True)
comment(0x9C06, "Port != 0: skip immediate op setup", inline=True)
comment(0x9C08, "Ctrl < &83: PEEK/POKE need address calc", inline=True)
comment(0x9C0A, "Ctrl >= &83: skip to range check", inline=True)
comment(0x9C0C, "SEC: init borrow for 4-byte subtract", inline=True)
comment(0x9C0D, "Save carry on stack for loop", inline=True)
comment(0x9C0E, "Y=8: high pointer offset in TXCB", inline=True)
label(0x9C10, "calc_peek_poke_size")   # 4-byte subtraction for PEEK/POKE transfer size
comment(0x9C10, "Load TXCB[Y] (end addr byte)", inline=True)
comment(0x9C12, "Y -= 4: back to start addr offset", inline=True)
comment(0x9C16, "Restore borrow from stack", inline=True)
comment(0x9C17, "end - start = transfer size byte", inline=True)
comment(0x9C19, "Store result to tx_data_start", inline=True)
comment(0x9C21, "Save borrow for next byte", inline=True)
comment(0x9C22, "Done all 4 bytes? (Y reaches &0C)", inline=True)
comment(0x9C24, "No: next byte pair", inline=True)
comment(0x9C26, "Discard final borrow", inline=True)
comment(0x9C27, "Ctrl >= &89: out of immediate range", inline=True)
comment(0x9C29, "Above range: normal data transfer", inline=True)
comment(0x9C2B, "Y=&0C: start of extra data in TXCB", inline=True)
label(0x9C2D, "copy_imm_params")      # Copy 4 extra parameter bytes from TXCB to NMI workspace
comment(0x9C2D, "Load extra parameter byte from TXCB", inline=True)
comment(0x9C2F, "Copy to NMI shim workspace at &0D1A+Y", inline=True)
comment(0x9C32, "Next byte", inline=True)
comment(0x9C33, "Done 4 bytes? (Y reaches &10)", inline=True)
comment(0x9C35, "No: continue copying", inline=True)
label(0x9C37, "tx_line_idle_check")   # BNE: port != 0, test SR2 INACTIVE before polling
comment(0x9C37, "A=&20: mask for SR2 INACTIVE bit", inline=True)
comment(0x9C39, "BIT SR2: test if line is idle", inline=True)
comment(0x9C3C, "Line not idle: handle as line jammed", inline=True)
comment(0x9C3E, "A=&FD: high byte of timeout counter", inline=True)
comment(0x9C40, "Push timeout high byte to stack", inline=True)
comment(0x9C41, "Scout frame = 6 address+ctrl bytes", inline=True)
comment(0x9C43, "Store scout frame length", inline=True)
comment(0x9C46, "A=0: init low byte of timeout counter", inline=True)
label(0x9C4F, "test_inactive_retry")   # Reload INACTIVE mask and retry polling
label(0x9C6D, "inactive_retry")       # BEQ: INACTIVE not set, re-enable NMIs/retry
comment(0x9C8A, "Write CR2 to abort TX", inline=True)
comment(0x9C8D, "Clean 3 bytes of timeout loop state", inline=True)
comment(0x9C92, "ALWAYS branch to shared error handler", inline=True)
label(0x9C94, "tx_no_clock_error")   # Error code &43: "No Clock"
comment(0x9C94, "Error &43 = 'No Clock'", inline=True)
label(0x9C96, "store_tx_error")      # Store error code to TX control block
comment(0x9C96, "Offset 0 = error byte in TX control block", inline=True)
comment(0x9C98, "Store error code in TX CB byte 0", inline=True)
comment(0x9C9A, "&80 = TX complete flag", inline=True)
comment(0x9C9C, "Signal TX operation complete", inline=True)
comment(0x9C9F, "Restore X saved by caller", inline=True)
comment(0x9CA0, "Move to X register", inline=True)
comment(0x9CA1, "Return to TX caller", inline=True)
comment(0x9CA7, "Write to ADLC CR1", inline=True)
comment(0x9CAC, "High byte of NMI handler address", inline=True)
comment(0x9CAE, "Write NMI vector low byte directly", inline=True)
comment(0x9CB1, "Write NMI vector high byte directly", inline=True)
comment(0x9CB7, "Load destination port number", inline=True)
comment(0x9CBA, "Port != 0: standard data transfer", inline=True)
comment(0x9CBC, "Port 0: load control byte for table lookup", inline=True)
comment(0x9CBF, "Look up tx_flags from table", inline=True)
comment(0x9CC2, "Store operation flags", inline=True)
comment(0x9CC5, "Look up tx_length from table", inline=True)
comment(0x9CC8, "Store expected transfer length", inline=True)
subroutine(0x9D00, "tx_ctrl_add_done", hook=None,
    title="TX ctrl: JSR/UserProc/OSProc setup",
    description="""\
Sets scout_status=2 and calls tx_calc_transfer directly
(no 4-byte address addition needed for procedure calls).
Shared by operation types &83-&85.""")
label(0x9D16, "setup_data_xfer")       # Configure scout length and flags for data transfer
comment(0x9D16, "Load dest station for broadcast check", inline=True)
comment(0x9D19, "AND with dest network", inline=True)
comment(0x9D1C, "Both &FF = broadcast address?", inline=True)
comment(0x9D1E, "Not broadcast: unicast path", inline=True)
comment(0x9D20, "Broadcast scout: 14 bytes total", inline=True)
comment(0x9D22, "Store broadcast scout length", inline=True)
comment(0x9D25, "A=&40: broadcast flag", inline=True)
comment(0x9D27, "Set broadcast flag in tx_flags", inline=True)
comment(0x9D2A, "Y=4: start of address data in TXCB", inline=True)
label(0x9D2C, "copy_bcast_addr")      # Copy 8-byte broadcast address data into TX scout buffer
comment(0x9D2C, "Copy TXCB address bytes to scout buffer", inline=True)
comment(0x9D2E, "Store to TX source/data area", inline=True)
comment(0x9D31, "Next byte", inline=True)
comment(0x9D32, "Done 8 bytes? (Y reaches &0C)", inline=True)
comment(0x9D34, "No: continue copying", inline=True)
label(0x9D38, "setup_unicast_xfer")   # BNE: not broadcast, clear flags/scout_status=2
comment(0x9D38, "A=0: clear flags for unicast", inline=True)
comment(0x9D3A, "Clear tx_flags", inline=True)
comment(0x9D3D, "scout_status=2: data transfer pending", inline=True)
comment(0x9D3F, "Store scout status", inline=True)
comment(0x9D42, "Calculate transfer size from RXCB", inline=True)
comment(0x9D45, "Restore processor status from stack", inline=True)
comment(0x9D46, "Restore stacked registers (4 PLAs)", inline=True)
comment(0x9D47, "Second PLA", inline=True)
comment(0x9D48, "Third PLA", inline=True)
comment(0x9D49, "Fourth PLA", inline=True)
comment(0x9D4A, "Restore X from A", inline=True)
comment(0x9D4B, "Return to caller", inline=True)
label(0x9D52, "tx_fifo_write")        # NMI TX loop: write 2 bytes per iteration to ADLC FIFO
label(0x9D76, "tx_fifo_not_ready")    # BVC: TDRA clear, write CR2=&67, error &41
label(0x9D7D, "tx_store_error")       # BNE: error &42 path, merge with &9CF6
label(0x9D80, "delay_nmi_disable")    # PHA/PLA delay loop after INTOFF before storing TX result
comment(0x9D8A, "Write to ADLC CR2", inline=True)
comment(0x9D8F, "High byte of handler address", inline=True)
comment(0x9D91, "Install and return via set_nmi_vector", inline=True)
label(0x9DA1, "check_handshake_bit")  # BVC: tx_flags bit6 clear, check bit0
label(0x9DAB, "install_reply_scout")  # BEQ: handshake bit0 clear, install nmi_reply_scout
comment(0x9DB9, "Read first RX byte (destination station)", inline=True)
label(0x9DE0, "reject_reply")          # Reject invalid reply scout frame
comment(0x9E01, "Write CR2: enable RTS for TX handshake", inline=True)
comment(0x9E06, "Write CR1: reset RX, enable TX interrupt", inline=True)
comment(0x9E0B, "High byte &9E of next handler address", inline=True)
comment(0x9E0D, "Store low byte to nmi_next_lo", inline=True)
comment(0x9E10, "Store high byte to nmi_next_hi", inline=True)
comment(0x9E1E, "Load dest network for scout ACK TX", inline=True)
comment(0x9E21, "Write dest network to TX FIFO", inline=True)
comment(0x9E26, "High byte &9D of handler address", inline=True)
comment(0x9E28, "Set NMI vector and return", inline=True)
comment(0x9E2E, "BIT SR1: check TDRA before writing", inline=True)
comment(0x9E31, "TDRA not ready: TX error", inline=True)
comment(0x9E36, "Network = 0 (local network)", inline=True)
comment(0x9E38, "Write network byte to TX FIFO", inline=True)
comment(0x9E3B, "Test bit 1 of tx_flags", inline=True)
comment(0x9E3D, "Check if immediate-op or data-transfer", inline=True)
comment(0x9E40, "Bit 1 set: immediate op, use alt handler", inline=True)
comment(0x9E42, "Install nmi_data_tx at &9E50", inline=True)
comment(0x9E44, "High byte of handler address", inline=True)
comment(0x9E46, "Install and return via set_nmi_vector", inline=True)
label(0x9E49, "install_imm_data_nmi")  # BNE: tx_flags bit1 set, install nmi_imm_data
comment(0x9E49, "Install nmi_imm_data at &9EA4", inline=True)
comment(0x9E4B, "High byte of handler address", inline=True)
comment(0x9E4D, "Install and return via set_nmi_vector", inline=True)
label(0x9E55, "data_tx_check_fifo")   # Test TDRA and write data byte pair to FIFO
comment(0x9E59, "Write first byte of pair to FIFO", inline=True)
comment(0x9E5C, "Advance buffer offset", inline=True)
comment(0x9E5D, "No page crossing", inline=True)
comment(0x9E5F, "Page crossing: decrement page count", inline=True)
comment(0x9E61, "No pages left: send last data", inline=True)
comment(0x9E63, "Increment buffer high byte", inline=True)
label(0x9E65, "write_second_tx_byte") # BNE: skip page check, write second FIFO byte
comment(0x9E65, "Load second byte of pair", inline=True)
comment(0x9E67, "Write second byte to FIFO", inline=True)
comment(0x9E6A, "Advance buffer offset", inline=True)
comment(0x9E6B, "Save updated buffer position", inline=True)
comment(0x9E6D, "No page crossing", inline=True)
comment(0x9E6F, "Page crossing: decrement page count", inline=True)
comment(0x9E71, "No pages left: send last data", inline=True)
comment(0x9E73, "Increment buffer high byte", inline=True)
label(0x9E75, "check_irq_loop")       # BNE: skip page check, test SR1 IRQ for loop
comment(0x9E75, "BIT SR1: test IRQ (N=bit7) for tight loop", inline=True)
comment(0x9E78, "IRQ still set: write 2 more bytes", inline=True)
comment(0x9E7A, "No IRQ: return, wait for next NMI", inline=True)
comment(0x9E7F, "Write CR2 to close frame", inline=True)
comment(0x9E82, "Check tx_flags for next action", inline=True)
comment(0x9E85, "Bit7 clear: error, install saved handler", inline=True)
comment(0x9E87, "Install discard_reset_listen at &9A34", inline=True)
comment(0x9E89, "High byte of &9A34 handler", inline=True)
comment(0x9E8B, "Set NMI vector and return", inline=True)
comment(0x9E8E, "Load saved next handler low byte", inline=True)
comment(0x9E9E, "Load saved next handler high byte", inline=True)
comment(0x9EA1, "Install saved handler and return", inline=True)
comment(0x9EA4, "Tube TX: BIT SR1 test TDRA", inline=True)
label(0x9EA7, "tube_tx_fifo_write")    # BMI: IRQ set, Tube TX FIFO write entry point
comment(0x9EA7, "TDRA not ready -- error", inline=True)
comment(0x9EA9, "Read byte from Tube R3", inline=True)
comment(0x9EAC, "Write to TX FIFO", inline=True)
comment(0x9EAF, "Increment 4-byte buffer counter", inline=True)
comment(0x9EB1, "Low byte didn't wrap", inline=True)
comment(0x9EB3, "Carry into second byte", inline=True)
comment(0x9EB5, "No further carry", inline=True)
comment(0x9EB7, "Carry into third byte", inline=True)
comment(0x9EB9, "No further carry", inline=True)
comment(0x9EBB, "Carry into fourth byte", inline=True)
comment(0x9EBD, "Counter wrapped to zero: last data", inline=True)
label(0x9EBF, "write_second_tube_byte") # BNE: skip carry, read/write second Tube byte
comment(0x9EBF, "Read second Tube byte from R3", inline=True)
comment(0x9EC2, "Write second byte to TX FIFO", inline=True)
comment(0x9EC5, "Increment 4-byte counter (second byte)", inline=True)
comment(0x9EC7, "Low byte didn't wrap", inline=True)
comment(0x9EC9, "Carry into second byte", inline=True)
comment(0x9ECB, "No further carry", inline=True)
label(0x9ECD, "tube_tx_inc_byte3")    # Tube TX buffer counter byte 3 increment
comment(0x9ECD, "Carry into third byte", inline=True)
comment(0x9ECF, "No further carry", inline=True)
comment(0x9ED1, "Carry into fourth byte", inline=True)
comment(0x9ED3, "Counter wrapped to zero: last data", inline=True)
label(0x9ED5, "check_tube_irq_loop")  # BNE: skip carry, test SR1 IRQ for loop
comment(0x9ED5, "BIT SR1: test IRQ for tight loop", inline=True)
comment(0x9ED8, "IRQ still set: write 2 more bytes", inline=True)
comment(0x9EDA, "No IRQ: return, wait for next NMI", inline=True)
comment(0x9EDF, "Write to ADLC CR1", inline=True)
comment(0x9EE4, "High byte of handler address", inline=True)
comment(0x9EE6, "Install and return via set_nmi_vector", inline=True)
label(0x9F32, "check_fv_final_ack")    # BPL: tx_flags bit7 clear, test FV for frame end
subroutine(0x9F3D, "tx_result_fail", hook=None,
    title="TX failure: not listening",
    description="""\
Loads error code &41 (not listening) and falls through to
tx_store_result. The most common TX error path — reached from
11 sites across the final-ACK validation chain when the remote
station doesn't respond or the frame is malformed.""")
comment(0x9F3D, "A=&41: not listening error code", inline=True)
label(0x9F77, "calc_transfer_size")    # 4-byte subtraction to calculate actual bytes received
comment(0x9F8C, "A = saved X", inline=True)
comment(0x9F8D, "Save X", inline=True)
label(0x9FA4, "restore_x_and_return") # BCC: Tube not claimed, restore X/RTS
label(0x9FA7, "fallback_calc_transfer") # BEQ: no buffer/Tube, simple 2-byte subtract
comment(0x9FA7, "Y=4: RXCB current pointer offset", inline=True)
comment(0x9FAB, "Y=8: RXCB start address offset", inline=True)
comment(0x9FAD, "Set carry for subtraction", inline=True)
comment(0x9FB2, "Y=5: current ptr hi offset", inline=True)
comment(0x9FB6, "Propagate borrow from lo subtraction", inline=True)
comment(0x9FB8, "Temp store adjusted current ptr hi", inline=True)
comment(0x9FBA, "Y=8: start address lo offset", inline=True)
comment(0x9FBE, "Store to scratch (side effect)", inline=True)
comment(0x9FC0, "Y=9: start address hi offset", inline=True)
comment(0x9FC2, "Load RXCB[9] (start ptr hi)", inline=True)
comment(0x9FC4, "Set carry for subtraction", inline=True)
comment(0x9FC5, "start_hi - adjusted current_hi", inline=True)
comment(0x9FCB, "INTOFF: disable NMIs while switching ROM", inline=True)
comment(0x9FCE, "Save A", inline=True)
comment(0x9FCF, "Transfer Y to A", inline=True)
comment(0x9FD0, "Save Y (via A)", inline=True)
comment(0x9FD1, "ROM bank 0 (patched during init for actual bank)", inline=True)
comment(0x9FD3, "Select Econet ROM bank via ROMSEL", inline=True)
comment(0x9FD6, "Jump to scout handler in ROM", inline=True)
comment(0x9FD9, "Store handler high byte at &0D0D", inline=True)
comment(0x9FDC, "Store handler low byte at &0D0C", inline=True)
comment(0x9FDF, "Restore NFS ROM bank", inline=True)
comment(0x9FE1, "Page in via hardware latch", inline=True)
comment(0x9FE4, "Restore Y from stack", inline=True)
comment(0x9FE6, "Restore A from stack", inline=True)
comment(0x9FE7, "INTON: re-enable NMIs", inline=True)
comment(0x9FEA, "Return from interrupt", inline=True)
# ============================================================

# ============================================================
# Annotations back-propagated from NFS 3.34B
# ============================================================
label(0x0020, "tube_send_zero_r2")    # Sends zero prefix via R2 to Tube
label(0x0036, "tube_enter_main_loop")
subroutine(0x0036, "tube_enter_main_loop", hook=None,
    title="Save registers and enter Tube polling loop",
    description="""\
Saves X and Y to zp_temp_11/zp_temp_10, then falls through
to tube_main_loop which polls Tube R1 (WRCH) and R2 (command)
registers in an infinite loop. Called from tube_init_reloc
after ROM relocation and from tube_dispatch_table handlers
that need to restart the main loop.""")
comment(0x0036, "Save X to temporary", inline=True)
comment(0x0038, "Save Y to temporary", inline=True)
comment(0x0414, "&80 sentinel: clear address claim", inline=True)
label(0x0426, "setup_data_transfer")   # Save (X,Y) as transfer addr, send type via R4
comment(0x0438, "Y=8: write to Tube control register", inline=True)
comment(0x043A, "Configure Tube for data transfer", inline=True)
comment(0x043D, "Y=&10: data transfer control value", inline=True)
comment(0x043F, "Check transfer type (X=2?)", inline=True)
comment(0x0441, "X<2: skip alternate control", inline=True)
comment(0x0443, "Y=&90: alternate control for X>=2", inline=True)
label(0x0445, "tube_ctrl_write_2")
comment(0x0445, "Write transfer control to Tube", inline=True)
comment(0x0448, "Send data byte via Tube R4", inline=True)
comment(0x044B, "Y=&88: post-transfer control value", inline=True)
comment(0x044D, "Transfer type to A for comparison", inline=True)
comment(0x044E, "Type 0: go to NMI flush check", inline=True)
comment(0x0450, "Check if type 2", inline=True)
comment(0x0452, "Type 2: go to NMI flush check", inline=True)
comment(0x0454, "Write post-transfer control", inline=True)
comment(0x0457, "Check if type 4 (SENDW)", inline=True)
comment(0x045B, "Discard return address (low byte)", inline=True)
comment(0x045C, "Discard return address (high byte)", inline=True)
label(0x045D, "release_claim_restart")  # Release Tube claim flag and restart main loop
comment(0x045D, "A=&80: reset claim flag sentinel", inline=True)
comment(0x045F, "Clear claim-in-progress flag", inline=True)
label(0x0464, "flush_r3_nmi_check")   # BIT R3 twice to flush, check NMI
comment(0x0464, "Poll R4 status: wait for transfer ready", inline=True)
comment(0x0467, "V=0: not ready, poll again", inline=True)
comment(0x0469, "Flush Tube R3 data register", inline=True)
comment(0x046C, "Flush Tube R3 again", inline=True)
comment(0x046F, "Write final control value", inline=True)
comment(0x0472, "Return from Tube data setup", inline=True)
label(0x0473, "tube_begin")          # BEGIN: startup entry for Tube host code
comment(0x0473, "BEGIN: enable interrupts for Tube host code", inline=True)
comment(0x0474, "Save processor status", inline=True)
comment(0x0475, "Save A on stack", inline=True)
comment(0x0476, "Y=0: start at beginning of page", inline=True)
comment(0x0478, "Store to zero page pointer low byte", inline=True)
subroutine(0x047A, "tube_init_reloc", hook=None,
    title="Initialise relocation address for ROM transfer",
    description="""\
Sets source page to &8000 and page counter to &80. Checks
ROM type bit 5 for a relocation address in the ROM header;
if present, extracts the 4-byte address from after the
copyright string. Otherwise uses default &8000 start.""")
comment(0x04A4, "Restore A from stack", inline=True)
comment(0x04A5, "Restore processor status", inline=True)
comment(0x04A6, "Carry set: language entry (claim Tube)", inline=True)
comment(0x04A8, "X = A (preserved from entry)", inline=True)
comment(0x04A9, "Non-zero: check break type", inline=True)
comment(0x04AB, "A=0: acknowledge and return", inline=True)
comment(0x04AE, "X=0 for OSBYTE read", inline=True)
comment(0x04B0, "Y=&FF for OSBYTE read", inline=True)
comment(0x04B2, "OSBYTE &FD: read last break type", inline=True)
comment(0x04B8, "Soft break (0): skip ROM transfer", inline=True)
comment(0x04BA, "A=&FF: claim Tube for all operations", inline=True)
comment(0x04BC, "Claim Tube address via R4", inline=True)
comment(0x04BF, "Not claimed: retry until claimed", inline=True)
comment(0x04C1, "Transfer type 1 (parasite to host)", inline=True)
comment(0x04C3, "Set up Tube transfer parameters", inline=True)
comment(0x04C6, "Y=0: start at page boundary", inline=True)
comment(0x04C8, "Source ptr low = 0", inline=True)
comment(0x04CA, "X=&40: 64 pages (16KB) to transfer", inline=True)
label(0x04CC, "send_rom_byte")         # Read byte from (zp_ptr),Y and send to Tube R3
comment(0x04CC, "Read byte from source address", inline=True)
comment(0x04CE, "Send byte to Tube via R3", inline=True)
label(0x04D1, "poll_r3_ready")         # Poll Tube R3 status until ready
comment(0x04D1, "Check R3 status", inline=True)
comment(0x04D4, "Not ready: wait for Tube", inline=True)
comment(0x04D6, "Next byte in page", inline=True)
comment(0x04D7, "More bytes in page: continue", inline=True)
comment(0x04D9, "Next source page", inline=True)
comment(0x04DB, "Decrement page counter", inline=True)
comment(0x04DC, "More pages: continue transfer", inline=True)
comment(0x04DE, "Transfer type 4 (host to parasite burst)", inline=True)
comment(0x04E0, "Y=0: low byte of param block ptr", inline=True)
comment(0x04E2, "X=&57: param block at &0057", inline=True)
comment(0x04E4, "Claim Tube and start transfer", inline=True)
comment(0x04E7, "R2 command: OSRDCH request", inline=True)
comment(0x04E9, "Send OSRDCH request to host", inline=True)
comment(0x04EC, "Jump to RDCH completion handler", inline=True)
comment(0x04F1, "Restore X from saved value", inline=True)
comment(0x04F3, "Read result byte from R2", inline=True)
comment(0x04F6, "Shift carry into C flag", inline=True)
comment(0x04F7, "Poll R2 status register", inline=True)
comment(0x04FA, "Bit 7 clear: R2 not ready, wait", inline=True)
comment(0x04FC, "Read byte from R2 data register", inline=True)
comment(0x04FF, "Return with pointers initialised", inline=True)
comment(0x051D, "A=0: send null prefix via R2", inline=True)
comment(0x051F, "Send prefix byte to co-processor", inline=True)
label(0x0522, "poll_r2_reply")         # Poll Tube R2 status for co-processor reply
comment(0x0522, "Poll R2 for co-processor reply", inline=True)
comment(0x0525, "R2 ready: go process reply", inline=True)
comment(0x0527, "Check R1 for pending WRCH request", inline=True)
comment(0x052A, "No R1 data: back to polling R2", inline=True)
comment(0x052C, "Read WRCH character from R1", inline=True)
comment(0x0532, "Resume R2 polling after servicing", inline=True)
label(0x0535, "wrch_echo_reply")       # R2 ready: recover char, echo back, re-enter loop
comment(0x0535, "Recover original character", inline=True)
comment(0x0536, "Echo character back via R2", inline=True)
comment(0x0539, "Push for dispatch loop re-entry", inline=True)
comment(0x053A, "Enter main dispatch loop", inline=True)
comment(0x053F, "Restore saved Y from temporary", inline=True)
comment(0x0541, "Restore saved A", inline=True)
comment(0x0542, "Return to caller", inline=True)
comment(0x0557, "Save byte read from file", inline=True)
comment(0x0558, "Send carry+byte reply (BGET result)", inline=True)
label(0x055F, "send_reply_ok")         # Set no-error bit, encode carry, send reply via R2
comment(0x055F, "Set bit 7 (no-error flag)", inline=True)
comment(0x0561, "ROR A: encode carry (error flag) into bit 7", inline=True)
comment(0x0562, "= JSR tube_send_r2 (overlaps &053D entry)", inline=True)
comment(0x0565, "Restore read character/byte", inline=True)
comment(0x0576, "Save file handle result", inline=True)
comment(0x0577, "A=&FF: success marker", inline=True)
comment(0x0579, "Send success marker via R2", inline=True)
comment(0x057C, "Restore file handle", inline=True)
comment(0x0598, "Loop until all 4 bytes read", inline=True)
comment(0x059A, "X=0: reset index after loop", inline=True)
comment(0x05F1, "Set bit 7: mark result as present", inline=True)
comment(0x0600, "OSGBPB done: return to main loop", inline=True)
label(0x0604, "read_gbpb_params")      # Read 13 OSGBPB param bytes from R2
comment(0x0604, "Read param byte from Tube R2", inline=True)
comment(0x0607, "Store in zero page param block", inline=True)
comment(0x0609, "Next byte (descending)", inline=True)
comment(0x060A, "Loop until all 13 bytes read", inline=True)
comment(0x060C, "Read A (OSGBPB function code)", inline=True)
comment(0x060F, "X=0 after loop", inline=True)
comment(0x0610, "Y=0 for OSGBPB call", inline=True)
comment(0x0619, "X=12: send 13 updated param bytes", inline=True)
label(0x061B, "send_gbpb_params")      # Send 13 updated OSGBPB params via R2
comment(0x061B, "Load updated param byte", inline=True)
comment(0x061D, "Send param byte via R2", inline=True)
comment(0x0620, "Next byte (descending)", inline=True)
comment(0x0621, "Loop until all 13 bytes sent", inline=True)
comment(0x0623, "Return to main event loop", inline=True)
comment(0x0629, "Save in X", inline=True)
comment(0x062A, "Read A (OSBYTE function code)", inline=True)
comment(0x062D, "Execute OSBYTE A,X", inline=True)
comment(0x0630, "Poll R2 status (bit 6 = ready)", inline=True)
comment(0x0633, "Not ready: keep polling", inline=True)
comment(0x0638, "Return to main event loop", inline=True)
comment(0x063E, "Save in X", inline=True)
comment(0x063F, "Read Y parameter from co-processor", inline=True)
comment(0x0642, "Save in Y", inline=True)
comment(0x0643, "Read A (OSBYTE function code)", inline=True)
comment(0x0646, "Execute OSBYTE A,X,Y", inline=True)
comment(0x064D, "A=&40: high bit will hold carry", inline=True)
comment(0x0650, "Send carry+status byte via R2", inline=True)
comment(0x0653, "Poll R2 status for ready", inline=True)
comment(0x0656, "Not ready: keep polling", inline=True)
comment(0x0660, "Save OSWORD number in Y", inline=True)
comment(0x0661, "Poll R2 status for data ready", inline=True)
comment(0x0664, "Not ready: keep polling", inline=True)
comment(0x066A, "No params (length=0): skip read loop", inline=True)
comment(0x066C, "Poll R2 status for data ready", inline=True)
comment(0x066F, "Not ready: keep polling", inline=True)
comment(0x0671, "Read param byte from R2", inline=True)
comment(0x0677, "Next param byte (descending)", inline=True)
comment(0x0678, "Loop until all params read", inline=True)
comment(0x067D, "Y=&01: param block at &0130", inline=True)
comment(0x067F, "Execute OSWORD with XY=&0130", inline=True)
comment(0x0682, "A=&FF: result marker for co-processor", inline=True)
comment(0x0684, "Send result marker via R2", inline=True)
comment(0x0687, "Poll R2 status for ready", inline=True)
comment(0x068A, "Not ready: keep polling", inline=True)
comment(0x068F, "Decrement result byte counter", inline=True)
comment(0x0695, "Poll R2 status for ready", inline=True)
comment(0x0698, "Not ready: keep polling", inline=True)
comment(0x069A, "Send result byte via R2", inline=True)
comment(0x069D, "Next result byte (descending)", inline=True)
comment(0x069E, "Loop until all results sent", inline=True)
comment(0x06A0, "Return to main event loop", inline=True)
comment(0x06A5, "Read control block byte from R2", inline=True)
comment(0x06A8, "Store in zero page params", inline=True)
comment(0x06AA, "Next byte (descending)", inline=True)
comment(0x06AB, "Loop until all 5 bytes read", inline=True)
comment(0x06AE, "Y=0 for OSWORD 0", inline=True)
comment(0x06B0, "A=0: OSWORD 0 (read line)", inline=True)
comment(0x06B1, "Read input line from keyboard", inline=True)
comment(0x06B8, "Escape: send &FF error to co-processor", inline=True)
comment(0x06BB, "X=0: start of input buffer at &0700", inline=True)
comment(0x06BF, "Send &7F (success) to co-processor", inline=True)
comment(0x06C2, "Load char from input buffer", inline=True)
comment(0x06C5, "Send char to co-processor", inline=True)
comment(0x06C8, "Next character", inline=True)
comment(0x06CB, "Loop until CR terminator sent", inline=True)
comment(0x06CD, "Return to main event loop", inline=True)
comment(0x06D0, "Poll R2 status (bit 6 = ready)", inline=True)
comment(0x06D3, "Not ready: keep polling", inline=True)
comment(0x06D5, "Write A to Tube R2 data register", inline=True)
comment(0x06D8, "Return to caller", inline=True)
comment(0x06D9, "Poll R4 status (bit 6 = ready)", inline=True)
comment(0x06DC, "Not ready: keep polling", inline=True)
comment(0x06DE, "Write A to Tube R4 data register", inline=True)
comment(0x06E1, "Return to caller", inline=True)
comment(0x06E5, "ROR: shift escape bit 7 to carry", inline=True)
comment(0x06EB, "Send zero prefix via R1", inline=True)
comment(0x06EE, "Y value for event", inline=True)
comment(0x06EF, "Send Y via R1", inline=True)
comment(0x06F2, "X value for event", inline=True)
comment(0x06F3, "Send X via R1", inline=True)
comment(0x06F6, "Restore A (event type)", inline=True)
comment(0x06F7, "Poll R1 status (bit 6 = ready)", inline=True)
comment(0x06FA, "Not ready: keep polling", inline=True)
comment(0x06FC, "Write A to Tube R1 data register", inline=True)
comment(0x06FF, "Return to caller", inline=True)
comment(0x806D, "Negative: not a net command, exit", inline=True)
comment(0x8074, "Transfer Y to A for dispatch", inline=True)
comment(0x8079, "Copy command text to FS buffer", inline=True)
comment(0x8083, "CSD handle zero: not logged in", inline=True)
comment(0x8093, "X = function code for dispatch", inline=True)
comment(0x8094, "Save Y (command text ptr hi)", inline=True)
comment(0x80B9, "Save ROM number across OSBYTE", inline=True)
comment(0x80BB, "Save Tube address across OSBYTE", inline=True)
comment(0x80BD, "X=6 extra pages for char definitions", inline=True)
comment(0x80BF, "OSBYTE &14: explode character RAM", inline=True)
comment(0x80C4, "Restore ROM number", inline=True)
comment(0x80C6, "Continue to vector setup", inline=True)
comment(0x80CA, "Set WRCHV low byte", inline=True)
comment(0x80CD, "A=5: WRCHV high byte", inline=True)
comment(0x80CF, "Set WRCHV high byte", inline=True)
comment(0x80D4, "Set RDCHV low byte", inline=True)
comment(0x80D7, "A=4: RDCHV high byte", inline=True)
comment(0x80D9, "Set RDCHV high byte", inline=True)
comment(0x80DE, "Set BRKV low byte", inline=True)
comment(0x80E1, "A=0: BRKV high byte (page zero)", inline=True)
comment(0x80E3, "Set BRKV high byte", inline=True)
comment(0x80E8, "Set EVNTV low byte", inline=True)
comment(0x80EB, "A=6: EVNTV high byte", inline=True)
comment(0x80ED, "Set EVNTV high byte", inline=True)
comment(0x80F2, "Write &8E to Tube control register", inline=True)
comment(0x80F5, "Save Y to temporary", inline=True)
comment(0x80F7, "Y=0: start ROM-to-RAM copy loop", inline=True)
label(0x811B, "restore_y_check_svc")   # Restore Y from temp, continue service dispatch
comment(0x811B, "Restore Y (ROM number)", inline=True)
label(0x811D, "tube_chars_done")       # BEQ: zero byte received, transfer complete
comment(0x811D, "A=0: fall through to service &12 check", inline=True)
label(0x811F, "check_svc_12")          # Convergence before CMP #&12 test
comment(0x811F, "Is this service &12 (select FS)?", inline=True)
comment(0x8121, "No: check if service < &0D", inline=True)
comment(0x8123, "Service &12: Y=5 (NFS)?", inline=True)
comment(0x8125, "Y=5: select NFS", inline=True)
comment(0x8145, "Return (not our command)", inline=True)
label(0x819D, "match_next_char")       # Compare next char against ROM string byte
comment(0x81BB, "Return (not our service call)", inline=True)
comment(0x81BC, "Print inline ROM identification string", inline=True)
comment(0x822E, "A=&8F: issue service request", inline=True)
comment(0x8230, "X=&0F: 'vectors claimed' service", inline=True)
comment(0x8235, "X=&0A: service &0A", inline=True)
comment(0x823C, "Non-zero: skip auto-boot", inline=True)
comment(0x8240, "Y=&82: ROM page high byte", inline=True)
comment(0x8242, "Execute command string at (X, Y)", inline=True)
comment(0x8273, "Claim workspace up to page &10", inline=True)
comment(0x8275, "Return to caller", inline=True)
comment(0x82FF, "Load FS state byte at offset Y", inline=True)
comment(0x8302, "Store to workspace backup area", inline=True)
comment(0x8304, "Next byte down", inline=True)
comment(0x8307, "Loop for offsets &1D..&15", inline=True)
comment(0x8309, "A=&7B: printer driver going dormant", inline=True)
comment(0x831B, "Return after port setup", inline=True)
comment(0x8341, "A=&2A: error ptr for retry", inline=True)
comment(0x8349, "A=&77: OSBYTE close spool/exec", inline=True)
comment(0x8357, "A=&2A: error ptr for retry", inline=True)
label(0x8359, "store_fs_hdr_clc")       # CLC entry: clear carry then store function code
comment(0x8359, "CLC: no byte-stream path", inline=True)
label(0x835A, "store_fs_hdr_fn")       # Store function code and CSD/LIB handles
comment(0x835A, "Store function code at &0F01", inline=True)
comment(0x835D, "Store error ptr for TX poll", inline=True)
comment(0x8384, "Load error ptr for TX retry", inline=True)
comment(0x83A2, "CLC for address addition", inline=True)
label(0x840F, "find_cr_terminator")
comment(0x840F, "Advance to next reply buffer byte", inline=True)
comment(0x8410, "A=CR: terminator to search for", inline=True)
comment(0x8412, "XOR with buffer byte (0 when CR)", inline=True)
comment(0x8414, "Not CR: continue scanning", inline=True)
comment(0x8416, "Store 0 (from XOR) to replace CR", inline=True)
comment(0x8418, "Execute error via JMP indirect", inline=True)
comment(0x841F, "Transfer A to Y for indexing", inline=True)
comment(0x8421, "Transfer to X for return", inline=True)
comment(0x843D, "Advance output buffer position", inline=True)
comment(0x843E, "Advance source string pointer", inline=True)
comment(0x843F, "Continue copying message bytes", inline=True)
label(0x8441, "execute_brk_error")
comment(0x8441, "Execute constructed BRK error", inline=True)
label(0x8444, "sp_dot_string")
comment(0x847A, "A=&7E: OSBYTE acknowledge escape", inline=True)
subroutine(0x847C, "check_escape_handler", hook=None,
    title="Test MOS escape flag and abort if pending",
    description="""\
Tests MOS escape flag (&FF bit 7). If escape is pending:
acknowledges via OSBYTE &7E, writes &3F (deleted marker) into
the control block via (net_tx_ptr),Y, and branches to the
NLISTN error path. If no escape, returns immediately.""")
comment(0x847C, "Test escape flag (bit 7)", inline=True)
comment(0x847E, "Bit 7 clear: no escape, return", inline=True)
comment(0x8480, "Acknowledge escape via OSBYTE &7E", inline=True)
comment(0x8483, "Non-zero: report 'Not listening'", inline=True)
comment(0x8496, "C=0: no escape, test for retry", inline=True)
label(0x849B, "tx_flow_control")
comment(0x849B, "Branch if flow control set", inline=True)
comment(0x849D, "Error code: TX failed", inline=True)
label(0x84A0, "tx_error_classify")
comment(0x84A0, "Shift error bits right", inline=True)
comment(0x84A4, "Y += 5", inline=True)
comment(0x84AE, "Return with handle mask in A", inline=True)
comment(0x8508, "A = function code / command", inline=True)
comment(0x850A, "X = control block ptr lo", inline=True)
comment(0x850C, "Y = control block ptr hi", inline=True)
comment(0x850E, "X dup for indexed access via (fs_crc)", inline=True)
comment(0x8510, "Y dup for indexed access", inline=True)
comment(0x8512, "Return", inline=True)
comment(0x853C, "Store return addr low as string ptr", inline=True)
comment(0x853F, "Store return addr high as string ptr", inline=True)
comment(0x8541, "Y=0: offset for indirect load", inline=True)
comment(0x8545, "No page wrap: skip high byte inc", inline=True)
comment(0x8547, "Handle page crossing in pointer", inline=True)
comment(0x8550, "Continue printing loop", inline=True)
label(0x8552, "filev_attrib_code_check")
comment(0x8555, "Load character from parameter string", inline=True)
comment(0x8557, "Advance to next character", inline=True)
comment(0x8558, "Compare against space (ASCII &20)", inline=True)
comment(0x855A, "Space found: keep scanning", inline=True)
comment(0x855C, "Back up one (first non-space char)", inline=True)
comment(0x855D, "Compare against 'A' for case flag", inline=True)
comment(0x855F, "Return: A=char, C set if >= 'A'", inline=True)
comment(0x8563, "Clear accumulator workspace", inline=True)
label(0x8565, "scan_decimal_digit")    # Read ASCII digits and accumulate decimal value
comment(0x8587, "Return with result in A", inline=True)
comment(0x85A2, "Restore X from stack", inline=True)
comment(0x85A4, "Return with mask in X", inline=True)
comment(0x85AE, "Return with A=handle number", inline=True)
comment(0x85AF, "Y=dividend, A=100: hundreds digit", inline=True)
comment(0x85BA, "Convert to ASCII and print", inline=True)
comment(0x85BC, "Store divisor in temporary", inline=True)
comment(0x85BE, "Transfer dividend (Y) to A", inline=True)
comment(0x85BF, "X=&2F: ASCII '0'-1 (loop init)", inline=True)
comment(0x85C1, "Set carry for subtraction", inline=True)
label(0x85C2, "decimal_divide_loop")
comment(0x85C2, "Increment digit (ASCII '0'..'9')", inline=True)
comment(0x85C3, "Subtract divisor from remainder", inline=True)
comment(0x85C5, "Carry set: subtract again", inline=True)
comment(0x85C7, "Add back divisor (undo last SBC)", inline=True)
comment(0x85C9, "Remainder to Y for next digit", inline=True)
comment(0x85CA, "Quotient digit (X) to A for print", inline=True)
label(0x85CB, "print_via_osasci")
comment(0x85D6, "Next byte", inline=True)
comment(0x85D9, "Return with Z flag result", inline=True)
comment(0x85DE, "Return (FSCV 7 read handles)", inline=True)
comment(0x85DF, "Invert A (NOT mask)", inline=True)
comment(0x85E1, "AND inverted mask to clear bits", inline=True)
comment(0x85E4, "OR mask into EOF flags", inline=True)
comment(0x85E7, "Store updated EOF flags", inline=True)
comment(0x85EA, "Return to caller", inline=True)
comment(0x85EB, "Save full byte on stack", inline=True)
comment(0x85EC, "Shift high nibble to low position", inline=True)
comment(0x85ED, "Continue shift (4 LSRs total)", inline=True)
comment(0x85EE, "Continue shift", inline=True)
comment(0x85EF, "High nibble now in bits 0-3", inline=True)
comment(0x85F0, "Print high nibble as hex", inline=True)
comment(0x85F3, "Restore original byte", inline=True)
comment(0x85F4, "Mask to low nibble", inline=True)
comment(0x85F6, "Convert to ASCII digit ('0'-'9')", inline=True)
comment(0x85F8, "Compare against ':' (past '9'?)", inline=True)
comment(0x85FA, "Digit 0-9: skip A-F adjustment", inline=True)
comment(0x85FC, "Add 7 to get ASCII 'A'-'F'", inline=True)
label(0x85FE, "print_hex_digit")
comment(0x85FE, "ALWAYS branch to print character", inline=True)
label(0x8607, "print_filename_loop")
comment(0x860B, "CR: pad rest of filename field", inline=True)
comment(0x860F, "Space: also ends filename", inline=True)
comment(0x8615, "Loop until all chars printed", inline=True)
comment(0x861B, "Pad to 12 chars wide", inline=True)
comment(0x8621, "Print load address as 2 hex bytes", inline=True)
comment(0x8633, "ALWAYS branch", inline=True)
comment(0x8635, "X=4: print 4 bytes for address", inline=True)
comment(0x863E, "Loop for remaining hex bytes", inline=True)
comment(0x8644, "X=&C0: TX control block at &00C0", inline=True)
comment(0x8646, "Set TX pointer lo", inline=True)
comment(0x8648, "X=0: page zero", inline=True)
comment(0x864A, "Set TX pointer hi", inline=True)
comment(0x864C, "A=&FF: full retry count", inline=True)
comment(0x8650, "Save retry count on stack", inline=True)
comment(0x8651, "Transfer timeout to A", inline=True)
comment(0x8652, "Save timeout on stack", inline=True)
comment(0x8653, "X=0 for (net_tx_ptr,X) indirect", inline=True)
comment(0x8655, "Load TXCB byte 0 (control/status)", inline=True)
label(0x8657, "tx_retry")             # Retry TX after error
comment(0x8657, "Write control byte to start TX", inline=True)
comment(0x8659, "Save control byte for retry", inline=True)
label(0x865A, "tx_semaphore_spin")    # TX semaphore spinlock
comment(0x865A, "Test TX semaphore (C=1 when free)", inline=True)
comment(0x865D, "Spin until semaphore released", inline=True)
comment(0x865F, "Copy TX ptr lo to NMI block", inline=True)
comment(0x8661, "Store for NMI handler access", inline=True)
comment(0x8663, "Copy TX ptr hi to NMI block", inline=True)
comment(0x8665, "Store for NMI handler access", inline=True)
comment(0x8667, "Initiate ADLC TX via trampoline", inline=True)
comment(0x866A, "Poll TXCB byte 0 for completion", inline=True)
comment(0x866C, "Bit 7 set: still busy, keep polling", inline=True)
comment(0x866E, "Shift bit 6 into bit 7 (error flag)", inline=True)
comment(0x866F, "Bit 6 clear: success, clean return", inline=True)
comment(0x8671, "Shift bit 5 into carry", inline=True)
comment(0x8672, "Zero: fatal error, no escape", inline=True)
comment(0x8674, "Check for user escape condition", inline=True)
comment(0x8677, "Discard saved control byte", inline=True)
comment(0x8678, "Save to X for retry delay", inline=True)
comment(0x8679, "Restore timeout parameter", inline=True)
comment(0x867A, "Back to Y", inline=True)
comment(0x867B, "Restore retry count", inline=True)
comment(0x867C, "No retries left: report error", inline=True)
comment(0x867E, "Decrement retry count", inline=True)
comment(0x8680, "Save updated retry count", inline=True)
comment(0x8681, "Timeout to A for delay", inline=True)
comment(0x8682, "Save timeout parameter", inline=True)
comment(0x8683, "Control byte for delay duration", inline=True)
comment(0x8684, "Inner delay loop", inline=True)
comment(0x8685, "Spin until X=0", inline=True)
comment(0x8687, "Outer delay loop", inline=True)
comment(0x8688, "Continue delay", inline=True)
label(0x868C, "tx_not_listening")     # Fatal TX error: "Not listening"
comment(0x868C, "Save error code in X", inline=True)
comment(0x868D, "Report 'Not listening' error", inline=True)
label(0x8690, "tx_success")           # TX success: clean return
comment(0x8690, "Discard saved control byte", inline=True)
comment(0x8691, "Discard timeout parameter", inline=True)
comment(0x8692, "Discard retry count", inline=True)
comment(0x8693, "Return (success)", inline=True)
comment(0x8694, "Load FILEV function code from A", inline=True)
subroutine(0x8697, "copy_filename_ptr", hook=None,
    title="Copy filename pointer to os_text_ptr and parse",
    description="""\
Copies the 2-byte filename pointer from (fs_options),Y into
os_text_ptr (&F2/&F3), then falls through to parse_filename_gs
to parse the filename via GSINIT/GSREAD into the &0E30 buffer.""")
label(0x86B3, "tx_result_check")
comment(0x86C6, "A=&FF: branch to load path", inline=True)
comment(0x86CB, "Copy parsed filename to cmd buffer", inline=True)
comment(0x86CE, "Y=2: FS function code offset", inline=True)
comment(0x86D5, "A=&2A: error ptr for retry", inline=True)
comment(0x8703, "Display file info after FS reply", inline=True)
comment(0x877E, "A=&14: FS function code for SAVE", inline=True)
comment(0x8780, "Build header and send FS save command", inline=True)
comment(0x8783, "Send file data blocks to server", inline=True)
label(0x8786, "save_csd_display")       # Save CSD from reply and display file info
comment(0x8786, "Save CSD from reply for catalogue display", inline=True)
comment(0x8789, "Print file length in hex", inline=True)
label(0x878C, "set_star_reply_port")
label(0x8790, "send_fs_reply")        # Sends FS reply command after transfer
comment(0x8790, "Send FS reply acknowledgement", inline=True)
comment(0x879E, "Z=1: first byte, use A directly", inline=True)
label(0x87A0, "copy_attr_loop")       # Copy 4 attribute bytes loop
comment(0x87A0, "Load attribute byte from FS reply", inline=True)
label(0x87A3, "direct_attr_copy")     # Skip attr decode, direct copy
comment(0x87A3, "Store decoded access in param block", inline=True)
comment(0x87A5, "Next attribute byte", inline=True)
comment(0x87C2, "Next byte (descending)", inline=True)
comment(0x87C5, "Loop until offset 2 reached", inline=True)
comment(0x87C7, "Return to caller", inline=True)
label(0x87CE, "next_block")           # Reinit for next transfer block
comment(0x87CE, "X=0: clear hi bytes of block size", inline=True)
comment(0x87D0, "Y=4: process 4 address bytes", inline=True)
comment(0x87D2, "Clear block size hi byte 1", inline=True)
comment(0x87D5, "Clear block size hi byte 2", inline=True)
comment(0x87D8, "CLC for ADC in loop", inline=True)
label(0x87D9, "block_addr_loop")      # Multi-byte address addition loop
comment(0x87D9, "Source = current position", inline=True)
comment(0x87DB, "Store source address byte", inline=True)
comment(0x87DD, "Add block size to current position", inline=True)
comment(0x87E8, "Carry: address overflowed, clamp", inline=True)
label(0x87F7, "clamp_dest_setup")     # Set up 4-byte dest clamping
comment(0x8818, "A=&2A: error ptr for retry", inline=True)
label(0x88DE, "argsv_zero_length")
label(0x8933, "argsv_dispatch_a")
comment(0x8933, "Transfer A to Y for test", inline=True)
comment(0x8934, "Non-zero: halve A", inline=True)
comment(0x8936, "A=5: default FS number", inline=True)
subroutine(0x8945, "return_a_zero", hook=None,
    title="Return with A=0 via register restore",
    description="""\
Loads A=0 and branches (always taken) to the common register
restore exit at restore_args_return. Used as a shared exit
point by ARGSV, FINDV, and GBPBV when an operation is
unsupported or should return zero.""")
label(0x89A9, "gbpbv_func_dispatch")
comment(0x89E9, "Return (unsupported function)", inline=True)
comment(0x8A6E, "Non-zero: branch past error ptr", inline=True)
label(0x8A70, "gbpb_read_path")      # BNE: non-zero read, skip write transfer
comment(0x8A70, "Read path: receive data blocks from FS", inline=True)
label(0x8A73, "findv_eof_check")
label(0x8BCC, "cmd_match_retry")
comment(0x8BD6, "XOR with '.' (abbreviation check)", inline=True)
comment(0x8BF2, "Pre-decrement Y for parameter", inline=True)
comment(0x8BF3, "X=1: boot option display field", inline=True)
comment(0x8BF5, "Store to fs_work_7 (&B7)", inline=True)
comment(0x8BF7, "X=&50: 80-column display width", inline=True)
comment(0x8BF9, "Store column width at &B6", inline=True)
label(0x8C07, "cat_init_display")
comment(0x8CA2, "Print two CRs (blank line)", inline=True)
label(0x8CAF, "count_columns_loop")
label(0x8CBA, "cat_examine_continue")
label(0x8CBC, "cat_examine_loop")      # Send examine request and display entries
comment(0x8CCB, "Load entry count from reply", inline=True)
comment(0x8CCE, "Zero entries returned: catalogue done", inline=True)
comment(0x8CD0, "X=2: first entry offset in reply", inline=True)
comment(0x8CD2, "Print/format this directory entry", inline=True)
comment(0x8CD5, "CLC for addition", inline=True)
comment(0x8CD6, "Load current examine start offset", inline=True)
comment(0x8CD8, "Add entries returned this batch", inline=True)
comment(0x8CDB, "Update next examine start offset", inline=True)
comment(0x8CDE, "Save updated start offset", inline=True)
comment(0x8CE0, "Reload batch size for next request", inline=True)
comment(0x8CE2, "Store batch size in command buffer", inline=True)
comment(0x8CE5, "Loop for remaining characters", inline=True)
comment(0x8CFC, "Store Y (CSD handle) to &0E03", inline=True)
label(0x8CFF, "set_handle_return")
comment(0x8CFF, "Jump to restore_args_return", inline=True)
label(0x8D16, "fsreply_handle_copy")
comment(0x8D4B, "Offset 0 (BRK opcode as zero byte)", inline=True)
comment(0x8D4F, "Y=10: default character count", inline=True)
comment(0x8D51, "Load character from reply buffer", inline=True)
comment(0x8D57, "Advance to next character", inline=True)
comment(0x8D58, "Decrement remaining count", inline=True)
comment(0x8D59, "Loop until count exhausted", inline=True)
comment(0x8D5B, "Return to caller", inline=True)
comment(0x8D5C, "Print one space character", inline=True)
comment(0x8D5F, "Decrement space count", inline=True)
comment(0x8D60, "Loop until all spaces printed", inline=True)
comment(0x8D62, "Return to caller", inline=True)
comment(0x8D63, "X=0: start of output buffer", inline=True)
comment(0x8D72, "Return to caller", inline=True)
comment(0x8D73, "X=0: start of reply buffer", inline=True)
comment(0x8D75, "Load character from reply", inline=True)
comment(0x8D78, "Bit 7 set: end of string", inline=True)
comment(0x8D7A, "Non-zero: printable character", inline=True)
comment(0x8D7C, "Replace null with CR", inline=True)
comment(0x8D81, "Advance to next character", inline=True)
comment(0x8D82, "Continue printing directory path", inline=True)
comment(0x8D84, "X=&0E: OSWORD &10 parameter block size", inline=True)
comment(0x8D86, "Y=0: param block offset", inline=True)
comment(0x8D88, "A=&10: OSWORD &10 (open RXCB)", inline=True)
comment(0x8D8A, "Issue OSWORD &10 to open RXCB", inline=True)
comment(0x8D93, "Y=&70: FS workspace offset", inline=True)
comment(0x8D9E, "Store final byte", inline=True)
comment(0x8DA0, "X=&16: OSBYTE param", inline=True)
comment(0x8DA7, "Save original value on stack", inline=True)
label(0x8DAC, "net_handle_validate")
comment(0x8DAF, "Y=&6F: handle offset in RX buffer", inline=True)
comment(0x8DB1, "Load handle byte from RX data", inline=True)
comment(0x8DB3, "Store handle to &F0", inline=True)
comment(0x8DB5, "Branch to cleanup path", inline=True)
comment(0x8DC8, "Return after calculation", inline=True)
label(0x8DDA, "clear_svc_return")
comment(0x8DE6, "Preserve carry via ROL", inline=True)
comment(0x8DE9, "&3F = '?' marks slot as unused", inline=True)
comment(0x8DEB, "Mark handle as closed in workspace", inline=True)
label(0x8DED, "restore_rx_flags")
subroutine(0x8DED, "restore_rx_flags", hook=None,
    title="Restore RX flags after close handle",
    description="""\
Performs ROR on rx_flags to restore the carry flag state
that was preserved by the matching ROL in net_3_close_handle.
Falls through to osword_12_handler (clearing fs_temp_ce).""")
comment(0x8DED, "Restore carry via ROR", inline=True)
comment(0x8DF0, "C=0: branch to cleanup exit", inline=True)
comment(0x8DF2, "Jump to clear_svc_restore_args", inline=True)
comment(0x8DF5, "Enable remote operations flag", inline=True)
comment(0x8DFB, "Outside our OSWORD range, exit", inline=True)
comment(0x8E01, "X = sub-function code for table lookup", inline=True)
comment(0x8E17, "RTS dispatches to pushed handler", inline=True)
label(0x8E2A, "load_workspace_byte")   # Load byte from workspace (C=0 skip-copy path)
comment(0x8E2C, "Store to param block (no-op if C=1)", inline=True)
comment(0x8E32, "Return after copy", inline=True)
comment(0x8E33, "ASL: set C if TX in progress", inline=True)
comment(0x8E36, "C=0: read path", inline=True)
label(0x8E4F, "osword_12_subfunc")
label(0x8E79, "osword_12_ws_offsets")
label(0x8EAC, "set_carry_dispatch")
label(0x8EAF, "read_local_station")
label(0x8EDB, "osword_12_error")
label(0x8EE1, "carry_exit_or_read")
label(0x8EFD, "scan_or_read_rxcb")
label(0x8F48, "clear_svc_restore_args")
subroutine(0x8F48, "clear_svc_restore_args", hook=None,
    title="Clear service number and restore OSWORD args",
    description="""\
Shared exit for OSWORD handlers. Zeros rom_svc_num to
release the service claim, then copies 3 bytes from
(net_rx_ptr) back to the fs_last_byte_flag area,
restoring the OSWORD argument state saved at entry.""")
comment(0x8F48, "Y=0: clear service claim", inline=True)
comment(0x8F4A, "Release ROM service number", inline=True)
comment(0x8F4E, "Load saved arg from (net_rx_ptr)+Y", inline=True)
comment(0x8F50, "Restore saved OSWORD argument byte", inline=True)
comment(0x8F53, "Decrement byte counter", inline=True)
comment(0x8F54, "Loop for bytes 2,1,0", inline=True)
comment(0x8F56, "Return to caller", inline=True)
comment(0x8F57, "Y=&28: RXCB template offset", inline=True)
comment(0x8F94, "Y=&04: advance to station address", inline=True)
comment(0x8FDD, "Y=&7D: store byte for TX at offset &7D", inline=True)
comment(0x8FDF, "Store data byte at (net_rx_ptr)+&7D for TX", inline=True)
comment(0x8FE1, "Save data byte for &0D check after TX", inline=True)
comment(0x8FE2, "Set up TX control block", inline=True)
comment(0x8FE5, "Enable interrupts for TX", inline=True)
comment(0x8FE6, "Enable IRQs and transmit", inline=True)
label(0x8FE9, "delay_between_tx")      # Spin-delay between consecutive TX packets
comment(0x8FE9, "Short delay loop between TX packets", inline=True)
comment(0x8FEA, "Spin until X reaches 0", inline=True)
comment(0x8FEC, "Restore data byte for terminator check", inline=True)
comment(0x8FED, "Z=1: not intercepted, pass through", inline=True)
label(0x8FF3, "rx_first_packet")
subroutine(0x9000, "enable_irq_and_tx", hook=None,
    title="Enable interrupts and transmit via tx_poll_ff",
    description="""\
CLI to enable interrupts, then JMP tx_poll_ff. A short
tail-call wrapper used after building the TX control block.""")
label(0x9004, "jmp_clear_svc_restore")
comment(0x909A, "Write &7F to RXCB (wait for reply)", inline=True)
label(0x909C, "poll_rxcb_loop")       # Poll RXCB for OSBYTE reply
comment(0x909C, "Poll RXCB for completion (bit7)", inline=True)
comment(0x90FC, "Y=4: RX control block byte 4", inline=True)
comment(0x90FE, "Load first data byte from RX", inline=True)
comment(0x9100, "Zero: standard boot, skip code", inline=True)
comment(0x9102, "Load language ROM number", inline=True)
comment(0x9110, "Non-zero: remote boot handler", inline=True)
comment(0x9117, "A=2: OSBYTE function code", inline=True)
comment(0x9119, "Copy command to &0100 area", inline=True)
comment(0x911E, "Y=0: command string high byte", inline=True)
comment(0x912A, "X=2: zero 3 bytes (offsets 2,1,0)", inline=True)
comment(0x912C, "A=0: zero / BRK opcode", inline=True)
label(0x912E, "zero_0100_loop")
comment(0x912E, "Store zero at &0100+X", inline=True)
comment(0x9131, "Decrement byte counter", inline=True)
comment(0x9132, "Loop until 3 bytes zeroed", inline=True)
comment(0x9134, "Release JSR protection mask", inline=True)
comment(0x9137, "Execute downloaded code at &0100", inline=True)
comment(0x913A, "Y=4: validation byte offset", inline=True)
comment(0x913C, "Load validation byte from RX data", inline=True)
comment(0x913E, "Zero: validation passed, continue", inline=True)
comment(0x9140, "Y=&80: source station offset", inline=True)
comment(0x9142, "Load source station from RX buffer", inline=True)
comment(0x9144, "Y=&0E: controlling station offset", inline=True)
comment(0x9146, "Compare with controlling station", inline=True)
comment(0x9148, "Mismatch: reject remote command", inline=True)
comment(0x914A, "Y=&82: character offset in RX data", inline=True)
comment(0x914C, "Load remote keypress character", inline=True)
comment(0x914E, "Transfer character to Y", inline=True)
comment(0x914F, "X=0: keyboard input buffer", inline=True)
comment(0x9151, "Release JSR protection before call", inline=True)
comment(0x9154, "A=&99: OSBYTE insert into buffer", inline=True)
comment(0x9176, "V=1: use (net_rx_ptr) page", inline=True)
comment(0x9178, "V=1: skip to net_rx_ptr page", inline=True)
comment(0x917A, "V=0: use (nfs_workspace) page", inline=True)
label(0x917C, "rxcb_matched")         # Scout frame matched RXCB
comment(0x9188, "Loop until all template bytes done", inline=True)
comment(0x918B, "Store final offset as net_tx_ptr", inline=True)
comment(0x91C3, "Store initial PFLAGS value", inline=True)
comment(0x91F6, "Decrement transfer count low byte", inline=True)
comment(0x91FC, "Check if both bytes zero", inline=True)
comment(0x9202, "Tube active: send via R3", inline=True)
comment(0x9205, "Decrement Tube count low", inline=True)
label(0x920B, "rx_imm_discard")
label(0x920E, "rx_data_phase")
comment(0x922F, "Load current PFLAGS", inline=True)
comment(0x9232, "Save current PFLAGS", inline=True)
comment(0x9233, "Carry = current sequence (bit 7)", inline=True)
comment(0x9234, "Restore original PFLAGS", inline=True)
comment(0x9235, "Toggle sequence number (bit 7 of PFLAGS)", inline=True)
comment(0x9237, "Store toggled sequence number", inline=True)
comment(0x9289, "Transfer count to X", inline=True)
comment(0x928A, "Test for retry exhaustion", inline=True)
comment(0x928B, "X wrapped to 0: retries exhausted", inline=True)
comment(0x9303, "Return after storing result", inline=True)
comment(0x9660, "Trampoline: forward to tx_begin", inline=True)
comment(0x9663, "Trampoline: forward to adlc_init", inline=True)
comment(0x9666, "Trampoline: forward to NMI release", inline=True)
comment(0x9669, "Trampoline: forward to NMI claim", inline=True)
comment(0x966C, "Trampoline: forward to IRQ handler", inline=True)
comment(0x9694, "A=0: clear source network", inline=True)
comment(0x9696, "Clear TX source network byte", inline=True)
comment(0x9699, "INTON: re-enable NMIs (&FE20 read side effect)", inline=True)
comment(0x969C, "Return to caller", inline=True)
comment(0x969D, "INTOFF: disable NMIs for state save", inline=True)
comment(0x96A0, "Y=8: RXCB offset for rx_status_flags", inline=True)
comment(0x96A2, "Load rx_status_flags", inline=True)
comment(0x96A5, "Store to RXCB offset 8", inline=True)
comment(0x96A8, "Load prot_status", inline=True)
comment(0x96AB, "Store to RXCB offset 9", inline=True)
comment(0x96B4, "INTOFF: disable NMIs for state restore", inline=True)
comment(0x96B9, "Load saved rx_status_flags from RXCB", inline=True)
comment(0x96BB, "Restore rx_status_flags", inline=True)
comment(0x96C1, "Restore prot_status", inline=True)
comment(0x96C4, "Load saved tx_in_progress from RXCB", inline=True)
label(0x96D1, "poll_nmi_complete")
comment(0x96DE, "Write CR1: full reset", inline=True)
comment(0x96E3, "Write CR4 via ADLC reg 3 (AC=1)", inline=True)
comment(0x96E8, "Write CR3=0: clear loop-back/AEX/DTR", inline=True)
comment(0x96ED, "Write CR1: RIE | TX_RESET", inline=True)
comment(0x96F2, "Write CR2: listen mode config", inline=True)
comment(0x970B, "Store broadcast flag in TX flags", inline=True)
comment(0x9710, "High byte of scout net handler", inline=True)
comment(0x9712, "Install next handler and RTI", inline=True)
comment(0x9725, "Write CR1 to discontinue RX", inline=True)
comment(0x9728, "Return to idle scout listening", inline=True)
comment(0x9732, "High byte of scout data handler", inline=True)
comment(0x9734, "Install scout data loop and RTI", inline=True)
comment(0x9744, "Gentle discard: RX_DISCONTINUE", inline=True)
comment(0x9763, "Copied all 12 scout bytes?", inline=True)
comment(0x9767, "Save final buffer offset", inline=True)
label(0x97AB, "scan_nfs_port_list")   # NFS workspace port list scan entry
comment(0x97AB, "Store page to workspace pointer low", inline=True)
comment(0x97AD, "A=0: no NFS workspace offset yet", inline=True)
comment(0x97AF, "Clear NFS workspace search flag", inline=True)
label(0x97B3, "scout_ctrl_check")     # Check scout control byte
comment(0x97BB, "Y=1: advance to port byte in slot", inline=True)
label(0x97CF, "scout_port_match")     # Check scout port number
comment(0x97D9, "CLC for 12-byte slot advance", inline=True)
comment(0x97DA, "Advance to next 12-byte port slot", inline=True)
comment(0x97DC, "Update workspace pointer to next slot", inline=True)
comment(0x97DE, "Always branches (page &C0 won't overflow)", inline=True)
label(0x97E0, "scout_station_check")  # Check scout station number
comment(0x97E0, "Check if NFS workspace already searched", inline=True)
comment(0x97E2, "Already searched: no match found", inline=True)
label(0x97E4, "scout_network_match")  # Check scout network number
comment(0x97E4, "Try NFS workspace if paged list exhausted", inline=True)
comment(0x97E7, "No NFS workspace RX (bit6 clear) -- discard", inline=True)
comment(0x97E9, "Get NFS workspace page number", inline=True)
comment(0x97EB, "Mark NFS workspace as search target", inline=True)
comment(0x97ED, "Y=0: start at offset 0 in workspace", inline=True)
comment(0x97EF, "Reset slot pointer to start", inline=True)
label(0x97F3, "scout_accept")         # Scout accepted: all checks passed
comment(0x97F3, "Check broadcast flag (bit 6)", inline=True)
comment(0x97F6, "Not broadcast: ACK and set up RX", inline=True)
comment(0x97F8, "Broadcast: copy scout fields directly", inline=True)
label(0x97FB, "ack_scout_match")      # Sets scout_status=3, initiates ACK
comment(0x97FB, "Match found: set scout_status = 3", inline=True)
comment(0x97FD, "Record match for completion handler", inline=True)
comment(0x9800, "Save current TX block ptr (low)", inline=True)
comment(0x9802, "Push TX block low on stack", inline=True)
comment(0x9803, "Save current TX block ptr (high)", inline=True)
comment(0x9805, "Push TX block high on stack", inline=True)
comment(0x9806, "Use port slot as temp RXCB ptr (lo)", inline=True)
comment(0x9808, "Set RXCB low for tx_calc_transfer", inline=True)
comment(0x980A, "Use workspace page as temp RXCB (hi)", inline=True)
comment(0x980C, "Set RXCB high for tx_calc_transfer", inline=True)
comment(0x980E, "Calculate transfer parameters", inline=True)
comment(0x9811, "Restore original TX block (high)", inline=True)
comment(0x9812, "Restore TX block ptr (high)", inline=True)
comment(0x9814, "Restore original TX block (low)", inline=True)
comment(0x9815, "Restore TX block ptr (low)", inline=True)
comment(0x9817, "Transfer OK: send data ACK", inline=True)
comment(0x9834, "High byte of nmi_data_rx handler", inline=True)
comment(0x984A, "High byte of nmi_data_rx handler", inline=True)
subroutine(0x9870, "install_data_rx_handler", hook=None,
    title="Install data RX bulk or Tube handler",
    description="""\
Selects either the normal bulk RX handler (&989A) or the Tube
RX handler (&98F7) based on the Tube transfer flag in tx_flags,
and installs the appropriate NMI handler.""")
comment(0x988F, "A=&41: 'not listening' error", inline=True)
comment(0x98FF, "Advance Tube transfer byte count", inline=True)
comment(0x9901, "Send byte to Tube data register 3", inline=True)
comment(0x9904, "No overflow: read second byte", inline=True)
comment(0x9906, "Carry to transfer count byte 2", inline=True)
comment(0x9908, "No overflow: read second byte", inline=True)
comment(0x990A, "Carry to transfer count byte 3", inline=True)
comment(0x990C, "No overflow: read second byte", inline=True)
comment(0x990E, "Carry to transfer count byte 4", inline=True)
comment(0x9910, "All bytes zero: overflow error", inline=True)
label(0x9912, "rx_update_buf")        # Update buffer pointer after RX
comment(0x9912, "Read second data byte (paired transfer)", inline=True)
comment(0x9915, "Send second byte to Tube", inline=True)
comment(0x9918, "Advance count after second byte", inline=True)
comment(0x991A, "No overflow: check for more data", inline=True)
comment(0x991C, "Carry to count byte 2", inline=True)
comment(0x991E, "No overflow: check for more data", inline=True)
comment(0x9920, "Carry to count byte 3", inline=True)
comment(0x9922, "No overflow: check for more data", inline=True)
comment(0x9924, "Carry to count byte 4", inline=True)
comment(0x9926, "Zero: Tube transfer complete", inline=True)
label(0x9928, "rx_check_error")       # Check error status after data RX
comment(0x9928, "Re-read SR2 for next byte pair", inline=True)
comment(0x992B, "More data available: continue loop", inline=True)
comment(0x992D, "Return from NMI, wait for data", inline=True)
comment(0x999F, "Write network=0 (local) to TX FIFO", inline=True)
comment(0x99A2, "Check tx_flags for data phase", inline=True)
comment(0x99A5, "bit7 set: start data TX phase", inline=True)
label(0x99B8, "tdra_error")            # JMP nmi_error_dispatch (TDRA not ready)
comment(0x99B8, "TDRA error: jump to error handler", inline=True)
comment(0x99BB, "Check port byte from scout", inline=True)
comment(0x99BE, "Non-zero port: advance RX buffer", inline=True)
subroutine(0x99C3, "advance_rx_buffer_ptr", hook=None,
    title="Advance RX buffer pointer after transfer",
    description="""\
Adds the transfer count to the RXCB buffer pointer (4-byte
addition). If a Tube transfer is active, re-claims the Tube
address and sends the extra RX byte via R3, incrementing the
Tube pointer by 1.""")
comment(0x99F9, "Restore X from stack", inline=True)
comment(0x99FA, "Transfer to X register", inline=True)
comment(0x99FB, "Y=8: RXCB buffer ptr offset", inline=True)
comment(0x99FD, "Load current RXCB buffer ptr lo", inline=True)
comment(0x99FF, "SEC for ADC #0 = add carry", inline=True)
comment(0x9A00, "Increment by 1 (Tube extra byte)", inline=True)
comment(0x9A02, "Store updated ptr back to RXCB", inline=True)
label(0x9A04, "jmp_store_rxcb")
comment(0x9A04, "Other port-0 ops: immediate dispatch", inline=True)
label(0x9A07, "add_buf_to_base")       # Add buffer length to base address (no Tube)
label(0x9A0E, "inc_rxcb_buf_hi")      # Increments RXCB buffer high byte
label(0x9A12, "store_rxcb_buf_ptr")  # Store updated buffer pointer pair to RXCB
label(0x9A15, "load_rxcb_buf_hi")
label(0x9A17, "store_rxcb_buf_hi")    # Stores buffer hi byte to RXCB offset 9
label(0x9A19, "store_rxcb_completion")
subroutine(0x9A19, "store_rxcb_completion", hook=None,
    title="Store RXCB completion fields from scout buffer",
    description="""\
Writes source network, source station, port, and control
byte from the scout buffer into the active RXCB. Sets
bit 7 of the control byte to mark reception complete.""")
comment(0x9A36, "Test tx_flags for Tube transfer", inline=True)
comment(0x9A3B, "A=&82: Tube release claim type", inline=True)
label(0x9A4A, "copy_scout_fields")    # Copies scout fields to port workspace
comment(0x9A4A, "Y=4: start at RX CB offset 4", inline=True)
label(0x9A4C, "copy_scout_loop")      # Copy 8 scout fields to workspace
comment(0x9A4C, "Load scout field (stn/net/ctrl/port)", inline=True)
comment(0x9A4F, "Store to port workspace buffer", inline=True)
comment(0x9A51, "Next field", inline=True)
comment(0x9A52, "All 8 fields copied?", inline=True)
comment(0x9A54, "No page crossing", inline=True)
comment(0x9A56, "Jump to completion handler", inline=True)
comment(0x9A68, "Load source station number", inline=True)
comment(0x9A6B, "Station >= &F0? (privileged)", inline=True)
comment(0x9A6D, "Privileged: skip protection check", inline=True)
comment(0x9A7B, "Carry clear: operation permitted", inline=True)
comment(0x9A7D, "Operation blocked by LSTAT mask", inline=True)
label(0x9A80, "imm_op_dispatch")      # PHA/PHA/RTS dispatch for immediate ops
comment(0x9A80, "Reload ctrl byte for dispatch table", inline=True)
comment(0x9A83, "Look up handler address high byte", inline=True)
comment(0x9A86, "Push &9A as dispatch high byte", inline=True)
comment(0x9A87, "Load handler low byte from jump table", inline=True)
comment(0x9A8A, "Push handler low byte", inline=True)
comment(0x9A8B, "RTS dispatches to handler", inline=True)
label(0x9A8C, "imm_op_out_of_range")  # JMP nmi_error_dispatch
comment(0x9A8C, "Jump to discard handler", inline=True)
comment(0x9A9F, "Buffer start lo = &00", inline=True)
comment(0x9AA1, "Set port buffer lo", inline=True)
comment(0x9AA3, "Buffer length lo = &82", inline=True)
comment(0x9AA5, "Set buffer length lo", inline=True)
comment(0x9AA7, "Buffer length hi = 1", inline=True)
comment(0x9AA9, "Set buffer length hi", inline=True)
comment(0x9AAB, "Load RX page hi for buffer", inline=True)
comment(0x9AAD, "Set port buffer hi", inline=True)
comment(0x9AAF, "Y=3: copy 4 bytes (3 down to 0)", inline=True)
label(0x9AB1, "copy_addr_loop")       # Copy 4-byte remote address loop
comment(0x9AB1, "Load remote address byte", inline=True)
comment(0x9AB4, "Store to exec address workspace", inline=True)
comment(0x9AB7, "Next byte (descending)", inline=True)
comment(0x9AB8, "Loop until all 4 bytes copied", inline=True)
comment(0x9ABA, "Enter common data-receive path", inline=True)
comment(0x9ABD, "Port workspace offset = &3D", inline=True)
comment(0x9ABF, "Store workspace offset lo", inline=True)
comment(0x9AC1, "RX buffer page = &0D", inline=True)
comment(0x9AC3, "Store workspace offset hi", inline=True)
comment(0x9AC5, "Enter POKE data-receive path", inline=True)
comment(0x9AC8, "Buffer length hi = 1", inline=True)
comment(0x9ACA, "Set buffer length hi", inline=True)
comment(0x9ACC, "Buffer length lo = &FC", inline=True)
comment(0x9ACE, "Set buffer length lo", inline=True)
comment(0x9AD0, "Buffer start lo = &25", inline=True)
comment(0x9AD2, "Set port buffer lo", inline=True)
comment(0x9AD4, "Buffer hi = &7F (below screen)", inline=True)
comment(0x9AD6, "Set port buffer hi", inline=True)
comment(0x9AD8, "Enter reply build path", inline=True)
comment(0x9ADB, "Save current TX block low byte", inline=True)
comment(0x9ADD, "Push to stack", inline=True)
comment(0x9ADE, "Save current TX block high byte", inline=True)
comment(0x9AE0, "Push to stack", inline=True)
comment(0x9AE1, "Port workspace offset = &3D", inline=True)
comment(0x9AE3, "Store workspace offset lo", inline=True)
comment(0x9AE5, "RX buffer page = &0D", inline=True)
comment(0x9AE7, "Store workspace offset hi", inline=True)
comment(0x9AE9, "Scout status = 2 (PEEK response)", inline=True)
comment(0x9AEB, "Store scout status", inline=True)
comment(0x9AEE, "Calculate transfer size for response", inline=True)
comment(0x9AF1, "Restore saved nmi_tx_block_hi", inline=True)
comment(0x9AF2, "Restore workspace ptr hi byte", inline=True)
comment(0x9AF4, "Restore saved nmi_tx_block", inline=True)
comment(0x9AF5, "Restore workspace ptr lo byte", inline=True)
comment(0x9AF7, "C=0: transfer not set up, discard", inline=True)
label(0x9AF9, "set_tx_reply_flag")    # Sets TX reply-pending flag (bit7)
comment(0x9AF9, "Mark TX flags bit 7 (reply pending)", inline=True)
comment(0x9AFC, "Set reply pending flag", inline=True)
comment(0x9AFE, "Store updated TX flags", inline=True)
label(0x9B01, "rx_imm_halt_cont")     # Handler for HALT/CONTINUE immediate ops
comment(0x9B01, "CR1=&44: TIE | TX_LAST_DATA", inline=True)
comment(0x9B03, "Write CR1: enable TX interrupts", inline=True)
label(0x9B06, "tx_cr2_setup")         # Self-modifying CR2 configuration
comment(0x9B06, "CR2=&A7: RTS|CLR_RX_ST|FC_TDRA|PSE", inline=True)
comment(0x9B08, "Write CR2 for TX setup", inline=True)
label(0x9B0B, "tx_nmi_setup")         # Self-modifying NMI handler lo byte
comment(0x9B0B, "NMI handler lo byte (self-modifying)", inline=True)
label(0x9B0D, "tx_nmi_dispatch_page")
comment(0x9B0D, "Y=&9B: dispatch table page", inline=True)
comment(0x9B0F, "Acknowledge and write TX dest", inline=True)
label(0x9B12, "check_imm_op_ctrl")
subroutine(0x9B12, "check_imm_op_ctrl", hook=None,
    title="Check control byte for immediate operation type",
    description="""\
Loads the RX control byte and compares against &82
(immediate HALT). If HALT, discards the frame via
imm_op_discard. Otherwise falls through to
imm_op_build_reply.""")
comment(0x9B12, "Load RX control byte", inline=True)
comment(0x9B15, "Compare against &82 (HALT)", inline=True)
comment(0x9B17, "HALT: discard frame", inline=True)
subroutine(0x9B19, "imm_op_build_reply", hook=None,
    title="Build immediate operation reply header",
    description="""\
Stores data length, source station/network, and control byte
into the RX buffer header area for port-0 immediate operations.
Then disables SR interrupts and configures the VIA shift
register for shift-in mode before returning to
idle listen.""")
label(0x9B4F, "imm_op_discard")       # Error path: JMP discard_listen
label(0x9B52, "check_sr_irq")         # Tests SR interrupt pending via IFR
comment(0x9B52, "A=&04: IFR bit 2 (SR) mask", inline=True)
comment(0x9B54, "Test SR interrupt pending", inline=True)
comment(0x9B57, "SR fired: handle TX completion", inline=True)
comment(0x9B59, "A=5: no SR, return status 5", inline=True)
comment(0x9B5B, "Return (no SR interrupt)", inline=True)
label(0x9B5C, "tx_done_error")        # TX error code check
comment(0x9B5C, "Save X", inline=True)
comment(0x9B5D, "Push X", inline=True)
comment(0x9B5E, "Save Y", inline=True)
comment(0x9B5F, "Push Y", inline=True)
comment(0x9B60, "Read ACR for shift register mode", inline=True)
comment(0x9B63, "Clear SR mode bits (2-4)", inline=True)
comment(0x9B65, "Restore original SR mode", inline=True)
comment(0x9B68, "Write updated ACR", inline=True)
comment(0x9B6B, "Read SR to clear pending interrupt", inline=True)
comment(0x9B6E, "A=&04: SR bit mask", inline=True)
comment(0x9B70, "Clear SR in IFR", inline=True)
comment(0x9B73, "Disable SR in IER", inline=True)
comment(0x9B76, "Load ctrl byte for dispatch", inline=True)
comment(0x9B79, "Ctrl >= &86? (HALT/CONTINUE)", inline=True)
comment(0x9B7B, "Yes: skip protection mask save", inline=True)
comment(0x9B7D, "Load current protection mask", inline=True)
comment(0x9B80, "Save mask before JSR modification", inline=True)
comment(0x9B83, "Enable bits 2-4 (allow JSR ops)", inline=True)
comment(0x9B85, "Store modified protection mask", inline=True)
label(0x9B88, "tx_done_classify")     # TX operation type classification
comment(0x9B88, "Load handler addr hi from table", inline=True)
comment(0x9B8B, "Push handler hi", inline=True)
comment(0x9B8C, "Load handler addr lo from table", inline=True)
comment(0x9B8F, "Push handler lo", inline=True)
comment(0x9B90, "Dispatch via RTS (addr-1 on stack)", inline=True)
comment(0x9B9B, "Push hi of (tx_done_exit-1)", inline=True)
comment(0x9B9D, "Push hi byte on stack", inline=True)
comment(0x9B9E, "Push lo of (tx_done_exit-1)", inline=True)
comment(0x9BA0, "Push lo byte on stack", inline=True)
comment(0x9BA1, "Call remote JSR; RTS to tx_done_exit", inline=True)
comment(0x9BA4, "Y=8: network event type", inline=True)
comment(0x9BA6, "X = remote address lo", inline=True)
comment(0x9BA9, "A = remote address hi", inline=True)
comment(0x9BAF, "Exit TX done handler", inline=True)
comment(0x9BB2, "X = remote address lo", inline=True)
comment(0x9BB5, "Y = remote address hi", inline=True)
comment(0x9BB8, "Call ROM entry point at &8000", inline=True)
comment(0x9BBB, "Exit TX done handler", inline=True)
comment(0x9BBE, "A=&04: bit 2 mask for rx_flags", inline=True)
comment(0x9BC0, "Test if already halted", inline=True)
comment(0x9BC3, "Already halted: skip to exit", inline=True)
comment(0x9BC5, "Set bit 2 in rx_flags", inline=True)
comment(0x9BC8, "Store halt flag", inline=True)
comment(0x9BCB, "A=4: re-load halt bit mask", inline=True)
comment(0x9BCD, "Enable interrupts during halt wait", inline=True)
label(0x9BCE, "halt_spin_loop")       # Spin-wait during system halt state
comment(0x9BCE, "Test halt flag", inline=True)
comment(0x9BD1, "Still halted: keep spinning", inline=True)
comment(0x9BD5, "Load current RX flags", inline=True)
comment(0x9BD8, "Clear bit 2: release halted station", inline=True)
comment(0x9BDA, "Store updated flags", inline=True)
comment(0x9BDD, "Restore Y from stack", inline=True)
comment(0x9BDE, "Transfer to Y register", inline=True)
comment(0x9BDF, "Restore X from stack", inline=True)
comment(0x9BE0, "Transfer to X register", inline=True)
comment(0x9BE1, "A=0: success status", inline=True)
comment(0x9BE3, "Return with A=0 (success)", inline=True)
subroutine(0x9BE4, "tx_begin", hook=None,
    title="Begin TX operation",
    description="""\
Main TX initiation entry point (called via trampoline at &06CE).
Copies dest station/network from the TXCB to the scout buffer,
dispatches to immediate op setup (ctrl >= &81) or normal data
transfer, calculates transfer sizes, copies extra parameters,
then enters the INACTIVE polling loop.""")
comment(0x9C13, "(continued)", inline=True)
comment(0x9C14, "(continued)", inline=True)
comment(0x9C15, "(continued)", inline=True)
comment(0x9C1C, "Y += 5: advance to next end byte", inline=True)
comment(0x9C1D, "(continued)", inline=True)
comment(0x9C1E, "(continued)", inline=True)
comment(0x9C1F, "(continued)", inline=True)
comment(0x9C20, "(continued)", inline=True)
label(0x9C27, "check_imm_range")       # Check if ctrl byte is in immediate op range
comment(0x9C48, "Save TX index", inline=True)
comment(0x9C4B, "Push timeout byte 1 on stack", inline=True)
comment(0x9C4C, "Push timeout byte 2 on stack", inline=True)
comment(0x9C51, "Save interrupt state", inline=True)
comment(0x9C52, "Disable interrupts for ADLC access", inline=True)
subroutine(0x9C53, "intoff_test_inactive", hook=None,
    title="Disable NMIs and test INACTIVE",
    description="""\
Mid-instruction label within the INACTIVE polling loop.
sr2_test_operand is the self-modifying target for patching
the SR2 test. Disables NMIs twice (belt-and-braces) then
tests SR2 for INACTIVE before proceeding with TX.""")
label(0x9C59, "test_line_idle")       # Tests SR2 INACTIVE bit for line idle
comment(0x9C63, "Write CR2: clear status, prepare TX", inline=True)
comment(0x9C70, "Restore interrupt state", inline=True)
comment(0x9C72, "Increment timeout counter byte 1", inline=True)
comment(0x9C75, "Not overflowed: retry INACTIVE test", inline=True)
comment(0x9C77, "Increment timeout counter byte 2", inline=True)
comment(0x9C7A, "Not overflowed: retry INACTIVE test", inline=True)
comment(0x9C7C, "Increment timeout counter byte 3", inline=True)
comment(0x9C7F, "Not overflowed: retry INACTIVE test", inline=True)
comment(0x9C81, "All 3 bytes overflowed: line jammed", inline=True)
comment(0x9C84, "CR1=&44: TIE | TX_LAST_DATA", inline=True)
comment(0x9C8E, "Pop saved register", inline=True)
comment(0x9C8F, "Pop saved register", inline=True)
comment(0x9CCB, "Load handler from dispatch table", inline=True)
comment(0x9CCE, "Push high byte for PHA/PHA/RTS dispatch", inline=True)
comment(0x9CCF, "Look up handler address low from table", inline=True)
comment(0x9CD2, "Push low byte for PHA/PHA/RTS dispatch", inline=True)
comment(0x9CD3, "RTS dispatches to control-byte handler", inline=True)
label(0x9CE4, "imm_op_status3")       # Loads scout_status=3 for immediate ops
comment(0x9CE4, "A=3: scout_status for PEEK", inline=True)
comment(0x9CE8, "A=3: scout_status for PEEK op", inline=True)
comment(0x9CEC, "Scout status = 2 (POKE transfer)", inline=True)
label(0x9CEE, "store_status_add4")    # Stores scout status + 4-byte addition
comment(0x9CEE, "Store scout status", inline=True)
comment(0x9CF1, "Clear carry for 4-byte addition", inline=True)
comment(0x9CF2, "Save carry on stack", inline=True)
comment(0x9CF3, "Y=&0C: start at offset 12", inline=True)
label(0x9CF5, "add_bytes_loop")       # 4-byte address addition loop
comment(0x9CF5, "Load workspace address byte", inline=True)
comment(0x9CF8, "Restore carry from previous byte", inline=True)
comment(0x9CF9, "Add TXCB address byte", inline=True)
comment(0x9CFB, "Store updated address byte", inline=True)
comment(0x9CFE, "Next byte", inline=True)
comment(0x9CFF, "Save carry for next addition", inline=True)
comment(0x9D00, "Compare Y with 16-byte boundary", inline=True)
comment(0x9D02, "Below boundary: continue addition", inline=True)
comment(0x9D04, "Restore processor flags", inline=True)
comment(0x9D05, "Calculate transfer byte count", inline=True)
comment(0x9D08, "Jump to TX control exit", inline=True)
comment(0x9D0B, "A=2: scout_status for procedure ops", inline=True)
label(0x9D0D, "store_status_calc_xfer")  # Store scout_status, calculate transfer, exit
comment(0x9D0D, "Store scout status", inline=True)
comment(0x9D10, "Calculate transfer parameters", inline=True)
comment(0x9D13, "Exit TX ctrl setup", inline=True)
label(0x9D3D, "proc_op_status2")      # Loads scout_status=2 for proc calls
label(0x9D3F, "store_status_copy_ptr")  # Stores status + copies TX block ptr
comment(0x9D5A, "Next TX buffer byte", inline=True)
comment(0x9D5B, "Load second byte from TX buffer", inline=True)
comment(0x9D5E, "Advance TX index past second byte", inline=True)
comment(0x9D5F, "Save updated TX buffer index", inline=True)
comment(0x9D78, "Write CR2: clear status, idle listen", inline=True)
comment(0x9D81, "PHA/PLA delay (~7 cycles each)", inline=True)
comment(0x9D82, "Increment delay counter", inline=True)
comment(0x9D83, "Loop 256 times for NMI disable", inline=True)
comment(0x9D85, "Store error and return to idle", inline=True)
comment(0x9D96, "Write CR1 to switch from TX to RX", inline=True)
comment(0x9DA1, "A=1: mask for bit0 test", inline=True)
comment(0x9DA3, "Test tx_flags bit0 (handshake)", inline=True)
comment(0x9DA6, "bit0 clear: install reply handler", inline=True)
comment(0x9DAD, "High byte of nmi_reply_scout addr", inline=True)
comment(0x9DAF, "Install handler and RTI", inline=True)
comment(0x9DC3, "High byte of nmi_reply_cont", inline=True)
comment(0x9DC5, "Install continuation handler", inline=True)
comment(0x9DD4, "High byte of nmi_reply_validate", inline=True)
comment(0x9DDE, "A=&41: 'not listening' error code", inline=True)
comment(0x9DE0, "Store error and return to idle", inline=True)
comment(0x9E91, "bit7 clear: error path", inline=True)
comment(0x9E93, "ADLC reset and return to idle", inline=True)
label(0x9E96, "nmi_tx_not_listening")  # Store "not listening" error and exit
comment(0x9E96, "A=&41: 'not listening' error", inline=True)
label(0x9E98, "jmp_tx_result_fail")   # JMP tx_result_fail
comment(0x9E98, "Store result and return to idle", inline=True)
comment(0x9E9B, "Load saved handler low byte", inline=True)
label(0x9EC9, "tube_tx_inc_byte2")    # Increment byte 2 of 4-byte counter
label(0x9ED1, "tube_tx_inc_byte4")    # Increment byte 4 of 4-byte counter
comment(0x9EFA, "High byte of handler address", inline=True)
comment(0x9EFC, "Install continuation handler", inline=True)
comment(0x9F0B, "High byte of handler address", inline=True)
comment(0x9F12, "Install handler and RTI", inline=True)
comment(0x9F2A, "Load TX flags for next action", inline=True)
comment(0x9F2D, "bit7 clear: no data phase", inline=True)
comment(0x9F2F, "Install data RX handler", inline=True)
label(0x9F3D, "tx_result_fail")        # Store result=&41 (not listening) (9 refs)
comment(0x9F6B, "Load TX flags for transfer setup", inline=True)
comment(0x9F70, "Store with bit 1 set (Tube xfer)", inline=True)
comment(0x9F7A, "(continued)", inline=True)
comment(0x9F7B, "(continued)", inline=True)
comment(0x9F7C, "(continued)", inline=True)
comment(0x9F84, "(continued)", inline=True)
comment(0x9F85, "(continued)", inline=True)
comment(0x9F90, "CLC for base pointer addition", inline=True)
comment(0x9F91, "Add RXCB base to get RXCB+4 addr", inline=True)
comment(0x9F98, "Claim Tube transfer address", inline=True)
comment(0x9FA0, "Reclaim with scout status type", inline=True)
comment(0x9FA5, "Restore X from stack", inline=True)
comment(0x9FA6, "Return with C = transfer status", inline=True)
comment(0x9FCA, "Return with C=1 (success)", inline=True)
comment(0x9FE5, "Transfer ROM bank to Y", inline=True)
# ============================================================
# 3.34-specific annotations (gap-filling after backfill)
# ============================================================

# --- Inline comments for under-commented subroutines ---

# fsreply_5_set_lib
comment(0x8CF7, "Store Y (library handle) to &0E04", inline=True)
comment(0x8CFA, "Non-zero: continue to set handle", inline=True)

# install_nmi_shim
comment(0x96CE, "Enable interrupts during copy", inline=True)
comment(0x96D1, "Load NMI shim byte from ROM table", inline=True)
comment(0x96D4, "Store to NMI area at &0D00+Y", inline=True)
comment(0x96D7, "Decrement byte counter", inline=True)
comment(0x96DA, "Restore interrupt state", inline=True)

# print_decimal
comment(0x85B0, "A=100: hundreds divisor", inline=True)
comment(0x85B2, "Print hundreds digit", inline=True)
comment(0x85B5, "A=10: tens divisor", inline=True)
comment(0x85B7, "Print tens digit", inline=True)

# print_file_info
comment(0x8609, "Compare with CR (end of filename)", inline=True)
comment(0x8614, "Advance to next filename char", inline=True)
comment(0x8617, "Print padding space", inline=True)
comment(0x861A, "Advance padding counter", inline=True)
comment(0x861D, "Continue padding if < 12 chars", inline=True)
comment(0x8624, "Print exec address and length", inline=True)
comment(0x862A, "Y=9: exec address offset", inline=True)
comment(0x862C, "Print exec address bytes", inline=True)
comment(0x862F, "Y=&0C: file length offset", inline=True)
comment(0x8637, "Load address/length byte", inline=True)
comment(0x8639, "Print as 2 hex digits", inline=True)
comment(0x863D, "Decrement byte counter", inline=True)
comment(0x8640, "A=space: separator character", inline=True)

# lang_1_remote_boot
comment(0x9105, "OR with 9: set remote boot bits", inline=True)
comment(0x9107, "Store modified control byte", inline=True)
comment(0x9109, "X=&80: exec address offset lo", inline=True)
comment(0x910B, "Y=&80: exec address offset hi", inline=True)
comment(0x910D, "Load exec address low byte", inline=True)
comment(0x910F, "Save exec lo on stack", inline=True)
comment(0x9111, "Load exec address high byte", inline=True)
comment(0x9113, "Y=&0F: workspace offset for hi", inline=True)
comment(0x9115, "Store exec hi byte to workspace", inline=True)
comment(0x9118, "Restore exec lo byte from stack", inline=True)
comment(0x911B, "Initialize OSBYTE vectors", inline=True)
comment(0x9121, "X=1: enable parameter", inline=True)
comment(0x9125, "Disable keyboard for Econet boot", inline=True)

# store_output_byte
comment(0x91F9, "XOR with transfer count flags", inline=True)
comment(0x91FD, "Data phase active: continue", inline=True)
comment(0x91FF, "Load transfer count flags", inline=True)
comment(0x9203, "No Tube transfer: discard", inline=True)
comment(0x9206, "Mask off control bits", inline=True)
comment(0x9208, "Store updated flags", inline=True)

# print_station_info
comment(0x81F8, "Load local station number", inline=True)
comment(0x81FB, "Print station number as decimal", inline=True)
comment(0x81FE, "A=&20: test bit 5 of SR2 (clock)", inline=True)
comment(0x8200, "Test ADLC SR2 for network clock", inline=True)
comment(0x8203, "Clock present: skip warning msg", inline=True)

# restore_econet_state
comment(0x96B7, "Y=8: workspace offset for flags", inline=True)
comment(0x96B9, "Load saved rx_status_flags", inline=True)
comment(0x96BF, "Load saved protection mask", inline=True)
comment(0x96C5, "Load saved TX-in-progress flag", inline=True)
comment(0x96C7, "Restore TX-in-progress status", inline=True)
comment(0x96CA, "Re-initialize ADLC and NMI", inline=True)

# fsreply_4_notify_exec
comment(0x8D8C, "X=&4A: parameter block offset", inline=True)
comment(0x8D8E, "Y=5: command code offset", inline=True)
comment(0x8D90, "Send FS examine command", inline=True)
comment(0x8D96, "No Tube: skip transfer setup", inline=True)
comment(0x8D98, "Add file load address upper byte", inline=True)
comment(0x8D9B, "Add address check byte", inline=True)
comment(0x8DA3, "X=9: Tube claim parameter", inline=True)
comment(0x8DA5, "Y=&0F: Tube claim parameter", inline=True)
comment(0x8DAC, "Execute via indirect load vector", inline=True)

# --- Label renames ---

# Shared tail
label(0x81C9, "restore_y_return")

# Data labels
label(0x8001, "lang_entry_lo")
label(0x8002, "lang_entry_hi")
label(0x8004, "svc_entry_lo")
label(0x0055, "tube_dispatch_ptr_lo")
label(0x8BD7, "cmd_table_entry_1")
label(0x9A16, "rxcb_buf_hi_operand")
label(0x9B0E, "tx_dispatch_page_operand")
label(0x9B13, "rx_ctrl_operand")
label(0x9C5B, "sr2_test_operand")
label(0x9ECA, "tube_tx_byte2_operand")
label(0x9ED2, "tube_tx_byte4_operand")

# Internal loop
label(0x8C76, "print_option_char")

# Internal conditional
label(0x8C4D, "cat_access_setup")


# ============================================================
# Annotations back-propagated from NFS 3.34B
# ============================================================
comment(0x0615, "Encode carry into result bit 7", inline=True)
comment(0x0616, "Send carry+result byte via R2", inline=True)
comment(0x8171, "Return from workspace reset", inline=True)
comment(0x8172, "X=8: ROM offset for *ROFF match", inline=True)
comment(0x8174, "Match command against ROM string", inline=True)
comment(0x8177, "No match: try *NET command", inline=True)
comment(0x8179, "Match found: claim service (A=0)", inline=True)
comment(0x82A0, "Y=2: printer server offset", inline=True)
comment(0x82A2, "A=&EB: default printer server", inline=True)
comment(0x82A4, "Store printer server at offset 2", inline=True)
comment(0x82A7, "A=0: clear remaining fields", inline=True)
comment(0x82A9, "Clear FS server network number", inline=True)
comment(0x82AC, "Clear workspace byte at offset 3", inline=True)
comment(0x82AE, "Clear protection status mask", inline=True)
comment(0x82B1, "Clear FS messages flag", inline=True)
comment(0x82C6, "Store station ID for TX scout", inline=True)
comment(0x83CE, "Load handle bitmask for BPUT/BGET", inline=True)
comment(0x83ED, "Convert SPOOL handle to bitmask", inline=True)
comment(0x83F0, "Compare SPOOL mask with file mask", inline=True)
comment(0x83F2, "Not SPOOL file: dispatch FS error", inline=True)
comment(0x83F4, "Load '*SP.' command string low", inline=True)
comment(0x845A, "Load TX flag byte from ctrl block", inline=True)
comment(0x845C, "Bit 7 set: TX complete, clean up", inline=True)
comment(0x845E, "Check for Escape during TX wait", inline=True)
comment(0x8492, "Bit 7 set: set EOF hint flag", inline=True)
comment(0x8494, "Load handle bitmask for flag op", inline=True)
comment(0x8499, "Flag cleared: load handle mask", inline=True)
comment(0x84A3, "Return with handle mask in A", inline=True)
comment(0x84A5, "Y += 4", inline=True)
comment(0x84A6, "(continued)", inline=True)
comment(0x84A7, "(continued)", inline=True)
comment(0x84A8, "(continued)", inline=True)
comment(0x84A9, "Return with Y adjusted", inline=True)
comment(0x84AA, "Y -= 4", inline=True)
comment(0x84AB, "Y -= 3", inline=True)
comment(0x84AC, "(continued)", inline=True)
comment(0x84AD, "(continued)", inline=True)
comment(0x8600, "Check if file info available", inline=True)
comment(0x8603, "No info available: return", inline=True)
comment(0x8605, "Y=0: start of filename string", inline=True)
comment(0x8607, "Load filename character", inline=True)
comment(0x860D, "Also end name on space character", inline=True)
comment(0x861F, "Y=5: high byte of load address", inline=True)
comment(0x8631, "X=3: print 3 bytes for file length", inline=True)
comment(0x863C, "Move to next lower address byte", inline=True)
comment(0x86A1, "Y=1: offset past filename pointer", inline=True)
comment(0x86A2, "X=&FF: parse all characters", inline=True)
comment(0x86A4, "C=0: normal string parse entry", inline=True)
comment(0x86A5, "Init string parsing via GSINIT", inline=True)
comment(0x878C, "A=&2A: error ptr for FS retry", inline=True)
comment(0x878E, "Store error ptr for TX poll", inline=True)
comment(0x8820, "Save handle for EOF check", inline=True)
comment(0x88B9, "Load FS command code from reply", inline=True)
comment(0x88BC, "Zero: no attribute data returned", inline=True)
comment(0x88DB, "Reload FS command code", inline=True)
comment(0x88DE, "A = command code for exit test", inline=True)
comment(0x8978, "A = handle bitmask from set_fs_flag", inline=True)
comment(0x8979, "Merge handle into sequence tracking", inline=True)
comment(0x897C, "Store updated sequence tracking", inline=True)
comment(0x89A9, "X=1? (*OPT 1: set messaging)", inline=True)
comment(0x89AB, "Not *OPT 1: bad option error", inline=True)
comment(0x89AD, "Y < 2? (valid: 0=off, 1=on)", inline=True)
comment(0x89AF, "Y >= 2: bad option value error", inline=True)
comment(0x8A73, "A=&2A: error ptr for FS retry", inline=True)
comment(0x8A75, "Store error ptr for TX poll", inline=True)
comment(0x8BBD, "CLC for pointer calculation", inline=True)
comment(0x8BBE, "A = chars consumed from input", inline=True)
comment(0x8BBF, "X = command text pointer high", inline=True)
comment(0x8BC1, "Add chars consumed to pointer low", inline=True)
comment(0x8BC3, "Store adjusted text pointer low", inline=True)
comment(0x8BC6, "Duplicate to second pointer copy", inline=True)
comment(0x8BC9, "No page overflow: skip INX", inline=True)
comment(0x8BCB, "Adjust high byte for page crossing", inline=True)
comment(0x8BCC, "Store high byte to context ptr 1", inline=True)
comment(0x8BCF, "Store high byte to context ptr 2", inline=True)
comment(0x8BD2, "Store high byte to context ptr 3", inline=True)
comment(0x8BD5, "Dispatch via PHA/PHA/RTS", inline=True)
comment(0x8BFD, "X=&14 (20): column width for display", inline=True)
comment(0x8BFF, "Store column width for batch calc", inline=True)
comment(0x8C01, "X=3: column count for examine request", inline=True)
comment(0x8C03, "Store column count", inline=True)
comment(0x8C05, "Y=0: initial entry start offset", inline=True)
comment(0x8C07, "A=6: examine format type in command", inline=True)
comment(0x8C09, "Store format type at &0F05", inline=True)
comment(0x8C0C, "Skip spaces in dir name argument", inline=True)
comment(0x8C0F, "Save parameter offset after spaces", inline=True)
comment(0x8C58, "X=4: space padding count", inline=True)
comment(0x8C5A, "Print 4 spaces for alignment", inline=True)
comment(0x8C5D, "Print 'Option ' label", inline=True)
comment(0x8C92, "Print 5 spaces for alignment", inline=True)
comment(0x8C95, "Print 'Lib. ' label", inline=True)
comment(0x8CAC, "A = reply buffer bytes consumed", inline=True)
comment(0x8CAD, "Complement for divide-by-subtraction", inline=True)
comment(0x8CAF, "SEC for subtraction", inline=True)
comment(0x8CB0, "Subtract one column width (20)", inline=True)
comment(0x8CB2, "Count another entry that fits", inline=True)
comment(0x8CB3, "Loop while space remains", inline=True)
comment(0x8CB5, "Store entries per examine batch", inline=True)
comment(0x8CB8, "Save batch size for loop reset", inline=True)
comment(0x8CBA, "Reload dir name offset for examine", inline=True)
comment(0x8CE7, "Fallthrough (also boot string 'L.!')", inline=True)
comment(0x8D09, "C=1: alphabetic, forward to FS", inline=True)
comment(0x8D0B, "A=0: default network (local)", inline=True)
comment(0x8D10, "C=0: no dot, single number only", inline=True)
comment(0x8DA9, "Claim Tube for address transfer", inline=True)
comment(0x8DC9, "Load handle number from &F0", inline=True)
comment(0x8DDA, "A=0: clear service claim", inline=True)
comment(0x8DDC, "Release ROM service number", inline=True)
comment(0x8DDE, "Return to caller", inline=True)
comment(0x8DDF, "Load handle number from &F0", inline=True)
comment(0x8E49, "Set up and start low-level transmit", inline=True)
comment(0x8E4C, "Exit: release service claim", inline=True)
comment(0x8E4F, "SEC: alternate entry for OSWORD &11", inline=True)
comment(0x8E50, "A = param block high for branch", inline=True)
comment(0x8E65, "Reset JSR protection status", inline=True)
comment(0x8E68, "Branch to set carry and dispatch", inline=True)
comment(0x8E77, "Always taken (SEC set above)", inline=True)
comment(0x8E7F, "Sub-function >= 4? (protection)", inline=True)
comment(0x8E96, "Copy station bytes to/from workspace", inline=True)
comment(0x8E99, "Always taken (Y=2 after copy)", inline=True)
comment(0x8EAC, "SEC: set carry for exit", inline=True)
comment(0x8EAF, "Load local station number", inline=True)
comment(0x8EB2, "Y=1: param block offset for result", inline=True)
comment(0x8EB3, "Return station number to caller", inline=True)
comment(0x8EB5, "Always taken (C set above)", inline=True)
comment(0x8EDB, "Y=1: param block offset for error", inline=True)
comment(0x8EDC, "Load last FS error number", inline=True)
comment(0x8EDF, "Return error code to caller", inline=True)
comment(0x8EE1, "Exit with carry set", inline=True)
comment(0x8FF3, "First packet: exit handler", inline=True)
comment(0x9001, "Poll TX until complete", inline=True)
comment(0x90F8, "Set up control block for reply", inline=True)
comment(0x90FB, "Return from remote command handler", inline=True)
comment(0x9123, "Y=0: second argument for OSBYTE", inline=True)
comment(0x91B5, "A=0: clear printer buffer state", inline=True)
comment(0x91EA, "Flush done: continue loop", inline=True)
comment(0x920B, "Flush accumulated output to network", inline=True)
comment(0x920E, "Save PFLAGS bit 0 via carry", inline=True)
comment(0x9211, "Restore original reason code", inline=True)
comment(0x9212, "Old PFLAGS bit 0 to A bit 7", inline=True)
comment(0x9213, "Reason bit 0 into PFLAGS bit 0", inline=True)
comment(0x9681, "Copy NMI shim from ROM to &0D00", inline=True)
comment(0x9684, "Load current ROM bank number", inline=True)
comment(0x9686, "Patch ROM bank into NMI shim", inline=True)
comment(0x9689, "A=&80: TX idle/complete status", inline=True)
comment(0x96B1, "Store tx_in_progress to offset &0A", inline=True)
comment(0x96B3, "Return to caller", inline=True)
comment(0x96CD, "Save interrupt state on stack", inline=True)
comment(0x96CF, "Y=&20: copy 32 bytes", inline=True)
comment(0x96D8, "Loop until all bytes copied", inline=True)
comment(0x96DB, "Return from shim installation", inline=True)
comment(0x9FEB, "Load current TX flags", inline=True)
comment(0x9FEE, "Set bit 1 (transfer mode flag)", inline=True)
comment(0x9FF0, "Store updated TX flags", inline=True)
comment(0x9FF3, "SEC for subtraction", inline=True)
comment(0x9FF4, "Save carry on stack", inline=True)
comment(0x9FF5, "Y=4: TXCB data start low offset", inline=True)
comment(0x9FF7, "Load data start low byte", inline=True)
comment(0x9FF9, "Y += 4: advance to data end low offset", inline=True)
comment(0x9FFA, "(continued)", inline=True)
comment(0x9FFB, "(continued)", inline=True)
comment(0x9FFC, "(continued)", inline=True)
comment(0x9FFD, "Restore carry for subtraction", inline=True)
comment(0x9FFE, "Subtract buffer end from start", inline=True)

# tube_init_reloc: Tube initialisation
comment(0x04EF, "Restore saved Y register", inline=True)

# tube_dispatch_table: Tube host code page 5
comment(0x051C, "Save character for WRCH echo", inline=True)
comment(0x053D, "Restore saved X", inline=True)
comment(0x0543, "Read file handle from R2", inline=True)
comment(0x0550, "Read file handle from R2", inline=True)
comment(0x0569, "Read open mode from R2", inline=True)
comment(0x058C, "Read file handle from R2", inline=True)
comment(0x05C5, "Read command string into &0700", inline=True)
comment(0x05D8, "X=&10: read 16-byte control block", inline=True)

# tube_code_page6: Tube host code page 6
comment(0x0602, "X=&0C: read 13-byte param block", inline=True)
comment(0x0626, "Read X parameter from R2", inline=True)
comment(0x063B, "Read X parameter from R2", inline=True)
comment(0x065D, "Read OSWORD number from R2", inline=True)
comment(0x06A3, "X=4: read 5-byte RDLN ctrl block", inline=True)

# svc_9_help: print help text
comment(0x81C9, "Reload character counter", inline=True)

# init_fs_vectors: install FS vectors
comment(0x8219, "Load vector address from table", inline=True)

# svc_1_abs_workspace: claim workspace
comment(0x826F, "Check if page &10 or above", inline=True)
comment(0x8271, "Not our workspace: return", inline=True)

# svc_2_private_workspace: claim private workspace
comment(0x8278, "Store RX buffer page", inline=True)
comment(0x827A, "Advance to next page", inline=True)
comment(0x827B, "Store workspace page", inline=True)

# store_fs_error: FS error ptr setup
comment(0x8448, "A=&2A: error ptr for FS retry", inline=True)

# fscv_5_cat: *CAT handler (shifted addresses)
comment(0x8C2E, "X=5: space padding count", inline=True)
comment(0x8C30, "Print 5 spaces for alignment", inline=True)
comment(0x8C33, "Access: 0=Owner, non-zero=Public", inline=True)
comment(0x8C41, "Always taken (high-bit term. str)", inline=True)
comment(0x8C67, "Load boot option from workspace", inline=True)
comment(0x8C73, "Load string offset for option name", inline=True)
comment(0x8C76, "Load char from option name string", inline=True)
comment(0x8C79, "Zero terminator: name complete", inline=True)
comment(0x8C8B, "X=&11: CSD name offset in reply", inline=True)
comment(0x8C8D, "Print current directory name", inline=True)
comment(0x8C90, "X=5: space padding count", inline=True)
comment(0x8C9D, "X=&1B: library name offset in reply", inline=True)
comment(0x8CA7, "Y=0: initial examine start position", inline=True)

# i_am_handler: parse station number
comment(0x8D06, "Skip spaces in command argument", inline=True)

# osword_12_handler: read/set state information
comment(0x8E7B, "Sub-function >= 6? (handle ops)", inline=True)
comment(0x8E7D, "Sub >= 6: handle/station/error", inline=True)

# remote_cmd_data: handle remote command data
comment(0x90CD, "Y=&0E: 14-byte parameter block", inline=True)
comment(0x90CF, "OSWORD 7? (make sound)", inline=True)

# net_write_char: IRQ flag manipulation
comment(0x903D, "Get stack pointer for P register", inline=True)

# save_econet_state: save TX state
comment(0x96AE, "Load TX in-progress flag", inline=True)

# tx_calc_transfer: TX block check
comment(0x9F5D, "Load TX block byte at offset 6", inline=True)

# Generate disassembly
# ============================================================

import json
import sys

output = go(print_output=False)

_output_dirpath.mkdir(parents=True, exist_ok=True)
output_filepath = _output_dirpath / "nfs-3.34.asm"
output_filepath.write_text(output)
print(f"Wrote {output_filepath}", file=sys.stderr)

structured = get_structured()
json_filepath = _output_dirpath / "nfs-3.34.json"
json_filepath.write_text(json.dumps(structured))
print(f"Wrote {json_filepath}", file=sys.stderr)
