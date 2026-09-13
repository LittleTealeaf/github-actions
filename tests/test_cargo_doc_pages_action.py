#!/usr/bin/env python3
"""Validation tests for cargo-doc-pages/action.yml without external dependencies."""

from pathlib import Path
import re
import unittest

ACTION_YML_PATH = Path(__file__).resolve().parent.parent / "cargo-doc-pages" / "action.yml"


def parse_simple_yaml(text: str):
    """
    A lightweight parser for GitHub Action composite action YAML files
    supporting mappings, lists, strings (quoted/unquoted), and comments.
    """
    lines = text.splitlines()

    def strip_comment(line: str) -> str:
        # Avoid stripping # inside quotes
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

    cleaned_lines = []
    for line_no, raw_line in enumerate(lines, start=1):
        line = strip_comment(raw_line).rstrip()
        if line.strip():
            indent = len(line) - len(line.lstrip())
            cleaned_lines.append((indent, line.strip(), line_no))

    if not cleaned_lines:
        return {}

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

    def parse_block(idx: int, current_indent: int):
        # Determine if this block is a list or mapping
        if idx >= len(cleaned_lines):
            return {}, idx

        indent, content, line_no = cleaned_lines[idx]
        if indent < current_indent:
            return {}, idx

        if content.startswith("-"):
            # It's a list
            items = []
            while idx < len(cleaned_lines):
                indent, content, line_no = cleaned_lines[idx]
                if indent < current_indent:
                    break
                if indent > current_indent:
                    raise ValueError(f"Unexpected indentation at line {line_no}: {content}")
                if not content.startswith("-"):
                    break

                # Item line
                item_content = content[1:].strip()
                idx += 1
                if not item_content:
                    # Item is a nested block
                    if idx < len(cleaned_lines) and cleaned_lines[idx][0] > indent:
                        nested_val, idx = parse_block(idx, cleaned_lines[idx][0])
                        items.append(nested_val)
                    else:
                        items.append(None)
                elif ":" in item_content:
                    # Item starts with a key-value mapping on the same line: "- name: Foo"
                    k, v = item_content.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    item_dict = {}
                    if v:
                        item_dict[k] = parse_value(v)
                    else:
                        if idx < len(cleaned_lines) and cleaned_lines[idx][0] > indent:
                            nested_val, idx = parse_block(idx, cleaned_lines[idx][0])
                            item_dict[k] = nested_val
                        else:
                            item_dict[k] = None

                    # Continue collecting key-values at the nested indent level if any
                    # The indent level for keys following "- name: ..." can be indent + 2 (or more)
                    if idx < len(cleaned_lines) and cleaned_lines[idx][0] > indent and not cleaned_lines[idx][1].startswith("-"):
                        child_indent = cleaned_lines[idx][0]
                        while idx < len(cleaned_lines) and cleaned_lines[idx][0] == child_indent:
                            if cleaned_lines[idx][1].startswith("-"):
                                break
                            c_line = cleaned_lines[idx][1]
                            idx += 1
                            if ":" in c_line:
                                ck, cv = c_line.split(":", 1)
                                ck = ck.strip()
                                cv = cv.strip()
                                if cv:
                                    item_dict[ck] = parse_value(cv)
                                else:
                                    if idx < len(cleaned_lines) and cleaned_lines[idx][0] > child_indent:
                                        nested_c, idx = parse_block(idx, cleaned_lines[idx][0])
                                        item_dict[ck] = nested_c
                                    else:
                                        item_dict[ck] = None
                    items.append(item_dict)
                else:
                    items.append(parse_value(item_content))
            return items, idx
        else:
            # It's a mapping
            mapping = {}
            while idx < len(cleaned_lines):
                indent, content, line_no = cleaned_lines[idx]
                if indent < current_indent:
                    break
                if indent > current_indent:
                    raise ValueError(f"Unexpected indentation at line {line_no}: {content}")
                if content.startswith("-"):
                    break

                idx += 1
                if ":" not in content:
                    raise ValueError(f"Expected key-value pair at line {line_no}: {content}")

                k, v = content.split(":", 1)
                k = k.strip()
                v = v.strip()

                if v:
                    mapping[k] = parse_value(v)
                else:
                    if idx < len(cleaned_lines) and cleaned_lines[idx][0] > indent:
                        nested_val, idx = parse_block(idx, cleaned_lines[idx][0])
                        mapping[k] = nested_val
                    else:
                        mapping[k] = None
            return mapping, idx

    parsed, _ = parse_block(0, cleaned_lines[0][0])
    return parsed


class TestCargoDocPagesActionYaml(unittest.TestCase):
    """Tests to validate cargo-doc-pages/action.yml syntax and composite action structure."""

    @classmethod
    def setUpClass(cls):
        cls.raw_content = ACTION_YML_PATH.read_text(encoding="utf-8")
        cls.data = parse_simple_yaml(cls.raw_content)

    def test_yaml_syntax_valid(self):
        """Action YAML must be valid YAML and parse into a dictionary."""
        self.assertIsInstance(self.data, dict)

    def test_metadata_fields(self):
        """Top-level metadata fields should be properly defined."""
        self.assertEqual(self.data.get("name"), "Cargo Doc Pages")
        self.assertTrue(self.data.get("description"))
        self.assertEqual(self.data.get("author"), "Thomas Kwashnak")

    def test_inputs_structure(self):
        """All required inputs must be defined with defaults and descriptions."""
        inputs = self.data.get("inputs", {})
        expected_inputs = [
            "crate-name",
            "toolchain",
            "working-directory",
            "args",
            "deploy",
        ]
        for inp in expected_inputs:
            self.assertIn(inp, inputs)
            self.assertIn("description", inputs[inp])
            self.assertIn("required", inputs[inp])
            self.assertFalse(inputs[inp]["required"])
            self.assertIn("default", inputs[inp])

        self.assertEqual(inputs["toolchain"]["default"], "stable")
        self.assertEqual(inputs["working-directory"]["default"], ".")
        self.assertEqual(inputs["args"]["default"], "--no-deps --all-features --workspace")
        self.assertEqual(inputs["deploy"]["default"], "true")

    def test_outputs_structure(self):
        """Outputs should be defined correctly."""
        outputs = self.data.get("outputs", {})
        self.assertIn("page-url", outputs)
        self.assertEqual(outputs["page-url"]["value"], "${{ steps.deployment.outputs.page_url }}")

    def test_runs_using_composite(self):
        """Action must use composite runtype."""
        runs = self.data.get("runs", {})
        self.assertEqual(runs.get("using"), "composite")
        self.assertIsInstance(runs.get("steps"), list)

    def test_all_run_steps_have_shell(self):
        """All composite action steps with a 'run' property must specify a 'shell'."""
        steps = self.data.get("runs", {}).get("steps", [])
        for step in steps:
            if "run" in step:
                self.assertIn("shell", step, f"Step '{step.get('name')}' has 'run' but missing 'shell'")

    def test_setup_docs_step(self):
        """The redirect setup step should invoke python3 setup_docs.py with action_path and CRATE_NAME env."""
        steps = self.data.get("runs", {}).get("steps", [])
        setup_step = next((s for s in steps if s.get("name") == "Setup Documentation Redirect"), None)
        self.assertIsNotNone(setup_step)
        self.assertEqual(setup_step.get("shell"), "bash")
        self.assertEqual(setup_step.get("working-directory"), "${{ inputs.working-directory }}")
        self.assertIn("env", setup_step)
        self.assertEqual(setup_step["env"].get("CRATE_NAME"), "${{ inputs.crate-name }}")
        run_cmd = setup_step.get("run", "")
        self.assertEqual(run_cmd.strip(), 'python3 "${{ github.action_path }}/setup_docs.py"')

    def test_input_references_match_defined_inputs(self):
        """Any expression referencing inputs.<name> must match an existing input."""
        defined_inputs = set(self.data.get("inputs", {}).keys())
        matches = re.findall(r"inputs\.([a-zA-Z0-9_-]+)", self.raw_content)
        for match in matches:
            self.assertIn(match, defined_inputs, f"Referenced input '{match}' not found in inputs definition")


if __name__ == "__main__":
    unittest.main()
