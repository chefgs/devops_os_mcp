---
title: "Getting Started"
weight: 10
bookCollapseSection: true
---

# Getting Started with DevOps-OS

Welcome! This guide walks you through DevOps-OS from **zero to your first generated pipeline** in under five minutes.

---

## What is DevOps-OS?

DevOps-OS is a toolkit that generates production-ready CI/CD pipelines, Kubernetes manifests, infrastructure hardening baselines, and SRE monitoring configs — so you can stop writing boilerplate and start shipping.

| Category | Tools |
|----------|-------|
| CI/CD | GitHub Actions, GitLab CI, Jenkins |
| GitOps / Deploy | ArgoCD, Flux CD, kubectl, Kustomize |
| Containers | Docker, Helm |
| Hardening / Compliance | Kyverno policies, InSpec profiles, Checkov checks, compliance mappings |
| SRE / Observability | Prometheus alert rules, Grafana dashboards, SLO configs |
| Unit Testing | pytest, Jest, Vitest, Mocha, Go test |
| AI Integration | Claude (MCP Server), OpenAI (function calling) |

---

## Prerequisites

| Requirement | Why |
|------------|-----|
| Python 3.10+ | Runs the CLI generators |
| pip | Installs Python dependencies |
| Git | Clones the repo |
| Docker *(optional)* | Builds / runs the dev container |
| VS Code + Dev Containers extension *(optional)* | Opens the pre-configured dev environment |

---

## 1 — Clone and install

```bash
git clone https://github.com/cloudengine-labs/devops_os.git
cd devops_os
```

**Set up a virtual environment** (strongly recommended):

```bash
python -m venv .venv

# Activate
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (cmd)
# .venv\Scripts\Activate.ps1     # Windows (PowerShell)
```

**Install the CLI dependencies:**

```bash
pip install -r cli/requirements.txt
```

> [!WARNING]
> Run `source .venv/bin/activate` in every new terminal session before using `python -m cli.*` commands.

---

## 2 — Learn the Process-First philosophy *(recommended)*

Before running any generator, understand *why* each tool exists:

```bash
python -m cli.devopsos process-first                    # full overview
python -m cli.devopsos process-first --section what     # 5 core principles
python -m cli.devopsos process-first --section mapping  # which scaffold encodes which principle
python -m cli.devopsos process-first --section tips     # AI prompts for deeper learning
```

See the [Process-First guide]({{< relref "/docs/getting-started/process-first" >}}) for the full reference.

---

## 3 — Generate your first CI/CD pipeline

All scaffold generators are subcommands of the unified `devopsos scaffold` command. Use `--help` on any subcommand to see all options.

### GitHub Actions

```bash
python -m cli.devopsos scaffold gha --name my-app --languages python,javascript --type complete
```

**Output:** `.github/workflows/my-app-complete.yml`

### GitLab CI

```bash
python -m cli.devopsos scaffold gitlab --name my-app --languages python --type complete
```

**Output:** `.gitlab-ci.yml`

### Jenkins

```bash
python -m cli.devopsos scaffold jenkins --name my-app --languages java --type complete
```

**Output:** `Jenkinsfile`

---

## 4 — Generate Kubernetes / GitOps configs

```bash
# ArgoCD Application CR + AppProject
python -m cli.devopsos scaffold argocd --name my-app \
       --repo https://github.com/myorg/my-app.git \
       --namespace production
# Output: argocd/application.yaml + argocd/appproject.yaml

# Flux CD configs
python -m cli.devopsos scaffold argocd --name my-app --method flux \
       --repo https://github.com/myorg/my-app.git
# Output: flux/ directory
```

---

## 5 — Generate infrastructure hardening baselines

```bash
# Kubernetes policy baselines
python -m cli.devopsos scaffold hardening --standard cis-k8s --type kyverno --environment production

# Operating system compliance profiles
python -m cli.devopsos scaffold hardening --standard cis-rhel9 --type inspec
```

**Output:** `hardening/` directory containing Kyverno policies, InSpec profiles, Checkov checks, and a compliance mapping file.

See [Infrastructure Hardening]({{< relref "/docs/platform-engineering/hardening" >}}) for supported standards and validation examples.

---

## 6 — Generate SRE configs

```bash
python -m cli.devopsos scaffold sre --name my-app --team platform
```

**Output:** `sre/` directory containing:
- `alert-rules.yaml` — Prometheus PrometheusRule CR
- `grafana-dashboard.json` — Grafana importable dashboard
- `slo.yaml` — Sloth-compatible SLO manifest
- `alertmanager-config.yaml` — Alertmanager routing stub

---

## 7 — Generate unit test configs

```bash
# Python — generates pytest.ini, conftest.py, and a sample test file
python -m cli.devopsos scaffold unittest --name my-app --languages python

# JavaScript with Jest
python -m cli.devopsos scaffold unittest --name my-app --languages javascript --framework jest

# TypeScript with Vitest
python -m cli.devopsos scaffold unittest --name my-app --languages typescript --framework vitest

# Multi-stack (Python + JavaScript + Go) in one command
python -m cli.devopsos scaffold unittest --name my-platform --languages python,javascript,go
```

See [CLI Reference]({{< relref "/docs/reference" >}}) for all options and output file paths.

---

## 8 — Interactive wizard (all-in-one)

```bash
python -m cli.devopsos init              # interactive project configurator
python -m cli.devopsos scaffold gha      # scaffold GitHub Actions
python -m cli.devopsos scaffold gitlab   # scaffold GitLab CI
python -m cli.devopsos scaffold jenkins  # scaffold Jenkins
python -m cli.devopsos scaffold argocd   # scaffold ArgoCD / Flux
python -m cli.devopsos scaffold hardening # scaffold hardening baselines
python -m cli.devopsos scaffold sre      # scaffold SRE configs
python -m cli.devopsos scaffold cicd     # scaffold GHA + Jenkins in one step
python -m cli.devopsos scaffold unittest # scaffold unit test configs
```

---

## 9 — Use with an AI assistant

### Via MCP (Recommended — Native Integration)

Use DevOps-OS as an **MCP server in Claude Desktop or ChatGPT** for seamless integration.

**For Claude Desktop (5-minute setup):**
```bash
pip install -r mcp_server/requirements.txt
```
Then see **[MCP Quick Start]({{< relref "/docs/getting-started/mcp-quickstart" >}})** for step-by-step instructions.

**For ChatGPT, HTTP endpoints, and production deployment:**
See **[MCP Setup & Configuration]({{< relref "/docs/ai-integration/mcp-setup" >}})** for detailed setup guide.

### Via API (Alternative — Direct API Calls)

Load tools from `skills/` directory and call Claude or OpenAI APIs directly:

---

## 10 — Next steps

| I want to… | Read |
|-----------|------|
| **Use MCP with Claude Desktop** | [MCP Quick Start]({{< relref "/docs/getting-started/mcp-quickstart" >}}) (5 minutes) |
| **Set up MCP for ChatGPT, HTTP, production** | [MCP Setup & Configuration]({{< relref "/docs/ai-integration/mcp-setup" >}}) (detailed) |
| Understand the Process-First philosophy | [Process-First guide]({{< relref "/docs/getting-started/process-first" >}}) |
| See every CLI option and output path | [CLI Reference]({{< relref "/docs/reference" >}}) |
| Generate infrastructure hardening baselines | [Infrastructure Hardening]({{< relref "/docs/platform-engineering/hardening" >}}) |
| Deep-dive GitHub Actions | [GitHub Actions]({{< relref "/docs/ci-cd/github-actions" >}}) |
| Deep-dive GitLab CI | [GitLab CI]({{< relref "/docs/ci-cd/gitlab-ci" >}}) |
| Deep-dive Jenkins | [Jenkins]({{< relref "/docs/ci-cd/jenkins" >}}) |
| Learn ArgoCD integration | [GitOps & ArgoCD]({{< relref "/docs/gitops" >}}) |
| Set up SRE monitoring configs | [SRE Configuration]({{< relref "/docs/sre" >}}) |
| Set up the dev container | [Dev Container]({{< relref "/docs/dev-container" >}}) |
| Explore all AI integration options | [AI Integration Overview]({{< relref "/docs/ai-integration" >}}) |
