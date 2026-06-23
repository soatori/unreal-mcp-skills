#!/usr/bin/env python3
"""Configure Epic Unreal MCP client files for a UE project."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


CLIENTS = ("claude", "codex", "cursor", "vscode", "gemini")
CORE_PLUGINS = ("ModelContextProtocol", "ToolsetRegistry")
COMMON_TOOLSET_PLUGINS = ("EditorToolset", "AutomationTestToolset", "LiveCodingToolset")
ALL_TOOLSET_PLUGINS = ("AllToolsets",)
INI_SECTION = "/Script/ModelContextProtocol.ModelContextProtocolSettings"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure Unreal MCP for agent clients.")
    parser.add_argument("-ProjectPath", "--project-path", default=".", help="UE project root or .uproject path.")
    parser.add_argument(
        "-Target",
        "--target",
        choices=(*CLIENTS, "all"),
        default="all",
        help="Client target to configure.",
    )
    parser.add_argument("-Port", "--port", type=int, default=8000, help="Unreal MCP server port.")
    parser.add_argument("-AutoStart", "--auto-start", action="store_true", help="Write Auto Start defaults. Default behavior already writes them.")
    parser.add_argument("-EnablePlugins", "--enable-plugins", action="store_true", help="Enable core MCP plugins. Default behavior already enables them.")
    parser.add_argument(
        "-ToolsetProfile",
        "--toolset-profile",
        choices=("core", "common", "all"),
        default="common",
        help="Toolset plugin profile to enable with the core MCP plugins.",
    )
    parser.add_argument("--skip-auto-start", action="store_true", help="Do not write Auto Start defaults.")
    parser.add_argument("--skip-enable-plugins", action="store_true", help="Do not enable core MCP plugins.")
    parser.add_argument("-Verify", "--verify", action="store_true", help="Probe the MCP endpoint after writing.")
    parser.add_argument("-DryRun", "--dry-run", action="store_true", help="Print planned changes without writing.")
    return parser.parse_args()


def fail(message: str) -> None:
    raise RuntimeError(message)


def resolve_uproject(project_path: str) -> Path:
    path = Path(project_path).expanduser().resolve()
    if path.is_dir():
        projects = sorted(path.glob("*.uproject"))
        if not projects:
            fail(f"No .uproject file found in '{path}'. Pass a UE project root or .uproject file.")
        if len(projects) > 1:
            names = ", ".join(project.name for project in projects)
            fail(f"Multiple .uproject files found in '{path}': {names}. Pass the exact .uproject path.")
        return projects[0]
    if path.suffix != ".uproject":
        fail("ProjectPath must point to a UE project directory or .uproject file.")
    if not path.exists():
        fail(f"ProjectPath does not exist: {path}")
    return path


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        fail(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def show_plan(message: str, dry_run: bool) -> None:
    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}{message}")


def plugin_names_for_profile(profile: str) -> tuple[str, ...]:
    if profile == "core":
        return CORE_PLUGINS
    if profile == "common":
        return (*CORE_PLUGINS, *COMMON_TOOLSET_PLUGINS)
    if profile == "all":
        return (*CORE_PLUGINS, *ALL_TOOLSET_PLUGINS)
    fail(f"Unsupported Toolset profile: {profile}")


def enable_uproject_plugins(uproject: Path, plugin_names: tuple[str, ...], dry_run: bool) -> None:
    project = read_json(uproject)
    plugins = project.get("Plugins")
    if plugins is None:
        plugins = []
    if not isinstance(plugins, list):
        fail(f"Plugins must be an array in {uproject}")

    changed = False
    for plugin_name in plugin_names:
        entry = next((item for item in plugins if isinstance(item, dict) and item.get("Name") == plugin_name), None)
        if entry is None:
            plugins.append({"Name": plugin_name, "Enabled": True})
            changed = True
        elif entry.get("Enabled") is not True:
            entry["Enabled"] = True
            changed = True

    if changed:
        project["Plugins"] = plugins
        show_plan(f"Enable {', '.join(plugin_names)} in {uproject}", dry_run)
        write_json(uproject, project, dry_run)
    else:
        print(f"Requested plugins already enabled in {uproject}")


def set_ini_value(lines: list[str], section: str, key: str, value: str) -> None:
    section_line = f"[{section}]"
    section_index = next((i for i, line in enumerate(lines) if line.strip() == section_line), -1)
    if section_index < 0:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([section_line, f"{key}={value}"])
        return

    insert_at = len(lines)
    for index in range(section_index + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            insert_at = index
            break
        if lines[index].split("=", 1)[0].strip() == key and "=" in lines[index]:
            lines[index] = f"{key}={value}"
            return
    lines.insert(insert_at, f"{key}={value}")


def configure_editor_settings(project_root: Path, port: int, dry_run: bool) -> None:
    engine_ini = project_root / "Config" / "DefaultEngine.ini"
    lines = engine_ini.read_text(encoding="utf-8").splitlines() if engine_ini.exists() else []

    set_ini_value(lines, INI_SECTION, "bAutoStartServer", "True")
    set_ini_value(lines, INI_SECTION, "ServerPortNumber", str(port))
    set_ini_value(lines, INI_SECTION, "ServerURLPath", "/mcp")
    set_ini_value(lines, INI_SECTION, "bEnableToolSearch", "True")

    show_plan(f"Configure Unreal MCP editor settings in {engine_ini}", dry_run)
    if not dry_run:
        engine_ini.parent.mkdir(parents=True, exist_ok=True)
        engine_ini.write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_mcp_json_config(path: Path, server_entry: dict[str, Any], dry_run: bool) -> None:
    config = read_json(path)
    servers = config.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        fail(f"mcpServers must be an object in {path}")
    servers["unreal-mcp"] = server_entry
    show_plan(f"Merge unreal-mcp server into {path}", dry_run)
    write_json(path, config, dry_run)


def write_codex_config(path: Path, url: str, dry_run: bool) -> None:
    if path.exists():
        fail(
            f"Codex config already exists at '{path}'. UE's Codex TOML generation is write-once; "
            "delete or edit the stale file manually before regenerating."
        )
    show_plan(f"Create Codex MCP config at {path}", dry_run)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'[mcp_servers.unreal-mcp]\nurl = "{url}"\n', encoding="utf-8")


def configure_client(project_root: Path, client: str, url: str, dry_run: bool) -> None:
    if client == "claude":
        merge_mcp_json_config(project_root / ".mcp.json", {"type": "http", "url": url, "disabled": False}, dry_run)
    elif client == "cursor":
        merge_mcp_json_config(project_root / ".cursor" / "mcp.json", {"url": url}, dry_run)
    elif client == "vscode":
        merge_mcp_json_config(project_root / ".vscode" / "mcp.json", {"url": url}, dry_run)
    elif client == "gemini":
        merge_mcp_json_config(project_root / ".gemini" / "settings.json", {"httpUrl": url}, dry_run)
    elif client == "codex":
        write_codex_config(project_root / ".codex" / "config.toml", url, dry_run)
    else:
        fail(f"Unsupported client: {client}")


def editor_client_name(target: str) -> str:
    return {
        "claude": "ClaudeCode",
        "codex": "Codex",
        "cursor": "Cursor",
        "vscode": "VSCode",
        "gemini": "Gemini",
        "all": "All",
    }[target]


def verify_server(url: str, project_root: Path, port: int) -> None:
    print()
    print(f"Verifying {url} ...")
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            print(f"Server responded with HTTP {response.status}. Launch the agent from '{project_root}' and call list_toolsets.")
    except (urllib.error.URLError, TimeoutError, OSError):
        print(
            f"No HTTP response from {url}. Start the UE editor, enable Auto Start or run "
            f"ModelContextProtocol.StartServer {port}, then reconnect the agent."
        )


def main() -> int:
    args = parse_args()
    if not 1 <= args.port <= 65535:
        fail("Port must be in range 1..65535.")

    uproject = resolve_uproject(args.project_path)
    project_root = uproject.parent
    server_url = f"http://127.0.0.1:{args.port}/mcp"
    clients = list(CLIENTS) if args.target == "all" else [args.target]

    print(f"UE project: {uproject}")
    print(f"Target: {args.target}")
    print(f"Server URL: {server_url}")
    print(f"Toolset profile: {args.toolset_profile}")

    codex_path = project_root / ".codex" / "config.toml"
    if "codex" in clients and codex_path.exists():
        fail(
            f"Codex config already exists at '{codex_path}'. UE's Codex TOML generation is write-once; "
            "delete or edit the stale file manually before regenerating. No changes were written."
        )

    if not args.skip_enable_plugins:
        enable_uproject_plugins(uproject, plugin_names_for_profile(args.toolset_profile), args.dry_run)
    else:
        print("Plugin changes skipped by --skip-enable-plugins.")

    if not args.skip_auto_start:
        configure_editor_settings(project_root, args.port, args.dry_run)
        print(
            "Editor settings are written as project defaults. If UE ignores a setting name in this engine version, "
            "set Auto Start Server in Editor Preferences > General > Model Context Protocol."
        )
    else:
        print("Auto Start changes skipped by --skip-auto-start.")

    for client in clients:
        configure_client(project_root, client, server_url, args.dry_run)

    print()
    print("Editor console fallback:")
    print(f"  ModelContextProtocol.StartServer {args.port}")
    print(f"  ModelContextProtocol.GenerateClientConfig {editor_client_name(args.target)}")
    print()
    print("Post-configure next step:")
    print("  Save the UE project before restart.")
    print("  Ask whether to launch/restart the editor now or let the user restart manually.")
    print("  Do not terminate a running Unreal Editor process without explicit confirmation.")

    if args.verify:
        verify_server(server_url, project_root, args.port)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
