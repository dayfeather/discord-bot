"""Keep temporary Discord startup failures from causing a restart loop."""

import logging
import math
import random
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
    delay = 300
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
            # run() closes the client and its event loop, including background tasks.
            client.clear()
            delay = min(delay * 2, 1800)
