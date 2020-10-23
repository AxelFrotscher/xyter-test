import uhal
import os
import sys
import pickle
import time
import struct
#from numba import jit

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
log.setLevel(logging.INFO)
sh = logging.StreamHandler(sys.stderr)
sh.setLevel(logging.INFO)
log.addHandler(sh)
fh = logging.FileHandler("./logs/" + sys.argv[0].replace('py', 'log'), 'w')
fh.setLevel(logging.INFO)
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
      sts_ifaces[edpb_idx].append(sxdc.sts_xyter_iface_ctrl(
          sts_com[edpb_idx], i, settings.sts_addr_map[ edpb_idx ][i],
          afck_id[ edpb_idx ]))

def get_trim_adc(sts, pol_val):

  # ------------------------ pol -------------------------------------
  pol = pol_val

  if (pol == 1):
    sts.write_check(130, 2, 163)   #  163 holes     131 electrons
    print "\n____HOLES MODE____\n"
    print "......Setting ADC reference potentials (HOLES) ...... \n"

    sts.write(130, 8, vref_n_h)
    sts.write(130, 9, vref_p_h)
    sts.write(130,10, vref_t)

    print " ADC Reference potentials"
    print "VRef_N: ", sts.read(130, 8)
    print "VRef_P: ", sts.read(130, 9)
    print "VRef_T: ", sts.read(130,10)
    
    print "\n......Setting FAST disc reference potential (HOLES) ...... \n"
    sts.write(130, 7, thr2_glb)

    print "FAST Reference potentials"
    print "Thr2_global: ", sts.read(130, 7)
  
  elif (pol == 0):
    sts.write(130, 2, 131)   #  163 holes     131 electrons
    print "\n____ELECTRONS MODE____"

    print "......Setting ADC reference potentials (ELECTRONS)..... "

    sts.write(130, 8, vref_n_e)
    sts.write(130, 9, vref_p_e)
    sts.write(130,10, vref_t)

    print "\n ADC Reference potentials"
    print "VRef_N: ", sts.read(130, 8)
    print "VRef_P: ", sts.read(130, 9)
    print "VRef_T: ", sts.read(130,10)

    print "\n......Setting FAST disc reference potential(ELECTRONS) ....\n"
    sts.write(130, 7, thr2_glb)

    print "\n FAST Reference potentials"
    print "Thr2_global: ", sts.read(130, 7)

  # -----------------------------------------------------------------

  print "\n............... Getting ADC Trim Values .....................\n"

  # counters array for trim
  vpset = [0 for d in range (d_min,d_max)]   									# array of pulse heights for each discriminator
  vcnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]            		# array for discriminator counters coarse
  fcnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]  	                	# array for discriminator counters fine
  avg_cnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]   		        # smothed counter values from fine scan
  hh_cnt = [[0 for d in range(d_max)] for ch in range(ch_max)]					        	# half maximun count values
  trim_coarse_low = [[0 for d in range(d_max)] for ch in range(ch_max)]					        # lower trim values before switching

  # setting vpset = [32]
  # Implemented linearily -> could it be not linearly to implemment nonlinearADC characteristics
  vp_d = ((amp_cal_max - amp_cal_min) / (d_max - d_min))# + 0.5 )    # + 0.5 Why ?     # Step in the pulse amplitud/trim
  print "vp_d :", float(vp_d)

  print "vpset:",
  for d in range (d_min, d_max):
    vpset[d] = int(amp_cal_min + (d - d_min) * vp_d)
    print float(vpset[d]),

  d_counter = 0
  # Loop over discriminators
  for d in range (d_min, d_max):
    disc = 61 - 2 * d
    count = 61 - 2 * d - 1
    vp = int(vpset[d])
    if (vp < amp_cal_min or vp > amp_cal_max):
      print "NOTE: Pulse amplitude should be in the range ...."
    sts.write(130, 4, vp)
    print "\nCalibration Pulse Amplitude set to: ", vp

    itr = 0

    #Coarse loop over trim
    for tr in range (tr_min, tr_max, tr_coarse_step):
      #print "Discriminator number:   " , d, "  Set_trim:   ", tr, "\n"
      #if tr<0 or tr>255:
        #print "NOTE: Trim out of range, should be between (0-255) ....", tr, "\n"

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
          vcnt[ch][d][itr]= sts.read(ch, count)

      itr += 1  # here ends the loop over trim

    # Finding coarse switching point from vcnt[ch][d][tr]
    #print "............Coarse switching.........."
    #logfile.write(" ............Coarse switching..........\n")
    for ch in range(ch_min, ch_max):
      #trim_coarse_low[ch][d] = 0
      trim_coarse_low[ch][d] = -1
      itr = 0
      #print "ch", '{:4d}'.format(ch),
      coarse_flag = 0
      y_coarse_min = 0
      y_coarse_max = 0
      print vcnt[ch][0][:]
      for tr in range (tr_min, tr_max, tr_coarse_step):   # the loop should include the tr_max
        if (itr >= tr_coarse_range and coarse_flag == 0):
          if ((vcnt[ch][d][itr] >= cnt_max_coarse) and 
               vcnt[ch][d][itr+tr_coarse_range] <= cnt_max_coarse):  # Axel - -> +
            y_coarse_min = cnt_max_coarse - vcnt[ch][d][itr + tr_coarse_range] #Axel - -> +
            y_coarse_max = vcnt[ch][d][itr] - cnt_max_coarse
            trim_coarse_low[ch][d] = (
                tr if (y_coarse_min <= y_coarse_max) 
                   else (tr + tr_coarse_step)) - (tr_coarse_range * 
                         tr_coarse_step - tr_coarse_offset) # Searching range tr-25(35)
            #print  '{:4d}'.format(itr), '{:4d}'.format(trim_coarse_low[ch][d]),
            if (trim_coarse_low[ch][d] < 0):
              trim_coarse_low[ch][d] = 0

            coarse_flag = 1
        itr += 1
    #print "\n"

    #fine loop over tr
    print "fine_disc", '{:2d}'.format(d), " ", '{:2d}'.format(tr_i_fine_max),\
          "Iterations...",
    sys.stdout.flush()
    for itr in range(0, tr_i_fine_max + 1):
      print itr,
      sys.stdout.flush()
     
      ## Loop over groups
      for grp in range (grp_min, grp_max):
        grp_shslow = ((shslowfs & 0x3) << 2 | (grp & 0x3)) # Included the slow shaper configuration (90,130,220,280ns)
        sts.write(130, 5, grp_shslow)
        #print " Selected Shaping time and group: " ,format(bin(sts.read(130,5))), "\n"

        # Loop over channels in group to set trim values
        for ch in range(grp, ch_max, 4):
          tr = trim_coarse_low[ch][d] + itr * tr_fine_step
          #print "ch: ", ch, " tr: " '{:4d}'.format(tr), "\n"
          sts.write(ch, disc, tr)

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
          fcnt[ch][d][itr] = sts.read(ch, count)

    # Smooth fcnt -> This is not done here
    asum = 0
    isum = 0
    avg_max = 0.000
    avg_max_range = 5
    #logfile.write("the Half height counts condition")
    for ch in range(ch_min, ch_max):
      avg_max = 0
      for itr in range (tr_i_fine_max - avg_max_range, tr_i_fine_max):
        #avg_cnt[ch][d][itr] = fcnt[ch][d][itr]
        #if (itr>=(tr_i_fine_max-avg_max_range) and (itr<(tr_i_fine_max))):
          if (abs(fcnt[ch][d][itr] - loop_max_fine) > 0.1 * loop_max_fine):
            fcnt[ch][d][itr] = loop_max_fine
          avg_max += fcnt[ch][d][itr]      # Max value condition
      hh_cnt[ch][d] = (avg_max/avg_max_range / 2.)   # Condition for half height count
      #print "ch:", '{:4d}'.format(ch), "    disc: ", '{:3d}'.format(d), "   hh_cnt: ", '{:4f}'.format(hh_cnt[ch][d]), "\n"
    
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
            trim_final[ch][d] = trim_coarse_low[ch][d] + ((itr*tr_fine_step) if (y_min<=y_max) else (itr+1)*tr_fine_step)
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

  sts.write(130, 4, amp_cal_min + 20)
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
        cnt[ch][thr_i] = sts.read(ch, 62)
        #print '{:3d}'.format(cnt[ch][thr_i])
      sys.stdout.flush()
      #print "\n"
    thr_i += 1
    #print "\n"

  thr_i = 0
  
  #fscanfile.close()
  thr_val_t = int(thr_max/thr_step)

  # ---------------------- Finding trim values -----------------------
  # -------------- Smoothing the  scurve and finding S-curves HH -----------------
  for ch in range(ch_min, ch_max):
    thr_i = 0
    isum =0
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
        isum = cnt[ch][thr_i - 1] + cnt[ch][thr_i] + cnt[ch][thr_i + 1]
        asum = float(isum)
        avg[ch][thr_i] = int(asum / 3)

      if (thr >= thr_max - 6 * thr_step and thr < thr_max - thr_step):
        if (abs(cnt[ch][thr_i] - npulses) > 0.1 * npulses):
          cnt[ch][thr_i] = npulses
        avg_max += cnt[ch][thr_i]
      thr_i += 1

    hh[ch] = int(avg_max / avg_max_range / 2)
    #print '{:3d}'.format(hh[ch])

  #print "\n------------ Final trim values ------------\n "
  for ch in range (ch_min, ch_max):
    thr_i = 0
    trim_final[ch][31] = -1
    find_flag = 0
    y_min = 0
    y_max = 0

    for thr in range (thr_min, thr_max, thr_step):
      if (thr > 0 and thr < thr_max - thr_step and find_flag == 0):
        #if (avg[ch][thr_i]<=hh[ch] and avg[ch][thr_i-1]<hh[ch] and avg[ch][thr_i+1]>= hh[ch]):
        if (cnt[ch][thr_i] <= hh[ch]  and cnt[ch][thr_i + 1] >= hh[ch]):
          print  "|",
          y_max = cnt[ch][thr_i + 1] - hh[ch]
          y_min = hh[ch] - cnt[ch][thr_i]
          trim_final[ch][31] = (thr_i * thr_step) if (y_min <= y_max) \
                                                  else ((thr_i + 1) * thr_step)
          find_flag = 1
      thr_i += 1
  return 0

def  write_trim_file(sts, pol_val):
 
  filename_trim = ("trim_cal/trim_cal_" + date + "_box_" + str(box_number) + 
                   "_asic_sn_" + str(asic_serial_nr) + "_fast_" + 
                   str(sts.read(130, 7)) + "_adc_" + str(sts.read(130, 9)) + 
                   str(sts.read(130, 8)) + str(sts.read(130, 10)) + "_vp_" + 
                   str(amp_cal_min) + "_" + str(amp_cal_max))

  # ------------------------ pol -------------------------------------
  pol = pol_val

  if (pol == 1):
    print "\n____WRITING TRIMING FILE for HOLES ____\n"
    filename_trim = filename_trim + "_holes.txt"
  elif (pol == 0):
    print "\n____WRITING TRIMING FILE for ELECTRONES ____\n"
    filename_trim = filename_trim + "_elect.txt"

  # -----------------------------------------------------------------

  trimfile = open(filename_trim, "w+")
  assert path.exists(filename_trim)

  print "\n\n\n"

  # writing trim values on file
  for ch in range (ch_min, ch_max):
    trimfile.write("ch:")
    trimfile.write('{:4d}'.format(ch))
    print "\nch: ", '{:3d}'.format(ch),
    for d in range(d_min, d_max + 1):
      trimfile.write('{:5d}'.format(trim_final[ch][d]))
      print '{:3d}'.format(trim_final[ch][d]),
    trimfile.write("\n")

  trimfile.close()
  return 0

## For now make a script only for the 1st ASIC on the 1st DPB
sts = sts_ifaces[0][0]

# ----------------- Writing and Reading register in the STS_XYTER ----------------------

# --- Confirm25ing MODE_FRAME ------
sts.EncMode.write(sxdc.MODE_FRAME)
time.sleep(0.000002)

# ----------- Set the link mask accordingly -----------
lmask = ((1 << 5) - 1) ^ LINK_ASIC
lmask |= (lmask << 5)
sts.emg_write(192, 25, lmask)
confirm = False
print "Link Mask" + hex(sts.read(192, 25))

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
#                         get trim: General Settings
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

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

itr = 0
tr_min = 80
tr_max = 180
tr_coarse_step = 5
tr_coarse_range = 1
tr_coarse_offset = -15
tr_fine_offset = -20
tr_i_fine_max = tr_coarse_step * tr_coarse_range - tr_fine_offset
tr_fine_step = 1

# .......................  ADC  Reference Voltages ...........................

vref_p_h = 56     # Ref. voltages Positive  (130, 9) (48)
vref_n_h = 24     # Ref. voltages Negative  (130, 8) (30)

vref_p_e = 56     # Ref. voltages Positive  (130, 9) (48)
vref_n_e = 28     # Ref. voltages Negative  (130, 8) (30)
vref_t = 186    # Ref. voltages Threshold (130,10)  (188)

# ................. FAST thr settings (0...137,d_min...d_max,thr) ..............

thr_min = 0
thr_max = 64
thr_step = 1
# ......................  FAST  Reference Voltages ............................

thr2_glb = 36

# .......................... CSA reference current ..........................
csa_in = 31

# .................. Calibration pulse settings .............................

amp_cal_min = 5  # (130,4, amp_cal), usually 20 changed by Axel
amp_cal_max = 248.

loop_max = 30+15   # Number of test hits to be sent in the coarse mode

#list_arg = sys.argv
#loop_max_fine = int(list_arg[1])

loop_max_fine = 80 # number of test hits to be sent in the fine mode
npulses = 80

shslowfs = 0  # 0,..,3 for FS=90,160,220,280ns

# calibration range
cnt_min_coarse = int(loop_max*0.30)
cnt_max_coarse = int(loop_max*0.40)

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

print "\n --------------------------------- "
print "Number of test_pulses: ", loop_max
print "Reference levels for coarse switching, MIN: ", cnt_min_coarse
print "Reference levels for coarse switching, MIN: ", cnt_max_coarse
print " --------------------------------- \n"

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

print "\n CSA input current"
print "CSA_in front: ", sts.read(130, 0)
print "CSA in back: ", sts.read(130, 13), "\n"

date  = time.strftime("%y%m%d")
if len(sys.argv) != 3:
  log.error("This script has to be called with 2 arguments: box Nr and asic_serial_nr")
  log.error("The arguments should respectively follow these conventions:")
  log.error("- box_nr           = integer > 0 e.g. 88")
  log.error("- asic_serial_nr   = float, given as a matrix element (row,column) starting in (0,0), e.g 4.3")
  log.error("E.g.: python test_sts_gettrim.py 88 9.9")
  sys.exit()

box_number     = int( sys.argv[1] )
asic_serial_nr = float( sys.argv[2] )

# Creating files for saving the trim information
#filename_trim = "module_comp/trim_cal_" +date+"_module_"+str(module_id)+"_asic_addr_"+str(sts.read(192,22))+"_fast_"+str(sts.read(130,7))+"_adc_"+str(sts.read(130,9))+str(sts.read(130,8))+str(sts.read(130,10))+"_vp_"+str(amp_cal_min)+"_"+str(amp_cal_max)

#logfile = open(filename_trim + "_log.txt", "w+")

trim_final = [[0 for d in range(d_max+1)] for ch in range(ch_max)]						# final trim values to storage

# ---------------------------------------------------------------------------------------
#                                     to run
# ---------------------------------------------------------------------------------------

# Calibration for holes (p-side)
pol = 1
get_trim_adc(sts, pol)
get_trim_fast(sts, pol)
write_trim_file(sts, pol)
date  = time.strftime("%y%m%d")
time_end2 = time.time()

# making pc make a sound when the program finishes
#duration = 3   # seconds
#freq = 800     # Hz
#os.system('play --no-show-progress --null --channels 1 synth %s sine %f' % (duration, freq))
