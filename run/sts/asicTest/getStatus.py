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

if len(sys.argv) !=3:
  log.error("This script has to be called with 2 arguments: eDPB index, FEB index")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEE  index")
  log.error("E.g. for FEB 0 of eDPB 1: python readStsAnalogCnter.py 0 2")
  sys.exit()

edpb_idx  = int(sys.argv[1])
iface_idx = int(sys.argv[2])

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



global_gate_rb = (sts_iface.read(130,11) >> 6) & 0x1

status = sts_iface.read(192,27)
status_mask = sts_iface.read(192,28)
status_af_alert = (status >> 0) & 0x1
status_em_alert = (status >> 2) & 0x1


af_counter = sts_iface.read(192,24)
em_counter = sts_iface.read(192,30)
af_thr_rb =  sts_iface.read(192,23)
em_thr_rb =  sts_iface.read(192,29)

ro_config_rb = sts_iface.read(192,3)
link_mask_rb = sts_iface.read(192,25)

chip_address = sts_iface.read(192,22) & 0x7

reset_rb = sts_iface.read(192,2)
timestamp = sts_iface.read(192,1)
last_addr = sts_iface.read(192,26)


test_reg = sts_iface.read(112,21)


print "Global Gate: \t", global_gate_rb
print "Status: \t", hex(status), "\t\tstatus mask: ",hex(status_mask)
print "  AF alert: \t", status_af_alert
print "  EM alert: \t", status_em_alert
print "AF Counter: \t", af_counter
print "EM Counter: \t", em_counter
print "AF Threshold: \t", af_thr_rb
print "EM Threshold: \t", em_thr_rb
print "Readout Config: \t", hex(ro_config_rb)
print "Chip Address: \t", hex(chip_address)
print "Link Mask: \t", hex(link_mask_rb&0x1f),"\t" , hex((link_mask_rb>>5)&0x1f)

print "Resets Active: \t", hex(reset_rb)
print "Timestamp: \t", hex(timestamp)
print "Last Addr: \t", hex(last_addr)
print ": \t",

print "Trim 112, 21: \t", hex(test_reg)



sts_iface.write(192,27,0)    # reset status
sts_iface.write(192,24,0)    # reset AF counter
sts_iface.write(192,30,0)    # reset EM counter

print("Done")
