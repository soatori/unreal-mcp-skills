---
feature: third-party-ecosystem-contrast
status: delivered
updated: 2026-09-15
branch: feat/third-party-contrast
commits: c6b430b..4a5be17
---

# Third-Party Ecosystem Contrast

## Report

**What was built** — Added a third-party Unreal MCP contrast layer beside the official Epic path. New `references/third-party-ecosystem.md` covers stack identification (HTTP Tool Search vs stdio+TCP 55557), tool-name mapping to official Toolset baselines, a decision matrix for which stack to follow, and Windows client configs (Claude Desktop `%APPDATA%\Claude\claude_desktop_config.json`, Cursor, Windsurf). Linked from `mcp-tools.md` preamble + Public Case Boundary (chongdashu named), `SKILL.md` description/Runtime Boundaries/References, and a README note. Official automation contract, configure script, tests, and evals unchanged.

**Verification** — `python scripts/validate-skill.py` exit 0 (`Skill validation passed.`); `python -m unittest discover -s tests` 36/36 OK; cross-file link/token check PASS; task review Spec ✅ Approved; final whole-branch review Important (temporal phrasing) fixed in `4a5be17` and scoped re-review ADDRESSED.

**Journey log**
- Claude Desktop Windows path is `%APPDATA%\Claude\claude_desktop_config.json` — do not port upstream Linux `~/.config/claude-desktop/mcp.json` to `%USERPROFILE%`.
- PowerShell `-match` is case-insensitive: `ServerURLPath` checks false-positive on legitimate `ServerUrlPath`; use `-cmatch`.
- Tool Mapping official-column naming mix mirrors existing `mcp-tools.md` Toolset map — not a new inconsistency.
- SKILL.md frontmatter `description` is the activation gate; reference-only content will not trigger on third-party-only projects.
- Plan check scripts with over-escaped Windows paths (`\\` vs `\`) create false negatives; prefer single-backslash literals.

## [S1] Problem

`unreal-mcp-skills` is the agent handbook for Epic's **official** Unreal MCP
(`ModelContextProtocol` / `ToolsetRegistry`, UE 5.8+). It is deep on that path:
configure automation, connection recovery, dirty-state restart gate, Toolset map,
Blueprint graph reading, custom Toolset authoring.

It does **not** cover the most popular third-party Unreal MCP stack:
[chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp) (2k+ stars,
C++ plugin + Python FastMCP, UE 5.5+). Agents that land in a project using that
stack have no skill guidance: the official `list_toolsets` /
`describe_toolset` / `call_tool` discovery model does not apply, tool names are
fixed (`get_actors_in_level`, `create_blueprint`, `focus_viewport`, …), and the
transport is stdio + a TCP bridge on port 55557 rather than loopback HTTP on
8000.

The only existing mention is a generic "third-party Unreal MCP projects" row in
`references/mcp-tools.md` § Public Case Boundary. That is not enough for an
agent to:

1. Detect which stack is live.
2. Map third-party tool names to official Toolset equivalents (or vice versa).
3. Decide which stack is appropriate for the task.
4. Configure clients (Windsurf / Claude Desktop) the third-party stack actually
   targets — clients the official configure script does not support.

## [S2] Design

Add a **third-party ecosystem contrast** layer that sits *beside* the official
path, never replaces it. Official `SKILL.md` automation contract remains
authoritative for Epic MCP.

### S2.1 Stack identification

When MCP tools or client config are present, classify the live stack before
acting:

| Signal | Official (Epic) | Third-party (chongdashu) |
|---|---|---|
| Transport | HTTP / Streamable HTTP, default `http://127.0.0.1:8000/mcp` | stdio (`uv run unreal_mcp_server.py`) + in-editor TCP 55557 |
| Discovery | `list_toolsets` / `describe_toolset` / `call_tool` | Fixed tool names, no meta-tools |
| Plugin | `ModelContextProtocol` + `ToolsetRegistry` in `.uproject` | `UnrealMCP` plugin under `Plugins/UnrealMCP` |
| UE version | 5.8+ | 5.5+ |
| Client config shape | HTTP endpoint URL in project-local `.mcp.json` / Cursor / VSCode / Gemini | stdio command+args (`uv --directory … run unreal_mcp_server.py`) |

If both signals appear (rare but possible during migration), prefer official for
editor-state/Live Coding/automation-test tasks and ask only when the task
depends on a capability unique to the other stack.

### S2.2 Tool-name mapping (third-party → official baseline)

Document this table in the new reference. Official column is a **capability
baseline**, not a guaranteed live schema — the agent still must
`list_toolsets` / `describe_toolset` before calling official tools.

| Third-party module / tool | Official Toolset baseline |
|---|---|
| `editor_tools` — `get_actors_in_level`, `find_actors_by_name` | `editor_toolset.toolsets.scene.SceneTools` (find actors) |
| `editor_tools` — `spawn_actor`, `delete_actor` | `editor_toolset.toolsets.scene.SceneTools` (add/remove actors) |
| `editor_tools` — `set_actor_transform`, `get_actor_properties`, `set_actor_property` | `editor_toolset.toolsets.actor.ActorTools` |
| `editor_tools` — `spawn_blueprint_actor` | `editor_toolset.toolsets.scene.SceneTools` + Blueprint spawn |
| `blueprint_tools` — `create_blueprint`, `compile_blueprint` | `editor_toolset.toolsets.blueprint.BlueprintTools` |
| `blueprint_tools` — `add_component_to_blueprint`, `set_component_property`, `set_static_mesh_properties`, `set_physics_properties` | `editor_toolset.toolsets.blueprint.BlueprintTools` (components) |
| `node_tools` — `add_blueprint_event_node`, `add_blueprint_function_node`, `connect_blueprint_nodes`, `find_blueprint_nodes` | `editor_toolset.toolsets.blueprint.BlueprintTools` (graph authoring and inspection; read path: `find_nodes`, `get_node_infos`, `get_connected_subgraph`) |
| `node_tools` — `add_blueprint_variable`, `add_blueprint_self_reference`, `add_blueprint_get_self_component_reference` | Blueprint variables and self/component reference nodes under `BlueprintTools` |
| `project_tools` — `create_input_mapping` | Project input config, not a 1:1 Toolset; treat as project-file work |
| `editor_tools` — `focus_viewport` | Present in source but currently unregistered (`@mcp.tool()` commented out as buggy). Official baseline: `EditorToolset.EditorAppToolset` (camera / focus) |
| `umg_tools` | `UMGToolSet` |

Upstream Docs/Tools/*.md can lag the Python tool modules; prefer the registered `@mcp.tool()` surface as source of truth.

Never invent a third-party tool name that is not in the upstream docs, and never
substitute a third-party name for an official live schema.

### S2.3 Decision matrix (which stack to operate)

| Task context | Preferred stack |
|---|---|
| UE 5.8+ with official plugins enabled | Official (default for this skill) |
| UE 5.5–5.7 without `ModelContextProtocol` | Third-party if installed; otherwise no MCP control |
| Live Coding, Automation Tests, PCG, GAS, Game Features, StateTree | Official only |
| Basic actor place/move, Blueprint create/compile/spawn, UMG widget skeleton | Either; follow whichever is live |
| Client is Windsurf or Claude Desktop | Follow the **live** stack. Official HTTP MCP can serve these clients if already configured manually; the official configure script merely does not generate their configs. Prefer third-party only when that plugin is the live server. |

### S2.4 Client configuration (third-party only)

The official configure script covers claude/codex/cursor/vscode/gemini. For the
third-party stack, document (do not auto-write without permission) the stdio
shape and these locations:

| Client | Config location (Windows) | Notes |
|---|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | Anthropic official path. Upstream README's `~/.config/claude-desktop/mcp.json` is Linux-style and must not be ported to `%USERPROFILE%` |
| Cursor | `.cursor/mcp.json` (project root) | Same file name as official, different payload |
| Windsurf | `%USERPROFILE%\.codeium\windsurf\mcp_config.json` | Not in official configure targets. Upstream README may document a different Windsurf path; verify the live client config location. |

Payload shape:

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

Do **not** extend `scripts/configure-unreal-mcp.py` to write third-party
configs in this change. That is out of scope (see S3).

### S2.5 Safety and boundary rules (carry forward)

- Unreal MCP (both stacks) is local-only; do not expose beyond the machine.
- Third-party commands still mutate the live editor; preflight + post-write
  readback rules from `SKILL.md` apply.
- The third-party project is experimental and last pushed 2025-04; treat its
  docs as a capability snapshot, not a long-term contract.
- Keep the existing "Public Case Boundary" rule: Jianying/CapCut MCP and other
  non-Unreal MCP ecosystems stay out of the Unreal capability model.

### S2.6 File-level changes

| File | Change |
|---|---|
| `references/third-party-ecosystem.md` | **New.** Stack ID, mapping table, decision matrix, client configs, safety notes, upstream links |
| `references/mcp-tools.md` | Reconcile the preamble ("official path only") so a named third-party link is consistent; expand § Public Case Boundary to name `chongdashu/unreal-mcp` and link the new reference |
| `SKILL.md` | Extend frontmatter `description` with a third-party identification trigger (so the skill activates on that stack); add reference pointer in § References; one sentence in § Runtime Boundaries on the discovery/transport difference |
| `README.md` | One short "Related third-party stack" note with link |

No script, test, or eval changes.

## [S3] Out of Scope

- Implementing or vendoring the third-party plugin/server into this repo.
- Extending `configure-unreal-mcp.py` to write Windsurf / Claude Desktop /
  third-party stdio configs.
- Adding operational playbooks (step-by-step create-cube-blueprint etc.) for
  the third-party stack — this change is identification + mapping + boundary.
- Changing the official automation contract, restart gate, or Toolset map.
- Supporting the third-party stack on UE versions that also have official MCP
  as a dual-write path.
- Any non-Unreal MCP ecosystems beyond the existing boundary sentence.

## Tasks

- [x] T1: Write `references/third-party-ecosystem.md` — acceptance: file exists with stack-ID table, tool mapping (S2.2), decision matrix (S2.3), client config table + JSON shape (S2.4), safety notes (S2.5), and upstream repo/docs links; validate-skill passes (covers: S2.1, S2.2, S2.3, S2.4, S2.5)
- [x] T2: Update `references/mcp-tools.md` preamble + Public Case Boundary — acceptance: preamble no longer contradicts a named third-party section; chongdashu/unreal-mcp named, linked to `references/third-party-ecosystem.md` (covers: S2.6; depends: T1)
- [x] T3: Update `SKILL.md` description, References, Runtime Boundaries — acceptance: frontmatter description mentions third-party Unreal MCP identification; new reference listed; one boundary sentence on discovery/transport difference; official automation contract unchanged (covers: S2.6; depends: T1)
- [x] T4: Update `README.md` — acceptance: short third-party note present, links to GitHub upstream and does not claim the skill operates that stack (covers: S2.6; depends: T1)
- [x] T5: Run `scripts/validate-skill.py` — acceptance: script exits 0 on the updated skill tree (covers: S2.6; depends: T1, T2, T3, T4)
