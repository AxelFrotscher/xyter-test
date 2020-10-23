#!/usr/bin/python

import time
import sys
import logging
import uhal
sys.path.append("../../../lib")
import global_dev_ctrl as gdc
import flim_dev_ctrl as fdc
import sts_xyter_dev_ctrl as sxdc

import sts_xyter_settings as settings

log = logging.getLogger()
# This is a global level, sets the miminum level which can be reported
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler(sys.stderr)
sh.setLevel(logging.INFO)
log.addHandler(sh)
fh = logging.FileHandler("./logs/" + sys.argv[0].replace('.py', '.log'), 'w')
fh.setLevel(logging.DEBUG)
fmt = logging.Formatter('[%(levelname)s] %(message)s')
fh.setFormatter(fmt)
log.addHandler(fh)

uhal.setLogLevelTo(uhal.LogLevel.WARNING)
manager = uhal.ConnectionManager( settings.xml_filename )

hw = []
for edpb in settings.edpb_names:
  hw.append( manager.getDevice( edpb ) )

sts_com  = []
flims    = []
afck_id  = []
afck_mac = []
sts_ifaces = [[]]
for edpb_idx in range( 0, len(hw) ):
  sts_ifaces.append( [] )

  sts_com.append( sxdc.sts_xyter_com_ctrl( hw[ edpb_idx ], "sts_xyter_dev") )
  flims.append(   fdc.flim_dev_ctrl(       hw[ edpb_idx ], "flim_ctrl_dev") )
  sts_com[ edpb_idx ].read_public_dev_info()

  afck_id.append( gdc.get_afck_id(   hw[ edpb_idx ], "global_dev") )
  afck_mac.append( gdc.get_afck_mac( hw[ edpb_idx ], "global_dev") )
  log.info("\nAFCK ID:  0x%04x", afck_id[ edpb_idx ] )
  log.info("\nAFCK MAC: %s",     afck_mac[ edpb_idx ] )

  # iface_no: xyter_addr
  for i in range(0, sts_com[ edpb_idx ].interface_count()):
    if settings.iface_active[ edpb_idx ][i] == 1:
      sts_ifaces[edpb_idx].append( sxdc.sts_xyter_iface_ctrl( sts_com[ edpb_idx ], i, settings.sts_addr_map[ edpb_idx ][i], afck_id[ edpb_idx ] ) )

### For settings please see in the sts_xyter_settings.py file
'''
## Channel settings
ana_chan_63 = 144 # 8-bit ADC control register Typical value 144
ana_chan_65 = 244 # Typical value for STS
#ana_chan_65 = 228 # Typical value for MUCH

## Global DAC settings
ana_glob_00 =  60 # CSA front pads, push current to reduce noise Typical value 31 (CSA bias currnent)
ana_glob_01 =  20 # CSA feedback resistance Typical value 7
ana_glob_02 = 147 # Electron or hole mode with reset on or off options. Typical value 147 for Electron reset off and 211 for electron reset on. Also selects polarity, pulse stretcher, PSC switch and polarity selection bias current
ana_glob_03 =  15 # Bias current of slow and fast shaper Typical value 31
ana_glob_04 =   0 # Calibration pulse up to 15fc charge. Value should be 0 to use external pulser
ana_glob_05 =   0 # Shaping time constant for slow shaper <3:2> 0-90ns, 1-160ns, Channel selection <1:0> 0-0,4,...124 + 129, 3-3,7,....127 +128. For ampCal, channel selection is not showing any affect.
ana_glob_06 =  32 # Reference current for the high speed discriminator Typical value 32 for 53uA
#ana_glob_07 = 100 # High speed discriminator threshold Typical value 100
ana_glob_07 =  50 # High speed discriminator threshold Typical value 100
ana_glob_08 =  25 # ADC low threshold <5:0> and DAC ADC_VREF_N for bit 6 Typical value 31
ana_glob_09 =  53 # ADC high threshold
ana_glob_10 = 186 # DAC ADC_VREF_T bit 6, Global ADC threshold (VREF_T) <5:0> and <8>: enable Typical value 188
ana_glob_11 =   0 # Triggerring conditions of calSTROBE and global gate backend Typical value 64
ana_glob_12 =  30 # NEW IN_CSAP register for PSC reference voltage control Typical value 30
ana_glob_13 =  60 # CSA back pads, push current to reduce noise Typical value 31 (CSA bias currnent)
ana_glob_14 =  27 # CSA buffer & cascode current control register Typical value 27
ana_glob_15 =  27 # SHAPERs buffer & cascode current control register Typical value 27
ana_glob_16 =  31 # Reserved, 6-bit CSA_BIAS 1V generator Typical value

## Register File settings: digital part control, row 190
#reg_file_00 = 0xXXXX # Not existing
reg_file_01 = 0x0000 # Timestamp counter gray
reg_file_02 =   0x00 # Reset
reg_file_03 =    0x0 # Channel Mask Enable, ACK TS ena
reg_file_04 = 0x0000 # Mask 013_000 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_05 = 0x0000 # Mask 027_014 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_06 = 0x0000 # Mask 041_028 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_07 = 0x0000 # Mask 055_042 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_08 = 0x0000 # Mask 069_056 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_09 = 0x0000 # Mask 083_070 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_10 = 0x0000 # Mask 097_084 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_11 = 0x0000 # Mask 111_098 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_12 = 0x0000 # Mask 125_112 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_13 = 0x0000 # Mask 129_126 use 0x3FFF to mask entirely. First 13 bits only counts
reg_file_14 = 0x0000 # TS Reset val
reg_file_15 = 0x0000 # CMD TS load
###reg_file_16 = 0x0000 # Spare
###reg_file_17 = 0x0000 # Spare
reg_file_18 = 0x0000 # Test_Ctrl 1
reg_file_19 = 0x0000 # Test_Ctrl 2
reg_file_20 = 0x0000 # Test_Ctrl 3
reg_file_21 = 0x0000 # Monitor ref
#reg_file_22 = 0x0000 # Chip Address, RO
reg_file_23 = 0x0000 # FIFO AFULL THR
reg_file_24 = 0x0000 # FIFO AFULL Counter
reg_file_25 = 0x0000 # eLink Mask
reg_file_26 = 0x0000 # Last Addr
reg_file_27 = 0x0000 # Status
reg_file_28 = 0x0000 # Status Mask
reg_file_29 = 0x0000 # FE Event Missd THR
reg_file_30 = 0x0000 # FE Event missed Counter
reg_file_31 = 0x0000 # SEU counter
###reg_file_32 = 0x0000 # eFuse !!!
###reg_file_33 = 0x0000 # eFuse !!!
'''

for edpb_idx in range( 0, len(hw) ):
  print("Setting custom for eDPB #", edpb_idx)
  for sts_iface in sts_ifaces[edpb_idx]:
    print("--> Setting custom for FEB #", sts_iface.iface)
    mask_settings = []

    # channel settings used range till 130 as test channel are also configured. In python last value is not included unless forced
    for ch in range( 0, 130 ):
      sts_iface.write(ch, 63, settings.ana_chan_63[ edpb_idx ][ sts_iface.iface ] )
      if settings.much_mode_on[ edpb_idx ][ sts_iface.iface ] == 1 :
        sts_iface.write(ch, 65, 228 )
      else :
        sts_iface.write(ch, 65, 244 )

      if ch == 0:
        print("Channel ", ch )
        print("----> Set register 63 to ", sts_iface.read(ch, 63 ) & 0xFF )
        print("----> Set register 65 to ", sts_iface.read(ch, 65 ) & 0xFF )

    # Global DAC settings
    print("Global DAC settings" )
    sts_iface.write_check( 130,  0, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  0 ] )
    sts_iface.write_check( 130,  1, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  1 ] )
    if settings.charge_type[ edpb_idx ][ sts_iface.iface ] == 1 :
      sts_iface.write_check( 130,  2, 163 ) # holes
    else :
      sts_iface.write_check( 130,  2, 131 ) # e-
    print edpb_idx, " ", sts_iface.iface
    sts_iface.write_check( 130,  3, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  2 ] )
    sts_iface.write_check( 130,  4, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  3 ] )
    sts_iface.write_check( 130,  5, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  4 ] )
    sts_iface.write_check( 130,  6, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  5 ] )
    sts_iface.write_check( 130,  7, settings.thr2_glb[ edpb_idx ][ sts_iface.iface ] )
    sts_iface.write_check( 130,  8, settings.vref_n[ edpb_idx ][ sts_iface.iface ]  )
    sts_iface.write_check( 130,  9, settings.vref_p[ edpb_idx ][ sts_iface.iface ] )

    if settings.asic_version[ edpb_idx ][ sts_iface.iface ] == 0 :
      sts_iface.write_check( 130, 10, settings.vref_t[ edpb_idx ][ sts_iface.iface ] )
    elif settings.asic_version[ edpb_idx ][ sts_iface.iface ] == 1 :
      # Keep only enable bit and pick the "old range"
      sts_iface.write_check( 130, 10, settings.vref_t[ edpb_idx ][ sts_iface.iface ] & 0x80 + 0x40 )

    sts_iface.write_check( 130, 11, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  6 ] )
    sts_iface.write_check( 130, 12, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  7 ] )
    sts_iface.write_check( 130, 13, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  8 ] )
    sts_iface.write_check( 130, 14, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][  9 ] )
    sts_iface.write_check( 130, 15, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][ 10 ] )
    sts_iface.write_check( 130, 16, settings.ana_glob[ edpb_idx ][ sts_iface.iface ][ 11 ] )

    if settings.asic_version[ edpb_idx ][ sts_iface.iface ] == 1 :
      # Set new reference voltage for fast discr side to 0 to keep old behavior
      sts_iface.write( 130, 17, 0 )
      sts_iface.write( 130, 18, settings.vref_t[ edpb_idx ][ sts_iface.iface ] & 0x3F )

    print("----> Set register 00 to ", sts_iface.read( 130,  0 ) & 0xFF )
    print("----> Set register 01 to ", sts_iface.read( 130,  1 ) & 0xFF )
    print("----> Set register 02 to ", sts_iface.read( 130,  2 ) & 0xFF )
    print("----> Set register 03 to ", sts_iface.read( 130,  3 ) & 0xFF )
    print("----> Set register 04 to ", sts_iface.read( 130,  4 ) & 0xFF )
    print("----> Set register 05 to ", sts_iface.read( 130,  5 ) & 0xFF )
    print("----> Set register 06 to ", sts_iface.read( 130,  6 ) & 0xFF )
    print("----> Set register 07 to ", sts_iface.read( 130,  7 ) & 0xFF )
    print("----> Set register 08 to ", sts_iface.read( 130,  8 ) & 0xFF )
    print("----> Set register 09 to ", sts_iface.read( 130,  9 ) & 0xFF )
    print("----> Set register 10 to ", sts_iface.read( 130, 10 ) & 0xFF )
    print("----> Set register 11 to ", sts_iface.read( 130, 11 ) & 0xFF )
    print("----> Set register 12 to ", sts_iface.read( 130, 12 ) & 0xFF )
    print("----> Set register 13 to ", sts_iface.read( 130, 13 ) & 0xFF )
    print("----> Set register 14 to ", sts_iface.read( 130, 14 ) & 0xFF )
    print("----> Set register 15 to ", sts_iface.read( 130, 15 ) & 0xFF )
    print("----> Set register 16 to ", sts_iface.read( 130, 16 ) & 0xFF )

    sts_iface.write_check( 192,  23, settings.regfile[ edpb_idx ][ sts_iface.iface ][  0 ] )
    sts_iface.write( 192,  24, 0 )
    sts_iface.write( 192,  27, 0 )
    sts_iface.write_check( 192,  29, settings.regfile[ edpb_idx ][ sts_iface.iface ][  1 ] )
    sts_iface.write( 192,  30, 0 )
    sts_iface.write( 192,  31, 0 )
    print("Register file readbacks" )
    print("----> Readback of register 23 ", sts_iface.read( 192, 23 ) & 0x3FFF )
    print("----> Readback of register 24 ", sts_iface.read( 192, 24 ) & 0x3FFF )
    print("----> Readback of register 27 ", sts_iface.read( 192, 27 ) & 0x3FFF )
    print("----> Readback of register 29 ", sts_iface.read( 192, 29 ) & 0x3FFF )
    print("----> Readback of register 30 ", sts_iface.read( 192, 30 ) & 0x3FFF )
    print("----> Readback of register 31 ", sts_iface.read( 192, 31 ) & 0x3FFF )

print("Done")

