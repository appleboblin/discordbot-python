# main.py
import discord
from discord.ext import commands
import settings
from jobot.commands.llm import llm_commands
from jobot.commands.misc import misc_commands
from jobot.commands.minecraft import mc_commands

# Initialize logger
logger = settings.logging.getLogger("bot")

class DiscordBot:
    """
    Main class containing discord bot
    """
    def __init__(self):
        """
        Initialize the Discord bot with settings.

        Attributes:
            _bot (command.Bot): Command handling bot object.
        """
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        self._prefix = "$"
        self._bot = commands.Bot(command_prefix=self._prefix, intents=intents)
        self._register_events()
        self._register_commands()

    def _register_events(self):
        """Event logger"""
        @self._bot.event
        async def on_ready():
            logger.info(f"User: {self._bot.user} (ID: {self._bot.user.id})")
            await self._bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.playing, name=f'{self._prefix}help')
            )

    def _register_commands(self):
        """Register avaliable commands"""
        llm_commands(self._bot)
        misc_commands(self._bot)
        mc_commands(self._bot)

    def run(self, max_retries=30, delay=30):
        """
        Run Discord bot using token from settings, with retry on failure.

        Args:
            max_retries (int): Maximum number of retries before giving up.
            delay (int): Delay between retries in seconds.
        """
        attempt = 0
        while attempt < max_retries:
            try:
                logger.info("Starting Discord bot...")
                self._bot.run(settings.DISCORD_API_TOKEN, root_logger=True)
            except discord.DiscordException as e:
                attempt += 1
                logger.error(f"Failed to connect to Discord (Attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Max retries reached. Exiting.")
                    break

def main():
    bot = DiscordBot()
    bot.run()

if __name__ == "__main__":
    main()
