# Third-Party Unreal MCP Ecosystem

Use when the live project looks like [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp) (or the user names it). `SKILL.md` still owns the official Epic path. Upstream is experimental — treat its docs as a snapshot.

## Stack Identification

| Signal | Official (Epic) | Third-party (chongdashu) |
|---|---|---|
| Transport | HTTP `http://127.0.0.1:8000/mcp` | stdio (`uv run unreal_mcp_server.py`) + TCP 55557 |
| Discovery | `list_toolsets` / `describe_toolset` / `call_tool` | Fixed tool names |
| Plugin | `ModelContextProtocol` + `ToolsetRegistry` | `Plugins/UnrealMCP` |
| UE | 5.8+ | 5.5+ |

If both appear, prefer official for editor state, Live Coding, and automation tests.

## Tool Mapping

Official column is a **capability baseline**, not a live schema. Names drift — identify the family, then use live `describe_toolset` on the official side.

| Third-party family | Official baseline |
|---|---|
| `editor_tools` (actors via `spawn_actor` / `delete_actor`, viewport) | `editor_toolset.toolsets.scene.SceneTools` / `actor.ActorTools`; focus via `EditorToolset.EditorAppToolset` |
| `blueprint_tools` + `node_tools` | `editor_toolset.toolsets.blueprint.BlueprintTools` |
| `project_tools` (`create_input_mapping`) | Project input config, not a 1:1 Toolset |
| `umg_tools` | `UMGToolSet` |

Do not invent third-party names. `focus_viewport` exists in upstream source but is currently unregistered.

## Client Configuration

Do not extend `scripts/configure-unreal-mcp.py` for this stack. Stdio shape is `uv --directory <repo>/Python run unreal_mcp_server.py`. On Windows, Claude Desktop reads `%APPDATA%\Claude\claude_desktop_config.json` — do not port upstream's Linux `~/.config/...` path to `%USERPROFILE%`. Verify Windsurf's live config path; upstream README may be stale.

## Safety

- Both stacks are local-only; do not expose them.
- Preflight + independent post-write readback from `SKILL.md` still apply.
- Non-Unreal MCP ecosystems stay out of scope — see `references/mcp-tools.md` § Public Case Boundary.
