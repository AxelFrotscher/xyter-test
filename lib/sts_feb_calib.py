import time
import sys
import logging as log

import numpy as np
import matplotlib.pyplot as plt
#from drawnow import *
import pyqtgraph as pg
import math

#-------------ASICs settings -------------------
ch_min = 0
ch_max = 128

grp_min = 0
grp_max = 4

d_min = 0
d_max = 31

loop_max = 40
loop_max_fine = 40
npulses = loop_max + loop_max_fine

def get_trim_adc( feb_ctl, asic_idx, pol, trim_final, amp_cal_min, amp_cal_max,
                  tr_min = 30, tr_max = 220, tr_coarse_step = 5, tr_coarse_range = 1,
                  tr_coarse_offset = -20, tr_fine_offset = -20, much_mode_on = 0 ):
  # ------------------ get_trim_settings ------------------------------------------------------
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

  tr_i_fine_max =tr_coarse_step*tr_coarse_range-tr_fine_offset+15
  tr_fine_step = 1


  # calibration range
  cnt_min_coarse = int(loop_max*0.30)
  cnt_max_coarse = int(loop_max*0.40)

  # ------------------------------------------------------------------------------------------

  # ------------------------ pol -------------------------------------
  if (pol == 1):
    feb_ctl[asic_idx].write_check(130,2,163)   #  163 holes     131 electrons
    log.info(" ")
    log.info("____HOLES MODE____")
    log.info(" ")
  if (pol == 0):
    feb_ctl[asic_idx].write(130,2,131)   #  163 holes     131 electrons
    log.info(" ")
    log.info("____ELECTRONS MODE____")
    log.info(" ")

  # -----------------------------------------------------------------
  # ------------------------ MUCH -----------------------------------

  # Read 130,1 configuration
  old_pulser_mode = ( feb_ctl[asic_idx].read(130, 1) & 0xBF )
  if (much_mode_on == 1):
    log.info("____MUCH MODE____")
    log.info(" ")
    # Force MUCH mode for all channels
    for ch in range( 0, 130 ):
      feb_ctl[asic_idx].write_check(ch, 65, 228 )
    # Set 130,1 for pulser in MUCH mode
    feb_ctl[asic_idx].write_check( 130, 1, old_pulser_mode | 0x40 )

  # -----------------------------------------------------------------

  log.info(" ")
  log.info(".......................... Getting ADC Trim Values ................................")
  log.info(" ")

  # counters array for trim
  vpset = [0 for d in range (d_min,d_max)]   									                            # array of pulse heights for each discriminator
  vcnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]    # array for discriminator counters coarse
  fcnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)]  	# array for discriminator counters fine
  avg_cnt = [[[0 for tr in range(tr_max)] for d in range(d_max)] for ch in range(ch_max)] # smothed counter values from fine scan
  hh_cnt = [[0 for d in range(d_max)] for ch in range(ch_max)]					        	        # half maximun count values
  trim_coarse_low = [[0 for d in range(d_max)] for ch in range(ch_max)]					          # lower trim values before switching

  # setting vpset = [32]
  # Implemented linearily -> could it be not linearly to implemment nonlinearADC characteristics
  vp_d=((amp_cal_max-amp_cal_min)/(d_max-d_min))# + 0.5 )    # + 0.5 Why ?     # Step in the pulse amplitud/trim
  log.info("vp_d : %3f", float(vp_d) )

  for d in range (d_min, d_max):
    vpset[d]= int(amp_cal_min + (d-d_min)*vp_d)
    log.info("vpset: %3f", float(vpset[d]) )

  # Read slow shaper configuration
  shslowfs = ( feb_ctl[asic_idx].read(130, 5) & 0xC ) >> 2

  d_counter = 0
  # Loop over discriminators
  for d in range (d_min, d_max):
    disc = 61 - 2*d
    count = 61 - 2*d -1
    vp = int(vpset[d])
    if (vp<amp_cal_min or vp>amp_cal_max):
      log.info("NOTE: Pulse amplitude should be in the range ....")
    feb_ctl[asic_idx].write(130, 4, vp)
    log.info("Calibration Pulse Amplitude set to: %3d", vp)

    itr = 0

    #Coarse loop over trim
    for tr in range (tr_min,tr_max,tr_coarse_step):
      #log.info("Discriminator number:   " , d, "  Set_trim:   ", tr, "\n")
      #if tr<0 or tr>255:
        #log.info("NOTE: Trim out of range, should be between (0-255) ....", tr, "\n")

        # Loop over groups
      for grp in range (grp_min, grp_max):
        grp_shslow = ((shslowfs & 0x3)<<2 | (grp & 0x3)) # Included the slow shaper configuration (90,130,220,280ns)
        feb_ctl[asic_idx].write(130, 5, grp_shslow)
        #log.info(" Selected Shaping time and group: " ,format(bin(sts.read(130,5))), "\n")

        # Loop over the channels of the group
        for ch in range(grp, ch_max, 4):
          feb_ctl[asic_idx].write(ch, disc, tr)

        # Reset ADC counters
        feb_ctl[asic_idx].write(192,2,32)
        #time.sleep(0.00001)
        feb_ctl[asic_idx].write(192,2,0)

      # multiple count loops
        for loop in range (0,loop_max):
          #Sending the signal to trigger pulses.
          feb_ctl[asic_idx].write(130,11,128)
          #time.sleep(0.004)
          feb_ctl[asic_idx].write(130,11,0)
        # loop to read counter
        cnt_val = 0
        for ch in range(grp,ch_max, 4):
          vcnt[ch][d][itr]= feb_ctl[asic_idx].read(ch,count)

      itr +=1  # here ends the loop over trim

    '''
    # Start loop to print out collected data and log_file writing
    for ch in range (ch_min, ch_max):
      print "coarse: ch ", '{:3d}'.format(ch),
      logfile.write("coarse: ch ")
      logfile.write('{:4d}'.format(ch))
      itr = 0
      for tr in range (tr_min, tr_max, tr_coarse_step):
        print '{:7d}'.format(vcnt[ch][d][itr]),
        logfile.write('{:7d}'.format(vcnt[ch][d][itr]))
        itr += 1
      print "\n"
      logfile.write("\n")
    '''


    # Finding coarse switching point from vcnt[ch][d][tr]
    #log.info("............Coarse switching..........")
    #logfile.write(" ............Coarse switching..........\n")
    for ch in range(ch_min,ch_max):
      #trim_coarse_low[ch][d] = 0
      trim_coarse_low[ch][d] = -1
      itr = 0
      #print "ch", '{:4d}'.format(ch),
      coarse_flag =0
      y_coarse_min =0
      y_coarse_max =0
      for tr in range (tr_min,tr_max,tr_coarse_step):   # the loop should include the tr_max
        if (itr >= tr_coarse_range and coarse_flag == 0):
          if ((vcnt[ch][d][itr]>=cnt_max_coarse) and vcnt[ch][d][itr-tr_coarse_range]<=cnt_max_coarse):
            y_coarse_min = cnt_max_coarse-vcnt[ch][d][itr-tr_coarse_range]
            y_coarse_max = vcnt[ch][d][itr] - cnt_max_coarse
            trim_coarse_low[ch][d] = (tr if (y_coarse_min<=y_coarse_max) else (tr+tr_coarse_step)) - (tr_coarse_range*tr_coarse_step - tr_coarse_offset) # Searching range tr-25(35)
            #print  '{:4d}'.format(itr), '{:4d}'.format(trim_coarse_low[ch][d]),
            if (trim_coarse_low[ch][d]<0):
              trim_coarse_low[ch][d]=0

              #logfile.write("coarse adjust to 0: ch")
              #logfile.write('{:4d}'.format(ch))
              #logfile.write("disc")
              #logfile.write('{:4d}'.format(d))
              #logfile.write("trim")
              #logfile.write('{:7d}'.format(tr))
              #logfile.write("\n")
            #print "ch", '{:4d}'.format(ch), "      trim ", '{:6d}'.format(trim_coarse_low[ch][d]), "      vcnt", '{:6d}'.format(vcnt[ch][d][itr-tr_coarse_range-1]),"\n"
            #logfile.write("ch")
            #logfile.write('{:4d}'.format(ch))
            #logfile.write("      trim")
            #logfile.write('{:7d}'.format(trim_coarse_low[ch][d]))
            #logfile.write("      vcnt")
            #logfile.write('{:7d}'.format(vcnt[ch][d][itr-tr_coarse_range+tr_coarse_offset/tr_coarse_step]))
            #logfile.write("\n")

            coarse_flag =1

        itr +=1
    log.info("")


    #fine loop over tr
    for  itr in range(0,tr_i_fine_max+1):
      log.info("fine_disc %3d itr %3d/%3d", d, itr, tr_i_fine_max)

      #logfile.write("fine_disc")
      #logfile.write('{:4d}'.format(d))
      #logfile.write(" itr ")
      #logfile.write('{:3d}'.format(itr))
      #logfile.write("/")
      #logfile.write('{:3d}'.format(tr_i_fine_max))
      #logfile.write("\n")

      ## Loop over groups
      for grp in range (grp_min, grp_max):
        grp_shslow = ((shslowfs & 0x3)<<2 | (grp & 0x3)) # Included the slow shaper configuration (90,130,220,280ns)
        feb_ctl[asic_idx].write(130, 5, grp_shslow)
        #log.info(" Selected Shaping time and group: " ,format(bin(sts.read(130,5))), "\n"

        # Loop over channels in group to set trim values
        for ch in range(grp,ch_max,4):
          tr = trim_coarse_low[ch][d] + itr*tr_fine_step
          #log.info("ch: ", ch, " tr: " '{:4d}'.format(tr), "\n"
          '''
          if (tr < 0):
            tr =0
          if (tr >255):
            tr = 255
          '''
          feb_ctl[asic_idx].write(ch,disc,tr)


        ## Reset ADC counters
        feb_ctl[asic_idx].write(192,2,32)
        #time.sleep(0.00001)
        feb_ctl[asic_idx].write(192,2,0)

        ## multiple count loops
        for loop in range(0,loop_max_fine):
          feb_ctl[asic_idx].write(130,11,128)    # sending trigger pulses ()
          #time.sleep(0.004)
          feb_ctl[asic_idx].write(130,11,0)

        ## loop to read counter
        #cnt_val = 0
        for ch in range(grp,ch_max, 4):
          fcnt[ch][d][itr]= feb_ctl[asic_idx].read(ch,count)
        #log.info("\n"


    '''
    # Start loop to print out collected data and log_file writing
    for ch in range (ch_min, ch_max):
      print "fine: ch ", '{:3d}'.format(ch),
      logfile.write("fine: ch ")
      logfile.write('{:4d}'.format(ch))
      itr = 0
      for itr in range (0, tr_i_fine_max):
        print '{:7d}'.format(fcnt[ch][d][itr]),
        logfile.write('{:7d}'.format(fcnt[ch][d][itr]))
        itr += 1
      print "\n"
      logfile.write("\n")
    '''

    # Smooth fcnt -> This is not done here
    asum = 0
    isum = 0
    avg_max = 0.000
    avg_max_range = 5
    #logfile.write("the Half height counts condition")
    for ch in range(ch_min,ch_max):
      avg_max = 0
      for itr in range (tr_i_fine_max-avg_max_range,tr_i_fine_max):
        #avg_cnt[ch][d][itr] = fcnt[ch][d][itr]
        #if (itr>=(tr_i_fine_max-avg_max_range) and (itr<(tr_i_fine_max))):
          if (abs(fcnt[ch][d][itr]-loop_max_fine)>0.1*loop_max_fine):
            fcnt[ch][d][itr] = loop_max_fine
          avg_max += fcnt[ch][d][itr]      # Max value condition
      hh_cnt[ch][d] = (avg_max/avg_max_range/2.)   # Condition for half height count
      #log.info("ch:", '{:4d}'.format(ch), "    disc: ", '{:3d}'.format(d), "   hh_cnt: ", '{:4f}'.format(hh_cnt[ch][d]), "\n"
      '''
      logfile.write("ch:")
      logfile.write('{:4d}'.format(ch))
      logfile.write("    disc:")
      logfile.write('{:3d}'.format(d))
      logfile.write("    hh_cnt:      ")
      logfile.write('{:4f}'.format(hh_cnt[ch][d]))
      logfile.write("\n")
      '''

    # determining switching point for trim_final[ch][d]
    #logfile.write("Determining switching point for final trim")
    #for ch in range(ch_min,ch_max):
      trim_final[ch][d] = -1
      find_flag = 0
      y_min = 0
      y_max = 0
      for itr in range(0,tr_i_fine_max):
        #print '{:4d}'.format(avg_cnt[ch][d][itr]),
        if (itr > 0 and itr<(tr_i_fine_max-1) and find_flag ==0):
          if ((fcnt[ch][d][itr]<=hh_cnt[ch][d]) and (fcnt[ch][d][itr+1]>=hh_cnt[ch][d])):
            #print "   |   "
            y_max = fcnt[ch][d][itr+1] - hh_cnt[ch][d]
            y_min = hh_cnt[ch][d] - fcnt[ch][d][itr]
            trim_final[ch][d] = trim_coarse_low[ch][d] + ((itr*tr_fine_step) if (y_min<=y_max) else (itr+1)*tr_fine_step)
            find_flag =1
      #print "\n"

    '''
    for ch in range(ch_min,ch_max):
      print "final_trim  ch: ", '{:4d}'.format(ch), '{:4d}'.format(trim_final[ch][d]), "\n"
      logfile.write("final_trim ch:  ")
      logfile.write('{:4d}'.format(ch))
      logfile.write('{:5d}'.format(trim_final[ch][d]))
      logfile.write("\n")
    '''
  #logfile.close()

  # restore original setting
  if (much_mode_on == 1):
    feb_ctl[asic_idx].write_check( 130, 1, old_pulser_mode )

  return 0

def get_trim_fast(feb_ctl, asic_idx, pol, trim_final, amp_cal_fast,
                   thr_min = 0, thr_max = 63, thr_step = 1, much_mode_on = 0 ):

  grp_min = 0
  grp_max = 4

  ch_min = 0
  ch_max = 128

  # ------------------------ pol -------------------------------------

  if (pol == 1):
    feb_ctl[asic_idx].write_check(130,2,163)   #  163 holes     131 electrons
    log.info(" ")
    log.info("____HOLES MODE____")
    log.info(" ")
  if (pol == 0):
    feb_ctl[asic_idx].write_check(130,2,131)   #  163 holes     131 electrons
    log.info(" ")
    log.info("____ELECTRONS MODE____")
    log.info(" ")
  # -----------------------------------------------------------------
  # ------------------------ MUCH -----------------------------------

  # Read 130,1 configuration
  old_pulser_mode = ( feb_ctl[asic_idx].read(130, 1) & 0xBF )
  if (much_mode_on == 1):
    log.info("____MUCH MODE____")
    log.info(" ")
    # Force MUCH mode for all channels
    for ch in range( 0, 130 ):
      feb_ctl[asic_idx].write_check(ch, 65, 228 )
    # Set 130,1 for pulser in MUCH mode
    feb_ctl[asic_idx].write_check( 130, 1, old_pulser_mode | 0x40 )

  # -----------------------------------------------------------------


  cnt = [[0 for thr in range(thr_max)] for ch in range (ch_max)]
  avg = [[0 for thr in range(thr_max)] for ch in range (ch_max)]
  hh  = [0 for ch in range (ch_max)]

  # cleaning lists

  for ch in range (ch_min, ch_max):
    thr_i = 0
    for thr in range (thr_min, thr_max):
      cnt[ch][thr_i]=0
      thr_i +=1

  #print " "

  thr_i =0

  feb_ctl[asic_idx].write_check(130,4,amp_cal_fast)
  for thr in range (thr_min, thr_max):
    log.info("disc_threshold: %3d", thr )
    #sys.stdout.flush()
    # reseting counters
    #feb_ctl[asic_idx].write(192,2,32)
    #feb_ctl[asic_idx].write(192,2, 0)
    for grp in range (grp_min, grp_max):
      feb_ctl[asic_idx].write_check(130,5,grp)
      log.info("group: %3d", grp )

      # setting disc. threshold
      for ch in range (grp, ch_max,4):
        feb_ctl[asic_idx].write_check(ch,67,thr)

      # reseting counters
      feb_ctl[asic_idx].write_check(192,2,32)
      feb_ctl[asic_idx].write_check(192,2, 0)

      # generating npulses
      for n in range (npulses):
        feb_ctl[asic_idx].write_check(130,11,128)
        feb_ctl[asic_idx].write_check(130,11,0)

      # reading ch counters
      for ch in range (grp, ch_max,4):
        cnt[ch][thr_i] =feb_ctl[asic_idx].read(ch,62)
        log.info("ch: %3d %3d", ch, cnt[ch][thr_i])
#      sys.stdout.flush()
      log.info(" ")
    thr_i +=1
    log.info(" ")

  thr_i = 0
  '''
  for ch in range (ch_min, ch_max):
    print "ch: ", '{:3d}'.format(ch),": ",
    #fscanfile.write("ch:")
    #fscanfile.write('{:3d}'.format(ch))
    #fscanfile.write(":")
    thr_i = 0
    for thr in range (thr_min, thr_max):
      #fscanfile.write('{:3d}'.format(cnt[ch][thr_i]))
      print '{:3d}'.format(cnt[ch][thr_i]),
      thr_i +=1
    print"\n"
    #fscanfile.write("\n")
  '''
  #fscanfile.close()
  thr_val_t = int(thr_max/thr_step)

  '''
  print " "
  print "disc_thresh: ",
  for thr in range(thr_min, thr_max+1, thr_step):
    print '{:3d}'.format(thr),
  print " "
  '''

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
      if (thr <=thr_step):
        avg[ch][thr_i] = 0
      elif (thr>=thr_max-thr_step):
        avg[ch][thr_i] = 0
      else:
        isum = cnt[ch][thr_i-1]+cnt[ch][thr_i]+cnt[ch][thr_i+1]
        asum = float(isum)
        avg[ch][thr_i] = int(asum/3)

      if (thr>=thr_max -6*thr_step and thr<thr_max-thr_step):
        if (abs(cnt[ch][thr_i]-npulses)>0.1*npulses):
          cnt[ch][thr_i]=npulses
        avg_max += cnt[ch][thr_i]
      thr_i +=1

    hh[ch] = int(avg_max/avg_max_range/2)
    #print '{:3d}'.format(hh[ch])


  #print " "
  #print "------------ Final trim values ------------ "
  #print " "
  for ch in range (ch_min, ch_max):
    thr_i = 0
    trim_final[ch][31] = -1
    find_flag = 0
    y_min = 0
    y_max = 0

    for thr in range (thr_min, thr_max, thr_step):
      if (thr >0 and thr<thr_max-thr_step and find_flag ==0):
        #if (avg[ch][thr_i]<=hh[ch] and avg[ch][thr_i-1]<hh[ch] and avg[ch][thr_i+1]>= hh[ch]):
        if (cnt[ch][thr_i]<=hh[ch]  and cnt[ch][thr_i+1]>= hh[ch]):
#          print  " | "
          y_max = cnt[ch][thr_i+1]-hh[ch]
          y_min = hh[ch]-cnt[ch][thr_i]
          trim_final[ch][31] = (thr_i*thr_step) if (y_min<=y_max) else ((thr_i+1)*thr_step)
          find_flag = 1
      thr_i += 1
    #print "\n"

  # restore original setting
  if (much_mode_on == 1):
    feb_ctl[asic_idx].write_check( 130, 1, old_pulser_mode )

  return 0


def  write_trim_file( pol, filename_trim, trim_final, much_mode_on = 0 ):

  # ------------------------ pol ------------------------------------

  if (pol == 1):
    log.info(" ")
    log.info("____WRITING TRIMING FILE for HOLES ____")
    log.info(" ")
    filename_trim = filename_trim +"_holes"
  if (pol == 0):
    log.info(" ")
    log.info("____WRITING TRIMING FILE for ELECTRONS ____")
    log.info(" ")
    filename_trim = filename_trim +"_elect"

  # -----------------------------------------------------------------
  # ------------------------ MUCH -----------------------------------

  if (much_mode_on == 1):
    log.info(" ")
    log.info("____WRITING TRIMING FILE for MUCH ____")
    log.info(" ")
    filename_trim = filename_trim +"_much"

  # -----------------------------------------------------------------
  filename_trim = filename_trim +".txt"

  trimfile = open(filename_trim, "w+")

  log.info(" ")
  log.info("")

  # writing trim values on file
  for ch in range (ch_min,ch_max):
    trimfile.write("ch:")
    trimfile.write('{:4d}'.format(ch))
#    print "ch: ", '{:4d}'.format(ch),
    log_line = "ch: " + '{:4d}'.format(ch)
    for d in range(d_min,d_max+1):
      trimfile.write('{:5d}'.format(trim_final[ch][d]))
#      print '{:5d}'.format(trim_final[ch][d]),
      log_line = log_line + '{:5d}'.format(trim_final[ch][d])
#    print""
    log.info( log_line )
    trimfile.write("\n")

  trimfile.close()

  return 0

def getAsicTrim( feb_ctl, asic_idx, pol, amp_cal_min, amp_cal_max, amp_cal_fast, filename_trim,
                  tr_min = 30, tr_max = 220, tr_coarse_step = 5, tr_coarse_range = 1,
                  tr_coarse_offset = -20, tr_fine_offset = -20,
                  thr_min = 0, thr_max = 63, thr_step = 1, much_mode_on = 0 ):

  trim_final = [[0 for d in range(d_max+1)] for ch in range(ch_max)]

  get_trim_adc(  feb_ctl, asic_idx, pol, trim_final, amp_cal_min, amp_cal_max,
                  tr_min, tr_max, tr_coarse_step, tr_coarse_range,
                  tr_coarse_offset, tr_fine_offset, much_mode_on )
  time.sleep(1)
  get_trim_fast( feb_ctl, asic_idx, pol, trim_final, amp_cal_fast,
                  thr_min, thr_max, thr_step, much_mode_on )
  write_trim_file( pol, filename_trim, trim_final, much_mode_on )


# --------------------- check trim ----------------------------
# -------------------------------------------------------------
# -------------------------------------------------------------

def check_trim(feb_ctl, asic_idx, pol, shslowfs, vp_min, vp_max, filename_scan, vp_step = 1, fast_check = False ):
  ivp = 0
  d_counter = 0
  ch_step = 1

  vp_max = int(vp_max)

  # ---------------  Polarity selection --------------
  if (pol == 1):
    feb_ctl[asic_idx].write_check(130,2,163)   #  163 holes     131 electrons
    log.info( " " )
    log.info( "____HOLES MODE____" )
    filename_scan = filename_scan +"_holes.txt"
    log.info( " " )
  if (pol == 0):
    feb_ctl[asic_idx].write_check(130,2,131)   #  163 holes     131 electrons
    log.info( " " )
    log.info( "____ELECTRONS MODE____" )
    filename_scan = filename_scan +"_elect.txt"
    log.info( " " )

  myfile = open(filename_scan,"w+")

  # ---------------------------------------------------

  vcnt = [[[0 for vp in range(vp_min,vp_max+1, vp_step)] for d in range(d_min,d_max+1)] for ch in range(ch_max/ch_step)]
  #vcnt = [[[0 for vp in range(5000)] for d in range(20,d_max)] for ch in range(ch_max/ch_step)]

  nd = 31
  nthr = 256
  nch = 256

  log.info( " " )
  log.info( "......Start acquiring data...... " )
  log.info( " " )

  # ------------------------------------------------------
  # In case to set all ch-disc to the typical value(128)
  # ------------------------------------------------------
  '''
  for ch in range(ch_min,ch_max):
    for d in range(d_min,d_max):
      n=61-2*d
      sts.write_check(ch,n,128)
  '''
  # loop over test charge range
  for vp in range(vp_min,vp_max, vp_step):
    a = (vp*15.)/256.
    log.info( a ) # Pulse height value in fC
    log.info( "vp: %4d (%3f)", vp, a )

    if ((vp<vp_min) or (vp>vp_max)):
      log.info( "Pulse amplitude should be in range: %3d-%3d. Currently it is set to %3d", vp_min, vp_max, vp )

    feb_ctl[asic_idx].write(130, 4, vp)
    #sts.write_check(130, 4, 61)
    log.info( "vpulse: %3d", feb_ctl[asic_idx].read(130,4) )

    max_ch_grp =0
    #loop over groups
    for grp in range(grp_min, grp_max):
      grp_shslow = ((shslowfs & 0x3)<<2 | (grp & 0x3)) # Included the slow shaper configuration (90,130,220,280ns)

      # ADC counters resets
      feb_ctl[asic_idx].write(192,2,32)
      time.sleep(0.00001)
      feb_ctl[asic_idx].write(192,2,0)

      feb_ctl[asic_idx].write(130, 5, grp_shslow)
      log.info( "group " + '{0:04b}'.format( feb_ctl[asic_idx].read(130,5) ) )
      # Number of trigger pulses

      for npulse in range(0, npulses):
        #log.info( " loop %4d", npulse )
        # Pulse triggering
        feb_ctl[asic_idx].write(130,11,128)
       # time.sleep(0.001)
        feb_ctl[asic_idx].write(130,11, 0)

        ## read counters
      ch_counter =0
      for ch in range(grp,ch_max,4):
#        print "ch  ", '{:4d}'.format(ch),
        log_line = "ch: " + '{:3d}'.format( ch )
        cnt_val = 0
        d_counter =0
        #cnt_val =0
        for d in range(d_min,d_max+1):
          count = d*2
          #print "d: ", d, " counter: ", count, "\n"
          vcnt[ch][d_counter][ivp]  = feb_ctl[asic_idx].read(ch,count)
#          print '{:4d}'.format(vcnt[ch][d_counter][ivp]),
          log_line = log_line + " " + '{:4d}'.format(vcnt[ch][d_counter][ivp])
          #vcnt[ch][d_counter][ivp] = cnt_val
          d_counter +=1
          #print cnt_val,
#        print "\n"
        log.info( log_line )
        ch_counter +=4

    ivp+=1

  log.info( " " )

  ivp = 0
  for vp in range(vp_min,vp_max, vp_step):
    ch_counter = 0
    for ch in range(ch_min,ch_max, ch_step):
#      print "vp ", '{:4d}'.format(vp), "   ch: ", '{:4d}'.format(ch), ": ",
      log_line = "vp " + '{:4d}'.format(vp) + "   ch: " + '{:4d}'.format(ch) + ": "
      myfile.write("vp")
      myfile.write('{:4d}'.format(vp))
      myfile.write("   ch ")
      myfile.write('{:4d}'.format(ch))
      myfile.write(": ")
      d_counter = 0
      for d in range(d_min,d_max+1):
#        print '{:4d}'.format(vcnt[ch][d_counter][ivp]),
        log_line = log_line + '{:4d}'.format(vcnt[ch][d_counter][ivp])
        myfile.write('{:6d}'.format(vcnt[ch][d_counter][ivp]))
        d_counter+=1
      ch_counter+=1
#      print "\n"
      log.info( log_line )
      myfile.write("\n")
    ivp+=1

  myfile.close()

  if fast_check :
    quick_noise_analysis( vp_min, vp_max, vp_step, vcnt, filename_scan )

def quick_noise_analysis( vp_min, vp_max, vp_step, vcnt, filename_scan ):
  ##
  ## ----------------- Quick noise and linearity analysis ---------------------##
  ##

  log.info( "" )
  log.info( "............. Quick noise- linearity analysis ............" )
  log.info( "" )
  d_list =[24,25,26]
  d_len=len(d_list)
#  log.info( "d_len: ",d_len

  hnoise = [[0 for d in range(d_len)] for ch in range(ch_min, ch_max)]
  hmean = [[0 for d in range(d_len)] for ch in range(ch_min, ch_max)]
  ch_array = [0 for ch in range(ch_min, ch_max)]
  hnoise_avg = [0 for ch in range(ch_min, ch_max)]
  hmean_avg = [0 for ch in range(ch_min, ch_max)]

  for ch in range(ch_min, ch_max):
    for d in d_list:
      ivp=0
      for vp in range(vp_min, vp_max, vp_step):
        # Remove potential double peaks
        if( vcnt[ch][d][ivp] > 1.1 * npulses ):
          vcnt[ch][d][ivp] = npulses
          ivp+=1

  for ch in range(ch_min, ch_max):
    d_counter = 0
    for d in d_list:
      d_cnt = 0;
      sum_delta = 0.001
      sum_mean = 0
      ivp =1
      for vp in range(vp_min+1, vp_max, vp_step):
        d_cnt = vcnt[ch][d][ivp] - vcnt[ch][d][ivp-1]
        sum_delta += d_cnt
        sum_mean  += (vp+vp_min)*d_cnt
        ivp+=1

      hmean[ch][d_counter] =float(sum_mean/sum_delta)
      d_counter+=1

  for ch in range(ch_min, ch_max):
    d_counter = 0
    for d in d_list:
      d_cnt = 0
      sum_delta = 0.001
      sum_sigma = 0
      ivp =1
      for vp in range(vp_min+1, vp_max, vp_step):
        d_cnt = vcnt[ch][d][ivp]-vcnt[ch][d][ivp-1]
        sum_delta+=d_cnt
        sum_sigma +=((vp+vp_min)-hmean[ch][d_counter])*((vp+vp_min)-hmean[ch][d_counter])*d_cnt
        ivp+=1

      hnoise[ch][d_counter] =math.sqrt(float(sum_sigma/sum_delta))
      d_counter+=1

  for ch in range(ch_min, ch_max):
    ch_array[ch] = ch
    d_counter =0
#    log.info( "ch: ", '{:4d}'.format(ch),
    for d in d_list:
      hnoise_avg[ch]+= hnoise[ch][d_counter]
#      hmean_avg[ch]+= hmean[ch][d_counter]
      if hnoise[ch][d_counter]>0:
        d_counter+=1

    hnoise_avg[ch]= 350*float(hnoise_avg[ch]/d_len)

    d_counter+=1

#    log.info( "enc: ", '{:4f}'.format(hnoise_avg[ch]) )



  ##
  ## ----------------- Plot noise and linearity analysis ---------------------##
  ##

  f = plt.figure()

  plt.step(ch_array,hnoise_avg)
  plt.xlabel('Channel number')
  plt.ylabel('ENC[electrons]')
  plt.title('Quick noise estimation')
  plt.grid(True, linestyle='--', color='0.75')
  plt.show()

  f.savefig(filename_scan+'.png', bbox_inches = 'tight' )

def get_s_curve(feb_ctl, asic_idx, test_ch, vp_min, vp_max):
  # ------------------ s_curve__settings ------------------------------------------------------
  vp_step = 5
  grp_test = test_ch%4
  test_npulse = 20

  log.info( " " )
  log.info( " ------------------------------------------ S-curves in test channel: " +  test_ch
            + " --------------------------------------" )
  log.info( " " )

  for vp in range (vp_min,vp_max, vp_step):
    feb_ctl[asic_idx].write(130, 4, vp) # test pulse Recommended value between 80-200
#    print "Volt_pulse ", '{:3d}'.format(vp), ": ",
    log_line = "Volt_pulse " + '{:3d}'.format(vp) + ": "
#    sys.stdout.flush()

    # Reset ADC counters
    feb_ctl[asic_idx].write(192,2,32)
    time.sleep(0.00001)
    feb_ctl[asic_idx].write(192,2,0)

    # Generate calib pulses
    feb_ctl[asic_idx].write(130,5,grp_test)
    for i in range (0,test_npulse):
      feb_ctl[asic_idx].write(130,11,128)
      time.sleep(0.01)
      feb_ctl[asic_idx].write(130,11,0)

    # readback counter values
    for d in range (0,32):
      n=2*d
#      print '{:4d}'.format(feb_ctl[asic_idx].read(test_ch,n)),
      log_line = log_line + '{:4d}'.format(feb_ctl[asic_idx].read(test_ch,n))
#      sys.stdout.flush()


#    print " "
    log.info( log_line )


  log.info( " " )
  log.info( " ------------------------------------------ S-curves in test channel: " + test_ch
            + " --------------------------------------" )
  log.info( " " )

def get_s_curve_all(feb_ctl, asic_idx, pol, vp_min, vp_max, vp_step = 10, test_npulse = 20, filename_scan = "" ):
  # ------------------ s_curve__settings ------------------------------------------------------


  log.info( " " )
  log.info( " ------------------------------------------ S-curves in all channels "
            + " --------------------------------------" )
  log.info( " " )

  vp_nb = int( (vp_max - vp_min) / vp_step )

  vp_idx = 0
  cnt = [[[0 for vp in range( vp_nb )] for d in range (d_max + 1)] for ch in range (ch_max)]
  for vp in range (vp_min,vp_max, vp_step):
    feb_ctl[asic_idx].write(130, 4, vp) # test pulse Recommended value between 80-200
    log.info( "Volt_pulse " + '{:3d}'.format(vp) + ": " )

    # Loop on groups
    for grp in range (grp_min, grp_max):
      feb_ctl[asic_idx].write( 130, 5, grp)
      log.info("group: %3d", grp )

      # Reset ADC counters
      feb_ctl[asic_idx].write( 192, 2, 32)
      time.sleep(0.00001)
      feb_ctl[asic_idx].write( 192, 2,  0)

      # Generate calib pulses
      for i in range (0,test_npulse):
        feb_ctl[asic_idx].write( 130, 11, 128)
        time.sleep(0.01)
        feb_ctl[asic_idx].write( 130, 11, 0)

      # readback counter values
      for d in range (d_min, d_max + 1):
        n=2*d
        # Store instead of log
        for ch in range (grp, ch_max,4):
          cnt[ ch ][ d ][ vp_idx ] =feb_ctl[ asic_idx ].read( ch, n )

    vp_idx += 1

  log.info( " -----------------------------------------------------------------------"
            + " --------------------------------------" )

  ## Loop on Channels
  for ch in range ( 0, ch_max):
    log.info( " " )
    log.info( " ------------------------------------------ S-curves in channel: %3d -"
              + " --------------------------------------", ch )
    log.info( " " )

    log_line = "                "
    for d in range (d_min, d_max + 1):
      log_line = log_line + '{:5d}'.format( d )
    log.info( log_line )

    vp_idx = 0
    for vp in range (vp_min,vp_max, vp_step):
      log_line = "Volt_pulse " + '{:3d}'.format(vp) + ": "
      for d in range (0,32):
        log_line = log_line + '{:5d}'.format( cnt[ ch ][ d ][ vp_idx ] )
      log.info( log_line )
      vp_idx += 1
    log.info( " -----------------------------------------------------------------------"
              + " --------------------------------------" )

  if filename_scan or filename_scan.strip():
    # ---------------  Polarity selection --------------
    if (pol == 1):
      filename_scan = filename_scan +"_holes.txt"
    if (pol == 0):
      filename_scan = filename_scan +"_elect.txt"
    myfile = open(filename_scan,"w+")
    ## Loop on Channels
    for ch in range ( 0, ch_max):
      myfile.write( "\n" )
      myfile.write( " ------------------------------------------ S-curves in channel: "+ '{:3d}'.format(ch)
                + "- --------------------------------------\n"  )
      myfile.write( "\n" )

      log_line = "                "
      for d in range (d_min, d_max + 1):
        log_line = log_line + '{:5d}'.format( d )
      myfile.write( log_line )
      myfile.write( "\n" )

      vp_idx = 0
      for vp in range (vp_min,vp_max, vp_step):
        log_line = "Volt_pulse " + '{:3d}'.format(vp) + ": "
        for d in range (0,32):
          log_line = log_line + '{:5d}'.format( cnt[ ch ][ d ][ vp_idx ] )
        myfile.write( log_line )
        myfile.write( "\n" )
        vp_idx += 1
      myfile.write( " -----------------------------------------------------------------------"
                + " --------------------------------------" )
      myfile.write( "\n" )


def get_scan_fast_thr(feb_ctl, asic_idx, thr_min, thr_max, filename_scan, vp = 100, test_npulse = 100):

  log.info( " " )
  log.info( " ------------------------------------------ Fast scan in all channels "
            + " --------------------------------------" )
  log.info( " " )

  thr_max = thr_max + 1 # To include the last value
  thr_nb = thr_max - thr_min

  cnt = [ [0 for thr in range( thr_nb )]  for ch in range (ch_max)]

  feb_ctl[asic_idx].write(130, 4, vp) # test pulse Recommended value between 80-200
  log.info( "Volt_pulse = " + '{:3d}'.format(vp) )

  thr_idx = 0
  for thr in range( thr_min, thr_max ):
    feb_ctl[asic_idx].write(130, 7, thr) # Fast Threshold thr2_glob
    log.info( "Fast_Thr " + '{:3d}'.format(thr) + ": " )

    # Loop on groups
    for grp in range (grp_min, grp_max):
      feb_ctl[asic_idx].write( 130, 5, grp)
      log.info("group: %3d", grp )

      # Reset ADC counters
      feb_ctl[asic_idx].write( 192, 2, 32)
      time.sleep(0.00001)
      feb_ctl[asic_idx].write( 192, 2,  0)

      # Generate calib pulses
      for i in range (0,test_npulse):
        feb_ctl[asic_idx].write( 130, 11, 128)
        time.sleep(0.0001)
        feb_ctl[asic_idx].write( 130, 11, 0)

      # readback counter values
      for ch in range (grp, ch_max,4):
        cnt[ ch ][ thr_idx ] =feb_ctl[ asic_idx ].read( ch, 62 )

    thr_idx += 1

  feb_ctl[asic_idx].write(130, 4, 0) # Reset pulser height to 0 to avoid pb


  log.info( " -----------------------------------------------------------------------"
            + " --------------------------------------" )

  log_line = "Fast_Thr: "
  for thr in range( thr_min, thr_max ):
    log_line = log_line +  '{:5d}'.format( thr )
  log.info( log_line )

  ## Loop on Channels
  for ch in range ( 0, ch_max):
    log_line = "Chan " + '{:3d}'.format(ch) + ": "

    thr_idx = 0
    for thr in range( thr_min, thr_max ):
      log_line = log_line + '{:5d}'.format( cnt[ ch ][ thr_idx ] )
      thr_idx += 1
    log.info( log_line )


  myfile = open(filename_scan,"w+")

  myfile.write( "Fast_Thr: " )
  for thr in range( thr_min, thr_max ):
    myfile.write('{:5d}'.format( thr ) )
  myfile.write( "\n" )

  ## Loop on Channels
  for ch in range ( 0, ch_max):
    myfile.write( "Chan " )
    myfile.write( '{:3d}'.format(ch) )
    myfile.write( ": " )

    thr_idx = 0
    for thr in range( thr_min, thr_max ):
      myfile.write( '{:5d}'.format( cnt[ ch ][ thr_idx ] ) )
      thr_idx += 1
    myfile.write( "\n" )

  myfile.close()

  return

def get_scan_slow_thr(feb_ctl, asic_idx, thr_min, thr_max, filename_scan, vp = 100, test_npulse = 100):

  log.info( " " )
  log.info( " ------------------------------------------ Fast scan in all channels "
            + " --------------------------------------" )
  log.info( " " )

  thr_max = thr_max + 1 # To include the last value

  thr_nb = thr_max - thr_min
  cnt = [ [ [ 0 for d in range(d_max) ] for ch in range (ch_max)] for thr in range( thr_nb )]

  feb_ctl[asic_idx].write(130, 4, vp) # test pulse Recommended value between 80-200
  log.info( "Volt_pulse = " + '{:3d}'.format(vp) )

  thr_idx = 0
  for thr in range( thr_min, thr_max ):
    feb_ctl[asic_idx].write(130, 10, thr) # VrefT threshold
    log.info( "Fast_Thr " + '{:3d}'.format(thr) + ": " )

    # Loop on groups
    for grp in range (grp_min, grp_max):
      feb_ctl[asic_idx].write( 130, 5, grp)
      log.info("group: %3d", grp )

      # Reset ADC counters
      feb_ctl[asic_idx].write( 192, 2, 32)
      time.sleep(0.00001)
      feb_ctl[asic_idx].write( 192, 2,  0)

      # Generate calib pulses
      for i in range (0,test_npulse):
        feb_ctl[asic_idx].write( 130, 11, 128)
        time.sleep(0.0001)
        feb_ctl[asic_idx].write( 130, 11, 0)

      # readback counter values
      for ch in range( grp, ch_max, 4 ):
        for d in range( d_min, d_max ):
          count = d*2
          cnt[ thr_idx ][ ch ][ d ] =feb_ctl[ asic_idx ].read( ch, count )

    thr_idx += 1

  feb_ctl[asic_idx].write(130, 4, 0) # Reset pulser height to 0 to avoid pb


  log.info( " -----------------------------------------------------------------------"
            + " --------------------------------------" )

  ## Printout in log
  thr_idx = 0
  for thr in range( thr_min, thr_max ):
    log_line = "Slow_Thr: "
    log_line = log_line +  '{:5d}'.format( thr )
    log.info( log_line )

    log_line = "ADC Id    "
    for d in range (d_min, d_max):
      log_line = log_line + '{:5}'.format( d )
    log.info( log_line )

    ## Loop on Channels
    for ch in range ( 0, ch_max):
      log_line = "Chan " + '{:3d}'.format(ch) + ": "

      for d in range( d_min, d_max ):
        log_line = log_line + '{:5d}'.format( cnt[ thr_idx ][ ch ][ d ] )
      log.info( log_line )
    thr_idx += 1

  ## Write data to file
  myfile = open(filename_scan,"w+")

  thr_idx = 0
  for thr in range( thr_min, thr_max ):
    myfile.write( "Slow_Thr: " )
    myfile.write( '{:5d}'.format( thr ) )
    myfile.write( "\n" )


    myfile.write( "ADC Id    " )
    for d in range (d_min, d_max):
      myfile.write( '{:5}'.format( d ) )
    myfile.write( "\n" )

    ## Loop on Channels
    for ch in range ( 0, ch_max):
      myfile.write( "Chan " )
      myfile.write( '{:3d}'.format(ch) )
      myfile.write( ": " )

      for d in range( d_min, d_max ):
        myfile.write( '{:5d}'.format( cnt[ thr_idx ][ ch ][ d ] ) )
      myfile.write( "\n" )

    thr_idx += 1

  myfile.close()

  return

## TODO: Check if real difference with check_trim in fast mode TRUE apart from the initial register config
## TODO: Add MUCH mode!
## TODO: VRef as Param with
def check_trim_fast(feb_ctl, asic_idx, pol, filename_scan, vref_n = 26, vref_p = 55, vref_t = 128, vref_t_r = 122):

  ivp = 0
  d_counter = 0

  # ---------------  Polarirty selection --------------

  pol = pol

  # ---------------  Running settings --------------

  testch = 58
  rdch =63
  test_thr = 129

  test_delta_ch = 5

  loop_max = 30

  ch_min = 0    # 20
  ch_max = 128  #
  ch_step = 1

  d_min = 0
  d_max = 32

  ivp = 0
  vp_min = 0
  vp_max = 100
  vp_step = 1

  grp_min = 0
  grp_max = 4

  setdisc_flag = 0

  # --------------------------- ADC settings --------------------------------------------
  '''
  vref_n = 26    # Vref_N   AGH:  31    Test:  22
  vref_p = 55    # Vref_P   AGH:  48    Test:  51
  vref_t = 128   # Vref_T   AGH: 188    Test: 184         bit7: enable   5..0: threshold
  vref_t_r = 122
  '''
  # -------------------------------------------------------------------------------------
  shslowfs = 0    # shaping time ADC
  # --------------------------- FAST disc settings --------------------------------------

  thr2_glb = 40

  if (pol == 1):
    feb_ctl[asic_idx].write_check(130,2,163)   #  163 holes     131 electrons
    print " "
    print "____HOLES MODE____"
    filename_scan = filename_scan+"_holes"
  print " "
  if (pol == 0):
    feb_ctl[asic_idx].write_check(130,2,131)   #  163 holes     131 electrons
    print " "
    print "____ELECTRONS MODE____"
    filename_scan = filename_scan+ "_elect"
  print " "

  myfile_fast_noise = open(filename_scan+".txt","w+")


  # ---------------------------------------------------
  feb_ctl[asic_idx].write_check(130, 0,31)
  feb_ctl[asic_idx].write_check(130, 13,31)

  print " "
  print "......Setting ADC reference voltages...... "
  print " "
  feb_ctl[asic_idx].write_check(130, 8,vref_n)
  feb_ctl[asic_idx].write_check(130, 9,vref_p)
  feb_ctl[asic_idx].write_check(130,10,vref_t)
  feb_ctl[asic_idx].write(130,18,vref_t_r)
  print "VRef_N: ",feb_ctl[asic_idx].read(130, 8)
  print "VRef_P: ",feb_ctl[asic_idx].read(130, 9)
  print "VRef_T: ",feb_ctl[asic_idx].read(130,10)

  print " "
  print "......Setting FAST reference voltages...... "
  print " "
  feb_ctl[asic_idx].write_check(130, 7,thr2_glb)
  print "Thr2_global: ",feb_ctl[asic_idx].read(130, 7)

  # ------------------------------- Checking trim --------------------------------------

  # resets
  print "Resetting front-end channels "
  print "Resetting ADC counters"
  print "Reset channel fifos"
  feb_ctl[asic_idx].write_check(192,2,42)
  time.sleep(0.00001)
  feb_ctl[asic_idx].write_check(192,2,0)

  # channel mask disable. All channels enabled
  feb_ctl[asic_idx].write_check(192, 3, 0)


  print " "
  ### resets
  print "1. Resetting front-end channels "
  print "2. Resetting ADC counters"
  print "3. Reset channel fifos"
  feb_ctl[asic_idx].write_check(192,2,42)
  time.sleep(0.00001)
  feb_ctl[asic_idx].write_check(192,2,0)

  vcnt = [[[0 for vp in range(vp_min,vp_max+1)] for d in range(d_min,d_max)] for ch in range(ch_max/ch_step)]
  #vcnt = [[[0 for vp in range(5000)] for d in range(20,d_max)] for ch in range(ch_max/ch_step)]

  nd = 31
  nthr = 256
  nch = 256

  print " "
  print "......Start acquiring data...... "
  print " "

  # ------------------------------------------------------
  # In case to set all ch-disc to the typical value(128)
  # ------------------------------------------------------
  '''
  for ch in range(ch_min,ch_max):
    for d in range(d_min,d_max):
      n=61-2*d
      sts.write_check(ch,n,128)
  '''
  # loop over test charge range
  for vp in range(vp_min,vp_max,vp_step):
  #for vp in range(5000):
    a = (vp*15.)/256.
    print a# Pulse height value in fC
    print "vp: ", '{:4d}'.format(vp), " (", '{:3f}'.format(a), ")", "\n"

    if ((vp<vp_min) or (vp>vp_max)):
      print "Pulse amplitude should be in range: ", vp_min, "-", vp_max, ". Currently it is set to ", vp, "\n"

    feb_ctl[asic_idx].write_check(130, 4, vp)
    #sts.write_check(130, 4, 61)
    print "vpulse: ", feb_ctl[asic_idx].read(130,4) , "\n"

    max_ch_grp =0
    #loop over groups
    for grp in range(grp_min, grp_max):
      #max_ch_grp = 124+ grp
      grp_shslow = ((shslowfs & 0x3)<<2 | (grp & 0x3)) # Included the slow shaper configuration (90,130,220,280ns)


      # ADC counters resets
      feb_ctl[asic_idx].write_check(192,2,63)
      time.sleep(0.00001)
      feb_ctl[asic_idx].write_check(192,2,0)

      feb_ctl[asic_idx].write_check(130, 5, grp_shslow)
      print "group", '{0:04b}'.format(feb_ctl[asic_idx].read(130,5)), "\n"
      # Number of trigger pulses

      for npulse in range(0,loop_max):
        #print " loop ", npulse, "\n"
        # Pulse triggering
        feb_ctl[asic_idx].write_check(130,11,128)
       # time.sleep(0.001)
        feb_ctl[asic_idx].write_check(130,11, 0)

        ## read counters
      ch_counter =0
      for ch in range(grp,ch_max,4):
        #print "ch  ", ch,
        cnt_val = 0
        d_counter =0
        #cnt_val =0
        for d in range(d_min,d_max):
          count = d*2
          #print "d: ", d, " counter: ", count, "\n"
          cnt_val = feb_ctl[asic_idx].read(ch,count)
          vcnt[ch][d_counter][ivp] = cnt_val
          d_counter +=1
          #print cnt_val,
        #print "\n"
        ch_counter +=4

      ch_counter =grp
      for ch in range(grp,ch_max,4):
          print "cnt_ch: ", '{:4d}'.format(ch),
          d_counter = 0
          for d in range(d_min,d_max):
            print '{:4d}'.format(vcnt[ch][d_counter][ivp]),
            d_counter+=1
          ch_counter +=4
          print "\n"

    ivp+=1

  print " "


  ivp = 0
  for vp in range(vp_min,vp_max,vp_step):
    ch_counter = 0
    for ch in range(ch_min,ch_max, ch_step):
      print "vp ", '{:4d}'.format(vp), "   ch: ", '{:4d}'.format(ch), ": ",
      myfile_fast_noise.write("vp")
      myfile_fast_noise.write('{:4d}'.format(vp))
      myfile_fast_noise.write("   ch ")
      myfile_fast_noise.write('{:4d}'.format(ch))
      myfile_fast_noise.write(": ")
      d_counter = 0
      for d in range(d_min,d_max):
        print '{:4d}'.format(vcnt[ch][d_counter][ivp]),
        myfile_fast_noise.write('{:6d}'.format(vcnt[ch][d_counter][ivp]))
        d_counter+=1
      ch_counter+=1
      print "\n"
      myfile_fast_noise.write("\n")
    ivp+=1

  ##
  ## ----------------- Quick noise and linearity analysis ---------------------##
  ##

  print ""
  print "............. Quick noise- linearity analysis ............"
  print ""
  d_list =[24,25,26]
  d_len=len(d_list)
  print "d_len: ",d_len

  hnoise = [[0 for d in range(d_len)] for ch in range(ch_min, ch_max)]
  hmean = [[0 for d in range(d_len)] for ch in range(ch_min, ch_max)]
  ch_array = [0 for ch in range(ch_min, ch_max)]
  hnoise_avg = [0 for ch in range(ch_min, ch_max)]
  hmean_avg = [0 for ch in range(ch_min, ch_max)]

  for ch in range(ch_min, ch_max):
    for d in d_list:
      ivp=0
      for vp in range(vp_min, vp_max, vp_step):
        if (vcnt[ch][d][ivp]>1.1*loop_max):
          vcnt[ch][d][ivp]=loop_max
          ivp+=1

  for ch in range(ch_min, ch_max):
    d_counter = 0
    for d in d_list:
      d_cnt = 0;
      sum_delta = 0.001
      sum_mean = 0
      ivp =1
      for vp in range(vp_min+1, vp_max, vp_step):
        d_cnt = vcnt[ch][d][ivp]-vcnt[ch][d][ivp-1]
        sum_delta+=d_cnt
        sum_mean +=(vp+vp_min)*d_cnt
        ivp+=1

      hmean[ch][d_counter] =float(sum_mean/sum_delta)
      d_counter+=1

  for ch in range(ch_min, ch_max):
    d_counter = 0
    for d in d_list:
      d_cnt = 0
      sum_delta = 0.001
      sum_sigma = 0
      ivp =1
      for vp in range(vp_min+1, vp_max, vp_step):
        d_cnt = vcnt[ch][d][ivp]-vcnt[ch][d][ivp-1]
        sum_delta+=d_cnt
        sum_sigma +=((vp+vp_min)-hmean[ch][d_counter])*((vp+vp_min)-hmean[ch][d_counter])*d_cnt
        ivp+=1
      print "suma delta", sum_delta
      print "suma sigma", sum_sigma
      hnoise[ch][d_counter] = math.sqrt(sum_sigma/sum_delta)
      d_counter+=1

  for ch in range(ch_min, ch_max):
    ch_array[ch] = ch
    d_counter =0
    print "ch: ", '{:4d}'.format(ch),
    for d in d_list:
      hnoise_avg[ch]+= hnoise[ch][d_counter]
      hmean_avg[ch]+= hmean[ch][d_counter]
      if hnoise[ch][d_counter]>0:
        d_counter+=1

    hnoise_avg[ch]= 350*float(hnoise_avg[ch]/d_len)

    d_counter+=1

    print "enc: ", '{:4f}'.format(hnoise_avg[ch])



  ##
  ## ----------------- Plot noise and linearity analysis ---------------------##
  ##

  f = plt.figure()

  plt.step(ch_array,hnoise_avg)
  plt.xlabel('Channel number')
  plt.ylabel('ENC[electrons]')
  plt.title('Quick noise estimation')
  plt.grid(True, linestyle='--', color='0.75')
  plt.show()

  f.savefig(filename_scan+'.png', bbox_inches = 'tight' )

  myfile_fast_noise.close()


## TODO: Add MUCH mode?
def connect_check(feb_ctl, asic_idx, filename_conn):

  date = time.strftime("%y%m%d")
  asic_number = 2

  thr_broken = 0.4
  loop_max = 5

  feb_ctl[asic_idx].write_check(130, 8,26)
  feb_ctl[asic_idx].write_check(130, 9,58)
  feb_ctl[asic_idx].write_check(130,10,128)
  feb_ctl[asic_idx].write(130,18,180)


#  filename_conn = "/opt/cbmsoft/python_ipbus_gbtx/run/mcbm/sts/conn_check/conn_file_feb_4_" +date+"_asic_id_"+str(asic_number)
  #filename_conn = "./Tests/box_"+str(box_nr)+"conn_" +date+"_"+"_asic_pos_id_"+str(asic_pos_id)+".txt"
  vcnt = [[[0 for vp in range(0,100)] for d in range(d_min,d_max)] for ch in range(ch_min,ch_max)]
  cnt = [[0 for d in range(d_min,d_max)] for ch in range(ch_min,ch_max)]
  ch_array = [0 for ch in range(ch_min,ch_max)]
  suma_ch = [0 for ch in range(ch_min,ch_max)]
  average =[0 for ch in range(ch_min,ch_max)]
  ch_even=["" for ch in range(64)]
  ch_odd =["" for ch in range(64)]
  ch_array_even =[0 for ch in range(64)]
  ch_array_odd = [0 for ch in range(64)]
  thr = [0 for ch in range(ch_min,ch_max)]
  #myfile_conn=open(filename_conn, "w+")

  feb_ctl[asic_idx].write_check(130,4,0)
  #sts.write_check(130,11,128)
  #sts.write_check(130,10,vref_t)
  for nloop in range (loop_max):
    for grp in range(grp_min, grp_max):
      # ADC counters resets
      feb_ctl[asic_idx].write_check(192,2,63)
      time.sleep(0.00001)
      feb_ctl[asic_idx].write_check(192,2,0)
      for ch in range(grp,ch_max,4):

        print "ch  ", ch,
        cnt_val = 0
        for d in range(d_min,d_max):
          count = d*2
          #print "d: ", d, " counter: ", count, "\n"
          cnt_val = feb_ctl[asic_idx].read(ch,count)&0xfff
          vcnt[ch][d][nloop] = cnt_val
          print '{:4d}'.format(cnt_val),

        print "\n"

    nloop +=1



  '''
  for nloop in range(0,loop_max):
    for ch in range(ch_min,ch_max):
      myfile_conn.write("nloop")
      myfile_conn.write('{:4d}'.format(nloop))
      myfile_conn.write("   ch ")
      myfile_conn.write('{:4d}'.format(ch))
      myfile_conn.write(": ")
      for d in range(d_min,d_max):
        #print '{:6d}'.format(vcnt[ch][d][nloop]),
        myfile_conn.write('{:6d}'.format(vcnt[ch][d][nloop]))
        #print "\n"
      myfile_conn.write("\n")
      '''

  sum_ave = 0
  sum_total = 0
  ave_even = 0
  even_cnt=0
  odd_cnt=0
  for ch in range(ch_min+20,ch_max-10):
    for d in range(d_min,d_max):
      for nloop in range(0,loop_max):
        sum_ave +=vcnt[ch][d][nloop]
    ave_even = float (sum_ave/98.)
  broken_ch_conn_check = []
  for ch in range(ch_min,ch_max):
    ch_array[ch]= ch
    sum_total = 0
    average[ch] = ave_even
    thr[ch]=ave_even*thr_broken
    print "ch: ",'{:3d}'.format(ch),
    for d in range(d_min,d_max):
      for nloop in range(0,loop_max):
        sum_total +=vcnt[ch][d][nloop]
        #suma_ch[ch]+=vcnt[ch][d][nloop]
    suma_ch[ch] = sum_total

    if ch%2 == 0:
      ch_even[even_cnt]="even"
      ch_array_even[even_cnt]=ch
      even_cnt+= 1
    else:
      ch_odd[odd_cnt]="odd"
      ch_array_odd[odd_cnt]=ch
      odd_cnt+=1
    print '{:5d}'.format(sum_total)," ", '{:3d}'.format(int(ave_even)),
    #print '{:5d}'.format(suma_ch[ch])," ", '{:3d}'.format(int(ave_even)),

    if (float(sum_total/(ave_even+1))<thr_broken):
      print "---------- Broken channel -------\n"
      broken_ch_conn_check.append(ch)
    else:
      print "--------- Connect channel -------\n"



  print " "
  print "----------------- List of broken channels: ------------------"

  print " "
  print "Total number of broken channels: ", '{:4d}'.format(len(broken_ch_conn_check))
  print " "

  print "List of broken channels: "
  for i in range(len(broken_ch_conn_check)):
    print str(broken_ch_conn_check[i]), ",",
  print " "

  '''
  myfile_conn.write("\n")
  myfile_conn.write("Total number of channels with problems: ")
  myfile_conn.write('{:4d}'.format(len(broken_ch_conn_check)))
  myfile_conn.write("\n")
  myfile_conn.write("Broken or channels with problems:  ")
  for i in range(len(broken_ch_conn_check)):
    myfile_conn.write(str(broken_ch_conn_check[i]))
    myfile_conn.write(", ")


  myfile_conn.close()
  '''


  f, (axs1,axs2) = plt.subplots(2)
  f.patch.set_facecolor('#bde3ff')
  axs1.step(ch_array,suma_ch, where='mid')
  axs1.plot(ch_array,average, linestyle='-.')
  axs1.plot(ch_array,thr)
  axs1.set_xlabel('Channel number')
  axs1.set_ylabel('No.Counts')
  axs1.set_title('Connection Check')
  axs1.grid(True, linestyle='--', color='0.75')
  axs1.set_xlim(0,127)
  axs1.set_ylim(bottom =-0.5)
  axs1.legend(['Number of Counts', 'Average', 'Broken_channel_THR'],loc='upper left')
  y_broken= ["" for i in range (len(broken_ch_conn_check))]
  axs2.scatter(ch_array_even,ch_even,  marker= 'D',s=100, color ='green')
  axs2.scatter(ch_array_odd,ch_odd,  marker= 'D',s=100, color='green')
  for i in range(len(broken_ch_conn_check)):
        if broken_ch_conn_check[i]%2 ==0:
           y_broken[i]="even"
        else:
            y_broken[i] = "odd"

  axs2.scatter(broken_ch_conn_check,y_broken,  marker= 'D',s=100, color ='red')
  axs2.set_xlabel('Channel number')
  axs2.set_ylabel('Channel group')
  axs2.set_title('Connection Check')
  axs2.set_xlim(-0.5,127.5)
  axs2.set_ylim(bottom =-0.5)
  axs2.grid(True, linestyle='--', color='0.75')

  #plt.show()
  f.set_size_inches(18.5, 10.5)
  f.savefig(filename_conn + '.png', dpi=300 ) #bbox_inches = 'tight')


  return 0


# ------------------------ TEMPERATURE CHECK ----------------------------#

#def diag_circ_test(feb_ctl, asic_idx):
    ##tests the built in diagnostic circuit
    #feb_ctl[asic_idx].write(130,21,31) #diagnostic circuit current reference: default: 31
    #print "testing diagnostic circuit"


    #if False:
        #print "DAC range scan 0 throuth 255, step=1"
        #for i in range(0,256):
            #print str(i)
            #feb_ctl[asic_idx].write(130,22,int(i))
            #time.sleep(0.01)

    #if True:
        #print "measurement of internal values (sweep)"
        #for ch in range(0, 8):
            #feb_ctl[asic_idx].write(130,20,ch) #diagnostic circuit input mux (0: aux, 5: bias_CSA, 3:vTemp, 7: VDDM)
            #print "set mux to ", str(ch)
            #time.sleep(0.05)
            #diag_circuit_monitor()

    #if False:
        #print "set mux to VTEMP"
        #feb_ctl[asic_idx].write(130,20,3) #diagnostic circuit input mux (0: aux, 5: bias_CSA, 3:vTemp, 7: VDDM)
        #while True:
            #time.sleep(0.5)
            #diag_circuit_monitor()

def diag_circuit_monitor(feb_ctl, asic_idx, quantity="VDDM", verbose=True):
    dac_thr=0b10000000 #half range: starting point

    if quantity=="VDDM":
        feb_ctl[asic_idx].write(130,20,7)
    elif quantity=="CSA_BIAS":
        feb_ctl[asic_idx].write(130,20,5)
    elif quantity=="TEMP":
        feb_ctl[asic_idx].write(130,20,3)
    elif quantity=="AUX":
        feb_ctl[asic_idx].write(130,20,0)
    else:
        print "unknown potential"
    for i in range(0,8):
        feb_ctl[asic_idx].write(130,22,dac_thr)
        time.sleep(0.01)
        result = feb_ctl[asic_idx].read(192,34)
        #print "iter: ", i, "result: ", result, "tempval:" , dac_thr
        if result>0:
            if i==7:
                pass
            else:
                dac_thr=dac_thr|(2**(6-i)) #set next bit
        else:
            dac_thr=dac_thr&~(2**(7-i)) #clear current
            if i==7:
                pass
            else:
                dac_thr=dac_thr|(2**(6-i)) #set next bit
    #print "final", dac_thr

     #outvolt = (dac_thr**2)*(-0.000002)+0.0065*dac_thr+0.0192
    outvolt = (dac_thr**2)*(-0.0026)+6.8971*dac_thr+3.2474
    if verbose==True:
    	if quantity=="TEMP":
            temperature = -0.5412*outvolt+379.91
            #fig = plt.figure(facecolor= '#bde3ff')
            #ax = fig.add_subplot(1, 1, 1)
            #xs = []
            #ys = []
            #def animate(i, xs, ys):

                #xs.append(dt.datetime.now().strftime('%H:%M:%S.%f'))
                #ys.append(temperature)

                ## Limit x and y lists to 20 items
                #xs = xs[-20:]
                #ys = ys[-20:]

                ## Draw x and y lists
                #ax.clear()
                #ax.plot(xs, ys)

                ## Format plot
                #plt.xticks(rotation=45, ha='right')
                #plt.subplots_adjust(bottom=0.30)
                #plt.title('Time')
                #plt.ylabel('Temperature (deg C)')
                #plt.grid(True, linestyle='--', color='0.75')
            #ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=3000)
            #plt.show()
            print quantity, "result is: ", int(dac_thr), " bin,  ", str(outvolt), " mV, ", temperature, "degC"
        else:
            print quantity, "result is: ", int(dac_thr), " bin,  ", str(outvolt), " mV"
    return [outvolt, dac_thr]


def temp_online_plotting(feb_ctl, asic_idx):
    while True:
        diag_circuit_monitor(feb_ctl, asic_idx, quantity="VDDM", verbose=False)
        diag_circuit_monitor(feb_ctl, asic_idx, quantity="CSA_BIAS", verbose=False)
        diag_circuit_monitor(feb_ctl, asic_idx, quantity="TEMP", verbose=True)
        diag_circuit_monitor(feb_ctl, asic_idx, quantity="AUX", verbose=False)
        time.sleep(3)
