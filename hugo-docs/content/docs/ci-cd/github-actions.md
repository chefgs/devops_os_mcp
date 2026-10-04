---
title: "GitHub Actions"
weight: 21
---

# GitHub Actions Workflow Generator

The GitHub Actions generator creates YAML workflow files that orchestrate CI/CD processes using GitHub's built-in action system. Jobs run on GitHub-hosted `ubuntu-latest` runners with the official `setup-*` actions; running them in a container image is optional. Every workflow uses current action versions, least-privilege `permissions:` and a `concurrency:` group.

You can generate these through your AI assistant (the `generate_github_actions_workflow` tool — see [What You Can Do]({{< relref "/docs/getting-started/what-you-can-do" >}})) or with the CLI options below.

---

## Basic Usage

```bash
python -m cli.devopsos scaffold gha --name "my-app" --type complete
```

**Output:** `.github/workflows/my-app-complete.yml`

The filename pattern is `<name-hyphenated>-<type>.yml` inside the output directory.  
Change the output directory with `--output <dir>` (default: `.github/workflows/`).

---

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--name NAME` | `DevOps-OS` | Workflow name |
| `--type TYPE` | `complete` | `build` \| `test` \| `deploy` \| `complete` \| `reusable` \| `security` |
| `--languages LANGS` | `python,javascript` | Comma-separated: `python`, `java`, `javascript`, `go` |
| `--kubernetes` | off | Include Kubernetes deployment steps |
| `--registry URL` | `ghcr.io` | Container registry URL |
| `--k8s-method METHOD` | `kubectl` | `kubectl` \| `kustomize` \| `argocd` \| `flux` |
| `--output DIR` | `.github/workflows` | Output directory |
| `--custom-values FILE` | _(none)_ | Path to custom values JSON file |
| `--image IMAGE` | _(none)_ | Optional container image to run jobs in. Default: jobs run directly on `ubuntu-latest` |
| `--deploy-target TARGET` | _(none)_ | Deploy to a hosting platform instead of Docker/Kubernetes: `vercel` \| `cloudflare-workers` \| `cloudflare-pages` \| `netlify` \| `render` \| `github-pages` |
| `--build-output-dir DIR` | `dist` | Build output directory for static hosting targets |
| `--security-scans LIST` | _(none)_ | Comma-separated: `gitleaks`, `semgrep`, `trivy`, `checkov`, `codeql` |
| `--pin-actions` | off | Pin actions to full commit SHAs with a version comment |
| `--branches BRANCHES` | `main` | Comma-separated branches that trigger the workflow |
| `--matrix` | off | Enable matrix builds across OS/architectures |
| `--env-file FILE` | _(cli dir)_ | Path to `devcontainer.env.json` |
| `--reusable` | off | Generate a reusable workflow |

---

## Workflow Types

| Type | Description |
|------|-------------|
| `build` | Focuses on building and packaging your application |
| `test` | Focuses on running tests |
| `deploy` | Focuses on deploying to the target environment |
| `complete` | Combines build, test, and deploy stages |
| `reusable` | Creates a workflow callable from other workflows |
| `security` | Security scans only (defaults to `gitleaks,semgrep,trivy`); also addable to `build`, `test` and `complete` with `--security-scans` |

---

## Examples

### Python application — complete pipeline

```bash
python -m cli.devopsos scaffold gha --name "Python App" --languages python --type complete
# Output: .github/workflows/python-app-complete.yml
```

### Java with Maven

```bash
python -m cli.devopsos scaffold gha --name "Java Service" --languages java --custom-values maven-config.json
# Output: .github/workflows/java-service-complete.yml
```

### Multi-language microservices with Kubernetes

```bash
python -m cli.devopsos scaffold gha \
  --name "Microservices" \
  --languages python,javascript,go \
  --kubernetes --k8s-method kustomize
# Output: .github/workflows/microservices-complete.yml
```

### Matrix build (cross-platform)

```bash
python -m cli.devopsos scaffold gha --name "Node.js App" --languages javascript --matrix
# Output: .github/workflows/node-js-app-complete.yml
```

### Reusable workflow

```bash
python -m cli.devopsos scaffold gha --name "shared" --type reusable
# Output: .github/workflows/shared-reusable.yml
```

---

## Environment Variables

All options can be set using environment variables prefixed with `DEVOPS_OS_GHA_`:

```bash
export DEVOPS_OS_GHA_NAME="API Service"
export DEVOPS_OS_GHA_TYPE="complete"
export DEVOPS_OS_GHA_LANGUAGES="python,go"
export DEVOPS_OS_GHA_KUBERNETES="true"
export DEVOPS_OS_GHA_K8S_METHOD="kustomize"
export DEVOPS_OS_GHA_MATRIX="true"

python -m cli.devopsos scaffold gha
# Output: .github/workflows/api-service-complete.yml
```

---

## Kubernetes Deployment Methods

| Method | What happens |
|--------|-------------|
| `kubectl` | Direct deployment using `kubectl set image` and rollout status |
| `kustomize` | `kustomize edit set image` + `kubectl apply -k` |
| `argocd` | `argocd app set` + sync + wait |
| `flux` | `flux reconcile` + kustomization reconcile |

---

## Reusable Workflows

Call the generated reusable workflow from another workflow:

```yaml
jobs:
  call-devops-os-workflow:
    uses: ./.github/workflows/shared-reusable.yml
    with:
      languages: '{"python": true, "java": true}'
      deploy_environment: 'production'
```

---

## Custom Values File

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
    "parallel": 4
  },
  "deploy": {
    "environments": ["dev", "staging", "prod"],
    "approval_required": true,
    "rollback_enabled": true
  },
  "matrix": {
    "os": ["ubuntu-latest", "windows-latest", "macos-latest"],
    "architecture": ["x86_64", "arm64"]
  }
}
```

```bash
python -m cli.devopsos scaffold gha --custom-values advanced-config.json
```

---

## Deploy Targets

By default the deploy job builds and pushes a Docker image (skipped if the repo has no `Dockerfile`) and deploys to Kubernetes if enabled. Set `--deploy-target` to deploy to a hosting platform instead. It applies to the `deploy` and `complete` types and cannot be combined with Kubernetes.

| Target | Mechanism | Repository secrets |
|---|---|---|
| `vercel` | Vercel CLI (`pull`, `build --prod`, `deploy --prebuilt --prod`), version pinned | `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` |
| `cloudflare-workers` | `cloudflare/wrangler-action` (`deploy`) | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| `cloudflare-pages` | `cloudflare/wrangler-action` (`pages deploy <dir>`, project name = app name) | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` |
| `netlify` | Netlify CLI (`deploy --prod --dir`), version pinned | `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` |
| `render` | POST to the service's deploy hook | `RENDER_DEPLOY_HOOK_URL` |
| `github-pages` | `configure-pages`, `upload-pages-artifact`, `deploy-pages` (enable Pages with source "GitHub Actions") | none |

The generated file starts with a comment listing the secrets to create (names only). Targets other than `render` build with `npm ci` and `npm run build`, so they assume a Node project; set `--build-output-dir` to match your framework. Deploys run only from `main`.

> **These are scaffolds, not tested integrations.** They are linted and their scripts are tested against stub commands, but they have not been run against live hosting accounts. Review the job and try it on a non-production project first. The `generate_deploy_preflight` tool gives you commands to test your setup locally.

## Security Scans

`--security-scans` adds each selected scan as its own job. In a `complete` workflow, deployment waits for all of them. Each fails the job on findings.

| Scan | Covers | Notes |
|---|---|---|
| `gitleaks` | secrets in git history | CLI downloaded from the release and checksum-verified; full-history checkout. Allowlist test fixtures with a `.gitleaks.toml`. |
| `semgrep` | static analysis | `p/default` rules, fails on ERROR severity, telemetry off |
| `trivy` | dependency and config vulnerabilities | CRITICAL/HIGH with a fix available |
| `checkov` | infrastructure as code | fails on any failed check; expect findings on first run |
| `codeql` | static analysis (GitHub) | per-language matrix; needs code scanning enabled (GitHub Advanced Security for private repos) |

Scan jobs always run on the runner, ignoring `--image` and `--matrix`.

---

## Generated Workflow Structure

```yaml
name: My CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7   # one setup action per selected language
      # Language-specific build steps...

  test:
    needs: [build]
    # ...

  deploy:
    needs: [test]              # plus any selected security scans
    if: github.ref == 'refs/heads/main'
    # ...
```

---

## Best Practices

1. Start with `--type complete` and remove stages you don't need
2. Use `--pin-actions` for supply-chain hardening, and let Dependabot (`generate_dependabot_config`) keep the pinned versions current
3. Use `--env-file` to align CI/CD with your local dev container
4. Use reusable workflows to standardize pipelines across multiple repos
5. Store secrets in GitHub Secrets, reference them with `${{ secrets.MY_SECRET }}`
