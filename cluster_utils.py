from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import re
import time
import socket

'''
Returns the path to the actual file depending on where the code is run.
  If run locally (not vision-0x), just return the path.

  If run on the cluster:
    Copy the file (or the entire folder) specified by "path" from your
    workstation to the cluster and return the local path to the copied
    file on the cluster. Copying is performed when the file has never
    been copied or when the copied file is outdated.

  *** Setting the "clone" flag to False means skipping the copying,
  and only creating the directory tree on the cluster. This is for creating
  an output file / folder.

  Examples:
    1. If you want to have large data file available to your cluster locally,
    do the following. Suppose the data is "data/bigdata.tfrecord"
    (relative path)

    Instead of using:
      file_path = "data/bigdata.tfrecord"
    Use:
      file_path = getLocalPath("/home2/YOURUSER/local_storage", "data/bigdata.tfrecord")

    This also works with absolute paths on your workstation.



    2. If you want to write an output file locally instead of sshfs-mounted
    directory on your workstation, set the clone flag to false:

      getLocalPath("/home2/YOURUSER/local_storage", "output/out.txt", clone=False)



    3. If you want to have the entire folder cloned from your workstation.

      getLocalPath("/home2/YOURUSER/local_storage", "model_dir/")



    4. If you want to use an output folder locally, e.g., when using tensorflow's
    estimator which requires setting model_dir. Set clone to False and use:

      getLocalPath("/home2/YOURUSER/local_storage", "run/experiment1", clone=False)

'''
def getLocalPath(local_storage, path, clone=True):
  if not os.path.exists(local_storage):
    os.makedirs(local_storage)

  # removing trailing /
  while len(path) > 1 and path[-1] == "/":
    path = path[:-1]

  cluster = re.search(r"vision-\d{2}", socket.gethostname())
  if cluster is None:
    print("NOT on cluster: " + path)
    return path

  src = get_remote_path(path)
  destination = local_storage + os.path.abspath(path)


  print("-" * 60)
  print("  On cluster: " + destination)
  print("  Remote    : " + src)

  if os.path.isdir(path) and clone is False:
    cmd("  mkdir -p " + destination)
    print("     >> Not cloned\n")
  else:
    cmd("  mkdir -p " + os.path.dirname(destination))
    if clone:
      cmd("  rsync -ru " + src + " " + os.path.dirname(destination))
      print("     >> Cloned\n")
  # exit()
  return destination

def find_remote_mount_point(path):
  print("PP", path)
  for l in open("/proc/mounts", "r"):
    mp = l.split(" ")
    print(l)
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
  print("AAAA", rd)

  if rd is None or "@" not in rd:
    print("non-mounted file")

    # absolute path
    if path[0] == '/':
      ld2 = find_local_mount_point(os.getcwd())
      rd2 = find_remote_mount_point(ld2)
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

