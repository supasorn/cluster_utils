# GPUtil - GPU utilization
#
# A Python module for programmically getting the GPU utilization from NVIDA GPUs using nvidia-smi
#
# Author: Anders Krogh Mortensen (anderskm)
# Date:   16 January 2017
# Web:    https://github.com/anderskm/gputil
#
# LICENSE
#
# MIT License
#
# Copyright (c) 2017 anderskm
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from subprocess import Popen, PIPE
import os
import math
import random
import time
import sys
import platform
import pwd
from threading import Timer

import xml.etree.ElementTree as ET

__version__ = '1.4.0'

def getUser(cluster, pid):
  if cluster == "":
    # the /proc/PID is owned by process creator
    proc_stat_file = os.stat("/proc/%d" % pid)
    # get UID via stat call
    uid = proc_stat_file.st_uid
    # look up the username from uid
    username = pwd.getpwuid(uid)[0]
    return username
  
  p = Popen(["ssh", cluster, "ps -o uname -p", str(pid)], stdout=PIPE)
  stdout, stderr = p.communicate()
  stdout = str(stdout)
  if "\\n" in stdout:
    return stdout.split("\\n")[1]
  return ""


def getGPUsInfo(cluster=""):
  if cluster != "":
    p = Popen(['ssh', cluster, "nvidia-smi", "-q", "-x"], stdout=PIPE)
    timer = Timer(3, p.kill)
    try:
      timer.start()
      stdout, stderr = p.communicate()
    finally:
      timer.cancel()
  else:
    p = Popen(["nvidia-smi","-q", "-x"], stdout=PIPE)
    stdout, stderr = p.communicate()

  output = stdout.decode('UTF-8')
  root = ET.fromstring(output)
  info = []
  for child in root:
    # print(child.tag, end='')
    if child.tag == "gpu":
      gpu_util = int(child.find("utilization").find("gpu_util").text.replace(" %", ""))
      mem_util = int(child.find("utilization").find("memory_util").text.replace(" %", ""))

      procs = child.find("processes").findall("process_info")
      proc_info = []
      for proc in procs:
        pid = proc.find("pid").text
        proc_info.append((pid, getUser(cluster, int(pid))))

      info.append((gpu_util, mem_util, proc_info))
  return info

def printStatus(info, cpu_thresh=15, mem_thresh=15):
  outstr = ""
  for g in info:
    if g[0] < cpu_thresh and g[1] < mem_thresh:
      outstr += "\33[38;5;0m\33[48;5;82m%02d\33[0m " % g[0]
    else:
      outstr += "\33[38;5;0m\33[48;5;196m%02d\33[0m " % g[0]

  proclist = []
  for g in info:
    users = [proc[1] for proc in g[2]]
    if len(users):
      proclist.append(",".join(users))
  outstr += " | ".join(proclist)
  return outstr

def getAvailable(cluster, cpu_thresh=15, mem_thresh=15):
  info = getGPUsInfo(cluster)
  device = []
  print(info)
  for i, g in enumerate(info):
    if g[0] < cpu_thresh and g[1] < mem_thresh:
      device.append(i)
  print("Device", device)
  return device

def getFirstAvailable(cluster, cpu_thresh=15, mem_thres=15):
  devices = getAvailable(cluster, cpu_thresh, mem_thres)
  if len(devices) == 0:
    raise RuntimeError("Cannot find available GPU")
  print(devices)
  return devices[0]

def showUtilization(cluster):
  info = getGPUsInfo(cluster)
  outstr = "Cluster " + cluster
  outstr += " " * (13 - len(outstr))
  return outstr + printStatus(info) + "\n"

# print(getAvailable("v13"))
