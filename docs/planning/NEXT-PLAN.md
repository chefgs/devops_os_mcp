# Next Plan

Backlog after PR #18 (modern GitHub Actions defaults, deploy targets, security scans, `analyze_repo`, `audit_github_workflow`, `generate_dependabot_config`, `generate_deploy_preflight`, scan-first guidance). Written 2026-10-04. Nothing below is started.

## Ground rules (agreed during PR #18)

- **Be realistic, not enthusiastic.** Build only what is needed and verify it works; no speculative features.
- **Verify before moving on.** Each item ships with tests, and with real-tool checks where a tool is involved (actionlint + shellcheck, the real CLIs, the real MCP stdio session).
- **The MCP never runs commands, deploys, or accepts credentials.** It generates and advises. Tokens stay in the user's environment.
- **Existing pipelines are never replaced.** Missing pieces are added as separate files.
- **This repo is independent of CodePilot AI** (private product). Do not copy its code, text or identifiers here; any mapping between the two lives on the private side.
- **Deploy targets are scaffolds**, not tested on live accounts. Accepted and documented; do not claim otherwise.
- Conventions: branch from `main` as `feature/*` or `fix/*`; commit format `<type>(<scope>): <subject>`; end commits with the attribution line; update CHANGELOG and docs with the change.

Legend: **Effort** S under an hour, M one session, L several. **Status** is *unverified* where the problem was noticed but not investigated.

---

## Priority 1: finish what PR #18 left open

| ID | Item | Why | Done when | Effort |
|----|------|-----|-----------|--------|
| N1 | **Release housekeeping.** Pull `main`, delete the merged branch, choose the version bump (the generator output changed for existing callers: no container, new action versions, new `permissions:`/`concurrency:`; Jenkins now `agent any`), write release notes, tag. | The change is breaking for some callers and is only described in the CHANGELOG. | Version chosen and recorded; tag and release notes published. | S |
| N2 | **Dogfood this repo's own CI.** `.github/workflows/*.yml` use `checkout@v4`, `setup-python@v5`, have no `permissions:`/`concurrency:`, and there is no `dependabot.yml`. Run `analyze_repo` and `audit_github_workflow` on the repo, apply the findings, add Gitleaks and Semgrep (via `workflow_type: security`). | The audit tool already flags these; the repo should pass its own checks. | `audit_github_workflow` on each workflow reports no medium/high findings; Dependabot config present; scans green. | S |
| N3 | **Review the GitLab generator** (`scaffold_gitlab.py` / `generate_gitlab_ci_pipeline`). *Unverified.* GitHub Actions and Jenkins had placeholder images, secrets pasted into scripts, unquoted variables and stale versions; GitLab was never audited for the same. | Likely sibling bugs. | Findings listed; each fixed with a test, or recorded as not applicable. | S–M |
| N4 | **Check how tool output reaches the user.** *Unverified.* Over a real stdio session the workflow arrived wrapped in JSON with suggestion metadata (`specificity_score`), from the response enhancer. Confirm what each client shows and whether the YAML is still easy to copy. Decide whether to keep the wrapper. | Core user experience. | Behaviour documented for at least one real client; decision recorded; fixed if it hinders copying. | S |
| N5 | **Remove stale artifacts.** `devops_os/core/scaffold_cicd.py` (unused by any tool, still defaults to `docker.io/yourorg/devops-os`); `scripts/examples/github-actions-complete.yml` and `scripts/examples/jenkins-complete.groovy` (old output). Delete or regenerate. | Misleading leftovers. | No `yourorg` in code or examples; nothing references the removed files. | S |

## Priority 2: close known gaps

| ID | Item | Why | Done when | Effort |
|----|------|-----|-----------|--------|
| N6 | **Request #2 is only partly delivered.** The user asked the audit to "return a diff or only the missing jobs". `audit_github_workflow` returns findings and suggested calls only. Add an output that proposes the hardening fixes as a unified diff of the pasted file, and/or the missing jobs as YAML. | The main gap against the original request. | Given a legacy workflow, the tool returns a diff that applies cleanly and passes actionlint; tests cover it. | M |
| N7 | **Regenerate `skills/*.json` from the server's tool schemas.** They cover 7 tools and none of the new options (17 tools exist). Keep the Claude/OpenAI parity test. | API users see an older product; hand-edited JSON drifts. | A script generates both files from the server schemas; a test fails when they differ from the server. | M |
| N8 | **Pin freshness automation.** `ACTION_REFS`, scanner and CLI versions were resolved on 2026-10-04 and will age. `tests/test_action_pins_live.py` only warns about newer majors. Add a scheduled workflow that opens a PR when pins are stale. | Silent drift. | Scheduled run opens a PR (or issue) listing stale pins. | M |
| N9 | **CI Python matrix.** CI runs 3.11 only; development used 3.14. Add 3.12 and 3.13. | Version-specific breakage. | Matrix green. | S |
| N10 | **Jenkinsfile validation.** Output is checked as text only; no Groovy or Jenkins linter was available. Add a parse/lint check in CI. | Unverified output. | CI step fails on an invalid Jenkinsfile. | M |
| N11 | **Real-account deploy checks (optional).** Cheapest first: `github-pages` (no secrets), `render` (one hook). Then Netlify, Vercel, Cloudflare on throwaway projects. | Upgrades "scaffold" to "tested" per target. | Per target: a recorded successful run, and the docs note updated for that target only. | S per target |

## Priority 3: product improvements

| ID | Item | Notes | Effort |
|----|------|-------|--------|
| N12 | **Monorepo and package-manager support in generators.** Add `working_directory` and a package-manager option (pnpm, yarn, bun) to `generate_github_actions_workflow`. `analyze_repo` already detects both and only warns. | Detection exists; generation does not. | M |
| N13 | **Dependabot: several directories in one call**, plus labels and ignore rules. A monorepo currently needs one call per directory. | `analyze_repo` already emits one call per directory. | S |
| N14 | **Deeper detection in `analyze_repo`.** Python and Node versions (`pyproject.toml`, `.nvmrc`, `engines`), framework-specific output directories (Next.js is currently unset). | Fewer values for users to correct. | M |
| N15 | **More audit rules.** `pull_request_target` with PR checkout, missing `timeout-minutes`, `continue-on-error` on security steps. | | M |
| N16 | **Scan improvements.** SARIF upload to code scanning, weekly schedule for the `security` workflow, configurable severity thresholds, a generated `.gitleaks.toml`. | | M |
| N17 | **Cloud deploy templates with OIDC** (AWS, GCP, Azure) without stored keys. | Preferred by platform teams. | L |
| N18 | **More prompts and a client check.** Add `harden` and `deploy` prompts. Test how Claude Desktop, Cursor and Copilot present the `start` prompt and whether they follow the server instructions. *Only protocol-level behaviour has been verified so far.* | | M |
| N19 | **Reusable "golden path" workflow for platform teams.** Typed `workflow_call` inputs, callable in about 20 lines. | | L |

## Cross-project (private side, not in this repo)

- **CodePilot ↔ MCP mapping.** CodePilot's issue IDs mapped to MCP tool calls, kept in the private repo. The MCP stays unaware of CodePilot.

## Decisions needed

1. **Version bump** for N1: minor or major, given the output change for existing callers.
2. **N4:** keep or drop the response wrapper around tool output.
3. **N7:** generate `skills/*.json` from schemas, or retire the files.
4. **N11:** whether any live-account testing is worth doing, or the "scaffold" label is final.

## Suggested order

N1, N2, N4, N6 first (close the release and the biggest gap against the original request); then N3, N5, N9; then N7, N8, N10; then Priority 3 as users ask for it.
