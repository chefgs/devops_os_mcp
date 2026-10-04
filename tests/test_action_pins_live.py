"""Check pinned actions against GitHub (needs the `gh` CLI, authenticated).

Verifies that (1) every pinned SHA is still the commit its release tag points to,
and (2) every `with:` input the generator emits exists in the pinned action's
action.yml. Skipped when `gh` is unavailable or unauthenticated, so offline runs
are unaffected. Newer major versions are reported as warnings, not failures.
"""

import base64
import itertools
import json
import shutil
import subprocess
import warnings

import pytest
import yaml

from devops_os.core.scaffold_gha import ACTION_REFS
from mcp_server.server import generate_github_actions_workflow


def _gh(path):
    p = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return json.loads(p.stdout)


def _gh_available():
    if shutil.which("gh") is None:
        return False
    return subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not _gh_available(), reason="gh CLI not installed/authenticated")


def _split(action):
    """'github/codeql-action/init' -> ('github/codeql-action', 'init')."""
    owner, repo, *sub = action.split("/")
    return f"{owner}/{repo}", "/".join(sub)


def _commit_for_tag(repo, tag):
    obj = _gh(f"repos/{repo}/git/ref/tags/{tag}")["object"]
    for _ in range(3):  # dereference annotated tags
        if obj["type"] != "tag":
            break
        obj = _gh(f"repos/{repo}/git/tags/{obj['sha']}")["object"]
    return obj["sha"]


@pytest.mark.parametrize("action", sorted(ACTION_REFS))
def test_pinned_sha_matches_its_release_tag(action):
    repo, _ = _split(action)
    _major, tag, sha = ACTION_REFS[action]
    assert _commit_for_tag(repo, tag) == sha, f"{action}: {tag} no longer points at the pinned SHA"


@pytest.mark.parametrize("action", sorted(ACTION_REFS))
def test_floating_major_tag_resolves_to_the_pinned_commit(action):
    repo, _ = _split(action)
    major, tag, sha = ACTION_REFS[action]
    if major != tag:  # actions without a floating major use the exact tag
        assert _commit_for_tag(repo, major) == sha, f"{action}: {major} has moved past {tag}; refresh the pin"


def _emitted_inputs():
    """Map action -> set of `with:` keys the generator can emit."""
    seen = {}
    for target, scans, langs in itertools.product(
        ["", "vercel", "cloudflare-workers", "cloudflare-pages", "netlify", "render", "github-pages"],
        ["", "gitleaks,semgrep,trivy,checkov,codeql"], ["python", "javascript,go,java,rust"],
    ):
        for k8s_method_args in ({"kubernetes": False}, {"kubernetes": True}):
            if target and k8s_method_args["kubernetes"]:
                continue
            text = generate_github_actions_workflow(
                name="demo", workflow_type="complete", languages=langs, security_scans=scans,
                deploy_target=target, **k8s_method_args)
            for job in yaml.safe_load(text)["jobs"].values():
                for step in job["steps"]:
                    if "uses" in step:
                        seen.setdefault(step["uses"].rsplit("@", 1)[0], set()).update(step.get("with", {}))
    return seen


@pytest.mark.parametrize("action,keys", sorted(_emitted_inputs().items()) if _gh_available() else [])
def test_emitted_with_inputs_exist_in_the_pinned_action(action, keys):
    repo, sub = _split(action)
    _major, _tag, sha = ACTION_REFS[action]
    for name in ("action.yml", "action.yaml"):
        try:
            meta = _gh(f"repos/{repo}/contents/{sub + '/' if sub else ''}{name}?ref={sha}")
            break
        except RuntimeError:
            continue
    else:
        pytest.fail(f"no action.yml found for {action}")
    declared = set(yaml.safe_load(base64.b64decode(meta["content"]))["inputs"] or {})
    assert keys <= declared, f"{action}: emits unknown inputs {sorted(keys - declared)}"


def test_report_newer_major_versions():
    for action, (major, _tag, _sha) in ACTION_REFS.items():
        repo, _ = _split(action)
        try:
            latest = _gh(f"repos/{repo}/releases/latest")["tag_name"]
        except RuntimeError:
            continue
        if latest.startswith("v") and latest.lstrip("v").split(".")[0].isdigit() and major.startswith("v") \
                and "." not in major and int(latest.lstrip("v").split(".")[0]) > int(major.lstrip("v")):
            warnings.warn(f"{action}: pinned {major}, latest release is {latest}")
