# Claude Code Agent — Unreal MCP

## Setup

1. Enable the **Unreal MCP** plugin in UE Editor (Edit > Plugins).
2. Start the MCP server: Auto Start or `ModelContextProtocol.StartServer [port]`.
3. Generate client config from the UE Editor console:
   ```
   ModelContextProtocol.GenerateClientConfig ClaudeCode
   ```
   This merges the Unreal MCP server into `.mcp.json` in the project root (existing entries are preserved). Sample entry:
   ```json
   {
     "mcpServers": {
       "unreal-mcp": {
         "type": "http",
         "url": "http://127.0.0.1:8000/mcp",
         "disabled": false
       }
     }
   }
   ```

   **Configuration locations:**
   - **Project-specific:** `.mcp.json` in project root (merged with existing config)
   - **Global:** `~/.claude/.mcp.json` for all projects
   - **Project settings:** `.claude/settings.json` can also contain MCP config

4. Launch Claude Code **from that project root** so it picks up the config.

## Connection Verification

Once connected, verify MCP tools are available:

```json
{ "tool_name": "list_toolsets" }
```

If no tools appear, check:
- Plugin enabled and editor restarted
- Server running (`http://127.0.0.1:8000/mcp`)
- Config file exists in the project root
- Claude Code launched from the same root

## Tool Invocation

Use `call_tool` with the short tool name:

```json
{
  "tool_name": "call_tool",
  "arguments": {
    "toolset_name": "editor_toolset.toolsets.scene.SceneTools",
    "tool_name": "get_current_level",
    "arguments": {}
  }
}
```

## Safety

- Read-only first: always inspect before mutating.
- Serial calls: wait for each result before the next dependent call.
- AgentSkill create/update requires explicit user permission.
