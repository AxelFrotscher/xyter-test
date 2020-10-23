#!/usr/bin/python
import uhal
import sys
import pickle
import time
import struct

import logging
sys.path.append("../../../lib")
import global_dev_ctrl as gdc
import flim_dev_ctrl as fdc
import sts_xyter_dev_ctrl as sxdc

import sts_xyter_settings as settings
from os import path
#Below we set active links
# 1 - link is working
# 0 - we simulate, that the link is broken
LINK_BREAK = 0b00001
LINK_ASIC =  0b00001

log = logging.getLogger()
# This is a global level, sets the miminum level which can be reported
log.setLevel(logging.WARNING)
sh = logging.StreamHandler(sys.stderr)
sh.setLevel(logging.INFO)
log.addHandler(sh)
fh = logging.FileHandler("./logs/" + sys.argv[0].replace('py', 'log'), 'w')
fh.setLevel(logging.WARNING)
fmt = logging.Formatter('[%(levelname)s] %(message)s')
fh.setFormatter(fmt)
log.addHandler(fh)

uhal.setLogLevelTo(uhal.LogLevel.WARNING)
manager = uhal.ConnectionManager( settings.xml_filename )

hw = []
for edpb in settings.edpb_names:
  hw.append( manager.getDevice( edpb ) )

sts_com  = []
flims    = []
afck_id  = []
afck_mac = []
sts_ifaces = [[]]
for edpb_idx in range( 0, len(hw) ):
  sts_ifaces.append( [] )

  sts_com.append( sxdc.sts_xyter_com_ctrl( hw[ edpb_idx ], "sts_xyter_dev") )
  flims.append(   fdc.flim_dev_ctrl(       hw[ edpb_idx ], "flim_ctrl_dev") )
  sts_com[ edpb_idx ].read_public_dev_info()

  afck_id.append( gdc.get_afck_id(   hw[ edpb_idx ], "global_dev") )
  afck_mac.append( gdc.get_afck_mac( hw[ edpb_idx ], "global_dev") )
  log.info("\nAFCK ID:  0x%04x", afck_id[ edpb_idx ] )
  log.info("\nAFCK MAC: %s",     afck_mac[ edpb_idx ] )

  # iface_no: xyter_addr
  for i in range(0, sts_com[ edpb_idx ].interface_count()):
    if settings.iface_active[ edpb_idx ][i] == 1:
      sts_ifaces[edpb_idx].append( sxdc.sts_xyter_iface_ctrl( sts_com[ edpb_idx ], i, settings.sts_addr_map[ edpb_idx ][i], afck_id[ edpb_idx ] ) )

def input_float(prompt):

  while True:
    try:
      return float(raw_input(prompt))
    except ValueError:
      print('That is not a valid current')

def config( sts ):

  # --------------AFE Registers -----------------
  print "\nFull set of registers for the AFE. Typical values\n"
  print "------------------ooooOOOOOoooo-------------------"

  for ch in range (ch_min, ch_max):
    for d in range (d_min, d_max):
      n = 2 * d + 1
      sts.write_check(ch, n, 128)
    sts.write_check(ch, 63, 144)
    sts.write_check(ch, 65, 244 - 16 * much_modifier)
    sts.write_check(ch, 67, 36)

  csa_in = 31
  #vref_t = 186

  sts.write_check(130, 0, csa_in)   #Typ: 31, Max: 63
  sts.write_check(130, 1, 63 + 64 * much_modifier)   #Typ value for Ileak = 0nA
  sts.write_check(130, 2, 163)   #electrons: 131, holes: 163
  sts.write_check(130, 3, 31)   #Typ: 31, Max: 63
  sts.write_check(130, 4,  0)
  sts.write_check(130, 5,  0)      # 0
  sts.write_check(130, 6, 32)   #Typ: 32, Max: 63
  sts.write_check(130, 7, thr2_glb)
  sts.write_check(130, 8, 22)  # useless, gets overwritten
  sts.write_check(130, 9, 58)  # useless, gets overwritten
  #sts.write_check(130,10, vref_t & 0x80 + 0x40)   # enables vrefT + get same range as for 2.0
  if smx2_ver == 0:
    sts.write_check(130, 10, vref_t)   # enables vrefT + get same range as for 2.0
  elif smx2_ver == 1:
    sts.write_check(130, 10, 128)
    sts.write(130, 18, 0x40 + (vref_t&0x3f))  # hardcoded vref_t range = b001 which is coarsest range
  sts.write_check(130, 11, 64)
  sts.write_check(130, 12, 30)
  sts.write_check(130, 13, csa_in)   #Typ: 31, Max: 63
  sts.write_check(130, 14, 27)   #Typ: 27, Max: 63
  sts.write_check(130, 15, 27)   #Typ: 27, Max: 63
  sts.write_check(130, 16, 88)
  #sts.write(130, 17,  0) # Set new Vref Fast polarity to 0 to get same as for 2.0

  for i in range(3, 14):
    sts.write_check(192, i, 0x0)

  print rdch, ", 63,", sts.read(rdch, 63 ) & 0xff
  print rdch, ", 65,", sts.read(rdch, 65 ) & 0xff
  print rdch, ", 67,", sts.read(rdch, 67 ) & 0xff

  print "\nReading the re ASIC registers\n"
  print "ch selected to check-up ASIC mode: ", rdch, '\n'
  print str(rdch), " , 63, ", '{:5d}'.format(sts.read(rdch, 63) & 0xff)
  print str(rdch), " , 65, ", '{:5d}'.format(sts.read(rdch, 65) & 0xff)

  print "\nASIC analog registers:\n"

  print "130,  0, ", sts.read(130, 0) & 0xff
  print "130,  1, ", sts.read(130, 1) & 0xff
  print "130,  2, ", sts.read(130, 2) & 0xff    # bit 5 is polarity:
  print "130,  3, ", sts.read(130, 3) & 0xff
  print "130,  4, ", sts.read(130, 4) & 0xff # test pulse Recommended value between 80-200
  print "130,  5, ", sts.read(130, 5) & 0xff      # SHslow shapin gtime and calib pulse group
  print "130,  6, ", sts.read(130, 6) & 0xff
  print "130,  7, ", sts.read(130, 7) & 0xff
  print "130,  8, ", sts.read(130, 8) & 0xff    # Vref_N   def 31
  print "130,  9, ", sts.read(130, 9) & 0xff    # Vref_P   def 48
  print "130, 10, ", sts.read(130, 10) & 0xff      # Vref_T    def 188
  print "130, 11, ", sts.read(130,11 ) & 0xff      # Cal_strobe_dlm and global_gate
  print "130, 12, ", sts.read(130,12 ) & 0xff
  print "130, 13, ", sts.read(130,13 ) & 0xff
  print "130, 14, ", sts.read(130,14 ) & 0xff
  print "130, 15, ", sts.read(130,15 ) & 0xff
  print "130, 16, ", sts.read(130,16 ) & 0xff
  #print "130, 17, ", sts.read(130,17 ) & 0xff
  #print "130, 18, ", sts.read(130,18 ) & 0xff
  #print "130, 20, ", sts.read(130,20 ) & 0xff
  #print "130, 21, ", sts.read(130,21 ) & 0xff
  #print "130, 22, ", sts.read(130,22 ) & 0xff

  print "\nASIC file registers: \n"

  print "192,  1  ", sts.read(192, 1) & 0xff
  print "192,  2  ", sts.read(192, 2) & 0xff
  print "192,  3  ", sts.read(192, 3) & 0xff

  # disable all channels
  for i in range (4, 13):
  #  print "set mask register ", i
    print "192,", i, "  ", sts.read(192, i) & 0xff            # 0x3fff
  print "192, 13,", sts.read(192, 13) & 0xff            # 0xf

  print "192, 14, ", sts.read(192, 14) & 0xff
  print "192, 15, ", sts.read(192, 15) & 0xff
  print "192, 18, ", sts.read(192, 18) & 0xff
  print "192, 19, ", sts.read(192, 19) & 0xff
  print "192, 20, ", sts.read(192, 20) & 0xff
  print "192, 22, ", sts.read(192, 22) & 0xff
  print "192, 23, ", sts.read(192, 23) & 0xff
  print "192, 24, ", sts.read(192, 24) & 0xff
  print "192, 25, ", sts.read(192, 25) & 0xff
  print "192, 26, ", sts.read(192, 26) & 0xff
  print "192, 27, ", sts.read(192, 27) & 0xff
  print "192, 28, ", sts.read(192, 28) & 0xff
  print "192, 29, ", sts.read(192, 29) & 0xff
  print "192, 30, ", sts.read(192, 30) & 0xff
  print "192, 31, ", sts.read(192, 31) & 0xff
  print "192, 32, ", sts.read(192, 32) & 0xff
  print "192, 33, ", sts.read(192, 33) & 0xff

  # Here insert a break asking to measure the chip current.

def get_trim_adc(sts, pol_val):

  # ------------------------ pol -------------------------------------
  pol = pol_val

  if (pol == 1):
    sts.write_check(130, 2, 163)   #  163 holes     131 electrons
    print "\n____HOLES MODE____\n"

    print "......Setting ADC reference potentials (HOLES) ......\n"

    sts.write(130, 8, vref_n_h)
    sts.write(130, 9, vref_p_h)
    if smx2_ver == 0:
      sts.write_check(130,10, vref_t)   # enables vrefT + get same range as for 2.0
    elif smx2_ver == 1:
      sts.write_check(130, 10, 128)
      sts.write(130, 18, 0x40 + (vref_t & 0x3f))  # hardcoded vref_t range = b001 which is coarsest range

    #sts.write(130, 10, vref_t)
    #sts.write(130, 18, vref_t_r)
    #sts.write(130, 10, vref_t & 0x80 + 0x40)   # enables vrefT + get same range as for 2.0
    #sts.write(130, 18, vref_t & 0x3F + 0xC0 )   # get same range as for 2.0 + loads VREFT

    print " ADC Reference potentials"
    print "VRef_N: ",sts.read(130, 8) & 0xff
    print "VRef_P: ",sts.read(130, 9) & 0xff
    print "VRef_T: ",sts.read(130,10) & 0xff

    print "\n......Setting FAST disc reference potential (HOLES) ...... "
    sts.write(130, 7, thr2_glb)
    #sts.write(130, 17,  0) # Set new Vref Fast polarity to 0 to get same as for 2.0

    print "\nFAST Reference potentials"
    print "Thr2_global: ",sts.read(130, 7)

  elif (pol == 0):
    sts.write(130, 2, 131)   #  163 holes     131 electrons
    print "\n____ELECTRONS MODE____"
    print "\n......Setting ADC reference potentials (ELECTRONS)..... "

    sts.write(130, 8, vref_n_e)
    sts.write(130, 9, vref_p_e)
    if smx2_ver == 0:
      sts.write_check(130, 10, vref_t)   # enables vrefT + get same range as for 2.0
    elif smx2_ver == 1:
      sts.write_check(130, 10, 128)
      sts.write(130, 18, 0x40 + (vref_t & 0x3f))  # hardcoded vref_t range = b001 which is coarsest range
    #sts.write(130,10,vref_t)
  #sts.write(130,18,vref_t_r)
#    sts.write(130,10, vref_t & 0x80 + 0x40)   # enables vrefT + get same range as for 2.0
#    sts.write(130,18, vref_t & 0x3F + 0xC0 )   # get same range as for 2.0 + loads VREFT

    print "\n ADC Reference potentials"
    print "VRef_N: ",sts.read(130, 8)
    print "VRef_P: ",sts.read(130, 9)
    print "VRef_T: ",sts.read(130,10)

    print "\n......Setting FAST disc reference potential(ELECTRONS) ....\n"
    sts.write(130, 7,thr2_glb)

    print " FAST Reference potentials"
    print "Thr2_global: ",sts.read(130, 7)

  # -----------------------------------------------------------------

  print "\n................ Getting ADC Trim Values ......................\n"

  # counters array for trim
  vpset = [0 for d in range (d_min, d_max)] # pulse height array for each discriminator
  vcnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]     # array for discriminator counters coarse
  fcnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]     # array for discriminator counters fine
  avg_cnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]  # smothed counter values from fine scan
  hh_cnt = [[0 for d in range(d_max)] for ch in range(ch_max)]					           # half maximun count values
  trim_coarse_low = [[0 for d in range(d_max)] for ch in range(ch_max)]					   # lower trim values before switching

  # setting vpset = [32]
  # Implemented linearily -> could it be not linearly to implemment nonlinearADC characteristics
  vp_d = ((amp_cal_max - amp_cal_min) / (d_max - d_min))# + 0.5 )    # + 0.5 Why ?     # Step in the pulse amplitud/trim
  print "vp_d :", float(vp_d)

  print "vpset: ",
  for d in range (d_min, d_max):
    vpset[d] = int(amp_cal_min + (d - d_min) * vp_d)
    print float(vpset[d]),

  d_counter = 0
  print_channel = 62
  # Loop over discriminators
  for d in range (d_min, d_max):
    disc = 61 - 2 * d
    count = 61 - 2 * d - 1
    vp = int(vpset[d])
    if (vp < amp_cal_min or vp > amp_cal_max):
      print "NOTE: Pulse amplitude should be in the range ...."
    sts.write(130, 4, vp)
    print "\n\nCalibration Pulse Amplitude: {0}, Discriminator {1}, Verbose"\
          "Channel {2}, Pulses: {3}".format(vp, d, print_channel, loop_max)

    itr = 0

    #Coarse loop over trim
    for tr in range (tr_min, tr_max, tr_coarse_step):
      # Loop over groups
      for grp in range (grp_min, grp_max):
        grp_shslow = ((shslowfs & 0x3) << 2 | (grp & 0x3)) # Included the slow shaper configuration (90,130,220,280ns)
        sts.write(130, 5, grp_shslow)
        #print " Selected Shaping time and group: " ,format(bin(sts.read(130,5))), "\n"

        # Loop over the channels of the group
        for ch in range(grp, ch_max, 4):
          sts.write(ch, disc, tr)

        # Reset ADC counters
        sts.write(192, 2, 32)
        #time.sleep(0.00001)
        sts.write(192, 2, 0)

      # multiple count loops
        for loop in range (0, loop_max):
          #Sending the signal to trigger pulses.
          sts.write(130, 11, 128)
          #time.sleep(0.004)
          sts.write(130, 11, 0)
        # loop to read counter
        cnt_val = 0
        for ch in range(grp, ch_max, 4):
          vcnt[ch][d][itr] = sts.read(ch, count) & 0xfff
          if(ch == print_channel):
            print "({0} {1})".format(tr, vcnt[ch][d][itr]),
            sys.stdout.flush()
            if((tr-tr_min)/tr_coarse_step == 10):
              print ""

      itr += 1  # here ends the loop over trim

    for ch in range(ch_min,ch_max):
      #trim_coarse_low[ch][d] = 0
      trim_coarse_low[ch][d] = -1
      itr = 0
      #print "ch", '{:4d}'.format(ch),
      coarse_flag = 0
      y_coarse_min = 0
      y_coarse_max = 0
      #if(ch == 0):
      #  print vcnt[ch][0][0:29]
      # the loop should include the tr_max
      for tr in range (tr_min, tr_max, tr_coarse_step):
        if (itr >= tr_coarse_range and coarse_flag == 0):
          if ((vcnt[ch][d][itr] >= cnt_max_coarse) and
               vcnt[ch][d][itr - tr_coarse_range] <= cnt_max_coarse): # WRONG TRIM direction! //Axel - -> +, <= -> <
            y_coarse_min = cnt_max_coarse - vcnt[ch][d][itr - tr_coarse_range]
            y_coarse_max = vcnt[ch][d][itr] - cnt_max_coarse
            trim_coarse_low[ch][d] = (tr if (y_coarse_min <= y_coarse_max)
                 else (tr + tr_coarse_step)) - (tr_coarse_range * tr_coarse_step
                       - tr_coarse_offset) # Searching range tr-25(35)
                 #else (tr - 1)) # Axel searching for previous step
            #print  '{:4d}'.format(itr), '{:4d}'.format(trim_coarse_low[ch][d]),
            if (trim_coarse_low[ch][d] < 0):
              trim_coarse_low[ch][d] = 0

            coarse_flag = 1
        itr += 1

    #fine loop over tri
    print "\nfine discriminator {0:2d}, Iterations {1:2d}, Pulses {2}"\
           .format(d, tr_i_fine_max, loop_max_fine)
    for  itr in range(0, tr_i_fine_max + 1):
      #print itr,
      #sys.stdout.flush()

      ## Loop over groups
      for grp in range (grp_min, grp_max):
        grp_shslow = ((shslowfs & 0x3) << 2 | (grp & 0x3)) # Included the slow shaper configuration (90,130,220,280ns)
        sts.write(130, 5, grp_shslow)
        #print " Selected Shaping time and group: " ,format(bin(sts.read(130,5))), "\n"

        # Loop over channels in group to set trim values
        for ch in range(grp, ch_max, 4):
          tr = trim_coarse_low[ch][d] + itr * tr_fine_step
          #print "ch: ", ch, " tr: " '{:4d}'.format(tr), "\n"
          sts.write(ch,disc,tr)

        ## Reset ADC counters
        sts.write(192, 2, 32)
        #time.sleep(0.00001)
        sts.write(192, 2, 0)

        ## multiple count loops
        for loop in range(0, loop_max_fine):
          sts.write(130, 11, 128)    # sending trigger pulses ()
          #time.sleep(0.004)
          sts.write(130, 11, 0)

        ## loop to read counter
        #cnt_val = 0
        for ch in range(grp, ch_max, 4):
          fcnt[ch][d][itr]= sts.read(ch, count) & 0xfff
          if(ch == print_channel):
            print "({0} {1})".format(trim_coarse_low[ch][d] + itr*tr_fine_step,\
                   fcnt[ch][d][itr]),
            sys.stdout.flush()
            if(itr > 0 and itr%9 == 0):
              print ""
        #print "\n"

    # Smooth fcnt -> This is not done here
    asum = 0
    isum = 0
    avg_max = 0.000
    avg_max_range = 5
    #logfile.write("the Half height counts condition")
    for ch in range(ch_min, ch_max):
      avg_max = 0
      for itr in range (tr_i_fine_max - avg_max_range, tr_i_fine_max):
          if (abs(fcnt[ch][d][itr] - loop_max_fine) > 0.1 * loop_max_fine):
            fcnt[ch][d][itr] = loop_max_fine
          avg_max += fcnt[ch][d][itr]      # Max value condition
      hh_cnt[ch][d] = (avg_max / avg_max_range / 2.)   # Condition for half height count

    # determining switching point for trim_final[ch][d]
    #logfile.write("Determining switching point for final trim")
    #for ch in range(ch_min,ch_max):
      trim_final[ch][d] = -1
      find_flag = 0
      y_min = 0
      y_max = 0
      for itr in range(0, tr_i_fine_max):
        #print '{:4d}'.format(avg_cnt[ch][d][itr]),
        if (itr > 0 and itr < (tr_i_fine_max - 1) and find_flag == 0):
          if ((fcnt[ch][d][itr] <= hh_cnt[ch][d]) and
              (fcnt[ch][d][itr + 1] >= hh_cnt[ch][d])):
            #print "   |   "
            y_max = fcnt[ch][d][itr + 1] - hh_cnt[ch][d]
            y_min = hh_cnt[ch][d] - fcnt[ch][d][itr]
            trim_final[ch][d] = trim_coarse_low[ch][d] + ((itr*tr_fine_step)
                                if (y_min <= y_max)
                                else (itr + 1) * tr_fine_step)
            find_flag == 1
      #print "\n"
  #logfile.close()
  return 0

def get_trim_fast(sts, pol_val):

  # ------------------------ pol -------------------------------------
  pol = pol_val

  if (pol == 1):
    sts.write(130, 2, 163)   #  163 holes     131 electrons
    print "\n____HOLES MODE____\n"
  elif (pol == 0):
    sts.write(130, 2, 131)   #  163 holes     131 electrons
    print "\n____ELECTRONS MODE____\n"

  # -----------------------------------------------------------------
  cnt = [[0 for thr in range(thr_max)] for ch in range (ch_max)]
  avg = [[0 for thr in range(thr_max)] for ch in range (ch_max)]
  hh  = [0 for ch in range (ch_max)]

  # cleaning lists

  sts.write_check(130, 7, thr2_glb)

  for ch in range (ch_min, ch_max):
    thr_i = 0
    for thr in range (thr_min, thr_max):
      cnt[ch][thr_i] = 0
      thr_i += 1

  thr_i = 0

  sts.write(130, 4, amp_cal_min)
  for thr in range (thr_min, thr_max):
    #print "disc_threshold: ", '{:3d}'.format(thr)
    sys.stdout.flush()
    # reseting counters
    sts.write(192, 2, 42)
    sts.write(192, 2, 0)
    for grp in range (grp_min, grp_max):
      sts.write(130, 5, grp)
      #print "group: ", '{:3d}'.format(grp)

      # setting disc. threshold
      for ch in range (grp, ch_max, 4):
        sts.write(ch, 67, thr)

      # reseting counters
      sts.write(192, 2, 32)
      sts.write(192, 2, 0)

      # generating npulses
      for n in range (npulses):
        sts.write(130, 11, 128)
        sts.write(130, 11, 0)

      # reading ch counters
      for ch in range (grp, ch_max, 4):
        #print "ch: ", '{:3d}'.format(ch),
        cnt[ch][thr_i] = sts.read(ch, 62) & 0xfff
        if(ch == 45):
          print "Ch {0} trim {1} cts {2} snt {3}"\
                 .format(ch, thr_i,cnt[ch][thr_i], npulses)
        #print '{:3d}'.format(cnt[ch][thr_i])
      sys.stdout.flush()
      #print "\n"
    thr_i += 1
    #print "\n"

  thr_i = 0
  thr_val_t = int(thr_max/thr_step)

  # ---------------------- Finding trim values -----------------------
  # -------------- Smoothing the  scurve and finding S-curves HH -------------
  for ch in range(ch_min, ch_max):
    thr_i = 0
    isum = 0
    asum = 0
    avg_max = 0
    avg_max_range = 5
    #print "ch: ", ch, " ",
    for thr in range(thr_min, thr_max, thr_step):
      if (thr <= thr_step):
        avg[ch][thr_i] = 0
      elif (thr >= thr_max - thr_step):
        avg[ch][thr_i] = 0
      else:
        # Wrong interpolation. Add: 4 *
        isum = cnt[ch][thr_i - 1] + 4 * cnt[ch][thr_i] + cnt[ch][thr_i + 1]
        asum = float(isum)
        avg[ch][thr_i] = int(asum / 3)

      if (thr >= thr_max - 6 * thr_step and thr <= thr_max - thr_step):
        if (abs(cnt[ch][thr_i] - npulses) > 0.1 * npulses):
          cnt[ch][thr_i] = npulses
        avg_max += cnt[ch][thr_i]
      thr_i += 1

    hh[ch] = int(avg_max / avg_max_range / 2)
    #print '{:3d}'.format(hh[ch])

  #print "\n------------ Final trim values ------------\n"
  for ch in range (ch_min, ch_max):
    thr_i = 0
    trim_final[ch][31] = -1
    find_flag = 0
    y_min = 0
    y_max = 0

    for thr in range (thr_min, thr_max, thr_step):
      if (thr > 0 and thr < thr_max - thr_step and find_flag == 0):
        #if (avg[ch][thr_i]<=hh[ch] and avg[ch][thr_i-1]<hh[ch] and avg[ch][thr_i+1]>= hh[ch]):
        if (cnt[ch][thr_i] <= hh[ch] and cnt[ch][thr_i + 1] >= hh[ch]):
          print  "|",
          y_max = cnt[ch][thr_i + 1] - hh[ch]
          y_min = hh[ch] - cnt[ch][thr_i]
          trim_final[ch][31] = (thr_i * thr_step) if (y_min <= y_max) \
                                                  else ((thr_i + 1) * thr_step)
          find_flag = 1
      thr_i += 1
    #print "\n"
  return 0

def  write_trim_file(sts, pol_val):

  filename_trim = ("trim_cal/trim_cal_"  + date + "_gsi_feb_c_89" + "_fast_" +
                   str(sts.read(130, 7) & 0xff) + "_adc_" +
                   str(sts.read(130, 9) & 0xff) + str(sts.read(130, 8) & 0xff) +
                   str(vref_t) + "" + str(amp_cal_min) + "_" + str(amp_cal_max))

  # ------------------------ pol -------------------------------------
  pol = pol_val

  if (pol == 1):
    print "\n____WRITING TRIMING FILE for HOLES ____\n"
    filename_trim = filename_trim + "_holes.txt"
  if (pol == 0):
    print "\n____WRITING TRIMING FILE for ELECTRONS ____\n"
    filename_trim = filename_trim + "_elect.txt"
  # -----------------------------------------------------------------

  trimfile = open(filename_trim, "w+")
  assert path.exists(filename_trim)

  print "\n\n"

  # writing trim values on file
  for ch in range (ch_min, ch_max):
    trimfile.write("ch:")
    trimfile.write('{:4d}'.format(ch))
    print "\nch: ", '{:3d}'.format(ch),
    for d in range(d_min,d_max+1):
      trimfile.write('{:5d}'.format(trim_final[ch][d]))
      print '{:3d}'.format(trim_final[ch][d]),
    trimfile.write("\n")
  trimfile.close()

  return 0

# ----------------- Writing and Reading register in the STS_XYTER ----------------------
# Executing commands
# ..................ooooo00000ooooo.................
## For now make a script only for the 1st ASIC on the 1st DPB
sts = sts_ifaces[0][0]
t0 = time.time()

sts.full_link_sync( LINK_BREAK )
sts.EncMode.write(sxdc.MODE_FRAME)

lmask = ((1 << 5) - 1) ^ LINK_BREAK
lmask |= (lmask << 5)

print " Setting the E-Link Mask register according to value provided initially "
print "E-LINK MASK " + bin(lmask), "\n"
#sts=stsxyter(15)
sts.emg_write(192, 25, lmask)
confirm = False
print " FULL and FAST Synchronization procedures are done... "
print " System set to send frames mode (w/r) -> MODE_FRAME"

# ---------------------------------------------------------------------------
#                         get trim: General Settings
# ---------------------------------------------------------------------------
smx2_ver = 1

# group range
grp_min = 0
grp_max = 4

# channel range
ch_min = 0
ch_max = 128

# discrim. range. Here fast disc is not included
d_min = 0
d_max = 31

# ................. ADC thr settings (0...137,d_min...d_max,thr) ..............
rdch = 63
itr = 0
tr_min = 60
tr_max = 180
tr_coarse_step = 5
tr_coarse_range = 1
tr_coarse_offset = -15
tr_fine_offset = -20
tr_i_fine_max = tr_coarse_step * tr_coarse_range - tr_fine_offset
tr_fine_step = 1

# .......................  ADC  Reference Voltages ...........................

vref_p_h = 63     # Ref. voltages Positive  (130, 9) (48)
vref_n_h = 22     # Ref. voltages Negative  (130, 8) (30)

vref_p_e = 52     # Ref. voltages Positive  (130, 9) (48)
vref_n_e = 22     # Ref. voltages Negative  (130, 8) (30)
vref_t = 128 + vref_p_h -1 # Ref. voltages Threshold (130,10)  (188) = 186
#vref_t_r = 186
# ................. FAST thr settings (0...137,d_min...d_max,thr) ..............

thr_min = 0
thr_max = 64
thr_step = 1
# ......................  FAST  Reference Voltages ............................

thr2_glb = 12

# .......................... CSA reference current ..........................
csa_in = 31

# .................. Calibration pulse settings .............................
much_modifier = 0
#amp_cal_min = 40  # (130,4, amp_cal)
#amp_cal_min = 15   # Test Axel for proper noise measurement
amp_cal_min = 10    # Test Axel for Si-Detector
amp_cal_max = 255.

loop_max = 30

loop_max_fine = 50
npulses = loop_max_fine

shslowfs = 0  # 0,..,3 for FS=90,160,220,280ns

# calibration range
cnt_min_coarse = int(loop_max * 0.30)
cnt_max_coarse = int(loop_max * 0.50)

# ---------------------------------------------------------------------------

print "\n--------------------------------- "
print "Number of test_pulses: ", loop_max
print "Reference levels for coarse switching, MIN: ", cnt_min_coarse
print "Reference levels for coarse switching, MIN: ", cnt_max_coarse
print " ---------------------------------\n "

# resets
print "Resetting front-end channels "
print "Resetting ADC counters"
print "Reset channel fifos"
sts.write(192, 2, 42)
time.sleep(0.00001)
sts.write(192, 2, 0)
sts.write(192, 3, 0)

print "......Setting CSAs Input currents...... "

sts.write(130, 0, csa_in)
sts.write(130, 13, csa_in)

print "\nCSA input current"
print "CSA_in front: ",sts.read(130, 0)
print "CSA in back: ",sts.read(130, 13)

date  = time.strftime("%y%m%d")
box_number = 6
asic_nr = 1
#list_arg = sys.argv
#cable_length = list_arg[1]

# Creating files for saving the trim information
filename_trim = ("trim_cal/trim_cal_" + date + "_asic_nr_" + str(asic_nr) +
                 "_fast_" + str(sts.read(130, 7)) + "_adc_" +
                 str(sts.read(130, 9) &0xff) + str(sts.read(130, 8) &0xff) +
                 str(sts.read(130, 10) &0xff) + "_vp_" + str(amp_cal_min) + "_" +
                 str(amp_cal_max))

logfile = open(filename_trim + "_log.txt", "w+")

trim_final = [[0 for d in range(d_max+1)] for ch in range(ch_max)]						# final trim values to storage

# ---------------------------------------------------------------------------------------
#                                     to run
# ---------------------------------------------------------------------------------------

# Calibration for holes (p-side)
pol = 1
config(sts)
time_start1 = time.time()
#get_trim_fast(sts,pol)
get_trim_adc(sts,pol)
get_trim_fast(sts,pol)
write_trim_file(sts,pol)
time_end1 = time.time()

date  = time.strftime("%y%m%d")

# Calibration for electrons (n-side)
#pol = 0
#time_end1 = 0
#time_start1 = time.time()
#get_trim_adc(sts,pol)
#read_write(500)
#time_end1 = time.time()
#get_trim_fast(sts,pol)
time_end2 = time.time()
#write_trim_file(sts,pol)

print "\n..............CALIBRATION FILES HAVE BEEN GENERATED ...............\n"
print " -------------------------- TIME SUMMARY ------------------------------ "
print "Starting time_ADC + FAST calib: ", str(time_start1)
print "Ending time_ADC + FAST calib: ", str(time_end1)
print "Duration time_(single polarity): ", str(time_end1 - time_start1), "\n"
print "Starting time FULL process: ", str(time_start1)
print "Ending time FULL process: ", str(time_end2)
print "Duration time FULL process: ", str(time_end2 - time_start1)

logfile.write(" -------------------------- TIME SUMMARY ------------------------------ ")
logfile.write("\n")
logfile.write("Starting time_ADC_calib: ")
logfile.write(str(time_start1))
logfile.write("\n")
logfile.write("Ending time_ADC_calib: ")
logfile.write(str(time_end1))
logfile.write("\n")
logfile.write("Duration time_ADC: ")
logfile.write(str(time_end1 - time_start1))
logfile.write("\n")
logfile.write("Starting time_FAST_calib: ")
logfile.write(str(time_end1))
logfile.write("\n")
logfile.write("Ending time_FAST_calib: ")
logfile.write(str(time_end2))
logfile.write("\n")
logfile.write("Duration time_FAST: ")
logfile.write(str(time_end2 - time_end1))
