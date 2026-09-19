#!/usr/bin/env python3
"""Unit tests for .github/scripts/release.py."""

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import MagicMock, patch

RELEASE_SCRIPT_PATH = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "release.py"

spec = importlib.util.spec_from_file_location("release", RELEASE_SCRIPT_PATH)
release_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_mod)

Commit = release_mod.Commit
parse_semver = release_mod.parse_semver
format_semver = release_mod.format_semver
determine_bump = release_mod.determine_bump
calculate_next_version = release_mod.calculate_next_version
generate_changelog = release_mod.generate_changelog
get_latest_tag = release_mod.get_latest_tag
get_commits_since = release_mod.get_commits_since
run_release = release_mod.run_release


class TestSemVerRelease(unittest.TestCase):
    def test_parse_semver(self):
        self.assertEqual(parse_semver("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_semver("v0.0.1"), (0, 0, 1))
        self.assertIsNone(parse_semver("invalid"))
        self.assertIsNone(parse_semver("v1.2"))

    def test_format_semver(self):
        self.assertEqual(format_semver(1, 2, 3), "v1.2.3")
        self.assertEqual(format_semver(0, 1, 0), "v0.1.0")

    def test_commit_parsing_conventional(self):
        c1 = Commit("1234567890", "feat(clippy): add new linter option")
        self.assertEqual(c1.commit_type, "feat")
        self.assertEqual(c1.scope, "clippy")
        self.assertEqual(c1.description, "add new linter option")
        self.assertFalse(c1.is_breaking)
        self.assertEqual(c1.short_hash, "1234567")

        c2 = Commit("abcdef1234", "fix!: change public API signature")
        self.assertEqual(c2.commit_type, "fix")
        self.assertEqual(c2.scope, "")
        self.assertEqual(c2.description, "change public API signature")
        self.assertTrue(c2.is_breaking)

        c3 = Commit("9999999999", "chore: maintenance", body="BREAKING CHANGE: drops python 3.8 support")
        self.assertEqual(c3.commit_type, "chore")
        self.assertTrue(c3.is_breaking)
        self.assertEqual(c3.breaking_description, "drops python 3.8 support")

    def test_commit_parsing_non_conventional(self):
        c = Commit("1111111111", "Initial commit without convention")
        self.assertEqual(c.commit_type, "")
        self.assertEqual(c.description, "Initial commit without convention")
        self.assertFalse(c.is_breaking)

    def test_determine_bump(self):
        # Empty commits
        self.assertIsNone(determine_bump([]))

        # Breaking change -> major
        c_break = Commit("h1", "feat!: overhaul action interface")
        c_feat = Commit("h2", "feat: add feature")
        c_fix = Commit("h3", "fix: small bug")
        self.assertEqual(determine_bump([c_break, c_feat, c_fix]), "major")

        # Feature -> minor
        self.assertEqual(determine_bump([c_feat, c_fix]), "minor")

        # Fix -> patch
        self.assertEqual(determine_bump([c_fix]), "patch")

        # Non-conventional commit -> patch
        c_other = Commit("h4", "Update README")
        self.assertEqual(determine_bump([c_other]), "patch")

    def test_calculate_next_version(self):
        # Initial versions
        self.assertEqual(calculate_next_version(None, "major"), "v1.0.0")
        self.assertEqual(calculate_next_version(None, "minor"), "v0.1.0")
        self.assertEqual(calculate_next_version(None, "patch"), "v0.0.1")

        # Increments
        self.assertEqual(calculate_next_version("v1.2.3", "patch"), "v1.2.4")
        self.assertEqual(calculate_next_version("v1.2.3", "minor"), "v1.3.0")
        self.assertEqual(calculate_next_version("v1.2.3", "major"), "v2.0.0")
        self.assertEqual(calculate_next_version("1.0.0", "minor"), "v1.1.0")

    def test_generate_changelog(self):
        commits = [
            Commit("aaa1111", "feat(coverage): add workspaces option"),
            Commit("bbb2222", "fix(clippy): resolve SARIF empty file upload"),
            Commit("ccc3333", "feat!: breaking change to inputs", body="BREAKING CHANGE: workspace input deprecated"),
        ]
        changelog = generate_changelog(commits, "v2.0.0")
        self.assertIn("## Release v2.0.0", changelog)
        self.assertIn("### 💥 BREAKING CHANGES", changelog)
        self.assertIn("workspace input deprecated (ccc3333)", changelog)
        self.assertIn("### 🚀 Features", changelog)
        self.assertIn("**coverage:** add workspaces option (aaa1111)", changelog)
        self.assertIn("### 🐛 Bug Fixes", changelog)
        self.assertIn("**clippy:** resolve SARIF empty file upload (bbb2222)", changelog)

    @patch("subprocess.run")
    def test_get_latest_tag(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="v1.1.0\nv1.0.1\nv1.0.0\n")
        tag = get_latest_tag()
        self.assertEqual(tag, "v1.1.0")

        mock_run.return_value = MagicMock(returncode=0, stdout="")
        self.assertIsNone(get_latest_tag())

    @patch("subprocess.run")
    def test_get_commits_since(self, mock_run):
        stdout = f"hash1\x1ffeat: test commit\x1fbody text\x1e"
        mock_run.return_value = MagicMock(returncode=0, stdout=stdout)
        commits = get_commits_since("v1.0.0")
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].subject, "feat: test commit")
        self.assertEqual(commits[0].commit_type, "feat")

    @patch.object(release_mod, "get_latest_tag")
    @patch.object(release_mod, "get_commits_since")
    @patch("subprocess.run")
    def test_run_release_flow(self, mock_run, mock_get_commits, mock_get_tag):
        mock_get_tag.return_value = "v1.0.0"
        mock_get_commits.return_value = [
            Commit("1111111", "feat: new feature"),
        ]
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/...", stderr="")

        with patch("pathlib.Path.write_text") as mock_write:
            run_release()

        # Check tag commands
        calls = [c[0][0] for c in mock_run.call_args_list]
        self.assertTrue(any("tag" in cmd and "v1.1.0" in cmd for cmd in calls))
        self.assertTrue(any("push" in cmd and "v1.1.0" in cmd for cmd in calls))
        self.assertTrue(any("gh" in cmd and "release" in cmd and "create" in cmd for cmd in calls))


if __name__ == "__main__":
    unittest.main()
