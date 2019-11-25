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
  p = Pool(2)
  a = p.map(func, range(2))

if __name__== "__main__":
  main()

