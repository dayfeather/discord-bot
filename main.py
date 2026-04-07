import os
import discord
from discord import app_commands
from count_feature import handle_count, get_current_count

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1488457090304577627

# 你的伺服器 ID，這個要換成你自己的
GUILD_ID = 1382824039847956510

intents = discord.Intents.default()
intents.message_content = True


class MyClient(discord.Client):
    async def setup_hook(self):
        # 只同步到這個 guild，測試最快
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


client = MyClient(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    print(f"已上線: {client.user}")
    print(f"目前數到: {get_current_count()}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    await handle_count(message, CHANNEL_ID)


@tree.command(name="目前", description="查看現在數到幾")
async def current_count(interaction: discord.Interaction):
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message("這個指令只能在數數頻道用。", ephemeral=True)
        return

    await interaction.response.send_message(f"現在數到 {get_current_count()}")


if not TOKEN:
    raise ValueError("TOKEN 沒設")

client.run(TOKEN)