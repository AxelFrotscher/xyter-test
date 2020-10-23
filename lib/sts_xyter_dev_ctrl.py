import pickle
import time
import logging as log

N_OF_SLOTS = 5
LINK_BREAK = 0b11111
# Detector masks
SOS_DET_STABLE0 = 1 << 8
SOS_DET_STABLE1 = 1 << 7
SOS_DET = 1 << 6
EOS_DET_STABLE1 = 1 << 5
EOS_DET = 1 << 4
K28_5_DET_STABLE1 = 1 << 3
K28_5_DET = 1 << 2
K28_1_DET_STABLE1 = 1 << 1
K28_1_DET = 1 << 0
# Detector clear and sel masks
SOS_CLEAR = 1 << 0
EOS_CLEAR = 1 << 1
K28_1_CLEAR = 1 << 2
K28_5_CLEAR = 1 << 3
# Encoder mode values
MODE_SOS = 2
MODE_K28_1 = 3
MODE_EOS = 1
MODE_FRAME = 0


class ipbus(object):
  """
  Wrapper for objects used for IPbus communication
  """
  def __init__(self, hw, node):
    self.hw = hw
    self.node = hw.getNode(node)
    pass

  def write(self, val):
    self.node.write(val)
    self.hw.dispatch()

  def read(self):
    v = self.node.read()
    self.hw.dispatch()
    return v

  def readBlock(self, nwords):
    v = self.node.readBlock(nwords)
    self.hw.dispatch()
    return v


class sts_xyter_com_ctrl(object):
  """
  Class for controlling a single COMMON firmware module
  """
  hw = None
  dev = None

  def __init__(self, hw, dev):
    self.hw = hw
    self.dev = dev
    self.tfc_fr_per_cnt = ipbus(hw, dev + ".TFC_FR_PER_CNT")
    self.tfc_pps_pos = ipbus(hw, dev + ".TFC_PPS_POS")
    self.ckstrobe = 0

    self.tdreg_val      = ipbus(hw, dev+".TD_REG_VAL")
    self.tdreg_tdval    = ipbus(hw, dev+".TD_REG_TDVAL")
    self.tdreg_tdfnum   = ipbus(hw, dev+".TD_REG_TDFNUM")
    self.tdreg_stat     = ipbus(hw, dev+".TD_REG_SAT")
    self.tdreg_readback = ipbus(hw, dev+".TD_REG_READBACK")

  def read_public_dev_info(self):
    log.debug("The public device information is:")
    val = self.hw.getNode(self.dev + ".DEV_TYPE").read()
    self.hw.dispatch()
    log.debug("Device type:         %s", hex(val))
    val = self.hw.getNode(self.dev + ".FW_VER").read()
    self.hw.dispatch()
    log.debug("Firmware version:    %s", hex(val))
    val = self.hw.getNode(self.dev + ".FMC0_SPT_DEV").read()
    self.hw.dispatch()
    log.debug("Support FMC0:        %s", hex(val))
    val = self.hw.getNode(self.dev + ".FMC1_SPT_DEV").read()
    self.hw.dispatch()
    log.debug("Support FMC1:        %s", hex(val))
    val = self.hw.getNode(self.dev + ".STAT_REG_NUM").read()
    self.hw.dispatch()
    log.debug("Status reg number:   %d", val)
    val = self.hw.getNode(self.dev + ".CTRL_REG_NUM").read()
    self.hw.dispatch()
    log.debug("Control reg number:  %d", val)
    val = self.hw.getNode(self.dev + ".IFACE_SLV_NUM").read()
    self.hw.dispatch()
    log.debug("Interface slaves:    %d", val)
    val = self.hw.getNode(self.dev + ".SLV_MASK").read()
    self.hw.dispatch()
    log.debug("Other slave type:    %s", hex(val))
    return

  def dev_rw_reg_test(self):
    self.hw.getNode(self.dev + ".DEV_TEST_W").write(0xa55a5aa5)
    self.hw.dispatch()
    val = self.hw.getNode(self.dev + ".DEV_TEST_R").read()
    self.hw.dispatch()
    if val == 0xa55a5aa5:
      log.debug("Device register write/read test passed!")
    else:
      log.debug("Device register write/read test failed!")
    return

  def interface_count(self):
    val = self.hw.getNode(self.dev + ".IFACE_SLV_NUM").read()
    self.hw.dispatch()
    return val

# Currently not supported by firmware
  def rst_sts_xyter_ic_all(self):
    log.debug("Reset STS-XYTER ...")
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".STS_RST_N").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(0)
    self.hw.dispatch()
#    time.sleep(0.1)
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".STS_RST_N").write(0)
    self.hw.dispatch()
    log.debug("Reset done")
    return

  def reset_fifo_all(self):
    log.debug("Reset all FIFOs")
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".RST_FIFO").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(0)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".RST_FIFO").write(0)
    self.hw.dispatch()
    self.reset_raw_fifo()
    return

  def reset_raw_fifo(self):
    log.debug("Reset raw data FIFO")
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".RST_RAW_FIFO").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(0)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".RST_RAW_FIFO").write(0)
    self.hw.dispatch()
    return

  def reset_data_processing(self, val):
    self.hw.getNode(self.dev+".SYS_CMD_DATA").write(val)
    self.hw.dispatch()
    self.hw.getNode(self.dev+".DAT_PROC_RES").write(val)
    self.hw.dispatch()
    return

  def set_dest(self, data_dest):
    """
    data_dest: 0: data to flim fifo 1: data to ipbus fifo
    """
    if data_dest == 0:
      log.debug("Work mode: Data will be transfered to FLIM")
    else:
      log.debug("Work mode: Data will be transfered to IPBus data FIFO")
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(data_dest)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".DATA_DEST").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".DATA_DEST").write(0)
    self.hw.dispatch()
    return

  def read_ipb_data_fifo_len(self):
    read_len = self.hw.getNode(self.dev + ".DATA_FIFO.RFIFO_LEN").read()
    self.hw.dispatch()
    return read_len

  def read_ipb_rawdata_fifo_len(self):
    read_len = self.hw.getNode(self.dev + ".RAW_DATA_FIFO.RFIFO_LEN").read()
    self.hw.dispatch()
    return read_len

  def read_ipb_data_fifo(self, num):
    left = num
    mem = []
    while left > 0:
      read_len = self.hw.getNode(self.dev + ".DATA_FIFO.RFIFO_LEN").read()
      self.hw.dispatch()
      if read_len == 0:
        time.sleep(0.01)
        continue
      read_len = min(left, int(read_len))
      node = self.hw.getNode(self.dev + ".DATA_FIFO.RFIFO_DATA")
      mem0 = node.readBlock(read_len)
      self.hw.dispatch()
      # log.debug("%d", read_len)
      mem.extend(mem0.value())
      left = left - read_len
    return mem

  def read_ipb_raw_data_fifo(self, num):
    left = num
    mem = []
    while left > 0:
      read_len = self.hw.getNode(self.dev + ".RAW_DATA_FIFO.RFIFO_LEN").read()
      self.hw.dispatch()
      if read_len == 0:
        time.sleep(0.01)
        continue
      read_len = min(left, int(read_len))
      node = self.hw.getNode(self.dev + ".RAW_DATA_FIFO.RFIFO_DATA")
      mem0 = node.readBlock(read_len)
      self.hw.dispatch()
      # log.debug("%d", read_len)
      mem.extend(mem0.value())
      left = left - read_len
    return mem

  def wait_for_sync(self, sync_interval):
    log.debug("Wait for reasonable time to send SYNC command...")
    wait_end = 0
    while wait_end == 0:
      current_time = self.hw.getNode(self.dev + ".PPS_TO_NOW").read()
      self.hw.dispatch()
      if current_time < (sync_interval >> 2):
        log.debug("Current time={}".format(current_time))
        wait_end = 1
    return

  def system_sync(self):
    log.debug("Start to reset the STS-XYTER epoch count...")
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(0)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".SYNC_ENA").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".SYS_CMD_DATA").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".SYNC_ENA").write(0)
    self.hw.dispatch()
    return

  def get_sync_status(self):
    status = self.hw.getNode(self.dev + ".LTS_SYNC_DONE").read()
    self.hw.dispatch()
    if status == 1:
      log.debug("LTS Synchronization finished")
    return status

  def clkout_sel_output(self, output):
    self.hw.getNode(self.dev + ".CKOSEL").write(output)
    self.hw.dispatch()
    return

  def clkout_set_delay(self, delay):
    # CDelLock = ipbus(self.hw, self.dev + ".CDEL_LOCK")
    CDelRdy = ipbus(self.hw, self.dev + ".CDEL_RDY")
    ClkDelStr = ipbus(self.hw, self.dev + ".CKDELSTR")
    ClkDel = ipbus(self.hw, self.dev + ".CKDEL")
    ClkDel.write(delay)
    self.ckstrobe ^= 1
    ClkDelStr.write(self.ckstrobe)
    # Wait until Clock delay gets locked
    time.sleep(0.0002)
    counter = 0
    while CDelRdy.read() != 0x1:
      if 100 == counter :
        print counter
      counter += 1
      pass


class sts_xyter_iface_ctrl(object):
  def __init__(self, common, iface, chip_nr, afck_id):
    self.com = common
    self.hw = common.hw
    self.dev = common.dev + ".IFACE" + str(iface)
    self.iface = iface
    self.chip_nr = chip_nr
    self.afck_id = afck_id
    self.seq_nr = 1
    self.slot_nr = 0
    self.cmd_slots = [ipbus(self.hw, self.dev + node) for node
                      in (".CMD0", ".CMD1", ".CMD2", ".CMD3", ".CMD4")]
    self.cmd_stats = [ipbus(self.hw, self.dev + node) for node
                      in (".CST0", ".CST1", ".CST2", ".CST3", ".CST4")]
    self.td_cmd_slots = [ipbus(self.hw, self.dev + node) for node
                         in (".TD_CMD0", ".TD_CMD1")]
    self.td_cmd_stats = [ipbus(self.hw, self.dev + node) for node
                         in (".TD_CST0", ".TD_CST1")]
    self.td_cmd_fnums = [ipbus(self.hw, self.dev + node) for node
                         in (".TD_FNUM0", ".TD_FNUM1")]

    self.Cmd0RepeatPeriod = ipbus(self.hw, self.dev + ".REPEAT_CMD0_PERIOD")

    self.ElinkWarnings = ipbus(self.hw, self.dev + ".ELINK_WARNINGS")

    # register
    self.CDelLock = ipbus(self.hw, self.com.dev + ".CDEL_LOCK")
    self.CDelRdy = ipbus(self.hw, self.com.dev + ".CDEL_RDY")
    self.DDelLock = ipbus(self.hw, self.dev + ".DDEL_LOCK")
    self.EncMode = ipbus(self.hw, self.dev + ".ENC_MODE")
    self.InpDelays = [ipbus(self.hw, self.dev + node) for node
                      in (".DDEL0", ".DDEL1", ".DDEL2", ".DDEL3", ".DDEL4")]
    self.DetClears = [ipbus(self.hw, self.dev + node) for node
                      in (".DETI0", ".DETI1", ".DETI2", ".DETI3", ".DETI4")]
    self.DetOuts = [ipbus(self.hw, self.dev + node) for node
                    in (".DETO0", ".DETO1", ".DETO2", ".DETO3", ".DETO4")]

  def rst_sts_xyter_ic(self, iface):
    """
    Not implemented in firmware yet
    """
    log.debug("Reset STS-XYTER #{} ...".format(iface))
    self.hw.getNode(self.dev + ".STS_RST_N").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".STS_RST_N").write(0)
    self.hw.dispatch()
    log.debug("Reset done")
    return

  def reset_fifo(self):
    log.debug("Reset FIFOs ...")
    self.hw.getNode(self.dev + ".RST_FIFO").write(1)
    self.hw.dispatch()
    self.hw.getNode(self.dev + ".RST_FIFO").write(0)
    self.hw.dispatch()
    return

  def set_work_mode(self, pass_through, data_source):
    """
    pass_through: 0: data pre-proc enabled 1: data pre-proc disabled
    data_source:  0: data from get4        1: data auto-generated
    """
    if pass_through == 1:
      log.debug("Work mode: DATA_PASS_THROUGH mode enabled")
    else:
      log.debug("Work mode: DATA_PASS_THROUGH mode disabled")
    self.hw.getNode(self.dev + ".DATA_PASS_THR").write(pass_through)
    self.hw.dispatch()
    if data_source == 0:
      log.debug("Work mode: Data gotten from GET4 will be used")
    else:
      log.debug("Work mode: Auto generated data will be used")
    self.hw.getNode(self.dev + ".DATA_SOURCE").write(data_source)
    self.hw.dispatch()
    return

  def set_epoch_suppress(self, ena):
    if ena == 1:
      log.debug("epoch suppression enabled")
    else:
      log.debug("epoch suppression disabled")
    self.hw.getNode(self.dev + ".ENA_EPOCH_SUPR").write(ena)
    self.hw.dispatch()
    return

  def set_link_break(self, val):
    self.hw.getNode(self.dev + ".LINK_BREAK").write(val)
    self.hw.dispatch()
    return

  def emg_write(self, row, col, val):
    self.write( row, col, val, 2, False )
    '''
    xaddr = ((self.chip_nr & 0xf) << 21) | \
            ((self.seq_nr & 0xf) << 17) | \
            (0x01 << 15) | \
            ((col & 0x7f) << 8) | \
            (row & 0xff)
    self.seq_nr += 1
    self.seq_nr %= 16
    xval = (self.chip_nr & 0xf) << 21 | \
           ((self.seq_nr & 0xf) << 17) | \
           (0x02 << 15) | \
           (val & 0x7fff)
    self.seq_nr += 1
    self.seq_nr %= 16
    # Write address
    self.cmd_slots[self.slot_nr].write(xaddr)
    slot1 = self.slot_nr
    self.slot_nr += 1
    self.slot_nr %= N_OF_SLOTS
    # Write data
    self.cmd_slots[self.slot_nr].write(xval)
    while True:
      val = self.cmd_stats[self.slot_nr].read()
      if val & 0x80000000 == 0:
         break
    while True:
      if self.cmd_stats[slot1].read() & 0x80000000 == 0:
        break
    self.slot_nr += 1
    self.slot_nr %= N_OF_SLOTS
    '''

  def write(self, row, col, val, timeout=2, checkAck = True ):
    xaddr = ((self.chip_nr & 0xf) << 21) | \
            ((self.seq_nr & 0xf) << 17) | \
            (0x01 << 15) | \
            ((col & 0x7f) << 8) | \
            (row & 0xff)
    self.seq_nr += 1
    self.seq_nr %= 16
    xval = (self.chip_nr & 0xf) << 21 | \
           ((self.seq_nr & 0xf) << 17) | \
           (0x02 << 15) | \
           (val & 0x7fff)
    self.seq_nr += 1
    self.seq_nr %= 16

    # Ensure that we are going to send the command using a pair of frames
    # => Starting slot should be an even one
    # => Starting slot cannot be the last possible if Nb slot is odd
    if 1 == self.slot_nr % 2 :
        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS
        log.debug("Increase slot to have a pair starting on even slot for write command, new slot %u", self.slot_nr )
    if (1 == N_OF_SLOTS % 2) and (N_OF_SLOTS - 1 == self.slot_nr) :
        self.slot_nr = 0
        log.debug("Change slot to have a full pair for write command" )

    # Force bit 25 of both commands to 1 to indicate we are doing a (Addr + Data) pair sending
    xaddr |= (0x01 << 25)
    xval  |= (0x01 << 25)

    # Write address
    start_time = time.time()
    self.cmd_slots[self.slot_nr].write(xaddr)

    slot_prev = self.slot_nr
    self.slot_nr += 1
    self.slot_nr %= N_OF_SLOTS

    # Write data
    self.cmd_slots[self.slot_nr].write(xval)

    while checkAck:
      ret_val = self.cmd_stats[slot_prev].read()
      if ret_val & (0x1 << 31) == 0:
        return_type = ret_val & (0x3 << 19)
        if return_type == (0x1 << 19):
          log.debug("Write wraddr ACK: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
          log.debug("ACK fields: seqIn %u, seqOut %u CP %u Status %x TS_MSB %u CRC %x",
                    self.seq_nr, (ret_val >> 15) & 0xf, (ret_val >> 14) & 0x1,
                    (ret_val >> 10) & 0xf, (ret_val >> 4) & 0x3f, (ret_val >> 0) & 0xf )
        elif return_type == (0x2 << 19):
          log.warning("Write wraddr NACK: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
          log.warning("NACK: Seq %2u CP %u Status %x",
                      (ret_val >> 15) & 0xf, (ret_val >> 14) & 0x1, (ret_val >> 10) & 0xf )
        elif return_type == (0x3 << 19):
          log.warning("Write wraddr ALERT: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
        elif return_type == (0x0 << 19):
          log.warning("Write wraddr SEQ MISS: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
          log.warning("SEQ MISS: Seq %2u CP %u Status %x",
                      (ret_val >> 15) & 0xf, (ret_val >> 14) & 0x1, (ret_val >> 10) & 0xf )
        break
      if time.time() - start_time > timeout:
        self.cmd_slots[slot_prev].write(0x1 << 31)
        self.cmd_slots[self.slot_nr].write(0x1 << 31)
        raise Exception("Timeout waiting for STSXYTER wraddr ack after delay")

    while checkAck:
      ret_val = self.cmd_stats[self.slot_nr].read()
      if ret_val & (0x1 << 31) == 0:
        return_type = ret_val & (0x3 << 19)
        if return_type == (0x1 << 19):
          log.debug("Write wrdata ACK: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
          log.debug("ACK fields: seqIn %u, seqOut %u CP %u Status %x TS_MSB %u CRC %x",
                    self.seq_nr, (ret_val >> 15) & 0xf, (ret_val >> 14) & 0x1,
                    (ret_val >> 10) & 0xf, (ret_val >> 4) & 0x3f, (ret_val >> 0) & 0xf )
        elif return_type == (0x2 << 19):
          log.warning("Write wrdata NACK: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
          log.warning("NACK: Seq %2u CP %u Status %x",
                      (ret_val >> 15) & 0xf, (ret_val >> 14) & 0x1, (ret_val >> 10) & 0xf )
        elif return_type == (0x3 << 19):
          log.warning("Write wrdata ALERT: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
        elif return_type == (0x0 << 19):
          log.warning("Write wrdata SEQ MISS: 0x%08x when writing r%3u c%2u val 0x%4x",
                      ret_val, row, col, val )
          log.warning("SEQ MISS: Seq %2u CP %u Status %x",
                      (ret_val >> 15) & 0xf, (ret_val >> 14) & 0x1, (ret_val >> 10) & 0xf )
        break
      if time.time() - start_time > timeout:
        self.cmd_slots[self.slot_nr].write(0x1 << 31)
        raise Exception("Timeout waiting for STSXYTER wrdata ack")

    self.slot_nr += 1
    self.slot_nr %= N_OF_SLOTS

  def read(self, row, col, timeout=2 ):
    xrdad = ((self.chip_nr & 0xf) << 21) | \
            ((self.seq_nr & 0xf) << 17) | \
            (0x03 << 15) | \
            ((col & 0x7f) << 8) | \
            (row & 0xff)
    self.seq_nr += 1
    self.seq_nr %= 16

    start_time = time.time()
    # Read command
    self.cmd_slots[self.slot_nr].write(xrdad)
    timeout_cnt=0
    while True:
      val = self.cmd_stats[self.slot_nr].read()
      if val & 0x80000000 == 0:
        break
      if time.time() - start_time > timeout:
        self.cmd_slots[self.slot_nr].write(0x1 << 31)
        raise Exception("Timeout waiting for STSXYTER read ack")
        log.error("Read command timeout on answer")
    self.slot_nr += 1
    self.slot_nr %= N_OF_SLOTS
    # NACK comes in different frame than RDDATA, so check frame type too
    log.debug("Return val = 0x%08x", val)
    if val & 0x200000 == 0:
      if val & 0x080000 == 0:
        log.warning("Command NACK!")
    return (val & 0x1fffff) >> 6

  def write_check(self,row,col,val):
    self.write(row,col,val)
    w_val = val

    r_val = self.read(row,col)

    #print "r_val", r_val
    if row <= 130 :
      r_val = (r_val & 0xff)
      #print "val1 ", val1
      #print "r_val ", r_val

    if r_val == w_val:
      log.debug("Initial written value. val %u" , w_val)
      log.debug("read_val %u" ,r_val )
      log.debug("Register value set correctly: [%3u, %3u, %4u ]",row, col, w_val )
#      kk=1
    else:
      log.warning("ERROR writing the register: [{:3d},{:3d}] {:5d} vs {:5d}".format(row, col, r_val, w_val) )
      raise Exception("Failed to check written value")

    return

  def td_write(self, row, col, val, fnum, blocking):
    fnum = fnum & ((1 >> 28) - 1)
    fnum1 = (fnum + 1) & ((1 >> 28) - 1)
    fnum |= (1 << 31)
    fnum1 |= (1 << 31)
    seq_nr = 14
    xaddr = ((self.chip_nr & 0xf) << 21) | \
            ((seq_nr & 0xf) << 17) | \
            (0x01 << 15) | \
            ((col & 0x7f) << 8) | \
            (row & 0xff)
    seq_nr = 15
    xval = (self.chip_nr & 0xf) << 21 | \
           ((seq_nr & 0xf) << 17) | \
           (0x02 << 15) | \
           (val & 0x7fff)
    # Write data
    self.td_cmd_slots[1].write(xval)
    self.td_cmd_fnums[1].write(fnum1)
    # Write address
    self.td_cmd_slots[0].write(xaddr)
    self.td_cmd_fnums[0].write(fnum)
    if blocking:
      # Usually we don't wait until the TD command is executed.
      # But for debugging purposes it may be good to wait and print the status!
      while True:
        val = self.td_cmd_stats[0].read()
        val2 = self.td_cmd_stats[1].read()
        log.debug(hex(val) + ":" + hex(val2))
        if (val & 0x80000000 == 0) and (val2 & 0x80000000 == 0):
          break
    # Here we should check if it is not an NACK!

  def td_cancel(self):
    # Prepare TD slot 1 for desactivation
    self.td_cmd_slots[1].write(1 << 31)
    self.td_cmd_fnums[1].write(1 << 31)
    # Prepare TD slot 0 for desactivation and trigger the desactivation
    self.td_cmd_slots[0].write(1 << 31)
    self.td_cmd_fnums[0].write(1 << 31)
    while True:
      val = self.td_cmd_stats[0].read()
      val2 = self.td_cmd_stats[1].read()
      log.debug(hex(val) + ":" + hex(val2))
      if (val & 0x80000000 == 0) and (val2 & 0x80000000 == 0):
         break

  def find_center(self, dta, dlen):
    # Find first "False" position
    start = -1
    for i in range(0, dlen):
      if dta[i] is False:
        start = i
    if start == -1:
      raise Exception("No False value in data")
    # Now we are looking for the longest area of True values
    was_true = False
    longest = -1
    lb = -1
    le = -1
    for i in range(0, dlen):
      j = (start + i + 1) % dlen
      if dta[j]:
        if was_true:
          # We are in the sequence of True values
          ie = j
          ilen += 1
        else:
          ib = j
          ie = j
          ilen = 1
          was_true = True
      else:
        # End of sequence of True values
        if was_true:
          if ilen > longest:
            lb = ib
            le = ie
            longest = ilen
        was_true = False
    # Please note that it is granted, that we ended scanning at the Fale value!
    # We started AFTER the last False position, so the last checked value will
    # be that last False position. Therefore it is sure that the "else"
    # sequence will be executed after the last sequence of True values!
    if longest == -1:
      raise Exception("No True values in scanned data!")
    if lb < le:
      res = int((le + lb) / 2)
    else:
      res = int(((lb + le + dlen) / 2) % dlen)
    return res

  def full_link_sync(self, link_break_user):
    """
    Perform full link synchronisation procedure.
    It should be noted that this function won't automatically enable data
    frame mode, so after synchronisation you should call EncMode(MODE_FRAME)
    to enable data transmission.
    """
    log.info("\n### Doing full eLink SYNC for for STSXYTER #%d with address %d ###" %(self.iface, self.chip_nr))
    self.com.clkout_sel_output(self.iface)
    self.com.clkout_set_delay(0)
    self.com.clkout_set_delay(0)
    # Force SOS mode
    #print "sun Force SOS mode"
    self.EncMode.write(MODE_SOS)
    for i in range(0, 5):
      #print "sun i", i
      self.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
      time.sleep(0.0001)
      self.DetClears[i].write(0)
    time.sleep(0.0001)
    log.debug("DDelLock: {:#b}, CDelLock: {}, CDelRdy: {}".format(
              int(self.DDelLock.read()), self.CDelLock.read(),
              self.CDelRdy.read()))
    # Check, that all input channels responded
    print "Check, that all input channels responded"
    for i in range(0, 5):
      #print "sun i", i
      r = self.DetOuts[i].read()
      if (r & SOS_DET == 0) and (link_break_user & (1 << i)):
        log.debug("{}, {:#x}, {}".format(i, r, "SOS not received after 1us"))
        raise Exception("Not received SOS")
    # Clear glitch detectors
    for i in range(0, 5):
      self.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
    for i in range(0, 5):
      self.DetClears[i].write(0)
    # Wait for testing period
    #print "sun Wait for testing period"
    time.sleep(0.0001)
    # Verify results
    for i in range(0, 5):
      #print "sun i", i
      r = self.DetOuts[i].read()
      log.debug("{}, {}".format(i, r))
    # Now switch to sending K28_1
    #print "sun Now switch to sending K28_1"
    self.EncMode.write(MODE_K28_1)
    time.sleep(0.0002)
    # Verify results
    for i in range(0, 5):
      #print "sun i", i
      r = self.DetOuts[i].read()
      log.debug("K28_1? {} {}".format(i, r))
    # Now we should shift the delay and check results - to be done later!
    test = []
    CLK_STEPS = 88
    clk_del = 0
    while clk_del < CLK_STEPS:
      # Scan possible values, looking for those, assuring correct transmission
      #print "sun clk_del", clk_del
      self.com.clkout_set_delay(clk_del)
      time.sleep(0.0002)
      # Clear detectors
      #print "sun Clear detectors"
      for i in range(0, 5):
        #print "sun i", i
        self.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
      time.sleep(0.0002)
      for i in range(0, 5):
        #print "Det Clears sun i", i
        self.DetClears[i].write(0)
      # Wait a little and check glitch detectors
      time.sleep(0.002)
      res = []
      sos_all = True
      for i in range(0, 5):
        r = self.DetOuts[i].read()
        r1 = (r & SOS_DET_STABLE0) or (link_break_user & (1 << i) == 0)
        res.append(r1 != 0)
        if r1 == 0:
          sos_all = False
      test.append(sos_all)
      log.debug("{} {}".format(clk_del, res))
      log.info("{} {}".format(clk_del, res))
      clk_del += 1
    #print "sun clk decay scan finish!!!!!"
    clk_del = self.find_center(test, CLK_STEPS)
    # build a nice window eye graph to display
    #print "sun build a nice window eye graph to display"
    window = ['_' if item else 'X' for item in test]
    window.insert(0, '|')
    window.append('|')
    window = ''.join(window)
    log.info("Clock delay = {}".format(clk_del))
    log.info("Eye window of the clock signal:")
    log.info(window)
    # Set the clock delay to the found value and adjust the input data delays
    #print "sun Set the clock delay to the found value and adjust the input data delays"
    self.com.clkout_set_delay(clk_del)
    data_del = 0
    test = [[], [], [], [], []]
    while data_del < 64:
      for i in range(0, 5):
        self.InpDelays[i].write(data_del)
      # Wait a little and clear glitch detectors
      time.sleep(0.0002)
      while self.DDelLock.read() != 0x1f:
        pass
      time.sleep(0.0002)
      for i in range(0, 5):
        self.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
      time.sleep(0.0002)
      for i in range(0, 5):
        self.DetClears[i].write(0)
      # Wait for test result
      time.sleep(0.002)
      res = []
      for i in range(0, 5):
        r = self.DetOuts[i].read()
        r1 = r & K28_1_DET_STABLE1
        res.append(r1 != 0)
        test[i].append(r1 != 0)
      log.debug("{} {}".format(data_del, res))
      data_del += 1
    # Find the biggest area filled with ones
    # Now calculate optimum delay for each channel
    data_dels = [1, 2, 3, 4, 5]
    for i in range(0, 5):
      if link_break_user & (1 << i):
        data_dels[i] = self.find_center(test[i], 64)
        self.InpDelays[i].write(data_dels[i])
        log.debug("{} {}".format(i, data_dels[i]))
    # build a nice window eye graph to display
    windows = []
    for window in test:
      windows.append(['_' if item else 'X' for item in window])
    [w.insert(0, '|') for w in windows]
    [w.append('|') for w in windows]
    windows = [''.join(w) for w in windows]
    log.info("Data delays = {}".format(data_dels))
    log.info("Eye window of the data signals:")
    for w in windows:
      log.info(w)
    # Now verify correct operation:
    time.sleep(0.0001)
    for i in range(0, 5):
      self.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
    time.sleep(0.0001)
    for i in range(0, 5):
      self.DetClears[i].write(0)
    time.sleep(0.002)
    test = []
    for i in range(0, 5):
      r = self.DetOuts[i].read()
      r1 = r & K28_1_DET_STABLE1
      test.append(r1 != 0)
    log.debug("k28_1 test result: {}".format(test))
    # Send EOS
    self.EncMode.write(MODE_EOS)
    time.sleep(0.0001)
    # Now verify correct operation:
    for i in range(0, 5):
      self.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
    time.sleep(0.0001)
    for i in range(0, 5):
      self.DetClears[i].write(0)
    time.sleep(0.0001)
    all_eos = True
    test = []
    for i in range(0, 5):
      r = self.DetOuts[i].read()
      r1 = (r & EOS_DET_STABLE1) or (link_break_user & (1 << i) == 0)
      if r1 == 0:
        all_eos = False
      test.append(r1 != 0)
    log.debug("eos test result: {}".format(test))
    if all_eos is False:
      raise Exception("Not received EOS")
    # Write found configuration:
    cfg = {'cdel': clk_del, 'ddel': data_dels}
    filename = "dels_{:04x}_{:d}.cfg".format(self.afck_id, self.iface)
    fcfg = open(filename, "w")
    pickle.dump(cfg, fcfg)
    fcfg.close()

  def fast_sync(self, link_break_user):
    filename = "dels_{:04x}_{:d}.cfg".format(self.afck_id, self.iface)
    fcfg = open(filename, "r")
    cfg = pickle.load(fcfg)
    fcfg.close()
    clk_del = cfg['cdel']
    data_dels = cfg['ddel']
    log.info("Clock delay = {}".format(clk_del))
    log.info("Data delays = {}".format(data_dels))
    self.com.clkout_sel_output(self.iface)
    self.com.clkout_set_delay(clk_del)
    self.com.clkout_set_delay(clk_del)
    # Wait until Clock delay gets locked
    for i in range(0, 5):
      self.InpDelays[i].write(data_dels[i])
    # Wait a little and clear glitch detectors
    while self.DDelLock.read() != 0x1f:
      pass
    # Send EOS
    self.EncMode.write(MODE_EOS)
    time.sleep(0.000001)
    # Now verify correct operation:
    for i in range(0, 5):
      self.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
    time.sleep(0.000001)
    for i in range(0, 5):
      self.DetClears[i].write(0)
    time.sleep(0.000001)
    all_eos = True
    test = []
    for i in range(0, 5):
      r = self.DetOuts[i].read()
      r1 = (r & EOS_DET_STABLE1) or (link_break_user & (1 << i) == 0)
      if r1 == 0:
        all_eos = False
      test.append(r1 != 0)
    log.debug("eos test result: {}".format(test))
    if all_eos is False:
      raise Exception("Not received EOS")




