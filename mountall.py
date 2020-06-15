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

# args = argparse.parse_args()

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

def readClustersAndURLs():
  clusters = {}
  if "clusters" not in os.environ:
    raise Exception("please define clusters environment")
  cs = os.environ["clusters"].split(",")

  f = open(os.path.expanduser("~/.ssh/config"), "r")
  c = ""
  for line in f.readlines():
    if "Host " in line:
      c = line[5:].strip()
    if "HostName " in line:
      if c in cs:
        clusters[c] = line.strip()[8:].strip()

  f.close()
  print(clusters)
  for cluster in clusters:
    print(cluster)
  # exit()
  return clusters

def cmd(st):
  print(st)
  os.system(st)

def main():
  clusters = readClustersAndURLs()
  for cluster in clusters:
    cmd("sudo umount -l ~/mnt/" + cluster)
    cmd("mkdir ~/mnt/" + cluster)
    cmd("sshfs -o follow_symlinks -o IdentityFile=/home/$USER/.ssh/id_rsa $USER@%s:/ ~/mnt/%s" % (cluster, cluster))

if __name__== "__main__":
  main()
  # tensorboard()
  # main()

