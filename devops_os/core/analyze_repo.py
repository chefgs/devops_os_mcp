#!/usr/bin/env python3
"""
DevOps-OS repository analyzer.

Detects a project's stack, hosting target and existing CI from a fixed list of
well-known files, and recommends calls to the generator tools. It never walks
the tree: only the files named here are opened, each size-capped and resolved
so a symlink cannot lead outside the repository. Raw file contents are not
returned, only derived facts.
"""

import json
import os
import re

from devops_os.core.audit_gha import EXPECTED, MAX_BYTES, audit_workflow

MAX_FILE_BYTES = 512_000
MAX_WORKFLOWS = 20

LOCKFILES = {
    "pnpm-lock.yaml": "pnpm", "yarn.lock": "yarn", "package-lock.json": "npm",
    "bun.lockb": "bun", "bun.lock": "bun",
}
JS_FRAMEWORKS = ["next", "nuxt", "astro", "vite", "react-scripts", "react", "vue", "svelte", "express", "@nestjs/core"]
PY_FRAMEWORKS = ["fastapi", "django", "flask"]
# Framework -> usual build output directory (only where it is unambiguous).
OUTPUT_DIRS = {"vite": "dist", "astro": "dist", "react-scripts": "build"}
PY_FILES = ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"]
JAVA_FILES = ["pom.xml", "build.gradle", "build.gradle.kts"]
# Ecosystem names for dependabot, by detected language/file.
DEPENDABOT = {"python": "pip", "javascript": "npm", "go": "gomod", "rust": "cargo", "java": "maven"}


class _Repo:
    """Safe, read-only view of a repository root."""

    def __init__(self, path):
        if not isinstance(path, str) or not path.strip() or "\x00" in path:
            raise ValueError("path must be a non-empty string")
        root = os.path.realpath(os.path.expanduser(path))
        if not os.path.isdir(root):
            raise ValueError(f"path is not a directory: {path}")
        self.root = root

    def resolve(self, rel):
        """Real path of ``rel`` if it exists inside the repo, else None."""
        full = os.path.realpath(os.path.join(self.root, rel))
        if full != self.root and not full.startswith(self.root + os.sep):
            return None  # symlink escaping the repository
        return full if os.path.exists(full) else None

    def exists(self, rel):
        return self.resolve(rel) is not None

    def read(self, rel, limit=MAX_FILE_BYTES):
        full = self.resolve(rel)
        if not full or not os.path.isfile(full) or os.path.getsize(full) > limit:
            return None
        with open(full, encoding="utf-8", errors="replace") as f:
            return f.read()


def _word(text, name):
    return re.search(rf"(?im)(^|[\s\"'=<>~!,\[]){re.escape(name)}([\s\"'=<>~!,\]\[;:]|$)", text) is not None


MAX_SUBDIRS = 30
SKIP_DIRS = {"node_modules", "venv", "env", "vendor", "dist", "build", "target", "__pycache__", "site-packages"}


def _scan_dir(repo, rel, notes):
    """Detect languages, frameworks and package manager from the manifests in one directory."""
    def p(name):
        return f"{rel}/{name}" if rel else name

    languages, frameworks = [], []
    pkg_text = repo.read(p("package.json"))
    pkg = {}
    if pkg_text is not None:
        try:
            pkg = json.loads(pkg_text)
        except ValueError:
            notes.append(f"{p('package.json')} is not valid JSON and was ignored.")
        else:
            languages.append("javascript")
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            frameworks += [f for f in JS_FRAMEWORKS if f in deps]

    py_text = "\n".join(t for t in (repo.read(p(f)) for f in PY_FILES) if t)
    if any(repo.exists(p(f)) for f in PY_FILES):
        languages.append("python")
        frameworks += [f for f in PY_FRAMEWORKS if _word(py_text, f)]
    if repo.exists(p("go.mod")):
        languages.append("go")
    if repo.exists(p("Cargo.toml")):
        languages.append("rust")
    if any(repo.exists(p(f)) for f in JAVA_FILES):
        languages.append("java")

    package_manager = next((pm for lock, pm in LOCKFILES.items() if repo.exists(p(lock))), None)
    if package_manager is None and pkg_text is not None:
        field = str(pkg.get("packageManager", "")).split("@")[0]
        package_manager = field if field in ("npm", "pnpm", "yarn", "bun") else None
    return languages, frameworks, package_manager


def analyze(path):
    """Analyze the repository at ``path``; returns a JSON-serialisable dict.

    Manifests are looked up in the root and in each immediate subdirectory (the
    usual ``frontend/`` + ``backend/`` monorepo layout); nothing deeper is read.
    """
    repo = _Repo(path)
    notes = []

    languages, frameworks, package_manager = _scan_dir(repo, "", notes)
    projects = [{"dir": ".", "languages": list(languages), "package_manager": package_manager}] if languages else []
    subdirs = sorted(n for n in os.listdir(repo.root)
                     if not n.startswith(".") and n not in SKIP_DIRS and repo.resolve(n)
                     and os.path.isdir(repo.resolve(n)))
    if len(subdirs) > MAX_SUBDIRS:
        notes.append(f"Only the first {MAX_SUBDIRS} of {len(subdirs)} subdirectories were checked.")
    for sub in subdirs[:MAX_SUBDIRS]:
        s_langs, s_fw, s_pm = _scan_dir(repo, sub, notes)
        if s_langs:
            projects.append({"dir": sub, "languages": s_langs, "package_manager": s_pm})
            languages += s_langs
            frameworks += s_fw
    languages = list(dict.fromkeys(languages))
    package_managers = {pr["package_manager"] for pr in projects if pr["package_manager"]}
    package_manager = package_manager or (sorted(package_managers)[0] if len(package_managers) == 1 else None)
    for pm in sorted(package_managers & {"pnpm", "yarn", "bun"}):
        notes.append(f"{pm} project: generated JavaScript steps use `npm ci`; "
                     "swap in your package manager's install command.")
    if len(projects) > 1 or (projects and projects[0]["dir"] != "."):
        notes.append("Manifests found in subdirectories: generated build/test steps run at the repository "
                     "root, so add `working-directory:` to them, and call generate_dependabot_config "
                     "once per project directory.")

    # Hosting / deployment signals
    signals = []
    if repo.exists("vercel.json") or repo.exists(".vercel"):
        signals.append("vercel")
    wrangler = next((f for f in ("wrangler.jsonc", "wrangler.json", "wrangler.toml") if repo.exists(f)), None)
    if wrangler:
        text = repo.read(wrangler) or ""
        signals.append("cloudflare-pages" if "pages_build_output_dir" in text else "cloudflare-workers")
    if repo.exists("netlify.toml"):
        signals.append("netlify")
    if repo.exists("render.yaml") or repo.exists("render.yml"):
        signals.append("render")
    if repo.exists("Dockerfile") or repo.exists("docker-compose.yml"):
        signals.append("docker")
    if repo.exists("Chart.yaml") or repo.exists("helm") or repo.exists("k8s") or repo.exists("kubernetes"):
        signals.append("kubernetes")
    hosting = next((s for s in signals if s not in ("docker", "kubernetes")), "")
    if len(set(signals) - {"docker", "kubernetes"}) > 1:
        notes.append(f"Several hosting configs found ({', '.join(signals)}); verify which one is live.")

    output_dir = next((OUTPUT_DIRS[f] for f in OUTPUT_DIRS if f in frameworks), None)

    # Existing workflows, audited
    workflows = []
    wf_dir = repo.resolve(".github/workflows")
    if wf_dir and os.path.isdir(wf_dir):
        names = sorted(n for n in os.listdir(wf_dir) if n.endswith((".yml", ".yaml")))
        if len(names) > MAX_WORKFLOWS:
            notes.append(f"Only the first {MAX_WORKFLOWS} of {len(names)} workflow files were audited.")
        for name in names[:MAX_WORKFLOWS]:
            text = repo.read(f".github/workflows/{name}", MAX_BYTES)
            if text is None:
                workflows.append({"file": name, "error": "unreadable or larger than the audit limit"})
                continue
            try:
                r = audit_workflow(text)
            except ValueError as e:
                workflows.append({"file": name, "error": str(e)})
                continue
            workflows.append({"file": name, "covers": sorted(r["covers"]), "missing": r["missing"],
                              "findings": sorted({f["id"] for f in r["findings"]})})
    has_dependabot = repo.exists(".github/dependabot.yml") or repo.exists(".github/dependabot.yaml")

    # Recommendations (calls to the generator tools)
    langs = ",".join(languages)
    app_name = re.sub(r"[^a-z0-9-]+", "-", os.path.basename(repo.root).lower()).strip("-") or "my-app"
    calls = []
    valid = [w for w in workflows if "covers" in w]
    if not workflows and languages:
        args = {"name": app_name,
                "workflow_type": "complete" if hosting or "docker" in signals else "test",
                "languages": langs}
        if hosting:
            args["deploy_target"] = hosting
            if output_dir:
                args["build_output_dir"] = output_dir
        calls.append({"tool": "generate_github_actions_workflow", "arguments": args,
                      "why": "No workflows found: generate a first pipeline."})
    elif valid:
        covered = set().union(*(set(w["covers"]) for w in valid))
        scans = [s for cap, s in (("secrets-scan", "gitleaks"), ("sast", "semgrep"),
                                  ("dependency-scan", "trivy")) if cap not in covered]
        calls.append({"tool": "audit_github_workflow", "arguments": {"workflow_yaml": "<contents of an existing workflow>"},
                      "why": "Existing CI found: review its gaps before generating anything."})
        if scans:
            calls.append({"tool": "generate_github_actions_workflow",
                          "arguments": {"workflow_type": "security", "languages": langs or "python",
                                        "security_scans": ",".join(scans)},
                          "why": "Add missing scans as a separate workflow file; the existing CI is untouched."})
    if not has_dependabot:
        extra = ["docker"] if "docker" in signals else []
        for proj in (projects or [{"dir": ".", "languages": []}]):
            eco = [DEPENDABOT[l] for l in proj["languages"] if l in DEPENDABOT] + (extra if proj["dir"] == "." or not projects else [])
            args = {"ecosystems": ",".join(eco) or "github-actions"}
            if proj["dir"] != ".":
                args["directory"] = "/" + proj["dir"]
            calls.append({"tool": "generate_dependabot_config", "arguments": args,
                          "why": "No dependabot.yml: enable automatic dependency and action updates"
                                 + (f" for {proj['dir']}/." if proj["dir"] != "." else ".")})
    if hosting:
        pre = {"deploy_target": hosting, "name": app_name}
        if output_dir:
            pre["build_output_dir"] = output_dir
        calls.append({"tool": "generate_deploy_preflight", "arguments": pre,
                      "why": f"{hosting} config found: get a local test plan to verify your hosting setup "
                             "(read-only checks first, then a preview deploy) before relying on the workflow."})
    if "kubernetes" in signals:
        calls.append({"tool": "generate_k8s_config", "arguments": {},
                      "why": "Kubernetes files detected; generate_k8s_config can produce or compare manifests."})

    stack = ", ".join(list(dict.fromkeys(languages)) + list(dict.fromkeys(frameworks))) or "no recognised stack"
    if not workflows:
        ci = "no CI workflows"
    else:
        ci = f"{len(workflows)} CI workflow(s)"
        covered_all = set().union(*(set(w["covers"]) for w in workflows if "covers" in w))
        gaps = [c for c in EXPECTED if c not in covered_all] if covered_all or any("covers" in w for w in workflows) else []
        if gaps:
            ci += f" (not detected: {', '.join(gaps)})"
    summary = (f"Detected {stack}; {ci}; "
               f"{'dependabot configured' if has_dependabot else 'no dependabot'}"
               f"{'; hosting: ' + hosting if hosting else ''}. "
               f"{len(calls)} suggested next step(s) in recommended_calls, in priority order: "
               "present them to the user and generate only what they choose.")

    return {
        "summary": summary,
        "path": repo.root,
        "languages": languages,
        "frameworks": list(dict.fromkeys(frameworks)),
        "package_manager": package_manager,
        "projects": projects,
        "deploy_signals": signals,
        "recommended_deploy_target": hosting,
        "build_output_dir": output_dir,
        "existing_workflows": workflows,
        "has_dependabot": has_dependabot,
        "notes": notes,
        "recommended_calls": calls,
    }
