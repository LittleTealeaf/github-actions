#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re
import subprocess

try:
    import tomllib
except ImportError:
    tomllib = None

crate_name = os.environ.get("CRATE_NAME", "").strip()
doc_dir = Path(os.environ.get("DOC_DIR", "target/doc"))
manifest_file = Path(os.environ.get("MANIFEST_PATH", "Cargo.toml"))
if manifest_file.is_dir():
    manifest_file /= "Cargo.toml"

# 1. Parse Cargo.toml
if not crate_name and manifest_file.is_file():
    if tomllib:
        try:
            with open(manifest_file, "rb") as f:
                crate_name = tomllib.load(f).get("package", {}).get("name", "")
        except Exception:
            pass
    if not crate_name:
        try:
            match = re.search(
                r'(?m)^\s*\[package\](?:(?!^\s*\[).)*?^\s*name\s*=\s*["\']([^"\']+)["\']',
                manifest_file.read_text(encoding="utf-8"),
                re.DOTALL,
            )
            if match:
                crate_name = match.group(1)
        except Exception:
            pass

# 2. Cargo metadata / read-manifest fallback
if not crate_name and manifest_file.exists():
    for cmd in (
        ["cargo", "metadata", "--no-deps", "--format-version", "1", "--manifest-path", str(manifest_file)],
        ["cargo", "read-manifest", "--manifest-path", str(manifest_file)],
    ):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                crate_name = data.get("packages", [{}])[0].get("name", "") if "packages" in data else data.get("name", "")
                if crate_name:
                    break
        except Exception:
            pass

# 3. Fallback: scan doc directory
if not crate_name and doc_dir.is_dir():
    for item in sorted(doc_dir.iterdir()):
        if item.is_dir() and item.name not in ("src", "implementors") and (item / "index.html").is_file():
            crate_name = item.name
            break

# 4. Generate files
doc_dir.mkdir(parents=True, exist_ok=True)
if crate_name:
    crate_name = crate_name.replace("-", "_")
    print(f"Setting up root index redirect to {crate_name}/index.html")
    (doc_dir / "index.html").write_text(f'<meta http-equiv="refresh" content="0; url={crate_name}/index.html">\n', encoding="utf-8")

(doc_dir / ".nojekyll").touch(exist_ok=True)
