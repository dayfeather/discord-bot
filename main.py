import discord
import json
import os
import re
import asyncio

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1488457090304577627
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

DATA_FILE = "count.json"

# ------------------------
# 讀寫資料
# ------------------------
def load_count():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"count": 0}

def save_count(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

data = load_count()
count_lock = asyncio.Lock()
# ------------------------
# 安全算式解析
# ------------------------
def safe_eval(expr):
    if not re.match(r'^[0-9+\-*/ ()]+$', expr):
        return None
    try:
        return int(eval(expr))
    except:
        return None

# ------------------------
# Bot 上線
# ------------------------
@client.event
async def on_ready():
    print(f"已上線: {client.user}")
    print(f"目前數到: {data['count']}")

# ------------------------
# 收到訊息（唯一一個！）
# ------------------------
@client.event
async def on_message(message):
    global data

    if message.author.bot:
        return

    if message.channel.id != CHANNEL_ID:
        return

    content = message.content.strip()
    number = safe_eval(content)
    if number is None:
        return

    async with count_lock:
        expected = data["count"] + 1

        if number == expected:
            data["count"] = number
            save_count(data)
            await message.add_reaction("✅")
            await message.channel.send("你好棒👍數對了")

        else:
            data["count"] = 0
            save_count(data)
            await message.add_reaction("❌")
            await message.channel.send("敢數錯?咬爆你喔 <a:emoji_R4:1408487451424587897>")

# ------------------------
client.run(TOKEN)
# emoji_R4