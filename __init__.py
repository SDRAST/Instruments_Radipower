from datetime import datetime
from glob import glob
from math import log
from serial import Serial
from time import sleep
import logging

from Electronics.Instruments import PowerMeter

module_logger = logging.getLogger(__name__)

IDs = {"1.99.234.24.23.0.0.212":  0,
       "1.222.178.24.23.0.0.50":  1,
       "1.253.178.24.23.0.0.221": 2,
       "1.120.234.24.23.0.0.119": 3,  # wrong label on box
       "1.104.234.24.23.0.0.44":  4,
       "1.243.178.24.23.0.0.206": 5,
       "1.229.178.24.23.0.0.39":  6,
       "1.152.210.24.23.0.0.228": 7,
       "114.80.79.87.69.82.0.68": 99} # lab test unit

class RadipowerError(RuntimeError):
  """
  Exception for Radipower class
  """
  def __init__(self,args,message):
    """
    """
    self.args = args
    self.message = message

  def __repr__(self):
    return repr(("".join(str(self.args)), self.message))

class Radipower(PowerMeter,Serial):
  """
  Class for a Radipower USB power reading head.
  
  The head provides for averaging of readings according to a filter code
  defined in class variable 'averages'.  At filter code setting 1, the
  rate is 100 samples/sec.
  
  Reference
  ========= 
  http://dsnra.jpl.nasa.gov/dss/manuals/RadiPower_Standalone_V1_1.pdf
  """
  averages = {1:1, 2:3, 3:10, 4:30, 5:100, 6:300, 7:1000}
  
  def __init__(self, device="/dev/ttyUSB0", baud=115200,
               timeout=1, writeTimeout=1, num_avg=10):
    """
    """
    mylogger = logging.getLogger(module_logger.name+".Radipower")
    Serial.__init__(self, device, baud,
                          timeout=timeout, writeTimeout=writeTimeout)
    sleep(0.02)
    PowerMeter.__init__(self)
    self.logger = mylogger
    self.logger.debug(" initializing %s", device)    
    self._attributes_ = []
    self._attributes_.append('logger')
    if self.get_ID():
      #self.write('REBOOT SYSTEM\n')
      self._attributes_.append('ID')
      self.identify()
      self._attributes_.append('model')
      self._attributes_.append("HWversion"),
      self._attributes_.append("SWversion")
      # These replace class PowerMeter defaults
      self.f_min = float(self.ask("FREQUENCY? MIN")[:-4])/1.e6 # GHz
      self.f_max = float(self.ask("FREQUENCY? MAX")[:-4])/1.e6 # GHz
      self.p_min = -55 # dBm
      self.p_max = +10 # dBm
      self.set_averaging(num_avg) # sets num_avg
      # units and trigmode are the same as the PowerMeter defaults
      self.logger.info(" initialized %s", device[5:])
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
    """
    """
    self.model = self.ask("*IDN?")
    self.HWversion = self.ask("VERSION_HW?")
    self.SWversion = self.ask("VERSION_SW?")

  def ask(self, command):
    """
    """
    self.logger.debug("ask: '%s'", command)
    self.write(command+'\n')
    response = self.readline().strip()
    self.logger.debug("ask: response: %s", response)
    parts = response.split(";")
    if len(parts) == 1:
      return response
    else:
      _IO_error(parts)
  
  def _IO_error(self, parts):
    """
    """
    if parts[0] == 'ERROR 1':
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
      raise RadipowerError(response,"is an unexpected response")

  def set_cal_freq(self, freq=None):
    """
    Gets or sets the calibration frequency

    @param freq : frequency in GHz
    @type  freq : float
    """
    if freq == None:
      suffix = "?"
    else:
      f = int(round(freq*1e9))
      suffix = " "+str(f)+" Hz"
    response = self.ask("FREQUENCY"+suffix)
    if freq == None:
      self.f_cal = float(response[:-4])/1.e9
    else:
      self.f_cal = f
    self._add_attr("f_cal")
    return self.f_cal

  def get_temp(self):
    self.temp = float(self.ask("TEMPERATURE?"))/10.
    self._add_attr("temp")
    return self.temp

  # --------------------- methods defined for PowerMeter ----------------------
  
  def power(self):
    """
    Returns one (possible averaged) power reading in dBm
    """
    self.reading = float(self.ask("POWER?")[:-4])
    self.logger.debug("power: reading is %6.2f at %s", self.reading, str(datetime.now()))
    self._add_attr("power")
    return self.reading

  def get_averaging(self):
    """
    Number of samples averaged according to filter code
    
    If the filter code is AUTO then the effective filter code must be inferred
    from the power level.
    """
    self.filter = self.ask("FILTER?")
    self._add_attr("filter")
    if self.filter == "AUTO":
      self.power()
      if self.reading > -20. and self.reading <= 10.:
        self.num_avg = 10
      elif self.reading > -30. and self.reading <= -20.:
        self.num_avg = 30
      elif self.reading > -40. and self.reading <= -30.:
        self.num_avg = 100
      elif self.reading > -50. and self.reading <= -40.:
        self.num_avg = 300
      else:
        self.num_avg = 1000
    else:
      self.num_avg = Radipower.averages[int(self.filter)]
    if self.filter == "1":
      self.num_avg = 1
    elif self.filter == "2":
      self.num_avg = 3
    elif self.filter == "3":
      self.num_avg = 10
    elif self.filter == "4":
      self.num_avg = 30
    elif self.filter == "5":
      self.num_avg = 100
    elif self.filter == "6":
      self.num_avg = 300
    elif self.filter == "7":
      self.num_avg = 1000
    return self.num_avg

  def set_averaging(self, num_averages):
    """
    Sets filter code for number of averages closest to requested

    @param num_averages : 1-1000; 0 for AUTO
    @type  num_averages : int
    """
    if num_averages > 1000:
      raise RadipowerError(num_averages,"averages is greater than 1000")
    if num_averages <= 1000 and num_averages > 0:
      self.filter = int(round(log(num_averages,3.15)))+1
      response  = self.ask("FILTER "+str(self.filter))
    elif num_averages == 0:
      self.filter = "AUTO"
      response  = self.ask("FILTER AUTO")
    self.get_averaging()
    return response

class RP_array(dict):
  """
  Array of power meters
  
  This redefines key() so it returns a sorted list
  """
  def __init__(self, args):
    """
    Initialize the dict
    """
    dict.__init__(self, args)
    
  def keys(self):
    """
    Return sorted list of keys
    """
    keys = super(RP_array,self).keys()
    keys.sort()
    return keys
    
# ----------------------------- module methods ---------------------------------

def find_radipowers():
  """
  Instantiates the Radipowers found and returns a dict
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
  return rp
