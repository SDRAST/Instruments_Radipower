from numpy import array, loadtxt
from dateutil import parser
from pylab import *

data = loadtxt('/tmp/sorted', usecols=(0,1), dtype=str)
length,width = data.shape

dates = []
for row in range(length):
  dates.append(parser.parse(data[row,0]+' '+data[row,1].replace(',','.')))
starts = dates[0::2]
stops = dates[1::2]
intervals = array(stops)-array(starts)

times = []
for interval in intervals:
  times.append( interval.microseconds/1000 )
plot(times)
xlabel('Sample')
ylabel('Duration')
grid()
show()