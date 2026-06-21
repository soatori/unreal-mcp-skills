#!/usr/bin/env python3
"""Validate the Unreal MCP skill package for naming and resource consistency."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def add_error(message: str) -> None:
    ERRORS.append(message)


def require_file(relative_path: str) -> Path:
    path = ROOT / relative_path
    if not path.is_file():
        add_error(f"Missing file: {relative_path}")
    return path


def read_text(relative_path: str) -> str:
    path = require_file(relative_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def main() -> int:
    ps_suffix = "." + "ps1"
    skill = read_text("SKILL.md")
    readme = read_text("README.md")
    metadata_text = read_text("skills.sh.json")
    openai = read_text("agents/openai.yaml")

    if not re.search(r"(?m)^name:\s*unreal-mcp\s*$", skill):
        add_error("SKILL.md frontmatter must use name: unreal-mcp")
    if not all(token in skill for token in ("/unreal-mcp", "/ue-mcp", "$unreal-mcp")):
        add_error("SKILL.md must document /unreal-mcp, /ue-mcp, and $unreal-mcp activation forms")
    if "/unreal-mcp-skills" in skill and not re.search(r"Do not .*?/unreal-mcp-skills", skill):
        add_error("SKILL.md may mention /unreal-mcp-skills only to say it is not a command")
    if "unreal-mcp-skills\\" in skill:
        add_error("SKILL.md must not contain stale local unreal-mcp-skills runtime paths")
    if "references/configure-workflow.md" not in skill:
        add_error("SKILL.md must point configuration tasks to references/configure-workflow.md")
    if "references/uasset-read-comparison.md" not in skill:
        add_error("SKILL.md must point uasset comparison tasks to references/uasset-read-comparison.md")
    if "scripts/configure-unreal-mcp.py" not in skill or f"scripts/configure-unreal-mcp{ps_suffix}" in skill:
        add_error("SKILL.md must point configure tasks to scripts/configure-unreal-mcp.py only")

    if "npx skills add soatori/unreal-mcp-skills" not in readme:
        add_error("README.md must keep the skills.sh install command")
    if "/unreal-mcp-skills" in readme and "Do not use `/unreal-mcp-skills`" not in readme:
        add_error("README.md may mention /unreal-mcp-skills only to say it is not a command")
    if "scripts/configure-unreal-mcp.py" not in readme or "scripts/validate-skill.py" not in readme:
        add_error("README.md must document configure and validation Python scripts")
    if ps_suffix in readme:
        add_error("README.md must not document Windows-only script commands")

    try:
        metadata = json.loads(metadata_text)
        entry = metadata["skills"][0]
        if entry.get("name") != "unreal-mcp-skills":
            add_error("skills.sh.json first skill name must be unreal-mcp-skills")
        if "ue-mcp-skills" not in entry.get("aliases", []):
            add_error("skills.sh.json aliases must include ue-mcp-skills")
        if entry.get("path") != "SKILL.md":
            add_error("skills.sh.json path must be SKILL.md")
    except Exception as exc:
        add_error(f"skills.sh.json is not valid JSON: {exc}")

    if not re.search(r"display_name:\s*[\"']Unreal MCP[\"']", openai):
        add_error("agents/openai.yaml display_name should be Unreal MCP")
    if "$unreal-mcp" not in openai:
        add_error("agents/openai.yaml default_prompt should mention $unreal-mcp")

    for file_path in (
        "references/examples/.mcp.json",
        "references/examples/.codex/config.toml",
        "references/examples/.cursor/mcp.json",
        "references/examples/.vscode/mcp.json",
        "references/examples/.gemini/settings.json",
        "references/configure-workflow.md",
        "references/uasset-read-comparison.md",
        "scripts/configure-unreal-mcp.py",
        "scripts/validate-skill.py",
    ):
        require_file(file_path)

    for removed_script in (ROOT / "scripts").glob(f"*{ps_suffix}"):
        add_error(f"Windows-only script should be removed: {removed_script.relative_to(ROOT)}")

    if ERRORS:
        print("Skill validation failed:")
        for error in ERRORS:
            print(f" - {error}")
        return 1

    print("Skill validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
