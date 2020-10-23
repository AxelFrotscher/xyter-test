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

print "VRef_N: ",sts.read(130, 8)
print "VRef_P: ",sts.read(130, 9)
print "VRef_T: ",sts.read(130,10)
print " "
