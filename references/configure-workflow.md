# Unreal MCP Configure Workflow

Use this reference when handling `/unreal-mcp:configure <target>` or `/ue-mcp:configure <target>`.

The configure command is an automatic project setup workflow. Do not merely ask whether the user wants guidance. If a UE project root or `.uproject` can be inferred from the current workspace or the user's request, run the dry-run, report the planned files, then run the real configuration unless a blocker appears.

## Command

The agent should invoke this workflow for `/unreal-mcp:configure <target>`. The bundled helper is implementation support; ordinary users should call the skill command instead of manually starting the helper.

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
- `--skip-auto-start`: skip `Config/DefaultEngine.ini` MCP settings edits.
- `-Verify` or `--verify`: try a short HTTP request to `http://127.0.0.1:<Port>/mcp`.
- `-Target <client>` or `--target <client>`: selects the client config to write. Every target also configures the UE project by default.
- `-Target all` or `--target all`: configures the UE project and all supported clients.

The script is Python and cross-platform. It accepts the UE-style `-ProjectPath`, `-Target`, `-Port`, `-DryRun`, `-EnablePlugins`, `-AutoStart`, and `-Verify` flags, plus lowercase GNU-style aliases.

## What The Script Changes

- Resolves exactly one `.uproject` from `-ProjectPath`.
- Enables the core Unreal MCP plugins: `ModelContextProtocol` and `ToolsetRegistry`.
- Enables the default `common` Toolset profile: `EditorToolset`, `AutomationTestToolset`, and `LiveCodingToolset`.
- Writes project default settings for Auto Start, port, URL path, and Tool Search.
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
5. After writing, run the save/restart dialog below instead of ending with a one-line manual restart instruction. Verify through `list_toolsets` once the MCP server is reachable.

## Save/Restart Dialog

Configuration commonly changes `.uproject` plugin entries, Toolset plugin entries, and `Config/DefaultEngine.ini`. Unreal may not load those changes until the project is reopened.

After a successful write:

1. Summarize the changed files.
2. Tell the user to save the project before any restart. If MCP is already connected, inspect dirty assets and save only after explicit permission. If MCP is not connected, ask the user to save manually in the editor.
3. Ask: "Should I launch or restart Unreal Editor for this project now, or would you prefer to restart it manually?"
4. If the user chooses agent launch/restart, confirm the editor executable and project path. Use `references/find-editor-installations.md` when the editor path is unknown. Do not terminate a running editor process without explicit confirmation.
5. If the user chooses manual restart, provide exact manual steps: save, close/reopen the project, start the agent from the project root, then call `list_toolsets`.
6. If the user chooses to continue without restart, continue only with already available Toolsets and note that newly enabled plugins may not appear until restart.

After the core connection is configured, enable Toolset plugins according to the task. `AllToolsets` is acceptable for broad exploration or prototyping when the user accepts the larger startup and schema surface; otherwise enable the specific domain Toolsets needed and verify them with `list_toolsets`.

## Codex TOML Rule

Codex TOML generation is write-once. If `.codex/config.toml` exists for a Codex target, stop before any write and ask the user whether to edit or delete it. Do not overwrite it automatically.

## Editor Fallback

If project defaults are ignored by a specific engine build, use the editor UI:

1. Enable **Unreal MCP** in Edit > Plugins.
2. Open Editor Preferences > General > Model Context Protocol.
3. Enable Auto Start Server.
4. Set port `8000` and URL path `/mcp`.
5. Run `ModelContextProtocol.GenerateClientConfig <Client|All>` from the editor console.
6. Start the agent from the project root and call `list_toolsets`.

## Verification

After configuration:

1. Launch/restart the UE editor only after the save/restart dialog above, or have the user restart manually.
2. Confirm Output Log includes `LogModelContextProtocol` startup messages.
3. Start the agent from the project root where config was written.
4. Call `list_toolsets`.
5. If Toolsets are missing, run `ModelContextProtocol.RefreshTools`, reconnect the agent, and inspect `LogModelContextProtocol`.

