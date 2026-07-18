"""Behavioral contract tests for the skill-package validator."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    "$unreal-mcp",
    "/unreal-mcp",
    "/ue-mcp",
    "/unreal-mcp:configure <client>",
    "/ue-mcp:configure <client>",
)
REQUIRED_MCP_SETTINGS = (
    "Config/DefaultEditorPerProjectUserSettings.ini",
    "/Script/ModelContextProtocolEngine.ModelContextProtocolSettings",
    "ServerUrlPath",
)
LEGACY_MCP_SETTINGS = (
    "Config/DefaultEngine.ini",
    "/Script/ModelContextProtocol.ModelContextProtocolSettings",
    "ServerURLPath",
)
AUTHORITATIVE_MCP_SURFACES = (
    "SKILL.md",
    "references/configure-workflow.md",
    "references/mcp-tools.md",
)
HELPER_MCP_SETTINGS = (
    ("Config/DefaultEditorPerProjectUserSettings.ini", '"Config" / "DefaultEditorPerProjectUserSettings.ini"'),
    ("/Script/ModelContextProtocolEngine.ModelContextProtocolSettings", "/Script/ModelContextProtocolEngine.ModelContextProtocolSettings"),
    ("ServerUrlPath", "ServerUrlPath"),
)
HELPER_CONTRACT_TOKENS = (
    '"method": "initialize"',
    '"protocolVersion": "2025-11-25"',
    'method="POST"',
    '"Accept": "application/json, text/event-stream"',
    "_parse_initialize_payload",
    "json.loads",
    'else "configured"',
    'print_status("verified",',
    'else "configured-but-recovery-required"',
    'print_status("protected-config-blocker",',
)
FORBIDDEN_TUTORIAL_CONTENT = (
    "Quick Setup (Step by Step)",
    "Terminal Plugin (Optional)",
    "manually delete",
    "manual cleanup",
    "ordinary users should",
)
EXAMPLE_SCHEMAS = (
    ("references/examples/.mcp.json", "Claude"),
    ("references/examples/.cursor/mcp.json", "Cursor"),
    ("references/examples/.vscode/mcp.json", "VS Code"),
    ("references/examples/.gemini/settings.json", "Gemini"),
)
EVAL_SCENARIOS = (
    "VS Code official schema",
    "per-user editor setting overriding defaults",
    "initialize verification failure after safe writes",
    "Tool Search disabled/eager native tools",
    "Codex TOML protected blocker",
)
EVAL_SUCCESS_CONTRACT = (
    "execute",
    "independent evidence",
    "minimal blocker only when",
    "explanation, suggestion, or manual steps alone are not success",
)


class ValidateSkillTests(unittest.TestCase):
    def make_package(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary_directory = tempfile.TemporaryDirectory()
        package_root = Path(temporary_directory.name) / "unreal-mcp"
        shutil.copytree(
            REPOSITORY_ROOT,
            package_root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        return temporary_directory, package_root

    def validate(self, package_root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(package_root / "scripts" / "validate-skill.py")],
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_mutation_is_rejected(self, package_root: Path, message: str) -> None:
        result = self.validate(package_root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(message, result.stdout + result.stderr)

    def replace_all(self, path: Path, token: str, replacement: str) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(token, text, f"precondition missing {token!r} in {path}")
        path.write_text(text.replace(token, replacement), encoding="utf-8")

    def test_rejects_each_readme_command_that_is_not_an_exact_nonempty_fence_line(self) -> None:
        for command in COMMANDS:
            with self.subTest(command=command):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    self.replace_all(package_root / "README.md", f"{command}\n", f"{command} extra\n")
                    self.assert_mutation_is_rejected(package_root, f"exact command line: {command}")

    def test_rejects_readme_alias_outside_the_text_command_fence(self) -> None:
        temporary_directory, package_root = self.make_package()
        with temporary_directory:
            readme = package_root / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nUse /ue-mcp outside the command list.\n", encoding="utf-8")
            self.assert_mutation_is_rejected(package_root, "outside the supported text command fence")

    def test_requires_each_current_mcp_setting_in_every_authoritative_surface(self) -> None:
        for relative_path in AUTHORITATIVE_MCP_SURFACES:
            for token in REQUIRED_MCP_SETTINGS:
                with self.subTest(path=relative_path, token=token):
                    temporary_directory, package_root = self.make_package()
                    with temporary_directory:
                        self.replace_all(package_root / relative_path, token, "REMOVED_SETTING")
                        self.assert_mutation_is_rejected(package_root, f"{relative_path} must use {token}")

    def test_requires_each_current_mcp_setting_in_the_configure_helper(self) -> None:
        for contract_token, source_token in HELPER_MCP_SETTINGS:
            with self.subTest(token=contract_token):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    self.replace_all(package_root / "scripts" / "configure-unreal-mcp.py", source_token, "REMOVED_SETTING")
                    self.assert_mutation_is_rejected(package_root, f"scripts/configure-unreal-mcp.py must use {contract_token}")

    def test_rejects_each_legacy_mcp_setting_in_policy_surfaces(self) -> None:
        for token in LEGACY_MCP_SETTINGS:
            with self.subTest(token=token):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    policy = package_root / "SKILL.md"
                    policy.write_text(policy.read_text(encoding="utf-8") + f"\nLegacy: {token}\n", encoding="utf-8")
                    self.assert_mutation_is_rejected(package_root, f"legacy MCP setting {token}")

    def test_rejects_each_missing_configure_helper_protocol_or_status_token(self) -> None:
        for token in HELPER_CONTRACT_TOKENS:
            with self.subTest(token=token):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    self.replace_all(package_root / "scripts" / "configure-unreal-mcp.py", token, "REMOVED_HELPER_TOKEN")
                    self.assert_mutation_is_rejected(package_root, f"configure helper protocol/status contract is incomplete: {token}")

    def test_rejects_each_forbidden_tutorial_phrase(self) -> None:
        for phrase in FORBIDDEN_TUTORIAL_CONTENT:
            with self.subTest(phrase=phrase):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    workflow = package_root / "references" / "configure-workflow.md"
                    workflow.write_text(workflow.read_text(encoding="utf-8") + f"\n{phrase}\n", encoding="utf-8")
                    self.assert_mutation_is_rejected(package_root, f"tutorial content is forbidden")
                    self.assert_mutation_is_rejected(package_root, phrase)

    def test_rejects_each_client_example_schema(self) -> None:
        for relative_path, client in EXAMPLE_SCHEMAS:
            with self.subTest(path=relative_path):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    path = package_root / relative_path
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["unexpected"] = True
                    path.write_text(json.dumps(data), encoding="utf-8")
                    self.assert_mutation_is_rejected(package_root, f"{client} example")

    def test_rejects_each_missing_required_eval_scenario(self) -> None:
        for scenario in EVAL_SCENARIOS:
            with self.subTest(scenario=scenario):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    eval_path = package_root / "evals" / "evals.json"
                    data = json.loads(eval_path.read_text(encoding="utf-8"))
                    for item in data["evals"]:
                        item["prompt"] = item["prompt"].replace(scenario, "REMOVED_SCENARIO")
                    eval_path.write_text(json.dumps(data), encoding="utf-8")
                    self.assert_mutation_is_rejected(package_root, f"evals must include scenario: {scenario}")

    def test_rejects_invalid_eval_external_object_shapes(self) -> None:
        for name, mutate in (
            ("top-level", lambda data: data.update({"unexpected": True})),
            ("eval-object", lambda data: data["evals"][0].update({"unexpected": True})),
        ):
            with self.subTest(shape=name):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    eval_path = package_root / "evals" / "evals.json"
                    data = json.loads(eval_path.read_text(encoding="utf-8"))
                    mutate(data)
                    eval_path.write_text(json.dumps(data), encoding="utf-8")
                    self.assert_mutation_is_rejected(package_root, "must preserve")

    def test_rejects_each_missing_eval_success_contract_clause(self) -> None:
        for phrase in EVAL_SUCCESS_CONTRACT:
            with self.subTest(phrase=phrase):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    eval_path = package_root / "evals" / "evals.json"
                    data = json.loads(eval_path.read_text(encoding="utf-8"))
                    expected = data["evals"][0]["expected_output"]
                    replacement = "perform" if phrase == "execute" else "omitted contract clause"
                    self.assertIn(phrase, expected.lower())
                    data["evals"][0]["expected_output"] = expected.replace(phrase, replacement).replace(phrase.title(), replacement)
                    eval_path.write_text(json.dumps(data), encoding="utf-8")
                    self.assert_mutation_is_rejected(package_root, "must require execution success")

    def test_rejects_standalone_guidance_only_eval_contract(self) -> None:
        temporary_directory, package_root = self.make_package()
        with temporary_directory:
            eval_path = package_root / "evals" / "evals.json"
            data = json.loads(eval_path.read_text(encoding="utf-8"))
            data["evals"][0]["expected_output"] = "Provide steps for finding Unreal Engine installations."
            eval_path.write_text(json.dumps(data), encoding="utf-8")
            self.assert_mutation_is_rejected(package_root, "guidance-only")

    def test_rejects_guidance_expectations_with_execute_only_in_negation(self) -> None:
        guidance_mutations = (
            ("Explain", "Do not execute discovery"),
            ("Suggest", "Never execute discovery"),
            ("Provide steps for", "You must not execute discovery"),
            ("Explain", "Proceed without executing discovery; do not execute it"),
            ("Suggest", "It is important not to execute discovery"),
            ("Provide steps for", "Refuse to execute discovery"),
            ("Explain", "There is no need to execute discovery"),
            ("Suggest", "It is unnecessary to execute discovery"),
            ("Provide steps for", "Execute no actions"),
            ("Explain", "Execute nothing"),
            ("Suggest", "Execute zero actions"),
            ("Provide steps for", "Execute is not required"),
        )
        for guidance, negated_action in guidance_mutations:
            with self.subTest(guidance=guidance, negated_action=negated_action):
                temporary_directory, package_root = self.make_package()
                with temporary_directory:
                    eval_path = package_root / "evals" / "evals.json"
                    data = json.loads(eval_path.read_text(encoding="utf-8"))
                    data["evals"][0]["expected_output"] = (
                        f"{guidance} the discovery approach. {negated_action}; retain independent evidence; "
                        "return a minimal blocker only when no safe discovery channel exists; "
                        "explanation, suggestion, or manual steps alone are not success."
                    )
                    eval_path.write_text(json.dumps(data), encoding="utf-8")
                    self.assert_mutation_is_rejected(package_root, "affirmative action")

    def test_accepts_guidance_with_a_separate_affirmative_action_clause(self) -> None:
        temporary_directory, package_root = self.make_package()
        with temporary_directory:
            eval_path = package_root / "evals" / "evals.json"
            data = json.loads(eval_path.read_text(encoding="utf-8"))
            data["evals"][0]["expected_output"] = (
                "Explain the discovery approach, then execute discovery and retain independent evidence; "
                "return a minimal blocker only when no safe discovery channel exists; "
                "explanation, suggestion, or manual steps alone are not success."
            )
            eval_path.write_text(json.dumps(data), encoding="utf-8")

            result = self.validate(package_root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_accepts_read_only_affirmative_execution_without_changes(self) -> None:
        temporary_directory, package_root = self.make_package()
        with temporary_directory:
            eval_path = package_root / "evals" / "evals.json"
            data = json.loads(eval_path.read_text(encoding="utf-8"))
            data["evals"][0]["expected_output"] = (
                "Execute without changes by inspecting current state and retain independent evidence; "
                "return a minimal blocker only when no safe read-only channel exists; "
                "explanation, suggestion, or manual steps alone are not success."
            )
            eval_path.write_text(json.dumps(data), encoding="utf-8")

            result = self.validate(package_root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
