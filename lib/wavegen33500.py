import time
import scpi

class wavegen33500(object):
  def __init__(self, host='10.203.0.89'):
    SCPI = scpi.SCPI
    print "connect to waveform generator at ", host
    self.wvgen = SCPI(host, timeout=1)

    # --- Note: no setter functioncs yet for the parameters below
    self.sample_rate = 5000000   # samples / sec    # 5000000

    self.trg_period = 0.0001     # delay in s between individual triggers (uses time.sleep)
    self.par_delay = 4           # time in us at high voltage level before ramping down
    self.decay_time = 10         # time in us to ramp down to 0V

    self.n_rep_wave = 1          # number of repetitions of the generated waveform (for a single trigger)
    # ------------

    self.sample_period = 1e6 / self.sample_rate   # period in usec
    print "sample Period ", self.sample_period

    self.pinv = 0       # Set pinv = 1 for negative going waveform

    self.amp_cal_cap = 1e-13     # sts-xyter internal test capacitance in F
    self.amp_cal_divider = 1   # factor of ampcal voltage divider: internal 1k1Ohm, example: factor 10 with external 9k9Ohm
    self.v2q =  1e-15 / self.amp_cal_cap
    self.sig_vext_scale = self.v2q * self.amp_cal_divider

    self.v_ampcal_limit = 1.2  # ToDO: check limit
    self.v_ext_limit = 3.   # ToDo: check limit

    self.v_thr = 0

  def conf_sig_gen(self, amp_cal_divider=1, amp_cal_cap=1e-13):
    print "set test voltage downscale factor to ", amp_cal_divider
    print "set test capacitance to: ", amp_cal_cap
    self.amp_cal_cap = amp_cal_cap     # sts-xyter internal test capacitance in F
    self.amp_cal_divider = amp_cal_divider   # factor of ampcal voltage divider: internal 1k1Ohm, example: factor 10 with external 9k9Ohm
    self.v2q =  1e-15 / self.amp_cal_cap
    self.sig_vext_scale = self.v2q * self.amp_cal_divider


  def conf_generator(self, n_rep_wave=1, pinv=0):
    cmd_srat = "SOUR1:FUNC:ARB:SRAT " + "{0:d}".format(self.sample_rate)
    self.wvgen.write('OUTP 0')
    self.wvgen.ask('SYST:ERR?')

    self.wvgen.write('*RST')
    self.wvgen.write('SOUR1:DATA:VOL:CLE')

    #a.write('MMEM:STOR:DATA1 "INT:\myarb.arb".')

    self.wvgen.write(cmd_srat)   # 1 MHz sampling; what is max --> 250 MSa/s ??
    #a.write('SOUR1:FUNC:ARB:SRAT 5e6')   # 1 MHz sampling; what is max --> 250 MSa/s ??

    self.wvgen.write('SOURCE1:VOLT:OFFSET 0.2')

    self.wvgen.write('FUNC:ARB:FILT OFF')
    self.wvgen.write('OUTP:LOAD INF')
    #self.wvgen.write('OUTP:LOAD INF')


    self.wvgen.write('SOUR1:BURS:MODE TRIG')
    self.wvgen.write('SOUR1:BURS:NCYC 1')
    self.wvgen.write('TRIG:SOUR BUS')
    self.wvgen.write('SOUR1:BURS:STAT ON')    # enable burst mode

    self.wvgen.write('SOUR1:DATA:VOL:CLE')

  def conf_v(self, voltage):
    # check proper range
    voltage = voltage/1000.
    self.set_V(voltage)

  def conf_vfromQ(self, charge):
    voltage = charge * self.sig_vext_scale
    self.set_V(voltage)

  def set_V(self, v_max):
    cmd_volt = "SOUR1:VOLT " + "{0:.4f}".format(v_max)
    self.wvgen.write(cmd_volt)
    print cmd_volt
    cmd_offset = "SOURCE1:VOLT:OFFSET " + "{0:.4f}".format(self.v_thr)
    self.wvgen.write(cmd_offset)


  def set_VThr(self, vreft_val):
    v_thr = (vreft_val - 32) * 0.01 + 1
    cmd_offset = "SOURCE1:VOLT:OFFSET " + "{0:.4f}".format(v_thr)
    self.v_thr = v_thr
    self.wvgen.write(cmd_offset)
    print cmd_offset

  def set_pinv(self, value):
    self.pinv = value
    print "set pinv to ", self.pinv

  def conf_polarity(self, pstr):
    if pstr=="e" :
      self.set_pinv(1)
    elif pstr=="h":
      self.set_pinv(0)
    else:
      print "no valid polarity setting (should be e or h). Polarity unchanged at: ", self.pinv

  def conf_wf_single(self):
    # generate a single test pulse
    #  i.e. rise to defined voltage, stay, ramp to 0V
    wv = " .0, "
    v_act = 1
    if ( self.pinv == 1 ):
      v_act = -1 * v_act
    n_hold = int(self.par_delay / self.sample_period)
    print "n_hold  ",n_hold
    for j in range(0,n_hold):
      sv = " {0:.3f},".format(v_act)
      wv = wv + sv

    n_decay = int(self.decay_time / self.sample_period)
    print "n_decay  ",n_decay
    decay_step = 1 / float(n_decay)

    for i in range(0,n_decay):
      v_dec = (1 - i * decay_step)
      if ( self.pinv == 1 ):
        v_dec = -1 * v_dec
      sv = " {0:.3f},".format(v_dec)
      wv = wv + sv

    cmd_arb = "DATA:ARB myArb,"
    for i in range(0, self.n_rep_wave):
      cmd_arb = cmd_arb + wv + " .0, .0,"
    cmd_arb = cmd_arb + " .0, .0, .0"
    print cmd_arb
    print "\n"
    self.wvgen.write(cmd_arb)

    self.wvgen.write('*WAI')
    self.wvgen.write('SOUR1:FUNC:ARB myarb')
    self.wvgen.write('SOUR1:FUNC ARB')

  def output_enable(self):
    self.wvgen.write('OUTPUT1 ON')
    self.wvgen.write('OUTPUT2 ON')

  def output_disable(self):
    self.wvgen.write('OUTPUT1 OFF')
    self.wvgen.write('OUTPUT2 OFF')


  def gen_trg(self, n_trg):
    print "Start triggering...\n"

    for i in range(0,n_trg):
      self.wvgen.write('*TRG')     # a.write('TRIG')
      time.sleep(self.trg_period)           # 0.0001 without sleep approx. 1.3 kHz rate
    #self.wvgen.write('OUTPUT1 OFF')

  def set_trigger_delay_ch1_ns( self, delay):
    cmd_del = "TRIG1:DEL " + "{0:d}e-9".format(delay)
    print cmd_del
    self.wvgen.write(cmd_del)
