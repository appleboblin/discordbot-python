import asyncio
from ollama import AsyncClient

async def chat():
  message = {'role': 'user', 'content': 'Why is the sky blue?'}
  response = await AsyncClient(host='http://192.168.2.100:11434').chat(model='llama2:7b', messages=[message], stream=False)
  print(response['message']['content'])

asyncio.run(chat())