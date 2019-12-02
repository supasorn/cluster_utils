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
from time import sleep
import time

local_storage = '/home2/supasorn/local_storage'
clusters = ""

def main():
  if len(sys.argv) != 4:
    print("runner.py id session_folder path")

  id = sys.argv[1]
  sess = sys.argv[2]
  path = sys.argv[3]

  # if not os.path.exists(sess):
    # os.mkdir(sess)

  start = time.time()
  while True:
    reqf = path + sess + "/" + id + ".req"
    if not os.path.exists(reqf):
      open(reqf, "w").close()
    elif os.path.exists(reqf + ".res"):
      fi = open(reqf + ".res", "r")
      data = fi.readlines()
      fi.close()
      print("remove " + reqf)
      os.remove(reqf)
      print("remove " + reqf + ".res")
      os.remove(reqf + ".res")

      if len(data):
        if data[0] == "DONE":
          exit()
        for line in data:
          print(line)
          os.system(line)
    sleep(1)
    print(id + "@" + sess, time.strftime("%H:%M:%S", time.gmtime(time.time() - start)))


  print("done")

  # print(listdir)

def cmd(c):
  print(c)
  os.system(c)



if __name__== "__main__":
  main()

