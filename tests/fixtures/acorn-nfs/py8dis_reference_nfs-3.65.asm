; Constants
adlc_cr1                                    = 65184
adlc_cr2                                    = 65185
adlc_tx                                     = 65186
adlc_tx2                                    = 65187
buffer_printer                              = 3
cb_fill                                     = 252
cb_skip                                     = 253
cb_stop                                     = 254
econet_nmi_enable                           = 65056
econet_station_id                           = 65048
err_fs_cutoff                               = 168
err_line_jammed                             = 160
err_net_error                               = 161
err_no_clock                                = 163
err_no_reply                                = 165
err_not_listening                           = 162
err_tx_cb_error                             = 164
event_network_error                         = 8
handle_base                                 = 32
osbyte_acknowledge_escape                   = 126
osbyte_close_spool_exec                     = 119
osbyte_explode_chars                        = 20
osbyte_insert_input_buffer                  = 153
osbyte_issue_service_request                = 143
osbyte_read_buffer                          = 145
osbyte_read_rom_ptr_table_low               = 168
osbyte_read_tube_presence                   = 234
osbyte_read_write_econet_keyboard_disable   = 201
osbyte_read_write_exec_file_handle          = 198
osbyte_read_write_last_break_type           = 253
osbyte_scan_keyboard_from_16                = 122
osbyte_write_keys_pressed                   = 120
osfind_close                                = 0
osword_read_palette                         = 11
port_command                                = 153
port_load_data                              = 146
port_printer                                = 209
port_remote                                 = 147
port_reply                                  = 144
port_save_ack                               = 145
rx_ready                                    = 127
tx_flag                                     = 128

; Memory locations
zp_ptr_lo                               = &0000
zp_ptr_hi                               = &0001
zp_work_2                               = &0002
zp_work_3                               = &0003
zp_temp_10                              = &0010
zp_temp_11                              = &0011
tube_data_ptr                           = &0012
tube_data_ptr_hi                        = &0013
tube_claim_flag                         = &0014
tube_claimed_id                         = &0015
zp_63                                   = &005f
l0063                                   = &0063
escapable                               = &0097
need_release_tube                       = &0098
prot_flags                              = &0099
net_tx_ptr                              = &009a
net_tx_ptr_hi                           = &009b
net_rx_ptr                              = &009c
net_rx_ptr_hi                           = &009d
nfs_workspace                           = &009e
nfs_workspace_hi                        = &009f
nmi_tx_block                            = &00a0
nmi_tx_block_hi                         = &00a1
port_buf_len                            = &00a2
port_buf_len_hi                         = &00a3
open_port_buf                           = &00a4
open_port_buf_hi                        = &00a5
port_ws_offset                          = &00a6
rx_buf_offset                           = &00a7
ws_page                                 = &00a8
svc_state                               = &00a9
osword_flag                             = &00aa
ws_ptr_lo                               = &00ab
ws_ptr_hi                               = &00ac
table_idx                               = &00ad
work_ae                                 = &00ae
addr_work                               = &00af
fs_load_addr                            = &00b0
fs_load_addr_hi                         = &00b1
fs_load_addr_2                          = &00b2
fs_load_addr_3                          = &00b3
fs_work_4                               = &00b4
fs_work_5                               = &00b5
fs_work_7                               = &00b7
fs_error_ptr                            = &00b8
fs_crflag                               = &00b9
fs_spool_handle                         = &00ba
fs_options                              = &00bb
fs_block_offset                         = &00bc
fs_last_byte_flag                       = &00bd
fs_crc_lo                               = &00be
fs_crc_hi                               = &00bf
txcb_ctrl                               = &00c0
txcb_port                               = &00c1
txcb_dest                               = &00c2
txcb_start                              = &00c4
txcb_pos                                = &00c7
txcb_end                                = &00c8
nfs_temp                                = &00cd
rom_svc_num                             = &00ce
fs_spool0                               = &00cf
osbyte_a_copy                           = &00ef
osword_pb_ptr                           = &00f0
osword_pb_ptr_hi                        = &00f1
os_text_ptr                             = &00f2
os_text_ptr_hi                          = &00f3
romsel_copy                             = &00f4
osrdsc_ptr                              = &00f6
osrdsc_ptr_hi                           = &00f7
brk_ptr                                 = &00fd
escape_flag                             = &00ff
error_block                             = &0100
error_text                              = &0101
stk_timeout_mid                         = &0102
stk_frame_3                             = &0103
stk_timeout_hi                          = &0104
stk_frame_p                             = &0106
tube_osword_pb                          = &0128
brkv                                    = &0202
filev                                   = &0212
fscv                                    = &021e
evntv                                   = &0220
netv                                    = &0224
vdu_screen_mode                         = &0350
vdu_colours                             = &0351
vdu_cursor_edit                         = &0355
string_buf                              = &0700
l0701                                   = &0701
nmi_code_base                           = &0cff
nmi_shim_07                             = &0d07
nmi_jmp_lo                              = &0d0c
nmi_jmp_hi                              = &0d0d
set_nmi_vector                          = &0d0e
install_nmi_handler                     = &0d11
nmi_rti                                 = &0d14
nmi_shim_1a                             = &0d1a
l0d1c                                   = &0d1c
l0d1e                                   = &0d1e
tx_dst_stn                              = &0d20
tx_dst_net                              = &0d21
tx_src_stn                              = &0d22
tx_src_net                              = &0d23
tx_ctrl_byte                            = &0d24
tx_port                                 = &0d25
tx_data_start                           = &0d26
tx_data_len                             = &0d2a
rx_status_flags                         = &0d38
tx_ctrl_status                          = &0d3a
rx_ctrl_copy                            = &0d3b
rx_src_stn                              = &0d3d
rx_src_net                              = &0d3e
rx_ctrl                                 = &0d3f
rx_port                                 = &0d40
rx_remote_addr                          = &0d41
tx_flags                                = &0d4a
nmi_next_lo                             = &0d4b
nmi_next_hi                             = &0d4c
tx_index                                = &0d4f
tx_length                               = &0d50
tx_work_51                              = &0d51
tx_in_progress                          = &0d52
tx_work_57                              = &0d57
l0d58                                   = &0d58
l0d59                                   = &0d59
scout_status                            = &0d5c
rx_extra_byte                           = &0d5d
printer_buf_ptr                         = &0d61
tx_clear_flag                           = &0d62
prot_status                             = &0d63
rx_flags                                = &0d64
saved_jsr_mask                          = &0d65
econet_init_flag                        = &0d66
tube_flag                               = &0d67
nmi_sub_table                           = &0de6
fs_state_deb                            = &0deb
rom_ws_table                            = &0df0
fs_context_base                         = &0dfe
fs_server_stn                           = &0e00
fs_server_net                           = &0e01
fs_urd_handle                           = &0e02
fs_csd_handle                           = &0e03
fs_lib_handle                           = &0e04
fs_boot_option                          = &0e05
fs_messages_flag                        = &0e06
fs_eof_flags                            = &0e07
fs_sequence_nos                         = &0e08
fs_last_error                           = &0e09
fs_cmd_context                          = &0e0a
fs_context_hi                           = &0e0b
fs_reply_status                         = &0e0d
fs_target_stn                           = &0e0e
fs_cmd_ptr                              = &0e10
fs_work_16                              = &0e16
fs_filename_buf                         = &0e30
fs_reply_data                           = &0ef7
fs_cmd_type                             = &0f00
fs_cmd_y_param                          = &0f01
fs_cmd_urd                              = &0f02
fs_cmd_csd                              = &0f03
fs_cmd_lib                              = &0f04
fs_cmd_data                             = &0f05
fs_func_code                            = &0f06
fs_data_count                           = &0f07
fs_reply_cmd                            = &0f08
fs_load_vector                          = &0f09
fs_load_upper                           = &0f0b
fs_addr_check                           = &0f0c
fs_file_len                             = &0f0d
fs_file_attrs                           = &0f0e
fs_file_len_3                           = &0f10
fs_obj_type                             = &0f11
fs_access_level                         = &0f12
fs_reply_stn                            = &0f13
fs_len_clear                            = &0f14
fs_boot_data                            = &0f16
fs_putb_buf                             = &0fdc
fs_getb_buf                             = &0fdd
fs_handle_mask                          = &0fde
fs_error_flags                          = &0fdf
fs_error_buf                            = &0fe0
l4655                                   = &4655
l7845                                   = &7845
l7dfd                                   = &7dfd
start_adlc_tx                           = &9650
init_adlc_hw                            = &9653
econet_save                             = &9656
econet_restore                          = &9659
svc5_irq_check                          = &965c
station_id_disable_net_nmis             = &fe18
video_ula_control                       = &fe20
romsel                                  = &fe30
system_via_sr                           = &fe4a
system_via_acr                          = &fe4b
system_via_ifr                          = &fe4d
system_via_ier                          = &fe4e
econet_control1_or_status1              = &fea0
econet_control23_or_status2             = &fea1
econet_data_continue_frame              = &fea2
econet_data_terminate_frame             = &fea3
tube_status_1_and_tube_control          = &fee0
tube_data_register_1                    = &fee1
tube_status_register_2                  = &fee2
tube_data_register_2                    = &fee3
tube_data_register_3                    = &fee5
tube_status_register_4_and_cpu_control  = &fee6
tube_data_register_4                    = &fee7
oseven                                  = &ffbf
gsinit                                  = &ffc2
gsread                                  = &ffc5
osfind                                  = &ffce
osgbpb                                  = &ffd1
osbput                                  = &ffd4
osbget                                  = &ffd7
osargs                                  = &ffda
osfile                                  = &ffdd
osrdch                                  = &ffe0
osasci                                  = &ffe3
osnewl                                  = &ffe7
oswrch                                  = &ffee
osword                                  = &fff1
osbyte                                  = &fff4
oscli                                   = &fff7

    org &9324

.reloc_zp_src

; Move 1: &9324 to &16 for length 65
    org &16
; ***************************************************************************************
; Tube BRK handler (BRKV target) — reference: NFS11 NEWBR
; 
; Sends error information to the Tube co-processor via R2 and R4:
;   1. Sends &FF to R4 (WRIFOR) to signal error
;   2. Reads R2 data (flush any pending byte)
;   3. Sends &00 via R2, then error number from (&FD),0
;   4. Loops sending error string bytes via R2 until zero terminator
;   5. Falls through to tube_reset_stack → tube_main_loop
; The main loop continuously polls R1 for WRCH requests (forwarded
; to OSWRITCH &FFCB) and R2 for command bytes (dispatched via the
; 12-entry table at &0500). The R2 command byte is stored at &51
; (self-modifying the JMP indirect low byte) before dispatch.
; ***************************************************************************************
; &9324 referenced 1 time by &816f
.nmi_workspace_start
.tube_brk_handler
    lda #&ff                                                          ; 9324: a9 ff       ..  :0016[1]   ; A=&FF: signal error to co-processor via R4
    jsr tube_send_r4                                                  ; 9326: 20 9e 06     .. :0018[1]   ; Send &FF error signal to Tube R4
    lda tube_data_register_2                                          ; 9329: ad e3 fe    ... :001b[1]   ; Flush any pending R2 byte
    lda #0                                                            ; 932c: a9 00       ..  :001e[1]   ; A=0: send zero prefix to R2
.tube_send_zero_r2
    jsr tube_send_r2                                                  ; 932e: 20 95 06     .. :0020[1]   ; Send zero prefix byte via R2
    tay                                                               ; 9331: a8          .   :0023[1]   ; Y=0: start of error block at (&FD)
    lda (brk_ptr),y                                                   ; 9332: b1 fd       ..  :0024[1]   ; Load error number from (&FD),0
    jsr tube_send_r2                                                  ; 9334: 20 95 06     .. :0026[1]   ; Send error number via R2
; &9337 referenced 1 time by &0030[1]
.tube_brk_send_loop
    iny                                                               ; 9337: c8          .   :0029[1]   ; Advance to next error string byte
.tube_send_error_byte
    lda (brk_ptr),y                                                   ; 9338: b1 fd       ..  :002a[1]   ; Load next error string byte
    jsr tube_send_r2                                                  ; 933a: 20 95 06     .. :002c[1]   ; Send error string byte via R2
    tax                                                               ; 933d: aa          .   :002f[1]   ; Zero byte = end of error string
    bne tube_brk_send_loop                                            ; 933e: d0 f7       ..  :0030[1]   ; Loop until zero terminator sent
; &9340 referenced 1 time by &0477[2]
.tube_reset_stack
    ldx #&ff                                                          ; 9340: a2 ff       ..  :0032[1]   ; Reset stack pointer to top
    txs                                                               ; 9342: 9a          .   :0034[1]   ; TXS: set stack pointer from X
    cli                                                               ; 9343: 58          X   :0035[1]   ; Enable interrupts for main loop
; &9344 referenced 6 times by &0044[1], &057f[3], &05a6[3], &0604[4], &0665[4], &0692[4]
.tube_main_loop
    bit tube_status_1_and_tube_control                                ; 9344: 2c e0 fe    ,.. :0036[1]   ; BIT R1 status: check WRCH request
    bpl tube_poll_r2                                                  ; 9347: 10 06       ..  :0039[1]   ; R1 not ready: check R2 instead
; &9349 referenced 1 time by &0049[1]
.tube_handle_wrch
    lda tube_data_register_1                                          ; 9349: ad e1 fe    ... :003b[1]   ; Read character from Tube R1 data
    jsr oswrch                                                        ; 934c: 20 ee ff     .. :003e[1]   ; Write character
; &934f referenced 1 time by &0039[1]
.tube_poll_r2
    bit tube_status_register_2                                        ; 934f: 2c e2 fe    ,.. :0041[1]   ; BIT R2 status: check command byte
    bpl tube_main_loop                                                ; 9352: 10 f0       ..  :0044[1]   ; R2 not ready: loop back to R1 check
    bit tube_status_1_and_tube_control                                ; 9354: 2c e0 fe    ,.. :0046[1]   ; Re-check R1: WRCH has priority over R2
    bmi tube_handle_wrch                                              ; 9357: 30 f0       0.  :0049[1]   ; R1 ready: handle WRCH first
    ldx tube_data_register_2                                          ; 9359: ae e3 fe    ... :004b[1]   ; Read command byte from Tube R2 data
    stx tube_cmd_lo                                                   ; 935c: 86 51       .Q  :004e[1]   ; Self-modify JMP low byte for dispatch
.tube_dispatch_cmd
tube_cmd_lo = tube_dispatch_cmd+1
    jmp (tube_dispatch_table)                                         ; 935e: 6c 00 05    l.. :0050[1]   ; Dispatch to handler via indirect JMP

; &935f referenced 1 time by &004e[1]
; &9361 referenced 2 times by &04de[2], &04ee[2]
.tube_transfer_addr
    equb 0                                                            ; 9361: 00          .   :0053[1]   ; Tube transfer address low byte
; &9362 referenced 3 times by &04b6[2], &04d4[2], &04f3[2]
.tube_xfer_page
    equb &80                                                          ; 9362: 80          .   :0054[1]   ; Tube transfer page (default &80)
; &9363 referenced 2 times by &04ba[2], &04fd[2]
.tube_xfer_addr_2
    equb 0                                                            ; 9363: 00          .   :0055[1]   ; Tube transfer address byte 2
; &9364 referenced 2 times by &04be[2], &04fb[2]
.tube_xfer_addr_3
    equb 0                                                            ; 9364: 00          .   :0056[1]   ; Tube transfer address byte 3

    ; Copy the newly assembled block of code back to it's proper place in the binary
    ; file.
    ; (Note the parameter order: 'copyblock <start>,<end>,<dest>')
    copyblock nmi_workspace_start, *, reloc_zp_src

    ; Clear the area of memory we just temporarily used to assemble the new block,
    ; allowing us to assemble there again if needed
    clear nmi_workspace_start, &0057

    ; Set the program counter to the next position in the binary file.
    org reloc_zp_src + (* - nmi_workspace_start)

.reloc_p4_src

; Move 2: &9365 to &0400 for length 256
    org &0400
; ***************************************************************************************
; Tube host code page 4 — reference: NFS12 (BEGIN, ADRR, SENDW)
; 
; Copied from ROM at reloc_p4_src during init. The first 28 bytes (&0400-&041B)
; overlap with the end of the ZP block (the same ROM bytes serve both
; the ZP copy at &005B-&0076 and this page at &0400-&041B). Contains:
;   &0400: JMP &0484 (BEGIN — startup/CLI entry, break type check)
;   &0403: JMP &06E2 (tube_escape_check)
;   &0406: tube_addr_claim — Tube address claim (ADRR protocol)
;   &0414: tube_release_claim — release address claim via R4 cmd 5
;   &0421: tube_post_init — reset claimed-address state to &80
;   &0435: data transfer setup (SENDW protocol) — &0435-&0483
;   &0484: BEGIN — startup entry, sends ROM contents to Tube
;   &04CB: tube_claim_default — claim default transfer address
;   &04D2: tube_init_reloc — extract relocation address from ROM
; ***************************************************************************************
; &9365 referenced 1 time by &8155
.tube_code_page4
    jmp tube_begin                                                    ; 9365: 4c 84 04    L.. :0400[2]   ; JMP to BEGIN startup entry

.tube_escape_entry
    jmp tube_escape_check                                             ; 9368: 4c a7 06    L.. :0403[2]   ; JMP to tube_escape_check (&06A7)

; &936b referenced 10 times by &049a[2], &04cf[2], &8b8f, &8ba6, &8c03, &8e29, &999d, &9a53, &9f3a, &9f42
.tube_addr_claim
    cmp #&80                                                          ; 936b: c9 80       ..  :0406[2]   ; A>=&80: address claim; A<&80: data transfer
    bcc tube_transfer_setup                                           ; 936d: 90 2b       .+  :0408[2]   ; A<&80: data transfer setup (SENDW)
    cmp #&c0                                                          ; 936f: c9 c0       ..  :040a[2]   ; A>=&C0: new address claim from another host
    bcs addr_claim_external                                           ; 9371: b0 1a       ..  :040c[2]   ; C=1: external claim, check ownership
    ora #&40 ; '@'                                                    ; 9373: 09 40       .@  :040e[2]   ; Map &80-&BF range to &C0-&FF for comparison
    cmp tube_claimed_id                                               ; 9375: c5 15       ..  :0410[2]   ; Is this for our currently-claimed address?
    bne return_tube_init                                              ; 9377: d0 20       .   :0412[2]   ; Not our address: return
; ***************************************************************************************
; Release Tube address claim via R4 command 5
; 
; Saves interrupt state (PHP/SEI), sends R4 command 5 (release)
; followed by the currently-claimed address, then restores
; interrupts. Falls through to tube_post_init to reset the
; claimed-address state to &80.
; ***************************************************************************************
; &9379 referenced 1 time by &0471[2]
.tube_release_claim
    php                                                               ; 9379: 08          .   :0414[2]   ; PHP: save interrupt state for release
    sei                                                               ; 937a: 78          x   :0415[2]   ; SEI: disable interrupts during R4 protocol
    lda #5                                                            ; 937b: a9 05       ..  :0416[2]   ; R4 cmd 5: release our address claim
    jsr tube_send_r4                                                  ; 937d: 20 9e 06     .. :0418[2]   ; Send release command to co-processor
    lda tube_claimed_id                                               ; 9380: a5 15       ..  :041b[2]   ; Load our currently-claimed address
    jsr tube_send_r4                                                  ; 9382: 20 9e 06     .. :041d[2]   ; Send our address as release parameter
    plp                                                               ; 9385: 28          (   :0420[2]   ; Restore interrupt state
; &9386 referenced 1 time by &8167
.tube_post_init
    lda #&80                                                          ; 9386: a9 80       ..  :0421[2]   ; &80 sentinel: clear address claim
    sta tube_claimed_id                                               ; 9388: 85 15       ..  :0423[2]   ; &80 sentinel = no address currently claimed
    sta tube_claim_flag                                               ; 938a: 85 14       ..  :0425[2]   ; Store to claim-in-progress flag
    rts                                                               ; 938c: 60          `   :0427[2]   ; Return from tube_post_init

; &938d referenced 1 time by &040c[2]
.addr_claim_external
    asl tube_claim_flag                                               ; 938d: 06 14       ..  :0428[2]   ; Another host claiming; check if we're owner
    bcs accept_new_claim                                              ; 938f: b0 06       ..  :042a[2]   ; C=1: we have an active claim
    cmp tube_claimed_id                                               ; 9391: c5 15       ..  :042c[2]   ; Compare with our claimed address
    beq return_tube_init                                              ; 9393: f0 04       ..  :042e[2]   ; Match: return (we already have it)
    clc                                                               ; 9395: 18          .   :0430[2]   ; Not ours: CLC = we don't own this address
    rts                                                               ; 9396: 60          `   :0431[2]   ; Return with C=0 (claim denied)

; &9397 referenced 1 time by &042a[2]
.accept_new_claim
    sta tube_claimed_id                                               ; 9397: 85 15       ..  :0432[2]   ; Accept new claim: update our address
; &9399 referenced 2 times by &0412[2], &042e[2]
.return_tube_init
    rts                                                               ; 9399: 60          `   :0434[2]   ; Return with address updated

; &939a referenced 1 time by &0408[2]
.tube_transfer_setup
    php                                                               ; 939a: 08          .   :0435[2]   ; PHP: save interrupt state
    sei                                                               ; 939b: 78          x   :0436[2]   ; SEI: disable interrupts for R4 protocol
.setup_data_transfer
    sty tube_data_ptr_hi                                              ; 939c: 84 13       ..  :0437[2]   ; Save 16-bit transfer address from (X,Y)
    stx tube_data_ptr                                                 ; 939e: 86 12       ..  :0439[2]   ; Store address pointer low byte
    jsr tube_send_r4                                                  ; 93a0: 20 9e 06     .. :043b[2]   ; Send transfer type byte to co-processor
    tax                                                               ; 93a3: aa          .   :043e[2]   ; X = transfer type for table lookup
    ldy #3                                                            ; 93a4: a0 03       ..  :043f[2]   ; Y=3: send 4 bytes (address + claimed addr)
    lda tube_claimed_id                                               ; 93a6: a5 15       ..  :0441[2]   ; Send our claimed address + 4-byte xfer addr
    jsr tube_send_r4                                                  ; 93a8: 20 9e 06     .. :0443[2]   ; Send transfer address byte
; &93ab referenced 1 time by &044c[2]
.send_xfer_addr_bytes
    lda (tube_data_ptr),y                                             ; 93ab: b1 12       ..  :0446[2]   ; Load transfer address byte from (X,Y)
    jsr tube_send_r4                                                  ; 93ad: 20 9e 06     .. :0448[2]   ; Send address byte to co-processor via R4
    dey                                                               ; 93b0: 88          .   :044b[2]   ; Previous byte (big-endian: 3,2,1,0)
    bpl send_xfer_addr_bytes                                          ; 93b1: 10 f8       ..  :044c[2]   ; Loop for all 4 address bytes
    ldy #&18                                                          ; 93b3: a0 18       ..  :044e[2]   ; Y=&18: enable Tube control register
    sty tube_status_1_and_tube_control                                ; 93b5: 8c e0 fe    ... :0450[2]   ; Enable Tube interrupt generation
    lda tube_ctrl_values,x                                            ; 93b8: bd 18 05    ... :0453[2]   ; Look up Tube control bits for this xfer type
    sta tube_status_1_and_tube_control                                ; 93bb: 8d e0 fe    ... :0456[2]   ; Apply transfer-specific control bits
    lsr a                                                             ; 93be: 4a          J   :0459[2]   ; LSR: check bit 2 (2-byte flush needed?)
    lsr a                                                             ; 93bf: 4a          J   :045a[2]   ; LSR: shift bit 2 to carry
    bcc skip_r3_flush                                                 ; 93c0: 90 06       ..  :045b[2]   ; C=0: no flush needed, skip R3 reads
    bit tube_data_register_3                                          ; 93c2: 2c e5 fe    ,.. :045d[2]   ; Dummy R3 reads: flush for 2-byte transfers
    bit tube_data_register_3                                          ; 93c5: 2c e5 fe    ,.. :0460[2]   ; Second dummy read to flush R3 FIFO
; &93c8 referenced 1 time by &045b[2]
.skip_r3_flush
    jsr tube_send_r4                                                  ; 93c8: 20 9e 06     .. :0463[2]   ; Trigger co-processor ack via R4
; &93cb referenced 1 time by &0469[2]
.poll_r4_copro_ack
    bit tube_status_register_4_and_cpu_control                        ; 93cb: 2c e6 fe    ,.. :0466[2]   ; Poll R4 status for co-processor response
    bvc poll_r4_copro_ack                                             ; 93ce: 50 fb       P.  :0469[2]   ; Bit 6 clear: not ready, keep polling
    bcs copro_ack_nmi_check                                           ; 93d0: b0 0d       ..  :046b[2]   ; R4 bit 7: co-processor acknowledged transfer
    cpx #4                                                            ; 93d2: e0 04       ..  :046d[2]   ; Type 4 = SENDW (host-to-parasite word xfer)
    bne skip_nmi_release                                              ; 93d4: d0 11       ..  :046f[2]   ; Not SENDW type: skip release path
; &93d6 referenced 1 time by &0496[2]
.tube_sendw_complete
    jsr tube_release_claim                                            ; 93d6: 20 14 04     .. :0471[2]   ; SENDW complete: release, sync, restart
    jsr tube_send_r2                                                  ; 93d9: 20 95 06     .. :0474[2]   ; Sync via R2 send
    jmp tube_reset_stack                                              ; 93dc: 4c 32 00    L2. :0477[2]   ; Restart Tube main loop

; &93df referenced 1 time by &046b[2]
.copro_ack_nmi_check
    lsr a                                                             ; 93df: 4a          J   :047a[2]   ; LSR: check bit 0 (NMI used?)
    bcc skip_nmi_release                                              ; 93e0: 90 05       ..  :047b[2]   ; C=0: NMI not used, skip NMI release
    ldy #&88                                                          ; 93e2: a0 88       ..  :047d[2]   ; Release Tube NMI (transfer used interrupts)
    sty tube_status_1_and_tube_control                                ; 93e4: 8c e0 fe    ... :047f[2]   ; Write &88 to Tube control to release NMI
; &93e7 referenced 2 times by &046f[2], &047b[2]
.skip_nmi_release
    plp                                                               ; 93e7: 28          (   :0482[2]   ; Restore interrupt state
.return_tube_xfer
    rts                                                               ; 93e8: 60          `   :0483[2]   ; Return from transfer setup

; ***************************************************************************************
; Tube host startup entry (BEGIN)
; 
; Entry point via JMP from &0400. Enables interrupts, checks
; break type via OSBYTE &FD: soft break re-initialises Tube and
; restarts, hard break claims address &FF. Sends ROM contents
; to co-processor page by page via SENDW, then claims the final
; transfer address.
; ***************************************************************************************
; &93e9 referenced 1 time by &0400[2]
.tube_begin
    cli                                                               ; 93e9: 58          X   :0484[2]   ; BEGIN: enable interrupts for Tube host code
    bcs claim_addr_ff                                                 ; 93ea: b0 11       ..  :0485[2]   ; C=1: hard break, claim addr &FF
    bne check_break_type                                              ; 93ec: d0 03       ..  :0487[2]   ; C=0, A!=0: re-init path
    jmp tube_reply_ack                                                ; 93ee: 4c 9c 05    L.. :0489[2]   ; Z=1 from C=0 path: just acknowledge

; &93f1 referenced 1 time by &0487[2]
.check_break_type
    ldx #0                                                            ; 93f1: a2 00       ..  :048c[2]   ; X=0 for OSBYTE
    ldy #&ff                                                          ; 93f3: a0 ff       ..  :048e[2]   ; Y=&FF for OSBYTE
    lda #osbyte_read_write_last_break_type                            ; 93f5: a9 fd       ..  :0490[2]   ; OSBYTE &FD: what type of reset was this?
    jsr osbyte                                                        ; 93f7: 20 f4 ff     .. :0492[2]   ; Read type of last reset
    txa                                                               ; 93fa: 8a          .   :0495[2]   ; X=value of type of last reset
    beq tube_sendw_complete                                           ; 93fb: f0 d9       ..  :0496[2]   ; Soft break (X=0): re-init Tube and restart
; &93fd referenced 2 times by &0485[2], &049d[2]
.claim_addr_ff
    lda #&ff                                                          ; 93fd: a9 ff       ..  :0498[2]   ; Claim address &FF (startup = highest prio)
    jsr tube_addr_claim                                               ; 93ff: 20 06 04     .. :049a[2]   ; Request address claim from Tube system
    bcc claim_addr_ff                                                 ; 9402: 90 f9       ..  :049d[2]   ; C=0: claim failed, retry
    jsr tube_init_reloc                                               ; 9404: 20 d2 04     .. :049f[2]   ; Init reloc pointers from ROM header
; &9407 referenced 1 time by &04c4[2]
.next_rom_page
    lda #7                                                            ; 9407: a9 07       ..  :04a2[2]   ; R4 cmd 7: SENDW to send ROM to parasite
    jsr tube_claim_default                                            ; 9409: 20 cb 04     .. :04a4[2]   ; Set up Tube for SENDW transfer
    ldy #0                                                            ; 940c: a0 00       ..  :04a7[2]   ; Y=0: start at beginning of page
    sty zp_ptr_lo                                                     ; 940e: 84 00       ..  :04a9[2]   ; Store to zero page pointer low byte
; &9410 referenced 1 time by &04b4[2]
.send_rom_page_bytes
    lda (zp_ptr_lo),y                                                 ; 9410: b1 00       ..  :04ab[2]   ; Send 256-byte page via R3, byte at a time
    sta tube_data_register_3                                          ; 9412: 8d e5 fe    ... :04ad[2]   ; Write byte to Tube R3 data register
    nop                                                               ; 9415: ea          .   :04b0[2]   ; Timing delay: Tube data register needs NOPs
    nop                                                               ; 9416: ea          .   :04b1[2]   ; NOP delay (2)
    nop                                                               ; 9417: ea          .   :04b2[2]   ; NOP delay (3)
    iny                                                               ; 9418: c8          .   :04b3[2]   ; Next byte in page
    bne send_rom_page_bytes                                           ; 9419: d0 f5       ..  :04b4[2]   ; Loop for all 256 bytes
    inc tube_xfer_page                                                ; 941b: e6 54       .T  :04b6[2]   ; Increment 24-bit destination addr
    bne skip_addr_carry                                               ; 941d: d0 06       ..  :04b8[2]   ; No carry: skip higher bytes
    inc tube_xfer_addr_2                                              ; 941f: e6 55       .U  :04ba[2]   ; Carry into second byte
    bne skip_addr_carry                                               ; 9421: d0 02       ..  :04bc[2]   ; No carry: skip third byte
    inc tube_xfer_addr_3                                              ; 9423: e6 56       .V  :04be[2]   ; Carry into third byte
; &9425 referenced 2 times by &04b8[2], &04bc[2]
.skip_addr_carry
    inc zp_ptr_hi                                                     ; 9425: e6 01       ..  :04c0[2]   ; Increment page counter
    bit zp_ptr_hi                                                     ; 9427: 24 01       $.  :04c2[2]   ; Bit 6 set = all pages transferred
    bvc next_rom_page                                                 ; 9429: 50 dc       P.  :04c4[2]   ; More pages: loop back to SENDW
    jsr tube_init_reloc                                               ; 942b: 20 d2 04     .. :04c6[2]   ; Re-init reloc pointers for final claim
    lda #4                                                            ; 942e: a9 04       ..  :04c9[2]   ; A=4: transfer type for final address claim
; ***************************************************************************************
; Claim default Tube transfer address
; 
; Sets Y=0, X=&53 (address &0053), then JMP tube_addr_claim
; to initiate a Tube address claim for the default transfer
; address. Called from the BEGIN startup path and after the
; page transfer loop completes.
; ***************************************************************************************
; &9430 referenced 1 time by &04a4[2]
.tube_claim_default
    ldy #0                                                            ; 9430: a0 00       ..  :04cb[2]   ; Y=0: transfer address low byte
    ldx #&53 ; 'S'                                                    ; 9432: a2 53       .S  :04cd[2]   ; X=&53: transfer address high byte (&0053)
    jmp tube_addr_claim                                               ; 9434: 4c 06 04    L.. :04cf[2]   ; Claim Tube address for transfer

; ***************************************************************************************
; Initialise relocation address for ROM transfer
; 
; Sets source page to &8000 and page counter to &80. Checks
; ROM type bit 5 for a relocation address in the ROM header;
; if present, extracts the 4-byte address from after the
; copyright string. Otherwise uses default &8000 start.
; ***************************************************************************************
; &9437 referenced 2 times by &049f[2], &04c6[2]
.tube_init_reloc
    lda #&80                                                          ; 9437: a9 80       ..  :04d2[2]   ; Init: start sending from &8000
    sta tube_xfer_page                                                ; 9439: 85 54       .T  :04d4[2]   ; Store &80 as source page high byte
    sta zp_ptr_hi                                                     ; 943b: 85 01       ..  :04d6[2]   ; Store &80 as page counter initial value
    lda #&20 ; ' '                                                    ; 943d: a9 20       .   :04d8[2]   ; A=&20: bit 5 mask for ROM type check
    and rom_type                                                      ; 943f: 2d 06 80    -.. :04da[2]   ; ROM type bit 5: reloc address in header?
    tay                                                               ; 9442: a8          .   :04dd[2]   ; Y = 0 or &20 (reloc flag)
    sty tube_transfer_addr                                            ; 9443: 84 53       .S  :04de[2]   ; Store as transfer address selector
    beq store_xfer_end_addr                                           ; 9445: f0 19       ..  :04e0[2]   ; No reloc addr: use defaults
    ldx copyright_offset                                              ; 9447: ae 07 80    ... :04e2[2]   ; Skip past copyright string to find reloc addr
; &944a referenced 1 time by &04e9[2]
.scan_copyright_end
    inx                                                               ; 944a: e8          .   :04e5[2]   ; Skip past null-terminated copyright string
    lda rom_header,x                                                  ; 944b: bd 00 80    ... :04e6[2]   ; Load next byte from ROM header
    bne scan_copyright_end                                            ; 944e: d0 fa       ..  :04e9[2]   ; Loop until null terminator found
    lda language_handler_lo,x                                         ; 9450: bd 01 80    ... :04eb[2]   ; Read 4-byte reloc address from ROM header
    sta tube_transfer_addr                                            ; 9453: 85 53       .S  :04ee[2]   ; Store reloc addr byte 1 as transfer addr
    lda language_handler_hi,x                                         ; 9455: bd 02 80    ... :04f0[2]   ; Load reloc addr byte 2
    sta tube_xfer_page                                                ; 9458: 85 54       .T  :04f3[2]   ; Store as source page start
    ldy service_entry,x                                               ; 945a: bc 03 80    ... :04f5[2]   ; Load reloc addr byte 3
    lda service_handler_lo,x                                          ; 945d: bd 04 80    ... :04f8[2]   ; Load reloc addr byte 4 (highest)
; &9460 referenced 1 time by &04e0[2]
.store_xfer_end_addr
    sta tube_xfer_addr_3                                              ; 9460: 85 56       .V  :04fb[2]   ; Store high byte of end address
    sty tube_xfer_addr_2                                              ; 9462: 84 55       .U  :04fd[2]   ; Store byte 3 of end address
    rts                                                               ; 9464: 60          `   :04ff[2]   ; Return with pointers initialised


    ; Copy the newly assembled block of code back to it's proper place in the binary
    ; file.
    ; (Note the parameter order: 'copyblock <start>,<end>,<dest>')
    copyblock tube_code_page4, *, reloc_p4_src

    ; Clear the area of memory we just temporarily used to assemble the new block,
    ; allowing us to assemble there again if needed
    clear tube_code_page4, &0500

    ; Set the program counter to the next position in the binary file.
    org reloc_p4_src + (* - tube_code_page4)

.reloc_p5_src

; Move 3: &9465 to &0500 for length 256
    org &0500
; ***************************************************************************************
; Tube host code page 5 — reference: NFS13 (TASKS, BPUT-FILE)
; 
; Copied from ROM at reloc_p5_src during init. Contains:
;   &0500: 12-entry dispatch table (&0500-&0517)
;   &0518: 8-byte Tube control register value table
;   &0520: tube_osbput — write byte to file
;   &052D: tube_osbget — read byte from file
;   &0537: tube_osrdch — read character
;   &053A: tube_rdch_reply — send carry+data as reply
;   &0542: tube_osfind — open/close file
;   &055E: tube_osargs — file argument read/write
;   &0582: tube_read_string — read string from R2 into &0700
;   &0596: tube_oscli — execute * command
;   &059C: tube_reply_ack — send &7F acknowledge
;   &05A9: tube_osfile — whole file operation
;   &05D1: tube_osgbpb — multi-byte file read/write
; Code continues seamlessly into page 6 (tube_osbyte_short at &05F2
; straddles the page boundary with a BVC at &05FF/&0600).
; ***************************************************************************************
; &9465 referenced 2 times by &0050[1], &815b
.tube_dispatch_table
    equw tube_osrdch                                                  ; 9465: 37 05       7.  :0500[3]   ; R2 cmd 0: OSRDCH
    equw tube_oscli                                                   ; 9467: 96 05       ..  :0502[3]   ; R2 cmd 1: OSCLI
    equw tube_osbyte_2param                                           ; 9469: f2 05       ..  :0504[3]   ; R2 cmd 2: OSBYTE (2-param)
    equw tube_osbyte_long                                             ; 946b: 07 06       ..  :0506[3]   ; R2 cmd 3: OSBYTE (3-param)
    equw tube_osword                                                  ; 946d: 27 06       '.  :0508[3]   ; R2 cmd 4: OSWORD
    equw tube_osword_rdln                                             ; 946f: 68 06       h.  :050a[3]   ; R2 cmd 5: OSWORD 0 (read line)
    equw tube_osargs                                                  ; 9471: 5e 05       ^.  :050c[3]   ; R2 cmd 6: OSARGS
    equw tube_osbget                                                  ; 9473: 2d 05       -.  :050e[3]   ; R2 cmd 7: OSBGET
    equw tube_osbput                                                  ; 9475: 20 05        .  :0510[3]   ; R2 cmd 8: OSBPUT
    equw tube_osfind                                                  ; 9477: 42 05       B.  :0512[3]   ; R2 cmd 9: OSFIND
    equw tube_osfile                                                  ; 9479: a9 05       ..  :0514[3]   ; R2 cmd 10: OSFILE
    equw tube_osgbpb                                                  ; 947b: d1 05       ..  :0516[3]   ; R2 cmd 11: OSGBPB
; Tube ULA control register values, indexed by transfer
; type (0-7). Written to &FEE0 after clearing V+M with
; &18. Bit layout: S=set/clear, T=reset regs, P=PRST,
; V=2-byte R3, M=PNMI(R3), J=PIRQ(R4), I=PIRQ(R1),
; Q=HIRQ(R4). Bits 1-7 select flags; bit 0 (S) is the
; value to set or clear.
; &947d referenced 1 time by &0453[2]
.tube_ctrl_values
    equb &86                                                          ; 947d: 86          .   :0518[3]   ; Type 0: set I+J (1-byte R3, parasite to host)
    equb &88                                                          ; 947e: 88          .   :0519[3]   ; Type 1: set M (1-byte R3, host to parasite)
    equb &96                                                          ; 947f: 96          .   :051a[3]   ; Type 2: set V+I+J (2-byte R3, parasite to host)
    equb &98                                                          ; 9480: 98          .   :051b[3]   ; Type 3: set V+M (2-byte R3, host to parasite)
    equb &18                                                          ; 9481: 18          .   :051c[3]   ; Type 4: clear V+M (execute code at address)
    equb &18                                                          ; 9482: 18          .   :051d[3]   ; Type 5: clear V+M (release address claim)
    equb &82                                                          ; 9483: 82          .   :051e[3]   ; Type 6: set I (define event handler)
    equb &18                                                          ; 9484: 18          .   :051f[3]   ; Type 7: clear V+M (transfer and release)

; ***************************************************************************************
; Tube OSBPUT handler (R2 cmd 8)
; 
; Reads file handle and data byte from R2, then
; calls OSBPUT (&FFD4) to write the byte. Falls through
; to tube_reply_ack to send &7F acknowledgement.
; ***************************************************************************************
.tube_osbput
    jsr tube_read_r2                                                  ; 9485: 20 c5 06     .. :0520[3]   ; Read channel handle from R2 for BPUT
    tay                                                               ; 9488: a8          .   :0523[3]   ; Y=channel handle from R2
    jsr tube_read_r2                                                  ; 9489: 20 c5 06     .. :0524[3]   ; Read data byte from R2 for BPUT
.tube_poll_r1_wrch
    jsr osbput                                                        ; 948c: 20 d4 ff     .. :0527[3]   ; Write a single byte A to an open file Y
    jmp tube_reply_ack                                                ; 948f: 4c 9c 05    L.. :052a[3]   ; BPUT done: send acknowledge, return

; ***************************************************************************************
; Tube OSBGET handler (R2 cmd 7)
; 
; Reads file handle from R2, calls OSBGET (&FFD7)
; to read a byte, then falls through to tube_rdch_reply
; which encodes the carry flag (error) into bit 7 and
; sends the result byte via R2.
; ***************************************************************************************
.tube_osbget
    jsr tube_read_r2                                                  ; 9492: 20 c5 06     .. :052d[3]   ; Read channel handle from R2 for BGET
    tay                                                               ; 9495: a8          .   :0530[3]   ; Y=channel handle for OSBGET; Y=file handle
    jsr osbget                                                        ; 9496: 20 d7 ff     .. :0531[3]   ; Read a single byte from an open file Y
    jmp tube_rdch_reply                                               ; 9499: 4c 3a 05    L:. :0534[3]   ; Send carry+byte reply (BGET result)

; ***************************************************************************************
; Tube OSRDCH handler (R2 cmd 0)
; 
; Calls OSRDCH (&FFE0) to read a character from
; the current input stream, then falls through to
; tube_rdch_reply which encodes the carry flag (error)
; into bit 7 and sends the result byte via R2.
; ***************************************************************************************
.tube_osrdch
    jsr osrdch                                                        ; 949c: 20 e0 ff     .. :0537[3]   ; Read a character from the current input stream
; &949f referenced 2 times by &0534[3], &05ef[3]
.tube_rdch_reply
    ror a                                                             ; 949f: 6a          j   :053a[3]   ; ROR A: encode carry (error flag) into bit 7
    jsr tube_send_r2                                                  ; 94a0: 20 95 06     .. :053b[3]   ; Send carry+data byte to Tube R2
    rol a                                                             ; 94a3: 2a          *   :053e[3]   ; ROL A: restore carry flag
    jmp tube_reply_byte                                               ; 94a4: 4c 9e 05    L.. :053f[3]   ; Return via tube_reply_byte

; ***************************************************************************************
; Tube OSFIND handler (R2 cmd 9)
; 
; Reads open mode from R2. If zero, reads a file
; handle and closes that file. Otherwise saves the mode,
; reads a filename string into &0700 via tube_read_string,
; then calls OSFIND (&FFCE) to open the file. Sends the
; resulting file handle (or &00) via tube_reply_byte.
; ***************************************************************************************
.tube_osfind
    jsr tube_read_r2                                                  ; 94a7: 20 c5 06     .. :0542[3]   ; Read open mode from R2 for OSFIND
    beq tube_osfind_close                                             ; 94aa: f0 0b       ..  :0545[3]   ; A=0: close file, else open with filename
    pha                                                               ; 94ac: 48          H   :0547[3]   ; Save open mode while reading filename
    jsr tube_read_string                                              ; 94ad: 20 82 05     .. :0548[3]   ; Read filename string from R2 into &0700
    pla                                                               ; 94b0: 68          h   :054b[3]   ; Recover open mode from stack
    jsr osfind                                                        ; 94b1: 20 ce ff     .. :054c[3]   ; Open or close file(s)
    jmp tube_reply_byte                                               ; 94b4: 4c 9e 05    L.. :054f[3]   ; Send file handle result to co-processor

; &94b7 referenced 1 time by &0545[3]
.tube_osfind_close
    jsr tube_read_r2                                                  ; 94b7: 20 c5 06     .. :0552[3]   ; OSFIND close: read handle from R2
    tay                                                               ; 94ba: a8          .   :0555[3]   ; Y=handle to close
    lda #osfind_close                                                 ; 94bb: a9 00       ..  :0556[3]   ; A=0: close command for OSFIND
    jsr osfind                                                        ; 94bd: 20 ce ff     .. :0558[3]   ; Close one or all files
    jmp tube_reply_ack                                                ; 94c0: 4c 9c 05    L.. :055b[3]   ; Close done: send acknowledge, return

; ***************************************************************************************
; Tube OSARGS handler (R2 cmd 6)
; 
; Reads file handle from R2 into Y, then reads
; a 4-byte argument and reason code into zero page.
; Calls OSARGS (&FFDA), sends the result A and 4-byte
; return value via R2, then returns to the main loop.
; ***************************************************************************************
.tube_osargs
    jsr tube_read_r2                                                  ; 94c3: 20 c5 06     .. :055e[3]   ; Read file handle from R2 for OSARGS
    tay                                                               ; 94c6: a8          .   :0561[3]   ; Y=file handle for OSARGS
.tube_read_params
    ldx #4                                                            ; 94c7: a2 04       ..  :0562[3]   ; Read 4-byte arg + reason from R2 into ZP
; &94c9 referenced 1 time by &056a[3]
.read_osargs_params
    jsr tube_read_r2                                                  ; 94c9: 20 c5 06     .. :0564[3]   ; Read next param byte from R2
    sta escape_flag,x                                                 ; 94cc: 95 ff       ..  :0567[3]   ; Params stored at &00-&03 (little-endian)
    dex                                                               ; 94ce: ca          .   :0569[3]   ; Decrement byte counter
    bne read_osargs_params                                            ; 94cf: d0 f8       ..  :056a[3]   ; Loop for 4 bytes
    jsr tube_read_r2                                                  ; 94d1: 20 c5 06     .. :056c[3]   ; Read OSARGS reason code from R2
    jsr osargs                                                        ; 94d4: 20 da ff     .. :056f[3]   ; Read or write a file's attributes
    jsr tube_send_r2                                                  ; 94d7: 20 95 06     .. :0572[3]   ; Send result A back to co-processor
    ldx #3                                                            ; 94da: a2 03       ..  :0575[3]   ; Return 4-byte result from ZP &00-&03
; &94dc referenced 1 time by &057d[3]
.send_osargs_result
    lda zp_ptr_lo,x                                                   ; 94dc: b5 00       ..  :0577[3]   ; Load result byte from zero page
    jsr tube_send_r2                                                  ; 94de: 20 95 06     .. :0579[3]   ; Send byte to co-processor via R2
    dex                                                               ; 94e1: ca          .   :057c[3]   ; Previous byte (count down)
    bpl send_osargs_result                                            ; 94e2: 10 f8       ..  :057d[3]   ; Loop for all 4 bytes
    jmp tube_main_loop                                                ; 94e4: 4c 36 00    L6. :057f[3]   ; Return to Tube main loop

; ***************************************************************************************
; Read string from Tube R2 into buffer
; 
; Loops reading bytes from tube_read_r2 into the
; string buffer at &0700, storing at string_buf+Y.
; Terminates on CR (&0D) or when Y wraps to zero
; (256-byte overflow). Returns with X=0, Y=7 so that
; XY = &0700, ready for OSCLI or OSFIND dispatch.
; Called by the Tube OSCLI and OSFIND handlers.
; ***************************************************************************************
; &94e7 referenced 3 times by &0548[3], &0596[3], &05b3[3]
.tube_read_string
    ldx #0                                                            ; 94e7: a2 00       ..  :0582[3]   ; X=0: initialise string buffer index
    ldy #0                                                            ; 94e9: a0 00       ..  :0584[3]   ; Y=0: string buffer offset 0
; &94eb referenced 1 time by &0591[3]
.strnh
    jsr tube_read_r2                                                  ; 94eb: 20 c5 06     .. :0586[3]   ; Read next string byte from R2
    sta string_buf,y                                                  ; 94ee: 99 00 07    ... :0589[3]   ; Store byte in string buffer at &0700+Y
    iny                                                               ; 94f1: c8          .   :058c[3]   ; Next buffer position
    beq string_buf_done                                               ; 94f2: f0 04       ..  :058d[3]   ; Y overflow: string too long, truncate
    cmp #&0d                                                          ; 94f4: c9 0d       ..  :058f[3]   ; Check for CR terminator
    bne strnh                                                         ; 94f6: d0 f3       ..  :0591[3]   ; Not CR: continue reading string
; &94f8 referenced 1 time by &058d[3]
.string_buf_done
    ldy #7                                                            ; 94f8: a0 07       ..  :0593[3]   ; Y=7: set XY=&0700 for OSCLI/OSFIND
    rts                                                               ; 94fa: 60          `   :0595[3]   ; Return with XY pointing to &0700

; ***************************************************************************************
; Tube OSCLI handler (R2 cmd 1)
; 
; Reads a command string from R2 into &0700 via
; tube_read_string, then calls OSCLI (&FFF7) to execute
; it. Falls through to tube_reply_ack to send &7F
; acknowledgement.
; ***************************************************************************************
.tube_oscli
    jsr tube_read_string                                              ; 94fb: 20 82 05     .. :0596[3]   ; Read command string from R2 into &0700
    jsr oscli                                                         ; 94fe: 20 f7 ff     .. :0599[3]   ; Execute * command via OSCLI
; &9501 referenced 3 times by &0489[2], &052a[3], &055b[3]
.tube_reply_ack
    lda #&7f                                                          ; 9501: a9 7f       ..  :059c[3]   ; &7F = success acknowledgement
; &9503 referenced 4 times by &053f[3], &054f[3], &05a1[3], &067d[4]
.tube_reply_byte
    bit tube_status_register_2                                        ; 9503: 2c e2 fe    ,.. :059e[3]   ; Poll R2 status until ready
    bvc tube_reply_byte                                               ; 9506: 50 fb       P.  :05a1[3]   ; Bit 6 clear: not ready, loop
    sta tube_data_register_2                                          ; 9508: 8d e3 fe    ... :05a3[3]   ; Write byte to R2 data register
; &950b referenced 1 time by &05cf[3]
.mj
    jmp tube_main_loop                                                ; 950b: 4c 36 00    L6. :05a6[3]   ; Return to Tube main loop

; ***************************************************************************************
; Tube OSFILE handler (R2 cmd 10)
; 
; Reads a 16-byte control block into zero page,
; a filename string into &0700 via tube_read_string,
; and a reason code from R2. Calls OSFILE (&FFDD),
; then sends the result A and updated 16-byte control
; block back via R2. Returns to the main loop via mj.
; ***************************************************************************************
.tube_osfile
    ldx #&10                                                          ; 950e: a2 10       ..  :05a9[3]   ; Read 16-byte OSFILE control block from R2
; &9510 referenced 1 time by &05b1[3]
.argsw
    jsr tube_read_r2                                                  ; 9510: 20 c5 06     .. :05ab[3]   ; Read next control block byte from R2
    sta zp_ptr_hi,x                                                   ; 9513: 95 01       ..  :05ae[3]   ; Store at &01+X (descending)
    dex                                                               ; 9515: ca          .   :05b0[3]   ; Decrement byte counter
    bne argsw                                                         ; 9516: d0 f8       ..  :05b1[3]   ; Loop for all 16 bytes
    jsr tube_read_string                                              ; 9518: 20 82 05     .. :05b3[3]   ; Read filename string from R2 into &0700
    stx zp_ptr_lo                                                     ; 951b: 86 00       ..  :05b6[3]   ; XY=&0700: filename pointer for OSFILE
    sty zp_ptr_hi                                                     ; 951d: 84 01       ..  :05b8[3]   ; Store Y=7 as pointer high byte
    ldy #0                                                            ; 951f: a0 00       ..  :05ba[3]   ; Y=0 for OSFILE control block offset
    jsr tube_read_r2                                                  ; 9521: 20 c5 06     .. :05bc[3]   ; Read OSFILE reason code from R2
    jsr osfile                                                        ; 9524: 20 dd ff     .. :05bf[3]   ; Execute OSFILE operation
    jsr tube_send_r2                                                  ; 9527: 20 95 06     .. :05c2[3]   ; Send result A (object type) to co-processor
    ldx #&10                                                          ; 952a: a2 10       ..  :05c5[3]   ; Return 16-byte control block to co-processor
; &952c referenced 1 time by &05cd[3]
.send_osfile_ctrl_blk
    lda zp_ptr_hi,x                                                   ; 952c: b5 01       ..  :05c7[3]   ; Load control block byte
    jsr tube_send_r2                                                  ; 952e: 20 95 06     .. :05c9[3]   ; Send byte to co-processor via R2
    dex                                                               ; 9531: ca          .   :05cc[3]   ; Decrement byte counter
    bne send_osfile_ctrl_blk                                          ; 9532: d0 f8       ..  :05cd[3]   ; Loop for all 16 bytes
    beq mj                                                            ; 9534: f0 d5       ..  :05cf[3]   ; ALWAYS branch to main loop; ALWAYS branch

; ***************************************************************************************
; Tube OSGBPB handler (R2 cmd 11)
; 
; Reads a 13-byte control block and reason code
; from R2 into zero page. Calls OSGBPB (&FFD1), then
; sends 12 result bytes and the carry+result byte
; (via tube_rdch_reply) back via R2.
; ***************************************************************************************
.tube_osgbpb
    ldx #&0d                                                          ; 9536: a2 0d       ..  :05d1[3]   ; Read 13-byte OSGBPB control block from R2
; &9538 referenced 1 time by &05d9[3]
.read_osgbpb_ctrl_blk
    jsr tube_read_r2                                                  ; 9538: 20 c5 06     .. :05d3[3]   ; Read next control block byte from R2
    sta escape_flag,x                                                 ; 953b: 95 ff       ..  :05d6[3]   ; Store at &FF+X (descending into &00-&0C)
    dex                                                               ; 953d: ca          .   :05d8[3]   ; Decrement byte counter
    bne read_osgbpb_ctrl_blk                                          ; 953e: d0 f8       ..  :05d9[3]   ; Loop for all 13 bytes
    jsr tube_read_r2                                                  ; 9540: 20 c5 06     .. :05db[3]   ; Read OSGBPB reason code from R2
    ldy #0                                                            ; 9543: a0 00       ..  :05de[3]   ; Y=0 for OSGBPB control block
    jsr osgbpb                                                        ; 9545: 20 d1 ff     .. :05e0[3]   ; Read or write multiple bytes to an open file
    pha                                                               ; 9548: 48          H   :05e3[3]   ; Save A (completion status) for later
    ldx #&0c                                                          ; 9549: a2 0c       ..  :05e4[3]   ; Return 13-byte result block to co-processor
; &954b referenced 1 time by &05ec[3]
.send_osgbpb_result
    lda zp_ptr_lo,x                                                   ; 954b: b5 00       ..  :05e6[3]   ; Load result byte from zero page
    jsr tube_send_r2                                                  ; 954d: 20 95 06     .. :05e8[3]   ; Send byte to co-processor via R2
    dex                                                               ; 9550: ca          .   :05eb[3]   ; Decrement byte counter
    bpl send_osgbpb_result                                            ; 9551: 10 f8       ..  :05ec[3]   ; Loop for 13 bytes (X=12..0)
    pla                                                               ; 9553: 68          h   :05ee[3]   ; Recover completion status from stack
    jmp tube_rdch_reply                                               ; 9554: 4c 3a 05    L:. :05ef[3]   ; Send carry+status as RDCH-style reply

; ***************************************************************************************
; Tube OSBYTE 2-param handler (R2 cmd 2)
; 
; Reads X and A from R2, calls OSBYTE (&FFF4)
; with Y=0, then sends the result X via
; tube_reply_byte. Used for OSBYTE calls that take
; only A and X parameters.
; ***************************************************************************************
.tube_osbyte_2param
    jsr tube_read_r2                                                  ; 9557: 20 c5 06     .. :05f2[3]   ; Read X param from R2 for 2-param OSBYTE
    tax                                                               ; 955a: aa          .   :05f5[3]   ; X = first parameter
    jsr tube_read_r2                                                  ; 955b: 20 c5 06     .. :05f6[3]   ; Read A (OSBYTE number) from R2
    jsr osbyte                                                        ; 955e: 20 f4 ff     .. :05f9[3]   ; Execute OSBYTE call
; &9561 referenced 2 times by &05ff[3], &0625[4]
.tube_poll_r2_result
    bit tube_status_register_2                                        ; 9561: 2c e2 fe    ,.. :05fc[3]   ; Poll R2 status for result send
    equb &50                                                          ; 9564: 50          P   :05ff[3]   ; BVC: page 5/6 boundary straddle

    ; Copy the newly assembled block of code back to it's proper place in the binary
    ; file.
    ; (Note the parameter order: 'copyblock <start>,<end>,<dest>')
    copyblock tube_dispatch_table, *, reloc_p5_src

    ; Clear the area of memory we just temporarily used to assemble the new block,
    ; allowing us to assemble there again if needed
    clear tube_dispatch_table, &0600

    ; Set the program counter to the next position in the binary file.
    org reloc_p5_src + (* - tube_dispatch_table)

.reloc_p6_src

; Move 4: &9565 to &0600 for length 256
    org &0600
; &9565 referenced 1 time by &8161
.tube_page6_start
    equb &fb                                                          ; 9565: fb          .   :0600[4]   ; Send carry+status to co-processor via R2

    stx tube_data_register_2                                          ; 9566: 8e e3 fe    ... :0601[4]   ; Send X result for 2-param OSBYTE
; &9569 referenced 1 time by &0617[4]
.bytex
    jmp tube_main_loop                                                ; 9569: 4c 36 00    L6. :0604[4]   ; Return to main event loop

; ***************************************************************************************
; Tube OSBYTE 3-param handler (R2 cmd 3)
; 
; Reads X, Y, and A from R2, calls OSBYTE
; (&FFF4), then sends carry+Y and X as result bytes
; via R2. Used for OSBYTE calls needing all three
; parameters and returning both X and Y results.
; ***************************************************************************************
.tube_osbyte_long
    jsr tube_read_r2                                                  ; 956c: 20 c5 06     .. :0607[4]   ; Read X, Y, A from R2 for 3-param OSBYTE
    tax                                                               ; 956f: aa          .   :060a[4]   ; Save in X
    jsr tube_read_r2                                                  ; 9570: 20 c5 06     .. :060b[4]   ; Read Y parameter from co-processor
    tay                                                               ; 9573: a8          .   :060e[4]   ; Save in Y
    jsr tube_read_r2                                                  ; 9574: 20 c5 06     .. :060f[4]   ; Read A (OSBYTE function code)
    jsr osbyte                                                        ; 9577: 20 f4 ff     .. :0612[4]   ; Execute OSBYTE A,X,Y
    eor #&9d                                                          ; 957a: 49 9d       I.  :0615[4]   ; Test for OSBYTE &9D (fast Tube BPUT)
    beq bytex                                                         ; 957c: f0 eb       ..  :0617[4]   ; OSBYTE &9D (fast Tube BPUT): no result needed
    ror a                                                             ; 957e: 6a          j   :0619[4]   ; Encode carry (error flag) into bit 7
    jsr tube_send_r2                                                  ; 957f: 20 95 06     .. :061a[4]   ; Send carry+status byte via R2
; &9582 referenced 1 time by &0620[4]
.tube_osbyte_send_y
    bit tube_status_register_2                                        ; 9582: 2c e2 fe    ,.. :061d[4]   ; Poll R2 status for ready
    bvc tube_osbyte_send_y                                            ; 9585: 50 fb       P.  :0620[4]   ; Not ready: keep polling
    sty tube_data_register_2                                          ; 9587: 8c e3 fe    ... :0622[4]   ; Send Y result, then fall through to send X
.tube_osbyte_short
    bvs tube_poll_r2_result                                           ; 958a: 70 d5       p.  :0625[4]   ; BVS &05FC: overlapping code — loops back to page 5 R2 poll to send X after Y
; ***************************************************************************************
; Tube OSWORD handler (R2 cmd 4)
; 
; Reads OSWORD number A and in-length from R2,
; then reads the parameter block into &0128. Calls
; OSWORD (&FFF1), then sends the out-length result
; bytes from the parameter block back via R2.
; Returns to the main loop via tube_return_main.
; ***************************************************************************************
.tube_osword
    jsr tube_read_r2                                                  ; 958c: 20 c5 06     .. :0627[4]   ; Overlapping entry: &20 = JSR c06c5 (OSWORD)
    tay                                                               ; 958f: a8          .   :062a[4]   ; Save OSWORD number in Y
; &9590 referenced 1 time by &062e[4]
.tube_osword_read
    bit tube_status_register_2                                        ; 9590: 2c e2 fe    ,.. :062b[4]   ; Poll R2 status for data ready
    bpl tube_osword_read                                              ; 9593: 10 fb       ..  :062e[4]   ; Not ready: keep polling
.tube_osbyte_send_x
    ldx tube_data_register_2                                          ; 9595: ae e3 fe    ... :0630[4]   ; Read param block length from R2
    dex                                                               ; 9598: ca          .   :0633[4]   ; DEX: length 0 means no params to read
    bmi skip_param_read                                               ; 9599: 30 0f       0.  :0634[4]   ; No params (length=0): skip read loop
; &959b referenced 2 times by &0639[4], &0642[4]
.tube_osword_read_lp
    bit tube_status_register_2                                        ; 959b: 2c e2 fe    ,.. :0636[4]   ; Poll R2 status for data ready
    bpl tube_osword_read_lp                                           ; 959e: 10 fb       ..  :0639[4]   ; Not ready: keep polling
    lda tube_data_register_2                                          ; 95a0: ad e3 fe    ... :063b[4]   ; Read param byte from R2
    sta tube_osword_pb,x                                              ; 95a3: 9d 28 01    .(. :063e[4]   ; Store param bytes into block at &0128
    dex                                                               ; 95a6: ca          .   :0641[4]   ; Next param byte (descending)
    bpl tube_osword_read_lp                                           ; 95a7: 10 f2       ..  :0642[4]   ; Loop until all params read
    tya                                                               ; 95a9: 98          .   :0644[4]   ; Restore OSWORD number from Y
; &95aa referenced 1 time by &0634[4]
.skip_param_read
    ldx #<(tube_osword_pb)                                            ; 95aa: a2 28       .(  :0645[4]   ; XY=&0128: param block address for OSWORD
    ldy #>(tube_osword_pb)                                            ; 95ac: a0 01       ..  :0647[4]   ; Y=&01: param block at &0128
    jsr osword                                                        ; 95ae: 20 f1 ff     .. :0649[4]   ; Execute OSWORD with XY=&0128
; &95b1 referenced 1 time by &064f[4]
.poll_r2_osword_result
    bit tube_status_register_2                                        ; 95b1: 2c e2 fe    ,.. :064c[4]   ; Poll R2 status for ready
    bpl poll_r2_osword_result                                         ; 95b4: 10 fb       ..  :064f[4]   ; Not ready: keep polling
    ldx tube_data_register_2                                          ; 95b6: ae e3 fe    ... :0651[4]   ; Read result block length from R2
    dex                                                               ; 95b9: ca          .   :0654[4]   ; Decrement result byte counter
    bmi tube_return_main                                              ; 95ba: 30 0e       0.  :0655[4]   ; No results to send: return to main loop
; &95bc referenced 1 time by &0663[4]
.tube_osword_write
    ldy tube_osword_pb,x                                              ; 95bc: bc 28 01    .(. :0657[4]   ; Send result block bytes from &0128 via R2
; &95bf referenced 1 time by &065d[4]
.tube_osword_write_lp
    bit tube_status_register_2                                        ; 95bf: 2c e2 fe    ,.. :065a[4]   ; Poll R2 status for ready
    bvc tube_osword_write_lp                                          ; 95c2: 50 fb       P.  :065d[4]   ; Not ready: keep polling
    sty tube_data_register_2                                          ; 95c4: 8c e3 fe    ... :065f[4]   ; Send result byte via R2
    dex                                                               ; 95c7: ca          .   :0662[4]   ; Next result byte (descending)
    bpl tube_osword_write                                             ; 95c8: 10 f2       ..  :0663[4]   ; Loop until all results sent
; &95ca referenced 1 time by &0655[4]
.tube_return_main
    jmp tube_main_loop                                                ; 95ca: 4c 36 00    L6. :0665[4]   ; Return to main event loop

; ***************************************************************************************
; Tube OSWORD 0 handler (R2 cmd 5)
; 
; Handles OSWORD 0 (read line) specially. Reads
; 4 parameter bytes from R2 into &0128 (max length,
; min char, max char, flags). Calls OSWORD 0 (&FFF1)
; to read a line, then sends &7F+CR or the input line
; byte-by-byte via R2, followed by &80 (error/escape)
; or &7F (success).
; ***************************************************************************************
.tube_osword_rdln
    ldx #4                                                            ; 95cd: a2 04       ..  :0668[4]   ; Read 5-byte OSWORD 0 control block from R2
; &95cf referenced 1 time by &0670[4]
.read_rdln_ctrl_block
    jsr tube_read_r2                                                  ; 95cf: 20 c5 06     .. :066a[4]   ; Read control block byte from R2
    sta zp_ptr_lo,x                                                   ; 95d2: 95 00       ..  :066d[4]   ; Store in zero page params
    dex                                                               ; 95d4: ca          .   :066f[4]   ; Next byte (descending)
    bpl read_rdln_ctrl_block                                          ; 95d5: 10 f8       ..  :0670[4]   ; Loop until all 5 bytes read
    inx                                                               ; 95d7: e8          .   :0672[4]   ; X=0 after loop, A=0 for OSWORD 0 (read line)
    ldy #0                                                            ; 95d8: a0 00       ..  :0673[4]   ; Y=0 for OSWORD 0
    txa                                                               ; 95da: 8a          .   :0675[4]   ; A=0: OSWORD 0 (read line)
    jsr osword                                                        ; 95db: 20 f1 ff     .. :0676[4]   ; Read input line from keyboard
    bcc tube_rdln_send_line                                           ; 95de: 90 05       ..  :0679[4]   ; C=0: line read OK; C=1: escape pressed
    lda #&ff                                                          ; 95e0: a9 ff       ..  :067b[4]   ; &FF = escape/error signal to co-processor
    jmp tube_reply_byte                                               ; 95e2: 4c 9e 05    L.. :067d[4]   ; Escape: send &FF error to co-processor

; &95e5 referenced 1 time by &0679[4]
.tube_rdln_send_line
    ldx #0                                                            ; 95e5: a2 00       ..  :0680[4]   ; X=0: start of input buffer at &0700
    lda #&7f                                                          ; 95e7: a9 7f       ..  :0682[4]   ; &7F = line read successfully
    jsr tube_send_r2                                                  ; 95e9: 20 95 06     .. :0684[4]   ; Send &7F (success) to co-processor
; &95ec referenced 1 time by &0690[4]
.tube_rdln_send_loop
    lda string_buf,x                                                  ; 95ec: bd 00 07    ... :0687[4]   ; Load char from input buffer
.tube_rdln_send_byte
    jsr tube_send_r2                                                  ; 95ef: 20 95 06     .. :068a[4]   ; Send char to co-processor
    inx                                                               ; 95f2: e8          .   :068d[4]   ; Next character
    cmp #&0d                                                          ; 95f3: c9 0d       ..  :068e[4]   ; Check for CR terminator
    bne tube_rdln_send_loop                                           ; 95f5: d0 f5       ..  :0690[4]   ; Loop until CR terminator sent
    jmp tube_main_loop                                                ; 95f7: 4c 36 00    L6. :0692[4]   ; Return to main event loop

; ***************************************************************************************
; Send byte to Tube data register R2
; 
; Polls Tube status register 2 until bit 6 (TDRA)
; is set, then writes A to the data register. Uses a
; tight BIT/BVC polling loop. Called by 12 sites
; across the Tube host code for all R2 data
; transmission: command responses, file data, OSBYTE
; results, and control block bytes.
; ***************************************************************************************
; &95fa referenced 14 times by &0020[1], &0026[1], &002c[1], &0474[2], &053b[3], &0572[3], &0579[3], &05c2[3], &05c9[3], &05e8[3], &061a[4], &0684[4], &068a[4], &0698[4]
.tube_send_r2
    bit tube_status_register_2                                        ; 95fa: 2c e2 fe    ,.. :0695[4]   ; Poll R2 status (bit 6 = ready)
    bvc tube_send_r2                                                  ; 95fd: 50 fb       P.  :0698[4]   ; Not ready: keep polling
    sta tube_data_register_2                                          ; 95ff: 8d e3 fe    ... :069a[4]   ; Write A to Tube R2 data register
    rts                                                               ; 9602: 60          `   :069d[4]   ; Return to caller

; ***************************************************************************************
; Send byte to Tube data register R4
; 
; Polls Tube status register 4 until bit 6 is set,
; then writes A to the data register. Uses a tight
; BIT/BVC polling loop. R4 is the command/control
; channel used for address claims (ADRR), data transfer
; setup (SENDW), and release commands. Called by 7
; sites, primarily during tube_release_claim and
; tube_transfer_setup sequences.
; ***************************************************************************************
; &9603 referenced 8 times by &0018[1], &0418[2], &041d[2], &043b[2], &0443[2], &0448[2], &0463[2], &06a1[4]
.tube_send_r4
    bit tube_status_register_4_and_cpu_control                        ; 9603: 2c e6 fe    ,.. :069e[4]   ; Poll R4 status (bit 6 = ready)
    bvc tube_send_r4                                                  ; 9606: 50 fb       P.  :06a1[4]   ; Not ready: keep polling
    sta tube_data_register_4                                          ; 9608: 8d e7 fe    ... :06a3[4]   ; Write A to Tube R4 data register
    rts                                                               ; 960b: 60          `   :06a6[4]   ; Return to caller

; &960c referenced 1 time by &0403[2]
.tube_escape_check
    lda escape_flag                                                   ; 960c: a5 ff       ..  :06a7[4]   ; Check OS escape flag at &FF
    sec                                                               ; 960e: 38          8   :06a9[4]   ; SEC+ROR: put bit 7 of &FF into carry+bit 7
    ror a                                                             ; 960f: 6a          j   :06aa[4]   ; ROR: shift escape bit 7 to carry
    bmi tube_send_r1                                                  ; 9610: 30 0f       0.  :06ab[4]   ; Escape set: forward to co-processor via R1
.tube_event_handler
    pha                                                               ; 9612: 48          H   :06ad[4]   ; EVNTV: forward event A, Y, X to co-processor
    lda #0                                                            ; 9613: a9 00       ..  :06ae[4]   ; Send &00 prefix (event notification)
    jsr tube_send_r1                                                  ; 9615: 20 bc 06     .. :06b0[4]   ; Send zero prefix via R1
    tya                                                               ; 9618: 98          .   :06b3[4]   ; Y value for event
    jsr tube_send_r1                                                  ; 9619: 20 bc 06     .. :06b4[4]   ; Send Y via R1
    txa                                                               ; 961c: 8a          .   :06b7[4]   ; X value for event
    jsr tube_send_r1                                                  ; 961d: 20 bc 06     .. :06b8[4]   ; Send X via R1
    pla                                                               ; 9620: 68          h   :06bb[4]   ; Restore A (event type)
; ***************************************************************************************
; Send byte to Tube data register R1
; 
; Polls Tube status register 1 until bit 6 is set,
; then writes A to the data register. Uses a tight
; BIT/BVC polling loop. R1 is used for asynchronous
; event and escape notification to the co-processor.
; Called by tube_event_handler to forward event type,
; Y, and X parameters, and reached via BMI from
; tube_escape_check when the escape flag is set.
; ***************************************************************************************
; &9621 referenced 5 times by &06ab[4], &06b0[4], &06b4[4], &06b8[4], &06bf[4]
.tube_send_r1
    bit tube_status_1_and_tube_control                                ; 9621: 2c e0 fe    ,.. :06bc[4]   ; Poll R1 status (bit 6 = ready)
    bvc tube_send_r1                                                  ; 9624: 50 fb       P.  :06bf[4]   ; Not ready: keep polling
    sta tube_data_register_1                                          ; 9626: 8d e1 fe    ... :06c1[4]   ; Write A to Tube R1 data register
    rts                                                               ; 9629: 60          `   :06c4[4]   ; Return to caller

; ***************************************************************************************
; Read a byte from Tube data register R2
; 
; Polls Tube status register 2 until data is available
; (bit 7 set), then loads A from Tube data register 2.
; Called by all Tube dispatch handlers that receive data
; or parameters from the co-processor.
; ***************************************************************************************
; &962a referenced 21 times by &0520[3], &0524[3], &052d[3], &0542[3], &0552[3], &055e[3], &0564[3], &056c[3], &0586[3], &05ab[3], &05bc[3], &05d3[3], &05db[3], &05f2[3], &05f6[3], &0607[4], &060b[4], &060f[4], &0627[4], &066a[4], &06c8[4]
.tube_read_r2
    bit tube_status_register_2                                        ; 962a: 2c e2 fe    ,.. :06c5[4]   ; Poll R2 status (bit 7 = ready)
    bpl tube_read_r2                                                  ; 962d: 10 fb       ..  :06c8[4]   ; Not ready: keep polling
    lda tube_data_register_2                                          ; 962f: ad e3 fe    ... :06ca[4]   ; Read data byte from R2
    rts                                                               ; 9632: 60          `   :06cd[4]   ; Return with byte in A

    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; 9633: ff ff ff... ... :06ce[4]   ; &FF padding (29 bytes before trampolines)
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; 963f: ff ff ff... ... :06da[4]
    equb &ff, &ff, &ff, &ff, &ff                                      ; 964b: ff ff ff... ... :06e6[4]

.trampoline_tx_setup
    jmp tx_begin                                                      ; 9650: 4c 90 9b    L.. :06eb[4]   ; Trampoline: begin TX operation

.trampoline_adlc_init
    jmp adlc_init                                                     ; 9653: 4c 9a 96    L.. :06ee[4]   ; Trampoline: full ADLC init

.svc_12_nmi_release
    jmp wait_idle_and_reset                                           ; 9656: 4c 8a 9f    L.. :06f1[4]   ; Trampoline: wait idle and reset

.svc_11_nmi_claim
    jmp init_nmi_workspace                                            ; 9659: 4c b8 96    L.. :06f4[4]   ; Trampoline: init NMI workspace

    lda #4                                                            ; 965c: a9 04       ..  :06f7[4]   ; A=4: SR interrupt bit mask
    bit system_via_ifr                                                ; 965e: 2c 4d fe    ,M. :06f9[4]   ; Test SR flag in VIA IFR
    bne l0701                                                         ; 9661: d0 03       ..  :06fc[4]   ; SR active: handle interrupt
    lda #5                                                            ; 9663: a9 05       ..  :06fe[4]   ; A=5: NMI not for us

    ; Copy the newly assembled block of code back to it's proper place in the binary
    ; file.
    ; (Note the parameter order: 'copyblock <start>,<end>,<dest>')
    copyblock tube_page6_start, *, reloc_p6_src

    ; Clear the area of memory we just temporarily used to assemble the new block,
    ; allowing us to assemble there again if needed
    clear tube_page6_start, &0700

    ; Set the program counter to the next position in the binary file.
    org reloc_p6_src + (* - tube_page6_start)


    org &8000

; Sideways ROM header
; NFS ROM 3.65 disassembly (Acorn Econet filing system)
; ====================================================
; &8000 referenced 2 times by &04e6[2], &9b64
.pydis_start
.rom_header
.language_entry
language_handler_lo = rom_header+1
language_handler_hi = rom_header+2
    jmp language_handler                                              ; 8000: 4c dd 80    L..            ; JMP language_handler

; &8001 referenced 1 time by &04eb[2]
; &8002 referenced 1 time by &04f0[2]
; &8003 referenced 1 time by &04f5[2]
.service_entry
service_handler_lo = service_entry+1
    jmp service_handler                                               ; 8003: 4c f3 80    L..            ; JMP service_handler

; &8004 referenced 1 time by &04f8[2]
; &8006 referenced 1 time by &04da[2]
.rom_type
    equb &82                                                          ; 8006: 82          .              ; ROM type: service + language
; &8007 referenced 1 time by &04e2[2]
.copyright_offset
    equb copyright - rom_header                                       ; 8007: 0c          .              ; Copyright string offset from &8000
; &8008 referenced 2 times by &835c, &8365
.binary_version
    equb 3                                                            ; 8008: 03          .              ; Binary version number
.title
    equs "NET"                                                        ; 8009: 4e 45 54    NET            ; ROM title string "NET"
.copyright
    equb 0                                                            ; 800c: 00          .              ; Null terminator before copyright
; The 'ROFF' suffix at &8014 is reused by the *ROFF
; command matcher (svc_star_command) — a space-saving
; trick that shares ROM bytes between the copyright
; string and the star command table.
.copyright_string
    equs "(C)ROFF"                                                    ; 800d: 28 43 29... (C)            ; Copyright string "(C)ROFF"
; Error message offset table (9 entries).
; Each byte is a Y offset into error_msg_table.
; Entry 0 (Y=0, "Line Jammed") doubles as the
; copyright string null terminator.
; Indexed by TXCB status (AND #7), or hardcoded 8.
; &8014 referenced 1 time by &8503
.error_offsets
    equb 0                                                            ; 8014: 00          .              ; "Line Jammed"
    equb &0d                                                          ; 8015: 0d          .              ; "Net Error"
    equb &18                                                          ; 8016: 18          .              ; "Not listening"
    equb &27                                                          ; 8017: 27          '              ; "No Clock"
    equb &31                                                          ; 8018: 31          1              ; "Escape"
    equb &31                                                          ; 8019: 31          1              ; "Escape"
    equb &31                                                          ; 801a: 31          1              ; "Escape"
    equb &39                                                          ; 801b: 39          9              ; "Bad Option"
    equb &45                                                          ; 801c: 45          E              ; "No reply"
; Four bytes with unknown purpose.
    equb 1                                                            ; 801d: 01          .              ; Purpose unknown
    equb 0                                                            ; 801e: 00          .              ; Purpose unknown
    equb &65                                                          ; 801f: 65          e              ; Purpose unknown
; &8020 referenced 1 time by &80ec
    equb 3                                                            ; 8020: 03          .              ; Purpose unknown
; Dispatch table: low bytes of (handler_address - 1)
; Each entry stores the low byte of a handler address minus 1,
; for use with the PHA/PHA/RTS dispatch trick at &80E7.
; See dispatch_0_hi (&804A) for the corresponding high bytes.
; 
; Five callers share this table via different Y base offsets:
;   Y=&00  Service calls 0-12       (indices 0-13)
;   Y=&0E  Language entry reasons    (indices 14-18)
;   Y=&13  FSCV codes 0-7           (indices 19-26)
;   Y=&17  FS reply handlers        (indices 27-32)
;   Y=&21  *NET1-4 sub-commands     (indices 33-36)
; 
; Lo bytes for the last 6 entries (indices 31-36) occupy
; &8040-&8045, immediately before the hi bytes. Their hi
; bytes are at &8065-&806A, after dispatch_0_hi.
.dispatch_0_lo
    equb <(return_1-1)                                                ; 8021: f1          .              ; lo - Svc 0: already claimed (no-op)
    equb <(svc_1_abs_workspace-1)                                     ; 8022: a9          .              ; lo - Svc 1: absolute workspace
    equb <(svc_2_private_workspace-1)                                 ; 8023: b2          .              ; lo - Svc 2: private workspace
    equb <(svc_3_autoboot-1)                                          ; 8024: 0a          .              ; lo - Svc 3: auto-boot
    equb <(svc_4_star_command-1)                                      ; 8025: a2          .              ; lo - Svc 4: unrecognised star command
    equb <(svc5_irq_check-1)                                          ; 8026: 5b          [              ; lo - Svc 5: unrecognised interrupt
    equb <(return_1-1)                                                ; 8027: f1          .              ; lo - Svc 6: BRK (no-op)
    equb <(dispatch_net_cmd-1)                                        ; 8028: 6a          j              ; lo - Svc 7: unrecognised OSBYTE
    equb <(svc_8_osword-1)                                            ; 8029: 89          .              ; lo - Svc 8: unrecognised OSWORD
    equb <(svc_9_help-1)                                              ; 802a: f5          .              ; lo - Svc 9: *HELP
    equb <(return_1-1)                                                ; 802b: f1          .              ; lo - Svc 10: static workspace (no-op)
    equb <(econet_restore-1)                                          ; 802c: 58          X              ; lo - Svc 11: NMI release (reclaim NMIs)
    equb <(econet_save-1)                                             ; 802d: 55          U              ; lo - Svc 12: NMI claim (save NMI state)
    equb <(svc_13_select_nfs-1)                                       ; 802e: de          .              ; lo - Svc 13: select NFS (intercepted before dispatch)
    equb <(lang_0_insert_remote_key-1)                                ; 802f: ea          .              ; lo - Lang 0: no language / Tube
    equb <(lang_1_remote_boot-1)                                      ; 8030: 9c          .              ; lo - Lang 1: normal startup
    equb <(lang_2_save_palette_vdu-1)                                 ; 8031: ad          .              ; lo - Lang 2: softkey byte (Electron)
    equb <(lang_3_execute_at_0100-1)                                  ; 8032: ca          .              ; lo - Lang 3: softkey length (Electron)
    equb <(lang_4_remote_validated-1)                                 ; 8033: da          .              ; lo - Lang 4: remote validated
    equb <(fscv_0_opt_entry-1)                                        ; 8034: 19          .              ; lo - FSCV 0: *OPT
    equb <(fscv_1_eof-1)                                              ; 8035: 9a          .              ; lo - FSCV 1: EOF check
    equb <(fscv_2_star_run-1)                                         ; 8036: de          .              ; lo - FSCV 2: */ (run)
    equb <(fscv_3_star_cmd-1)                                         ; 8037: 08          .              ; lo - FSCV 3: unrecognised star command
    equb <(fscv_2_star_run-1)                                         ; 8038: de          .              ; lo - FSCV 4: *RUN
    equb <(fscv_5_cat-1)                                              ; 8039: 54          T              ; lo - FSCV 5: *CAT
    equb <(fscv_6_shutdown-1)                                         ; 803a: 3e          >              ; lo - FSCV 6: shutdown
    equb <(fscv_7_read_handles-1)                                     ; 803b: b8          .              ; lo - FSCV 7: read handle range
    equb <(fsreply_0_print_dir-1)                                     ; 803c: 83          .              ; lo - FS reply: print directory name
    equb <(fsreply_1_copy_handles_boot-1)                             ; 803d: 3a          :              ; lo - FS reply: copy handles + boot
    equb <(fsreply_2_copy_handles-1)                                  ; 803e: 3b          ;              ; lo - FS reply: copy handles
    equb <(fsreply_3_set_csd-1)                                       ; 803f: 34          4              ; lo - FS reply: set CSD handle
    equb <(fsreply_4_notify_exec-1)                                   ; 8040: e4          .              ; lo - FS reply: notify + execute
    equb <(fsreply_5_set_lib-1)                                       ; 8041: 2f          /              ; lo - FS reply: set library handle
    equb <(net_1_read_handle-1)                                       ; 8042: 69          i              ; lo - *NET1: read handle from packet
    equb <(net_2_read_handle_entry-1)                                 ; 8043: 6f          o              ; lo - *NET2: read handle from workspace
    equb <(net_3_close_handle-1)                                      ; 8044: 7f          .              ; lo - *NET3: close handle
; &8045 referenced 1 time by &80e8
    equb <(net_4_resume_remote-1)                                     ; 8045: a9          .              ; lo - *NET4: resume remote
.dispatch_0_hi
    equb >(return_1-1)                                                ; 8046: 80          .              ; hi - Svc 0: already claimed (no-op)
    equb >(svc_1_abs_workspace-1)                                     ; 8047: 82          .              ; hi - Svc 1: absolute workspace
    equb >(svc_2_private_workspace-1)                                 ; 8048: 82          .              ; hi - Svc 2: private workspace
    equb >(svc_3_autoboot-1)                                          ; 8049: 82          .              ; hi - Svc 3: auto-boot
    equb >(svc_4_star_command-1)                                      ; 804a: 81          .              ; hi - Svc 4: unrecognised star command
    equb >(svc5_irq_check-1)                                          ; 804b: 96          .              ; hi - Svc 5: unrecognised interrupt
    equb >(return_1-1)                                                ; 804c: 80          .              ; hi - Svc 6: BRK (no-op)
    equb >(dispatch_net_cmd-1)                                        ; 804d: 80          .              ; hi - Svc 7: unrecognised OSBYTE
    equb >(svc_8_osword-1)                                            ; 804e: 8e          .              ; hi - Svc 8: unrecognised OSWORD
    equb >(svc_9_help-1)                                              ; 804f: 81          .              ; hi - Svc 9: *HELP
    equb >(return_1-1)                                                ; 8050: 80          .              ; hi - Svc 10: static workspace (no-op)
    equb >(econet_restore-1)                                          ; 8051: 96          .              ; hi - Svc 11: NMI release (reclaim NMIs)
    equb >(econet_save-1)                                             ; 8052: 96          .              ; hi - Svc 12: NMI claim (save NMI state)
    equb >(svc_13_select_nfs-1)                                       ; 8053: 81          .              ; hi - Svc 13: select NFS (intercepted before dispatch)
    equb >(lang_0_insert_remote_key-1)                                ; 8054: 84          .              ; hi - Lang 0: no language / Tube
    equb >(lang_1_remote_boot-1)                                      ; 8055: 84          .              ; hi - Lang 1: normal startup
    equb >(lang_2_save_palette_vdu-1)                                 ; 8056: 92          .              ; hi - Lang 2: softkey byte (Electron)
    equb >(lang_3_execute_at_0100-1)                                  ; 8057: 84          .              ; hi - Lang 3: softkey length (Electron)
    equb >(lang_4_remote_validated-1)                                 ; 8058: 84          .              ; hi - Lang 4: remote validated
    equb >(fscv_0_opt_entry-1)                                        ; 8059: 8a          .              ; hi - FSCV 0: *OPT
    equb >(fscv_1_eof-1)                                              ; 805a: 88          .              ; hi - FSCV 1: EOF check
    equb >(fscv_2_star_run-1)                                         ; 805b: 8d          .              ; hi - FSCV 2: */ (run)
    equb >(fscv_3_star_cmd-1)                                         ; 805c: 8c          .              ; hi - FSCV 3: unrecognised star command
    equb >(fscv_2_star_run-1)                                         ; 805d: 8d          .              ; hi - FSCV 4: *RUN
    equb >(fscv_5_cat-1)                                              ; 805e: 8c          .              ; hi - FSCV 5: *CAT
    equb >(fscv_6_shutdown-1)                                         ; 805f: 83          .              ; hi - FSCV 6: shutdown
    equb >(fscv_7_read_handles-1)                                     ; 8060: 86          .              ; hi - FSCV 7: read handle range
    equb >(fsreply_0_print_dir-1)                                     ; 8061: 8d          .              ; hi - FS reply: print directory name
    equb >(fsreply_1_copy_handles_boot-1)                             ; 8062: 8e          .              ; hi - FS reply: copy handles + boot
    equb >(fsreply_2_copy_handles-1)                                  ; 8063: 8e          .              ; hi - FS reply: copy handles
    equb >(fsreply_3_set_csd-1)                                       ; 8064: 8e          .              ; hi - FS reply: set CSD handle
    equb >(fsreply_4_notify_exec-1)                                   ; 8065: 8d          .              ; hi - FS reply: notify + execute
    equb >(fsreply_5_set_lib-1)                                       ; 8066: 8e          .              ; hi - FS reply: set library handle
    equb >(net_1_read_handle-1)                                       ; 8067: 8e          .              ; hi - *NET1: read handle from packet
    equb >(net_2_read_handle_entry-1)                                 ; 8068: 8e          .              ; hi - *NET2: read handle from workspace
    equb >(net_3_close_handle-1)                                      ; 8069: 8e          .              ; hi - *NET3: close handle
    equb >(net_4_resume_remote-1)                                     ; 806a: 81          .              ; hi - *NET4: resume remote

; ***************************************************************************************
; *NET command dispatcher
; 
; Parses the character after *NET as '1'-'4', maps to table
; indices 33-36 via base offset Y=&21, and dispatches via &80E3.
; Characters outside '1'-'4' fall through to return_1 (RTS).
; 
; These are internal sub-commands used only by the ROM itself,
; not user-accessible star commands. The MOS command parser
; requires a space or terminator after 'NET', so *NET1 typed
; at the command line does not match; these are reached only
; via OSCLI calls within the ROM.
; 
; *NET1 (&8E6A): read file handle from received
; packet (net_1_read_handle)
; 
; *NET2 (&8E70): read handle entry from workspace
; (net_2_read_handle_entry)
; 
; *NET3 (&8E80): close handle / mark as unused
; (net_3_close_handle)
; 
; *NET4 (&81AA): resume after remote operation
; (net_4_resume_remote)
; ***************************************************************************************
.dispatch_net_cmd
    lda osbyte_a_copy                                                 ; 806b: a5 ef       ..             ; Read command character following *NET
    sbc #&31 ; '1'                                                    ; 806d: e9 31       .1             ; Subtract ASCII '1' to get 0-based command index
    cmp #4                                                            ; 806f: c9 04       ..             ; Command index >= 4: invalid *NET sub-command
    bcs svc_dispatch_range                                            ; 8071: b0 6c       .l             ; Out of range: return via c80e3/RTS
    tax                                                               ; 8073: aa          .              ; X = command index (0-3)
    lda #0                                                            ; 8074: a9 00       ..             ; Clear &A9 (used by dispatch)
    sta svc_state                                                     ; 8076: 85 a9       ..             ; Store zero to &A9
    tya                                                               ; 8078: 98          .              ; Preserve A before dispatch
    ldy #&21 ; '!'                                                    ; 8079: a0 21       .!             ; Y=&21: base offset for *NET commands (index 33+)
    bne dispatch                                                      ; 807b: d0 66       .f             ; ALWAYS branch to dispatch; ALWAYS branch

; &807d referenced 1 time by &8082
.skip_cmd_spaces
    iny                                                               ; 807d: c8          .              ; Advance past matched command text
; ***************************************************************************************
; "I AM" command handler
; 
; Dispatched from the command match table when the user types
; "*I AM <station>" or "*I AM <network>.<station>". Also used as
; the station number parser for "*NET <network>.<station>".
; Skips leading spaces, then calls parse_decimal for the first
; number. If a dot separator was found (carry set), it stores the
; result directly as the network (&0E01) and calls parse_decimal
; again for the station (&0E00). With a single number, it is stored
; as the station and the network defaults to 0 (local). If a colon
; follows, reads interactive input via OSRDCH and appends it to
; the command buffer. Finally jumps to forward_star_cmd.
; ***************************************************************************************
.i_am_handler
    lda (fs_options),y                                                ; 807e: b1 bb       ..             ; Load next char from command line
    cmp #&20 ; ' '                                                    ; 8080: c9 20       .              ; Skip spaces
    beq skip_cmd_spaces                                               ; 8082: f0 f9       ..             ; Loop back to skip leading spaces
    cmp #&3a ; ':'                                                    ; 8084: c9 3a       .:             ; Colon = interactive remote command prefix
    bcs skip_stn_parse                                                ; 8086: b0 11       ..             ; Char >= ':': skip number parsing
    jsr parse_decimal                                                 ; 8088: 20 65 86     e.            ; Parse decimal number from (fs_options),Y (DECIN)
    bcc got_station_num                                               ; 808b: 90 07       ..             ; C=1: dot found, first number was network
    sta fs_server_net                                                 ; 808d: 8d 01 0e    ...            ; Store network number (n.s = network.station); A=parsed value (accumulated in &B2)
    iny                                                               ; 8090: c8          .              ; Y=offset into (fs_options) buffer
    jsr parse_decimal                                                 ; 8091: 20 65 86     e.            ; Parse decimal number from (fs_options),Y (DECIN)
; &8094 referenced 1 time by &808b
.got_station_num
    beq skip_stn_parse                                                ; 8094: f0 03       ..             ; Z=1: no station parsed (empty or non-numeric)
    sta fs_server_stn                                                 ; 8096: 8d 00 0e    ...            ; A=parsed value (accumulated in &B2)
; &8099 referenced 2 times by &8086, &8094
.skip_stn_parse
    jsr infol2                                                        ; 8099: 20 70 8d     p.            ; Copy command text to FS buffer
; &809c referenced 2 times by &80a4, &80bb
.scan_for_colon
    dey                                                               ; 809c: 88          .              ; Scan backward for ':' (interactive prefix)
    beq prepare_cmd_dispatch                                          ; 809d: f0 22       ."             ; Y=0: no colon found, send command
    lda fs_cmd_data,y                                                 ; 809f: b9 05 0f    ...            ; Read char from FS command buffer
    cmp #&3a ; ':'                                                    ; 80a2: c9 3a       .:             ; Test for colon separator
    bne scan_for_colon                                                ; 80a4: d0 f6       ..             ; Not colon: keep scanning backward
    jsr oswrch                                                        ; 80a6: 20 ee ff     ..            ; Echo colon, then read user input from keyboard; Write character
; &80a9 referenced 1 time by &80b6
.read_remote_cmd_line
    jsr check_escape                                                  ; 80a9: 20 8f 84     ..            ; Check for escape condition
    jsr osrdch                                                        ; 80ac: 20 e0 ff     ..            ; Test escape flag before FS reply; Read a character from the current input stream
    sta fs_cmd_data,y                                                 ; 80af: 99 05 0f    ...            ; Append typed character to command buffer; A=character read
    iny                                                               ; 80b2: c8          .              ; Advance write pointer
    inx                                                               ; 80b3: e8          .              ; Increment character count
    cmp #&0d                                                          ; 80b4: c9 0d       ..             ; Test for CR (end of line)
    bne read_remote_cmd_line                                          ; 80b6: d0 f1       ..             ; Not CR: continue reading input
    jsr osnewl                                                        ; 80b8: 20 e7 ff     ..            ; Write newline (characters 10 and 13)
    bne scan_for_colon                                                ; 80bb: d0 df       ..             ; After OSNEWL: loop back to scan for colon
; ***************************************************************************************
; Forward unrecognised * command to fileserver (COMERR)
; 
; Copies command text from (fs_crc_lo) to &0F05+ via copy_filename,
; prepares an FS command with function code 0, and sends it to the
; fileserver to request decoding. The server returns a command code
; indicating what action to take (e.g. code 4=INFO, 7=DIR, 9=LIB,
; 5=load-as-command). This mechanism allows the fileserver to extend
; the client's command set without ROM updates. Called from the "I."
; and catch-all entries in the command match table at &8C4B, and
; from FSCV 2/3/4 indirectly. If CSD handle is zero (not logged
; in), returns without sending.
; ***************************************************************************************
.forward_star_cmd
    jsr infol2                                                        ; 80bd: 20 70 8d     p.            ; Copy command text to FS buffer
    tay                                                               ; 80c0: a8          .              ; Y=function code for HDRFN
; &80c1 referenced 1 time by &809d
.prepare_cmd_dispatch
    jsr prepare_fs_cmd                                                ; 80c1: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    ldx fs_cmd_csd                                                    ; 80c4: ae 03 0f    ...            ; X=depends on function
    beq return_1                                                      ; 80c7: f0 29       .)             ; CSD handle zero: not logged in
    lda fs_cmd_data                                                   ; 80c9: ad 05 0f    ...            ; A=function code (0-7)
    ldy #&17                                                          ; 80cc: a0 17       ..             ; Y=depends on function
    bne dispatch                                                      ; 80ce: d0 13       ..             ; ALWAYS branch

; ***************************************************************************************
; FSCV dispatch entry
; 
; Entered via the extended vector table when the MOS calls FSCV.
; Stores A/X/Y via save_fscv_args, compares A (function code) against 8,
; and dispatches codes 0-7 via the shared dispatch table at &8024
; with base offset Y=&13 (table indices 20-27).
; Function codes: 0=*OPT, 1=EOF, 2=*/, 3=unrecognised *,
; 4=*RUN, 5=*CAT, 6=shutdown, 7=read handles.
; 
; On Entry:
;     A: function code (0-7)
;     X: depends on function
;     Y: depends on function
; 
; On Exit:
;     A: depends on handler (preserved if A >= 8)
;     X: depends on handler (preserved if A >= 8)
;     Y: depends on handler (preserved if A >= 8)
; ***************************************************************************************
.fscv_handler
    jsr save_fscv_args_with_ptrs                                      ; 80d0: 20 37 86     7.            ; Store A/X/Y in FS workspace
    cmp #8                                                            ; 80d3: c9 08       ..             ; FSCV function >= 8?
    bcs return_1                                                      ; 80d5: b0 1b       ..             ; Function code >= 8? Return (unsupported)
    tax                                                               ; 80d7: aa          .              ; X = function code for dispatch
    tya                                                               ; 80d8: 98          .              ; Save Y (command text ptr hi)
    ldy #&13                                                          ; 80d9: a0 13       ..             ; Y=&13: base offset for FSCV dispatch (indices 20+)
    bne dispatch                                                      ; 80db: d0 06       ..             ; ALWAYS branch

; ***************************************************************************************
; Language entry dispatcher
; 
; Called when the NFS ROM is entered as a language. Although rom_type
; (&82) does not set the language bit, the MOS enters this point
; after NFS claims service &FE (Tube post-init). X = reason code
; (0-4). Dispatches via table indices 15-19 (base offset Y=&0E).
; ***************************************************************************************
; &80dd referenced 1 time by &8000
.language_handler
.lang_entry_dispatch
    cpx #5                                                            ; 80dd: e0 05       ..             ; X >= 5: invalid reason code, return
; &80df referenced 1 time by &8071
.svc_dispatch_range
    bcs return_1                                                      ; 80df: b0 11       ..             ; Out of range: return via RTS
    ldy #&0e                                                          ; 80e1: a0 0e       ..             ; Y=&0E: base offset for language handlers (index 15+)
; ***************************************************************************************
; PHA/PHA/RTS computed dispatch
; 
; X = command index within caller's group (e.g. service number)
; Y = base offset into dispatch table (0, &0E, &13, &21, etc.)
; The loop adds Y+1 to X, so final X = command index + base + 1.
; Then high and low bytes of (handler-1) are pushed onto the stack,
; and RTS pops them and jumps to handler_address.
; 
; This is a standard 6502 trick: RTS increments the popped address
; by 1 before jumping, so the table stores (address - 1) to
; compensate. Multiple callers share one table via different Y
; base offsets.
; ***************************************************************************************
; &80e3 referenced 5 times by &807b, &80ce, &80db, &80e5, &8194
.dispatch
    inx                                                               ; 80e3: e8          .              ; Add base offset Y to index X (loop: X += Y+1)
    dey                                                               ; 80e4: 88          .              ; Decrement base offset counter
    bpl dispatch                                                      ; 80e5: 10 fc       ..             ; Loop until Y exhausted
    tay                                                               ; 80e7: a8          .              ; Y=&FF (no further use)
    lda dispatch_0_hi-1,x                                             ; 80e8: bd 45 80    .E.            ; Load high byte of (handler - 1) from table
    pha                                                               ; 80eb: 48          H              ; Push high byte onto stack
    lda dispatch_0_lo-1,x                                             ; 80ec: bd 20 80    . .            ; Load low byte of (handler - 1) from table
    pha                                                               ; 80ef: 48          H              ; Push low byte onto stack
    ldx fs_options                                                    ; 80f0: a6 bb       ..             ; Restore X (fileserver options) for use by handler
; &80f2 referenced 3 times by &80c7, &80d5, &80df
.return_1
    rts                                                               ; 80f2: 60          `              ; RTS pops address, adds 1, jumps to handler

; &80f3 referenced 1 time by &8003
.service_handler
    pha                                                               ; 80f3: 48          H              ; Save service call number
    cmp #1                                                            ; 80f4: c9 01       ..             ; Only probe ADLC on service 1 (workspace claim)
    bne check_disable_flag                                            ; 80f6: d0 15       ..             ; Not service 1: skip probe
    lda econet_control1_or_status1                                    ; 80f8: ad a0 fe    ...            ; Probe ADLC SR1: non-zero = absent (bus noise)
    and #&ed                                                          ; 80fb: 29 ed       ).             ; Mask SR1 status bits (ignore bits 4,1)
    bne set_adlc_disable                                              ; 80fd: d0 07       ..             ; Non-zero: ADLC absent, set disable flag
    lda econet_control23_or_status2                                   ; 80ff: ad a1 fe    ...            ; Probe ADLC SR2 if SR1 was all zeros
    and #&db                                                          ; 8102: 29 db       ).             ; Mask SR2 status bits (ignore bits 5,2)
    beq check_disable_flag                                            ; 8104: f0 07       ..             ; Both zero: ADLC present, skip
; &8106 referenced 1 time by &80fd
.set_adlc_disable
    rol rom_ws_table,x                                                ; 8106: 3e f0 0d    >..            ; Set bit 7 of per-ROM workspace = disable flag
    sec                                                               ; 8109: 38          8              ; SEC for ROR to set bit 7
    ror rom_ws_table,x                                                ; 810a: 7e f0 0d    ~..            ; Rotate carry into bit 7 of workspace
; &810d referenced 2 times by &80f6, &8104
.check_disable_flag
    lda rom_ws_table,x                                                ; 810d: bd f0 0d    ...            ; Read back flag; ASL puts bit 7 into carry
    asl a                                                             ; 8110: 0a          .              ; C into bit 7 of A
    pla                                                               ; 8111: 68          h              ; Restore service call number
    bmi check_svc_high                                                ; 8112: 30 02       0.             ; Service >= &80: always handle (Tube/init)
    bcs svc_unhandled_return                                          ; 8114: b0 6e       .n             ; C=1 (no ADLC): disable ROM, skip
; ***************************************************************************************
; Service handler entry
; 
; On service 1 only, probes ADLC status registers SR1 (&FEA0)
; and SR2 (&FEA1) to detect whether Econet hardware is present.
; Non-zero reads indicate bus noise from absent hardware; sets
; bit 7 of per-ROM workspace as a disable flag. For services
; < &80, the flag causes an early return (disabling this ROM).
; Services >= &80 (&FE, &FF) are always handled regardless.
; 
; Intercepts three service calls before normal dispatch:
;   &FE: Tube init — explode character definitions
;   &FF: Full init — vector setup, copy code to RAM, select NFS
;   &12 (Y=5): Select NFS as active filing system
; All other service calls < &0D dispatch via c8146.
; ***************************************************************************************
; &8116 referenced 1 time by &8112
.check_svc_high
.service_handler_entry
    cmp #&fe                                                          ; 8116: c9 fe       ..             ; Service >= &FE?
    bcc check_svc_12                                                  ; 8118: 90 5c       .\             ; Service < &FE: skip to &12/dispatch check
    bne init_vectors_and_copy                                         ; 811a: d0 1b       ..             ; Service &FF: full init (vectors + RAM copy)
    cpy #0                                                            ; 811c: c0 00       ..             ; Service &FE: Y=0?
    beq check_svc_12                                                  ; 811e: f0 56       .V             ; Y=0: no Tube data, skip to &12 check
    ldx #6                                                            ; 8120: a2 06       ..             ; X=6 extra pages for char definitions
    lda #osbyte_explode_chars                                         ; 8122: a9 14       ..             ; OSBYTE &14: explode character RAM
    jsr osbyte                                                        ; 8124: 20 f4 ff     ..            ; Explode character definition RAM (six extra pages), can redefine all characters 32-255 (X=6)
; &8127 referenced 2 times by &812a, &8134
.poll_tube_ready
    bit tube_status_1_and_tube_control                                ; 8127: 2c e0 fe    ,..            ; Poll Tube status register 1
    bpl poll_tube_ready                                               ; 812a: 10 fb       ..             ; Loop until Tube ready (bit 7 set)
    lda tube_data_register_1                                          ; 812c: ad e1 fe    ...            ; Read byte from Tube data register 1
    beq tube_chars_done                                               ; 812f: f0 43       .C             ; Zero byte: Tube transfer complete
    jsr oswrch                                                        ; 8131: 20 ee ff     ..            ; Send Tube char to screen via OSWRCH; Write character
    jmp poll_tube_ready                                               ; 8134: 4c 27 81    L'.            ; Loop for next Tube byte

; &8137 referenced 1 time by &811a
.init_vectors_and_copy
    lda #&ad                                                          ; 8137: a9 ad       ..             ; EVNTV low = &AD (event handler address)
    sta evntv                                                         ; 8139: 8d 20 02    . .            ; Set EVNTV low byte at &0220
    lda #6                                                            ; 813c: a9 06       ..             ; EVNTV high = &06 (page 6)
    sta evntv+1                                                       ; 813e: 8d 21 02    .!.            ; Set EVNTV high byte at &0221
    lda #&16                                                          ; 8141: a9 16       ..             ; BRKV low = &16 (NMI workspace)
    sta brkv                                                          ; 8143: 8d 02 02    ...            ; Set BRKV low byte at &0202
    lda #0                                                            ; 8146: a9 00       ..             ; BRKV high = &00 (zero page)
    sta brkv+1                                                        ; 8148: 8d 03 02    ...            ; Set BRKV high byte at &0203
    lda #&8e                                                          ; 814b: a9 8e       ..             ; Tube control register init value &8E
    sta tube_status_1_and_tube_control                                ; 814d: 8d e0 fe    ...            ; Write to Tube control register
    ldy #0                                                            ; 8150: a0 00       ..             ; Y=0: copy 256 bytes per page
; Copy NMI handler code from ROM to RAM pages &04-&06
; &8152 referenced 1 time by &8165
.cloop
    lda reloc_p4_src,y                                                ; 8152: b9 65 93    .e.            ; Load ROM byte from page &93
    sta tube_code_page4,y                                             ; 8155: 99 00 04    ...            ; Store to page &04 (Tube code)
    lda reloc_p5_src,y                                                ; 8158: b9 65 94    .e.            ; Load ROM byte from page &94
    sta tube_dispatch_table,y                                         ; 815b: 99 00 05    ...            ; Store to page &05 (dispatch table)
    lda reloc_p6_src,y                                                ; 815e: b9 65 95    .e.            ; Load ROM byte from page &95
    sta tube_page6_start,y                                            ; 8161: 99 00 06    ...            ; Store to page &06
    dey                                                               ; 8164: 88          .              ; DEY wraps 0 -> &FF on first iteration
    bne cloop                                                         ; 8165: d0 eb       ..             ; Loop until 256 bytes copied per page
    jsr tube_post_init                                                ; 8167: 20 21 04     !.            ; Run post-init routine in copied code
    ldx #&60 ; '`'                                                    ; 816a: a2 60       .`             ; X=&60: copy 97 bytes (&60..&00)
; Copy NMI workspace initialiser from ROM to &0016-&0076
; &816c referenced 1 time by &8172
.copy_nmi_workspace
    lda reloc_zp_src,x                                                ; 816c: bd 24 93    .$.            ; Load NMI workspace init byte from ROM
    sta nmi_workspace_start,x                                         ; 816f: 95 16       ..             ; Store to zero page &16+X
    dex                                                               ; 8171: ca          .              ; Next byte
    bpl copy_nmi_workspace                                            ; 8172: 10 f8       ..             ; Loop until all workspace bytes copied
; &8174 referenced 1 time by &812f
.tube_chars_done
    lda #0                                                            ; 8174: a9 00       ..             ; A=0: fall through to service &12 check
; &8176 referenced 2 times by &8118, &811e
.check_svc_12
    cmp #&12                                                          ; 8176: c9 12       ..             ; Is this service &12 (select FS)?
    bne not_svc_12_nfs                                                ; 8178: d0 08       ..             ; No: check if service < &0D
    cpy #5                                                            ; 817a: c0 05       ..             ; Service &12: Y=5 (NFS)?
    bne not_svc_12_nfs                                                ; 817c: d0 04       ..             ; Not NFS: check if service < &0D
    lda #&0d                                                          ; 817e: a9 0d       ..             ; A=&0D: dispatch index for svc_13_select_nfs
    bne do_svc_dispatch                                               ; 8180: d0 04       ..             ; ALWAYS branch to dispatch; ALWAYS branch

; &8182 referenced 2 times by &8178, &817c
.not_svc_12_nfs
    cmp #&0d                                                          ; 8182: c9 0d       ..             ; Service >= &0D?
; &8184 referenced 1 time by &8114
.svc_unhandled_return
    bcs return_2                                                      ; 8184: b0 1c       ..             ; Service >= &0D: not handled, return
; &8186 referenced 1 time by &8180
.do_svc_dispatch
    tax                                                               ; 8186: aa          .              ; X = service number (dispatch index)
    lda svc_state                                                     ; 8187: a5 a9       ..             ; Save &A9 (current service state)
    pha                                                               ; 8189: 48          H              ; Push saved &A9
    lda ws_page                                                       ; 818a: a5 a8       ..             ; Save &A8 (workspace page number)
    pha                                                               ; 818c: 48          H              ; Push saved &A8
    stx svc_state                                                     ; 818d: 86 a9       ..             ; Store service number to &A9
    sty ws_page                                                       ; 818f: 84 a8       ..             ; Store Y (page number) to &A8
    tya                                                               ; 8191: 98          .              ; A = Y for dispatch table offset
    ldy #0                                                            ; 8192: a0 00       ..             ; Y=0: base offset for service dispatch
    jsr dispatch                                                      ; 8194: 20 e3 80     ..            ; Dispatch to service handler
    ldx svc_state                                                     ; 8197: a6 a9       ..             ; Recover service claim status from &A9
    pla                                                               ; 8199: 68          h              ; Restore saved &A8 from stack
    sta ws_page                                                       ; 819a: 85 a8       ..             ; Write back &A8
; ***************************************************************************************
; Service dispatch epilogue
; 
; Common return path for all dispatched service handlers.
; Restores rom_svc_num from the stack (pushed by dispatch_service),
; transfers X (ROM number) to A, then returns via RTS.
; ***************************************************************************************
.svc_dispatch_epilogue
    pla                                                               ; 819c: 68          h              ; Restore saved A from service dispatch
    sta svc_state                                                     ; 819d: 85 a9       ..             ; Save to workspace &A9
    txa                                                               ; 819f: 8a          .              ; Return ROM number in A
    ldx romsel_copy                                                   ; 81a0: a6 f4       ..             ; Restore X from MOS ROM select copy
; &81a2 referenced 1 time by &8184
.return_2
    rts                                                               ; 81a2: 60          `              ; Return to MOS service handler

.svc_4_star_command
    ldx #8                                                            ; 81a3: a2 08       ..             ; ROM offset for "ROFF" (copyright suffix)
    jsr match_rom_string                                              ; 81a5: 20 50 83     P.            ; Try matching *ROFF command
    bne match_net_cmd                                                 ; 81a8: d0 2e       ..             ; No match: try *NET
; ***************************************************************************************
; Resume after remote operation / *ROFF handler (NROFF)
; 
; Checks byte 4 of (net_rx_ptr): if non-zero, the keyboard was
; disabled during a remote operation (peek/poke/boot). Clears
; the flag, re-enables the keyboard via OSBYTE &C9, and sends
; function &0A to notify completion. Also handles *ROFF and the
; triple-plus escape sequence (+++), which resets system masks
; via OSBYTE &CE and returns control to the MOS, providing an
; escape route when a remote session becomes unresponsive.
; ***************************************************************************************
.net_4_resume_remote
    ldy #4                                                            ; 81aa: a0 04       ..             ; Y=4: offset of keyboard disable flag
    lda (net_rx_ptr),y                                                ; 81ac: b1 9c       ..             ; Read flag from RX buffer
    beq skip_kbd_reenable                                             ; 81ae: f0 21       .!             ; Zero: keyboard not disabled, skip
    lda #0                                                            ; 81b0: a9 00       ..             ; A=0: value to clear flag and re-enable
    tax                                                               ; 81b2: aa          .              ; X=&00
    sta (net_rx_ptr),y                                                ; 81b3: 91 9c       ..             ; Clear keyboard disable flag in buffer
    tay                                                               ; 81b5: a8          .              ; Y=&00
    lda #osbyte_read_write_econet_keyboard_disable                    ; 81b6: a9 c9       ..             ; OSBYTE &C9: Econet keyboard disable
    jsr osbyte                                                        ; 81b8: 20 f4 ff     ..            ; Re-enable keyboard (X=0, Y=0); Enable keyboard (for Econet)
    lda #&0a                                                          ; 81bb: a9 0a       ..             ; Function &0A: remote operation complete
    jsr setup_tx_and_send                                             ; 81bd: 20 c7 90     ..            ; Send notification to controlling station
; &81c0 referenced 1 time by &84bc
.clear_osbyte_ce_cf
    stx nfs_workspace                                                 ; 81c0: 86 9e       ..             ; Save X (return value from TX)
    lda #&ce                                                          ; 81c2: a9 ce       ..             ; OSBYTE &CE: first system mask to reset
; &81c4 referenced 1 time by &81cf
.clear_osbyte_masks
    ldx nfs_workspace                                                 ; 81c4: a6 9e       ..             ; Restore X for OSBYTE call
    ldy #&7f                                                          ; 81c6: a0 7f       ..             ; Y=&7F: AND mask (clear bit 7)
    jsr osbyte                                                        ; 81c8: 20 f4 ff     ..            ; Reset system mask byte
    adc #1                                                            ; 81cb: 69 01       i.             ; Advance to next OSBYTE (&CE -> &CF)
    cmp #&d0                                                          ; 81cd: c9 d0       ..             ; Reached &D0? (past &CF)
.cmd_name_matched
    beq clear_osbyte_masks                                            ; 81cf: f0 f3       ..             ; No: reset &CF too
; &81d1 referenced 1 time by &81ae
.skip_kbd_reenable
    lda #0                                                            ; 81d1: a9 00       ..             ; A=0: clear remote state
    sta svc_state                                                     ; 81d3: 85 a9       ..             ; Clear &A9 (service dispatch state)
.skpspi
    sta nfs_workspace                                                 ; 81d5: 85 9e       ..             ; Clear workspace byte
    rts                                                               ; 81d7: 60          `              ; Return

; &81d8 referenced 1 time by &81a8
.match_net_cmd
    ldx #1                                                            ; 81d8: a2 01       ..             ; X=1: ROM offset for "NET" match
    jsr match_rom_string                                              ; 81da: 20 50 83     P.            ; Try matching *NET command
    bne restore_ws_return                                             ; 81dd: d0 24       .$             ; No match: return unclaimed
; ***************************************************************************************
; Select NFS as active filing system (INIT)
; 
; Reached from service &12 (select FS) with Y=5, or when *NET command
; selects NFS. Notifies the current FS of shutdown via FSCV A=6 —
; this triggers the outgoing FS to save its context back to its
; workspace page, allowing restoration if re-selected later (the
; FSDIE handoff mechanism). Then sets up the standard OS vector
; indirections (FILEV through FSCV) to NFS entry points, claims the
; extended vector table entries, and issues service &0F (vectors
; claimed) to notify other ROMs. If nfs_temp is zero (auto-boot
; not inhibited), injects the synthetic command "I .BOOT" through
; the command decoder to trigger auto-boot login.
; ***************************************************************************************
.svc_13_select_nfs
    jsr call_fscv_shutdown                                            ; 81df: 20 06 82     ..            ; Notify current FS of shutdown (FSCV A=6)
    sec                                                               ; 81e2: 38          8              ; C=1 for ROR
    ror ws_page                                                       ; 81e3: 66 a8       f.             ; Set bit 7 of l00a8 (inhibit auto-boot)
    jsr issue_vectors_claimed                                         ; 81e5: 20 69 82     i.            ; Claim OS vectors, issue service &0F
    ldy #&1d                                                          ; 81e8: a0 1d       ..             ; Y=&1D: top of FS state range
; &81ea referenced 1 time by &81f2
.initl
    lda (net_rx_ptr),y                                                ; 81ea: b1 9c       ..             ; Copy FS state from RX buffer...
    sta fs_state_deb,y                                                ; 81ec: 99 eb 0d    ...            ; ...to workspace (offsets &15-&1D)
    dey                                                               ; 81ef: 88          .              ; Next byte (descending)
    cpy #&14                                                          ; 81f0: c0 14       ..             ; Loop until offset &14 done
    bne initl                                                         ; 81f2: d0 f6       ..             ; Continue loop
    beq init_fs_vectors                                               ; 81f4: f0 5c       .\             ; ALWAYS branch to init_fs_vectors; ALWAYS branch

; ***************************************************************************************
; Service 9: *HELP
; 
; Prints the ROM identification string using print_inline.
; 
; On Exit:
;     Y: workspace page number (from ws_page)
; ***************************************************************************************
.svc_9_help
    jsr print_inline                                                  ; 81f6: 20 4a 86     J.            ; Print ROM identification string
    equs &0d, "NFS 3.65", &0d                                         ; 81f9: 0d 4e 46... .NF            ; "NFS 3.65" version string + CRs

; &8203 referenced 2 times by &81dd, &8218
.restore_ws_return
    ldy ws_page                                                       ; 8203: a4 a8       ..             ; Restore Y (workspace page number)
    rts                                                               ; 8205: 60          `              ; Return (service not claimed)

; ***************************************************************************************
; Notify filing system of shutdown
; 
; Loads A=6 (FS shutdown notification) and JMP (FSCV).
; The FSCV handler's RTS returns to the caller of this routine
; (JSR/JMP trick saves one level of stack).
; ***************************************************************************************
; &8206 referenced 2 times by &81df, &820b
.call_fscv_shutdown
    lda #6                                                            ; 8206: a9 06       ..             ; FSCV reason 6 = FS shutdown
    jmp (fscv)                                                        ; 8208: 6c 1e 02    l..            ; Tail-call via filing system control vector

; ***************************************************************************************
; Service 3: auto-boot
; 
; Notifies current FS of shutdown via FSCV A=6. Scans keyboard
; (OSBYTE &7A): if no key is pressed, auto-boot proceeds directly
; via print_station_info. If a key is pressed, falls through to
; check_boot_key: the 'N' key (matrix address &55) proceeds with
; auto-boot, any other key causes the auto-boot to be declined.
; ***************************************************************************************
.svc_3_autoboot
    jsr call_fscv_shutdown                                            ; 820b: 20 06 82     ..            ; Notify current FS of shutdown
    lda #osbyte_scan_keyboard_from_16                                 ; 820e: a9 7a       .z             ; OSBYTE &7A: scan keyboard
    jsr osbyte                                                        ; 8210: 20 f4 ff     ..            ; Keyboard scan starting from key 16
    txa                                                               ; 8213: 8a          .              ; X is key number if key is pressed, or &ff otherwise
    bmi print_station_info                                            ; 8214: 30 0a       0.             ; No key pressed: proceed with auto-boot
; ***************************************************************************************
; Check boot key
; 
; Checks if the pressed key (in A) is 'N' (matrix address &55). If
; not 'N', returns to the MOS without claiming the service call
; (another ROM may boot instead). If 'N', forgets the keypress via
; OSBYTE &78 and falls through to print_station_info.
; ***************************************************************************************
.check_boot_key
    eor #&55 ; 'U'                                                    ; 8216: 49 55       IU             ; XOR with &55: result=0 if key is 'N'
    bne restore_ws_return                                             ; 8218: d0 e9       ..             ; Not 'N': return without claiming
    tay                                                               ; 821a: a8          .              ; Y=key
    lda #osbyte_write_keys_pressed                                    ; 821b: a9 78       .x             ; OSBYTE &78: clear key-pressed state
    jsr osbyte                                                        ; 821d: 20 f4 ff     ..            ; Write current keys pressed (X and Y)
; ***************************************************************************************
; Print station identification
; 
; Prints "Econet Station <n>" using the station number from the net
; receive buffer, then tests ADLC SR2 for the network clock signal —
; prints " No Clock" if absent. Falls through to init_fs_vectors.
; ***************************************************************************************
; &8220 referenced 1 time by &8214
.print_station_info
    jsr print_inline                                                  ; 8220: 20 4a 86     J.            ; Print 'Econet Station ' banner
    equs "Econet Station "                                            ; 8223: 45 63 6f... Eco            ; "Econet Station " inline string data

    ldy #&14                                                          ; 8232: a0 14       ..             ; Y=&14: station number offset in RX buf
    lda (net_rx_ptr),y                                                ; 8234: b1 9c       ..             ; Load station number
    jsr print_decimal                                                 ; 8236: 20 ab 8d     ..            ; Print as 3-digit decimal
    lda #&20 ; ' '                                                    ; 8239: a9 20       .              ; BIT trick: bit 5 of SR2 = clock present
    bit econet_control23_or_status2                                   ; 823b: 2c a1 fe    ,..            ; Test DCD: clock present if bit 5 clear
.dofsl1
    beq skip_no_clock_msg                                             ; 823e: f0 0d       ..             ; Clock present: skip warning
    jsr print_inline                                                  ; 8240: 20 4a 86     J.            ; Print ' No Clock' warning
    equs " No Clock"                                                  ; 8243: 20 4e 6f...  No            ; " No Clock" inline string data

    nop                                                               ; 824c: ea          .              ; NOP (padding after inline string)
; &824d referenced 1 time by &823e
.skip_no_clock_msg
    jsr print_inline                                                  ; 824d: 20 4a 86     J.            ; Print two CRs (blank line)
    equs &0d, &0d                                                     ; 8250: 0d 0d       ..             ; CR CR inline string data

; ***************************************************************************************
; Initialise filing system vectors
; 
; Copies 14 bytes from l8288 (&8288) into FILEV-FSCV (&0212),
; setting all 7 filing system vectors to the extended vector dispatch
; addresses (&FF1B-&FF2D). Calls setup_rom_ptrs_netv to install the
; ROM pointer table entries with the actual NFS handler addresses. Also
; reached directly from svc_13_select_nfs, bypassing the station display.
; Falls through to issue_vectors_claimed.
; ***************************************************************************************
; &8252 referenced 1 time by &81f4
.init_fs_vectors
    ldy #&0d                                                          ; 8252: a0 0d       ..             ; Copy 14 bytes: FS vector addresses to FILEV-FSCV
; &8254 referenced 1 time by &825b
.copy_fs_vectors
    lda fs_dispatch_addrs,y                                           ; 8254: b9 88 82    ...            ; Load extended vector dispatch address
    sta filev,y                                                       ; 8257: 99 12 02    ...            ; Write to FILEV-FSCV vector table
    dey                                                               ; 825a: 88          .              ; Next byte (descending)
    bpl copy_fs_vectors                                               ; 825b: 10 f7       ..             ; Loop until all 14 bytes copied
    jsr setup_rom_ptrs_netv                                           ; 825d: 20 13 83     ..            ; Read ROM ptr table addr, install NETV
    ldy #&1b                                                          ; 8260: a0 1b       ..             ; Install 7 handler entries in ROM ptr table
    ldx #7                                                            ; 8262: a2 07       ..             ; 7 FS vectors to install
    jsr store_rom_ptr_pair                                            ; 8264: 20 27 83     '.            ; Install each 3-byte vector entry
    stx svc_state                                                     ; 8267: 86 a9       ..             ; X=0 after loop; store as workspace offset
; ***************************************************************************************
; Issue 'vectors claimed' service and optionally auto-boot
; 
; Issues service &0F (vectors claimed) via OSBYTE &8F, then
; service &0A. If l00a8 is zero (soft break — RXCBs already
; initialised), sets up the command string "I .BOOT" at &828E
; and jumps to the FSCV 3 unrecognised-command handler (which
; matches against the command table at &8C4B). The "I." prefix
; triggers the catch-all entry which forwards the command to
; the fileserver. Falls through to run_fscv_cmd.
; ***************************************************************************************
; &8269 referenced 1 time by &81e5
.issue_vectors_claimed
    lda #osbyte_issue_service_request                                 ; 8269: a9 8f       ..             ; A=&8F: issue service request
    ldx #&0f                                                          ; 826b: a2 0f       ..             ; X=&0F: 'vectors claimed' service
    jsr osbyte                                                        ; 826d: 20 f4 ff     ..            ; Issue paged ROM service call, Reason X=15 - Vectors claimed
    ldx #&0a                                                          ; 8270: a2 0a       ..             ; X=&0A: service &0A
    jsr osbyte                                                        ; 8272: 20 f4 ff     ..            ; Issue service &0A
    ldx ws_page                                                       ; 8275: a6 a8       ..             ; Non-zero after hard reset: skip auto-boot
    bne return_3                                                      ; 8277: d0 37       .7             ; Non-zero: skip auto-boot
    ldx #&80                                                          ; 8279: a2 80       ..             ; X = lo byte of auto-boot string at &8292
; ***************************************************************************************
; Run FSCV command from ROM
; 
; Sets Y to the ROM page high byte (&82) and jumps to fscv_3_star_cmd
; to execute the command string at (X, Y). X is pre-loaded by the
; caller with the low byte of the string address. Also used as a
; data base address by store_rom_ptr_pair for Y-indexed access to
; the handler address table.
; ***************************************************************************************
; &827b referenced 2 times by &8327, &832d
.run_fscv_cmd
    ldy #&82                                                          ; 827b: a0 82       ..             ; Y=&82: ROM page high byte
; Synthetic auto-boot command string. "I " does not match any
; entry in NFS's local command table — "I." requires a dot, and
; "I AM" requires 'A' after the space — so fscv_3_star_cmd
; forwards the entire string to the fileserver, which executes
; the .BOOT file.
    jmp fscv_3_star_cmd                                               ; 827d: 4c 09 8c    L..            ; Execute command string at (X, Y)

    equs "I .BOO"                                                     ; 8280: 49 20 2e... I .
; ***************************************************************************************
; FS vector dispatch and handler addresses (34 bytes)
; 
; Bytes 0-13: extended vector dispatch addresses, copied to
; FILEV-FSCV (&0212) by init_fs_vectors. Each 2-byte pair is
; a dispatch address (&FF1B-&FF2D) that the MOS uses to look up
; the handler in the ROM pointer table.
; 
; Bytes 14-33: handler address pairs read by store_rom_ptr_pair.
; Each entry has addr_lo, addr_hi, then a padding byte that is
; not read at runtime (store_rom_ptr_pair writes the current ROM
; bank number without reading). The last entry (FSCV) has no
; padding byte.
; ***************************************************************************************
.fs_vector_addrs
    equb &54, &0d                                                     ; 8286: 54 0d       T.             ; Auto-boot string tail / vector table header
; &8288 referenced 1 time by &8254
.fs_dispatch_addrs
    equw &ff1b                                                        ; 8288: 1b ff       ..             ; FILEV dispatch (&FF1B)
    equw &ff1e                                                        ; 828a: 1e ff       ..             ; ARGSV dispatch (&FF1E)
    equw &ff21                                                        ; 828c: 21 ff       !.             ; BGETV dispatch (&FF21)
    equw &ff24                                                        ; 828e: 24 ff       $.             ; BPUTV dispatch (&FF24)
    equw &ff27                                                        ; 8290: 27 ff       '.             ; GBPBV dispatch (&FF27)
    equw &ff2a                                                        ; 8292: 2a ff       *.             ; FINDV dispatch (&FF2A)
    equw &ff2d                                                        ; 8294: 2d ff       -.             ; FSCV dispatch (&FF2D)
    equw &86fa                                                        ; 8296: fa 86       ..             ; FILEV handler (&86FA)
    equb &4a                                                          ; 8298: 4a          J              ; (ROM bank — not read)
    equw &8956                                                        ; 8299: 56 89       V.             ; ARGSV handler (&8956)
    equb &44                                                          ; 829b: 44          D              ; (ROM bank — not read)
    equw &8551                                                        ; 829c: 51 85       Q.             ; BGETV handler (&8551)
    equb &57                                                          ; 829e: 57          W              ; (ROM bank — not read)
    equw &8401                                                        ; 829f: 01 84       ..             ; BPUTV handler (&8401)
    equb &42                                                          ; 82a1: 42          B              ; (ROM bank — not read)
    equw &8a60                                                        ; 82a2: 60 8a       `.             ; GBPBV handler (&8A60)
    equb &41                                                          ; 82a4: 41          A              ; (ROM bank — not read)
    equw &89c6                                                        ; 82a5: c6 89       ..             ; FINDV handler (&89C6)
    equb &52                                                          ; 82a7: 52          R              ; (ROM bank — not read)
    equw &80d0                                                        ; 82a8: d0 80       ..             ; FSCV handler (&80D0)

; ***************************************************************************************
; Service 1: claim absolute workspace
; 
; Claims pages up to &10 for NMI workspace (&0D), FS state (&0E),
; and FS command buffer (&0F). If Y >= &10, workspace already
; allocated — returns unchanged.
; 
; On Entry:
;     Y: current top of absolute workspace
; 
; On Exit:
;     Y: updated top of absolute workspace (max of input and &10)
; ***************************************************************************************
.svc_1_abs_workspace
    cpy #&10                                                          ; 82aa: c0 10       ..             ; Already at page &10 or above?
    bcs return_3                                                      ; 82ac: b0 02       ..             ; Yes: nothing to claim
    ldy #&10                                                          ; 82ae: a0 10       ..             ; Claim pages &0D-&0F (3 pages)
; &82b0 referenced 2 times by &8277, &82ac
.return_3
    rts                                                               ; 82b0: 60          `              ; Return (workspace claim done)

    equb &83, &90                                                     ; 82b1: 83 90       ..

; ***************************************************************************************
; Service 2: claim private workspace and initialise NFS
; 
; Y = next available workspace page on entry.
; Sets up net_rx_ptr (Y) and nfs_workspace (Y+1) page pointers.
; On soft break (OSBYTE &FD returns 0): skips FS state init,
; preserving existing login state, file server selection, and
; control block configuration — this is why pressing BREAK
; keeps the user logged in.
; On power-up/CTRL-BREAK (result non-zero):
;   - Sets FS server station to &FE (no server selected)
;   - Sets printer server station to &FE (no server selected)
;   - Clears FS handles, OPT byte, message flag, SEQNOS
;   - Initialises all RXCBs with &3F flag (available)
; In both cases: reads station ID from &FE18 (only valid during
; reset), calls adlc_init, enables user-level RX (LFLAG=&40).
; 
; On Entry:
;     Y: next available workspace page
; 
; On Exit:
;     Y: next available workspace page after NFS (input + 2)
; ***************************************************************************************
.svc_2_private_workspace
    sty net_rx_ptr_hi                                                 ; 82b3: 84 9d       ..             ; RX buffer page = first claimed page
    iny                                                               ; 82b5: c8          .              ; Advance to next page
    sty nfs_workspace_hi                                              ; 82b6: 84 9f       ..             ; Workspace page = second claimed page
    lda #0                                                            ; 82b8: a9 00       ..             ; A=0 for clearing workspace
    ldy #4                                                            ; 82ba: a0 04       ..             ; Y=4: remote status offset
    sta (net_rx_ptr),y                                                ; 82bc: 91 9c       ..             ; Clear status byte in net receive buffer
    ldy #&ff                                                          ; 82be: a0 ff       ..             ; Y=&FF: used for later iteration
    sta net_rx_ptr                                                    ; 82c0: 85 9c       ..             ; Clear RX ptr low byte
    sta nfs_workspace                                                 ; 82c2: 85 9e       ..             ; Clear workspace ptr low byte
    sta ws_page                                                       ; 82c4: 85 a8       ..             ; Clear RXCB iteration counter
    sta tx_clear_flag                                                 ; 82c6: 8d 62 0d    .b.            ; Clear TX semaphore (no TX in progress)
    tax                                                               ; 82c9: aa          .              ; X=0 for OSBYTE; X=&00
    lda #osbyte_read_write_last_break_type                            ; 82ca: a9 fd       ..             ; OSBYTE &FD: read type of last reset
    jsr osbyte                                                        ; 82cc: 20 f4 ff     ..            ; Read type of last reset
    txa                                                               ; 82cf: 8a          .              ; X = break type from OSBYTE result; X=value of type of last reset
    beq read_station_id                                               ; 82d0: f0 32       .2             ; Soft break (X=0): skip FS init
    ldy #&15                                                          ; 82d2: a0 15       ..             ; Y=&15: printer station offset in RX buffer
    lda #&fe                                                          ; 82d4: a9 fe       ..             ; &FE = no server selected
    sta fs_server_stn                                                 ; 82d6: 8d 00 0e    ...            ; Station &FE = no server selected
    sta (net_rx_ptr),y                                                ; 82d9: 91 9c       ..             ; Store &FE at printer station offset
    lda #0                                                            ; 82db: a9 00       ..             ; A=0 for clearing workspace fields
    sta fs_server_net                                                 ; 82dd: 8d 01 0e    ...            ; Clear network number
    sta prot_status                                                   ; 82e0: 8d 63 0d    .c.            ; Clear protection status
    sta fs_messages_flag                                              ; 82e3: 8d 06 0e    ...            ; Clear message flag
    sta fs_boot_option                                                ; 82e6: 8d 05 0e    ...            ; Clear boot option
    iny                                                               ; 82e9: c8          .              ; Y=&16
    sta (net_rx_ptr),y                                                ; 82ea: 91 9c       ..             ; Clear net number at RX buffer offset &16
    ldy #3                                                            ; 82ec: a0 03       ..             ; Init printer server: station &FE, net 0
    sta (nfs_workspace),y                                             ; 82ee: 91 9e       ..             ; Store net 0 at workspace offset 3
    dey                                                               ; 82f0: 88          .              ; Y=2: printer station offset; Y=&02
    lda #&eb                                                          ; 82f1: a9 eb       ..             ; &FE = no printer server
    sta (nfs_workspace),y                                             ; 82f3: 91 9e       ..             ; Store &FE at printer station in workspace
; &82f5 referenced 1 time by &8302
.init_rxcb_entries
    lda ws_page                                                       ; 82f5: a5 a8       ..             ; Load RXCB counter
    jsr calc_handle_offset                                            ; 82f7: 20 58 8e     X.            ; Convert to workspace byte offset
    bcs read_station_id                                               ; 82fa: b0 08       ..             ; C=1: past max handles, done
    lda #&3f ; '?'                                                    ; 82fc: a9 3f       .?             ; Mark RXCB as available
    sta (nfs_workspace),y                                             ; 82fe: 91 9e       ..             ; Write &3F flag to workspace
    inc ws_page                                                       ; 8300: e6 a8       ..             ; Next RXCB number
    bne init_rxcb_entries                                             ; 8302: d0 f1       ..             ; Loop for all RXCBs
; &8304 referenced 2 times by &82d0, &82fa
.read_station_id
    lda station_id_disable_net_nmis                                   ; 8304: ad 18 fe    ...            ; Read station ID (also INTOFF)
    ldy #&14                                                          ; 8307: a0 14       ..             ; Y=&14: station ID offset in RX buffer
    sta (net_rx_ptr),y                                                ; 8309: 91 9c       ..             ; Store our station number
    jsr init_adlc_hw                                                  ; 830b: 20 53 96     S.            ; Initialise ADLC hardware
    lda #&40 ; '@'                                                    ; 830e: a9 40       .@             ; Enable user-level RX (LFLAG=&40)
    sta rx_flags                                                      ; 8310: 8d 64 0d    .d.            ; Store to rx_flags
; ***************************************************************************************
; Set up ROM pointer table and NETV
; 
; Reads the ROM pointer table base address via OSBYTE &A8, stores
; it in osrdsc_ptr (&F6). Sets NETV low byte to &36. Then copies
; one 3-byte extended vector entry (addr=&9080, rom=current) into
; the ROM pointer table at offset &36, installing osword_dispatch
; as the NETV handler.
; ***************************************************************************************
; &8313 referenced 1 time by &825d
.setup_rom_ptrs_netv
    lda #osbyte_read_rom_ptr_table_low                                ; 8313: a9 a8       ..             ; OSBYTE &A8: read ROM pointer table address
    ldx #0                                                            ; 8315: a2 00       ..             ; X=0: read low byte
    ldy #&ff                                                          ; 8317: a0 ff       ..             ; Y=&FF: read high byte
    jsr osbyte                                                        ; 8319: 20 f4 ff     ..            ; Returns table address in X (lo) Y (hi); Read address of ROM pointer table
    stx osrdsc_ptr                                                    ; 831c: 86 f6       ..             ; Store table base address low byte; X=value of address of ROM pointer table (low byte)
    sty osrdsc_ptr_hi                                                 ; 831e: 84 f7       ..             ; Store table base address high byte; Y=value of address of ROM pointer table (high byte)
    ldy #&36 ; '6'                                                    ; 8320: a0 36       .6             ; NETV extended vector offset in ROM ptr table
    sty netv                                                          ; 8322: 8c 24 02    .$.            ; Set NETV low byte = &36 (vector dispatch)
    ldx #1                                                            ; 8325: a2 01       ..             ; Install 1 entry (NETV) in ROM ptr table
; &8327 referenced 2 times by &8264, &8339
.store_rom_ptr_pair
    lda run_fscv_cmd,y                                                ; 8327: b9 7b 82    .{.            ; Load handler address low byte from table
    sta (osrdsc_ptr),y                                                ; 832a: 91 f6       ..             ; Store to ROM pointer table
    iny                                                               ; 832c: c8          .              ; Next byte
    lda run_fscv_cmd,y                                                ; 832d: b9 7b 82    .{.            ; Load handler address high byte from table
    sta (osrdsc_ptr),y                                                ; 8330: 91 f6       ..             ; Store to ROM pointer table
    iny                                                               ; 8332: c8          .              ; Next byte
    lda romsel_copy                                                   ; 8333: a5 f4       ..             ; Write current ROM bank number
    sta (osrdsc_ptr),y                                                ; 8335: 91 f6       ..             ; Store ROM number to ROM pointer table
    iny                                                               ; 8337: c8          .              ; Advance to next entry position
    dex                                                               ; 8338: ca          .              ; Count down entries
    bne store_rom_ptr_pair                                            ; 8339: d0 ec       ..             ; Loop until all entries installed
    ldy nfs_workspace_hi                                              ; 833b: a4 9f       ..             ; Y = workspace high byte + 1 = next free page
    iny                                                               ; 833d: c8          .              ; Advance past workspace page
    rts                                                               ; 833e: 60          `              ; Return; Y = page after NFS workspace

; ***************************************************************************************
; FSCV 6: Filing system shutdown / save state (FSDIE)
; 
; Called when another filing system (e.g. DFS) is selected. Saves
; the current NFS context (FSLOCN station number, URD/CSD/LIB
; handles, OPT byte, etc.) from page &0E into the dynamic workspace
; backup area. This allows the state to be restored when *NET is
; re-issued later, without losing the login session. Finally calls
; OSBYTE &77 (close SPOOL/EXEC files) to release the
; Econet network printer on FS switch.
; ***************************************************************************************
.fscv_6_shutdown
    ldy #&1d                                                          ; 833f: a0 1d       ..             ; Copy 10 bytes: FS state to workspace backup
; &8341 referenced 1 time by &8349
.fsdiel
    lda fs_state_deb,y                                                ; 8341: b9 eb 0d    ...            ; Load FS state byte at offset Y
    sta (net_rx_ptr),y                                                ; 8344: 91 9c       ..             ; Store to workspace backup area
    dey                                                               ; 8346: 88          .              ; Next byte down
    cpy #&14                                                          ; 8347: c0 14       ..             ; Offsets &15-&1D: server, handles, OPT, etc.
    bne fsdiel                                                        ; 8349: d0 f6       ..             ; Loop for offsets &1D..&15
    lda #osbyte_close_spool_exec                                      ; 834b: a9 77       .w             ; A=&77: OSBYTE close spool/exec
    jmp osbyte                                                        ; 834d: 4c f4 ff    L..            ; Close any *SPOOL and *EXEC files

; &8350 referenced 2 times by &81a5, &81da
.match_rom_string
    ldy ws_page                                                       ; 8350: a4 a8       ..             ; Y = saved text pointer offset
; &8352 referenced 1 time by &8363
.match_cmd_chars
    lda (os_text_ptr),y                                               ; 8352: b1 f2       ..             ; Load next input character
    cmp #&2e ; '.'                                                    ; 8354: c9 2e       ..             ; Is it a '.' (abbreviation)?
    beq skip_space_next                                               ; 8356: f0 13       ..             ; Yes: skip to space skipper (match)
    and #&df                                                          ; 8358: 29 df       ).             ; Force uppercase (clear bit 5)
    beq check_rom_end                                                 ; 835a: f0 09       ..             ; Input char is NUL/space: check ROM byte
    cmp binary_version,x                                              ; 835c: dd 08 80    ...            ; Compare with ROM string byte
    bne check_rom_end                                                 ; 835f: d0 04       ..             ; Mismatch: check if ROM string ended
    iny                                                               ; 8361: c8          .              ; Advance input pointer
    inx                                                               ; 8362: e8          .              ; Advance ROM string pointer
    bne match_cmd_chars                                               ; 8363: d0 ed       ..             ; Continue matching (always taken)
; &8365 referenced 2 times by &835a, &835f
.check_rom_end
    lda binary_version,x                                              ; 8365: bd 08 80    ...            ; Load ROM string byte at match point
    beq skip_spaces                                                   ; 8368: f0 02       ..             ; Zero = end of ROM string = full match
    rts                                                               ; 836a: 60          `              ; Non-zero = partial/no match; Z=0

; &836b referenced 2 times by &8356, &8370
.skip_space_next
    iny                                                               ; 836b: c8          .              ; Skip this space
; ***************************************************************************************
; Skip spaces and test for end of line
; 
; Advances Y past leading spaces in the text at (os_text_ptr),Y.
; Returns Z=1 if the next non-space character is CR (end of line),
; Z=0 otherwise with A holding the character.
; 
; On Entry:
;     Y: offset into (os_text_ptr) buffer
; 
; On Exit:
;     A: character EOR &0D (0 if CR)
;     Y: offset of first non-space character
;     Z: set if end of line (CR)
; ***************************************************************************************
; &836c referenced 2 times by &8368, &8df0
.skip_spaces
    lda (os_text_ptr),y                                               ; 836c: b1 f2       ..             ; Load next input character
    cmp #&20 ; ' '                                                    ; 836e: c9 20       .              ; Is it a space?
    beq skip_space_next                                               ; 8370: f0 f9       ..             ; Yes: keep skipping
    eor #&0d                                                          ; 8372: 49 0d       I.             ; XOR with CR: Z=1 if end of line
    rts                                                               ; 8374: 60          `              ; Return with Z flag result

; ***************************************************************************************
; Initialise TX control block for FS reply on port &90
; 
; Loads port &90 (PREPLY) into A, calls init_tx_ctrl_block to set
; up the TX control block, stores the port and control bytes, then
; decrements the control flag. Used by send_fs_reply_cmd to prepare
; for receiving the fileserver's reply.
; ***************************************************************************************
; &8375 referenced 1 time by &83e2
.init_tx_reply_port
    lda #&90                                                          ; 8375: a9 90       ..             ; A=&90: FS reply port (PREPLY)
; &8377 referenced 1 time by &888a
.init_tx_ctrl_port
    jsr init_tx_ctrl_block                                            ; 8377: 20 83 83     ..            ; Init TXCB from template
    sta txcb_port                                                     ; 837a: 85 c1       ..             ; Store port number in TXCB
    lda #3                                                            ; 837c: a9 03       ..             ; Control byte: 3 = transmit
    sta txcb_start                                                    ; 837e: 85 c4       ..             ; Store control byte in TXCB
    dec txcb_ctrl                                                     ; 8380: c6 c0       ..             ; Decrement TXCB flag to arm TX
    rts                                                               ; 8382: 60          `              ; Return after port setup

; ***************************************************************************************
; Initialise TX control block at &00C0 from template
; 
; Copies 12 bytes from tx_ctrl_template (&839B) to &00C0.
; For the first 2 bytes (Y=0,1), also copies the fileserver
; station/network from &0E00/&0E01 to &00C2/&00C3.
; The template sets up: control=&80, port=&99 (FS command port),
; command data length=&0F, plus padding bytes.
; 
; On Exit:
;     A: preserved
;     Y: &FF (decremented past 0)
; ***************************************************************************************
; &8383 referenced 4 times by &8377, &83d1, &841d, &8ff9
.init_tx_ctrl_block
    pha                                                               ; 8383: 48          H              ; Preserve A across call
    ldy #&0b                                                          ; 8384: a0 0b       ..             ; Copy 12 bytes (Y=11..0)
; &8386 referenced 1 time by &8397
.fstxl1
    lda tx_ctrl_template,y                                            ; 8386: b9 9b 83    ...            ; Load template byte
    sta txcb_ctrl,y                                                   ; 8389: 99 c0 00    ...            ; Store to TX control block at &00C0
    cpy #2                                                            ; 838c: c0 02       ..             ; Y < 2: also copy FS server station/network
    bpl fstxl2                                                        ; 838e: 10 06       ..             ; Skip station/network copy for Y >= 2
    lda fs_server_stn,y                                               ; 8390: b9 00 0e    ...            ; Load FS server station (Y=0) or network (Y=1)
    sta txcb_dest,y                                                   ; 8393: 99 c2 00    ...            ; Store to dest station/network at &00C2
; &8396 referenced 1 time by &838e
.fstxl2
    dey                                                               ; 8396: 88          .              ; Next byte (descending)
    bpl fstxl1                                                        ; 8397: 10 ed       ..             ; Loop until all 12 bytes copied
    pla                                                               ; 8399: 68          h              ; Restore A
    rts                                                               ; 839a: 60          `              ; Return

; ***************************************************************************************
; TX control block template (TXTAB, 12 bytes)
; 
; 12-byte template copied to &00C0 by init_tx_ctrl. Defines the
; TX control block for FS commands: control flag, port, station/
; network, and data buffer pointers (&0F00-&0FFF). The 4-byte
; Econet addresses use only the low 2 bytes; upper bytes are &FF.
; ***************************************************************************************
; &839b referenced 1 time by &8386
.tx_ctrl_template
    equb &80, &99, 0, 0, 0, &0f                                       ; 839b: 80 99 00... ...            ; Control flag; Port (FS command = &99); Buffer start low; Buffer start high (page &0F)
; &83a1 referenced 3 times by &890a, &89e9, &9186
.tx_ctrl_upper
    equb &ff, &ff, &ff, &0f, &ff, &ff                                 ; 83a1: ff ff ff... ...            ; Buffer start pad (4-byte Econet addr); Buffer start pad; Buffer end low; Buffer end high (page &0F); Buffer end pad; Buffer end pad

; ***************************************************************************************
; Prepare FS command with carry set
; 
; Alternate entry to prepare_fs_cmd that pushes A, loads &2A
; into fs_error_ptr, and enters with carry set (SEC). The carry
; flag is later tested by build_send_fs_cmd to select the
; byte-stream (BSXMIT) transmission path.
; 
; On Entry:
;     A: flag byte to include in FS command
;     Y: function code for FS header
; ***************************************************************************************
; &83a7 referenced 1 time by &8ab1
.prepare_cmd_with_flag
    pha                                                               ; 83a7: 48          H              ; Save flag byte for command
    sec                                                               ; 83a8: 38          8              ; C=1: include flag in FS command
    bcs store_fs_hdr_fn                                               ; 83a9: b0 12       ..             ; ALWAYS branch to prepare_fs_cmd; ALWAYS branch

; &83ab referenced 2 times by &8717, &87bd
.prepare_cmd_clv
    clv                                                               ; 83ab: b8          .              ; V=0: command has no flag byte
    bvc store_fs_hdr_clc                                              ; 83ac: 50 0e       P.             ; ALWAYS branch to prepare_fs_cmd; ALWAYS branch

; ***************************************************************************************
; *BYE handler (logoff)
; 
; Closes any open *SPOOL and *EXEC files via OSBYTE &77 (FXSPEX),
; then falls into prepare_fs_cmd with Y=&17 (FCBYE: logoff code).
; Dispatched from the command match table at &8C4B for "BYE".
; ***************************************************************************************
.bye_handler
    lda #osbyte_close_spool_exec                                      ; 83ae: a9 77       .w             ; A=&77: OSBYTE close spool/exec
    jsr osbyte                                                        ; 83b0: 20 f4 ff     ..            ; Close any *SPOOL and *EXEC files
    ldy #&17                                                          ; 83b3: a0 17       ..             ; Y=function code for HDRFN
; ***************************************************************************************
; Prepare FS command buffer (12 references)
; 
; Builds the 5-byte FS protocol header at &0F00:
;   &0F00 HDRREP = reply port (set downstream, typically &90/PREPLY)
;   &0F01 HDRFN  = Y parameter (function code)
;   &0F02 HDRURD = URD handle (from &0E02)
;   &0F03 HDRCSD = CSD handle (from &0E03)
;   &0F04 HDRLIB = LIB handle (from &0E04)
; Command-specific data follows at &0F05 (TXBUF). Also clears V flag.
; Called before building specific FS commands for transmission.
; 
; On Entry:
;     Y: function code for HDRFN
;     X: preserved through header build
; 
; On Exit:
;     A: 0 on success (from build_send_fs_cmd)
;     X: 0 on success, &D6 on not-found
;     Y: 1 (offset past command code in reply)
; ***************************************************************************************
; &83b5 referenced 12 times by &80c1, &88af, &8925, &8971, &8998, &8a0f, &8a36, &8b0c, &8bc7, &8c73, &8caa, &8d15
.prepare_fs_cmd
    clv                                                               ; 83b5: b8          .              ; V=0: standard FS command path
; &83b6 referenced 2 times by &890d, &89ec
.init_tx_ctrl_data
.prepare_fs_cmd_v
    lda fs_urd_handle                                                 ; 83b6: ad 02 0e    ...            ; Copy URD handle from workspace to buffer
    sta fs_cmd_urd                                                    ; 83b9: 8d 02 0f    ...            ; Store URD at &0F02
; &83bc referenced 1 time by &83ac
.store_fs_hdr_clc
    clc                                                               ; 83bc: 18          .              ; CLC: no byte-stream path
; &83bd referenced 1 time by &83a9
.store_fs_hdr_fn
    sty fs_cmd_y_param                                                ; 83bd: 8c 01 0f    ...            ; Store function code at &0F01
    ldy #1                                                            ; 83c0: a0 01       ..             ; Y=1: copy CSD (offset 1) then LIB (offset 0)
; &83c2 referenced 1 time by &83c9
.copy_dir_handles
    lda fs_csd_handle,y                                               ; 83c2: b9 03 0e    ...            ; Copy CSD and LIB handles to command buffer
    sta fs_cmd_csd,y                                                  ; 83c5: 99 03 0f    ...            ; Store at &0F03 (CSD) and &0F04 (LIB)
    dey                                                               ; 83c8: 88          .              ; Y=function code
    bpl copy_dir_handles                                              ; 83c9: 10 f7       ..             ; Loop for both handles
; ***************************************************************************************
; Build and send FS command (DOFSOP)
; 
; Sets reply port to &90 (PREPLY) at &0F00, initialises the TX
; control block, then adjusts TXCB's high pointer (HPTR) to X+5
; -- the 5-byte FS header (reply port, function code, URD, CSD,
; LIB) plus the command data -- so only meaningful bytes are
; transmitted, conserving Econet bandwidth. If carry is set on
; entry (DOFSBX byte-stream path), takes the alternate path
; through econet_tx_retry for direct BSXMIT transmission.
; Otherwise sets up the TX pointer via setup_tx_ptr_c0 and falls
; through to send_fs_reply_cmd for reply handling. The carry flag
; is the sole discriminator between byte-stream and standard FS
; protocol paths -- set by SEC at the BPUTV/BGETV entry points.
; On return from WAITFS/BSXMIT, Y=0; INY advances past the
; command code to read the return code. Error &D6 ("not found")
; is detected via ADC #(&100-&D6) with C=0 -- if the return code
; was exactly &D6, the result wraps to zero (Z=1). This is a
; branchless comparison returning C=1, A=0 as a soft error that
; callers can handle, vs hard errors which go through FSERR.
; 
; On Entry:
;     X: buffer extent (command-specific data bytes)
;     Y: function code
;     C: 0 for standard FS path, 1 for byte-stream (BSXMIT)
; 
; On Exit:
;     A: 0 on success
;     X: 0 on success, &D6 on not-found
;     Y: 1 (offset past command code in reply)
; ***************************************************************************************
; &83cb referenced 1 time by &8b65
.build_send_fs_cmd
    php                                                               ; 83cb: 08          .              ; Save carry (FS path vs byte-stream)
    lda #&90                                                          ; 83cc: a9 90       ..             ; Reply port &90 (PREPLY)
    sta fs_cmd_type                                                   ; 83ce: 8d 00 0f    ...            ; Store at &0F00 (HDRREP)
    jsr init_tx_ctrl_block                                            ; 83d1: 20 83 83     ..            ; Copy TX template to &00C0
    txa                                                               ; 83d4: 8a          .              ; A = X (buffer extent)
    adc #5                                                            ; 83d5: 69 05       i.             ; HPTR = header (5) + data (X) bytes to send
    sta txcb_end                                                      ; 83d7: 85 c8       ..             ; Store to TXCB end-pointer low
    plp                                                               ; 83d9: 28          (              ; Restore carry flag
    bcs dofsl5                                                        ; 83da: b0 1a       ..             ; C=1: byte-stream path (BSXMIT)
    php                                                               ; 83dc: 08          .              ; Save flags for send_fs_reply_cmd
    jsr setup_tx_ptr_c0                                               ; 83dd: 20 e5 85     ..            ; Point net_tx_ptr to &00C0; transmit
    plp                                                               ; 83e0: 28          (              ; Restore flags
; &83e1 referenced 2 times by &87ca, &8ae9
.send_fs_reply_cmd
    php                                                               ; 83e1: 08          .              ; Save flags (V flag state)
    jsr init_tx_reply_port                                            ; 83e2: 20 75 83     u.            ; Set up RX wait for FS reply
    jsr waitfs                                                        ; 83e5: 20 1e 85     ..            ; Transmit and wait (BRIANX)
    plp                                                               ; 83e8: 28          (              ; Restore flags
; &83e9 referenced 1 time by &83ff
.dofsl7
    iny                                                               ; 83e9: c8          .              ; Y=1: skip past command code byte
    lda (txcb_start),y                                                ; 83ea: b1 c4       ..             ; Load return code from FS reply
    tax                                                               ; 83ec: aa          .              ; X = return code
    beq return_dofsl7                                                 ; 83ed: f0 06       ..             ; Zero: success, return
    bvc check_fs_error                                                ; 83ef: 50 02       P.             ; V=0: standard path, error is fatal
    adc #&2a ; '*'                                                    ; 83f1: 69 2a       i*             ; ADC #&2A: test for &D6 (not found)
; &83f3 referenced 1 time by &83ef
.check_fs_error
    bne store_fs_error                                                ; 83f3: d0 73       .s             ; Non-zero: hard error, go to FSERR
; &83f5 referenced 1 time by &83ed
.return_dofsl7
    rts                                                               ; 83f5: 60          `              ; Return (success or soft &D6 error)

; &83f6 referenced 1 time by &83da
.dofsl5
    pla                                                               ; 83f6: 68          h              ; Discard saved flags from stack
    ldx #&c0                                                          ; 83f7: a2 c0       ..             ; X=&C0: TXCB address for byte-stream TX
    iny                                                               ; 83f9: c8          .              ; Y++ past command code
    jsr econet_tx_retry                                               ; 83fa: 20 69 92     i.            ; Byte-stream transmit with retry
    sta fs_load_addr_3                                                ; 83fd: 85 b3       ..             ; Store result to &B3
    bcc dofsl7                                                        ; 83ff: 90 e8       ..             ; C=0: success, check reply code
.bputv_handler
    clc                                                               ; 8401: 18          .              ; CLC for address addition
; ***************************************************************************************
; BGETV entry point
; 
; Clears the escapable flag via clear_escapable, then falls
; through to handle_bput_bget with carry set (SEC by caller)
; to indicate a BGET operation.
; 
; On Entry:
;     Y: file handle
;     C: 1 (set by MOS before calling BGETV)
; 
; On Exit:
;     A: byte read from file
;     C: 1 if EOF, 0 otherwise
; ***************************************************************************************
; &8402 referenced 1 time by &8552
.bgetv_entry
    jsr clear_escapable                                               ; 8402: 20 45 86     E.            ; Clear escapable flag before BGET
; ***************************************************************************************
; Handle BPUT/BGET file byte I/O
; 
; BPUTV enters at &8413 (CLC; fall through) and BGETV enters
; at &8551 (SEC; JSR here). The carry flag is preserved via
; PHP/PLP through the call chain and tested later (BCS) to
; select byte-stream transmission (BSXMIT) vs normal FS
; transmission (FSXMIT) -- a control-flow encoding using
; processor flags to avoid an extra flag variable.
; 
; BSXMIT uses handle=0 for print stream transactions (which
; sidestep the SEQNOS sequence number manipulation) and non-zero
; handles for file operations. After transmission, the high
; pointer bytes of the CB are reset to &FF -- "The BGET/PUT byte
; fix" which prevents stale buffer pointers corrupting subsequent
; byte-level operations.
; 
; On Entry:
;     C: 0 for BPUT (write byte), 1 for BGET (read byte)
;     A: byte to write (BPUT only)
;     Y: file handle
; 
; On Exit:
;     A: preserved
;     X: preserved
;     Y: preserved
; ***************************************************************************************
.handle_bput_bget
    pha                                                               ; 8405: 48          H              ; Save A (BPUT byte) on stack
    sta fs_error_flags                                                ; 8406: 8d df 0f    ...            ; Also save byte at &0FDF for BSXMIT
    txa                                                               ; 8409: 8a          .              ; Transfer X for stack save
    pha                                                               ; 840a: 48          H              ; Save X on stack
    tya                                                               ; 840b: 98          .              ; Transfer Y (handle) for stack save
    pha                                                               ; 840c: 48          H              ; Save Y (handle) on stack
    php                                                               ; 840d: 08          .              ; Save P (C = BPUT/BGET selector) on stack
    sty fs_spool_handle                                               ; 840e: 84 ba       ..             ; Save handle for SPOOL/EXEC comparison later
    jsr handle_to_mask_clc                                            ; 8410: 20 89 86     ..            ; Convert handle Y to single-bit mask
    sty fs_handle_mask                                                ; 8413: 8c de 0f    ...            ; Store handle bitmask at &0FDE
    sty fs_spool0                                                     ; 8416: 84 cf       ..             ; Store handle bitmask for sequence tracking
    ldy #&90                                                          ; 8418: a0 90       ..             ; &90 = data port (PREPLY)
    sty fs_putb_buf                                                   ; 841a: 8c dc 0f    ...            ; Store reply port in command buffer
    jsr init_tx_ctrl_block                                            ; 841d: 20 83 83     ..            ; Set up 12-byte TXCB from template
    lda #&dc                                                          ; 8420: a9 dc       ..             ; CB reply buffer at &0FDC
    sta txcb_start                                                    ; 8422: 85 c4       ..             ; Store reply buffer ptr low in TXCB
    lda #&e0                                                          ; 8424: a9 e0       ..             ; Error buffer at &0FE0
    sta txcb_end                                                      ; 8426: 85 c8       ..             ; Store error buffer ptr low in TXCB
    iny                                                               ; 8428: c8          .              ; Y=1 (from init_tx_ctrl_block exit)
    ldx #9                                                            ; 8429: a2 09       ..             ; X=9: BPUT function code
    plp                                                               ; 842b: 28          (              ; Restore C: selects BPUT (0) vs BGET (1)
    bcc store_retry_count                                             ; 842c: 90 01       ..             ; C=0 (BPUT): keep X=9
    dex                                                               ; 842e: ca          .              ; X=&08
; &842f referenced 1 time by &842c
.store_retry_count
    stx fs_getb_buf                                                   ; 842f: 8e dd 0f    ...            ; Store function code at &0FDD
    lda fs_spool0                                                     ; 8432: a5 cf       ..             ; Load handle bitmask for BSXMIT
    ldx #&c0                                                          ; 8434: a2 c0       ..             ; X=&C0: TXCB address for econet_tx_retry
    jsr econet_tx_retry                                               ; 8436: 20 69 92     i.            ; Transmit via byte-stream protocol
    ldx fs_getb_buf                                                   ; 8439: ae dd 0f    ...            ; Load reply byte from buffer
    beq update_sequence_return                                        ; 843c: f0 48       .H             ; Zero reply = success, skip error handling
    ldy #&1f                                                          ; 843e: a0 1f       ..             ; Copy 32-byte reply to error buffer at &0FE0
; &8440 referenced 1 time by &8447
.error1
    lda fs_putb_buf,y                                                 ; 8440: b9 dc 0f    ...            ; Load reply byte at offset Y
    sta fs_error_buf,y                                                ; 8443: 99 e0 0f    ...            ; Store to error buffer at &0FE0+Y
    dey                                                               ; 8446: 88          .              ; Next byte (descending)
    bpl error1                                                        ; 8447: 10 f7       ..             ; Loop until all 32 bytes copied
    tax                                                               ; 8449: aa          .              ; X=File handle
    lda #osbyte_read_write_exec_file_handle                           ; 844a: a9 c6       ..             ; A=&C6: read *EXEC file handle
    jsr osbyte                                                        ; 844c: 20 f4 ff     ..            ; Read/Write *EXEC file handle
    lda #&17                                                          ; 844f: a9 17       ..             ; ')': offset into "SP." string at &8529
    cpy fs_spool_handle                                               ; 8451: c4 ba       ..             ; Y=value of *SPOOL file handle
    beq close_spool_exec                                              ; 8453: f0 06       ..             ; Handle matches SPOOL -- close it
    lda #&1b                                                          ; 8455: a9 1b       ..             ; A=&1B: low byte of "E." string address
    cpx fs_spool_handle                                               ; 8457: e4 ba       ..             ; X=value of *EXEC file handle
    bne dispatch_fs_error                                             ; 8459: d0 06       ..             ; No EXEC match -- skip close
; &845b referenced 1 time by &8453
.close_spool_exec
    tax                                                               ; 845b: aa          .              ; X = string offset for OSCLI close
    ldy #&85                                                          ; 845c: a0 85       ..             ; Y=&85: high byte of OSCLI string in ROM
    jsr oscli                                                         ; 845e: 20 f7 ff     ..            ; Close SPOOL/EXEC via "*SP." or "*E."
; &8461 referenced 1 time by &8459
.dispatch_fs_error
    lda #&e0                                                          ; 8461: a9 e0       ..             ; Reset CB pointer to error buffer at &0FE0
    sta txcb_start                                                    ; 8463: 85 c4       ..             ; Reset reply ptr to error buffer
    ldx fs_getb_buf                                                   ; 8465: ae dd 0f    ...            ; Reload reply byte for error dispatch
; ***************************************************************************************
; Handle fileserver error replies (FSERR)
; 
; The fileserver returns errors as: zero command code + error number +
; CR-terminated message string. This routine converts the reply buffer
; in-place to a standard MOS BRK error packet by:
;   1. Storing the error code at fs_last_error (&0E09)
;   2. Normalizing error codes below &A8 to &A8 (the standard FS error
;      number), since the MOS error space below &A8 has other meanings
;   3. Scanning for the CR terminator and replacing it with &00
;   4. JMPing indirect through (l00c4) to execute the buffer as a BRK
;      instruction — the zero command code serves as the BRK opcode
; N.B. This relies on the fileserver always returning a zero command
; code in position 0 of the reply buffer.
; ***************************************************************************************
; &8468 referenced 1 time by &83f3
.store_fs_error
    stx fs_last_error                                                 ; 8468: 8e 09 0e    ...            ; Remember raw FS error code
    ldy #1                                                            ; 846b: a0 01       ..             ; Y=1: point to error number byte in reply
    cpx #&a8                                                          ; 846d: e0 a8       ..             ; Clamp FS errors below &A8 to standard &A8
    bcs error_code_clamped                                            ; 846f: b0 04       ..             ; Error >= &A8: keep original value
    lda #&a8                                                          ; 8471: a9 a8       ..             ; Error < &A8: override with standard &A8
    sta (txcb_start),y                                                ; 8473: 91 c4       ..             ; Write clamped error number to reply buffer
; &8475 referenced 1 time by &846f
.error_code_clamped
    ldy #&ff                                                          ; 8475: a0 ff       ..             ; Start scanning from offset &FF (will INY to 0)
; &8477 referenced 1 time by &847f
.copy_error_to_brk
    iny                                                               ; 8477: c8          .              ; Next byte in reply buffer
    lda (txcb_start),y                                                ; 8478: b1 c4       ..             ; Copy reply buffer to &0100 for BRK execution
    sta error_block,y                                                 ; 847a: 99 00 01    ...            ; Build BRK error block at &0100
    eor #&0d                                                          ; 847d: 49 0d       I.             ; Scan for CR terminator (&0D)
    bne copy_error_to_brk                                             ; 847f: d0 f6       ..             ; Continue until CR found
    sta error_block,y                                                 ; 8481: 99 00 01    ...            ; Replace CR with zero = BRK error block end
    beq execute_downloaded                                            ; 8484: f0 52       .R             ; Execute as BRK error block at &0100; ALWAYS; ALWAYS branch

; &8486 referenced 1 time by &843c
.update_sequence_return
    sta fs_sequence_nos                                               ; 8486: 8d 08 0e    ...            ; Save updated sequence number
    pla                                                               ; 8489: 68          h              ; Restore Y from stack
    tay                                                               ; 848a: a8          .              ; Transfer A to Y for indexing
    pla                                                               ; 848b: 68          h              ; Restore X from stack
    tax                                                               ; 848c: aa          .              ; Transfer to X for return
    pla                                                               ; 848d: 68          h              ; Restore A from stack
; &848e referenced 1 time by &8493
.return_remote_cmd
    rts                                                               ; 848e: 60          `              ; Return to caller

; ***************************************************************************************
; Check for pending escape condition
; 
; Tests bit 7 of the MOS escape flag (&FF) ANDed with the
; escapable flag. If no escape is pending, returns immediately.
; If escape is active, acknowledges it via OSBYTE &7E and jumps
; to the escape error handler.
; 
; On Exit:
;     A: corrupted (AND result on normal return)
; ***************************************************************************************
; &848f referenced 2 times by &80a9, &8615
.check_escape
    lda escape_flag                                                   ; 848f: a5 ff       ..             ; Read escape flag from MOS workspace
    and escapable                                                     ; 8491: 25 97       %.             ; Mask with escapable: bit 7 set if active
    bpl return_remote_cmd                                             ; 8493: 10 f9       ..             ; No escape pending: return
    lda #osbyte_acknowledge_escape                                    ; 8495: a9 7e       .~             ; OSBYTE &7E: acknowledge escape condition
    jsr osbyte                                                        ; 8497: 20 f4 ff     ..            ; Clear escape condition and perform escape effects
    jmp nlisne                                                        ; 849a: 4c 00 85    L..            ; Report escape error via error message table

; ***************************************************************************************
; Remote boot/execute handler
; 
; Checks byte 4 of the RX control block (remote status flag).
; If zero (not currently remoted), falls through to remot1 to
; set up a new remote session. If non-zero (already remoted),
; jumps to clear_jsr_protection and returns.
; ***************************************************************************************
.lang_1_remote_boot
    ldy #4                                                            ; 849d: a0 04       ..             ; Y=4: remote status flag offset
    lda (net_rx_ptr),y                                                ; 849f: b1 9c       ..             ; Read remote status from RX CB
    beq remot1                                                        ; 84a1: f0 03       ..             ; Zero: not remoted, set up session
; &84a3 referenced 1 time by &84e9
.rchex
    jmp clear_jsr_protection                                          ; 84a3: 4c f3 92    L..            ; Already remoted: clear and return

; &84a6 referenced 2 times by &84a1, &84df
.remot1
    ora #9                                                            ; 84a6: 09 09       ..             ; Set remote status: bits 0+3 (ORA #9)
    sta (net_rx_ptr),y                                                ; 84a8: 91 9c       ..             ; Store updated remote status
    ldx #&80                                                          ; 84aa: a2 80       ..             ; X=&80: RX data area offset
    ldy #&80                                                          ; 84ac: a0 80       ..             ; Y=&80: read source station low
    lda (net_rx_ptr),y                                                ; 84ae: b1 9c       ..             ; Read source station lo from RX data at &80
    pha                                                               ; 84b0: 48          H              ; Save source station low byte
    iny                                                               ; 84b1: c8          .              ; Y=&81
    lda (net_rx_ptr),y                                                ; 84b2: b1 9c       ..             ; Read source station hi from RX data at &81
    ldy #&0f                                                          ; 84b4: a0 0f       ..             ; Save controlling station to workspace &0E/&0F
    sta (nfs_workspace),y                                             ; 84b6: 91 9e       ..             ; Store station high to ws+&0F
    dey                                                               ; 84b8: 88          .              ; Y=&0E; Y=&0e
    pla                                                               ; 84b9: 68          h              ; Restore source station low
    sta (nfs_workspace),y                                             ; 84ba: 91 9e       ..             ; Store station low to ws+&0E
    jsr clear_osbyte_ce_cf                                            ; 84bc: 20 c0 81     ..            ; Clear OSBYTE &CE/&CF flags
    jsr ctrl_block_setup                                              ; 84bf: 20 8b 91     ..            ; Set up TX control block
    ldx #1                                                            ; 84c2: a2 01       ..             ; X=1: disable keyboard
    ldy #0                                                            ; 84c4: a0 00       ..             ; Y=0 for OSBYTE
    lda #osbyte_read_write_econet_keyboard_disable                    ; 84c6: a9 c9       ..             ; Disable keyboard for remote session
    jsr osbyte                                                        ; 84c8: 20 f4 ff     ..            ; Disable keyboard (for Econet)
; ***************************************************************************************
; Execute code at &0100
; 
; Clears JSR protection, zeroes &0100-&0102 (creating a BRK
; instruction at &0100 as a safe default), then JMP &0100 to
; execute code received over the network. If no code was loaded,
; the BRK triggers an error handler.
; ***************************************************************************************
.lang_3_execute_at_0100
    jsr clear_jsr_protection                                          ; 84cb: 20 f3 92     ..            ; Allow JSR to page 1 (stack page)
    ldx #2                                                            ; 84ce: a2 02       ..             ; Zero bytes &0100-&0102
    lda #0                                                            ; 84d0: a9 00       ..             ; A=0: zero execution header bytes
; &84d2 referenced 1 time by &84d6
.zero_exec_header
    sta error_block,x                                                 ; 84d2: 9d 00 01    ...            ; BRK at &0100 as safe default
    dex                                                               ; 84d5: ca          .              ; Next byte
    bpl zero_exec_header                                              ; 84d6: 10 fa       ..             ; Loop until all zeroed
; &84d8 referenced 2 times by &8484, &8511
.execute_downloaded
    jmp error_block                                                   ; 84d8: 4c 00 01    L..            ; Execute downloaded code

; ***************************************************************************************
; Remote operation with source validation
; 
; Validates that the source station in the received packet matches
; the controlling station stored in the NFS workspace. If byte 4 of
; the RX control block is zero (not currently remoted), allows the
; new remote session via remot1. If non-zero, compares the source
; station at RX offset &80 against workspace offset &0E -- rejects
; mismatched stations via clear_jsr_protection, accepts matching
; stations by falling through to lang_0_insert_remote_key.
; ***************************************************************************************
.lang_4_remote_validated
    ldy #4                                                            ; 84db: a0 04       ..             ; Y=4: RX control block byte 4 (remote status)
    lda (net_rx_ptr),y                                                ; 84dd: b1 9c       ..             ; Read remote status flag
    beq remot1                                                        ; 84df: f0 c5       ..             ; Zero = not remoted; allow new session
    ldy #&80                                                          ; 84e1: a0 80       ..             ; Read source station from RX data at &80
    lda (net_rx_ptr),y                                                ; 84e3: b1 9c       ..             ; A = source station number
    ldy #&0e                                                          ; 84e5: a0 0e       ..             ; Compare against controlling station at &0E
    cmp (nfs_workspace),y                                             ; 84e7: d1 9e       ..             ; Check if source matches controller
    bne rchex                                                         ; 84e9: d0 b8       ..             ; Reject: source != controlling station
; ***************************************************************************************
; Insert remote keypress
; 
; Reads a character from RX block offset &82 and inserts it into
; keyboard input buffer 0 via OSBYTE &99.
; ***************************************************************************************
.lang_0_insert_remote_key
    ldy #&82                                                          ; 84eb: a0 82       ..             ; Read keypress from RX data at &82
    lda (net_rx_ptr),y                                                ; 84ed: b1 9c       ..             ; Load character byte
    tay                                                               ; 84ef: a8          .              ; Y = character to insert
    ldx #0                                                            ; 84f0: a2 00       ..             ; X = buffer 0 (keyboard input)
    jsr clear_jsr_protection                                          ; 84f2: 20 f3 92     ..            ; Release JSR protection before inserting key
    lda #osbyte_insert_input_buffer                                   ; 84f5: a9 99       ..             ; OSBYTE &99: insert char into input buffer
    jmp osbyte                                                        ; 84f7: 4c f4 ff    L..            ; Tail call: insert character Y into buffer X; Insert character Y into input buffer X

; &84fa referenced 1 time by &854e
.error_not_listening
    lda #8                                                            ; 84fa: a9 08       ..             ; Error code 8: "Not listening" error
    bne set_listen_offset                                             ; 84fc: d0 04       ..             ; ALWAYS branch to set_listen_offset; ALWAYS branch

; &84fe referenced 1 time by &862e
.nlistn
    lda (net_tx_ptr,x)                                                ; 84fe: a1 9a       ..             ; Load TX status byte for error lookup
; &8500 referenced 2 times by &849a, &8a2e
.nlisne
    and #7                                                            ; 8500: 29 07       ).             ; Mask to 3-bit error code (0-7)
; &8502 referenced 1 time by &84fc
.set_listen_offset
    tax                                                               ; 8502: aa          .              ; X = error code index
    ldy error_offsets,x                                               ; 8503: bc 14 80    ...            ; Look up error message offset from table
    ldx #0                                                            ; 8506: a2 00       ..             ; X=0: start writing at &0101
    stx error_block                                                   ; 8508: 8e 00 01    ...            ; Store BRK opcode at &0100
; &850b referenced 1 time by &8515
.copy_error_message
    lda error_msg_table,y                                             ; 850b: b9 6e 85    .n.            ; Load error message byte
    sta error_text,x                                                  ; 850e: 9d 01 01    ...            ; Build error message at &0101+
    beq execute_downloaded                                            ; 8511: f0 c5       ..             ; Zero byte = end of message; go execute BRK
    iny                                                               ; 8513: c8          .              ; Next source byte
    inx                                                               ; 8514: e8          .              ; Next dest byte
    bne copy_error_message                                            ; 8515: d0 f4       ..             ; Continue copying message
    equs "SP."                                                        ; 8517: 53 50 2e    SP.            ; "SP." remote spool command string
    equb &0d, &45, &2e, &0d                                           ; 851a: 0d 45 2e... .E.            ; CR + "E." + CR remote exec strings

; ***************************************************************************************
; Load '*' prefix and send FS command (WAITFS)
; 
; Loads A with &2A ('*') as the FS command prefix byte, then
; falls through to send_to_fs to perform a full fileserver
; transaction: transmit and wait for reply.
; 
; On Exit:
;     A: reply command code
; ***************************************************************************************
; &851e referenced 5 times by &83e5, &876d, &8896, &903e, &929e
.waitfs
    lda #&2a ; '*'                                                    ; 851e: a9 2a       .*             ; A = '*' for FS command prefix
; ***************************************************************************************
; Send command to fileserver and handle reply (WAITFS)
; 
; Performs a complete FS transaction: transmit then wait for reply.
; Sets bit 7 of rx_flags (mark FS transaction in progress),
; builds a TX frame from the data at (net_tx_ptr), and transmits
; it. The system RX flag (LFLAG bit 7) is only set when receiving
; into the page-zero control block — if RXCBP's high byte is
; non-zero, setting the system flag would interfere with other RX
; operations. The timeout counter uses the stack (indexed via TSX)
; rather than memory to avoid bus conflicts with Econet hardware
; during the tight polling loop. Handles multi-block replies and
; checks for escape conditions between blocks.
; 
; On Entry:
;     A: function code / command prefix byte
; 
; On Exit:
;     A: reply command code
; ***************************************************************************************
.send_to_fs
    pha                                                               ; 8520: 48          H              ; Save function code on stack
.send_to_fs_star
    lda rx_flags                                                      ; 8521: ad 64 0d    .d.            ; Load current rx_flags
    pha                                                               ; 8524: 48          H              ; Save rx_flags on stack for restore
    ldx net_tx_ptr_hi                                                 ; 8525: a6 9b       ..             ; Only flag rx_flags if using page-zero CB
    bne skip_rx_flag_set                                              ; 8527: d0 05       ..             ; High byte != 0: skip flag set
    ora #&80                                                          ; 8529: 09 80       ..             ; Set bit7: FS transaction in progress
    sta rx_flags                                                      ; 852b: 8d 64 0d    .d.            ; Write back updated rx_flags
; &852e referenced 1 time by &8527
.skip_rx_flag_set
    lda #0                                                            ; 852e: a9 00       ..             ; Push two zero bytes as timeout counters
    pha                                                               ; 8530: 48          H              ; First zero for timeout
    pha                                                               ; 8531: 48          H              ; Second zero for timeout
    tay                                                               ; 8532: a8          .              ; Y=0: index for flag byte check; Y=&00
    tsx                                                               ; 8533: ba          .              ; TSX: index stack-based timeout via X
; &8534 referenced 3 times by &853b, &8540, &8545
.incpx
    lda (net_tx_ptr),y                                                ; 8534: b1 9a       ..             ; Read flag byte from TX control block
    bmi fs_wait_cleanup                                               ; 8536: 30 0f       0.             ; Bit 7 set = reply received
    dec error_text,x                                                  ; 8538: de 01 01    ...            ; Three-stage nested timeout: inner loop
    bne incpx                                                         ; 853b: d0 f7       ..             ; Inner not expired: keep polling
    dec stk_timeout_mid,x                                             ; 853d: de 02 01    ...            ; Middle timeout loop
    bne incpx                                                         ; 8540: d0 f2       ..             ; Middle not expired: keep polling
    dec stk_timeout_hi,x                                              ; 8542: de 04 01    ...            ; Outer timeout loop (slowest)
    bne incpx                                                         ; 8545: d0 ed       ..             ; Outer not expired: keep polling
; &8547 referenced 1 time by &8536
.fs_wait_cleanup
    pla                                                               ; 8547: 68          h              ; Pop first timeout byte
    pla                                                               ; 8548: 68          h              ; Pop second timeout byte
    pla                                                               ; 8549: 68          h              ; Pop saved rx_flags into A
    sta rx_flags                                                      ; 854a: 8d 64 0d    .d.            ; Restore saved rx_flags from stack
    pla                                                               ; 854d: 68          h              ; Pop saved function code
    beq error_not_listening                                           ; 854e: f0 aa       ..             ; A=saved func code; zero would mean no reply
    rts                                                               ; 8550: 60          `              ; Return to caller

.bgetv_handler
    sec                                                               ; 8551: 38          8              ; C=1: flag for BGET mode
    jsr bgetv_entry                                                   ; 8552: 20 02 84     ..            ; Handle BGET via FS command
    sec                                                               ; 8555: 38          8              ; SEC: set carry for error check
    lda #&fe                                                          ; 8556: a9 fe       ..             ; A=&FE: mask for EOF check
    bit fs_error_flags                                                ; 8558: 2c df 0f    ,..            ; BIT l0fdf: test error flags
    bvs return_4                                                      ; 855b: 70 10       p.             ; V=1: error, return early
    clc                                                               ; 855d: 18          .              ; CLC: no error
    php                                                               ; 855e: 08          .              ; Save flags for EOF check
    lda fs_spool0                                                     ; 855f: a5 cf       ..             ; Load BGET result byte
    plp                                                               ; 8561: 28          (              ; Restore flags
    bmi bgetv_shared_jsr                                              ; 8562: 30 03       0.             ; Bit7 set: skip FS flag clear
    jsr clear_fs_flag                                                 ; 8564: 20 c3 86     ..            ; Clear FS flag for handle
; &8567 referenced 1 time by &8562
.bgetv_shared_jsr
error_table_base = bgetv_shared_jsr+1
    jsr set_fs_flag                                                   ; 8567: 20 be 86     ..            ; Set EOF flag for this handle
.load_handle_mask
    lda fs_handle_mask                                                ; 856a: ad de 0f    ...            ; Load handle bitmask for caller
; &856d referenced 1 time by &855b
.return_4
    rts                                                               ; 856d: 60          `              ; Return with handle mask in A

; Econet error message table (ERRTAB, 7 entries).
; Each entry: error number byte followed by NUL-terminated string.
;   &A0: "Line Jammed"     &A1: "Net Error"
;   &A2: "Not listening"   &A3: "No Clock"
;   &11: "Escape"           &CB: "Bad Option"
;   &A5: "No reply"
; Indexed by the low 3 bits of the TXCB flag byte (AND #&07),
; which encode the specific Econet failure reason. The NREPLY
; and NLISTN routines build a MOS BRK error block at &100 on the
; stack page: NREPLY fires when the fileserver does not respond
; within the timeout period; NLISTN fires when the destination
; station actively refused the connection.
; Indexed via c84FA/nlistn/nlisne at &84FA-&850B.
; &856e referenced 1 time by &850b
.error_msg_table
    equb &a0                                                          ; 856e: a0          .              ; Error &A0: Line Jammed
    equs "Line Jamme"                                                 ; 856f: 4c 69 6e... Lin            ; "Line Jammed" string
    equb &64                                                          ; 8579: 64          d              ; Terminator + error &A1
    equs 0                                                            ; 857a: 00          .              ; NUL terminator
    equb &a1                                                          ; 857b: a1          .              ; Error &A1: Net Error
    equs "Net Error", 0                                               ; 857c: 4e 65 74... Net            ; "Net Error" string
    equb &a2                                                          ; 8586: a2          .              ; Error &A2: Not listening
    equs "Not listening", 0                                           ; 8587: 4e 6f 74... Not            ; "Not listening" string
    equb &a3                                                          ; 8595: a3          .              ; Error &A3: No Clock
    equs "No Clock", 0                                                ; 8596: 4e 6f 20... No             ; "No Clock" string
    equb &11                                                          ; 859f: 11          .              ; Error &11: Escape
    equs "Escape", 0                                                  ; 85a0: 45 73 63... Esc            ; "Escape" string
    equb &cb                                                          ; 85a7: cb          .              ; Error &CB: Bad Option
    equs "Bad Option", 0                                              ; 85a8: 42 61 64... Bad            ; "Bad Option" string
    equb &a5                                                          ; 85b3: a5          .              ; Error &A5: No reply
    equs "No reply", 0                                                ; 85b4: 4e 6f 20... No             ; "No reply" string

; ***************************************************************************************
; Decode file attributes: FS → BBC format (FSBBC, 6-bit variant)
; 
; Reads attribute byte at offset &0E from the parameter block,
; masks to 6 bits, then falls through to the shared bitmask
; builder. Converts fileserver protection format (5-6 bits) to
; BBC OSFILE attribute format (8 bits) via the lookup table at
; &85DA. The two formats use different bit layouts for file
; protection attributes.
; 
; On Exit:
;     A: BBC attribute bitmask (8-bit)
;     X: corrupted
;     Y: &0E
; ***************************************************************************************
; &85bd referenced 2 times by &88e9, &8914
.decode_attribs_6bit
    ldy #&0e                                                          ; 85bd: a0 0e       ..             ; Y=&0E: attribute byte offset in param block
    lda (fs_options),y                                                ; 85bf: b1 bb       ..             ; Load FS attribute byte
    and #&3f ; '?'                                                    ; 85c1: 29 3f       )?             ; Mask to 6 bits (FS → BBC direction)
    ldx #4                                                            ; 85c3: a2 04       ..             ; X=4: skip first 4 table entries (BBC→FS half)
    bne attrib_shift_bits                                             ; 85c5: d0 04       ..             ; ALWAYS branch to shared bitmask builder; ALWAYS branch

; ***************************************************************************************
; Decode file attributes: BBC → FS format (BBCFS, 5-bit variant)
; 
; Masks A to 5 bits and builds an access bitmask via the
; lookup table at &85DA. Each input bit position maps to a
; different output bit via the table. The conversion is done
; by iterating through the source bits and OR-ing in the
; corresponding destination bits from the table, translating
; between BBC (8-bit) and fileserver (5-bit) protection formats.
; 
; On Entry:
;     A: BBC attribute byte (bits 0-4 used)
; 
; On Exit:
;     A: FS attribute bitmask (5-bit)
;     X: corrupted
; ***************************************************************************************
; &85c7 referenced 2 times by &880d, &8931
.decode_attribs_5bit
    and #&1f                                                          ; 85c7: 29 1f       ).             ; Mask to 5 bits (BBC → FS direction)
    ldx #&ff                                                          ; 85c9: a2 ff       ..             ; X=&FF: INX makes 0; start from table index 0
; &85cb referenced 1 time by &85c5
.attrib_shift_bits
    sta fs_error_ptr                                                  ; 85cb: 85 b8       ..             ; Temp storage for source bitmask to shift out
    lda #0                                                            ; 85cd: a9 00       ..             ; A=0: accumulate destination bits here
; &85cf referenced 1 time by &85d7
.map_attrib_bits
    inx                                                               ; 85cf: e8          .              ; Next table entry
    lsr fs_error_ptr                                                  ; 85d0: 46 b8       F.             ; Shift out source bits one at a time
    bcc skip_set_attrib_bit                                           ; 85d2: 90 03       ..             ; Bit was 0: skip this destination bit
    ora access_bit_table,x                                            ; 85d4: 1d da 85    ...            ; OR in destination bit from lookup table
; &85d7 referenced 1 time by &85d2
.skip_set_attrib_bit
    bne map_attrib_bits                                               ; 85d7: d0 f6       ..             ; Loop while source bits remain (A != 0)
    rts                                                               ; 85d9: 60          `              ; Return; A = converted attribute bitmask

; &85da referenced 1 time by &85d4
.access_bit_table
    equb &50, &20, 5, 2, &88, 4, 8, &80, &10, 1, 2                    ; 85da: 50 20 05... P .            ; Attribute bit mapping table (11 entries)

; ***************************************************************************************
; Set up TX pointer to control block at &00C0
; 
; Points net_tx_ptr to &00C0 where the TX control block has
; been built by init_tx_ctrl_block. Falls through to tx_poll_ff
; to initiate transmission with full retry.
; 
; On Exit:
;     A: &FF (retry count, restored)
;     X: 0
;     Y: 0
; ***************************************************************************************
; &85e5 referenced 2 times by &83dd, &8885
.setup_tx_ptr_c0
    ldx #&c0                                                          ; 85e5: a2 c0       ..             ; TX control block low byte
    stx net_tx_ptr                                                    ; 85e7: 86 9a       ..             ; Set net_tx_ptr = &00C0
    ldx #0                                                            ; 85e9: a2 00       ..             ; TX control block high byte
    stx net_tx_ptr_hi                                                 ; 85eb: 86 9b       ..             ; Set net_tx_ptr+1 = &00
; ***************************************************************************************
; Transmit and poll for result (full retry)
; 
; Sets A=&FF (retry count) and Y=&60 (timeout parameter).
; Falls through to tx_poll_core.
; 
; On Exit:
;     A: &FF (retry count, restored)
;     X: 0
;     Y: 0
; ***************************************************************************************
; &85ed referenced 4 times by &9027, &9080, &90dd, &927c
.tx_poll_ff
    lda #&ff                                                          ; 85ed: a9 ff       ..             ; A=&FF: full retry count
.tx_poll_timeout
    ldy #&60 ; '`'                                                    ; 85ef: a0 60       .`             ; Y=timeout parameter (&60 = standard)
; ***************************************************************************************
; Core transmit and poll routine (XMIT)
; 
; Claims the TX semaphore (tx_clear_flag) via ASL -- a busy-wait
; spinlock where carry=0 means the semaphore is held by another
; operation. Only after claiming the semaphore is the TX pointer
; copied to nmi_tx_block, ensuring the low-level transmit code
; sees a consistent pointer. Then calls the ADLC TX setup routine
; and polls the control byte for completion:
;   bit 7 set = still busy (loop)
;   bit 6 set = error (check escape or report)
;   bit 6 clear = success (clean return)
; On error, checks for escape condition and handles retries.
; Two entry points: setup_tx_ptr_c0 (&85E5) always uses the
; standard TXCB; tx_poll_core (&85F1) is general-purpose.
; 
; On Entry:
;     A: retry count (&FF = full retry)
;     Y: timeout parameter (&60 = standard)
; 
; On Exit:
;     A: entry A (retry count, restored from stack)
;     X: 0
;     Y: 0
; ***************************************************************************************
.tx_poll_core
    pha                                                               ; 85f1: 48          H              ; Save retry count and timeout on stack
    tya                                                               ; 85f2: 98          .              ; Transfer timeout to A
    pha                                                               ; 85f3: 48          H              ; Push timeout parameter
    ldx #0                                                            ; 85f4: a2 00       ..             ; X=0 for (zp,X) indirect addressing
    lda (net_tx_ptr,x)                                                ; 85f6: a1 9a       ..             ; Read control byte from TX block
; &85f8 referenced 1 time by &862b
.rearm_tx_attempt
    sta (net_tx_ptr,x)                                                ; 85f8: 81 9a       ..             ; Write back control byte (re-arm for TX)
    pha                                                               ; 85fa: 48          H              ; Save control byte for error recovery
; &85fb referenced 1 time by &85fe
.poll_tx_semaphore
    asl tx_clear_flag                                                 ; 85fb: 0e 62 0d    .b.            ; Spin until TX semaphore is free (C=1)
    bcc poll_tx_semaphore                                             ; 85fe: 90 fb       ..             ; C=0: still held, keep spinning
    lda net_tx_ptr                                                    ; 8600: a5 9a       ..             ; Copy TX pointer to NMI block while locked
    sta nmi_tx_block                                                  ; 8602: 85 a0       ..             ; Store low byte to NMI TX block
    lda net_tx_ptr_hi                                                 ; 8604: a5 9b       ..             ; Load TX pointer high byte
    sta nmi_tx_block_hi                                               ; 8606: 85 a1       ..             ; Store high byte to NMI TX block
    jsr start_adlc_tx                                                 ; 8608: 20 50 96     P.            ; Initiate ADLC transmission
; &860b referenced 1 time by &860d
.poll_tx_complete
    lda (net_tx_ptr,x)                                                ; 860b: a1 9a       ..             ; Poll: wait for bit 7 to clear (TX done)
    bmi poll_tx_complete                                              ; 860d: 30 fc       0.             ; Bit 7 set: still busy, keep polling
    asl a                                                             ; 860f: 0a          .              ; Bit 6 into sign: 0=success, 1=error
    bpl tx_success_exit                                               ; 8610: 10 1f       ..             ; Success: clean up stack and exit
    asl a                                                             ; 8612: 0a          .              ; Bit 5: escape condition?
    beq tx_abort                                                      ; 8613: f0 18       ..             ; Yes (Z=1): abort via nlistn
    jsr check_escape                                                  ; 8615: 20 8f 84     ..            ; Check for escape key pressed
    pla                                                               ; 8618: 68          h              ; Recover saved control byte
    tax                                                               ; 8619: aa          .              ; Move to X for retry
    pla                                                               ; 861a: 68          h              ; Recover timeout parameter
    tay                                                               ; 861b: a8          .              ; Move to Y for delay loop
    pla                                                               ; 861c: 68          h              ; Recover retry count
    beq tx_abort                                                      ; 861d: f0 0e       ..             ; Retries exhausted: abort via nlistn
    sbc #1                                                            ; 861f: e9 01       ..             ; Decrement retry count (C=1 from CMP)
    pha                                                               ; 8621: 48          H              ; Re-push retry count and timeout for retry
    tya                                                               ; 8622: 98          .              ; Transfer timeout to A
    pha                                                               ; 8623: 48          H              ; Push timeout for next attempt
    txa                                                               ; 8624: 8a          .              ; Restore control byte for retry
; &8625 referenced 2 times by &8626, &8629
.tx_retry_delay
    dex                                                               ; 8625: ca          .              ; Delay loop: X*Y iterations before retry
    bne tx_retry_delay                                                ; 8626: d0 fd       ..             ; Inner loop: decrement X
    dey                                                               ; 8628: 88          .              ; Outer loop: decrement Y
    bne tx_retry_delay                                                ; 8629: d0 fa       ..             ; Continue delay until Y=0
    beq rearm_tx_attempt                                              ; 862b: f0 cb       ..             ; ALWAYS branch

; &862d referenced 2 times by &8613, &861d
.tx_abort
    tax                                                               ; 862d: aa          .              ; A = error code for nlistn
    jmp nlistn                                                        ; 862e: 4c fe 84    L..            ; Report net error via nlistn

; &8631 referenced 1 time by &8610
.tx_success_exit
    pla                                                               ; 8631: 68          h              ; Success: discard 3 saved bytes from stack
    pla                                                               ; 8632: 68          h              ; Discard timeout
    pla                                                               ; 8633: 68          h              ; Discard retry count
    jmp clear_escapable                                               ; 8634: 4c 45 86    LE.            ; Jump to clear escapable flag and return

; ***************************************************************************************
; Save FSCV arguments with text pointers
; 
; Extended entry used by FSCV, FINDV, and fscv_3_star_cmd.
; Copies X/Y into os_text_ptr/&F3 and fs_cmd_ptr/&0E11, then
; falls through to save_fscv_args to store A/X/Y in the FS
; workspace.
; 
; On Entry:
;     A: function code
;     X: text pointer low
;     Y: text pointer high
; ***************************************************************************************
; &8637 referenced 3 times by &80d0, &89c6, &8c09
.save_fscv_args_with_ptrs
    stx os_text_ptr                                                   ; 8637: 86 f2       ..             ; Set os_text_ptr low = X
    sty os_text_ptr_hi                                                ; 8639: 84 f3       ..             ; Set os_text_ptr high = Y
; ***************************************************************************************
; Save FSCV/vector arguments
; 
; Stores A, X, Y into the filing system workspace. Called at the
; start of every FS vector handler (FILEV, ARGSV, BGETV, BPUTV,
; GBPBV, FINDV, FSCV). NFS repurposes CFS/RFS workspace locations:
;   &BD (fs_last_byte_flag) = A (function code / command)
;   &BB (fs_options)        = X (control block ptr low)
;   &BC (fs_block_offset)   = Y (control block ptr high)
;   &BE/&BF (fs_crc_lo/hi)  = X/Y (duplicate for indexed access)
; 
; On Entry:
;     A: function code
;     X: control block pointer low
;     Y: control block pointer high
; ***************************************************************************************
; &863b referenced 3 times by &86fa, &8956, &8a60
.save_fscv_args
    sta fs_last_byte_flag                                             ; 863b: 85 bd       ..             ; Save A = function code / command
    stx fs_options                                                    ; 863d: 86 bb       ..             ; Save X = control block ptr low
    sty fs_block_offset                                               ; 863f: 84 bc       ..             ; Save Y = control block ptr high
    stx fs_crc_lo                                                     ; 8641: 86 be       ..             ; Duplicate X for indirect indexed access
    sty fs_crc_hi                                                     ; 8643: 84 bf       ..             ; Duplicate Y for indirect indexed access
; ***************************************************************************************
; Clear escapable flag preserving processor status
; 
; PHP/LSR escapable/PLP: clears bit 7 of the escapable flag
; while preserving the processor status register. Used at the
; start of FS vector operations to mark them as not yet
; escapable.
; ***************************************************************************************
; &8645 referenced 2 times by &8402, &8634
.clear_escapable
    php                                                               ; 8645: 08          .              ; Clear escapable flag, preserving processor flags
    lsr escapable                                                     ; 8646: 46 97       F.             ; Reset: this operation is not escapable yet
    plp                                                               ; 8648: 28          (              ; Restore flags (caller may need N/Z/C)
    rts                                                               ; 8649: 60          `              ; Return

; ***************************************************************************************
; Print inline string, high-bit terminated (VSTRNG)
; 
; Pops the return address from the stack, prints each byte via OSASCI
; until a byte with bit 7 set is found, then jumps to that address.
; The high-bit byte serves as both the string terminator and the opcode
; of the first instruction after the string. N.B. Cannot be used for
; BRK error messages -- the stack manipulation means a BRK in the
; inline data would corrupt the stack rather than invoke the error
; handler.
; 
; On Exit:
;     A: terminator byte (bit 7 set, also next opcode)
;     X: corrupted (by OSASCI)
;     Y: 0
; ***************************************************************************************
; &864a referenced 13 times by &81f6, &8220, &8240, &824d, &8c7b, &8c85, &8c93, &8c9e, &8cb3, &8cc8, &8cdb, &8cea, &8d99
.print_inline
    pla                                                               ; 864a: 68          h              ; Pop return address (low) — points to last byte of JSR
    sta fs_load_addr                                                  ; 864b: 85 b0       ..             ; Store return addr low as string ptr
    pla                                                               ; 864d: 68          h              ; Pop return address (high)
    sta fs_load_addr_hi                                               ; 864e: 85 b1       ..             ; Store return addr high as string ptr
    ldy #0                                                            ; 8650: a0 00       ..             ; Y=0: offset for indirect load
; &8652 referenced 1 time by &865f
.print_inline_char
    inc fs_load_addr                                                  ; 8652: e6 b0       ..             ; Advance pointer past return address / to next char
    bne print_next_char                                               ; 8654: d0 02       ..             ; No page wrap: skip high byte inc
    inc fs_load_addr_hi                                               ; 8656: e6 b1       ..             ; Handle page crossing in pointer
; &8658 referenced 1 time by &8654
.print_next_char
    lda (fs_load_addr),y                                              ; 8658: b1 b0       ..             ; Load next byte from inline string
    bmi jump_via_addr                                                 ; 865a: 30 06       0.             ; Bit 7 set? Done — this byte is the next opcode
    jsr osasci                                                        ; 865c: 20 e3 ff     ..            ; Write character
    jmp print_inline_char                                             ; 865f: 4c 52 86    LR.            ; Continue printing next character

; &8662 referenced 1 time by &865a
.jump_via_addr
    jmp (fs_load_addr)                                                ; 8662: 6c b0 00    l..            ; Jump to address of high-bit byte (resumes code after string)

; ***************************************************************************************
; Parse decimal number from (fs_options),Y (DECIN)
; 
; Reads ASCII digits and accumulates in &B2 (fs_load_addr_2).
; Multiplication by 10 uses the identity: n*10 = n*8 + n*2,
; computed as ASL &B2 (x2), then A = &B2*4 via two ASLs,
; then ADC &B2 gives x10.
; Terminates on "." (pathname separator), control chars, or space.
; The delimiter handling was revised to support dot-separated path
; components (e.g. "1.$.PROG") -- originally stopped on any char
; >= &40 (any letter), but the revision allows numbers followed
; by dots.
; 
; On Entry:
;     Y: offset into (fs_options) buffer
; 
; On Exit:
;     A: parsed value (accumulated in &B2)
;     X: preserved
;     Y: offset past last digit parsed
; ***************************************************************************************
; &8665 referenced 2 times by &8088, &8091
.parse_decimal
    lda #0                                                            ; 8665: a9 00       ..             ; Zero accumulator
    sta fs_load_addr_2                                                ; 8667: 85 b2       ..             ; Initialise accumulator to zero
; &8669 referenced 1 time by &8682
.scan_decimal_digit
    lda (fs_options),y                                                ; 8669: b1 bb       ..             ; Load next char from buffer
    cmp #&2e ; '.'                                                    ; 866b: c9 2e       ..             ; Dot separator?
    beq parse_decimal_rts                                             ; 866d: f0 16       ..             ; Yes: exit with C=1 (dot found)
    bcc no_dot_exit                                                   ; 866f: 90 13       ..             ; Control char or space: done
    and #&0f                                                          ; 8671: 29 0f       ).             ; Mask ASCII digit to 0-9
    sta fs_load_addr_3                                                ; 8673: 85 b3       ..             ; Save new digit
    asl fs_load_addr_2                                                ; 8675: 06 b2       ..             ; Running total * 2
    lda fs_load_addr_2                                                ; 8677: a5 b2       ..             ; A = running total * 2
    asl a                                                             ; 8679: 0a          .              ; A = running total * 4
    asl a                                                             ; 867a: 0a          .              ; A = running total * 8
    adc fs_load_addr_2                                                ; 867b: 65 b2       e.             ; + total*2 = total * 10
    adc fs_load_addr_3                                                ; 867d: 65 b3       e.             ; + digit = total*10 + digit
    sta fs_load_addr_2                                                ; 867f: 85 b2       ..             ; Store new running total
    iny                                                               ; 8681: c8          .              ; Advance to next char
    bne scan_decimal_digit                                            ; 8682: d0 e5       ..             ; Loop (always: Y won't wrap to 0)
; &8684 referenced 1 time by &866f
.no_dot_exit
    clc                                                               ; 8684: 18          .              ; No dot found: C=0
; &8685 referenced 1 time by &866d
.parse_decimal_rts
    lda fs_load_addr_2                                                ; 8685: a5 b2       ..             ; Return result in A
    rts                                                               ; 8687: 60          `              ; Return with result in A

; ***************************************************************************************
; Convert handle in A to bitmask
; 
; Transfers A to Y via TAY, then falls through to
; handle_to_mask_clc to clear carry and convert.
; 
; On Entry:
;     A: file handle number (&20-&27, or 0)
; 
; On Exit:
;     A: preserved
;     X: preserved
;     Y: bitmask (single bit set) or &FF if invalid
; ***************************************************************************************
; &8688 referenced 3 times by &889d, &8a7b, &8f5e
.handle_to_mask_a
    tay                                                               ; 8688: a8          .              ; Handle number to Y for conversion
; ***************************************************************************************
; Convert handle to bitmask (carry cleared)
; 
; Clears carry to ensure handle_to_mask converts
; unconditionally. Falls through to handle_to_mask.
; 
; On Entry:
;     Y: file handle number (&20-&27, or 0)
; 
; On Exit:
;     A: preserved
;     X: preserved
;     Y: bitmask (single bit set) or &FF if invalid
; ***************************************************************************************
; &8689 referenced 2 times by &8410, &8961
.handle_to_mask_clc
    clc                                                               ; 8689: 18          .              ; Force unconditional conversion
; ***************************************************************************************
; Convert file handle to bitmask (Y2FS)
; 
; Converts fileserver handles to single-bit masks segregated inside
; the BBC. NFS handles occupy the &20-&27 range (base HAND=&20),
; which cannot collide with local filing system or cassette handles
; -- the MOS routes OSFIND/OSBGET/OSBPUT to the correct filing
; system based on the handle value alone. The power-of-two encoding
; allows the EOF hint byte to track up to 8 files simultaneously
; with one bit per file, and enables fast set operations (ORA to
; add, EOR to toggle, AND to test) without loops. Handle 0 passes
; through unchanged (means "no file"). The bit-shift conversion loop
; has a built-in validity check: if the handle is out of range, the
; repeated ASL shifts all bits out, leaving A=0, which is converted
; to Y=&FF as a sentinel -- bad handles fail gracefully rather than
; indexing into garbage.
; Callers needing to move the handle from A use handle_to_mask_a;
; callers needing carry cleared use handle_to_mask_clc.
; 
; On Entry:
;     Y: handle number
;     C: 0: convert, 1 with Y=0: skip, 1 with Y!=0: convert
; 
; On Exit:
;     A: preserved
;     X: preserved
;     Y: bitmask (single bit set) or &FF if handle invalid
; ***************************************************************************************
; &868a referenced 1 time by &89ca
.handle_to_mask
    pha                                                               ; 868a: 48          H              ; Save A (will be restored on exit)
    txa                                                               ; 868b: 8a          .              ; Save X (will be restored on exit)
    pha                                                               ; 868c: 48          H              ;   (second half of X save)
    tya                                                               ; 868d: 98          .              ; A = handle from Y
    bcc y2fsl5                                                        ; 868e: 90 02       ..             ; C=0: always convert
    beq handle_mask_exit                                              ; 8690: f0 0f       ..             ; C=1 and Y=0: skip (handle 0 = none)
; &8692 referenced 1 time by &868e
.y2fsl5
    sec                                                               ; 8692: 38          8              ; C=1 and Y!=0: convert
    sbc #&1f                                                          ; 8693: e9 1f       ..             ; A = handle - &1F (1-based bit position)
    tax                                                               ; 8695: aa          .              ; X = shift count
    lda #1                                                            ; 8696: a9 01       ..             ; Start with bit 0 set
; &8698 referenced 1 time by &869a
.y2fsl2
    asl a                                                             ; 8698: 0a          .              ; Shift bit left
    dex                                                               ; 8699: ca          .              ; Count down
    bne y2fsl2                                                        ; 869a: d0 fc       ..             ; Loop until correct position
    ror a                                                             ; 869c: 6a          j              ; Undo final extra shift
    tay                                                               ; 869d: a8          .              ; Y = resulting bitmask
    bne handle_mask_exit                                              ; 869e: d0 01       ..             ; Non-zero: valid mask, skip to exit
    dey                                                               ; 86a0: 88          .              ; Zero: invalid handle, set Y=&FF
; &86a1 referenced 2 times by &8690, &869e
.handle_mask_exit
    pla                                                               ; 86a1: 68          h              ; Restore X
    tax                                                               ; 86a2: aa          .              ; Restore X from stack
    pla                                                               ; 86a3: 68          h              ; Restore A
    rts                                                               ; 86a4: 60          `              ; Return with mask in X

; ***************************************************************************************
; Convert bitmask to handle number (FS2A)
; 
; Inverse of Y2FS. Converts from the power-of-two FS format
; back to a sequential handle number by counting right shifts
; until A=0. Adds &1E to convert the 1-based bit position to
; a handle number (handles start at &1F+1 = &20). Used when
; receiving handle values from the fileserver in reply packets.
; 
; On Entry:
;     A: single-bit bitmask
; 
; On Exit:
;     A: handle number (&20-&27)
;     X: corrupted
;     Y: preserved
; ***************************************************************************************
; &86a5 referenced 2 times by &89f9, &8f76
.mask_to_handle
    ldx #&1f                                                          ; 86a5: a2 1f       ..             ; X = &1F (handle base - 1)
; &86a7 referenced 1 time by &86a9
.fs2al1
    inx                                                               ; 86a7: e8          .              ; Count this bit position
    lsr a                                                             ; 86a8: 4a          J              ; Shift mask right; C=0 when done
    bne fs2al1                                                        ; 86a9: d0 fc       ..             ; Loop until all bits shifted out
    txa                                                               ; 86ab: 8a          .              ; A = X = &1F + bit position = handle
    rts                                                               ; 86ac: 60          `              ; Return with handle in A

; ***************************************************************************************
; Compare two 4-byte addresses
; 
; Compares bytes at &B0-&B3 against &B4-&B7 using EOR.
; Used by the OSFILE save handler to compare the current
; transfer address (&C8-&CB, copied to &B0) against the end
; address (&B4-&B7) during multi-block file data transfers.
; 
; On Exit:
;     A: corrupted (EOR result)
;     X: corrupted
;     Y: preserved
; ***************************************************************************************
; &86ad referenced 2 times by &8753, &8842
.compare_addresses
    ldx #4                                                            ; 86ad: a2 04       ..             ; Compare 4 bytes (index 4,3,2,1)
; &86af referenced 1 time by &86b6
.compare_addr_byte
    lda addr_work,x                                                   ; 86af: b5 af       ..             ; Load byte from first address
    eor fs_load_addr_3,x                                              ; 86b1: 55 b3       U.             ; XOR with corresponding byte
    bne return_compare                                                ; 86b3: d0 03       ..             ; Mismatch: Z=0, return unequal
    dex                                                               ; 86b5: ca          .              ; Next byte
    bne compare_addr_byte                                             ; 86b6: d0 f7       ..             ; Continue comparing
; &86b8 referenced 1 time by &86b3
.return_compare
    rts                                                               ; 86b8: 60          `              ; Return with Z flag result

.fscv_7_read_handles
    ldx #&20 ; ' '                                                    ; 86b9: a2 20       .              ; X=first handle (&20)
    ldy #&27 ; '''                                                    ; 86bb: a0 27       .'             ; Y=last handle (&27)
.return_fscv_handles
    rts                                                               ; 86bd: 60          `              ; Return (FSCV 7 read handles)

; ***************************************************************************************
; Set bit(s) in EOF hint flags (&0E07)
; 
; ORs A into fs_eof_flags then stores the result via
; store_fs_flag. Each bit represents one of up to 8 open file
; handles. When clear, the file is definitely NOT at EOF. When
; set, the fileserver must be queried to confirm EOF status.
; This negative-cache optimisation avoids expensive network
; round-trips for the common case. The hint is cleared when
; the file pointer is updated (since seeking away from EOF
; invalidates the hint) and set after BGET/OPEN/EOF operations
; that might have reached the end.
; 
; On Entry:
;     A: bitmask of bits to set
; 
; On Exit:
;     A: updated fs_eof_flags value
; ***************************************************************************************
; &86be referenced 5 times by &8567, &899e, &89f5, &8a15, &8af6
.set_fs_flag
    ora fs_eof_flags                                                  ; 86be: 0d 07 0e    ...            ; Merge new bits into flags
    bne store_fs_flag                                                 ; 86c1: d0 05       ..             ; Store updated flags (always taken)
; ***************************************************************************************
; Clear bit(s) in FS flags (&0E07)
; 
; Inverts A (EOR #&FF), then ANDs the result into fs_eof_flags
; to clear the specified bits.
; 
; On Entry:
;     A: bitmask of bits to clear
; 
; On Exit:
;     A: updated fs_eof_flags value
; ***************************************************************************************
; &86c3 referenced 3 times by &8564, &88b8, &8af3
.clear_fs_flag
    eor #&ff                                                          ; 86c3: 49 ff       I.             ; Invert mask: set bits become clear bits
    and fs_eof_flags                                                  ; 86c5: 2d 07 0e    -..            ; Clear specified bits in flags
; &86c8 referenced 1 time by &86c1
.store_fs_flag
    sta fs_eof_flags                                                  ; 86c8: 8d 07 0e    ...            ; Write back updated flags
    rts                                                               ; 86cb: 60          `              ; Return

; ***************************************************************************************
; Copy filename pointer to os_text_ptr and parse
; 
; Copies the 2-byte filename pointer from (fs_options),Y into
; os_text_ptr (&F2/&F3), then falls through to parse_filename_gs
; to parse the filename via GSINIT/GSREAD into the &0E30 buffer.
; 
; On Exit:
;     X: length of parsed string
;     Y: 0
; ***************************************************************************************
; &86cc referenced 1 time by &86fd
.copy_filename_ptr
    ldy #1                                                            ; 86cc: a0 01       ..             ; Y=1: copy 2 bytes (high then low)
; &86ce referenced 1 time by &86d4
.file1
    lda (fs_options),y                                                ; 86ce: b1 bb       ..             ; Load filename ptr from control block
    sta os_text_ptr,y                                                 ; 86d0: 99 f2 00    ...            ; Store to MOS text pointer (&F2/&F3)
    dey                                                               ; 86d3: 88          .              ; Next byte (descending)
    bpl file1                                                         ; 86d4: 10 f8       ..             ; Loop for both bytes
; ***************************************************************************************
; Parse filename using GSINIT/GSREAD into &0E30
; 
; Uses the MOS GSINIT/GSREAD API to parse a filename string from
; (os_text_ptr),Y, handling quoted strings and |-escaped characters.
; Stores the parsed result CR-terminated at &0E30 and sets up
; fs_crc_lo/hi to point to that buffer. Sub-entry at &86D8 allows
; a non-zero starting Y offset.
; 
; On Entry:
;     Y: offset into (os_text_ptr) buffer (0 at &86D6)
; 
; On Exit:
;     X: length of parsed string
;     Y: preserved
; ***************************************************************************************
; &86d6 referenced 2 times by &89df, &8ddf
.parse_filename_gs
    ldy #0                                                            ; 86d6: a0 00       ..             ; Start from beginning of string
; ***************************************************************************************
; Parse filename via GSINIT/GSREAD from offset Y
; 
; Sub-entry of parse_filename_gs that accepts a non-zero Y offset
; into the (os_text_ptr) string. Initialises GSINIT, reads chars
; via GSREAD into &0E30, CR-terminates the result, and sets up
; fs_crc_lo/hi to point at the buffer.
; 
; On Entry:
;     Y: offset into (os_text_ptr) string
; 
; On Exit:
;     X: length of parsed string
;     Y: preserved
; ***************************************************************************************
; &86d8 referenced 1 time by &8c69
.parse_filename_gs_y
    ldx #&ff                                                          ; 86d8: a2 ff       ..             ; X=&FF: next INX wraps to first char index
    clc                                                               ; 86da: 18          .              ; C=0 for GSINIT: parse from current position
    jsr gsinit                                                        ; 86db: 20 c2 ff     ..            ; Initialise GS string parser
    beq terminate_filename                                            ; 86de: f0 0b       ..             ; Empty string: skip to CR terminator
; &86e0 referenced 1 time by &86e9
.quote1
    jsr gsread                                                        ; 86e0: 20 c5 ff     ..            ; Read next character via GSREAD
    bcs terminate_filename                                            ; 86e3: b0 06       ..             ; C=1 from GSREAD: end of string reached
    inx                                                               ; 86e5: e8          .              ; Advance buffer index
    sta fs_filename_buf,x                                             ; 86e6: 9d 30 0e    .0.            ; Store parsed character to &0E30+X
    bcc quote1                                                        ; 86e9: 90 f5       ..             ; ALWAYS loop (GSREAD clears C on success); ALWAYS branch

; &86eb referenced 2 times by &86de, &86e3
.terminate_filename
    inx                                                               ; 86eb: e8          .              ; Terminate parsed string with CR
    lda #&0d                                                          ; 86ec: a9 0d       ..             ; CR = &0D
    sta fs_filename_buf,x                                             ; 86ee: 9d 30 0e    .0.            ; Store CR terminator at end of string
    lda #&30 ; '0'                                                    ; 86f1: a9 30       .0             ; Point fs_crc_lo/hi at &0E30 parse buffer
    sta fs_crc_lo                                                     ; 86f3: 85 be       ..             ; fs_crc_lo = &30
    lda #&0e                                                          ; 86f5: a9 0e       ..             ; fs_crc_hi = &0E → buffer at &0E30
    sta fs_crc_hi                                                     ; 86f7: 85 bf       ..             ; Store high byte
    rts                                                               ; 86f9: 60          `              ; Return; X = string length

; ***************************************************************************************
; FILEV handler (OSFILE entry point)
; 
; Calls save_fscv_args (&863B) to preserve A/X/Y, then JSR &86CC
; to copy the 2-byte filename pointer from the parameter block to
; os_text_ptr and fall through to parse_filename_gs (&86D6) which
; parses the filename into &0E30+. Sets fs_crc_lo/hi to point at
; the parsed filename buffer.
; Dispatches by function code A:
;   A=&FF: load file (send_fs_examine at &8710)
;   A=&00: save file (filev_save at &8783)
;   A=&01-&06: attribute operations (filev_attrib_dispatch at &88BF)
;   Other: restore_args_return (unsupported, no-op)
; 
; On Entry:
;     A: function code (&FF=load, &00=save, &01-&06=attrs)
;     X: parameter block address low byte
;     Y: parameter block address high byte
; 
; On Exit:
;     A: restored
;     X: restored
;     Y: restored
; ***************************************************************************************
.filev_handler
    jsr save_fscv_args                                                ; 86fa: 20 3b 86     ;.            ; Save A/X/Y in FS workspace
    jsr copy_filename_ptr                                             ; 86fd: 20 cc 86     ..            ; Copy filename ptr from param block to os_text_ptr
    lda fs_last_byte_flag                                             ; 8700: a5 bd       ..             ; Recover function code from saved A
    bpl saveop                                                        ; 8702: 10 7a       .z             ; A >= 0: save (&00) or attribs (&01-&06)
    cmp #&ff                                                          ; 8704: c9 ff       ..             ; A=&FF? Only &FF is valid for load
    beq loadop                                                        ; 8706: f0 03       ..             ; A=&FF: branch to load path
    jmp restore_args_return                                           ; 8708: 4c a1 89    L..            ; Unknown negative code: no-op return

; &870b referenced 1 time by &8706
.loadop
    jsr infol2                                                        ; 870b: 20 70 8d     p.            ; Copy parsed filename to cmd buffer
    ldy #2                                                            ; 870e: a0 02       ..             ; Y=2: FS function code offset
; ***************************************************************************************
; Send FS examine command
; 
; Sends an FS examine/load command to the fileserver. The function
; code in Y is set by the caller (Y=2 for load, Y=5 for examine).
; Overwrites fs_cmd_urd (&0F02) with &92 (PLDATA port number) to
; repurpose the URD header field for the data transfer port. Sets
; escapable to &92 so escape checking is active during the transfer.
; Calls prepare_cmd_clv to build the FS header (which skips the
; normal URD copy, preserving &92). The FS reply contains load/exec
; addresses and file length used to set up the data transfer.
; Byte 6 of the parameter block selects load address handling:
; non-zero uses the address from the FS reply (load to file's own
; address); zero uses the caller-supplied address.
; 
; On Entry:
;     Y: FS function code (2=load, 5=examine)
;     X: TX buffer extent
; ***************************************************************************************
; &8710 referenced 1 time by &8e10
.send_fs_examine
    lda #&92                                                          ; 8710: a9 92       ..             ; Port &92 = PLDATA (data transfer port)
    sta escapable                                                     ; 8712: 85 97       ..             ; Mark transfer as escapable
    sta fs_cmd_urd                                                    ; 8714: 8d 02 0f    ...            ; Overwrite URD field with data port number
    jsr prepare_cmd_clv                                               ; 8717: 20 ab 83     ..            ; Build FS header (V=1: CLV path)
    ldy #6                                                            ; 871a: a0 06       ..             ; Y=6: param block byte 6
    lda (fs_options),y                                                ; 871c: b1 bb       ..             ; Byte 6: use file's own load address?
    bne lodfil                                                        ; 871e: d0 08       ..             ; Non-zero: use FS reply address (lodfil)
    jsr copy_load_addr_from_params                                    ; 8720: 20 1d 88     ..            ; Zero: copy caller's load addr first
    jsr copy_reply_to_params                                          ; 8723: 20 2f 88     /.            ; Then copy FS reply to param block
    bcc skip_lodfil                                                   ; 8726: 90 06       ..             ; Carry clear from prepare_cmd_clv: skip lodfil
; &8728 referenced 1 time by &871e
.lodfil
    jsr copy_reply_to_params                                          ; 8728: 20 2f 88     /.            ; Copy FS reply addresses to param block
    jsr copy_load_addr_from_params                                    ; 872b: 20 1d 88     ..            ; Then copy load addr from param block
; &872e referenced 1 time by &8726
.skip_lodfil
    ldy #4                                                            ; 872e: a0 04       ..             ; Compute end address = load + file length
; &8730 referenced 1 time by &873b
.copy_load_end_addr
    lda fs_load_addr,x                                                ; 8730: b5 b0       ..             ; Load address byte
    sta txcb_end,x                                                    ; 8732: 95 c8       ..             ; Store as current transfer position
    adc fs_file_len,x                                                 ; 8734: 7d 0d 0f    }..            ; Add file length byte
    sta fs_work_4,x                                                   ; 8737: 95 b4       ..             ; Store as end position
    inx                                                               ; 8739: e8          .              ; Next address byte
    dey                                                               ; 873a: 88          .              ; Decrement byte counter
    bne copy_load_end_addr                                            ; 873b: d0 f3       ..             ; Loop for all 4 address bytes
    sec                                                               ; 873d: 38          8              ; Adjust high byte for 3-byte length overflow
    sbc fs_file_len_3                                                 ; 873e: ed 10 0f    ...            ; Subtract 4th length byte from end addr
    sta fs_work_7                                                     ; 8741: 85 b7       ..             ; Store adjusted end address high byte
    jsr send_data_blocks                                              ; 8743: 20 53 87     S.            ; Transfer file data in &80-byte blocks
    ldx #2                                                            ; 8746: a2 02       ..             ; Copy 3-byte file length to FS reply cmd buffer
; &8748 referenced 1 time by &874f
.floop
    lda fs_file_len_3,x                                               ; 8748: bd 10 0f    ...            ; Load file length byte
    sta fs_cmd_data,x                                                 ; 874b: 9d 05 0f    ...            ; Store in FS command data buffer
    dex                                                               ; 874e: ca          .              ; Next byte (count down)
    bpl floop                                                         ; 874f: 10 f7       ..             ; Loop for 3 bytes (X=2,1,0)
    bmi save_csd_display                                              ; 8751: 30 73       0s             ; ALWAYS branch

; ***************************************************************************************
; Send file data in multi-block chunks
; 
; Repeatedly sends &80-byte (128-byte) blocks of file data to the
; fileserver using command &7F. Compares current address (&C8-&CB)
; against end address (&B4-&B7) via compare_addresses, and loops
; until the entire file has been transferred. Each block is sent
; via send_to_fs_star.
; ***************************************************************************************
; &8753 referenced 2 times by &8743, &8ae6
.send_data_blocks
    jsr compare_addresses                                             ; 8753: 20 ad 86     ..            ; Compare two 4-byte addresses
    beq return_lodchk                                                 ; 8756: f0 25       .%             ; Addresses match: transfer complete
    lda #&92                                                          ; 8758: a9 92       ..             ; Port &92 for data block transfer
    sta txcb_port                                                     ; 875a: 85 c1       ..             ; Store port to TXCB command byte
; &875c referenced 1 time by &8778
.send_block_loop
    ldx #3                                                            ; 875c: a2 03       ..             ; Set up next &80-byte block for transfer
; &875e referenced 1 time by &8767
.copy_block_addrs
    lda txcb_end,x                                                    ; 875e: b5 c8       ..             ; Swap: current addr -> source, end -> current
    sta txcb_start,x                                                  ; 8760: 95 c4       ..             ; Source addr = current position
    lda fs_work_4,x                                                   ; 8762: b5 b4       ..             ; Load end address byte
    sta txcb_end,x                                                    ; 8764: 95 c8       ..             ; Dest = end address (will be clamped)
    dex                                                               ; 8766: ca          .              ; Next address byte
    bpl copy_block_addrs                                              ; 8767: 10 f5       ..             ; Loop for all 4 bytes
    lda #&7f                                                          ; 8769: a9 7f       ..             ; Command &7F = data block transfer
    sta txcb_ctrl                                                     ; 876b: 85 c0       ..             ; Store to TXCB control byte
    jsr waitfs                                                        ; 876d: 20 1e 85     ..            ; Send this block to the fileserver
    ldy #3                                                            ; 8770: a0 03       ..             ; Y=3: compare 4 bytes (3..0)
; &8772 referenced 1 time by &877b
.lodchk
    lda txcb_end,y                                                    ; 8772: b9 c8 00    ...            ; Compare current vs end address (4 bytes)
    eor fs_work_4,y                                                   ; 8775: 59 b4 00    Y..            ; XOR with end address byte
    bne send_block_loop                                               ; 8778: d0 e2       ..             ; Not equal: more blocks to send
    dey                                                               ; 877a: 88          .              ; Next byte
    bpl lodchk                                                        ; 877b: 10 f5       ..             ; Loop for all 4 address bytes
; &877d referenced 1 time by &8756
.return_lodchk
    rts                                                               ; 877d: 60          `              ; All equal: transfer complete

; &877e referenced 1 time by &8702
.saveop
    beq filev_save                                                    ; 877e: f0 03       ..             ; A=0: SAVE handler
    jmp filev_attrib_dispatch                                         ; 8780: 4c bf 88    L..            ; A!=0: attribute dispatch (A=1-6)

; ***************************************************************************************
; OSFILE save handler (A=&00)
; 
; Copies 4-byte load/exec/length addresses from the parameter block
; to the FS command buffer, along with the filename. The savsiz loop
; computes data-end minus data-start for each address byte to derive
; the transfer length, saving both the original address and the
; difference. Sends FS command with port &91, function code Y=1,
; and the filename via copy_string_to_cmd. After transfer_file_blocks
; sends the data, calls send_fs_reply_cmd for the final handshake.
; If fs_messages_flag is set, prints the catalogue line inline:
; filename (padded to 12 chars), load address, exec address, and
; file length. Finally decodes the FS attributes and copies the
; reply data back into the caller's parameter block.
; ***************************************************************************************
; &8783 referenced 1 time by &877e
.filev_save
    ldx #4                                                            ; 8783: a2 04       ..             ; Process 4 address bytes (load/exec/start/end)
    ldy #&0e                                                          ; 8785: a0 0e       ..             ; Y=&0E: start from end-address in param block
; &8787 referenced 1 time by &87a1
.savsiz
    lda (fs_options),y                                                ; 8787: b1 bb       ..             ; Read end-address byte from param block
    sta port_ws_offset,y                                              ; 8789: 99 a6 00    ...            ; Save to port workspace for transfer setup
    jsr sub_4_from_y                                                  ; 878c: 20 3c 88     <.            ; Y = Y-4: point to start-address byte
    sbc (fs_options),y                                                ; 878f: f1 bb       ..             ; end - start = transfer length byte
    sta fs_cmd_csd,y                                                  ; 8791: 99 03 0f    ...            ; Store length byte in FS command buffer
    pha                                                               ; 8794: 48          H              ; Save length byte for param block restore
    lda (fs_options),y                                                ; 8795: b1 bb       ..             ; Read corresponding start-address byte
    sta port_ws_offset,y                                              ; 8797: 99 a6 00    ...            ; Save to port workspace
    pla                                                               ; 879a: 68          h              ; Restore length byte from stack
    sta (fs_options),y                                                ; 879b: 91 bb       ..             ; Replace param block entry with length
    jsr add_5_to_y                                                    ; 879d: 20 29 88     ).            ; Y = Y+5: advance to next address group
    dex                                                               ; 87a0: ca          .              ; Decrement address byte counter
    bne savsiz                                                        ; 87a1: d0 e4       ..             ; Loop for all 4 address bytes
    ldy #9                                                            ; 87a3: a0 09       ..             ; Copy load/exec addresses to FS command buffer
; &87a5 referenced 1 time by &87ab
.copy_save_params
    lda (fs_options),y                                                ; 87a5: b1 bb       ..             ; Read load/exec address byte from params
    sta fs_cmd_csd,y                                                  ; 87a7: 99 03 0f    ...            ; Copy to FS command buffer
    dey                                                               ; 87aa: 88          .              ; Next byte (descending)
    bne copy_save_params                                              ; 87ab: d0 f8       ..             ; Loop for bytes 9..1
    lda #&91                                                          ; 87ad: a9 91       ..             ; Port &91 for save command
    sta escapable                                                     ; 87af: 85 97       ..             ; Mark as escapable during save
    sta fs_cmd_urd                                                    ; 87b1: 8d 02 0f    ...            ; Overwrite URD field with port number
    sta fs_error_ptr                                                  ; 87b4: 85 b8       ..             ; Save port &91 for flow control ACK
    ldx #&0b                                                          ; 87b6: a2 0b       ..             ; Append filename at offset &0B in cmd buffer
    jsr copy_string_to_cmd                                            ; 87b8: 20 72 8d     r.            ; Append filename to cmd buffer at offset X
    ldy #1                                                            ; 87bb: a0 01       ..             ; Y=1: function code for save
    jsr prepare_cmd_clv                                               ; 87bd: 20 ab 83     ..            ; Build header and send FS save command
    lda fs_cmd_data                                                   ; 87c0: ad 05 0f    ...            ; Read FS reply command code for transfer type
    jsr transfer_file_blocks                                          ; 87c3: 20 41 88     A.            ; Send file data blocks to server
; &87c6 referenced 1 time by &8751
.save_csd_display
    lda fs_cmd_csd                                                    ; 87c6: ad 03 0f    ...            ; Save CSD from reply for catalogue display
    pha                                                               ; 87c9: 48          H              ; Save CSD byte from reply for display
    jsr send_fs_reply_cmd                                             ; 87ca: 20 e1 83     ..            ; Send final reply acknowledgement
    pla                                                               ; 87cd: 68          h              ; Restore CSD byte after reply command
    ldy fs_messages_flag                                              ; 87ce: ac 06 0e    ...            ; Check if file info messages enabled
    beq skip_catalogue_msg                                            ; 87d1: f0 32       .2             ; Messages off: skip catalogue display
    ldy #0                                                            ; 87d3: a0 00       ..             ; Y=0: start of filename in reply
    tax                                                               ; 87d5: aa          .              ; A = CSD; test for directory prefix
    beq print_filename_char                                           ; 87d6: f0 05       ..             ; CSD=0: no directory prefix
    jsr print_dir_from_offset                                         ; 87d8: 20 86 8d     ..            ; Print directory prefix from reply
    bmi print_addresses                                               ; 87db: 30 14       0.             ; Dir printed: skip to address display
; &87dd referenced 2 times by &87d6, &87e7
.print_filename_char
    lda (fs_crc_lo),y                                                 ; 87dd: b1 be       ..             ; Load filename character from reply
    cmp #&21 ; '!'                                                    ; 87df: c9 21       .!             ; Check for control character or space
    bcc pad_filename_space                                            ; 87e1: 90 06       ..             ; Below &21: pad with spaces to column 12
    jsr osasci                                                        ; 87e3: 20 e3 ff     ..            ; Write character
    iny                                                               ; 87e6: c8          .              ; Next character in filename
    bne print_filename_char                                           ; 87e7: d0 f4       ..             ; Loop for more filename characters
; &87e9 referenced 2 times by &87e1, &87ef
.pad_filename_space
    jsr print_space                                                   ; 87e9: 20 69 8d     i.            ; Print space to pad filename to 12 chars
    iny                                                               ; 87ec: c8          .              ; Advance column counter
    cpy #&0c                                                          ; 87ed: c0 0c       ..             ; Reached column 12?
    bcc pad_filename_space                                            ; 87ef: 90 f8       ..             ; No: keep padding with spaces
; &87f1 referenced 1 time by &87db
.print_addresses
    ldy #5                                                            ; 87f1: a0 05       ..             ; Y=5: load address offset in reply
    jsr print_hex_bytes                                               ; 87f3: 20 5e 8d     ^.            ; Print 4-byte load address in hex
    ldy #9                                                            ; 87f6: a0 09       ..             ; Y=9: exec address offset in reply
    jsr print_hex_bytes                                               ; 87f8: 20 5e 8d     ^.            ; Print 4-byte exec address in hex
    ldy #&0c                                                          ; 87fb: a0 0c       ..             ; Y=&0C: file length offset in reply
    ldx #3                                                            ; 87fd: a2 03       ..             ; X=3: print 3 bytes of length
    jsr num01                                                         ; 87ff: 20 60 8d     `.            ; Print file length in hex
.send_fs_reply
    jsr osnewl                                                        ; 8802: 20 e7 ff     ..            ; Send FS reply acknowledgement; Write newline (characters 10 and 13)
; &8805 referenced 1 time by &87d1
.skip_catalogue_msg
    stx fs_reply_cmd                                                  ; 8805: 8e 08 0f    ...            ; Store reply command for attr decode
    ldy #&0e                                                          ; 8808: a0 0e       ..             ; Y=&0E: access byte offset in param block
    lda fs_cmd_data                                                   ; 880a: ad 05 0f    ...            ; Load access byte from FS reply
    jsr decode_attribs_5bit                                           ; 880d: 20 c7 85     ..            ; Convert FS access to BBC attribute format
; &8810 referenced 1 time by &8818
.copy_attribs_reply
    sta (fs_options),y                                                ; 8810: 91 bb       ..             ; Store decoded access in param block
    iny                                                               ; 8812: c8          .              ; Next attribute byte
    lda fs_reply_data,y                                               ; 8813: b9 f7 0e    ...            ; Load remaining reply data for param block
    cpy #&12                                                          ; 8816: c0 12       ..             ; Copied all 4 bytes? (Y=&0E..&11)
    bne copy_attribs_reply                                            ; 8818: d0 f6       ..             ; Loop for 4 attribute bytes
    jmp restore_args_return                                           ; 881a: 4c a1 89    L..            ; Restore A/X/Y and return to caller

; ***************************************************************************************
; Copy load address from parameter block
; 
; Copies 4 bytes from (fs_options)+2..5 (the load address in the
; OSFILE parameter block) to &AE-&B3 (local workspace).
; 
; On Exit:
;     Y: 8 (final offset)
;     A: last byte copied
; ***************************************************************************************
; &881d referenced 2 times by &8720, &872b
.copy_load_addr_from_params
    ldy #5                                                            ; 881d: a0 05       ..             ; Start at offset 5 (top of 4-byte addr)
; &881f referenced 1 time by &8827
.lodrl1
    lda (fs_options),y                                                ; 881f: b1 bb       ..             ; Read from parameter block
    sta work_ae,y                                                     ; 8821: 99 ae 00    ...            ; Store to local workspace
    dey                                                               ; 8824: 88          .              ; Next byte (descending)
    cpy #2                                                            ; 8825: c0 02       ..             ; Copy offsets 5,4,3,2 (4 bytes)
    bcs lodrl1                                                        ; 8827: b0 f6       ..             ; Loop while Y >= 2
; &8829 referenced 1 time by &879d
.add_5_to_y
    iny                                                               ; 8829: c8          .              ; Y += 5
; &882a referenced 1 time by &8ac3
.add_4_to_y
    iny                                                               ; 882a: c8          .              ; Y += 4
    iny                                                               ; 882b: c8          .              ; (continued)
    iny                                                               ; 882c: c8          .              ; (continued)
    iny                                                               ; 882d: c8          .              ; (continued)
    rts                                                               ; 882e: 60          `              ; Return

; ***************************************************************************************
; Copy FS reply data to parameter block
; 
; Copies bytes from the FS command reply buffer (&0F02+) into the
; parameter block at (fs_options)+2..13. Used to fill in the OSFILE
; parameter block with information returned by the fileserver.
; 
; On Entry:
;     X: attribute byte (stored first at offset &0D)
; ***************************************************************************************
; &882f referenced 2 times by &8723, &8728
.copy_reply_to_params
    ldy #&0d                                                          ; 882f: a0 0d       ..             ; Start at offset &0D (top of range)
    txa                                                               ; 8831: 8a          .              ; First store uses X (attrib byte)
; &8832 referenced 1 time by &883a
.lodrl2
    sta (fs_options),y                                                ; 8832: 91 bb       ..             ; Write to parameter block
    lda fs_cmd_urd,y                                                  ; 8834: b9 02 0f    ...            ; Read next byte from reply buffer
    dey                                                               ; 8837: 88          .              ; Next byte (descending)
    cpy #2                                                            ; 8838: c0 02       ..             ; Copy offsets &0D down to 2
    bcs lodrl2                                                        ; 883a: b0 f6       ..             ; Loop until offset 2 reached
; &883c referenced 1 time by &878c
.sub_4_from_y
    dey                                                               ; 883c: 88          .              ; Y -= 4
; &883d referenced 2 times by &88d7, &8acb
.sub_3_from_y
    dey                                                               ; 883d: 88          .              ; Y -= 3
    dey                                                               ; 883e: 88          .              ; (continued)
    dey                                                               ; 883f: 88          .              ; (continued)
    rts                                                               ; 8840: 60          `              ; Return to caller

; ***************************************************************************************
; Multi-block file data transfer
; 
; Manages the transfer of file data in chunks between the local
; machine and the fileserver. Entry conditions: WORK (&B0-&B3) and
; WORK+4 (&B4-&B7) hold the low and high addresses of the data
; being sent/received. Sets up source (&C4-&C7) and destination
; (&C8-&CB) from the FS reply, sends &80-byte (128-byte) blocks
; with command &91, and continues until all data has been
; transferred. Handles address overflow and Tube co-processor
; transfers. For SAVE, WORK+8 holds the port on which to receive
; byte-level ACKs for each data block (flow control).
; ***************************************************************************************
; &8841 referenced 2 times by &87c3, &8ae1
.transfer_file_blocks
    pha                                                               ; 8841: 48          H              ; Save FS command byte on stack
    jsr compare_addresses                                             ; 8842: 20 ad 86     ..            ; Compare two 4-byte addresses
    beq restore_ay_return                                             ; 8845: f0 74       .t             ; Addresses equal: nothing to transfer
; &8847 referenced 1 time by &8899
.transfer_loop_top
    lda #0                                                            ; 8847: a9 00       ..             ; A=0: high bytes of block size
    pha                                                               ; 8849: 48          H              ; Push 4-byte block size: 0, 0, hi, lo
    pha                                                               ; 884a: 48          H              ; Push second zero byte
    tax                                                               ; 884b: aa          .              ; X=&00
    lda fs_data_count                                                 ; 884c: ad 07 0f    ...            ; Load block size high byte from &0F07
    pha                                                               ; 884f: 48          H              ; Push block size high
    lda fs_func_code                                                  ; 8850: ad 06 0f    ...            ; Load block size low byte from &0F06
    pha                                                               ; 8853: 48          H              ; Push block size low
    ldy #4                                                            ; 8854: a0 04       ..             ; Y=4: process 4 address bytes
    clc                                                               ; 8856: 18          .              ; CLC for ADC in loop
; &8857 referenced 1 time by &8864
.setup_block_addrs
    lda fs_load_addr,x                                                ; 8857: b5 b0       ..             ; Source = current position
    sta txcb_start,x                                                  ; 8859: 95 c4       ..             ; Store source address byte
    pla                                                               ; 885b: 68          h              ; Pop block size byte from stack
    adc fs_load_addr,x                                                ; 885c: 75 b0       u.             ; Dest = current pos + block size
    sta txcb_end,x                                                    ; 885e: 95 c8       ..             ; Store dest address byte
    sta fs_load_addr,x                                                ; 8860: 95 b0       ..             ; Advance current position
    inx                                                               ; 8862: e8          .              ; Next address byte
    dey                                                               ; 8863: 88          .              ; Decrement byte counter
    bne setup_block_addrs                                             ; 8864: d0 f1       ..             ; Loop for all 4 bytes
    sec                                                               ; 8866: 38          8              ; SEC for SBC in overshoot check
; &8867 referenced 1 time by &886f
.savchk
    lda fs_load_addr,y                                                ; 8867: b9 b0 00    ...            ; Check if new pos overshot end addr
    sbc fs_work_4,y                                                   ; 886a: f9 b4 00    ...            ; Subtract end address byte
    iny                                                               ; 886d: c8          .              ; Next byte
    dex                                                               ; 886e: ca          .              ; Decrement counter
    bne savchk                                                        ; 886f: d0 f6       ..             ; Loop for 4-byte comparison
    bcc send_block                                                    ; 8871: 90 09       ..             ; C=0: no overshoot, proceed
.clamp_dest_setup
    ldx #3                                                            ; 8873: a2 03       ..             ; Overshot: clamp dest to end address
; &8875 referenced 1 time by &887a
.clamp_dest_addr
    lda fs_work_4,x                                                   ; 8875: b5 b4       ..             ; Load end address byte
    sta txcb_end,x                                                    ; 8877: 95 c8       ..             ; Replace dest with end address
    dex                                                               ; 8879: ca          .              ; Next byte
    bpl clamp_dest_addr                                               ; 887a: 10 f9       ..             ; Loop for all 4 bytes
; &887c referenced 1 time by &8871
.send_block
    pla                                                               ; 887c: 68          h              ; Recover original FS command byte
    pha                                                               ; 887d: 48          H              ; Re-push for next iteration
    php                                                               ; 887e: 08          .              ; Save processor flags (C from cmp)
    sta txcb_port                                                     ; 887f: 85 c1       ..             ; Store command byte in TXCB
    lda #&80                                                          ; 8881: a9 80       ..             ; 128-byte block size for data transfer
    sta txcb_ctrl                                                     ; 8883: 85 c0       ..             ; Store size in TXCB control byte
    jsr setup_tx_ptr_c0                                               ; 8885: 20 e5 85     ..            ; Point TX ptr to &00C0; transmit
    lda fs_error_ptr                                                  ; 8888: a5 b8       ..             ; ACK port for flow control
    jsr init_tx_ctrl_port                                             ; 888a: 20 77 83     w.            ; Set reply port for ACK receive
    plp                                                               ; 888d: 28          (              ; Restore flags (C=overshoot status)
    bcs restore_ay_return                                             ; 888e: b0 2b       .+             ; C=1: all data sent (overshot), done
    lda #&91                                                          ; 8890: a9 91       ..             ; Command &91 = data block transfer
    sta txcb_port                                                     ; 8892: 85 c1       ..             ; Store command &91 in TXCB
    inc txcb_start                                                    ; 8894: e6 c4       ..             ; Skip command code byte in TX buffer
    jsr waitfs                                                        ; 8896: 20 1e 85     ..            ; Transmit block and wait (BRIANX)
    bne transfer_loop_top                                             ; 8899: d0 ac       ..             ; More blocks? Loop back
; ***************************************************************************************
; FSCV 1: EOF handler
; 
; Checks whether a file handle has reached end-of-file. Converts
; the handle via handle_to_mask_clc, tests the result against the
; EOF hint byte (&0E07). If the hint bit is clear, returns X=0
; immediately (definitely not at EOF — no network call needed).
; If the hint bit is set, sends FS command &11 (FCEOF) to query
; the fileserver for definitive EOF status. Returns X=&FF if at
; EOF, X=&00 if not. This two-level check avoids an expensive
; network round-trip when the file is known to not be at EOF.
; 
; On Entry:
;     X: file handle to check
; 
; On Exit:
;     X: &FF if at EOF, &00 if not
; ***************************************************************************************
.fscv_1_eof
    pha                                                               ; 889b: 48          H              ; Save A (function code)
    txa                                                               ; 889c: 8a          .              ; X = file handle to check
    jsr handle_to_mask_a                                              ; 889d: 20 88 86     ..            ; Convert handle to bitmask in A
    tya                                                               ; 88a0: 98          .              ; Y = handle bitmask from conversion
    and fs_eof_flags                                                  ; 88a1: 2d 07 0e    -..            ; Local hint: is EOF possible for this handle?
    tax                                                               ; 88a4: aa          .              ; X = result of AND (0 = not at EOF)
    beq restore_ay_return                                             ; 88a5: f0 14       ..             ; Hint clear: definitely not at EOF
    pha                                                               ; 88a7: 48          H              ; Save bitmask for clear_fs_flag
    sty fs_cmd_data                                                   ; 88a8: 8c 05 0f    ...            ; Handle byte in FS command buffer
    ldy #&11                                                          ; 88ab: a0 11       ..             ; Y=&11: FS function code FCEOF; Y=function code for HDRFN
    ldx #1                                                            ; 88ad: a2 01       ..             ; X=preserved through header build
    jsr prepare_fs_cmd                                                ; 88af: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    pla                                                               ; 88b2: 68          h              ; Restore bitmask
    ldx fs_cmd_data                                                   ; 88b3: ae 05 0f    ...            ; FS reply: non-zero = at EOF
    bne restore_ay_return                                             ; 88b6: d0 03       ..             ; At EOF: skip flag clear
    jsr clear_fs_flag                                                 ; 88b8: 20 c3 86     ..            ; Not at EOF: clear the hint bit
; &88bb referenced 4 times by &8845, &888e, &88a5, &88b6
.restore_ay_return
    pla                                                               ; 88bb: 68          h              ; Restore A
    ldy fs_block_offset                                               ; 88bc: a4 bc       ..             ; Restore Y
    rts                                                               ; 88be: 60          `              ; Return; X=0 (not EOF) or X=&FF (EOF)

; ***************************************************************************************
; FILEV attribute dispatch (A=1-6)
; 
; Dispatches OSFILE operations by function code:
;   A=1: write catalogue info (load/exec/length/attrs) — FS &14
;   A=2: write load address only
;   A=3: write exec address only
;   A=4: write file attributes
;   A=5: read catalogue info, returns type in A — FS &12
;   A=6: delete named object — FS &14 (FCDEL)
;   A>=7: falls through to restore_args_return (no-op)
; Each handler builds the appropriate FS command, sends it to
; the fileserver, and copies the reply into the parameter block.
; The control block layout uses dual-purpose fields: the 'data
; start' field doubles as 'length' and 'data end' doubles as
; 'protection' depending on whether reading or writing attrs.
; 
; On Entry:
;     A: function code (1-6)
; 
; On Exit:
;     A: object type (A=5 read info) or restored
; ***************************************************************************************
; &88bf referenced 1 time by &8780
.filev_attrib_dispatch
    sta fs_cmd_data                                                   ; 88bf: 8d 05 0f    ...            ; Store function code in FS cmd buffer
    cmp #6                                                            ; 88c2: c9 06       ..             ; A=6? (delete)
    beq cha6                                                          ; 88c4: f0 3f       .?             ; Yes: jump to delete handler
    bcs check_attrib_result                                           ; 88c6: b0 48       .H             ; A>=7: unsupported, fall through to return
    cmp #5                                                            ; 88c8: c9 05       ..             ; A=5? (read catalogue info)
    beq cha5                                                          ; 88ca: f0 52       .R             ; Yes: jump to read info handler
    cmp #4                                                            ; 88cc: c9 04       ..             ; A=4? (write attributes only)
    beq cha4                                                          ; 88ce: f0 44       .D             ; Yes: jump to write attrs handler
    cmp #1                                                            ; 88d0: c9 01       ..             ; A=1? (write all catalogue info)
    beq get_file_protection                                           ; 88d2: f0 15       ..             ; Yes: jump to write-all handler
    asl a                                                             ; 88d4: 0a          .              ; A=2 or 3: convert to param block offset
    asl a                                                             ; 88d5: 0a          .              ; A*4: 2->8, 3->12
    tay                                                               ; 88d6: a8          .              ; Y = A*4
    jsr sub_3_from_y                                                  ; 88d7: 20 3d 88     =.            ; Y = A*4 - 3 (load addr offset for A=2)
    ldx #3                                                            ; 88da: a2 03       ..             ; X=3: copy 4 bytes
; &88dc referenced 1 time by &88e3
.chalp1
    lda (fs_options),y                                                ; 88dc: b1 bb       ..             ; Load address byte from param block
    sta fs_func_code,x                                                ; 88de: 9d 06 0f    ...            ; Store to FS cmd data area
    dey                                                               ; 88e1: 88          .              ; Next source byte (descending)
    dex                                                               ; 88e2: ca          .              ; Next dest byte
    bpl chalp1                                                        ; 88e3: 10 f7       ..             ; Loop for 4 bytes
    ldx #5                                                            ; 88e5: a2 05       ..             ; X=5: data extent for filename copy
    bne copy_filename_to_cmd                                          ; 88e7: d0 15       ..             ; ALWAYS branch

; &88e9 referenced 1 time by &88d2
.get_file_protection
    jsr decode_attribs_6bit                                           ; 88e9: 20 bd 85     ..            ; A=1: encode protection from param block
    sta fs_file_attrs                                                 ; 88ec: 8d 0e 0f    ...            ; Store encoded attrs at &0F0E
    ldy #9                                                            ; 88ef: a0 09       ..             ; Y=9: source offset in param block
    ldx #8                                                            ; 88f1: a2 08       ..             ; X=8: dest offset in cmd buffer
; &88f3 referenced 1 time by &88fa
.chalp2
    lda (fs_options),y                                                ; 88f3: b1 bb       ..             ; Load byte from param block
    sta fs_cmd_data,x                                                 ; 88f5: 9d 05 0f    ...            ; Store to FS cmd buffer
    dey                                                               ; 88f8: 88          .              ; Next source byte (descending)
    dex                                                               ; 88f9: ca          .              ; Next dest byte
    bne chalp2                                                        ; 88fa: d0 f7       ..             ; Loop until X=0 (8 bytes copied)
    ldx #&0a                                                          ; 88fc: a2 0a       ..             ; X=&0A: data extent past attrs+addrs
; &88fe referenced 2 times by &88e7, &891c
.copy_filename_to_cmd
    jsr copy_string_to_cmd                                            ; 88fe: 20 72 8d     r.            ; Append filename to cmd buffer
    ldy #&13                                                          ; 8901: a0 13       ..             ; Y=&13: fn code for FCSAVE (write attrs)
    bne send_fs_cmd_v1                                                ; 8903: d0 05       ..             ; ALWAYS branch to send command; ALWAYS branch

; &8905 referenced 1 time by &88c4
.cha6
    jsr infol2                                                        ; 8905: 20 70 8d     p.            ; A=6: copy filename (delete)
    ldy #&14                                                          ; 8908: a0 14       ..             ; Y=&14: fn code for FCDEL (delete)
; &890a referenced 1 time by &8903
.send_fs_cmd_v1
    bit tx_ctrl_upper                                                 ; 890a: 2c a1 83    ,..            ; Set V=1 (BIT trick: &B3 has bit 6 set)
    jsr init_tx_ctrl_data                                             ; 890d: 20 b6 83     ..            ; Send via prepare_fs_cmd_v (V=1 path)
; &8910 referenced 1 time by &88c6
.check_attrib_result
    bcs attrib_error_exit                                             ; 8910: b0 42       .B             ; C=1: &D6 not-found, skip to return
    bcc argsv_check_return                                            ; 8912: 90 71       .q             ; C=0: success, copy reply to param block; ALWAYS branch

; &8914 referenced 1 time by &88ce
.cha4
    jsr decode_attribs_6bit                                           ; 8914: 20 bd 85     ..            ; A=4: encode attrs from param block
    sta fs_func_code                                                  ; 8917: 8d 06 0f    ...            ; Store encoded attrs at &0F06
    ldx #2                                                            ; 891a: a2 02       ..             ; X=2: data extent (1 attr byte + fn)
    bne copy_filename_to_cmd                                          ; 891c: d0 e0       ..             ; ALWAYS branch to append filename; ALWAYS branch

; &891e referenced 1 time by &88ca
.cha5
    ldx #1                                                            ; 891e: a2 01       ..             ; X=1: filename only, no data extent
    jsr copy_string_to_cmd                                            ; 8920: 20 72 8d     r.            ; Copy filename to cmd buffer
    ldy #&12                                                          ; 8923: a0 12       ..             ; Y=&12: fn code for FCEXAM (read info); Y=function code for HDRFN
    jsr prepare_fs_cmd                                                ; 8925: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    lda fs_obj_type                                                   ; 8928: ad 11 0f    ...            ; Save object type from FS reply
    stx fs_obj_type                                                   ; 892b: 8e 11 0f    ...            ; Clear reply byte (X=0 on success); X=0 on success, &D6 on not-found
    stx fs_len_clear                                                  ; 892e: 8e 14 0f    ...            ; Clear length high byte in reply
    jsr decode_attribs_5bit                                           ; 8931: 20 c7 85     ..            ; Decode 5-bit access byte from FS reply
    ldy #&0e                                                          ; 8934: a0 0e       ..             ; Y=&0E: attrs offset in param block
    sta (fs_options),y                                                ; 8936: 91 bb       ..             ; Store decoded attrs at param block +&0E
    dey                                                               ; 8938: 88          .              ; Y=&0D: start copy below attrs; Y=&0d
    ldx #&0c                                                          ; 8939: a2 0c       ..             ; X=&0C: copy from reply offset &0C down
; &893b referenced 1 time by &8942
.copy_fs_reply_to_cb
    lda fs_cmd_data,x                                                 ; 893b: bd 05 0f    ...            ; Load reply byte (load/exec/length)
    sta (fs_options),y                                                ; 893e: 91 bb       ..             ; Store to param block
    dey                                                               ; 8940: 88          .              ; Next dest byte (descending)
    dex                                                               ; 8941: ca          .              ; Next source byte
    bne copy_fs_reply_to_cb                                           ; 8942: d0 f7       ..             ; Loop until X=0 (12 bytes copied)
    inx                                                               ; 8944: e8          .              ; X=0 -> X=2 for length high copy
    inx                                                               ; 8945: e8          .              ; INX again: X=2
    ldy #&11                                                          ; 8946: a0 11       ..             ; Y=&11: length high dest in param block
; &8948 referenced 1 time by &894f
.cha5lp
    lda fs_access_level,x                                             ; 8948: bd 12 0f    ...            ; Load length high byte from reply
    sta (fs_options),y                                                ; 894b: 91 bb       ..             ; Store to param block
    dey                                                               ; 894d: 88          .              ; Next dest byte (descending)
    dex                                                               ; 894e: ca          .              ; Next source byte
    bpl cha5lp                                                        ; 894f: 10 f7       ..             ; Loop for 3 length-high bytes
    lda fs_cmd_data                                                   ; 8951: ad 05 0f    ...            ; Return object type in A
; &8954 referenced 1 time by &8910
.attrib_error_exit
    bpl restore_xy_return                                             ; 8954: 10 4d       .M             ; A>=0: branch to restore_args_return
; ***************************************************************************************
; ARGSV handler (OSARGS entry point)
; 
;   A=0, Y=0: return filing system number (5 = network FS)
;   A=0, Y>0: read file pointer via FS command &0C (FCRDSE)
;   A=1, Y>0: write file pointer via FS command &0D (FCWRSE)
;   A=2, Y=0: return &01 (command-line tail supported)
;   A>=3 (ensure): silently returns -- NFS has no local write buffer
;      to flush, since all data is sent to the fileserver immediately
; The handle in Y is converted via handle_to_mask_clc. For writes
; (A=1), the carry flag from the mask conversion is used to branch
; to save_args_handle, which records the handle for later use.
; 
; On Entry:
;     A: function code (0=query, 1=write ptr, >=3=ensure)
;     Y: file handle (0=FS-level query, >0=per-file)
; 
; On Exit:
;     A: filing system number if A=0/Y=0 query, else restored
;     X: restored
;     Y: restored
; ***************************************************************************************
.argsv_handler
    jsr save_fscv_args                                                ; 8956: 20 3b 86     ;.            ; Save A/X/Y registers for later restore
    cmp #3                                                            ; 8959: c9 03       ..             ; Function >= 3?
    bcs restore_args_return                                           ; 895b: b0 44       .D             ; A>=3 (ensure/flush): no-op for NFS
    cpy #0                                                            ; 895d: c0 00       ..             ; Test file handle
    beq argsv_fs_query                                                ; 895f: f0 47       .G             ; Y=0: FS-level query, not per-file
    jsr handle_to_mask_clc                                            ; 8961: 20 89 86     ..            ; Convert handle to bitmask
    sty fs_cmd_data                                                   ; 8964: 8c 05 0f    ...            ; Store bitmask as first cmd data byte
    lsr a                                                             ; 8967: 4a          J              ; LSR splits A: C=1 means write (A=1)
    sta fs_func_code                                                  ; 8968: 8d 06 0f    ...            ; Store function code to cmd data byte 2
    bcs save_args_handle                                              ; 896b: b0 1a       ..             ; C=1: write path, copy ptr from caller
    ldy #&0c                                                          ; 896d: a0 0c       ..             ; Y=&0C: FCRDSE (read sequential pointer); Y=function code for HDRFN
    ldx #2                                                            ; 896f: a2 02       ..             ; X=2: 3 data bytes in command; X=preserved through header build
    jsr prepare_fs_cmd                                                ; 8971: 20 b5 83     ..            ; Build and send FS command; Prepare FS command buffer (12 references)
    sta fs_last_byte_flag                                             ; 8974: 85 bd       ..             ; Clear last-byte flag on success; A=0 on success (from build_send_fs_cmd)
    ldx fs_options                                                    ; 8976: a6 bb       ..             ; X = saved control block ptr low
    ldy #2                                                            ; 8978: a0 02       ..             ; Y=2: copy 3 bytes of file pointer
    sta zp_work_3,x                                                   ; 897a: 95 03       ..             ; Zero high byte of 3-byte pointer
; &897c referenced 1 time by &8983
.copy_fileptr_reply
    lda fs_cmd_data,y                                                 ; 897c: b9 05 0f    ...            ; Read reply byte from FS cmd data
    sta zp_work_2,x                                                   ; 897f: 95 02       ..             ; Store to caller's control block
    dex                                                               ; 8981: ca          .              ; Next byte (descending)
    dey                                                               ; 8982: 88          .              ; Next source byte
    bpl copy_fileptr_reply                                            ; 8983: 10 f7       ..             ; Loop for all 3 bytes
; &8985 referenced 1 time by &8912
.argsv_check_return
    bcc restore_args_return                                           ; 8985: 90 1a       ..             ; C=0 (read): return to caller
; &8987 referenced 1 time by &896b
.save_args_handle
    tya                                                               ; 8987: 98          .              ; Save bitmask for set_fs_flag later
    pha                                                               ; 8988: 48          H              ; Push bitmask
    ldy #3                                                            ; 8989: a0 03       ..             ; Y=3: copy 4 bytes of file pointer
; &898b referenced 1 time by &8992
.copy_fileptr_to_cmd
    lda zp_work_3,x                                                   ; 898b: b5 03       ..             ; Read caller's pointer byte
    sta fs_data_count,y                                               ; 898d: 99 07 0f    ...            ; Store to FS command data area
    dex                                                               ; 8990: ca          .              ; Next source byte
    dey                                                               ; 8991: 88          .              ; Next destination byte
    bpl copy_fileptr_to_cmd                                           ; 8992: 10 f7       ..             ; Loop for all 4 bytes
    ldy #&0d                                                          ; 8994: a0 0d       ..             ; Y=&0D: FCWRSE (write sequential pointer); Y=function code for HDRFN
    ldx #5                                                            ; 8996: a2 05       ..             ; X=5: 6 data bytes in command; X=preserved through header build
    jsr prepare_fs_cmd                                                ; 8998: 20 b5 83     ..            ; Build and send FS command; Prepare FS command buffer (12 references)
    stx fs_last_byte_flag                                             ; 899b: 86 bd       ..             ; Save not-found status from X; X=0 on success, &D6 on not-found
    pla                                                               ; 899d: 68          h              ; Recover bitmask for EOF hint update
    jsr set_fs_flag                                                   ; 899e: 20 be 86     ..            ; Set EOF hint bit for this handle
; ***************************************************************************************
; Restore arguments and return
; 
; Common exit point for FS vector handlers. Reloads A from
; fs_last_byte_flag (&BD), X from fs_options (&BB), and Y from
; fs_block_offset (&BC) — the values saved at entry by
; save_fscv_args — and returns to the caller.
; 
; On Exit:
;     A: restored from fs_last_byte_flag (&BD)
;     X: restored from fs_options (&BB)
;     Y: restored from fs_block_offset (&BC)
; ***************************************************************************************
; &89a1 referenced 7 times by &8708, &881a, &895b, &8985, &8a18, &8a6b, &8e38
.restore_args_return
    lda fs_last_byte_flag                                             ; 89a1: a5 bd       ..             ; A = saved function code / command
; &89a3 referenced 5 times by &8954, &89b4, &89c4, &89ef, &89fc
.restore_xy_return
    ldx fs_options                                                    ; 89a3: a6 bb       ..             ; X = saved control block ptr low
    ldy fs_block_offset                                               ; 89a5: a4 bc       ..             ; Y = saved control block ptr high
    rts                                                               ; 89a7: 60          `              ; Return to MOS with registers restored

; &89a8 referenced 1 time by &895f
.argsv_fs_query
    cmp #2                                                            ; 89a8: c9 02       ..             ; Y=0: FS-level queries (no file handle)
    beq halve_args_a                                                  ; 89aa: f0 07       ..             ; A=2: FS-level ensure (write extent)
    bcs return_a_zero                                                 ; 89ac: b0 14       ..             ; A>=3: FS command (ARGSV write)
    tay                                                               ; 89ae: a8          .              ; Y = A = byte count for copy loop
    bne osarg1                                                        ; 89af: d0 05       ..             ; A!=0: copy command context block
    lda #&0a                                                          ; 89b1: a9 0a       ..             ; FS number 5 (loaded as &0A, LSR'd)
; &89b3 referenced 1 time by &89aa
.halve_args_a
    lsr a                                                             ; 89b3: 4a          J              ; Shared: halve A (A=0 or A=2 paths)
    bne restore_xy_return                                             ; 89b4: d0 ed       ..             ; Return with A = FS number or 1
; &89b6 referenced 2 times by &89af, &89bc
.osarg1
    lda fs_cmd_context,y                                              ; 89b6: b9 0a 0e    ...            ; Copy command context to caller's block
    sta (fs_options),y                                                ; 89b9: 91 bb       ..             ; Store to caller's parameter block
    dey                                                               ; 89bb: 88          .              ; Next byte (descending)
    bpl osarg1                                                        ; 89bc: 10 f8       ..             ; Loop until all bytes copied
    sty zp_work_2,x                                                   ; 89be: 94 02       ..             ; Y=&FF after loop; fill high bytes
    sty zp_work_3,x                                                   ; 89c0: 94 03       ..             ; Set 32-bit result bytes 2-3 to &FF
; ***************************************************************************************
; Return with A=0 via register restore
; 
; Loads A=0 and branches (always taken) to the common register
; restore exit at restore_args_return. Used as a shared exit
; point by ARGSV, FINDV, and GBPBV when an operation is
; unsupported or should return zero.
; 
; On Exit:
;     A: 0
;     X: restored from fs_options (&BB)
;     Y: restored from fs_block_offset (&BC)
; ***************************************************************************************
; &89c2 referenced 4 times by &89ac, &89d2, &8b07, &8ba9
.return_a_zero
    lda #0                                                            ; 89c2: a9 00       ..             ; A=operation (0=close, &40=read, &80=write, &C0=R/W)
    bpl restore_xy_return                                             ; 89c4: 10 dd       ..             ; ALWAYS branch

; ***************************************************************************************
; FINDV handler (OSFIND entry point)
; 
;   A=0: close file -- delegates to close_handle (&89FE)
;   A>0: open file -- modes &40=read, &80=write/update, &C0=read/write
; For open: the mode byte is converted to the fileserver's two-flag
; format by flipping bit 7 (EOR #&80) and shifting. This produces
; Flag 1 (read/write direction) and Flag 2 (create/existing),
; matching the fileserver protocol. After a successful open, the
; new handle's bit is OR'd into the EOF hint byte (marks it as
; "might be at EOF, query the server"), and into the sequence
; number tracking byte for the byte-stream protocol.
; 
; On Entry:
;     A: operation (0=close, &40=read, &80=write, &C0=R/W)
;     X: filename pointer low (open)
;     Y: file handle (close) or filename pointer high (open)
; 
; On Exit:
;     A: handle on open, 0 on close-all, restored on close-one
;     X: restored
;     Y: restored
; ***************************************************************************************
.findv_handler
    jsr save_fscv_args_with_ptrs                                      ; 89c6: 20 37 86     7.            ; Save A/X/Y and set up pointers
    sec                                                               ; 89c9: 38          8              ; SEC distinguishes open (A>0) from close
    jsr handle_to_mask                                                ; 89ca: 20 8a 86     ..            ; Convert file handle to bitmask (Y2FS)
    tax                                                               ; 89cd: aa          .              ; A=preserved
    beq close_handle                                                  ; 89ce: f0 2e       ..             ; A=0: close file(s)
    and #&3f ; '?'                                                    ; 89d0: 29 3f       )?             ; Valid open modes: &40, &80, &C0 only
    bne return_a_zero                                                 ; 89d2: d0 ee       ..             ; Invalid mode bits: return
    txa                                                               ; 89d4: 8a          .              ; A = original mode byte
    eor #&80                                                          ; 89d5: 49 80       I.             ; Convert MOS mode to FS protocol flags
    asl a                                                             ; 89d7: 0a          .              ; ASL: shift mode bits left
    sta fs_cmd_data                                                   ; 89d8: 8d 05 0f    ...            ; Flag 1: read/write direction
    rol a                                                             ; 89db: 2a          *              ; ROL: Flag 2 into bit 0
    sta fs_func_code                                                  ; 89dc: 8d 06 0f    ...            ; Flag 2: create vs existing file
    jsr parse_filename_gs                                             ; 89df: 20 d6 86     ..            ; Parse filename from command line
    ldx #2                                                            ; 89e2: a2 02       ..             ; X=2: copy after 2-byte flags
    jsr copy_string_to_cmd                                            ; 89e4: 20 72 8d     r.            ; Copy filename to FS command buffer
    ldy #6                                                            ; 89e7: a0 06       ..             ; Y=6: FS function code FCOPEN
    bit tx_ctrl_upper                                                 ; 89e9: 2c a1 83    ,..            ; Set V flag from l83b3 bit 6
    jsr init_tx_ctrl_data                                             ; 89ec: 20 b6 83     ..            ; Build and send FS open command
    bcs restore_xy_return                                             ; 89ef: b0 b2       ..             ; Error: restore and return
    lda fs_cmd_data                                                   ; 89f1: ad 05 0f    ...            ; Load reply handle from FS
    tax                                                               ; 89f4: aa          .              ; X = new file handle
    jsr set_fs_flag                                                   ; 89f5: 20 be 86     ..            ; Set EOF hint + sequence bits
; OR handle bit into fs_sequence_nos
; (&0E08). Without this, a newly opened file could
; inherit a stale sequence number from a previous
; file using the same handle, causing byte-stream
; protocol errors.
    txa                                                               ; 89f8: 8a          .              ; A=handle bitmask for new file; A=single-bit bitmask
    jsr mask_to_handle                                                ; 89f9: 20 a5 86     ..            ; Convert bitmask to handle number (FS2A)
    bne restore_xy_return                                             ; 89fc: d0 a5       ..             ; ALWAYS branch to restore and return
; ***************************************************************************************
; Close file handle(s) (CLOSE)
; 
;   Y=0: close all files — first calls OSBYTE &77 (close SPOOL and
;        EXEC files) to coordinate with the MOS before sending the
;        close-all command to the fileserver. This ensures locally-
;        managed file handles are released before the server-side
;        handles are invalidated, preventing the MOS from writing to
;        a closed spool file.
;   Y>0: close single handle — sends FS close command and clears
;        the handle's bit in both the EOF hint byte and the sequence
;        number tracking byte.
; 
; On Entry:
;     Y: file handle (0=close all, >0=close single)
; ***************************************************************************************
; &89fe referenced 1 time by &89ce
.close_handle
    tya                                                               ; 89fe: 98          .              ; A = handle (Y preserved in A); Y=preserved
    bne close_single_handle                                           ; 89ff: d0 07       ..             ; Y>0: close single file
    lda #osbyte_close_spool_exec                                      ; 8a01: a9 77       .w             ; Close SPOOL/EXEC before FS close-all
    jsr osbyte                                                        ; 8a03: 20 f4 ff     ..            ; Close any *SPOOL and *EXEC files
    ldy #0                                                            ; 8a06: a0 00       ..             ; Y=0: close all handles on server
; &8a08 referenced 1 time by &89ff
.close_single_handle
    sty fs_cmd_data                                                   ; 8a08: 8c 05 0f    ...            ; Handle byte in FS command buffer
    ldx #1                                                            ; 8a0b: a2 01       ..             ; X=preserved through header build
    ldy #7                                                            ; 8a0d: a0 07       ..             ; Y=function code for HDRFN
    jsr prepare_fs_cmd                                                ; 8a0f: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    lda fs_cmd_data                                                   ; 8a12: ad 05 0f    ...            ; Reply handle for flag update
    jsr set_fs_flag                                                   ; 8a15: 20 be 86     ..            ; Update EOF/sequence tracking bits
; &8a18 referenced 1 time by &8a3e
.close_opt_return
    bcc restore_args_return                                           ; 8a18: 90 87       ..             ; C=0: restore A/X/Y and return
.fscv_0_opt_entry
    beq set_messages_flag                                             ; 8a1a: f0 0b       ..             ; Entry from fscv_0_opt (close-all path)
; ***************************************************************************************
; FSCV 0: *OPT handler (OPTION)
; 
; Handles *OPT X,Y to set filing system options:
;   *OPT 1,Y (Y=0/1): set local user option in &0E06 (OPT)
;   *OPT 4,Y (Y=0-3): set boot option via FS command &16 (FCOPT)
; Other combinations generate error &CB (OPTER: "bad option").
; 
; On Entry:
;     X: option number (1 or 4)
;     Y: option value
; ***************************************************************************************
.fscv_0_opt
    cpx #4                                                            ; 8a1c: e0 04       ..             ; Is it *OPT 4,Y?
    bne check_opt1                                                    ; 8a1e: d0 04       ..             ; No: check for *OPT 1
    cpy #4                                                            ; 8a20: c0 04       ..             ; Y must be 0-3 for boot option
    bcc optl1                                                         ; 8a22: 90 0d       ..             ; Y < 4: valid boot option
; &8a24 referenced 1 time by &8a1e
.check_opt1
    dex                                                               ; 8a24: ca          .              ; Not *OPT 4: check for *OPT 1
    bne opter1                                                        ; 8a25: d0 05       ..             ; Not *OPT 1 either: bad option
; &8a27 referenced 1 time by &8a1a
.set_messages_flag
    sty fs_messages_flag                                              ; 8a27: 8c 06 0e    ...            ; Set local messages flag (*OPT 1,Y)
    bcc opt_return                                                    ; 8a2a: 90 12       ..             ; Return via restore_args_return
; &8a2c referenced 1 time by &8a25
.opter1
    lda #7                                                            ; 8a2c: a9 07       ..             ; Error index 7 (Bad option)
    jmp nlisne                                                        ; 8a2e: 4c 00 85    L..            ; Generate BRK error

; &8a31 referenced 1 time by &8a22
.optl1
    sty fs_cmd_data                                                   ; 8a31: 8c 05 0f    ...            ; Boot option value in FS command
    ldy #&16                                                          ; 8a34: a0 16       ..             ; Y=&16: FS function code FCOPT; Y=function code for HDRFN
    jsr prepare_fs_cmd                                                ; 8a36: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    ldy fs_block_offset                                               ; 8a39: a4 bc       ..             ; Restore Y from saved value
    sty fs_boot_option                                                ; 8a3b: 8c 05 0e    ...            ; Cache boot option locally
; &8a3e referenced 1 time by &8a2a
.opt_return
    bcc close_opt_return                                              ; 8a3e: 90 d8       ..             ; Return via restore_args_return
; &8a40 referenced 1 time by &8afb
.adjust_addrs_9
    ldy #9                                                            ; 8a40: a0 09       ..             ; Y=9: adjust 9 address bytes
    jsr adjust_addrs_clc                                              ; 8a42: 20 47 8a     G.            ; Adjust with carry clear
; &8a45 referenced 1 time by &8bf0
.adjust_addrs_1
    ldy #1                                                            ; 8a45: a0 01       ..             ; Y=1: adjust 1 address byte
; &8a47 referenced 1 time by &8a42
.adjust_addrs_clc
    clc                                                               ; 8a47: 18          .              ; C=0 for address adjustment
; ***************************************************************************************
; Bidirectional 4-byte address adjustment
; 
; Adjusts a 4-byte value in the parameter block at (fs_options)+Y:
;   If fs_load_addr_2 (&B2) is positive: adds fs_lib_handle+X values
;   If fs_load_addr_2 (&B2) is negative: subtracts fs_lib_handle+X
; Starting offset X=&FC means it reads from &0E06-&0E09 area.
; Used to convert between absolute and relative file positions.
; 
; On Entry:
;     Y: starting offset into (fs_options) parameter block
; 
; On Exit:
;     A: corrupted (last adjusted byte)
;     X: 0
;     Y: entry Y + 4
; ***************************************************************************************
; &8a48 referenced 2 times by &8b01, &8bfc
.adjust_addrs
    ldx #&fc                                                          ; 8a48: a2 fc       ..             ; X=&FC: index into &0E06 area (wraps to 0)
; &8a4a referenced 1 time by &8a5d
.adjust_addr_byte
    lda (fs_options),y                                                ; 8a4a: b1 bb       ..             ; Load byte from param block
    bit fs_load_addr_2                                                ; 8a4c: 24 b2       $.             ; Test sign of adjustment direction
    bmi subtract_adjust                                               ; 8a4e: 30 06       0.             ; Negative: subtract instead
    adc fs_cmd_context,x                                              ; 8a50: 7d 0a 0e    }..            ; Add adjustment value
    jmp gbpbx                                                         ; 8a53: 4c 59 8a    LY.            ; Skip to store result

; &8a56 referenced 1 time by &8a4e
.subtract_adjust
    sbc fs_cmd_context,x                                              ; 8a56: fd 0a 0e    ...            ; Subtract adjustment value
; &8a59 referenced 1 time by &8a53
.gbpbx
    sta (fs_options),y                                                ; 8a59: 91 bb       ..             ; Store adjusted byte back
    iny                                                               ; 8a5b: c8          .              ; Next param block byte
    inx                                                               ; 8a5c: e8          .              ; Next adjustment byte (X wraps &FC->&00)
    bne adjust_addr_byte                                              ; 8a5d: d0 eb       ..             ; Loop 4 times (X=&FC,&FD,&FE,&FF,done)
    rts                                                               ; 8a5f: 60          `              ; Return (unsupported function)

; ***************************************************************************************
; GBPBV handler (OSGBPB entry point)
; 
;   A=1-4: file read/write operations (handle-based)
;   A=5-8: info queries (disc title, current dir, lib, filenames)
; Calls 1-4 are standard file data transfers via the fileserver.
; Calls 5-8 were a late addition to the MOS spec and are the only
; NFS operations requiring Tube data transfer -- described in the
; original source as "untidy but useful in theory." The data format
; uses length-prefixed strings (<name length><object name>) rather
; than the CR-terminated strings used elsewhere in the FS.
; 
; On Entry:
;     A: call number (1-8)
;     X: parameter block address low byte
;     Y: parameter block address high byte
; 
; On Exit:
;     A: 0 after FS operation, else restored
;     X: restored
;     Y: restored
; ***************************************************************************************
.gbpbv_handler
    jsr save_fscv_args                                                ; 8a60: 20 3b 86     ;.            ; Save A/X/Y to FS workspace
    tax                                                               ; 8a63: aa          .              ; X = call number for range check
    beq gbpb_invalid_exit                                             ; 8a64: f0 05       ..             ; A=0: invalid, restore and return
    dex                                                               ; 8a66: ca          .              ; Convert to 0-based (A=0..7)
    cpx #8                                                            ; 8a67: e0 08       ..             ; Range check: must be 0-7
    bcc gbpbx1                                                        ; 8a69: 90 03       ..             ; In range: continue to handler
; &8a6b referenced 1 time by &8a64
.gbpb_invalid_exit
    jmp restore_args_return                                           ; 8a6b: 4c a1 89    L..            ; Out of range: restore args and return

; &8a6e referenced 1 time by &8a69
.gbpbx1
    txa                                                               ; 8a6e: 8a          .              ; Recover 0-based function code
    ldy #0                                                            ; 8a6f: a0 00       ..             ; Y=0: param block byte 0 (file handle)
    pha                                                               ; 8a71: 48          H              ; Save function code on stack
    cmp #4                                                            ; 8a72: c9 04       ..             ; A>=4: info queries, dispatch separately
    bcc gbpbe1                                                        ; 8a74: 90 03       ..             ; A<4: file read/write operations
    jmp osgbpb_info                                                   ; 8a76: 4c 1f 8b    L..            ; Dispatch to OSGBPB 5-8 info handler

; &8a79 referenced 1 time by &8a74
.gbpbe1
    lda (fs_options),y                                                ; 8a79: b1 bb       ..             ; Get file handle from param block byte 0
    jsr handle_to_mask_a                                              ; 8a7b: 20 88 86     ..            ; Convert handle to bitmask for EOF flags
    sty fs_cmd_data                                                   ; 8a7e: 8c 05 0f    ...            ; Store handle in FS command data
    ldy #&0b                                                          ; 8a81: a0 0b       ..             ; Y=&0B: start at param block byte 11
    ldx #6                                                            ; 8a83: a2 06       ..             ; X=6: copy 6 bytes of transfer params
; &8a85 referenced 1 time by &8a91
.gbpbf1
    lda (fs_options),y                                                ; 8a85: b1 bb       ..             ; Load param block byte
    sta fs_func_code,x                                                ; 8a87: 9d 06 0f    ...            ; Store to FS command buffer at &0F06+X
    dey                                                               ; 8a8a: 88          .              ; Previous param block byte
    cpy #8                                                            ; 8a8b: c0 08       ..             ; Skip param block offset 8 (the handle)
    bne gbpbx0                                                        ; 8a8d: d0 01       ..             ; Not at handle offset: continue
    dey                                                               ; 8a8f: 88          .              ; Extra DEY to skip handle byte
; &8a90 referenced 1 time by &8a8d
.gbpbx0
.gbpbf2
    dex                                                               ; 8a90: ca          .              ; Decrement copy counter
    bne gbpbf1                                                        ; 8a91: d0 f2       ..             ; Loop for all 6 bytes
    pla                                                               ; 8a93: 68          h              ; Recover function code from stack
    lsr a                                                             ; 8a94: 4a          J              ; LSR: odd=read (C=1), even=write (C=0)
    pha                                                               ; 8a95: 48          H              ; Save function code again (need C later)
    bcc gbpbl1                                                        ; 8a96: 90 01       ..             ; Even (write): X stays 0
    inx                                                               ; 8a98: e8          .              ; Odd (read): X=1
; &8a99 referenced 1 time by &8a96
.gbpbl1
    stx fs_func_code                                                  ; 8a99: 8e 06 0f    ...            ; Store FS direction flag
    ldy #&0b                                                          ; 8a9c: a0 0b       ..             ; Y=&0B: command data extent
    ldx #&91                                                          ; 8a9e: a2 91       ..             ; Command &91=put, &92=get
    pla                                                               ; 8aa0: 68          h              ; Recover function code
    pha                                                               ; 8aa1: 48          H              ; Save again for later direction check
    beq gbpb_write_path                                               ; 8aa2: f0 03       ..             ; Even (write): keep &91 and Y=&0B
    ldx #&92                                                          ; 8aa4: a2 92       ..             ; Odd (read): use &92 (get) instead
    dey                                                               ; 8aa6: 88          .              ; Read: one fewer data byte in command; Y=&0a
; &8aa7 referenced 1 time by &8aa2
.gbpb_write_path
    stx fs_cmd_urd                                                    ; 8aa7: 8e 02 0f    ...            ; Store port to FS command URD field
    stx fs_error_ptr                                                  ; 8aaa: 86 b8       ..             ; Save port for error recovery
    ldx #8                                                            ; 8aac: a2 08       ..             ; X=8: command data bytes
    lda fs_cmd_data                                                   ; 8aae: ad 05 0f    ...            ; Load handle from FS command data
    jsr prepare_cmd_with_flag                                         ; 8ab1: 20 a7 83     ..            ; Build FS command with handle+flag
    lda fs_load_addr_3                                                ; 8ab4: a5 b3       ..             ; Save seq# for byte-stream flow control
    sta fs_sequence_nos                                               ; 8ab6: 8d 08 0e    ...            ; Store to FS sequence number workspace
    ldx #4                                                            ; 8ab9: a2 04       ..             ; X=4: copy 4 address bytes
; &8abb referenced 1 time by &8acf
.gbpbl3
    lda (fs_options),y                                                ; 8abb: b1 bb       ..             ; Set up source/dest from param block
    sta addr_work,y                                                   ; 8abd: 99 af 00    ...            ; Store as source address
    sta txcb_pos,y                                                    ; 8ac0: 99 c7 00    ...            ; Store as current transfer position
    jsr add_4_to_y                                                    ; 8ac3: 20 2a 88     *.            ; Skip 4 bytes to reach transfer length
    adc (fs_options),y                                                ; 8ac6: 71 bb       q.             ; Dest = source + length
    sta addr_work,y                                                   ; 8ac8: 99 af 00    ...            ; Store as end address
    jsr sub_3_from_y                                                  ; 8acb: 20 3d 88     =.            ; Back 3 to align for next iteration
    dex                                                               ; 8ace: ca          .              ; Decrement byte counter
    bne gbpbl3                                                        ; 8acf: d0 ea       ..             ; Loop for all 4 address bytes
    inx                                                               ; 8ad1: e8          .              ; X=1 after loop
; &8ad2 referenced 1 time by &8ad9
.gbpbf3
    lda fs_cmd_csd,x                                                  ; 8ad2: bd 03 0f    ...            ; Copy CSD data to command buffer
    sta fs_func_code,x                                                ; 8ad5: 9d 06 0f    ...            ; Store at &0F06+X
    dex                                                               ; 8ad8: ca          .              ; Decrement counter
    bpl gbpbf3                                                        ; 8ad9: 10 f7       ..             ; Loop for X=1,0
    pla                                                               ; 8adb: 68          h              ; Odd (read): send data to FS first
    bne gbpb_read_path                                                ; 8adc: d0 08       ..             ; Non-zero: skip write path
    lda fs_cmd_urd                                                    ; 8ade: ad 02 0f    ...            ; Load port for transfer setup
    jsr transfer_file_blocks                                          ; 8ae1: 20 41 88     A.            ; Transfer data blocks to fileserver
    bcs wait_fs_reply                                                 ; 8ae4: b0 03       ..             ; Carry set: transfer error
; &8ae6 referenced 1 time by &8adc
.gbpb_read_path
    jsr send_data_blocks                                              ; 8ae6: 20 53 87     S.            ; Read path: receive data blocks from FS
; &8ae9 referenced 1 time by &8ae4
.wait_fs_reply
    jsr send_fs_reply_cmd                                             ; 8ae9: 20 e1 83     ..            ; Wait for FS reply command
    lda (fs_options,x)                                                ; 8aec: a1 bb       ..             ; Load handle mask for EOF flag update
    bit fs_cmd_data                                                   ; 8aee: 2c 05 0f    ,..            ; Check FS reply: bit 7 = not at EOF
    bmi skip_clear_flag                                               ; 8af1: 30 03       0.             ; Bit 7 set: not EOF, skip clear
    jsr clear_fs_flag                                                 ; 8af3: 20 c3 86     ..            ; At EOF: clear EOF hint for this handle
; &8af6 referenced 1 time by &8af1
.skip_clear_flag
    jsr set_fs_flag                                                   ; 8af6: 20 be 86     ..            ; Set EOF hint flag (may be at EOF)
    stx fs_load_addr_2                                                ; 8af9: 86 b2       ..             ; Direction=0: forward adjustment
    jsr adjust_addrs_9                                                ; 8afb: 20 40 8a     @.            ; Adjust param block addrs by +9 bytes
    dec fs_load_addr_2                                                ; 8afe: c6 b2       ..             ; Direction=&FF: reverse adjustment
    sec                                                               ; 8b00: 38          8              ; SEC for reverse subtraction
    jsr adjust_addrs                                                  ; 8b01: 20 48 8a     H.            ; Adjust param block addrs (reverse)
    asl fs_cmd_data                                                   ; 8b04: 0e 05 0f    ...            ; Shift bit 7 into C for return flag
    jmp return_a_zero                                                 ; 8b07: 4c c2 89    L..            ; Return via restore_args path

; &8b0a referenced 1 time by &8b3a
.get_disc_title
    ldy #&15                                                          ; 8b0a: a0 15       ..             ; Y=&15: function code for disc title; Y=function code for HDRFN
    jsr prepare_fs_cmd                                                ; 8b0c: 20 b5 83     ..            ; Build and send FS command; Prepare FS command buffer (12 references)
    lda fs_boot_option                                                ; 8b0f: ad 05 0e    ...            ; Load boot option from FS workspace
    sta fs_boot_data                                                  ; 8b12: 8d 16 0f    ...            ; Store boot option in reply area
    stx fs_load_addr                                                  ; 8b15: 86 b0       ..             ; X=0: reply data start offset; X=0 on success, &D6 on not-found
    stx fs_load_addr_hi                                               ; 8b17: 86 b1       ..             ; Clear reply buffer high byte
    lda #&12                                                          ; 8b19: a9 12       ..             ; A=&12: 18 bytes of reply data
    sta fs_load_addr_2                                                ; 8b1b: 85 b2       ..             ; Store as byte count for copy
    bne copy_reply_to_caller                                          ; 8b1d: d0 4e       .N             ; ALWAYS branch to copy_reply_to_caller; ALWAYS branch

; ***************************************************************************************
; OSGBPB 5-8 info handler (OSINFO)
; 
; Handles the "messy interface tacked onto OSGBPB" (original source).
; Checks whether the destination address is in Tube space by comparing
; the high bytes against TBFLAG. If in Tube space, data must be
; copied via the Tube FIFO registers (with delays to accommodate the
; slow 16032 co-processor) instead of direct memory access.
; ***************************************************************************************
; &8b1f referenced 1 time by &8a76
.osgbpb_info
    ldy #4                                                            ; 8b1f: a0 04       ..             ; Y=4: check param block byte 4
    lda tube_flag                                                     ; 8b21: ad 67 0d    .g.            ; Check if destination is in Tube space
    beq store_tube_flag                                               ; 8b24: f0 07       ..             ; No Tube: skip Tube address check
    cmp (fs_options),y                                                ; 8b26: d1 bb       ..             ; Compare Tube flag with addr byte 4
    bne store_tube_flag                                               ; 8b28: d0 03       ..             ; Mismatch: not Tube space
    dey                                                               ; 8b2a: 88          .              ; Y=&03
    sbc (fs_options),y                                                ; 8b2b: f1 bb       ..             ; Y=3: subtract addr byte 3 from flag
; &8b2d referenced 2 times by &8b24, &8b28
.store_tube_flag
    sta svc_state                                                     ; 8b2d: 85 a9       ..             ; Non-zero = Tube transfer required
; &8b2f referenced 1 time by &8b35
.info2
    lda (fs_options),y                                                ; 8b2f: b1 bb       ..             ; Copy param block bytes 1-4 to workspace
    sta fs_last_byte_flag,y                                           ; 8b31: 99 bd 00    ...            ; Store to &BD+Y workspace area
    dey                                                               ; 8b34: 88          .              ; Previous byte
    bne info2                                                         ; 8b35: d0 f8       ..             ; Loop for bytes 3,2,1
    pla                                                               ; 8b37: 68          h              ; Sub-function: AND #3 of (original A - 4)
    and #3                                                            ; 8b38: 29 03       ).             ; Mask to 0-3 (OSGBPB 5-8 → 0-3)
    beq get_disc_title                                                ; 8b3a: f0 ce       ..             ; A=0 (OSGBPB 5): read disc title
    lsr a                                                             ; 8b3c: 4a          J              ; LSR: A=0 (OSGBPB 6) or A=1 (OSGBPB 7)
    beq gbpb6_read_name                                               ; 8b3d: f0 02       ..             ; A=0 (OSGBPB 6): read CSD/LIB name
    bcs gbpb8_read_dir                                                ; 8b3f: b0 6b       .k             ; C=1 (OSGBPB 8): read filenames from dir
; &8b41 referenced 1 time by &8b3d
.gbpb6_read_name
    tay                                                               ; 8b41: a8          .              ; Y=0 for CSD or carry for fn code select; Y=function code
    lda fs_csd_handle,y                                               ; 8b42: b9 03 0e    ...            ; Get CSD/LIB/URD handles for FS command
    sta fs_cmd_csd                                                    ; 8b45: 8d 03 0f    ...            ; Store CSD handle in command buffer
    lda fs_lib_handle                                                 ; 8b48: ad 04 0e    ...            ; Load LIB handle from workspace
    sta fs_cmd_lib                                                    ; 8b4b: 8d 04 0f    ...            ; Store LIB handle in command buffer
    lda fs_urd_handle                                                 ; 8b4e: ad 02 0e    ...            ; Load URD handle from workspace
    sta fs_cmd_urd                                                    ; 8b51: 8d 02 0f    ...            ; Store URD handle in command buffer
    ldx #&12                                                          ; 8b54: a2 12       ..             ; X=&12: buffer extent for command data; X=buffer extent (command-specific data bytes)
    stx fs_cmd_y_param                                                ; 8b56: 8e 01 0f    ...            ; Store X as function code in header
    lda #&0d                                                          ; 8b59: a9 0d       ..             ; &0D = 13 bytes of reply data expected
    sta fs_func_code                                                  ; 8b5b: 8d 06 0f    ...            ; Store reply length in command buffer
    sta fs_load_addr_2                                                ; 8b5e: 85 b2       ..             ; Store as byte count for copy loop
    lsr a                                                             ; 8b60: 4a          J              ; LSR: &0D >> 1 = 6
    sta fs_cmd_data                                                   ; 8b61: 8d 05 0f    ...            ; Store as command data byte
    clc                                                               ; 8b64: 18          .              ; CLC for standard FS path
    jsr build_send_fs_cmd                                             ; 8b65: 20 cb 83     ..            ; Build and send FS command (DOFSOP)
    stx fs_load_addr_hi                                               ; 8b68: 86 b1       ..             ; X=0 on success, &D6 on not-found
    inx                                                               ; 8b6a: e8          .              ; INX: X=1 after build_send_fs_cmd
    stx fs_load_addr                                                  ; 8b6b: 86 b0       ..             ; Store X as reply start offset
; &8b6d referenced 2 times by &8b1d, &8be5
.copy_reply_to_caller
    lda svc_state                                                     ; 8b6d: a5 a9       ..             ; Copy FS reply to caller's buffer
    bne tube_transfer                                                 ; 8b6f: d0 11       ..             ; Non-zero: use Tube transfer path
    ldx fs_load_addr                                                  ; 8b71: a6 b0       ..             ; X = reply start offset
    ldy fs_load_addr_hi                                               ; 8b73: a4 b1       ..             ; Y = reply buffer high byte
; &8b75 referenced 1 time by &8b7e
.copy_reply_bytes
    lda fs_cmd_data,x                                                 ; 8b75: bd 05 0f    ...            ; Load reply data byte
    sta (fs_crc_lo),y                                                 ; 8b78: 91 be       ..             ; Store to caller's buffer
    inx                                                               ; 8b7a: e8          .              ; Next source byte
    iny                                                               ; 8b7b: c8          .              ; Next destination byte
    dec fs_load_addr_2                                                ; 8b7c: c6 b2       ..             ; Decrement remaining bytes
    bne copy_reply_bytes                                              ; 8b7e: d0 f5       ..             ; Loop until all bytes copied
    beq gbpb_done                                                     ; 8b80: f0 27       .'             ; ALWAYS branch to exit; ALWAYS branch

; &8b82 referenced 1 time by &8b6f
.tube_transfer
    jsr tube_claim_loop                                               ; 8b82: 20 01 8c     ..            ; Claim Tube transfer channel
    lda #1                                                            ; 8b85: a9 01       ..             ; A=1: Tube claim type 1 (write)
    ldx fs_options                                                    ; 8b87: a6 bb       ..             ; X = param block address low
    ldy fs_block_offset                                               ; 8b89: a4 bc       ..             ; Y = param block address high
    inx                                                               ; 8b8b: e8          .              ; INX: advance past byte 0
    bne no_page_wrap                                                  ; 8b8c: d0 01       ..             ; No page wrap: keep Y
    iny                                                               ; 8b8e: c8          .              ; Page wrap: increment high byte
; &8b8f referenced 1 time by &8b8c
.no_page_wrap
    jsr tube_addr_claim                                               ; 8b8f: 20 06 04     ..            ; Claim Tube address for transfer
    ldx fs_load_addr                                                  ; 8b92: a6 b0       ..             ; X = reply data start offset
; &8b94 referenced 1 time by &8ba2
.tbcop1
    lda fs_cmd_data,x                                                 ; 8b94: bd 05 0f    ...            ; Load reply data byte
    sta tube_data_register_3                                          ; 8b97: 8d e5 fe    ...            ; Send byte to Tube via R3
    inx                                                               ; 8b9a: e8          .              ; Next source byte
    ldy #6                                                            ; 8b9b: a0 06       ..             ; Delay loop for slow Tube co-processor
; &8b9d referenced 1 time by &8b9e
.wait_tube_delay
    dey                                                               ; 8b9d: 88          .              ; Decrement delay counter
    bne wait_tube_delay                                               ; 8b9e: d0 fd       ..             ; Loop until delay complete
    dec fs_load_addr_2                                                ; 8ba0: c6 b2       ..             ; Decrement remaining bytes
    bne tbcop1                                                        ; 8ba2: d0 f0       ..             ; Loop until all bytes sent to Tube
    lda #&83                                                          ; 8ba4: a9 83       ..             ; Release Tube after transfer complete
    jsr tube_addr_claim                                               ; 8ba6: 20 06 04     ..            ; Release Tube address claim
; &8ba9 referenced 2 times by &8b80, &8bff
.gbpb_done
    jmp return_a_zero                                                 ; 8ba9: 4c c2 89    L..            ; Return via restore_args path

; &8bac referenced 1 time by &8b3f
.gbpb8_read_dir
    ldy #9                                                            ; 8bac: a0 09       ..             ; OSGBPB 8: read filenames from dir
    lda (fs_options),y                                                ; 8bae: b1 bb       ..             ; Byte 9: number of entries to read
    sta fs_func_code                                                  ; 8bb0: 8d 06 0f    ...            ; Store as reply count in command buffer
    ldy #5                                                            ; 8bb3: a0 05       ..             ; Y=5: byte 5 = starting entry number
    lda (fs_options),y                                                ; 8bb5: b1 bb       ..             ; Load starting entry number
    sta fs_data_count                                                 ; 8bb7: 8d 07 0f    ...            ; Store in command buffer
    ldx #&0d                                                          ; 8bba: a2 0d       ..             ; X=&0D: command data extent; X=preserved through header build
    stx fs_reply_cmd                                                  ; 8bbc: 8e 08 0f    ...            ; Store extent in command buffer
    ldy #2                                                            ; 8bbf: a0 02       ..             ; Y=2: function code for dir read
    sty fs_load_addr                                                  ; 8bc1: 84 b0       ..             ; Store 2 as reply data start offset
    sty fs_cmd_data                                                   ; 8bc3: 8c 05 0f    ...            ; Store 2 as command data byte
    iny                                                               ; 8bc6: c8          .              ; Y=3: function code for header read; Y=function code for HDRFN; Y=&03
    jsr prepare_fs_cmd                                                ; 8bc7: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    stx fs_load_addr_hi                                               ; 8bca: 86 b1       ..             ; X=0 after FS command completes; X=0 on success, &D6 on not-found
    lda fs_func_code                                                  ; 8bcc: ad 06 0f    ...            ; Load reply entry count
    sta (fs_options,x)                                                ; 8bcf: 81 bb       ..             ; Store at param block byte 0 (X=0)
    lda fs_cmd_data                                                   ; 8bd1: ad 05 0f    ...            ; Load entries-read count from reply
    ldy #9                                                            ; 8bd4: a0 09       ..             ; Y=9: param block byte 9
    adc (fs_options),y                                                ; 8bd6: 71 bb       q.             ; Add to starting entry number
    sta (fs_options),y                                                ; 8bd8: 91 bb       ..             ; Update param block with new position
    lda txcb_end                                                      ; 8bda: a5 c8       ..             ; Load total reply length
    sbc #7                                                            ; 8bdc: e9 07       ..             ; Subtract header (7 bytes) from reply len
    sta fs_func_code                                                  ; 8bde: 8d 06 0f    ...            ; Store adjusted length in command buffer
    sta fs_load_addr_2                                                ; 8be1: 85 b2       ..             ; Store as byte count for copy loop
    beq skip_copy_reply                                               ; 8be3: f0 03       ..             ; Zero bytes: skip copy
    jsr copy_reply_to_caller                                          ; 8be5: 20 6d 8b     m.            ; Copy reply data to caller's buffer
; &8be8 referenced 1 time by &8be3
.skip_copy_reply
    ldx #2                                                            ; 8be8: a2 02       ..             ; X=2: clear 3 bytes
; &8bea referenced 1 time by &8bee
.zero_cmd_bytes
    sta fs_data_count,x                                               ; 8bea: 9d 07 0f    ...            ; Zero out &0F07+X area
    dex                                                               ; 8bed: ca          .              ; Next byte
    bpl zero_cmd_bytes                                                ; 8bee: 10 fa       ..             ; Loop for X=2,1,0
    jsr adjust_addrs_1                                                ; 8bf0: 20 45 8a     E.            ; Adjust pointer by +1 (one filename read)
    sec                                                               ; 8bf3: 38          8              ; SEC for reverse adjustment
    dec fs_load_addr_2                                                ; 8bf4: c6 b2       ..             ; Reverse adjustment for updated counter
    lda fs_cmd_data                                                   ; 8bf6: ad 05 0f    ...            ; Load entries-read count
    sta fs_func_code                                                  ; 8bf9: 8d 06 0f    ...            ; Store in command buffer
    jsr adjust_addrs                                                  ; 8bfc: 20 48 8a     H.            ; Adjust param block addresses
    beq gbpb_done                                                     ; 8bff: f0 a8       ..             ; Z=1: all done, exit
; &8c01 referenced 3 times by &8b82, &8c06, &8e20
.tube_claim_loop
    lda #&c3                                                          ; 8c01: a9 c3       ..             ; A=&C3: Tube claim with retry
    jsr tube_addr_claim                                               ; 8c03: 20 06 04     ..            ; Request Tube address claim
    bcc tube_claim_loop                                               ; 8c06: 90 f9       ..             ; C=0: claim failed, retry
    rts                                                               ; 8c08: 60          `              ; Tube claimed successfully

; ***************************************************************************************
; FSCV 2/3/4: unrecognised * command handler (DECODE)
; 
; CLI parser originally by Sophie Wilson (co-designer of ARM). Matches command text
; against the table
; at &8C4B using case-insensitive comparison with abbreviation
; support — commands can be shortened with '.' (e.g. "I." for
; "INFO"). The "I." entry is a special fudge placed first in the
; table: since "I." could match multiple commands, it jumps to
; forward_star_cmd to let the fileserver resolve the ambiguity.
; 
; The matching loop compares input characters against table
; entries. On mismatch, it skips to the next entry. On match
; of all table characters, or when '.' abbreviation is found,
; it dispatches via PHA/PHA/RTS to the entry's handler address.
; 
; After matching, adjusts fs_crc_lo/fs_crc_hi to point past
; the matched command text.
; ***************************************************************************************
; &8c09 referenced 1 time by &827d
.fscv_3_star_cmd
    jsr save_fscv_args_with_ptrs                                      ; 8c09: 20 37 86     7.            ; Save A/X/Y and set up command ptr
    ldx #&ff                                                          ; 8c0c: a2 ff       ..             ; X=&FF: table index (pre-incremented)
    stx fs_crflag                                                     ; 8c0e: 86 b9       ..             ; Disable column formatting
    stx escapable                                                     ; 8c10: 86 97       ..             ; Enable escape checking
; &8c12 referenced 1 time by &8c2d
.scan_cmd_table
    ldy #&ff                                                          ; 8c12: a0 ff       ..             ; Y=&FF: input index (pre-incremented)
; &8c14 referenced 1 time by &8c1f
.decfir
    iny                                                               ; 8c14: c8          .              ; Advance input pointer
    inx                                                               ; 8c15: e8          .              ; Advance table pointer
; &8c16 referenced 1 time by &8c31
.decmor
    lda fs_cmd_match_table,x                                          ; 8c16: bd 39 8c    .9.            ; Load table character
    bmi dispatch_cmd                                                  ; 8c19: 30 18       0.             ; Bit 7: end of name, dispatch
    eor (fs_crc_lo),y                                                 ; 8c1b: 51 be       Q.             ; XOR input char with table char
    and #&df                                                          ; 8c1d: 29 df       ).             ; Case-insensitive (clear bit 5)
    beq decfir                                                        ; 8c1f: f0 f3       ..             ; Match: continue comparing
    dex                                                               ; 8c21: ca          .              ; Mismatch: back up table pointer
; &8c22 referenced 1 time by &8c26
.decmin
    inx                                                               ; 8c22: e8          .              ; Skip to end of table entry
    lda fs_cmd_match_table,x                                          ; 8c23: bd 39 8c    .9.            ; Load table byte
    bpl decmin                                                        ; 8c26: 10 fa       ..             ; Loop until bit 7 set (end marker)
    lda (fs_crc_lo),y                                                 ; 8c28: b1 be       ..             ; Check input for '.' abbreviation
    inx                                                               ; 8c2a: e8          .              ; Skip past handler high byte
    cmp #&2e ; '.'                                                    ; 8c2b: c9 2e       ..             ; Is input '.' (abbreviation)?
    bne scan_cmd_table                                                ; 8c2d: d0 e3       ..             ; No: try next table entry
    iny                                                               ; 8c2f: c8          .              ; Yes: skip '.' in input
    dex                                                               ; 8c30: ca          .              ; Back to handler high byte
    bcs decmor                                                        ; 8c31: b0 e3       ..             ; ALWAYS branch; dispatch via BMI
; &8c33 referenced 1 time by &8c19
.dispatch_cmd
    pha                                                               ; 8c33: 48          H              ; Push handler address high byte
    lda cmd_match_data,x                                              ; 8c34: bd 3a 8c    .:.            ; Load handler address low byte
    pha                                                               ; 8c37: 48          H              ; Push handler address low byte
    rts                                                               ; 8c38: 60          `              ; Dispatch via RTS (addr-1 on stack)

; ***************************************************************************************
; FS command match table (COMTAB)
; 
; Format: command letters (bit 7 clear), then dispatch address
; as two big-endian bytes: high|(bit 7 set), low. The bit 7 set
; on the high byte marks the end of the command string. The
; PHA/PHA/RTS trick adds 1 to the stored (address-1). Matching
; is case-insensitive (AND &DF) and supports '.' abbreviation.
; 
; Entries:
;   "I."     → &80BD (forward_star_cmd) — placed first as a fudge
;              to catch *I. abbreviation before matching *I AM
;   "I AM"   → &8082 (i_am_handler: parse station.net, logon)
;   "}EX"    → &8C4F (ex_handler: } terminator rejects *EXEC)
;   "BYE"\r  → &83AE (bye_handler: logoff)
;   <catch-all> → &80BD (forward anything else to FS)
; ***************************************************************************************
; &8c39 referenced 2 times by &8c16, &8c23
.fs_cmd_match_table
cmd_match_data = fs_cmd_match_table+1
    eor #&2e ; '.'                                                    ; 8c39: 49 2e       I.             ; Match last char against '.' for *I. abbreviation
; &8c3a referenced 1 time by &8c34
    equb &80                                                          ; 8c3b: 80          .              ; I. handler hi → &80BD (forward_star_cmd)
    equb &bc                                                          ; 8c3c: bc          .              ; I. handler lo
    equs "I AM"                                                       ; 8c3d: 49 20 41... I A            ; "I AM" command string
    equb &80                                                          ; 8c41: 80          .              ; I AM handler hi (shared lo for I.)
    equs "}EX"                                                        ; 8c42: 7d 45 58    }EX            ; "}EX" command (} = special terminator)
    equb &8c                                                          ; 8c45: 8c          .              ; EX handler hi → &8C4F (ex_handler)
    equs "NBYE"                                                       ; 8c46: 4e 42 59... NBY            ; "NBYE" command (BYE with N prefix)
    equb &0d                                                          ; 8c4a: 0d          .              ; CR terminator for BYE
    equb &83                                                          ; 8c4b: 83          .              ; BYE handler hi → &83AE (bye_handler)
    equb &ad                                                          ; 8c4c: ad          .              ; BYE handler lo
    equb &80                                                          ; 8c4d: 80          .              ; Catch-all hi → &80BD (forward_star_cmd)
    equb &bc                                                          ; 8c4e: bc          .              ; Catch-all lo

.ex_handler
    ldx #1                                                            ; 8c4f: a2 01       ..             ; X=1: force one entry per line for *EX
    lda #3                                                            ; 8c51: a9 03       ..             ; A=3: examine format code
    bne init_cat_params                                               ; 8c53: d0 0b       ..             ; ALWAYS branch

; ***************************************************************************************
; *CAT handler (directory catalogue)
; 
; Initialises &B5=&0B (examine arg count) and &B7=&03 (column
; count). The catalogue protocol is multi-step: first sends
; FCREAD (&12: examine) to get the directory header, then sends
; FCUSER (&15: read user environment) to get CSD, disc, and
; library names, then sends FC &03 (examine entries) repeatedly
; to fetch entries in batches until zero are returned (end of dir).
; The receive buffer abuts the examine request buffer and ends at
; RXBUFE, allowing seamless data handling across request cycles.
; 
; The command code byte in the fileserver reply indicates FS type:
; zero means an old-format FS (client must format data locally),
; non-zero means new-format (server returns pre-formatted strings).
; This enables backward compatibility with older Acorn fileservers.
; 
; Display format:
;   - Station number in parentheses
;   - "Owner" or "Public" access level
;   - Boot option with name (Off/Load/Run/Exec)
;   - Current directory and library paths
;   - Directory entries: CRFLAG (&B9) cycles 0-3 for multi-column
;     layout; at count 0 a newline is printed, others get spaces.
;     *EX sets CRFLAG=&FF to force one entry per line.
; ***************************************************************************************
.fscv_5_cat
    ldx #3                                                            ; 8c55: a2 03       ..             ; X=3: column count for multi-column layout
    stx fs_crflag                                                     ; 8c57: 86 b9       ..             ; CRFLAG=3: first entry will trigger newline
    ldy #&ff                                                          ; 8c59: a0 ff       ..             ; Y=&FF: mark as escapable
    sty escapable                                                     ; 8c5b: 84 97       ..             ; Store escapable flag for Escape checking
    iny                                                               ; 8c5d: c8          .              ; Y=&00
    lda #&0b                                                          ; 8c5e: a9 0b       ..             ; A=&0B: examine argument count
; &8c60 referenced 1 time by &8c53
.init_cat_params
    sta fs_work_5                                                     ; 8c60: 85 b5       ..             ; Store examine argument count
    stx fs_work_7                                                     ; 8c62: 86 b7       ..             ; Store column count
    lda #6                                                            ; 8c64: a9 06       ..             ; A=6: examine format type in command
    sta fs_cmd_data                                                   ; 8c66: 8d 05 0f    ...            ; Store format type at &0F05
    jsr parse_filename_gs_y                                           ; 8c69: 20 d8 86     ..            ; Set up command parameter pointers
    ldx #1                                                            ; 8c6c: a2 01       ..             ; X=1: copy dir name at cmd offset 1
    jsr copy_string_to_cmd                                            ; 8c6e: 20 72 8d     r.            ; Copy directory name to command buffer
    ldy #&12                                                          ; 8c71: a0 12       ..             ; Y=function code for HDRFN
    jsr prepare_fs_cmd                                                ; 8c73: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    ldx #3                                                            ; 8c76: a2 03       ..             ; X=3: start printing from reply offset 3
    jsr print_reply_bytes                                             ; 8c78: 20 35 8d     5.            ; Print directory title (10 chars)
    jsr print_inline                                                  ; 8c7b: 20 4a 86     J.            ; Print '('
    equs "("                                                          ; 8c7e: 28          (              ; "(" inline string data

    lda fs_reply_stn                                                  ; 8c7f: ad 13 0f    ...            ; Load station number from FS reply
    jsr print_decimal                                                 ; 8c82: 20 ab 8d     ..            ; Print station number as decimal
    jsr print_inline                                                  ; 8c85: 20 4a 86     J.            ; Print ')     '
    equs ")     "                                                     ; 8c88: 29 20 20... )              ; ")     " inline string data

    ldy fs_access_level                                               ; 8c8e: ac 12 0f    ...            ; Access level byte: 0=Owner, non-zero=Public
    bne print_public                                                  ; 8c91: d0 0b       ..             ; Non-zero: Public access
    jsr print_inline                                                  ; 8c93: 20 4a 86     J.            ; Print 'Owner' + CR
    equs "Owner", &0d                                                 ; 8c96: 4f 77 6e... Own            ; "Owner" + CR inline string data

    bne print_user_env                                                ; 8c9c: d0 0a       ..             ; Always branches (print_inline sets N=1)
; &8c9e referenced 1 time by &8c91
.print_public
    jsr print_inline                                                  ; 8c9e: 20 4a 86     J.            ; Print 'Public' + CR
    equs "Public", &0d                                                ; 8ca1: 50 75 62... Pub            ; "Public" + CR inline string data

; &8ca8 referenced 1 time by &8c9c
.print_user_env
    ldy #&15                                                          ; 8ca8: a0 15       ..             ; Y=function code for HDRFN
    jsr prepare_fs_cmd                                                ; 8caa: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    inx                                                               ; 8cad: e8          .              ; X=1: past command code byte
    ldy #&10                                                          ; 8cae: a0 10       ..             ; Y=&10: print 16 characters
    jsr print_reply_counted                                           ; 8cb0: 20 37 8d     7.            ; Print disc/CSD name from reply
    jsr print_inline                                                  ; 8cb3: 20 4a 86     J.            ; Print '    Option '
    equs "    Option "                                                ; 8cb6: 20 20 20...                ; "    Option " inline string data

    lda fs_boot_option                                                ; 8cc1: ad 05 0e    ...            ; Load boot option from workspace
    tax                                                               ; 8cc4: aa          .              ; X = boot option for name table lookup
    jsr print_hex_byte                                                ; 8cc5: 20 ca 8d     ..            ; Print boot option as hex digit
    jsr print_inline                                                  ; 8cc8: 20 4a 86     J.            ; Print ' ('
    equs " ("                                                         ; 8ccb: 20 28        (             ; " (" inline string data

    ldy option_name_offsets,x                                         ; 8ccd: bc 42 8d    .B.            ; Load string offset for option name
; &8cd0 referenced 1 time by &8cd9
.print_option_name
    lda option_name_offsets,y                                         ; 8cd0: b9 42 8d    .B.            ; Load character from option name string
    bmi done_option_name                                              ; 8cd3: 30 06       0.             ; Bit7 set: string terminated, done
    jsr osasci                                                        ; 8cd5: 20 e3 ff     ..            ; Write character
    iny                                                               ; 8cd8: c8          .              ; Next character
    bne print_option_name                                             ; 8cd9: d0 f5       ..             ; Continue printing option name
; &8cdb referenced 1 time by &8cd3
.done_option_name
    jsr print_inline                                                  ; 8cdb: 20 4a 86     J.            ; Print ')' + CR + 'Dir. '
    equs ")", &0d, "Dir. "                                            ; 8cde: 29 0d 44... ).D            ; ") CR Dir. " inline string data

    ldx #&11                                                          ; 8ce5: a2 11       ..             ; X=&11: directory name offset in reply
    jsr print_reply_bytes                                             ; 8ce7: 20 35 8d     5.            ; Print current directory name
    jsr print_inline                                                  ; 8cea: 20 4a 86     J.            ; Print '     Lib. '
    equs "     Lib. "                                                 ; 8ced: 20 20 20...                ; "     Lib. " inline string data

    ldx #&1b                                                          ; 8cf7: a2 1b       ..             ; X=&1B: library name offset in reply
    jsr print_reply_bytes                                             ; 8cf9: 20 35 8d     5.            ; Print library name
    jsr osnewl                                                        ; 8cfc: 20 e7 ff     ..            ; Print two CRs (blank line); Write newline (characters 10 and 13)
; &8cff referenced 1 time by &8d33
.fetch_dir_batch
    sty fs_func_code                                                  ; 8cff: 8c 06 0f    ...            ; Store entry start offset for request
    sty fs_work_4                                                     ; 8d02: 84 b4       ..             ; Save start offset in zero page for loop
    ldx fs_work_5                                                     ; 8d04: a6 b5       ..             ; Load examine arg count for batch size
    stx fs_data_count                                                 ; 8d06: 8e 07 0f    ...            ; Store as request count at &0F07
.cat_examine_loop
    ldx fs_work_7                                                     ; 8d09: a6 b7       ..             ; Load column count for display format
    stx fs_cmd_data                                                   ; 8d0b: 8e 05 0f    ...            ; Store column count in command data
    ldx #3                                                            ; 8d0e: a2 03       ..             ; X=3: copy directory name at offset 3
    jsr copy_string_to_cmd                                            ; 8d10: 20 72 8d     r.            ; Append directory name to examine command
    ldy #3                                                            ; 8d13: a0 03       ..             ; Y=function code for HDRFN
    jsr prepare_fs_cmd                                                ; 8d15: 20 b5 83     ..            ; Prepare FS command buffer (12 references)
    inx                                                               ; 8d18: e8          .              ; X past command code byte in reply
    lda fs_cmd_data                                                   ; 8d19: ad 05 0f    ...            ; Load entry count from reply
    bne process_entries                                               ; 8d1c: d0 03       ..             ; Zero entries returned = end of directory
    jmp osnewl                                                        ; 8d1e: 4c e7 ff    L..            ; Write newline (characters 10 and 13)

; &8d21 referenced 1 time by &8d1c
.process_entries
    pha                                                               ; 8d21: 48          H              ; Save entry count for batch processing
; &8d22 referenced 1 time by &8d26
.scan_entry_terminator
    iny                                                               ; 8d22: c8          .              ; Advance Y past entry data bytes
    lda fs_cmd_data,y                                                 ; 8d23: b9 05 0f    ...            ; Read entry byte from reply buffer
    bpl scan_entry_terminator                                         ; 8d26: 10 fa       ..             ; Loop until high-bit terminator found
    sta fs_cmd_lib,y                                                  ; 8d28: 99 04 0f    ...            ; Store terminator as print boundary
    jsr cat_column_separator                                          ; 8d2b: 20 8d 8d     ..            ; Print/format this directory entry
    pla                                                               ; 8d2e: 68          h              ; Restore entry count from stack
    clc                                                               ; 8d2f: 18          .              ; CLC for addition
    adc fs_work_4                                                     ; 8d30: 65 b4       e.             ; Advance start offset by entry count
    tay                                                               ; 8d32: a8          .              ; Y = new entry start offset
    bne fetch_dir_batch                                               ; 8d33: d0 ca       ..             ; More entries: fetch next batch
; &8d35 referenced 3 times by &8c78, &8ce7, &8cf9
.print_reply_bytes
    ldy #&0a                                                          ; 8d35: a0 0a       ..             ; Y=&0A: default print 10 characters
; &8d37 referenced 2 times by &8cb0, &8d3f
.print_reply_counted
    lda fs_cmd_data,x                                                 ; 8d37: bd 05 0f    ...            ; Load reply byte at offset X
    jsr osasci                                                        ; 8d3a: 20 e3 ff     ..            ; Write character
    inx                                                               ; 8d3d: e8          .              ; Next reply byte
    dey                                                               ; 8d3e: 88          .              ; Decrement character count
    bne print_reply_counted                                           ; 8d3f: d0 f6       ..             ; Loop for remaining characters
; Option name encoding: the boot option names ("Off", "Load",
; "Run", "Exec") are scattered through the code rather than
; stored as a contiguous table. They are addressed via base+offset
; from option_name_offsets (&8D42), whose four bytes are offsets:
;   &2B→option_name_offsets+&2B "Off",
;   &3E→option_name_offsets+&3E "Load",
;   &66→option_name_offsets+&66 "Run",
;   &18→option_name_offsets+&18 "Exec"
; Each string is terminated by the next instruction's opcode
; having bit 7 set (e.g. LDA #imm = &A9, RTS = &60).
.return_9
    rts                                                               ; 8d41: 60          `              ; Return from column separator

; &8d42 referenced 2 times by &8ccd, &8cd0
.option_name_offsets
    equs "+>f"                                                        ; 8d42: 2b 3e 66    +>f            ; Boot option name offsets (4 entries)
    equb &18                                                          ; 8d45: 18          .              ; Offset &18: Exec option name start
    equs "L.!"                                                        ; 8d46: 4c 2e 21    L.!            ; Boot option name string data "L.!"
; ***************************************************************************************
; Boot command strings for auto-boot
; 
; The four boot options use OSCLI strings at offsets within page &8D.
; The offset table at boot_option_offsets+1 is indexed by
; the boot option value (0-3); each byte is the low byte of the
; string address, with the page high byte loaded separately:
;   Option 0 (Off):  offset &55 → boot_option_offsets = bare CR
;   Option 1 (Load): offset &46 → "L.!BOOT" (the bytes
;       &4C='L', &2E='.', &21='!' precede "BOOT" + CR at &8D4D)
;   Option 2 (Run):  offset &48 → boot_cmd_strings-1 = "!BOOT"
;   Option 3 (Exec): offset &4E → &8D4E = "E.!BOOT"
; 
; This is a classic BBC ROM space optimisation: the string data
; overlaps with other byte sequences to save space. The &0D byte
; at &8D55 terminates "E.!BOOT" AND doubles as the bare-CR
; command for boot option 0.
; ***************************************************************************************
.boot_cmd_strings
    equs "BOOT"                                                       ; 8d49: 42 4f 4f... BOO            ; "BOOT" command string tail
    equb &0d                                                          ; 8d4d: 0d          .              ; CR terminator for BOOT string
    equs "E.!BOOT"                                                    ; 8d4e: 45 2e 21... E.!            ; "E.!BOOT" exec boot command

; ***************************************************************************************
; Boot option → OSCLI string offset table
; 
; Five bytes: the first byte (&0D) is the bare-CR target for boot
; option 0; bytes 1-4 are the offset table indexed by boot option
; (0-3). Each offset is the low byte of a pointer into page &8D.
; The code reads from boot_option_offsets+1 (&8D68) via
; LDX l8d56,Y with Y=boot_option, then LDY #&8D, JMP oscli.
; See boot_cmd_strings for the target strings.
; ***************************************************************************************
.boot_option_offsets
boot_string_offsets = boot_option_offsets+1
    ora l4655                                                         ; 8d55: 0d 55 46    .UF            ; Opt 0 (Off): bare CR at &8D55; Opt 1 (Load): L.!BOOT at &8D46
; &8d56 referenced 1 time by &8e4e
    pha                                                               ; 8d58: 48          H              ; Opt 2 (Run): !BOOT at boot_cmd_strings-1
    lsr l7845                                                         ; 8d59: 4e 45 78    NEx            ; Opt 3 (Exec): E.!BOOT at &8D4E
    adc l0063                                                         ; 8d5c: 65 63       ec             ; Boot string overlap: "ec" tail of "Exec"
; &8d5e referenced 2 times by &87f3, &87f8
.print_hex_bytes
    ldx #4                                                            ; 8d5e: a2 04       ..             ; X=4: print 4 hex bytes
; &8d60 referenced 1 time by &87ff
.num01
    lda (fs_options),y                                                ; 8d60: b1 bb       ..             ; Load byte from parameter block
    jsr print_hex_byte                                                ; 8d62: 20 ca 8d     ..            ; Print as two hex digits
    dey                                                               ; 8d65: 88          .              ; Next byte (descending)
    dex                                                               ; 8d66: ca          .              ; Count down
    equb &d0                                                          ; 8d67: d0          .              ; Loop until 4 bytes printed
    equb &f7                                                          ; 8d68: f7          .              ; BNE operand (also boot offset data)
; &8d69 referenced 1 time by &87e9
.print_space
    equb &a9                                                          ; 8d69: a9          .              ; A=space character
    equb &20                                                          ; 8d6a: 20                         ; LDA #&20 operand (space)
    equb &d0                                                          ; 8d6b: d0          .              ; BNE opcode (also string overlap)
    equs "ZOff"                                                       ; 8d6c: 5a 4f 66... ZOf            ; Boot option name "Exec" starts here

; ***************************************************************************************
; Copy filename to FS command buffer
; 
; Entry with X=0: copies from (fs_crc_lo),Y to &0F05+X until CR.
; Used to place a filename into the FS command buffer before
; sending to the fileserver. Falls through to copy_string_to_cmd.
; 
; On Exit:
;     X: next free position in cmd buffer
;     Y: string length (incl CR)
;     A: 0 (from EOR &0D with final CR)
; ***************************************************************************************
; &8d70 referenced 5 times by &8099, &80bd, &870b, &8905, &8de2
.infol2
.copy_filename
    ldx #0                                                            ; 8d70: a2 00       ..             ; Start writing at &0F05 (after cmd header)
; ***************************************************************************************
; Copy string to FS command buffer
; 
; Entry with X and Y specified: copies bytes from (fs_crc_lo),Y
; to &0F05+X, stopping when a CR (&0D) is encountered. The CR
; itself is also copied. Returns with X pointing past the last
; byte written.
; 
; On Entry:
;     X: destination offset in fs_cmd_data (&0F05+X)
; 
; On Exit:
;     X: next free position past CR
;     Y: string length (incl CR)
;     A: 0 (from EOR &0D with final CR)
; ***************************************************************************************
; &8d72 referenced 6 times by &87b8, &88fe, &8920, &89e4, &8c6e, &8d10
.copy_string_to_cmd
    ldy #0                                                            ; 8d72: a0 00       ..             ; Start copying from offset 0
; &8d74 referenced 1 time by &8d7d
.copy_string_from_offset
    lda (fs_crc_lo),y                                                 ; 8d74: b1 be       ..             ; Load next byte from source string
    sta fs_cmd_data,x                                                 ; 8d76: 9d 05 0f    ...            ; Store to FS command buffer (&0F05+X)
    inx                                                               ; 8d79: e8          .              ; Advance write position
    iny                                                               ; 8d7a: c8          .              ; Advance source pointer
    eor #&0d                                                          ; 8d7b: 49 0d       I.             ; XOR with CR: result=0 if byte was CR
    bne copy_string_from_offset                                       ; 8d7d: d0 f5       ..             ; Loop until CR copied
; &8d7f referenced 1 time by &8d89
.return_5
    rts                                                               ; 8d7f: 60          `              ; Return; X = next free position in buffer

    equs "Load"                                                       ; 8d80: 4c 6f 61... Loa            ; "Load" boot option name string

; ***************************************************************************************
; Print directory name from reply buffer
; 
; Prints characters from the FS reply buffer (&0F05+X onwards).
; Null bytes (&00) are replaced with CR (&0D) for display.
; Stops when a byte with bit 7 set is encountered (high-bit
; terminator). Used by fscv_5_cat to display Dir. and Lib. paths.
; ***************************************************************************************
.fsreply_0_print_dir
    ldx #0                                                            ; 8d84: a2 00       ..             ; X=0: start from first reply byte
; &8d86 referenced 2 times by &87d8, &8da6
.print_dir_from_offset
    lda fs_cmd_data,x                                                 ; 8d86: bd 05 0f    ...            ; Load byte from FS reply buffer
    bmi return_5                                                      ; 8d89: 30 f4       0.             ; Bit 7 set: end of string, return
    bne print_newline                                                 ; 8d8b: d0 15       ..             ; Non-zero: print character
; ***************************************************************************************
; Print catalogue column separator or newline
; 
; Handles column formatting for *CAT display. On a null byte
; separator, advances the column counter modulo 4: prints a
; 2-space separator between columns, or a CR at column 0.
; Called from fsreply_0_print_dir.
; ***************************************************************************************
; &8d8d referenced 1 time by &8d2b
.cat_column_separator
    ldy fs_crflag                                                     ; 8d8d: a4 b9       ..             ; Null byte: check column counter
    bmi print_cr                                                      ; 8d8f: 30 0f       0.             ; Negative: print CR (no columns)
    iny                                                               ; 8d91: c8          .              ; Advance column counter
    tya                                                               ; 8d92: 98          .              ; Transfer to A for modulo
    and #3                                                            ; 8d93: 29 03       ).             ; Modulo 4 columns
    sta fs_crflag                                                     ; 8d95: 85 b9       ..             ; Update column counter
    beq print_cr                                                      ; 8d97: f0 07       ..             ; Column 0: start new line
    jsr print_inline                                                  ; 8d99: 20 4a 86     J.            ; Print 2-space column separator
    equs "  "                                                         ; 8d9c: 20 20                      ; "  " column separator string

    bne next_dir_entry                                                ; 8d9e: d0 05       ..             ; ALWAYS branch to next byte
; &8da0 referenced 2 times by &8d8f, &8d97
.print_cr
    lda #&0d                                                          ; 8da0: a9 0d       ..             ; CR = carriage return
; &8da2 referenced 1 time by &8d8b
.print_newline
    jsr osasci                                                        ; 8da2: 20 e3 ff     ..            ; Write character 13
; &8da5 referenced 1 time by &8d9e
.next_dir_entry
    inx                                                               ; 8da5: e8          .              ; Next byte in reply buffer
    bne print_dir_from_offset                                         ; 8da6: d0 de       ..             ; Loop until end of buffer
    equs "Run"                                                        ; 8da8: 52 75 6e    Run            ; "Run" boot option name string

; ***************************************************************************************
; Print byte as 3-digit decimal number
; 
; Prints A as a decimal number using repeated subtraction
; for each digit position (100, 10, 1). Leading zeros are
; printed (no suppression). Used to display station numbers.
; 
; On Entry:
;     A: byte value to print
; 
; On Exit:
;     A: last digit character
;     X: corrupted
;     Y: 0 (remainder after last division)
; ***************************************************************************************
; &8dab referenced 2 times by &8236, &8c82
.print_decimal
    tay                                                               ; 8dab: a8          .              ; Y = value to print
    lda #&64 ; 'd'                                                    ; 8dac: a9 64       .d             ; Divisor = 100 (hundreds digit)
    jsr print_decimal_digit                                           ; 8dae: 20 b8 8d     ..            ; Print hundreds digit
    lda #&0a                                                          ; 8db1: a9 0a       ..             ; Divisor = 10 (tens digit)
    jsr print_decimal_digit                                           ; 8db3: 20 b8 8d     ..            ; Print tens digit
    lda #1                                                            ; 8db6: a9 01       ..             ; Divisor = 1; fall through to units
; ***************************************************************************************
; Print one decimal digit by repeated subtraction
; 
; Divides Y by A using repeated subtraction. Prints the
; quotient as an ASCII digit ('0'-'9') via OSASCI. Returns
; with the remainder in Y. X starts at &2F ('0'-1) and
; increments once per subtraction, giving the ASCII digit
; directly.
; 
; On Entry:
;     A: divisor (stored to &B8)
;     Y: dividend
; 
; On Exit:
;     Y: remainder
; ***************************************************************************************
; &8db8 referenced 2 times by &8dae, &8db3
.print_decimal_digit
    sta fs_error_ptr                                                  ; 8db8: 85 b8       ..             ; Save divisor to workspace
    tya                                                               ; 8dba: 98          .              ; A = dividend (from Y)
    ldx #&2f ; '/'                                                    ; 8dbb: a2 2f       ./             ; X = &2F = ASCII '0' - 1
    sec                                                               ; 8dbd: 38          8              ; Prepare for subtraction
; &8dbe referenced 1 time by &8dc1
.divide_subtract
    inx                                                               ; 8dbe: e8          .              ; Count one subtraction (next digit value)
    sbc fs_error_ptr                                                  ; 8dbf: e5 b8       ..             ; A = A - divisor
    bcs divide_subtract                                               ; 8dc1: b0 fb       ..             ; Loop while A >= 0 (borrow clear)
    adc fs_error_ptr                                                  ; 8dc3: 65 b8       e.             ; Undo last subtraction: A = remainder
    tay                                                               ; 8dc5: a8          .              ; Y = remainder for caller
    txa                                                               ; 8dc6: 8a          .              ; A = X = ASCII digit character
; &8dc7 referenced 2 times by &8dd9, &8ddd
.print_digit
    jmp osasci                                                        ; 8dc7: 4c e3 ff    L..            ; Write character

; ***************************************************************************************
; Print A as two hexadecimal digits
; 
; Prints the byte in A as two hex digits (e.g. &3F prints "3F").
; Saves A, shifts high nibble down, prints it via print_hex_nibble,
; then recovers the original A and prints the low nibble.
; The nibble-to-hex conversion uses ORA #&30 / CMP #&3A to
; distinguish 0-9 (ASCII &30-&39) from A-F (add 7 more).
; New in 3.65: moved inline from &9F9D (end of ROM in 3.62).
; ***************************************************************************************
; &8dca referenced 2 times by &8cc5, &8d62
.print_hex_byte
    pha                                                               ; 8dca: 48          H              ; Save original byte
    lsr a                                                             ; 8dcb: 4a          J              ; Shift high nibble to low position
    lsr a                                                             ; 8dcc: 4a          J              ; LSR (continued)
    lsr a                                                             ; 8dcd: 4a          J              ; LSR (continued)
    lsr a                                                             ; 8dce: 4a          J              ; LSR (continued): A = high nibble
    jsr print_hex_nibble                                              ; 8dcf: 20 d5 8d     ..            ; Print high nibble as hex digit
    pla                                                               ; 8dd2: 68          h              ; Recover original byte
    and #&0f                                                          ; 8dd3: 29 0f       ).             ; Mask to low nibble
; &8dd5 referenced 1 time by &8dcf
.print_hex_nibble
    ora #&30 ; '0'                                                    ; 8dd5: 09 30       .0             ; Convert nibble to ASCII: &00-&09 -> '0'-'9'
    cmp #&3a ; ':'                                                    ; 8dd7: c9 3a       .:             ; Digit or letter? &3A = ':'
    bcc print_digit                                                   ; 8dd9: 90 ec       ..             ; Digit 0-9: print directly
    adc #6                                                            ; 8ddb: 69 06       i.             ; Letter A-F: add 7 (carry already set)
    bne print_digit                                                   ; 8ddd: d0 e8       ..             ; ALWAYS branch to print_digit
; ***************************************************************************************
; FSCV 2/4: */ (run) and *RUN handler
; 
; Parses the filename via parse_filename_gs and calls infol2,
; then falls through to fsreply_4_notify_exec to set up and
; send the FS load-as-command request.
; ***************************************************************************************
.fscv_2_star_run
    jsr parse_filename_gs                                             ; 8ddf: 20 d6 86     ..            ; Parse filename from command line
    jsr infol2                                                        ; 8de2: 20 70 8d     p.            ; Copy filename to FS command buffer
; ***************************************************************************************
; FS reply 4: send FS load-as-command and execute response
; 
; Initialises a GS reader to skip past the filename and
; calculate the command context address, then sets up an FS
; command with function code &05 (FCCMND: load as command)
; using send_fs_examine. If a Tube co-processor is present
; (tube_flag != 0), transfers the response data to the Tube
; via tube_addr_claim. Otherwise jumps via the indirect
; pointer at (&0F09) to execute at the load address.
; ***************************************************************************************
.fsreply_4_notify_exec
    ldy #0                                                            ; 8de5: a0 00       ..             ; Y=0: start of text for GSINIT
    clc                                                               ; 8de7: 18          .              ; CLC before GSINIT call
    jsr gsinit                                                        ; 8de8: 20 c2 ff     ..            ; GSINIT/GSREAD: skip past the filename
; &8deb referenced 1 time by &8dee
.skip_gs_filename
    jsr gsread                                                        ; 8deb: 20 c5 ff     ..            ; Read next filename character
    bcc skip_gs_filename                                              ; 8dee: 90 fb       ..             ; C=0: more characters, keep reading
    jsr skip_spaces                                                   ; 8df0: 20 6c 83     l.            ; Skip spaces after filename
    clc                                                               ; 8df3: 18          .              ; Calculate context addr = text ptr + Y
    tya                                                               ; 8df4: 98          .              ; Y = offset past filename end
    adc os_text_ptr                                                   ; 8df5: 65 f2       e.             ; Add text pointer low byte
    sta fs_cmd_context                                                ; 8df7: 8d 0a 0e    ...            ; Store context address low byte
    lda os_text_ptr_hi                                                ; 8dfa: a5 f3       ..             ; Load text pointer high byte
    adc #0                                                            ; 8dfc: 69 00       i.             ; Add carry from low byte addition
    sta fs_context_hi                                                 ; 8dfe: 8d 0b 0e    ...            ; Store context address high byte
    ldx #&0e                                                          ; 8e01: a2 0e       ..             ; X=&0E: FS command buffer offset
    stx fs_block_offset                                               ; 8e03: 86 bc       ..             ; Store block offset for FS command
    lda #&10                                                          ; 8e05: a9 10       ..             ; A=&10: 16 bytes of command data
    sta fs_options                                                    ; 8e07: 85 bb       ..             ; Store options byte
    sta fs_work_16                                                    ; 8e09: 8d 16 0e    ...            ; Store to FS workspace
    ldx #&4a ; 'J'                                                    ; 8e0c: a2 4a       .J             ; X=&4A: TXCB size for load command
    ldy #5                                                            ; 8e0e: a0 05       ..             ; Y=5: FCCMND (load as command)
    jsr send_fs_examine                                               ; 8e10: 20 10 87     ..            ; Send FS examine/load command
    lda tube_flag                                                     ; 8e13: ad 67 0d    .g.            ; Check for Tube co-processor
    beq exec_local                                                    ; 8e16: f0 14       ..             ; No Tube: execute locally
    adc fs_load_upper                                                 ; 8e18: 6d 0b 0f    m..            ; Check load address upper bytes
    adc fs_addr_check                                                 ; 8e1b: 6d 0c 0f    m..            ; Continue address range check
    bcs exec_local                                                    ; 8e1e: b0 0c       ..             ; Carry set: not Tube space, exec locally
    jsr tube_claim_loop                                               ; 8e20: 20 01 8c     ..            ; Claim Tube transfer channel
    ldx #9                                                            ; 8e23: a2 09       ..             ; X=9: source offset in FS reply
    ldy #&0f                                                          ; 8e25: a0 0f       ..             ; Y=&0F: page &0F (FS command buffer)
    lda #4                                                            ; 8e27: a9 04       ..             ; A=4: Tube transfer type 4 (256-byte)
    jmp tube_addr_claim                                               ; 8e29: 4c 06 04    L..            ; Transfer data to Tube co-processor

; &8e2c referenced 2 times by &8e16, &8e1e
.exec_local
    rol a                                                             ; 8e2c: 2a          *              ; ROL: restore A (undo ADC carry)
.exec_at_load_addr
    jmp (fs_load_vector)                                              ; 8e2d: 6c 09 0f    l..            ; Execute at load address via indirect JMP

; ***************************************************************************************
; Set library handle
; 
; Stores Y into &0E04 (library directory handle in FS workspace).
; Falls through to JMP restore_args_return if Y is non-zero.
; 
; On Entry:
;     Y: library handle from FS reply
; ***************************************************************************************
.fsreply_5_set_lib
    sty fs_lib_handle                                                 ; 8e30: 8c 04 0e    ...            ; Save library handle from FS reply
    bcc jmp_restore_args                                              ; 8e33: 90 03       ..             ; SDISC path: skip CSD, jump to return
; ***************************************************************************************
; Set CSD handle
; 
; Stores Y into &0E03 (current selected directory handle).
; Falls through to JMP restore_args_return.
; 
; On Entry:
;     Y: CSD handle from FS reply
; ***************************************************************************************
.fsreply_3_set_csd
    sty fs_csd_handle                                                 ; 8e35: 8c 03 0e    ...            ; Store CSD handle from FS reply
; &8e38 referenced 2 times by &8e33, &8e49
.jmp_restore_args
    jmp restore_args_return                                           ; 8e38: 4c a1 89    L..            ; Restore A/X/Y and return to caller

; ***************************************************************************************
; Copy FS reply handles to workspace and execute boot command
; 
; SEC entry (LOGIN): copies 4 bytes from &0F05-&0F08 (FS reply) to
; &0E02-&0E05 (URD, CSD, LIB handles and boot option), then
; looks up the boot option in boot_option_offsets to get the
; OSCLI command string and executes it via JMP oscli.
; The carry flag distinguishes LOGIN (SEC) from SDISC (CLC) — both
; share the handle-copying code, but only LOGIN executes the boot
; command. This use of the carry flag to select behaviour between
; two callers avoids duplicating the handle-copy loop.
; ***************************************************************************************
.fsreply_1_copy_handles_boot
    sec                                                               ; 8e3b: 38          8              ; Set carry: LOGIN path (copy + boot)
; ***************************************************************************************
; Copy FS reply handles to workspace (no boot)
; 
; CLC entry (SDISC): copies handles only, then jumps to
; restore_args_return via jmp_restore_args. Called when the FS reply contains
; updated handle values but no boot action is needed.
; ***************************************************************************************
.fsreply_2_copy_handles
    ldx #3                                                            ; 8e3c: a2 03       ..             ; Copy 4 bytes: boot option + 3 handles
    bcc copy_handles_loop                                             ; 8e3e: 90 06       ..             ; SDISC: skip boot option, copy handles only
; &8e40 referenced 1 time by &8e47
.logon2
    lda fs_cmd_data,x                                                 ; 8e40: bd 05 0f    ...            ; Load from FS reply (&0F05+X)
    sta fs_urd_handle,x                                               ; 8e43: 9d 02 0e    ...            ; Store to handle workspace (&0E02+X)
; &8e46 referenced 1 time by &8e3e
.copy_handles_loop
    dex                                                               ; 8e46: ca          .              ; Next handle (descending)
    bpl logon2                                                        ; 8e47: 10 f7       ..             ; Loop while X >= 0
    bcc jmp_restore_args                                              ; 8e49: 90 ed       ..             ; SDISC: done, restore args and return
; ***************************************************************************************
; Execute boot command via OSCLI
; 
; Reached from fsreply_1_copy_handles_boot when carry is set (LOGIN
; path). Reads the boot option from fs_boot_option (&0E05),
; looks up the OSCLI command string offset from boot_option_offsets+1,
; and executes the boot command via JMP oscli with page &8D.
; ***************************************************************************************
.boot_cmd_execute
    ldy fs_boot_option                                                ; 8e4b: ac 05 0e    ...            ; Y = boot option from FS workspace
    ldx boot_string_offsets,y                                         ; 8e4e: be 56 8d    .V.            ; X = command string offset from table
    ldy #&8d                                                          ; 8e51: a0 8d       ..             ; Y = &8D (high byte of command address)
    jmp oscli                                                         ; 8e53: 4c f7 ff    L..            ; Execute boot command string via OSCLI

; ***************************************************************************************
; Load handle from &F0 and calculate workspace offset
; 
; Loads the file handle byte from &F0, then falls through to
; calc_handle_offset which converts handle * 12 to a workspace
; byte offset. Validates offset < &48.
; 
; On Exit:
;     A: handle*12 or 0 if invalid
;     Y: workspace offset or 0 if invalid
;     C: clear if valid, set if invalid
; ***************************************************************************************
; &8e56 referenced 2 times by &8e70, &8e80
.load_handle_calc_offset
    lda osword_pb_ptr                                                 ; 8e56: a5 f0       ..             ; Load handle from &F0
; ***************************************************************************************
; Calculate handle workspace offset
; 
; Converts a file handle number (in A) to a byte offset (in Y)
; into the NFS handle workspace. The calculation is A*12:
;   ASL A (A*2), ASL A (A*4), PHA, ASL A (A*8),
;   ADC stack (A*8 + A*4 = A*12).
; Validates that the offset is < &48 (max 6 handles × 12 bytes
; per handle entry = 72 bytes). If invalid (>= &48), returns
; with C set and Y=0, A=0 as an error indicator.
; 
; On Entry:
;     A: file handle number
; 
; On Exit:
;     A: handle*12 or 0 if invalid
;     Y: workspace offset or 0 if invalid
;     C: clear if valid, set if invalid
; ***************************************************************************************
; &8e58 referenced 3 times by &82f7, &8f90, &8fa9
.calc_handle_offset
    asl a                                                             ; 8e58: 0a          .              ; A = handle * 2
    asl a                                                             ; 8e59: 0a          .              ; A = handle * 4
    pha                                                               ; 8e5a: 48          H              ; Push handle*4 onto stack
    asl a                                                             ; 8e5b: 0a          .              ; A = handle * 8
    tsx                                                               ; 8e5c: ba          .              ; X = stack pointer
    adc error_text,x                                                  ; 8e5d: 7d 01 01    }..            ; A = handle*8 + handle*4 = handle*12
    tay                                                               ; 8e60: a8          .              ; Y = offset into handle workspace
    pla                                                               ; 8e61: 68          h              ; Clean up stack (discard handle*4)
    cmp #&48 ; 'H'                                                    ; 8e62: c9 48       .H             ; Offset >= &48? (6 handles max)
    bcc return_6                                                      ; 8e64: 90 03       ..             ; Valid: return with C clear
    ldy #0                                                            ; 8e66: a0 00       ..             ; Invalid: Y = 0
    tya                                                               ; 8e68: 98          .              ; A = 0, C set (error); A=&00
; &8e69 referenced 1 time by &8e64
.return_6
.return_calc_handle
    rts                                                               ; 8e69: 60          `              ; Return after calculation

; *NET1: read file handle from received packet.
; Reads a byte from offset &6F of the RX buffer (net_rx_ptr)
; and falls through to net_2_read_handle_entry's common path.
.net_1_read_handle
    ldy #&6f ; 'o'                                                    ; 8e6a: a0 6f       .o             ; Y=&6F: RX buffer handle offset
    lda (net_rx_ptr),y                                                ; 8e6c: b1 9c       ..             ; Read handle from RX packet
    bcc store_handle_return                                           ; 8e6e: 90 0d       ..             ; Valid handle: store and return
; ***************************************************************************************
; *NET2: read handle entry from workspace
; 
; Looks up the handle in &F0 via calc_handle_offset. If the
; workspace slot contains &3F ('?', meaning unused/closed),
; returns 0. Otherwise returns the stored handle value.
; Clears rom_svc_num on exit.
; 
; On Exit:
;     A: handle value (0 if closed/invalid)
; ***************************************************************************************
.net_2_read_handle_entry
    jsr load_handle_calc_offset                                       ; 8e70: 20 56 8e     V.            ; Look up handle &F0 in workspace
    bcs rxpol2                                                        ; 8e73: b0 06       ..             ; Invalid handle: return 0
    lda (nfs_workspace),y                                             ; 8e75: b1 9e       ..             ; Load stored handle value
    cmp #&3f ; '?'                                                    ; 8e77: c9 3f       .?             ; &3F = unused/closed slot marker
    bne store_handle_return                                           ; 8e79: d0 02       ..             ; Slot in use: return actual value
; &8e7b referenced 2 times by &8e73, &8e83
.rxpol2
    lda #0                                                            ; 8e7b: a9 00       ..             ; Return 0 for closed/invalid handle
; &8e7d referenced 2 times by &8e6e, &8e79
.store_handle_return
    sta osword_pb_ptr                                                 ; 8e7d: 85 f0       ..             ; Store result back to &F0
    rts                                                               ; 8e7f: 60          `              ; Return

; ***************************************************************************************
; *NET3: close handle (mark as unused)
; 
; Looks up the handle in &F0 via calc_handle_offset. Writes
; &3F ('?') to mark the handle slot as closed in the NFS
; workspace. Returns via RTS (earlier versions preserved the
; carry flag across the write using ROL/ROR on rx_flags, but
; 3.60 simplified this).
; 
; On Exit:
;     A: &3F (close marker) or 0 if invalid
; ***************************************************************************************
.net_3_close_handle
    jsr load_handle_calc_offset                                       ; 8e80: 20 56 8e     V.            ; Look up handle &F0 in workspace
    bcs rxpol2                                                        ; 8e83: b0 f6       ..             ; Invalid handle: return 0
    lda #&3f ; '?'                                                    ; 8e85: a9 3f       .?             ; &3F = '?' marks slot as unused
    sta (nfs_workspace),y                                             ; 8e87: 91 9e       ..             ; Write close marker to workspace slot
    rts                                                               ; 8e89: 60          `              ; Return

; ***************************************************************************************
; Filing system OSWORD entry
; 
; Subtracts &0F from the command code in &EF, giving a 0-4 index
; for OSWORD calls &0F-&13 (15-19). Falls through to the range
; check and dispatch at osword_12_handler (&8E90).
; ***************************************************************************************
.svc_8_osword
    lda osbyte_a_copy                                                 ; 8e8a: a5 ef       ..             ; Command code from &EF
    sbc #&0f                                                          ; 8e8c: e9 0f       ..             ; Subtract &0F: OSWORD &0F-&13 become indices 0-4
    bmi return_7                                                      ; 8e8e: 30 2a       0*             ; Outside our OSWORD range, exit
; ***************************************************************************************
; OSWORD range check, dispatch, and register restore
; 
; Reached by fall-through from svc_8_osword with A = OSWORD
; number minus &0F. Rejects indices >= 5 (only OSWORDs &0F-&13
; are handled). Dispatches to the appropriate handler via
; fs_osword_dispatch, then on return copies 3 bytes from
; (net_rx_ptr)+0..2 back to &AA-&AC (restoring the param block
; pointer that was saved by fs_osword_dispatch before dispatch).
; 
; The actual OSWORD &12 sub-function dispatch (FS/printer server
; station/network, protection mask, context handles, local
; station number read-back etc.) lives in osword_12_dispatch.
; ***************************************************************************************
.osword_12_handler
    cmp #5                                                            ; 8e90: c9 05       ..             ; Only OSWORDs &0F-&13 (index 0-4)
    bcs return_7                                                      ; 8e92: b0 26       .&             ; Index >= 5: not ours, return
    jsr fs_osword_dispatch                                            ; 8e94: 20 a2 8e     ..            ; Dispatch via PHA/PHA/RTS table
    ldy #2                                                            ; 8e97: a0 02       ..             ; Y=2: restore 3 bytes (&AA-&AC)
; &8e99 referenced 1 time by &8e9f
.copy_param_ptr
    lda (net_rx_ptr),y                                                ; 8e99: b1 9c       ..             ; Load saved param block byte
    sta osword_flag,y                                                 ; 8e9b: 99 aa 00    ...            ; Restore to &AA-&AC
    dey                                                               ; 8e9e: 88          .              ; Next byte (descending)
    bpl copy_param_ptr                                                ; 8e9f: 10 f8       ..             ; Loop for all 3 bytes
    rts                                                               ; 8ea1: 60          `              ; Return to service handler

; ***************************************************************************************
; PHA/PHA/RTS dispatch for filing system OSWORDs
; 
; Saves the param block pointer (&AA-&AC) to (net_rx_ptr) and
; reads the sub-function code from (&F0)+1, then dispatches via
; the 5-entry table at &8EB8 (low) / &8EBD (high) using
; PHA/PHA/RTS. The RTS at the end of the dispatched handler
; returns here, after which the caller restores &AA-&AC.
; ***************************************************************************************
; &8ea2 referenced 1 time by &8e94
.fs_osword_dispatch
    tax                                                               ; 8ea2: aa          .              ; X = sub-function code for table lookup
    lda fs_osword_tbl_hi,x                                            ; 8ea3: bd c0 8e    ...            ; Load handler address high byte from table
    pha                                                               ; 8ea6: 48          H              ; Push high byte for RTS dispatch
    lda osword_handler_lo,x                                           ; 8ea7: bd bb 8e    ...            ; Load handler address low byte from table
.fs_osword_tbl_lo
    pha                                                               ; 8eaa: 48          H              ; Dispatch table: low bytes for OSWORD &0F-&13 handlers
    ldy #2                                                            ; 8eab: a0 02       ..             ; Y=2: save 3 bytes (&AA-&AC)
; &8ead referenced 1 time by &8eb3
.save1
    lda osword_flag,y                                                 ; 8ead: b9 aa 00    ...            ; Load param block pointer byte
    sta (net_rx_ptr),y                                                ; 8eb0: 91 9c       ..             ; Save to NFS workspace via (net_rx_ptr)
    dey                                                               ; 8eb2: 88          .              ; Next byte (descending)
    bpl save1                                                         ; 8eb3: 10 f8       ..             ; Loop for all 3 bytes
    iny                                                               ; 8eb5: c8          .              ; Y=0 after BPL exit; INY makes Y=1
    lda (osword_pb_ptr),y                                             ; 8eb6: b1 f0       ..             ; Read sub-function code from (&F0)+1
    sty svc_state                                                     ; 8eb8: 84 a9       ..             ; Store Y=1 to &A9
; &8eba referenced 2 times by &8e8e, &8e92
.return_7
    rts                                                               ; 8eba: 60          `              ; RTS dispatches to pushed handler address

; &8ebb referenced 1 time by &8ea7
.osword_handler_lo
    equb <(osword_0f_handler-1)                                       ; 8ebb: c4          .              ; lo(osword_0f_handler-1): OSWORD &0F
    equb <(osword_10_handler-1)                                       ; 8ebc: 7e          ~              ; lo(osword_10_handler-1): OSWORD &10
    equb <(osword_11_handler-1)                                       ; 8ebd: de          .              ; lo(osword_11_handler-1): OSWORD &11
    equb <(osword_12_dispatch-1)                                      ; 8ebe: 03          .              ; lo(osword_12_dispatch-1): OSWORD &12
    equb <(econet_tx_rx-1)                                            ; 8ebf: f2          .              ; lo(econet_tx_rx-1): OSWORD &13
; &8ec0 referenced 1 time by &8ea3
.fs_osword_tbl_hi
    equb >(osword_0f_handler-1)                                       ; 8ec0: 8e          .              ; Dispatch table: high bytes for OSWORD &0F-&13 handlers
    equb >(osword_10_handler-1)                                       ; 8ec1: 8f          .              ; hi(osword_10_handler-1): OSWORD &10
    equb >(osword_11_handler-1)                                       ; 8ec2: 8e          .              ; hi(osword_11_handler-1): OSWORD &11
    equb >(osword_12_dispatch-1)                                      ; 8ec3: 8f          .              ; hi(osword_12_dispatch-1): OSWORD &12
    equb >(econet_tx_rx-1)                                            ; 8ec4: 8f          .              ; hi(econet_tx_rx-1): OSWORD &13

; ***************************************************************************************
; OSWORD &0F handler: initiate transmit (CALLTX)
; 
; Checks the TX semaphore (TXCLR at &0D62) via ASL -- if carry is
; clear, a TX is already in progress and the call returns an error,
; preventing user code from corrupting a system transmit. Otherwise
; copies 16 bytes from the caller's OSWORD parameter block into the
; user TX control block (UTXCB) in static workspace. The TXCB
; pointer is copied to LTXCBP only after the semaphore is claimed,
; ensuring the low-level transmit code (BRIANX) sees a consistent
; pointer -- if copied before claiming, another transmitter could
; modify TXCBP between the copy and the claim.
; 
; On Entry:
;     X: parameter block address low byte
;     Y: parameter block address high byte
; 
; On Exit:
;     A: corrupted
;     X: corrupted
;     Y: &FF
; ***************************************************************************************
.osword_0f_handler
    asl tx_clear_flag                                                 ; 8ec5: 0e 62 0d    .b.            ; ASL TXCLR: C=1 means TX free to claim
    tya                                                               ; 8ec8: 98          .              ; Save Y (param block high) for later
    bcc readry                                                        ; 8ec9: 90 34       .4             ; C=0: TX busy, return error status
    lda net_rx_ptr_hi                                                 ; 8ecb: a5 9d       ..             ; User TX CB in workspace page (high byte)
    sta ws_ptr_hi                                                     ; 8ecd: 85 ac       ..             ; Set param block high byte
    sta nmi_tx_block_hi                                               ; 8ecf: 85 a1       ..             ; Set LTXCBP high byte for low-level TX
    lda #&6f ; 'o'                                                    ; 8ed1: a9 6f       .o             ; &6F: offset into workspace for user TXCB
    sta ws_ptr_lo                                                     ; 8ed3: 85 ab       ..             ; Set param block low byte
    sta nmi_tx_block                                                  ; 8ed5: 85 a0       ..             ; Set LTXCBP low byte for low-level TX
    ldx #&0f                                                          ; 8ed7: a2 0f       ..             ; X=15: copy 16 bytes (OSWORD param block)
    jsr copy_param_workspace                                          ; 8ed9: 20 1f 8f     ..            ; Copy param block to user TX control block
    jmp start_adlc_tx                                                 ; 8edc: 4c 50 96    LP.            ; Start user transmit via BRIANX

; ***************************************************************************************
; OSWORD &11 handler: read JSR arguments (READRA)
; 
; Copies the JSR (remote procedure call) argument buffer from the
; static workspace page back to the caller's OSWORD parameter block.
; Reads the buffer size from workspace offset JSRSIZ, then copies
; that many bytes. After the copy, clears the old LSTAT byte via
; CLRJSR to reset the protection status. Also provides READRB as
; a sub-entry (&8EE7) to return just the buffer size and args size
; without copying the data.
; ***************************************************************************************
.osword_11_handler
    lda net_rx_ptr_hi                                                 ; 8edf: a5 9d       ..             ; Set source high byte from workspace page
    sta ws_ptr_hi                                                     ; 8ee1: 85 ac       ..             ; Store as copy source high byte in &AC
    ldy #&7f                                                          ; 8ee3: a0 7f       ..             ; JSRSIZ at workspace offset &7F
    lda (net_rx_ptr),y                                                ; 8ee5: b1 9c       ..             ; Load buffer size from workspace
    iny                                                               ; 8ee7: c8          .              ; Y=&80: start of JSR argument data; Y=&80
    sty ws_ptr_lo                                                     ; 8ee8: 84 ab       ..             ; Store &80 as copy source low byte
    tax                                                               ; 8eea: aa          .              ; X = buffer size (loop counter)
    dex                                                               ; 8eeb: ca          .              ; X = size-1 (0-based count for copy)
    ldy #0                                                            ; 8eec: a0 00       ..             ; Y=0: start of destination param block
    jsr copy_param_workspace                                          ; 8eee: 20 1f 8f     ..            ; Copy X+1 bytes from workspace to param
    jmp clear_jsr_protection                                          ; 8ef1: 4c f3 92    L..            ; Clear JSR protection status (CLRJSR)

; &8ef4 referenced 1 time by &8f4f
.read_args_size
    ldy #&7f                                                          ; 8ef4: a0 7f       ..             ; Y=&7F: JSRSIZ offset (READRB entry)
    lda (net_rx_ptr),y                                                ; 8ef6: b1 9c       ..             ; Load buffer size from workspace
    ldy #1                                                            ; 8ef8: a0 01       ..             ; Y=1: param block offset for size byte
    sta (osword_pb_ptr),y                                             ; 8efa: 91 f0       ..             ; Store buffer size to (&F0)+1
    iny                                                               ; 8efc: c8          .              ; Y=2: param block offset for args size; Y=&02
    lda #&80                                                          ; 8efd: a9 80       ..             ; A=&80: argument data starts at offset &80
; &8eff referenced 1 time by &8ec9
.readry
    sta (osword_pb_ptr),y                                             ; 8eff: 91 f0       ..             ; Store args start offset to (&F0)+2
    rts                                                               ; 8f01: 60          `              ; Return

; &8f02 referenced 1 time by &8f16
.osword_12_offsets
    equb &ff, 1                                                       ; 8f02: ff 01       ..             ; OSWORD &12 workspace offset table

; ***************************************************************************************
; OSWORD &12 handler: dispatch sub-functions 0-9
; 
; Range-checks the sub-function code from the param block and
; dispatches:
;   0: read FS server station/network (from &0E00/&0E01)
;   1: set  FS server station/network
;   2: read printer server station/network (from dynamic ws)
;   3: set  printer server station/network
;   4: read JSR protection mask (LSTAT at &0D63)
;   5: set  JSR protection mask
;   6: read context handles (URD/CSD/LIB)
;   7: set  context handles
;   8: read cached local station number (from (net_rx_ptr)+&14,
;      populated at init by reading the &FE18 station-ID latch)
;   9: read JSR argument buffer size
; Sub-functions 0-3 select the appropriate workspace page
; (static &0D or dynamic) and offset, then fall through to the
; bidirectional param block copy loop. Sub-functions >= 6 are
; re-dispatched via rsl1; values >= 10 return the last FS error.
; Note: there is no sub-function that *sets* the local station
; number -- on the Model B that is hardwired via the 8 station
; ID links read from &FE18.
; ***************************************************************************************
.osword_12_dispatch
    cmp #6                                                            ; 8f04: c9 06       ..             ; OSWORD &12: range check sub-function
    bcs rsl1                                                          ; 8f06: b0 41       .A             ; Sub-function >= 6: not supported
    cmp #4                                                            ; 8f08: c9 04       ..             ; Check for sub-functions 4-5
    bcs rssl1                                                         ; 8f0a: b0 22       ."             ; Sub-function 4 or 5: read/set protection
    lsr a                                                             ; 8f0c: 4a          J              ; LSR: 0->0, 1->0, 2->1, 3->1
    ldx #&0d                                                          ; 8f0d: a2 0d       ..             ; X=&0D: default to static workspace page
    tay                                                               ; 8f0f: a8          .              ; Transfer LSR result to Y for indexing
    beq set_workspace_page                                            ; 8f10: f0 02       ..             ; Y=0 (sub 0-1): use page &0D
    ldx nfs_workspace_hi                                              ; 8f12: a6 9f       ..             ; Y=1 (sub 2-3): use dynamic workspace
; &8f14 referenced 1 time by &8f10
.set_workspace_page
    stx ws_ptr_hi                                                     ; 8f14: 86 ac       ..             ; Store workspace page in &AC (hi byte)
    lda osword_12_offsets,y                                           ; 8f16: b9 02 8f    ...            ; Load offset: &FF (sub 0-1) or &01 (sub 2-3)
    sta ws_ptr_lo                                                     ; 8f19: 85 ab       ..             ; Store offset in &AB (lo byte)
    ldx #1                                                            ; 8f1b: a2 01       ..             ; X=1: copy 2 bytes
    ldy #1                                                            ; 8f1d: a0 01       ..             ; Y=1: start at param block offset 1
; ***************************************************************************************
; Bidirectional copy loop between param block and workspace
; 
; If C=1, copies from OSWORD param block (&F0),Y to workspace
; (&AB),Y. In either case, loads from workspace and stores to
; param block. Loops for X+1 bytes. Used by OSWORD &0F, &10,
; &11, and &12 handlers.
; 
; On Entry:
;     C: 1=copy param to workspace first, 0=workspace to param only
;     X: byte count minus 1
;     Y: starting offset
; 
; On Exit:
;     A: last byte copied
;     X: &FF
;     Y: start + count + 1
; ***************************************************************************************
; &8f1f referenced 4 times by &8ed9, &8eee, &8f2b, &8fc0
.copy_param_workspace
    bcc skip_param_write                                              ; 8f1f: 90 04       ..             ; C=0: skip param-to-workspace copy
    lda (osword_pb_ptr),y                                             ; 8f21: b1 f0       ..             ; C=1: copy from param to workspace
    sta (ws_ptr_lo),y                                                 ; 8f23: 91 ab       ..             ; Store param byte to workspace
; &8f25 referenced 1 time by &8f1f
.skip_param_write
    lda (ws_ptr_lo),y                                                 ; 8f25: b1 ab       ..             ; Load byte from workspace
; ***************************************************************************************
; Bidirectional block copy between OSWORD param block and workspace.
; 
; C=1: copy X+1 bytes from (&F0),Y to (&AB),Y (param to workspace)
; C=0: copy X+1 bytes from (&AB),Y to (&F0),Y (workspace to param)
; 
; On Entry:
;     C: 1=param to workspace, 0=workspace to param
;     X: byte count minus 1
;     Y: starting offset
; 
; On Exit:
;     A: last byte copied
;     X: &FF
;     Y: start + count + 1
; ***************************************************************************************
.copy_param_block
    sta (osword_pb_ptr),y                                             ; 8f27: 91 f0       ..             ; Store to param block (no-op if C=1)
    iny                                                               ; 8f29: c8          .              ; Advance to next byte
    dex                                                               ; 8f2a: ca          .              ; Decrement remaining count
    bpl copy_param_workspace                                          ; 8f2b: 10 f2       ..             ; Loop while bytes remain
.logon3
.return_copy_param
    rts                                                               ; 8f2d: 60          `              ; Return

; &8f2e referenced 1 time by &8f0a
.rssl1
    lsr a                                                             ; 8f2e: 4a          J              ; LSR A: test bit 0 of sub-function
    iny                                                               ; 8f2f: c8          .              ; Y=1: offset for protection byte
    lda (osword_pb_ptr),y                                             ; 8f30: b1 f0       ..             ; Load protection byte from param block
    bcs rssl2                                                         ; 8f32: b0 05       ..             ; C=1 (odd sub): set protection
    lda prot_status                                                   ; 8f34: ad 63 0d    .c.            ; C=0 (even sub): read current status
    sta (osword_pb_ptr),y                                             ; 8f37: 91 f0       ..             ; Return current value to param block
; &8f39 referenced 1 time by &8f32
.rssl2
    sta prot_status                                                   ; 8f39: 8d 63 0d    .c.            ; Update protection status
    sta saved_jsr_mask                                                ; 8f3c: 8d 65 0d    .e.            ; Also save as JSR mask backup
    rts                                                               ; 8f3f: 60          `              ; Return

; &8f40 referenced 1 time by &8f4b
.read_local_station_id
    ldy #&14                                                          ; 8f40: a0 14       ..             ; Y=&14: RX buf offset of cached station ID
    lda (net_rx_ptr),y                                                ; 8f42: b1 9c       ..             ; Read cached local station number
    ldy #1                                                            ; 8f44: a0 01       ..             ; Y=1: param block byte 1
    sta (osword_pb_ptr),y                                             ; 8f46: 91 f0       ..             ; Return handle to caller's param block
    rts                                                               ; 8f48: 60          `              ; Return

; &8f49 referenced 1 time by &8f06
.rsl1
    cmp #8                                                            ; 8f49: c9 08       ..             ; Sub-function 8: read local station number
    beq read_local_station_id                                         ; 8f4b: f0 f3       ..             ; Match: read cached station ID from RX buffer
    cmp #9                                                            ; 8f4d: c9 09       ..             ; Sub-function 9: read args size
    beq read_args_size                                                ; 8f4f: f0 a3       ..             ; Match: read ARGS buffer info
    bpl return_last_error                                             ; 8f51: 10 19       ..             ; Sub >= 10 (bit 7 clear): read error
    ldy #3                                                            ; 8f53: a0 03       ..             ; Y=3: start from handle 3 (descending)
    lsr a                                                             ; 8f55: 4a          J              ; LSR: test read/write bit
    bcc readc1                                                        ; 8f56: 90 1b       ..             ; C=0: read handles from workspace
    sty ws_page                                                       ; 8f58: 84 a8       ..             ; Init loop counter at Y=3
; &8f5a referenced 1 time by &8f69
.copy_handles_to_ws
    ldy ws_page                                                       ; 8f5a: a4 a8       ..             ; Reload loop counter
    lda (osword_pb_ptr),y                                             ; 8f5c: b1 f0       ..             ; Read handle from caller's param block
    jsr handle_to_mask_a                                              ; 8f5e: 20 88 86     ..            ; Convert handle number to bitmask
    tya                                                               ; 8f61: 98          .              ; TYA: get bitmask result
    ldy ws_page                                                       ; 8f62: a4 a8       ..             ; Reload loop counter
    sta fs_server_net,y                                               ; 8f64: 99 01 0e    ...            ; Store bitmask to FS server table
    dec ws_page                                                       ; 8f67: c6 a8       ..             ; Next handle (descending)
    bne copy_handles_to_ws                                            ; 8f69: d0 ef       ..             ; Loop for handles 3,2,1
    rts                                                               ; 8f6b: 60          `              ; Return

; &8f6c referenced 1 time by &8f51
.return_last_error
    iny                                                               ; 8f6c: c8          .              ; Y=1 (post-INY): param block byte 1
    lda fs_last_error                                                 ; 8f6d: ad 09 0e    ...            ; Read last FS error code
    sta (osword_pb_ptr),y                                             ; 8f70: 91 f0       ..             ; Return error to caller's param block
    rts                                                               ; 8f72: 60          `              ; Return

; &8f73 referenced 2 times by &8f56, &8f7c
.readc1
    lda fs_server_net,y                                               ; 8f73: b9 01 0e    ...            ; A=single-bit bitmask
    jsr mask_to_handle                                                ; 8f76: 20 a5 86     ..            ; Convert bitmask to handle number (FS2A)
    sta (osword_pb_ptr),y                                             ; 8f79: 91 f0       ..             ; A=handle number (&20-&27); Y=preserved
    dey                                                               ; 8f7b: 88          .              ; Next handle (descending)
    bne readc1                                                        ; 8f7c: d0 f5       ..             ; Loop for handles 3,2,1
    rts                                                               ; 8f7e: 60          `              ; Return

; ***************************************************************************************
; OSWORD &10 handler: open/read RX control block (OPENRX)
; 
; If the first byte of the caller's parameter block is zero, scans
; for a free RXCB (flag byte = &3F = deleted) starting from RXCB #3
; (RXCBs 0-2 are dedicated: printer, remote, FS). Returns the RXCB
; number in the first byte, or zero if none free. If the first byte
; is non-zero, reads the specified RXCB's data back into the caller's
; parameter block (12 bytes) and then deletes the RXCB by setting
; its flag byte to &3F -- a consume-once semantic so user code reads
; received data and frees the CB in a single atomic operation,
; preventing double-reads. The low-level user RX flag (LFLAG) is
; temporarily disabled via ROR/ROL during the operation to prevent
; the interrupt-driven receive code from modifying a CB that is
; being read or opened.
; 
; On Entry:
;     X: parameter block address low byte
;     Y: parameter block address high byte
; 
; On Exit:
;     A: corrupted
;     X: corrupted
;     Y: &FF
; ***************************************************************************************
.osword_10_handler
    ldx nfs_workspace_hi                                              ; 8f7f: a6 9f       ..             ; Workspace page high byte
    stx ws_ptr_hi                                                     ; 8f81: 86 ac       ..             ; Set up pointer high byte in &AC
    sty ws_ptr_lo                                                     ; 8f83: 84 ab       ..             ; Save param block high byte in &AB
    ror rx_flags                                                      ; 8f85: 6e 64 0d    nd.            ; Disable user RX during CB operation
    lda (osword_pb_ptr),y                                             ; 8f88: b1 f0       ..             ; Read first byte of param block
    sta osword_flag                                                   ; 8f8a: 85 aa       ..             ; Save: 0=open new, non-zero=read RXCB
    bne read_rxcb                                                     ; 8f8c: d0 1b       ..             ; Non-zero: read specified RXCB
    lda #3                                                            ; 8f8e: a9 03       ..             ; Start scan from RXCB #3 (0-2 reserved)
; &8f90 referenced 1 time by &8fa2
.scan0
    jsr calc_handle_offset                                            ; 8f90: 20 58 8e     X.            ; Convert RXCB number to workspace offset
    bcs openl4                                                        ; 8f93: b0 3d       .=             ; Invalid RXCB: return zero
    lsr a                                                             ; 8f95: 4a          J              ; LSR twice: byte offset / 4
    lsr a                                                             ; 8f96: 4a          J              ; Yields RXCB number from offset
    tax                                                               ; 8f97: aa          .              ; X = RXCB number for iteration
    lda (ws_ptr_lo),y                                                 ; 8f98: b1 ab       ..             ; Read flag byte from RXCB workspace
    beq openl4                                                        ; 8f9a: f0 36       .6             ; Zero = end of CB list
    cmp #&3f ; '?'                                                    ; 8f9c: c9 3f       .?             ; &3F = deleted slot, free for reuse
    beq scan1                                                         ; 8f9e: f0 04       ..             ; Found free slot
    inx                                                               ; 8fa0: e8          .              ; Try next RXCB
    txa                                                               ; 8fa1: 8a          .              ; A = next RXCB number
    bne scan0                                                         ; 8fa2: d0 ec       ..             ; Continue scan (always branches)
; &8fa4 referenced 1 time by &8f9e
.scan1
    txa                                                               ; 8fa4: 8a          .              ; A = free RXCB number
    ldx #0                                                            ; 8fa5: a2 00       ..             ; X=0 for indexed indirect store
    sta (osword_pb_ptr,x)                                             ; 8fa7: 81 f0       ..             ; Return RXCB number to caller's byte 0
; &8fa9 referenced 1 time by &8f8c
.read_rxcb
    jsr calc_handle_offset                                            ; 8fa9: 20 58 8e     X.            ; Convert RXCB number to workspace offset
    bcs openl4                                                        ; 8fac: b0 24       .$             ; Invalid: write zero to param block
    dey                                                               ; 8fae: 88          .              ; Y = offset-1: points to flag byte
    sty ws_ptr_lo                                                     ; 8faf: 84 ab       ..             ; Set &AB = workspace ptr low byte
    lda #&c0                                                          ; 8fb1: a9 c0       ..             ; &C0: test mask for flag byte
    ldy #1                                                            ; 8fb3: a0 01       ..             ; Y=1: flag byte offset in RXCB
    ldx #&0b                                                          ; 8fb5: a2 0b       ..             ; Enable interrupts before transmit
    cpy osword_flag                                                   ; 8fb7: c4 aa       ..             ; Compare Y(1) with saved byte (open/read)
    adc (ws_ptr_lo),y                                                 ; 8fb9: 71 ab       q.             ; ADC flag: test if slot is in use
    beq openl6                                                        ; 8fbb: f0 03       ..             ; Dest station = &FFFF (accept reply from any station)
    bmi openl7                                                        ; 8fbd: 30 0e       0.             ; Negative: slot has received data
; &8fbf referenced 1 time by &8fcf
.copy_rxcb_to_param
    clc                                                               ; 8fbf: 18          .              ; C=0: workspace-to-param direction
; &8fc0 referenced 1 time by &8fbb
.openl6
    jsr copy_param_workspace                                          ; 8fc0: 20 1f 8f     ..            ; Copy RXCB data to param block
    bcs reenable_rx                                                   ; 8fc3: b0 0f       ..             ; Done: skip deletion on error
    lda #&3f ; '?'                                                    ; 8fc5: a9 3f       .?             ; Mark CB as consumed (consume-once)
    ldy #1                                                            ; 8fc7: a0 01       ..             ; Y=1: flag byte offset
    sta (ws_ptr_lo),y                                                 ; 8fc9: 91 ab       ..             ; Write &3F to mark slot deleted
    bne reenable_rx                                                   ; 8fcb: d0 07       ..             ; Branch to exit (always taken); ALWAYS branch

; &8fcd referenced 1 time by &8fbd
.openl7
    adc #1                                                            ; 8fcd: 69 01       i.             ; Advance through multi-byte field
    bne copy_rxcb_to_param                                            ; 8fcf: d0 ee       ..             ; Loop until all bytes processed
    dey                                                               ; 8fd1: 88          .              ; Y=-1 → Y=0 after STA below
; &8fd2 referenced 3 times by &8f93, &8f9a, &8fac
.openl4
    sta (osword_pb_ptr),y                                             ; 8fd2: 91 f0       ..             ; Return zero (no free RXCB found)
; &8fd4 referenced 2 times by &8fc3, &8fcb
.reenable_rx
    rol rx_flags                                                      ; 8fd4: 2e 64 0d    .d.            ; Re-enable user RX
    rts                                                               ; 8fd7: 60          `              ; Return

; ***************************************************************************************
; Set up RX buffer pointers in NFS workspace
; 
; Calculates the start address of the RX data area (&F0+1) and stores
; it at workspace offset &1C. Also reads the data length from (&F0)+1
; and adds it to &F0 to compute the end address at offset &20.
; 
; On Entry:
;     C: clear for ADC
; ***************************************************************************************
; &8fd8 referenced 1 time by &900b
.setup_rx_buffer_ptrs
    ldy #&1c                                                          ; 8fd8: a0 1c       ..             ; Y=&1C: workspace offset for RX data start
    lda osword_pb_ptr                                                 ; 8fda: a5 f0       ..             ; A = base address low byte
    adc #1                                                            ; 8fdc: 69 01       i.             ; A = base + 1 (skip length byte)
    jsr store_16bit_at_y                                              ; 8fde: 20 e9 8f     ..            ; Receive data blocks until command byte = &00 or &0D
    ldy #1                                                            ; 8fe1: a0 01       ..             ; Read data length from (&F0)+1
    lda (osword_pb_ptr),y                                             ; 8fe3: b1 f0       ..             ; A = data length byte
    ldy #&20 ; ' '                                                    ; 8fe5: a0 20       .              ; Workspace offset &20 = RX data end
    adc osword_pb_ptr                                                 ; 8fe7: 65 f0       e.             ; A = base + length = end address low
; &8fe9 referenced 1 time by &8fde
.store_16bit_at_y
    sta (nfs_workspace),y                                             ; 8fe9: 91 9e       ..             ; Store low byte of 16-bit address
    iny                                                               ; 8feb: c8          .              ; Advance to high byte offset
    lda osword_pb_ptr_hi                                              ; 8fec: a5 f1       ..             ; A = high byte of base address
    adc #0                                                            ; 8fee: 69 00       i.             ; Add carry for 16-bit addition
    sta (nfs_workspace),y                                             ; 8ff0: 91 9e       ..             ; Store high byte
    rts                                                               ; 8ff2: 60          `              ; Return

; ***************************************************************************************
; Econet transmit/receive handler
; 
; A=0: Initialise TX control block from ROM template at &8383
;      (init_tx_ctrl_block+Y, zero entries substituted from NMI
;      workspace &0DE6), transmit it, set up RX control block,
;      and receive reply.
; A>=1: Handle transmit result (branch to cleanup at &903E).
; 
; On Entry:
;     A: 0=set up and transmit, >=1=handle TX result
; ***************************************************************************************
.econet_tx_rx
    cmp #1                                                            ; 8ff3: c9 01       ..             ; A=0: set up and transmit; A>=1: handle result
    bcs handle_tx_result                                              ; 8ff5: b0 4a       .J             ; A >= 1: handle TX result
    ldy #&23 ; '#'                                                    ; 8ff7: a0 23       .#             ; Y=&23: start of template (descending)
; &8ff9 referenced 1 time by &9006
.dofs01
    lda init_tx_ctrl_block,y                                          ; 8ff9: b9 83 83    ...            ; Load ROM template byte
    bne store_txcb_byte                                               ; 8ffc: d0 03       ..             ; Non-zero = use ROM template byte as-is
    lda nmi_sub_table,y                                               ; 8ffe: b9 e6 0d    ...            ; Zero = substitute from NMI workspace
; &9001 referenced 1 time by &8ffc
.store_txcb_byte
    sta (nfs_workspace),y                                             ; 9001: 91 9e       ..             ; Store to dynamic workspace
    dey                                                               ; 9003: 88          .              ; Descend through template
    cpy #&17                                                          ; 9004: c0 17       ..             ; Stop at offset &17
    bne dofs01                                                        ; 9006: d0 f1       ..             ; Loop until all bytes copied
    iny                                                               ; 9008: c8          .              ; Y=&18: TX block starts here
    sty net_tx_ptr                                                    ; 9009: 84 9a       ..             ; Point net_tx_ptr at workspace+&18
    jsr setup_rx_buffer_ptrs                                          ; 900b: 20 d8 8f     ..            ; Set up RX buffer start/end pointers
    ldy #2                                                            ; 900e: a0 02       ..             ; Y=2: port byte offset in RXCB
    lda #&90                                                          ; 9010: a9 90       ..             ; A=&90: FS reply port
    sta escapable                                                     ; 9012: 85 97       ..             ; Mark as escapable operation
    sta (osword_pb_ptr),y                                             ; 9014: 91 f0       ..             ; Store port &90 at (&F0)+2
    iny                                                               ; 9016: c8          .              ; Y=&03
    iny                                                               ; 9017: c8          .              ; Y=&04: advance to station address; Y=&04
; &9018 referenced 1 time by &9020
.copy_fs_addr
    lda fs_context_base,y                                             ; 9018: b9 fe 0d    ...            ; Copy FS station addr from workspace
    sta (osword_pb_ptr),y                                             ; 901b: 91 f0       ..             ; Store to RX param block
    iny                                                               ; 901d: c8          .              ; Next byte
    cpy #7                                                            ; 901e: c0 07       ..             ; Done 3 bytes (Y=4,5,6)?
    bne copy_fs_addr                                                  ; 9020: d0 f6       ..             ; No: continue copying
    lda nfs_workspace_hi                                              ; 9022: a5 9f       ..             ; High byte of workspace for TX ptr
    sta net_tx_ptr_hi                                                 ; 9024: 85 9b       ..             ; Store as TX pointer high byte
    cli                                                               ; 9026: 58          X              ; Enable interrupts before transmit
    jsr tx_poll_ff                                                    ; 9027: 20 ed 85     ..            ; Transmit with full retry
    ldy #&20 ; ' '                                                    ; 902a: a0 20       .              ; Y=&20: RX end address offset
    lda #&ff                                                          ; 902c: a9 ff       ..             ; Set RX end address to &FFFF (accept any length)
    sta (nfs_workspace),y                                             ; 902e: 91 9e       ..             ; Store end address low byte (&FF)
    iny                                                               ; 9030: c8          .              ; Y=&21
    sta (nfs_workspace),y                                             ; 9031: 91 9e       ..             ; Store end address high byte (&FF)
    ldy #&19                                                          ; 9033: a0 19       ..             ; Y=&19: port byte in workspace RXCB
    lda #&90                                                          ; 9035: a9 90       ..             ; A=&90: FS reply port
    sta (nfs_workspace),y                                             ; 9037: 91 9e       ..             ; Store port to workspace RXCB
    dey                                                               ; 9039: 88          .              ; Y=&18
    lda #&7f                                                          ; 903a: a9 7f       ..             ; A=&7F: flag byte = waiting for reply
    sta (nfs_workspace),y                                             ; 903c: 91 9e       ..             ; Store flag byte to workspace RXCB
    jmp waitfs                                                        ; 903e: 4c 1e 85    L..            ; Jump to RX poll (BRIANX)

; &9041 referenced 1 time by &8ff5
.handle_tx_result
    php                                                               ; 9041: 08          .              ; Save processor flags
    ldy #1                                                            ; 9042: a0 01       ..             ; Y=1: first data byte offset
    lda (osword_pb_ptr),y                                             ; 9044: b1 f0       ..             ; Load first data byte from RX buffer
; ***************************************************************************************
; FS response data relay (DOFS)
; 
; Entered from the econet_tx_rx response handler at &903E after
; loading the first data byte from the RX buffer. Saves the
; command byte and station address from the received packet into
; (net_rx_ptr)+&71/&72, then iterates through remaining data
; bytes. Each byte is stored at (net_rx_ptr)+&7D, the control
; block is set up via ctrl_block_setup_alt, and the packet is
; transmitted. Loops until a &0D terminator or &00 null is found.
; The branch at &9053 (BNE dofs2) handles the first-packet case
; where the data length field at (net_rx_ptr)+&7B is adjusted.
; ***************************************************************************************
.net_write_char
    tax                                                               ; 9046: aa          .              ; X = first data byte (command code)
    iny                                                               ; 9047: c8          .              ; Advance to next data byte
    lda (osword_pb_ptr),y                                             ; 9048: b1 f0       ..             ; Load station address high byte
    iny                                                               ; 904a: c8          .              ; Advance past station addr
    sty ws_ptr_lo                                                     ; 904b: 84 ab       ..             ; Save Y as data index
    ldy #&72 ; 'r'                                                    ; 904d: a0 72       .r             ; Store station addr hi at (net_rx_ptr)+&72
    sta (net_rx_ptr),y                                                ; 904f: 91 9c       ..             ; Store to workspace
    dey                                                               ; 9051: 88          .              ; Y=&71
    txa                                                               ; 9052: 8a          .              ; A = command code (from X)
    sta (net_rx_ptr),y                                                ; 9053: 91 9c       ..             ; Store station addr lo at (net_rx_ptr)+&71
    plp                                                               ; 9055: 28          (              ; Restore flags from earlier PHP
    bne dofs2                                                         ; 9056: d0 1c       ..             ; First call: adjust data length
; &9058 referenced 1 time by &9071
.send_data_bytes
    ldy ws_ptr_lo                                                     ; 9058: a4 ab       ..             ; Reload data index
    inc ws_ptr_lo                                                     ; 905a: e6 ab       ..             ; Advance data index for next iteration
    lda (osword_pb_ptr),y                                             ; 905c: b1 f0       ..             ; Load next data byte
    beq return_8                                                      ; 905e: f0 13       ..             ; Zero byte: end of data, return
    ldy #&7d ; '}'                                                    ; 9060: a0 7d       .}             ; Y=&7D: store byte for TX at offset &7D
    sta (net_rx_ptr),y                                                ; 9062: 91 9c       ..             ; Store data byte at (net_rx_ptr)+&7D for TX
    pha                                                               ; 9064: 48          H              ; Save data byte for &0D check after TX
    jsr ctrl_block_setup_alt                                          ; 9065: 20 82 91     ..            ; Set up TX control block
    jsr enable_irq_and_tx                                             ; 9068: 20 7f 90     ..            ; Enable IRQs and transmit
; &906b referenced 1 time by &906c
.delay_between_tx
    dex                                                               ; 906b: ca          .              ; Short delay loop between TX packets
    bne delay_between_tx                                              ; 906c: d0 fd       ..             ; Spin until X reaches 0
    pla                                                               ; 906e: 68          h              ; Restore data byte for terminator check
    eor #&0d                                                          ; 906f: 49 0d       I.             ; Test for end-of-data marker (&0D)
    bne send_data_bytes                                               ; 9071: d0 e5       ..             ; Not &0D: continue with next byte
; &9073 referenced 1 time by &905e
.return_8
    rts                                                               ; 9073: 60          `              ; Return (data complete)

; &9074 referenced 1 time by &9056
.dofs2
    jsr ctrl_block_setup_alt                                          ; 9074: 20 82 91     ..            ; First-packet: set up control block
    ldy #&7b ; '{'                                                    ; 9077: a0 7b       .{             ; Y=&7B: data length offset
    lda (net_rx_ptr),y                                                ; 9079: b1 9c       ..             ; Load current data length
    adc #3                                                            ; 907b: 69 03       i.             ; Adjust data length by 3 for header bytes
    sta (net_rx_ptr),y                                                ; 907d: 91 9c       ..             ; Store adjusted length
; ***************************************************************************************
; Enable interrupts and transmit via tx_poll_ff
; 
; CLI to enable interrupts, then JMP tx_poll_ff. A short
; tail-call wrapper used after building the TX control block.
; ***************************************************************************************
; &907f referenced 1 time by &9068
.enable_irq_and_tx
    cli                                                               ; 907f: 58          X              ; Enable interrupts
    jmp tx_poll_ff                                                    ; 9080: 4c ed 85    L..            ; Transmit via tx_poll_ff

; ***************************************************************************************
; NETVEC dispatch handler (ENTRY)
; 
; Indirected from NETVEC at &0224. Saves all registers and flags,
; retrieves the reason code from the stacked A, and dispatches to
; one of 9 handlers (codes 0-8) via the PHA/PHA/RTS trampoline at
; &9099. Reason codes >= 9 are ignored.
; 
; Dispatch targets (from NFS09):
;   0:   no-op (RTS)
;   1-3: PRINT -- chars in printer buffer / Ctrl-B / Ctrl-C
;   4:   NWRCH -- write character to screen (net write char)
;   5:   SELECT -- printer selection changed
;   6:   no-op (net read char -- not implemented)
;   7:   NBYTE -- remote OSBYTE call
;   8:   NWORD -- remote OSWORD call
; 
; On Entry:
;     A: reason code (0-8)
; 
; On Exit:
;     A: preserved
;     X: preserved
;     Y: preserved
; ***************************************************************************************
.osword_dispatch
    php                                                               ; 9083: 08          .              ; Save processor status
    pha                                                               ; 9084: 48          H              ; Save A (reason code)
    txa                                                               ; 9085: 8a          .              ; Save X
    pha                                                               ; 9086: 48          H              ; Push X to stack
    tya                                                               ; 9087: 98          .              ; Save Y
    pha                                                               ; 9088: 48          H              ; Push Y to stack
    tsx                                                               ; 9089: ba          .              ; Get stack pointer for indexed access
    lda stk_frame_3,x                                                 ; 908a: bd 03 01    ...            ; Retrieve original A (reason code) from stack
    cmp #9                                                            ; 908d: c9 09       ..             ; Reason codes 0-8 only
    bcs entry1                                                        ; 908f: b0 04       ..             ; Code >= 9: skip dispatch, restore regs
    tax                                                               ; 9091: aa          .              ; X = reason code for table lookup
    jsr osword_trampoline                                             ; 9092: 20 9c 90     ..            ; Dispatch to handler via trampoline
; &9095 referenced 1 time by &908f
.entry1
    pla                                                               ; 9095: 68          h              ; Restore Y
    tay                                                               ; 9096: a8          .              ; Transfer to Y register
    pla                                                               ; 9097: 68          h              ; Restore X
    tax                                                               ; 9098: aa          .              ; Transfer to X register
    pla                                                               ; 9099: 68          h              ; Restore A
    plp                                                               ; 909a: 28          (              ; Restore processor status flags
    rts                                                               ; 909b: 60          `              ; Return with all registers preserved

; &909c referenced 1 time by &9092
.osword_trampoline
    lda osword_tbl_hi,x                                               ; 909c: bd b0 90    ...            ; PHA/PHA/RTS trampoline: push handler addr-1, RTS jumps to it
    pha                                                               ; 909f: 48          H              ; Push high byte of handler address
    lda osword_tbl_lo,x                                               ; 90a0: bd a7 90    ...            ; Load handler low byte from table
    pha                                                               ; 90a3: 48          H              ; Push low byte of handler address
    lda osbyte_a_copy                                                 ; 90a4: a5 ef       ..             ; Load workspace byte &EF for handler
    rts                                                               ; 90a6: 60          `              ; RTS dispatches to pushed handler

; &90a7 referenced 1 time by &90a0
.osword_tbl_lo
    equb <(return_1-1)                                                ; 90a7: f1          .              ; lo(return_1-1): fn 0 (null handler)
    equb <(remote_print_handler-1)                                    ; 90a8: ec          .              ; lo(remote_print_handler-1): fn 1
    equb <(remote_print_handler-1)                                    ; 90a9: ec          .              ; lo(remote_print_handler-1): fn 2
    equb <(remote_print_handler-1)                                    ; 90aa: ec          .              ; lo(remote_print_handler-1): fn 3
    equb <(net_write_char_handler-1)                                  ; 90ab: b8          .              ; lo(net_write_char_handler-1): fn 4
    equb <(printer_select_handler-1)                                  ; 90ac: dd          .              ; lo(printer_select_handler-1): fn 5
    equb <(return_1-1)                                                ; 90ad: f1          .              ; lo(return_1-1): fn 6 (null handler)
    equb <(remote_cmd_dispatch-1)                                     ; 90ae: ea          .              ; lo(remote_cmd_dispatch-1): fn 7
    equb <(remote_osword_handler-1)                                   ; 90af: 56          V              ; lo(remote_osword_handler-1): fn 8
; &90b0 referenced 1 time by &909c
.osword_tbl_hi
    equb >(return_1-1)                                                ; 90b0: 80          .              ; hi(return_1-1): fn 0 (null handler)
    equb >(remote_print_handler-1)                                    ; 90b1: 91          .              ; hi(remote_print_handler-1): fn 1
    equb >(remote_print_handler-1)                                    ; 90b2: 91          .              ; hi(remote_print_handler-1): fn 2
    equb >(remote_print_handler-1)                                    ; 90b3: 91          .              ; hi(remote_print_handler-1): fn 3
    equb >(net_write_char_handler-1)                                  ; 90b4: 90          .              ; hi(net_write_char_handler-1): fn 4
    equb >(printer_select_handler-1)                                  ; 90b5: 91          .              ; hi(printer_select_handler-1): fn 5
    equb >(return_1-1)                                                ; 90b6: 80          .              ; hi(return_1-1): fn 6 (null handler)
    equb >(remote_cmd_dispatch-1)                                     ; 90b7: 90          .              ; hi(remote_cmd_dispatch-1): fn 7
    equb >(remote_osword_handler-1)                                   ; 90b8: 91          .              ; hi(remote_osword_handler-1): fn 8

; ***************************************************************************************
; NETVEC fn 4: handle net write character (NWRCH)
; 
; Zeros the carry flag in the stacked processor status to
; signal success, stores the character from Y into workspace
; offset &DA, loads A=0 as the command type, and falls through
; to setup_tx_and_send.
; 
; On Entry:
;     Y: character to write
; ***************************************************************************************
.net_write_char_handler
    tsx                                                               ; 90b9: ba          .              ; Get stack pointer for P register access
    ror stk_frame_p,x                                                 ; 90ba: 7e 06 01    ~..            ; ROR/ASL on stacked P: zeros carry to signal success
    asl stk_frame_p,x                                                 ; 90bd: 1e 06 01    ...            ; ASL: restore P after ROR zeroed carry
    tya                                                               ; 90c0: 98          .              ; Y = character to write
    ldy #&da                                                          ; 90c1: a0 da       ..             ; Store character at workspace offset &DA
    sta (nfs_workspace),y                                             ; 90c3: 91 9e       ..             ; Store char at workspace offset &DA
    lda #0                                                            ; 90c5: a9 00       ..             ; A=0: command type for net write char
; ***************************************************************************************
; Set up TX control block and send
; 
; Stores A at workspace offset &D9 (command type), then sets byte
; &0C to &80 (TX active flag). Saves the current net_tx_ptr,
; temporarily redirects it to (nfs_workspace)+&0C so tx_poll_ff
; transmits from the workspace TX control block. After transmission
; completes, writes &3F (TX deleted) at (net_tx_ptr)+&00 to mark
; the control block as free, then restores net_tx_ptr to its
; original value.
; 
; On Entry:
;     A: command type byte
; ***************************************************************************************
; &90c7 referenced 3 times by &81bd, &911a, &917d
.setup_tx_and_send
    ldy #&d9                                                          ; 90c7: a0 d9       ..             ; Y=&D9: command type offset
    sta (nfs_workspace),y                                             ; 90c9: 91 9e       ..             ; Store command type at ws+&D9
    lda #&80                                                          ; 90cb: a9 80       ..             ; Mark TX control block as active (&80)
    ldy #&0c                                                          ; 90cd: a0 0c       ..             ; Y=&0C: TXCB start offset
    sta (nfs_workspace),y                                             ; 90cf: 91 9e       ..             ; Set TX active flag at ws+&0C
    lda net_tx_ptr                                                    ; 90d1: a5 9a       ..             ; Save net_tx_ptr; redirect to workspace TXCB
    pha                                                               ; 90d3: 48          H              ; Save net_tx_ptr low
    lda net_tx_ptr_hi                                                 ; 90d4: a5 9b       ..             ; Load net_tx_ptr high
    pha                                                               ; 90d6: 48          H              ; Save net_tx_ptr high
    sty net_tx_ptr                                                    ; 90d7: 84 9a       ..             ; Redirect net_tx_ptr low to workspace
    ldx nfs_workspace_hi                                              ; 90d9: a6 9f       ..             ; Load workspace page high byte
    stx net_tx_ptr_hi                                                 ; 90db: 86 9b       ..             ; Complete ptr redirect
    jsr tx_poll_ff                                                    ; 90dd: 20 ed 85     ..            ; Transmit with full retry
    lda #&3f ; '?'                                                    ; 90e0: a9 3f       .?             ; Mark TXCB as deleted (&3F) after transmit
    sta (net_tx_ptr,x)                                                ; 90e2: 81 9a       ..             ; Write &3F to TXCB byte 0
    pla                                                               ; 90e4: 68          h              ; Restore net_tx_ptr high
    sta net_tx_ptr_hi                                                 ; 90e5: 85 9b       ..             ; Write back
    pla                                                               ; 90e7: 68          h              ; Restore net_tx_ptr low
    sta net_tx_ptr                                                    ; 90e8: 85 9a       ..             ; Write back
    rts                                                               ; 90ea: 60          `              ; Return

; ***************************************************************************************
; Fn 7: remote OSBYTE handler (NBYTE)
; 
; Full RPC mechanism for OSBYTE calls across the network. When a
; machine is remoted, OSBYTE/OSWORD calls that affect terminal-side
; hardware (keyboard scanning, flash rates, etc.) must be indirected
; across the net. OSBYTE calls are classified into three categories:
;   Y>0 (NCTBPL table): executed on BOTH machines (flash rates etc.)
;   Y<0 (NCTBMI table): executed on terminal only, result sent back
;   Y=0: not recognised, passed through unhandled
; Results returned via stack manipulation: the saved processor status
; byte at &0106 has V-flag (bit 6) forced on to tell the MOS the
; call was claimed (preventing dispatch to other ROMs), and the I-bit
; (bit 2) forced on to disable interrupts during register restoration,
; preventing race conditions. The carry flag in the saved P is also
; manipulated via ROR/ASL to zero it, signaling success to the caller.
; OSBYTE &81 (INKEY) gets special handling as it must read the
; terminal's keyboard.
; ***************************************************************************************
.remote_cmd_dispatch
    ldy osword_pb_ptr_hi                                              ; 90eb: a4 f1       ..             ; Load original Y (OSBYTE secondary param)
    cmp #&81                                                          ; 90ed: c9 81       ..             ; OSBYTE &81 (INKEY): always forward to terminal
    beq dispatch_remote_osbyte                                        ; 90ef: f0 13       ..             ; Forward &81 to terminal for keyboard read
    ldy #1                                                            ; 90f1: a0 01       ..             ; Y=1: search NCTBPL table (execute on both)
    ldx #9                                                            ; 90f3: a2 09       ..             ; X=9: 10-entry NCTBPL table size
    jsr match_osbyte_code                                             ; 90f5: 20 3f 91     ?.            ; Search for OSBYTE code in NCTBPL table
    beq dispatch_remote_osbyte                                        ; 90f8: f0 0a       ..             ; Match found: dispatch with Y=1 (both)
    dey                                                               ; 90fa: 88          .              ; Y=-1: search NCTBMI table (terminal only)
    dey                                                               ; 90fb: 88          .              ; Second DEY: Y=&FF (from 1 via 0)
    ldx #&0e                                                          ; 90fc: a2 0e       ..             ; X=&0E: 15-entry NCTBMI table size
    jsr match_osbyte_code                                             ; 90fe: 20 3f 91     ?.            ; Search for OSBYTE code in NCTBMI table
    beq dispatch_remote_osbyte                                        ; 9101: f0 01       ..             ; Match found: dispatch with Y=&FF (terminal)
    iny                                                               ; 9103: c8          .              ; Y=0: OSBYTE not recognised, ignore
; &9104 referenced 3 times by &90ef, &90f8, &9101
.dispatch_remote_osbyte
    ldx #2                                                            ; 9104: a2 02       ..             ; X=2 bytes to copy (default for RBYTE)
    tya                                                               ; 9106: 98          .              ; A=Y: check table match result
    beq return_nbyte                                                  ; 9107: f0 35       .5             ; Y=0: not recognised, return unhandled
    php                                                               ; 9109: 08          .              ; Y>0 (NCTBPL): send only, no result expected
    bpl nbyte6                                                        ; 910a: 10 01       ..             ; Y>0 (NCTBPL): no result expected, skip RX
    inx                                                               ; 910c: e8          .              ; Y<0 (NCTBMI): X=3 bytes (result + P flags); X=&03
; &910d referenced 1 time by &910a
.nbyte6
    ldy #&dc                                                          ; 910d: a0 dc       ..             ; Y=&DC: top of 3-byte stack frame region
; &910f referenced 1 time by &9117
.nbyte1
    lda tube_claimed_id,y                                             ; 910f: b9 15 00    ...            ; Copy OSBYTE args from stack frame to workspace
    sta (nfs_workspace),y                                             ; 9112: 91 9e       ..             ; Store to NFS workspace for transmission
    dey                                                               ; 9114: 88          .              ; Next byte (descending)
    cpy #&da                                                          ; 9115: c0 da       ..             ; Copied all 3 bytes? (&DC, &DB, &DA)
    bpl nbyte1                                                        ; 9117: 10 f6       ..             ; Loop for remaining bytes
    txa                                                               ; 9119: 8a          .              ; A = byte count for setup_tx_and_send
    jsr setup_tx_and_send                                             ; 911a: 20 c7 90     ..            ; Build TXCB and transmit to terminal
    plp                                                               ; 911d: 28          (              ; Restore N flag from table match type
    bpl return_nbyte                                                  ; 911e: 10 1e       ..             ; Y was positive (NCTBPL): done, no result
    lda #&7f                                                          ; 9120: a9 7f       ..             ; Set up RX control block to wait for reply
    ldy #&0c                                                          ; 9122: a0 0c       ..             ; Y=&0C: RX control block offset in workspace
    sta (nfs_workspace),y                                             ; 9124: 91 9e       ..             ; Write &7F (waiting) to RXCB flag byte
; &9126 referenced 1 time by &9128
.poll_rxcb_flag
    lda (nfs_workspace),y                                             ; 9126: b1 9e       ..             ; Poll for TX completion (wait for bit 7 set)
    bpl poll_rxcb_flag                                                ; 9128: 10 fc       ..             ; Bit7 clear: still waiting, poll again
    tsx                                                               ; 912a: ba          .              ; X = stack pointer for register restoration
    ldy #&dd                                                          ; 912b: a0 dd       ..             ; Y=&DD: saved P byte offset in workspace
    lda (nfs_workspace),y                                             ; 912d: b1 9e       ..             ; Load remote processor status from reply
    ora #&44 ; 'D'                                                    ; 912f: 09 44       .D             ; Force V=1 (claimed) and I=1 (no IRQ) in saved P
    bne nbyte5                                                        ; 9131: d0 04       ..             ; ALWAYS branch (ORA #&44 never zero); ALWAYS branch

; &9133 referenced 1 time by &913c
.nbyte4
    dey                                                               ; 9133: 88          .              ; Previous workspace offset
    dex                                                               ; 9134: ca          .              ; Previous stack register slot
    lda (nfs_workspace),y                                             ; 9135: b1 9e       ..             ; Load next result byte (X, then Y)
; &9137 referenced 1 time by &9131
.nbyte5
    sta stk_frame_p,x                                                 ; 9137: 9d 06 01    ...            ; Write result bytes to stacked registers
    cpy #&da                                                          ; 913a: c0 da       ..             ; Copied all result bytes? (P at &DA)
    bne nbyte4                                                        ; 913c: d0 f5       ..             ; Loop for remaining result bytes
; &913e referenced 2 times by &9107, &911e
.return_nbyte
    rts                                                               ; 913e: 60          `              ; Return to OSBYTE dispatcher

; ***************************************************************************************
; Search remote OSBYTE table for match (NCALLP)
; 
; Searches remote_osbyte_table for OSBYTE code A. X indexes the
; last entry to check (table is scanned X..0). Returns Z=1 if
; found. Called twice by remote_cmd_dispatch:
; 
;   X=9  → first 10 entries (NCTBPL: execute on both machines)
;   X=14 → all 15 entries (NCTBMI: execute on terminal only)
; 
; The last 5 entries (&0B, &0C, &0F, &79, &7A) are terminal-only
; because they affect the local keyboard or buffers.
; 
; On entry: A = OSBYTE code, X = table size - 1
; On exit:  Z=1 if match found, Z=0 if not
; ***************************************************************************************
; &913f referenced 3 times by &90f5, &90fe, &9145
.match_osbyte_code
    cmp remote_osbyte_table,x                                         ; 913f: dd 48 91    .H.            ; Compare OSBYTE code with table entry
    beq return_match_osbyte                                           ; 9142: f0 03       ..             ; Match found: return with Z=1
    dex                                                               ; 9144: ca          .              ; Next table entry (descending)
    bpl match_osbyte_code                                             ; 9145: 10 f8       ..             ; Loop for remaining entries
; &9147 referenced 2 times by &9142, &915f
.return_match_osbyte
    rts                                                               ; 9147: 60          `              ; Return; Z=1 if match, Z=0 if not

; &9148 referenced 1 time by &913f
.remote_osbyte_table
    equb 4                                                            ; 9148: 04          .              ; OSBYTE &04: cursor key status
    equb 9                                                            ; 9149: 09          .              ; OSBYTE &09: flash duration (1st colour)
    equb &0a                                                          ; 914a: 0a          .              ; OSBYTE &0A: flash duration (2nd colour)
    equb &15                                                          ; 914b: 15          .              ; OSBYTE &15: flush specific buffer
    equb &9a                                                          ; 914c: 9a          .              ; OSBYTE &9A: video ULA control register
    equb &9b                                                          ; 914d: 9b          .              ; OSBYTE &9B: video ULA palette
    equb &e1                                                          ; 914e: e1          .              ; OSBYTE &E1: function key &C0-&CF
    equb &e2                                                          ; 914f: e2          .              ; OSBYTE &E2: function key &D0-&DF
    equb &e3                                                          ; 9150: e3          .              ; OSBYTE &E3: function key &E0-&EF
    equb &e4                                                          ; 9151: e4          .              ; OSBYTE &E4: function key &F0-&FF
    equb &0b                                                          ; 9152: 0b          .              ; OSBYTE &0B: auto-repeat delay
    equb &0c                                                          ; 9153: 0c          .              ; OSBYTE &0C: auto-repeat rate
    equb &0f                                                          ; 9154: 0f          .              ; OSBYTE &0F: flush buffer class
    equb &79                                                          ; 9155: 79          y              ; OSBYTE &79: keyboard scan from X
    equb &7a                                                          ; 9156: 7a          z              ; OSBYTE &7A: keyboard scan from 16

; ***************************************************************************************
; NETVEC fn 8: remote OSWORD dispatch (NWORD)
; 
; Only accepts OSWORD 7 (make a sound) and OSWORD 8 (define an
; envelope), rejecting all others. Sets Y=14 as the maximum
; parameter byte count, then falls through to remote_cmd_data.
; ***************************************************************************************
.remote_osword_handler
    ldy #&0e                                                          ; 9157: a0 0e       ..             ; Y=&0E: max 14 parameter bytes for OSWORD
    cmp #7                                                            ; 9159: c9 07       ..             ; OSWORD 7 = make a sound
    beq copy_params_rword                                             ; 915b: f0 04       ..             ; OSWORD 7 (sound): handle via common path
    cmp #8                                                            ; 915d: c9 08       ..             ; OSWORD 8 = define an envelope
; ***************************************************************************************
; Fn 8: remote OSWORD handler (NWORD)
; 
; Only intercepts OSWORD 7 (make a sound) and OSWORD 8 (define an
; envelope). Unlike NBYTE which returns results, NWORD is entirely
; fire-and-forget -- no return path is implemented. The developer
; explicitly noted this was acceptable since sound/envelope commands
; don't return meaningful results. Copies up to 14 parameter bytes
; from the RX buffer to workspace, tags the message as RWORD, and
; transmits.
; ***************************************************************************************
.remote_cmd_data
    bne return_match_osbyte                                           ; 915f: d0 e6       ..             ; Not OSWORD 7 or 8: ignore (BNE exits)
; &9161 referenced 1 time by &915b
.copy_params_rword
    ldx #&db                                                          ; 9161: a2 db       ..             ; Point workspace to offset &DB for params
    stx nfs_workspace                                                 ; 9163: 86 9e       ..             ; Store workspace ptr offset &DB
; &9165 referenced 1 time by &916a
.copy_osword_params
    lda (osword_pb_ptr),y                                             ; 9165: b1 f0       ..             ; Load param byte from OSWORD param block
    sta (nfs_workspace),y                                             ; 9167: 91 9e       ..             ; Write param byte to workspace
    dey                                                               ; 9169: 88          .              ; Next byte (descending)
    bpl copy_osword_params                                            ; 916a: 10 f9       ..             ; Loop for all parameter bytes
    iny                                                               ; 916c: c8          .              ; Y=0 after loop
    dec nfs_workspace                                                 ; 916d: c6 9e       ..             ; Point workspace to offset &DA
    lda osbyte_a_copy                                                 ; 916f: a5 ef       ..             ; Load original OSWORD code
    sta (nfs_workspace),y                                             ; 9171: 91 9e       ..             ; Store OSWORD code at ws+0
    sty nfs_workspace                                                 ; 9173: 84 9e       ..             ; Reset workspace ptr to base
    ldy #&14                                                          ; 9175: a0 14       ..             ; Y=&14: command type offset
    lda #&e9                                                          ; 9177: a9 e9       ..             ; Tag as RWORD (port &E9)
    sta (nfs_workspace),y                                             ; 9179: 91 9e       ..             ; Store port tag at ws+&14
    lda #1                                                            ; 917b: a9 01       ..             ; A=1: single-byte TX
    jsr setup_tx_and_send                                             ; 917d: 20 c7 90     ..            ; Load template byte from ctrl_block_template[X]
    stx nfs_workspace                                                 ; 9180: 86 9e       ..             ; Restore workspace ptr
; ***************************************************************************************
; Alternate entry into control block setup
; 
; Sets X=&0D, Y=&7C. Tests bit 6 of &83B3 to choose target:
;   V=0 (bit 6 clear): stores to (nfs_workspace)
;   V=1 (bit 6 set):   stores to (net_rx_ptr)
; ***************************************************************************************
; &9182 referenced 2 times by &9065, &9074
.ctrl_block_setup_alt
    ldx #&0d                                                          ; 9182: a2 0d       ..             ; X=&0D: template offset for alt entry
    ldy #&7c ; '|'                                                    ; 9184: a0 7c       .|             ; Y=&7C: target workspace offset for alt entry
    bit tx_ctrl_upper                                                 ; 9186: 2c a1 83    ,..            ; BIT test: V flag = bit 6 of &83B3
    bvs cbset2                                                        ; 9189: 70 05       p.             ; V=1: store to (net_rx_ptr) instead
; ***************************************************************************************
; Control block setup — main entry
; 
; Sets X=&1A, Y=&17, clears V (stores to nfs_workspace).
; Reads the template table at &91B4 indexed by X, storing each
; value into the target workspace at offset Y. Both X and Y
; are decremented on each iteration.
; 
; Template sentinel values:
;   &FE = stop (end of template for this entry path)
;   &FD = skip (leave existing value unchanged)
;   &FC = use page high byte of target pointer
; ***************************************************************************************
; &918b referenced 1 time by &84bf
.ctrl_block_setup
    ldy #&17                                                          ; 918b: a0 17       ..             ; Y=&17: workspace target offset (main entry)
    ldx #&1a                                                          ; 918d: a2 1a       ..             ; X=&1A: template table index (main entry)
; &918f referenced 1 time by &924e
.ctrl_block_setup_clv
    clv                                                               ; 918f: b8          .              ; V=0: target is (nfs_workspace)
; &9190 referenced 2 times by &9189, &91b1
.cbset2
    lda ctrl_block_template,x                                         ; 9190: bd b7 91    ...            ; Load template byte from ctrl_block_template[X]
    cmp #&fe                                                          ; 9193: c9 fe       ..             ; &FE = stop sentinel
    beq cb_template_tail                                              ; 9195: f0 1c       ..             ; End of template: jump to exit
    cmp #&fd                                                          ; 9197: c9 fd       ..             ; &FD = skip sentinel
    beq cb_template_main_start                                        ; 9199: f0 14       ..             ; Skip: don't store, just decrement Y
    cmp #&fc                                                          ; 919b: c9 fc       ..             ; &FC = page byte sentinel
    bne cbset3                                                        ; 919d: d0 08       ..             ; Not sentinel: store template value directly
    lda net_rx_ptr_hi                                                 ; 919f: a5 9d       ..             ; V=1: use (net_rx_ptr) page
    bvs rxcb_matched                                                  ; 91a1: 70 02       p.             ; V=1: skip to net_rx_ptr page
    lda nfs_workspace_hi                                              ; 91a3: a5 9f       ..             ; V=0: use (nfs_workspace) page
; &91a5 referenced 1 time by &91a1
.rxcb_matched
    sta net_tx_ptr_hi                                                 ; 91a5: 85 9b       ..             ; PAGE byte → Y=&02 / Y=&74
; &91a7 referenced 1 time by &919d
.cbset3
    bvs cbset4                                                        ; 91a7: 70 04       p.             ; → Y=&04 / Y=&76
    sta (nfs_workspace),y                                             ; 91a9: 91 9e       ..             ; PAGE byte → Y=&06 / Y=&78
    bvc cb_template_main_start                                        ; 91ab: 50 02       P.             ; → Y=&08 / Y=&7A; ALWAYS branch

; &91ad referenced 1 time by &91a7
.cbset4
    sta (net_rx_ptr),y                                                ; 91ad: 91 9c       ..             ; Alt-path only → Y=&70
; &91af referenced 2 times by &9199, &91ab
.cb_template_main_start
    dey                                                               ; 91af: 88          .              ; → Y=&0C (main only)
    dex                                                               ; 91b0: ca          .              ; → Y=&0D (main only)
    bpl cbset2                                                        ; 91b1: 10 dd       ..             ; Loop until all template bytes done
; &91b3 referenced 1 time by &9195
.cb_template_tail
    iny                                                               ; 91b3: c8          .              ; → Y=&10 (main only)
    sty net_tx_ptr                                                    ; 91b4: 84 9a       ..             ; Store final offset as net_tx_ptr
    rts                                                               ; 91b6: 60          `              ; → Y=&07 / Y=&79

; ***************************************************************************************
; Control block initialisation template
; 
; Read by the loop at &918D, indexed by X from a starting value
; down to 0. Values are stored into either (nfs_workspace) or
; (net_rx_ptr) at offset Y, depending on the V flag.
; 
; Two entry paths read different slices of this table:
;   ctrl_block_setup:   X=&1A (26) down, Y=&17 (23) down, V=0
;   ctrl_block_setup_alt: X=&0D (13) down, Y=&7C (124) down, V from BIT &83B3
; 
; Sentinel values:
;   &FE = stop processing
;   &FD = skip this offset (decrement Y but don't store)
;   &FC = substitute the page byte (net_rx_ptr_hi or nfs_workspace_hi)
; ***************************************************************************************
; &91b7 referenced 1 time by &9190
.ctrl_block_template
    sta zp_ptr_lo                                                     ; 91b7: 85 00       ..             ; Alt-path only → Y=&6F
    sbc l7dfd,x                                                       ; 91b9: fd fd 7d    ..}
    equb &fc, &ff, &ff, &7e, &fc, &ff, &ff,   0,   0, &fe, &80, &93   ; 91bc: fc ff ff... ...            ; → Y=&0D (main only); → Y=&03 / Y=&75; SKIP (main only); → Y=&10 (main only); → Y=&08 / Y=&7A; → Y=&09 / Y=&7B; PAGE byte → Y=&15 (main only); → Y=&16 (main only)
    equb &fd, &fd, &d9, &fc, &ff, &ff, &de, &fc, &ff, &ff, &fe, &d1   ; 91c8: fd fd d9... ...            ; SKIP (main only); PAGE byte → Y=&11 (main only); → Y=&12 (main only); → Y=&13 (main only); → Y=&14 (main only); → Y=&17 (main only)
    equb &fd, &fd, &1f, &fd, &ff, &ff, &fd, &fd, &ff, &ff             ; 91d4: fd fd 1f... ...

; ***************************************************************************************
; Fn 5: printer selection changed (SELECT)
; 
; Called when the printer selection changes. Compares X against
; the network printer buffer number (&F0). If it matches,
; initialises the printer buffer pointer (&0D61 = &1F) and
; sets the initial flag byte (&0D60 = &41). Otherwise falls
; through to return.
; 
; On Entry:
;     X: 1-based buffer number
; ***************************************************************************************
.printer_select_handler
    dex                                                               ; 91de: ca          .              ; X-1: convert 1-based buffer to 0-based
    cpx osword_pb_ptr                                                 ; 91df: e4 f0       ..             ; Is this the network printer buffer?
    bne setup1                                                        ; 91e1: d0 07       ..             ; No: skip printer init
    lda #&1f                                                          ; 91e3: a9 1f       ..             ; &1F = initial buffer pointer offset
    sta printer_buf_ptr                                               ; 91e5: 8d 61 0d    .a.            ; Reset printer buffer write position
    lda #&41 ; 'A'                                                    ; 91e8: a9 41       .A             ; &41 = initial PFLAGS (bit 6 set, bit 0 set)
; &91ea referenced 1 time by &91e1
.setup1
    sta prot_flags                                                    ; 91ea: 85 99       ..             ; Store A to printer status byte
; &91ec referenced 2 times by &91ef, &9203
.return_printer_select
    rts                                                               ; 91ec: 60          `              ; Return

; ***************************************************************************************
; Fn 1/2/3: network printer handler (PRINT)
; 
; Handles network printer output. Reason 1 = chars in buffer (extract
; from MOS buffer 3 and accumulate), reason 2 = Ctrl-B (start print),
; reason 3 = Ctrl-C (end print). The printer status byte PFLAGS uses:
;   bit 7 = sequence number (toggles per packet for dup detection)
;   bit 6 = always 1 (validity marker)
;   bit 0 = 0 when print active
; Print streams reuse the BSXMIT (byte-stream transmit) code with
; handle=0, which causes the AND SEQNOS to produce zero and sidestep
; per-file sequence tracking. After transmission, TXCB pointer bytes
; are filled with &FF to prevent stale values corrupting subsequent
; BGET/BPUT operations (a historically significant bug fix).
; N.B. The printer and REMOTE facility share the same dynamically
; allocated static workspace page via WORKP1 (&9E,&9F) — care must
; be taken to never leave the pointer corrupted, as corruption would
; cause one subsystem to overwrite the other's data.
; Only handles buffer 4 (network printer); others are ignored.
; 
; On Entry:
;     X: reason code (1=chars, 2=Ctrl-B, 3=Ctrl-C)
;     Y: buffer number (must be 4 for network printer)
; ***************************************************************************************
.remote_print_handler
    cpy #4                                                            ; 91ed: c0 04       ..             ; Only handle buffer 4 (network printer)
    bne return_printer_select                                         ; 91ef: d0 fb       ..             ; Not buffer 4: ignore
    txa                                                               ; 91f1: 8a          .              ; A = reason code
    dex                                                               ; 91f2: ca          .              ; Reason 1? (DEX: 1->0)
    bne toggle_print_flag                                             ; 91f3: d0 26       .&             ; Not reason 1: handle Ctrl-B/C
    tsx                                                               ; 91f5: ba          .              ; Get stack pointer for P register
    ora stk_frame_p,x                                                 ; 91f6: 1d 06 01    ...            ; Force I flag in stacked P to block IRQs
    sta stk_frame_p,x                                                 ; 91f9: 9d 06 01    ...            ; Write back modified P register
; &91fc referenced 2 times by &920b, &9210
.prlp1
    lda #osbyte_read_buffer                                           ; 91fc: a9 91       ..             ; OSBYTE &91: extract char from MOS buffer
    ldx #buffer_printer                                               ; 91fe: a2 03       ..             ; X=3: printer buffer number
    jsr osbyte                                                        ; 9200: 20 f4 ff     ..            ; Get character from input buffer (C is set if the buffer is empty, otherwise Y=extracted character)
    bcs return_printer_select                                         ; 9203: b0 e7       ..             ; Buffer empty: return
    tya                                                               ; 9205: 98          .              ; Y = extracted character; Y is the character extracted from the buffer
    jsr store_output_byte                                             ; 9206: 20 12 92     ..            ; Store char in output buffer
    cpy #&6e ; 'n'                                                    ; 9209: c0 6e       .n             ; Buffer nearly full? (&6E = threshold)
    bcc prlp1                                                         ; 920b: 90 ef       ..             ; Not full: get next char
    jsr flush_output_block                                            ; 920d: 20 3a 92     :.            ; Buffer full: flush to network
    bcc prlp1                                                         ; 9210: 90 ea       ..             ; Continue after flush
; ***************************************************************************************
; Store output byte to network buffer
; 
; Stores byte A at the current output offset in the RX buffer
; pointed to by (net_rx_ptr). Advances the offset counter and
; triggers a flush if the buffer is full.
; 
; On Entry:
;     A: byte to store
; 
; On Exit:
;     Y: buffer offset before store
; ***************************************************************************************
; &9212 referenced 2 times by &9206, &921f
.store_output_byte
    ldy printer_buf_ptr                                               ; 9212: ac 61 0d    .a.            ; Load current buffer offset
    sta (net_rx_ptr),y                                                ; 9215: 91 9c       ..             ; Store byte at current position
    inc printer_buf_ptr                                               ; 9217: ee 61 0d    .a.            ; Advance buffer pointer
    rts                                                               ; 921a: 60          `              ; Return; Y = buffer offset

; &921b referenced 1 time by &91f3
.toggle_print_flag
    pha                                                               ; 921b: 48          H              ; Save reason code
    txa                                                               ; 921c: 8a          .              ; A = reason code
    eor #1                                                            ; 921d: 49 01       I.             ; EOR #1: toggle print-active flag (bit 0)
    jsr store_output_byte                                             ; 921f: 20 12 92     ..            ; Store toggled flag as output byte
    eor prot_flags                                                    ; 9222: 45 99       E.             ; XOR with PFLAGS
    ror a                                                             ; 9224: 6a          j              ; Test if sequence changed (bit 7 mismatch)
    bcc skip_flush                                                    ; 9225: 90 06       ..             ; Sequence unchanged: skip flush
    rol a                                                             ; 9227: 2a          *              ; Undo ROR
    sta prot_flags                                                    ; 9228: 85 99       ..             ; Update PFLAGS
    jsr flush_output_block                                            ; 922a: 20 3a 92     :.            ; Flush current output block
; &922d referenced 1 time by &9225
.skip_flush
    lda prot_flags                                                    ; 922d: a5 99       ..             ; Load PFLAGS
    and #&f0                                                          ; 922f: 29 f0       ).             ; Extract upper nibble of PFLAGS
    ror a                                                             ; 9231: 6a          j              ; Shift for bit extraction
    tax                                                               ; 9232: aa          .              ; Save in X
    pla                                                               ; 9233: 68          h              ; Restore original reason code
    ror a                                                             ; 9234: 6a          j              ; Merge print-active bit from original A
    txa                                                               ; 9235: 8a          .              ; Retrieve shifted PFLAGS
    rol a                                                             ; 9236: 2a          *              ; Recombine into new PFLAGS value
    sta prot_flags                                                    ; 9237: 85 99       ..             ; Update PFLAGS
    rts                                                               ; 9239: 60          `              ; Return

; ***************************************************************************************
; Flush output block
; 
; Sends the accumulated output block over the network, resets the
; buffer pointer, and prepares for the next block of output data.
; ***************************************************************************************
; &923a referenced 2 times by &920d, &922a
.flush_output_block
    ldy #8                                                            ; 923a: a0 08       ..             ; Store buffer length at workspace offset &08
    lda printer_buf_ptr                                               ; 923c: ad 61 0d    .a.            ; Current buffer fill position
    sta (nfs_workspace),y                                             ; 923f: 91 9e       ..             ; Write to workspace offset &08
    lda net_rx_ptr_hi                                                 ; 9241: a5 9d       ..             ; Store page high byte at offset &09
    iny                                                               ; 9243: c8          .              ; Y=&09
    sta (nfs_workspace),y                                             ; 9244: 91 9e       ..             ; Write page high byte at offset &09
    ldy #5                                                            ; 9246: a0 05       ..             ; Also store at offset &05
    sta (nfs_workspace),y                                             ; 9248: 91 9e       ..             ; (end address high byte)
    ldy #&0b                                                          ; 924a: a0 0b       ..             ; Y=&0B: flag byte offset
    ldx #&26 ; '&'                                                    ; 924c: a2 26       .&             ; X=&26: start from template entry &26
    jsr ctrl_block_setup_clv                                          ; 924e: 20 8f 91     ..            ; Reuse ctrl_block_setup with CLV entry
    dey                                                               ; 9251: 88          .              ; Y=&0A: sequence flag byte offset
    lda prot_flags                                                    ; 9252: a5 99       ..             ; Load protocol flags (PFLAGS)
    pha                                                               ; 9254: 48          H              ; Save current PFLAGS
    rol a                                                             ; 9255: 2a          *              ; Carry = current sequence (bit 7)
    pla                                                               ; 9256: 68          h              ; Restore original PFLAGS
    eor #&80                                                          ; 9257: 49 80       I.             ; Toggle sequence number (bit 7 of PFLAGS)
    sta prot_flags                                                    ; 9259: 85 99       ..             ; Save toggled PFLAGS
    rol a                                                             ; 925b: 2a          *              ; Old sequence bit into bit 0
    sta (nfs_workspace),y                                             ; 925c: 91 9e       ..             ; Store sequence flag at offset &0A
    ldy #&1f                                                          ; 925e: a0 1f       ..             ; Y=&1F: buffer start offset
    sty printer_buf_ptr                                               ; 9260: 8c 61 0d    .a.            ; Reset printer buffer to start (&1F)
    lda #0                                                            ; 9263: a9 00       ..             ; A=0: printer output flag
    tax                                                               ; 9265: aa          .              ; X=0: workspace low byte; X=&00
    ldy nfs_workspace_hi                                              ; 9266: a4 9f       ..             ; Y = workspace page high byte
    cli                                                               ; 9268: 58          X              ; Enable interrupts before TX
; ***************************************************************************************
; Byte-stream transmit (BSXMIT/BSPSX)
; 
; Transmits a data packet over econet with sequence number tracking.
; Sets up the TX control block pointer from X/Y, computes the
; sequence bit from A AND fs_sequence_nos (handle-based tracking),
; merges it into the flag byte at (net_tx_ptr)+0, then initiates
; transmit via tx_poll_ff. Sets end addresses (offsets 8/9) to
; &FF to allow unlimited data. Selects port byte &D1 (print) or
; &90 (FS) based on the original A value. Polls the TX result in
; a loop via BRIANX (c8530), retrying while the result bit
; differs from the expected sequence. On success, toggles the
; sequence tracking bit in fs_sequence_nos.
; 
; On Entry:
;     A: handle bitmask (0=printer, non-zero=file)
;     X: TX control block address low
;     Y: TX control block address high
; ***************************************************************************************
; &9269 referenced 2 times by &83fa, &8436
.econet_tx_retry
    stx net_tx_ptr                                                    ; 9269: 86 9a       ..             ; Set TX control block ptr low byte
    sty net_tx_ptr_hi                                                 ; 926b: 84 9b       ..             ; Set TX control block ptr high byte
    pha                                                               ; 926d: 48          H              ; Save A (handle bitmask) for later
    and fs_sequence_nos                                               ; 926e: 2d 08 0e    -..            ; Compute sequence bit from handle
    beq bsxl1                                                         ; 9271: f0 02       ..             ; Zero: no sequence bit set
    lda #1                                                            ; 9273: a9 01       ..             ; Non-zero: normalise to bit 0
; &9275 referenced 1 time by &9271
.bsxl1
    ldy #0                                                            ; 9275: a0 00       ..             ; Y=0: flag byte offset in TXCB
    ora (net_tx_ptr),y                                                ; 9277: 11 9a       ..             ; Merge sequence into existing flag byte
    pha                                                               ; 9279: 48          H              ; Save merged flag byte
    sta (net_tx_ptr),y                                                ; 927a: 91 9a       ..             ; Write flag+sequence to TXCB byte 0
    jsr tx_poll_ff                                                    ; 927c: 20 ed 85     ..            ; Transmit with full retry
    lda #&ff                                                          ; 927f: a9 ff       ..             ; End address &FFFF = unlimited data length
    ldy #8                                                            ; 9281: a0 08       ..             ; Y=8: end address low offset in TXCB
    sta (net_tx_ptr),y                                                ; 9283: 91 9a       ..             ; Store &FF to end addr low
    iny                                                               ; 9285: c8          .              ; Y=&09
    sta (net_tx_ptr),y                                                ; 9286: 91 9a       ..             ; Store &FF to end addr high (Y=9)
    pla                                                               ; 9288: 68          h              ; Recover merged flag byte
    tax                                                               ; 9289: aa          .              ; Save in X for sequence compare
    ldy #&d1                                                          ; 928a: a0 d1       ..             ; Y=&D1: printer port number
    pla                                                               ; 928c: 68          h              ; Recover saved handle bitmask
    pha                                                               ; 928d: 48          H              ; Re-save for later consumption
    beq bspsx                                                         ; 928e: f0 02       ..             ; A=0: port &D1 (print); A!=0: port &90 (FS)
    ldy #&90                                                          ; 9290: a0 90       ..             ; Y=&90: FS data port
; &9292 referenced 1 time by &928e
.bspsx
    tya                                                               ; 9292: 98          .              ; A = selected port number
    ldy #1                                                            ; 9293: a0 01       ..             ; Y=1: port byte offset in TXCB
    sta (net_tx_ptr),y                                                ; 9295: 91 9a       ..             ; Write port to TXCB byte 1
    txa                                                               ; 9297: 8a          .              ; A = saved flag byte (expected sequence)
    dey                                                               ; 9298: 88          .              ; Y=&00
    pha                                                               ; 9299: 48          H              ; Push expected sequence for retry loop
; &929a referenced 1 time by &92a6
.bsxl0
    lda #&7f                                                          ; 929a: a9 7f       ..             ; Flag byte &7F = waiting for reply
    sta (net_tx_ptr),y                                                ; 929c: 91 9a       ..             ; Write to TXCB flag byte (Y=0)
    jsr waitfs                                                        ; 929e: 20 1e 85     ..            ; Transmit and wait for reply (BRIANX)
    pla                                                               ; 92a1: 68          h              ; Recover expected sequence
    pha                                                               ; 92a2: 48          H              ; Keep on stack for next iteration
    eor (net_tx_ptr),y                                                ; 92a3: 51 9a       Q.             ; Check if TX result matches expected sequence
    ror a                                                             ; 92a5: 6a          j              ; Bit 0 to carry (sequence mismatch?)
    bcs bsxl0                                                         ; 92a6: b0 f2       ..             ; C=1: mismatch, retry transmit
    pla                                                               ; 92a8: 68          h              ; Clean up: discard expected sequence
    pla                                                               ; 92a9: 68          h              ; Discard saved handle bitmask
    eor fs_sequence_nos                                               ; 92aa: 4d 08 0e    M..            ; Toggle sequence bit on success
.return_bspsx
    rts                                                               ; 92ad: 60          `              ; Return

; ***************************************************************************************
; Save palette and VDU state (CVIEW)
; 
; Part of the VIEW facility (second iteration, started 27/7/82).
; Uses dynamically allocated buffer store. The WORKP1 pointer
; (&9E,&9F) serves double duty: non-zero indicates data ready AND
; provides the buffer address — an efficient use of scarce zero-
; page space. This code must be user-transparent as the NFS may not
; be the dominant filing system.
; Reads all 16 palette entries using OSWORD &0B (read palette) and
; stores the results. Then reads cursor position (OSBYTE &85),
; shadow RAM allocation (OSBYTE &C2), and screen start address
; (OSBYTE &C3) using the 3-entry table at &931E.
; On completion, restores the JSR buffer protection bits (LSTAT)
; from OLDJSR to re-enable JSR reception, which was disabled during
; the screen data capture to prevent interference.
; ***************************************************************************************
.lang_2_save_palette_vdu
    lda table_idx                                                     ; 92ae: a5 ad       ..             ; Save current table index
    pha                                                               ; 92b0: 48          H              ; Push for later restore
    lda #&e9                                                          ; 92b1: a9 e9       ..             ; Point workspace to palette save area (&E9)
    sta nfs_workspace                                                 ; 92b3: 85 9e       ..             ; Set workspace low byte
    ldy #0                                                            ; 92b5: a0 00       ..             ; Y=0: first palette entry
    sty table_idx                                                     ; 92b7: 84 ad       ..             ; Clear table index counter
    lda vdu_screen_mode                                               ; 92b9: ad 50 03    .P.            ; Save current screen MODE to workspace
    sta (nfs_workspace),y                                             ; 92bc: 91 9e       ..             ; Store MODE at workspace[0]
    inc nfs_workspace                                                 ; 92be: e6 9e       ..             ; Advance workspace pointer past MODE byte
    lda vdu_colours                                                   ; 92c0: ad 51 03    .Q.            ; Read colour count (from &0351)
    pha                                                               ; 92c3: 48          H              ; Push for iteration count tracking
    tya                                                               ; 92c4: 98          .              ; A=0: logical colour number for OSWORD; A=&00
; &92c5 referenced 1 time by &92e4
.save_palette_entry
    sta (nfs_workspace),y                                             ; 92c5: 91 9e       ..             ; Store logical colour at workspace[0]
    ldx nfs_workspace                                                 ; 92c7: a6 9e       ..             ; X = workspace ptr low (param block addr)
    ldy nfs_workspace_hi                                              ; 92c9: a4 9f       ..             ; Y = workspace ptr high
    lda #osword_read_palette                                          ; 92cb: a9 0b       ..             ; OSWORD &0B: read palette for logical colour
    jsr osword                                                        ; 92cd: 20 f1 ff     ..            ; Read palette
    pla                                                               ; 92d0: 68          h              ; Recover colour count
    ldy #0                                                            ; 92d1: a0 00       ..             ; Y=0: access workspace[0]
    sta (nfs_workspace),y                                             ; 92d3: 91 9e       ..             ; Write colour count back to workspace[0]
    iny                                                               ; 92d5: c8          .              ; Y=1: access workspace[1] (palette result); Y=&01
    lda (nfs_workspace),y                                             ; 92d6: b1 9e       ..             ; Read palette value returned by OSWORD
    pha                                                               ; 92d8: 48          H              ; Push palette value for next iteration
    ldx nfs_workspace                                                 ; 92d9: a6 9e       ..             ; X = current workspace ptr low
    inc nfs_workspace                                                 ; 92db: e6 9e       ..             ; Advance workspace pointer
    inc table_idx                                                     ; 92dd: e6 ad       ..             ; Increment table index
    dey                                                               ; 92df: 88          .              ; Y=0 for next store; Y=&00
    lda table_idx                                                     ; 92e0: a5 ad       ..             ; Load table index as logical colour
    cpx #&f9                                                          ; 92e2: e0 f9       ..             ; Loop until workspace wraps past &F9
    bne save_palette_entry                                            ; 92e4: d0 df       ..             ; Continue for all 16 palette entries
    pla                                                               ; 92e6: 68          h              ; Discard last palette value from stack
    sty table_idx                                                     ; 92e7: 84 ad       ..             ; Reset table index to 0
    inc nfs_workspace                                                 ; 92e9: e6 9e       ..             ; Advance workspace past palette data
    jsr save_vdu_state                                                ; 92eb: 20 fa 92     ..            ; Save cursor pos and OSBYTE state values
    inc nfs_workspace                                                 ; 92ee: e6 9e       ..             ; Advance workspace past VDU state data
    pla                                                               ; 92f0: 68          h              ; Recover saved table index
    sta table_idx                                                     ; 92f1: 85 ad       ..             ; Restore table index
; &92f3 referenced 4 times by &84a3, &84cb, &84f2, &8ef1
.clear_jsr_protection
    lda saved_jsr_mask                                                ; 92f3: ad 65 0d    .e.            ; Restore LSTAT from saved OLDJSR value
    sta prot_status                                                   ; 92f6: 8d 63 0d    .c.            ; Write to protection status
    rts                                                               ; 92f9: 60          `              ; Return

; ***************************************************************************************
; Save VDU workspace state
; 
; Stores the cursor position value from &0355 into NFS workspace,
; then reads cursor position (OSBYTE &85), shadow RAM (OSBYTE &C2),
; and screen start (OSBYTE &C3) via read_vdu_osbyte, storing
; each result into consecutive workspace bytes. The JSR to
; read_vdu_osbyte_x0 is a self-calling trick: it executes
; read_vdu_osbyte twice (once for &C2, once for &C3) because the
; RTS returns to the instruction at read_vdu_osbyte_x0 itself.
; ***************************************************************************************
; &92fa referenced 1 time by &92eb
.save_vdu_state
    lda vdu_cursor_edit                                               ; 92fa: ad 55 03    .U.            ; Read cursor editing state
    sta (nfs_workspace),y                                             ; 92fd: 91 9e       ..             ; Store to workspace[Y]
    tax                                                               ; 92ff: aa          .              ; Preserve in X for OSBYTE
    jsr read_vdu_osbyte                                               ; 9300: 20 0d 93     ..            ; OSBYTE &85: read cursor position
    inc nfs_workspace                                                 ; 9303: e6 9e       ..             ; Advance workspace pointer
    tya                                                               ; 9305: 98          .              ; Y result from OSBYTE &85
    sta (nfs_workspace,x)                                             ; 9306: 81 9e       ..             ; Store Y pos to workspace (X=0)
    jsr read_vdu_osbyte_x0                                            ; 9308: 20 0b 93     ..            ; Self-call trick: executes twice
; &930b referenced 1 time by &9308
.read_vdu_osbyte_x0
    ldx #0                                                            ; 930b: a2 00       ..             ; X=0 for (zp,X) addressing
; &930d referenced 1 time by &9300
.read_vdu_osbyte
    ldy table_idx                                                     ; 930d: a4 ad       ..             ; Index into OSBYTE number table
    inc table_idx                                                     ; 930f: e6 ad       ..             ; Next table entry next time
    inc nfs_workspace                                                 ; 9311: e6 9e       ..             ; Advance workspace pointer
    lda vdu_osbyte_table,y                                            ; 9313: b9 21 93    .!.            ; Read OSBYTE number from table
    ldy #&ff                                                          ; 9316: a0 ff       ..             ; Y=&FF: read current value
    jsr osbyte                                                        ; 9318: 20 f4 ff     ..            ; Call OSBYTE
    txa                                                               ; 931b: 8a          .              ; Result in X to A
    ldx #0                                                            ; 931c: a2 00       ..             ; X=0 for indexed indirect store
    sta (nfs_workspace,x)                                             ; 931e: 81 9e       ..             ; Store result to workspace
    rts                                                               ; 9320: 60          `              ; Return after storing result

; &9321 referenced 1 time by &9313
.vdu_osbyte_table
    equb &85, &c2, &c3                                                ; 9321: 85 c2 c3    ...            ; OSBYTE &85: read cursor position; OSBYTE &C3: read screen start address
; &9324 referenced 1 time by &816c

    org &9665

    rts                                                               ; 9665: 60          `              ; RTS (end of save_vdu_state data)

    equb &8a, &48, &98, &48, &ad, &4b, &fe, &29, &e3, &0d, &51, &0d   ; 9666: 8a 48 98... .H.
    equb &8d, &4b, &fe, &ad, &4a, &fe, &a9,   4, &8d, &4d, &fe, &8d   ; 9672: 8d 4b fe... .K.
    equb &4e, &fe, &ac, &57, &0d, &c0, &86, &b0, &0b, &ad, &63, &0d   ; 967e: 4e fe ac... N..            ; Y >= &86: above dispatch range; Out of range: skip protection; Save current JSR protection mask
    equb &8d, &65, &0d,   9, &1c, &8d, &63, &0d                       ; 968a: 8d 65 0d... .e.            ; Backup to saved_jsr_mask; Set protection bits 2-4; Apply protection during dispatch
.dispatch_svc5
    equb &a9, &9b, &48, &b9, &bf, &9a, &48                            ; 9692: a9 9b 48... ..H            ; Push return addr high (&9B); High byte on stack for RTS; Load dispatch target low byte; Low byte on stack for RTS

.svc_5_unknown_irq
    rts                                                               ; 9699: 60          `              ; RTS = dispatch to PHA'd address

; ***************************************************************************************
; ADLC initialisation
; 
; Reads station ID (INTOFF side effect), performs full ADLC reset,
; checks for Tube presence (OSBYTE &EA), then falls through to
; adlc_init_workspace.
; ***************************************************************************************
; &969a referenced 1 time by &06ee[4]
.adlc_init
    bit station_id_disable_net_nmis                                   ; 969a: 2c 18 fe    ,..            ; INTOFF: read station ID, disable NMIs
    jsr adlc_full_reset                                               ; 969d: 20 70 9f     p.            ; Full ADLC hardware reset
    lda #osbyte_read_tube_presence                                    ; 96a0: a9 ea       ..             ; OSBYTE &EA: check Tube co-processor
    ldx #0                                                            ; 96a2: a2 00       ..             ; X=0 for OSBYTE
    stx econet_init_flag                                              ; 96a4: 8e 66 0d    .f.            ; Clear Econet init flag before setup
    ldy #&ff                                                          ; 96a7: a0 ff       ..             ; Y=&FF for OSBYTE
    jsr osbyte                                                        ; 96a9: 20 f4 ff     ..            ; Read Tube present flag
    stx tube_flag                                                     ; 96ac: 8e 67 0d    .g.            ; X=value of Tube present flag
    lda #osbyte_issue_service_request                                 ; 96af: a9 8f       ..             ; OSBYTE &8F: issue service request
    ldx #&0c                                                          ; 96b1: a2 0c       ..             ; X=&0C: NMI claim service
    ldy #&ff                                                          ; 96b3: a0 ff       ..             ; Y=&FF: pass to adlc_init_workspace
; ***************************************************************************************
; Initialise NMI workspace
; 
; Issues OSBYTE &8F with X=&0C (NMI claim service request) before
; copying the NMI shim. Sub-entry at &96B8 skips the service
; request for quick re-init. Then copies 32 bytes of
; NMI shim from ROM (&9FB2) to RAM (&0D00), patches the current
; ROM bank number into the shim's self-modifying code at &0D07,
; sets TX clear flag and econet_init_flag to &80, reads station ID
; from &FE18 (INTOFF side effect), stores it in the TX scout buffer,
; and re-enables NMIs by reading &FE20 (INTON side effect).
; ***************************************************************************************
.adlc_init_workspace
    jsr osbyte                                                        ; 96b5: 20 f4 ff     ..            ; Issue paged ROM service call, Reason X=12 - NMI claim
; ***************************************************************************************
; Initialise NMI workspace (skip service request)
; 
; Sub-entry of adlc_init_workspace that skips the OSBYTE &8F
; service request. Copies 32 bytes of NMI shim from ROM to
; &0D00, patches the ROM bank number, sets init flags, reads
; station ID, and re-enables NMIs.
; ***************************************************************************************
; &96b8 referenced 1 time by &06f4[4]
.init_nmi_workspace
    ldy #&20 ; ' '                                                    ; 96b8: a0 20       .              ; Copy 32 bytes of NMI shim from ROM to &0D00
; &96ba referenced 1 time by &96c1
.copy_nmi_shim
    lda listen_jmp_hi,y                                               ; 96ba: b9 b1 9f    ...            ; Read byte from NMI shim ROM source
    sta nmi_code_base,y                                               ; 96bd: 99 ff 0c    ...            ; Write to NMI shim RAM at &0D00
    dey                                                               ; 96c0: 88          .              ; Next byte (descending)
    bne copy_nmi_shim                                                 ; 96c1: d0 f7       ..             ; Loop until all 32 bytes copied
    lda romsel_copy                                                   ; 96c3: a5 f4       ..             ; Patch current ROM bank into NMI shim
    sta nmi_shim_07                                                   ; 96c5: 8d 07 0d    ...            ; Self-modifying code: ROM bank at &0D07
    lda #&80                                                          ; 96c8: a9 80       ..             ; &80 = Econet initialised
    sta tx_clear_flag                                                 ; 96ca: 8d 62 0d    .b.            ; Mark TX as complete (ready)
    sta econet_init_flag                                              ; 96cd: 8d 66 0d    .f.            ; Mark Econet as initialised
    lda station_id_disable_net_nmis                                   ; 96d0: ad 18 fe    ...            ; Read station ID (&FE18 = INTOFF side effect)
    sta tx_src_stn                                                    ; 96d3: 8d 22 0d    .".            ; Store our station ID in TX scout
    sty tx_src_net                                                    ; 96d6: 8c 23 0d    .#.            ; Y=0 after copy loop: net = local
    sty need_release_tube                                             ; 96d9: 84 98       ..             ; Clear Tube release flag
    bit video_ula_control                                             ; 96db: 2c 20 fe    , .            ; INTON: re-enable NMIs (&FE20 read side effect)
    rts                                                               ; 96de: 60          `              ; Return

; ***************************************************************************************
; NMI RX scout handler (initial byte)
; 
; Default NMI handler for incoming scout frames. Checks if the frame
; is addressed to us or is a broadcast. Installed as the NMI target
; during idle RX listen mode.
; Tests SR2 bit0 (AP = Address Present) to detect incoming data.
; Reads the first byte (destination station) from the RX FIFO and
; compares against our station ID. Reading &FE18 also disables NMIs
; (INTOFF side effect).
; ***************************************************************************************
; &96df referenced 1 time by &9fbd
.nmi_rx_scout
    lda #1                                                            ; 96df: a9 01       ..             ; A=&01: mask for SR2 bit0 (AP = Address Present)
    bit econet_control23_or_status2                                   ; 96e1: 2c a1 fe    ,..            ; BIT SR2: Z = A AND SR2 -- tests if AP is set
    beq scout_error                                                   ; 96e4: f0 38       .8             ; AP not set, no incoming data -- check for errors
    lda econet_data_continue_frame                                    ; 96e6: ad a2 fe    ...            ; Read first RX byte (destination station address)
    cmp station_id_disable_net_nmis                                   ; 96e9: cd 18 fe    ...            ; Compare to our station ID (&FE18 read = INTOFF, disables NMIs)
    beq accept_frame                                                  ; 96ec: f0 09       ..             ; Match -- accept frame
    cmp #&ff                                                          ; 96ee: c9 ff       ..             ; Check for broadcast address (&FF)
    bne scout_reject                                                  ; 96f0: d0 18       ..             ; Neither our address nor broadcast -- reject frame
    lda #&40 ; '@'                                                    ; 96f2: a9 40       .@             ; Flag &40 = broadcast frame
    sta tx_flags                                                      ; 96f4: 8d 4a 0d    .J.            ; Store broadcast flag in TX flags
; &96f7 referenced 1 time by &96ec
.accept_frame
    lda #&fc                                                          ; 96f7: a9 fc       ..             ; Install next NMI handler at &9715 (RX scout second byte)
    jmp install_nmi_handler                                           ; 96f9: 4c 11 0d    L..            ; Install next handler and RTI

; ***************************************************************************************
; RX scout second byte handler
; 
; Reads the second byte of an incoming scout (destination network).
; Checks for network match: 0 = local network (accept), &FF = broadcast
; (accept and flag), anything else = reject.
; Installs the scout data reading loop handler at &972E.
; ***************************************************************************************
.nmi_rx_scout_net
    bit econet_control23_or_status2                                   ; 96fc: 2c a1 fe    ,..            ; BIT SR2: test for RDA (bit7 = data available)
    bpl scout_error                                                   ; 96ff: 10 1d       ..             ; No RDA -- check errors
    lda econet_data_continue_frame                                    ; 9701: ad a2 fe    ...            ; Read destination network byte
    beq accept_local_net                                              ; 9704: f0 0c       ..             ; Network = 0 -- local network, accept
    eor #&ff                                                          ; 9706: 49 ff       I.             ; EOR &FF: test if network = &FF (broadcast)
    beq accept_scout_net                                              ; 9708: f0 0b       ..             ; Broadcast network -- accept
; &970a referenced 1 time by &96f0
.scout_reject
    lda #&a2                                                          ; 970a: a9 a2       ..             ; Reject: wrong network. CR1=&A2: RIE|RX_DISCONTINUE
    sta econet_control1_or_status1                                    ; 970c: 8d a0 fe    ...            ; Write CR1 to discontinue RX
    jmp install_rx_scout_handler                                      ; 970f: 4c 0d 9a    L..            ; Return to idle scout listening

; &9712 referenced 1 time by &9704
.accept_local_net
    sta tx_flags                                                      ; 9712: 8d 4a 0d    .J.            ; Network = 0 (local): clear tx_flags
; &9715 referenced 1 time by &9708
.accept_scout_net
    sta port_buf_len                                                  ; 9715: 85 a2       ..             ; Store Y offset for scout data buffer
    lda #&2e ; '.'                                                    ; 9717: a9 2e       ..             ; Install scout data reading loop at &972E
    ldy #&97                                                          ; 9719: a0 97       ..             ; High byte of scout data handler
    jmp set_nmi_vector                                                ; 971b: 4c 0e 0d    L..            ; Install scout data loop and RTI

; ***************************************************************************************
; Scout error/discard handler
; 
; Reached when the scout data loop sees no RDA (BPL at &9733) or
; when scout completion finds unexpected SR2 state.
; If SR2 & &81 is non-zero (AP or RDA still active), performs full
; ADLC reset and discards. If zero (clean end), discards via &9A0A.
; This path is a common landing for any unexpected ADLC state during
; scout reception.
; ***************************************************************************************
; &971e referenced 5 times by &96e4, &96ff, &9733, &9767, &9769
.scout_error
    lda econet_control23_or_status2                                   ; 971e: ad a1 fe    ...            ; Read SR2
    and #&81                                                          ; 9721: 29 81       ).             ; Test AP (b0) | RDA (b7)
    beq scout_discard                                                 ; 9723: f0 06       ..             ; Neither set -- clean end, discard via &972B
    jsr adlc_full_reset                                               ; 9725: 20 70 9f     p.            ; Unexpected data/status: full ADLC reset
    jmp install_rx_scout_handler                                      ; 9728: 4c 0d 9a    L..            ; Discard and return to idle

; &972b referenced 1 time by &9723
.scout_discard
    jmp discard_listen                                                ; 972b: 4c 0a 9a    L..            ; Gentle discard: RX_DISCONTINUE

; ***************************************************************************************
; Scout data reading loop
; 
; Reads the body of a scout frame, two bytes per iteration. Stores
; bytes at &0D3D+Y (scout buffer: src_stn, src_net, ctrl, port, ...).
; Between each pair it checks SR2:
;   - At entry (&9730): SR2 read, BPL tests RDA (bit7)
;     - No RDA (BPL) -> error (&971E)
;     - RDA set (BMI) -> read byte
;   - After first byte (&973C): full SR2 tested
;     - SR2 non-zero (BNE) -> scout completion (&9758)
;       This is the FV detection point: when FV is set (by inline refill
;       of the last byte during the preceding RX FIFO read), SR2 is
;       non-zero and the branch is taken.
;     - SR2 = 0 -> read second byte and loop
;   - After second byte (&9750): re-test full SR2
;     - SR2 non-zero (BNE) -> loop back to &9733
;     - SR2 = 0 -> RTI, wait for next NMI
; The loop ends at Y=&0C (12 bytes max in scout buffer).
; ***************************************************************************************
.scout_data_loop
    ldy port_buf_len                                                  ; 972e: a4 a2       ..             ; Y = buffer offset
    lda econet_control23_or_status2                                   ; 9730: ad a1 fe    ...            ; Read SR2
; &9733 referenced 1 time by &9753
.scout_loop_rda
    bpl scout_error                                                   ; 9733: 10 e9       ..             ; No RDA -- error handler &971E
    lda econet_data_continue_frame                                    ; 9735: ad a2 fe    ...            ; Read data byte from RX FIFO
    sta rx_src_stn,y                                                  ; 9738: 99 3d 0d    .=.            ; Store at &0D3D+Y (scout buffer)
    iny                                                               ; 973b: c8          .              ; Advance buffer index
    lda econet_control23_or_status2                                   ; 973c: ad a1 fe    ...            ; Read SR2 again (FV detection point)
    bmi scout_loop_second                                             ; 973f: 30 02       0.             ; RDA set -- more data, read second byte
    bne scout_complete                                                ; 9741: d0 15       ..             ; SR2 non-zero (FV or other) -- scout completion
; &9743 referenced 1 time by &973f
.scout_loop_second
    lda econet_data_continue_frame                                    ; 9743: ad a2 fe    ...            ; Read second byte of pair
    sta rx_src_stn,y                                                  ; 9746: 99 3d 0d    .=.            ; Store at &0D3D+Y
    iny                                                               ; 9749: c8          .              ; Advance and check buffer limit
    cpy #&0c                                                          ; 974a: c0 0c       ..             ; Copied all 12 scout bytes?
    beq scout_complete                                                ; 974c: f0 0a       ..             ; Buffer full (Y=12) -- force completion
    sty port_buf_len                                                  ; 974e: 84 a2       ..             ; Save final buffer offset
    lda econet_control23_or_status2                                   ; 9750: ad a1 fe    ...            ; Read SR2 for next pair
    bne scout_loop_rda                                                ; 9753: d0 de       ..             ; SR2 non-zero -- loop back for more bytes
    jmp nmi_rti                                                       ; 9755: 4c 14 0d    L..            ; SR2 = 0 -- RTI, wait for next NMI

; ***************************************************************************************
; Scout completion handler
; 
; Reached from the scout data loop when SR2 is non-zero (FV detected).
; Disables PSE to allow individual SR2 bit testing:
;   CR1=&00 (clear all enables)
;   CR2=&84 (RDA_SUPPRESS_FV | FC_TDRA) -- no PSE, no CLR bits
; Then checks FV (bit1) and RDA (bit7):
;   - No FV (BEQ) -> error &971E (not a valid frame end)
;   - FV set, no RDA (BPL) -> error &971E (missing last byte)
;   - FV set, RDA set -> read last byte, process scout
; After reading the last byte, the complete scout buffer (&0D3D-&0D48)
; contains: src_stn, src_net, ctrl, port [, extra_data...].
; The port byte at &0D40 determines further processing:
;   - Port = 0 -> immediate operation (&9A46)
;   - Port non-zero -> check if it matches an open receive block
; ***************************************************************************************
; &9758 referenced 2 times by &9741, &974c
.scout_complete
    lda #0                                                            ; 9758: a9 00       ..             ; CR1=&00: disable all interrupts
    sta econet_control1_or_status1                                    ; 975a: 8d a0 fe    ...            ; Write CR1
    lda #&84                                                          ; 975d: a9 84       ..             ; CR2=&84: disable PSE, enable RDA_SUPPRESS_FV
    sta econet_control23_or_status2                                   ; 975f: 8d a1 fe    ...            ; Write CR2
    lda #2                                                            ; 9762: a9 02       ..             ; A=&02: FV mask for SR2 bit1
    bit econet_control23_or_status2                                   ; 9764: 2c a1 fe    ,..            ; BIT SR2: test FV (Z) and RDA (N)
    beq scout_error                                                   ; 9767: f0 b5       ..             ; No FV -- not a valid frame end, error
    bpl scout_error                                                   ; 9769: 10 b3       ..             ; FV set but no RDA -- missing last byte, error
    lda econet_data_continue_frame                                    ; 976b: ad a2 fe    ...            ; Read last byte from RX FIFO
    sta rx_src_stn,y                                                  ; 976e: 99 3d 0d    .=.            ; Store last byte at &0D3D+Y
    lda #&44 ; 'D'                                                    ; 9771: a9 44       .D             ; CR1=&44: RX_RESET | TIE (switch to TX for ACK)
    sta econet_control1_or_status1                                    ; 9773: 8d a0 fe    ...            ; Write CR1: switch to TX mode
    sec                                                               ; 9776: 38          8              ; Set bit7 of need_release_tube flag
    ror need_release_tube                                             ; 9777: 66 98       f.             ; Rotate C=1 into bit7: mark Tube release needed
    lda rx_port                                                       ; 9779: ad 40 0d    .@.            ; Check port byte: 0 = immediate op, non-zero = data transfer
    bne scout_match_port                                              ; 977c: d0 03       ..             ; Port non-zero -- look for matching receive block
.scout_no_match
    jmp immediate_op                                                  ; 977e: 4c 68 9a    Lh.            ; Port = 0 -- immediate operation handler

; &9781 referenced 1 time by &977c
.scout_match_port
    bit tx_flags                                                      ; 9781: 2c 4a 0d    ,J.            ; Check if broadcast (bit6 of tx_flags)
    bvc scan_port_list                                                ; 9784: 50 05       P.             ; Not broadcast -- skip CR2 setup
    lda #7                                                            ; 9786: a9 07       ..             ; CR2=&07: broadcast prep
    sta econet_control23_or_status2                                   ; 9788: 8d a1 fe    ...            ; Write CR2: broadcast frame prep
; &978b referenced 1 time by &9784
.scan_port_list
    bit rx_flags                                                      ; 978b: 2c 64 0d    ,d.            ; Check if RX port list active (bit7)
    bpl try_nfs_port_list                                             ; 978e: 10 3e       .>             ; No active ports -- try NFS workspace
    lda #&c0                                                          ; 9790: a9 c0       ..             ; Start scanning port list at page &C0
    ldy #0                                                            ; 9792: a0 00       ..             ; Y=0: start offset within each port slot
; &9794 referenced 1 time by &97d7
.scan_nfs_port_list
    sta port_ws_offset                                                ; 9794: 85 a6       ..             ; Store page to workspace pointer low
    sty rx_buf_offset                                                 ; 9796: 84 a7       ..             ; Store page high byte for slot scanning
; &9798 referenced 1 time by &97c9
.check_port_slot
    ldy #0                                                            ; 9798: a0 00       ..             ; Y=0: read control byte from start of slot
.scout_ctrl_check
    lda (port_ws_offset),y                                            ; 979a: b1 a6       ..             ; Read port control byte from slot
    beq discard_no_match                                              ; 979c: f0 2d       .-             ; Zero = end of port list, no match
    cmp #&7f                                                          ; 979e: c9 7f       ..             ; &7F = any-port wildcard
    bne next_port_slot                                                ; 97a0: d0 1c       ..             ; Not wildcard -- check specific port match
    iny                                                               ; 97a2: c8          .              ; Y=1: advance to port byte in slot
    lda (port_ws_offset),y                                            ; 97a3: b1 a6       ..             ; Read port number from slot (offset 1)
    beq check_station_filter                                          ; 97a5: f0 05       ..             ; Zero port in slot = match any port
    cmp rx_port                                                       ; 97a7: cd 40 0d    .@.            ; Check if port matches this slot
    bne next_port_slot                                                ; 97aa: d0 12       ..             ; Port mismatch -- try next slot
; &97ac referenced 1 time by &97a5
.check_station_filter
    iny                                                               ; 97ac: c8          .              ; Y=2: advance to station byte
    lda (port_ws_offset),y                                            ; 97ad: b1 a6       ..             ; Read station filter from slot (offset 2)
    beq port_match_found                                              ; 97af: f0 28       .(             ; Zero station = match any station, accept
    cmp rx_src_stn                                                    ; 97b1: cd 3d 0d    .=.            ; Check if source station matches
    bne next_port_slot                                                ; 97b4: d0 08       ..             ; Station mismatch -- try next slot
.scout_port_match
    iny                                                               ; 97b6: c8          .              ; Y=3: advance to network byte
    lda (port_ws_offset),y                                            ; 97b7: b1 a6       ..             ; Read network filter from slot (offset 3)
    cmp rx_src_net                                                    ; 97b9: cd 3e 0d    .>.            ; Check if source network matches
    beq port_match_found                                              ; 97bc: f0 1b       ..             ; Network matches or zero = accept
; &97be referenced 3 times by &97a0, &97aa, &97b4
.next_port_slot
    lda rx_buf_offset                                                 ; 97be: a5 a7       ..             ; Check if NFS workspace search pending
    beq try_nfs_port_list                                             ; 97c0: f0 0c       ..             ; No NFS workspace -- try fallback path
    lda port_ws_offset                                                ; 97c2: a5 a6       ..             ; Load current slot base address
    clc                                                               ; 97c4: 18          .              ; CLC for 12-byte slot advance
    adc #&0c                                                          ; 97c5: 69 0c       i.             ; Advance to next 12-byte port slot
    sta port_ws_offset                                                ; 97c7: 85 a6       ..             ; Update workspace pointer to next slot
    bcc check_port_slot                                               ; 97c9: 90 cd       ..             ; Always branches (page &C0 won't overflow)
; &97cb referenced 2 times by &979c, &97d1
.discard_no_match
    jmp nmi_error_dispatch                                            ; 97cb: 4c 57 98    LW.            ; No match found -- discard frame

; &97ce referenced 2 times by &978e, &97c0
.try_nfs_port_list
    bit rx_flags                                                      ; 97ce: 2c 64 0d    ,d.            ; Try NFS workspace if paged list exhausted
    bvc discard_no_match                                              ; 97d1: 50 f8       P.             ; No NFS workspace RX (bit6 clear) -- discard
    lda #0                                                            ; 97d3: a9 00       ..             ; NFS workspace starts at offset 0 in page
    ldy nfs_workspace_hi                                              ; 97d5: a4 9f       ..             ; NFS workspace high byte for port list
    bne scan_nfs_port_list                                            ; 97d7: d0 bb       ..             ; Scan NFS workspace port list
; &97d9 referenced 3 times by &97af, &97bc, &9ac9
.port_match_found
    lda #3                                                            ; 97d9: a9 03       ..             ; Match found: set scout_status = 3
    sta scout_status                                                  ; 97db: 8d 5c 0d    .\.            ; Record match for completion handler
    jsr tx_calc_transfer                                              ; 97de: 20 fd 9e     ..            ; Calculate transfer parameters
    bcc nmi_error_dispatch                                            ; 97e1: 90 74       .t             ; C=0: no Tube claimed -- discard
    bit tx_flags                                                      ; 97e3: 2c 4a 0d    ,J.            ; Check broadcast flag for ACK path
    bvc send_data_rx_ack                                              ; 97e6: 50 03       P.             ; Not broadcast -- normal ACK path
    jmp copy_scout_to_buffer                                          ; 97e8: 4c 14 9a    L..            ; Broadcast: different completion path

; &97eb referenced 2 times by &97e6, &9abe
.send_data_rx_ack
    lda #&44 ; 'D'                                                    ; 97eb: a9 44       .D             ; CR1=&44: RX_RESET | TIE
    sta econet_control1_or_status1                                    ; 97ed: 8d a0 fe    ...            ; Write CR1: TX mode for ACK
    lda #&a7                                                          ; 97f0: a9 a7       ..             ; CR2=&A7: RTS | CLR_TX_ST | FC_TDRA | PSE
    sta econet_control23_or_status2                                   ; 97f2: 8d a1 fe    ...            ; Write CR2: enable TX with PSE
    lda #&fc                                                          ; 97f5: a9 fc       ..             ; Install data_rx_setup at &97FC
    ldy #&97                                                          ; 97f7: a0 97       ..             ; High byte of data_rx_setup handler
    jmp ack_tx_write_dest                                             ; 97f9: 4c 29 99    L).            ; Send ACK with data_rx_setup as next NMI

.data_rx_setup
    lda #&82                                                          ; 97fc: a9 82       ..             ; CR1=&82: TX_RESET | RIE (switch to RX for data frame)
    sta econet_control1_or_status1                                    ; 97fe: 8d a0 fe    ...            ; Write CR1: switch to RX for data frame
    lda #8                                                            ; 9801: a9 08       ..             ; Install nmi_data_rx at &9808
    ldy #&98                                                          ; 9803: a0 98       ..             ; Y=&98: NMI handler high byte
    jmp set_nmi_vector                                                ; 9805: 4c 0e 0d    L..            ; Install nmi_data_rx and return from NMI

; ***************************************************************************************
; Data frame RX handler (four-way handshake)
; 
; Receives the data frame after the scout ACK has been sent.
; First checks AP (Address Present) for the start of the data frame.
; Reads and validates the first two address bytes (dest_stn, dest_net)
; against our station address, then installs continuation handlers
; to read the remaining data payload into the open port buffer.
; 
; Handler chain: &9808 (AP+addr check) -> &981C (net=0 check) ->
; &9832 (skip ctrl+port) -> &9865 (bulk data read) -> &9899 (completion)
; ***************************************************************************************
.nmi_data_rx
    lda #1                                                            ; 9808: a9 01       ..             ; A=&01: mask for AP (Address Present)
    bit econet_control23_or_status2                                   ; 980a: 2c a1 fe    ,..            ; BIT SR2: test AP bit
    beq nmi_error_dispatch                                            ; 980d: f0 48       .H             ; No AP: wrong frame or error
    lda econet_data_continue_frame                                    ; 980f: ad a2 fe    ...            ; Read first byte (dest station)
    cmp station_id_disable_net_nmis                                   ; 9812: cd 18 fe    ...            ; Compare to our station ID (INTOFF)
    bne nmi_error_dispatch                                            ; 9815: d0 40       .@             ; Not for us: error path
    lda #&1c                                                          ; 9817: a9 1c       ..             ; Install net check handler at &981C
    jmp install_nmi_handler                                           ; 9819: 4c 11 0d    L..            ; Set NMI vector via RAM shim

.nmi_data_rx_net
    bit econet_control23_or_status2                                   ; 981c: 2c a1 fe    ,..            ; Validate source network = 0
    bpl nmi_error_dispatch                                            ; 981f: 10 36       .6             ; SR2 bit7 clear: no data ready -- error
    lda econet_data_continue_frame                                    ; 9821: ad a2 fe    ...            ; Read dest network byte
    bne nmi_error_dispatch                                            ; 9824: d0 31       .1             ; Network != 0: wrong network -- error
    lda #&32 ; '2'                                                    ; 9826: a9 32       .2             ; Install skip handler at &9832
    ldy #&98                                                          ; 9828: a0 98       ..             ; High byte of &9832 handler
    bit econet_control1_or_status1                                    ; 982a: 2c a0 fe    ,..            ; SR1 bit7: IRQ, data already waiting
    bmi nmi_data_rx_skip                                              ; 982d: 30 03       0.             ; Data ready: skip directly, no RTI
    jmp set_nmi_vector                                                ; 982f: 4c 0e 0d    L..            ; Install handler and return via RTI

; &9832 referenced 1 time by &982d
.nmi_data_rx_skip
    bit econet_control23_or_status2                                   ; 9832: 2c a1 fe    ,..            ; Skip control and port bytes (already known from scout)
    bpl nmi_error_dispatch                                            ; 9835: 10 20       .              ; SR2 bit7 clear: error
    lda econet_data_continue_frame                                    ; 9837: ad a2 fe    ...            ; Discard control byte
    lda econet_data_continue_frame                                    ; 983a: ad a2 fe    ...            ; Discard port byte
; ***************************************************************************************
; Install data RX bulk or Tube handler
; 
; Selects either the normal bulk RX handler (&9865) or the Tube
; RX handler (&98C2) based on the Tube transfer flag in tx_flags,
; and installs the appropriate NMI handler.
; ***************************************************************************************
; &983d referenced 1 time by &9ed1
.install_data_rx_handler
    lda #2                                                            ; 983d: a9 02       ..             ; A=2: Tube transfer flag mask
    bit tx_flags                                                      ; 983f: 2c 4a 0d    ,J.            ; Check if Tube transfer active
    bne install_tube_rx                                               ; 9842: d0 0c       ..             ; Tube active: use Tube RX path
    lda #&65 ; 'e'                                                    ; 9844: a9 65       .e             ; Install bulk read at &9865
    ldy #&98                                                          ; 9846: a0 98       ..             ; High byte of &9865 handler
    bit econet_control1_or_status1                                    ; 9848: 2c a0 fe    ,..            ; SR1 bit7: more data already waiting?
    bmi nmi_data_rx_bulk                                              ; 984b: 30 18       0.             ; Yes: enter bulk read directly
    jmp set_nmi_vector                                                ; 984d: 4c 0e 0d    L..            ; No: install handler and RTI

; &9850 referenced 1 time by &9842
.install_tube_rx
    lda #&c2                                                          ; 9850: a9 c2       ..             ; Tube: install Tube RX at &98C2
    ldy #&98                                                          ; 9852: a0 98       ..             ; High byte of &98C2 handler
    jmp set_nmi_vector                                                ; 9854: 4c 0e 0d    L..            ; Install Tube handler and RTI

; ***************************************************************************************
; NMI error handler dispatch
; 
; Common error/abort entry used by 12 call sites. Checks
; tx_flags bit 7: if clear, does a full ADLC reset and returns
; to idle listen (RX error path); if set, jumps to tx_result_fail
; (TX not-listening path).
; ***************************************************************************************
; &9857 referenced 12 times by &97cb, &97e1, &980d, &9815, &981f, &9824, &9835, &9878, &98aa, &98b0, &996d, &9a98
.nmi_error_dispatch
    lda tx_flags                                                      ; 9857: ad 4a 0d    .J.            ; Check tx_flags for error path
    bpl rx_error                                                      ; 985a: 10 03       ..             ; Bit7 clear: RX error path
    jmp tx_result_fail                                                ; 985c: 4c df 9e    L..            ; Bit7 set: TX result = not listening

; &985f referenced 1 time by &985a
.rx_error
.rx_error_reset
    jsr adlc_full_reset                                               ; 985f: 20 70 9f     p.            ; Full ADLC reset on RX error
    jmp discard_reset_listen                                          ; 9862: 4c fd 99    L..            ; Discard and return to idle listen

; ***************************************************************************************
; Data frame bulk read loop
; 
; Reads data payload bytes from the RX FIFO and stores them into
; the open port buffer at (open_port_buf),Y. Reads bytes in pairs
; (like the scout data loop), checking SR2 between each pair.
; SR2 non-zero (FV or other) -> frame completion at &9899.
; SR2 = 0 -> RTI, wait for next NMI to continue.
; ***************************************************************************************
; &9865 referenced 1 time by &984b
.nmi_data_rx_bulk
    ldy port_buf_len                                                  ; 9865: a4 a2       ..             ; Y = buffer offset, resume from last position
    lda econet_control23_or_status2                                   ; 9867: ad a1 fe    ...            ; Read SR2 for next pair
; &986a referenced 1 time by &9894
.data_rx_loop
    bpl data_rx_complete                                              ; 986a: 10 2d       .-             ; SR2 bit7 clear: frame complete (FV)
    lda econet_data_continue_frame                                    ; 986c: ad a2 fe    ...            ; Read first byte of pair from RX FIFO
    sta (open_port_buf),y                                             ; 986f: 91 a4       ..             ; Store byte to buffer
    iny                                                               ; 9871: c8          .              ; Advance buffer offset
    bne read_sr2_between_pairs                                        ; 9872: d0 06       ..             ; Y != 0: no page boundary crossing
    inc open_port_buf_hi                                              ; 9874: e6 a5       ..             ; Crossed page: increment buffer high byte
    dec port_buf_len_hi                                               ; 9876: c6 a3       ..             ; Decrement remaining page count
    beq nmi_error_dispatch                                            ; 9878: f0 dd       ..             ; No pages left: handle as complete
; &987a referenced 1 time by &9872
.read_sr2_between_pairs
    lda econet_control23_or_status2                                   ; 987a: ad a1 fe    ...            ; Read SR2 between byte pairs
    bmi read_second_rx_byte                                           ; 987d: 30 02       0.             ; SR2 bit7 set: more data available
    bne data_rx_complete                                              ; 987f: d0 18       ..             ; SR2 non-zero, bit7 clear: frame done
; &9881 referenced 1 time by &987d
.read_second_rx_byte
    lda econet_data_continue_frame                                    ; 9881: ad a2 fe    ...            ; Read second byte of pair from RX FIFO
    sta (open_port_buf),y                                             ; 9884: 91 a4       ..             ; Store byte to buffer
    iny                                                               ; 9886: c8          .              ; Advance buffer offset
    sty port_buf_len                                                  ; 9887: 84 a2       ..             ; Save updated buffer position
    bne check_sr2_loop_again                                          ; 9889: d0 06       ..             ; Y != 0: no page boundary crossing
    inc open_port_buf_hi                                              ; 988b: e6 a5       ..             ; Crossed page: increment buffer high byte
    dec port_buf_len_hi                                               ; 988d: c6 a3       ..             ; Decrement remaining page count
    beq data_rx_complete                                              ; 988f: f0 08       ..             ; No pages left: frame complete
; &9891 referenced 1 time by &9889
.check_sr2_loop_again
    lda econet_control23_or_status2                                   ; 9891: ad a1 fe    ...            ; Read SR2 for next iteration
    bne data_rx_loop                                                  ; 9894: d0 d4       ..             ; SR2 non-zero: more data, loop back
    jmp nmi_rti                                                       ; 9896: 4c 14 0d    L..            ; SR2=0: no more data yet, wait for NMI

; ***************************************************************************************
; Data frame completion
; 
; Reached when SR2 non-zero during data RX (FV detected).
; Same pattern as scout completion (&9758): disables PSE (CR2=&84,
; CR1=&00), then tests FV and RDA. If FV+RDA, reads the last byte.
; If extra data available and buffer space remains, stores it.
; Proceeds to send the final ACK via &9910.
; ***************************************************************************************
; &9899 referenced 3 times by &986a, &987f, &988f
.data_rx_complete
    lda #&84                                                          ; 9899: a9 84       ..             ; CR2=&84: disable PSE for bit testing
    sta econet_control23_or_status2                                   ; 989b: 8d a1 fe    ...            ; Write CR2
    lda #0                                                            ; 989e: a9 00       ..             ; CR1=&00: disable all interrupts
    sta econet_control1_or_status1                                    ; 98a0: 8d a0 fe    ...            ; Write CR1
    sty port_buf_len                                                  ; 98a3: 84 a2       ..             ; Save Y (byte count from data RX loop)
    lda #2                                                            ; 98a5: a9 02       ..             ; A=&02: FV mask
    bit econet_control23_or_status2                                   ; 98a7: 2c a1 fe    ,..            ; BIT SR2: test FV (Z) and RDA (N)
    beq nmi_error_dispatch                                            ; 98aa: f0 ab       ..             ; No FV -- error
    bpl send_ack                                                      ; 98ac: 10 11       ..             ; FV set, no RDA -- proceed to ACK
    lda port_buf_len_hi                                               ; 98ae: a5 a3       ..             ; Check if buffer space remains
; &98b0 referenced 3 times by &98cd, &98f4, &9900
.read_last_rx_byte
    beq nmi_error_dispatch                                            ; 98b0: f0 a5       ..             ; No buffer space: error/discard frame
    lda econet_data_continue_frame                                    ; 98b2: ad a2 fe    ...            ; FV+RDA: read and store last data byte
    ldy port_buf_len                                                  ; 98b5: a4 a2       ..             ; Y = current buffer write offset
    sta (open_port_buf),y                                             ; 98b7: 91 a4       ..             ; Store last byte in port receive buffer
    inc port_buf_len                                                  ; 98b9: e6 a2       ..             ; Advance buffer write offset
    bne send_ack                                                      ; 98bb: d0 02       ..             ; No page wrap: proceed to send ACK
    inc open_port_buf_hi                                              ; 98bd: e6 a5       ..             ; Page boundary: advance buffer page
; &98bf referenced 2 times by &98ac, &98bb
.send_ack
    jmp ack_tx                                                        ; 98bf: 4c 10 99    L..            ; Send ACK frame to complete handshake

.nmi_data_rx_tube
    lda econet_control23_or_status2                                   ; 98c2: ad a1 fe    ...            ; Read SR2 for Tube data receive path
; &98c5 referenced 1 time by &98e0
.rx_tube_data
    bpl data_rx_tube_complete                                         ; 98c5: 10 1e       ..             ; RDA clear: no more data, frame complete
    lda econet_data_continue_frame                                    ; 98c7: ad a2 fe    ...            ; Read data byte from ADLC RX FIFO
    jsr inc_buf_counter_32                                            ; 98ca: 20 59 9a     Y.            ; Check buffer limits and transfer size
    beq read_last_rx_byte                                             ; 98cd: f0 e1       ..             ; Zero: buffer full, handle as error
    sta tube_data_register_3                                          ; 98cf: 8d e5 fe    ...            ; Send byte to Tube data register 3
    lda econet_data_continue_frame                                    ; 98d2: ad a2 fe    ...            ; Read second data byte (paired transfer)
    sta tube_data_register_3                                          ; 98d5: 8d e5 fe    ...            ; Send second byte to Tube
    jsr inc_buf_counter_32                                            ; 98d8: 20 59 9a     Y.            ; Check limits after byte pair
    beq data_rx_tube_complete                                         ; 98db: f0 08       ..             ; Zero: Tube transfer complete
    lda econet_control23_or_status2                                   ; 98dd: ad a1 fe    ...            ; Re-read SR2 for next byte pair
    bne rx_tube_data                                                  ; 98e0: d0 e3       ..             ; More data available: continue loop
.data_rx_tube_error
    jmp nmi_rti                                                       ; 98e2: 4c 14 0d    L..            ; Unexpected end: return from NMI

; &98e5 referenced 2 times by &98c5, &98db
.data_rx_tube_complete
    lda #0                                                            ; 98e5: a9 00       ..             ; CR1=&00: disable all interrupts
    sta econet_control1_or_status1                                    ; 98e7: 8d a0 fe    ...            ; Write CR1 for individual bit testing
    lda #&84                                                          ; 98ea: a9 84       ..             ; CR2=&84: disable PSE
    sta econet_control23_or_status2                                   ; 98ec: 8d a1 fe    ...            ; Write CR2: same pattern as main path
    lda #2                                                            ; 98ef: a9 02       ..             ; A=&02: FV mask for Tube completion
    bit econet_control23_or_status2                                   ; 98f1: 2c a1 fe    ,..            ; BIT SR2: test FV (Z) and RDA (N)
    beq read_last_rx_byte                                             ; 98f4: f0 ba       ..             ; No FV: incomplete frame, error
    bpl ack_tx                                                        ; 98f6: 10 18       ..             ; FV set, no RDA: proceed to ACK
    lda port_buf_len                                                  ; 98f8: a5 a2       ..             ; Check if any buffer was allocated
    ora port_buf_len_hi                                               ; 98fa: 05 a3       ..             ; OR all 4 buffer pointer bytes together
    ora open_port_buf                                                 ; 98fc: 05 a4       ..             ; Check buffer low byte
    ora open_port_buf_hi                                              ; 98fe: 05 a5       ..             ; Check buffer high byte
    beq read_last_rx_byte                                             ; 9900: f0 ae       ..             ; All zero (null buffer): error
    lda econet_data_continue_frame                                    ; 9902: ad a2 fe    ...            ; Read extra trailing byte from FIFO
    sta rx_extra_byte                                                 ; 9905: 8d 5d 0d    .].            ; Save extra byte at &0D5D for later use
    lda #&20 ; ' '                                                    ; 9908: a9 20       .              ; Bit5 = extra data byte available flag
    ora tx_flags                                                      ; 990a: 0d 4a 0d    .J.            ; Set extra byte flag in tx_flags
    sta tx_flags                                                      ; 990d: 8d 4a 0d    .J.            ; Store updated flags
; ***************************************************************************************
; ACK transmission
; 
; Sends a scout ACK or final ACK frame as part of the four-way handshake.
; If bit7 of &0D4A is set, this is a final ACK -> completion (&9EDB).
; Otherwise, configures for TX (CR1=&44, CR2=&A7) and sends the ACK
; frame (dst_stn, dst_net from &0D3D, src_stn from &FE18, src_net=0).
; The ACK frame has no data payload -- just address bytes.
; 
; After writing the address bytes to the TX FIFO, installs the next
; NMI handler from &0D4B/&0D4C (saved by the scout/data RX handler)
; and sends TX_LAST_DATA (CR2=&3F) to close the frame.
; ***************************************************************************************
; &9910 referenced 2 times by &98bf, &98f6
.ack_tx
    lda tx_flags                                                      ; 9910: ad 4a 0d    .J.            ; Load TX flags to check ACK type
    bpl ack_tx_configure                                              ; 9913: 10 06       ..             ; Bit7 clear: normal scout ACK
    jsr advance_rx_buffer_ptr                                         ; 9915: 20 70 99     p.            ; Final ACK: call completion handler
    jmp tx_result_ok                                                  ; 9918: 4c db 9e    L..            ; Jump to TX success result

; &991b referenced 1 time by &9913
.ack_tx_configure
    lda #&44 ; 'D'                                                    ; 991b: a9 44       .D             ; CR1=&44: RX_RESET | TIE (switch to TX mode)
    sta econet_control1_or_status1                                    ; 991d: 8d a0 fe    ...            ; Write CR1: switch to TX mode
    lda #&a7                                                          ; 9920: a9 a7       ..             ; CR2=&A7: RTS|CLR_TX_ST|FC_TDRA|2_1_BYTE|PSE
    sta econet_control23_or_status2                                   ; 9922: 8d a1 fe    ...            ; Write CR2: enable TX with status clear
    lda #&b7                                                          ; 9925: a9 b7       ..             ; Install saved next handler (&99B7 for scout ACK)
    ldy #&99                                                          ; 9927: a0 99       ..             ; High byte of post-ACK handler
; &9929 referenced 2 times by &97f9, &9b06
.ack_tx_write_dest
    sta nmi_next_lo                                                   ; 9929: 8d 4b 0d    .K.            ; Store next handler low byte
    sty nmi_next_hi                                                   ; 992c: 8c 4c 0d    .L.            ; Store next handler high byte
    lda rx_src_stn                                                    ; 992f: ad 3d 0d    .=.            ; Load dest station from RX scout buffer
    bit econet_control1_or_status1                                    ; 9932: 2c a0 fe    ,..            ; BIT SR1: test TDRA (V=bit6)
    bvc dispatch_nmi_error                                            ; 9935: 50 36       P6             ; TDRA not ready -- error
    sta econet_data_continue_frame                                    ; 9937: 8d a2 fe    ...            ; Write dest station to TX FIFO
    lda rx_src_net                                                    ; 993a: ad 3e 0d    .>.            ; Write dest network to TX FIFO
    sta econet_data_continue_frame                                    ; 993d: 8d a2 fe    ...            ; Write dest net byte to FIFO
    lda #&47 ; 'G'                                                    ; 9940: a9 47       .G             ; Install handler at &9992 (write src addr)
    ldy #&99                                                          ; 9942: a0 99       ..             ; High byte of nmi_ack_tx_src
    jmp set_nmi_vector                                                ; 9944: 4c 0e 0d    L..            ; Set NMI vector to ack_tx_src handler

; ***************************************************************************************
; ACK TX continuation
; 
; Writes source station and network to TX FIFO, completing the 4-byte
; ACK frame. Then sends TX_LAST_DATA (CR2=&3F) to close the frame.
; ***************************************************************************************
.nmi_ack_tx_src
    lda station_id_disable_net_nmis                                   ; 9947: ad 18 fe    ...            ; Load our station ID (also INTOFF)
    bit econet_control1_or_status1                                    ; 994a: 2c a0 fe    ,..            ; BIT SR1: test TDRA
    bvc dispatch_nmi_error                                            ; 994d: 50 1e       P.             ; TDRA not ready -- error
    sta econet_data_continue_frame                                    ; 994f: 8d a2 fe    ...            ; Write our station to TX FIFO
    lda #0                                                            ; 9952: a9 00       ..             ; Write network=0 to TX FIFO
    sta econet_data_continue_frame                                    ; 9954: 8d a2 fe    ...            ; Write network=0 (local) to TX FIFO
    lda tx_flags                                                      ; 9957: ad 4a 0d    .J.            ; Check tx_flags for data phase
    bmi start_data_tx                                                 ; 995a: 30 0e       0.             ; bit7 set: start data TX phase
    lda #&3f ; '?'                                                    ; 995c: a9 3f       .?             ; CR2=&3F: TX_LAST_DATA | CLR_RX_ST | FLAG_IDLE | FC_TDRA | 2_1_BYTE | PSE
; ***************************************************************************************
; Post-ACK scout processing
; 
; Called after the scout ACK has been transmitted. Processes the
; received scout data stored in the buffer at &0D3D-&0D48.
; Checks the port byte (&0D40) against open receive blocks to
; find a matching listener. If a match is found, sets up the
; data RX handler chain for the four-way handshake data phase.
; If no match, discards the frame.
; ***************************************************************************************
.post_ack_scout
    sta econet_control23_or_status2                                   ; 995e: 8d a1 fe    ...            ; Write CR2 to clear status after ACK TX
    lda nmi_next_lo                                                   ; 9961: ad 4b 0d    .K.            ; Install saved handler from &0D4B/&0D4C
    ldy nmi_next_hi                                                   ; 9964: ac 4c 0d    .L.            ; Load saved next handler high byte
    jmp set_nmi_vector                                                ; 9967: 4c 0e 0d    L..            ; Install next NMI handler

; &996a referenced 1 time by &995a
.start_data_tx
    jmp data_tx_begin                                                 ; 996a: 4c e6 9d    L..            ; Jump to start data TX phase

; &996d referenced 2 times by &9935, &994d
.dispatch_nmi_error
    jmp nmi_error_dispatch                                            ; 996d: 4c 57 98    LW.            ; Jump to error handler

; ***************************************************************************************
; Advance RX buffer pointer after transfer
; 
; Adds the transfer count to the RXCB buffer pointer (4-byte
; addition). If a Tube transfer is active, re-claims the Tube
; address and sends the extra RX byte via R3, incrementing the
; Tube pointer by 1.
; ***************************************************************************************
; &9970 referenced 2 times by &9915, &99c6
.advance_rx_buffer_ptr
    lda #2                                                            ; 9970: a9 02       ..             ; A=2: test bit1 of tx_flags
    bit tx_flags                                                      ; 9972: 2c 4a 0d    ,J.            ; BIT tx_flags: check data transfer bit
    beq return_10                                                     ; 9975: f0 3f       .?             ; Bit1 clear: no transfer -- return
    clc                                                               ; 9977: 18          .              ; CLC: init carry for 4-byte add
    php                                                               ; 9978: 08          .              ; Save carry on stack for loop
    ldy #8                                                            ; 9979: a0 08       ..             ; Y=8: RXCB high pointer offset
; &997b referenced 1 time by &9987
.add_rxcb_ptr
    lda (port_ws_offset),y                                            ; 997b: b1 a6       ..             ; Load RXCB[Y] (buffer pointer byte)
    plp                                                               ; 997d: 28          (              ; Restore carry from stack
    adc net_tx_ptr,y                                                  ; 997e: 79 9a 00    y..            ; Add transfer count byte
    sta (port_ws_offset),y                                            ; 9981: 91 a6       ..             ; Store updated pointer back to RXCB
    iny                                                               ; 9983: c8          .              ; Next byte
    php                                                               ; 9984: 08          .              ; Save carry for next iteration
    cpy #&0c                                                          ; 9985: c0 0c       ..             ; Done 4 bytes? (Y reaches &0C)
    bcc add_rxcb_ptr                                                  ; 9987: 90 f2       ..             ; No: continue adding
    plp                                                               ; 9989: 28          (              ; Discard final carry
    lda #&20 ; ' '                                                    ; 998a: a9 20       .              ; A=&20: test bit5 of tx_flags
    bit tx_flags                                                      ; 998c: 2c 4a 0d    ,J.            ; BIT tx_flags: check Tube bit
    beq skip_tube_update                                              ; 998f: f0 23       .#             ; No Tube: skip Tube update
    txa                                                               ; 9991: 8a          .              ; Save X on stack
    pha                                                               ; 9992: 48          H              ; Push X
    lda #8                                                            ; 9993: a9 08       ..             ; A=8: offset for Tube address
    clc                                                               ; 9995: 18          .              ; CLC for address calculation
    adc port_ws_offset                                                ; 9996: 65 a6       e.             ; Add workspace base offset
    tax                                                               ; 9998: aa          .              ; X = address low for Tube claim
    ldy rx_buf_offset                                                 ; 9999: a4 a7       ..             ; Y = address high for Tube claim
    lda #1                                                            ; 999b: a9 01       ..             ; A=1: Tube claim type (read)
    jsr tube_addr_claim                                               ; 999d: 20 06 04     ..            ; Claim Tube address for transfer
    lda rx_extra_byte                                                 ; 99a0: ad 5d 0d    .].            ; Load extra RX data byte
    sta tube_data_register_3                                          ; 99a3: 8d e5 fe    ...            ; Send to Tube via R3
    sec                                                               ; 99a6: 38          8              ; SEC: init carry for increment
    ldy #8                                                            ; 99a7: a0 08       ..             ; Y=8: start at high pointer
; &99a9 referenced 1 time by &99b0
.inc_rxcb_ptr
    lda #0                                                            ; 99a9: a9 00       ..             ; A=0: add carry only (increment)
    adc (port_ws_offset),y                                            ; 99ab: 71 a6       q.             ; Add carry to pointer byte
    sta (port_ws_offset),y                                            ; 99ad: 91 a6       ..             ; Store back to RXCB
    iny                                                               ; 99af: c8          .              ; Next byte
    bcs inc_rxcb_ptr                                                  ; 99b0: b0 f7       ..             ; Keep going while carry propagates
    pla                                                               ; 99b2: 68          h              ; Restore X from stack
    tax                                                               ; 99b3: aa          .              ; Transfer to X register
; &99b4 referenced 1 time by &998f
.skip_tube_update
    lda #&ff                                                          ; 99b4: a9 ff       ..             ; A=&FF: return value (transfer done)
; &99b6 referenced 1 time by &9975
.return_10
    rts                                                               ; 99b6: 60          `              ; Return

    lda rx_port                                                       ; 99b7: ad 40 0d    .@.            ; Load received port byte
    bne rx_complete_update_rxcb                                       ; 99ba: d0 0a       ..             ; Port != 0: data transfer frame
    ldy rx_ctrl                                                       ; 99bc: ac 3f 0d    .?.            ; Port=0: load control byte
    cpy #&82                                                          ; 99bf: c0 82       ..             ; Ctrl = &82 (POKE)?
    beq rx_complete_update_rxcb                                       ; 99c1: f0 03       ..             ; Yes: POKE also needs data transfer
    jmp imm_op_build_reply                                            ; 99c3: 4c 09 9b    L..            ; Other port-0 ops: immediate dispatch

; ***************************************************************************************
; Complete RX and update RXCB
; 
; Post-scout completion for data transfer frames (port != 0)
; and POKE (ctrl=&82). Calls advance_rx_buffer_ptr, updates
; the open port buffer address, then writes source station/
; network, port, and control byte into the RXCB.
; ***************************************************************************************
; &99c6 referenced 3 times by &99ba, &99c1, &9a38
.rx_complete_update_rxcb
    jsr advance_rx_buffer_ptr                                         ; 99c6: 20 70 99     p.            ; Update buffer pointer and check for Tube
    bne skip_buf_ptr_update                                           ; 99c9: d0 12       ..             ; Transfer not done: skip buffer update
.add_buf_to_base
    lda port_buf_len                                                  ; 99cb: a5 a2       ..             ; Load buffer bytes remaining
    clc                                                               ; 99cd: 18          .              ; CLC for address add
    adc open_port_buf                                                 ; 99ce: 65 a4       e.             ; Add to buffer base address
    bcc store_buf_ptr_lo                                              ; 99d0: 90 02       ..             ; No carry: skip high byte increment
.inc_rxcb_buf_hi
    inc open_port_buf_hi                                              ; 99d2: e6 a5       ..             ; Carry: increment buffer high byte
; &99d4 referenced 1 time by &99d0
.store_buf_ptr_lo
    ldy #8                                                            ; 99d4: a0 08       ..             ; Y=8: store updated buffer position
.store_rxcb_buf_ptr
    sta (port_ws_offset),y                                            ; 99d6: 91 a6       ..             ; Store updated low byte to RXCB
    iny                                                               ; 99d8: c8          .              ; Y=9: buffer high byte offset
    lda open_port_buf_hi                                              ; 99d9: a5 a5       ..             ; Load updated buffer high byte
.store_rxcb_buf_hi
    sta (port_ws_offset),y                                            ; 99db: 91 a6       ..             ; Store high byte to RXCB
; &99dd referenced 1 time by &99c9
.skip_buf_ptr_update
    lda rx_port                                                       ; 99dd: ad 40 0d    .@.            ; Check port byte again
    beq discard_reset_listen                                          ; 99e0: f0 1b       ..             ; Port=0: immediate op, discard+listen
    lda rx_src_net                                                    ; 99e2: ad 3e 0d    .>.            ; Load source network from scout buffer
    ldy #3                                                            ; 99e5: a0 03       ..             ; Y=3: RXCB source network offset
    sta (port_ws_offset),y                                            ; 99e7: 91 a6       ..             ; Store source network to RXCB
    dey                                                               ; 99e9: 88          .              ; Y=2: source station offset; Y=&02
    lda rx_src_stn                                                    ; 99ea: ad 3d 0d    .=.            ; Load source station from scout buffer
    sta (port_ws_offset),y                                            ; 99ed: 91 a6       ..             ; Store source station to RXCB
    dey                                                               ; 99ef: 88          .              ; Y=1: port byte offset; Y=&01
    lda rx_port                                                       ; 99f0: ad 40 0d    .@.            ; Load port byte
    sta (port_ws_offset),y                                            ; 99f3: 91 a6       ..             ; Store port to RXCB
    dey                                                               ; 99f5: 88          .              ; Y=0: control/flag byte offset; Y=&00
    lda rx_ctrl                                                       ; 99f6: ad 3f 0d    .?.            ; Load control byte from scout
    ora #&80                                                          ; 99f9: 09 80       ..             ; Set bit7 = reception complete flag
    sta (port_ws_offset),y                                            ; 99fb: 91 a6       ..             ; Store to RXCB (marks CB as complete)
; ***************************************************************************************
; Discard with Tube release
; 
; Conditionally releases the Tube co-processor before discarding.
; If tx_flags bit 1 is set (Tube transfer was active), calls
; sub_c9a2b to release the Tube claim, then falls through to
; discard_listen. The main teardown path for RX operations that
; used the Tube.
; ***************************************************************************************
; &99fd referenced 4 times by &9862, &99e0, &9e80, &9eea
.discard_reset_listen
    lda #2                                                            ; 99fd: a9 02       ..             ; Tube flag bit 1 AND tx_flags bit 1
    and tube_flag                                                     ; 99ff: 2d 67 0d    -g.            ; Check if Tube transfer active
    bit tx_flags                                                      ; 9a02: 2c 4a 0d    ,J.            ; Test tx_flags for Tube transfer
    beq discard_listen                                                ; 9a05: f0 03       ..             ; No Tube transfer active -- skip release
    jsr release_tube                                                  ; 9a07: 20 4d 9a     M.            ; Release Tube claim before discarding
; ***************************************************************************************
; Discard frame and return to idle listen
; 
; Calls adlc_rx_listen to re-enter idle RX mode (CR1=&82, CR2=&67),
; then installs nmi_rx_scout (&96DF) as the NMI handler via
; set_nmi_vector. Returns to the caller's NMI context. Used as
; the common discard tail for both gentle rejection (wrong
; station/network) and error recovery paths.
; ***************************************************************************************
; &9a0a referenced 4 times by &972b, &9a05, &9a83, &9b3f
.discard_listen
    jsr adlc_rx_listen                                                ; 9a0a: 20 7f 9f     ..            ; Re-enter idle RX listen mode
; ***************************************************************************************
; Install RX scout NMI handler
; 
; Installs nmi_rx_scout (&96DF) as the NMI handler via
; set_nmi_vector, without first calling adlc_rx_listen.
; Used when the ADLC is already in the correct RX mode.
; ***************************************************************************************
; &9a0d referenced 2 times by &970f, &9728
.install_rx_scout_handler
    lda #&df                                                          ; 9a0d: a9 df       ..             ; Install nmi_rx_scout (&96DF) as NMI handler
    ldy #&96                                                          ; 9a0f: a0 96       ..             ; High byte of nmi_rx_scout
    jmp set_nmi_vector                                                ; 9a11: 4c 0e 0d    L..            ; Set NMI vector and return

; ***************************************************************************************
; Copy scout data to port buffer
; 
; Copies scout data bytes (offsets 4-11) from the RX scout
; buffer into the open port buffer, handling both direct memory
; and Tube R3 write paths.
; ***************************************************************************************
; &9a14 referenced 1 time by &97e8
.copy_scout_to_buffer
    txa                                                               ; 9a14: 8a          .              ; Save X on stack
    pha                                                               ; 9a15: 48          H              ; Push X
    ldx #4                                                            ; 9a16: a2 04       ..             ; X=4: start at scout byte offset 4
    lda #2                                                            ; 9a18: a9 02       ..             ; A=2: Tube transfer check mask
; &9a1a referenced 1 time by &9a8b
    bit tx_flags                                                      ; 9a1a: 2c 4a 0d    ,J.            ; BIT tx_flags: check Tube bit
    bne copy_scout_via_tube                                           ; 9a1d: d0 1c       ..             ; Tube active: use R3 write path
    ldy port_buf_len                                                  ; 9a1f: a4 a2       ..             ; Y = current buffer position
; &9a21 referenced 1 time by &9a34
.copy_scout_bytes
    lda rx_src_stn,x                                                  ; 9a21: bd 3d 0d    .=.            ; Load scout data byte
    sta (open_port_buf),y                                             ; 9a24: 91 a4       ..             ; Store to port buffer
    iny                                                               ; 9a26: c8          .              ; Advance buffer pointer
    bne next_scout_byte                                               ; 9a27: d0 06       ..             ; No page crossing
    inc open_port_buf_hi                                              ; 9a29: e6 a5       ..             ; Page crossing: inc buffer high byte
    dec port_buf_len_hi                                               ; 9a2b: c6 a3       ..             ; Decrement remaining page count
    beq scout_page_overflow                                           ; 9a2d: f0 61       .a             ; No pages left: overflow
; &9a2f referenced 1 time by &9a27
.next_scout_byte
    inx                                                               ; 9a2f: e8          .              ; Next scout data byte
    sty port_buf_len                                                  ; 9a30: 84 a2       ..             ; Save updated buffer position
    cpx #&0c                                                          ; 9a32: e0 0c       ..             ; Done all scout data? (X reaches &0C)
    bne copy_scout_bytes                                              ; 9a34: d0 eb       ..             ; No: continue copying
; &9a36 referenced 2 times by &9a4b, &9a94
.scout_copy_done
    pla                                                               ; 9a36: 68          h              ; Restore X from stack
    tax                                                               ; 9a37: aa          .              ; Transfer to X register
    jmp rx_complete_update_rxcb                                       ; 9a38: 4c c6 99    L..            ; Jump to completion handler

; &9a3b referenced 2 times by &9a1d, &9a49
.copy_scout_via_tube
    lda rx_src_stn,x                                                  ; 9a3b: bd 3d 0d    .=.            ; Tube path: load scout data byte
    sta tube_data_register_3                                          ; 9a3e: 8d e5 fe    ...            ; Send byte to Tube via R3
    jsr inc_buf_counter_32                                            ; 9a41: 20 59 9a     Y.            ; Increment buffer position counters
    beq check_scout_done                                              ; 9a44: f0 4c       .L             ; Counter overflow: handle end of buffer
    inx                                                               ; 9a46: e8          .              ; Next scout data byte
    cpx #&0c                                                          ; 9a47: e0 0c       ..             ; Done all scout data?
    bne copy_scout_via_tube                                           ; 9a49: d0 f0       ..             ; No: continue Tube writes
    beq scout_copy_done                                               ; 9a4b: f0 e9       ..             ; ALWAYS branch

; ***************************************************************************************
; Release Tube co-processor claim
; 
; If need_release_tube bit 7 is clear (Tube is claimed), calls
; tube_addr_claim with A=&82 to release it, then clears the
; release flag via LSR.
; ***************************************************************************************
; &9a4d referenced 2 times by &9a07, &9f45
.release_tube
    bit need_release_tube                                             ; 9a4d: 24 98       $.             ; Check if Tube needs releasing
    bmi clear_release_flag                                            ; 9a4f: 30 05       0.             ; Bit7 set: already released
    lda #&82                                                          ; 9a51: a9 82       ..             ; A=&82: Tube release claim type
    jsr tube_addr_claim                                               ; 9a53: 20 06 04     ..            ; Release Tube address claim
; &9a56 referenced 1 time by &9a4f
.clear_release_flag
    lsr need_release_tube                                             ; 9a56: 46 98       F.             ; Clear release flag (LSR clears bit7)
    rts                                                               ; 9a58: 60          `              ; Return

; ***************************************************************************************
; Increment 32-bit buffer counter
; 
; Increments a 4-byte counter across port_buf_len / port_buf_len_hi
; / open_port_buf / open_port_buf_hi with carry propagation.
; Returns Z=1 if the counter wraps to zero.
; ***************************************************************************************
; &9a59 referenced 3 times by &98ca, &98d8, &9a41
.inc_buf_counter_32
    inc port_buf_len                                                  ; 9a59: e6 a2       ..             ; Increment buffer position (4-byte)
    bne return_inc_port_buf                                           ; 9a5b: d0 0a       ..             ; Low byte didn't wrap: done
    inc port_buf_len_hi                                               ; 9a5d: e6 a3       ..             ; Carry into second byte
    bne return_inc_port_buf                                           ; 9a5f: d0 06       ..             ; No further carry: done
    inc open_port_buf                                                 ; 9a61: e6 a4       ..             ; Carry into third byte
    bne return_inc_port_buf                                           ; 9a63: d0 02       ..             ; No further carry: done
    inc open_port_buf_hi                                              ; 9a65: e6 a5       ..             ; Carry into fourth byte
; &9a67 referenced 3 times by &9a5b, &9a5f, &9a63
.return_inc_port_buf
    rts                                                               ; 9a67: 60          `              ; Return

; ***************************************************************************************
; Immediate operation handler (port = 0)
; 
; Handles immediate (non-data-transfer) operations received via
; scout frames with port byte = 0. The control byte (&0D3F)
; determines the operation type:
;   &81 = PEEK (read memory)
;   &82 = POKE (write memory)
;   &83 = JSR (remote procedure call)
;   &84 = user procedure
;   &85 = OS procedure
;   &86 = HALT
;   &87 = CONTINUE
; The protection mask (LSTAT at &D63) controls which operations
; are permitted — each bit enables or disables an operation type.
; If the operation is not permitted by the mask, it is silently
; ignored. LSTAT can be read/set via OSWORD &12 sub-functions 4/5.
; ***************************************************************************************
; &9a68 referenced 1 time by &977e
.immediate_op
    ldy rx_ctrl                                                       ; 9a68: ac 3f 0d    .?.            ; Control byte &81-&88 range check
    cpy #&81                                                          ; 9a6b: c0 81       ..             ; Below &81: not an immediate op
    bcc imm_op_out_of_range                                           ; 9a6d: 90 29       .)             ; Out of range low: jump to discard
    cpy #&89                                                          ; 9a6f: c0 89       ..             ; Above &88: not an immediate op
    bcs imm_op_out_of_range                                           ; 9a71: b0 25       .%             ; Out of range high: jump to discard
    cpy #&87                                                          ; 9a73: c0 87       ..             ; HALT(&87)/CONTINUE(&88) skip protection
    bcs dispatch_imm_op                                               ; 9a75: b0 0e       ..             ; Ctrl >= &87: dispatch without mask check
    tya                                                               ; 9a77: 98          .              ; Convert ctrl byte to 0-based index for mask
    sec                                                               ; 9a78: 38          8              ; SEC for subtract
    sbc #&81                                                          ; 9a79: e9 81       ..             ; A = ctrl - &81 (0-based operation index)
    tay                                                               ; 9a7b: a8          .              ; Y = index for mask rotation count
    lda prot_status                                                   ; 9a7c: ad 63 0d    .c.            ; Load protection mask from LSTAT
; &9a7f referenced 1 time by &9a81
.rotate_prot_mask
    ror a                                                             ; 9a7f: 6a          j              ; Rotate mask right by control byte index
    dey                                                               ; 9a80: 88          .              ; Decrement rotation counter
    bpl rotate_prot_mask                                              ; 9a81: 10 fc       ..             ; Loop until bit aligned
    bcs discard_listen                                                ; 9a83: b0 85       ..             ; Bit set = operation disabled, discard
; &9a85 referenced 1 time by &9a75
.dispatch_imm_op
    ldy rx_ctrl                                                       ; 9a85: ac 3f 0d    .?.            ; Reload ctrl byte for dispatch table
    lda #&9a                                                          ; 9a88: a9 9a       ..             ; Hi byte: all handlers are in page &9A
    pha                                                               ; 9a8a: 48          H              ; Push hi byte for PHA/PHA/RTS dispatch
    lda imm_op_dispatch_lo-&81,y                                      ; 9a8b: b9 1a 9a    ...            ; Load handler low byte from jump table
    pha                                                               ; 9a8e: 48          H              ; Push handler low byte
    rts                                                               ; 9a8f: 60          `              ; RTS dispatches to handler

; &9a90 referenced 1 time by &9a2d
.scout_page_overflow
    inc port_buf_len                                                  ; 9a90: e6 a2       ..             ; Increment port buffer length
; &9a92 referenced 1 time by &9a44
.check_scout_done
    cpx #&0b                                                          ; 9a92: e0 0b       ..             ; Check if scout data index reached 11
    beq scout_copy_done                                               ; 9a94: f0 a0       ..             ; Yes: loop back to continue reading
    pla                                                               ; 9a96: 68          h              ; Restore A from stack
    tax                                                               ; 9a97: aa          .              ; Transfer to X
; &9a98 referenced 2 times by &9a6d, &9a71
.imm_op_out_of_range
    jmp nmi_error_dispatch                                            ; 9a98: 4c 57 98    LW.            ; Jump to discard handler

.imm_op_dispatch_lo
    equb <(rx_imm_peek-1)                                             ; 9a9b: dd          .              ; Ctrl &81: PEEK
    equb <(rx_imm_poke-1)                                             ; 9a9c: c0          .              ; Ctrl &82: POKE
    equb <(rx_imm_exec-1)                                             ; 9a9d: a2          .              ; Ctrl &83: JSR
    equb <(rx_imm_exec-1)                                             ; 9a9e: a2          .              ; Ctrl &84: UserProc
    equb <(rx_imm_exec-1)                                             ; 9a9f: a2          .              ; Ctrl &85: OSProc
    equb <(rx_imm_halt_cont-1)                                        ; 9aa0: f7          .              ; Ctrl &86: HALT
    equb <(rx_imm_halt_cont-1)                                        ; 9aa1: f7          .              ; Ctrl &87: CONTINUE
    equb <(rx_imm_machine_type-1)                                     ; 9aa2: cb          .              ; Ctrl &88: machine type query

; ***************************************************************************************
; RX immediate: JSR/UserProc/OSProc setup
; 
; Sets up the port buffer to receive remote procedure data.
; Copies the 4-byte remote address from rx_remote_addr into
; the execution address workspace at &0D58, then jumps to
; the common receive path at c9826. Used for operation types
; &83 (JSR), &84 (UserProc), and &85 (OSProc).
; ***************************************************************************************
.rx_imm_exec
    lda #0                                                            ; 9aa3: a9 00       ..             ; A=0: port buffer lo at page boundary
    sta open_port_buf                                                 ; 9aa5: 85 a4       ..             ; Set port buffer lo
    lda #&82                                                          ; 9aa7: a9 82       ..             ; Buffer length lo = &82
    sta port_buf_len                                                  ; 9aa9: 85 a2       ..             ; Set buffer length lo
    lda #1                                                            ; 9aab: a9 01       ..             ; Buffer length hi = 1
    sta port_buf_len_hi                                               ; 9aad: 85 a3       ..             ; Set buffer length hi
    lda net_rx_ptr_hi                                                 ; 9aaf: a5 9d       ..             ; Load RX page hi for buffer
    sta open_port_buf_hi                                              ; 9ab1: 85 a5       ..             ; Set port buffer hi
    ldy #3                                                            ; 9ab3: a0 03       ..             ; Y=3: copy 4 bytes (3 down to 0)
; &9ab5 referenced 1 time by &9abc
.copy_addr_loop
    lda rx_remote_addr,y                                              ; 9ab5: b9 41 0d    .A.            ; Load remote address byte
    sta l0d58,y                                                       ; 9ab8: 99 58 0d    .X.            ; Store to exec address workspace
    dey                                                               ; 9abb: 88          .              ; Next byte (descending)
    bpl copy_addr_loop                                                ; 9abc: 10 f7       ..             ; Loop until all 4 bytes copied
.sub_c9abe
svc5_dispatch_lo = sub_c9abe+1
    jmp send_data_rx_ack                                              ; 9abe: 4c eb 97    L..            ; Enter common data-receive path; Svc 5 dispatch table low bytes

; ***************************************************************************************
; RX immediate: POKE setup
; 
; Sets up workspace offsets for receiving POKE data.
; port_ws_offset=&3D, rx_buf_offset=&0D, then jumps to
; the common data-receive path at port_match_found.
; ***************************************************************************************
.rx_imm_poke
    lda #&3d ; '='                                                    ; 9ac1: a9 3d       .=             ; Port workspace offset = &3D
    sta port_ws_offset                                                ; 9ac3: 85 a6       ..             ; Store workspace offset lo
    lda #&0d                                                          ; 9ac5: a9 0d       ..             ; RX buffer page = &0D
    sta rx_buf_offset                                                 ; 9ac7: 85 a7       ..             ; Store workspace offset hi
    jmp port_match_found                                              ; 9ac9: 4c d9 97    L..            ; Enter POKE data-receive path

; ***************************************************************************************
; RX immediate: machine type query
; 
; Sets up a reply buffer (open_port_buf=&21, page &7F,
; length &01FC) for the machine type query response, then
; branches to set_tx_reply_flag. Returns system identification
; data to the remote station.
; ***************************************************************************************
.rx_imm_machine_type
    lda #1                                                            ; 9acc: a9 01       ..             ; Buffer length hi = 1
    sta port_buf_len_hi                                               ; 9ace: 85 a3       ..             ; Set buffer length hi
    lda #&fc                                                          ; 9ad0: a9 fc       ..             ; Buffer length lo = &FC
    sta port_buf_len                                                  ; 9ad2: 85 a2       ..             ; Set buffer length lo
    lda #&21 ; '!'                                                    ; 9ad4: a9 21       .!             ; Buffer start lo = &21
    sta open_port_buf                                                 ; 9ad6: 85 a4       ..             ; Set port buffer lo
    lda #&7f                                                          ; 9ad8: a9 7f       ..             ; Buffer hi = &7F (below screen)
    sta open_port_buf_hi                                              ; 9ada: 85 a5       ..             ; Set port buffer hi
    bne set_tx_reply_flag                                             ; 9adc: d0 12       ..             ; ALWAYS branch

; ***************************************************************************************
; RX immediate: PEEK setup
; 
; Writes &0D3D to port_ws_offset/rx_buf_offset, sets
; scout_status=2, then calls tx_calc_transfer to send the
; PEEK response data back to the requesting station.
; Uses workspace offsets (&A6/&A7) for nmi_tx_block.
; ***************************************************************************************
.rx_imm_peek
    lda #&3d ; '='                                                    ; 9ade: a9 3d       .=             ; Port workspace offset = &3D
    sta port_ws_offset                                                ; 9ae0: 85 a6       ..             ; Store workspace offset lo
    lda #&0d                                                          ; 9ae2: a9 0d       ..             ; RX buffer page = &0D
    sta rx_buf_offset                                                 ; 9ae4: 85 a7       ..             ; Store workspace offset hi
    lda #2                                                            ; 9ae6: a9 02       ..             ; Scout status = 2 (PEEK response)
    sta scout_status                                                  ; 9ae8: 8d 5c 0d    .\.            ; Store scout status
    jsr tx_calc_transfer                                              ; 9aeb: 20 fd 9e     ..            ; Calculate transfer size for response
    bcc imm_op_discard                                                ; 9aee: 90 4f       .O             ; C=0: transfer not set up, discard
; &9af0 referenced 1 time by &9adc
.set_tx_reply_flag
    lda tx_flags                                                      ; 9af0: ad 4a 0d    .J.            ; Mark TX flags bit 7 (reply pending)
    ora #&80                                                          ; 9af3: 09 80       ..             ; Set reply pending flag
    sta tx_flags                                                      ; 9af5: 8d 4a 0d    .J.            ; Store updated TX flags
.rx_imm_halt_cont
    lda #&44 ; 'D'                                                    ; 9af8: a9 44       .D             ; CR1=&44: TIE | TX_LAST_DATA
    sta econet_control1_or_status1                                    ; 9afa: 8d a0 fe    ...            ; Write CR1: enable TX interrupts
.tx_cr2_setup
    lda #&a7                                                          ; 9afd: a9 a7       ..             ; CR2=&A7: RTS|CLR_RX_ST|FC_TDRA|PSE
    sta econet_control23_or_status2                                   ; 9aff: 8d a1 fe    ...            ; Write CR2 for TX setup
.tx_nmi_setup
    lda #&1f                                                          ; 9b02: a9 1f       ..             ; NMI handler lo byte (self-modifying)
    ldy #&9b                                                          ; 9b04: a0 9b       ..             ; Y=&9B: dispatch table page
    jmp ack_tx_write_dest                                             ; 9b06: 4c 29 99    L).            ; Acknowledge and write TX dest

; ***************************************************************************************
; Build immediate operation reply header
; 
; Stores data length, source station/network, and control byte
; into the RX buffer header area for port-0 immediate operations.
; Then disables SR interrupts and configures the VIA shift
; register for shift-in mode before returning to
; idle listen.
; ***************************************************************************************
; &9b09 referenced 1 time by &99c3
.imm_op_build_reply
    lda port_buf_len                                                  ; 9b09: a5 a2       ..             ; Get buffer position for reply header
    clc                                                               ; 9b0b: 18          .              ; Clear carry for offset addition
    adc #&80                                                          ; 9b0c: 69 80       i.             ; Data offset = buf_len + &80 (past header)
    ldy #&7f                                                          ; 9b0e: a0 7f       ..             ; Y=&7F: reply data length slot
    sta (net_rx_ptr),y                                                ; 9b10: 91 9c       ..             ; Store reply data length in RX buffer
    ldy #&80                                                          ; 9b12: a0 80       ..             ; Y=&80: source station slot
    lda rx_src_stn                                                    ; 9b14: ad 3d 0d    .=.            ; Load requesting station number
    sta (net_rx_ptr),y                                                ; 9b17: 91 9c       ..             ; Store source station in reply header
    iny                                                               ; 9b19: c8          .              ; Y=&81
    lda rx_src_net                                                    ; 9b1a: ad 3e 0d    .>.            ; Load requesting network number
    sta (net_rx_ptr),y                                                ; 9b1d: 91 9c       ..             ; Store source network in reply header
    lda rx_ctrl                                                       ; 9b1f: ad 3f 0d    .?.            ; Load control byte from received frame
    sta tx_work_57                                                    ; 9b22: 8d 57 0d    .W.            ; Save ctrl byte for TX response
    lda #&84                                                          ; 9b25: a9 84       ..             ; IER bit 2: disable SR interrupt
    sta system_via_ier                                                ; 9b27: 8d 4e fe    .N.            ; Write IER to disable SR
    lda system_via_acr                                                ; 9b2a: ad 4b fe    .K.            ; Read ACR for shift register config
    and #&1c                                                          ; 9b2d: 29 1c       ).             ; Isolate shift register mode bits (2-4)
    sta tx_work_51                                                    ; 9b2f: 8d 51 0d    .Q.            ; Save original SR mode for later restore
    lda system_via_acr                                                ; 9b32: ad 4b fe    .K.            ; Reload ACR for modification
    and #&e3                                                          ; 9b35: 29 e3       ).             ; Clear SR mode bits (keep other bits)
    ora #8                                                            ; 9b37: 09 08       ..             ; SR mode 2: shift in under φ2
    sta system_via_acr                                                ; 9b39: 8d 4b fe    .K.            ; Apply new shift register mode
    bit system_via_sr                                                 ; 9b3c: 2c 4a fe    ,J.            ; Read SR to clear pending interrupt
; &9b3f referenced 1 time by &9aee
.imm_op_discard
    jmp discard_listen                                                ; 9b3f: 4c 0a 9a    L..            ; Return to idle listen mode

    equs "FO]i"                                                       ; 9b42: 46 4f 5d... FO]            ; Unreferenced data (reply tail bytes)
    equb &80                                                          ; 9b46: 80          .              ; Terminator byte (&80)

; ***************************************************************************************
; TX done: remote JSR execution
; 
; Pushes tx_done_exit-1 on the stack (so RTS returns to
; tx_done_exit), then does JMP (l0d58) to call the remote
; JSR target routine. When that routine returns via RTS,
; control resumes at tx_done_exit.
; ***************************************************************************************
.tx_done_jsr
    lda #&9b                                                          ; 9b47: a9 9b       ..             ; Hi byte of tx_done_exit-1
    pha                                                               ; 9b49: 48          H              ; Push hi byte on stack
    lda #&88                                                          ; 9b4a: a9 88       ..             ; Push lo of (tx_done_exit-1)
    pha                                                               ; 9b4c: 48          H              ; Push lo byte on stack
    jmp (l0d58)                                                       ; 9b4d: 6c 58 0d    lX.            ; Call remote JSR; RTS to tx_done_exit; ORA opcode (dead code / data overlap)

; ***************************************************************************************
; TX done: UserProc event
; 
; Generates a network event (event 8) via OSEVEN with
; X=l0d58, A=l0d59 (the remote address). This notifies
; the user program that a UserProc operation has completed.
; ***************************************************************************************
.tx_done_user_proc
    ldy #event_network_error                                          ; 9b50: a0 08       ..             ; Y=8: network event type
    ldx l0d58                                                         ; 9b52: ae 58 0d    .X.            ; X = remote address lo
    lda l0d59                                                         ; 9b55: ad 59 0d    .Y.            ; A = remote address hi
    jsr oseven                                                        ; 9b58: 20 bf ff     ..            ; Generate event Y='Network error'
    jmp tx_done_exit                                                  ; 9b5b: 4c 89 9b    L..            ; Exit TX done handler

; ***************************************************************************************
; TX done: OSProc call
; 
; Calls the ROM entry point at &8000 (rom_header) with
; X=l0d58, Y=l0d59. This invokes an OS-level procedure
; on behalf of the remote station.
; ***************************************************************************************
.tx_done_os_proc
    ldx l0d58                                                         ; 9b5e: ae 58 0d    .X.            ; X = remote address lo
    ldy l0d59                                                         ; 9b61: ac 59 0d    .Y.            ; Y = remote address hi
    jsr rom_header                                                    ; 9b64: 20 00 80     ..            ; Call ROM entry point at &8000
    jmp tx_done_exit                                                  ; 9b67: 4c 89 9b    L..            ; Exit TX done handler

; ***************************************************************************************
; TX done: HALT
; 
; Sets bit 2 of rx_flags (&0D64), enables interrupts, and
; spin-waits until bit 2 is cleared (by a CONTINUE from the
; remote station). If bit 2 is already set, skips to exit.
; ***************************************************************************************
.tx_done_halt
    lda #4                                                            ; 9b6a: a9 04       ..             ; A=&04: bit 2 mask for rx_flags
    bit rx_flags                                                      ; 9b6c: 2c 64 0d    ,d.            ; Test if already halted
    bne tx_done_exit                                                  ; 9b6f: d0 18       ..             ; Already halted: skip to exit
    ora rx_flags                                                      ; 9b71: 0d 64 0d    .d.            ; Set bit 2 in rx_flags
    sta rx_flags                                                      ; 9b74: 8d 64 0d    .d.            ; Store halt flag
    lda #4                                                            ; 9b77: a9 04       ..             ; A=4: re-load halt bit mask
    cli                                                               ; 9b79: 58          X              ; Enable interrupts during halt wait
; &9b7a referenced 1 time by &9b7d
.halt_spin_loop
    bit rx_flags                                                      ; 9b7a: 2c 64 0d    ,d.            ; Test halt flag
    bne halt_spin_loop                                                ; 9b7d: d0 fb       ..             ; Still halted: keep spinning
    beq tx_done_exit                                                  ; 9b7f: f0 08       ..             ; ALWAYS branch

; ***************************************************************************************
; TX done: CONTINUE
; 
; Clears bit 2 of rx_flags (&0D64), releasing any station
; that is halted and spinning in tx_done_halt.
; ***************************************************************************************
.tx_done_continue
    lda rx_flags                                                      ; 9b81: ad 64 0d    .d.            ; Load current RX flags
    and #&fb                                                          ; 9b84: 29 fb       ).             ; Clear bit 2: release halted station
    sta rx_flags                                                      ; 9b86: 8d 64 0d    .d.            ; Store updated flags
; &9b89 referenced 4 times by &9b5b, &9b67, &9b6f, &9b7f
.tx_done_exit
    pla                                                               ; 9b89: 68          h              ; Restore Y from stack
    tay                                                               ; 9b8a: a8          .              ; Transfer to Y register
    pla                                                               ; 9b8b: 68          h              ; Restore X from stack
    tax                                                               ; 9b8c: aa          .              ; Transfer to X register
    lda #0                                                            ; 9b8d: a9 00       ..             ; A=0: success status
    rts                                                               ; 9b8f: 60          `              ; Return with A=0 (success)

; ***************************************************************************************
; Begin TX operation
; 
; Main TX initiation entry point (called via trampoline at &06CE).
; Copies dest station/network from the TXCB to the scout buffer,
; dispatches to immediate op setup (ctrl >= &81) or normal data
; transfer, calculates transfer sizes, copies extra parameters,
; then enters the INACTIVE polling loop.
; ***************************************************************************************
; &9b90 referenced 1 time by &06eb[4]
.tx_begin
    txa                                                               ; 9b90: 8a          .              ; Save X on stack
    pha                                                               ; 9b91: 48          H              ; Push X
    ldy #2                                                            ; 9b92: a0 02       ..             ; Y=2: TXCB offset for dest station
    lda (nmi_tx_block),y                                              ; 9b94: b1 a0       ..             ; Load dest station from TX control block
    sta tx_dst_stn                                                    ; 9b96: 8d 20 0d    . .            ; Store to TX scout buffer
    iny                                                               ; 9b99: c8          .              ; Y=&03
    lda (nmi_tx_block),y                                              ; 9b9a: b1 a0       ..             ; Load dest network from TX control block
    sta tx_dst_net                                                    ; 9b9c: 8d 21 0d    .!.            ; Store to TX scout buffer
    ldy #0                                                            ; 9b9f: a0 00       ..             ; Y=0: first byte of TX control block
    lda (nmi_tx_block),y                                              ; 9ba1: b1 a0       ..             ; Load control/flag byte
    bmi tx_imm_op_setup                                               ; 9ba3: 30 03       0.             ; Bit7 set: immediate operation ctrl byte
    jmp tx_active_start                                               ; 9ba5: 4c 3a 9c    L:.            ; Bit7 clear: normal data transfer

; &9ba8 referenced 1 time by &9ba3
.tx_imm_op_setup
    sta tx_ctrl_byte                                                  ; 9ba8: 8d 24 0d    .$.            ; Store control byte to TX scout buffer
    tax                                                               ; 9bab: aa          .              ; X = control byte for range checks
    iny                                                               ; 9bac: c8          .              ; Y=1: port byte offset
    lda (nmi_tx_block),y                                              ; 9bad: b1 a0       ..             ; Load port byte from TX control block
    sta tx_port                                                       ; 9baf: 8d 25 0d    .%.            ; Store port byte to TX scout buffer
    bne tx_line_idle_check                                            ; 9bb2: d0 33       .3             ; Port != 0: skip immediate op setup
    cpx #&83                                                          ; 9bb4: e0 83       ..             ; Ctrl < &83: PEEK/POKE need address calc
    bcs tx_ctrl_range_check                                           ; 9bb6: b0 1b       ..             ; Ctrl >= &83: skip to range check
    sec                                                               ; 9bb8: 38          8              ; SEC: init borrow for 4-byte subtract
    php                                                               ; 9bb9: 08          .              ; Save carry on stack for loop
    ldy #8                                                            ; 9bba: a0 08       ..             ; Y=8: high pointer offset in TXCB
; &9bbc referenced 1 time by &9bd0
.calc_peek_poke_size
    lda (nmi_tx_block),y                                              ; 9bbc: b1 a0       ..             ; Load TXCB[Y] (end addr byte)
    dey                                                               ; 9bbe: 88          .              ; Y -= 4: back to start addr offset
    dey                                                               ; 9bbf: 88          .              ; (continued)
    dey                                                               ; 9bc0: 88          .              ; (continued)
    dey                                                               ; 9bc1: 88          .              ; (continued)
    plp                                                               ; 9bc2: 28          (              ; Restore borrow from stack
    sbc (nmi_tx_block),y                                              ; 9bc3: f1 a0       ..             ; end - start = transfer size byte
    sta tx_data_start,y                                               ; 9bc5: 99 26 0d    .&.            ; Store result to tx_data_start
    iny                                                               ; 9bc8: c8          .              ; Y += 5: advance to next end byte
    iny                                                               ; 9bc9: c8          .              ; (continued)
    iny                                                               ; 9bca: c8          .              ; (continued)
    iny                                                               ; 9bcb: c8          .              ; (continued)
    iny                                                               ; 9bcc: c8          .              ; (continued)
    php                                                               ; 9bcd: 08          .              ; Save borrow for next byte
    cpy #&0c                                                          ; 9bce: c0 0c       ..             ; Done all 4 bytes? (Y reaches &0C)
    bcc calc_peek_poke_size                                           ; 9bd0: 90 ea       ..             ; No: next byte pair
    plp                                                               ; 9bd2: 28          (              ; Discard final borrow
; &9bd3 referenced 1 time by &9bb6
.tx_ctrl_range_check
    cpx #&81                                                          ; 9bd3: e0 81       ..             ; Ctrl < &81: not an immediate op
    bcc tx_active_start                                               ; 9bd5: 90 63       .c             ; Below range: normal data transfer
.check_imm_range
    cpx #&89                                                          ; 9bd7: e0 89       ..             ; Ctrl >= &89: out of immediate range
    bcs tx_active_start                                               ; 9bd9: b0 5f       ._             ; Above range: normal data transfer
    ldy #&0c                                                          ; 9bdb: a0 0c       ..             ; Y=&0C: start of extra data in TXCB
; &9bdd referenced 1 time by &9be5
.copy_imm_params
    lda (nmi_tx_block),y                                              ; 9bdd: b1 a0       ..             ; Load extra parameter byte from TXCB
    sta nmi_shim_1a,y                                                 ; 9bdf: 99 1a 0d    ...            ; Copy to NMI shim workspace at &0D1A+Y
    iny                                                               ; 9be2: c8          .              ; Next byte
    cpy #&10                                                          ; 9be3: c0 10       ..             ; Done 4 bytes? (Y reaches &10)
    bcc copy_imm_params                                               ; 9be5: 90 f6       ..             ; No: continue copying
; &9be7 referenced 1 time by &9bb2
.tx_line_idle_check
    lda #&20 ; ' '                                                    ; 9be7: a9 20       .              ; A=&20: mask for SR2 INACTIVE bit
    bit econet_control23_or_status2                                   ; 9be9: 2c a1 fe    ,..            ; BIT SR2: test if line is idle
    bne tx_no_clock_error                                             ; 9bec: d0 5c       .\             ; Line not idle: handle as line jammed
    lda #&fd                                                          ; 9bee: a9 fd       ..             ; A=&FD: high byte of timeout counter
    pha                                                               ; 9bf0: 48          H              ; Push timeout high byte to stack
    lda #6                                                            ; 9bf1: a9 06       ..             ; Scout frame = 6 address+ctrl bytes
    sta tx_length                                                     ; 9bf3: 8d 50 0d    .P.            ; Store scout frame length
    lda #0                                                            ; 9bf6: a9 00       ..             ; A=0: init low byte of timeout counter
; ***************************************************************************************
; INACTIVE polling loop
; 
; Polls SR2 for INACTIVE (bit2) to confirm the network line is idle before
; attempting transmission. Uses a 3-byte timeout counter on the stack.
; The timeout (~256^3 iterations) generates "Line Jammed" if INACTIVE
; never appears.
; The CTS check at &9C18-&9C1D works because CR2=&67 has RTS=0, so
; cts_input_ is always true, and SR1_CTS reflects presence of clock hardware.
; ***************************************************************************************
.inactive_poll
    sta tx_index                                                      ; 9bf8: 8d 4f 0d    .O.            ; Save TX index
    pha                                                               ; 9bfb: 48          H              ; Push timeout byte 1 on stack
    pha                                                               ; 9bfc: 48          H              ; Push timeout byte 2 on stack
    ldy #&e7                                                          ; 9bfd: a0 e7       ..             ; Y=&E7: CR2 value for TX prep (RTS|CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)
; &9bff referenced 3 times by &9c2c, &9c31, &9c36
.test_inactive_retry
    php                                                               ; 9bff: 08          .              ; A=&04: INACTIVE mask for SR2 bit2
    sei                                                               ; 9c00: 78          x              ; Disable interrupts for ADLC access
    lda #&40 ; '@'                                                    ; 9c01: a9 40       .@             ; A=&40: BIT &FE18 becomes RTI (disable NMI)
    sta l0d1c                                                         ; 9c03: 8d 1c 0d    ...            ; Self-modify NMI shim at &0D1C: disable
; ***************************************************************************************
; Disable NMIs and test INACTIVE
; 
; Mid-instruction label within the INACTIVE polling loop. The
; address &9BE2 is referenced as a constant for self-modifying
; code. Disables NMIs twice (belt-and-braces) then tests SR2
; for INACTIVE before proceeding with TX.
; ***************************************************************************************
.intoff_test_inactive
    bit station_id_disable_net_nmis                                   ; 9c06: 2c 18 fe    ,..            ; INTOFF -- disable NMIs; INTOFF again (belt-and-braces)
    lda #4                                                            ; 9c09: a9 04       ..             ; A=4: INACTIVE mask for SR2 bit 2
.test_line_idle
    bit econet_control23_or_status2                                   ; 9c0b: 2c a1 fe    ,..            ; BIT SR2: Z = &04 AND SR2 -- tests INACTIVE
    beq c9c1f                                                         ; 9c0e: f0 0f       ..             ; INACTIVE not set -- re-enable NMIs and loop
    lda econet_control1_or_status1                                    ; 9c10: ad a0 fe    ...            ; Read SR1 (acknowledge pending interrupt)
    lda #&67 ; 'g'                                                    ; 9c13: a9 67       .g             ; CR2=&67: CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE
; &9c15 referenced 1 time by &9c91
.c9c15
    sta econet_control23_or_status2                                   ; 9c15: 8d a1 fe    ...            ; Write CR2: clear status, prepare TX
    lda #&10                                                          ; 9c18: a9 10       ..             ; A=&10: CTS mask for SR1 bit4
    bit econet_control1_or_status1                                    ; 9c1a: 2c a0 fe    ,..            ; BIT SR1: tests CTS present
    bne c9c58                                                         ; 9c1d: d0 39       .9             ; CTS set -- clock hardware detected, start TX
; &9c1f referenced 1 time by &9c0e
.c9c1f
    lda #&2c ; ','                                                    ; 9c1f: a9 2c       .,             ; A=&2C: BIT opcode (re-enable NMI processing)
    sta l0d1c                                                         ; 9c21: 8d 1c 0d    ...            ; Self-modify NMI shim at &0D1C: enable
.inactive_retry
    bit video_ula_control                                             ; 9c24: 2c 20 fe    , .            ; INTON -- re-enable NMIs (&FE20 read)
    plp                                                               ; 9c27: 28          (              ; Restore interrupt state
    tsx                                                               ; 9c28: ba          .              ; 3-byte timeout counter on stack
    inc error_text,x                                                  ; 9c29: fe 01 01    ...            ; Increment timeout counter byte 1
    bne test_inactive_retry                                           ; 9c2c: d0 d1       ..             ; Not overflowed: retry INACTIVE test
    inc stk_timeout_mid,x                                             ; 9c2e: fe 02 01    ...            ; Increment timeout counter byte 2
    bne test_inactive_retry                                           ; 9c31: d0 cc       ..             ; Not overflowed: retry INACTIVE test
    inc stk_frame_3,x                                                 ; 9c33: fe 03 01    ...            ; Increment timeout counter byte 3
    bne test_inactive_retry                                           ; 9c36: d0 c7       ..             ; Not overflowed: retry INACTIVE test
    beq tx_line_jammed                                                ; 9c38: f0 04       ..             ; ALWAYS branch

; TX_ACTIVE branch (A=&44 = CR1 value for TX active)
; &9c3a referenced 3 times by &9ba5, &9bd5, &9bd9
.tx_active_start
    lda #&44 ; 'D'                                                    ; 9c3a: a9 44       .D             ; CR1=&44: TIE | TX_LAST_DATA
    bne store_tx_error                                                ; 9c3c: d0 0e       ..             ; ALWAYS branch

; ***************************************************************************************
; TX timeout error handler (Line Jammed)
; 
; Writes CR2=&07 to abort TX, cleans 3 bytes from stack (the
; timeout loop's state), then stores error code &40 ("Line
; Jammed") into the TX control block and signals completion.
; ***************************************************************************************
; &9c3e referenced 1 time by &9c38
.tx_line_jammed
    lda #7                                                            ; 9c3e: a9 07       ..             ; CR2=&07: FC_TDRA | 2_1_BYTE | PSE (abort TX)
    sta econet_control23_or_status2                                   ; 9c40: 8d a1 fe    ...            ; Write CR2 to abort TX
    pla                                                               ; 9c43: 68          h              ; Clean 3 bytes of timeout loop state
    pla                                                               ; 9c44: 68          h              ; Pop saved register
    pla                                                               ; 9c45: 68          h              ; Pop saved register
    lda #&40 ; '@'                                                    ; 9c46: a9 40       .@             ; Error &40 = 'Line Jammed'
    bne store_tx_error                                                ; 9c48: d0 02       ..             ; ALWAYS branch to shared error handler; ALWAYS branch

; &9c4a referenced 1 time by &9bec
.tx_no_clock_error
    lda #&43 ; 'C'                                                    ; 9c4a: a9 43       .C             ; Error &43 = 'No Clock'
; &9c4c referenced 2 times by &9c3c, &9c48
.store_tx_error
    ldy #0                                                            ; 9c4c: a0 00       ..             ; Offset 0 = error byte in TX control block
    sta (nmi_tx_block),y                                              ; 9c4e: 91 a0       ..             ; Store error code in TX CB byte 0
    lda #&80                                                          ; 9c50: a9 80       ..             ; &80 = TX complete flag
    sta tx_clear_flag                                                 ; 9c52: 8d 62 0d    .b.            ; Signal TX operation complete
    pla                                                               ; 9c55: 68          h              ; Restore X saved by caller
    tax                                                               ; 9c56: aa          .              ; Move to X register
    rts                                                               ; 9c57: 60          `              ; Return to TX caller

; &9c58 referenced 1 time by &9c1d
.c9c58
    ldx #&c0                                                          ; 9c58: a2 c0       ..             ; X=&C0: CR1 = AC | RX_RESET
    stx econet_control1_or_status1                                    ; 9c5a: 8e a0 fe    ...            ; Write CR1: reset RX before TX (new in 3.65)
; ***************************************************************************************
; TX preparation
; 
; Configures ADLC for transmission: asserts RTS via CR2, enables TIE via CR1,
; installs NMI TX handler at &9CFF (nmi_tx_data), and re-enables NMIs.
; For port-0 (immediate) operations, dispatches via a lookup table indexed
; by control byte to set tx_flags, tx_length, and a per-operation handler.
; For port non-zero, branches to c9c8e for standard data transfer setup.
; ***************************************************************************************
.tx_prepare
    sty econet_control23_or_status2                                   ; 9c5d: 8c a1 fe    ...            ; Write CR2 = Y (&E7: RTS|CLR_TX_ST|CLR_RX_ST|FC_TDRA|2_1_BYTE|PSE)
    ldx #&44 ; 'D'                                                    ; 9c60: a2 44       .D             ; CR1=&44: RX_RESET | TIE (TX active, TX interrupts enabled)
    stx econet_control1_or_status1                                    ; 9c62: 8e a0 fe    ...            ; Write to ADLC CR1
    ldx #&ff                                                          ; 9c65: a2 ff       ..             ; Install NMI handler at &9D4C (TX data handler)
    ldy #&9c                                                          ; 9c67: a0 9c       ..             ; High byte of NMI handler address
    stx nmi_jmp_lo                                                    ; 9c69: 8e 0c 0d    ...            ; Write NMI vector low byte directly
    sty nmi_jmp_hi                                                    ; 9c6c: 8c 0d 0d    ...            ; Write NMI vector high byte directly
    sec                                                               ; 9c6f: 38          8              ; Set need_release_tube flag (SEC/ROR = bit7)
    ror need_release_tube                                             ; 9c70: 66 98       f.             ; Rotate carry into bit 7 of flag
    lda #&2c ; ','                                                    ; 9c72: a9 2c       .,             ; A=&2C: BIT opcode (re-enable NMI processing)
    sta l0d1c                                                         ; 9c74: 8d 1c 0d    ...            ; Self-modify NMI shim at &0D1C: enable
    bit video_ula_control                                             ; 9c77: 2c 20 fe    , .            ; INTON -- NMIs now fire for TDRA (&FE20 read)
    lda tx_port                                                       ; 9c7a: ad 25 0d    .%.            ; Load destination port number
    bne setup_data_xfer                                               ; 9c7d: d0 42       .B             ; Port != 0: standard data transfer
    ldy tx_ctrl_byte                                                  ; 9c7f: ac 24 0d    .$.            ; Port 0: load control byte for table lookup
    lda tube_tx_sr1_operand,y                                         ; 9c82: b9 74 9e    .t.            ; Look up tx_flags from table
    sta tx_flags                                                      ; 9c85: 8d 4a 0d    .J.            ; Store operation flags
    lda tube_tx_inc_operand,y                                         ; 9c88: b9 6c 9e    .l.            ; Look up tx_length from table
    sta tx_length                                                     ; 9c8b: 8d 50 0d    .P.            ; Store expected transfer length
    lda #&9c                                                          ; 9c8e: a9 9c       ..             ; Push high byte of return address (&9C)
    pha                                                               ; 9c90: 48          H              ; Push high byte for PHA/PHA/RTS dispatch
    lda c9c15,y                                                       ; 9c91: b9 15 9c    ...            ; Look up handler address low from table
    pha                                                               ; 9c94: 48          H              ; Push low byte for PHA/PHA/RTS dispatch
    rts                                                               ; 9c95: 60          `              ; RTS dispatches to control-byte handler

    equb &a1, &a5, &e7, &e7, &e7, &f7, &f7, &9d                       ; 9c96: a1 a5 e7... ...            ; Control byte → CR2 value lookup table
.imm_op_status3
    equb &a9, 3, &d0, &48                                             ; 9c9e: a9 03 d0... ...            ; A=3: scout_status for PEEK

; ***************************************************************************************
; TX ctrl: PEEK transfer setup
; 
; Sets scout_status=3, then performs a 4-byte addition of
; bytes from the TX block into the transfer parameter
; workspace at &0D1E-&0D21 (with carry propagation).
; Calls tx_calc_transfer to finalise, then exits via
; tx_ctrl_exit.
; ***************************************************************************************
.tx_ctrl_peek
    lda #3                                                            ; 9ca2: a9 03       ..             ; A=3: scout_status for PEEK op
    bne store_status_add4                                             ; 9ca4: d0 02       ..             ; ALWAYS branch

; ***************************************************************************************
; TX ctrl: POKE transfer setup
; 
; Sets scout_status=2 and shares the 4-byte addition and
; transfer calculation path with tx_ctrl_peek.
; ***************************************************************************************
.tx_ctrl_poke
    lda #2                                                            ; 9ca6: a9 02       ..             ; Scout status = 2 (POKE transfer)
; &9ca8 referenced 1 time by &9ca4
.store_status_add4
    sta scout_status                                                  ; 9ca8: 8d 5c 0d    .\.            ; Store scout status
    clc                                                               ; 9cab: 18          .              ; Clear carry for 4-byte addition
    php                                                               ; 9cac: 08          .              ; Save carry on stack
    ldy #&0c                                                          ; 9cad: a0 0c       ..             ; Y=&0C: start at offset 12
; &9caf referenced 1 time by &9cbc
.add_bytes_loop
    lda l0d1e,y                                                       ; 9caf: b9 1e 0d    ...            ; Load workspace address byte
    plp                                                               ; 9cb2: 28          (              ; Restore carry from previous byte
    adc (nmi_tx_block),y                                              ; 9cb3: 71 a0       q.             ; Add TXCB address byte
    sta l0d1e,y                                                       ; 9cb5: 99 1e 0d    ...            ; Store updated address byte
    iny                                                               ; 9cb8: c8          .              ; Next byte
    php                                                               ; 9cb9: 08          .              ; Save carry for next addition
; ***************************************************************************************
; TX ctrl: JSR/UserProc/OSProc setup
; 
; Sets scout_status=2 and calls tx_calc_transfer directly
; (no 4-byte address addition needed for procedure calls).
; Shared by operation types &83-&85.
; ***************************************************************************************
.tx_ctrl_proc
    cpy #&10                                                          ; 9cba: c0 10       ..             ; Compare Y with 16-byte boundary
    bcc add_bytes_loop                                                ; 9cbc: 90 f1       ..             ; Below boundary: continue addition
    plp                                                               ; 9cbe: 28          (              ; Restore processor flags
    bne skip_buf_setup                                                ; 9cbf: d0 2c       .,             ; Skip buffer setup if transfer size is zero
; &9cc1 referenced 1 time by &9c7d
.setup_data_xfer
    lda tx_dst_stn                                                    ; 9cc1: ad 20 0d    . .            ; Load dest station for broadcast check
    and tx_dst_net                                                    ; 9cc4: 2d 21 0d    -!.            ; AND with dest network
    cmp #&ff                                                          ; 9cc7: c9 ff       ..             ; Both &FF = broadcast address?
    bne setup_unicast_xfer                                            ; 9cc9: d0 18       ..             ; Not broadcast: unicast path
    lda #&0e                                                          ; 9ccb: a9 0e       ..             ; Broadcast scout: 14 bytes total
    sta tx_length                                                     ; 9ccd: 8d 50 0d    .P.            ; Store broadcast scout length
    lda #&40 ; '@'                                                    ; 9cd0: a9 40       .@             ; A=&40: broadcast flag
    sta tx_flags                                                      ; 9cd2: 8d 4a 0d    .J.            ; Set broadcast flag in tx_flags
    ldy #4                                                            ; 9cd5: a0 04       ..             ; Y=4: start of address data in TXCB
; &9cd7 referenced 1 time by &9cdf
.copy_bcast_addr
    lda (nmi_tx_block),y                                              ; 9cd7: b1 a0       ..             ; Copy TXCB address bytes to scout buffer
    sta tx_src_stn,y                                                  ; 9cd9: 99 22 0d    .".            ; Store to TX source/data area
    iny                                                               ; 9cdc: c8          .              ; Next byte
    cpy #&0c                                                          ; 9cdd: c0 0c       ..             ; Done 8 bytes? (Y reaches &0C)
    bcc copy_bcast_addr                                               ; 9cdf: 90 f6       ..             ; No: continue copying
    bcs tx_ctrl_exit                                                  ; 9ce1: b0 15       ..             ; ALWAYS branch

; &9ce3 referenced 1 time by &9cc9
.setup_unicast_xfer
    lda #0                                                            ; 9ce3: a9 00       ..             ; A=0: clear flags for unicast
    sta tx_flags                                                      ; 9ce5: 8d 4a 0d    .J.            ; Clear tx_flags
.proc_op_status2
    lda #2                                                            ; 9ce8: a9 02       ..             ; scout_status=2: data transfer pending
.store_status_copy_ptr
    sta scout_status                                                  ; 9cea: 8d 5c 0d    .\.            ; Store scout status
; &9ced referenced 1 time by &9cbf
.skip_buf_setup
    lda nmi_tx_block                                                  ; 9ced: a5 a0       ..             ; Copy TX block pointer to workspace ptr
    sta port_ws_offset                                                ; 9cef: 85 a6       ..             ; Store low byte
    lda nmi_tx_block_hi                                               ; 9cf1: a5 a1       ..             ; Copy TX block pointer high byte
    sta rx_buf_offset                                                 ; 9cf3: 85 a7       ..             ; Store high byte
    jsr tx_calc_transfer                                              ; 9cf5: 20 fd 9e     ..            ; Calculate transfer size from RXCB
; &9cf8 referenced 1 time by &9ce1
.tx_ctrl_exit
    plp                                                               ; 9cf8: 28          (              ; Restore processor status from stack
    pla                                                               ; 9cf9: 68          h              ; Restore stacked registers (4 PLAs)
    pla                                                               ; 9cfa: 68          h              ; Second PLA
    pla                                                               ; 9cfb: 68          h              ; Third PLA
    pla                                                               ; 9cfc: 68          h              ; Fourth PLA
    tax                                                               ; 9cfd: aa          .              ; Restore X from A
    rts                                                               ; 9cfe: 60          `              ; Return to caller

; ***************************************************************************************
; NMI TX data handler
; 
; Writes 2 bytes per NMI invocation to the TX FIFO at &FEA2. Uses the
; BIT instruction on SR1 to test TDRA (V flag = bit6) and IRQ (N flag = bit7).
; After writing 2 bytes, checks if the frame is complete. If more data,
; tests SR1 bit7 (IRQ) via BMI -- if IRQ still asserted, writes 2 more bytes
; without returning from NMI (tight loop). Otherwise returns via RTI.
; ***************************************************************************************
.nmi_tx_data
    ldy tx_index                                                      ; 9cff: ac 4f 0d    .O.            ; Load TX buffer index
    bit econet_control1_or_status1                                    ; 9d02: 2c a0 fe    ,..            ; BIT SR1: V=bit6(TDRA), N=bit7(IRQ)
; &9d05 referenced 1 time by &9d20
.tx_fifo_write
    bvc tx_fifo_not_ready                                             ; 9d05: 50 22       P"             ; TDRA not set -- TX error
    lda tx_dst_stn,y                                                  ; 9d07: b9 20 0d    . .            ; Load byte from TX buffer
    sta econet_data_continue_frame                                    ; 9d0a: 8d a2 fe    ...            ; Write to TX_DATA (continue frame)
    iny                                                               ; 9d0d: c8          .              ; Next TX buffer byte
    lda tx_dst_stn,y                                                  ; 9d0e: b9 20 0d    . .            ; Load second byte from TX buffer
    iny                                                               ; 9d11: c8          .              ; Advance TX index past second byte
    sty tx_index                                                      ; 9d12: 8c 4f 0d    .O.            ; Save updated TX buffer index
    sta econet_data_continue_frame                                    ; 9d15: 8d a2 fe    ...            ; Write second byte to TX_DATA
    cpy tx_length                                                     ; 9d18: cc 50 0d    .P.            ; Compare index to TX length
    bcs tx_last_data                                                  ; 9d1b: b0 1e       ..             ; Frame complete -- go to TX_LAST_DATA
    bit econet_control1_or_status1                                    ; 9d1d: 2c a0 fe    ,..            ; Check if we can send another pair
    bmi tx_fifo_write                                                 ; 9d20: 30 e3       0.             ; IRQ set -- send 2 more bytes (tight loop)
    jmp nmi_rti                                                       ; 9d22: 4c 14 0d    L..            ; RTI -- wait for next NMI

; TX error path
; &9d25 referenced 1 time by &9d68
.tx_error
    lda #&42 ; 'B'                                                    ; 9d25: a9 42       .B             ; Error &42
    bne tx_store_error                                                ; 9d27: d0 07       ..             ; ALWAYS branch

; &9d29 referenced 1 time by &9d05
.tx_fifo_not_ready
    lda #&67 ; 'g'                                                    ; 9d29: a9 67       .g             ; CR2=&67: clear status, return to listen
    sta econet_control23_or_status2                                   ; 9d2b: 8d a1 fe    ...            ; Write CR2: clear status, idle listen
    lda #&41 ; 'A'                                                    ; 9d2e: a9 41       .A             ; Error &41 (TDRA not ready)
; &9d30 referenced 1 time by &9d27
.tx_store_error
    ldy station_id_disable_net_nmis                                   ; 9d30: ac 18 fe    ...            ; INTOFF (also loads station ID)
; &9d33 referenced 1 time by &9d36
.delay_nmi_disable
    pha                                                               ; 9d33: 48          H              ; PHA/PLA delay loop (256 iterations for NMI disable)
    pla                                                               ; 9d34: 68          h              ; PHA/PLA delay (~7 cycles each)
    iny                                                               ; 9d35: c8          .              ; Increment delay counter
    bne delay_nmi_disable                                             ; 9d36: d0 fb       ..             ; Loop 256 times for NMI disable
    jmp tx_store_result                                               ; 9d38: 4c e1 9e    L..            ; Store error and return to idle

; ***************************************************************************************
; TX_LAST_DATA and frame completion
; 
; Signals end of TX frame by writing CR2=&3F (TX_LAST_DATA). Then installs
; the TX completion NMI handler at &9D47 (nmi_tx_complete).
; CR2=&3F = 0011_1111:
;   bit5: CLR_RX_ST -- clears fv_stored_ (prepares for RX of reply)
;   bit4: TX_LAST_DATA -- tells ADLC this is the final data byte
;   bit3: FLAG_IDLE -- send flags/idle after frame
;   bit2: FC_TDRA -- force clear TDRA
;   bit1: 2_1_BYTE -- two-byte transfer mode
;   bit0: PSE -- prioritised status enable
; Note: NO CLR_TX_ST (bit6=0), NO RTS (bit7=0 -- drops RTS after frame)
; ***************************************************************************************
; &9d3b referenced 1 time by &9d1b
.tx_last_data
    lda #&3f ; '?'                                                    ; 9d3b: a9 3f       .?             ; CR2=&3F: TX_LAST_DATA | CLR_RX_ST | FLAG_IDLE | FC_TDRA | 2_1_BYTE | PSE
    sta econet_control23_or_status2                                   ; 9d3d: 8d a1 fe    ...            ; Write to ADLC CR2
    lda #&47 ; 'G'                                                    ; 9d40: a9 47       .G             ; Install NMI handler at &9D47 (TX completion)
    ldy #&9d                                                          ; 9d42: a0 9d       ..             ; High byte of handler address
    jmp set_nmi_vector                                                ; 9d44: 4c 0e 0d    L..            ; Install and return via set_nmi_vector

; ***************************************************************************************
; TX completion: switch to RX mode
; 
; Called via NMI after the frame (including CRC and closing flag) has been
; fully transmitted. Switches from TX mode to RX mode by writing CR1=&82.
; CR1=&82 = 1000_0010: TX_RESET | RIE (listen for reply).
; Checks workspace flags to decide next action:
;   - bit6 set at &0D4A -> tx_result_ok at &9EDB
;   - bit0 set at &0D4A -> handshake_await_ack at &9E83
;   - Otherwise -> install nmi_reply_scout at &9D63
; ***************************************************************************************
.nmi_tx_complete
    lda #&82                                                          ; 9d47: a9 82       ..             ; CR1=&82: TX_RESET | RIE (now in RX mode)
    sta econet_control1_or_status1                                    ; 9d49: 8d a0 fe    ...            ; Write CR1 to switch from TX to RX
    bit tx_flags                                                      ; 9d4c: 2c 4a 0d    ,J.            ; Test workspace flags
    bvc check_handshake_bit                                           ; 9d4f: 50 03       P.             ; bit6 not set -- check bit0
    jmp tx_result_ok                                                  ; 9d51: 4c db 9e    L..            ; bit6 set -- TX completion

; &9d54 referenced 1 time by &9d4f
.check_handshake_bit
    lda #1                                                            ; 9d54: a9 01       ..             ; A=1: mask for bit0 test
    bit tx_flags                                                      ; 9d56: 2c 4a 0d    ,J.            ; Test tx_flags bit0 (handshake)
    beq install_reply_scout                                           ; 9d59: f0 03       ..             ; bit0 clear: install reply handler
    jmp handshake_await_ack                                           ; 9d5b: 4c 83 9e    L..            ; bit0 set -- four-way handshake data phase

; &9d5e referenced 1 time by &9d59
.install_reply_scout
    lda #&63 ; 'c'                                                    ; 9d5e: a9 63       .c             ; Install RX reply handler at &9D63
    jmp install_nmi_handler                                           ; 9d60: 4c 11 0d    L..            ; Install handler and RTI

; ***************************************************************************************
; RX reply scout handler
; 
; Handles reception of the reply scout frame after transmission.
; Checks SR2 bit0 (AP) for incoming data, reads the first byte
; (destination station) and compares to our station ID via &FE18
; (which also disables NMIs as a side effect).
; ***************************************************************************************
.nmi_reply_scout
    lda #1                                                            ; 9d63: a9 01       ..             ; A=&01: AP mask for SR2
    bit econet_control23_or_status2                                   ; 9d65: 2c a1 fe    ,..            ; BIT SR2: test AP (Address Present)
    beq tx_error                                                      ; 9d68: f0 bb       ..             ; No AP -- error
    lda econet_data_continue_frame                                    ; 9d6a: ad a2 fe    ...            ; Read first RX byte (destination station)
    cmp station_id_disable_net_nmis                                   ; 9d6d: cd 18 fe    ...            ; Compare to our station ID (INTOFF side effect)
    bne reject_reply                                                  ; 9d70: d0 19       ..             ; Not our station -- error/reject
    lda #&77 ; 'w'                                                    ; 9d72: a9 77       .w             ; Install next handler at &9D77 (reply continuation)
    jmp install_nmi_handler                                           ; 9d74: 4c 11 0d    L..            ; Install continuation handler

; ***************************************************************************************
; RX reply continuation handler
; 
; Reads the second byte of the reply scout (destination network) and
; validates it is zero (local network). Installs nmi_reply_validate
; (&9D8E) for the remaining two bytes (source station and network).
; Optimisation: checks SR1 bit7 (IRQ still asserted) via BMI at &9D86.
; If IRQ is still set, falls through directly to &9D8E without an RTI,
; avoiding NMI re-entry overhead for short frames where all bytes arrive
; in quick succession.
; ***************************************************************************************
.nmi_reply_cont
    bit econet_control23_or_status2                                   ; 9d77: 2c a1 fe    ,..            ; BIT SR2: test for RDA (bit7 = data available)
    bpl reject_reply                                                  ; 9d7a: 10 0f       ..             ; No RDA -- error
    lda econet_data_continue_frame                                    ; 9d7c: ad a2 fe    ...            ; Read destination network byte
    bne reject_reply                                                  ; 9d7f: d0 0a       ..             ; Non-zero -- network mismatch, error
    lda #&8e                                                          ; 9d81: a9 8e       ..             ; Install next handler at &9DE3 (reply validation)
    bit econet_control1_or_status1                                    ; 9d83: 2c a0 fe    ,..            ; BIT SR1: test IRQ (N=bit7) -- more data ready?
    bmi nmi_reply_validate                                            ; 9d86: 30 06       0.             ; IRQ set: validate reply immediately
    jmp install_nmi_handler                                           ; 9d88: 4c 11 0d    L..            ; IRQ not set -- install handler and RTI

; &9d8b referenced 7 times by &9d70, &9d7a, &9d7f, &9d91, &9d99, &9da1, &9da8
.reject_reply
    jmp tx_result_fail                                                ; 9d8b: 4c df 9e    L..            ; Store error and return to idle

; ***************************************************************************************
; RX reply validation (Path 2 for FV/PSE interaction)
; 
; Reads the source station and source network from the reply scout and
; validates them against the original TX destination (&0D20/&0D21).
; Sequence:
;   1. Check SR2 bit7 (RDA) at &9D8E -- must see data available
;   2. Read source station at &9D93, compare to &0D20 (tx_dst_stn)
;   3. Read source network at &9D9B, compare to &0D21 (tx_dst_net)
;   4. Check SR2 bit1 (FV) at &9DA5 -- must see frame complete
; If all checks pass, the reply scout is valid and the ROM proceeds
; to send the scout ACK (CR2=&A7 for RTS, CR1=&44 for TX mode).
; ***************************************************************************************
; &9d8e referenced 1 time by &9d86
.nmi_reply_validate
    bit econet_control23_or_status2                                   ; 9d8e: 2c a1 fe    ,..            ; BIT SR2: test RDA (bit7). Must be set for valid reply.
    bpl reject_reply                                                  ; 9d91: 10 f8       ..             ; No RDA -- error (FV masking RDA via PSE would cause this)
    lda econet_data_continue_frame                                    ; 9d93: ad a2 fe    ...            ; Read source station
    cmp tx_dst_stn                                                    ; 9d96: cd 20 0d    . .            ; Compare to original TX destination station (&0D20)
    bne reject_reply                                                  ; 9d99: d0 f0       ..             ; Mismatch -- not the expected reply, error
    lda econet_data_continue_frame                                    ; 9d9b: ad a2 fe    ...            ; Read source network
    cmp tx_dst_net                                                    ; 9d9e: cd 21 0d    .!.            ; Compare to original TX destination network (&0D21)
    bne reject_reply                                                  ; 9da1: d0 e8       ..             ; Mismatch -- error
    lda #2                                                            ; 9da3: a9 02       ..             ; A=&02: FV mask for SR2 bit1
    bit econet_control23_or_status2                                   ; 9da5: 2c a1 fe    ,..            ; BIT SR2: test FV -- frame must be complete
    beq reject_reply                                                  ; 9da8: f0 e1       ..             ; No FV -- incomplete frame, error
    lda #&a7                                                          ; 9daa: a9 a7       ..             ; CR2=&A7: RTS|CLR_TX_ST|FC_TDRA|2_1_BYTE|PSE (TX in handshake)
    sta econet_control23_or_status2                                   ; 9dac: 8d a1 fe    ...            ; Write CR2: enable RTS for TX handshake
    lda #&44 ; 'D'                                                    ; 9daf: a9 44       .D             ; CR1=&44: RX_RESET | TIE (TX active for scout ACK)
    sta econet_control1_or_status1                                    ; 9db1: 8d a0 fe    ...            ; Write CR1: reset RX, enable TX interrupt
    lda #&83                                                          ; 9db4: a9 83       ..             ; Install next handler at &9E83 into &0D4B/&0D4C
    ldy #&9e                                                          ; 9db6: a0 9e       ..             ; High byte &9E of next handler address
    sta nmi_next_lo                                                   ; 9db8: 8d 4b 0d    .K.            ; Store low byte to nmi_next_lo
    sty nmi_next_hi                                                   ; 9dbb: 8c 4c 0d    .L.            ; Store high byte to nmi_next_hi
    lda tx_dst_stn                                                    ; 9dbe: ad 20 0d    . .            ; Load dest station for scout ACK TX
    bit econet_control1_or_status1                                    ; 9dc1: 2c a0 fe    ,..            ; BIT SR1: test TDRA (V=bit6)
    bvc data_tx_check_fifo                                            ; 9dc4: 50 3a       P:             ; TDRA not ready -- error
    sta econet_data_continue_frame                                    ; 9dc6: 8d a2 fe    ...            ; Write dest station to TX FIFO
    lda tx_dst_net                                                    ; 9dc9: ad 21 0d    .!.            ; Load dest network for scout ACK TX
    sta econet_data_continue_frame                                    ; 9dcc: 8d a2 fe    ...            ; Write dest network to TX FIFO
    lda #&d6                                                          ; 9dcf: a9 d6       ..             ; Install handler at &9DD6 (write src addr for scout ACK)
    ldy #&9d                                                          ; 9dd1: a0 9d       ..             ; High byte &9D of handler address
    jmp set_nmi_vector                                                ; 9dd3: 4c 0e 0d    L..            ; Set NMI vector and return

; ***************************************************************************************
; TX scout ACK: write source address
; 
; Writes our station ID and network=0 to TX FIFO, completing the
; 4-byte scout ACK frame. Then proceeds to send the data frame.
; ***************************************************************************************
.nmi_scout_ack_src
    lda station_id_disable_net_nmis                                   ; 9dd6: ad 18 fe    ...            ; Load our station ID (also INTOFF)
    bit econet_control1_or_status1                                    ; 9dd9: 2c a0 fe    ,..            ; BIT SR1: check TDRA before writing
    bvc data_tx_check_fifo                                            ; 9ddc: 50 22       P"             ; TDRA not ready: TX error
    sta econet_data_continue_frame                                    ; 9dde: 8d a2 fe    ...            ; Write our station to TX FIFO
    lda #0                                                            ; 9de1: a9 00       ..             ; Network = 0 (local network)
    sta econet_data_continue_frame                                    ; 9de3: 8d a2 fe    ...            ; Write network byte to TX FIFO
; &9de6 referenced 1 time by &996a
.data_tx_begin
    lda #2                                                            ; 9de6: a9 02       ..             ; Test bit 1 of tx_flags
    bit tx_flags                                                      ; 9de8: 2c 4a 0d    ,J.            ; Check if immediate-op or data-transfer
    bne install_imm_data_nmi                                          ; 9deb: d0 07       ..             ; Bit 1 set: immediate op, use alt handler
    lda #&fb                                                          ; 9ded: a9 fb       ..             ; Install nmi_data_tx at &9DFB
    ldy #&9d                                                          ; 9def: a0 9d       ..             ; High byte of handler address
    jmp set_nmi_vector                                                ; 9df1: 4c 0e 0d    L..            ; Install and return via set_nmi_vector

; &9df4 referenced 1 time by &9deb
.install_imm_data_nmi
    lda #&42 ; 'B'                                                    ; 9df4: a9 42       .B             ; Install nmi_imm_data at &9E42
    ldy #&9e                                                          ; 9df6: a0 9e       ..             ; High byte of handler address
    jmp set_nmi_vector                                                ; 9df8: 4c 0e 0d    L..            ; Install and return via set_nmi_vector

; ***************************************************************************************
; TX data phase: send payload
; 
; Sends the data frame payload from (open_port_buf),Y in pairs per NMI.
; Same pattern as the NMI TX handler at &9CFF but reads from the port
; buffer instead of the TX workspace. Writes two bytes per iteration,
; checking SR1 IRQ between pairs for tight looping.
; ***************************************************************************************
.nmi_data_tx
    ldy port_buf_len                                                  ; 9dfb: a4 a2       ..             ; Y = buffer offset, resume from last position
    bit econet_control1_or_status1                                    ; 9dfd: 2c a0 fe    ,..            ; BIT SR1: test TDRA (V=bit6)
; &9e00 referenced 3 times by &9dc4, &9ddc, &9e23
.data_tx_check_fifo
    bvc tx_tdra_error                                                 ; 9e00: 50 79       Py             ; TDRA not ready -- error
    lda (open_port_buf),y                                             ; 9e02: b1 a4       ..             ; Write data byte to TX FIFO
    sta econet_data_continue_frame                                    ; 9e04: 8d a2 fe    ...            ; Write first byte of pair to FIFO
    iny                                                               ; 9e07: c8          .              ; Advance buffer offset
    bne write_second_tx_byte                                          ; 9e08: d0 06       ..             ; No page crossing
    dec port_buf_len_hi                                               ; 9e0a: c6 a3       ..             ; Page crossing: decrement page count
    beq data_tx_last                                                  ; 9e0c: f0 1a       ..             ; No pages left: send last data
    inc open_port_buf_hi                                              ; 9e0e: e6 a5       ..             ; Increment buffer high byte
; &9e10 referenced 1 time by &9e08
.write_second_tx_byte
    lda (open_port_buf),y                                             ; 9e10: b1 a4       ..             ; Load second byte of pair
    sta econet_data_continue_frame                                    ; 9e12: 8d a2 fe    ...            ; Write second byte to FIFO
    iny                                                               ; 9e15: c8          .              ; Advance buffer offset
    sty port_buf_len                                                  ; 9e16: 84 a2       ..             ; Save updated buffer position
    bne check_irq_loop                                                ; 9e18: d0 06       ..             ; No page crossing
    dec port_buf_len_hi                                               ; 9e1a: c6 a3       ..             ; Page crossing: decrement page count
    beq data_tx_last                                                  ; 9e1c: f0 0a       ..             ; No pages left: send last data
    inc open_port_buf_hi                                              ; 9e1e: e6 a5       ..             ; Increment buffer high byte
; &9e20 referenced 1 time by &9e18
.check_irq_loop
    bit econet_control1_or_status1                                    ; 9e20: 2c a0 fe    ,..            ; BIT SR1: test IRQ (N=bit7) for tight loop
    bmi data_tx_check_fifo                                            ; 9e23: 30 db       0.             ; IRQ still set: write 2 more bytes
    jmp nmi_rti                                                       ; 9e25: 4c 14 0d    L..            ; No IRQ: return, wait for next NMI

; &9e28 referenced 4 times by &9e0c, &9e1c, &9e5b, &9e71
.data_tx_last
    lda #&3f ; '?'                                                    ; 9e28: a9 3f       .?             ; CR2=&3F: TX_LAST_DATA (close data frame)
    sta econet_control23_or_status2                                   ; 9e2a: 8d a1 fe    ...            ; Write CR2 to close frame
    lda tx_flags                                                      ; 9e2d: ad 4a 0d    .J.            ; Check tx_flags for next action
    bpl data_tx_error                                                 ; 9e30: 10 07       ..             ; Bit7 clear: error, install saved handler
    lda #&fd                                                          ; 9e32: a9 fd       ..             ; Install discard_reset_listen at &99DB
    ldy #&99                                                          ; 9e34: a0 99       ..             ; High byte of &99DB handler
    jmp set_nmi_vector                                                ; 9e36: 4c 0e 0d    L..            ; Set NMI vector and return

; &9e39 referenced 1 time by &9e30
.data_tx_error
.install_saved_handler
    lda nmi_next_lo                                                   ; 9e39: ad 4b 0d    .K.            ; Load saved next handler low byte
    ldy nmi_next_hi                                                   ; 9e3c: ac 4c 0d    .L.            ; Load saved next handler high byte
    jmp set_nmi_vector                                                ; 9e3f: 4c 0e 0d    L..            ; Install saved handler and return

.nmi_data_tx_tube
    bit econet_control1_or_status1                                    ; 9e42: 2c a0 fe    ,..            ; Tube TX: BIT SR1 test TDRA
; &9e45 referenced 1 time by &9e76
.tube_tx_fifo_write
    bvc tx_tdra_error                                                 ; 9e45: 50 34       P4             ; TDRA not ready -- error
    lda tube_data_register_3                                          ; 9e47: ad e5 fe    ...            ; Read byte from Tube R3
    sta econet_data_continue_frame                                    ; 9e4a: 8d a2 fe    ...            ; Write to TX FIFO
    inc port_buf_len                                                  ; 9e4d: e6 a2       ..             ; Increment 4-byte buffer counter
    bne write_second_tube_byte                                        ; 9e4f: d0 0c       ..             ; Low byte didn't wrap
    inc port_buf_len_hi                                               ; 9e51: e6 a3       ..             ; Carry into second byte
    bne write_second_tube_byte                                        ; 9e53: d0 08       ..             ; No further carry
    inc open_port_buf                                                 ; 9e55: e6 a4       ..             ; Carry into third byte
    bne write_second_tube_byte                                        ; 9e57: d0 04       ..             ; No further carry
    inc open_port_buf_hi                                              ; 9e59: e6 a5       ..             ; Carry into fourth byte
    beq data_tx_last                                                  ; 9e5b: f0 cb       ..             ; Counter wrapped to zero: last data
; &9e5d referenced 3 times by &9e4f, &9e53, &9e57
.write_second_tube_byte
    lda tube_data_register_3                                          ; 9e5d: ad e5 fe    ...            ; Read second Tube byte from R3
    sta econet_data_continue_frame                                    ; 9e60: 8d a2 fe    ...            ; Write second byte to TX FIFO
    inc port_buf_len                                                  ; 9e63: e6 a2       ..             ; Increment 4-byte counter (second byte)
    bne check_tube_irq_loop                                           ; 9e65: d0 0c       ..             ; Low byte didn't wrap
.tube_tx_inc_byte2
    inc port_buf_len_hi                                               ; 9e67: e6 a3       ..             ; Carry into second byte
    bne check_tube_irq_loop                                           ; 9e69: d0 08       ..             ; No further carry
.tube_tx_inc_byte3
tube_tx_inc_operand = tube_tx_inc_byte3+1
    inc open_port_buf                                                 ; 9e6b: e6 a4       ..             ; Carry into third byte
; &9e6c referenced 1 time by &9c88
    bne check_tube_irq_loop                                           ; 9e6d: d0 04       ..             ; No further carry
.tube_tx_inc_byte4
    inc open_port_buf_hi                                              ; 9e6f: e6 a5       ..             ; Carry into fourth byte
    beq data_tx_last                                                  ; 9e71: f0 b5       ..             ; Counter wrapped to zero: last data
; &9e73 referenced 3 times by &9e65, &9e69, &9e6d
.check_tube_irq_loop
tube_tx_sr1_operand = check_tube_irq_loop+1
    bit econet_control1_or_status1                                    ; 9e73: 2c a0 fe    ,..            ; BIT SR1: test IRQ for tight loop
; &9e74 referenced 1 time by &9c82
    bmi tube_tx_fifo_write                                            ; 9e76: 30 cd       0.             ; IRQ still set: write 2 more bytes
    jmp nmi_rti                                                       ; 9e78: 4c 14 0d    L..            ; No IRQ: return, wait for next NMI

; &9e7b referenced 2 times by &9e00, &9e45
.tx_tdra_error
    lda tx_flags                                                      ; 9e7b: ad 4a 0d    .J.            ; TX error: check flags for path
    bpl tx_result_fail                                                ; 9e7e: 10 5f       ._             ; Bit7 clear: TX result = not listening
    jmp discard_reset_listen                                          ; 9e80: 4c fd 99    L..            ; Bit7 set: discard and return to listen

; ***************************************************************************************
; Four-way handshake: switch to RX for final ACK
; 
; After the data frame TX completes, switches to RX mode (CR1=&82)
; and installs &9E8F to receive the final ACK from the remote station.
; ***************************************************************************************
; &9e83 referenced 1 time by &9d5b
.handshake_await_ack
    lda #&82                                                          ; 9e83: a9 82       ..             ; CR1=&82: TX_RESET | RIE (switch to RX for final ACK)
    sta econet_control1_or_status1                                    ; 9e85: 8d a0 fe    ...            ; Write to ADLC CR1
    lda #&8f                                                          ; 9e88: a9 8f       ..             ; Install handler at &9E8F (RX final ACK)
    ldy #&9e                                                          ; 9e8a: a0 9e       ..             ; High byte of handler address
    jmp set_nmi_vector                                                ; 9e8c: 4c 0e 0d    L..            ; Install and return via set_nmi_vector

; ***************************************************************************************
; RX final ACK handler
; 
; Receives the final ACK in a four-way handshake. Same validation
; pattern as the reply scout handler (&9D63-&9D8E):
;   &9E8F: Check AP, read dest_stn, compare to our station
;   &9EA3: Check RDA, read dest_net, validate = 0
;   &9EB7: Check RDA, read src_stn/net, compare to TX dest
;   &9ED6: Check FV for frame completion
; On success, stores result=0 at tx_result_ok. On failure, error &41.
; ***************************************************************************************
.nmi_final_ack
    lda #1                                                            ; 9e8f: a9 01       ..             ; A=&01: AP mask
    bit econet_control23_or_status2                                   ; 9e91: 2c a1 fe    ,..            ; BIT SR2: test AP
    beq tx_result_fail                                                ; 9e94: f0 49       .I             ; No AP -- error
    lda econet_data_continue_frame                                    ; 9e96: ad a2 fe    ...            ; Read dest station
    cmp station_id_disable_net_nmis                                   ; 9e99: cd 18 fe    ...            ; Compare to our station (INTOFF side effect)
    bne tx_result_fail                                                ; 9e9c: d0 41       .A             ; Not our station -- error
    lda #&a3                                                          ; 9e9e: a9 a3       ..             ; Install handler at &9EFF (final ACK continuation)
    jmp install_nmi_handler                                           ; 9ea0: 4c 11 0d    L..            ; Install continuation handler

.nmi_final_ack_net
    bit econet_control23_or_status2                                   ; 9ea3: 2c a1 fe    ,..            ; BIT SR2: test RDA
    bpl tx_result_fail                                                ; 9ea6: 10 37       .7             ; No RDA -- error
    lda econet_data_continue_frame                                    ; 9ea8: ad a2 fe    ...            ; Read dest network
    bne tx_result_fail                                                ; 9eab: d0 32       .2             ; Non-zero -- network mismatch, error
    lda #&b7                                                          ; 9ead: a9 b7       ..             ; Install handler at &9F15 (final ACK validation)
    bit econet_control1_or_status1                                    ; 9eaf: 2c a0 fe    ,..            ; BIT SR1: test IRQ -- more data ready?
    bmi nmi_final_ack_validate                                        ; 9eb2: 30 03       0.             ; IRQ set: validate final ACK immediately
    jmp install_nmi_handler                                           ; 9eb4: 4c 11 0d    L..            ; Install handler and RTI

; ***************************************************************************************
; Final ACK validation
; 
; Reads and validates src_stn and src_net against original TX dest.
; Then checks FV for frame completion.
; ***************************************************************************************
; &9eb7 referenced 1 time by &9eb2
.nmi_final_ack_validate
    bit econet_control23_or_status2                                   ; 9eb7: 2c a1 fe    ,..            ; BIT SR2: test RDA
    bpl tx_result_fail                                                ; 9eba: 10 23       .#             ; No RDA -- error
    lda econet_data_continue_frame                                    ; 9ebc: ad a2 fe    ...            ; Read source station
    cmp tx_dst_stn                                                    ; 9ebf: cd 20 0d    . .            ; Compare to TX dest station (&0D20)
    bne tx_result_fail                                                ; 9ec2: d0 1b       ..             ; Mismatch -- error
    lda econet_data_continue_frame                                    ; 9ec4: ad a2 fe    ...            ; Read source network
    cmp tx_dst_net                                                    ; 9ec7: cd 21 0d    .!.            ; Compare to TX dest network (&0D21)
    bne tx_result_fail                                                ; 9eca: d0 13       ..             ; Mismatch -- error
    lda tx_flags                                                      ; 9ecc: ad 4a 0d    .J.            ; Load TX flags for next action
    bpl check_fv_final_ack                                            ; 9ecf: 10 03       ..             ; bit7 clear: no data phase
    jmp install_data_rx_handler                                       ; 9ed1: 4c 3d 98    L=.            ; Install data RX handler

; &9ed4 referenced 1 time by &9ecf
.check_fv_final_ack
    lda #2                                                            ; 9ed4: a9 02       ..             ; A=&02: FV mask for SR2 bit1
    bit econet_control23_or_status2                                   ; 9ed6: 2c a1 fe    ,..            ; BIT SR2: test FV -- frame must be complete
    beq tx_result_fail                                                ; 9ed9: f0 04       ..             ; No FV -- error
; ***************************************************************************************
; TX completion handler
; 
; Stores result code 0 (success) into the first byte of the TX control
; block (nmi_tx_block),Y=0. Then sets &0D3A bit7 to signal completion
; and calls discard_reset_listen to return to idle.
; ***************************************************************************************
; &9edb referenced 2 times by &9918, &9d51
.tx_result_ok
    lda #0                                                            ; 9edb: a9 00       ..             ; A=0: success result code
    beq tx_store_result                                               ; 9edd: f0 02       ..             ; BEQ: always taken (A=0); ALWAYS branch

; ***************************************************************************************
; TX failure: not listening
; 
; Loads error code &41 (not listening) and falls through to
; tx_store_result. The most common TX error path — reached from
; 11 sites across the final-ACK validation chain when the remote
; station doesn't respond or the frame is malformed.
; ***************************************************************************************
; &9edf referenced 11 times by &985c, &9d8b, &9e7e, &9e94, &9e9c, &9ea6, &9eab, &9eba, &9ec2, &9eca, &9ed9
.tx_result_fail
    lda #&41 ; 'A'                                                    ; 9edf: a9 41       .A             ; A=&41: not listening error code
; ***************************************************************************************
; TX result store and completion
; 
; Stores result code (A) into the TX control block at
; (nmi_tx_block),0 and sets bit 7 of &0D3A to signal completion.
; Returns to idle via discard_reset_listen. Reached from
; tx_result_ok (A=0, success), tx_result_fail (A=&41, not
; listening), and directly with other codes (A=&40 line jammed,
; A=&42 net error).
; ***************************************************************************************
; &9ee1 referenced 2 times by &9d38, &9edd
.tx_store_result
    ldy #0                                                            ; 9ee1: a0 00       ..             ; Y=0: index into TX control block
    sta (nmi_tx_block),y                                              ; 9ee3: 91 a0       ..             ; Store result/error code at (nmi_tx_block),0
    lda #&80                                                          ; 9ee5: a9 80       ..             ; &80: completion flag for &0D3A
    sta tx_clear_flag                                                 ; 9ee7: 8d 62 0d    .b.            ; Signal TX complete
    jmp discard_reset_listen                                          ; 9eea: 4c fd 99    L..            ; Full ADLC reset and return to idle listen

; Unreferenced data block (purpose unknown)
    equb &0e, &0e, &0a, &0a, &0a, 6, 6, &0a, &81, 0, 0, 0, 0, 1, 1    ; 9eed: 0e 0e 0a... ...            ; Unreferenced data block (purpose unknown)
    equb &81                                                          ; 9efc: 81          .

; ***************************************************************************************
; Calculate transfer size
; 
; Computes the number of bytes actually transferred during a data
; frame reception by subtracting RXCB[8..11] (start address) from
; RXCB[4..7] (current pointer), giving the byte count.
; Two paths: the main path performs a 4-byte subtraction for Tube
; transfers, storing results to port_buf_len..open_port_buf_hi
; (&A2-&A5). The fallback path (no Tube or buffer addr = &FFFF)
; does a 2-byte subtraction using open_port_buf/open_port_buf_hi
; (&A4/&A5) as scratch. Both paths clobber &A4/&A5 as a side
; effect of the result area overlapping open_port_buf.
; 
; On Exit:
;     C: 1 if transfer set up, 0 if not
;     X: preserved
; ***************************************************************************************
; &9efd referenced 3 times by &97de, &9aeb, &9cf5
.tx_calc_transfer
    ldy #6                                                            ; 9efd: a0 06       ..             ; Load RXCB[6] (buffer addr byte 2)
    lda (port_ws_offset),y                                            ; 9eff: b1 a6       ..             ; Load workspace byte at offset Y
    iny                                                               ; 9f01: c8          .              ; Y=&07
    and (port_ws_offset),y                                            ; 9f02: 31 a6       1.             ; AND with TX block[7] (byte 3)
    cmp #&ff                                                          ; 9f04: c9 ff       ..             ; Both &FF = no buffer?
    beq fallback_calc_transfer                                        ; 9f06: f0 44       .D             ; Yes: fallback path
    lda tube_flag                                                     ; 9f08: ad 67 0d    .g.            ; Tube transfer in progress?
    beq fallback_calc_transfer                                        ; 9f0b: f0 3f       .?             ; No: fallback path
    lda tx_flags                                                      ; 9f0d: ad 4a 0d    .J.            ; Load TX flags for transfer setup
    ora #2                                                            ; 9f10: 09 02       ..             ; Set bit 1 (transfer complete)
    sta tx_flags                                                      ; 9f12: 8d 4a 0d    .J.            ; Store with bit 1 set (Tube xfer)
    sec                                                               ; 9f15: 38          8              ; Init borrow for 4-byte subtract
    php                                                               ; 9f16: 08          .              ; Save carry on stack
    ldy #4                                                            ; 9f17: a0 04       ..             ; Y=4: start at RXCB offset 4
; &9f19 referenced 1 time by &9f2b
.calc_transfer_size
    lda (port_ws_offset),y                                            ; 9f19: b1 a6       ..             ; Load RXCB[Y] (current ptr byte)
    iny                                                               ; 9f1b: c8          .              ; Y += 4: advance to RXCB[Y+4]
    iny                                                               ; 9f1c: c8          .              ; (continued)
    iny                                                               ; 9f1d: c8          .              ; (continued)
    iny                                                               ; 9f1e: c8          .              ; (continued)
    plp                                                               ; 9f1f: 28          (              ; Restore borrow from previous byte
    sbc (port_ws_offset),y                                            ; 9f20: f1 a6       ..             ; Subtract RXCB[Y+4] (start ptr byte)
    sta net_tx_ptr,y                                                  ; 9f22: 99 9a 00    ...            ; Store result byte
    dey                                                               ; 9f25: 88          .              ; Y -= 3: next source byte
    dey                                                               ; 9f26: 88          .              ; (continued)
    dey                                                               ; 9f27: 88          .              ; (continued)
    php                                                               ; 9f28: 08          .              ; Save borrow for next byte
    cpy #8                                                            ; 9f29: c0 08       ..             ; Done all 4 bytes?
    bcc calc_transfer_size                                            ; 9f2b: 90 ec       ..             ; No: next byte pair
    plp                                                               ; 9f2d: 28          (              ; Discard final borrow
    txa                                                               ; 9f2e: 8a          .              ; A = saved X
    pha                                                               ; 9f2f: 48          H              ; Save X
    lda #4                                                            ; 9f30: a9 04       ..             ; Compute address of RXCB+4
    clc                                                               ; 9f32: 18          .              ; CLC for base pointer addition
    adc port_ws_offset                                                ; 9f33: 65 a6       e.             ; Add RXCB base to get RXCB+4 addr
    tax                                                               ; 9f35: aa          .              ; X = low byte of RXCB+4
    ldy rx_buf_offset                                                 ; 9f36: a4 a7       ..             ; Y = high byte of RXCB ptr
    lda #&c2                                                          ; 9f38: a9 c2       ..             ; Tube claim type &C2
    jsr tube_addr_claim                                               ; 9f3a: 20 06 04     ..            ; Claim Tube transfer address
    bcc restore_x_and_return                                          ; 9f3d: 90 0a       ..             ; No Tube: skip reclaim
    lda scout_status                                                  ; 9f3f: ad 5c 0d    .\.            ; Tube: reclaim with scout status
    jsr tube_addr_claim                                               ; 9f42: 20 06 04     ..            ; Reclaim with scout status type
    jsr release_tube                                                  ; 9f45: 20 4d 9a     M.            ; Release Tube claim after reclaim
    sec                                                               ; 9f48: 38          8              ; C=1: Tube address claimed
; &9f49 referenced 1 time by &9f3d
.restore_x_and_return
    pla                                                               ; 9f49: 68          h              ; Restore X
    tax                                                               ; 9f4a: aa          .              ; Restore X from stack
    rts                                                               ; 9f4b: 60          `              ; Return with C = transfer status

; &9f4c referenced 2 times by &9f06, &9f0b
.fallback_calc_transfer
    ldy #4                                                            ; 9f4c: a0 04       ..             ; Y=4: RXCB current pointer offset
    lda (port_ws_offset),y                                            ; 9f4e: b1 a6       ..             ; Load RXCB[4] (current ptr lo)
    ldy #8                                                            ; 9f50: a0 08       ..             ; Y=8: RXCB start address offset
    sec                                                               ; 9f52: 38          8              ; Set carry for subtraction
    sbc (port_ws_offset),y                                            ; 9f53: f1 a6       ..             ; Subtract RXCB[8] (start ptr lo)
    sta port_buf_len                                                  ; 9f55: 85 a2       ..             ; Store transfer size lo
    ldy #5                                                            ; 9f57: a0 05       ..             ; Y=5: current ptr hi offset
    lda (port_ws_offset),y                                            ; 9f59: b1 a6       ..             ; Load RXCB[5] (current ptr hi)
    sbc #0                                                            ; 9f5b: e9 00       ..             ; Propagate borrow from lo subtraction
    sta open_port_buf_hi                                              ; 9f5d: 85 a5       ..             ; Temp store adjusted current ptr hi
    ldy #8                                                            ; 9f5f: a0 08       ..             ; Y=8: start address lo offset
    lda (port_ws_offset),y                                            ; 9f61: b1 a6       ..             ; Copy RXCB[8] to open port buffer lo
    sta open_port_buf                                                 ; 9f63: 85 a4       ..             ; Store to scratch (side effect)
    ldy #9                                                            ; 9f65: a0 09       ..             ; Y=9: start address hi offset
    lda (port_ws_offset),y                                            ; 9f67: b1 a6       ..             ; Load RXCB[9] (start ptr hi)
    sec                                                               ; 9f69: 38          8              ; Set carry for subtraction
    sbc open_port_buf_hi                                              ; 9f6a: e5 a5       ..             ; start_hi - adjusted current_hi
    sta port_buf_len_hi                                               ; 9f6c: 85 a3       ..             ; Store transfer size hi
    sec                                                               ; 9f6e: 38          8              ; Return with C=1
.nmi_shim_rom_src
    rts                                                               ; 9f6f: 60          `              ; Return with C=1 (success)

; ***************************************************************************************
; ADLC full reset
; 
; Aborts all activity and returns to idle RX listen mode.
; 
; On Exit:
;     A: 0
; ***************************************************************************************
; &9f70 referenced 3 times by &969d, &9725, &985f
.adlc_full_reset
    lda #&c1                                                          ; 9f70: a9 c1       ..             ; CR1=&C1: TX_RESET | RX_RESET | AC (both sections in reset, address control set)
    sta econet_control1_or_status1                                    ; 9f72: 8d a0 fe    ...            ; Write CR1 to ADLC register 0
    lda #&1e                                                          ; 9f75: a9 1e       ..             ; CR4=&1E (via AC=1): 8-bit RX word length, abort extend enabled, NRZ encoding
    sta econet_data_terminate_frame                                   ; 9f77: 8d a3 fe    ...            ; Write CR4 to ADLC register 3
    lda #0                                                            ; 9f7a: a9 00       ..             ; CR3=&00 (via AC=1): no loop-back, no AEX, NRZ, no DTR
    sta econet_control23_or_status2                                   ; 9f7c: 8d a1 fe    ...            ; Write CR3 to ADLC register 1
; ***************************************************************************************
; Enter RX listen mode
; 
; TX held in reset, RX active with interrupts. Clears all status.
; 
; On Exit:
;     A: &67
; ***************************************************************************************
; &9f7f referenced 2 times by &9a0a, &9faf
.adlc_rx_listen
    lda #&82                                                          ; 9f7f: a9 82       ..             ; CR1=&82: TX_RESET | RIE (TX in reset, RX interrupts enabled)
    sta econet_control1_or_status1                                    ; 9f81: 8d a0 fe    ...            ; Write to ADLC CR1
    lda #&67 ; 'g'                                                    ; 9f84: a9 67       .g             ; CR2=&67: CLR_TX_ST | CLR_RX_ST | FC_TDRA | 2_1_BYTE | PSE
    sta econet_control23_or_status2                                   ; 9f86: 8d a1 fe    ...            ; Write to ADLC CR2
    rts                                                               ; 9f89: 60          `              ; Return; ADLC now in RX listen mode

; ***************************************************************************************
; Wait for idle NMI state and reset Econet
; 
; Called via svc_12_nmi_release (&06D4). Checks if Econet has been
; initialised; if not, skips to adlc_rx_listen. If initialised,
; spins until the NMI handler is idle (pointing at nmi_rx_scout),
; then falls through to save_econet_state to clear flags and
; re-enter RX listen mode.
; ***************************************************************************************
; &9f8a referenced 1 time by &06f1[4]
.wait_idle_and_reset
    bit econet_init_flag                                              ; 9f8a: 2c 66 0d    ,f.            ; Econet not initialised -- skip to adlc_rx_listen
    bpl reset_enter_listen                                            ; 9f8d: 10 20       .              ; Not initialised: skip to RX listen
; &9f8f referenced 2 times by &9f94, &9f9b
.poll_nmi_idle
    lda nmi_jmp_lo                                                    ; 9f8f: ad 0c 0d    ...            ; Spin until NMI handler = &96DF (nmi_rx_scout)
    cmp #&df                                                          ; 9f92: c9 df       ..             ; Expected: &DF (nmi_rx_scout low)
    bne poll_nmi_idle                                                 ; 9f94: d0 f9       ..             ; Not idle: spin and wait
    lda nmi_jmp_hi                                                    ; 9f96: ad 0d 0d    ...            ; Read current NMI handler high byte
    cmp #&96                                                          ; 9f99: c9 96       ..             ; Expected: &96 (nmi_rx_scout high)
    bne poll_nmi_idle                                                 ; 9f9b: d0 f2       ..             ; Not idle: spin and wait
    lda #&40 ; '@'                                                    ; 9f9d: a9 40       .@             ; A=&40: RTI opcode (disable NMI processing)
    sta l0d1c                                                         ; 9f9f: 8d 1c 0d    ...            ; Self-modify NMI shim at &0D1C: disable
; ***************************************************************************************
; Reset Econet flags and enter RX listen
; 
; Disables NMIs via INTOFF (BIT &FE18), clears tx_clear_flag and
; econet_init_flag to zero, then falls through to adlc_rx_listen
; with Y=5.
; ***************************************************************************************
.save_econet_state
    bit station_id_disable_net_nmis                                   ; 9fa2: 2c 18 fe    ,..            ; INTOFF: disable NMIs
    lda #0                                                            ; 9fa5: a9 00       ..             ; Clear both flags
    sta tx_clear_flag                                                 ; 9fa7: 8d 62 0d    .b.            ; TX not in progress
    sta econet_init_flag                                              ; 9faa: 8d 66 0d    .f.            ; Econet not initialised
    ldy #5                                                            ; 9fad: a0 05       ..             ; Y=5: service call workspace page
; &9faf referenced 1 time by &9f8d
.reset_enter_listen
listen_jmp_hi = reset_enter_listen+2
    jmp adlc_rx_listen                                                ; 9faf: 4c 7f 9f    L..            ; Set ADLC to RX listen mode

; &9fb1 referenced 1 time by &96ba
; ***************************************************************************************
; Bootstrap NMI entry point (in ROM)
; 
; An alternate NMI handler that lives in the ROM itself rather than
; in the RAM workspace at &0D00. Unlike the RAM shim (which uses a
; self-modifying JMP to dispatch to different handlers), this one
; hardcodes JMP nmi_rx_scout (&96DF). Used as the initial NMI handler
; before the workspace has been properly set up during initialisation.
; Same sequence as the RAM shim: BIT &FE18 (INTOFF), PHA, TYA, PHA,
; LDA romsel, STA &FE30, JMP &96DF.
; ***************************************************************************************
.nmi_bootstrap_entry
    bit station_id_disable_net_nmis                                   ; 9fb2: 2c 18 fe    ,..            ; INTOFF: disable NMIs while switching ROM
    pha                                                               ; 9fb5: 48          H              ; Save A
    tya                                                               ; 9fb6: 98          .              ; Transfer Y to A
    pha                                                               ; 9fb7: 48          H              ; Save Y (via A)
    lda #0                                                            ; 9fb8: a9 00       ..             ; ROM bank 0 (patched during init for actual bank)
    sta romsel                                                        ; 9fba: 8d 30 fe    .0.            ; Select Econet ROM bank via ROMSEL
    jmp nmi_rx_scout                                                  ; 9fbd: 4c df 96    L..            ; Jump to scout handler in ROM

; ***************************************************************************************
; ROM copy of set_nmi_vector + nmi_rti
; 
; A version of the NMI vector-setting subroutine and RTI sequence
; that lives in ROM. The RAM workspace copy at &0D0E/&0D14 is the
; one normally used at runtime; this ROM copy is used during early
; initialisation before the RAM workspace has been set up, and as
; the source for the initial copy to RAM.
; ***************************************************************************************
.rom_set_nmi_vector
    sty nmi_jmp_hi                                                    ; 9fc0: 8c 0d 0d    ...            ; Store handler high byte at &0D0D
    sta nmi_jmp_lo                                                    ; 9fc3: 8d 0c 0d    ...            ; Store handler low byte at &0D0C
    lda romsel_copy                                                   ; 9fc6: a5 f4       ..             ; Restore NFS ROM bank
    sta romsel                                                        ; 9fc8: 8d 30 fe    .0.            ; Page in via hardware latch
    pla                                                               ; 9fcb: 68          h              ; Restore Y from stack
    tay                                                               ; 9fcc: a8          .              ; Transfer ROM bank to Y
    pla                                                               ; 9fcd: 68          h              ; Restore A from stack
    bit video_ula_control                                             ; 9fce: 2c 20 fe    , .            ; INTON: re-enable NMIs
    rti                                                               ; 9fd1: 40          @              ; Return from interrupt

    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; 9fd2: ff ff ff... ...            ; &FF padding (unused ROM space)
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; 9fde: ff ff ff... ...
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; 9fea: ff ff ff... ...
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff             ; 9ff6: ff ff ff... ...
.pydis_end

    assert <(dispatch_net_cmd-1) == &6a
    assert <(econet_restore-1) == &58
    assert <(econet_save-1) == &55
    assert <(econet_tx_rx-1) == &f2
    assert <(fscv_0_opt_entry-1) == &19
    assert <(fscv_1_eof-1) == &9a
    assert <(fscv_2_star_run-1) == &de
    assert <(fscv_3_star_cmd-1) == &08
    assert <(fscv_5_cat-1) == &54
    assert <(fscv_6_shutdown-1) == &3e
    assert <(fscv_7_read_handles-1) == &b8
    assert <(fsreply_0_print_dir-1) == &83
    assert <(fsreply_1_copy_handles_boot-1) == &3a
    assert <(fsreply_2_copy_handles-1) == &3b
    assert <(fsreply_3_set_csd-1) == &34
    assert <(fsreply_4_notify_exec-1) == &e4
    assert <(fsreply_5_set_lib-1) == &2f
    assert <(lang_0_insert_remote_key-1) == &ea
    assert <(lang_1_remote_boot-1) == &9c
    assert <(lang_2_save_palette_vdu-1) == &ad
    assert <(lang_3_execute_at_0100-1) == &ca
    assert <(lang_4_remote_validated-1) == &da
    assert <(net_1_read_handle-1) == &69
    assert <(net_2_read_handle_entry-1) == &6f
    assert <(net_3_close_handle-1) == &7f
    assert <(net_4_resume_remote-1) == &a9
    assert <(net_write_char_handler-1) == &b8
    assert <(osword_0f_handler-1) == &c4
    assert <(osword_10_handler-1) == &7e
    assert <(osword_11_handler-1) == &de
    assert <(osword_12_dispatch-1) == &03
    assert <(printer_select_handler-1) == &dd
    assert <(remote_cmd_dispatch-1) == &ea
    assert <(remote_osword_handler-1) == &56
    assert <(remote_print_handler-1) == &ec
    assert <(return_1-1) == &f1
    assert <(rx_imm_exec-1) == &a2
    assert <(rx_imm_halt_cont-1) == &f7
    assert <(rx_imm_machine_type-1) == &cb
    assert <(rx_imm_peek-1) == &dd
    assert <(rx_imm_poke-1) == &c0
    assert <(svc5_irq_check-1) == &5b
    assert <(svc_13_select_nfs-1) == &de
    assert <(svc_1_abs_workspace-1) == &a9
    assert <(svc_2_private_workspace-1) == &b2
    assert <(svc_3_autoboot-1) == &0a
    assert <(svc_4_star_command-1) == &a2
    assert <(svc_8_osword-1) == &89
    assert <(svc_9_help-1) == &f5
    assert <(tube_osword_pb) == &28
    assert >(dispatch_net_cmd-1) == &80
    assert >(econet_restore-1) == &96
    assert >(econet_save-1) == &96
    assert >(econet_tx_rx-1) == &8f
    assert >(fscv_0_opt_entry-1) == &8a
    assert >(fscv_1_eof-1) == &88
    assert >(fscv_2_star_run-1) == &8d
    assert >(fscv_3_star_cmd-1) == &8c
    assert >(fscv_5_cat-1) == &8c
    assert >(fscv_6_shutdown-1) == &83
    assert >(fscv_7_read_handles-1) == &86
    assert >(fsreply_0_print_dir-1) == &8d
    assert >(fsreply_1_copy_handles_boot-1) == &8e
    assert >(fsreply_2_copy_handles-1) == &8e
    assert >(fsreply_3_set_csd-1) == &8e
    assert >(fsreply_4_notify_exec-1) == &8d
    assert >(fsreply_5_set_lib-1) == &8e
    assert >(lang_0_insert_remote_key-1) == &84
    assert >(lang_1_remote_boot-1) == &84
    assert >(lang_2_save_palette_vdu-1) == &92
    assert >(lang_3_execute_at_0100-1) == &84
    assert >(lang_4_remote_validated-1) == &84
    assert >(net_1_read_handle-1) == &8e
    assert >(net_2_read_handle_entry-1) == &8e
    assert >(net_3_close_handle-1) == &8e
    assert >(net_4_resume_remote-1) == &81
    assert >(net_write_char_handler-1) == &90
    assert >(osword_0f_handler-1) == &8e
    assert >(osword_10_handler-1) == &8f
    assert >(osword_11_handler-1) == &8e
    assert >(osword_12_dispatch-1) == &8f
    assert >(printer_select_handler-1) == &91
    assert >(remote_cmd_dispatch-1) == &90
    assert >(remote_osword_handler-1) == &91
    assert >(remote_print_handler-1) == &91
    assert >(return_1-1) == &80
    assert >(svc5_irq_check-1) == &96
    assert >(svc_13_select_nfs-1) == &81
    assert >(svc_1_abs_workspace-1) == &82
    assert >(svc_2_private_workspace-1) == &82
    assert >(svc_3_autoboot-1) == &82
    assert >(svc_4_star_command-1) == &81
    assert >(svc_8_osword-1) == &8e
    assert >(svc_9_help-1) == &81
    assert >(tube_osword_pb) == &01
    assert copyright - rom_header == &0c
    assert tube_osargs == &055e
    assert tube_osbget == &052d
    assert tube_osbput == &0520
    assert tube_osbyte_2param == &05f2
    assert tube_osbyte_long == &0607
    assert tube_oscli == &0596
    assert tube_osfile == &05a9
    assert tube_osfind == &0542
    assert tube_osgbpb == &05d1
    assert tube_osrdch == &0537
    assert tube_osword == &0627
    assert tube_osword_rdln == &0668

save pydis_start, pydis_end

; Label references by decreasing frequency:
;     nfs_workspace:                           55
;     econet_control23_or_status2:             46
;     fs_options:                              41
;     econet_data_continue_frame:              37
;     fs_cmd_data:                             37
;     econet_control1_or_status1:              33
;     net_rx_ptr:                              33
;     port_ws_offset:                          33
;     tx_flags:                                27
;     osword_pb_ptr:                           26
;     net_tx_ptr:                              23
;     osbyte:                                  23
;     port_buf_len:                            22
;     tube_read_r2:                            21
;     open_port_buf_hi:                        16
;     fs_load_addr_2:                          15
;     set_nmi_vector:                          15
;     fs_func_code:                            14
;     fs_load_addr:                            14
;     nmi_tx_block:                            14
;     open_port_buf:                           14
;     rx_flags:                                14
;     tube_send_r2:                            14
;     ws_page:                                 14
;     port_buf_len_hi:                         13
;     print_inline:                            13
;     station_id_disable_net_nmis:             13
;     ws_ptr_lo:                               13
;     nmi_error_dispatch:                      12
;     prepare_fs_cmd:                          12
;     tube_data_register_2:                    11
;     tx_result_fail:                          11
;     nfs_workspace_hi:                        10
;     svc_state:                               10
;     tube_addr_claim:                         10
;     tube_data_register_3:                    10
;     tube_status_register_2:                  10
;     net_tx_ptr_hi:                            9
;     rx_src_stn:                               9
;     txcb_end:                                 9
;     txcb_start:                               9
;     fs_error_ptr:                             8
;     table_idx:                                8
;     tube_send_r4:                             8
;     tube_status_1_and_tube_control:           8
;     escapable:                                7
;     fs_cmd_csd:                               7
;     fs_cmd_urd:                               7
;     fs_crc_lo:                                7
;     fs_work_4:                                7
;     install_nmi_handler:                      7
;     prot_flags:                               7
;     reject_reply:                             7
;     restore_args_return:                      7
;     rx_buf_offset:                            7
;     tube_claimed_id:                          7
;     tx_clear_flag:                            7
;     tx_dst_stn:                               7
;     zp_ptr_lo:                                7
;     copy_string_to_cmd:                       6
;     fs_block_offset:                          6
;     fs_last_byte_flag:                        6
;     fs_load_addr_hi:                          6
;     net_rx_ptr_hi:                            6
;     nmi_rti:                                  6
;     osasci:                                   6
;     tube_main_loop:                           6
;     zp_ptr_hi:                                6
;     copy_filename:                            5
;     dispatch:                                 5
;     error_block:                              5
;     fs_boot_option:                           5
;     fs_data_count:                            5
;     fs_load_addr_3:                           5
;     infol2:                                   5
;     need_release_tube:                        5
;     os_text_ptr:                              5
;     printer_buf_ptr:                          5
;     prot_status:                              5
;     restore_xy_return:                        5
;     rx_ctrl:                                  5
;     rx_port:                                  5
;     scout_error:                              5
;     scout_status:                             5
;     set_fs_flag:                              5
;     stk_frame_p:                              5
;     tube_flag:                                5
;     tube_send_r1:                             5
;     tx_dst_net:                               5
;     waitfs:                                   5
;     clear_jsr_protection:                     4
;     copy_param_workspace:                     4
;     data_tx_last:                             4
;     discard_listen:                           4
;     discard_reset_listen:                     4
;     econet_init_flag:                         4
;     error_text:                               4
;     escape_flag:                              4
;     fs_cmd_context:                           4
;     fs_crflag:                                4
;     fs_eof_flags:                             4
;     fs_sequence_nos:                          4
;     fs_server_net:                            4
;     init_tx_ctrl_block:                       4
;     l0d1c:                                    4
;     l0d58:                                    4
;     nmi_next_hi:                              4
;     nmi_next_lo:                              4
;     osbyte_a_copy:                            4
;     osnewl:                                   4
;     osrdsc_ptr:                               4
;     osword_flag:                              4
;     restore_ay_return:                        4
;     return_a_zero:                            4
;     romsel_copy:                              4
;     rx_src_net:                               4
;     tube_reply_byte:                          4
;     tx_done_exit:                             4
;     tx_length:                                4
;     tx_poll_ff:                               4
;     txcb_ctrl:                                4
;     txcb_port:                                4
;     video_ula_control:                        4
;     ws_ptr_hi:                                4
;     addr_work:                                3
;     adlc_full_reset:                          3
;     calc_handle_offset:                       3
;     check_tube_irq_loop:                      3
;     clear_fs_flag:                            3
;     data_rx_complete:                         3
;     data_tx_check_fifo:                       3
;     dispatch_remote_osbyte:                   3
;     fs_csd_handle:                            3
;     fs_getb_buf:                              3
;     fs_messages_flag:                         3
;     fs_server_stn:                            3
;     fs_spool0:                                3
;     fs_spool_handle:                          3
;     fs_urd_handle:                            3
;     fs_work_7:                                3
;     handle_to_mask_a:                         3
;     inc_buf_counter_32:                       3
;     incpx:                                    3
;     match_osbyte_code:                        3
;     next_port_slot:                           3
;     nmi_jmp_hi:                               3
;     nmi_jmp_lo:                               3
;     nmi_tx_block_hi:                          3
;     openl4:                                   3
;     oscli:                                    3
;     osword:                                   3
;     oswrch:                                   3
;     port_match_found:                         3
;     print_reply_bytes:                        3
;     read_last_rx_byte:                        3
;     return_1:                                 3
;     return_inc_port_buf:                      3
;     rom_ws_table:                             3
;     rx_complete_update_rxcb:                  3
;     save_fscv_args:                           3
;     save_fscv_args_with_ptrs:                 3
;     setup_tx_and_send:                        3
;     system_via_acr:                           3
;     test_inactive_retry:                      3
;     tube_claim_loop:                          3
;     tube_data_register_1:                     3
;     tube_read_string:                         3
;     tube_reply_ack:                           3
;     tube_xfer_page:                           3
;     tx_active_start:                          3
;     tx_calc_transfer:                         3
;     tx_ctrl_upper:                            3
;     tx_index:                                 3
;     write_second_tube_byte:                   3
;     zp_work_3:                                3
;     ack_tx:                                   2
;     ack_tx_write_dest:                        2
;     adjust_addrs:                             2
;     adlc_rx_listen:                           2
;     advance_rx_buffer_ptr:                    2
;     binary_version:                           2
;     brk_ptr:                                  2
;     call_fscv_shutdown:                       2
;     cb_template_main_start:                   2
;     cbset2:                                   2
;     check_disable_flag:                       2
;     check_escape:                             2
;     check_rom_end:                            2
;     check_svc_12:                             2
;     claim_addr_ff:                            2
;     clear_escapable:                          2
;     compare_addresses:                        2
;     copy_filename_to_cmd:                     2
;     copy_load_addr_from_params:               2
;     copy_reply_to_caller:                     2
;     copy_reply_to_params:                     2
;     copy_scout_via_tube:                      2
;     ctrl_block_setup_alt:                     2
;     data_rx_tube_complete:                    2
;     decode_attribs_5bit:                      2
;     decode_attribs_6bit:                      2
;     discard_no_match:                         2
;     dispatch_nmi_error:                       2
;     econet_tx_retry:                          2
;     exec_local:                               2
;     execute_downloaded:                       2
;     fallback_calc_transfer:                   2
;     flush_output_block:                       2
;     fs_access_level:                          2
;     fs_cmd_lib:                               2
;     fs_cmd_match_table:                       2
;     fs_cmd_y_param:                           2
;     fs_crc_hi:                                2
;     fs_error_flags:                           2
;     fs_file_len_3:                            2
;     fs_filename_buf:                          2
;     fs_handle_mask:                           2
;     fs_last_error:                            2
;     fs_lib_handle:                            2
;     fs_obj_type:                              2
;     fs_putb_buf:                              2
;     fs_reply_cmd:                             2
;     fs_state_deb:                             2
;     fs_work_5:                                2
;     gbpb_done:                                2
;     gsinit:                                   2
;     gsread:                                   2
;     handle_mask_exit:                         2
;     handle_to_mask_clc:                       2
;     imm_op_out_of_range:                      2
;     init_tx_ctrl_data:                        2
;     install_rx_scout_handler:                 2
;     jmp_restore_args:                         2
;     l0d1e:                                    2
;     l0d59:                                    2
;     language_entry:                           2
;     load_handle_calc_offset:                  2
;     mask_to_handle:                           2
;     match_rom_string:                         2
;     nlisne:                                   2
;     not_svc_12_nfs:                           2
;     option_name_offsets:                      2
;     os_text_ptr_hi:                           2
;     osarg1:                                   2
;     osfind:                                   2
;     osrdch:                                   2
;     osword_pb_ptr_hi:                         2
;     pad_filename_space:                       2
;     parse_decimal:                            2
;     parse_filename_gs:                        2
;     poll_nmi_idle:                            2
;     poll_tube_ready:                          2
;     prepare_cmd_clv:                          2
;     prepare_fs_cmd_v:                         2
;     print_cr:                                 2
;     print_decimal:                            2
;     print_decimal_digit:                      2
;     print_digit:                              2
;     print_dir_from_offset:                    2
;     print_filename_char:                      2
;     print_hex_byte:                           2
;     print_hex_bytes:                          2
;     print_reply_counted:                      2
;     prlp1:                                    2
;     pydis_start:                              2
;     read_station_id:                          2
;     readc1:                                   2
;     reenable_rx:                              2
;     release_tube:                             2
;     remot1:                                   2
;     restore_ws_return:                        2
;     return_3:                                 2
;     return_7:                                 2
;     return_match_osbyte:                      2
;     return_nbyte:                             2
;     return_printer_select:                    2
;     return_tube_init:                         2
;     rom_header:                               2
;     romsel:                                   2
;     run_fscv_cmd:                             2
;     rx_extra_byte:                            2
;     rxpol2:                                   2
;     saved_jsr_mask:                           2
;     scan_for_colon:                           2
;     scout_complete:                           2
;     scout_copy_done:                          2
;     send_ack:                                 2
;     send_data_blocks:                         2
;     send_data_rx_ack:                         2
;     send_fs_reply_cmd:                        2
;     setup_tx_ptr_c0:                          2
;     skip_addr_carry:                          2
;     skip_nmi_release:                         2
;     skip_space_next:                          2
;     skip_spaces:                              2
;     skip_stn_parse:                           2
;     start_adlc_tx:                            2
;     stk_frame_3:                              2
;     stk_timeout_mid:                          2
;     store_handle_return:                      2
;     store_output_byte:                        2
;     store_rom_ptr_pair:                       2
;     store_tube_flag:                          2
;     store_tx_error:                           2
;     string_buf:                               2
;     sub_3_from_y:                             2
;     terminate_filename:                       2
;     transfer_file_blocks:                     2
;     try_nfs_port_list:                        2
;     tube_claim_flag:                          2
;     tube_data_ptr:                            2
;     tube_dispatch_table:                      2
;     tube_init_reloc:                          2
;     tube_osword_pb:                           2
;     tube_osword_read_lp:                      2
;     tube_poll_r2_result:                      2
;     tube_rdch_reply:                          2
;     tube_status_register_4_and_cpu_control:   2
;     tube_transfer_addr:                       2
;     tube_xfer_addr_2:                         2
;     tube_xfer_addr_3:                         2
;     tx_abort:                                 2
;     tx_ctrl_byte:                             2
;     tx_port:                                  2
;     tx_result_ok:                             2
;     tx_retry_delay:                           2
;     tx_src_stn:                               2
;     tx_store_result:                          2
;     tx_tdra_error:                            2
;     zp_work_2:                                2
;     accept_frame:                             1
;     accept_local_net:                         1
;     accept_new_claim:                         1
;     accept_scout_net:                         1
;     access_bit_table:                         1
;     ack_tx_configure:                         1
;     add_4_to_y:                               1
;     add_5_to_y:                               1
;     add_bytes_loop:                           1
;     add_rxcb_ptr:                             1
;     addr_claim_external:                      1
;     adjust_addr_byte:                         1
;     adjust_addrs_1:                           1
;     adjust_addrs_9:                           1
;     adjust_addrs_clc:                         1
;     adlc_init:                                1
;     argsv_check_return:                       1
;     argsv_fs_query:                           1
;     argsw:                                    1
;     attrib_error_exit:                        1
;     attrib_shift_bits:                        1
;     bgetv_entry:                              1
;     bgetv_shared_jsr:                         1
;     boot_string_offsets:                      1
;     brkv:                                     1
;     bspsx:                                    1
;     bsxl0:                                    1
;     bsxl1:                                    1
;     build_send_fs_cmd:                        1
;     bytex:                                    1
;     c9c15:                                    1
;     c9c1f:                                    1
;     c9c58:                                    1
;     calc_peek_poke_size:                      1
;     calc_transfer_size:                       1
;     cat_column_separator:                     1
;     cb_template_tail:                         1
;     cbset3:                                   1
;     cbset4:                                   1
;     cha4:                                     1
;     cha5:                                     1
;     cha5lp:                                   1
;     cha6:                                     1
;     chalp1:                                   1
;     chalp2:                                   1
;     check_attrib_result:                      1
;     check_break_type:                         1
;     check_fs_error:                           1
;     check_fv_final_ack:                       1
;     check_handshake_bit:                      1
;     check_irq_loop:                           1
;     check_opt1:                               1
;     check_port_slot:                          1
;     check_scout_done:                         1
;     check_sr2_loop_again:                     1
;     check_station_filter:                     1
;     check_svc_high:                           1
;     clamp_dest_addr:                          1
;     clear_osbyte_ce_cf:                       1
;     clear_osbyte_masks:                       1
;     clear_release_flag:                       1
;     cloop:                                    1
;     close_handle:                             1
;     close_opt_return:                         1
;     close_single_handle:                      1
;     close_spool_exec:                         1
;     cmd_match_data:                           1
;     compare_addr_byte:                        1
;     copro_ack_nmi_check:                      1
;     copy_addr_loop:                           1
;     copy_attribs_reply:                       1
;     copy_bcast_addr:                          1
;     copy_block_addrs:                         1
;     copy_dir_handles:                         1
;     copy_error_message:                       1
;     copy_error_to_brk:                        1
;     copy_filename_ptr:                        1
;     copy_fileptr_reply:                       1
;     copy_fileptr_to_cmd:                      1
;     copy_fs_addr:                             1
;     copy_fs_reply_to_cb:                      1
;     copy_fs_vectors:                          1
;     copy_handles_loop:                        1
;     copy_handles_to_ws:                       1
;     copy_imm_params:                          1
;     copy_load_end_addr:                       1
;     copy_nmi_shim:                            1
;     copy_nmi_workspace:                       1
;     copy_osword_params:                       1
;     copy_param_ptr:                           1
;     copy_params_rword:                        1
;     copy_reply_bytes:                         1
;     copy_rxcb_to_param:                       1
;     copy_save_params:                         1
;     copy_scout_bytes:                         1
;     copy_scout_to_buffer:                     1
;     copy_string_from_offset:                  1
;     copyright_offset:                         1
;     ctrl_block_setup:                         1
;     ctrl_block_setup_clv:                     1
;     ctrl_block_template:                      1
;     data_rx_loop:                             1
;     data_tx_begin:                            1
;     data_tx_error:                            1
;     decfir:                                   1
;     decmin:                                   1
;     decmor:                                   1
;     delay_between_tx:                         1
;     delay_nmi_disable:                        1
;     dispatch_0_hi-1:                          1
;     dispatch_0_lo-1:                          1
;     dispatch_cmd:                             1
;     dispatch_fs_error:                        1
;     dispatch_imm_op:                          1
;     divide_subtract:                          1
;     do_svc_dispatch:                          1
;     dofs01:                                   1
;     dofs2:                                    1
;     dofsl5:                                   1
;     dofsl7:                                   1
;     done_option_name:                         1
;     econet_data_terminate_frame:              1
;     enable_irq_and_tx:                        1
;     entry1:                                   1
;     error1:                                   1
;     error_code_clamped:                       1
;     error_msg_table:                          1
;     error_not_listening:                      1
;     error_offsets:                            1
;     evntv:                                    1
;     fetch_dir_batch:                          1
;     file1:                                    1
;     filev:                                    1
;     filev_attrib_dispatch:                    1
;     filev_save:                               1
;     floop:                                    1
;     fs2al1:                                   1
;     fs_addr_check:                            1
;     fs_boot_data:                             1
;     fs_cmd_type:                              1
;     fs_context_base:                          1
;     fs_context_hi:                            1
;     fs_dispatch_addrs:                        1
;     fs_error_buf:                             1
;     fs_file_attrs:                            1
;     fs_file_len:                              1
;     fs_len_clear:                             1
;     fs_load_upper:                            1
;     fs_load_vector:                           1
;     fs_osword_dispatch:                       1
;     fs_osword_tbl_hi:                         1
;     fs_reply_data:                            1
;     fs_reply_stn:                             1
;     fs_wait_cleanup:                          1
;     fs_work_16:                               1
;     fscv:                                     1
;     fscv_3_star_cmd:                          1
;     fsdiel:                                   1
;     fstxl1:                                   1
;     fstxl2:                                   1
;     gbpb6_read_name:                          1
;     gbpb8_read_dir:                           1
;     gbpb_invalid_exit:                        1
;     gbpb_read_path:                           1
;     gbpb_write_path:                          1
;     gbpbe1:                                   1
;     gbpbf1:                                   1
;     gbpbf2:                                   1
;     gbpbf3:                                   1
;     gbpbl1:                                   1
;     gbpbl3:                                   1
;     gbpbx:                                    1
;     gbpbx0:                                   1
;     gbpbx1:                                   1
;     get_disc_title:                           1
;     get_file_protection:                      1
;     got_station_num:                          1
;     halt_spin_loop:                           1
;     halve_args_a:                             1
;     handle_to_mask:                           1
;     handle_tx_result:                         1
;     handshake_await_ack:                      1
;     imm_op_build_reply:                       1
;     imm_op_discard:                           1
;     imm_op_dispatch_lo-&81:                   1
;     immediate_op:                             1
;     inc_rxcb_ptr:                             1
;     info2:                                    1
;     init_adlc_hw:                             1
;     init_cat_params:                          1
;     init_fs_vectors:                          1
;     init_nmi_workspace:                       1
;     init_rxcb_entries:                        1
;     init_tx_ctrl_port:                        1
;     init_tx_reply_port:                       1
;     init_vectors_and_copy:                    1
;     initl:                                    1
;     install_data_rx_handler:                  1
;     install_imm_data_nmi:                     1
;     install_reply_scout:                      1
;     install_saved_handler:                    1
;     install_tube_rx:                          1
;     issue_vectors_claimed:                    1
;     jump_via_addr:                            1
;     l0063:                                    1
;     l0701:                                    1
;     l4655:                                    1
;     l7845:                                    1
;     l7dfd:                                    1
;     lang_entry_dispatch:                      1
;     language_handler:                         1
;     language_handler_hi:                      1
;     language_handler_lo:                      1
;     listen_jmp_hi:                            1
;     loadop:                                   1
;     lodchk:                                   1
;     lodfil:                                   1
;     lodrl1:                                   1
;     lodrl2:                                   1
;     logon2:                                   1
;     map_attrib_bits:                          1
;     match_cmd_chars:                          1
;     match_net_cmd:                            1
;     mj:                                       1
;     nbyte1:                                   1
;     nbyte4:                                   1
;     nbyte5:                                   1
;     nbyte6:                                   1
;     netv:                                     1
;     next_dir_entry:                           1
;     next_rom_page:                            1
;     next_scout_byte:                          1
;     nlistn:                                   1
;     nmi_code_base:                            1
;     nmi_data_rx_bulk:                         1
;     nmi_data_rx_skip:                         1
;     nmi_final_ack_validate:                   1
;     nmi_reply_validate:                       1
;     nmi_rx_scout:                             1
;     nmi_shim_07:                              1
;     nmi_shim_1a:                              1
;     nmi_sub_table:                            1
;     nmi_workspace_start:                      1
;     no_dot_exit:                              1
;     no_page_wrap:                             1
;     num01:                                    1
;     openl6:                                   1
;     openl7:                                   1
;     opt_return:                               1
;     opter1:                                   1
;     optl1:                                    1
;     osargs:                                   1
;     osbget:                                   1
;     osbput:                                   1
;     oseven:                                   1
;     osfile:                                   1
;     osgbpb:                                   1
;     osgbpb_info:                              1
;     osrdsc_ptr_hi:                            1
;     osword_12_offsets:                        1
;     osword_handler_lo:                        1
;     osword_tbl_hi:                            1
;     osword_tbl_lo:                            1
;     osword_trampoline:                        1
;     parse_decimal_rts:                        1
;     parse_filename_gs_y:                      1
;     poll_r2_osword_result:                    1
;     poll_r4_copro_ack:                        1
;     poll_rxcb_flag:                           1
;     poll_tx_complete:                         1
;     poll_tx_semaphore:                        1
;     prepare_cmd_dispatch:                     1
;     prepare_cmd_with_flag:                    1
;     print_addresses:                          1
;     print_hex_nibble:                         1
;     print_inline_char:                        1
;     print_newline:                            1
;     print_next_char:                          1
;     print_option_name:                        1
;     print_public:                             1
;     print_space:                              1
;     print_station_info:                       1
;     print_user_env:                           1
;     process_entries:                          1
;     quote1:                                   1
;     rchex:                                    1
;     read_args_size:                           1
;     read_local_station_id:                    1
;     read_osargs_params:                       1
;     read_osgbpb_ctrl_blk:                     1
;     read_rdln_ctrl_block:                     1
;     read_remote_cmd_line:                     1
;     read_rxcb:                                1
;     read_second_rx_byte:                      1
;     read_sr2_between_pairs:                   1
;     read_vdu_osbyte:                          1
;     read_vdu_osbyte_x0:                       1
;     readry:                                   1
;     rearm_tx_attempt:                         1
;     reloc_p4_src:                             1
;     reloc_p5_src:                             1
;     reloc_p6_src:                             1
;     reloc_zp_src:                             1
;     remote_osbyte_table:                      1
;     reset_enter_listen:                       1
;     restore_x_and_return:                     1
;     return_10:                                1
;     return_2:                                 1
;     return_4:                                 1
;     return_5:                                 1
;     return_6:                                 1
;     return_8:                                 1
;     return_calc_handle:                       1
;     return_compare:                           1
;     return_dofsl7:                            1
;     return_last_error:                        1
;     return_lodchk:                            1
;     return_remote_cmd:                        1
;     rom_type:                                 1
;     rotate_prot_mask:                         1
;     rsl1:                                     1
;     rssl1:                                    1
;     rssl2:                                    1
;     rx_error:                                 1
;     rx_error_reset:                           1
;     rx_remote_addr:                           1
;     rx_tube_data:                             1
;     rxcb_matched:                             1
;     savchk:                                   1
;     save1:                                    1
;     save_args_handle:                         1
;     save_csd_display:                         1
;     save_palette_entry:                       1
;     save_vdu_state:                           1
;     saveop:                                   1
;     savsiz:                                   1
;     scan0:                                    1
;     scan1:                                    1
;     scan_cmd_table:                           1
;     scan_copyright_end:                       1
;     scan_decimal_digit:                       1
;     scan_entry_terminator:                    1
;     scan_nfs_port_list:                       1
;     scan_port_list:                           1
;     scout_discard:                            1
;     scout_loop_rda:                           1
;     scout_loop_second:                        1
;     scout_match_port:                         1
;     scout_page_overflow:                      1
;     scout_reject:                             1
;     send_block:                               1
;     send_block_loop:                          1
;     send_data_bytes:                          1
;     send_fs_cmd_v1:                           1
;     send_fs_examine:                          1
;     send_osargs_result:                       1
;     send_osfile_ctrl_blk:                     1
;     send_osgbpb_result:                       1
;     send_rom_page_bytes:                      1
;     send_xfer_addr_bytes:                     1
;     service_entry:                            1
;     service_handler:                          1
;     service_handler_entry:                    1
;     service_handler_lo:                       1
;     set_adlc_disable:                         1
;     set_listen_offset:                        1
;     set_messages_flag:                        1
;     set_tx_reply_flag:                        1
;     set_workspace_page:                       1
;     setup1:                                   1
;     setup_block_addrs:                        1
;     setup_data_xfer:                          1
;     setup_rom_ptrs_netv:                      1
;     setup_rx_buffer_ptrs:                     1
;     setup_unicast_xfer:                       1
;     skip_buf_ptr_update:                      1
;     skip_buf_setup:                           1
;     skip_catalogue_msg:                       1
;     skip_clear_flag:                          1
;     skip_cmd_spaces:                          1
;     skip_copy_reply:                          1
;     skip_flush:                               1
;     skip_gs_filename:                         1
;     skip_kbd_reenable:                        1
;     skip_lodfil:                              1
;     skip_no_clock_msg:                        1
;     skip_param_read:                          1
;     skip_param_write:                         1
;     skip_r3_flush:                            1
;     skip_rx_flag_set:                         1
;     skip_set_attrib_bit:                      1
;     skip_tube_update:                         1
;     start_data_tx:                            1
;     stk_timeout_hi:                           1
;     store_16bit_at_y:                         1
;     store_buf_ptr_lo:                         1
;     store_fs_error:                           1
;     store_fs_flag:                            1
;     store_fs_hdr_clc:                         1
;     store_fs_hdr_fn:                          1
;     store_retry_count:                        1
;     store_status_add4:                        1
;     store_txcb_byte:                          1
;     store_xfer_end_addr:                      1
;     string_buf_done:                          1
;     strnh:                                    1
;     sub_4_from_y:                             1
;     subtract_adjust:                          1
;     svc_dispatch_range:                       1
;     svc_unhandled_return:                     1
;     system_via_ier:                           1
;     system_via_ifr:                           1
;     system_via_sr:                            1
;     tbcop1:                                   1
;     toggle_print_flag:                        1
;     transfer_loop_top:                        1
;     tube_begin:                               1
;     tube_brk_handler:                         1
;     tube_brk_send_loop:                       1
;     tube_chars_done:                          1
;     tube_claim_default:                       1
;     tube_cmd_lo:                              1
;     tube_code_page4:                          1
;     tube_ctrl_values:                         1
;     tube_data_ptr_hi:                         1
;     tube_data_register_4:                     1
;     tube_escape_check:                        1
;     tube_handle_wrch:                         1
;     tube_osbyte_send_y:                       1
;     tube_osfind_close:                        1
;     tube_osword_read:                         1
;     tube_osword_write:                        1
;     tube_osword_write_lp:                     1
;     tube_page6_start:                         1
;     tube_poll_r2:                             1
;     tube_post_init:                           1
;     tube_rdln_send_line:                      1
;     tube_rdln_send_loop:                      1
;     tube_release_claim:                       1
;     tube_reset_stack:                         1
;     tube_return_main:                         1
;     tube_sendw_complete:                      1
;     tube_transfer:                            1
;     tube_transfer_setup:                      1
;     tube_tx_fifo_write:                       1
;     tube_tx_inc_operand:                      1
;     tube_tx_sr1_operand:                      1
;     tx_begin:                                 1
;     tx_ctrl_exit:                             1
;     tx_ctrl_range_check:                      1
;     tx_ctrl_template:                         1
;     tx_data_start:                            1
;     tx_error:                                 1
;     tx_fifo_not_ready:                        1
;     tx_fifo_write:                            1
;     tx_imm_op_setup:                          1
;     tx_last_data:                             1
;     tx_line_idle_check:                       1
;     tx_line_jammed:                           1
;     tx_no_clock_error:                        1
;     tx_src_net:                               1
;     tx_store_error:                           1
;     tx_success_exit:                          1
;     tx_work_51:                               1
;     tx_work_57:                               1
;     txcb_dest:                                1
;     txcb_pos:                                 1
;     update_sequence_return:                   1
;     vdu_colours:                              1
;     vdu_cursor_edit:                          1
;     vdu_osbyte_table:                         1
;     vdu_screen_mode:                          1
;     wait_fs_reply:                            1
;     wait_idle_and_reset:                      1
;     wait_tube_delay:                          1
;     work_ae:                                  1
;     write_second_tx_byte:                     1
;     y2fsl2:                                   1
;     y2fsl5:                                   1
;     zero_cmd_bytes:                           1
;     zero_exec_header:                         1

; Automatically generated labels:
;     c9c15
;     c9c1f
;     c9c58
;     l0063
;     l0701
;     l0d1c
;     l0d1e
;     l0d58
;     l0d59
;     l4655
;     l7845
;     l7dfd
;     sub_c9abe

; Stats:
;     Total size (Code + Data) = 8192 bytes
;     Code                     = 7508 bytes (92%)
;     Data                     = 684 bytes (8%)
;
;     Number of instructions   = 3634
;     Number of data bytes     = 411 bytes
;     Number of data words     = 52 bytes
;     Number of string bytes   = 221 bytes
;     Number of strings        = 36
