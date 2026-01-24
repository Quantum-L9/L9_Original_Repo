#!/usr/bin/env python3
"""
============================================================================
L9 Secure AI OS - Version Manager
============================================================================
Semantic versioning automation for L9

Version: 1.0.0
Last Updated: 2026-01-22

Features:
- Semantic versioning (MAJOR.MINOR.PATCH)
- Automatic version bumping
- Changelog generation
- Git tag creation
- Version validation

Usage:
    python scripts/version_manager.py bump patch
    python scripts/version_manager.py bump minor
    python scripts/version_manager.py bump major
    python scripts/version_manager.py current
    python scripts/version_manager.py validate
============================================================================
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple

# ============================================================================
# Constants
# ============================================================================

VERSION_FILE = Path("VERSION")
PYPROJECT_FILE = Path("pyproject.toml")
CHANGELOG_FILE = Path("CHANGELOG.md")

# Semantic versioning regex
SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$")

# ============================================================================
# Version Class
# ============================================================================

class Version:
    """Semantic version representation"""
    
    def __init__(self, major: int, minor: int, patch: int, prerelease: str = "", build: str = ""):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease
        self.build = build
    
    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """Parse version string into Version object"""
        match = SEMVER_PATTERN.match(version_str.strip())
        if not match:
            raise ValueError(f"Invalid semantic version: {version_str}")
        
        major, minor, patch, prerelease, build = match.groups()
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease or "",
            build=build or "",
        )
    
    def bump_major(self) -> "Version":
        """Bump major version (breaking changes)"""
        return Version(self.major + 1, 0, 0)
    
    def bump_minor(self) -> "Version":
        """Bump minor version (new features)"""
        return Version(self.major, self.minor + 1, 0)
    
    def bump_patch(self) -> "Version":
        """Bump patch version (bug fixes)"""
        return Version(self.major, self.minor, self.patch + 1)
    
    def __str__(self) -> str:
        """String representation"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version
    
    def __repr__(self) -> str:
        return f"Version({self})"

# ============================================================================
# Version Management Functions
# ============================================================================

def read_version() -> Version:
    """Read current version from VERSION file"""
    if not VERSION_FILE.exists():
        raise FileNotFoundError(f"VERSION file not found: {VERSION_FILE}")
    
    version_str = VERSION_FILE.read_text().strip()
    return Version.parse(version_str)

def write_version(version: Version) -> None:
    """Write version to VERSION file"""
    VERSION_FILE.write_text(f"{version}\n")
    print(f"✅ Updated VERSION file: {version}")

def update_pyproject_version(version: Version) -> None:
    """Update version in pyproject.toml"""
    if not PYPROJECT_FILE.exists():
        print(f"⚠️  pyproject.toml not found, skipping")
        return
    
    content = PYPROJECT_FILE.read_text()
    
    # Update version line
    updated = re.sub(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
        content,
        flags=re.MULTILINE,
    )
    
    PYPROJECT_FILE.write_text(updated)
    print(f"✅ Updated pyproject.toml: {version}")

def update_changelog(version: Version, bump_type: str) -> None:
    """Update CHANGELOG.md with new version"""
    if not CHANGELOG_FILE.exists():
        # Create new changelog
        content = f"""# Changelog

All notable changes to L9 Secure AI OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [{version}] - {datetime.now().strftime("%Y-%m-%d")}

### {get_changelog_section(bump_type)}
- Version bump: {bump_type}

"""
        CHANGELOG_FILE.write_text(content)
        print(f"✅ Created CHANGELOG.md")
    else:
        # Update existing changelog
        content = CHANGELOG_FILE.read_text()
        
        # Find [Unreleased] section
        unreleased_pattern = r"## \[Unreleased\]"
        
        new_entry = f"""## [Unreleased]

## [{version}] - {datetime.now().strftime("%Y-%m-%d")}

### {get_changelog_section(bump_type)}
- Version bump: {bump_type}

"""
        
        updated = re.sub(
            unreleased_pattern,
            new_entry,
            content,
            count=1,
        )
        
        CHANGELOG_FILE.write_text(updated)
        print(f"✅ Updated CHANGELOG.md")

def get_changelog_section(bump_type: str) -> str:
    """Get appropriate changelog section for bump type"""
    if bump_type == "major":
        return "Changed"  # Breaking changes
    elif bump_type == "minor":
        return "Added"  # New features
    elif bump_type == "patch":
        return "Fixed"  # Bug fixes
    else:
        return "Changed"

def create_git_tag(version: Version) -> None:
    """Create git tag for version"""
    tag_name = f"v{version}"
    
    try:
        # Check if tag already exists
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            capture_output=True,
            text=True,
            check=True,
        )
        
        if result.stdout.strip():
            print(f"⚠️  Git tag {tag_name} already exists")
            return
        
        # Create annotated tag
        subprocess.run(
            ["git", "tag", "-a", tag_name, "-m", f"Release {version}"],
            check=True,
        )
        print(f"✅ Created git tag: {tag_name}")
        
        # Push tag
        push = input(f"Push tag {tag_name} to remote? (y/N): ")
        if push.lower() == "y":
            subprocess.run(["git", "push", "origin", tag_name], check=True)
            print(f"✅ Pushed tag to remote: {tag_name}")
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Git tag creation failed: {e}")

def validate_version() -> bool:
    """Validate version consistency across files"""
    print("🔍 Validating version consistency...")
    
    # Read VERSION file
    version = read_version()
    print(f"  VERSION file: {version}")
    
    # Check pyproject.toml
    if PYPROJECT_FILE.exists():
        content = PYPROJECT_FILE.read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if match:
            pyproject_version = match.group(1)
            print(f"  pyproject.toml: {pyproject_version}")
            
            if str(version) != pyproject_version:
                print(f"❌ Version mismatch!")
                return False
    
    print("✅ Version validation passed")
    return True

# ============================================================================
# CLI Commands
# ============================================================================

def cmd_current(args):
    """Show current version"""
    version = read_version()
    print(f"Current version: {version}")

def cmd_bump(args):
    """Bump version"""
    current = read_version()
    print(f"Current version: {current}")
    
    # Bump version
    if args.type == "major":
        new_version = current.bump_major()
        print(f"⚠️  MAJOR version bump (breaking changes)")
    elif args.type == "minor":
        new_version = current.bump_minor()
        print(f"📦 MINOR version bump (new features)")
    elif args.type == "patch":
        new_version = current.bump_patch()
        print(f"🐛 PATCH version bump (bug fixes)")
    else:
        print(f"❌ Invalid bump type: {args.type}")
        sys.exit(1)
    
    print(f"New version: {new_version}")
    
    # Confirm
    if not args.yes:
        confirm = input(f"Bump version to {new_version}? (y/N): ")
        if confirm.lower() != "y":
            print("❌ Aborted")
            sys.exit(0)
    
    # Update files
    write_version(new_version)
    update_pyproject_version(new_version)
    update_changelog(new_version, args.type)
    
    # Create git tag
    if args.tag:
        create_git_tag(new_version)
    
    print(f"\n✅ Version bumped to {new_version}")
    print(f"\nNext steps:")
    print(f"  1. Review CHANGELOG.md")
    print(f"  2. Commit changes: git add VERSION pyproject.toml CHANGELOG.md")
    print(f"  3. Commit: git commit -m 'chore: bump version to {new_version}'")
    if not args.tag:
        print(f"  4. Create tag: git tag -a v{new_version} -m 'Release {new_version}'")
        print(f"  5. Push: git push && git push --tags")

def cmd_validate(args):
    """Validate version consistency"""
    if validate_version():
        sys.exit(0)
    else:
        sys.exit(1)

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="L9 Semantic Version Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current version
  python scripts/version_manager.py current
  
  # Bump patch version (bug fixes)
  python scripts/version_manager.py bump patch
  
  # Bump minor version (new features)
  python scripts/version_manager.py bump minor
  
  # Bump major version (breaking changes)
  python scripts/version_manager.py bump major --tag
  
  # Validate version consistency
  python scripts/version_manager.py validate

Semantic Versioning:
  MAJOR.MINOR.PATCH
  
  MAJOR: Breaking changes (incompatible API changes)
  MINOR: New features (backward-compatible)
  PATCH: Bug fixes (backward-compatible)
""",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # current command
    subparsers.add_parser("current", help="Show current version")
    
    # bump command
    bump_parser = subparsers.add_parser("bump", help="Bump version")
    bump_parser.add_argument(
        "type",
        choices=["major", "minor", "patch"],
        help="Version component to bump",
    )
    bump_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    bump_parser.add_argument(
        "-t", "--tag",
        action="store_true",
        help="Create git tag",
    )
    
    # validate command
    subparsers.add_parser("validate", help="Validate version consistency")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == "current":
        cmd_current(args)
    elif args.command == "bump":
        cmd_bump(args)
    elif args.command == "validate":
        cmd_validate(args)

if __name__ == "__main__":
    main()
