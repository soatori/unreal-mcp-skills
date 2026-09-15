#!/usr/bin/env python3
"""Find locally installed Unreal Engine editor installations."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def find_registry_installations() -> list[dict[str, Any]]:
    """Find UE installations via Windows registry."""
    installations: list[dict[str, Any]] = []

    try:
        import winreg
    except ImportError:
        return installations

    registry_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EpicGames\Unreal Engine"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\EpicGames\Unreal Engine"),
    ]

    for hkey, key_path in registry_keys:
        try:
            with winreg.OpenKey(hkey, key_path) as key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                    except OSError:
                        break
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        try:
                            install_location, _ = winreg.QueryValueEx(subkey, "InstalledDirectory")
                        except (FileNotFoundError, OSError):
                            index += 1
                            continue
                    install_path = Path(install_location)
                    editor_exe = install_path / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
                    if install_path.exists() and editor_exe.exists():
                        installations.append({
                            "path": str(install_path),
                            "editor_exe": str(editor_exe),
                            "version": detect_version(install_path),
                            "source": "registry",
                        })
                    index += 1
        except (FileNotFoundError, OSError):
            continue

    return installations


def find_common_paths() -> list[dict[str, Any]]:
    """Find UE installations in common default locations."""
    installations: list[dict[str, Any]] = []
    common_bases = [
        Path("C:/Program Files/Epic Games"),
        Path("D:/Program Files/Epic Games"),
        Path("E:/Program Files/Epic Games"),
        Path("C:/Epic Games"),
        Path("D:/Epic Games"),
        Path("E:/Epic Games"),
    ]

    for base in common_bases:
        if not base.is_dir():
            continue
        for item in base.iterdir():
            if not item.is_dir() or not item.name.startswith("UE_"):
                continue
            editor_exe = item / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
            if editor_exe.exists():
                installations.append({
                    "path": str(item),
                    "editor_exe": str(editor_exe),
                    "version": detect_version(item),
                    "source": "common_path",
                })

    return installations


def detect_version(install_path: Path) -> str:
    """Detect UE version from Build.version, else the UE_ directory name."""
    build_version = install_path / "Engine" / "Build" / "Build.version"
    if build_version.exists():
        try:
            content = build_version.read_text(encoding="utf-8").strip()
            if content.startswith("{"):
                data = json.loads(content)
                major = data.get("MajorVersion", 0)
                minor = data.get("MinorVersion", 0)
                patch = data.get("PatchVersion", 0)
                return f"{major}.{minor}.{patch}"
            lines = content.split("\n")
            if len(lines) >= 3:
                return f"{lines[0].strip()}.{lines[1].strip()}.{lines[2].strip()}"
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    if install_path.name.startswith("UE_"):
        return install_path.name[3:]

    return "unknown"


def deduplicate_installations(installations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_paths: set[str] = set()
    unique: list[dict[str, Any]] = []
    for inst in installations:
        normalized = str(Path(inst["path"]).resolve())
        if normalized not in seen_paths:
            seen_paths.add(normalized)
            unique.append(inst)
    return unique


def main() -> int:
    all_installations = [
        *find_registry_installations(),
        *find_common_paths(),
    ]
    installations = deduplicate_installations(all_installations)
    print(json.dumps({"installations": installations, "count": len(installations)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
