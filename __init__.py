from serial import Serial
from time import sleep
import logging
from glob import glob

module_logger = logging.getLogger(__name__)

IDs = {"1.99.234.24.23.0.0.212":  0,
       "1.222.178.24.23.0.0.50":  1,
       "1.253.178.24.23.0.0.221": 2,
       "1.120.234.24.23.0.0.119": 3,  # wrong label on box
       "1.104.234.24.23.0.0.44":  4,
       "1.243.178.24.23.0.0.206": 5,
       "1.229.178.24.23.0.0.39":  6,
       "1.152.210.24.23.0.0.228": 7}

class RadipowerError(RuntimeError):
  def __init__(self,args,message):
    self.args = args
    self.message = message

  def __repr__(self):
    return repr(("".join(str(self.args)), self.message))

class Radipower(Serial):
  """
  """
  def __init__(self, device="/dev/ttyUSB0", baud=115200,
               timeout=1, writeTimeout=1):
    """
    """
    super(Radipower,self).__init__(device, baud,
                                   timeout=timeout, writeTimeout=writeTimeout)
    sleep(0.02)
    self._attributes_ = []
    self.logger = logging.getLogger(module_logger.name+".Radipower")
    self.logger.debug(" initializing %s", device)
    self._attributes_.append('logger')
    if self.get_ID():
      self._attributes_.append('ID')
      self.logger.info(" initialized %s", self.ID)
      self.identify()
      self._attributes_.append('model')
      self._attributes_.append("HWversion")
      self._attributes_.append("SWversion")
      self.fcal_min = float(self.ask("FREQUENCY? MIN")[:-4])/1000.
      self._attributes_.append('fcal_min')
      self.fcal_max = float(self.ask("FREQUENCY? MAX")[:-4])/1000.
      self._attributes_.append('fcal_max')
    else:
      self.logger.warning(" initialization failed")
    
  def get_ID(self):
    """
    """
    retries = 0
    exists = False
    while exists == False and retries < 3:
      try:
        self.ID = self.ask("ID_NUMBER?")
        exists = True
      except RadipowerError,details:
        self.logger.error("command error: "+str(details))
        retries += 1
        self.ID = None
        exists = False
    return exists

  def identify(self):
    self.model = self.ask("*IDN?")
    self.HWversion = self.ask("VERSION_HW?")
    self.SWversion = self.ask("VERSION_SW?")

  def ask(self,command):
    self.write(command+'\n')
    response = self.readline().strip()
    self.logger.debug("ask: response: %s", response)
    parts = response.split(";")
    if len(parts) == 1:
      return response
    elif parts[0] == 'ERROR 1':
      raise RadipowerError(parts[1],"is not a valid command")
    elif parts[0] == 'ERROR 50':
      raise RadipowerError(response,"; command has a bad argument")
    elif parts[0] == 'ERROR 51':
      raise RadipowerError(response,"; argument value is too high")
    elif parts[0] == 'ERROR 52':
      raise RadipowerError(response,"; argument value is too low")
    elif parts[0] == 'ERROR_601':
      raise RadipowerError(response,"; measurement frequency is not set")
    elif parts[0] == 'ERROR_602':
      raise RadipowerError(response,"; over range")
    elif parts[0] == 'ERROR_603':
      raise RadipowerError(response,"; under range")
    elif parts[0] == 'ERROR_604':
      raise RadipowerError(response,"; no calibration data for this frequency")
    else:
      raise RadipowerError(response,"is and unexpected response")

  def _add_attr(self, attr):
    try:
      self._attributes_.index(attr)
    except ValueError:
      self._attributes_.append(attr)

  def __dir__(self):
    return self._attributes_
    
  def get_power(self):
    self.power = float(self.ask("POWER?")[:-4])
    self._add_attr("power")
    return self.power

  def get_cal_freq(self):
    self.fcal = float(self.ask("FREQUENCY?")[:-4])/1000.
    self._add_attr("fcal")
    return self.fcal

  def get_temp(self):
    self.temp = float(self.ask("TEMPERATURE?"))/10.
    self._add_attr("temp")
    return self.temp

  def get_averaging_code(self):
    self.filter = self.ask("FILTER?")
    self._add_attr("filter")
    if self.filter == "1":
      self.num_samples = 1
    elif self.filter == "2":
      self.num_samples = 3
    elif self.filter == "3":
      self.num_samples = 10
    elif self.filter == "4":
      self.num_samples = 30
    elif self.filter == "5":
      self.num_samples = 100
    elif self.filter == "6":
      self.num_samples = 300
    elif self.filter == "7":
      self.num_samples = 1000
    elif self.filter == "AUTO":
      pass # for now
    self._add_attr("num_samples")

# ----------------------------- module methods ---------------------------------

def find_radipowers():
  """
  Instantiates the Radipowers found and returns a sorted list of indices
  """
  ports = glob("/dev/ttyUSB*")
  module_logger.debug(" ports: %s", ports)
  rp = {}
  for port in ports:
    module_logger.debug(" Opening %s", port)
    RP = Radipower(device=port)
    if RP.ID != None:
      index = IDs[RP.ID]
      rp[index] = RP
      module_logger.debug(" Attached Radipower %d", index)
  available = rp.keys()
  available.sort()
  module_logger.debug(" available: %s", available)
  return rp, available
