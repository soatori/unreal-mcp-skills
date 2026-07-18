#!/usr/bin/env python3
"""Validate the Unreal MCP skill package's executable automation contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
COMMANDS = (
    "$unreal-mcp",
    "/unreal-mcp",
    "/ue-mcp",
    "/unreal-mcp:configure <client>",
    "/ue-mcp:configure <client>",
)
LEGACY_MCP_SETTINGS = (
    "Config/DefaultEngine.ini",
    "/Script/ModelContextProtocol.ModelContextProtocolSettings",
    "ServerURLPath",
)
REQUIRED_MCP_SETTINGS = (
    "Config/DefaultEditorPerProjectUserSettings.ini",
    "/Script/ModelContextProtocolEngine.ModelContextProtocolSettings",
    "ServerUrlPath",
)
EVAL_SUCCESS_CONTRACT = (
    "execute",
    "independent evidence",
    "minimal blocker only when",
    "explanation, suggestion, or manual steps alone are not success",
)


def add_error(message: str) -> None:
    ERRORS.append(message)


def require_file(relative_path: str) -> Path:
    path = ROOT / relative_path
    if not path.is_file():
        add_error(f"Missing file: {relative_path}")
    return path


def read_text(relative_path: str) -> str:
    path = require_file(relative_path)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def read_json(relative_path: str) -> Any | None:
    try:
        return json.loads(read_text(relative_path))
    except json.JSONDecodeError as exc:
        add_error(f"{relative_path} is not valid JSON: {exc}")
        return None


def read_tree_text(relative_directory: str, suffixes: tuple[str, ...]) -> dict[str, str]:
    directory = ROOT / relative_directory
    if not directory.is_dir():
        add_error(f"Missing directory: {relative_directory}")
        return {}
    return {
        str(path.relative_to(ROOT)): path.read_text(encoding="utf-8")
        for path in directory.rglob("*")
        if path.is_file() and path.suffix in suffixes
    }


def extract_readme_command_fence(readme: str) -> tuple[set[str], str] | None:
    matches = list(re.finditer(r"(?ms)^```text[ \t]*\r?\n(.*?)^```[ \t]*$", readme))
    if len(matches) != 1:
        add_error("README.md must contain exactly one text command fence")
        return None
    match = matches[0]
    command_lines = {line.strip() for line in match.group(1).splitlines() if line.strip()}
    prose = readme[: match.start()] + readme[match.end() :]
    return command_lines, prose


def validate_readme_commands(readme: str) -> None:
    result = extract_readme_command_fence(readme)
    if result is None:
        return
    command_lines, prose = result
    for command in COMMANDS:
        if command not in command_lines:
            add_error(f"README.md text command fence must include exact command line: {command}")
    if "/ue-mcp" in prose:
        add_error("README.md must reject /ue-mcp outside the supported text command fence")


def validate_mcp_settings(policy_surfaces: dict[str, str], operational_surfaces: dict[str, str]) -> None:
    helper_settings = {
        "Config/DefaultEditorPerProjectUserSettings.ini": '"Config" / "DefaultEditorPerProjectUserSettings.ini"',
        "/Script/ModelContextProtocolEngine.ModelContextProtocolSettings": "/Script/ModelContextProtocolEngine.ModelContextProtocolSettings",
        "ServerUrlPath": "ServerUrlPath",
    }
    configure_helper = operational_surfaces["scripts/configure-unreal-mcp.py"]
    for setting, helper_token in helper_settings.items():
        if helper_token not in configure_helper:
            add_error(f"scripts/configure-unreal-mcp.py must use {setting}")
    for relative_path in ("SKILL.md", "references/configure-workflow.md", "references/mcp-tools.md"):
        text = operational_surfaces[relative_path]
        for setting in REQUIRED_MCP_SETTINGS:
            if setting not in text:
                add_error(f"{relative_path} must use {setting}")
    for legacy_setting in LEGACY_MCP_SETTINGS:
        for relative_path, text in policy_surfaces.items():
            if legacy_setting in text:
                add_error(f"legacy MCP setting {legacy_setting} is forbidden in {relative_path}")


def validate_examples() -> None:
    expected_examples = {
        "references/examples/.mcp.json": ("mcpServers", {"type": "http", "url": "http://127.0.0.1:8000/mcp", "disabled": False}, "Claude"),
        "references/examples/.cursor/mcp.json": ("mcpServers", {"url": "http://127.0.0.1:8000/mcp"}, "Cursor"),
        "references/examples/.vscode/mcp.json": ("servers", {"type": "http", "url": "http://127.0.0.1:8000/mcp"}, "VS Code"),
        "references/examples/.gemini/settings.json": ("mcpServers", {"httpUrl": "http://127.0.0.1:8000/mcp"}, "Gemini"),
    }
    for relative_path, (root_key, expected_server, client) in expected_examples.items():
        example = read_json(relative_path)
        if not isinstance(example, dict) or set(example) != {root_key}:
            add_error(f"{client} example must use exactly the {root_key} root object")
            continue
        servers = example.get(root_key)
        if not isinstance(servers, dict) or servers.get("unreal-mcp") != expected_server:
            add_error(f"{client} example must retain the exact unreal-mcp client schema")


def validate_configure_helper(configure_script: str) -> None:
    protocol_tokens = (
        '"method": "initialize"',
        '"protocolVersion": "2025-11-25"',
        'method="POST"',
        '"Accept": "application/json, text/event-stream"',
        "_parse_initialize_payload",
        "json.loads",
    )
    statuses = (
        'else "configured"',
        'print_status("verified",',
        'else "configured-but-recovery-required"',
        'print_status("protected-config-blocker",',
    )
    missing = [token for token in (*protocol_tokens, *statuses) if token not in configure_script]
    if missing:
        add_error(f"configure helper protocol/status contract is incomplete: {', '.join(missing)}")


def has_affirmative_execution_clause(expected: str) -> bool:
    negated_prefix = re.compile(
        r"(?:\b(?:do|does|did|must|should|shall|will|would|can|could|may)\s+not"
        r"|\b(?:cannot|can't|don't|doesn't|didn't|won't|wouldn't|shouldn't|mustn't)"
        r"|\bnot(?!\s+only\b)|\bnever|\bwithout|\bavoid|\bskip"
        r"|\bno\s+(?:need|reason|requirement)(?:\s+\w+){0,4}\s+to"
        r"|\bunnecessary\s+to|\b(?:refuse|decline)\s+to|\brefrain\s+from)"
        r"(?:\s+\w+){0,4}\s*$"
    )
    negated_suffix = re.compile(
        r"^\s*(?:nothing\b|none\b|zero\s+(?:actions?|operations?|steps?|changes?)\b"
        r"|no\s+(?:actions?|operations?|steps?|changes?|commands?|tools?|work)\b|neither\b"
        r"|without\s+(?:any\s+)?(?:actions?|operations?|steps?|work)\b"
        r"|(?:is|are|was|were)\s+(?:not\s+(?:required|needed|allowed)\b|forbidden\b|prohibited\b|unnecessary\b)"
        r"|(?:must|should|shall|will|would|can|could|may)\s+not\b)"
    )
    for action in re.finditer(r"\bexecut(?:e|es|ed|ing)\b", expected):
        clause_start = max(expected.rfind(separator, 0, action.start()) for separator in ".;:\n") + 1
        following_separators = [expected.find(separator, action.end()) for separator in ".;:\n"]
        clause_end = min((index for index in following_separators if index >= 0), default=len(expected))
        prefix = expected[clause_start : action.start()]
        suffix = expected[action.end() : clause_end]
        if negated_prefix.search(prefix) is None and negated_suffix.search(suffix) is None:
            return True
    return False


def validate_evals(evals_text: str) -> None:
    try:
        eval_data = json.loads(evals_text)
    except json.JSONDecodeError as exc:
        add_error(f"evals/evals.json is not valid JSON: {exc}")
        return
    if not isinstance(eval_data, dict) or set(eval_data) != {"skill_name", "evals"}:
        add_error("evals/evals.json must preserve skill_name and evals external shape")
        return
    if eval_data.get("skill_name") != "unreal-mcp" or not isinstance(eval_data.get("evals"), list):
        add_error("evals/evals.json must name unreal-mcp and contain an eval array")
        return

    scenario_tokens = (
        "VS Code official schema",
        "per-user editor setting overriding defaults",
        "initialize verification failure after safe writes",
        "Tool Search disabled/eager native tools",
        "Codex TOML protected blocker",
    )
    prompts: list[str] = []
    for index, item in enumerate(eval_data["evals"], start=1):
        if not isinstance(item, dict) or set(item) != {"id", "prompt", "expected_output", "files"}:
            add_error(f"eval {index} must preserve id, prompt, expected_output, and files")
            continue
        if not isinstance(item["id"], int) or not isinstance(item["prompt"], str) or not isinstance(item["expected_output"], str) or not isinstance(item["files"], list):
            add_error(f"eval {index} has invalid external field types")
            continue
        prompts.append(item["prompt"])
        expected = item["expected_output"].lower()
        starts_with_guidance = re.match(r"\s*(?:explain|suggest|provide steps|manual steps)\b", expected) is not None
        has_affirmative_action = has_affirmative_execution_clause(expected)
        if not has_affirmative_action:
            qualifier = "guidance-only " if starts_with_guidance else ""
            add_error(f"eval {index} contains a {qualifier}expectation without an affirmative action clause")
        missing = [phrase for phrase in EVAL_SUCCESS_CONTRACT if phrase not in expected]
        if missing:
            add_error(f"eval {index} must require execution success with: {', '.join(missing)}")
    prompt_text = "\n".join(prompts)
    for scenario in scenario_tokens:
        if scenario not in prompt_text:
            add_error(f"evals must include scenario: {scenario}")


def main() -> int:
    ps_suffix = "." + "ps1"
    skill = read_text("SKILL.md")
    readme = read_text("README.md")
    metadata_text = read_text("skills.sh.json")
    openai = read_text("agents/openai.yaml")
    evals_text = read_text("evals/evals.json")
    configure_script = read_text("scripts/configure-unreal-mcp.py")
    configure_workflow = read_text("references/configure-workflow.md")
    mcp_tools = read_text("references/mcp-tools.md")
    references = read_tree_text("references", (".md", ".json", ".toml"))
    agents = read_tree_text("agents", (".md", ".yaml", ".yml"))
    policy_surfaces = {
        "SKILL.md": skill,
        "README.md": readme,
        "scripts/configure-unreal-mcp.py": configure_script,
        **references,
        **agents,
    }

    if not re.search(r"(?m)^name:\s*unreal-mcp\s*$", skill):
        add_error("SKILL.md frontmatter must use name: unreal-mcp")
    if not all(token in skill for token in ("/unreal-mcp", "$unreal-mcp")):
        add_error("SKILL.md must document /unreal-mcp and $unreal-mcp activation forms")
    alias_surfaces = {"SKILL.md": skill, **references, **agents, "evals/evals.json": evals_text}
    if any("/ue-mcp" in text for text in alias_surfaces.values()):
        add_error("SKILL.md, references, agents, and evals must use the canonical /unreal-mcp command")
    if "unreal-mcp-skills\\" in skill:
        add_error("SKILL.md must not contain stale local unreal-mcp-skills runtime paths")
    if "references/configure-workflow.md" not in skill or "references/uasset-read-comparison.md" not in skill:
        add_error("SKILL.md must link its configuration and uasset comparison references")
    if "configure helper" not in skill or f"scripts/configure-unreal-mcp{ps_suffix}" in skill:
        add_error("SKILL.md must describe the configure helper without Windows-only script paths")
    for token in ("Agent Automation Contract", "list_toolsets", "describe_toolset", "call_tool", "independent read", "dirty-state", "minimal blocker"):
        if token not in skill:
            add_error(f"SKILL.md must encode the agent automation contract: {token}")

    if "npx skills add soatori/unreal-mcp-skills" not in readme:
        add_error("README.md must keep the skills.sh install command")
    if ps_suffix in readme:
        add_error("README.md must not document Windows-only script commands")
    validate_readme_commands(readme)
    mcp_policy_surfaces = {"SKILL.md": skill, "README.md": readme, **references, **agents}
    mcp_operational_surfaces = {
        "scripts/configure-unreal-mcp.py": configure_script,
        "SKILL.md": skill,
        "references/configure-workflow.md": configure_workflow,
        "references/mcp-tools.md": mcp_tools,
    }
    validate_mcp_settings(mcp_policy_surfaces, mcp_operational_surfaces)
    validate_examples()
    validate_configure_helper(configure_script)

    for forbidden in ("Quick Setup (Step by Step)", "Terminal Plugin (Optional)", "manually delete", "manual cleanup", "ordinary users should"):
        for relative_path, text in policy_surfaces.items():
            if forbidden.lower() in text.lower():
                add_error(f"tutorial content is forbidden in {relative_path}: {forbidden}")

    try:
        metadata = json.loads(metadata_text)
        entry = metadata["skills"][0]
        if entry.get("name") != "unreal-mcp-skills" or "ue-mcp-skills" not in entry.get("aliases", []) or entry.get("path") != "SKILL.md":
            add_error("skills.sh.json must retain the unreal-mcp-skills distribution metadata")
    except Exception as exc:
        add_error(f"skills.sh.json is not valid JSON: {exc}")

    if not re.search(r"display_name:\s*[\"']Unreal MCP[\"']", openai) or "$unreal-mcp" not in openai:
        add_error("agents/openai.yaml must retain the Unreal MCP activation metadata")

    validate_evals(evals_text)
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
