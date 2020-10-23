#!/usr/bin/python

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg
import random
import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('TKagg')
import matplotlib.ticker as ticker
#from drawnow import *
#import main_gui414
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

''' DEPRECATED
#Configure objects used for IPbus communication
#from cbus import *
#hw=cbus_read_nodes("./sts_emul1_address.xml")
#def ipbus(nodes,name):
#   return nodes[name]

time.sleep(100e-9)
#ID
IDReg=ipbus(hw,"ID")
#Simulate unconnected links
LinkBreak=ipbus(hw,"LINK_BREAK")
LinkBreak.write(LINK_BREAK)
print hex(IDReg.read())
#Start test
TestEna=ipbus(hw,"TSTEN")
TestEna.write(0)

#Output delay register
ClkDel=ipbus(hw,"CKDEL")
ClkDelStr=ipbus(hw,"CKDELSTR")
DDelLock=ipbus(hw,"DDEL_LOCK")
CDelLock=ipbus(hw,"CDEL_LOCK")
CDelRdy=ipbus(hw,"CDEL_RDY")
#HITS FIFO
HitFifo=ipbus(hw,"HITS")
#Encoder mode register
EncMode=ipbus(hw,"ENC_MODE")

#Encoder mode values
MODE_SOS=2
MODE_K28_1=3
MODE_EOS=1
MODE_FRAME=0

#Input channels register address
InpDelays=[ipbus(hw,node) for node in ("DDEL0","DDEL1","DDEL2","DDEL3","DDEL4")]
DetClears=[ipbus(hw,node) for node in ("DETI0","DETI1","DETI2","DETI3","DETI4")]
DetOuts=[ipbus(hw,node) for node in ("DETO0","DETO1","DETO2","DETO3","DETO4")]
cmd_slots=[ipbus(hw,node) for node in ("CMD0","CMD1","CMD2","CMD3","CMD4")]
cmd_stats=[ipbus(hw,node) for node in ("CST0","CST1","CST2","CST3","CST4")]

#Detector masks
SOS_DET_STABLE0=1<<8
SOS_DET_STABLE1=1<<7
SOS_DET=1<<6
EOS_DET_STABLE1=1<<5
EOS_DET=1<<4
K28_5_DET_STABLE1=1<<3
K28_5_DET=1<<2
K28_1_DET_STABLE1=1<<1
K28_1_DET=1<<0

#Detector clear and sel masks
SOS_CLEAR = 1<<0
EOS_CLEAR = 1<<1
K28_1_CLEAR = 1<<2
K28_5_CLEAR = 1<<3
'''
# ----------------- Writing and Reading register in the STS_XYTER ----------------------


# --- Confirming MODE_FRAME ------
#EncMode.write(MODE_FRAMEchrg 250    1000 1000 1000 1000 1000 )
#time.sleep(0.000002)

# --------------- Creating object ---------------------

#sts=stsxyter(15)

# ----------- Set the link mask accordingly -----------
sts = sts_ifaces[0][0]
#sts1 = sts_ifaces[0][0]

t0 = time.time()

lmask = ((1<<5)-1) ^ LINK_BREAK
lmask |= (lmask << 5)
sts.emg_write(192,25,lmask)
confirm = False
print "Link Mask" + bin(lmask)
app = QtGui.QApplication(sys.argv)


vref_n = 26     # Vref_N   AGH:  31    Test:  22
vref_p = 53    # Vref_P   AGH:  48    Test:  51
vref_t = 186
#vref_t_r = 176  # Vref_T   AGH: 188    Test: 184         bit7: enable   5..0:

testch = 127-50
thr2_glb = 37

d_min = 0
d_max = 32

ch_min = 0
ch_max = 250
#ch_max = ch_min+5

test_delta_ch = 10
test_thr = 255 
grp_min = 0
grp_max = 4

csa_in = 31
test_npulse = 80

vp_cnt = [0 for d in range(ch_min,ch_max, test_delta_ch)]
cnt = [[0 for c in range(ch_min, ch_max, test_delta_ch)] for d in range(d_min,d_max)]
x_n = [0 for c in range(ch_min, ch_max, test_delta_ch)]
vp_set = [0 for d in range(d_min,d_max)]
vp_mean = [0 for d in range(d_min,d_max)]
vp_sigma = [0 for d in range(d_min,d_max)]

# ---------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------

def scurves(sts,vref_n,vref_p,vref_t):
    #testch = int(testch)
    #vref_n = int(vref_n)
    #vref_p = int(vref_p)
    #vref_t = int(vref_t)
    #thr2_glb =int(thr2_glb)

    #ch_max = ch_min+5;

    #thr_arr = [134,141,148,145,136,125,133,129,136,117,139,124,139,128,128,136,133,128,129,138,134,129,135,124,120,139,124,129,132,131,128]
    #thr_arr = [128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128]
    #ch 77, channel  lowest to highest
    thr_arr = [145,136,145,135,131,145,130,122,133,129,123,133,131,132,133,126,119,116,129,131,123,133,123,122,112,128,121,130,125,113,112,39]

    thr_fast = 36
    #thr_arr =[128,134,128,128,128,128,131,128,120,131,128,128,130,118,122,121,128,128,128,128,128,128,128,128,128,128,130,131,128,128,128]

    setdisc_flag = 1 
    read_nword = 50

    shslowfs = 0  # 0,..,3 for FS=90,160,220,280ns

    # ---------------------------------------------------------------------------------------
    # -----------------------------------------------------------------ch_min----------------------

    pol = 1

    if (pol == 1):
      sts.write_check(130,2,163)   #  163 holes, 227 holes reset on ,   131 electrons, 195 electrons reset on
      print " "
      print "____HOLES MODE____"
      print " "
    if (pol == 0):
      sts.write_check(130,2,131)   #  163 holes     131 electrons
      print " "
      print "____ELECTRONS MODE____"
    print " "


    sts.write_check(130,  0, csa_in)
    sts.write_check(130, 3, 31)
    sts.write_check(130, 13, csa_in)



   ##Mask disable
    for i in range(4,13):
      sts.write_check(192,i,0x0000)
    sts.write_check(192,13,0x00)
    #sts.write_check(192,8,0x3ffb) # Enabling channel 58
    #sts.write_check(192,12,0x37ff) # Enabling channel 123
    sts.write_check(192,3,1) #channel mask enable

    '''
    if setdisc_flag == 1:
      print "Setting all disc, trim values to highest threshold "
      for i in range (0,128):    # (0,128)
         print "Disc: ", i #print "Initially the trim-value for lowest discriminator was:  " + bin(sts.read(i,61))
        for j in range (0,31):
          n=2*j+1
          sts.write_check(i,n,0)
          sts.write_check(i,63,144)
          sts.write_check(i,65,244)
          sts.write_check(i,67,36)
    '''

    # disable other test modes
    sts.write_check(192,18,0)
    sts.write_check(192,20,0)



    print "test channel ", testch

    testgrp = testch%4

    regval = testgrp + 4*shslowfs
    sts.write_check(130,5,testgrp)
    print " group selected", testgrp
    print " "


    #sts.write_check(130, 1, 7)

    print "......Setting ADC reference potentials ...... "

    sts.write(130, 8,vref_n)
    sts.write(130, 9,vref_p)
    sts.write(130,10,vref_t)
    #sts.write(130,18,vref_t_r)
    #sts.write(130,10, vref_t & 0x80 + 0x40)   # enables vrefT + get same range as for 2.0
    #sts.write(130,18, vref_t & 0x3F + 0xC0 )   # get same range as for 2.0 + loads VREFT

    print " "
    print " ADC Reference potentials"
    print "VRef_N: ",sts.read(130, 8)
    print "VRef_P: ",sts.read(130, 9)
    print "VRef_T: ",sts.read(130,10)
    print " "

    print "......Setting FAST disc reference potential ...... "
    sts.write(130, 7,thr2_glb)
    #sts.write(130,17,  0) # Set new Vref Fast polarity to 0 to get same as for 2.0

    print " "
    print "FAST Reference potentials"
    print "Thr2_global: ",sts.read(130, 7)
    print " "


    print "Vref_n ", (sts.read(130,8)&0xFF)
    print "Vref_p ", (sts.read(130,9)&0xFF)
    print "Vref_t ", (sts.read(130,10)&0xFF)
    print "Thr2_glb ", (sts.read(130,7)&0xFF)

    print "test thr ", test_thr

    # set threshold for all disc's of test channel
    print "set disc. thresholds: ",
    for d in range (0,31):
      n=2*d+1
    #  sts.write_check(testch,n,test_thr)
    #sun
      n = 61 - 2*d
      sts.write_check(testch,n,thr_arr[d])
     # print "  ",dregval,",",thr_arr[d],
      #sys.stdout.flush()
      #sts.write_check(testch,n,test_thr)
    sts.write_check(testch,67,thr_fast)
    print "fast: ", str(sts.read(testch,67))
    print " "

    # Set Thrshold for all ch disc.
    #for i in range(0,128):
     # for j in range(0,31):
      #  n = 2*j+1
       # sts.write_check(i,n,test_thr)


    # sun read trim settings of testch
    print("ch: %3d" % testch),
    for d in range (0,31):
      n = 61 - 2*d
      trim = sts.read(testch, n) & 0xFF
      print("%3d" % trim),
    trim = sts.read(testch, 67) & 0xFF
    print("%3d" % trim)



    # resets
    print "Resetting front-end channels "
    print "Resetting ADC counters"
    print "Reset channel fifos"
    sts.write_check(192,2,42)
    time.sleep(0.00001)
    sts.write_check(192,2,0)
    sts.write_check(130,11,0)


    nd = 32
    nthr = 256
    nch = 256
    ch_cnt = 0


    #### For testing the CSA IFED value
    ifed = 31
    sts.write_check(130,0,csa_in )
    sts.write_check(130,13, csa_in)
    sts.write_check(130,1,ifed )

    # loop over test charge range
    #sts.write_check(130,11,0)

    print "test charge",
    #sun
    #create_graph(sts,num_discr,testch)
    for ch in range (ch_min,ch_max, test_delta_ch):
     # sts.write_check(130,11,0)
      print "sun chrg", '{:3d}'.format(ch)
      sts.write_check(130, 4, ch) # test pulse Recommended value between 80-200
      #print ch,
      #sys.stdout.flush()
      x_n[ch_cnt]=ch
      x = np.array(x_n[:ch_cnt])
      data_n = np.array([])
      plt.pause(0.5)
      # Reset ADC counters
      sts.write_check(192,2,63)
      time.sleep(0.00001)
      sts.write_check(192,2,0)
      #for grp in range(grp_min, grp_max):
       # sts.write_check(130,5,grp)
      # Generate calib pulses
      sts.write_check(130,5,testgrp)
      for i in range (0,test_npulse):
        sts.write_check(130,11,128)
        sts.write_check(130,11,0)
      #sun, generate 80 more pulse
      time.sleep(1)
      for i in range (0,test_npulse):
        sts.write_check(130,11,128)
        sts.write_check(130,11,0)

      for d in range(d_min,d_max):
        n=2*d
        cnt[d][ch_cnt] = sts.read(testch,n)
        #sun
        print("ch=%3d, cnt=%3d" % (d, cnt[d][ch_cnt]))
        #
        data_n = np.array(cnt)
        #time.sleep(0.05)

      for d in range(d_min,d_max):
        data =data_n[d,:ch_cnt]
        #lines[d].set_data(x,data_n[d,:ch_cnt])

      ch_cnt+=1
    #for i in range(len(vp_inj)):
      #print vp_inj[i]

    f1 = open("sts_test_mode2.txt", "w+")

    print
    ch_cnt = 0
    for ch in range (ch_min, ch_max, test_delta_ch):
        f1.write("chrg")
        f1.write('{:4d}'.format(ch))
        #print "chrg", '{:3d}'.format(ch), "  ",
        #sun
        print "", '{:3d}'.format(ch), "  ",

        for d in range (0,32):
            val = cnt[d][ch_cnt]
            f1.write('{:5d}'.format(val))
            print '{:4d}'.format(val),
        ch_cnt += 1
        print " "
        f1.write("\n")
    print

    raw_input()

    ####################################################
    #Calculating mean value and sigma

    #sum_delta = 0.0000001
    #sum_sig = 0
    #d_cnt = 0
    #sum_mean = 0
    ##range where most of scurves are
    #vp_min_0 = 20.
    #vp_max_0 = 246.
    #width = 60.


    #vp_d = (vp_max_0-vp_min_0)/(31.)

    #for d in range(0,31):
      #vp_set[d] =(vp_min_0 + vp_d*d)
      #print "d:   ",vp_set[d]


    #for d in range(0,31):


    ####range where I will look for the Scurve. Expanded range compare to the fit

      #thr_min = int(vp_set[d]-ch_min-width)
      #if (thr_min <=0):
   #thr_min = 1
      #thr_max = int(vp_set[d]-ch_min+width)
      #if (thr_max >ch_max-ch_min):
   #thr_max = ch_max-ch_min

      #ivp = thr_min/test_delta_ch +1
      #print "disc",d, " ", thr_min, " ", thr_max

      #ivp = 1
      #for vp in range(ch_min, ch_min, test_delta_ch):
          #d_cnt = cnt[d][ivp]- 130cnt[d][ivp-1]
          #if (d_cnt <0):
       #d_cnt =0
     #sum_delta += d_cnt
     #sum_mean += (vp+ch_min)*d_cnt
     #ivp+=1


      #mean = sum_mean/sum_delta
      #vp_mean[d]= mean
      #print "d:   ",vp_mean[d]


      #ivp = thr_min/test_delta_ch

      #for vp in range(thr_min, thr_max, test_delta_ch):
          #d_cnt = cnt[30-d][ivp]- cnt[30-d][ivp-1]
          #if (d_cnt <0):
       #d_cnt =0
          #sum_delta += d_cnt
          #sum_sig +=((vp+ch_min)-mean)*((vp+ch_min)-mean)*d_cnt
          #ivp+=1

      #sigma = math.sqrt(sum_sig/sum_delta)
      #vp_sigma[d]= sigma


####################################################

axarr = None
f = None
lines = []


#color = ['black','red','blue']
num_discr = 32

def create_graph(sts,num_discr,testch):

    global axarr,f,lines

    width = 10.487
    height = width / 1.718

    f, axarr = plt.subplots(facecolor= '#bde3ff', sharex=True, sharey=False)
    f.subplots_adjust(left=.14, bottom=.14, right=.88, top=.90)

    f.set_size_inches(width, height)

    for i in range(num_discr):
        line_x, = axarr.plot([], [],
              linestyle='-',
              marker='o',
              markersize=1,
              linewidth=2,
              color ='dodgerblue')
        if (i==31):
            line_x, = axarr.plot([], [],
              linestyle='-',
              marker='o',
              markersize=1,
              linewidth=2,
              color ='red')
        lines.append(line_x)

    axarr.set_xlim(0,300)
    axarr.set_ylim(0,200)
    axarr.set_facecolor('white')
    axarr.xaxis.set_ticks_position('both')
    axarr.yaxis.set_ticks_position('both')
    axarr.get_yaxis().set_tick_params(direction='in')
    axarr.get_xaxis().set_tick_params(direction='in')
    axarr.set_xlabel('Pulse injected amplitude [Amp_cal]', x=1, ha='right')
    axarr.set_ylabel('No. Conteos', y=1, ha='right')
    #axarr.autoscale(enable=True, axis='y', tight=None)

    plt.title('S-Curves Monitor')
    plt.grid(True, linestyle='--', color='0.75')
    plt.show(False)
    plt.draw()

##################################################
# Esto es para probarlo / This is for testing it
##################################################

def config( sts ):

  # --------------AFE Registers -----------------
  print " "
  print "Full set of registers for the AFE. Typical values"
  print " "
  print "------------------ooooOOOOOoooo-------------------"

  for ch in range (ch_min, ch_max):
    for d in range (d_min, d_max):
      n=2*d+1
      sts.write_check(ch,n,128)
    sts.write_check(ch,63,144)
    sts.write_check(ch,65,244)
    sts.write_check(ch,67,36)

  #csa_in = 63
  #vref_t = 186

  sts.write_check(130, 0, csa_in)   #Typ: 31, Max: 63
  sts.write_check(130, 1, 63)   #Typ value for Ileak = 0nA
  sts.write_check(130, 2, 131)   #electrons: 131, holes: 163
  sts.write_check(130, 3, 31)   #Typ: 31, Max: 63
  sts.write_check(130, 4,  0)
  sts.write_check(130, 5,  0)      # 0
  sts.write_check(130, 6, 32)   #Typ: 32, Max: 63
  sts.write_check(130, 7, 37)
  sts.write_check(130, 8, 26)
  sts.write_check(130, 9, 53)
  sts.write_check(130,10, vref_t)   # enables vrefT + get same range as for 2.0
  sts.write_check(130,11, 64)
  sts.write_check(130,12, 30)
  sts.write_check(130,13, csa_in)   #Typ: 31, Max: 63
  sts.write_check(130,14, 27)   #Typ: 27, Max: 63
  sts.write_check(130,15, 27)   #Typ: 27, Max: 63
  sts.write_check(130,16, 88)
  sts.write(130,17,  0) # Set new Vref Fast polarity to 0 to get same as for 2.0
  sts.write(130,18, vref_t_r)   # get same range as for 2.0 + loads VREFT
  #sts.write_check(130,20,  0)
  #sts.write_check(130,21,  0)
  #sts.write_check(130,22,  0)

#config(sts)
scurves(sts,vref_n,vref_p,vref_t)

#scurves(sts1,vref_n,vref_p,vref_t)
