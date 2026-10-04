"""Tests for the modernised GitHub Actions generator (runner defaults, hardening, pinning)."""

import argparse
import re

import pytest
import yaml

from devops_os.core import scaffold_gha
from mcp_server.server import generate_github_actions_workflow

TYPES = ["build", "test", "deploy", "complete", "reusable"]


def _render(workflow_type="complete", languages="python,javascript", **kw):
    return generate_github_actions_workflow(
        name="demo", workflow_type=workflow_type, languages=languages, **kw
    )


def _all_steps(wf):
    return [s for job in wf["jobs"].values() for s in job["steps"]]


def _uses(wf):
    return [s["uses"] for s in _all_steps(wf) if "uses" in s]


@pytest.mark.parametrize("wf_type", TYPES)
class TestRunnerDefaults:
    def test_no_container_and_no_placeholder_image(self, wf_type):
        text = _render(wf_type)
        assert "yourorg" not in text
        assert all("container" not in j for j in yaml.safe_load(text)["jobs"].values())

    def test_optional_container_is_applied_to_every_job(self, wf_type):
        wf = yaml.safe_load(_render(wf_type, container_image="ubuntu:24.04"))
        assert all(j["container"]["image"] == "ubuntu:24.04" for j in wf["jobs"].values())

    def test_no_deprecated_v3_actions(self, wf_type):
        assert not [u for u in _uses(yaml.safe_load(_render(wf_type))) if u.endswith("@v3")]

    def test_least_privilege_permissions(self, wf_type):
        assert yaml.safe_load(_render(wf_type))["permissions"] == {"contents": "read"}


def test_setup_actions_follow_languages():
    uses = " ".join(_uses(yaml.safe_load(_render("test", "python,go,java,javascript"))))
    for action in ("setup-python", "setup-go", "setup-java", "setup-node"):
        assert action in uses
    assert "setup-go" not in " ".join(_uses(yaml.safe_load(_render("test", "python"))))


def test_concurrency_cancels_only_pull_requests():
    for wf_type in ("build", "test", "complete"):
        c = yaml.safe_load(_render(wf_type))["concurrency"]
        assert c["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"
    assert yaml.safe_load(_render("deploy"))["concurrency"]["cancel-in-progress"] is False


def test_reusable_has_no_concurrency_and_no_input_interpolation_in_scripts():
    wf = yaml.safe_load(_render("reusable", kubernetes=True))
    assert "concurrency" not in wf
    for step in _all_steps(wf):
        assert "${{ inputs." not in step.get("run", ""), step["name"]


def test_matrix_applies_to_all_jobs():
    wf = yaml.safe_load(_render("complete", matrix=True))
    assert all("strategy" in j for j in wf["jobs"].values())


class TestPinning:
    def test_unpinned_uses_major_tags(self):
        for u in _uses(yaml.safe_load(_render())):
            assert re.fullmatch(r"[\w./-]+@v\d+(\.\d+\.\d+)?", u), u

    @pytest.mark.parametrize("wf_type", TYPES)
    def test_pinned_uses_full_sha_with_version_comment(self, wf_type):
        text = _render(wf_type, pin_actions=True)
        refs = re.findall(r"uses: (\S+)(.*)", text)
        assert refs
        for ref, rest in refs:
            assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", ref), ref
            assert re.fullmatch(r" # v\d+(\.\d+\.\d+)?", rest), (ref, rest)

    def test_every_emitted_action_has_a_pin_entry(self):
        """A new action added to the generator must also get a verified SHA."""
        for flux in (False, True):
            args = argparse.Namespace(
                name="demo", type="complete", languages="python,javascript,go,java",
                kubernetes=True, k8s_method="flux" if flux else "kubectl", branches="main",
                matrix=False, image="", pin_actions=False, reusable=False, registry="ghcr.io",
            )
            configs = {
                "languages": scaffold_gha.generate_language_config(args.languages, {}),
                "code_analysis": scaffold_gha.generate_code_analysis_config({}),
            }
            for wf_type in TYPES:
                args.type, args.reusable = wf_type, wf_type == "reusable"
                wf = scaffold_gha.generate_workflow(args, {}, configs)
                for u in _uses(wf):
                    assert u.rsplit("@", 1)[0] in scaffold_gha.ACTION_REFS, u

    def test_pin_table_shape(self):
        for action, (major, tag, sha) in scaffold_gha.ACTION_REFS.items():
            assert re.fullmatch(r"[0-9a-f]{40}", sha), action
            assert tag.startswith(major), action


class TestKubernetesToolInstall:
    def _wf(self, method, image=""):
        args = argparse.Namespace(
            name="demo", type="deploy", languages="python", kubernetes=True, k8s_method=method,
            branches="main", matrix=False, image=image, pin_actions=False, reusable=False,
            registry="ghcr.io",
        )
        return scaffold_gha.generate_workflow(args, {}, {"languages": {"python": True}})

    def test_argocd_cli_installed_with_checksum_verification(self):
        run = next(s["run"] for s in self._wf("argocd")["jobs"]["deploy"]["steps"]
                   if s["name"] == "Install ArgoCD CLI")
        assert "sha256sum -c" in run and scaffold_gha.ARGOCD_VERSION in run

    def test_flux_cli_installed(self):
        assert any(s["name"] == "Install Flux CLI" for s in self._wf("flux")["jobs"]["deploy"]["steps"])

    def test_no_install_when_container_supplies_tools(self):
        names = [s["name"] for s in self._wf("argocd", "my/img:1")["jobs"]["deploy"]["steps"]]
        assert "Install ArgoCD CLI" not in names


@pytest.mark.parametrize("bad", ["img; rm -rf /", "a b", "$(whoami)"])
def test_container_image_is_validated(bad):
    with pytest.raises(ValueError):
        _render("build", container_image=bad)


def test_output_is_deterministic():
    assert _render(pin_actions=True) == _render(pin_actions=True)


# ---------------------------------------------------------------------------
# Phase 2: hosting deploy targets
# ---------------------------------------------------------------------------

TARGETS = ["vercel", "cloudflare-workers", "cloudflare-pages", "netlify", "render", "github-pages"]


def _target(target, workflow_type="deploy", **kw):
    return _render(workflow_type, "javascript", deploy_target=target, **kw)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("wf_type", ["deploy", "complete"])
class TestDeployTargets:
    def test_replaces_docker_push(self, target, wf_type):
        wf = yaml.safe_load(_target(target, wf_type))
        names = [s["name"] for s in wf["jobs"]["deploy"]["steps"]]
        assert "Build and Push Docker Image" not in names
        assert "docker login" not in _target(target, wf_type)

    def test_secrets_only_referenced_not_embedded(self, target, wf_type):
        text = _target(target, wf_type)
        for name in scaffold_gha.DEPLOY_TARGETS[target]:
            assert f"secrets.{name}" in text
            assert f"#   {name}\n" in text  # listed in the header comment

    def test_deploys_only_from_main(self, target, wf_type):
        assert "refs/heads/main" in yaml.safe_load(_target(target, wf_type))["jobs"]["deploy"]["if"]

    def test_pinned_variant_uses_shas(self, target, wf_type):
        for ref in re.findall(r"uses: (\S+)", _target(target, wf_type, pin_actions=True)):
            assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", ref), ref


def test_github_pages_job_has_scoped_permissions_and_environment():
    job = yaml.safe_load(_target("github-pages"))["jobs"]["deploy"]
    assert job["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert job["environment"]["name"] == "github-pages"
    # Elevated permissions must not leak to the workflow level.
    assert yaml.safe_load(_target("github-pages"))["permissions"] == {"contents": "read"}


def test_only_the_deploy_job_gets_secrets():
    wf = yaml.safe_load(_target("vercel", "complete"))
    for name in ("build", "test"):
        assert "secrets." not in yaml.dump(wf["jobs"][name])


def test_build_output_dir_reaches_static_targets():
    assert "--dir=build" in _target("netlify", build_output_dir="build")
    assert "pages deploy build --project-name=demo" in _target("cloudflare-pages", build_output_dir="build")
    assert "path: build" in _target("github-pages", build_output_dir="build")


def test_default_deploy_unchanged_without_target():
    wf = yaml.safe_load(_render("complete"))
    assert any(s["name"] == "Build and Push Docker Image" for s in wf["jobs"]["deploy"]["steps"])


@pytest.mark.parametrize("kwargs", [
    dict(deploy_target="heroku", workflow_type="deploy"),
    dict(deploy_target="vercel", workflow_type="build"),
    dict(deploy_target="vercel", workflow_type="test"),
    dict(deploy_target="vercel", workflow_type="reusable"),
    dict(deploy_target="vercel", workflow_type="deploy", kubernetes=True),
    dict(deploy_target="netlify", workflow_type="deploy", build_output_dir="../etc"),
    dict(deploy_target="netlify", workflow_type="deploy", build_output_dir="/abs"),
    dict(deploy_target="netlify", workflow_type="deploy", build_output_dir="dist; rm -rf /"),
    dict(deploy_target="netlify", workflow_type="deploy", build_output_dir="a b"),
])
def test_invalid_deploy_combinations_rejected(kwargs):
    with pytest.raises(ValueError):
        generate_github_actions_workflow(name="demo", languages="javascript", **kwargs)


@pytest.mark.parametrize("target", TARGETS)
def test_every_action_emitted_for_a_target_has_a_pin_entry(target):
    for ref in re.findall(r"uses: (\S+)", _target(target, "complete")):
        assert ref.rsplit("@", 1)[0] in scaffold_gha.ACTION_REFS, ref


def test_docker_push_skipped_when_repo_has_no_dockerfile():
    wf = yaml.safe_load(_render("complete"))
    step = next(s for s in wf["jobs"]["deploy"]["steps"] if s["name"] == "Build and Push Docker Image")
    assert "hashFiles('Dockerfile') != ''" in step["if"]


def test_rust_language_produces_cargo_steps():
    wf = yaml.safe_load(_render("complete", "rust"))
    assert any("cargo build" in s.get("run", "") for s in wf["jobs"]["build"]["steps"])
    assert any("cargo test" in s.get("run", "") for s in wf["jobs"]["test"]["steps"])


# ---------------------------------------------------------------------------
# Phase 3: security scans
# ---------------------------------------------------------------------------

ALL_SCANS = "gitleaks,semgrep,trivy,checkov,codeql"


def _scans(workflow_type="complete", scans=ALL_SCANS, languages="python,javascript", **kw):
    return yaml.safe_load(_render(workflow_type, languages, security_scans=scans, **kw))


@pytest.mark.parametrize("wf_type", ["build", "test", "complete"])
def test_each_selected_scan_becomes_a_job(wf_type):
    jobs = _scans(wf_type)["jobs"]
    for name in ALL_SCANS.split(","):
        assert name in jobs


def test_only_selected_scans_are_added_and_order_is_stable():
    a = _scans("test", "trivy,gitleaks")["jobs"]
    assert [j for j in a if j in scaffold_gha.SECURITY_SCANS] == ["gitleaks", "trivy"]
    assert "semgrep" not in a


def test_no_scans_by_default():
    jobs = yaml.safe_load(_render("complete"))["jobs"]
    assert not set(jobs) & set(scaffold_gha.SECURITY_SCANS)


def test_complete_deploy_waits_for_every_scan():
    wf = _scans("complete", "gitleaks,trivy")
    assert set(wf["jobs"]["deploy"]["needs"]) == {"test", "gitleaks", "trivy"}


def test_security_type_defaults_to_core_scans():
    jobs = yaml.safe_load(_render("security", "python"))["jobs"]
    assert list(jobs) == ["gitleaks", "semgrep", "trivy"]


def test_scans_ignore_container_and_matrix():
    wf = _scans("complete", "gitleaks,trivy", container_image="my/img:1", matrix=True)
    for name in ("gitleaks", "trivy"):
        job = wf["jobs"][name]
        assert "container" not in job and "strategy" not in job and job["runs-on"] == "ubuntu-latest"


def test_codeql_is_the_only_job_with_elevated_permissions():
    wf = _scans("complete", ALL_SCANS, languages="python,javascript,go")
    assert wf["jobs"]["codeql"]["permissions"]["security-events"] == "write"
    assert {j["language"] for j in wf["jobs"]["codeql"]["strategy"]["matrix"]["include"]} == {
        "python", "javascript-typescript", "go"}
    assert wf["permissions"] == {"contents": "read"}
    assert [n for n, j in wf["jobs"].items() if "permissions" in j] == ["codeql"]


def test_codeql_requires_a_supported_language():
    with pytest.raises(ValueError, match="codeql"):
        scaffold_gha._codeql_job(argparse.Namespace(pin_actions=False), {"languages": {}})


def test_gitleaks_verifies_checksum_and_scans_full_history():
    job = _scans("test", "gitleaks")["jobs"]["gitleaks"]
    assert job["steps"][0]["with"] == {"fetch-depth": 0}
    run = job["steps"][1]["run"]
    assert "sha256sum -c" in run and scaffold_gha.GITLEAKS_VERSION in run


def test_scanners_are_version_pinned():
    wf = _scans("test", "semgrep,checkov,trivy")
    assert f"semgrep=={scaffold_gha.SEMGREP_VERSION}" in wf["jobs"]["semgrep"]["steps"][2]["run"]
    assert f"checkov=={scaffold_gha.CHECKOV_VERSION}" in wf["jobs"]["checkov"]["steps"][2]["run"]
    assert "@v0.36.0" in wf["jobs"]["trivy"]["steps"][1]["uses"]


def test_scan_actions_have_pin_entries_and_pin_cleanly():
    text = _render("complete", "python", security_scans=ALL_SCANS, pin_actions=True)
    for ref in re.findall(r"uses: (\S+)", text):
        assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", ref), ref
        assert ref.rsplit("@", 1)[0] in scaffold_gha.ACTION_REFS


@pytest.mark.parametrize("kwargs", [
    dict(security_scans="snyk", workflow_type="test"),
    dict(security_scans="gitleaks,nope", workflow_type="test"),
    dict(security_scans="gitleaks", workflow_type="deploy"),
    dict(security_scans="gitleaks", workflow_type="reusable"),
])
def test_invalid_security_scans_rejected(kwargs):
    with pytest.raises(ValueError):
        generate_github_actions_workflow(name="demo", languages="python", **kwargs)


# ---------------------------------------------------------------------------
# generate_dependabot_config
# ---------------------------------------------------------------------------

from mcp_server.server import generate_dependabot_config  # noqa: E402


def _dependabot(**kw):
    return yaml.safe_load(generate_dependabot_config(**kw))


def test_dependabot_default_is_github_actions_weekly():
    cfg = _dependabot()
    assert cfg["version"] == 2
    assert [u["package-ecosystem"] for u in cfg["updates"]] == ["github-actions"]
    assert cfg["updates"][0]["schedule"] == {"interval": "weekly"}


def test_dependabot_language_aliases_and_github_actions_always_last():
    cfg = _dependabot(ecosystems="python, javascript,go,rust,pip", schedule="monthly")
    assert [u["package-ecosystem"] for u in cfg["updates"]] == ["pip", "npm", "gomod", "cargo", "github-actions"]
    assert all(u["schedule"]["interval"] == "monthly" for u in cfg["updates"])


def test_dependabot_actions_entry_stays_at_repo_root():
    cfg = _dependabot(ecosystems="npm", directory="/web")
    by_eco = {u["package-ecosystem"]: u["directory"] for u in cfg["updates"]}
    assert by_eco == {"npm": "/web", "github-actions": "/"}


def test_dependabot_groups_minor_and_patch():
    assert _dependabot(ecosystems="npm")["updates"][0]["groups"]["minor-and-patch"]["update-types"] == ["minor", "patch"]


@pytest.mark.parametrize("kw", [
    dict(ecosystems="cobol"), dict(schedule="hourly"), dict(directory="app"),
    dict(directory="/../etc"), dict(directory="/a b"), dict(directory="/x;rm"),
])
def test_dependabot_rejects_bad_input(kw):
    with pytest.raises(ValueError):
        generate_dependabot_config(**kw)


# ---------------------------------------------------------------------------
# audit_github_workflow
# ---------------------------------------------------------------------------

import json  # noqa: E402

from mcp_server.server import audit_github_workflow  # noqa: E402

LEGACY = """
name: old
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/yourorg/devops-os:latest
    steps:
      - uses: actions/checkout@v3
      - run: echo "${{ github.event.pull_request.title }}"
      - uses: actions/upload-artifact@v3
      - uses: some/action@main
"""


def _audit(text):
    return json.loads(audit_github_workflow(text))


def _ids(report):
    return {f["id"] for f in report["findings"]}


def test_audit_flags_the_legacy_generated_workflow_problems():
    ids = _ids(_audit(LEGACY))
    assert {"no-permissions", "no-concurrency", "deprecated-artifact-action", "floating-action-ref",
            "script-injection", "placeholder-container"} <= ids


def test_audit_detects_covered_and_missing_capabilities():
    r = _audit("""
on: push
permissions: {contents: read}
concurrency: {group: x}
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check .
      - run: pytest
      - uses: gitleaks/gitleaks-action@v2
""")
    assert {"lint", "test", "secrets-scan"} <= set(r["covers"])
    assert r["missing"] == ["build", "sast", "dependency-scan"]
    sec = next(s for s in r["suggestions"] if s["tool"] == "generate_github_actions_workflow")
    assert sec["arguments"] == {"workflow_type": "security", "security_scans": "semgrep,trivy"}
    assert "no-permissions" not in _ids(r) and "no-concurrency" not in _ids(r)


def test_step_names_are_not_evidence():
    r = _audit("on: push\njobs:\n  t:\n    runs-on: x\n    steps:\n      - name: 'Test: ArgoCD tool'\n        run: pytest\n")
    assert "deploy" not in r["covers"]


def test_generated_workflow_with_all_scans_audits_clean():
    text = _render("complete", "python", security_scans=ALL_SCANS, pin_actions=True)
    r = _audit(text)
    assert {"secrets-scan", "sast", "dependency-scan", "iac-scan"} <= set(r["covers"])
    assert not [f for f in r["findings"] if f["severity"] in ("medium", "high")]
    assert "actions-not-sha-pinned" not in _ids(r)


def test_audit_never_suggests_replacing_the_file():
    for s in _audit(LEGACY)["suggestions"]:
        assert "replace" not in s["why"].lower()


@pytest.mark.parametrize("bad", [
    "", "   ", "just a string", "key: value", "jobs: {}", "jobs: [a, b]", "a: [unclosed",
    "x" * 100_001,
    "a: &a [1]\n" + "b: [" + ", ".join(["*a"] * 200) + "]\njobs: {j: {steps: []}}",
])
def test_audit_rejects_non_workflow_or_hostile_input(bad):
    with pytest.raises(ValueError):
        audit_github_workflow(bad)


def test_audit_handles_reusable_workflow_jobs():
    r = _audit("on: push\njobs:\n  call:\n    uses: org/repo/.github/workflows/ci.yml@v1\n")
    assert r["jobs"] == ["call"]


# ---------------------------------------------------------------------------
# analyze_repo
# ---------------------------------------------------------------------------

import mcp_server.server as server_mod  # noqa: E402
from mcp_server.server import analyze_repo  # noqa: E402


def _repo(tmp_path, files):
    for rel, content in files.items():
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return str(tmp_path)


def _analyze(tmp_path, files):
    return json.loads(analyze_repo(_repo(tmp_path, files)))


def test_analyze_vite_react_on_vercel(tmp_path):
    r = _analyze(tmp_path, {
        "package.json": json.dumps({"dependencies": {"react": "18"}, "devDependencies": {"vite": "5"}}),
        "package-lock.json": "{}", "vercel.json": "{}"})
    assert r["languages"] == ["javascript"] and {"react", "vite"} <= set(r["frameworks"])
    assert r["package_manager"] == "npm"
    assert r["recommended_deploy_target"] == "vercel" and r["build_output_dir"] == "dist"
    gen = next(c for c in r["recommended_calls"] if c["tool"] == "generate_github_actions_workflow")
    assert gen["arguments"]["deploy_target"] == "vercel" and gen["arguments"]["workflow_type"] == "complete"


@pytest.mark.parametrize("wrangler, expected", [
    ('{"name": "w"}', "cloudflare-workers"),
    ('// c\n{"pages_build_output_dir": "dist"}', "cloudflare-pages"),
])
def test_analyze_cloudflare_flavours(tmp_path, wrangler, expected):
    r = _analyze(tmp_path, {"package.json": "{}", "wrangler.jsonc": wrangler})
    assert r["recommended_deploy_target"] == expected


def test_analyze_python_docker_netlify_render(tmp_path):
    assert _analyze(tmp_path / "a", {"requirements.txt": "fastapi==0.1\n", "Dockerfile": "FROM x"})["frameworks"] == ["fastapi"]
    assert _analyze(tmp_path / "b", {"package.json": "{}", "netlify.toml": ""})["recommended_deploy_target"] == "netlify"
    assert _analyze(tmp_path / "c", {"requirements.txt": "", "render.yaml": ""})["recommended_deploy_target"] == "render"


def test_analyze_docker_alone_is_not_a_hosting_target(tmp_path):
    r = _analyze(tmp_path, {"go.mod": "module x", "Dockerfile": "FROM x"})
    assert r["deploy_signals"] == ["docker"] and r["recommended_deploy_target"] == ""
    assert r["languages"] == ["go"]


def test_analyze_monorepo_subdirectories(tmp_path):
    r = _analyze(tmp_path, {
        "backend/requirements.txt": "django\n", "frontend/package.json": json.dumps({"dependencies": {"next": "14"}})})
    assert set(r["languages"]) == {"python", "javascript"} and {"django", "next"} <= set(r["frameworks"])
    assert {p["dir"] for p in r["projects"]} == {"backend", "frontend"}
    dirs = {c["arguments"].get("directory") for c in r["recommended_calls"] if c["tool"] == "generate_dependabot_config"}
    assert dirs == {"/backend", "/frontend"}
    assert any("working-directory" in n for n in r["notes"])


def test_analyze_does_not_descend_past_one_level_or_into_node_modules(tmp_path):
    r = _analyze(tmp_path, {"a/b/package.json": "{}", "node_modules/x/package.json": "{}", "node_modules/package.json": "{}"})
    assert r["languages"] == []


def test_analyze_pnpm_note(tmp_path):
    r = _analyze(tmp_path, {"package.json": "{}", "pnpm-lock.yaml": ""})
    assert r["package_manager"] == "pnpm" and any("npm ci" in n for n in r["notes"])


def test_analyze_audits_existing_workflows_and_recommends_gap_fill(tmp_path):
    r = _analyze(tmp_path, {
        "package.json": "{}",
        ".github/workflows/ci.yml": "on: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: npm test\n",
        ".github/workflows/broken.yml": "not: a workflow",
    })
    by_file = {w["file"]: w for w in r["existing_workflows"]}
    assert "test" in by_file["ci.yml"]["covers"] and "sast" in by_file["ci.yml"]["missing"]
    assert "error" in by_file["broken.yml"]
    tools = [c["tool"] for c in r["recommended_calls"]]
    assert "audit_github_workflow" in tools
    sec = next(c for c in r["recommended_calls"] if c["arguments"].get("workflow_type") == "security")
    assert sec["arguments"]["security_scans"] == "gitleaks,semgrep,trivy"
    # An existing CI must never trigger a "generate a first pipeline" recommendation.
    assert not any(c["arguments"].get("workflow_type") in ("complete", "test") for c in r["recommended_calls"])


def test_analyze_skips_dependabot_recommendation_when_present(tmp_path):
    r = _analyze(tmp_path, {"package.json": "{}", ".github/dependabot.yml": "version: 2"})
    assert r["has_dependabot"] and not any(c["tool"] == "generate_dependabot_config" for c in r["recommended_calls"])


def test_analyze_empty_and_invalid_manifests(tmp_path):
    (tmp_path / "e").mkdir()
    r = json.loads(analyze_repo(str(tmp_path / "e")))
    assert r["languages"] == [] and r["recommended_calls"][0]["tool"] == "generate_dependabot_config"
    r = _analyze(tmp_path / "bad", {"package.json": "{not json"})
    assert r["languages"] == [] and any("not valid JSON" in n for n in r["notes"])


def test_analyze_returns_derived_facts_not_file_contents(tmp_path):
    secret = "SUPER-SECRET-VALUE-123"
    out = analyze_repo(_repo(tmp_path, {"package.json": json.dumps({"name": secret}), "vercel.json": secret}))
    assert secret not in out


def test_analyze_ignores_oversized_files(tmp_path):
    big = json.dumps({"dependencies": {"react": "1"}}) + " " * 600_000
    assert _analyze(tmp_path, {"package.json": big})["languages"] == []


def test_analyze_refuses_symlinks_that_escape_the_repo(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "package.json").write_text('{"dependencies": {"react": "1"}}')
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").symlink_to(outside / "package.json")
    (repo / "frontend").symlink_to(outside, target_is_directory=True)
    r = json.loads(analyze_repo(str(repo)))
    assert r["languages"] == [] and r["frameworks"] == []


@pytest.mark.parametrize("bad", ["", "   ", "/definitely/not/here", "bad\x00path"])
def test_analyze_rejects_bad_paths(bad):
    with pytest.raises(ValueError):
        analyze_repo(bad)


def test_analyze_rejects_a_file_path(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x")
    with pytest.raises(ValueError):
        analyze_repo(str(f))


def test_analyze_disabled_with_remote_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "_config", type("C", (), {"profile": "remote"})())
    with pytest.raises(ValueError, match="remote profile"):
        analyze_repo(str(tmp_path))
