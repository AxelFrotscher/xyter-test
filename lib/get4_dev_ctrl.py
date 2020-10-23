#!/usr/bin/python
import math
import time
import get4_asic_defs

class get4_dev_ctrl:

  def __init__(self, hw, dev):
#    self.max_get4_number=max_get4
#    self.group_num=(int)(math.ceil(float(max_get4)/32.0))
    self.nb_gbtx = 6
    self.nb_masks = 2 * self.nb_gbtx
    self.hw=hw
    self.dev=dev

  def enable_slow_control_all(self):
    for i in range(self.nb_gbtx):
      node=self.dev+".SLCTRL_MASK%d_L" %(i)
      self.hw.getNode( node ).write( 0xffffffff )

      node=self.dev+".SLCTRL_MASK%d_H" %(i)
      self.hw.getNode( node ).write( 0x000000ff )

    self.hw.dispatch()
    print "All the slow control has been enabled"

  def disable_slow_control_all(self):
    for i in range(self.nb_gbtx):
      node=self.dev+".SLCTRL_MASK%d_L" %(i)
      self.hw.getNode( node ).write( 0x00000000 )

      node=self.dev+".SLCTRL_MASK%d_H" %(i)
      self.hw.getNode( node ).write( 0x00000000 )

    self.hw.dispatch()
    print "All the slow control has been disabled"

  def set_slow_control_all(self, masks):
    assert isinstance(masks, (list, tuple))
    assert self.nb_masks == len(masks)

    for i in range(self.nb_gbtx):
      node=self.dev+".SLCTRL_MASK%d_L" %(i)
      self.hw.getNode( node ).write( int( masks[ 2 * i ] ) )

      node=self.dev+".SLCTRL_MASK%d_H" %(i)
      self.hw.getNode( node ).write( int( masks[ 2 * i + 1 ] ) )

    self.hw.dispatch()
    print "All the slow control masks have been set"

  def get_slow_control_all(self):
    # Prepare array for storing the masks
    masks = []

    for i in range(self.nb_gbtx):
      node=self.dev+".SLCTRL_MASK%d_L" %(i)
      masks.append( self.hw.getNode( node ).read() )

      node=self.dev+".SLCTRL_MASK%d_H" %(i)
      masks.append( self.hw.getNode( node ).read() )

    self.hw.dispatch()
    print "All the slow control masks have been read"
    return masks

  def system_sync(self):
    print "Start initialize all the GET4 SYNC count... "

    ## Start by reading the current slow control mask
    old_masks = self.get_slow_control_all()

    ## Set slow control mask to enable for all
    self.enable_slow_control_all()

    ## Send SYNC command by generating a transition
    self.hw.getNode(self.dev+".GET4_SYNC_CMD").write(0x00000000)
    self.hw.dispatch()
    self.hw.getNode(self.dev+".GET4_SYNC_CMD").write(0xC0000000)
    self.hw.dispatch()

    ## Restore the slow control mask
    self.set_slow_control_all( old_masks )

    print "gDPB System synchronization command has been sent"
    return

  def get_pps_to_now(self):
    ppsToNow = self.hw.getNode( self.dev + ".PPS_TO_NOW" ).read()
    self.hw.dispatch()
    return ppsToNow

  def get_lts_sync_done(self):
    syncDone = self.hw.getNode( self.dev + ".SYNC_DONE" ).read()
    self.hw.dispatch()
    return syncDone



