import logging
from discord.ext import commands

# Initialize logger
logger = logging.getLogger("bot")

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
