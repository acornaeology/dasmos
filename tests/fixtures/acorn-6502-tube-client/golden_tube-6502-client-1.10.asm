; Memory locations
zp_data_base          = &00
; &00 used as index base 2 times by &fbe9, &fc08
zp_data_base_1        = &01
; &01 used as index base 2 times by &fbe4, &fc03
zp_data_base_2        = &02
; &02 used as index base 2 times by &fbdf, &fbfe
zp_data_base_3        = &03
; &03 used as index base 2 times by &fbda, &fbf9
current_program       = &ee
; &ee referenced 7 times by &f844, &f8b7, &f8c3, &f8c7, &f8ee, &fa5f, &fa66
current_program_hi    = &ef
; &ef referenced 5 times by &f848, &f8bd, &f8cd, &fa5c, &fa6b
hex_accumulator       = &f0
; &f0 referenced 3 times by &f988, &f9a7, &fa54
hex_accumulator_hi    = &f1
; &f1 referenced 3 times by &f98a, &f9a9, &fa58
memory_top            = &f2
; &f2 referenced 5 times by &f850, &f8b9, &f8fc, &fa68, &faf0
memory_top_hi         = &f3
; &f3 referenced 4 times by &f854, &f8bf, &fa6d, &faf2
transfer_addr_ptr     = &f4
; &f4 referenced 3 times by &fd7c, &fdab, &fdb6
transfer_addr_ptr_hi  = &f5
; &f5 referenced 1 time by &fd81
data_transfer_addr    = &f6
; &f6 referenced 11 times by &f846, &f8b5, &fa56, &fe27, &fe2c, &fe32, &fe37, &fe49, &fe4b, &fe54, &fe56
data_transfer_addr_hi = &f7
; &f7 referenced 7 times by &f84a, &f8bb, &fa5a, &fe30, &fe3b, &fe4f, &fe5a
string_ptr            = &f8
; &f8 referenced 23 times by &f824, &f82a, &f82c, &f97f, &f98c, &f9b2, &f9bd, &f9cb, &f9dc, &f9f1, &f9fe, &fa0b, &faff, &fb1e, &fb3d, &fb4a, &fb6c, &fb73, &fb83, &fb92, &fb9e, &fbab, &fbba
string_ptr_hi         = &f9
; &f9 referenced 9 times by &f828, &f831, &f833, &f9b4, &f9c7, &f9cd, &fb01, &fb71, &fbae
control_block_ptr     = &fa
; &fa referenced 14 times by &fc55, &fc5f, &fc6a, &fc6e, &fc81, &fc8a, &fc90, &fc9a, &fcab, &fcb2, &fe99, &fea0, &fea6, &feb0
control_block_ptr_hi  = &fb
; &fb referenced 6 times by &fc53, &fc88, &fc8e, &fcb0, &fe9c, &fea4
irq_a_store           = &fc
; &fc referenced 7 times by &fce5, &fd12, &fd33, &fd3c, &fde9, &fe8a, &fe8f
last_error            = &fd
; &fd referenced 7 times by &f8c9, &f8d3, &f8d8, &f8df, &f8e6, &f94d, &fd07
last_error_hi         = &fe
; &fe referenced 2 times by &f8cf, &fd0e
escape_flag           = &ff
; &ff referenced 2 times by &f84e, &fd3a
userv                 = &0200
; &0200 used as index base 1 time by &f810
brkv                  = &0202
; &0202 referenced 3 times by &f901, &f924, &fd15
brkv_hi               = &0203
; &0203 referenced 2 times by &f906, &f929
irq1v                 = &0204
; &0204 referenced 1 time by &fced
irq2v                 = &0206
; &0206 referenced 1 time by &fcfa
cliv                  = &0208
; &0208 referenced 1 time by &fff7
bytev                 = &020a
; &020a referenced 1 time by &fff4
wordv                 = &020c
; &020c referenced 1 time by &fff1
wrchv                 = &020e
; &020e referenced 1 time by &ffee
rdchv                 = &0210
; &0210 referenced 1 time by &ffe0
filev                 = &0212
; &0212 referenced 1 time by &ffdd
argsv                 = &0214
; &0214 referenced 1 time by &ffda
bgetv                 = &0216
; &0216 referenced 1 time by &ffd7
bputv                 = &0218
; &0218 referenced 1 time by &ffd4
gbpbv                 = &021a
; &021a referenced 1 time by &ffd1
findv                 = &021c
; &021c referenced 1 time by &ffce
evntv                 = &0220
; &0220 referenced 1 time by &fd36
error_buffer          = &0236
; &0236 referenced 2 times by &fd4f, &fd62
error_buffer_errnum   = &0237
; &0237 referenced 1 time by &fd56; also used as index base 1 time by &fd5d
soft_reset_jmp        = &f85d
soft_reset_jmp_lo     = &f85e
; &f85e referenced 1 time by &f87e
soft_reset_jmp_hi     = &f85f
; &f85f referenced 1 time by &f883

cpu 1

    org &f859
.reloc_low_memory_src

; Move 1: &f859 to &0100 for length 7
    org &0100
; ***************************************************************************************
; Low memory startup code (relocated from ROM at reloc_low_memory_src)
;
; Copied from ROM to &0100 by the reset routine.
;
; Reads Tube R1 status to page out the ROM, enables interrupts, then jumps to display the
; startup banner. On subsequent soft resets, the JMP target at &F85E is patched to skip
; the banner and enter the command prompt directly.
; &0100 referenced 1 time by &f856; also used as index base 1 time by &f83e
.low_memory_code
.low_memory_startup_code
    lda tube_r1_status                                                ; f859: ad f8 fe    ... :0100[1]        ; Read Tube R1 status to page ROM out
; &0103 used as index base 1 time by &fd00
.irq_return_addr_lo
    cli                                                               ; f85c: 58          X :0103[1]          ; Enable interrupts for data transfers
; &0104 used as index base 1 time by &fd09
.irq_return_addr_hi
    jmp startup_banner                                                ; f85d: 4c 60 f8    L`. :0104[1]        ; Patched after first boot to skip banner


    ; Copy the newly assembled block of code back to it's proper place in the binary
    ; file.
    ; (Note the parameter order: 'copyblock <start>,<end>,<dest>')
    copyblock low_memory_code, *, reloc_low_memory_src

    ; Clear the area of memory we just temporarily used to assemble the new block,
    ; allowing us to assemble there again if needed
    clear low_memory_code, &0107

    ; Set the program counter to the next position in the binary file.
    org reloc_low_memory_src + (* - low_memory_code)


    org &f800

.pydis_start
; ***************************************************************************************
; Power-on reset
;
; Initialise the 65C02 parasite processor.
;
; Copies the ROM contents to RAM, sets up the default MOS vectors, clears the escape
; flag, and jumps via low memory to page out the ROM and start the operating system.
.reset
    ldx #0                                                            ; f800: a2 00       ..       ; Start copy index at 0
; &f802 referenced 1 time by &f809
.copy_page_ff_loop
    lda unused_fill_page_ff,x                                         ; f802: bd 00 ff    ...      ; Read byte from page &FF of ROM
    sta unused_fill_page_ff,x                                         ; f805: 9d 00 ff    ...      ; Copy to RAM (vectors + MOS entries)
    dex                                                               ; f808: ca          .        ; Next byte
    bne copy_page_ff_loop                                             ; f809: d0 f7       ..       ; Loop until all 256 bytes copied
    ldx #&36 ; '6'                                                    ; f80b: a2 36       .6       ; 54 bytes = 27 default vector entries
; &f80d referenced 1 time by &f814
.copy_vectors_loop
    lda default_vector_table,x                                        ; f80d: bd 80 ff    ...      ; Read default vector value
    sta userv,x                                                       ; f810: 9d 00 02    ...      ; Write to MOS vector table
    dex                                                               ; f813: ca          .        ; Next entry
    bpl copy_vectors_loop                                             ; f814: 10 f7       ..       ; Loop until all vectors set
    txs                                                               ; f816: 9a          .        ; Clear the stack (X=&FF from loop)
    ldx #&f0                                                          ; f817: a2 f0       ..       ; X=&F0: copy &FE00-&FEEF to RAM
; &f819 referenced 1 time by &f820
.copy_io_page_loop
    lda io_page_base,x                                                ; f819: bd ff fd    ...      ; Read ROM byte below Tube I/O window
    sta io_page_base,x                                                ; f81c: 9d ff fd    ...      ; Copy to RAM
    dex                                                               ; f81f: ca          .        ; Next byte
    bne copy_io_page_loop                                             ; f820: d0 f7       ..       ; Loop until &FE00-&FEEF copied
    ldy #0                                                            ; f822: a0 00       ..       ; Y=0 for page offset
    sty string_ptr                                                    ; f824: 84 f8       ..       ; Point string_ptr low to &00
    lda #&f8                                                          ; f826: a9 f8       ..       ; High byte = &F8 (start of ROM)
    sta string_ptr_hi                                                 ; f828: 85 f9       ..       ; Set string_ptr to &F800
; &f82a referenced 2 times by &f82f, &f837
.copy_rom_page
    lda (string_ptr),y                                                ; f82a: b1 f8       ..       ; Read byte from ROM page
    sta (string_ptr),y                                                ; f82c: 91 f8       ..       ; Write to RAM (self-copy)
    iny                                                               ; f82e: c8          .        ; Next byte in page
    bne copy_rom_page                                                 ; f82f: d0 f9       ..       ; Loop until 256 bytes copied
    inc string_ptr_hi                                                 ; f831: e6 f9       ..       ; Move to next page
    lda string_ptr_hi                                                 ; f833: a5 f9       ..       ; Get current page number
    cmp #&fe                                                          ; f835: c9 fe       ..       ; Reached Tube I/O window at &FE00?
    bne copy_rom_page                                                 ; f837: d0 f1       ..       ; No, copy next page
    ldx #&10                                                          ; f839: a2 10       ..       ; 17 bytes of startup code to copy
; &f83b referenced 1 time by &f842
.copy_startup_code_loop
    lda reloc_low_memory_src,x                                        ; f83b: bd 59 f8    .Y.      ; Read startup code byte
    sta low_memory_code,x                                             ; f83e: 9d 00 01    ...      ; Write to low memory at &0100
    dex                                                               ; f841: ca          .        ; Next byte
    bpl copy_startup_code_loop                                        ; f842: 10 f7       ..       ; Loop until all startup code copied
    lda current_program                                               ; f844: a5 ee       ..       ; Get current program low byte
    sta data_transfer_addr                                            ; f846: 85 f6       ..       ; Set as transfer address low
    lda current_program_hi                                            ; f848: a5 ef       ..       ; Get current program high byte
    sta data_transfer_addr_hi                                         ; f84a: 85 f7       ..       ; Set as transfer address high
    lda #0                                                            ; f84c: a9 00       ..       ; A=0 for clearing
    sta escape_flag                                                   ; f84e: 85 ff       ..       ; Clear Escape flag
    sta memory_top                                                    ; f850: 85 f2       ..       ; Set memory top low byte to 0
    lda #&f8                                                          ; f852: a9 f8       ..       ; High byte = &F8 (start of ROM)
    sta memory_top_hi                                                 ; f854: 85 f3       ..       ; Set memory top to &F800
    jmp low_memory_code                                               ; f856: 4c 00 01    L..      ; Jump to low memory to page ROM out

    org &f860
; ***************************************************************************************
; Display startup banner and initialise
;
; Print the startup banner, patch the soft reset entry to skip the banner on future
; resets, then wait for the host's acknowledge byte.
;
; If the acknowledge has bit 7 set, the host is requesting code execution; otherwise
; enters the command prompt.
; &f860 referenced 1 time by &f85d
.startup_banner
    jsr print_embedded_text                                           ; f860: 20 98 fe     ..      ; Print inline startup banner string
    equb &0a, "Acorn TUBE 6502 64K", &0a, &0a, &0d, &00               ; f863: 0a 41 63... .Ac...
    nop                                                               ; f87b: ea          .        ; NOP (&EA) terminates string and is executed
    lda #&8d                                                          ; f87c: a9 8d       ..       ; Low byte of command_prompt address
    sta soft_reset_jmp_lo                                             ; f87e: 8d 5e f8    .^.      ; Patch JMP target low byte
    lda #&f8                                                          ; f881: a9 f8       ..       ; High byte of command_prompt address
    sta soft_reset_jmp_hi                                             ; f883: 8d 5f f8    ._.      ; Patch JMP target high byte
    jsr wait_for_tube_r2_byte                                         ; f886: 20 75 f9     u.      ; Wait for host acknowledge byte
    cmp #&80                                                          ; f889: c9 80       ..       ; Is it &80 (enter code)?
    beq enter_code                                                    ; f88b: f0 28       .(       ; Yes, enter transferred code
; ***************************************************************************************
; Command prompt loop
;
; The main supervisor command prompt.
;
; Prints a '*' prompt, reads a line of input using OSWORD 0, and passes it to OSCLI for
; execution. Handles Escape by acknowledging it and reporting the error.
; &f88d referenced 2 times by &f8a4, &f95a
.command_prompt
    lda #&2a ; '*'                                                    ; f88d: a9 2a       .*       ; Print '*' prompt character
    jsr oswrch_entry                                                  ; f88f: 20 ee ff     ..      ; Send '*' via OSWRCH
    ldx #&5d ; ']'                                                    ; f892: a2 5d       .]       ; Low byte of rdline control block
    ldy #&f9                                                          ; f894: a0 f9       ..       ; High byte of rdline control block
    lda #0                                                            ; f896: a9 00       ..       ; OSWORD 0: read line of input
    jsr osword_entry                                                  ; f898: 20 f1 ff     ..      ; Call OSWORD
    bcs command_prompt_escape                                         ; f89b: b0 0a       ..       ; Carry set: Escape was pressed
    ldx #&36 ; '6'                                                    ; f89d: a2 36       .6       ; Low byte of input buffer &0236
    ldy #2                                                            ; f89f: a0 02       ..       ; High byte of input buffer
    jsr oscli_entry                                                   ; f8a1: 20 f7 ff     ..      ; Execute command via OSCLI
    jmp command_prompt                                                ; f8a4: 4c 8d f8    L..      ; Loop back for next command
; &f8a7 referenced 1 time by &f89b
.command_prompt_escape
    lda #&7e ; '~'                                                    ; f8a7: a9 7e       .~       ; OSBYTE &7E: acknowledge Escape
    jsr osbyte_entry                                                  ; f8a9: 20 f4 ff     ..      ; Call OSBYTE
    brk                                                               ; f8ac: 00          .        ; Generate error 17: 'Escape'
    equb &11                                                          ; f8ad: 11          .     
    equs "Escape"                                                     ; f8ae: 45 73 63... Esc...
    equb &00                                                          ; f8b4: 00          .     
; ***************************************************************************************
; Enter code at transfer address
;
; Check whether the code at the data transfer address has a valid ROM header with a (C)
; string, and if so verify it is a 6502 language ROM.
;
; Sets the current program and memory top to the transfer address, then enters the code
; with A=1. If the header is missing or invalid, enters with A=1 anyway (raw code entry).
; Generates an error if the ROM type indicates it is not a language or not 6502 code.
;
; Note: the v1.10 ROM always enters with A=1 regardless of whether it is a RESET or OSCLI
; entry, and does not pass the carry flag. J.G. Harston identifies this as a bug.
; &f8b5 referenced 2 times by &f88b, &fa62
.enter_code
    lda data_transfer_addr                                            ; f8b5: a5 f6       ..       ; Get transfer address low byte
    sta current_program                                               ; f8b7: 85 ee       ..       ; Set as current program low
    sta memory_top                                                    ; f8b9: 85 f2       ..       ; Also set memory top low
    lda data_transfer_addr_hi                                         ; f8bb: a5 f7       ..       ; Get transfer address high byte
    sta current_program_hi                                            ; f8bd: 85 ef       ..       ; Set as current program high
    sta memory_top_hi                                                 ; f8bf: 85 f3       ..       ; Also set memory top high
    ldy #7                                                            ; f8c1: a0 07       ..       ; Offset 7 = copyright string offset
    lda (current_program),y                                           ; f8c3: b1 ee       ..       ; Read copyright offset from header
    cld                                                               ; f8c5: d8          .        ; Clear decimal mode
    clc                                                               ; f8c6: 18          .        ; Clear carry for addition
    adc current_program                                               ; f8c7: 65 ee       e.       ; Add base address to offset
    sta last_error                                                    ; f8c9: 85 fd       ..       ; Store copyright pointer low
    lda #0                                                            ; f8cb: a9 00       ..       ; A=0 for high byte add
    adc current_program_hi                                            ; f8cd: 65 ef       e.       ; Add carry to high byte
    sta last_error_hi                                                 ; f8cf: 85 fe       ..       ; Store copyright pointer high
    ldy #0                                                            ; f8d1: a0 00       ..       ; Y=0 to check first byte
    lda (last_error),y                                                ; f8d3: b1 fd       ..       ; Read byte at copyright pointer
    bne enter_raw_code                                                ; f8d5: d0 23       .#       ; Not zero: no valid header, enter raw
    iny                                                               ; f8d7: c8          .        ; Y=1 to check '('
    lda (last_error),y                                                ; f8d8: b1 fd       ..       ; Read next byte
    cmp #&28 ; '('                                                    ; f8da: c9 28       .(       ; Is it '('?
    bne enter_raw_code                                                ; f8dc: d0 1c       ..       ; No: enter as raw code
    iny                                                               ; f8de: c8          .        ; Y=2 to check 'C'
    lda (last_error),y                                                ; f8df: b1 fd       ..       ; Read next byte
    cmp #&43 ; 'C'                                                    ; f8e1: c9 43       .C       ; Is it 'C'?
    bne enter_raw_code                                                ; f8e3: d0 15       ..       ; No: enter as raw code
    iny                                                               ; f8e5: c8          .        ; Y=3 to check ')'
    lda (last_error),y                                                ; f8e6: b1 fd       ..       ; Read next byte
    cmp #&29 ; ')'                                                    ; f8e8: c9 29       .)       ; Is it ')'?
    bne enter_raw_code                                                ; f8ea: d0 0e       ..       ; No: enter as raw code
    ldy #6                                                            ; f8ec: a0 06       ..       ; Offset 6 = ROM type byte
    lda (current_program),y                                           ; f8ee: b1 ee       ..       ; Read ROM type
    and #&4f ; 'O'                                                    ; f8f0: 29 4f       )O       ; Mask language and CPU type bits
    cmp #&40 ; '@'                                                    ; f8f2: c9 40       .@       ; Bit 6 clear: not a language ROM
    bcc error_not_a_language                                          ; f8f4: 90 09       ..       ; Generate 'not a language' error
    and #&0d                                                          ; f8f6: 29 0d       ).       ; Mask CPU type: 0 or 2 = 6502
    bne error_not_6502_code                                           ; f8f8: d0 28       .(       ; Non-zero: not 6502 code
; ***************************************************************************************
; Enter raw code
;
; Enter code at the transfer address without a valid ROM header. Loads A=1 and jumps via
; the memory top pointer (which has been set to the transfer address).
;
; Note: J.G. Harston identifies a bug where raw code should be entered with A=0, and the
; carry should indicate whether the entry is from RESET or OSCLI.
; &f8fa referenced 4 times by &f8d5, &f8dc, &f8e3, &f8ea
.enter_raw_code
    lda #1                                                            ; f8fa: a9 01       ..       ; Enter code with A=1
    jmp (memory_top)                                                  ; f8fc: 6c f2 00    l..      ; Jump to code via memory top pointer
; ***************************************************************************************
; Generate 'not a language' error
;
; Set up the BRK vector to point to the default error handler, then generate error 0:
; 'This is not a language'. The error handler must be re-established here because the
; previous language's handler will have been overwritten.
; &f8ff referenced 1 time by &f8f4
.error_not_a_language
    lda #&45 ; 'E'                                                    ; f8ff: a9 45       .E       ; Set BRKV low to error handler
    sta brkv                                                          ; f901: 8d 02 02    ...      ; Store BRKV low byte
    lda #&f9                                                          ; f904: a9 f9       ..       ; Set BRKV high to error handler
    sta brkv_hi                                                       ; f906: 8d 03 02    ...      ; Store BRKV high byte
    brk                                                               ; f909: 00          .        ; Generate 'not a language' error
    equb &00                                                          ; f90a: 00          .     
    equs "This is not a language"                                     ; f90b: 54 68 69... Thi...
    equb &00                                                          ; f921: 00          .     
; ***************************************************************************************
; Generate 'not 6502 code' error
;
; Set up the BRK vector to point to the default error handler, then generate error 0: 'I
; cannot run this code'. Called when the ROM type indicates the code is not suitable for
; a 6502 processor.
; &f922 referenced 1 time by &f8f8
.error_not_6502_code
    lda #&45 ; 'E'                                                    ; f922: a9 45       .E       ; Set BRKV low to error handler
    sta brkv                                                          ; f924: 8d 02 02    ...      ; Store BRKV low byte
    lda #&f9                                                          ; f927: a9 f9       ..       ; Set BRKV high to error handler
    sta brkv_hi                                                       ; f929: 8d 03 02    ...      ; Store BRKV high byte
    brk                                                               ; f92c: 00          .        ; Generate 'I cannot run this code'
    equb &00                                                          ; f92d: 00          .     
    equs "I cannot run this code"                                     ; f92e: 49 20 63... I c...
    equb &00                                                          ; f944: 00          .     
; ***************************************************************************************
; Error handler
;
; Default BRK handler. Clears the stack, prints the error message from the BRK
; instruction, and returns to the command prompt.
.error_handler
    ldx #&ff                                                          ; f945: a2 ff       ..       ; Reset stack pointer to &FF
    txs                                                               ; f947: 9a          .        ; Clear the stack
    jsr osnewl_entry                                                  ; f948: 20 e7 ff     ..      ; Print newline before error message
    ldy #1                                                            ; f94b: a0 01       ..       ; Start at offset 1 (skip error number)
; &f94d referenced 1 time by &f955
.print_error_loop
    lda (last_error),y                                                ; f94d: b1 fd       ..       ; Get next error message character
    beq print_error_done                                              ; f94f: f0 06       ..       ; Zero: end of error message
    jsr oswrch_entry                                                  ; f951: 20 ee ff     ..      ; Print character via OSWRCH
    iny                                                               ; f954: c8          .        ; Next character
    bne print_error_loop                                              ; f955: d0 f6       ..       ; Loop until all characters printed
; &f957 referenced 1 time by &f94f
.print_error_done
    jsr osnewl_entry                                                  ; f957: 20 e7 ff     ..      ; Print trailing newline
    jmp command_prompt                                                ; f95a: 4c 8d f8    L..      ; Return to command prompt
; ***************************************************************************************
; OSWORD 0 control block
;
; Parameter block passed to OSWORD 0 (read line) when reading input at the supervisor
; command prompt. Specifies where to store the input text, the buffer size, and the range
; of acceptable character codes.
.rdline_control_block
    equb &36                                                          ; f95d: 36          6        ; Buffer address low (&0236)
    equb &02                                                          ; f95e: 02          .        ; Buffer address high
    equb &ca                                                          ; f95f: ca          .        ; Buffer length (&CA = 202 bytes)
    equb &20                                                          ; f960: 20                   ; Minimum ASCII value (&20 = space)
    equb &ff                                                          ; f961: ff          .        ; Maximum ASCII value (&FF = all)
; ***************************************************************************************
; OSWRCH implementation
;
; Send character in A to the host via Tube R1.
;
; On Entry:
;     A: character to send
;
; On Exit:
;     A: preserved
; &f962 referenced 2 times by &f966, &ffcb
.oswrch_impl
    bit tube_r1_status                                                ; f962: 2c f8 fe    ,..      ; Check Tube R1 status
    nop                                                               ; f965: ea          .        ; NOP for timing
    bvc oswrch_impl                                                   ; f966: 50 fa       P.       ; Wait until R1 ready to accept data
    sta tube_r1_data                                                  ; f968: 8d f9 fe    ...      ; Send character to Tube R1
    rts                                                               ; f96b: 60          `        ; Return with A preserved
; ***************************************************************************************
; OSRDCH implementation
;
; Read a character from the host via the Tube.
;
; Sends command &00 to the host, then waits for a carry byte and the character.
;
; On Exit:
;     A: character received
;     C: Escape flag
; &f96c referenced 1 time by &ffc8
.osrdch_impl
    lda #0                                                            ; f96c: a9 00       ..       ; Command &00: request character
    jsr send_command                                                  ; f96e: 20 4a fc     J.      ; Send command to host via Tube R2
; ***************************************************************************************
; Wait for carry byte and data byte
;
; Wait for two bytes from Tube R2: first a carry indicator, then the data byte.
;
; The carry byte is shifted left so bit 7 moves into the carry flag, then falls through
; to read the actual data byte.
;
; On Exit:
;     A: data byte from Tube R2
;     C: carry indicator from host
; &f971 referenced 2 times by &fc33, &fcb4
.wait_carry_and_byte
    jsr wait_for_tube_r2_byte                                         ; f971: 20 75 f9     u.      ; Wait for carry byte from host
    asl a                                                             ; f974: 0a          .        ; Shift carry flag into C
; ***************************************************************************************
; Wait for byte from Tube R2
;
; Poll Tube R2 status until data is available, then read and return the byte.
;
; On Exit:
;     A: byte read from Tube R2
; &f975 referenced 18 times by &f886, &f971, &f978, &fa35, &fba3, &fbf2, &fbf6, &fbfb, &fc00, &fc05, &fc1f, &fc27, &fc45, &fc78, &fc7e, &fca8, &fd53, &fd5a
.wait_for_tube_r2_byte
    bit tube_r2_status                                                ; f975: 2c fa fe    ,..      ; Poll Tube R2 status
    bpl wait_for_tube_r2_byte                                         ; f978: 10 fb       ..       ; Loop until data available
    lda tube_r2_data                                                  ; f97a: ad fb fe    ...      ; Read data byte from Tube R2
; ***************************************************************************************
; Null return
;
; An RTS used as a no-op handler for vectors that have no action (EVNTV, IND1V-IND3V in
; the default table).
.null_return
    rts                                                               ; f97d: 60          `        ; Return
; ***************************************************************************************
; Advance and skip spaces in command string
;
; Increment Y then fall through to skip_spaces. Called when the current character has
; been consumed and any following spaces should be skipped.
;
; On Entry:
;     Y: offset of the character just consumed
;
; On Exit:
;     A: first non-space character after skipped spaces
;     Y: offset of that character
; &f97e referenced 2 times by &f983, &fa44
.skip_spaces_step
    iny                                                               ; f97e: c8          .        ; Advance past current character
; ***************************************************************************************
; Skip spaces in command string
;
; Advance past space characters in the string at (string_ptr),Y.
;
; On Entry:
;     Y: current offset into string
;
; On Exit:
;     A: first non-space character
;     Y: offset of that character
; &f97f referenced 2 times by &f9d1, &fa4a
.skip_spaces
    lda (string_ptr),y                                                ; f97f: b1 f8       ..       ; Get character from string
    cmp #&20 ; ' '                                                    ; f981: c9 20       .        ; Is it a space?
    beq skip_spaces_step                                              ; f983: f0 f9       ..       ; Yes: skip and check next
    rts                                                               ; f985: 60          `        ; Return with non-space char in A
; ***************************************************************************************
; Parse hexadecimal number
;
; Read a hexadecimal number from the string at (string_ptr),Y into the hex accumulator at
; &F0/F1.
;
; On Entry:
;     Y: offset into string
;
; On Exit:
;     HEX_ACCUMULATOR: parsed value (low byte)
;     HEX_ACCUMULATOR_HI: parsed value (high byte)
;     X: non-zero if any digits were parsed
;     Y: offset past last hex digit
;     A: first non-hex character
; &f986 referenced 1 time by &fa47
.scan_hex
    ldx #0                                                            ; f986: a2 00       ..       ; X=0: no digits parsed yet
    stx hex_accumulator                                               ; f988: 86 f0       ..       ; Clear hex accumulator low
    stx hex_accumulator_hi                                            ; f98a: 86 f1       ..       ; Clear hex accumulator high
; &f98c referenced 1 time by &f9af
.scan_hex_next_char
    lda (string_ptr),y                                                ; f98c: b1 f8       ..       ; Get current character
    cmp #&30 ; '0'                                                    ; f98e: c9 30       .0       ; Below '0': not a hex digit
    bcc scan_hex_return                                               ; f990: 90 1f       ..       ; Exit if not a digit
    cmp #&3a ; ':'                                                    ; f992: c9 3a       .:       ; Below ':': it is a decimal digit
    bcc scan_hex_got_digit                                            ; f994: 90 0a       ..       ; Process digit 0-9
    and #&df                                                          ; f996: 29 df       ).       ; Force uppercase
    sbc #7                                                            ; f998: e9 07       ..       ; Adjust for hex letter offset
    bcc scan_hex_return                                               ; f99a: 90 15       ..       ; Below 'A': not a hex digit
    cmp #&40 ; '@'                                                    ; f99c: c9 40       .@       ; Above 'F': not a hex digit
    bcs scan_hex_return                                               ; f99e: b0 11       ..       ; Exit if out of range
; &f9a0 referenced 1 time by &f994
.scan_hex_got_digit
    asl a                                                             ; f9a0: 0a          .        ; Shift digit into upper nybble
    asl a                                                             ; f9a1: 0a          .        ; Second shift
    asl a                                                             ; f9a2: 0a          .        ; Third shift
    asl a                                                             ; f9a3: 0a          .        ; Fourth shift (digit now in bits 7-4)
    ldx #3                                                            ; f9a4: a2 03       ..       ; 4 bits to rotate in
; &f9a6 referenced 1 time by &f9ac
.scan_hex_shift_loop
    asl a                                                             ; f9a6: 0a          .        ; Shift bit out of digit
    rol hex_accumulator                                               ; f9a7: 26 f0       &.       ; Rotate into accumulator low
    rol hex_accumulator_hi                                            ; f9a9: 26 f1       &.       ; Rotate into accumulator high
    dex                                                               ; f9ab: ca          .        ; Next bit
    bpl scan_hex_shift_loop                                           ; f9ac: 10 f8       ..       ; Loop for 4 bits
    iny                                                               ; f9ae: c8          .        ; Move to next input character
    bne scan_hex_next_char                                            ; f9af: d0 db       ..       ; Loop for more hex digits
; &f9b1 referenced 3 times by &f990, &f99a, &f99e
.scan_hex_return
    rts                                                               ; f9b1: 60          `        ; Return
; ***************************************************************************************
; Send string to Tube R2
;
; Send a CR-terminated string to the host via Tube R2.
;
; On Entry:
;     X: string address low byte
;     Y: string address high byte
;
; On Exit:
;     Y: restored from string_ptr_hi
; &f9b2 referenced 2 times by &fc24, &fc71
.send_string
    stx string_ptr                                                    ; f9b2: 86 f8       ..       ; Set string pointer low byte
    sty string_ptr_hi                                                 ; f9b4: 84 f9       ..       ; Set string pointer high byte
; &f9b6 referenced 1 time by &fa32
.send_string_via_ptr
    ldy #0                                                            ; f9b6: a0 00       ..       ; Start at offset 0
; &f9b8 referenced 2 times by &f9bb, &f9c5
.send_string_loop
    bit tube_r2_status                                                ; f9b8: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc send_string_loop                                              ; f9bb: 50 fb       P.       ; Wait until R2 ready
    lda (string_ptr),y                                                ; f9bd: b1 f8       ..       ; Get character from string
    sta tube_r2_data                                                  ; f9bf: 8d fb fe    ...      ; Send to Tube R2
    iny                                                               ; f9c2: c8          .        ; Next character
    cmp #&0d                                                          ; f9c3: c9 0d       ..       ; Was it carriage return?
    bne send_string_loop                                              ; f9c5: d0 f1       ..       ; No: send next character
    ldy string_ptr_hi                                                 ; f9c7: a4 f9       ..       ; Restore Y from string_ptr_hi
    rts                                                               ; f9c9: 60          `        ; Return
; ***************************************************************************************
; OSCLI implementation
;
; Execute a * command. Parses the command to check for *GO and *HELP which are handled
; locally; all other commands are forwarded to the host via the Tube.
;
; On Entry:
;     X: command string address low byte
;     Y: command string address high byte
.oscli_impl
    pha                                                               ; f9ca: 48          H        ; Save A on stack
    stx string_ptr                                                    ; f9cb: 86 f8       ..       ; Store command string low byte
    sty string_ptr_hi                                                 ; f9cd: 84 f9       ..       ; Store command string high byte
    ldy #0                                                            ; f9cf: a0 00       ..       ; Start at offset 0
; &f9d1 referenced 1 time by &f9d7
.oscli_skip_stars_loop
    jsr skip_spaces                                                   ; f9d1: 20 7f f9     ..      ; Skip leading spaces
    iny                                                               ; f9d4: c8          .        ; Advance past character
    cmp #&2a ; '*'                                                    ; f9d5: c9 2a       .*       ; Is it a '*'?
    beq oscli_skip_stars_loop                                         ; f9d7: f0 f8       ..       ; Yes: skip leading stars
    and #&df                                                          ; f9d9: 29 df       ).       ; Force uppercase for matching
    tax                                                               ; f9db: aa          .        ; Save first command letter in X
    lda (string_ptr),y                                                ; f9dc: b1 f8       ..       ; Peek at next character
    cpx #&47 ; 'G'                                                    ; f9de: e0 47       .G       ; Is first letter 'G'?
    beq command_go                                                    ; f9e0: f0 5c       .\       ; Yes: check for *GO
    cpx #&48 ; 'H'                                                    ; f9e2: e0 48       .H       ; Is first letter 'H'?
    bne oscli_send_to_host                                            ; f9e4: d0 47       .G       ; No: pass command to host
    cmp #&2e ; '.'                                                    ; f9e6: c9 2e       ..       ; Is next char '.' (abbreviated)?
    beq command_help                                                  ; f9e8: f0 2d       .-       ; H. matches *HELP
    and #&df                                                          ; f9ea: 29 df       ).       ; Force uppercase
    cmp #&45 ; 'E'                                                    ; f9ec: c9 45       .E       ; Is it 'E'?
    bne oscli_send_to_host                                            ; f9ee: d0 3d       .=       ; No: pass to host
    iny                                                               ; f9f0: c8          .        ; Advance past 'E'
    lda (string_ptr),y                                                ; f9f1: b1 f8       ..       ; Get next character
    cmp #&2e ; '.'                                                    ; f9f3: c9 2e       ..       ; Is it '.' (abbreviated)?
    beq command_help                                                  ; f9f5: f0 20       .        ; HE. matches *HELP
    and #&df                                                          ; f9f7: 29 df       ).       ; Force uppercase
    cmp #&4c ; 'L'                                                    ; f9f9: c9 4c       .L       ; Is it 'L'?
    bne oscli_send_to_host                                            ; f9fb: d0 30       .0       ; No: pass to host
    iny                                                               ; f9fd: c8          .        ; Advance past 'L'
    lda (string_ptr),y                                                ; f9fe: b1 f8       ..       ; Get next character
    cmp #&2e ; '.'                                                    ; fa00: c9 2e       ..       ; Is it '.' (abbreviated)?
    beq command_help                                                  ; fa02: f0 13       ..       ; HEL. matches *HELP
    and #&df                                                          ; fa04: 29 df       ).       ; Force uppercase
    cmp #&50 ; 'P'                                                    ; fa06: c9 50       .P       ; Is it 'P'?
    bne oscli_send_to_host                                            ; fa08: d0 23       .#       ; No: pass to host
    iny                                                               ; fa0a: c8          .        ; Advance past 'P'
    lda (string_ptr),y                                                ; fa0b: b1 f8       ..       ; Get next character
    and #&df                                                          ; fa0d: 29 df       ).       ; Force uppercase
    cmp #&41 ; 'A'                                                    ; fa0f: c9 41       .A       ; Below 'A': end of command, it is HELP
    bcc command_help                                                  ; fa11: 90 04       ..       ; Non-letter terminates: do *HELP
    cmp #&5b ; '['                                                    ; fa13: c9 5b       .[       ; Below '[': followed by letter
    bcc oscli_send_to_host                                            ; fa15: 90 16       ..       ; Letter follows: pass to host
; ***************************************************************************************
; Handle *HELP command
;
; Print local help text showing the Tube Client version, then fall through to forward the
; *HELP command to the host.
; &fa17 referenced 4 times by &f9e8, &f9f5, &fa02, &fa11
.command_help
    jsr print_embedded_text                                           ; fa17: 20 98 fe     ..      ; Print inline version string
    equb &0a, &0d, "6502 TUBE 1.10", &0a, &0d                         ; fa1a: 0a 0d 36... ..6...
    nop                                                               ; fa2c: ea          .        ; NOP (&EA) terminates string and is executed
; ***************************************************************************************
; Send OSCLI command to host
;
; Forward the command string at (string_ptr) to the host via Tube R2 with command code
; &02.
;
; Tube protocol: &02 string &0D -- &7F or &80
;
; If the response has bit 7 set, code needs to be entered (a language was selected).
; &fa2d referenced 7 times by &f9e4, &f9ee, &f9fb, &fa08, &fa15, &fa42, &fa4f
.oscli_send_to_host
    lda #2                                                            ; fa2d: a9 02       ..       ; Command &02: OSCLI
    jsr send_command                                                  ; fa2f: 20 4a fc     J.      ; Send command code to host
    jsr send_string_via_ptr                                           ; fa32: 20 b6 f9     ..      ; Send command string via string_ptr
; ***************************************************************************************
; Wait for OSCLI acknowledgement
;
; Wait for the host's response byte after sending an OSCLI command. If the response has
; bit 7 set (&80), the host has selected a language and code needs to be entered at the
; transfer address. Otherwise restore A and return to the caller.
;
; Also used by OSBYTE &8E (select language) via the check at osbyte_check_ack.
; &fa35 referenced 1 time by &fa71
.oscli_wait_ack
    jsr wait_for_tube_r2_byte                                         ; fa35: 20 75 f9     u.      ; Wait for host acknowledgement
    cmp #&80                                                          ; fa38: c9 80       ..       ; &80: host wants code entered
    beq execute_code                                                  ; fa3a: f0 20       .        ; Enter transferred code
    pla                                                               ; fa3c: 68          h        ; Restore saved A
    rts                                                               ; fa3d: 60          `        ; Return to caller
; ***************************************************************************************
; Handle *GO command
;
; Parse *GO [address]. If an address is given, set the transfer address to it. If no
; address given, use the current transfer address. Falls through to execute the code.
;
; Note: does not check for a separator after 'GO', so commands like *GOAD would be
; incorrectly matched. J.G. Harston identifies this as a bug.
; &fa3e referenced 1 time by &f9e0
.command_go
    and #&df                                                          ; fa3e: 29 df       ).       ; Force uppercase
    cmp #&4f ; 'O'                                                    ; fa40: c9 4f       .O       ; Is it 'O' (completing GO)?
    bne oscli_send_to_host                                            ; fa42: d0 e9       ..       ; No: pass to host
    jsr skip_spaces_step                                              ; fa44: 20 7e f9     ~.      ; Skip past 'O' and spaces
    jsr scan_hex                                                      ; fa47: 20 86 f9     ..      ; Parse optional hex address
    jsr skip_spaces                                                   ; fa4a: 20 7f f9     ..      ; Skip trailing spaces
    cmp #&0d                                                          ; fa4d: c9 0d       ..       ; End of line (CR)?
    bne oscli_send_to_host                                            ; fa4f: d0 dc       ..       ; No: extra params, pass to host
    txa                                                               ; fa51: 8a          .        ; X=0 means no address was given
    beq execute_code                                                  ; fa52: f0 08       ..       ; Use current transfer address
    lda hex_accumulator                                               ; fa54: a5 f0       ..       ; Get parsed address low byte
    sta data_transfer_addr                                            ; fa56: 85 f6       ..       ; Set transfer address low
    lda hex_accumulator_hi                                            ; fa58: a5 f1       ..       ; Get parsed address high byte
    sta data_transfer_addr_hi                                         ; fa5a: 85 f7       ..       ; Set transfer address high
; ***************************************************************************************
; Execute code and restore state
;
; Save the current program pointer, call enter_code, then restore the current program and
; memory top on return.
;
; Note: in v1.10, the carry flag is not explicitly set before calling enter_code, so
; entered code cannot reliably distinguish RESET from OSCLI entry. J.G. Harston
; identifies this as a bug.
; &fa5c referenced 2 times by &fa3a, &fa52
.execute_code
    lda current_program_hi                                            ; fa5c: a5 ef       ..       ; Get current program high byte
    pha                                                               ; fa5e: 48          H        ; Save on stack
    lda current_program                                               ; fa5f: a5 ee       ..       ; Get current program low byte
    pha                                                               ; fa61: 48          H        ; Save on stack
    jsr enter_code                                                    ; fa62: 20 b5 f8     ..      ; Enter the code at transfer address
    pla                                                               ; fa65: 68          h        ; Restore current program low
    sta current_program                                               ; fa66: 85 ee       ..       ; Set current program low
    sta memory_top                                                    ; fa68: 85 f2       ..       ; Also restore memory top low
    pla                                                               ; fa6a: 68          h        ; Restore current program high
    sta current_program_hi                                            ; fa6b: 85 ef       ..       ; Set current program high
    sta memory_top_hi                                                 ; fa6d: 85 f3       ..       ; Also restore memory top high
    pla                                                               ; fa6f: 68          h        ; Restore saved A
    rts                                                               ; fa70: 60          `        ; Return to caller
; ***************************************************************************************
; Check OSCLI acknowledgement (OSBYTE &8E path)
;
; Entry point used by OSBYTE &8E (select language). If the function matched &8E, branches
; to wait for the OSCLI acknowledgement byte from the host, which may trigger code entry.
; &fa71 referenced 1 time by &face
.check_oscli_ack
.osbyte_check_ack
    beq oscli_wait_ack                                                ; fa71: f0 c2       ..       ; If &8E matched, wait for OSCLI ack
; ***************************************************************************************
; OSBYTE implementation
;
; Handle OSBYTE calls. Functions &82-&84 are handled locally (memory high word,
; bottom/top of memory). Low functions (A < &80) send command &04 with X and A. High
; functions send command &06 with X, Y, and A.
;
; Special handling for OSBYTE &8E (select language) which checks for code to enter, and
; &9D (fast BPUT) which returns immediately without waiting for a response.
;
; On Entry:
;     A: function
;     X: parameter 1
;     Y: parameter 2
;
; On Exit:
;     A: preserved
;     X: returned value (for A >= &80)
;     Y: returned value (for A >= &80)
;     C: returned value (for A >= &80)
.osbyte_impl
    cmp #&80                                                          ; fa73: c9 80       ..       ; Function >= &80?
    bcs osbyte_high                                                   ; fa75: b0 25       .%       ; Yes: handle high OSBYTE
    pha                                                               ; fa77: 48          H        ; Save function on stack
    lda #4                                                            ; fa78: a9 04       ..       ; Command &04: OSBYTE low
; &fa7a referenced 1 time by &fa7d
.osbyte_low_wait_r2_1
    bit tube_r2_status                                                ; fa7a: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osbyte_low_wait_r2_1                                          ; fa7d: 50 fb       P.       ; Wait until R2 ready
    sta tube_r2_data                                                  ; fa7f: 8d fb fe    ...      ; Send command &04
; &fa82 referenced 1 time by &fa85
.osbyte_low_wait_r2_2
    bit tube_r2_status                                                ; fa82: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osbyte_low_wait_r2_2                                          ; fa85: 50 fb       P.       ; Wait until R2 ready
    stx tube_r2_data                                                  ; fa87: 8e fb fe    ...      ; Send X parameter
    pla                                                               ; fa8a: 68          h        ; Restore function code
; &fa8b referenced 1 time by &fa8e
.osbyte_low_wait_r2_3
    bit tube_r2_status                                                ; fa8b: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osbyte_low_wait_r2_3                                          ; fa8e: 50 fb       P.       ; Wait until R2 ready
    sta tube_r2_data                                                  ; fa90: 8d fb fe    ...      ; Send function code
; &fa93 referenced 1 time by &fa96
.osbyte_low_wait_result
    bit tube_r2_status                                                ; fa93: 2c fa fe    ,..      ; Poll Tube R2 for response
    bpl osbyte_low_wait_result                                        ; fa96: 10 fb       ..       ; Wait until data available
    ldx tube_r2_data                                                  ; fa98: ae fb fe    ...      ; Read return value into X
    rts                                                               ; fa9b: 60          `        ; Return
; &fa9c referenced 1 time by &fa75
.osbyte_high
    cmp #&82                                                          ; fa9c: c9 82       ..       ; Is it OSBYTE &82 (read high word)?
    beq osbyte_read_high_word                                         ; fa9e: f0 5a       .Z       ; Yes: return &0000
    cmp #&83                                                          ; faa0: c9 83       ..       ; Is it OSBYTE &83 (read LOMEM)?
    beq osbyte_read_lomem                                             ; faa2: f0 51       .Q       ; Yes: return &0800
    cmp #&84                                                          ; faa4: c9 84       ..       ; Is it OSBYTE &84 (read HIMEM)?
    beq osbyte_read_himem                                             ; faa6: f0 48       .H       ; Yes: return memory_top
    pha                                                               ; faa8: 48          H        ; Save function on stack
    lda #6                                                            ; faa9: a9 06       ..       ; Command &06: OSBYTE high
; &faab referenced 1 time by &faae
.osbyte_high_wait_r2_1
    bit tube_r2_status                                                ; faab: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osbyte_high_wait_r2_1                                         ; faae: 50 fb       P.       ; Wait until R2 ready
    sta tube_r2_data                                                  ; fab0: 8d fb fe    ...      ; Send command &06
; &fab3 referenced 1 time by &fab6
.osbyte_high_wait_r2_2
    bit tube_r2_status                                                ; fab3: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osbyte_high_wait_r2_2                                         ; fab6: 50 fb       P.       ; Wait until R2 ready
    stx tube_r2_data                                                  ; fab8: 8e fb fe    ...      ; Send X parameter
; &fabb referenced 1 time by &fabe
.osbyte_high_wait_r2_3
    bit tube_r2_status                                                ; fabb: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osbyte_high_wait_r2_3                                         ; fabe: 50 fb       P.       ; Wait until R2 ready
    sty tube_r2_data                                                  ; fac0: 8c fb fe    ...      ; Send Y parameter
    pla                                                               ; fac3: 68          h        ; Restore function code
; &fac4 referenced 1 time by &fac7
.osbyte_high_wait_r2_4
    bit tube_r2_status                                                ; fac4: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osbyte_high_wait_r2_4                                         ; fac7: 50 fb       P.       ; Wait until R2 ready
    sta tube_r2_data                                                  ; fac9: 8d fb fe    ...      ; Send function code
    cmp #&8e                                                          ; facc: c9 8e       ..       ; Is it &8E (select language)?
    beq check_oscli_ack                                               ; face: f0 a1       ..       ; Yes: check for code to enter
    cmp #&9d                                                          ; fad0: c9 9d       ..       ; Is it &9D (fast BPUT)?
    beq osbyte_high_return                                            ; fad2: f0 1b       ..       ; Yes: return without response
    pha                                                               ; fad4: 48          H        ; Save function for later restore
; &fad5 referenced 1 time by &fad8
.osbyte_high_wait_carry
    bit tube_r2_status                                                ; fad5: 2c fa fe    ,..      ; Poll Tube R2 for carry byte
    bpl osbyte_high_wait_carry                                        ; fad8: 10 fb       ..       ; Wait until data available
    lda tube_r2_data                                                  ; fada: ad fb fe    ...      ; Read carry byte
    asl a                                                             ; fadd: 0a          .        ; Shift carry into C flag
    pla                                                               ; fade: 68          h        ; Restore saved function
; &fadf referenced 1 time by &fae2
.osbyte_high_wait_y
    bit tube_r2_status                                                ; fadf: 2c fa fe    ,..      ; Poll Tube R2 for Y return value
    bpl osbyte_high_wait_y                                            ; fae2: 10 fb       ..       ; Wait until data available
    ldy tube_r2_data                                                  ; fae4: ac fb fe    ...      ; Read Y return value
; &fae7 referenced 1 time by &faea
.osbyte_high_wait_x
    bit tube_r2_status                                                ; fae7: 2c fa fe    ,..      ; Poll Tube R2 for X return value
    bpl osbyte_high_wait_x                                            ; faea: 10 fb       ..       ; Wait until data available
    ldx tube_r2_data                                                  ; faec: ae fb fe    ...      ; Read X return value
; &faef referenced 1 time by &fad2
.osbyte_high_return
    rts                                                               ; faef: 60          `        ; Return
; ***************************************************************************************
; OSBYTE &84: read top of memory
;
; Return the current top of user memory from &F2/F3. Falls through to the RTS at
; osbyte_himem_rts.
;
; On Exit:
;     X: memory_top low byte
;     Y: memory_top high byte
; &faf0 referenced 1 time by &faa6
.osbyte_read_himem
    ldx memory_top                                                    ; faf0: a6 f2       ..       ; X = memory top low byte
    ldy memory_top_hi                                                 ; faf2: a4 f3       ..       ; Y = memory top high byte
.osbyte_himem_rts
    rts                                                               ; faf4: 60          `        ; Return (OSBYTE &84)
; ***************************************************************************************
; OSBYTE &83: read bottom of memory
;
; Return the bottom of user memory, fixed at &0800. Shares its RTS with
; osbyte_read_high_word.
;
; On Exit:
;     X: &00
;     Y: &08
; &faf5 referenced 1 time by &faa2
.osbyte_read_lomem
    ldx #0                                                            ; faf5: a2 00       ..       ; X = &00 (bottom of user memory)
    ldy #8                                                            ; faf7: a0 08       ..       ; Y = &08 (bottom of memory high byte)
.osbyte_lomem_rts
    rts                                                               ; faf9: 60          `        ; Return (OSBYTE &83)
; ***************************************************************************************
; OSBYTE &82: read machine high order address
;
; Return &0000 as the high word of the address space. This indicates the 6502 has a
; 16-bit address space with no bank switching.
;
; On Exit:
;     X: &00
;     Y: &00
; &fafa referenced 1 time by &fa9e
.osbyte_read_high_word
    ldx #0                                                            ; fafa: a2 00       ..       ; X = &00 (high word low)
    ldy #0                                                            ; fafc: a0 00       ..       ; Y = &00 (high word high)
    rts                                                               ; fafe: 60          `        ; Return (OSBYTE &82)
; ***************************************************************************************
; OSWORD implementation
;
; Handle OSWORD calls. OSWORD 0 (read line) is handled specially via rdline. All other
; functions send the control block to the host and receive the response, with block sizes
; determined by lookup tables.
;
; On Entry:
;     A: function
;     XY: control block address
.osword_impl
    stx string_ptr                                                    ; faff: 86 f8       ..       ; Store control block address low
    sty string_ptr_hi                                                 ; fb01: 84 f9       ..       ; Store control block address high
    tay                                                               ; fb03: a8          .        ; A=0: OSWORD 0?
    beq rdline                                                        ; fb04: f0 71       .q       ; Yes: handle read line specially
    pha                                                               ; fb06: 48          H        ; Save function on stack
    ldy #8                                                            ; fb07: a0 08       ..       ; Command &08: OSWORD
; &fb09 referenced 1 time by &fb0c
.osword_wait_r2_cmd
    bit tube_r2_status                                                ; fb09: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osword_wait_r2_cmd                                            ; fb0c: 50 fb       P.       ; Wait until R2 ready
    sty tube_r2_data                                                  ; fb0e: 8c fb fe    ...      ; Send command &08
; &fb11 referenced 1 time by &fb14
.osword_wait_r2_func
    bit tube_r2_status                                                ; fb11: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osword_wait_r2_func                                           ; fb14: 50 fb       P.       ; Wait until R2 ready
    sta tube_r2_data                                                  ; fb16: 8d fb fe    ...      ; Send function number
    tax                                                               ; fb19: aa          .        ; Copy function to X
    bpl osword_send_low_lookup                                        ; fb1a: 10 08       ..       ; Function >= &80?
    ldy #0                                                            ; fb1c: a0 00       ..       ; Y=0 for control block read
    lda (string_ptr),y                                                ; fb1e: b1 f8       ..       ; Get send length from control block
    tay                                                               ; fb20: a8          .        ; Transfer to Y
    jmp osword_send_block                                             ; fb21: 4c 2d fb    L-.      ; Jump to send block
; &fb24 referenced 1 time by &fb1a
.osword_send_low_lookup
    ldy osword_send_lengths,x                                         ; fb24: bc bc fc    ...      ; Get send length from table
    cpx #&15                                                          ; fb27: e0 15       ..       ; Function < &15?
    bcc osword_send_block                                             ; fb29: 90 02       ..       ; Yes: use table length
    ldy #&10                                                          ; fb2b: a0 10       ..       ; Default: send 16 bytes
; &fb2d referenced 3 times by &fb21, &fb29, &fb30
.osword_send_block
    bit tube_r2_status                                                ; fb2d: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osword_send_block                                             ; fb30: 50 fb       P.       ; Wait until R2 ready
    sty tube_r2_data                                                  ; fb32: 8c fb fe    ...      ; Send block length to host
    dey                                                               ; fb35: 88          .        ; Decrement index
    bmi osword_recv_get_length                                        ; fb36: 30 0d       0.       ; Negative: nothing to send
; &fb38 referenced 2 times by &fb3b, &fb43
.osword_send_bytes_loop
    bit tube_r2_status                                                ; fb38: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osword_send_bytes_loop                                        ; fb3b: 50 fb       P.       ; Wait until R2 ready
    lda (string_ptr),y                                                ; fb3d: b1 f8       ..       ; Read byte from control block
    sta tube_r2_data                                                  ; fb3f: 8d fb fe    ...      ; Send to Tube R2
    dey                                                               ; fb42: 88          .        ; Next byte (reverse order)
    bpl osword_send_bytes_loop                                        ; fb43: 10 f3       ..       ; Loop until all bytes sent
; &fb45 referenced 1 time by &fb36
.osword_recv_get_length
    txa                                                               ; fb45: 8a          .        ; Get function back in A
    bpl osword_recv_low_lookup                                        ; fb46: 10 08       ..       ; Function >= &80?
    ldy #1                                                            ; fb48: a0 01       ..       ; Y=1 for control block read
    lda (string_ptr),y                                                ; fb4a: b1 f8       ..       ; Get receive length from block
    tay                                                               ; fb4c: a8          .        ; Transfer to Y
    jmp osword_recv_block                                             ; fb4d: 4c 59 fb    LY.      ; Jump to receive block
; &fb50 referenced 1 time by &fb46
.osword_recv_low_lookup
    ldy osword_recv_lengths,x                                         ; fb50: bc d0 fc    ...      ; Get receive length from table
    cpx #&15                                                          ; fb53: e0 15       ..       ; Function < &15?
    bcc osword_recv_block                                             ; fb55: 90 02       ..       ; Yes: use table length
    ldy #&10                                                          ; fb57: a0 10       ..       ; Default: receive 16 bytes
; &fb59 referenced 3 times by &fb4d, &fb55, &fb5c
.osword_recv_block
    bit tube_r2_status                                                ; fb59: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osword_recv_block                                             ; fb5c: 50 fb       P.       ; Wait until R2 ready
    sty tube_r2_data                                                  ; fb5e: 8c fb fe    ...      ; Send receive length to host
    dey                                                               ; fb61: 88          .        ; Decrement index
    bmi osword_restore_regs                                           ; fb62: 30 0d       0.       ; Negative: nothing to receive
; &fb64 referenced 2 times by &fb67, &fb6f
.osword_recv_bytes_loop
    bit tube_r2_status                                                ; fb64: 2c fa fe    ,..      ; Poll Tube R2 for data
    bpl osword_recv_bytes_loop                                        ; fb67: 10 fb       ..       ; Wait until data available
    lda tube_r2_data                                                  ; fb69: ad fb fe    ...      ; Read response byte
    sta (string_ptr),y                                                ; fb6c: 91 f8       ..       ; Store in control block
    dey                                                               ; fb6e: 88          .        ; Next byte (reverse order)
    bpl osword_recv_bytes_loop                                        ; fb6f: 10 f3       ..       ; Loop until all received
; &fb71 referenced 1 time by &fb62
.osword_restore_regs
    ldy string_ptr_hi                                                 ; fb71: a4 f9       ..       ; Restore Y from string_ptr_hi
    ldx string_ptr                                                    ; fb73: a6 f8       ..       ; Restore X from string_ptr
    pla                                                               ; fb75: 68          h        ; Restore function code
    rts                                                               ; fb76: 60          `        ; Return
; ***************************************************************************************
; Read line of input (OSWORD 0)
;
; Read a line of text from the host.
;
; Sends command &0A with the control block parameters, then receives the input string
; character by character.
;
; Tube protocol: &0A block -- &FF or &7F string &0D
;
; On Exit:
;     Y: length of string (excluding CR)
;     C: 0 if OK, 1 if Escape
; &fb77 referenced 1 time by &fb04
.rdline
    lda #&0a                                                          ; fb77: a9 0a       ..       ; Command &0A: read line
    jsr send_command                                                  ; fb79: 20 4a fc     J.      ; Send command to host
    ldy #4                                                            ; fb7c: a0 04       ..       ; Start at control block byte 4
; &fb7e referenced 2 times by &fb81, &fb8b
.rdline_send_block_loop
    bit tube_r2_status                                                ; fb7e: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc rdline_send_block_loop                                        ; fb81: 50 fb       P.       ; Wait until R2 ready
    lda (string_ptr),y                                                ; fb83: b1 f8       ..       ; Get control block byte
    sta tube_r2_data                                                  ; fb85: 8d fb fe    ...      ; Send to host
    dey                                                               ; fb88: 88          .        ; Decrement index
    cpy #1                                                            ; fb89: c0 01       ..       ; Reached byte 1?
    bne rdline_send_block_loop                                        ; fb8b: d0 f1       ..       ; No: send next (bytes 4, 3, 2)
    lda #7                                                            ; fb8d: a9 07       ..       ; &07 as high byte of buffer address
    jsr send_command                                                  ; fb8f: 20 4a fc     J.      ; Send buffer address high byte
    lda (string_ptr),y                                                ; fb92: b1 f8       ..       ; Get actual buffer high byte
    pha                                                               ; fb94: 48          H        ; Save on stack for later
    dey                                                               ; fb95: 88          .        ; Decrement to byte 0
; &fb96 referenced 1 time by &fb99
.rdline_send_addr_low
    bit tube_r2_status                                                ; fb96: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc rdline_send_addr_low                                          ; fb99: 50 fb       P.       ; Wait until R2 ready
    sty tube_r2_data                                                  ; fb9b: 8c fb fe    ...      ; Send &00 as buffer address low byte
    lda (string_ptr),y                                                ; fb9e: b1 f8       ..       ; Get actual buffer low byte
    pha                                                               ; fba0: 48          H        ; Save on stack for later
    ldx #&ff                                                          ; fba1: a2 ff       ..       ; X=&FF as Escape indicator
    jsr wait_for_tube_r2_byte                                         ; fba3: 20 75 f9     u.      ; Wait for host response
    cmp #&80                                                          ; fba6: c9 80       ..       ; Is response >= &80 (Escape)?
    bcs rdline_escape                                                 ; fba8: b0 1d       ..       ; Yes: handle Escape
    pla                                                               ; fbaa: 68          h        ; Recover buffer low byte
    sta string_ptr                                                    ; fbab: 85 f8       ..       ; Set string_ptr low
    pla                                                               ; fbad: 68          h        ; Recover buffer high byte
    sta string_ptr_hi                                                 ; fbae: 85 f9       ..       ; Set string_ptr high
    ldy #0                                                            ; fbb0: a0 00       ..       ; Start at offset 0
; &fbb2 referenced 2 times by &fbb5, &fbbf
.rdline_recv_loop
    bit tube_r2_status                                                ; fbb2: 2c fa fe    ,..      ; Poll Tube R2 for data
    bpl rdline_recv_loop                                              ; fbb5: 10 fb       ..       ; Wait until data available
    lda tube_r2_data                                                  ; fbb7: ad fb fe    ...      ; Read character from host
    sta (string_ptr),y                                                ; fbba: 91 f8       ..       ; Store in buffer
    iny                                                               ; fbbc: c8          .        ; Advance buffer position
    cmp #&0d                                                          ; fbbd: c9 0d       ..       ; Is it carriage return?
    bne rdline_recv_loop                                              ; fbbf: d0 f1       ..       ; No: receive next character
    lda #0                                                            ; fbc1: a9 00       ..       ; A=0 on success
    dey                                                               ; fbc3: 88          .        ; Y=length (exclude CR)
    clc                                                               ; fbc4: 18          .        ; Clear carry: no Escape
    inx                                                               ; fbc5: e8          .        ; X=0 on success
    rts                                                               ; fbc6: 60          `        ; Return: A=0, Y=len, C=0
; &fbc7 referenced 1 time by &fba8
.rdline_escape
    pla                                                               ; fbc7: 68          h        ; Discard saved buffer low byte
    pla                                                               ; fbc8: 68          h        ; Discard saved buffer high byte
    lda #0                                                            ; fbc9: a9 00       ..       ; A=0, carry set from CMP &80
    rts                                                               ; fbcb: 60          `        ; Return: Escape, A=0, C=1
; ***************************************************************************************
; OSARGS implementation
;
; Read or write information about an open file.
;
; Sends command &0C with handle, 4-byte data word, and function code. Receives result and
; updated data.
;
; On Entry:
;     A: function
;     X: zero-page data word address
;     Y: handle
;
; On Exit:
;     A: result
;     DATA WORD AT X: updated
.osargs_impl
    pha                                                               ; fbcc: 48          H        ; Save function on stack
    lda #&0c                                                          ; fbcd: a9 0c       ..       ; Command &0C: OSARGS
    jsr send_command                                                  ; fbcf: 20 4a fc     J.      ; Send command to host
; &fbd2 referenced 1 time by &fbd5
.osargs_wait_r2_handle
    bit tube_r2_status                                                ; fbd2: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc osargs_wait_r2_handle                                         ; fbd5: 50 fb       P.       ; Wait until R2 ready
    sty tube_r2_data                                                  ; fbd7: 8c fb fe    ...      ; Send file handle
    lda zp_data_base_3,x                                              ; fbda: b5 03       ..       ; Get data word byte 3
    jsr send_command                                                  ; fbdc: 20 4a fc     J.      ; Send data byte 3
    lda zp_data_base_2,x                                              ; fbdf: b5 02       ..       ; Get data word byte 2
    jsr send_command                                                  ; fbe1: 20 4a fc     J.      ; Send data byte 2
    lda zp_data_base_1,x                                              ; fbe4: b5 01       ..       ; Get data word byte 1
    jsr send_command                                                  ; fbe6: 20 4a fc     J.      ; Send data byte 1
    lda zp_data_base,x                                                ; fbe9: b5 00       ..       ; Get data word byte 0
    jsr send_command                                                  ; fbeb: 20 4a fc     J.      ; Send data byte 0
    pla                                                               ; fbee: 68          h        ; Restore function code
    jsr send_command                                                  ; fbef: 20 4a fc     J.      ; Send function code
    jsr wait_for_tube_r2_byte                                         ; fbf2: 20 75 f9     u.      ; Wait for result byte
    pha                                                               ; fbf5: 48          H        ; Save result on stack
    jsr wait_for_tube_r2_byte                                         ; fbf6: 20 75 f9     u.      ; Wait for data byte 3
    sta zp_data_base_3,x                                              ; fbf9: 95 03       ..       ; Store in data word
    jsr wait_for_tube_r2_byte                                         ; fbfb: 20 75 f9     u.      ; Wait for data byte 2
    sta zp_data_base_2,x                                              ; fbfe: 95 02       ..       ; Store in data word
    jsr wait_for_tube_r2_byte                                         ; fc00: 20 75 f9     u.      ; Wait for data byte 1
    sta zp_data_base_1,x                                              ; fc03: 95 01       ..       ; Store in data word
    jsr wait_for_tube_r2_byte                                         ; fc05: 20 75 f9     u.      ; Wait for data byte 0
    sta zp_data_base,x                                                ; fc08: 95 00       ..       ; Store in data word
    pla                                                               ; fc0a: 68          h        ; Restore result to A
    rts                                                               ; fc0b: 60          `        ; Return with result in A
; ***************************************************************************************
; OSFIND implementation
;
; Open or close a file.
;
; For close (A=0): sends command &12, function, handle. For open (A<>0): sends command
; &12, function, filename.
;
; On Entry:
;     A: function
;     XY: filename address (open) or Y = handle (close)
;
; On Exit:
;     A: handle (open) or preserved (close)
.osfind_impl
    pha                                                               ; fc0c: 48          H        ; Save function on stack
    lda #&12                                                          ; fc0d: a9 12       ..       ; Command &12: OSFIND
    jsr send_command                                                  ; fc0f: 20 4a fc     J.      ; Send command to host
    pla                                                               ; fc12: 68          h        ; Restore function code
    jsr send_command                                                  ; fc13: 20 4a fc     J.      ; Send function code
    cmp #0                                                            ; fc16: c9 00       ..       ; Is it close (A=0)?
    bne osfind_open                                                   ; fc18: d0 0a       ..       ; No: handle open
    pha                                                               ; fc1a: 48          H        ; Save A=0
    tya                                                               ; fc1b: 98          .        ; Transfer handle from Y to A
    jsr send_command                                                  ; fc1c: 20 4a fc     J.      ; Send handle
    jsr wait_for_tube_r2_byte                                         ; fc1f: 20 75 f9     u.      ; Wait for acknowledge
    pla                                                               ; fc22: 68          h        ; Restore A=0
    rts                                                               ; fc23: 60          `        ; Return
; &fc24 referenced 1 time by &fc18
.osfind_open
    jsr send_string                                                   ; fc24: 20 b2 f9     ..      ; Send filename string
    jmp wait_for_tube_r2_byte                                         ; fc27: 4c 75 f9    Lu.      ; Wait for and return file handle
; ***************************************************************************************
; OSBGET implementation
;
; Read a byte from an open file.
;
; Sends command &0E with handle, waits for carry and byte.
;
; On Entry:
;     Y: handle
;
; On Exit:
;     A: byte read
;     C: set if EOF
.osbget_impl
    lda #&0e                                                          ; fc2a: a9 0e       ..       ; Command &0E: OSBGET
    jsr send_command                                                  ; fc2c: 20 4a fc     J.      ; Send command to host
    tya                                                               ; fc2f: 98          .        ; Transfer handle from Y to A
    jsr send_command                                                  ; fc30: 20 4a fc     J.      ; Send handle
    jmp wait_carry_and_byte                                           ; fc33: 4c 71 f9    Lq.      ; Wait for carry and data byte
; ***************************************************************************************
; OSBPUT implementation
;
; Write a byte to an open file.
;
; Sends command &10 with handle and byte.
;
; On Entry:
;     A: byte
;     Y: handle
;
; On Exit:
;     A: preserved
.osbput_impl
    pha                                                               ; fc36: 48          H        ; Save byte to write
    lda #&10                                                          ; fc37: a9 10       ..       ; Command &10: OSBPUT
    jsr send_command                                                  ; fc39: 20 4a fc     J.      ; Send command to host
    tya                                                               ; fc3c: 98          .        ; Transfer handle from Y to A
    jsr send_command                                                  ; fc3d: 20 4a fc     J.      ; Send handle
    pla                                                               ; fc40: 68          h        ; Restore byte to write
    jsr send_command                                                  ; fc41: 20 4a fc     J.      ; Send data byte
    pha                                                               ; fc44: 48          H        ; Save A for restore after ack
    jsr wait_for_tube_r2_byte                                         ; fc45: 20 75 f9     u.      ; Wait for acknowledge
    pla                                                               ; fc48: 68          h        ; Restore A (preserved)
    rts                                                               ; fc49: 60          `        ; Return
; ***************************************************************************************
; Send byte to Tube R2
;
; Wait for Tube R2 to be free, then send byte.
;
; On Entry:
;     A: byte to send
;
; On Exit:
;     A: preserved
; &fc4a referenced 25 times by &f96e, &fa2f, &fb79, &fb8f, &fbcf, &fbdc, &fbe1, &fbe6, &fbeb, &fbef, &fc0f, &fc13, &fc1c, &fc2c, &fc30, &fc39, &fc3d, &fc41, &fc4d, &fc5a, &fc61, &fc75, &fc95, &fc9c, &fca3
.send_command
.send_byte_to_tube_r2
    bit tube_r2_status                                                ; fc4a: 2c fa fe    ,..      ; Poll Tube R2 status
    bvc send_command                                                  ; fc4d: 50 fb       P.       ; Wait until R2 ready
    sta tube_r2_data                                                  ; fc4f: 8d fb fe    ...      ; Write byte to Tube R2 data
    rts                                                               ; fc52: 60          `        ; Return with A preserved
; ***************************************************************************************
; OSFILE implementation
;
; Operate on whole files (load, save, read/write attributes).
;
; Sends command &14 with 16-byte control block, filename, and function code. Receives
; result and updated control block.
;
; On Entry:
;     A: function
;     XY: control block address
.osfile_impl
    sty control_block_ptr_hi                                          ; fc53: 84 fb       ..       ; Store control block high byte
    stx control_block_ptr                                             ; fc55: 86 fa       ..       ; Store control block low byte
    pha                                                               ; fc57: 48          H        ; Save function on stack
    lda #&14                                                          ; fc58: a9 14       ..       ; Command &14: OSFILE
    jsr send_command                                                  ; fc5a: 20 4a fc     J.      ; Send command to host
    ldy #&11                                                          ; fc5d: a0 11       ..       ; Start at control block byte &11
; &fc5f referenced 1 time by &fc67
.osfile_send_block_loop
    lda (control_block_ptr),y                                         ; fc5f: b1 fa       ..       ; Get control block byte
    jsr send_command                                                  ; fc61: 20 4a fc     J.      ; Send to host
    dey                                                               ; fc64: 88          .        ; Decrement index
    cpy #1                                                            ; fc65: c0 01       ..       ; Reached byte 1?
    bne osfile_send_block_loop                                        ; fc67: d0 f6       ..       ; No: send next byte
    dey                                                               ; fc69: 88          .        ; Decrement to byte 0
    lda (control_block_ptr),y                                         ; fc6a: b1 fa       ..       ; Get filename pointer low
    tax                                                               ; fc6c: aa          .        ; Transfer to X
    iny                                                               ; fc6d: c8          .        ; Move to byte 1
    lda (control_block_ptr),y                                         ; fc6e: b1 fa       ..       ; Get filename pointer high
    tay                                                               ; fc70: a8          .        ; Transfer to Y
    jsr send_string                                                   ; fc71: 20 b2 f9     ..      ; Send filename string
    pla                                                               ; fc74: 68          h        ; Restore function code
    jsr send_command                                                  ; fc75: 20 4a fc     J.      ; Send function code
    jsr wait_for_tube_r2_byte                                         ; fc78: 20 75 f9     u.      ; Wait for result byte
    pha                                                               ; fc7b: 48          H        ; Save result on stack
    ldy #&11                                                          ; fc7c: a0 11       ..       ; Start at control block byte &11
; &fc7e referenced 1 time by &fc86
.osfile_recv_block_loop
    jsr wait_for_tube_r2_byte                                         ; fc7e: 20 75 f9     u.      ; Wait for response byte
    sta (control_block_ptr),y                                         ; fc81: 91 fa       ..       ; Store in control block
    dey                                                               ; fc83: 88          .        ; Decrement index
    cpy #1                                                            ; fc84: c0 01       ..       ; Reached byte 1?
    bne osfile_recv_block_loop                                        ; fc86: d0 f6       ..       ; No: receive next byte
    ldy control_block_ptr_hi                                          ; fc88: a4 fb       ..       ; Restore Y from control block ptr
    ldx control_block_ptr                                             ; fc8a: a6 fa       ..       ; Restore X from control block ptr
    pla                                                               ; fc8c: 68          h        ; Restore result to A
    rts                                                               ; fc8d: 60          `        ; Return with result in A
; ***************************************************************************************
; OSGBPB implementation
;
; Multiple byte read and write.
;
; Sends command &16 with 13-byte control block and function. Receives updated control
; block, carry, and result.
;
; On Entry:
;     A: function
;     XY: control block address
.osgbpb_impl
    sty control_block_ptr_hi                                          ; fc8e: 84 fb       ..       ; Store control block high byte
    stx control_block_ptr                                             ; fc90: 86 fa       ..       ; Store control block low byte
    pha                                                               ; fc92: 48          H        ; Save function on stack
    lda #&16                                                          ; fc93: a9 16       ..       ; Command &16: OSGBPB
    jsr send_command                                                  ; fc95: 20 4a fc     J.      ; Send command to host
    ldy #&0c                                                          ; fc98: a0 0c       ..       ; Start at control block byte &0C
; &fc9a referenced 1 time by &fca0
.osgbpb_send_block_loop
    lda (control_block_ptr),y                                         ; fc9a: b1 fa       ..       ; Get control block byte
    jsr send_command                                                  ; fc9c: 20 4a fc     J.      ; Send to host
    dey                                                               ; fc9f: 88          .        ; Decrement index
    bpl osgbpb_send_block_loop                                        ; fca0: 10 f8       ..       ; Loop for bytes &0C..&00
    pla                                                               ; fca2: 68          h        ; Restore function code
    jsr send_command                                                  ; fca3: 20 4a fc     J.      ; Send function code
    ldy #&0c                                                          ; fca6: a0 0c       ..       ; Start at control block byte &0C
; &fca8 referenced 1 time by &fcae
.osgbpb_recv_block_loop
    jsr wait_for_tube_r2_byte                                         ; fca8: 20 75 f9     u.      ; Wait for response byte
    sta (control_block_ptr),y                                         ; fcab: 91 fa       ..       ; Store in control block
    dey                                                               ; fcad: 88          .        ; Decrement index
    bpl osgbpb_recv_block_loop                                        ; fcae: 10 f8       ..       ; Loop for bytes &0C..&00
    ldy control_block_ptr_hi                                          ; fcb0: a4 fb       ..       ; Restore Y from control block ptr
    ldx control_block_ptr                                             ; fcb2: a6 fa       ..       ; Restore X from control block ptr
    jmp wait_carry_and_byte                                           ; fcb4: 4c 71 f9    Lq.      ; Get carry and result byte
; ***************************************************************************************
; Unsupported MOS call
;
; Generate a 'Bad' error for unsupported MOS calls. Used as the default handler for
; USERV, IRQ2V, FSCV, and several other vectors that have no parasite-side
; implementation.
; &fcb7 referenced 5 times by &ffb9, &ffbc, &ffbf, &ffc2, &ffc5
.unsupported
    brk                                                               ; fcb7: 00          .        ; Generate error 255: 'Bad'
    equb &ff                                                          ; fcb8: ff          .     
    equs "Bad"                                                        ; fcb9: 42 61 64    Bad   
; ***************************************************************************************
; OSWORD send block length table
;
; Indexed by OSWORD number via LDY table,X where X is the OSWORD function. Entry 0 is
; never used because OSWORD 0 (RDLINE) is handled separately. Entries 1-20 give the
; number of bytes to send from the control block to the host for each OSWORD function.
; Functions above &14 (20) default to sending 16 bytes.
;
; For functions >= &80, the send length is taken from byte 0 of the control block instead
; of this table.
; &fcbc used as index base 1 time by &fb24
.osword_send_lengths
    equb &00                                                          ; fcbc: 00          .        ; (unused: OSWORD 0 handled separately)
    equb &00                                                          ; fcbd: 00          .        ; &01 Read system clock
    equb &05                                                          ; fcbe: 05          .        ; &02 Write system clock
    equb &00                                                          ; fcbf: 00          .        ; &03 Read interval timer
    equb &05                                                          ; fcc0: 05          .        ; &04 Write interval timer
    equb &02                                                          ; fcc1: 02          .        ; &05 Read I/O memory (2-byte addr)
    equb &05                                                          ; fcc2: 05          .        ; &06 Read real-time clock
    equb &08                                                          ; fcc3: 08          .        ; &07 Write real-time clock / sound
    equb &0e                                                          ; fcc4: 0e          .        ; &08 Define envelope
    equb &04                                                          ; fcc5: 04          .        ; &09 Read pixel colour
    equb &01                                                          ; fcc6: 01          .        ; &0A Read character definition
    equb &01                                                          ; fcc7: 01          .        ; &0B Read palette
    equb &05                                                          ; fcc8: 05          .        ; &0C Write palette
    equb &00                                                          ; fcc9: 00          .        ; &0D Read last two graphics cursor posns
    equb &01                                                          ; fcca: 01          .        ; &0E Read clock as string
    equb &20                                                          ; fccb: 20                   ; &0F Write clock as string
    equb &10                                                          ; fccc: 10          .        ; &10 Net transmit
    equb &0d                                                          ; fccd: 0d          .        ; &11 Net receive
    equb &00                                                          ; fcce: 00          .        ; &12 Net read arguments
    equb &04                                                          ; fccf: 04          .        ; &13 Net FS operation
; ***************************************************************************************
; OSWORD receive block length table
;
; Indexed by OSWORD number via LDY table,X. Gives the number of bytes to receive back
; from the host into the control block. Entries 1-20 correspond to OSWORD functions
; &01-&14. Functions above &14 default to receiving 16 bytes.
;
; The first byte (&80) is shared: it serves as both the OSWORD &14 send length (meaning
; the length is in the control block) and the unused recv slot 0.
;
; For functions >= &80, the receive length is taken from byte 1 of the control block
; instead of this table.
; &fcd0 used as index base 1 time by &fb50
.osword_recv_lengths
    equb &80                                                          ; fcd0: 80          .        ; &14 send / (recv slot 0 unused)
    equb &05                                                          ; fcd1: 05          .        ; &01 Read system clock
    equb &00                                                          ; fcd2: 00          .        ; &02 Write system clock
    equb &05                                                          ; fcd3: 05          .        ; &03 Read interval timer
    equb &00                                                          ; fcd4: 00          .        ; &04 Write interval timer
    equb &05                                                          ; fcd5: 05          .        ; &05 Read I/O memory
    equb &00                                                          ; fcd6: 00          .        ; &06 Read real-time clock
    equb &00                                                          ; fcd7: 00          .        ; &07 Write real-time clock / sound
    equb &00                                                          ; fcd8: 00          .        ; &08 Define envelope
    equb &05                                                          ; fcd9: 05          .        ; &09 Read pixel colour
    equb &09                                                          ; fcda: 09          .        ; &0A Read character definition
    equb &05                                                          ; fcdb: 05          .        ; &0B Read palette
    equb &00                                                          ; fcdc: 00          .        ; &0C Write palette
    equb &08                                                          ; fcdd: 08          .        ; &0D Read last two graphics cursor posns
    equb &18                                                          ; fcde: 18          .        ; &0E Read clock as string
    equb &00                                                          ; fcdf: 00          .        ; &0F Write clock as string
    equb &01                                                          ; fce0: 01          .        ; &10 Net transmit
    equb &0d                                                          ; fce1: 0d          .        ; &11 Net receive
    equb &80                                                          ; fce2: 80          .        ; &12 Net read arguments
    equb &04                                                          ; fce3: 04          .        ; &13 Net FS operation
    equb &80                                                          ; fce4: 80          .        ; &14 Net FS operation
; ***************************************************************************************
; Interrupt handler entry
;
; Hardware interrupt entry point. Saves A, checks the break flag in the stacked processor
; status to distinguish BRK from IRQ, and dispatches accordingly.
.interrupt_handler
    sta irq_a_store                                                   ; fce5: 85 fc       ..       ; Save A in irq_a_store
    pla                                                               ; fce7: 68          h        ; Pull stacked processor status
    pha                                                               ; fce8: 48          H        ; Push it back (non-destructive read)
    and #&10                                                          ; fce9: 29 10       ).       ; Isolate BRK flag (bit 4)
    bne brk_handler_entry                                             ; fceb: d0 10       ..       ; BRK flag set: handle BRK
    jmp (irq1v)                                                       ; fced: 6c 04 02    l..      ; Dispatch via IRQ1V
; ***************************************************************************************
; IRQ1 handler
;
; First-level IRQ handler. Checks Tube R4 for data transfer requests, then Tube R1 for
; escape/event notifications. Falls through to IRQ2V if neither.
.irq1_handler
    bit tube_r4_status                                                ; fcf0: 2c fe fe    ,..      ; Check Tube R4 for data
    bmi tube_r4_interrupt                                             ; fcf3: 30 4a       0J       ; Data present: handle transfer/error
    bit tube_r1_status                                                ; fcf5: 2c f8 fe    ,..      ; Check Tube R1 for data
    bmi tube_r1_interrupt                                             ; fcf8: 30 1e       0.       ; Data present: handle escape/event
    jmp (irq2v)                                                       ; fcfa: 6c 06 02    l..      ; Neither: dispatch via IRQ2V
; ***************************************************************************************
; BRK handler dispatch
;
; Extract the return address from the stack, subtract 1 to point to the byte after the
; BRK opcode (the error block), store the pointer in last_error (&FD/FE), then re-enable
; interrupts and dispatch via BRKV.
; &fcfd referenced 1 time by &fceb
.brk_handler_entry
    txa                                                               ; fcfd: 8a          .        ; Save X on stack
    pha                                                               ; fcfe: 48          H        ; Push X
    tsx                                                               ; fcff: ba          .        ; Get stack pointer
    lda irq_return_addr_lo,x                                          ; fd00: bd 03 01    ...      ; Get return address low from stack
    cld                                                               ; fd03: d8          .        ; Clear decimal mode
    sec                                                               ; fd04: 38          8        ; Set carry for subtract
    sbc #1                                                            ; fd05: e9 01       ..       ; Subtract 1 to point at error block
    sta last_error                                                    ; fd07: 85 fd       ..       ; Store as last_error low
    lda irq_return_addr_hi,x                                          ; fd09: bd 04 01    ...      ; Get return address high from stack
    sbc #0                                                            ; fd0c: e9 00       ..       ; Subtract borrow
    sta last_error_hi                                                 ; fd0e: 85 fe       ..       ; Store as last_error high
    pla                                                               ; fd10: 68          h        ; Restore X from stack
    tax                                                               ; fd11: aa          .        ; Transfer back to X
    lda irq_a_store                                                   ; fd12: a5 fc       ..       ; Get saved A from irq_a_store
    cli                                                               ; fd14: 58          X        ; Re-enable interrupts
    jmp (brkv)                                                        ; fd15: 6c 02 02    l..      ; Dispatch via BRKV
; ***************************************************************************************
; Handle Tube R1 interrupt (escape and events)
;
; Process data received via Tube R1. If bit 7 is set, it is an Escape state change
; (stored in escape_flag). Otherwise, it is an event notification: reads the event
; parameters (Y, X, event number) from R1 and dispatches via EVNTV.
; &fd18 referenced 1 time by &fcf8
.tube_r1_interrupt
    lda tube_r1_data                                                  ; fd18: ad f9 fe    ...      ; Read data from Tube R1
    bmi set_escape_flag                                               ; fd1b: 30 1c       0.       ; Bit 7 set: Escape state change
    tya                                                               ; fd1d: 98          .        ; Save Y
    pha                                                               ; fd1e: 48          H        ; Push Y
    txa                                                               ; fd1f: 8a          .        ; Save X
    pha                                                               ; fd20: 48          H        ; Push X
    jsr wait_for_tube_r1_byte                                         ; fd21: 20 80 fe     ..      ; Read event Y parameter via R1
    tay                                                               ; fd24: a8          .        ; Store in Y
    jsr wait_for_tube_r1_byte                                         ; fd25: 20 80 fe     ..      ; Read event X parameter via R1
    tax                                                               ; fd28: aa          .        ; Store in X
    jsr wait_for_tube_r1_byte                                         ; fd29: 20 80 fe     ..      ; Read event number via R1
    jsr dispatch_event                                                ; fd2c: 20 36 fd     6.      ; Dispatch event via EVNTV
    pla                                                               ; fd2f: 68          h        ; Restore X from stack
    tax                                                               ; fd30: aa          .        ; Transfer to X
    pla                                                               ; fd31: 68          h        ; Restore Y from stack
    tay                                                               ; fd32: a8          .        ; Transfer to Y
    lda irq_a_store                                                   ; fd33: a5 fc       ..       ; Get saved A from irq_a_store
    rti                                                               ; fd35: 40          @        ; Return from interrupt
; &fd36 referenced 1 time by &fd2c
.dispatch_event
    jmp (evntv)                                                       ; fd36: 6c 20 02    l .      ; Dispatch event via EVNTV
; ***************************************************************************************
; Set escape flag from Tube R1 data
;
; Called when Tube R1 data has bit 7 set, indicating an Escape state change. Shifts bit 6
; of the received byte into bit 7 via ASL and stores the result in escape_flag (&FF). Bit
; 7 set = Escape active.
; &fd39 referenced 1 time by &fd1b
.set_escape_flag
    asl a                                                             ; fd39: 0a          .        ; Shift bit 6 into bit 7 for Escape
    sta escape_flag                                                   ; fd3a: 85 ff       ..       ; Store as Escape flag
    lda irq_a_store                                                   ; fd3c: a5 fc       ..       ; Get saved A from irq_a_store
    rti                                                               ; fd3e: 40          @        ; Return from interrupt
; ***************************************************************************************
; Handle Tube R4 interrupt
;
; Process data received via Tube R4. If bit 7 is set, it is an error from the host: reads
; the error number and message via R2 into the error buffer, then executes the error via
; a JMP to the buffer (which starts with a BRK opcode).
;
; If bit 7 is clear, it is a data transfer request: falls through to data_transfer_setup.
; &fd3f referenced 1 time by &fcf3
.tube_r4_interrupt
    lda tube_r4_data                                                  ; fd3f: ad ff fe    ...      ; Read data from Tube R4
    bpl data_transfer_setup                                           ; fd42: 10 21       .!       ; Bit 7 clear: data transfer request
    cli                                                               ; fd44: 58          X        ; Re-enable IRQs for error reception
; &fd45 referenced 1 time by &fd48
.tube_r4_wait_error
    bit tube_r2_status                                                ; fd45: 2c fa fe    ,..      ; Poll Tube R2 for error data
    bpl tube_r4_wait_error                                            ; fd48: 10 fb       ..       ; Wait until data available
    lda tube_r2_data                                                  ; fd4a: ad fb fe    ...      ; Read and discard R2 sync byte
    lda #0                                                            ; fd4d: a9 00       ..       ; A=0 (BRK opcode)
    sta error_buffer                                                  ; fd4f: 8d 36 02    .6.      ; Store BRK at start of error buffer
    tay                                                               ; fd52: a8          .        ; Y=0 for buffer index
    jsr wait_for_tube_r2_byte                                         ; fd53: 20 75 f9     u.      ; Wait for error number byte
    sta error_buffer_errnum                                           ; fd56: 8d 37 02    .7.      ; Store error number in buffer
; &fd59 referenced 1 time by &fd60
.tube_r4_read_error_loop
    iny                                                               ; fd59: c8          .        ; Advance buffer index
    jsr wait_for_tube_r2_byte                                         ; fd5a: 20 75 f9     u.      ; Wait for next error string byte
    sta error_buffer_errnum,y                                         ; fd5d: 99 37 02    .7.      ; Store in error buffer
    bne tube_r4_read_error_loop                                       ; fd60: d0 f7       ..       ; Loop until NUL terminator
    jmp error_buffer                                                  ; fd62: 4c 36 02    L6.      ; Execute BRK in error buffer
; ***************************************************************************************
; Set up data transfer via NMI
;
; Configure the NMI handler for a data transfer.
;
; The transfer type (0-7) from R4 selects the NMI routine and the address pointer. Types
; 0-3 are single/double byte transfers. Types 4-5 are release. Types 6-7 are 256-byte
; block transfers.
;
; The setup phase consumes 7 bytes on R4 in this order: transfer type, called ID, address
; bytes 4/3/2/1 (only the low two are stored, via transfer_addr_ptr), then a sync byte.
; The transfer type byte has already been read by tube_r4_interrupt before falling
; through here; the other 6 are read below. Between the last address byte and the sync
; wait, two bytes are drained from R3 in the H-to-P direction via BIT tube_r3_data.
;
; No bytes are written to R3 during setup: any P-to-H R3 write happens later, from the
; NMI handler selected by the transfer type. For transfer types 0-5 the routine exits via
; RTI after the sync byte; for type 6 it runs transfer_write_loop to send 256 bytes to
; R3, and for type 7 it runs transfer_256_bytes_from_tube to read 256 bytes from R3.
;
; The sync byte is the final step of the host-side Tube handshake: the host writes it
; only once it is ready to begin the data phase. The parasite blocks in the BIT/BPL loop
; at transfer_wait_sync until bit 7 of R4 status is set, so if the sync byte is never
; written the parasite spins here indefinitely.
; &fd65 referenced 1 time by &fd42
.data_transfer_setup
    sta nmi_vector                                                    ; fd65: 8d fa ff    ...      ; Save transfer type in NMI vector
    tya                                                               ; fd68: 98          .        ; Save Y on stack
    pha                                                               ; fd69: 48          H        ; Push Y
    ldy nmi_vector                                                    ; fd6a: ac fa ff    ...      ; Get transfer type back
    lda nmi_routine_addr_table,y                                      ; fd6d: b9 70 fe    .p.      ; Look up NMI routine address low
    sta nmi_vector                                                    ; fd70: 8d fa ff    ...      ; Set NMI vector low byte
    lda nmi_routine_addr_hi_table,y                                   ; fd73: b9 78 fe    .x.      ; Look up NMI routine address high
    sta nmi_vector_hi                                                 ; fd76: 8d fb ff    ...      ; Set NMI vector high byte
    lda transfer_addr_ptr_table,y                                     ; fd79: b9 60 fe    .`.      ; Look up address pointer low
    sta transfer_addr_ptr                                             ; fd7c: 85 f4       ..       ; Set transfer_addr_ptr low
    lda transfer_addr_ptr_hi_table,y                                  ; fd7e: b9 68 fe    .h.      ; Look up address pointer high
    sta transfer_addr_ptr_hi                                          ; fd81: 85 f5       ..       ; Set transfer_addr_ptr high
; &fd83 referenced 1 time by &fd86
.transfer_wait_id
    bit tube_r4_status                                                ; fd83: 2c fe fe    ,..      ; Poll Tube R4 for called ID byte
    bpl transfer_wait_id                                              ; fd86: 10 fb       ..       ; Wait until data available
    lda tube_r4_data                                                  ; fd88: ad ff fe    ...      ; Consume called ID byte (value discarded)
    cpy #5                                                            ; fd8b: c0 05       ..       ; Type 5: release, no transfer needed
    beq restore_regs_and_rti                                          ; fd8d: f0 58       .X       ; Yes: exit immediately
    tya                                                               ; fd8f: 98          .        ; Save transfer type
    pha                                                               ; fd90: 48          H        ; Push transfer type
    ldy #1                                                            ; fd91: a0 01       ..       ; Y=1 for address byte index
; &fd93 referenced 1 time by &fd96
.transfer_read_addr4
    bit tube_r4_status                                                ; fd93: 2c fe fe    ,..      ; Poll Tube R4 for address byte 4
    bpl transfer_read_addr4                                           ; fd96: 10 fb       ..       ; Wait until data available
    lda tube_r4_data                                                  ; fd98: ad ff fe    ...      ; Read and discard byte 4 (bits 31-24)
; &fd9b referenced 1 time by &fd9e
.transfer_read_addr3
    bit tube_r4_status                                                ; fd9b: 2c fe fe    ,..      ; Poll Tube R4 for address byte 3
    bpl transfer_read_addr3                                           ; fd9e: 10 fb       ..       ; Wait until data available
    lda tube_r4_data                                                  ; fda0: ad ff fe    ...      ; Read and discard byte 3 (bits 23-16)
; &fda3 referenced 1 time by &fda6
.transfer_read_addr2
    bit tube_r4_status                                                ; fda3: 2c fe fe    ,..      ; Poll Tube R4 for address byte 2
    bpl transfer_read_addr2                                           ; fda6: 10 fb       ..       ; Wait until data available
    lda tube_r4_data                                                  ; fda8: ad ff fe    ...      ; Read address byte 2 (high)
    sta (transfer_addr_ptr),y                                         ; fdab: 91 f4       ..       ; Store via transfer address pointer
    dey                                                               ; fdad: 88          .        ; Decrement to byte 0
; &fdae referenced 1 time by &fdb1
.transfer_read_addr1
    bit tube_r4_status                                                ; fdae: 2c fe fe    ,..      ; Poll Tube R4 for address byte 1
    bpl transfer_read_addr1                                           ; fdb1: 10 fb       ..       ; Wait until data available
    lda tube_r4_data                                                  ; fdb3: ad ff fe    ...      ; Read address byte 1 (low)
    sta (transfer_addr_ptr),y                                         ; fdb6: 91 f4       ..       ; Store via transfer address pointer
    bit tube_r3_data                                                  ; fdb8: 2c fd fe    ,..      ; Drain 1st byte from R3 H-to-P FIFO (BIT reads R3 data)
    bit tube_r3_data                                                  ; fdbb: 2c fd fe    ,..      ; Drain 2nd byte from R3 H-to-P FIFO
; &fdbe referenced 1 time by &fdc1
.transfer_wait_sync
    bit tube_r4_status                                                ; fdbe: 2c fe fe    ,..      ; Poll Tube R4 status for host sync byte
    bpl transfer_wait_sync                                            ; fdc1: 10 fb       ..       ; Spin until host writes sync byte (gates data phase)
    lda tube_r4_data                                                  ; fdc3: ad ff fe    ...      ; Read sync byte
    pla                                                               ; fdc6: 68          h        ; Restore transfer type
    cmp #6                                                            ; fdc7: c9 06       ..       ; Is it type 6 or above?
    bcc restore_regs_and_rti                                          ; fdc9: 90 1c       ..       ; Below 6: exit (single/double/release)
    bne transfer_256_bytes_from_tube                                  ; fdcb: d0 1f       ..       ; Not 6: must be type 7 (read block)
    ldy #0                                                            ; fdcd: a0 00       ..       ; Y=0 for 256-byte counter
; &fdcf referenced 2 times by &fdd4, &fddd
.transfer_write_loop
    lda tube_r3_status                                                ; fdcf: ad fc fe    ...      ; Read Tube R3 status
    and #&80                                                          ; fdd2: 29 80       ).       ; Isolate ready bit
    bpl transfer_write_loop                                           ; fdd4: 10 f9       ..       ; Wait until R3 ready
.transfer_write_read_byte
nmi6_transfer_addr = transfer_write_read_byte+1
    lda irq_vector_hi,y                                               ; fdd6: b9 ff ff    ...      ; Read byte (address patched)
    sta tube_r3_data                                                  ; fdd9: 8d fd fe    ...      ; Send to Tube R3
    iny                                                               ; fddc: c8          .        ; Next byte
    bne transfer_write_loop                                           ; fddd: d0 f0       ..       ; Loop for 256 bytes
; &fddf referenced 1 time by &fde2
.transfer_write_sync
    bit tube_r3_status                                                ; fddf: 2c fc fe    ,..      ; Poll Tube R3 status
    bpl transfer_write_sync                                           ; fde2: 10 fb       ..       ; Wait until R3 ready
    sta tube_r3_data                                                  ; fde4: 8d fd fe    ...      ; Send final sync byte to R3
; ***************************************************************************************
; Restore registers and return from interrupt
;
; Common exit path for data transfer setup. Restores Y from the stack, retrieves saved A
; from irq_a_store, and executes RTI.
; &fde7 referenced 3 times by &fd8d, &fdc9, &fdfe
.restore_regs_and_rti
    pla                                                               ; fde7: 68          h        ; Restore Y from stack
    tay                                                               ; fde8: a8          .        ; Transfer to Y
    lda irq_a_store                                                   ; fde9: a5 fc       ..       ; Get saved A from irq_a_store
    rti                                                               ; fdeb: 40          @        ; Return from interrupt
; ***************************************************************************************
; Transfer 256 bytes from Tube via R3
;
; Read 256 bytes from Tube R3 into memory at the address patched into the STA
; instruction. Used for transfer type 7 (256-byte read from host).
;
; The target address is set up by data_transfer_setup via the transfer address pointer
; table.
; &fdec referenced 1 time by &fdcb
.transfer_256_bytes_from_tube
    ldy #0                                                            ; fdec: a0 00       ..       ; Y=0 for 256-byte counter
; &fdee referenced 2 times by &fdf3, &fdfc
.transfer_read_loop
    lda tube_r3_status                                                ; fdee: ad fc fe    ...      ; Read Tube R3 status
    and #&80                                                          ; fdf1: 29 80       ).       ; Isolate data ready bit
    bpl transfer_read_loop                                            ; fdf3: 10 f9       ..       ; Wait until R3 has data
    lda tube_r3_data                                                  ; fdf5: ad fd fe    ...      ; Read byte from Tube R3
.transfer_read_store_byte
nmi7_transfer_addr = transfer_read_store_byte+1
    sta irq_vector_hi,y                                               ; fdf8: 99 ff ff    ...      ; Store byte (address patched)
    iny                                                               ; fdfb: c8          .        ; Next byte
    bne transfer_read_loop                                            ; fdfc: d0 f0       ..       ; Loop for 256 bytes
.transfer_read_done
; &fdff used as index base 2 times by &f819, &f81c
io_page_base = transfer_read_done+1
    beq restore_regs_and_rti                                          ; fdfe: f0 e7       ..       ; Always branch to exit
; ***************************************************************************************
; NMI: single byte to Tube
;
; Transfer type 0. Sends one byte from the transfer address to Tube R3, then increments
; the address.
.nmi_single_byte_to_tube
    pha                                                               ; fe00: 48          H        ; Save A
.nmi0_read_byte
; &fe02 referenced 1 time by &fe07
nmi0_transfer_addr = nmi0_read_byte+1
; &fe03 referenced 1 time by &fe0c
lfe03 = nmi0_read_byte+2
    lda irq_vector_hi                                                 ; fe01: ad ff ff    ...      ; Read byte (address patched by setup)
    sta tube_r3_data                                                  ; fe04: 8d fd fe    ...      ; Send byte to Tube R3
    inc nmi0_transfer_addr                                            ; fe07: ee 02 fe    ...      ; Increment address low byte
    bne nmi0_done                                                     ; fe0a: d0 03       ..       ; No carry: skip high byte increment
    inc lfe03                                                         ; fe0c: ee 03 fe    ...      ; Increment address high byte
; &fe0f referenced 1 time by &fe0a
.nmi0_done
    pla                                                               ; fe0f: 68          h        ; Restore A
    rti                                                               ; fe10: 40          @        ; Return from NMI
; ***************************************************************************************
; NMI: single byte from Tube
;
; Transfer type 1. Reads one byte from Tube R3 and stores it at the transfer address,
; then increments the address.
.nmi_single_byte_from_tube
    pha                                                               ; fe11: 48          H        ; Save A
    lda tube_r3_data                                                  ; fe12: ad fd fe    ...      ; Read byte from Tube R3
.sub_cfe15
; &fe16 referenced 1 time by &fe18
nmi1_transfer_addr = sub_cfe15+1
; &fe17 referenced 1 time by &fe1d
lfe17 = sub_cfe15+2
    sta irq_vector_hi                                                 ; fe15: 8d ff ff    ...      ; Store byte (address patched by setup)
    inc nmi1_transfer_addr                                            ; fe18: ee 16 fe    ...      ; Increment address low byte
    bne nmi1_done                                                     ; fe1b: d0 03       ..       ; No carry: skip high byte increment
    inc lfe17                                                         ; fe1d: ee 17 fe    ...      ; Increment address high byte
; &fe20 referenced 1 time by &fe1b
.nmi1_done
    pla                                                               ; fe20: 68          h        ; Restore A
    rti                                                               ; fe21: 40          @        ; Return from NMI
; ***************************************************************************************
; NMI: two bytes to Tube
;
; Transfer type 2. Sends two consecutive bytes from (data_transfer_addr) to Tube R3,
; incrementing the pointer after each byte.
.nmi_two_bytes_to_tube
    pha                                                               ; fe22: 48          H        ; Save A
    tya                                                               ; fe23: 98          .        ; Save Y
    pha                                                               ; fe24: 48          H        ; Push Y
    ldy #0                                                            ; fe25: a0 00       ..       ; Y=0 for indirect indexed access
    lda (data_transfer_addr),y                                        ; fe27: b1 f6       ..       ; Read first byte via pointer
    sta tube_r3_data                                                  ; fe29: 8d fd fe    ...      ; Send to Tube R3
    inc data_transfer_addr                                            ; fe2c: e6 f6       ..       ; Increment transfer address low
    bne nmi2_second_byte                                              ; fe2e: d0 02       ..       ; No carry: skip high increment
    inc data_transfer_addr_hi                                         ; fe30: e6 f7       ..       ; Increment transfer address high
; &fe32 referenced 1 time by &fe2e
.nmi2_second_byte
    lda (data_transfer_addr),y                                        ; fe32: b1 f6       ..       ; Read second byte via pointer
    sta tube_r3_data                                                  ; fe34: 8d fd fe    ...      ; Send to Tube R3
    inc data_transfer_addr                                            ; fe37: e6 f6       ..       ; Increment transfer address low
    bne nmi2_done                                                     ; fe39: d0 02       ..       ; No carry: skip high increment
    inc data_transfer_addr_hi                                         ; fe3b: e6 f7       ..       ; Increment transfer address high
; &fe3d referenced 1 time by &fe39
.nmi2_done
    pla                                                               ; fe3d: 68          h        ; Restore Y from stack
    tay                                                               ; fe3e: a8          .        ; Transfer to Y
    pla                                                               ; fe3f: 68          h        ; Restore A
    rti                                                               ; fe40: 40          @        ; Return from NMI
; ***************************************************************************************
; NMI: two bytes from Tube
;
; Transfer type 3. Reads two bytes from Tube R3 and stores them at (data_transfer_addr),
; incrementing the pointer after each byte.
.nmi_two_bytes_from_tube
    pha                                                               ; fe41: 48          H        ; Save A
    tya                                                               ; fe42: 98          .        ; Save Y
    pha                                                               ; fe43: 48          H        ; Push Y
    ldy #0                                                            ; fe44: a0 00       ..       ; Y=0 for indirect indexed access
    lda tube_r3_data                                                  ; fe46: ad fd fe    ...      ; Read first byte from Tube R3
    sta (data_transfer_addr),y                                        ; fe49: 91 f6       ..       ; Store via transfer address pointer
    inc data_transfer_addr                                            ; fe4b: e6 f6       ..       ; Increment transfer address low
    bne nmi3_second_byte                                              ; fe4d: d0 02       ..       ; No carry: skip high increment
    inc data_transfer_addr_hi                                         ; fe4f: e6 f7       ..       ; Increment transfer address high
; &fe51 referenced 1 time by &fe4d
.nmi3_second_byte
    lda tube_r3_data                                                  ; fe51: ad fd fe    ...      ; Read second byte from Tube R3
    sta (data_transfer_addr),y                                        ; fe54: 91 f6       ..       ; Store via transfer address pointer
    inc data_transfer_addr                                            ; fe56: e6 f6       ..       ; Increment transfer address low
    bne nmi3_done                                                     ; fe58: d0 02       ..       ; No carry: skip high increment
    inc data_transfer_addr_hi                                         ; fe5a: e6 f7       ..       ; Increment transfer address high
; &fe5c referenced 1 time by &fe58
.nmi3_done
    pla                                                               ; fe5c: 68          h        ; Restore Y from stack
    tay                                                               ; fe5d: a8          .        ; Transfer to Y
    pla                                                               ; fe5e: 68          h        ; Restore A
    rti                                                               ; fe5f: 40          @        ; Return from NMI
; ***************************************************************************************
; Transfer address pointer table (low bytes)
;
; Eight entries indexed by transfer type (0-7). Each entry is the low byte of the address
; of the two-byte field that holds the current transfer address for that type. Types 0-1
; and 6-7 point to self-modifying code address operands; types 2-5 point to the
; data_transfer_addr zero page location (&F6).
; &fe60 used as index base 1 time by &fd79
.transfer_addr_ptr_table
    equb <(nmi0_transfer_addr)                                        ; fe60: 02          .        ; Low bytes of transfer addr pointers
    equb <(nmi1_transfer_addr)                                        ; fe61: 16          .     
    equb <(data_transfer_addr)                                        ; fe62: f6          .     
    equb <(data_transfer_addr)                                        ; fe63: f6          .     
    equb <(data_transfer_addr)                                        ; fe64: f6          .     
    equb <(data_transfer_addr)                                        ; fe65: f6          .     
    equb <(nmi6_transfer_addr)                                        ; fe66: d7          .     
    equb <(nmi7_transfer_addr)                                        ; fe67: f9          .     
; ***************************************************************************************
; Transfer address pointer table (high bytes)
;
; High bytes corresponding to the low byte table at &FE60. Together they form 8 pointers
; to the address fields used by each transfer type.
; &fe68 used as index base 1 time by &fd7e
.transfer_addr_ptr_hi_table
    equb >(nmi0_transfer_addr)                                        ; fe68: fe          .        ; High bytes of transfer addr pointers
    equb >(nmi1_transfer_addr)                                        ; fe69: fe          .     
    equb >(data_transfer_addr)                                        ; fe6a: 00          .     
    equb >(data_transfer_addr)                                        ; fe6b: 00          .     
    equb >(data_transfer_addr)                                        ; fe6c: 00          .     
    equb >(data_transfer_addr)                                        ; fe6d: 00          .     
    equb >(nmi6_transfer_addr)                                        ; fe6e: fd          .     
    equb >(nmi7_transfer_addr)                                        ; fe6f: fd          .     
; ***************************************************************************************
; NMI routine address table (low bytes)
;
; Eight entries indexed by transfer type (0-7). Each entry is the low byte of the NMI
; handler routine for that type. Types 0-3 have dedicated handlers; types 4-7 all use the
; NMI acknowledge routine.
; &fe70 used as index base 1 time by &fd6d
.nmi_routine_addr_table
    equb <(nmi_single_byte_to_tube)                                   ; fe70: 00          .        ; Low bytes of NMI handler addresses
    equb <(nmi_single_byte_from_tube)                                 ; fe71: 11          .     
    equb <(nmi_two_bytes_to_tube)                                     ; fe72: 22          "     
    equb <(nmi_two_bytes_from_tube)                                   ; fe73: 41          A     
    equb <(nmi_acknowledge)                                           ; fe74: b3          .     
    equb <(nmi_acknowledge)                                           ; fe75: b3          .     
    equb <(nmi_acknowledge)                                           ; fe76: b3          .     
    equb <(nmi_acknowledge)                                           ; fe77: b3          .     
; ***************************************************************************************
; NMI routine address table (high bytes)
;
; High bytes corresponding to the low byte table at &FE70. Together they form 8 NMI
; handler addresses.
; &fe78 used as index base 1 time by &fd73
.nmi_routine_addr_hi_table
    equb >(nmi_single_byte_to_tube)                                   ; fe78: fe          .        ; High bytes of NMI handler addresses
    equb >(nmi_single_byte_from_tube)                                 ; fe79: fe          .     
    equb >(nmi_two_bytes_to_tube)                                     ; fe7a: fe          .     
    equb >(nmi_two_bytes_from_tube)                                   ; fe7b: fe          .     
    equb >(nmi_acknowledge)                                           ; fe7c: fe          .     
    equb >(nmi_acknowledge)                                           ; fe7d: fe          .     
    equb >(nmi_acknowledge)                                           ; fe7e: fe          .     
    equb >(nmi_acknowledge)                                           ; fe7f: fe          .     
; ***************************************************************************************
; Wait for byte in Tube R1
;
; Wait for data in Tube R1, allowing Tube R4 transfer requests to be serviced via IRQ
; while waiting.
;
; Polls R1 status; if R4 has data instead, briefly enables interrupts to let the R4
; handler run, then resumes polling R1.
;
; On Exit:
;     A: byte from Tube R1
; &fe80 referenced 5 times by &fd21, &fd25, &fd29, &fe88, &fe91
.wait_for_tube_r1_byte
    bit tube_r1_status                                                ; fe80: 2c f8 fe    ,..      ; Check Tube R1 for data
    bmi tube_r1_read_byte                                             ; fe83: 30 0f       0.       ; Data available: go read it
    bit tube_r4_status                                                ; fe85: 2c fe fe    ,..      ; Check Tube R4 for pending transfers
    bpl wait_for_tube_r1_byte                                         ; fe88: 10 f6       ..       ; Nothing pending: keep polling R1
    lda irq_a_store                                                   ; fe8a: a5 fc       ..       ; Save irq_a_store before IRQ
    php                                                               ; fe8c: 08          .        ; Save processor status
    cli                                                               ; fe8d: 58          X        ; Allow one IRQ to service R4
    plp                                                               ; fe8e: 28          (        ; Restore processor status
    sta irq_a_store                                                   ; fe8f: 85 fc       ..       ; Restore irq_a_store after IRQ
    jmp wait_for_tube_r1_byte                                         ; fe91: 4c 80 fe    L..      ; Continue polling R1
; &fe94 referenced 1 time by &fe83
.tube_r1_read_byte
    lda tube_r1_data                                                  ; fe94: ad f9 fe    ...      ; Read byte from Tube R1
    rts                                                               ; fe97: 60          `        ; Return with byte in A
; ***************************************************************************************
; Print inline text
;
; Print the text string embedded immediately after the JSR to this routine. Characters
; are sent to OSWRCH until a byte with bit 7 set is encountered, which terminates the
; string.
;
; Execution resumes by jumping directly to the address of the terminator byte, so the
; terminator is executed as a 6502 instruction. This is why NOP (&EA) is used: bit 7 is
; set (ending the string loop), it is a single- byte opcode (no operand to skip), and it
; has no effect when executed. This saves the bytes and cycles that would otherwise be
; needed to increment the pointer past the terminator before returning.
;
; On Exit:
;     A: terminator byte (bit 7 set)
; &fe98 referenced 2 times by &f860, &fa17
.print_embedded_text
    pla                                                               ; fe98: 68          h        ; Pull return address low
    sta control_block_ptr                                             ; fe99: 85 fa       ..       ; Store in control_block_ptr low
    pla                                                               ; fe9b: 68          h        ; Pull return address high
    sta control_block_ptr_hi                                          ; fe9c: 85 fb       ..       ; Store in control_block_ptr high
    ldy #0                                                            ; fe9e: a0 00       ..       ; Y=0 for indirect access
; &fea0 referenced 1 time by &fead
.print_text_loop
    inc control_block_ptr                                             ; fea0: e6 fa       ..       ; Increment string pointer low
    bne print_text_get_char                                           ; fea2: d0 02       ..       ; No carry: skip high byte
.print_text_inc_high
    inc control_block_ptr_hi                                          ; fea4: e6 fb       ..       ; Increment string pointer high
; &fea6 referenced 1 time by &fea2
.print_text_get_char
    lda (control_block_ptr),y                                         ; fea6: b1 fa       ..       ; Read character from inline string
    bmi print_text_resume                                             ; fea8: 30 06       0.       ; Bit 7 set: end of string
    jsr oswrch_entry                                                  ; feaa: 20 ee ff     ..      ; Print character via OSWRCH
    jmp print_text_loop                                               ; fead: 4c a0 fe    L..      ; Loop for next character
; &feb0 referenced 1 time by &fea8
.print_text_resume
    jmp (control_block_ptr)                                           ; feb0: 6c fa 00    l..      ; Jump to terminator byte and execute it
; ***************************************************************************************
; NMI acknowledge
;
; Acknowledge an NMI by writing A to Tube R3, then return from interrupt. Used as the NMI
; handler for transfer types 4-7 (release and 256-byte block transfers, which do not use
; NMI for individual bytes). Also the initial value of the NMI vector at reset.
.nmi_acknowledge
    sta tube_r3_data                                                  ; feb3: 8d fd fe    ...      ; Write to Tube R3 to acknowledge NMI
    rti                                                               ; feb6: 40          @     
; ***************************************************************************************
; Unused fill between code and I/O window
;
; 39 bytes of &FF fill between the end of the NMI acknowledge routine and the start of
; the Tube ULA I/O register window at &FEF0.
.unused_fill_pre_io
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; feb7: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; fec3: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; fecf: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; fedb: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff                  ; fee7: ff ff ff... ......
; ***************************************************************************************
; Tube ULA I/O window
;
; Hardware registers overlay these ROM addresses. The ROM bytes here are never read by
; the CPU. The registers at &FEF0-&FEF7 mirror &FEF8-&FEFF but are not used by the Tube
; Client software.
.tube_ula_io_window
    equb &ff                                                          ; fef0: ff          .        ; Tube R1 status (mirror, not used)
    equb &ff                                                          ; fef1: ff          .        ; Tube R1 data (mirror, not used)
    equb &ff                                                          ; fef2: ff          .        ; Tube R2 status (mirror, not used)
    equb &ff                                                          ; fef3: ff          .        ; Tube R2 data (mirror, not used)
    equb &ff                                                          ; fef4: ff          .        ; Tube R3 status (mirror, not used)
    equb &ff                                                          ; fef5: ff          .        ; Tube R3 data (mirror, not used)
    equb &ff                                                          ; fef6: ff          .        ; Tube R4 status (mirror, not used)
    equb &ff                                                          ; fef7: ff          .        ; Tube R4 data (mirror, not used)
; &fef8 referenced 4 times by &f859, &f962, &fcf5, &fe80
.tube_r1_status
    equb &ff                                                          ; fef8: ff          .        ; Tube register 1 status
; &fef9 referenced 3 times by &f968, &fd18, &fe94
.tube_r1_data
    equb &ff                                                          ; fef9: ff          .        ; Tube register 1 data
; &fefa referenced 25 times by &f975, &f9b8, &fa7a, &fa82, &fa8b, &fa93, &faab, &fab3, &fabb, &fac4, &fad5, &fadf, &fae7, &fb09, &fb11, &fb2d, &fb38, &fb59, &fb64, &fb7e, &fb96, &fbb2, &fbd2, &fc4a, &fd45
.tube_r2_status
    equb &ff                                                          ; fefa: ff          .        ; Tube register 2 status
; &fefb referenced 25 times by &f97a, &f9bf, &fa7f, &fa87, &fa90, &fa98, &fab0, &fab8, &fac0, &fac9, &fada, &fae4, &faec, &fb0e, &fb16, &fb32, &fb3f, &fb5e, &fb69, &fb85, &fb9b, &fbb7, &fbd7, &fc4f, &fd4a
.tube_r2_data
    equb &ff                                                          ; fefb: ff          .        ; Tube register 2 data
; &fefc referenced 3 times by &fdcf, &fddf, &fdee
.tube_r3_status
    equb &ff                                                          ; fefc: ff          .        ; Tube register 3 status
; &fefd referenced 12 times by &fdb8, &fdbb, &fdd9, &fde4, &fdf5, &fe04, &fe12, &fe29, &fe34, &fe46, &fe51, &feb3
.tube_r3_data
    equb &ff                                                          ; fefd: ff          .        ; Tube register 3 data
; &fefe referenced 8 times by &fcf0, &fd83, &fd93, &fd9b, &fda3, &fdae, &fdbe, &fe85
.tube_r4_status
    equb &ff                                                          ; fefe: ff          .        ; Tube register 4 status
; &feff referenced 7 times by &fd3f, &fd88, &fd98, &fda0, &fda8, &fdb3, &fdc3
.tube_r4_data
    equb &ff                                                          ; feff: ff          .        ; Tube register 4 data
; ***************************************************************************************
; Unused fill in lower page &FF
;
; The reset code copies all of page &FF to RAM with LDA/STA &FF00,X but only &FF80
; onwards contains the default vector table and MOS entry points.
; &ff00 used as index base 2 times by &f802, &f805
.unused_fill_page_ff
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff00: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff0c: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff18: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff24: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff30: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff3c: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff48: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff54: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff60: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff   ; ff6c: ff ff ff... ......
    equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff                       ; ff78: ff ff ff... ......
; ***************************************************************************************
; Default MOS vector table
;
; 27 two-byte entries (54 bytes) copied to &0200-&0235 at reset. Each entry is the
; initial value for the corresponding MOS vector. Vectors for unimplemented functions
; point to the 'unsupported' error handler; unused event and indirect vectors point to
; null_return (RTS).
; &ff80 used as index base 1 time by &f80d
.default_vector_table
    equw unsupported                                                  ; ff80: b7 fc       ..       ; USERV - User vector
    equw error_handler                                                ; ff82: 45 f9       E.       ; BRKV - BRK vector
    equw irq1_handler                                                 ; ff84: f0 fc       ..       ; IRQ1V - Primary IRQ handler
    equw unsupported                                                  ; ff86: b7 fc       ..       ; IRQ2V - Secondary IRQ handler
    equw oscli_impl                                                   ; ff88: ca f9       ..       ; CLIV - OSCLI vector
    equw osbyte_impl                                                  ; ff8a: 73 fa       s.       ; BYTEV - OSBYTE vector
    equw osword_impl                                                  ; ff8c: ff fa       ..       ; WORDV - OSWORD vector
    equw oswrch_impl                                                  ; ff8e: 62 f9       b.       ; WRCHV - OSWRCH vector
    equw osrdch_impl                                                  ; ff90: 6c f9       l.       ; RDCHV - OSRDCH vector
    equw osfile_impl                                                  ; ff92: 53 fc       S.       ; FILEV - OSFILE vector
    equw osargs_impl                                                  ; ff94: cc fb       ..       ; ARGSV - OSARGS vector
    equw osbget_impl                                                  ; ff96: 2a fc       *.       ; BGetV - OSBGET vector
    equw osbput_impl                                                  ; ff98: 36 fc       6.       ; BPutV - OSBPUT vector
    equw osgbpb_impl                                                  ; ff9a: 8e fc       ..       ; GBPBV - OSGBPB vector
    equw osfind_impl                                                  ; ff9c: 0c fc       ..       ; FINDV - OSFIND vector
    equw unsupported                                                  ; ff9e: b7 fc       ..       ; FSCV - FS control vector
    equw null_return                                                  ; ffa0: 7d f9       }.       ; EVNTV - Event vector
    equw unsupported                                                  ; ffa2: b7 fc       ..       ; UPTV - User print vector
    equw unsupported                                                  ; ffa4: b7 fc       ..       ; NETV - Network vector
    equw unsupported                                                  ; ffa6: b7 fc       ..       ; VduV - Unrecognised VDU vector
    equw unsupported                                                  ; ffa8: b7 fc       ..       ; KEYV - Keyboard vector
    equw unsupported                                                  ; ffaa: b7 fc       ..       ; INSV - Insert buffer vector
    equw unsupported                                                  ; ffac: b7 fc       ..       ; RemV - Remove buffer vector
    equw unsupported                                                  ; ffae: b7 fc       ..       ; CNPV - Count/purge buffer vector
    equw null_return                                                  ; ffb0: 7d f9       }.       ; IND1V - Spare indirect vector 1
    equw null_return                                                  ; ffb2: 7d f9       }.       ; IND2V - Spare indirect vector 2
    equw null_return                                                  ; ffb4: 7d f9       }.       ; IND3V - Spare indirect vector 3
; ***************************************************************************************
; Vector table descriptor
;
; Three-byte block at &FFB6 used by OSBYTE &FD (read vector table info). Byte 0 = length
; of the vector table in bytes (&36 = 54 = 27 vectors). Bytes 1-2 = address of the
; default vector table (&FF80).
.vector_table_info
    equb &36                                                          ; ffb6: 36          6        ; Vector table: length &36 at &FF80  Vector count in bytes (&36 = 27 words)
    equw default_vector_table                                         ; ffb7: 80 ff       ..       ; Address of default vector table
; ***************************************************************************************
; MOS entry: unsupported (5 stubs at &FFB9-&FFC7)
;
; Five consecutive JMP unsupported stubs at &FFB9, &FFBC, &FFBF, &FFC2, &FFC5. In the
; v1.10 external ROM, all five generate a 'Bad' error. These addresses are reserved for
; MOS compatibility but have no function in this Tube Client.
.mos_stub_unsupported_1
    jmp unsupported                                                   ; ffb9: 4c b7 fc    L..      ; Unsupported: generates 'Bad' error
.mos_stub_unsupported_2
    jmp unsupported                                                   ; ffbc: 4c b7 fc    L..   
.mos_stub_unsupported_3
    jmp unsupported                                                   ; ffbf: 4c b7 fc    L..   
.mos_stub_unsupported_4
    jmp unsupported                                                   ; ffc2: 4c b7 fc    L..   
.mos_stub_unsupported_5
    jmp unsupported                                                   ; ffc5: 4c b7 fc    L..   
; ***************************************************************************************
; MOS entry: NVRDCH (non-vectored RDCH)
;
; Jump directly to the OSRDCH implementation, bypassing RDCHV. Used when the caller needs
; to ensure the real RDCH handler runs regardless of any vector interception.
.nvrdch
    jmp osrdch_impl                                                   ; ffc8: 4c 6c f9    Ll.      ; Non-vectored RDCH
; ***************************************************************************************
; MOS entry: NVWRCH (non-vectored WRCH)
;
; Jump directly to the OSWRCH implementation, bypassing WRCHV. Used when the caller needs
; to ensure the real WRCH handler runs regardless of any vector interception.
.nvwrch
    jmp oswrch_impl                                                   ; ffcb: 4c 62 f9    Lb.      ; Non-vectored WRCH
; ***************************************************************************************
; MOS entry: OSFIND
;
; Open or close a file. Dispatches via FINDV (&021C).
;
; On Entry:
;     A: 0 to close, non-zero to open
;     Y: handle (close) or XY => filename (open)
;
; On Exit:
;     A: file handle (open) or preserved (close)
.osfind_entry
    jmp (findv)                                                       ; ffce: 6c 1c 02    l..      ; Dispatch via FINDV
; ***************************************************************************************
; MOS entry: OSGBPB
;
; Multiple-byte get or put. Dispatches via GBPBV (&021A).
;
; On Entry:
;     A: function
;     XY: 13-byte control block address
.osgbpb_entry
    jmp (gbpbv)                                                       ; ffd1: 6c 1a 02    l..      ; Dispatch via GBPBV
; ***************************************************************************************
; MOS entry: OSBPUT
;
; Write a byte to an open file. Dispatches via BPUTV (&0218).
;
; On Entry:
;     A: byte to write
;     Y: file handle
.osbput_entry
    jmp (bputv)                                                       ; ffd4: 6c 18 02    l..      ; Dispatch via BPUTV
; ***************************************************************************************
; MOS entry: OSBGET
;
; Read a byte from an open file. Dispatches via BGETV (&0216).
;
; On Entry:
;     Y: file handle
;
; On Exit:
;     A: byte read
;     C: set if EOF
.osbget_entry
    jmp (bgetv)                                                       ; ffd7: 6c 16 02    l..      ; Dispatch via BGETV
; ***************************************************************************************
; MOS entry: OSARGS
;
; Read or write open file arguments. Dispatches via ARGSV (&0214).
;
; On Entry:
;     A: function
;     X: zero-page data word address
;     Y: handle
.osargs_entry
    jmp (argsv)                                                       ; ffda: 6c 14 02    l..      ; Dispatch via ARGSV
; ***************************************************************************************
; MOS entry: OSFILE
;
; Whole-file operations. Dispatches via FILEV (&0212).
;
; On Entry:
;     A: function
;     XY: 18-byte control block address
.osfile_entry
    jmp (filev)                                                       ; ffdd: 6c 12 02    l..      ; Dispatch via FILEV
; ***************************************************************************************
; MOS entry: OSRDCH
;
; Read a character from the input stream. Dispatches via RDCHV (&0210).
;
; On Exit:
;     A: character
;     C: set if Escape
.osrdch_entry
    jmp (rdchv)                                                       ; ffe0: 6c 10 02    l..      ; Dispatch via RDCHV
; ***************************************************************************************
; MOS entry: OSASCI
;
; Write a character, converting CR to CR+LF. If the character is &0D, falls through to
; OSNEWL to send LF then CR. Otherwise jumps directly to OSWRCH.
;
; On Entry:
;     A: character to write
.osasci_entry
    cmp #&0d                                                          ; ffe3: c9 0d       ..       ; Is it carriage return?
    bne oswrch_entry                                                  ; ffe5: d0 07       ..       ; No: skip newline, go to OSWRCH
; ***************************************************************************************
; MOS entry: OSNEWL
;
; Send a newline sequence (LF followed by CR) via OSWRCH. Loads A=&0A, calls OSWRCH, then
; falls through to OSWRCR which loads A=&0D and calls OSWRCH.
; &ffe7 referenced 2 times by &f948, &f957
.osnewl_entry
    lda #&0a                                                          ; ffe7: a9 0a       ..       ; Send linefeed first
    jsr oswrch_entry                                                  ; ffe9: 20 ee ff     ..      ; Send linefeed via OSWRCH
; ***************************************************************************************
; MOS entry: OSWRCR
;
; Send a carriage return via OSWRCH. Loads A=&0D and falls through to OSWRCH.
.oswrcr_entry
    lda #&0d                                                          ; ffec: a9 0d       ..       ; Load carriage return
; ***************************************************************************************
; MOS entry: OSWRCH
;
; Write a character to the output stream. Dispatches via WRCHV (&020E).
;
; On Entry:
;     A: character to write
;
; On Exit:
;     A: preserved
; &ffee referenced 5 times by &f88f, &f951, &feaa, &ffe5, &ffe9
.oswrch_entry
    jmp (wrchv)                                                       ; ffee: 6c 0e 02    l..      ; Dispatch via WRCHV
; ***************************************************************************************
; MOS entry: OSWORD
;
; Perform a word-based MOS operation. Dispatches via WORDV (&020C).
;
; On Entry:
;     A: function
;     XY: control block address
; &fff1 referenced 1 time by &f898
.osword_entry
    jmp (wordv)                                                       ; fff1: 6c 0c 02    l..      ; Dispatch via WORDV
; ***************************************************************************************
; MOS entry: OSBYTE
;
; Perform a byte-based MOS operation. Dispatches via BYTEV (&020A).
;
; On Entry:
;     A: function
;     X: parameter 1
;     Y: parameter 2
; &fff4 referenced 1 time by &f8a9
.osbyte_entry
    jmp (bytev)                                                       ; fff4: 6c 0a 02    l..      ; Dispatch via BYTEV
; ***************************************************************************************
; MOS entry: OSCLI
;
; Execute a star command. Dispatches via CLIV (&0208).
;
; On Entry:
;     XY: command string address (CR-terminated)
; &fff7 referenced 1 time by &f8a1
.oscli_entry
    jmp (cliv)                                                        ; fff7: 6c 08 02    l..      ; Dispatch via CLIV
; &fffa referenced 3 times by &fd65, &fd6a, &fd70
.nmi_vector
; &fffb referenced 1 time by &fd76
nmi_vector_hi = nmi_vector+1
    equw nmi_acknowledge                                              ; fffa: b3 fe       ..       ; NMI vector (patched at runtime)
.reset_vector
    equw reset                                                        ; fffc: 00 f8       ..       ; RESET vector
.irq_vector
; &ffff referenced 2 times by &fe01, &fe15; also used as index base 2 times by &fdd6, &fdf8
irq_vector_hi = irq_vector+1
    equw interrupt_handler                                            ; fffe: e5 fc       ..       ; IRQ/BRK vector
.pydis_end

save pydis_start, pydis_end

; Label references by decreasing frequency:
;     send_byte_to_tube_r2:          25
;     send_command:                  25
;     tube_r2_data:                  25
;     tube_r2_status:                25
;     string_ptr:                    23
;     wait_for_tube_r2_byte:         18
;     control_block_ptr:             14
;     tube_r3_data:                  12
;     data_transfer_addr:            11
;     string_ptr_hi:                  9
;     tube_r4_status:                 8
;     current_program:                7
;     data_transfer_addr_hi:          7
;     irq_a_store:                    7
;     last_error:                     7
;     oscli_send_to_host:             7
;     tube_r4_data:                   7
;     control_block_ptr_hi:           6
;     current_program_hi:             5
;     memory_top:                     5
;     oswrch_entry:                   5
;     unsupported:                    5
;     wait_for_tube_r1_byte:          5
;     command_help:                   4
;     enter_raw_code:                 4
;     irq_vector_hi:                  4
;     memory_top_hi:                  4
;     tube_r1_status:                 4
;     brkv:                           3
;     hex_accumulator:                3
;     hex_accumulator_hi:             3
;     nmi_vector:                     3
;     osword_recv_block:              3
;     osword_send_block:              3
;     restore_regs_and_rti:           3
;     scan_hex_return:                3
;     transfer_addr_ptr:              3
;     tube_r1_data:                   3
;     tube_r3_status:                 3
;     brkv_hi:                        2
;     command_prompt:                 2
;     copy_rom_page:                  2
;     enter_code:                     2
;     error_buffer:                   2
;     error_buffer_errnum:            2
;     escape_flag:                    2
;     execute_code:                   2
;     io_page_base:                   2
;     last_error_hi:                  2
;     low_memory_code:                2
;     low_memory_startup_code:        2
;     osnewl_entry:                   2
;     osword_recv_bytes_loop:         2
;     osword_send_bytes_loop:         2
;     oswrch_impl:                    2
;     print_embedded_text:            2
;     rdline_recv_loop:               2
;     rdline_send_block_loop:         2
;     send_string:                    2
;     send_string_loop:               2
;     skip_spaces:                    2
;     skip_spaces_step:               2
;     transfer_read_loop:             2
;     transfer_write_loop:            2
;     unused_fill_page_ff:            2
;     wait_carry_and_byte:            2
;     zp_data_base:                   2
;     zp_data_base_1:                 2
;     zp_data_base_2:                 2
;     zp_data_base_3:                 2
;     argsv:                          1
;     bgetv:                          1
;     bputv:                          1
;     brk_handler_entry:              1
;     bytev:                          1
;     check_oscli_ack:                1
;     cliv:                           1
;     command_go:                     1
;     command_prompt_escape:          1
;     copy_io_page_loop:              1
;     copy_page_ff_loop:              1
;     copy_startup_code_loop:         1
;     copy_vectors_loop:              1
;     data_transfer_setup:            1
;     default_vector_table:           1
;     dispatch_event:                 1
;     error_not_6502_code:            1
;     error_not_a_language:           1
;     evntv:                          1
;     filev:                          1
;     findv:                          1
;     gbpbv:                          1
;     irq1v:                          1
;     irq2v:                          1
;     irq_return_addr_hi:             1
;     irq_return_addr_lo:             1
;     lfe03:                          1
;     lfe17:                          1
;     nmi0_done:                      1
;     nmi0_transfer_addr:             1
;     nmi1_done:                      1
;     nmi1_transfer_addr:             1
;     nmi2_done:                      1
;     nmi2_second_byte:               1
;     nmi3_done:                      1
;     nmi3_second_byte:               1
;     nmi_routine_addr_hi_table:      1
;     nmi_routine_addr_table:         1
;     nmi_vector_hi:                  1
;     osargs_wait_r2_handle:          1
;     osbyte_check_ack:               1
;     osbyte_entry:                   1
;     osbyte_high:                    1
;     osbyte_high_return:             1
;     osbyte_high_wait_carry:         1
;     osbyte_high_wait_r2_1:          1
;     osbyte_high_wait_r2_2:          1
;     osbyte_high_wait_r2_3:          1
;     osbyte_high_wait_r2_4:          1
;     osbyte_high_wait_x:             1
;     osbyte_high_wait_y:             1
;     osbyte_low_wait_r2_1:           1
;     osbyte_low_wait_r2_2:           1
;     osbyte_low_wait_r2_3:           1
;     osbyte_low_wait_result:         1
;     osbyte_read_high_word:          1
;     osbyte_read_himem:              1
;     osbyte_read_lomem:              1
;     oscli_entry:                    1
;     oscli_skip_stars_loop:          1
;     oscli_wait_ack:                 1
;     osfile_recv_block_loop:         1
;     osfile_send_block_loop:         1
;     osfind_open:                    1
;     osgbpb_recv_block_loop:         1
;     osgbpb_send_block_loop:         1
;     osrdch_impl:                    1
;     osword_entry:                   1
;     osword_recv_get_length:         1
;     osword_recv_lengths:            1
;     osword_recv_low_lookup:         1
;     osword_restore_regs:            1
;     osword_send_lengths:            1
;     osword_send_low_lookup:         1
;     osword_wait_r2_cmd:             1
;     osword_wait_r2_func:            1
;     print_error_done:               1
;     print_error_loop:               1
;     print_text_get_char:            1
;     print_text_loop:                1
;     print_text_resume:              1
;     rdchv:                          1
;     rdline:                         1
;     rdline_escape:                  1
;     rdline_send_addr_low:           1
;     reloc_low_memory_src:           1
;     scan_hex:                       1
;     scan_hex_got_digit:             1
;     scan_hex_next_char:             1
;     scan_hex_shift_loop:            1
;     send_string_via_ptr:            1
;     set_escape_flag:                1
;     soft_reset_jmp_hi:              1
;     soft_reset_jmp_lo:              1
;     startup_banner:                 1
;     transfer_256_bytes_from_tube:   1
;     transfer_addr_ptr_hi:           1
;     transfer_addr_ptr_hi_table:     1
;     transfer_addr_ptr_table:        1
;     transfer_read_addr1:            1
;     transfer_read_addr2:            1
;     transfer_read_addr3:            1
;     transfer_read_addr4:            1
;     transfer_wait_id:               1
;     transfer_wait_sync:             1
;     transfer_write_sync:            1
;     tube_r1_interrupt:              1
;     tube_r1_read_byte:              1
;     tube_r4_interrupt:              1
;     tube_r4_read_error_loop:        1
;     tube_r4_wait_error:             1
;     userv:                          1
;     wordv:                          1
;     wrchv:                          1

; Automatically generated labels:
;     lfe03
;     lfe17
;     sub_cfe15

; Stats:
;     Total size (Code + Data) = 2048 bytes
;     Code                     = 1604 bytes (78%)
;     Data                     = 444 bytes (22%)
;
;     Number of instructions   = 784
;     Number of data bytes     = 287 bytes
;     Number of data words     = 62 bytes
;     Number of string bytes   = 95 bytes
;     Number of strings        = 6
