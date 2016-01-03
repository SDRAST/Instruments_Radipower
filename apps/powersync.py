"""
Synchronized multi-channel power meter

  Test of class Radiometer using RadiPower heads
"""
import logging
import datetime
import time
import sys
import Queue

from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers
from support import check_permission
from support.logs import init_logging
from DatesTimes import UnixTime_to_MPL

if __name__ == "__main__":
  logging.basicConfig()
  mylogger = logging.getLogger()
  mylogger = init_logging(mylogger,
                          loglevel = logging.INFO,
                          consolevel = logging.DEBUG,
                          logname = "/tmp/logging.log")
  pm = find_radipowers()

  if check_permission('ops') == False:
    raise RuntimeError("Insufficient permission")
  
  if pm:
    mylogger.info("Starting powersync at %s", str(datetime.datetime.now()))
    radiometer = Radiometer(pm, rate=10)
    mylogger.debug(" radiometer initialized")
    mylogger.info(" radiometer started")
    data = {}
    # dummy reading to wake up Radipower
    for key in pm.keys():
      reading = pm[key].power() 
      data[key] = []
    run = True
    radiometer.start()
    while run:
      try:
        # This just gives the main loop something to do so an <Esc> will be
        # caught
        for pm in pmlist:
          time.sleep(0.0001)
      except KeyboardInterrupt:
        mylogger.warning(" main thread got Ctrl-C")
        radiometer.close()
        run = False
    mylogger.info(" radiometer stopped")    

  else:
    mylogger.error("No power meters found")
