# Test program for RPR2006C speed measurement.

import serial
from timeit import default_timer as timer

def readlineCR(port):
    rv = ""
    while True:
        ch = port.read()        
        if ch=='\n' or ch=='':
            return rv
	else:
  	    rv += ch

port = serial.Serial("/dev/ttyUSB0", baudrate=115200, timeout=3.0)

#Getting the current filter setting
port.write("Filter?\n")
rcv = readlineCR(port)
print "Filter:", rcv

# time the measurement
start = timer()
for x in range(0, 1000):	
	port.write("POWER?\n")
	rcv = readlineCR(port)

end = timer()

print "Samples:", x+1
#print the last measurement, to ensure that the power is measuring what we are expecting.
print "Measuring:", rcv
#print the test time
print "Duration(Sec):", (end - start)

