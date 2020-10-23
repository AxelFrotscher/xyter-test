#!/usr/bin/python
import time
import logging as log
import ipbus_i2c_ctrl


def Int2IP(ipnum):
    o1 = int(ipnum >>24) % 256
    o2 = int(ipnum >>16) % 256
    o3 = int(ipnum >>8) % 256
    o4 = int(ipnum) % 256
    return '%(o1)d.%(o2)d.%(o3)d.%(o4)d' % locals()


def Int2MAC(macnum_m, macnum_l):
    o1 = int(macnum_m >> 8) % 256
    o2 = int(macnum_m) % 256
    o3 = int(macnum_l >> 24) % 256
    o4 = int(macnum_l >> 16) % 256
    o5 = int(macnum_l >> 8) % 256
    o6 = int(macnum_l) % 256
    return '%(o1)02x:%(o2)02x:%(o3)02x:%(o4)02x:%(o5)02x:%(o6)02x' % locals()


def read_public_dev_info(hw, dev):
  log.debug("\nThe public device information is:")
  val = hw.getNode(dev + ".global_dev_reg.DEV_TYPE").read()
  hw.dispatch()
  log.debug("device type:         %s", hex(val))
  val = hw.getNode(dev + ".global_dev_reg.FW_VER").read()
  hw.dispatch()
  log.debug("Firmware version:    %s", hex(val))
  val = hw.getNode(dev + ".global_dev_reg.FMC0_SPT_DEV").read()
  hw.dispatch()
  log.debug("Support FMC0:        %s", hex(val))
  val = hw.getNode(dev + ".global_dev_reg.FMC1_SPT_DEV").read()
  hw.dispatch()
  log.debug("Support FMC1:        %s", hex(val))
  val = hw.getNode(dev + ".global_dev_reg.STAT_REG_NUM").read()
  hw.dispatch()
  log.debug("Status reg number:   %d", val)
  val = hw.getNode(dev + ".global_dev_reg.CTRL_REG_NUM").read()
  hw.dispatch()
  log.debug("Control reg number:  %d", val)
  val = hw.getNode(dev + ".global_dev_reg.OTH_SLV_NUM").read()
  hw.dispatch()
  log.debug("Other slave number:  %d", val)
  val = hw.getNode(dev + ".global_dev_reg.SLV_MASK").read()
  hw.dispatch()
  log.debug("Other slave type:    %s", hex(val))
  return


def read_afck_info(hw, dev):
  log.debug("\nThe AFCK information is:")
  val = hw.getNode(dev + ".global_dev_reg.AFCK_ID").read()
  hw.dispatch()
  log.debug("AFCK ID:             0x%08x", val)
  val = hw.getNode(dev + ".global_dev_reg.FMC0_SPT_BD").read()
  hw.dispatch()
  log.debug("Supported FMC0:      %s", hex(val))
  val = hw.getNode(dev + ".global_dev_reg.FMC1_SPT_BD").read()
  hw.dispatch()
  log.debug("Supported FMC1:      %s", hex(val))
  val = hw.getNode(dev + ".global_dev_reg.FMC0_EXIST").read()
  hw.dispatch()
  if val == 1:
    log.debug("FMC0 installed:      true")
  else:
    log.debug("FMC0 installed:      false")
  val = hw.getNode(dev + ".global_dev_reg.FMC1_EXIST").read()
  hw.dispatch()
  if val == 1:
    log.debug("FMC1 installed:      true")
  else:
    log.debug("FMC1 installed:      false")
  val = hw.getNode(dev + ".global_dev_reg.IPB_DEV_NUM").read()
  hw.dispatch()
  log.debug("Device number:       %d", val)
  val = hw.getNode(dev + ".global_dev_reg.IP_ADDR").read()
  hw.dispatch()
  log.debug("AFCK IP Address:     %s", Int2IP(val))
  mac_m = hw.getNode(dev + ".global_dev_reg.MAC_ADDR_M").read()
  hw.dispatch()
  mac_l = hw.getNode(dev + ".global_dev_reg.MAC_ADDR_L").read()
  hw.dispatch()
  log.debug("AFCK MAC Address:    %s", Int2MAC(mac_m, mac_l))
  return

def read_build_time(hw, dev):
#   ddddd_MMMM_yyyyyy_hhhhh_mmmmmm_ssssss
#(bit 31) ........................ (bit 0)
#Where:
#ddddd = 5 bits to represent 31 days in a month
#MMMM = 4 bits to represent 12 months in a year
#yyyyyy = 6 bits to represent 0 to 63 (to note year 2000 to 2063)
#hhhhh = 5 bits to represent 24 hours in a day
#mmmmmm = 6 bits to represent 60 minutes in an hour
#ssssss = 6 bits to represent 60 seconds in a minute
  timestamp=hw.getNode(dev+".global_dev_reg.FW_TIME_STAMP").read()
  hw.dispatch()
  day  =(timestamp&0xf8000000)>>27
  month=(timestamp&0x07800000)>>23
  year =((timestamp&0x007E0000)>>17)+2000
  hour =(timestamp&0x0001F000)>>12
  minu =(timestamp&0x00000FC0)>>6
  sec  = timestamp&0x0000003F
  return "Firmware build time: %04d-%02d-%02d: %02d:%02d:%02d" %(year, month, day, hour, minu, sec)

def get_afck_id(hw, dev):
  val = hw.getNode(dev + ".global_dev_reg.AFCK_ID").read()
  hw.dispatch()
  return val & 0xFFFF

def get_afck_ip(hw, dev):
  val = hw.getNode(dev + ".global_dev_reg.IP_ADDR").read()
  hw.dispatch()
  return Int2IP(val)

def get_afck_mac(hw, dev):
  mac_m = hw.getNode(dev + ".global_dev_reg.MAC_ADDR_M").read()
  hw.dispatch()
  mac_l = hw.getNode(dev + ".global_dev_reg.MAC_ADDR_L").read()
  hw.dispatch()
  return Int2MAC(mac_m, mac_l)

def afck_i2c_init(hw, dev):
  ipbus_i2c_ctrl.i2c_wr_reg(hw, dev+".i2c_ctrl.prer_lo", 0x3E)  		# Write PRERlo=0x3F(100kHz)
  ipbus_i2c_ctrl.i2c_wr_reg(hw, dev+".i2c_ctrl.prer_hi",0)			# Write PRERhi=0
  ipbus_i2c_ctrl.i2c_wr_reg(hw, dev+".i2c_ctrl.control",0x80)			# Write CTR=0x80: I2C core enable, interrupt disable

def afck_set_clock_matrix(hw, dev, n_in,n_out):
  ipbus_i2c_ctrl.ClkMtx_set_out(hw, dev+".i2c_ctrl", n_in, n_out)
  return

def afck_bus_sel(hw, dev, bus):
  ipbus_i2c_ctrl.bus_sel(hw, dev+".i2c_ctrl", bus)
  return

def afck_set_fms14_frq(hw, dev, frq):
  ipbus_i2c_ctrl.FMS14Q_SetFrq(hw, dev+".i2c_ctrl",frq)
  return

def afck_set_si570_frq(hw, dev, frq):
  ipbus_i2c_ctrl.Si57xSetFrq(hw,  dev+".i2c_ctrl", frq)
  return

def dev_rw_reg_test(hw, dev):
  hw.getNode(dev+".global_dev_reg.SYS_TEST_WR").write(0xa55a5aa5)
  hw.dispatch()
  val=hw.getNode(dev+".global_dev_reg.SYS_TEST_RD").read()
  hw.dispatch()
  if val == 0xa55a5aa5:
    log.debug("Global device register write/read test passed!")
  else:
    log.warning("Global device register write/read test failed!")
  return

def set_afck_base_eqipment_id(hw, dev, eq_id):
  hw.getNode(dev+".global_dev_reg.EQ_ID").write(eq_id)
  hw.dispatch()
  return

def afck_reset_device(hw, dev, dev_num):
  if dev_num == 0:
    log.warning("Global device can't be reset!")
    return
  else:
    val = 1<<dev_num
    hw.getNode(dev+".global_dev_reg.SYS_RST").write(val)
    hw.dispatch()
    hw.getNode(dev+".global_dev_reg.SYS_RST").write(0)
    hw.dispatch()
  return

def flash_program_read_sel(hw, dev, mode):
# 0: flash program  1: flash read
  if mode==0:
    log.debug("Switch to FLASH programming/check ID/verify mode")
  else:
    log.debug("Switch to FLASH reading mode")
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(mode)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FP_FR_SEL").write(1)
  hw.getNode(dev+".global_dev_reg.FP_FR_SEL").write(0)
  hw.dispatch()
  return

def flash_program_start(hw, dev):
  log.info("Start FLASH programming...")
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(1)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FP_START").write(1)
  hw.getNode(dev+".global_dev_reg.FP_START").write(0)
  hw.dispatch()
  return

def flash_program_stop_all(hw,dev):
  log.debug("Stop FLASH programming/check ID/verify")
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(0)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FP_START").write(1)
  hw.getNode(dev+".global_dev_reg.FP_START").write(0)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(0)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FP_CHK_ID_ONLY").write(1)
  hw.getNode(dev+".global_dev_reg.FP_CHK_ID_ONLY").write(0)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(0)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FP_VERIFY_ONLY").write(1)
  hw.getNode(dev+".global_dev_reg.FP_VERIFY_ONLY").write(0)
  hw.dispatch()
  return

def write_flash_data(hw, dev, mem):
  total=len(mem)
  left=total
  writen=0
  while left>0:
    write_len=hw.getNode(dev+".wfifo.WFIFO_LEN").read()
    hw.dispatch()
    if write_len==0:
      time.sleep(0.1)
      continue
    write_len=min(write_len,left)
    hw.getNode(dev+".wfifo.WFIFO_DATA").writeBlock(mem[writen:writen+write_len])
    hw.dispatch()
    writen=writen+write_len
    left=left-write_len
    print 'FLASH programming: %d%% ( %d / %d ) finised!\r' %(writen*100/total, writen, total),;
  log.info("\nFLASH programming: Write to Flash finished")
  return

def flash_program_check_ID(hw, dev):
  log.debug("Start FLASH ID checking...")
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(1)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FP_CHK_ID_ONLY").write(1)
  hw.getNode(dev+".global_dev_reg.FP_CHK_ID_ONLY").write(0)
  hw.dispatch()
  return

def flash_program_verify(hw, dev):
  log.debug("Start FLASH verification...")
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(1)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FP_VERIFY_ONLY").write(1)
  hw.getNode(dev+".global_dev_reg.FP_VERIFY_ONLY").write(0)
  hw.dispatch()
  return

def get_flash_prog_busy_status(hw, dev):
  val=hw.getNode(dev+".global_dev_reg.FP_READY_BUSY").read()
  hw.dispatch()
  if val == 0:
    log.debug("FLASH programming status: READY")
  elif val==1:
    log.debug("FLASH programming status: BUSY")
  else:
    log.warning("FLASH programming status: WRONG STATUS")
  return val

def get_flash_prog_done(hw, dev):
  val=hw.getNode(dev+".global_dev_reg.FP_DONE").read()
  hw.dispatch()
  return val

def get_flash_prog_error_status(hw, dev):
  val=hw.getNode(dev+".global_dev_reg.FP_ERROR").read()
  hw.dispatch()
  if val == 0:
    log.debug("FLASH programming/check ID/verify success!")
    return 0
  else:
    status=hw.getNode(dev+".global_dev_reg.FP_ERROR_CODE").read()
    hw.dispatch()
    if (status&0x1)!=0:
      log.warning("FLASH programming: Read FLASH ID code error!")
    if (status&0x2)!=0:
      log.warning("FLASH programming: Erase FLASH error!")
    if (status&0x4)!=0:
      log.warning("FLASH programming: FLASH programming error!")
    if (status&0x8)!=0:
      log.warning("FLASH programming: Time out error!")
    if (status&0x10)!=0:
      log.warning("FLASH programming: CRC check error!")
    return 1

def get_flash_prog_status(hw, dev):
# bit 0: started
# bit 1: Initialize OK
# bit 2: Check ID OK
# bit 3: Erase switch word OK
# bit 4: Erase OK
# bit 5: Program OK
# bit 6: Verify OK
# bit 7: Program switch word OK
  val=hw.getNode(dev+".global_dev_reg.FP_STATUS").read()
  hw.dispatch()
  return val

def flash_read_start(hw, dev, mode):
  log.debug("Start FLASH reading...")
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(mode)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FR_START").write(1)
  hw.getNode(dev+".global_dev_reg.FR_START").write(0)
  hw.dispatch()
  return

def set_flash_read_start_addr(hw, dev, addr):
  log.debug("Set the start address of FLASH reading to : %s", hex(addr))
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(addr)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FR_RD_START_ADDR").write(1)
  hw.getNode(dev+".global_dev_reg.FR_RD_START_ADDR").write(0)
  hw.dispatch()
  return

def read_flash_data(hw, dev, num):
  left=num
  mem=[]
  while left>0:
    read_len=hw.getNode(dev+".rfifo.RFIFO_LEN").read()
    self.hw.dispatch()
    time.sleep(0.01)
    if read_len==0:
      continue
    read_len=min(left,int(read_len))
    mem0=self.hw.getNode(dev+".rfifo.RFIFO_DATA").readBlock(read_len)
    self.hw.dispatch()
#    print read_len
    mem.extend(mem0)
    left=left-read_len
  return mem

def set_flash_read_counter(hw, dev, count):
  log.debug("Set FLASH reading counter to : %s", hex(count))
  hw.getNode(dev+".global_dev_reg.FLASH_CMD_D").write(count)
  hw.dispatch()
  hw.getNode(dev+".global_dev_reg.FR_RD_COUNT").write(1)
  hw.getNode(dev+".global_dev_reg.FR_RD_COUNT").write(0)
  hw.dispatch()
  return

def get_flash_read_busy_status(hw, dev):
  val=hw.getNode(dev+".global_dev_reg.FR_READY_BUSY").read()
  hw.dispatch()
  if val == 0:
    log.debug("FLASH reading status: READY")
  elif val == 1:
    log.debug("FLASH reading status: BUSY")
  else:
    log.warning("FLASH reading status: WRONG STATUS")
  return val


