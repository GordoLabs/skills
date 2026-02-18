# AGENTS.md

> **Keep in sync:** This file and `CLAUDE.md` must always have identical content (except for the title). When updating one, update the other to match.

This file provides guidance when working with code in this repository.

## What This Is

A skill that manages installation of other skills into projects via symlinks. It is itself a skill (defined by `SKILL.md`) and contains a Python CLI (`scripts/manage_skills.py`) that handles discovery, installation, and removal of skills.

## Architecture

- **`SKILL.md`** — Skill definition with YAML frontmatter (`name`, `description`) and usage instructions that Claude Code reads at runtime.
- **`scripts/manage_skills.py`** — Single-file Python CLI (requires `pyyaml`). All logic lives here: skill discovery, frontmatter parsing, symlink management.

### Key concepts

- **Skills root**: `~/Documents/workspaces/skills/` — contains provider subdirectories (e.g., `gordolabs/`, `anthropics/`). Each provider contains skill directories, each identified by having a `SKILL.md` file.
- **Installation**: Creates symlinks in a project's `.claude/skills/`, `.copilot/skills/`, and `.agents/skills/` directories pointing back to the source skill directory. This means updates to source skills propagate automatically.
- **Discovery**: Walks provider directories recursively, skipping `.git`, `node_modules`, `__pycache__`, `template`, `spec`, `.claude-plugin`. Skills named `template` are also skipped. Categories are inferred from dot-prefixed path segments (e.g., `.curated` → category `curated`).
- **Frontmatter**: YAML between `---` delimiters at the top of `SKILL.md` files. Fields: `name`, `description`.

## Commands

```bash
# List all available skills (with install status if --project given)
python3 scripts/manage_skills.py list --project /path/to/project

# Show installed skills for a project
python3 scripts/manage_skills.py installed --project /path/to/project

# Install a skill (creates symlink)
python3 scripts/manage_skills.py install <skill-name> --project /path/to/project

# Install with explicit provider (when name is ambiguous)
python3 scripts/manage_skills.py install <skill-name> --provider <provider> --project /path/to/project

# Uninstall a skill (removes symlink)
python3 scripts/manage_skills.py uninstall <skill-name> --project /path/to/project
```

`--project` defaults to cwd if omitted. `--skills-root` overrides the default `~/Documents/workspaces/skills/`.
