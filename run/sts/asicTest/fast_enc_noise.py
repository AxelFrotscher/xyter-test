#!/usr/bin/python
import uhal
import os
import sys
import pickle
import time
import struct

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
#from drawnow import *
import pyqtgraph as pg
import math
from PyQt4 import QtCore, QtGui,uic
import pyqtgraph as pg
import random
import numpy as np

import logging
sys.path.append("../../../lib")
import global_dev_ctrl as gdc
import flim_dev_ctrl as fdc
import sts_xyter_dev_ctrl as sxdc

import sts_xyter_settings as settings
from os import path
#import usbtmc
import time
#instr =  usbtmc.Instrument(1689, 1034)

#Below we set active links
# 1 - link is working
# 0 - we simulate, that the link is broken
LINK_BREAK = 0b00001
LINK_ASIC =  0b00001

log = logging.getLogger()
# This is a global level, sets the miminum level which can be reported
log.setLevel(logging.DEBUG)
sh = logging.StreamHandler(sys.stderr)
sh.setLevel(logging.INFO)
log.addHandler(sh)
fh = logging.FileHandler("./logs/" + sys.argv[0].replace('py', 'log'), 'w')
#fh = logging.FileHandler("/home/ststest/cbmsoft/python_ipbus/run/sts/asicTest/logs/fast_enc_noise.log", 'w')

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
  for i in range(0, sts_com[edpb_idx].interface_count()):
    if settings.iface_active[edpb_idx][i] == 1:
      sts_ifaces[edpb_idx].append(sxdc.sts_xyter_iface_ctrl(sts_com[edpb_idx],
                      i, settings.sts_addr_map[edpb_idx][i], afck_id[edpb_idx]))

# ------------- Writing and Reading register in the STS_XYTER ------------------
# --- Confirming MODE_FRAME ------
#EncMode.write(MODE_FRAMEchrg 250    1000 1000 1000 1000 1000 )
#time.sleep(0.000002)
# --------------- Creating object ---------------------
#sts=stsxyter(15)
# ----------- Set the link mask accordingly -----------
sts = sts_ifaces[0][0]
#sts1 = sts_ifaces[0][0]

t0 = time.time()
# --------------- Creating object ---------------------
#sts=stsxyter(15)
# ----------- Set the link mask accordingly -----------
lmask = ((1 << 5) - 1) ^ LINK_ASIC
lmask |= (lmask << 5)
sts.emg_write(192, 25, lmask)
confirm = False
print "Link Mask " + hex(sts.read(192, 25))
#app = QtGui.QApplication(sys.argv)

def input_float(prompt):
  while True:
    try:
      return float(raw_input(prompt))
    except ValueError:
      print('That is not a valid current')

def config( sts ):

  # --------------AFE Registers -----------------
  print "\nFull set of registers for the AFE. Typical values\n"
  print "------------------ooooOOOOOoooo-------------------\n"

  for ch in range (ch_min, ch_max):
    for d in range (d_min, d_max):
      n = 2 * d + 1
      #sts.write_check(ch, n, 128)  # Don't reset trim for ADC
    sts.write_check(ch, 63, 144)
    sts.write_check(ch, 65, 244 - 16 * much_modifier * 1)  # forced overwrite
    #sts.write_check(ch, 67, 36)    # Don't reset trim for TDC

  sts.write_check(130, 0, csa_current)   #Typ: 31, Max: 63
  sts.write_check(130, 1, 63 + 64 * much_modifier) #Typ value for Ileak = 0nA #31
  sts.write_check(130, 2, 163)   #electrons: 131, holes: 163
  sts.write_check(130, 3, 31)    #Typ: 31, Max: 63
  sts.write_check(130, 4,  0)
  sts.write_check(130, 5,  0)      # 0
  sts.write_check(130, 6, 32)   #Typ: 32, Max: 63
  sts.write_check(130, 7, thr2_glb)  # 15
  sts.write_check(130, 8, vref_n)
  sts.write_check(130, 9, vref_p)
  sts.write_check(130, 10, 128)
  sts.write(130, 18, 0x40 + (vref_t&0x3f))  # hardcoded vref_t range = b001 which is coarsest range
  sts.write_check(130,11, 64)
  sts.write_check(130,12, 30)
  sts.write_check(130,13, csa_current)   #Typ: 31, Max: 63
  sts.write_check(130,14, 27)   #Typ: 27, Max: 63
  sts.write_check(130,15, 27)   #Typ: 27, Max: 63
  sts.write_check(130,16, 91 - 3)
  #sts.write(130,17, 0)
  #sts.write(130,18, 186)
  #sts.write(130,18, 63)   #controls VREFT

  for i in range(3, 14):
    sts.write_check(192, i, 0x0)

  print "{0}, 63, {1}".format(rdch, sts.read(rdch, 63) & 0xff)
  print "{0}, 65, {1}".format(rdch, sts.read(rdch, 65) & 0xff)
  print "{0}, 67, {1}".format(rdch, sts.read(rdch, 67) & 0xff)

  # ----------- Resetting counters and FIFO channels -----------

  sts.write(192, 2, 128)
  sts.write(192, 2,   0)
  # enabling counters readout
  sts.write_check(130, 11, 0)

  print "\nReading the re ASIC registers\n "
  print "ch selected to check-up ASIC mode:\n", rdch
  print str(rdch), " , 63, ", '{:5d}'.format(sts.read(rdch, 63) & 0xff)
  print str(rdch), " , 65, ", '{:5d}'.format(sts.read(rdch, 65) & 0xff)

  print "\nASIC analog registers:\n"
  for reg in range(0,23,1):
      print "130, {0:2d}, {1}".format(reg, sts.read(130, reg) & 0xff)

  print "\nASIC file registers:\n"
  asic_reg = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 19, 20, 22,
              23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]
  for register in asic_reg:
      print "192, {0}, {1}".format(register, sts.read(192, register) & 0xff)

def check_trim(sts, prompt):
  ivp = 0
  d_counter = 0

  # ---------------  Polarity selection --------------
  pol = prompt

  if (pol == 1):
    sts.write_check(130,2,163)   #  163 holes     131 electrons
    print "\n____HOLES MODE____\n"
    filename_scan = filename_trim + "_holes.txt"

  if (pol == 0):
    sts.write_check(130,2,131)   #  163 holes     131 electrons
    print "\n____ELECTRONS MODE____\n"
    filename_scan = filename_trim + "_elect.txt"

  myfile = open(filename_scan, "w+")
  assert path.exists(filename_scan)

  # ---------------------------------------------------
  print "\n......Setting ADC reference voltages......\n"
  sts.write_check(130, 8, vref_n)
  sts.write_check(130, 9, vref_p)
  sts.write_check(130,10, vref_t)
  #sts.write(130, 18, vref_t_r)  # Only for XYTER2.1
  print "VRef_N: ", sts.read(130,  8) & 0xff
  print "VRef_P: ", sts.read(130,  9) & 0xff
  print "VRef_T: ", sts.read(130, 10) & 0xff

  print "\n......Setting FAST reference voltages......\n"
  sts.write_check(130, 7, thr2_glb)
  print "Thr2_global: ", sts.read(130, 7) & 0xff

  # channel mask disable. All channels enabled
  sts.write_check(192, 3, 0)

  ### resets
  print "\n1. Resetting front-end channels "
  print "2. Resetting ADC counters"
  print "3. Reset channel fifos"
  sts.write_check(192,2,42)
  time.sleep(0.00001)
  sts.write_check(192,2,0)

  vcnt = [[[0 for vp in range(vp_min, vp_max, vp_step)] for d in range(d_min,d_max)]
                                                for ch in range(ch_max/ch_step)]
  #vcnt = [[[0 for vp in range(5000)] for d in range(20,d_max)]
  #                                   for ch in range(ch_max/ch_step)]
  nd = 31
  nthr = 256
  nch = 256

  print "\n......Start acquiring data......"
  # loop over test charge range
  for vp in range(vp_min, vp_max, vp_step):
    a = (vp * 14.32) / 255. * (1 + 5 * much_modifier) # Pulse height value in fC

    if ((vp < vp_min) or (vp > vp_max)):
      print "Pulse amplitude should be in range: {0}-{1}. Currently set to {2}\n"\
            .format(vp_min, vp_max, vp)

    sts.write_check(130, 4, vp)
    print "\n\nvp: {0:3d} ({1:2f} fC), vpulse: {2}"\
           .format(vp, a, sts.read(130, 4) & 0xFF)

    #loop over groups
    for grp in range(grp_min, grp_max):
      #max_ch_grp = 124+ grp
      # Included the slow shaper configuration (90,130,220,280ns)
      grp_shslow = ((shslowfs & 0x3) << 2 | (grp & 0x3))

      # ADC counters resets
      sts.write_check(192, 2, 63)
      time.sleep(0.00001)
      sts.write_check(192, 2, 0)
      sts.write_check(130, 5, grp_shslow)

      # Number of trigger pulses
      for npulse in range(0, loop_max):
        #print " loop ", npulse, "\n"
        # Pulse triggering
        sts.write_check(130, 11, 128)
       # time.sleep(0.001)
        sts.write_check(130, 11, 0)

        ## read counters
      ch_counter = 0
      for ch in range(grp, ch_max, 4):
        #print "ch  ", ch,
        cnt_val = 0
        d_counter = 0
        #cnt_val =0
        for d in range(d_min, d_max):
          count = d * 2
          #print "d: ", d, " counter: ", count, "\n"
          cnt_val = sts.read(ch, count)
          vcnt[ch][d_counter][ivp] = cnt_val
          d_counter += 1
          #print cnt_val,
        #print "\n"
        ch_counter += 4

      ch_counter = grp
      for ch in range(grp, ch_max,4):
          if(ch == 45):
            print ""
          if(ch == 44 or ch == 45):
            print "cnt_ch: {:3d}".format(ch),
          d_counter = 0
          for d in range(d_min, d_max):
            if(ch == 44 or ch == 45):
              print '{0}'.format(vcnt[ch][d_counter][ivp]),
            d_counter+= 1
          ch_counter += 4
          #print "\n"
    ivp += 1

  ivp = 0
  for vp in range(vp_min, vp_max, vp_step):
    ch_counter = 0
    for ch in range(ch_min, ch_max, ch_step):
      if(ch == 1):
        print "\nvp {0:3d} ch: {1:3d}: ".format(vp, ch),
      myfile.write("vp {0:3d}  ch {1:3d}: ".format(vp,ch))
      d_counter = 0
      for d in range(d_min, d_max):
        if(ch%10 == 1):
          print '\n{0}'.format(vcnt[ch][d_counter][ivp]),
        myfile.write('{:6d}'.format(vcnt[ch][d_counter][ivp]))
        d_counter += 1
      ch_counter += 1
      myfile.write("\n")
    ivp += 1

  print "\n............. Quick noise- linearity analysis ............\n"
  d_list = [27, 28, 29, 30]          # Defining used discriminators, 26 missin'
  d_len = len(d_list)
  print "d_len: {}".format(d_len)

  hnoise = [[0 for d in range(d_len)] for ch in range(ch_min, ch_max)]
  hmean = [[0 for d in range(d_len)] for ch in range(ch_min, ch_max)]
  ch_array = [ch for ch in range(ch_min, ch_max)]
  hnoise_avg = [0 for ch in range(ch_min, ch_max)]
  hmean_avg = [0 for ch in range(ch_min, ch_max)]

  vcnt = np.clip(vcnt, 0, loop_max) # prohibit overshoot
  ## Axel
  vp_distr = [vp for vp in range(vp_min, vp_max, vp_step)]
  for ch in range(ch_min, ch_max):
    for d in d_list:
      derivative = np.gradient(vcnt[ch][d]) # derivative of S-Curve
      if(np.sum(derivative) > 0):           # exclude fully saturated channels
        # Expectation value of derivative
        hmean[ch - ch_min][d - d_list[0]] = \
               np.sum(derivative * vp_distr)/np.sum(derivative)

        hnoise[ch - ch_min][d - d_list[0]] = np.sqrt(
               np.sum(np.square(vp_distr - hmean[ch - ch_min][d - d_list[0]]) *
               derivative)/np.sum(derivative))
      else:
        break
    hmean_avg[ch - ch_min] = np.mean(hmean[ch - ch_min])
    hnoise_avg[ch - ch_min] = np.mean(hnoise[ch - ch_min]) * (336 + much_modifier * 1761)
    print "Ch: {0:3d} enc: {1:4.1f} Flip charge mean: {2:3.1f}"\
        .format(ch, hnoise_avg[ch - ch_min], hmean_avg[ch - ch_min])

  ## ----------------- Plot noise and linearity analysis ---------------------##
  f = plt.figure()
  plt.step(ch_array,hnoise_avg)
  plt.xlabel('Channel number')
  plt.ylabel('ENC[electrons]')
  plt.title('Quick noise estimation')
  plt.grid(True, linestyle='--', color='0.75')
  #plt.show()

  f.savefig(filename_scan + '.png', bbox_inches = 'tight' )
  myfile.close()
# ---------------------------------------------------------------------------------------
rdch = 63
test_thr = 129

much_modifier = 0       # Set 1 for MUCH mode, 0 for STS mode
loop_max = 100          # Pulses per Charge

ch_min = 0              # Minimum channel of XYTER
ch_max = 128            # Maximum channel of XYTER
ch_step = 1             # Channel Step: 1: each channel, 2: every second channel

d_min = 0               # Minimum discriminator (highest threshold)
d_max = 32              # Maximum discriminator (lowest threshold)

ivp = 0
vp_min = 40             # Minimum charge injected
vp_max = 80             # Maximum charge injected
vp_step = 1             # Charge steps

grp_min = 0
grp_max = 4

# --------------------------- ADC settings --------------------------------------------
vref_n = 22    # Vref_N   AGH:  31    Test:  22
vref_p = 52    # Vref_P   AGH:  48    Test:  51
vref_t = 128 + vref_p -1  # Vref_T  18 AGH: 188    Test: 184         bit7: enable   5..0: threshold
#vref_t_r = 128 + vref_t -1
# -------------------------------------------------------------------------------------
# --------------------------- FAST disc settings --------------------------------------
thr2_glb = 39
# -------------------------------------------------------------------------------------
#csa_current = 60
offset = 0

# -------------------------- CSA current settings ------------------------------------
csa_current = 31
sts.write_check(130, 0, csa_current)
sts.write_check(130, 13, csa_current)

# -------------------------------------------------------------------------------------
read_nword = 50
shslowfs = 0  # 0,..,3 for FS=90,160,220,280ns

# -------------------------------
#      Saving file details
# -------------------------------
sensor_on = 0
sensor_hv = 150
pogo_on = 0
#thr = 350

print "\n......Setting ADC reference voltages......\n "

sts.write_check(130, 8,  vref_n)
sts.write_check(130, 9,  vref_p)
sts.write_check(130, 10, 128)
sts.write(130, 18, 0x40 + (vref_t&0x3f))  # hardcoded vref_t range = b001 which is coarsest range
print "VRef_N: ", sts.read(130,  8) & 0xff
print "VRef_P: ", sts.read(130,  9) & 0xff
print "VRef_T: ", sts.read(130, 10) & 0xff

print "\n......Setting FAST reference voltages......\n"

sts.write_check(130, 7, thr2_glb)
print "Thr2_global: ",sts.read(130, 7) & 0xff

cal_flag = 1         #Enable or disable the use of the calibration file
feb_serial_nr = 65
asic_test_nr = 4.9

date = time.strftime("%y%m%d%H%M")
#date = "180320"
module_nr = "T-1"

#Files to be created to store voltage scan data
filename_trim = "pscan_files/pscan_{0}_asic_test_{1}_asic_addr_{2}_{3}{4}{5}"\
                 .format(date, asic_test_nr, sts.read(192,22), sts.read(130,9) & 0xff,
                  sts.read(130,8)  & 0xff, sts.read(130,10) & 0xff)

if (sensor_on == 1):
  filename_trim = filename_trim + "_sensor_6x4_"+ str(sensor_hv)
if (pogo_on == 1):
  filename_trim = filename_trim + "_pogo_pin"

pol = 1                                       # Holes
config(sts)
time.sleep(1)
print ".... Checking ADC and FAST trim form STS mode: {0} ....... ".format(pol)
check_trim(sts, pol)
