#!/usr/bin/python

import time
import sys
import struct

import logging

import uhal

sys.path.append("../../../lib")
import global_dev_ctrl as gdc
import flim_dev_ctrl as fdc
import sts_xyter_dev_ctrl as sxdc

import sts_xyter_settings as settings

MSB_count= [ 0 for chan in range (0,1)]
ch_count=  [ 0 for chan in range (0,128)]
lastTsMsb= [-1 for chan in range (0,1)]

def print_frame( frame ):
  frame_type = frame & 0x00800000
  frame_subtype = frame & 0x00400000
  if frame_type:
    if frame_subtype:
      print 'Raw 0x{:08x}'.format( frame ),
      print 'Elink {:3d}'.format( (frame & 0xFF000000 ) >> 24 ),
      print 'MSB',
      print 'A   {:3d}'.format( (frame & 0x003F0000 ) >> 16 ),
      print 'B   {:3d}'.format( (frame & 0x0000FC00 ) >> 10 ),
      print 'C   {:3d}'.format( (frame & 0x000003F0 ) >>  4 ),
      print 'CRC {:3d}'.format( (frame & 0x0000000F )       ),
      print 'ovr {:1d}'.format( (frame & 0x00000030 ) >>  4 )
      lastTsMsb[ 0 ]     = ( (frame & 0x0000FC00 ) >> 2 )
      MSB_count[ 0 ] += 1
    #else:
      #print 'Raw 0x{:08x}'.format( frame ),
      #print 'Elink {:3d}'.format( (frame & 0xFF000000 ) >> 24 ),
      #print 'Unexpected frame: {:2d}'.format( (frame & 0x00E00000 ) >> 21 ),
  else:
    fullTs =  ( lastTsMsb[ 0 ]  ) + ( (frame & 0x000001FE ) >>  1 )
    if 1:
#    if 3 == (frame & 0x007F0000 ) >> 16:
      print 'Raw 0x{:08x}'.format( frame ),
      print 'Elink {:3d}'.format( (frame & 0xFF000000 ) >> 24 ),
      print 'Hit',
      print 'ch  {:3d}'.format( (frame & 0x007F0000 ) >> 16 ),
      print 'adc  {:2d}'.format( (frame & 0x0000F800 ) >> 11 ),
      print 'ovr   {:1d}'.format( (frame & 0x00000600 ) >>  9 ),
      print 'ovr M {:1d}'.format( (lastTsMsb[ 0 ] & 0x00000300 ) >> 8 ),
      print 'ts  {:3d}'.format( (frame & 0x000001FE ) >>  1 ),
      print 'full {:4d}'.format( (frame & 0x000007FE ) >>  1 ),
      print 'mis {:1d}'.format( (frame & 0x00000001 )       ),
      print 'Big {:5d}'.format( fullTs ),
      print 'Mod {:5d}'.format( fullTs % 4096 )
    ch_count[ (frame & 0x007F0000 ) >> 16 ] += 1


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
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index, readout duration")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEE  index")
  log.error("- readout duration in seconds")
  log.error("E.g. for FEB 0 of eDPB 1: python readRawDataFifo.py 0 2")
  sys.exit()

edpb_idx  = int( sys.argv[1] )
iface_idx = int( sys.argv[2] )
durationS = int( sys.argv[3] )

if len( settings.edpb_names) <= edpb_idx:
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index, readout duration")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEE  index")
  log.error("- readout duration in seconds")
  log.error("In this call the eDPB index is too big for edpb_names array [{}] VS size {}".format( edpb_idx, len( settings.edpb_names ) ) )
  sys.exit()

if len( settings.sts_addr_map[ edpb_idx ] ) <= iface_idx:
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index, readout duration")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEB  index")
  log.error("- readout duration in seconds")
  log.error("In this call the FEB index is too big for the corresponding sts_addr_map sub-array [{}] VS size {}".format( iface_idx, len( settings.sts_addr_map[ edpb_idx ] ) ) )
  sys.exit()

if durationS <= 0:
  log.error("This script has to be called with 3 arguments: eDPB index, FEB index, readout duration")
  log.error("The arguments should respectively fit in the following arrays in sts_xyter_settings:")
  log.error("- edpb_names   for eDPB index")
  log.error("- sts_addr_map for FEB  index")
  log.error("- readout duration in seconds")
  log.error("In this call the readout duration is not greater than 0!!!")
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

# reset the raw data IPbus FIFO
#print "Reset the Raw data Fifo "
sts_com.reset_raw_fifo()

log.info("----------------------------------------------------------------")

timestart = time.time()
frame_buffer = []
while time.time() - timestart < durationS:
#  print (time.time() - timestart),
#  print sts_com.read_ipb_data_fifo_len()
#  print sts_com.read_ipb_rawdata_fifo_len()
#  print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"

  # Read the raw data IPbus FIFO
  data_buffer = []
  frameNb = int( sts_com.read_ipb_rawdata_fifo_len() ) 
  print("frameNb %4d" % frameNb)
  data_buffer = sts_com.read_ipb_raw_data_fifo( frameNb )
  frame_buffer.extend( data_buffer )
#  sts_com.reset_raw_fifo()
  frame_cnt = 0
#  for frame in data_buffer :
#    print_frame( frame )
#    print '{:08x}'.format(frame),
#    if 15 == frame_cnt%16 :
#      print ""
#      print '{:5d} '.format(frame_cnt),
#    frame_cnt += 1

#  if 0 < len(data_buffer):
#    print ""

#  print ""
#  print "----------------------------------------------------------------"

log.info("----------------------------------------------------------------")
for frame in frame_buffer :
    print_frame( frame )

log.info("----------------------------------------------------------------")
print 'TS MSB cnt   {:5d}'.format( MSB_count[ 0 ] )
for chan in range( 0, 128):
  if 0 < ch_count[ chan ] :
    print 'ch  {:3d}'.format( chan ),
    print '    {:5d}'.format( ch_count[ chan ] )

log.info("----------------------------------------------------------------")


runid=time.strftime( "%y%m%d_%H%M%S", time.gmtime())
outfilename = "binarydump_1elink_6ch_extAmpCalPhaseLock_4ch_InputPhaseScan_%s.bin"%(runid)
fout = open(outfilename,"wb")
pstr = "i"
for frame in frame_buffer :
  data = struct.pack(pstr, frame) # pack unsigned integer frame in a binary string
  fout.write( data )
fout.close()

log.info("Done")
logging.shutdown()
