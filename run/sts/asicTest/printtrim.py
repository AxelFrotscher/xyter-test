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

for edpb_idx in range( 0, len(hw) ):
  print("Trim  setting for eDPB #", edpb_idx)
  for sts_iface in sts_ifaces[edpb_idx]:
    print("--> Trim setting for FEB #", sts_iface.iface)
    mask_settings = []


print(" ch\d  "),
for d in range (0,31):
      print("%3d" % d),
print("%3d" % 31)

# read trim settings
print("Lowest to highest!!")
for ch in range( 0, 128 ):
   print("ch: %3d" % ch),
   for d in range (0,31):
      n = 61 - 2*d
      trim = sts_iface.read(ch, n) & 0xFF
      print("%3d" % trim),
   trim = sts_iface.read(ch, 67) & 0xFF
   print("%3d" % trim)

   #  sts_iface.write(ch, n, 128 )

#print("trim value in ch %d is %d" % (ch, d, trim))

#trim_offset = 0;
#ch_min = 0;
#ch_max = 128;
#d_min = 0;
#d_max = 31;
#trim_ok_min = 0;
#trim_ok_max = 255;

#for ch in range(ch_min,ch_max):
#  print "ch: ", ch,
#  for d in range (d_min,d_max):
#    disc = 61- 2*d
#    val_f = sts_iface.read(ch,disc) & 0xff
#    print '{:4d}'.format(val_f),
#  print '{:4d}'.format(sts_iface.read(ch,67) & 0xff ),
#  print "\n"


print("Done")

