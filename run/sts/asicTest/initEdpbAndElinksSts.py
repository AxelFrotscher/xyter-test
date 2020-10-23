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
fh = logging.FileHandler("./logs/" + sys.argv[0].replace('.py', '.log'), 'w')
fh.setLevel(logging.DEBUG)
fmt = logging.Formatter('[%(levelname)s] %(message)s')
fh.setFormatter(fmt)
log.addHandler(fh)

#uhal.setLogLevelTo( uhal.LogLevel.DEBUG)
uhal.setLogLevelTo(uhal.LogLevel.WARNING)
manager = uhal.ConnectionManager( settings.xml_filename )

hw = []
for edpb in settings.edpb_names:
  hw.append( manager.getDevice( edpb ) )

#log.info("Configuring TS subsystem")
#tdpb    = ts_config.dev("tDPB", manager)
#edpb_ts = []
#for edpb in settings.edpb_names:
  #edpb_ts.append( ts_config.dev( edpb, manager) )
#ts_config.configure_tDPB(tdpb)
#log.info("...tDPB set up")
#time.sleep(1)
#for edpb in edpb_ts:
  #ts_config.configure_eDPB( edpb )
#log.info("...eDPB set up")

sts_com  = []
flims    = []
afck_id  = []
afck_mac = []
for edpb_idx in range( 0, len(hw) ):
  gdc.dev_rw_reg_test(           hw[ edpb_idx ], "global_dev")
  gdc.read_public_dev_info(      hw[ edpb_idx ], "global_dev")
  gdc.read_afck_info(            hw[ edpb_idx ], "global_dev")
  gdc.afck_i2c_init(             hw[ edpb_idx ], "global_dev")
  gdc.afck_bus_sel(              hw[ edpb_idx ], "global_dev", 0)
#  gdc.afck_set_si570_frq(        hw[ edpb_idx ], "global_dev", 156250000)
#  gdc.set_afck_base_eqipment_id( hw[ edpb_idx ], "global_dev", 0xaaaa)
#  Insert new frequencies here: [Hz]
  gdc.afck_set_si570_frq(        hw[ edpb_idx ], "global_dev",  415000000)
  gdc.afck_reset_device(         hw[ edpb_idx ], "global_dev", 1)  # reset device
  sts_com.append( sxdc.sts_xyter_com_ctrl( hw[ edpb_idx ], "sts_xyter_dev") )
  flims.append(   fdc.flim_dev_ctrl(       hw[ edpb_idx ], "flim_ctrl_dev") )
  sts_com[ edpb_idx ].read_public_dev_info()

  afck_id.append( gdc.get_afck_id(   hw[ edpb_idx ], "global_dev") )
  afck_mac.append( gdc.get_afck_mac( hw[ edpb_idx ], "global_dev") )
  log.info("\nAFCK ID:  0x%04x", afck_id[ edpb_idx ] )
  log.info("\nAFCK MAC: %s",     afck_mac[ edpb_idx ] )

  ## Force Equipment ID to AFCK ID as not done automatically!!!
  gdc.set_afck_base_eqipment_id( hw[ edpb_idx ], "global_dev", afck_id[ edpb_idx ])

sts_ifaces = [[]]
for edpb_idx in range( 0, len(hw) ):
  sts_ifaces.append( [] )

  # iface_no: xyter_addr
  for i in range(0, sts_com[ edpb_idx ].interface_count()):
    if settings.iface_active[ edpb_idx ][i] == 1:
      sts_ifaces[edpb_idx].append( sxdc.sts_xyter_iface_ctrl( sts_com[ edpb_idx ], i, settings.sts_addr_map[ edpb_idx ][i], afck_id[ edpb_idx ] ) )

  for sts_iface in sts_ifaces[edpb_idx]:
    sts_iface.set_link_break(settings.LINK_BREAK)

  if len(sys.argv) > 1:
    log.info("\nDoing FAST synchronisation")
    for s in sts_ifaces[edpb_idx]:
      log.info("Setting interface [{}][{}] [{}]".format(edpb_idx, s.iface, sts_ifaces[edpb_idx].index(s) ))
      s.fast_sync( settings.LINK_BREAK )
    for s in sts_ifaces[edpb_idx]:
      s.EncMode.write(sxdc.MODE_FRAME)
  else:
    log.info("\nDoing FULL eLink synchronisation")
    # full_link_sync won't automatically switch do data frame mode
    # This is due to firmware/XYTER limitations - all ASICs have to be synch.
    # before switching to data transmission, otherwise things will fail
    for s in sts_ifaces[edpb_idx]:
      log.info("Calibrating interface [{}][{}] ([{}])".format(edpb_idx, s.iface, sts_ifaces[edpb_idx].index(s) ))
      s.full_link_sync( settings.LINK_BREAK )
    # Now switch to sending frames
    for s in sts_ifaces[edpb_idx]:
      s.EncMode.write(sxdc.MODE_FRAME)

    print("\nFull link synchronisation completed.")
    print("Calibration results were written to a file.")
    print("You can now run \"%s 1\" to skip full synchronisation" % sys.argv[0])

  log.info("\nSTS eLink synchronisation completed")

  time.sleep(0.1e-6)
  # Set the link mask accordingly
  lmask = ((1 << 5) - 1) ^ settings.LINK_BREAK
  lmask |= (lmask << 5)

  # Set the link mask accordingly
  for sts_iface in sts_ifaces[edpb_idx]:
    sts_iface.emg_write(192, 25, lmask)

  log.info("Stopping readout & STSXYTER pattern generator")
  for sts_iface in sts_ifaces[edpb_idx]:
    sts_iface.write(192, 18, 0)  # Stop test


  log.info("start to initialize AFCK Microslice threshold")
  #flims[edpb_idx].set_ms_period( settings.ms_period, settings.ms_clock_period )
  #flims[edpb_idx].set_ms_index_threshold( 0xFFFFFFFF, 0xFFFFFFFF,
  #                                        0x0, 0x0 )

  # FIFOs should be reset after setting up all XYTERs, otherwise the startup
  # data in readout buffer will reflect a sequence in which XYTERs were enabled
  log.info("Setup sts-xyter datapath")
  sts_com[ edpb_idx ].reset_fifo_all()
  sts_com[ edpb_idx ].set_dest(0)

  log.info("We will now be transmitting data to FLIM when microslices are enabled ")

  sts_com[ edpb_idx ].reset_fifo_all()

logging.shutdown()
