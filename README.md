[![skills.sh](https://skills.sh/b/soatori/unreal-mcp-skills)](https://skills.sh/soatori/unreal-mcp-skills)

# Unreal MCP Skill

Agent guidance skill for operating the Unreal Editor through Epic's official **ModelContextProtocol (MCP)** toolset.

> **Supported version:** UE 5.8+

## What It Does

This skill teaches AI coding agents (Claude Code, Codex, Cursor, Gemini CLI) how to:

- Connect to a running UE Editor via the local MCP server
- Discover available Toolsets with `list_toolsets` / `describe_toolset`
- Call editor tools safely through `call_tool`
- Create and manage UE AgentSkill assets (with permission)
- Debug MCP configuration and tool availability issues

## Install

```bash
npx skills add soatori/unreal-mcp-skills
```

Or clone manually:

```bash
git clone https://github.com/soatori/unreal-mcp-skills.git
```

## Quick Start

1. Invoke `/unreal-mcp-skills` or `$unreal-mcp-skills` in your agent
2. The skill will guide you through connecting to UE Editor via MCP
3. Follow the workflow in SKILL.md for toolset discovery and safe tool invocation

## Repository Structure

```
unreal-mcp-skills/
├── SKILL.md                          # Main skill (loaded by agents)
├── skills.sh.json                    # skills.sh discovery metadata
├── agents/
│   ├── claude.md                     # Claude Code agent setup
│   └── openai.yaml                   # Codex/OpenAI agent setup
└── references/
    ├── mcp-tools.md                  # Full MCP toolset reference
    └── sample-mcp-configs/           # Sample MCP configs (copy to project root)
        ├── .mcp.json                 # Claude Code config
        ├── .cursor/mcp.json          # Cursor config
        ├── .codex/config.toml        # Codex config
        └── .gemini/settings.json     # Gemini config
```

## Supported Clients

| Client | Config format | Generate command | Config location |
|---|---|---|---|
| Claude Code | `.mcp.json` | `ModelContextProtocol.GenerateClientConfig ClaudeCode` | Project root or `~/.claude/.mcp.json` |
| Codex | `.codex/config.toml` | `ModelContextProtocol.GenerateClientConfig Codex` | Project root |
| Cursor | `.mcp.json` | `ModelContextProtocol.GenerateClientConfig Cursor` | Project root |
| Gemini CLI | `.gemini/settings.json` | `ModelContextProtocol.GenerateClientConfig Gemini` | Project root |

## Documentation

- **[SKILL.md](SKILL.md)** — full agent instructions (workflow, toolsets, safety rules, debugging)
- **[references/mcp-tools.md](references/mcp-tools.md)** — setup guide, architecture, toolset map, Blueprint playbook, custom tool authoring
- **[Epic MCP docs](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)** — official Unreal documentation
