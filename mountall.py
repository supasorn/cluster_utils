import os
import GPUtil
from subprocess import Popen, PIPE
from multiprocessing import Pool
from functools import partial
import sys
import socket
import getpass
from time import sleep
import subprocess
import time
import glob
import argparse

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-clusters', type=str, default="v1,v2,v3,v4")
parser.add_argument('-path', type=str, default="")

args = parser.parse_args()

def mountall():
  for c in args.clusters.split(","):
    os.system("sshfs -o IdentityFile=/home/supasorn/.ssh/id_rsa supasorn@%s:/ ~/mnt/%s" % (c, c))

def tensorboard():
  print("Mounting all")
  mountall()

  local_storage = "/home2/" + getpass.getuser() + "/local_storage"

  abspath = os.path.join(os.getcwd(), args.path)
  # print(sys.argv[1])
  # print()
  cmd = "tensorboard --logdir=%s,%s" % (abspath, ",".join(["~/mnt/%s" % c + local_storage + abspath for c in args.clusters.split(",")]))
  print(cmd)
  os.system(cmd)


if __name__== "__main__":
  tensorboard()
  # main()

