"""
Dare! Total Power Radiometer server

Instead of superceding the inherited loggers it may be possible simply to 
rename them.
"""
import logging
import signal
import sys
import time
from os.path import dirname

from support import NamedClass, check_permission, sync_second
from support.logs import get_loglevel, initiate_option_parser, init_logging
from support.logs import set_module_loggers
from support.pyro import PyroServerLauncher, PyroServer
from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers

module_logger = logging.getLogger(__name__)
    
class RadiometerServer(PyroServer, Radiometer):
  """
  Pyro server for the Radipower radiometer
  
  Public Attributes::
    datafile - file object to which the data are written
    logger   - logging.Logger object
    run      - True when server is running
  Inherited from Radiometer::
    integration     - 2*update_interval for Nyquist sampling
    last_reading    - results of the last power meter reading
    logger          - logging.Logger object but superceded
    pm_reader       - DeviceReadThread object
    reader_done     - threading.Event object, set when reading has been taken
    reader_started  - threading.Event object, set when a reading is started
    take_data       - threading.Event object to signal readers to take reading
    update_interval - inverse of reading rate
  Inherited from Pyroserver::
    logger - logging.Logger object but superceded
    run    - True if server is running
  """

  def __init__(self, name, logpath="/var/tmp/", rate=1./60):
    """
    Initialize a Radipower radiometer server
    
    At present with a Raspberry Pi controller the maximum rate is about 1/s.
    
    @param name : name for the Pyro nameserver
    @type  name : str
    
    @param logpath : directory for the radiometer datafiles
    @type  logpath : str
    
    @param rate : number of readings per second
    @type  rate : float
    """
    super(RadiometerServer,self).__init__()
    # Replaces inherited logger
    self.logger = logging.getLogger(module_logger.name+".RadiometerServer")
    self.logger.debug(" superclass initialized")
    if check_permission('ops') == False:
      raise RuntimeError("Insufficient permission to access USB")
    pm = find_radipowers()
    self.logger.debug(" initializing")
    Radiometer.__init__(self, pm, rate=rate)
    # Open power logging file:
    self.open_datafile(logpath)
    self.run = True
    self.start()
  
  def stop(self):
    """
    Stops the radiometer and closes the datafile
    """
    self.close() # for the Radiometer
    self.datafile.close()
    self.logger.info("close: finished.")

  def open_datafile(self, logpath):
    """
    Opens the datafile
    
    The filename is RMYYY-DDD-HHMM.csv
    
    @param logpath : directory for the radiometer datafiles
    @type  logpath : str
    """
    filename = time.strftime("RM%Y-%j-%H%M.csv", time.gmtime(time.time()))
    self.datafile = open(logpath+filename,"w")
      
  def change_rate(self, rate):
    """
    Change the reading rate
    
    Closes the datafile, sets the new rate and open a new datafile.
    """
    # ? suspend the read threads
    # pause the timer
    signal.setitimer(signal.ITIMER_REAL, 0)
    # close the data file
    logpath = dirname(self.datafile.name)
    self.datafile.close()
    # set the new rate
    self.set_rate(rate)
    # open a new data file
    self.open_datafile(logpath+"/")
    # ? resume the read threads
    # resume the timer
    sync_second()
    signal.setitimer(signal.ITIMER_REAL, self.update_interval, self.update_interval)

if __name__ == "__main__":

  def main(name):
    """
    Starts a Pyro server launcher which launches the radiometer server
    
    Provides command line options for logging and starts the top-level logger.
    """
    p = initiate_option_parser(
     """Generic Pyro server which servers as a template for actual servers.""")
    # Add other options here
  
    opts, args = p.parse_args(sys.argv[1:])
  
    # This cannot be delegated to another module or class
    mylogger = init_logging(logging.getLogger(),
                            loglevel   = get_loglevel(opts.file_loglevel),
                            consolevel = get_loglevel(opts.stderr_loglevel),
                            logname    = opts.logpath+name+".log")
    mylogger.debug(" Handlers: %s", mylogger.handlers)
    loggers = set_module_loggers(eval(opts.modloglevels))

    psl = PyroServerLauncher(name+"Server") # the name by which the Pyro task is known
    m = RadiometerServer(name, logpath=opts.logpath+name+"/") # identifier for the hardware
    psl.start(m)
    # clean up after the server stops
    psl.finish()
  
  main("Radiometer")
