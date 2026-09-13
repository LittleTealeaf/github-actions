#!/usr/bin/env python3
import os
from pathlib import Path
import shlex
import subprocess

args = shlex.split(os.environ.get("ARGS", ""))
clippy_args = shlex.split(os.environ.get("CLIPPY_ARGS", ""))
sarif_file = Path(os.environ.get("SARIF_FILE", "rust-clippy-results.sarif"))

# 1. Run cargo clippy
cmd = ["cargo", "clippy", *args, "--message-format=json"]
if clippy_args:
    cmd += ["--", *clippy_args]
clippy_res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", check=False)

# 2. Deduplicate diagnostic JSON lines
seen = set()
unique_lines = [line for line in clippy_res.stdout.splitlines() if line.strip() and not (line in seen or seen.add(line))]
clippy_json = "\n".join(unique_lines) + "\n" if unique_lines else ""

# 3. Convert JSON to SARIF and save
sarif_res = subprocess.run(["clippy-sarif"], input=clippy_json, capture_output=True, text=True, errors="replace", check=False)
sarif_file.parent.mkdir(parents=True, exist_ok=True)
sarif_file.write_text(sarif_res.stdout, encoding="utf-8")

# 4. Format and print to console
if sarif_res.stdout.strip():
    subprocess.run(["sarif-fmt"], input=sarif_res.stdout, text=True, check=False)
