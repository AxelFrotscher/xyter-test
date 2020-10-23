#!/usr/bin/python

from PyQt4 import QtCore, QtGui
#import pyqtgraph as pg
import random
import numpy as np
#import matplotlib.pyplot as plt
#import matplotlib.ticker as ticker
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

# Detector masks
SOS_DET_STABLE0 = 1 << 8
SOS_DET_STABLE1 = 1 << 7
SOS_DET = 1 << 6
EOS_DET_STABLE1 = 1 << 5
EOS_DET = 1 << 4
K28_5_DET_STABLE1 = 1 << 3
K28_5_DET = 1 << 2
K28_1_DET_STABLE1 = 1 << 1
K28_1_DET = 1 << 0
# Detector clear and sel masks
SOS_CLEAR = 1 << 0
EOS_CLEAR = 1 << 1
K28_1_CLEAR = 1 << 2
K28_5_CLEAR = 1 << 3

# Encoder mode values
MODE_SOS = 2
MODE_K28_1 = 3
MODE_EOS = 1
MODE_FRAME = 0

logging.info("\n### Doing full eLink SYNC for for STSXYTER #%d with address %d ###" %(sts.iface, sts.chip_nr))
sts.com.clkout_sel_output(sts.iface)
sts.com.clkout_set_delay(0)
sts.com.clkout_set_delay(0)

print "sun Force EOS mode"
sts.EncMode.write(MODE_EOS)
print "sun Force SOS mode"
sts.EncMode.write(MODE_SOS)

for i in range(0, 5):
    print "Clear det ",i
    sts.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
    sts.DetClears[i].write(0)

# Verify results
for i in range(0, 5):
  print "Read det ",i
  r = sts.DetOuts[i].read()
  logging.info("{}, {}".format(i, r))

time.sleep(0.0001)

logging.info("DDelLock: {:#b}, CDelLock: {}, CDelRdy: {}".format(
              int(sts.DDelLock.read()), sts.CDelLock.read(),sts.CDelRdy.read()))

print "sun Now switch to sending K28_1"
sts.EncMode.write(MODE_K28_1)

test = []
CLK_STEPS = 200 
clk_del = 0
NN = 1
testn = 0
link_break_user=0b00001
while testn < NN:
    logging.info("testn:%d",testn)
    clk_del = 0
    while clk_del < CLK_STEPS:
        print "clk_del= ",clk_del
        sts.com.clkout_set_delay(clk_del)
        for i in range(0, 5):
            #print "Clear det ",i
            sts.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)

        time.sleep(0.0002)

        for i in range(0, 5):
           #print "Det Clears sun i", i
           sts.DetClears[i].write(0)
         # Wait a little and check glitch detectors

        time.sleep(0.002)

        for i in range(0, 5):
          r = sts.DetOuts[i].read()
          #print "Det Out read i", i
          #print "Out=", r

        res = []
        sos_all = True
        for i in range(0, 5):
          r = sts.DetOuts[i].read()
          r1 = (r & SOS_DET_STABLE0) or (link_break_user & (1 << i) == 0)
          res.append(r1 != 0)
          if r1 == 0:
            sos_all = False
        test.append(sos_all)
        logging.info("{} {}".format(clk_del, res))

        #print "test:", test
        clk_del+=1


        ###############
        testn+=1

print "sun clk decay scan finish!!!!!"
clk_del = sts.find_center(test, CLK_STEPS)
# build a nice window eye graph to display
print "sun build a nice window eye graph to display"
window = ['_' if item else 'X' for item in test]
window.insert(0, '|')
window.append('|')
window = ''.join(window)
logging.info("Clock delay = {}".format(clk_del))
logging.info("Eye window of the clock signal:")
logging.info(window)
# Set the clock delay to the found value and adjust the input data delays
print "sun Set the clock delay to the found value and adjust the input data delays"
sts.com.clkout_set_delay(clk_del)
data_del = 0
test = [[], [], [], [], []]
