[![skills.sh](https://skills.sh/b/soatori/ue-mcp)](https://skills.sh/soatori/ue-mcp)

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
# Claude Code
npx skills add soatori/ue-mcp

# Codex
npx skills add soatori/ue-mcp

# Cursor / Gemini CLI
npx skills add soatori/ue-mcp
```

Or clone manually:

```bash
git clone https://github.com/soatori/ue-mcp.git ~/.claude/skills/ue-mcp
```

## Quick Start

1. Enable the **Unreal MCP** plugin in UE Editor (Edit > Plugins)
2. Start the server: `ModelContextProtocol.StartServer`
3. Generate client config: `ModelContextProtocol.GenerateClientConfig ClaudeCode`
4. Launch your agent from the project root
5. Verify: send `list_toolsets` — if you see toolsets, you're connected

## Repository Structure

```
ue-mcp/
├── SKILL.md                          # Main skill (loaded by agents)
├── skills.sh.json                    # skills.sh discovery metadata
├── agents/
│   ├── claude.md                     # Claude Code agent setup
│   └── openai.yaml                   # Codex/OpenAI agent setup
└── references/
    ├── mcp-tools.md                  # Full MCP toolset reference
    └── sample-configs/
        ├── claude-code-mcp.json      # .mcp.json sample
        ├── codex-config.toml         # .codex/config.toml sample
        ├── cursor-mcp.json           # .cursor/mcp.json sample
        └── gemini-settings.json      # .gemini/settings.json sample
```

## Supported Clients

| Client | Config format | Generate command |
|---|---|---|
| Claude Code | `.mcp.json` | `ModelContextProtocol.GenerateClientConfig ClaudeCode` |
| Codex | `.codex/config.toml` | `ModelContextProtocol.GenerateClientConfig Codex` |
| Cursor | `.cursor/mcp.json` | `ModelContextProtocol.GenerateClientConfig Cursor` |
| Gemini CLI | `.gemini/settings.json` | `ModelContextProtocol.GenerateClientConfig Gemini` |

## Documentation

- **[SKILL.md](SKILL.md)** — full agent instructions (workflow, toolsets, safety rules, debugging)
- **[references/mcp-tools.md](references/mcp-tools.md)** — setup guide, architecture, toolset map, Blueprint playbook, custom tool authoring
- **[Epic MCP docs](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor?lang=en-US)** — official Unreal documentation

## License

MIT
