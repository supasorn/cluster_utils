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


def tmux_commands(cms):
  st = 'tmux new-session \; '
  for i, cm in enumerate(cms):
    st += 'send-keys "' + cm + '" C-m \; '

    if i < len(cms) - 1:
      st += 'split-window \; '
  st += 'select-layout even-vertical\; '
  print(st)
  os.system(st)

def main():
  cmds = ["export CUDA_VISIBLE_DEVICES=%d; source /home/vll/venv_tf1.15/bin/activate; python /home/supasorn/research/orbiter/cluster_utils/runner.py v1g%d sess" % (i, i) for i in range(3)]
  tmux_commands(cmds)


if __name__== "__main__":
  main()

