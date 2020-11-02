#!/usr/bin/python
import random
import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('TKagg')
import matplotlib.ticker as ticker
import math
import uhal
import sys
import pickle
import time
import struct
import logging
sys.path.append("../../../lib")
import global_dev_ctrl as gdc
import flim_dev_ctrl as fdc
import sts_xyter_dev_ctrl as sxdc
import sts_xyter_settings as settings

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
      sts_ifaces[edpb_idx].append(sxdc.sts_xyter_iface_ctrl(sts_com[edpb_idx],
               i, settings.sts_addr_map[edpb_idx][i], afck_id[edpb_idx]))

# ----------------- Writing and Reading register in the STS_XYTER ----------------------
# --- Confirming MODE_FRAME ------
#EncMode.write(MODE_FRAMEchrg 250    1000 1000 1000 1000 1000 )
#time.sleep(0.000002)
# --------------- Creating object ---------------------
#sts=stsxyter(15)

# ----------- Set the link mask accordingly -----------
if not (len(sys.argv) == 4):
  print "Script has to be called with [edpb_id] [afck_id] [channel number]"
  quit();
if int(sys.argv[3]) < 0 or int(sys.argv[3]) > 127:
  print "Invalid test channel {}. Must be between 0 and 127".format(sys.argv[3])
  quit();

sts = sts_ifaces[int(sys.argv[1])][int(sys.argv[2])]
#sts1 = sts_ifaces[0][0]

t0 = time.time()

lmask = ((1<<5)-1) ^ LINK_BREAK
lmask |= (lmask << 5)
sts.emg_write(192,25,lmask)
confirm = False
print "Link Mask" + bin(lmask)
#app = QtGui.QApplication(sys.argv)

vref_n = 22      # Vref_N   AGH:  31    Test:  22
vref_p = 58      # Vref_P   AGH:  48    Test:  51
vref_t = 128 + vref_p - 2
#vref_t_r = 176  # Vref_T   AGH: 188    Test: 184         bit7: enable   5..0:

testch = int(sys.argv[3])       # Channel to be tested
thr2_glb = 22                   # TDC Threshold

d_min = 0                       # Minimum and maximum discriminator
d_max = 32

ch_min = 0                      # Minimum and maximum charge injected
ch_max = 255
#ch_max = ch_min+5

test_delta_ch = 1               # Charge Step size for scanning response
test_thr = 128                  # Default trim value
grp_min = 0
grp_max = 4

much_strength = 0               # Input range from STS (0) or MUCH (1)

csa_in = 31
test_npulse = 2 * 80            # Number of Pulses per charge step

vp_cnt = [0 for d in range(ch_min,ch_max, test_delta_ch)]
cnt = [[0 for c in range(ch_min, ch_max, test_delta_ch)] for d in range(d_min,d_max)]
x_n = [0 for c in range(ch_min, ch_max, test_delta_ch)]
vp_set = [0 for d in range(d_min,d_max)]
vp_mean = [0 for d in range(d_min,d_max)]
vp_sigma = [0 for d in range(d_min,d_max)]

# ---------------------------------------------------------------------------------------
def scurves(sts,vref_n,vref_p,vref_t):
    # Default trim values
    thr_arr = [128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,
               128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128]
    thr_fast = 36           # TDC fast global threshold
    setdisc_flag = 0        # overwrite bool of trim for selected channel
    read_nword = 50
    shslowfs = 0  # 0,..,3 for FS=90,160,220,280ns

    # ----------------------------------------------ch_min----------------------
    pol = 1

    if (pol == 1):
      sts.write_check(130, 2, 163)   #  163 holes, 227 holes reset on ,   131 electrons, 195 electrons reset on
      print "\n____HOLES MODE____\n"

    if (pol == 0):
      sts.write_check(130, 2, 131)   #  163 holes     131 electrons
      print "\n____ELECTRONS MODE____\n"

    sts.write_check(130,  0, csa_in)
    sts.write_check(130, 3, 31)
    sts.write_check(130, 13, csa_in)

    for i in range(4, 13):
      sts.write_check(192, i, 0x0000)
    sts.write_check(192, 13, 0x00)
    sts.write_check(192, 3, 1)

    # disable other test modes
    sts.write_check(192, 18, 0)
    sts.write_check(192, 20, 0)

    print "test channel {}".format(testch)
    testgrp = testch % 4

    regval = testgrp + 4 * shslowfs
    sts.write_check(130, 5, testgrp)
    print " group selected {} \n".format(testgrp)

    #sts.write_check(130, 1, 7)

    print "\n......Setting ADC reference potentials ......\n"

    sts.write_check(130, 8, vref_n)
    sts.write_check(130, 9, vref_p)
    sts.write_check(130, 10, 128)
    sts.write(130, 18, 0x40 + (vref_t&0x3f))  # hardcoded vref_t range = b001 which is coarsest range

    print "\nADC Reference potentials"
    print "VRef_N: {}".format(sts.read(130, 8) & 0xff)
    print "VRef_P: {}".format(sts.read(130, 9) & 0xff)
    print "VRef_T: {} \n".format(sts.read(130, 10) & 0xff)

    print "......Setting FAST disc reference potential ...... "
    sts.write(130, 7, thr2_glb)
    #sts.write(130,17,  0) # Set new Vref Fast polarity to 0 to get same as for 2.0

    print "\nFAST Reference potentials"
    print "Thr2_global: {}\n".format(sts.read(130, 7) & 0xff)

    print "Vref_n {}".format(sts.read(130, 8) & 0xFF)
    print "Vref_p {}".format(sts.read(130, 9) & 0xFF)
    print "Vref_t {}".format(sts.read(130, 10) & 0xFF)
    print "Thr2_glb {}".format(sts.read(130, 7) & 0xFF)

    print "test thr {}".format(test_thr)

    # implement much mode for detection
    sts.write_check(130, 1, 63 + 64 * much_strength)   #Typ value for Ileak = 0nA
    for ch in range(0,128):
        sts.write_check(ch, 65, 244 - 16 * much_strength)
    # set threshold for all disc's of test channel
    if(setdisc_flag):
      print "set disc. thresholds: ",
      for d in range (0,31):
        n = 2 * d + 1
        sts.write_check(testch, n, test_thr)
      sts.write_check(testch, 67, thr_fast)
    print "fast: {}\n".format(str(sts.read(testch, 67)))

    # resets
    print "Resetting front-end channels "
    print "Resetting ADC counters"
    print "Reset channel fifos"
    sts.write_check(192, 2, 42)
    time.sleep(0.00001)
    sts.write_check(192, 2, 0)
    sts.write_check(130, 11, 0)

    nd = 32
    nthr = 256
    nch = 256
    ch_cnt = 0

    sts.write_check(130, 0, csa_in)
    sts.write_check(130, 13, csa_in)

    print "test charge",
    create_graph(sts, num_discr, testch)
    for ch in range (ch_min, ch_max, test_delta_ch):
     # sts.write_check(130,11,0)
      sts.write_check(130, 4, ch) # test pulse Recommended value between 80-200
      print ch,
      sys.stdout.flush()
      x_n[ch_cnt] = ch
      x = np.array(x_n[:ch_cnt])
      data_n = np.array([])
      plt.pause(0.5)

      # Reset ADC counters
      sts.write_check(192, 2, 63)
      time.sleep(0.00001)
      sts.write_check(192, 2, 0)
      #for grp in range(grp_min, grp_max):
       # sts.write_check(130,5,grp)
      # Generate calib pulses
      sts.write_check(130, 5, testgrp)

      for i in range (0, test_npulse):  # Send test pulses
        sts.write_check(130, 11, 128)
        sts.write_check(130, 11, 0)

      for d in range(d_min,d_max):    # Read out registered hits
        n = 2 * d
        cnt[d][ch_cnt] = sts.read(testch, n)
        data_n = np.array(cnt)
        #time.sleep(0.05)

      for d in range(d_min, d_max):
        data = data_n[d,:ch_cnt]
        lines[d].set_data(x, data_n[d,:ch_cnt])

      ch_cnt += 1

    f1 = open("sts_test_mode2.txt", "w+")

    print
    ch_cnt = 0
    for ch in range (ch_min, ch_max, test_delta_ch):
        f1.write("chrg")
        f1.write('{:4d}'.format(ch))
        print "chrg {:3d}".format(ch),

        for d in range (0,32):
            val = cnt[d][ch_cnt]
            f1.write('{:5d}'.format(val))
            print '{:4d}'.format(val),
        ch_cnt += 1
        print " "
        f1.write("\n")
    print
    raw_input()

axarr = None
f = None
lines = []

num_discr = 32

def create_graph(sts, num_discr, testch):

    global axarr, f, lines
    width = 10.487
    height = width / 1.718

    f, axarr = plt.subplots(facecolor = '#bde3ff', sharex = True, sharey = False)
    f.subplots_adjust(left = .14, bottom = .14, right = .88, top = .90)

    f.set_size_inches(width, height)

    for i in range(num_discr):
        line_x, = axarr.plot([], [],
              linestyle = '-',
              marker = 'o',
              markersize = 1,
              linewidth = 2,
              color = 'dodgerblue')
        if (i == 31):
            line_x, = axarr.plot([], [],
              linestyle = '-',
              marker = 'o',
              markersize = 1,
              linewidth = 2,
              color = 'red')
        lines.append(line_x)

    axarr.set_xlim(ch_min, ch_max)
    axarr.set_ylim(0, 1.5 * test_npulse)
    axarr.set_facecolor('white')
    axarr.xaxis.set_ticks_position('both')
    axarr.yaxis.set_ticks_position('both')
    axarr.get_yaxis().set_tick_params(direction = 'in')
    axarr.get_xaxis().set_tick_params(direction = 'in')
    axarr.set_xlabel('Pulse injected amplitude [Amp_cal]', x = 1, ha = 'right')
    axarr.set_ylabel('Counts', y = 1, ha = 'right')
    #axarr.autoscale(enable=True, axis='y', tight=None)

    plt.title('S-Curve Channel: {0} | Pulses: {1}'.format(testch, test_npulse))
    plt.grid(True, linestyle = '--', color = '0.75')
    plt.show(False)
    plt.draw()

scurves(sts, vref_n, vref_p, vref_t)
