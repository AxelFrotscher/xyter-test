import time
import logging as log
from sca_defs import *


FEB_MODE_5xFEB1 = 0x0
FEB_MODE_1xFEB5 = 0x1
FEB_MODE_gDPB = 0x2
FEB_MODE_MUCH = 0x3

logger = log.getLogger(__name__)


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


class crob_com_ctrl(object):
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
        self.tdreg_val = ipbus(hw, dev + ".TD_REG_VAL")
        self.tdreg_tdval = ipbus(hw, dev + ".TD_REG_TDVAL")
        self.tdreg_tdfnum = ipbus(hw, dev + ".TD_REG_TDFNUM")
        self.tdreg_stat = ipbus(hw, dev + ".TD_REG_SAT")
        self.crob_warnings = ipbus(hw, dev + ".CROB_WARNINGS")

    def read_public_dev_info(self):
        log.debug("CROB public device information is:")
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
        log.debug("CROB slaves:         %d", val)
        val = self.hw.getNode(self.dev + ".SLV_MASK").read()
        self.hw.dispatch()
        log.debug("Other slave type:    %s", hex(val))

    def dev_rw_reg_test(self):
        self.hw.getNode(self.dev + ".DEV_TEST_W").write(0xa55a5aa5)
        self.hw.dispatch()
        val = self.hw.getNode(self.dev + ".DEV_TEST_R").read()
        self.hw.dispatch()
        if val == 0xa55a5aa5:
            log.debug("Device register write/read test passed!")
        else:
            log.debug("Device register write/read test failed!")

    def interface_count(self):
        val = self.hw.getNode(self.dev + ".IFACE_SLV_NUM").read()
        self.hw.dispatch()
        return val

    def reset_fifo_all(self):
        log.debug("Reset all FIFOs")
        self.hw.getNode(self.dev + ".RST_FIFO").write(1)
        self.hw.getNode(self.dev + ".RST_FIFO").write(0)
        self.hw.dispatch()

    def reset_data_processing(self, val):
        self.hw.getNode(self.dev + ".DAT_PROC_RES").write(val)
        self.hw.dispatch()

    def set_dest(self, data_dest):
        """
        data_dest: 0: data to flim fifo 1: data to ipbus fifo
        """
        if data_dest == 0:
            log.debug("Work mode: Data will be transfered to FLIM")
        else:
            log.debug("Work mode: Data will be transfered to IPBus data FIFO")
        self.hw.getNode(self.dev + ".DATA_DEST").write(data_dest)
        self.hw.dispatch()

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

    def gbt_tx_reset(self):
        self.hw.getNode(self.dev + ".GBT_TX_RESET").write(0x1)
        self.hw.getNode(self.dev + ".GBT_TX_RESET").write(0x0)
        self.hw.dispatch()

    def gbt_rx_reset(self):
        self.hw.getNode(self.dev + ".GBT_RX_RESET").write(0x1)
        self.hw.getNode(self.dev + ".GBT_RX_RESET").write(0x0)
        self.hw.dispatch()

    def check_crob_warnings(self, crob):
        wrn = self.crob_warnings.read()
        if wrn & (1<<crob):
            return True
        else:
            return False

    def print_crob_warnings(self):
        wrn = self.crob_warnings.read()
        if wrn != 0:
            crobs = []
            for i in xrange(32):
                if wrn & (1<<i):
                    crobs.append(i)
            log.info("Found warnings on CROBs: "+str(crobs))
        return crobs

    def set_raw_fifo_elink(self, elinkSel):
        self.hw.getNode(self.dev + ".RAW_FIFO_ELINK_SEL").write( elinkSel )
        self.hw.dispatch()

    def reset_raw_fifo(self):
        self.hw.getNode(self.dev + ".RAW_FIFO_RESET").write( 1 )
        self.hw.dispatch()
        self.hw.getNode(self.dev + ".RAW_FIFO_RESET").write( 0 )
        self.hw.dispatch()

    def read_ipb_raw_data_fifo_len(self):
        read_len = self.hw.getNode(self.dev + ".RAW_DATA_FIFO.RFIFO_LEN").read()
        self.hw.dispatch()
        return read_len

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

class crob_iface_ctrl(object):
    """
    Class for controlling a single CROB interface.
    CROB interface is connected to COMMON module; many STSXYTER classes may be
    connected to this class and use it for communication
    """

    def __init__(self, common, crob_id):
        self.com = common
        self.hw = common.hw
        self.dev = common.dev + ".CROB" + str(crob_id)
        self.id = crob_id
        self.master_gbtx_addr = 0x1
        self.ec_transid = 0x1
        self.GBTX_MASTER = 0
        self.GBTX_SLAVE_1 = 1
        self.GBTX_SLAVE_2 = 2
        self.sca_i2c_speed = [SCA_I2C_SPEED_100] * 16
        self.reg_version = ipbus(self.hw, self.dev+".crob_addr_ver")

        self.ul_warnings = []
        for i in xrange(42):
            self.ul_warnings.append( ipbus(self.hw, self.dev+".ul.warnings[%d]"%i))

    def feb_mode(self, mode):
        self.hw.getNode(self.dev + ".sys_ctrl.febs_mode").write(mode)
        self.hw.dispatch()

    def ulink_enable(self, val):
        self.hw.getNode(self.dev + ".link_mask[0]").write(val & 0xFFFFFFFF)
        self.hw.getNode(self.dev + ".link_mask[1]").write(val >> 32)
        self.hw.dispatch()
        return

    def ulink_mask_read(self):
        valLsb = self.hw.getNode(self.dev + ".link_mask[0]").read()
        valMsb = self.hw.getNode(self.dev + ".link_mask[1]").read()
        self.hw.dispatch()
        val = (valMsb << 32) + valLsb
        return val

    def ulink_enable_check(self, val):
        self.ulink_enable( val )
        ret_val = self.ulink_mask_read()
        if ret_val == val :
          log.info("eLink mask readback ok: 0x%016x", ret_val )
        else:
          log.info("Bad eLink mask readback: 0x%016x VS 0x%016x ", ret_val, val )
        return

    def print_elink_warnings(self):
        sx_throttling_bit = 0
        sx_sync_alert_bit = 1
        sx_alert_bit      = 2
        missing_sync_bit  = 3
        dpb_bitslip_bit   = 4

        elinks = []
        mask = self.ulink_mask_read()
        for i in xrange(42):
          if mask & (1<<i):
            wrn = self.ul_warnings[ i ].read()
            if wrn != 0:
              log.info("eLink %2u: 0x%08x", i, wrn )
              elinks.append(i)
        log.info("Found warnings on eLinks: "+str(elinks))
        return elinks

    def gbt_sc_reset(self):
        log.debug("GBT-SC controller reset")
        self.hw.getNode(self.dev + ".ic.ctrl.reset").write(0x1)
        self.hw.getNode(self.dev + ".ic.ctrl.reset").write(0x0)
        self.hw.dispatch()

    def ic_write(self, addr, data):
        assert isinstance(data, (list, tuple))
        #log.debug("GBT IC write addr = {:d} data = {:#x}".format(addr, *data))
        # GBT-SC shouldn't get stuck here permanently. In fact it should be almost
        # always ready if we're controlling it via IPbus
        while True:
            ready = self.hw.getNode(self.dev + ".ic.status.ready").read()
            self.hw.dispatch()
            if ready:
                break

        self.hw.getNode(self.dev + ".ic.ctrl.addr").write(self.master_gbtx_addr)
        self.hw.getNode(self.dev + ".ic.tx_rega_nbtr.reg_addr").write(addr)
        for val in data:
            self.hw.getNode(self.dev + ".ic.tx_data").write(val)
        self.hw.getNode(self.dev + ".ic.ctrl.start_write").write(0x1)
        self.hw.getNode(self.dev + ".ic.ctrl.start_write").write(0x0)
        self.hw.dispatch()

    def ic_read(self, addr, size):
        #log.debug("GBT IC read addr = {0:d} size = {1:d}".format(addr, size))
        # GBT-SC shouldn't get stuck here permanently. In fact it should be almost
        # always ready if we're controlling it via IPbus
        while True:
            ready = self.hw.getNode(self.dev + ".ic.status.ready").read()
            self.hw.dispatch()
            if ready:
                break

        self.hw.getNode(self.dev + ".ic.ctrl.addr").write(self.master_gbtx_addr)
        self.hw.getNode(self.dev + ".ic.tx_rega_nbtr.reg_addr").write(addr)
        self.hw.getNode(self.dev + ".ic.tx_rega_nbtr.bytes_to_read").write(size)
        self.hw.getNode(self.dev + ".ic.ctrl.start_read").write(0x1)
        self.hw.getNode(self.dev + ".ic.ctrl.start_read").write(0x0)
        self.hw.dispatch()
        """ Wait until GBT response arrives and read data
            NOTE: theoretically we should check 'empty' status before reading each
            byte. But due to IPbus latency for each read cycle I'm pretty sure
            GBT data will arrive faster than we can read it via IPbus - remember
            that we are dispatching read() byte after byte """
        while True:
            empty = self.hw.getNode(self.dev + ".ic.status.empty").read()
            self.hw.dispatch()
            if empty == 0:
                break
        # First read is a dummy, it will send a pulse to fetch data from response FIFO to register
        self.hw.getNode(self.dev + ".ic.rx_data").read()
        self.hw.dispatch()
        data = []
        for i in range(0, size):
            val = self.hw.getNode(self.dev + ".ic.rx_data").read()
            self.hw.dispatch()
            data.append(val)

        #log.debug("GBT IC read resp = {:#x} ".format(*data))
        return data

    def ec_connect(self):
        log.debug("Connecting to SCA")
        self.hw.getNode(self.dev + ".ec.ctrl.start_connect").write(0x1)
        self.hw.getNode(self.dev + ".ec.ctrl.start_connect").write(0x0)
        self.hw.dispatch()

    def ec_reset(self):
        log.debug("Resetting SCA")
        self.hw.getNode(self.dev + ".ec.ctrl.start_reset").write(0x1)
        self.hw.getNode(self.dev + ".ec.ctrl.start_reset").write(0x0)
        self.hw.dispatch()
        self.ec_transid = 1

    def ec_send_cmd(self, chan, cmd, data):
        #log.debug("GBT EC send cmd chan = {0:#x} cmd = {1:#x}, data = {2:#x}".format(chan, cmd, data))
        self.hw.getNode(self.dev + ".ec.tx_cmd.chan").write(chan)
        self.hw.getNode(self.dev + ".ec.tx_cmd.command").write(cmd)
        self.hw.getNode(self.dev + ".ec.tx_cmd.trans_id").write(self.ec_transid)
        self.ec_transid += 1
        if self.ec_transid == 0xff:  # 0x0 and 0xFF are reserved IDs
            self.ec_transid = 1
        # there seems to be a bug in GBT-SCA, only single word can be sent
        self.hw.getNode(self.dev + ".ec.tx_data").write(data)
        self.hw.getNode(self.dev + ".ec.ctrl.start_cmd").write(0x1)
        self.hw.getNode(self.dev + ".ec.ctrl.start_cmd").write(0x0)
        self.hw.dispatch()
        while True:
            status = self.hw.getNode(self.dev + ".ec.status").read()
            self.hw.dispatch()
            if status & 0x1:  # reply received
                if status & 0xFF0000:  # there's an error
                    log.warn("SCA reply with error received, status = {:#x}".format(status))
                break

    def ec_read_data(self):
        val = self.hw.getNode(self.dev + ".ec.rx_data").read()
        self.hw.dispatch()
        #log.debug("GBT EC read data = {:#x}".format(val))
        return val

    def sca_configure(self):
        log.info("Configuring SCA for CROB operation")
        self.ec_reset()
        # enable channels
        cmd = SCA_CTRL_CRB_ENGPIO | SCA_CTRL_CRB_ENI2C0 | SCA_CTRL_CRB_ENI2C1 | \
            SCA_CTRL_CRB_ENI2C2 | SCA_CTRL_CRB_ENI2C3 | SCA_CTRL_CRB_ENI2C4
        self.ec_send_cmd(SCA_CH_CTRL, SCA_CTRL_W_CRB, cmd)
        cmd = SCA_CTRL_CRD_ENJTAG | SCA_CTRL_CRD_ENADC | SCA_CTRL_CRD_ENDAC
        self.ec_send_cmd(SCA_CH_CTRL, SCA_CTRL_W_CRD, cmd)
        # configure GPIO
        gpio = (0x1 << 31) | (0x1 << 30) | (0x1 << 29)  # LEDs
        gpio |= (0x1 << 27)  # GBTx master IC sel (kynar wire workaround in WUT setup)
        gpio |= (0x1 << 19) | (0x1 << 18)  # GBT slaves resetB pins
        self.sca_gpio_set_dir(gpio)
        gpio = (0x1 << 31) | (0x1 << 19) | (0x1 << 18)
        self.sca_gpio_set_output(gpio)
        # ADC
        temp_mon_pads = (0x1 << 5) | (0x1 << 6)
        self.ec_send_cmd(SCA_CH_ADC, SCA_ADC_W_CURR, temp_mon_pads)
        # I2C
        i2c_chans = [SCA_CH_I2C0, SCA_CH_I2C1, SCA_CH_I2C2, SCA_CH_I2C3, SCA_CH_I2C4]
        for chan in i2c_chans:
            self.sca_i2c_set_speed(chan, SCA_I2C_SPEED_100)

    def sca_get_id(self):
        self.ec_send_cmd(SCA_CH_ID, SCA_CTRL_R_ID_V2, SCA_CTRL_DATA_R_ID)
        return self.ec_read_data()

    def sca_gpio_set_dir(self, dir_mask):
        """
        Set direction of GPIO pins.
        dir_mask - Bit mask of pin directions. '0' - input, '1' - output
        """
        self.ec_send_cmd(SCA_CH_GPIO, SCA_GPIO_W_DIRECTION, dir_mask)

    def sca_gpio_set_output(self, out_mask):
        self.ec_send_cmd(SCA_CH_GPIO, SCA_GPIO_W_DATAOUT, out_mask)

    def sca_gpio_get_output(self):
        self.ec_send_cmd(SCA_CH_GPIO, SCA_GPIO_R_DATAOUT, 0)
        return self.ec_read_data()

    def sca_gpio_get_input(self):
        self.ec_send_cmd(SCA_CH_GPIO, SCA_GPIO_R_DATAIN, 0)
        return self.ec_read_data()

    def sca_adc_get(self, chan):
        """Return ADC channel value in [V]"""
        self.ec_send_cmd(SCA_CH_ADC, SCA_ADC_W_MUX, chan)
        self.ec_send_cmd(SCA_CH_ADC, SCA_ADC_GO, 0x1)
        val = self.ec_read_data()
        return int(val)/4096.0

    def sca_dac_set(self, chan, val):
        assert 0.0 <= val <= 1.0
        dac_cmd = (SCA_DAC_W_A, SCA_DAC_W_B, SCA_DAC_W_C, SCA_DAC_W_D)
        if chan < 0 or chan > 3:
            log.warn("Incorrect SCA DAC channel selected")
            return

        self.ec_send_cmd(SCA_CH_DAC, dac_cmd[chan], int(val*256))

    def sca_i2c_set_speed(self, chan, speed):
        """
        Set one of 4 allowed I2C speed modes.
        speed - hex value as defined in GBT-SCA manual
        """
        # cache current speed so we don't have to query it every time
        self.sca_i2c_speed[chan] = speed
        # TODO: stop clearing NBYTE and SCLMODE fields
        self.ec_send_cmd(chan, SCA_I2C_W_CTRL, speed << 24)

    @staticmethod
    def __parse_sca_i2c_status(status):
        """Return 0 on success or positive value on error"""
        if status & (0x1 << 2):
            #log.debug("SCA I2C transaction status SUCCESS")
            pass
        elif status & (0x1 << 3):
            log.warn("SCA I2C transaction LEVERR - SDA pulled to GND")
        elif status & (0x1 << 5):
            log.warn("SCA I2C transaction INVOM - invalid command")
        elif status & (0x1 << 6):
            log.warn("SCA I2C transaction NOACK - no acknowledge from slave")

        return status & 0x68

    def sca_i2c_write(self, chan, addr, data, addr_mode_10b=False):
        assert isinstance(data, (list, tuple))
        if len(data) > 16 or len(data) == 0:
            log.warn("SCA I2C: request to send {0:d} bytes (max = 16)".format(len(data)))
            return

        elif len(data) == 1 and not addr_mode_10b:
            cmd = SCA_I2C_S_7B_W
            cmd_data = (addr << 24) | ((data[0] & 0xFF) << 16)
        elif len(data) == 1 and addr_mode_10b:
            cmd = SCA_I2C_S_10B_W
            cmd_data = (addr << 16) | ((data[0] & 0xFF) << 8)
        elif len(data) > 1 and not addr_mode_10b:
            cmd = SCA_I2C_M_7B_W
            cmd_data = (addr << 24)
        elif len(data) > 1 and addr_mode_10b:
            cmd = SCA_I2C_M_10B_W
            cmd_data = (addr << 16)
        else:
            log.error("SCA I2C: unknown write request, this shouldn't happen")
            return

        #log.debug("SCA I2C write i2c_chan = {:#d} addr = {:#x}, data = {:#x}".format(chan, addr, *data))
        # for multibyte transactions preload write registers with data
        if len(data) > 1:
            data_regs = [0, 0, 0, 0]
            wdata_cmd = [SCA_I2C_W_DATA0, SCA_I2C_W_DATA1, SCA_I2C_W_DATA2, SCA_I2C_W_DATA3]
            """I know this loop looks strange and behaves in non standard way,
            but I don't know of any better way to unpack variable-length data
            into different bitfields of non-constant number of variables.
            """
            for x in range(0, len(data)):
                data_regs[x // 4] |= data[x] << (24 - (x % 4) * 8)
            # now preload the data into registers
            for x in range(0, ((len(data) - 1) // 4) + 1):
                self.ec_send_cmd(chan + 3, wdata_cmd[x], data_regs[x])

        ctrl_reg = (self.sca_i2c_speed[chan] << 24) | (len(data) << 26)
        self.ec_send_cmd(chan + 3, SCA_I2C_W_CTRL, ctrl_reg)
        # start the I2C transaction
        self.ec_send_cmd(chan + 3, cmd, cmd_data)
        status = self.ec_read_data()
        self.__parse_sca_i2c_status(status >> 24)

    def sca_i2c_read(self, chan, addr, size, addr_mode_10b=False):
        if size > 16 or size == 0:
            log.warn("SCA I2C: request to read {:d} bytes (max = 16)".format(size))
            return

        if size == 1 and not addr_mode_10b:
            cmd = SCA_I2C_S_7B_R
            cmd_data = (addr << 24)
        elif size == 1 and addr_mode_10b:
            cmd = SCA_I2C_S_10B_R
            cmd_data = (addr << 16)
        elif size > 1 and not addr_mode_10b:
            cmd = SCA_I2C_M_7B_R
            cmd_data = (addr << 24)
        elif size > 1 and addr_mode_10b:
            cmd = SCA_I2C_M_10B_R
            cmd_data = (addr << 16)
        else:
            log.error("SCA I2C: unknown read request, this shouldn't happen")
            return

        #log.debug("SCA I2C read i2c_chan = {:#d} addr = {:#x}, size = {:#d}".format(chan, addr, size))
        if size > 1:
            ctrl_reg = (self.sca_i2c_speed[chan] << 24) | (size << 26)
            self.ec_send_cmd(chan + 3, SCA_I2C_W_CTRL, ctrl_reg)
        # start the I2C transaction
        self.ec_send_cmd(chan + 3, cmd, cmd_data)
        status = self.ec_read_data()
        # check if error occured
        if self.__parse_sca_i2c_status(status >> 24):
            return [0]

        if size == 1:
            return [(status & 0xFF0000) >> 16]
        else:
            data = []
            rdata_cmd = [SCA_I2C_R_DATA0, SCA_I2C_R_DATA1, SCA_I2C_R_DATA2, SCA_I2C_R_DATA3]
            for x in range(0, ((size - 1) // 4) + 1):
                self.ec_send_cmd(chan + 3, rdata_cmd[x], 0x0)
                reg = self.ec_read_data()
                # extract bytes and put them on list
                for i in range(0, 4):
                    byte = reg & (0xFF << (24 - i*8))
                    data.append(byte >> (24 - i*8))
            return data

    def gbtx_write_reg_array(self, gbtx_id, addr, data):
        assert self.GBTX_MASTER <= gbtx_id <= self.GBTX_SLAVE_2
        assert isinstance(data, (list, tuple))

        if gbtx_id == self.GBTX_MASTER:
            self.ic_write(addr, data)
            return
        elif gbtx_id == self.GBTX_SLAVE_1:
            i2c_addr = 0x2
        elif gbtx_id == self.GBTX_SLAVE_2:
            i2c_addr = 0x4

        i2c_data = [addr & 0xFF, (addr >> 8) & 0xFF] + data
        self.sca_i2c_write(gbtx_id - 1, i2c_addr, i2c_data)

    def gbtx_write_reg(self, gbtx_id, addr, val):
        self.gbtx_write_reg_array(gbtx_id, addr, [val])

    def gbtx_read_reg_array(self, gbtx_id, addr, size):
        assert self.GBTX_MASTER <= gbtx_id <= self.GBTX_SLAVE_2

        if gbtx_id == self.GBTX_MASTER:
            data = self.ic_read(addr, size)
            return data
        elif gbtx_id == self.GBTX_SLAVE_1:
            i2c_addr = 0x2
        elif gbtx_id == self.GBTX_SLAVE_2:
            i2c_addr = 0x4

        i2c_cmd = [addr & 0xFF, (addr >> 8) & 0xFF]
        self.sca_i2c_write(gbtx_id - 1, i2c_addr, i2c_cmd)
        # block read doesn't work for GBTx, but single access autoincrements register address
        data = []
        for _ in range(size):
            data.append(self.sca_i2c_read(gbtx_id - 1, i2c_addr, 1)[0])
        return data

    def gbtx_read_reg(self, gbtx_id, addr):
        data = self.gbtx_read_reg_array(gbtx_id, addr, 1)
        return data[0]

    def gbtx_reset(self, gbtx_id):
        if gbtx_id == self.GBTX_SLAVE_1:
            pin = 19
        elif gbtx_id == self.GBTX_SLAVE_2:
            pin = 18
        else:
            log.error("Unknown or wrong GBTx ID")
            return

        log.info("Issuing reset of GBTx id = {:d}".format(gbtx_id))
        gpio = self.sca_gpio_get_input()
        gpio &= ~(0x1 << pin)
        self.sca_gpio_set_output(gpio)
        gpio |= (0x1 << pin)
        self.sca_gpio_set_output(gpio)

    def gbtx_config_readback(self, gbtx_id, path=None):
        """Read full configuration from GBTx and optionally write it to a file.
        Returns register list.
        path - optional readback file
        """
        log.info("Reading back configuration of GBTx (id = {:d})".format(gbtx_id))
        config = [0] * 366
        # use block access to make it faster
        for i in range(0, 22):
            data = self.gbtx_read_reg_array(gbtx_id, i * 16, 16)
            config[i*16:(i+1)*16] = data
        data = self.gbtx_read_reg_array(gbtx_id, 352, 14)
        config[352:] = data

        if path:
            with open(path, 'w') as f:
                for val in config:
                    f.write("{:0>2x}\n".format(val))

        return config

    def gbtx_config_write(self, gbtx_id, path):
        """Read full configuration from file and send it to GBTx.
        Returns config as register array.
        File format must be compatible with TXT files generated by CERN tools
        """
        with open(path, 'r') as f:
            lines = f.readlines()
            config = []
            for line in lines:
                parts = line.split()
                config.append(int(parts[0], 16))

        if len(config) != 366:
            log.error("Config file has {:d} entries, needs to be exactly 366. Aborting".format(len(config)))
            return

        # Without reset GBTx sometimes end up in non-working state
        self.gbtx_reset(gbtx_id)

        log.info("Writing full configuration to GBTx (id = {:d})".format(gbtx_id))
        for i in range(0, 26):
            self.gbtx_write_reg_array(gbtx_id, i * 14, config[i*14:(i+1)*14])
        self.gbtx_write_reg_array(gbtx_id, 364, config[364:])

    def gbtx_config_write_check(self, gbtx_id, path):
        """Read full configuration from file and send it to GBTx.
        Returns config as register array.
        File format must be compatible with TXT files generated by CERN tools
        """
        with open(path, 'r') as f:
            lines = f.readlines()
            config = []
            for line in lines:
                parts = line.split()
                config.append(int(parts[0], 16))

        if len(config) != 366:
            log.error("Config file has {:d} entries, needs to be exactly 366. Aborting".format(len(config)))
            return

        # Without reset GBTx sometimes end up in non-working state
        self.gbtx_reset(gbtx_id)

        log.info("Writing full configuration to GBTx (id = {:d})".format(gbtx_id))
        for i in range(0, 26):
            self.gbtx_write_reg_array(gbtx_id, i * 14, config[i*14:(i+1)*14])
        self.gbtx_write_reg_array(gbtx_id, 364, config[364:])

        config_read = self.gbtx_config_readback( gbtx_id )
        for regIdx in range( 0, len( config ) ):
            if config[regIdx] != config_read[ regIdx ]:
                log.info("Readback error for GBTx {:d} register {:3d}: read {:8x} vs {:8x} written".format(
                                gbtx_id, regIdx, config_read[ regIdx ], config[regIdx] ) )

    def gbtx_config_patch_write(self, gbtx_id, path):
        """Read partial configuration from file and send it to GBTx.
        Returns patch config as a tuple array with tuple pairs in form:
        (register index, register value).
        Code was backported from Joerg Lenhert's scripts
        """
        log.info("Writing partial patch configuration to GBTx (id = {:d})".format(gbtx_id))
        with open(path, 'r') as f:
            lines = f.readlines()
            patch_config = []
            for line in lines:
                parts = line.split()
                reg = int(parts[0])
                val = int(parts[1], 16)
                patch_config.append((reg, val))

        for pair in patch_config:
            self.gbtx_write_reg(gbtx_id, pair[0], pair[1])

    def gbtx_epll_init(self, gbtx_id, phase_override=False):
        """Initialise elink PLL setting. ePLL is used only in 160 and 320 MHz modes
        phase_override - override internal phase settings which are factory-fused
        """
        # ePLL should use only 160 MHz reference
        self.gbtx_write_reg(gbtx_id, 242, 0x3f)
        self.gbtx_write_reg(gbtx_id, 243, 0x3f)
        # charge pump current (not described in the docs)
        for i in range(3):
            self.gbtx_write_reg(gbtx_id, 299 + i, 0x2a)
        for i in range(3):
            self.gbtx_write_reg(gbtx_id, 310 + i, 0x2a)
        # enable ePLL
        # TODO: does it have to be enabled here, or can I move it to gbtx_elink_init() ?
        for i in range(3):
            self.gbtx_write_reg(gbtx_id, 293 + i, 0xff)
        for i in range(3):
            self.gbtx_write_reg(gbtx_id, 304 + i, 0xff)
        if phase_override:
            for i in range(3):
                self.gbtx_write_reg(gbtx_id, 296 + i, 0x40)
            for i in range(3):
                self.gbtx_write_reg(gbtx_id, 307 + i, 0x40)
        else:
            for i in range(3):
                reg = self.gbtx_read_reg(gbtx_id, 296 + i)
                self.gbtx_write_reg(gbtx_id, 296 + i, 0x40 | reg)
            for i in range(3):
                reg = self.gbtx_read_reg(gbtx_id, 307 + i)
                self.gbtx_write_reg(gbtx_id, 307 + i, 0x40 | reg)

        # reset ePLL
        self.gbtx_write_reg(gbtx_id, 303, 0x77)
        self.gbtx_write_reg(gbtx_id, 303, 0x0)

    def gbtx_ec_init(self, gbtx_id, drive=0x8):
        """Initialise EC channel
        drive - output driver current strength, lower value means higher strength
        """
        assert 0 <= drive <= 15
        # assert EC reset
        self.gbtx_write_reg(gbtx_id, 251, 0x7)
        # 40 MHz clock (register shared with elink channel)
        reg = self.gbtx_read_reg(gbtx_id, 257)
        reg &= ~(0x7 << 4)
        self.gbtx_write_reg(gbtx_id, 257, reg)
        # 80 Mbit mode (register shared with elink channel)
        reg = self.gbtx_read_reg(gbtx_id, 254)
        reg |= 0x7 << 4
        self.gbtx_write_reg(gbtx_id, 254, reg)
        # phase aligner static phase mode
        self.gbtx_write_reg(gbtx_id, 62, 0x0)
        # phase aligner DLL charge pump current
        self.gbtx_write_reg(gbtx_id, 231, 0xbb)
        self.gbtx_write_reg(gbtx_id, 232, 0x7b)  # + assert DLL reset
        # disable phase training
        self.gbtx_write_reg(gbtx_id, 245, 0x0)
        # input phase select
        self.gbtx_write_reg(gbtx_id, 233, 0x7a)  # + coarse lock detection
        self.gbtx_write_reg(gbtx_id, 237, 0xa)
        self.gbtx_write_reg(gbtx_id, 241, 0xa)
        # enable input termination + set drive strength
        self.gbtx_write_reg(gbtx_id, 273, 0x20 | drive)
        # enable EC channel
        self.gbtx_write_reg(gbtx_id, 248, 0x7)
        # deassert DLL & channel reset
        self.gbtx_write_reg(gbtx_id, 232, 0xb)
        self.gbtx_write_reg(gbtx_id, 251, 0x0)

    def gbtx_elink_clock_init(self, gbtx_id, group, clocks, freq):
        """Configure and enable elink clock outputs within group.
        Faster clocks require ePLL to be enabled.
        group - elink group index (refer to GBTx manual)
        clocks - list of clock indexes within a group (available clocks depend on chosen elink RX rate)
        freq - one of {40, 80, 160, 320} [MHz]
        """
        allowed_freq = (0, 80, 160, 320)
        assert 0 <= group <= 4
        assert isinstance(clocks, (list, tuple))
        assert freq in allowed_freq
        frq_mode = allowed_freq.index(freq)
        reg_offset = group * 3
        # set clock frequency
        # this register is triplicated under different addresses
        reg = self.gbtx_read_reg(gbtx_id, 254 + reg_offset)
        reg &= ~(0x3 << 2)
        for addr in [254 + reg_offset, 332 + reg_offset, 347 + reg_offset]:
            self.gbtx_write_reg(gbtx_id, addr, reg | (frq_mode << 2))
        # enable clock output
        reg = 0
        for clock in clocks:
            reg |= (0x1 << clock)
        for addr in [255 + reg_offset, 333 + reg_offset, 348 + reg_offset]:
            self.gbtx_write_reg(gbtx_id, addr, reg)

    def gbtx_elink_output_init(self, gbtx_id, group, outputs, rate, drive=0x8):
        """Configure and enable elink outputs within group.
        Faster rates require ePLL-RX to be enabled
        group - elink group index (refer to GBTx manual)
        outputs - list of elink outputs within a group (available outputs depend on chosen elink rate)
        rate - one of {0, 80, 160, 320} [Mbit/s]
        drive - output driver current strength, lower value means higher current
        """
        allowed_rate = (0, 80, 160, 320)
        assert 0 <= group <= 4
        assert isinstance(outputs, (list, tuple))
        assert rate in allowed_rate
        rate_mode = allowed_rate.index(rate)
        reg_offset = group * 3
        # set output rate
        # this register is triplicated under different addresses
        reg = self.gbtx_read_reg(gbtx_id, 254 + reg_offset)
        reg &= ~0x3
        for addr in [254 + reg_offset, 332 + reg_offset, 347 + reg_offset]:
            self.gbtx_write_reg(gbtx_id, addr, reg | rate_mode)
        # set output strength
        reg = self.gbtx_read_reg(gbtx_id, 327 + group // 2)
        reg &= ~(0xF << ((group % 2) * 4))
        self.gbtx_write_reg(gbtx_id, 327 + group // 2, reg | (drive << ((group % 2) * 4)))
        # enable outputs
        reg = 0
        for output in outputs:
            reg |= (0x1 << output)
        for addr in [256 + reg_offset, 334 + reg_offset, 349 + reg_offset]:
            self.gbtx_write_reg(gbtx_id, addr, reg)

    def gbtx_elink_input_init(self, gbtx_id, group, inputs, rate, term=True):
        """Configure and enable elink inputs within group.
        Faster rates require ePLL-TX to be enabled.
        This function will reset
        group - elink group index (refer to GBTx manual)
        inputs - list of elink inputs within a group (available inputs depend on chosen elink rate)
        rate - one of {0, 80, 160, 320} [Mbit/s]
        term - enable input termination
        phase - input phase shift
        """
        allowed_rate = (0, 80, 160, 320)
        assert 0 <= group <= 6
        assert isinstance(inputs, (list, tuple))
        assert rate in allowed_rate
        rate_mode = allowed_rate.index(rate)
        reg_offset = group * 24
        # phase aligner static phase mode
        self.gbtx_write_reg(gbtx_id, 62, 0x0)
        # set DLL parameters for elink group
        reg = self.gbtx_read_reg(gbtx_id, 233)
        self.gbtx_write_reg(gbtx_id, 233, reg | 0x70)  # coarse lock detect mode
        self.gbtx_write_reg(gbtx_id, 64 + reg_offset, 0xbb)  # DLL charge pump current AB
        self.gbtx_write_reg(gbtx_id, 65 + reg_offset, 0xb)  # DLL charge pump current C
        # set data rate
        self.gbtx_write_reg(gbtx_id, 63 + reg_offset, rate_mode | (rate_mode << 2) | (rate_mode << 4))  # ABC
        # enable inputs and termination
        reg = 0
        for input in inputs:
            reg |= (0x1 << input)
        # fix for bug in GBTx silicon (not mentioned in manual): for widebus mode and 160/320 rate
        # the dIO 1/5 channels are swapped and controlled by dIO 0/4 registers
        # except for termination settings
        if rate == 80 or 0 <= group <= 4:
            reg_fixed = reg
        else:
            reg_fixed = reg >> 1

        for i in range(3):
            self.gbtx_write_reg(gbtx_id, 81 + reg_offset + i, reg_fixed)  # ABC
        if term:
            self.gbtx_write_reg(gbtx_id, 320 + group, reg)
        else :
            self.gbtx_write_reg(gbtx_id, 320 + group, 0)
        # reset DLL (register shared with DLL CP current C)
        self.gbtx_write_reg(gbtx_id, 65 + reg_offset, 0x7b)
        self.gbtx_write_reg(gbtx_id, 65 + reg_offset, 0x0b)
        # reset elink channel
        for i in range(3):
            self.gbtx_write_reg(gbtx_id, 84 + reg_offset + i, reg_fixed)  # ABC
        for i in range(3):
            self.gbtx_write_reg(gbtx_id, 84 + reg_offset + i, 0x0)  # ABC

    def gbtx_elink_phase_set(self, gbtx_id, elink, phase):
        """Set static phase of given input e-link.
        elink - input e-link number as numbered on GBTx pins. DIN pins are in range
        <0; 39>; DIO pins are in range <40; 55>
        phase - required phase in range <0; 15>
        """
        assert 0 <= elink <= 55
        assert 0 <= phase <= 15
        # fortunately mapping of e=link to group number is linear
        group = elink // 8
        base_reg_map = {0: 66, 1: 90, 2: 114, 3: 138, 4: 162, 5: 186, 6: 210}
        offset = 3 - (elink % 8) // 2
        reg_addr = base_reg_map[group] + offset
        # Maybe we should read all ABC registers, but what should I do if they differ?
        pa_reg = self.gbtx_read_reg(gbtx_id, reg_addr)
        # modify relevant bitfiels of A, B, C registers
        # this is already taking into account that for 160/320 modes and groups 5/6 dIO 1/5 is controlled by
        # pacontrol0/pacontrol4
        # TODO: make this work for groups 5/6 in 80 Mb mode
        rega = (pa_reg & ~(0xF << ((elink % 2) * 4))) | (phase << ((elink % 2) * 4))
        # it should be a bit faster to write back full block again, but I don't
        # want to touch channels which I didn't change at all
        self.gbtx_write_reg(gbtx_id, reg_addr, rega)
        self.gbtx_write_reg(gbtx_id, reg_addr + 4, rega)
        self.gbtx_write_reg(gbtx_id, reg_addr + 8, rega)

    def gbtx_clock_pll_init(self, gbtx_id):
        """Initialize PLL registers required for all PACLK
        """
        self.gbtx_write_reg(gbtx_id, 26, 0x7F)  # defaults as suggested by GBTx manual
        reg = self.gbtx_read_reg(gbtx_id, 52)
        self.gbtx_write_reg(gbtx_id, 52, reg | 0x7)
        # reset PLL
        self.gbtx_write_reg(gbtx_id, 25, 0x2)
        self.gbtx_write_reg(gbtx_id, 25, 0x3)

    def gbtx_clock_init(self, gbtx_id, clock, freq, isel=0x3, drive=0x8):
        """Configure and enable given phase-adjustable clock output.
        Clock will stop for a moment while DLL is reset.
        clock - output clock number as numbered on GBTx pins, range <0; 7>
        freq - target frequency, one of {40, 80, 160, 320} [MHz]
        isel - DLL charge pump current, use default
        drive - output drive strength, lower value means higher strength
        """
        allowed_freq = (40, 80, 160, 320)
        assert 0 <= clock <= 7
        assert freq in allowed_freq
        assert 0 <= isel <= 15
        assert 0 <= drive <= 15

        frq_mode = allowed_freq.index(freq)
        # frequency and iSel share the same reg
        self.gbtx_write_reg(gbtx_id, 16 + clock, (frq_mode << 4) | isel)
        drv = self.gbtx_read_reg(gbtx_id, 269 + clock // 2)
        drv = (drv & ~(0xF << ((clock % 2) * 4))) | ((drive & 0xF) << ((clock % 2) * 4))
        self.gbtx_write_reg(gbtx_id, 269 + clock // 2, drv)
        # reset DLL for given clock (some channels may be kept in reset, so let's check state first)
        rst_mask = self.gbtx_read_reg(gbtx_id, 24)
        self.gbtx_write_reg(gbtx_id, 24, rst_mask & ~(0x1 << clock))
        self.gbtx_write_reg(gbtx_id, 24, rst_mask | (0x1 << clock))

    def gbtx_clock_phase_set(self, gbtx_id, clock, phase):
        """Set static phase of given phase-adjustable clock output
        clock - output clock number as numbered on GBTx pins, range <0; 7>
        phase - required phase in range <0; 127>
        """
        assert 0 <= clock <= 7
        assert 0 <= phase <= 127
        # I don't know if it's better to set coarse or fine delay first. One would
        # have to observe GBTx response with a scope to see how smooth phase transition is
        self.gbtx_write_reg(gbtx_id, 8 + clock, phase >> 4)  # coarse delay
        fdl = self.gbtx_read_reg(gbtx_id, 4 + clock // 2)
        fdl = (fdl & ~(0xF << ((clock % 2) * 4))) | ((phase & 0xF) << ((clock % 2) * 4))
        self.gbtx_write_reg(gbtx_id, 4 + clock // 2, fdl)  # fine delay

    def gbtx_watchdog_set(self, gbtx_id, enable):
        """Enable/disable watchdog and timeout
        """
        # register 52 is shared with PACLK PLL enable
        log.info("Reading timeout")
        timeout = self.gbtx_read_reg(gbtx_id, 52)
        log.info("Timeout is %u", timeout)
        if enable:
            self.gbtx_write_reg(gbtx_id, 50, 0x7)
            self.gbtx_write_reg(gbtx_id, 52, timeout | (0x7 << 3))
        else:
            self.gbtx_write_reg(gbtx_id, 50, 0x0)
            self.gbtx_write_reg(gbtx_id, 52, timeout & ~(0x7 << 3))

    def gbld_read(self, gbtx_id):
        """Fetch values of GBLD connected to given GBTx and return register array"""
        self.gbtx_write_reg(gbtx_id, 253, 126)
        self.gbtx_write_reg(gbtx_id, 389, 1)
        time.sleep(0.01)  # transactions take around 2.2 ms
        data = self.gbtx_read_reg_array(gbtx_id, 381, 7)
        log.debug("GBLD Control = \t{:#x}".format(data[0]))
        log.debug("GBLD ModCurr = \t{:#x}".format(data[1]))
        log.debug("GBLD BiasCurr = \t{:#x}".format(data[2]))
        log.debug("GBLD PreEmph = \t{:#x}".format(data[3]))
        log.debug("GBLD ModMask = \t{:#x}".format(data[4]))
        log.debug("GBLD BiasMask = \t{:#x}".format(data[5]))
        log.debug("GBLD PreDrv = \t{:#x}".format(data[6]))
        return data

    def gbld_write(self, gbtx_id, regs):
        """Write register array to GBLD connected to given GBTx
        regs - list of register values, preferably fetched initially by gbld_read()
        """
        assert len(regs) == 7
        self.gbtx_write_reg_array(gbtx_id, 55, regs)
        self.gbtx_write_reg(gbtx_id, 253, 126)
        self.gbtx_write_reg(gbtx_id, 388, 1)

    def gbtx_init_master(self, term=True ):
        """Configure all master GBTx settings for CROB"""
        log.info("Configuring master GBTx through software functions")
        # watchdog has to be disabled while reconfiguring elinks/clocks
        # otherwise it will trigger and make GBTx inaccesible
        self.gbtx_watchdog_set(self.GBTX_MASTER, False)
        # master GBTx #
        log.info("Configuring epll")
        self.gbtx_epll_init(self.GBTX_MASTER)
        log.info("Configuring elinks")
        for i in range(5):
            self.gbtx_elink_input_init(self.GBTX_MASTER, i, (0, 4), 320, term)
        # for dIO used in widebus mode the elink offsets are +1
        for i in range(5, 7):
            self.gbtx_elink_input_init(self.GBTX_MASTER, i, (1, 5), 320, term)
        for i in range(2, 5):
            self.gbtx_elink_output_init(self.GBTX_MASTER, i, (0, 4), 160)
        # there are some dependencies between EC and normal elinks, so it's safer to initialise EC later
        self.gbtx_ec_init(self.GBTX_MASTER)
        log.info("Configuring pll")
        self.gbtx_clock_pll_init(self.GBTX_MASTER)
        for i in range(6):
            self.gbtx_clock_init(self.GBTX_MASTER, i, 160)
        # reference clocks for slave GBTx
        log.info("Configuring clock for slaves")
        self.gbtx_clock_init(self.GBTX_MASTER, 6, 40)
        self.gbtx_clock_init(self.GBTX_MASTER, 7, 40)
        # select a clock phase for slave GBTX external clock i, 160)
        # reference clocks for slave GBTx
        log.info("Configuring clock phase for slaves")
        self.gbtx_clock_phase_set(self.GBTX_MASTER, 6, 0)
        self.gbtx_clock_phase_set(self.GBTX_MASTER, 7, 0)
        # select positive edge when passing data from TX path to serialiser
        log.info("Configuring xyzgflb?!?")
        self.gbtx_write_reg(self.GBTX_MASTER, 244, 0x38)
        self.gbtx_watchdog_set(self.GBTX_MASTER, True)

    def gbtx_init_master_test(self):
        """Configure all master GBTx settings for CROB"""
        log.info("Configuring master GBTx through software functions")
        # watchdog has to be disabled while reconfiguring elinks/clocks
        # otherwise it will trigger and make GBTx inaccesible
        log.info("Disable watchdog")
        self.gbtx_watchdog_set(self.GBTX_MASTER, False)
        # master GBTx #
        log.info("EPLL Init")
        self.gbtx_epll_init(self.GBTX_MASTER)
        #for i in range(5):
        #    self.gbtx_elink_input_init(self.GBTX_MASTER, i, (0, 4), 320)
        # for dIO used in widebus mode the elink offsets are +1
        #for i in range(5, 7):
        #    self.gbtx_elink_input_init(self.GBTX_MASTER, i, (1, 5), 320)
        #for i in range(2, 5):
        #    self.gbtx_elink_output_init(self.GBTX_MASTER, i, (0, 4), 160)
        # there are some dependencies between EC and normal elinks, so it's safer to initialise EC later
        #self.gbtx_ec_init(self.GBTX_MASTER)
        #self.gbtx_clock_pll_init(self.GBTX_MASTER)
        #for i in range(6):
        #    self.gbtx_clock_init(self.GBTX_MASTER, i, 160)
        # reference clocks for slave GBTx
        #self.gbtx_clock_init(self.GBTX_MASTER, 6, 40)
        #self.gbtx_clock_init(self.GBTX_MASTER, 7, 40)
        # select a clock phase for slave GBTX external clock
        #self.gbtx_clock_phase_set(self.GBTX_MASTER, 6, 0)
        #self.gbtx_clock_phase_set(self.GBTX_MASTER, 7, 0)
        # select positive edge when passing data from TX path to serialiser
        #self.gbtx_write_reg(self.GBTX_MASTER, 244, 0x38)
        #self.gbtx_watchdog_set(self.GBTX_MASTER, True)

    def gbtx_init_slaves(self):
        """Configure slave GBTx for CROB"""
        log.info("Configuring slave GBTx through software functions")
        self.gbtx_epll_init(self.GBTX_SLAVE_1)
        self.gbtx_epll_init(self.GBTX_SLAVE_2)
        for i in range(7):
            self.gbtx_elink_input_init(self.GBTX_SLAVE_1, i, (0, 4), 320)
            self.gbtx_elink_input_init(self.GBTX_SLAVE_2, i, (0, 4), 320)
        # slave #1 has 3 clock outputs connected, but they aren't used outside of MUCH
        # self.gbtx_clock_pll_init(self.GBTX_SLAVE_1)
        # for i in range(3):
        #     self.gbtx_clock_init(self.GBTX_SLAVE_1, i, 160)


    def warnings_decode(self, warnings):
        # res(0) := warn_rec.sx_throttling;
        # res(1) := warn_rec.sx_sync_alert;
        # res(2) := warn_rec.sx_alert;
        # res(3) := warn_rec.missing_sync;
        # res(4) := warn_rec.dpb_bitslip;
        # res(5) := warn_rec.code_err;
        # res(6) := warn_rec.disp_err;
        log.info("Fields from SX ACK frame:")
        log.info("   Throttling: %d" % ( 1 if warnings%(1<<0) else 0))
        log.info("   Sync Alert: %d" % ( 1 if warnings%(1<<1) else 0))
        log.info("   Alert: %d" % ( 1 if warnings%(1<<2) else 0))
        log.info("Generated by DPB:")
        log.info("   Missing sync: %d" % ( 1 if warnings%(1<<3) else 0))
        log.info("   UL bitslip: %d" % ( 1 if warnings%(1<<4) else 0))
        log.info("   UL 8b/10b encoder code error: %d" % ( 1 if warnings%(1<<5) else 0))
        log.info("   UL 8b/10b encoder disparity error: %d" % ( 1 if warnings%(1<<6) else 0))
        log.info("\n\n")
