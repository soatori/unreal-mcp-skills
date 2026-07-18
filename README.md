[![skills.sh](https://skills.sh/b/soatori/unreal-mcp-skills)](https://skills.sh/soatori/unreal-mcp-skills)

# Unreal MCP Skill

Agent automation for discovering, configuring, controlling, recovering, and verifying Unreal Editor through Epic's official **ModelContextProtocol (MCP)** toolset.

> Supported version: UE 5.8+

## Installation

```bash
npx skills add soatori/unreal-mcp-skills
```

The package name is `unreal-mcp-skills`. Activate the installed skill as `$unreal-mcp`.

## Supported Commands

```text
$unreal-mcp
/unreal-mcp
/ue-mcp
/unreal-mcp:configure <client>
/ue-mcp:configure <client>
/unreal-mcp:execute-blueprint
/unreal-mcp:open-widget
/unreal-mcp:find-installations
```

## Agent Automation

Use `$unreal-mcp` with the editor outcome to produce. The agent resolves the project, discovers live capabilities, configures or recovers MCP when necessary, executes the scoped editor operation, and independently verifies the result. It records completed actions, resulting state, partial failures, and a minimal blocker only when no available control channel can safely proceed.

## Configure Behavior

The canonical configure command automatically resolves one `.uproject`, inspects a dry-run, enables the selected Toolset profile, writes shared Auto Start defaults, creates or merges supported client configuration when permitted, recovers the connection, and verifies the live capability surface. The default profile is `common`: `EditorToolset`, `AutomationTestToolset`, and `LiveCodingToolset` alongside core MCP plugins.

Shared defaults are written to `Config/DefaultEditorPerProjectUserSettings.ini` in `/Script/ModelContextProtocolEngine.ModelContextProtocolSettings`; the URL-path key is `ServerUrlPath`. They do not overwrite an existing `Saved/Config/*Editor/EditorPerProjectUserSettings.ini`, which the agent does not mutate automatically. The agent recovers the current session through live `ConfigSettingsToolset`, editor control or console, `ModelContextProtocol.StartServer`, or launch flags, then independently verifies effective state.

If `list_toolsets` is absent while native Toolset operations or schemas are available, the agent treats the connection as Tool Search disabled/eager mode, prefers restoring `bEnableToolSearch=True`, and otherwise uses the live native schemas to complete and verify the task. An existing `.codex/config.toml` is one protected-configuration authorization blocker and remains unchanged.

## Capability and Safety Boundaries

- Live Toolset schemas are authoritative; do not invent Toolsets or arguments.
- Calls execute serially on the editor game thread; dependent calls wait for completion.
- Every mutation has a read-only preflight where possible and an independent post-write readback.
- Restarts use the dirty-state gate and never terminate an unrelated editor process.
- `CreateSkill` and `UpdateSkill` create or update Blueprint-backed UE assets and require explicit authorization.
- Unreal MCP is loopback-only and has no authentication layer; do not expose it beyond the local machine.

## Official Reference

- [Epic Unreal MCP documentation](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)
