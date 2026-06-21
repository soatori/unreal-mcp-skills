# Finding Unreal Editor Installations

This reference explains how to discover locally installed Unreal Engine editor installations and record them to memory for future use.

## Why This Matters

When working with Unreal Engine projects, it's useful to know which editor versions are available on the local system. This enables:
- Quickly identifying the correct editor to launch
- Verifying that the required UE version is installed
- Recording installation paths for automation scripts
- Troubleshooting version mismatches between project and editor

## Discovery Methods

The `scripts/find-ue-installations.py` script uses three methods to find UE installations:

### 1. Epic Games Launcher Manifest

The Epic Games Launcher stores installed engine information in a manifest file:

- **Location**: `%PROGRAMDATA%\Epic\EpicGamesLauncher\Data\Manifest.xml`
- **Fallback**: `%LOCALAPPDATA%\Epic\EpicGamesLauncher\Saved\Config\Windows\Manifest.xml`

The script parses this XML to find `InstalledItems` and checks each path for `Engine\Binaries\Win64\UnrealEditor.exe`.

### 2. Windows Registry

UE installations are registered in the Windows registry:

- `HKEY_LOCAL_MACHINE\SOFTWARE\EpicGames\Unreal Engine`
- `HKEY_CURRENT_USER\SOFTWARE\EpicGames\Unreal Engine`

Each subkey contains an `InstalledDirectory` value pointing to the installation root.

### 3. Common Default Paths

The script checks standard installation directories:

```
C:\Program Files\Epic Games\UE_5.x
D:\Program Files\Epic Games\UE_5.x
E:\Program Files\Epic Games\UE_5.x
C:\Epic Games\UE_5.x
D:\Epic Games\UE_5.x
E:\Epic Games\UE_5.x
```

## Version Detection

The script attempts to detect the UE version from:

1. **Build.version file**: Located at `Engine\Build\Build.version` in the installation directory. Contains major, minor, and patch version numbers on separate lines.

2. **Directory name**: If the directory is named `UE_5.x`, the version is extracted from the name.

## Usage

### Run the discovery script

```bash
python scripts/find-ue-installations.py
```

Output format:
```json
{
  "installations": [
    {
      "path": "C:\\Program Files\\Epic Games\\UE_5.4",
      "editor_exe": "C:\\Program Files\\Epic Games\\UE_5.4\\Engine\\Binaries\\Win64\\UnrealEditor.exe",
      "version": "5.4.0",
      "source": "epic_games_launcher"
    }
  ],
  "count": 1
}
```

### Record to memory

After discovering installations, record the paths to memory for future sessions:

```python
# Example: Record to Claude memory
memory_key = "ue_installations"
memory_value = {
    "installations": [...],  # From script output
    "discovered_at": "2026-06-21T20:00:00Z",
    "system": "windows"
}
```

### Use in automation

The discovered paths can be used to:
- Launch the editor: `"C:\...\UnrealEditor.exe" "path/to/project.uproject"`
- Verify version compatibility
- Configure CI/CD pipelines

## Troubleshooting

### No installations found

1. **Epic Games Launcher not installed**: Install from https://www.unrealengine.com/download
2. **No engines installed**: Open Epic Games Launcher and install an engine version
3. **Custom installation path**: Add your custom path to the `common_bases` list in the script
4. **Permissions**: Run the script with appropriate permissions to read registry keys

### Version shows as "unknown"

- The `Build.version` file may not exist in older UE versions
- The script falls back to parsing the directory name

### Multiple versions detected

This is expected if you have multiple UE versions installed. The script deduplicates based on normalized paths.
