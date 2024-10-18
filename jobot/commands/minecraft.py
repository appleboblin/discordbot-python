from proxmoxer.core import AuthenticationError
import logging
import os
import paramiko
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI, ResourceException
import asyncio
import minestat
import discord

# Load environment variables
load_dotenv()

# Environment variable settings
PROXMOX_HOSTNAME = os.getenv('PROXMOX_ADDRESS')
PROXMOX_USER = os.getenv('PROXMOX_USER')
PROXMOX_PASSWORD = os.getenv('PROXMOX_PASSWORD')
SSH_HOSTNAME = os.getenv('SSH_HOST')
SSH_USER = os.getenv('SSH_USER')
SSH_KEY = os.getenv('SSHK')
MC_HOST = os.getenv('MINECRAFT_ADDRESS')

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

async def check_minecraft_status():
    """
    Check Minecraft server status using MineStat.
    Returns True if online, False otherwise.
    """
    logger.info(f'Checking MC status')
    mc = minestat.MineStat(MC_HOST)
    return mc

async def check_vm_status():
    """
    Fetches the current VM status from Proxmox.
    """
    return await get_vm_status()  # Returns 'running' or 'stopped'

async def wait_vm_status(target_status, retries=7, delay=5):
    """
    Poll the VM status until reaches target status or retries run out.

    Arg:
        target_status (str): Desired status, 'running' or 'stopped'
        retries (int): Number of retries before giving up
        delay (int): Seconds to wait between retries
    """
    for _ in range(retries):
        current_status = await check_vm_status()
        if current_status == target_status:
            return True
        await asyncio.sleep(delay)
    return False

async def start_server(ctx):
    """
    Start the Minecraft server if it's not already running.
    
    Args:
        ctx (Context): The message context.
    """
    try:
        vm_status = await get_vm_status()
        if vm_status == 'stopped':
            await ctx.send("Starting the server... Please wait.")
            proxmox = connect_to_proxmox()
            proxmox.nodes('pve1').qemu('105').status.start.post()
            logger.info(f'Starting proxmox 105')
            await asyncio.sleep(40)  # Wait for the server to start
            mc_status = await check_minecraft_status()
            if not mc_status.online:
                logger.info(f'MC not started')
                await execute_ssh_command("screen -S minecraft -X stuff 'java -Xmx11G -Xms11G -jar minecraft_server.jar nogui\n'")
                logger.info(f'Starting TFG server')
                await asyncio.sleep(26)
                for _ in range(7):
                    mc_status = await check_minecraft_status()
                    if mc_status.online:
                        logger.info(f'TFG server started successfuly')
                        await ctx.send("Server started successfully.")
                        return
                    await asyncio.sleep(5)
                logger.info(f'Server failed to start')
                await ctx.send("Server failed to start")
                return
            logger.info(f'TFG server started successfuly')
            await ctx.send("Server started successfully.")
        else:
            mc_status = await check_minecraft_status()
            if not mc_status.online:
                await execute_ssh_command("screen -S minecraft -X stuff 'java -Xmx11G -Xms11G -jar minecraft_server.jar nogui\n'")
                logger.info(f'Starting TFG server')
                await asyncio.sleep(26)
                for _ in range(7):
                    mc_status = await check_minecraft_status()
                    if mc_status.online:
                        logger.info(f'TFG server started successfully')
                        await ctx.send("Server started successfully.")
                        return
                    await asyncio.sleep(5)
                logger.info(f'Server failed to start')
                await ctx.send("Server failed to start")
                return
            await ctx.send("Server already started")
    except Exception as e:
        logger.info(f"Failed to start the server: {e}")
        await ctx.send(f"Failed to start the server: {e}")


async def stop_server(ctx):
    """
    Stop the Minecraft server if it's running.
    
    Args:
        ctx (Context): The message context.
    """
    try:
        vm_status = await get_vm_status()
        if vm_status == 'stopped':
            await ctx.send("Server is already stopped.")
        else:
            await ctx.send("Stopping the server... Please wait.")
            # Stop Minecraft via SSH first
            await execute_ssh_command("screen -S minecraft -X stuff '/stop\n'")
            logger.info(f'Stopping TFG server')
            await asyncio.sleep(10)  # Wait for Minecraft to stop
            for _ in range(7):
                mc_status = await check_minecraft_status()
                if not mc_status.online:
                    proxmox = connect_to_proxmox()
                    proxmox.nodes('pve1').qemu('105').status.stop.post()
                    logger.info(f'Stopping proxmox 105')
                    await asyncio.sleep(5)
                    if await wait_vm_status("stopped"):
                        logger.info(f'Proxmox 105 stopped')
                        await ctx.send("Server stopped successfully.")
                        return
                    else: 
                        logger.info(f'Proxmox stopped failed')
                        await ctx.send("VM stopped failed.")
                        return
                await asyncio.sleep(5)
    except Exception as e:
        logger.info(f"Failed to stop the server: {e}")
        await ctx.send(f"Failed to stop the server: {e}")


async def restart_server(ctx):
    """
    Restart the Minecraft server if it's running.
    
    Args:
        ctx (Context): The message context.
    """
    try:
        vm_status = await get_vm_status()
        if vm_status == 'stopped':
            await ctx.send("Server is not running. Please start the server first.")
        else:
            await ctx.send("Restarting the server... Please wait.")
            await stop_server(ctx)
            await start_server(ctx)
            await ctx.send("Server restarted successfully.")
    except Exception as e:
        logger.info(f'Failed to restart the server: {e}')
        await ctx.send(f"Failed to restart the server: {e}")

async def server_status(ctx):
    """
    Get status of minecraft server
    
    Args:
        ctx (Context): The message context.
    """
    logger.info(f"Checking TFG server status")
    embed_wait=discord.Embed(title="Server Status", description="Checking server status... Please wait", color=0xf6d32d)
    embed_wait.add_field(name="Status", value="Checking", inline=True)
    waiting_embed = await ctx.send(embed=embed_wait)
    vm_status = await check_vm_status()
    mc_status = await check_minecraft_status()

    if vm_status == "stopped":
        # If VM is stopped, send vm offline status
        embed=discord.Embed(title="Server Status", color=0xf66151)
        embed.add_field(name="Status", value="Offline", inline=True)
        await waiting_embed.edit(embed=embed)
    elif vm_status == "running":
        # If VM is running, check mc server status
        if mc_status.online:
            player_status = f"{mc_status.current_players}/{mc_status.max_players}"
            server_version = f"{mc_status.version}"
            embed=discord.Embed(title="Server Status", color=0x33d17a)
            embed.add_field(name="Status", value="Online", inline=True)
            embed.add_field(name="Player count", value=player_status, inline=True)
            embed.add_field(name="Version", value=mc_status.version, inline=True)
            await waiting_embed.edit(embed=embed)
        else:
            embed=discord.Embed(title="Server Status", description="VM running, server offline", color=0xf66151)
            embed.add_field(name="Status", value="Unknown", inline=True)
            await waiting_embed.edit(embed=embed)

    else:
        embed=discord.Embed(title="Server Status", color=0xf66151)
        embed.add_field(name="Status", value=f"VM status: {vm_status}", inline=True)
        await waiting_embed.edit(embed=embed)


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

        # Check if the command is provided
        if not cmd:
            await server_status(ctx)
            return

        cmd = cmd.lower()

        # Execute corresponding command function
        if cmd == 'start':
            await start_server(ctx)
        elif cmd == 'stop':
            await stop_server(ctx)
        elif cmd == 'restart':
            await restart_server(ctx)
        else:
            await ctx.send("Invalid command. Please use 'start', 'stop', or 'restart'.")