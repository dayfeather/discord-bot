import json
import os
import asyncio

DATA_FILE = "count.json"
count_lock = asyncio.Lock()

def load_count():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"count": 0, "last_user": None}

    if "last_user" not in data:
        data["last_user"] = None

    save_count(data)
    print(f"[load_count] data={data}")
    return data

def save_count(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

data = load_count()

def get_current_count():
    return data["count"]

async def handle_count(message, channel_id):
    global data

    if message.channel.id != channel_id:
        return

    content = message.content.strip()

    if not content.isdigit():
        return

    number = int(content)
    user_id = message.author.id

    async with count_lock:
        expected = data["count"] + 1
        last_user = data.get("last_user")

        print(
            f"[handle_count] msg={content}, user_id={user_id}, "
            f"last_user={last_user}, expected={expected}, data={data}"
        )

        if last_user == user_id:
            await message.add_reaction("❌")
            await message.channel.send("不能連續數！重來 👊")
            return

        if number == expected:
            data["count"] = number
            data["last_user"] = user_id
            save_count(data)
            print(f"[success] data={data}")

            await message.add_reaction("✅")
            await message.channel.send("你好棒👍數對了")
        else:
            data["count"] = 0
            data["last_user"] = None
            save_count(data)
            print(f"[fail_reset] data={data}")

            await message.add_reaction("❌")
            await message.channel.send("敢數錯?咬爆你喔 <a:emoji_R4:1408487451424587897>")
def get_current_count():
    return data["count"]

async def handle_count_status(message, channel_id):
    if message.channel.id != channel_id:
        return False

    content = message.content.strip()

    if content == "!目前":
        await message.channel.send(f"現在數到 {data['count']}")
        return True

    return False