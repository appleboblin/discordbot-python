# Standard Library
import urllib3
import os

# Third Party

# Application Specific
import settings

import pyvips
import discord
from discord.ext import commands
from ollama import AsyncClient
import ollama

# Initialize logger from settings
logger = settings.logging.getLogger("bot")

class _LLMHandler:
    """
    A private handler class that manages interaction with a language model
    """

    def __init__(self, llm_address):
        """
        Initialize handler with specific address for the language model API call.

        Attributes:
            _client (AsyncClient): Client for interacting with Ollama.

        Args:
            llm_address (str): The address of the language model server
        """
        self._client = AsyncClient(host=llm_address)

    async def send_prompt(self, prompt):
        """
        Send a text promp to the language model and return the response.

        Args:
            prompt (str): Text promp to send to the language model.

        Returns:
            str: Response content from the language model.
        """
        message = {'role': 'user', 'content': prompt}
        response = await self._client.chat(model='discord-bot:latest', messages=[message], stream=False)
        return response['message']['content']

    async def process_image_and_send_prompt(self, url, prompt, msg_id):
        """
        Download attached image, process it and send to the language model with text prompt,
        and return the response.

        Args:
            url (str): URL of the image attachment.
            prompt (str): Text prompt to send to the language model.
            msg_id (str): Discord message ID for unique filename.

        Returns:
            str: Response content from the language model after processing the image.
        """
        # Process URL
        http = urllib3.PoolManager()
        res = http.request('GET', url)
        file_name = url.split("/")[-1]

        # Save image
        with open(file_name, 'wb') as f:
            f.write(res.data)

        # Convert image to JPG
        image = pyvips.Image.new_from_file(file_name, access="sequential")
        image_path = f'{msg_id}.jpg'
        image.write_to_file(image_path)
        os.remove(file_name)

        # Send image and prompt to LLM
        message = {'role': 'user', 'content': prompt, 'images': [image_path]}
        response = await self._client.chat(model='llava:13b', messages=[message], stream=False)
        os.remove(image_path)

class DiscordBot:
    """
    Main class of the Discord bot containing commands.
    """
    def __init__(self):
        """
        Initialize the Discord bot with settings.

        Attributes:
            _bot (command.Bot): Command handling bot object.
            _llm_handler (_LLMHandler): Handler for language model interactions.
        """
        # Set permission to interact with discord messages.
        intents = discord.Intents.default()
        intents.message_content = True
        # Set prefix and give permission
        self._prefix = "$"
        self._bot = commands.Bot(command_prefix=self._prefix, intents=intents)
        # LLM
        self._llm_handler = _LLMHandler(settings.LLM_ADDRESS)

        # Listen to events and command
        self._register_events()
        self._register_commands()

    def _register_events(self):
        """
        Register bot events such as when the bot is online and set presence.
        """
        @self._bot.event
        async def on_ready():
            logger.info(f"User: {self._bot.user} (ID: {self._bot.user.id})")
            await self._bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f'{self._prefix}help'))

    def _register_commands(self):
        """
        Register commands called.
        """
        @self._bot.command(
            aliases = ['p'],
            help = "Sends pong",
            enabled = True,
            hidden = True
            )
        async def ping(ctx):
            """
            Respond with 'pong' to the "!ping' command.

            Args:
                ctx (Context): Message context.
            """
            logger.info(f"{ctx.author} ran the command !ping")
            await ctx.send("pong")

        @self._bot.command(
            help = "Adds two number together",
            enabled = True,
            hidden = False
        )
        async def add(ctx, one: int, two: int):
            """
            Adds two numbers provided and send the result.

            Args:
                ctx (Context): Message context.
                one (int): First number.
                two (int): Second number.

            Return:
                None: Output added number to the chat
            """
            logger.info(f"{ctx.author} ran the command !add")
            await ctx.send(one + two)

        @self._bot.command(
            aliases=['c'],
            help = "Sends a text prompt to LLM",
            description = "Sends a user entered text promp to LLM",
            enabled = True,
            hidden = False
            )
        async def chat(ctx, *args):
            """
            Takes user text input and sends to the langeage model and response
            with model output.

            Args:
                ctx (Context): Message context.
                args (str): String of user entered prompt.
                            Is there a better way of getting text entered?

            Return:
                None: Output response to chat.
            """
            prompt = ' '.join(args)
            logger.info(f"{ctx.author} ran the command !chat with input {prompt}")
            response = await self._llm_handler.send_prompt(prompt)
            await ctx.send(response)

        @self._bot.command(
            aliases=['i'],
            help = "Sends a text prompt and image to LLM",
            description = "Sends a user entered text promp and attached image file to LLM",
            enabled = True,
            hidden = False
            )
        async def img(ctx, *args):
            """
            Sends image URL and text prompt to the language model and response with output.

            Args:
                ctx (Context): Message context.
                args (str): String of user entered prompt.
                attachment (image): Image to process.

            Return:
                None: Output response to chat.
            """
            prompt = ' '.join(args)
            logger.info(f"{ctx.author} ran the command !img with input {prompt}")
            # Get attachment url, if no url, return error.
            if ctx.message.attachments:
                url = ctx.message.attachments[0].url
                response = await self._llm_handler.process_image_and_send_prompt(url, prompt, ctx.message.id)
                await ctx.send(response)
            else:
                await ctx.send("Please attach an image.")

    def run(self):
        """
        Run Discord bot using token from settings.
        """
        self._bot.run(settings.DISCORD_API_TOKEN, root_logger=True)

def main():
    bot = DiscordBot()
    bot.run()

if __name__ == "__main__":
    main()
