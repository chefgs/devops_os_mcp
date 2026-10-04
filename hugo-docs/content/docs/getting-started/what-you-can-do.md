---
title: "What You Can Do"
weight: 5
---

# What You Can Do with DevOps-OS MCP

DevOps-OS MCP gives your AI assistant (Claude, ChatGPT, Cursor, Copilot and other MCP clients) the ability to **look at your project, tell you what automation it is missing, and generate the files to add it** — one small, reviewable step at a time.

It is an **advisor and generator**. It never deploys anything, never runs commands on your behalf, and never needs your passwords or tokens. Everything it produces is a normal file in your repository that you review, commit, and can delete.

---

## The recommended flow

Start with a scan, not with a config. You get advice that fits your project instead of a generic template that may replace something that already works.

| Step | What happens | Tool |
|------|--------------|------|
| **1. Scan** | Reads your repo: stack, frameworks, package manager, hosting config, existing CI, dependency updates | `analyze_repo` |
| **2. Audit** (if you already have CI) | Checks an existing workflow for what it covers, what is missing, and hardening problems. Never rewrites it | `audit_github_workflow` |
| **3. Choose** | Your assistant explains the result in plain language and proposes 2–4 next steps. You pick | — |
| **4. Generate** | Creates only what you chose, as separate files | `generate_*` tools |
| **5. Verify** | Gives you commands to test your hosting setup on your own machine, with your own credentials | `generate_deploy_preflight` |

The fastest way to begin is the **`start`** prompt. In clients that show MCP prompts, choose *Start here: scan my repo*. In any client you can simply ask:

> *Scan my repo at ~/projects/shop and tell me how DevOps-OS can help.*

The server also tells your assistant to work this way, but an assistant may not always follow server guidance. If it jumps straight to generating, ask it to scan first.

---

## Example: a project that already has CI

> **You:** Scan ~/projects/shop and tell me what DevOps-OS can do for it.
>
> **Assistant:** *(calls `analyze_repo`)* Shop is a Vite + React app deployed on Vercel, with one CI workflow that runs tests. I did not find a secrets scan, static analysis, or automatic dependency updates. Three small steps, cheapest first:
> 1. Add Dependabot (a config file; update PRs then arrive on their own).
> 2. Add a separate security workflow with Gitleaks, Semgrep and Trivy. Your existing CI is untouched.
> 3. Add a Vercel deploy workflow (needs three repository secrets).
>
> Which would you like?
>
> **You:** 1 and 2.
>
> **Assistant:** *(calls `generate_dependabot_config` and `generate_github_actions_workflow` with `workflow_type="security"`)* Here is `.github/dependabot.yml` and a separate security workflow file to add next to your existing CI...

## Example: a new app that should deploy to a hosting platform

> **You:** Generate a workflow that tests my Vite app and deploys it to Netlify.
>
> **Assistant:** *(calls `generate_github_actions_workflow` with `deploy_target="netlify"`)* The workflow is below. Create the repository secrets `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` before the first run. Want a checklist to test your Netlify setup locally first?
>
> **You:** Yes.
>
> **Assistant:** *(calls `generate_deploy_preflight`)* Run these in order from your repo root. The first two only read; the last publishes a **draft** deploy, so point it at a test site...

## Example: a monorepo

`analyze_repo` also checks the immediate subdirectories, so a `frontend/` + `backend/` layout is detected (for example React/Vite and FastAPI) and you get one Dependabot suggestion per directory. Generated build and test steps run at the repository root, so add `working-directory:` to them for subdirectory projects.

---

## Everything you can ask for

### Understand your project
| Tool | What you get |
|------|--------------|
| `analyze_repo` | Detected stack, hosting target, existing workflows with their gaps, a one-sentence summary, and recommended next calls with ready-to-use arguments |
| `audit_github_workflow` | For a workflow you paste in: capabilities covered (lint, test, build, secrets-scan, sast, dependency-scan, iac-scan, deploy), what is missing, and findings such as no `permissions:` block, deprecated artifact actions, floating `@main` refs, script injection, placeholder container images |

### Create pipelines
| Tool | What you get |
|------|--------------|
| `generate_github_actions_workflow` | GitHub Actions workflow: build, test, deploy, complete, reusable, or security-scans-only |
| `generate_gitlab_ci_pipeline` | GitLab CI pipeline |
| `generate_jenkins_pipeline` | Jenkins declarative pipeline |
| `generate_unittest_config` | Unit-test scaffolding for your language |

### Deploy and run
| Tool | What you get |
|------|--------------|
| `generate_k8s_config` | Kubernetes Deployment and Service manifests |
| `generate_argocd_config` | Argo CD / Flux GitOps configuration |
| `generate_sre_configs` | Prometheus alert rules, Grafana dashboard, SLO manifest |
| `generate_deploy_preflight` | A local test plan for a hosting target (see below) |

### Keep it secure and current
| Tool | What you get |
|------|--------------|
| `generate_dependabot_config` | `.github/dependabot.yml` for your ecosystems, always including GitHub Actions; minor and patch updates grouped into one PR |
| `check_security_issues` | Security status of the **tool versions** DevOps-OS manages (not your project's own dependencies — use Dependabot or a scan for those) |
| `get_version_config`, `check_version_updates`, `suggest_versions`, `update_versions` | Look up, check, and update the tool versions used in dev containers (`update_versions` is the only tool that changes server state) |

### Set up your workstation
| Tool | What you get |
|------|--------------|
| `scaffold_devcontainer` | `devcontainer.json` and `devcontainer.env.json` for your languages and tools |

---

## What the GitHub Actions generator can do

| Option | Effect |
|--------|--------|
| `workflow_type` | `build`, `test`, `deploy`, `complete`, `reusable`, or `security` (scans only) |
| `languages` | Python, JavaScript, Go, Java, Rust — each gets build and test steps, with the official `setup-*` action where one is needed (Rust uses the runner's preinstalled cargo) |
| `deploy_target` | `vercel`, `cloudflare-workers`, `cloudflare-pages`, `netlify`, `render`, `github-pages`. Default is a Docker image push, plus Kubernetes if enabled |
| `build_output_dir` | Build output directory for static targets (`dist`, `build`, `out`) |
| `security_scans` | Any of `gitleaks`, `semgrep`, `trivy`, `checkov`, `codeql` as jobs. In a `complete` workflow, deployment waits for them |
| `pin_actions` | Pin every action to a full commit SHA with a version comment |
| `container_image` | Run jobs in a container. Off by default: jobs run on `ubuntu-latest` |
| `kubernetes`, `k8s_method` | Add a Kubernetes deploy stage: `kubectl`, `kustomize`, `argocd` or `flux` (an unknown method is rejected) |

Every workflow gets least-privilege `permissions: contents: read`, and all but reusable workflows get a `concurrency:` group (pull-request runs cancel superseded runs; deploys are never cancelled; a reusable workflow shares its caller's group). The generated file starts with a comment listing the repository secrets you need to create.

### Testing a deploy target on your machine

`generate_deploy_preflight` returns the secret names, a `.env.deploy` template containing placeholders only, and ordered commands, each labelled:

- **read-only** — checks your identity or settings; changes nothing.
- **local-build** — builds or writes files on your machine only.
- **publishes** — changes the hosting platform (a preview or draft deploy, never production). Use a test project.

You, or your assistant with your approval, run the commands with tokens from your own shell. **Do not paste tokens into the chat.** GitHub Pages deploys use GitHub's own token and cannot run locally, so only the prerequisites and the build are checked.

---

## What it does not do

- **It does not deploy, run commands, or touch your infrastructure.** It returns text. You apply it.
- **It never asks for credentials.** Tokens stay in your shell or repository secrets.
- **Deploy targets are scaffolding.** The workflows are linted, the scripts are tested against stub commands, and the CLI flags are checked against the real tools — but they have **not been run against live Vercel, Cloudflare, Netlify, Render or Pages accounts**. Review the job and try it on a non-production project first.
- **Detection is heuristic.** It recognises well-known files and commands. Read "missing" as "not detected" and check the finding before acting on it.
- **JavaScript steps use `npm ci`.** For pnpm, yarn or bun projects, `analyze_repo` tells you to swap in your package manager's install command.
- **Existing pipelines are never replaced.** Missing pieces are suggested as separate files.

## Local and remote servers

| | Local (stdio, default) | Remote (HTTP with authentication) |
|--|------------------------|-----------------------------------|
| `analyze_repo` | Available — reads a directory on your machine | **Disabled.** A remote server must not read its own filesystem on your behalf |
| `audit_github_workflow` | Available | Available — paste the file contents |
| Generators and `generate_deploy_preflight` | Available | Available |

With a remote server, paste your workflow files and use `audit_github_workflow`; the assistant can still recommend steps from what you share.

---

## Next steps

- [MCP Quick Start]({{< relref "/docs/getting-started/mcp-quickstart" >}}) — install and connect your assistant
- [GitHub Actions]({{< relref "/docs/ci-cd/github-actions" >}}) — all workflow options in detail
- [AI Integration]({{< relref "/docs/ai-integration" >}}) — every tool and the `start` prompt
