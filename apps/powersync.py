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
                          consolevel = logging.WARNING,
                          logname = "/tmp/logging.log")
  pm, pmlist = find_radipowers()

  if check_permission('ops') == False:
    raise RuntimeError("Insufficient permission")
  
  if pmlist:
    mylogger.info("Starting powersync at %s", str(datetime.datetime.now()))
    radiometer = Radiometer(pm, pmlist, rate=20)
    mylogger.debug(" radiometer initialized")
    mylogger.debug(" radiometer started")
    data = {}
    for key in pmlist:
      reading = pm[key].power() # dummy reading to wake up Radipower
      data[key] = []
    run = True
    radiometer.start()
    while run:
      try:
        for pm in pmlist:
          time.sleep(0.0001)
          #mylogger.debug(" reading queue %s", pm)
          #data[pm].append(radiometer.queue[pm].get(False))
          #mylogger.debug(" acquired %s at %s", data[pm][-1], datetime.datetime.now())
          # except Queue.Empty:
          # mylogger.debug(" no data on queue %s at %s",
          #                pm, str(datetime.datetime.now()))
          #except Exception, details:
          #mylogger.error("Exception: %s", details)
          #run = False
      except KeyboardInterrupt:
        mylogger.warning(" main thread got Ctrl-C")
        radiometer.close()
        run = False
    mylogger.debug(" radiometer stopped")    

  else:
    mylogger.error("No power meters found")
