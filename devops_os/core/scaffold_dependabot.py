#!/usr/bin/env python3
"""
DevOps-OS Dependabot Config Generator

Generates ``.github/dependabot.yml``. Dependency updates are the cheapest
security control to adopt: once the file exists, update PRs arrive on their own.
``github-actions`` is always included so pinned actions do not go stale.
"""

import re

import yaml

# Friendly names -> Dependabot ``package-ecosystem`` values.
ECOSYSTEM_ALIASES = {
    "python": "pip",
    "javascript": "npm",
    "typescript": "npm",
    "go": "gomod",
    "java": "maven",
    "rust": "cargo",
}
ECOSYSTEMS = [
    "pip", "npm", "gomod", "maven", "gradle", "cargo", "docker",
    "github-actions", "terraform", "composer", "bundler", "nuget",
]
SCHEDULES = ["daily", "weekly", "monthly"]


class _NoAliasDumper(yaml.Dumper):
    def ignore_aliases(self, data):  # noqa: ARG002
        return True


def parse_ecosystems(value):
    """Return validated, de-duplicated ecosystems (aliases resolved); github-actions is always last."""
    result = []
    for item in (value or "").split(","):
        item = item.strip().lower()
        if not item:
            continue
        item = ECOSYSTEM_ALIASES.get(item, item)
        if item not in ECOSYSTEMS:
            raise ValueError(
                f"Unknown ecosystem '{item}'. Valid: {sorted(ECOSYSTEMS)} "
                f"or language aliases {sorted(ECOSYSTEM_ALIASES)}"
            )
        if item != "github-actions" and item not in result:
            result.append(item)
    return result + ["github-actions"]


def validate_directory(value):
    """Directory Dependabot should scan: an absolute-looking repo path such as ``/`` or ``/app``."""
    if not re.fullmatch(r"/[A-Za-z0-9._/-]*", value or "") or ".." in value.split("/"):
        raise ValueError("directory must be a repository path starting with '/', e.g. '/' or '/app'")
    return value


def generate_dependabot_config(ecosystems="github-actions", schedule="weekly", directory="/"):
    """Return the dependabot.yml text."""
    if schedule not in SCHEDULES:
        raise ValueError(f"schedule must be one of {SCHEDULES}")
    directory = validate_directory(directory)
    updates = []
    for eco in parse_ecosystems(ecosystems):
        updates.append({
            "package-ecosystem": eco,
            # Workflows always live at the repository root regardless of the app directory.
            "directory": "/" if eco == "github-actions" else directory,
            "schedule": {"interval": schedule},
            "open-pull-requests-limit": 5,
            # One PR for all minor/patch bumps keeps the noise down; majors stay separate.
            "groups": {"minor-and-patch": {"update-types": ["minor", "patch"]}},
        })
    text = yaml.dump({"version": 2, "updates": updates}, sort_keys=False, Dumper=_NoAliasDumper)
    return "# Save as .github/dependabot.yml\n" + text
