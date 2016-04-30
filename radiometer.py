import logging

from Electronics.Instruments.radiometer import Radiometer

class DareRadiometer(Radiometer):
  """
  """
  def __init__(self):
    """
    """
    self.logger = logging.getLogger(module_logger.name+".DareRadiometer")
    super(DareRadiometer,self).__init__()
    self.logger.debug(" superclass initialized")

  def set_averaging(self, integr_time):
    """
    """
    
    

