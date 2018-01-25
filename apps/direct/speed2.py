"""
Jeffrey Westgeest, DARE!! Instruments, 2016-04-20
"""
# Test program for RPR2006C speed measurement.
import time
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

ID = '2'
device = "/dev/ttyUSB"+ID
print "Using", device
port = serial.Serial(device, baudrate=115200, timeout=3.0)

# acquisition speed; 20, 100 or 1000 kS/s
acq_speed = '1000'
port.write("ACQ_SPEED "+acq_speed+"\n")
time.sleep(0.001)
rcv = readlineCR(port)
print "set 'ACQ_SPEED "+acq_speed+"' response: ",rcv

# filter code (samples per reading)
#   '1' gives the smallest number of samples; AUTO adjusts for power level
filt = '1'
port.write("FILTER "+filt+"\n")
time.sleep(0.001)
rcv = readlineCR(port)
print "set 'Filter "+filt+"' response: ",rcv

# BAUD rate
baud = '1'
port.write("BAUD "+baud+"\n")
time.sleep(0.001)
rcv = readlineCR(port)
print "set 'BAUD "+baud+"' response: ",rcv

port.write("ACQ_SPEED?\n")
rcv = readlineCR(port)
print "ACQ_SPEED:",rcv

port.write("Filter?\n")
rcv = readlineCR(port)
print "Filter:", rcv

port.write("BAUD?\n")
rcv = readlineCR(port)
print "BAUD:", rcv


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

