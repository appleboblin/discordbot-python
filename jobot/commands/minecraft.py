import logging
import os
import paramiko
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI
import asyncio

load_dotenv()
# Proxmox and SSH details from .env
PROXMOX_HOSTNAME = os.getenv('PROXMOX_ADDRESS')
PROXMOX_USER = os.getenv('PROXMOX_USER')
PROXMOX_PASSWORD = os.getenv('PROXMOX_PASSWORD')
SSH_HOSTNAME = os.getenv('SSH_HOST')
SSH_USER = os.getenv('SSH_USER')
SSH_KEY = os.getenv('SSHK')

# Initialize Proxmox API connection
proxmox = ProxmoxAPI(
    PROXMOX_HOSTNAME, user=PROXMOX_USER, password=PROXMOX_PASSWORD, verify_ssl=False
    )

# Initialize logger
logger = logging.getLogger("bot")

def get_vm_status():
    """Get vm status"""
    vm_status = proxmox.nodes('pve1').qemu('105').status.current.get()
    return vm_status['status']

async def execute_ssh_command(command):
    """Execute command to stop server"""
    sshcon = paramiko.SSHClient()
    sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sshcon.connect(SSH_HOSTNAME, username=SSH_USER, key_filename=SSH_KEY)
    
    # Execute the command
    _stdin, _stdout, _stderr = sshcon.exec_command(command, get_pty=True)
    output = _stdout.read().decode()
    logger.info(f'SSH output: ${output}')
    sshcon.close()

def mc_commands(bot):
    """
    minecraft commands
    """
    @bot.command(
    aliases=['t'],
    help = "Control TFG server",
    description = "Start, Stop and Restart TerraFirmaGreg minecraft server",
    enabled = True,
    hidden = False
    )
    async def tfg(ctx, cmd: str = None):
        """
        Allow user to start, stop and restart tfg minecraft server

        Args:
            ctx (Context): Message context.
            cmd (str): Action.

        Return:
            None: Output response to chat.
        """
        logger.info(f"{ctx.author} used tfg command: {cmd}")

        vm_status = get_vm_status()

        # Check if command is missing
        if not cmd:
            await ctx.send(f"Server status: **{vm_status}**\nPlease specify a command. You can choose between 'start', 'stop', 'restart', or 'status'.")
            return

        cmd = cmd.lower()

        # Check the current server status
        if cmd == 'status':
            if vm_status == 'running':
                await ctx.send("The server is currently **running**.")
            elif vm_status == 'stopped':
                await ctx.send("The server is currently **stopped**.")
            else:
                await ctx.send(f"Server status is unknown: **{vm_status}**")
            return

        # Start the server
        if cmd == 'start':
            if vm_status == 'running':
                await ctx.send("Server is already running.")
            else:
                proxmox.nodes('pve1').qemu('105').status.start.post()
                await ctx.send("Starting the server... Please wait.")
                await asyncio.sleep(35)  # Wait for the server to start
                await ctx.send("Server started successfully.")

        # Stop the server
        elif cmd == 'stop':
            if vm_status == 'stopped':
                await ctx.send("Server is already stopped.")
            else:
                await ctx.send("Stopping the server... Please wait.")
                # Connect via SSH and stop the Minecraft server
                await execute_ssh_command("screen -S minecraft -X stuff '/stop\n'")
                await asyncio.sleep(15)  # Wait for the Minecraft server to stop
                proxmox.nodes('pve1').qemu('105').status.stop.post()
                await ctx.send("Server stopped successfully.")

        # Restart the server
        elif cmd == 'restart':
            if vm_status == 'stopped':
                await ctx.send("Server is not running. Please start the server first.")
            else:
                await ctx.send("Restarting the server... Please wait.")
                # Connect via SSH and stop Minecraft before restarting VM
                await execute_ssh_command("screen -S minecraft -X stuff '/stop\n'")
                proxmox.nodes('pve1').qemu('105').status.reboot.post()
                await asyncio.sleep(40)  # Wait for the server to restart
                await ctx.send("Server restarted successfully.")

        # Invalid command
        else:
            await ctx.send("Invalid command. Please use 'start', 'stop', 'restart' or 'status'.")
