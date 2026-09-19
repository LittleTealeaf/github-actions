#!/usr/bin/env python3
"""
Automated Semantic Versioning and GitHub Release creation script.
Parses conventional commits since the latest git tag, computes the next semver version,
generates a structured changelog, and creates the GitHub release and tags.
"""

import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

COMMIT_REGEX = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$"
)

CATEGORY_MAP = {
    "feat": ("🚀 Features", 1),
    "fix": ("🐛 Bug Fixes", 2),
    "perf": ("⚡ Performance Improvements", 3),
    "refactor": ("♻️ Code Refactoring", 4),
    "docs": ("📝 Documentation", 5),
    "ci": ("👷 Continuous Integration", 6),
    "chore": ("🔧 Chores & Maintenance", 7),
    "test": ("✅ Tests", 8),
    "build": ("📦 Build System", 9),
}


class Commit:
    def __init__(self, commit_hash: str, subject: str, body: str = ""):
        self.commit_hash = commit_hash.strip()
        self.short_hash = self.commit_hash[:7] if len(self.commit_hash) >= 7 else self.commit_hash
        self.subject = subject.strip()
        self.body = body.strip()
        self.commit_type = ""
        self.scope = ""
        self.description = self.subject
        self.is_breaking = False
        self.breaking_description = ""
        self._parse()

    def _parse(self):
        match = COMMIT_REGEX.match(self.subject)
        if match:
            self.commit_type = match.group("type").lower()
            self.scope = match.group("scope") or ""
            if match.group("breaking"):
                self.is_breaking = True
            self.description = match.group("desc").strip()

        # Check for BREAKING CHANGE / BREAKING-CHANGE in body or subject
        breaking_match = re.search(
            r"BREAKING[\s-]CHANGE:\s*(.+)", self.body, re.IGNORECASE | re.MULTILINE
        )
        if breaking_match:
            self.is_breaking = True
            self.breaking_description = breaking_match.group(1).strip()
        elif self.is_breaking and not self.breaking_description:
            self.breaking_description = self.description


def parse_semver(tag: str) -> Optional[Tuple[int, int, int]]:
    """Parse 'vX.Y.Z' or 'X.Y.Z' into (major, minor, patch)."""
    tag = tag.strip().lstrip("v")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", tag)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_semver(major: int, minor: int, patch: int) -> str:
    """Format (major, minor, patch) into 'vX.Y.Z'."""
    return f"v{major}.{minor}.{patch}"


def get_latest_tag() -> Optional[str]:
    """Find the latest semver git tag matching v*.*.* or *.*.*."""
    res = subprocess.run(
        ["git", "tag", "--list", "--sort=-v:refname"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return None

    for line in res.stdout.splitlines():
        line = line.strip()
        if parse_semver(line) is not None:
            return line
    return None


def get_commits_since(tag: Optional[str]) -> List[Commit]:
    """Retrieve commits since the specified tag (or all commits if tag is None)."""
    rev_range = f"{tag}..HEAD" if tag else "HEAD"
    # %H = commit hash, %s = subject, %b = body, %x1f = unit separator, %x1e = record separator
    cmd = ["git", "log", rev_range, "--pretty=format:%H%x1f%s%x1f%b%x1e"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0 or not res.stdout.strip():
        return []

    commits = []
    records = res.stdout.split("\x1e")
    for rec in records:
        rec = rec.strip()
        if not rec:
            continue
        parts = rec.split("\x1f")
        h = parts[0].strip() if len(parts) > 0 else ""
        s = parts[1].strip() if len(parts) > 1 else ""
        b = parts[2].strip() if len(parts) > 2 else ""
        if h or s:
            commits.append(Commit(h, s, b))
    return commits


def determine_bump(commits: List[Commit]) -> Optional[str]:
    """
    Determine semver bump level: 'major', 'minor', 'patch', or None if no bump.
    """
    if not commits:
        return None

    has_major = False
    has_minor = False
    has_patch = False

    for c in commits:
        # Ignore automated merge commits or chore tags that don't need release if desired,
        # but standard conventional commits handle them:
        if c.is_breaking:
            has_major = True
            break
        elif c.commit_type == "feat":
            has_minor = True
        elif c.commit_type in ("fix", "perf", "refactor", "docs", "ci", "chore", "test", "build"):
            has_patch = True
        elif c.subject:
            # Non-conventional commit defaults to patch
            has_patch = True

    if has_major:
        return "major"
    if has_minor:
        return "minor"
    if has_patch:
        return "patch"
    return None


def calculate_next_version(current_tag: Optional[str], bump: str) -> str:
    """Compute the next semver version string given the current tag and bump level."""
    if not current_tag:
        if bump == "major":
            return "v1.0.0"
        elif bump == "minor":
            return "v0.1.0"
        else:
            return "v0.0.1"

    parsed = parse_semver(current_tag)
    if not parsed:
        return "v0.1.0"

    major, minor, patch = parsed
    if bump == "major":
        return format_semver(major + 1, 0, 0)
    elif bump == "minor":
        return format_semver(major, minor + 1, 0)
    elif bump == "patch":
        return format_semver(major, minor, patch + 1)
    return current_tag


def generate_changelog(commits: List[Commit], new_version: str) -> str:
    """Generate categorized markdown changelog from commits."""
    sections: Dict[str, List[str]] = {}
    breaking_changes: List[str] = []

    for c in commits:
        if c.is_breaking:
            desc = c.breaking_description or c.description
            breaking_changes.append(f"- **{c.scope + ': ' if c.scope else ''}**{desc} ({c.short_hash})")

        cat_title, _ = CATEGORY_MAP.get(c.commit_type, ("🔧 Other Changes", 99))
        if cat_title not in sections:
            sections[cat_title] = []

        scope_prefix = f"**{c.scope}:** " if c.scope else ""
        sections[cat_title].append(f"- {scope_prefix}{c.description} ({c.short_hash})")

    lines = [f"## Release {new_version}\n"]

    if breaking_changes:
        lines.append("### 💥 BREAKING CHANGES\n")
        lines.extend(breaking_changes)
        lines.append("")

    # Sort sections by rank in CATEGORY_MAP
    sorted_sections = sorted(
        sections.items(),
        key=lambda item: next((rank for _, (title, rank) in CATEGORY_MAP.items() if title == item[0]), 99),
    )

    for cat_title, items in sorted_sections:
        lines.append(f"### {cat_title}\n")
        lines.extend(items)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def run_release():
    """Main release process executed in CI."""
    latest_tag = get_latest_tag()
    print(f"Latest tag detected: {latest_tag or 'None (initial release)'}")

    commits = get_commits_since(latest_tag)
    print(f"Found {len(commits)} commit(s) since last tag.")

    if not commits:
        print("No new commits found. Skipping release.")
        return

    bump = determine_bump(commits)
    if not bump:
        print("No releasable changes found. Skipping release.")
        return

    new_version = calculate_next_version(latest_tag, bump)
    print(f"Bump type: {bump} -> Target version: {new_version}")

    changelog = generate_changelog(commits, new_version)
    print("\n--- Generated Changelog ---")
    print(changelog)
    print("---------------------------\n")

    # Write changelog to temp file for gh release
    notes_file = Path("RELEASE_NOTES.md")
    notes_file.write_text(changelog, encoding="utf-8")

    # Git tag creation and push
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=False)
    subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)

    print(f"Creating tag {new_version}...")
    subprocess.run(["git", "tag", "-a", new_version, "-m", f"Release {new_version}"], check=True)
    subprocess.run(["git", "push", "origin", new_version], check=True)

    # Major version floating tag (e.g. v1)
    parsed = parse_semver(new_version)
    if parsed:
        major_tag = f"v{parsed[0]}"
        print(f"Updating floating major tag {major_tag}...")
        subprocess.run(["git", "tag", "-fa", major_tag, "-m", f"Update {major_tag} to {new_version}"], check=False)
        subprocess.run(["git", "push", "origin", major_tag, "--force"], check=False)

    # Create GitHub Release via gh CLI
    print(f"Creating GitHub Release for {new_version}...")
    gh_cmd = [
        "gh",
        "release",
        "create",
        new_version,
        "--title",
        new_version,
        "--notes-file",
        str(notes_file),
    ]
    res = subprocess.run(gh_cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"gh release create output: {res.stderr or res.stdout}", file=sys.stderr)
    else:
        print(f"Successfully created GitHub Release {new_version}!")


if __name__ == "__main__":
    run_release()
