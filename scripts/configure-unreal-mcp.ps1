param(
    [string]$ProjectPath = ".",
    [ValidateSet("claude", "codex", "cursor", "vscode", "gemini", "all")]
    [string]$Target = "all",
    [int]$Port = 8000,
    [switch]$AutoStart,
    [switch]$EnablePlugins,
    [switch]$Verify,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Resolve-UProject {
    param([string]$Path)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    $item = Get-Item -LiteralPath $resolved

    if ($item.PSIsContainer) {
        $projects = Get-ChildItem -LiteralPath $item.FullName -Filter "*.uproject" -File
        if ($projects.Count -eq 0) {
            throw "No .uproject file found in '$($item.FullName)'. Pass -ProjectPath with a UE project root or .uproject file."
        }
        if ($projects.Count -gt 1) {
            $names = ($projects | ForEach-Object { $_.Name }) -join ", "
            throw "Multiple .uproject files found in '$($item.FullName)': $names. Pass the exact .uproject path."
        }
        return $projects[0]
    }

    if ($item.Extension -ne ".uproject") {
        throw "ProjectPath must point to a UE project directory or .uproject file."
    }
    return $item
}

function ConvertFrom-JsonFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{}
    }

    $text = Get-Content -Raw -LiteralPath $Path
    if ([string]::IsNullOrWhiteSpace($text)) {
        return [pscustomobject]@{}
    }
    return $text | ConvertFrom-Json
}

function Write-JsonFile {
    param(
        [string]$Path,
        [object]$Value
    )

    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $Value | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Ensure-ObjectProperty {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Value
    )

    if ($Object.PSObject.Properties.Name -contains $Name) {
        $Object.$Name = $Value
    } else {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
}

function Show-Plan {
    param([string]$Message)
    if ($DryRun) {
        Write-Host "[dry-run] $Message"
    } else {
        Write-Host $Message
    }
}

function Enable-UProjectPlugins {
    param([string]$UProjectPath)

    $project = ConvertFrom-JsonFile -Path $UProjectPath
    if (-not ($project.PSObject.Properties.Name -contains "Plugins") -or $null -eq $project.Plugins) {
        Ensure-ObjectProperty -Object $project -Name "Plugins" -Value @()
    }

    $plugins = @($project.Plugins)
    $changed = $false

    foreach ($pluginName in @("ModelContextProtocol", "ToolsetRegistry")) {
        $entry = $plugins | Where-Object { $_.Name -eq $pluginName } | Select-Object -First 1
        if ($entry) {
            if ($entry.Enabled -ne $true) {
                $entry.Enabled = $true
                $changed = $true
            }
        } else {
            $plugins += [pscustomobject]@{
                Name = $pluginName
                Enabled = $true
            }
            $changed = $true
        }
    }

    if ($changed) {
        Ensure-ObjectProperty -Object $project -Name "Plugins" -Value $plugins
        Show-Plan "Enable ModelContextProtocol and ToolsetRegistry in $UProjectPath"
        if (-not $DryRun) {
            Write-JsonFile -Path $UProjectPath -Value $project
        }
    } else {
        Write-Host "Plugins already enabled in $UProjectPath"
    }
}

function Set-IniValue {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Section,
        [string]$Key,
        [string]$Value
    )

    $sectionLine = "[$Section]"
    $sectionIndex = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim() -eq $sectionLine) {
            $sectionIndex = $i
            break
        }
    }

    if ($sectionIndex -lt 0) {
        if ($Lines.Count -gt 0 -and $Lines[$Lines.Count - 1].Trim() -ne "") {
            $Lines.Add("")
        }
        $Lines.Add($sectionLine)
        $Lines.Add("$Key=$Value")
        return
    }

    $insertAt = $Lines.Count
    for ($i = $sectionIndex + 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].Trim().StartsWith("[") -and $Lines[$i].Trim().EndsWith("]")) {
            $insertAt = $i
            break
        }
        if ($Lines[$i] -match "^\s*$([regex]::Escape($Key))\s*=") {
            $Lines[$i] = "$Key=$Value"
            return
        }
    }
    $Lines.Insert($insertAt, "$Key=$Value")
}

function Configure-EditorSettings {
    param(
        [string]$ProjectRoot,
        [int]$Port
    )

    $configDir = Join-Path $ProjectRoot "Config"
    $engineIni = Join-Path $configDir "DefaultEngine.ini"
    $lines = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $engineIni) {
        foreach ($line in Get-Content -LiteralPath $engineIni) {
            $lines.Add($line)
        }
    }

    $section = "/Script/ModelContextProtocol.ModelContextProtocolSettings"
    Set-IniValue -Lines $lines -Section $section -Key "bAutoStartServer" -Value "True"
    Set-IniValue -Lines $lines -Section $section -Key "ServerPortNumber" -Value $Port
    Set-IniValue -Lines $lines -Section $section -Key "ServerURLPath" -Value "/mcp"
    Set-IniValue -Lines $lines -Section $section -Key "bEnableToolSearch" -Value "True"

    Show-Plan "Configure Unreal MCP editor settings in $engineIni"
    if (-not $DryRun) {
        if (-not (Test-Path -LiteralPath $configDir)) {
            New-Item -ItemType Directory -Force -Path $configDir | Out-Null
        }
        Set-Content -LiteralPath $engineIni -Value $lines -Encoding UTF8
    }
}

function Merge-McpJsonConfig {
    param(
        [string]$Path,
        [hashtable]$ServerEntry
    )

    $config = ConvertFrom-JsonFile -Path $Path
    if (-not ($config.PSObject.Properties.Name -contains "mcpServers") -or $null -eq $config.mcpServers) {
        Ensure-ObjectProperty -Object $config -Name "mcpServers" -Value ([pscustomobject]@{})
    }

    $entryObject = [pscustomobject]$ServerEntry
    if ($config.mcpServers.PSObject.Properties.Name -contains "unreal-mcp") {
        $config.mcpServers."unreal-mcp" = $entryObject
    } else {
        $config.mcpServers | Add-Member -NotePropertyName "unreal-mcp" -NotePropertyValue $entryObject
    }

    Show-Plan "Merge unreal-mcp server into $Path"
    if (-not $DryRun) {
        Write-JsonFile -Path $Path -Value $config
    }
}

function Write-CodexConfig {
    param(
        [string]$Path,
        [string]$Url
    )

    if (Test-Path -LiteralPath $Path) {
        throw "Codex config already exists at '$Path'. UE's Codex TOML generation is write-once; delete or edit the stale file manually before regenerating."
    }

    $dir = Split-Path -Parent $Path
    Show-Plan "Create Codex MCP config at $Path"
    if (-not $DryRun) {
        if (-not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
        @"
[mcp_servers.unreal-mcp]
url = "$Url"
"@ | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

function Configure-Client {
    param(
        [string]$ProjectRoot,
        [string]$Client,
        [string]$Url
    )

    switch ($Client) {
        "claude" {
            Merge-McpJsonConfig -Path (Join-Path $ProjectRoot ".mcp.json") -ServerEntry @{
                type = "http"
                url = $Url
                disabled = $false
            }
        }
        "cursor" {
            Merge-McpJsonConfig -Path (Join-Path $ProjectRoot ".cursor/mcp.json") -ServerEntry @{
                url = $Url
            }
        }
        "vscode" {
            Merge-McpJsonConfig -Path (Join-Path $ProjectRoot ".vscode/mcp.json") -ServerEntry @{
                url = $Url
            }
        }
        "gemini" {
            Merge-McpJsonConfig -Path (Join-Path $ProjectRoot ".gemini/settings.json") -ServerEntry @{
                httpUrl = $Url
            }
        }
        "codex" {
            Write-CodexConfig -Path (Join-Path $ProjectRoot ".codex/config.toml") -Url $Url
        }
    }
}

function Get-EditorClientName {
    param([string]$Client)

    switch ($Client) {
        "claude" { return "ClaudeCode" }
        "codex" { return "Codex" }
        "cursor" { return "Cursor" }
        "vscode" { return "VSCode" }
        "gemini" { return "Gemini" }
        "all" { return "All" }
    }
}

if ($Port -lt 1 -or $Port -gt 65535) {
    throw "Port must be in range 1..65535."
}

$uproject = Resolve-UProject -Path $ProjectPath
$projectRoot = $uproject.Directory.FullName
$serverUrl = "http://127.0.0.1:$Port/mcp"

Write-Host "UE project: $($uproject.FullName)"
Write-Host "Target: $Target"
Write-Host "Server URL: $serverUrl"

$clients = if ($Target -eq "all") {
    @("claude", "codex", "cursor", "vscode", "gemini")
} else {
    @($Target)
}

if ($clients -contains "codex") {
    $codexPath = Join-Path $projectRoot ".codex/config.toml"
    if (Test-Path -LiteralPath $codexPath) {
        throw "Codex config already exists at '$codexPath'. UE's Codex TOML generation is write-once; delete or edit the stale file manually before regenerating. No changes were written."
    }
}

if ($EnablePlugins -or $Target -eq "all") {
    Enable-UProjectPlugins -UProjectPath $uproject.FullName
} else {
    Write-Host "Plugin changes skipped. Pass -EnablePlugins or use -Target all to enable ModelContextProtocol and ToolsetRegistry."
}

if ($AutoStart -or $Target -eq "all") {
    Configure-EditorSettings -ProjectRoot $projectRoot -Port $Port
    Write-Host "Editor settings are written as project defaults. If UE ignores a setting name in this engine version, set Auto Start Server in Editor Preferences > General > Model Context Protocol."
} else {
    Write-Host "Auto Start changes skipped. Pass -AutoStart or use -Target all."
}

foreach ($client in $clients) {
    Configure-Client -ProjectRoot $projectRoot -Client $client -Url $serverUrl
}

Write-Host ""
Write-Host "Editor console fallback:"
Write-Host "  ModelContextProtocol.StartServer $Port"
Write-Host "  ModelContextProtocol.GenerateClientConfig $(Get-EditorClientName -Client $Target)"

if ($Verify) {
    Write-Host ""
    Write-Host "Verifying $serverUrl ..."
    try {
        $response = Invoke-WebRequest -Uri $serverUrl -Method Get -TimeoutSec 3 -UseBasicParsing
        Write-Host "Server responded with HTTP $($response.StatusCode). Launch the agent from '$projectRoot' and call list_toolsets."
    } catch {
        Write-Host "No HTTP response from $serverUrl. Start the UE editor, enable Auto Start or run ModelContextProtocol.StartServer $Port, then reconnect the agent."
    }
}
