"""OS-call enum tables.

Each enum maps the value passed in the appropriate register
(typically A) when calling the corresponding MOS routine, to a
canonical symbolic name (e.g. ``osbyte_read_buffer = &91``). The
hook system uses these to register a :meth:`Disassembler.constant`
and an auto-expression at the operand byte of the preceding
``LDA #imm`` so the rendered disassembly reads as
``lda #osbyte_read_buffer`` instead of ``lda #&91``.
"""

from __future__ import annotations


OSBYTE_ENUM: dict[int, str] = {
    0x00: "osbyte_read_os_version",
    0x01: "osbyte_set_user_flag",
    0x02: "osbyte_select_input_stream",
    0x03: "osbyte_select_output_stream",
    0x04: "osbyte_set_cursor_editing",
    0x05: "osbyte_select_printer",
    0x06: "osbyte_set_printer_ignore",
    0x07: "osbyte_set_serial_receive_rate",
    0x08: "osbyte_set_serial_transmit_rate",
    0x09: "osbyte_set_flashing_mark",
    0x0a: "osbyte_set_flashing_space",
    0x0b: "osbyte_set_keyboard_repeat_delay",
    0x0c: "osbyte_set_keyboard_repeat_rate",
    0x0d: "osbyte_disable_event",
    0x0e: "osbyte_enable_event",
    0x0f: "osbyte_flush_buffer_class",
    0x10: "osbyte_select_adc_channels",
    0x11: "osbyte_force_adc_conversion",
    0x12: "osbyte_reset_soft_keys",
    0x13: "osbyte_vsync",
    0x14: "osbyte_explode_chars",
    0x15: "osbyte_flush_buffer",
    0x16: "osbyte_increment_polling_semaphore",
    0x17: "osbyte_decrement_polling_semaphore",
    0x18: "osbyte_electron_external_sound",
    0x19: "osbyte_restore_group_of_font_definitions",
    0x44: "osbyte_test_for_sideways_ram",
    0x45: "osbyte_get_sideways_ram_allocation",
    0x6B: "osbyte_selects_internal_or_external_bus",
    0x6C: "osbyte_select_screen_memory_for_direct_access",
    0x6d: "osbyte_make_temporary_filing_system_permanent",
    0x70: "osbyte_select_main_or_shadow_memory_for_vdu_access",
    0x71: "osbyte_select_main_or_shadow_memory_for_display",
    0x72: "osbyte_write_shadow_memory_use",
    0x73: "osbyte_blank_or_restore_palette",
    0x74: "osbyte_reset_electron_sound_system",
    0x75: "osbyte_read_vdu_status",
    0x76: "osbyte_reflect_keyboard_status_in_leds",
    0x77: "osbyte_close_spool_exec",
    0x78: "osbyte_write_keys_pressed",
    0x79: "osbyte_scan_keyboard",
    0x7a: "osbyte_scan_keyboard_from_16",
    0x7b: "osbyte_printer_driver_going_dormant",
    0x7c: "osbyte_clear_escape",
    0x7d: "osbyte_set_escape",
    0x7e: "osbyte_acknowledge_escape",
    0x7f: "osbyte_check_eof",
    0x80: "osbyte_read_adc_or_get_buffer_status",
    0x81: "osbyte_inkey",
    0x82: "osbyte_read_high_order_address",
    0x83: "osbyte_read_oshwm",
    0x84: "osbyte_read_himem",
    0x85: "osbyte_read_himem_for_mode",
    0x86: "osbyte_read_text_cursor_pos",
    0x87: "osbyte_read_char_at_cursor",
    0x88: "osbyte_code",
    0x89: "osbyte_motor",
    0x8a: "osbyte_insert_buffer",
    0x8b: "osbyte_opt",
    0x8c: "osbyte_tape",
    0x8d: "osbyte_rom",
    0x8e: "osbyte_enter_language",
    0x8f: "osbyte_issue_service_request",
    0x90: "osbyte_tv",
    0x91: "osbyte_read_buffer",
    0x92: "osbyte_read_fred",
    0x93: "osbyte_write_fred",
    0x94: "osbyte_read_jim",
    0x95: "osbyte_write_jim",
    0x96: "osbyte_read_sheila",
    0x97: "osbyte_write_sheila",
    0x98: "osbyte_examine_buffer",
    0x99: "osbyte_insert_input_buffer",
    0x9a: "osbyte_write_video_ula_control",
    0x9b: "osbyte_write_video_ula_palette",
    0x9c: "osbyte_read_write_6850_control",
    0x9d: "osbyte_fast_tube_bput",
    0x9e: "osbyte_read_speech",
    0x9f: "osbyte_write_speech",
    0xa0: "osbyte_read_vdu_variable",
    0xa1: "osbyte_read_cmos_ram",
    0xa2: "osbyte_write_cmos_ram",
    0xa3: "osbyte_reserved_for_application_software",
    0xa4: "osbyte_check_for_6502_code",
    0xa5: "osbyte_read_output_cursor_position",
    0xa6: "osbyte_read_os_variables_low",
    0xa7: "osbyte_read_os_variables_high",
    0xa8: "osbyte_read_rom_ptr_table_low",
    0xa9: "osbyte_read_rom_ptr_table_high",
    0xaa: "osbyte_read_rom_info_table_low",
    0xab: "osbyte_read_rom_info_table_high",
    0xac: "osbyte_read_key_table_low",
    0xad: "osbyte_read_key_table_high",
    0xae: "osbyte_read_vdu_variables_low",
    0xaf: "osbyte_read_vdu_variables_high",
    0xb0: "osbyte_read_write_cfs_timeout",
    0xb1: "osbyte_read_write_input_source",
    0xb2: "osbyte_read_write_keyboard_semaphore",
    0xb3: "osbyte_read_write_primary_oshwm",
    0xb4: "osbyte_read_write_current_oshwm",
    0xb5: "osbyte_read_write_serial_mode",
    0xb6: "osbyte_read_char_explode_state",
    0xb7: "osbyte_read_write_cfs_rfs_switch",
    0xb8: "osbyte_read_video_ula_control",
    0xb9: "osbyte_read_video_ula_palette",
    0xba: "osbyte_read_write_rom_bank_at_last_brk",
    0xbb: "osbyte_read_write_basic_rom_bank",
    0xbc: "osbyte_read_current_adc_channel",
    0xbd: "osbyte_read_write_max_adc_channel",
    0xbe: "osbyte_read_write_adc_conversion_type",
    0xbf: "osbyte_read_write_serial_user_flag",
    0xc0: "osbyte_read_serial_control_register_copy",
    0xc1: "osbyte_read_write_flash_counter",
    0xc2: "osbyte_read_write_mark_count",
    0xc3: "osbyte_read_write_space_count",
    0xc4: "osbyte_read_write_keyboard_repeat_delay",
    0xc5: "osbyte_read_write_keyboard_repeat_rate",
    0xc6: "osbyte_read_write_exec_file_handle",
    0xc7: "osbyte_read_write_spool_file_handle",
    0xc8: "osbyte_read_write_escape_break_effect",
    0xc9: "osbyte_read_write_econet_keyboard_disable",
    0xca: "osbyte_read_write_keyboard_status",
    0xcb: "osbyte_read_write_serial_handshake_extent",
    0xcc: "osbyte_read_write_serial_input_suppression",
    0xcd: "osbyte_read_write_cassette_serial_selection",
    0xce: "osbyte_read_write_econet_os_call_interception",
    0xcf: "osbyte_read_write_econet_osrdch_interception",
    0xd0: "osbyte_read_write_econet_oswrch_interception",
    0xd1: "osbyte_read_write_speech_suppression",
    0xd2: "osbyte_read_write_sound_suppression",
    0xd3: "osbyte_read_write_bell_channel",
    0xd4: "osbyte_read_write_bell_envelope",
    0xd5: "osbyte_read_write_bell_frequency",
    0xd6: "osbyte_read_write_bell_duration",
    0xd7: "osbyte_read_write_startup_boot_options",
    0xd8: "osbyte_read_write_soft_key_length",
    0xd9: "osbyte_read_write_lines_since_last_page",
    0xda: "osbyte_read_write_vdu_queue_size",
    0xdb: "osbyte_read_write_tab_char",
    0xdc: "osbyte_read_write_escape_char",
    0xdd: "osbyte_read_write_characters_c0_cf_status",
    0xde: "osbyte_read_write_characters_d0_df_status",
    0xdf: "osbyte_read_write_characters_e0_ef_status",
    0xe0: "osbyte_read_write_characters_f0_ff_status",
    0xe1: "osbyte_read_write_function_key_status",
    0xe2: "osbyte_read_write_shift_function_key_status",
    0xe3: "osbyte_read_write_ctrl_function_key_status",
    0xe4: "osbyte_read_write_ctrl_shift_function_key_status",
    0xe5: "osbyte_read_write_escape_status",
    0xe6: "osbyte_read_write_escape_effects",
    0xe7: "osbyte_read_write_user_via_irq_mask",
    0xe8: "osbyte_read_write_6850_irq_mark",
    0xe9: "osbyte_read_write_system_via_irq_mask",
    0xea: "osbyte_read_tube_presence",
    0xeb: "osbyte_read_speech_processor_presence",
    0xec: "osbyte_read_write_char_destination_status",
    0xed: "osbyte_read_write_cursor_editing_status",
    0xee: "osbyte_read_write_27e",
    0xef: "osbyte_read_write_27f",
    0xf0: "osbyte_read_write_280",
    0xf1: "osbyte_read_write_281",
    0xf2: "osbyte_read_serial_ula",
    0xf3: "osbyte_read_write_timer_switch_state",
    0xf4: "osbyte_read_write_soft_key_consistency_flag",
    0xf5: "osbyte_read_write_printer_destination",
    0xf6: "osbyte_read_write_printer_ignore_char",
    0xf7: "osbyte_read_write_first_byte_break_intercept",
    0xf8: "osbyte_read_write_second_byte_break_intercept",
    0xf9: "osbyte_read_write_third_byte_break_intercept",
    0xfa: "osbyte_read_write_28a",
    0xfb: "osbyte_read_write_28b",
    0xfc: "osbyte_read_write_current_language_rom_bank",
    0xfd: "osbyte_read_write_last_break_type",
    0xfe: "osbyte_read_write_available_ram",
    0xff: "osbyte_read_write_startup_options",
}


OSWORD_ENUM: dict[int, str] = {
    0x00: "osword_read_line",
    0x01: "osword_read_clock",
    0x02: "osword_write_clock",
    0x03: "osword_read_interval_timer",
    0x04: "osword_write_interval_timer",
    0x05: "osword_read_io_memory",
    0x06: "osword_write_io_memory",
    0x07: "osword_sound",
    0x08: "osword_envelope",
    0x09: "osword_read_pixel",
    0x0a: "osword_read_char",
    0x0b: "osword_read_palette",
    0x0c: "osword_write_palette",
    0x0d: "osword_read_graphics_cursor_position",
    0x0e: "osword_read_cmos_clock",
    0x0f: "osword_write_cmos_clock",
    # Extra OSWORDs — see https://beebwiki.mdfs.net/OSWORDs
    0x10: "osword_network_transmit",
    0x11: "osword_network_receive",
    0x12: "osword_nfs_read_args",
    0x13: "osword_nfs_info",
    0x14: "osword_nfs_misc",
    0x15: "osword_mouse_pointer_info",
    0x16: "osword_screen_base_start",
}


OSFIND_ENUM: dict[int, str] = {
    0x00: "osfind_close",
    0x40: "osfind_open_input",
    0x80: "osfind_open_output",
    0xc0: "osfind_open_random_access",
}


OSFILE_ENUM: dict[int, str] = {
    0x00: "osfile_save",
    0x01: "osfile_write_catalogue_info",
    0x02: "osfile_write_load_addr",
    0x03: "osfile_write_exec_addr",
    0x04: "osfile_write_attributes",
    0x05: "osfile_read_catalogue_info",
    0x06: "osfile_delete",
    0x07: "osfile_create",
    0xff: "osfile_load",
}


OSGBPB_ENUM: dict[int, str] = {
    0x01: "osgbpb_write_bytes",
    0x02: "osgbpb_append_bytes",
    0x03: "osgbpb_read_bytes_from_position",
    0x04: "osgbpb_read_bytes_from_current_position",
    0x05: "osgbpb_read_title_option_and_drive",
    0x06: "osgbpb_read_current_directory",
    0x07: "osgbpb_read_current_library",
    0x08: "osgbpb_read_file_names",
}


# INKEY scan-code enum, keyed by the unsigned-byte form an OSBYTE
# &79 / &81 caller actually loads into X.
#
# Origin: Acorn's INKEY table maps each physical key to a small
# negative number (-1 = SHIFT, -2 = CTRL, -17 = Q, …). To scan for
# that key with OSBYTE &79 (scan keyboard) or &81 (INKEY), the caller
# loads X with the byte value ``(-key_number) EOR 128``, equivalently
# ``(key_number AND &FF) EOR 128`` — the formula that fits a
# negative number into an unsigned byte and signals "negative scan"
# by the high bit.
#
# Storing the enum keyed by the unsigned byte (the value the
# disassembler actually sees in ``LDX #imm``) lets the analyser do
# a single dict lookup instead of computing the inverse arithmetic
# on every call. The reverse — ``key_code = 255 - (byte_value EOR
# 128)`` — is folded into the dict via ``{k & 0xff: v for k, v in
# raw}``.
INKEY_ENUM: dict[int, str] = {
    (k & 0xff): v
    for k, v in {
        -1:   "inkey_key_shift",
        -2:   "inkey_key_ctrl",
        -17:  "inkey_key_q",
        -18:  "inkey_key_3",
        -19:  "inkey_key_4",
        -20:  "inkey_key_5",
        -21:  "inkey_key_f4",
        -22:  "inkey_key_8",
        -23:  "inkey_key_f7",
        -24:  "inkey_key_minus",
        -25:  "inkey_key_caret",
        -26:  "inkey_key_left",
        -27:  "inkey_key_keypad_6",
        -28:  "inkey_key_keypad_7",
        -33:  "inkey_key_f0",
        -34:  "inkey_key_w",
        -35:  "inkey_key_e",
        -36:  "inkey_key_t",
        -37:  "inkey_key_7",
        -38:  "inkey_key_i",
        -39:  "inkey_key_9",
        -40:  "inkey_key_0",
        -41:  "inkey_key_underscore",
        -42:  "inkey_key_down",
        -43:  "inkey_key_keypad_8",
        -44:  "inkey_key_keypad_9",
        -49:  "inkey_key_1",
        -50:  "inkey_key_2",
        -51:  "inkey_key_d",
        -52:  "inkey_key_r",
        -53:  "inkey_key_6",
        -54:  "inkey_key_u",
        -55:  "inkey_key_o",
        -56:  "inkey_key_p",
        -57:  "inkey_key_left_square_bracket",
        -58:  "inkey_key_up",
        -59:  "inkey_key_keypad_plus",
        -60:  "inkey_key_keypad_minus",
        -61:  "inkey_key_keypad_enter",
        -65:  "inkey_key_caps_lock",
        -66:  "inkey_key_a",
        -67:  "inkey_key_x",
        -68:  "inkey_key_f",
        -69:  "inkey_key_y",
        -70:  "inkey_key_j",
        -71:  "inkey_key_k",
        -72:  "inkey_key_at",
        -73:  "inkey_key_colon",
        -74:  "inkey_key_return",
        -75:  "inkey_key_keypad_slash",
        -76:  "inkey_key_keypad_del",
        -77:  "inkey_key_keypad_full_stop",
        -81:  "inkey_key_shift_lock",
        -82:  "inkey_key_s",
        -83:  "inkey_key_c",
        -84:  "inkey_key_g",
        -85:  "inkey_key_h",
        -86:  "inkey_key_n",
        -87:  "inkey_key_l",
        -88:  "inkey_key_semicolon",
        -89:  "inkey_key_right_square_bracket",
        -90:  "inkey_key_delete",
        -91:  "inkey_key_keypad_hash",
        -92:  "inkey_key_keypad_asterisk",
        -93:  "inkey_key_keypad_comma",
        -97:  "inkey_key_tab",
        -98:  "inkey_key_z",
        -99:  "inkey_key_space",
        -100: "inkey_key_v",
        -101: "inkey_key_b",
        -102: "inkey_key_m",
        -103: "inkey_key_comma",
        -104: "inkey_key_full_stop",
        -105: "inkey_key_slash",
        -106: "inkey_key_copy",
        -107: "inkey_key_keypad_0",
        -108: "inkey_key_keypad_1",
        -109: "inkey_key_keypad_3",
        -113: "inkey_key_escape",
        -114: "inkey_key_f1",
        -115: "inkey_key_f2",
        -116: "inkey_key_f3",
        -117: "inkey_key_f5",
        -118: "inkey_key_f6",
        -119: "inkey_key_f8",
        -120: "inkey_key_f9",
        -121: "inkey_key_backslash",
        -122: "inkey_key_right",
        -123: "inkey_key_keypad_4",
        -124: "inkey_key_keypad_5",
        -125: "inkey_key_keypad_2",
    }.items()
}


# Buffer-number enum: passed in X to OSBYTE actions that target a
# specific buffer (flush / insert / examine / read).
BUFFER_ENUM: dict[int, str] = {
    0: "buffer_keyboard",
    1: "buffer_rs423_input",
    2: "buffer_rs423_output",
    3: "buffer_printer",
    4: "buffer_sound_channel_0",
    5: "buffer_sound_channel_1",
    6: "buffer_sound_channel_2",
    7: "buffer_sound_channel_3",
    8: "buffer_speech",
}


# Event-number enum: passed in Y to OSEVEN, or in X to OSBYTE
# actions that enable/disable specific events.
EVENT_ENUM: dict[int, str] = {
    0: "event_output_buffer_empty",
    1: "event_input_buffer_full",
    2: "event_character_entering_input_buffer",
    3: "event_adc_conversion_complete",
    4: "event_start_of_vertical_sync",
    5: "event_interval_timer_crossing_zero",
    6: "event_escape_condition_detected",
    7: "event_rs423_error",
    8: "event_network_error",
    9: "event_user",
}


# OSBYTE actions whose X register carries a SECONDARY enum value.
# Built into the osbyte analyzer so that ``LDA #&15 ; LDX #&03 ;
# JSR osbyte`` registers BOTH ``osbyte_flush_buffer`` (for A) AND
# ``buffer_printer`` (for X). Format: action_byte → enum dict.
#
# OSBYTE &99 (insert into input buffer) is DELIBERATELY OMITTED: the
# choice is binary in practice (&00 keyboard / &01 RS423) and reads
# more naturally as an inline comment (``Insert character Y into
# keyboard buffer``) than as a symbolic-name substitution.
OSBYTE_X_SECONDARY_ENUMS: dict[int, dict[int, str]] = {
    0x0d: EVENT_ENUM,   # Disable event X
    0x0e: EVENT_ENUM,   # Enable event X
    0x15: BUFFER_ENUM,  # Flush specific buffer X
    0x8a: BUFFER_ENUM,  # Insert into buffer X
    0x91: BUFFER_ENUM,  # Read from buffer X
    0x98: BUFFER_ENUM,  # Examine buffer X
}


# Long descriptive inline-comment text per OSBYTE call number. Ported
# from the py8dis-fork ``acorn.osbyte_action()`` if/elif chain into a
# pure data table — easier to scan, easier to test, and more amenable
# to per-X-value extension (planned for the per-call analyser bucket).
#
# When an entry is present, the inline-comment generator uses it
# verbatim; otherwise it falls back to a mechanical
# ``osbyte: <name-stripped>`` form. Drivers that override the inline
# comment with ``d.comment(addr, …, align=Align.INLINE)`` always win
# over either of these.
OSBYTE_DESCRIPTIONS: dict[int, str] = {
    0x00: "Read OS version (returns A=0)",
    0x01: "Set user flag",
    0x02: "Select input stream",
    0x03: "Select output stream",
    0x04: "Set cursor editing keys",
    0x05: "Select printer destination",
    0x06: "Set ignore character for printer",
    0x07: "Set serial baud receive rate",
    0x08: "Set serial baud transmit rate",
    0x09: "Set duration of first colour for flashing colours",
    0x0a: "Set duration of second colour for flashing colours",
    0x0b: "Set keyboard auto-repeat delay",
    0x0c: "Set keyboard auto-repeat rate",
    0x0d: "Disable event",
    0x0e: "Enable event",
    0x0f: "Flush selected class of buffer",
    0x10: "Select ADC channels",
    0x11: "Force ADC conversion on channel X",
    0x12: "Reset function keys",
    0x13: "Wait for vertical sync",
    0x14: "Implode or Explode character definition RAM based on X",
    0x15: "Flush specific buffer X",
    0x16: "Electron and Master: Increment polling semaphore",
    0x17: "Electron and Master: Decrement polling semaphore",
    0x18: "Electron: External sound (with parameter X)",
    0x19: "Master only: Restore a group of default font definitions based on X",
    0x44: "Master and B+ only: Test for sideways RAM",
    0x45: "Master and B+ only: Get sideways RAM allocation",
    0x6b: "Master, Compact and Electron: Select internal or external bus",
    0x6c: "Select screen memory for direct CPU access",
    0x6d: "Make temporary filing system permanent",
    0x70: "Master only: Select main or shadow memory for VDU access",
    0x71: "Master only: Select main or shadow memory for display",
    0x72: "Master only: Read/write current shadow memory in use",
    0x73: "Master only: Blank or restore palette",
    0x74: "Electron only: Reset Plus 1 sound system",
    0x75: "Read VDU status",
    0x76: "Reflect keyboard status in keyboard LEDs",
    0x77: "Close any SPOOLed or EXECed files",
    0x78: "Write all keys pressed information",
    0x79: "Scan keyboard from keynumber X",
    0x7a: "Scan keyboard from key 16",
    0x7b: "Inform OS that printer driver is going dormant",
    0x7c: "Clear escape condition (no further escape effects)",
    0x7d: "Set escape condition",
    0x7e: "Clear escape condition and perform escape effects",
    0x7f: "Check for end-of-file on file handle Y",
    0x80: "Read ADC channel X or buffer status",
    0x81: "INKEY: Scan for a key with positive X, or read internal "
          "key number EOR 128 for negative X",
    0x82: "Read high-order address (machine high word)",
    0x83: "Read top of operating system RAM address (OSHWM)",
    0x84: "Read top of available user RAM (HIMEM)",
    0x85: "Read top of user RAM for given screen mode",
    0x86: "Read input cursor position (Sets X=POS and Y=VPOS)",
    0x87: "Read character at text cursor position and current screen MODE",
    0x88: "*CODE: pass control to user routine via USERV",
    0x89: "Set or read motor state and CFS speed",
    0x8a: "Insert character Y into buffer X",
    0x8b: "*OPT: set filing system options",
    0x8c: "*TAPE: select cassette filing system",
    0x8d: "*ROM: select paged ROM filing system",
    0x8e: "Enter language ROM in ROM bank X",
    0x8f: "Issue paged ROM service call, Reason X",
    0x90: "*TV: set vertical screen shift and interlace state",
    0x91: "Read character from buffer X",
    0x92: "Read byte from FRED (&FCxx)",
    0x93: "Write byte to FRED (&FCxx)",
    0x94: "Read byte from JIM (&FDxx)",
    0x95: "Write byte to JIM (&FDxx)",
    0x96: "Read byte from SHEILA (&FExx)",
    0x97: "Write byte to SHEILA (&FExx)",
    0x98: "Examine buffer X (without removing the byte)",
    0x99: "Insert byte Y into input buffer X",
    0x9a: "Write to Video ULA control register and copy at &248",
    0x9b: "Write to Video ULA palette register and copy at &249",
    0x9c: "Read/write 6850 ACIA control register",
    0x9d: "Fast Tube BPUT",
    0x9e: "Read from speech processor",
    0x9f: "Write to speech processor",
    0xa0: "Read VDU variable",
    0xa1: "Read CMOS RAM/EEPROM byte (Master and B+) or Tube ID (Compact)",
    0xa2: "Write CMOS RAM byte",
    0xa3: "Reserved for application software",
    0xa4: "Check for 6502 second processor presence",
    0xa5: "Read output cursor position",
    0xa6: "Read low byte of address of OS variables table",
    0xa7: "Read high byte of address of OS variables table",
    0xa8: "Read low byte of ROM pointer table address",
    0xa9: "Read high byte of ROM pointer table address",
    0xaa: "Read low byte of ROM information table address",
    0xab: "Read high byte of ROM information table address",
    0xac: "Read low byte of key translation table address",
    0xad: "Read high byte of key translation table address",
    0xae: "Read low byte of VDU variables table address",
    0xaf: "Read high byte of VDU variables table address",
    0xea: "Read tube presence flag",
    0xeb: "Read speech processor presence flag",
    0xf4: "Read/Write soft-key consistency flag",
    0xfd: "Read/Write last break type",
}


# Per-X-value description specialising the OSBYTE base description
# above. When the analyser sees ``LDA #A_value ; LDX #X_value ; JSR
# osbyte`` and both A and X are tracked, it prefers the more-
# specific text from this table. Falls back to the base description
# when X is unknown or no X-specific row applies.
#
# Design improvement over py8dis: py8dis keeps these in a 1500-line
# imperative if/elif chain (``if x == 0: com = "Implode…" elif x ==
# 1: com = "Explode 1 page…"``) — dasmos pulls the same content into
# a pure data table that's easy to scan, easy to test, and
# directly reusable for the optional Markdown-summary banner the
# analyser can emit alongside the inline comment.
OSBYTE_X_VALUE_DESCRIPTIONS: dict[int, dict[int, str]] = {
    # OSBYTE &00: Read OS version into X (X=0 = read; X=anything else
    # is reserved). py8dis describes the version-id layout as if X
    # were the *result* — these strings appear in py8dis's reference
    # for the post-call X = OS-version mapping. dasmos uses them as
    # POST-CALL descriptions instead (see OSBYTE_POST_CALL_DESCRIPTIONS),
    # but keep the table here too in case some driver pre-loads X
    # to a documented value.
    0x00: {
        0: "X=0, OS 1.00 (Early BBC B or Electron OS 1.00)",
        1: "X=1, OS 1.20 or American OS",
        2: "X=2, OS 0.10",
        3: "X=3, OS 3.2/3.5 (Master 128)",
        4: "X=4, OS 4.0 (Master Econet Terminal)",
        5: "X=5, OS 3.20 (Master Compact)",
    },

    # OSBYTE &14: Implode/Explode character definition RAM.
    0x14: {
        0: "Implode character definition RAM, can redefine characters 128-159 (X=0)",
        1: "Explode character definition RAM (one extra page), can redefine characters 128-191 (X=1)",
        2: "Explode character definition RAM (two extra pages), can redefine characters 128-223 (X=2)",
        3: "Explode character definition RAM (three extra pages), can redefine characters 128-255 (X=3)",
        4: "Explode character definition RAM (four extra pages), can redefine characters 128-255 and 32-63 (X=4)",
        5: "Explode character definition RAM (five extra pages), can redefine characters 128-255 and 32-95 (X=5)",
        6: "Explode character definition RAM (six extra pages), can redefine all characters 32-255 (X=6)",
    },

    # OSBYTE &8B: *OPT — set filing-system options. X selects an
    # OPT category (0..3 traditional, 4 = boot mode for ADFS, etc.).
    # Most ROMs use literal *OPT, but the OSBYTE form appears in
    # filing-system code.
    0x8b: {
        0: "*OPT 0 — disable messages",
        1: "*OPT 1 — short messages",
        2: "*OPT 2 — long messages",
        3: "*OPT 3 — load options",
        4: "*OPT 4 — boot option (DFS/ADFS)",
    },

    # OSBYTE &8d: *ROM — select paged-ROM filing system as A. py8dis
    # describes filing-system numbers via the post-call X-value
    # mapping; same texts used here when the driver pre-loads A.
}


# After-call descriptions: these get attached as inline comments to
# the FIRST instruction after the JSR/JMP that reads X, Y, or A —
# not to the call site itself. py8dis tracks "next use" via its CPU
# state pass and attaches there; dasmos does the same via the
# post-trace state tracker (``previous_load_imm_addr`` already
# records source-of-value provenance, and the analyser can scan
# forward from the JSR's binary address until the trace's classified
# opcodes show a read of the named register).
#
# Each entry maps OSBYTE call number → register letter ("a"/"x"/"y")
# → description string. Multiple registers per call are common
# (OSBYTE &86 returns POS in X *and* VPOS in Y).
OSBYTE_POST_CALL_DESCRIPTIONS_INLINE_PLACEHOLDER = None  # see comment below


# Post-call value-tables: when an OS call returns a register holding
# a value from a known (small) enum, emit a multi-line standalone
# comment at the byte after the call listing every possible value.
# The next-use site usually consumes the register, so the table
# sits right above the consumer.
#
# Format: OSBYTE# → register letter ("a"/"x"/"y") → (intro, {value: description}).
#
# Rendered as a Markdown table preceded by the intro phrase. The
# JSON renderer keeps the source markdown verbatim (consumed by the
# site generator); the asm renderer flattens to a pipe-table layout
# via mistletoe — both downstream forms surface the per-value
# description text, recovering the words py8dis emits in the same
# spot.
#
# Design improvement over py8dis: py8dis emits these as raw
# multi-line strings (tabular by indentation). Encoding as
# structured (intro, {value: desc}) data lets dasmos render them as
# Markdown tables that downstream consumers can format
# appropriately — and lets future analysers reuse the same data
# tables without reparsing free-text.
OSBYTE_POST_CALL_TABLES: dict[int, dict[str, tuple[str, dict[int, str]]]] = {
    # OSBYTE &00: "Read OS version number into X" (when X != 0 at
    # entry). Sets X = OS-version id.
    0x00: {
        "x": (
            "On return, X is the OS version number",
            {
                0: "OS 1.00 (Early BBC B or Electron OS 1.00)",
                1: "OS 1.20 or American OS",
                2: "OS 2.00 (BBC B+)",
                3: "OS 3.2/3.5 (Master 128)",
                4: "OS 4.0 (Master Econet Terminal)",
                5: "OS 5.0 (Master Compact)",
            },
        ),
    },
}


# OSARGS dispatches on (A, Y) jointly. Most A values further fork on
# Y == 0 vs Y != 0. Encoded as:
#   {a_value: {y_match: inline_description}}
# where y_match is either an int (specific Y) or None (any Y, used
# as the fallback when no specific Y matches).
OSARGS_INLINE: dict[int, dict[int | None, str]] = {
    0x00: {
        0: "Get filing system number (A=0, Y=0)",
        None: "Get sequential file pointer into zero page address X (A=0)",
    },
    0x01: {
        0: "Get address of remaining command line into zero page "
           "address X (A=1, Y=0)",
        None: "Write sequential file pointer from zero page address X (A=1)",
    },
    0x02: {
        None: "Get length of file into zero page address X (A=2)",
    },
    0xFF: {
        0: "Write any buffered data to all pending files (A=&FF, Y=0)",
        None: "Write any buffered data to file Y (A=&FF)",
    },
}


# OSARGS post-call value tables (parallel to OSBYTE_POST_CALL_TABLES).
# Only OSARGS A=0 Y=0 (Get filing system number) returns a
# value-table-shaped result in A.
OSARGS_POST_CALL_TABLES: dict[
    tuple[int, int | None], dict[str, tuple[str, dict[int, str]]],
] = {
    (0x00, 0x00): {
        "a": (
            "On return, A is the filing system number",
            {
                0: "no filing system selected",
                1: "1200 baud CFS",
                2: "300 baud CFS",
                3: "ROM filing system",
                4: "Disc filing system",
                5: "Network filing system",
                6: "Teletext filing system",
                7: "IEEE filing system",
                8: "ADFS",
                9: "Host filing system",
                10: "Videodisc filing system",
            },
        ),
    },
}


OSBYTE_POST_CALL_DESCRIPTIONS: dict[int, dict[str, str]] = {
    # OSBYTE &00: Read OS version. Returns X=version-id.
    0x00: {
        "x": "X is the host OS version (0=1.00, 1=1.20, 3=Master, "
             "4=Master Terminal, 5=Master Compact)",
    },

    # OSBYTE &7F: Read EOF on file handle Y. Returns X=0 (EOF) or
    # X=&FF (more data). py8dis emits a description on next-use of X.
    0x7f: {
        "x": "X=0 means EOF reached, X=&FF means data remaining",
    },

    # OSBYTE &81: INKEY scan. Returns X=ASCII (or internal key code
    # EOR 128 in negative-X mode), Y=time-out flag (0/&FF).
    0x81: {
        "x": "X=ASCII code typed (positive timeout) or "
             "internal key number EOR 128 (negative scan)",
        "y": "Y=0 if a key was pressed, Y=&FF on time-out, "
             "Y=&1B on Escape",
    },

    # OSBYTE &83: Read OSHWM. Returns X=OSHWM low, Y=OSHWM high.
    0x83: {
        "x": "X and Y contain the address of OSHWM (low, high)",
    },

    # OSBYTE &84: Read HIMEM. Returns X=HIMEM low, Y=HIMEM high.
    0x84: {
        "x": "X and Y contain the address of HIMEM (low, high)",
    },

    # OSBYTE &86: Read input cursor position. X=POS, Y=VPOS.
    0x86: {
        "x": "X is the horizontal text position ('POS')",
        "y": "Y is the vertical text position ('VPOS')",
    },

    # OSBYTE &14 (post-call): X is the new OSHWM (high byte) — a
    # side-effect of mode-page changes after explode/implode.
    0x14: {
        "x": "X is the new OSHWM (high byte)",
    },
}


# OSWORD descriptions are a clean data table in py8dis already; copy
# verbatim. The single-line text is used as the inline comment on
# ``JSR osword`` call sites when A is recognised.
OSWORD_DESCRIPTIONS: dict[int, str] = {
    0x00: "Read line from input stream (exits with C=1 if ESCAPE pressed)",
    0x01: "Read system clock",
    0x02: "Write system clock",
    0x03: "Read interval timer",
    0x04: "Write interval timer",
    0x05: "Read byte of I/O processor memory",
    0x06: "Write byte of I/O processor memory",
    0x07: "SOUND command",
    0x08: "ENVELOPE command",
    0x09: "Read pixel value",
    0x0a: "Read character definition",
    0x0b: "Read palette",
    0x0c: "Write palette",
    0x0d: "Read graphics cursor position",
    0x0e: "Read CMOS clock",
    0x0f: "Write CMOS clock",
    # Extra OSWORDs — see https://beebwiki.mdfs.net/OSWORDs
    0x10: "Network transmit",
    0x11: "Open or read network receive block",
    0x12: "Read argument block and restore protection mask NFS",
    0x13: "Read/Write NFS information (see https://beebwiki.mdfs.net/OSWORDs)",
    0x14: "Various NFS/Network functions",
    0x15: "Read/Write mouse and pointer information",
    0x16: "Set screen base start",
    0x18: "IP Network transmit",
    0x19: "IP Open or read network receive block",
}
