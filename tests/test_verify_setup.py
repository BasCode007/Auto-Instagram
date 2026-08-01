"""Tests for scripts/verify_setup.sh.

These stay offline: every case here exits before the script makes a network
call, so the suite never depends on live API credentials.
"""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "verify_setup.sh"

# A minimal environment: no API keys, so the script stops after the env section.
# AUTO_IG_SKIP_DOTENV keeps results identical whether or not the machine running
# the tests happens to have a populated .env in the repo root.
BASE_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "NO_COLOR": "1",
    "AUTO_IG_SKIP_DOTENV": "1",
}


def run(*args, env_extra=None):
    env = dict(BASE_ENV)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


class VerifySetupTests(unittest.TestCase):
    def test_script_exists_and_is_executable(self):
        self.assertTrue(SCRIPT.exists(), f"missing {SCRIPT}")
        self.assertTrue(os.access(SCRIPT, os.X_OK), "verify_setup.sh not executable")

    def test_syntax_is_valid(self):
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_exits_zero_and_describes_usage(self):
        result = run("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("preflight", result.stdout.lower())
        self.assertIn("--skip-network", result.stdout)
        # The help text is the leading comment block; it must not leak code.
        self.assertNotIn("set -uo pipefail", result.stdout)

    def test_unknown_flag_is_rejected(self):
        result = run("--definitely-not-a-flag")
        self.assertEqual(result.returncode, 2)

    def test_missing_env_fails_before_any_network_call(self):
        result = run("--skip-network")
        self.assertEqual(result.returncode, 1)
        self.assertIn("OPENAI_API_KEY is not set", result.stdout)
        self.assertIn("IG_ACCESS_TOKEN is not set", result.stdout)
        # Should stop at the env stage rather than reporting service results.
        self.assertNotIn("publishing permission confirmed", result.stdout)

    def test_names_the_uploader_specific_variables(self):
        cloudinary = run("--skip-network")
        self.assertIn("CLOUDINARY_UPLOAD_PRESET is not set", cloudinary.stdout)

        copy_mode = run("--skip-network", env_extra={"UPLOADER": "copy"})
        self.assertIn("PUBLIC_BASE_URL is not set", copy_mode.stdout)
        self.assertNotIn("CLOUDINARY_UPLOAD_PRESET", copy_mode.stdout)

    def test_unknown_uploader_is_reported(self):
        result = run("--skip-network", env_extra={"UPLOADER": "carrier-pigeon"})
        self.assertIn("carrier-pigeon", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_warns_about_localhost_webhook_url(self):
        result = run(
            "--skip-network", env_extra={"WEBHOOK_URL": "http://localhost:5678"}
        )
        self.assertIn("WEBHOOK_URL", result.stdout)
        self.assertIn("call back", result.stdout)

    def test_warns_about_placeholder_encryption_key(self):
        result = run(
            "--skip-network",
            env_extra={"N8N_ENCRYPTION_KEY": "change-me-to-a-long-random-string"},
        )
        self.assertIn("N8N_ENCRYPTION_KEY", result.stdout)
        self.assertIn("placeholder", result.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
