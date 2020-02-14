from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re
import time
import socket
import getpass

'''
Returns the path to the actual file depending on where the code is run.
  If run locally (not vision-0x), just return the path.

  If run on the cluster:
    Copy the file (or the entire folder) specified by "path" from your
    workstation to the cluster and return the local path to the copied
    file on the cluster. Copying is performed when the file doesn't 
    exist or when the copied file is too old.

  *** Setting the "clone" flag to False means skipping the copying,
  and only creating the directory tree on the cluster. This is for creating
  an output file / folder.

  Suppose the file on your workstation is:
    /home/supasorn/research/project1/data/train.txt
  The copied file on cluster will be:
    LOCAL_STORAGE/home/supasorn/research/project1/data/train.txt
  where LOCAL_STORAGE is the first argument provided to this function.


  Usage:
    Go to your research folder, run:
      git clone https://github.com/supasorn/cluster_utils.git
    This will create a folder cluster_utils/ inside your research folder.

    Then in your code:
      from cluster_utils.localpath import getLocalPath


  Tips:
    Usually the local_storage has to be set for every getLocalPath()'s calls, but
    we can shorten the call with a python's lambda function.

    lp = lambda path, clone=True: getLocalPath("/home2/YOURUSER/local_storage", path, clone)

    And instead of using:
      file_path = getLocalPath("/home2/YOURUSER/local_storage", "data/bigdata.tfrecord")
    we can use:
      file_path = lp("data/bigdata.tfrecord")
      
      
  Examples:
    1. If you want to have large data file available to your cluster locally,
    do the following. Suppose the data is "data/bigdata.tfrecord"
    (relative path)

    Instead of using:
      file_path = "data/bigdata.tfrecord"
    Use:
      file_path = lp("data/bigdata.tfrecord")

    This also works with absolute paths on your workstation.


    2. If you want to write an output file locally instead of sshfs-mounted
    directory on your workstation, set the clone flag to false:

      lp("output/out.txt", clone=False)


    3. If you want to have the entire folder cloned from your workstation.

      lp("model_dir/")


    4. If you want to use an output folder locally, e.g., when using tensorflow's
    estimator which requires setting model_dir. Set clone to False and use:

      lp("run/experiment1", clone=False)

'''

def minput(path):
  return getLocalPath(path, clone=True)

def moutput(path):
  return getLocalPath(path, clone=False)

def getLocalPath(local_storage, path, clone=True):
  if local_storage == "":
    local_storage = "/home2/" + getpass.getuser() + "/local_storage"

  if not os.path.exists(local_storage):
    os.makedirs(local_storage)

  # removing trailing /
  while len(path) > 1 and path[-1] == "/":
    path = path[:-1]

  if "HOSTNAME" in os.environ and os.environ["HOSTNAME"] == "dgx1":
    cluster = "dgx1"
  else:
    cluster = re.search(r"v.*\d{2}", socket.gethostname())

  if cluster is None:
    print("NOT on cluster: " + path)
    return path

  src_with_host = get_remote_path(path)
  if src_with_host is None:
    print("Seems like Teng!")
    return path
  src = src_with_host.split(":")[1]

  destination = local_storage + src

  print("-" * 60)
  print("  On cluster: " + destination)
  print("  Remote    : " + src_with_host)

  if os.path.isdir(path) and clone is False:
    cmd("  mkdir -p " + destination)
  else:
    cmd("  mkdir -p " + os.path.dirname(destination))

  if clone:
    cmd("  rsync -ru " + src_with_host + " " + os.path.dirname(destination))
    print("     >> Cloned\n")
  else:
    print("     >> Not cloned\n")

  return destination

def find_remote_mount_point(path):
  for l in open("/proc/mounts", "r"):
    mp = l.split(" ")
    if mp[1] != "/" and path == mp[1]:
      return mp[0]
  return None

def find_local_mount_point(path):
  path = os.path.abspath(path)
  while not os.path.ismount(path):
    path = os.path.dirname(path)
  return path

def get_remote_path(path):
  print("-" * 60)
  print("Syncing file: " + path)
  path = os.path.abspath(path)
  ld = find_local_mount_point(path)
  rd = find_remote_mount_point(ld)

  if rd is None or "@" not in rd:
    print("non-mounted file")

    # absolute path
    if path[0] == '/':
      ld2 = find_local_mount_point(os.getcwd())
      rd2 = find_remote_mount_point(ld2)
      if rd2 is None:
        return None
      return rd2.split(":")[0] + ":" + path
    else:
      print("Error: non-mounted file requires an absolute path")
      exit()

  rpath = path[len(ld)+1:]
  out = rd + "/" + rpath
  # print("  path       :", path)
  # print("  remote path:", rpath)
  # print("  local dir  :", ld)
  # print("  remote dir :", rd)
  # print("  output     :", out)
  return out

def cmd(c):
  print(c)
  os.system(c)

