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

sts_iface.write_check(130, 8, 22)
sts_iface.write_check(130, 9, 55)

#vref_t apparently gets disabled, if you set (130,10,<6>) to 1, 55 is a good value
sts_iface.write_check(130, 10, 128)
sts_iface.write(130, 18, 0x40 + 55)

#Write range (we chose low range 84mV)
#sts_iface.write_check(130, 18, 7)
# (n,p,t) = 25, 53, 127

sts = sts_ifaces[0][0]
print "VRef_N: ",sts.read(130, 8) & 0xFF
print "VRef_P: ",sts.read(130, 9) & 0xFF
print "VRef_T: ",sts.read(130,10) & 0x3F
print "Col18",sts.read(130,18) & 0xFF

'''
# Checking even and odd channels for counts
number_test_pulses = 80;

sts_iface.write(130, 4, 80)
sts_iface.write(192, 2, 32)
sts_iface.write(192, 2, 0)

for loop_round in range(0, number_test_pulses):
  sts_iface.write(130, 11, 128)
  sts_iface.write(130, 11, 0)

print "Pulses %i Ch 2: %i, Ch 3: %i"%(number_test_pulses, sts_iface.read(2, 60),
                                      sts_iface.read(3,60))

'''
print("Done")
