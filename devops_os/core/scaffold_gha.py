#!/usr/bin/env python3
"""
DevOps-OS GitHub Actions Workflow Generator

This script generates GitHub Actions workflow files for CI/CD pipelines
that run on GitHub-hosted runners (ubuntu-latest) with the official setup-*
actions. Running jobs in a container image is optional.

Features:
- Generates workflows for build, test, deploy, or complete CI/CD
- Supports multiple programming languages
- Configurable Kubernetes deployment methods
- Customizable through command-line arguments or environment variables
- Optional container image (default: run directly on the runner)
- Least-privilege permissions, concurrency, and optional SHA pinning
- Secrets and environment variable management
- Matrix build support for multiple OS/architectures
"""

import os
import sys
import argparse
import json
import yaml
from string import Template
from pathlib import Path


class _NoAliasDumper(yaml.Dumper):
    """Custom YAML Dumper that never emits anchors or aliases.

    When the same Python object (e.g. a ``branches`` list) is referenced in
    multiple places inside the workflow dict, the default PyYAML serialiser
    collapses those references into an anchor/alias pair such as::

        branches: &id001
        - main
        pull_request:
          branches: *id001

    GitHub Actions does not support YAML aliases, and the output is
    confusing to users.  This dumper overrides ``ignore_aliases`` so that
    every occurrence is written out in full.
    """

    def ignore_aliases(self, data):  # noqa: ARG002
        return True


def _str_representer(dumper, data):
    """Emit multi-line strings (``run:`` scripts) as literal blocks."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_NoAliasDumper.add_representer(str, _str_representer)


# Default paths
TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.getcwd()
ENV_CONFIG_PATH = os.path.join(TEMPLATE_DIR, "devcontainer.env.json")

# Default workflow types
WORKFLOW_TYPES = ["build", "test", "deploy", "complete", "reusable", "security"]

# Environment variable prefixes
ENV_PREFIX = "DEVOPS_OS_GHA_"

def parse_arguments():
    """Parse command line arguments with environment variable fallbacks."""
    parser = argparse.ArgumentParser(description="Generate GitHub Actions workflow files for DevOps-OS")
    parser.add_argument("--name", 
                       help="Workflow name",
                       default=os.environ.get(f"{ENV_PREFIX}NAME", "DevOps-OS"))
    parser.add_argument("--type", choices=WORKFLOW_TYPES, 
                       help="Type of workflow to generate",
                       default=os.environ.get(f"{ENV_PREFIX}TYPE", "complete"))
    parser.add_argument("--languages", 
                       help="Comma-separated list of languages to enable (python,java,javascript,go)",
                       default=os.environ.get(f"{ENV_PREFIX}LANGUAGES", "python,javascript"))
    parser.add_argument("--kubernetes", action="store_true", 
                       help="Include Kubernetes deployment steps",
                       default=os.environ.get(f"{ENV_PREFIX}KUBERNETES", "false").lower() in ("true", "1", "yes"))
    parser.add_argument("--registry", 
                       help="Container registry URL",
                       default=os.environ.get(f"{ENV_PREFIX}REGISTRY", "ghcr.io"))
    parser.add_argument("--k8s-method", choices=["kubectl", "kustomize", "argocd", "flux"],
                       help="Kubernetes deployment method",
                       default=os.environ.get(f"{ENV_PREFIX}K8S_METHOD", "kubectl"))
    parser.add_argument("--output", 
                       help="Output directory for generated workflow files",
                       default=os.environ.get(f"{ENV_PREFIX}OUTPUT", os.path.join(OUTPUT_DIR, ".github/workflows")))
    parser.add_argument("--custom-values", 
                       help="Path to custom values JSON file",
                       default=os.environ.get(f"{ENV_PREFIX}CUSTOM_VALUES"))
    parser.add_argument("--image",
                       help="Optional container image to run jobs in (default: none, jobs run on ubuntu-latest)",
                       default=os.environ.get(f"{ENV_PREFIX}IMAGE", ""))
    parser.add_argument("--deploy-target", choices=sorted(DEPLOY_TARGETS), default=os.environ.get(f"{ENV_PREFIX}DEPLOY_TARGET", ""),
                       help="Deploy to a hosting platform instead of Docker/Kubernetes")
    parser.add_argument("--build-output-dir", default=os.environ.get(f"{ENV_PREFIX}BUILD_OUTPUT_DIR", "dist"),
                       help="Directory the build writes to (static hosting targets)")
    parser.add_argument("--security-scans", default=os.environ.get(f"{ENV_PREFIX}SECURITY_SCANS", ""),
                       help=f"Comma-separated security scans to add: {','.join(SECURITY_SCANS)}")
    parser.add_argument("--pin-actions", action="store_true", dest="pin_actions",
                       help="Pin third-party actions to full commit SHAs (with a version comment)",
                       default=os.environ.get(f"{ENV_PREFIX}PIN_ACTIONS", "false").lower() in ("true", "1", "yes"))
    parser.add_argument("--branches", 
                       help="Comma-separated list of branches to trigger workflow",
                       default=os.environ.get(f"{ENV_PREFIX}BRANCHES", "main"))
    parser.add_argument("--matrix", action="store_true",
                       help="Enable matrix builds (multiple OS/architectures)",
                       default=os.environ.get(f"{ENV_PREFIX}MATRIX", "false").lower() in ("true", "1", "yes"))
    parser.add_argument("--env-file", 
                       help="Use DevOps-OS devcontainer.env.json for configuration",
                       default=os.environ.get(f"{ENV_PREFIX}ENV_FILE", ENV_CONFIG_PATH))
    parser.add_argument("--reusable", action="store_true", 
                       help="Generate a reusable workflow that can be called from other workflows",
                       default=os.environ.get(f"{ENV_PREFIX}REUSABLE", "false").lower() in ("true", "1", "yes"))
    
    args = parser.parse_args()
    
    # If type is 'reusable', set reusable flag to True
    if args.type == "reusable":
        args.reusable = True
    
    return args

def load_custom_values(file_path):
    """Load custom values from a JSON file."""
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def load_env_config(file_path):
    """Load DevOps-OS environment configuration."""
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            # Remove comments that start with // for JSON parsing
            lines = f.readlines()
            cleaned_json = ""
            for line in lines:
                if not line.strip().startswith("//"):
                    cleaned_json += line
            return json.loads(cleaned_json)
    return {}

def create_directory_structure(output_dir):
    """Create the necessary directory structure."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def generate_language_config(languages_str, env_config=None):
    """Generate language configuration JSON."""
    languages = languages_str.split(',')
    
    # Default to env_config if available, otherwise use languages from args
    if env_config and 'languages' in env_config:
        config = env_config['languages']
    else:
        config = {
            "python": "python" in languages,
            "java": "java" in languages,
            "javascript": "javascript" in languages, 
            "go": "go" in languages,
            "rust": "rust" in languages,
        }
    
    return config

def generate_kubernetes_config(k8s_enabled, k8s_method, env_config=None):
    """Generate Kubernetes configuration JSON."""
    # Default to env_config if available
    if env_config and 'kubernetes' in env_config:
        return env_config['kubernetes']
    
    if not k8s_enabled:
        return {"k9s": False, "kustomize": False, "argocd_cli": False, "flux": False}
    
    config = {
        "k9s": True,
        "kustomize": k8s_method == "kustomize",
        "argocd_cli": k8s_method == "argocd",
        "flux": k8s_method == "flux",
        "kind": False,
        "minikube": False
    }
    return config

def generate_cicd_config(env_config=None):
    """Generate CI/CD tools configuration JSON."""
    if env_config and 'cicd' in env_config:
        return env_config['cicd']
    
    return {
        "docker": True,
        "terraform": True,
        "kubectl": True,
        "helm": True,
        "github_actions": True
    }

def generate_build_tools_config(env_config=None):
    """Generate build tools configuration JSON."""
    if env_config and 'build_tools' in env_config:
        return env_config['build_tools']
    
    return {
        "gradle": True,
        "maven": True,
        "ant": False,
        "make": True,
        "cmake": False
    }

def generate_code_analysis_config(env_config=None):
    """Generate code analysis tools configuration JSON."""
    if env_config and 'code_analysis' in env_config:
        return env_config['code_analysis']
    
    return {
        "sonarqube": True,
        "checkstyle": True,
        "pmd": False,
        "eslint": True,
        "pylint": True
    }

def generate_devops_tools_config(env_config=None):
    """Generate DevOps tools configuration JSON."""
    if env_config and 'devops_tools' in env_config:
        return env_config['devops_tools']
    
    return {
        "nexus": False,
        "prometheus": True,
        "grafana": True,
        "elk": True,
        "jenkins": False
    }

# ---------------------------------------------------------------------------
# Action references
# ---------------------------------------------------------------------------

# action -> (floating major tag, exact release tag, full commit SHA).
# Verified against the GitHub releases API on 2026-10-04. Refresh when
# bumping; tests/test_gha_generator.py checks every action emitted by the
# generator has an entry here, so a new action cannot ship unpinned.
ACTION_REFS = {
    "actions/checkout": ("v7", "v7.0.1", "3d3c42e5aac5ba805825da76410c181273ba90b1"),
    "actions/setup-node": ("v7", "v7.0.0", "820762786026740c76f36085b0efc47a31fe5020"),
    "actions/setup-python": ("v7", "v7.0.0", "5fda3b95a4ea91299a34e894583c3862153e4b97"),
    "actions/setup-go": ("v7", "v7.0.0", "b7ad1dad31e06c5925ef5d2fc7ad053ef454303e"),
    "actions/setup-java": ("v6", "v6.0.1", "de7274f081f381c8f8158605e0321c36c376e2e6"),
    "actions/upload-artifact": ("v7", "v7.0.1", "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"),
    "codecov/codecov-action": ("v7", "v7.1.1", "303a32d7a59b442fa8d48b6a1cc6825c09c847a5"),
    "cloudflare/wrangler-action": ("v4", "v4.1.3", "953926a2e2182532811c01a25e53647d93bf07c0"),
    "actions/configure-pages": ("v6", "v6.0.0", "45bfe0192ca1faeb007ade9deae92b16b8254a0d"),
    "actions/upload-pages-artifact": ("v5", "v5.0.0", "fc324d3547104276b827a68afc52ff2a11cc49c9"),
    "actions/deploy-pages": ("v5", "v5.0.1", "368f82528645a54fb793d4d04e342629a3f51346"),
    "github/codeql-action/init": ("v4", "v4.38.2", "2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2"),
    "github/codeql-action/analyze": ("v4", "v4.38.2", "2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2"),
    # trivy-action publishes no floating major tag, so the exact tag is the reference.
    "aquasecurity/trivy-action": ("v0.36.0", "v0.36.0", "ed142fd0673e97e23eac54620cfb913e5ce36c25"),
    # flux2 publishes no floating major tag, so the exact tag is the reference.
    "fluxcd/flux2/action": ("v2.9.6", "v2.9.6", "b9c17924adb533d3617ec7de97a7b0f4acc07b39"),
}

ARGOCD_VERSION = "v3.5.3"
# npm CLIs run through npx, pinned to an exact version (checked 2026-10-04).
VERCEL_CLI_VERSION = "62.2.0"
NETLIFY_CLI_VERSION = "27.10.2"

# Scanner versions (checked 2026-10-04). Gitleaks is downloaded and checksum-verified
# rather than using gitleaks-action, which needs a paid licence for organisation repos.
GITLEAKS_VERSION = "8.30.1"
SEMGREP_VERSION = "1.179.0"
CHECKOV_VERSION = "3.3.22"
SECURITY_SCANS = ["gitleaks", "semgrep", "trivy", "checkov", "codeql"]
DEFAULT_SECURITY_SCANS = "gitleaks,semgrep,trivy"
# language -> (CodeQL language id, build mode)
CODEQL_LANGUAGES = {
    "python": ("python", "none"),
    "javascript": ("javascript-typescript", "none"),
    "java": ("java-kotlin", "none"),
    "go": ("go", "autobuild"),
    "rust": ("rust", "none"),
}

# Hosting targets that replace the default Docker push / Kubernetes deploy.
# Value: repository secrets the generated job expects (names only, never values).
DEPLOY_TARGETS = {
    "vercel": ["VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID"],
    "cloudflare-workers": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"],
    "cloudflare-pages": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"],
    "netlify": ["NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID"],
    "render": ["RENDER_DEPLOY_HOOK_URL"],
    "github-pages": [],
}

_RUN_ON_PR_ONLY = "${{ github.event_name == 'pull_request' }}"


def _uses(action, args):
    """Return the ``uses:`` reference for an action (major tag, or SHA if pinning)."""
    major, _tag, sha = ACTION_REFS[action]
    return f"{action}@{sha}" if getattr(args, "pin_actions", False) else f"{action}@{major}"


def dump_workflow(workflow, args=None):
    """Serialise a workflow dict to YAML.

    Never emits anchors/aliases. When ``args.pin_actions`` is set, each pinned
    reference gets a trailing ``# <release tag>`` comment so humans and
    Dependabot can tell which version a SHA is.
    """
    text = yaml.dump(workflow, sort_keys=False, Dumper=_NoAliasDumper, width=10_000)
    secrets = DEPLOY_TARGETS.get(getattr(args, "deploy_target", "") or "", [])
    if secrets:
        text = ("# Create these repository secrets before the first run "
                "(Settings > Secrets and variables > Actions):\n"
                + "".join(f"#   {name}\n" for name in secrets)
                + "# Test your setup locally first: call the generate_deploy_preflight tool "
                  f"(deploy_target={args.deploy_target}).\n" + text)
    if getattr(args, "pin_actions", False):
        for action, (_major, tag, sha) in ACTION_REFS.items():
            text = text.replace(f"{action}@{sha}\n", f"{action}@{sha} # {tag}\n")
    return text


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

def _branches(args):
    return [b.strip() for b in args.branches.split(',')]


def _container_image(args, values):
    """Optional job container. Empty string (the default) means run on the runner."""
    return values.get('container_image') or getattr(args, 'image', '') or ""


def _new_job(args, values, steps, needs=None, condition=None, permissions=None, environment=None):
    job = {}
    if needs:
        job["needs"] = needs
    if condition:
        job["if"] = condition
    if permissions:
        job["permissions"] = permissions
    if environment:
        job["environment"] = environment
    job["runs-on"] = "ubuntu-latest"
    image = _container_image(args, values)
    if image:
        job["container"] = {"image": image, "options": "--user root"}
    job["steps"] = steps
    if args.matrix:
        job["strategy"] = {
            "matrix": {"os": ["ubuntu-latest"], "arch": ["amd64", "arm64"]},
            "fail-fast": False,
        }
        job["runs-on"] = "${{ matrix.os }}"
    return job


def _artifact_suffix(args):
    return "-${{ matrix.os }}-${{ matrix.arch }}" if args.matrix else ""


def _checkout_step(args):
    return {"name": "Checkout code", "uses": _uses("actions/checkout", args)}


def _setup_steps(args, values, configs):
    """Language toolchain setup via the official setup-* actions."""
    langs = configs["languages"]
    steps = []
    if langs.get("python", False):
        steps.append({
            "name": "Set up Python",
            "uses": _uses("actions/setup-python", args),
            "with": {"python-version": values.get("python_version", "3.12")},
        })
    if langs.get("javascript", False):
        steps.append({
            "name": "Set up Node.js",
            "uses": _uses("actions/setup-node", args),
            "with": {"node-version": values.get("node_version", "lts/*")},
        })
    if langs.get("go", False):
        steps.append({
            "name": "Set up Go",
            "uses": _uses("actions/setup-go", args),
            "with": {"go-version": values.get("go_version", "stable")},
        })
    if langs.get("java", False):
        steps.append({
            "name": "Set up Java",
            "uses": _uses("actions/setup-java", args),
            "with": {"distribution": "temurin", "java-version": values.get("java_version", "21")},
        })
    return steps


def _build_steps(args, values, configs):
    langs = configs["languages"]
    steps = [_checkout_step(args)] + _setup_steps(args, values, configs)
    if langs.get("python", False):
        steps += [
            {"name": "Install Python dependencies",
             "run": "if [ -f requirements.txt ]; then pip install -r requirements.txt; fi"},
            {"name": "Build Python package",
             "run": "if [ -f setup.py ] || [ -f pyproject.toml ]; then pip install -e .; fi"},
        ]
    if langs.get("java", False):
        steps += [
            {"name": "Build with Maven",
             "run": "if [ -f pom.xml ]; then mvn -B package --file pom.xml; fi"},
            {"name": "Build with Gradle",
             "run": "if [ -f build.gradle ]; then ./gradlew build; fi"},
        ]
    if langs.get("javascript", False):
        steps += [
            {"name": "Install Node.js dependencies",
             "run": "if [ -f package.json ]; then npm ci; fi"},
            {"name": "Build JavaScript/TypeScript",
             "run": "if [ -f package.json ]; then npm run build --if-present; fi"},
        ]
    if langs.get("go", False):
        steps.append({"name": "Build Go application",
                      "run": "if [ -f go.mod ]; then go build -v ./...; fi"})
    if langs.get("rust", False):  # cargo is preinstalled on ubuntu-latest
        steps.append({"name": "Build Rust application",
                      "run": "if [ -f Cargo.toml ]; then cargo build --release; fi"})
    steps.append({
        "name": "Upload build artifacts",
        "uses": _uses("actions/upload-artifact", args),
        "with": {
            "name": f"build-artifacts{_artifact_suffix(args)}",
            "path": values.get("artifact_path", "dist/"),
            "retention-days": 1,
        },
    })
    return steps


def _test_steps(args, values, configs):
    langs = configs["languages"]
    analysis = configs.get("code_analysis", {})
    steps = [_checkout_step(args)] + _setup_steps(args, values, configs)
    if langs.get("python", False):
        steps += [
            {"name": "Install Python dependencies",
             "run": "if [ -f requirements.txt ]; then pip install -r requirements.txt pytest pytest-cov; fi"},
            {"name": "Run Python tests",
             "run": "if [ -d tests ]; then python -m pytest --cov=./ --cov-report=xml; fi"},
        ]
        if analysis.get("pylint", False):
            steps.append({"name": "Run Pylint",
                          "run": "if command -v pylint &> /dev/null; then git ls-files '*.py' | xargs -r pylint --disable=C0111; fi"})
    if langs.get("java", False):
        steps += [
            {"name": "Run Java tests with Maven",
             "run": "if [ -f pom.xml ]; then mvn -B test --file pom.xml; fi"},
            {"name": "Run Java tests with Gradle",
             "run": "if [ -f build.gradle ]; then ./gradlew test; fi"},
        ]
        if analysis.get("checkstyle", False):
            steps.append({"name": "Run Checkstyle",
                          "run": "if [ -f pom.xml ]; then mvn checkstyle:checkstyle; fi"})
    if langs.get("javascript", False):
        steps += [
            {"name": "Install Node.js dependencies",
             "run": "if [ -f package.json ]; then npm ci; fi"},
            {"name": "Run JavaScript tests",
             "run": "if [ -f package.json ]; then npm test; fi"},
        ]
        if analysis.get("eslint", False):
            steps.append({"name": "Run ESLint",
                          "run": "if [ -f package.json ] && grep -q eslint package.json; then npm run lint; fi"})
    if langs.get("go", False):
        steps.append({"name": "Run Go tests",
                      "run": "if [ -f go.mod ]; then go test -v ./...; fi"})
    if langs.get("rust", False):
        steps.append({"name": "Run Rust tests",
                      "run": "if [ -f Cargo.toml ]; then cargo test; fi"})
    steps += [
        {"name": "Upload test results",
         "uses": _uses("actions/upload-artifact", args),
         "with": {
             "name": f"test-results{_artifact_suffix(args)}",
             "path": values.get("test_report_path", "test-reports/"),
             "retention-days": 1,
         }},
        {"name": "Upload coverage reports",
         "uses": _uses("codecov/codecov-action", args),
         "with": {"files": "./coverage.xml,./coverage/lcov.info", "fail_ci_if_error": False}},
    ]
    return steps


def _docker_push_step(args, token_secret):
    """Build and push the image.

    The registry token reaches the script through ``env:`` and ``printf`` rather than
    being pasted into the script text, so quotes or ``$(...)`` in a secret cannot break
    or inject into the command. The tag is lower-cased because Docker rejects upper-case
    repository names and GitHub owners often have them.
    """
    reg = args.registry
    return {
        "name": "Build and Push Docker Image",
        # Skip quietly for repos without a Dockerfile instead of failing the deploy.
        "if": "github.ref == 'refs/heads/main' && hashFiles('Dockerfile') != ''",
        "env": {"REGISTRY_TOKEN": f"${{{{ secrets.{token_secret} }}}}"},
        "run": "\n".join([
            f"printf '%s' \"$REGISTRY_TOKEN\" | docker login {reg} -u \"$GITHUB_ACTOR\" --password-stdin",
            f"IMAGE=\"{reg}/$(printf '%s' \"$GITHUB_REPOSITORY\" | tr '[:upper:]' '[:lower:]'):latest\"",
            "docker build -t \"$IMAGE\" .",
            "docker push \"$IMAGE\"",
        ]),
    }


# The kubeconfig reaches the script through env: it routinely contains quotes and
# newlines that would break (or inject into) a secret pasted into the script text.
_KUBECONFIG_ENV = {"KUBECONFIG_DATA": "${{ secrets.KUBECONFIG }}"}
_KUBECONFIG_RUN = [
    "umask 077",
    "mkdir -p \"$HOME/.kube\"",
    "printf '%s\\n' \"$KUBECONFIG_DATA\" > \"$HOME/.kube/config\"",
]


def _argocd_install_step():
    """Install the ArgoCD CLI (not preinstalled on ubuntu-latest), verifying its checksum."""
    base = f"https://github.com/argoproj/argo-cd/releases/download/{ARGOCD_VERSION}"
    return {
        "name": "Install ArgoCD CLI",
        "run": "\n".join([
            f"curl -sSLfo argocd {base}/argocd-linux-amd64",
            f"curl -sSLfo cli_checksums.txt {base}/cli_checksums.txt",
            "grep ' argocd-linux-amd64$' cli_checksums.txt | sed 's/argocd-linux-amd64/argocd/' | sha256sum -c -",
            "sudo install -m 0755 argocd /usr/local/bin/argocd",
        ]),
    }


def _flux_install_step(args):
    return {"name": "Install Flux CLI", "uses": _uses("fluxcd/flux2/action", args)}


def _k8s_steps(args, values):
    """Kubernetes deployment steps for ``args.k8s_method``.

    ubuntu-latest ships kubectl (and ``kubectl -k`` for kustomize) but not the
    ArgoCD or Flux CLIs, so those are installed unless a container supplies them.
    """
    cond = "github.ref == 'refs/heads/main'"
    needs_install = not _container_image(args, values)
    method = args.k8s_method
    if method == "kubectl":
        return [{"name": "Deploy to Kubernetes", "if": cond, "env": dict(_KUBECONFIG_ENV), "run": "\n".join(
            _KUBECONFIG_RUN + [
                "kubectl apply -f ./k8s/deployment.yaml",
                "kubectl apply -f ./k8s/service.yaml",
                "kubectl rollout status deployment/my-app"])}]
    if method == "kustomize":
        return [{"name": "Deploy to Kubernetes with Kustomize", "if": cond,
                 "run": "\n".join(_KUBECONFIG_RUN + [
                     "kubectl apply -k \"./k8s/overlays/$ENVIRONMENT\"",
                     "kubectl rollout status deployment/my-app"]),
                 "env": {**_KUBECONFIG_ENV,
                         "ENVIRONMENT": "${{ github.event.inputs.environment || 'dev' }}"}}]
    if method == "argocd":
        steps = [_argocd_install_step()] if needs_install else []
        steps.append({
            "name": "Deploy with ArgoCD", "if": cond,
            "run": "\n".join([
                "argocd login \"$ARGOCD_SERVER\" --username \"$ARGOCD_USERNAME\" --password \"$ARGOCD_PASSWORD\" --insecure",
                "argocd app sync my-application",
                "argocd app wait my-application --health"]),
            "env": {"ARGOCD_SERVER": "${{ secrets.ARGOCD_SERVER }}",
                    "ARGOCD_USERNAME": "${{ secrets.ARGOCD_USERNAME }}",
                    "ARGOCD_PASSWORD": "${{ secrets.ARGOCD_PASSWORD }}"}})
        return steps
    if method == "flux":
        steps = [_flux_install_step(args)] if needs_install else []
        steps.append({"name": "Deploy with Flux", "if": cond, "run": "\n".join([
            "flux reconcile source git flux-system",
            "flux reconcile kustomization flux-system"])})
        return steps
    return []


def _js_build_steps(args, values):
    """Install and build a JavaScript project (used by hosting-target deploys)."""
    return [
        {"name": "Set up Node.js", "uses": _uses("actions/setup-node", args),
         "with": {"node-version": values.get("node_version", "lts/*")}},
        {"name": "Install dependencies", "run": "npm ci"},
        {"name": "Build", "run": "npm run build --if-present"},
    ]


def _target_steps(args, values):
    """Steps (and optional job settings) for a hosting ``deploy_target``.

    Returns ``(steps, job_settings)``. Credentials are only ever referenced as
    ``secrets.*`` and are scoped to the step that needs them.
    """
    target = args.deploy_target
    out_dir = getattr(args, "build_output_dir", "") or "dist"
    checkout = _checkout_step(args)
    if target == "vercel":
        v = f"npx --yes vercel@{VERCEL_CLI_VERSION}"
        return [checkout, {"name": "Set up Node.js", "uses": _uses("actions/setup-node", args),
                           "with": {"node-version": values.get("node_version", "lts/*")}},
                {"name": "Deploy to Vercel",
                 "env": {"VERCEL_TOKEN": "${{ secrets.VERCEL_TOKEN }}",
                         "VERCEL_ORG_ID": "${{ secrets.VERCEL_ORG_ID }}",
                         "VERCEL_PROJECT_ID": "${{ secrets.VERCEL_PROJECT_ID }}"},
                 "run": "\n".join([
                     f"{v} pull --yes --environment=production --token=\"$VERCEL_TOKEN\"",
                     f"{v} build --prod --token=\"$VERCEL_TOKEN\"",
                     f"{v} deploy --prebuilt --prod --token=\"$VERCEL_TOKEN\""])}], {}
    if target in ("cloudflare-workers", "cloudflare-pages"):
        command = ("deploy" if target == "cloudflare-workers"
                   else f"pages deploy {out_dir} --project-name={args.name}")
        return [checkout] + _js_build_steps(args, values) + [
            {"name": "Deploy to Cloudflare", "uses": _uses("cloudflare/wrangler-action", args),
             "with": {"apiToken": "${{ secrets.CLOUDFLARE_API_TOKEN }}",
                      "accountId": "${{ secrets.CLOUDFLARE_ACCOUNT_ID }}",
                      "command": command}}], {}
    if target == "netlify":
        return [checkout] + _js_build_steps(args, values) + [
            {"name": "Deploy to Netlify",
             "env": {"NETLIFY_AUTH_TOKEN": "${{ secrets.NETLIFY_AUTH_TOKEN }}",
                     "NETLIFY_SITE_ID": "${{ secrets.NETLIFY_SITE_ID }}"},
             "run": f"npx --yes netlify-cli@{NETLIFY_CLI_VERSION} deploy --prod --dir={out_dir}"}], {}
    if target == "render":
        return [{"name": "Trigger Render deploy",
                 "env": {"RENDER_DEPLOY_HOOK_URL": "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"},
                 "run": "curl -fsS -X POST \"$RENDER_DEPLOY_HOOK_URL\" > /dev/null"}], {}
    if target == "github-pages":
        steps = [checkout,
                 {"name": "Configure Pages", "uses": _uses("actions/configure-pages", args)}]
        steps += _js_build_steps(args, values)
        steps += [
            {"name": "Upload Pages artifact", "uses": _uses("actions/upload-pages-artifact", args),
             "with": {"path": out_dir}},
            {"name": "Deploy to GitHub Pages", "id": "deployment",
             "uses": _uses("actions/deploy-pages", args)}]
        return steps, {
            "permissions": {"contents": "read", "pages": "write", "id-token": "write"},
            "environment": {"name": "github-pages",
                            "url": "${{ steps.deployment.outputs.page_url }}"}}
    raise ValueError(f"Unknown deploy target '{target}'. Valid targets: {sorted(DEPLOY_TARGETS)}")


def _deploy_steps(args, values, token_secret="REGISTRY_TOKEN"):
    steps = [_checkout_step(args), _docker_push_step(args, token_secret)]
    if args.kubernetes:
        steps += _k8s_steps(args, values)
    return steps


def _deploy_job(args, values, needs=None, condition=None):
    """Deploy job: a hosting target if ``args.deploy_target`` is set, else Docker/Kubernetes."""
    if getattr(args, "deploy_target", ""):
        steps, settings = _target_steps(args, values)
        condition = condition or "github.ref == 'refs/heads/main'"
        return _new_job(args, values, steps, needs=needs, condition=condition, **settings)
    return _new_job(args, values, _deploy_steps(args, values), needs=needs, condition=condition)


def _triggers(args, pull_request=True, environment_input=False):
    on = {"push": {"branches": _branches(args)}}
    if pull_request:
        on["pull_request"] = {"branches": _branches(args)}
    if environment_input:
        on["workflow_dispatch"] = {"inputs": {"environment": {
            "description": "Environment to deploy to",
            "required": True,
            "default": "dev",
            "type": "choice",
            "options": ["dev", "test", "staging", "prod"],
        }}}
    else:
        on["workflow_dispatch"] = {}
    return on


def _concurrency(cancel):
    return {"group": "${{ github.workflow }}-${{ github.ref }}", "cancel-in-progress": cancel}


def _workflow(name, on, jobs, cancel_in_progress):
    """Assemble a workflow with least-privilege permissions and concurrency."""
    return {
        "name": name,
        "on": on,
        "permissions": {"contents": "read"},
        "concurrency": _concurrency(cancel_in_progress),
        "jobs": jobs,
    }



def parse_security_scans(value):
    """Return the validated, de-duplicated list of scans from a comma-separated string."""
    scans = []
    for item in (value or "").split(","):
        item = item.strip().lower()
        if item and item not in scans:
            if item not in SECURITY_SCANS:
                raise ValueError(f"Unknown security scan '{item}'. Valid scans: {SECURITY_SCANS}")
            scans.append(item)
    return scans


def _scan_job(args, steps, **extra):
    """A scan job. Scans always run on the runner (never in the optional container)."""
    return {"runs-on": "ubuntu-latest", **extra, "steps": steps}


def _gitleaks_job(args):
    ver = GITLEAKS_VERSION
    tarball = f"gitleaks_{ver}_linux_x64.tar.gz"
    base = f"https://github.com/gitleaks/gitleaks/releases/download/v{ver}"
    return _scan_job(args, [
        {"name": "Checkout code", "uses": _uses("actions/checkout", args), "with": {"fetch-depth": 0}},
        {"name": "Scan git history for secrets", "run": "\n".join([
            f"curl -sSLfo gitleaks.tar.gz {base}/{tarball}",
            f"curl -sSLfo checksums.txt {base}/gitleaks_{ver}_checksums.txt",
            f"grep ' {tarball}$' checksums.txt | sed 's/ {tarball}/ gitleaks.tar.gz/' | sha256sum -c -",
            "tar -xzf gitleaks.tar.gz gitleaks",
            "./gitleaks git --redact --no-banner --verbose"])},
    ])


def _semgrep_job(args, values):
    return _scan_job(args, [
        _checkout_step(args),
        {"name": "Set up Python", "uses": _uses("actions/setup-python", args),
         "with": {"python-version": values.get("python_version", "3.12")}},
        {"name": "Run Semgrep", "run": "\n".join([
            f"pip install semgrep=={SEMGREP_VERSION}",
            "semgrep scan --config p/default --severity ERROR --error --metrics=off"])},
    ])


def _trivy_job(args):
    return _scan_job(args, [
        _checkout_step(args),
        {"name": "Scan dependencies and config with Trivy",
         "uses": _uses("aquasecurity/trivy-action", args),
         "with": {"scan-type": "fs", "scan-ref": ".", "severity": "CRITICAL,HIGH",
                  "ignore-unfixed": True, "exit-code": "1"}},
    ])


def _checkov_job(args, values):
    return _scan_job(args, [
        _checkout_step(args),
        {"name": "Set up Python", "uses": _uses("actions/setup-python", args),
         "with": {"python-version": values.get("python_version", "3.12")}},
        {"name": "Scan infrastructure as code with Checkov", "run": "\n".join([
            f"pip install checkov=={CHECKOV_VERSION}",
            "checkov --directory . --compact --quiet"])},
    ])


def _codeql_job(args, configs):
    include = [{"language": lang, "build-mode": mode}
               for key, (lang, mode) in CODEQL_LANGUAGES.items() if configs["languages"].get(key)]
    if not include:
        raise ValueError("codeql needs at least one supported language: "
                         + ", ".join(sorted(CODEQL_LANGUAGES)))
    return _scan_job(
        args,
        [_checkout_step(args),
         {"name": "Initialize CodeQL", "uses": _uses("github/codeql-action/init", args),
          "with": {"languages": "${{ matrix.language }}", "build-mode": "${{ matrix.build-mode }}"}},
         {"name": "Analyze", "uses": _uses("github/codeql-action/analyze", args),
          "with": {"category": "/language:${{ matrix.language }}"}}],
        permissions={"contents": "read", "security-events": "write", "actions": "read"},
        strategy={"fail-fast": False, "matrix": {"include": include}},
    )


def _security_jobs(args, values, configs):
    """Scan jobs for ``args.security_scans`` (name -> job), in a stable order."""
    wanted = parse_security_scans(getattr(args, "security_scans", ""))
    builders = {
        "gitleaks": lambda: _gitleaks_job(args),
        "semgrep": lambda: _semgrep_job(args, values),
        "trivy": lambda: _trivy_job(args),
        "checkov": lambda: _checkov_job(args, values),
        "codeql": lambda: _codeql_job(args, configs),
    }
    return {name: builders[name]() for name in SECURITY_SCANS if name in wanted}

# ---------------------------------------------------------------------------
# Workflow generators
# ---------------------------------------------------------------------------

def generate_build_workflow(args, values, configs):
    """Generate a build workflow."""
    jobs = {"build": _new_job(args, values, _build_steps(args, values, configs))}
    jobs.update(_security_jobs(args, values, configs))
    return _workflow(f"{args.name} Build", _triggers(args), jobs, _RUN_ON_PR_ONLY)


def generate_test_workflow(args, values, configs):
    """Generate a test workflow."""
    jobs = {"test": _new_job(args, values, _test_steps(args, values, configs))}
    jobs.update(_security_jobs(args, values, configs))
    return _workflow(f"{args.name} Test", _triggers(args), jobs, _RUN_ON_PR_ONLY)


def generate_deploy_workflow(args, values, configs):
    """Generate a deployment workflow."""
    jobs = {"deploy": _deploy_job(args, values)}
    # Never cancel a deployment part-way through.
    return _workflow(f"{args.name} Deploy",
                     _triggers(args, pull_request=False, environment_input=True), jobs, False)


def generate_complete_workflow(args, values, configs):
    """Generate a complete CI/CD workflow."""
    scans = _security_jobs(args, values, configs)
    jobs = {
        "build": _new_job(args, values, _build_steps(args, values, configs)),
        "test": _new_job(args, values, _test_steps(args, values, configs), needs=["build"]),
        **scans,
        # Deployment is gated on every selected scan as well as the tests.
        "deploy": _deploy_job(args, values, needs=["test", *scans],
                              condition="github.ref == 'refs/heads/main'"),
    }
    # Cancel superseded PR runs only; a push to main (which deploys) is never cancelled.
    return _workflow(f"{args.name} CI/CD", _triggers(args, environment_input=True),
                     jobs, _RUN_ON_PR_ONLY)


def generate_security_workflow(args, values, configs):
    """Generate a workflow containing only security scans (default: gitleaks, semgrep, trivy)."""
    if not parse_security_scans(getattr(args, "security_scans", "")):
        args.security_scans = DEFAULT_SECURITY_SCANS
    jobs = _security_jobs(args, values, configs)
    return _workflow(f"{args.name} Security", _triggers(args), jobs, _RUN_ON_PR_ONLY)


def generate_reusable_workflow(args, values, configs):
    """Generate a reusable workflow that can be called from other workflows.

    Supports the Docker/Kubernetes deploy only; ``deploy_target`` is not used here.

    No ``concurrency:`` block is emitted: a called workflow shares its caller's
    concurrency group, so declaring the same group here would cancel the run itself.
    Inputs reach ``run:`` steps through ``env:`` rather than direct ``${{ }}``
    interpolation, which avoids script injection from caller-supplied values.
    """
    config_env = {
        "LANGUAGES": "${{ inputs.languages }}",
        "K8S_DEPLOY": "${{ inputs.kubernetes_deploy }}",
        "K8S_METHOD": "${{ inputs.k8s_method }}",
        "TARGET_ENV": "${{ inputs.environment }}",
    }
    needs_install = not _container_image(args, values)
    deploy_steps = [
        _checkout_step(args),
        {"name": "Parse input configurations", "id": "config", "env": config_env,
         "run": "\n".join([
             "{",
             "  echo \"languages=$LANGUAGES\"",
             "  echo \"k8s_deploy=$K8S_DEPLOY\"",
             "  echo \"k8s_method=$K8S_METHOD\"",
             "  echo \"env=$TARGET_ENV\"",
             "} >> \"$GITHUB_OUTPUT\""])},
        _docker_push_step(args, "registry_token"),
    ]
    k8s_cond = "github.ref == 'refs/heads/main' && steps.config.outputs.k8s_deploy == 'true'"
    if needs_install:
        deploy_steps.append({**_argocd_install_step(),
                             "if": f"{k8s_cond} && steps.config.outputs.k8s_method == 'argocd'"})
        deploy_steps.append({**_flux_install_step(args),
                             "if": f"{k8s_cond} && steps.config.outputs.k8s_method == 'flux'"})
    deploy_steps.append({
        "name": "Deploy to Kubernetes",
        "if": k8s_cond,
        "env": {"KUBECONFIG_DATA": "${{ secrets.kubeconfig }}",
                "K8S_METHOD": "${{ steps.config.outputs.k8s_method }}",
                "TARGET_ENV": "${{ steps.config.outputs.env }}",
                "ARGOCD_SERVER": "${{ secrets.ARGOCD_SERVER }}",
                "ARGOCD_USERNAME": "${{ secrets.ARGOCD_USERNAME }}",
                "ARGOCD_PASSWORD": "${{ secrets.ARGOCD_PASSWORD }}"},
        "run": "\n".join([
            *_KUBECONFIG_RUN,
            "if [[ \"$K8S_METHOD\" == \"kubectl\" ]]; then",
            "  kubectl apply -f ./k8s/deployment.yaml",
            "  kubectl apply -f ./k8s/service.yaml",
            "  kubectl rollout status deployment/my-app",
            "elif [[ \"$K8S_METHOD\" == \"kustomize\" ]]; then",
            "  kubectl apply -k \"./k8s/overlays/$TARGET_ENV\"",
            "  kubectl rollout status deployment/my-app",
            "elif [[ \"$K8S_METHOD\" == \"argocd\" ]]; then",
            "  argocd login \"$ARGOCD_SERVER\" --username \"$ARGOCD_USERNAME\" --password \"$ARGOCD_PASSWORD\" --insecure",
            "  argocd app sync my-application",
            "  argocd app wait my-application --health",
            "elif [[ \"$K8S_METHOD\" == \"flux\" ]]; then",
            "  flux reconcile source git flux-system",
            "  flux reconcile kustomization flux-system",
            "fi"]),
    })
    jobs = {
        "build": _new_job(args, values, _build_steps(args, values, configs)),
        "test": _new_job(args, values, _test_steps(args, values, configs), needs=["build"]),
        "deploy": _new_job(args, values, deploy_steps, needs=["test"],
                           condition="github.ref == 'refs/heads/main'"),
    }
    return {
        "name": f"{args.name} Reusable Workflow",
        "on": {"workflow_call": {
            "inputs": {
                "environment": {"description": "Environment to deploy to", "required": False,
                                "default": "dev", "type": "string"},
                "languages": {"description": "JSON string of languages to enable", "required": False,
                              "default": json.dumps(configs["languages"]), "type": "string"},
                "kubernetes_deploy": {"description": "Whether to deploy to Kubernetes", "required": False,
                                      "default": args.kubernetes, "type": "boolean"},
                "k8s_method": {"description": "Kubernetes deployment method", "required": False,
                               "default": args.k8s_method, "type": "string"},
            },
            "secrets": {
                "registry_token": {"description": "Token for container registry", "required": False},
                "kubeconfig": {"description": "Kubernetes configuration", "required": False},
                "ARGOCD_SERVER": {"description": "ArgoCD server (argocd method)", "required": False},
                "ARGOCD_USERNAME": {"description": "ArgoCD username (argocd method)", "required": False},
                "ARGOCD_PASSWORD": {"description": "ArgoCD password (argocd method)", "required": False},
            },
        }},
        "permissions": {"contents": "read"},
        "jobs": jobs,
    }

def generate_workflow(args, values, configs):
    """Generate the requested workflow type."""
    if args.type == "build":
        return generate_build_workflow(args, values, configs)
    elif args.type == "test":
        return generate_test_workflow(args, values, configs)
    elif args.type == "deploy":
        return generate_deploy_workflow(args, values, configs)
    elif args.type == "complete":
        return generate_complete_workflow(args, values, configs)
    elif args.type == "security":
        return generate_security_workflow(args, values, configs)
    elif args.type == "reusable" or args.reusable:
        return generate_reusable_workflow(args, values, configs)
    else:
        raise ValueError(
            f"Unknown workflow type '{args.type}'. Valid types: {WORKFLOW_TYPES}"
        )

def main():
    """Main function."""
    args = parse_arguments()
    output_dir = create_directory_structure(args.output)
    custom_values = load_custom_values(args.custom_values)
    env_config = load_env_config(args.env_file)
    
    # Generate configuration objects
    configs = {
        "languages": generate_language_config(args.languages, env_config),
        "kubernetes": generate_kubernetes_config(args.kubernetes, args.k8s_method, env_config),
        "cicd": generate_cicd_config(env_config),
        "build_tools": generate_build_tools_config(env_config),
        "code_analysis": generate_code_analysis_config(env_config),
        "devops_tools": generate_devops_tools_config(env_config)
    }
    
    # Generate workflow filename
    filename = f"{args.name.lower().replace(' ', '-')}-{args.type}.yml"
    filepath = os.path.join(output_dir, filename)
    
    # Generate workflow content
    workflow_content = generate_workflow(args, custom_values, configs)
    
    # Convert workflow to YAML (use _NoAliasDumper to avoid anchor/alias output)
    yaml_content = dump_workflow(workflow_content, args)
    
    # Write to file
    with open(filepath, 'w') as f:
        f.write(yaml_content)
    
    print(f"GitHub Actions workflow generated: {filepath}")
    print(f"Type: {args.type}")
    print(f"Languages: {args.languages}")
    if args.kubernetes:
        print(f"Kubernetes deployment method: {args.k8s_method}")

if __name__ == "__main__":
    main()
