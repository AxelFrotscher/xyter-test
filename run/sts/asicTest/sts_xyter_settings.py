LINK_BREAK=0b00001
#LINK_BREAK=0b00010
#LINK_BREAK=0b00100
#LINK_BREAK=0b01000
#LINK_BREAK=0b10000
#LINK_BREAK=0b00011
#LINK_BREAK=0b00111
#LINK_BREAK=0b01111
#LINK_BREAK=0b11111

# Box 3:
# Box 4: Assumes it has FEB 002 and 003

xml_filename  = "file://stsDPB_standalone.xml"
edpb_names    = [ "eDPB_S" ] # 1D: [ eDPB ]
sts_addr_map  = [  [  15,  15,  15,  15,  15,  15] ] # 2D: [ eDPB ][ FEB ]
feb_serial_nr = [  [ 165, 166, 165, 165, 166, 166] ] # 2D: [ eDPB ][ FEB ]
iface_active  = [  [   1,   0,   0,   0,   0,   0] ] # 2D: [ eDPB ][ FEB ]
much_mode_on  = [  [   0,   1,   1,   1,   1,   1] ] # 2D: [ eDPB ][ FEB ], 1 for MUCH mode and 0 for STS mode
global_gate   =    [   0,   0,   0,   0,   0,   0] # 1D: [ FEB ], 1 for FEB-A and 0 for FEB-B and later, same for all FEBs
asic_version  = [  [   1,   1,   1,   1,   1,   1]  ] # 2D: [ eDPB ][ FEB ]

#Parameters used during trim calib
date          = [ [ "171205_1020", "171205_1020", "171205_1020", "171205_1020", "171205_1020", "171205_1020" ] ] # 2D: [ eDPB ][ FEB ]
amp_cal_min   = [ [            40,            40,            40,            40,            40,           40  ] ] # 2D: [ eDPB ][ FEB ], (130,4, amp_cal)
amp_cal_max   = [ [           226.,          226.,          226.,          226.,          226.,         226. ] ] # 2D: [ eDPB ][ FEB ]
charge_type   = [ [             0,             0,             0,             0,             0,            0  ] ] # 2D: [ eDPB ][ FEB ], 0 for e- and 1 for holes, GEM & hodo use e-
# Reference Voltages used during trim calib
vref_n        = [ [            25,            25,            25,            25,            25,            25 ] ] # 2D: [ eDPB ][ FEB ], Ref. voltages Negative  (130, 8) (31)
vref_p        = [ [            53,            53,            53,            53,            53,            53 ] ] # 2D: [ eDPB ][ FEB ], Ref. voltages Positive  (130, 9) (48)
vref_t        = [ [           186,           186,           186,           186,           186,           186 ] ] # 2D: [ eDPB ][ FEB ], Ref. voltages Threshold (130,10)  (188)
# Slow shapers calib
tr_min        = [ [            40,            40,            40,            40,            40,            40 ] ] # 2D: [ eDPB ][ FEB ]
tr_max        = [ [           226,           226,           226,           226,           226,           226 ] ] # 2D: [ eDPB ][ FEB ]
tr_coarse_step= [ [             5,             5,             5,             5,             5,             5 ] ] # 2D: [ eDPB ][ FEB ]
tr_coarse_range= [ [            1,             1,             1,             1,             1,             1 ] ] # 2D: [ eDPB ][ FEB ]
tr_coarse_offset= [ [          -5,            -5,            -5,            -5,            -5,            -5 ] ] # 2D: [ eDPB ][ FEB ]
tr_fine_offset= [ [           -20,           -20,           -20,           -20,           -20,           -20 ] ] # 2D: [ eDPB ][ FEB ]
# Fast shaper threshold
thr2_glb      = [ [            37,            37,            37,            37,            37,            37 ] ] # 2D: [ eDPB ][ FEB ], Global threshold for the fast shaper calib. (130,7)  (37)
thr_min       = [ [             0,             0,             0,             0,             0,             0 ] ] # 2D: [ eDPB ][ FEB ]
thr_max       = [ [            64,            64,            64,            64,            64,            64 ] ] # 2D: [ eDPB ][ FEB ]
thr_step      = [ [             1,             1,             1,             1,             1,             1 ] ] # 2D: [ eDPB ][ FEB ]

# Parameters used during settrim
trim_offset   = [ [             0,             0,             0,             0,             0,             0 ] ] # 2D: [ eDPB ][ FEB ]

# Parameters used during custom settings
ana_chan_63   = [ [           144,           144,           144,           144,           144,           144 ] ] # 2D: [ eDPB ][ FEB ], 8-bit ADC control register Typical value 144

## Global DAC settings
### 00 = CSA front pads, push current to reduce noise Typical value 31 (CSA bias current)
### 01 = CSA feedback resistance Typical value 7
### 02 = Set by charge_type !!! Electron or hole mode with reset on or off options. Typical value 147 for Electron reset off and 211 for electron reset on.
###                             Also selects polarity, pulse stretcher, PSC switch and polarity selection bias current
### 03 = Bias current of slow and fast shaper Typical value 31
### 04 = Calibration pulse up to 15fc charge. Value should be 0 to use external pulser
### 05 = Shaping time constant for slow shaper <3:2> 0-90ns, 1-160ns, Channel selection <1:0> 0-0,4,...124 + 129, 3-3,7,....127 +128. For ampCal, channel selection is not showing any affect.
### 06 = Reference current for the high speed discriminator Typical value 32 for 53uA
### 07 = High speed discriminator threshold Typical value 100
### 08 = Set by vref_n !!!  ADC low threshold <5:0> and DAC ADC_VREF_N for bit 6 Typical value 31
### 09 = Set by vref_p !!! ADC high threshold
### 10 = Set by vref_t !!! DAC ADC_VREF_T bit 6, Global ADC threshold (VREF_T) <5:0> and <8>: enable Typical value 188
### 11 = Triggerring conditions of calSTROBE and global gate backend Typical value 64
### 12 = NEW IN_CSAP register for PSC reference voltage control Typical value 30
### 13 = CSA back pads, push current to reduce noise Typical value 31 (CSA bias currnent)
### 14 = CSA buffer & cascode current control register Typical value 27
### 15 = SHAPERs buffer & cascode current control register Typical value 27
### 16 = Reserved, 6-bit CSA_BIAS 1V generator Typical value
####                    0    1    3    4    5    6   11   12   13   14   15   16
ana_glob      = [ [ [  60,  20,  15,   0,   3,  32,   0,  30,  60,  27,  27,  31 ], # F0
                    [  60,  20,  15,   0,   3,  32,   0,  30,  60,  27,  27,  31 ], # F1
                    [  60,  20,  15,   0,   3,  32,   0,  30,  60,  27,  27,  31 ], # F2
                    [  60,  20,  15,   0,   3,  32,   0,  30,  60,  27,  27,  31 ], # F3
                    [  60,  20,  15,   0,   3,  32,   0,  30,  60,  27,  27,  31 ], # F4
                    [  60,  20,  15,   0,   3,  32,   0,  30,  60,  27,  27,  31 ]  # F5
                  ] # EDPB 0
                ] # 3D: [ eDPB ][ FEB ][ register ]

## Register file settings
### 23 = FIFO AFULL THR
### 29 = FE Event Missed THR
####                   23   29
regfile       = [ [ [   80,   80 ], # F0
                    [   80,   80 ], # F1
                    [   80,   80 ], # F2
                    [   80,   80 ], # F3
                    [   80,   80 ], # F4
                    [   80,   80 ]  # F5
                  ] # EDPB 0
                ] # 3D: [ eDPB ][ FEB ][ register ]

# Parameters used during channels masking
mask_reg_offs = 4
#             Chan:    0- 13  14- 27  28- 41  42- 55  56- 69  70- 83  84- 97  98-111 112-125 126-129
channel_mask  = [ [
                    [ 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000 ], # F0: 1 ch 7
                    [ 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000 ], # F1: 1 ch 7
                    [ 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000 ], # F2: 1 ch 7
                    [ 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000 ], # F3: 1 ch 7
                    [ 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000 ], # F4: 1 ch 7
                    [ 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000 ]  # F5: 1 ch 7
                  ] # EDPB 0
                ] # 3D: [ eDPB ][ FEB ][ register ]
'''
11 1111 0111 1111 3F7F
11 1101 1111 1101 3DFD
11 0111 1111 0111 37F7
01 1111 1101 1111 1FDF
11 1111 0111 1111 3F7F ...
'''
# SYNC paramaters
sync_wait_time  = 10000000
ms_period       = 102400
#ms_clock_period = 6.25
ms_clock_period = 3.125
ms_idx_thrs     = [ 0, 0, 0xffffffff, 0xffffffff ]

# eDPB sync with frames method parameters
frameIdxSz = 1 << 28 # Counter of frames: 28 bits of 1/15 * 40 MHz
tsCntSz    = 1 << 14 # Counter of ts : 14 bits of 320 MHz
nbClkPerFrame = 15
ppsPeriodClk = 33554432 # = 2^25
ppsPeriodSec = ppsPeriodClk * 25e-9 # 40 MHz TS clock
nbPpsPeriodsBefSync = 3
nbClkBefSync = ppsPeriodClk * nbPpsPeriodsBefSync

tsIniOffset   = [  [   0,   0,   0,   0,   0,   0] ] # 2D: [ eDPB ][ FEB ]
