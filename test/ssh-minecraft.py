import os
import paramiko
from dotenv import load_dotenv

load_dotenv()
hostname = os.getenv('SSH_HOST')
user     = os.getenv('SSH_USER')
SSHK     = os.getenv('SSHK')
sshcon   = paramiko.client.SSHClient()  # will create the object
sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # no known_hosts error
sshcon.connect(hostname, username=user, key_filename=SSHK) # no passwd needed

# Execute the command in a screen session
# Check if the screen session exists or create a new one
# _stdin, _stdout, _stderr = sshcon.exec_command("screen -list | grep minecraft || screen -dmS minecraft bash", get_pty=True)
# print(_stdout.read().decode())  # Output from the command

# Reattach to the screen session and run a command inside it
_stdin, _stdout, _stderr = sshcon.exec_command("screen -S minecraft -X '/stop\n'", get_pty=True)
print(_stdout.read().decode())

# Close the SSH connection
sshcon.close()
print("done")