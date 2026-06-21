#!/usr/bin/env python3
"""Find locally installed Unreal Engine editor installations."""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def find_epic_games_launcher_installations() -> list[dict[str, Any]]:
    """Find UE installations via Epic Games Launcher manifest."""
    installations = []

    # Common manifest locations
    manifest_paths = [
        Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "Epic" / "EpicGamesLauncher" / "Data" / "Manifest.xml",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Epic" / "EpicGamesLauncher" / "Saved" / "Config" / "Windows" / "Manifest.xml",
    ]

    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue

        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()

            # Look for InstalledItems
            for item in root.findall(".//InstalledItems"):
                for child in item:
                    install_location = child.text
                    if install_location:
                        install_path = Path(install_location)
                        if install_path.exists():
                            # Check for UnrealEditor.exe
                            editor_exe = install_path / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
                            if editor_exe.exists():
                                # Try to detect version from the path or ini
                                version = detect_version(install_path)
                                installations.append({
                                    "path": str(install_path),
                                    "editor_exe": str(editor_exe),
                                    "version": version,
                                    "source": "epic_games_launcher"
                                })
        except (ET.ParseError, OSError):
            continue

    return installations


def find_registry_installations() -> list[dict[str, Any]]:
    """Find UE installations via Windows registry."""
    installations = []

    try:
        import winreg
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EpicGames\Unreal Engine"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\EpicGames\Unreal Engine"),
        ]

        for hkey, key_path in registry_keys:
            try:
                with winreg.OpenKey(hkey, key_path) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    install_location, _ = winreg.QueryValueEx(subkey, "InstalledDirectory")
                                    install_path = Path(install_location)
                                    if install_path.exists():
                                        editor_exe = install_path / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
                                        if editor_exe.exists():
                                            version = detect_version(install_path)
                                            installations.append({
                                                "path": str(install_path),
                                                "editor_exe": str(editor_exe),
                                                "version": version,
                                                "source": "registry"
                                            })
                                except (FileNotFoundError, OSError):
                                    pass
                            i += 1
                        except OSError:
                            break
            except (FileNotFoundError, OSError):
                continue
    except ImportError:
        # winreg not available (non-Windows)
        pass

    return installations


def find_common_paths() -> list[dict[str, Any]]:
    """Find UE installations in common default locations."""
    installations = []

    # Common installation directories
    common_bases = [
        Path("C:/Program Files/Epic Games"),
        Path("D:/Program Files/Epic Games"),
        Path("E:/Program Files/Epic Games"),
        Path("C:/Epic Games"),
        Path("D:/Epic Games"),
        Path("E:/Epic Games"),
    ]

    for base in common_bases:
        if not base.exists():
            continue

        # Look for UE_5.x directories
        for item in base.iterdir():
            if item.is_dir() and item.name.startswith("UE_"):
                editor_exe = item / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
                if editor_exe.exists():
                    version = detect_version(item)
                    installations.append({
                        "path": str(item),
                        "editor_exe": str(editor_exe),
                        "version": version,
                        "source": "common_path"
                    })

    return installations


def detect_version(install_path: Path) -> str:
    """Try to detect UE version from the installation."""
    # Try to read from Build.version
    build_version = install_path / "Engine" / "Build" / "Build.version"
    if build_version.exists():
        try:
            content = build_version.read_text(encoding="utf-8").strip()

            # Try JSON format first (UE 5.x)
            if content.startswith("{"):
                import json
                data = json.loads(content)
                major = data.get("MajorVersion", 0)
                minor = data.get("MinorVersion", 0)
                patch = data.get("PatchVersion", 0)
                return f"{major}.{minor}.{patch}"

            # Try line-based format (older versions)
            lines = content.split("\n")
            if len(lines) >= 4:
                major = lines[0].strip()
                minor = lines[1].strip()
                patch = lines[2].strip()
                return f"{major}.{minor}.{patch}"
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    # Fallback: try to extract from directory name
    if install_path.name.startswith("UE_"):
        return install_path.name[3:]  # Remove "UE_" prefix

    return "unknown"


def deduplicate_installations(installations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate installations based on path."""
    seen_paths: set[str] = set()
    unique = []

    for inst in installations:
        normalized = str(Path(inst["path"]).resolve())
        if normalized not in seen_paths:
            seen_paths.add(normalized)
            unique.append(inst)

    return unique


def main() -> int:
    """Main entry point."""
    all_installations = []

    # Search in parallel (conceptually - Python GIL makes true parallelism limited)
    all_installations.extend(find_epic_games_launcher_installations())
    all_installations.extend(find_registry_installations())
    all_installations.extend(find_common_paths())

    # Deduplicate
    installations = deduplicate_installations(all_installations)

    # Output as JSON
    output = {
        "installations": installations,
        "count": len(installations)
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
