from proxmoxer.core import AuthenticationError
import logging
import os
import paramiko
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI, ResourceException
import asyncio

# Load environment variables
load_dotenv()

# Environment variable settings
PROXMOX_HOSTNAME = os.getenv('PROXMOX_ADDRESS')
PROXMOX_USER = os.getenv('PROXMOX_USER')
PROXMOX_PASSWORD = os.getenv('PROXMOX_PASSWORD')
SSH_HOSTNAME = os.getenv('SSH_HOST')
SSH_USER = os.getenv('SSH_USER')
SSH_KEY = os.getenv('SSHK')

# Initialize logger
logger = logging.getLogger("bot")

def retry_proxmox_request(func):
    """
    Decorator to retry Proxmox requests on authentication error.
    If authentication fails, reconnect and retry the request.
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise e
        except ResourceException as e:
            logger.error(f"Proxmox resource error: {e}")
            raise e
    return wrapper

# Function to establish Proxmox API connection
def connect_to_proxmox():
    try:
        proxmox = ProxmoxAPI(PROXMOX_HOSTNAME, user=PROXMOX_USER, password=PROXMOX_PASSWORD, verify_ssl=False)
        logger.info("Proxmox connection established")
        return proxmox
    except AuthenticationError as e:
        logger.error(f"Failed to authenticate Proxmox user: {e}")
        raise e
    except Exception as e:
        logger.error(f"Failed to connect to Proxmox: {e}")
        raise e

@retry_proxmox_request
async def get_vm_status():
    """Get VM status"""
    proxmox = connect_to_proxmox()  # Connect when function is called
    vm_status = proxmox.nodes('pve1').qemu('105').status.current.get()
    return vm_status['status']

async def execute_ssh_command(command):
    """Execute a command via SSH to stop the server"""
    sshcon = paramiko.SSHClient()
    sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sshcon.connect(SSH_HOSTNAME, username=SSH_USER, key_filename=SSH_KEY)
    
    # Execute the command
    _stdin, _stdout, _stderr = sshcon.exec_command(command, get_pty=True)
    output = _stdout.read().decode()
    logger.info(f'SSH output: {output}')
    sshcon.close()

def mc_commands(bot):
    """
    Minecraft server commands
    """
    @bot.command(
        aliases=['t'],
        help="Control TFG server",
        description="Start, Stop and Restart TerraFirmaGreg minecraft server",
        enabled=True,
        hidden=False
    )
    async def tfg(ctx, cmd: str = None):
        """
        Allow user to start, stop and restart the TFG Minecraft server

        Args:
            ctx (Context): Message context.
            cmd (str): Action.

        Returns:
            None: Outputs response to chat.
        """
        logger.info(f"{ctx.author} used tfg command: {cmd}")

        # Connect to Proxmox and get VM status
        try:
            vm_status = await get_vm_status()
        except AuthenticationError:
            await ctx.send("Failed to authenticate to Proxmox. Please check your credentials.")
            return
        except Exception as e:
            await ctx.send(f"Error connecting to Proxmox: {e}")
            return

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
                proxmox = connect_to_proxmox()
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
                proxmox = connect_to_proxmox()
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
                proxmox = connect_to_proxmox()
                proxmox.nodes('pve1').qemu('105').status.reboot.post()
                await asyncio.sleep(40)  # Wait for the server to restart
                await ctx.send("Server restarted successfully.")

        # Invalid command
        else:
            await ctx.send("Invalid command. Please use 'start', 'stop', 'restart', or 'status'.")
