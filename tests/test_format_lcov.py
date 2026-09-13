#!/usr/bin/env python3
"""Unit tests for cargo-test-coverage/format_lcov.py."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FORMAT_LCOV_PATH = Path(__file__).resolve().parent.parent / "cargo-test-coverage" / "format_lcov.py"


def run_script(env: dict) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    full_env.update(env)
    return subprocess.run(
        [sys.executable, str(FORMAT_LCOV_PATH)],
        env=full_env,
        capture_output=True,
        text=True,
    )


class TestFormatLcov(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.in_file = self.work_dir / "lcov.info"
        self.out_file = self.work_dir / "lcov_formatted.info"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_input_file_exits_0(self):
        env = {
            "LCOV_INPUT": str(self.work_dir / "missing.info"),
            "LCOV_OUTPUT": str(self.out_file),
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Input file not found", res.stdout)
        self.assertFalse(self.out_file.exists())

    def test_filtering_and_workspace_stripping_posix(self):
        lcov_content = (
            "TN:\n"
            "SF:/home/runner/work/repo/src/partial.rs\n"
            "DA:1,1\n"
            "DA:2,0\n"
            "LF:10\n"
            "LH:8\n"
            "end_of_record\n"
            "TN:\n"
            "SF:/home/runner/work/repo/src/full.rs\n"
            "DA:1,1\n"
            "LF:5\n"
            "LH:5\n"
            "end_of_record\n"
        )
        self.in_file.write_text(lcov_content, encoding="utf-8")
        env = {
            "LCOV_INPUT": str(self.in_file),
            "LCOV_OUTPUT": str(self.out_file),
            "GITHUB_WORKSPACE": "/home/runner/work/repo",
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        self.assertTrue(self.out_file.exists())

        out_text = self.out_file.read_text(encoding="utf-8")
        self.assertIn("SF:src/partial.rs", out_text)
        self.assertIn("LF:10", out_text)
        self.assertIn("LH:8", out_text)
        self.assertNotIn("src/full.rs", out_text)
        self.assertNotIn("LF:5", out_text)

    def test_windows_workspace_stripping(self):
        lcov_content = (
            "SF:C:\\runner\\workspace\\src\\lib.rs\n"
            "LF:10\n"
            "LH:3\n"
            "end_of_record\n"
        )
        self.in_file.write_text(lcov_content, encoding="utf-8")
        env = {
            "LCOV_INPUT": str(self.in_file),
            "LCOV_OUTPUT": str(self.out_file),
            "GITHUB_WORKSPACE": r"C:\runner\workspace",
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        out_text = self.out_file.read_text(encoding="utf-8")
        self.assertIn("SF:src/lib.rs", out_text)


if __name__ == "__main__":
    unittest.main()
