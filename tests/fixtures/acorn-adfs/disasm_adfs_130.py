"""py8dis driver for Acorn ADFS 1.30."""

import os
import sys
from pathlib import Path

from py8dis.commands import *
import py8dis.acorn as acorn

init(assembler_name="beebasm", lower_case=True)

# ---------------------------------------------------------------------------
# Custom hooks for inline error blocks
# ---------------------------------------------------------------------------

def brk_error_hook(target, addr):
    """Handle inline BRK error blocks following JSR to error-raising routines.

    Pattern: JSR error_routine / error_number / "error message" / &00
    The error routine pops the return address from the stack to find the
    inline error data. Execution never continues past the inline block.
    """
    inline_addr = addr + 3  # skip the JSR instruction
    byte(inline_addr)       # mark error number as data byte
    stringz(inline_addr + 1)  # mark error message as zero-terminated string
    return None  # execution does not continue (BRK raised)

# ---------------------------------------------------------------------------
# Load the ROM binary
# ---------------------------------------------------------------------------

_script_dirpath = Path(__file__).resolve().parent
_version_dirpath = _script_dirpath.parent
# `fantasm disassemble VID` sets FANTASM_ROM / FANTASM_OUTPUT_DIR;
# direct `python <driver>` invocations fall back to the conventional
# paths under the version directory.
_rom_filepath = os.environ.get(
    "FANTASM_ROM",
    str(_version_dirpath / "rom" / "adfs-1.30.rom"),
)
_output_dirpath = Path(os.environ.get(
    "FANTASM_OUTPUT_DIR",
    str(_version_dirpath / "output"),
))

load(0x8000, _rom_filepath, "6502")

# ---------------------------------------------------------------------------
# Standard Acorn BBC Micro definitions
# ---------------------------------------------------------------------------

acorn.bbc()
acorn.is_sideways_rom()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SCSI interface registers
constant(0xFC40, "scsi_data")
constant(0xFC41, "scsi_status")
constant(0xFC42, "scsi_select")
constant(0xFC43, "scsi_irq_enable")

# WD1770 floppy disc controller registers
label(0xFE80, "fdc_1770_drive_control")
label(0xFE84, "fdc_1770_command_or_status")

# System VIA
constant(0xFE44, "via_t1c_h")

# Tube ULA
constant(0xFEE5, "tube_r4_data")

# Filing system number
constant(0x08, "adfs_filing_system_number")

# OSBYTE calls used by ADFS
constant(0x8F, "osbyte_issue_service_request")
constant(0xA8, "osbyte_read_address_of_rom_pointer_table")
constant(0xBA, "osbyte_read_vdu_driver_screen_bank")
constant(0xFF, "osbyte_read_write_startup_options")

# OSWORD calls
constant(0x72, "osword_disc_access")

# Service call numbers
constant(0x03, "service_auto_boot")
constant(0x04, "service_unrecognised_command")
constant(0x08, "service_unrecognised_osword")
constant(0x09, "service_unrecognised_help")
constant(0x0E, "service_read_file_handle_range")
constant(0x12, "service_select_filing_system")
constant(0x21, "service_close_all_files")
constant(0x25, "service_filing_system_info")
constant(0x26, "service_close_file_handles")
constant(0x27, "service_reset_claimed_areas")

# ADFS error codes
constant(0x92, "err_aborted")
constant(0x93, "err_wont")
constant(0x94, "err_bad_parms")
constant(0x96, "err_cant_delete_csd")
constant(0x97, "err_cant_delete_library")
constant(0x98, "err_compaction_required")
constant(0x99, "err_map_full")
constant(0xA8, "err_broken_directory")
constant(0xA9, "err_bad_fs_map")
constant(0xAA, "err_bad_checksum")
constant(0xB0, "err_bad_rename")
constant(0xB3, "err_dir_full")
constant(0xB4, "err_dir_not_empty")
constant(0xB7, "err_outside_file")
constant(0xBD, "err_access_violation")
constant(0xC0, "err_too_many_open_files")
constant(0xC1, "err_not_open_for_update")
constant(0xC2, "err_already_open")
constant(0xC3, "err_locked")
constant(0xC4, "err_already_exists")
constant(0xC6, "err_disc_full")
constant(0xC7, "err_disc_error")
constant(0xCA, "err_data_lost")
constant(0xCB, "err_bad_opt")
constant(0xCC, "err_bad_name")
constant(0xD6, "err_not_found")
constant(0xDE, "err_channel")
constant(0xDF, "err_eof")
constant(0xFD, "err_wild_cards")
constant(0xFE, "err_bad_command")

# ---------------------------------------------------------------------------
# MOS zero page and system locations used by ADFS
# ---------------------------------------------------------------------------

# OSARGS user zero page pointer: X points to a 4-byte block
# at &00-&03 in the user's zero page allocation
label(0x0000, "zp_user_ptr_0")
label(0x0001, "zp_user_ptr_1")
label(0x0002, "zp_user_ptr_2")
label(0x0003, "zp_user_ptr_3")

# MOS zero page: OSWORD parameter block pointer
# MOS zero page: last OSBYTE/OSWORD register values
label(0x00EF, "zp_osbyte_last_a")
label(0x00F0, "zp_osbyte_last_x")
label(0x00F1, "zp_osbyte_last_y")

# MOS zero page: Escape flag (bit 7 set = Escape pressed)
label(0x00FF, "zp_escape_flag")

# Stack page: BRK error block construction area
label(0x0100, "brk_error_block")
label(0x0101, "brk_error_block_1")
label(0x0102, "brk_error_block_2")
label(0x0103, "brk_error_block_3")
label(0x0104, "brk_error_block_4")

# Tube host code entry point
label(0x0406, "tube_entry")

# Extended vector workspace: FSC entry for boot
label(0x06A9, "ext_vec_fsc_lo")

# NMI handler: branch target after data transfer loop
label(0x0D18, "nmi_transfer_done")

# FSM sector 0: third byte (first free space length entry)
label(0x0E03, "fsm_s0_first_length")

# Self-modifying target in NMI handler (patched with real address)
label(0xFFFF, "nmi_patched_addr")

# ---------------------------------------------------------------------------
# ADFS zero page variables
# ---------------------------------------------------------------------------

# NMI workspace (&A0-&A7): used by floppy disc driver
label(0x00A0, "zp_floppy_error")
label(0x00A1, "zp_floppy_control")
label(0x00A2, "zp_floppy_state")
label(0x00A3, "zp_floppy_track")
label(0x00A4, "zp_floppy_sector")
label(0x00A5, "zp_floppy_track_num")
label(0x00A6, "zp_floppy_dest_page")

# Filing system scratch space (&B0-&BF): pointer pairs
label(0x00B0, "zp_ctrl_blk_lo")
label(0x00B1, "zp_ctrl_blk_hi")
label(0x00B2, "zp_mem_ptr_lo")
label(0x00B3, "zp_mem_ptr_hi")
label(0x00B4, "zp_text_ptr_lo")
label(0x00B5, "zp_text_ptr_hi")
label(0x00B6, "zp_entry_ptr_lo")
label(0x00B7, "zp_entry_ptr_hi")
label(0x00B8, "zp_osfile_ptr_lo")
label(0x00B9, "zp_osfile_ptr_hi")
label(0x00BA, "zp_wksp_ptr_lo")
label(0x00BB, "zp_wksp_ptr_hi")
label(0x00BC, "zp_buf_src_lo")
label(0x00BD, "zp_buf_src_hi")
label(0x00BE, "zp_buf_dest_lo")
label(0x00BF, "zp_buf_dest_hi")

# Filing system persistent workspace (&C0-&CF)
label(0x00C0, "zp_name_ptr_lo")
label(0x00C1, "zp_name_ptr_hi")
label(0x00C2, "zp_save_y")
label(0x00C3, "zp_save_x")
label(0x00C4, "zp_osfind_y")
label(0x00C5, "zp_osfind_x")
label(0x00C6, "zp_gspb_ptr_lo")
label(0x00C7, "zp_gspb_ptr_hi")
label(0x00C8, "zp_temp_ptr")
label(0x00C9, "zp_temp_ptr_1")
label(0x00CA, "zp_temp_ptr_2")
label(0x00CB, "zp_temp_ptr_3")
label(0x00CC, "zp_scsi_status")
label(0x00CD, "zp_adfs_flags")
label(0x00CE, "zp_retry_count")
label(0x00CF, "zp_channel_offset")

# ---------------------------------------------------------------------------
# Paged workspace: free space map (&0E00-&0FFF)
# ---------------------------------------------------------------------------
# Sector 0 (&0E00-&0EFF): free space start sectors (3 bytes each)
#   Tail: &FA reserved, &FB padding, &FC-&FE disc size (24-bit), &FF checksum
# Sector 1 (&0F00-&0FFF): free space lengths (3 bytes each)
#   Tail: &FB-&FC disc ID, &FD boot option, &FE end-of-list ptr, &FF checksum
#
# The sector 0 tail labels (fsm_s0_disc_size_mid etc.) also appear in
# X-indexed instructions like "adc fsm_s0_disc_size_mid,x". This is an
# addressing trick: with X = 3*N+3 the effective address lands in sector 1,
# accessing free space length entries. The label reflects the byte's true
# meaning in sector 0; the inline comment describes the indexed access.

label(0x0E00, "fsm_sector_0")
label(0x0F00, "fsm_sector_1")
label(0x0EFA, "fsm_s0_reserved")
label(0x0EFB, "fsm_s0_pre_disc_size")
label(0x0EFC, "fsm_s0_disc_size_lo")
label(0x0EFD, "fsm_s0_disc_size_mid")
label(0x0EFE, "fsm_s0_disc_size_hi")
label(0x0EFF, "fsm_s0_checksum")
label(0x0F03, "fsm_s1_first_length")
label(0x0FFB, "fsm_s1_disc_id_lo")
label(0x0FFC, "fsm_s1_disc_id_hi")
label(0x0FFD, "fsm_s1_boot_option")
label(0x0FFE, "fsm_s1_end_of_list_ptr")
label(0x0FFF, "fsm_s1_checksum")

# ---------------------------------------------------------------------------
# Paged workspace: general (&1000-&11FF)
#
# The ADFS disc operation control block is at &1015-&1024:
#   &1015  Returned result
#   &1016  Memory address (4 bytes, little-endian)
#   &101A  Command
#   &101B  Drive+Sector b16-b20 (big-endian)
#   &101C  Sector b8-b15
#   &101D  Sector b0-b7
#   &101E  Sector count
#   &101F  Control
#   &1020  Transfer length (4 bytes, little-endian)
# ---------------------------------------------------------------------------

label(0x1000, "wksp")
label(0x1001, "wksp_buf_sec_lo")        # per-channel buffer sector addr low (X-indexed, 4-byte stride)
label(0x1002, "wksp_buf_sec_mid")       # per-channel buffer sector addr mid
label(0x1003, "wksp_buf_sec_hi")        # per-channel buffer sector addr high + drive bits
label(0x1004, "wksp_buf_flag")          # per-channel buffer state/dirty flags
label(0x1008, "wksp_buf_flag_1")        # buffer flag slot 1 (absolute init alias for wksp_buf_flag+4)
label(0x100C, "wksp_buf_flag_2")        # buffer flag slot 2 (absolute init alias for wksp_buf_flag+8)
label(0x100D, "wksp_entry_field_base")  # Y-indexed base: +Y reaches disc op/OSFILE fields
label(0x100E, "wksp_entry_len_base")    # Y-indexed base: +&12 reaches disc_op_transfer_len
label(0x1010, "wksp_osword_block")
label(0x1011, "wksp_entry_calc_base")   # Y-indexed base: +Y reaches sector calculation area
label(0x1014, "wksp_disc_op_block")     # disc op block base; also buffer flag slot 4
label(0x1015, "wksp_disc_op_result")
label(0x1016, "wksp_disc_op_mem_addr")
label(0x1017, "wksp_disc_op_mem_addr_1")
label(0x1018, "wksp_disc_op_mem_addr_2")
label(0x1019, "wksp_disc_op_mem_addr_3")
label(0x101A, "wksp_disc_op_command")
label(0x101B, "wksp_disc_op_sector")    # big-endian
label(0x101C, "wksp_disc_op_sector_mid")
label(0x101D, "wksp_disc_op_sector_lo")
label(0x101E, "wksp_disc_op_sector_count")
label(0x101F, "wksp_disc_op_control")
label(0x1020, "wksp_disc_op_transfer_len")  # little-endian
label(0x1021, "wksp_disc_op_xfer_len_1")
label(0x1022, "wksp_disc_op_xfer_len_2")
label(0x1023, "wksp_disc_op_xfer_len_3")
label(0x1024, "wksp_entry_size_base")   # Y-indexed base: +Y reaches object sector/size fields
label(0x1026, "wksp_tube_transfer_addr")
label(0x1027, "wksp_tube_transfer_addr_1")
label(0x1028, "wksp_tube_xfer_addr_2")
label(0x1029, "wksp_tube_xfer_addr_3")
label(0x102A, "wksp_csd_drive_temp")
label(0x102B, "wksp_csd_sector_temp")
label(0x102C, "wksp_csd_drive_sector")     # 3-byte CSD sector + 1 drive
label(0x102D, "wksp_csd_drive_sector_mid")
label(0x102E, "wksp_alt_sector_hi")        # alt workspace sector pointer
label(0x102F, "wksp_saved_drive")
label(0x1030, "wksp_temp_sector")          # 4-byte temp save for CSD sector
label(0x1033, "wksp_last_access_drive")
label(0x1034, "wksp_object_sector")        # 3-byte object sector address
label(0x1035, "wksp_object_sector_mid")
label(0x1036, "wksp_object_sector_hi")
label(0x1037, "wksp_object_size")          # 3-byte object size
label(0x1038, "wksp_object_size_mid")
label(0x1039, "wksp_object_size_hi")
label(0x103A, "wksp_alloc_sector")         # 3-byte allocated sector
label(0x103B, "wksp_saved_count")          # 4-byte saved byte count (OSGBPB)
label(0x103C, "wksp_saved_count_1")
label(0x103D, "wksp_alloc_size")           # 3-byte allocation request size
label(0x103E, "wksp_alloc_size_mid")
label(0x103F, "wksp_alloc_size_hi")
label(0x1040, "wksp_osfile_block")         # 18-byte control block for OSFILE
label(0x1041, "wksp_osfile_block_1")
label(0x1042, "wksp_osfile_load_addr")     # OSFILE load address (4 bytes)
label(0x1043, "wksp_osfile_load_addr_1")
label(0x1046, "wksp_osfile_exec_addr")     # OSFILE exec address (4 bytes)
label(0x1047, "wksp_osfile_exec_addr_1")
label(0x1048, "wksp_osfile_exec_addr_2")
label(0x1049, "wksp_osfile_exec_addr_3")
label(0x104A, "wksp_osfile_start_addr")    # OSFILE start/length (4 bytes)
label(0x104B, "wksp_osfile_start_addr_1")
label(0x104C, "wksp_osfile_start_addr_2")
label(0x104D, "wksp_osfile_start_addr_3")
label(0x104F, "wksp_osfile_end_addr_1")    # OSFILE end/attributes
label(0x1050, "wksp_osfile_end_addr_2")
label(0x1052, "wksp_osfile_attr")
label(0x1053, "wksp_osfile_attr_1")
label(0x1054, "wksp_osfile_attr_2")
label(0x105D, "wksp_access_accum")         # access attribute accumulator
label(0x105E, "wksp_access_accum_1")
label(0x105F, "wksp_free_space_total")     # 3-byte free space total
label(0x1060, "wksp_compact_start_page")   # *COMPACT start page
label(0x1061, "wksp_compact_length")
label(0x1062, "wksp_object_name")          # current object name buffer
label(0x1063, "wksp_object_name_1")

# Multi-file operation workspace (&106C-&1094)
label(0x106C, "wksp_saved_dir_sector")     # saved CSD sector for *COPY
label(0x106F, "wksp_drive_number")         # parsed drive number
label(0x1070, "wksp_new_parent_sector")    # new parent sector for *RENAME
label(0x1073, "wksp_dest_drive")           # destination drive for *COPY
label(0x1074, "wksp_dest_name")            # destination filename buffer
label(0x107E, "wksp_dest_filename_end")    # terminator position
label(0x107F, "wksp_copy_name_ptr")        # *COPY source name pointer
label(0x1080, "wksp_copy_name_ptr_hi")
label(0x1089, "wksp_copy_osfile_params")   # *COPY OSFILE parameters
label(0x108C, "wksp_copy_osfile_exec")
label(0x108D, "wksp_copy_dest_params")
label(0x1091, "wksp_filename_save")        # saved filename pointer
label(0x1092, "wksp_filename_save_hi")
label(0x1093, "wksp_entry_save")           # saved entry pointer
label(0x1094, "wksp_entry_save_hi")

# OSGBPB workspace (&1095-&10BF)
label(0x1095, "wksp_osgbpb_end_ptr")      # end position for transfer
label(0x1096, "wksp_osgbpb_sector_lo")    # current sector address
label(0x1097, "wksp_osgbpb_sector_mid")
label(0x1098, "wksp_osgbpb_sector_hi")
label(0x109A, "wksp_new_ptr_lo")           # new PTR value (4 bytes)
label(0x109B, "wksp_new_ptr_mid")
label(0x109C, "wksp_new_ptr_mid_hi")
label(0x109D, "wksp_new_ptr_hi")
label(0x109E, "wksp_new_ptr_4")
label(0x109F, "wksp_osgbpb_wksp_9f")
label(0x10A0, "wksp_ch_buf_sector")        # channel buffer sector
label(0x10A1, "wksp_ch_buf_sector_1")
label(0x10A2, "wksp_copy_read_sector")     # *COPY read sector address
label(0x10A3, "wksp_copy_read_sector_1")
label(0x10A4, "wksp_copy_read_sector_2")
label(0x10A5, "wksp_copy_write_sector")    # *COPY write sector address
label(0x10A6, "wksp_copy_write_sector_1")
label(0x10A7, "wksp_copy_write_sector_2")
label(0x10A8, "wksp_copy_src_sector")      # *COPY source sector
label(0x10A9, "wksp_copy_src_sector_1")
label(0x10AA, "wksp_copy_src_sector_2")
label(0x10AB, "wksp_copy_dest_sector")     # *COPY dest sector
label(0x10AC, "wksp_copy_dest_sector_1")
label(0x10AD, "wksp_copy_dest_sector_2")
label(0x10B4, "wksp_osgbpb_func")         # OSGBPB function code
label(0x10B5, "wksp_osgbpb_mode")         # OSGBPB mode/status flag
label(0x10B6, "wksp_osgbpb_start")        # transfer start position
label(0x10B7, "wksp_osgbpb_end")          # transfer end position
label(0x10B8, "wksp_osgbpb_data_addr")    # data transfer address (4 bytes)
label(0x10B9, "wksp_osgbpb_data_addr_1")
label(0x10BA, "wksp_osgbpb_data_addr_2")
label(0x10BB, "wksp_osgbpb_data_addr_3")
label(0x10BC, "wksp_osgbpb_wksp_bc")
label(0x10BD, "wksp_osgbpb_byte_count")   # output byte counter
label(0x10BE, "wksp_osgbpb_name_offset")  # name offset for A=8
label(0x10BF, "wksp_saved_drive_2")       # saved drive for extension

# Search/timing/disc-change workspace (&10C0-&10CF)
label(0x10C0, "wksp_search_flag")          # search/catalogue display flag
label(0x10C1, "wksp_workspace_checksum")   # workspace integrity checksum
label(0x10C2, "wksp_drive_change_mask")    # one bit per drive slot
label(0x10C3, "wksp_prev_clock")           # previous clock reading (5 bytes)
label(0x10C8, "wksp_clock")               # current/delta clock (5 bytes)
label(0x10C9, "wksp_clock_1")             # OSWORD 1 block byte 2
label(0x10CA, "wksp_clock_2")
label(0x10CB, "wksp_clock_3")
label(0x10CC, "wksp_clock_4")
label(0x10CD, "wksp_clock_5")
label(0x10CE, "wksp_error_suppress")       # non-zero suppresses wksp reload
label(0x10CF, "wksp_bput_modified")        # BPUT modification flag

# Workspace page &1100
label(0x1100, "wksp_csd_name")      # 10 bytes
label(0x110A, "wksp_lib_name")      # 10 bytes
label(0x1113, "wksp_csd_sector")    # 4 bytes (3 sector + 1 drive*32)
label(0x1114, "wksp_csd_sector_lo")
label(0x1115, "wksp_csd_sector_mid")
label(0x1116, "wksp_csd_sector_hi")
label(0x1117, "wksp_current_drive")
label(0x1118, "wksp_lib_sector")    # 4 bytes
label(0x1119, "wksp_lib_sector_lo")
label(0x111A, "wksp_lib_sector_mid")
label(0x111B, "wksp_lib_sector_hi")
label(0x111C, "wksp_prev_dir_sector")  # 4 bytes
label(0x111D, "wksp_prev_dir_sector_lo")
label(0x111E, "wksp_prev_dir_sector_mid")
label(0x111F, "wksp_prev_dir_sector_hi")
label(0x1120, "wksp_flags_save")
label(0x1121, "wksp_disc_id_lo")       # per-drive disc ID low (X-indexed by slot)
label(0x1122, "wksp_disc_id_hi")       # per-drive disc ID high
label(0x1131, "wksp_scsi_status")      # SCSI combined status byte
label(0x1132, "wksp_exec_handle")      # stored EXEC file handle for *RUN/boot
label(0x1133, "wksp_current_drive_hi")  # drive/LUN info

# Per-channel EXT tables (10 channels, 4 bytes each across 4 tables)
label(0x1134, "wksp_ch_ext_h")     # EXT high byte per channel
label(0x113E, "wksp_ch_ext_mh")
label(0x1148, "wksp_ch_ext_ml")
label(0x1152, "wksp_ch_ext_l")     # EXT low byte per channel

# Per-channel PTR tables
label(0x115C, "wksp_ch_ptr_h")     # PTR high byte per channel
label(0x1166, "wksp_ch_ptr_mh")
label(0x1170, "wksp_ch_ptr_ml")
label(0x117A, "wksp_ch_ptr_l")     # PTR low byte per channel

# Per-channel state tables
# Per-channel allocation tables (10 channels, 4 bytes each)
label(0x1183, "wksp_ch_alloc_pad")   # padding byte before table
label(0x1184, "wksp_ch_alloc_h")     # allocation high byte
label(0x118E, "wksp_ch_alloc_mh")    # allocation mid-high
label(0x1198, "wksp_ch_alloc_ml")    # allocation mid-low
label(0x11A2, "wksp_ch_alloc_l")     # allocation low byte

label(0x11AC, "wksp_ch_flags")     # channel flags per channel

# Per-channel start sector + drive tables (10 channels, 3 bytes each)
label(0x11B6, "wksp_ch_start_sec_h")   # start sector high + drive
label(0x11C0, "wksp_ch_start_sec_mh")  # start sector mid-high
label(0x11CA, "wksp_ch_start_sec_ml")  # start sector mid-low

# Per-channel parent directory sector (10 channels, 3 bytes each)
label(0x11D4, "wksp_ch_dir_sec_h")    # dir sector high + drive
label(0x11DE, "wksp_ch_dir_sec_mh")   # dir sector mid-high
label(0x11E8, "wksp_ch_dir_sec_ml")   # dir sector mid-low

# Per-channel sequence number (10 channels, 1 byte each)
label(0x11F2, "wksp_ch_seq_num")
label(0x10D0, "wksp_err_sector")   # error sector (little-endian)
label(0x10D1, "wksp_err_sector_mid")
label(0x10D2, "wksp_err_sector_hi")
label(0x10D3, "wksp_err_code")
label(0x10D4, "wksp_err_handle")    # file handle for error messages
label(0x10D5, "wksp_cur_channel")
label(0x10D6, "wksp_cmd_tail")      # saved command tail pointer low
label(0x10D7, "wksp_cmd_tail_hi")   # saved command tail pointer high
label(0x10D8, "wksp_compaction_reported") # saved screen mode for shadow
label(0x10E0, "wksp_fdc_xfer_mode") # FDC transfer mode (bit 7=read, bit 5=NMI)
label(0x10E1, "wksp_nmi_owner")     # NMI owner ID for release
label(0x10E2, "wksp_format_page")   # format buffer page number
label(0x10E3, "wksp_err_number")
label(0x10E4, "wksp_fdc_head_state")  # head-loaded / drive state flags
label(0x10E5, "wksp_fdc_track_0")    # saved track for drive 0
label(0x10E6, "wksp_fdc_track_1")    # saved track for drive 1
label(0x10E7, "wksp_stack_save")
label(0x10E8, "wksp_fdc_cmd_step")
label(0x10FE, "wksp_alt_csd_sector")  # alt workspace CSD sector

# ---------------------------------------------------------------------------
# Paged workspace: directory buffer (&1200-&16FF)
#
# A directory is 5 contiguous sectors (1280 bytes = &500).
# Directory entries are 26 bytes each, max 47 entries.
# &1200 = master sequence number (1 byte)
# &1201 = identity string "Hugo" (4 bytes)
# &1205 = first directory entry (26 bytes)
# ...
# &16CB = last possible entry end
# &16CC = directory name (10 bytes)
# &16D6 = parent sector pointer (3 bytes)
# &16D9 = directory title (19 bytes)
# &16FA = master sequence number (repeated)
# &16FB = identity string "Hugo" (repeated, 4 bytes)
# &16FF = reserved
# ---------------------------------------------------------------------------

label(0x1200, "dir_buffer")
label(0x1205, "dir_first_entry")
label(0x16B1, "dir_last_entry_area")
label(0x16CC, "dir_name")
label(0x16D6, "dir_parent_sector")
label(0x16D9, "dir_title")
label(0x16FA, "dir_master_sequence")
label(0x16FB, "dir_identity_string")

# ---------------------------------------------------------------------------
# Random access file buffers (&1700-&1BFF)
# Also used as temporary workspace (e.g. *CDIR buffer)
# ---------------------------------------------------------------------------

label(0x1700, "ra_buffer_1")
label(0x1800, "ra_buffer_2")
label(0x1900, "ra_buffer_3")
label(0x1A00, "ra_buffer_4")
label(0x1B00, "ra_buffer_5")

# Second directory buffer (for parent directory operations)
label(0x1BCC, "dir2_name")
label(0x1BD6, "dir2_parent_sector")
label(0x1BD9, "dir2_title")
label(0x1BFA, "dir2_master_sequence")

# ---------------------------------------------------------------------------
# NMI workspace (&0D00-&0D5F)
# ---------------------------------------------------------------------------

label(0x0D00, "nmi_workspace")
label(0x0D05, "nmi_rw_opcode")         # self-modified LDA/STA for read/write direction
label(0x0D0A, "nmi_rw_code")           # variable NMI code block (Tube/direct handlers copied here)
label(0x0D0B, "nmi_write_addr_lo")     # write handler: self-modified transfer address low
label(0x0D0C, "nmi_write_addr_hi")     # write handler: self-modified transfer address high
label(0x0D0E, "nmi_read_addr_lo")      # read handler: self-modified transfer address low
label(0x0D0F, "nmi_read_addr_hi")      # read handler: self-modified transfer address high
label(0x0D34, "nmi_saved_rom")         # patched ROM number for multi-sector NMI handler
label(0x0D56, "nmi_step_rate")         # FDC step rate / settle delay value
label(0x0D57, "nmi_tracks_remaining")  # full tracks remaining in multi-sector op
label(0x0D58, "nmi_secs_this_track")   # sectors remaining on current track
label(0x0D59, "nmi_secs_last_track")   # partial sectors remaining on last track
label(0x0D5A, "nmi_sec_position")      # current sector position counter within track
label(0x0D5C, "nmi_drive_cmd")         # drive select + step rate command bits
label(0x0D5D, "nmi_adfs_flags")        # copy of ADFS flags for NMI completion polling
label(0x0D5E, "nmi_drive_ctrl")        # FDC drive control byte (side/drive select)
label(0x0D5F, "nmi_completion")        # NMI transfer completion flag

# ---------------------------------------------------------------------------
# ROM workspace table and FSM indexed bases (&0DF0-&0DFF)
# ---------------------------------------------------------------------------

label(0x0DF0, "rom_wksp_table")        # per-ROM workspace page table (standard Acorn)
label(0x0DFA, "fsm_s0_pre6")           # X-indexed base: +6 reaches FSM sector 0 start
label(0x0DFD, "fsm_s0_pre3")           # X-indexed base: +3 reaches FSM sector 0 start
label(0x0DFF, "fsm_s0_pre1")           # X/Y-indexed base: +1 reaches FSM sector 0

# ---------------------------------------------------------------------------
# MOS vectors and system variables
# ---------------------------------------------------------------------------

label(0x0212, "filev")
label(0x021E, "fscv")
label(0x028D, "last_break_type")

# ---------------------------------------------------------------------------
# ROM code labels
#
# From ADFS-multi-target bbcSCSI build (byte-identical to ADFS 1.30).
# Names converted to snake_case and curated for our conventions.
# ---------------------------------------------------------------------------

# Tube claim/release wrappers
entry(0x8027)
label(0x8027, "claim_tube")
entry(0x8043)
label(0x8043, "release_tube")

# SCSI low-level routines
entry(0x8056)
label(0x8056, "scsi_get_status")
entry(0x8065)
label(0x8065, "scsi_start_command")
label(0x8067, "scsi_start_command2")
entry(0x8080)
label(0x8080, "command_set_retries")
entry(0x8089)
label(0x8089, "command_exec_xy")
label(0x80A4, "command_exec_retry_loop")
label(0x80C6, "command_exec_start_exec")
label(0x80CC, "command_exec_floppy_op")
entry(0x80ED)
label(0x80ED, "hd_command")
entry(0x818A)
label(0x818A, "command_done")
entry(0x81B8)
label(0x81B8, "hd_data_transfer_256")

# Tube transfer helpers
entry(0x81EF)
label(0x81EF, "tube_start_xfer_sei")
label(0x81F0, "tube_start_xfer")
label(0x81F5, "tube_delay")
label(0x81F8, "tube_delay2")

# SCSI request sense and error handling
entry(0x823A)
label(0x823A, "scsi_request_sense")
entry(0x829A)
label(0x829A, "generate_error")
label(0x82A6, "error_escape_ack_invalidate_reload_fsm")
entry(0x82FB)
label(0x82FB, "scsi_send_cmd_byte")
entry(0x8305)
label(0x8305, "wait_ensuring")
entry(0x830F)
label(0x830F, "scsi_wait_for_req")
entry(0x831B)
label(0x831B, "scsi_send_byte_a")
entry(0x8348)
label(0x8348, "reload_fsm_and_dir_then_brk")
entry(0x8351)
label(0x8351, "generate_error_no_suffix")
entry(0x8353)
label(0x8353, "generate_error_suffix_x")
label(0x83BB, "generate_error_skip_no_suffix")

# Hook print-inline-string routine
# sub_c92a0 pops return address, prints bit-7-terminated string, then
# pushes address past string for RTS to continue execution after.
label(0x92A0, "print_inline_string")
hook_subroutine(0x92A0, "print_inline_string", stringhi_hook)

# Hook inline error blocks
# These routines pop the return address to read inline error data:
#   error_number_byte, "error message", &00
hook_subroutine(0x8348, "reload_fsm_and_dir_then_brk", brk_error_hook)
hook_subroutine(0x832B, "generate_disc_error", brk_error_hook)  # falls through to &8348
hook_subroutine(0x8353, "generate_error_suffix_x", brk_error_hook)
hook_subroutine(0x83BB, "generate_error_skip_no_suffix", brk_error_hook)
hook_subroutine(0x8351, "generate_error_no_suffix", brk_error_hook)

# String data
entry(0x841C)
label(0x841C, "str_at")
label(0x8421, "str_on_channel")

# Number parsing
entry(0x842D)
label(0x842D, "error_append_hex")
entry(0x843E)
label(0x843E, "hex_digit")
entry(0x8449)
label(0x8449, "error_append_dec")

# FSM/directory invalidation and reload
entry(0x8476)
label(0x8476, "invalidate_fsm_and_dir")

# String data and utility
label(0x8499, "str_exec_abbrev")
stringcr(0x8499)
comment(0x8499, '"E." + CR: *EXEC abbreviation', inline=True)
label(0x849C, "str_spool_abbrev")
stringcr(0x849C)
comment(0x849C, '"SP." + CR: *SPOOL abbreviation', inline=True)
entry(0x84A0)
label(0x84A0, "osbyte_y_ff_x_00")
label(0x84A2, "osbyte_x_00")
entry(0x84A7)
label(0x84A7, "oscli_at_x")
label(0x84AC, "str_yes")
stringcr(0x84AC)
comment(0x84AC, 'CR + "SEY": reversed "YES" + CR', inline=True)
label(0x84B0, "str_hugo")
stringz(0x84B0)
comment(0x84B0, 'NUL + "Hugo": directory identity', inline=True)

# Partial sector operations
entry(0x8B1E)
label(0x8B1E, "floppy_partial_sector")
entry(0x8B41)
label(0x8B41, "hd_command_partial_sector")

# Open file checking
entry(0x8D21)
label(0x8D21, "check_open")

# Star commands
entry(0x9109)
label(0x9109, "star_remove")
entry(0x923E)
label(0x923E, "osfile_handler")
entry(0x9433)
label(0x9433, "star_ex")
entry(0x94E7)
label(0x94E7, "star_info")
entry(0x953F)
label(0x953F, "star_dir")
entry(0x9570)
label(0x9570, "star_cdir")
entry(0x993D)
label(0x993D, "star_access")
entry(0x99E6)
label(0x99E6, "star_destroy")
label(0x9A43, "jmp_indirect_fscv")

# Hard drive initialisation and detection
entry(0x9A63)
label(0x9A63, "hd_init_detect")

# Service call entry and dispatch
entry(0x9AA3)
label(0x9AA3, "service_call_handler")
label(0x9AB8, "service_handler_0")
label(0x9ACF, "service_handler_1")
label(0x9AF1, "service_handler_2")
label(0x9B41, "service_handler_3")

# Service call dispatch table (RTS trick)
# Low bytes at &9A8F, high bytes at &9A99, 10 entries (services 0-9)
label(0x9A8F, "service_dispatch_lo")
label(0x9A99, "service_dispatch_hi")
for i in range(10):
    rts_code_ptr(0x9A8F + i, 0x9A99 + i)

# OSFILE dispatch table (RTS trick)
# Interleaved [lo, hi] pairs at offsets 2,4,6,8,... from &9269.
# X = A*2+2; loads dispatch_hi,X and dispatch_lo,X.
# A=0: &8C05 (save file - check existing and overwrite)
# A=1-4: write cat info (load/exec addr, attributes)
# A=5: read cat info
# A=6: delete file
# A=7: create file
label(0x9269, "osfile_dispatch_lo")
label(0x926A, "osfile_dispatch_hi")
byte(0x9269)
expr(0x9269, "<(osfile_save_check_existing-1)")
comment(0x9269, "A=0 lo-1: OSFILE save", inline=True)
byte(0x926A)
expr(0x926A, ">(osfile_save_check_existing-1)")
comment(0x926A, "A=0 hi-1: OSFILE save", inline=True)
for i in range(8):
    rts_code_ptr(0x9269 + 2 + i*2, 0x926A + 2 + i*2)

# OSFILE A=0 entry point: the dispatch table's first entry points
# to &8C04 (RTS trick -> &8C05). py8dis cannot trace through the
# RTS-trick dispatch, so this code must be marked as an entry point.
entry(0x8C05)
label(0x8C05, "osfile_save_check_existing")

# Fix code regions that follow print_inline_string calls
# where py8dis doesn't trace the continuation correctly.
entry(0xA029)  # After "Free\r" inline string in star_free
entry(0xA05F)  # After "Address :  Length" in star_map
entry(0xA07F)  # After "  : &" in star_map
entry(0xA1E6)  # After " Sectors = " in print_space_value
entry(0xA251)  # RTS after " Bytes " in print_space_value
entry(0x9A0A)  # After "Destroy ? " in star_destroy
entry(0x9373)  # After "Option " in verify_dir_and_list
entry(0x9399)  # After ")\rDir. " in catalogue header
entry(0x93B3)  # After "     Lib. " in catalogue header
entry(0x9DBD)  # RTS after "Advanced DFS 1.30" in help_print_header
entry(0xA0BA)  # RTS after "Compaction recommended" in check_compaction

# The inline string at &9392 is ")\rDir." + &A0 (space+bit7).
# The stringhi_hook classifies this as one string; we can't
# split it with byte()/string() without conflicting with the hook.
# Instead, add a comment explaining the structure.
comment(0x9392, '")" + CR + "Dir." + space: option close + dir label', inline=True)

# *HELP command list printing code
# The code from &9E16 onwards prints the command list for *HELP ADFS.
# The print_inline_string at &9E12 has a 2-byte inline string " \xa0"
# (space, space+bit7). py8dis doesn't trace past it correctly so
# the continuation code at &9E17 appears as data.
# Force it as code:
entry(0x9E17)

# FSCV dispatch table (RTS trick)
# Low bytes at &9E6D, high bytes at &9E76, 9 entries (FSC 0-8)
label(0x9E6D, "fscv_dispatch_lo")
label(0x9E76, "fscv_dispatch_hi")
for i in range(9):
    rts_code_ptr(0x9E6D + i, 0x9E76 + i)

# Extended vector table
label(0x9CC1, "tbl_extended_vectors")
label(0x9CD6, "str_filing_system_name")
label(0x9CDA, "service_handler_4")
label(0x9D19, "service_handler_8")
label(0x9DBE, "service_handler_9")

# Filing system control vector
entry(0x9E50)
label(0x9E50, "fscv_handler")
entry(0x9E7F)
label(0x9E7F, "star_cmd")
label(0x9EE3, "tbl_commands")

# More star commands
entry(0xA01B)
label(0xA01B, "star_free")
entry(0xA04A)
label(0xA04A, "star_map")
entry(0xA0BB)
label(0xA0BB, "star_delete")
entry(0xA0C3)
label(0xA0C3, "star_bye")
entry(0xA111)
label(0xA111, "star_dismount")
entry(0xA15E)
label(0xA15E, "star_mount")
label(0xA19F, "scsi_cmd_unpark")
entry(0xA252)
label(0xA252, "star_title")
entry(0xA276)
label(0xA276, "star_compact")
entry(0xA399)
label(0xA399, "star_run")
entry(0xA444)
label(0xA444, "star_lib")
entry(0xA47F)
label(0xA47F, "star_lcat")
entry(0xA48B)
label(0xA48B, "star_lex")
entry(0xA497)
label(0xA497, "star_back")
entry(0xA503)
label(0xA503, "star_rename")

# Directory and workspace checksum
entry(0xA6C7)
label(0xA6C7, "check_dir_loaded")
entry(0xA70E)
label(0xA70E, "get_wksp_addr_ba")
entry(0xA71A)
label(0xA71A, "calc_wksp_checksum")
label(0xA72B, "store_wksp_checksum_ba_y")
entry(0xA731)
label(0xA731, "check_wksp_checksum")

# FSM loading
entry(0xA816)
label(0xA816, "load_fsm")
entry(0xA81D)
label(0xA81D, "star_copy")

# Filing system selection
entry(0xA93C)
label(0xA93C, "fsc6_new_filing_system")

# OSARGS handler
entry(0xA955)
label(0xA955, "osargs_handler")

# Channel I/O
entry(0xAAC6)
label(0xAAC6, "hd_command_bget_bput_sector")
entry(0xAB4B)
label(0xAB4B, "hd_bput_write_sector")
label(0xAB78, "svc5_irq")
entry(0xACB2)
label(0xACB2, "hd_bget_read_sector")
entry(0xACFE)
label(0xACFE, "check_set_channel_y")
entry(0xAD16)
label(0xAD16, "compare_ext_to_ptr")
entry(0xAD63)
label(0xAD63, "osbget_handler")
entry(0xB08F)
label(0xB08F, "osbput_handler")
entry(0xB1B3)
label(0xB1B3, "star_close")
entry(0xB1B6)
label(0xB1B6, "osfind_handler")
entry(0xB57F)
label(0xB57F, "osgbpb_handler")

# Floppy disc driver entry points (indirect jump table)
label(0xBA00, "floppy_command_ind")
label(0xBA03, "exec_floppy_partial_sector_buf_ind")
label(0xBA06, "exec_floppy_write_bput_sector_ind")
label(0xBA09, "exec_floppy_read_bput_sector_ind")
entry(0xBA11)
label(0xBA11, "floppy_check_present")
entry(0xBA26)
label(0xBA26, "exec_floppy_write_bput_sector")
entry(0xBA2A)
label(0xBA2A, "exec_floppy_read_bput_sector")
entry(0xBB14)
label(0xBB14, "floppy_command")
entry(0xBB25)
label(0xBB25, "exec_floppy_partial_sector_buf")
entry(0xBBB4)
label(0xBBB4, "floppy_get_step_rate")
entry(0xBBF1)
label(0xBBF1, "copy_code_to_nmi_space")
# Main NMI handler: 73 bytes at &BC79-&BCC1 copied to &0D00-&0D48
# at runtime by copy_code_to_nmi_space.
nmi_main_move_id = move(0x0D00, 0xBC79, 0x49)
with nmi_main_move_id:
    entry(0x0D00)
    entry(0x0D0A)
    entry(0x0D18)
    label(0x0D1A, "nmi_check_status_error")
    entry(0x0D1A)
    label(0x0D25, "nmi_set_transfer_complete")
    entry(0x0D25)
    label(0x0D2C, "nmi_check_end_of_operation")
    entry(0x0D2C)

entry(0xBCC2)
label(0xBCC2, "floppy_wait_nmi_finish")

# NMI handler code fragments: all three are copied to &0D0A at
# runtime. Each uses move() with a context manager so py8dis can
# disambiguate the overlapping runtime addresses.
nmi_write_move_id = move(0x0D0A, 0xBCDF, 14)
with nmi_write_move_id:
    entry(0x0D0A)

nmi_tube_write_move_id = move(0x0D0A, 0xBCED, 8)
with nmi_tube_write_move_id:
    entry(0x0D0A)

nmi_tube_read_move_id = move(0x0D0A, 0xBCF5, 8)
with nmi_tube_read_move_id:
    entry(0x0D0A)
label(0xBD19, "floppy_set_side_0_unused")
entry(0xBD19)
comment(0xBD19, "Get NMI drive control byte", inline=True)
comment(0xBD1C, "Clear bit 2 (select side 0)", inline=True)
comment(0xBD1E, "Store updated control byte", inline=True)
comment(0xBD21, "Return", inline=True)
entry(0xBD22)
label(0xBD22, "floppy_set_side_1")
entry(0xBD3F)
label(0xBD3F, "floppy_restore_track_0")
entry(0xBF55)
label(0xBF55, "floppy_ts_block_check_range")
entry(0xBF86)
label(0xBF86, "floppy_ts_b0_block")
label(0xBF8E, "floppy_ts_xa")
entry(0xBFA2)
label(0xBFA2, "xa_div_16_to_ya")
entry(0xBFAE)
label(0xBFAE, "floppy_error")

# ---------------------------------------------------------------------------
# Additional entry points from audit --undeclared
# These are JSR targets that need subroutine() declarations.
# ---------------------------------------------------------------------------

entry(0x803B)
entry(0x81DD)
entry(0x81F0)
entry(0x81F8)
entry(0x8287)
entry(0x828B)
entry(0x8301)
entry(0x832B)
entry(0x8436)
entry(0x8459)
entry(0x84B5)
entry(0x8609)
entry(0x8632)
entry(0x8708)
entry(0x870F)
entry(0x871A)
entry(0x872D)
entry(0x8753)
entry(0x87E7)
entry(0x8822)
entry(0x884C)
entry(0x8851)
entry(0x895E)
entry(0x89D0)
entry(0x89D3)
entry(0x8A3D)
entry(0x8A45)
entry(0x8B04)
entry(0x8BB3)
entry(0x8BE5)
entry(0x8C10)
entry(0x8C62)
entry(0x8C65)
entry(0x8CC9)
entry(0x8CE2)
entry(0x8CE9)
entry(0x8D10)
entry(0x8D6E)
entry(0x8DBD)
entry(0x8DD6)
entry(0x8DF3)
entry(0x8DF6)
entry(0x8E6F)
entry(0x8E8B)
entry(0x8F4C)
entry(0x8F52)
entry(0x8F58)
entry(0x8F86)
entry(0x8FDF)
entry(0x8FEA)
entry(0x9009)
entry(0x905C)
entry(0x9212)
entry(0x9287)
entry(0x92A0)
entry(0x92C4)
entry(0x92DE)
entry(0x931B)
entry(0x9324)
entry(0x932A)
entry(0x93C5)
entry(0x93D4)
entry(0x9436)
entry(0x944F)
entry(0x9471)
entry(0x947F)
entry(0x94FA)
entry(0x9501)
entry(0x9642)
entry(0x96A6)
entry(0x97A8)
entry(0x98AE)
entry(0x9945)
entry(0x9A6C)
entry(0xA016)
entry(0xA0F5)
entry(0xA149)
entry(0xA161)
entry(0xA1AA)
entry(0xA1C6)
entry(0xA35A)
entry(0xA365)
entry(0xA460)
entry(0xA473)
entry(0xA4B7)
entry(0xA4CF)
entry(0xA4F6)
entry(0xA685)
entry(0xA6DE)
entry(0xA749)
entry(0xA797)
entry(0xA7A2)
entry(0xA7C0)
entry(0xA7F5)
entry(0xA97C)
entry(0xA998)
entry(0xAAA6)
entry(0xAAF3)
entry(0xABA5)
entry(0xABC9)
entry(0xABD8)
entry(0xACD7)
entry(0xACF5)
entry(0xADA8)
entry(0xADC5)
entry(0xAE59)
entry(0xAE5E)
entry(0xB123)
entry(0xB13F)
entry(0xB18C)
entry(0xB3B6)
entry(0xB468)
entry(0xB47C)
entry(0xB48E)
entry(0xB4BF)
entry(0xB4F5)
entry(0xB510)
entry(0xB51C)
entry(0xB579)
entry(0xB825)
entry(0xB85B)
entry(0xB872)
entry(0xB8FC)
entry(0xB980)
entry(0xBA06)
entry(0xBA09)
entry(0xBA0C)
entry(0xBAC6)
entry(0xBB09)
entry(0xBB42)
entry(0xBB92)
entry(0xBBDA)
entry(0xBBE7)
entry(0xBC2D)
entry(0xBC5C)
entry(0xBCFD)
entry(0xBD2B)
entry(0xBD31)
entry(0xBD38)
entry(0xBD4C)
entry(0xBD58)
entry(0xBDA6)
entry(0xBE84)

# ---------------------------------------------------------------------------
# Additional entry points: labels preceded by RTS/JMP with refs >= 2,
# or labels with in-degree >= 4. These get visual separator blocks in
# the assembly output, making the code much easier to read.
# ---------------------------------------------------------------------------

entry(0x80C6)
entry(0x8159)
entry(0x8282)
entry(0x8291)
entry(0x856B)
entry(0x85C1)
entry(0x8737)
entry(0x8798)
entry(0x87A8)
entry(0x87CB)
entry(0x87CF)
entry(0x8849)
entry(0x8905)
entry(0x8A63)
entry(0x8BC8)
entry(0x8CC3)
entry(0x8D69)
entry(0x8DD5)
entry(0x8DDB)
entry(0x8DDE)
entry(0x8FFA)
entry(0x9128)
entry(0x927B)
entry(0x9299)
entry(0x94EF)
entry(0x977D)
entry(0x9951)
entry(0x9AE6)
entry(0x9B6E)
entry(0x9C74)
entry(0x9D11)
entry(0x9D63)
entry(0x9D6A)
entry(0x9DDA)
entry(0xA049)
entry(0xA29B)
entry(0xA344)
entry(0xA434)
entry(0xA6F9)
entry(0xA72B)
entry(0xA738)
entry(0xAB63)
entry(0xAC62)
entry(0xACE9)
entry(0xAD39)
entry(0xAD53)
entry(0xAD8D)
entry(0xAE4C)
entry(0xAEBC)
entry(0xB00D)
entry(0xB060)
entry(0x8BD7)
entry(0x8BF0)
entry(0xBA03)
entry(0xB218)
entry(0xB24D)
entry(0xB3F1)
entry(0xB4AE)
entry(0xB5C8)
entry(0xB8DB)
entry(0xBAF4)
entry(0xBB82)

# Interstitial data block entries (visual separation for data between routines)
entry(0x8499)
# FSM read template: individual fields annotated
label(0x880C, "disc_op_tpl_read_fsm")
entry(0x880C)
byte(0x880C)
comment(0x880C, "Result: &01 (default)", inline=True)
byte(0x880D)
comment(0x880D, "Memory address low: &00", inline=True)
byte(0x880E)
comment(0x880E, "Memory address high: &0E (-> &0E00 FSM buffer)", inline=True)
byte(0x880F)
comment(0x880F, "Memory address byte 3: &FF (host memory)", inline=True)
byte(0x8810)
comment(0x8810, "Memory address byte 4: &FF (host memory)", inline=True)
byte(0x8811)
comment(0x8811, "Command: &08 (read sectors)", inline=True)
byte(0x8812)
comment(0x8812, "Sector high: &00", inline=True)
byte(0x8813)
comment(0x8813, "Sector mid: &00", inline=True)
byte(0x8814)
comment(0x8814, "Sector low: &00 (sector 0)", inline=True)
byte(0x8815)
comment(0x8815, "Sector count: &02 (2 sectors for FSM)", inline=True)

# Padding byte + directory read template
label(0x8816, "disc_op_tpl_padding")
byte(0x8816)
comment(0x8816, "Padding: &00 (for 12-byte copy from &1014)", inline=True)

label(0x8817, "disc_op_tpl_read_dir")
entry(0x8817)
byte(0x8817)
comment(0x8817, "Result: &01 (default)", inline=True)
byte(0x8818)
comment(0x8818, "Memory address low: &00", inline=True)
byte(0x8819)
comment(0x8819, "Memory address high: &12 (-> &1200 dir buffer)", inline=True)
byte(0x881A)
comment(0x881A, "Memory address byte 3: &FF (host memory)", inline=True)
byte(0x881B)
comment(0x881B, "Memory address byte 4: &FF (host memory)", inline=True)
byte(0x881C)
comment(0x881C, "Command: &08 (read sectors)", inline=True)
byte(0x881D)
comment(0x881D, "Sector high: &00", inline=True)
byte(0x881E)
comment(0x881E, "Sector mid: &00", inline=True)
byte(0x881F)
comment(0x881F, "Sector low: &02 (sector 2 = root dir)", inline=True)
byte(0x8820)
comment(0x8820, "Sector count: &05 (5 sectors per directory)", inline=True)
byte(0x8821)
comment(0x8821, "Control: &00", inline=True)
label(0x8DED, "tbl_forbidden_chars")
entry(0x8DED)
byte(0x8DED)
comment(0x8DED, "&7F: DEL (control character)", inline=True)
byte(0x8DEE)
comment(0x8DEE, "'^': parent directory specifier", inline=True)
byte(0x8DEF)
comment(0x8DEF, "'@': current directory specifier", inline=True)
byte(0x8DF0)
comment(0x8DF0, "':': drive separator", inline=True)
byte(0x8DF1)
comment(0x8DF1, "'$': root directory specifier", inline=True)
byte(0x8DF2)
comment(0x8DF2, "'&': hex number prefix", inline=True)
label(0x9071, "disc_op_tpl_write_fsm")
entry(0x9071)
byte(0x9071)
comment(0x9071, "Result: &01 (default)", inline=True)
byte(0x9072)
comment(0x9072, "Memory address low: &00", inline=True)
byte(0x9073)
comment(0x9073, "Memory address high: &0E (-> &0E00 FSM buffer)", inline=True)
byte(0x9074)
comment(0x9074, "Memory address byte 3: &FF (host memory)", inline=True)
byte(0x9075)
comment(0x9075, "Memory address byte 4: &FF (host memory)", inline=True)
byte(0x9076)
comment(0x9076, "Command: &0A (write sectors)", inline=True)
byte(0x9077)
comment(0x9077, "Sector high: &00", inline=True)
byte(0x9078)
comment(0x9078, "Sector mid: &00", inline=True)
byte(0x9079)
comment(0x9079, "Sector low: &00 (sector 0)", inline=True)
byte(0x907A)
comment(0x907A, "Sector count: &02 (2 sectors for FSM)", inline=True)
byte(0x907B)
comment(0x907B, "Control: &00", inline=True)
entry(0x9269)
label(0x94CC, "dummy_root_dir_entry")
entry(0x94CC)
byte(0x94CC)
comment(0x94CC, "'$' + bit 7 (R access): filename char 0", inline=True)
byte(0x94CD)
comment(0x94CD, "CR: filename padding char 1", inline=True)
byte(0x94CE)
comment(0x94CE, "CR + bit 7 (L access): filename char 2", inline=True)
byte(0x94CF)
comment(0x94CF, "CR + bit 7 (D=directory): filename char 3", inline=True)
byte(0x94D0, 6)
comment(0x94D0, "CR padding: filename chars 4-9", inline=True)
byte(0x94D6, 4)
comment(0x94D6, "Load address: &00000000", inline=True)
byte(0x94DA, 4)
comment(0x94DA, "Exec address: &00000000", inline=True)
byte(0x94DE)
comment(0x94DE, "Length low: &00", inline=True)
byte(0x94DF)
comment(0x94DF, "Length byte 1: &05 (5 sectors = &500 bytes)", inline=True)
byte(0x94E0, 2)
comment(0x94E0, "Length bytes 2-3: &0000", inline=True)
byte(0x94E2)
comment(0x94E2, "Start sector low: &02 (root directory)", inline=True)
byte(0x94E3, 2)
comment(0x94E3, "Start sector mid/high: &0000", inline=True)
byte(0x94E5)
comment(0x94E5, "Sequence number: &00", inline=True)
byte(0x94E6)
comment(0x94E6, "Padding: &00", inline=True)
label(0x9632, "osfile_tpl_cdir")
entry(0x9632)
byte(0x9632, 4)
comment(0x9632, "Load address: &00000000 (not used)", inline=True)
byte(0x9636, 4)
comment(0x9636, "Exec address: &00000000 (not used)", inline=True)
byte(0x963A)
comment(0x963A, "Data start low: &00", inline=True)
byte(0x963B)
comment(0x963B, "Data start high: &17 (-> &1700 ra_buffer_1)", inline=True)
byte(0x963C)
comment(0x963C, "Data start byte 3: &FF (host memory)", inline=True)
byte(0x963D)
comment(0x963D, "Data start byte 4: &FF (host memory)", inline=True)
byte(0x963E)
comment(0x963E, "Data end low: &00", inline=True)
byte(0x963F)
comment(0x963F, "Data end high: &1C (-> &1C00, 5 pages)", inline=True)
byte(0x9640)
comment(0x9640, "Data end byte 3: &FF (host memory)", inline=True)
byte(0x9641)
comment(0x9641, "Data end byte 4: &FF (host memory)", inline=True)
stringcr(0x993B)
comment(0x993B, 'Unused "^" + CR: dead remnant', inline=True)
stringcr(0xB9FE)
comment(0xB9FE, 'Unused "." + CR: dead remnant', inline=True)
# SCSI park heads control block (used by *BYE via X=&EA, Y=&A0)
label(0xA0EA, "scsi_cmd_park")
entry(0xA0EA)

# SCSI unpark heads control block (used by *MOUNT via X=&9F, Y=&A1)
entry(0xA19F)
byte(0xA19F)
comment(0xA19F, "Result: &00", inline=True)
byte(0xA1A0)
comment(0xA1A0, "Memory address low: &00", inline=True)
byte(0xA1A1)
comment(0xA1A1, "Memory address high: &17 (buffer page)", inline=True)
byte(0xA1A2)
comment(0xA1A2, "Memory address byte 3: &FF (host memory)", inline=True)
byte(0xA1A3)
comment(0xA1A3, "Memory address byte 4: &FF (host memory)", inline=True)
byte(0xA1A4)
comment(0xA1A4, "Command: &1B (SCSI Start/Stop Unit)", inline=True)
byte(0xA1A5)
comment(0xA1A5, "Sector high: &00", inline=True)
byte(0xA1A6)
comment(0xA1A6, "Sector mid: &00", inline=True)
byte(0xA1A7)
comment(0xA1A7, "Sector low: &00", inline=True)
byte(0xA1A8)
comment(0xA1A8, "Sector count: &01 (start/unpark heads)", inline=True)
byte(0xA1A9)
comment(0xA1A9, "Control: &00", inline=True)
byte(0xA0EA)
comment(0xA0EA, "Result: &00", inline=True)
byte(0xA0EB)
comment(0xA0EB, "Memory address low: &00", inline=True)
byte(0xA0EC)
comment(0xA0EC, "Memory address high: &17 (buffer page)", inline=True)
byte(0xA0ED)
comment(0xA0ED, "Memory address byte 3: &FF (host memory)", inline=True)
byte(0xA0EE)
comment(0xA0EE, "Memory address byte 4: &FF (host memory)", inline=True)
byte(0xA0EF)
comment(0xA0EF, "Command: &1B (SCSI Start/Stop Unit)", inline=True)
byte(0xA0F0)
comment(0xA0F0, "Sector high: &00", inline=True)
byte(0xA0F1)
comment(0xA0F1, "Sector mid: &00", inline=True)
byte(0xA0F2)
comment(0xA0F2, "Sector low: &00", inline=True)
byte(0xA0F3)
comment(0xA0F3, "Sector count: &00 (stop/park heads)", inline=True)
byte(0xA0F4)
comment(0xA0F4, "Control: &00", inline=True)
entry(0x9316)
entry(0x9A46)
label(0x9A46, "default_workspace_data")
label(0x9A50, "default_lib_name")
label(0x9A5A, "default_csd_sector")
label(0x9A5E, "default_lib_sector")
label(0x9A62, "default_prev_dir_sector")
string(0x9A46, 10)
comment(0x9A46, "'$' + 9 spaces: default CSD name", inline=True)
string(0x9A50, 10)
comment(0x9A50, "'$' + 9 spaces: default library name", inline=True)
byte(0x9A5A)
comment(0x9A5A, "CSD sector low: 2 (root directory)", inline=True)
byte(0x9A5B)
comment(0x9A5B, "CSD sector mid: 0", inline=True)
byte(0x9A5C)
comment(0x9A5C, "CSD sector high: 0", inline=True)
byte(0x9A5D)
comment(0x9A5D, "Current drive: 0", inline=True)
byte(0x9A5E)
comment(0x9A5E, "Library sector low: 2 (root directory)", inline=True)
byte(0x9A5F)
comment(0x9A5F, "Library sector mid: 0", inline=True)
byte(0x9A60)
comment(0x9A60, "Library sector high: 0", inline=True)
byte(0x9A61)
comment(0x9A61, "Library drive: 0", inline=True)
byte(0x9A62)
comment(0x9A62, "Previous dir sector low: 2 (root dir)", inline=True)
label(0x9A78, "boot_option_addr_table")
entry(0x9A78)
byte(0x9A78)
expr(0x9A78, "<(str_l_boot)")
comment(0x9A78, "Option 1: *LOAD $.!BOOT", inline=True)
byte(0x9A79)
expr(0x9A79, "<(str_run_boot)")
comment(0x9A79, "Option 2: *RUN $.!BOOT", inline=True)
byte(0x9A7A)
expr(0x9A7A, "<(str_e_boot)")
comment(0x9A7A, "Option 3: *EXEC $.!BOOT", inline=True)
entry(0x9A8F)
label(0x9CB3, "tbl_fs_vectors")
entry(0x9CB3)
word(0x9CB3)
comment(0x9CB3, "FILEV: &FF1B (OSFILE)", inline=True)
word(0x9CB5)
comment(0x9CB5, "ARGSV: &FF1E (OSARGS)", inline=True)
word(0x9CB7)
comment(0x9CB7, "BGETV: &FF21 (OSBGET)", inline=True)
word(0x9CB9)
comment(0x9CB9, "BPUTV: &FF24 (OSBPUT)", inline=True)
word(0x9CBB)
comment(0x9CBB, "GBPBV: &FF27 (OSGBPB)", inline=True)
word(0x9CBD)
comment(0x9CBD, "FINDV: &FF2A (OSFIND)", inline=True)
word(0x9CBF)
comment(0x9CBF, "FSCV:  &FF2D (FSC)", inline=True)
entry(0x9CC1)
# Extended vector table: 7 entries of 3 bytes (addr, ROM)
# ROM byte is &FF, patched to actual ROM number at install time.
word(0x9CC1)
comment(0x9CC1, "FILEV: osfile_handler (&923E)", inline=True)
byte(0x9CC3)
comment(0x9CC3, "ROM: &FF (patched at runtime)", inline=True)
word(0x9CC4)
comment(0x9CC4, "ARGSV: osargs_handler (&A955)", inline=True)
byte(0x9CC6)
comment(0x9CC6, "ROM: &FF", inline=True)
word(0x9CC7)
comment(0x9CC7, "BGETV: osbget_handler (&AD63)", inline=True)
byte(0x9CC9)
comment(0x9CC9, "ROM: &FF", inline=True)
word(0x9CCA)
comment(0x9CCA, "BPUTV: osbput_handler (&B08F)", inline=True)
byte(0x9CCC)
comment(0x9CCC, "ROM: &FF", inline=True)
word(0x9CCD)
comment(0x9CCD, "GBPBV: osgbpb_handler (&B57F)", inline=True)
byte(0x9CCF)
comment(0x9CCF, "ROM: &FF", inline=True)
word(0x9CD0)
comment(0x9CD0, "FINDV: osfind_handler (&B1B6)", inline=True)
byte(0x9CD2)
comment(0x9CD2, "ROM: &FF", inline=True)
word(0x9CD3)
comment(0x9CD3, "FSCV:  fscv_handler (&9E50)", inline=True)
byte(0x9CD5)
comment(0x9CD5, "ROM: &FF", inline=True)
entry(0x9CD6)
label(0x9E48, "tbl_help_param_ptrs")
entry(0x9E48)
_help_param_ptrs = [
    (0x9E48, "help_param_none",         '(no parameter)'),
    (0x9E49, "help_param_list_spec",    '"<List Spec>"'),
    (0x9E4A, "help_param_ob_spec",      '"<Ob Spec>"'),
    (0x9E4B, "help_param_wild_ob_spec", '"<*Ob Spec*>"'),
    (0x9E4C, "help_param_drive",        '"(<Drive>)"'),
    (0x9E4D, "help_param_sp_lp",        '"<SP> <LP>"'),
    (0x9E4E, "help_param_access",       '"(L)(W)(R)(E)"'),
    (0x9E4F, "help_param_title",        '"<Title>"'),
]
for addr, target, desc in _help_param_ptrs:
    byte(addr)
    expr(addr, f"<({target})")
    comment(addr, desc, inline=True)
entry(0x9E6D)
entry(0x9EE3)

# Command table: force all entries as data (name string + 3 bytes)
# Format: ASCII name, HI(handler-1), LO(handler-1), param_nibbles
# Dispatch uses the RTS trick: address stored is handler-1.
_cmd_table = [
    # (name_addr, name_len, name,       hi_addr, lo_addr, param_addr, handler_label,   params_desc)
    (0x9EE3, 6, "ACCESS",  0x9EE9, 0x9EEA, 0x9EEB, "star_access",  "Params &16: <List Spec> (L)(W)(R)(E)"),
    (0x9EEC, 4, "BACK",    0x9EF0, 0x9EF1, 0x9EF2, "star_back",    "Params &00: (none)"),
    (0x9EF3, 3, "BYE",     0x9EF6, 0x9EF7, 0x9EF8, "star_bye",     "Params &00: (none)"),
    (0x9EF9, 4, "CDIR",    0x9EFD, 0x9EFE, 0x9EFF, "star_cdir",    "Params &20: <Ob Spec>"),
    (0x9F00, 5, "CLOSE",   0x9F05, 0x9F06, 0x9F07, "star_close",   "Params &00: (none)"),
    (0x9F08, 7, "COMPACT", 0x9F0F, 0x9F10, 0x9F11, "star_compact", "Params &50: <SP> <LP>"),
    (0x9F12, 4, "COPY",    0x9F16, 0x9F17, 0x9F18, "star_copy",    "Params &13: <List Spec> <*Ob Spec*>"),
    (0x9F19, 6, "DELETE",  0x9F1F, 0x9F20, 0x9F21, "star_delete",  "Params &20: <Ob Spec>"),
    (0x9F22, 7, "DESTROY", 0x9F29, 0x9F2A, 0x9F2B, "star_destroy", "Params &10: <List Spec>"),
    (0x9F2C, 3, "DIR",     0x9F2F, 0x9F30, 0x9F31, "star_dir",     "Params &20: <Ob Spec>"),
    (0x9F32, 8, "DISMOUNT",0x9F3A, 0x9F3B, 0x9F3C, "star_dismount","Params &40: (<Drive>)"),
    (0x9F3D, 2, "EX",      0x9F3F, 0x9F40, 0x9F41, "star_ex",      "Params &30: <*Ob Spec*>"),
    (0x9F42, 4, "FREE",    0x9F46, 0x9F47, 0x9F48, "star_free",    "Params &00: (none)"),
    (0x9F49, 4, "INFO",    0x9F4D, 0x9F4E, 0x9F4F, "star_info",    "Params &10: <List Spec>"),
    (0x9F50, 4, "LCAT",    0x9F54, 0x9F55, 0x9F56, "star_lcat",    "Params &00: (none)"),
    (0x9F57, 3, "LEX",     0x9F5A, 0x9F5B, 0x9F5C, "star_lex",     "Params &00: (none)"),
    (0x9F5D, 3, "LIB",     0x9F60, 0x9F61, 0x9F62, "star_lib",     "Params &30: <*Ob Spec*>"),
    (0x9F63, 3, "MAP",     0x9F66, 0x9F67, 0x9F68, "star_map",     "Params &00: (none)"),
    (0x9F69, 5, "MOUNT",   0x9F6E, 0x9F6F, 0x9F70, "star_mount",   "Params &40: (<Drive>)"),
    (0x9F71, 6, "REMOVE",  0x9F77, 0x9F78, 0x9F79, "star_remove",  "Params &20: <Ob Spec>"),
    (0x9F7A, 6, "RENAME",  0x9F80, 0x9F81, 0x9F82, "star_rename",  "Params &22: <Ob Spec> <Ob Spec>"),
    (0x9F83, 5, "TITLE",   0x9F88, 0x9F89, 0x9F8A, "star_title",   "Params &70: <Title>"),
]
for name_addr, name_len, name, hi_addr, lo_addr, param_addr, handler, params in _cmd_table:
    string(name_addr, name_len)
    comment(name_addr, f'"{name}" command name', inline=True)
    byte(hi_addr)
    expr(hi_addr, f">({handler}-1)")
    comment(hi_addr, f"Dispatch hi-1 -> {handler}", inline=True)
    byte(lo_addr)
    expr(lo_addr, f"<({handler}-1)")
    comment(lo_addr, f"Dispatch lo-1 -> {handler}", inline=True)
    byte(param_addr)
    comment(param_addr, params, inline=True)
# Final entry: *RUN handler (sentinel, no command name)
byte(0x9F8B)
expr(0x9F8B, "HI(star_run-1)")
comment(0x9F8B, "End: dispatch hi-1 -> star_run", inline=True)
byte(0x9F8C)
expr(0x9F8C, "LO(star_run-1)")
comment(0x9F8C, "End: dispatch lo-1 -> star_run", inline=True)

entry(0xBC79)
label(0xBFF6, "str_rom_footer")
entry(0xBFF6)

# *HELP parameter format strings (referenced by tbl_help_param_ptrs)
label(0x9F8D, "help_param_list_spec")
entry(0x9F8D)
stringz(0x9F8D)
comment(0x9F8D, "Index 1: file list specification", inline=True)
label(0x9F99, "help_param_ob_spec")
stringz(0x9F99)
comment(0x9F99, "Index 2: object specification", inline=True)
label(0x9FA3, "help_param_wild_ob_spec")
stringz(0x9FA3)
comment(0x9FA3, "Index 3: wildcard object specification", inline=True)
label(0x9FAF, "help_param_drive")
stringz(0x9FAF)
comment(0x9FAF, "Index 4: optional drive number", inline=True)
label(0x9FB9, "help_param_sp_lp")
stringz(0x9FB9)
comment(0x9FB9, "Index 5: *COMPACT start/length pages", inline=True)
label(0x9FC3, "help_param_access")
stringz(0x9FC3)
comment(0x9FC3, "Index 6: access attribute flags", inline=True)
label(0x9FD0, "help_param_title")
stringz(0x9FD0)
comment(0x9FD0, "Index 7: directory title string", inline=True)
label(0x9FD7, "help_param_none")  # NUL terminator of help_param_title doubles as empty string

# FSC 7: read file handle range
label(0x9FD8, "fsc7_read_handle_range")
entry(0x9FD8)
comment(0x9FD8, "X=&30 ('0'): lowest ADFS file handle", inline=True)
comment(0x9FDA, "Y=&39 ('9'): highest ADFS file handle", inline=True)
comment(0x9FDC, "Return X=&30, Y=&39 to MOS", inline=True)

# FSC 0: *OPT handler
label(0x9FDD, "fsc0_star_opt")
entry(0x9FDD)

# ===========================================================================
# Code label renames
# ===========================================================================


# ---------------------------------------------------------------------------
# Inline comments
# ---------------------------------------------------------------------------

# claim_tube (&8027)
comment(0x8029, "Is Tube present?", inline=True)
comment(0x802B, "No, return immediately", inline=True)
comment(0x802D, "Copy 4-byte transfer address", inline=True)
comment(0x802F, "Store in Tube transfer workspace", inline=True)
comment(0x8035, "Set bit 6: Tube in use", inline=True)
comment(0x803B, "Claim Tube with A=&C4", inline=True)
comment(0x8040, "Loop until claim succeeds", inline=True)

# release_tube (&8043)
comment(0x8045, "Not in use, return immediately", inline=True)
comment(0x8047, "Release Tube with A=&84", inline=True)
comment(0x804C, "Save interrupt state", inline=True)
comment(0x804E, "Clear bit 6: Tube no longer in use", inline=True)

# scsi_get_status (&8056)
comment(0x8056, "Save processor flags", inline=True)
comment(0x8057, "Read SCSI status register", inline=True)
comment(0x805A, "Store first reading", inline=True)
comment(0x805C, "Read SCSI status register again", inline=True)
comment(0x805F, "Has it settled?", inline=True)
comment(0x8061, "No, try again", inline=True)
comment(0x8063, "Restore processor flags", inline=True)

# command_set_retries (&8080)
comment(0x8080, "Default retry count from workspace", inline=True)

# hd_command (&80ED)
comment(0x80ED, "Byte 6: drive + sector b16-b20", inline=True)
comment(0x80F1, "Combine with current drive", inline=True)
comment(0x80F4, "Bit 7 set = floppy drive", inline=True)
comment(0x80F6, "Select SCSI device and begin command", inline=True)
comment(0x80F9, "Byte 7: sector b8-b15", inline=True)
comment(0x80FC, "Store as memory address low", inline=True)
comment(0x80FE, "Byte 8: sector b0-b7", inline=True)
comment(0x8101, "Store as memory address high", inline=True)
comment(0x8103, "Byte 9: transfer address high", inline=True)
comment(0x8106, "Address >= &FE00?", inline=True)
comment(0x8108, "No, claim Tube for normal transfer", inline=True)
comment(0x810A, "Byte 10: next address byte", inline=True)
comment(0x810D, "Address = &FFxx (host memory)?", inline=True)
comment(0x810F, "Yes, skip Tube claim", inline=True)
comment(0x8114, "Byte 5: SCSI command byte", inline=True)
comment(0x8118, "Send SCSI command byte", inline=True)
comment(0x811B, "Byte 6: drive + sector high", inline=True)
comment(0x811E, "Combine with current drive for LUN", inline=True)
comment(0x8121, "Save combined drive/LUN", inline=True)
comment(0x8127, "Get next command byte", inline=True)
comment(0x8129, "Send command byte to target", inline=True)
comment(0x812C, "Wait for SCSI REQ signal", inline=True)
comment(0x812F, "Status phase? Done sending command", inline=True)
comment(0x8131, "Message phase? Done sending command", inline=True)
comment(0x8133, "Next command byte", inline=True)
comment(0x8136, "Check for 256-byte sector transfer", inline=True)
comment(0x8138, "Get command byte", inline=True)
comment(0x813A, "Mask to read/write bits", inline=True)
comment(0x813C, "Is it a read/write 256-byte command?", inline=True)
comment(0x813E, "Yes, use optimised transfer", inline=True)
comment(0x8140, "Wait for data phase", inline=True)
comment(0x8143, "C=0: write direction", inline=True)
comment(0x8144, "I/O bit clear? Writing", inline=True)
comment(0x8146, "C=1: read direction", inline=True)
comment(0x8147, "Y=0: byte counter for 256-byte page", inline=True)
comment(0x8149, "Tube in use?", inline=True)
comment(0x814B, "No, direct memory transfer", inline=True)
comment(0x814D, "X=&27: Tube workspace addr low", inline=True)
comment(0x8151, "A=0 (direction flag)", inline=True)
comment(0x8153, "Save direction flag", inline=True)
comment(0x8154, "Rotate carry into bit 0", inline=True)
comment(0x8155, "Start Tube transfer", inline=True)
comment(0x8159, "Wait for SCSI REQ", inline=True)
comment(0x815C, "Status phase, transfer done", inline=True)
comment(0x815E, "Tube in use?", inline=True)
comment(0x8160, "Yes, use Tube path", inline=True)
comment(0x8162, "Reading from SCSI?", inline=True)
comment(0x8164, "Writing: get byte from memory", inline=True)
comment(0x8166, "Write to SCSI data register", inline=True)
comment(0x8169, "Always branch to increment", inline=True)
comment(0x816B, "Reading: get byte from SCSI", inline=True)
comment(0x816E, "Store in memory", inline=True)
comment(0x8170, "Next byte", inline=True)
comment(0x8171, "Continue until page done", inline=True)
comment(0x8173, "Increment page pointer", inline=True)
comment(0x8175, "Continue transfer", inline=True)
comment(0x8178, "Reading from SCSI via Tube?", inline=True)
comment(0x817A, "Writing via Tube: read from Tube R3", inline=True)
comment(0x817D, "Write to SCSI data register", inline=True)
comment(0x8180, "Always branch back", inline=True)
comment(0x8182, "Reading via Tube: read from SCSI", inline=True)
comment(0x8185, "Write to Tube R3", inline=True)
comment(0x8188, "Always branch back", inline=True)

# command_done (&818A)
comment(0x818A, "Release Tube if claimed", inline=True)
comment(0x818D, "Wait for SCSI REQ (status phase)", inline=True)
comment(0x8190, "Read status byte from SCSI data", inline=True)
comment(0x8193, "Wait for SCSI REQ (message phase)", inline=True)
comment(0x8196, "Save status in Y", inline=True)
comment(0x8197, "Read SCSI status register", inline=True)
comment(0x819A, "Check BSY still asserted", inline=True)
comment(0x819C, "Loop until bus free", inline=True)
comment(0x819E, "Retrieve status byte", inline=True)
comment(0x819F, "Read final data byte", inline=True)
comment(0x81A2, "Status OK?", inline=True)
comment(0x81A4, "No, return error &FF", inline=True)
comment(0x81A7, "Transfer status to X", inline=True)
comment(0x81A8, "Check error bit in status", inline=True)
comment(0x81AA, "No error, return success", inline=True)
comment(0x81AC, "Error: do SCSI Request Sense", inline=True)
comment(0x81AF, "A=0: success return code", inline=True)
comment(0x81B1, "Restore control block pointer", inline=True)
comment(0x81B5, "Mask to 7-bit error code", inline=True)

# hd_data_transfer_256 (&81B8)
comment(0x81B8, "Y=0: byte counter", inline=True)
comment(0x81BA, "Tube in use?", inline=True)
comment(0x81BC, "Yes, use Tube 256-byte transfer", inline=True)
comment(0x81BE, "Wait for SCSI REQ", inline=True)
comment(0x81C1, "Status phase, done", inline=True)
comment(0x81C3, "I/O bit: reading from SCSI?", inline=True)
comment(0x81C5, "Writing: get byte from memory", inline=True)
comment(0x81C7, "Write to SCSI data register", inline=True)
comment(0x81CA, "Next byte", inline=True)
comment(0x81CB, "Continue for 256 bytes", inline=True)
comment(0x81CD, "Next page", inline=True)
comment(0x81CF, "Continue transfer", inline=True)
comment(0x81D1, "Reading: get byte from SCSI", inline=True)
comment(0x81D4, "Store in memory", inline=True)
comment(0x81D6, "Next byte", inline=True)
comment(0x81D7, "Continue for 256 bytes", inline=True)
comment(0x81D9, "Next page", inline=True)
comment(0x81DB, "Continue transfer", inline=True)

# sub_c81dd - increment Tube transfer address
comment(0x81DD, "Increment low byte of transfer addr", inline=True)
comment(0x81E2, "Increment mid byte", inline=True)
comment(0x81E7, "Increment high byte", inline=True)
comment(0x81EA, "X=&27: Tube workspace addr low", inline=True)

# tube_start_xfer_sei / tube_start_xfer (&81EF-&81FB)
comment(0x81EF, "Disable interrupts for Tube xfer", inline=True)
comment(0x81F0, "Call Tube host code at &0406", inline=True)
comment(0x81F3, "Y=0", inline=True)
comment(0x81F5, "Delay for Tube synchronisation", inline=True)
comment(0x81F8, "Nested JSR/RTS delay", inline=True)

# Tube 256-byte write transfer (&81FC-&821E)
comment(0x81FC, "X=&27: Tube workspace addr low", inline=True)
comment(0x8200, "Wait for SCSI REQ", inline=True)
comment(0x8203, "Data phase?", inline=True)
comment(0x8205, "No, status phase - done", inline=True)
comment(0x8208, "I/O bit: reading from SCSI?", inline=True)
comment(0x820B, "Tube transfer type 6 (write)", inline=True)
comment(0x820D, "Start Tube transfer with SEI", inline=True)
comment(0x8213, "Read byte from Tube R3", inline=True)
comment(0x8216, "Write to SCSI data register", inline=True)
comment(0x8219, "Next byte", inline=True)
comment(0x821A, "Continue for 256 bytes", inline=True)
comment(0x821C, "Increment transfer address", inline=True)
comment(0x821F, "Restore flags, continue transfer", inline=True)
comment(0x8223, "Tube transfer type 7 (read)", inline=True)
comment(0x8225, "Start Tube transfer with SEI", inline=True)
comment(0x822B, "Read byte from SCSI data register", inline=True)
comment(0x822E, "Write to Tube R3", inline=True)
comment(0x8231, "Next byte", inline=True)
comment(0x8232, "Continue for 256 bytes", inline=True)
comment(0x8234, "Increment transfer address", inline=True)
comment(0x8237, "Restore flags, continue transfer", inline=True)

# scsi_request_sense (&823A)
comment(0x823A, "Select SCSI device", inline=True)
comment(0x823D, "SCSI Request Sense command = 3", inline=True)
comment(0x823F, "X=3: receive 4 sense bytes", inline=True)
comment(0x8240, "Y=3: send 3 more command bytes", inline=True)
comment(0x8241, "Send command byte", inline=True)
comment(0x8244, "Get LUN bits from drive number", inline=True)
comment(0x8247, "Isolate LUN (bits 5-7)", inline=True)
comment(0x8249, "Send LUN byte", inline=True)
comment(0x824C, "Send remaining zero bytes", inline=True)
comment(0x824F, "Decrement byte counter", inline=True)
comment(0x8250, "Loop for 3 bytes", inline=True)
comment(0x8252, "Receive sense data bytes", inline=True)
comment(0x8255, "Read sense data from SCSI bus", inline=True)
comment(0x8258, "Store in error workspace", inline=True)
comment(0x825B, "Next byte", inline=True)
comment(0x825C, "Loop for 4 bytes", inline=True)
comment(0x825E, "Get drive LUN bits", inline=True)
comment(0x8261, "Isolate LUN", inline=True)
comment(0x8263, "Merge with error sector high byte", inline=True)
comment(0x8266, "Store back", inline=True)
comment(0x8269, "Wait for status phase", inline=True)
comment(0x826C, "Get error code from workspace", inline=True)
comment(0x826F, "Read status byte", inline=True)
comment(0x8272, "Wait for message phase", inline=True)
comment(0x8275, "Read message byte", inline=True)
comment(0x8278, "Message byte non-zero? Error", inline=True)
comment(0x827A, "Check status error bit", inline=True)
comment(0x827C, "Error bit set? Return error", inline=True)
comment(0x827E, "Transfer error code to A", inline=True)
comment(0x827F, "Return with error code", inline=True)
comment(0x8282, "Unrecoverable SCSI error", inline=True)
comment(0x8284, "Return &FF", inline=True)

# c8287/c828b - execute command with workspace block
comment(0x8287, "Point to workspace disc op block", inline=True)
comment(0x828B, "Execute disc command", inline=True)
comment(0x828E, "Error? Generate BRK", inline=True)
comment(0x8291, "Restore saved drive number", inline=True)
comment(0x8294, "Set current drive", inline=True)

# c84b5 - Release disc space back to free space map
# Searches the FSM for the free space entry adjacent to the
# object at wksp_object_sector (size at &1037-&1039) and
# merges the released space with adjacent free entries.
label(0x802D, "copy_tube_addr_loop")
label(0x803B, "claim_tube_retry")
label(0x8057, "scsi_read_settle_loop")
label(0x806A, "wait_bus_free_loop")
label(0x8078, "wait_target_bsy_loop")
label(0x8086, "escape_during_retry")
label(0x80AF, "check_escape_during_retry")
label(0x80BE, "dispatch_hd_or_floppy")
label(0x8111, "skip_tube_claim")
label(0x8114, "send_scsi_command_bytes")
label(0x8127, "send_cmd_byte_loop")
label(0x8129, "send_next_cmd_byte")
label(0x8136, "check_256_byte_transfer")
label(0x8147, "start_byte_transfer")
label(0x8159, "wait_data_phase")
label(0x816B, "read_scsi_to_memory")
label(0x8170, "advance_memory_page")
label(0x8178, "read_scsi_via_tube")
label(0x8182, "write_tube_to_scsi")
label(0x818D, "wait_status_phase")
label(0x81A7, "check_scsi_error_bit")
label(0x81AF, "return_scsi_result")
label(0x81B1, "mask_error_code")
label(0x81BE, "wait_req_and_transfer")
label(0x81C5, "write_sector_byte_loop")
label(0x81D1, "read_sector_byte_loop")
label(0x81DD, "increment_tube_xfer_addr")
label(0x81EA, "load_tube_workspace_ptr")
label(0x81FC, "setup_tube_write_256")
label(0x8200, "wait_tube_data_phase")
label(0x8208, "set_tube_write_direction")
label(0x8210, "tube_write_byte_loop")
label(0x8222, "set_tube_read_direction")
label(0x8228, "tube_read_byte_loop")
label(0x824C, "send_zero_bytes_loop")
label(0x8252, "receive_sense_data_loop")
label(0x8282, "unrecoverable_scsi_error")
label(0x8287, "exec_disc_op_from_wksp")
label(0x828B, "exec_disc_command")
label(0x8291, "restore_drive_after_op")
label(0x82B9, "check_escape_condition")
label(0x82D1, "translate_scsi_error")
label(0x82E8, "store_error_sector")
label(0x8310, "poll_req_loop")
label(0x8326, "write_scsi_data_byte")
label(0x832B, "generate_disc_error")
label(0x8339, "copy_error_string_loop")
label(0x8342, "check_for_on_channel")
label(0x8361, "copy_error_msg_loop")
label(0x8376, "append_hex_suffix")
label(0x837C, "check_colon_suffix")
label(0x8383, "append_drive_sector_suffix")
label(0x8385, "copy_at_string_loop")
label(0x83AC, "append_sector_bytes_loop")
label(0x83AF, "append_sector_hex")
label(0x83C3, "append_channel_suffix_loop")
label(0x83ED, "close_exec_or_spool")
label(0x83F0, "restore_error_position")
label(0x83F2, "raise_brk_error")
label(0x83FA, "copy_brk_block_loop")
label(0x8419, "run_exec_or_spool")
label(0x8436, "store_hex_nibble")
label(0x8459, "print_decimal_digit")
label(0x845F, "divide_loop")
label(0x8470, "store_digit")
label(0x8474, "skip_leading_zero")
label(0x847A, "invalidate_sectors_loop")
label(0x848C, "zero_buffers_loop")
label(0x84B5, "release_disc_space")
subroutine(0x84B5, "release_disc_space",
    title="Release disc space back to free space map",
    description="""\
Return the disc space occupied by the object at
wksp_object_sector (3 bytes) with size at &1037-&1039
(3 bytes) back to the free space map. Searches for the
correct position in the sorted FSM and merges with
adjacent free entries where possible.
""",
    on_entry={"note": "wksp_object_sector and wksp_object_size set in workspace"},
    on_exit={"a": "corrupted", "x": "corrupted", "y": "corrupted"})

comment(0x84B5, "Check if object has non-zero size", inline=True)
comment(0x84BE, "Size is zero, nothing to release", inline=True)
comment(0x84C1, "X=0: start of FSM entries", inline=True)
comment(0x84C3, "Past end of free space list?", inline=True)
comment(0x84C6, "Yes, insert at end", inline=True)
comment(0x84C8, "Advance X by 3 (entry size)", inline=True)
comment(0x84CB, "Save X for backtrack", inline=True)
comment(0x84CD, "Y=2: compare 3-byte address", inline=True)
comment(0x84CF, "Back up X to compare bytes", inline=True)
comment(0x84D0, "Get FSM entry address byte", inline=True)
comment(0x84D3, "Compare with object sector byte", inline=True)
comment(0x84D6, "FSM entry >= object? Found position", inline=True)
comment(0x84D8, "Restore X, try next entry", inline=True)
comment(0x84DC, "Exact match on this byte?", inline=True)
comment(0x84DE, "Compare next byte down", inline=True)
comment(0x84E1, "Back to entry start", inline=True)
comment(0x84E8, "C=0 for addition", inline=True)
comment(0x84EA, "Y=0: compare 3 address bytes", inline=True)
comment(0x84EC, "Restore carry", inline=True)
comment(0x84ED, "Object sector + object size", inline=True)
comment(0x84F3, "Save carry", inline=True)
comment(0x84F4, "Compare with FSM entry address", inline=True)
comment(0x84F7, "Match? Object is adjacent to entry", inline=True)
comment(0x84FA, "No match, insert new entry", inline=True)
comment(0x84FD, "Next compare byte", inline=True)
comment(0x84FE, "Next object sector byte", inline=True)
comment(0x84FF, "Compared all 3 bytes?", inline=True)
comment(0x8501, "No, continue comparing", inline=True)
comment(0x8503, "Restore carry from addition", inline=True)
comment(0x8504, "Get FSM entry index back", inline=True)
comment(0x8506, "Entry 0: no preceding entry to merge", inline=True)
comment(0x8508, "Clear carry for addition", inline=True)
comment(0x850A, "Y=0: compare bytes of prev+size", inline=True)
comment(0x850C, "Restore carry", inline=True)
comment(0x850D, "Get prev entry address byte", inline=True)
comment(0x8510, "Add prev entry length byte", inline=True)
comment(0x8513, "Save carry", inline=True)
comment(0x8514, "Compare prev+size with object sector", inline=True)
comment(0x8517, "Match: prev is adjacent (merge back)", inline=True)
comment(0x8519, "No match: insert new entry", inline=True)
comment(0x851F, "Next byte", inline=True)
comment(0x8520, "Next object sector byte", inline=True)
comment(0x8521, "Compared all 3 bytes?", inline=True)
comment(0x8523, "No, continue", inline=True)
comment(0x8525, "Adjacent to prev: merge backward", inline=True)
comment(0x8526, "Restore FSM index", inline=True)
comment(0x8528, "Y=0: add released size to prev length", inline=True)
comment(0x852C, "Restore carry", inline=True)
comment(0x852D, "Get prev entry length byte", inline=True)
comment(0x8530, "Add released size byte", inline=True)
comment(0x8533, "Store updated length", inline=True)
comment(0x8536, "Save carry for next byte", inline=True)
comment(0x8537, "Next entry byte", inline=True)
comment(0x8538, "Next size byte", inline=True)
comment(0x8539, "All 3 bytes?", inline=True)
comment(0x853B, "No, continue adding", inline=True)
comment(0x853D, "Restore carry", inline=True)
comment(0x853E, "Y=2: check if merged entry is now", inline=True)
comment(0x8540, "adjacent to the NEXT entry too", inline=True)
comment(0x8542, "Clear carry for addition", inline=True)
comment(0x8543, "Get merged entry address byte", inline=True)
comment(0x8546, "Add merged entry length byte", inline=True)
comment(0x8549, "Store sum (prev+released+next?)", inline=True)
comment(0x854C, "Next byte", inline=True)
comment(0x854D, "Decrement counter", inline=True)
comment(0x854E, "Loop for 3 bytes", inline=True)
comment(0x8550, "Check if past end of FSM list", inline=True)
comment(0x8553, "Yes: shrink list by removing entry", inline=True)
comment(0x8555, "Get next entry length", inline=True)
comment(0x8558, "Store over current (shift down)", inline=True)
comment(0x855B, "Get next entry address", inline=True)
comment(0x855E, "Store over current (shift down)", inline=True)
comment(0x8561, "Next entry", inline=True)
comment(0x8562, "Loop shifting entries", inline=True)
comment(0x8564, "Adjust end-of-list pointer", inline=True)
comment(0x8565, "Back 3 bytes", inline=True)
comment(0x8566, "Back 3 bytes total", inline=True)
comment(0x8567, "Store new end-of-list pointer", inline=True)
comment(0x856A, "Return", inline=True)

# c856b - add size to existing entry (no merge with next)
comment(0x856B, "Y=0: copy+add 3-byte address+length", inline=True)
comment(0x856D, "Clear carry for addition", inline=True)
comment(0x856F, "Get object sector byte", inline=True)
comment(0x8572, "Store as FSM entry address", inline=True)
comment(0x8575, "Restore carry from prev iteration", inline=True)
comment(0x8576, "Get current FSM length byte", inline=True)
comment(0x8579, "Add released size byte", inline=True)
comment(0x857C, "Store updated length", inline=True)
comment(0x857F, "Save carry", inline=True)
comment(0x8580, "Next byte", inline=True)
comment(0x8581, "Next FSM byte", inline=True)
comment(0x8582, "All 3 bytes?", inline=True)
comment(0x8584, "No, continue", inline=True)
comment(0x8586, "Restore final carry", inline=True)
comment(0x8587, "Return (merge complete)", inline=True)

# c8588 - check merge with preceding entry
comment(0x8588, "Get FSM entry index", inline=True)
comment(0x858A, "Entry 0: no predecessor, insert new", inline=True)
comment(0x858C, "Clear carry for addition", inline=True)
comment(0x858E, "Y=0: compare prev+size with object", inline=True)
comment(0x8590, "Restore carry", inline=True)
comment(0x8591, "Get prev entry address byte", inline=True)
comment(0x8594, "Add prev entry length byte", inline=True)
comment(0x8597, "Save carry", inline=True)
comment(0x8598, "Compare with object sector byte", inline=True)
comment(0x859B, "Match: prev is adjacent", inline=True)
comment(0x859D, "Restore carry, no match", inline=True)
comment(0x859E, "Not adjacent: insert new entry", inline=True)
comment(0x85A1, "Next byte", inline=True)
comment(0x85A2, "Next object byte", inline=True)
comment(0x85A3, "All 3 bytes?", inline=True)
comment(0x85A5, "No, continue", inline=True)
comment(0x85A7, "Restore carry (all matched)", inline=True)
comment(0x85A8, "Y=0: add released size to prev", inline=True)
comment(0x85AA, "Get FSM entry index", inline=True)
comment(0x85AC, "Clear carry for addition", inline=True)
comment(0x85AE, "Restore carry", inline=True)
comment(0x85AF, "Get prev entry length byte", inline=True)
comment(0x85B2, "Add released size byte", inline=True)
comment(0x85B5, "Store updated length", inline=True)
comment(0x85B8, "Save carry", inline=True)
comment(0x85B9, "Next FSM byte", inline=True)
comment(0x85BA, "Next size byte", inline=True)
comment(0x85BB, "All 3 bytes?", inline=True)
comment(0x85BD, "No, continue", inline=True)
comment(0x85BF, "Restore carry", inline=True)
comment(0x85C0, "Return (merge with prev complete)", inline=True)

# c85c1 - insert new FSM entry (no merge possible)
comment(0x85C1, "Get end-of-list pointer", inline=True)
comment(0x85C4, "Room for new entry (< &F6)?", inline=True)
comment(0x85C6, "Yes: proceed with insert", inline=True)
comment(0x85D5, "Get end-of-list pointer", inline=True)
comment(0x85D8, "Reached insertion point?", inline=True)
comment(0x85DA, "Yes: insert here", inline=True)
comment(0x85DC, "Shift entries up by 3 bytes", inline=True)
comment(0x85DD, "Get FSM address byte to shift", inline=True)
comment(0x85E0, "Store 3 bytes higher", inline=True)
comment(0x85E3, "Get FSM length byte to shift", inline=True)
comment(0x85E6, "Store 3 bytes higher", inline=True)
comment(0x85E9, "Continue shifting", inline=True)
comment(0x85EC, "Y=0: store new entry at gap", inline=True)
comment(0x85EE, "Get object sector byte", inline=True)
comment(0x85F1, "Store as FSM entry address", inline=True)
comment(0x85F4, "Get released size byte", inline=True)
comment(0x85F7, "Store as FSM entry length", inline=True)
comment(0x85FA, "Next byte", inline=True)
comment(0x85FB, "Next source byte", inline=True)
comment(0x85FC, "All 3 bytes?", inline=True)
comment(0x85FE, "No, continue", inline=True)
comment(0x8600, "Get end-of-list pointer", inline=True)
comment(0x8603, "Add 3 (new entry size)", inline=True)
comment(0x8605, "Store updated pointer", inline=True)
comment(0x8608, "Return", inline=True)

# Remaining items scattered through release_disc_space extent
comment(0x84B8, "OR with size mid byte", inline=True)
comment(0x84BB, "OR with size high byte", inline=True)
comment(0x84C0, "Size is zero: return", inline=True)
comment(0x84C9, "Advance X (2nd byte of entry)", inline=True)
comment(0x84CA, "Advance X (3rd byte of entry)", inline=True)
comment(0x84DA, "Try next FSM entry", inline=True)
comment(0x84DF, "Continue comparing bytes", inline=True)
comment(0x84E3, "Back up to entry start", inline=True)
comment(0x84E4, "2nd byte back", inline=True)
comment(0x84E5, "3rd byte back", inline=True)
comment(0x84E6, "Save entry index for merge check", inline=True)
comment(0x84E9, "Save carry for multi-byte add", inline=True)
comment(0x84F0, "Add object size byte", inline=True)
comment(0x84F9, "Restore carry after mismatch", inline=True)
comment(0x8509, "Save carry for multi-byte add", inline=True)
comment(0x851B, "Restore carry", inline=True)
comment(0x851C, "Not adjacent: insert new entry", inline=True)
comment(0x852A, "Clear carry for addition", inline=True)
comment(0x852B, "Save carry", inline=True)
comment(0x856E, "Save carry for multi-byte operation", inline=True)
comment(0x858D, "Save carry for multi-byte add", inline=True)
comment(0x85AD, "Save carry for multi-byte add", inline=True)
comment(0x85C8, "Save drive state and raise error", inline=True)

# sub_c8609 - sum all free space entries
comment(0x8609, "X=0: start scanning FSM", inline=True)
comment(0x860B, "Clear accumulator low byte", inline=True)
comment(0x860E, "Clear accumulator mid byte", inline=True)
comment(0x8611, "Clear accumulator high byte", inline=True)
comment(0x8614, "Past end of FSM entries?", inline=True)
comment(0x8617, "Yes: return total", inline=True)
comment(0x8619, "Y=0: sum this 3-byte entry", inline=True)
comment(0x861B, "Clear carry for addition", inline=True)
comment(0x861C, "Save carry for multi-byte add", inline=True)
comment(0x861D, "Restore carry", inline=True)
comment(0x861E, "Get FSM length byte", inline=True)
comment(0x8621, "Add to accumulator", inline=True)
comment(0x8624, "Store updated accumulator", inline=True)
comment(0x8627, "Save carry for next byte", inline=True)
comment(0x8628, "Next accumulator byte", inline=True)
comment(0x8629, "Next FSM byte", inline=True)
comment(0x862A, "All 3 bytes?", inline=True)
comment(0x862C, "No, continue", inline=True)
comment(0x862E, "Restore carry", inline=True)
comment(0x862F, "Loop for next FSM entry", inline=True)

# sub_c8632 - allocate disc space from FSM
comment(0x8632, "X=&FF: no best-fit entry yet", inline=True)
comment(0x8634, "Store as best-fit index", inline=True)
comment(0x8637, "Past end of FSM entries?", inline=True)
comment(0x863A, "No: check this entry", inline=True)
comment(0x863C, "Get best-fit index", inline=True)
comment(0x863E, "Still &FF (no fit found)?", inline=True)
comment(0x8640, "Found a fit: use it", inline=True)
comment(0x8642, "No fit: sum all free space", inline=True)
comment(0x8645, "Y=0: compare total vs requested", inline=True)
comment(0x8647, "X=2: compare 3 bytes", inline=True)
comment(0x8649, "Set carry for subtraction", inline=True)
comment(0x864A, "Get total free space byte", inline=True)
comment(0x864D, "Subtract requested size byte", inline=True)
comment(0x8650, "Next byte", inline=True)
comment(0x8651, "Next requested byte", inline=True)
comment(0x8652, "All 3 bytes?", inline=True)
comment(0x8654, "Total >= requested: space exists", inline=True)
comment(0x8656, "Not enough: Disc full error", inline=True)
comment(0x8664, "Compaction needed: error", inline=True)
comment(0x867C, "Y=2: copy best-fit entry sector addr", inline=True)
comment(0x867E, "Back up to entry start", inline=True)
comment(0x867F, "Get FSM address byte", inline=True)
comment(0x8682, "Store as allocated sector", inline=True)
comment(0x8685, "Next byte", inline=True)
comment(0x8686, "Loop for 3 bytes", inline=True)
comment(0x8688, "Y=1 (adjusted for carry)", inline=True)
comment(0x8689, "Restore best-fit index", inline=True)
comment(0x868B, "Clear carry for addition", inline=True)
comment(0x868C, "Save carry", inline=True)
comment(0x868D, "Restore carry", inline=True)
comment(0x868E, "Get entry address byte", inline=True)
comment(0x8691, "Add requested size to advance addr", inline=True)
comment(0x8694, "Store updated entry address", inline=True)
comment(0x8697, "Save carry", inline=True)
comment(0x8698, "Next entry byte", inline=True)
comment(0x8699, "Next requested byte", inline=True)
comment(0x869A, "All 3 bytes?", inline=True)
comment(0x869C, "No, continue", inline=True)
comment(0x869E, "Restore carry", inline=True)
comment(0x869F, "Y=0: subtract requested from length", inline=True)
comment(0x86A1, "Get best-fit index", inline=True)
comment(0x86A3, "Set carry for subtraction", inline=True)
comment(0x86A4, "Save carry", inline=True)
comment(0x86A5, "Restore carry", inline=True)
comment(0x86A6, "Get entry length byte", inline=True)
comment(0x86A9, "Subtract requested size", inline=True)
comment(0x86AC, "Store reduced length", inline=True)
comment(0x86AF, "Save carry", inline=True)
comment(0x86B0, "Next entry byte", inline=True)
comment(0x86B1, "Next requested byte", inline=True)
comment(0x86B2, "All 3 bytes?", inline=True)
comment(0x86B4, "No, continue", inline=True)
comment(0x86B6, "Restore carry", inline=True)
comment(0x86B7, "Return (allocation complete)", inline=True)

# Scanning loop for best-fit entry
comment(0x86B8, "Y=2: compare entry length backwards", inline=True)
comment(0x86BA, "Advance X to entry+3", inline=True)
comment(0x86BB, "2nd byte", inline=True)
comment(0x86BC, "3rd byte", inline=True)
comment(0x86BD, "Save entry end index", inline=True)
comment(0x86BF, "Back up one byte", inline=True)
comment(0x86C0, "Get entry length byte", inline=True)
comment(0x86C3, "Compare with requested size", inline=True)
comment(0x86C6, "Entry < requested: too small", inline=True)
comment(0x86C8, "Not equal: entry is larger", inline=True)
comment(0x86CA, "Next byte (decreasing Y)", inline=True)
comment(0x86CB, "Loop for 3 bytes", inline=True)
comment(0x86CD, "Exact match: use this entry", inline=True)
comment(0x86CF, "Y=2: copy entry address", inline=True)
comment(0x86D1, "Back up", inline=True)
comment(0x86D2, "Get entry address byte", inline=True)
comment(0x86D5, "Store as allocated sector", inline=True)
comment(0x86D8, "Next byte", inline=True)
comment(0x86D9, "Loop for 3 bytes", inline=True)
comment(0x86DB, "Restore entry index", inline=True)
comment(0x86DD, "Past end of entries?", inline=True)
comment(0x86E0, "Yes: shrink list", inline=True)
comment(0x86E2, "Shift entries down", inline=True)
comment(0x86E5, "Store 3 bytes lower (addresses)", inline=True)
comment(0x86E8, "Get length entry to shift", inline=True)
comment(0x86EB, "Store 3 bytes lower (lengths)", inline=True)
comment(0x86EE, "Next entry", inline=True)
comment(0x86EF, "Loop shifting entries", inline=True)
comment(0x86F1, "Get end-of-list pointer", inline=True)
comment(0x86F4, "Subtract 3 (removed entry)", inline=True)
comment(0x86F6, "Store updated pointer", inline=True)
comment(0x86F9, "Return (exact match used)", inline=True)
comment(0x86FA, "Get current best-fit", inline=True)
comment(0x86FC, "X+1: was &FF (no fit yet)?", inline=True)
comment(0x86FD, "Non-zero: this entry is new best", inline=True)
comment(0x86FF, "No previous fit: store this one", inline=True)
comment(0x8701, "Store as best-fit index", inline=True)
comment(0x8703, "Restore entry index", inline=True)
comment(0x8705, "Continue scanning", inline=True)

# sub_c8708 - advance text pointer
# Wildcard matching code (&8787-&87E6)
comment(0x878A, "Trailing '#' in pattern?", inline=True)
comment(0x878C, "Yes: match (name shorter than pattern)", inline=True)
comment(0x878E, "Trailing '*' in pattern?", inline=True)
comment(0x8790, "Yes: match (wildcard eats rest)", inline=True)
comment(0x8792, "Back up Y to try shorter match", inline=True)
comment(0x8793, "More positions to try", inline=True)
comment(0x8795, "Compare &FF (force NE for no match)", inline=True)
comment(0x8797, "Return Z clear (no match)", inline=True)
comment(0x8798, "Pattern exhausted: check name too", inline=True)
comment(0x879A, "Both at 10: exact match", inline=True)
comment(0x879C, "Check if pattern char is terminator", inline=True)
comment(0x879F, "Terminator: name matches", inline=True)
comment(0x87A1, "Trailing '*': match", inline=True)
comment(0x87A5, "Compare 0 with 0 to set Z flag", inline=True)
comment(0x87A7, "Return with Z flag result", inline=True)

# '*' wildcard matching (recursive) (&87A8-&87E5)
comment(0x87A8, "Skip past '*' in pattern", inline=True)
comment(0x87A9, "Get object name char at X", inline=True)
comment(0x87AC, "Strip bit 7", inline=True)
comment(0x87AE, "< '!': end of name (CR padding)", inline=True)
comment(0x87B0, "End of name: check pattern trail", inline=True)
comment(0x87B2, "X >= 10: end of name", inline=True)
comment(0x87B4, "End of name: check pattern trail", inline=True)
comment(0x87B6, "Save X (name position)", inline=True)
comment(0x87B7, "Push on stack", inline=True)
comment(0x87B8, "Save Y (pattern position)", inline=True)
comment(0x87B9, "Push on stack", inline=True)
comment(0x87BA, "Try matching from here (recursive)", inline=True)
comment(0x87BD, "Z set: match succeeded", inline=True)
comment(0x87BF, "No match: restore Y", inline=True)
comment(0x87C0, "Transfer to Y", inline=True)
comment(0x87C1, "Restore X", inline=True)
comment(0x87C2, "Transfer to X", inline=True)
comment(0x87C3, "Advance name position, try again", inline=True)
comment(0x87C4, "Loop trying next position", inline=True)
comment(0x87C6, "Compare X with 0 to set Z flag", inline=True)
comment(0x87C8, "Return with Z flag", inline=True)
comment(0x87C9, "Match: discard saved positions", inline=True)
comment(0x87CB, "A=0: set Z flag (match)", inline=True)
comment(0x87CD, "Set carry", inline=True)
comment(0x87CE, "Return Z set (match)", inline=True)
comment(0x87CF, "Name ended: check pattern trail", inline=True)
comment(0x87D1, "Y >= 10: both exhausted, match", inline=True)
comment(0x87D3, "Get pattern char", inline=True)
comment(0x87D5, "Control char: pattern ended too", inline=True)
comment(0x87D7, "Pattern ended: match", inline=True)
comment(0x87D9, "Is it '.'?", inline=True)
comment(0x87DB, "Dot: match (path separator)", inline=True)
comment(0x87DD, "Is it '\"'?", inline=True)
comment(0x87DF, "Quote: match (string end)", inline=True)
comment(0x87E1, "Is it '*'?", inline=True)
comment(0x87E3, "Another '*': skip it and retry", inline=True)
comment(0x87E5, "Other char: no match (always)", inline=True)

# sub_c87e7 - pathname parser entry point
comment(0x87E7, "Skip leading spaces", inline=True)
comment(0x87EA, "Set (&B6) to first dir entry", inline=True)
comment(0x87ED, "Verify directory integrity", inline=True)
comment(0x87F0, "Y=0: start parsing pathname", inline=True)

comment(0x87F0, """\
Linear scan through sorted directory entries. Entries are
in ascending alphabetical order. Each 26-byte entry is
checked in turn. The scan terminates on: match (Z=1),
sorted early exit when pattern < entry name (C=0), or
end of directory (first byte = 0). On exit, (&B6)
points to the matched or insertion-point entry.""")
comment(0x87F2, "Get first byte of entry", inline=True)
comment(0x87F4, "Zero: end of entries", inline=True)
comment(0x87F6, "Check name length and compare", inline=True)
comment(0x87F9, "Z=1: match found", inline=True)
comment(0x87FB, "C=0: pattern < name, stop (sorted)", inline=True)
comment(0x87FD, "C=1: pattern > name, next entry", inline=True)
comment(0x87FF, "Add &19+C(=1) = &1A (26 byte entry)", inline=True)
comment(0x8801, "Store updated pointer", inline=True)
comment(0x8803, "No page crossing: continue", inline=True)
comment(0x8805, "Increment page", inline=True)
comment(0x8807, "Continue searching", inline=True)
comment(0x8809, "A=0 at end: compare with &0F", inline=True)
comment(0x880B, "Return (Z clear = not found)", inline=True)

# sub_c8822 - parse drive number from ASCII
comment(0x8822, "Character >= '0'?", inline=True)
comment(0x8824, "Below '0': bad name", inline=True)
comment(0x8826, "Character >= '8' (not digit)?", inline=True)
comment(0x8828, "Digit 0-7: valid drive", inline=True)
comment(0x882A, "Convert to lowercase", inline=True)
comment(0x882C, "Character >= 'a'?", inline=True)
comment(0x882E, "Below 'a': bad name", inline=True)
comment(0x8830, "Character >= 'i'?", inline=True)
comment(0x8832, "Above 'h': bad name", inline=True)
comment(0x8834, "Subtract to get drive number", inline=True)
comment(0x8836, "Save drive digit on stack", inline=True)
comment(0x8837, "Check for hard drive", inline=True)
comment(0x8839, "Bit 5: hard drive present?", inline=True)
comment(0x883B, "HD present: allow drives 0-7", inline=True)
comment(0x883D, "No HD: restore drive digit", inline=True)
comment(0x883E, "Mask to drives 0-3 only (floppy)", inline=True)
comment(0x8840, "Re-push limited drive number", inline=True)
comment(0x8841, "Restore drive number", inline=True)
comment(0x8842, "Mask to 3 bits (drives 0-7)", inline=True)
comment(0x8844, "Shift into drive ID position", inline=True)
comment(0x8845, "Rotate right", inline=True)
comment(0x8846, "Rotate right", inline=True)
comment(0x8847, "Rotate right (bits 5-7)", inline=True)
comment(0x8848, "Return drive ID in A", inline=True)
comment(0x8849, "Invalid: Bad name error", inline=True)

# sub_c884c - parse filename from command line
# sub_c8851 - full pathname parser
# Handles :D.$.DIR.FILE syntax, drive specifiers,
# root ($), parent (^), current (@), and dot separators.
comment(0x8851, "Get first path character", inline=True)
comment(0x8854, "Empty: use current directory", inline=True)
comment(0x8856, "Is it ':' (drive specifier)?", inline=True)
comment(0x8858, "No colon: check for $ or path", inline=True)
comment(0x885A, "Advance past ':'", inline=True)
comment(0x885D, "Check if drive already saved", inline=True)
comment(0x8860, "Saved drive = &FF (not set)?", inline=True)
comment(0x8861, "Already set: keep it", inline=True)
comment(0x8863, "Save current drive for restore", inline=True)
comment(0x8866, "Store as saved drive", inline=True)
comment(0x8869, "Get drive character", inline=True)
comment(0x886C, "Parse drive number from ASCII", inline=True)
comment(0x886F, "Store as new current drive", inline=True)
comment(0x8872, "Advance past drive number", inline=True)
comment(0x8875, "Check drive is initialised", inline=True)
comment(0x8878, "Drive = &FF (uninitialised)?", inline=True)
comment(0x8879, "Not &FF: drive is valid", inline=True)
comment(0x887B, "Set to drive 0 as default", inline=True)
comment(0x887E, "Set FSM-inconsistent flag (bit 4)", inline=True)
comment(0x8880, "Bit 4: FSM being loaded", inline=True)
comment(0x8882, "Store updated flags", inline=True)
comment(0x8884, "Load FSM from disc (sectors 0-1)", inline=True)
comment(0x888B, "Clear FSM-inconsistent flag", inline=True)
comment(0x888D, "Mask off bit 4", inline=True)
comment(0x888F, "Store cleared flags", inline=True)
comment(0x8891, "Check if alt workspace is set", inline=True)
comment(0x8894, "Set: skip CSD copy", inline=True)
comment(0x8896, "Y=2: copy CSD sector to workspace", inline=True)
comment(0x8898, "Get CSD sector byte", inline=True)
comment(0x889B, "Copy to CSD drive sector", inline=True)
comment(0x889E, "Next byte", inline=True)
comment(0x889F, "Loop for 3 bytes", inline=True)
comment(0x88A1, "Load root directory (sector 2)", inline=True)
comment(0x88A8, "Set root sector = 2", inline=True)
comment(0x88AA, "Store root sector low", inline=True)
comment(0x88AD, "A=0: clear mid and high bytes", inline=True)
comment(0x88AF, "Clear sector mid byte", inline=True)
comment(0x88B2, "Clear sector high byte", inline=True)
comment(0x88B5, "Validate FSM checksums", inline=True)
comment(0x88B8, "Y=0: check next path character", inline=True)
comment(0x88BA, "Get next character", inline=True)
comment(0x88BD, "Is it '.' (path separator)?", inline=True)
comment(0x88BF, "No dot: this is the final component", inline=True)
comment(0x88C1, "Skip past dot separator", inline=True)
comment(0x88C4, "Y=0: check for $ or path component", inline=True)
comment(0x88C6, "Get character", inline=True)
comment(0x88C9, "Mask to check for $ (ignore bit 1)", inline=True)
comment(0x88CB, "Is it '$' (root directory)?", inline=True)
comment(0x88CD, "Yes: advance and load root", inline=True)
comment(0x88CF, "Not root: load current directory", inline=True)
comment(0x88D2, "Check for ^ or @ specifiers", inline=True)
comment(0x88D5, "Not special: regular path component", inline=True)
comment(0x88D7, "Advance past ^ or @ character", inline=True)
comment(0x88D8, "Store length marker", inline=True)
comment(0x88DB, "Get next character", inline=True)
comment(0x88DE, "Is it '.' (more path follows)?", inline=True)
comment(0x88E0, "No: this is the final component", inline=True)

# Pathname continuation (&88E2-&8938)
comment(0x88E2, "Jump to subdirectory descent", inline=True)
comment(0x88E5, "No dot after root: set up $ entry", inline=True)
comment(0x88E7, "Store '$' as object name", inline=True)
comment(0x88EA, "CR padding", inline=True)
comment(0x88EC, "Store CR after name", inline=True)
comment(0x88EF, "Point to dummy dir entry at &94CC", inline=True)
comment(0x88F1, "Store pointer low", inline=True)
comment(0x88F3, "Pointer high = &94", inline=True)
comment(0x88F5, "Store pointer high", inline=True)
comment(0x88F7, "A=2: root sector number", inline=True)
comment(0x88F9, "Store as found sector", inline=True)
comment(0x88FC, "A=0: success (Z set)", inline=True)
comment(0x88FE, "Return", inline=True)
comment(0x88FF, "Regular path: search current dir", inline=True)
comment(0x8902, "Found? Proceed to check dir/file", inline=True)
comment(0x8904, "Return (not found)", inline=True)

# c8905 - set up after finding path component
comment(0x8905, "Save current text pointer", inline=True)
comment(0x8907, "Push low byte", inline=True)
comment(0x8908, "Get high byte", inline=True)
comment(0x890A, "Push high byte", inline=True)
comment(0x890B, "Transfer Y to A (matched length)", inline=True)
comment(0x890C, "Clear carry for addition", inline=True)
comment(0x890D, "Add matched length to text pointer", inline=True)
comment(0x890F, "Store updated text pointer low", inline=True)
comment(0x8911, "A=0 for carry propagation", inline=True)
comment(0x8913, "Add carry to high byte", inline=True)
comment(0x8915, "Store updated text pointer high", inline=True)
comment(0x8917, "Skip spaces after path component", inline=True)
comment(0x891A, "Save remaining text pointer", inline=True)
comment(0x891C, "Store for later use", inline=True)
comment(0x891F, "Get high byte", inline=True)
comment(0x8921, "Store high byte", inline=True)
comment(0x8924, "Restore original text pointer", inline=True)
comment(0x8925, "Store high byte", inline=True)
comment(0x8927, "Restore low byte", inline=True)
comment(0x8928, "Store low byte", inline=True)
comment(0x892A, "X=1: object type (file)", inline=True)
comment(0x892C, "Y=3: check access byte", inline=True)
comment(0x892E, "Get access/attribute byte", inline=True)
comment(0x8930, "Bit 7 clear: not a directory", inline=True)
comment(0x8932, "Bit 7 set: X=2 (directory)", inline=True)
comment(0x8933, "Store object type", inline=True)
comment(0x8936, "A=0: success (Z set)", inline=True)
comment(0x8938, "Return", inline=True)

# Directory search after finding path component (&8939-&8990)
comment(0x8939, "Y=0: scan for end of component", inline=True)
comment(0x893B, "Check next character", inline=True)
comment(0x893E, "Control char? End of component", inline=True)
comment(0x8940, "Yes: set up result", inline=True)
comment(0x8942, "Double-quote? End of component", inline=True)
comment(0x8944, "Yes: set up result", inline=True)
comment(0x8946, "Dot? Path separator", inline=True)
comment(0x8948, "Yes: descend into subdirectory", inline=True)
comment(0x894A, "Next character", inline=True)
comment(0x894B, "Loop scanning", inline=True)
comment(0x894D, "Save component length", inline=True)
comment(0x8950, "Y=3: check if entry is directory", inline=True)
comment(0x8952, "Get access byte", inline=True)
comment(0x8954, "Bit 7: is a directory", inline=True)
comment(0x8956, "Not dir: advance to next entry", inline=True)
comment(0x8959, "Found next entry: retry match", inline=True)
comment(0x895B, "A=&FF: return not found", inline=True)
comment(0x895D, "Return", inline=True)

# c895e - advance to next directory entry
comment(0x895E, "Clear carry for addition", inline=True)
comment(0x895F, "Get entry pointer low", inline=True)
comment(0x8961, "Add &1A (26 bytes per entry)", inline=True)
comment(0x8963, "Store updated pointer", inline=True)
comment(0x8965, "No page crossing", inline=True)
comment(0x8967, "Increment page on overflow", inline=True)
comment(0x8969, "Y=0: check first byte", inline=True)
comment(0x896B, "Get first byte of next entry", inline=True)
comment(0x896D, "Zero: end of entries (not found)", inline=True)
comment(0x896F, "Compare against pattern", inline=True)
comment(0x8972, "No match: try next entry", inline=True)
comment(0x8974, "Match found: return", inline=True)

# c8975 - entry is directory, descend into it
comment(0x8975, "Y=9: check last name byte", inline=True)
comment(0x8977, "Get name byte 9", inline=True)
comment(0x8979, "Bit 7 clear: normal descent", inline=True)
comment(0x897B, "Bit 7 set: clear it (bad rename?)", inline=True)
comment(0x897D, "Store cleaned name byte", inline=True)
comment(0x897F, "Write directory back to disc", inline=True)

# c8991 - advance text pointer past matched component
comment(0x8991, "Get matched component length", inline=True)
comment(0x8994, "Set carry (add 1 for separator)", inline=True)
comment(0x8995, "Add to text pointer", inline=True)
comment(0x8997, "Store updated pointer low", inline=True)
comment(0x8999, "No page crossing", inline=True)
comment(0x899B, "Increment page", inline=True)
comment(0x899D, "Check if alt workspace is set", inline=True)
comment(0x89A0, "&FF: not set", inline=True)
comment(0x89A2, "Set: skip CSD copy", inline=True)
comment(0x89A4, "Y=2: copy CSD sector", inline=True)
comment(0x89A6, "Get CSD sector byte", inline=True)
comment(0x89A9, "Copy to CSD drive sector", inline=True)
comment(0x89AC, "Next byte", inline=True)

# osfind_handler body - open file path (&B203-&B57E)
# After finding an empty channel slot, searches for the file,
# checks for conflicts with already-open files, and sets up
# the channel's buffer, PTR, EXT, and allocation info.
comment(0xB1C2, "Store filename high in OSFILE blk", inline=True)
comment(0xB1CB, "Clear current channel for errors", inline=True)
comment(0xB1DB, "Clear stored EXEC handle", inline=True)
comment(0xB1E0, "Return with stored handle", inline=True)
comment(0xB203, "Store channel index in zp_cf", inline=True)
comment(0xB205, "Save open mode (Y) in workspace", inline=True)
comment(0xB208, "Transfer mode to A", inline=True)
comment(0xB209, "Bit 7 set: open for output/random", inline=True)
comment(0xB20B, "Output/random: jump to write path", inline=True)
comment(0xB20E, "Open for input: search for file", inline=True)
comment(0xB211, "Found?", inline=True)
comment(0xB213, "Not found: A=0 (no handle)", inline=True)
comment(0xB215, "Return with A=0", inline=True)
comment(0xB218, "X=9: check all channels for conflict", inline=True)
comment(0xB21A, "Get channel flags", inline=True)
comment(0xB21D, "Bit 7 clear: channel not active", inline=True)
comment(0xB21F, "Get channel drive number", inline=True)
comment(0xB222, "Isolate drive bits", inline=True)
comment(0xB224, "Same drive as file being opened?", inline=True)
comment(0xB227, "Different drive: no conflict", inline=True)
comment(0xB229, "Compare sector address bytes", inline=True)
comment(0xB22C, "Compare with file's sector low", inline=True)
comment(0xB22F, "No match: no conflict", inline=True)
comment(0xB231, "Compare sector mid", inline=True)
comment(0xB234, "Match?", inline=True)
comment(0xB237, "No match: no conflict", inline=True)
comment(0xB239, "Compare sector high", inline=True)
comment(0xB23C, "Match?", inline=True)
comment(0xB23F, "No match: no conflict", inline=True)
comment(0xB241, "Y=&19: compare sequence number", inline=True)
comment(0xB243, "Get entry's sequence number", inline=True)
comment(0xB245, "Compare with channel's sequence", inline=True)
comment(0xB248, "Mismatch: not the same file", inline=True)
comment(0xB24A, "Match: Already open error", inline=True)
comment(0xB24D, "Next channel", inline=True)
comment(0xB24E, "Loop for all 10 channels", inline=True)
comment(0xB250, "Y=0: check entry first byte", inline=True)
comment(0xB252, "Get first name byte", inline=True)
comment(0xB254, "Bit 7 set: has attributes, open it", inline=True)
comment(0xB256, "No attributes: access violation", inline=True)

# Channel setup: copy EXT from directory entry
comment(0xB259, "Y=&12: entry length (4 bytes)", inline=True)
comment(0xB25B, "Get channel index", inline=True)
comment(0xB25D, "Get length low from entry", inline=True)
comment(0xB25F, "Store as channel EXT low", inline=True)
comment(0xB262, "Y=&13: length mid-low", inline=True)
comment(0xB263, "Get length mid-low", inline=True)
comment(0xB265, "Store as channel EXT mid-low", inline=True)
comment(0xB268, "Y=&14: length mid-high", inline=True)
comment(0xB269, "Get length mid-high", inline=True)
comment(0xB26B, "Store as channel EXT mid-high", inline=True)
comment(0xB26E, "Y=&15: length high", inline=True)
comment(0xB26F, "Get length high", inline=True)
comment(0xB271, "Store as channel EXT high", inline=True)

# Copy allocation size and start sector from entry
comment(0xB274, "Y=&12: allocation size (4 bytes)", inline=True)
comment(0xB276, "Get channel index", inline=True)
comment(0xB278, "Get allocation low from entry", inline=True)
comment(0xB27A, "Store as channel allocation low", inline=True)
comment(0xB27D, "Y=&13", inline=True)
comment(0xB27E, "Get allocation mid-low", inline=True)
comment(0xB280, "Store as channel alloc mid-low", inline=True)
comment(0xB283, "Y=&14", inline=True)
comment(0xB284, "Get allocation mid-high", inline=True)
comment(0xB286, "Store as channel alloc mid-high", inline=True)
comment(0xB289, "Y=&15", inline=True)
comment(0xB28A, "Get allocation high", inline=True)
comment(0xB28C, "Store as channel alloc high", inline=True)
comment(0xB28F, "Y=&16: start sector (3 bytes)", inline=True)
comment(0xB290, "Get start sector low", inline=True)
comment(0xB292, "Store as channel start sector low", inline=True)
comment(0xB295, "Y=&17: start sector mid", inline=True)
comment(0xB296, "Get start sector mid", inline=True)
comment(0xB298, "Store as channel start sector mid", inline=True)
comment(0xB29B, "Y=&18: start sector high", inline=True)
comment(0xB29C, "Get start sector high from entry", inline=True)
comment(0xB29E, "OR with current drive number", inline=True)
comment(0xB2A1, "Store as channel start+drive", inline=True)
comment(0xB2A4, "Y=&19: sequence number", inline=True)
comment(0xB2A5, "Get sequence number", inline=True)
comment(0xB2A7, "Store for channel", inline=True)

# Copy directory sector address for this file's parent
comment(0xB2AA, "Get parent dir sector low", inline=True)
comment(0xB2AD, "Store for channel", inline=True)
comment(0xB2B0, "Get parent dir sector mid", inline=True)
comment(0xB2B3, "Store for channel", inline=True)
comment(0xB2B6, "Get parent dir sector high", inline=True)
comment(0xB2B9, "Store for channel", inline=True)

# Set PTR to 0 and store channel flags
comment(0xB2BC, "A=0: set PTR to start of file", inline=True)
comment(0xB2BE, "Clear PTR low", inline=True)
comment(0xB2C1, "Clear PTR mid-low", inline=True)
comment(0xB2C4, "Clear PTR mid-high", inline=True)
comment(0xB2C7, "Clear PTR high", inline=True)
comment(0xB2CA, "Get open mode flags", inline=True)
comment(0xB2CD, "Store as channel flags", inline=True)
comment(0xB2D0, "Transfer channel index to A", inline=True)
comment(0xB2D1, "Clear carry for addition", inline=True)
comment(0xB2D2, "Add &30 to get file handle", inline=True)
comment(0xB2D4, "Push file handle on stack", inline=True)
comment(0xB2D5, "Ensure buffer state is consistent", inline=True)
comment(0xB2D8, "Restore file handle", inline=True)
comment(0xB2D9, "Save workspace and return A=handle", inline=True)
comment(0xB2DC, "Restore X from saved value", inline=True)
comment(0xB2DE, "Restore Y from saved value", inline=True)
comment(0xB2E0, "Return", inline=True)

# Open for output/random access path (&B2E1)
comment(0xB2E1, "Check open mode for random access", inline=True)
comment(0xB2E4, "Bit 6 clear: open for output only", inline=True)
comment(0xB2E6, "Random: search for existing file", inline=True)
comment(0xB2E9, "Save search result flags", inline=True)
comment(0xB2EA, "A=0: default no-file result", inline=True)
comment(0xB2EC, "Restore flags from search", inline=True)
comment(0xB2ED, "Not found: return A=0", inline=True)
comment(0xB2F2, "Y=1: check first name byte", inline=True)
comment(0xB2F4, "Get name byte", inline=True)
comment(0xB2F6, "Bit 7 set: has attributes", inline=True)
comment(0xB2F8, "No attributes: access violation", inline=True)
comment(0xB2FB, "Jump to check for open conflicts", inline=True)

# Open for output: create new file (&B2FE)
comment(0xB2FE, "Parse destination path", inline=True)
comment(0xB301, "Search for existing file", inline=True)
comment(0xB304, "Not found: create new", inline=True)
comment(0xB306, "Found: check it's not open", inline=True)
comment(0xB309, "Y=1: check access byte", inline=True)
comment(0xB30B, "Get first name byte", inline=True)
comment(0xB30D, "Bit 7 clear: access violation", inline=True)
comment(0xB30F, "Jump to open with existing entry", inline=True)
comment(0xB312, "A=0: clear OSFILE block", inline=True)
comment(0xB314, "X=&0F: clear 16 bytes", inline=True)
comment(0xB316, "Clear OSFILE block byte", inline=True)
comment(0xB319, "Next byte", inline=True)
comment(0xB31A, "Loop for 16 bytes", inline=True)

# Find best free space for new file (&B31C)
comment(0xB31C, "Get FSM end-of-list pointer", inline=True)
comment(0xB31F, "A=0: initial max size = 0", inline=True)
comment(0xB321, "OR FSM entry address bytes", inline=True)
comment(0xB324, "Continue OR-ing", inline=True)
comment(0xB327, "Get FSM entry length", inline=True)
comment(0xB32A, "Compare with current max", inline=True)
comment(0xB32D, "Smaller: skip", inline=True)
comment(0xB32F, "Larger: update max", inline=True)
comment(0xB332, "Back up 3 bytes to prev entry", inline=True)
comment(0xB333, "Continue", inline=True)
comment(0xB334, "Continue", inline=True)
comment(0xB335, "Loop for all entries", inline=True)
comment(0xB337, "Transfer A to Y (non-zero check)", inline=True)
comment(0xB338, "Zero: no free space at all", inline=True)
comment(0xB33A, "Store 0 as max (will use default)", inline=True)
comment(0xB33D, "X=1", inline=True)
comment(0xB33E, "Store default allocation", inline=True)
comment(0xB341, "A=&FF: fill OSFILE block", inline=True)
comment(0xB343, "Set load addr to &FFFFFFFF", inline=True)
comment(0xB346, "Second byte", inline=True)
comment(0xB349, "Third byte", inline=True)
comment(0xB34C, "Fourth byte", inline=True)
comment(0xB34F, "X=&40: OSFILE block offset", inline=True)
comment(0xB351, "Store block pointer low", inline=True)
comment(0xB353, "Y=&10: OSFILE block page", inline=True)
comment(0xB355, "Store block pointer high", inline=True)
comment(0xB357, "Save workspace", inline=True)
comment(0xB35A, "Create directory entry for new file", inline=True)
comment(0xB35D, "Write directory to disc", inline=True)
comment(0xB360, "Save workspace after dir write", inline=True)
comment(0xB363, "Restore original filename pointer", inline=True)
comment(0xB366, "Store in (&B4)", inline=True)
comment(0xB368, "Get filename high byte", inline=True)
comment(0xB36B, "Store in (&B5)", inline=True)
comment(0xB36D, "Search for newly created entry", inline=True)

# Set EXT to 0 for new file (&B370)
comment(0xB370, "A=0: new file has zero length", inline=True)
comment(0xB372, "Get channel index", inline=True)
comment(0xB374, "Set EXT low = 0", inline=True)
comment(0xB377, "Set EXT mid-low = 0", inline=True)
comment(0xB37A, "Set EXT mid-high = 0", inline=True)
comment(0xB37D, "Set EXT high = 0", inline=True)
comment(0xB380, "Jump to copy allocation and finish", inline=True)

# Close file path (&B383)
comment(0xB383, "Get channel number (Y) from saved", inline=True)
comment(0xB385, "Y non-zero: close specific channel", inline=True)
comment(0xB387, "Y=0: close all - save X first", inline=True)
comment(0xB388, "Push X on stack", inline=True)
comment(0xB389, "OSBYTE &77: close SPOOL and EXEC", inline=True)
comment(0xB38E, "Restore X", inline=True)
comment(0xB38F, "Store as saved X", inline=True)
comment(0xB391, "X=9: scan all channels", inline=True)
comment(0xB393, "Get channel flags", inline=True)
comment(0xB396, "Flags=0: not open, skip", inline=True)
comment(0xB398, "Next channel", inline=True)
comment(0xB399, "Loop for all 10 channels", inline=True)
comment(0xB39E, "A=0: all closed", inline=True)
comment(0xB3A0, "Restore X", inline=True)
comment(0xB3A3, "Return", inline=True)
comment(0xB3A4, "Channel is open: get file handle", inline=True)
comment(0xB3A5, "Clear carry for addition", inline=True)
comment(0xB3A6, "Add &30 to get handle", inline=True)
comment(0xB3A8, "Store handle", inline=True)
comment(0xB3AA, "Store channel index", inline=True)
comment(0xB3AC, "Close this channel", inline=True)
comment(0xB3AF, "Restore channel index", inline=True)
comment(0xB3B1, "Continue scanning", inline=True)

# sub_cb3b6 - close single channel
comment(0xB3B6, "Flush buffer if dirty", inline=True)
comment(0xB3B9, "Get channel flags", inline=True)
comment(0xB3BC, "A=0: clear channel flags (closed)", inline=True)
comment(0xB3BE, "Mark channel as closed", inline=True)
comment(0xB3C1, "Transfer old flags to A", inline=True)
comment(0xB3C2, "Bit 7 clear: was read-only", inline=True)
comment(0xB3C4, "Was writable: check if EXT changed", inline=True)
comment(0xB3C7, "Compare EXT low with allocation low", inline=True)
comment(0xB3CA, "Different: need to update dir entry", inline=True)
comment(0xB3CC, "Compare EXT mid-low", inline=True)
comment(0xB3CF, "With allocation mid-low", inline=True)
comment(0xB3D2, "Different: update needed", inline=True)
comment(0xB3D4, "Compare EXT mid-high", inline=True)
comment(0xB3D7, "With allocation mid-high", inline=True)
comment(0xB3DA, "Different: update needed", inline=True)
comment(0xB3DC, "Compare EXT high", inline=True)
comment(0xB3DF, "With allocation high", inline=True)
comment(0xB3E2, "Different: update needed", inline=True)
comment(0xB3E4, "EXT == alloc: no update needed", inline=True)
comment(0xB3E7, "Save workspace", inline=True)
comment(0xB3EA, "A=0: success", inline=True)
comment(0xB3EC, "Restore Y", inline=True)
comment(0xB3EE, "Restore X", inline=True)
comment(0xB3F0, "Return", inline=True)

# Update directory entry with actual file size on close
comment(0xB3F1, "Switch to file's drive", inline=True)
comment(0xB3F4, "Calculate sectors used from EXT", inline=True)
comment(0xB3F7, "Compare low byte with 1", inline=True)
comment(0xB3F9, "Get object sector low", inline=True)
comment(0xB3FC, "Add EXT mid-low + carry", inline=True)
comment(0xB3FF, "Store updated sector low", inline=True)
comment(0xB402, "Get sector mid", inline=True)
comment(0xB405, "Add EXT mid-high + carry", inline=True)
comment(0xB408, "Store updated sector mid", inline=True)
comment(0xB40B, "Get sector high", inline=True)
comment(0xB40E, "Add EXT high + carry", inline=True)
comment(0xB411, "Store updated sector high", inline=True)
comment(0xB414, "Calculate unused sectors to release", inline=True)
comment(0xB417, "Compare alloc low with 1", inline=True)
comment(0xB419, "Get alloc mid-low", inline=True)
comment(0xB41C, "Subtract EXT mid-low", inline=True)
comment(0xB41F, "Store unused low", inline=True)
comment(0xB422, "Get alloc mid-high", inline=True)
comment(0xB425, "Subtract EXT mid-high", inline=True)
comment(0xB428, "Store unused mid", inline=True)
comment(0xB42B, "Get alloc high", inline=True)
comment(0xB42E, "Subtract EXT high", inline=True)
comment(0xB431, "Store unused high", inline=True)
comment(0xB434, "Check if EXT has fractional sector", inline=True)
comment(0xB437, "Non-zero: adjust sector count", inline=True)
comment(0xB439, "Increment unused sector count", inline=True)
comment(0xB43C, "No wrap", inline=True)
comment(0xB43E, "Wrap: increment mid", inline=True)
comment(0xB441, "No wrap", inline=True)
comment(0xB443, "Wrap: increment high", inline=True)
comment(0xB446, "Update dir entry with actual length", inline=True)
comment(0xB449, "Y=&12: length field in entry", inline=True)
comment(0xB44B, "Store EXT low in entry", inline=True)
comment(0xB44D, "Get EXT mid-low", inline=True)
comment(0xB451, "Store in entry", inline=True)
comment(0xB453, "Get EXT mid-high", inline=True)
comment(0xB457, "Store in entry", inline=True)
comment(0xB459, "Get EXT high", inline=True)
comment(0xB45D, "Store in entry", inline=True)
comment(0xB462, "Write updated directory to disc", inline=True)
comment(0xB465, "Jump to release space and return", inline=True)

# sub_cb468 - check all channels on current drive
comment(0xB468, "X=9: scan all channels", inline=True)
comment(0xB46A, "Get channel flags", inline=True)
comment(0xB46D, "Not open: skip", inline=True)
comment(0xB46F, "Get channel drive number", inline=True)
comment(0xB472, "Isolate drive bits", inline=True)
comment(0xB474, "Same drive as current?", inline=True)
comment(0xB477, "Same drive: found one", inline=True)
comment(0xB479, "Next channel", inline=True)
comment(0xB47A, "Loop for all 10", inline=True)
comment(0xB47C, "Get current drive number", inline=True)
comment(0xB47F, "Get drive slot index", inline=True)
comment(0xB482, "Cache disc ID low from FSM", inline=True)
comment(0xB485, "Store in per-drive workspace", inline=True)
comment(0xB488, "Cache disc ID high from FSM", inline=True)
comment(0xB48B, "Store in per-drive workspace", inline=True)
comment(0xB48E, "Read clock for elapsed time", inline=True)
comment(0xB491, "Get current drive", inline=True)
comment(0xB494, "Get drive slot index", inline=True)
comment(0xB497, "Re-read disc ID low from FSM", inline=True)
comment(0xB49A, "Compare with cached value", inline=True)
comment(0xB49D, "Mismatch: disc was changed", inline=True)
comment(0xB49F, "Re-read disc ID high from FSM", inline=True)
comment(0xB4A2, "Compare with cached value", inline=True)
comment(0xB4A5, "Mismatch: disc was changed", inline=True)
comment(0xB4A7, "Get drive bit mask", inline=True)
comment(0xB4AA, "Update drive change mask", inline=True)
comment(0xB4AD, "Return (disc unchanged)", inline=True)

# sub_cb4bf - read clock for disc change timing
comment(0xB4BF, "OSWORD 1: read system clock", inline=True)
comment(0xB4C1, "X: control block low", inline=True)
comment(0xB4C3, "Y: control block high", inline=True)
comment(0xB4C8, "X=0: compare 5 clock bytes", inline=True)
comment(0xB4CA, "Y=4: 5 bytes to compare", inline=True)
comment(0xB4CC, "Set carry for subtraction", inline=True)
comment(0xB4CD, "Get current clock byte", inline=True)
comment(0xB4D0, "Save current value", inline=True)
comment(0xB4D1, "Subtract previous value", inline=True)
comment(0xB4D4, "Store difference", inline=True)
comment(0xB4D7, "Restore current value", inline=True)
comment(0xB4D8, "Save as new previous", inline=True)
comment(0xB4DB, "Next byte", inline=True)
comment(0xB4DC, "Decrement counter", inline=True)
comment(0xB4DD, "Loop for 5 bytes", inline=True)
comment(0xB4DF, "Check if elapsed time > threshold", inline=True)
comment(0xB4E2, "OR with byte 3", inline=True)
comment(0xB4E5, "OR with byte 2", inline=True)
comment(0xB4E8, "Non-zero high bytes: long time", inline=True)
comment(0xB4EA, "Check byte 1", inline=True)
comment(0xB4ED, "Less than 2 ticks?", inline=True)
comment(0xB4EF, "Yes: disc probably not changed", inline=True)
comment(0xB4F1, "Long time: set change flag", inline=True)
comment(0xB4F4, "Return", inline=True)
comment(0xB4F5, "Read clock and check disc", inline=True)
comment(0xB4F8, "Get current drive", inline=True)
comment(0xB4FB, "Get drive slot index", inline=True)
comment(0xB4FE, "Get channel bit mask", inline=True)
comment(0xB501, "XOR with stored mask", inline=True)
comment(0xB504, "Same: disc not changed", inline=True)
comment(0xB506, "Changed: reload FSM", inline=True)
comment(0xB508, "Y=&88: FSM control block", inline=True)
comment(0xB50A, "Read FSM from disc", inline=True)
comment(0xB50D, "Continue checking", inline=True)

# sub_cb510 - get bit mask for drive index
comment(0xB510, "A=&FF: start with all bits set", inline=True)
comment(0xB512, "Clear carry for shift", inline=True)
comment(0xB513, "Shift left (rotate 0 in)", inline=True)
comment(0xB514, "Decrement drive index by 2", inline=True)
comment(0xB515, "Continue", inline=True)
comment(0xB516, "Loop until index < 0", inline=True)
comment(0xB518, "AND with current change flags", inline=True)
comment(0xB51B, "Return bit mask in A", inline=True)

# sub_cb51c - set drive from A and check disc change
comment(0xB51C, "Isolate drive bits from A", inline=True)
comment(0xB51E, "Store drive for later", inline=True)
comment(0xB521, "Save X", inline=True)
comment(0xB522, "Push on stack", inline=True)
comment(0xB523, "Save Y", inline=True)
comment(0xB524, "Push on stack", inline=True)
comment(0xB525, "Read clock for timing check", inline=True)
comment(0xB528, "Get stored drive", inline=True)
comment(0xB52B, "Get drive slot index", inline=True)
comment(0xB52E, "Get bit mask for this drive", inline=True)
comment(0xB531, "XOR with change flags", inline=True)
comment(0xB534, "Same: disc hasn't changed", inline=True)
comment(0xB536, "Different: need to reload FSM", inline=True)
comment(0xB539, "Transfer to X", inline=True)
comment(0xB53A, "Save drive on stack", inline=True)
comment(0xB53B, "Save current drive", inline=True)
comment(0xB53E, "Store as temp drive", inline=True)
comment(0xB541, "Check saved drive", inline=True)
comment(0xB544, "&FF: not set", inline=True)
comment(0xB546, "Set: don't overwrite", inline=True)
comment(0xB548, "Save current as saved drive", inline=True)
comment(0xB54B, "Set temp to &FF", inline=True)
comment(0xB54E, "Set current to new drive", inline=True)
comment(0xB551, "Reload FSM for new drive", inline=True)
comment(0xB554, "Get temp drive back", inline=True)
comment(0xB557, "Set as current drive", inline=True)
comment(0xB55A, "Was it &FF?", inline=True)
comment(0xB55C, "No: keep it", inline=True)
comment(0xB55E, "Restore saved drive", inline=True)
comment(0xB561, "Set as current", inline=True)
comment(0xB564, "Restore saved drive as &FF", inline=True)
comment(0xB567, "Restore original drive from stack", inline=True)
comment(0xB568, "Compare with current", inline=True)
comment(0xB56B, "Same: no FSM reload needed", inline=True)
comment(0xB56D, "Different: reload FSM for current", inline=True)
comment(0xB56F, "Y=&88: FSM control block", inline=True)
comment(0xB571, "Read FSM from disc", inline=True)
comment(0xB574, "Restore Y from stack", inline=True)
comment(0xB575, "Transfer to Y", inline=True)
comment(0xB576, "Restore X from stack", inline=True)
comment(0xB577, "Transfer to X", inline=True)
comment(0xB578, "Return", inline=True)

# sub_cb579 - convert drive to slot index
comment(0xB579, "Shift drive right 4 positions", inline=True)
comment(0xB57A, "Second shift", inline=True)
comment(0xB57B, "Third shift", inline=True)
comment(0xB57C, "Fourth shift", inline=True)
comment(0xB57D, "Transfer to X as index", inline=True)
comment(0xB57E, "Return", inline=True)

# osbget_handler body (&AD7E-&B08E)
# After validating the channel and checking EOF,
# calculates the buffer address from PTR, loads the sector
# if needed, reads the byte, and advances PTR.
comment(0xAD7E, "Keep open+writable bits only", inline=True)
comment(0xAD80, "Set EOF-read flag (bit 3)", inline=True)
comment(0xAD82, "Store updated channel flags", inline=True)
comment(0xAD85, "Restore Y", inline=True)
comment(0xAD87, "Restore X", inline=True)
comment(0xAD89, "Set carry: C=1 means EOF", inline=True)
comment(0xAD8A, "A=&FE: EOF return value", inline=True)
comment(0xAD8C, "Return (EOF)", inline=True)
comment(0xAD8D, "Get channel index for buffer calc", inline=True)
comment(0xAD8F, "Clear carry for address calculation", inline=True)
comment(0xAD90, "Get channel buffer offset low", inline=True)
comment(0xAD93, "Add PTR mid-low for buffer addr", inline=True)
comment(0xAD96, "Store sector address low", inline=True)
comment(0xAD99, "Get channel buffer offset mid", inline=True)
comment(0xAD9C, "Add PTR mid-high", inline=True)
comment(0xAD9F, "Store sector address mid", inline=True)
comment(0xADA2, "Get channel buffer base page", inline=True)
comment(0xADA5, "Add PTR high", inline=True)
comment(0xADA8, "Store sector address high", inline=True)
comment(0xADAB, "A=&40: read buffer mode", inline=True)
comment(0xADAD, "Load sector into channel buffer", inline=True)
comment(0xADB0, "Get channel index", inline=True)
comment(0xADB2, "Get PTR low byte as buffer offset", inline=True)
comment(0xADB5, "A=0: clear modification flag", inline=True)
comment(0xADB7, "Store zero mod flag", inline=True)
comment(0xADBA, "Advance PTR and update flags", inline=True)
comment(0xADBD, "Read byte from buffer at PTR offset", inline=True)
comment(0xADBF, "Restore Y", inline=True)
comment(0xADC1, "Restore X", inline=True)
comment(0xADC3, "Clear carry: C=0 means success", inline=True)
comment(0xADC4, "Return (byte in A)", inline=True)

# sub_cadc5 - switch drive for channel I/O
comment(0xADC5, "Y=2: save 3 bytes of CSD sector", inline=True)
comment(0xADC7, "Get CSD sector byte", inline=True)
comment(0xADCA, "Store in temp workspace", inline=True)
comment(0xADCD, "Next byte", inline=True)
comment(0xADCE, "Loop for 3 bytes", inline=True)
comment(0xADD0, "Save current drive", inline=True)
comment(0xADD3, "Store as last access drive", inline=True)
comment(0xADD6, "Get channel index", inline=True)
comment(0xADD8, "Get channel's drive number", inline=True)
comment(0xADDB, "Isolate drive bits (top 3)", inline=True)
comment(0xADDD, "Save as current working drive", inline=True)
comment(0xADE0, "Get channel's sector low", inline=True)
comment(0xADE3, "Store in CSD sector low", inline=True)
comment(0xADE6, "Get channel's sector mid", inline=True)
comment(0xADE9, "Store in workspace mid", inline=True)
comment(0xADEC, "Get channel's sector high", inline=True)
comment(0xADEF, "Store in workspace high", inline=True)
comment(0xADF2, "Save workspace state", inline=True)
comment(0xADF5, "Y=2: restore CSD sector", inline=True)
comment(0xADF7, "Get saved CSD sector byte", inline=True)
comment(0xADFA, "Restore to CSD workspace", inline=True)
comment(0xADFD, "Next byte", inline=True)
comment(0xADFE, "Loop for 3 bytes", inline=True)
comment(0xAE00, "Get last access drive", inline=True)
comment(0xAE03, "Set as saved drive for restore", inline=True)
comment(0xAE06, "Ensure files on drive are closed", inline=True)
comment(0xAE09, "Get channel index", inline=True)
comment(0xAE0B, "Get channel's allocation low", inline=True)
comment(0xAE0E, "Store in object sector low", inline=True)
comment(0xAE11, "Get allocation mid", inline=True)
comment(0xAE14, "Store in workspace", inline=True)
comment(0xAE17, "Get allocation high + drive", inline=True)
comment(0xAE1A, "Mask to sector bits only", inline=True)
comment(0xAE1C, "Store sector high", inline=True)
comment(0xAE1F, "Set (&B8) to dir entry at &1205", inline=True)
comment(0xAE21, "Store low byte", inline=True)
comment(0xAE23, "Page &12", inline=True)
comment(0xAE25, "Store high byte", inline=True)
comment(0xAE27, "Get channel index", inline=True)
comment(0xAE29, "Y=0: check first dir entry byte", inline=True)
comment(0xAE2B, "Get first byte", inline=True)
comment(0xAE2D, "Non-zero: valid entry", inline=True)
comment(0xAE2F, "Zero: channel invalid, clear flags", inline=True)
comment(0xAE32, "Bad checksum error", inline=True)
comment(0xAE35, "Y=&19: check entry sequence number", inline=True)
comment(0xAE37, "Get sequence number from entry", inline=True)
comment(0xAE39, "Compare with channel's saved seq", inline=True)
comment(0xAE3C, "Mismatch: different entry", inline=True)
comment(0xAE3F, "Check next entry field", inline=True)
comment(0xAE41, "Compare sector field with channel", inline=True)
comment(0xAE44, "Mismatch: try next entry", inline=True)
comment(0xAE46, "Next byte (decreasing Y)", inline=True)
comment(0xAE47, "Past start of sector field (&16)?", inline=True)
comment(0xAE49, "Still in range: continue comparing", inline=True)
comment(0xAE4B, "All fields match: return", inline=True)
comment(0xAE4C, "Advance to next dir entry (+&1A)", inline=True)
comment(0xAE4E, "Clear carry", inline=True)
comment(0xAE4F, "Add 26 bytes per entry", inline=True)
comment(0xAE51, "Store updated pointer", inline=True)
comment(0xAE53, "No page crossing: continue search", inline=True)
comment(0xAE55, "Increment page", inline=True)

# sub_cae59 / sub_cae5e - extend file allocation
comment(0xAE59, "A=0: clear allocation flag", inline=True)
comment(0xAE5B, "Clear extension flag", inline=True)
comment(0xAE5E, "Get saved drive", inline=True)
comment(0xAE61, "Store for restore later", inline=True)
comment(0xAE64, "X=2: save 3 bytes of CSD", inline=True)
comment(0xAE66, "Get CSD sector byte", inline=True)
comment(0xAE69, "Store in temp workspace", inline=True)
comment(0xAE6C, "Next byte", inline=True)
comment(0xAE6D, "Loop for 3 bytes", inline=True)
comment(0xAE6F, "A=&FF: mark workspace as modified", inline=True)
comment(0xAE71, "Clear alt workspace pointer", inline=True)
comment(0xAE74, "Clear saved drive", inline=True)
comment(0xAE77, "Get channel index", inline=True)
comment(0xAE79, "Compare allocation with new PTR", inline=True)
comment(0xAE7C, "High byte matches?", inline=True)
comment(0xAE7F, "No: need to extend", inline=True)
comment(0xAE81, "Compare mid-high", inline=True)
comment(0xAE84, "Match?", inline=True)
comment(0xAE87, "No: need to extend", inline=True)
comment(0xAE89, "Compare mid-low", inline=True)
comment(0xAE8C, "Match?", inline=True)
comment(0xAE8F, "No: need to extend", inline=True)
comment(0xAE91, "Compare low byte", inline=True)
comment(0xAE94, "Match?", inline=True)
comment(0xAE97, "Alloc < PTR: need to extend", inline=True)
comment(0xAE99, "Compare EXT with new PTR", inline=True)
comment(0xAE9C, "High byte matches?", inline=True)
comment(0xAE9F, "No: EXT needs update", inline=True)
comment(0xAEA1, "Compare mid-high", inline=True)
comment(0xAEA4, "Match?", inline=True)
comment(0xAEA7, "No: EXT needs update", inline=True)
comment(0xAEA9, "Compare mid-low", inline=True)
comment(0xAEAC, "Match?", inline=True)
comment(0xAEAF, "No: EXT needs update", inline=True)
comment(0xAEB1, "Compare low byte", inline=True)
comment(0xAEB4, "Match?", inline=True)
comment(0xAEB7, "No: EXT needs update", inline=True)
comment(0xAEB9, "PTR == EXT: handle EOF write", inline=True)
comment(0xAEBC, "EXT > PTR: still within file", inline=True)
comment(0xAEBE, "PTR > alloc: need to extend file", inline=True)
comment(0xAEC1, "Calculate new allocation size", inline=True)
comment(0xAEC2, "A=0: compute pages needed", inline=True)
comment(0xAEC4, "Add PTR mid-low + 1 page", inline=True)
comment(0xAEC7, "Store new allocation mid", inline=True)
comment(0xAECA, "A=0: propagate carry", inline=True)
comment(0xAECC, "Add PTR high + carry", inline=True)
comment(0xAECF, "Store new allocation high", inline=True)
comment(0xAED2, "No overflow: proceed", inline=True)
comment(0xAED4, "Overflow: Disc full error", inline=True)
comment(0xAED7, "Switch to file's drive", inline=True)
comment(0xAEDA, "Get current allocation low", inline=True)
comment(0xAEDD, "Compare with 1 (minimum)", inline=True)
comment(0xAEDF, "Get allocation mid-low", inline=True)
comment(0xAEE2, "Add carry from compare", inline=True)
comment(0xAEE4, "Store as required size low", inline=True)
comment(0xAEE7, "Get allocation mid-high", inline=True)
comment(0xAEEA, "Add carry", inline=True)
comment(0xAEEC, "Store as required size mid", inline=True)
comment(0xAEEF, "Get allocation high", inline=True)
comment(0xAEF2, "Add carry", inline=True)
comment(0xAEF4, "Store as required size high", inline=True)
comment(0xAEF7, "Clear sector info", inline=True)
comment(0xAEF9, "Clear low", inline=True)
comment(0xAEFC, "Get new allocation mid", inline=True)
comment(0xAEFF, "Store as extension mid", inline=True)
comment(0xAF02, "Get new allocation high", inline=True)
comment(0xAF05, "Store as extension high", inline=True)
comment(0xAF0B, "Allocate disc space from FSM", inline=True)
comment(0xAF0E, "Y=&12: update dir entry length", inline=True)
comment(0xAF10, "A=0: clear length low byte", inline=True)
comment(0xAF12, "Get channel index", inline=True)
comment(0xAF14, "Store zero in entry length low", inline=True)
comment(0xAF16, "Update channel alloc low", inline=True)
comment(0xAF1A, "Store in dir entry", inline=True)
comment(0xAF1C, "Update channel alloc mid-low", inline=True)
comment(0xAF1F, "Get new alloc mid", inline=True)
comment(0xAF23, "Store in dir entry", inline=True)
comment(0xAF25, "Update channel alloc mid-high", inline=True)
comment(0xAF28, "Get new alloc high", inline=True)
comment(0xAF2C, "Store in dir entry", inline=True)
comment(0xAF2E, "Update channel alloc high", inline=True)
comment(0xAF31, "Get new start sector low", inline=True)
comment(0xAF35, "Store in dir entry start sector", inline=True)
comment(0xAF37, "Update channel start sector low", inline=True)
comment(0xAF3A, "Get new start sector mid", inline=True)
comment(0xAF3E, "Store in dir entry", inline=True)
comment(0xAF40, "Update channel start sector mid", inline=True)
comment(0xAF43, "Get new start sector high", inline=True)
comment(0xAF47, "Store in dir entry", inline=True)
comment(0xAF49, "OR with drive number for channel", inline=True)
comment(0xAF4C, "Update channel start sector+drive", inline=True)
comment(0xAF4F, "Write directory back to disc", inline=True)
comment(0xAF52, "Clear bit 3 of ADFS flags", inline=True)
comment(0xAF54, "Mask off bit 3", inline=True)
comment(0xAF56, "Store cleared flags", inline=True)
comment(0xAF58, "Set up buffer: page &12", inline=True)
comment(0xAF5A, "Store buffer start page", inline=True)
comment(0xAF5D, "Buffer length: 9 pages (&1200)", inline=True)
comment(0xAF5F, "Store buffer length", inline=True)
comment(0xAF62, "X=0: check if file was relocated", inline=True)
comment(0xAF64, "Y=2: compare old and new sectors", inline=True)
comment(0xAF66, "Get old start sector byte", inline=True)
comment(0xAF69, "Store for copy source", inline=True)
comment(0xAF6C, "Compare with new start sector", inline=True)
comment(0xAF6F, "Same: no relocation needed", inline=True)
comment(0xAF71, "Different: flag relocation", inline=True)
comment(0xAF72, "Get new start sector byte", inline=True)
comment(0xAF75, "Store for copy destination", inline=True)
comment(0xAF78, "Get required size byte", inline=True)
comment(0xAF7B, "Store for copy length", inline=True)
comment(0xAF7E, "Next byte", inline=True)
comment(0xAF7F, "Loop for 3 bytes", inline=True)
comment(0xAF81, "X non-zero: relocation occurred", inline=True)
comment(0xAF82, "Zero: no relocation, skip copy", inline=True)
comment(0xAF84, "Copy data from old to new location", inline=True)
comment(0xAF87, "Check extension flag", inline=True)
comment(0xAF8A, "Non-zero: skip zeroing", inline=True)
comment(0xAF8C, "Jump to update EXT", inline=True)
comment(0xAF8F, "Get channel index", inline=True)
comment(0xAF91, "Clear carry for address calculation", inline=True)
comment(0xAF92, "Get EXT mid-low", inline=True)
comment(0xAF95, "Add channel offset low", inline=True)
comment(0xAF98, "Store zero-fill start sector low", inline=True)
comment(0xAF9B, "Get EXT mid-high", inline=True)
comment(0xAF9E, "Add channel offset mid", inline=True)
comment(0xAFA1, "Store zero-fill start mid", inline=True)
comment(0xAFA4, "Get EXT high", inline=True)
comment(0xAFA7, "Add channel base + drive", inline=True)
comment(0xAFAA, "Store zero-fill start high", inline=True)
comment(0xAFAD, "A=&C0: write buffer mode", inline=True)
comment(0xAFAF, "Set up buffer for writing zeros", inline=True)
comment(0xAFB2, "Get channel index", inline=True)
comment(0xAFB4, "Get EXT low as buffer start", inline=True)
comment(0xAFB7, "A=0: zero fill", inline=True)
comment(0xAFB9, "Write zero to buffer", inline=True)
comment(0xAFBB, "Next byte", inline=True)
comment(0xAFBC, "Loop for rest of sector", inline=True)
comment(0xAFBE, "Get new PTR mid-low", inline=True)
comment(0xAFC1, "Clear carry", inline=True)
comment(0xAFC2, "Add channel base", inline=True)
comment(0xAFC5, "Store target sector low", inline=True)
comment(0xAFC8, "Get new PTR mid-high", inline=True)
comment(0xAFCB, "Add channel offset", inline=True)
comment(0xAFCE, "Store target sector mid", inline=True)
comment(0xAFD1, "Get new PTR high", inline=True)
comment(0xAFD4, "Add channel base + drive", inline=True)
comment(0xAFD7, "Store target sector high", inline=True)
comment(0xAFDA, "Get PTR low byte", inline=True)
comment(0xAFDD, "Non-zero: not sector-aligned", inline=True)
comment(0xAFDF, "Check sector low", inline=True)
comment(0xAFE2, "Non-zero: adjust sector", inline=True)
comment(0xAFE4, "Check sector mid", inline=True)
comment(0xAFE7, "Non-zero: adjust mid", inline=True)
comment(0xAFE9, "Decrement sector high", inline=True)
comment(0xAFEC, "Decrement sector mid", inline=True)
comment(0xAFEF, "Decrement sector low", inline=True)
comment(0xAFF2, "Compare with buffer sector", inline=True)
comment(0xAFF5, "Match low byte?", inline=True)
comment(0xAFF8, "No: need to write more zeros", inline=True)
comment(0xAFFA, "Match mid byte?", inline=True)
comment(0xAFFD, "Check mid", inline=True)
comment(0xB000, "No: need more", inline=True)
comment(0xB002, "Match high byte?", inline=True)
comment(0xB005, "Check high", inline=True)
comment(0xB008, "No: need more", inline=True)
comment(0xB00A, "All match: done zeroing", inline=True)
comment(0xB010, "Advance buffer sector: inc low", inline=True)
comment(0xB013, "No wrap", inline=True)
comment(0xB015, "Wrap: inc mid", inline=True)
comment(0xB018, "No wrap", inline=True)
comment(0xB01A, "Wrap: inc high", inline=True)
comment(0xB01D, "A=&40: read buffer mode", inline=True)
comment(0xB01F, "Load next sector into buffer", inline=True)
comment(0xB022, "Y=0: zero fill entire sector", inline=True)
comment(0xB025, "Write zero to buffer", inline=True)
comment(0xB027, "Next byte", inline=True)
comment(0xB028, "Loop for 256 bytes", inline=True)
comment(0xB02A, "Get channel buffer table index", inline=True)
comment(0xB02D, "A=&C0: mark buffer as dirty", inline=True)
comment(0xB02F, "OR with channel state", inline=True)
comment(0xB032, "Store dirty state", inline=True)
comment(0xB035, "Flush dirty buffer to disc", inline=True)
comment(0xB038, "Compare current sector with target", inline=True)
comment(0xB03B, "Compare low bytes", inline=True)
comment(0xB03E, "No match: advance sector", inline=True)
comment(0xB040, "Compare mid bytes", inline=True)
comment(0xB043, "Compare", inline=True)
comment(0xB046, "No match: advance", inline=True)
comment(0xB048, "Compare high bytes", inline=True)
comment(0xB04B, "Compare", inline=True)
comment(0xB04E, "Match: done writing zeros", inline=True)
comment(0xB050, "Advance channel sector: inc low", inline=True)
comment(0xB053, "No wrap", inline=True)
comment(0xB055, "Wrap: inc mid", inline=True)
comment(0xB058, "No wrap", inline=True)
comment(0xB05A, "Wrap: inc high", inline=True)
comment(0xB05D, "Continue zeroing loop", inline=True)

# cb060 - update EXT and restore drive
comment(0xB060, "Get channel index", inline=True)
comment(0xB062, "Get new PTR low", inline=True)
comment(0xB065, "Store as new EXT low", inline=True)
comment(0xB068, "Get new PTR mid-low", inline=True)
comment(0xB06B, "Store as new EXT mid-low", inline=True)
comment(0xB06E, "Get new PTR mid-high", inline=True)
comment(0xB071, "Store as new EXT mid-high", inline=True)
comment(0xB074, "Get new PTR high", inline=True)
comment(0xB077, "Store as new EXT high", inline=True)
comment(0xB07A, "Save workspace", inline=True)
comment(0xB07D, "Restore saved drive from temp", inline=True)
comment(0xB080, "Set as saved drive", inline=True)
comment(0xB083, "X=2: restore 3 bytes of CSD", inline=True)
comment(0xB085, "Get saved CSD byte", inline=True)
comment(0xB088, "Restore to CSD workspace", inline=True)
comment(0xB08B, "Next byte", inline=True)
comment(0xB08C, "Loop for 3 bytes", inline=True)
comment(0xB08E, "Return", inline=True)

# compare_filename remaining items - scattered through extent
comment(0x877E, "Advance Y (pattern index)", inline=True)
comment(0x8781, "Return", inline=True)
comment(0x8785, "Pattern check failed: Bad name", inline=True)
comment(0x87A3, "Is it '*'? Match rest", inline=True)
comment(0x87CA, "Discard saved Y", inline=True)
comment(0x8886, "Y=&88: FSM read control block page", inline=True)
comment(0x8888, "Read FSM from disc", inline=True)
comment(0x88A3, "X=&17: directory read block offset", inline=True)
comment(0x88A5, "Read directory from disc", inline=True)
comment(0x89AD, "Loop for 3 bytes", inline=True)
comment(0x89AF, "X=&0A: copy 11-byte disc op template", inline=True)
comment(0x89B1, "Get template byte from ROM", inline=True)
comment(0x89B4, "Store in disc op workspace", inline=True)
comment(0x89B7, "Next byte", inline=True)
comment(0x89B8, "Loop for 11 bytes", inline=True)
comment(0x89BA, "X=2: copy 3 sector address bytes", inline=True)
comment(0x89BC, "Y=&16: start sector in entry", inline=True)
comment(0x89BE, "Get sector byte from entry", inline=True)
comment(0x89C0, "Store in disc op sector field", inline=True)
comment(0x89C3, "Also store in CSD info", inline=True)
comment(0x89C6, "Next entry byte", inline=True)
comment(0x89C7, "Next sector byte", inline=True)
comment(0x89C8, "Loop for 3 bytes", inline=True)
comment(0x89CA, "Execute disc read command", inline=True)
comment(0x89CD, "Continue parsing path", inline=True)

# c89d0/c89d3 - save workspace and return
comment(0x89D0, "Get object type result", inline=True)
comment(0x89D3, "Save on stack", inline=True)
comment(0x89D4, "Check if drive was changed", inline=True)
comment(0x89D7, "Saved drive = &FF (not changed)?", inline=True)
comment(0x89D9, "Not changed: skip drive restore", inline=True)
comment(0x89DB, "Restore original drive", inline=True)
comment(0x89DE, "A=&FF: clear saved drive marker", inline=True)
comment(0x89E0, "Mark saved drive as unused", inline=True)
comment(0x89E3, "X=&0C: FSM control block offset", inline=True)
comment(0x89E5, "Y=&88: FSM control block page", inline=True)
comment(0x89E7, "Reload FSM for original drive", inline=True)
comment(0x89EA, "Check alt workspace pointer", inline=True)
comment(0x89ED, "&FF: not set", inline=True)
comment(0x89EF, "Not set: skip workspace restore", inline=True)
comment(0x89F1, "Transfer to X", inline=True)
comment(0x89F2, "Y=&0A: copy 11-byte template", inline=True)
comment(0x89F4, "Get template byte", inline=True)
comment(0x89F7, "Store in workspace", inline=True)
comment(0x89FA, "Next byte", inline=True)
comment(0x89FB, "Loop for 11 bytes", inline=True)
comment(0x89FD, "Store alt sector high", inline=True)
comment(0x8A00, "Store in disc op sector", inline=True)
comment(0x8A03, "Get alt sector mid", inline=True)
comment(0x8A06, "Store in CSD mid", inline=True)
comment(0x8A09, "Store in disc op mid", inline=True)
comment(0x8A0C, "Get CSD sector low", inline=True)
comment(0x8A0F, "Store in CSD low", inline=True)
comment(0x8A12, "Store in disc op low", inline=True)
comment(0x8A15, "A=&FF: clear alt workspace", inline=True)
comment(0x8A17, "Mark as unused", inline=True)
comment(0x8A1A, "Read directory from disc", inline=True)
comment(0x8A1D, "Save flags to workspace", inline=True)
comment(0x8A1F, "Store in flags save area", inline=True)
comment(0x8A25, "Y=&FB: save 252 bytes of workspace", inline=True)
comment(0x8A27, "Get workspace byte", inline=True)
comment(0x8A2A, "Store in saved workspace", inline=True)
comment(0x8A2C, "Next byte", inline=True)
comment(0x8A2D, "Loop until Y=0", inline=True)
comment(0x8A2F, "Get byte at Y=0 too", inline=True)
comment(0x8A32, "Store in saved workspace", inline=True)
comment(0x8A34, "Update workspace checksum", inline=True)
comment(0x8A37, "Restore X from (&B8)", inline=True)
comment(0x8A39, "Restore Y from (&B9)", inline=True)
comment(0x8A3B, "Restore object type from stack", inline=True)
comment(0x8A3C, "Return", inline=True)

# sub_c8a3d / sub_c8a45 - multi-sector disc read with chunking
comment(0x8A3D, "Set up sector count and execute", inline=True)
comment(0x8A40, "Success: return Z set", inline=True)
comment(0x8A45, "Get disc op command", inline=True)
comment(0x8A48, "Command 8 (read)?", inline=True)
comment(0x8A4A, "Yes: check sector count", inline=True)
comment(0x8A4C, "Get partial transfer count", inline=True)
comment(0x8A4F, "Zero: no partial, skip adjust", inline=True)
comment(0x8A51, "Clear partial transfer count", inline=True)
comment(0x8A53, "Store zero", inline=True)
comment(0x8A56, "Increment full sector count", inline=True)
comment(0x8A59, "No wrap", inline=True)
comment(0x8A5B, "Wrap: increment mid byte", inline=True)
comment(0x8A5E, "No wrap", inline=True)
comment(0x8A60, "Wrap: increment high byte", inline=True)
comment(0x8A63, "X=&15: disc op block offset", inline=True)
comment(0x8A65, "Y=&10: disc op block page", inline=True)
comment(0x8A67, "Set sector count to &FF (max)", inline=True)
comment(0x8A69, "Store max sector count", inline=True)
comment(0x8A6C, "Check if total > 255 sectors", inline=True)
comment(0x8A6F, "OR with mid byte", inline=True)
comment(0x8A72, "Both zero: <= 255, use exact count", inline=True)
comment(0x8A77, "Non-zero: use max (&FF), loop", inline=True)
comment(0x8A79, "Advance transfer address by &FF pages", inline=True)
comment(0x8A7B, "Clear carry for addition", inline=True)
comment(0x8A7C, "Add &FF to transfer addr mid", inline=True)
comment(0x8A7F, "Store updated mid", inline=True)
comment(0x8A82, "No carry", inline=True)
comment(0x8A84, "Carry: increment high", inline=True)
comment(0x8A87, "No wrap", inline=True)
comment(0x8A89, "Wrap: increment highest", inline=True)
comment(0x8A8C, "Advance disc sector by &FF", inline=True)
comment(0x8A8E, "Clear carry", inline=True)
comment(0x8A8F, "Add &FF to sector low", inline=True)
comment(0x8A92, "Store updated sector low", inline=True)
comment(0x8A95, "No carry", inline=True)
comment(0x8A97, "Carry: increment sector mid", inline=True)
comment(0x8A9A, "No wrap", inline=True)
comment(0x8A9C, "Wrap: increment sector high", inline=True)
comment(0x8A9F, "Subtract &FF from remaining count", inline=True)
comment(0x8AA2, "Set carry for subtraction", inline=True)
comment(0x8AA3, "Subtract &FF", inline=True)
comment(0x8AA5, "Store updated count low", inline=True)
comment(0x8AA8, "No borrow: loop for more chunks", inline=True)
comment(0x8AAA, "Borrow: decrement mid byte", inline=True)
comment(0x8AAD, "Non-zero: adjust high too", inline=True)
comment(0x8AAF, "Decrement high byte", inline=True)
comment(0x8AB2, "Decrement mid byte", inline=True)
comment(0x8AB5, "Continue chunked read", inline=True)
comment(0x8AB7, "Get remaining sector count", inline=True)
comment(0x8ABA, "Zero: check for partial sector", inline=True)
comment(0x8ABC, "Non-zero: use as final chunk size", inline=True)
comment(0x8AC2, "Non-zero: execute this chunk", inline=True)
comment(0x8AC4, "Get partial transfer count", inline=True)
comment(0x8AC7, "Non-zero: execute partial sector", inline=True)
comment(0x8AC9, "All done: return", inline=True)
comment(0x8ACA, "Store partial count as sector count", inline=True)
comment(0x8ACD, "Advance transfer address by partial", inline=True)
comment(0x8AD0, "Clear carry", inline=True)
comment(0x8AD1, "Add partial count to sector", inline=True)
comment(0x8AD4, "Store updated sector", inline=True)
comment(0x8AD7, "No carry", inline=True)
comment(0x8AD9, "Carry: increment mid", inline=True)
comment(0x8ADC, "No wrap", inline=True)
comment(0x8ADE, "Wrap: increment high", inline=True)
comment(0x8AE1, "Advance transfer address", inline=True)
comment(0x8AE4, "Clear carry", inline=True)
comment(0x8AE5, "Add to transfer addr", inline=True)
comment(0x8AE8, "Store updated addr", inline=True)
comment(0x8AEB, "No carry", inline=True)
comment(0x8AED, "Carry: increment high", inline=True)
comment(0x8AF0, "No wrap", inline=True)
comment(0x8AF2, "Wrap: increment highest", inline=True)
comment(0x8AFB, "Execute disc read with retry", inline=True)
comment(0x8AFE, "Success: return", inline=True)
comment(0x8B00, "Decrement retry counter", inline=True)
comment(0x8B02, "More retries: try again", inline=True)

# sub_c8b04 - execute disc command via workspace block
comment(0x8B04, "X=&15: disc op block offset", inline=True)
comment(0x8B06, "Y=&10: disc op block page", inline=True)
comment(0x8B08, "Store in (&B0)", inline=True)
comment(0x8B0A, "Store page in (&B1)", inline=True)
comment(0x8B0C, "Get current drive", inline=True)
comment(0x8B0F, "OR into sector high byte", inline=True)
comment(0x8B12, "Store updated sector+drive", inline=True)
comment(0x8B15, "Store as current drive info", inline=True)
comment(0x8B18, "Get ADFS flags", inline=True)
comment(0x8B1A, "Check bit 5: hard drive present?", inline=True)

comment(0x884C, "Get filename from (&B4)", inline=True)
comment(0x884F, "Empty filename: bad name", inline=True)

comment(0x8708, "Increment pointer low byte", inline=True)
comment(0x870A, "No page crossing: return", inline=True)
comment(0x870C, "Increment pointer high byte", inline=True)
comment(0x870E, "Return", inline=True)

# sub_c8712 - beginning of pathname parser
comment(0x8712, "Set up directory for search", inline=True)
comment(0x8715, "Y=0: clear search flag", inline=True)
comment(0x8717, "Store in workspace", inline=True)

# invalidate_fsm_and_dir (&8476)
comment(0x8476, "X=&0C: clear 12 workspace bytes", inline=True)
comment(0x8478, "A=&FF: invalid marker", inline=True)
comment(0x847A, "Invalidate drive/sector workspace", inline=True)
comment(0x847D, "Invalidate CSD/lib/prev sectors", inline=True)
comment(0x8483, "Reset CSD name to default", inline=True)
comment(0x8489, "Y=0: loop counter", inline=True)
comment(0x848B, "A=0: zero fill", inline=True)
comment(0x848C, "Zero FSM sector 1 buffer", inline=True)
comment(0x848F, "Zero FSM sector 0 buffer", inline=True)
comment(0x8492, "Zero directory buffer", inline=True)
comment(0x8495, "Next byte", inline=True)
comment(0x8496, "Loop for 256 bytes", inline=True)

# osfile_handler (&923E)
comment(0x923E, "Save control block address low", inline=True)
comment(0x9240, "Save control block address high", inline=True)
comment(0x9242, "Transfer function code to Y", inline=True)
comment(0x9243, "Clear current channel", inline=True)
comment(0x9248, "A = function * 2 (table index)", inline=True)
comment(0x924A, "X = A*2 + 1 (skip table base)", inline=True)
comment(0x924C, "Function < 0? Invalid", inline=True)
comment(0x924E, "Function >= 8? Invalid", inline=True)
comment(0x9252, "Push dispatch address high byte", inline=True)
comment(0x9256, "Push dispatch address low byte", inline=True)
comment(0x925A, "Restore function code to A", inline=True)
comment(0x925B, "Save function code on stack", inline=True)
comment(0x925C, "Y=0: read filename pointer from block", inline=True)
comment(0x925E, "Filename address low byte", inline=True)
comment(0x9260, "Store in (&B4)", inline=True)
comment(0x9263, "Filename address high byte", inline=True)
comment(0x9265, "Store in (&B5)", inline=True)
comment(0x9267, "Restore function code", inline=True)
comment(0x9268, "RTS-dispatch to function handler", inline=True)

# sub_c9287 / sub_c927b - print filename from directory entry
comment(0x927B, "Transfer index to X", inline=True)
comment(0x927C, "Set up (&B6) to point to pathname", inline=True)
comment(0x9280, "Get pathname format byte", inline=True)
comment(0x9283, "Store as pointer low byte", inline=True)
comment(0x9285, "X=&0C: max 12 characters", inline=True)
comment(0x9289, "Get character from entry", inline=True)
comment(0x928B, "Strip bit 7 (access bit)", inline=True)
comment(0x928D, "Is it a printable character?", inline=True)
comment(0x928F, "No, pad rest with spaces", inline=True)
comment(0x9294, "Next character", inline=True)
comment(0x9295, "Decrement column counter", inline=True)
comment(0x9296, "Loop for remaining columns", inline=True)
comment(0x929C, "Pad with spaces", inline=True)
comment(0x929D, "Loop for remaining columns", inline=True)

# check_char_is_terminator (&871A)
comment(0x871A, "Get character, strip bit 7", inline=True)
comment(0x871E, "Is it '.'?", inline=True)
comment(0x8720, "Yes, terminator", inline=True)
comment(0x8722, 'Is it a double-quote?', inline=True)
comment(0x8724, "Yes, terminator", inline=True)
comment(0x8726, "Is it >= space?", inline=True)
comment(0x8728, "Yes, not a terminator", inline=True)
comment(0x872A, "X=0: signal terminator found", inline=True)

# sub_c872d - check filename length (&872D)
label(0x84C1, "find_fsm_position")
label(0x84C3, "scan_fsm_entries_loop")
label(0x84CF, "compare_fsm_addr_loop")
label(0x84DC, "check_exact_match")
label(0x84E1, "found_insertion_point")
label(0x84EC, "check_adjacent_to_next_loop")
label(0x84FA, "insert_new_fsm_entry")
label(0x84FD, "adjacent_next_byte")
label(0x850C, "check_adjacent_to_prev_loop")
label(0x851F, "adjacent_prev_byte")
label(0x852C, "merge_with_prev_loop")
label(0x8543, "check_triple_merge_loop")
label(0x8550, "shift_entries_down_loop")
label(0x8564, "shrink_fsm_list")
label(0x856B, "add_size_to_existing_entry")
label(0x856F, "merge_forward_loop")
label(0x8588, "check_merge_with_prev")
label(0x8590, "compare_prev_plus_size_loop")
label(0x85A1, "merge_size_into_prev")
label(0x85AE, "add_size_to_prev_loop")
label(0x85C1, "insert_new_entry")
label(0x85D5, "shift_entries_up_start")
label(0x85D8, "shift_entries_up_loop")
label(0x85EC, "store_new_entry")
label(0x85EE, "store_new_entry_loop")
label(0x8609, "sum_free_space")
label(0x8614, "sum_fsm_entries_loop")
label(0x861D, "sum_entry_bytes_loop")
label(0x8632, "allocate_disc_space")
label(0x8637, "scan_for_best_fit")
label(0x864A, "compare_total_vs_requested")
label(0x8656, "disc_full_error")
label(0x8664, "compaction_required_error")
label(0x867C, "use_best_fit_entry")
label(0x867E, "copy_allocated_sector_loop")
label(0x868D, "advance_entry_addr_loop")
label(0x86A5, "subtract_from_length_loop")
label(0x86B8, "compare_entry_size")
label(0x86BF, "compare_size_bytes_loop")
label(0x86D1, "copy_exact_match_addr_loop")
label(0x86DD, "remove_exact_entry_loop")
label(0x86F1, "shrink_list_after_exact")
label(0x86FA, "check_if_first_fit")
label(0x8703, "continue_scanning")
label(0x8708, "advance_text_ptr")
label(0x870F, "parse_and_setup_search")
label(0x872A, "set_terminator_flag")
label(0x872D, "check_filename_length")
subroutine(0x872D, "check_filename_length",
    title="Check filename length, copy entry name, and compare",
    description="""\
Scan up to 10 characters of filename at (&B4),Y. Raises
Bad name error if no terminator found within 10 characters.
Then copies all 10 bytes of the directory entry name at
(zp_entry_ptr) to wksp_object_name, stripping bit 7 from
each byte. This removes access attribute bits so the
workspace copy contains pure 7-bit ASCII. Padding CRs
(&0D) in unused name positions are preserved as-is; they
terminate the name during compare_filename (via CMP #&21).

Falls through to compare_filename, whose return flags are
passed back to the caller: Z=1 for match, and carry
indicates sort order (C=0: pattern < entry name, C=1:
pattern >= entry name). See compare_filename for details.
""",
    on_exit={"a": "corrupted (Z set if match, C for sort order)",
             "x": "corrupted", "y": "corrupted"})
comment(0x872D, "Y=&0A: check up to 10 characters", inline=True)
comment(0x872F, "Check next character", inline=True)
comment(0x8732, "Terminator found, ok", inline=True)
comment(0x8734, "Decrement character count", inline=True)
comment(0x8735, "Continue checking", inline=True)
comment(0x8744, "Y=9: copy 10 bytes of entry name", inline=True)
comment(0x8746, "Get name byte from directory entry", inline=True)
comment(0x8748, "Strip bit 7 (access bit)", inline=True)
comment(0x874A, "Store in object name workspace", inline=True)

# c8753 - compare filename against pattern (&8753)
label(0x872F, "check_name_char_loop")
label(0x8737, "bad_name_error")
label(0x8744, "name_length_ok")
label(0x8746, "copy_entry_name_loop")
label(0x8753, "compare_filename")
subroutine(0x8753, "compare_filename",
    title="Compare filename against pattern with wildcards",
    description="""\
Compare the object name in workspace against the pattern
at (&B4),Y. Supports '#' (match one char) and '*' (match
rest) wildcards. Case-insensitive comparison.

The workspace name has already had bit 7 stripped by
copy_entry_name_loop, so name characters are pure 7-bit
ASCII. End-of-name is detected by CMP #&21: any character
below '!' (including CR padding at &0D) signals the name
has ended. Called recursively for '*' wildcard backtracking.

Return flags are used by begin_dir_entry_search for the
sorted-order early exit:
  Z=1:        match found
  Z=0, C=0:  no match, pattern < entry name (entry sorts
              after pattern; stop scanning sorted dir)
  Z=0, C=1:  no match, pattern > entry name (entry sorts
              before pattern; continue to next entry)
Wildcard patterns may return C=1 even when the pattern
sorts before the entry, so wildcard searches do not
benefit from the sorted early-exit optimisation.
""",
    on_entry={"x": "index into wksp_object_name",
              "y": "index into pattern at (&B4)"},
    on_exit={"a": "corrupted (Z set if match, C for sort order)",
             "x": "corrupted", "y": "corrupted"})
comment(0x8753, "X >= 10? End of name reached", inline=True)
comment(0x8755, "Yes, check pattern is also done", inline=True)
comment(0x8757, "Get object name character", inline=True)
comment(0x875A, "< '!': end of name (CR padding)", inline=True)
comment(0x875C, "Yes, name ended early", inline=True)
comment(0x875E, "Convert name char to lowercase", inline=True)
comment(0x8760, "Store for comparison", inline=True)
comment(0x8763, "Y >= 10? Pattern exhausted", inline=True)
comment(0x8765, "Yes, check if pattern terminated", inline=True)
comment(0x8767, "Check if pattern char is terminator", inline=True)
comment(0x876A, "Yes, compare lengths", inline=True)
comment(0x876C, "Pattern char is '*' wildcard?", inline=True)
comment(0x876E, "Yes, match rest of name", inline=True)
comment(0x8770, "Pattern char is '#' wildcard?", inline=True)
comment(0x8772, "Yes, match any single char", inline=True)
comment(0x8774, "Convert pattern char to lowercase", inline=True)
comment(0x8776, "Compare pattern char with name char", inline=True)
comment(0x8779, "C=0: pattern < name (sorted exit)", inline=True)
comment(0x877B, "C=1: pattern > name (continue)", inline=True)
comment(0x877D, "Match: advance both pointers", inline=True)

# osbyte_y_ff_x_00 / osbyte_x_00 (&84A0)
comment(0x84A0, "Y=&FF: read current value", inline=True)
comment(0x84A2, "X=0: no modification", inline=True)
comment(0x84A4, "Call OSBYTE", inline=True)

# oscli_at_x (&84A7)
comment(0x84A7, "Y=&84: high byte (string in this ROM)", inline=True)
comment(0x84A9, "Call OSCLI with (X,Y) address", inline=True)

# fscv_handler (&9E50)
comment(0x9E50, "Save text pointer in (&B4)", inline=True)
comment(0x9E54, "Transfer FSC code to X", inline=True)
comment(0x9E55, "FSC >= &80? Not for us", inline=True)
comment(0x9E57, "FSC >= 9? Not for us", inline=True)
comment(0x9E5B, "Clear current channel", inline=True)
comment(0x9E60, "Get dispatch address high byte", inline=True)
comment(0x9E64, "Get dispatch address low byte", inline=True)
comment(0x9E68, "Restore X (text pointer low)", inline=True)
comment(0x9E6A, "Restore Y (text pointer high)", inline=True)
comment(0x9E6C, "RTS-dispatch to handler", inline=True)

# star_cmd (&9E7F) - command table parser
comment(0x9E7F, "Wait if files being ensured", inline=True)
comment(0x9E82, "Set up workspace pointer", inline=True)
comment(0x9E8A, "Skip leading spaces in command", inline=True)
comment(0x9E8D, "X=&FD: start before first table entry", inline=True)
comment(0x9E8F, "Advance X past previous entry's data", inline=True)
comment(0x9E91, "Y=&FF: start before first char", inline=True)
comment(0x9E93, "Next table byte and command char", inline=True)
comment(0x9E95, "Get byte from command table", inline=True)
comment(0x9E98, "Bit 7 set: end of command name", inline=True)
comment(0x9E9A, "Compare with input character", inline=True)
comment(0x9E9C, "Match, continue", inline=True)
comment(0x9E9E, "Try case-insensitive (OR &20)", inline=True)
comment(0x9EA0, "Compare again", inline=True)
comment(0x9EA2, "Match, continue", inline=True)
comment(0x9EA5, "Skip to next table entry", inline=True)
comment(0x9EA6, "Read table byte", inline=True)
comment(0x9EA9, "Loop until bit 7 set (end marker)", inline=True)
comment(0x9EAB, "Check if input has abbreviation dot", inline=True)
comment(0x9EAD, "Is it a dot?", inline=True)
comment(0x9EAF, "No, try next command", inline=True)
comment(0x9EB1, "Skip past the dot", inline=True)
comment(0x9EB4, "Y=0: no chars matched at all?", inline=True)
comment(0x9EB5, "Yes, unknown command", inline=True)
comment(0x9EB7, "Check if next input char is alpha", inline=True)
comment(0x9EB9, "Mask to uppercase", inline=True)
comment(0x9EBB, "Below 'A'? Not alpha, command done", inline=True)
comment(0x9EBF, "Above 'Z'? Not alpha, command done", inline=True)
comment(0x9EC1, "Alpha: partial match, try next cmd", inline=True)
comment(0x9EC3, "Advance text pointer past matched chars", inline=True)
comment(0x9ECD, "Skip spaces after command", inline=True)
comment(0x9ED0, "Save text pointer for command handler", inline=True)
comment(0x9EDA, "Get dispatch address from table", inline=True)
comment(0x9EDD, "Push high byte", inline=True)
comment(0x9EDE, "Get dispatch low from table+1", inline=True)
comment(0x9EE1, "Push low byte", inline=True)
comment(0x9EE2, "RTS-dispatch to command handler", inline=True)

# *OPT handling within star_cmd dispatch area
# *OPT 1,n sets/clears verbose mode (bit 2 of zp_flags)
# *OPT 4,n sets boot option in FSM sector 1 byte 253
comment(0x9FDD, "Get *OPT first parameter", inline=True)
comment(0x9FDF, "Param=0: *OPT 0 (clear OPT1)", inline=True)
comment(0x9FE1, "Param-1: check for *OPT 1", inline=True)
comment(0x9FE2, "Not *OPT 1: check *OPT 4", inline=True)
comment(0x9FE4, "Param=1: check second parameter", inline=True)
comment(0x9FE5, "Second param=0: clear OPT1", inline=True)
comment(0x9FED, "Clear bit 2 (OPT1 verbose off)", inline=True)
comment(0x9FF1, "Store updated flags", inline=True)
comment(0x9FF3, "Save workspace and return", inline=True)
comment(0x9FF6, "Check for *OPT 4 (boot option)", inline=True)
comment(0x9FF8, "Not *OPT 4: bad opt error", inline=True)
comment(0xA000, "Get boot option value (second param)", inline=True)
comment(0xA002, "Mask to 2 bits (options 0-3)", inline=True)
comment(0xA004, "Store in FSM boot option byte", inline=True)
comment(0xA007, "Write directory and FSM to disc", inline=True)

# hd_init_detect (&9A63)
# Writes &5A then &A5 to SCSI data register and reads back.
# If either value doesn't survive, no SCSI hardware present.
comment(0x9A63, "Write &5A to SCSI data register", inline=True)
comment(0x9A65, "Check if value survived", inline=True)
comment(0x9A68, "No match: SCSI hardware not present", inline=True)
comment(0x9A6A, "Write complement &A5", inline=True)
comment(0x9A6C, "Write test value to SCSI data port", inline=True)
comment(0x9A6F, "X=0: clear IRQ enable register", inline=True)
comment(0x9A71, "Disable SCSI interrupts", inline=True)
comment(0x9A74, "Read back: does value match?", inline=True)

# get_wksp_addr_ba (&A70E)
comment(0xA70E, "Get our ROM number", inline=True)
comment(0xA710, "Read workspace page from ROM table", inline=True)
comment(0xA713, "Store as high byte of (&BA)", inline=True)
comment(0xA715, "Low byte = 0 (page-aligned)", inline=True)
comment(0xA717, "Store low byte", inline=True)

# xa_div_16_to_ya (&BFA2)
# Repeated subtraction: subtract 16 from A, increment Y each time.
# When A underflows, decrement X (high byte) and continue.
# Result: Y:A = quotient, with remainder lost.
comment(0xBFA2, "Set carry for subtraction", inline=True)
comment(0xBFA3, "Subtract 16", inline=True)
comment(0xBFA5, "Increment quotient", inline=True)
comment(0xBFA6, "No underflow, subtract again", inline=True)
comment(0xBFA8, "Underflow: borrow from high byte", inline=True)
comment(0xBFA9, "High byte >= 0, continue subtracting", inline=True)
comment(0xBFAB, "Add back the last 16 (remainder)", inline=True)

# check_set_channel_y (&ACFE)
# ADFS file handles are &30-&39 (channels 0-9).
# Subtracts &30 to get channel index, validates range,
# checks channel is actually open.
comment(0xACFE, "Save file handle", inline=True)
comment(0xAD00, "Store as current channel for errors", inline=True)
comment(0xAD03, "Handle >= &3A?", inline=True)
comment(0xAD05, "Yes, invalid handle", inline=True)
comment(0xAD07, "Transfer handle to A", inline=True)
comment(0xAD08, "Set carry for subtraction", inline=True)
comment(0xAD09, "Subtract &30 to get channel index", inline=True)
comment(0xAD0B, "Handle < &30? Invalid", inline=True)
comment(0xAD0D, "Store channel index offset", inline=True)
comment(0xAD0F, "Transfer to X for table lookup", inline=True)
comment(0xAD10, "Read channel flags", inline=True)
comment(0xAD13, "Zero = channel not open", inline=True)

# NMI patch variants: use move_id to disambiguate overlapping
# runtime addresses at &0D0A.
comment(0x0D0A, "Read byte from transfer address", inline=True, move_id=nmi_write_move_id)
comment(0x0D0D, "Write to WD1770 data register", inline=True, move_id=nmi_write_move_id)
comment(0x0D10, "Increment transfer address low", inline=True, move_id=nmi_write_move_id)
comment(0x0D13, "No page crossing: done", inline=True, move_id=nmi_write_move_id)
comment(0x0D15, "Increment transfer address high", inline=True, move_id=nmi_write_move_id)
comment(0x0D0A, "Read byte from Tube R3", inline=True, move_id=nmi_tube_write_move_id)
comment(0x0D0D, "Write to WD1770 data register", inline=True, move_id=nmi_tube_write_move_id)
comment(0x0D10, "Always branch: done", inline=True, move_id=nmi_tube_write_move_id)
comment(0x0D0A, "Read byte from WD1770", inline=True, move_id=nmi_tube_read_move_id)
comment(0x0D0D, "Write to Tube R3", inline=True, move_id=nmi_tube_read_move_id)
comment(0x0D10, "Always branch: done", inline=True, move_id=nmi_tube_read_move_id)

# floppy_get_step_rate (&BBB4)
# Reads OSBYTE &FF startup options, extracts bits 4-5 for
# disc drive step rate and head settle time.
no_automatic_comment(0xBBC4)
comment(0xBBB4, "Clear side select flag", inline=True)
comment(0xBBB9, "Clear FDC step rate command bits", inline=True)
comment(0xBBBC, "OSBYTE &FF: read startup options", inline=True)
comment(0xBBC0, "Y=&FF: read current value", inline=True)
comment(0xBBC4, "Get startup byte to A", inline=True)
comment(0xBBC5, "Save startup byte", inline=True)
comment(0xBBC6, "Test bit 5 (step rate high)", inline=True)
comment(0xBBC8, "Clear: fast step rate", inline=True)
comment(0xBBCA, "Bit 5 set: slow step (rate=3)", inline=True)
comment(0xBBCC, "Store in FDC command step field", inline=True)
comment(0xBBCF, "Restore startup byte", inline=True)
comment(0xBBD0, "Test bit 4 (settle time)", inline=True)
comment(0xBBD2, "Clear: short settle", inline=True)
comment(0xBBD4, "Bit 4 set: long settle (rate=2)", inline=True)
comment(0xBBD6, "Store in NMI workspace", inline=True)

# sub_cbbda - claim NMI for floppy operations (&BBDA)
label(0x877D, "advance_pattern_index")
label(0x8782, "check_pattern_exhausted")
label(0x8787, "check_hash_wildcard")
label(0x8798, "check_both_exhausted")
label(0x87A5, "check_trailing_star")
label(0x87A8, "begin_star_match")
label(0x87A9, "try_star_position_loop")
label(0x87C6, "no_match_cleanup_loop")
label(0x87C9, "discard_saved_positions")
label(0x87CB, "star_match_succeeded")
label(0x87CF, "check_name_ended")
label(0x87E7, "parse_pathname_entry")
label(0x87F0, "begin_dir_entry_search")
label(0x8809, "end_of_dir_entries")
label(0x8822, "parse_drive_from_ascii")
label(0x8836, "push_valid_drive")
label(0x8841, "restore_drive_digit")
label(0x8849, "bad_drive_name")
label(0x884C, "parse_filename_from_cmdline")
label(0x8851, "full_pathname_parser")
label(0x8869, "get_first_path_char")
label(0x8872, "advance_past_colon")
label(0x8875, "check_drive_initialised")
label(0x887E, "set_fsm_loading_flag")
label(0x8898, "copy_csd_to_root_loop")
label(0x88A1, "load_root_directory")
label(0x88C4, "check_root_specifier")
label(0x88D2, "check_special_dir_in_path")
label(0x88E5, "set_root_dir_entry")
label(0x88FF, "search_current_dir")
label(0x8905, "save_text_ptr_after_match")
label(0x8933, "scan_for_component_end")
label(0x8939, "check_if_dir_entry")
label(0x893B, "scan_component_chars_loop")
label(0x894D, "save_component_length")
label(0x8950, "check_access_is_dir_loop")
label(0x895B, "next_entry_not_found")
label(0x895E, "advance_dir_entry_ptr")
label(0x8969, "compare_next_dir_entry")
label(0x8975, "descend_into_subdir")
label(0x8982, "clean_dir_rename_bit")
label(0x8991, "advance_text_past_component")
label(0x899D, "check_alt_workspace_set")
label(0x89A6, "copy_csd_sector_after_descent")
label(0x89AF, "copy_disc_op_for_subdir")
label(0x89B1, "copy_subdir_template_loop")
label(0x89BE, "copy_subdir_sector_loop")
label(0x89D0, "get_object_type_result")
label(0x89D3, "save_wksp_and_return")
label(0x89EA, "check_alt_wksp_on_return")
label(0x89F4, "copy_alt_wksp_template_loop")
label(0x8A1D, "save_workspace_checksum")
label(0x8A27, "save_wksp_page_loop")
label(0x8A3D, "multi_sector_disc_command")
label(0x8A45, "check_disc_command_type")
label(0x8A63, "exec_disc_transfer_batched")
label(0x8A6C, "single_sector_read")
label(0x8A8C, "calc_partial_start_sector")
label(0x8A9F, "calc_partial_end_sector")
label(0x8AB2, "exec_partial_sector_op")
label(0x8AB7, "partial_sector_complete")
label(0x8AC4, "read_256_via_hd")
label(0x8ACA, "load_sector_check_result")
label(0x8AE1, "calc_multi_sector_count")
label(0x8AF5, "copy_sector_to_transfer")
label(0x8AFB, "copy_sector_count_loop")
label(0x8B04, "set_transfer_length")
label(0x8B61, "check_partial_sector_needed")
label(0x8B64, "setup_partial_sector_buffer")
label(0x8B74, "copy_partial_sector_loop")
label(0x8B90, "complete_partial_write")
label(0x8B97, "copy_write_data_loop")
label(0x8BAA, "check_write_or_read")
label(0x8BAC, "partial_write_to_disc")
label(0x8BAD, "partial_read_from_disc")
label(0x8BB0, "execute_partial_disc_op")
label(0x8BB3, "search_for_file")
label(0x8BBA, "copy_partial_read_loop")
label(0x8BBF, "complete_partial_op")
label(0x8BC5, "check_partial_sectors_done")
label(0x8BC8, "not_found_error")
label(0x8BD0, "check_locked_loop")
label(0x8BD3, "file_is_locked_error")
label(0x8BD7, "bad_parms_error")
label(0x8BE5, "find_file_and_validate")
label(0x8BF0, "validate_found_entry")
label(0x8C10, "create_new_dir_entry")
label(0x8C17, "clear_osfile_block_loop")
label(0x8C23, "allocate_space_for_file")
label(0x8C27, "copy_alloc_sector_loop")
label(0x8C30, "write_dir_entry")
label(0x8C43, "copy_name_byte_loop")
label(0x8C50, "set_access_bits_loop")
label(0x8C5C, "store_length_and_sector")
label(0x8C62, "search_dir_for_file")
label(0x8C65, "search_dir_with_wildcards")
label(0x8C69, "scan_dir_entries_loop")
label(0x8C76, "compare_entry_names_loop")
label(0x8C86, "extract_entry_access_loop")
label(0x8CA8, "osfile_save_handler")
label(0x8CC3, "check_existing_for_save")
label(0x8CC6, "delete_existing_before_save")
label(0x8CC9, "parse_osfile_and_search")
label(0x8CE2, "build_osfile_control_block")
label(0x8CE9, "copy_osfile_addrs")
label(0x8CEE, "check_4byte_addrs")
label(0x8CF0, "copy_3byte_addrs_loop")
label(0x8CF6, "mark_entry_dirty")
label(0x8CF9, "copy_4byte_addrs_loop")
label(0x8D04, "update_entry_from_osfile")
label(0x8D07, "write_entry_metadata")
label(0x8D10, "check_file_not_open")
label(0x8D23, "check_open_channel_loop")
label(0x8D53, "channel_on_same_drive")
label(0x8D69, "no_open_files_on_drive")
label(0x8D6E, "set_up_directory_search")
label(0x8D7A, "begin_pathname_scan")
label(0x8D7F, "scan_name_bytes_loop")
label(0x8D8D, "skip_dot_in_path")
label(0x8D93, "scan_name_alpha_loop")
label(0x8D9E, "check_bad_name_char")
label(0x8DA4, "check_special_chars_loop")
label(0x8DB2, "valid_name_continue_loop")
label(0x8DBD, "set_up_gsinit_path")
label(0x8DC0, "gsinit_scan_loop")
label(0x8DD6, "check_path_terminator")
label(0x8DDB, "bad_name_in_path")
label(0x8DDE, "wild_cards_error")
label(0x8DF3, "copy_addrs_and_find_empty_entry")
label(0x8DF6, "search_dir_for_new_entry")
label(0x8E00, "scan_entry_bytes_loop")
label(0x8E0F, "find_empty_entry_loop")
label(0x8E19, "no_empty_entry_found")
label(0x8E2B, "check_name_already_exists")
label(0x8E43, "compare_names_loop")
label(0x8E49, "copy_entry_data_loop")
label(0x8E59, "write_entry_to_dir")
label(0x8E5F, "mark_entry_created")
label(0x8E64, "mark_directory_modified")
label(0x8E6F, "allocate_disc_space_for_file")
label(0x8E71, "copy_alloc_request_loop")
label(0x8E7D, "store_allocated_sector")
label(0x8E7F, "check_exact_alloc")
label(0x8E85, "reduce_alloc_to_available")
label(0x8E8B, "copy_entry_from_template")
label(0x8E8D, "copy_name_to_entry_loop")
label(0x8E9A, "copy_access_byte_loop")
label(0x8EA8, "store_entry_lengths_loop")
label(0x8EB8, "store_entry_3byte_sector")
label(0x8EC0, "store_entry_4byte_sector")
label(0x8EDC, "update_entry_access")
label(0x8EED, "copy_osfile_to_entry_loop")
label(0x8F01, "copy_load_addr_loop")
label(0x8F1B, "copy_exec_addr_to_entry_loop")
label(0x8F2D, "check_if_updating_length")
label(0x8F3D, "update_length_and_access")
label(0x8F4C, "validate_not_locked")
label(0x8F52, "write_entry_sector_info")
label(0x8F58, "copy_length_to_entry")
label(0x8F5C, "copy_3byte_length_loop")
label(0x8F69, "copy_sector_to_entry_loop")
label(0x8F74, "osfile_load_handler")
label(0x8F7D, "osfile_read_cat_info")
label(0x8F80, "search_for_osfile_target")
label(0x8F86, "write_dir_and_validate")
label(0x8F8E, "copy_dir_write_template_loop")
label(0x8FDF, "find_first_matching_entry")
label(0x8FEA, "validate_fsm_checksums")
label(0x8FFA, "bad_fs_map_error")
label(0x9009, "validate_fsm_entries")
label(0x9010, "check_fsm_entry_loop")
label(0x902C, "check_fsm_ordering")
label(0x902F, "add_entry_size_loop")
label(0x903E, "compare_with_next_entry_loop")
label(0x904C, "discard_comparison_bytes")
label(0x905C, "calc_fsm_checksums")
label(0x9060, "checksum_s0_loop")
label(0x906A, "checksum_s1_loop")
label(0x907C, "osfile_write_load_addr")
label(0x9087, "osfile_write_load_search")
label(0x9092, "copy_load_to_entry_loop")
label(0x909F, "copy_exec_to_entry_loop")
label(0x90AF, "update_entry_after_write")
label(0x90B3, "update_cat_info_loop")
label(0x90C0, "copy_cat_info_to_entry_loop")
label(0x90CF, "set_entry_access_from_osfile")
label(0x90E2, "apply_access_bits_loop")
label(0x90E9, "access_bit_clear")
label(0x90EB, "advance_access_bit")
label(0x90FB, "check_dir_access_bit")
label(0x9101, "osfile_delete_handler")
label(0x911E, "search_and_delete_entry")
label(0x9128, "check_and_delete_found")
label(0x9133, "save_csd_for_dir_check_loop")
label(0x9150, "restore_csd_after_check_loop")
label(0x916E, "proceed_with_delete")
label(0x9176, "copy_locked_name_loop")
label(0x9185, "check_locked_attr_loop")
label(0x91A0, "file_is_locked")
label(0x91A2, "copy_entry_name_to_wksp_loop")
label(0x91C2, "release_entry_space")
label(0x91CC, "remove_entry_shift_loop")
label(0x91F0, "update_dir_sequence")
label(0x91FA, "copy_entry_up_loop")
label(0x9212, "write_dir_and_release")
label(0x921B, "check_csd_deleted")
label(0x921F, "check_lib_deleted")
label(0x9229, "check_prev_dir_deleted")
label(0x927B, "setup_help_param_ptr")
label(0x9287, "print_padded_name")
label(0x9289, "print_name_char_loop")
label(0x9299, "pad_with_spaces")
label(0x92A8, "print_char_loop")
label(0x92B2, "last_char_reached")
label(0x92C4, "print_via_osasci")
label(0x92DE, "print_entry_name_and_access")
label(0x92EA, "print_entry_char_loop")
label(0x92F6, "print_access_space")
label(0x92F9, "print_access_chars_loop")
label(0x9302, "print_access_done")
label(0x931B, "print_hex_byte")
label(0x9324, "print_hex_nibble")
label(0x932A, "verify_dir_and_list")
label(0x93C5, "print_catalogue_header")
label(0x93CE, "print_catalogue_entries")
label(0x93D4, "print_cat_header_and_entries")
label(0x93DC, "print_cat_entry_loop")
label(0x93F5, "advance_cat_entry")
label(0x93F8, "print_cat_pair")
label(0x9405, "print_cat_pair_second")
label(0x9419, "print_cat_newline")
label(0x941C, "print_cat_done")
label(0x9436, "load_dir_and_list_entries")
label(0x9439, "print_next_entry_loop")
label(0x9463, "check_at_sign")
label(0x946F, "set_matched_flag")
label(0x947F, "parse_path_and_load")
label(0x9484, "search_for_dir_entry")
label(0x948F, "path_not_found")
label(0x9492, "check_special_dir")
label(0x9497, "prepare_dir_read")
label(0x949F, "copy_csd_sector_to_wksp")
label(0x94A8, "copy_disc_op_template")
label(0x94AA, "copy_template_loop")
label(0x94B7, "copy_entry_sector_loop")
label(0x94EF, "print_info_loop")
label(0x951B, "print_entry_field_loop")
label(0x9524, "check_field_boundary")
label(0x9536, "next_entry_byte")
label(0x953C, "print_newline_return")
label(0x9544, "copy_dir_name_loop")
label(0x9557, "store_csd_drive")
label(0x955C, "copy_csd_sector_loop")
label(0x9579, "check_dir_exists_loop")
label(0x95A4, "already_exists_error2")
label(0x95B7, "cdir_name_validated")
label(0x95C3, "check_root_or_special")
label(0x95C5, "not_root_or_special")
label(0x95CF, "copy_cdir_sector_loop")
label(0x95E5, "copy_dir_template_loop")
label(0x95F9, "init_dir_identity_loop")
label(0x960D, "zero_dir_entries_loop")
label(0x9619, "write_new_dir_to_disc")
label(0x961B, "set_dir_parent_sector")
label(0x9642, "copy_sectors_between_dirs")
label(0x964E, "read_source_sector")
label(0x9650, "copy_sector_data_loop")
label(0x965D, "write_dest_sector")
label(0x9666, "advance_sector_ptrs")
label(0x9670, "copy_remaining_loop")
label(0x967D, "advance_dest_sector")
label(0x9686, "advance_source_sector")
label(0x9690, "copy_dir_name_to_entry")
label(0x969D, "set_entry_dir_attribute")
label(0x96A6, "execute_sector_copy")
label(0x96B2, "check_tube_for_copy")
label(0x96BE, "read_source_to_buffer")
label(0x96CE, "write_buffer_to_dest")
label(0x96D1, "advance_copy_sector")
label(0x96E6, "copy_sectors_remaining")
label(0x970B, "set_transfer_address")
label(0x9766, "check_format_parameters")
label(0x977A, "validate_sector_count")
label(0x977D, "validate_disc_size")
label(0x9784, "begin_format_operation")
label(0x97A8, "format_init_dir")
label(0x97B3, "format_init_fsm")
label(0x97C1, "init_fsm_zeros_loop")
label(0x97D7, "init_fsm_total_sectors")
label(0x97DC, "init_fsm_sector_loop")
label(0x97EC, "write_fsm_to_disc_loop")
label(0x97FB, "create_root_dir")
label(0x980C, "init_root_dir_entries")
label(0x9819, "init_root_dir_name")
label(0x9823, "fill_root_name_loop")
label(0x9830, "set_root_identity_loop")
label(0x9838, "write_root_dir_to_disc")
label(0x983F, "write_root_sectors_loop")
label(0x984C, "set_root_as_csd")
label(0x9851, "copy_root_sector_loop")
label(0x985B, "init_workspace_for_root")
label(0x9869, "set_format_drive")
label(0x986C, "format_next_track_loop")
label(0x987B, "format_write_sectors_loop")
label(0x989C, "verify_formatted_sectors")
label(0x98AE, "calculate_total_sectors")
label(0x98C9, "prepare_cdir_directory")
label(0x98CE, "init_cdir_entries_loop")
label(0x98DD, "setup_cdir_dir_entry")
label(0x9903, "copy_name_to_cdir_loop")
label(0x990E, "set_cdir_parent_sector")
label(0x992B, "write_cdir_directory")
label(0x9938, "finalise_cdir")
label(0x9945, "clear_rwl_attributes")
label(0x9947, "clear_attr_bits_loop")
label(0x9951, "set_file_attributes")
label(0x9965, "save_e_attribute_state")
label(0x996A, "skip_filename_loop")
label(0x9979, "skip_spaces_before_attrs")
label(0x9985, "skip_space_or_quote")
label(0x9988, "parse_attr_char")
label(0x99A5, "check_rwl_char")
label(0x99A7, "match_rwl_loop")
label(0x99B4, "check_attr_terminator")
label(0x99B8, "next_attr_char")
label(0x99BB, "display_and_find_next")
label(0x99C9, "set_rwl_attribute_bit")
label(0x99D7, "print_aborted_error")
label(0x9A0C, "confirm_destroy_loop")
label(0x9A16, "check_confirm_response")
label(0x9A27, "delete_matching_files_loop")
label(0x9A3E, "all_files_deleted")
label(0x9A6C, "scsi_write_read_test")
label(0x9AB0, "check_workspace_claimed")
label(0x9AB9, "dispatch_service_call")
label(0x9AE6, "adfs_hardware_found")
label(0x9AFF, "copy_default_workspace_loop")
label(0x9B08, "check_workspace_initialised")
label(0x9B10, "verify_workspace_checksum")
label(0x9B22, "claim_filing_system")
label(0x9B38, "select_adfs_filing_system")
label(0x9B57, "check_boot_option")
label(0x9B6B, "check_boot_key")
label(0x9B6E, "boot_shift_pressed")
label(0x9B87, "boot_run_option")
label(0x9B9C, "copy_boot_command_loop")
label(0x9BB2, "copy_csd_name_loop")
label(0x9BBB, "set_default_csd")
label(0x9BE4, "restore_boot_workspace_loop")
label(0x9C06, "boot_load_from_disc")
label(0x9C12, "boot_set_page")
label(0x9C14, "copy_workspace_to_save_loop")
label(0x9C48, "copy_drive_info_loop")
label(0x9C55, "set_workspace_drive")
label(0x9C59, "init_channel_flags_loop")
label(0x9C6A, "init_per_channel_loop")
label(0x9C74, "init_channel_complete")
label(0x9C77, "set_fsm_load_flag")
label(0x9C85, "load_fsm_for_boot")
label(0x9C97, "clear_fsm_flag_after_load")
label(0x9CA4, "set_default_dir_for_boot")
stringcr(0x9CAB)
comment(0x9CAB, '":0.LIB*" + CR: default library path', inline=True)
label(0x9CEC, "check_adfs_prefix")
label(0x9CEE, "match_command_loop")
label(0x9CFF, "service4_not_matched")
label(0x9D11, "service4_decline")
label(0x9D35, "match_osword_block_loop")
label(0x9D46, "copy_disc_op_params_loop")
label(0x9D52, "execute_osword_disc_op")
label(0x9D57, "store_osword_result")
label(0x9D5F, "copy_result_sector_loop")
label(0x9D63, "set_result_error_code")
label(0x9D6A, "store_result_byte")
label(0x9D71, "check_transfer_complete")
label(0x9D77, "copy_transfer_count_loop")
label(0x9D81, "adjust_partial_transfer")
label(0x9D94, "store_adjusted_count")
label(0x9D9D, "copy_adjusted_bytes_loop")
label(0x9DD2, "check_help_adfs_keyword")
label(0x9DDA, "print_help_command_list")
label(0x9DE5, "print_next_command")
label(0x9DEA, "output_command_name_loop")
label(0x9DEF, "end_of_command_name")
label(0x9DF1, "pad_command_name_loop")
label(0x9E08, "check_more_commands")
label(0x9E0D, "print_help_data_commands")
label(0x9E19, "print_data_cmd_name_loop")
label(0x9E25, "end_of_data_command")
label(0x9E8F, "next_command_entry")
label(0x9E93, "match_command_char")
label(0x9EA5, "skip_to_end_of_name")
label(0x9EB4, "end_of_table_name")
label(0x9EC3, "advance_past_command")
label(0x9ECD, "skip_spaces_before_args")
label(0x9EDA, "dispatch_command")
label(0x9FED, "clear_opt1_verbose")
label(0x9FF1, "store_opt_flags")
label(0x9FF6, "check_opt4_boot")
label(0xA00A, "bad_opt_error")
label(0xA016, "print_space")
label(0xA031, "print_used_space")
label(0xA061, "print_map_header")
label(0xA06D, "print_fsm_entries_loop")
label(0xA083, "print_entry_hex_loop")
label(0xA0CE, "close_all_drives_start")
label(0xA0D3, "close_each_drive_loop")
label(0xA0FF, "store_default_drive")
label(0xA116, "close_drive_channels_loop")
label(0xA12F, "check_csd_on_drive")
label(0xA14B, "copy_default_name_loop")
label(0xA161, "mount_drive_setup")
label(0xA179, "mount_read_root_dir")
label(0xA189, "mount_set_boot_option")
label(0xA1AE, "clear_accumulators_loop")
label(0xA1BC, "copy_result_loop")
label(0xA1EF, "clear_bcd_digits_loop")
label(0xA1F5, "shift_binary_bit")
label(0xA205, "dabble_digit_loop")
label(0xA20F, "store_bcd_digit")
label(0xA21F, "print_digit_loop")
label(0xA223, "check_leading_zero")
label(0xA230, "print_nonzero_digit")
label(0xA235, "output_digit_char")
label(0xA240, "print_comma_separator")
label(0xA244, "next_digit")
label(0xA25D, "copy_title_loop")
label(0xA269, "pad_title_with_cr")
label(0xA26B, "store_title_char")
label(0xA29B, "bad_compact_error")
label(0xA2AB, "parse_compact_start_page")
label(0xA2BF, "skip_separator_spaces")
label(0xA2DF, "skip_trailing_spaces")
label(0xA2EA, "convert_hex_digits_loop")
label(0xA2FD, "check_hex_af")
label(0xA30C, "store_converted_byte")
label(0xA31F, "check_hex_digit_valid")
label(0xA322, "convert_two_digits")
label(0xA334, "combine_hex_nibbles")
label(0xA344, "begin_compaction")
label(0xA35A, "combine_hex_digit_pair")
label(0xA365, "parse_second_filename")
label(0xA386, "restore_csd_and_error")
label(0xA389, "bad_command_error")
label(0xA3BC, "search_lib_for_command")
label(0xA3CC, "copy_run_params_loop")
label(0xA3E9, "execute_loaded_file")
label(0xA401, "run_tube_transfer")
label(0xA41E, "run_set_exec_addr")
label(0xA42F, "copy_exec_addr_loop")
label(0xA434, "run_jump_to_file")
label(0xA449, "copy_lib_name_loop")
label(0xA454, "copy_lib_sector_loop")
label(0xA45D, "save_workspace_and_return")
label(0xA462, "swap_csd_to_lib_loop")
label(0xA475, "restore_csd_sector_loop")
label(0xA499, "swap_dir_sectors_loop")
label(0xA4AD, "copy_prev_dir_name_loop")
label(0xA4B9, "scan_filename_loop")
label(0xA4BE, "advance_past_char")
label(0xA4C1, "check_dot_separator")
label(0xA4D3, "scan_spaces_loop")
label(0xA4E5, "enter_quoted_string")
label(0xA4E7, "advance_and_continue")
label(0xA4EA, "end_of_spaces")
label(0xA500, "parse_drive_specifier")
label(0xA517, "source_is_found")
label(0xA534, "scan_dest_for_parent_ref")
label(0xA53D, "advance_dest_scan")
label(0xA540, "check_dot_in_dest")
label(0xA544, "parse_destination_name")
label(0xA560, "save_dest_dir_info_loop")
label(0xA569, "check_alt_workspace")
label(0xA570, "restore_csd_sector_loop2")
label(0xA579, "reload_and_parse_source")
label(0xA590, "compare_src_dest_dir_loop")
label(0xA5A4, "find_last_path_component")
label(0xA5A6, "scan_component_chars")
label(0xA5B5, "advance_past_component")
label(0xA5C0, "copy_new_name_to_entry")
label(0xA5C2, "merge_name_attributes_loop")
label(0xA5D5, "pad_with_cr")
label(0xA5D7, "store_merged_name_byte")
label(0xA5E8, "already_exists_error")
label(0xA5EB, "cross_dir_rename")
label(0xA5FF, "copy_entry_metadata_loop")
label(0xA618, "copy_entry_sector_loop2")
label(0xA623, "build_access_byte_loop")
label(0xA635, "copy_start_sector_loop")
label(0xA651, "restore_attributes_loop")
label(0xA679, "clear_sector_workspace_loop")
label(0xA685, "update_moved_dir_parent")
label(0xA68C, "update_parent_sector")
label(0xA68E, "copy_parent_sector_loop")
label(0xA699, "copy_dir_name_from_entry")
label(0xA6B0, "write_dir_name_loop")
label(0xA6BB, "write_parent_sector_loop")
label(0xA6E6, "compare_hugo_loop")
label(0xA6F9, "broken_directory_error")
label(0xA721, "sum_workspace_loop")
label(0xA738, "bad_checksum_error")
label(0xA749, "save_workspace_state")
label(0xA75A, "save_wksp_byte_loop")
label(0xA767, "save_wksp_and_checksum")
label(0xA77C, "restore_workspace_state")
label(0xA797, "restore_wksp_from_save")
label(0xA79B, "restore_wksp_byte_loop")
label(0xA7A2, "load_dir_for_drive")
label(0xA7C0, "setup_disc_read_for_dir")
label(0xA7D6, "copy_disc_op_template_loop")
label(0xA7E1, "copy_dir_sector_loop")
label(0xA7EE, "read_dir_from_disc")
label(0xA7F5, "setup_fsm_read")
label(0xA7F7, "copy_fsm_template_loop")
label(0xA802, "copy_fsm_sector_loop")
label(0xA80F, "read_fsm_from_disc")
label(0xA837, "source_file_found")
label(0xA84D, "save_source_dir_sector_loop")
label(0xA85B, "copy_csd_for_dest_loop")
label(0xA867, "check_dest_terminator")
label(0xA86F, "load_dest_directory")
label(0xA877, "save_dest_dir_sector_loop")
label(0xA883, "scan_source_entries_loop")
label(0xA88C, "skip_dir_entry_or_done")
label(0xA894, "copy_file_entry")
label(0xA8BB, "copy_osfile_params_loop")
label(0xA8CA, "copy_source_name_loop")
label(0xA8E7, "copy_sector_addresses_loop")
label(0xA95F, "osargs_general_query")
label(0xA976, "return_success")
label(0xA97C, "flush_all_channels")
label(0xA97E, "flush_channels_loop")
label(0xA995, "osargs_file_specific")
label(0xA998, "set_channel_and_dispatch")
label(0xA9BD, "return_after_flag_update")
label(0xA9C7, "check_write_ptr")
label(0xA9CF, "copy_new_ptr_from_user")
label(0xAA03, "not_open_for_update")
label(0xAA35, "check_read_allocation")
label(0xAA46, "check_write_ext")
label(0xAA5F, "read_allocation_size")
label(0xAA62, "read_ext_value")
label(0xAA6F, "write_new_ext")
label(0xAAA6, "validate_and_set_ptr")
label(0xAAA8, "copy_ptr_to_channel_loop")
label(0xAABD, "set_ptr_complete")
label(0xAAF0, "calc_channel_buffer_page")
label(0xAAF3, "flush_dirty_channel_buffer")
label(0xAB3D, "write_dirty_sector_to_disc")
label(0xAB63, "scsi_write_page")
label(0xAB75, "write_buffer_to_scsi_loop")
label(0xAB87, "advance_write_page")
label(0xAB8A, "write_complete")
label(0xABA5, "ensure_channel_buffer")
label(0xABC9, "calc_buffer_address")
label(0xABD8, "find_buffer_for_sector")
label(0xABDE, "scan_channel_buffers")
label(0xABE8, "buffer_sector_match")
label(0xAC08, "allocate_new_buffer_slot")
label(0xAC1F, "find_free_slot_loop")
label(0xAC2B, "use_free_slot")
label(0xAC3B, "evict_oldest_buffer")
label(0xAC45, "evict_check_dirty")
label(0xAC5F, "load_sector_to_buffer")
label(0xAC62, "read_single_hd_sector")
label(0xAC6B, "wait_read_data_phase")
label(0xAC99, "read_scsi_to_buffer_loop")
label(0xACA6, "advance_read_page")
label(0xACAB, "read_hd_256_complete")
label(0xACBE, "read_complete_check")
label(0xACC6, "store_read_result")
label(0xACCB, "check_read_error")
label(0xACD7, "calc_buffer_page_from_offset")
label(0xACD9, "step_channel_offset_loop")
label(0xACE9, "step_ensure_offset_loop")
label(0xACF5, "convert_handle_to_offset")
label(0xAD3A, "check_eof_for_handle")
label(0xAD4B, "return_eof_status")
label(0xAD50, "return_eof_result")
label(0xAD53, "eof_error")
label(0xAD8D, "calc_bget_sector_addr")
label(0xADC5, "switch_to_channel_drive")
label(0xADC7, "save_csd_sector_loop")
label(0xADF7, "restore_csd_after_switch_loop")
label(0xAE29, "search_dir_for_channel")
label(0xAE35, "compare_entry_sequence")
label(0xAE3F, "compare_entry_sector_loop")
label(0xAE4C, "advance_to_next_dir_entry")
label(0xAE59, "check_ptr_within_allocation")
label(0xAE5E, "extend_file_if_needed")
label(0xAE66, "save_csd_for_extend_loop")
label(0xAE97, "check_alloc_vs_ptr")
label(0xAEB9, "handle_eof_write")
label(0xAEBC, "update_ext_to_ptr")
label(0xAEC1, "extend_file_allocation")
label(0xAED7, "switch_drive_for_extend")
label(0xAF66, "copy_old_sector_info_loop")
label(0xAF75, "check_relocation_needed")
label(0xAF87, "skip_zero_fill")
label(0xAF8F, "calc_zero_fill_start")
label(0xAFB9, "zero_fill_sector_loop")
label(0xAFEC, "check_sector_low")
label(0xAFEF, "check_sector_mid")
label(0xAFF2, "decrement_fill_sector")
label(0xB00D, "write_zero_sector")
label(0xB01D, "advance_fill_sector")
label(0xB025, "zero_entire_sector_loop")
label(0xB02A, "mark_buffer_dirty")
label(0xB050, "advance_channel_sector")
label(0xB060, "update_ext_from_new_ptr")
label(0xB07D, "restore_drive_after_extend")
label(0xB085, "restore_csd_after_extend_loop")
label(0xB09D, "not_open_for_update_error")
label(0xB0B5, "check_buffer_state")
label(0xB0F0, "calc_buffer_sector_addr")
label(0xB123, "increment_ptr_after_write")
label(0xB132, "increment_ptr_mid_bytes")
label(0xB13F, "update_channel_flags_for_ptr")
label(0xB164, "check_ext_vs_allocation")
label(0xB17C, "set_buffer_flush_flag")
label(0xB181, "set_buffer_dirty_and_flush")
label(0xB184, "apply_writable_mask")
label(0xB188, "store_channel_flags")
label(0xB18C, "sync_ext_to_ptr")
label(0xB1AE, "recalc_flags_from_base")
label(0xB1D4, "find_empty_channel_slot")
label(0xB1E1, "store_exec_handle")
label(0xB1E3, "scan_channels_loop")
label(0xB203, "open_for_read_channel")
label(0xB20E, "search_for_input_file")
label(0xB218, "check_read_conflicts")
label(0xB21A, "check_open_conflict_loop")
label(0xB24D, "next_conflict_check")
label(0xB259, "copy_ext_from_entry")
label(0xB274, "copy_allocation_from_entry")
label(0xB2D9, "save_and_return_handle")
label(0xB2E1, "check_random_access_mode")
label(0xB2F8, "check_random_access_attr")
label(0xB2FB, "open_for_random_access")
label(0xB2FE, "open_for_output_new")
label(0xB312, "clear_new_file_osfile")
label(0xB316, "clear_osfile_block_loop2")
label(0xB321, "find_best_free_space_loop")
label(0xB332, "store_default_allocation")
label(0xB341, "set_ffffffff_load_addr")
label(0xB370, "set_ext_zero_for_new")
label(0xB383, "close_file_handler")
label(0xB393, "close_all_scan_loop")
label(0xB398, "close_next_channel_loop")
label(0xB3A4, "close_single_channel")
label(0xB3B3, "close_all_complete")
label(0xB3B6, "close_and_update_dir")
label(0xB3E4, "close_read_only")
label(0xB3F1, "update_dir_entry_on_close")
label(0xB446, "update_entry_length")
label(0xB468, "check_channels_on_drive")
label(0xB46A, "scan_drive_channels_loop")
label(0xB479, "no_channels_on_drive")
label(0xB47C, "check_disc_changed")
label(0xB48E, "read_clock_then_verify_disc_id")
label(0xB491, "verify_disc_id_unchanged")
label(0xB4AE, "raise_disc_changed_error")
label(0xB4BF, "read_clock_for_timing")
label(0xB4CD, "compare_clock_bytes_loop")
label(0xB4F1, "disc_probably_changed")
label(0xB4F5, "check_drive_and_reload_fsm")
label(0xB510, "get_drive_bit_mask")
label(0xB513, "shift_drive_mask_loop")
label(0xB51C, "set_drive_from_channel")
label(0xB54E, "save_and_restore_drive")
label(0xB567, "reload_fsm_for_drive")
label(0xB574, "restore_saved_drive")
label(0xB579, "convert_drive_to_slot")
label(0xB590, "copy_data_addr_loop")
label(0xB5A4, "dispatch_dir_operations")
label(0xB5C8, "get_function_and_set_ptr")
label(0xB5D3, "copy_new_ptr_loop")
label(0xB5DD, "set_ptr_from_temp")
label(0xB5E9, "calc_end_position_loop")
label(0xB602, "store_new_ptr_in_channel")
label(0xB630, "save_byte_count_for_write")
label(0xB634, "save_and_clear_count_loop")
label(0xB644, "compare_ext_with_ptr")
label(0xB678, "reduce_count_to_available_loop")
label(0xB6B4, "setup_disc_transfer")
label(0xB6B9, "update_control_block_addr_loop")
label(0xB6CB, "calc_disc_sector_for_channel")
label(0xB6FD, "compare_buffer_sector_loop")
label(0xB710, "save_and_flush_after_transfer")
label(0xB716, "prepare_osgbpb_return")
label(0xB720, "handle_buffer_mismatch")
label(0xB742, "adjust_remaining_count")
label(0xB750, "propagate_borrow_loop")
label(0xB75D, "check_full_sectors_remain")
label(0xB76B, "setup_disc_op_block")
label(0xB772, "copy_data_addr_to_disc_op_loop")
label(0xB7A7, "save_csd_state_loop")
label(0xB7BF, "add_sector_count_loop")
label(0xB7E3, "check_remaining_buffered")
label(0xB7EB, "calc_remaining_sector")
label(0xB825, "setup_osgbpb_output_buffer")
label(0xB837, "claim_tube_for_output")
label(0xB84C, "setup_output_pointer")
label(0xB85B, "output_byte_to_buffer")
label(0xB863, "output_byte_direct")
label(0xB86F, "restore_caller_y")
label(0xB872, "output_dir_entry_name")
label(0xB87C, "output_name_char_loop")
label(0xB889, "output_printable_char")
label(0xB890, "dispatch_dir_info_handler")
label(0xB8A1, "read_dir_title_handler")
label(0xB8A6, "scan_title_length_loop")
label(0xB8B4, "output_title_length")
label(0xB8BA, "output_title_chars_loop")
label(0xB8CB, "output_boot_and_drive")
label(0xB8DB, "release_tube_and_return")
label(0xB8E1, "read_csd_name_handler")
label(0xB8FC, "drive_to_ascii_digit")
label(0xB905, "read_lib_name_handler")
label(0xB920, "read_filenames_handler")
label(0xB945, "skip_to_start_entry")
label(0xB950, "set_entry_pointer")
label(0xB954, "output_entries_loop")
label(0xB96B, "advance_entry_index")
label(0xB971, "store_remaining_count")
label(0xB980, "transfer_sector_bytes")
label(0xB989, "claim_tube_for_sector")
label(0xB99D, "set_tube_transfer_flag")
label(0xB9B5, "setup_buffer_pointers")
label(0xB9CF, "copy_byte_loop")
label(0xB9DC, "write_byte_from_memory")
label(0xB9E2, "tube_byte_transfer")
label(0xB9EE, "read_byte_from_tube")
label(0xB9F3, "advance_byte_position")
label(0xBA0C, "mark_partial_transfer")
label(0xBA2C, "store_direction_flag")
label(0xBA4D, "set_buffer_addr_for_read")
label(0xBA57, "get_sector_count")
label(0xBA5F, "check_drive_number")
label(0xBA63, "set_drive_1_select")
label(0xBA72, "check_format_command")
label(0xBA74, "set_read_write_command")
label(0xBA9B, "set_fdc_control_byte")
label(0xBAB0, "set_track_and_sector")
label(0xBABA, "seek_to_track_0")
label(0xBABD, "setup_nmi_for_transfer")
label(0xBAC6, "setup_fdc_and_seek")
label(0xBAF1, "check_floppy_error_code")
label(0xBAF4, "retry_after_error")
label(0xBB06, "return_floppy_result")
label(0xBB5F, "check_host_memory")
label(0xBB63, "check_tube_present")
label(0xBB6A, "validate_disc_command")
label(0xBB82, "set_read_transfer_mode")
label(0xBB89, "setup_nmi_and_step_rate")
label(0xBB92, "claim_nmi_and_init")
label(0xBBCF, "step_rate_fast")
label(0xBBDA, "claim_nmi")
subroutine(0xBBDA, "claim_nmi",
    title="Claim NMI via service call 12",
    description="""\
Issue service call 12 (NMI claim) via OSBYTE &8F to claim
exclusive use of the NMI handler for floppy disc operations.
Saves the return argument for later release.
""")
comment(0xBBDA, "OSBYTE &8F: issue service request", inline=True)
comment(0xBBDC, "X=&0C: service 12 (NMI claim)", inline=True)
comment(0xBBE0, "Issue service call", inline=True)
comment(0xBBE3, "Save NMI owner for release", inline=True)

# sub_cbbe7 - release NMI (&BBE7)
label(0xBBE7, "release_nmi")
subroutine(0xBBE7, "release_nmi",
    title="Release NMI via service call 11",
    description="""\
Issue service call 11 (NMI released) via OSBYTE &8F to
release the NMI handler after floppy disc operations.
""")
comment(0xBBE7, "Retrieve NMI owner", inline=True)
comment(0xBBEA, "OSBYTE &8F: issue service request", inline=True)
comment(0xBBEC, "X=&0B: service 11 (NMI released)", inline=True)
comment(0xBBEE, "Issue service call", inline=True)

# floppy_command (&BB14)
# Main entry point for floppy disc operations. Saves the stack
# for error recovery, sets up the control block, then dispatches
# to the appropriate read/write/format handler.
comment(0xBB14, "Save stack pointer for error recovery", inline=True)
comment(0xBB18, "Set transfer mode flags", inline=True)
comment(0xBB1D, "Set up NMI handler and drive select", inline=True)
comment(0xBB20, "Execute the read/write operation", inline=True)
comment(0xBB23, "Error: jump to floppy error handler", inline=True)
comment(0xBB25, "Partial sector buffer: save count", inline=True)
comment(0xBB28, "Save stack for error recovery", inline=True)
comment(0xBB2E, "Point (&B0) to workspace control blk", inline=True)
comment(0xBB34, "Clear transfer mode flags", inline=True)
comment(0xBB39, "Set up NMI handler", inline=True)
comment(0xBB3C, "Execute format track operation", inline=True)
comment(0xBB3F, "Process result/error", inline=True)

# sub_cbb42 - initialise floppy transfer
label(0xBB42, "floppy_init_transfer")
subroutine(0xBB42, "floppy_init_transfer",
    title="Initialise floppy disc transfer",
    description="""\
Set up for a floppy disc operation: clear error number,
copy the transfer address and control parameters from
the control block, claim NMI, set step rate, and copy
the NMI handler code to NMI workspace.
""")
comment(0xBB42, "Clear error number", inline=True)
comment(0xBB47, "Y=1: get transfer address from blk", inline=True)
comment(0xBB49, "Transfer address low", inline=True)
comment(0xBB4E, "Transfer address high", inline=True)

# floppy_check_present (&BA11)
# Writes &5A to the WD1770 track register and reads it back.
# If it matches, the 1770 is present. Also checks drive
# control register for valid drive select bits.
comment(0xBA11, "Write &5A to WD1770 track register", inline=True)
comment(0xBA13, "Write to FDC track register", inline=True)
comment(0xBA16, "Read back from track register", inline=True)
comment(0xBA19, "Does it match &5A?", inline=True)
comment(0xBA1B, "No: WD1770 not present, return C=1", inline=True)
comment(0xBA1D, "Read drive control register", inline=True)
comment(0xBA20, "Check drive select bits (0-1)", inline=True)
comment(0xBA22, "Both zero: no drive, return C=1", inline=True)
comment(0xBA24, "WD1770 present: C=0", inline=True)

# exec_floppy_write_bput_sector (&BA26)
comment(0xBA26, "A=&40: write direction flag", inline=True)
comment(0xBA2A, "A=&C0: read direction flag", inline=True)
comment(0xBA2C, "Store direction in workspace", inline=True)
comment(0xBA2F, "Transfer X to A", inline=True)
comment(0xBA30, "Save current stack pointer", inline=True)
comment(0xBA31, "For error recovery", inline=True)
comment(0xBA35, "Get disc step rate from settings", inline=True)
comment(0xBA3D, "Check read/write direction", inline=True)
comment(0xBA3F, "Reading: set up read buffer address", inline=True)
comment(0xBA41, "Writing: use zp_bc,bd as buffer", inline=True)
comment(0xBA46, "Buffer address high byte", inline=True)
comment(0xBA4D, "Reading: use zp_be,bf as buffer", inline=True)
comment(0xBA57, "Get sector count from control block", inline=True)
comment(0xBA5B, "Check drive number bits", inline=True)
comment(0xBA5D, "Drive 0: continue", inline=True)
comment(0xBA65, "Check format bit", inline=True)
comment(0xBA6A, "Check verify bit", inline=True)
comment(0xBA6E, "Not verify: seek+read (&21)", inline=True)
comment(0xBA72, "Verify: seek+read (&22)", inline=True)
comment(0xBA74, "Store in NMI control byte", inline=True)
comment(0xBA7E, "Get sector address from control blk", inline=True)
comment(0xBA85, "X = sector address high byte", inline=True)
comment(0xBA87, "Y=&FF: init track counter", inline=True)
comment(0xBA89, "Convert sector to track/sector", inline=True)
comment(0xBA8C, "Store sector number", inline=True)
comment(0xBA8E, "Store track number", inline=True)
comment(0xBA90, "Track to A for side check", inline=True)
comment(0xBA92, "Subtract 80 (side 0 tracks)", inline=True)
comment(0xBA94, "Track < 80: side 0", inline=True)
comment(0xBA96, "Track >= 80: adjust for side 1", inline=True)
comment(0xBA98, "Select side 1", inline=True)
comment(0xBA9B, "Get NMI control byte", inline=True)
comment(0xBA9E, "Write to FDC control register", inline=True)
comment(0xBABA, "Seek to track 0 first", inline=True)
comment(0xBABD, "Set up sector parameters", inline=True)
comment(0xBAC0, "Set up NMI handler", inline=True)
comment(0xBAC3, "Process result/error", inline=True)

# floppy_restore_track_0 (&BD3F)
# Issues a WD1770 restore command (seek to track 0).
# The actual restore is just 5 instructions.
comment(0xBD3F, "A=0: target track number = 0", inline=True)
comment(0xBD41, "Store as target track", inline=True)
comment(0xBD43, "OR with drive select bits", inline=True)
comment(0xBD46, "Issue restore command to WD1770", inline=True)
comment(0xBD49, "Wait for command to complete", inline=True)

# sub_cbd4c - apply head load delay flag
label(0xBBF3, "copy_nmi_code_loop")
label(0xBC12, "check_tube_for_nmi")
label(0xBC21, "setup_direct_nmi")
label(0xBC24, "store_nmi_completion")
label(0xBC2D, "setup_tube_nmi_transfer")
label(0xBC46, "copy_tube_write_nmi_loop")
label(0xBC50, "setup_tube_read_nmi")
label(0xBC52, "copy_tube_read_nmi_loop")
label(0xBC5C, "setup_direct_write_nmi")
label(0xBC62, "copy_write_nmi_loop")
label(0xBCC8, "poll_nmi_complete")
label(0xBCFD, "select_fdc_rw_command")
label(0xBD0E, "set_read_command")
label(0xBD10, "issue_fdc_command")
label(0xBD2B, "clear_transfer_complete")
label(0xBD31, "clear_side_flag")
label(0xBD38, "clear_seek_flag")
label(0xBD4C, "apply_head_load_flag")
subroutine(0xBD4C, "apply_head_load_flag",
    title="Apply head load delay to FDC command",
    description="""\
If the head-loaded flag is set in the transfer state,
OR bit 2 into A (the head load delay bit in WD1770
step/seek commands).
""",
    on_entry={"a": "FDC command byte"},
    on_exit={"a": "command with bit 2 set if head loaded",
             "x": "preserved", "y": "preserved"})
comment(0xBD4C, "Rotate head-loaded flag to carry", inline=True)
comment(0xBD4F, "Not loaded: skip", inline=True)
comment(0xBD51, "Set bit 2: head load delay", inline=True)
comment(0xBD53, "Clear carry (was set by SEC)", inline=True)
comment(0xBD54, "Restore head-loaded flag", inline=True)

# sub_cbd58 - format track operation
label(0xBD54, "restore_head_flag")
label(0xBD58, "floppy_format_track")
subroutine(0xBD58, "floppy_format_track",
    title="Format a floppy disc track",
    description="""\
Set up NMI handler addresses for a format operation,
then write the track format data to disc.
""")

label(0xBE69, "floppy_next_sector")
subroutine(0xBE69, "floppy_next_sector",
    title="Advance multi-sector transfer to next sector",
    description="""\
Called from the NMI end-of-operation handler during
multi-sector transfers. Clears the transfer-complete
flag, then calls the FDC seek routine to check whether
a track boundary has been crossed and step the head if
needed. If the seek routine returns zero, all sectors
have been transferred and the completion flag is set.
""")

# cbb09 - write WD1770 register with verify
label(0xBB09, "fdc_write_register_verify")
subroutine(0xBB09, "fdc_write_register_verify",
    title="Write to WD1770 register with readback verify",
    description="""\
Write value from zp_a3+X to FDC register at &FE85+X,
then read back and loop until the value matches.
This handles the WD1770's register write timing.
""",
    on_entry={"x": "FDC register index (0=track, 1=sector, 2=data)"},
    on_exit={"a": "value written to register",
             "x": "preserved", "y": "preserved"})
comment(0xBB09, "Get value to write", inline=True)
comment(0xBB0B, "Write to FDC register", inline=True)
comment(0xBB0E, "Read back from register", inline=True)
comment(0xBB11, "Loop until value sticks", inline=True)

# floppy_wait_nmi_finish (&BCC2)
# Polls until the NMI transfer flag is set (bit 4 of &0D5D),
# indicating the WD1770 has completed its data transfer.
# Also checks for Escape and times out with drive overrun
# error (&6F) if Escape is pressed during the transfer.
comment(0xBCC2, "Check if transfer already complete", inline=True)
comment(0xBCC4, "Bit 0 of zp_a2 into carry", inline=True)
comment(0xBCC5, "Carry set: already done", inline=True)
comment(0xBCC8, "Read NMI completion flag", inline=True)
comment(0xBCCB, "Bit 4 set = DRQ complete?", inline=True)
comment(0xBCCD, "Not yet, keep waiting", inline=True)
comment(0xBCCF, "Check for Escape condition", inline=True)
comment(0xBCD1, "Bit 7 clear: no Escape", inline=True)
comment(0xBCD3, "Escape pressed: stop drive", inline=True)
comment(0xBCD5, "Write 0 to FDC control", inline=True)
comment(0xBCD8, "Error &6F: drive overrun/Escape", inline=True)
comment(0xBCDC, "Handle floppy error", inline=True)

# floppy_ts_block_check_range (&BF55)
# Validates sector address < &0A00 (640K disc limit).
# Error &61 = bad address, &63 = volume error.
comment(0xBF55, "Y=7: offset to sector mid byte", inline=True)
comment(0xBF57, "Get sector address mid byte", inline=True)
comment(0xBF59, "Sector mid >= &0A (2560 sectors)?", inline=True)
comment(0xBF5B, "Below limit, calculate track/sector", inline=True)
comment(0xBF5D, "Above &0A: definitely out of range", inline=True)
comment(0xBF5F, "Exactly &0A: check low byte too", inline=True)
comment(0xBF60, "Get sector address low byte", inline=True)
comment(0xBF62, "Low byte < 0? (always false)", inline=True)
comment(0xBF66, "Error &61: bad address", inline=True)
comment(0xBF68, "Store error code", inline=True)
comment(0xBF6A, "Branch to floppy error handler", inline=True)
comment(0xBF6C, "Check if multi-sector operation", inline=True)
comment(0xBF6E, "Bit 4 set: sector count specified?", inline=True)
comment(0xBF70, "No, just calculate track/sector", inline=True)
comment(0xBF72, "Y=9: offset to sector count", inline=True)
comment(0xBF74, "Get sector count", inline=True)
comment(0xBF76, "Y=8: back to sector low byte", inline=True)
comment(0xBF77, "Clear carry for addition", inline=True)
comment(0xBF78, "Add sector count to start sector", inline=True)
comment(0xBF7A, "Carry set: overflow, error", inline=True)
comment(0xBF7C, "End sector < 1? (no sectors)", inline=True)
comment(0xBF7E, "OK, calculate track/sector", inline=True)
comment(0xBF80, "Error &63: volume error", inline=True)
comment(0xBF82, "Store error code", inline=True)
comment(0xBF84, "Branch to floppy error handler", inline=True)

# floppy_ts_b0_block (&BF86)
# Block address at (&B0)+7,+8. Divides by 16 sectors/track.
# Track in Y (zp_a5), sector in A (zp_a4).
# If track >= 80, subtracts 80 and selects side 1.
comment(0xBF86, "Y=7: offset to sector mid byte", inline=True)
comment(0xBF88, "Get sector address mid byte (X)", inline=True)
comment(0xBF8B, "Y=8: offset to sector low byte", inline=True)
comment(0xBF8C, "Get sector address low byte (A)", inline=True)
comment(0xBF8E, "Y=&FF: init quotient to 0 (+1 later)", inline=True)
comment(0xBF90, "Divide X:A by 16 sectors/track", inline=True)
comment(0xBF93, "A = sector within track", inline=True)
comment(0xBF95, "Y = track number", inline=True)
comment(0xBF97, "Copy track to A", inline=True)
comment(0xBF98, "Set carry for subtraction", inline=True)
comment(0xBF99, "Subtract 80 tracks (side 0)", inline=True)
comment(0xBF9B, "Track < 80: side 0, done", inline=True)
comment(0xBF9D, "Track >= 80: save adjusted track", inline=True)
comment(0xBF9F, "Select side 1", inline=True)

# load_fsm (&A816)
# Loads sectors 0-1 from disc to &0E00-&0FFF using a
# pre-built control block at &880C.
comment(0xA816, "X=&0C: control block offset", inline=True)
comment(0xA818, "Y=&88: control block page", inline=True)
comment(0xA81A, "Execute disc read command", inline=True)

# floppy_error (&BFAE)
# Called when a floppy disc operation fails. Restores the stack,
# releases NMI and Tube, translates the error code, and returns
# to the caller of the original disc operation.
comment(0xBFAE, "Restore stack pointer from saved val", inline=True)
comment(0xBFB2, "Check if NMI was in use", inline=True)
comment(0xBFB5, "Bit 5: NMI active?", inline=True)
comment(0xBFB7, "No NMI, skip to Tube release", inline=True)
comment(0xBFB9, "Get NMI status byte", inline=True)
comment(0xBFBC, "Rotate bit 0 into carry", inline=True)
comment(0xBFBD, "Get partial transfer count", inline=True)
comment(0xBFBF, "C=0: store as second count", inline=True)
comment(0xBFC1, "C=1: store as first count", inline=True)
comment(0xBFCD, "Store as second count", inline=True)
comment(0xBFD8, "Get error code from zp_a0", inline=True)
comment(0xBFDA, "Save as error number", inline=True)
comment(0xBFDD, "Release NMI", inline=True)
comment(0xBFE0, "Release Tube if in use", inline=True)
comment(0xBFE3, "Restore control block ptr low", inline=True)
comment(0xBFE5, "Get error number", inline=True)
comment(0xBFE8, "Zero = no error, return success", inline=True)
comment(0xBFEA, "Set bit 6: disc error flag", inline=True)
comment(0xBFEC, "Y=&FF: mark transfer incomplete", inline=True)
comment(0xBFF1, "Restore control block ptr high", inline=True)
comment(0xBFF3, "Mask to 7-bit error code", inline=True)

# service_handler_9 (&9DBE) - *HELP handler
# Checks if the *HELP argument matches "ADFS" (case-insensitive,
# abbreviation with dot allowed). If so, prints the version
# string and a list of all star commands from the command table.
comment(0x9DBC, "CR + bit 7: end of version string", inline=True)
comment(0x9DBD, "Return to caller", inline=True)
comment(0x9DBE, "Save Y (text pointer offset)", inline=True)
comment(0x9DC0, "Get first char of *HELP argument", inline=True)
comment(0x9DC2, "Is it a printable char?", inline=True)
comment(0x9DC4, "Yes, try matching 'ADFS'", inline=True)
comment(0x9DC6, "No argument: print version banner", inline=True)
comment(0x9DC9, "Print '  ADFS'", inline=True)
comment(0x9DD5, "Get our ROM number", inline=True)
comment(0x9DD7, "A=9: return service 9 (not claimed)", inline=True)
comment(0x9DDA, "Check next char of HELP argument", inline=True)
comment(0x9DDD, "Is it printable?", inline=True)
comment(0x9DDF, "Yes, return (more text follows)", inline=True)
comment(0x9DE1, "End of argument: pop return address", inline=True)
comment(0x9DE3, "Return to service dispatcher", inline=True)
comment(0x9DE5, "Skip non-space chars in argument", inline=True)
comment(0x9DEA, "Skip space chars after word", inline=True)
comment(0x9DEF, "X=3: compare 4 chars of 'ADFS'", inline=True)
comment(0x9DF1, "Get char from argument", inline=True)
comment(0x9DF3, "Is it a dot (abbreviation)?", inline=True)
comment(0x9DF5, "Yes, match succeeded", inline=True)
comment(0x9DF7, "Convert to lowercase for compare", inline=True)
comment(0x9DF9, 'Compare with "adfs" backwards', inline=True)
comment(0x9DFC, "No match, skip this word", inline=True)
comment(0x9DFE, "Next char in argument", inline=True)
comment(0x9DFF, "Next char in 'ADFS'", inline=True)
comment(0x9E00, "Loop for 4 chars", inline=True)
comment(0x9E02, "Check char after 'ADFS' match", inline=True)
comment(0x9E04, "More alpha chars? Not exact match", inline=True)
comment(0x9E06, "Not a match, skip word", inline=True)
comment(0x9E08, "Print version info", inline=True)
comment(0x9E0B, "X=0: start of command table", inline=True)
comment(0x9E0D, "Get command table byte", inline=True)
comment(0x9E10, "Bit 7 set: end of table", inline=True)
comment(0x9E12, 'Print "  " indent before command name', inline=True)
comment(0x9E16, "' ' + bit 7: end of inline string", inline=True)

# *HELP command list loop (&9E17)
# Prints each command from the table, padded to 10 chars,
# followed by its address as two hex digits.
comment(0x9E17, "Y=9: max 10 chars per command name", inline=True)
comment(0x9E19, "Get char from command table", inline=True)
comment(0x9E1C, "Bit 7 set: end of command name", inline=True)
comment(0x9E1E, "Print command name character", inline=True)
comment(0x9E21, "Next table byte", inline=True)
comment(0x9E22, "Decrement char counter", inline=True)
comment(0x9E23, "Loop for up to 10 chars", inline=True)
comment(0x9E25, "Print space for padding", inline=True)
comment(0x9E28, "Decrement padding counter", inline=True)
comment(0x9E29, "Loop until 10 columns filled", inline=True)
comment(0x9E2B, "Save table index", inline=True)
comment(0x9E2D, "Get address byte from table+2", inline=True)
comment(0x9E30, "Save for low nibble", inline=True)
comment(0x9E31, "Shift high nibble down", inline=True)
comment(0x9E35, "Print as hex digit", inline=True)
comment(0x9E38, "Restore address byte", inline=True)
comment(0x9E39, "Isolate low nibble", inline=True)
comment(0x9E3B, "Print as hex digit", inline=True)
comment(0x9E3E, "Print newline", inline=True)
comment(0x9E41, "Restore table index", inline=True)
comment(0x9E43, "Skip past 3-byte entry data", inline=True)
comment(0x9E46, "Loop for all commands", inline=True)

# jmp_indirect_fscv (&9A43)
comment(0x9A43, "Jump through filing system control", inline=True)

# Data block at &9A46 - default workspace initialisation data
# Default workspace data: label, byte directives, and comments
# are in the interstitial data section near the entry() calls.

# scsi_send_cmd_byte (&82FB)
# Wrapper that sends a byte via scsi_send_byte_a and raises
# a BRK error if the SCSI bus enters an unexpected phase.
comment(0x82FB, "Send byte A via SCSI", inline=True)
comment(0x82FE, "Non-zero result: SCSI error", inline=True)

# sub_c8301 - send byte wrapper
label(0x8301, "scsi_send_byte_wrapper")
comment(0x8301, "Send byte and return status", inline=True)

# floppy_command_ind (&BA00)
# Indirect jump table for floppy disc operations.
# These are called from the main command_exec code
# and redirect to the actual floppy driver routines.
comment(0xBA0C, "A=&FF: mark transfer state", inline=True)
comment(0xBA0E, "Store in transfer workspace", inline=True)

# osbget_handler (&AD63)
# OSBGET reads one byte from an open file.
# Validates the channel, checks for EOF, reads the next
# byte from the file buffer, advancing PTR.
comment(0xAD63, "Save X register", inline=True)
comment(0xAD65, "Validate file handle in Y", inline=True)
comment(0xAD68, "Rotate channel flags bit 0 to C", inline=True)
comment(0xAD69, "Bit 0 set: file is readable", inline=True)
comment(0xAD6B, "Check bit 2 (at EOF flag)", inline=True)
comment(0xAD6D, "At EOF: raise EOF error", inline=True)
comment(0xAD6F, "Compare EXT with PTR", inline=True)
comment(0xAD72, "EXT != PTR: not at EOF, read byte", inline=True)
comment(0xAD74, "EXT == PTR and EOF: raise error", inline=True)
comment(0xAD76, "Save registers for restore", inline=True)
comment(0xAD79, "Get channel index", inline=True)
comment(0xAD7B, "Get channel flags", inline=True)

# osargs_handler (&A955)
# OSARGS dispatch:
#   Y=0, A=0: return FS number (8 = ADFS)
#   Y=0, A=1: return command line tail address
#   Y=0, A=2+: further handlers
#   Y!=0: file-specific (PTR, EXT, allocation)
comment(0xA955, "Y=0? General OSARGS query", inline=True)
comment(0xA957, "Y!=0: file-specific handler", inline=True)
comment(0xA959, "Transfer A to Y (function code)", inline=True)
comment(0xA95A, "A=0? Return FS number", inline=True)
comment(0xA95C, "A=8: ADFS filing system number", inline=True)
comment(0xA95F, "Save registers for later restore", inline=True)
comment(0xA962, "Save X (zero page pointer)", inline=True)
comment(0xA964, "Y=0 means function was 1", inline=True)
comment(0xA965, "A!=1: check further functions", inline=True)
comment(0xA967, "A=1: return command tail low byte", inline=True)
comment(0xA96A, "Store in zero page at X+0", inline=True)
comment(0xA96C, "Command tail high byte", inline=True)
comment(0xA96F, "Store in zero page at X+1", inline=True)
comment(0xA971, "Y=&FF", inline=True)
comment(0xA972, "Clear X+2 (high bytes)", inline=True)
comment(0xA974, "Clear X+3", inline=True)
comment(0xA976, "Restore X", inline=True)
comment(0xA978, "A=0: success", inline=True)

# OSARGS dispatch continuation (&A97C onwards)
# A=0,1 handled above. For A>=2, Y!=0 (file handle):
# A=2: read PTR, A=3: write PTR, A=4: read EXT,
# A=5: write EXT (allocation), A=&FF: ensure
comment(0xA981, "Clear workspace entry", inline=True)
comment(0xA986, "Step back 4 bytes (entry size)", inline=True)
comment(0xA98A, "Loop for all entries", inline=True)
comment(0xA9A1, "Restore function code", inline=True)
comment(0xA9A2, "Get channel index", inline=True)
comment(0xA9A4, "A still non-zero?", inline=True)
comment(0xA9A5, "A=2: skip (A-1!=0 means not A=2)", inline=True)
comment(0xA9A7, "A=2: read PTR to user zero page", inline=True)
comment(0xA9A9, "Get PTR low byte from channel table", inline=True)
comment(0xA9AC, "Store at user's X+0", inline=True)
comment(0xA9AE, "Get PTR mid-low byte", inline=True)
comment(0xA9B3, "Get PTR mid-high byte", inline=True)
comment(0xA9B8, "Get PTR high byte", inline=True)
comment(0xA9C0, "A=0: success return", inline=True)
comment(0xA9C7, "Decrement: A=3 (write PTR)?", inline=True)
comment(0xA9C8, "No, check A=4", inline=True)
comment(0xA9CA, "A=3: check file is open for write", inline=True)
comment(0xA9CD, "Bit 7 clear: read-only, error", inline=True)
comment(0xA9CF, "A=3: copy new PTR from user's ZP", inline=True)
comment(0xA9D1, "Get new PTR low byte", inline=True)
comment(0xA9E8, "Store new PTR in channel table", inline=True)
comment(0xA9EE, "Set PTR low byte", inline=True)
comment(0xA9F3, "Set PTR mid-low byte", inline=True)
comment(0xA9F8, "Set PTR mid-high byte", inline=True)
comment(0xA9FD, "Set PTR high byte", inline=True)
comment(0xAA03, "A=3: check new PTR <= EXT", inline=True)
comment(0xAA07, "Subtract new PTR from EXT", inline=True)
comment(0xAA1C, "New PTR > EXT: error", inline=True)
comment(0xAA1E, "New PTR <= EXT: set PTR", inline=True)
comment(0xAA46, "Decrement: A=4 (read EXT)?", inline=True)
comment(0xAA47, "No, check A=5", inline=True)
comment(0xAA49, "A=4: read EXT to user zero page", inline=True)
comment(0xAA4B, "Get EXT low byte", inline=True)
comment(0xAA62, "Decrement: A=5 (write EXT)?", inline=True)
comment(0xAA63, "No, handle ensure", inline=True)
comment(0xAA65, "A=5: check file is open for write", inline=True)
comment(0xAA67, "Get channel flags", inline=True)
comment(0xAA6A, "Bit 7 set: writable, proceed", inline=True)
comment(0xAA6F, "Copy new EXT from user's ZP", inline=True)

# fsc6_new_filing_system (&A93C)
# Called when another filing system is about to take over.
# Saves workspace checksum and closes any open spool/exec.
comment(0xA93C, "Get workspace page address", inline=True)
comment(0xA93F, "Y=&FF: store at byte 255", inline=True)
comment(0xA941, "Mark workspace as needing save", inline=True)
comment(0xA943, "Check if drive is initialised", inline=True)
comment(0xA946, "Drive = &FF (uninitialised)?", inline=True)
comment(0xA947, "Yes, nothing more to do", inline=True)
comment(0xA949, "OSBYTE &77: close spool/exec files", inline=True)
comment(0xA94E, "Save workspace state to disc", inline=True)
comment(0xA951, "Y=&FF: will become 0 after INY", inline=True)
comment(0xA953, "A=&FF: flag for OSARGS", inline=True)
comment(0xA954, "Y=0: falls through to osargs_handler", inline=True)

# star_destroy (&99E6)
# Lists matching files, prompts "Destroy ? ", reads "YES\r"
# one char at a time (case-insensitive), then deletes each
# matching file in a loop.
comment(0x99E6, "Save filename pointer low", inline=True)
comment(0x99E8, "Push low byte", inline=True)
comment(0x99E9, "Save filename pointer high", inline=True)
comment(0x99EB, "Push high byte", inline=True)
comment(0x99EC, "Set up workspace for *INFO call", inline=True)
comment(0x99EE, "Store in control block pointer low", inline=True)
comment(0x99F0, "Control block page = &10", inline=True)
comment(0x99F2, "Store in control block pointer high", inline=True)
comment(0x99F4, "List matching files via *INFO", inline=True)
comment(0x99F7, "Restore filename pointer high", inline=True)
comment(0x99F8, "Store in (&B5)", inline=True)
comment(0x99FA, "Restore filename pointer low", inline=True)
comment(0x99FB, "Store in (&B4)", inline=True)
comment(0x99FD, 'Print "Destroy ? "', inline=True)
comment(0x9A09, "' ' + bit 7: end of inline string", inline=True)
comment(0x9A0A, 'X=3: expect 4 chars (CR,Y,E,S)', inline=True)
comment(0x9A0C, "Read character from keyboard", inline=True)
comment(0x9A0F, "Is it a printable char?", inline=True)
comment(0x9A11, "No, don't echo control chars", inline=True)
comment(0x9A13, "Echo the typed character", inline=True)
comment(0x9A16, "Convert to uppercase", inline=True)
comment(0x9A18, 'Compare with "YES\\r" (reversed)', inline=True)
comment(0x9A1B, "Mismatch: abort with Aborted error", inline=True)
comment(0x9A1D, "Next expected character", inline=True)
comment(0x9A1E, "Loop for all 4 chars", inline=True)
comment(0x9A20, "Print newline after YES", inline=True)
comment(0x9A23, "Clear channel for error messages", inline=True)
comment(0x9A24, "Store in current channel workspace", inline=True)
comment(0x9A27, "Deletion loop: save filename low", inline=True)
comment(0x9A29, "Push low byte", inline=True)
comment(0x9A2A, "Save filename pointer high", inline=True)
comment(0x9A2C, "Push high byte", inline=True)
comment(0x9A2D, "Find next matching file", inline=True)
comment(0x9A30, "Not found: all deleted, finish", inline=True)
comment(0x9A32, "Delete this file", inline=True)
comment(0x9A35, "Restore filename pointer high", inline=True)
comment(0x9A36, "Store in (&B5)", inline=True)
comment(0x9A38, "Restore filename pointer low", inline=True)
comment(0x9A39, "Store in (&B4)", inline=True)
comment(0x9A3B, "Loop to delete next match", inline=True)
comment(0x9A3E, "Discard saved filename from stack", inline=True)
comment(0x9A3F, "Discard second saved byte", inline=True)
comment(0x9A40, "Save workspace and return", inline=True)

# osgbpb_handler (&B57F)
# OSGBPB dispatch:
#   A=1-4: file byte transfer operations (read/write)
#   A=5-8: directory/title reading operations
comment(0xB57F, "Save registers for restore", inline=True)
comment(0xB582, "Store OSGBPB function code", inline=True)
comment(0xB588, "Save control block pointer", inline=True)
comment(0xB58C, "Y=1: copy 4 bytes of memory addr", inline=True)
comment(0xB58E, "X=3: 4 bytes to copy", inline=True)
comment(0xB590, "Copy data address from control blk", inline=True)
comment(0xB592, "Store in workspace", inline=True)
comment(0xB599, "Get function code", inline=True)
comment(0xB59C, "Function >= 5?", inline=True)
comment(0xB59E, "No, file I/O operations (1-4)", inline=True)
comment(0xB5A0, "Yes, directory operations (5-8)", inline=True)
comment(0xB5A4, "Transfer function to Y", inline=True)
comment(0xB5A5, "Function 0: do nothing", inline=True)
comment(0xB5A7, "Y=0: get file handle from block", inline=True)
comment(0xB5A9, "Read channel number from block+0", inline=True)
comment(0xB5AC, "Validate file handle", inline=True)

# osgbpb_handler body (&B5B0-&B9FF) - the final routine!
# OSGBPB: A=1-4 file byte transfer, A=5-8 directory info read

# File I/O path: setup channel and PTR
comment(0xB5B0, "Flush buffer if dirty", inline=True)
comment(0xB5B3, "Get channel index", inline=True)
comment(0xB5B5, "Get channel drive+sector", inline=True)
comment(0xB5B8, "Check disc change for drive", inline=True)
comment(0xB5BB, "Restore flags from earlier", inline=True)
comment(0xB5BC, "Bit 7 set: writable channel", inline=True)
comment(0xB5BE, "Get function code", inline=True)
comment(0xB5C1, "A >= 3 (read operation)?", inline=True)
comment(0xB5C3, "Yes: skip write check", inline=True)
comment(0xB5C5, "Write to read-only: error", inline=True)

# Handle PTR for A=1,3 (new sequential pointer)
comment(0xB5C8, "Get function code", inline=True)
comment(0xB5CB, "Bit 0 set = use new PTR (A=1,3)", inline=True)
comment(0xB5CD, "Bit 0 clear = use current PTR", inline=True)
comment(0xB5CF, "Y=&0C: copy new PTR from block", inline=True)
comment(0xB5D1, "X=3: 4 PTR bytes", inline=True)
comment(0xB5D3, "Get PTR byte from control block", inline=True)
comment(0xB5D5, "Store in zp_c8-cb (temp PTR)", inline=True)
comment(0xB5D7, "Next block byte (decreasing)", inline=True)
comment(0xB5D8, "Next ZP byte (decreasing)", inline=True)
comment(0xB5D9, "Loop for 4 bytes", inline=True)
comment(0xB5DB, "A=1: flag for new PTR", inline=True)
comment(0xB5DD, "Restore Y from saved value", inline=True)
comment(0xB5DF, "X=&C8: point to temp PTR in ZP", inline=True)
comment(0xB5E1, "Set PTR from temp PTR", inline=True)
comment(0xB5E4, "Clear carry for addition", inline=True)
comment(0xB5E5, "X=3: add byte count to end PTR", inline=True)
comment(0xB5E7, "Y=5: byte count in control block", inline=True)
comment(0xB5E9, "Get byte count byte", inline=True)
comment(0xB5EB, "Add to start PTR byte", inline=True)
comment(0xB5EE, "Store end position", inline=True)
comment(0xB5F1, "Next byte", inline=True)
comment(0xB5F2, "Next count byte", inline=True)
comment(0xB5F3, "Loop for 4 bytes", inline=True)
comment(0xB5F5, "Get function code", inline=True)
comment(0xB5F8, "Store in mode flag", inline=True)
comment(0xB5FB, "A >= 3 (read)?", inline=True)
comment(0xB5FD, "Yes: skip extent check", inline=True)
comment(0xB5FF, "Write: extend file if needed", inline=True)

# Update PTR in channel table and control block
comment(0xB602, "Y=9: PTR offset in control block", inline=True)
comment(0xB604, "Get channel index", inline=True)
comment(0xB606, "Get new PTR low from workspace", inline=True)
comment(0xB609, "Store in channel PTR low", inline=True)
comment(0xB60C, "Store in control block too", inline=True)
comment(0xB60E, "Y=&0A: next byte", inline=True)
comment(0xB60F, "Get PTR mid-low", inline=True)
comment(0xB612, "Store in channel", inline=True)
comment(0xB615, "Store in control block", inline=True)
comment(0xB617, "Y=&0B", inline=True)
comment(0xB618, "Get PTR mid-high", inline=True)
comment(0xB61B, "Store in channel", inline=True)
comment(0xB61E, "Store in control block", inline=True)
comment(0xB620, "Y=&0C", inline=True)
comment(0xB621, "Get PTR high", inline=True)
comment(0xB624, "Store in channel", inline=True)
comment(0xB627, "Store in control block", inline=True)
comment(0xB629, "Get function code", inline=True)
comment(0xB62C, "A >= 3 (read)?", inline=True)
comment(0xB62E, "Yes: skip to byte transfer", inline=True)

# Save byte count and clear it in control block
comment(0xB630, "X=3: save 4-byte count", inline=True)
comment(0xB632, "Y=5: byte count in block", inline=True)
comment(0xB634, "Get byte count from block", inline=True)
comment(0xB636, "Save in workspace", inline=True)
comment(0xB639, "A=0: clear byte count in block", inline=True)
comment(0xB63B, "Store zero in block", inline=True)
comment(0xB63D, "Next byte", inline=True)
comment(0xB63F, "Loop for 4 bytes", inline=True)
comment(0xB641, "Jump to byte transfer loop", inline=True)

# Read path: check if read would pass EOF
comment(0xB644, "Compare EXT with PTR", inline=True)
comment(0xB647, "C set: EXT > PTR, data available", inline=True)
comment(0xB649, "Equal: at EOF already", inline=True)
comment(0xB64B, "A=0: clear mode flag (partial read)", inline=True)
comment(0xB64D, "Store cleared mode", inline=True)
comment(0xB650, "Get channel index", inline=True)
comment(0xB652, "Calculate available = EXT - PTR", inline=True)
comment(0xB653, "EXT low - PTR low", inline=True)
comment(0xB656, "Subtract PTR byte", inline=True)
comment(0xB658, "Store available low", inline=True)
comment(0xB65B, "EXT mid-low", inline=True)
comment(0xB65E, "Subtract PTR mid-low", inline=True)
comment(0xB660, "Store available mid-low", inline=True)
comment(0xB663, "EXT mid-high", inline=True)
comment(0xB666, "Subtract PTR mid-high", inline=True)
comment(0xB668, "Store available mid-high", inline=True)
comment(0xB66B, "EXT high", inline=True)
comment(0xB66E, "Subtract PTR high", inline=True)
comment(0xB670, "Store available high", inline=True)
comment(0xB673, "X=3: reduce requested by unavail", inline=True)
comment(0xB675, "Y=5: byte count in control block", inline=True)
comment(0xB677, "Set carry for subtraction", inline=True)
comment(0xB678, "Get requested count byte", inline=True)
comment(0xB67A, "Subtract saved count byte", inline=True)
comment(0xB67D, "Store reduced count in block", inline=True)
comment(0xB67F, "Next byte", inline=True)
comment(0xB680, "Next count byte", inline=True)
comment(0xB681, "Loop for 4 bytes", inline=True)

# Set PTR to EXT (we'll read exactly to EOF)
comment(0xB683, "Get channel index", inline=True)
comment(0xB685, "Get EXT low", inline=True)
comment(0xB688, "Store as new PTR low", inline=True)
comment(0xB68B, "Update channel PTR low", inline=True)
comment(0xB68E, "Store in control block", inline=True)
comment(0xB690, "Y=next byte", inline=True)
comment(0xB691, "Get EXT mid-low", inline=True)
comment(0xB694, "Store as new PTR mid-low", inline=True)
comment(0xB697, "Update channel PTR mid-low", inline=True)
comment(0xB69A, "Store in control block", inline=True)
comment(0xB69C, "Y=next byte", inline=True)
comment(0xB69D, "Get EXT mid-high", inline=True)
comment(0xB6A0, "Store as new PTR mid-high", inline=True)
comment(0xB6A3, "Update channel PTR mid-high", inline=True)
comment(0xB6A6, "Store in control block", inline=True)
comment(0xB6A8, "Y=next byte", inline=True)
comment(0xB6A9, "Get EXT high", inline=True)
comment(0xB6AC, "Store as new PTR high", inline=True)
comment(0xB6AF, "Update channel PTR high", inline=True)
comment(0xB6B2, "Store in control block", inline=True)

# Byte transfer loop setup (&B6B4)
comment(0xB6B4, "Y=1: memory address in control block", inline=True)
comment(0xB6B6, "X=3: 4 address bytes", inline=True)
comment(0xB6B8, "Clear carry for addition", inline=True)

# OSGBPB remaining scattered items
comment(0xB585, "Store mode flag copy", inline=True)
comment(0xB58A, "Store control block pointer low", inline=True)
comment(0xB595, "Next byte", inline=True)
comment(0xB596, "Decrement counter", inline=True)
comment(0xB597, "Loop for 4 bytes", inline=True)
comment(0xB5A3, "Return (function 0: do nothing)", inline=True)
comment(0xB5AB, "Transfer function to Y", inline=True)
comment(0xB5AF, "Save flags for write check", inline=True)
comment(0xB63E, "Decrement counter", inline=True)

# Multi-sector disc transfer setup (cb6b4)
# After updating PTR and byte counts in the control block,
# this prepares for bulk disc I/O. It adds the transferred
# byte count to the control block memory address, checks
# whether the target is Tube or host memory, and sets up
# the disc operation for the actual sector read/write.
comment(0xB6B9, "Get transferred bytes count", inline=True)
comment(0xB6BE, "Store updated memory address", inline=True)
comment(0xB6C0, "Next address byte", inline=True)
comment(0xB6C1, "Next count byte", inline=True)
comment(0xB6C2, "Loop for 4 address bytes", inline=True)
comment(0xB6C4, "Get PTR high byte", inline=True)
comment(0xB6C6, "Non-zero: multi-sector possible", inline=True)
comment(0xB6C8, "PTR high=0: no full sectors remain", inline=True)
comment(0xB6CB, "Get channel index for sector calc", inline=True)
comment(0xB6CD, "Clear carry for sector addition", inline=True)
comment(0xB6CE, "Get channel start sector low", inline=True)
comment(0xB6D1, "Add PTR mid-low for disc sector", inline=True)
comment(0xB6D3, "Store disc operation sector low", inline=True)
comment(0xB6D6, "Get channel start sector mid", inline=True)
comment(0xB6D9, "Add PTR mid-high", inline=True)
comment(0xB6DB, "Store disc operation sector mid", inline=True)
comment(0xB6DE, "Get channel start sector+drive", inline=True)
comment(0xB6E1, "Add PTR high byte", inline=True)
comment(0xB6E3, "Store disc operation sector high", inline=True)
comment(0xB6E6, "A=2: compare against function code", inline=True)
comment(0xB6E8, "C set if A=1/2 (write), clear if 3/4", inline=True)
comment(0xB6EB, "A=&80: base for disc command", inline=True)
comment(0xB6ED, "Rotate C into bit 0: &40=read, &80=write", inline=True)

# OSGBPB multi-sector transfer body (&B6EE-&B824)
# Performs the actual byte-at-a-time or sector transfer
# between the file and user memory/Tube. Handles both
# the buffered single-byte path and the bulk disc path.
comment(0xB6EE, "Find/load buffer for current sector", inline=True)
comment(0xB6F1, "Get current byte offset in sector", inline=True)
comment(0xB6F3, "Store as transfer start position", inline=True)
comment(0xB6F6, "A=0: default end position", inline=True)
comment(0xB6F8, "Clear transfer end position", inline=True)
comment(0xB6FB, "X=2: compare 3-byte buffer sector", inline=True)
comment(0xB6FD, "Get buffered sector address byte", inline=True)
comment(0xB700, "Compare with requested sector byte", inline=True)
comment(0xB702, "Mismatch: different sector in buffer", inline=True)
comment(0xB704, "Next sector address byte", inline=True)
comment(0xB705, "Loop for 3-byte sector comparison", inline=True)
comment(0xB707, "Sector match: get bytes remaining", inline=True)
comment(0xB70A, "Store as transfer end position", inline=True)
comment(0xB70D, "Transfer bytes within this sector", inline=True)
comment(0xB710, "Save workspace state", inline=True)
comment(0xB713, "Flush buffer if modified", inline=True)
comment(0xB716, "A=0: prepare return status", inline=True)
comment(0xB718, "Compare against mode flag for C", inline=True)
comment(0xB71B, "Restore control block pointer low", inline=True)
comment(0xB71D, "Restore control block pointer high", inline=True)
comment(0xB71F, "Return to OSGBPB caller", inline=True)
comment(0xB720, "Buffer mismatch: handle partial xfer", inline=True)
comment(0xB723, "A=0: compute bytes already done", inline=True)
comment(0xB725, "Set carry for subtraction", inline=True)
comment(0xB726, "Subtract start position", inline=True)
comment(0xB729, "Store bytes transferred this pass", inline=True)
comment(0xB72C, "Clear carry for addition", inline=True)
comment(0xB72D, "Add to cumulative data address low", inline=True)
comment(0xB730, "Store updated address low", inline=True)
comment(0xB733, "No carry: skip higher bytes", inline=True)
comment(0xB735, "Propagate carry to address byte 2", inline=True)
comment(0xB738, "No carry: skip", inline=True)
comment(0xB73A, "Propagate carry to address byte 3", inline=True)
comment(0xB73D, "No carry: skip", inline=True)
comment(0xB73F, "Propagate carry to address byte 4", inline=True)
comment(0xB742, "Subtract from remaining byte count", inline=True)
comment(0xB743, "Get remaining count low", inline=True)
comment(0xB746, "Subtract bytes transferred", inline=True)
comment(0xB749, "Store updated remaining count", inline=True)
comment(0xB74C, "No borrow: count still positive", inline=True)
comment(0xB74E, "Y=1: propagate borrow to higher bytes", inline=True)
comment(0xB750, "Get remaining count byte", inline=True)
comment(0xB753, "Subtract borrow", inline=True)
comment(0xB755, "Store updated count byte", inline=True)
comment(0xB758, "No borrow: done adjusting", inline=True)
comment(0xB75A, "Next count byte", inline=True)
comment(0xB75B, "Loop for remaining bytes", inline=True)
comment(0xB75D, "Check if any full sectors to transfer", inline=True)
comment(0xB760, "OR mid-low count byte", inline=True)
comment(0xB763, "OR mid-high count byte", inline=True)
comment(0xB766, "Non-zero: full sectors remain", inline=True)
comment(0xB768, "No full sectors: finish transfer", inline=True)
comment(0xB76B, "A=1: flag multi-sector disc operation", inline=True)
comment(0xB76D, "Store in disc op result field", inline=True)
comment(0xB770, "Y=3: copy 4-byte data address", inline=True)
comment(0xB772, "Get data address byte", inline=True)
comment(0xB775, "Store in disc op memory address", inline=True)
comment(0xB778, "Next byte (decreasing)", inline=True)
comment(0xB779, "Loop for 4 bytes", inline=True)
comment(0xB77B, "A=2: compare against function code", inline=True)
comment(0xB77D, "C set if write (A<=2), clear if read", inline=True)
comment(0xB780, "A=2: base for disc command", inline=True)
comment(0xB782, "Rotate C into bit 0", inline=True)
comment(0xB783, "Shift to command position", inline=True)
comment(0xB784, "Store read/write disc command", inline=True)
comment(0xB787, "Get channel index", inline=True)
comment(0xB789, "Get PTR low (byte offset in sector)", inline=True)
comment(0xB78B, "Compare with 1 to set carry", inline=True)
comment(0xB78D, "Get channel start sector low", inline=True)
comment(0xB790, "Add PTR mid-low for disc sector", inline=True)
comment(0xB792, "Store disc op sector low byte", inline=True)
comment(0xB795, "Get channel start sector mid", inline=True)
comment(0xB798, "Add PTR mid-high", inline=True)
comment(0xB79A, "Store disc op sector mid byte", inline=True)
comment(0xB79D, "Get channel start sector+drive", inline=True)
comment(0xB7A0, "Add PTR high", inline=True)
comment(0xB7A2, "Store disc op sector high byte", inline=True)
comment(0xB7A5, "Y=4: save 5 bytes of CSD state", inline=True)
comment(0xB7A7, "Get CSD sector/drive byte", inline=True)
comment(0xB7AA, "Save in temp workspace", inline=True)
comment(0xB7AD, "Next byte (decreasing)", inline=True)
comment(0xB7AE, "Loop for 5 bytes", inline=True)
comment(0xB7B0, "Clear current drive (Y=0)", inline=True)
comment(0xB7B3, "Clear disc op sector count", inline=True)
comment(0xB7B6, "Clear disc op control byte", inline=True)
comment(0xB7B9, "Clear disc op transfer length", inline=True)
comment(0xB7BC, "Clear carry for sector calculation", inline=True)
comment(0xB7BD, "X=2: add 3-byte sector count", inline=True)
comment(0xB7BF, "Get remaining count byte", inline=True)
comment(0xB7C2, "Copy to disc op transfer length", inline=True)
comment(0xB7C5, "Add to cumulative address", inline=True)
comment(0xB7C8, "Store updated address", inline=True)
comment(0xB7CB, "Next byte", inline=True)
comment(0xB7CC, "Next sector byte", inline=True)
comment(0xB7CD, "Loop for 3 bytes", inline=True)
comment(0xB7CF, "Flush channel ensure buffers", inline=True)
comment(0xB7D2, "Execute multi-sector disc command", inline=True)
comment(0xB7D5, "Restore saved drive number", inline=True)
comment(0xB7D8, "Set as current drive", inline=True)
comment(0xB7DB, "A=&FF: mark saved drive as unused", inline=True)
comment(0xB7DD, "Store in saved drive slot", inline=True)
comment(0xB7E0, "Mark alt workspace as unused", inline=True)
comment(0xB7E3, "Check for remaining buffered bytes", inline=True)
comment(0xB7E6, "Non-zero: more bytes in buffer", inline=True)
comment(0xB7E8, "Zero: finish via save and return", inline=True)
comment(0xB7EB, "Get channel index", inline=True)
comment(0xB7ED, "Clear carry for sector addition", inline=True)
comment(0xB7EE, "Get channel start sector low", inline=True)
comment(0xB7F1, "Add remaining PTR low", inline=True)
comment(0xB7F4, "Store result sector low", inline=True)
comment(0xB7F7, "Get channel start sector mid", inline=True)
comment(0xB7FA, "Add remaining PTR mid", inline=True)
comment(0xB7FD, "Store result sector mid", inline=True)
comment(0xB800, "Get channel start sector+drive", inline=True)
comment(0xB803, "Add remaining PTR high", inline=True)
comment(0xB806, "Store result sector high", inline=True)
comment(0xB809, "A=2: compare against function code", inline=True)
comment(0xB80B, "C set if write, clear if read", inline=True)
comment(0xB80E, "A=&80: base disc command", inline=True)
comment(0xB810, "Rotate C to form read/write command", inline=True)
comment(0xB811, "Find/load buffer for remaining sector", inline=True)
comment(0xB814, "A=0: clear start position", inline=True)
comment(0xB816, "Store start at beginning of sector", inline=True)
comment(0xB819, "Get bytes remaining in buffer", inline=True)
comment(0xB81C, "Store as transfer end position", inline=True)
comment(0xB81F, "Transfer remaining bytes in sector", inline=True)
comment(0xB822, "Finish via save and return", inline=True)

# sub_cb825 - set up Tube/direct output buffer for OSGBPB A=5-8
# Claims Tube if address is in second processor space,
# then sets up (zp_b2) as the output pointer.
comment(0xB825, "Tube in use (bit 7 of flags)?", inline=True)
comment(0xB827, "No Tube: skip to buffer setup", inline=True)
comment(0xB829, "Get output address byte 3", inline=True)
comment(0xB82C, "Address < &FE00?", inline=True)
comment(0xB82E, "Yes: second processor, claim Tube", inline=True)
comment(0xB830, "Get output address byte 4", inline=True)
comment(0xB833, "Address = &FFxx (host memory)?", inline=True)
comment(0xB835, "Yes: skip Tube claim", inline=True)
comment(0xB837, "Save flags for restore after Tube", inline=True)
comment(0xB838, "Disable interrupts for Tube claim", inline=True)
comment(0xB839, "Claim Tube for transfer", inline=True)
comment(0xB83C, "Set bit 6: Tube data transfer active", inline=True)
comment(0xB83E, "OR with &40 flag", inline=True)
comment(0xB840, "Store updated flags", inline=True)
comment(0xB842, "A=1: Tube read transfer type", inline=True)
comment(0xB844, "X=&B8: Tube address workspace low", inline=True)
comment(0xB846, "Y=&10: Tube address workspace high", inline=True)
comment(0xB848, "Start Tube transfer", inline=True)
comment(0xB84B, "Restore flags (re-enable interrupts)", inline=True)
comment(0xB84C, "A=0: clear output byte counter", inline=True)
comment(0xB84E, "Store zero in output byte counter", inline=True)
comment(0xB850, "Get output address low byte", inline=True)
comment(0xB853, "Store in output pointer low", inline=True)
comment(0xB855, "Get output address high byte", inline=True)
comment(0xB858, "Store in output pointer high", inline=True)
comment(0xB85A, "Return (buffer ready)", inline=True)

# cb85b - output one byte to user buffer or Tube
# Writes A to the OSGBPB output destination. If Tube
# is active (V flag set), writes to Tube R4. Otherwise
# writes via (zp_b2) indirect and advances the pointer.
comment(0xB85B, "Tube active (V flag)?", inline=True)
comment(0xB85D, "No: write to host memory", inline=True)
comment(0xB85F, "Write byte to Tube R3 data register", inline=True)
comment(0xB862, "Return", inline=True)
comment(0xB863, "Save Y (caller's index)", inline=True)
comment(0xB865, "Get output byte counter as offset", inline=True)
comment(0xB867, "Store byte at (zp_b2)+offset", inline=True)
comment(0xB869, "Increment output byte counter", inline=True)
comment(0xB86B, "No page crossing: restore Y", inline=True)
comment(0xB86D, "Page crossed: increment pointer high", inline=True)
comment(0xB86F, "Restore Y (caller's index)", inline=True)
comment(0xB871, "Return", inline=True)

# sub_cb872 - output 10-byte directory entry name
# Writes the name length byte then 10 name characters
# from (zp_b4), replacing control chars with spaces.
comment(0xB872, "A=&0A: name is 10 bytes long", inline=True)
comment(0xB874, "Output name length byte", inline=True)
comment(0xB877, "Set carry for first iteration", inline=True)
comment(0xB878, "X=9: countdown for 10 name bytes", inline=True)
comment(0xB87A, "Y=&FF: will increment to 0 first", inline=True)
comment(0xB87C, "Next name byte position", inline=True)
comment(0xB87D, "C clear from prev: skip fetch", inline=True)
comment(0xB87F, "Get name byte from entry", inline=True)
comment(0xB881, "Strip bit 7 (attribute flags)", inline=True)
comment(0xB883, "Printable character (>= '!')?", inline=True)
comment(0xB885, "Yes: output as-is", inline=True)
comment(0xB887, "Control char: replace with space", inline=True)
comment(0xB889, "Output character to buffer/Tube", inline=True)
comment(0xB88C, "Next character", inline=True)
comment(0xB88D, "Loop for 10 characters", inline=True)
comment(0xB88F, "Return", inline=True)

# OSGBPB A=5-8 dispatch (&B890)
# Dispatches to the handler for the OSGBPB function.
# A=5: read dir title + boot option + drive
# A=6: read CSD name
# A=7: read library name
# A=8: read filenames from CSD
comment(0xB890, "Subtract 5 to get sub-function 0-3", inline=True)
comment(0xB892, "Transfer to Y for dispatch", inline=True)
comment(0xB893, "Y=0 (A=5): read title/boot/drive", inline=True)
comment(0xB895, "Decrement for next check", inline=True)
comment(0xB896, "Y=0 (A=6): read CSD name", inline=True)
comment(0xB898, "Decrement for next check", inline=True)
comment(0xB899, "Y=0 (A=7): read library name", inline=True)
comment(0xB89B, "Decrement for next check", inline=True)
comment(0xB89C, "Y!=0: invalid sub-function, exit", inline=True)
comment(0xB89E, "A=8: read filenames from CSD", inline=True)

# A=5: read directory title, boot option, drive (&B8A1)
comment(0xB8A1, "Set up output buffer/Tube", inline=True)
comment(0xB8A4, "Y=&FF: will increment to 0 first", inline=True)
comment(0xB8A6, "Next title byte", inline=True)
comment(0xB8A7, "Get directory title character", inline=True)
comment(0xB8AA, "Strip bit 7", inline=True)
comment(0xB8AC, "Printable (>= space)?", inline=True)
comment(0xB8AE, "Control char: end of title", inline=True)
comment(0xB8B0, "Reached max 19 chars?", inline=True)
comment(0xB8B2, "No: continue scanning title", inline=True)
comment(0xB8B4, "Output title length byte", inline=True)
comment(0xB8B5, "Write length to buffer/Tube", inline=True)
comment(0xB8B8, "Y=&FF: will increment to 0 first", inline=True)
comment(0xB8BA, "Next title byte", inline=True)
comment(0xB8BB, "Get directory title character", inline=True)
comment(0xB8BE, "Strip bit 7", inline=True)
comment(0xB8C0, "Printable (>= space)?", inline=True)
comment(0xB8C2, "Control char: done outputting title", inline=True)
comment(0xB8C4, "Output title character", inline=True)
comment(0xB8C7, "Reached max 19 chars?", inline=True)
comment(0xB8C9, "No: continue outputting", inline=True)
comment(0xB8CB, "Get boot option from FSM sector 1", inline=True)
comment(0xB8CE, "Output boot option byte", inline=True)
comment(0xB8D1, "Get current drive number", inline=True)
comment(0xB8D4, "Shift drive into low 3 bits", inline=True)
comment(0xB8D5, "Second shift", inline=True)
comment(0xB8D6, "Third shift", inline=True)
comment(0xB8D7, "Fourth shift (now in bits 0-2)", inline=True)
comment(0xB8D8, "Output drive number byte", inline=True)

# cb8db - clean up after A=5-8 and return (&B8DB)
comment(0xB8DB, "Release Tube if in use", inline=True)
comment(0xB8DE, "Return via OSGBPB exit path", inline=True)

# A=6: read CSD name (&B8E1)
comment(0xB8E1, "Set up output buffer/Tube", inline=True)
comment(0xB8E4, "A=1: drive prefix is 1 char long", inline=True)
comment(0xB8E6, "Output drive prefix length", inline=True)
comment(0xB8E9, "Get current drive number", inline=True)
comment(0xB8EC, "Convert drive to ASCII digit", inline=True)
comment(0xB8EF, "A=0: CSD name starts at offset 0", inline=True)
comment(0xB8F1, "Store CSD name pointer low", inline=True)
comment(0xB8F3, "A=&11: CSD name is at &1100", inline=True)
comment(0xB8F5, "Store CSD name pointer high", inline=True)
comment(0xB8F7, "Output 10-byte CSD directory name", inline=True)
comment(0xB8FA, "Exit via cleanup", inline=True)

# sub_cb8fc - convert drive number to ASCII digit
# Shifts A left 4 times and adds &30 to produce an
# ASCII digit representing the drive number.
comment(0xB8FC, "Shift drive into high nibble", inline=True)
comment(0xB8FD, "Continue shift", inline=True)
comment(0xB8FE, "Continue shift", inline=True)
comment(0xB8FF, "Continue shift (now in bits 4-7)", inline=True)
comment(0xB900, "Add &30 for ASCII '0'", inline=True)
comment(0xB902, "Output via cb85b", inline=True)

# A=7: read library name (&B905)
comment(0xB905, "Set up output buffer/Tube", inline=True)
comment(0xB908, "A=1: drive prefix is 1 char long", inline=True)
comment(0xB90A, "Output drive prefix length", inline=True)
comment(0xB90D, "Get library drive number", inline=True)
comment(0xB910, "Convert drive to ASCII digit", inline=True)
comment(0xB913, "A=&0A: library name at offset &0A", inline=True)
comment(0xB915, "Store library name pointer low", inline=True)
comment(0xB917, "A=&11: library name is at &110A", inline=True)
comment(0xB919, "Store library name pointer high", inline=True)
comment(0xB91B, "Output 10-byte library dir name", inline=True)
comment(0xB91E, "Exit via cleanup", inline=True)

# A=8: read filenames from CSD (&B920)
# Writes directory entry names to the output buffer,
# starting from the entry index in the control block.
# Updates the control block with remaining count and
# the directory sequence number for change detection.
comment(0xB920, "Set up output buffer/Tube", inline=True)
comment(0xB923, "Y=0: clear result counter", inline=True)
comment(0xB925, "Clear result file count", inline=True)
comment(0xB928, "Get directory sequence number", inline=True)
comment(0xB92B, "Store in control block byte 0", inline=True)
comment(0xB92D, "Y=5: get requested count from block", inline=True)
comment(0xB92F, "Get requested entry count", inline=True)
comment(0xB931, "Store as entries remaining", inline=True)
comment(0xB933, "Zero entries requested: done", inline=True)
comment(0xB935, "Y=9: get start index from block", inline=True)
comment(0xB937, "Get starting entry index", inline=True)
comment(0xB939, "Store as current entry counter", inline=True)
comment(0xB93B, "Index >= 47? Past max entries", inline=True)
comment(0xB93D, "Yes: exit (no more entries)", inline=True)
comment(0xB93F, "Transfer index to X for loop", inline=True)
comment(0xB940, "Clear carry for pointer arithmetic", inline=True)
comment(0xB941, "A=5: first entry at offset &1205", inline=True)
comment(0xB943, "Y=&12: directory buffer page", inline=True)
comment(0xB945, "Decrement entries to skip", inline=True)
comment(0xB946, "Skipped enough: start reading", inline=True)
comment(0xB948, "Add &1A (26 bytes per dir entry)", inline=True)
comment(0xB94A, "No page crossing: continue", inline=True)
comment(0xB94C, "Page crossing: increment page", inline=True)
comment(0xB94D, "Clear carry for next addition", inline=True)
comment(0xB94E, "Continue skipping entries", inline=True)
comment(0xB950, "Store entry pointer high", inline=True)
comment(0xB952, "Store entry pointer low", inline=True)
comment(0xB954, "Y=0: check first byte of entry", inline=True)
comment(0xB956, "Get entry name byte 0", inline=True)
comment(0xB958, "Store as non-zero check for output", inline=True)
comment(0xB95B, "Zero: end of directory entries", inline=True)
comment(0xB95D, "Output 10-byte entry name", inline=True)
comment(0xB960, "Get entry pointer low", inline=True)
comment(0xB962, "Clear carry for addition", inline=True)
comment(0xB963, "Add &1A to advance to next entry", inline=True)
comment(0xB965, "Store updated entry pointer low", inline=True)
comment(0xB967, "No page crossing", inline=True)
comment(0xB969, "Page crossing: increment high byte", inline=True)
comment(0xB96B, "Increment current entry index", inline=True)
comment(0xB96D, "Decrement remaining count", inline=True)
comment(0xB96F, "More entries to read: continue", inline=True)
comment(0xB971, "Y=5: update remaining count in block", inline=True)
comment(0xB973, "Get remaining entries count", inline=True)
comment(0xB975, "Store in control block byte 5", inline=True)
comment(0xB977, "Y=9: update current index in block", inline=True)
comment(0xB979, "Get current entry index", inline=True)
comment(0xB97B, "Store in control block byte 9", inline=True)
comment(0xB97D, "Exit via cleanup and return", inline=True)

# sub_cb980 - transfer bytes between buffer and user memory
# Copies bytes from position l10b6 to position l10b7
# within the current sector buffer, routing through
# either direct memory, (zp_be) indirect, or the Tube.
comment(0xB980, "Get transfer start position", inline=True)
comment(0xB983, "Compare with end position", inline=True)
comment(0xB986, "Not equal: bytes to transfer", inline=True)
comment(0xB988, "Equal: no bytes to transfer, return", inline=True)
comment(0xB989, "Save flags for Tube check", inline=True)
comment(0xB98A, "Disable interrupts for Tube setup", inline=True)
comment(0xB98B, "Tube in use (bit 7 of flags)?", inline=True)
comment(0xB98D, "No Tube: skip to direct transfer", inline=True)
comment(0xB98F, "Get Tube address byte 3", inline=True)
comment(0xB992, "Address < &FE00?", inline=True)
comment(0xB994, "Yes: Tube address, claim it", inline=True)
comment(0xB996, "Get Tube address byte 4", inline=True)
comment(0xB999, "Address = &FFxx (host memory)?", inline=True)
comment(0xB99B, "Yes: skip Tube claim", inline=True)
comment(0xB99D, "Set bit 6: Tube transfer active", inline=True)
comment(0xB99F, "OR with &40 flag", inline=True)
comment(0xB9A1, "Store updated flags", inline=True)
comment(0xB9A3, "Claim Tube for transfer", inline=True)
comment(0xB9A6, "Get OSGBPB function code", inline=True)
comment(0xB9A9, "C set if A>=3 (read from file)", inline=True)
comment(0xB9AB, "A=0: base for Tube direction", inline=True)
comment(0xB9AD, "Rotate C to set direction bit", inline=True)
comment(0xB9AE, "X=&B8: Tube address workspace low", inline=True)
comment(0xB9B0, "Y=&10: Tube address workspace high", inline=True)
comment(0xB9B2, "Start Tube transfer", inline=True)
comment(0xB9B5, "Restore flags", inline=True)
comment(0xB9B6, "Get data address low", inline=True)
comment(0xB9B9, "Set carry for subtraction", inline=True)
comment(0xB9BA, "Subtract start offset for buffer ptr", inline=True)
comment(0xB9BD, "Store buffer pointer low", inline=True)
comment(0xB9BF, "Get data address high", inline=True)
comment(0xB9C2, "Subtract borrow", inline=True)
comment(0xB9C4, "Store buffer pointer high", inline=True)
comment(0xB9C6, "Get OSGBPB function code", inline=True)
comment(0xB9C9, "C set if A>=3 (read from file)", inline=True)
comment(0xB9CB, "Get start position as byte index", inline=True)
comment(0xB9CE, "Save read/write direction flag", inline=True)

# Byte copy loop (&B9CF)
# Copies one byte per iteration between (zp_be) and
# either (zp_b2) or Tube R4, depending on direction
# and Tube presence. Loops from Y=start to Y=end.
comment(0xB9CF, "Restore direction flag", inline=True)
comment(0xB9D0, "Tube active (V flag)?", inline=True)
comment(0xB9D2, "Yes: use Tube data path", inline=True)
comment(0xB9D4, "C set: reading from file to memory", inline=True)
comment(0xB9D6, "Read: get byte from sector buffer", inline=True)
comment(0xB9D8, "Write to user memory", inline=True)
comment(0xB9DA, "Always branch to advance", inline=True)
comment(0xB9DC, "Write: get byte from user memory", inline=True)
comment(0xB9DE, "Store in sector buffer", inline=True)
comment(0xB9E0, "Always branch to advance", inline=True)
comment(0xB9E2, "Tube: delay for synchronisation", inline=True)
comment(0xB9E5, "C clear: writing to file from Tube", inline=True)
comment(0xB9E7, "Read file: get byte from buffer", inline=True)
comment(0xB9E9, "Write to Tube R4", inline=True)
comment(0xB9EC, "Always branch to advance", inline=True)
comment(0xB9EE, "Write file: read byte from Tube R4", inline=True)
comment(0xB9F1, "Store in sector buffer", inline=True)
comment(0xB9F3, "Next byte position", inline=True)
comment(0xB9F4, "Save direction flag for next byte", inline=True)
comment(0xB9F5, "Reached end position?", inline=True)
comment(0xB9F8, "No: continue copying", inline=True)
comment(0xB9FA, "Restore flags", inline=True)
comment(0xB9FB, "Release Tube and return", inline=True)

# tube_start_xfer (&81F0) - already commented in SCSI section
# The tube_start_xfer_sei and tube_start_xfer routines at
# &81EF-&81FB are already fully commented above.

# osbput_handler (&B08F)
# Writes a byte to an open file at the current PTR position.
# Checks the file is open for writing, manages the buffer,
# and advances PTR. If PTR passes EXT, extends the file.
comment(0xB08F, "Save X register", inline=True)
comment(0xB091, "Save byte to write on stack", inline=True)
comment(0xB092, "Validate file handle in Y", inline=True)
comment(0xB095, "Clear modification flag", inline=True)
comment(0xB09A, "Transfer channel flags to Y", inline=True)
comment(0xB09B, "Bit 7 set: file is writable", inline=True)
comment(0xB0B5, "Get channel flags", inline=True)
comment(0xB0B8, "Isolate buffer state bits (0-2)", inline=True)
comment(0xB0BA, "State >= 6: buffer dirty, ready", inline=True)
comment(0xB0BE, "State = 3: buffer clean, skip load", inline=True)
comment(0xB0C2, "Compute PTR+1 to check if extending", inline=True)

# osfind_handler (&B1B6)
# A=0: close file (Y=handle, or Y=0 for all)
# A=&40: open for input (reading)
# A=&80: open for output (writing)
# A=&C0: open for random access
comment(0xB1B6, "Save registers for later restore", inline=True)
comment(0xB1B9, "Save X in OSFILE block as filename", inline=True)
comment(0xB1BC, "Filename pointer low = X", inline=True)
comment(0xB1BE, "Save Y for close channel", inline=True)
comment(0xB1C0, "Y also to OSFILE block + filename hi", inline=True)
comment(0xB1C5, "Filename pointer high = Y", inline=True)
comment(0xB1C7, "Isolate open mode (bits 6-7)", inline=True)
comment(0xB1C9, "Y=0: clear current channel", inline=True)
comment(0xB1CE, "Transfer mode to Y", inline=True)
comment(0xB1CF, "A!=0: open file", inline=True)
comment(0xB1D1, "A=0: close file(s)", inline=True)
comment(0xB1D4, "Check for stored EXEC handle", inline=True)
comment(0xB1D7, "No stored handle: normal open", inline=True)
comment(0xB1D9, "Clear stored EXEC handle", inline=True)
comment(0xB1DE, "Return with stored handle in Y", inline=True)
comment(0xB1E1, "X=9: scan channels for empty slot", inline=True)
comment(0xB1E3, "Get channel flags", inline=True)
comment(0xB1E6, "Flags=0: channel is free", inline=True)
comment(0xB1E8, "Try next channel", inline=True)
comment(0xB1E9, "Loop for all 10 channels", inline=True)

# star_remove (&9109)
# Removes a file or empty directory from the catalogue.
# Checks against CSD, library, and previous directory.
comment(0x9109, "Skip leading spaces in filename", inline=True)
comment(0x910C, "Save filename address in OSFILE blk", inline=True)
comment(0x9116, "Point (&B8) to OSFILE control block", inline=True)
comment(0x911E, "Search directory for the file", inline=True)
comment(0x9121, "Found? Proceed to delete", inline=True)
comment(0x9123, "Not found: A=0 (no error)", inline=True)
comment(0x9125, "Save workspace and return", inline=True)
comment(0x9128, "Check if file has open channels", inline=True)
comment(0x912B, "Y=3: check access byte", inline=True)
comment(0x912D, "Get access/attribute byte", inline=True)
comment(0x912F, "Bit 7 clear: regular file, skip", inline=True)
comment(0x9131, "Directory: check if empty", inline=True)
comment(0x9133, "Save CSD sector to temp workspace", inline=True)
comment(0x913C, "Mark workspace as not saved", inline=True)
comment(0x9144, "Load the subdirectory to check", inline=True)
comment(0x9147, "Is first entry empty (dir empty)?", inline=True)
comment(0x914B, "Restore CSD and directory", inline=True)
comment(0x9150, "Restore saved CSD sector", inline=True)
comment(0x915A, "Directory was empty: proceed", inline=True)
comment(0x916E, "Get file size from directory entry", inline=True)
comment(0x9172, "Y=&12: length bytes offset", inline=True)
comment(0x9174, "Calculate number of sectors", inline=True)
comment(0x9181, "Y=&18: get start sector", inline=True)
comment(0x9185, "Copy start sector to workspace", inline=True)
comment(0x9190, "Check access byte for directory", inline=True)
comment(0x9192, "Not a directory: skip to delete", inline=True)
comment(0x9194, "Get saved drive", inline=True)
comment(0x9199, "Not set? Check CSD", inline=True)
comment(0x919B, "Same as current drive?", inline=True)
comment(0x919E, "No, skip CSD check", inline=True)
comment(0x91A2, "Compare sector with CSD sector", inline=True)
comment(0x91C2, "Check if it's the library dir", inline=True)
comment(0x91CA, "Compare sector with lib sector", inline=True)
comment(0x91F0, "Check if it's the previous dir", inline=True)
comment(0x91F8, "Compare sector with prev dir sector", inline=True)
comment(0x9200, "Different: skip", inline=True)
comment(0x9205, "Reset previous dir to root (sector 2)", inline=True)
comment(0x9176, "Next length byte", inline=True)
comment(0x9177, "Add carry from previous byte", inline=True)
comment(0x9179, "Add entry length byte", inline=True)
comment(0x917B, "Store sector count in workspace", inline=True)
comment(0x91AA, "Next byte in CSD comparison", inline=True)
comment(0x91AB, "Loop for 3 bytes", inline=True)
comment(0x91CC, "Compare sector with lib sector byte", inline=True)
comment(0x91D2, "Mismatch: not the library dir", inline=True)
comment(0x91D4, "Next byte in library comparison", inline=True)
comment(0x9202, "Next byte in prev dir comparison", inline=True)
comment(0x9203, "Loop for 3 bytes", inline=True)
comment(0x922F, "Check if past end of entries (&16xx)", inline=True)
comment(0x9231, "High byte should be &16", inline=True)
comment(0x9233, "Not past end: continue copying", inline=True)
comment(0x9212, "Remove entry from directory", inline=True)
comment(0x9214, "Y=4: check lock bit", inline=True)
comment(0x9216, "Bit 7 set: directory, skip lock chk", inline=True)
comment(0x9218, "Check file is not locked", inline=True)
comment(0x921B, "Y=&1A: offset to next entry", inline=True)
comment(0x921F, "Copy next entry over this one", inline=True)
comment(0x9221, "Store in current position", inline=True)
comment(0x9223, "Advance pointer", inline=True)
comment(0x922B, "Low byte = &BB? (dir footer boundary)", inline=True)
comment(0x9235, "Release the file's disc space", inline=True)
comment(0x9238, "Write modified directory to disc", inline=True)
comment(0x923B, "Save workspace and return", inline=True)

# check_open (&8D21)
# Scans all 10 channels to see if any files are open on
# the current drive with a matching sector address.
comment(0x8D21, "X=9: check all 10 channels", inline=True)
comment(0x8D23, "Get channel flags", inline=True)
comment(0x8D26, "Channel not open? Skip", inline=True)
comment(0x8D28, "Get channel's drive number", inline=True)
comment(0x8D2B, "Isolate drive bits (top 3)", inline=True)
comment(0x8D2D, "Compare with current drive", inline=True)
comment(0x8D30, "Different drive? Skip", inline=True)
comment(0x8D32, "Compare sector address byte", inline=True)
comment(0x8D35, "With target sector", inline=True)
comment(0x8D38, "No match? Skip", inline=True)
comment(0x8D3A, "Compare sector mid byte", inline=True)
comment(0x8D3D, "With target sector mid", inline=True)
comment(0x8D40, "No match? Skip", inline=True)
comment(0x8D42, "Compare sector high byte", inline=True)
comment(0x8D45, "With target sector high", inline=True)
comment(0x8D48, "No match? Skip", inline=True)
comment(0x8D4A, "Y=&19: compare sequence number", inline=True)
comment(0x8D4C, "Get entry sequence from dir", inline=True)
comment(0x8D4E, "Compare with channel's sequence", inline=True)
comment(0x8D51, "Mismatch: not the same file", inline=True)
comment(0x8D69, "Next channel", inline=True)
comment(0x8D6A, "Loop for all 10 channels", inline=True)
comment(0x8D6C, "X=1: no conflict found", inline=True)
comment(0x8D6D, "Return (X=1 = no conflict)", inline=True)

# sub_c8d6e - check for wildcards in filename
comment(0x8D6E, "Y=0: scan filename", inline=True)
comment(0x8D73, "Non-terminator: check for wildcards", inline=True)
comment(0x8D75, "Is it '.'?", inline=True)
comment(0x8D77, "Dot: wild cards error", inline=True)
comment(0x8D79, "Return (no wildcards)", inline=True)
comment(0x8D7A, "Is it ':'?", inline=True)
comment(0x8D7C, "No: check path components", inline=True)
comment(0x8D7E, "Skip past ':D' drive specifier", inline=True)
comment(0x8D7F, "Skip past drive number", inline=True)
comment(0x8D83, "Non-zero: wild cards error", inline=True)
comment(0x8D85, "Is it '.'?", inline=True)
comment(0x8D87, "No dot after drive: return", inline=True)
comment(0x8D89, "Skip past dot", inline=True)
comment(0x8D8A, "Get next character", inline=True)
comment(0x8D8D, "Strip to check for '$'", inline=True)
comment(0x8D8F, "Is it '$' (root)?", inline=True)
comment(0x8D91, "Yes: continue past root specifier", inline=True)
comment(0x8D93, "Get next path character", inline=True)
comment(0x8D96, "Is it '^' (parent)?", inline=True)
comment(0x8D98, "Yes: skip past it", inline=True)
comment(0x8D9A, "Is it '@' (current)?", inline=True)
comment(0x8D9C, "No: check for wildcards in name", inline=True)
comment(0x8D9E, "Skip past ^ or @ specifier", inline=True)
comment(0x8DA2, "Non-terminator: wild cards error", inline=True)
comment(0x8DA4, "Is it '.'?", inline=True)
comment(0x8DA6, "No dot: return", inline=True)
comment(0x8DA8, "Skip past dot", inline=True)
comment(0x8DA9, "Continue scanning", inline=True)
comment(0x8DAE, "Terminator: check for dot", inline=True)
comment(0x8DB0, "X=5: check against 6 special chars", inline=True)
comment(0x8DB2, "Compare with special char table", inline=True)
comment(0x8DB5, "Match: wild cards error", inline=True)
comment(0x8DB7, "Next special char", inline=True)
comment(0x8DB8, "Loop for 6 chars", inline=True)
comment(0x8DBA, "Next filename character", inline=True)
comment(0x8DBB, "Continue scanning", inline=True)

# sub_c8dbd - set up GSINIT for pathname parsing
comment(0x8DBD, "Save text pointer low", inline=True)
comment(0x8DC0, "Save text pointer high", inline=True)
comment(0x8DC2, "Push on stack", inline=True)
comment(0x8DCE, "Restore text pointer high", inline=True)
comment(0x8DD1, "Restore text pointer low", inline=True)

# sub_c8dd6 - get character from current position
comment(0x8DD6, "Get character at (&B4),Y", inline=True)

# sub_c8df3 / sub_c8df6 - prepare for new directory entry
comment(0x8DF3, "A=&FF: mark saved drive as unset", inline=True)
comment(0x8DF6, "Ensure directory integrity", inline=True)
comment(0x8E01, "Get name and compare", inline=True)
comment(0x8E08, "Clear carry for addition", inline=True)
comment(0x8E09, "Add 26 bytes", inline=True)
comment(0x8E0B, "Store updated pointer low", inline=True)
comment(0x8E0D, "No page crossing", inline=True)
comment(0x8E0F, "Increment page", inline=True)
comment(0x8E11, "Continue searching", inline=True)
comment(0x8E15, "Compare pointer with &16B1", inline=True)
comment(0x8E19, "Below limit: slot found", inline=True)

# sub_c8e6f - allocate space and create entry
comment(0x8E6F, "Get OSFILE block pointer low", inline=True)
comment(0x8E71, "Store in (&B8)", inline=True)
comment(0x8E73, "Get OSFILE block pointer high", inline=True)
comment(0x8E75, "Store in (&B9)", inline=True)
comment(0x8E77, "Y=2: copy 3-byte start sector", inline=True)
comment(0x8E79, "Get start sector byte from entry", inline=True)
comment(0x8E7F, "Next byte (decreasing Y)", inline=True)
comment(0x8E85, "Compare with 1 (round up sectors)", inline=True)

# sub_c8e8b - copy file metadata to new entry
comment(0x8E8B, "Y=&11: copy filename and attributes", inline=True)
comment(0x8E8D, "Get name byte from workspace", inline=True)
comment(0x8E92, "Next byte", inline=True)
comment(0x8E93, "Loop for 10 bytes", inline=True)
comment(0x8E95, "Increment dir sequence number", inline=True)
comment(0x8E98, "Store updated sequence in header", inline=True)
comment(0x8EA0, "Store sequence in entry", inline=True)

# sub_c8f4c / sub_c8f52 / sub_c8f58 - write entry fields
comment(0x8F4C, "Save (&B6) for restore", inline=True)
comment(0x8F4F, "Save (&B7)", inline=True)
comment(0x8F52, "Y=&0D: copy load/exec/length", inline=True)
comment(0x8F58, "Y=&18: get OSFILE data bytes", inline=True)
comment(0x8F5A, "Get OSFILE block byte", inline=True)
comment(0x8F63, "Next OSFILE byte (decreasing)", inline=True)
comment(0x8F65, "Loop for 12 bytes", inline=True)
comment(0x8F67, "Restore (&B7) from stack", inline=True)
comment(0x8F6F, "X=2: 3 sector bytes", inline=True)
comment(0x8F71, "Get new sector byte from workspace", inline=True)
comment(0x8F74, "Store in directory entry", inline=True)
comment(0x8F7A, "Next workspace byte (decreasing X)", inline=True)
comment(0x8F7D, "Y=4: clear access byte 4", inline=True)

# sub_c8f86 - write directory and update FSM checksums
comment(0x8F86, "Verify directory integrity", inline=True)
comment(0x8F89, "Validate FSM entries", inline=True)
comment(0x8F8C, "X=&0A: copy 11 template bytes", inline=True)
comment(0x8F8E, "Get disc op template byte from ROM", inline=True)
comment(0x8F91, "Store in disc op workspace", inline=True)
comment(0x8F94, "Next template byte", inline=True)
comment(0x8F97, "Patch to write command (&0A)", inline=True)
comment(0x8F9C, "Get CSD sector low", inline=True)
comment(0x8FA8, "Get CSD sector high", inline=True)
comment(0x8FAB, "Store in disc op sector high", inline=True)
comment(0x8FAE, "Write directory to disc", inline=True)
comment(0x8FB1, "Get current drive", inline=True)

# Update disc ID and FSM checksums after directory write
comment(0x8FB4, "Get drive slot index in X", inline=True)
comment(0x8FB7, "Cache disc ID high in workspace", inline=True)
comment(0x8FBD, "Read VIA T1 counter as new disc ID low", inline=True)
comment(0x8FC0, "Cache disc ID low in workspace", inline=True)
comment(0x8FC6, "Calculate FSM checksums", inline=True)
comment(0x8FC9, "Store sector 0 checksum", inline=True)
comment(0x8FCC, "Store sector 1 checksum", inline=True)
comment(0x8FD1, "Write FSM sectors to disc", inline=True)
comment(0x8FDA, "Return", inline=True)

# sub_c8fdf - search directory for file
# check_open remaining items - scattered inner loops
comment(0x8DCC, "Is it '.'?", inline=True)
comment(0x8DD0, "Decrement index", inline=True)
comment(0x8DD5, "Return", inline=True)
comment(0x8DDB, "Wild cards found: Bad name error", inline=True)
comment(0x8E00, "Next entry byte", inline=True)
comment(0x8E14, "Back up one entry position", inline=True)
comment(0x8E18, "Return (slot found)", inline=True)
comment(0x8E1C, "Exactly at limit: dir full", inline=True)

# sub_c8e2b - shift entries to make room for new one
comment(0x8E2B, "Save text pointer low", inline=True)
comment(0x8E2D, "Store in workspace", inline=True)
comment(0x8E30, "Save text pointer high", inline=True)
comment(0x8E32, "Store in workspace", inline=True)
comment(0x8E35, "Source = &16B1 (last entry area)", inline=True)
comment(0x8E37, "Store pointer low", inline=True)
comment(0x8E39, "Page &16", inline=True)
comment(0x8E3B, "Store pointer high", inline=True)
comment(0x8E3D, "Y=&1A: dest offset (one entry up)", inline=True)
comment(0x8E3F, "X=6: clear 7 bytes of new entry", inline=True)
comment(0x8E41, "A=0: zero fill", inline=True)
comment(0x8E43, "Clear workspace byte", inline=True)
comment(0x8E46, "Next byte", inline=True)
comment(0x8E47, "Loop for 7 bytes", inline=True)
comment(0x8E49, """\
Shift entries up by one position (26 bytes) working
backwards from end of directory towards the insertion
point at (&B6). Opens a 26-byte gap for the new entry.""")
comment(0x8E49, "Get byte from current position", inline=True)
comment(0x8E4B, "Store 26 bytes higher (Y=&1A)", inline=True)
comment(0x8E4D, "Reached insertion point (&B6)?", inline=True)
comment(0x8E4F, "Compare low byte", inline=True)
comment(0x8E51, "Not yet: keep shifting", inline=True)
comment(0x8E53, "Compare high byte", inline=True)
comment(0x8E55, "Match: insertion point reached", inline=True)
comment(0x8E57, "Gap opened: restore text ptr", inline=True)
comment(0x8E59, "Decrement source pointer", inline=True)
comment(0x8E5B, "Low byte non-zero", inline=True)
comment(0x8E5D, "Zero: borrow from high byte", inline=True)
comment(0x8E5F, "Decrement low byte", inline=True)
comment(0x8E61, "Continue shifting backwards", inline=True)
comment(0x8E64, "Restore text pointer low", inline=True)
comment(0x8E67, "Store back in (&B4)", inline=True)
comment(0x8E69, "Restore text pointer high", inline=True)
comment(0x8E6C, "Store back in (&B5)", inline=True)
comment(0x8E6E, "Return", inline=True)

# Entry metadata copy loops
comment(0x8E7D, "A=CR: pad entry name", inline=True)
comment(0x8E83, "Set bit 7 for D attribute", inline=True)
comment(0x8E87, "Next byte", inline=True)
comment(0x8E88, "Loop for all name bytes", inline=True)
comment(0x8E8A, "Return", inline=True)
comment(0x8E97, "Set carry for sector calculation", inline=True)
comment(0x8EA2, "Next byte", inline=True)
comment(0x8EA3, "Decrement counter", inline=True)
comment(0x8EA4, "Loop for required bytes", inline=True)
comment(0x8EA6, "Y=&0A: copy access byte", inline=True)
comment(0x8EA8, "Get OSFILE data byte", inline=True)
comment(0x8EAB, "Store in directory entry", inline=True)
comment(0x8EAD, "Next byte", inline=True)
comment(0x8EAE, "Past length field (Y=&12)?", inline=True)
comment(0x8EB0, "No: continue copying", inline=True)
comment(0x8EB2, "Save (&B6) for entry shifting", inline=True)
comment(0x8EB4, "Push on stack", inline=True)
comment(0x8EB5, "Save (&B7)", inline=True)
comment(0x8EB7, "Push on stack", inline=True)
comment(0x8EB8, "Point to first dir entry (&1205)", inline=True)
comment(0x8EBA, "Store pointer low", inline=True)
comment(0x8EBC, "Page &12", inline=True)
comment(0x8EBE, "Store pointer high", inline=True)
comment(0x8EC0, "Y=0: check entry", inline=True)
comment(0x8EC2, "Get first byte", inline=True)
comment(0x8EC4, "Zero: end of entries, done", inline=True)
comment(0x8EC6, "Y=&19: check sequence number", inline=True)
comment(0x8EC8, "Get entry sequence", inline=True)
comment(0x8ECA, "Compare with dir master sequence", inline=True)
comment(0x8ECD, "Match: needs incrementing", inline=True)
comment(0x8ECF, "Clear carry for entry advance", inline=True)
comment(0x8ED0, "Get pointer low", inline=True)
comment(0x8ED2, "Add 26 bytes per entry", inline=True)
comment(0x8ED4, "Store updated pointer", inline=True)
comment(0x8ED6, "No page crossing: continue", inline=True)
comment(0x8ED8, "Increment page", inline=True)
comment(0x8EDC, "Get master sequence number", inline=True)
comment(0x8EDF, "Clear carry for BCD add", inline=True)
comment(0x8EE0, "Switch to BCD mode", inline=True)
comment(0x8EE1, "Increment sequence (BCD)", inline=True)
comment(0x8EE3, "Back to binary mode", inline=True)
comment(0x8EE4, "Store updated sequence in footer", inline=True)
comment(0x8EE7, "Also store in header", inline=True)
comment(0x8EEA, "Retry from beginning of entries", inline=True)
comment(0x8EED, "Restore (&B7) from stack", inline=True)
comment(0x8EEE, "Store back", inline=True)
comment(0x8EF0, "Restore (&B6) from stack", inline=True)
comment(0x8EF1, "Store back", inline=True)
comment(0x8EF3, "Y=&19: store new sequence in entry", inline=True)
comment(0x8EF5, "Get current master sequence", inline=True)
comment(0x8EF8, "Store in the new entry", inline=True)
comment(0x8EFA, "Result = 1 (file created)", inline=True)
comment(0x8EFC, "Store result code", inline=True)
comment(0x8EFF, "X=4: copy 4 transfer length bytes", inline=True)
comment(0x8F01, "Get transfer count byte", inline=True)
comment(0x8F04, "Copy to disc op result", inline=True)
comment(0x8F07, "Next byte", inline=True)
comment(0x8F08, "Loop for 4 bytes", inline=True)
comment(0x8F0A, "SCSI write command = &0A", inline=True)
comment(0x8F0C, "Store command", inline=True)
comment(0x8F0F, "Clear sector count (use transfer)", inline=True)
comment(0x8F11, "Store zero sector count", inline=True)
comment(0x8F14, "A=0: clear control byte", inline=True)
comment(0x8F16, "Store zero control", inline=True)
comment(0x8F19, "Y=&12: copy 4 length bytes to entry", inline=True)
comment(0x8F1B, "Get length byte from entry", inline=True)
comment(0x8F1D, "Copy to workspace", inline=True)
comment(0x8F20, "Next byte", inline=True)
comment(0x8F21, "Past length field (Y=&16)?", inline=True)
comment(0x8F23, "No: continue", inline=True)
comment(0x8F25, "Y=&12: calculate sector count", inline=True)
comment(0x8F27, "Get length low from entry", inline=True)
comment(0x8F29, "Compare with 1 (round up)", inline=True)
comment(0x8F2B, "X=2: process 3 sector bytes", inline=True)
comment(0x8F2D, "A=0: zero for carry propagation", inline=True)
comment(0x8F2F, "Next length byte", inline=True)
comment(0x8F30, "Add with carry from comparison", inline=True)
comment(0x8F32, "Store in sector workspace", inline=True)
comment(0x8F35, "Next byte", inline=True)
comment(0x8F36, "Loop for 3 bytes", inline=True)
comment(0x8F38, "No overflow: proceed", inline=True)
comment(0x8F3A, "Overflow: Disc full error", inline=True)
comment(0x8F3D, "Y=&16: mark entry sector as &FF", inline=True)
comment(0x8F3F, "A=&FF: temporary marker", inline=True)
comment(0x8F41, "Store &FF in sector low", inline=True)
comment(0x8F44, "Store &FF in sector mid", inline=True)
comment(0x8F47, "Store &FF in sector high", inline=True)
comment(0x8F61, "Next entry byte (decreasing)", inline=True)
comment(0x8F62, "Next workspace byte", inline=True)
comment(0x8F70, "Decrement counter", inline=True)
comment(0x8F73, "Return", inline=True)
comment(0x8F80, "Write directory and update", inline=True)
comment(0x8F83, "Check and write entry", inline=True)
comment(0x8F95, "Loop for template bytes", inline=True)

# Write FSM to disc and clear flags
comment(0x8FCF, "Point to write-FSM template", inline=True)
comment(0x8FD8, "Clear FSM-inconsistent flag", inline=True)
comment(0x8FDC, "A=0: success", inline=True)
comment(0x8FDE, "Return", inline=True)
comment(0x8FE3, "Save A on stack", inline=True)
comment(0x8FE7, "Restore A", inline=True)
comment(0x8FE9, "Return", inline=True)
comment(0x8FFA, "Bad FS map error", inline=True)

# FSM integrity check (&9009-&905C)
comment(0x9009, "Get FSM end-of-list pointer", inline=True)
comment(0x900C, "Empty: return OK", inline=True)
comment(0x900E, "A=0: init check accumulator", inline=True)
comment(0x9010, "OR entry address high byte", inline=True)
comment(0x9013, "OR entry length high byte", inline=True)
comment(0x9016, "Back up one", inline=True)
comment(0x9017, "At entry 0: bad FS map", inline=True)
comment(0x9019, "Back up more", inline=True)
comment(0x901A, "At entry 0: bad FS map", inline=True)
comment(0x901C, "Back up more", inline=True)
comment(0x901D, "Loop for all entries", inline=True)
comment(0x901F, "Check drive bits in accumulator", inline=True)
comment(0x9021, "Non-zero: bad FS map", inline=True)
comment(0x9023, "Get end pointer again", inline=True)
comment(0x9026, "Need at least 2 entries (>= 6)", inline=True)
comment(0x9028, "Not enough: return OK (empty disc)", inline=True)
comment(0x902A, "X=3: check entry ordering", inline=True)
comment(0x902C, "Y=2: compare 3-byte addresses", inline=True)
comment(0x902E, "Clear carry for addition", inline=True)
comment(0x902F, "Get prev entry address byte", inline=True)
comment(0x9032, "Add prev entry length byte", inline=True)
comment(0x9035, "Push result on stack", inline=True)
comment(0x9036, "Next byte", inline=True)
comment(0x9037, "Next comparison byte", inline=True)
comment(0x9038, "Loop for 3 bytes", inline=True)
comment(0x903A, "Carry set: overlap, bad FS map", inline=True)
comment(0x903C, "Y=2: compare prev+size with next", inline=True)
comment(0x903E, "Pop result byte", inline=True)
comment(0x903F, "Back up X", inline=True)
comment(0x9040, "Compare with next entry address", inline=True)
comment(0x9043, "Below: entries are ordered OK", inline=True)
comment(0x9045, "Above: bad ordering, bad FS map", inline=True)
comment(0x9047, "Next comparison byte", inline=True)
comment(0x9048, "Loop for 3 bytes", inline=True)
comment(0x904C, "Discard remaining stack bytes", inline=True)
comment(0x904D, "Back up X", inline=True)
comment(0x904E, "Decrement Y too", inline=True)
comment(0x904F, "More to discard", inline=True)
comment(0x9051, "Push separator", inline=True)
comment(0x9052, "Advance to next entry pair", inline=True)
comment(0x9053, "Continue advancing", inline=True)
comment(0x9054, "Continue advancing", inline=True)
comment(0x9055, "Continue advancing", inline=True)
comment(0x9056, "Past end of list?", inline=True)
comment(0x9059, "No: check next pair", inline=True)
comment(0x905B, "All entries OK: return", inline=True)

# sub_c905c - calculate FSM checksums
comment(0x905C, "Clear carry for checksum", inline=True)
comment(0x905D, "Y=&FF: sum 255 bytes", inline=True)
comment(0x9060, "Add FSM sector 0 byte", inline=True)
comment(0x9063, "Next byte", inline=True)
comment(0x9064, "Loop for 255 bytes", inline=True)
comment(0x9066, "Save sector 0 checksum in X", inline=True)
comment(0x9067, "Y=&FF for sector 1", inline=True)
comment(0x9068, "Transfer to A", inline=True)
comment(0x9069, "Clear carry", inline=True)
comment(0x906A, "Add FSM sector 1 byte", inline=True)
comment(0x906D, "Next byte", inline=True)
comment(0x906E, "Loop for 255 bytes", inline=True)
comment(0x9070, "Return (X=chk0, A=chk1)", inline=True)

# OSFILE write catalogue info (A=1,2,3,4)
comment(0x907C, "Store function code", inline=True)
comment(0x907F, "Find file, check access", inline=True)
comment(0x9082, "Found?", inline=True)
comment(0x9084, "Not found: A=0 return", inline=True)
comment(0x9086, "Return", inline=True)
comment(0x9087, "Get function code", inline=True)
comment(0x908A, "A=3 (write exec addr)?", inline=True)
comment(0x908C, "Yes: skip to exec addr", inline=True)
comment(0x908E, "Y=5: get load addr from OSFILE blk", inline=True)
comment(0x9090, "X=3: copy 4 bytes", inline=True)
comment(0x9092, "Get OSFILE block byte", inline=True)
comment(0x9094, "Store in workspace", inline=True)
comment(0x9097, "Next OSFILE byte", inline=True)
comment(0x9098, "Next workspace byte", inline=True)
comment(0x9099, "Loop for 4 bytes", inline=True)
comment(0x909B, "Y=&0D: store in dir entry load addr", inline=True)
comment(0x909D, "X=3: copy 4 bytes", inline=True)
comment(0x909F, "Get from workspace", inline=True)
comment(0x90A2, "Store in directory entry", inline=True)
comment(0x90A4, "Next entry byte", inline=True)
comment(0x90A5, "Next workspace byte", inline=True)
comment(0x90A6, "Loop for 4 bytes", inline=True)
comment(0x90A8, "Get function code", inline=True)
comment(0x90AB, "A=2 (write load addr only)?", inline=True)
comment(0x90AD, "Yes: skip exec addr, write dir", inline=True)
comment(0x90AF, "Y=9: get exec addr from OSFILE blk", inline=True)
comment(0x90B1, "X=3: copy 4 bytes", inline=True)
comment(0x90B3, "Get OSFILE block byte", inline=True)
comment(0x90B5, "Store in workspace", inline=True)
comment(0x90B8, "Next OSFILE byte", inline=True)
comment(0x90B9, "Next workspace byte", inline=True)
comment(0x90BA, "Loop for 4 bytes", inline=True)
comment(0x90BC, "Y=&11: store in dir entry exec addr", inline=True)
comment(0x90BE, "X=3: copy 4 bytes", inline=True)
comment(0x90C0, "Get from workspace", inline=True)
comment(0x90C3, "Store in directory entry", inline=True)
comment(0x90C5, "Next entry byte", inline=True)
comment(0x90C6, "Next workspace byte", inline=True)
comment(0x90C7, "Loop for 4 bytes", inline=True)
comment(0x90C9, "Get function code again", inline=True)
comment(0x90CC, "X=0 means function was 1 (write all)", inline=True)
comment(0x90CD, "A=1 (write all): continue to access", inline=True)
comment(0x90CF, "Y=&0E: get access byte from OSFILE", inline=True)
comment(0x90D1, "Get access byte from block", inline=True)
comment(0x90D3, "Store in workspace", inline=True)
comment(0x90D6, "Y=3: test directory flag", inline=True)
comment(0x90D8, "Get byte 3 from entry", inline=True)
comment(0x90DA, "Bit 7 clear: file, use owner R,W,L", inline=True)
comment(0x90DC, "Dir: skip owner R (bit 0)", inline=True)
comment(0x90DF, "Dir: skip owner W (bit 1)", inline=True)
comment(0x90E2, "Skip unused bit (bit 2 for file)", inline=True)
comment(0x90E5, "Y=2: start at byte 2 for L bit", inline=True)
comment(0x90E9, "Y=0: start with byte 0", inline=True)
comment(0x90EB, "Get name byte", inline=True)
comment(0x90ED, "Shift out bit 7 (old attribute)", inline=True)
comment(0x90EE, "Shift access bit into carry", inline=True)
comment(0x90F1, "Shift carry into name bit 7", inline=True)
comment(0x90F2, "Store updated name byte", inline=True)
comment(0x90F4, "Next byte", inline=True)
comment(0x90F5, "Past byte 2?", inline=True)
comment(0x90F7, "Y < 2: continue (R then W)", inline=True)
comment(0x90F9, "Y = 2: re-enter for L bit", inline=True)
comment(0x90FB, "Write directory to disc", inline=True)
comment(0x90FE, "Return via catalogue info copy", inline=True)
comment(0x9101, "OSFILE A=4: write attributes only", inline=True)
comment(0x9104, "Found: write access byte", inline=True)
comment(0x9106, "Not found: A=0", inline=True)
comment(0x9108, "Return", inline=True)

comment(0x8FDF, "Parse filename from command line", inline=True)
comment(0x8FE2, "Save flags across FSM validation", inline=True)
comment(0x8FE8, "Restore flags from parse result", inline=True)
comment(0x8FED, "Recalculate FSM checksums", inline=True)
comment(0x8FF0, "Compare sector 1 checksum", inline=True)
comment(0x8FF3, "Mismatch: bad FS map", inline=True)

# floppy_partial_sector (&8B1E)
# Reads a partial sector via floppy for BGET/BPUT operations
# where the transfer doesn't align to a full 256-byte sector.
comment(0x8B1E, "Get sector address high byte", inline=True)
comment(0x8B21, "Combine with current drive", inline=True)
comment(0x8B24, "Store in error sector workspace", inline=True)
comment(0x8B27, "Get sector address mid byte", inline=True)
comment(0x8B2A, "Store in error sector workspace", inline=True)
comment(0x8B2D, "Get sector address low byte", inline=True)
comment(0x8B30, "Store in error sector workspace", inline=True)
comment(0x8B33, "Calculate buffer offset", inline=True)
comment(0x8B36, "Store partial transfer count", inline=True)
comment(0x8B39, "Channel offset to A for buffer calc", inline=True)

# hd_command_partial_sector (&8B41)
comment(0x8B41, "Check zp_flags for hard drive", inline=True)
comment(0x8B44, "Bit 5 clear: floppy, use floppy path", inline=True)
comment(0x8B46, "Select SCSI target", inline=True)

# hd_command_bget_bput_sector (&AAC6)
# Executes a single sector read or write for byte-level
# file I/O (BGET/BPUT) via the SCSI hard drive.
comment(0xAAC6, "Wait if files being ensured", inline=True)

# star_copy (&A81D)
# Copies a file, possibly between different drives.
# Reads source file info, creates destination file using
# OSFILE save, reading sectors from source and writing
# to destination.
comment(0xA81D, "Set up control block pointers", inline=True)
comment(0xA825, "Store source name offset", inline=True)
comment(0xA82F, "Find source file", inline=True)
comment(0xA832, "Found?", inline=True)
comment(0xA834, "Not found: report error", inline=True)
comment(0xA837, "Save directory entry pointer", inline=True)
comment(0xA841, "Save filename pointer", inline=True)
comment(0xA84B, "Y=3: save current directory sector", inline=True)
comment(0xA84D, "Copy CSD sector to workspace", inline=True)
comment(0xA856, "Save workspace state", inline=True)

# star_rename (&A503)
# Parses two path arguments, checks they're on the same drive,
# finds the source file, checks for illegal self-referencing
# renames, then moves/renames the directory entry.
comment(0xA503, "Save first argument pointer", inline=True)
comment(0xA509, "Check for drive specifier", inline=True)
comment(0xA50C, "Parse and validate destination path", inline=True)
comment(0xA50F, "Search for source file", inline=True)
comment(0xA512, "Found?", inline=True)
comment(0xA514, "Not found: report error", inline=True)
comment(0xA517, "Y=3: check if source is directory", inline=True)
comment(0xA51B, "Save workspace state", inline=True)
comment(0xA51E, "Not a directory: skip self-ref check", inline=True)
comment(0xA520, "Restore first argument pointer", inline=True)
comment(0xA52C, "Check for '$' (root specifier)", inline=True)
comment(0xA530, "Is it '$'?", inline=True)
comment(0xA532, "Root: Bad rename error", inline=True)
comment(0xA534, "Scan for '^' in destination path", inline=True)
comment(0xA539, "Is it '^' (parent)?", inline=True)
comment(0xA53B, "Parent ref in dest: Bad rename error", inline=True)
# hd_command_bget_bput_sector (&AAC6) - SCSI single sector I/O
# Sends a 6-byte SCSI command to read or write one sector
# for BGET/BPUT byte-level file operations.
comment(0xAACA, "Start SCSI command phase (Y in cmd)", inline=True)
comment(0xAACD, "Restore command byte from stack", inline=True)
comment(0xAAD1, "Get drive+LUN from channel block", inline=True)
comment(0xAAD4, "Save as current drive info", inline=True)
comment(0xAADA, "Get sector address high", inline=True)
comment(0xAAE0, "Get sector address mid", inline=True)
comment(0xAAE6, "Sector count = 1", inline=True)
comment(0xAAEB, "Control byte = 0", inline=True)
comment(0xAAED, "Send last command byte and return", inline=True)

# sub_caaf0/sub_caaf3 - buffer management for channel I/O
comment(0xAAF0, "Calculate buffer page from channel", inline=True)
comment(0xAAF3, "Ensure channel buffer is allocated", inline=True)
comment(0xAAF6, "Get channel state byte", inline=True)
comment(0xAAF9, "State >= &C0 (dirty write)?", inline=True)
comment(0xAAFB, "No: buffer clean, return", inline=True)
comment(0xAAFD, "Transfer X to A", inline=True)
comment(0xAAFE, "Divide by 4 for channel number", inline=True)
comment(0xAAFF, "Second shift", inline=True)
comment(0xAB00, "Add &17 for buffer page base", inline=True)
comment(0xAB02, "Store as buffer high byte", inline=True)
comment(0xAB04, "Buffer low byte = 0", inline=True)
comment(0xAB06, "Store buffer low byte", inline=True)
comment(0xAB08, "Get channel state", inline=True)
comment(0xAB0B, "Clear bit 6 (dirty flag)", inline=True)
comment(0xAB0D, "Store cleared state", inline=True)
comment(0xAB10, "Isolate channel number bits", inline=True)
comment(0xAB12, "Shift right to get channel index", inline=True)
comment(0xAB13, "OR with &30 to get file handle", inline=True)
comment(0xAB15, "Store file handle for errors", inline=True)
comment(0xAB18, "Get sector address low", inline=True)
comment(0xAB1B, "Store in error sector workspace", inline=True)
comment(0xAB1E, "Get sector address mid", inline=True)
comment(0xAB21, "Store in error sector mid", inline=True)
comment(0xAB24, "Get drive+sector high", inline=True)
comment(0xAB27, "Store in error sector high", inline=True)
comment(0xAB2A, "Flush channel if dirty", inline=True)
comment(0xAB30, "Save channel index", inline=True)
comment(0xAB32, "Check for hard drive", inline=True)
comment(0xAB34, "Bit 5: hard drive present?", inline=True)
comment(0xAB36, "No HD: use floppy", inline=True)
comment(0xAB38, "Get drive number from channel", inline=True)
comment(0xAB3B, "Bit 7 clear: use SCSI hard drive", inline=True)
comment(0xAB3D, "Restore channel index for floppy", inline=True)
comment(0xAB3F, "Execute floppy write sector", inline=True)
comment(0xAB42, "Success? Done", inline=True)
comment(0xAB44, "Decrement retry counter", inline=True)
comment(0xAB46, "More retries: try again", inline=True)
comment(0xAB4B, "Restore channel index for SCSI", inline=True)
comment(0xAB4D, "A=&0A: SCSI write command", inline=True)
comment(0xAB52, "Y=0: data transfer index", inline=True)
comment(0xAB57, "Status OK: continue", inline=True)
comment(0xAB5C, "Decrement retry counter", inline=True)
comment(0xAB5E, "More retries: try write again", inline=True)
comment(0xAB63, "Get byte from buffer", inline=True)
comment(0xAB65, "Write to SCSI data bus", inline=True)
comment(0xAB68, "Next byte", inline=True)
comment(0xAB69, "Loop for 256 bytes", inline=True)
comment(0xAB6B, "Set ensuring flag", inline=True)
comment(0xAB6D, "OR into ADFS flags", inline=True)
comment(0xAB6F, "Store updated flags", inline=True)
comment(0xAB71, "Y=&FF: disable SCSI IRQ", inline=True)
comment(0xAB72, "Write to SCSI IRQ enable register", inline=True)
comment(0xAB75, "Restore channel index", inline=True)
comment(0xAB77, "Return (success)", inline=True)

# svc5_irq (&AB78) - service 5 IRQ handler for SCSI
comment(0xAB78, "Get ADFS flags", inline=True)
comment(0xAB7A, "Check ensuring + HD bits", inline=True)
comment(0xAB7C, "Both set?", inline=True)
comment(0xAB7E, "No: not our interrupt", inline=True)
comment(0xAB80, "Read SCSI status", inline=True)
comment(0xAB83, "Status = &F2 (completion)?", inline=True)
comment(0xAB85, "Yes: handle SCSI completion", inline=True)
comment(0xAB87, "Not ours: A=5 (not claimed)", inline=True)
comment(0xAB89, "Return", inline=True)
comment(0xAB8A, "Save Y", inline=True)
comment(0xAB8B, "Push on stack", inline=True)
comment(0xAB8C, "A=0: clear SCSI IRQ", inline=True)
comment(0xAB8E, "Write to SCSI IRQ enable", inline=True)
comment(0xAB91, "Clear ensuring flag (bit 0)", inline=True)
comment(0xAB93, "Clear carry", inline=True)
comment(0xAB94, "Restore bit 0 cleared", inline=True)
comment(0xAB96, "Read SCSI status byte", inline=True)
comment(0xAB99, "Wait for message phase", inline=True)
comment(0xAB9C, "OR with final status byte", inline=True)
comment(0xAB9F, "Store combined status", inline=True)
comment(0xABA2, "Return to service dispatcher", inline=True)

# sub_caba5 - check for data lost error
comment(0xABA5, "Check for pending data lost error", inline=True)
comment(0xABA8, "Zero: no error, return", inline=True)
comment(0xABAA, "Clear pending error", inline=True)
comment(0xABAC, "Clear error status", inline=True)
comment(0xABAF, "Get file handle for error message", inline=True)

# sub_cabc9 - calculate buffer page from channel
comment(0xABC9, "Save X (channel index)", inline=True)
comment(0xABCA, "Store in workspace", inline=True)
comment(0xABCD, "Divide by 4 for channel number", inline=True)
comment(0xABCE, "Second shift", inline=True)
comment(0xABCF, "Add &17 for buffer page base", inline=True)
comment(0xABD1, "Store as buffer high byte", inline=True)
comment(0xABD3, "Buffer low = 0 (page-aligned)", inline=True)
comment(0xABD5, "Store buffer low", inline=True)
comment(0xABD7, "Return", inline=True)

# sub_cabd8 - find channel in ensure/buffer table
comment(0xABD8, "X=&10: start of channel table", inline=True)
comment(0xABDA, "Store as initial best match", inline=True)
comment(0xABDD, "Transfer A to Y (mode flag)", inline=True)
comment(0xABDE, "Get channel state entry", inline=True)
comment(0xABE1, "Check bit 0 (dirty flag)", inline=True)
comment(0xABE3, "Not dirty: skip", inline=True)
comment(0xABE5, "Update best dirty channel index", inline=True)
comment(0xABE8, "Get channel state", inline=True)
comment(0xABEB, "Bit 7 clear: channel not active", inline=True)
comment(0xABED, "Get channel sector low", inline=True)
comment(0xABF0, "Compare with target sector low", inline=True)
comment(0xABF3, "No match: try next channel", inline=True)
comment(0xABF5, "Get channel sector mid", inline=True)
comment(0xABF8, "Compare with target sector mid", inline=True)
comment(0xABFB, "No match: try next channel", inline=True)
comment(0xABFD, "Get channel drive+sector high", inline=True)
comment(0xAC00, "Compare with target high", inline=True)
comment(0xAC03, "No match: try next channel", inline=True)
comment(0xAC05, "Match: set up buffer address", inline=True)
comment(0xAC08, "Transfer mode flag to A", inline=True)
comment(0xAC09, "Shift right for direction bit", inline=True)
comment(0xAC0A, "Isolate bit 6 (read/write)", inline=True)
comment(0xAC0C, "Merge with channel state", inline=True)
comment(0xAC0F, "Rotate state bits", inline=True)
comment(0xAC10, "Keep top 3 bits", inline=True)
comment(0xAC12, "OR in channel index", inline=True)
comment(0xAC14, "Save flags", inline=True)
comment(0xAC15, "Clear carry for rotate", inline=True)
comment(0xAC16, "Shift left to final position", inline=True)
comment(0xAC17, "Store updated channel state", inline=True)
comment(0xAC1A, "Restore flags", inline=True)
comment(0xAC1B, "C=0: read operation, skip write", inline=True)
comment(0xAC1D, "Y=&10: scan for empty ensure slot", inline=True)
comment(0xAC1F, "Get ensure table entry", inline=True)
comment(0xAC22, "Non-zero: slot in use", inline=True)
comment(0xAC24, "A=1: mark slot as dirty", inline=True)
comment(0xAC26, "Store in ensure table", inline=True)
comment(0xAC2B, "Step back 4 bytes", inline=True)
comment(0xAC2C, "Continue stepping", inline=True)
comment(0xAC2D, "Continue stepping", inline=True)
comment(0xAC2E, "Continue stepping", inline=True)
comment(0xAC2F, "Loop for all ensure entries", inline=True)
comment(0xAC31, "Flush oldest dirty buffer", inline=True)
comment(0xAC34, "Clear bit 0 of channel state", inline=True)
comment(0xAC37, "Set carry", inline=True)
comment(0xAC38, "Set bit 0 (mark as dirty)", inline=True)
comment(0xAC3B, "Advance X past current entry", inline=True)
comment(0xAC3C, "Continue advancing", inline=True)
comment(0xAC3D, "Continue advancing", inline=True)
comment(0xAC3E, "Continue advancing", inline=True)
comment(0xAC3F, "Past end of table (&11)?", inline=True)
comment(0xAC41, "No: continue", inline=True)
comment(0xAC43, "Wrap to start: X=0", inline=True)
comment(0xAC45, "Get channel state at new position", inline=True)
comment(0xAC48, "Shift right to check state", inline=True)
comment(0xAC49, "Empty slot: use it", inline=True)
comment(0xAC4B, "C=0: clean buffer, reuse it", inline=True)
comment(0xAC4D, "Clear carry for rotate back", inline=True)
comment(0xAC4E, "Restore state bits", inline=True)
comment(0xAC4F, "Store updated state", inline=True)
comment(0xAC52, "Flush this buffer to disc", inline=True)
comment(0xAC55, "Flush again (ensure completion)", inline=True)
comment(0xAC58, "Clear dirty bit", inline=True)
comment(0xAC5B, "Set carry", inline=True)
comment(0xAC5C, "Set dirty bit (will be written)", inline=True)
comment(0xAC5F, "Jump to buffer fill", inline=True)
comment(0xAC62, "Step back 4 bytes to prev entry", inline=True)
comment(0xAC63, "Continue stepping", inline=True)
comment(0xAC64, "Continue stepping", inline=True)
comment(0xAC65, "Continue stepping", inline=True)
comment(0xAC66, "Past start: no match found", inline=True)
comment(0xAC68, "Continue scanning from top", inline=True)
comment(0xAC6B, "Get best dirty channel index", inline=True)
comment(0xAC6E, "Get target sector low", inline=True)
comment(0xAC71, "Store as channel sector low", inline=True)
comment(0xAC74, "Also store in error workspace", inline=True)
comment(0xAC77, "Get target sector mid", inline=True)
comment(0xAC7A, "Store as channel sector mid", inline=True)
comment(0xAC7D, "Store in error workspace", inline=True)
comment(0xAC80, "Get target drive+sector high", inline=True)
comment(0xAC83, "Store as channel drive+sector", inline=True)
comment(0xAC86, "Store in error workspace", inline=True)
comment(0xAC89, "Calculate buffer page for channel", inline=True)
comment(0xAC8C, "Get drive+sector high for read", inline=True)
comment(0xAC8F, "Set up disc read control block", inline=True)
comment(0xAC92, "Save Y (buffer high)", inline=True)
comment(0xAC94, "Save X (buffer low)", inline=True)
comment(0xAC99, "Restore buffer pointer", inline=True)
comment(0xAC9B, "Check for hard drive", inline=True)
comment(0xAC9D, "Bit 5: hard drive present?", inline=True)
comment(0xAC9F, "No: use floppy", inline=True)
comment(0xACA1, "Get drive from channel", inline=True)
comment(0xACA4, "Bit 7 clear: use SCSI", inline=True)
comment(0xACA6, "Floppy: read sector to buffer", inline=True)
comment(0xACA9, "Success? Done", inline=True)
comment(0xACAB, "Decrement retry counter", inline=True)
comment(0xACAD, "More retries: try again", inline=True)
comment(0xACB2, "SCSI: read command = 8", inline=True)
comment(0xACBA, "Status phase: read complete", inline=True)
comment(0xACBC, "Y=0: read data byte index", inline=True)
comment(0xACBE, "Read byte from SCSI data bus", inline=True)
comment(0xACC1, "Store in buffer", inline=True)
comment(0xACC3, "Next byte", inline=True)
comment(0xACC4, "Loop for 256 bytes", inline=True)
comment(0xACC9, "Error: retry", inline=True)
comment(0xACCB, "Restore buffer pointer X", inline=True)
comment(0xACCD, "Restore buffer pointer Y", inline=True)
comment(0xACCF, "A=&81: buffer valid + dirty", inline=True)
comment(0xACD1, "Store as channel state", inline=True)
comment(0xACD4, "Jump to set up buffer access", inline=True)

# sub_cacd7 - find dirty channel for flush
comment(0xACD7, "X=&10: start of channel table", inline=True)
comment(0xACD9, "Get channel state", inline=True)
comment(0xACDC, "Bit 0: dirty flag", inline=True)
comment(0xACDE, "Not dirty: done scanning", inline=True)
comment(0xACE0, "Step back 4 bytes", inline=True)
comment(0xACE1, "Continue stepping", inline=True)
comment(0xACE2, "Continue stepping", inline=True)
comment(0xACE3, "Continue stepping", inline=True)
comment(0xACE4, "Loop for all entries", inline=True)
comment(0xACE6, "No dirty buffers: workspace error", inline=True)

# sub_cacf5 - step back in channel table with wraparound
comment(0xACF5, "Step back 4 bytes", inline=True)
comment(0xACF6, "Continue stepping", inline=True)
comment(0xACF7, "Continue stepping", inline=True)
comment(0xACF8, "Continue stepping", inline=True)
comment(0xACF9, "Still in range: return", inline=True)
comment(0xACFB, "Wrap: X=&10 (back to end)", inline=True)
comment(0xACFD, "Return", inline=True)

# floppy_format_track (&BD58) - complete body
# Formats a track: sets up NMI handler, copies format data
# from memory (or via Tube), seeks to track, issues format
# command, then handles multi-sector read/write operations.
comment(0xBD58, "Get format page number", inline=True)
comment(0xBD5B, "Store as NMI buffer high byte", inline=True)
comment(0xBD5E, "A=0: NMI buffer low byte", inline=True)
comment(0xBD60, "Store as NMI buffer low byte", inline=True)
comment(0xBD63, "Set up FDC registers for operation", inline=True)
comment(0xBD66, "Set up FDC command and issue", inline=True)
comment(0xBD69, "Save current track", inline=True)
comment(0xBD6B, "Push on stack", inline=True)
comment(0xBD6C, "Get transfer address low", inline=True)
comment(0xBD6F, "Store as dest address low", inline=True)
comment(0xBD71, "Get transfer address high", inline=True)
comment(0xBD74, "Store as dest address high", inline=True)
comment(0xBD76, "Source address low = 0", inline=True)
comment(0xBD78, "Store source low", inline=True)
comment(0xBD7A, "Get format buffer page", inline=True)
comment(0xBD7D, "Store source high (format data page)", inline=True)
comment(0xBD7F, "Is Tube active?", inline=True)
comment(0xBD81, "No Tube: use direct memory copy", inline=True)
comment(0xBD83, "Y=0: Tube transfer byte index", inline=True)
comment(0xBD85, "Get format data byte from source", inline=True)
comment(0xBD87, "X=7: timing delay loop", inline=True)
comment(0xBD89, "Delay", inline=True)
comment(0xBD8A, "Loop for delay", inline=True)
comment(0xBD8C, "Send byte to Tube R3", inline=True)
comment(0xBD8F, "Next byte", inline=True)
comment(0xBD90, "Transferred all bytes?", inline=True)
comment(0xBD93, "No, continue transfer", inline=True)
comment(0xBD97, "Direct copy: get byte count", inline=True)
comment(0xBD9A, "Adjust for 0-based index", inline=True)
comment(0xBD9B, "Get last byte from source", inline=True)
comment(0xBD9D, "Store at dest", inline=True)
comment(0xBD9F, "Transfer Y to A", inline=True)
comment(0xBDA0, "Loop until all bytes copied", inline=True)
comment(0xBDA2, "Restore saved track", inline=True)
comment(0xBDA3, "Store back as current track", inline=True)
comment(0xBDA5, "Return", inline=True)

# sub_cbda6 onwards - multi-sector floppy read/write
comment(0xBDA6, "Set up FDC registers", inline=True)
comment(0xBDA9, "Get transfer state flags", inline=True)
comment(0xBDAB, "Set bit 6 (multi-sector flag)", inline=True)
comment(0xBDAD, "Store updated state", inline=True)
comment(0xBDAF, "Y=7: get sector address from block", inline=True)
comment(0xBDB1, "Get sector address mid byte", inline=True)
comment(0xBDB3, "Store in NMI workspace", inline=True)
comment(0xBDB6, "Y=8: sector address low", inline=True)
comment(0xBDB7, "Get sector address low", inline=True)
comment(0xBDB9, "Y=9: sector count", inline=True)
comment(0xBDBA, "Clear carry for addition", inline=True)
comment(0xBDBB, "Add sector count to start sector", inline=True)
comment(0xBDBD, "Store end sector in NMI workspace", inline=True)
comment(0xBDC0, "No carry: no wrap", inline=True)
comment(0xBDC2, "Increment mid byte on carry", inline=True)
comment(0xBDC5, "Get end sector mid byte", inline=True)
comment(0xBDC8, "Transfer to X", inline=True)
comment(0xBDC9, "Get end sector low byte", inline=True)
comment(0xBDCC, "Y=&FF: init for divide", inline=True)
comment(0xBDCE, "Divide end sector by 16", inline=True)
comment(0xBDD1, "Remainder = 0?", inline=True)
comment(0xBDD3, "No: adjust sectors per track", inline=True)
comment(0xBDD5, "Yes: use full 16 sectors/track", inline=True)
comment(0xBDD7, "Y=9: get sector count from block", inline=True)
comment(0xBDD9, "Set carry for subtraction", inline=True)
comment(0xBDDA, "Subtract sector count", inline=True)
comment(0xBDDC, "Result >= 0: fits in remaining", inline=True)
comment(0xBDDE, "Need to cross track boundary", inline=True)
comment(0xBDE0, "Set carry for subtraction", inline=True)
comment(0xBDE1, "Subtract start sector position", inline=True)
comment(0xBDE3, "Store sectors remaining this track", inline=True)
comment(0xBDE6, "Get sector count from block", inline=True)
comment(0xBDE8, "Set carry", inline=True)
comment(0xBDE9, "Subtract sectors done this track", inline=True)
comment(0xBDEC, "X=0: init result", inline=True)
comment(0xBDEE, "Y=&FF: init for divide", inline=True)
comment(0xBDF0, "Divide remaining by 16", inline=True)
comment(0xBDF3, "Store full tracks to process", inline=True)
comment(0xBDF6, "Store partial sectors on last track", inline=True)
comment(0xBDF9, "Branch always (positive)", inline=True)
comment(0xBDFB, "Y=9: get sector count", inline=True)
comment(0xBDFD, "Get sector count from block", inline=True)
comment(0xBDFF, "Store in NMI workspace", inline=True)
comment(0xBE02, "A=&FF: no additional tracks", inline=True)
comment(0xBE04, "Store track count", inline=True)
comment(0xBE07, "A=0: no partial sectors", inline=True)
comment(0xBE09, "Store partial count", inline=True)
comment(0xBE0C, "Clear sector position counter", inline=True)
comment(0xBE0E, "Store in NMI workspace", inline=True)
comment(0xBE11, "Increment full track count", inline=True)
comment(0xBE14, "Decrement sectors this track", inline=True)
comment(0xBE17, "X=1: write sector register", inline=True)
comment(0xBE19, "Write sector to FDC with verify", inline=True)
comment(0xBE1C, "Check read/write direction", inline=True)
comment(0xBE1E, "Reading: use read command", inline=True)
comment(0xBE20, "A=&A0: write command base", inline=True)
comment(0xBE22, "OR in step rate", inline=True)
comment(0xBE25, "Branch (always non-zero)", inline=True)
comment(0xBE27, "A=&80: read command base", inline=True)
comment(0xBE29, "Store FDC command in workspace", inline=True)
comment(0xBE2B, "Clear seek flag", inline=True)
comment(0xBE2E, "Get FDC command", inline=True)
comment(0xBE30, "Issue command to FDC", inline=True)
comment(0xBE33, "Wait for NMI completion", inline=True)
comment(0xBE36, "Get transfer state", inline=True)
comment(0xBE38, "Bit 1 set: need track step", inline=True)
comment(0xBE3A, "No step needed: check side switch", inline=True)
comment(0xBE3C, "Clear seek flag", inline=True)
comment(0xBE3F, "Clear track-step flag", inline=True)
comment(0xBE42, "FDC step-in command (&54)", inline=True)
comment(0xBE44, "OR in drive select bits", inline=True)
comment(0xBE47, "Issue step-in command", inline=True)
comment(0xBE4A, "Increment current track", inline=True)
comment(0xBE4C, "Continue multi-sector loop", inline=True)
comment(0xBE4E, "Check bit 3: side switch needed?", inline=True)
comment(0xBE50, "Check if set", inline=True)
comment(0xBE52, "Not set: operation complete", inline=True)
comment(0xBE54, "Clear seek flag for side switch", inline=True)
comment(0xBE57, "Clear side-switch flag", inline=True)
comment(0xBE5A, "Increment track for side 1", inline=True)
comment(0xBE5C, "Select side 1", inline=True)
comment(0xBE5F, "FDC restore command (seek to trk 0)", inline=True)
comment(0xBE61, "OR in drive select", inline=True)
comment(0xBE64, "Issue restore command", inline=True)
comment(0xBE67, "Continue loop (always branches)", inline=True)
comment(0xBE69, "Clear seek flag", inline=True)
comment(0xBE6C, "Check for next track boundary", inline=True)
comment(0xBE6F, "Transfer result to A", inline=True)
comment(0xBE70, "Non-zero: more sectors to transfer", inline=True)
comment(0xBE72, "Set completion flag bit 0", inline=True)
comment(0xBE74, "Set carry", inline=True)
comment(0xBE75, "Store completion flag", inline=True)
comment(0xBE77, "Return (operation complete)", inline=True)
comment(0xBE78, "Clear track-step flag", inline=True)
comment(0xBE7B, "Get FDC command", inline=True)
comment(0xBE7D, "Apply head load delay", inline=True)
comment(0xBE80, "Issue FDC command", inline=True)
comment(0xBE83, "Return", inline=True)

# sub_cbe84 - check track boundary crossing
comment(0xBE84, "Get sectors remaining this track", inline=True)
comment(0xBE87, "Non-zero: not at boundary", inline=True)
comment(0xBE89, "Get full tracks remaining", inline=True)
comment(0xBE8C, "Non-zero: need track step", inline=True)
comment(0xBE8E, "Get partial sectors on last track", inline=True)
comment(0xBE91, "Non-zero: still have partial track", inline=True)
comment(0xBE93, "X=0: all done", inline=True)
comment(0xBE95, "Branch to return", inline=True)
comment(0xBE97, "Decrement partial sector count", inline=True)
comment(0xBE9A, "Jump to update sector position", inline=True)
comment(0xBE9D, "Get sector position counter", inline=True)
comment(0xBEA0, "Non-zero: continue processing", inline=True)
comment(0xBEA2, "Set head-loaded flag", inline=True)
comment(0xBEA5, "Set carry", inline=True)
comment(0xBEA6, "Restore head-loaded flag", inline=True)
comment(0xBEA9, "Read current track from FDC", inline=True)
comment(0xBEAC, "Track >= 79 (&4F)?", inline=True)
comment(0xBEAE, "No: normal track step", inline=True)
comment(0xBEB0, "Get NMI control byte", inline=True)
comment(0xBEB3, "Bit 2 set (double-sided)?", inline=True)
comment(0xBEB5, "Not set: single-sided disc", inline=True)
comment(0xBEB7, "X=0: operation ending", inline=True)
comment(0xBEB9, "Jump to track position update", inline=True)
comment(0xBEBC, "Track &4F: switch to side 1", inline=True)
comment(0xBEBE, "Set track to &FF (will be 0 after inc)", inline=True)
comment(0xBEC0, "Select side 1", inline=True)
comment(0xBEC3, "Get NMI drive control byte", inline=True)
comment(0xBEC6, "Write to FDC control register", inline=True)
comment(0xBEC9, "Get transfer state", inline=True)
comment(0xBECB, "Set bit 3 (side switch flag)", inline=True)
comment(0xBECD, "Branch (always non-zero)", inline=True)
comment(0xBECF, "Get transfer state", inline=True)
comment(0xBED1, "Set bit 1 (track step flag)", inline=True)
comment(0xBED3, "Store updated state", inline=True)
comment(0xBED5, "Decrement full track count", inline=True)
comment(0xBED8, "Zero: check for partial track", inline=True)
comment(0xBEDA, "Sectors per track = &10 (16)", inline=True)
comment(0xBEDC, "Store in sector counter", inline=True)
comment(0xBEDF, "A=&FE: sector position reset", inline=True)
comment(0xBEE1, "Store sector position", inline=True)
comment(0xBEE3, "X=0: continue processing", inline=True)
comment(0xBEE5, "Branch to update (always)", inline=True)
comment(0xBEE7, "Decrement sector position counter", inline=True)
comment(0xBEEA, "Jump to update sector position", inline=True)
comment(0xBEED, "Decrement sectors this track", inline=True)
comment(0xBEF0, "X=&FF: more sectors to do", inline=True)
comment(0xBEF2, "Increment sector position", inline=True)
comment(0xBEF4, "Get current sector position", inline=True)
comment(0xBEF6, "Write to FDC sector register", inline=True)
comment(0xBEF9, "Read back to verify", inline=True)
comment(0xBEFC, "Loop until value sticks", inline=True)
comment(0xBEFE, "Return", inline=True)

# cbeff - set up drive select for floppy operation
comment(0xBEFF, "Y=6: get drive+sector from block", inline=True)
comment(0xBF01, "Get drive+sector byte", inline=True)
comment(0xBF03, "OR with current drive", inline=True)
comment(0xBF06, "Store as drive control byte", inline=True)
comment(0xBF08, "Isolate drive number bits", inline=True)
comment(0xBF0A, "Drive 0? OK", inline=True)
comment(0xBF0C, "Non-zero: bad drive error", inline=True)
comment(0xBF0F, "Check drive select bits", inline=True)
comment(0xBF11, "Bit 6: invalid drive?", inline=True)
comment(0xBF13, "Error &65: volume error (bad drive)", inline=True)
comment(0xBF15, "Store error code", inline=True)
comment(0xBF17, "Branch to floppy error", inline=True)
comment(0xBF19, "Get drive control byte", inline=True)
comment(0xBF1B, "Check bit 5 (drive 1 select)", inline=True)
comment(0xBF1D, "Not set: drive 0, use &21", inline=True)
comment(0xBF1F, "Drive 1: control byte &21", inline=True)
comment(0xBF21, "Branch (always)", inline=True)
comment(0xBF23, "Drive 0: control byte &22", inline=True)
comment(0xBF25, "Store in NMI drive control", inline=True)
comment(0xBF28, "Set head-loaded flag", inline=True)
comment(0xBF2B, "Set carry", inline=True)
comment(0xBF2C, "Restore head-loaded flag", inline=True)
comment(0xBF2F, "Calculate track/sector with range chk", inline=True)
comment(0xBF32, "Get NMI drive control byte", inline=True)
comment(0xBF35, "Write to FDC control register", inline=True)
comment(0xBF38, "Rotate bit 0 to carry", inline=True)
comment(0xBF39, "C=0: last access was other drive", inline=True)
comment(0xBF3B, "Get saved track for this drive", inline=True)
comment(0xBF3E, "Store as current track", inline=True)
comment(0xBF40, "Check head-loaded state", inline=True)
comment(0xBF43, "Head loaded: no seek needed", inline=True)
comment(0xBF45, "Branch (always)", inline=True)
comment(0xBF47, "Get saved track for other drive", inline=True)
comment(0xBF4A, "Store as current track", inline=True)
comment(0xBF4C, "Check head-loaded state", inline=True)
comment(0xBF4F, "Not loaded: need seek", inline=True)
comment(0xBF51, "Seek to track 0 and re-seek", inline=True)
comment(0xBF54, "Return", inline=True)

# star_rename body - complete coverage
comment(0xA505, "Save first arg pointer low", inline=True)
comment(0xA506, "Get first arg pointer high", inline=True)
comment(0xA508, "Save on stack", inline=True)
comment(0xA519, "Get source entry access byte", inline=True)
comment(0xA521, "Transfer to X for save", inline=True)
comment(0xA522, "Restore first arg low from stack", inline=True)
comment(0xA523, "Store in (&B4)", inline=True)
comment(0xA525, "Re-save on stack", inline=True)
comment(0xA526, "Get saved high byte from X", inline=True)
comment(0xA527, "Store in (&B5)", inline=True)
comment(0xA529, "Save on stack", inline=True)
comment(0xA52A, "Y=0: check path for $ root ref", inline=True)
comment(0xA52E, "Mask to ignore L and D bits", inline=True)
comment(0xA537, "Terminator found, check type", inline=True)
comment(0xA53D, "Next character in scan", inline=True)
comment(0xA53E, "Loop scanning destination path", inline=True)
comment(0xA59E, "Restore first arg low", inline=True)
comment(0xA59F, "Store in (&B4)", inline=True)
comment(0xA5A1, "Parse last component of dest path", inline=True)
comment(0xA5A4, "Y=0: scan for end of path component", inline=True)
comment(0xA5A6, "Get next character", inline=True)
comment(0xA5A8, "Is it '.' separator?", inline=True)
comment(0xA5AA, "Yes: advance past component", inline=True)
comment(0xA5AC, "Strip to printable range", inline=True)
comment(0xA5AE, "Control char: end of name", inline=True)
comment(0xA5B0, "End of destination name found", inline=True)
comment(0xA5B2, "Next character", inline=True)
comment(0xA5B3, "Loop scanning", inline=True)
comment(0xA5B5, "Advance pointer past component", inline=True)
comment(0xA5B6, "Add Y to pointer", inline=True)
comment(0xA5B8, "Store updated pointer", inline=True)
comment(0xA5BA, "No carry: scan next component", inline=True)
comment(0xA5BC, "Increment high byte on overflow", inline=True)
comment(0xA5BE, "Always branch back to scan", inline=True)
comment(0xA5C0, "Y=9: copy 10-byte new name", inline=True)
comment(0xA5C2, "Get old name byte (with attributes)", inline=True)
comment(0xA5C4, "Keep only bit 7 (attribute flag)", inline=True)
comment(0xA5C6, "Save attribute bit", inline=True)
comment(0xA5C9, "Get new name character", inline=True)
comment(0xA5CB, "Strip bit 7", inline=True)
comment(0xA5CD, "Is it '\"'?", inline=True)
comment(0xA5CF, "Yes: pad with CR", inline=True)
comment(0xA5D1, "Is it printable?", inline=True)
comment(0xA5D3, "Yes: use as-is", inline=True)
comment(0xA5D5, "Non-printable: use CR padding", inline=True)
comment(0xA5D7, "Merge attribute bit with new char", inline=True)
comment(0xA5DA, "Store renamed byte in entry", inline=True)
comment(0xA5DC, "Next byte", inline=True)
comment(0xA5DD, "Loop for 10 bytes", inline=True)
comment(0xA5DF, "Write directory back to disc", inline=True)
comment(0xA5E2, "Update directory checksums", inline=True)
comment(0xA5E5, "Save workspace and return", inline=True)
comment(0xA5E8, "Already exists: error", inline=True)
comment(0xA5EB, "Check if dest has zero size", inline=True)
comment(0xA5EE, "Non-zero: Already exists error", inline=True)
comment(0xA5F0, "Y=9: mark old entry as deleted", inline=True)
comment(0xA5F2, "Get last name byte", inline=True)
comment(0xA5F4, "Set bit 7 (mark as directory?)", inline=True)
comment(0xA5F6, "Store back", inline=True)
comment(0xA5F8, "Write source directory", inline=True)
comment(0xA5FB, "Y=&0A: copy entry data to workspace", inline=True)
comment(0xA5FD, "X=7: 8 bytes of entry metadata", inline=True)
comment(0xA5FF, "Get entry data byte", inline=True)
comment(0xA601, "Store in workspace for dest entry", inline=True)
comment(0xA604, "Next byte", inline=True)
comment(0xA605, "Decrement counter", inline=True)
comment(0xA606, "Loop for 8 bytes", inline=True)
comment(0xA608, "Clear OSFILE block fields", inline=True)
comment(0xA60A, "Clear load address", inline=True)
comment(0xA60D, "Clear exec address", inline=True)
comment(0xA610, "Clear length", inline=True)
comment(0xA613, "Clear attributes", inline=True)
comment(0xA616, "X=3: copy 3+1 start sector bytes", inline=True)
comment(0xA618, "Get sector byte from entry", inline=True)
comment(0xA61A, "Store in workspace", inline=True)
comment(0xA61D, "Next byte", inline=True)
comment(0xA61E, "Decrement counter", inline=True)
comment(0xA61F, "Loop for 4 bytes", inline=True)
comment(0xA621, "Y=0: build access byte from entry", inline=True)
comment(0xA623, "Get name byte", inline=True)
comment(0xA625, "Shift bit 7 into carry", inline=True)
comment(0xA626, "Rotate into access accumulator", inline=True)
comment(0xA629, "Next name byte", inline=True)
comment(0xA62A, "Done 4 bytes?", inline=True)
comment(0xA62C, "No, continue building access", inline=True)
comment(0xA62E, "Parse dest path and switch dir", inline=True)
comment(0xA631, "Y=&18: start sector in entry", inline=True)
comment(0xA633, "X=2: copy 3 sector bytes", inline=True)
comment(0xA635, "Get start sector byte", inline=True)
comment(0xA637, "Store in workspace", inline=True)
comment(0xA63A, "Next byte (decreasing)", inline=True)
comment(0xA63B, "Next workspace byte", inline=True)
comment(0xA63C, "Loop for 3 bytes", inline=True)
comment(0xA63E, "Save workspace state", inline=True)
comment(0xA641, "Set up OSFILE block for create", inline=True)
comment(0xA643, "Store block pointer low", inline=True)
comment(0xA645, "Block page = &10", inline=True)
comment(0xA647, "Store block pointer high", inline=True)
comment(0xA649, "Create entry in dest directory", inline=True)
comment(0xA64C, "Allocate disc space", inline=True)
comment(0xA64F, "Y=3: copy attributes back to entry", inline=True)
comment(0xA651, "Get new entry access byte", inline=True)
comment(0xA653, "Shift attribute bit to position", inline=True)
comment(0xA654, "Rotate into access accumulator", inline=True)
comment(0xA657, "Shift back", inline=True)
comment(0xA658, "Store in entry name byte", inline=True)
comment(0xA65A, "Next byte", inline=True)
comment(0xA65B, "Loop for 4 bytes", inline=True)
comment(0xA65D, "Write entry metadata", inline=True)
comment(0xA660, "Update entry size", inline=True)
comment(0xA663, "Write dest directory to disc", inline=True)
comment(0xA666, "Update moved dir's parent pointer", inline=True)
comment(0xA669, "Save workspace state", inline=True)
comment(0xA66C, "Restore source name pointer", inline=True)
comment(0xA66D, "Store high byte", inline=True)
comment(0xA66F, "Restore low byte", inline=True)
comment(0xA670, "Store low byte", inline=True)
comment(0xA672, "Find source entry again", inline=True)
comment(0xA675, "X=5: clear 6 bytes of sector info", inline=True)
comment(0xA677, "A=0: zero fill", inline=True)
comment(0xA679, "Clear sector/size workspace", inline=True)
comment(0xA67C, "Next byte", inline=True)
comment(0xA67D, "Loop for 6 bytes", inline=True)
comment(0xA67F, "Remove entry from source directory", inline=True)
comment(0xA682, "Save workspace and return", inline=True)

# sub_ca685 - update parent pointer if moved dir
comment(0xA685, "Y=3: check if entry is directory", inline=True)
comment(0xA687, "Get access byte", inline=True)
comment(0xA689, "Bit 7: is a directory", inline=True)
comment(0xA68B, "Not a dir: nothing to update", inline=True)
comment(0xA68C, "Y=2: copy 3 dir sector bytes", inline=True)
comment(0xA68E, "Get CSD sector byte", inline=True)
comment(0xA691, "Store as new parent sector", inline=True)
comment(0xA694, "Next byte", inline=True)
comment(0xA695, "Loop for 3 bytes", inline=True)
comment(0xA697, "Y=9: copy 10-byte directory name", inline=True)
comment(0xA699, "Get name byte from entry", inline=True)
comment(0xA69B, "Strip bit 7 (attribute)", inline=True)
comment(0xA69D, "Store as directory name", inline=True)
comment(0xA6A0, "Next byte", inline=True)
comment(0xA6A1, "Loop for 10 bytes", inline=True)
comment(0xA6A3, "Point to workspace name buffer", inline=True)
comment(0xA6A5, "Low byte = &74", inline=True)
comment(0xA6A7, "Page = &10", inline=True)
comment(0xA6A9, "High byte", inline=True)
comment(0xA6AB, "Load the moved directory", inline=True)
comment(0xA6AE, "Y=9: copy name to dir header", inline=True)
comment(0xA6B0, "Get name from workspace", inline=True)
comment(0xA6B3, "Store in directory name field", inline=True)
comment(0xA6B6, "Next byte", inline=True)
comment(0xA6B7, "Loop for 10 bytes", inline=True)
comment(0xA6B9, "Y=2: copy parent sector pointer", inline=True)
comment(0xA6BB, "Get new parent sector byte", inline=True)
comment(0xA6BE, "Store in directory parent field", inline=True)
comment(0xA6C1, "Next byte", inline=True)
comment(0xA6C2, "Loop for 3 bytes", inline=True)
comment(0xA6C4, "Write updated directory to disc", inline=True)
comment(0xA542, "Dot separator: continue past it", inline=True)
comment(0xA544, "Parse second arg (destination)", inline=True)
comment(0xA54A, "Set up OSFILE block pointer", inline=True)
comment(0xA54C, "Store low byte", inline=True)
comment(0xA54E, "Block page = &10", inline=True)
comment(0xA550, "Store high byte", inline=True)
comment(0xA552, "Search for dest filename", inline=True)
comment(0xA555, "Save search result flags", inline=True)
comment(0xA556, "Check directory state", inline=True)
comment(0xA559, "Restore flags", inline=True)
comment(0xA55A, "Dest not found: good for rename", inline=True)
comment(0xA55C, "Dest exists: save entry pointer", inline=True)
comment(0xA55E, "Y=3: copy sector+entry info", inline=True)
comment(0xA560, "Store in object sector workspace", inline=True)
comment(0xA563, "Get CSD sector byte", inline=True)
comment(0xA566, "Next byte", inline=True)
comment(0xA567, "Loop for 4 bytes", inline=True)
comment(0xA569, "Check if alt workspace is set", inline=True)
comment(0xA56C, "Set: skip CSD restore", inline=True)
comment(0xA56E, "Y=2: copy CSD sector from backup", inline=True)
comment(0xA570, "Get saved CSD sector byte", inline=True)
comment(0xA573, "Restore to CSD workspace", inline=True)
comment(0xA576, "Next byte", inline=True)
comment(0xA577, "Loop for 3 bytes", inline=True)
comment(0xA579, "Save workspace and reload dir", inline=True)
comment(0xA57C, "Restore second arg pointer", inline=True)
comment(0xA57D, "Store in (&B5)", inline=True)
comment(0xA57F, "Save in X", inline=True)
comment(0xA580, "Restore first arg pointer", inline=True)
comment(0xA581, "Store in (&B4)", inline=True)
comment(0xA583, "Re-save for later", inline=True)
comment(0xA584, "Get high byte from X", inline=True)
comment(0xA585, "Re-save", inline=True)
comment(0xA586, "Search source in original dir", inline=True)
comment(0xA589, "Check if file is open", inline=True)
comment(0xA58C, "Y=3: compare directories", inline=True)
comment(0xA58E, "Get source entry pointer", inline=True)
comment(0xA590, "Compare with dest dir sector", inline=True)
comment(0xA593, "Different: cross-dir rename", inline=True)
comment(0xA595, "Get CSD sector byte", inline=True)
comment(0xA598, "Next byte", inline=True)
comment(0xA599, "Loop for 4 bytes", inline=True)
comment(0xA59B, "Same dir: restore dest name ptr", inline=True)
comment(0xA59C, "Store in (&B5)", inline=True)
comment(0xA540, "Check for '.' separator", inline=True)

# star_compact (&A276)
# Uses RAM buffer to move files on disc, consolidating
# free space. If no SP/LP args, uses screen memory.
comment(0xA276, "Skip leading spaces", inline=True)
comment(0xA279, "Y=0: check for argument", inline=True)
comment(0xA27B, "Get first char", inline=True)
comment(0xA27D, "Printable char? Parse SP and LP", inline=True)
comment(0xA27F, "Yes, parse hex SP LP arguments", inline=True)
comment(0xA281, "OSBYTE &84: read top of user memory", inline=True)
comment(0xA286, "X = HIMEM low byte", inline=True)
comment(0xA287, "Non-zero low byte: bad compact", inline=True)
comment(0xA289, "Y = HIMEM high byte", inline=True)
comment(0xA28A, "Bit 7 set (>= &80): bad compact", inline=True)
comment(0xA28C, "Store HIMEM page as start page", inline=True)
comment(0xA28F, "Calculate length: &80 - start", inline=True)
comment(0xA295, "Store buffer length in pages", inline=True)
comment(0xA298, "Jump to compaction main loop", inline=True)

# star_cdir (&9570)
# Creates a new empty directory: allocates 5 sectors,
# initialises with Hugo identifiers, title from filename,
# parent pointer, and sequence number 0.
comment(0x9570, "OSARGS &FF: ensure FS is selected", inline=True)
comment(0x9577, "X=&0F: copy 16-byte template block", inline=True)
comment(0x9579, "Copy OSFILE template to workspace", inline=True)
comment(0x9582, "Store filename pointer in OSFILE blk", inline=True)
comment(0x958C, "Point (&B8) to workspace OSFILE blk", inline=True)
comment(0x9594, "Search for existing entry", inline=True)
comment(0x9597, "Y=9: check if entry has size > 0", inline=True)
comment(0x9599, "Check size bytes for non-zero", inline=True)
comment(0x95A2, "Size is 0: entry slot is free", inline=True)
comment(0x95B7, "Copy filename to dir entry, max 10", inline=True)
comment(0x95B9, "Strip bit 7", inline=True)
comment(0x95BB, "Quote terminates name", inline=True)
comment(0x95BF, "Control char terminates name", inline=True)
comment(0x95C3, "Pad with CR", inline=True)
comment(0x95C5, "Store character in entry", inline=True)
comment(0x95CA, "Allocate disc space for new dir", inline=True)
comment(0x95CD, "Y=3: set directory attribute", inline=True)
comment(0x95CF, "Get entry byte", inline=True)
comment(0x95D1, "Set bit 7 (D attribute on all)", inline=True)
comment(0x95D3, "Store back", inline=True)

# star_cdir body - remaining items (&9570-&993B)
# Creates directory: copies template, searches for name,
# zeroes 5 buffer pages, writes Hugo+parent+name+title.
comment(0x9572, "Y=0: for OSARGS", inline=True)
comment(0x957C, "Copy template to workspace", inline=True)
comment(0x957F, "Next byte", inline=True)
comment(0x9580, "Loop for 16 bytes", inline=True)
comment(0x9584, "Store filename in OSFILE block", inline=True)
comment(0x9587, "Get filename high byte", inline=True)
comment(0x9589, "Store in OSFILE block", inline=True)
comment(0x958E, "Store block pointer low", inline=True)
comment(0x9590, "Block page = &10", inline=True)
comment(0x9592, "Store block pointer high", inline=True)
comment(0x959C, "OR size mid byte", inline=True)
comment(0x959F, "OR size high byte", inline=True)
comment(0x95BD, "Quote: pad with CR", inline=True)
comment(0x95C1, "Printable: use as-is", inline=True)
comment(0x95C7, "Next name byte (decreasing)", inline=True)
comment(0x95C8, "Loop for 10 bytes", inline=True)
comment(0x95D5, "Next byte down", inline=True)
comment(0x95D6, "Past byte 1? (byte 0 is special)", inline=True)
comment(0x95D8, "No: continue setting attributes", inline=True)
comment(0x95DA, "Y=0: set D attribute on byte 0", inline=True)
comment(0x95DB, "Get name byte 0", inline=True)
comment(0x95DD, "Set bit 7 (D attribute)", inline=True)
comment(0x95DF, "Store back", inline=True)
comment(0x95E1, "A=0: zero-fill all 5 dir pages", inline=True)
comment(0x95E5, "Zero page 2 (&1800)", inline=True)
comment(0x95E8, "Zero page 1 (&1700)", inline=True)
comment(0x95EB, "Zero page 3 (&1900)", inline=True)
comment(0x95EE, "Zero page 4 (&1A00)", inline=True)
comment(0x95F1, "Zero page 5 (&1B00)", inline=True)
comment(0x95F4, "Next byte", inline=True)
comment(0x95F5, "Loop for 256 bytes per page", inline=True)
comment(0x95F7, "X=4: copy 5 bytes (seq+Hugo)", inline=True)
comment(0x95F9, "Get Hugo identifier byte from ROM", inline=True)
comment(0x95FC, "Store in dir header (&1700)", inline=True)
comment(0x95FF, "Store in dir footer (&1BFA)", inline=True)
comment(0x9602, "Get parent dir sector byte", inline=True)
comment(0x9605, "Store in footer parent pointer", inline=True)
comment(0x9608, "Next byte", inline=True)
comment(0x9609, "Loop for 5 bytes", inline=True)
comment(0x960B, "X=0: copy name as title and name", inline=True)
comment(0x960D, "Get name character from argument", inline=True)
comment(0x960F, "Strip bit 7", inline=True)
comment(0x9611, "Is it double-quote?", inline=True)
comment(0x9613, "Yes: pad with CR", inline=True)
comment(0x9615, "Is it printable (> '!')?", inline=True)
comment(0x9617, "Yes: use character as-is", inline=True)
comment(0x9619, "Non-printable: use CR padding", inline=True)
comment(0x961B, "Store in directory title", inline=True)
comment(0x961E, "Store in directory name", inline=True)
comment(0x9621, "Next argument character", inline=True)
comment(0x9622, "Next position in title/name", inline=True)
comment(0x9623, "Copied all 10 characters?", inline=True)
comment(0x9625, "No: continue copying", inline=True)
comment(0x9627, "A=CR: terminate title", inline=True)
comment(0x9629, "Store CR after last title char", inline=True)
comment(0x962C, "Calculate sectors and write dir", inline=True)
comment(0x962F, "Write directory and update FSM", inline=True)

# sub_c9642 - update CSD/lib/prev dir after file relocation
comment(0x9642, "Check if saved drive matches", inline=True)
comment(0x9645, "Compare with current drive", inline=True)
comment(0x9648, "Same: check CSD sector match", inline=True)
comment(0x964A, "Saved = &FF (not set)?", inline=True)
comment(0x964C, "Different drive: skip CSD check", inline=True)
comment(0x964E, "Y=2: compare 3 sector bytes", inline=True)
comment(0x9650, "Get old sector address byte", inline=True)
comment(0x9653, "Compare with CSD sector", inline=True)
comment(0x9656, "Mismatch: not CSD", inline=True)
comment(0x9658, "Next byte", inline=True)
comment(0x9659, "Loop for 3 bytes", inline=True)
comment(0x965B, "CSD matches: update to new sector", inline=True)
comment(0x965D, "Get new sector byte", inline=True)
comment(0x9660, "Store as CSD sector", inline=True)
comment(0x9663, "Next byte", inline=True)
comment(0x9664, "Loop for 3 bytes", inline=True)
comment(0x9666, "Check library directory", inline=True)
comment(0x9669, "Compare lib drive with current", inline=True)
comment(0x966C, "Different drive: skip lib", inline=True)
comment(0x966E, "Y=2: compare 3 sector bytes", inline=True)
comment(0x9670, "Get old sector address byte", inline=True)
comment(0x9673, "Compare with lib sector", inline=True)
comment(0x9676, "Mismatch: not library", inline=True)
comment(0x9678, "Next byte", inline=True)
comment(0x9679, "Loop for 3 bytes", inline=True)
comment(0x967B, "Lib matches: update to new sector", inline=True)
comment(0x967D, "Get new sector byte", inline=True)
comment(0x9680, "Store as lib sector", inline=True)
comment(0x9683, "Next byte", inline=True)
comment(0x9684, "Loop for 3 bytes", inline=True)
comment(0x9686, "Check previous directory", inline=True)
comment(0x9689, "Compare prev dir drive", inline=True)
comment(0x968C, "Different drive: skip", inline=True)
comment(0x968E, "Y=2: compare 3 sector bytes", inline=True)
comment(0x9690, "Get old sector byte", inline=True)
comment(0x9693, "Compare with prev dir sector", inline=True)
comment(0x9696, "Mismatch: not prev dir", inline=True)
comment(0x9698, "Next byte", inline=True)
comment(0x9699, "Loop for 3 bytes", inline=True)
comment(0x969B, "Prev dir matches: update", inline=True)
comment(0x969D, "Get new sector byte", inline=True)
comment(0x96A0, "Store as prev dir sector", inline=True)
comment(0x96A3, "Next byte", inline=True)
comment(0x96A4, "Loop for 3 bytes", inline=True)

# c96a6 - sector-by-sector file copy between drives
comment(0x96A6, "Check bit 3 (copy in progress?)", inline=True)
comment(0x96A8, "Bit 3: copy operation flag", inline=True)
comment(0x96AA, "Set: skip directory write", inline=True)
comment(0x96AC, "Write directory to disc", inline=True)
comment(0x96AF, "Flush OSARGS workspace", inline=True)
comment(0x96B2, "Check if sectors remain to copy", inline=True)
comment(0x96B5, "OR with mid byte", inline=True)
comment(0x96B8, "OR with high byte", inline=True)
comment(0x96BB, "Non-zero: more to copy", inline=True)
comment(0x96BD, "All done: return", inline=True)
comment(0x96BE, "Get sector count high", inline=True)
comment(0x96C1, "OR with mid byte", inline=True)
comment(0x96C4, "Non-zero: more than buffer fits", inline=True)
comment(0x96C6, "Get sector count low", inline=True)
comment(0x96C9, "Compare with buffer size", inline=True)
comment(0x96CC, "Fits in buffer: use exact count", inline=True)
comment(0x96CE, "Too many: use buffer size", inline=True)
comment(0x96D1, "Store sector count for this chunk", inline=True)
comment(0x96D4, "Set transfer addr to buffer start", inline=True)
comment(0x96D7, "Store transfer addr mid", inline=True)
comment(0x96DA, "X=0: clear other addr bytes", inline=True)
comment(0x96DC, "Clear transfer addr low", inline=True)
comment(0x96E0, "Clear high bytes", inline=True)
comment(0x96E3, "Clear highest byte", inline=True)
comment(0x96E6, "Set carry for subtraction", inline=True)
comment(0x96E7, "Subtract copied amount from total", inline=True)
comment(0x96EA, "Subtract buffer size", inline=True)
comment(0x96ED, "Store reduced count low", inline=True)
comment(0x96F0, "Get count mid", inline=True)
comment(0x96F3, "Subtract borrow", inline=True)
comment(0x96F5, "Store reduced mid", inline=True)
comment(0x96F8, "Get count high", inline=True)
comment(0x96FB, "Subtract borrow", inline=True)
comment(0x96FD, "Store reduced high", inline=True)
comment(0x9700, "No underflow: proceed", inline=True)
comment(0x9702, "Underflow: adjust sector count", inline=True)
comment(0x9705, "Add buffer size back", inline=True)
comment(0x9708, "Store as final chunk size", inline=True)
comment(0x970B, "Read command = 8", inline=True)
comment(0x970D, "Store in disc op", inline=True)
comment(0x9710, "Get source sector low", inline=True)
comment(0x9713, "Store in disc op sector", inline=True)
comment(0x9716, "Get source sector mid", inline=True)
comment(0x9719, "Store in disc op", inline=True)
comment(0x971C, "Get source sector high + drive", inline=True)
comment(0x971F, "Store in disc op", inline=True)
comment(0x9722, "Read from source", inline=True)
comment(0x9725, "Write command = &0A", inline=True)
comment(0x9727, "Store in disc op", inline=True)
comment(0x972A, "Get dest sector low", inline=True)
comment(0x972D, "Store in disc op sector", inline=True)
comment(0x9730, "Get dest sector mid", inline=True)
comment(0x9733, "Store in disc op", inline=True)
comment(0x9736, "Get dest sector high + drive", inline=True)
comment(0x9739, "Store in disc op", inline=True)
comment(0x973C, "Write to destination", inline=True)
comment(0x973F, "Check if more sectors to copy", inline=True)
comment(0x9742, "OR with mid byte", inline=True)
comment(0x9745, "OR with high byte", inline=True)
comment(0x9748, "Zero: all copied", inline=True)
comment(0x974A, "Check if full buffer was used", inline=True)
comment(0x974D, "Compare with buffer size", inline=True)
comment(0x9750, "Partial: done", inline=True)
comment(0x9752, "Advance source sector", inline=True)
comment(0x9753, "Get source low", inline=True)
comment(0x9756, "Add buffer pages copied", inline=True)
comment(0x9759, "Store updated source low", inline=True)
comment(0x975C, "No carry", inline=True)
comment(0x975E, "Carry: inc source mid", inline=True)
comment(0x9761, "No wrap", inline=True)
comment(0x9763, "Wrap: inc source high", inline=True)
comment(0x9766, "Advance dest sector", inline=True)
comment(0x9767, "Get dest low", inline=True)
comment(0x976A, "Add buffer pages", inline=True)
comment(0x976D, "Store updated dest low", inline=True)
comment(0x9770, "No carry", inline=True)
comment(0x9772, "Carry: inc dest mid", inline=True)
comment(0x9775, "No wrap", inline=True)
comment(0x9777, "Wrap: inc dest high", inline=True)
comment(0x977A, "Loop for more chunks", inline=True)
comment(0x977D, "Check copy operation flag", inline=True)
comment(0x977F, "Bit 3: copy in progress?", inline=True)
comment(0x9781, "Not set: reload directory", inline=True)
comment(0x9783, "Set: return directly", inline=True)
comment(0x9784, "Set transfer addr to &12 page", inline=True)
comment(0x9786, "Store addr mid", inline=True)
comment(0x9789, "Read command = 8", inline=True)
comment(0x978B, "Store command", inline=True)
comment(0x978E, "Get dir sector low", inline=True)
comment(0x9791, "Store in disc op sector low", inline=True)
comment(0x9794, "Get dir sector mid", inline=True)
comment(0x9797, "Store in disc op mid", inline=True)
comment(0x979A, "Get dir sector high", inline=True)
comment(0x979D, "Store in disc op high", inline=True)
comment(0x97A0, "Read 5 sectors (full directory)", inline=True)
comment(0x97A2, "Store sector count", inline=True)
comment(0x97A5, "Execute disc read", inline=True)

# sub_c97a8 - init compaction search state
comment(0x97A8, "A=0: clear search state", inline=True)
comment(0x97AA, "Clear dest sector low", inline=True)
comment(0x97AD, "Clear dest sector mid", inline=True)
comment(0x97B0, "Clear dest sector high", inline=True)
comment(0x97B3, "A=&FF: init source sector to &FFFFFF", inline=True)
comment(0x97B5, "Set source sector low", inline=True)
comment(0x97B8, "Set source sector mid", inline=True)
comment(0x97BB, "Set source sector high", inline=True)
comment(0x97BE, "Point to first directory entry", inline=True)
comment(0x97C1, "Y=0: check entry first byte", inline=True)
comment(0x97C3, "Get first byte", inline=True)
comment(0x97C5, "Non-zero: valid entry", inline=True)
comment(0x97C7, "End of entries: check if any found", inline=True)
comment(0x97CA, "AND all source sector bytes", inline=True)
comment(0x97CD, "All &FF?", inline=True)
comment(0x97D0, "Compare with &FF", inline=True)
comment(0x97D2, "Not &FF: found an entry", inline=True)
comment(0x97D4, "All &FF: no entries, write dir", inline=True)
comment(0x97D7, "Y=&16: get entry start sector", inline=True)
comment(0x97D9, "X=2: compare 3 sector bytes", inline=True)
comment(0x97DB, "Set carry for subtraction", inline=True)
comment(0x97DC, "Get workspace sector byte", inline=True)
comment(0x97DF, "Subtract entry sector byte", inline=True)
comment(0x97E1, "Next byte", inline=True)
comment(0x97E2, "Next workspace byte", inline=True)
comment(0x97E3, "Loop for 3 bytes", inline=True)
comment(0x97E5, "Workspace >= entry: skip", inline=True)
comment(0x97E7, "Y=&16: compare with other workspace", inline=True)
comment(0x97E9, "X=2: 3 bytes", inline=True)
comment(0x97EB, "Set carry", inline=True)
comment(0x97EC, "Get other workspace byte", inline=True)
comment(0x97EF, "Subtract entry sector byte", inline=True)
comment(0x97F1, "Next byte", inline=True)
comment(0x97F2, "Next workspace byte", inline=True)
comment(0x97F3, "Loop for 3 bytes", inline=True)
comment(0x97F5, "Other < entry: update best entry", inline=True)
comment(0x97F7, "Y=&16: copy entry sector to best", inline=True)
comment(0x97F9, "X=2: 3 bytes", inline=True)
comment(0x97FB, "Get entry sector byte", inline=True)
comment(0x97FD, "Store as best entry sector", inline=True)
comment(0x9800, "Next byte", inline=True)
comment(0x9801, "Next workspace byte", inline=True)
comment(0x9802, "Loop for 3 bytes", inline=True)
comment(0x9804, "Save entry pointer", inline=True)
comment(0x9806, "Store as best entry pointer low", inline=True)
comment(0x9808, "Get pointer high", inline=True)
comment(0x980A, "Store as best entry pointer high", inline=True)
comment(0x980C, "Advance to next dir entry", inline=True)
comment(0x980E, "Clear carry for addition", inline=True)
comment(0x980F, "Add 26 bytes per entry", inline=True)
comment(0x9811, "Store updated pointer", inline=True)
comment(0x9813, "No page crossing: continue search", inline=True)
comment(0x9815, "Increment page", inline=True)

# Compaction: allocate new space for relocated file
comment(0x9819, "Restore best entry pointer", inline=True)
comment(0x981B, "Store in (&B6)", inline=True)
comment(0x981D, "Get high byte", inline=True)
comment(0x981F, "Store in (&B7)", inline=True)
comment(0x9821, "Y=2: copy 3 source sector bytes", inline=True)
comment(0x9823, "Get source sector byte", inline=True)
comment(0x9826, "Store as dest for allocation", inline=True)
comment(0x9829, "Next byte", inline=True)
comment(0x982A, "Loop for 3 bytes", inline=True)
comment(0x982C, "X=0: start scanning FSM", inline=True)
comment(0x982E, "Store scan position", inline=True)
comment(0x9830, "Past end of FSM?", inline=True)
comment(0x9833, "No: check this entry", inline=True)
comment(0x9835, "Past end: reinit search", inline=True)
comment(0x9838, "Advance X by 3", inline=True)
comment(0x9839, "Continue advancing", inline=True)
comment(0x983A, "3rd byte", inline=True)
comment(0x983B, "Save position", inline=True)
comment(0x983D, "Y=2: compare sector bytes", inline=True)
comment(0x983F, "Back up one", inline=True)
comment(0x9840, "Get FSM address byte", inline=True)
comment(0x9843, "Compare with source sector", inline=True)
comment(0x9846, "FSM >= source: possible match", inline=True)
comment(0x9848, "Restore X, try next", inline=True)
comment(0x984A, "Loop (X != 0)", inline=True)
comment(0x984C, "Exact match? Check all bytes", inline=True)
comment(0x984E, "Next byte (decreasing)", inline=True)
comment(0x984F, "Loop for 3 bytes", inline=True)
comment(0x9851, "Restore entry position", inline=True)
comment(0x9853, "Need at least 2 entries (>= 6)", inline=True)
comment(0x9855, "Not enough entries: reinit", inline=True)
comment(0x9857, "Check if entry is adjacent", inline=True)
comment(0x9859, "Clear carry for addition", inline=True)
comment(0x985A, "Save carry", inline=True)
comment(0x985B, "Restore carry", inline=True)
comment(0x985C, "Get previous entry end address", inline=True)
comment(0x985F, "Add previous entry length", inline=True)
comment(0x9862, "Save carry", inline=True)
comment(0x9863, "Compare with source sector", inline=True)
comment(0x9866, "Match: entries are adjacent", inline=True)
comment(0x9868, "Restore carry, not adjacent", inline=True)
comment(0x9869, "Not adjacent: reinit search", inline=True)
comment(0x986C, "Next byte", inline=True)
comment(0x986D, "Next source byte", inline=True)
comment(0x986E, "All 3 bytes?", inline=True)
comment(0x9870, "No: continue comparing", inline=True)
comment(0x9872, "Restore carry", inline=True)
comment(0x9873, "X=2: copy sector address", inline=True)
comment(0x9875, "Y=&12: entry length offset", inline=True)
comment(0x9877, "Get entry length byte", inline=True)
comment(0x9879, "Compare with 1 (min sector)", inline=True)
comment(0x987B, "Next length byte", inline=True)
comment(0x987C, "Get next byte", inline=True)
comment(0x987E, "Add carry from compare", inline=True)
comment(0x9880, "Store sector count", inline=True)
comment(0x9883, "Store in alt workspace", inline=True)
comment(0x9886, "Store in disc op", inline=True)
comment(0x9889, "Get source sector byte", inline=True)
comment(0x988C, "Store in object sector", inline=True)
comment(0x988F, "Next byte", inline=True)
comment(0x9890, "Loop for 3 bytes", inline=True)
comment(0x9895, "Allocate space from FSM", inline=True)
comment(0x9898, "X=2: copy new sector address", inline=True)
comment(0x989A, "Y=&18: start sector in entry", inline=True)
comment(0x989C, "Get new sector byte", inline=True)
comment(0x989F, "Store in directory entry", inline=True)
comment(0x98A1, "Store as dest sector", inline=True)
comment(0x98A4, "Next entry byte (decreasing)", inline=True)
comment(0x98A5, "Next workspace byte", inline=True)
comment(0x98A6, "Loop for 3 bytes", inline=True)
comment(0x98A8, "Update CSD/lib/prev dir pointers", inline=True)
comment(0x98AB, "Continue compaction search", inline=True)

# sub_c98ae - compaction main loop
comment(0x98AE, "A=0: init recursion stack pointer", inline=True)
comment(0x98B0, "Store in workspace", inline=True)
comment(0x98B2, "Clear root sector low", inline=True)
comment(0x98B5, "Clear root sector mid", inline=True)
comment(0x98B8, "Root sector = 2", inline=True)
comment(0x98BA, "Store root sector low", inline=True)
comment(0x98BD, "Set up path ':0.$' for root", inline=True)
comment(0x98BF, "Store in workspace", inline=True)
comment(0x98C1, "Path string address low", inline=True)
comment(0x98C3, "Store in (&B4)", inline=True)
comment(0x98C5, "Path string page &99", inline=True)
comment(0x98C7, "Store in (&B5)", inline=True)
comment(0x98C9, "Load root directory", inline=True)
comment(0x98CC, "Y=2: copy parent sector", inline=True)
comment(0x98CE, "Get sector byte from workspace", inline=True)
comment(0x98D1, "Store as dir parent pointer", inline=True)
comment(0x98D4, "Next byte", inline=True)
comment(0x98D5, "Loop for 3 bytes", inline=True)
comment(0x98D7, "Init search state for this dir", inline=True)
comment(0x98DA, "Point to first entry", inline=True)
comment(0x98DD, "Y=0: check entry", inline=True)
comment(0x98DF, "Get first byte", inline=True)
comment(0x98E1, "Zero: end of entries in this dir", inline=True)
comment(0x98E3, "Y=3: check access byte", inline=True)
comment(0x98E5, "Get access byte", inline=True)
comment(0x98E7, "Bit 7 clear: regular file", inline=True)
comment(0x98E9, "Directory: check stack depth", inline=True)
comment(0x98EB, "Compare with &FE (max depth)", inline=True)
comment(0x98ED, "At max depth: skip this subdir", inline=True)
comment(0x98EF, "Push subdir entry address on stack", inline=True)
comment(0x98F1, "Get entry pointer low", inline=True)
comment(0x98F3, "Store in (&B4)", inline=True)
comment(0x98F5, "Store on recursion stack", inline=True)
comment(0x98F7, "Advance stack pointer", inline=True)
comment(0x98F9, "Get entry pointer high", inline=True)
comment(0x98FB, "Store in (&B5)", inline=True)
comment(0x98FD, "Store on recursion stack", inline=True)
comment(0x98FF, "Advance stack pointer", inline=True)
comment(0x9901, "X=2: save parent dir sector", inline=True)
comment(0x9903, "Get parent sector byte", inline=True)
comment(0x9906, "Store in workspace", inline=True)
comment(0x9909, "Next byte", inline=True)
comment(0x990A, "Loop for 3 bytes", inline=True)

# Return from subdirectory recursion
comment(0x990E, "Check recursion stack", inline=True)
comment(0x9910, "Stack empty: compaction done", inline=True)
comment(0x9912, "Set up path for parent return", inline=True)
comment(0x9914, "Store path address low", inline=True)
comment(0x9916, "Path page &99", inline=True)
comment(0x9918, "Store path address high", inline=True)
comment(0x991A, "Load parent directory", inline=True)
comment(0x991D, "Y=0: pop entry address from stack", inline=True)
comment(0x991F, "Decrement stack pointer", inline=True)
comment(0x9921, "Get entry pointer high", inline=True)
comment(0x9923, "Restore (&B7)", inline=True)
comment(0x9925, "Decrement stack pointer", inline=True)
comment(0x9927, "Get entry pointer low", inline=True)
comment(0x9929, "Restore (&B6)", inline=True)
comment(0x992B, "Advance to next entry", inline=True)
comment(0x992C, "Get entry pointer low", inline=True)
comment(0x992E, "Add 26 bytes per entry", inline=True)
comment(0x9930, "Store updated pointer", inline=True)
comment(0x9932, "No page crossing: continue scan", inline=True)
comment(0x9934, "Increment page", inline=True)
comment(0x9938, "Save workspace and return", inline=True)

# star_access (&993D)
# Attributes are stored as bit 7 of name bytes:
#   byte 0 bit 7 = R (read)
#   byte 1 bit 7 = W (write)
#   byte 2 bit 7 = L (locked)
#   byte 3 bit 7 = D (directory)
#   byte 4 bit 7 = E (execute only)
comment(0x993D, "Find first matching file", inline=True)
comment(0x9940, "Found? Set attributes", inline=True)
comment(0x9942, "Not found: report error", inline=True)
comment(0x9945, "Y=2: clear R,W,L attribute bits", inline=True)
comment(0x9947, "Get name byte", inline=True)
comment(0x9949, "Strip bit 7 (clear attribute)", inline=True)
comment(0x994B, "Store back", inline=True)
comment(0x9951, "Clear existing R,W,L attributes", inline=True)
comment(0x9954, "Y=4: check E attribute byte", inline=True)
comment(0x9956, "Get byte 4", inline=True)
comment(0x9958, "Bit 7 set: E attribute, skip", inline=True)
comment(0x995A, "Y=3: get D attribute byte", inline=True)
comment(0x995B, "Get byte 3", inline=True)
comment(0x995D, "Keep only bit 7 (D flag)", inline=True)
comment(0x995F, "Y=0: get first name byte", inline=True)
comment(0x9961, "OR D flag into name byte 0", inline=True)
comment(0x9963, "Store back", inline=True)
comment(0x9965, "Save for E attribute check", inline=True)
comment(0x9968, "Y=0: scan for attribute string", inline=True)
comment(0x996A, "Skip filename characters", inline=True)
comment(0x996C, "Compare with space", inline=True)
comment(0x996E, "Control char: end of command", inline=True)
comment(0x9970, "Space: skip to attributes", inline=True)
comment(0x9972, "Double-quote?", inline=True)
comment(0x9974, "Yes: skip to attributes", inline=True)
comment(0x9979, "Skip spaces between name and attrs", inline=True)
comment(0x997D, "Control char: no attributes given", inline=True)
comment(0x997F, "Space: keep skipping", inline=True)
comment(0x9988, "Parse attribute character", inline=True)
comment(0x998A, "Convert to uppercase", inline=True)
comment(0x998C, "Check if E attribute already set", inline=True)
comment(0x998F, "E set: only L attribute allowed", inline=True)
comment(0x9991, "Is it 'E'?", inline=True)
comment(0x9993, "No, check R/W/L", inline=True)
comment(0x9995, "E: clear R,W,L first", inline=True)
comment(0x9998, "Y=4: set bit 7 of byte 4", inline=True)
comment(0x999C, "Set E attribute", inline=True)
comment(0x99A5, 'X=2: check against "RWL" table', inline=True)
comment(0x99A7, "Compare with R/W/L character", inline=True)
comment(0x99AA, "Match: set this attribute", inline=True)
comment(0x99AC, "E already set? Only L allowed", inline=True)
comment(0x99B4, "Unknown char: check if printable", inline=True)
comment(0x99B6, "Control char: end of attributes", inline=True)
comment(0x99BB, "Display info if *OPT1 verbose", inline=True)
comment(0x99BE, "Find next matching file", inline=True)
comment(0x99C1, "More matches? Continue", inline=True)
comment(0x99C3, "Write directory back to disc", inline=True)
comment(0x99C9, "Set attribute: save text pointer", inline=True)
comment(0x99CB, "X = index into R/W/L (0,1,2)", inline=True)
comment(0x99CC, "Use as Y index into entry", inline=True)
comment(0x99CD, "Get name byte at that position", inline=True)
comment(0x99CF, "Set bit 7 (attribute flag)", inline=True)
comment(0x99D1, "Store back", inline=True)
comment(0x99D3, "Restore text pointer", inline=True)
comment(0x99D5, "Continue parsing attributes", inline=True)

# star_info (&94E7)
# Prints info for files matching a wildcard pattern.
# Loops finding matching entries and printing each one.
comment(0x94E7, "Find first matching file", inline=True)
comment(0x94EA, "Found? Print its info", inline=True)
comment(0x94EC, "Not found: report error", inline=True)
comment(0x94EF, "Print this entry's catalogue info", inline=True)
comment(0x94F2, "Find next matching file", inline=True)
comment(0x94F5, "More matches? Continue loop", inline=True)
comment(0x94F7, "No more matches: save and return", inline=True)

# sub_c94fa - conditional info display
label(0x94FA, "conditional_info_display")
comment(0x94FA, "Check *OPT1 setting", inline=True)
comment(0x94FC, "Bit 2 set: verbose mode on", inline=True)
comment(0x94FE, "Yes, display the info", inline=True)

# c9501 - print one directory entry's full info
label(0x9501, "print_entry_info")
subroutine(0x9501, "print_entry_info",
    title="Print full catalogue info for one directory entry",
    description="""\
Print a directory entry in *INFO/*EX format:
  filename  access/  loadaddr execaddr length sector [D]

Entry at (&B6) is a 26-byte directory entry. Checks the
E (execute-only) attribute and suppresses detail if set.
Uses 3-byte addresses for small files, 4-byte for large.
""")
comment(0x9501, "Print filename and access string", inline=True)
comment(0x9504, "Print space after access string", inline=True)
comment(0x9507, "Y=4: check first access nibble byte", inline=True)
comment(0x9509, "Get access/attribute byte", inline=True)
comment(0x950B, "Bit 7 (E attribute): suppress info", inline=True)
comment(0x950D, "Y=3: get access byte for format", inline=True)
comment(0x950E, "Get access byte", inline=True)
comment(0x9510, "Shift bit 7 into C (directory flag)", inline=True)
comment(0x9511, "X=&0A: start offset (3-byte addrs)", inline=True)
comment(0x9513, "Y=&0D: end offset for 3-byte format", inline=True)
comment(0x9515, "C=0: 3-byte addresses", inline=True)
comment(0x9517, "X=&17: start offset (4-byte addrs)", inline=True)
comment(0x9519, "Y=&18: end offset for 4-byte format", inline=True)
comment(0x951B, "Skip sector field boundary?", inline=True)
comment(0x951D, "Yes, skip the sector field gap", inline=True)
comment(0x951F, "Get byte from entry", inline=True)
comment(0x9521, "Print as 2 hex digits", inline=True)
comment(0x9524, "Check if at field boundary", inline=True)
comment(0x9525, "Field boundary every 4 bytes (X&3=1)", inline=True)
comment(0x9529, "Not at boundary, continue", inline=True)
comment(0x952B, "Print two spaces between fields", inline=True)
comment(0x9531, "Skip ahead to next field", inline=True)
comment(0x9533, "Advance Y by 5", inline=True)
comment(0x9536, "Next byte backwards", inline=True)
comment(0x9537, "Advance field index", inline=True)
comment(0x9538, "Past end of entry (X=&1A)?", inline=True)
comment(0x953A, "No, continue printing", inline=True)
comment(0x953C, "Print newline at end of entry", inline=True)

# star_ex (&9433)
# Displays each directory entry in the format:
#   filename  access/  loadaddr execaddr length sector [D]
# Loops through 26-byte entries until first byte is 0.
comment(0x9433, "Parse directory argument", inline=True)
comment(0x9436, "Load and validate the directory", inline=True)
comment(0x9439, "Y=0: check first byte of entry", inline=True)
comment(0x943B, "Get first byte of entry name", inline=True)
comment(0x943D, "Zero: end of entries, done", inline=True)
comment(0x943F, "Print this entry's full info", inline=True)
comment(0x9442, "Clear carry for addition", inline=True)
comment(0x9443, "Advance (&B6) by 26 to next entry", inline=True)
comment(0x9445, "Add &1A (26 bytes per entry)", inline=True)
comment(0x9449, "No page crossing, continue loop", inline=True)
comment(0x944B, "Page crossed: increment high byte", inline=True)
comment(0x944D, "Continue loop (always branches)", inline=True)

# sub_c944f (&944F) - check for parent/current dir specifiers
label(0x944F, "check_special_dir_char")
subroutine(0x944F, "check_special_dir_char",
    title="Check for ^ (parent) or @ (current) directory",
    description="""\
Check if the first character of the argument is ^ (parent
directory) or @ (current directory). Sets (&B6) to point
to the appropriate directory footer area.
""",
    on_exit={"a": "corrupted (Z set if ^ or @ matched)",
             "x": "corrupted", "y": "corrupted"})
comment(0x944F, "Y=0: get first argument char", inline=True)
comment(0x9453, "Strip bit 7", inline=True)
comment(0x9455, "Is it '^' (parent directory)?", inline=True)
comment(0x9457, "No, check for '@'", inline=True)
comment(0x9459, "'^': point to dir parent sector", inline=True)
comment(0x9461, "Set Z flag (matched)", inline=True)
comment(0x9463, "Is it '@' (current directory)?", inline=True)
comment(0x9465, "No, return Z clear (no match)", inline=True)
comment(0x9467, "'@': point to workspace at &10FE", inline=True)
comment(0x946F, "Transfer Y=0 to A, setting Z flag", inline=True)

# sub_c9471 (&9471) - parse optional directory argument
label(0x9471, "parse_dir_argument")
subroutine(0x9471, "parse_dir_argument",
    title="Parse optional directory path argument",
    description="""\
If a directory argument is given, parse the path and load
the target directory. If no argument, use the current
directory (checking it's initialised first).

Used by *EX, *CAT, *CDIR, and *DIR.
""")
comment(0x9471, "Y=0: check for argument", inline=True)
comment(0x9473, "Get first char of argument", inline=True)
comment(0x9475, "Is it a printable char?", inline=True)
comment(0x9477, "Yes, parse the path", inline=True)
comment(0x9479, "No arg: check drive is initialised", inline=True)
comment(0x947C, "Drive = &FF (uninitialised)?", inline=True)
comment(0x947D, "Drive OK, return", inline=True)
comment(0x947F, "Parse path and load directory", inline=True)
comment(0x9482, "Simple path or '^'/'@'?", inline=True)
comment(0x9484, "Y=3: check entry access byte", inline=True)
comment(0x9486, "Get access/attribute byte", inline=True)
comment(0x9488, "Bit 7 set: is a directory, found it", inline=True)
comment(0x948A, "Not a directory, search deeper", inline=True)
comment(0x9492, "Check for '^' or '@' specifier", inline=True)
comment(0x9497, "Set up workspace for directory read", inline=True)
comment(0x949D, "Copy CSD sector to workspace", inline=True)
comment(0x94A8, "X=&0A: copy 11-byte disc op block", inline=True)
comment(0x94AA, "Copy template control block", inline=True)
comment(0x94B3, "X=2: copy 3 sector address bytes", inline=True)
comment(0x94B5, "Y=&16: offset of start sector in entry", inline=True)
comment(0x94B7, "Get sector byte from directory entry", inline=True)
comment(0x94B9, "Store in disc op control block", inline=True)
comment(0x94BC, "Also store in workspace", inline=True)
comment(0x94C3, "Check if this is an *INFO call", inline=True)
comment(0x94C5, "zp_b7 = &94 means *INFO context", inline=True)
comment(0x94C7, "Yes, return without reading dir", inline=True)
comment(0x94C9, "Execute disc read to load directory", inline=True)

# star_run (&A399)
# Tries CSD first, then library. If exec addr is &FFFFFFFF,
# opens file with *EXEC. If load addr is &FFFFFFFF, raises
# Won't error. Otherwise loads and jumps to exec address.
comment(0xA399, "Save filename pointer for retry", inline=True)
comment(0xA3A1, "Try to find file in CSD", inline=True)
comment(0xA3A4, "Found in CSD, proceed to load", inline=True)
comment(0xA3A6, "Not found: save workspace state", inline=True)
comment(0xA3A9, "Restore filename pointer", inline=True)
comment(0xA3B1, "Switch CSD to library directory", inline=True)
comment(0xA3B4, "Try to find file in library", inline=True)
comment(0xA3B7, "Not in library either: Not found", inline=True)
comment(0xA3B9, "Restore CSD after library search", inline=True)
comment(0xA3BC, "Save filename address for OSFILE", inline=True)
comment(0xA3C6, "Y=&0E: check exec address bytes", inline=True)
comment(0xA3C8, "Get exec addr byte 0", inline=True)
comment(0xA3CA, "X=2: AND with bytes 1 and 2", inline=True)
comment(0xA3CC, "AND exec addr bytes together", inline=True)
comment(0xA3D2, "All &FF? Exec addr = &FFFFFFFF", inline=True)
comment(0xA3D4, "No, check load address", inline=True)
comment(0xA3D6, "Exec = &FFFFFFFF: open with OSFIND", inline=True)
comment(0xA3DA, "A=&40: open for reading", inline=True)
comment(0xA3DC, "Open the file", inline=True)
comment(0xA3DF, "Save handle for *EXEC", inline=True)
comment(0xA3E2, 'Point to "E.$.!BOOT" string', inline=True)
comment(0xA3E6, "Execute via OSCLI", inline=True)
comment(0xA3E9, "Y=&0B: check load addr bytes", inline=True)
comment(0xA3F3, "All &FF? Load addr = &FFFFFFFF", inline=True)
comment(0xA3F5, "No, proceed with load and execute", inline=True)
comment(0xA401, "Set up OSFILE block for load", inline=True)
comment(0xA40E, "Load the file", inline=True)
comment(0xA411, "Y=4: check if Tube/IO address", inline=True)
comment(0xA413, "Get exec addr high byte", inline=True)
comment(0xA417, "OR with lowest byte", inline=True)
comment(0xA419, "Bit 7 set: I/O or Tube address", inline=True)
comment(0xA41B, "Host address: jump directly", inline=True)
comment(0xA41E, "Set up Tube transfer", inline=True)
comment(0xA421, "Check exec addr for &FFxx (Tube)", inline=True)
comment(0xA42F, "A=1: language entry point", inline=True)
comment(0xA431, "Jump to execution address", inline=True)
comment(0xA434, "Check if Tube present", inline=True)
comment(0xA436, "No Tube: execute directly", inline=True)
comment(0xA438, "Tube: set up Tube transfer", inline=True)
comment(0xA43B, "Point to exec addr block", inline=True)
comment(0xA43F, "A=4: Tube transfer type", inline=True)
comment(0xA441, "Start Tube execution", inline=True)

# star_lib (&A444)
# Same structure as star_dir but copies to library workspace.
comment(0xA444, "Parse path and load target dir", inline=True)
comment(0xA447, "Y=9: copy 10-byte directory name", inline=True)
comment(0xA449, "Get name byte from dir buffer", inline=True)
comment(0xA44C, "Store as library name", inline=True)
comment(0xA450, "Loop for 10 bytes", inline=True)
comment(0xA452, "Y=3: copy 4-byte sector+drive", inline=True)
comment(0xA454, "Get sector address byte", inline=True)
comment(0xA457, "Store as library sector", inline=True)
comment(0xA45B, "Loop for 4 bytes", inline=True)
comment(0xA45D, "Save workspace and return", inline=True)

# sub_ca460 - switch CSD to library directory
label(0xA460, "switch_to_library")
subroutine(0xA460, "switch_to_library",
    title="Switch CSD to library directory",
    description="""\
Save the current CSD sector address, then replace it with
the library directory sector address. Used before *LCAT
and *LEX to temporarily operate on the library.
""")
comment(0xA460, "Y=3: copy 4 bytes", inline=True)
comment(0xA462, "Save current CSD sector", inline=True)
comment(0xA465, "To temporary workspace", inline=True)
comment(0xA468, "Get library sector", inline=True)
comment(0xA46B, "Set as CSD sector", inline=True)
comment(0xA46E, "Next byte", inline=True)
comment(0xA471, "Load the library directory", inline=True)

# sub_ca473 - restore CSD from saved copy
label(0xA473, "restore_csd")
subroutine(0xA473, "restore_csd",
    title="Restore CSD sector from saved copy",
    description="""\
Restore the CSD sector address from the temporary save
in wksp_1030. Used after *LCAT/*LEX to switch back.
""")
comment(0xA473, "Y=3: copy 4 bytes", inline=True)
comment(0xA475, "Get saved CSD sector", inline=True)
comment(0xA478, "Restore to CSD workspace", inline=True)

# star_lcat (&A47F) and star_lex (&A48B)
comment(0xA47F, "Switch CSD to library", inline=True)
comment(0xA482, "Restore CSD after catalogue", inline=True)
comment(0xA485, "Print catalogue (*CAT format)", inline=True)
comment(0xA488, "Save workspace and return", inline=True)
comment(0xA48B, "Switch CSD to library", inline=True)
comment(0xA48E, "Restore CSD after display", inline=True)
comment(0xA491, "Print full catalogue (*EX format)", inline=True)
comment(0xA494, "Save workspace and return", inline=True)

# star_mount (&A15E)
# Loads the FSM and root directory from the specified drive,
# then sets it as the CSD. Also resets the library and
# previous directory if they were on this drive.
comment(0xA15E, "Parse drive number argument", inline=True)
comment(0xA161, "Get drive number to mount", inline=True)
comment(0xA164, "Set as current drive", inline=True)
comment(0xA167, "Point to unpark command block", inline=True)
comment(0xA16B, "Send unpark command to drive", inline=True)
comment(0xA16E, "Point to root directory path", inline=True)
comment(0xA176, "Set root as CSD via *DIR", inline=True)
comment(0xA179, "Check if previous dir is on drive", inline=True)
comment(0xA17F, "Different drive, leave previous", inline=True)
comment(0xA181, "Invalidate previous directory", inline=True)
comment(0xA189, "Check if library is on this drive", inline=True)
comment(0xA18F, "Different drive, leave library", inline=True)
comment(0xA191, "Invalidate library sector", inline=True)
comment(0xA199, 'X=&0A: reset lib name to "Unset"', inline=True)
comment(0xA19B, "Copy default name to library", inline=True)

# sub_ca1aa - calculate total free space
label(0xA1AA, "calc_total_free_space")
subroutine(0xA1AA, "calc_total_free_space",
    title="Calculate total free space on disc",
    description="""\
Sum all free space entries in the FSM to get the total
free space. Prepares workspace for display by *FREE.

On exit:
  3-byte sum in wksp_disc_op_result (little-endian)
""")
comment(0xA1AA, "A=0: clear accumulators", inline=True)
comment(0xA1AC, "X=3: clear 4 bytes", inline=True)
comment(0xA1AE, "Clear disc op result bytes", inline=True)
comment(0xA1B1, "Clear Tube transfer bytes", inline=True)
comment(0xA1B7, "Sum the free space entries", inline=True)
comment(0xA1BA, "X=2: copy 3 bytes of result", inline=True)
comment(0xA1BC, "Get result byte", inline=True)
comment(0xA1BF, "Store in disc op workspace", inline=True)

# sub_ca1c6 - print space value with headers
label(0xA1C6, "print_space_value")
subroutine(0xA1C6, "print_space_value",
    title="Print space value in hex and decimal",
    description="""\
Print a 3-byte sector count from the disc op workspace as
hex bytes, then convert to decimal bytes and print as
' Sectors = NNN,NNN,NNN Bytes'. Used by *FREE to display
free and used space.

The hex part prints the 3-byte value at &1016-&1018. The
decimal part uses the double-dabble algorithm (also called
shift-and-add-3) to convert the 4-byte binary value at
&1015-&1018 into 10 BCD digits stored at &1040-&1049.
Each iteration shifts the binary value left one bit and
rotates the carry into the BCD digits, subtracting 10
from any digit that reaches 10 or above (carrying into
the next digit). After 31 iterations (32 bits minus the
sign bit), the BCD digits are printed with leading-zero
suppression and comma separators at positions 3 and 6
(thousands and millions).
""")
comment(0xA1C6, "Print high byte as hex", inline=True)
comment(0xA1CC, "Print mid byte as hex", inline=True)
comment(0xA1D2, "Print low byte as hex", inline=True)
comment(0xA1D8, 'Print " Sectors ="', inline=True)

# star_dismount (&A111)
comment(0xA111, "Parse drive number argument", inline=True)
comment(0xA114, "X=9: check all 10 channels", inline=True)
comment(0xA116, "Get channel flags", inline=True)
comment(0xA119, "Channel not open? Skip", inline=True)
comment(0xA11B, "Get channel's drive number", inline=True)
comment(0xA11E, "Isolate drive bits", inline=True)
comment(0xA120, "Compare with target drive", inline=True)
comment(0xA123, "Different drive? Skip", inline=True)
comment(0xA125, "Clear carry for addition", inline=True)
comment(0xA126, "Channel index to A", inline=True)
comment(0xA127, "Add &30 to get file handle", inline=True)
comment(0xA129, "Transfer to Y for OSFIND", inline=True)
comment(0xA12A, "A=0: close file", inline=True)
comment(0xA12C, "Close this file", inline=True)
comment(0xA12F, "Next channel", inline=True)
comment(0xA132, "Is dismounted drive the CSD drive?", inline=True)
comment(0xA135, "Compare with target drive", inline=True)
comment(0xA138, "Different drive: CSD unaffected", inline=True)
comment(0xA13A, "Mark current drive as uninitialised", inline=True)
comment(0xA13C, "Set CSD drive to &FF (unset)", inline=True)
comment(0xA142, 'X=0: reset CSD name to "Unset"', inline=True)
comment(0xA144, "Copy default name to CSD workspace", inline=True)

# sub_ca149 - copy default directory name
label(0xA149, "copy_default_dir_name")
subroutine(0xA149, "copy_default_dir_name",
    title="Copy default directory name to workspace",
    description="""\
Copy the reversed string 'Unset' (with quotes and CR
padding) to the CSD or library name workspace at &1100+X.
Used when dismounting or initialising to set the directory
name to the default 'Unset' value.
""",
    on_entry={"x": "workspace offset (0 for CSD, 10 for library)"})
comment(0xA149, "Y=9: copy 10 bytes", inline=True)
comment(0xA14B, "Get byte from reversed name table", inline=True)
comment(0xA14E, "Store in CSD/lib name workspace", inline=True)
comment(0xA151, "Next workspace byte", inline=True)
comment(0xA152, "Next table byte (backwards)", inline=True)
comment(0xA153, "Loop for 10 bytes", inline=True)

# star_free (&A01B)
# Calculates and displays free and used space on the disc.
# Calls sub_ca1aa to sum all free space entries in the FSM,
# then subtracts from total disc size to get used space.
comment(0xA01B, "Calculate total free space", inline=True)
comment(0xA01E, "Print free space with header", inline=True)
comment(0xA021, 'Print "Free" + CR', inline=True)
comment(0xA028, "CR + bit 7: end of inline string", inline=True)
comment(0xA029, "Calculate total free space again", inline=True)
comment(0xA02C, "Y=1: offset to disc size low byte", inline=True)
comment(0xA02E, "X=2: loop counter for 3-byte subtract", inline=True)
comment(0xA030, "Set carry for subtraction", inline=True)
comment(0xA031, "Get disc size byte (Y-indexed)", inline=True)
comment(0xA034, "Subtract free space", inline=True)
comment(0xA037, "Store result (used space)", inline=True)
comment(0xA03C, "Loop for 3 bytes", inline=True)
comment(0xA03E, "Print used space with header", inline=True)
comment(0xA041, 'Print "Used" + CR', inline=True)
comment(0xA048, "CR + bit 7: end of inline string", inline=True)

# star_bye (&A0C3)
# Saves current drive, closes all files, then loops through
# drives &60, &40, &20, &00 (4 drives with bit-shifted IDs)
# dismounting each one.
comment(0xA0C3, "Save current drive for restore", inline=True)
comment(0xA0C7, "Transfer to X to check for &FF", inline=True)
comment(0xA0C8, "Drive &FF = uninitialised?", inline=True)
comment(0xA0C9, "Yes, skip close", inline=True)
comment(0xA0CB, "Close all open files", inline=True)
comment(0xA0CE, "Start with drive 3 (ID = &60)", inline=True)
comment(0xA0D0, "Set as current drive", inline=True)
comment(0xA0D3, "X=&EA: scsi_cmd_park control block low", inline=True)
comment(0xA0D5, "Y=&A0: scsi_cmd_park control block high", inline=True)
comment(0xA0D7, "Park heads on this drive", inline=True)
comment(0xA0DA, "Get current drive ID", inline=True)
comment(0xA0DD, "Set carry for subtraction", inline=True)
comment(0xA0DE, "Next drive (subtract &20)", inline=True)
comment(0xA0E0, "Store updated drive ID", inline=True)
comment(0xA0E3, "Loop while drive ID >= 0", inline=True)
comment(0xA0E5, "Restore original drive", inline=True)
comment(0xA0E6, "Store back as current drive", inline=True)

# sub_ca0f5 - parse optional drive argument
label(0xA0F5, "parse_drive_argument")
subroutine(0xA0F5, "parse_drive_argument",
    title="Parse optional drive number argument",
    description="""\
Parse an optional drive number from the command line for
commands like *DISMOUNT, *MOUNT, *FREE, *MAP. If no
argument given, uses the current drive.
""")
comment(0xA0F5, "Skip leading spaces", inline=True)
comment(0xA0F8, "Get current drive", inline=True)
comment(0xA0FB, "Drive uninitialised (&FF)?", inline=True)
comment(0xA0FC, "Yes, use 0 instead", inline=True)
comment(0xA0FF, "Store default drive number", inline=True)
comment(0xA102, "Y=0: check for argument", inline=True)
comment(0xA104, "Get first argument char", inline=True)
comment(0xA106, "Is it a printable char?", inline=True)
comment(0xA108, "No argument: use default drive", inline=True)
comment(0xA10A, "Parse drive number from argument", inline=True)
comment(0xA10D, "Store parsed drive number", inline=True)

# star_delete (&A0BB)
comment(0xA0BB, "Try to remove the file", inline=True)
comment(0xA0BE, "Not found? Just return", inline=True)
comment(0xA0C0, "Found: delete from directory", inline=True)

# star_map (&A04A)
# Prints a table of all free space entries from the FSM,
# then checks if compaction is recommended.
comment(0xA04A, 'Print "Address :  Length" + CR header', inline=True)
comment(0xA05E, "CR + bit 7: end of inline string", inline=True)
comment(0xA05F, "X=0: start of FSM entries", inline=True)
comment(0xA061, "Past end of free space list?", inline=True)
comment(0xA064, "Yes, done", inline=True)
comment(0xA066, "Advance X to entry+3", inline=True)
comment(0xA069, "Save FSM index for next iteration", inline=True)
comment(0xA06B, "Y=2: print 3 address bytes", inline=True)
comment(0xA06D, "Back up to previous byte", inline=True)
comment(0xA06E, "Get address byte from FSM sector 0", inline=True)
comment(0xA071, "Print as 2 hex digits", inline=True)
comment(0xA074, "Next byte", inline=True)
comment(0xA075, "Loop for 3 bytes (high to low)", inline=True)
comment(0xA077, 'Print "  : " separator', inline=True)
comment(0xA07E, "' ' + bit 7: end of inline string", inline=True)
comment(0xA07F, "Restore FSM index", inline=True)
comment(0xA081, "Y=2: print 3 length bytes", inline=True)
comment(0xA083, "Back up to previous byte", inline=True)
comment(0xA084, "Get length byte from FSM sector 1", inline=True)
comment(0xA087, "Print as 2 hex digits", inline=True)
comment(0xA08A, "Next byte", inline=True)
comment(0xA08B, "Loop for 3 bytes (high to low)", inline=True)
comment(0xA08D, "Print newline after each entry", inline=True)
comment(0xA090, "Restore FSM index for next entry", inline=True)
comment(0xA092, "Loop if more entries", inline=True)

# sub_ca094 - check if compaction recommended
label(0xA094, "check_compaction_recommended")
subroutine(0xA094, "check_compaction_recommended",
    title="Check if disc compaction is recommended",
    description="""\
After *MAP output, check if the FSM has become fragmented
enough to recommend compaction. Prints a recommendation
message if the free space list pointer exceeds &E1.
""")
comment(0xA094, "Check if already reported", inline=True)
comment(0xA097, "Already done, skip", inline=True)
comment(0xA099, "Get FSM end-of-list pointer", inline=True)
comment(0xA09C, "Pointer >= &E1 (many fragments)?", inline=True)
comment(0xA09E, "No, space not fragmented enough", inline=True)
comment(0xA0A0, 'Print "Compaction recommended" + CR', inline=True)
comment(0xA0B9, "CR + bit 7: end of inline string", inline=True)
comment(0xA0BA, "Return to caller", inline=True)

# service_handler_4 (&9CDA) - unrecognised star command
# Checks if the command is prefixed with "ADFS" or "FADFS"
# (the MOS filing system prefix convention). If so, selects
# ADFS and passes the remainder of the command for execution.
comment(0x9CDA, "Save Y (text offset)", inline=True)
comment(0x9CDC, "Push &FF (no prefix flag)", inline=True)
comment(0x9CDF, "Get first command character", inline=True)
comment(0x9CE1, "Convert to lowercase", inline=True)
comment(0x9CE3, "Is it 'f' (FADFS prefix)?", inline=True)
comment(0x9CE5, "No, check for ADFS prefix", inline=True)
comment(0x9CE7, "Replace &FF with 'C' (FSC code)", inline=True)
comment(0x9CEB, "Skip past 'F' prefix", inline=True)
comment(0x9CEC, "X=3: match 4 chars of 'ADFS'", inline=True)
comment(0x9CEE, "Get next command character", inline=True)
comment(0x9CF0, "Advance text pointer", inline=True)
comment(0x9CF1, "Is it a dot (abbreviation)?", inline=True)
comment(0x9CF3, "Yes, match succeeded", inline=True)
comment(0x9CF5, "Convert to lowercase for compare", inline=True)
comment(0x9CF7, 'Compare with "adfs" (backwards)', inline=True)
comment(0x9CFA, "No match, not for us", inline=True)
comment(0x9CFF, "Skip spaces after 'ADFS'", inline=True)
comment(0x9D02, "Space?", inline=True)
comment(0x9D04, "Yes, skip more spaces", inline=True)
comment(0x9D06, "Printable: more text follows, fail", inline=True)
comment(0x9D08, "Get prefix flag", inline=True)
comment(0x9D0A, "Get saved text offset", inline=True)
comment(0x9D0E, "Select ADFS and execute command", inline=True)
comment(0x9D11, "Not for us: clean up stack", inline=True)
comment(0x9D13, "Restore Y", inline=True)
comment(0x9D14, "A=4: pass on to next ROM", inline=True)
comment(0x9D16, "Get our ROM number", inline=True)

# service_handler_8 (&9D19) - unrecognised OSWORD
# Handles OSWORD &70 (read dir state), &71 (read free space),
# &72 (disc access), &73 (read last error).
comment(0x9D19, "Save Y (OSWORD number is at &EF)", inline=True)
comment(0x9D1B, "A=0 for OSARGS read filing system", inline=True)
comment(0x9D1E, "Get current filing system number", inline=True)
comment(0x9D21, "Is it ADFS (filing system 8)?", inline=True)
comment(0x9D23, "No, pass on to next ROM", inline=True)
comment(0x9D25, "Get OSWORD number from &EF", inline=True)
comment(0x9D27, "Is it OSWORD &72 (disc access)?", inline=True)
comment(0x9D29, "No, check other OSWORD numbers", inline=True)
comment(0x9D2B, "Get control block address from &F0", inline=True)
comment(0x9D2D, "Store in (&BA) for access", inline=True)
comment(0x9D33, "Y=&0F: copy 16 bytes of ctrl block", inline=True)
comment(0x9D35, "Copy control block to workspace", inline=True)
comment(0x9D3D, "Get disc operation command byte", inline=True)
comment(0x9D40, "Mask out direction bit", inline=True)
comment(0x9D42, "Command 8 = verify?", inline=True)
comment(0x9D44, "Yes, handle verify specially", inline=True)
comment(0x9D46, "Set up disc op control block", inline=True)
comment(0x9D4A, "Temporarily set drive to &FF+1=0", inline=True)
comment(0x9D4D, "Was it already 0 (unset)?", inline=True)
comment(0x9D4F, "No, restore original drive", inline=True)
comment(0x9D52, "Execute the disc command", inline=True)
comment(0x9D55, "Success?", inline=True)
comment(0x9D57, "Check sector count for verify", inline=True)
comment(0x9D5A, "More sectors to verify", inline=True)
comment(0x9D5F, "Y=0: store result at block+0", inline=True)
comment(0x9D61, "Write result back to control block", inline=True)
comment(0x9D63, "Restore ROM number", inline=True)
comment(0x9D65, "Restore Y", inline=True)
comment(0x9D67, "A=0: service call claimed", inline=True)
comment(0x9D6A, "Not our filing system", inline=True)
comment(0x9D6E, "A=8: pass on to next ROM", inline=True)
comment(0x9D71, "OSWORD &73 (read last error)?", inline=True)
comment(0x9D73, "No, check next", inline=True)
comment(0x9D75, "Y=4: copy 5 bytes of error info", inline=True)
comment(0x9D77, "Copy error sector+code to block", inline=True)
comment(0x9D7F, "Return as claimed", inline=True)
comment(0x9D81, "OSWORD &70 (read dir state)?", inline=True)
comment(0x9D83, "No, check next", inline=True)
comment(0x9D85, "Get directory master sequence", inline=True)
comment(0x9D88, "Y=0: store at block+0", inline=True)
comment(0x9D8A, "Write sequence number to block", inline=True)
comment(0x9D8C, "Get ADFS flags", inline=True)
comment(0x9D8F, "Write flags to block+1", inline=True)
comment(0x9D91, "Return as claimed", inline=True)
comment(0x9D94, "OSWORD &71 (read free space)?", inline=True)
comment(0x9D96, "No, not for us", inline=True)
comment(0x9D98, "Calculate free space on disc", inline=True)
comment(0x9D9B, "Y=3: copy 4 bytes of result", inline=True)
comment(0x9D9D, "Copy free space to control block", inline=True)
comment(0x9DA5, "Return as claimed", inline=True)

# sub_c9da7 - print *HELP header line
label(0x9DA7, "help_print_header")
subroutine(0x9DA7, "help_print_header",
    title="Print *HELP version header line",
    description="""\
Print a newline followed by the ROM version string for
*HELP output. Uses print_inline_string.
""")

# star_back (&A497)
# Swaps CSD and previous directory sector addresses,
# loads the new CSD, copies its name to workspace.
comment(0xA497, "Y=3: swap 4 bytes of sector+drive", inline=True)
comment(0xA499, "Get previous dir sector byte", inline=True)
comment(0xA49C, "Store as CSD sector", inline=True)
comment(0xA49F, "Get current CSD sector byte", inline=True)
comment(0xA4A2, "Store as previous dir sector", inline=True)
comment(0xA4A5, "Next byte", inline=True)
comment(0xA4A6, "Loop for 4 bytes (sector+drive)", inline=True)
comment(0xA4A8, "Reload directory from new sector", inline=True)
comment(0xA4AB, "Y=9: copy 10-byte directory name", inline=True)
comment(0xA4AD, "Get dir name from buffer", inline=True)
comment(0xA4B0, "Store as CSD name", inline=True)
comment(0xA4B3, "Next byte", inline=True)
comment(0xA4B4, "Loop for 10 bytes", inline=True)

# sub_ca4b7 (&A4B7) - skip past filename in command line
label(0xA4B7, "skip_filename")
subroutine(0xA4B7, "skip_filename",
    title="Skip past filename in command string",
    description="""\
Advance (&B4) past the next filename component in the
command string, handling dots as path separators.
""")
comment(0xA4B7, "Y=0: start scanning", inline=True)
comment(0xA4B9, "Check if char is a terminator", inline=True)
comment(0xA4BC, "Yes, check if it's a dot", inline=True)
comment(0xA4BE, "Advance past non-terminator", inline=True)
comment(0xA4C1, "Is terminator a dot?", inline=True)
comment(0xA4C3, "Yes, skip dot and continue", inline=True)
comment(0xA4C5, "Y = number of chars scanned", inline=True)
comment(0xA4C7, "Add to (&B4) to advance pointer", inline=True)

# ca4cf (&A4CF) - skip leading spaces and handle quotes
label(0xA4CF, "skip_spaces")
subroutine(0xA4CF, "skip_spaces",
    title="Skip leading spaces in command argument",
    description="""\
Advance (&B4) past leading spaces. Also handles
double-quoted strings (skips to closing quote).

On exit:
  (&B4) points past the skipped characters
""")
comment(0xA4CF, "Y=0: start scanning", inline=True)
comment(0xA4D1, "C=0: not inside quotes", inline=True)
comment(0xA4D3, "Get character from command line", inline=True)
comment(0xA4D5, "Compare with space", inline=True)
comment(0xA4D7, "Control char: end of argument", inline=True)
comment(0xA4D9, "Space: skip it", inline=True)
comment(0xA4DB, "Double-quote?", inline=True)
comment(0xA4DD, "No, end of argument", inline=True)
comment(0xA4DF, "Restore C (quote tracking flag)", inline=True)
comment(0xA4E0, "C=0 first quote: start quoted str", inline=True)
comment(0xA4E2, "C=1 second quote: bad name error", inline=True)
comment(0xA4E5, "C=1: inside quoted string now", inline=True)
comment(0xA4E7, "Next character", inline=True)
comment(0xA4EA, "Y = number of chars to skip", inline=True)
comment(0xA4ED, "Add to (&B4) to advance pointer", inline=True)

# sub_ca4f6 (&A4F6) - check for drive specifier colon
label(0xA4F6, "check_drive_colon")
subroutine(0xA4F6, "check_drive_colon",
    title="Check for drive specifier colon",
    description="""\
Check if the next character at (&B4) is a colon,
indicating a drive number follows.

On exit:
  Z set if no colon found
  If colon found, jumps to parse drive number
""")
comment(0xA4F6, "Y=0", inline=True)
comment(0xA4F8, "Get next character", inline=True)
comment(0xA4FA, "Strip bit 7", inline=True)
comment(0xA4FC, "Is it ':'?", inline=True)
comment(0xA4FE, "No, return", inline=True)
comment(0xA500, "Yes, parse drive number", inline=True)

# star_dir (&953F)
# Parses the directory path argument, loads the target
# directory, copies its name to CSD workspace, saves
# the previous directory sector for *BACK.
comment(0x953F, "Parse path and load target dir", inline=True)
comment(0x9542, "Y=9: copy 10-byte directory name", inline=True)
comment(0x9544, "Get name byte from dir buffer", inline=True)
comment(0x9547, "Store as CSD name", inline=True)
comment(0x954B, "Loop for all 10 bytes", inline=True)
comment(0x954D, "Get saved drive number", inline=True)
comment(0x9550, "Is it &FF (not set)?", inline=True)
comment(0x9552, "No, use saved drive", inline=True)
comment(0x9554, "Use current drive instead", inline=True)
comment(0x9557, "Store as new CSD drive", inline=True)
comment(0x955A, "Y=2: copy 3-byte sector address", inline=True)
comment(0x955C, "Get CSD sector address byte", inline=True)
comment(0x955F, "Save as previous dir sector (*BACK)", inline=True)
comment(0x9563, "Loop for 3 bytes", inline=True)
comment(0x9565, "A=&FF: mark as unset", inline=True)
comment(0x9567, "Clear alternative workspace ptr", inline=True)
comment(0x956A, "Clear saved drive", inline=True)
comment(0x956D, "Save workspace and return", inline=True)

comment(0xA250, "' ' + bit 7: end of inline string", inline=True)
comment(0xA251, "Return to caller", inline=True)

# star_title (&A252)
comment(0xA252, "Ensure dir is loaded and writable", inline=True)
comment(0xA255, "Validate FSM before modification", inline=True)
comment(0xA258, "Skip leading spaces in argument", inline=True)
comment(0xA25B, "Y=0: index into title string", inline=True)
comment(0xA25D, "Get next character", inline=True)
comment(0xA25F, "Strip bit 7", inline=True)
comment(0xA261, "Double-quote terminates title", inline=True)
comment(0xA263, "Yes, pad with CR", inline=True)
comment(0xA265, "Control char terminates title", inline=True)
comment(0xA267, "Printable, store it", inline=True)
comment(0xA269, "Use CR as padding character", inline=True)
comment(0xA26B, "Store in directory title field", inline=True)
comment(0xA26E, "Next character", inline=True)
comment(0xA26F, "Title is 19 characters max", inline=True)
comment(0xA271, "Loop for all 19 characters", inline=True)
comment(0xA273, "Write directory back to disc", inline=True)

# copy_code_to_nmi_space (&BBF1)
# Copies 73 bytes of NMI handler code from ROM (&BC79)
# to NMI workspace (&0D00), then patches the handler
# for the current transfer direction and Tube state.
comment(0xBBF1, "Y=&48: copy 73 bytes of NMI code", inline=True)
comment(0xBBF3, "Read NMI handler byte from ROM", inline=True)
comment(0xBBF6, "Write to NMI workspace", inline=True)
comment(0xBBFA, "Loop until all bytes copied", inline=True)
comment(0xBBFC, "Y=1: get memory address low from blk", inline=True)
comment(0xBBFE, "Get transfer address low byte", inline=True)
comment(0xBC00, "Patch NMI handler with address low", inline=True)
comment(0xBC04, "Get transfer address high byte", inline=True)
comment(0xBC06, "Patch NMI handler with address high", inline=True)
comment(0xBC09, "Check control flags", inline=True)
comment(0xBC0B, "Bit 7 set: reading from disc", inline=True)
comment(0xBC0D, "Writing: patch NMI with STA opcode", inline=True)
comment(0xBC0F, "Store at NMI read/write instruction", inline=True)
comment(0xBC12, "Tube in use?", inline=True)
comment(0xBC14, "No, use direct memory NMI handler", inline=True)
comment(0xBC16, "Get control flags for Tube setup", inline=True)
comment(0xBC1C, "Set up Tube transfer parameters", inline=True)
comment(0xBC21, "Set up direct memory NMI handler", inline=True)
comment(0xBC24, "Store NMI completion flag", inline=True)
comment(0xBC27, "Get current ROM number", inline=True)
comment(0xBC29, "Patch NMI handler with ROM number", inline=True)

# check_dir_loaded (&A6C7)
# Checks wksp_current_drive is not &FF (uninitialised).
comment(0xA6C7, "Get current drive number", inline=True)
comment(0xA6CA, "Increment: &FF becomes 0", inline=True)
comment(0xA6CB, "Non-zero = drive is set, OK", inline=True)
comment(0xA6CD, "Drive is &FF: no directory loaded", inline=True)

# sub_ca6de (&A6DE) - verify directory integrity
label(0xA6DE, "verify_dir_integrity")
subroutine(0xA6DE, "verify_dir_integrity",
    title="Verify directory buffer integrity",
    description="""\
Check that the directory buffer contains a valid directory
by verifying the Hugo identity string and master sequence
number are consistent at both ends of the directory.
Raises Broken directory error if verification fails.
""")
comment(0xA6DE, "Check drive is loaded", inline=True)
comment(0xA6E1, "X=0: compare index", inline=True)
comment(0xA6E3, "Get master sequence from footer", inline=True)
comment(0xA6E6, "Compare with header sequence+ID", inline=True)
comment(0xA6E9, "Mismatch: broken directory", inline=True)
comment(0xA6EB, "Compare footer sequence+ID", inline=True)
comment(0xA6EE, "Mismatch: broken directory", inline=True)
comment(0xA6F0, "Next byte", inline=True)
comment(0xA6F1, 'Check against "Hugo" string', inline=True)
comment(0xA6F4, "Checked all 5 bytes (seq+Hugo)?", inline=True)
comment(0xA6F6, "No, continue checking", inline=True)

# check_wksp_checksum (&A731)
comment(0xA731, "Calculate actual checksum", inline=True)
comment(0xA734, "Compare with stored checksum", inline=True)
comment(0xA736, "Match: workspace is valid", inline=True)
comment(0xA738, "Checksum mismatch or corruption", inline=True)
comment(0xA73A, "Set error flag", inline=True)

# calc_wksp_checksum (&A71A)
# Sum all 255 bytes of workspace page, starting from byte &FD
# downward to byte 0. Returns sum in A, Y=&FE (checksum byte).
comment(0xA71A, "Get workspace page address", inline=True)
comment(0xA71D, "Y=&FD: start from byte 253", inline=True)
comment(0xA71F, "A=&FD: initial accumulator", inline=True)
comment(0xA720, "Clear carry for addition", inline=True)
comment(0xA721, "Add workspace byte to checksum", inline=True)
comment(0xA723, "Next byte down", inline=True)
comment(0xA724, "Loop until Y wraps to 0", inline=True)
comment(0xA726, "Add byte 0", inline=True)
comment(0xA728, "Y=&FE: index of checksum byte", inline=True)

# store_wksp_checksum_ba_y (&A72B)
comment(0xA72B, "Calculate checksum", inline=True)
comment(0xA72E, "Store at (&BA)+&FE", inline=True)

# compare_ext_to_ptr (&AD16)
# Compares 4-byte EXT and PTR for current channel.
# Returns C clear if EXT == PTR (at end of file).
# Returns C set if EXT != PTR (not at EOF).
comment(0xAD16, "Get channel index", inline=True)
comment(0xAD18, "Compare EXT high byte", inline=True)
comment(0xAD1B, "With PTR high byte", inline=True)
comment(0xAD1E, "Different: not at EOF (C set)", inline=True)
comment(0xAD20, "Compare EXT mid-high byte", inline=True)
comment(0xAD23, "With PTR mid-high byte", inline=True)
comment(0xAD26, "Different: not at EOF", inline=True)
comment(0xAD28, "Compare EXT mid-low byte", inline=True)
comment(0xAD2B, "With PTR mid-low byte", inline=True)
comment(0xAD2E, "Different: not at EOF", inline=True)
comment(0xAD30, "Compare EXT low byte", inline=True)
comment(0xAD33, "With PTR low byte", inline=True)
comment(0xAD36, "Different: not at EOF", inline=True)
comment(0xAD38, "All equal: C=0, at EOF", inline=True)

# star_close (&B1B3)
# A=0 with Y=0 tells OSFIND to close all files on all drives.
comment(0xB1B3, "A=0: OSFIND close function", inline=True)
comment(0xB1B5, "Y=0: close all files", inline=True)

# floppy_set_side_1 (&BD22)
comment(0xBD22, "Set side select flag", inline=True)

# Boot file strings (label and byte directives for boot_option_addr_table
# are in the interstitial data section near the entry() calls)
label(0x9A7B, "str_l_boot")
label(0x9A7D, "str_run_boot")     # inside str_l_boot: "$.!BOOT" for *RUN
stringcr(0x9A7B)
comment(0x9A7B, '"L.$.!BOOT" + CR: load boot file', inline=True)
label(0x9A85, "str_e_boot")
stringcr(0x9A85)
comment(0x9A85, '"E.$.!BOOT" + CR: exec boot file', inline=True)
label(0xBD85, "tube_format_xfer_loop")
label(0xBD89, "tube_format_delay_loop")
label(0xBD97, "direct_format_copy")
label(0xBD9A, "direct_format_copy_loop")
label(0xBDA2, "format_track_data_ready")
label(0xBDA6, "issue_fdc_track_command")
label(0xBDC5, "wait_format_track_complete")
label(0xBDD7, "format_next_track")
label(0xBDFB, "format_double_sided")
label(0xBE0C, "set_format_sector_id")
label(0xBE27, "check_format_complete")
label(0xBE29, "format_track_loop")
label(0xBE33, "wait_format_nmi_complete")
label(0xBE4E, "format_verify_pass")
label(0xBE78, "clear_verify_seek_flag")
label(0xBE84, "execute_fdc_seek")
label(0xBE97, "wait_seek_complete")
label(0xBE9D, "check_seek_error")
label(0xBEBC, "seek_with_stepping")
label(0xBECF, "begin_step_sequence")
label(0xBED3, "check_step_direction")
label(0xBEDF, "step_outward")
label(0xBEE7, "step_inward")
label(0xBEED, "issue_step_command")
label(0xBEF0, "step_track_counter")
label(0xBEF2, "steps_remaining_check")
label(0xBEF4, "step_loop")
label(0xBEFF, "setup_track_for_rw")
label(0xBF0F, "get_sector_from_block")
label(0xBF19, "adjust_for_partial_sector")
label(0xBF23, "check_sectors_remaining")
label(0xBF25, "issue_multi_sector_rw")
label(0xBF47, "handle_sector_error")
label(0xBF51, "restore_track_zero")
label(0xBF66, "bad_address_error")
label(0xBF6A, "branch_to_floppy_error")
label(0xBF6C, "check_multi_sector_range")
label(0xBF80, "volume_error")
label(0xBFCD, "store_second_partial")
label(0xBFD8, "save_error_and_release_nmi")
label(0xBFE0, "release_tube_after_floppy")
label(0xBFF1, "return_error_code")
comment(0x9A85, "E.$.!BOOT (exec boot file)", inline=True)

# service_call_handler (&9AA3)
comment(0x9AA3, "Save service call number", inline=True)
comment(0x9AA4, "Service 1: absolute workspace claim?", inline=True)
comment(0x9AA8, "Read our ROM status byte", inline=True)
comment(0x9AAB, "Clear bit 6 (ADFS workspace claimed)", inline=True)
comment(0x9AAD, "Store updated status", inline=True)
comment(0x9AB0, "Read ROM status byte", inline=True)
comment(0x9AB3, "Bit 6 set (workspace claimed)?", inline=True)
comment(0x9AB5, "No, continue with dispatch", inline=True)
comment(0x9AB7, "Yes, discard call and return", inline=True)
comment(0x9AB9, "Restore service call number", inline=True)
comment(0x9ABA, "Service &12: select filing system?", inline=True)
comment(0x9ABC, "Yes, handle FS selection", inline=True)
comment(0x9ABE, "Service >= &0A?", inline=True)
comment(0x9AC0, "Yes, not for us, return", inline=True)
comment(0x9AC2, "Transfer to X for table index", inline=True)
comment(0x9AC3, "Get dispatch address high byte", inline=True)
comment(0x9AC7, "Get dispatch address low byte", inline=True)
comment(0x9ACB, "Restore service number to A", inline=True)
comment(0x9ACC, "Get our ROM number", inline=True)
comment(0x9ACE, "RTS-dispatch to service handler", inline=True)

# service_handler_1 (&9ACF) - ROM filing system init
comment(0x9ACF, "Check if floppy hardware present", inline=True)
comment(0x9AD2, "Increment result counter", inline=True)
comment(0x9AD5, "No floppy, check hard drive", inline=True)
comment(0x9AD7, "Check if hard drive present", inline=True)
comment(0x9ADA, "Not present, skip ADFS init", inline=True)
comment(0x9ADC, "Mark ROM as having ADFS workspace", inline=True)
comment(0x9ADE, "Get our ROM number", inline=True)
comment(0x9AE0, "Store flag in ROM status table", inline=True)
comment(0x9AE3, "Return A=1: service handled", inline=True)
comment(0x9AE6, "Return A=1: claim 1 page", inline=True)
comment(0x9AEA, "Y < &1C (PAGE already high enough)?", inline=True)
comment(0x9AEC, "Yes, don't change PAGE", inline=True)
comment(0x9AEE, "Y=&1C: ADFS PAGE value high byte", inline=True)

# service_handler_2 (&9AF1) - private workspace claim
comment(0x9AF1, "Save workspace page in ROM table", inline=True)
comment(0x9AF5, "Save Y on stack", inline=True)
comment(0x9AF6, "Check break type", inline=True)
comment(0x9AF9, "Soft break, skip workspace init", inline=True)
comment(0x9AFB, "Get workspace base address", inline=True)
comment(0x9AFF, "Get default workspace byte", inline=True)
comment(0x9B02, "Past initialisation data (Y>=&1D)?", inline=True)
comment(0x9B04, "No, use default value from table", inline=True)
comment(0x9B08, "Store byte in workspace", inline=True)
comment(0x9B0A, "Next byte", inline=True)
comment(0x9B0B, "Loop for all 256 workspace bytes", inline=True)
comment(0x9B13, "Y=next byte in workspace", inline=True)
comment(0x9B14, "Read stored workspace byte", inline=True)
comment(0x9B16, "Is it &FF (uninitialised)?", inline=True)
comment(0x9B18, "No, workspace valid from soft break", inline=True)
comment(0x9B30, "Restore Y (original service param)", inline=True)
comment(0x9B32, "Get our ROM number", inline=True)
comment(0x9B34, "Increment Y (next workspace page)", inline=True)
comment(0x9B35, "A=2: return service 2 handled", inline=True)
comment(0x9B38, "Service &12: select filing system?", inline=True)
comment(0x9B3A, "No, return", inline=True)
comment(0x9B3C, "Y=8: ADFS filing system number", inline=True)
comment(0x9B3D, "Save on stack twice for later", inline=True)
comment(0x9B3F, "Always branch to FS init code", inline=True)

# service_handler_3 (&9B41) - auto-boot
comment(0x9B41, "Save Y (boot flag)", inline=True)
comment(0x9B43, "OSBYTE &7A: keyboard scan", inline=True)
comment(0x9B48, "Key pressed? (X=-1 means no)", inline=True)
comment(0x9B49, "Yes, key pressed - check which", inline=True)
comment(0x9B4B, "No key: try hard drive boot", inline=True)
comment(0x9B4E, "Hard drive found?", inline=True)
comment(0x9B50, "Check break type", inline=True)
comment(0x9B53, "Power-on break? Skip to boot", inline=True)
comment(0x9B55, "X=&44: floppy drive 4 default", inline=True)
comment(0x9B57, "Adjust key code", inline=True)
comment(0x9B58, "Shift (key 122-1)?", inline=True)
comment(0x9B5C, "A (key 66-1)?", inline=True)

# generate_error (&829A)
comment(0x829A, "Error code &25 = drive not present?", inline=True)
comment(0x829C, "Yes, restore drive and raise error", inline=True)
comment(0x829E, "Error code &65 = volume error?", inline=True)
comment(0x82A0, "Yes, restore drive and raise error", inline=True)
comment(0x82A2, "Error code &6F = drive overrun?", inline=True)
comment(0x82A4, "No, check other error codes", inline=True)
comment(0x82A6, "Acknowledge Escape condition", inline=True)
comment(0x82AB, "Invalidate FSM and directory", inline=True)
comment(0x82B9, "Error code &04 = drive not ready?", inline=True)
comment(0x82D1, "Error code &40 = write protected?", inline=True)
comment(0x82D3, "Yes, generate Disc protected error", inline=True)
comment(0x82D5, "Convert SCSI error to disc error", inline=True)
comment(0x82D8, "X = suffix control", inline=True)
comment(0x82E8, "Write protected: save drive state", inline=True)

# wait_ensuring (&8305)
comment(0x8305, "A=1: test bit 0 of zp_flags", inline=True)
comment(0x8307, "Save flags", inline=True)
comment(0x8308, "Enable interrupts briefly", inline=True)
comment(0x8309, "Restore flags", inline=True)
comment(0x830A, "Bit 0 set (ensuring)?", inline=True)
comment(0x830C, "Yes, keep waiting", inline=True)

# scsi_wait_for_req (&830F)
comment(0x830F, "Save A on stack", inline=True)
comment(0x8310, "Read SCSI status", inline=True)
comment(0x8313, "Check REQ bit (bit 5)", inline=True)
comment(0x8315, "Loop until REQ asserted", inline=True)
comment(0x8317, "Restore A", inline=True)
comment(0x8318, "Test C/D and MSG bits via BIT", inline=True)

# scsi_send_byte_a (&831B)
comment(0x831B, "Wait for SCSI REQ", inline=True)
comment(0x831E, "MSG phase? Abort command", inline=True)
comment(0x8320, "Write data byte to SCSI bus", inline=True)
comment(0x8323, "A=0: success", inline=True)
comment(0x8326, "Pop 2 return addresses from stack", inline=True)
comment(0x8328, "Jump to status/message phase handler", inline=True)

# error_append_hex (&842D)
comment(0x842D, "Save byte value", inline=True)
comment(0x842E, "Shift high nibble to low nibble", inline=True)
comment(0x8432, "Output high nibble as hex digit", inline=True)
comment(0x8435, "Restore original byte", inline=True)
comment(0x8436, "Convert low nibble and output", inline=True)
comment(0x8439, "Advance position in error block", inline=True)
comment(0x843A, "Store hex digit character", inline=True)

# hex_digit (&843E)
comment(0x843E, "Isolate low nibble", inline=True)
comment(0x8440, "Merge with &30 for ASCII '0'-'?'", inline=True)
comment(0x8442, "Result > '9' (i.e. A-F)?", inline=True)
comment(0x8444, "No, digit is 0-9, done", inline=True)
comment(0x8446, "Add 7 to get 'A'-'F' (6 + carry)", inline=True)

# error_append_dec (&8449)
comment(0x8449, "Set V flag for leading zero suppress", inline=True)
comment(0x844C, "X=100: divide by hundreds", inline=True)
comment(0x844E, "Output hundreds digit", inline=True)
comment(0x8451, "X=10: divide by tens", inline=True)
comment(0x8453, "Output tens digit", inline=True)
comment(0x8456, "Clear V: always show units digit", inline=True)
comment(0x8457, "X=1: divide by ones", inline=True)
comment(0x8459, "Save V flag (leading zero suppress)", inline=True)
comment(0x845A, "Store divisor", inline=True)
comment(0x845C, "X='/': ASCII digit will be X+1", inline=True)
comment(0x845E, "Set carry for subtraction", inline=True)
comment(0x845F, "Increment quotient digit", inline=True)
comment(0x8460, "Subtract divisor", inline=True)
comment(0x8462, "Loop while result >= 0", inline=True)
comment(0x8464, "Add divisor back (went too far)", inline=True)
comment(0x8466, "Restore V flag", inline=True)
comment(0x8467, "Save remainder", inline=True)
comment(0x8468, "Get ASCII digit", inline=True)
comment(0x8469, "V set: suppress leading zeros", inline=True)
comment(0x846B, "Is it '0'?", inline=True)
comment(0x846D, "Yes, skip (suppress leading zero)", inline=True)
comment(0x846F, "Not zero: clear V, show from now on", inline=True)
comment(0x8470, "Advance position", inline=True)
comment(0x8471, "Store decimal digit", inline=True)
comment(0x8474, "Restore remainder", inline=True)

# sub_c832b - save drive state for error handling
comment(0x832B, "Check if drive was already saved", inline=True)
comment(0x832E, "Non-zero means drive already saved", inline=True)
comment(0x832F, "Already saved, just raise the error", inline=True)
comment(0x8331, "Check alternative workspace", inline=True)
comment(0x8337, "Copy CSD sector info to workspace", inline=True)
comment(0x8342, "Save current drive for error message", inline=True)

# reload_fsm_and_dir_then_brk (&8348)
comment(0x8348, "Ensure directory/FSM state is clean", inline=True)
comment(0x834B, "Clear FSM-inconsistent flag (bit 4)", inline=True)

# generate_error_suffix_x (&8353)
# Builds a BRK error block on page 1 from inline data:
#   JSR generate_error_suffix_x / error_code / "message" / &00
# Appends " at :D/SSSSSS" suffix if X != 0
# Appends " on channel N" if a channel is active
comment(0x8353, "Pop return address (inline data ptr)", inline=True)
comment(0x8356, "High byte of inline data address", inline=True)
comment(0x8359, "Clear FSM-inconsistent flag (bit 4)", inline=True)
comment(0x835F, "Y=0: index into inline error data", inline=True)
comment(0x8361, "Copy inline error message to page 1", inline=True)
comment(0x8364, "Store in error block on page 1", inline=True)
comment(0x8367, "Loop until zero terminator", inline=True)
comment(0x8369, "X=0 means no suffix wanted", inline=True)
comment(0x836A, "Skip suffix, go to channel check", inline=True)
comment(0x836C, "Append space before suffix", inline=True)
comment(0x8371, "Check if suffix is hex or decimal", inline=True)
comment(0x8372, "Suffix value >= '0'?", inline=True)
comment(0x8374, "Yes, check for colon", inline=True)
comment(0x8376, "Append as hex number", inline=True)
comment(0x837C, "Suffix value >= ':'?", inline=True)
comment(0x837E, "Yes, append as hex", inline=True)
comment(0x8380, "Append as decimal number", inline=True)
comment(0x8383, "Copy reversed ' at :' suffix", inline=True)
comment(0x8385, "Next position", inline=True)
comment(0x8386, "Get char from reversed string", inline=True)
comment(0x8389, "Store in error block", inline=True)
comment(0x838F, "Get drive number from error sector", inline=True)
comment(0x8392, "Shift drive bits into low nibble", inline=True)
comment(0x8396, "Convert to hex digit character", inline=True)
comment(0x8399, "Advance position", inline=True)
comment(0x839A, "Store drive digit", inline=True)
comment(0x839D, "Append '/' separator", inline=True)
comment(0x83A3, "Get sector high byte", inline=True)
comment(0x83A6, "Mask to 5-bit sector address", inline=True)
comment(0x83A8, "X=2: output 3 bytes of sector addr", inline=True)
comment(0x83AA, "Always branch to loop entry", inline=True)
comment(0x83AC, "Get next sector byte from workspace", inline=True)
comment(0x83AF, "Append as two hex digits", inline=True)
comment(0x83B2, "Next byte", inline=True)
comment(0x83B3, "Loop for 3 sector bytes", inline=True)
comment(0x83B5, "Advance past suffix", inline=True)
comment(0x83B6, "Zero-terminate the error string", inline=True)
comment(0x83BB, "Check for open channel suffix", inline=True)
comment(0x83BE, "No channel active, skip", inline=True)
comment(0x83C0, "X=&0B: copy 12-char ' on channel '", inline=True)
comment(0x83C3, "Get char from reversed string", inline=True)
comment(0x83C7, "Store in error block", inline=True)
comment(0x83CD, "Get channel number", inline=True)
comment(0x83D0, "Append as decimal digits", inline=True)
comment(0x83D5, "OSBYTE &C6: read EXEC file handle", inline=True)
comment(0x83DA, "OSBYTE &C6: read/write EXEC handle", inline=True)
comment(0x83DD, "Is EXEC on this channel?", inline=True)
comment(0x83E4, "Yes, close EXEC file", inline=True)
comment(0x83E6, "Is SPOOL on this channel?", inline=True)
comment(0x83E9, "No, skip", inline=True)
comment(0x83EB, "Close SPOOL file (ptr at &9C)", inline=True)
comment(0x83ED, "Execute close via OSCLI", inline=True)
comment(0x83F2, "Check for additional error handling", inline=True)
comment(0x83FA, "Store BRK opcode at start of page 1", inline=True)
comment(0x83FF, "Zero-terminate after channel suffix", inline=True)
comment(0x8402, "Release Tube before raising error", inline=True)
comment(0x8405, "Check error code", inline=True)
comment(0x8408, "Is it &C7 (Disc error)?", inline=True)
comment(0x840A, "No, just execute the BRK", inline=True)
comment(0x840C, "Close SPOOL before disc error", inline=True)
comment(0x8411, "Close EXEC before disc error", inline=True)
comment(0x8416, "Invalidate FSM/dir after disc error", inline=True)
comment(0x8419, "Jump to BRK block on page 1", inline=True)

# scsi_start_command (&8065)
comment(0x8065, "Y=0 for normal start", inline=True)
comment(0x8067, "SCSI ID bit pattern = 1 (drive 0)", inline=True)
comment(0x8069, "Save SCSI ID on stack", inline=True)
comment(0x806A, "Wait for BSY to deassert", inline=True)
comment(0x806D, "Check BSY bit", inline=True)
comment(0x806F, "Loop while BSY asserted", inline=True)
comment(0x8071, "Retrieve SCSI ID", inline=True)
comment(0x8072, "Assert ID on SCSI data bus", inline=True)
comment(0x8075, "Assert SEL to select target", inline=True)
comment(0x8078, "Wait for target to assert BSY", inline=True)
comment(0x807B, "Check BSY bit", inline=True)
comment(0x807D, "Loop until BSY asserted", inline=True)

# command_exec_xy (&8089)
comment(0x8089, "Wait if files being ensured", inline=True)
comment(0x808C, "Store control block address low", inline=True)
comment(0x808E, "Store control block address high", inline=True)
comment(0x8090, "Ensure directory is loaded", inline=True)
comment(0x8093, "Byte 5 of control block = command", inline=True)
comment(0x8097, "Format track?", inline=True)
comment(0x8099, "Yes, skip retries", inline=True)
comment(0x809B, "Seek?", inline=True)
comment(0x809D, "Yes, skip retries", inline=True)
comment(0x809F, "Set default retry count", inline=True)
comment(0x80A2, "Always branch (retry count >= 0)", inline=True)
comment(0x80A4, "Execute the disc operation", inline=True)
comment(0x80A7, "Success, return", inline=True)
comment(0x80A9, "Not-ready error?", inline=True)
comment(0x80AB, "No, check if retries exhausted", inline=True)
comment(0x80AD, "Delay loop for not-ready", inline=True)
comment(0x80AF, "Check for Escape during delay", inline=True)
comment(0x80B1, "Escape pressed, abort", inline=True)
comment(0x80BE, "Drive-not-present error?", inline=True)
comment(0x80C0, "Yes, no point retrying", inline=True)
comment(0x80C2, "Decrement retry counter", inline=True)
comment(0x80C4, "More retries remaining", inline=True)

# command_exec_start_exec (&80C6)
comment(0x80C6, "Check zp_flags for hard drive", inline=True)
comment(0x80C8, "Bit 5: hard drive present?", inline=True)
comment(0x80CA, "Yes, use hard drive command", inline=True)
comment(0x80CC, "Floppy disc operation", inline=True)
comment(0x80CF, "Success, return", inline=True)
comment(0x80D1, "Save error code", inline=True)
comment(0x80D2, "Byte 6: drive + sector high", inline=True)
comment(0x80D6, "Combine with current drive number", inline=True)
comment(0x80D9, "Store in error sector workspace", inline=True)
comment(0x80DD, "Byte 7: sector mid", inline=True)
comment(0x80DF, "Store sector mid byte", inline=True)
comment(0x80E3, "Byte 8: sector low", inline=True)
comment(0x80E5, "Store sector low byte", inline=True)
comment(0x80E8, "Retrieve error code", inline=True)
comment(0x80E9, "Store error code", inline=True)

# ---------------------------------------------------------------------------
# Gap-filling comments to reach 100% coverage
# Mostly RTS instructions and loop body items in nearly-complete routines
# ---------------------------------------------------------------------------

# command_set_retries - remaining items
comment(0x8083, "Store in retry counter", inline=True)
comment(0x8085, "Return", inline=True)
comment(0x8086, "Escape during retry: abort", inline=True)

# reload_fsm_and_dir_then_brk - remaining items
comment(0x834D, "Clear FSM inconsistent flag", inline=True)
comment(0x834F, "Store updated flags", inline=True)

# hd_command - remaining items (gaps in data transfer)
comment(0x80EF, "Get byte from control block", inline=True)
comment(0x80FA, "Get byte from control block", inline=True)
comment(0x80FF, "Get byte from control block", inline=True)
comment(0x8104, "Get byte from control block", inline=True)
comment(0x810B, "Get byte from control block", inline=True)
comment(0x8116, "Get byte from control block", inline=True)
comment(0x811C, "Get byte from control block", inline=True)
comment(0x8124, "Jump into command send loop", inline=True)
comment(0x8134, "More command bytes to send", inline=True)
comment(0x814F, "Y=&10: Tube workspace page", inline=True)
comment(0x8158, "Restore processor flags", inline=True)

# tube_start_xfer - remaining items
comment(0x81FB, "Return (also used as delay)", inline=True)
comment(0x81FE, "Y=&10: Tube workspace page", inline=True)
comment(0x820A, "Save flags before SEI", inline=True)
comment(0x8210, "NOP timing delay for Tube", inline=True)
comment(0x8211, "NOP timing delay", inline=True)
comment(0x8212, "NOP timing delay", inline=True)
comment(0x8220, "Continue outer transfer loop", inline=True)
comment(0x8222, "Save flags for read path", inline=True)
comment(0x8228, "NOP timing delay for Tube", inline=True)
comment(0x8229, "NOP timing delay", inline=True)
comment(0x822A, "NOP timing delay", inline=True)
comment(0x8238, "Continue outer transfer loop", inline=True)

# osfile_handler - remaining items
comment(0x9245, "Clear current channel", inline=True)
comment(0x9249, "Transfer A*2 to X", inline=True)
comment(0x924B, "X = A*2 + 2 (dispatch table offset)", inline=True)
comment(0x9250, "Function >= 8: unsupported", inline=True)
comment(0x9255, "Push dispatch address high", inline=True)
comment(0x9259, "Push dispatch address low", inline=True)
comment(0x927E, "Set pointer high byte", inline=True)
comment(0x9287, "Y=0: start of entry name", inline=True)
comment(0x9291, "Print character via OSASCI", inline=True)
comment(0x9298, "Return", inline=True)
comment(0x9299, "Print space padding", inline=True)
comment(0x929F, "Return", inline=True)

# parse_dir_argument - remaining items
comment(0x948D, "Found directory: loop complete", inline=True)
comment(0x948F, "Not found: raise error", inline=True)
comment(0x9495, "Continue to next path component", inline=True)
comment(0x949A, "Increment: was &FF, now 0", inline=True)
comment(0x949B, "Non-zero: skip CSD copy", inline=True)
comment(0x949F, "Get CSD sector byte", inline=True)
comment(0x94A2, "Copy to CSD workspace", inline=True)
comment(0x94A5, "Next byte", inline=True)
comment(0x94A6, "Loop for 3 bytes", inline=True)
comment(0x94AD, "Copy template byte to workspace", inline=True)
comment(0x94B0, "Next byte", inline=True)
comment(0x94B1, "Loop for 11 bytes", inline=True)
comment(0x94BF, "Next sector address byte", inline=True)
comment(0x94C0, "Decrement counter", inline=True)
comment(0x94C1, "Loop for 3 bytes", inline=True)

# service_handler_2 - remaining items (workspace init)
comment(0x9AF2, "Store workspace page in ROM table", inline=True)
comment(0x9AFE, "Transfer Y to A", inline=True)
comment(0x9B06, "A=0: zero for unused workspace", inline=True)
comment(0x9B0D, "Store workspace checksum", inline=True)
comment(0x9B1A, "Clear Tube-present flag (bit 7)", inline=True)
comment(0x9B1C, "Clear carry for rotate", inline=True)
comment(0x9B1D, "Restore bit 0, Tube flag cleared", inline=True)
comment(0x9B22, "X=0: keyboard buffer number", inline=True)
comment(0x9B24, "OSBYTE &15: flush buffer", inline=True)
comment(0x9B29, "OSBYTE &8A: insert into buffer", inline=True)
comment(0x9B2B, "Y=&CA: character to insert", inline=True)
comment(0x9B31, "Restore Y", inline=True)
comment(0x9B37, "Return", inline=True)
comment(0x9B3E, "Push again (2 copies on stack)", inline=True)

# service_handler_4 - remaining items
comment(0x9CDB, "Save Y for later restore", inline=True)
comment(0x9CDE, "Push default prefix flag (&FF)", inline=True)
comment(0x9CE8, "Replace with 'C' (FSC code)", inline=True)
comment(0x9CEA, "Push FSC code", inline=True)
comment(0x9CFC, "Next char in 'ADFS'", inline=True)
comment(0x9CFD, "Loop for 4 characters", inline=True)
comment(0x9D01, "Advance past matched space", inline=True)
comment(0x9D09, "Transfer prefix flag to X", inline=True)
comment(0x9D0B, "Transfer back to A", inline=True)
comment(0x9D0C, "Push for later restore", inline=True)
comment(0x9D0D, "Push again", inline=True)
comment(0x9D12, "Clean up stack (discard flag)", inline=True)
comment(0x9D18, "Return (not our command)", inline=True)

# service_handler_9 (*HELP) - remaining items
comment(0x9DBF, "Save text pointer on stack", inline=True)
comment(0x9DD2, "Store flag for help type", inline=True)
comment(0x9DD9, "Return", inline=True)
comment(0x9DDB, "Get next char from help text", inline=True)
comment(0x9DE2, "Pop 2 return addresses", inline=True)
comment(0x9DE8, "Loop skipping non-space chars", inline=True)
comment(0x9DED, "Loop skipping space chars", inline=True)
comment(0x9E2C, "Save table index on stack", inline=True)
comment(0x9E32, "Shift high nibble to low", inline=True)
comment(0x9E33, "4 right shifts total", inline=True)
comment(0x9E34, "4th shift", inline=True)
comment(0x9E42, "Restore table index to X", inline=True)
comment(0x9E44, "Skip past 1st dispatch byte", inline=True)
comment(0x9E45, "Skip past 2nd dispatch byte", inline=True)

# star_mount - remaining items
comment(0xA169, "Y=&A1: control block page", inline=True)
comment(0xA170, "Point to root dir path '$'", inline=True)
comment(0xA172, "Path string is in this page", inline=True)
comment(0xA174, "Store path high byte", inline=True)
comment(0xA17C, "Compare with target drive", inline=True)
comment(0xA183, "Invalidate prev dir high byte", inline=True)
comment(0xA186, "Invalidate prev dir drive byte", inline=True)
comment(0xA18C, "Compare with target drive", inline=True)
comment(0xA193, "Invalidate lib sector high", inline=True)
comment(0xA196, "Invalidate lib drive byte", inline=True)
comment(0xA19E, "Return", inline=True)

# compare_ext_to_ptr - remaining items (sub_cad3a / cad53)
comment(0xAD39, "Return (EXT == PTR: C clear)", inline=True)
comment(0xAD3A, "Get file handle from (&B4)", inline=True)
comment(0xAD3F, "Rotate flags bit 0 into carry", inline=True)
comment(0xAD40, "Carry set: skip flush", inline=True)
comment(0xAD42, "Ensure workspace is valid", inline=True)
comment(0xAD45, "Flush channel buffer if dirty", inline=True)
comment(0xAD4B, "X=0: PTR == EXT result", inline=True)
comment(0xAD4D, "Carry set: PTR == EXT", inline=True)
comment(0xAD50, "Restore Y from (&B5)", inline=True)
comment(0xAD52, "Return", inline=True)
comment(0xAD53, "Clear EOF and buffer dirty flags", inline=True)
comment(0xAD56, "Keep bits 7,6,3 (writeable,open)", inline=True)
comment(0xAD58, "Store updated flags", inline=True)

# floppy_wait_nmi_finish - remaining items (sub_cbcfd)
comment(0xBCC7, "Transfer already complete, return", inline=True)
comment(0xBCDA, "Store drive overrun error code", inline=True)
comment(0xBCFD, "Check read/write direction", inline=True)
comment(0xBCFF, "Reading: use read command", inline=True)
comment(0xBD01, "Get current track", inline=True)
comment(0xBD03, "Track >= 20?", inline=True)
comment(0xBD05, "A=&A0: write command base", inline=True)
comment(0xBD07, "Track < 20: no step rate delay", inline=True)
comment(0xBD09, "OR in step rate from settings", inline=True)
comment(0xBD0C, "Always branch (non-zero result)", inline=True)
comment(0xBD0E, "A=&80: read command base", inline=True)
comment(0xBD13, "Issue FDC command", inline=True)

# floppy_set_side_1 and helpers - remaining items
comment(0xBD25, "Set bit 2 (side 1 flag)", inline=True)
comment(0xBD27, "Store in NMI drive control byte", inline=True)
comment(0xBD2A, "Return", inline=True)
comment(0xBD2B, "Clear bit 0 of transfer state", inline=True)
comment(0xBD2D, "Clear carry", inline=True)
comment(0xBD2E, "Restore bit 0 cleared", inline=True)
comment(0xBD30, "Return", inline=True)
comment(0xBD31, "Get transfer state", inline=True)
comment(0xBD33, "Clear bit 3 (side flag)", inline=True)
comment(0xBD35, "Store updated state", inline=True)
comment(0xBD37, "Return", inline=True)
comment(0xBD38, "Get transfer state", inline=True)
comment(0xBD3A, "Clear bit 1 (seek flag)", inline=True)
comment(0xBD3C, "Store updated state", inline=True)
comment(0xBD3E, "Return", inline=True)

# claim_tube (&8027) - remaining items
comment(0x8027, "Y=4: copy 4 bytes", inline=True)
comment(0x8032, "Next byte", inline=True)
comment(0x8033, "Loop for 4 bytes", inline=True)
comment(0x8037, "Set Tube-in-use flag", inline=True)
comment(0x8039, "Store updated flags", inline=True)
comment(0x803D, "Call Tube host to claim", inline=True)
comment(0x8042, "Return", inline=True)

# release_tube (&8043) - remaining items
comment(0x8043, "Check Tube-in-use flag", inline=True)
comment(0x8049, "Call Tube host to release", inline=True)
comment(0x804D, "Disable interrupts", inline=True)
comment(0x8050, "Clear Tube-in-use bit", inline=True)
comment(0x8052, "Store updated flags", inline=True)
comment(0x8054, "Restore interrupt state", inline=True)
comment(0x8055, "Return", inline=True)

# command_exec_xy - delay loop items
comment(0x8095, "Get command byte from control block", inline=True)
comment(0x80B3, "Set carry for subtraction", inline=True)
comment(0x80B4, "Decrement delay low byte", inline=True)
comment(0x80B6, "Inner loop not done", inline=True)
comment(0x80B8, "Decrement delay mid byte", inline=True)
comment(0x80B9, "Mid loop not done", inline=True)
comment(0x80BB, "Decrement delay high byte", inline=True)
comment(0x80BC, "Outer loop not done", inline=True)
comment(0x80D4, "Get drive+sector byte from blk", inline=True)
comment(0x80EC, "Return", inline=True)

# hd_data_transfer_256 - remaining items
comment(0x81E0, "No wrap: skip mid byte increment", inline=True)
comment(0x81E5, "No wrap: skip high byte increment", inline=True)
comment(0x81EC, "Y=&10: Tube workspace page", inline=True)
comment(0x81EE, "Return", inline=True)

# scsi_request_sense / c8287 - remaining items
comment(0x8289, "Y=&10: workspace page", inline=True)
comment(0x8290, "Return (success)", inline=True)
comment(0x8297, "Restore drive and raise error", inline=True)

# scsi_send_byte_a / sub_c832b - remaining items
comment(0x8325, "Return (byte sent OK)", inline=True)
comment(0x8327, "Pop one return address", inline=True)
comment(0x8334, "Increment: non-zero?", inline=True)
comment(0x8335, "Yes, skip CSD restore", inline=True)
comment(0x8339, "Get CSD sector byte", inline=True)
comment(0x833C, "Copy to CSD drive sector workspace", inline=True)
comment(0x833F, "Next byte", inline=True)
comment(0x8340, "Loop for 3 bytes", inline=True)
comment(0x8345, "Save current drive for error msg", inline=True)

# error_append_hex - remaining items
comment(0x842F, "(continued)", inline=True)
comment(0x8430, "(continued)", inline=True)
comment(0x8431, "(continued)", inline=True)
comment(0x843D, "Return", inline=True)

# invalidate_fsm_and_dir - remaining items
comment(0x8480, "Next byte", inline=True)
comment(0x8481, "Loop for 12 bytes", inline=True)
comment(0x8498, "Return", inline=True)

# check_filename_length - remaining items
comment(0x874D, "Next byte in entry name", inline=True)
comment(0x874E, "Loop for 10 bytes", inline=True)
comment(0x8750, "Y=1: start of object name", inline=True)
comment(0x8751, "X=0: pattern index", inline=True)

# floppy_partial_sector - remaining items
comment(0x8B3A, "Divide by 4 for buffer page index", inline=True)
comment(0x8B3B, "(continued)", inline=True)
comment(0x8B3C, "Add buffer base page (&17)", inline=True)
comment(0x8B3E, "Execute floppy partial sector op", inline=True)

# check_special_dir_char - remaining items
comment(0x9451, "Get first argument char", inline=True)
comment(0x945B, "Set (&B6) low to &C0", inline=True)
comment(0x945D, "Set (&B6) high to &16 (dir footer)", inline=True)
comment(0x945F, "Store high byte", inline=True)
comment(0x9469, "Set (&B6) low to &FE", inline=True)
comment(0x946B, "Set (&B6) high to &10 (workspace)", inline=True)
comment(0x946D, "Store high byte", inline=True)
comment(0x9470, "Return", inline=True)

# print_entry_info - remaining items
comment(0x9527, "X mod 4 == 1? Field boundary", inline=True)
comment(0x952E, "Print second padding space", inline=True)
comment(0x9532, "Clear carry for addition", inline=True)
comment(0x9535, "Transfer new Y offset", inline=True)

# service_call_handler - remaining items
comment(0x9AA6, "Not service 1, continue", inline=True)
comment(0x9AB8, "Return (service not claimed)", inline=True)
comment(0x9AC6, "Push dispatch high byte", inline=True)
comment(0x9ACA, "Push dispatch low byte", inline=True)

# service_handler_1 - remaining items
comment(0x9AE5, "Return A=1 (claim 1 page)", inline=True)
comment(0x9AE8, "Get our ROM number", inline=True)
comment(0x9AF0, "Return", inline=True)

# fscv_handler - remaining items
comment(0x9E52, "Store text pointer high", inline=True)
comment(0x9E59, "FSC >= 9: not for us", inline=True)
comment(0x9E5D, "Clear current channel", inline=True)
comment(0x9E63, "Push dispatch high byte", inline=True)
comment(0x9E67, "Push dispatch low byte", inline=True)

# star_free - remaining items
comment(0xA03A, "Next FSM byte", inline=True)
comment(0xA03B, "Decrement byte counter", inline=True)
comment(0xA049, "Return", inline=True)

# star_bye - remaining items
comment(0xA0C6, "Save current drive on stack", inline=True)
comment(0xA0E9, "Return", inline=True)

# star_dismount - remaining items
comment(0xA130, "Loop for all 10 channels", inline=True)
comment(0xA13F, "Invalidate drive status", inline=True)
comment(0xA147, "Always branch to exit code", inline=True)

# calc_total_free_space - remaining items
comment(0xA1B4, "Next byte", inline=True)
comment(0xA1B5, "Loop for 4 bytes", inline=True)
comment(0xA1C2, "Next result byte", inline=True)
comment(0xA1C3, "Loop for 3 bytes", inline=True)
comment(0xA1C5, "Return", inline=True)

# print_space_value - remaining items
comment(0xA1C9, "Print mid byte as hex", inline=True)
comment(0xA1CF, "Print low byte as hex", inline=True)
comment(0xA1D5, "Print result byte as hex", inline=True)
comment(0xA1E5, "' ' + bit 7: end of inline string", inline=True)

# Double-dabble binary-to-decimal conversion and printing
comment(0xA1E6, "X=&1F: 31 bit shifts (32-bit value)", inline=True)
comment(0xA1E8, "Store bit counter in workspace", inline=True)
comment(0xA1EB, "A=0: clear all BCD digit accumulators", inline=True)
comment(0xA1ED, "X=9: clear 10 BCD digits (0-9)", inline=True)
comment(0xA1EF, "Clear BCD digit at &1040+X", inline=True)
comment(0xA1F2, "Next digit", inline=True)
comment(0xA1F3, "Loop for all 10 digits", inline=True)
comment(0xA1F5, "Shift binary value left: byte 0", inline=True)
comment(0xA1F8, "Rotate carry into byte 1", inline=True)
comment(0xA1FB, "Rotate carry into byte 2", inline=True)
comment(0xA1FE, "Rotate carry into byte 3", inline=True)
comment(0xA201, "X=0: start from least significant digit", inline=True)
comment(0xA203, "Y=9: process 10 BCD digits", inline=True)
comment(0xA205, "Get BCD digit", inline=True)
comment(0xA208, "Rotate shifted bit into digit", inline=True)
comment(0xA209, "Digit >= 10?", inline=True)
comment(0xA20B, "No: digit is valid (0-9)", inline=True)
comment(0xA20D, "Yes: subtract 10 (carry propagates)", inline=True)
comment(0xA20F, "Store corrected BCD digit", inline=True)
comment(0xA212, "Next digit (toward most significant)", inline=True)
comment(0xA213, "Decrement digit counter", inline=True)
comment(0xA214, "Loop for all 10 digits", inline=True)
comment(0xA216, "Decrement bit counter", inline=True)
comment(0xA219, "Loop for all 31 bits", inline=True)
comment(0xA21B, "Y=' ': separator starts as space", inline=True)
comment(0xA21D, "X=8: start from most significant digit", inline=True)
comment(0xA21F, "X!=0: not at units position yet", inline=True)
comment(0xA221, "X=0: switch separator to comma", inline=True)
comment(0xA223, "Get BCD digit value", inline=True)
comment(0xA226, "Non-zero: print this digit", inline=True)
comment(0xA228, "Zero: has a non-zero digit been seen?", inline=True)
comment(0xA22A, "Yes (separator=comma): print zero", inline=True)
comment(0xA22C, "No: suppress leading zero with space", inline=True)
comment(0xA22E, "Skip to output", inline=True)
comment(0xA230, "Mark that we've seen a non-zero digit", inline=True)
comment(0xA232, "Clear carry for addition", inline=True)
comment(0xA233, "Convert BCD digit to ASCII ('0'-'9')", inline=True)
comment(0xA235, "Print digit or space", inline=True)
comment(0xA238, "At position 6 (millions boundary)?", inline=True)
comment(0xA23A, "Yes: print comma separator", inline=True)
comment(0xA23C, "At position 3 (thousands boundary)?", inline=True)
comment(0xA23E, "No: skip separator", inline=True)
comment(0xA240, "Print separator (space or comma)", inline=True)
comment(0xA241, "Output separator character", inline=True)
comment(0xA244, "Next digit (toward least significant)", inline=True)
comment(0xA245, "Loop for 9 digits (8 down to 0)", inline=True)

# restore_csd - remaining items
comment(0xA47B, "Next byte", inline=True)
comment(0xA47C, "Loop for 4 bytes", inline=True)
comment(0xA47E, "Return", inline=True)

# skip_filename - remaining items
comment(0xA4BF, "Loop scanning characters", inline=True)
comment(0xA4C6, "Clear carry for addition", inline=True)
comment(0xA4C9, "Store updated pointer low", inline=True)
comment(0xA4CD, "Increment pointer high on overflow", inline=True)

# skip_spaces - remaining items
comment(0xA4D2, "Save quote tracking flag", inline=True)
comment(0xA4E6, "Save updated quote flag", inline=True)
comment(0xA4E8, "Continue scanning", inline=True)
comment(0xA4EB, "Restore quote flag", inline=True)
comment(0xA4EC, "Clear carry for addition", inline=True)
comment(0xA4EF, "Store updated pointer low", inline=True)
comment(0xA4F1, "No overflow, return", inline=True)
comment(0xA4F3, "Increment pointer high on overflow", inline=True)
comment(0xA4F5, "Return", inline=True)

# floppy_command - remaining items
comment(0xBB15, "Save stack for error recovery", inline=True)
comment(0xBB1A, "Store transfer mode", inline=True)
comment(0xBB29, "Save stack for error recovery", inline=True)
comment(0xBB2C, "Workspace page for control block", inline=True)
comment(0xBB30, "Control block offset", inline=True)
comment(0xBB32, "Store in (&B0)", inline=True)
comment(0xBB36, "Clear transfer mode for format", inline=True)

# floppy_get_step_rate - remaining items
comment(0xBBB6, "Store in NMI side select", inline=True)
comment(0xBBBE, "X=0: read current value", inline=True)
comment(0xBBD9, "Return", inline=True)

# floppy_error - remaining items
comment(0xBFB1, "Restore stack from saved pointer", inline=True)
comment(0xBFC4, "Set bit 6 of transfer flag", inline=True)
comment(0xBFC7, "Clear carry", inline=True)
comment(0xBFC8, "Clear bit 0 of transfer flag", inline=True)
comment(0xBFCB, "Branch if first partial sector", inline=True)
comment(0xBFD0, "Get transfer state flags", inline=True)
comment(0xBFD3, "Clear bit 6", inline=True)
comment(0xBFD5, "Store updated flags", inline=True)
comment(0xBFEE, "Mark transfer as incomplete", inline=True)
comment(0xBFF5, "Return", inline=True)
stringcr(0xBFF6)
comment(0xBFF6, '"and Hugo." + CR: ROM footer text', inline=True)

# hd_command_partial_sector (&8B41) - SCSI partial sector read
# Reads one full sector via SCSI, transfers only the needed
# bytes (count in sector_count field), discarding the rest.
comment(0x8B49, "Get transfer address low from blk", inline=True)
comment(0x8B4C, "Store in (&B2)", inline=True)
comment(0x8B4E, "Get transfer address mid", inline=True)
comment(0x8B51, "Store in (&B3)", inline=True)
comment(0x8B53, "Get transfer address high", inline=True)
comment(0x8B56, "Address >= &FE00?", inline=True)
comment(0x8B58, "Below: might need Tube claim", inline=True)
comment(0x8B5A, "Get next address byte", inline=True)
comment(0x8B5D, "Is it &FF (host memory)?", inline=True)
comment(0x8B5F, "Yes: skip Tube claim", inline=True)
comment(0x8B64, "Get partial transfer byte count", inline=True)
comment(0x8B67, "Save count in X", inline=True)
comment(0x8B68, "Set sector count to 1", inline=True)
comment(0x8B6A, "Only read one sector", inline=True)
comment(0x8B6D, "SCSI read command = 8", inline=True)
comment(0x8B6F, "Store command byte", inline=True)
comment(0x8B72, "Y=0: start of 6-byte command", inline=True)
comment(0x8B74, "Get SCSI command byte", inline=True)
comment(0x8B7A, "Next command byte", inline=True)
comment(0x8B7B, "Sent all 6 bytes?", inline=True)
comment(0x8B7D, "No, send next", inline=True)
comment(0x8B7F, "Tube in use?", inline=True)
comment(0x8B81, "No Tube: skip Tube transfer setup", inline=True)
comment(0x8B83, "Save byte count from X to A", inline=True)
comment(0x8B84, "Push byte count on stack", inline=True)
comment(0x8B85, "X=&27: Tube workspace offset", inline=True)
comment(0x8B87, "Y=&10: Tube workspace page", inline=True)
comment(0x8B89, "A=1: Tube read transfer type", inline=True)
comment(0x8B8B, "Start Tube transfer", inline=True)
comment(0x8B8E, "Restore byte count", inline=True)
comment(0x8B8F, "Back to X", inline=True)
comment(0x8B90, "Y=0: data transfer byte index", inline=True)
comment(0x8B95, "Status phase: transfer complete", inline=True)
comment(0x8B97, "Read byte from SCSI data bus", inline=True)
comment(0x8B9A, "Byte count exhausted?", inline=True)
comment(0x8B9C, "Yes: discard remaining bytes", inline=True)
comment(0x8B9E, "Tube in use?", inline=True)
comment(0x8BA0, "No Tube: store in memory", inline=True)
comment(0x8BA2, "Tube timing delay", inline=True)
comment(0x8BA5, "Write byte to Tube R3", inline=True)
comment(0x8BA8, "Always branch (V always set here)", inline=True)
comment(0x8BAA, "Store byte in memory buffer", inline=True)
comment(0x8BAC, "Decrement remaining byte count", inline=True)
comment(0x8BAD, "Next transfer position", inline=True)
comment(0x8BAE, "Loop for 256 bytes (full sector)", inline=True)
comment(0x8BB0, "Status phase: get SCSI result", inline=True)
comment(0x8BC7, "Return", inline=True)
comment(0x8BD0, "Bad name error (^ or @ in context)", inline=True)

# sub_c8c62 - copy dir entry to OSFILE control block
comment(0x8C62, "Display info if *OPT1 verbose", inline=True)
comment(0x8C65, "Y=&15: start of entry data in dir", inline=True)
comment(0x8C67, "X=&0B: copy 12 bytes to workspace", inline=True)
comment(0x8C69, "Get entry data byte", inline=True)
comment(0x8C6B, "Store in disc op workspace", inline=True)
comment(0x8C6E, "Next entry byte (decreasing)", inline=True)
comment(0x8C6F, "Next workspace byte (decreasing)", inline=True)
comment(0x8C70, "Loop for 12 bytes", inline=True)
comment(0x8C72, "Y=&0D: copy to OSFILE control block", inline=True)
comment(0x8C74, "X=&0B: 12 bytes", inline=True)
comment(0x8C76, "Get byte from workspace", inline=True)
comment(0x8C79, "Store in OSFILE control block", inline=True)
comment(0x8C7B, "Next control block byte", inline=True)
comment(0x8C7C, "Next workspace byte", inline=True)
comment(0x8C7D, "Loop for 12 bytes", inline=True)
comment(0x8C7F, """\
Extract access attributes from entry name bytes.
Bit 7 of each name byte stores one access attribute:
  byte 0 bit 7 = R (read)
  byte 1 bit 7 = W (write)
  byte 2 bit 7 = L (locked)
The loop collects these into 00000LWR, then the
bit-shuffling below produces the OSFILE access byte
format L0WRL0WR, duplicating the same R/W/L bits into
both the owner (bits 3,1,0) and public (bits 7,5,4)
nibbles. ADFS does not distinguish owner from public.""")
comment(0x8C7F, "Clear access accumulator", inline=True)
comment(0x8C81, "Store zero in workspace", inline=True)
comment(0x8C84, "Y=2: extract from bytes 2,1,0", inline=True)
comment(0x8C86, "Get name byte from entry", inline=True)
comment(0x8C88, "Shift bit 7 (attribute) into carry", inline=True)
comment(0x8C89, "Rotate carry into accumulator", inline=True)
comment(0x8C8C, "Next name byte (decreasing Y)", inline=True)
comment(0x8C8D, "Loop: Y=2(L), Y=1(W), Y=0(R)", inline=True)
comment(0x8C8F, "A = 00000LWR, C = 0", inline=True)
comment(0x8C92, "A = 000000LW, C = R", inline=True)
comment(0x8C93, "A = R000000L, C = W", inline=True)
comment(0x8C94, "A = WR000000, C = L", inline=True)
comment(0x8C95, "Save C = L on stack", inline=True)
comment(0x8C96, "A = 0WR00000, C = 0 (LSR)", inline=True)
comment(0x8C97, "Restore C = L from stack", inline=True)
comment(0x8C98, "A = L0WR0000, C = 0", inline=True)
comment(0x8C99, "Store L0WR0000", inline=True)
comment(0x8C9C, "A = 0000L0WR after 4x LSR", inline=True)
comment(0x8C9D, "Second shift", inline=True)
comment(0x8C9E, "Third shift", inline=True)
comment(0x8C9F, "Fourth shift", inline=True)
comment(0x8CA0, "L0WR0000 OR 0000L0WR = L0WRL0WR", inline=True)
comment(0x8CA3, "Y=&0E: OSFILE access byte position", inline=True)
comment(0x8CA5, "Store access byte in control block", inline=True)
comment(0x8CA7, "Return", inline=True)

# sub_c8ca8 - OSFILE read catalogue info (A=5)
comment(0x8CA8, "Y=0: get filename addr from block", inline=True)
comment(0x8CAA, "Get filename address low", inline=True)
comment(0x8CAC, "Store in (&B4)", inline=True)
comment(0x8CAF, "Get filename address high", inline=True)
comment(0x8CB1, "Store in (&B5)", inline=True)
comment(0x8CB3, "Search for file in directory", inline=True)
comment(0x8CB6, "Found? Copy catalogue info", inline=True)
comment(0x8CB8, "Y=4: check E attribute", inline=True)
comment(0x8CBA, "Get E attribute byte", inline=True)
comment(0x8CBC, "Bit 7 clear: not E, copy info", inline=True)
comment(0x8CBE, "E attribute: return A=&FF", inline=True)
comment(0x8CC0, "Save workspace and return", inline=True)
comment(0x8CC3, "Copy catalogue info to block", inline=True)
comment(0x8CC6, "Save workspace and return", inline=True)

# sub_c8cc9 - OSFILE write catalogue / parse path
comment(0x8CC9, "Y=0: get filename from block", inline=True)
comment(0x8CCB, "Get filename address low", inline=True)
comment(0x8CCD, "Store in (&B4)", inline=True)
comment(0x8CD0, "Get filename address high", inline=True)
comment(0x8CD2, "Store in (&B5)", inline=True)
comment(0x8CD4, "Parse path and set up directory", inline=True)
comment(0x8CD7, "Search for file", inline=True)
comment(0x8CDA, "Found: return Z set", inline=True)
comment(0x8CDF, "Z clear: check for create", inline=True)
comment(0x8CE1, "Return", inline=True)

# sub_c8ce2 - OSFILE delete (A=6)
comment(0x8CE2, "Parse filename and search", inline=True)
comment(0x8CE5, "Found: proceed to delete", inline=True)

# sub_c8ce9 - OSFILE create (A=7)
comment(0x8CE9, "Parse filename and search", inline=True)
comment(0x8CEC, "Found: check if directory", inline=True)
comment(0x8CEE, "Y=0: check remaining path", inline=True)
comment(0x8CF0, "Get next path character", inline=True)
comment(0x8CF2, "Is it '.' (path separator)?", inline=True)
comment(0x8CF4, "Yes: check for ^ or @ error", inline=True)
comment(0x8CF6, "Check for ^ or @ prefix error", inline=True)
comment(0x8CF9, "Is it printable (> '!')?", inline=True)
comment(0x8CFB, "No: end of filename", inline=True)
comment(0x8CFD, "Is it '\"'?", inline=True)
comment(0x8CFF, "Yes: end of filename", inline=True)
comment(0x8D01, "Next character", inline=True)
comment(0x8D02, "Loop scanning filename", inline=True)
comment(0x8D04, "A=&11: return code for file found", inline=True)
comment(0x8D06, "Return", inline=True)
comment(0x8D07, "Y=3: check if it's a directory", inline=True)
comment(0x8D09, "Get access byte", inline=True)
comment(0x8D0B, "Bit 7 clear: not dir, create file", inline=True)
comment(0x8D0D, "Directory: Already exists error", inline=True)
comment(0x8D10, "Y=2: check file access", inline=True)
comment(0x8D12, "Get access byte 2 (L attribute)", inline=True)

# sub_c8bb3 - find file, skipping directories
comment(0x8BB3, "Search for file in directory", inline=True)
comment(0x8BB6, "Found? Check if it's a directory", inline=True)
comment(0x8BB8, "Not found: return Z clear", inline=True)
comment(0x8BBA, "Skip directory entries", inline=True)
comment(0x8BBD, "Not found after dirs: return Z clear", inline=True)
comment(0x8BBF, "Y=3: check access byte", inline=True)
comment(0x8BC1, "Get access byte from entry", inline=True)
comment(0x8BC3, "Bit 7: is a directory, skip it", inline=True)
comment(0x8BC5, "A=0: return Z set (found)", inline=True)

# c8bc8 - check for ^ or @ then Not found error
comment(0x8BC8, "Y=0: get first path char", inline=True)
comment(0x8BCA, "Get first character", inline=True)
comment(0x8BCC, "Is it '^' (parent)?", inline=True)
comment(0x8BCE, "No, check '@'", inline=True)
comment(0x8BD3, "Is it '@' (current dir)?", inline=True)
comment(0x8BD5, "Yes: Bad name error", inline=True)

# sub_c8be5 - find file, check not E attribute
comment(0x8BE5, "Search for file", inline=True)
comment(0x8BE8, "Not found: return", inline=True)
comment(0x8BEA, "Y=4: check E attribute byte", inline=True)
comment(0x8BEC, "Get access/E byte", inline=True)
comment(0x8BEE, "Bit 7 clear: not E, return found", inline=True)

# sub_c8c10 - set up disc op from control block
comment(0x8C10, "Y=6: check control block byte 6", inline=True)
comment(0x8C12, "Get byte 6", inline=True)
comment(0x8C14, "Non-zero: use entry's load address", inline=True)
comment(0x8C16, "Y=5: copy bytes 2-5 from block", inline=True)
comment(0x8C17, "Get control block byte", inline=True)
comment(0x8C19, "Store in disc op workspace", inline=True)
comment(0x8C1C, "Next byte", inline=True)
comment(0x8C1D, "Past byte 1?", inline=True)
comment(0x8C1F, "No, continue copying", inline=True)
comment(0x8C21, "Done: skip to sector setup", inline=True)
comment(0x8C23, "X=4: copy 4 bytes from dir entry", inline=True)
comment(0x8C25, "Y=&0D: entry offset for load addr", inline=True)
comment(0x8C27, "Get byte from directory entry", inline=True)
comment(0x8C29, "Store in disc op workspace", inline=True)
comment(0x8C2C, "Next entry byte", inline=True)
comment(0x8C2D, "Next workspace byte", inline=True)
comment(0x8C2E, "Loop for 4 bytes", inline=True)
comment(0x8C30, "Disc op result = 1", inline=True)
comment(0x8C32, "Store result", inline=True)
comment(0x8C35, "SCSI read command = 8", inline=True)
comment(0x8C37, "Store command byte", inline=True)
comment(0x8C3A, "Clear control byte", inline=True)
comment(0x8C3C, "Store control", inline=True)
comment(0x8C3F, "Y=&16: entry offset for start sector", inline=True)
comment(0x8C41, "X=3: copy 3+1 sector bytes", inline=True)
comment(0x8C43, "Get sector byte from entry", inline=True)
comment(0x8C45, "Store in disc op command block", inline=True)
comment(0x8C48, "Next entry byte", inline=True)
comment(0x8C49, "Next command byte", inline=True)
comment(0x8C4A, "Loop for 3 bytes", inline=True)
comment(0x8C4C, "Y=&15: entry offset for length", inline=True)
comment(0x8C4E, "X=4: copy length bytes", inline=True)
comment(0x8C50, "Get length byte from entry", inline=True)
comment(0x8C52, "Store in control field", inline=True)
comment(0x8C55, "Next byte", inline=True)
comment(0x8C56, "Next control byte", inline=True)
comment(0x8C57, "Loop for 4 bytes", inline=True)
comment(0x8C59, "Calculate sector count from length", inline=True)
comment(0x8C5C, "Validate checksum and flags", inline=True)
comment(0x8C5F, "Save workspace and return", inline=True)

# service_handler_3 (&9B41) - complete boot sequence body
comment(0x9B42, "Push Y on stack", inline=True)
comment(0x9B5A, "Shift+Break: boot from floppy", inline=True)
comment(0x9B5E, "A+Break: boot from hard drive", inline=True)
comment(0x9B60, "Ctrl+Break?", inline=True)
comment(0x9B62, "Yes, handle Ctrl+Break boot", inline=True)
comment(0x9B64, "Unrecognised key: pass on service", inline=True)
comment(0x9B65, "Restore Y", inline=True)
comment(0x9B66, "Get our ROM number", inline=True)
comment(0x9B68, "A=3: service not claimed", inline=True)
comment(0x9B6A, "Return", inline=True)
comment(0x9B6B, "Ctrl+Break: discard saved Y", inline=True)
comment(0x9B6C, "Push key code instead", inline=True)
comment(0x9B6D, "Push key code on stack", inline=True)
comment(0x9B6E, "Enable interrupts for OSBYTE", inline=True)
comment(0x9B6F, "Transfer key code to A", inline=True)
comment(0x9B70, "Push key code for later", inline=True)
comment(0x9B73, "OSBYTE &78: clear keys pressed", inline=True)
comment(0x9B8C, "OSBYTE &8F: issue service 10", inline=True)
comment(0x9B8E, "X=&0A: service 10 (claim workspace)", inline=True)
comment(0x9B90, "Y=&FF", inline=True)
comment(0x9B95, "Default retry count = &10", inline=True)
comment(0x9B97, "Store in workspace base", inline=True)
comment(0x9B9A, "Y=&0D: copy 14 bytes of vectors", inline=True)
comment(0x9B9C, "Get vector table byte from ROM", inline=True)
comment(0x9B9F, "Store in MOS vector table", inline=True)
comment(0x9BA2, "Next byte", inline=True)
comment(0x9BA3, "Loop for 14 bytes", inline=True)
comment(0x9BA5, "OSBYTE &A8: read ROM pointer table", inline=True)
comment(0x9BA7, "Read current value", inline=True)
comment(0x9BAA, "Store extended vector base low", inline=True)
comment(0x9BAC, "Store extended vector base high", inline=True)
comment(0x9BAE, "Y=&2F: offset into ext vector table", inline=True)
comment(0x9BB0, "X=&14: 21 bytes of ext vectors", inline=True)
comment(0x9BB2, "Get ext vector byte from ROM", inline=True)
comment(0x9BB5, "Is it &FF (use our ROM number)?", inline=True)
comment(0x9BB7, "No, use value as-is", inline=True)
comment(0x9BB9, "Replace &FF with our ROM number", inline=True)
comment(0x9BBB, "Store in extended vector table", inline=True)
comment(0x9BBD, "Next vector byte", inline=True)
comment(0x9BBE, "Next ROM table byte", inline=True)
comment(0x9BBF, "Loop for 21 bytes", inline=True)
comment(0x9BC1, "OSBYTE &8F: issue service 15", inline=True)
comment(0x9BC3, "X=&0F: service 15 (vectors claimed)", inline=True)
comment(0x9BC5, "Y=&FF", inline=True)
comment(0x9BCA, "Initialise floppy state", inline=True)
comment(0x9BD0, "X=0: clear workspace entries", inline=True)
comment(0x9BD2, "Clear workspace byte &08", inline=True)
comment(0x9BD5, "Clear workspace byte &0C", inline=True)
comment(0x9BD8, "Clear OSWORD block", inline=True)
comment(0x9BDB, "Clear workspace byte &14", inline=True)
comment(0x9BDF, "Set workspace byte &04 to 1", inline=True)
comment(0x9BE2, "Y=&FB: copy 252 bytes from saved ws", inline=True)
comment(0x9BE4, "Get byte from saved workspace", inline=True)
comment(0x9BE6, "Copy to CSD name area", inline=True)
comment(0x9BE9, "Next byte", inline=True)
comment(0x9BEA, "Loop until Y=0", inline=True)
comment(0x9BEC, "Copy byte at Y=0 too", inline=True)
comment(0x9BEE, "Store in CSD name byte 0", inline=True)
comment(0x9BF1, "Get saved flags from workspace", inline=True)
comment(0x9BF4, "Keep only *OPT1 bit", inline=True)
comment(0x9BF6, "Set as current ADFS flags", inline=True)
comment(0x9BF8, "Store channel checksum", inline=True)
comment(0x9BFE, "HD not found: skip HD flag", inline=True)
comment(0x9C00, "Get current flags", inline=True)
comment(0x9C02, "Set bit 5: hard drive present", inline=True)
comment(0x9C04, "Store updated flags", inline=True)
comment(0x9C06, "Y=-1 (will be &FF after DEY)", inline=True)
comment(0x9C07, "Transfer to A", inline=True)
comment(0x9C08, "Store &FF in workspace (marking done)", inline=True)
comment(0x9C0A, "Retrieve key code from stack", inline=True)
comment(0x9C0B, "Was it Ctrl+Break (key C = &43)?", inline=True)
comment(0x9C0D, "No, do normal boot sequence", inline=True)
comment(0x9C12, "Y=3: copy CSD sector to workspace", inline=True)
comment(0x9C14, "Get CSD sector byte", inline=True)
comment(0x9C17, "Copy to CSD drive sector", inline=True)
comment(0x9C1A, "Next byte", inline=True)
comment(0x9C1B, "Loop for 4 bytes", inline=True)
comment(0x9C1D, "Save workspace state", inline=True)
comment(0x9C20, "Check current drive is valid", inline=True)
comment(0x9C23, "Drive = &FF (uninitialised)?", inline=True)
comment(0x9C24, "Yes, skip to Tube detection", inline=True)
comment(0x9C26, "Ensure files are closed", inline=True)
comment(0x9C29, "Check if library is at default", inline=True)
comment(0x9C2C, "Sector = 2 (root)?", inline=True)
comment(0x9C2E, "No, library is already set", inline=True)
comment(0x9C30, "Check other sector bytes", inline=True)
comment(0x9C33, "OR with mid byte", inline=True)
comment(0x9C36, "OR with high byte", inline=True)
comment(0x9C39, "Non-zero: lib sector is set", inline=True)
comment(0x9C3B, "Set up path ':0.LIB*'", inline=True)
comment(0x9C3D, "Store path address low", inline=True)
comment(0x9C3F, "Path in this ROM page", inline=True)
comment(0x9C41, "Store path address high", inline=True)
comment(0x9C43, "Search for LIB directory", inline=True)
comment(0x9C46, "Not found: leave lib as default", inline=True)
comment(0x9C48, "Y=3: check access byte", inline=True)
comment(0x9C4A, "Get access byte", inline=True)
comment(0x9C4C, "Bit 7: is it a directory?", inline=True)
comment(0x9C4E, "Not a dir: try next match", inline=True)
comment(0x9C51, "No more matches: leave default", inline=True)
comment(0x9C55, "X=2: copy 3 sector address bytes", inline=True)
comment(0x9C57, "Y=&18: start sector in entry", inline=True)
comment(0x9C59, "Get sector byte", inline=True)
comment(0x9C5B, "Store as library sector", inline=True)
comment(0x9C5E, "Next entry byte (decreasing Y)", inline=True)
comment(0x9C5F, "Next workspace byte (decreasing X)", inline=True)
comment(0x9C60, "Loop for 3 bytes", inline=True)
comment(0x9C62, "Get current drive number", inline=True)
comment(0x9C65, "Store as library drive", inline=True)
comment(0x9C68, "Y=9: copy 10-byte directory name", inline=True)
comment(0x9C6A, "Get name byte from entry", inline=True)
comment(0x9C6C, "Strip bit 7 (access flag)", inline=True)
comment(0x9C6E, "Store as library name", inline=True)
comment(0x9C71, "Next byte", inline=True)
comment(0x9C72, "Loop for 10 bytes", inline=True)
comment(0x9C74, "Save workspace state", inline=True)
comment(0x9C77, "OSBYTE &EA: read Tube presence", inline=True)
comment(0x9C79, "Read current value", inline=True)
comment(0x9C7C, "Get current ADFS flags", inline=True)
comment(0x9C7E, "Clear bit 7 (Tube flag)", inline=True)
comment(0x9C80, "X+1: was X &FF (Tube present)?", inline=True)
comment(0x9C81, "Non-zero: no Tube", inline=True)
comment(0x9C83, "Tube present: set bit 7", inline=True)
comment(0x9C85, "Store updated flags", inline=True)
comment(0x9C87, "Retrieve key/boot code from stack", inline=True)
comment(0x9C88, "Push back for later", inline=True)
comment(0x9C89, "Non-zero: skip auto-boot", inline=True)
comment(0x9C8B, "Check drive is valid", inline=True)
comment(0x9C8E, "Drive = &FF?", inline=True)
comment(0x9C8F, "No, check boot option", inline=True)
comment(0x9C91, "X=0: store as drive for mount", inline=True)
comment(0x9C94, "Mount drive 0", inline=True)
comment(0x9C97, "Get boot option from FSM", inline=True)
comment(0x9C9A, "Option 0: no auto-boot", inline=True)
comment(0x9C9C, "Get boot command addr from table", inline=True)
comment(0x9C9F, "Y=&9A: command string page", inline=True)
comment(0x9CA1, "Execute boot command via OSCLI", inline=True)
comment(0x9CA4, "Restore ROM number", inline=True)
comment(0x9CA6, "Restore Y", inline=True)
comment(0x9CA7, "Transfer to Y", inline=True)
comment(0x9CA8, "A=0: service claimed", inline=True)
comment(0x9CAA, "Return", inline=True)

# check_wksp_checksum - complete body (&A731-&A815)
# sub_ca749: validates workspace before file operations
comment(0xA749, "Save all registers", inline=True)
comment(0xA74A, "Save A", inline=True)
comment(0xA74B, "Transfer Y to A", inline=True)
comment(0xA74C, "Save Y", inline=True)
comment(0xA74D, "Transfer X to A", inline=True)
comment(0xA74E, "Save X", inline=True)
comment(0xA74F, "Check error flag", inline=True)
comment(0xA752, "Non-zero: workspace corrupt, error", inline=True)
comment(0xA754, "Validate FSM before modification", inline=True)
comment(0xA757, "Clear carry for scan", inline=True)
comment(0xA758, "X=&10: scan open channel table", inline=True)
comment(0xA75A, "Get channel state entry", inline=True)
comment(0xA75D, "Check bits 0 and 5 (dirty flags)", inline=True)
comment(0xA75F, "Both clear: channel clean", inline=True)
comment(0xA761, "Carry set + dirty: corrupt", inline=True)
comment(0xA763, "Only bit 0 set: check value", inline=True)
comment(0xA765, "Not exactly 1: corrupt", inline=True)
comment(0xA767, "Step back 4 bytes", inline=True)
comment(0xA768, "Continue stepping", inline=True)
comment(0xA769, "Continue stepping", inline=True)
comment(0xA76A, "Continue stepping", inline=True)
comment(0xA76B, "Loop for all entries", inline=True)
comment(0xA76D, "No dirty entries + C=0: corrupt", inline=True)
comment(0xA76F, "Calculate channel checksum", inline=True)
comment(0xA772, "Compare with stored checksum", inline=True)
comment(0xA775, "Mismatch: corrupt", inline=True)
comment(0xA777, "Push 2 dummy bytes for stack frame", inline=True)
comment(0xA778, "Second push", inline=True)
comment(0xA779, "Y=5: shift 6 bytes on stack", inline=True)
comment(0xA77B, "Get current stack pointer", inline=True)
comment(0xA77C, "Get byte from stack+3", inline=True)
comment(0xA77F, "Move down to stack+1", inline=True)
comment(0xA782, "Next byte", inline=True)
comment(0xA783, "Decrement counter", inline=True)
comment(0xA784, "Loop for 6 bytes", inline=True)
comment(0xA786, "Insert return addr low = &A1", inline=True)
comment(0xA788, "Store at stack+1", inline=True)
comment(0xA78B, "Insert return addr high = &A7", inline=True)
comment(0xA78D, "Store at stack+2 (return to &A7A2)", inline=True)
comment(0xA790, "Restore X from dummy push", inline=True)
comment(0xA791, "Transfer to X", inline=True)
comment(0xA792, "Restore Y from dummy push", inline=True)
comment(0xA793, "Transfer to Y", inline=True)
comment(0xA794, "Restore A", inline=True)
comment(0xA795, "Restore flags", inline=True)
comment(0xA796, "Return (via inserted &A7A2 addr)", inline=True)

# sub_ca797: calculate channel table checksum
comment(0xA797, "X=&78: sum 120 bytes of channel data", inline=True)
comment(0xA79A, "Clear carry for summation", inline=True)
comment(0xA79B, "Add channel table byte", inline=True)
comment(0xA79E, "Next byte", inline=True)
comment(0xA79F, "Loop for 120 bytes", inline=True)
comment(0xA7A1, "Return checksum in A", inline=True)

# sub_ca7a2: store channel checksum and clear error flags
comment(0xA7A2, "Save all registers", inline=True)
comment(0xA7A3, "Save A", inline=True)
comment(0xA7A4, "Transfer Y to A", inline=True)
comment(0xA7A5, "Save Y", inline=True)
comment(0xA7A6, "Transfer X to A", inline=True)
comment(0xA7A7, "Save X", inline=True)
comment(0xA7A8, "Calculate channel checksum", inline=True)
comment(0xA7AB, "Store checksum in workspace", inline=True)
comment(0xA7AE, "A=0: clear flags", inline=True)
comment(0xA7B0, "Clear compaction-reported flag", inline=True)
comment(0xA7B3, "Clear error flag", inline=True)
comment(0xA7B6, "Clear current channel", inline=True)
comment(0xA7B9, "Restore X", inline=True)
comment(0xA7BA, "Transfer to X", inline=True)
comment(0xA7BB, "Restore Y", inline=True)
comment(0xA7BC, "Transfer to Y", inline=True)
comment(0xA7BD, "Restore A", inline=True)
comment(0xA7BE, "Restore flags", inline=True)
comment(0xA7BF, "Return", inline=True)

# sub_ca7c0: read directory from disc (source sector)
comment(0xA7C0, "Get saved filename pointer low", inline=True)
comment(0xA7C3, "Store in (&B4)", inline=True)
comment(0xA7C5, "Get saved filename pointer high", inline=True)
comment(0xA7C8, "Store in (&B5)", inline=True)
comment(0xA7CA, "Get saved dir entry high", inline=True)
comment(0xA7CD, "Store in (&B7)", inline=True)
comment(0xA7CF, "Get saved dir entry low", inline=True)
comment(0xA7D2, "Store in (&B6)", inline=True)
comment(0xA7D4, "X=&0B: copy 12-byte disc op template", inline=True)
comment(0xA7D6, "Get template byte", inline=True)
comment(0xA7D9, "Copy to workspace", inline=True)
comment(0xA7DC, "Next byte", inline=True)
comment(0xA7DD, "Loop for 12 bytes", inline=True)
comment(0xA7DF, "Y=3: copy 4-byte sector address", inline=True)
comment(0xA7E1, "Get source sector byte", inline=True)
comment(0xA7E4, "Store in CSD sector", inline=True)
comment(0xA7E7, "X=0?", inline=True)
comment(0xA7E9, "Yes, skip disc op sector store", inline=True)
comment(0xA7EB, "Store in disc op sector field", inline=True)
comment(0xA7EE, "Next X", inline=True)
comment(0xA7EF, "Next Y (decreasing)", inline=True)
comment(0xA7F0, "Loop for 4 bytes", inline=True)
comment(0xA7F2, "Execute disc read command", inline=True)

# sub_ca7f5: read directory from disc (dest sector)
comment(0xA7F5, "X=&0B: copy 12-byte disc op template", inline=True)
comment(0xA7F7, "Get template byte", inline=True)
comment(0xA7FA, "Copy to workspace", inline=True)
comment(0xA7FD, "Next byte", inline=True)
comment(0xA7FE, "Loop for 12 bytes", inline=True)
comment(0xA800, "Y=3: copy 4-byte sector address", inline=True)
comment(0xA802, "Get dest sector byte", inline=True)
comment(0xA805, "Store in CSD sector", inline=True)
comment(0xA808, "X=0?", inline=True)
comment(0xA80A, "Yes, skip disc op store", inline=True)
comment(0xA80C, "Store in disc op sector field", inline=True)
comment(0xA80F, "Next X", inline=True)
comment(0xA810, "Next Y (decreasing)", inline=True)
comment(0xA811, "Loop for 4 bytes", inline=True)
comment(0xA813, "Execute disc read command", inline=True)

# print_inline_string - complete body (&92A0-&941C)
comment(0x92A0, "Pop return addr low (inline data)", inline=True)
comment(0x92A1, "Store as string pointer low", inline=True)
comment(0x92A3, "Pop return addr high", inline=True)
comment(0x92A4, "Store as string pointer high", inline=True)
comment(0x92A6, "Y=1: start past JSR return addr", inline=True)
comment(0x92A8, "Get next string character", inline=True)
comment(0x92AA, "Bit 7 set: last character", inline=True)
comment(0x92AC, "Print character via OSASCI", inline=True)
comment(0x92AF, "Next character", inline=True)
comment(0x92B0, "Loop for more characters", inline=True)
comment(0x92B2, "Strip bit 7 from last char", inline=True)
comment(0x92B4, "Print last character", inline=True)
comment(0x92B7, "Y = string length + 1", inline=True)
comment(0x92B8, "Clear carry for address calc", inline=True)
comment(0x92B9, "Add string length to pointer", inline=True)
comment(0x92BB, "Transfer low result to Y", inline=True)
comment(0x92BC, "A=0: add carry only", inline=True)
comment(0x92BE, "Add carry to high byte", inline=True)
comment(0x92C0, "Push updated return addr high", inline=True)
comment(0x92C1, "Transfer low to A", inline=True)
comment(0x92C2, "Push updated return addr low", inline=True)
comment(0x92C3, "Return (past inline string)", inline=True)

# sub_c92c4: print character preserving pointers
comment(0x92C4, "Save character to print", inline=True)
comment(0x92C5, "Save X", inline=True)
comment(0x92C6, "Save X on stack", inline=True)
comment(0x92C7, "Save (&B6) low", inline=True)
comment(0x92C9, "Push on stack", inline=True)
comment(0x92CA, "Save (&B6) high", inline=True)
comment(0x92CC, "Push on stack", inline=True)
comment(0x92CD, "Get stack pointer", inline=True)
comment(0x92CE, "Get character from stack+4", inline=True)
comment(0x92D4, "Restore (&B6) high", inline=True)
comment(0x92D5, "Store back", inline=True)
comment(0x92D7, "Restore (&B6) low", inline=True)
comment(0x92D8, "Store back", inline=True)
comment(0x92DA, "Restore X", inline=True)
comment(0x92DB, "Transfer to X", inline=True)
comment(0x92DC, "Restore character (was printed)", inline=True)
comment(0x92DD, "Return", inline=True)

# sub_c92de: print entry name with access string
comment(0x92DE, "X=&0A: print up to 10 name chars", inline=True)
comment(0x92E0, "Print name characters", inline=True)
comment(0x92E3, "Print space after name", inline=True)
comment(0x92E6, "Y=4: scan bytes 4,3,2,1,0 (EDLWR)", inline=True)
comment(0x92E8, "X=3: space-pad counter for columns", inline=True)
comment(0x92EA, "Get name byte Y from entry", inline=True)
comment(0x92EC, "Bit 7 (attribute flag) into carry", inline=True)
comment(0x92ED, "C=0: attribute not set, skip", inline=True)
comment(0x92EF, "C=1: get letter from 'RWLDE'[Y]", inline=True)
comment(0x92F5, "X-- (tracks set attribute count)", inline=True)
comment(0x92F6, "Y-- (next entry byte, towards 0)", inline=True)
comment(0x92F7, "Loop for 5 bytes (E,D,L,W,R)", inline=True)
comment(0x92F9, "X--: pad remaining columns", inline=True)
comment(0x92FA, "All columns done", inline=True)
comment(0x92FC, "Print space for unset attribute", inline=True)
comment(0x92FF, "Continue padding loop", inline=True)
comment(0x9302, "Print '(' before sequence number", inline=True)
comment(0x9307, "Y=&19: offset to sequence number", inline=True)
comment(0x9309, "Get sequence number byte", inline=True)
comment(0x930B, "Print as 2 hex digits", inline=True)
comment(0x930E, "Print ')' after sequence number", inline=True)
comment(0x9313, "Print space and return", inline=True)

# sub_c931b: print A as two hex digits
comment(0x931B, "Save value", inline=True)
comment(0x931C, "Shift high nibble to low", inline=True)
comment(0x931D, "Second shift", inline=True)
comment(0x931E, "Third shift", inline=True)
comment(0x931F, "Fourth shift", inline=True)
comment(0x9320, "Print high nibble as hex char", inline=True)
comment(0x9323, "Restore value for low nibble", inline=True)

# sub_c932a-c93cd: catalogue display routines
comment(0x932D, "Point to dir title at &16D9", inline=True)
comment(0x932F, "Store low byte", inline=True)
comment(0x9331, "Page &16", inline=True)
comment(0x9333, "Store high byte", inline=True)
comment(0x9335, "X=&13: print 19 chars of title", inline=True)
comment(0x9337, "Print title characters", inline=True)
comment(0x933E, "Transfer Y to A for display", inline=True)
comment(0x933F, "Get directory sequence number", inline=True)
comment(0x9342, "Print as 2 hex digits", inline=True)
comment(0x934F, "Get stack pointer", inline=True)
comment(0x9350, "Get current drive number", inline=True)
comment(0x9353, "Shift drive bits into position", inline=True)
comment(0x9354, "Second shift", inline=True)
comment(0x9355, "Third shift", inline=True)
comment(0x9356, "Fourth shift", inline=True)
comment(0x9357, "Convert to ASCII digit", inline=True)
comment(0x935C, "Point to CSD path string in ROM", inline=True)
comment(0x935E, "Store pointer low", inline=True)
comment(0x9360, "Page &9A", inline=True)
comment(0x9362, "Store pointer high", inline=True)
comment(0x9364, "X=&0D: print CSD path", inline=True)
comment(0x9366, "Print path characters", inline=True)
comment(0x9372, "' ' + bit 7: end of inline string", inline=True)
comment(0x9373, "Get boot option from FSM", inline=True)
comment(0x9376, "Print boot option as two hex digits", inline=True)
comment(0x937D, "Transfer boot option to Y for lookup", inline=True)
comment(0x937E, "Get boot option again for table index", inline=True)
comment(0x9381, "Look up option name string address", inline=True)
comment(0x9384, "Set entry ptr to option name string", inline=True)
comment(0x938A, "X=4: print 4-char option name", inline=True)
comment(0x938C, "Print boot option name (Off/Load/Run/Exec)", inline=True)
comment(0x9398, "' ' + bit 7: end of inline string", inline=True)
comment(0x9399, "A=&00: CSD name low (wksp_csd_name)", inline=True)
comment(0x939B, "Store pointer low byte", inline=True)
comment(0x939D, "A=&11: CSD name high (&1100)", inline=True)
comment(0x939F, "Store pointer high byte", inline=True)
comment(0x93A1, "X=&0A: print 10-char directory name", inline=True)
comment(0x93A3, "Print CSD directory name", inline=True)
comment(0x93B2, "' ' + bit 7: end of inline string", inline=True)
comment(0x93C3, "CR: end of library name line", inline=True)
comment(0x93C4, "CR + bit 7: blank line after header", inline=True)
comment(0x93B3, "A=&0A: library name low (wksp_lib_name)", inline=True)
comment(0x93B5, "Store pointer low byte", inline=True)
comment(0x93B7, "A=&11: library name high (&110A)", inline=True)
comment(0x93B9, "Store pointer high byte", inline=True)
comment(0x93BB, "X=&0A: print 10-char library name", inline=True)
comment(0x93BD, "Print library directory name", inline=True)
comment(0x93C5, "Point to first dir entry at &1205", inline=True)
comment(0x93C7, "Store pointer low = &05", inline=True)
comment(0x93C9, "Page &12", inline=True)
comment(0x93CB, "Store pointer high", inline=True)
comment(0x93CD, "Return", inline=True)

# sub_c93d4: *CAT command body
comment(0x93D4, "Load and validate directory", inline=True)
comment(0x93D7, "Columns per line = 4", inline=True)
comment(0x93D9, "Store column counter", inline=True)
comment(0x93DC, "Y=0: check first byte of entry", inline=True)
comment(0x93DE, "Get first byte", inline=True)
comment(0x93E0, "Zero: end of entries", inline=True)
comment(0x93E2, "Print entry name with access", inline=True)
comment(0x93E5, "Decrement column counter", inline=True)
comment(0x93E8, "Not zero: same line", inline=True)
comment(0x93EA, "Reset column counter to 4", inline=True)
comment(0x93EC, "Store column counter", inline=True)
comment(0x93F2, "Jump to newline print", inline=True)
comment(0x93F5, "Print space between entries", inline=True)
comment(0x93F8, "Clear carry for pointer advance", inline=True)
comment(0x93F9, "Get entry pointer low", inline=True)
comment(0x93FB, "Add &1A (26 bytes per entry)", inline=True)
comment(0x93FD, "Store updated pointer", inline=True)
comment(0x93FF, "No page crossing: continue", inline=True)
comment(0x9401, "Increment page", inline=True)
comment(0x9405, "Get column counter", inline=True)
comment(0x9408, "Full line (4 columns)?", inline=True)
comment(0x940A, "Yes: no partial line to finish", inline=True)
comment(0x940C, "OSBYTE &86: read cursor position", inline=True)
comment(0x9412, "X non-zero: cursor not at col 0", inline=True)
comment(0x9414, "At col 0: VDU 11 (cursor up)", inline=True)
comment(0x941C, "Save workspace and return", inline=True)

# star_copy (&A81D) - complete body coverage
comment(0xA81F, "Store control block pointer low", inline=True)
comment(0xA821, "Control block page = &10", inline=True)
comment(0xA823, "Store control block pointer high", inline=True)
comment(0xA827, "Store source name offset", inline=True)
comment(0xA82A, "Source name page = &10", inline=True)
comment(0xA82C, "Store source name page", inline=True)
comment(0xA839, "Save dir entry pointer low", inline=True)
comment(0xA83C, "Get dir entry pointer high", inline=True)
comment(0xA83E, "Save dir entry pointer high", inline=True)
comment(0xA843, "Save filename pointer low", inline=True)
comment(0xA846, "Get filename pointer high", inline=True)
comment(0xA848, "Save filename pointer high", inline=True)
comment(0xA850, "Save CSD sector byte", inline=True)
comment(0xA853, "Next byte", inline=True)
comment(0xA854, "Loop for 4 bytes", inline=True)
comment(0xA859, "Y=3: copy current dir sector", inline=True)
comment(0xA85B, "Get CSD sector byte", inline=True)
comment(0xA85E, "Set as target dir for copy", inline=True)
comment(0xA861, "Next byte", inline=True)
comment(0xA862, "Loop for 4 bytes", inline=True)
comment(0xA864, "Parse destination path", inline=True)
comment(0xA86A, "Found destination dir?", inline=True)
comment(0xA86C, "Bad name: invalid destination", inline=True)
comment(0xA86F, "Load destination directory", inline=True)
comment(0xA872, "Validate FSM before dest dir change", inline=True)
comment(0xA875, "Y=3: save dest dir sector", inline=True)
comment(0xA877, "Get dest dir sector byte", inline=True)
comment(0xA87A, "Store in workspace", inline=True)
comment(0xA87D, "Next byte", inline=True)
comment(0xA87E, "Loop for 4 bytes", inline=True)
comment(0xA880, "Set up disc read for source", inline=True)
comment(0xA883, "Y=4: check entry access byte", inline=True)
comment(0xA885, "Get access byte from entry", inline=True)
comment(0xA888, "OR with first name byte", inline=True)
comment(0xA88A, "Bit 7 clear: regular file, copy it", inline=True)
comment(0xA88C, "Directory: find next entry", inline=True)
comment(0xA88F, "More entries: loop", inline=True)
comment(0xA891, "No more entries: done", inline=True)
comment(0xA894, "Save source entry pointer", inline=True)
comment(0xA896, "Store entry pointer low", inline=True)
comment(0xA899, "Get entry pointer high", inline=True)
comment(0xA89B, "Store entry pointer high", inline=True)
comment(0xA89E, "Check if file already exists at dest", inline=True)
comment(0xA8A1, "Y=&16: get source start sector", inline=True)
comment(0xA8A3, "Get sector low byte", inline=True)
comment(0xA8A5, "Store in load address workspace", inline=True)
comment(0xA8A9, "Get sector mid byte", inline=True)
comment(0xA8AB, "Store in load address workspace", inline=True)
comment(0xA8AF, "Get sector high byte", inline=True)
comment(0xA8B1, "OR with drive number", inline=True)
comment(0xA8B4, "Store in load address workspace", inline=True)
comment(0xA8B7, "X=0: clear length bytes", inline=True)
comment(0xA8B9, "Y=3: copy 4-byte OSFILE params", inline=True)
comment(0xA8BB, "Get source OSFILE param", inline=True)
comment(0xA8BE, "Copy to dest OSFILE block", inline=True)
comment(0xA8C1, "Transfer X (=0) for clearing", inline=True)
comment(0xA8C2, "Clear source param", inline=True)
comment(0xA8C5, "Next byte", inline=True)
comment(0xA8C6, "Loop for 4 bytes", inline=True)
comment(0xA8C8, "Y=9: copy 10-byte filename", inline=True)
comment(0xA8CA, "Get filename byte from source", inline=True)
comment(0xA8CC, "Strip bit 7 (access flag)", inline=True)
comment(0xA8CE, "Store in dest name workspace", inline=True)
comment(0xA8D1, "Next byte", inline=True)
comment(0xA8D2, "Loop for 10 bytes", inline=True)
comment(0xA8D4, "A=CR: terminate filename", inline=True)
comment(0xA8D6, "Store terminator", inline=True)
comment(0xA8D9, "Set up disc read for source file", inline=True)
comment(0xA8DC, "Check if file is open", inline=True)
comment(0xA8DF, "Allocate space for dest file", inline=True)
comment(0xA8E2, "Write dest directory entry", inline=True)
comment(0xA8E5, "Y=2: copy sector addresses", inline=True)
comment(0xA8E7, "Get source sector byte", inline=True)
comment(0xA8EA, "Store as read sector", inline=True)
comment(0xA8ED, "Get dest sector byte", inline=True)
comment(0xA8F0, "Store as write sector", inline=True)
comment(0xA8F3, "Next byte", inline=True)
comment(0xA8F4, "Loop for 3 bytes", inline=True)
comment(0xA8F6, "OSBYTE &83: read OSHWM", inline=True)
comment(0xA8FE, "OSBYTE &84: read HIMEM", inline=True)
comment(0xA904, "Calculate buffer size: HIMEM-OSHWM", inline=True)
comment(0xA905, "Subtract OSHWM page", inline=True)
comment(0xA908, "Store buffer size in pages", inline=True)
comment(0xA90B, "Set bit 3 of ADFS flags", inline=True)
comment(0xA90D, "Indicate copy operation in progress", inline=True)
comment(0xA90F, "Store updated flags", inline=True)
comment(0xA911, "Get source drive number", inline=True)
comment(0xA914, "OR into read sector high byte", inline=True)
comment(0xA917, "Store source drive+sector", inline=True)
comment(0xA91A, "Get dest drive number", inline=True)
comment(0xA91D, "OR into write sector high byte", inline=True)
comment(0xA920, "Store dest drive+sector", inline=True)
comment(0xA923, "Save current drive", inline=True)
comment(0xA926, "Push on stack", inline=True)
comment(0xA927, "Set drive to 0 temporarily", inline=True)
comment(0xA929, "Store temporary drive", inline=True)
comment(0xA92C, "Execute sector-by-sector copy", inline=True)
comment(0xA92F, "Restore original drive", inline=True)
comment(0xA930, "Set as current drive", inline=True)
comment(0xA933, "Write modified directory", inline=True)
comment(0xA936, "Set up for next source file", inline=True)
comment(0xA939, "Loop to copy next file", inline=True)

# osbput_handler (&B08F) - complete body coverage
comment(0xB097, "Clear modification flag", inline=True)
comment(0xB0BC, "Buffer state >= 6: ready", inline=True)
comment(0xB0C0, "Buffer state = 3: skip load", inline=True)
comment(0xB0C5, "Set carry for PTR+1 calculation", inline=True)
comment(0xB0C6, "Add 1 (carry) to PTR low", inline=True)
comment(0xB0C8, "Store next PTR low in workspace", inline=True)
comment(0xB0CB, "Get PTR mid-low", inline=True)
comment(0xB0CE, "Add carry", inline=True)
comment(0xB0D0, "Store next PTR mid-low", inline=True)
comment(0xB0D3, "Get PTR mid-high", inline=True)
comment(0xB0D6, "Add carry", inline=True)
comment(0xB0D8, "Store next PTR mid-high", inline=True)
comment(0xB0DB, "Get PTR high", inline=True)
comment(0xB0DE, "Add carry", inline=True)
comment(0xB0E0, "Store next PTR high", inline=True)
comment(0xB0E3, "Restore byte to write", inline=True)
comment(0xB0E4, "Save registers for restore", inline=True)
comment(0xB0E7, "Re-push byte to write", inline=True)
comment(0xB0E8, "Set modification flag", inline=True)
comment(0xB0EB, "Validate PTR and load sector", inline=True)
comment(0xB0EE, "Get channel index", inline=True)
comment(0xB0F0, "Clear carry for address calc", inline=True)
comment(0xB0F1, "Get channel start sector low", inline=True)
comment(0xB0F4, "Add PTR to get current disc sector", inline=True)
comment(0xB0F7, "Store disc sector address low", inline=True)
comment(0xB0FA, "Get channel start sector mid", inline=True)
comment(0xB0FD, "Add PTR mid-high with carry", inline=True)
comment(0xB100, "Store disc sector address mid", inline=True)
comment(0xB103, "Get channel start sector+drive", inline=True)
comment(0xB106, "Add PTR high with carry", inline=True)
comment(0xB109, "Store disc sector address high", inline=True)
comment(0xB10C, "A=&C0: buffer write mode", inline=True)
comment(0xB10E, "Load sector into buffer", inline=True)
comment(0xB111, "Get channel index", inline=True)
comment(0xB113, "Get PTR low as buffer offset", inline=True)
comment(0xB116, "Restore byte to write", inline=True)
comment(0xB117, "Write byte into buffer at PTR", inline=True)
comment(0xB119, "Save byte again", inline=True)
comment(0xB11A, "Advance PTR and update flags", inline=True)
comment(0xB11D, "Restore written byte", inline=True)
comment(0xB11E, "Restore Y", inline=True)
comment(0xB120, "Restore X", inline=True)
comment(0xB122, "Return", inline=True)
comment(0xB123, "Get channel index", inline=True)
comment(0xB125, "Increment PTR low byte", inline=True)
comment(0xB128, "No wrap: done", inline=True)
comment(0xB12A, "Check modification flag", inline=True)
comment(0xB12D, "Not modified: skip workspace save", inline=True)
comment(0xB12F, "Save workspace state", inline=True)
comment(0xB132, "Increment PTR mid-low", inline=True)
comment(0xB135, "No wrap: update flags", inline=True)
comment(0xB137, "Increment PTR mid-high", inline=True)
comment(0xB13A, "No wrap: update flags", inline=True)
comment(0xB13C, "Increment PTR high", inline=True)
comment(0xB13F, "Update channel flags for new PTR", inline=True)
comment(0xB142, "Save current flags on stack", inline=True)
comment(0xB143, "Set carry for subtraction", inline=True)
comment(0xB144, "Compare PTR with EXT: mid-low", inline=True)
comment(0xB147, "Subtract EXT mid-low", inline=True)
comment(0xB14A, "PTR mid-high", inline=True)
comment(0xB14D, "Subtract EXT mid-high", inline=True)
comment(0xB150, "PTR high", inline=True)
comment(0xB153, "Subtract EXT high", inline=True)
comment(0xB156, "PTR < EXT: not at EOF", inline=True)
comment(0xB158, "PTR >= EXT: compare low bytes", inline=True)
comment(0xB15B, "Compare PTR low with EXT low", inline=True)
comment(0xB15E, "Not equal: PTR past EXT", inline=True)
comment(0xB160, "Equal: set EOF flag (bit 2)", inline=True)
comment(0xB161, "Set bit 2 in flags", inline=True)
comment(0xB163, "Re-push updated flags", inline=True)
comment(0xB164, "Check if buffer needs flushing", inline=True)
comment(0xB165, "Compare EXT mid-low with allocation", inline=True)
comment(0xB168, "Subtract allocation mid-low", inline=True)
comment(0xB16B, "EXT mid-high", inline=True)
comment(0xB16E, "Subtract allocation mid-high", inline=True)
comment(0xB171, "EXT high", inline=True)
comment(0xB174, "Subtract allocation high", inline=True)
comment(0xB177, "EXT < allocation: buffer has room", inline=True)
comment(0xB179, "Restore flags", inline=True)
comment(0xB17A, "Non-zero flags: keep them", inline=True)
comment(0xB17C, "Restore flags", inline=True)
comment(0xB17D, "Set bit 1 (buffer needs flushing)", inline=True)
comment(0xB181, "Restore flags", inline=True)
comment(0xB182, "Set bits 0+1 (dirty + flush)", inline=True)
comment(0xB184, "Bit 7 set: writable channel", inline=True)
comment(0xB186, "Clear bits 0-2 (read-only mode)", inline=True)
comment(0xB188, "Store updated channel flags", inline=True)
comment(0xB18B, "Return", inline=True)
comment(0xB18C, "Get channel index", inline=True)
comment(0xB18E, "Get current channel flags", inline=True)
comment(0xB191, "Save on stack", inline=True)
comment(0xB192, "Check EOF flag (bit 2)", inline=True)
comment(0xB194, "Not at EOF: skip EXT update", inline=True)
comment(0xB196, "At EOF: set EXT = PTR", inline=True)
comment(0xB199, "Copy PTR low to EXT low", inline=True)
comment(0xB19C, "Copy PTR mid-low to EXT mid-low", inline=True)
comment(0xB19F, "Store in EXT", inline=True)
comment(0xB1A2, "Copy PTR mid-high to EXT mid-high", inline=True)
comment(0xB1A5, "Store in EXT", inline=True)
comment(0xB1A8, "Copy PTR high to EXT high", inline=True)
comment(0xB1AB, "Store in EXT", inline=True)
comment(0xB1AE, "Restore flags from stack", inline=True)
comment(0xB1AF, "Keep only writable+open bits", inline=True)
comment(0xB1B1, "Non-zero: store flags", inline=True)

# star_compact (&A276) - complete body coverage
comment(0xA291, "Set carry for subtraction", inline=True)
comment(0xA292, "Subtract start page from HIMEM", inline=True)
comment(0xA2AB, "Store first hex digit", inline=True)
comment(0xA2AE, "Next argument character", inline=True)
comment(0xA2AF, "Get second hex digit", inline=True)
comment(0xA2B1, "Store as second digit", inline=True)
comment(0xA2B4, "Next character", inline=True)
comment(0xA2B5, "Get separator/terminator", inline=True)
comment(0xA2B7, "Is it a space?", inline=True)
comment(0xA2B9, "Yes, skip to length parameter", inline=True)
comment(0xA2BB, "Is it a comma?", inline=True)
comment(0xA2BD, "No separator: bad compact error", inline=True)
comment(0xA2BF, "Skip spaces/commas", inline=True)
comment(0xA2C0, "Get length first digit", inline=True)
comment(0xA2C2, "Is it a space?", inline=True)
comment(0xA2C4, "Yes, skip more spaces", inline=True)
comment(0xA2C6, "Store length first digit", inline=True)
comment(0xA2C9, "Next character", inline=True)
comment(0xA2CA, "Get length second digit", inline=True)
comment(0xA2CC, "Store length second digit", inline=True)
comment(0xA2CF, "Is second digit printable?", inline=True)
comment(0xA2D1, "Yes, both digits present", inline=True)
comment(0xA2D3, "Only one digit: treat as low nibble", inline=True)
comment(0xA2D6, "Move to high position", inline=True)
comment(0xA2D9, "Set low nibble to '0'", inline=True)
comment(0xA2DB, "Store '0' as low nibble", inline=True)
comment(0xA2DE, "Back up one char position", inline=True)
comment(0xA2DF, "Skip past length argument", inline=True)
comment(0xA2E0, "Get next character", inline=True)
comment(0xA2E2, "Is it a space?", inline=True)
comment(0xA2E4, "Yes, skip spaces", inline=True)
comment(0xA2E6, "Printable after length: bad compact", inline=True)
comment(0xA2E8, "X=3: convert 4 hex digits to 2 bytes", inline=True)
comment(0xA2EA, "Get hex digit", inline=True)
comment(0xA2ED, "Is it '0'-'9'?", inline=True)
comment(0xA2EF, "Below '0': bad compact", inline=True)
comment(0xA2F1, "Above '9'?", inline=True)
comment(0xA2F3, "No, it's '0'-'9': convert", inline=True)
comment(0xA2F5, "Set carry for subtraction", inline=True)
comment(0xA2F6, "Convert ASCII digit to value", inline=True)
comment(0xA2F8, "Store value", inline=True)
comment(0xA2FB, "Always branch (non-negative)", inline=True)
comment(0xA2FD, "Convert to uppercase", inline=True)
comment(0xA2FF, "Below 'A'?", inline=True)
comment(0xA301, "Yes: bad compact", inline=True)
comment(0xA303, "Above 'F'?", inline=True)
comment(0xA305, "Yes: bad compact", inline=True)
comment(0xA307, "Convert 'A'-'F' to 10-15", inline=True)
comment(0xA309, "Store value", inline=True)
comment(0xA30C, "Next digit", inline=True)
comment(0xA30D, "Loop for 4 digits", inline=True)
comment(0xA30F, "X=0: combine first pair", inline=True)
comment(0xA310, "Combine two hex digits into byte", inline=True)
comment(0xA313, "Negative result: bad compact", inline=True)
comment(0xA315, "Store as start page", inline=True)
comment(0xA318, "X=2: combine second pair", inline=True)
comment(0xA31A, "Combine two hex digits into byte", inline=True)
comment(0xA31D, "Positive result: valid", inline=True)
comment(0xA31F, "Zero length: bad compact", inline=True)
comment(0xA322, "Also zero: bad compact", inline=True)
comment(0xA324, "Store as buffer length in pages", inline=True)
comment(0xA327, "Get our ROM number", inline=True)
comment(0xA329, "Get workspace page from ROM table", inline=True)
comment(0xA32C, "Start page below workspace?", inline=True)
comment(0xA32F, "Yes: buffer doesn't overlap", inline=True)
comment(0xA331, "No: bad compact (overlaps workspace)", inline=True)
comment(0xA334, "Clear carry for addition", inline=True)
comment(0xA335, "Start page + length", inline=True)
comment(0xA338, "Add buffer length", inline=True)
comment(0xA33B, "Result > &7F: check for exactly &80", inline=True)
comment(0xA33D, "Is it exactly &80?", inline=True)
comment(0xA33F, "Yes: OK (up to screen memory)", inline=True)
comment(0xA341, "Above &80: bad compact", inline=True)
comment(0xA34A, "Set bit 3 of ADFS flags", inline=True)
comment(0xA34C, "Indicate compaction in progress", inline=True)
comment(0xA34E, "Store updated flags", inline=True)
comment(0xA350, "Execute compaction algorithm", inline=True)
comment(0xA353, "Clear bit 3 when done", inline=True)
comment(0xA355, "Mask off bit 3", inline=True)
comment(0xA357, "Store cleared flags", inline=True)
comment(0xA359, "Return", inline=True)
comment(0xA35A, "Get hex digit pair high nibble", inline=True)
comment(0xA35D, "Shift left 4 positions", inline=True)
comment(0xA35E, "Second shift", inline=True)
comment(0xA35F, "Third shift", inline=True)
comment(0xA360, "Fourth shift", inline=True)
comment(0xA361, "OR in low nibble", inline=True)
comment(0xA364, "Return combined byte", inline=True)
comment(0xA368, "Save text pointer high", inline=True)
comment(0xA36A, "Push on stack", inline=True)
comment(0xA36B, "Save text pointer low", inline=True)
comment(0xA36D, "Push on stack", inline=True)
comment(0xA371, "Y=0: check for argument", inline=True)
comment(0xA373, "Get first char", inline=True)
comment(0xA375, "Is it printable?", inline=True)
comment(0xA377, "No: end of command", inline=True)
comment(0xA379, "Restore text pointer low", inline=True)
comment(0xA37A, "Store in (&B4)", inline=True)
comment(0xA37C, "Also in OSFILE block", inline=True)
comment(0xA37F, "Restore text pointer high", inline=True)
comment(0xA380, "Store in (&B5)", inline=True)
comment(0xA382, "Also in OSFILE block+1", inline=True)
comment(0xA385, "Return", inline=True)

# osargs_handler - remaining items (complete body coverage)
comment(0xA95E, "Return (FS number in A)", inline=True)
comment(0xA97B, "Return (success)", inline=True)
comment(0xA97C, "X=&10: scan open channels", inline=True)
comment(0xA97E, "Flush channel buffer if dirty", inline=True)
comment(0xA983, "Clear channel dirty flag", inline=True)
comment(0xA987, "Step back 4 bytes (next channel)", inline=True)
comment(0xA988, "Continue stepping", inline=True)
comment(0xA989, "Continue stepping", inline=True)
comment(0xA98C, "Increment flush counter", inline=True)
comment(0xA992, "Return success", inline=True)
comment(0xA995, "Save regs for file-specific OSARGS", inline=True)
comment(0xA998, "Save X (ZP pointer)", inline=True)
comment(0xA99A, "Save function code on stack", inline=True)
comment(0xA99E, "Flush channel buffer", inline=True)
comment(0xA9B1, "Store PTR mid-low at X+1", inline=True)
comment(0xA9B6, "Store PTR mid-high at X+2", inline=True)
comment(0xA9BB, "Store PTR high at X+3", inline=True)
comment(0xA9BD, "Ensure channel state is consistent", inline=True)
comment(0xA9C2, "Restore X", inline=True)
comment(0xA9C4, "Restore Y", inline=True)
comment(0xA9C6, "Return", inline=True)
comment(0xA9D3, "Store new PTR low in workspace", inline=True)
comment(0xA9D6, "Get new PTR mid-low from user ZP", inline=True)
comment(0xA9D8, "Store in workspace", inline=True)
comment(0xA9DB, "Get new PTR mid-high", inline=True)
comment(0xA9DD, "Store in workspace", inline=True)
comment(0xA9E0, "Get new PTR high", inline=True)
comment(0xA9E2, "Store in workspace", inline=True)
comment(0xA9E5, "Validate and apply new PTR", inline=True)
comment(0xA9EA, "Get channel index", inline=True)
comment(0xA9EC, "Get validated PTR low from user ZP", inline=True)
comment(0xA9F1, "Get PTR mid-low", inline=True)
comment(0xA9F6, "Get PTR mid-high", inline=True)
comment(0xA9FB, "Get PTR high", inline=True)
comment(0xAA00, "Jump to success return", inline=True)
comment(0xAA05, "Get channel index for EXT compare", inline=True)
comment(0xAA08, "Get EXT low byte", inline=True)
comment(0xAA0B, "Subtract new PTR low", inline=True)
comment(0xAA0D, "Get EXT mid-low", inline=True)
comment(0xAA10, "Subtract new PTR mid-low", inline=True)
comment(0xAA12, "Get EXT mid-high", inline=True)
comment(0xAA15, "Subtract new PTR mid-high", inline=True)
comment(0xAA17, "Get EXT high", inline=True)
comment(0xAA1A, "Subtract new PTR high", inline=True)
comment(0xAA20, "Set new PTR low byte", inline=True)
comment(0xAA23, "Get mid-low from user ZP", inline=True)
comment(0xAA25, "Set PTR mid-low", inline=True)
comment(0xAA28, "Get mid-high from user ZP", inline=True)
comment(0xAA2A, "Set PTR mid-high", inline=True)
comment(0xAA2D, "Get high from user ZP", inline=True)
comment(0xAA2F, "Set PTR high", inline=True)
comment(0xAA32, "Jump to success return", inline=True)
comment(0xAA4E, "Store EXT low at user X+0", inline=True)
comment(0xAA50, "Get EXT mid-low", inline=True)
comment(0xAA53, "Store at user X+1", inline=True)
comment(0xAA55, "Get EXT mid-high", inline=True)
comment(0xAA58, "Store at user X+2", inline=True)
comment(0xAA5A, "Get EXT high", inline=True)
comment(0xAA5D, "Store at user X+3", inline=True)
comment(0xAA5F, "Jump to success return", inline=True)
comment(0xAA6C, "Not writable: error", inline=True)
comment(0xAA71, "Store new EXT low in workspace", inline=True)
comment(0xAA74, "Get new EXT mid-low", inline=True)
comment(0xAA76, "Store in workspace", inline=True)
comment(0xAA79, "Get new EXT mid-high", inline=True)
comment(0xAA7B, "Store in workspace", inline=True)
comment(0xAA7E, "Get new EXT high", inline=True)
comment(0xAA80, "Store in workspace", inline=True)
comment(0xAA83, "Validate and apply new EXT", inline=True)
comment(0xAA86, "Restore X", inline=True)
comment(0xAA88, "Get channel index", inline=True)
comment(0xAA8A, "Get validated EXT low", inline=True)
comment(0xAA8C, "Set channel EXT low", inline=True)
comment(0xAA8F, "Get EXT mid-low", inline=True)
comment(0xAA91, "Set channel EXT mid-low", inline=True)
comment(0xAA94, "Get EXT mid-high", inline=True)
comment(0xAA96, "Set channel EXT mid-high", inline=True)
comment(0xAA99, "Get EXT high", inline=True)
comment(0xAA9B, "Set channel EXT high", inline=True)
comment(0xAAA1, "EXT >= current: just update table", inline=True)
comment(0xAAA3, "EXT < current: also update PTR", inline=True)
comment(0xAAA6, "X=&10: scan ensure table", inline=True)
comment(0xAAA8, "Get ensure table entry", inline=True)
comment(0xAAAB, "Shift right to get channel index", inline=True)
comment(0xAAAC, "Mask to 4-bit channel number", inline=True)
comment(0xAAAE, "This channel's entry?", inline=True)
comment(0xAAB0, "No, skip to next entry", inline=True)
comment(0xAAB2, "Flush this entry's buffer", inline=True)
comment(0xAAB5, "Get ensure table entry again", inline=True)
comment(0xAAB8, "Keep only bit 0 (dirty flag)", inline=True)
comment(0xAABA, "Clear other bits", inline=True)
comment(0xAABD, "Step back 4 bytes", inline=True)
comment(0xAABE, "Continue stepping", inline=True)
comment(0xAABF, "Continue stepping", inline=True)
comment(0xAAC0, "Continue stepping", inline=True)
comment(0xAAC1, "Loop for all ensure entries", inline=True)
comment(0xAAC3, "Return success", inline=True)

# floppy_check_present / exec_floppy_*_sector - remaining items
# These routines handle floppy disc BGET/BPUT sector operations.
comment(0xBA25, "Return (C=1: not present)", inline=True)
comment(0xBA34, "Save X on stack", inline=True)
comment(0xBA38, "Set up drive select and step rate", inline=True)
comment(0xBA3B, "Restore X", inline=True)
comment(0xBA3C, "Transfer to X", inline=True)
comment(0xBA43, "Patch NMI handler buffer addr low", inline=True)
comment(0xBA48, "Patch NMI handler buffer addr high", inline=True)
comment(0xBA4B, "Always branch (high byte non-zero)", inline=True)
comment(0xBA4F, "Patch NMI read buffer addr low", inline=True)
comment(0xBA52, "Get read buffer addr high", inline=True)
comment(0xBA54, "Patch NMI read buffer addr high", inline=True)
comment(0xBA5A, "Save sector count on stack", inline=True)
comment(0xBA5F, "Pop and discard", inline=True)
comment(0xBA60, "Jump to error: bad drive number", inline=True)
comment(0xBA63, "Pop sector count", inline=True)
comment(0xBA64, "Re-push for later", inline=True)
comment(0xBA67, "Non-zero format bit: error", inline=True)
comment(0xBA69, "Pop sector count", inline=True)
comment(0xBA6C, "Non-zero verify bit: use verify cmd", inline=True)
comment(0xBA77, "Set head-loaded flag in state", inline=True)
comment(0xBA7A, "Set carry", inline=True)
comment(0xBA7B, "Restore head-loaded flag", inline=True)
comment(0xBA81, "Save sector address on stack", inline=True)
comment(0xBA82, "Get sector address mid byte", inline=True)
comment(0xBA86, "Restore sector address", inline=True)
comment(0xBA91, "Set carry for track calculation", inline=True)
comment(0xBAA1, "Rotate drive select into carry", inline=True)
comment(0xBAA2, "C=0: not last sector, continue", inline=True)
comment(0xBAA4, "Get previous track for drive", inline=True)
comment(0xBAA7, "Store as target track", inline=True)
comment(0xBAA9, "Check head-loaded state", inline=True)
comment(0xBAAC, "Head loaded: skip restore", inline=True)
comment(0xBAB0, "Get alternative track for drive", inline=True)
comment(0xBAB3, "Store as target track", inline=True)
comment(0xBAB5, "Check head-loaded state", inline=True)
comment(0xBAB8, "Not loaded: skip restore", inline=True)
comment(0xBAC6, "Clear seek-complete flag", inline=True)
comment(0xBAC9, "X=0: first FDC register", inline=True)
comment(0xBACE, "X=1: track register", inline=True)
comment(0xBAD2, "X=2: sector register", inline=True)
comment(0xBAD6, "Compare with target track", inline=True)
comment(0xBAD8, "Already on track: skip seek", inline=True)
comment(0xBADA, "Set head-loaded flag", inline=True)
comment(0xBADD, "Set carry", inline=True)
comment(0xBADE, "Restore head-loaded flag", inline=True)
comment(0xBAE1, "FDC seek command (&14)", inline=True)
comment(0xBAE3, "OR in drive select bits", inline=True)
comment(0xBAE6, "Issue seek command to FDC", inline=True)
comment(0xBAEC, "Get control flags", inline=True)
comment(0xBAEE, "Rotate verify flag to carry", inline=True)
comment(0xBAEF, "C=0: no verify, proceed to data", inline=True)
comment(0xBAF4, "Set sector number as target", inline=True)
comment(0xBAF6, "Store as current track", inline=True)
comment(0xBAF8, "Check transfer direction", inline=True)
comment(0xBAFA, "V set: multi-sector operation", inline=True)
comment(0xBAFC, "Y=5: check command byte", inline=True)
comment(0xBAFE, "Get command from control block", inline=True)
comment(0xBB00, "Is it &0B (verify)?", inline=True)
comment(0xBB02, "No, proceed with data transfer", inline=True)
comment(0xBB06, "Clear seek flag and return", inline=True)

# floppy_init_transfer (&BB42) - set up for floppy operation
comment(0xBB44, "Clear error number", inline=True)
comment(0xBB4B, "Store transfer addr low in (&B2)", inline=True)
comment(0xBB50, "Store transfer addr high in (&B3)", inline=True)
comment(0xBB53, "Get control byte 3", inline=True)
comment(0xBB55, "Transfer to X", inline=True)
comment(0xBB57, "Get control byte 4", inline=True)
comment(0xBB59, "Check X+1 for zero (was &FF)", inline=True)
comment(0xBB5A, "X was &FF: check A for &FF too", inline=True)
comment(0xBB5C, "Check X for zero (wrap from &FF)", inline=True)
comment(0xBB5D, "X non-zero: check Tube flag", inline=True)
comment(0xBB5F, "A == &FF?", inline=True)
comment(0xBB61, "Both &FF: host memory, skip Tube", inline=True)
comment(0xBB63, "Check if Tube is present", inline=True)
comment(0xBB65, "No Tube: skip Tube setup", inline=True)
comment(0xBB6A, "Y=5: get command byte from block", inline=True)
comment(0xBB6C, "Read command byte", inline=True)
comment(0xBB6E, "Command 8 (read)?", inline=True)
comment(0xBB70, "Yes, valid command", inline=True)
comment(0xBB72, "Command &0A (write)?", inline=True)
comment(0xBB74, "Yes, valid command", inline=True)
comment(0xBB76, "Command &0B (verify)?", inline=True)
comment(0xBB78, "Yes, valid command", inline=True)
comment(0xBB7A, "Error &67: bad command", inline=True)
comment(0xBB7C, "Store error code", inline=True)
comment(0xBB82, "Set bit 7 of transfer mode", inline=True)
comment(0xBB85, "Set carry for rotate", inline=True)
comment(0xBB86, "Restore bit 7 set", inline=True)
comment(0xBB8C, "Set up drive select and NMI", inline=True)
comment(0xBB8F, "Jump to floppy track setup", inline=True)
comment(0xBB95, "Get FDC step rate setting", inline=True)
comment(0xBB98, "Store in NMI control byte", inline=True)
comment(0xBB9B, "A=0: clear error flag", inline=True)
comment(0xBB9D, "Clear error code", inline=True)
comment(0xBB9F, "Clear transfer state", inline=True)
comment(0xBBA1, "Get transfer mode flags", inline=True)
comment(0xBBA4, "Set bit 5 (NMI active)", inline=True)
comment(0xBBA6, "Store updated mode", inline=True)
comment(0xBBA9, "Store as control flags", inline=True)
comment(0xBBAB, "Get ADFS flags", inline=True)
comment(0xBBAD, "Store in NMI workspace", inline=True)
comment(0xBBB3, "Return", inline=True)

# copy_code_to_nmi_space - remaining items
comment(0xBBF9, "Next byte (loop back)", inline=True)
comment(0xBC18, "Clear bit 1 (read/write direction)", inline=True)
comment(0xBC1A, "Store updated control flags", inline=True)
comment(0xBC1F, "Tube read: use read NMI handler", inline=True)
comment(0xBC2C, "Return", inline=True)
comment(0xBC2D, "Get control flags", inline=True)
comment(0xBC2F, "Rotate bit 7 into carry", inline=True)
comment(0xBC30, "A=0 (will become direction flag)", inline=True)
comment(0xBC32, "Rotate carry into bit 0", inline=True)
comment(0xBC33, "Y=&10: Tube workspace page", inline=True)
comment(0xBC35, "X=&27: Tube workspace offset", inline=True)
comment(0xBC37, "Start Tube transfer", inline=True)
comment(0xBC3A, "Get control flags again", inline=True)
comment(0xBC3C, "Bit 4 set (sector count specified)?", inline=True)
comment(0xBC3E, "No, return (single sector)", inline=True)
comment(0xBC40, "Check read/write direction", inline=True)
comment(0xBC42, "Bit 7 set: reading from disc", inline=True)
comment(0xBC44, "Y=7: copy 8 bytes of Tube write NMI", inline=True)
comment(0xBC46, "Get Tube write NMI handler byte", inline=True)
comment(0xBC49, "Copy to NMI workspace", inline=True)
comment(0xBC4C, "Next byte", inline=True)
comment(0xBC4D, "Loop for 8 bytes", inline=True)
comment(0xBC4F, "Return", inline=True)
comment(0xBC50, "Y=7: copy 8 bytes of Tube read NMI", inline=True)
comment(0xBC52, "Get Tube read NMI handler byte", inline=True)
comment(0xBC55, "Copy to NMI workspace", inline=True)
comment(0xBC58, "Next byte", inline=True)
comment(0xBC59, "Loop for 8 bytes", inline=True)
comment(0xBC5B, "Return", inline=True)
comment(0xBC5C, "Check read/write direction", inline=True)
comment(0xBC5E, "Reading: use default NMI handler", inline=True)
comment(0xBC60, "Y=&0D: copy 14 bytes of write NMI", inline=True)
comment(0xBC62, "Get direct memory write NMI byte", inline=True)
comment(0xBC65, "Copy to NMI workspace", inline=True)
comment(0xBC68, "Next byte", inline=True)
comment(0xBC69, "Loop for 14 bytes", inline=True)
comment(0xBC6B, "Y=1: patch transfer address", inline=True)
comment(0xBC6D, "Get transfer addr low from block", inline=True)
comment(0xBC6F, "Patch NMI handler with addr low", inline=True)
comment(0xBC73, "Get transfer addr high from block", inline=True)
comment(0xBC75, "Patch NMI handler with addr high", inline=True)
comment(0xBC78, "Return", inline=True)

# NMI handler code (&BC79-&BCC1, runs at &0D00-&0D48)
# All comments use runtime addresses with move_id since this
# code is in a move block.

# Entry point: NMI vector fires on each WD1770 DRQ or status change
comment(0x0D00, "Save A (NMI must preserve all regs)", inline=True, move_id=nmi_main_move_id)
comment(0x0D01, "Read WD1770 status register", inline=True, move_id=nmi_main_move_id)
comment(0x0D04, "Mask to low 5 status bits", inline=True, move_id=nmi_main_move_id)
comment(0x0D06, "Status = 3 (data request)?", inline=True, move_id=nmi_main_move_id)
comment(0x0D08, "No: check for error or completion", inline=True, move_id=nmi_main_move_id)

# DRQ handler: transfer one byte (default is read from disc)
# This section is patched by nmi_write_code, nmi_tube_write_code,
# or nmi_tube_read_code depending on the transfer direction.
comment(0x0D0A, "Read byte from WD1770 data register", inline=True, move_id=nmi_main_move_id)
comment(0x0D0D, "Store at transfer address (patched)", inline=True, move_id=nmi_main_move_id)
comment(0x0D10, "Increment transfer address low byte", inline=True, move_id=nmi_main_move_id)
comment(0x0D13, "No page crossing: skip high byte", inline=True, move_id=nmi_main_move_id)
comment(0x0D15, "Increment transfer address high byte", inline=True, move_id=nmi_main_move_id)
comment(0x0D18, "Restore A", inline=True, move_id=nmi_main_move_id)
comment(0x0D19, "Return from NMI", inline=True, move_id=nmi_main_move_id)

# Status/error handler: not a DRQ, check for errors
comment(0x0D1A, "Test error bits: WP, RNF, CRC", inline=True, move_id=nmi_main_move_id)
comment(0x0D1C, "No errors: check for end of operation", inline=True, move_id=nmi_main_move_id)
comment(0x0D1E, "Store error status for caller", inline=True, move_id=nmi_main_move_id)
comment(0x0D20, "Rotate control flags right", inline=True, move_id=nmi_main_move_id)
comment(0x0D22, "Set carry for error flag", inline=True, move_id=nmi_main_move_id)
comment(0x0D23, "Set bit 0: error occurred", inline=True, move_id=nmi_main_move_id)

# Set transfer-complete flag and return
comment(0x0D25, "Rotate state flags right", inline=True, move_id=nmi_main_move_id)
comment(0x0D27, "Set carry for complete flag", inline=True, move_id=nmi_main_move_id)
comment(0x0D28, "Set bit 0: transfer complete", inline=True, move_id=nmi_main_move_id)
comment(0x0D2A, "Restore A", inline=True, move_id=nmi_main_move_id)
comment(0x0D2B, "Return from NMI", inline=True, move_id=nmi_main_move_id)

# End-of-operation: no error, no DRQ — check if track stepping needed
comment(0x0D2C, "Multi-sector mode active? (bit 6)", inline=True, move_id=nmi_main_move_id)
comment(0x0D2E, "No: mark complete and return", inline=True, move_id=nmi_main_move_id)
comment(0x0D30, "Save current ROM bank number", inline=True, move_id=nmi_main_move_id)
comment(0x0D32, "Push onto stack", inline=True, move_id=nmi_main_move_id)
comment(0x0D33, "Select ROM bank 0", inline=True, move_id=nmi_main_move_id)
comment(0x0D35, "Update ROM select shadow copy", inline=True, move_id=nmi_main_move_id)
comment(0x0D37, "Switch to ROM bank 0", inline=True, move_id=nmi_main_move_id)
comment(0x0D3A, "Save X register", inline=True, move_id=nmi_main_move_id)
comment(0x0D3B, "Push onto stack", inline=True, move_id=nmi_main_move_id)
comment(0x0D3C, "Advance to next sector", inline=True, move_id=nmi_main_move_id)
comment(0x0D3F, "Restore X register", inline=True, move_id=nmi_main_move_id)
comment(0x0D40, "Pull from stack", inline=True, move_id=nmi_main_move_id)
comment(0x0D41, "Restore original ROM bank", inline=True, move_id=nmi_main_move_id)
comment(0x0D42, "Update ROM select shadow copy", inline=True, move_id=nmi_main_move_id)
comment(0x0D44, "Switch back to original ROM bank", inline=True, move_id=nmi_main_move_id)
comment(0x0D47, "Restore A", inline=True, move_id=nmi_main_move_id)
comment(0x0D48, "Return from NMI", inline=True, move_id=nmi_main_move_id)

# star_remove - remaining gap items
comment(0x910E, "Store filename addr in OSFILE block", inline=True)
comment(0x9111, "Get filename pointer high", inline=True)
comment(0x9113, "Store in OSFILE block+1", inline=True)
comment(0x9118, "Store control block pointer low", inline=True)
comment(0x911A, "Control block page = &10", inline=True)
comment(0x911C, "Store control block pointer high", inline=True)
comment(0x9136, "Save CSD sector to temp workspace", inline=True)
comment(0x9139, "Next byte", inline=True)
comment(0x913A, "Loop for 4 bytes", inline=True)
comment(0x913E, "Mark alternative workspace as unset", inline=True)
comment(0x9141, "Mark saved drive as unset", inline=True)
comment(0x914A, "Save result (empty flag)", inline=True)
comment(0x914E, "Y=3: restore 4 bytes of CSD sector", inline=True)
comment(0x9153, "Restore CSD sector byte", inline=True)
comment(0x9156, "Next byte", inline=True)
comment(0x9157, "Loop for 4 bytes", inline=True)
comment(0x9159, "Restore empty flag", inline=True)
comment(0x9170, "X=2: 3 bytes of length to process", inline=True)
comment(0x917E, "Next length byte", inline=True)
comment(0x917F, "Loop for 3 bytes", inline=True)
comment(0x9183, "X=2: copy 3 sector address bytes", inline=True)
comment(0x9187, "Store sector address byte", inline=True)
comment(0x918A, "Next entry byte (decreasing)", inline=True)
comment(0x918B, "Next workspace byte (decreasing)", inline=True)
comment(0x918C, "Loop for 3 bytes", inline=True)
comment(0x918E, "Y=3: check access byte for dir flag", inline=True)
comment(0x9197, "Saved drive = &FF (not set)?", inline=True)
comment(0x91A0, "X=2: compare 3 sector bytes", inline=True)
comment(0x91A5, "Compare with CSD sector byte", inline=True)
comment(0x91A8, "Mismatch: not the CSD", inline=True)
comment(0x91C5, "Compare drive with library drive", inline=True)
comment(0x91C8, "Different: not the library", inline=True)
comment(0x91CF, "Compare with library sector byte", inline=True)
comment(0x91D5, "Loop for 3 bytes", inline=True)
comment(0x91F3, "Compare drive with prev dir drive", inline=True)
comment(0x91F6, "Different: skip prev dir reset", inline=True)
comment(0x91FA, "Get object sector byte", inline=True)
comment(0x91FD, "Compare with prev dir sector", inline=True)
comment(0x9207, "Reset prev dir to root (sector 2)", inline=True)
comment(0x920A, "A=0: clear high sector bytes", inline=True)
comment(0x920C, "Clear prev dir mid byte", inline=True)
comment(0x920F, "Clear prev dir high byte", inline=True)
comment(0x921D, "X=0: for indirect store via (&B6,X)", inline=True)
comment(0x9225, "No page crossing", inline=True)
comment(0x9227, "Increment pointer high byte", inline=True)
comment(0x9229, "Check if past end of entries", inline=True)
comment(0x922D, "Low byte not at boundary, continue", inline=True)

# service_handler_8 - remaining items
comment(0x9D1A, "Save Y on stack", inline=True)
comment(0x9D2F, "Get control block high byte", inline=True)
comment(0x9D31, "Store in (&BB)", inline=True)
comment(0x9D37, "Copy control block to workspace", inline=True)
comment(0x9D3A, "Next byte", inline=True)
comment(0x9D3B, "Loop for 16 bytes", inline=True)
comment(0x9D48, "Y=&10: workspace control block", inline=True)
comment(0x9D5C, "Process verify result", inline=True)
comment(0x9D66, "Restore Y", inline=True)
comment(0x9D69, "Return (service claimed)", inline=True)
comment(0x9D6C, "Restore Y", inline=True)
comment(0x9D6D, "Transfer to Y", inline=True)
comment(0x9D70, "Return (not claimed)", inline=True)
comment(0x9D7A, "Store error byte in control block", inline=True)
comment(0x9D7C, "Next byte", inline=True)
comment(0x9D7D, "Loop for 5 error bytes", inline=True)
comment(0x9DA0, "Store free space byte", inline=True)
comment(0x9DA2, "Next byte", inline=True)
comment(0x9DA3, "Loop for 4 bytes", inline=True)

# star_access - remaining items
comment(0x994D, "Next name byte", inline=True)
comment(0x994E, "Loop for 3 bytes", inline=True)
comment(0x9950, "Return (attributes cleared)", inline=True)
comment(0x9976, "Next filename character", inline=True)
comment(0x9977, "Loop scanning filename", inline=True)
comment(0x997B, "Is it a space?", inline=True)
comment(0x9981, "Is it a double-quote?", inline=True)
comment(0x9983, "No, start parsing attribute chars", inline=True)
comment(0x9985, "Skip quote character", inline=True)
comment(0x9986, "Continue skipping spaces", inline=True)
comment(0x999A, "Get entry byte at attribute pos", inline=True)
comment(0x999E, "Store with E bit set", inline=True)
comment(0x99A0, "Save E flag for later checks", inline=True)
comment(0x99AF, "E already set: only L allowed", inline=True)
comment(0x99B1, "Try next R/W/L character", inline=True)
comment(0x99B2, "Loop through R, W, L", inline=True)
comment(0x99B8, "Next attribute character", inline=True)
comment(0x99B9, "Continue parsing", inline=True)
comment(0x99C6, "Save workspace and return", inline=True)
comment(0x99CA, "Save Y (text position) on stack", inline=True)
comment(0x99D4, "Restore Y", inline=True)

# star_cmd - remaining items
comment(0x9E84, "Store workspace pointer low", inline=True)
comment(0x9E86, "Workspace page = &10", inline=True)
comment(0x9E88, "Store workspace pointer high", inline=True)
comment(0x9E90, "Next table entry", inline=True)
comment(0x9E94, "Next argument character", inline=True)
comment(0x9EA4, "Back up table pointer", inline=True)
comment(0x9EB2, "Always branch (Y != 0)", inline=True)
comment(0x9EBD, "Not alpha: command name complete", inline=True)
comment(0x9EC4, "Clear carry for pointer advance", inline=True)
comment(0x9EC5, "Add matched length to pointer", inline=True)
comment(0x9EC7, "Store updated pointer low", inline=True)
comment(0x9EC9, "No page crossing", inline=True)
comment(0x9ECB, "Increment pointer high page", inline=True)
comment(0x9ED2, "Save text pointer low for handler", inline=True)
comment(0x9ED5, "Get text pointer high", inline=True)
comment(0x9ED7, "Save for handler", inline=True)
comment(0x9FD8, "X=&30 ('0'): lowest ADFS file handle", inline=True)
comment(0x9FDA, "Y=&39 ('9'): highest ADFS file handle", inline=True)
comment(0x9FDC, "Return to FSC dispatcher", inline=True)
comment(0x9FE7, "Get ADFS flags", inline=True)
comment(0x9FE9, "Set bit 2 (*OPT1 verbose on)", inline=True)
comment(0x9FEF, "Clear bit 2 (*OPT1 verbose off)", inline=True)
comment(0x9FFA, "Validate FSM before modification", inline=True)
comment(0x9FFD, "Check for disc change, reload if needed", inline=True)
comment(0xA016, "A=&20: space character", inline=True)

# star_run - remaining items
comment(0xA39B, "Store in save area low", inline=True)
comment(0xA39D, "Get filename high byte", inline=True)
comment(0xA39F, "Store in save area high", inline=True)
comment(0xA3AB, "Restore filename low", inline=True)
comment(0xA3AD, "Get saved high byte", inline=True)
comment(0xA3AF, "Restore filename high", inline=True)
comment(0xA3BE, "Store filename addr for OSFILE", inline=True)
comment(0xA3C1, "Get filename pointer high", inline=True)
comment(0xA3C3, "Store in OSFILE block", inline=True)
comment(0xA3CD, "AND exec addr bytes together", inline=True)
comment(0xA3CF, "Next byte", inline=True)
comment(0xA3D0, "Loop for 3 bytes", inline=True)
comment(0xA3D8, "Get directory entry pointer high", inline=True)
comment(0xA3E4, "Y: high byte of E.$.!BOOT string", inline=True)
comment(0xA3EB, "Get load addr byte 1", inline=True)
comment(0xA3EE, "AND with byte 2", inline=True)
comment(0xA3F1, "AND with byte 3", inline=True)
comment(0xA403, "Store exec addr for later JMP", inline=True)
comment(0xA406, "X=&A2: OSFILE block offset", inline=True)
comment(0xA408, "Y=&10: OSFILE block page", inline=True)
comment(0xA40A, "Store block pointer low", inline=True)
comment(0xA40C, "Store block pointer high", inline=True)
comment(0xA415, "Y=0: check low byte of exec addr", inline=True)
comment(0xA424, "High byte = &FF (Tube address)?", inline=True)
comment(0xA426, "No, check further", inline=True)
comment(0xA428, "Get next exec addr byte", inline=True)
comment(0xA42B, "Is it >= &FE (I/O space)?", inline=True)
comment(0xA42D, "No, normal Tube address", inline=True)
comment(0xA43D, "Y=&10: Tube workspace page", inline=True)

# generate_error_suffix_x - remaining items
comment(0x8354, "Store inline data pointer low", inline=True)
comment(0x8357, "Store inline data pointer high", inline=True)
comment(0x835B, "Mask off bit 4", inline=True)
comment(0x835D, "Store cleared flags", inline=True)
comment(0x8362, "Read error msg byte from inline data", inline=True)
comment(0x836E, "Store space in error block", inline=True)
comment(0x8379, "Jump to hex formatting", inline=True)
comment(0x838C, "Next character in reversed string", inline=True)
comment(0x838D, "Loop for 5 chars of ' at :'", inline=True)
comment(0x8393, "Rotate drive bits to low nibble", inline=True)
comment(0x8394, "Second rotate", inline=True)
comment(0x8395, "Third rotate", inline=True)
comment(0x839F, "Advance to next position", inline=True)
comment(0x83A0, "Store separator in error block", inline=True)
comment(0x83B8, "Store zero terminator", inline=True)
comment(0x83C2, "Back up one position", inline=True)
comment(0x83C6, "Advance position", inline=True)
comment(0x83CA, "Next character in reversed string", inline=True)
comment(0x83CB, "Loop for 12 chars", inline=True)
comment(0x83D3, "Save current position", inline=True)
comment(0x83D4, "Push Y on stack", inline=True)
comment(0x83D7, "Store OSBYTE number in workspace", inline=True)
comment(0x83E0, "Save flags for comparison result", inline=True)
comment(0x83E1, "X=&99: EXEC string address", inline=True)
comment(0x83E3, "Restore flags", inline=True)
comment(0x83F0, "Restore Y (position)", inline=True)
comment(0x83F1, "Transfer back to Y", inline=True)
comment(0x83F5, "Non-zero: skip workspace update", inline=True)
comment(0x83F7, "Update workspace checksum", inline=True)
comment(0x83FC, "Store BRK opcode (&00) at start", inline=True)

# RTS instructions in completed subroutines
comment(0x8064, "Return", inline=True)
comment(0x807F, "Return", inline=True)
comment(0x830E, "Return", inline=True)
comment(0x831A, "Return", inline=True)
comment(0x8448, "Return", inline=True)
comment(0x8475, "Return", inline=True)
comment(0x9500, "Return", inline=True)
comment(0x9A77, "Return", inline=True)
comment(0xA155, "Return", inline=True)
byte(0xA156, 1)
comment(0xA156, "CR (read backwards as name terminator)", inline=True)
string(0xA157, 7)
comment(0xA157, 'Reversed: \'"Unset"\' default dir name', inline=True)
comment(0xA4B6, "Return", inline=True)
comment(0xA6F8, "Return", inline=True)
comment(0xA719, "Return", inline=True)
comment(0xA72A, "Return", inline=True)
comment(0xA730, "Return", inline=True)
comment(0xAD15, "Return", inline=True)
comment(0xBB13, "Return", inline=True)
comment(0xBBE6, "Return", inline=True)
comment(0xBD57, "Return", inline=True)
comment(0xBFAD, "Return", inline=True)
comment(0x8300, "Return (success)", inline=True)
comment(0x8304, "Return", inline=True)
comment(0xA0FE, "Decrement Y (was INY+1)", inline=True)
comment(0xA110, "Return", inline=True)

# Loop body items in nearly-complete subroutines
comment(0x81B3, "Restore Y", inline=True)
comment(0x81B7, "Return", inline=True)
comment(0x82BB, "Not drive overrun, check other codes", inline=True)
comment(0x871C, "Strip bit 7 of character", inline=True)
comment(0x872C, "Return (not a terminator)", inline=True)
comment(0x9447, "Store low byte", inline=True)
comment(0x954A, "Next byte in name copy", inline=True)
comment(0x9562, "Next byte in sector copy", inline=True)
comment(0xA067, "Advance X: 2nd byte of 3-byte entry", inline=True)
comment(0xA068, "Advance X: 3rd byte of 3-byte entry", inline=True)
comment(0xA44F, "Next byte in name copy", inline=True)
comment(0xA45A, "Next byte in sector copy", inline=True)
comment(0xA46F, "Always branch (loop back)", inline=True)
comment(0xA6F9, "Dir broken: save drive and error", inline=True)
comment(0xBBDE, "Y = NMI owner return value", inline=True)
comment(0xBF64, "Compare always false (A >= 0)", inline=True)
comment(0xBF8A, "Transfer low byte to X", inline=True)

# ---------------------------------------------------------------------------
# Subroutine descriptions
# ---------------------------------------------------------------------------

subroutine(0x8027, "claim_tube", title="Claim Tube if present",
    description="""\
Claim the Tube for a data transfer if a Tube is present.
Copies the 4-byte transfer address from the control block
to workspace and sets the Tube-in-use flag.
""")

subroutine(0x8043, "release_tube", title="Release Tube if in use",
    description="""\
Release the Tube after a data transfer if it was claimed.
Checks zp_adfs_flags bit 6 and clears it after release.
""")

subroutine(0x8056, "scsi_get_status",
    title="Read SCSI status with settling",
    description="""\
Read the SCSI status register, waiting for the value to settle.
Reads the status twice and loops until consecutive reads match.
Also stores result in zp_scsi_status.
""",
    on_exit={"a": "settled SCSI status byte",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8065, "scsi_start_command",
    title="SCSI bus selection and command phase",
    description="""\
Select a SCSI device on the bus and begin the command phase.
Asserts the target's SCSI ID on the data bus and waits for
the BSY signal to be asserted by the target.
""")

subroutine(0x8080, "command_set_retries",
    title="Set retry count for disc operation",
    description="""\
Set the retry counter to the default value (16).
""")

subroutine(0x8089, "command_exec_xy",
    title="Execute disc command with control block at (X,Y)",
    description="""\
Execute a disc operation using the control block pointed to
by X (low) and Y (high). Handles both hard drive (SCSI) and
floppy disc operations with retry logic.
""",
    on_entry={"x": "control block address low byte",
              "y": "control block address high byte"},
    on_exit={"a": "result code (0 = success, Z set)",
             "x": "control block address low (preserved)",
             "y": "control block address high (preserved)"})

subroutine(0x829A, "generate_error",
    title="Generate a BRK error",
    description="""\
Generate a BRK error from the disc error code in A. Never
returns to caller.
""",
    on_entry={"a": "SCSI/disc error code"})

subroutine(0x9AA3, "service_call_handler",
    title="ROM service call handler",
    description="""\
Main entry point for MOS service calls. Dispatches to
individual handlers based on the service call number in A.
""")

subroutine(0x9E50, "fscv_handler",
    title="Filing system control vector handler",
    description="""\
Handle filing system control calls via FSCV. Dispatches
star commands, *RUN, *CAT, etc.
""")

subroutine(0x923E, "osfile_handler",
    title="OSFILE handler",
    description="""\
Handle OSFILE calls for whole-file operations: load, save,
read/write catalogue info, delete, create.
""")

subroutine(0xA955, "osargs_handler",
    title="OSARGS handler",
    description="""\
Handle OSARGS calls for reading and writing file arguments
(PTR, EXT, allocation) and filing system information.
""")

subroutine(0xAD63, "osbget_handler",
    title="OSBGET handler",
    description="""\
Handle OSBGET calls to read a single byte from an open file.
""")

subroutine(0xB08F, "osbput_handler",
    title="OSBPUT handler",
    description="""\
Handle OSBPUT calls to write a single byte to an open file.
""")

subroutine(0xB1B6, "osfind_handler",
    title="OSFIND handler",
    description="""\
Handle OSFIND calls to open and close files for byte access.
""")

subroutine(0xB57F, "osgbpb_handler",
    title="OSGBPB handler",
    description="""\
Handle OSGBPB calls for reading and writing groups of bytes.
""")

subroutine(0x80ED, "hd_command",
    title="Execute hard drive SCSI command",
    description="""\
Execute a disc operation via the SCSI hard drive interface.
Sends the SCSI command bytes from the control block at (&B0),
performs data transfer (direct or via Tube), and reads the
SCSI status and message phases.

Falls back to floppy if drive bit 7 is set.
""",
    on_exit={"a": "result code (0 = success, Z set)",
             "x": "control block address low (restored)",
             "y": "control block address high (restored)"})

subroutine(0x818A, "command_done",
    title="Complete SCSI command and read status",
    description="""\
Release the Tube, then read the SCSI status and message
bytes to determine the outcome of the command.
""",
    on_exit={"a": "result code (0 = success, &7F-masked error)",
             "x": "control block address low (restored)",
             "y": "control block address high (restored)"})

subroutine(0x81B8, "hd_data_transfer_256",
    title="SCSI 256-byte sector data transfer",
    description="""\
Transfer complete 256-byte sectors between SCSI bus and
memory (direct or via Tube). Optimised inner loop with no
per-byte SCSI REQ polling.
""")

subroutine(0x823A, "scsi_request_sense",
    title="SCSI Request Sense command",
    description="""\
Send a SCSI Request Sense command (opcode 3) to retrieve
extended error information after a failed operation. Stores
the 4-byte sense data in the error workspace.
""",
    on_exit={"a": "error code from sense data (&FF if unrecoverable)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x82FB, "scsi_send_cmd_byte",
    title="Send one byte during SCSI command phase",
    description="""\
Wait for SCSI REQ, then write byte A to the SCSI data bus.
Returns only on success; generates BRK on error.
""",
    on_entry={"a": "SCSI command byte to send"})

subroutine(0x8305, "wait_ensuring",
    title="Wait while files are being ensured",
    description="""\
If zp_flags bit 0 (ensuring) is set, loop until it clears.
This prevents disc operations during file ensure operations.
""")

subroutine(0x830F, "scsi_wait_for_req",
    title="Wait for SCSI REQ signal",
    description="""\
Poll the SCSI status register until the REQ bit is asserted,
indicating the target is ready for the next bus phase.
Preserves A; N and V flags reflect SCSI bus phase.
""",
    on_exit={"a": "preserved",
             "x": "preserved", "y": "preserved",
             "n": "C/D bit from SCSI status (set = command phase)",
             "v": "MSG bit from SCSI status (set = message phase)"})

subroutine(0x831B, "scsi_send_byte_a",
    title="Send byte A on SCSI bus after REQ",
    description="""\
Wait for SCSI REQ then write A to the SCSI data register.
May not return if MSG phase detected (unwinds call stack
to command_done).
""",
    on_entry={"a": "byte to send on SCSI bus"})

subroutine(0x8348, "reload_fsm_and_dir_then_brk",
    title="Reload FSM and directory then raise error",
    description="""\
Reload the free space map and current directory from disc,
then generate a BRK error. Used after operations that may
have left the in-memory copies inconsistent.
""")

subroutine(0x8351, "generate_error_no_suffix",
    title="Generate error without drive/sector suffix",
    description="""\
Generate a BRK error from the disc error code without
appending the drive:sector suffix.
""")

subroutine(0x8353, "generate_error_suffix_x",
    title="Generate error with suffix control in X",
    description="""\
Generate a BRK error from the inline error data following
the JSR. X controls whether the drive:sector suffix is
appended. Never returns.
""",
    on_entry={"x": "non-zero to append drive:sector suffix"})

subroutine(0x8476, "invalidate_fsm_and_dir",
    title="Mark FSM and directory as invalid",
    description="""\
Set flags to indicate that the in-memory free space map and
directory buffer may be stale and need reloading from disc.
""",
    on_exit={"a": "zero", "x": "corrupted", "y": "zero"})

subroutine(0xA6C7, "check_dir_loaded",
    title="Ensure current directory is loaded",
    description="""\
Check that the current directory buffer contains valid data.
If not, reload it from disc.
""")

subroutine(0xA70E, "get_wksp_addr_ba",
    title="Get workspace address into &BA",
    description="""\
Load a workspace address into zero page locations &BA-&BB.
""")

subroutine(0xA71A, "calc_wksp_checksum",
    title="Calculate workspace checksum",
    description="""\
Calculate a checksum over the workspace area for integrity
checking.
""")

subroutine(0xA731, "check_wksp_checksum",
    title="Verify workspace checksum",
    description="""\
Check the workspace checksum matches the stored value.
Raises a Bad checksum error if verification fails.
""")

subroutine(0xA816, "load_fsm",
    title="Load free space map from disc",
    description="""\
Read sectors 0 and 1 from the current drive into the free
space map workspace at &0E00-&0FFF. Validates the checksum.
""")

subroutine(0x842D, "error_append_hex",
    title="Append byte as two hex digits to error block",
    description="""\
Write the byte in A as two ASCII hex digits into the
error block at the current position Y.
""",
    on_entry={"a": "byte value to convert to hex", "y": "index into brk_error_block"},
    on_exit={"a": "ASCII hex digit of low nibble", "x": "preserved", "y": "advanced by 2"})

subroutine(0x843E, "hex_digit",
    title="Convert 4-bit value to ASCII hex digit",
    description="""\
Convert a 4-bit value in A to an ASCII hex character
('0'-'9' or 'A'-'F'). The low nibble of A is used.
""",
    on_entry={"a": "value with hex digit in low nibble"},
    on_exit={"a": "ASCII hex character ('0'-'9' or 'A'-'F')", "x": "preserved", "y": "preserved"})

subroutine(0x8449, "error_append_dec",
    title="Append byte as decimal digits to error block",
    description="""\
Write the byte in A as up to three decimal digits into
the error block at the current position Y, suppressing
leading zeros.
""",
    on_entry={"a": "byte value to convert to decimal", "y": "index into brk_error_block"},
    on_exit={"a": "corrupted", "x": "corrupted", "y": "advanced past decimal digits"})

subroutine(0x9ACF, "service_handler_1",
    title="Service 1: absolute workspace claim",
    description="""\
Initialise ADFS on a ROM filing system init service call.
Checks for floppy and hard drive hardware. If either is
present, claims the ROM workspace slot and raises PAGE
to make room for ADFS workspace.
""")

subroutine(0x9AF1, "service_handler_2",
    title="Service 2: private workspace claim",
    description="""\
Claim private workspace pages. On hard break, initialises
the workspace with default values (CSD name, directory
sector pointers, checksum). On soft break, preserves
existing workspace. Sets up the filing system vectors
and checks for Tube presence.
""")

subroutine(0x9B41, "service_handler_3",
    title="Service 3: auto-boot",
    description="""\
Handle auto-boot on power-on or Ctrl+Break. Scans the
keyboard for Shift+Break (floppy boot) or A+Break
(hard drive boot). Selects ADFS as the filing system
and executes the boot file if configured.
""")

subroutine(0x9CDA, "service_handler_4",
    title="Service 4: unrecognised star command",
    description="""\
Handle unrecognised star commands passed to filing system
ROMs. Matches commands against the ADFS command table
and dispatches to the appropriate handler.
""")

subroutine(0x9D19, "service_handler_8",
    title="Service 8: unrecognised OSWORD",
    description="""\
Handle unrecognised OSWORD calls. ADFS claims OSWORD &72
for direct disc access.
""")

subroutine(0x9DBE, "service_handler_9",
    title="Service 9: *HELP",
    description="""\
Handle *HELP requests. Prints ADFS version information
when *HELP ADFS is entered.
""")

subroutine(0x84A7, "oscli_at_x",
    title="Execute OSCLI with string at X",
    description="""\
Call OSCLI with the command string address in X (low byte).
""",
    on_entry={"x": "low byte of command string address in page &84"},
    on_exit={"a": "corrupted", "x": "corrupted", "y": "corrupted"})

subroutine(0x871A, "check_char_is_terminator",
    title="Check if character is a filename terminator",
    description="""\
Test whether the character at (&B4),Y is a filename
terminator. Bit 7 is stripped with AND #&7F before any
comparison, so &8D (CR with bit 7 set) is treated
identically to &0D. After stripping, any character below
space (&20) is a terminator, as are '.' and '"'.

Used for parsing user-typed command-line text, not for
scanning on-disc directory entry names directly.
""",
    on_entry={"y": "index into text at (&B4)"},
    on_exit={"a": "character with bit 7 stripped (Z set if terminator)",
             "x": "0 if terminator, else preserved",
             "y": "preserved"})

subroutine(0x8B1E, "floppy_partial_sector",
    title="Floppy disc partial sector transfer",
    description="""\
Transfer a partial sector (less than 256 bytes) to or from
a floppy disc. Used for operations that don't align to
sector boundaries.
""")

subroutine(0x8B41, "hd_command_partial_sector",
    title="Hard drive partial sector transfer",
    description="""\
Transfer a partial sector via the SCSI hard drive interface.
""")

subroutine(0x8D21, "check_open",
    title="Check if file is open",
    description="""\
Check whether any files are currently open on a given drive.
Used before operations that would be unsafe with open files.
""")

subroutine(0x9109, "star_remove",
    title="*REMOVE command handler",
    description="""\
Remove a file from the current directory. Unlike *DELETE,
*REMOVE does not report an error if the file is locked.
""")

subroutine(0x9433, "star_ex",
    title="*EX command handler",
    description="""\
Display a full catalogue of the current or specified
directory, showing filename, attributes, load and execution
addresses, length, and start sector for each entry.
""")

subroutine(0x94E7, "star_info",
    title="*INFO command handler",
    description="""\
Display catalogue information for a single file, with the
same format as *EX but for one file only. Supports wildcards.
""")

subroutine(0x953F, "star_dir",
    title="*DIR command handler",
    description="""\
Change the currently selected directory. With no argument,
selects the root directory of the current drive.
""")

subroutine(0x9570, "star_cdir",
    title="*CDIR command handler",
    description="""\
Create a new directory. Allocates 5 contiguous sectors on
disc and initialises the directory structure with the Hugo
identifier, title, and parent pointer.
""")

subroutine(0x9632, "osfile_tpl_cdir",
    title="OSFILE control block template for *CDIR",
    description="""\
16-byte template copied to the OSFILE control block at
&1042-&1051 when creating a new directory. Sets the data
region to &1700-&1BFF (the 5-page random access buffer
area used as scratch space to build the new directory
before writing to disc). The &FFFF prefix marks host
memory (not Tube).
""")

subroutine(0x993D, "star_access",
    title="*ACCESS command handler",
    description="""\
Change the access attributes of a file. Attributes are
specified as a combination of L (locked), W (write), R (read),
D (directory), and E (execute).
""")

subroutine(0x99E6, "star_destroy",
    title="*DESTROY command handler",
    description="""\
Delete multiple files matching a wildcard specification.
Prompts for confirmation before deleting.
""")

subroutine(0x9A43, "jmp_indirect_fscv",
    title="Jump through FSCV indirect vector",
    description="""\
Jump indirectly through the filing system control vector.
""")

subroutine(0x9A63, "hd_init_detect",
    title="Detect hard drive hardware",
    description="""\
Check whether a SCSI hard drive is present by attempting
to read the SCSI status register.
""",
    on_exit={"a": "corrupted (Z set if hard drive present)",
             "x": "zero", "y": "preserved"})

subroutine(0x9E7F, "star_cmd",
    title="Parse and dispatch star command",
    description="""\
Match the command string at (&B4) against the command table
at tbl_commands. The table encodes command names with their
dispatch addresses. Supports abbreviation with dot.

Uses RTS-trick dispatch to the matched command handler.
""")

subroutine(0xA01B, "star_free",
    title="*FREE command handler",
    description="""\
Display the free space remaining on the current or specified
drive, in bytes and as a number of sectors.
""")

subroutine(0xA04A, "star_map",
    title="*MAP command handler",
    description="""\
Display the free space map of the current or specified drive,
showing the address and length of each free space region.
""")

subroutine(0xA0BB, "star_delete",
    title="*DELETE command handler",
    description="""\
Delete a file from the current directory. Reports an error
if the file is locked.
""")

subroutine(0xA0C3, "star_bye",
    title="*BYE command handler",
    description="""\
Close all open files and dismount all drives. Equivalent
to *CLOSE followed by *DISMOUNT for all drives.
""")

subroutine(0xA0EA, "scsi_cmd_park",
    title="SCSI park heads disc operation control block",
    description="""\
Disc operation control block used by *BYE to park the hard
drive heads on shutdown. Referenced indirectly as X=&EA, Y=&A0
from the close_each_drive_loop. Issues SCSI command &1B
(Start/Stop Unit) with count=0 (stop/park). The companion
block at scsi_cmd_unpark (&A19F) has count=1 (start/unpark)
and is used by *MOUNT.
""")

subroutine(0xA19F, "scsi_cmd_unpark",
    title="SCSI unpark heads disc operation control block",
    description="""\
Disc operation control block used by *MOUNT to unpark (spin up)
the hard drive heads. Referenced indirectly as X=&9F, Y=&A1
from star_mount. Issues SCSI command &1B (Start/Stop Unit)
with count=1 (start/unpark). The companion block at
scsi_cmd_park (&A0EA) has count=0 (stop/park) and is used
by *BYE.
""")

subroutine(0xA111, "star_dismount",
    title="*DISMOUNT command handler",
    description="""\
Close all open files on the specified drive and mark the
drive as not mounted.
""")

subroutine(0xA15E, "star_mount",
    title="*MOUNT command handler",
    description="""\
Mount a drive by loading its free space map and root
directory into memory.
""")

subroutine(0xA252, "star_title",
    title="*TITLE command handler",
    description="""\
Change the title of the currently selected directory. The
title may be up to 19 characters long.
""")

subroutine(0xA276, "star_compact",
    title="*COMPACT command handler",
    description="""\
Compact the free space on a drive by moving files to
consolidate fragmented free space into a single contiguous
region.
""")

subroutine(0xA399, "star_run",
    title="*RUN command handler",
    description="""\
Load and execute a file. Sets the execution address from the
file's catalogue entry.
""")

subroutine(0xA444, "star_lib",
    title="*LIB command handler",
    description="""\
Change the current library directory. The library is searched
for commands not found in the current directory.
""")

subroutine(0xA47F, "star_lcat",
    title="*LCAT command handler",
    description="""\
Display a catalogue of the current library directory.
""")

subroutine(0xA48B, "star_lex",
    title="*LEX command handler",
    description="""\
Display a full catalogue of the current library directory,
with the same format as *EX.
""")

subroutine(0xA497, "star_back",
    title="*BACK command handler",
    description="""\
Switch the current directory to the previously selected
directory and vice versa.
""")

subroutine(0xA503, "star_rename",
    title="*RENAME command handler",
    description="""\
Rename a file or move it between directories on the same
drive. The source and destination must be on the same drive.
""")

subroutine(0xA81D, "star_copy",
    title="*COPY command handler",
    description="""\
Copy a file. The source and destination may be on different
drives.
""")

subroutine(0xB1B3, "star_close",
    title="*CLOSE command handler",
    description="""\
Close all open files on all drives.
""")

subroutine(0x92A0, "print_inline_string",
    title="Print bit-7-terminated inline string",
    description="""\
Pop the return address from the stack, print the inline
string that follows the JSR instruction. Characters are
printed via OSASCI until a byte with bit 7 set is found
(the last character, printed with bit 7 stripped). Pushes
the address past the string so RTS continues after it.
""",
    on_exit={"a": "corrupted", "x": "preserved", "y": "corrupted"})

subroutine(0xAAC6, "hd_command_bget_bput_sector",
    title="Hard drive single sector for BGET/BPUT",
    description="""\
Read or write a single sector via the SCSI interface for
byte-level file access (BGET/BPUT channel operations).
""",
    on_entry={"a": "SCSI command byte (&08=read, &0A=write)",
              "x": "channel buffer table offset"})

subroutine(0xACFE, "check_set_channel_y",
    title="Validate and set channel number from Y",
    description="""\
Check that Y contains a valid file handle and set the
channel offset workspace variable.
""",
    on_entry={"y": "file handle (&30-&39)"},
    on_exit={"a": "channel flags from wksp_ch_flags",
             "x": "channel offset", "y": "preserved"})

subroutine(0xAD16, "compare_ext_to_ptr",
    title="Compare file EXT to PTR",
    description="""\
Compare the file extent (EXT) with the current pointer
(PTR) for the channel in the workspace.
""",
    on_exit={"a": "last compared EXT byte (C clear if at EOF)",
             "x": "channel offset", "y": "preserved"})

subroutine(0xA93C, "fsc6_new_filing_system",
    title="FSC 6: new filing system selected",
    description="""\
Handle the FSC 6 call which notifies ADFS that a new
filing system is being selected. Ensures all files are
closed and workspace is saved.
""")

subroutine(0xBA00, "floppy_command_ind",
    title="Floppy disc command (indirect entry)",
    description="""\
Indirect entry point for floppy disc operations.
Jumps through to floppy_command.
""")

subroutine(0xBA11, "floppy_check_present",
    title="Check floppy disc hardware present",
    description="""\
Test whether the WD1770 floppy disc controller is present
by probing its registers.
""",
    on_exit={"a": "corrupted (C set if present, clear if not)",
             "x": "preserved", "y": "preserved"})

subroutine(0xBB14, "floppy_command",
    title="Execute floppy disc command",
    description="""\
Execute a disc operation on the floppy disc using the
WD1770 controller. Handles sector read, write, and
format operations.
""")

subroutine(0xBBB4, "floppy_get_step_rate",
    title="Get floppy step rate",
    description="""\
Fetch the startup options byte via OSBYTE &FF and use
bits 4 and 5 to set the FDC step rate and head settle
time in milliseconds.
""")

subroutine(0xBBF1, "copy_code_to_nmi_space",
    title="Copy NMI handler code to NMI workspace",
    description="""\
Copy the NMI handler routine from ROM to the NMI workspace
at &0D00. The NMI handler is used for byte-by-byte data
transfer between the WD1770 and memory.
""")

subroutine(0xBCC2, "floppy_wait_nmi_finish",
    title="Wait for floppy NMI transfer to complete",
    description="""\
Wait for the WD1770 floppy disc controller to complete
a data transfer. Polls the controller status register.
""")

subroutine(0xBD19, "floppy_set_side_0_unused",
    title="Unused: select floppy disc side 0",
    description="""\
Unreferenced routine that clears bit 2 of the NMI drive
control byte at &0D5E, selecting side 0 of a double-sided
floppy disc. The inverse of floppy_set_side_1 which sets
bit 2. Dead code — side 0 is the default so no explicit
selection is needed.
""")

subroutine(0xBD22, "floppy_set_side_1",
    title="Select floppy disc side 1",
    description="""\
Select side 1 (the second side) of a double-sided floppy
disc by setting the appropriate control register bit.
""")

subroutine(0xBD3F, "floppy_restore_track_0",
    title="Seek floppy head to track 0",
    description="""\
Issue a restore command to the WD1770 to seek the
read/write head to track 0.
""")

subroutine(0xBF55, "floppy_ts_block_check_range",
    title="Calculate track/sector from block with range check",
    description="""\
Convert a logical block number to a physical track and
sector number for the floppy disc, checking that the
block is within the valid range for the disc.
""")

subroutine(0xBF86, "floppy_ts_b0_block",
    title="Calculate track/sector from block at &B0",
    description="""\
Convert the logical block number at (&B0) to a physical
track and sector number.
""")

subroutine(0xBFA2, "xa_div_16_to_ya",
    title="Divide X:A by 16, result in Y:A",
    description="""\
Divide the 16-bit value X:A by 16 (shift right 4 places).
Result quotient in Y, remainder in A.
""",
    on_entry={"x": "dividend high byte", "a": "dividend low byte",
              "y": "must be &FF (initial quotient)"},
    on_exit={"a": "remainder (0-15)", "x": "corrupted",
             "y": "quotient"})

subroutine(0xBFAE, "floppy_error",
    title="Handle floppy disc error",
    description="""\
Process an error from the WD1770 floppy disc controller.
Translates the controller error code into an ADFS error
code and stores the error information in workspace.
""")

subroutine(0x81EF, "tube_start_xfer_sei",
    title="Start Tube transfer with interrupts disabled",
    description="""\
Disable interrupts then call the Tube host code at &0406
to initiate a data transfer.
""",
    on_entry={"a": "Tube transfer type (6=write, 7=read)"})

subroutine(0x81F0, "tube_start_xfer",
    title="Start Tube transfer",
    description="""\
Call the Tube host code at &0406 to initiate a data transfer.
Followed by a delay for Tube synchronisation.
""",
    on_entry={"a": "Tube transfer type"})

# ---------------------------------------------------------------------------
# Promoted routines: labels with high in-degree, come-from distance,
# or preceded by terminal instructions that are clearly standalone.
# ---------------------------------------------------------------------------

subroutine(0x89D3, "save_wksp_and_return",
    title="Save workspace state and return result",
    description="""\
Restore the original drive if changed, reload the FSM,
restore alternative workspace if set, and save workspace
with checksum. Return value passed via A on stack.
""",
    on_entry={"a": "result value to preserve across save"},
    on_exit={"a": "result value from entry (preserved)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8F86, "write_dir_and_validate",
    title="Write directory and FSM back to disc",
    description="""\
Verify directory integrity, validate the free space map
entries, then write the current directory to disc. Update
the disc ID low byte from the System VIA Timer 1 counter
(pseudo-random, for disc-change detection), cache both
disc ID bytes in per-drive workspace, recalculate FSM
checksums, and write both FSM sectors to disc.
""")

subroutine(0x8FDF, "find_first_matching_entry",
    title="Find first matching directory entry",
    description="""\
Parse a filename from the command line and search the
current directory for the first entry matching the
parsed filename pattern.
""",
    on_exit={"a": "corrupted (Z set if found, (&B6) points to entry)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8287, "exec_disc_op_from_wksp",
    title="Execute disc command from workspace control block",
    description="""\
Execute a disc command using the control block at &1015.
Generates a BRK error if the command fails.
""")

subroutine(0x895E, "advance_dir_entry_ptr",
    title="Advance to next matching directory entry",
    description="""\
Advance (&B6) by 26 bytes to the next directory entry,
then check whether it matches the current search pattern.
""",
    on_exit={"a": "corrupted (Z set if match, (&B6) points to entry)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x931B, "print_hex_byte",
    title="Print a byte as two hex digits",
    description="""\
Print the value in A as two hexadecimal ASCII digits
via OSWRCH, high nibble first.
""",
    on_entry={"a": "byte value to print as hex"})

subroutine(0x832B, "generate_disc_error",
    title="Generate disc error with state recovery",
    description="""\
Save the current drive state, reload FSM and directory,
then generate a BRK error. The inline error number and
message string follow the JSR instruction.
""")

subroutine(0x8FEA, "validate_fsm_checksums",
    title="Validate FSM entry structure and checksums",
    description="""\
Validate the in-memory free space map by checking entry
structure (via validate_fsm_entries) and recalculating
both sector checksums (via calc_fsm_checksums). Raises
a Bad FS map error if entries are malformed or checksums
do not match. Called as a guard before operations that
modify the FSM or directory.
""")

subroutine(0x8BC8, "not_found_error",
    title="Generate Not found error",
    description="""\
Check for special directory characters in path and
generate either Bad name or Not found error.
""")

subroutine(0x89D0, "get_object_type_result",
    title="Load object type and save workspace",
    description="""\
Load object type from workspace and fall through to
save_wksp_and_return.
""",
    on_exit={"a": "object type (0=not found, 1=file, 2=directory)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8A3D, "multi_sector_disc_command",
    title="Execute multi-sector disc command",
    description="""\
Set up sector count and execute a disc read or write
command. Rounds up partial counts for writes. Generates
BRK on error.
""",
    on_exit={"a": "0 on success (Z set)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8BB3, "search_for_file",
    title="Search for non-directory file",
    description="""\
Parse a filename and search the current directory for
a matching non-directory entry.
""",
    on_exit={"a": "corrupted (Z set if found, (&B6) points to entry)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8D10, "check_file_not_open",
    title="Check file is not locked or open",
    description="""\
Check the entry at (&B6) for the locked attribute and
generate a Locked error if set. Then check whether any
files on the current drive are open.
""")

subroutine(0x8632, "allocate_disc_space",
    title="Allocate disc space from free space map",
    description="""\
Find the best-fit free entry for the requested size at
&103D-&103F. Generates Disc full or Compaction required
errors if allocation is not possible.
""")

subroutine(0x84A0, "osbyte_y_ff_x_00",
    title="Call OSBYTE to read current value",
    description="""\
Call OSBYTE with Y=&FF and X=0 to read the current
value of the variable specified in A.
""",
    on_entry={"a": "OSBYTE number"},
    on_exit={"a": "corrupted", "x": "OSBYTE result low byte", "y": "OSBYTE result high byte"})

subroutine(0x8F4C, "validate_not_locked",
    title="Validate file is not locked then create entry",
    description="""\
Check file is not locked or open, write the filename
into the directory entry, allocate disc space, and copy
the file length and sector address.
""")

subroutine(0x8708, "advance_text_ptr",
    title="Advance text pointer by one character",
    description="""\
Increment the 16-bit text pointer at (&B4) by one,
handling page crossing.
""")

subroutine(0x870F, "parse_and_setup_search",
    title="Parse argument and set up directory search",
    description="""\
Skip leading spaces, set up directory search state,
and clear the search result workspace. Falls through
to check_char_is_terminator.
""",
    on_exit={"a": "first non-space character (Z set if terminator)",
             "x": "0 if terminator, else preserved",
             "y": "0"})

subroutine(0x8822, "parse_drive_from_ascii",
    title="Parse drive number from ASCII character",
    description="""\
Convert ASCII drive character ('0'-'7' or 'A'-'H')
to a 3-bit drive ID in bits 5-7 of A. Limits to
drives 0-3 if no hard drive present.
""",
    on_entry={"a": "ASCII drive character ('0'-'7' or 'A'-'H')"},
    on_exit={"a": "drive ID (bits 5-7)",
             "x": "preserved", "y": "preserved"})

subroutine(0x884C, "parse_filename_from_cmdline",
    title="Parse filename from command line",
    description="""\
Parse a filename from (&B4) including drive specifier,
root, and parent directory references.
""",
    on_exit={"a": "corrupted (Z set if found, (&B6) points to entry)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8905, "save_text_ptr_after_match",
    title="Save text pointer and determine object type",
    description="""\
After a directory entry match, save the remaining text
position and determine whether the entry is a file
(type 1) or directory (type 2).
""")

subroutine(0x8CC9, "parse_osfile_and_search",
    title="Parse filename from OSFILE block and search",
    description="""\
Extract filename from the OSFILE control block, parse
the path, and search the current directory.
""",
    on_exit={"a": "corrupted (Z set if found, (&B6) points to entry)",
             "x": "corrupted", "y": "corrupted"})

subroutine(0x8D6E, "set_up_directory_search",
    title="Validate path and check for wildcards",
    description="""\
Scan the filename at (&B4) checking for invalid
characters and wildcards. Generates Bad name or
Wild cards errors for invalid patterns.
""")

subroutine(0x8E8B, "copy_entry_from_template",
    title="Copy OSFILE template into directory entry",
    description="""\
Copy filename, attributes, and sector information from
the OSFILE workspace into the directory entry at (&B6).
""")

subroutine(0x92C4, "print_via_osasci",
    title="Print character preserving registers",
    description="""\
Write A via OSASCI while preserving A, X, and (&B6).
Used during catalogue printing.
""",
    on_entry={"a": "character to print via OSASCI"},
    on_exit={"a": "preserved", "x": "preserved", "y": "corrupted"})

subroutine(0x92DE, "print_entry_name_and_access",
    title="Print entry name and access string",
    description="""\
Print the 10-character padded filename from (&B6) via
print_padded_name, followed by the access attribute
string. Scans name bytes 4 down to 0, testing bit 7 of
each to determine which attributes are set. Uses Y as the
index into both the entry and tbl_access_chars ("RWLDE"),
so byte 0 maps to 'R', byte 1 to 'W', etc. X counts set
attributes (starting at 3) to pad unset ones with spaces,
producing a fixed-width "DLW " or "  WR" style field.
Followed by the sequence number in parentheses.
""")

subroutine(0x932A, "verify_dir_and_list",
    title="Verify directory and print catalogue header",
    description="""\
Verify directory integrity then print directory title,
sequence number, drive number, and name as the header
for a catalogue listing.
""")

subroutine(0x93C5, "print_catalogue_header",
    title="Point (&B6) to first directory entry",
    description="""\
Set zp_entry_ptr (&B6) to &1205, the address of the first
26-byte directory entry in the directory buffer. Directory
entries are stored in case-insensitive ascending
alphabetical order starting at this address. A zero first
byte marks the end of the entry list. Maximum 47 entries
(47 x 26 = 1222 bytes from &1205 to &16B0).

Despite its name, this subroutine does not print anything.
The label reflects its position in the code, immediately
following the catalogue header printing code which falls
through to it.
""")

subroutine(0x947F, "parse_path_and_load",
    title="Parse path and load target directory",
    description="""\
Parse a full pathname and load the target directory
into the buffer. Handles drive specifiers, root,
parent, and current directory references.
""")

subroutine(0x94CC, "dummy_root_dir_entry",
    title="Dummy directory entry for root directory '$'",
    description="""\
A synthetic 26-byte directory entry representing the root
directory. Used when '$' is referenced directly to avoid
loading the root directory just to read its metadata.
The entry has name '$' (padded with CR), access R/L/D
(read, locked, directory), load/exec &00000000, length
&00000500 (5 sectors), start sector 2.
""")

subroutine(0x8E6F, "allocate_disc_space_for_file",
    title="Allocate disc space and store in entry",
    description="""\
Allocate disc space from the FSM for the requested
file size, then store the allocated sector address
in the directory entry at (&B6).
""")

subroutine(0x8DD6, "check_path_terminator",
    title="Check next path character is terminator",
    description="""\
Read the character at (&B4),Y and generate a Bad name
error if it is not a filename terminator.
""")

subroutine(0xB85B, "output_byte_to_buffer",
    title="Output byte to Tube or host buffer",
    description="""\
Write byte in A to the OSGBPB output destination. If Tube
is active, sends via Tube R3; otherwise stores via
(zp_mem_ptr) indirect and advances the byte counter.
""",
    on_entry={"a": "byte to output"},
    on_exit={"a": "preserved", "x": "preserved", "y": "preserved"})

subroutine(0xB579, "convert_drive_to_slot",
    title="Convert drive number to slot index",
    description="""\
Shift drive number in A right 4 bits to produce a slot
index in X.
""",
    on_entry={"a": "drive number (bits 5-7)"},
    on_exit={"a": "corrupted", "x": "slot index (drive >> 4)",
             "y": "preserved"})

subroutine(0xABD8, "find_buffer_for_sector",
    title="Find or allocate a buffer for a sector",
    description="""\
Scan channel buffer table for a buffer matching the target
sector. If not found, evict the oldest buffer for reuse.
""",
    on_entry={"a": "buffer mode (&40=read, &C0=write)"},
    on_exit={"a": "corrupted",
             "x": "buffer table offset for slot",
             "y": "corrupted"})

subroutine(0xB47C, "check_disc_changed",
    title="Check for disc change via disc ID comparison",
    description="""\
Cache the current disc ID from the FSM into per-drive
workspace, read the system clock for timing, then re-read
the disc ID and compare with the cached values. If either
byte differs, raise a "Disc changed" error. Entry point
when no channels are open on the drive; when channels are
open, entry is via read_clock_then_verify_disc_id instead.
""")

subroutine(0xB4BF, "read_clock_for_timing",
    title="Read system clock for disc-change timing",
    description="""\
Read the 5-byte system clock via OSWORD 1 and compute the
elapsed time since the previous reading. If more than 1
centisecond has elapsed, set the disc-probably-changed flag
to trigger a disc ID comparison on the next check.
""")

subroutine(0xB4F5, "check_drive_and_reload_fsm",
    title="Check disc changed and reload FSM if needed",
    description="""\
Read the system clock for disc-change timing, then check
whether the current drive's disc has changed since last
access. If changed, reload the FSM from disc.
""")

subroutine(0xBD2B, "clear_transfer_complete",
    title="Clear floppy transfer complete flag",
    description="""\
Clear bit 0 of the floppy transfer state byte.
""")

subroutine(0xA29B, "bad_compact_error",
    title="Raise Bad compact error",
    description="""\
Reload FSM and directory then raise error &94: Bad compact.
""")

subroutine(0xB18C, "sync_ext_to_ptr",
    title="Synchronise EXT to PTR if at EOF",
    description="""\
If the EOF flag is set, copy PTR to EXT. Then recalculate
channel flags from the writable and open bits.
""")

subroutine(0xA72B, "store_wksp_checksum_ba_y",
    title="Calculate and store workspace checksum",
    description="""\
Calculate workspace checksum and store at (zp_wksp_ptr)+&FE.
""")

subroutine(0xA7A2, "load_dir_for_drive",
    title="Restore workspace and load directory",
    description="""\
Restore workspace from saved copy, then load the current
directory from disc for the active drive.
""")

subroutine(0xACD7, "calc_buffer_page_from_offset",
    title="Calculate buffer page from channel offset",
    description="""\
Divide the channel offset by 4 and add the buffer base
page (&17) to compute the buffer memory page.
""")

subroutine(0x8C62, "search_dir_for_file",
    title="Search directory for matching file",
    description="""\
Copy catalogue data from the entry at (zp_entry_ptr) to
workspace and the OSFILE control block, then extract the
R/W/L access attributes from bit 7 of name bytes 0-2
into a standard OSFILE access byte (L0WRL0WR format).
Search the current directory for a matching filename.
""")

subroutine(0x8609, "sum_free_space",
    title="Sum all free space in FSM",
    description="""\
Walk the FSM entries accumulating the 3-byte length of
each free extent into workspace &105D-&105F.
""")

subroutine(0x8A45, "check_disc_command_type",
    title="Check command type and adjust sector count",
    description="""\
For write commands with partial transfers, round up the
sector count. For reads, skip the adjustment.
""")

subroutine(0xA365, "parse_second_filename",
    title="Parse second filename from command line",
    description="""\
Skip past the first filename, save the text pointer, then
parse the second filename for commands like *RENAME and
*COPY. Raises Bad command if extra arguments follow.
""")

subroutine(0xB51C, "set_drive_from_channel",
    title="Set current drive from channel's drive",
    description="""\
Extract drive bits from A, check disc-change timing, and
reload the FSM if the drive's disc has changed.
""")

subroutine(0xAAA6, "validate_and_set_ptr",
    title="Flush buffers and set file pointer",
    description="""\
Scan the ensure table for entries matching the current
channel and flush any dirty buffers before updating PTR.
""")

subroutine(0xA97C, "flush_all_channels",
    title="Flush all open channel buffers",
    description="""\
Iterate all channel entries, flushing dirty buffers to disc
and clearing state flags. Used by OSARGS A=&FF.
""")

subroutine(0x927B, "setup_help_param_ptr",
    title="Set up pointer to *HELP parameter format string",
    description="""\
Point (zp_entry_ptr) to a pathname format string in ROM
and prepare to print up to 12 characters.
""",
    on_entry={"a": "index into tbl_help_param_ptrs"},
    on_exit={"a": "corrupted", "x": "zero", "y": "corrupted"})

subroutine(0x9287, "print_padded_name",
    title="Print padded entry name from (&B6)",
    description="""\
Print up to X characters of the entry name at (&B6).
Each byte has bit 7 stripped with AND #&7F before use.
Any character below space (&20) — typically CR (&0D) in
unused name positions — ends the name; remaining columns
are padded with spaces to produce fixed-width output.
""",
    on_entry={"x": "maximum number of characters to print"},
    on_exit={"a": "corrupted", "x": "zero", "y": "corrupted"})

subroutine(0xB825, "setup_osgbpb_output_buffer",
    title="Set up OSGBPB output buffer",
    description="""\
Configure the output buffer for OSGBPB A=5-8. Claims the
Tube if the target address is in second processor memory.
""")

subroutine(0x94FA, "conditional_info_display",
    title="Display file info if *OPT1 verbose",
    description="""\
Check *OPT1 verbose flag. If set, print full catalogue
info for the current directory entry.
""")

subroutine(0xB980, "transfer_sector_bytes",
    title="Transfer sector bytes between buffer and memory",
    description="""\
Copy bytes from position l10b6 to l10b7 within the
current sector buffer, routing through direct memory,
indirect via (zp_buf_dest), or the Tube.
""")

subroutine(0xBAC6, "setup_fdc_and_seek",
    title="Set up FDC registers and seek to track",
    description="""\
Write track and sector to the WD1770 registers with
readback verify, then seek to the target track.
""")

subroutine(0x828B, "exec_disc_command",
    title="Execute disc command and check for error",
    description="""\
Execute disc command via command_exec_xy. On error,
generate a BRK (never returns). On success, restore
saved drive and return.
""",
    on_entry={"x": "control block address low byte",
              "y": "control block address high byte"})

subroutine(0xB510, "get_drive_bit_mask",
    title="Get bit mask for drive slot",
    description="""\
Build a bit mask by rotating based on the drive slot
index, then AND with drive-change flags.
""",
    on_exit={"a": "bit mask ANDed with wksp_drive_change_mask",
             "x": "corrupted", "y": "preserved"})

subroutine(0xB872, "output_dir_entry_name",
    title="Output 10-byte directory entry name",
    description="""\
Write name length byte then 10 characters from
(zp_text_ptr), replacing control chars with spaces.
""")

subroutine(0xADC5, "switch_to_channel_drive",
    title="Switch to channel's drive for I/O",
    description="""\
Save CSD sector and current drive, then switch to the
drive associated with the current channel.
""")

subroutine(0x9128, "check_and_delete_found",
    title="Validate and delete a directory entry",
    description="""\
Check file is not open, verify locked attribute, for
directories confirm empty, then proceed with deletion.
""")

subroutine(0xB060, "update_ext_from_new_ptr",
    title="Update EXT from new PTR value",
    description="""\
Copy 4-byte PTR from workspace to the channel's EXT,
then save workspace and restore drive state.
""")

subroutine(0xB123, "increment_ptr_after_write",
    title="Increment PTR after byte write",
    description="""\
Increment the channel's 4-byte PTR. On page boundaries,
save workspace and propagate carry through mid/high bytes.
""")

subroutine(0xB24D, "next_conflict_check",
    title="Continue open-channel conflict scan",
    description="""\
Advance to next channel and continue scanning for files
that conflict with the file being opened.
""")

subroutine(0xBCFD, "select_fdc_rw_command",
    title="Select and issue FDC read/write command",
    description="""\
Choose WD1770 read (&80) or write (&A0) command based
on transfer direction. Apply head load delay and step
rate, then issue the command.
""")

subroutine(0x97A8, "format_init_dir",
    title="Initialise directory structure for format",
    description="""\
Set up source and destination sector addresses for
directory initialisation during a disc format operation.
""")

subroutine(0xA7C0, "setup_disc_read_for_dir",
    title="Set up disc read for directory load",
    description="""\
Copy a disc operation template to the workspace and set
up the sector address for reading a directory from disc.
""")

subroutine(0xBB92, "claim_nmi_and_init",
    title="Claim NMI and initialise floppy transfer",
    description="""\
Claim the NMI vector via service call 12, set FDC step
rate, clear error flags, and copy the NMI handler code
into NMI workspace.
""")

subroutine(0xBD38, "clear_seek_flag",
    title="Clear floppy seek-in-progress flag",
    description="""\
Clear bit 1 of the floppy transfer state byte.
""")

subroutine(0x8CC3, "check_existing_for_save",
    title="Check for existing file before save",
    description="""\
Search directory using wildcards for an existing entry
matching the save filename.
""")

subroutine(0x905C, "calc_fsm_checksums",
    title="Calculate FSM sector checksums",
    description="""\
Compute 8-bit checksums of FSM sectors 0 and 1 by
summing all 255 bytes of each sector.
""",
    on_exit={"a": "FSM sector 1 checksum",
             "x": "FSM sector 0 checksum", "y": "corrupted"})

subroutine(0x9071, "disc_op_tpl_write_fsm",
    title="Write-FSM disc operation template",
    description="""\
Disc operation template for writing both FSM sectors (0 and
1) from the FSM buffer at &0E00 back to disc. Used by
write_dir_and_validate via exec_disc_command with X=&71,
Y=&90 pointing to this template.
""")

subroutine(0x907C, "osfile_write_load_addr",
    title="OSFILE write catalogue info handler",
    description="""\
Handle OSFILE A=1 (write all catalogue info), A=2 (write
load address) and A=3 (write execution address). Finds the
file, validates access, then updates the directory entry
fields from the OSFILE parameter block.
""")

subroutine(0x90CF, "set_entry_access_from_osfile",
    title="Write access attributes to directory entry name bytes",
    description="""\
Apply access bits from the OSFILE parameter block (offset
&0E) to bit 7 of directory entry name bytes 0-2. Each
name byte's lower 7 bits (the character) are preserved;
only bit 7 is replaced.

The OSFILE access byte layout is L0WRL0WR:
  bit 0: R (owner read)    bit 4: R (public read)
  bit 1: W (owner write)   bit 5: W (public write)
  bit 3: L (owner locked)  bit 7: L (public locked)
  bits 2,6: unused

For files (byte 3 bit 7 clear), the owner bits are used
directly: bit 0 (R) to byte 0, bit 1 (W) to byte 1,
bit 3 (L) to byte 2 (bit 2 is skipped via the loop
re-entry at apply_access_bits_loop).

For directories (byte 3 bit 7 set), two extra LSRs skip
the owner R and W bits, so only the L bit (bit 3) is
applied to byte 2. Bytes 0 and 1 are left unchanged.
""")

subroutine(0x9945, "clear_rwl_attributes",
    title="Clear R, W, L attribute bits in entry",
    description="""\
Strip bit 7 from the first three name bytes of the
directory entry at (zp_entry_ptr).
""")

subroutine(0x9DDA, "print_help_command_list",
    title="Print *HELP ADFS command list",
    description="""\
Print the ADFS command list for *HELP output, formatting
each command name with padding.
""")

subroutine(0xA35A, "combine_hex_digit_pair",
    title="Combine two hex nibbles into a byte",
    description="""\
Take high nibble from workspace, shift left 4, and
OR with low nibble to produce a combined byte.
""",
    on_entry={"x": "offset into wksp_disc_op_result (0 or 2)"},
    on_exit={"a": "combined byte value",
             "x": "preserved", "y": "preserved"})

subroutine(0xA016, "print_space",
    title="Print a space character",
    description="""\
Print a single space (&20) via OSWRCH.
""")

subroutine(0x8D69, "no_open_files_on_drive",
    title="No open file conflict found",
    description="""\
All channels checked with no conflicts. Continue with
the file operation.
""")

subroutine(0xA749, "save_workspace_state",
    title="Save all registers and workspace",
    description="""\
Save registers, validate workspace checksum, check FSM
integrity, and store workspace with updated checksum.
""")

subroutine(0x8DDE, "wild_cards_error",
    title="Raise Wild cards error",
    description="""\
Reload FSM and directory then raise error &FD: Wild cards.
""")

subroutine(0xA6F9, "broken_directory_error",
    title="Raise Broken directory error",
    description="""\
Generate disc error with state recovery, then raise
error &A8: Broken directory.
""")

subroutine(0x8FFA, "bad_fs_map_error",
    title="Raise Bad FS map error",
    description="""\
Generate a Bad FS map error (&A9) via generate_disc_error.
Called when FSM checksum validation fails.
""")

subroutine(0xBAF4, "retry_after_error",
    title="Set up track for floppy retry",
    description="""\
After a floppy error, set up the track for a retry
attempt by copying target sector to current track.
""")

subroutine(0xBB82, "set_read_transfer_mode",
    title="Set read mode and initialise floppy",
    description="""\
Set bit 7 of transfer mode for read, get step rate,
claim NMI, and set up the track.
""")

subroutine(0x9D11, "service4_decline",
    title="Decline service 4 and pass on",
    description="""\
Clean up stack and return A=4 to pass the unrecognised
command to the next ROM in the service chain.
""")

subroutine(0x856B, "add_size_to_existing_entry",
    title="Add released size to FSM entry",
    description="""\
Copy the object sector address and add the released
block size to an existing FSM length entry, merging
adjacent free regions.
""",
    on_entry={"x": "FSM entry index into sector 0/1 buffers"},
    on_exit={"a": "corrupted", "x": "corrupted", "y": "3"})

subroutine(0x85C1, "insert_new_entry",
    title="Insert new entry into FSM",
    description="""\
Check for room in the FSM. If full, raise Map full error.
Otherwise shift entries up and insert the new entry at
the correct sorted position.
""",
    on_entry={"note": "zp_mem_ptr_lo = insertion point index in FSM"},
    on_exit={"a": "corrupted", "x": "corrupted", "y": "corrupted"})

subroutine(0x8A63, "exec_disc_transfer_batched",
    title="Execute disc transfer in batches",
    description="""\
For transfers exceeding 255 sectors, loop with full
batches. For the final batch, use the remaining count.
""")

subroutine(0x8798, "check_both_exhausted",
    title="Check pattern and name both exhausted",
    description="""\
After pattern ends, check whether the entry name has
also ended. Returns Z set if the match succeeds.
""")

subroutine(0x87A8, "begin_star_match",
    title="Begin wildcard '*' matching",
    description="""\
Skip past '*' in pattern and try matching the rest
against each successive position in the entry name.
""")

subroutine(0x87CB, "star_match_succeeded",
    title="Return successful wildcard match",
    description="""\
Set A=0 and carry to signal a successful match.
""")

subroutine(0x87CF, "check_name_ended",
    title="Check name ended during '*' match",
    description="""\
After name is exhausted, check whether remaining pattern
is only terminators. Returns Z set if match succeeds.
""")

subroutine(0x87E7, "parse_pathname_entry",
    title="Linear scan of sorted directory for matching entry",
    description="""\
Skip leading spaces, point (&B6) to the first directory
entry, verify directory integrity, then perform a linear
scan through entries comparing each against the filename
pattern.

Directory entries are stored in case-insensitive ascending
alphabetical order. The scan exploits this invariant: if
compare_filename returns with carry clear (pattern sorts
before the current entry name), the target cannot exist
later in the directory and the search terminates early.

On return, (&B6) points to the matched entry (Z=1) or to
the first entry that sorts after the pattern (Z=0). This
position is used by the sorted-insertion code at
check_name_already_exists to maintain directory order when
creating new entries.
""",
    on_exit={"a": "corrupted (Z set if match found)",
             "x": "corrupted", "y": "match length if found"})

subroutine(0x8849, "bad_drive_name",
    title="Raise Bad name error for invalid drive",
    description="""\
Jump to bad name error handler for an invalid drive
specifier character.
""")

subroutine(0x9951, "set_file_attributes",
    title="Set file attributes from access string",
    description="""\
Clear existing R, W, L attributes then parse the access
string to set appropriate flags including E and D.
""")

subroutine(0x9AE6, "adfs_hardware_found",
    title="Claim workspace for ADFS",
    description="""\
Return A=1 to claim one workspace page and set Y=&1C
to raise PAGE to &1D00 for ADFS workspace.
""")

subroutine(0xAB63, "scsi_write_page",
    title="Write 256 bytes to SCSI bus",
    description="""\
Transfer a page from (zp_buf_src) to the SCSI data
register, then set the ensuring flag.
""")

subroutine(0xAC62, "read_single_hd_sector",
    title="Read a single sector via SCSI",
    description="""\
Issue a single-sector read command and transfer 256
bytes from the SCSI data register into the buffer.
""")

subroutine(0xACE9, "step_ensure_offset_loop",
    title="Step through ensure table entries",
    description="""\
Step backward through the ensure table checking for
entries associated with the current channel.
""")

subroutine(0xAD53, "eof_error",
    title="Raise EOF error",
    description="""\
Clear EOF and buffer flags then raise error &DF: EOF.
""")

subroutine(0xAD8D, "calc_bget_sector_addr",
    title="Calculate sector address for BGET",
    description="""\
Compute disc sector from channel base + PTR, load the
sector into the buffer, and set up the byte offset.
""")

subroutine(0xAE4C, "advance_to_next_dir_entry",
    title="Advance directory scan pointer",
    description="""\
Add 26 bytes to the directory entry pointer to move to
the next entry, handling page crossing.
""")

subroutine(0xAEBC, "update_ext_to_ptr",
    title="Handle PTR exceeding EXT",
    description="""\
If PTR has exceeded the file allocation, begin file
extension. Otherwise jump to EOF write handler.
""")

subroutine(0xB3F1, "update_dir_entry_on_close",
    title="Update directory entry on file close",
    description="""\
Switch to the file's drive, calculate actual sectors
used from EXT, then release unused allocation back to
the free space map.
""")

# ---------------------------------------------------------------------------
# Inline error number bytes
# These equb values are BRK error codes in inline error blocks:
#   JSR error_routine / error_number / "message" / &00
# ---------------------------------------------------------------------------

comment(0x82B1, "Error &11: Escape", inline=True)
comment(0x82C0, "Error &CD: Drive not ready", inline=True)
comment(0x82DC, "Error &C7: Disc error", inline=True)
comment(0x82EB, "Error &C9: Disc protected", inline=True)
comment(0x85CB, "Error &99: Map full", inline=True)
comment(0x8659, "Error &C6: Disc full", inline=True)
comment(0x8667, "Error &98: Compaction required", inline=True)
comment(0x873A, "Error &CC: Bad name", inline=True)
comment(0x8985, "Error &B0: Bad rename", inline=True)
comment(0x8BDA, "Error &D6: Not found", inline=True)
comment(0x8BF3, "Error &BD: Access violation", inline=True)
comment(0x8D19, "Error &C3: Locked", inline=True)
comment(0x8D56, "Error &C2: Already open", inline=True)
comment(0x8DE1, "Error &FD: Wild cards", inline=True)
comment(0x8E21, "Error &B3: Dir full", inline=True)
comment(0x8FFD, "Error &A9: Bad FS map", inline=True)
comment(0x915F, "Error &B4: Dir not empty", inline=True)
comment(0x91B0, "Error &96: Cant delete CSD", inline=True)
comment(0x91DA, "Error &97: Cant delete library", inline=True)
comment(0x95A7, "Error &C4: Already exists", inline=True)
comment(0x99DD, "Error &92: Aborted", inline=True)
comment(0xA00D, "Error &CB: Bad opt", inline=True)
comment(0xA29E, "Error &94: Bad compact", inline=True)
comment(0xA38C, "Error &FE: Bad command", inline=True)
comment(0xA3FA, "Error &93: Wont", inline=True)
comment(0xA6D0, "Error &A9: Bad FS map", inline=True)
comment(0xA6FC, "Error &A8: Broken directory", inline=True)
comment(0xA740, "Error &AA: Bad checksum", inline=True)
comment(0xAA38, "Error &B7: Outside file", inline=True)
comment(0xABB5, "Error &CA: Data lost", inline=True)
comment(0xACEC, "Error &DE: Channel", inline=True)
comment(0xAD5E, "Error &DF: EOF", inline=True)
comment(0xB0A0, "Error &C1: Not open for update", inline=True)
comment(0xB1EE, "Error &C0: Too many open", inline=True)
comment(0xB4B1, "Error &C8: Disc changed", inline=True)

# ---------------------------------------------------------------------------
# Interstitial data blocks: these are data areas between routines that
# need visual separation to avoid appearing as part of adjacent code.
# ---------------------------------------------------------------------------

subroutine(0x841C, "str_at",
    title="Error suffix string constants",
    description="""\
Reversed string constants used when building error messages.
str_at contains ': ta ' (reversed ' at :') appended to disc
error messages, and str_on_channel contains ' lennahc no '
(reversed ' on channel') for channel-specific errors.
""")

subroutine(0x8499, "str_exec_abbrev",
    title="OSCLI abbreviation strings",
    description="""\
CR-terminated command abbreviation strings passed to OSCLI:
str_exec_abbrev = 'E.' (*EXEC), str_spool_abbrev = 'SP.'
(*SPOOL). Also includes str_yes (reversed 'YES' + CR for
*DESTROY confirmation) and str_hugo (NUL + 'Hugo' directory
identity string).
""")

subroutine(0x880C, "disc_op_tpl_read_fsm",
    title="Disc operation templates for FSM and directory reads",
    description="""\
Two overlapping disc operation control block templates that
share common fields. The templates are copied to workspace
&1014-&101F before issuing disc read commands.

disc_op_tpl_read_fsm (&880C, 10 bytes via l8816+offset):
  Read 2 sectors from sector 0 into &0E00 (FSM buffer).
  Used to reload the free space map from disc.

disc_op_tpl_read_dir (&8817, 11 bytes):
  Read 5 sectors from sector 2 into &1200 (directory buffer).
  Used to load a directory from disc.

The templates overlap at &8817-&881B, sharing the result
byte (&01), host memory marker (&FFFF), and read command
(&08). The zero byte at l8816 (&8816) provides padding
when copying starts from &1014 instead of &1015.
""")

subroutine(0x9269, "osfile_dispatch_lo",
    title="OSFILE dispatch table",
    description="""\
RTS-trick dispatch table for OSFILE functions 0-7. Low
bytes at &9269, high bytes at &926A, interleaved as pairs.
Functions: 0=save, 1=write cat info, 2=write load addr,
3=write exec addr, 4=write attrs, 5=read cat info,
6=delete, 7=create.
""")

subroutine(0x9316, "tbl_access_chars",
    title="Access attribute character table",
    description="""\
Five-character table 'RWLDE' used to look up and display
file access attributes. Indexed by attribute bit position.
""")

subroutine(0x9A46, "default_workspace_data",
    title="Default workspace initialisation template",
    description="""\
29-byte template copied to workspace page &1100 during hard
break initialisation (service call 2). Bytes beyond &1C are
zeroed. Sets both CSD and library to the root directory '$'
on drive 0, sector 2.

+00  wksp_csd_name (10 bytes): '$' + 9 spaces
+0A  wksp_lib_name (10 bytes): '$' + 9 spaces
+14  wksp_csd_sector (3 bytes): sector 2 (root directory)
+17  wksp_current_drive: drive 0
+18  wksp_lib_sector (3 bytes): sector 2 (root directory)
+1B  wksp_lib_drive: drive 0
+1C  wksp_prev_dir_sector low: sector 2
""")

subroutine(0x9A78, "boot_option_addr_table",
    title="Boot option OSCLI address table and command strings",
    description="""\
Three-byte lookup table of OSCLI string low addresses, indexed
by boot option number (1-3). The high byte is always &9A.
The auto-boot code reads fsm_s1_boot_option and uses it as
an index into this table to select the OSCLI command.

  Option 1 (Load): &7B -> "L.$.!BOOT" at &9A7B
  Option 2 (Run):  &7D -> "$.!BOOT" at &9A7D (*RUN)
  Option 3 (Exec): &85 -> "E.$.!BOOT" at &9A85

Option 2 cleverly points into the middle of the "L.$.!BOOT"
string to get just "$.!BOOT", which OSCLI interprets as
*RUN $.!BOOT.
""")

subroutine(0x9A8F, "service_dispatch_lo",
    title="Service call dispatch table",
    description="""\
RTS-trick dispatch table for MOS service calls 0-9.
Low bytes at &9A8F, high bytes at &9A99, 10 entries.
""")

subroutine(0x9CB3, "tbl_fs_vectors",
    title="Filing system vector addresses",
    description="""\
Seven 2-byte vector addresses copied to the MOS vector table
at &0212-&021F when ADFS is selected. All point into the
extended vector jump block at &FFxx, which dispatches through
tbl_extended_vectors to reach the actual ADFS handler routines.

  FILEV  &FF1B  OSFILE handler
  ARGSV  &FF1E  OSARGS handler
  BGETV  &FF21  OSBGET handler
  BPUTV  &FF24  OSBPUT handler
  GBPBV  &FF27  OSGBPB handler
  FINDV  &FF2A  OSFIND handler
  FSCV   &FF2D  Filing system control handler
""")

subroutine(0x9CC1, "tbl_extended_vectors",
    title="Extended vector table",
    description="""\
Seven 3-byte extended vector entries for the filing system
API. Each entry is: handler address low, handler address
high, ROM number (&FF, patched to actual ROM number when
installed). Copied to the MOS extended vector area when
ADFS is selected as the current filing system.

  FILEV  &923E  osfile_handler
  ARGSV  &A955  osargs_handler
  BGETV  &AD63  osbget_handler
  BPUTV  &B08F  osbput_handler
  GBPBV  &B57F  osgbpb_handler
  FINDV  &B1B6  osfind_handler
  FSCV   &9E50  fscv_handler
""")

subroutine(0x9CD6, "str_filing_system_name",
    title="Filing system name string",
    description="""\
The string 'adfs' (reversed for stack-based comparison)
used to identify the filing system during service call
handling.
""")

subroutine(0x9E48, "tbl_help_param_ptrs",
    title="*HELP parameter format string pointer table",
    description="""\
Eight low-byte pointers into the &9Fxx page, indexing the
parameter format strings displayed after each command name
in the *HELP ADFS output. Each command's third table byte
packs two nibble indices: the high nibble selects the first
parameter string, the low nibble selects the second. For
example, *ACCESS has byte &16 meaning index 1 then index 6,
producing "ACCESS <List Spec> (L)(W)(R)(E)" in the listing.

  0: (none)         4: (<Drive>)
  1: <List Spec>    5: <SP> <LP>
  2: <Ob Spec>      6: (L)(W)(R)(E)
  3: <*Ob Spec*>    7: <Title>
""")

subroutine(0x9E6D, "fscv_dispatch_lo",
    title="FSCV dispatch table",
    description="""\
RTS-trick dispatch table for filing system control calls
0-8. Low bytes at &9E6D, high bytes at &9E76, 9 entries.
FSC 0=*OPT, 1=check EOF, 2=*/, 3=*command, 4=*RUN,
5=*CAT, 6=new FS, 7=handle range, 8=*command (OS 1.20).
""")

subroutine(0x9EE3, "tbl_commands",
    title="Star command name and dispatch table",
    description="""\
Table of ADFS star command names with dispatch addresses.
Each entry is: command name bytes (bit 7 set on last),
dispatch address high byte, dispatch address low byte,
parameter count nibbles.

Dispatch uses the RTS trick: the high and low bytes are
pushed onto the stack, then RTS pops and adds 1 to form
the target address. The stored address is therefore the
handler address minus one.
""")

subroutine(0x9F8D, "help_param_list_spec",
    title="*HELP parameter format strings",
    description="""\
Seven NUL-terminated strings displayed after command names in
the *HELP ADFS listing. Indexed via tbl_help_param_ptrs using
nibble pairs from each command's parameter byte. Index 0 points
to the NUL at &9FD7 (end of the last string), producing no
output for commands with no parameters.

  1: "<List Spec>"     Wildcard file specification
  2: "<Ob Spec>"       Single object specification
  3: "<*Ob Spec*>"     Optional wildcard specification
  4: "(<Drive>)"       Optional drive number
  5: "<SP> <LP>"       Start page and length page
  6: "(L)(W)(R)(E)"    Access attribute flags
  7: "<Title>"         Directory title string
""")

subroutine(0x9FD8, "fsc7_read_handle_range",
    title="FSC 7: return ADFS file handle range",
    description="""\
Return the range of file handles used by ADFS. The MOS calls
FSC 7 to determine which handles belong to the current filing
system. ADFS uses handles &30-&39 (ASCII '0'-'9', 10 channels).
""",
    on_exit={"a": "corrupted",
             "x": "&30 (lowest handle, ASCII '0')",
             "y": "&39 (highest handle, ASCII '9')"})

subroutine(0x9FDD, "fsc0_star_opt",
    title="FSC 0: *OPT command handler",
    description="""\
Handle the *OPT command. *OPT 1,N controls verbose mode
(bit 2 of zp_adfs_flags). *OPT 4,N sets the disc boot
option in the free space map.
""",
    on_entry={"x": "first *OPT parameter (option number)",
              "y": "second *OPT parameter (value)"})

subroutine(0xBC79, "nmi_handler_rom",
    title="NMI handler code (copied to &0D00)",
    at_binary_addr=True,
    description="""\
NMI handler for floppy disc byte-by-byte data transfer.
Copied from ROM to the NMI workspace at &0D00 before each
floppy operation. The WD1770 fires an NMI on each byte
transferred (DRQ) and on command completion.

The handler has three paths:
  1. DRQ (status & &1F = 3): transfer one byte between
     the WD1770 data register and memory. The code at
     &0D0A-&0D17 is patched with one of three variants:
     nmi_write_code (direct memory write to disc),
     nmi_tube_write_code (Tube to disc), or
     nmi_tube_read_code (disc to Tube). The default
     (nmi_code_rw) is direct memory read from disc.
  2. Error (status & &58 != 0): store the error status
     and set bit 0 of zp_floppy_control and
     zp_floppy_state to signal the error to the caller.
  3. Completion (no DRQ, no error): if multi-sector mode
     is active (bit 6 of zp_floppy_state), switch to
     ROM 0 and call the track-stepping routine to set up
     the next sector. Otherwise mark transfer complete.
""")

subroutine(0x0D1A, "nmi_check_status_error",
    title="NMI status/error handler",
    move_id=nmi_main_move_id,
    description="""\
Not a DRQ: check WD1770 status for error bits. Bits 6
(write protect), 4 (record not found), and 3 (CRC error)
are tested via AND #&58. If any are set, store the error
code and set the error flag in the control byte.
""")

subroutine(0x0D2C, "nmi_check_end_of_operation",
    title="NMI end-of-operation handler",
    move_id=nmi_main_move_id,
    description="""\
No error and no DRQ: the WD1770 command has completed.
If multi-sector mode (bit 6 of zp_floppy_state) is not
active, just mark the transfer complete. Otherwise, save
the current ROM state, switch to ROM 0, and call the
track-stepping routine to prepare the next sector for
transfer.
""")

subroutine(0xBCDF, "nmi_write_code",
    title="NMI patch: write memory to disc",
    at_binary_addr=True,
    description="""\
Patched into &0D0A when writing to floppy disc from host
memory. Reads a byte from the self-modifying transfer
address and writes it to the WD1770 data register.
""")

subroutine(0xBCED, "nmi_tube_write_code",
    title="NMI patch: write Tube to disc",
    at_binary_addr=True,
    description="""\
Patched into &0D0A when writing to floppy disc via the
Tube. Reads a byte from Tube data register 3 and writes
it to the WD1770 data register.
""")

subroutine(0xBCF5, "nmi_tube_read_code",
    title="NMI patch: read disc to Tube",
    at_binary_addr=True,
    description="""\
Patched into &0D0A when reading from floppy disc via the
Tube. Reads a byte from the WD1770 data register and
writes it to Tube data register 3.
""")

subroutine(0xBFF6, "str_rom_footer",
    title="ROM footer text",
    description="""\
The text 'and Hugo.' followed by CR. This fills the last
10 bytes of the ROM, a credit to Hugo Tyson who wrote
ADFS. The 'Hugo' string also serves as the 4-byte magic
number at both ends of every ADFS directory structure.
""")

subroutine(0x8DED, "tbl_forbidden_chars",
    title="Forbidden filename characters",
    description="""\
Six characters that may not appear in ADFS filenames because
they have special meaning in the pathname syntax. The path
validator at set_up_directory_search loops through this table,
rejecting any filename containing these characters.
""")

subroutine(0x8DF3, "copy_addrs_and_find_empty_entry",
    title="Copy OSFILE addresses and search for empty entry",
    description="""\
Copy the load and exec addresses from the OSFILE control
block into the disc operation workspace, then search the
current directory for an empty entry slot to use for a
new file. Called when creating files via OSFILE save,
*CDIR, *RENAME, and *COPY.
""")

subroutine(0x8E2B, "check_name_already_exists",
    title="Insert new entry at sorted position in directory",
    description="""\
Insert a new directory entry at the position indicated by
zp_entry_ptr, which was set by parse_pathname_entry to
the first entry that sorts after the new name. Shifts all
entries from the end of the directory (&16B1) backwards
to zp_entry_ptr up by 26 bytes to open a gap, then
returns with zp_text_ptr restored to the saved command
text position. The caller then fills in the gap with the
new entry's data.

This maintains the ascending alphabetical order invariant
that the directory search at begin_dir_entry_search
depends on for its sorted early-exit optimisation.
""")

subroutine(0x8C05, "osfile_save_check_existing",
    title="OSFILE A=0: check for existing file before save",
    description="""\
Entry point for OSFILE save (A=0), reached via RTS-trick
dispatch from osfile_handler. Searches the current directory for
an existing file with the same name, checking it is not a
directory and has the correct access attributes.

On entry:
  (&B4) points to filename, (&B8) to OSFILE control block
On exit:
  Falls through to osfile_save_handler if file is valid
""")

# Inline comments for osfile_save_check_existing
comment(0x8C05, "Search for matching non-directory file", inline=True)
comment(0x8C08, "Not found: report Not found error", inline=True)
comment(0x8C0A, "Y=0: check first entry name byte", inline=True)
comment(0x8C0C, "Get first byte of found entry", inline=True)
comment(0x8C0E, "Bit 7 clear: no read access, error", inline=True)

# ---------------------------------------------------------------------------
# Generate disassembly
# ---------------------------------------------------------------------------

import json

output = go(print_output=False)

_output_dirpath.mkdir(parents=True, exist_ok=True)
output_filepath = _output_dirpath / "adfs-1.30.asm"
output_filepath.write_text(output)
print(f"Wrote {output_filepath}", file=sys.stderr)

structured = get_structured()
json_filepath = _output_dirpath / "adfs-1.30.json"
json_filepath.write_text(json.dumps(structured))
print(f"Wrote {json_filepath}", file=sys.stderr)
