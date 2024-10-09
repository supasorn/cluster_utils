from GPUtil import *
from subprocess import Popen, PIPE
from multiprocessing import Pool
from functools import partial
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box
from rich.spinner import Spinner
import random

session_special = "UL"
clusters = [f'v{i}' for i in range(1, 24)]
console = Console()

cluster_status = {cluster: "waiting" for cluster in clusters}

def update_table():
  table = Table(title="")
  # table.row_styles = ["none", "dim"]
  table.show_lines = True
  table.box = box.SIMPLE
  table.add_column("Node", justify="left")
  table.add_column("Status", justify="left")
  for cl, st in cluster_status.items():
      if st == "waiting":
          # Use a spinner for the "waiting" state
          spinner = Spinner("dots", text="")
          table.add_row(cl, spinner)
      else:
          table.add_row(cl, st)
  return table

def showUtilization(cluster):
  info = getGPUsInfo(cluster, True, timeout=10)
  # outstr = " " * (13 - len(outstr))
  # return outstr + printStatus(info) + "\n"
  return printStatus(info)

def showGPUs_fn(cluster):
  out = showUtilization(cluster)
  return cluster, out

def showGPUs():
  with Live(update_table(), console=console, refresh_per_second=10, transient=False) as live:
    with Pool(len(clusters)) as p:
      for cluster, status in p.imap_unordered(showGPUs_fn, clusters):
        cluster_status[cluster] = status
        live.update(update_table())

def main():
  showGPUs()

if __name__== "__main__":
  main()

