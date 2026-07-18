"""Regression tests for the Unreal MCP project configuration writer."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(os.environ.get("UNREAL_MCP_CONFIGURE_SCRIPT", REPOSITORY_ROOT / "scripts" / "configure-unreal-mcp.py"))


def load_configure_module():
    spec = importlib.util.spec_from_file_location("configure_unreal_mcp", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConfigureUnrealMcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.configure = load_configure_module()

    def make_project(self, root: Path, contents: str = "{}\n") -> Path:
        uproject = root / "Sample.uproject"
        uproject.write_text(contents, encoding="utf-8")
        return uproject

    def test_writes_project_default_editor_settings_with_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)

            self.configure.configure_editor_settings(project_root, 8123, dry_run=False)

            settings_path = project_root / "Config" / "DefaultEditorPerProjectUserSettings.ini"
            self.assertTrue(settings_path.exists())
            self.assertFalse((project_root / "Config" / "DefaultEngine.ini").exists())
            self.assertEqual(
                settings_path.read_text(encoding="utf-8").splitlines(),
                [
                    "[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]",
                    "bAutoStartServer=True",
                    "ServerPortNumber=8123",
                    "ServerUrlPath=/mcp",
                    "bEnableToolSearch=True",
                ],
            )

    def test_existing_default_engine_ini_is_unchanged_when_editor_settings_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            engine_ini = project_root / "Config" / "DefaultEngine.ini"
            engine_ini.parent.mkdir()
            sentinel = b"\xef\xbb\xbf[ExistingSection]\r\nSentinel=unchanged\r\n"
            engine_ini.write_bytes(sentinel)

            self.configure.configure_editor_settings(project_root, 8123, dry_run=False)

            self.assertEqual(engine_ini.read_bytes(), sentinel)
            self.assertTrue((project_root / "Config" / "DefaultEditorPerProjectUserSettings.ini").exists())

    def test_updates_existing_mcp_settings_without_duplicates_or_unrelated_loss(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            settings_path = project_root / "Config" / "DefaultEditorPerProjectUserSettings.ini"
            settings_path.parent.mkdir()
            settings_path.write_text(
                "[OtherSection]\nOtherKey=preserved\n\n"
                "[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]\n"
                "ServerPortNumber=7000\nServerPortNumber=7001\n"
                "ServerURLPath=/legacy\nbAutoStartServer=False\n\n[LaterSection]\nLaterKey=preserved\n",
                encoding="utf-8",
            )

            self.configure.configure_editor_settings(project_root, 8123, dry_run=False)

            lines = settings_path.read_text(encoding="utf-8").splitlines()
            self.assertIn("OtherKey=preserved", lines)
            self.assertIn("LaterKey=preserved", lines)
            self.assertEqual(lines.count("ServerPortNumber=8123"), 1)
            self.assertEqual(sum(line.startswith("ServerPortNumber=") for line in lines), 1)
            self.assertEqual(lines.count("bAutoStartServer=True"), 1)
            self.assertEqual(lines.count("ServerUrlPath=/mcp"), 1)
            self.assertNotIn("ServerURLPath=/legacy", lines)
            self.assertEqual(lines.count("bEnableToolSearch=True"), 1)

    def test_dry_run_writes_no_project_or_client_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            uproject = self.make_project(project_root)

            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "all", "--dry-run"],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(project_root.iterdir()), [uproject])

    def test_client_descriptors_use_the_official_schema_and_preserve_json_merges(self) -> None:
        expected_clients = {
            "claude": (".mcp.json", "mcpServers", {"type": "http", "url": "http://127.0.0.1:8123/mcp", "disabled": False}),
            "cursor": (".cursor/mcp.json", "mcpServers", {"url": "http://127.0.0.1:8123/mcp"}),
            "vscode": (".vscode/mcp.json", "servers", {"type": "http", "url": "http://127.0.0.1:8123/mcp"}),
            "gemini": (".gemini/settings.json", "mcpServers", {"httpUrl": "http://127.0.0.1:8123/mcp"}),
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            url = "http://127.0.0.1:8123/mcp"
            for client, (relative_path, root_key, expected_server) in expected_clients.items():
                config_path = project_root / relative_path
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(
                    json.dumps({"unrelatedTopLevel": client, root_key: {"other-server": {"command": "keep"}}}),
                    encoding="utf-8",
                )

                self.configure.configure_client(project_root, client, url, dry_run=False)

                config = json.loads(config_path.read_text(encoding="utf-8"))
                self.assertEqual(config["unrelatedTopLevel"], client)
                self.assertEqual(config[root_key]["other-server"], {"command": "keep"})
                self.assertEqual(config[root_key]["unreal-mcp"], expected_server)

            self.configure.configure_client(project_root, "codex", url, dry_run=False)
            self.assertEqual(
                (project_root / ".codex" / "config.toml").read_text(encoding="utf-8"),
                '[mcp_servers.unreal-mcp]\nurl = "http://127.0.0.1:8123/mcp"\n',
            )

    def test_existing_codex_config_blocks_all_selected_target_writes_without_manual_edit_advice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            original_uproject = '{"Plugins": [{"Name": "Existing", "Enabled": true}]}\n'
            uproject = self.make_project(project_root, original_uproject)
            codex_path = project_root / ".codex" / "config.toml"
            codex_path.parent.mkdir()
            codex_path.write_text("[mcp_servers.other]\nurl = \"http://keep\"\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "all"],
                capture_output=True,
                text=True,
                check=False,
            )

            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("protected configuration blocker", output.lower())
            self.assertNotIn("delete or edit", output.lower())
            self.assertEqual(uproject.read_text(encoding="utf-8"), original_uproject)
            self.assertFalse((project_root / "Config").exists())
            self.assertFalse((project_root / ".mcp.json").exists())
            self.assertFalse((project_root / ".cursor").exists())
            self.assertFalse((project_root / ".vscode").exists())
            self.assertFalse((project_root / ".gemini").exists())


if __name__ == "__main__":
    unittest.main()
