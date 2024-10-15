from proxmoxer import ProxmoxAPI
import os
from dotenv import load_dotenv

load_dotenv()
hostname = os.getenv('PROXMOX_ADDRESS')
px_user     = os.getenv('PROXMOX_USER')
SSHK     = os.getenv('PROXMOX_PASSWORD')

proxmox = ProxmoxAPI(
    hostname, user=px_user, password=SSHK, verify_ssl=False
)

# start vm
# proxmox.nodes('pve1').qemu('105').status.start.post()

# stop vm
# proxmox.nodes('pve1').qemu('105').status.stop.post()

# restart vm
proxmox.nodes('pve1').qemu('105').status.reboot.post()
# give 10 seconds mc server stop timer just to be safe.
# give 40 seconds proxmox server reboot time to be safe
vm_status = proxmox.nodes('pve1').qemu('105').status.current.get()
print(vm_status['status'])
# status: running, stopped