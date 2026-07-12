---
name: unreal-mcp
description: "Use when an agent must inspect, configure, control, recover, or verify Unreal Editor 5.8+ through Epic's official MCP; discover live Toolsets and schemas, execute editor operations, automate server and plugin setup, or manage UE AgentSkill assets with permission."
---

# Unreal MCP Agent Automation

Operate Unreal Editor through Epic's official `ModelContextProtocol` implementation. The goal is completion of the requested editor task, not instructions for the user to perform it.

## Agent Automation Contract

For every request:

1. Discover the target project and current editor/MCP state.
2. Use available filesystem, process, port, log, and MCP tools to remove recoverable blockers.
3. Discover live capabilities with `list_toolsets`, inspect the exact schema with `describe_toolset`, and execute with `call_tool`.
4. After every mutation, perform an independent read that proves the requested state.
5. Return the result and verification evidence. Ask the user only for one minimal blocker action when no available control channel can continue safely.

Do not replace an available action with setup directions, troubleshooting steps, UI click instructions, or a list of commands for the user. Reporting completed actions, risks, partial failures, and verification evidence is required.

Before declaring a blocker, record which applicable filesystem, process, port, log, editor-control, and MCP channels were inspected or attempted and the evidence that each cannot perform the next action. A failed recovery requires a fresh retry or readback; one unsuccessful call is not exhaustion evidence.

## Architecture and Truth Sources

Unreal MCP has three layers:

- `ModelContextProtocol`: local HTTP/Streamable HTTP server, sessions, settings, and client configuration.
- `ToolsetRegistry`: Toolset discovery, JSON schema generation, dispatch, and UE `UAgentSkill` assets.
- `Experimental/Toolsets/*`: editor, asset, test, Live Coding, UI, Gameplay, PCG, VFX, and other operational capabilities.

Treat live evidence in this order:

1. Current `list_toolsets` and `describe_toolset` results.
2. Current editor state, logs, project files, process state, and tool results.
3. Local UE source and Epic documentation.
4. This skill and its references as a capability baseline.

Never invent a documented Toolset or argument when the current session does not expose it. The wrapper expects the full Toolset name in `toolset_name` and the short operation name in `tool_name`.

Unreal MCP runs calls serially on the editor game thread. Execute dependent calls serially and wait for PIE, saving, compilation, Live Coding, tests, and editor startup to settle.

## Activation and Commands

Activate for `$unreal-mcp`, `/unreal-mcp`, `/ue-mcp`, or any request to inspect, configure, control, recover, or validate Unreal Editor through MCP. `unreal-mcp-skills` is the distribution name, not an agent command. Do not use `/unreal-mcp-skills` as a command.

| Command | Agent behavior |
|---|---|
| `/unreal-mcp:configure <target>` | Resolve one project, dry-run, configure it, recover/restart if needed, and verify the connection. |
| `/unreal-mcp:execute-blueprint` | Discover the Blueprint execution capability, execute the requested function, and verify its effect. |
| `/unreal-mcp:open-widget` | Discover the editor/widget capability, open the requested Editor Utility Widget, and verify it is open. |
| `/unreal-mcp:find-installations` | Run the bundled discovery script and return verified editor paths and versions. |

All commands accept the `ue-mcp` prefix. Claude Code uses project `.mcp.json`; Codex uses project `.codex/config.toml`. Do not create or manage cc-switch links.

## Automation State Machine

### 1. Resolve the project

Use, in order: an explicit `.uproject`, an explicit project directory, the current workspace, then a unique `.uproject` candidate beneath the workspace. Confirm its resolved absolute path and reject edits outside its project root.

Ask only when more than one plausible project remains. The minimal blocker is the project path or candidate selection; do not provide setup instructions.

### 2. Inspect bootstrap state

Before launching or diagnosing the editor, read:

- `.uproject`: `ModelContextProtocol`, `ToolsetRegistry`, and task-required Toolset plugins.
- `Config/DefaultEngine.ini`: Auto Start, port, URL path, and Tool Search settings.
- Target client config: endpoint and project-local placement.
- Unreal Editor processes: executable path and project command line when available.
- Endpoint/port state and available MCP/log evidence.

If configuration is missing or inconsistent, read `references/configure-workflow.md`, run the configure helper `scripts/configure-unreal-mcp.py` with `-DryRun`, inspect the proposed paths, then run the write automatically when it stays inside the target project and does not hit a protected file. Automatic project configuration is the default. Do not stop at asking whether guidance is needed.

Codex TOML is write-once: if `.codex/config.toml` exists and must change, stop before any configure write and request permission for that one protected edit. Do not delete or overwrite it implicitly.

### 3. Connect and discover

When MCP tools are exposed:

1. Call `list_toolsets`.
2. Select the smallest Toolset domain that can fulfill the task.
3. Call `describe_toolset` using the exact live name.
4. Form arguments from that schema.
5. Perform a read-only preflight when the operation mutates state.
6. Call the operation through `call_tool`.
7. Use a separate read/query operation to verify the effect.

When MCP tools are not exposed, or `list_toolsets` returns an empty/unusable registry, do not immediately return instructions. Treat discovery as failed, enter connection recovery, and retry discovery after recovery.

### 4. Recover the connection

Use available controls in this order:

1. Verify project plugins/settings/client config and correct them through the configure workflow when safe.
2. Check the configured loopback endpoint and Unreal Editor process.
3. If the editor is not running, discover the matching installation, launch it with the `.uproject`, wait, and retry the MCP connection.
4. If an editor control channel exists, run `ModelContextProtocol.StartServer [port]` or use Auto Start, then retry.
5. Inspect `LogModelContextProtocol`, `LogToolsetRegistry`, `LogPython`, Blueprint compiler, and target Toolset logs through MCP or another available log channel.
6. Run `ModelContextProtocol.RefreshTools`, reconnect, and retry `list_toolsets` when registration is stale.
7. If RefreshTools is insufficient, stop/start the server; use restart automation when plugin loading or new `UFUNCTION` registration requires an editor restart.

HTTP telemetry errors involving `datarouter.ol.epicgames.com` do not by themselves prove MCP failure. Unreal MCP is loopback-only, has no authentication layer, and must not be exposed beyond the local machine.

### 5. Enable missing capabilities

Only the live registry proves that a Toolset is usable. Route common tasks as follows, then confirm the exact live name/schema:

| Goal | Capability baseline |
|---|---|
| Editor state, scene, actors, assets, materials, Blueprints, logs | `EditorToolset` |
| Automation tests | `AutomationTestToolset` |
| C++ iteration and compile state | `LiveCodingToolset` |
| Plugin discovery/state | `PluginToolset` |
| Project/editor settings | `ConfigSettingsToolset` |
| Slate/UMG/MVVM | `SlateInspectorToolset`, `UMGToolSet`, `MVVMToolset` |
| GAS, tags, Game Features, StateTree, AI | corresponding Gameplay Toolset |
| PCG, Niagara, Dataflow, physics, animation | corresponding content Toolset |
| UE AgentSkill inspection | `ToolsetRegistry.AgentSkillToolset` |

If the required Toolset is absent:

1. Identify the providing plugin from live plugin metadata, local UE source, or the Toolset reference; do not infer it from a similar name alone.
2. Check whether that plugin is enabled through live `PluginToolset` state when available, otherwise through `.uproject`.
3. Enable only the task-required plugin through the live plugin operation when its schema supports the change, otherwise use the configure helper/project file path.
4. Make one evidenced dynamic-load/RefreshTools/reconnect attempt when supported.
5. Repeat `list_toolsets` and `describe_toolset` and retain the failure evidence if still absent.
6. Restart only after the dynamic attempt proves insufficient or the plugin/reflected API is known to require restart.

The default configure profile is `common`: core MCP plus `EditorToolset`, `AutomationTestToolset`, and `LiveCodingToolset`. Use `core` only for transport/discovery-only projects. Use `all` only when broad discovery is part of the request; otherwise prefer task-specific plugins.

## Restart Automation and Dirty-State Gate

Restart is an automated recovery action when it is safe, not a default conversation choice.

1. Discover a read-only dirty package/asset or unsaved-change capability from the live Toolset schemas. Do not hard-code a tool name that has not been discovered. The query must cover all dirty packages/assets and the current map in the target editor; a narrower query cannot prove restart safety.
2. Resolve and uniquely match the editor executable, process, and project before the final safety check. Combine any missing process/project identification with the same restart blocker request; allow at most one blocker request per restart attempt.
3. Immediately before closing, quiesce new mutations and repeat the full dirty-state query. If it proves no unsaved state, request a graceful close of only that editor process, wait for normal exit, relaunch it, wait for readiness, reconnect, inspect MCP logs, run `list_toolsets`, and resume the original task. Do not escalate to force-kill if graceful close times out or presents a save dialog.
4. If dirty assets/packages exist, request permission to save/discard them or ask the user to perform only that action and confirm the editor is safe to restart. Continue automatically after the response.
5. If MCP is disconnected and the bounded filesystem, process, port, log, and editor-control checks cannot reliably establish dirty-state, do not infer that the editor is clean. Issue the single restart blocker from step 2, asking the user to save/discard outstanding changes and confirm restart safety.
6. Never terminate unrelated Unreal Editor processes.

After restart, verification is incomplete until the endpoint responds, relevant MCP logs show startup, required Toolsets appear, their schemas load, and the original operation can resume or its prior result can be read back.

## Mutation and Verification Rules

- User requests for an editor outcome authorize normal, scoped configuration and editor operations needed to produce that outcome.
- Inspect current state before scene, asset, graph, plugin, config, PIE, save, compile, test, file, or AgentSkill mutation.
- State the expected effect briefly before a mutation when the user is observing the session; do not turn this notice into a tutorial or confirmation gate.
- Stop PIE before editor-only operations when the live schema/state requires it.
- Treat property and object writes as non-transactional unless the live schema proves otherwise. Split multi-object changes, verify each write, and stop dependent writes on the first failure.
- For bulk or destructive changes, require an explicit recovery point or authorization appropriate to the risk.
- `ListSkills` and `GetSkills` are read-only. `CreateSkill` and `UpdateSkill` write Blueprint-backed assets and always require explicit user permission.
- Run Automation Tests only when test execution is part of the requested task or required verification; wait for completion and read the final result.

The completion report contains: actions performed, verified resulting state, unresolved risks/partial changes, and any minimal blocker. It does not contain steps the user could have taken instead.

## Blueprint EventGraph Reading

For Blueprint inspection:

1. Discover `BlueprintTools` and inspect its live schema.
2. Call `list_graphs`, then `get_graph`, preserving the returned graph `refPath`.
3. Call `read_graph_dsl` with the exact graph reference.
4. If it is empty or rejects the path, call `find_nodes` with `title: ""`, then `get_node_infos` for pins/connections.
5. Use `get_connected_subgraph` from a relevant event/input node for a focused execution chain.
6. Report execution and data flow separately.

An empty DSL is not evidence of an empty graph. When the live schema marks an input as a UObject reference, pass `{ "refPath": "/Game/..." }`, not a bare string.

Read `references/uasset-read-comparison.md` for parser comparisons. MCP is editor-visible semantic evidence, not proof of raw `.uasset` serialization fidelity.

## Runtime Boundaries

- UE 5.8 MCP is experimental; schemas and return shapes may change.
- Editor Toolset discovery is editor-only. Cooked builds must register runtime tools through `IModelContextProtocolModule::AddTool()` and advertise them eagerly.
- Tool Search meta-tools are editor-only.
- Adding a new reflected `UFUNCTION` requires an editor restart; Live Coding alone is insufficient.
- Refresh tools after Python/C++ Toolset registration, hot reload, or Game Feature activation.

## References

- `references/configure-workflow.md`: automatic project/client configuration and restart recovery.
- `references/mcp-tools.md`: detailed Toolset map, schemas, console commands, and implementation limits.
- `references/find-editor-installations.md`: installation discovery used by launch/restart automation.
- `references/uasset-read-comparison.md`: editor-side comparison workflow for `uasset_read`.
