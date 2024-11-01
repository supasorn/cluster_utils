'''
add this alias to bashrc or zshrc
alias run="python YOUR_PATH/singularitylauncher.py"

List gpu usage:
  run lsgpu

List running tasks
  run ls

Launch a singularity container
  run sg

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
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box
from rich.text import Text
from rich.spinner import Spinner
import psutil

session_special = "UL"
console = Console()
if "SG" in os.environ:
  singularity_locations = os.environ["SG"]
else:
  singularity_locations = "/home2/supasorn/singularity,10.204.100.129:/mnt/data/supasorn/singularity,v23:/home2/supasorn/singularity,v21:/home2/supasorn/singularity,v1:/home2/supasorn/singularity"

singularity_locations = singularity_locations.split(",")
singularity_hosts = []
singularity_folders = []
for location in singularity_locations:
  ab = location.split(":")
  singularity_folders.append(ab[-1])
  if len(ab) > 1:
    singularity_hosts.append(ab[0])


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

def colorprint(msg, tp):
  if tp == "Info": # use orange
    print(f"\033[33mInfo: \033[0m{msg}")
  else:
    print(msg)


def cmd(a, cluster=""):
  if cluster != "":
    a = "ssh " + cluster + " -t \"" + a + "\""

  red = "\033[32m"
  reset = "\033[0m"
  print(f"{red}Exec:{reset} {a}")
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
          spinner = Spinner("point", text="")
          table.add_row(cl, spinner)
      else:
          table.add_row(cl, st)
  return table

def showGPUs_fn(cluster):
  info = getGPUsInfo(cluster, True, timeout=60)
  return cluster, Text.from_ansi(printStatus(info))

def showGPUs():
  with Live(update_table(), console=console, refresh_per_second=10, transient=False) as live:
    with Pool(len(clusters)) as p:
      for cluster, status in p.imap_unordered(showGPUs_fn, clusters):
        cluster_status[cluster] = status
        live.update(update_table())

# def sshfs_mount(src, target):

def mount_singularity(cluster=""):
  if cluster == "": # running locally
    for i in range(len(singularity_hosts)):
      if singularity_hosts[i] == "" or is_localhost(singularity_hosts[i]):
        if os.path.exists(singularity_folders[i]):
          return singularity_folders[i]

    for i in range(len(singularity_hosts)):
      # check if remote location is reachable by ssh and the remote server specified by singularity_location[i] exists
      if singularity_hosts[i] != "" and os.system(f"ssh -o StrictHostKeyChecking=no {singularity_hosts[i]} 'test -d {singularity_folders[i]}'") == 0:
        print("here!", singularity_folders[i])
        singularity_host = singularity_hosts[i]
        singularity_folder = singularity_folders[i]
        singularity_location = singularity_locations[i]
        break
  else: # running remotely
    for i in range(len(singularity_hosts)): 
      if singularity_hosts[i] == cluster:
        return singularity_folders[i]

    for i in range(len(singularity_hosts)):
      if singularity_hosts[i] == "":
        if os.system(f"ssh -o StrictHostKeyChecking=no {cluster} 'test -d {singularity_folders[i]}'") == 0:
          return singularity_folders[i]

    for i in range(len(singularity_hosts)):
      if singularity_hosts[i] != "" and os.system(f"ssh -o StrictHostKeyChecking=no {singularity_hosts[i]} 'test -d {singularity_folders[i]}'") == 0:
        print("here!", singularity_folders[i])
        singularity_host = singularity_hosts[i]
        singularity_folder = singularity_folders[i]
        singularity_location = singularity_locations[i]
        break

  if singularity_host == "":
    print("No singularity location available")
    exit()

  target = "~/mnt/" + singularity_host + "_singularity"
  if not os.path.exists(target):
    cmd("mkdir -p " + target, cluster)
  if os.path.ismount(target):
    cmd("umount " + target, cluster)
  # cmd(f"nohup sshfs -o IdentityFile=~/.ssh/id_rsa -o reconnect,allow_other,idmap=user,cache=no,noauto_cache,StrictHostKeyChecking=no,max_conns=16 {singularity_location} {target} > /dev/null 2>&1", cluster)
  cmd(f"sudo mount -o soft {singularity_location} {target}", cluster)

  return target


def parseNodeCode(argv):
  if "@" not in argv[1]:
    print("Wrong format. Needed: SESSION_NAME@ClUSTER[gID][#NUMGPUs]")
    exit()

  sp = argv[1].split("@")
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
  return cluster, gpu_id, sp
#
# exit()
def main():
  if sys.argv[1] == "ls":
    showWindows()
  elif sys.argv[1] == "lsgpu":
    showGPUs()
  elif sys.argv[1] == "tm":
    os.system("ssh " + sys.argv[2] + " -t \"tmux a\"")
  elif sys.argv[1] == "sg":
    local_sing = mount_singularity()
    colorprint(f"Using singularity {local_sing}", "Info")
    rcmd = "cd /host/" + os.getcwd() 
    terminal_cmd = f"""singularity exec --containall --nv --bind {local_sing}/home:/home/$USER --home /home/$USER --bind /tmp:/tmp --bind /:/host {local_sing}/sand /usr/bin/zsh -is eval \"{rcmd}\""""
    cmd(terminal_cmd)

  else:
    cluster, gpu_id, sp = parseNodeCode(sys.argv)

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

    # Mounting working folder
    print("SSHFS Mapping ...")
    user_host = getpass.getuser() + "@" + get_ip()
    target = "~/mnt/" + platform.node() + "_tl/"
    cmd("mkdir -p " + target, cluster)
    cmd("umount " + target, cluster)
    cmd("nohup sshfs -o StrictHostKeyChecking=no,follow_symlinks,cache=no,idmap=user -o IdentityFile=~/.ssh/id_rsa " + user_host + ":/ " + target + " > /dev/null 2>&1", cluster)

    # Mounting Singularity
    local_sing = mount_singularity(cluster)
    colorprint(f"Using singularity {local_sing}", "Info")

    tf_cmd = "CUDA_VISIBLE_DEVICES=" + gpu_id + " " + " ".join(sys.argv[2:])
    rcmd = "cd /remote/" + os.getcwd() 

    terminal_cmd = f"""singularity exec --containall --nv --bind {local_sing}/home:/home/$USER --home /home/$USER --bind /tmp:/tmp --bind {target}:/remote --bind /:/host {local_sing}/sand /usr/bin/zsh -is eval \\\"{rcmd}\\\""""

    print(windows)
    if len(windows) == 0:
      tmux_creation = 'tmux new -A -s ' + session_special + ' -n ' + session_name + '\;'
    elif session_name in windows:
      print("Duplicate session name")
      exit()
    else:
      tmux_creation = 'tmux new -A -s ' + session_special + '\; new-window -t ' + session_special + ' -n ' + session_name + ' \;'


    # https://unix.stackexchange.com/questions/266866/how-to-prevent-ctrlc-to-break-ssh-connection/841125
    terminal_cmd = ' ssh ' + cluster + ' -t \'trap : INT; ' + terminal_cmd + ' \'; exit' # last exit is for when closing ssh connection, also close ROG
    tmux_cmd = tmux_creation + ' send-keys "' + terminal_cmd + '" C-m\; send-keys "' + tf_cmd + '" C-m\;'
    cmd(tmux_cmd)

if __name__== "__main__":
  main()

