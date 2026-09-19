#!/usr/bin/env python3
"""Validation tests for cargo-clippy/action.yml without external dependencies."""

from pathlib import Path
import re
import unittest

ACTION_YML_PATH = Path(__file__).resolve().parent.parent / "cargo-clippy" / "action.yml"


def parse_simple_yaml(text: str):
    """
    A lightweight parser for GitHub Action composite action YAML files
    supporting mappings, lists, strings (quoted/unquoted), multiline block scalars, and comments.
    """
    lines = text.splitlines()

    def strip_comment(line: str) -> str:
        in_quote = None
        for i, char in enumerate(line):
            if char in ('"', "'"):
                if in_quote == char:
                    in_quote = None
                elif in_quote is None:
                    in_quote = char
            elif char == '#' and in_quote is None:
                return line[:i]
        return line

    raw_lines = [strip_comment(l) for l in lines]
    n = len(raw_lines)

    def get_indent(l: str) -> int:
        return len(l) - len(l.lstrip())

    def parse_value(val_str: str):
        val_str = val_str.strip()
        if (val_str.startswith("'") and val_str.endswith("'")) or \
           (val_str.startswith('"') and val_str.endswith('"')):
            return val_str[1:-1]
        if val_str.lower() == "true":
            return True
        if val_str.lower() == "false":
            return False
        if val_str.isdigit():
            return int(val_str)
        return val_str

    def parse_block_scalar(start_idx: int, parent_indent: int):
        block_lines = []
        block_indent = None
        idx = start_idx
        while idx < n:
            line = raw_lines[idx]
            if not line.strip():
                block_lines.append("")
                idx += 1
                continue
            curr_ind = get_indent(line)
            if block_indent is None:
                if curr_ind <= parent_indent:
                    break
                block_indent = curr_ind
            elif curr_ind < block_indent:
                break
            block_lines.append(line[block_indent:])
            idx += 1
        return "\n".join(block_lines), idx

    def parse_block(start_idx: int, min_indent: int):
        idx = start_idx
        while idx < n and not raw_lines[idx].strip():
            idx += 1
        if idx >= n:
            return None, idx

        line = raw_lines[idx]
        indent = get_indent(line)
        if indent < min_indent:
            return None, idx

        content = line.strip()
        if content.startswith("-"):
            items = []
            while idx < n:
                while idx < n and not raw_lines[idx].strip():
                    idx += 1
                if idx >= n:
                    break
                l = raw_lines[idx]
                ind = get_indent(l)
                if ind < indent:
                    break
                if ind > indent:
                    raise ValueError(f"Unexpected indentation at line {idx+1}: {l}")
                c = l.strip()
                if not c.startswith("-"):
                    break

                item_text = c[1:].strip()
                idx += 1

                if not item_text:
                    val, idx = parse_block(idx, indent + 1)
                    items.append(val)
                elif ":" in item_text:
                    k, v = item_text.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    item_map = {}
                    if v in ("|", "|-", "|+", ">", ">-", ">+"):
                        scalar_val, idx = parse_block_scalar(idx, ind)
                        item_map[k] = scalar_val
                    elif v:
                        item_map[k] = parse_value(v)
                    else:
                        val, idx = parse_block(idx, ind + 2)
                        item_map[k] = val

                    # Sibling keys under same list item
                    while idx < n:
                        while idx < n and not raw_lines[idx].strip():
                            idx += 1
                        if idx >= n:
                            break
                        child_l = raw_lines[idx]
                        child_ind = get_indent(child_l)
                        if child_ind <= ind:
                            break
                        child_c = child_l.strip()
                        if child_c.startswith("-") or ":" not in child_c:
                            break
                        idx += 1
                        ck, cv = child_c.split(":", 1)
                        ck = ck.strip()
                        cv = cv.strip()
                        if cv in ("|", "|-", "|+", ">", ">-", ">+"):
                            scalar_val, idx = parse_block_scalar(idx, child_ind)
                            item_map[ck] = scalar_val
                        elif cv:
                            item_map[ck] = parse_value(cv)
                        else:
                            c_val, idx = parse_block(idx, child_ind + 2)
                            item_map[ck] = c_val
                    items.append(item_map)
                else:
                    items.append(parse_value(item_text))
            return items, idx
        else:
            mapping = {}
            while idx < n:
                while idx < n and not raw_lines[idx].strip():
                    idx += 1
                if idx >= n:
                    break
                l = raw_lines[idx]
                ind = get_indent(l)
                if ind < indent:
                    break
                if ind > indent:
                    raise ValueError(f"Unexpected indentation at line {idx+1}: {l}")
                c = l.strip()
                if c.startswith("-"):
                    break
                if ":" not in c:
                    raise ValueError(f"Expected key-value at line {idx+1}: {l}")
                idx += 1
                k, v = c.split(":", 1)
                k = k.strip()
                v = v.strip()
                if v in ("|", "|-", "|+", ">", ">-", ">+"):
                    scalar_val, idx = parse_block_scalar(idx, ind)
                    mapping[k] = scalar_val
                elif v:
                    mapping[k] = parse_value(v)
                else:
                    val, idx = parse_block(idx, ind + 2)
                    mapping[k] = val
            return mapping, idx

    parsed, _ = parse_block(0, 0)
    return parsed


class TestCargoClippyActionYaml(unittest.TestCase):
    """Tests to validate cargo-clippy/action.yml syntax and composite action structure."""

    @classmethod
    def setUpClass(cls):
        cls.raw_content = ACTION_YML_PATH.read_text(encoding="utf-8")
        cls.data = parse_simple_yaml(cls.raw_content)

    def test_yaml_syntax_valid(self):
        """Action YAML must be valid YAML and parse into a dictionary."""
        self.assertIsInstance(self.data, dict)

    def test_metadata_fields(self):
        """Top-level metadata fields should be properly defined."""
        self.assertEqual(self.data.get("name"), "Cargo Clippy")
        self.assertTrue(self.data.get("description"))
        self.assertEqual(self.data.get("author"), "Thomas Kwashnak")

    def test_inputs_structure(self):
        """All expected inputs must be defined with defaults and descriptions."""
        inputs = self.data.get("inputs", {})
        expected_inputs = [
            "toolchain",
            "components",
            "working-directory",
            "args",
            "clippy-args",
            "upload-sarif",
            "sarif-file",
        ]
        for inp in expected_inputs:
            self.assertIn(inp, inputs)
            self.assertIn("description", inputs[inp])
            self.assertIn("required", inputs[inp])
            self.assertFalse(inputs[inp]["required"])
            self.assertIn("default", inputs[inp])

        self.assertEqual(inputs["toolchain"]["default"], "stable")
        self.assertEqual(inputs["components"]["default"], "clippy")
        self.assertEqual(inputs["working-directory"]["default"], ".")
        self.assertEqual(inputs["args"]["default"], "--all --no-deps --all-features")
        self.assertEqual(inputs["clippy-args"]["default"], "-W clippy::todo")
        self.assertEqual(inputs["upload-sarif"]["default"], "true")
        self.assertEqual(inputs["sarif-file"]["default"], "rust-clippy-results.sarif")

    def test_runs_using_composite(self):
        """Action must use composite runtype."""
        runs = self.data.get("runs", {})
        self.assertEqual(runs.get("using"), "composite")
        self.assertIsInstance(runs.get("steps"), list)

    def test_steps_count_and_names(self):
        """Verify the sequence and names of steps in the action."""
        steps = self.data.get("runs", {}).get("steps", [])
        step_names = [s.get("name") for s in steps]
        expected_names = [
            "Setup Rust",
            "Install Components",
            "Run Clippy",
            "Upload Clippy Results",
        ]
        self.assertEqual(step_names, expected_names)

    def test_all_run_steps_have_shell(self):
        """All composite action steps with a 'run' property must specify a 'shell'."""
        steps = self.data.get("runs", {}).get("steps", [])
        for step in steps:
            if "run" in step:
                self.assertIn("shell", step, f"Step '{step.get('name')}' has 'run' but missing 'shell'")

    def test_setup_rust_step(self):
        """Setup Rust step must configure toolchain and components."""
        steps = self.data.get("runs", {}).get("steps", [])
        step = next((s for s in steps if s.get("name") == "Setup Rust"), None)
        self.assertIsNotNone(step)
        self.assertIn("actions-rust-lang/setup-rust-toolchain", step.get("uses", ""))
        with_params = step.get("with", {})
        self.assertEqual(with_params.get("toolchain"), "${{ inputs.toolchain }}")
        self.assertEqual(with_params.get("components"), "${{ inputs.components }}")

    def test_install_components_step(self):
        """Install Components step must install sarif-fmt and clippy-sarif."""
        steps = self.data.get("runs", {}).get("steps", [])
        step = next((s for s in steps if s.get("name") == "Install Components"), None)
        self.assertIsNotNone(step)
        self.assertIn("taiki-e/install-action", step.get("uses", ""))
        self.assertEqual(step.get("with", {}).get("tool"), "sarif-fmt,clippy-sarif")

    def test_run_clippy_step(self):
        """Run Clippy step must invoke python3 run_clippy.py with env variables."""
        steps = self.data.get("runs", {}).get("steps", [])
        step = next((s for s in steps if s.get("name") == "Run Clippy"), None)
        self.assertIsNotNone(step)
        self.assertEqual(step.get("shell"), "bash")
        self.assertEqual(step.get("working-directory"), "${{ inputs.working-directory }}")
        self.assertTrue(step.get("continue-on-error"))
        self.assertIn("env", step)
        self.assertEqual(step["env"].get("ARGS"), "${{ inputs.args }}")
        self.assertEqual(step["env"].get("CLIPPY_ARGS"), "${{ inputs.clippy-args }}")
        self.assertEqual(step["env"].get("SARIF_FILE"), "${{ inputs.sarif-file }}")
        run_cmd = step.get("run", "")
        self.assertEqual(run_cmd.strip(), 'python3 "${{ github.action_path }}/run_clippy.py"')

    def test_upload_clippy_results_step(self):
        """Upload Clippy Results step must check upload-sarif and pass sarif_file."""
        steps = self.data.get("runs", {}).get("steps", [])
        step = next((s for s in steps if s.get("name") == "Upload Clippy Results"), None)
        self.assertIsNotNone(step)
        self.assertEqual(step.get("if"), "inputs.upload-sarif == 'true' && inputs.sarif-file != ''")
        self.assertIn("github/codeql-action/upload-sarif", step.get("uses", ""))
        with_params = step.get("with", {})
        self.assertEqual(with_params.get("sarif_file"), "${{ inputs.working-directory }}/${{ inputs.sarif-file }}")
        self.assertTrue(with_params.get("wait-for-processing"))

    def test_input_references_match_defined_inputs(self):
        """Any expression referencing inputs.<name> must match an existing input."""
        defined_inputs = set(self.data.get("inputs", {}).keys())
        matches = re.findall(r"inputs\.([a-zA-Z0-9_-]+)", self.raw_content)
        for match in matches:
            self.assertIn(match, defined_inputs, f"Referenced input '{match}' not found in inputs definition")


if __name__ == "__main__":
    unittest.main()
