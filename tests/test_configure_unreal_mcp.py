"""Regression tests for the Unreal MCP project configuration writer."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(os.environ.get("UNREAL_MCP_CONFIGURE_SCRIPT", REPOSITORY_ROOT / "scripts" / "configure-unreal-mcp.py"))


def load_configure_module():
    spec = importlib.util.spec_from_file_location("configure_unreal_mcp", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def mock_mcp_server(status: int, body: bytes, content_type: str | None = "application/json") -> Iterator[tuple[str, dict[str, object]]]:
    received: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - HTTP handler convention
            received["method"] = self.command
            received["path"] = self.path
            received["headers"] = dict(self.headers.items())
            received["body"] = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(status)
            if content_type is not None:
                self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/mcp", received
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class ConfigureUnrealMcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.configure = load_configure_module()

    def make_project(self, root: Path, contents: str = "{}\n") -> Path:
        uproject = root / "Sample.uproject"
        uproject.write_text(contents, encoding="utf-8")
        return uproject

    def make_symlink_or_skip(self, link: Path, target: Path, *, is_directory: bool) -> None:
        try:
            link.symlink_to(target, target_is_directory=is_directory)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"platform refused temporary symlink creation: {exc}")

    def run_configure(self, uproject: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_project_target_containment_rejects_a_direct_escape_deterministically(self) -> None:
        guard = getattr(self.configure, "require_project_target", None)
        self.assertIsNotNone(guard, "configure helper must expose the project target containment guard")
        if guard is None:
            return
        with tempfile.TemporaryDirectory() as project_directory, tempfile.TemporaryDirectory() as outside_directory:
            with self.assertRaisesRegex(RuntimeError, "containment blocker"):
                guard(Path(project_directory), Path(outside_directory) / "escaped.json")

    def test_file_destination_symlink_escape_blocks_before_any_selected_write(self) -> None:
        with tempfile.TemporaryDirectory() as project_directory, tempfile.TemporaryDirectory() as outside_directory:
            project_root = Path(project_directory)
            uproject_original = "{}\n"
            uproject = self.make_project(project_root, uproject_original)
            outside_file = Path(outside_directory) / "outside.json"
            outside_original = '{"outside": "unchanged"}\n'
            outside_file.write_text(outside_original, encoding="utf-8")
            self.make_symlink_or_skip(project_root / ".mcp.json", outside_file, is_directory=False)

            result = self.run_configure(uproject, "--target", "claude")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("containment blocker", (result.stdout + result.stderr).lower())
            self.assertEqual(uproject.read_text(encoding="utf-8"), uproject_original)
            self.assertEqual(outside_file.read_text(encoding="utf-8"), outside_original)
            self.assertFalse((project_root / "Config").exists())

    def test_directory_symlink_escapes_are_blocked_across_writer_categories(self) -> None:
        cases = (
            ("editor settings", "Config", ("--target", "claude", "--skip-enable-plugins"), "DefaultEditorPerProjectUserSettings.ini"),
            ("JSON client", ".cursor", ("--target", "cursor", "--skip-enable-plugins", "--skip-auto-start"), "mcp.json"),
            ("Codex TOML", ".codex", ("--target", "codex", "--skip-enable-plugins", "--skip-auto-start"), "config.toml"),
        )
        for category, link_name, arguments, escaped_name in cases:
            with self.subTest(category=category):
                with tempfile.TemporaryDirectory() as project_directory, tempfile.TemporaryDirectory() as outside_directory:
                    project_root = Path(project_directory)
                    uproject = self.make_project(project_root)
                    outside_root = Path(outside_directory)
                    self.make_symlink_or_skip(project_root / link_name, outside_root, is_directory=True)

                    result = self.run_configure(uproject, *arguments)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("containment blocker", (result.stdout + result.stderr).lower())
                    self.assertFalse((outside_root / escaped_name).exists())
                    self.assertEqual(uproject.read_text(encoding="utf-8"), "{}\n")
                    self.assertFalse((project_root / ".mcp.json").exists())

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

    def test_normalizes_repeated_mcp_sections_and_preserves_unmanaged_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            settings_path = project_root / "Config" / "DefaultEditorPerProjectUserSettings.ini"
            settings_path.parent.mkdir()
            settings_path.write_text(
                "; preamble comment\n"
                "[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]\n"
                "; first MCP comment\nFirstUnmanaged=preserved\nServerPortNumber=7000\n\n"
                "[OtherSection]\nOtherKey=preserved\n\n"
                "[/script/modelcontextprotocolengine.modelcontextprotocolsettings]\n"
                "; second MCP comment\nSecondUnmanaged=preserved\n"
                "serverportnumber=9000\nBAUTOSTARTSERVER=False\n"
                "ServerURLPath=/legacy\nServerUrlPath=/stale\nbEnableToolSearch=False\n",
                encoding="utf-8",
            )

            self.configure.configure_editor_settings(project_root, 8123, dry_run=False)

            lines = settings_path.read_text(encoding="utf-8").splitlines()
            section = f"[{self.configure.INI_SECTION}]".casefold()
            self.assertEqual(sum(line.strip().casefold() == section for line in lines), 1)
            for key, expected in (
                ("bAutoStartServer", "bAutoStartServer=True"),
                ("ServerPortNumber", "ServerPortNumber=8123"),
                ("ServerUrlPath", "ServerUrlPath=/mcp"),
                ("bEnableToolSearch", "bEnableToolSearch=True"),
            ):
                self.assertEqual(sum(line.partition("=")[0].strip().casefold() == key.casefold() for line in lines), 1)
                self.assertIn(expected, lines)
            self.assertFalse(any(line.partition("=")[0].strip() == "ServerURLPath" for line in lines))
            for preserved in (
                "; preamble comment",
                "; first MCP comment",
                "FirstUnmanaged=preserved",
                "[OtherSection]",
                "OtherKey=preserved",
                "; second MCP comment",
                "SecondUnmanaged=preserved",
            ):
                self.assertIn(preserved, lines)

    def test_normalizes_a_bom_prefixed_first_mcp_section_and_preserves_the_bom(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            settings_path = project_root / "Config" / "DefaultEditorPerProjectUserSettings.ini"
            settings_path.parent.mkdir()
            settings_path.write_bytes(
                b"\xef\xbb\xbf"
                + (
                    "[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]\n"
                    "; BOM section comment\nUnmanaged=preserved\nServerPortNumber=7000\n"
                    "[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]\n"
                    "bAutoStartServer=False\nServerURLPath=/legacy\n"
                ).encode("utf-8")
            )

            self.configure.configure_editor_settings(project_root, 8123, dry_run=False)

            output = settings_path.read_bytes()
            self.assertTrue(output.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM must be preserved")
            text = output.decode("utf-8-sig")
            lines = text.splitlines()
            self.assertEqual(lines.count(f"[{self.configure.INI_SECTION}]"), 1)
            self.assertIn("; BOM section comment", lines)
            self.assertIn("Unmanaged=preserved", lines)
            self.assertEqual(lines.count("ServerPortNumber=8123"), 1)
            self.assertEqual(lines.count("bAutoStartServer=True"), 1)
            self.assertEqual(lines.count("ServerUrlPath=/mcp"), 1)
            self.assertNotIn("ServerURLPath=/legacy", lines)

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

    def test_verify_posts_initialize_request_with_required_headers_and_accepts_direct_json(self) -> None:
        response = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        with tempfile.TemporaryDirectory() as temporary_directory, mock_mcp_server(200, response) as (url, received):
            outcome = self.configure.verify_server(url, Path(temporary_directory), 8000)

        self.assertTrue(outcome.ok, outcome.evidence)
        self.assertEqual(received["method"], "POST")
        self.assertEqual(received["path"], "/mcp")
        self.assertEqual(json.loads(received["body"]), {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "unreal-mcp-configure", "version": "1.0"},
            },
        })
        headers = {key.lower(): value for key, value in received["headers"].items()}
        self.assertEqual(headers["content-type"], "application/json")
        self.assertIn("application/json", headers["accept"])
        self.assertIn("text/event-stream", headers["accept"])

    def test_verify_bypasses_environment_proxy_for_loopback_endpoint(self) -> None:
        success = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        with tempfile.TemporaryDirectory() as temporary_directory:
            with mock_mcp_server(200, success) as (target_url, target_received):
                with mock_mcp_server(502, b"proxy intercepted request") as (proxy_url, proxy_received):
                    proxy_origin = proxy_url.removesuffix("/mcp")
                    proxy_environment = {
                        "HTTP_PROXY": proxy_origin,
                        "HTTPS_PROXY": proxy_origin,
                        "NO_PROXY": "",
                        "no_proxy": "",
                    }
                    with mock.patch.dict(os.environ, proxy_environment), mock.patch.object(
                        self.configure.urllib.request, "_opener", None
                    ):
                        outcome = self.configure.verify_server(target_url, Path(temporary_directory), 8000)

        self.assertTrue(outcome.ok, f"loopback request inherited environment proxy: {outcome.evidence}")
        self.assertEqual(target_received["path"], "/mcp")
        self.assertEqual(proxy_received, {})

    def test_verify_accepts_first_sse_data_payload(self) -> None:
        response = b"event: message\ndata: {\"jsonrpc\": \"2.0\", \"id\": 1, \"result\": {\"protocolVersion\": \"2025-11-25\"}}\n\n"
        with tempfile.TemporaryDirectory() as temporary_directory, mock_mcp_server(200, response, "text/event-stream") as (url, _):
            outcome = self.configure.verify_server(url, Path(temporary_directory), 8000)

        self.assertTrue(outcome.ok, outcome.evidence)

    def test_verify_accepts_only_parameterized_json_and_sse_media_types(self) -> None:
        json_response = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        sse_response = b'data: {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}\n\n'
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            for content_type, response in (
                ("application/json; charset=utf-8", json_response),
                ("text/event-stream; charset=utf-8", sse_response),
            ):
                with self.subTest(content_type=content_type), mock_mcp_server(200, response, content_type) as (url, _):
                    outcome = self.configure.verify_server(url, project_root, 8000)
                    self.assertTrue(outcome.ok, outcome.evidence)

    def test_verify_rejects_missing_plain_and_other_media_types(self) -> None:
        response = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            for content_type in (None, "text/plain", "application/xml"):
                with self.subTest(content_type=content_type), mock_mcp_server(200, response, content_type) as (url, _):
                    outcome = self.configure.verify_server(url, project_root, 8000)
                    self.assertFalse(outcome.ok)
                    self.assertIn("content-type", outcome.evidence.lower())

    def test_verify_rejects_malformed_json_and_json_rpc_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            with mock_mcp_server(200, b"not-json") as (url, _):
                malformed = self.configure.verify_server(url, project_root, 8000)
            error_response = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32600}}).encode()
            with mock_mcp_server(200, error_response) as (url, _):
                rpc_error = self.configure.verify_server(url, project_root, 8000)

        self.assertFalse(malformed.ok)
        self.assertIn("malformed", malformed.evidence.lower())
        self.assertFalse(rpc_error.ok)
        self.assertIn("json-rpc error", rpc_error.evidence.lower())

    def test_verify_rejects_http_error_and_connection_failure(self) -> None:
        response = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            with mock_mcp_server(503, response) as (url, _):
                http_error = self.configure.verify_server(url, project_root, 8000)
            opener = mock.Mock()
            opener.open.side_effect = self.configure.urllib.error.URLError("connection refused")
            with mock.patch.object(self.configure.urllib.request, "build_opener", return_value=opener):
                refused = self.configure.verify_server("http://127.0.0.1:9/mcp", project_root, 9)

        self.assertFalse(http_error.ok)
        self.assertIn("http 503", http_error.evidence.lower())
        self.assertFalse(refused.ok)
        self.assertIn("connection", refused.evidence.lower())

    def test_cli_real_run_statuses_cover_configured_verified_recovery_and_protected_blocker(self) -> None:
        success = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            uproject = self.make_project(project_root)

            configured = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "claude"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(configured.returncode, 0, configured.stderr)
            self.assertIn("status: configured", configured.stdout)

            with mock_mcp_server(200, success) as (url, _):
                port = url.split(":")[2].split("/")[0]
                verified = subprocess.run(
                    [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "cursor", "--port", port, "--verify"],
                    capture_output=True, text=True, check=False,
                )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertIn("status: verified", verified.stdout)

            failure_port = 9
            recovery = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "vscode", "--port", str(failure_port), "--verify"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(recovery.returncode, 2, recovery.stderr)
            self.assertIn("status: configured-but-recovery-required", recovery.stdout)
            self.assertTrue((project_root / ".vscode" / "mcp.json").exists(), "verification failure must not roll back writes")

            codex_path = project_root / ".codex" / "config.toml"
            codex_path.parent.mkdir(exist_ok=True)
            codex_path.write_text("[mcp_servers.other]\nurl = \"http://keep\"\n", encoding="utf-8")
            protected = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "codex"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(protected.returncode, 1)
            self.assertIn("status: protected-config-blocker", protected.stdout + protected.stderr)

    def test_cli_dry_run_verify_probes_without_writes_and_has_recovery_status(self) -> None:
        success = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            uproject = self.make_project(project_root)
            with mock_mcp_server(200, success) as (url, _):
                port = url.split(":")[2].split("/")[0]
                verified = subprocess.run(
                    [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "claude", "--port", port, "--dry-run", "--verify"],
                    capture_output=True, text=True, check=False,
                )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertIn("status: verified", verified.stdout)
            self.assertEqual(list(project_root.iterdir()), [uproject])

            failed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "claude", "--port", "9", "--dry-run", "--verify"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(failed.returncode, 2, failed.stderr)
            self.assertIn("status: dry-run-recovery-required", failed.stdout)
            self.assertEqual(list(project_root.iterdir()), [uproject])

    def test_cli_dry_run_verify_probes_when_codex_config_is_protected(self) -> None:
        success = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-11-25"}}).encode()
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_root = Path(temporary_directory)
            uproject = self.make_project(project_root)
            codex_path = project_root / ".codex" / "config.toml"
            codex_path.parent.mkdir()
            original_config = "[mcp_servers.other]\nurl = \"http://keep\"\n"
            codex_path.write_text(original_config, encoding="utf-8")
            with mock_mcp_server(200, success) as (url, _):
                port = url.split(":")[2].split("/")[0]
                result = subprocess.run(
                    [sys.executable, "-B", str(SCRIPT_PATH), "--project-path", str(uproject), "--target", "codex", "--port", port, "--dry-run", "--verify"],
                    capture_output=True, text=True, check=False,
                )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("status: verified", result.stdout)
            self.assertEqual(codex_path.read_text(encoding="utf-8"), original_config)


if __name__ == "__main__":
    unittest.main()
