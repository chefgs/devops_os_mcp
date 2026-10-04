# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

> **📌 Note:** This is the **DevOps-OS MCP Server** — a separate MCP implementation for AI tool integration. The original DevOps-OS CLI is available at [cloudengine-labs/devops_os](https://github.com/cloudengine-labs/devops_os). Both projects share the same core scaffold modules.

---

## [Unreleased]

### Changed
- **GitHub Actions generator output (affects `generate_github_actions_workflow` and `devops_os.core.scaffold_gha`)**:
  - Jobs now run on `ubuntu-latest` with `actions/setup-python`, `setup-node`, `setup-go` and `setup-java` instead of the non-existent `ghcr.io/yourorg/devops-os:latest` container. A container is now opt-in via `container_image` (`--image` on the CLI). The CLI `--image` default changed from the placeholder to empty.
  - Action versions updated: `checkout@v7`, `setup-python@v7`, `setup-node@v7`, `setup-go@v7`, `setup-java@v6`, `upload-artifact@v7` (v3 is deprecated and fails), `codecov-action@v7`.
  - Every workflow now has top-level `permissions: contents: read` and a `concurrency:` group (PR runs cancel superseded runs; deploys are never cancelled; reusable workflows omit it).
  - Removed placeholder `echo` steps ("Set up build environment", SonarQube) that did nothing.
  - Reusable workflow passes `inputs.*` to scripts through `env:` instead of interpolating them into `run:`, and declares the ArgoCD secrets it uses.
  - ArgoCD (checksum-verified) and Flux CLIs are installed when not running in a container, since `ubuntu-latest` does not include them.
  - `validate_image_reference` now rejects whitespace.
  - The Docker build/push step is skipped when the repository has no `Dockerfile`, instead of failing the deploy job.
- The server now exposes 16 tools (was 13).

### Fixed
- Jenkins generator no longer hard-codes the non-existent `docker.io/yourorg/devops-os:latest` agent image: the default is `agent any`, and a Docker agent is opt-in via `container_image` (`--image` on the CLI). The Jenkins node must provide the toolchains (and Docker for image builds) when no image is given.
- `validate_image_reference` is now an allowlist (letters, digits, `. _ / : @ -`). The old blocklist let quotes and backslashes through, which could break out of the quoted string in a generated Jenkinsfile.
- Generated deploy scripts no longer paste secrets into script text. The registry token and kubeconfig now go through `env:` and `printf`, so a secret containing quotes, newlines or `$(...)` can no longer break or inject into the step (found by running the generated scripts against stub commands, `tests/test_gha_deploy_mock.py`).
- Docker image tags are lower-cased (Docker rejects upper-case repository names, which GitHub owners often have) and use the runner's `$GITHUB_ACTOR` / `$GITHUB_REPOSITORY`.
- ArgoCD login arguments, `$GITHUB_OUTPUT` writes and kustomize overlay paths are quoted (shellcheck clean).
- Python lint step used `pylint **/*.py`, which without `globstar` only matched one directory level; it now lints `git ls-files '*.py'`.
- `scripts/smoke-test.py` used SDK classes that do not exist (`StdioClientTransport`) and had been failing silently behind `continue-on-error`; it now uses `stdio_client` and the CI step is enforced.
- Added `.gitleaks.toml` allowlisting the fake credentials in test fixtures, and `.DS_Store` to `.gitignore`.

### Added
- Guard tests: `tests/test_gha_deploy_mock.py` (runs deploy scripts against stubs), `tests/test_gha_lint.py` (actionlint + shellcheck over a generated matrix) and `tests/test_action_pins_live.py` (verifies pinned SHAs and emitted `with:` inputs against GitHub; skipped without an authenticated `gh`).
- `security_scans` option (`--security-scans`) and `security` workflow type for `generate_github_actions_workflow`: `gitleaks`, `semgrep`, `trivy`, `checkov`, `codeql` as jobs; `complete` deployments wait for them. Scanner versions are pinned and the Gitleaks download is checksum-verified.
- New tool `generate_dependabot_config`: `.github/dependabot.yml` for chosen ecosystems (language aliases accepted), always including `github-actions`, with minor/patch updates grouped.
- New tool `audit_github_workflow`: reports capabilities covered/missing and hardening findings for an existing workflow, without modifying it.
- New tool `analyze_repo`: detects stack, frameworks, package manager, hosting target and existing workflows (root plus immediate subdirectories) and returns recommended tool calls. Local profile only; fixed file list, size-capped, symlink-safe, returns no file contents.
- Rust is now handled by the GitHub Actions generator (`cargo build`/`cargo test`).
- `deploy_target` (`--deploy-target`) and `build_output_dir` options for `generate_github_actions_workflow`: `vercel`, `cloudflare-workers`, `cloudflare-pages`, `netlify`, `render`, `github-pages`. Combinations that would silently do nothing (a target on a build/test/reusable workflow, or with `kubernetes=true`) are rejected.
- `pin_actions` option (`--pin-actions` on the CLI) to pin actions to full commit SHAs with a `# vX.Y.Z` comment. Pins live in `scaffold_gha.ACTION_REFS`; a test fails if the generator emits an action that has no pin.
- **MCP Dev Container Module** (`mcp_server/devcontainer_mcp.py`) with comprehensive language and tool support:
  - Multi-language support: Python, Java, Go, Node.js, Rust, Ruby, C/C++, PHP, C#, Kotlin, TypeScript, JavaScript
  - CI/CD tools: Docker, Podman, GitHub Actions, Jenkins, GitLab CI, Terraform, Kubectl, Helm
  - Kubernetes tools: K9s, Kustomize, ArgoCD, Flux, KinD, Minikube, OpenShift CLI
  - Build systems: Maven, Gradle, Make, CMake, Ant
  - Code analysis: SonarQube, ESLint, Pylint, Checkstyle, PMD
  - DevOps platforms: Prometheus, Grafana, ELK Stack, Nexus
- **Version Management System** (`mcp_server/version_manager.py`):
  - Centralized version database for 12 programming languages and tools
  - Environment variable-based version configuration (`DEVOPS_OS_VERSION_*`)
  - Version status tracking (latest, LTS, stable, deprecated, EOL)
  - Security-aware update recommendations and vulnerability detection
  - Version parsing, comparison, and constraint validation
  - `.env` file persistence and environment variable management
- **New MCP Tools for Version Management**:
  - `get_version_config()` - Retrieve current version configuration
  - `check_version_updates()` - Check available updates with security status
  - `suggest_versions()` - Get recommended versions (latest or LTS)
  - `update_versions()` - Update tool versions in environment
  - `check_security_issues()` - Identify security vulnerabilities by urgency level
- **Comprehensive Version Management Documentation**:
  - New guide: `hugo-docs/content/docs/dev-container/version-management.md` (11,440 bytes)
  - Version database with 12 tools and LTS information
  - Security level definitions (critical, high, medium, low)
  - Environment variable configuration examples
  - MCP tool usage examples and workflows
  - Team version management best practices
- Enhanced Hugo documentation:
  - New MCP Dev Container Setup guide (`hugo-docs/content/docs/dev-container/mcp-setup.md`)
  - New Language-Specific Guides (`hugo-docs/content/docs/dev-container/language-guides.md`)
  - New Version Management guide with security recommendations
  - Updated main Dev Container documentation with version management and MCP references
- Intelligent VS Code extension recommendations based on selected tools
- Automatic port forwarding configuration for services
- Support for multiple programming language versions
- AI-driven dev container configuration generation via MCP

### Removed
- Legacy dev container implementation (`.legacy/devcontainer/`)
- References to archived implementations from documentation

### Changed
- Updated `scaffold_devcontainer` MCP tool to use new `devcontainer_mcp` module
- Enhanced MCP tool with additional parameters for build tools, code analysis, and DevOps tools
- Updated Python, Node.js, Java, and Go version defaults to latest stable:
  - Python: 3.12 (was 3.11)
  - Node.js: 22 (was 20)
  - Java: 21 (was 17)
  - Go: 1.25.0 (was 1.21)
- Updated README.md repository structure documentation (removed .legacy reference)
- Updated .devcontainer/README.md to reflect new MCP module structure
- Enhanced version management with security-aware recommendations and LTS support

---

## [0.4.7] - 2026-07-08

### Changed
- Bumped CLI version to `0.4.7` in `cli/__version__.py`.
- Updated version badge to `0.4.7` in `README.md`.
- Updated version badge to `0.4.7` in `hugo-docs/content/_index.md`.

---

## [0.4.6] - 2026-04-01

### Changed
- Automated patch release — version bump to 0.4.6.

---

## [0.4.5] - 2026-03-21

### Changed
- Automated patch release — version bump to 0.4.5.

---

## [0.4.4] - 2026-03-21

### Changed
- Automated patch release — version bump to 0.4.4.

---

## [0.4.3] - 2026-03-21

### Changed
- Automated patch release — version bump to 0.4.3.

---

## [0.4.2] - 2026-03-18

### Fixed
- **`scaffold sre` empty `slos: []` when `--slo-type error_rate`** — `generate_slo_manifest()` in
  `cli/scaffold_sre.py` had no branch for the `error_rate` SLO type, leaving `slo.yaml` with an
  empty `slos: []` list. Sloth/OpenSLO tooling therefore received no SLO objectives. A dedicated
  `error_rate` SLO entry (with matching SLI queries and alerting config) is now generated when
  `--slo-type error_rate` is specified.

---

## [0.4.1] - 2026-03-17

### Changed
- Automated patch release — version bump to 0.4.1.

---

## [0.4.0] - 2026-03-15

### Added
- **`scaffold unittest` subcommand** — new `devopsos scaffold unittest` command that generates
  unit testing configuration files and sample test stubs for multiple tech stacks:
  - **Python** → `pytest.ini` (with pytest-cov options), `conftest.py` with shared fixtures,
    `tests/__init__.py`, and `tests/test_sample.py` with parametrized examples.
  - **JavaScript** → Jest (`jest.config.js`), Vitest (`vitest.config.js`), or Mocha (`.mocharc.js`)
    configuration plus a matching `tests/sample.test.js`.
  - **TypeScript** → same as JavaScript with TypeScript-specific Jest transform (`ts-jest`)
    and `tests/sample.test.ts`.
  - **Go** → table-driven `<name>_test.go` sample and `Makefile.test` with `test`, `test-race`,
    `test-cov`, and `lint` targets.
  - Coverage configuration is included by default and can be disabled with `--no-coverage`.
  - Supports comma-separated `--languages` to scaffold multiple stacks at once.
- **`generate_unittest_config` MCP tool** — exposes the new unit-test scaffold as an MCP tool
  so AI assistants can generate test configurations via conversation.
- **`cli/scaffold_unittest.py`** — the scaffold library backing the new command.
- **`docs/CLI-COMMANDS-REFERENCE.md`** — new section documenting all `unittest` options,
  output files, and examples.

---

## [0.3.0] - 2026-03-10

### Fixed
- **`scaffold gitlab` empty stages when `--type deploy` without `--kubernetes`** — `scaffold_gitlab.py`
  `_global_section()` previously excluded the `deploy` stage from the stages list whenever the
  `--kubernetes` flag was absent, producing an invalid pipeline. The condition is now corrected so
  that `--type deploy` always adds the `deploy` stage regardless of the Kubernetes flag.
- **Missing deploy job when `--type deploy` without `--kubernetes`** — `_deploy_job()` previously
  returned an empty dict when `kubernetes=False`, leaving the pipeline with a declared `deploy` stage
  but no corresponding job. A generic deploy stub (with branch-based rules) is now returned instead,
  giving users a ready-to-customise deployment step out of the box.

### Added
- **GitHub star count badge in README** — the project README now displays a live GitHub Stars badge
  alongside the existing license and version badges.

---

## [0.2.0] - 2026-03-08

### Fixed
- **`scaffold cicd` broken subprocess calls** — `scaffold_cicd.py` previously invoked
  `github-actions-generator-improved.py` and `jenkins-pipeline-generator-improved.py` via
  `subprocess.run`, which no longer exist. Both generators are now called directly via the
  `scaffold_gha` and `scaffold_jenkins` modules (same `_run_module_main` pattern used by all
  other scaffold subcommands).

### Added
- **Graceful help exit for all scaffold subcommands** — invoking any of the 7 scaffold
  subcommands (`gha`, `jenkins`, `gitlab`, `argocd`, `sre`, `devcontainer`, `cicd`) with no
  options now prints the command's full help text (including usage summary and examples) and
  exits cleanly with code 0, instead of silently running with defaults.
- **`--version` / `-V` flag** — `devopsos --version` (or `devopsos -V`) prints the current
  version string and exits. Version is sourced from the new `cli/__version__.py` single source
  of truth.
- **`cli/__version__.py`** — single source of truth for the package version (`0.2.0`).
- **`CHANGELOG.md`** — this file, tracking all notable changes.

---

## [0.1.0] - 2025-03-08

### Added

#### CLI (`cli/`)
- **`devopsos` unified CLI** – single entry-point (`python -m cli.devopsos`) built with [Typer](https://typer.tiangolo.com/).
- **`devopsos init`** – interactive wizard that scaffolds a `.devcontainer/devcontainer.json` tailored to the languages, CI/CD tools, and DevOps utilities you select.
- **`devopsos scaffold gha`** – generates a multi-stage GitHub Actions workflow (lint → build → test → deploy).
- **`devopsos scaffold jenkins`** – generates a `Jenkinsfile` with declarative pipeline stages.
- **`devopsos scaffold gitlab`** – generates a `.gitlab-ci.yml` with Docker, Kubernetes, and deploy stages.
- **`devopsos scaffold argocd`** – generates ArgoCD `Application` and `AppProject` manifests for GitOps deployments.
- **`devopsos scaffold sre`** – generates Prometheus alert rules, Grafana dashboard JSON, and SLO manifests.
- **`devopsos scaffold devcontainer`** – standalone devcontainer scaffolder with full tool-version control.
- **`devopsos scaffold cicd`** – meta-scaffolder that runs both GHA and Jenkins generation in one step.
- **`devopsos process-first`** – prints Process-First DevOps principles (Systems Thinking sections: what, mapping, tips, best-practices).
- **`--version` / `-V` flag** – prints the current `devopsos` version and exits.

#### MCP Server (`mcp_server/`)
- FastMCP-based server exposing every scaffold function as a native AI tool for Claude / ChatGPT plugins.
- Tools: `generate_github_actions`, `generate_jenkins_pipeline`, `generate_gitlab_ci`, `generate_argocd_config`, `generate_sre_config`, `generate_devcontainer`, `generate_cicd_pipeline`.

#### Documentation & Examples
- `README.md` – full project overview with quick-start, use-case table, and architecture diagram.
- `README-USECASE-EXAMPLES.md` – end-to-end worked examples for every scaffold command.
- `README-INDEX.md` – top-level navigation index for all documentation.
- `CONTRIBUTING.md` – contribution guide with coding conventions and PR checklist.
- `docs/` – extended Hugo-compatible documentation site sources.
- `feature-announcements/` – HTML/Markdown feature-announcement pages.
- `skills/` – reusable prompt-skill definitions for AI assistants.
- `go-project/` – example Go micro-service wired to the DevOps-OS scaffold outputs.
- `kubernetes/` – sample Kubernetes manifests referenced by the ArgoCD scaffold.
- `scripts/examples/` – shell-script quick-start examples.

#### Development Environment
- `.devcontainer/devcontainer.json` – ready-to-use GitHub Codespaces / VS Code dev-container with all Python, Docker, and Kubernetes tooling pre-installed.
- `.github/workflows/ci.yml` – full CI pipeline (lint, unit tests, integration tests).
- `.github/workflows/sanity.yml` – lightweight sanity-check workflow for PRs.
- `.github/workflows/pages.yml` – GitHub Pages deployment workflow for the Hugo docs site.

[0.3.0]: https://github.com/cloudengine-labs/devops_os/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/cloudengine-labs/devops_os/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cloudengine-labs/devops_os/releases/tag/v0.1.0
