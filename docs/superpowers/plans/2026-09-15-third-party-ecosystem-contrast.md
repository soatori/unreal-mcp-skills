# Third-Party Ecosystem Contrast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `unreal-mcp-skills` with a third-party Unreal MCP contrast layer (identification, tool mapping, decision matrix, client configs) so agents can recognize and reason about `chongdashu/unreal-mcp` without replacing the official Epic MCP path.

**Architecture:** Documentation-only change. One new reference (`references/third-party-ecosystem.md`) carries the full contrast content. Three existing files get small, targeted edits that name the third-party stack and link the new reference. `scripts/configure-unreal-mcp.py`, tests, and evals are untouched. Validation is `scripts/validate-skill.py` (exit 0) plus token greps on the new file.

**Tech Stack:** Markdown skill package; Python 3 validator (`scripts/validate-skill.py`); git worktree already at `.worktrees/third-party-contrast`.

**Spec:** `docs/compose/spec/third-party-ecosystem-contrast.md`

## Global Constraints

- Work only in worktree `C:\Users\cbsjz\.agents\skills\unreal-mcp-skills\.worktrees\third-party-contrast` (branch `feat/third-party-contrast`). Never edit main checkout.
- Official `SKILL.md` automation contract tokens must remain present: `Agent Automation Contract`, `list_toolsets`, `describe_toolset`, `call_tool`, `independent read`, `dirty-state`, `minimal blocker`.
- Forbidden in SKILL.md / README.md / references/** / agents/** / evals: `/ue-mcp`, `Config/DefaultEngine.ini`, `/Script/ModelContextProtocol.ModelContextProtocolSettings`, `ServerURLPath`, tutorial phrases (`Quick Setup (Step by Step)`, `Terminal Plugin (Optional)`, `manually delete`, `manual cleanup`, `ordinary users should`), Windows-only `.ps1` script paths.
- README.md must keep exactly one `text` command fence containing `$unreal-mcp`, `/unreal-mcp`, `/ue-mcp`, `/unreal-mcp:configure <client>`, `/ue-mcp:configure <client>`, and the install line `npx skills add soatori/unreal-mcp-skills`.
- Do not invent third-party tool names beyond the upstream set listed in Spec S2.2.
- Claude Desktop Windows config path is `%APPDATA%\Claude\claude_desktop_config.json` (never `%USERPROFILE%\.config\claude-desktop\...`).
- No script, test, or eval changes in this feature.

## File Structure

| File | Role |
|---|---|
| `references/third-party-ecosystem.md` | **Create.** Stack ID, tool mapping, decision matrix, client configs, safety notes, upstream links |
| `references/mcp-tools.md` | **Modify.** Reconcile preamble; name chongdashu in Public Case Boundary |
| `SKILL.md` | **Modify.** Description trigger, Runtime Boundaries sentence, References pointer |
| `README.md` | **Modify.** Short third-party note under Official Reference |
| `docs/compose/spec/third-party-ecosystem-contrast.md` | Existing Spec; status updates only at finalize (out of these tasks) |

---

### Task 1: Create `references/third-party-ecosystem.md`

**Files:**
- Create: `references/third-party-ecosystem.md`

**Interfaces:**
- Consumes: Spec S2.1–S2.5 content (already settled).
- Produces: A reference file whose sections are later linked from `mcp-tools.md` and `SKILL.md`. Later tasks only need the path `references/third-party-ecosystem.md` and the heading names `## Stack Identification`, `## Tool Mapping`, `## Decision Matrix`, `## Client Configuration`, `## Safety Boundaries`.

- [ ] **Step 1: Confirm baseline validate still passes (pre-change control)**

Run from worktree root:

```powershell
& $env:MIMO_PYTHON scripts/validate-skill.py
```

Expected: `Skill validation passed.` exit 0. If it fails, fix pre-existing issues first — do not attribute them to this feature.

- [ ] **Step 2: Write the new reference with the exact content below**

Create `references/third-party-ecosystem.md` with this full body (no placeholders):

````markdown
# Third-Party Unreal MCP Ecosystem

Use this reference when the live project or client config indicates a third-party Unreal MCP stack, or when the user asks about `chongdashu/unreal-mcp` or another community Unreal MCP server. This skill's automation contract and official Toolset path in `SKILL.md` remain authoritative for Epic's `ModelContextProtocol`. This file identifies the third-party stack, maps its tools to an official capability baseline, and states client-config and safety boundaries.

Upstream project: [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp). Treat upstream docs as a capability snapshot, not a long-term contract; the project is experimental.

## Stack Identification

Classify the live stack before acting. Do not apply official Tool Search rules to a third-party server, and do not invent Toolset names for fixed third-party tools.

| Signal | Official (Epic) | Third-party (chongdashu) |
|---|---|---|
| Transport | HTTP / Streamable HTTP, default `http://127.0.0.1:8000/mcp` | stdio (`uv run unreal_mcp_server.py`) plus in-editor TCP bridge on port 55557 |
| Discovery | `list_toolsets` / `describe_toolset` / `call_tool` | Fixed tool names; no meta-tools |
| Plugin | `ModelContextProtocol` and `ToolsetRegistry` in `.uproject` | `UnrealMCP` plugin under `Plugins/UnrealMCP` |
| UE version | 5.8+ | 5.5+ |
| Client config shape | HTTP endpoint URL in project-local `.mcp.json` / Cursor / VS Code / Gemini | stdio `command` + `args` (`uv --directory … run unreal_mcp_server.py`) |

If both stacks appear, prefer official for editor state, Live Coding, and automation tests. Ask only when the task depends on a capability unique to the other stack.

## Tool Mapping

Third-party tool names to official Toolset **capability baselines**. The official column is not a live schema: always `list_toolsets` and `describe_toolset` before calling official tools. Never substitute a third-party name for an official live schema.

| Third-party family / tool | Official Toolset baseline |
|---|---|
| `actor_tools` — `get_actors_in_level`, `find_actors_by_name` | `editor_toolset.toolsets.scene.SceneTools` (find actors) |
| `actor_tools` — `create_actor`, `delete_actor` | `editor_toolset.toolsets.scene.SceneTools` (add/remove actors) |
| `actor_tools` — `set_actor_transform`, `get_actor_properties` | `editor_toolset.toolsets.actor.ActorTools` |
| `blueprint_tools` — `create_blueprint`, `compile_blueprint` | `editor_toolset.toolsets.blueprint.BlueprintTools` |
| `blueprint_tools` — `add_component_to_blueprint`, `set_component_property` | `editor_toolset.toolsets.blueprint.BlueprintTools` (components) |
| `blueprint_tools` — `spawn_blueprint_actor` | `editor_toolset.toolsets.scene.SceneTools` with Blueprint spawn |
| `node_tools` — `add_blueprint_event_node`, `add_blueprint_function_node`, `connect_blueprint_nodes`, `find_blueprint_nodes` | `editor_toolset.toolsets.blueprint.BlueprintTools` (graph authoring and inspection; read path uses `find_nodes`, `get_node_infos`, `get_connected_subgraph`) |
| `node_tools` — `add_blueprint_variable`, `add_blueprint_self_reference`, `add_blueprint_get_self_component_reference` | Blueprint variables and self/component reference nodes under `BlueprintTools` |
| `node_tools` — `create_input_mapping` | Project input configuration; not a 1:1 Toolset. Treat as project-file work |
| `editor_tools` — `focus_viewport` | `EditorToolset.EditorAppToolset` (camera / focus) |
| `editor_tools` — `take_screenshot` | `EditorToolset.EditorAppToolset` (viewport or editor screenshot) |
| `umg_tools` | `UMGToolSet` |
| `project_tools` | `ConfigSettingsToolset` for settings; remaining project file operations through filesystem tools |

## Decision Matrix

| Task context | Preferred stack |
|---|---|
| UE 5.8+ with official plugins enabled | Official (default for this skill) |
| UE 5.5–5.7 without `ModelContextProtocol` | Third-party if installed; otherwise no MCP control |
| Live Coding, Automation Tests, PCG, GAS, Game Features, StateTree | Official only |
| Simple actor place/move, viewport focus/screenshot, basic Blueprint create/compile/spawn, UMG widget skeleton | Either; follow whichever stack is live |
| Client is Windsurf or Claude Desktop | Follow the live stack. Official HTTP MCP can serve these clients if already configured manually; the official configure script does not generate their configs. Prefer third-party only when that plugin is the live server |

## Client Configuration

The official configure helper covers claude, codex, cursor, vscode, and gemini. For the third-party stack, document these locations; do not auto-write them without permission.

| Client | Config location (Windows) | Notes |
|---|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | Anthropic official path. Upstream README's `~/.config/claude-desktop/mcp.json` is Linux-style and must not be ported to `%USERPROFILE%` |
| Cursor | `.cursor/mcp.json` (project root) | Same file name as official clients, different payload |
| Windsurf | `%USERPROFILE%\.codeium\windsurf\mcp_config.json` | Not an official configure target |

Stdio payload shape:

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

Do not extend `scripts/configure-unreal-mcp.py` to write third-party configs in this feature.

## Safety Boundaries

- Unreal MCP on both stacks is local-only; do not expose it beyond the local machine.
- Third-party commands still mutate the live editor. Apply the preflight and independent post-write readback rules from `SKILL.md`.
- The third-party project is experimental. Treat its docs as a capability snapshot.
- Jianying/CapCut and other non-Unreal MCP ecosystems remain outside the Unreal capability model. See `references/mcp-tools.md` § Public Case Boundary.
````

- [ ] **Step 3: Token-check the new file**

Run from worktree root:

```powershell
$t = Get-Content references/third-party-ecosystem.md -Raw
@('chongdashu/unreal-mcp', '55557', '%APPDATA%\\Claude\\claude_desktop_config.json', 'list_toolsets', 'Stack Identification', 'Tool Mapping', 'Decision Matrix', 'Client Configuration', 'Safety Boundaries', 'focus_viewport', 'create_blueprint', 'get_actors_in_level') | ForEach-Object {
  if ($t -notmatch [regex]::Escape($_)) { Write-Error "MISSING: $_"; exit 1 } else { Write-Host "OK: $_" }
}
```

Expected: every token prints `OK`. No `MISSING`.

Also confirm forbidden tokens are absent:

```powershell
$t = Get-Content references/third-party-ecosystem.md -Raw
@('/ue-mcp', 'ServerURLPath', 'Config/DefaultEngine.ini', 'manually delete', 'manual cleanup', 'ordinary users should', '%USERPROFILE%\.config\claude-desktop') | ForEach-Object {
  if ($t -match [regex]::Escape($_)) { Write-Error "FORBIDDEN PRESENT: $_"; exit 1 } else { Write-Host "OK absent: $_" }
}
```

Expected: all `OK absent`.

- [ ] **Step 4: Commit Task 1**

```powershell
git add references/third-party-ecosystem.md
git commit -m "docs: add third-party Unreal MCP ecosystem contrast reference"
```

---

### Task 2: Update `references/mcp-tools.md`

**Files:**
- Modify: `references/mcp-tools.md` (preamble line 3; Public Case Boundary ~L466–475)

**Interfaces:**
- Consumes: path `references/third-party-ecosystem.md` from Task 1.
- Produces: mcp-tools preamble that no longer claims exclusivity without pointer; Public Case Boundary names chongdashu and links the new reference.

- [ ] **Step 1: Reconcile the preamble**

Replace this exact line (line 3):

```
Use this reference after `SKILL.md` triggers and the task needs concrete MCP tool, Toolset, configuration, authoring, or diagnostic details. This reference covers Epic's official `ModelContextProtocol` / Unreal MCP path only.
```

With:

```
Use this reference after `SKILL.md` triggers and the task needs concrete MCP tool, Toolset, configuration, authoring, or diagnostic details. This reference covers Epic's official `ModelContextProtocol` / Unreal MCP path. For the third-party `chongdashu/unreal-mcp` stack, use `references/third-party-ecosystem.md` instead of inventing official Toolset names.
```

- [ ] **Step 2: Expand Public Case Boundary**

Replace the Public Case Boundary section (from `## Public Case Boundary` through the final sentence) with:

````markdown
## Public Case Boundary

Keep these public examples out of the official UE MCP capability model:

| Example type | What it can inform | What it must not imply |
|---|---|---|
| Jianying/CapCut MCP projects | General automation patterns and the need to distinguish runtime control from file/API wrappers | Toolset names, Unreal Editor capabilities, or official `ModelContextProtocol` behavior |
| Third-party Unreal MCP projects | Task ideas such as level generation, viewport verification, Blueprint automation, and project analysis | Replacement for official Tool Search, ToolsetRegistry, or schemas returned by `describe_toolset` |
| [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp) | Stack identification, fixed tool-name families, stdio + TCP 55557 transport, and UE 5.5+ plugin layout | Official Tool Search, ToolsetRegistry schemas, or Epic `ModelContextProtocol` behavior |

If a user asks about Jianying/CapCut control, answer that it is a separate MCP ecosystem. Official Unreal MCP controls the Unreal Editor, not Jianying/CapCut. If the live project uses `chongdashu/unreal-mcp`, follow `references/third-party-ecosystem.md` for identification and mapping; do not treat its tool names as official Toolsets.
````

- [ ] **Step 3: Verify mcp-tools constraints**

Run:

```powershell
$t = Get-Content references/mcp-tools.md -Raw
if ($t -notmatch 'chongdashu/unreal-mcp') { Write-Error 'missing chongdashu'; exit 1 }
if ($t -notmatch 'references/third-party-ecosystem\.md') { Write-Error 'missing link'; exit 1 }
if ($t -match '/ue-mcp') { Write-Error 'forbidden /ue-mcp'; exit 1 }
if ($t -match 'ServerURLPath') { Write-Error 'forbidden ServerURLPath'; exit 1 }
Write-Host 'mcp-tools OK'
& $env:MIMO_PYTHON scripts/validate-skill.py
```

Expected: `mcp-tools OK` and `Skill validation passed.`

- [ ] **Step 4: Commit Task 2**

```powershell
git add references/mcp-tools.md
git commit -m "docs: name chongdashu stack in mcp-tools boundary and preamble"
```

---

### Task 3: Update `SKILL.md`

**Files:**
- Modify: `SKILL.md` frontmatter `description` (line 3), `## Runtime Boundaries` (L176–182), `## References` (L184–189)

**Interfaces:**
- Consumes: `references/third-party-ecosystem.md` from Task 1.
- Produces: description that can activate on third-party identification; References pointer used by agents.

- [ ] **Step 1: Extend the frontmatter description**

Replace:

```
description: Use when a task targets Unreal Editor 5.8+ through Epic's official MCP, or when its MCP connection, Toolsets, schemas, plugins, or editor state are unavailable, stale, or incomplete.
```

With:

```
description: Use when a task targets Unreal Editor 5.8+ through Epic's official MCP, when a third-party Unreal MCP stack such as chongdashu/unreal-mcp must be identified or mapped to official Toolsets, or when its MCP connection, Toolsets, schemas, plugins, or editor state are unavailable, stale, or incomplete.
```

Keep `name: unreal-mcp` unchanged.

- [ ] **Step 2: Add Runtime Boundaries bullet**

After the existing bullet `Refresh tools after Python/C++ Toolset registration, hot reload, or Game Feature activation.`, insert:

```
- Third-party Unreal MCP stacks such as `chongdashu/unreal-mcp` use fixed tool names, stdio transport, and a TCP bridge; they are not Tool Search / ToolsetRegistry sessions. Identify the live stack before discovery — see `references/third-party-ecosystem.md`.
```

- [ ] **Step 3: Add References pointer**

Append to the References list:

```
- `references/third-party-ecosystem.md`: third-party stack identification, tool mapping, decision matrix, and client-config boundaries.
```

- [ ] **Step 4: Verify SKILL.md contract tokens still present**

Run:

```powershell
$skill = Get-Content SKILL.md -Raw
@('name: unreal-mcp', '/unreal-mcp', '$unreal-mcp', 'Agent Automation Contract', 'list_toolsets', 'describe_toolset', 'call_tool', 'independent read', 'dirty-state', 'minimal blocker', 'references/configure-workflow.md', 'references/uasset-read-comparison.md', 'references/third-party-ecosystem.md', 'chongdashu/unreal-mcp') | ForEach-Object {
  if ($skill -notmatch [regex]::Escape($_)) { Write-Error "MISSING: $_"; exit 1 } else { Write-Host "OK: $_" }
}
if ($skill -match '/ue-mcp') { Write-Error 'forbidden /ue-mcp'; exit 1 }
& $env:MIMO_PYTHON scripts/validate-skill.py
```

Expected: all `OK`, then `Skill validation passed.`

- [ ] **Step 5: Commit Task 3**

```powershell
git add SKILL.md
git commit -m "docs: activate skill on third-party Unreal MCP identification"
```

---

### Task 4: Update `README.md`

**Files:**
- Modify: `README.md` (after `## Official Reference`)

**Interfaces:**
- Consumes: GitHub URL `https://github.com/chongdashu/unreal-mcp`.
- Produces: user-facing note that this skill documents but does not operate the third-party stack.

- [ ] **Step 1: Append a third-party section**

After the existing `## Official Reference` list, add:

````markdown
## Related Third-Party Stack

This skill targets Epic's official Unreal MCP. The community project [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp) is a separate C++ plugin plus Python MCP server (UE 5.5+, stdio + TCP 55557). The skill can identify that stack and map its tools to official Toolset baselines via `references/third-party-ecosystem.md`; it does not configure or operate that server. Prefer official MCP on UE 5.8+.
````

Do not modify the `text` command fence, the install line, or any `/ue-mcp` entry inside the fence (those are required exact tokens).

- [ ] **Step 2: Verify README contract**

Run:

```powershell
$readme = Get-Content README.md -Raw
if ($readme -notmatch 'npx skills add soatori/unreal-mcp-skills') { Write-Error 'missing install'; exit 1 }
if ($readme -notmatch 'chongdashu/unreal-mcp') { Write-Error 'missing third-party note'; exit 1 }
if ($readme -notmatch 'third-party-ecosystem\.md') { Write-Error 'missing reference link'; exit 1 }
# /ue-mcp is allowed only inside the text fence; validator enforces this
& $env:MIMO_PYTHON scripts/validate-skill.py
```

Expected: no errors, `Skill validation passed.`

- [ ] **Step 3: Commit Task 4**

```powershell
git add README.md
git commit -m "docs: note related third-party Unreal MCP stack in README"
```

---

### Task 5: Full validation and Spec task checklist

**Files:**
- Modify: none (verification only); optionally tick Spec tasks in `docs/compose/spec/third-party-ecosystem-contrast.md` if implementing now

**Interfaces:**
- Consumes: all prior file states.
- Produces: green validator + Spec tasks T1–T5 marked complete when this plan is fully executed.

- [ ] **Step 1: Run the package validator from worktree root**

```powershell
& $env:MIMO_PYTHON scripts/validate-skill.py
```

Expected: `Skill validation passed.` exit 0.

- [ ] **Step 2: Run the existing unit tests**

```powershell
& $env:MIMO_PYTHON -m unittest discover -s tests -v
```

Expected: all tests pass (pre-existing suite; this feature adds no tests).

- [ ] **Step 3: Cross-file link check**

```powershell
$skill = Get-Content SKILL.md -Raw
$mcp = Get-Content references/mcp-tools.md -Raw
$readme = Get-Content README.md -Raw
$ref = Get-Content references/third-party-ecosystem.md -Raw
@(
  @{n='SKILL->ref'; ok=($skill -match 'references/third-party-ecosystem\.md')},
  @{n='mcp-tools->ref'; ok=($mcp -match 'references/third-party-ecosystem\.md')},
  @{n='README->ref'; ok=($readme -match 'third-party-ecosystem\.md')},
  @{n='ref has upstream'; ok=($ref -match 'chongdashu/unreal-mcp')},
  @{n='ref Claude Desktop path'; ok=($ref -match '%APPDATA%\\Claude\\claude_desktop_config\.json')}
) | ForEach-Object { if (-not $_.ok) { Write-Error "FAIL $($_.n)"; exit 1 } else { Write-Host "OK $($_.n)" } }
```

Expected: all `OK`.

- [ ] **Step 4: Show final diff summary**

```powershell
git log --oneline main..HEAD
git diff --stat main..HEAD
```

Expected: four documentation commits; `references/third-party-ecosystem.md` added; `SKILL.md`, `README.md`, `references/mcp-tools.md` modified; no changes under `scripts/`, `tests/`, `evals/`.

- [ ] **Step 5: Tick Spec tasks if this execution is the implementation**

In `docs/compose/spec/third-party-ecosystem-contrast.md`, change `- [ ] T1` … `- [ ] T5` to `- [x]` only when each acceptance criterion above has been verified. Commit as docs if changed:

```powershell
git add docs/compose/spec/third-party-ecosystem-contrast.md
git commit -m "docs: mark third-party contrast spec tasks complete"
```

---

## Self-Review Notes (plan author)

1. **Spec coverage:** S2.1 stack ID → Task 1 `## Stack Identification`. S2.2 mapping → Task 1 `## Tool Mapping`. S2.3 matrix → Task 1 `## Decision Matrix`. S2.4 client configs → Task 1 `## Client Configuration`. S2.5 safety → Task 1 `## Safety Boundaries`. S2.6 file edits → Tasks 2–4. Validation → Tasks 1/2/3/4/5. No Spec requirement is unassigned.
2. **Placeholders:** Full markdown bodies and exact replace strings are inlined. No TBD.
3. **Type/name consistency:** Reference path is always `references/third-party-ecosystem.md`. Claude Desktop path always `%APPDATA%\Claude\claude_desktop_config.json`. Tool names match Spec S2.2 list only.
