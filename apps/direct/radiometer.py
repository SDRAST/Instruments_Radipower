"""
Synchronized multi-channel power meter using realtime clock
"""
import logging
import datetime
import time

from support import check_permission
from support.rtc import RTC

from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers

if __name__ == "__main__":
  """
  This is a test using HP power meters at Goldstone
  """
  mylogger = logging.getLogger()
  mylogger.setLevel(logging.INFO)

  pm = find_radipowers()
  
  rtc = RTC()
  rtc.N_pps.start()

  mylogger.info("Starting pm_reader at %s", str(datetime.datetime.now()))
  radiometer = Radiometer(pm, rtc)
  run = True
  try:
    while run:
      time.sleep(0.1)
  except KeyboardInterrupt:
    run = False

