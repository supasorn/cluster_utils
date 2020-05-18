import os

nodes = ["v1", "v2", "v3", "v4", "v7", "v8", "v9", "v10", "v23", "v24"]
for node in nodes:
  cmd = "sshpass -f password.txt ssh-copy-id " + node
  os.system(cmd)

