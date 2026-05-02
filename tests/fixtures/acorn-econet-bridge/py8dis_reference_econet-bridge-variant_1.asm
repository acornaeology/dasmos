; Memory locations
st_ptr_lo       = &0000  ; Low byte of the self-test scan pointer. Paired with st_ptr_hi to form a 16-bit indirect pointer walked by self_test_rom_checksum and self_test_ram_pattern.
st_ptr_hi       = &0001  ; High byte of the self-test scan pointer. Paired with st_ptr_lo; incremented page by page as the scanning loops stride through each 256-byte block of ROM or RAM.
st_page_count   = &0002  ; Page counter for the self-test scans. Pre-loaded with a hard-coded &20 (32 pages = 8 KiB) at every site and decremented once per page by self_test_rom_checksum, self_test_ram_pattern, and both phases of self_test_ram_incr. The self-test therefore always covers exactly the low 8 KiB of RAM (&0000-&1FFF) and the 8 KiB ROM (&E000-&FFFF), regardless of what the boot-time ram_test found: this counter is never loaded from top_ram_page.
st_pass_phase   = &0003  ; Self-test pass-phase flag. Initialised by self_test at entry and toggled by self_test_pass_done at the end of each full pass; bit 7 then selects between a plain restart from self_test_reset_adlcs and the alternate path through self_test_alt_pass, which drives the ADLC control registers slightly differently to catch intermittent faults.
mem_ptr_lo      = &0080  ; Low byte of the indirect pointer. Paired with mem_ptr_hi.
mem_ptr_hi      = &0081  ; High byte of the indirect pointer. Paired with mem_ptr_lo.
top_ram_page    = &0082  ; Highest page that verified &AA/&55 during ram_test. Used later by workspace initialisation to decide how much RAM is safe to touch.
tx_end_lo       = &0200  ; Low byte of the TX end-pointer, consumed by transmit_frame_a. The TX loop sends byte pairs from mem_ptr_lo upward and terminates once the index reaches or passes this pointer.
tx_end_hi       = &0201  ; High byte of the TX end-pointer. Paired with tx_end_lo.
ctr24_lo        = &0214  ; Low byte of a 24-bit counter reused by several routines. wait_adlc_a_idle uses all three bytes as a timeout; stagger_delay uses this low byte alone as an 8-bit delay.
ctr24_mid       = &0215  ; Middle byte of the 24-bit counter. Rooted at ctr24_lo.
ctr24_hi        = &0216  ; High byte of the 24-bit counter. Rooted at ctr24_lo.
rx_len          = &0228  ; Byte count received into the RX frame buffer. Written by the drain loop once the ADLC reports end-of-frame; read back by the dispatch paths to decide how many payload bytes to process.
announce_flag   = &0229  ; Event-driven re-announcement selector.
announce_tmr_lo = &022a  ; Low byte of the 16-bit re-announcement countdown. Decremented every pass through main_loop_idle; fires re_announce when it reaches zero.
announce_tmr_hi = &022b  ; High byte of the 16-bit re-announcement countdown. Paired with announce_tmr_lo.
announce_count  = &022c  ; Remaining BridgeReply frames to emit in the current re-announcement burst. Initialised to 10 when a peer BridgeReset is heard, decremented in re_announce, and clears announce_flag on reaching zero.
rx_dst_stn      = &023c  ; RX frame buffer byte 0 – destination station number. First byte of the 20-byte RX staging area at &023C-&024F filled by rx_frame_a / rx_frame_b.
rx_dst_net      = &023d  ; RX frame buffer byte 1 – destination network number.
rx_src_stn      = &023e  ; RX frame buffer byte 2 – source station number.
rx_src_net      = &023f  ; RX frame buffer byte 3 – source network number.
rx_ctrl         = &0240  ; RX frame buffer byte 4 – control byte. Bridge protocol uses &80..&83; see rx_frame_a_dispatch.
rx_port         = &0241  ; RX frame buffer byte 5 – port number. The bridge-protocol port is &9C.
rx_query_port   = &0248  ; RX frame buffer byte 12 – port on which the querier wants the bridge to send its response.
rx_query_net    = &0249  ; RX frame buffer byte 13 – network number that a ctrl=&83 (IsNet) query is asking about. Checked against reachable_via_b / reachable_via_a in the query handlers.
reachable_via_b = &025a  ; 256-byte routing table for forwarding out of side B. Indexed by destination network number; a non-zero entry means "this network is reachable from here".
reachable_via_a = &035a  ; 256-byte routing table for forwarding out of side A. Indexed by destination network number; a non-zero entry means "this network is reachable from here".
tx_dst_stn      = &045a  ; TX frame buffer byte 0 – destination station number. First byte of the outbound frame staging area at &045A-&0460+, populated by the frame-builder subroutines and consumed by transmit_frame_a / transmit_frame_b.
tx_dst_net      = &045b  ; TX frame buffer byte 1 – destination network number.
tx_src_stn      = &045c  ; TX frame buffer byte 2 – source station number.
tx_src_net      = &045d  ; TX frame buffer byte 3 – source network number.
tx_ctrl         = &045e  ; TX frame buffer byte 4 – control byte in a scout frame, or the first data byte in a data frame. The same buffer serves both frame types; the caller chooses the semantics.
tx_port         = &045f  ; TX frame buffer byte 5 – port in a scout frame, or the second data byte in a data frame. Pair with tx_ctrl.
tx_data0        = &0460  ; TX frame buffer byte 6 – first optional scout payload byte. For example, a queried network number in a WhatNet response.
net_num_a       = &c000  ; Econet side A network number, read at &C000. Sourced from a bank of jumpered links buffered by a 74LS244. 7-bit (range 1-127); the top link is always made, so bit 7 reads 0.
adlc_a_cr1      = &c800  ; ADLC A control/status port 0.
adlc_a_cr2      = &c801  ; ADLC A control/status port 1.
adlc_a_tx       = &c802  ; ADLC A TX/RX FIFO port.
adlc_a_tx2      = &c803  ; ADLC A TX-last-byte port. Write: push the final byte of a frame (chip closes the frame and appends the FCS + flag). Reading this port is not used by the Bridge.
net_num_b       = &d000  ; Econet side B network number, read at &D000. Sourced from a bank of jumpered links buffered by a 74LS244. 7-bit (range 1-127); the top link is always made, so bit 7 reads 0.
adlc_b_cr1      = &d800  ; ADLC B control/status port 0.
adlc_b_cr2      = &d801  ; ADLC B control/status port 1.
adlc_b_tx       = &d802  ; ADLC B TX/RX FIFO port.
adlc_b_tx2      = &d803  ; ADLC B TX-last-byte port. Write: push the final byte of a frame (chip closes the frame and appends the FCS + flag). Reading this port is not used by the Bridge.

    org &e000

; &e000 referenced 7 times by &f2a9, &f2ac, &f2af, &f2b2, &f2b5, &f2b8, &f2bb
.pydis_start
.reset
    cli                                                               ; e000: 58          X              ; Enable IRQs (self-test button wired to ~IRQ)
    cld                                                               ; e001: d8          .              ; Clear decimal mode (6502 arithmetic in binary)
    jsr init_reachable_nets                                           ; e002: 20 24 e4     $.            ; Initialise reachable_via_a/b tables for routing
    jsr adlc_a_full_reset                                             ; e005: 20 f0 e3     ..            ; Reset ADLC A through its full CR1/CR2/CR3/CR4 sequence
    jsr adlc_b_full_reset                                             ; e008: 20 0a e4     ..            ; Reset ADLC B through its full CR1/CR2/CR3/CR4 sequence
; ***************************************************************************************
; Scan pages from &1800 upward; record top of RAM
;
; Probes pages upward from &1800 by writing &AA and &55 patterns through
; mem_ptr_lo/mem_ptr_hi (&80/&81) and verifying each. The highest page that verifies is
; stored in top_ram_page (&82), used downstream by workspace initialisation. The Bridge
; can be built with either one 8 KiB 6264 chip or four 2 KiB 6116 chips (chosen by
; soldered links), so RAM size must be discovered at power-on.
;
; The routine looks like a textbook two-pattern memory test but is considerably more
; robust than a naive STA/LDA/CMP would be. Three independent mechanisms have to fail
; simultaneously for it to report RAM where none exists:
;
; 1. The INC on zero-page &00 between each write and its matching read is an
;    anti-bus-residue defence. When the 6502 writes to an unmapped address, no chip
;    latches the value, but the data-bus capacitance can hold the written byte long
;    enough for the subsequent LDA to sample its own ghost. INC $00 is a
;    read-modify-write that drives the data bus three times with values unrelated to
;    the test pattern (the cycle-4 dummy write is a classic NMOS 6502 quirk that is
;    exploited here), clobbering any residue of &AA or &55.
; 2. The choice of &00 specifically is an alias tripwire. If the address decoder is
;    miswired and the target address aliases into zero page, the obvious alias landing
;    point is &00 – so disturbing &00 between write and read forces any alias-based
;    false-positive to fail the CMP.
; 3. The two patterns &AA and &55 are bitwise complements: a stuck bit is detected on
;    whichever pattern it contradicts, and a single-value bus residue cannot spoof both
;    checks simultaneously.
;
; See docs/analysis/ram-test-anti-aliasing.md for the full cycle-level analysis.
.ram_test
    ldy #0                                                            ; e00b: a0 00       ..             ; Y = 0: ZP offset used by (mem_ptr_lo),Y throughout
    sty mem_ptr_lo                                                    ; e00d: 84 80       ..             ; Clear mem_ptr_lo so every probe is page-aligned
    lda #&17                                                          ; e00f: a9 17       ..             ; A = &17: seed for mem_ptr_hi (first probe will be page &18)
    sta mem_ptr_hi                                                    ; e011: 85 81       ..             ; Commit mem_ptr_hi; first INC at loop head advances to &18
; &e013 referenced 1 time by &e02b
.ram_test_loop
    inc mem_ptr_hi                                                    ; e013: e6 81       ..             ; Step up to the next candidate page
    lda #&aa                                                          ; e015: a9 aa       ..             ; Pattern 1: &AA (1010_1010) – half the bits set
    sta (mem_ptr_lo),y                                                ; e017: 91 80       ..             ; Write &AA to (mem_ptr_lo) indirect
    inc st_ptr_lo                                                     ; e019: e6 00       ..             ; INC $00: read-modify-write disturbs the data bus…
    lda (mem_ptr_lo),y                                                ; e01b: b1 80       ..             ; …then read the probe byte back
    cmp #&aa                                                          ; e01d: c9 aa       ..             ; Did &AA survive the disturbance?
    bne ram_test_done                                                 ; e01f: d0 0c       ..             ; Mismatch → this page isn't real RAM; back off
    lda #&55 ; 'U'                                                    ; e021: a9 55       .U             ; Pattern 2: &55 (0101_0101) – exact complement of &AA
    sta (mem_ptr_lo),y                                                ; e023: 91 80       ..             ; Write &55 to (mem_ptr_lo) indirect
    inc st_ptr_lo                                                     ; e025: e6 00       ..             ; INC $00 again – anti-aliasing tripwire
    lda (mem_ptr_lo),y                                                ; e027: b1 80       ..             ; Read pattern 2 back
    cmp #&55 ; 'U'                                                    ; e029: c9 55       .U             ; Did &55 survive?
    beq ram_test_loop                                                 ; e02b: f0 e6       ..             ; Both patterns held – real RAM, try next page
; &e02d referenced 1 time by &e01f
.ram_test_done
    dec mem_ptr_hi                                                    ; e02d: c6 81       ..             ; Step back one: last-probed page failed, prior page was OK
    lda mem_ptr_hi                                                    ; e02f: a5 81       ..             ; Read the highest-verified page number
    sta top_ram_page                                                  ; e031: 85 82       ..             ; Save as top_ram_page; workspace init caps buffers here
; ***************************************************************************************
; Emit the boot-time BridgeReset pair on both Econet sides
;
; Second half of the reset handler. Clears announce_flag so the idle-path re-announcer
; starts quiescent, then builds a single BridgeReset template (ctrl=&80, port=&9C,
; payload=net_num_b) via build_announce_b and transmits it twice: first on side A with
; net_num_b in the payload, then on side B after patching the payload to net_num_a. The
; two wait_adlc_a_idle / wait_adlc_b_idle calls gate each transmit on carrier-sense;
; either can escape to main_loop if the line never goes idle.
;
; Falls through to main_loop on success. A clean reset therefore emits exactly two
; frames before steady-state polling begins. See
; docs/analysis/two-broadcasts-one-template.md for why one template suffices.
.reset_announce_broadcasts
    lda #0                                                            ; e033: a9 00       ..             ; A = 0: clear announce_flag (idle path stays quiet initially)
    sta announce_flag                                                 ; e035: 8d 29 02    .).            ; Commit announce_flag = 0 to workspace
    jsr build_announce_b                                              ; e038: 20 58 e4     X.            ; Build the BridgeReset scout template into &045A-&0460
    jsr wait_adlc_a_idle                                              ; e03b: 20 dc e6     ..            ; CSMA: wait for side A's line to go idle
    jsr transmit_frame_a                                              ; e03e: 20 17 e5     ..            ; Transmit first broadcast (announcing net_num_b to side A)
    lda net_num_a                                                     ; e041: ad 00 c0    ...            ; Load net_num_a – the payload byte for the B-side broadcast
    sta tx_data0                                                      ; e044: 8d 60 04    .`.            ; Patch payload byte 0 of the template in-place
    lda #4                                                            ; e047: a9 04       ..             ; A = &04: reset mem_ptr_hi to the template's base page…
    sta mem_ptr_hi                                                    ; e049: 85 81       ..             ; …so transmit_frame_b re-reads from &045A
    jsr wait_adlc_b_idle                                              ; e04b: 20 90 e6     ..            ; CSMA: wait for side B's line to go idle
    jsr transmit_frame_b                                              ; e04e: 20 c0 e4     ..            ; Transmit second broadcast (announcing net_num_a to side B)
; ***************************************************************************************
; Main Bridge loop: re-arm ADLCs, poll for frames, re-announce
;
; The Bridge's continuous-operation entry point. Reached by fall- through from the
; reset handler once startup completes, and by JMP from fourteen other sites – every
; routine that takes an "escape to main" path (wait_adlc_a_idle,
; transmit_frame_a/transmit_frame_b, etc.) lands here, so main_loop is the anchor of
; every packet-processing cycle.
;
; The header (&E051-&E078) forces each ADLC into a known RX-listening state: if SR2 bit
; 0 or 7 (AP or RDA) is already set from a partial or aborted previous operation, CR1
; is cycled through &C2 (reset TX, leave RX running) before setting it to &82 (TX in
; reset, RX IRQs enabled). CR2 is set to &67 – the standard listen-mode value used
; throughout the firmware.
;
; The inner poll loop at main_loop_poll (&E079) tests SR1 bit 7 (IRQ summary) on each
; ADLC in turn, with side B checked first. If either chip has a pending IRQ, control
; jumps straight to the corresponding frame handler; otherwise the idle path at
; main_loop_idle (&E089) runs the periodic re-announcement.
;
; The re-announce scheme uses three bytes of workspace:
;
; | byte               | role                                                                                                                                 |
; |--------------------|--------------------------------------------------------------------------------------------------------------------------------------|
; | announce_flag      | enables re-announce; bit 7 additionally selects which side the re-announce goes out on                                               |
; | announce_tmr_lo/hi | 16-bit countdown, decremented every idle-path iteration; zero triggers the re-announce                                               |
; | announce_count     | remaining re-announce cycles; when this hits zero, announce_flag is cleared and re-announce stops until something else re-enables it |
;
; The re-announce path (re_announce) rebuilds the announcement frame, sets tx_ctrl to
; &81 (distinguishing it from the reset-time &80 first announcement), then dispatches
; to side A or side B based on announce_flag bit 7. The timer is re-armed to &8000
; (32768 idle iterations) after each announce, giving a roughly constant cadence
; regardless of how busy the ADLCs are with other traffic.
; &e051 referenced 14 times by &e0bf, &e0c7, &e13c, &e1d3, &e260, &e2bd, &e354, &e3e1, &e4d6, &e52d, &e5b3, &e644, &e6d0, &e71c
.main_loop
    lda adlc_a_cr2                                                    ; e051: ad 01 c8    ...            ; Read ADLC A's SR2
    and #&81                                                          ; e054: 29 81       ).             ; Mask AP/RDA bits to test for any stale RX state
    beq main_loop_arm_a                                               ; e056: f0 05       ..             ; Clean → skip the TX reset
    lda #&c2                                                          ; e058: a9 c2       ..             ; Mask: reset TX, leave RX running
    sta adlc_a_cr1                                                    ; e05a: 8d 00 c8    ...            ; Clear any stale TX state on ADLC A
; &e05d referenced 1 time by &e056
.main_loop_arm_a
    ldx #&82                                                          ; e05d: a2 82       ..             ; X = &82: listen-mode CR1 (TX reset, RX IRQ)
    stx adlc_a_cr1                                                    ; e05f: 8e 00 c8    ...            ; Commit CR1 on ADLC A
    ldy #&67 ; 'g'                                                    ; e062: a0 67       .g             ; Y = &67: listen-mode CR2 (status-clear pattern)
    sty adlc_a_cr2                                                    ; e064: 8c 01 c8    ...            ; Commit CR2 on ADLC A
    lda adlc_b_cr2                                                    ; e067: ad 01 d8    ...            ; Read ADLC B's SR2
    and #&81                                                          ; e06a: 29 81       ).             ; Mask AP/RDA to test for any stale RX state
    beq main_loop_arm_b                                               ; e06c: f0 05       ..             ; Clean → skip the TX reset on B
    lda #&c2                                                          ; e06e: a9 c2       ..             ; Mask: reset TX, leave RX running
    sta adlc_b_cr1                                                    ; e070: 8d 00 d8    ...            ; Clear any stale TX state on ADLC B
; &e073 referenced 1 time by &e06c
.main_loop_arm_b
    stx adlc_b_cr1                                                    ; e073: 8e 00 d8    ...            ; Commit CR1 on ADLC B (X still = &82)
    sty adlc_b_cr2                                                    ; e076: 8c 01 d8    ...            ; Commit CR2 on ADLC B (Y still = &67)
; &e079 referenced 5 times by &e08c, &e091, &e096, &e144, &e2c5
.main_loop_poll
    bit adlc_b_cr1                                                    ; e079: 2c 00 d8    ,..            ; BIT ADLC B's SR1 – N ← bit 7 (IRQ summary)
    bpl main_loop_poll_a                                              ; e07c: 10 03       ..             ; B quiet → check A
    jmp rx_frame_b                                                    ; e07e: 4c 63 e2    Lc.            ; B has an event → dispatch to rx_frame_b

; &e081 referenced 1 time by &e07c
.main_loop_poll_a
    bit adlc_a_cr1                                                    ; e081: 2c 00 c8    ,..            ; BIT ADLC A's SR1 – N ← bit 7 (IRQ summary)
    bpl main_loop_idle                                                ; e084: 10 03       ..             ; A quiet → nothing to do; maybe re-announce
    jmp rx_frame_a                                                    ; e086: 4c e2 e0    L..            ; A has an event → dispatch to rx_frame_a

; &e089 referenced 1 time by &e084
.main_loop_idle
    lda announce_flag                                                 ; e089: ad 29 02    .).            ; Read announce_flag – is a re-announce burst pending?
    beq main_loop_poll                                                ; e08c: f0 eb       ..             ; No burst in progress → straight back to polling
    dec announce_tmr_lo                                               ; e08e: ce 2a 02    .*.            ; Tick the 16-bit re-announce countdown, low byte
    bne main_loop_poll                                                ; e091: d0 e6       ..             ; Low byte didn't wrap → keep polling
    dec announce_tmr_hi                                               ; e093: ce 2b 02    .+.            ; Low byte wrapped → tick the high byte too
    bne main_loop_poll                                                ; e096: d0 e1       ..             ; Timer hasn't expired yet → keep polling
; ***************************************************************************************
; Emit one BridgeReply in an in-progress response burst
;
; Reached from main_loop_idle once the 16-bit announce_tmr has ticked down to zero and
; announce_flag is non-zero. Both conditions are only met after rx_a_handle_80 or
; rx_b_handle_80 has set the flag in response to a BridgeReset received from another
; bridge. This routine is the per-tick action of that response burst – it is not a
; self-scheduled periodic announcement.
;
; Rebuilds the outbound template via build_announce_b and patches tx_ctrl from &80 (the
; BridgeReset value the builder writes) to &81 (BridgeReply), distinguishing the
; follow-up announcements from the initial one that triggered the burst.
;
; Which side to transmit on is selected by announce_flag bit 7:
;
; | announce_flag bit 7 | side   | notes                                                                        |
; |---------------------|--------|------------------------------------------------------------------------------|
; | clear (1..&7F)      | ADLC A | transmit directly                                                            |
; | set (&80..&FF)      | ADLC B | patch tx_data0 with net_num_a first, mirroring the reset-time dual-broadcast |
;
; Each invocation decrements announce_count. When it hits zero, announce_flag is
; cleared (re_announce_done); the burst is complete and the idle path goes quiet until
; another BridgeReset arrives. Otherwise the timer is re-armed to &8000 and control
; returns to main_loop (re_announce_rearm).
;
; Before transmitting on one side, the routine resets the other ADLC's TX path (CR1 =
; &C2) to prevent the opposite side from inadvertently transmitting a colliding frame
; while we're busy.
.re_announce
    jsr build_announce_b                                              ; e098: 20 58 e4     X.            ; Rebuild the frame template from scratch (ctrl=&80 default)
    lda #&81                                                          ; e09b: a9 81       ..             ; A = &81: the BridgeReply control byte
    sta tx_ctrl                                                       ; e09d: 8d 5e 04    .^.            ; Patch tx_ctrl to &81 – this announcement is a reply
    bit announce_flag                                                 ; e0a0: 2c 29 02    ,).            ; Test announce_flag bit 7 via BIT
    bmi re_announce_side_b                                            ; e0a3: 30 25       0%             ; Bit 7 set → send via ADLC B (re_announce_side_b)
    lda #&c2                                                          ; e0a5: a9 c2       ..             ; Side-A path: silence B's TX first
    sta adlc_b_cr1                                                    ; e0a7: 8d 00 d8    ...            ; Reset ADLC B's TX to avoid a cross-side collision
    jsr wait_adlc_a_idle                                              ; e0aa: 20 dc e6     ..            ; CSMA wait on A before transmitting
    jsr transmit_frame_a                                              ; e0ad: 20 17 e5     ..            ; Send the BridgeReply on ADLC A
    dec announce_count                                                ; e0b0: ce 2c 02    .,.            ; Decrement burst-remaining count
    beq re_announce_done                                              ; e0b3: f0 0d       ..             ; Count hit zero → clear announce_flag
; &e0b5 referenced 1 time by &e0e0
.re_announce_rearm
    lda #&80                                                          ; e0b5: a9 80       ..             ; A = &80: reseed timer high byte
    sta announce_tmr_hi                                               ; e0b7: 8d 2b 02    .+.            ; Store new timer_hi
    lda #0                                                            ; e0ba: a9 00       ..             ; A = 0: timer low byte
    sta announce_tmr_lo                                               ; e0bc: 8d 2a 02    .*.            ; Store timer_lo; next firing in ~&8000 idle iterations
    jmp main_loop                                                     ; e0bf: 4c 51 e0    LQ.            ; Continue the main loop

; &e0c2 referenced 2 times by &e0b3, &e0de
.re_announce_done
    lda #0                                                            ; e0c2: a9 00       ..             ; A = 0: 'burst complete' marker
    sta announce_flag                                                 ; e0c4: 8d 29 02    .).            ; Clear announce_flag; re-announce stops until next BridgeReset
    jmp main_loop                                                     ; e0c7: 4c 51 e0    LQ.            ; Continue the main loop

; &e0ca referenced 1 time by &e0a3
.re_announce_side_b
    lda net_num_a                                                     ; e0ca: ad 00 c0    ...            ; Fetch our side-A network number
    sta tx_data0                                                      ; e0cd: 8d 60 04    .`.            ; Patch tx_data0: this frame announces net_num_a to side B
    lda #&c2                                                          ; e0d0: a9 c2       ..             ; Mask: reset TX, RX going
    sta adlc_a_cr1                                                    ; e0d2: 8d 00 c8    ...            ; Silence ADLC A's TX to avoid collision while we send on B
    jsr wait_adlc_b_idle                                              ; e0d5: 20 90 e6     ..            ; CSMA wait on B
    jsr transmit_frame_b                                              ; e0d8: 20 c0 e4     ..            ; Send the BridgeReply on ADLC B
    dec announce_count                                                ; e0db: ce 2c 02    .,.            ; Decrement burst-remaining count
    beq re_announce_done                                              ; e0de: f0 e2       ..             ; Count hit zero → clear announce_flag
    bne re_announce_rearm                                             ; e0e0: d0 d3       ..             ; Not exhausted → re-arm timer and continue (ALWAYS branch)

; ***************************************************************************************
; Drain and dispatch an inbound frame on ADLC A
;
; Reached from main_loop_poll when ADLC A raises SR1 bit 7. Drains the incoming scout
; frame from the RX FIFO into the rx_* buffer at &023C-&024F, runs two levels of
; filtering, and then dispatches on the control byte to per-message handlers.
;
; 1. Addressing filter. Expect SR2 bit 0 (AP: Address Present) – if missing, bail to
;    main_loop (spurious IRQ). Read byte 0 (rx_dst_stn) and byte 1 (rx_dst_net). If
;    rx_dst_net is zero (local net) or reachable_via_b[rx_dst_net] is zero (unknown
;    network), jump to rx_a_not_for_us (&E13F): ignore the frame, re-listen, drop back
;    to main_loop_poll without a full main_loop re-init.
; 2. Drain. Read the rest of the frame in byte-pairs into &023C+Y up to Y=20 (the
;    Bridge only keeps the first 20 bytes). After the drain, force CR1=0 and CR2=&84 to
;    halt the chip and test SR2 bit 1 (FV, Frame Valid). If FV is clear, the frame was
;    corrupt or short – bail to main_loop. If SR2 bit 7 (RDA) is also set, read one
;    trailing byte.
; 3. Broadcast check. Only frames with dst_stn == dst_net == &FF (full broadcast)
;    proceed to the bridge-protocol dispatcher. Everything else falls to rx_a_forward
;    (&E208), the cross-network forwarding path.
; 4. Dispatch on rx_ctrl (after verifying rx_port == &9C, the bridge-protocol port):
;
;    | ctrl  | handler        | role                        |
;    |-------|----------------|-----------------------------|
;    | &80   | rx_a_handle_80 | initial bridge announcement |
;    | &81   | rx_a_handle_81 | re-announcement             |
;    | &82   | rx_a_handle_82 | bridge query (tentative)    |
;    | &83   | rx_a_handle_83 | bridge query, known-station |
;    | other | rx_a_forward   | forward or discard          |
;
; The side-B handler rx_frame_b (&E263) is the mirror of this routine.
; &e0e2 referenced 1 time by &e086
.rx_frame_a
    lda #1                                                            ; e0e2: a9 01       ..             ; A = &01: mask SR2 bit 0 (AP = Address Present)
    bit adlc_a_cr2                                                    ; e0e4: 2c 01 c8    ,..            ; BIT SR2 – confirm the IRQ was a frame start
    beq rx_frame_a_bail                                               ; e0e7: f0 53       .S             ; AP not set → spurious IRQ, return to main_loop
    lda adlc_a_tx                                                     ; e0e9: ad 02 c8    ...            ; Read FIFO byte 0: destination station
    sta rx_dst_stn                                                    ; e0ec: 8d 3c 02    .<.            ; Stage dst_stn into the rx header buffer
    jsr wait_adlc_a_irq                                               ; e0ef: 20 e4 e3     ..            ; Block until ADLC A IRQs again (byte 1 ready)
    bit adlc_a_cr2                                                    ; e0f2: 2c 01 c8    ,..            ; BIT SR2 – RDA still set for the next byte?
    bpl rx_frame_a_bail                                               ; e0f5: 10 45       .E             ; RDA cleared: frame truncated before dst_net, bail
    ldy adlc_a_tx                                                     ; e0f7: ac 02 c8    ...            ; Read byte 1 into Y: destination network
    beq rx_a_not_for_us                                               ; e0fa: f0 43       .C             ; dst_net == 0 means 'local net of sender' – not for us
    lda reachable_via_b,y                                             ; e0fc: b9 5a 02    .Z.            ; Probe reachable_via_b[dst_net] for a route via side B
    beq rx_a_not_for_us                                               ; e0ff: f0 3e       .>             ; No route → frame isn't ours to drain, re-listen
    sty rx_dst_net                                                    ; e101: 8c 3d 02    .=.            ; Commit dst_net now that it has passed filtering
    ldy #2                                                            ; e104: a0 02       ..             ; Y = 2: resume drain at offset 2 (after header)
; &e106 referenced 1 time by &e11e
.rx_frame_a_drain
    jsr wait_adlc_a_irq                                               ; e106: 20 e4 e3     ..            ; Wait for the next FIFO byte IRQ
    bit adlc_a_cr2                                                    ; e109: 2c 01 c8    ,..            ; BIT SR2 – RDA still asserted?
    bpl rx_frame_a_end                                                ; e10c: 10 12       ..             ; RDA cleared mid-body → go to FV check
    lda adlc_a_tx                                                     ; e10e: ad 02 c8    ...            ; Read byte Y of payload from TX/RX FIFO
    sta rx_dst_stn,y                                                  ; e111: 99 3c 02    .<.            ; Store into rx_dst_stn+Y (buffer grows into rx_*)
    iny                                                               ; e114: c8          .              ; Advance Y to the next slot
    lda adlc_a_tx                                                     ; e115: ad 02 c8    ...            ; Read byte Y+1 (pair-read without an IRQ wait)
    sta rx_dst_stn,y                                                  ; e118: 99 3c 02    .<.            ; Store the second byte of the pair
    iny                                                               ; e11b: c8          .              ; Advance Y past the pair
    cpy #&14                                                          ; e11c: c0 14       ..             ; Cap at 20 bytes (6-byte header + up to 14 payload)
    bcc rx_frame_a_drain                                              ; e11e: 90 e6       ..             ; Under cap → keep draining
; &e120 referenced 1 time by &e10c
.rx_frame_a_end
    lda #0                                                            ; e120: a9 00       ..             ; A = &00: halt ADLC A
    sta adlc_a_cr1                                                    ; e122: 8d 00 c8    ...            ; CR1 = 0: disable TX and RX IRQs
    lda #&84                                                          ; e125: a9 84       ..             ; A = &84: clear-RX-status + FV-clear bits
    sta adlc_a_cr2                                                    ; e127: 8d 01 c8    ...            ; Commit CR2: acknowledge end-of-frame
    lda #2                                                            ; e12a: a9 02       ..             ; A = &02: mask SR2 bit 1 (FV: Frame Valid)
    bit adlc_a_cr2                                                    ; e12c: 2c 01 c8    ,..            ; BIT SR2 – test FV and RDA
    beq rx_frame_a_bail                                               ; e12f: f0 0b       ..             ; FV clear → frame corrupt or short, bail
    bpl rx_frame_a_dispatch                                           ; e131: 10 17       ..             ; FV set + no RDA → clean end; go to dispatch
    lda adlc_a_tx                                                     ; e133: ad 02 c8    ...            ; FV + RDA: one trailing byte still in FIFO
    sta rx_dst_stn,y                                                  ; e136: 99 3c 02    .<.            ; Store the odd trailing byte
    iny                                                               ; e139: c8          .              ; Advance Y to count that final byte
    bne rx_frame_a_dispatch                                           ; e13a: d0 0e       ..             ; Unconditional: continue to dispatch
; &e13c referenced 4 times by &e0e7, &e0f5, &e12f, &e14f
.rx_frame_a_bail
    jmp main_loop                                                     ; e13c: 4c 51 e0    LQ.            ; Bail: restart from main_loop (full ADLC re-init)

; &e13f referenced 2 times by &e0fa, &e0ff
.rx_a_not_for_us
    lda #&a2                                                          ; e13f: a9 a2       ..             ; A = &A2: RX on, IRQ enabled, TX in reset
    sta adlc_a_cr1                                                    ; e141: 8d 00 c8    ...            ; Re-arm ADLC A to listen for the next frame
    jmp main_loop_poll                                                ; e144: 4c 79 e0    Ly.            ; Skip main_loop re-init; go straight back to polling

; &e147 referenced 2 times by &e171, &e180
.rx_a_to_forward
    jmp rx_a_forward                                                  ; e147: 4c 08 e2    L..            ; Out-of-range JMP to rx_a_forward (JSR can't reach)

; &e14a referenced 2 times by &e131, &e13a
.rx_frame_a_dispatch
    sty rx_len                                                        ; e14a: 8c 28 02    .(.            ; Save final byte count (even if 0 bytes of payload)
    cpy #6                                                            ; e14d: c0 06       ..             ; Compare to 6 – minimum valid scout header
    bcc rx_frame_a_bail                                               ; e14f: 90 eb       ..             ; Shorter than header → bail
    lda rx_src_net                                                    ; e151: ad 3f 02    .?.            ; Load src_net from the drained frame
    bne rx_a_src_net_resolved                                         ; e154: d0 06       ..             ; Non-zero → sender supplied src_net, keep it
    lda net_num_a                                                     ; e156: ad 00 c0    ...            ; Sender left src_net = 0 ('my local net')
    sta rx_src_net                                                    ; e159: 8d 3f 02    .?.            ; …substitute our own A-side network number
; &e15c referenced 1 time by &e154
.rx_a_src_net_resolved
    lda net_num_b                                                     ; e15c: ad 00 d0    ...            ; Load our B-side network number for comparison
    cmp rx_dst_net                                                    ; e15f: cd 3d 02    .=.            ; Compare against the incoming dst_net
    bne rx_a_broadcast_check                                          ; e162: d0 05       ..             ; Not for side B → skip the local rewrite
    lda #0                                                            ; e164: a9 00       ..             ; dst_net names our B-side network…
    sta rx_dst_net                                                    ; e166: 8d 3d 02    .=.            ; …normalise dst_net to 0 (local on B)
; &e169 referenced 1 time by &e162
.rx_a_broadcast_check
    lda rx_dst_stn                                                    ; e169: ad 3c 02    .<.            ; Load dst_stn for the broadcast test
    and rx_dst_net                                                    ; e16c: 2d 3d 02    -=.            ; AND with dst_net (both &FF only if full broadcast)
    cmp #&ff                                                          ; e16f: c9 ff       ..             ; Compare result to &FF
    bne rx_a_to_forward                                               ; e171: d0 d4       ..             ; Not a full broadcast → forward path
    jsr adlc_a_listen                                                 ; e173: 20 ff e3     ..            ; Broadcast: re-arm A's listen mode for any follow-up
    lda #&c2                                                          ; e176: a9 c2       ..             ; A = &C2: reset TX, enable RX
    sta adlc_a_cr1                                                    ; e178: 8d 00 c8    ...            ; Commit CR1 while we process the bridge-protocol frame
    lda rx_port                                                       ; e17b: ad 41 02    .A.            ; Load the port byte from the drained frame
    cmp #&9c                                                          ; e17e: c9 9c       ..             ; Compare with &9C (bridge-protocol port)
    bne rx_a_to_forward                                               ; e180: d0 c5       ..             ; Not our port → drop into forward path
    lda rx_ctrl                                                       ; e182: ad 40 02    .@.            ; Load ctrl byte for the per-type dispatch
    cmp #&81                                                          ; e185: c9 81       ..             ; Test &81 (BridgeReply: re-announcement)
    beq rx_a_handle_81                                                ; e187: f0 65       .e             ; Match → rx_a_handle_81
    cmp #&80                                                          ; e189: c9 80       ..             ; Test &80 (BridgeReset: initial announcement)
    beq rx_a_handle_80                                                ; e18b: f0 49       .I             ; Match → rx_a_handle_80
    cmp #&82                                                          ; e18d: c9 82       ..             ; Test &82 (WhatNet: general query)
    beq rx_a_handle_82                                                ; e18f: f0 0c       ..             ; Match → rx_a_handle_82
    cmp #&83                                                          ; e191: c9 83       ..             ; Test &83 (IsNet: targeted query)
    bne rx_a_forward                                                  ; e193: d0 73       .s             ; Unknown ctrl → forward path (fall through to rx_a_handle_83 on match)
; ***************************************************************************************
; Side-A IsNet query (ctrl=&83): targeted network lookup
;
; Called when a received frame on side A is broadcast + port=&9C + ctrl=&83 – the
; querier is asking "can you reach network X?", where X is the byte at offset 13 of the
; payload (rx_query_net).
;
; Consults reachable_via_b[rx_query_net]. If the entry is zero, there is no route to
; that network so the query is silently dropped (JMP main_loop via rx_a_query_done). If
; non-zero, falls through to the shared response body at rx_a_handle_82 to transmit the
; reply – so the targeted query is effectively the general query with an up-front
; routing filter.
.rx_a_handle_83
    ldy rx_query_net                                                  ; e195: ac 49 02    .I.            ; Y = the queried network number
    lda reachable_via_b,y                                             ; e198: b9 5a 02    .Z.            ; Check if we have a route via the other side
    beq rx_a_query_done                                               ; e19b: f0 36       .6             ; Unknown → silently drop this IsNet query
; ***************************************************************************************
; Side-A WhatNet query (ctrl=&82); also the IsNet response path
;
; Called when a received frame on side A is broadcast + port=&9C + ctrl=&82 – a general
; bridge query asking "which networks do you reach?" – or when rx_a_handle_83 has
; verified that a specific IsNet queried network is in fact reachable via side B and is
; re-using this response path.
;
; The response is a complete four-way handshake transaction, which the Bridge drives
; from the responder side as two transmissions (scout, then data) with an inbound ACK
; after each:
;
; 1. Build a reply-scout template via build_query_response, addressed back to the
;    querier on its local network with tx_src_net patched to our net_num_b.
; 2. Stagger the scout transmission via stagger_delay, seeded from net_num_b. Multiple
;    bridges on the same segment will all react to a broadcast query, and without the
;    stagger their responses would overlap on the wire; seeding from the network number
;    gives each bridge a deterministic but distinct delay.
; 3. CSMA, transmit the scout, then handshake_rx_a to receive the scout-ACK.
; 4. Rebuild the frame via build_query_response again – this time to be a data frame
;    following the scout we just exchanged, not a new scout. The patches that follow
;    populate the first two payload bytes of that data frame (at the byte positions
;    labelled tx_ctrl and tx_port, but those names refer to scout semantics; in a data
;    frame those slots are payload, not header):
;
;    | slot        | value        | meaning                     |
;    |-------------|--------------|-----------------------------|
;    | data byte 0 | net_num_a    | the Bridge's side-A network |
;    | data byte 1 | rx_query_net | echo of the queried network |
;
;    The answer thus consists of the dst/src quad plus two payload bytes, packed into
;    the smallest Econet frame that can carry it.
; 5. Transmit the data frame, then handshake_rx_a for the final data-ACK. JMP main_loop
;    on completion.
;
; Either handshake_rx_a call can escape to main_loop if the querier doesn't keep up the
; handshake, aborting the conversation cleanly.
; Re-arm A for listen after the received query
; &e19d referenced 1 time by &e18f
.rx_a_handle_82
    jsr adlc_a_listen                                                 ; e19d: 20 ff e3     ..            ; Re-arm ADLC A into listen mode before replying
    jsr build_query_response                                          ; e1a0: 20 8d e4     ..            ; Build reply-scout template addressed at the querier
    lda net_num_b                                                     ; e1a3: ad 00 d0    ...            ; Fetch our side-B network number
    sta tx_src_net                                                    ; e1a6: 8d 5d 04    .].            ; Patch src_net so the scout names us by net_num_b
    sta ctr24_lo                                                      ; e1a9: 8d 14 02    ...            ; Copy it into the stagger-delay counter too
    jsr stagger_delay                                                 ; e1ac: 20 48 e4     H.            ; Busy-wait for (net_num_b * ~50us) + 160us
    jsr wait_adlc_a_idle                                              ; e1af: 20 dc e6     ..            ; CSMA wait on A so we don't collide with live traffic
    jsr transmit_frame_a                                              ; e1b2: 20 17 e5     ..            ; Transmit the reply scout
    jsr handshake_rx_a                                                ; e1b5: 20 6e e5     n.            ; Wait for the querier's scout-ACK on A
    jsr build_query_response                                          ; e1b8: 20 8d e4     ..            ; Rebuild template – next frame is the data response
    lda net_num_b                                                     ; e1bb: ad 00 d0    ...            ; Fetch net_num_b
    sta tx_src_net                                                    ; e1be: 8d 5d 04    .].            ; Re-patch src_net (rebuilt block needs it again)
    lda net_num_a                                                     ; e1c1: ad 00 c0    ...            ; Fetch net_num_a
    sta tx_ctrl                                                       ; e1c4: 8d 5e 04    .^.            ; Write it as data-frame payload byte 0 (tx_ctrl slot)
    lda rx_query_net                                                  ; e1c7: ad 49 02    .I.            ; Fetch the network the querier asked about
    sta tx_port                                                       ; e1ca: 8d 5f 04    ._.            ; Write it as data-frame payload byte 1 (tx_port slot)
    jsr transmit_frame_a                                              ; e1cd: 20 17 e5     ..            ; Transmit the data frame
    jsr handshake_rx_a                                                ; e1d0: 20 6e e5     n.            ; Wait for the querier's final data-ACK
; &e1d3 referenced 1 time by &e19b
.rx_a_query_done
    jmp main_loop                                                     ; e1d3: 4c 51 e0    LQ.            ; Transaction complete → back to main_loop

; ***************************************************************************************
; Side-A BridgeReset (ctrl=&80): learn topology from scratch
;
; Called when a received frame on side A is broadcast + port=&9C + ctrl=&80 – a bridge
; on the far side is advertising a fresh topology, likely because it has itself just
; come up. The handler:
;
; 1. Wipe all learned routing state via init_reachable_nets. The topology may have
;    changed non-monotonically, so accumulated reachable_via_? entries are suspect and
;    the safe move is to discard them and relearn.
; 2. Schedule a burst of our own re-announcements: ten cycles with a staggered initial
;    timer value seeded from net_num_b. Using the local network number as the timer's
;    phase means bridges on different segments aren't all re-announcing at the same
;    millisecond. announce_flag is set to &40 (enable, bit 7 clear = next outbound on
;    side A).
; 3. Fall through to rx_a_handle_81 (the same payload-processing loop runs for both
;    BridgeReset and BridgeReply) to mark the sender's known networks as
;    reachable-via-A.
;
; This is one of only two places in the ROM that sets announce_flag non-zero (the other
; is the mirror rx_b_handle_80). Receiving a BridgeReply (ctrl=&81) does not trigger
; the burst; only receiving a BridgeReset does. A solo bridge therefore stays silent
; after its boot-time BridgeReset pair, because nothing comes back to trigger a
; response. See docs/analysis/event-driven-reannouncement.md.
; &e1d6 referenced 1 time by &e18b
.rx_a_handle_80
    jsr init_reachable_nets                                           ; e1d6: 20 24 e4     $.            ; Wipe all learned routing state (topology reset)
    lda net_num_b                                                     ; e1d9: ad 00 d0    ...            ; Fetch our side-B network number
    sta announce_tmr_hi                                               ; e1dc: 8d 2b 02    .+.            ; Use it as the re-announce timer's high byte (stagger)
    lda #0                                                            ; e1df: a9 00       ..             ; A = 0: timer low byte
    sta announce_tmr_lo                                               ; e1e1: 8d 2a 02    .*.            ; Store timer_lo; first fire in (net_num_b * 256) idle ticks
    lda #&0a                                                          ; e1e4: a9 0a       ..             ; A = 10: number of BridgeReplies to emit
    sta announce_count                                                ; e1e6: 8d 2c 02    .,.            ; Store the burst count
    lda #&40 ; '@'                                                    ; e1e9: a9 40       .@             ; A = &40: enable re-announce, bit 7 clear = send via A
    sta announce_flag                                                 ; e1eb: 8d 29 02    .).            ; Set announce_flag; main loop will now schedule the burst
; ***************************************************************************************
; Side-A BridgeReply (ctrl=&81): learn and re-broadcast
;
; Reached either directly as the ctrl=&81 handler (the re-announcement that follows a
; BridgeReset) or via fall-through from rx_a_handle_80 (which additionally wipes
; routing state before the learn loop).
;
; Processes the announcement payload: each byte from offset 6 up to rx_len is a network
; number that the announcer says it can reach. Since the announcer is on side A, those
; networks are reachable via side A from here too – mark each in reachable_via_a.
;
; After the learn loop, append our own net_num_a to the payload and bump rx_len.
; Falling through to rx_a_forward re-broadcasts the augmented frame out of ADLC B, so
; any bridges beyond us on that side hear about the announced networks plus us as one
; further hop along the route. This is classic distance-vector flooding.
; &e1ee referenced 1 time by &e187
.rx_a_handle_81
    ldy #6                                                            ; e1ee: a0 06       ..             ; Y = 6: skip past the 6-byte scout header
; &e1f0 referenced 1 time by &e1fd
.rx_a_learn_loop
    lda rx_dst_stn,y                                                  ; e1f0: b9 3c 02    .<.            ; Fetch next announced network number from payload
    tax                                                               ; e1f3: aa          .              ; X = the network to record
    lda #&ff                                                          ; e1f4: a9 ff       ..             ; A = &FF: 'route known' marker
    sta reachable_via_a,x                                             ; e1f6: 9d 5a 03    .Z.            ; Remember that network X is reachable via side A
    iny                                                               ; e1f9: c8          .              ; Advance to next payload byte
    cpy rx_len                                                        ; e1fa: cc 28 02    .(.            ; Have we reached the end of the payload?
    bne rx_a_learn_loop                                               ; e1fd: d0 f1       ..             ; No – keep learning
    lda net_num_a                                                     ; e1ff: ad 00 c0    ...            ; Load our own side-A network number
    sta rx_dst_stn,y                                                  ; e202: 99 3c 02    .<.            ; Append it to the payload for the onward broadcast
    inc rx_len                                                        ; e205: ee 28 02    .(.            ; Payload grew by one byte; record the new length
; ***************************************************************************************
; Forward an A-side frame to B, completing the 4-way handshake
;
; Entry point for cross-network forwarding of frames received on side A. Reached from
; three places:
;
; - rx_a_to_forward (&E147): the A-side frame is addressed to a remote station (not a
;   full broadcast), and we have accepted it via the routing filter.
; - rx_frame_a ctrl dispatch fall-through (at &E193): the frame is broadcast + port &9C
;   but has a control byte outside the recognised bridge-protocol set (&80-&83).
; - Fall-through from rx_a_handle_81 (at &E207): we've learned from the announcement
;   and appended net_num_a to the payload; now propagate it onward.
;
; The routine bridges the complete Econet four-way handshake by alternating
; direct-forward, receive-on-one-side, and re-transmit:
;
; | stage | direction | drain                                | retransmit                               |
; |-------|-----------|--------------------------------------|------------------------------------------|
; | SCOUT | A → B     | already in rx_* (done by rx_frame_a) | push rx_* into adlc_b_tx, pair-at-a-time |
; | ACK1  | B → A     | handshake_rx_b into &045A            | transmit_frame_a                         |
; | DATA  | A → B     | handshake_rx_a into &045A            | transmit_frame_b                         |
; | ACK2  | B → A     | handshake_rx_b into &045A            | transmit_frame_a                         |
;
; Each handshake_rx_? call can escape to main_loop (PLA/PLA/JMP) if the expected frame
; doesn't arrive, cleanly aborting the bridged conversation without further work on
; either side.
;
; The A-B-A transmit pattern at the routine's tail is therefore the natural shape of a
; bridged four-way handshake when the initial scout came from side A: two frames travel
; A → B (scout and data) and two travel B → A (two ACKs).
; &e208 referenced 2 times by &e147, &e193
.rx_a_forward
    lda rx_len                                                        ; e208: ad 28 02    .(.            ; Read rx_len into A
    tax                                                               ; e20b: aa          .              ; Preserve original length in X for odd-parity check
    and #&fe                                                          ; e20c: 29 fe       ).             ; Mask low bit to round DOWN to even byte count
    sta rx_len                                                        ; e20e: 8d 28 02    .(.            ; Store the rounded count for the pair loop
    jsr wait_adlc_b_idle                                              ; e211: 20 90 e6     ..            ; CSMA wait on B before transmitting the forwarded scout
    ldy #0                                                            ; e214: a0 00       ..             ; Y = 0: start at byte 0 of the rx_* buffer
; &e216 referenced 1 time by &e22f
.rx_a_forward_pair_loop
    jsr wait_adlc_b_irq                                               ; e216: 20 ea e3     ..            ; Wait for ADLC B's TDRA
    bit adlc_b_cr1                                                    ; e219: 2c 00 d8    ,..            ; BIT SR1 – V ← bit 6 (TDRA)
    bvc rx_a_forward_done                                             ; e21c: 50 42       PB             ; TDRA clear → chip lost sync, escape to main_loop
    lda rx_dst_stn,y                                                  ; e21e: b9 3c 02    .<.            ; Load byte Y of the received scout
    sta adlc_b_tx                                                     ; e221: 8d 02 d8    ...            ; Push it to ADLC B's TX FIFO
    iny                                                               ; e224: c8          .              ; Advance Y
    lda rx_dst_stn,y                                                  ; e225: b9 3c 02    .<.            ; Load byte Y+1
    sta adlc_b_tx                                                     ; e228: 8d 02 d8    ...            ; Push the second byte of the pair
    iny                                                               ; e22b: c8          .              ; Advance Y again
    cpy rx_len                                                        ; e22c: cc 28 02    .(.            ; Have we reached the even-rounded length yet?
    bcc rx_a_forward_pair_loop                                        ; e22f: 90 e5       ..             ; No → keep looping
    txa                                                               ; e231: 8a          .              ; Recover original length from X for parity check
    ror a                                                             ; e232: 6a          j              ; ROR: carry ← bit 0 (= original length was odd?)
    bcc rx_a_forward_ack_round                                        ; e233: 90 09       ..             ; Even → skip the trailing-byte path
    jsr wait_adlc_b_irq                                               ; e235: 20 ea e3     ..            ; Odd: wait for TDRA once more for the last byte
    lda rx_dst_stn,y                                                  ; e238: b9 3c 02    .<.            ; Load the trailing byte
    sta adlc_b_tx                                                     ; e23b: 8d 02 d8    ...            ; Push it to the TX FIFO
; &e23e referenced 1 time by &e233
.rx_a_forward_ack_round
    lda #&3f ; '?'                                                    ; e23e: a9 3f       .?             ; A = &3F: end-of-burst CR2 value
    sta adlc_b_cr2                                                    ; e240: 8d 01 d8    ...            ; Commit CR2 – ADLC B flushes the scout
    jsr wait_adlc_b_irq                                               ; e243: 20 ea e3     ..            ; Wait for the frame-complete IRQ
    lda #&5a ; 'Z'                                                    ; e246: a9 5a       .Z             ; A = &5A: reset mem_ptr_lo for the handshake stages below
    sta mem_ptr_lo                                                    ; e248: 85 80       ..             ; Store mem_ptr_lo
    lda #4                                                            ; e24a: a9 04       ..             ; A = 4: reset mem_ptr_hi
    sta mem_ptr_hi                                                    ; e24c: 85 81       ..             ; Store mem_ptr_hi – handshake_rx_? will write here
    jsr handshake_rx_b                                                ; e24e: 20 ff e5     ..            ; Stage 2: drain ACK1 from B into &045A…
    jsr transmit_frame_a                                              ; e251: 20 17 e5     ..            ; …and retransmit it on A so the originator hears its ACK
    jsr handshake_rx_a                                                ; e254: 20 6e e5     n.            ; Stage 3: drain DATA from A into &045A…
    jsr transmit_frame_b                                              ; e257: 20 c0 e4     ..            ; …and retransmit it on B to the destination
    jsr handshake_rx_b                                                ; e25a: 20 ff e5     ..            ; Stage 4: drain ACK2 from B into &045A…
    jsr transmit_frame_a                                              ; e25d: 20 17 e5     ..            ; …and retransmit it on A as the final ACK
; &e260 referenced 1 time by &e21c
.rx_a_forward_done
    jmp main_loop                                                     ; e260: 4c 51 e0    LQ.            ; 4-way handshake bridged; back to main_loop

; ***************************************************************************************
; Drain and dispatch an inbound frame on ADLC B
;
; Byte-for-byte mirror of rx_frame_a (&E0E2): same three-stage structure (addressing
; filter, drain, broadcast + bridge-protocol check), same control-byte dispatch, with
; adlc_a_* replaced by adlc_b_*, reachable_via_b by reachable_via_a, and the
; side-selector value swaps (net_num_a ↔ net_num_b) where appropriate.
;
; Bridge-protocol dispatch for this side:
;
; | ctrl  | handler        | role                        |
; |-------|----------------|-----------------------------|
; | &80   | rx_b_handle_80 | initial bridge announcement |
; | &81   | rx_b_handle_81 | re-announcement             |
; | &82   | rx_b_handle_82 | bridge query (shared &83)   |
; | &83   | rx_b_handle_83 | bridge query, known-station |
; | other | rx_b_forward   | forward or discard          |
;
; See rx_frame_a for the full per-instruction explanation.
; &e263 referenced 1 time by &e07e
.rx_frame_b
    lda #1                                                            ; e263: a9 01       ..             ; A = &01: mask SR2 bit 0 (AP = Address Present)
    bit adlc_b_cr2                                                    ; e265: 2c 01 d8    ,..            ; BIT SR2 – confirm the IRQ was a frame start
    beq rx_frame_b_bail                                               ; e268: f0 53       .S             ; AP not set → spurious IRQ, return to main_loop
    lda adlc_b_tx                                                     ; e26a: ad 02 d8    ...            ; Read FIFO byte 0: destination station
    sta rx_dst_stn                                                    ; e26d: 8d 3c 02    .<.            ; Stage dst_stn into the rx header buffer
    jsr wait_adlc_b_irq                                               ; e270: 20 ea e3     ..            ; Block until ADLC B IRQs again (byte 1 ready)
    bit adlc_b_cr2                                                    ; e273: 2c 01 d8    ,..            ; BIT SR2 – RDA still set for the next byte?
    bpl rx_frame_b_bail                                               ; e276: 10 45       .E             ; RDA cleared: frame truncated before dst_net, bail
    ldy adlc_b_tx                                                     ; e278: ac 02 d8    ...            ; Read byte 1 into Y: destination network
    beq rx_b_not_for_us                                               ; e27b: f0 43       .C             ; dst_net == 0 means 'local net of sender' – not for us
    lda reachable_via_a,y                                             ; e27d: b9 5a 03    .Z.            ; Probe reachable_via_a[dst_net] for a route via side A
    beq rx_b_not_for_us                                               ; e280: f0 3e       .>             ; No route → frame isn't ours to drain, re-listen
    sty rx_dst_net                                                    ; e282: 8c 3d 02    .=.            ; Commit dst_net now that it has passed filtering
    ldy #2                                                            ; e285: a0 02       ..             ; Y = 2: resume drain at offset 2 (after header)
; &e287 referenced 1 time by &e29f
.rx_frame_b_drain
    jsr wait_adlc_b_irq                                               ; e287: 20 ea e3     ..            ; Wait for the next FIFO byte IRQ
    bit adlc_b_cr2                                                    ; e28a: 2c 01 d8    ,..            ; BIT SR2 – RDA still asserted?
    bpl rx_frame_b_end                                                ; e28d: 10 12       ..             ; RDA cleared mid-body → go to FV check
    lda adlc_b_tx                                                     ; e28f: ad 02 d8    ...            ; Read byte Y of payload from TX/RX FIFO
    sta rx_dst_stn,y                                                  ; e292: 99 3c 02    .<.            ; Store into rx_dst_stn+Y (buffer grows into rx_*)
    iny                                                               ; e295: c8          .              ; Advance Y to the next slot
    lda adlc_b_tx                                                     ; e296: ad 02 d8    ...            ; Read byte Y+1 (pair-read without an IRQ wait)
    sta rx_dst_stn,y                                                  ; e299: 99 3c 02    .<.            ; Store the second byte of the pair
    iny                                                               ; e29c: c8          .              ; Advance Y past the pair
    cpy #&14                                                          ; e29d: c0 14       ..             ; Cap at 20 bytes (6-byte header + up to 14 payload)
    bcc rx_frame_b_drain                                              ; e29f: 90 e6       ..             ; Under cap → keep draining
; &e2a1 referenced 1 time by &e28d
.rx_frame_b_end
    lda #0                                                            ; e2a1: a9 00       ..             ; A = &00: halt ADLC B
    sta adlc_b_cr1                                                    ; e2a3: 8d 00 d8    ...            ; CR1 = 0: disable TX and RX IRQs
    lda #&84                                                          ; e2a6: a9 84       ..             ; A = &84: clear-RX-status + FV-clear bits
    sta adlc_b_cr2                                                    ; e2a8: 8d 01 d8    ...            ; Commit CR2: acknowledge end-of-frame
    lda #2                                                            ; e2ab: a9 02       ..             ; A = &02: mask SR2 bit 1 (FV: Frame Valid)
    bit adlc_b_cr2                                                    ; e2ad: 2c 01 d8    ,..            ; BIT SR2 – test FV and RDA
    beq rx_frame_b_bail                                               ; e2b0: f0 0b       ..             ; FV clear → frame corrupt or short, bail
    bpl rx_frame_b_dispatch                                           ; e2b2: 10 17       ..             ; FV set + no RDA → clean end; go to dispatch
    lda adlc_b_tx                                                     ; e2b4: ad 02 d8    ...            ; FV + RDA: one trailing byte still in FIFO
    sta rx_dst_stn,y                                                  ; e2b7: 99 3c 02    .<.            ; Store the odd trailing byte
    iny                                                               ; e2ba: c8          .              ; Advance Y to count that final byte
    bne rx_frame_b_dispatch                                           ; e2bb: d0 0e       ..             ; Unconditional: continue to dispatch
; &e2bd referenced 4 times by &e268, &e276, &e2b0, &e2d0
.rx_frame_b_bail
    jmp main_loop                                                     ; e2bd: 4c 51 e0    LQ.            ; Bail: restart from main_loop (full ADLC re-init)

; &e2c0 referenced 2 times by &e27b, &e280
.rx_b_not_for_us
    lda #&a2                                                          ; e2c0: a9 a2       ..             ; A = &A2: RX on, IRQ enabled, TX in reset
    sta adlc_b_cr1                                                    ; e2c2: 8d 00 d8    ...            ; Re-arm ADLC B to listen for the next frame
    jmp main_loop_poll                                                ; e2c5: 4c 79 e0    Ly.            ; Skip main_loop re-init; go straight back to polling

; &e2c8 referenced 2 times by &e2f2, &e301
.rx_b_to_forward
    jmp rx_b_forward                                                  ; e2c8: 4c 89 e3    L..            ; Out-of-range JMP to rx_b_forward (JSR can't reach)

; &e2cb referenced 2 times by &e2b2, &e2bb
.rx_frame_b_dispatch
    sty rx_len                                                        ; e2cb: 8c 28 02    .(.            ; Save final byte count (even if 0 bytes of payload)
    cpy #6                                                            ; e2ce: c0 06       ..             ; Compare to 6 – minimum valid scout header
    bcc rx_frame_b_bail                                               ; e2d0: 90 eb       ..             ; Shorter than header → bail
    lda rx_src_net                                                    ; e2d2: ad 3f 02    .?.            ; Load src_net from the drained frame
    bne rx_b_src_net_resolved                                         ; e2d5: d0 06       ..             ; Non-zero → sender supplied src_net, keep it
    lda net_num_b                                                     ; e2d7: ad 00 d0    ...            ; Sender left src_net = 0 ('my local net')
    sta rx_src_net                                                    ; e2da: 8d 3f 02    .?.            ; …substitute our own B-side network number
; &e2dd referenced 1 time by &e2d5
.rx_b_src_net_resolved
    lda net_num_a                                                     ; e2dd: ad 00 c0    ...            ; Load our A-side network number for comparison
    cmp rx_dst_net                                                    ; e2e0: cd 3d 02    .=.            ; Compare against the incoming dst_net
    bne rx_b_broadcast_check                                          ; e2e3: d0 05       ..             ; Not for side A → skip the local rewrite
    lda #0                                                            ; e2e5: a9 00       ..             ; dst_net names our A-side network…
    sta rx_dst_net                                                    ; e2e7: 8d 3d 02    .=.            ; …normalise dst_net to 0 (local on A)
; &e2ea referenced 1 time by &e2e3
.rx_b_broadcast_check
    lda rx_dst_stn                                                    ; e2ea: ad 3c 02    .<.            ; Load dst_stn for the broadcast test
    and rx_dst_net                                                    ; e2ed: 2d 3d 02    -=.            ; AND with dst_net (both &FF only if full broadcast)
    cmp #&ff                                                          ; e2f0: c9 ff       ..             ; Compare result to &FF
    bne rx_b_to_forward                                               ; e2f2: d0 d4       ..             ; Not a full broadcast → forward path
    jsr adlc_b_listen                                                 ; e2f4: 20 19 e4     ..            ; Broadcast: re-arm B's listen mode for any follow-up
    lda #&c2                                                          ; e2f7: a9 c2       ..             ; A = &C2: reset TX, enable RX
    sta adlc_b_cr1                                                    ; e2f9: 8d 00 d8    ...            ; Commit CR1 while we process the bridge-protocol frame
    lda rx_port                                                       ; e2fc: ad 41 02    .A.            ; Load the port byte from the drained frame
    cmp #&9c                                                          ; e2ff: c9 9c       ..             ; Compare with &9C (bridge-protocol port)
    bne rx_b_to_forward                                               ; e301: d0 c5       ..             ; Not our port → drop into forward path
    lda rx_ctrl                                                       ; e303: ad 40 02    .@.            ; Load ctrl byte for the per-type dispatch
    cmp #&81                                                          ; e306: c9 81       ..             ; Test &81 (BridgeReply: re-announcement)
    beq rx_b_handle_81                                                ; e308: f0 65       .e             ; Match → rx_b_handle_81
    cmp #&80                                                          ; e30a: c9 80       ..             ; Test &80 (BridgeReset: initial announcement)
    beq rx_b_handle_80                                                ; e30c: f0 49       .I             ; Match → rx_b_handle_80
    cmp #&82                                                          ; e30e: c9 82       ..             ; Test &82 (WhatNet: general query)
    beq rx_b_handle_82                                                ; e310: f0 0c       ..             ; Match → rx_b_handle_82
    cmp #&83                                                          ; e312: c9 83       ..             ; Test &83 (IsNet: targeted query)
    bne rx_b_forward                                                  ; e314: d0 73       .s             ; Unknown ctrl → forward path (fall through to rx_b_handle_83 on match)
; ***************************************************************************************
; Side-B IsNet query (ctrl=&83): targeted network lookup
;
; Mirror of rx_a_handle_83 (&E195) with A/B swapped: consults reachable_via_a (not _b)
; because the frame arrived on side B. Falls through to rx_b_handle_82 when the queried
; network is known.
.rx_b_handle_83
    ldy rx_query_net                                                  ; e316: ac 49 02    .I.            ; Y = the queried network number
    lda reachable_via_a,y                                             ; e319: b9 5a 03    .Z.            ; Check if we have a route via the other side
    beq rx_b_query_done                                               ; e31c: f0 36       .6             ; Unknown → silently drop this IsNet query
; ***************************************************************************************
; Side-B WhatNet query (ctrl=&82); also IsNet response path
;
; Mirror of rx_a_handle_82 (&E19D) with A/B swapped throughout: stagger seeded from
; net_num_a, transmit via ADLC B, tx_src_net patched to net_num_a, response-data's
; first payload byte (at the tx_ctrl slot) encodes net_num_b. See rx_a_handle_82 for
; the full protocol description.
; &e31e referenced 1 time by &e310
.rx_b_handle_82
    jsr adlc_b_listen                                                 ; e31e: 20 19 e4     ..            ; Re-arm ADLC B into listen mode before replying
    jsr build_query_response                                          ; e321: 20 8d e4     ..            ; Build reply-scout template addressed at the querier
    lda net_num_a                                                     ; e324: ad 00 c0    ...            ; Fetch our side-A network number
    sta tx_src_net                                                    ; e327: 8d 5d 04    .].            ; Patch src_net so the scout names us by net_num_a
    sta ctr24_lo                                                      ; e32a: 8d 14 02    ...            ; Copy it into the stagger-delay counter too
    jsr stagger_delay                                                 ; e32d: 20 48 e4     H.            ; Busy-wait for (net_num_a * ~50us) + 160us
    jsr wait_adlc_b_idle                                              ; e330: 20 90 e6     ..            ; CSMA wait on B
    jsr transmit_frame_b                                              ; e333: 20 c0 e4     ..            ; Transmit the reply scout
    jsr handshake_rx_b                                                ; e336: 20 ff e5     ..            ; Wait for the querier's scout-ACK on B
    jsr build_query_response                                          ; e339: 20 8d e4     ..            ; Rebuild template – next frame is the data response
    lda net_num_a                                                     ; e33c: ad 00 c0    ...            ; Fetch net_num_a
    sta tx_src_net                                                    ; e33f: 8d 5d 04    .].            ; Re-patch src_net
    lda net_num_b                                                     ; e342: ad 00 d0    ...            ; Fetch net_num_b
    sta tx_ctrl                                                       ; e345: 8d 5e 04    .^.            ; Write as data-frame payload byte 0
    lda rx_query_net                                                  ; e348: ad 49 02    .I.            ; Fetch the network the querier asked about
    sta tx_port                                                       ; e34b: 8d 5f 04    ._.            ; Write as data-frame payload byte 1
    jsr transmit_frame_b                                              ; e34e: 20 c0 e4     ..            ; Transmit the data frame
    jsr handshake_rx_b                                                ; e351: 20 ff e5     ..            ; Wait for final data-ACK
; &e354 referenced 1 time by &e31c
.rx_b_query_done
    jmp main_loop                                                     ; e354: 4c 51 e0    LQ.            ; Transaction complete → back to main_loop

; ***************************************************************************************
; Side-B BridgeReset (ctrl=&80): learn topology from scratch
;
; Mirror of rx_a_handle_80 (&E1D6): wipe reachable_via_* via init_reachable_nets, seed
; the re-announce timer's high byte from net_num_a (mirror of A-side seeding from
; net_num_b), set announce_count = 10 and announce_flag = &80 (bit 7 set = next
; outbound on side B). Falls through to rx_b_handle_81.
;
; The other of the two places in the ROM that sets announce_flag non-zero; all other
; writes to that byte clear it.
; &e357 referenced 1 time by &e30c
.rx_b_handle_80
    jsr init_reachable_nets                                           ; e357: 20 24 e4     $.            ; Wipe all learned routing state (topology reset)
    lda net_num_a                                                     ; e35a: ad 00 c0    ...            ; Fetch our side-A network number
    sta announce_tmr_hi                                               ; e35d: 8d 2b 02    .+.            ; Use as re-announce timer high byte (stagger)
    lda #0                                                            ; e360: a9 00       ..             ; A = 0: timer low byte
    sta announce_tmr_lo                                               ; e362: 8d 2a 02    .*.            ; Store timer_lo; first fire in (net_num_a * 256) ticks
    lda #&0a                                                          ; e365: a9 0a       ..             ; A = 10: number of BridgeReplies to emit
    sta announce_count                                                ; e367: 8d 2c 02    .,.            ; Store the burst count
    lda #&80                                                          ; e36a: a9 80       ..             ; A = &80: enable re-announce, bit 7 set = send via B
    sta announce_flag                                                 ; e36c: 8d 29 02    .).            ; Set announce_flag; main loop will now schedule the burst
; ***************************************************************************************
; Side-B BridgeReply (ctrl=&81): learn and re-broadcast
;
; Mirror of rx_a_handle_81 (&E1EE): reads each payload byte from offset 6 onward as a
; network number reachable via side B, marks reachable_via_b[x] = &FF for each (mirror
; of the A-side writing reachable_via_a). Appends net_num_b to the payload and falls
; through to rx_b_forward for re-broadcast onto side A.
; &e36f referenced 1 time by &e308
.rx_b_handle_81
    ldy #6                                                            ; e36f: a0 06       ..             ; Y = 6: skip past the 6-byte scout header
; &e371 referenced 1 time by &e37e
.rx_b_learn_loop
    lda rx_dst_stn,y                                                  ; e371: b9 3c 02    .<.            ; Fetch next announced network number from payload
    tax                                                               ; e374: aa          .              ; X = the network to record
    lda #&ff                                                          ; e375: a9 ff       ..             ; A = &FF: 'route known' marker
    sta reachable_via_b,x                                             ; e377: 9d 5a 02    .Z.            ; Remember that network X is reachable via side B
    iny                                                               ; e37a: c8          .              ; Advance to next payload byte
    cpy rx_len                                                        ; e37b: cc 28 02    .(.            ; Have we reached the end of the payload?
    bne rx_b_learn_loop                                               ; e37e: d0 f1       ..             ; No – keep learning
    lda net_num_b                                                     ; e380: ad 00 d0    ...            ; Load our own side-B network number
    sta rx_dst_stn,y                                                  ; e383: 99 3c 02    .<.            ; Append it to the payload for the onward broadcast
    inc rx_len                                                        ; e386: ee 28 02    .(.            ; Payload grew by one byte; record the new length
; ***************************************************************************************
; Forward a B-side frame to A, completing the 4-way handshake
;
; Byte-for-byte mirror of rx_a_forward (&E208) with A and B swapped throughout: the
; inbound scout is pushed via adlc_a_tx, and the B-A-B tail bridges the four-way
; handshake the other direction.
;
; Reached from three places:
;
; - rx_b_to_forward (&E2C8): the B-side frame is addressed to a remote station (not a
;   full broadcast), and we have accepted it via the routing filter.
; - rx_frame_b ctrl dispatch fall-through (at &E314): the frame is broadcast + port &9C
;   but has a control byte outside the recognised bridge-protocol set (&80-&83).
; - Fall-through from rx_b_handle_81 (at &E387): we've learned from the announcement
;   and appended net_num_b to the payload; now propagate it onward.
;
; | stage | direction | drain                                | retransmit                               |
; |-------|-----------|--------------------------------------|------------------------------------------|
; | SCOUT | B → A     | already in rx_* (done by rx_frame_b) | push rx_* into adlc_a_tx, pair-at-a-time |
; | ACK1  | A → B     | handshake_rx_a into &045A            | transmit_frame_b                         |
; | DATA  | B → A     | handshake_rx_b into &045A            | transmit_frame_a                         |
; | ACK2  | A → B     | handshake_rx_a into &045A            | transmit_frame_b                         |
;
; See rx_a_forward for the full per-stage explanation.
; &e389 referenced 2 times by &e2c8, &e314
.rx_b_forward
    lda rx_len                                                        ; e389: ad 28 02    .(.            ; Read rx_len into A
    tax                                                               ; e38c: aa          .              ; Preserve original length in X for odd-parity check
    and #&fe                                                          ; e38d: 29 fe       ).             ; Mask low bit to round DOWN to even byte count
    sta rx_len                                                        ; e38f: 8d 28 02    .(.            ; Store the rounded count for the pair loop
    jsr wait_adlc_a_idle                                              ; e392: 20 dc e6     ..            ; CSMA wait on A before transmitting the forwarded scout
    ldy #0                                                            ; e395: a0 00       ..             ; Y = 0: start at byte 0 of the rx_* buffer
; &e397 referenced 1 time by &e3b0
.rx_b_forward_pair_loop
    jsr wait_adlc_a_irq                                               ; e397: 20 e4 e3     ..            ; Wait for ADLC A's TDRA
    bit adlc_a_cr1                                                    ; e39a: 2c 00 c8    ,..            ; BIT SR1 – V ← bit 6 (TDRA)
    bvc rx_b_forward_done                                             ; e39d: 50 42       PB             ; TDRA clear → chip lost sync, escape to main_loop
    lda rx_dst_stn,y                                                  ; e39f: b9 3c 02    .<.            ; Load byte Y of the received scout
    sta adlc_a_tx                                                     ; e3a2: 8d 02 c8    ...            ; Push it to ADLC A's TX FIFO
    iny                                                               ; e3a5: c8          .              ; Advance Y
    lda rx_dst_stn,y                                                  ; e3a6: b9 3c 02    .<.            ; Load byte Y+1
    sta adlc_a_tx                                                     ; e3a9: 8d 02 c8    ...            ; Push the second byte of the pair
    iny                                                               ; e3ac: c8          .              ; Advance Y again
    cpy rx_len                                                        ; e3ad: cc 28 02    .(.            ; Have we reached the even-rounded length yet?
    bcc rx_b_forward_pair_loop                                        ; e3b0: 90 e5       ..             ; No → keep looping
    txa                                                               ; e3b2: 8a          .              ; Recover original length from X for parity check
    ror a                                                             ; e3b3: 6a          j              ; ROR: carry ← bit 0 (= original length was odd?)
    bcc rx_b_forward_ack_round                                        ; e3b4: 90 09       ..             ; Even → skip the trailing-byte path
    jsr wait_adlc_a_irq                                               ; e3b6: 20 e4 e3     ..            ; Odd: wait for TDRA once more for the last byte
    lda rx_dst_stn,y                                                  ; e3b9: b9 3c 02    .<.            ; Load the trailing byte
    sta adlc_a_tx                                                     ; e3bc: 8d 02 c8    ...            ; Push it to the TX FIFO
; &e3bf referenced 1 time by &e3b4
.rx_b_forward_ack_round
    lda #&3f ; '?'                                                    ; e3bf: a9 3f       .?             ; A = &3F: end-of-burst CR2 value
    sta adlc_a_cr2                                                    ; e3c1: 8d 01 c8    ...            ; Commit CR2 – ADLC A flushes the scout
    jsr wait_adlc_a_irq                                               ; e3c4: 20 e4 e3     ..            ; Wait for the frame-complete IRQ
    lda #&5a ; 'Z'                                                    ; e3c7: a9 5a       .Z             ; A = &5A: reset mem_ptr_lo for the handshake stages below
    sta mem_ptr_lo                                                    ; e3c9: 85 80       ..             ; Store mem_ptr_lo
    lda #4                                                            ; e3cb: a9 04       ..             ; A = 4: reset mem_ptr_hi
    sta mem_ptr_hi                                                    ; e3cd: 85 81       ..             ; Store mem_ptr_hi – handshake_rx_? will write here
    jsr handshake_rx_a                                                ; e3cf: 20 6e e5     n.            ; Stage 2: drain ACK1 from A into &045A…
    jsr transmit_frame_b                                              ; e3d2: 20 c0 e4     ..            ; …and retransmit it on B so the originator hears its ACK
    jsr handshake_rx_b                                                ; e3d5: 20 ff e5     ..            ; Stage 3: drain DATA from B into &045A…
    jsr transmit_frame_a                                              ; e3d8: 20 17 e5     ..            ; …and retransmit it on A to the destination
    jsr handshake_rx_a                                                ; e3db: 20 6e e5     n.            ; Stage 4: drain ACK2 from A into &045A…
    jsr transmit_frame_b                                              ; e3de: 20 c0 e4     ..            ; …and retransmit it on B as the final ACK
; &e3e1 referenced 1 time by &e39d
.rx_b_forward_done
    jmp main_loop                                                     ; e3e1: 4c 51 e0    LQ.            ; 4-way handshake bridged; back to main_loop

; ***************************************************************************************
; Wait for ADLC A IRQ (polled)
;
; Spin reading SR1 of ADLC A until the IRQ bit (bit 7) is set. Called from 19 sites
; where the code needs to wait for the ADLC to signal an event (frame complete, RX data
; available, TX ready, etc.).
;
; The Bridge does not route the ADLC ~IRQ output to the 6502 ~IRQ line (that pin is
; used for the self-test push-button), so ADLC attention is obtained by polling.
; &e3e4 referenced 19 times by &e0ef, &e106, &e397, &e3b6, &e3c4, &e3e7, &e523, &e550, &e562, &e575, &e583, &e593, &f125, &f15c, &f1da, &f1ea, &f20d, &f22a, &f242
.wait_adlc_a_irq
    bit adlc_a_cr1                                                    ; e3e4: 2c 00 c8    ,..            ; Peek ADLC A status, testing the IRQ-summary bit
    bpl wait_adlc_a_irq                                               ; e3e7: 10 fb       ..             ; Spin while the chip has nothing to report
    rts                                                               ; e3e9: 60          `              ; Event pending; return to caller to handle it

; ***************************************************************************************
; Wait for ADLC B IRQ (polled)
;
; As wait_adlc_a_irq but for ADLC B.
; &e3ea referenced 19 times by &e216, &e235, &e243, &e270, &e287, &e3ed, &e4cc, &e4f9, &e50b, &e606, &e614, &e624, &f139, &f149, &f16c, &f189, &f1a1, &f1c6, &f1fd
.wait_adlc_b_irq
    bit adlc_b_cr1                                                    ; e3ea: 2c 00 d8    ,..            ; Peek ADLC B status, testing the IRQ-summary bit
    bpl wait_adlc_b_irq                                               ; e3ed: 10 fb       ..             ; Spin while the chip has nothing to report
    rts                                                               ; e3ef: 60          `              ; Event pending; return to caller to handle it

; ***************************************************************************************
; ADLC A full reset, then enter RX listen
;
; Aborts all ADLC A activity and returns it to idle RX listen mode. Falls through to
; adlc_a_listen. Called from the reset handler.
; &e3f0 referenced 1 time by &e005
.adlc_a_full_reset
    lda #&c1                                                          ; e3f0: a9 c1       ..             ; Mask: reset TX and RX, unlock CR3/CR4 via AC=1
    sta adlc_a_cr1                                                    ; e3f2: 8d 00 c8    ...            ; Drop ADLC A into full reset
    lda #&1e                                                          ; e3f5: a9 1e       ..             ; Mask: 8-bit RX word length, abort-extend, NRZ
    sta adlc_a_tx2                                                    ; e3f7: 8d 03 c8    ...            ; Program CR4 (reached via tx2 slot while AC=1)
    lda #0                                                            ; e3fa: a9 00       ..             ; Mask: no loopback, DTR released, NRZ encoding
    sta adlc_a_cr2                                                    ; e3fc: 8d 01 c8    ...            ; Program CR3 (reached via cr2 slot while AC=1); fall through
; ***************************************************************************************
; Enter ADLC A RX listen mode
;
; TX held in reset, RX active. IRQs are generated internally by the chip but the ~IRQ
; output is not wired; see wait_adlc_a_irq.
; &e3ff referenced 2 times by &e173, &e19d
.adlc_a_listen
    lda #&82                                                          ; e3ff: a9 82       ..             ; Mask: keep TX in reset, enable RX IRQs, AC=0
    sta adlc_a_cr1                                                    ; e401: 8d 00 c8    ...            ; Commit CR1; subsequent cr2/tx writes hit CR2/TX again
    lda #&67 ; 'g'                                                    ; e404: a9 67       .g             ; Mask: clear status flags, FC_TDRA, 2/1-byte, PSE
    sta adlc_a_cr2                                                    ; e406: 8d 01 c8    ...            ; Commit CR2; ADLC A now listening for incoming frames
    rts                                                               ; e409: 60          `              ; Return; Econet side A is idle-listen

; ***************************************************************************************
; ADLC B full reset, then enter RX listen
;
; Byte-for-byte mirror of adlc_a_full_reset, targeting ADLC B's register set at
; &D800-&D803. Falls through to adlc_b_listen. CR3=&00 puts the LOC/DTR pin HIGH,
; sourcing current through the front-panel status LED – so the LED is LIT throughout
; normal operation, the distinguishing feature from self_test_reset_adlcs which writes
; CR3 = &80 to extinguish it.
; &e40a referenced 1 time by &e008
.adlc_b_full_reset
    lda #&c1                                                          ; e40a: a9 c1       ..             ; Mask: reset TX and RX, unlock CR3/CR4 via AC=1
    sta adlc_b_cr1                                                    ; e40c: 8d 00 d8    ...            ; Drop ADLC B into full reset
    lda #&1e                                                          ; e40f: a9 1e       ..             ; Mask: 8-bit RX word length, abort-extend, NRZ
    sta adlc_b_tx2                                                    ; e411: 8d 03 d8    ...            ; Program CR4 (reached via tx2 slot while AC=1)
    lda #0                                                            ; e414: a9 00       ..             ; Mask: CR3 bit 7 clear → LOC/DTR pin high → status LED ON
    sta adlc_b_cr2                                                    ; e416: 8d 01 d8    ...            ; Program CR3; fall through into listen mode
; ***************************************************************************************
; Enter ADLC B RX listen mode
;
; Mirror of adlc_a_listen for ADLC B.
; &e419 referenced 2 times by &e2f4, &e31e
.adlc_b_listen
    lda #&82                                                          ; e419: a9 82       ..             ; Mask: keep TX in reset, enable RX IRQs, AC=0
    sta adlc_b_cr1                                                    ; e41b: 8d 00 d8    ...            ; Commit CR1; subsequent cr2/tx writes hit CR2/TX again
    lda #&67 ; 'g'                                                    ; e41e: a9 67       .g             ; Mask: clear status flags, FC_TDRA, 2/1-byte, PSE
    sta adlc_b_cr2                                                    ; e420: 8d 01 d8    ...            ; Commit CR2; ADLC B now listening for incoming frames
    rts                                                               ; e423: 60          `              ; Return; Econet side B is idle-listen

; ***************************************************************************************
; Reset both routing tables to the directly-attached networks
;
; Zeroes the two 256-entry routing tables (reachable_via_a at &035A and reachable_via_b
; at &025A), then writes &FF to four slots that are true by virtue of the Bridge's
; immediate topology:
;
; | slot                       | meaning                                 |
; |----------------------------|-----------------------------------------|
; | reachable_via_a[net_num_a] | side A's own network is reachable via A |
; | reachable_via_b[net_num_b] | side B's own network is reachable via B |
; | reachable_via_a[255]       | broadcast network reachable via either  |
; | reachable_via_b[255]       | side                                    |
;
; Everything else starts at zero and is populated later by bridge-protocol
; announcements learned in the rx handlers (see rx_a_handle_80 / rx_b_handle_80).
;
; Called from the reset handler and also re-invoked from the two rx_?_handle_80 paths –
; receiving an initial bridge announcement indicates a topology change that invalidates
; the learned state, so the Bridge forgets everything and starts accumulating again.
; &e424 referenced 3 times by &e002, &e1d6, &e357
.init_reachable_nets
    ldy #0                                                            ; e424: a0 00       ..             ; Y: walks every network number 0..255
    lda #0                                                            ; e426: a9 00       ..             ; A = 0: 'route not known' marker
; &e428 referenced 1 time by &e42f
.init_reachable_nets_clear
    sta reachable_via_b,y                                             ; e428: 99 5a 02    .Z.            ; Clear side-A handler's entry for network Y
    sta reachable_via_a,y                                             ; e42b: 99 5a 03    .Z.            ; Clear side-B handler's entry for network Y
    iny                                                               ; e42e: c8          .              ; Step to next network number
    bne init_reachable_nets_clear                                     ; e42f: d0 f7       ..             ; Loop back until Y wraps through all 256 slots
    lda #&ff                                                          ; e431: a9 ff       ..             ; A = &FF: 'route known' marker for the writes below
    ldy net_num_a                                                     ; e433: ac 00 c0    ...            ; Y = net_num_a: our own side-A network number
    sta reachable_via_a,y                                             ; e436: 99 5a 03    .Z.            ; side-B handler can reach net_num_a via side A
    ldy net_num_b                                                     ; e439: ac 00 d0    ...            ; Y = net_num_b: our own side-B network number
    sta reachable_via_b,y                                             ; e43c: 99 5a 02    .Z.            ; side-A handler can reach net_num_b via side B
    ldy #&ff                                                          ; e43f: a0 ff       ..             ; Y = 255: the Econet broadcast network
    sta reachable_via_b,y                                             ; e441: 99 5a 02    .Z.            ; Broadcasts reachable for side-A handler's traffic
    sta reachable_via_a,y                                             ; e444: 99 5a 03    .Z.            ; Broadcasts reachable for side-B handler's traffic
    rts                                                               ; e447: 60          `              ; Tables primed; return to caller

; ***************************************************************************************
; Fixed prelude + per-count delay scaled by ctr24_lo
;
; A calibrated busy-wait used by the query-response paths to stagger their
; transmissions. Called from rx_a_handle_82 (at &E1AC) and rx_b_handle_82 (at &E32D),
; in each case with ctr24_lo pre-loaded with the bridge's opposite-side network number
; (net_num_b for A-side responses, net_num_a for B-side responses).
;
; Two phases:
;
; 1. Prelude (~&40 × DEY/BNE cycles): a fixed settling delay, the same regardless of
;    caller. Roughly &40 * 5 = 320 cycles = ~160 us at 2 MHz.
; 2. Per-count loop (ctr24_lo iterations × (&14 × DEY/BNE + DEC/BNE) cycles): roughly
;    ctr24_lo * 110 cycles. For a typical network number of ~24, that's ~2600 cycles =
;    ~1.3 ms.
;
; For the range of network numbers permitted (1-127), the total delay runs from ~215 us
; to ~7 ms. This spread means multiple bridges on the same segment responding to a
; broadcast query (ctrl=&82) transmit their responses at measurably different times,
; reducing the chance of collisions on the shared medium. Bridges with higher network
; numbers back off longer – a cheap deterministic priority scheme that requires no
; coordination.
; &e448 referenced 2 times by &e1ac, &e32d
.stagger_delay
    ldy #&40 ; '@'                                                    ; e448: a0 40       .@             ; Y = &40: seed for the fixed-length settling delay
; &e44a referenced 1 time by &e44b
.stagger_delay_prelude
    dey                                                               ; e44a: 88          .              ; Tight DEY/BNE loop – burns ~160 us regardless of caller
    bne stagger_delay_prelude                                         ; e44b: d0 fd       ..             ; Spin until the prelude counter hits zero
; &e44d referenced 1 time by &e455
.stagger_delay_outer
    ldy #&14                                                          ; e44d: a0 14       ..             ; Y = &14: seed for one inner-loop iteration
; &e44f referenced 1 time by &e450
.stagger_delay_inner
    dey                                                               ; e44f: 88          .              ; Tight DEY/BNE – ~50 us per outer iteration
    bne stagger_delay_inner                                           ; e450: d0 fd       ..             ; Spin until the inner counter hits zero
    dec ctr24_lo                                                      ; e452: ce 14 02    ...            ; One tick of the caller's network-number count
    bne stagger_delay_outer                                           ; e455: d0 f6       ..             ; Loop until ctr24_lo reaches zero (net_num_? ticks)
    rts                                                               ; e457: 60          `              ; Delay complete; return so caller can transmit

; ***************************************************************************************
; Build a BridgeReset scout carrying net_num_b as payload
;
; Populates the outbound frame control block at &045A-&0460 with an all-broadcast
; BridgeReset scout – ctrl=&80, port=&9C, payload=net_num_b. At reset time this is
; transmitted via ADLC A first (announcing "network net_num_b is reachable through me"
; to side A's stations), then tx_data0 is patched to net_num_a and the same frame is
; re-transmitted via ADLC B.
;
; | field      | value     | meaning                     |
; |------------|-----------|-----------------------------|
; | tx_dst_stn | &FF       | broadcast station           |
; | tx_dst_net | &FF       | broadcast network           |
; | tx_src_stn | &18       | firmware marker (see below) |
; | tx_src_net | &18       | firmware marker (see below) |
; | tx_ctrl    | &80       | initial-announcement ctrl   |
; | tx_port    | &9C       | bridge-protocol port        |
; | tx_data0   | net_num_b | network number on side B    |
;
; The src_stn/src_net fields are both set to the constant &18. The Bridge has no
; station number of its own (only network numbers, per the Installation Guide), so
; these fields are not real addresses. Receivers do not use them for routing --
; rx_a_handle_81 reads the payload starting at offset 6 and ignores bytes 2-3 entirely.
; The most plausible role for &18 is defensive redundancy: together with dst=(&FF,&FF),
; ctrl=&80/&81 and port=&9C it gives a receiver multiple ways to confirm that a
; received frame is a well-formed bridge announcement.
;
; Also writes &06 to tx_end_lo and &04 to tx_end_hi (so the transmit routine sends
; bytes &045A..&0460 inclusive – 7 bytes when X=1), loads X=1 (trailing-byte flag for
; transmit_frame_a), and points mem_ptr at the frame block (&045A).
;
; Called from the reset handler at &E038 and again from &E098 (the main-loop periodic
; re-announce path). A structurally identical cousin builder is build_query_response
; (&E48D), called from four sites; it populates the same fields with values drawn from
; RAM variables at rx_src_stn and rx_query_net rather than baked-in constants.
; &e458 referenced 2 times by &e038, &e098
.build_announce_b
    lda #&ff                                                          ; e458: a9 ff       ..             ; Broadcast marker &FF for dst station AND network
    sta tx_dst_stn                                                    ; e45a: 8d 5a 04    .Z.            ; Write dst_stn = 255 into the frame header
    sta tx_dst_net                                                    ; e45d: 8d 5b 04    .[.            ; Write dst_net = 255 into the frame header
    lda #&18                                                          ; e460: a9 18       ..             ; Firmware marker &18 for src fields (no station id)
    sta tx_src_stn                                                    ; e462: 8d 5c 04    .\.            ; Write src_stn = &18
    sta tx_src_net                                                    ; e465: 8d 5d 04    .].            ; Write src_net = &18
    lda #&9c                                                          ; e468: a9 9c       ..             ; Bridge-protocol port number
    sta tx_port                                                       ; e46a: 8d 5f 04    ._.            ; Write port = &9C into the frame header
    lda #&80                                                          ; e46d: a9 80       ..             ; Control byte: &80 = BridgeReset (initial announcement)
    sta tx_ctrl                                                       ; e46f: 8d 5e 04    .^.            ; Write ctrl = &80 into the frame header
    lda net_num_b                                                     ; e472: ad 00 d0    ...            ; Payload: our side-B network number to announce
    sta tx_data0                                                      ; e475: 8d 60 04    .`.            ; Write as data byte 0 (trailing byte after header)
    ldx #1                                                            ; e478: a2 01       ..             ; X = 1: ask transmit_frame_? to send the trailing byte too
    lda #6                                                            ; e47a: a9 06       ..             ; Low byte of tx-end: &06 == 6 header bytes
    sta tx_end_lo                                                     ; e47c: 8d 00 02    ...            ; Store low byte of tx_end
    lda #4                                                            ; e47f: a9 04       ..             ; High byte of tx-end: &04 matches mem_ptr_hi below
    sta tx_end_hi                                                     ; e481: 8d 01 02    ...            ; Store high byte of tx_end (end pair = &0406)
    lda #&5a ; 'Z'                                                    ; e484: a9 5a       .Z             ; Low byte of mem_ptr: frame starts at &045A
    sta mem_ptr_lo                                                    ; e486: 85 80       ..             ; Store mem_ptr_lo
    lda #4                                                            ; e488: a9 04       ..             ; High byte of mem_ptr: page &04
    sta mem_ptr_hi                                                    ; e48a: 85 81       ..             ; Store mem_ptr_hi (pointer = &045A)
    rts                                                               ; e48c: 60          `              ; Return; caller may now transmit the BridgeReset scout

; ***************************************************************************************
; Build a reply template for WhatNet/IsNet query responses
;
; A second frame-builder (sibling of build_announce_b) used by the bridge-query
; response path. Called twice per response: once to build the reply scout (ctrl=&80 +
; reply_port as the port), then after the querier's scout-ACK has been received, called
; again to rebuild the buffer as a data frame – the caller then patches bytes 4 and 5
; (labelled tx_ctrl and tx_port but genuinely payload in a data frame) with the routing
; answer. Where build_announce_b writes a broadcast-addressed template, this one builds
; a unicast reply:
;
; | field      | value         | notes                               |
; |------------|---------------|-------------------------------------|
; | tx_dst_stn | rx_src_stn    | station that sent the query         |
; | tx_dst_net | 0             | local network                       |
; | tx_src_stn | 0             | Bridge has no station               |
; | tx_src_net | 0             | (caller patches to net_num_?)       |
; | tx_ctrl    | &80           | scout control byte                  |
; | tx_port    | rx_query_port | response port from byte 12 of query |
; | X register | 0             | no trailing payload                 |
;
; Also writes tx_end_lo=&06 / tx_end_hi=&04 and points mem_ptr at &045A so a subsequent
; transmit_frame_? sends the 6-byte scout.
;
; Called from the two query-response paths (&E1A0 and &E1B8 on side A; &E321 and &E339
; on side B). Each caller then patches a subset of the fields before calling
; transmit_frame_? – the idiomatic second call in particular overwrites tx_ctrl and
; tx_port to carry the bridge's routing answer.
; &e48d referenced 4 times by &e1a0, &e1b8, &e321, &e339
.build_query_response
    lda rx_src_stn                                                    ; e48d: ad 3e 02    .>.            ; Load querier's station from the received scout
    sta tx_dst_stn                                                    ; e490: 8d 5a 04    .Z.            ; Target the reply back at them as dst_stn
    lda #0                                                            ; e493: a9 00       ..             ; A = 0: local network marker
    sta tx_dst_net                                                    ; e495: 8d 5b 04    .[.            ; dst_net = 0: answer on the querier's local net
    lda #0                                                            ; e498: a9 00       ..             ; A = 0: Bridge has no station identity
    sta tx_src_stn                                                    ; e49a: 8d 5c 04    .\.            ; src_stn = 0 in the reply (unused by Econet routing)
    sta tx_src_net                                                    ; e49d: 8d 5d 04    .].            ; src_net = 0 for now (caller patches to net_num_?)
    lda #&80                                                          ; e4a0: a9 80       ..             ; ctrl = &80: this is a scout, not a data frame
    sta tx_ctrl                                                       ; e4a2: 8d 5e 04    .^.            ; Write ctrl into the frame header
    lda rx_query_port                                                 ; e4a5: ad 48 02    .H.            ; Fetch the reply_port the querier asked for
    sta tx_port                                                       ; e4a8: 8d 5f 04    ._.            ; Write it as the outbound scout's port
    ldx #0                                                            ; e4ab: a2 00       ..             ; X = 0: transmit_frame_? should send 6 bytes exactly
    lda #6                                                            ; e4ad: a9 06       ..             ; Low byte of tx_end: 6-byte frame
    sta tx_end_lo                                                     ; e4af: 8d 00 02    ...            ; Store tx_end_lo
    lda #4                                                            ; e4b2: a9 04       ..             ; High byte of tx_end: page &04
    sta tx_end_hi                                                     ; e4b4: 8d 01 02    ...            ; Store tx_end_hi (end pair = &0406)
    lda #&5a ; 'Z'                                                    ; e4b7: a9 5a       .Z             ; Low byte of mem_ptr: &045A
    sta mem_ptr_lo                                                    ; e4b9: 85 80       ..             ; Store mem_ptr_lo
    lda #4                                                            ; e4bb: a9 04       ..             ; High byte of mem_ptr: page &04
    sta mem_ptr_hi                                                    ; e4bd: 85 81       ..             ; Store mem_ptr_hi; pointer = &045A
    rts                                                               ; e4bf: 60          `              ; Return; caller patches src_net and ctrl/port as needed

; ***************************************************************************************
; Send the frame at mem_ptr out through ADLC B's TX FIFO
;
; Byte-for-byte mirror of transmit_frame_a (&E517) with adlc_a_* replaced by adlc_b_*.
; Everything there applies here -- same entry conditions, same end-pointer semantics
; (tx_end_lo/hi), same X=0/1 trailing-byte flag, same escape-to-main-loop on unexpected
; SR1 state, same normal exit that resets mem_ptr to &045A.
;
; Called from seven sites: reset (&E04E), &E0D8, &E257, &E333, &E34E, &E3D2, &E3DE.
; &e4c0 referenced 7 times by &e04e, &e0d8, &e257, &e333, &e34e, &e3d2, &e3de
.transmit_frame_b
    lda #&e7                                                          ; e4c0: a9 e7       ..             ; A = &E7: prime CR2 for TX (FC_TDRA, 2/1-byte, PSE)
    sta adlc_b_cr2                                                    ; e4c2: 8d 01 d8    ...            ; Commit CR2 on ADLC B
    lda #&44 ; 'D'                                                    ; e4c5: a9 44       .D             ; A = &44: arm CR1 for TX (TX on, RX off for now)
    sta adlc_b_cr1                                                    ; e4c7: 8d 00 d8    ...            ; Commit CR1 on ADLC B
    ldy #0                                                            ; e4ca: a0 00       ..             ; Y = 0: byte offset into the frame buffer
; &e4cc referenced 2 times by &e4ec, &e4f3
.transmit_frame_b_pair_loop
    jsr wait_adlc_b_irq                                               ; e4cc: 20 ea e3     ..            ; Wait for ADLC B IRQ (TDRA = FIFO ready for bytes)
    bit adlc_b_cr1                                                    ; e4cf: 2c 00 d8    ,..            ; BIT SR1 – V flag ← bit 6 (TDRA)
    bvs transmit_frame_b_send_pair                                    ; e4d2: 70 05       p.             ; TDRA set → FIFO has room, send the next pair
; &e4d4 referenced 1 time by &e4ff
.transmit_frame_b_escape
    pla                                                               ; e4d4: 68          h              ; TDRA clear → ADLC state bad; drop return address…
    pla                                                               ; e4d5: 68          h              ; …(second PLA completes the drop)
    jmp main_loop                                                     ; e4d6: 4c 51 e0    LQ.            ; …and escape to main_loop

; &e4d9 referenced 1 time by &e4d2
.transmit_frame_b_send_pair
    lda (mem_ptr_lo),y                                                ; e4d9: b1 80       ..             ; Load frame byte at (mem_ptr),Y
    sta adlc_b_tx                                                     ; e4db: 8d 02 d8    ...            ; Push to ADLC B's TX FIFO
    iny                                                               ; e4de: c8          .              ; Advance Y within page
    lda (mem_ptr_lo),y                                                ; e4df: b1 80       ..             ; Load the next frame byte
    sta adlc_b_tx                                                     ; e4e1: 8d 02 d8    ...            ; Push the second byte of the pair
    iny                                                               ; e4e4: c8          .              ; Advance Y again
    bne transmit_frame_b_end_check                                    ; e4e5: d0 02       ..             ; Non-zero Y → stay on current page
    inc mem_ptr_hi                                                    ; e4e7: e6 81       ..             ; Y wrapped to zero → bump mem_ptr to next page
; &e4e9 referenced 1 time by &e4e5
.transmit_frame_b_end_check
    cpy tx_end_lo                                                     ; e4e9: cc 00 02    ...            ; Compare Y with tx_end_lo
    bne transmit_frame_b_pair_loop                                    ; e4ec: d0 de       ..             ; Still short of end-of-frame low byte → more to send
    lda mem_ptr_hi                                                    ; e4ee: a5 81       ..             ; Load current mem_ptr_hi
    cmp tx_end_hi                                                     ; e4f0: cd 01 02    ...            ; Compare with tx_end_hi
    bcc transmit_frame_b_pair_loop                                    ; e4f3: 90 d7       ..             ; Still on a lower page than the end → more to send
    txa                                                               ; e4f5: 8a          .              ; Recover X (trailing-byte flag) from before the loop
    ror a                                                             ; e4f6: 6a          j              ; Rotate bit 0 into carry
    bcc transmit_frame_b_finish                                       ; e4f7: 90 0d       ..             ; X was even → no trailing byte, skip ahead
    jsr wait_adlc_b_irq                                               ; e4f9: 20 ea e3     ..            ; X was odd → wait for TDRA once more
    bit adlc_b_cr1                                                    ; e4fc: 2c 00 d8    ,..            ; BIT SR1 to test TDRA again
    bvc transmit_frame_b_escape                                       ; e4ff: 50 d3       P.             ; TDRA clear → escape (mirror of &E4D4)
    lda (mem_ptr_lo),y                                                ; e501: b1 80       ..             ; Load the extra trailing byte
    sta adlc_b_tx                                                     ; e503: 8d 02 d8    ...            ; Push trailing byte to TX FIFO
; &e506 referenced 1 time by &e4f7
.transmit_frame_b_finish
    lda #&3f ; '?'                                                    ; e506: a9 3f       .?             ; A = &3F: signal end-of-burst via CR2
    sta adlc_b_cr2                                                    ; e508: 8d 01 d8    ...            ; Commit CR2 – ADLC flushes and flags frame-complete
    jsr wait_adlc_b_irq                                               ; e50b: 20 ea e3     ..            ; Wait for the frame-complete IRQ
    lda #&5a ; 'Z'                                                    ; e50e: a9 5a       .Z             ; A = &5A: reset mem_ptr_lo to &045A base
    sta mem_ptr_lo                                                    ; e510: 85 80       ..             ; Store mem_ptr_lo
    lda #4                                                            ; e512: a9 04       ..             ; A = 4: reset mem_ptr_hi to page &04
    sta mem_ptr_hi                                                    ; e514: 85 81       ..             ; Store mem_ptr_hi – pointer ready for next builder
    rts                                                               ; e516: 60          `              ; Return; the frame has left ADLC B

; ***************************************************************************************
; Send the frame at mem_ptr out through ADLC A's TX FIFO
;
; Sends the frame starting at mem_ptr (&80/&81 – normally pointing at the outbound
; control block &045A) through ADLC A's TX FIFO. Termination is controlled by the
; 16-bit pointer tx_end_lo/tx_end_hi (&0200/&0201): the loop sends byte pairs until
; mem_ptr + Y reaches or passes (tx_end_hi:tx_end_lo). X is a flag – non-zero means
; send one extra trailing byte after the terminator (used by builders that append a
; payload like build_announce_b's net_num_b at &0460).
;
; On entry:
;
; | register / byte | role                                             |
; |-----------------|--------------------------------------------------|
; | mem_ptr_lo/hi   | start address of frame                           |
; | tx_end_lo/hi    | end address (exclusive pair)                     |
; | X               | 0 = no trailing byte, 1 = send one trailing byte |
; | (ADLC A)        | must already be primed by a frame builder        |
;
; On exit (normal RTS):
;
; - mem_ptr_lo/hi reset to &045A, ready for the next builder.
; - ADLC A's TX FIFO flushed, CR2 = &3F.
;
; Abnormal exit: if any of the three wait_adlc_a_irq polls returns with SR1's V-bit
; clear instead of set (meaning the ADLC didn't reach the expected TDRA state), the
; routine drops the caller's return address from the stack and JMP's into main_loop –
; the same escape-to-main pattern used by wait_adlc_a_idle.
;
; Called from seven sites: reset (&E03E), &E0AD, &E1B2, &E1CD, &E251, &E25D, &E3D8.
; &e517 referenced 7 times by &e03e, &e0ad, &e1b2, &e1cd, &e251, &e25d, &e3d8
.transmit_frame_a
    lda #&e7                                                          ; e517: a9 e7       ..             ; A = &E7: prime CR2 for TX (FC_TDRA, 2/1-byte, PSE)
    sta adlc_a_cr2                                                    ; e519: 8d 01 c8    ...            ; Commit CR2 on ADLC A
    lda #&44 ; 'D'                                                    ; e51c: a9 44       .D             ; A = &44: arm CR1 for TX (TX on, RX off for now)
    sta adlc_a_cr1                                                    ; e51e: 8d 00 c8    ...            ; Commit CR1 on ADLC A
    ldy #0                                                            ; e521: a0 00       ..             ; Y = 0: byte offset into the frame buffer
; &e523 referenced 2 times by &e543, &e54a
.transmit_frame_a_pair_loop
    jsr wait_adlc_a_irq                                               ; e523: 20 e4 e3     ..            ; Wait for ADLC A IRQ (TDRA = FIFO ready for bytes)
    bit adlc_a_cr1                                                    ; e526: 2c 00 c8    ,..            ; BIT SR1 – V flag ← bit 6 (TDRA)
    bvs transmit_frame_a_send_pair                                    ; e529: 70 05       p.             ; TDRA set → FIFO has room, send the next pair
; &e52b referenced 1 time by &e556
.transmit_frame_a_escape
    pla                                                               ; e52b: 68          h              ; TDRA clear → ADLC state bad; drop return address…
    pla                                                               ; e52c: 68          h              ; …(second PLA completes the drop)
    jmp main_loop                                                     ; e52d: 4c 51 e0    LQ.            ; …and escape to main_loop

; &e530 referenced 1 time by &e529
.transmit_frame_a_send_pair
    lda (mem_ptr_lo),y                                                ; e530: b1 80       ..             ; Load frame byte at (mem_ptr),Y
    sta adlc_a_tx                                                     ; e532: 8d 02 c8    ...            ; Push to ADLC A's TX FIFO
    iny                                                               ; e535: c8          .              ; Advance Y within page
    lda (mem_ptr_lo),y                                                ; e536: b1 80       ..             ; Load the next frame byte
    sta adlc_a_tx                                                     ; e538: 8d 02 c8    ...            ; Push the second byte of the pair
    iny                                                               ; e53b: c8          .              ; Advance Y again
    bne transmit_frame_a_end_check                                    ; e53c: d0 02       ..             ; Non-zero Y → stay on current page
    inc mem_ptr_hi                                                    ; e53e: e6 81       ..             ; Y wrapped to zero → bump mem_ptr to next page
; &e540 referenced 1 time by &e53c
.transmit_frame_a_end_check
    cpy tx_end_lo                                                     ; e540: cc 00 02    ...            ; Compare Y with tx_end_lo
    bne transmit_frame_a_pair_loop                                    ; e543: d0 de       ..             ; Still short of end-of-frame low byte → more to send
    lda mem_ptr_hi                                                    ; e545: a5 81       ..             ; Load current mem_ptr_hi
    cmp tx_end_hi                                                     ; e547: cd 01 02    ...            ; Compare with tx_end_hi
    bcc transmit_frame_a_pair_loop                                    ; e54a: 90 d7       ..             ; Still on a lower page than the end → more to send
    txa                                                               ; e54c: 8a          .              ; Recover X (trailing-byte flag) from before the loop
    ror a                                                             ; e54d: 6a          j              ; Rotate bit 0 into carry
    bcc transmit_frame_a_finish                                       ; e54e: 90 0d       ..             ; X was even → no trailing byte, skip ahead
    jsr wait_adlc_a_irq                                               ; e550: 20 e4 e3     ..            ; X was odd → wait for TDRA once more
    bit adlc_a_cr1                                                    ; e553: 2c 00 c8    ,..            ; BIT SR1 to test TDRA again
    bvc transmit_frame_a_escape                                       ; e556: 50 d3       P.             ; TDRA clear → escape (mirror of &E52B)
    lda (mem_ptr_lo),y                                                ; e558: b1 80       ..             ; Load the extra trailing byte (tx_data0 in announce frames)
    sta adlc_a_tx                                                     ; e55a: 8d 02 c8    ...            ; Push trailing byte to TX FIFO
; &e55d referenced 1 time by &e54e
.transmit_frame_a_finish
    lda #&3f ; '?'                                                    ; e55d: a9 3f       .?             ; A = &3F: signal end-of-burst via CR2
    sta adlc_a_cr2                                                    ; e55f: 8d 01 c8    ...            ; Commit CR2 – ADLC flushes and flags frame-complete
    jsr wait_adlc_a_irq                                               ; e562: 20 e4 e3     ..            ; Wait for the frame-complete IRQ
    lda #&5a ; 'Z'                                                    ; e565: a9 5a       .Z             ; A = &5A: reset mem_ptr_lo to &045A base
    sta mem_ptr_lo                                                    ; e567: 85 80       ..             ; Store mem_ptr_lo
    lda #4                                                            ; e569: a9 04       ..             ; A = 4: reset mem_ptr_hi to page &04
    sta mem_ptr_hi                                                    ; e56b: 85 81       ..             ; Store mem_ptr_hi – pointer ready for next builder
    rts                                                               ; e56d: 60          `              ; Return; the frame has left ADLC A

; ***************************************************************************************
; Receive a handshake frame on ADLC A and stage it for forward
;
; The receive half of four-way-handshake bridging for the A side. Enables RX on ADLC A,
; drains an inbound frame byte-by-byte into the outbound buffer starting at tx_dst_stn
; (&045A), then sets up tx_end_lo/tx_end_hi so the next call to transmit_frame_b
; transmits the just-received frame out of the other port verbatim.
;
; The drain is capped at top_ram_page (set by the boot RAM test) so very long frames
; fill available RAM and no further.
;
; After the drain, does three pieces of address fix-up on the now-staged frame:
;
; - If tx_src_net (byte 3 of the frame) is zero, fill it with net_num_a. Many Econet
;   senders leave src_net as zero to mean "my local network"; the Bridge makes that
;   explicit before forwarding.
; - Reject the frame if tx_dst_net is zero (no destination network declared) or if
;   reachable_via_b has no entry for that network (we don't know a route).
; - If tx_dst_net equals net_num_b (our own B-side network), normalise it to zero –
;   from side B's perspective the frame is now "local".
;
; On any of the "reject" paths above, and on any sub-step that fails (no AP/RDA, no
; Frame Valid, no response at all), takes the standard escape-to-main-loop exit:
; PLA/PLA/JMP main_loop.
;
; On success, return to the caller with mem_ptr / tx_end_lo / tx_end_hi ready for
; transmit_frame_b (or transmit_frame_a in the reverse direction for queries).
;
; Mirror-image pair with handshake_rx_b (&E5FF): the two routines share identical
; structure with adlc_a_* / adlc_b_* and net_num_a / net_num_b swapped, and are used in
; complementary roles depending on which side the next handshake frame is expected to
; arrive from.
;
; Called from five sites:
;
; | site  | in             | role                                                       |
; |-------|----------------|------------------------------------------------------------|
; | &E1B5 | rx_a_handle_82 | drain the querier's scout-ACK on A                         |
; | &E1D0 | rx_a_handle_82 | drain the querier's final data-ACK on A                    |
; | &E254 | rx_a_forward   | Stage 3 DATA drain from A (originator's data, A → B)       |
; | &E3CF | rx_b_forward   | Stage 2 ACK1 drain from A (destination's scout-ACK, B → A) |
; | &E3DB | rx_b_forward   | Stage 4 ACK2 drain from A (destination's final ACK, B → A) |
; &e56e referenced 5 times by &e1b5, &e1d0, &e254, &e3cf, &e3db
.handshake_rx_a
    lda #&82                                                          ; e56e: a9 82       ..             ; A = &82: TX in reset, RX IRQs enabled
    sta adlc_a_cr1                                                    ; e570: 8d 00 c8    ...            ; Re-arm ADLC A for the incoming handshake frame
    lda #1                                                            ; e573: a9 01       ..             ; A = &01: SR2 mask for AP (Address Present)
    jsr wait_adlc_a_irq                                               ; e575: 20 e4 e3     ..            ; Block until ADLC A raises its first IRQ
    bit adlc_a_cr2                                                    ; e578: 2c 01 c8    ,..            ; BIT SR2 – test AP bit against mask in A
    beq handshake_rx_a_escape                                         ; e57b: f0 34       .4             ; No AP: nothing arrived, escape to main
    lda adlc_a_tx                                                     ; e57d: ad 02 c8    ...            ; Read byte 0 of the handshake frame (dst_stn)
    sta tx_dst_stn                                                    ; e580: 8d 5a 04    .Z.            ; Stage into tx buffer for onward transmission
    jsr wait_adlc_a_irq                                               ; e583: 20 e4 e3     ..            ; Wait for the second RX IRQ (next byte ready)
    bit adlc_a_cr2                                                    ; e586: 2c 01 c8    ,..            ; BIT SR2 – RDA (bit 7) still set?
    bpl handshake_rx_a_escape                                         ; e589: 10 26       .&             ; RDA cleared mid-frame: truncated, escape
    lda adlc_a_tx                                                     ; e58b: ad 02 c8    ...            ; Read byte 1: destination network
    sta tx_dst_net                                                    ; e58e: 8d 5b 04    .[.            ; Stage dst_net into the forward buffer
    ldy #2                                                            ; e591: a0 02       ..             ; Y = 2: start draining pair-payload into (mem_ptr_lo),Y
; &e593 referenced 2 times by &e5a7, &e5af
.handshake_rx_a_pair_loop
    jsr wait_adlc_a_irq                                               ; e593: 20 e4 e3     ..            ; Wait for the next RX byte
    bit adlc_a_cr2                                                    ; e596: 2c 01 c8    ,..            ; BIT SR2 – RDA still asserted?
    bpl handshake_rx_a_drained                                        ; e599: 10 1b       ..             ; End-of-frame detected mid-pair – jump to FV check
    lda adlc_a_tx                                                     ; e59b: ad 02 c8    ...            ; Read even-indexed payload byte
    sta (mem_ptr_lo),y                                                ; e59e: 91 80       ..             ; Store into (mem_ptr_lo)+Y in the staging buffer
    iny                                                               ; e5a0: c8          .              ; Advance Y to odd slot
    lda adlc_a_tx                                                     ; e5a1: ad 02 c8    ...            ; Read odd-indexed payload byte (no IRQ wait: paired)
    sta (mem_ptr_lo),y                                                ; e5a4: 91 80       ..             ; Store into (mem_ptr_lo)+Y
    iny                                                               ; e5a6: c8          .              ; Advance Y; wraps to 0 after 256 bytes
    bne handshake_rx_a_pair_loop                                      ; e5a7: d0 ea       ..             ; Y didn't wrap – stay in this page
    inc mem_ptr_hi                                                    ; e5a9: e6 81       ..             ; Y wrapped: advance mem_ptr_hi to next page
    lda mem_ptr_hi                                                    ; e5ab: a5 81       ..             ; Reload new page number for bounds test
    cmp top_ram_page                                                  ; e5ad: c5 82       ..             ; Compare against top_ram_page (set by boot RAM test)
    bcc handshake_rx_a_pair_loop                                      ; e5af: 90 e2       ..             ; Still room – keep draining into the next page
; &e5b1 referenced 5 times by &e57b, &e589, &e5c5, &e5e4, &e5e9
.handshake_rx_a_escape
    pla                                                               ; e5b1: 68          h              ; Drop caller's return address (lo)
    pla                                                               ; e5b2: 68          h              ; Drop caller's return address (hi)
    jmp main_loop                                                     ; e5b3: 4c 51 e0    LQ.            ; Abandon handshake and rejoin main_loop

; &e5b6 referenced 1 time by &e599
.handshake_rx_a_drained
    lda #0                                                            ; e5b6: a9 00       ..             ; A = &00: halt ADLC A
    sta adlc_a_cr1                                                    ; e5b8: 8d 00 c8    ...            ; CR1 = 0: disable TX and RX IRQs
    lda #&84                                                          ; e5bb: a9 84       ..             ; A = &84: clear-RX-status + FV-clear bits
    sta adlc_a_cr2                                                    ; e5bd: 8d 01 c8    ...            ; Commit CR2: acknowledge the end-of-frame
    lda #2                                                            ; e5c0: a9 02       ..             ; A = &02: mask SR2 bit 1 (Frame Valid)
    bit adlc_a_cr2                                                    ; e5c2: 2c 01 c8    ,..            ; BIT SR2 – test FV and RDA bits together
    beq handshake_rx_a_escape                                         ; e5c5: f0 ea       ..             ; FV clear → frame was corrupt/short, escape
    bpl handshake_rx_a_finalise_len                                   ; e5c7: 10 06       ..             ; FV set but no RDA → clean end, finalise length
    lda adlc_a_tx                                                     ; e5c9: ad 02 c8    ...            ; FV+RDA both set: one trailing byte still pending
    sta (mem_ptr_lo),y                                                ; e5cc: 91 80       ..             ; Store the odd trailing byte into the staging buffer
    iny                                                               ; e5ce: c8          .              ; Advance Y to cover that final byte
; &e5cf referenced 1 time by &e5c7
.handshake_rx_a_finalise_len
    tya                                                               ; e5cf: 98          .              ; A = Y (current byte offset in page)
    tax                                                               ; e5d0: aa          .              ; X = A: preserve raw length for odd-length callers
    and #&fe                                                          ; e5d1: 29 fe       ).             ; Mask low bit: round length DOWN to even
    sta tx_end_lo                                                     ; e5d3: 8d 00 02    ...            ; Store rounded tx_end_lo
    lda tx_src_net                                                    ; e5d6: ad 5d 04    .].            ; Load src_net from the just-drained frame
    bne handshake_rx_a_route_check                                    ; e5d9: d0 06       ..             ; Non-zero → sender supplied src_net, keep it
    lda net_num_a                                                     ; e5db: ad 00 c0    ...            ; Sender left src_net as 0 ('my local net')
    sta tx_src_net                                                    ; e5de: 8d 5d 04    .].            ; Substitute our own A-side network number
; &e5e1 referenced 1 time by &e5d9
.handshake_rx_a_route_check
    ldy tx_dst_net                                                    ; e5e1: ac 5b 04    .[.            ; Load dst_net into Y for routing lookup
    beq handshake_rx_a_escape                                         ; e5e4: f0 cb       ..             ; dst_net = 0 (unspecified) → reject, escape
    lda reachable_via_b,y                                             ; e5e6: b9 5a 02    .Z.            ; Probe reachable_via_b[dst_net]
    beq handshake_rx_a_escape                                         ; e5e9: f0 c6       ..             ; No route via side B → reject, escape
    cpy net_num_b                                                     ; e5eb: cc 00 d0    ...            ; Compare dst_net with our B-side net number
    bne handshake_rx_a_end                                            ; e5ee: d0 05       ..             ; Not us → leave dst_net as-is, skip the rewrite
    lda #0                                                            ; e5f0: a9 00       ..             ; Frame is for the B-side's local network…
    sta tx_dst_net                                                    ; e5f2: 8d 5b 04    .[.            ; …normalise dst_net to 0 for the outbound header
; &e5f5 referenced 1 time by &e5ee
.handshake_rx_a_end
    lda mem_ptr_hi                                                    ; e5f5: a5 81       ..             ; Read final mem_ptr_hi (last page written)
    sta tx_end_hi                                                     ; e5f7: 8d 01 02    ...            ; Record as tx_end_hi (multi-page frames need this)
    lda #4                                                            ; e5fa: a9 04       ..             ; A = &04: reset mem_ptr_hi back to &045A page…
    sta mem_ptr_hi                                                    ; e5fc: 85 81       ..             ; …so the transmit path walks the buffer from byte 0
    rts                                                               ; e5fe: 60          `              ; Return: frame staged, transmitter can send it verbatim

; ***************************************************************************************
; Receive a handshake frame on ADLC B and stage it for forward
;
; The receive half of four-way-handshake bridging for the B side. Enables RX on ADLC B,
; drains an inbound frame byte-by-byte into the outbound buffer starting at tx_dst_stn
; (&045A), then sets up tx_end_lo/tx_end_hi so the next call to transmit_frame_a
; transmits the just-received frame out of the other port verbatim.
;
; The drain is capped at top_ram_page (set by the boot RAM test) so very long frames
; fill available RAM and no further.
;
; After the drain, does three pieces of address fix-up on the now-staged frame:
;
; - If tx_src_net (byte 3 of the frame) is zero, fill it with net_num_b. Many Econet
;   senders leave src_net as zero to mean "my local network"; the Bridge makes that
;   explicit before forwarding.
; - Reject the frame if tx_dst_net is zero (no destination network declared) or if
;   reachable_via_a has no entry for that network (no route).
; - If tx_dst_net equals net_num_a (our own A-side network), normalise it to zero –
;   from side A's perspective the frame is now "local".
;
; On any of the "reject" paths above, and on any sub-step that fails (no AP/RDA, no
; Frame Valid, no response at all), takes the standard escape-to-main-loop exit:
; PLA/PLA/JMP main_loop.
;
; On success, return to the caller with mem_ptr / tx_end_lo / tx_end_hi ready for
; transmit_frame_a (or transmit_frame_b in the reverse direction for queries).
;
; Mirror-image pair with handshake_rx_a (&E56E): the two routines share identical
; structure with adlc_a_* / adlc_b_* and net_num_a / net_num_b swapped, and are used in
; complementary roles depending on which side the next handshake frame is expected to
; arrive from.
;
; Called from five sites:
;
; | site  | in             | role                                                       |
; |-------|----------------|------------------------------------------------------------|
; | &E336 | rx_b_handle_82 | drain the querier's scout-ACK on B                         |
; | &E351 | rx_b_handle_82 | drain the querier's final data-ACK on B                    |
; | &E3D5 | rx_b_forward   | Stage 3 DATA drain from B (originator's data, B → A)       |
; | &E24E | rx_a_forward   | Stage 2 ACK1 drain from B (destination's scout-ACK, A → B) |
; | &E25A | rx_a_forward   | Stage 4 ACK2 drain from B (destination's final ACK, A → B) |
; &e5ff referenced 5 times by &e24e, &e25a, &e336, &e351, &e3d5
.handshake_rx_b
    lda #&82                                                          ; e5ff: a9 82       ..             ; A = &82: TX in reset, RX IRQs enabled
    sta adlc_b_cr1                                                    ; e601: 8d 00 d8    ...            ; Re-arm ADLC B for the incoming handshake frame
    lda #1                                                            ; e604: a9 01       ..             ; A = &01: SR2 mask for AP (Address Present)
    jsr wait_adlc_b_irq                                               ; e606: 20 ea e3     ..            ; Block until ADLC B raises its first IRQ
    bit adlc_b_cr2                                                    ; e609: 2c 01 d8    ,..            ; BIT SR2 – test AP bit against mask in A
    beq handshake_rx_b_escape                                         ; e60c: f0 34       .4             ; No AP: nothing arrived, escape to main
    lda adlc_b_tx                                                     ; e60e: ad 02 d8    ...            ; Read byte 0 of the handshake frame (dst_stn)
    sta tx_dst_stn                                                    ; e611: 8d 5a 04    .Z.            ; Stage into tx buffer for onward transmission
    jsr wait_adlc_b_irq                                               ; e614: 20 ea e3     ..            ; Wait for the second RX IRQ (next byte ready)
    bit adlc_b_cr2                                                    ; e617: 2c 01 d8    ,..            ; BIT SR2 – RDA (bit 7) still set?
    bpl handshake_rx_b_escape                                         ; e61a: 10 26       .&             ; RDA cleared mid-frame: truncated, escape
    lda adlc_b_tx                                                     ; e61c: ad 02 d8    ...            ; Read byte 1: destination network
    sta tx_dst_net                                                    ; e61f: 8d 5b 04    .[.            ; Stage dst_net into the forward buffer
    ldy #2                                                            ; e622: a0 02       ..             ; Y = 2: start draining pair-payload into (mem_ptr_lo),Y
; &e624 referenced 2 times by &e638, &e640
.handshake_rx_b_pair_loop
    jsr wait_adlc_b_irq                                               ; e624: 20 ea e3     ..            ; Wait for the next RX byte
    bit adlc_b_cr2                                                    ; e627: 2c 01 d8    ,..            ; BIT SR2 – RDA still asserted?
    bpl handshake_rx_b_drained                                        ; e62a: 10 1b       ..             ; End-of-frame detected mid-pair – jump to FV check
    lda adlc_b_tx                                                     ; e62c: ad 02 d8    ...            ; Read even-indexed payload byte
    sta (mem_ptr_lo),y                                                ; e62f: 91 80       ..             ; Store into (mem_ptr_lo)+Y in the staging buffer
    iny                                                               ; e631: c8          .              ; Advance Y to odd slot
    lda adlc_b_tx                                                     ; e632: ad 02 d8    ...            ; Read odd-indexed payload byte (no IRQ wait: paired)
    sta (mem_ptr_lo),y                                                ; e635: 91 80       ..             ; Store into (mem_ptr_lo)+Y
    iny                                                               ; e637: c8          .              ; Advance Y; wraps to 0 after 256 bytes
    bne handshake_rx_b_pair_loop                                      ; e638: d0 ea       ..             ; Y didn't wrap – stay in this page
    inc mem_ptr_hi                                                    ; e63a: e6 81       ..             ; Y wrapped: advance mem_ptr_hi to next page
    lda mem_ptr_hi                                                    ; e63c: a5 81       ..             ; Reload new page number for bounds test
    cmp top_ram_page                                                  ; e63e: c5 82       ..             ; Compare against top_ram_page (set by boot RAM test)
    bcc handshake_rx_b_pair_loop                                      ; e640: 90 e2       ..             ; Still room – keep draining into the next page
; &e642 referenced 5 times by &e60c, &e61a, &e656, &e675, &e67a
.handshake_rx_b_escape
    pla                                                               ; e642: 68          h              ; Drop caller's return address (lo)
    pla                                                               ; e643: 68          h              ; Drop caller's return address (hi)
    jmp main_loop                                                     ; e644: 4c 51 e0    LQ.            ; Abandon handshake and rejoin main_loop

; &e647 referenced 1 time by &e62a
.handshake_rx_b_drained
    lda #0                                                            ; e647: a9 00       ..             ; A = &00: halt ADLC B
    sta adlc_b_cr1                                                    ; e649: 8d 00 d8    ...            ; CR1 = 0: disable TX and RX IRQs
    lda #&84                                                          ; e64c: a9 84       ..             ; A = &84: clear-RX-status + FV-clear bits
    sta adlc_b_cr2                                                    ; e64e: 8d 01 d8    ...            ; Commit CR2: acknowledge the end-of-frame
    lda #2                                                            ; e651: a9 02       ..             ; A = &02: mask SR2 bit 1 (Frame Valid)
    bit adlc_b_cr2                                                    ; e653: 2c 01 d8    ,..            ; BIT SR2 – test FV and RDA bits together
    beq handshake_rx_b_escape                                         ; e656: f0 ea       ..             ; FV clear → frame was corrupt/short, escape
    bpl handshake_rx_b_finalise_len                                   ; e658: 10 06       ..             ; FV set but no RDA → clean end, finalise length
    lda adlc_b_tx                                                     ; e65a: ad 02 d8    ...            ; FV+RDA both set: one trailing byte still pending
    sta (mem_ptr_lo),y                                                ; e65d: 91 80       ..             ; Store the odd trailing byte into the staging buffer
    iny                                                               ; e65f: c8          .              ; Advance Y to cover that final byte
; &e660 referenced 1 time by &e658
.handshake_rx_b_finalise_len
    tya                                                               ; e660: 98          .              ; A = Y (current byte offset in page)
    tax                                                               ; e661: aa          .              ; X = A: preserve raw length for odd-length callers
    and #&fe                                                          ; e662: 29 fe       ).             ; Mask low bit: round length DOWN to even
    sta tx_end_lo                                                     ; e664: 8d 00 02    ...            ; Store rounded tx_end_lo
    lda tx_src_net                                                    ; e667: ad 5d 04    .].            ; Load src_net from the just-drained frame
    bne handshake_rx_b_route_check                                    ; e66a: d0 06       ..             ; Non-zero → sender supplied src_net, keep it
    lda net_num_b                                                     ; e66c: ad 00 d0    ...            ; Sender left src_net as 0 ('my local net')
    sta tx_src_net                                                    ; e66f: 8d 5d 04    .].            ; Substitute our own B-side network number
; &e672 referenced 1 time by &e66a
.handshake_rx_b_route_check
    ldy tx_dst_net                                                    ; e672: ac 5b 04    .[.            ; Load dst_net into Y for routing lookup
    beq handshake_rx_b_escape                                         ; e675: f0 cb       ..             ; dst_net = 0 (unspecified) → reject, escape
    lda reachable_via_a,y                                             ; e677: b9 5a 03    .Z.            ; Probe reachable_via_a[dst_net]
    beq handshake_rx_b_escape                                         ; e67a: f0 c6       ..             ; No route via side A → reject, escape
    cpy net_num_a                                                     ; e67c: cc 00 c0    ...            ; Compare dst_net with our A-side net number
    bne handshake_rx_b_end                                            ; e67f: d0 05       ..             ; Not us → leave dst_net as-is, skip the rewrite
    lda #0                                                            ; e681: a9 00       ..             ; Frame is for the A-side's local network…
    sta tx_dst_net                                                    ; e683: 8d 5b 04    .[.            ; …normalise dst_net to 0 for the outbound header
; &e686 referenced 1 time by &e67f
.handshake_rx_b_end
    lda mem_ptr_hi                                                    ; e686: a5 81       ..             ; Read final mem_ptr_hi (last page written)
    sta tx_end_hi                                                     ; e688: 8d 01 02    ...            ; Record as tx_end_hi (multi-page frames need this)
    lda #4                                                            ; e68b: a9 04       ..             ; A = &04: reset mem_ptr_hi back to &045A page…
    sta mem_ptr_hi                                                    ; e68d: 85 81       ..             ; …so the transmit path walks the buffer from byte 0
    rts                                                               ; e68f: 60          `              ; Return: frame staged, transmitter can send it verbatim

; ***************************************************************************************
; Wait for ADLC B's line to go idle (CSMA) or escape
;
; Byte-for-byte mirror of wait_adlc_a_idle (&E6DC) with adlc_a_* replaced by adlc_b_*.
; Same pre-transmit carrier-sense semantics: wait for SR2 bit 2 (Rx Idle), back off on
; AP/RDA, escape to main_loop on ~131K-iteration timeout.
;
; Called from four sites: reset (&E04B), &E0D5, &E211, &E330.
; &e690 referenced 4 times by &e04b, &e0d5, &e211, &e330
.wait_adlc_b_idle
    lda #0                                                            ; e690: a9 00       ..             ; A = 0: seed the 24-bit timeout counter
    sta ctr24_lo                                                      ; e692: 8d 14 02    ...            ; Clear timeout counter low byte
    sta ctr24_mid                                                     ; e695: 8d 15 02    ...            ; Clear timeout counter mid byte
    lda #&fe                                                          ; e698: a9 fe       ..             ; A = &FE: seed for the high byte (~131K iterations)
    sta ctr24_hi                                                      ; e69a: 8d 16 02    ...            ; Store timeout high; counter = &00_00_FE counting up
    lda adlc_b_cr2                                                    ; e69d: ad 01 d8    ...            ; Read SR2 (result discarded; flags irrelevant here)
    ldy #&e7                                                          ; e6a0: a0 e7       ..             ; Y = &E7: CR2 value to arm the chip on Rx-Idle exit
; &e6a2 referenced 3 times by &e6c2, &e6c7, &e6cc
.wait_adlc_b_idle_loop
    lda #&67 ; 'g'                                                    ; e6a2: a9 67       .g             ; A = &67: standard listen-mode CR2 value
    sta adlc_b_cr2                                                    ; e6a4: 8d 01 d8    ...            ; Re-prime CR2 – clears any stale status bits
    lda #4                                                            ; e6a7: a9 04       ..             ; A = &04: mask for SR2 bit 2 (Rx Idle / line quiet)
    bit adlc_b_cr2                                                    ; e6a9: 2c 01 d8    ,..            ; Test SR2 bit 2 via BIT
    bne wait_adlc_b_idle_ready                                        ; e6ac: d0 25       .%             ; Bit set → line idle; we can transmit (exit)
    lda adlc_b_cr2                                                    ; e6ae: ad 01 d8    ...            ; Read SR2 into A for the mask test below
    and #&81                                                          ; e6b1: 29 81       ).             ; Mask AP (bit 0) + RDA (bit 7) – someone else talking?
    beq wait_adlc_b_idle_tick                                         ; e6b3: f0 0a       ..             ; Neither set → still quiet-ish, just increment counter
    lda #&c2                                                          ; e6b5: a9 c2       ..             ; Mask: reset TX, RX active
    sta adlc_b_cr1                                                    ; e6b7: 8d 00 d8    ...            ; Abort our pending TX on ADLC B (yield to other station)
    lda #&82                                                          ; e6ba: a9 82       ..             ; Mask: TX still reset, RX IRQ enabled
    sta adlc_b_cr1                                                    ; e6bc: 8d 00 d8    ...            ; Keep CR1 in TX-reset state for another pass
; &e6bf referenced 1 time by &e6b3
.wait_adlc_b_idle_tick
    inc ctr24_lo                                                      ; e6bf: ee 14 02    ...            ; Bump timeout counter (LSB first)
    bne wait_adlc_b_idle_loop                                         ; e6c2: d0 de       ..             ; Low byte didn't wrap → keep polling
    inc ctr24_mid                                                     ; e6c4: ee 15 02    ...            ; Bump mid byte
    bne wait_adlc_b_idle_loop                                         ; e6c7: d0 d9       ..             ; Mid byte didn't wrap → keep polling
    inc ctr24_hi                                                      ; e6c9: ee 16 02    ...            ; Bump high byte
    bne wait_adlc_b_idle_loop                                         ; e6cc: d0 d4       ..             ; High byte didn't wrap → keep polling
    pla                                                               ; e6ce: 68          h              ; Counter overflowed – drop caller's return address…
    pla                                                               ; e6cf: 68          h              ; …(second PLA completes the return-address drop)
    jmp main_loop                                                     ; e6d0: 4c 51 e0    LQ.            ; …and escape to main_loop without returning

; &e6d3 referenced 1 time by &e6ac
.wait_adlc_b_idle_ready
    sty adlc_b_cr2                                                    ; e6d3: 8c 01 d8    ...            ; STY: arm CR2 with &E7 (from Y) – TX-ready listen state
    lda #&44 ; 'D'                                                    ; e6d6: a9 44       .D             ; Mask: arm CR1 for transmit (TX on, IRQ off)
    sta adlc_b_cr1                                                    ; e6d8: 8d 00 d8    ...            ; Commit CR1; ADLC B ready to send
    rts                                                               ; e6db: 60          `              ; Normal return: caller transmits the frame

; ***************************************************************************************
; Wait for ADLC A's line to go idle (CSMA) or escape
;
; Pre-transmit carrier-sense: polls ADLC A's SR2 until the Rx Idle bit goes high (SR2
; bit 2 = 15+ consecutive 1s received, i.e. the line is quiet and it is safe to start a
; frame). A 24-bit timeout counter at ctr24_lo/mid/hi (&0214-&0216) starts at &00_00_FE
; and increments LSB-first; overflow takes ~131K iterations, a few seconds at typical
; bus speeds.
;
; Each iteration re-primes CR2 with &67 (clear TX/RX status, FC_TDRA, 2/1-byte, PSE)
; then reads SR2. Three outcomes:
;
; - SR2 bit 2 set (Rx Idle): line is quiet. Arm CR2=&E7 and CR1=&44, RTS – caller
;   proceeds to transmit.
; - SR2 bit 0 or bit 7 set (AP or RDA): another station is sending into this ADLC. Back
;   off by cycling CR1 through &C2 → &82 (reset TX without touching RX) and keep
;   polling. The Bridge is not the right place to assert on a busy line.
; - Timeout (counter overflows without ever seeing Rx Idle): PLA/PLA discards the
;   caller's saved return address from the stack and JMP main_loop escapes into the
;   main Bridge loop. The code between the caller's JSR and the main loop is skipped
;   entirely. See docs/analysis/escape-to-main-control-flow.md.
;
; Called from four sites, always immediately before a transmit: reset (&E03B, before
; transmit_frame_a), &E0AA, &E1AF, &E392.
; &e6dc referenced 4 times by &e03b, &e0aa, &e1af, &e392
.wait_adlc_a_idle
    lda #0                                                            ; e6dc: a9 00       ..             ; A = 0: seed the 24-bit timeout counter
    sta ctr24_lo                                                      ; e6de: 8d 14 02    ...            ; Clear timeout counter low byte
    sta ctr24_mid                                                     ; e6e1: 8d 15 02    ...            ; Clear timeout counter mid byte
    lda #&fe                                                          ; e6e4: a9 fe       ..             ; A = &FE: seed for the high byte (gives ~131K iterations)
    sta ctr24_hi                                                      ; e6e6: 8d 16 02    ...            ; Store timeout high; counter = &00_00_FE counting up
    lda adlc_a_cr2                                                    ; e6e9: ad 01 c8    ...            ; Read SR2 (result discarded; flags irrelevant here)
    ldy #&e7                                                          ; e6ec: a0 e7       ..             ; Y = &E7: CR2 value arm the chip with on Rx-Idle exit
; &e6ee referenced 3 times by &e70e, &e713, &e718
.wait_adlc_a_idle_loop
    lda #&67 ; 'g'                                                    ; e6ee: a9 67       .g             ; A = &67: standard listen-mode CR2 value
    sta adlc_a_cr2                                                    ; e6f0: 8d 01 c8    ...            ; Re-prime CR2 – clears any stale status bits
    lda #4                                                            ; e6f3: a9 04       ..             ; A = &04: mask for SR2 bit 2 (Rx Idle / line quiet)
    bit adlc_a_cr2                                                    ; e6f5: 2c 01 c8    ,..            ; Test SR2 bit 2 via BIT
    bne wait_adlc_a_idle_ready                                        ; e6f8: d0 25       .%             ; Bit set → line idle; we can transmit (exit)
    lda adlc_a_cr2                                                    ; e6fa: ad 01 c8    ...            ; Read SR2 into A for the mask test below
    and #&81                                                          ; e6fd: 29 81       ).             ; Mask AP (bit 0) + RDA (bit 7) – someone else talking?
    beq wait_adlc_a_idle_tick                                         ; e6ff: f0 0a       ..             ; Neither set → still quiet-ish, just increment counter
    lda #&c2                                                          ; e701: a9 c2       ..             ; Mask: reset TX, RX active
    sta adlc_a_cr1                                                    ; e703: 8d 00 c8    ...            ; Abort our pending TX on ADLC A (yield to the other station)
    lda #&82                                                          ; e706: a9 82       ..             ; Mask: TX still reset, RX IRQ enabled
    sta adlc_a_cr1                                                    ; e708: 8d 00 c8    ...            ; Keep CR1 in TX-reset state for another pass
; &e70b referenced 1 time by &e6ff
.wait_adlc_a_idle_tick
    inc ctr24_lo                                                      ; e70b: ee 14 02    ...            ; Bump timeout counter (LSB first)
    bne wait_adlc_a_idle_loop                                         ; e70e: d0 de       ..             ; Low byte didn't wrap → keep polling
    inc ctr24_mid                                                     ; e710: ee 15 02    ...            ; Bump mid byte
    bne wait_adlc_a_idle_loop                                         ; e713: d0 d9       ..             ; Mid byte didn't wrap → keep polling
    inc ctr24_hi                                                      ; e715: ee 16 02    ...            ; Bump high byte
    bne wait_adlc_a_idle_loop                                         ; e718: d0 d4       ..             ; High byte didn't wrap → keep polling
    pla                                                               ; e71a: 68          h              ; Counter overflowed – drop caller's return address…
    pla                                                               ; e71b: 68          h              ; …(second PLA completes the return-address drop)
    jmp main_loop                                                     ; e71c: 4c 51 e0    LQ.            ; …and escape to main_loop without returning

; &e71f referenced 1 time by &e6f8
.wait_adlc_a_idle_ready
    sty adlc_a_cr2                                                    ; e71f: 8c 01 c8    ...            ; STY: arm CR2 with &E7 (from Y) – TX-ready listen state
    lda #&44 ; 'D'                                                    ; e722: a9 44       .D             ; Mask: arm CR1 for transmit (TX on, IRQ off)
    sta adlc_a_cr1                                                    ; e724: 8d 00 c8    ...            ; Commit CR1; ADLC A ready to send
    rts                                                               ; e727: 60          `              ; Normal return: caller transmits the frame

; ***************************************************************************************
; ROM body gap – unused space before the self-test
;
; 2264 bytes of &FF padding between the end of the main code at wait_adlc_a_idle_ready
; and the start of the self-test entry at self_test (&F000).
;
; The region is simply the unused tail of the main-code half of the ROM, before the
; self-test at the page-aligned &F000.
.rom_body_gap
    for _py8dis_fill_n%, 1, 2264 : equb &ff : next                    ; e728: ff ff ff... ...

; ***************************************************************************************
; Self-test entry (IRQ/BRK vector target)
;
; Invoked by pressing the self-test push-button on the 6502 ~IRQ line (and, implicitly,
; by any BRK instruction in the ROM). Runs through a sequence of hardware checks,
; signalling any failure via self_test_fail (&F2C7) with an error code in A.
;
; Not to be pressed while the Bridge is connected to a live network: the self-test
; reconfigures the ADLCs and drives their control registers in ways that will disturb
; any in-flight frames.
;
; The official self-test rig is a minimal Econet segment, not a full one. It comprises
; a clock box (which on the original Acorn/SJ design provides only the bit-clock, not
; biasing), a T-piece joining both Bridge ports to one cable to the clock box, and a
; single terminator on the clock box's other socket. The terminator does double duty:
; it terminates the line and provides the DC bias that lets the differential pair carry
; data at all. One terminator is enough to bias the line for the loopback test to work,
; which is why the rig has just one – a real two-station Econet segment would have a
; terminator at each end of the cable run. A bare port-to-port patch cable will not
; work: without clock and without bias the loopback tests can never see a frame. See
; docs/self-test-connections.png for the manual's diagram.
.self_test
    sei                                                               ; f000: 78          x              ; Mask IRQs – this routine polls and must not re-enter
    lda #0                                                            ; f001: a9 00       ..             ; A = 0: initial value for the scratch pass-phase flag
    sta st_pass_phase                                                 ; f003: 85 03       ..             ; &03 = pass-phase; toggled by self_test_pass_done
; ***************************************************************************************
; Reset both ADLCs and extinguish the status LED
;
; Byte-for-byte identical to the adlc_*_full_reset pair except for one crucial detail:
; CR3 is programmed to &80 (bit 7 set) instead of &00. CR3 bit 7 is the MC6854's
; LOC/DTR control bit, and the pin it drives is inverted relative to the bit – when the
; control bit is HIGH, the pin output goes LOW. On ADLC B (IC18) that pin sources
; current through the front-panel status LED (anode tied to the pin, cathode to
; ground), so CR3 bit 7 = 1 leaves the LED dark. The LED is therefore extinguished at
; the start of every normal self-test pass, marking the transition out of
; normal-operation steady-on. ADLC A's LOC/DTR pin is not wired and gets the same write
; for code symmetry only.
;
; The LED does not stay dark for the whole test pass: the loopback tests at
; self_test_loopback_a_to_b and self_test_loopback_b_to_a each begin with a full ADLC
; reset (CR1 = &C0 on both chips), and that reset clears CR3 bit 7 back to 0 – which
; lights the LED again for the rest of the pass. The visible flash the operator sees
; during a healthy self-test is the alternation between this dark "early-tests" phase
; and the lit "loopback-and-after" phase, modulated by the two-pass structure described
; at self_test_pass_done.
;
; Re-entered at &F26C after each "normal" pass completes; the alternate path at
; self_test_alt_pass deliberately skips this routine on every other pass, leaving B's
; CR3 bit 7 cleared from the previous loopback reset (so the alt-pass runs entirely in
; the LED-lit state).
; &f005 referenced 1 time by &f26c
.self_test_reset_adlcs
    lda #&c1                                                          ; f005: a9 c1       ..             ; Mask: reset TX+RX, AC=1 to reach CR3/CR4
    sta adlc_a_cr1                                                    ; f007: 8d 00 c8    ...            ; Drop ADLC A into full reset
    sta adlc_b_cr1                                                    ; f00a: 8d 00 d8    ...            ; Drop ADLC B into full reset
    lda #&1e                                                          ; f00d: a9 1e       ..             ; Mask: 8-bit RX, abort-extend, NRZ encoding
    sta adlc_a_tx2                                                    ; f00f: 8d 03 c8    ...            ; Program ADLC A's CR4 (via tx2 while AC=1)
    sta adlc_b_tx2                                                    ; f012: 8d 03 d8    ...            ; Program ADLC B's CR4
    lda #&80                                                          ; f015: a9 80       ..             ; Mask &80: CR3 bit 7 = drive LOC/DTR low → LED OFF
    sta adlc_a_cr2                                                    ; f017: 8d 01 c8    ...            ; Program ADLC A's CR3 (pin not wired; no effect)
    lda #&80                                                          ; f01a: a9 80       ..             ; Mask &80 again (separate load for symmetry)
    sta adlc_b_cr2                                                    ; f01c: 8d 01 d8    ...            ; Program ADLC B's CR3 – extinguishes the status LED
    lda #&82                                                          ; f01f: a9 82       ..             ; Mask: TX in reset, RX IRQ enabled, AC=0
    sta adlc_a_cr1                                                    ; f021: 8d 00 c8    ...            ; Release CR1 AC bit on ADLC A (CR3 value sticks)
    sta adlc_b_cr1                                                    ; f024: 8d 00 d8    ...            ; Release CR1 AC bit on ADLC B (CR3 value sticks)
    lda #&67 ; 'g'                                                    ; f027: a9 67       .g             ; Mask: clear status, FC_TDRA, 2/1-byte, PSE
    sta adlc_a_cr2                                                    ; f029: 8d 01 c8    ...            ; Commit CR2 on ADLC A
    sta adlc_b_cr2                                                    ; f02c: 8d 01 d8    ...            ; Commit CR2 on ADLC B; falls through to ZP test
; ***************************************************************************************
; Zero-page integrity test (&00-&02)
;
; Writes &55 to &00, &01, &02 and reads them back; then &AA and reads back. Failure
; jumps to ram_test_fail (via self_test_ram_fail_jump, because RAM isn't trustworthy
; enough at this point to use a countable blink).
;
; Tests only the three ZP bytes that are used as scratch by the later self-test stages
; (ROM checksum, RAM scan). A full ZP test isn't needed – the main reset handler has
; already exercised ZP indirectly via ram_test.
; &f02f referenced 1 time by &f289
.self_test_zp
    lda #&55 ; 'U'                                                    ; f02f: a9 55       .U             ; First test pattern = &55 (0101_0101)
; &f031 referenced 1 time by &f049
.self_test_zp_write_read
    sta st_ptr_lo                                                     ; f031: 85 00       ..             ; Write pattern to scratch byte &00
    sta st_ptr_hi                                                     ; f033: 85 01       ..             ; Write pattern to scratch byte &01
    sta st_page_count                                                 ; f035: 85 02       ..             ; Write pattern to scratch byte &02
    cmp st_ptr_lo                                                     ; f037: c5 00       ..             ; Check &00 still reads as pattern
    bne self_test_ram_fail_jump                                       ; f039: d0 62       .b             ; Mismatch → ram_test_fail (distinct blink pattern)
    cmp st_ptr_hi                                                     ; f03b: c5 01       ..             ; Check &01 still reads as pattern
    bne self_test_ram_fail_jump                                       ; f03d: d0 5e       .^             ; Mismatch → ram_test_fail
    cmp st_page_count                                                 ; f03f: c5 02       ..             ; Check &02 still reads as pattern
    bne self_test_ram_fail_jump                                       ; f041: d0 5a       .Z             ; Mismatch → ram_test_fail
    cmp #&aa                                                          ; f043: c9 aa       ..             ; Was the pattern &AA? then both halves passed
    beq self_test_rom_checksum                                        ; f045: f0 05       ..             ; Yes → continue to ROM checksum
    lda #&aa                                                          ; f047: a9 aa       ..             ; Second test pattern = &AA (1010_1010)
    jmp self_test_zp_write_read                                       ; f049: 4c 31 f0    L1.            ; Loop back to rerun the three-byte check

;
; ***************************************************************************************
; ROM checksum
;
; Sums every byte of the 8 KiB ROM modulo 256 using a running A accumulator. Expected
; total is &55; on mismatch, jumps to self_test_fail with A=2.
;
; Runtime pointer in &00/&01 starts at &E000; &02 holds the page counter (32 pages = 8
; KiB). The required total is balanced on-disc by the rom_checksum_adjust byte at
; &FFF0, hand-tuned to make the ROM-wide sum land on &55.
; &f04c referenced 1 time by &f045
.self_test_rom_checksum
    lda #0                                                            ; f04c: a9 00       ..             ; A = 0: low byte of the ROM pointer
    sta st_ptr_lo                                                     ; f04e: 85 00       ..             ; Store pointer_lo = 0
    lda #&20 ; ' '                                                    ; f050: a9 20       .              ; A = &20: 32 pages remaining to sum
    sta st_page_count                                                 ; f052: 85 02       ..             ; Store page counter
    lda #&e0                                                          ; f054: a9 e0       ..             ; A = &E0: pointer_hi starts at ROM base &E000
    sta st_ptr_hi                                                     ; f056: 85 01       ..             ; Store pointer_hi = &E0
    ldy #0                                                            ; f058: a0 00       ..             ; Y = 0: within-page byte offset
    tya                                                               ; f05a: 98          .              ; A = 0: seed the running sum
; &f05b referenced 2 times by &f05f, &f065
.self_test_rom_checksum_loop
    clc                                                               ; f05b: 18          .              ; Clear carry before the addition
    adc (st_ptr_lo),y                                                 ; f05c: 71 00       q.             ; Add next ROM byte at (pointer),Y into running sum
    iny                                                               ; f05e: c8          .              ; Advance to next byte within the page
    bne self_test_rom_checksum_loop                                   ; f05f: d0 fa       ..             ; Loop 256 times through the current page
    inc st_ptr_hi                                                     ; f061: e6 01       ..             ; Roll the pointer to the next 256-byte page
    dec st_page_count                                                 ; f063: c6 02       ..             ; One page done; decrement the page counter
    bne self_test_rom_checksum_loop                                   ; f065: d0 f4       ..             ; Loop until all 32 ROM pages have been summed
    cmp #&55 ; 'U'                                                    ; f067: c9 55       .U             ; Compare running sum with the expected &55
    beq self_test_ram_pattern                                         ; f069: f0 05       ..             ; Match → ROM is intact, proceed to RAM test
    lda #2                                                            ; f06b: a9 02       ..             ; Mismatch: load error code 2 (ROM checksum fail)
    jmp self_test_fail                                                ; f06d: 4c c7 f2    L..            ; Jump to the countable-blink failure handler

; ***************************************************************************************
; RAM pattern test: write &55/&AA to every byte, verify
;
; Starting at address &0004 (skipping the three zero-page bytes reserved for the
; self-test workspace at &00/&01/&02), iterates through the full 8 KiB of RAM and
; checks that each byte can store both &55 and &AA. Pointer in (&00,&01) = &0000, Y
; starts at 4 and wraps, page count in &02 = &20 (32 pages = 8 KiB).
;
; On mismatch, jumps to ram_test_fail (&F28C) – a different failure handler from
; self_test_fail, because a broken RAM cannot use the normal blink-code loop which
; needs RAM workspace.
; &f070 referenced 1 time by &f069
.self_test_ram_pattern
    lda #0                                                            ; f070: a9 00       ..             ; A = 0: low byte of the RAM-test indirect pointer
    sta st_ptr_lo                                                     ; f072: 85 00       ..             ; Store pointer_lo
    lda #0                                                            ; f074: a9 00       ..             ; A = 0: high byte – start scanning at RAM base
    sta st_ptr_hi                                                     ; f076: 85 01       ..             ; Store pointer_hi
    lda #&20 ; ' '                                                    ; f078: a9 20       .              ; A = &20: 32 pages to cover (the full 8 KiB)
    sta st_page_count                                                 ; f07a: 85 02       ..             ; Store page counter
    ldy #4                                                            ; f07c: a0 04       ..             ; Y = 4: skip &0000-&0003 (self-test scratch)
; &f07e referenced 2 times by &f093, &f099
.self_test_ram_pattern_loop
    lda #&55 ; 'U'                                                    ; f07e: a9 55       .U             ; First pattern = &55 (alternating 1-0 nibbles)
    sta (st_ptr_lo),y                                                 ; f080: 91 00       ..             ; Write pattern to the current RAM byte
    lda (st_ptr_lo),y                                                 ; f082: b1 00       ..             ; Read the same byte back
    cmp #&55 ; 'U'                                                    ; f084: c9 55       .U             ; Verify the cell held the written pattern
    bne self_test_ram_fail_jump                                       ; f086: d0 15       ..             ; Mismatch → ram_test_fail (unreliable storage)
    lda #&aa                                                          ; f088: a9 aa       ..             ; Second pattern = &AA (the bitwise complement)
    sta (st_ptr_lo),y                                                 ; f08a: 91 00       ..             ; Write complement to catch stuck-bit faults
    lda (st_ptr_lo),y                                                 ; f08c: b1 00       ..             ; Read it back
    cmp #&aa                                                          ; f08e: c9 aa       ..             ; Verify
    bne self_test_ram_fail_jump                                       ; f090: d0 0b       ..             ; Mismatch → ram_test_fail
    iny                                                               ; f092: c8          .              ; Advance to next byte within the page
    bne self_test_ram_pattern_loop                                    ; f093: d0 e9       ..             ; Loop 256 times through the current page
    inc st_ptr_hi                                                     ; f095: e6 01       ..             ; Advance to the next page
    dec st_page_count                                                 ; f097: c6 02       ..             ; One page done; decrement the remaining-page count
    bne self_test_ram_pattern_loop                                    ; f099: d0 e3       ..             ; Continue until all 32 pages verified
    beq self_test_ram_incr                                            ; f09b: f0 03       ..             ; All 8 KiB good – fall through to the incrementing test

; &f09d referenced 6 times by &f039, &f03d, &f041, &f086, &f090, &f0c9
.self_test_ram_fail_jump
    jmp ram_test_fail                                                 ; f09d: 4c 8c f2    L..            ; Any RAM check mismatch lands here; forward to blinker

; ***************************************************************************************
; RAM incrementing-pattern test: fill with X, read back
;
; Second RAM test. Fills the whole 8 KiB with an incrementing byte pattern (X register
; cycles through 0..&FF and then reinitialised each page with a different offset,
; giving a distinctive pattern across the RAM that catches address-line faults). Then
; reads back and verifies.
;
; Catches failures that a plain &55/&AA pattern would miss: particularly address-line
; shorts, where writing to (say) &0410 and &0420 would land at the same cell and
; produce the same bytes under a uniform pattern but different bytes under this one.
;
; On mismatch, jumps to ram_test_fail (&F28C).
; &f0a0 referenced 1 time by &f09b
.self_test_ram_incr
    lda #0                                                            ; f0a0: a9 00       ..             ; A = 0: low byte of the pointer stays zero
    sta st_ptr_hi                                                     ; f0a2: 85 01       ..             ; Reset pointer_hi to RAM base for the fill phase
    lda #&20 ; ' '                                                    ; f0a4: a9 20       .              ; A = &20: full 32-page coverage again
    sta st_page_count                                                 ; f0a6: 85 02       ..             ; Store the page counter
    ldy #4                                                            ; f0a8: a0 04       ..             ; Y = 4: skip the self-test scratch bytes
    ldx #0                                                            ; f0aa: a2 00       ..             ; X = 0: seed the fill value
; &f0ac referenced 2 times by &f0b1, &f0b8
.self_test_ram_incr_fill
    txa                                                               ; f0ac: 8a          .              ; A = X: the current fill value
    sta (st_ptr_lo),y                                                 ; f0ad: 91 00       ..             ; Write it to RAM via the indirect pointer
    inx                                                               ; f0af: e8          .              ; Increment fill value (wraps naturally at 256)
    iny                                                               ; f0b0: c8          .              ; Advance to next byte in the page
    bne self_test_ram_incr_fill                                       ; f0b1: d0 f9       ..             ; Loop 256 times through the page
    inc st_ptr_hi                                                     ; f0b3: e6 01       ..             ; Advance to next page
    inx                                                               ; f0b5: e8          .              ; Bump fill value by one extra per page – different offset
    dec st_page_count                                                 ; f0b6: c6 02       ..             ; Decrement page counter
    bne self_test_ram_incr_fill                                       ; f0b8: d0 f2       ..             ; Continue filling all 32 pages
    lda #0                                                            ; f0ba: a9 00       ..             ; Fill done; now reset state for the verify phase
    sta st_ptr_hi                                                     ; f0bc: 85 01       ..             ; pointer_hi back to RAM base
    lda #&20 ; ' '                                                    ; f0be: a9 20       .              ; A = &20: 32 pages again
    sta st_page_count                                                 ; f0c0: 85 02       ..             ; Store page counter
    ldy #4                                                            ; f0c2: a0 04       ..             ; Y = 4: skip scratch bytes
    ldx #0                                                            ; f0c4: a2 00       ..             ; X = 0: expected value follows the same sequence
; &f0c6 referenced 2 times by &f0cd, &f0d4
.self_test_ram_incr_verify
    txa                                                               ; f0c6: 8a          .              ; A = X: expected byte value
    cmp (st_ptr_lo),y                                                 ; f0c7: d1 00       ..             ; Compare with what we actually wrote and read back
    bne self_test_ram_fail_jump                                       ; f0c9: d0 d2       ..             ; Mismatch → ram_test_fail (via &F09D)
    inx                                                               ; f0cb: e8          .              ; Step expected value
    iny                                                               ; f0cc: c8          .              ; Step byte offset
    bne self_test_ram_incr_verify                                     ; f0cd: d0 f7       ..             ; Loop through the page
    inc st_ptr_hi                                                     ; f0cf: e6 01       ..             ; Advance to next page
    inx                                                               ; f0d1: e8          .              ; Bump offset between pages (match fill pattern)
    dec st_page_count                                                 ; f0d2: c6 02       ..             ; One page verified; decrement
    bne self_test_ram_incr_verify                                     ; f0d4: d0 f0       ..             ; Continue through all 32 pages; falls through on success
; ***************************************************************************************
; Verify both ADLCs' register state after reset
;
; Checks that both ADLCs show the expected register state after self_test_reset_adlcs
; has configured them. Tests specific bits of SR1 and SR2 on each chip (ADLC A bits
; from &C800/&C801, ADLC B bits from &D800/&D801).
;
; | code | fail at | reason                         |
; |------|---------|--------------------------------|
; | 3    | &F107   | ADLC A register-state mismatch |
; | 4    | &F102   | ADLC B register-state mismatch |
.self_test_adlc_state
    lda #&10                                                          ; f0d6: a9 10       ..             ; Mask bit 4 (CTS bit of SR1): expect 1 after reset
    bit adlc_a_cr1                                                    ; f0d8: 2c 00 c8    ,..            ; Test on ADLC A
    beq self_test_fail_adlc_a                                         ; f0db: f0 28       .(             ; CTS clear → ADLC A misconfigured (fail code 3)
    lda #4                                                            ; f0dd: a9 04       ..             ; Mask bit 2 (OVRN bit of SR2): expect 1 (idle, no OVRN)
    bit adlc_a_cr2                                                    ; f0df: 2c 01 c8    ,..            ; Test on ADLC A
    beq self_test_fail_adlc_a                                         ; f0e2: f0 21       .!             ; Bit clear → unexpected state, fail
    lda #&20 ; ' '                                                    ; f0e4: a9 20       .              ; Mask bit 5 (DCD of SR2): expect 0 (no carrier)
    bit adlc_a_cr2                                                    ; f0e6: 2c 01 c8    ,..            ; Test on ADLC A
    bne self_test_fail_adlc_a                                         ; f0e9: d0 1a       ..             ; Bit set → unexpected carrier; fail code 3
    lda #&10                                                          ; f0eb: a9 10       ..             ; Same CTS check for ADLC B
    bit adlc_b_cr1                                                    ; f0ed: 2c 00 d8    ,..            ; Test on ADLC B
    beq self_test_fail_adlc_b                                         ; f0f0: f0 0e       ..             ; Clear → fail code 4
    lda #4                                                            ; f0f2: a9 04       ..             ; Same OVRN check for ADLC B
    bit adlc_b_cr2                                                    ; f0f4: 2c 01 d8    ,..            ; Test on ADLC B
    beq self_test_fail_adlc_b                                         ; f0f7: f0 07       ..             ; Clear → fail code 4
    lda #&20 ; ' '                                                    ; f0f9: a9 20       .              ; Same DCD check for ADLC B
    bit adlc_b_cr2                                                    ; f0fb: 2c 01 d8    ,..            ; Test on ADLC B
    beq self_test_loopback_a_to_b                                     ; f0fe: f0 0a       ..             ; Clear → all checks passed, proceed to loopback test
; &f100 referenced 2 times by &f0f0, &f0f7
.self_test_fail_adlc_b
    lda #4                                                            ; f100: a9 04       ..             ; Fail code 4: ADLC B register state wrong
    jmp self_test_fail                                                ; f102: 4c c7 f2    L..            ; Jump to countable-blink failure handler

; &f105 referenced 3 times by &f0db, &f0e2, &f0e9
.self_test_fail_adlc_a
    lda #3                                                            ; f105: a9 03       ..             ; Fail code 3: ADLC A register state wrong
    jmp self_test_fail                                                ; f107: 4c c7 f2    L..            ; Jump to countable-blink failure handler

; ***************************************************************************************
; Loopback test: transmit on ADLC A, receive on ADLC B
;
; Assumes the official self-test rig is wired up – clock box for the bit-clock, T-piece
; across both Bridge ports, single terminator on the clock box's other socket (which
; both terminates the line and provides its DC bias). See self_test for the full
; rationale. Reconfigures ADLC A for transmit (CR1=&44) and ADLC B for receive
; (CR1=&82), then sends a 256-byte sequence (0,1,2,…,255) out of A and verifies each
; byte is received on B in order by incrementing X alongside the sender's Y.
;
; Four phases:
;
; 1. Pre-fill the A TX FIFO with bytes 0-7 (Y=0..7) while B is still settling – priming
;    the pipeline before any RX checks begin.
; 2. Handshake opening: wait for B's first RX IRQ, verify AP, read and match bytes 0
;    and 1. This is the special "opening" case because the AP/RDA transitions happen on
;    the first two bytes only.
; 3. Streaming loop: repeatedly send a pair via A, read a pair via B, compare against X
;    (increments in lockstep), and loop until Y wraps to 0 (256 bytes sent).
; 4. End-of-frame flush: program CR2=&3F on A to flush the final byte with an
;    end-of-frame marker. Drain the remaining bytes on B (another 255 iterations to
;    empty B's FIFO), then wait for the Frame Valid bit to confirm a clean
;    end-of-frame.
;
; Every mismatch or missing status bit jumps to the shared fail target at
; loopback_a_to_b_fail (&F151) which loads code 5 and hands off to self_test_fail.
; Falls through to self_test_loopback_b_to_a on success.
; &f10a referenced 1 time by &f0fe
.self_test_loopback_a_to_b
    lda #&c0                                                          ; f10a: a9 c0       ..             ; A = &C0: ADLC full reset
    sta adlc_a_cr1                                                    ; f10c: 8d 00 c8    ...            ; Reset ADLC A
    sta adlc_b_cr1                                                    ; f10f: 8d 00 d8    ...            ; Reset ADLC B
    lda #&82                                                          ; f112: a9 82       ..             ; A = &82: CR1 for receive (TX reset, RX IRQ enabled)
    sta adlc_b_cr1                                                    ; f114: 8d 00 d8    ...            ; B becomes the receiver
    lda #&e7                                                          ; f117: a9 e7       ..             ; A = &E7: CR2 for active TX (listen + IRQs armed)
    sta adlc_a_cr2                                                    ; f119: 8d 01 c8    ...            ; Program CR2 on ADLC A
    lda #&44 ; 'D'                                                    ; f11c: a9 44       .D             ; A = &44: CR1 for active TX (TX on, IRQ off)
    sta adlc_a_cr1                                                    ; f11e: 8d 00 c8    ...            ; A becomes the transmitter
    ldy #0                                                            ; f121: a0 00       ..             ; Y = 0: outbound byte counter / data value
    ldx #0                                                            ; f123: a2 00       ..             ; X = 0: expected RX byte on B
; &f125 referenced 1 time by &f137
.loopback_a_to_b_prefill
    jsr wait_adlc_a_irq                                               ; f125: 20 e4 e3     ..            ; Wait for A's TDRA IRQ
    bit adlc_a_cr1                                                    ; f128: 2c 00 c8    ,..            ; BIT SR1 (read CR1 addr) – test V = TDRA (bit 6)
    bvc loopback_a_to_b_fail                                          ; f12b: 50 24       P$             ; Not TDRA → A's TX stalled; fail
    sty adlc_a_tx                                                     ; f12d: 8c 02 c8    ...            ; Push Y into A's TX FIFO (even byte of pair)
    iny                                                               ; f130: c8          .              ; Advance Y
    sty adlc_a_tx                                                     ; f131: 8c 02 c8    ...            ; Push Y into A's TX FIFO (odd byte of pair)
    iny                                                               ; f134: c8          .              ; Advance Y past the pair
    cpy #8                                                            ; f135: c0 08       ..             ; Pre-filled 8 bytes yet?
    bne loopback_a_to_b_prefill                                       ; f137: d0 ec       ..             ; Keep prefilling
    jsr wait_adlc_b_irq                                               ; f139: 20 ea e3     ..            ; Wait for B's first RX IRQ
    lda #1                                                            ; f13c: a9 01       ..             ; A = &01: SR2 mask for AP (Address Present)
    bit adlc_b_cr2                                                    ; f13e: 2c 01 d8    ,..            ; BIT SR2 – first byte should assert AP
    beq loopback_a_to_b_fail                                          ; f141: f0 0e       ..             ; No AP on first byte → fail
    cpx adlc_b_tx                                                     ; f143: ec 02 d8    ...            ; Compare B's FIFO byte against X (expect 0)
    bne loopback_a_to_b_fail                                          ; f146: d0 09       ..             ; Mismatch → fail
    inx                                                               ; f148: e8          .              ; Advance X past the first byte
    jsr wait_adlc_b_irq                                               ; f149: 20 ea e3     ..            ; Wait for B's next RX IRQ
    bit adlc_b_cr2                                                    ; f14c: 2c 01 d8    ,..            ; BIT SR2 – RDA (bit 7) asserted?
    bmi loopback_a_to_b_head_ok                                       ; f14f: 30 05       0.             ; RDA set → good, compare second byte
; &f151 referenced 12 times by &f12b, &f141, &f146, &f159, &f162, &f172, &f177, &f17d, &f18f, &f194, &f19a, &f1a9
.loopback_a_to_b_fail
    lda #5                                                            ; f151: a9 05       ..             ; A = 5: error code for A-to-B loopback failure
    jmp self_test_fail                                                ; f153: 4c c7 f2    L..            ; Hand off to countable-blink failure handler

; &f156 referenced 1 time by &f14f
.loopback_a_to_b_head_ok
    cpx adlc_b_tx                                                     ; f156: ec 02 d8    ...            ; Compare B's second FIFO byte against X (expect 1)
    bne loopback_a_to_b_fail                                          ; f159: d0 f6       ..             ; Mismatch → fail
    inx                                                               ; f15b: e8          .              ; Advance X past the second byte
; &f15c referenced 1 time by &f182
.loopback_a_to_b_stream_loop
    jsr wait_adlc_a_irq                                               ; f15c: 20 e4 e3     ..            ; Wait for A's TDRA IRQ (TX slot ready)
    bit adlc_a_cr1                                                    ; f15f: 2c 00 c8    ,..            ; BIT SR1 – test V = TDRA
    bvc loopback_a_to_b_fail                                          ; f162: 50 ed       P.             ; TX stalled mid-stream → fail
    sty adlc_a_tx                                                     ; f164: 8c 02 c8    ...            ; Push even byte (Y) into A's TX FIFO
    iny                                                               ; f167: c8          .              ; Advance Y
    sty adlc_a_tx                                                     ; f168: 8c 02 c8    ...            ; Push odd byte (Y) into A's TX FIFO
    iny                                                               ; f16b: c8          .              ; Advance Y past the pair
    jsr wait_adlc_b_irq                                               ; f16c: 20 ea e3     ..            ; Wait for B's RX IRQ (pair received)
    bit adlc_b_cr2                                                    ; f16f: 2c 01 d8    ,..            ; BIT SR2 – RDA still asserted?
    bpl loopback_a_to_b_fail                                          ; f172: 10 dd       ..             ; RDA cleared early → fail
    cpx adlc_b_tx                                                     ; f174: ec 02 d8    ...            ; Compare B's even byte against X
    bne loopback_a_to_b_fail                                          ; f177: d0 d8       ..             ; Mismatch → fail
    inx                                                               ; f179: e8          .              ; Advance X
    cpx adlc_b_tx                                                     ; f17a: ec 02 d8    ...            ; Compare B's odd byte against X
    bne loopback_a_to_b_fail                                          ; f17d: d0 d2       ..             ; Mismatch → fail
    inx                                                               ; f17f: e8          .              ; Advance X past the pair
    cpy #0                                                            ; f180: c0 00       ..             ; Y wrapped back to 0 → all 256 bytes sent
    bne loopback_a_to_b_stream_loop                                   ; f182: d0 d8       ..             ; Not done → keep streaming
    lda #&3f ; '?'                                                    ; f184: a9 3f       .?             ; A = &3F: CR2 end-of-frame-with-flush
    sta adlc_a_cr2                                                    ; f186: 8d 01 c8    ...            ; Commit: A pushes the final byte and closes the frame
; &f189 referenced 1 time by &f19f
.loopback_a_to_b_flush_loop
    jsr wait_adlc_b_irq                                               ; f189: 20 ea e3     ..            ; Wait for B's remaining RX IRQ
    bit adlc_b_cr2                                                    ; f18c: 2c 01 d8    ,..            ; BIT SR2 – RDA still asserted?
    bpl loopback_a_to_b_fail                                          ; f18f: 10 c0       ..             ; Drain interrupted → fail
    cpx adlc_b_tx                                                     ; f191: ec 02 d8    ...            ; Compare B's residual byte against X
    bne loopback_a_to_b_fail                                          ; f194: d0 bb       ..             ; Mismatch → fail
    inx                                                               ; f196: e8          .              ; Advance X
    cpx adlc_b_tx                                                     ; f197: ec 02 d8    ...            ; Compare B's next residual byte against X
    bne loopback_a_to_b_fail                                          ; f19a: d0 b5       ..             ; Mismatch → fail
    inx                                                               ; f19c: e8          .              ; Advance X past the pair
    cpx #0                                                            ; f19d: e0 00       ..             ; X wrapped to 0 → B has drained all 256 bytes
    bne loopback_a_to_b_flush_loop                                    ; f19f: d0 e8       ..             ; Not done → keep draining
    jsr wait_adlc_b_irq                                               ; f1a1: 20 ea e3     ..            ; Wait for the trailing end-of-frame IRQ on B
    lda #2                                                            ; f1a4: a9 02       ..             ; A = &02: SR2 mask for FV (Frame Valid)
    bit adlc_b_cr2                                                    ; f1a6: 2c 01 d8    ,..            ; BIT SR2 – confirm FV is set
    beq loopback_a_to_b_fail                                          ; f1a9: f0 a6       ..             ; FV missing → malformed frame, fail
; ***************************************************************************************
; Loopback test: transmit on ADLC B, receive on ADLC A
;
; Mirror of self_test_loopback_a_to_b with adlc_a_* and adlc_b_* swapped: ADLC B
; becomes transmitter (CR1=&44), ADLC A the receiver (CR1=&82), and the same 256-byte
; sequence is sent and verified. Fail target loads code 6 (instead of 5). See
; self_test_loopback_a_to_b for the four-phase breakdown.
.self_test_loopback_b_to_a
    lda #&c0                                                          ; f1ab: a9 c0       ..             ; A = &C0: ADLC full reset
    sta adlc_a_cr1                                                    ; f1ad: 8d 00 c8    ...            ; Reset ADLC A
    sta adlc_b_cr1                                                    ; f1b0: 8d 00 d8    ...            ; Reset ADLC B
    lda #&82                                                          ; f1b3: a9 82       ..             ; A = &82: CR1 for receive (TX reset, RX IRQ enabled)
    sta adlc_a_cr1                                                    ; f1b5: 8d 00 c8    ...            ; A becomes the receiver
    lda #&e7                                                          ; f1b8: a9 e7       ..             ; A = &E7: CR2 for active TX (listen + IRQs armed)
    sta adlc_b_cr2                                                    ; f1ba: 8d 01 d8    ...            ; Program CR2 on ADLC B
    lda #&44 ; 'D'                                                    ; f1bd: a9 44       .D             ; A = &44: CR1 for active TX (TX on, IRQ off)
    sta adlc_b_cr1                                                    ; f1bf: 8d 00 d8    ...            ; B becomes the transmitter
    ldy #0                                                            ; f1c2: a0 00       ..             ; Y = 0: outbound byte counter / data value
    ldx #0                                                            ; f1c4: a2 00       ..             ; X = 0: expected RX byte on A
; &f1c6 referenced 1 time by &f1d8
.loopback_b_to_a_prefill
    jsr wait_adlc_b_irq                                               ; f1c6: 20 ea e3     ..            ; Wait for B's TDRA IRQ
    bit adlc_b_cr1                                                    ; f1c9: 2c 00 d8    ,..            ; BIT SR1 (read CR1 addr) – test V = TDRA (bit 6)
    bvc loopback_b_to_a_fail                                          ; f1cc: 50 24       P$             ; Not TDRA → B's TX stalled; fail
    sty adlc_b_tx                                                     ; f1ce: 8c 02 d8    ...            ; Push Y into B's TX FIFO (even byte of pair)
    iny                                                               ; f1d1: c8          .              ; Advance Y
    sty adlc_b_tx                                                     ; f1d2: 8c 02 d8    ...            ; Push Y into B's TX FIFO (odd byte of pair)
    iny                                                               ; f1d5: c8          .              ; Advance Y past the pair
    cpy #8                                                            ; f1d6: c0 08       ..             ; Pre-filled 8 bytes yet?
    bne loopback_b_to_a_prefill                                       ; f1d8: d0 ec       ..             ; Keep prefilling
    jsr wait_adlc_a_irq                                               ; f1da: 20 e4 e3     ..            ; Wait for A's first RX IRQ
    lda #1                                                            ; f1dd: a9 01       ..             ; A = &01: SR2 mask for AP (Address Present)
    bit adlc_a_cr2                                                    ; f1df: 2c 01 c8    ,..            ; BIT SR2 – first byte should assert AP
    beq loopback_b_to_a_fail                                          ; f1e2: f0 0e       ..             ; No AP on first byte → fail
    cpx adlc_a_tx                                                     ; f1e4: ec 02 c8    ...            ; Compare A's FIFO byte against X (expect 0)
    bne loopback_b_to_a_fail                                          ; f1e7: d0 09       ..             ; Mismatch → fail
    inx                                                               ; f1e9: e8          .              ; Advance X past the first byte
    jsr wait_adlc_a_irq                                               ; f1ea: 20 e4 e3     ..            ; Wait for A's next RX IRQ
    bit adlc_a_cr2                                                    ; f1ed: 2c 01 c8    ,..            ; BIT SR2 – RDA (bit 7) asserted?
    bmi loopback_b_to_a_head_ok                                       ; f1f0: 30 05       0.             ; RDA set → good, compare second byte
; &f1f2 referenced 12 times by &f1cc, &f1e2, &f1e7, &f1fa, &f203, &f213, &f218, &f21e, &f230, &f235, &f23b, &f24a
.loopback_b_to_a_fail
    lda #6                                                            ; f1f2: a9 06       ..             ; A = 6: error code for B-to-A loopback failure
    jmp self_test_fail                                                ; f1f4: 4c c7 f2    L..            ; Hand off to countable-blink failure handler

; &f1f7 referenced 1 time by &f1f0
.loopback_b_to_a_head_ok
    cpx adlc_a_tx                                                     ; f1f7: ec 02 c8    ...            ; Compare A's second FIFO byte against X (expect 1)
    bne loopback_b_to_a_fail                                          ; f1fa: d0 f6       ..             ; Mismatch → fail
    inx                                                               ; f1fc: e8          .              ; Advance X past the second byte
; &f1fd referenced 1 time by &f223
.loopback_b_to_a_stream_loop
    jsr wait_adlc_b_irq                                               ; f1fd: 20 ea e3     ..            ; Wait for B's TDRA IRQ (TX slot ready)
    bit adlc_b_cr1                                                    ; f200: 2c 00 d8    ,..            ; BIT SR1 – test V = TDRA
    bvc loopback_b_to_a_fail                                          ; f203: 50 ed       P.             ; TX stalled mid-stream → fail
    sty adlc_b_tx                                                     ; f205: 8c 02 d8    ...            ; Push even byte (Y) into B's TX FIFO
    iny                                                               ; f208: c8          .              ; Advance Y
    sty adlc_b_tx                                                     ; f209: 8c 02 d8    ...            ; Push odd byte (Y) into B's TX FIFO
    iny                                                               ; f20c: c8          .              ; Advance Y past the pair
    jsr wait_adlc_a_irq                                               ; f20d: 20 e4 e3     ..            ; Wait for A's RX IRQ (pair received)
    bit adlc_a_cr2                                                    ; f210: 2c 01 c8    ,..            ; BIT SR2 – RDA still asserted?
    bpl loopback_b_to_a_fail                                          ; f213: 10 dd       ..             ; RDA cleared early → fail
    cpx adlc_a_tx                                                     ; f215: ec 02 c8    ...            ; Compare A's even byte against X
    bne loopback_b_to_a_fail                                          ; f218: d0 d8       ..             ; Mismatch → fail
    inx                                                               ; f21a: e8          .              ; Advance X
    cpx adlc_a_tx                                                     ; f21b: ec 02 c8    ...            ; Compare A's odd byte against X
    bne loopback_b_to_a_fail                                          ; f21e: d0 d2       ..             ; Mismatch → fail
    inx                                                               ; f220: e8          .              ; Advance X past the pair
    cpy #0                                                            ; f221: c0 00       ..             ; Y wrapped back to 0 → all 256 bytes sent
    bne loopback_b_to_a_stream_loop                                   ; f223: d0 d8       ..             ; Not done → keep streaming
    lda #&3f ; '?'                                                    ; f225: a9 3f       .?             ; A = &3F: CR2 end-of-frame-with-flush
    sta adlc_b_cr2                                                    ; f227: 8d 01 d8    ...            ; Commit: B pushes the final byte and closes the frame
; &f22a referenced 1 time by &f240
.loopback_b_to_a_flush_loop
    jsr wait_adlc_a_irq                                               ; f22a: 20 e4 e3     ..            ; Wait for A's remaining RX IRQ
    bit adlc_a_cr2                                                    ; f22d: 2c 01 c8    ,..            ; BIT SR2 – RDA still asserted?
    bpl loopback_b_to_a_fail                                          ; f230: 10 c0       ..             ; Drain interrupted → fail
    cpx adlc_a_tx                                                     ; f232: ec 02 c8    ...            ; Compare A's residual byte against X
    bne loopback_b_to_a_fail                                          ; f235: d0 bb       ..             ; Mismatch → fail
    inx                                                               ; f237: e8          .              ; Advance X
    cpx adlc_a_tx                                                     ; f238: ec 02 c8    ...            ; Compare A's next residual byte against X
    bne loopback_b_to_a_fail                                          ; f23b: d0 b5       ..             ; Mismatch → fail
    inx                                                               ; f23d: e8          .              ; Advance X past the pair
    cpx #0                                                            ; f23e: e0 00       ..             ; X wrapped to 0 → A has drained all 256 bytes
    bne loopback_b_to_a_flush_loop                                    ; f240: d0 e8       ..             ; Not done → keep draining
    jsr wait_adlc_a_irq                                               ; f242: 20 e4 e3     ..            ; Wait for the trailing end-of-frame IRQ on A
    lda #2                                                            ; f245: a9 02       ..             ; A = &02: SR2 mask for FV (Frame Valid)
    bit adlc_a_cr2                                                    ; f247: 2c 01 c8    ,..            ; BIT SR2 – confirm FV is set
    beq loopback_b_to_a_fail                                          ; f24a: f0 a6       ..             ; FV missing → malformed frame, fail
; ***************************************************************************************
; Verify jumper-set network numbers match self-test expectations
;
; Checks that net_num_a == 1 and net_num_b == 2. The self-test presumes a standard
; loopback-test configuration: the jumpers on the bridge board should be set for 1 and
; 2 respectively before the self-test button is pressed, so that the network numbers
; are predictable and the loopback tests can complete without colliding with anything
; else a tester might leave plugged in.
;
; | code | condition      | fail at |
; |------|----------------|---------|
; | 7    | net_num_a != 1 | &F255   |
; | 8    | net_num_b != 2 | &F261   |
.self_test_check_netnums
    lda net_num_a                                                     ; f24c: ad 00 c0    ...            ; Fetch the side-A jumper setting
    cmp #1                                                            ; f24f: c9 01       ..             ; Expected self-test value = 1
    beq self_test_check_netnum_b                                      ; f251: f0 05       ..             ; Match → move on to check side B
    lda #7                                                            ; f253: a9 07       ..             ; Mismatch: load error code 7
    jmp self_test_fail                                                ; f255: 4c c7 f2    L..            ; Jump to countable-blink failure handler

; &f258 referenced 1 time by &f251
.self_test_check_netnum_b
    lda net_num_b                                                     ; f258: ad 00 d0    ...            ; Fetch the side-B jumper setting
    cmp #2                                                            ; f25b: c9 02       ..             ; Expected self-test value = 2
    beq self_test_pass_done                                           ; f25d: f0 05       ..             ; Match → end-of-pass bookkeeping
    lda #8                                                            ; f25f: a9 08       ..             ; Mismatch: load error code 8
    jmp self_test_fail                                                ; f261: 4c c7 f2    L..            ; Jump to countable-blink failure handler

; ***************************************************************************************
; End-of-pass: toggle scratch flag and loop for another pass
;
; Reached when every test in a pass has succeeded. The self-test doesn't stop – it
; loops indefinitely until reset. Toggles bit 7 of &0003 (the self-test scratch byte)
; via EOR #&FF; if bit 7 is set after the toggle, JMPs to self_test_reset_adlcs for
; another full pass. Otherwise falls through to self_test_alt_pass, which resets ADLCs
; differently before re-entering the ZP test.
;
; The two-pass structure is what produces the "even mark-space" flashing the operator
; sees during a healthy self-test. A "normal" pass starts with self_test_reset_adlcs
; writing CR3 = &80 on ADLC B (LED dark), and the LED stays dark through the ZP,
; ROM-checksum, and RAM tests. The first loopback test then issues CR1 = &C0 on B,
; which – per the MC6854 datasheet – clears the LOC/DTR control bit, so the LED comes
; on for the rest of the pass. The alt-pass runs the same tests over again but skips
; self_test_reset_adlcs, so B's CR3 stays cleared from the previous loopback reset and
; the LED stays lit for the entire alt-pass. The cycle is therefore: short dark stretch
; (early normal-pass tests) → long lit stretch (rest of normal pass + entire alt-pass)
; → short dark stretch → … – a slow, asymmetric flash whose mark and space the operator
; perceives as the "running" indicator.
; &f264 referenced 1 time by &f25d
.self_test_pass_done
    lda st_pass_phase                                                 ; f264: a5 03       ..             ; Read the pass-phase flag at &03
    eor #&ff                                                          ; f266: 49 ff       I.             ; Invert it so we alternate between passes
    sta st_pass_phase                                                 ; f268: 85 03       ..             ; Store the flipped phase back
    bmi self_test_alt_pass                                            ; f26a: 30 03       0.             ; If bit 7 set, restart with full self_test_reset_adlcs (LED goes dark)
    jmp self_test_reset_adlcs                                         ; f26c: 4c 05 f0    L..            ; Jump up to redo from the top

; &f26f referenced 1 time by &f26a
.self_test_alt_pass
    lda #&c1                                                          ; f26f: a9 c1       ..             ; Alt-pass: partial reset on A only; B's CR3 carries over (LED stays lit)
    sta adlc_a_cr1                                                    ; f271: 8d 00 c8    ...            ; ADLC A CR1 = &C1 (reset + AC=1)
    lda #0                                                            ; f274: a9 00       ..             ; A = 0: CR3=&00 for A only (B's CR3 untouched – stays cleared from last loopback)
    sta adlc_a_cr2                                                    ; f276: 8d 01 c8    ...            ; Program CR3 on A only this pass
    lda #&82                                                          ; f279: a9 82       ..             ; Mask: back to normal listen-mode CR1
    sta adlc_a_cr1                                                    ; f27b: 8d 00 c8    ...            ; Commit CR1 on ADLC A
    sta adlc_b_cr1                                                    ; f27e: 8d 00 d8    ...            ; Commit CR1 on ADLC B
    lda #&67 ; 'g'                                                    ; f281: a9 67       .g             ; Mask: standard listen-mode CR2
    sta adlc_a_cr2                                                    ; f283: 8d 01 c8    ...            ; Commit CR2 on ADLC A
    sta adlc_b_cr2                                                    ; f286: 8d 01 d8    ...            ; Commit CR2 on ADLC B
    jmp self_test_zp                                                  ; f289: 4c 2f f0    L/.            ; Enter the ZP test again (skip the ADLC reset)

; ***************************************************************************************
; RAM-failure blink pattern (does not use RAM)
;
; Reached from any of the three RAM tests on failure – ZP test, pattern RAM test,
; incrementing RAM test. This handler can't use RAM for counting blinks (if RAM is
; broken, reading/writing RAM is exactly what's untrustworthy), so it generates its
; blink pattern from ROM-based DEC abs,X instructions that exercise the CPU for timing
; without touching RAM.
;
; Sets CR1=1 (AC=1) so writes to adlc_a_cr2 target CR3. Alternates CR3 between &00 (LED
; on – LOC/DTR pin high) and &80 (LED off – LOC/DTR pin driven low) in an infinite loop
; paced by DEX/DEY delays and by seven DEC instructions that read-modify-write (but
; actually just read, since writes to ROM are ignored) bytes in the ROM starting at the
; reset vector.
;
; Continues forever; the operator infers "the RAM is bad" from the fact that the LED is
; blinking but no specific error code can be counted out – distinct from the more
; structured blink patterns produced by self_test_fail with codes 2-8.
; &f28c referenced 1 time by &f09d
.ram_test_fail
    ldx #1                                                            ; f28c: a2 01       ..             ; CR1 = 1: enable AC so cr2 writes hit CR3
    stx adlc_a_cr1                                                    ; f28e: 8e 00 c8    ...            ; Commit CR1 on ADLC A
; &f291 referenced 1 time by &f2c4
.ram_test_fail_loop
    ldx #0                                                            ; f291: a2 00       ..             ; CR3 = 0 → LOC/DTR pin high → LED ON on ADLC B
    stx adlc_a_cr2                                                    ; f293: 8e 01 c8    ...            ; Commit CR3
    ldx #0                                                            ; f296: a2 00       ..             ; X = 0: inner delay counter
    ldy #0                                                            ; f298: a0 00       ..             ; Y = 0: outer delay counter
; &f29a referenced 2 times by &f29b, &f29e
.ram_test_fail_short_delay
    dex                                                               ; f29a: ca          .              ; Pure-register busy-wait (no RAM access)
    bne ram_test_fail_short_delay                                     ; f29b: d0 fd       ..             ; Spin through X's 256 values
    dey                                                               ; f29d: 88          .              ; Bump Y
    bne ram_test_fail_short_delay                                     ; f29e: d0 fa       ..             ; Spin through Y's 256 values
    ldx #&80                                                          ; f2a0: a2 80       ..             ; CR3 = &80 → LOC/DTR pin driven low → LED OFF
    stx adlc_a_cr2                                                    ; f2a2: 8e 01 c8    ...            ; Commit CR3
    ldy #0                                                            ; f2a5: a0 00       ..             ; Y = 0 for the longer delay phase
    ldx #0                                                            ; f2a7: a2 00       ..             ; X = 0
; &f2a9 referenced 2 times by &f2bf, &f2c2
.ram_test_fail_long_delay
    dec reset,x                                                       ; f2a9: de 00 e0    ...            ; DEC of ROM (writes ignored); seven of them in a row…
    dec reset,x                                                       ; f2ac: de 00 e0    ...            ; …pace the LED-off interval without RAM writes
    dec reset,x                                                       ; f2af: de 00 e0    ...            ; (all seven DECs hit the same RO address)
    dec reset,x                                                       ; f2b2: de 00 e0    ...            ; DEC reset,X again – 4 cycles, no side effect
    dec reset,x                                                       ; f2b5: de 00 e0    ...            ; DEC reset,X again – 4 cycles, no side effect
    dec reset,x                                                       ; f2b8: de 00 e0    ...            ; DEC reset,X again – 4 cycles, no side effect
    dec reset,x                                                       ; f2bb: de 00 e0    ...            ; Last of the seven; together they lengthen the inner tick
    dex                                                               ; f2be: ca          .              ; Step X
    bne ram_test_fail_long_delay                                      ; f2bf: d0 e8       ..             ; Spin through X's 256 values
    dey                                                               ; f2c1: 88          .              ; Step Y
    bne ram_test_fail_long_delay                                      ; f2c2: d0 e5       ..             ; Spin through Y's 256 values
    jmp ram_test_fail_loop                                            ; f2c4: 4c 91 f2    L..            ; Loop forever; LED alternates at an uncountable pace

; ***************************************************************************************
; Self-test failure – signal error code via the LED
;
; Common failure exit for every non-RAM self-test stage. Called with the error code in
; A. Saves two copies of the code in &00/&01 then enters an infinite loop that blinks
; the LED (via CR3 bit 7 on ADLC B, which is the pin that drives the front-panel LED) a
; count of times equal to the error code, separated by longer gaps.
;
; Error codes:
;
; | code | meaning                     | fail point                         |
; |------|-----------------------------|------------------------------------|
; | 2    | ROM checksum mismatch       | self_test_rom_checksum             |
; | 3    | ADLC A register state wrong | self_test_adlc_state at &F107      |
; | 4    | ADLC B register state wrong | self_test_adlc_state at &F102      |
; | 5    | A-to-B loopback fail        | self_test_loopback_a_to_b at &F153 |
; | 6    | B-to-A loopback fail        | self_test_loopback_b_to_a at &F1F4 |
; | 7    | net_num_a != 1              | self_test_check_netnums at &F255   |
; | 8    | net_num_b != 2              | self_test_check_netnums at &F261   |
;
; Code 1 is not used: the zero-page integrity test's failure path routes to
; ram_test_fail via self_test_ram_fail_jump (&F09D), not here, because any failure of
; the first three RAM tests means normal counting loops can't be trusted. ram_test_fail
; (&F28C) uses a distinct ROM-only blink instead.
;
; Blink pattern: CR1=1 sets the ADLC's AC bit so writes to CR2's address hit CR3. The
; handler alternates CR3=&00 (LED on – LOC/DTR pin high) and CR3=&80 (LED off – pin
; driven low) N times, where N = error code held in &01. Each pulse pair runs ~1 s of
; LED-on followed by ~1 s of LED-off, so a burst of N pulses contains N visible
; flashes. After the burst, the LED is left in its OFF state (the last CR3 = &80 write
; before the spacer runs) and the spacer's 8× DEX/DEY iteration extends that OFF state
; to ~8 s before the next burst begins. The operator counts the LED-on flashes inside
; each burst – distinguishing them from the long ~8 s LED-off gap that separates bursts
; – to identify the failed test.
; &f2c7 referenced 7 times by &f06d, &f102, &f107, &f153, &f1f4, &f255, &f261
.self_test_fail
    sta st_ptr_lo                                                     ; f2c7: 85 00       ..             ; Save error code to &00 (the restart value)
    sta st_ptr_hi                                                     ; f2c9: 85 01       ..             ; …and to &01 (the per-burst countdown)
    ldx #1                                                            ; f2cb: a2 01       ..             ; X = 1: enable AC on ADLC A
    stx adlc_a_cr1                                                    ; f2cd: 8e 00 c8    ...            ; Commit CR1 so cr2 writes hit CR3 from here on
; &f2d0 referenced 2 times by &f2f0, &f308
.self_test_fail_pulse
    ldx #0                                                            ; f2d0: a2 00       ..             ; X = 0: CR3 off → LOC/DTR pin high → LED LIT
    stx adlc_a_cr2                                                    ; f2d2: 8e 01 c8    ...            ; Commit CR3 = 0
    ldy #0                                                            ; f2d5: a0 00       ..             ; Y = 0: outer loop counter for the LED-lit phase
    ldx #0                                                            ; f2d7: a2 00       ..             ; X = 0: inner loop counter
; &f2d9 referenced 2 times by &f2da, &f2dd
.self_test_fail_lit_delay
    dex                                                               ; f2d9: ca          .              ; DEX – tick the inner counter
    bne self_test_fail_lit_delay                                      ; f2da: d0 fd       ..             ; Inner spin through X's 256 values
    dey                                                               ; f2dc: 88          .              ; Step Y
    bne self_test_fail_lit_delay                                      ; f2dd: d0 fa       ..             ; Outer spin: Y cycles give ~65K iterations with LED lit
    ldx #&80                                                          ; f2df: a2 80       ..             ; X = &80: CR3 bit 7 set → LOC/DTR pin low → LED DARK
    stx adlc_a_cr2                                                    ; f2e1: 8e 01 c8    ...            ; Commit CR3 = &80
    ldy #0                                                            ; f2e4: a0 00       ..             ; Y = 0
    ldx #0                                                            ; f2e6: a2 00       ..             ; X = 0
; &f2e8 referenced 2 times by &f2e9, &f2ec
.self_test_fail_dark_delay
    dex                                                               ; f2e8: ca          .              ; DEX – tick the inner counter
    bne self_test_fail_dark_delay                                     ; f2e9: d0 fd       ..             ; Inner spin through X's 256 values (LED dark)
    dey                                                               ; f2eb: 88          .              ; Step Y
    bne self_test_fail_dark_delay                                     ; f2ec: d0 fa       ..             ; Outer spin: Y cycles give the same length as the lit phase
    dec st_ptr_hi                                                     ; f2ee: c6 01       ..             ; One pulse done; decrement the burst counter
    bne self_test_fail_pulse                                          ; f2f0: d0 de       ..             ; Loop until we've emitted N pulses
    lda #8                                                            ; f2f2: a9 08       ..             ; A = 8: spacer count between bursts
    sta st_ptr_hi                                                     ; f2f4: 85 01       ..             ; Seed the spacer loop counter
    ldy #0                                                            ; f2f6: a0 00       ..             ; Y = 0
    ldx #0                                                            ; f2f8: a2 00       ..             ; X = 0
; &f2fa referenced 3 times by &f2fb, &f2fe, &f302
.self_test_fail_spacer_delay
    dex                                                               ; f2fa: ca          .              ; DEX – tick the inner spacer counter
    bne self_test_fail_spacer_delay                                   ; f2fb: d0 fd       ..             ; Inner spin through X's 256 values (LED stays off after last pulse)
    dey                                                               ; f2fd: 88          .              ; Step Y
    bne self_test_fail_spacer_delay                                   ; f2fe: d0 fa       ..             ; Outer spin: 8x this pair keeps the gap audibly long
    dec st_ptr_hi                                                     ; f300: c6 01       ..             ; Decrement spacer loop counter
    bne self_test_fail_spacer_delay                                   ; f302: d0 f6       ..             ; Repeat eight times total
    lda st_ptr_lo                                                     ; f304: a5 00       ..             ; Reload the N-pulse counter with the saved error code
    sta st_ptr_hi                                                     ; f306: 85 01       ..             ; Store into &01 for the next burst
    jmp self_test_fail_pulse                                          ; f308: 4c d0 f2    L..            ; Jump back to start another N-pulse burst forever

    for _py8dis_fill_n%, 1, 3301 : equb &ff : next                    ; f30b: ff ff ff... ...
; Checksum-tuning byte: balances the ROM sum to &55
.rom_checksum_adjust
    equb &46                                                          ; fff0: 46          F
; ***************************************************************************************
; ROM vector gap – unused bytes before the hardware vectors
;
; 9 bytes of &FF padding between rom_checksum_adjust (&FFF0) at &FFF0 and the 6502
; hardware vector table at &FFFA (&FFFA).
;
; The firmware author had 10 bytes (&FFF0-&FFF9) to choose from for the sum-balancing
; byte; they placed &46 at &FFF0 and left the remaining nine as &FF.
.rom_vector_gap
    for _py8dis_fill_n%, 1, 9 : equb &ff : next                       ; fff1: ff ff ff... ...
; ***************************************************************************************
; 6502 hardware vector table
;
; The three addresses the 6502 fetches when an interrupt fires:
;
; | Offset      | Purpose        | Target            |
; |-------------|----------------|-------------------|
; | &FFFA-&FFFB | NMI vector     | &FFFF (unused)    |
; | &FFFC-&FFFD | RESET vector   | reset (&E000)     |
; | &FFFE-&FFFF | IRQ/BRK vector | self_test (&F000) |
;
; NMI isn't wired to anything on the Bridge board, so the slot is filled with &FFFF
; rather than a real handler. RESET enters the main firmware at &E000. IRQ/BRK – the
; line the self-test push-button pulls low – enters at &F000; pressing the button
; therefore runs the self-test, and any BRK instruction anywhere in the ROM would do
; the same thing.
.hardware_vectors
    equw &ffff                                                        ; fffa: ff ff       ..             ; NMI vector
    equw reset                                                        ; fffc: 00 e0       ..             ; RESET vector
    equw self_test                                                    ; fffe: 00 f0       ..             ; IRQ/BRK vector
.pydis_end

    assert reset == &e000
    assert self_test == &f000

save pydis_start, pydis_end

; Label references by decreasing frequency:
;     adlc_a_cr2:                   39
;     adlc_b_cr2:                   34
;     adlc_a_cr1:                   32
;     adlc_b_cr1:                   29
;     adlc_a_tx:                    26
;     adlc_b_tx:                    26
;     mem_ptr_hi:                   23
;     mem_ptr_lo:                   23
;     rx_dst_stn:                   20
;     wait_adlc_a_irq:              19
;     wait_adlc_b_irq:              19
;     st_ptr_hi:                    15
;     st_ptr_lo:                    15
;     main_loop:                    14
;     net_num_a:                    13
;     loopback_a_to_b_fail:         12
;     loopback_b_to_a_fail:         12
;     net_num_b:                    12
;     rx_len:                       12
;     st_page_count:                10
;     tx_src_net:                   10
;     rx_dst_net:                    8
;     tx_dst_net:                    8
;     ctr24_lo:                      7
;     pydis_start:                   7
;     reachable_via_a:               7
;     reachable_via_b:               7
;     reset:                         7
;     self_test_fail:                7
;     transmit_frame_a:              7
;     transmit_frame_b:              7
;     announce_flag:                 6
;     self_test_ram_fail_jump:       6
;     tx_end_hi:                     6
;     tx_end_lo:                     6
;     handshake_rx_a:                5
;     handshake_rx_a_escape:         5
;     handshake_rx_b:                5
;     handshake_rx_b_escape:         5
;     main_loop_poll:                5
;     tx_ctrl:                       5
;     announce_count:                4
;     announce_tmr_hi:               4
;     announce_tmr_lo:               4
;     build_query_response:          4
;     ctr24_hi:                      4
;     ctr24_mid:                     4
;     rx_frame_a_bail:               4
;     rx_frame_b_bail:               4
;     rx_query_net:                  4
;     rx_src_net:                    4
;     tx_dst_stn:                    4
;     tx_port:                       4
;     wait_adlc_a_idle:              4
;     wait_adlc_b_idle:              4
;     init_reachable_nets:           3
;     self_test_fail_adlc_a:         3
;     self_test_fail_spacer_delay:   3
;     st_pass_phase:                 3
;     top_ram_page:                  3
;     tx_data0:                      3
;     wait_adlc_a_idle_loop:         3
;     wait_adlc_b_idle_loop:         3
;     adlc_a_listen:                 2
;     adlc_a_tx2:                    2
;     adlc_b_listen:                 2
;     adlc_b_tx2:                    2
;     build_announce_b:              2
;     handshake_rx_a_pair_loop:      2
;     handshake_rx_b_pair_loop:      2
;     ram_test_fail_long_delay:      2
;     ram_test_fail_short_delay:     2
;     re_announce_done:              2
;     rx_a_forward:                  2
;     rx_a_not_for_us:               2
;     rx_a_to_forward:               2
;     rx_b_forward:                  2
;     rx_b_not_for_us:               2
;     rx_b_to_forward:               2
;     rx_ctrl:                       2
;     rx_frame_a_dispatch:           2
;     rx_frame_b_dispatch:           2
;     rx_port:                       2
;     self_test_fail_adlc_b:         2
;     self_test_fail_dark_delay:     2
;     self_test_fail_lit_delay:      2
;     self_test_fail_pulse:          2
;     self_test_ram_incr_fill:       2
;     self_test_ram_incr_verify:     2
;     self_test_ram_pattern_loop:    2
;     self_test_rom_checksum_loop:   2
;     stagger_delay:                 2
;     transmit_frame_a_pair_loop:    2
;     transmit_frame_b_pair_loop:    2
;     tx_src_stn:                    2
;     adlc_a_full_reset:             1
;     adlc_b_full_reset:             1
;     handshake_rx_a_drained:        1
;     handshake_rx_a_end:            1
;     handshake_rx_a_finalise_len:   1
;     handshake_rx_a_route_check:    1
;     handshake_rx_b_drained:        1
;     handshake_rx_b_end:            1
;     handshake_rx_b_finalise_len:   1
;     handshake_rx_b_route_check:    1
;     init_reachable_nets_clear:     1
;     loopback_a_to_b_flush_loop:    1
;     loopback_a_to_b_head_ok:       1
;     loopback_a_to_b_prefill:       1
;     loopback_a_to_b_stream_loop:   1
;     loopback_b_to_a_flush_loop:    1
;     loopback_b_to_a_head_ok:       1
;     loopback_b_to_a_prefill:       1
;     loopback_b_to_a_stream_loop:   1
;     main_loop_arm_a:               1
;     main_loop_arm_b:               1
;     main_loop_idle:                1
;     main_loop_poll_a:              1
;     ram_test_done:                 1
;     ram_test_fail:                 1
;     ram_test_fail_loop:            1
;     ram_test_loop:                 1
;     re_announce_rearm:             1
;     re_announce_side_b:            1
;     rx_a_broadcast_check:          1
;     rx_a_forward_ack_round:        1
;     rx_a_forward_done:             1
;     rx_a_forward_pair_loop:        1
;     rx_a_handle_80:                1
;     rx_a_handle_81:                1
;     rx_a_handle_82:                1
;     rx_a_learn_loop:               1
;     rx_a_query_done:               1
;     rx_a_src_net_resolved:         1
;     rx_b_broadcast_check:          1
;     rx_b_forward_ack_round:        1
;     rx_b_forward_done:             1
;     rx_b_forward_pair_loop:        1
;     rx_b_handle_80:                1
;     rx_b_handle_81:                1
;     rx_b_handle_82:                1
;     rx_b_learn_loop:               1
;     rx_b_query_done:               1
;     rx_b_src_net_resolved:         1
;     rx_frame_a:                    1
;     rx_frame_a_drain:              1
;     rx_frame_a_end:                1
;     rx_frame_b:                    1
;     rx_frame_b_drain:              1
;     rx_frame_b_end:                1
;     rx_query_port:                 1
;     rx_src_stn:                    1
;     self_test_alt_pass:            1
;     self_test_check_netnum_b:      1
;     self_test_loopback_a_to_b:     1
;     self_test_pass_done:           1
;     self_test_ram_incr:            1
;     self_test_ram_pattern:         1
;     self_test_reset_adlcs:         1
;     self_test_rom_checksum:        1
;     self_test_zp:                  1
;     self_test_zp_write_read:       1
;     stagger_delay_inner:           1
;     stagger_delay_outer:           1
;     stagger_delay_prelude:         1
;     transmit_frame_a_end_check:    1
;     transmit_frame_a_escape:       1
;     transmit_frame_a_finish:       1
;     transmit_frame_a_send_pair:    1
;     transmit_frame_b_end_check:    1
;     transmit_frame_b_escape:       1
;     transmit_frame_b_finish:       1
;     transmit_frame_b_send_pair:    1
;     wait_adlc_a_idle_ready:        1
;     wait_adlc_a_idle_tick:         1
;     wait_adlc_b_idle_ready:        1
;     wait_adlc_b_idle_tick:         1

; Stats:
;     Total size (Code + Data) = 2618 bytes
;     Code                     = 2611 bytes (100%)
;     Data                     = 7 bytes (0%)
;
;     Number of instructions   = 1117
;     Number of data bytes     = 1 bytes
;     Number of data words     = 6 bytes
;     Number of string bytes   = 0 bytes
;     Number of strings        = 0
