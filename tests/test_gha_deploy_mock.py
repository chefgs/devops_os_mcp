"""Mock execution of generated deploy scripts.

The ``run:`` scripts from generated workflows are executed in bash with stub
``npx``/``curl``/``docker``/``kubectl`` on PATH that record their arguments. This
checks the shell logic, argument quoting and secret handling without real
accounts. ``${{ }}`` expressions are resolved from a fixed table and the test
fails if any is left unresolved, so a new expression cannot slip through unchecked.
"""

import json
import os
import re
import stat
import subprocess

import pytest
import yaml

from mcp_server.server import generate_github_actions_workflow

EXPRESSIONS = {
    "github.actor": "octo",
    "github.repository_owner": "acme",
    "github.event.repository.name": "shop",
}
STUB = """#!/bin/bash
python3 - "$@" <<'PY'
import json, os, sys
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(json.dumps({"cmd": os.path.basename(os.environ.get("STUB_NAME", "?")), "argv": sys.argv[1:]}) + "\\n")
PY
exit ${STUB_EXIT:-0}
"""
# A token with a space, a quote and shell metacharacters: it must reach the CLI as one argument.
NASTY = 'tok en"$(touch pwned);`x`'


def _resolve(text, secrets):
    def sub(m):
        expr = m.group(1).strip()
        if expr.startswith("secrets."):
            return secrets[expr.split(".", 1)[1]]
        if expr in EXPRESSIONS:
            return EXPRESSIONS[expr]
        raise AssertionError(f"unresolved expression in generated script: {expr}")
    return re.sub(r"\$\{\{(.*?)\}\}", sub, text)


def _step(target_kwargs, name):
    text = generate_github_actions_workflow(name="shop", workflow_type="deploy", languages="javascript", **target_kwargs)
    wf = yaml.safe_load(text)
    return next(s for s in wf["jobs"]["deploy"]["steps"] if s["name"] == name)


def _run(step, tmp_path, secrets, **env):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for cmd in ("npx", "curl", "docker", "kubectl"):
        f = bin_dir / cmd
        f.write_text(STUB.replace("$STUB_NAME", cmd).replace("STUB_NAME", cmd) if False else
                     STUB.replace('os.environ.get("STUB_NAME", "?")', f'"{cmd}"'))
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "log.jsonl"
    step_env = {k: _resolve(v, secrets) for k, v in step.get("env", {}).items()}
    proc = subprocess.run(
        ["bash", "-e", "-c", _resolve(step["run"], secrets)],
        cwd=tmp_path, capture_output=True, text=True,
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path), "STUB_LOG": str(log), **step_env, **env},
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return proc, calls


def test_vercel_runs_pull_build_deploy_in_order_with_token_as_single_argument(tmp_path):
    secrets = {"VERCEL_TOKEN": NASTY, "VERCEL_ORG_ID": "org", "VERCEL_PROJECT_ID": "prj"}
    proc, calls = _run(_step(dict(deploy_target="vercel"), "Deploy to Vercel"), tmp_path, secrets)
    assert proc.returncode == 0, proc.stderr
    assert [c["argv"][2] for c in calls] == ["pull", "build", "deploy"]
    assert all(c["argv"][1].startswith("vercel@") for c in calls)
    for c in calls:
        assert f"--token={NASTY}" in c["argv"]  # the whole token is one intact argument
    assert "--prebuilt" in calls[2]["argv"] and "--prod" in calls[2]["argv"]
    assert not (tmp_path / "pwned").exists()  # nothing in the token was executed


def test_vercel_failure_stops_the_script(tmp_path):
    secrets = {"VERCEL_TOKEN": "t", "VERCEL_ORG_ID": "o", "VERCEL_PROJECT_ID": "p"}
    proc, calls = _run(_step(dict(deploy_target="vercel"), "Deploy to Vercel"), tmp_path, secrets, STUB_EXIT="1")
    assert proc.returncode != 0 and len(calls) == 1  # failed at `pull`; build/deploy never ran


def test_netlify_deploys_the_configured_directory(tmp_path):
    secrets = {"NETLIFY_AUTH_TOKEN": NASTY, "NETLIFY_SITE_ID": "site"}
    step = _step(dict(deploy_target="netlify", build_output_dir="build"), "Deploy to Netlify")
    proc, calls = _run(step, tmp_path, secrets)
    assert proc.returncode == 0, proc.stderr
    assert calls[0]["argv"][1].startswith("netlify-cli@") and "--dir=build" in calls[0]["argv"] and "--prod" in calls[0]["argv"]
    # Credentials travel in the environment, never on the command line.
    assert NASTY not in " ".join(calls[0]["argv"])


def test_render_posts_to_the_hook_without_echoing_it(tmp_path):
    hook = "https://api.render.com/deploy/srv-abc?key=SECRETKEY"
    step = _step(dict(deploy_target="render"), "Trigger Render deploy")
    proc, calls = _run(step, tmp_path, {"RENDER_DEPLOY_HOOK_URL": hook})
    assert proc.returncode == 0, proc.stderr
    assert calls == [{"cmd": "curl", "argv": ["-fsS", "-X", "POST", hook]}]
    assert "SECRETKEY" not in proc.stdout + proc.stderr


def test_render_failed_hook_fails_the_step(tmp_path):
    step = _step(dict(deploy_target="render"), "Trigger Render deploy")
    proc, _ = _run(step, tmp_path, {"RENDER_DEPLOY_HOOK_URL": "https://x"}, STUB_EXIT="22")
    assert proc.returncode != 0


def test_docker_push_survives_hostile_token_and_lowercases_the_tag(tmp_path):
    text = generate_github_actions_workflow(name="shop", workflow_type="deploy", languages="python")
    step = next(s for s in yaml.safe_load(text)["jobs"]["deploy"]["steps"] if s["name"] == "Build and Push Docker Image")
    proc, calls = _run(step, tmp_path, {"REGISTRY_TOKEN": NASTY}, GITHUB_ACTOR="octo", GITHUB_REPOSITORY="Acme/Shop")
    assert proc.returncode == 0, proc.stderr
    login, build, push = calls
    assert login["argv"] == ["login", "ghcr.io", "-u", "octo", "--password-stdin"]
    tag = "ghcr.io/acme/shop:latest"  # owner/repo lower-cased; Docker rejects upper case
    assert build["argv"] == ["build", "-t", tag, "."] and push["argv"] == ["push", tag]
    assert not (tmp_path / "pwned").exists()


def test_docker_push_script_contains_no_secret_expression():
    text = generate_github_actions_workflow(name="shop", workflow_type="deploy", languages="python")
    step = next(s for s in yaml.safe_load(text)["jobs"]["deploy"]["steps"] if s["name"] == "Build and Push Docker Image")
    assert "${{" not in step["run"]  # secrets only via env:


@pytest.mark.parametrize("method, expected", [
    ("kubectl", ["apply", "apply", "rollout"]),
    ("kustomize", ["apply", "rollout"]),
])
def test_kubernetes_methods_write_kubeconfig_privately_and_apply(tmp_path, method, expected):
    from devops_os.core import scaffold_gha
    import argparse
    args = argparse.Namespace(name="shop", type="deploy", languages="python", kubernetes=True, k8s_method=method,
                              branches="main", matrix=False, image="", pin_actions=False, reusable=False,
                              registry="ghcr.io")
    wf = scaffold_gha.generate_workflow(args, {}, {"languages": {"python": True}})
    step = next(s for s in wf["jobs"]["deploy"]["steps"] if s["name"].startswith("Deploy to Kubernetes"))
    step = {**step, "env": {k: ("dev" if "inputs" in v else v) for k, v in step.get("env", {}).items()}}
    # Real kubeconfigs contain quotes, newlines and sometimes `$`; none may break or run.
    kubeconfig = 'apiVersion: v1\nusers:\n- name: "a b"\n  token: \'x$(touch pwned)`y`\\\\z\'\n'
    proc, calls = _run(step, tmp_path, {"KUBECONFIG": kubeconfig})
    assert proc.returncode == 0, proc.stderr
    assert [c["argv"][0] for c in calls] == expected
    cfg = tmp_path / ".kube" / "config"
    assert cfg.read_text().rstrip("\n") == kubeconfig.rstrip("\n") and (cfg.stat().st_mode & 0o777) == 0o600
    assert not (tmp_path / "pwned").exists()
