"""Lint generated workflows with actionlint (and shellcheck, when installed).

Skipped when actionlint is not on PATH. CI installs both via
``pip install actionlint-py shellcheck-py``. actionlint only checks the shell
inside ``run:`` steps when shellcheck is available.
"""

import itertools
import shutil
import subprocess

import pytest

from mcp_server.server import generate_github_actions_workflow

pytestmark = pytest.mark.skipif(shutil.which("actionlint") is None, reason="actionlint not installed")

TARGETS = ["", "vercel", "cloudflare-workers", "cloudflare-pages", "netlify", "render", "github-pages"]


def _cases():
    for wf_type, langs, pin in itertools.product(
        ["build", "test", "deploy", "complete", "reusable", "security"],
        ["python", "java,rust,python,javascript,go"],
        [False, True],
    ):
        scans = "" if wf_type in ("deploy", "reusable") else "gitleaks,semgrep,trivy,checkov,codeql"
        targets = TARGETS if wf_type in ("deploy", "complete") else [""]
        for target in targets:
            for k8s in ([False, True] if not target and wf_type in ("deploy", "complete", "reusable") else [False]):
                yield dict(workflow_type=wf_type, languages=langs, pin_actions=pin, security_scans=scans,
                           deploy_target=target, kubernetes=k8s)


def test_generated_workflows_pass_actionlint(tmp_path):
    files = []
    for i, kw in enumerate(_cases()):
        f = tmp_path / f"{i:04d}-{kw['workflow_type']}.yml"
        f.write_text(generate_github_actions_workflow(name="demo", **kw))
        files.append(str(f))
    proc = subprocess.run(["actionlint", *files], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-3000:]
