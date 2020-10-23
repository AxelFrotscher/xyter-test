#!/usr/bin/python
import time
import logging as log

def i2c_wr_reg(hw,reg, val):
  hw.getNode(reg).write(val)
  hw.dispatch()
#  print "Write %s = %s" %(reg,hex(val))
  return

def i2c_rd_reg(hw,reg):
  val=hw.getNode(reg).read()
  hw.dispatch()
#  print "Read  %s = %s" %(reg, hex(val))
  return val

def i2c_write(hw, i2c_slave, dev, reg_nr, data):
  txr_rxr=i2c_slave+".txr_rxr"
  cr_sr=i2c_slave+".cr_sr"
  i2c_wr_reg(hw, txr_rxr,dev)
  i2c_wr_reg(hw, cr_sr, 0x90)
  while(1):
    val=i2c_rd_reg(hw, cr_sr)
    if ((val&2==0) & (val&128==0)):
      break
    time.sleep(0.1)
  i2c_wr_reg(hw,txr_rxr,reg_nr)
  i2c_wr_reg(hw,cr_sr,0x10)
  while(1):
    val=i2c_rd_reg(hw,cr_sr)
    if ((val&2==0)&(val&128==0)):
      break
    time.sleep(0.1)
  for i in range(len(data)):
    i2c_wr_reg(hw, txr_rxr,data[i])
    if (i==len(data)-1):
      i2c_wr_reg(hw,cr_sr,0x50)
    else:
      i2c_wr_reg(hw,cr_sr,0x10)
    while(1):
      val=i2c_rd_reg(hw,cr_sr)
      if ((val&2==0)&(val&128==0)):
        break
      time.sleep(0.1)
  return 0

def i2c_write_no_addr(hw, i2c_slave,dev, data):
  txr_rxr=i2c_slave+".txr_rxr"
  cr_sr=i2c_slave+".cr_sr"
  i2c_wr_reg(hw,txr_rxr,dev)
  i2c_wr_reg(hw,cr_sr,0x90)
  while(1):
    val=i2c_rd_reg(hw,cr_sr)
    if ((val&2==0) & (val&128==0)):
      break
    time.sleep(0.1)
  i2c_wr_reg(hw,txr_rxr,data)
  i2c_wr_reg(hw,cr_sr,0x50)
  while(1):
    val=i2c_rd_reg(hw,cr_sr)
    if ((val&2==0)&(val&128==0)):
      break
    time.sleep(0.1)
  return 0

def i2c_read(hw, i2c_slave, dev, reg_nr, num):
  txr_rxr=i2c_slave+".txr_rxr"
  cr_sr=i2c_slave+".cr_sr"
  i2c_wr_reg(hw,txr_rxr,dev)
  i2c_wr_reg(hw,cr_sr,0x90)
#  while(1):
#    val=i2c_rd_reg(hw,cr_sr)
#    if val & 0x20:
#      raise Exception("I2C arbitration lost")
#    if ((val&2==0) & (val&128==0)):
#      break
#    time.sleep(0.1)
  i2c_wr_reg(hw,txr_rxr,reg_nr)
  i2c_wr_reg(hw,cr_sr,0x10)
#  while(1):
#    val=i2c_rd_reg(hw,cr_sr)
#    if val & 0x20:
#      raise Exception("I2C arbitration lost")
#    if ((val&2==0)&(val&128==0)):
#      break
#    time.sleep(0.1)
  i2c_wr_reg(hw,txr_rxr,dev|1)
  i2c_wr_reg(hw,cr_sr,0x90)
#  while(1):
#    val=i2c_rd_reg(hw,cr_sr)
#    if val & 0x20:
#      raise Exception("I2C arbitration lost")
#    if ((val&2==0)&(val&128==0)):
#      break
#    time.sleep(0.1)
  data_out=[]
  for i in range(num):
    if i==num-1:
      i2c_wr_reg(hw,cr_sr,0x68)
#      while(1):
#        val=i2c_rd_reg(hw,cr_sr)
#        if (val&2==0):
#          break
#        time.sleep(0.1)
    else:
      i2c_wr_reg(hw,cr_sr,0x20)
#      while(1):
#        val=i2c_rd_reg(hw, cr_sr)
#        if val & 0x20:
#          raise Exception("I2C arbitration lost")
#        if ((val&2==0)&(val&128==0)):
#          break
#        time.sleep(0.1)
    data_out.append(i2c_rd_reg(hw, txr_rxr))
  return data_out

def bus_sel(hw, i2c_slave,bus):
  i2c_sel=i2c_slave+".i2c_sel"
  i2c_wr_reg(hw, i2c_sel, bus)
  return

def PCA9547_channel_sel(hw, i2c_slave,channel):
  if channel < 0:
    i2c_write_no_addr(hw, i2c_slave, 0xe0,   0)
  else:
    i2c_write_no_addr(hw, i2c_slave, 0xe0, 0x8 + channel)
  return

def FMS14Q_write_reg(hw, i2c_slave,addr, val):
  FMS14Q_adr=0xDC
  i2c_write(hw, i2c_slave,FMS14Q_adr, addr, [val])
  return

def FMS14Q_read_reg(hw, i2c_slave,addr):
  FMS14Q_adr=0xDC
  return i2c_read(hw, i2c_slave,FMS14Q_adr, addr, 1)[0]

def FMS14Q_SetFrq(hw, i2c_slave,frq):
  #Read settings for 0
  r0=FMS14Q_read_reg(hw, i2c_slave,0)
  cp0=r0 >> 6
  mint0=(r0 & 0x3e)>>1
  frac0=r0 & 1
  adr=4
  while(adr <= 11):
    frac0=frac0*256
    frac0=FMS14Q_read_reg(hw, i2c_slave,adr)|frac0
    adr=adr + 4
  r12=FMS14Q_read_reg(hw, i2c_slave,12)
  frac0=(frac0 * 2) | (r12 >> 7)
  n0=r12 & 0x7f
  r20=FMS14Q_read_reg(hw, i2c_slave,20)
  p0=r20 >> 6
  tmp=[1,2,4,5]
  p0v= tmp[p0]
  mint0=mint0|(r20 & 0x20)
  mtot=mint0+(frac0*(1.0/(1<<18)))
#  print "p0=%d p0v=%d n0=%d mint0=%d frac0=%d mtot=%d" %(p0,p0v,n0,mint0,frac0, mtot)
  fout=212.5e6
  fref=fout*n0/mtot
#  print "fref=%f" %(fref)
  #Now we look for the right divisor
  found=0
  P=0
  while(P<=3):
    PV=tmp[P]
    N=2
    while(N <= 126):
      fvco=N*PV*frq
      if((fvco >= 1.95e9)&(fvco <= 2.6e9)):
	found=1
	break
      if(N<6):
        N=N+1
      else:
        N=N+2
    if(found==1):
      break
    P=P+1
  #Check if the proper value was found
  if(found==0):
    log.error("Proper value of N not found")
    return
#  else:
#    print "fvco=%d N=%d P=%d" % (fvco, N, P)
  #Find the appropriate M
  M=fvco/fref
  #Divide M into integer and fractional part
  MINT=int(M)
  MFRAC=M-MINT
  #Shift bits appropriately
  MFRAC=int(MFRAC*(1<<18) + 0.5)
#  print "N=%d P=%d PV=%d MINT=%d MFRAC=%d" % (N, P, PV, MINT, MFRAC)
  #Now write the new settings back to the hardware, to channel 3
  #CP copy from channel 0
  r3=(cp0<<6)|((MINT&0x1f)<<1)|((MFRAC&0x20000)>>17)
  FMS14Q_write_reg(hw, i2c_slave,3,r3)
  r7=(MFRAC >> 9) & 0xff
  FMS14Q_write_reg(hw, i2c_slave,7,r7)
  r11=(MFRAC >> 1) & 0xff
  FMS14Q_write_reg(hw, i2c_slave,11,r11)
  r15=((MFRAC&0x01)<<7)|(N&0x7f)
  FMS14Q_write_reg(hw, i2c_slave,15,r15)
  #For r23 copy to channel 3 values from channel 0
  r23=FMS14Q_read_reg(hw, i2c_slave,20)
  #Now set only bits for P and MINT[5]
  r23=(r23 & 0x1f)|(P<<6)|(MINT& 0x20)
  FMS14Q_write_reg(hw, i2c_slave,23,r23)
  #Toggle the FSEL bits
  r18=FMS14Q_read_reg(hw, i2c_slave,18)
  #Clear those bits
  FMS14Q_write_reg(hw, i2c_slave,18,r18&0xe7)
  #set those bits
  FMS14Q_write_reg(hw, i2c_slave,18,r18|0x18)
  log.info("Set FM-S14 clock frequency to {:.2f} MHz Complete".format(float(frq)/1000000.0))

def ADN4604_read(hw, i2c_slave,addr):
  ADN4604_adr=0x96
  return i2c_read(hw, i2c_slave,ADN4604_adr, addr, 1)[0]

def ADN4604_write(hw, i2c_slave,addr,val):
  ADN4604_adr=0x96
  i2c_write(hw, i2c_slave,ADN4604_adr, addr, [val])

#The procedure below connects given input to output
#in the clock matrix n_in = -1 switches off the output
def ClkMtx_set_out(hw, i2c_slave,n_in,n_out):
  n_in=int(n_in)
  n_out=int(n_out)
  if ((n_in < -1)|(n_in > 15)):
    log.error("wrong n_in: {:d} (must be between -1 and 15)".format(n_in))
    return -1;
  if ((n_out < 0)|(n_out > 15)):
    log.error("wrong n_out: {:d} (must be between 0 and 15)".format(n_out))
  if n_in==-1:
    ADN4604_write(hw, i2c_slave,0x20+n_out,0x00)
  else:
    # Select the input and switch on the output
    # Number of register is 0x90+n_out/2
    nr_reg=0x90+int(n_out/2)
    # Nibble in the register is n_out % 2
    if (n_out%2==1):
      mask=0x0f
      val=n_in*16
    else:
      mask=0xf0
      val=n_in
    #Program the switch matrix
    old_val=ADN4604_read(hw, i2c_slave,nr_reg)
    ADN4604_write(hw, i2c_slave,nr_reg, (old_val&mask)|val)
    # Trigger matrix update
    ADN4604_write(hw, i2c_slave,0x81,0x00)
    ADN4604_write(hw, i2c_slave,0x80,0x01)
    # Switch on the output
    ADN4604_write(hw, i2c_slave,0x20+n_out,0x30)

def Si57x_write_reg(hw, i2c_slave,adr,val):
  Si57x_adr=0xaa
  i2c_write(hw, i2c_slave,Si57x_adr,adr,[val])

def Si57x_read_reg(hw, i2c_slave,addr):
  Si57x_adr=0xaa
  return i2c_read(hw, i2c_slave,Si57x_adr, addr, 1)[0]

def Si57xSetFrq(hw, i2c_slave,frq):
  #Save old mux setting and set mux to Si57x
  PCA9547_channel_sel(hw, i2c_slave,2)
  #Reset Silabs to initial settings
  Si57x_write_reg(hw, i2c_slave,0x87,0x01)
  #Now read rfreq
  r7=Si57x_read_reg(hw, i2c_slave,7)
  hsdiv=(r7&0xe0)>>5
  hsdiv=hsdiv+4
  n1=(r7&0x1f)<<2
  r8=Si57x_read_reg(hw, i2c_slave,8)
  n1=n1|((r8 & 192)>>6)
  n1=n1+1
  rfreq=r8&63
  adr=9
  while adr<=12:
    rfreq=rfreq*256
    rfreq=Si57x_read_reg(hw, i2c_slave,adr)|rfreq
    adr=adr+1
  fxtal=100e6*(1<<28)/rfreq*hsdiv*n1
  #Print the xtal frequency
#  print "fxtal=%f frq=%f" %(fxtal, frq)
  #Calculate the new values
  #To minimize the power consumption, we look for the minimal
  #value of N1 and maximum value of HSDIV, keeping the
  #DCO=frq*N1*HSDIV in range 4.85 to 5.67 GHz
  #We browse possible values of N1 and hsdiv looking for the best
  #combination
  #Below is the list of valid N1 values
  hsdvals=[[7,11.0],[5,9.0],[3,7.0],[2,6.0],[1,5.0],[0,4.0]]
  #set hsdvals {{0 4.0} {1 5.0} {2 6.0} {3 7.0} {5 9.0} {7 11.0}}
  found=0
  for i in range(len(hsdvals)):
    hsdl=hsdvals[i]
    hsdr=hsdl[0]
    hsdv=hsdl[1]
#    print "hsdr=%d hsdv=%d" %(hsdr, hsdv)
    #Now we check possible hsdiv values and take the greatest
    #matching the condition
    n1v=1
    while n1v<=128:
      fdco=frq*n1v
      fdco=fdco*hsdv
#      print "frq=%f fdco=%f n1v=%d hsdv=%f" %(frq, fdco, n1v, hsdv)
      if (fdco >= 4.85e9)&(fdco<=5.67e9):
         found=1
         break
      if n1v<2:
        n1v=n1v+1
      else:
        n1v=n1v+2
    if found==1:
      break
  #Check if the proper value was found
  if found==0:
    log.error("Proper values N1 HSDIV not found")
    return
#  else:
#    print "fdco=%f N1=%d HSDIV=%f" %(fdco, n1v, hsdv)
  #Calculate the nfreq
  nfreq=int(fdco*(1<<28)/fxtal + 0.5)
#  print hex(nfreq)
  Si57x_write_reg(hw, i2c_slave,0x89,0x10)
  Si57x_write_reg(hw, i2c_slave,0x87,0x30)
  #Decrement n1v, before writing to the register
  n1v=n1v-1
  #Now store the values
  r7=(hsdr<<5)|(n1v>>2)
#  print "r7: %s" %(hex(r7))
  Si57x_write_reg(hw, i2c_slave,7,r7)
  adr=12
  while adr>8:
    rval=nfreq&255
#    print "r%d: %s" %(adr,hex(rval))
    Si57x_write_reg(hw, i2c_slave,adr,rval)
    nfreq=nfreq >> 8
    adr=adr-1
  rval=((n1v&0x3)<<6)|nfreq
  Si57x_write_reg(hw, i2c_slave,8, rval)
#  print "r8: %s" %(hex(rval))
  Si57x_write_reg(hw, i2c_slave,0x89,0x00)
  Si57x_write_reg(hw, i2c_slave,0x87,0x40)
  PCA9547_channel_sel(hw, i2c_slave,4)
  log.info("Set Si570 clock frequency to {:.2f} MHz Complete".format(frq/1000000.0))

