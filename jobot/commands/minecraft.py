from proxmoxer.core import AuthenticationError
import logging
import os
import paramiko
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI, ResourceException
import asyncio
import minestat
import discord
from mcrcon import MCRcon

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
RCON_PASSWORD = os.getenv('MC_RCON_PASSWORD')

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
    output = _stdout.readlines()
    logger.info(f'SSH output: {output}')
    sshcon.close()
    return output  # Return the last line

async def execute_rcon_command(ctx, command):
    """Execute a command via rcon to mc server"""
    with MCRcon(MC_HOST, RCON_PASSWORD) as mcr:
        resp = mcr.command(command)
    if resp:
        await ctx.send(resp)

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
                await execute_rcon_command(ctx, "/stop")
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
                await execute_ssh_command("/home/applebbolin/start-screen")
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
            try:
                rcon_output = await execute_rcon_command(ctx, "/stop")
                logger.info(f'{rcon_output}')
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
            except:
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
    except Exception as e:
        logger.info(f'Failed to restart the server: {e}')
        await ctx.send(f"Failed to restart the server: {e}")

async def server_status(ctx, delay=0):
    """
    Get status of minecraft server
    
    Args:
        ctx (Context): The message context.
    """
    logger.info(f"Checking TFG server status")
    embed_wait=discord.Embed(title="Server Status", description="Checking server status... Please wait", color=0xf6d32d)
    embed_wait.add_field(name="Status", value="Checking", inline=True)
    waiting_embed = await ctx.send(embed=embed_wait)
    await asyncio.sleep(delay)
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

async def download_update(ctx):
    """
    Run bash script on server to download latest tfg update
    
    Args:
        ctx (Context): The message context.
    """
    try:
        vm_status = await get_vm_status()
        if vm_status == 'running':
            await ctx.send("Downloading update...")
            output = await execute_ssh_command("/home/appleboblin/update.sh")
            await ctx.send(f"{output[-1]}")
        else:
            await ctx.send("Please start the server first.")
    except Exception as e:
        logger.info(f'Failed to execute script: {e}')
        await ctx.send(f"Failed to execute script: {e}")

async def update_mc_server(ctx, arg1, arg2):
    """Execute a commands via SSH to update MC server"""
    sshcon = paramiko.SSHClient()
    sshcon.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sshcon.connect(SSH_HOSTNAME, username=SSH_USER, key_filename=SSH_KEY)
    await execute_rcon_command(ctx, "/stop")
    await asyncio.sleep(10)
    await ctx.send(f"Updating server...")
    # Move world
    try:
        move_files = (
            f'cp -pf "/home/appleboblin/tfg{arg1}/.minecraft/server.properties" "/home/appleboblin/tfg{arg2}/.minecraft/server.properties" && '
            f'cp -pf "/home/appleboblin/tfg{arg1}/.minecraft/config/ftbbackups2.json" "/home/appleboblin/tfg{arg2}/.minecraft/config/ftbbackups2.json" && '
            f'mkdir -p "/home/appleboblin/tfg{arg2}/.minecraft/world/" && '
            f'cp -rpf "/home/appleboblin/tfg{arg1}/.minecraft/world/"* "/home/appleboblin/tfg{arg2}/.minecraft/world/"'
        )
        _stdin, _stdout, _stderr = sshcon.exec_command(move_files, get_pty=True)
        output = _stdout.readlines()
        logger.info(f'copying world from {arg1} to {arg2}: {output}')
        _stdin, _stdout, _stderr = sshcon.exec_command('screen -X -S minecraft quit', get_pty=True)
        output = _stdout.readlines()
        logger.info(f'killed minecraft screen instance')
        replace_starter = f"sed -i 's/{arg1}/{arg2}/g' /home/appleboblin/start-screen"
        _stdin, _stdout, _stderr = sshcon.exec_command(replace_starter, get_pty=True)
        output = _stdout.readlines()
        logger.info(f'update start-screen script')
        _stdin, _stdout, _stderr = sshcon.exec_command('/home/appleboblin/start-screen', get_pty=True)
        output = _stdout.readlines()
        logger.info(f'run start-screen script')
        await ctx.send(f"Updated modpack from v{arg1} to v{arg2}, starting server.")
        await server_status(ctx, delay=55)
    except Exception as e:
        await ctx.send(f"Failed to upgrade modpack: {e}")
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
    async def tfg(ctx, cmd: str = None, *args):
        """
        Allow user to start, stop and restart the TFG Minecraft server

        Args:
            ctx (Context): Message context.
            cmd (str): Action.
            args (tuple): Additional arguments for 'commands'

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
        elif cmd == 'command':
            server_command = ' '.join(args) 
            logger.info(f"{server_command}")
            await execute_rcon_command(ctx, server_command)
        elif cmd == 'download':
            await download_update(ctx)
        elif cmd == 'update':
            # Check if args has enough elements
            if len(args) < 2:
                await ctx.send("Please provide old version and new version of the mod.")
                return
            arg1, arg2 = args[0], args[1]
            print(arg1 + ' ' + arg2)
            await update_mc_server(ctx, arg1, arg2)
        else:
            await ctx.send("Invalid command. Please use 'start', 'stop', 'restart', 'command', 'downlaod'.")
