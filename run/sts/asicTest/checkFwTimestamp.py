#!/usr/bin/python

import sys
import time
import struct
import logging
import uhal
sys.path.append("../../../lib")
import ts_config
import global_dev_ctrl as gdc
import sts_xyter_dev_ctrl as sxdc
import flim_dev_ctrl as fdc

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

#log.info("tDPB FW timestamps")
#log.info("  MAC address   => %s", gdc.get_afck_mac( manager.getDevice( "tDPB" ), "global_dev") )
#log.info("  FW Build time => %s", gdc.read_build_time( manager.getDevice( "tDPB" ), "global_dev") )

log.info("eDPB FW timestamps")
for edpb in settings.edpb_names:
  log.info("  %s", edpb)
  log.info("    MAC address   => %s", gdc.get_afck_mac( manager.getDevice( edpb ), "global_dev") )
  log.info("    FW Build time => %s", gdc.read_build_time( manager.getDevice( edpb ), "global_dev") )

logging.shutdown()
