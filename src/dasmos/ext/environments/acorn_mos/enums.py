"""OS-call enum tables.

Each enum maps the value passed in the appropriate register
(typically A) when calling the corresponding MOS routine, to the
canonical symbolic name py8dis-fork uses (e.g.
``osbyte_read_buffer = &91``). The hook system uses these to
register a :meth:`Disassembler.constant` and an auto-expression at
the operand byte of the preceding ``LDA #imm`` so the rendered
disassembly reads as ``lda #osbyte_read_buffer`` instead of
``lda #&91``.

Vendored verbatim from py8dis-fork's ``acorn.py``. Update those
tables (re-vendor) when py8dis adds new entries.
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
# OSBYTE &99 (insert into input buffer) is DELIBERATELY OMITTED:
# py8dis-fork's osbyte_hook for &99 uses an inline comment
# (``Insert character Y into keyboard buffer``) instead of a
# symbolic-name substitution, since the choice is binary in practice
# (&00 keyboard / &01 RS423) and reads more naturally as a comment.
OSBYTE_X_SECONDARY_ENUMS: dict[int, dict[int, str]] = {
    0x0d: EVENT_ENUM,   # Disable event X
    0x0e: EVENT_ENUM,   # Enable event X
    0x15: BUFFER_ENUM,  # Flush specific buffer X
    0x8a: BUFFER_ENUM,  # Insert into buffer X
    0x91: BUFFER_ENUM,  # Read from buffer X
    0x98: BUFFER_ENUM,  # Examine buffer X
}
