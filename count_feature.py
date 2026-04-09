import json
import os
import asyncio
import time
DATA_DIR = "/data"
DATA_FILE = os.path.join(DATA_DIR, "count.json")

os.makedirs(DATA_DIR, exist_ok=True)

count_lock = asyncio.Lock()


def load_count():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "last_user" not in data:
                data["last_user"] = None
            if "last_time" not in data:
                data["last_time"] = 0
            return data
    return {"count": 0, "last_user": None, "last_time": 0}

def save_count(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


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
    now = time.time()

    async with count_lock:
        expected = data["count"] + 1
        last_user = data.get("last_user")
        last_time = data.get("last_time", 0)

        print(
            f"[handle_count] file={DATA_FILE}, msg={content}, user_id={user_id}, "
            f"last_user={last_user}, expected={expected}, last_time={last_time}, data={data}"
        )

        # 同一個人連續數：不重製，只擋掉
        if last_user == user_id:
            await message.add_reaction("❌")
            await message.channel.send("不能連續數！換別人 👊")
            return

        # 正確數字
        if number == expected:
            data["count"] = number
            data["last_user"] = user_id
            data["last_time"] = now
            save_count(data)
            print(f"[success] data={data}")

            await message.add_reaction("✅")
            return

        # 30 秒內重複上一個已成功的數字：算慢一步，不重製
        if number == data["count"] and (now - last_time <= 30):
            await message.add_reaction("⚠️")
            await message.channel.send("慢了一步 😆")
            return

        # 其他錯誤才重製
        data["count"] = 0
        data["last_user"] = None
        data["last_time"] = 0
        save_count(data)
        print(f"[fail_reset] data={data}")

        await message.add_reaction("❌")
        await message.channel.send("敢數錯?咬爆你喔 <a:emoji_R4:1408487451424587897>")


async def handle_count_status(message, channel_id):
    if message.channel.id != channel_id:
        return False

    content = message.content.strip()

    if content == "!目前":
        await message.channel.send(f"現在數到 {data['count']}")
        return True

    return False


def set_current_count(value: int):
    global data
    data["count"] = value
    data["last_user"] = None
    save_count(data)