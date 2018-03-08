"""
untested program to plot data files in /tmp
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
    data = loadtxt(fname,dtype=str)
    startstr = data[0,0]+" "+ data[0,1]
    start = datestr2num(startstr)
    
    tm = datestr2num([ " ".join(line[0:2]) for line in data if len(line) > 1 ])
    pw = array(data[:,2], dtype=float)
    plot(tm-start, pw, '.', label=str(index))
  title(startstr)
  legend(numpoints=1)
  xlabel("elapsed time")
  grid()
  show()
