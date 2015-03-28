"""
untested
"""
from pylab import *

from support.text import select_files

data_path = "/tmp/"

data = {}
if __name__ == "__main__":
  files = select_files(data_path+"PM*")
  files.sort()
  for fname in files:
    index = files.index(fname)
    data[index] = loadtxt(fname,dtype=str)
    start = datestr2num(data[index][0,0])
    for pm in pmlist:
      tm = datestr2num(array(data[pm][:,0]))
      pw = array(data[pm][:,1],astype=float)
      plot(ar[:,0]-start, ar[:,1], '.', label=str(pm))
    title(time.ctime(data[0][0][0]))
    legend(numpoints=1)
    xlabel("%d samples/sec" % radiometer.rate)
    grid()
    show()