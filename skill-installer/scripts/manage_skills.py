#!/usr/bin/env python3
"""Manage skill installation for projects via symlinks.

Skills are sourced from a local skills directory organized by provider.
Installation creates symlinks in the project's .claude/skills/,
.copilot/skills/, and .agents/skills/ directories so updates to skills
propagate automatically.

Usage:
    manage_skills.py list [--skills-root PATH]
    manage_skills.py installed --project PATH
    manage_skills.py install SKILL_NAME --project PATH [--skills-root PATH]
    manage_skills.py uninstall SKILL_NAME --project PATH
"""

import argparse
import os
import sys
import yaml


DEFAULT_SKILLS_ROOT = os.path.expanduser(
    "~/Documents/workspaces/skills"
)

SKIP_DIRS = {".git", "node_modules", "__pycache__", "template", "spec", ".claude-plugin"}
SKIP_SKILL_NAMES = {"template"}

# All target directories where skill symlinks are installed
SKILL_TARGET_DIRS = [
    os.path.join(".claude", "skills"),
    os.path.join(".copilot", "skills"),
    os.path.join(".agents", "skills"),
]


def parse_frontmatter(skill_md_path):
    """Extract YAML frontmatter from a SKILL.md file."""
    try:
        with open(skill_md_path, "r") as f:
            content = f.read()
    except (OSError, IOError):
        return None

    if not content.startswith("---"):
        return None

    end = content.find("---", 3)
    if end == -1:
        return None

    try:
        return yaml.safe_load(content[3:end])
    except yaml.YAMLError:
        return None


def discover_skills(skills_root):
    """Walk the skills root directory and find all available skills.

    Returns a list of dicts: {name, description, provider, path, category}
    """
    skills = []
    seen = set()

    for provider in sorted(os.listdir(skills_root)):
        provider_path = os.path.join(skills_root, provider)
        if not os.path.isdir(provider_path) or provider.startswith("."):
            continue

        for root, dirs, files in os.walk(provider_path):
            # Prune directories we don't want to descend into
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            if "SKILL.md" not in files:
                continue

            skill_dir = root
            skill_name = os.path.basename(skill_dir)

            if skill_name in SKIP_SKILL_NAMES:
                continue

            # Deduplicate by (provider, skill_name)
            key = (provider, skill_name)
            if key in seen:
                continue
            seen.add(key)

            frontmatter = parse_frontmatter(os.path.join(skill_dir, "SKILL.md"))
            name = frontmatter.get("name", skill_name) if frontmatter else skill_name
            description = ""
            if frontmatter:
                desc = frontmatter.get("description", "")
                # Clean up quoted descriptions
                if isinstance(desc, str):
                    description = desc.strip().strip('"').strip("'")

            # Determine category from path (e.g., .curated, .system)
            rel = os.path.relpath(skill_dir, provider_path)
            parts = rel.split(os.sep)
            category = None
            for p in parts:
                if p.startswith("."):
                    category = p.lstrip(".")
                    break

            skills.append({
                "name": name,
                "dir_name": skill_name,
                "description": description,
                "provider": provider,
                "path": skill_dir,
                "category": category,
            })

    return skills


def get_project_skills_dirs(project_path):
    """Return the list of skills directories for a project."""
    return [os.path.join(project_path, d) for d in SKILL_TARGET_DIRS]


def get_installed_skills(project_path):
    """Return dict of installed skill names -> symlink targets (or None if not a symlink).

    Checks all target directories and reports a skill as installed if it exists
    in any of them.
    """
    installed = {}
    for skills_dir in get_project_skills_dirs(project_path):
        if not os.path.isdir(skills_dir):
            continue
        for entry in sorted(os.listdir(skills_dir)):
            entry_path = os.path.join(skills_dir, entry)
            if entry.startswith("."):
                continue
            if os.path.isdir(entry_path) and entry not in installed:
                if os.path.islink(entry_path):
                    installed[entry] = os.readlink(entry_path)
                else:
                    installed[entry] = None
    return installed


def cmd_list(args):
    """List all available skills grouped by provider."""
    skills = discover_skills(args.skills_root)
    if not skills:
        print("No skills found in", args.skills_root)
        return

    # Get installed skills if project is specified
    installed = {}
    if args.project:
        installed = get_installed_skills(args.project)

    # Group by provider
    by_provider = {}
    for s in skills:
        by_provider.setdefault(s["provider"], []).append(s)

    for provider in sorted(by_provider.keys()):
        provider_skills = by_provider[provider]
        print(f"\n## {provider}")
        for i, s in enumerate(sorted(provider_skills, key=lambda x: x["name"]), 1):
            status = ""
            if s["dir_name"] in installed or s["name"] in installed:
                status = " (installed)"
            cat = f" [{s['category']}]" if s.get("category") else ""
            # Truncate description for display
            desc = s["description"]
            if len(desc) > 120:
                desc = desc[:117] + "..."
            print(f"  {i}. {s['name']}{cat}{status}")
            if desc:
                print(f"     {desc}")

    print(f"\nTotal: {len(skills)} skills from {len(by_provider)} providers")


def cmd_installed(args):
    """List skills installed for the current project."""
    installed = get_installed_skills(args.project)
    if not installed:
        print(f"No skills installed for project at {args.project}")
        return

    print(f"Installed skills for {args.project}:\n")
    for name, target in sorted(installed.items()):
        if target:
            print(f"  - {name} -> {target}")
        else:
            print(f"  - {name} (local copy, not symlinked)")


def cmd_install(args):
    """Install a skill by creating a symlink."""
    skills = discover_skills(args.skills_root)

    # Find matching skill(s)
    matches = [s for s in skills if s["name"] == args.skill_name or s["dir_name"] == args.skill_name]

    if not matches:
        print(f"Error: Skill '{args.skill_name}' not found.")
        print("Run with 'list' to see available skills.")
        sys.exit(1)

    if len(matches) > 1 and not args.provider:
        print(f"Multiple skills named '{args.skill_name}' found:")
        for s in matches:
            cat = f" [{s['category']}]" if s.get("category") else ""
            print(f"  - {s['provider']}{cat}: {s['path']}")
        print("\nUse --provider to specify which one.")
        sys.exit(1)

    if args.provider:
        matches = [s for s in matches if s["provider"] == args.provider]
        if not matches:
            print(f"Error: Skill '{args.skill_name}' not found from provider '{args.provider}'.")
            sys.exit(1)

    skill = matches[0]
    skills_dirs = get_project_skills_dirs(args.project)

    # Check if already installed in any target directory
    for skills_dir in skills_dirs:
        link_path = os.path.join(skills_dir, skill["dir_name"])
        if os.path.exists(link_path):
            if os.path.islink(link_path):
                current_target = os.readlink(link_path)
                if current_target == skill["path"]:
                    continue  # Already correct in this dir
                else:
                    print(f"Skill '{skill['name']}' is already installed in {skills_dir} but points to a different location:")
                    print(f"  Current: {current_target}")
                    print(f"  New:     {skill['path']}")
                    print("Remove the existing link first with 'uninstall'.")
                    sys.exit(1)
            else:
                print(f"Error: '{link_path}' exists and is not a symlink. Remove it manually if you want to replace it.")
                sys.exit(1)

    # Create symlinks in all target directories
    created = []
    for skills_dir in skills_dirs:
        link_path = os.path.join(skills_dir, skill["dir_name"])
        if os.path.islink(link_path) and os.readlink(link_path) == skill["path"]:
            continue  # Already correct
        os.makedirs(skills_dir, exist_ok=True)
        os.symlink(skill["path"], link_path)
        created.append(link_path)

    print(f"Installed '{skill['name']}' from {skill['provider']}")
    for link_path in created:
        print(f"  {link_path} -> {skill['path']}")


def cmd_uninstall(args):
    """Uninstall a skill by removing its symlinks from all target directories."""
    skills_dirs = get_project_skills_dirs(args.project)
    removed = []
    errors = []

    for skills_dir in skills_dirs:
        link_path = os.path.join(skills_dir, args.skill_name)
        if not os.path.exists(link_path) and not os.path.islink(link_path):
            continue
        if not os.path.islink(link_path):
            errors.append(f"  '{link_path}' is not a symlink (local copy). Remove manually: rm -rf {link_path}")
            continue
        target = os.readlink(link_path)
        os.unlink(link_path)
        removed.append(f"  {link_path} -> {target}")

    if not removed and not errors:
        print(f"Error: Skill '{args.skill_name}' is not installed for this project.")
        sys.exit(1)

    if removed:
        print(f"Uninstalled '{args.skill_name}'")
        for r in removed:
            print(r)
    if errors:
        print("Warnings:")
        for e in errors:
            print(e)


def main():
    parser = argparse.ArgumentParser(description="Manage Claude Code skill installation via symlinks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common arguments added to each subparser
    def add_common_args(p):
        p.add_argument("--skills-root", default=DEFAULT_SKILLS_ROOT,
                        help="Root directory containing provider skill directories")
        p.add_argument("--project", default=None,
                        help="Project directory (defaults to current working directory)")

    # list
    list_parser = subparsers.add_parser("list", help="List available skills")
    add_common_args(list_parser)
    list_parser.set_defaults(func=cmd_list)

    # installed
    installed_parser = subparsers.add_parser("installed", help="Show installed skills for a project")
    add_common_args(installed_parser)
    installed_parser.set_defaults(func=cmd_installed)

    # install
    install_parser = subparsers.add_parser("install", help="Install a skill via symlink")
    install_parser.add_argument("skill_name", help="Name of the skill to install")
    install_parser.add_argument("--provider", help="Provider name if skill name is ambiguous")
    add_common_args(install_parser)
    install_parser.set_defaults(func=cmd_install)

    # uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a skill (remove symlink)")
    uninstall_parser.add_argument("skill_name", help="Name of the skill to uninstall")
    add_common_args(uninstall_parser)
    uninstall_parser.set_defaults(func=cmd_uninstall)

    args = parser.parse_args()

    # Default project to cwd if not specified
    if args.project is None:
        args.project = os.getcwd()

    args.func(args)


if __name__ == "__main__":
    main()
