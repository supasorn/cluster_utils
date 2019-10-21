import os
import GPUtil
from subprocess import Popen, PIPE
from multiprocessing import Pool
from functools import partial
import sys


session_special = "TL"
clusters = ["v2", "v3", "v4"]

def cmd(a):
  print("  " + a)
  os.system(a)

def getWindowList(cluster):
  stdout, stderr = Popen(['ssh', cluster, 'tmux list-windows -t ' + session_special], stdout=PIPE).communicate()
  if "[" not in stdout:
    return None
  k = [x.split(" ")[1] for x in stdout.rstrip().split("\n")]
  k = [x[:-1] if x[-1] == '-' or x[-1] == '*' else x for x in k]
  return k

def printGPU(cluster):
  return "Cluster " + cluster + "\n" + GPUtil.showUtilization(ssh=cluster)

def showGPUs():
  p = Pool(len(clusters))
  a = p.map(printGPU, clusters)
  for x in a:
    print(x)

def showWindows():
  p = Pool(len(clusters))
  a = p.map(getWindowList, clusters)
  for i, x in enumerate(a):
    print("Cluster " + clusters[i] + "\n  " + str(x) + "\n")


src = "supasorn@10.204.162.213:/home2/research/orbiter"
target = "/home/supasorn/mnt/orbiter"

cwd = "source /home/vll/venv_tf1.14/bin/activate"


# print(GPUtil.getAvailable(limit=4))
# exit()

def main():
  if sys.argv[1] == "ls":
    showWindows()
  elif sys.argv[1] == "lsgpu":
    showGPUs()
  elif sys.argv[1] == "tm":
    os.system("ssh " + sys.argv[2] + " -t \"tmux a\"")
  else:
    if "@" not in sys.argv[1]:
      print("Wrong format. Needed: SESSION_NAME@ClUSTER[gNUM]")
      exit()

    sp = sys.argv[1].split("@")
    session_name = sp[0]

    code = sp[1]
    cluster = ""
    for c in clusters:
      if code[:len(c)] == c:
        cluster = c
        code = code[len(c):]
        break

    if cluster == "":
      print("Invalid cluster")
      exit()
    if code != "" and (code[0] != 'g' or code[1] not in ["0", "1", "2", "3", "a"]):
      print("Invalid GPU code")
      exit()

    # auto
    if code == "" or code[1] == "a":
      gpu_id = str(GPUtil.getFirstAvailable(cluster)[0])
    else:
      gpu_id = code[1]

    print(gpu_id)

    print("Using cluster: " + cluster)
    print("Using gpu: " + gpu_id)
    print("Session name: " + session_name)

    print("SSHFS Mapping ...")
    sshfs_cmd = "ssh " + cluster + " -t \"mkdir -p " + target + "; nohup sshfs -o cache=no -o IdentityFile=/home/supasorn/.ssh/id_rsa " + src + " " + target + "\""
    cmd(sshfs_cmd)


    tf_cmd = "echo 'done'"
    tf_cmd = "CUDA_VISIBLE_DEVICES=" + gpu_id + " " + " ".join(sys.argv[2:])

    terminal_cmd = "source /home/vll/venv_tf1.14/bin/activate; cd " + target + "; " + tf_cmd

    windows = getWindowList(cluster)
    if windows is None:
      tmux_creation = 'tmux new -A -s ' + session_special + ' -n ' + session_name + '\;'
    elif session_name in windows:
      print("Duplicate session name")
      exit()
    else:
      tmux_creation = 'tmux new -A -s ' + session_special + '\; new-window -t ' + session_special + ' -n ' + session_name + ' \;'

    tmux_cmd = 'ssh ' + cluster + ' -t "' + tmux_creation + ' send-keys \\\" ' + terminal_cmd + '\\\" C-m\;"'
    cmd(tmux_cmd)

if __name__== "__main__":
  main()

