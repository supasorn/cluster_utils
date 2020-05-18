import os

nodes = ["10.204.100.111", 
  "10.204.100.112", 
  "10.204.100.113", 
  "10.204.100.114", 
  "10.204.100.117", 
  "10.204.100.118", 
  "10.204.100.119", 
  "10.204.100.120", 
  "10.204.100.123", 
  "10.204.100.124"]
for node in nodes:
  cmd = "sshpass -f password.txt ssh-copy-id " + node
  print(cmd)
  os.system(cmd)

