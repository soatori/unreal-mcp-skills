# Unreal MCP Configure Workflow

Use this reference when handling `/unreal-mcp:configure <target>` or `/ue-mcp:configure <target>`.

## Command

Run from the skill directory or pass the full script path:

```powershell
.\scripts\configure-unreal-mcp.ps1 -ProjectPath "E:\Path\Project" -Target all -Port 8000 -DryRun
```

Targets are `claude`, `codex`, `cursor`, `vscode`, `gemini`, and `all`.

Important switches:

- `-DryRun`: print planned file changes without writing. Use this first.
- `-EnablePlugins`: add `ModelContextProtocol` and `ToolsetRegistry` entries to the `.uproject`.
- `-AutoStart`: write project default MCP settings to `Config/DefaultEngine.ini`.
- `-Verify`: try a short HTTP request to `http://127.0.0.1:<Port>/mcp`.
- `-Target all`: enables plugins, writes Auto Start defaults, and configures all supported clients.

## What The Script Changes

- Resolves exactly one `.uproject` from `-ProjectPath`.
- Enables only the required Unreal MCP plugins: `ModelContextProtocol` and `ToolsetRegistry`.
- Writes project default settings for Auto Start, port, URL path, and Tool Search.
- Merges JSON client configs for Claude Code, Cursor, VS Code, and Gemini without deleting existing MCP servers.
- Creates Codex `.codex/config.toml` only when it does not already exist.

The script does not enable `AllToolsets` or optional domain toolsets. Enable optional Toolsets only after the task needs them.

## Codex TOML Rule

Codex TOML generation is write-once. If `.codex/config.toml` exists, stop and ask the user whether to edit or delete it. Do not overwrite it automatically.

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

1. Launch or restart the UE editor.
2. Confirm Output Log includes `LogModelContextProtocol` startup messages.
3. Start the agent from the project root where config was written.
4. Call `list_toolsets`.
5. If Toolsets are missing, run `ModelContextProtocol.RefreshTools`, reconnect the agent, and inspect `LogModelContextProtocol`.

