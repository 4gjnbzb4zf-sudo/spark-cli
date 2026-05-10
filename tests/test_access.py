from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from spark_cli.cli import build_parser, cmd_access


class AccessSetupTests(unittest.TestCase):
    def run_access(self, *argv: str, spark_home: Path) -> tuple[int, dict[str, object]]:
        args = build_parser().parse_args(["access", *argv, "--json"])
        stdout = StringIO()
        with patch.dict(os.environ, {"SPARK_HOME": str(spark_home)}, clear=False), \
             patch("spark_cli.sandbox.access.docker_available", return_value=False), \
             patch("spark_cli.sandbox.access.modal_sdk_available", return_value=False), \
             redirect_stdout(stdout):
            exit_code = cmd_access(args)
        return exit_code, json.loads(stdout.getvalue())

    def test_access_setup_creates_level4_workspace_without_docker_or_ssh(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spark_home = Path(tmpdir) / "spark-home"
            exit_code, payload = self.run_access("setup", spark_home=spark_home)

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["access_level"], 4)
            self.assertEqual(payload["recommended"]["id"], "spark_workspace")
            self.assertEqual(payload["recommended"]["setup_mode"], "automatic")
            self.assertTrue(Path(str(payload["workspace_path"])).exists())

    def test_access_status_keeps_level5_blocked_without_high_agency_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {"SPARK_ALLOW_HIGH_AGENCY_WORKERS": ""}, clear=False):
            exit_code, payload = self.run_access("status", "--level", "5", spark_home=Path(tmpdir) / "spark-home")

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["recommended"]["id"], "spark_workspace")
        self.assertEqual(payload["lanes"][0]["id"], "level5_operator")
        self.assertEqual(payload["lanes"][0]["setup_mode"], "blocked")

    def test_access_setup_can_recommend_docker_when_requested_and_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            args = build_parser().parse_args(["access", "setup", "--with", "docker", "--json"])
            stdout = StringIO()
            with patch.dict(os.environ, {"SPARK_HOME": str(Path(tmpdir) / "spark-home")}, clear=False), \
                 patch("spark_cli.sandbox.access.docker_available", return_value=True), \
                 patch("spark_cli.sandbox.access.modal_sdk_available", return_value=False), \
                 redirect_stdout(stdout):
                exit_code = cmd_access(args)
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["recommended"]["id"], "docker")
        self.assertEqual(payload["recommended"]["setup_mode"], "automatic")


if __name__ == "__main__":
    unittest.main()
