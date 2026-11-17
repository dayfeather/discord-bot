import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import discord
from startup import run_with_backoff


def http_error(status, retry_after="0"):
    return discord.HTTPException(
        SimpleNamespace(status=status, reason="test", headers={"Retry-After": retry_after}), "test"
    )


class StartupTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch("startup.os.execv")
    @patch("startup.random.uniform", return_value=0)
    @patch("startup.time.sleep")
    def test_cooldown_then_process_replacement(self, sleep, jitter, execv):
        client = Mock()
        client.run.side_effect = http_error(429, "3600")
        run_with_backoff(client, "test-token")
        sleep.assert_called_once_with(3600)
        self.assertEqual(os.environ["DISCORD_STARTUP_BACKOFF"], "600")
        execv.assert_called_once_with(sys.executable, [sys.executable, *sys.argv])
        client.clear.assert_not_called()

    @patch("startup.os.execv")
    @patch("startup.random.uniform", return_value=0)
    @patch("startup.time.sleep")
    def test_backoff_growth_and_cap(self, sleep, jitter, execv):
        for previous, expected in [("600", "1200"), ("1200", "1800"), ("1800", "1800")]:
            with patch.dict(os.environ, {"DISCORD_STARTUP_BACKOFF": previous}):
                client = Mock()
                client.run.side_effect = http_error(503, "invalid")
                run_with_backoff(client, "test-token")
                self.assertEqual(os.environ["DISCORD_STARTUP_BACKOFF"], expected)
                self.assertEqual(sleep.call_args.args[0], int(previous))

    @patch("startup.time.sleep")
    def test_permanent_failures_are_not_retried(self, sleep):
        for error in [http_error(403), discord.LoginFailure("invalid")]:
            client = Mock()
            client.run.side_effect = error
            with self.assertRaises(type(error)):
                run_with_backoff(client, "test-token")
        sleep.assert_not_called()

    def test_real_process_replacement_reinitializes_runtime(self):
        source = '''
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch
import discord
from startup import run_with_backoff
if os.environ.get("DISCORD_STARTUP_BACKOFF") == "600":
    assert "old_client" not in globals()
    print("fresh runtime ready", flush=True)
    sys.exit(0)
class Client:
    def run(self, token):
        raise discord.HTTPException(SimpleNamespace(status=429, reason="test", headers={}), "test")
old_client = Client()
with patch("startup.time.sleep"), patch("startup.random.uniform", return_value=0):
    run_with_backoff(old_client, "test-token")
raise AssertionError("process was not replaced")
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "probe.py"
            script.write_text(source, encoding="utf-8")
            env = dict(os.environ)
            env.pop("DISCORD_STARTUP_BACKOFF", None)
            env["PYTHONPATH"] = str(Path(__file__).parent)
            result = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("fresh runtime ready", result.stdout)


if __name__ == "__main__":
    unittest.main()
