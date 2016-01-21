"""
Dare! Total Power Radiometer server
"""
import logging

from support import NamedClass, check_permission

from support.pyro import initiate_server, PyroServer
from Electronics.Instruments.radiometer import Radiometer
from Electronics.Instruments.Radipower import find_radipowers

module_logger = logging.getLogger(__name__)
    
class RadiometerServer(PyroServer, Radiometer):
  """
  """
  def __init__(self, name):
    """
    """
    self.logger = logging.getLogger(module_logger.name+".RadiometerServer")
    super(RadiometerServer,self).__init__()
    self.logger.debug(" superclass initialized")
    if check_permission('ops') == False:
      raise RuntimeError("Insufficient permission to access USB")
    pm = find_radipowers()
    self.logger.debug(" initializing")
    Radiometer.__init__(self, pm, rate=0.2)
    data = {}
    # dummy reading to wake up Radipower
    for key in pm.keys():
      reading = pm[key].power() 
      data[key] = []
    self.run = True

if __name__ == "__main__":
  initiate_server(RadiometerServer, "radiometer_server")

