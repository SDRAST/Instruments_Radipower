# -*- coding: utf-8 -*-
"""
I would like to suggest that you use the following sequence every time you
connect to a RadiPower:
1.  Open the USB/serial port (in your case: /dev/ttyUSB15)
2.  Wait for 20 ms
3.  Send a ID_NUMBER?\n
4.  Read the response. Is it an Error then goto step 3. and try again
Just retry steps 3. And 4. For a maximum of 3 times.

Our internal device drivers are also using a retry-loop on that location. 
"""
plot_it = True

from os import environ
from time import sleep, time
if plot_it:
  from pylab import *
import logging

from Electronics.Instruments.Radipower import Radipower, IDs, find_radipowers
from support.process import invoke
from support.logs import init_logging

def check_permission(group):
  p = invoke("groups")
  groups = p.stdout.readline().split()
  try:
    groups.index(group)
  except ValueError:
    if environ['USER'] != 'root':
      raise RuntimeError("You must be in group '"+group+"', root or 'sudo'er")
  mylogger.info(" User permissions verified")
 
if __name__ == "__main__":
  logging.basicConfig(level=logging.DEBUG)
  mylogger = logging.getLogger()
  init_logging(mylogger, loglevel=logging.DEBUG,
                         consolevel=logging.DEBUG,
                         logname="/usr/local/logs/Radipowerradipower.log")
  
  check_permission('dialout')
  
  rp, rp_keys = find_radipowers()
  readings = []
  start = time()
  mylogger.setLevel(logging.INFO)
  for key in rp_keys:
    readings.append(rp[key].get_power())
    rp[key].close()
  stop = time()
  rate = len(rp_keys)/(stop-start)
  print rate,"Sps"

  if plot_it:
    bar(rp_keys, readings, align='center')
    ylabel("Power (dBm)")
    ylim(-40,-30)
    xlabel("Channel")
    title(str(len(rp_keys))+" samples at %5.1f samples/sec" % rate)
    grid()
    show()