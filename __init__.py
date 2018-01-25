from datetime import datetime
from glob import glob
from math import ceil, log, sqrt
from numpy import array
from os.path import basename
from serial import Serial
from time import sleep, time
import logging

from Electronics.Instruments import PowerMeter
from support import nearest_index
logger = logging.getLogger(__name__)

sqrt10 = sqrt(10)

IDs = {"1.99.234.24.23.0.0.212":   0,
       "1.222.178.24.23.0.0.50":   1,
       "1.253.178.24.23.0.0.221":  2,
       "1.120.234.24.23.0.0.119":  3,  # wrong label on box
       "1.104.234.24.23.0.0.44":   4,
       "1.243.178.24.23.0.0.206":  5,
       "1.229.178.24.23.0.0.39":   6,
       "1.152.210.24.23.0.0.228":  7,
       "1.117.145.134.23.0.0.212":99,  # to be repaired
       "1.30.144.134.23.0.0.34":   9,
       "1.20.144.134.23.0.0.237": 10,
       "1.237.143.134.23.0.0.26": 11,
       "1.40.144.134.23.0.0.125": 12,
       "1.250.169.133.23.0.0.40": 13,
       "1.189.250.90.24.0.0.199": 14,
       "1.200.250.90.24.0.0.180": 15,
       "114.80.79.87.69.82.0.68":  8} # lab test unit


class RadipowerError(RuntimeError):
  """
  Exception for Radipower class
  """
  def __init__(self, args, message):
    """
    """
    self.args = args
    self.message = message

  def __str__(self):
    return repr(("".join(self.args), self.message))

class Radipower(PowerMeter, Serial):
  """
  Class for a Radipower USB power reading head.
  
  The head provides for averaging of readings according to a filter code
  defined in class variable 'filtercodes'.  At filter code setting 1, the
  rate is 100 samples/sec.
  
  Reference
  ========= 
  http://dsnra.jpl.nasa.gov/dss/manuals/RadiPower_Standalone_V1_1.pdf
  """
  filtercodes = {"RPR1018A": {1:1, 2:3, 3:10, 4:30, 5:100, 6:300, 7:1000},
                 "RPR2006C": {1:10, 2:30, 3:100, 4:300, 5:1000, 6:3000, 7:5000}}
  assigned = {}
  
  def __init__(self, device="/dev/ttyUSB0", baud=115200,
               timeout=1, writeTimeout=1):
    """
    """
    mylogger = logging.getLogger(logger.name+".Radipower")
    Serial.__init__(self, device, baud,
                          timeout=timeout, writeTimeout=writeTimeout)
    sleep(0.02)
    self.name = basename(device)
    PowerMeter.__init__(self, self.name)
    self.logger = mylogger
    self.logger.debug(" initializing %s", device)    
    self._attributes_ = []
    self._attributes_.append('logger')
    if self.get_ID():
      if self.ID:
        print "found:", self.ID
        if Radipower.assigned.has_key(self.ID):
          self.logger.warning("__init__: %s already assigned as Radipower %d",
                              device, found)
        else:
          Radipower.assigned[IDs[self.ID]] = device # show device as assigned
        self.name = "PM%02d" % IDs[self.ID]
        self._attributes_.append('name')
        self.identify()
        self._attributes_.append('model')
        self._attributes_.append("HWversion"),
        self._attributes_.append("SWversion")
        # These replace class PowerMeter defaults
        self.f_min = float(self.ask("FREQUENCY? MIN")[:-4])/1.e6 # GHz
        self.f_max = float(self.ask("FREQUENCY? MAX")[:-4])/1.e6 # GHz
        self.p_min = -55 # dBm
        self.p_max = +10 # dBm
        self.auto_averaging() # sets num_avg
        # units and trigmode are the same as the PowerMeter defaults
        if self.model == 'RPR1018A':
          self.units = 0
        else:
          self.units = self.ask("POWER_UNIT?")
        self.trigmode = None
        # use lowest sampling speed
        try:
          self.ask("ACQ_SPEED 20")
        except RadipowerError as details:
          if str(details.message) == 'is not a valid command':
            # for old model radipowers
            pass
          else:
            raise RuntimeError(details)
        self.logger.info(" initialized %s", device[5:])
      else:
        raise RadipowerError(self.ID, 'is not a valid response to ID_NUMBER?')
    else:
      self.logger.warning(" initialization failed")
    
  def get_ID(self):
    """
    """
    retries = 0
    exists = False
    while exists == False and retries < 3:
      try:
        self.ID = self.ask("ID_NUMBER?").strip()
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
    response = self.ask("*IDN?")
    index = response.index('RPR')
    self.model = response[index:index+8]
    self.HWversion = self.ask("VERSION_HW?")
    self.SWversion = self.ask("VERSION_SW?")

  def ask(self, command):
    """
    An example of 'parts'::
      ['ERROR 1', '[ACQ_SPEED 20]', '']
    """
    self.logger.debug("ask: '%s'", command)
    self.write(command+'\n')
    response = self.readline().strip()
    self.logger.debug("ask: response: %s", response)
    parts = response.split(";")
    if len(parts) == 1:
      return response
    else:
      self._IO_error(parts)
  
  def _IO_error(self, parts):
    """
    """
    response = ";".join(parts)
    if parts[0] == 'ERROR 1':
      raise RadipowerError(parts[1],"is not a valid command")
    elif parts[0] == 'ERROR 50':
      raise RadipowerError(parts[1],"; command has a bad argument")
    elif parts[0] == 'ERROR 51':
      raise RadipowerError(parts[1],"; argument value is too high")
    elif parts[0] == 'ERROR 52':
      raise RadipowerError(parts[1],"; argument value is too low")
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
    
    This is only useful when measuring CW signals, not noise

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
    """
    Reports the Radipower physical temperature.
    
    Power measurements will be interrupted if a temperature reading is
    requested.
    """
    self.temp = float(self.ask("TEMPERATURE?"))/10.
    self._add_attr("temp")
    return self.temp
  
  def get_read_speed(self):
    """
    Returns the time taken for one reading in s.
    
    On an RPi-1 this takes about 25 s at ACQ_SPEED=1000.
    """
    t0 = time()
    for i in range(100):
      x = self.ask('POWER?')
    return (time()-t0)/100

  def filter_bounds(self, samples_per_reading):
    """
    """
    if samples_per_reading < 10:
      bounds = (None,1)
    elif samples_per_reading == 10:
      bounds = (1,1)
    elif samples_per_reading < 30:
      bounds = (1,2)
    elif samples_per_reading == 30:
      bounds = (2,2)
    elif samples_per_reading < 100:
      bounds = (2,3)
    elif samples_per_reading == 100:
      bounds = (3,3)
    elif samples_per_reading < 300:
      bounds = (3,4)
    elif samples_per_reading == 300:
      bounds = (4,4)
    elif samples_per_reading < 1000:
      bounds = (4,5)
    elif samples_per_reading == 1000:
      bounds = (5,5)
    elif samples_per_reading < 3000:
      bounds = (5,6)
    elif samples_per_reading == 3000:
      bounds = (6,6)
    elif samples_per_reading < 5000:
      bounds = (6,7)
    elif samples_per_reading == 5000:
      bounds = (7,7)
    else:
      bounds = (7,None)
    return bounds

  def auto_averaging(self):
    """
    Power meter selects best avaraging based on signal level.
    """
    self.filter = "AUTO"
    response  = self.ask("FILTER AUTO")
    self.get_averaging()
    return response
    
  def set_VBW(self,code):
    """
    Sets the video bandwidth
    
    VBW can be used to smooth the post-detection signal.  It sets the timescale
    over which the measured signal varies.  VBW = 1/smoothing_time_constant.
    
    If an AM modulated signal is to be measured with a modulation frequency of,
    for example, 1 kHz, the VBW should be set to 0 (10 MHz), 1 (1 MHz),
    2 (200 kHz) or AUTO (0 at 1MSps, 1 at 100kSps, 2 at 20kSps). To measure the
    modulation the VBW should be 10 times smaller than the RF carrier frequency
    but higher than the modulation frequency.
    """
    pass
    
  # --------------------- methods defined for PowerMeter ----------------------
  
  def power(self):
    """
    Returns one (possible averaged) power reading
    
    In mode 0 (RMS mode), a new power measurement is started after the "power?"
    command has been given. Depending on the filter setting, the RadiPower 
    performs the required number of measurements and returns the RMS value.
    """
    self.reading = float(self.ask("POWER?")[:-4])
    self.logger.debug("power: reading is %6.2f", self.reading)
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
        self.num_avg = Radipower.filtercodes[self.model][3]
      elif self.reading > -30. and self.reading <= -20.:
        self.num_avg = Radipower.filtercodes[self.model][4]
      elif self.reading > -40. and self.reading <= -30.:
        self.num_avg = Radipower.filtercodes[self.model][5]
      elif self.reading > -50. and self.reading <= -40.:
        self.num_avg = Radipower.filtercodes[self.model][6]
      else:
        self.num_avg = Radipower.filtercodes[self.model][7]
    else:
      self.num_avg = Radipower.filtercodes[self.model][int(self.filter)]
    return self.num_avg
    
  def set_averaging(self, num, no_smear=False, min_rms=False, most=False):
    """
    Selects the averaging option for power meter readings
    
    Sets the number of samples to average.  If no keyword argument is given,
    the averaging option is the one which averages the number of samples which
    is closest to num.
    
    The acquisition speed and filter should be set in such a way that at least
    one full period of the modulation signal is measured. At 1Msps, the filter
    should be set to 5 or higher, which results in 1000 or more samples. At
    lower sampling speeds, for example 100ksps, the filter should be set to 3
    or higher to measure at least one full period of the envelope signal. 
    
    @param num : number of samples to average; calculate if 0
    @type  num : int
    
    @param no_smear : if True, num is the largest < reading_time/sampling_time
    @type  no_smear : bool
    
    @param min_rms : if True, num is the smallest > reading_time/sampling_time
    @type  min_rms : bool
    
    @param most: largest number of samples available
    @type  most: bool
    
    @return num_averaged
    """
    if num > 5000:
      raise RadipowerError(num_averages,"averages is greater than 1000")
    elif num > 0:
      read_speed = get_read_speed() # ms
      if read_speed < 1 :
        response = self.ask("BAUD 3")           # 0.3 ms/sample
      elif read_speed < 2:
        response = self.ask("BAUD 2")           # 0.6 ms/sample
      else:
        response = self.ask("BAUD 1")           # 1.25 ms/sample
    elif num == 0:
      samples_per_read = read_speed*20
      bounds = filter_bounds(samples_per_read)
      if most:
        response = self.ask("FILTER 7")
      elif no_smear:
        response = self.ask("FILTER "+str(bounds[0]))
      elif min_rms:
        response = self.ask("FILTER "+str(bounds[1]))
      else:
        response = self.ask("FILTER "+str(nearest_index(array(bounds), num)))
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
  logger.debug(" ports: %s", ports)
  rp = {}
  for port in ports:
    logger.debug(" Opening %s", port)
    try:
      RP = Radipower(device=port)
    except RadipowerError:
      logger.error("find_radipowers: no response from %s", port)
    else:
      if RP.ID != "":
        index = IDs[RP.ID]
        rp[index] = RP
        logger.debug(" Attached Radipower %d", index)
  return rp
