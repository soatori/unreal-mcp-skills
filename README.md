[![skills.sh](https://skills.sh/b/soatori/unreal-mcp-skills)](https://skills.sh/soatori/unreal-mcp-skills)

# Unreal MCP Skill

Agent guidance skill for operating the Unreal Editor through Epic's official **ModelContextProtocol (MCP)** toolset.

> **Supported version:** UE 5.8+
> Learn to use this Experimental feature, but use caution when shipping with it.

## Features

This skill enables AI coding agents (Claude Code, Codex, Cursor, VS Code, Gemini CLI) to control the UE Editor via Epic's official MCP protocol, covering the following capability domains:

### Connection & Configuration

- Auto-detect MCP server connection status
- Guide enabling the Unreal MCP plugin, starting the server, and generating client configurations
- Connection troubleshooting: plugin status → server endpoint → config files → logs → tool refresh

### Editor Control

- Get/set camera position and orientation
- Get currently selected Actors and Assets
- Get Content Browser path
- Check PIE (Play In Editor) running status
- Trigger screenshots

### Level & Actor Management

- Query current level information
- Search Actors in the level by criteria
- Get Actor labels, transforms, component lists, bounding boxes
- Create, move, delete Actors
- Set Actor transforms and selection state

### Blueprint Operations

- List all graphs in a Blueprint
- Read graph structure and node information (titles, pins, connections)
- Perform Blueprint EventGraph logic analysis (execution flow + data flow)
- Read Blueprint logic via DSL or node traversal
- Automatic read-only diff check before modifications

### Asset & Content Management

- Browse and query assets in the Content Browser
- Import external files into UE
- Save, compile assets
- Manage materials, meshes, textures, tables, and other asset types

### Logging & Diagnostics

- Read editor logs in real-time (filter by category and keyword)
- Distinguish log sources: `LogModelContextProtocol`, `LogToolsetRegistry`, `LogPython`, etc.
- Filter out irrelevant logs like Epic telemetry uploads

### Automated Testing

- Discover and list automated tests in the project
- Execute tests on demand and retrieve results

### Live Coding

- Trigger C++ hot-reload compilation
- Wait for compilation to complete before executing dependent operations

### AgentSkill Management

- List and view existing UE AgentSkill assets
- Create or update AgentSkill (requires explicit user authorization)

### Extended Toolsets (Optional Plugins)

Enabling plugins under `Engine/Plugins/Experimental/Toolsets/*` unlocks additional capabilities:

| Domain | Available Toolsets |
|---|---|
| Plugins & Configuration | `PluginToolset`, `ConfigSettingsToolset` |
| Procedural Generation & VFX | `PCGToolset`, `NiagaraToolsets`, `DataflowAgent` |
| Gameplay Systems | `GameplayTagsToolset`, `GASToolsets`, `StateTreeToolset` |
| UI Inspection | `UMGToolSet`, `MVVMToolset`, `SlateInspectorToolset` |
| Specialized Assets | `PhysicsToolsets`, `AnimationAssistantToolset`, `MetaHumanGenerator` |

## Installation

```bash
npx skills add soatori/unreal-mcp-skills
```

Or clone manually:

```bash
git clone https://github.com/soatori/unreal-mcp-skills.git
```

## Quick Start

You can also use the `/ue-mcp:` prefix — it works the same way.

### Connection Configuration

```
/unreal-mcp:configure <target>
```

| Parameter | Description | Config Format | Config Location |
|---|---|---|---|
| `claude` | Generate config for Claude Code | `.mcp.json` | Project root or `~/.claude/.mcp.json` |
| `codex` | Generate config for Codex | `.codex/config.toml` | Project root |
| `cursor` | Generate config for Cursor | `.mcp.json` | Project root |
| `vscode` | Generate config for VS Code | `.vscode/mcp.json` | Project root |
| `gemini` | Generate config for Gemini CLI | `.gemini/settings.json` | Project root |
| `all` | Generate config for all clients | — | Respective locations |

Configuration follows this workflow:

1. **Detect UE Project** — If no `.uproject` file is found, ask the user for the project path
2. **Check Plugin Status** — Check if `ModelContextProtocol` and `ToolsetRegistry` are enabled:
   - If not enabled: ask the user if they want help configuring (auto-enabled with `all` parameter)
3. **Check Editor MCP Settings** — Check and configure these key settings:
   - Auto Start (auto-start MCP server)
   - Listen port (default `8000`)
   - Other ModelContextProtocol-related settings
   - If not configured: ask the user if they want help setting up (auto-configured with `all` parameter)
4. **Check Server Startup** — Confirm the server is running; guide startup if not
5. **Generate Client Config** — Generate the appropriate config file based on the target parameter
6. **Connection Verification** — Call `list_toolsets` to confirm tools are available

### Editor Operations

| Command | Description |
|---|---|
| `/unreal-mcp:execute-blueprint` | Execute a specified Blueprint function in the UE Editor |
| `/unreal-mcp:open-widget` | Open an Editor Utility Widget |

### Main Skill

When invoking `/unreal-mcp`, the Agent will automatically guide through this workflow:

1. Detect MCP connection status
2. Discover available toolsets (`list_toolsets`)
3. Query toolset schemas (`describe_toolset`)
4. Safely execute editor operations (`call_tool`)

## Tool Search Mode

Unreal MCP enables Tool Search mode by default. `tools/list` returns three meta-tools instead of all schemas:

| Meta-tool | Purpose |
|---|---|
| `list_toolsets` | List available Toolset names and descriptions |
| `describe_toolset` | Return the tool schema for a specified Toolset |
| `call_tool` | Call a tool within a specified Toolset |

When calling `call_tool`, pass `toolset_name` (full Toolset name) and `tool_name` (short tool name). Do not use fully-qualified tool names.

## Editor Settings

| Setting | Default | Location |
|---|---|---|
| Auto Start Server | `false` | Editor Preferences > General > Model Context Protocol |
| Server Port Number | `8000` | Same as above |
| Server URL Path | `/mcp` | Same as above |
| Server name | `unreal-mcp` | `serverInfo.name` |
| Enable Tool Search | `true` | `tools/list` returns meta-tools |

## Console Commands

| Command | Purpose |
|---|---|
| `ModelContextProtocol.StartServer [port]` | Start the server, optional port override |
| `ModelContextProtocol.StopServer` | Stop the server and close the session |
| `ModelContextProtocol.RefreshTools` | Reload tool registration (use after hot-reload / Game Feature activation) |
| `ModelContextProtocol.GenerateClientConfig <Client\|All>` | Generate client config, supports `ClaudeCode`, `Cursor`, `VSCode`, `Gemini`, `Codex`, `All` |

Launch parameters:

| Parameter | Purpose |
|---|---|
| `-ModelContextProtocolStartServer` | Auto-start MCP server when launching the editor |
| `-ModelContextProtocolPort=N` | Override listen port (`1..65535`) |

## Security & Limitations

- Unreal MCP is an experimental feature; APIs and schemas may change
- Only HTTP and Server-Sent Events transports are supported; `stdio` and WebSocket are not
- Binds to loopback (`127.0.0.1`) by default; does not accept non-local Origins
- No authentication layer — do not expose beyond the local machine
- Tool calls execute serially on the Unreal game thread; overlapping dependent calls are not supported
- Tool behavior may differ during PIE; check PIE status if results seem off
- Save the project before and after bulk changes — MCP edits are not always undoable

## Custom Tool Development

Supports adding custom tools via the Toolset Registry:

**Python Toolset:**

```python
import unreal
import toolset_registry

@unreal.uclass()
class MyTools(unreal.ToolsetDefinition):
    @staticmethod
    @toolset_registry.tool_call
    def get_scene_info() -> dict:
        world = unreal.EditorLevelLibrary.get_editor_world()
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        return {"level_name": world.get_name(), "actor_count": len(actors)}
```

**C++ Toolset:**

- Derive from `UToolsetDefinition`
- Mark with `UCLASS(BlueprintType, Hidden)`
- Expose static methods with `UFUNCTION(meta = (AICallable))`

After creation, run `ModelContextProtocol.RefreshTools` to refresh registration.

## Repository Structure

```
unreal-mcp-skills/
├── SKILL.md                          # Main skill file (Agent load entry point)
├── skills.sh.json                    # skills.sh discovery metadata
├── agents/
│   ├── claude.md                     # Claude Code configuration instructions
│   └── openai.yaml                   # Codex/OpenAI configuration instructions
└── references/
    ├── mcp-tools.md                  # Full MCP toolset reference documentation
    └── examples/                     # Example MCP configs (copy to project root)
        ├── .mcp.json                 # Claude Code config
        ├── .cursor/mcp.json          # Cursor config
        ├── .codex/config.toml        # Codex config
        ├── .vscode/mcp.json          # VS Code config
        └── .gemini/settings.json     # Gemini config
```

## Documentation

- **[SKILL.md](SKILL.md)** — Full Agent instructions (workflows, toolsets, safety rules, debugging)
- **[references/mcp-tools.md](references/mcp-tools.md)** — Installation guide, architecture, toolset map, Blueprint manual, custom tool development
- **[Epic MCP Official Documentation](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)** — Official Unreal documentation
