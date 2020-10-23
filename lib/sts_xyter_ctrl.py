import pickle
import logging as log
import time
import math

N_OF_SLOTS = 5
N_OF_SEQ   = 16
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



class sts_xyter(object):
    """This class is a logical unit representing single STSXYTER
    It doesn't have exact mapping in address map hierarchy. The exact registers
    used in CROB module for communication with this exact SX instance are
    determined based on downlink and uplink numbers
    group      - sts_xyter_group object holding this SX, should correspond to a full FEB (single downlink)
    chip_idx   - index of this sts_xyter object in the sts_xyter_group object vector
    chip_nr    - ordering number used by firmware; should be unique for each SX on given downlink; range <0; 7>
    chip_addr  - hardware address of SX; range <0; 7>
    ulink_map  - array/tuple containing index numbers of GBTx e-link inputs connected to this SX
    elink_mask - bit mask of hard/soft disabled elinks (refer to STSXYTER datasheet)
    dpb_mask   - elink mask to be applied in the DPB to enable the communication with this SX
    """

    def __init__(self, group, chip_idx, chip_nr, chip_addr, ulink_map, elink_mask, dpb_mask = None):
        assert isinstance(ulink_map, (list, tuple))
        assert 0 <= chip_nr <= 7
        assert 0 <= chip_addr <= 7
        assert 0x0 <= elink_mask <= 0x3FF

        self.hw = group.hw
        self.group = group
        self.chip_idx  = chip_idx
        self.chip_nr   = chip_nr
        self.chip_addr = chip_addr
        self.ulink_map = ulink_map
        self.elink_mask = elink_mask
        if dpb_mask is not None:
            self.dpb_mask = ~(0x1 << dpb_mask) & 0xFF # dpb_mask
            self.dpb_idx = dpb_mask
        else:
            self.dpb_mask = ~(0x1 << self.chip_nr) & 0xFF
            self.dpb_idx = chip_nr

        self.cmd_stats = [ipbus(self.hw, group.dev + ".sx[{:d}]".format(self.dpb_idx) + node) for node
                          in (".stats[0]", ".stats[1]", ".stats[2]", ".stats[3]", ".stats[4]")]
        self.td_cmd_stats = [ipbus(self.hw, group.dev + ".sx[{:d}]".format(self.dpb_idx) + node) for node
                             in (".td_stats[0]", ".td_stats[1]")]

        self.DetClears = [ipbus(self.hw, group.crob.dev + ".ul.seq_det_in[{:d}]".format(ulink)) for ulink in ulink_map]
        self.DetOuts = [ipbus(self.hw, group.crob.dev + ".ul.seq_det_out[{:d}]".format(ulink)) for ulink in ulink_map]

    def setMuchDpbMask(self):

        ulinkCnt = 0
        self.dpb_mask = 0xFF
        for ulink in self.ulink_map:
            self.dpb_mask &= ~(0x1 << ulinkCnt) & 0xFF # dpb_mask
            ulinkCnt += 1

    def write(self, row, col, val, delay_addr_ack=False, timeout=10):
        """ Write to SX register.
        """
        self.group.write(row, col, val, self.chip_idx, delay_addr_ack, timeout)
        #print "Register write: [",row,",",col,",",val,"]"


    def read(self, row, col, timeout=10):
        """ Read SX register.
        """
        data = self.group.read(row, col, self.chip_idx, timeout)
#        if row <= 130:
#            data[0] = (data[0] & 0xff)
        if 130 == row:
            data[0] = (data[0] & 0xff)
        elif row < 130:
            if 0 == col%2:
                data[0] = (data[0] & 0xfff)
            else:
                data[0] = (data[0] & 0xff)
        return data[0]

    def write_check(self, row, col, val, delay_addr_ack=False, timeout=10):
        self.write(row, col, val, delay_addr_ack, timeout)
        w_val = val
        r_val = self.read(row, col, timeout)

        # print "r_val", r_val

        if r_val == w_val:
            # print "Initial written value. val " , w_val
            # print "read_val " ,r_val
            # print "Register value set correctly: [",row,",",col,",",w_val,"]"
            # print " "
            pass
        else:
            log.warning("ERROR writing the register: [{:3d},{:3d}] {:5d} vs {:5d}".format(row, col, r_val, w_val) )
            raise Exception("Failed to check written value")
        # print " "


class sts_xyter_group(object):
    """ Class holding all STSXYTERs connected to one downlink.
    Implements indexing and iterator, so it can be used like a basic collection type.
    Read and write method allow for sending broadcast commands

    crob - base CROB module to which this SX group is connected
    clock - index of GBTx clock output driving this SX group
    dlink - index of GBTx e-link output driving this SX group; range <0; 5>
    """

    def __init__(self, crob, clock, dlink):
        self.crob = crob
        self.hw = crob.hw
        self.dev = crob.dev + ".ct[{:d}]".format(dlink)
        self.clock = clock
        self.dlink = dlink
        self.seq_nr = 1
        self.slot_nr = 0
        self.bcast_sx_mask = 0xFF  # all SX masked out by default
        self.sxs = []

        self.cmd_slots = [ipbus(self.hw, self.dev + node) for node
                          in (".cmds[0]", ".cmds[1]", ".cmds[2]", ".cmds[3]", ".cmds[4]")]
        self.td_cmd_slots = [ipbus(self.hw, self.dev + node) for node
                             in (".td_cmds[0]", ".td_cmds[1]")]
        self.td_cmd_fnums = [ipbus(self.hw, self.dev + node) for node
                             in (".td_fnums[0]", ".td_fnums[1]")]
        self.enc_mode = ipbus(self.hw, self.dev + ".sx_mask_enc_mode.mode")
        self.sx_mask = ipbus(self.hw, self.dev + ".sx_mask_enc_mode.mask")
        self.rep_period = ipbus(self.hw, self.dev + ".auto_c0_per")

    """ Add new STSXYTER to a SX group
    asic_idx  - SMX index in the FEB
    chip_addr - SX hardware address
    ulink_map - list/tuple containing index numbers of uplinks used by given SX
    """
    def add_sx(self, chip_nr, chip_addr, ulink_map, elink_mask, dpb_mask = None ):
#        chip_nr = len(self.sxs) <=== chip index is HW defined!
        self.sxs.append(sts_xyter(self, len(self.sxs), chip_nr, chip_addr, ulink_map, elink_mask, dpb_mask))

        if dpb_mask is not None:
            self.bcast_sx_mask &= dpb_mask
        else:
            self.bcast_sx_mask &= ~(0x1 << chip_nr)

    def sendElinkDisableAll(self):
        """ Broadcast a eLink hard disable all without waiting for any answer.
        """
        log.info("broadcast eLink disable")

        row = 192
        col = 25
        val = 0x3FF
        chip_addr = 0xF
        self.sx_mask.write( 0xFF )

        xaddr = ((chip_addr & 0xf) << 21) | \
                ((self.seq_nr & 0xf) << 17) | \
                (0x01 << 15) | \
                ((col & 0x7f) << 8) | \
                (row & 0xff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ
        xval = (chip_addr & 0xf) << 21 | \
               ((self.seq_nr & 0xf) << 17) | \
               (0x02 << 15) | \
               (val & 0x7fff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ

        start_time = time.time()
        # Write address
        self.cmd_slots[self.slot_nr].write(xaddr)

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS
        # Write data
        self.cmd_slots[self.slot_nr].write(xval)

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS

    def sendAllSetCsaToMin(self):
        """ Broadcast a eLink hard disable all without waiting for any answer.
        """
        log.info("broadcast front CSA set to 0")

        row = 130
        col = 0
        val = 0
        chip_addr = 0xF
        self.sx_mask.write( 0xFF )

        xaddr = ((chip_addr & 0xf) << 21) | \
                ((self.seq_nr & 0xf) << 17) | \
                (0x01 << 15) | \
                ((col & 0x7f) << 8) | \
                (row & 0xff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ
        xval = (chip_addr & 0xf) << 21 | \
               ((self.seq_nr & 0xf) << 17) | \
               (0x02 << 15) | \
               (val & 0x7fff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ

        start_time = time.time()
        # Write address
        self.cmd_slots[self.slot_nr].write(xaddr)

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS
        # Write data
        self.cmd_slots[self.slot_nr].write(xval)

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS

        log.info("broadcast back CSA set to 0")

        row = 130
        col = 13
        val = 0
        chip_addr = 0xF
        self.sx_mask.write( 0xFF )

        xaddr = ((chip_addr & 0xf) << 21) | \
                ((self.seq_nr & 0xf) << 17) | \
                (0x01 << 15) | \
                ((col & 0x7f) << 8) | \
                (row & 0xff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ
        xval = (chip_addr & 0xf) << 21 | \
               ((self.seq_nr & 0xf) << 17) | \
               (0x02 << 15) | \
               (val & 0x7fff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ

        start_time = time.time()
        # Write address
        self.cmd_slots[self.slot_nr].write(xaddr)

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS
        # Write data
        self.cmd_slots[self.slot_nr].write(xval)

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS

    def write(self, row, col, val, chip_nr=None, delay_addr_ack=False, timeout=2):
        """ Write to SX register.
        chip_nr - index number for targeted SX or '-1' for broadcast
        skip_addr_ack - skip checking address ACK. Main usage for this argument is when
        writing to elink_mask register to enable/disable some elinks
        timeout - timeout (in seconds) after which function should cancel the request
        and stop command transmitter
        """

        if chip_nr is not None:
            chip_addr = self.sxs[chip_nr].chip_addr
#            self.sx_mask.write(~(0x1 << chip_nr) & 0xFF) ## Would not work as chip_nr != Index in FEB!!
            self.sx_mask.write( self.sxs[chip_nr].dpb_mask )
        else:
            log.info("broadcast write")
            # If this is a broadcast write, we need to set SX mask accordingly.
            chip_addr = 0xF
            self.sx_mask.write(self.bcast_sx_mask)

        xaddr = ((chip_addr & 0xf) << 21) | \
                ((self.seq_nr & 0xf) << 17) | \
                (0x01 << 15) | \
                ((col & 0x7f) << 8) | \
                (row & 0xff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ
        xval = (chip_addr & 0xf) << 21 | \
               ((self.seq_nr & 0xf) << 17) | \
               (0x02 << 15) | \
               (val & 0x7fff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ

        # Ensure that we are going to send the command using a pair of frames
        # => Starting slot should be an even one
        # => Starting slot cannot be the last possible if Nb slot is odd
        if 1 == self.slot_nr % 2 :
            self.slot_nr += 1
        if (1 == N_OF_SLOTS % 2) and (N_OF_SLOTS - 1 == self.slot_nr) :
            self.slot_nr = 0

        # Force bit 25 of both commands to 1 to indicate we are doing a (Addr + Data) pair sending
        xaddr |= (0x01 << 25)
        xval  |= (0x01 << 25)

#        log.info("Write: r%3u c%2u val 0x%4x xaddr %08x xdata %08x slot %u seq %u",
#                  row, col, val, xaddr, xval, self.slot_nr, self.seq_nr)

        # Always check the Addr return frame after the full pair is sent
        delay_addr_ack = True

        start_time = time.time()
        # Write address
        self.cmd_slots[self.slot_nr].write(xaddr)

        # For unicast write, check single SX. For broadcast check all of them
        slot_prev = self.slot_nr
        if not delay_addr_ack:
            if chip_nr is not None:
                while True:
                    if self.sxs[chip_nr].cmd_stats[self.slot_nr].read() & (0x1 << 31) == 0:
                        break
                    if time.time() - start_time > timeout:
                        self.cmd_slots[self.slot_nr].write(0x1 << 31)
                        raise Exception("Timeout waiting for STSXYTER wraddr ack")

            else:
                for sx in self.sxs:
                    while True:
                        if sx.cmd_stats[self.slot_nr].read() & (0x1 << 31) == 0:
                            break
                        if time.time() - start_time > timeout:
                            self.cmd_slots[self.slot_nr].write(0x1 << 31)
                            raise Exception("Timeout waiting for STSXYTER wraddr ack")

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS
        # Write data
        self.cmd_slots[self.slot_nr].write(xval)

        # Check return frame for the Address part of the command if necessary
        if delay_addr_ack:
            if chip_nr is not None:
                while True:
                    ret_val = self.sxs[chip_nr].cmd_stats[slot_prev].read()
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
                        raise Exception("Timeout waiting for STSXYTER wraddr ack after delay")
            else:
                for sx in self.sxs:
                    while True:
                        ret_val = sx.cmd_stats[slot_prev].read()
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
                            raise Exception("Timeout waiting for STSXYTER wraddr ack after delay")

        # Check return frame for the data part of the command
        if chip_nr is not None:
            while True:
                ret_val = self.sxs[chip_nr].cmd_stats[self.slot_nr].read()
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
        else:
            for sx in self.sxs:
                while True:
                    ret_val = sx.cmd_stats[self.slot_nr].read()
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

    def read(self, row, col, chip_nr=None, timeout=2):
        """ Write to SX register.
        Broadcast mode will use broadcast address for command, but it will also
        skip setting a downlink SX mask. This can potentially confuse command
        transmitter into sending command indefinitely to unconnected (but unmasked)
        SXs.
        timeout - timeout (in seconds) after which function should cancel sending command
        """

        if chip_nr is not None:
            chip_addr = self.sxs[chip_nr].chip_addr
#            self.sx_mask.write(~(0x1 << chip_nr) & 0xFF) ## Would not work as chip_nr != Index in FEB!!
            self.sx_mask.write( self.sxs[chip_nr].dpb_mask )
        else:
            log.info("broadcast read")
            # If this is a broadcast read, we need to set SX mask accordingly.
            chip_addr = 0xF
            self.sx_mask.write(self.bcast_sx_mask)

        xrdad = ((chip_addr & 0xf) << 21) | \
                ((self.seq_nr & 0xf) << 17) | \
                (0x03 << 15) | \
                ((col & 0x7f) << 8) | \
                (row & 0xff)
        self.seq_nr += 1
        self.seq_nr %= N_OF_SEQ

        start_time = time.time()
        # Read command
        self.cmd_slots[self.slot_nr].write(xrdad)
        data = []
        if chip_nr is not None:
            while True:
                val = self.sxs[chip_nr].cmd_stats[self.slot_nr].read()
                if val & (0x1 << 31) == 0:
                    # NACK comes in different frame than RDDATA, so check frame type too
                    if val & 0x280000 == 0:
                        log.warning("STSXYTER read NACK!")
                        data.append(0x0)
                    else:
                        val = (val & 0x1fffff) >> 6
                        if 130 == row:
                            val = (val & 0xff)
                        elif row < 130:
                            if 0 == col%2:
                                val = (val & 0xfff)
                            else:
                                val = (val & 0xff)
                        data.append( val )
                    break
                if time.time() - start_time > timeout:
                    self.cmd_slots[self.slot_nr].write(0x1 << 31)
                    raise Exception("Timeout waiting for STSXYTER read ack")
        else:
            for sx in self.sxs:
                while True:
                    val = sx.cmd_stats[self.slot_nr].read()
                    if val & (0x1 << 31) == 0:
                        # NACK comes in different frame than RDDATA, so check frame type too
                        if val & 0x280000 == 0:
                            log.warning("STSXYTER read NACK!")
                            data.append(0x0)
                        else:
                            val = (val & 0x1fffff) >> 6
                            if 130 == row:
                                val = (val & 0xff)
                            elif row < 130:
                                if 0 == col%2:
                                    val = (val & 0xfff)
                                else:
                                    val = (val & 0xff)
                            data.append( val )
                        break
                    if time.time() - start_time > timeout:
                        self.cmd_slots[self.slot_nr].write(0x1 << 31)
                        raise Exception("Timeout waiting for STSXYTER read ack")

        self.slot_nr += 1
        self.slot_nr %= N_OF_SLOTS

        return data

    def write_check(self, row, col, val, chip_nr, delay_addr_ack=False, timeout=2):
        self.write(row, col, val, chip_nr, delay_addr_ack, timeout)
        w_val = val
        r_val = self.read(row, col, chip_nr, timeout)[0]

        # print "r_val", r_val

        if r_val == w_val:
            # print "Initial written value. val " , w_val
            # print "read_val " ,r_val
            # print "Register value set correctly: [",row,",",col,",",w_val,"]"
            # print " "
            pass
        else:
            log.warning("ERROR writing the register: [{:3d},{:3d}] {:5d} vs {:5d}".format(row, col, r_val, w_val) )
            raise Exception("Failed to check written value")
        # print " "

    def td_write(self, row, col, val, fnum, chip_nr=None, blocking=False):
        fnum = fnum & ((1 >> 28) - 1)
        fnum1 = (fnum + 1) & ((1 >> 28) - 1)
        fnum |= (1 << 31)
        fnum1 |= (1 << 31)
        seq_nr = 14
        if chip_nr is not None:
            chip_addr = self.sxs[chip_nr].chip_addr
#            self.sx_mask.write(~(0x1 << chip_nr)) ## Would not work as chip_nr != Index in FEB!!
            self.sx_mask.write( self.sxs[chip_nr].dpb_mask )
        else:
            log.info("broadcast TD write")
            # If this is a broadcast write, we need to set SX mask accordingly.
            chip_addr = 0xF
            self.sx_mask.write(self.bcast_sx_mask)

        xaddr = ((chip_addr & 0xf) << 21) | \
                ((seq_nr & 0xf) << 17) | \
                (0x01 << 15) | \
                ((col & 0x7f) << 8) | \
                (row & 0xff)
        seq_nr = 15
        xval = (chip_addr & 0xf) << 21 | \
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
            if chip_nr is not None:
                while True:
                    val = self.sxs[chip_nr].td_cmd_stats[0].read()
                    val2 = self.sxs[chip_nr].td_cmd_stats[1].read()
                    log.debug(hex(val) + ":" + hex(val2))
                    if (val & 0x80000000 == 0) and (val2 & 0x80000000 == 0):
                        break
                    # Here we should check if it is not an NACK!
            else:
                log.error("Not implemented yet")

    def td_cancel(self):
        log.error("td_cancel is not yet implemented properly")
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

    def __getitem__(self, item):
        return self.sxs[item]

    def __len__(self):
        return len(self.sxs)

    def __iter__(self):
        self.n = 0
        return self

    def next(self):
        if self.n < len(self.sxs):
            self.n += 1
            return self.sxs[self.n - 1]
        else:
            raise StopIteration


def __find_center(dta, dlen):
    """
    Given a list of (True, False) values, find and return center of longest "True" sequence
    """

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


def __mean_circular(data, wrap):
    """
    Find an average value of data representing circular arithmetics (e.g. angles, hours)
    This function uses a popular "mean of angles" method:
                   mean(sum_i_from_1_to_N sin(a[i]))
    mean = arctan2 ---------------------------------
                   mean(sum_i_from_1_to_N cos(a[i]))

    It is important to note that in circular arithmetics mean value is not always
    defined (e.g. mean between 0 and 180 deg is 90 or 270?)
    :param data: vector of values to be averaged
    :param wrap: maximum value possible for data vector (wraparound value)
    :return: mean value
    """
    assert isinstance(data, (list, tuple))

    if 1 == len(data):
        return data[0]

    scale = 2 * math.pi / wrap
    data_rad = [i * scale for i in data]
    cos = 0
    sin = 0
    for val in data_rad:
        cos += math.cos(val)
        sin += math.sin(val)

    cos /= len(data)
    sin /= len(data)
    if sin >= 0 and cos >= 0:
        mean = math.atan(sin/cos)
    elif cos < 0:
        mean = math.atan(sin/cos) + math.pi
    else:  # sin < 0 and cos > 0
        mean = math.atan(sin/cos) + 2 * math.pi

    return mean / scale


def full_link_sync( afck_idx, sx_group, merge_uplink_results=False):
    """
    Perform full link synchronisation procedure for all STSXYTERs in a given group.
    All SXs in a group must be connected to the same downlink line. That's because
    these SX chips share a common downlink, so if a downlink switches to sending
    synchronisation symbols all connected SXs will switch to synchronisation mode.
    It should be noted that this function won't automatically enable data
    frame mode, so after synchronisation you should call EncMode(MODE_FRAME)
    to enable data transmission.
    sx_group - class instance representing STSXYTER(s) connected to one downlink
    merge_elink_phase - merge link delay results of all uplinks of single SX to widen the forbidden 'X' area.
                This is useful when it's known that uplinks have similar delays, but due to minimal
                differences some channels are on the edge and not properly characterized during synchronisation.
    """
    assert isinstance(sx_group, sts_xyter_group)

    if( 0 == len(sx_group) ):
        log.info("### Doing nothing on Downlink #{:d} as no active ASIC ###".format( sx_group.dlink ) )
        return

    log.info(
        "\n### Doing full eLink SYNC for {:d} STSXYTERs on downlink #{:d} ###".format(len(sx_group), sx_group.dlink))

    crob = sx_group.crob
    clock = sx_group.clock
    dlink = sx_group.dlink

    # get mask of currently enabled elinks
    elink_mask = crob.hw.getNode(crob.dev + ".link_mask[0]").read()
    crob.hw.dispatch()
    reg = crob.hw.getNode(crob.dev + ".link_mask[1]").read()
    crob.hw.dispatch()
    elink_mask = int(elink_mask)  # to use python wide integers we have to convert from ipbus type
    elink_mask |= int(reg) << 32

    crob.gbtx_clock_phase_set(0, clock, 0)

    # Force SOS mode
    sx_group.enc_mode.write(MODE_SOS)
    for sx in sx_group:
        for dc in sx.DetClears:
            dc.write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
            dc.write(0)

    # Check, that all input channels responded
    missingSOS = False
    for sx in sx_group:
        for i in range(0, len(sx.DetOuts)):
            r = sx.DetOuts[i].read()
            ulink = sx.ulink_map[i]
            log.debug("DetOut status for uplink {:2d} = {:#x}".format(ulink, r))
            if (r & SOS_DET == 0) and (elink_mask & (1 << ulink)):
                log.debug("{:2d}, {:#x}, SOS not received after 1us".format(ulink, r))
                log.info("Not received SOS on uplink {:d} (ASIC {:d})".format(ulink, sx.chip_nr))
                missingSOS = True

    if True == missingSOS:
        raise Exception("Not received SOS on at least one enabled uplink")

    log.info("Switching to K28_1")
    # Now switch to sending K28_1
    sx_group.enc_mode.write(MODE_K28_1)
    # Clear glitch detectors
    for sx in sx_group:
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(0)
    # Verify results
    for sx in sx_group:
        for i in range(0, len(sx.DetOuts)):
            r = sx.DetOuts[i].read()
            log.debug("K28_1 status for uplink {:2d} = {:#x}".format(i, r))

    # Now shift clock step by step. For each step check uplink status of all SXs
    log.info("Performing clock scan")
    test = [[] for _ in range(0, len(sx_group))]
    CLK_STEPS = 128
    clk_del = 0
    while clk_del < CLK_STEPS:
        # Scan possible values, looking for those, assuring correct transmission
        crob.gbtx_clock_phase_set(0, clock, clk_del)
        idx = 0
        for sx in sx_group:
            # Clear detectors
            for i in range(0, len(sx.DetClears)):
                sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
            for i in range(0, len(sx.DetClears)):
                sx.DetClears[i].write(0)
            time.sleep(0.01)

            res = []
            sos_all = True
            for i in range(0, len(sx.DetOuts)):
                r = sx.DetOuts[i].read()
                ulink = sx.ulink_map[i]
                r1 = (r & SOS_DET_STABLE0) or (elink_mask & (0x1 << ulink) == 0)
                res.append(r1 != 0)
                if r1 == 0:
                    sos_all = False
            test[idx].append(sos_all)
            log.debug("SX #{:d} clk = {} {}".format(idx, clk_del, res))
            idx += 1
        clk_del += 1

    # Finished clock delay scanning. Let's summarize & apply scan results
    clk_results = []
    for idx in range(len(sx_group)):
        try:
            clk_results.append(__find_center(test[idx], CLK_STEPS))
        except:
            log.warn("Couldn't find clock edge; using default delay = 0")
            clk_results.append(0)
        # build a nice window eye graph to display
        window = ['_' if item else 'X' for item in test[idx]]
        window.insert(0, '|')
        window.append('|')
        window = ''.join(window)
        log.info("STSXYTER #{:d} (ASIC {:d}, addr {:d}) clock delay = {}".format(idx,
                        sx_group[idx].chip_nr, sx_group[idx].chip_addr, clk_results[idx]))
        log.info("Eye window of the clock signal:")
        log.info(window)

    # Set the clock delay to calculated values
    clk_average = round(__mean_circular(clk_results, CLK_STEPS - 1))
    log.info("Final clock delay (average) = {:d}".format(int(clk_average)))
    crob.gbtx_clock_phase_set(0, clock, int(clk_average))

    # Now start scanning input elink delays
    # Order is different than for clock scanning - now we perform phase scanning
    # sequentially for each STSXYTER
    log.info("Performing data delay scan")
    del_results = []
    test_results = []
    idx = 0
    for sx in sx_group:
        data_del = 0
        test = [[] for _ in range(0, len(sx.DetOuts))]
        while data_del < 16:
            for ul in sx.ulink_map:
                gbtx_id = ul // 14
                elink = ul % 14 * 4  # this calculation comes from linear mapping in FPGA gateware
                crob.gbtx_elink_phase_set(gbtx_id, elink, data_del)
            # Clear glitch detectors
            for i in range(0, len(sx.DetClears)):
                sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
                sx.DetClears[i].write(0)
            # Wait for test result
            time.sleep(0.1)
            res = []
            for i in range(0, len(sx.DetOuts)):
                r = sx.DetOuts[i].read()
                r1 = r & K28_1_DET_STABLE1 # K28_1_DET
                res.append(r1 != 0)
                test[i].append(r1 != 0)
            log.debug("SX #{:d} {} {}".format(idx, data_del, res))
            data_del += 1

        if merge_uplink_results:
            log.debug("Merging uplink results")
            merged_test = [all(x) for x in zip(*test)]
            test = [merged_test for x in test]

        # Find the biggest area filled with ones
        # Now calculate optimum delay for each channel
        data_dels = [ 6 ] * 5
        for i in range(0, len(sx.DetOuts)):
            if elink_mask & (0x1 << sx.ulink_map[i]):
                try:
                    data_dels[i] = __find_center(test[i], 16)
                except:
                    log.warn("Couldn't find data edge on uplink #{:2d}; using default delay = {:d}".format(
                                        sx.ulink_map[i], data_dels[i]))

                ul = sx.ulink_map[i]
                gbtx_id = ul // 14
                elink = ul % 14 * 4  # this calculation comes from linear mapping in FPGA gateware
                log.info("ul  #{:2d}  elink #{:2d} ".format(ul, elink))
                crob.gbtx_elink_phase_set(gbtx_id, elink, data_dels[i])
        test_results.append(test)
        del_results.append(data_dels)
        idx += 1

    # build a nice window eye graph to display
    for idx in range(len(sx_group)):
        windows = []
        for window in test_results[idx]:
            windows.append(['_' if item else 'X' for item in window])
        [w.insert(0, '|') for w in windows]
        [w.append('|') for w in windows]
        windows = [''.join(w) for w in windows]
        log.info("STSXYTER #{:d} (ASIC {:d}) data delays = {}".format(idx, sx_group[idx].chip_nr, del_results[idx]))
        idx += 1
        log.info("Eye window of the data signals:")
        for w in windows:
            log.info(w)

    # Now verify data delay settings:
    idx = 0
    for sx in sx_group:
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(0)
        time.sleep(0.02)
        test_k28 = []
        for i in range(0, len(sx.DetOuts)):
            r = sx.DetOuts[i].read()
            r1 = r & K28_1_DET_STABLE1 # K28_1_DET
            test_k28.append(r1 != 0)
        log.debug("STSXYTER #{:d} k28_1 test result: {}".format(idx, test_k28))
        idx += 1

    # Send EOS
    sx_group.enc_mode.write(MODE_EOS)

    # Now verify correct operation:
    idx = 0
    missingEOS = False
    for sx in sx_group:
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(0)
        time.sleep(0.01)
        all_eos = True
        test_eos = []
        for i in range(0, len(sx.DetOuts)):
            r = sx.DetOuts[i].read()
            ulink = sx.ulink_map[i]
            r1 = (r & EOS_DET_STABLE1) or (elink_mask & (0x1 << ulink) == 0)   # EOS_DET
            if r1 == 0:
                all_eos = False
                log.info("Not received EOS on uplink {:d} (ASIC {:d}): {:d} {:d}".format(
                            ulink, sx.chip_nr, r & EOS_DET_STABLE1, elink_mask & (0x1 << ulink) == 0 ) )
            test_eos.append(r1 != 0)
        log.debug("STSXYTER #{:2d} eos test result: {}".format(idx, test_eos))
        if all_eos is False:
            log.info("Not received EOS on all links for STSXYTER #{:d} (ASIC {:d})".format(idx, sx_group[idx].chip_nr) )

            # Clear the results arrays/list
#            test[i].clear()

            # Switch back to sending SOS
            sx_group.enc_mode.write(MODE_SOS)
            time.sleep(0.01)

            # Switch back to sending K28_1
            sx_group.enc_mode.write(MODE_K28_1)

            # Now start scanning input elink delays
            # Order is different than for clock scanning - now we perform phase scanning
            # sequentially for each STSXYTER
            log.info("--> Performing data delay scan without stable request")
            data_del = 0
            test = [[] for _ in range(0, len(sx.DetOuts))]
            while data_del < 16:
                for ul in sx.ulink_map:
                    gbtx_id = ul // 14
                    elink = ul % 14 * 4  # this calculation comes from linear mapping in FPGA gateware
                    crob.gbtx_elink_phase_set(gbtx_id, elink, data_del)
                # Clear glitch detectors
                for i in range(0, len(sx.DetClears)):
                    sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
                    sx.DetClears[i].write(0)
                # Wait for test result
                time.sleep(0.1)
                res = []
                for i in range(0, len(sx.DetOuts)):
                    r = sx.DetOuts[i].read()
                    r1 = r & K28_1_DET
                    res.append(r1 != 0)
                    test[i].append(r1 != 0)
                log.debug("--> SX #{:d} {} {}".format(idx, data_del, res))
                data_del += 1

            if merge_uplink_results:
                log.debug("--> Merging uplink results")
                merged_test = [all(x) for x in zip(*test)]
                test = [merged_test for x in test]

            # Find the biggest area filled with ones
            # Now calculate optimum delay for each channel
            data_dels = [ 6 ] * 5
            for i in range(0, len(sx.DetOuts)):
                if elink_mask & (0x1 << sx.ulink_map[i]):
                    try:
                        data_dels[i] = __find_center(test[i], 16)
                    except:
                        log.warn("--> Couldn't find data edge on uplink #{:2d}; using default delay = {:d}".format(
                                            sx.ulink_map[i], data_dels[i]))

                    ul = sx.ulink_map[i]
                    gbtx_id = ul // 14
                    elink = ul % 14 * 4  # this calculation comes from linear mapping in FPGA gateware
                    log.info("--> ul  #{:2d}  elink #{:2d} ".format(ul, elink))
                    crob.gbtx_elink_phase_set(gbtx_id, elink, data_dels[i])
            test_results[idx] = test
            del_results[ idx ] = data_dels

            windows_unstable = []
            for window in test_results[idx]:
                windows_unstable.append(['_' if item else 'X' for item in window])
            [w.insert(0, '|') for w in windows_unstable]
            [w.append('|') for w in windows_unstable]
            windows_unstable = [''.join(w) for w in windows_unstable]
            log.info("--> STSXYTER #{:d} (ASIC {:d}) data delays = {}".format(idx, sx_group[idx].chip_nr, del_results[idx]))

            log.info("--> Eye window of the data signals:")
            for w in windows_unstable:
                log.info(w)

            for i in range(0, len(sx.DetClears)):
                sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
            for i in range(0, len(sx.DetClears)):
                sx.DetClears[i].write(0)
            time.sleep(0.02)
            test_k28 = []
            for i in range(0, len(sx.DetOuts)):
                r = sx.DetOuts[i].read()
                r1 = r & K28_1_DET
                test_k28.append(r1 != 0)
            log.debug("--> STSXYTER #{:d} k28_1 test result: {}".format(idx, test_k28))


            # Send EOS
            sx_group.enc_mode.write(MODE_EOS)

            # Now verify correct operation:
            for i in range(0, len(sx.DetClears)):
                sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
            for i in range(0, len(sx.DetClears)):
                sx.DetClears[i].write(0)
            time.sleep(0.01)
            all_eos = True
            test_eos = []
            for i in range(0, len(sx.DetOuts)):
                r = sx.DetOuts[i].read()
                ulink = sx.ulink_map[i]
                r1 = (r & EOS_DET) or (elink_mask & (0x1 << ulink) == 0)
                if r1 == 0:
                    all_eos = False
                    log.info("--> Not received EOS on uplink {:d} (ASIC {:d}): {:d} {:d}".format(
                                ulink, sx.chip_nr, r & EOS_DET, elink_mask & (0x1 << ulink) == 0 ) )
                test_eos.append(r1 != 0)
            log.debug("--> STSXYTER #{:2d} eos test result: {}".format(idx, test_eos))
            if all_eos is False:
                log.info("--> Not received EOS on all links for STSXYTER #{:d} (ASIC {:d})".format(idx, sx_group[idx].chip_nr) )
                missingEOS = True
        idx += 1

    if True == missingEOS:
        raise Exception("Not received EOS for at least one enabled uplink")
    else:
        log.info("EOS OK on all links for all STSXYTER on this FEB")

    # Write found configuration:
    cfg = {'cdel': int(clk_average), 'ddel': del_results}
    filename = "dels_afck{:d}_crob{:d}_dlink{:d}.cfg".format( afck_idx, crob.id, dlink)
    fcfg = open(filename, "w")
    pickle.dump(cfg, fcfg)
    fcfg.close()


def fast_sync(afck_idx, sx_group):
    assert isinstance(sx_group, sts_xyter_group)

    if( 0 == len(sx_group) ):
        log.info("### Doing nothing on Downlink #{:d} as no active ASIC ###".format( sx_group.dlink ) )
        return

    crob = sx_group.crob
    clock = sx_group.clock
    dlink = sx_group.dlink

    # get mask of currently enabled elinks
    elink_mask = crob.hw.getNode(crob.dev + ".link_mask[0]").read()
    crob.hw.dispatch()
    reg = crob.hw.getNode(crob.dev + ".link_mask[1]").read()
    crob.hw.dispatch()
    elink_mask = int(elink_mask)  # to use python wide integers we have to convert from ipbus type
    elink_mask |= int(reg) << 32

    filename = "dels_afck{:d}_crob{:d}_dlink{:d}.cfg".format( afck_idx, crob.id, dlink)
    fcfg = open(filename, "r")
    cfg = pickle.load(fcfg)
    fcfg.close()
    clk_del = cfg['cdel'] #[0]
    data_dels = cfg['ddel']
    log.info("\nPerforming fast synchronisation for CROB #{:d} on downlink #{:d}".format(crob.id, dlink))
    log.info("Clock delays = {}".format(clk_del))
    log.info("Data delays = {}".format(data_dels))

    crob.gbtx_clock_phase_set(0, clock, clk_del)
    # Wait until Clock delay gets locked
    idx = 0
    for sx in sx_group:
        for i in range(0, len(sx.ulink_map)):
            ul = sx.ulink_map[i]
            gbtx_id = ul // 14
            elink = ul % 14 * 4  # this calculation comes from linear mapping in FPGA gateware
            crob.gbtx_elink_phase_set(gbtx_id, elink, data_dels[idx][i])
        idx += 1

    # Send EOS
    sx_group.enc_mode.write(MODE_EOS)
    # Now verify correct operation:
    idx = 0
    missingEOS = False
    for sx in sx_group:
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(SOS_CLEAR | EOS_CLEAR | K28_1_CLEAR | K28_5_CLEAR)
        for i in range(0, len(sx.DetClears)):
            sx.DetClears[i].write(0)
        time.sleep(0.01)
        all_eos = True
        test = []
        for i in range(0, len(sx.DetOuts)):
            r = sx.DetOuts[i].read()
            ulink = sx.ulink_map[i]
            r1 = (r & EOS_DET_STABLE1) or (elink_mask & (0x1 << ulink) == 0)
            if r1 == 0:
                all_eos = False
                log.info("Not received EOS for STSXYTER #{:d}".format(idx))
            test.append(r1 != 0)
        log.debug("STSXYTER #{:d} eos test result: {}".format(idx, test))
        idx += 1
        if all_eos is False:
            log.info("Not received EOS on all links for STSXYTER #{:d} (ASIC {:d})".format(idx, sx_group[idx].chip_nr) )
            missingEOS = True

    if True == missingEOS:
        raise Exception("Not received EOS for at least one enabled uplink")
    else:
        log.info("EOS OK on all links for all STSXYTER on this FEB")
