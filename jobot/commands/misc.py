import logging
from discord.ext import commands
import discord
import os

# Initialize logger
logger = logging.getLogger("bot")

def get_unique_filename(base_name: str, extension: str) -> str:
    """
    Returns a unique file name by checking if the file already exists and incrementing the number if necessary.
    Args:
        base_name (str): The base name of the file.
        extension (str): The file extension (e.g., '.txt').
    Returns:
        str: A unique file name with an incremented number if the file already exists.
    """
    file_name = f"{base_name}{extension}"
    counter = 1

    # Check if the file exists and increment the number if it does
    while os.path.exists(file_name):
        file_name = f"{base_name}_{counter}{extension}"
        counter += 1

    return file_name

def misc_commands(bot):
    """
    Misc commands
    """
    @bot.command(
        aliases = ['p'],
        help = "Sends pong",
        enabled = True,
        hidden = True
        )
    async def ping(ctx):
        """
        Respond with 'pong' to the "ping' command.

        Args:
            ctx (Context): Message context.
        """
        logger.info(f"{ctx.author} used ping command")
        await ctx.send("pong")

    @bot.command(
        help = "Adds two number together",
        enabled = True,
        hidden = False
    )
    async def add(ctx,
                one: str = commands.parameter(default="0", description="First number"),
                two: str = commands.parameter(default="0", description="Second number")):
        """
        Adds two numbers provided and send the result.

        Args:
            ctx (Context): Message context.
            one (int): First number.
            two (int): Second number.

        Return:
            None: Output added number to the chat.
        """
        logger.info(f"{ctx.author} used add command")
        # Check if entered are numbers
        try:
            one = float(one)
            two = float(two)
        except ValueError:
            await ctx.send("Please enter valid integers.")
            return
        # Convert floats to integers if they have no fractional part
        one = int(one) if one.is_integer() else one
        two = int(two) if two.is_integer() else two
        await ctx.send(one + two)

    @bot.command(
        aliases=['s'],
        help="Scrape all message history of a user on the server and output to a .txt file",
        enabled=True,
        hidden=True
    )
    async def scrape(ctx, member: discord.Member):
        """
        Scrape all message history of a user across all text channels in the server and save to a .txt file.

        Args:
            ctx (Context): Message context.
            member (discord.Member): The member whose message history you want to scrape.
        """
        logger.info(f"{ctx.author} used scrape command for {member}")
        
        # Prepare the base file name
        base_name = f"{member.name}_history"
        
        # Get a unique file name with the extension .txt
        file_name = get_unique_filename(base_name, ".txt")
        
        # Open the file for writing (in append mode) with utf-8 encoding to handle Japanese characters
        with open(file_name, 'a', encoding='utf-8') as file:
            # Filter for only text channels
            text_channels = [channel for channel in ctx.guild.channels if isinstance(channel, discord.TextChannel)]

            # Loop through each text channel
            for channel in text_channels:
                async for message in channel.history(limit=100):
                    if message.author == member and message.content.strip():
                        # Write each message directly to the file with support for Japanese characters
                        # file.write(f"[{message.created_at}] #{channel.name}: {message.content}\n")
                        file.write(f"{message.content}\n")

        # Send a confirmation message if no messages were written
        if os.stat(file_name).st_size == 0:
            await ctx.send(f"No messages found for {member.mention}.")
            os.remove(file_name)  # Delete empty file
            return

        # Send the file in Discord
        await ctx.send(f"Scraped messages of {member.mention} have been saved to `{file_name}`.")
        await ctx.send(file=discord.File(file_name))

    @bot.command(
        help="Write the message after the command to a text file.",
        enabled=True
    )
    async def writefile(ctx, *, content: str):
        """
        Write the content after the command to a text file, handling Japanese characters.

        Args:
            ctx (Context): The context of the message.
            content (str): The content to write to the file.
        """
        logger.info(f"{ctx.author} used writefile command with content: {content}")
        
        # Prepare file path
        file_name = f"{ctx.author.name}_input.txt"
        
        # Write the content to the file with utf-8 encoding to handle Japanese characters
        with open(file_name, 'a', encoding='utf-8') as file:
            file.write(f"{content}\n")

        # Send confirmation
        await ctx.send(f"Your content has been written to `{file_name}`.")

        # Send the file in Discord (optional, remove if not needed)
        await ctx.send(file=discord.File(file_name))

    @bot.command(
        aliases=['sc'],
        help="Scrape all messages from the current channel and save them to a .txt file in chronological order",
        enabled=True,
        hidden=True
    )
    async def scrape_channel(ctx):
        """
        Scrape all message history of the channel where the command is invoked, and save to a .txt file in chronological order (oldest first).

        Args:
            ctx (Context): Message context.
        """
        channel = ctx.channel
        logger.info(f"{ctx.author} used scrape command in {channel.name}")

        # Create a base name that includes both the server name and the channel name
        server_name = ctx.guild.name.replace(" ", "_")  # Replace spaces with underscores for file safety
        channel_name = channel.name.replace(" ", "_")
        base_name = f"{server_name}_{channel_name}_history"

        # Generate a unique filename
        file_name = get_unique_filename(base_name, ".txt")

        # Create/open the file for writing with utf-8 encoding
        with open(file_name, 'w', encoding='utf-8') as file:
            # List to store messages
            messages = []

            # Scrape messages (oldest to newest)
            async for message in channel.history(limit=None, oldest_first=True):
                if message.content.strip():  # Only save non-empty messages
                    messages.append(f"[{message.created_at}] {message.author}: {message.content}")

            # If there are no messages, notify the user
            if not messages:
                await ctx.send(f"No messages found in {channel.mention}.")
                return

            # Write the messages in order to the file (oldest first)
            file.write('\n'.join(messages))

        # Send a confirmation message
        await ctx.send(f"Messages from {channel.mention} have been saved to `{file_name}`.")

        # Send the file in Discord
        await ctx.send(file=discord.File(file_name))
