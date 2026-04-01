import discord
import os
from count_feature import handle_count, get_current_count

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1488457090304577627

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"已上線: {client.user}")
    print(f"目前數到: {get_current_count()}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    await handle_count(message, CHANNEL_ID)

if not TOKEN:
    raise ValueError("TOKEN 沒設")

client.run(TOKEN)