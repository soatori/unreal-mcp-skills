$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$errors = [System.Collections.Generic.List[string]]::new()

function Add-Error {
    param([string]$Message)
    $script:errors.Add($Message)
}

function Require-File {
    param([string]$RelativePath)
    $path = Join-Path $root $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Error "Missing file: $RelativePath"
    }
    return $path
}

function Read-Text {
    param([string]$RelativePath)
    $path = Require-File -RelativePath $RelativePath
    if (Test-Path -LiteralPath $path) {
        return Get-Content -Raw -LiteralPath $path
    }
    return ""
}

$skill = Read-Text "SKILL.md"
$readme = Read-Text "README.md"
$metadataText = Read-Text "skills.sh.json"
$openai = Read-Text "agents/openai.yaml"

if ($skill -notmatch "(?m)^name:\s*unreal-mcp\s*$") {
    Add-Error "SKILL.md frontmatter must use name: unreal-mcp"
}
if ($skill -notmatch '/unreal-mcp' -or $skill -notmatch '/ue-mcp' -or $skill -notmatch '\$unreal-mcp') {
    Add-Error "SKILL.md must document /unreal-mcp, /ue-mcp, and `$unreal-mcp activation forms"
}
if ($skill -match "/unreal-mcp-skills" -and $skill -notmatch "Do not .*?/unreal-mcp-skills") {
    Add-Error "SKILL.md may mention /unreal-mcp-skills only to say it is not a command"
}
if ($skill -match "unreal-mcp-skills\\") {
    Add-Error "SKILL.md must not contain stale local unreal-mcp-skills runtime paths"
}
if ($skill -notmatch "references/configure-workflow\.md") {
    Add-Error "SKILL.md must point configuration tasks to references/configure-workflow.md"
}
if ($skill -notmatch "references/uasset-read-comparison\.md") {
    Add-Error "SKILL.md must point uasset comparison tasks to references/uasset-read-comparison.md"
}

if ($readme -notmatch "npx skills add soatori/unreal-mcp-skills") {
    Add-Error "README.md must keep the skills.sh install command"
}
if ($readme -match "/unreal-mcp-skills" -and $readme -notmatch 'Do not use `/unreal-mcp-skills`') {
    Add-Error "README.md may mention /unreal-mcp-skills only to say it is not a command"
}
if (($readme -notmatch "scripts/configure-unreal-mcp\.ps1" -and $readme -notmatch "\.\\scripts\\configure-unreal-mcp\.ps1") -or
    ($readme -notmatch "scripts/validate-skill\.ps1" -and $readme -notmatch "\.\\scripts\\validate-skill\.ps1")) {
    Add-Error "README.md must document configure and validation scripts"
}

try {
    $metadata = $metadataText | ConvertFrom-Json
    $entry = $metadata.skills | Select-Object -First 1
    if ($entry.name -ne "unreal-mcp-skills") {
        Add-Error "skills.sh.json first skill name must be unreal-mcp-skills"
    }
    if (-not ($entry.aliases -contains "ue-mcp-skills")) {
        Add-Error "skills.sh.json aliases must include ue-mcp-skills"
    }
    if ($entry.path -ne "SKILL.md") {
        Add-Error "skills.sh.json path must be SKILL.md"
    }
} catch {
    Add-Error "skills.sh.json is not valid JSON: $($_.Exception.Message)"
}

if ($openai -notmatch 'display_name:\s*"Unreal MCP"' -and $openai -notmatch "display_name:\s*'Unreal MCP'") {
    Add-Error "agents/openai.yaml display_name should be Unreal MCP"
}
if ($openai -notmatch '\$unreal-mcp') {
    Add-Error "agents/openai.yaml default_prompt should mention `$unreal-mcp"
}

foreach ($file in @(
    "references/examples/.mcp.json",
    "references/examples/.codex/config.toml",
    "references/examples/.cursor/mcp.json",
    "references/examples/.vscode/mcp.json",
    "references/examples/.gemini/settings.json",
    "references/configure-workflow.md",
    "references/uasset-read-comparison.md",
    "scripts/configure-unreal-mcp.ps1"
)) {
    Require-File -RelativePath $file | Out-Null
}

if ($errors.Count -gt 0) {
    Write-Host "Skill validation failed:" -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host " - $err" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Skill validation passed."
