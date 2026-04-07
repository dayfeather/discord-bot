import os
import discord
from discord.ext import tasks
from datetime import datetime, time
from zoneinfo import ZoneInfo
from discord import app_commands
from count_feature import handle_count, get_current_count, set_current_count

from birthday_utils import (
    is_valid_birthday,
    register_birthday,
    get_birthday,
    delete_birthday,
    get_all_birthdays,
    get_today_birthdays,
    already_announced_today,
    mark_announced_today,
)

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1488457090304577627
BIRTHDAY_CHANNEL_ID = 1483251598108004433
BIRTHDAY_ANNOUNCE_CHANNEL_ID = 1416757980673736734
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

@tasks.loop(time=time(hour=14, minute=25, tzinfo=ZoneInfo("Asia/Taipei")))
async def birthday_check_loop():
    print("birthday_check_loop triggered")

    # if already_announced_today():
    #     print("今天已經公告過了")
    #     return

    today_birthdays = get_today_birthdays()
    if not today_birthdays:
        print("今天沒有人生日")
        mark_announced_today()
        return

    channel = client.get_channel(BIRTHDAY_ANNOUNCE_CHANNEL_ID)
    if channel is None:
        print("找不到生日公告頻道")
        return

    mentions = " ".join([f"<@{info['user_id']}>" for info in today_birthdays])

    embed = discord.Embed(
        title="🎉 生日快樂！",
        color=0xFF69B4
    )
    embed.set_image(url="https://media.giphy.com/media/g5R9dok94mrIvplmZd/giphy.gif")

    await channel.send(content=mentions, embed=embed)
    print("生日公告已送出")
    mark_announced_today()

@birthday_check_loop.before_loop
async def before_birthday_check_loop():
    await client.wait_until_ready()
    print("birthday_check_loop ready")

@client.event
async def on_ready():
    print(f"已上線: {client.user}")
    print(f"目前數到: {get_current_count()}")

    if not birthday_check_loop.is_running():
        birthday_check_loop.start()

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

@client.tree.command(name="測試生日", description="手動測試生日公告")
async def test_birthday(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # ⭐ 先回應（關鍵）

    today_birthdays = get_today_birthdays()

    if not today_birthdays:
        await interaction.followup.send("今天沒有人生日", ephemeral=True)
        return

    channel = client.get_channel(BIRTHDAY_ANNOUNCE_CHANNEL_ID)
    if channel is None:
        await interaction.followup.send("找不到公告頻道", ephemeral=True)
        return

    mentions = [f"<@{info['user_id']}>" for info in today_birthdays]

    msg = "【測試】今天生日的是：\n" + " ".join(mentions)
    await channel.send(msg)

    await interaction.followup.send("已送出測試訊息", ephemeral=True)

if not TOKEN:
    raise ValueError("TOKEN 沒設")

client.run(TOKEN)