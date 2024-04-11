import settings
# Default lib
import urllib3
import os
import base64

# Extra Libs
import pyvips
import discord
from discord.ext import commands
from ollama import AsyncClient
import ollama


def main():
    client = AsyncClient(host=settings.LLM_ADDRESS)

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user} (ID: {bot.user.id})")

    @bot.command(
        aliases = [ 'p' ],
        help = "This is help",
        description = "This is description", 
        brief = "This is brief",
        enabled = True,
        hidden = True
    )
    async def ping(ctx):
        """ Answers with pong"""
        await ctx.send("pong")

    # @bot.command()
    # async def say(ctx, what = "Huh?"):
    #     await ctx.send(what)

    @bot.command()
    async def add(ctx, one : int, two : int):
        await ctx.send(one + two)

    @bot.command(
        aliases = [ 'c' ],
        help = "Send a prompt to LLM",
        description = "Sends a user entered prompt to a LLM", 
        enabled = True,
        hidden = False
    )
    async def chat(ctx, *args):
        message = {'role': 'user', 'content': f'{" ".join(args[:])}'}
        response = await client.chat(model='discord-bot:latest', messages=[message], stream=False)
        await ctx.send(response['message']['content'])

    @bot.command(
        aliases = [ 'i' ],
        help = "Send a prompt and image to LLM",
        description = "Sends a user entered prompt and attached to a LLM", 
        enabled = True,
        hidden = False
    )
    async def img(ctx, *args):
        url = ctx.message.attachments[0].url
        # Get image
        res = urllib3.request('GET', url)
        file_name = url.split("/")[-1]
        #save img
        with open(file_name,'wb') as f:
            f.write(res.data)
        # rename and delete old img
        msgID = ctx.message.id
        image = pyvips.Image.new_from_file(file_name, access="sequential")
        image.write_to_file(f'{msgID}.jpg')
        os.remove(file_name)
        # send image to ollama to process
        image_path = f'{msgID}.jpg'
        message = {'role': 'user', 'content': f'{" ".join(args[:])}', 'images': [image_path] }
        response = await client.chat(model='llava', messages=[message], stream=False)
        os.remove(image_path)
        await ctx.send(response['message']['content'])

    bot.run(settings.DISCORD_API_TOKEN, root_logger=True)

if __name__ == "__main__":
    logger = settings.logging.getLogger("bot")
    main()