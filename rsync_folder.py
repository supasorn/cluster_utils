'''
'''

import os
import GPUtil
from subprocess import Popen, PIPE
from multiprocessing import Pool
from functools import partial
import sys
import socket
import getpass

def getFileList(cluster):
  # stdout, stderr = Popen(['ssh', cluster, 'ls', '/home2/supasorn/local_storage/' + os.getcwd()], stdout=PIPE).communicate()
  cmd("  rsync -rvu --exclude='graph*' " + cluster + ':/home2/supasorn/local_storage' + os.getcwd() + "/ .")
  # cmd("  rsync -rvu --exclude='event*' --exclude='graph*' " + cluster + ':/home2/supasorn/local_storage' + os.getcwd() + "/ .")

def main():
  if len(sys.argv) > 1:
    clusters = sys.argv[1]
  else:
    clusters = "v1,v2,v3,v4"

  clusters = clusters.split(",")


  p = Pool(len(clusters))
  a = p.map(getFileList, clusters)


def cmd(c):
  print(c)
  os.system(c)



if __name__== "__main__":
  main()

