# Claude Code Agent — Unreal MCP

Use `$unreal-mcp` to complete Unreal Editor tasks, not to teach setup steps.

## Execution Contract

1. Resolve the target `.uproject` from the request and workspace.
2. Inspect project plugins, MCP defaults, `.mcp.json`, editor process, endpoint, and logs.
3. Run the configure helper with dry-run first when bootstrap state is missing.
4. Connect and execute `list_toolsets → describe_toolset → call_tool`.
5. Use a separate read operation to verify every mutation.
6. If restart is required, discover dirty state from the live schema. Restart automatically when proven clean; request only the save action when dirty or unknown.

Launch Claude Code from the project root so `.mcp.json` is active. Use the full live Toolset name and short operation name in `call_tool`; never invent schemas from examples.

## Recovery

When tools are unavailable, inspect configuration, port, process, and MCP logs; start the server through an available control channel, refresh tools, reconnect, or restart through the dirty-state gate. Return a minimal blocker only when no available channel can safely continue.

## Safety

- Use read-only preflight and independent post-write verification.
- Serialize dependent editor operations and wait for async completion.
- Match restarts to the target project; do not terminate unrelated editor processes.
- `CreateSkill` and `UpdateSkill` require explicit permission.
