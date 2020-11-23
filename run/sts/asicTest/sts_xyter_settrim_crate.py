#!/usr/bin/python

import time
import sys
import logging
import uhal
sys.path.append("../../../lib")
import global_dev_ctrl as gdc
import flim_dev_ctrl as fdc
import sts_xyter_dev_ctrl as sxdc
import numpy as np
import os
import sts_xyter_settings as settings
from os import path

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
for edpb_idx in range( 0, len(hw) ):
  sts_com.append( sxdc.sts_xyter_com_ctrl( hw[ edpb_idx ], "sts_xyter_dev") )
  flims.append(   fdc.flim_dev_ctrl(       hw[ edpb_idx ], "flim_ctrl_dev") )
  sts_com[ edpb_idx ].read_public_dev_info()

  afck_id.append( gdc.get_afck_id(   hw[ edpb_idx ], "global_dev") )
  afck_mac.append( gdc.get_afck_mac( hw[ edpb_idx ], "global_dev") )
  log.info("\nAFCK ID:  0x%04x", afck_id[ edpb_idx ] )
  log.info("\nAFCK MAC: %s",     afck_mac[ edpb_idx ] )

sts_ifaces = [[]]
for edpb_idx in range( 0, len(hw) ):
   sts_ifaces.append( [] )

   # iface_no: xyter_addr
   for i in range(0, sts_com[edpb_idx].interface_count()):
     if settings.iface_active[edpb_idx][i] == 1:
       sts_ifaces[edpb_idx].append(sxdc.sts_xyter_iface_ctrl(sts_com[edpb_idx],
                      i, settings.sts_addr_map[edpb_idx][i], afck_id[edpb_idx]))

   for sts_iface in sts_ifaces[edpb_idx]:
     sts_iface.set_link_break(settings.LINK_BREAK)

   print("This script assumes that:")
   print("- AFCK clocks are already configured")
   print("- eLink calibration results are available")
   log.info("Start to configure AFCK")

   lmask = ((1 << 5) - 1) ^ settings.LINK_BREAK
   lmask |= (lmask << 5)

   for sts_iface in sts_ifaces[edpb_idx]:
     sts_iface.fast_sync( settings.LINK_BREAK )

   for sts_iface in sts_ifaces[edpb_idx]:
     sts_iface.EncMode.write(sxdc.MODE_FRAME)
     # Set the link mask accordingly
     sts_iface.emg_write(192, 25, lmask)

   for sts_iface in sts_ifaces[edpb_idx]:
     print("\n### Setting trim values for STSXYTER #%d ###")%( sts_iface.iface )

     if ("XXXXXX_XXXX" == settings.date[ edpb_idx ][ sts_iface.iface ] ):
       print("No date, time defined for trim file in the settings for this board")
       print("=> Do nothing!!! check your settings, this board is marked active in settings")
       continue

     sts_iface.emg_write(192,25,lmask)

     # ---------------------------------------------------------------------------------------
     # ---------------------------------------------------------------------------------------
     testch = 58
     test_thr = 128
     test_delta_ch = 5
     test_npulse = 100

     setdisc_flag = 0

     #vref_n = 28    # Vref_N   AGH:  31    Test:  22
     #vref_p = 56    # Vref_P   AGH:  48    Test:  51
     #vref_t = 188   # Vref_T   AGH: 188    Test: 184         bit7: enable   5..0: threshold

     read_nword = 500

     shslowfs = 0  # 0,..,3 for FS=90,160,220,280ns

     # ---------------------------------------------------------------------------------------
     # ---------------------------------------------------------------------------------------

     #-----------------------------------------------------------------------------------------
     #                                SETTINGS for TRIM
     #-----------------------------------------------------------------------------------------
     trim_offset = 0;

     ch_min = 0;
     ch_max = 128;

     d_min = 0;
     d_max = 31;

     trim_ok_min = 0;
     trim_ok_max = 255;

     trim_ok_avg = 0;
     trim_ok_n = 0;

     trim_corr_flag = 1;

     #Holes from get_trim.py for vacuum feb-c (globtop)
     filename_trim_g = "trim_cal/"\
                     "trim_cal_200707_gsi_feb_c_89_fast_39_adc_522217948_200.0_"\
                     "holes.txt"

     #Holes from get_trim.py for vacuum feb-c (globtop) wide range
     filename_trim_gw = "trim_cal/"\
                     "trim_cal_200709_gsi_feb_c_89_fast_14_adc_582218515_210.0_"\
                     "holes.txt"

     # Holes from get_trim.py for box feb-c (blue cover)
     filename_trim_b = "trim_cal/"\
                     "trim_cal_200615_gsi_feb_c_89_fast_39_adc_522217948_200.0_"\
                     "holes.txt"

     # Holes from trim_sts.py for vacuum feb-c with Si-Junction MUCH mode
     filename_trim_si= "trim_cal/"\
                     "trim_cal_200714_gsi_feb_c_89_fast_22_adc_582218430_250.0_"\
                     "holes.txt"

     # Holes from trim_sts.py for vacuum feb-c, 241Am test 
     filename_trim_am= "trim_cal/"\
                     "trim_cal_201120_gsi_feb_c_89_fast_32_adc_584618535_66.0_"\
                     "holes.txt"
     #Decide which calibration to load
     filename_trim = filename_trim_am

     assert path.exists(filename_trim)

     data = np.genfromtxt( filename_trim )
     trim = [ [0 for d in range(d_min,d_max+1)] for ch in range(ch_min, ch_max)]
     #-------------------------------------------------------------------------------------
     #                                END of SETTINGS
     #-------------------------------------------------------------------------------------

     chn = data[:,1]
     disc_thr = data [:,][:,2:34]

     ## reading trim file
     for ch in range (ch_min,ch_max):
       for d in range (d_min,d_max+1):
         trim[ch][d] = int(disc_thr[:,d][ch:ch+1])
         if (trim[ch][d] < 0):
           trim[ch][d] = 0
         if (trim[ch][d] > 255):
           trim[ch][d] = 255

     print "\n"

     ##correct trim outliers
     if (trim_corr_flag == 1):
       for ch in range(ch_min, ch_max):
         trim_ok_avg = 0
         trim_ok_n = 0
         for d in range(d_min,d_max+1):
           if ((trim[ch][d] >= trim_ok_min) and (trim[ch][d] <= trim_ok_max)):
             trim_ok_avg += trim[ch][d]
             trim_ok_n += 1
         trim_ok_avg = int(trim_ok_avg/trim_ok_n + 0.5)
         for d in range(d_min,d_max):
           if ((trim[ch][d] < trim_ok_min) or (trim[ch][d] > trim_ok_max)):
             print "Corrected channel ", '{:4d}'.format(ch), "   disc: ", '{:3d}'.format(d), "   from " , trim[ch][d], "  to ", '{:3d}'.format(trim_ok_avg), "\n"
             trim[ch][d] = trim_ok_avg

     #
     '''
     print " -------------Trim default values--------------"
     print " "
     for ch in range(ch_min,ch_max):
       print "ch", '{:4d}'.format(ch),
       for d in range (d_min,d_max):
         print '{:4d}'.format(trim[ch][d]),
       print "\n"

     print " "

     print " "
     '''
     print " -------------Writing trim values---------------"

     for ch in range(ch_min,ch_max):
       print "ch: ", ch,
       for d in range (d_min,d_max):
         set_val_trim = trim[ch][d] + trim_offset
         if (set_val_trim < 0):
           set_val_trim = 0
         if (set_val_trim > 255):
           set_val_trim = 255
         print set_val_trim,
         disc = 61- 2*d
         sts_iface.write_check(ch,disc,set_val_trim)
       print trim[ch][31],
       sts_iface.write_check(ch,67,trim[ch][31])
       print str(sts_iface.read(ch,67) & 0xff )
       #print "\n"

     print " "
     print "<<<------------ DONE: set trim values ------------->>>"
     #print " "
     #print " "
     #print ">>------------ READING trim values ---------------<<"

     #for ch in range(ch_min,ch_max):
       #print "\nch: ", ch,
       #for d in range (d_min,d_max):
         #disc = 61- 2*d
         #val_f = sts_iface.read(ch,disc) & 0xff
         #print '{:4d}'.format(val_f),
       #print '{:4d}'.format(sts_iface.read(ch,67) & 0xff ),
       #print "\n"
