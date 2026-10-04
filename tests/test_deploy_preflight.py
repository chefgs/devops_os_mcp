"""generate_deploy_preflight: the local test plan must match the workflow it accompanies."""

import json
import re
import stat
import subprocess

import pytest
import yaml

from devops_os.core import deploy_preflight, scaffold_gha
from mcp_server.server import generate_deploy_preflight, generate_github_actions_workflow

TARGETS = sorted(scaffold_gha.DEPLOY_TARGETS)
EFFECTS = {"read-only", "local-build", "publishes"}


def _plan(target, **kw):
    return json.loads(generate_deploy_preflight(deploy_target=target, **kw))


def _workflow(target, **kw):
    return generate_github_actions_workflow(
        name="shop", workflow_type="deploy", languages="javascript", deploy_target=target, **kw)


@pytest.mark.parametrize("target", TARGETS)
class TestPlanMatchesWorkflow:
    def test_secret_names_match_the_workflow(self, target):
        used = set(re.findall(r"secrets\.([A-Z_]+)", _workflow(target)))
        assert set(_plan(target)["required_secrets"]) == used

    def test_every_check_is_classified(self, target):
        checks = _plan(target)["checks"]
        assert checks and all(c["effect"] in EFFECTS for c in checks)
        assert len({c["id"] for c in checks}) == len(checks)

    def test_commands_only_use_declared_secrets(self, target):
        plan = _plan(target)
        allowed = set(plan["required_secrets"])
        for c in plan["checks"]:
            assert set(re.findall(r"\$\{?([A-Z][A-Z_]+)\}?", c["command"])) <= allowed, c["id"]

    def test_never_targets_production(self, target):
        for c in _plan(target)["checks"]:
            assert "--prod" not in c["command"], c["id"]

    def test_every_check_that_changes_the_platform_is_flagged(self, target):
        for c in _plan(target)["checks"]:
            publishing = re.search(r"@[\d.]+ (pages )?deploy( |$)|-X POST", c["command"])
            if publishing and "--dry-run" not in c["command"]:
                assert c["effect"] == "publishes", c["id"]

    def test_env_template_has_placeholders_only(self, target):
        env = _plan(target)["env_file"]
        if not env:
            assert not scaffold_gha.DEPLOY_TARGETS[target]
            return
        lines = [ln for ln in env["content"].splitlines() if ln]
        assert [ln.split("=")[0] for ln in lines] == _plan(target)["required_secrets"]
        assert all('"<' in ln and ln.endswith('>"') for ln in lines)

    def test_safety_guidance_present(self, target):
        text = " ".join(_plan(target)["safety"])
        assert "Do not paste tokens" in text and ".gitignore" in text


def test_workflow_output_points_to_the_preflight_tool():
    assert "generate_deploy_preflight" in _workflow("vercel")
    assert "generate_deploy_preflight" not in generate_github_actions_workflow(name="shop", workflow_type="deploy")


def test_cli_versions_match_the_workflow():
    vercel = json.dumps(_plan("vercel"))
    netlify = json.dumps(_plan("netlify"))
    assert f"vercel@{scaffold_gha.VERCEL_CLI_VERSION}" in vercel and f"vercel@{scaffold_gha.VERCEL_CLI_VERSION}" in _workflow("vercel")
    assert f"netlify-cli@{scaffold_gha.NETLIFY_CLI_VERSION}" in netlify and f"netlify-cli@{scaffold_gha.NETLIFY_CLI_VERSION}" in _workflow("netlify")


def test_project_name_and_output_dir_flow_into_commands():
    plan = json.dumps(_plan("cloudflare-pages", name="my-shop", build_output_dir="build"))
    assert "--project-name=my-shop" in plan and 'test -d \\"build\\"' in plan and 'pages deploy \\"build\\"' in plan


def test_github_pages_states_what_cannot_run_locally():
    assert "OIDC" in " ".join(_plan("github-pages")["not_testable_locally"])
    assert _plan("render")["not_testable_locally"] == []


def test_full_local_run_warns_that_it_really_deploys():
    assert "publishes" in _plan("vercel")["run_whole_workflow_locally"]["warning"]
    assert _plan("vercel")["run_whole_workflow_locally"]["validate_only"].startswith("act -n")


@pytest.mark.parametrize("kwargs", [
    dict(deploy_target="heroku"), dict(deploy_target=""), dict(deploy_target="vercel", name="a b; rm -rf /"),
    dict(deploy_target="netlify", build_output_dir="../etc"), dict(deploy_target="netlify", build_output_dir="/abs"),
    dict(deploy_target="netlify", build_output_dir="d;x"),
])
def test_invalid_input_rejected(kwargs):
    with pytest.raises(ValueError):
        generate_deploy_preflight(**kwargs)


def test_unknown_target_rejected_in_core():
    with pytest.raises(ValueError):
        deploy_preflight.build_plan("heroku")


# --- executing the pure-shell checks -----------------------------------------------------

def _sh(command, cwd, **env):
    return subprocess.run(["bash", "-c", command], cwd=cwd, capture_output=True, text=True,
                          env={"PATH": f"{cwd}/bin:/usr/bin:/bin", **env})


def _check(target, cid, **kw):
    return next(c["command"] for c in _plan(target, **kw)["checks"] if c["id"] == cid)


@pytest.mark.parametrize("url, ok", [
    ("https://api.render.com/deploy/srv-abc123?key=k", True),
    ("http://api.render.com/deploy/srv-abc123?key=k", False),
    ("https://evil.example/deploy/srv-abc", False),
    ("https://api.render.com/deploy/abc", False),
])
def test_render_hook_format_check(tmp_path, url, ok):
    r = _sh(_check("render", "hook-format"), tmp_path, RENDER_DEPLOY_HOOK_URL=url)
    assert (r.returncode == 0 and r.stdout.strip() == "ok") == ok


def test_render_hook_set_check(tmp_path):
    cmd = _check("render", "hook-set")
    assert _sh(cmd, tmp_path, RENDER_DEPLOY_HOOK_URL="x").stdout.strip() == "set"
    assert _sh(cmd, tmp_path).returncode != 0


@pytest.mark.parametrize("make_dir, ok", [(True, True), (False, False)])
def test_local_build_check_detects_a_wrong_output_directory(tmp_path, make_dir, ok):
    (tmp_path / "bin").mkdir()
    npm = tmp_path / "bin" / "npm"
    npm.write_text("#!/bin/bash\nexit 0\n")  # stub: install/build succeed
    npm.chmod(npm.stat().st_mode | stat.S_IEXEC)
    if make_dir:
        (tmp_path / "build").mkdir()
    r = _sh(_check("netlify", "local-build", build_output_dir="build"), tmp_path)
    assert (r.returncode == 0 and "build output found" in r.stdout) == ok
