bot_token = "MTAzODYyNzk5MDc4MDc4MDYwNA.GXlJI2.DWsev7Nllm_zYBFzNLNQwTWCEAZ4Bb7PxU3Kos"

import os

import discord
from dotenv import load_dotenv

load_dotenv()
# TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client(intents=None)

@client.event
async def on_ready():
    
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        print(f"Yooo, it's {guild.name}:{guild.id}")

client.run(bot_token)
