#!/usr/bin/python
import time
import ipbus_i2c_ctrl

def read_public_dev_info(hw, dev):
  print "\nThe public device information is:"
  val=hw.getNode(dev+".DEV_TYPE").read()
  hw.dispatch()
  print "device type:         %s" %(hex(val))
  val=hw.getNode(dev+".FW_VER").read()
  hw.dispatch()
  print "Firmware version:    %s" %(hex(val))
  val=hw.getNode(dev+".FMC0_SPT_DEV").read()
  hw.dispatch()
  print "Support FMC0:        %s" %(hex(val))
  val=hw.getNode(dev+".FMC1_SPT_DEV").read()
  hw.dispatch()
  print "Support FMC1:        %s" %(hex(val))
  val=hw.getNode(dev+".STAT_REG_NUM").read()
  hw.dispatch()
  print "Status reg number:   %d" % val
  val=hw.getNode(dev+".CTRL_REG_NUM").read()
  hw.dispatch()
  print "Control reg number:  %d" % val
  val=hw.getNode(dev+".OTH_SLV_NUM").read()
  hw.dispatch()
  print "Other slave number:  %d" % val
  val=hw.getNode(dev+".SLV_MASK").read()
  hw.dispatch()
  print "Other slave type:    %s" %(hex(val))
  return
 
def dev_rw_reg_test(hw, dev):
  hw.getNode(dev+".DEV_TEST_W").write(0xa55a5aa5)
  hw.dispatch()
  val=hw.getNode(dev+".DEV_TEST_R").read()
  hw.dispatch()
  if val==0xa55a5aa5:
    print "nXYTER device register write/read test passed!"
  else:
    print "nXYTER device register write/read test failed!"
  return

def read_ipb_data_fifo(hw, dev, num):
  left=num
  mem=[]
  while left>0:
    read_len=hw.getNode(dev+".DATA_FIFO.RFIFO_LEN").read()
    hw.dispatch() 
    time.sleep(0.01) 
    if read_len==0:
      continue
    read_len=min(left,int(read_len))
    mem0=hw.getNode(dev+".DATA_FIFO.RFIFO_DATA").readBlock(read_len)
    hw.dispatch()
#    print read_len   
    mem.extend(mem0)
    left=left-read_len
  return mem

#  default_rd_num=255
#  left=num
#  mem=[]
#  while left>0:
#    read_len=min(default_rd_num,left)
#    mem0=hw.getNode(dev+".DATA_FIFO.RFIFO_DATA").readBlock(read_len)
#    hw.dispatch()
#    valid_len=hw.getNode(dev+".DATA_FIFO.RVALID_LEN").read()
#    hw.dispatch()
#    valid_len=valid_len& 0x7fffffff
##    print "Read 0x%x words from fifo" % valid_len
#    if valid_len!=0:
#      for i in range(valid_len):
#        mem.append(mem0[i])
#      left=left-valid_len
#  return mem

def set_data_source(hw, dev, source):
#0: data from nxyter 1: data auto-generated 
  hw.getNode(dev+".DATA_SOURCE").write(source)
  hw.dispatch()
  return

def set_data_destination(hw, dev, dest):
#0: data to flim fifo 1: data to ipbus fifo
  hw.getNode(dev+".DATA_DEST").write(dest)
  hw.dispatch()
  return

def select_nxyter(hw, dev, sel):
  hw.getNode(dev+".NXYTER_SEL").write(sel)
  hw.dispatch()
  return

def set_pattern_throttle(hw, dev, throttle):
  hw.getNode(dev+".PGEN_THROTTLE").write(throttle)
  hw.dispatch()
  return

def read_nxyter_info(hw, dev):
  val=hw.getNode(dev+".NXYTER.TYPE").read()
  hw.dispatch()
  print "device type:         %s" %(hex(val))

def wait_for_sync(hw, dev, sync_interval):
  print "Wait for reasonable time to send SYNC command..."
  wait_end=0
  while wait_end==0:
    current_time=hw.getNode(dev+".PPS_TO_NOW").read()
    hw.dispatch()
    if current_time<(sync_interval>>2):
      print "Current time=%d" %(current_time)
      wait_end=1;
  return

def system_sync(hw, dev):
  print "Start initialize all the GET4 SYNC count... "
  hw.getNode(dev+".SYNC_ENA").write(0x00000000)
  hw.dispatch()
  hw.getNode(dev+".SYNC_ENA").write(0x00000001)
  hw.dispatch()
  print "System synchronization command has been sent"
  return			

def get_sync_status(hw, dev):
  val=hw.getNode(dev+".SYNC_DONE").read()
  hw.dispatch()
  if val==1:
    print "nDPB Synchronization finished"
  return val

