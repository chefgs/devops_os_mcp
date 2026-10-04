# Creating Customized GitHub Actions Templates

This guide covers how to create and customize GitHub Actions workflow templates using DevOps-OS tooling. The GitHub Actions generator helps you create workflows that integrate with your development environment and deployment needs.

## Table of Contents

- [Understanding the GitHub Actions Generator](#understanding-the-github-actions-generator)
- [Basic Usage](#basic-usage)
- [Workflow Types](#workflow-types)
- [Customization Options](#customization-options)
- [Matrix Builds](#matrix-builds)
- [Kubernetes Integration](#kubernetes-integration)
- [Reusable Workflows](#reusable-workflows)
- [Environment Variables](#environment-variables)
- [Advanced Customization](#advanced-customization)
- [Examples](#examples)

## Understanding the GitHub Actions Generator

The GitHub Actions generator (`github-actions-generator-improved.py`) creates YAML workflow files that orchestrate continuous integration and deployment processes using GitHub's action system. By default the jobs run directly on GitHub-hosted `ubuntu-latest` runners and use the official `setup-*` actions for toolchains. Running jobs in a container image is optional (`--image` on the CLI, `container_image` on the MCP tool).

## Basic Usage

To generate a basic GitHub Actions workflow:

```bash
python -m cli.scaffold_gha --name "My Workflow" --type complete
```

This generates a complete CI/CD workflow including build, test, and deploy stages.

**Output:** `.github/workflows/my-workflow-complete.yml`

The filename is built as `<name-lowercased-and-hyphenated>-<type>.yml` inside the output directory.  
Change the output directory with `--output <dir>` (default: `.github/workflows/`).

## Workflow Types

The generator supports several types of workflows:

1. **Build Workflow** (`--type build`): Focuses on building and packaging your application.
2. **Test Workflow** (`--type test`): Focuses on running tests and validating your application.
3. **Deploy Workflow** (`--type deploy`): Focuses on deploying your application to the target environment.
4. **Complete Workflow** (`--type complete`): Combines build, test, and deploy stages.
5. **Reusable Workflow** (`--type reusable` or `--reusable`): Creates a reusable workflow that can be called from other workflows.

## Customization Options

### Basic Options

- `--name`: The name of the workflow (e.g., "Backend CI/CD")
- `--languages`: Comma-separated list of languages to enable (e.g., "python,java,javascript,go")
- `--output`: Output directory for the generated workflow file

### Example with Basic Options

```bash
python -m cli.scaffold_gha --name "Python API" --languages python --output ./.github/workflows
```

**Output:** `.github/workflows/python-api-complete.yml`

## Matrix Builds

Matrix builds allow you to run your workflows across multiple configurations, such as different operating systems or language versions:

```bash
python -m cli.scaffold_gha --matrix
```

**Output:** `.github/workflows/devops-os-complete.yml`

This creates a workflow with a matrix strategy that runs on multiple platforms.

### Custom Matrix Configuration

For more advanced matrix configurations, you can provide a custom values file:

```json
{
  "matrix": {
    "os": ["ubuntu-latest", "windows-latest", "macos-latest"],
    "python-version": ["3.8", "3.9", "3.10", "3.11"],
    "exclude": [
      {
        "os": "windows-latest",
        "python-version": "3.11"
      }
    ]
  }
}
```

```bash
python -m cli.scaffold_gha --custom-values matrix-config.json
```

## Kubernetes Integration

To include Kubernetes deployment steps in your workflow:

```bash
python -m cli.scaffold_gha --kubernetes --k8s-method kubectl
```

### Kubernetes Deployment Methods

Four Kubernetes deployment methods are supported:

1. **kubectl** (`--k8s-method kubectl`): Direct deployment using kubectl commands.
2. **kustomize** (`--k8s-method kustomize`): Deployment using Kustomize for environment-specific configurations.
3. **argocd** (`--k8s-method argocd`): GitOps deployment using ArgoCD.
4. **flux** (`--k8s-method flux`): GitOps deployment using Flux CD.

## Reusable Workflows

Reusable workflows can be called from other workflows, making them ideal for creating standardized CI/CD templates:

```bash
python -m cli.scaffold_gha --type reusable
```

**Output:** `.github/workflows/devops-os-reusable.yml`

### Using a Reusable Workflow

The generated reusable workflow can be called from another workflow:

```yaml
jobs:
  call-devops-os-workflow:
    uses: ./.github/workflows/devops-os-reusable.yml
    with:
      languages: '{"python": true, "java": true}'
      deploy_environment: 'production'
```

## Environment Variables

All options can be set using environment variables prefixed with `DEVOPS_OS_GHA_`:

```bash
export DEVOPS_OS_GHA_NAME="API Service"
export DEVOPS_OS_GHA_TYPE="complete"
export DEVOPS_OS_GHA_LANGUAGES="python,go"
export DEVOPS_OS_GHA_KUBERNETES="true"
export DEVOPS_OS_GHA_K8S_METHOD="kustomize"
export DEVOPS_OS_GHA_MATRIX="true"

python -m cli.scaffold_gha
# Output: .github/workflows/api-service-complete.yml
```

## Advanced Customization

### Custom Values File

For advanced customization, create a custom values JSON file:

```json
{
  "build": {
    "cache": true,
    "timeout_minutes": 30,
    "artifact_paths": ["dist/**", "build/**"]
  },
  "test": {
    "coverage": true,
    "junit_reports": true,
    "parallel": 4,
    "timeout_minutes": 20
  },
  "deploy": {
    "environments": ["dev", "staging", "prod"],
    "approval_required": true,
    "rollback_enabled": true
  },
  "notifications": {
    "slack": {
      "channel": "deployments",
      "success": true,
      "failure": true
    },
    "email": {
      "recipients": ["team@example.com"],
      "on_failure_only": true
    }
  }
}
```

```bash
python -m cli.scaffold_gha --custom-values advanced-config.json
```

### Integration with DevOps-OS Configuration

The generator integrates with the DevOps-OS `devcontainer.env.json` file to ensure consistency between your development environment and CI/CD workflows:

```bash
python -m cli.scaffold_gha --env-file ./devcontainer.env.json
```

## Examples

### Basic Python Application Workflow

```bash
python -m cli.scaffold_gha --name "Python App" --languages python --type complete
# Output: .github/workflows/python-app-complete.yml
```

### Java Application with Maven

```bash
python -m cli.scaffold_gha --name "Java Service" --languages java --custom-values maven-config.json
# Output: .github/workflows/java-service-complete.yml
```

### Multi-language Microservices

```bash
python -m cli.scaffold_gha --name "Microservices" --languages python,javascript,go --kubernetes --k8s-method kustomize
# Output: .github/workflows/microservices-complete.yml
```

### Cross-platform Node.js Application

```bash
python -m cli.scaffold_gha --name "Node.js App" --languages javascript --matrix --custom-values node-matrix.json
# Output: .github/workflows/node-js-app-complete.yml
```

### Complete Docker and Kubernetes Workflow

```bash
python -m cli.scaffold_gha --name "Container Deploy" --languages go --kubernetes --k8s-method argocd --registry ghcr.io
# Output: .github/workflows/container-deploy-complete.yml
```

## Understanding the Generated Workflow

The generated GitHub Actions workflow includes:

1. **Triggers**: Configures when the workflow runs (push, pull request, workflow dispatch).
2. **Jobs**: Defines the jobs to run (build, test, deploy).
3. **Steps**: Details the steps within each job.
4. **Environment**: Runs on `ubuntu-latest` and installs toolchains with `actions/setup-python`, `setup-node`, `setup-go` and `setup-java` (or runs in your own container image if one is given).
5. **Artifacts**: Configures artifact handling for sharing between jobs.
6. **Hardening**: Every workflow declares top-level `permissions: contents: read` and a `concurrency:` group. Superseded pull-request runs are cancelled; pushes to the default branch and deployments never are. Reusable workflows omit `concurrency:` because a called workflow shares its caller's group. Pass `--pin-actions` (CLI) or `pin_actions=true` (MCP) to pin every action to a full commit SHA with a version comment.
7. **Deployments**: Includes deployment steps if Kubernetes is enabled.

### Example Structure

```yaml
name: My CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: Environment to deploy to
        required: true
        default: dev
        type: choice
        options: [dev, test, staging, prod]

permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      # Build steps here
      
  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      # Test steps here
      
  deploy:
    needs: test
    if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      # Deploy steps here
```

## Deploy Targets

By default the deploy job builds and pushes a Docker image (and deploys to Kubernetes if enabled). Set a hosting target to deploy to a platform instead (`--deploy-target` on the CLI, `deploy_target` on the MCP tool). It applies to the `deploy` and `complete` workflow types and cannot be combined with Kubernetes.

| Target | Mechanism | Repository secrets |
|---|---|---|
| `vercel` | Vercel CLI (`pull`, `build --prod`, `deploy --prebuilt --prod`), version pinned | `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` |
| `cloudflare-workers` | `cloudflare/wrangler-action` (`wrangler deploy`) | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| `cloudflare-pages` | `cloudflare/wrangler-action` (`pages deploy <dir>`, project name = app name) | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| `netlify` | Netlify CLI (`deploy --prod --dir`), version pinned | `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` |
| `render` | POST to the service's deploy hook | `RENDER_DEPLOY_HOOK_URL` |
| `github-pages` | `configure-pages`, `upload-pages-artifact`, `deploy-pages` (job gets `pages: write` and `id-token: write`; enable Pages with source "GitHub Actions") | none |

> **Scaffolding, not a tested integration.** The deploy targets generate a starting point. The workflows are linted (actionlint and shellcheck), the scripts are exercised against stub CLIs, and the pinned CLIs and actions are checked for the flags and inputs used, but they have not been run against live Vercel, Cloudflare, Netlify, Render or GitHub Pages accounts. Review the generated job and run it once on a non-production project before relying on it.

Notes:
- The generated file starts with a comment listing the secrets to create; only secret *names* appear, never values.
- Targets other than `render` build with `npm ci` and `npm run build`, so they assume a Node project. Set `build_output_dir` (`--build-output-dir`, default `dist`) to match your framework (`dist`, `build`, `out`).
- Deploys run only from `main`. Set the project up on the platform once (project, site or service) before the first run.

## Security Scans

`--security-scans` (CLI) / `security_scans` (MCP) adds scan jobs: a comma-separated list of `gitleaks`, `semgrep`, `trivy`, `checkov`, `codeql`. Use `workflow_type: security` for a workflow containing only scans (defaults to `gitleaks,semgrep,trivy`); it can also be added to `build`, `test` and `complete`. In a `complete` workflow, deployment waits for every selected scan. Each scan fails the job on findings.

| Scan | Covers | Notes |
|---|---|---|
| `gitleaks` | secrets in git history | CLI downloaded from the release and checksum-verified (the official action needs a paid licence for organisation repos); full-history checkout. Test fixtures that look like keys will be reported; allowlist them with a `.gitleaks.toml` (`[extend] useDefault = true` plus `[allowlist] paths = [...]`, as in this repo) rather than disabling the scan. |
| `semgrep` | SAST | `p/default` rules, fails on ERROR severity, telemetry off |
| `trivy` | dependency and config CVEs | fails on CRITICAL/HIGH with a fix available |
| `checkov` | IaC (Terraform, Dockerfile, Kubernetes) | fails on any failed check, so expect findings on the first run |
| `codeql` | SAST (GitHub) | per-language matrix; needs code scanning enabled (GitHub Advanced Security for private repos); the only job with `security-events: write` |

Scan jobs always run on the runner, ignoring `container_image` and `matrix`.

## Working with an existing pipeline

Adding a generated workflow on top of a repo that already has CI should extend it, not replace it:

1. `analyze_repo(path)` detects the stack (root and immediate subdirectories), hosting config and existing workflows, and returns `recommended_calls` with ready-to-use arguments. It is local-profile only, reads a fixed list of manifest files, returns derived facts rather than file contents, and refuses symlinks that leave the repository.
2. `audit_github_workflow(workflow_yaml)` takes an existing workflow's contents and reports what it covers (lint, test, build, secrets-scan, sast, dependency-scan, iac-scan, deploy), what is missing, and hardening findings (no `permissions:`, deprecated artifact actions, floating `@main` refs, script injection, placeholder containers). It never rewrites the file.
3. Add the missing scans as a **separate** file with `workflow_type: security`, and updates with `generate_dependabot_config`.

Detection is heuristic (it matches commands such as `pytest` or `semgrep`); treat "missing" as "not detected".

## Best Practices

1. **Start Simple**: Begin with a basic workflow and add complexity as needed.
2. **Use Environment Variables**: Use environment variables for secrets and configuration.
3. **Leverage Matrix Builds**: Use matrix builds for testing across multiple configurations.
4. **Use Reusable Workflows**: Create reusable workflows for common patterns.
5. **Custom Values**: Use custom values files for advanced configuration.
6. **Integration with DevOps-OS**: Integrate with your DevOps-OS configuration for consistency.

## Next Steps

- Explore the [Jenkins Pipeline Generator](./JENKINS-PIPELINE-README.md) for creating Jenkins pipelines.
- Learn about [Kubernetes deployments](./KUBERNETES-DEPLOYMENT-README.md) for deploying your applications.
- Implement [CI/CD pipelines for technology stacks](./CICD-TECH-STACK-README.md) specific to your project.
