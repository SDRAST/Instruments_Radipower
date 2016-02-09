"""
Dare! Total Power Radiometer server
"""
import logging
import sys

from support import NamedClass, check_permission
from support.logs import get_loglevel, initiate_option_parser, init_logging
from support.logs import set_module_loggers
from support.pyro import PyroServerLauncher, PyroServer
from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers

module_logger = logging.getLogger(__name__)
    
class RadiometerServer(PyroServer, Radiometer):
  """
  """
  def __init__(self, name, rate=1./60):
    """
    """
    self.logger = logging.getLogger(module_logger.name+".RadiometerServer")
    super(RadiometerServer,self).__init__()
    self.logger.debug(" superclass initialized")
    if check_permission('ops') == False:
      raise RuntimeError("Insufficient permission to access USB")
    pm = find_radipowers()
    self.logger.debug(" initializing")
    Radiometer.__init__(self, pm, rate=rate)
    data = {}
    # dummy reading to wake up Radipower
    for key in pm.keys():
      reading = pm[key].power() 
      data[key] = []
    self.run = True

if __name__ == "__main__":

  def main(name):
    """
    """
    p = initiate_option_parser(
     """Generic Pyro server which servers as a template for actual servers.""")
    # Add other options here
  
    opts, args = p.parse_args(sys.argv[1:])
  
    # This cannot be delegated to another module or class
    mylogger = init_logging(logging.getLogger(),
                            loglevel   = get_loglevel(opts.file_loglevel),
                            consolevel = get_loglevel(opts.stderr_loglevel),
                            logname    = opts.logpath+name)
    mylogger.debug(" Handlers: %s", mylogger.handlers)
    loggers = set_module_loggers(eval(opts.modloglevels))

    psl = PyroServerLauncher(name+"Server") # the name by which the Pyro task is known
    m = RadiometerServer(name) # identifier for the hardware
    psl.start(m)
  
    psl.finish()
  
  main("Radiometer")
