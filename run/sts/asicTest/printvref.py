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

for edpb_idx in range( 0, len(hw) ):
  print("Vref for eDPB #", edpb_idx)
  for sts_iface in sts_ifaces[edpb_idx]:
    print("--> Vref setting for FEB #", sts_iface.iface)
    mask_settings = []

#sts_iface.write(130, 8)
#sts_iface.write(130, 9)
#sts_iface.write(130, 10)
#sts_iface.write(130, 18, 200)
print "Col18 {0}".format(sts_iface.read(130,18) & 0xFF)

vref_n = sts_iface.read(130, 8) & 0xFF
vref_p = sts_iface.read(130, 9) & 0xFF
vref_t = sts_iface.read(130, 10) & 0xFF

print "Register value VRef_N: ", vref_n
print "Register value VRef_P: ", vref_p
print "Register value VRef_T: ", vref_t

sts = sts_ifaces[0][0]
print "VRef_N: ",sts.read(130, 8) & 0xFF
print "VRef_P: ",sts.read(130, 9) & 0xFF
print "VRef_T: ",sts.read(130,10) & 0x3F



print("Done")
