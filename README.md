[![skills.sh](https://skills.sh/b/soatori/unreal-mcp-skills)](https://skills.sh/soatori/unreal-mcp-skills)

# Unreal MCP Skill

Agent automation for discovering, configuring, controlling, recovering, and verifying Unreal Editor through Epic's official **ModelContextProtocol (MCP)** toolset.

> Supported version: UE 5.8+

## Install

```bash
npx skills add soatori/unreal-mcp-skills
```

The package name is `unreal-mcp-skills`. The skill command is `unreal-mcp`. Do not use `/unreal-mcp-skills` as a command.

Use one of these forms in an agent session:

```text
$unreal-mcp
/unreal-mcp
/ue-mcp
/unreal-mcp:configure all
/ue-mcp:configure codex
```

## Agent Automation

Invoke `$unreal-mcp`, `/unreal-mcp`, or `/ue-mcp` with the editor outcome you want. The skill directs the agent to discover the project and live Toolsets, configure or recover MCP when needed, execute the editor operation, and verify the result. Human input is reserved for an ambiguous target, a protected write, missing authorization, or a dirty-state safety gate that cannot be resolved through available controls.

## Configure Command

`/unreal-mcp:configure <target>` and `/ue-mcp:configure <target>` automatically set up the target UE project. The agent resolves the project root, runs a dry-run, reports planned files, then writes the core MCP plugins, common Toolset plugins, Auto Start defaults, and selected client config unless a blocker appears.

Supported targets:

| Target | Config file |
|---|---|
| `claude` | `.mcp.json` |
| `codex` | `.codex/config.toml` |
| `cursor` | `.cursor/mcp.json` |
| `vscode` | `.vscode/mcp.json` |
| `gemini` | `.gemini/settings.json` |
| `all` | all supported clients |

Codex TOML is protected as write-once. If `.codex/config.toml` already exists, the script stops and asks for manual cleanup instead of overwriting it.

The configure helper is implementation support for the skill command. `Target` selects the client config; it does not skip project setup. For example, `/ue-mcp:configure codex` still enables `ModelContextProtocol`, `ToolsetRegistry`, `EditorToolset`, `AutomationTestToolset`, and `LiveCodingToolset`, then writes `Config/DefaultEngine.ini` defaults.

The default Toolset profile is `common`, which covers the most frequent editor tasks: editor state/logs/viewport/selection, scene/actor/asset/Blueprint/material operations, automation test discovery, and Live Coding. Use `-ToolsetProfile core` for core MCP transport only, or `-ToolsetProfile all` for broad exploration.

After configuration, the agent discovers unsaved state. It restarts the matching editor automatically when the editor is proven clean; otherwise it requests only the save or confirmation action required for a safe restart.

## What This Skill Covers

- Tool Search flow: `list_toolsets` -> `describe_toolset` -> `call_tool`.
- Editor, scene, actor, asset, Blueprint, log, automation test, and Live Coding workflows exposed by enabled Toolsets.
- Safe read-before-write editor operations.
- UE AgentSkill inspection and creation/update boundaries.
- Blueprint EventGraph reading, including fallback from `read_graph_dsl` to node and pin inspection.
- `uasset_read` comparison support using UE MCP as editor semantic evidence, not binary serialization proof.

For detailed Toolset maps, runtime limits, custom Toolset authoring, and known call-shape pitfalls, read `references/mcp-tools.md`.

For parser comparison work, read `references/uasset-read-comparison.md`.

## Maintenance

Run the skill consistency check after editing docs, examples, metadata, or scripts:

```bash
python scripts/validate-skill.py
```

The configure helper is implementation support for `/unreal-mcp:configure`; the agent runs it as part of the automation workflow.

Useful local checks:

```bash
find references/examples -type f
rg -n '/unreal-mcp-skills|unreal-mcp-skills\\' SKILL.md README.md references agents
```

Expected key files:

```text
unreal-mcp/
├── SKILL.md
├── README.md
├── skills.sh.json
├── agents/
│   ├── claude.md
│   └── openai.yaml
├── scripts/
│   ├── configure-unreal-mcp.py
│   ├── validate-skill.py
│   └── find-ue-installations.py
└── references/
    ├── configure-workflow.md
    ├── mcp-tools.md
    ├── uasset-read-comparison.md
    └── examples/
```

## Official Reference

- [Epic Unreal MCP documentation](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)

