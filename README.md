[![skills.sh](https://skills.sh/b/soatori/unreal-mcp-skills)](https://skills.sh/soatori/unreal-mcp-skills)

# Unreal MCP Skill

Agent guidance for operating Unreal Editor through Epic's official **ModelContextProtocol (MCP)** toolset.

> Supported version: UE 5.8+

## Install

```bash
npx skills add soatori/unreal-mcp-skills
```

Use one of these forms in an agent session:

```text
$unreal-mcp
/unreal-mcp
/ue-mcp
/unreal-mcp:configure all
/ue-mcp:configure codex
```

## Quick Start

1. Start from a UE project root or provide a `.uproject` path.
2. Run a dry-run configuration check:

   ```powershell
   .\scripts\configure-unreal-mcp.ps1 -ProjectPath "E:\Path\Project" -Target all -DryRun
   ```

3. If the planned changes are correct, run the real configuration:

   ```powershell
   .\scripts\configure-unreal-mcp.ps1 -ProjectPath "E:\Path\Project" -Target all -Verify
   ```

4. Launch or restart Unreal Editor.
5. Start the agent from the project root where MCP config was written.
6. Confirm the connection by calling `list_toolsets`.

The script enables only the required plugins: `ModelContextProtocol` and `ToolsetRegistry`. It does not enable `AllToolsets` or optional experimental Toolsets.

## Configure Command

`/unreal-mcp:configure <target>` and `/ue-mcp:configure <target>` map to the script-backed workflow in `references/configure-workflow.md`.

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

```powershell
.\scripts\validate-skill.ps1
```

Useful local checks:

```powershell
Get-ChildItem -Recurse references\examples
rg -n "/unreal-mcp-skills|unreal-mcp-skills\\" SKILL.md README.md references agents
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
│   ├── configure-unreal-mcp.ps1
│   └── validate-skill.ps1
└── references/
    ├── configure-workflow.md
    ├── mcp-tools.md
    ├── uasset-read-comparison.md
    └── examples/
```

## Official Reference

- [Epic Unreal MCP documentation](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)

