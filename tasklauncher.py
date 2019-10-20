import os
from subprocess import Popen, PIPE

session_special = "TFL"

def cmd(a):
  print(a)
  os.system(a)

def getWindowList():
  stdout, stderr = Popen(['ssh', cluster, 'tmux list-windows -t ' + session_special], stdout=PIPE).communicate()
  if "[" not in stdout:
    return None
  k = [x.split(" ")[1] for x in stdout.rstrip().split("\n")]
  k = [x[:-1] if x[-1] == '-' or x[-1] == '*' else x for x in k]
  return k

cluster = "v3"
session_name = "aek6"
src = "supasorn@10.204.162.213:/home2/research/orbiter"
target = "/home/supasorn/mnt/orbiter"

cwd = "source /home/vll/venv_tf1.14/bin/activate"

sshfs_cmd = "ssh " + cluster + " -t \"mkdir -p " + target + "; nohup sshfs -o cache=no -o IdentityFile=/home/supasorn/.ssh/id_rsa " + src + " " + target + "\""
# cmd(sshfs_cmd)


# tf_cmd = "python model_depth_discrete.py --model_dir=temple2/tmp11 --layers=6 --input=c0043_50 -dataset=temple2 -up=right --tvc=0.001 --ref_img=0043"
tf_cmd = "echo 'done'"

terminal_cmd = "source /home/vll/venv_tf1.14/bin/activate; cd " + target + "; " + tf_cmd



windows = getWindowList()
if windows is None:
  tmux_creation = 'tmux new -A -s ' + session_special + ' -n ' + session_name + '\;'
elif session_name in windows:
  print("Duplicate session name")
  exit()
else:
  tmux_creation = 'tmux new -A -s ' + session_special + '\; new-window -t ' + session_special + ' -n ' + session_name + ' \;'

tmux_cmd = 'ssh ' + cluster + ' -t "' + tmux_creation + ' send-keys \\\" ' + terminal_cmd + '\\\" C-m\;"'
cmd(tmux_cmd)
