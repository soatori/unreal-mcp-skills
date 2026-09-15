# Finding Unreal Editor Installations

Use this reference for `/unreal-mcp:find-installations` and any task that needs verified local editor paths and versions.

## Discovery Methods

The `scripts/find-ue-installations.py` script uses two methods to find UE installations:

### 1. Windows Registry

UE installations are registered in the Windows registry:

- `HKEY_LOCAL_MACHINE\SOFTWARE\EpicGames\Unreal Engine`
- `HKEY_CURRENT_USER\SOFTWARE\EpicGames\Unreal Engine`

Each subkey contains an `InstalledDirectory` value pointing to the installation root.

### 2. Common Default Paths

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

1. **Build.version file**: Located at `Engine\Build\Build.version`. UE 5.x writes JSON (`MajorVersion` / `MinorVersion` / `PatchVersion`); older builds used one component per line. The script reads JSON first, then falls back to the line format.

2. **Directory name**: If `Build.version` is missing and the directory is named `UE_5.x`, the version is extracted from the name.

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
      "source": "registry"
    }
  ],
  "count": 1
}
```

### Use in automation

The discovered paths can be used to:
- Launch the editor: `"C:\...\UnrealEditor.exe" "path/to/project.uproject"`
- Verify version compatibility against the project
- Feed launch/restart recovery in the configure workflow

Multiple versions are expected when several engines are installed; the script deduplicates on normalized paths. A `version` of `unknown` means `Build.version` was missing and the directory name was not `UE_5.x`.
