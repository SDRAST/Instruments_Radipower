"""
Synchronized multi-channel power meter
"""
import logging
import datetime
import time

from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers
from support import check_permission
from support.rtc import RTC

if __name__ == "__main__":
  """
  This is a test using HP power meters at Goldstone
  """
  mylogger = logging.getLogger()
  mylogger.setLevel(logging.INFO)

  pm, pmlist = find_radipowers()

  if check_permission('ops') == False:
    raise RuntimeError("Insufficient permission")
  
  if pmlist:
    mylogger.info("Starting powersync at %s", str(datetime.datetime.now()))
    radiometer = Radiometer(pm, pmlist)

    run = True
    try:
      while run:
        time.sleep(0.001)
    except KeyboardInterrupt:
      mylogger.warning(" main thread got Ctrl-C")
      radiometer.close()
      run = False
  else:
    mylogger.error("No power meters found")
