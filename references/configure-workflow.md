# Unreal MCP Configure Workflow

Use this reference when handling `/unreal-mcp:configure <client>`.

The configure command is an automatic project setup workflow. Resolve, inspect, dry-run, write, recover the editor connection, and verify. Do not merely ask whether the user wants guidance, and do not substitute instructions for any step the agent can execute.

## Command

The agent invokes this workflow for the canonical configure command. The bundled helper is implementation support for agent automation.

```bash
python scripts/configure-unreal-mcp.py -ProjectPath "/path/to/Project" -Target all -Port 8000 -DryRun
```

Targets are `claude`, `codex`, `cursor`, `vscode`, `gemini`, and `all`.

Important switches:

- `-DryRun` or `--dry-run`: print planned file changes without writing. Use this first.
- `-EnablePlugins` or `--enable-plugins`: retained for compatibility; core plugins and the selected Toolset profile are enabled by default.
- `-AutoStart` or `--auto-start`: retained for compatibility; Auto Start defaults are written by default.
- `-ToolsetProfile core|common|all` or `--toolset-profile core|common|all`: choose which Toolset plugin set to enable. Default is `common`.
- `--skip-enable-plugins`: skip `.uproject` plugin edits.
- `--skip-auto-start`: skip `Config/DefaultEditorPerProjectUserSettings.ini` MCP settings edits.
- `-Verify` or `--verify`: try a short HTTP request to `http://127.0.0.1:<Port>/mcp`.
- `-Target <client>` or `--target <client>`: selects the client config to write. Every target also configures the UE project by default.
- `-Target all` or `--target all`: configures the UE project and all supported clients.

The script is Python and cross-platform. It accepts the UE-style `-ProjectPath`, `-Target`, `-Port`, `-DryRun`, `-EnablePlugins`, `-AutoStart`, and `-Verify` flags, plus lowercase GNU-style aliases.

## What The Script Changes

- Resolves exactly one `.uproject` from `-ProjectPath`.
- Enables the core Unreal MCP plugins: `ModelContextProtocol` and `ToolsetRegistry`.
- Enables the default `common` Toolset profile: `EditorToolset`, `AutomationTestToolset`, and `LiveCodingToolset`.
- Writes shared defaults in `Config/DefaultEditorPerProjectUserSettings.ini`, section `/Script/ModelContextProtocolEngine.ModelContextProtocolSettings`, for Auto Start, port, `ServerUrlPath`, and Tool Search.
- Merges JSON client configs for Claude Code, Cursor, VS Code, and Gemini without deleting existing MCP servers.
- Creates Codex `.codex/config.toml` only when it does not already exist.

The target client does not limit project setup. For example, `-Target codex` still enables the core UE plugins, the common Toolset plugins, and Auto Start defaults before creating `.codex/config.toml`.

## Toolset Profiles

- `core`: enable only `ModelContextProtocol` and `ToolsetRegistry`. Use this when the user wants the smallest transport/discovery footprint.
- `common`: enable `core` plus `EditorToolset`, `AutomationTestToolset`, and `LiveCodingToolset`. This is the default because it covers the most common editor state, logs, scene, asset, Blueprint, automation-test, and C++ iteration workflows.
- `all`: enable `core` plus `AllToolsets`. Use only for broad discovery/prototyping when the larger startup and schema surface is acceptable.

## Agent Execution Rules

1. Resolve the project from the explicit `-ProjectPath`, the current workspace root, or an exact `.uproject` path. Ask only if no single project can be identified.
2. Run dry-run first and summarize the exact files to be changed.
3. Run the real configure command automatically when the user requested `/unreal-mcp:configure`, opening an MCP-enabled project, or fixing a missing MCP connection.
4. Stop instead of writing when dry-run reveals an ambiguous project, an existing Codex config for a Codex target, or edits outside the intended project root.
5. After writing, use the dirty-state restart gate below and verify through `list_toolsets` once the MCP server is reachable.

## Automated Save/Restart Gate

Configuration commonly changes `.uproject` plugin entries, Toolset plugin entries, and `Config/DefaultEditorPerProjectUserSettings.ini`. Unreal may not load those changes until the project is reopened. Shared defaults do not overwrite an existing `Saved/Config/*Editor/EditorPerProjectUserSettings.ini`; the agent must not mutate that user file automatically.

After a successful write:

1. Record the changed files and determine whether plugin loading or reflected API changes require restart.
2. Discover a read-only dirty/unsaved-state operation from the live Toolset schema. Require coverage of all dirty packages/assets and the current map; do not assume a fixed tool name.
3. Match the editor process to the project, then immediately recheck full dirty state before a graceful close. If clean, restart automatically, wait for readiness, and reconnect; never escalate a close timeout to force-kill.
4. If unsaved state exists, request save/discard permission or ask for only that action and confirmation that restart is safe, then continue automatically.
5. If bounded filesystem, process, port, log, and editor-control checks cannot prove dirty-state, issue one minimal blocker for the entire restart attempt. Never infer a clean editor.
6. After launch/restart, verify the endpoint, `LogModelContextProtocol`, `list_toolsets`, the required schema, and the original requested operation.

After the core connection is configured, enable Toolset plugins according to the task. `AllToolsets` is acceptable for broad exploration or prototyping when the user accepts the larger startup and schema surface; otherwise enable the specific domain Toolsets needed and verify them with `list_toolsets`.

## Codex TOML Rule

Codex TOML generation is write-once. An existing `.codex/config.toml` is one protected-configuration authorization blocker; do not overwrite it automatically.

## Recovery When No Editor Control Channel Exists

If shared defaults are ignored, recover the current session through live `ConfigSettingsToolset`, editor control or console, `ModelContextProtocol.StartServer`, or launch flags. Independently read back the effective state before retrying discovery. If `list_toolsets` is absent but native Toolset operations or schemas are exposed, classify the session as Tool Search disabled/eager mode; prefer restoring `bEnableToolSearch=True`, or use the live native schemas when changing it is unsafe.

## Verification

After configuration:

1. Launch/restart through the dirty-state gate above.
2. Confirm Output Log includes `LogModelContextProtocol` startup messages.
3. Call `list_toolsets`; if it is absent but native Toolset operations or schemas are exposed, verify and use that eager-mode surface.
4. If neither discovery surface is available, run `ModelContextProtocol.RefreshTools`, reconnect, and inspect `LogModelContextProtocol`.

