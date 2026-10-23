import os
import discord
import random
import asyncio
import json
from discord.ext import tasks ,commands
from datetime import datetime, time
from zoneinfo import ZoneInfo
from discord import app_commands
from gif_maker import make_birthday_gif
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

make_birthday_gif(
    "Q36mu2oLOX.jpg",
    "duck-dance.gif",
    "result.gif",
    gif_size=(420, 420),
    pos=(210, 140)
)

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1488457090304577627
BIRTHDAY_CHANNEL_ID = 1562358080304324718
BIRTHDAY_ANNOUNCE_CHANNEL_ID = 1382839237120102443
# 你的伺服器 ID，這個要換成你
GUILD_ID = 1382824039847956510
BIRTHDAY_LIST_STATE_FILE = "/data/birthday_list_messages.json"
birthday_list_lock = asyncio.Lock()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

class MyClient(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)  

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


client = MyClient(intents=intents)

@tasks.loop(time=time(hour=12, minute=0, tzinfo=ZoneInfo("Asia/Taipei")))
async def birthday_check_loop():
    print("birthday_check_loop triggered")

    if already_announced_today():
        print("今天已經公告過了")
        return

    today_birthdays = get_today_birthdays()
    if not today_birthdays:
        print("今天沒有人生日")
        mark_announced_today()
        return

    channel = client.get_channel(BIRTHDAY_ANNOUNCE_CHANNEL_ID)
    if channel is None:
        print("找不到生日公告頻道")
        return

    make_birthday_gif("Q36mu2oLOX.jpg", "duck-dance.gif", "result.gif")

    file = discord.File("result.gif", filename="result.gif")

    mentions = " ".join([f"<@{info['user_id']}>" for info in today_birthdays])

    embed = discord.Embed(
    title="🎉 生日快樂！",
    color=random.randint(0, 0xFFFFFF)
    )

    embed.set_image(url="attachment://result.gif")
    await channel.send(content=mentions, embed=embed, file=file)    
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
async def birthday_register(
    interaction: discord.Interaction,
    月: int,
    日: int
):
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

    await interaction.response.defer(ephemeral=True)

    register_birthday(
        interaction.user.id,
        interaction.user.display_name,
        月,
        日
    )

    try:
        await refresh_birthday_list(interaction.channel)
    except Exception as error:
        print(f"更新生日列表失敗：{error}")
        await interaction.edit_original_response(
            content=f"生日已儲存：{月}/{日}，但列表更新失敗，請通知管理員。"
        )
        return

    await interaction.edit_original_response(
        content=f"登記成功，你的生日是 {月}/{日} 🎂"
    )

    await asyncio.sleep(10)

    try:
        await interaction.delete_original_response()
    except discord.NotFound:
        pass
birthday_list_lock = asyncio.Lock()


def save_birthday_list_state(state):
    os.makedirs("/data", exist_ok=True)

    temporary_file = BIRTHDAY_LIST_STATE_FILE + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    os.replace(temporary_file, BIRTHDAY_LIST_STATE_FILE)


async def refresh_birthday_list(channel):

    async with birthday_list_lock:
        try:
            with open(
                BIRTHDAY_LIST_STATE_FILE, "r", encoding="utf-8"
            ) as f:
                state = json.load(f)
        except FileNotFoundError:
            state = {}

        channel_key = str(channel.id)
        old_ids = state.get(channel_key, [])

        data = get_all_birthdays()

        sorted_birthdays = sorted(
            data.values(),
            key=lambda info: (
                int(info["month"]),
                int(info["day"])
            )
        )

        pages = []
        text = "🎂 最新生日列表\n"

        for info in sorted_birthdays:
            month = int(info["month"])
            day = int(info["day"])
            name = discord.utils.escape_markdown(
                str(info["name"])
                .replace("\n", " ")
                .replace("\r", " ")
            )

            line = f"`{month:02d}/{day:02d}` ｜ {name}\n"

            if len(text) + len(line) > 1900:
                pages.append(text)
                text = ""

            text += line

        if not sorted_birthdays:
            text += "目前還沒有人登記生日。"

        if text:
            pages.append(text)

        # 先發送新版，成功後再刪除舊版
        new_ids = []

        # 同時記錄新舊訊息，途中失敗時仍能在下次清理
        for page in pages:
            message = await channel.send(
                page,
                allowed_mentions=discord.AllowedMentions.none()
            )

            new_ids.append(message.id)
            state[channel_key] = old_ids + new_ids
            save_birthday_list_state(state)

        remaining_old_ids = list(old_ids)

        for message_id in old_ids:
            try:
                message = await channel.fetch_message(int(message_id))
                await message.delete()
            except discord.NotFound:
                pass

            remaining_old_ids.remove(message_id)
            state[channel_key] = remaining_old_ids + new_ids
            save_birthday_list_state(state)
        
@client.tree.command(name="幫人登記生日", description="管理員替成員登記或修改生日")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    成員="要登記生日的成員",
    月="生日月份",
    日="生日日期"
)
async def register_member_birthday(
    interaction: discord.Interaction,
    成員: discord.Member,
    月: int,
    日: int
):
    if interaction.channel_id != BIRTHDAY_CHANNEL_ID:
        await interaction.response.send_message(
            "這個指令只能在生日登記頻道用。",
            ephemeral=True
        )
        return

    if 成員.bot:
        await interaction.response.send_message(
            "不能替機器人登記生日。",
            ephemeral=True
        )
        return

    if not is_valid_birthday(月, 日):
        await interaction.response.send_message(
            "生日格式不合法，請重新輸入。",
            ephemeral=True
        )
        return

    register_birthday(
        成員.id,
        成員.display_name,
        月,
        日
    )

    await interaction.response.send_message(
        f"已替 {成員.mention} 登記生日：{月}/{日} 🎂",
        allowed_mentions=discord.AllowedMentions.none()
    )


@register_member_birthday.error
async def register_member_birthday_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "只有管理員可以替其他成員登記生日。",
            ephemeral=True
        )
        return

    raise error
    
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

    # 先依月份排序，同月份再依日期排序
    sorted_birthdays = sorted(
        data.values(),
        key=lambda info: (int(info["month"]), int(info["day"]))
    )

    pages = []
    text = "🎂 生日列表\n"

    for info in sorted_birthdays:
        month = int(info["month"])
        day = int(info["day"])
        name = discord.utils.escape_markdown(
            str(info["name"]).replace("\n", " ").replace("\r", " ")
        )

        line = f"`{month:02d}/{day:02d}` ｜ {name}\n"

        # 過長時分成多則訊息
        if len(text) + len(line) > 1900:
            pages.append(text)
            text = ""

        text += line

    if text:
        pages.append(text)

    await interaction.response.send_message(
        pages[0],
        allowed_mentions=discord.AllowedMentions.none()
    )

    for page in pages[1:]:
        await interaction.followup.send(
            page,
            allowed_mentions=discord.AllowedMentions.none()
        )

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

@bot.command()
async def dump(ctx):
    if ctx.author.id != 666918563856121886:
        return

    import os

    files = ["/data/count.json", "/data/birthdays.json", "/data/birthday_state.json"]

    for file in files:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                data = f.read()

            await ctx.author.send(f"{file}:\n```json\n{data[:1900]}\n```")
        else:
            await ctx.author.send(f"{file} 不存在")

if not TOKEN:
    raise ValueError("TOKEN 沒設")

@client.event
async def on_member_remove(member: discord.Member):
    # 只處理你的伺服器
    if member.guild.id != GUILD_ID:
        return

    deleted = delete_birthday(member.id)

    if deleted:
        print(f"成員離開，已刪除生日：{member.display_name}")
        
client.run(TOKEN)
