import logging
import unittest
import threading

import Pyro4
import Pyro4.socketutil
import Pyro4.naming

import pyro4tunneling

from radiometer_pyro4_server import RadiometerServer

class TestRadiometerServer(unittest.TestCase):

    isSetup = False
    server = None
    client = None

    def setUp(self):
        if not self.__class__.isSetup:
            logger = logging.getLogger("TestRadiometerServer")
            logger.setLevel(logging.DEBUG)
            port = Pyro4.socketutil.findProbablyUnusedPort()
            ns_details = Pyro4.naming.startNS(port=port)
            ns_thread = threading.Thread(target=ns_details[1].requestLoop)
            ns_thread.daemon = True
            ns_thread.start()

            res = pyro4tunneling.util.check_connection(Pyro4.locateNS, kwargs={"port":port})
            ns = Pyro4.locateNS(port=port)

            name = "Radiometer_pyro4_server"
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            server = RadiometerServer(name=name, logger=logger)
            server_thread = server.launch_server(ns_port=port, local=True, threaded=True)

            self.__class__.client = Pyro4.Proxy(ns.lookup(server.name))
            self.__class__.server = server
            self.__class__.isSetup = True

        else:
            pass

    def test_stop(self):
        client = self.__class__.client
        client.stop()

    def test_open_datafile(self):
        client = self.__class__.client
        client.open_datafile("/var/tmp")

    def test_change_rate(self):
        client = self.__class__.client
        client.change_rate(1./60.)

    def test_get_readings(self):
        client = self.__class__.client
        logger = logging.getLogger("TestRadiometerServer.test_get_readings")
        readings = client.get_readings()
        logger.debug(readings)
        self.assertTrue(isinstance(readings, dict))

    def test_get_ave_readings(self):
        client = self.__class__.client
        logger = logging.getLogger("TestRadiometerServer.test_get_ave_readings")
        readings = client.get_ave_readings(5)
        logger.debug(readings)
        self.assertTrue(isinstance(readings, list))

    def test_get_help(self):
        client = self.__class__.client
        help_text = client.help()
        logger = logging.getLogger("TestRadiometerServer.test_get_help")
        self.assertTrue(isinstance(help_text, str) or isinstance(help_text, unicode))

if __name__ == "__main__":
    logging.basicConfig(loglevel=logging.DEBUG)
    suite_get = unittest.TestSuite()
    suite_set = unittest.TestSuite()

    suite_get.addTest(TestRadiometerServer("test_get_readings"))
    suite_get.addTest(TestRadiometerServer("test_get_ave_readings"))
    suite_get.addTest(TestRadiometerServer("test_get_help"))

    suite_set.addTest(TestRadiometerServer("test_stop"))
    suite_set.addTest(TestRadiometerServer("test_open_datafile"))
    suite_set.addTest(TestRadiometerServer("test_change_rate"))
    suite_set.addTest(TestRadiometerServer("test_stop"))

    result_get = unittest.TextTestRunner().run(suite_get)
    if result_get.wasSuccessful():
        unittest.TextTestRunner().run(suite_set)
