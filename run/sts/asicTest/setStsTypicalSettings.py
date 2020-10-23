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
fh = logging.FileHandler("./logs/" + sys.argv[0].replace('py', 'log'), 'w')
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

## Channel settings
ana_chan_63 = 144 # 8-bit ADC control register Typical value 144
ana_chan_65 = 244 # Typical value for STS
#ana_chan_65 = 228 # Typical value for MUCH
ana_chan_67 = 36 # 0x80 #  36 # Fast discriminator threshold, Typical value 36

## Global DAC settings
ana_glob_00 =  31 # CSA front pads, push current to reduce noise Typical value 31 (CSA bias currnent)
ana_glob_01 =  63 #15 # CSA feedback resistance Typical value 7
# +64 from MUCH mode
ana_glob_02 = 163 # Electron or hole mode with reset on or off options. Typical value 147 for Electron reset off and 211 for electron reset on. Also selects polarity, pulse stretcher, PSC switch and polarity selection bias current
                  #  163: holes, reset off    227 : holes, reset on
ana_glob_03 =  31 # Bias current of slow and fast shaper Typical value 31
ana_glob_04 =  0 # Calibration pulse upto 15fc charge. Value should be 0 to use external pulser
ana_glob_05 =  12+3 # Shaping time constant for slow shaper <3:2> 0-90ns, 1-160ns, Channel selection <1:0> 0-0,4,...124 + 129, 3-3,7,....127 +128. For ampCal, channel selection is not showing any affect.
ana_glob_06 =  32# Reference current for the high speed discriminator Typical value 32 for 53uA
ana_glob_07 =  39 # High speed discriminator threshold Typical value 100
ana_glob_08 =  22 # ADC low threshold <5:0> and DAC ADC_VREF_N for bit 6 Typical value 31
ana_glob_09 =  52 # 54 ADC high threshold
ana_glob_10 =  51 # 58 DAC ADC_VREF_T bit 6, Global ADC threshold (VREF_T) <5:0> and <8>: enable Typical value 188
ana_glob_11 =  64 # Triggerring conditions of calSTROBE and global gate backend Typical value 64
ana_glob_12 =  30 # NEW IN_CSAP register for PSC reference voltage control Typical value 30
ana_glob_13 =  31 # CSA back pads, push current to reduce noise Typical value 31 (CSA bias currnent)
ana_glob_14 =  27 # CSA buffer & cascode current control register Typical value 27
ana_glob_15 =  27 # SHAPERs buffer & cascode current control register Typical value 27
ana_glob_16 =  88 # Reserved, 6-bit CSA_BIAS 1V generator Typical value
ana_glob_17 = 0

#digi_glob_02_reset = 0x2a
#digi_glob_04 = 0x01  #
#digi_glob_05_12 = 0x0000  #   0x00: enable all channels   0x3fff: disable

for edpb_idx in range( 0, len(hw) ):
  print("Typical setting for eDPB #", edpb_idx)
  for sts_iface in sts_ifaces[edpb_idx]:
    print("--> Typical setting for FEB #", sts_iface.iface)
    mask_settings = []

    # channel settings used range till 130 as test channel are also configured. In python last value is not included unless forced
    #for ch in range( 0, 0 ):
    for ch in range( 0, 130 ):
#      print("Channel ", ch )
      sts_iface.write(ch, 63, ana_chan_63 )
#      print("----> Set register 63 to ", sts_iface.read(ch, 63 ) & 0xFF )
      sts_iface.write(ch, 65, ana_chan_65 )
#      print("----> Set register 65 to ", sts_iface.read(ch, 65 ) & 0xFF )
      sts_iface.write(ch, 67, ana_chan_67 )
#      print("----> Set register 65 to ", sts_iface.read(ch, 67 ) & 0xFF )
      # disc settings
      #for d in range (0,31):
      #   n = 2*d+1
      #   sts_iface.write(ch, n, 128 )

    # Global DAC settings
#    print("Global DAC settings" )
    sts_iface.write( 130,  0, ana_glob_00 )
    sts_iface.write( 130,  1, ana_glob_01 )
    sts_iface.write( 130,  2, ana_glob_02 )
    sts_iface.write( 130,  3, ana_glob_03 )
    sts_iface.write( 130,  4, ana_glob_04 )
    sts_iface.write( 130,  5, ana_glob_05 )
    sts_iface.write( 130,  6, ana_glob_06 )
    sts_iface.write( 130,  7, ana_glob_07 )
    sts_iface.write( 130,  8, ana_glob_08 )
    sts_iface.write( 130,  9, ana_glob_09 )
#    sts_iface.write( 130, 10, ana_glob_10 )
    sts_iface.write( 130, 11, ana_glob_11 )
    sts_iface.write( 130, 12, ana_glob_12 )
    sts_iface.write( 130, 13, ana_glob_13 )
    sts_iface.write( 130, 14, ana_glob_14 )
    sts_iface.write( 130, 15, ana_glob_15 )
    sts_iface.write( 130, 16, ana_glob_16 )
    sts_iface.write( 130, 17, ana_glob_17 )

    sts_iface.write( 130, 10, 0x80)
    sts_iface.write( 130, 18, (ana_glob_10 & 0x3F) + 0x40 )      # select largest Vref_t range

    sts_iface.write( 192, 3, 0x1 )
    for reg in range(4,13):
      sts_iface.write( 192, reg, 0X0 )    # disable all: 0x3fff
    sts_iface.write( 192, 13, 0x3f )

    '''
    sts_iface.write( 192, 4, 0x3fff )
    sts_iface.write( 192, 5, 0x3fff )
    sts_iface.write( 192, 6, 0x3fff )
    sts_iface.write( 192, 7, 0x1ddd )
    sts_iface.write( 192, 8, 0x3777 )
    sts_iface.write( 192, 9, 0x1ddd )
    sts_iface.write( 192, 10, 0x3777 )
    sts_iface.write( 192, 11, 0x1ddd )
    sts_iface.write( 192, 12, 0x3fff )
    sts_iface.write( 192, 13, 0xf )
    '''
    # Reset of counters, fifos, AFE
    sts_iface.write( 192, 2, 0x2a )
    sts_iface.write( 192, 2, 0 )

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
    print("----> Set register 17 to ", sts_iface.read( 130, 17 ) & 0xFF )
    print("----> Set register 18 to ", sts_iface.read( 130, 18 ) & 0xFF )

    print("----> Set ch 83 register 67 to ", sts_iface.read( 83, 67 ) & 0xFF )

    for maskreg in range(4,13):
      print("----> Set mask register 192,",maskreg," to ", sts_iface.read( 192, maskreg ) & 0x3FFF )


'''
    print("Triggering groups...")
    for grp in range(4):
      print grp
      sts_iface.write( 130,  5, grp )
      for i in range(20+10*grp):
        sts_iface.write( 130, 11, 0x80 )
        sts_iface.write( 130, 11, 0x00 )
        #sts_iface.write( 130, 11, 0xc0 )
        #sts_iface.write( 130, 11, 0x40 )
'''

print("Done")
