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
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index, pulse ON duration")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEE  index")
  log.error("- pulse ON duration in seconds")
  log.error("E.g. for FEB 0 of eDPB 1: python setStsDigitalPulser.py 0 2 10.0")
  sys.exit()

edpb_idx  = int( sys.argv[1] )
iface_idx = int( sys.argv[2] )
durationS = int( sys.argv[3] )

if len( settings.edpb_names) <= edpb_idx:
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEE  index")
  log.error("- pulse ON duration in seconds")
  log.error("In this call the eDPB index is too big for edpb_names array [{}] VS size {}".format( edpb_idx, len( settings.edpb_names ) ) )
  sys.exit()

if len( settings.sts_addr_map[ edpb_idx ] ) <= iface_idx:
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEB  index")
  log.error("- pulse ON duration in seconds")
  log.error("In this call the FEB index is too big for the corresponding sts_addr_map sub-array [{}] VS size {}".format( iface_idx, len( settings.sts_addr_map[ edpb_idx ] ) ) )
  sys.exit()

if durationS <= 0:
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index, pulse ON duratio")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEB  index")
  log.error("- pulse ON duration in seconds")
  log.error("In this call the pulse ON duration is not greater than 0!!!")
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

# Initialize trigger register and reset the self-triggering part
hit_rate = 12          # 5 bit hit rate:     hit_rate in Hz = 160e6 / 96  * hit_rate_value
                       # max: 31 ( 51.67 MHz);   typ: 1 (1.67MHz)       - both with divider = 0
                       # min: hit_rate=1   divider = 7 -- >    13 kHz
n_ts_rand = 0         # the n_ts_rand LSBs are randomized;  default: 0 - no randomization
hit_divider = 0       # 3bit;  division of rate by 2**hit_divider;   default: 0 - division by 2**0=1 --> hit_rate

link_mask = 0b00001

lmask = ((1 << 5) - 1) ^ link_mask
lmask |= (lmask << 5)
sts_iface.emg_write(192, 25, lmask)
              


hit_rate = hit_rate & 0x1f
hit_rate_hz = float(160./3/32*hit_rate)

hit_divider = hit_divider & 0x7
n_ts_rand = n_ts_rand & 0x7 
log.info("----> Test Mode 1 (var. rate hit streaming)   Config:     Hit rate par %u      Hit rate %f  MHits/s", hit_rate, hit_rate_hz )
val = (hit_divider<<8) + (n_ts_rand<<5) + (hit_rate)


log.info ("Test hit settings for reg 192,19:  0x%x",  val)
sts_iface.write(192, 18,     2)
sts_iface.write(192, 19, val)
#sts_iface.write(192, 19, 0x701)

print "----------------------------------------------------------------"
print "Generating pulses: "
timestart = time.time()
## multiple count loops
while time.time() - timestart < durationS:
#  print (time.time() - timestart)
  time.sleep( 1 )

print "----------------------------------------------------------------"

sts_iface.write(192, 18, 0)  # Stop pulser

print("Done")
