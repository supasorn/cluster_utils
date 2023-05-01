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
import subprocess
import time
import glob
import platform


tasks = None
stats = None

if "tl_clusters" not in os.environ:
  clusters = ["v1", "v2", "v3", "v4"]
else:
  clusters = os.environ["tl_clusters"].split(",")

if "tl_venv" not in os.environ:
  venv = "source /home/vll/venv_tf1.15/bin/activate"
else:
  venv = os.environ["tl_venv"]

def getAvailableGPUs_fn(cluster):
  return (cluster, GPUtil.getAvailable(cluster, limit=4))

def getAvailableGPUs():
  print("Getting available machines...")
  p = Pool(len(clusters))
  gpu_list = p.map(getAvailableGPUs_fn, clusters)
  gpu_list.sort(key=lambda x:len(x[1]), reverse=True)
  return gpu_list # cluster, gpu_id

def cmd(a):
  print("  " + a)
  os.system(a)

def get_ip():
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  try:
    # doesn't even have to be reachable
    s.connect(('10.255.255.255', 1))
    IP = s.getsockname()[0]
  except:
    print("Can't automatically determine IP")
    exit()
  finally:
    s.close()
  return IP

def getWindowList(cluster):
  stdout, stderr = Popen(['ssh', cluster, 'tmux list-windows -t ' + session_special], stdout=PIPE).communicate()
  stdout = str(stdout)
  # print(stdout)
  if "[" not in stdout:
    return []
  k = [x.split(" ")[1] for x in stdout.rstrip().split("\\n") if " " in x]
  k = [x[:-1] if x[-1] == '-' or x[-1] == '*' else x for x in k]
  return k

def spawnAll(session_special, freeGpus):
  for cpu in freeGpus:
    cluster = cpu[0]

    user_host = getpass.getuser() + "@" + get_ip()
    target = "~/mnt_sp_" + platform.node() + "/"
    sshfs_cmd = "ssh " + cluster + " -t \"mkdir -p " + target + "; nohup sshfs -o follow_symlinks -o cache=no -o IdentityFile=~/.ssh/id_rsa " + user_host + ":/ " + target + "\""
    cmd(sshfs_cmd)

    tmux_cmd = "tmux kill-session -t %s;" % (session_special)
    for i, gpu in enumerate(cpu[1]):
      if i == 0:
        tmux_cmd += 'tmux new -A -s '
      else:
        tmux_cmd += 'new-window -t '
      tmux_cmd += session_special + ' -n ' + ("%sg%d" % (cluster, gpu)) + ' \; '

      thisdir = os.path.dirname(os.path.abspath(__file__))

      tmux_cmd += 'send-keys \\\"export CUDA_VISIBLE_DEVICES=%s; cd %s; %s; python %s%s/runner.py %sg%d %s %s/\\\" C-m \; ' % (str(gpu), target + os.getcwd(), venv, target, thisdir, cluster, gpu, session_special, target + os.getcwd())

    tmux_cmd += 'new-window -t ' + session_special + ' -n head \; '

    tmux_cmd = 'ssh ' + cluster + ' -t "' + tmux_cmd + ' send-keys \\\"tmux detach\\\" C-m\;"'

    cmd(tmux_cmd)
    # break


def main():
  global tasks


  if len(sys.argv) != 3:
    print("spawner.py session_folder num_workers")


  sess = "SP_" + sys.argv[1]
  num_workers = int(sys.argv[2])

  freeGpus = [cpu for cpu in getAvailableGPUs() if len(cpu[1]) > 0]
  numFreeGpus = sum(len(cpu[1]) for cpu in freeGpus)

  needRemove = numFreeGpus - num_workers

  while needRemove > 0:
    best = 0
    bestcpu = 0
    # find cpu with least gpu usage
    for cpu in freeGpus:
      if len(cpu[1]) > best:
        best = len(cpu[1])
        bestcpu = cpu

    print("remove", bestcpu)
    freeGpus.remove(bestcpu)
    if len(bestcpu[1]) > 1:
      freeGpus.append((bestcpu[0], bestcpu[1][:-1]))
    needRemove -= 1

  numUsedGpus = sum(len(cpu[1]) for cpu in freeGpus)
  print(freeGpus)
  spawnAll(sess, freeGpus)

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
    print(reqs)
    print(glob.glob(sess + "/*.req.res"))
    if len(glob.glob(sess + "/*.done")) == numUsedGpus:
      os.system("rm " + sess + "/*.done")
      break

    rewrite = 0
    for req in reqs:
      if os.path.exists(req + ".res"):
        print(req + ".res exists")
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

    sleep(3)
if __name__== "__main__":
  main()

