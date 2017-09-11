"""
Dare! Total Power Radiometer server

Instead of superceding the inherited loggers it may be possible simply to
rename them.
"""
import logging
import signal
import sys
import time
import os

import numpy as np
import Pyro4

import Electronics.Instruments.Radipower as Radipower
from Electronics.Instruments.radiometer import Radiometer
import support

from pyro_support import Pyro4Server, config

module_logger = logging.getLogger(__name__)

@config.expose
class RadiometerServer(Pyro4Server):
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
        get_readings    - Get the most recent set of readings from the Radiometer heads.
    """
    help_text = """
    change_rate(rate) - change sampling rate to 'rate' samples per second
    get_readings()    - return the most recent set of readings
    stop              - stop the radiometer server
    """

    def __init__(self, logpath="/var/tmp/", rate=1. / 60, name="Radiometer", logger=None, **kwargs):
        """
        Initialize a Radipower radiometer server

        At present with a Raspberry Pi controller the maximum rate is about 1/s.

        Args:
            name (str): name for the Pyro nameserver
        Keyword Args:
            bus (Pyro4.Proxy): The messagebus proxy.
            logpath (str): directory for the radiometer datafiles
            rate (float): number of readings per second
        """
        if not logger:
            logger = logging.getLogger(module_logger.name + "." + "RadiometerServer")
        Pyro4Server.__init__(self, name=name, logger=logger, **kwargs)
        self.pm = None
        self.radiometer = None
        self.pm_readings = None
        self.datefile = None
        self.rate = None
        self.logpath = None
        self.run = False

        self.connect_to_hardware(rate, logpath) # this sets some instance attributes

    def connect_to_hardware(self, rate, logpath):
        """
        Connect to radiometer power meter heads.
        Args:
            rate (float): The rate at which to collect data
            logpath (str): The location of the data file.
        """
        if support.check_permission('ops') == False:
            raise RuntimeError("Insufficient permission to access USB")
        self.logger.debug("connect_to_hardware: Finding radiometer power meter heads")
        pm = Radipower.find_radipowers()
        self.logger.debug("connect_to_hardware: Power meter heads: {}".format(pm))
        self.pm = pm
        self.rate = rate
        self.logpath = logpath
        self.logger.debug("connect_to_hardware: initializing Radiometer class")
        self.radiometer = Radiometer(pm, rate=rate)
        self.pm_readings = None
        self.open_datafile(logpath)
        self.run = True
        self.radiometer.start()

    def stop(self):
        """
        Stops the radiometer and closes the datafile
        """
        self.radiometer.close()  # for the Radiometer
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
        self.datafile = open(os.path.join(logpath, filename), "w")

    def change_rate(self, rate):
        """
        Change the reading rate

        Closes the datafile, sets the new rate and open a new datafile.
        """
        # ? suspend the read threads
        # pause the timer
        signal.setitimer(signal.ITIMER_REAL, 0)
        # close the data file
        logpath = os.path.dirname(self.datafile.name)
        self.datafile.close()
        # set the new rate
        self.radiometer.set_rate(rate)
        # open a new data file
        self.open_datafile(logpath + "/")
        # ? resume the read threads
        # resume the timer
        support.sync_second()
        signal.setitimer(signal.ITIMER_REAL, self.radiometer.update_interval, self.radiometer.update_interval)

    def get_readings(self):
        """
        Get radiometer power meter readings
        """
        readings = self.radiometer.get_readings()
        return readings

    def get_ave_readings(self, num=1):
        """
        Get a number of readings, and average them.
        Args:
            num (int): the number of readings to get.
        Returns:
            dict
        """
        readings = [[self.radiometer.get_readings()[j] for j in xrange(8)] for i in xrange(num)]
        readings = np.mean(readings, axis=0)
        return readings.tolist()

    def help(self):
        return RadiometerServer.help_text


if __name__ == '__main__':
    parsed = simple_parse_args("Create a Pyro4 radiometer server").parse_args()

    rad = RadiometerServer('RadiometerServer', loglevel=logging.DEBUG)

    rad.launch_server(remote_server_name='localhost',ns_host=parsed.ns_host, ns_port=parsed.ns_port)
