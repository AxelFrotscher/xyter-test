import logging as log
import uhal


class dev(object):
    def __init__(self, id, manager):
        self.hw = manager.getDevice(id)

    def write(self, reg_id, val):
        self.hw.getNode(reg_id).write(val)
        self.hw.dispatch()

    def read(self, reg_id):
        tmp = self.hw.getNode(reg_id).read()
        self.hw.dispatch()
        return tmp

    def write_verbose(self, id, val):
        log.debug("Write {} {} {:#x}".format(self.hw.id(), id, val))
        self.write(id, val)

    def read_verbose(self, id):
        tmp = self.read(id)
        log.debug("Read {} {} {:#x}".format(self.hw.id(), id, tmp))
        return tmp


def configure_tDPB(tdpb):
    # reset clock,
    tdpb.write_verbose("ts_dev.ctrl_rst", 0x2)
    # remove reset
    # fore local clock soure
    tdpb.write_verbose("ts_dev.ctrl_rst", 0xc)

    tdpb.write_verbose("ts_dev.ctrl_pps", 0)
    tdpb.write_verbose("ts_dev.ctrl_pps.pps_halt", 0)
    # this reg starts pps "now", other one starts pps on reference pps (if im not mistaked)
    tdpb.write_verbose("ts_dev.ctrl_pps.pps_start", 1)
    # external reference
    tdpb.write_verbose("ts_dev.ctrl_pps.pps_ext_Nint", 0)
    # start pps when external pps arrives
    tdpb.write_verbose("ts_dev.ctrl_pps.pps_event_listen", 0)

    # dunno?
    tdpb.write_verbose("ts_dev.ctrl_pps_cmpVal", 0x303)


def configure_eDPB(edpb):

    # reset clock
    edpb.write_verbose("ts_dev.ctrl_rst", 0x2)
    # remove reset clock
    # keep automatic selection of reference clock source
    edpb.write_verbose("ts_dev.ctrl_rst", 0x0)
    # dont halt
    edpb.write_verbose("ts_dev.ctrl_pps.pps_halt", 0)
    # this reg starts pps "now", other one starts pps on reference pps (if im not mistaked)
    edpb.write_verbose("ts_dev.ctrl_pps.pps_start", 0)
    # external reference
    edpb.write_verbose("ts_dev.ctrl_pps.pps_ext_Nint", 1)
    # start pps when external pps arrives
    edpb.write_verbose("ts_dev.ctrl_pps.pps_event_listen", 1)

    # dunno?
    edpb.write_verbose("ts_dev.ctrl_pps_cmpVal", 0x303)


def __main__():
    manager = uhal.ConnectionManager("file://boards.xml")
    edpb = dev("eDPB", manager)
    tdpb = dev("tDPB", manager)





