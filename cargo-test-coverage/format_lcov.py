#!/usr/bin/env python3
import os
from pathlib import Path

input_file = Path(os.environ.get("LCOV_INPUT", "lcov.info"))
output_file = Path(os.environ.get("LCOV_OUTPUT", "lcov_formatted.info"))
workspace = os.environ.get("GITHUB_WORKSPACE", "").replace("\\", "/").strip().rstrip("/")
ws_prefix = (workspace + "/") if workspace else ""

if not input_file.is_file():
    print(f"Input file not found: {input_file}")
    raise SystemExit(0)

records = []
current_lines = []
lf = None
lh = None

for line in input_file.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith("SF:"):
        source = line[3:].replace("\\", "/").strip()
        if ws_prefix and source.startswith(ws_prefix):
            source = source[len(ws_prefix):]
        elif workspace and source == workspace:
            source = ""
        current_lines = [f"SF:{source}"]
        lf, lh = None, None
    elif current_lines:
        current_lines.append(line)
        if line.startswith("LF:"):
            lf = line.split(":", 1)[1].strip()
        elif line.startswith("LH:"):
            lh = line.split(":", 1)[1].strip()
        elif line.strip() == "end_of_record":
            if lf is None or lh is None or lf != lh:
                records.extend(current_lines)
            current_lines = []
            lf, lh = None, None

output_file.parent.mkdir(parents=True, exist_ok=True)
output_file.write_text("\n".join(records) + ("\n" if records else ""), encoding="utf-8")
