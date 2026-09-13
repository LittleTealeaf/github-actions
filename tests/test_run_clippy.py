#!/usr/bin/env python3
"""Unit tests for cargo-clippy/run_clippy.py."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

RUN_CLIPPY_PATH = Path(__file__).resolve().parent.parent / "cargo-clippy" / "run_clippy.py"


class TestRunClippy(unittest.TestCase):
    """Tests for run_clippy.py execution."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.sarif_file = self.work_dir / "results.sarif"

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("subprocess.run")
    def test_run_clippy_flow(self, mock_run):
        # 1. Cargo clippy output with duplicate JSON lines
        line1 = '{"reason":"compiler-message","message":{"message":"warning 1"}}'
        line2 = '{"reason":"compiler-message","message":{"message":"warning 2"}}'
        clippy_stdout = f"{line1}\n{line1}\n{line2}\n{line1}\n"

        # 2. SARIF output
        sarif_stdout = '{"version":"2.1.0","runs":[]}'

        mock_clippy_res = MagicMock(returncode=0, stdout=clippy_stdout, stderr="")
        mock_sarif_res = MagicMock(returncode=0, stdout=sarif_stdout, stderr="")
        mock_fmt_res = MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = [mock_clippy_res, mock_sarif_res, mock_fmt_res]

        env = {
            "ARGS": "--all-targets --all-features",
            "CLIPPY_ARGS": "-D warnings",
            "SARIF_FILE": str(self.sarif_file),
        }

        with patch.dict(os.environ, env, clear=True):
            # Execute script via runpy/subprocess or exec
            with open(RUN_CLIPPY_PATH, "r", encoding="utf-8") as f:
                code = compile(f.read(), str(RUN_CLIPPY_PATH), "exec")
                exec(code, {"__name__": "__main__"})

        self.assertEqual(mock_run.call_count, 3)

        # Verify clippy command arguments
        clippy_call = mock_run.call_args_list[0]
        cmd = clippy_call[0][0]
        self.assertEqual(cmd, ["cargo", "clippy", "--all-targets", "--all-features", "--message-format=json", "--", "-D", "warnings"])

        # Verify clippy-sarif deduplicated input
        sarif_call = mock_run.call_args_list[1]
        self.assertEqual(sarif_call[0][0], ["clippy-sarif"])
        deduped_input = sarif_call[1]["input"]
        expected_deduped = f"{line1}\n{line2}\n"
        self.assertEqual(deduped_input, expected_deduped)

        # Verify SARIF file written
        self.assertTrue(self.sarif_file.exists())
        self.assertEqual(self.sarif_file.read_text(encoding="utf-8"), sarif_stdout)

        # Verify sarif-fmt formatted output call
        fmt_call = mock_run.call_args_list[2]
        self.assertEqual(fmt_call[0][0], ["sarif-fmt"])
        self.assertEqual(fmt_call[1]["input"], sarif_stdout)


if __name__ == "__main__":
    unittest.main()
