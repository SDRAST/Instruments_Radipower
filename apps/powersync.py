"""
Synchronized multi-channel power meter

  Test of class Radiometer using RadiPower heads
"""
import logging
import datetime
import time
import sys
import Queue
from pylab import *

from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers
from support import check_permission
from support.logs import init_logging
from DatesTimes import UnixTime_to_MPL

if __name__ == "__main__":
  logging.basicConfig()
  mylogger = logging.getLogger()
  mylogger = init_logging(mylogger,
                          loglevel = logging.DEBUG,
                          consolevel = logging.DEBUG,
                          logname = "/tmp/logging.log")

  pm, pmlist = find_radipowers()

  if check_permission('ops') == False:
    raise RuntimeError("Insufficient permission")
  
  if pmlist:
    mylogger.info("Starting powersync at %s", str(datetime.datetime.now()))
    radiometer = Radiometer(pm, pmlist, rate=1)
    mylogger.debug(" radiometer initialized")
    run = True
    radiometer.start()
    mylogger.debug(" radiometer started")
    data = {}
    for pm in pmlist:
      data[pm] = []
    while run:
      for pm in pmlist:
        try:
          pass
          #mylogger.debug(" reading queue %s", pm)
          #data[pm].append(radiometer.queue[pm].get(False))
          #mylogger.debug(" acquired %s at %s", data[pm][-1], datetime.datetime.now())
        except Queue.Empty:
          mylogger.debug(" no data on queue %s at %s",
                          pm, str(datetime.datetime.now()))
        except KeyboardInterrupt:
          mylogger.warning(" main thread got Ctrl-C")
          radiometer.close()
          run = False
        except Exception, details:
          mylogger.error("Exception: %s", details)
          run = False
    start = data[0][0][0]
    for pm in pmlist:
      ar = array(data[pm])
      plot(ar[:,0]-start, ar[:,1], '.', label=str(pm))
    title(time.ctime(data[0][0][0]))
    legend(numpoints=1)
    xlabel("%d samples/sec" % radiometer.rate)
    grid()
    show()
  else:
    mylogger.error("No power meters found")
