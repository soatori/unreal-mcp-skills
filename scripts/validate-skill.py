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
    configure_workflow = read_text("references/configure-workflow.md")
    mcp_tools = read_text("references/mcp-tools.md")
    configure_script = read_text("scripts/configure-unreal-mcp.py")
    policy_text = "\n".join((skill, readme, configure_workflow, mcp_tools))

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
    if "configure helper" not in skill or f"scripts/configure-unreal-mcp{ps_suffix}" in skill:
        add_error("SKILL.md must describe the configure helper without Windows-only script paths")
    if "Do not stop at asking whether guidance is needed" not in skill:
        add_error("SKILL.md workflow must require automatic project configuration, not guidance-only setup")

    if "npx skills add soatori/unreal-mcp-skills" not in readme:
        add_error("README.md must keep the skills.sh install command")
    if "/unreal-mcp-skills" in readme and "Do not use `/unreal-mcp-skills`" not in readme:
        add_error("README.md may mention /unreal-mcp-skills only to say it is not a command")
    if "scripts/validate-skill.py" not in readme:
        add_error("README.md must document the validation Python script")
    quick_start = readme.split("## Configure Command", 1)[0]
    if "scripts/configure-unreal-mcp.py" in quick_start:
        add_error("README.md Quick Start should describe skill invocation, not manual configure helper execution")
    if ps_suffix in readme:
        add_error("README.md must not document Windows-only script commands")
    if "automatically set up the target UE project" not in readme:
        add_error("README.md Configure Command must state that project setup is automatic")
    if "The target client does not limit project setup" not in configure_workflow:
        add_error("configure-workflow.md must state that every target configures the UE project by default")
    if "Do not merely ask whether the user wants guidance" not in configure_workflow:
        add_error("configure-workflow.md must block guidance-only configure behavior")
    if "not args.skip_enable_plugins" not in configure_script or "not args.skip_auto_start" not in configure_script:
        add_error("configure helper must enable core plugins and Auto Start by default")
    for token in ("COMMON_TOOLSET_PLUGINS", "EditorToolset", "AutomationTestToolset", "LiveCodingToolset", "ToolsetProfile"):
        if token not in configure_script:
            add_error(f"configure helper must support default common Toolset setup: {token}")
        if token != "COMMON_TOOLSET_PLUGINS" and token not in policy_text:
            add_error(f"docs must mention common Toolset setup: {token}")
    restart_tokens = (
        "Post-Configure Save/Restart Dialog",
        "Should I launch or restart Unreal Editor for this project now",
        "Do not terminate a running editor process without explicit confirmation",
    )
    for token in restart_tokens:
        if token not in policy_text:
            add_error(f"docs must include save/restart dialog guidance: {token}")
    for token in ("Save the UE project before restart", "restart manually", "explicit confirmation"):
        if token not in configure_script:
            add_error(f"configure helper must print post-configure restart guidance: {token}")
    stale_limits = (
        "It" + " does" + " not" + " enable `" + "AllToolsets`",
        "does" + " not" + " enable `" + "AllToolsets`",
        "Do" + " not" + " enable `" + "AllToolsets` by default",
        "Do" + " not" + " use `" + "AllToolsets` as the default",
    )
    for phrase in stale_limits:
        if phrase in policy_text:
            add_error(f"Stale AllToolsets restriction remains: {phrase}")

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
