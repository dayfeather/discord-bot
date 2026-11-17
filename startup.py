"""Keep temporary Discord startup failures from causing a restart loop."""

import logging
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import discord

log = logging.getLogger(__name__)


def cooldown_path():
    return Path(os.environ.get("DISCORD_LOGIN_BACKOFF_FILE", "/data/login_backoff.json"))


def load_cooldown(path):
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 0, 300
    deadline = float(state["retry_at"])
    delay = int(state["next_delay"])
    if not math.isfinite(deadline) or deadline < 0 or not 300 <= delay <= 1800:
        raise ValueError("登入冷卻檔案格式錯誤；停止登入以避免忽略冷卻期限。")
    return deadline, delay


def save_cooldown(path, deadline, delay):
    # A write failure must stop startup rather than silently lose the deadline.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump({"retry_at": deadline, "next_delay": delay}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def retry_after_seconds(error):
    value = error.response.headers.get("Retry-After", "0")
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return 0
    return max(0, seconds) if math.isfinite(seconds) else 0


def run_with_backoff(client, token):
    """Retry only rate limits and server errors; invalid credentials still fail."""
    path = cooldown_path()
    deadline, persisted_delay = load_cooldown(path)
    # Bootstrap the first deployment from the previous version's logged deadline.
    initial_deadline = float(os.environ.get("DISCORD_INITIAL_RETRY_AT", "0"))
    if not math.isfinite(initial_deadline) or initial_deadline < 0:
        raise ValueError("初始登入冷卻期限格式錯誤。")
    if initial_deadline > deadline:
        deadline = initial_deadline
        save_cooldown(path, deadline, persisted_delay)
    delay = min(max(int(os.environ.get("DISCORD_STARTUP_BACKOFF", str(persisted_delay))), 300), 1800)
    remaining = deadline - time.time()
    if remaining > 0:
        log.warning("保留先前登入冷卻期限，等待 %.0f 秒後才連線 Discord。", remaining)
        time.sleep(remaining)
    while True:
        try:
            client.run(token)
            return
        except discord.HTTPException as error:
            if error.status != 429 and not 500 <= error.status < 600:
                raise
            wait = max(delay, retry_after_seconds(error)) + random.uniform(0, 30)
            deadline = time.time() + wait
            next_delay = min(delay * 2, 1800)
            save_cooldown(path, deadline, next_delay)
            # Do not log the exception body: Cloudflare returns a full HTML page.
            log.warning("Discord 暫時無法登入（HTTP %s），等待 %.0f 秒後重試。", error.status, wait)
            log.warning("登入冷卻截止（UTC）：%s；Retry-After=%r；CF-Ray=%r", datetime.fromtimestamp(deadline, timezone.utc).isoformat(), error.response.headers.get("Retry-After"), error.response.headers.get("CF-Ray"))
            time.sleep(wait)
            # clear() does not reset discord.py's closed aiohttp connector.
            # Replace this process after the cooldown to rebuild all network state.
            os.environ["DISCORD_STARTUP_BACKOFF"] = str(next_delay)
            os.execv(sys.executable, [sys.executable, *sys.argv])
            return
