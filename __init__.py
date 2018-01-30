"""
support for Dare!! power meters

Frequency
=========
For narrow band signals, this is the frequency used to calibrate the readings.
The default reference frequency (command FREQUENCY) is 1.3 GHz.

Averaging
=========
The FILTER setting controls the number of samples averaged::
  Num 1018A 2006C
   1     1    10
   2     3    30
   3    10   100
   4    30   300
   5   100  1000
   6   300  3000
   7  1000  5000
 AUTO depends on power level
The default is AUTO.

Sampling Rate
=============
The sampling rate of the ADC is selectable with the ACQ_SPEED command.  The
acquisition speeds are 20, 100 and 1000 kS/s.

Measurement Rate
================
The fastest rate at which a Radipower can return data is about 100 S/s. 
That would be for a ACQ_SPEED of 100 kS/s and a FILTER of 1 or 2.

Video Bandwidth
===============
The video bandwidth can be coupled to the acquisition speed as shown in the 
next table.
  
The video bandwidth codes (command VBW) are::
  0 10     MHz    1    MS/s = 1000 kS/s
  1  1     MHz    0.1  MS/s =  100 kS/s
  2  0.2   MHz    0.02 MS/s =   20 kS/s
  3  0.001 MHz
The command 'VBW AUTO' couples the video bandwidth to the sampling speed as
shown in the table above.

BAUD Rate
=========
The serial communication BAUD rate codes are::
  0 for  57600 bps
  1 for 115200 bps (default)  reading time (144 bits) is 1.25 ms/S
  2 for 230400 bps            reading time (144 bits) is 0.6  ms/S
  3 for 460800 bps            reading time (144 bits) is 0.3  ms/S
In practice, the actual BAUD rate

These commands are not implemented for our devices::
  MODE
"""
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
    super(RadipowerError, self).__init__(message)
    self.args = args
    self.message = message
    self.logger = logging.getLogger(logger.name+".RadipowerError")

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
  filtercodes = {"RPR1006":{1:1,  2:3,  3:10,  4:30,  5:100,  6:300,  7:1000},
                 "RPR1018":{1:1,  2:3,  3:10,  4:30,  5:100,  6:300,  7:1000},
                 "RPR2006":{1:10, 2:30, 3:100, 4:300, 5:1000, 6:3000, 7:5000}}
  acq_speeds = {"RPR1018": [1000],        # kSps
                "RPR1006": [10,100,1000],
                "RPR2006": [20,100,1000]}
  assigned = {}
  
  def __init__(self, device="/dev/ttyUSB0", baud=115200,
               timeout=1, writeTimeout=1, Sps=1000, filtercode=1):
    """
    The 'baud' argument is provided to compensate for a possible difference
    between the Radipower BAUD rate andthe computer BAUD rate.  Basically,
    it's best not to fiddle with the BAUD rate because getting it wrong locks
    up the device.
    
    @param device : USB port assigned to the power meter
    @type  device : string
    
    @param baud : interface transfer rate in bps (bits per second)
    @type  baud : int
    
    @param timeout : give up reading after this amount of time
    @type  timeout : float
    
    @param writeTimeout : give up writing after this amount of time
    @type  writeTimeout : float
    
    @param Sps : ADC samples per second
    @type  Sps : int
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
        if self.model[:7] == 'RPR1018':
          self.units = 0 # dBm
          self.ask("FILTER 3") # so it's like the 2006s
        else:
          self.units = self.ask("POWER_UNIT?")
        self.trigmode = None # triggering mode
        # use highest sampling speed
        try:
          self.ask("ACQ_SPEED "+str(Sps))
        except RadipowerError as details:
          if str(details.message) == 'is not a valid command':
            # for old model radipowers
            pass
          else:
            raise RuntimeError(details)
        self.ask("FILTER "+str(filtercode))
        self.logger.debug(" initialized %s", device[5:])
      else:
        raise RadipowerError(self.ID, 'is not a valid response to ID_NUMBER?')
    else:
      self.logger.warning(" initialization failed")
    
  def get_ID(self):
    """
    """
    retries = 0
    while retries < 3:
      try:
        self.ID = self.ask("ID_NUMBER?")
        return True
      except RadipowerError, details:
        self.logger.error("get_ID: command error: "+str(details))
        retries += 1
      self.ID = None
      return False

  def identify(self):
    """
    """
    response = self.ask("*IDN?")
    index = response.index('RPR')
    self.model = response[index:index+8]
    self.HWversion = self.ask("VERSION_HW?")
    self.SWversion = self.ask("VERSION_SW?")
    return self.model, self.HWversion, self.SWversion

  def ask(self, command):
    """
    An example of 'parts'::
      ['ERROR 1', '[ACQ_SPEED 20]', '']
    """
    self.logger.debug("ask: '%s'", command)
    self.write(command+'\n')
    response = self.readline().strip()
    self.logger.debug("ask: response: '%s'", response)
    parts = response.split(";")
    self.logger.debug("ask: parts: %s", parts)
    if parts[0][:5] == "ERROR":
      if len(parts) == 1:
        parts.append(command)
      self._IO_error(parts)
    else:
      return response
  
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
    elif response == 'ERROR_602':
      raise RadipowerError(response,"; over range")
    elif response == 'ERROR_603':
      raise RadipowerError(response,"; under range")
    elif response == 'ERROR_604':
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
  
  def get_baud_rate(self):
    """
    returns sampling rate
    """
    try:
      code = self.ask('BAUD?')
      if code == '0':
        return 57600
      elif code == '1':
        return 115200
      elif code == '2':
        return 230400
      elif code == '3':
        return 460800
    except RadipowerError:
      return 115200

  def calc_read_speed(self):
    """
    time for one reading based on parameters
    
    See e-mail 04/29/2016 at 01:46 AM Jeffrey Westgeest
    """
    # com time to send command and get reply
    bitrate = self.get_baud_rate() # b/s
    byterate = bitrate/10
    com_bytes = 7+11 # command and reply
    com_time = float(com_bytes)/byterate
    self.logger.debug("calc_read_speed: com time per reading = %f", com_time)
    # single sample time
    try:
      sample_rate = int(self.ask("ACQ_SPEED?"))
    except RadipowerError:
      sample_rate = 1000
    sample_time = 1./sample_rate
    self.logger.debug("calc_read_speed: sample time = %f", sample_time)
    # number averaged
    samples_averaged = self.get_samples_averaged()
    self.logger.debug("calc_read_speed: %d samples averaged", samples_averaged)
    # measurement rate
    reading_time = sample_time * samples_averaged
    self.logger.debug("calc_read_speed: %f s/S", reading_time)
    measurement_rate = reading_time+com_time
    return measurement_rate

  def set_acq_speed(self, speed):
    """
    """
    if self.model[:7] == 'RPR1018':
      self.acq_speed = 1000
    elif speed in Radipower.acq_speeds[self.model][:7]:
      response = self.ask('ACQ_SPEED '+str(speed))
      return response
    else:
      raise RadipowerError(speed, "in not valid for "+self.model)
        
  def get_read_speed(self):
    """
    Returns the time taken for one reading in s.
    
    On an RPi-1 this takes about 25 s at ACQ_SPEED=1000.
    """
    t0 = time()
    if self.model[:7] != 'RPR1018':
      self.logger.info("get_read_speed: ACQ_SPEED is %s",
                       self.ask("ACQ_SPEED?"))
    self.logger.info("get_read_speed: FILTER %s", self.ask("FILTER?"))
    for i in range(100):
      x = self.ask('POWER?')
    return (time()-t0)/100

  def filter_bounds(self, samples_per_reading):
    """
    return the filter codes which bound the specified sampling rate
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
    
  def set_VBW(self, code):
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
    if code == 0:
      self.VBW = 1e7 # Hz
    elif code == 1:
      self.VBW = 1e6 # Hz
    elif code == 2:
      self.VBW = 2e5 # Hz
    elif code == 3:
      self.VBW = 1e3 # Hz
    else:
      raise RadipowerError(code, "is not a valid VBW code")
  
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

  def get_samples_averaged(self):
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
        self.num_avg = Radipower.filtercodes[self.model[:7]][3]
      elif self.reading > -30. and self.reading <= -20.:
        self.num_avg = Radipower.filtercodes[self.model[:7]][4]
      elif self.reading > -40. and self.reading <= -30.:
        self.num_avg = Radipower.filtercodes[self.model[:7]][5]
      elif self.reading > -50. and self.reading <= -40.:
        self.num_avg = Radipower.filtercodes[self.model[:7]][6]
      else:
        self.num_avg = Radipower.filtercodes[self.model[:7]][7]
    else:
      self.num_avg = Radipower.filtercodes[self.model[:7]][int(self.filter)]
    return self.num_avg
    
  def set_averaging(self, num, no_smear=False, min_rms=False, most=False):
    """
    Selects the averaging option for power meter readings
    
    NOT FINISHED
    
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
    if self.model == 'RPR2006C':
      if num > 5000:
        raise RadipowerError(num_averages,"averages is greater than 5000")
      elif num > 0:
        read_speed = self.get_read_speed() # ms
        self.logger.debug("set_averaging: read speed = %6.3f", read_speed)
        if read_speed < 0.5 :
          response = self.ask("BAUD 3")           # 0.3 ms/sample
        elif read_speed < 1:
          response = self.ask("BAUD 2")           # 0.6 ms/sample
        else:
          response = self.ask("BAUD 1")           # 1.25 ms/sample
      elif num == 0:
        samples_per_read = read_speed*20
        bounds = self.filter_bounds(samples_per_read)
        if most:
          response = self.ask("FILTER 7")
        elif no_smear:
          response = self.ask("FILTER "+str(bounds[0]))
        elif min_rms:
          response = self.ask("FILTER "+str(bounds[1]))
        else:
          response = self.ask("FILTER "+str(nearest_index(array(bounds), num)))
    elif self.model == 'RPR1018A':
      if num > 1000:
        raise RadipowerError(num_averages,"averages is greater than 1000")
      elif num > 0:
        read_speed = self.get_read_speed() # ms
        if read_speed < 1 :
          pass
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
  logger.debug("find_radipowers: found %s", ports)
  ports.sort()
  logger.debug("find_radipowers: ports: %s", ports)
  rp = {}
  for port in ports:
    logger.debug(" Opening %s", port)
    try:
      RP = Radipower(device=port)
    except RadipowerError:
      logger.error("find_radipowers: no response from %s", port)
    else:
      if RP.ID != None:
        index = IDs[RP.ID]
        rp[index] = RP
        logger.info(" Attached Radipower %d model %s", index, RP.model)
  return rp
