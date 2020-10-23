#!/usr/bin/python
import math
import time

class pGen_dev_ctrl:
 
  def __init__(self, flim_num, hw, dev):
    self.flim_num=flim_num
    self.hw=hw
    self.dev=dev
  
  def read_public_dev_info(self):
    print "\nThe public device information is:"
    val=self.hw.getNode(self.dev+".DEV_TYPE").read()
    self.hw.dispatch()
    print "Device type:         %s" %(hex(val))
    val=self.hw.getNode(self.dev+".FW_VER").read()
    self.hw.dispatch()
    print "Firmware version:    %s" %(hex(val))
    val=self.hw.getNode(self.dev+".FMC0_SPT_DEV").read()
    self.hw.dispatch()
    print "Support FMC0:        %s" %(hex(val))
    val=self.hw.getNode(self.dev+".FMC1_SPT_DEV").read()
    self.hw.dispatch()
    print "Support FMC1:        %s" %(hex(val))
    val=self.hw.getNode(self.dev+".STAT_REG_NUM").read()
    self.hw.dispatch()
    print "Status reg number:   %d" % val
    val=self.hw.getNode(self.dev+".CTRL_REG_NUM").read()
    self.hw.dispatch() 
    print "Control reg number:  %d" % val
    val=self.hw.getNode(self.dev+".OTH_SLV_NUM").read()
    self.hw.dispatch()
    print "Other slave number:  %d" % val
    val=self.hw.getNode(self.dev+".SLV_MASK").read()
    self.hw.dispatch()
    print "Other slave type:    %s" %(hex(val))
    return
 
  def dev_rw_reg_test(self):
    self.hw.getNode(self.dev+".DEV_TEST_W").write(0xa55a5aa5)
    self.hw.dispatch()
    val=self.hw.getNode(self.dev+".DEV_TEST_R").read()
    self.hw.dispatch()
    if val==0xa55a5aa5:
      print "register write/read test passed!"
    else:
      print "register write/read test failed!"
      print "Write: 0x%08X  Read: 0x%08X" %(0xa55a5aa5, val)
    return

  def wait_for_sync(self, sync_interval):
    print "Wait for reasonable time to send SYNC command..."
    wait_end=0
    while wait_end==0:
      current_time=self.hw.getNode(self.dev+".PPS_TO_NOW").read()
      self.hw.dispatch()
      if current_time<(sync_interval>>2):
        print "Current time=%d" %(current_time)
        wait_end=1;
    return

  def get_sync_status(self):
    status=self.hw.getNode(self.dev+".SYNC_DONE").read()
    self.hw.dispatch()
    if status==1:
      print "LTS Synchronization finished"
#    else:
#      print "LTS Synchronization is not finished"
    return status

  def set_throttle(self, throttle):
    self.hw.getNode(self.dev+".THROTTLE").write(throttle)
    self.hw.dispatch()
    rate=100.0-(float(throttle)/float(0xffff)*100.0)
    print "Set throttle to %d (%.2f%%)!" %(throttle, rate)
    return

  def set_sync_ena(self, ena):
    if (ena==0)or(ena==1):
      self.hw.getNode(self.dev+".SYNC_ENA").write(ena)
      self.hw.dispatch()
    if ena==1:
      self.hw.getNode(self.dev+".SYNC_ENA").write(0)
      self.hw.dispatch()
    return 0

  def sel_ipb_flim(self, sel):
    if (sel==0)or(sel==1):
      self.hw.getNode(self.dev+".IPB_FLIM_SEL").write(sel)
      self.hw.dispatch()
    if sel==0:
      print "Current mode: Channel 0 => IPbus FIFO"
    elif sel==1:
      print "Current mode: Channel 0 => FLIM"
    else:
      print "Parameter error!"
    return 0

  def set_channel_enable(self, link, mask_high24, mask_low32):
    if (link<0)or(link>self.flim_num-1):
      print "Parameter error!"
    self.hw.getNode(self.dev+".CHANNEL_ENA_0").write(mask_low32)
    self.hw.dispatch()   
    val=link<<24|mask_high24
#    print "CHANNEL_ENA_1=0x%X" %(val)
    self.hw.getNode(self.dev+".CHANNEL_ENA_1").write(int(val))
    self.hw.dispatch()     
    print "Flim channel %d : fifo enable mask is 0x%X%X" %(link, mask_high24, mask_low32)

  def read_ipb_data_fifo(self, num):
    left=num
    mem=[]
    while left>0:
      read_len=self.hw.getNode(self.dev+".DATA_FIFO.RFIFO_LEN").read()
      self.hw.dispatch()  
      time.sleep(0.01)
      if read_len==0:
        print read_len
        continue
      read_len=int(read_len)
      mem0=self.hw.getNode(self.dev+".DATA_FIFO.RFIFO_DATA").readBlock(read_len)
      self.hw.dispatch()
      mem.extend(mem0)
      left=left-read_len
    return mem
#    default_rd_num=255
#    left=num
#    mem=[]
#    while left>0:
#      read_len=min(default_rd_num,left)
#      mem0=self.hw.getNode(self.dev+".DATA_FIFO.RFIFO_DATA").readBlock(read_len)
#      self.hw.dispatch()
#      valid_len=self.hw.getNode(self.dev+".DATA_FIFO.RVALID_LEN").read()
#      self.hw.dispatch()
#      valid_len=valid_len& 0x7fffffff    
##      print "Read %d words from fifo" % valid_len
#      if valid_len!=0:
#        for i in range(valid_len):
#          mem.append(mem0[i])
#        left=left-valid_len
#    return mem

			

