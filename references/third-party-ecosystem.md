# Third-Party Unreal MCP Ecosystem

Use this reference when the live project or client config indicates a third-party Unreal MCP stack, or when the user asks about `chongdashu/unreal-mcp` or another community Unreal MCP server. This skill's automation contract and official Toolset path in `SKILL.md` remain authoritative for Epic's `ModelContextProtocol`. This file identifies the third-party stack, maps its tools to an official capability baseline, and states client-config and safety boundaries.

Upstream project: [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp). Treat upstream docs as a capability snapshot, not a long-term contract; the project is experimental.

## Stack Identification

Classify the live stack before acting. Do not apply official Tool Search rules to a third-party server, and do not invent Toolset names for fixed third-party tools.

| Signal | Official (Epic) | Third-party (chongdashu) |
|---|---|---|
| Transport | HTTP / Streamable HTTP, default `http://127.0.0.1:8000/mcp` | stdio (`uv run unreal_mcp_server.py`) plus in-editor TCP bridge on port 55557 |
| Discovery | `list_toolsets` / `describe_toolset` / `call_tool` | Fixed tool names; no meta-tools |
| Plugin | `ModelContextProtocol` and `ToolsetRegistry` in `.uproject` | `UnrealMCP` plugin under `Plugins/UnrealMCP` |
| UE version | 5.8+ | 5.5+ |
| Client config shape | HTTP endpoint URL in project-local `.mcp.json` / Cursor / VS Code / Gemini | stdio `command` + `args` (`uv --directory … run unreal_mcp_server.py`) |

If both stacks appear, prefer official for editor state, Live Coding, and automation tests. Ask only when the task depends on a capability unique to the other stack.

## Tool Mapping

Third-party tool names to official Toolset **capability baselines**. The official column is not a live schema: always `list_toolsets` and `describe_toolset` before calling official tools. Never substitute a third-party name for an official live schema.

| Third-party module / tool | Official Toolset baseline |
|---|---|
| `editor_tools` — `get_actors_in_level`, `find_actors_by_name` | `editor_toolset.toolsets.scene.SceneTools` (find actors) |
| `editor_tools` — `spawn_actor`, `delete_actor` | `editor_toolset.toolsets.scene.SceneTools` (add/remove actors) |
| `editor_tools` — `set_actor_transform`, `get_actor_properties`, `set_actor_property` | `editor_toolset.toolsets.actor.ActorTools` |
| `editor_tools` — `spawn_blueprint_actor` | `editor_toolset.toolsets.scene.SceneTools` with Blueprint spawn |
| `blueprint_tools` — `create_blueprint`, `compile_blueprint` | `editor_toolset.toolsets.blueprint.BlueprintTools` |
| `blueprint_tools` — `add_component_to_blueprint`, `set_component_property`, `set_static_mesh_properties`, `set_physics_properties` | `editor_toolset.toolsets.blueprint.BlueprintTools` (components) |
| `node_tools` — `add_blueprint_event_node`, `add_blueprint_function_node`, `connect_blueprint_nodes`, `find_blueprint_nodes` | `editor_toolset.toolsets.blueprint.BlueprintTools` (graph authoring and inspection; read path uses `find_nodes`, `get_node_infos`, `get_connected_subgraph`) |
| `node_tools` — `add_blueprint_variable`, `add_blueprint_self_reference`, `add_blueprint_get_self_component_reference` | Blueprint variables and self/component reference nodes under `BlueprintTools` |
| `project_tools` — `create_input_mapping` | Project input configuration; not a 1:1 Toolset. Treat as project-file work |
| `editor_tools` — `focus_viewport` | Present in source but currently unregistered (`@mcp.tool()` commented out as buggy). Official baseline: `EditorToolset.EditorAppToolset` (camera / focus) |
| `umg_tools` | `UMGToolSet` |

## Decision Matrix

| Task context | Preferred stack |
|---|---|
| UE 5.8+ with official plugins enabled | Official (default for this skill) |
| UE 5.5–5.7 without `ModelContextProtocol` | Third-party if installed; otherwise no MCP control |
| Live Coding, Automation Tests, PCG, GAS, Game Features, StateTree | Official only |
| Basic actor place/move, Blueprint create/compile/spawn, UMG widget skeleton | Either; follow whichever stack is live |
| Client is Windsurf or Claude Desktop | Follow the live stack. Official HTTP MCP can serve these clients if already configured manually; the official configure script does not generate their configs. Prefer third-party only when that plugin is the live server |

## Client Configuration

The official configure helper covers claude, codex, cursor, vscode, and gemini. For the third-party stack, document these locations; do not auto-write them without permission.

| Client | Config location (Windows) | Notes |
|---|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | Anthropic official path. Upstream README's `~/.config/claude-desktop/mcp.json` is Linux-style and must not be ported to `%USERPROFILE%` |
| Cursor | `.cursor/mcp.json` (project root) | Same file name as official clients, different payload |
| Windsurf | `%USERPROFILE%\.codeium\windsurf\mcp_config.json` | Not an official configure target. Upstream README may document a different Windsurf path; verify the live client config location. |

Stdio payload shape:

```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "uv",
      "args": ["--directory", "<path-to>/Python", "run", "unreal_mcp_server.py"]
    }
  }
}
```

Do not extend `scripts/configure-unreal-mcp.py` to write third-party configs.

## Safety Boundaries

- Unreal MCP on both stacks is local-only; do not expose it beyond the local machine.
- Third-party commands still mutate the live editor. Apply the preflight and independent post-write readback rules from `SKILL.md`.
- The third-party project is experimental. Treat its docs as a capability snapshot.
- Jianying/CapCut and other non-Unreal MCP ecosystems remain outside the Unreal capability model. See `references/mcp-tools.md` § Public Case Boundary.
