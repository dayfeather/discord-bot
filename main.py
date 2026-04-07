import os
import discord
from discord.ext import commands
from discord import app_commands
from count_feature import handle_count, get_current_count, set_current_count

from birthday_utils import (
    is_valid_birthday,
    register_birthday,
    get_birthday,
    delete_birthday,
    get_all_birthdays,
)

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1488457090304577627
BIRTHDAY_CHANNEL_ID = 1483251598108004433
# 你的伺服器 ID，這個要換成你自己的
GUILD_ID = 1382824039847956510

intents = discord.Intents.default()
intents.message_content = True


class MyClient(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)  # ⭐這行就是你缺的

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


client = MyClient(intents=intents)


@client.event
async def on_ready():
    print(f"已上線: {client.user}")
    print(f"目前數到: {get_current_count()}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    await handle_count(message, CHANNEL_ID)


@client.tree.command(name="目前")
async def current_count(interaction: discord.Interaction):
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message("這個指令只能在數數頻道用。", ephemeral=True)
        return

    await interaction.response.send_message(f"現在數到 {get_current_count()}")


@client.tree.command(name="設定數字", description="管理員設定目前數到幾")
@app_commands.describe(value="要設定成多少")
@app_commands.default_permissions(manage_guild=True)
async def set_count(interaction: discord.Interaction, value: int):
    if interaction.guild is None:
        await interaction.response.send_message("這個指令只能在伺服器內使用。", ephemeral=True)
        return

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("你沒有權限使用這個指令。", ephemeral=True)
        return

    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message("這個指令只能在數數頻道用。", ephemeral=True)
        return

    if value < 0:
        await interaction.response.send_message("不能設定成負數。", ephemeral=True)
        return

    set_current_count(value)
    await interaction.response.send_message(f"已將目前數字設定為 {value}")
@client.tree.command(name="生日登記", description="登記你的生日")
@app_commands.describe(月="生日月份", 日="生日日期")
async def birthday_register(interaction: discord.Interaction, 月: int, 日: int):
    if interaction.channel_id != BIRTHDAY_CHANNEL_ID:
        await interaction.response.send_message(
            "這個指令只能在生日登記頻道用。",
            ephemeral=True
        )
        return

    if not is_valid_birthday(月, 日):
        await interaction.response.send_message(
            "生日格式不合法，請重新輸入。",
            ephemeral=True
        )
        return

    register_birthday(interaction.user.id, interaction.user.display_name, 月, 日)

    await interaction.response.send_message(
        f"登記成功，你的生日是 {月}/{日} 🎂"
    )


@client.tree.command(name="我的生日", description="查看自己登記的生日")
async def my_birthday(interaction: discord.Interaction):
    info = get_birthday(interaction.user.id)

    if not info:
        await interaction.response.send_message(
            "你還沒有登記生日。",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"你登記的生日是 {info['month']}/{info['day']} 🎉",
        ephemeral=True
    )


@client.tree.command(name="刪除生日", description="刪除自己登記的生日")
async def remove_birthday(interaction: discord.Interaction):
    if interaction.channel_id != BIRTHDAY_CHANNEL_ID:
        await interaction.response.send_message(
            "這個指令只能在生日登記頻道用。",
            ephemeral=True
        )
        return

    ok = delete_birthday(interaction.user.id)

    if not ok:
        await interaction.response.send_message(
            "你還沒有登記生日。",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "你的生日資料已刪除。",
        ephemeral=True
    )


@client.tree.command(name="生日列表", description="查看全部已登記的生日")
async def birthday_list(interaction: discord.Interaction):
    if interaction.channel_id != BIRTHDAY_CHANNEL_ID:
        await interaction.response.send_message(
            "這個指令只能在生日登記頻道用。",
            ephemeral=True
        )
        return

    data = get_all_birthdays()

    if not data:
        await interaction.response.send_message(
            "目前還沒有人登記生日。",
            ephemeral=True
        )
        return

    lines = []
    for _, info in data.items():
        lines.append(f"{info['name']}：{info['month']}/{info['day']}")

    await interaction.response.send_message("\n".join(lines))   

if not TOKEN:
    raise ValueError("TOKEN 沒設")

client.run(TOKEN)