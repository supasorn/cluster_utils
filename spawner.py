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


tasks = None
stats = None

if "tl_clusters" not in os.environ:
  clusters = ["v2", "v3", "v4"]
else:
  clusters = os.environ["tl_clusters"].split(",")

def getAvailableGPUs_fn(cluster):
  return (cluster, GPUtil.getAvailable(cluster, limit=4))

def getAvailableGPUs():
  p = Pool(len(clusters))
  gpu_list = p.map(getAvailableGPUs_fn, clusters)
  gpu_list.sort(key=lambda x:len(x[1]), reverse=True)
  return gpu_list # cluster, gpu_id

def func(v):
  print(v)
  # os.system('gnome-terminal -- python tasklauncher.py @ sleep 5')
  # subprocess.check_output(['gnome-terminal', '-e', 'python tasklauncher.py @ sleep 5'], shell=True)
  p = Popen(['ssh', 'v2', 'sleep 10'])
  while p.poll() is None:
    print("sleep")
    sleep(1)
  print(p.poll())
  print("done")

def main():
  global tasks

  print(getAvailableGPUs())
  exit()

  if len(sys.argv) != 3:
    print("spawner.py session_folder num_workers")

  sess = "session_" + sys.argv[1]
  num_workers = int(sys.argv[2])

  if not os.path.exists(sess + "/tasks.txt"):
    print("tasks not exists")
    exit()

  with open(sess + "/tasks.txt", "r") as fi:
    tasks = fi.readlines()

  if not os.path.exists(sess + "/tasks_stats.txt"):
    with open(sess + "/tasks_stats.txt", "w") as fo:
      for task in tasks:
        fo.write("-\t0\t" + task)

  with open(sess + "/tasks_stats.txt", "r") as fi:
    stats = fi.readlines()
    stats = [s.split("\t") for s in stats]

  start = time.time()
  while True:
    reqs = glob.glob(sess + "/*.req")

    rewrite = 0
    for req in reqs:
      if os.path.exists(req + ".res"):
        continue

      left = 0
      for stat in stats:
        if stat[1] == "0":
          stat[1] = "1"
          stat[0] = req.split("/")[-1].split(".req")[0]
          with open(req + ".res", "w") as fo:
            fo.write(stat[2])
          left = 1
          rewrite = 1
          break

      if not left:
        with open(req + ".res", "w") as fo:
          fo.write("DONE")

    if rewrite:
      with open(sess + "/tasks_stats.txt", "w") as fo:
        for stat in stats:
          fo.write("\t".join(stat))


    print(time.strftime("%H:%M:%S", time.gmtime(time.time() - start)))
    done = len([x[1] for x in stats if x[1] == '1'])
    print([x[1] for x in stats])
    print("%d/%d" % (done, len(stats)))

    sleep(5)
if __name__== "__main__":
  main()

