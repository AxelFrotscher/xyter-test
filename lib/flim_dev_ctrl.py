#!/usr/bin/python
import logging as log


class flim_dev_ctrl:

  def __init__(self, hw, dev):
    self.hw = hw
    self.dev = dev

  def read_public_dev_info(self):
    log.debug("\nThe public device information is:")
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
    val = self.hw.getNode(self.dev + ".OTH_SLV_NUM").read()
    self.hw.dispatch()
    log.debug("Other slave number:  %d", val)
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
      log.debug("register write/read test passed!")
    else:
      log.warning("register write/read test failed!")
      log.warning("Write: 0x%08X  Read: 0x%08X", 0xa55a5aa5, val)
    return

  def get_current_ms_index_h(self, link = 0):
    index_h = self.hw.getNode(self.dev + ".CURRENT_MS%d_H" % link).read()
    self.hw.dispatch()
    return index_h

  def get_current_ms_index_l(self, link = 0):
    index_l = self.hw.getNode(self.dev + ".CURRENT_MS%d_L" % link).read()
    self.hw.dispatch()
    return index_l

  def set_ms_index_threshold(self, start_h, start_l, stop_h, stop_l):
    self.hw.getNode(self.dev + ".START_MS_L").write(start_l)
    self.hw.getNode(self.dev + ".START_MS_H").write(start_h)
    self.hw.getNode(self.dev + ".STOP_MS_L").write(stop_l)
    self.hw.getNode(self.dev + ".STOP_MS_H").write(stop_h)
    self.hw.getNode(self.dev + ".SET_THRESHOLD").write(1)
    self.hw.getNode(self.dev + ".SET_THRESHOLD").write(0)
    self.hw.dispatch()
    log.info("Set microslice index window to: 0x%08X%08X ~ 0x%08X%08X",
             start_h, start_l, stop_h, stop_l)
    return

# gDPB and nDPB: clk_period=6.25
# pGen_DPB: clk_period=25
  def set_ms_period(self, period_ns, clk_period):
    period_cnt = int(float(period_ns) / float(clk_period))
    self.hw.getNode(self.dev + ".MS_PERIOD_CNT").write(period_cnt)
    self.hw.getNode(self.dev + ".MS_PERIOD_NS").write(period_ns)
    self.hw.getNode(self.dev + ".SET_MS_PERIOD").write(1)
    self.hw.getNode(self.dev + ".SET_MS_PERIOD").write(0)
    self.hw.dispatch()
    log.info("Set MS period to: %d ns/%d cycles", period_ns, period_cnt)
    return

  def start_stop_ms_count(self, val):
    self.hw.getNode(self.dev + ".STOP_MS_CNT").write(val)
    self.hw.dispatch()
    return

  def get_ms_count_status(self):
    val = self.hw.getNode(self.dev + ".MS_CNT_STOPPED").read()
    self.hw.dispatch()
    return val

  def set_gtx_params(self, link, precursor=0xa, postcursor=0x6, maincursor=0x0, diffctrl=0xC):
    """Set transceiver TX driver parameters. Useful when working with CRC errors and SI issues.
    Default values were determined by IBERT tests.
    Maincursor has any effect only when GTX is configured to accept it (default - no)
    """
    assert 0 <= link <= 3
    assert 0 <= precursor <= 0x1F
    assert 0 <= postcursor <= 0x1F
    assert 0 <= diffctrl <= 0xF

    tx_dev = self.dev + ".tx[{:d}]".format(link)
    self.hw.getNode(tx_dev + ".precursor").write(precursor)
    self.hw.getNode(tx_dev + ".postcursor").write(postcursor)
    self.hw.getNode(tx_dev + ".maincursor").write(maincursor)
    self.hw.getNode(tx_dev + ".diffctrl").write(diffctrl)
    self.hw.dispatch()
