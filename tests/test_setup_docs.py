#!/usr/bin/env python3
"""Unit tests for cargo-doc-pages/setup_docs.py."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

SETUP_DOCS_PATH = Path(__file__).resolve().parent.parent / "cargo-doc-pages" / "setup_docs.py"


def run_script(env: dict) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    full_env.update(env)
    return subprocess.run(
        [sys.executable, str(SETUP_DOCS_PATH)],
        env=full_env,
        capture_output=True,
        text=True,
    )


class TestSetupDocs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.doc_dir = self.work_dir / "target" / "doc"
        self.manifest = self.work_dir / "Cargo.toml"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_explicit_crate_name_with_hyphens(self):
        env = {
            "CRATE_NAME": "my-awesome-crate",
            "DOC_DIR": str(self.doc_dir),
            "MANIFEST_PATH": str(self.manifest),
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        self.assertTrue((self.doc_dir / ".nojekyll").is_file())
        self.assertTrue((self.doc_dir / "index.html").is_file())
        self.assertIn("url=my_awesome_crate/index.html", (self.doc_dir / "index.html").read_text())

    def test_parse_from_cargo_toml_double_quotes(self):
        self.manifest.write_text('[package]\nname = "toml-pkg-name"\nversion = "0.1.0"\n', encoding="utf-8")
        env = {
            "CRATE_NAME": "",
            "DOC_DIR": str(self.doc_dir),
            "MANIFEST_PATH": str(self.manifest),
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        self.assertTrue((self.doc_dir / ".nojekyll").is_file())
        self.assertTrue((self.doc_dir / "index.html").is_file())
        self.assertIn("url=toml_pkg_name/index.html", (self.doc_dir / "index.html").read_text())

    def test_parse_from_cargo_toml_single_quotes(self):
        self.manifest.write_text("[package]\nname = 'single-quote-pkg'\n", encoding="utf-8")
        env = {
            "CRATE_NAME": "",
            "DOC_DIR": str(self.doc_dir),
            "MANIFEST_PATH": str(self.manifest),
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        self.assertIn("url=single_quote_pkg/index.html", (self.doc_dir / "index.html").read_text())

    def test_fallback_to_doc_dir_inspection(self):
        crate_dir = self.doc_dir / "discovered_crate"
        crate_dir.mkdir(parents=True)
        (crate_dir / "index.html").touch()

        env = {
            "CRATE_NAME": "",
            "DOC_DIR": str(self.doc_dir),
            "MANIFEST_PATH": str(self.manifest),
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        self.assertTrue((self.doc_dir / "index.html").is_file())
        self.assertIn("url=discovered_crate/index.html", (self.doc_dir / "index.html").read_text())

    def test_unresolvable_creates_nojekyll_only(self):
        env = {
            "CRATE_NAME": "",
            "DOC_DIR": str(self.doc_dir),
            "MANIFEST_PATH": str(self.manifest),
        }
        res = run_script(env)
        self.assertEqual(res.returncode, 0)
        self.assertTrue((self.doc_dir / ".nojekyll").is_file())
        self.assertFalse((self.doc_dir / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
