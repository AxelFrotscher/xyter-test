import logging as log
import ctypes
import time

# Minimun Tbeat frequency depends on phase noise in the system
# Our DPB is not so great, so let's make it as high as possible
HELPER_TARGET_FREQ = int(120e6 + 3e3)
MAIN_TARGET_FREQ = int(120e6)
# Phase offset is required in some clocking configurations to ensure enough
# hold margin in FPGA for data crossing [local] -> [TFC reference] clock domain
PHASE_OFFSET = 700  # measured in DMTD resolution units, so depends on Tbeat

logger = log.getLogger(__name__)


def _int32(n):
    """Helper function to convert python number to int32"""
    if n < 0:
        n += 2**32
    return n


class pll(object):
    class pll_part(object):

        def __init__(self, target, lock_thd, unlock_thd, initval=99999):
            self.value = initval
            self.value_hist = [initval] * 10

            self.target = target
            self.diff = initval

            self.lock = False
            self.lock_thd = lock_thd
            self.unlock_thd = unlock_thd

        def add_value(self, new):
            self.value_hist.pop()
            self.value_hist.insert(0, new)
            self.update()

        def update(self):
            self.value = sum(self.value_hist) / len(self.value_hist)
            self.diff = abs(self.value - self.target)
            if self.lock:
                self.lock = True if self.diff < self.unlock_thd else False
            else:
                self.lock = True if self.diff < self.lock_thd else False

    def __init__(self, local_freq, helper_freq):
        self.local_freq_target = int(local_freq)
        self.helper_freq_target = int(helper_freq)
        self.local_freq = pll.pll_part(self.local_freq_target, 1, 150)
        # the target phase offset is hardcoded in VHDL implementation
        self.local_phase = pll.pll_part(PHASE_OFFSET, 500, 1000)
        # there seems to be a problem with getting a strict frequency lock on boot_clk in AFCK board
        # my initial suspection is that boot_clk control traces are susceptible for noise pickup
        self.helper_freq = pll.pll_part(self.helper_freq_target, 1, 10)

        self.lock = False

    def update(self):
        self.local_freq.update()
        self.local_phase.update()
        self.helper_freq.update()
        self.lock = self.local_freq.lock and self.local_phase.lock and self.helper_freq.lock


class jitter_cleaner(object):

    def __init__(self, hw, dev):
        self.hw = hw
        self.dev = dev
        self.pll = pll(MAIN_TARGET_FREQ, HELPER_TARGET_FREQ)
        self.shutdown = False

    def configure(self):
        """
        Configure parameters of jitter cleaner PLLs, acquire control over I2C bus
        and start operation
        """
        self.hw.getNode(self.dev + ".controls.reset_clocking").write(0x1)
        self.hw.getNode(self.dev + ".controls.i2c_control_source").write(0x1)
        self.hw.getNode(self.dev + ".helper_target_frequency").write(HELPER_TARGET_FREQ)
        # these KI/KP settings were determined in lab or taken from other projects
        self.hw.getNode(self.dev + ".helper_kp").write(0)
        self.hw.getNode(self.dev + ".helper_ki").write(2 << 17)
        self.hw.getNode(self.dev + ".helper_cfg.tuning_dir").write(1)
        self.hw.getNode(self.dev + ".helper_cfg.lock_cond").write(3)
        self.hw.getNode(self.dev + ".helper_cfg.lock_thd").write(8)
        self.hw.getNode(self.dev + ".helper_cfg.ulock_thd").write(8)
        self.hw.getNode(self.dev + ".main_freq_kp").write(0x0)
        self.hw.getNode(self.dev + ".main_freq_ki").write(0x2F000000)
        self.hw.getNode(self.dev + ".main_freq2_kp").write(0x0)
        self.hw.getNode(self.dev + ".main_freq2_ki").write(0xFF)
        self.hw.getNode(self.dev + ".main_phase_kp").write(0xFFFF)
        self.hw.getNode(self.dev + ".main_phase_ki").write(0x1FF)
        self.hw.getNode(self.dev + ".main_phase_offset").write(_int32(PHASE_OFFSET))
        self.hw.getNode(self.dev + ".main_phase_avg").write(0x1)
        self.hw.getNode(self.dev + ".main_phase_trim").write(20000)  # with 3kHz Fbeat 40000 is full range
        self.hw.getNode(self.dev + ".main_cfg.tuning_dir_freq").write(0)
        self.hw.getNode(self.dev + ".main_cfg.tuning_dir_freq2").write(1)
        self.hw.getNode(self.dev + ".main_cfg.tuning_dir_phase").write(1)
        self.hw.getNode(self.dev + ".main_cfg.mode").write(0)
        self.hw.getNode(self.dev + ".main_cfg.lock_cond").write(3)
        self.hw.getNode(self.dev + ".main_cfg.lock_thd").write(8)
        self.hw.getNode(self.dev + ".main_cfg.ulock_thd").write(8)
        self.hw.getNode(self.dev + ".controls.reset_clocking").write(0x0)
        self.hw.dispatch()

    def monitor(self):
        """
        Monitor operation of jitter cleaner and switch between FREQ and PHASE tracking mode.
        Every change of tracking mode or lock state is logged.
        This function usually should be run in separate thread. It doesn't return, but can
        be killed by setting self.shutdown flag.
        """
        mode = 0  # 0 - FREQ, 1 - PHASE
        prev_mode = 0
        full_lock = False
        while not self.shutdown:
            time.sleep(0.001)
            # read current status
            local_freq = self.hw.getNode(self.dev + ".local_freq").read()
            helper_freq = self.hw.getNode(self.dev + ".helper_freq").read()
            local_phase = self.hw.getNode(self.dev + ".phase_diff").read()
            self.hw.dispatch()

            # update PLL statistics
            # phase_diff is actually int32, so we have to convert it
            self.pll.local_freq.add_value(int(local_freq))
            self.pll.helper_freq.add_value(int(helper_freq))
            self.pll.local_phase.add_value(ctypes.c_int32(local_phase).value)
            self.pll.update()

            # if both frequency generators are frequency-locked, we can switch to phase tracking mode
            if (mode == 0) and self.pll.local_freq.lock and self.pll.helper_freq.lock:
                self.hw.getNode(self.dev + ".main_cfg.mode").write(1)
                self.hw.dispatch()
                mode = 1
                log.info("PLL now working in PHASE mode")
            # if at least one generator lost frequency lock, let's switch back to freq tracking mode
            elif (mode == 1) and (not self.pll.local_freq.lock or not self.pll.helper_freq.lock):
                self.hw.getNode(self.dev + ".main_cfg.mode").write(0)
                self.hw.dispatch()
                mode = 0
                log.info("PLL now working in FREQ mode")

            if (prev_mode != mode) or (full_lock != self.pll.lock):
                prev_mode = mode
                full_lock = self.pll.lock
                log.info(time.strftime("%X"))
                log.info("Helper freq = {:d} Hz, diff = {:d} Hz".format(self.pll.helper_freq.value, self.pll.helper_freq.diff))
                log.info("Local freq = {:d} Hz, diff = {:d} Hz".format(self.pll.local_freq.value, self.pll.local_freq.diff))
                log.info("Local phase = {:d}, diff = {:d}".format(self.pll.local_phase.value, self.pll.local_phase.diff))
                log.info("PLL is " + "locked" if self.pll.lock else "NOT locked")
