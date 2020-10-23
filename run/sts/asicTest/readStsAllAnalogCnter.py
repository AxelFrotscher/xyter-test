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

if len(sys.argv) != 4:
  log.error("This script has to be called with 2 arguments: eDPB index, FEB index")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEE  index")
  log.error("E.g. for FEB 0 of eDPB 1: python readStsAnalogCnter.py 0 2")
  sys.exit()

edpb_idx  = int( sys.argv[1] )
iface_idx = int( sys.argv[2] )
reset_flag = int( sys.argv[3] )


if len( settings.edpb_names) <= edpb_idx:
  log.error("This script has to be called with 2 arguments: eDPB index, FEB index")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEE  index")
  log.error("In this call the eDPB index is too big for edpb_names array [{}] VS size {}".format( edpb_idx, len( settings.edpb_names ) ) )
  sys.exit()

if len( settings.sts_addr_map[ edpb_idx ] ) <= iface_idx:
  log.error("This script has to be called with 2 arguments: eDPB index, FEB index")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEB  index")
  log.error("In this call the FEB index is too big for the corresponding sts_addr_map sub-array [{}] VS size {}".format( iface_idx, len( settings.sts_addr_map[ edpb_idx ] ) ) )
  sys.exit()


uhal.setLogLevelTo(uhal.LogLevel.WARNING)
manager = uhal.ConnectionManager( settings.xml_filename )

hw = []
for edpb in settings.edpb_names:
  hw.append( manager.getDevice( edpb ) )

sts_com =  sxdc.sts_xyter_com_ctrl( hw[ edpb_idx ], "sts_xyter_dev")
flims   =  fdc.flim_dev_ctrl(       hw[ edpb_idx ], "flim_ctrl_dev")
sts_com.read_public_dev_info()

afck_id  = gdc.get_afck_id(   hw[ edpb_idx ], "global_dev")
afck_mac = gdc.get_afck_mac( hw[ edpb_idx ], "global_dev")
log.info("\nAFCK ID:  0x%04x", afck_id )
log.info("\nAFCK MAC: %s",     afck_mac )

if settings.iface_active[ edpb_idx ][iface_idx] == 0:
  log.info("FEB %d is inactive, doing nothing!!!",     edpb_idx )
  sys.exit()

# iface_no: xyter_addr
sts_iface = sxdc.sts_xyter_iface_ctrl( sts_com, iface_idx, settings.sts_addr_map[ edpb_idx ][iface_idx], afck_id )

ch_min = 1
ch_max = 128
ch_step = 1
d_min  =   0
d_max  =  31
d_step = 1

# reseting counters
if reset_flag == 1:
  sts_iface.write_check(192,2,42)
  sts_iface.write_check(192,2, 0)

#sts_iface.write(130,11,0x40)

# Read and printout the ADC and fast ch counters
print "ADC Id ",
for d in range (d_min, d_max, d_step):
  print '{:7d}'.format( d ),
print ""
for ch in range (ch_min, ch_max, ch_step):
  print "ch ", '{:3d}'.format(ch),
  for d in range (d_min, d_max):
    print '{:7d}'.format( sts_iface.read(ch, 61 - 2*d -1 ) ),
  print '{:7d}'.format( sts_iface.read(ch,62) )

print "----------------------------------------------------------------"
print "Sleep 1 s: "
time.sleep(1)
print "----------------------------------------------------------------"

#sts_iface.write(130,11,0x00)
# Read and printout the ADC and fast ch counters
print "ADC Id ",
for d in range (d_min, d_max, d_step):
  print '{:7d}'.format( d ),
print ""
for ch in range (ch_min, ch_max, ch_step):
  print "ch ", '{:3d}'.format(ch),
  for d in range (d_min, d_max):
    print '{:7d}'.format( sts_iface.read(ch, 61 - 2*d -1 ) ),
  print '{:7d}'.format( sts_iface.read(ch,62) )

print("Done")
