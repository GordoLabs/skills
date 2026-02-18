---
name: skill-installer
description: Install and manage Claude Code skills for the current project from a local skills directory. Use when a user asks to list available skills, install skills, uninstall skills, or check which skills are installed for their project. Skills are installed as symlinks so updates to source skills propagate automatically.
---

# Skill Installer

Manage project-level skill installation from a local skills directory at `~/Documents/workspaces/skills/`. Each subdirectory is a provider (e.g., `anthropics`, `openai`, `gordolabs`). Installation creates symlinks in the project's `.claude/skills/` directory.

## Script

Use `scripts/manage_skills.py` for all operations. Always pass `--project` with the current project root directory.

### List available skills

```bash
scripts/manage_skills.py list --project <PROJECT_PATH>
```

Shows all available skills grouped by provider, with `(installed)` markers for skills already installed in the project.

### Show installed skills

```bash
scripts/manage_skills.py installed --project <PROJECT_PATH>
```

### Install a skill

```bash
scripts/manage_skills.py install <SKILL_NAME> --project <PROJECT_PATH>
```

If the skill name exists in multiple providers, the script will list them and ask for `--provider`:

```bash
scripts/manage_skills.py install <SKILL_NAME> --provider <PROVIDER> --project <PROJECT_PATH>
```

### Uninstall a skill

```bash
scripts/manage_skills.py uninstall <SKILL_NAME> --project <PROJECT_PATH>
```

## Workflow

When the user asks to install skills:

1. Run `list --project <path>` to show available skills with install status
2. Present the list to the user and ask which skills they want
3. Run `install` for each selected skill
4. If a skill name is ambiguous (exists in multiple providers), ask the user which provider they want
5. After installation, tell the user to restart Claude Code to pick up new skills

When the user asks to uninstall:

1. Run `installed --project <path>` to show current installations
2. Confirm which skill(s) to remove
3. Run `uninstall` for each selected skill

## Notes

- Skills are symlinked, so updates to the source skill directory are immediately available
- The `--project` flag should point to the project root (where `.claude/` lives or will be created)
- The `--skills-root` flag can override the default skills directory if needed
