from pexpect import pxssh
import getpass
try:
    s = pxssh.pxssh()
    hostname = "10.204.100.126"
    username = "supasorn"
    password = getpass.getpass('password: ')
    s.login(hostname, username, password)
    # s.sendline("ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa 2>/dev/null <<< y >/dev/null")
    # s.prompt()             
    # print(s.before)        
    s.sendline("ssh-copy-id -f 10.204.162.213")
    s.prompt()
    print(s.before)
    s.logout()
except pxssh.ExceptionPxssh as e:
    print("pxssh failed on login.")
    print(e)
