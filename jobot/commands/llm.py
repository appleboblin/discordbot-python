# llm_commands.py
import settings
from ollama import AsyncClient
import discord
import os
import aiohttp
import aiofiles
import pyvips
import base64

# Initialize logger
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
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    # process url
                    file_name = url.split("/")[-1]
                    # save images
                    async with aiofiles.open(file_name, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            await f.write(chunk)

        # Convert image to JPG
        image = pyvips.Image.new_from_file(file_name, access="sequential")
        image_path = f'{msg_id}.jpg'
        image.write_to_file(image_path)
        os.remove(file_name)

        # Send image and prompt to LLM
        message = {'role': 'user', 'content': prompt, 'images': [image_path]}
        response = await self._client.chat(model='llava:13b', messages=[message], stream=False)
        os.remove(image_path)
        return response['message']['content']

    async def generate_image(self, prompt, msg_id):
        # Server url
        url = settings.IMG_ADDRESS + '/sdapi/v1/txt2img'

        # set image parameters
        payload = {
            "prompt": prompt,
            "negative_prompt": "",
            "sampler_index": "Euler a",
            "width": 512,
            "height": 512,
            "batch_size": 1,
            "steps": 20,
            "seed": -1,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        img_data = base64.b64decode(data['images'][0])
                        with open(f"{msg_id}.png", 'wb') as f:
                            f.write(img_data)
                        return "success"
                    except KeyError:
                        return "img-key-404"
                else:
                    return "no-valid-response"

def llm_commands(bot):
    """
    LLM commands
    """
    llm_handler = _LLMHandler(settings.LLM_ADDRESS)

    @bot.command(
        aliases=['c'],
        help = "Sends a text prompt to LLM",
        description = "Sends a user entered text promp to LLM",
        enabled = False,
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
        logger.info(f"{ctx.author} used chat command: {prompt}")
        response = await llm_handler.send_prompt(prompt)
        await ctx.send(response)

    @bot.command(
        aliases=['i'],
        help = "Sends a text prompt and image to LLM",
        description = "Sends a user entered text promp and attached image file to LLM",
        enabled = False,
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
        logger.info(f"{ctx.author} used img command: {prompt}")
        if ctx.message.attachments:
            url = ctx.message.attachments[0].url
            response = await llm_handler.process_image_and_send_prompt(url, prompt, ctx.message.id)
            await ctx.send(response)
        else:
            await ctx.send("Please attach an image.")

    @bot.command(
        aliases=['d'],
        help = "Generate image with text prompt",
        description = "Sends a user entered text promp to stable diffusion to generate an image",
        enabled = False,
        hidden = False
        )
    async def dream(ctx, *args):
        """
        Sends text prompt to stable diffusion server and response with output.

        Args:
            ctx (Context): Message context.
            args (str): String of user entered prompt.

        Return:
            None: Output response to chat.
        """
        prompt = ' '.join(args)
        logger.info(f"{ctx.author} used dream command: {prompt}")
        response = await llm_handler.generate_image(prompt, ctx.message.id)
        if response == "success":
            img_path = f'{ctx.message.id}.png'
            file = discord.File(img_path)
            await ctx.send(file=file, content="Your generated image")
            os.remove(img_path)
        else:
            await ctx.send("Failed to generate image.")
