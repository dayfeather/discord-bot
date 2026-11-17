"""Keep temporary Discord startup failures from causing a restart loop."""

import logging
import math
import os
import random
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import discord

log = logging.getLogger(__name__)


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
    delay = min(max(int(os.environ.get("DISCORD_STARTUP_BACKOFF", "300")), 300), 1800)
    while True:
        try:
            client.run(token)
            return
        except discord.HTTPException as error:
            if error.status != 429 and not 500 <= error.status < 600:
                raise
            wait = max(delay, retry_after_seconds(error)) + random.uniform(0, 30)
            # Do not log the exception body: Cloudflare returns a full HTML page.
            log.warning("Discord 暫時無法登入（HTTP %s），等待 %.0f 秒後重試。", error.status, wait)
            time.sleep(wait)
            # clear() does not reset discord.py's closed aiohttp connector.
            # Replace this process after the cooldown to rebuild all network state.
            os.environ["DISCORD_STARTUP_BACKOFF"] = str(min(delay * 2, 1800))
            os.execv(sys.executable, [sys.executable, *sys.argv])
            return
