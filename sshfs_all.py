'''
sshfs all folders that mirror current os.getcwd()
'''

import os
import GPUtil
from subprocess import Popen, PIPE
from multiprocessing import Pool
from functools import partial
import sys
import socket
import getpass

local_storage = '/home2/supasorn/local_storage'
clusters = ""

def getFileList(cluster):
  stdout, stderr = Popen(['ssh', cluster, 'find', local_storage + os.getcwd(), '-type', 'd'], stdout=PIPE).communicate()
  return stdout.split("\n")


def findLeafDirs(listdir):
  mp = {}
  for cluster, ld in enumerate(listdir):
    for d in ld:
      if d not in mp:
        mp[d] = cluster

  for k in mp:
    leaf = 1
    for k2 in mp:
      if k != k2 and k in k2:
        leaf = 0
    if leaf:
      print(k, mp[k])
      localdir = k[len(local_storage):]
      if not os.path.exists(localdir):
        os.makedirs(localdir)
      # cmd = "sshfs -o IdentityFile=/home/supasorn/.ssh/id_rsa supasorn@" + clusters[mp[k]] + ":" + local_storage + localdir + " " + localdir[len(os.getcwd())+1:]
      cmd = "sudo umount -l " + localdir[len(os.getcwd())+1:]
      print(cmd)
      os.system(cmd)


def main():
  global clusters
  if len(sys.argv) > 1:
    clusters = sys.argv[1]
  else:
    clusters = "v2,v3,v4"

  clusters = clusters.split(",")


  # print(stdout)
  p = Pool(len(clusters))
  listdir = p.map(getFileList, clusters)
  findLeafDirs(listdir)

  # print(listdir)

def cmd(c):
  print(c)
  os.system(c)



if __name__== "__main__":
  main()

