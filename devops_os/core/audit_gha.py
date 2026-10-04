#!/usr/bin/env python3
"""
DevOps-OS GitHub Actions workflow auditor.

Reads an existing workflow (as text), reports which pipeline capabilities it
already covers, which are missing, and hardening problems. It never rewrites
the workflow: missing capabilities are best added as a separate workflow file
next to it, so a working CI is never replaced.
"""

import re

import yaml

from devops_os.core.scaffold_gha import ACTION_REFS

MAX_BYTES = 100_000
MAX_ALIASES = 100

# capability -> regexes matched (case-insensitive) against each step's run/uses text.
CAPABILITIES = {
    "lint": r"eslint|ruff\b|flake8|pylint|golangci|clippy|npm run lint|prettier|checkstyle|black --check|mypy|tsc\b",
    "test": r"pytest|npm (run )?test|go test|cargo test|mvn\b.*\btest|gradle.*\btest|jest|vitest|unittest",
    "build": r"npm run build|go build|cargo build|mvn\b.*\bpackage|gradle.*\bbuild|docker build|docker/build-push-action|python -m build|vite build|next build",
    "secrets-scan": r"gitleaks|trufflehog|detect-secrets",
    "sast": r"semgrep|codeql-action|bandit\b|sonarqube|sonarcloud",
    "dependency-scan": r"trivy|dependency-review-action|snyk|npm audit|pip-audit|osv-scanner|grype|safety check",
    "iac-scan": r"checkov|tfsec|kics|trivy.*config",
    "deploy": r"vercel (deploy|--prod|pull)|vercel/|wrangler|netlify.*deploy|deploy-pages|kubectl (apply|rollout|set image)|helm (upgrade|install)|docker push|argocd app|flux reconcile|aws-actions/|azure/(webapps|k8s|login)|google-github-actions/(deploy|auth)",
}
# Capabilities a typical pipeline is expected to have (deploy is intentionally optional).
EXPECTED = ["lint", "test", "build", "secrets-scan", "sast", "dependency-scan"]
# Missing capability -> how to add it with this server.
SCAN_FOR = {"secrets-scan": "gitleaks", "sast": "semgrep", "dependency-scan": "trivy"}

_INJECTION = re.compile(
    r"\$\{\{\s*(github\.head_ref|github\.event\.(pull_request\.(title|body|head\.ref)|"
    r"issue\.(title|body)|comment\.body|review\.body|head_commit\.message|commits\[[^\]]*\]\.message)"
    r"|github\.event\.pages[^}]*)\s*\}\}"
)
_FLOATING = re.compile(r"@(main|master|latest)$")
_SHA = re.compile(r"@[0-9a-f]{40}$")


def _load(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("workflow_yaml must be a non-empty string")
    if len(text.encode()) > MAX_BYTES:
        raise ValueError(f"workflow_yaml is larger than {MAX_BYTES} bytes")
    if len(re.findall(r"(?m)[\s:\-\[,]\*[A-Za-z_]", text)) > MAX_ALIASES:
        raise ValueError("workflow_yaml uses too many YAML aliases")
    try:
        wf = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"workflow_yaml is not valid YAML: {e}") from e
    if not isinstance(wf, dict) or not isinstance(wf.get("jobs"), dict) or not wf["jobs"]:
        raise ValueError("workflow_yaml does not look like a GitHub Actions workflow (no 'jobs')")
    return wf


def _finding(fid, severity, message, fix):
    return {"id": fid, "severity": severity, "message": message, "fix": fix}


def _major(ref):
    m = re.match(r"v?(\d+)", ref)
    return int(m.group(1)) if m else None


def audit_workflow(text):
    """Audit workflow YAML text; returns a JSON-serialisable dict."""
    wf = _load(text)
    jobs = {n: j for n, j in wf["jobs"].items() if isinstance(j, dict)}

    covers = {c: [] for c in CAPABILITIES}
    uses_refs = []
    for name, job in jobs.items():
        steps = [s for s in job.get("steps", []) if isinstance(s, dict)]
        # Match commands and action references only; step names and test identifiers
        # (e.g. "Test: ArgoCD tool") must not count as evidence.
        blob = " \n".join(f"{s.get('run', '')} {s.get('uses', '')}" for s in steps)
        if isinstance(job.get("uses"), str):  # reusable workflow call
            blob += " " + job["uses"]
            uses_refs.append(job["uses"])
        uses_refs += [s["uses"] for s in steps if isinstance(s.get("uses"), str)]
        for cap, pattern in CAPABILITIES.items():
            if re.search(pattern, blob, re.IGNORECASE):
                covers[cap].append(name)
    covers = {k: v for k, v in covers.items() if v}
    missing = [c for c in EXPECTED if c not in covers]

    findings = []
    outdated = []
    if "permissions" not in wf and not all("permissions" in j for j in jobs.values()):
        findings.append(_finding(
            "no-permissions", "medium",
            "No `permissions:` block: the GITHUB_TOKEN gets the repository default, which may be read-write.",
            "Add top-level `permissions: contents: read` and grant more per job only where needed."))
    if "concurrency" not in wf:
        findings.append(_finding(
            "no-concurrency", "low", "No `concurrency:` group: superseded runs keep running.",
            "Add `concurrency: {group: ${{ github.workflow }}-${{ github.ref }}, "
            "cancel-in-progress: ${{ github.event_name == 'pull_request' }}}`."))

    for ref in dict.fromkeys(uses_refs):
        if ref.startswith("./") or ref.startswith("docker://") or "@" not in ref:
            continue
        action, version = ref.rsplit("@", 1)
        base = action if action in ACTION_REFS else None
        if base is None:  # sub-path of a known action, e.g. github/codeql-action/init
            base = next((a for a in ACTION_REFS if action == a), None)
        if _FLOATING.search(ref):
            findings.append(_finding(
                "floating-action-ref", "medium", f"`{ref}` tracks a moving branch.",
                "Pin to a release tag or full commit SHA."))
        if action in ("actions/upload-artifact", "actions/download-artifact") and (_major(version) or 99) <= 3:
            findings.append(_finding(
                "deprecated-artifact-action", "high",
                f"`{ref}`: v3 and older of the artifact actions are deprecated and fail on GitHub.",
                f"Use {action}@{ACTION_REFS[action][0]}."))
        elif base and _major(version) is not None and _major(ACTION_REFS[base][0]) is not None \
                and _major(version) < _major(ACTION_REFS[base][0]) - 1:
            outdated.append(f"{ref} -> {action}@{ACTION_REFS[base][0]}")
    if outdated:
        findings.append(_finding(
            "outdated-action", "low", "Actions more than one major version behind: " + ", ".join(
                o.split(" -> ")[0] for o in outdated) + ".",
            "Update: " + "; ".join(outdated) + "."))
    unpinned = sorted({r for r in uses_refs if "@" in r and not r.startswith(("./", "docker://"))
                       and not _SHA.search(r)})
    if unpinned:
        findings.append(_finding(
            "actions-not-sha-pinned", "info",
            f"{len(unpinned)} action reference(s) are not pinned to a commit SHA.",
            "Optional hardening: pin to full SHAs (generate_github_actions_workflow supports pin_actions=true) "
            "and let Dependabot's github-actions ecosystem keep them current."))

    for name, job in jobs.items():
        for step in job.get("steps", []):
            if isinstance(step, dict) and _INJECTION.search(str(step.get("run", ""))):
                findings.append(_finding(
                    "script-injection", "high",
                    f"Job `{name}`: untrusted event data is interpolated directly into a `run:` script.",
                    "Pass it through an `env:` variable and reference `$VAR` in the script."))
        image = (job.get("container") or {}).get("image") if isinstance(job.get("container"), dict) else job.get("container")
        if isinstance(image, str) and "yourorg" in image:
            findings.append(_finding(
                "placeholder-container", "high",
                f"Job `{name}` runs in `{image}`, a placeholder image that does not exist.",
                "Remove the `container:` block and use ubuntu-latest with the setup-* actions."))

    suggestions = []
    scans = [SCAN_FOR[c] for c in missing if c in SCAN_FOR]
    if scans:
        suggestions.append({
            "tool": "generate_github_actions_workflow",
            "arguments": {"workflow_type": "security", "security_scans": ",".join(scans)},
            "why": "Adds the missing scans as a separate security workflow file beside the existing one.",
        })
    suggestions.append({
        "tool": "generate_dependabot_config", "arguments": {},
        "why": "Automatic update PRs for dependencies and actions (no existing workflow change needed).",
    })
    for cap in ("lint", "test", "build"):
        if cap in missing:
            suggestions.append({
                "tool": None, "arguments": {},
                "why": f"No `{cap}` step detected; add it to the existing workflow "
                       f"(generate_github_actions_workflow(workflow_type='{'build' if cap == 'build' else 'test'}') "
                       "shows a reference implementation to copy from).",
            })

    return {
        "workflow_name": wf.get("name"),
        "jobs": list(jobs),
        "covers": covers,
        "missing": missing,
        "findings": findings,
        "suggestions": suggestions,
    }
