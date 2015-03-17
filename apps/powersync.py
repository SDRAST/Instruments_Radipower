"""
Synchronized multi-channel power meter

  Test of class Radiometer using RadiPower heads
"""
import logging
import datetime
import time
import sys
from pylab import *

from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers
from support import check_permission
from support.rtc import RTC
from DatesTimes import UnixTime_to_MPL

if __name__ == "__main__":
  mylogger = logging.getLogger()
  mylogger.setLevel(logging.DEBUG)

  pm, pmlist = find_radipowers()

  if check_permission('ops') == False:
    raise RuntimeError("Insufficient permission")
  
  if pmlist:
    mylogger.info("Starting powersync at %s", str(datetime.datetime.now()))
    radiometer = Radiometer(pm, pmlist, rate=16)
    run = True
    radiometer.start()
    data = {}
    for pm in pmlist:
      data[pm] = []
    while run:
      for pm in pmlist:
        try:
          data[pm].append(radiometer.queue[pm].get())
        except KeyboardInterrupt:
          mylogger.warning(" main thread got Ctrl-C")
          radiometer.close()
          run = False
        except AttributeError, details:
          try:
            mylogger.error(" AttributeError reading queue %d\n%s",
                           pm, str(details), exc_info=True)
          except KeyboardInterrupt:
            mylogger.warning(" main thread logger got Ctrl-C")
            radiometer.close()
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
