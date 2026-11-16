import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import discord

from startup import run_with_backoff


def http_error(status, retry_after="0"):
    return discord.HTTPException(
        SimpleNamespace(status=status, reason="test", headers={"Retry-After": retry_after}),
        "test",
    )


class StartupTests(unittest.TestCase):
    @patch("startup.random.uniform", return_value=0)
    @patch("startup.time.sleep")
    def test_backoff_caps_and_reopens_client(self, sleep, jitter):
        client = Mock()
        client.run.side_effect = [http_error(429)] * 5 + [None]
        run_with_backoff(client, "test-token")
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [300, 600, 1200, 1800, 1800])
        self.assertEqual(client.clear.call_count, 5)

    @patch("startup.random.uniform", return_value=0)
    @patch("startup.time.sleep")
    def test_respects_retry_after_and_server_errors(self, sleep, jitter):
        client = Mock()
        client.run.side_effect = [http_error(429, "3600"), http_error(503, "invalid"), None]
        run_with_backoff(client, "test-token")
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [3600, 600])

    @patch("startup.time.sleep")
    def test_permanent_failures_are_not_retried(self, sleep):
        for error in [http_error(403), discord.LoginFailure("invalid")]:
            client = Mock()
            client.run.side_effect = error
            with self.assertRaises(type(error)):
                run_with_backoff(client, "test-token")
            client.clear.assert_not_called()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
