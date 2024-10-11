'''
add this alias to bashrc or zshrc
alias sg="python YOUR_PATH/singularitylauncher.py"

List gpu usage:
  sg lsgpu

List running tasks
  sg ls

Launch a singularity container in the current directory
  sg here

Launch a job on some free gpu in a some free cluster:
  sg @ [cmd]

Launch a job on a particular cluster (e.g., on v3):
  sg @v3 [cmd]

Launch a job on a particular cluster on a particular gpu:
  sg @v3g0 [cmd]

Launch a job on a particular cluster using 4 gpus:
  sg @v3#4 [cmd]

Launch a job with a specific session name:
  sg name@v3g0 [cmd]
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
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box
from rich.text import Text
from rich.spinner import Spinner
import psutil

session_special = "UL"
console = Console()
singularity_location = "v1:/home2/supasorn/singularity"
singularity_host, singularity_folder = singularity_location.split(":")

if "clusters" not in os.environ:
  clusters = ["v%d" % i for i in range(1, 24)]
else:
  clusters = os.environ["clusters"].split(",")

cluster_status = {cluster: "waiting" for cluster in clusters}

def is_localhost(alias):
  try:
    ip_address = socket.gethostbyname(alias)
    local_ips = {addr.address for iface in psutil.net_if_addrs().values() for addr in iface}
    return ip_address in local_ips
  except socket.gaierror:
    # If the alias cannot be resolved, return False
    return False

def cmd(a, cluster=""):
  if cluster != "":
    a = "ssh " + cluster + " -t \"" + a + "\""

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


def update_table():
  table = Table(title="")
  # table.row_styles = ["none", "dim"]
  table.show_lines = True
  table.box = box.SIMPLE
  table.add_column("Node", justify="left", no_wrap=True, min_width=3)
  table.add_column("Status", justify="left", no_wrap=True, min_width=30)
  for cl, st in cluster_status.items():
      if st == "waiting":
          # Use a spinner for the "waiting" state
          spinner = Spinner("dots", text="")
          table.add_row(cl, spinner)
      else:
          table.add_row(cl, st)
  return table

def showGPUs_fn(cluster):
  info = getGPUsInfo(cluster, True, timeout=10)
  return cluster, Text.from_ansi(printStatus(info))

def showGPUs():
  with Live(update_table(), console=console, refresh_per_second=10, transient=False) as live:
    with Pool(len(clusters)) as p:
      for cluster, status in p.imap_unordered(showGPUs_fn, clusters):
        cluster_status[cluster] = status
        live.update(update_table())
#
# exit()
def main():
  if sys.argv[1] == "ls":
    showWindows()
  elif sys.argv[1] == "lsgpu":
    showGPUs()
  elif sys.argv[1] == "tm":
    os.system("ssh " + sys.argv[2] + " -t \"tmux a\"")
  elif sys.argv[1] == "here" or sys.argv[1] == "sg":
    cluster = ""
    if len(sys.argv) == 3:
      if sys.argv[2][0] == "@":
        cluster = sys.argv[2][1:]

    if (cluster != "" and singularity_host != cluster) or (cluster == "" and not is_localhost(singularity_host)):
      user_host = getpass.getuser() + "@" + get_ip()
      target_sing = f"~/automnt_{singularity_host}_singularity"
      # mkdir locally if not exist
      cmd(f"mkdir -p {target_sing}", cluster)
      # umount if already mounted
      cmd(f"umount {target_sing}", cluster)

      sshfs_cmd = "nohup sshfs -o StrictHostKeyChecking=no -o allow_other -o idmap=user -o IdentityFile=~/.ssh/id_rsa " + singularity_location + " " + target_sing
      cmd(sshfs_cmd, cluster)

      sf = target_sing
    else:
      sf = singularity_folder

    if cluster != "": # sshfs map current folder to cluster

      target = "~/automnt_" + platform.node() + "/"
      cmd(f"mkdir -p {target}", cluster)
      cmd(f"umount {target}", cluster)
      cmd(f"nohup sshfs -o StrictHostKeyChecking=no -o follow_symlinks -o cache=no -o IdentityFile=~/.ssh/id_rsa {user_host}:/ {target}", cluster)

    if sys.argv[1] == "here":
      if cluster != "":
        extracmd = f"-is eval cd {target}{os.getcwd()}"
      else:
        extracmd = f"-is eval cd /host/{os.getcwd()}"
    else:
      extracmd = ""
  
    cmd(f"singularity exec --containall --nv --bind {sf}/home:/home/$USER --bind /:/host {sf}/sand /usr/bin/zsh {extracmd}", cluster)


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
    SING = "/home/supasorn/mnt_v1_singularity"
    rcmd = "source ~/.zshrc && cd " + os.getcwd() +  " && " + tf_cmd 
    ccmd = f"""singularity exec --containall --nv \
        --bind {SING}/home:/home/supasorn \
        --bind /tmp:/tmp \
        --bind {target}:/host \
        "{SING}/sand" \
        /usr/bin/zsh -c '{rcmd}'"""

    # cmd(ccmd)
    terminal_cmd = "cd " + target + os.getcwd().replace("/host", "") + " && " + ccmd

    print(windows)
    if len(windows) == 0:
      tmux_creation = 'tmux new -A -s ' + session_special + ' -n ' + session_name + '\;'
    elif session_name in windows:
      print("Duplicate session name")
      exit()
    else:
      tmux_creation = 'tmux new -A -s ' + session_special + '\; new-window -t ' + session_special + ' -n ' + session_name + ' \;'


    # https://unix.stackexchange.com/questions/266866/how-to-prevent-ctrlc-to-break-ssh-connection/841125
    terminal_cmd = ' ssh ' + cluster + ' -t \\\"trap : INT; ' + terminal_cmd + ' \\\"' # last exit is for when closing ssh connection, also close ROG

    tmux_cmd = tmux_creation + ' send-keys "' + terminal_cmd + '" C-m\;'

    cmd(tmux_cmd)
    # print(tmux_cmd)

if __name__== "__main__":
  main()

