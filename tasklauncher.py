'''
add this alias to bashrc or zshrc
alias run="python YOUR_PATH/tasklauncher_uni.py"

List gpu usage:
  run lsgpu

List running tasks
  run ls

Launch a job on some free gpu in a some free cluster:
  run @ [cmd]

Launch a job on a particular cluster (e.g., on v3):
  run @v3 [cmd]

Launch a job on a particular cluster on a particular gpu:
  run @v3g0 [cmd]

Launch a job on a particular cluster using 4 gpus:
  run @v3#4 [cmd]

Launch a job with a specific session name:
  run name@v3g0 [cmd]
'''

import os
from GPUtil import *
from subprocess import Popen, PIPE
from multiprocessing import Pool
from functools import partial
import sys
import socket
import getpass
import platform
import random

session_special = "UL"

if "clusters" not in os.environ:
  clusters = ["v%d" % i for i in range(1, 24)]
  print(clusters)
else:
  clusters = os.environ["clusters"].split(",")

if "tl_venv" not in os.environ:
  venv = "source /home/vll/venv_pytorch1.9/bin/activate"
else:
  venv = os.environ["tl_venv"]

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

def showGPUs_fn(cluster):
  return showUtilization(cluster)

def showGPUs():
  p = Pool(len(clusters))
  a = p.map(showGPUs_fn, clusters)
  print("")
  for x in a:
    print(x)

def getWindowList():
  stdout, stderr = Popen(['tmux list-windows -t ' + session_special], stdout=PIPE, shell=True).communicate()
  stdout = str(stdout)
  if "[" not in stdout:
    return []

  st = stdout.rstrip()
  sp = "\n" if "\n" in st else "\\n"
  k = [x.split(" ")[1] for x in st.split(sp) if " " in x]
  k = [x[:-1] if (x[-1] == '-' or x[-1] == '*') else x for x in k]
  return k

def showWindows():
  # p = Pool(len(clusters))
  a = getWindowList() #p.map(getWindowList)
  for i, x in enumerate(a):
    # print("Cluster " + clusters[i] + "\n  " + str(x) + "\n")
    print(str(x))


def getAvailableGPUs_fn(cluster):
  return (cluster, getAvailable(cluster))

def getAvailableGPUs(numgpu = 1, custom_clusters=None):
  if custom_clusters is not None:
    cs = custom_clusters
  else:
    cs = clusters

  p = Pool(len(cs))
  gpu_list = p.map(getAvailableGPUs_fn, cs)

  # no_power_saving = ["v7", "v8", "v9", "v10", "v23", "v24"]
  for gpu in gpu_list:
    random.shuffle(gpu[1])
    # if gpu[0] not in no_power_saving and len(gpu[1]) > 0:
      # gpu[1].pop()

  gpu_list.sort(key=lambda x:len(x[1]), reverse=True)
  # print(gpu_list)

  print(gpu_list[0][1])
  if len(gpu_list[0][1]) < numgpu:
    raise Exception("%d gpus not available" % numgpu)

  return (gpu_list[0][0], gpu_list[0][1][:numgpu]) # cluster, gpu_id

def main():
  if sys.argv[1] == "ls":
    showWindows()
  elif sys.argv[1] == "lsgpu":
    showGPUs()
  elif sys.argv[1] == "tm":
    os.system("ssh " + sys.argv[2] + " -t \"tmux a\"")
  else:
    if "@" not in sys.argv[1]:
      print("Wrong format. Needed: SESSION_NAME@ClUSTER[gID][#NUMGPUs]")
      exit()

    sp = sys.argv[1].split("@")
    code = sp[1]

    if "#" in code: # user specify multiple gpus
      sp2 = code.split("#")
      code = sp2[0]
      num_gpu = int(sp2[1])
      if num_gpu < 0 or num_gpu > 4:
        raise ValueError("num_gpu invalid")
    else:
      num_gpu=1

    if code == "": #automatically select cluster and gpu
      print("Finding a free cluster and a free gpu...")
      cluster, gpu_id = getAvailableGPUs(num_gpu)
      gpu_id = ",".join([str(x) for x in gpu_id])
    else:
      cluster = ""
      if "g" in code:
        cluster, gpu = code.split("g")
      else:
        cluster = code
        gpu = "a"

      if cluster not in clusters:
        print("Invalid cluster")
        exit()
      # if gpu not in ["0", "1", "2", "3", "a"]:
        # print("Invalid GPU code")
        # exit()

      if num_gpu == 0:
        gpu_id = ""
      elif num_gpu > 1:
        cluster, gpu_id = getAvailableGPUs(num_gpu, [cluster])
        gpu_id = ",".join([str(x) for x in gpu_id[:num_gpu]])
      else:
        # auto
        if gpu == "a":
          print("Finding a free gpu...")
          gpu_id = str(getFirstAvailable(cluster))
        else:
          gpu_id = gpu

    print("Using cluster: " + cluster)
    print("Using gpu: " + gpu_id)

    print("Establishing session name...")
    windows = getWindowList()
    if sp[0] == "":
      sp[0] = cluster + "_0"
      while len(windows) and sp[0] in windows:
        sp[0] = cluster + "_%d" % (int(sp[0].split("_")[-1]) + 1)
    else:
      sp[0] = cluster + "_" + sp[0]

    session_name = sp[0]
    print("Session name: " + session_name)


    print("SSHFS Mapping ...")
    user_host = getpass.getuser() + "@" + get_ip()
    target = "~/mnt_tl_" + platform.node() + "/"
    sshfs_cmd = "ssh " + cluster + " -t \"mkdir -p " + target + "; nohup sshfs -o StrictHostKeyChecking=no -o follow_symlinks -o cache=no -o IdentityFile=~/.ssh/id_rsa " + user_host + ":/ " + target + "\""
    cmd(sshfs_cmd)

    tf_cmd = "CUDA_VISIBLE_DEVICES=" + gpu_id + " " + " ".join(sys.argv[2:])
    # terminal_cmd = venv + "; cd " + target + os.getcwd() + "; " + tf_cmd + "; tmux detach"
    terminal_cmd = venv + "; cd " + target + os.getcwd() + "; " + tf_cmd

    print(windows)
    if len(windows) == 0:
      tmux_creation = 'tmux new -A -s ' + session_special + ' -n ' + session_name + '\;'
    elif session_name in windows:
      print("Duplicate session name")
      exit()
    else:
      tmux_creation = 'tmux new -A -s ' + session_special + '\; new-window -t ' + session_special + ' -n ' + session_name + ' \;'


    # https://unix.stackexchange.com/questions/266866/how-to-prevent-ctrlc-to-break-ssh-connection/841125
    terminal_cmd = ' ssh ' + cluster + ' -t \\\"trap : INT; ' + terminal_cmd + ' ; echo \\\"' + tf_cmd + '\\\" >> ~/.zsh_history; /bin/zsh \\\"; exit' # last exit is for when closing ssh connection, also close ROG

    # tmux_cmd = tmux_creation + ' send-keys "' + terminal_cmd + '" C-m\; splitw -l 4 \; send-keys "' + tf_cmd + '" \; select-pane -P \'bg=colour234 fg=colour72\' \; select-pane -t 1 \;'
    tmux_cmd = tmux_creation + ' send-keys "' + terminal_cmd + '" C-m\;'

    cmd(tmux_cmd)
    # print(tmux_cmd)

if __name__== "__main__":
  main()

