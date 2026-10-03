# MCP Server — Scenario-Based Test Strategy

**Date:** 2026-10-03
**Scope:** all 13 tools exposed by the `devops-os` MCP server (`mcp_server/server.py`)
**Test suite:** `tests/test_scenario_based.py` (84 tests), building on the existing `tests/` + `mcp_server/test_*.py` suite (382 tests). Current total as of the spec-compliance audit below: 490 tests, 0 failed, 0 skipped.
**Related:** [`mcp-validation/TEST_REPORT.md`](../../mcp-validation/TEST_REPORT.md) (the incident log — how 3 of these bugs were actually found and fixed), `tests/test_mcp_protocol.py` (live wire-protocol tests this strategy reuses), [`docs/testing/mcp-test-coverage-report.html`](../testing/mcp-test-coverage-report.html) (visual coverage report — open in a browser, charts per functional area and scenario nature)

---

## Why this document exists

The existing suite (382 tests before this pass) is heavy on "does valid input produce valid output" and much lighter on "does invalid input get rejected, and does this actually run in the deployed server." That asymmetry is exactly what let two real bugs ship silently (documented in `mcp-validation/TEST_REPORT.md`). This document is the general, reusable strategy — not an incident report — for closing that gap across every tool, and for keeping it closed as new tools are added.

---

## The scenario framework

Every tool is run through the same fixed shape. The shape itself is the point: if a tool is missing a row, that's visible by omission, not by having to remember to think of it.

| Category | Question it answers | What it has caught |
|---|---|---|
| **Happy path** | Does realistic input work? | Baseline only — passes even when a tool is badly broken elsewhere |
| **Boundary** | What happens exactly at and past every numeric/length limit? | `replicas=101`, `port=65536`, `slo_target=49.99` |
| **Invalid / rejected** | Does the validator actually reject what it claims to reject? | The exact class of bug behind the `workflow_type="basic"` hang |
| **Cross-parameter** | Do flag combinations that change behavior together still behave correctly? | `kubernetes=True` × each `k8s_method`; `auto_sync` + `rollouts` together |
| **Adversarial / structural** | Shell metacharacters, malformed JSON, unknown enum values, empty/huge strings | `generate_argocd_config`'s `image`/`repo` injection gap (Bug #3) |
| **Live-protocol** | Does the *real* subprocess server (not just the Python function) behave correctly? | Bug #2 — suggestions worked in isolation, never fired through the real stdio entrypoint |
| **Determinism** | Same input twice → identical output? | Matters for GitOps diffing / CI reproducibility; not yet violated, but untested before this pass |

### Why two different calling styles are both necessary

Most scenario tests call the tool's Python function directly (`generate_k8s_config(...)`) — fast, lets you run hundreds of parameter combinations in milliseconds. But this bypasses `mcp_server/server.py`'s module-level `mcp` vs. `create_mcp_server()` split entirely: `_response_enhancer` and `_concurrency_manager` are only ever `None` or real depending on *which* code path actually ran, and a unit-level call can't see that difference. Bug #2 was invisible to every unit-level test in the suite — it only showed up in `test_mcp_protocol.py`, the one file that spawns `python -m mcp_server.server` as a real subprocess and talks actual MCP JSON-RPC to it.

**Rule applied here:** any claim about behavior that depends on server *wiring* (suggestions, concurrency limits, auth) needs at least one live-protocol test via `_MCPSession` (reused from `test_mcp_protocol.py`), not just a unit-level call. Everything else — pure input validation, generator output shape — is fine at the unit level and should stay there for speed.

### Why the hello-world sample apps

Scenarios use the project's own 5 sample apps (`hello-python`, `hello-typescript`, `hello-go`, `hello-rust`, `hello-java`, created during the earlier MCP validation pass) as realistic input instead of synthetic placeholder strings like `"my-app"`. This keeps the test suite's "happy path" grounded in something a reader can cross-reference against real generated output in `mcp-validation/hello/`, rather than abstract fixtures that only exist inside the test file.

---

## Coverage by tool

| Tool | Happy | Boundary | Invalid/rejected | Cross-param | Adversarial | Determinism | Finding |
|---|---|---|---|---|---|---|---|
| `generate_github_actions_workflow` | ✅ | ✅ (languages) | ✅ (`workflow_type`) | ✅ (k8s methods) | ✅ (name injection) | ✅ | Bug #1 fixed; now the only tool with a direct regression test for it |
| `generate_jenkins_pipeline` | ✅ | — | — | — | ✅ (name injection) | — | **Gap found**: `pipeline_type` has no validator at all (asymmetric with GHA) — documented, not yet fixed, pending a decision |
| `generate_gitlab_ci_pipeline` | ✅ | — | — | — | — | — | Same `pipeline_type` gap as Jenkins |
| `generate_k8s_config` | ✅ | ✅ (replicas, port, both edges) | ✅ (image injection) | ✅ (expose_service, deployment_method ×4) | ✅ | ✅ | Confirmed correctly defended at every edge |
| `generate_argocd_config` | ✅ | ✅ (repo length) | ✅ | ✅ (auto_sync + rollouts) | ✅ (image injection) | — | **Bug #3 found and fixed**: `repo`/`image` were never passed into validation at all |
| `generate_sre_configs` | ✅ | ✅ (slo_target, both edges) | ✅ | ✅ (all 4 slo_types) | — | — | Confirmed correct |
| `scaffold_devcontainer` | ✅ (all 5 langs) | ✅ (empty languages) | ✅ (mixed valid+invalid list) | — | — | — | Confirmed fail-closed (rejects whole list, doesn't silently drop the bad entry) |
| `generate_unittest_config` | ✅ | — | ✅ | — | — | — | Confirmed the `name`→`project_name` validator rename is intentional, not a bug (looked like one during review) |
| `get_version_config` / `check_version_updates` / `suggest_versions` / `check_security_issues` | ✅ | — | ✅ (unknown tool) | — | — | — | Confirmed graceful error envelope, no crash |
| `update_versions` | ✅ | — | ✅ (malformed JSON, empty object) | — | ✅ (unknown tool + bogus version) | — | Confirmed `VersionManager.set_version`'s whitelist already correctly rejects both, and never touches `os.environ` on rejection — the one tool that was well-defended going in |

---

## What this pass found

Three bugs, all the same root pattern: **validation logic existed in `validators.py`, was never wired to the parameter it was written for.**

| Bug | Tool | Gap | Fix |
|---|---|---|---|
| #1 | `generate_github_actions_workflow` | `workflow_type` never validated; `"basic"` (a value that never existed) reached `sys.exit(1)` in a server worker thread, hanging the whole connection | Added `validate_choice()`, replaced `sys.exit(1)` with `raise ValueError` |
| #2 | All tools (server-wide) | `create_mcp_server()` — the only function that initializes `_response_enhancer`/`_concurrency_manager` — was never called on the stdio path; suggestions silently never fired in production | Initialize those globals directly in `__main__` before `mcp.run()` |
| #3 | `generate_argocd_config` | `repo`/`image` never passed into `validate_tool_inputs()`, despite validators existing for both; `image="...$(whoami):latest"` was silently accepted | Pass `repo=repo, image=image` into the validation call |

None of these were found by reading code in isolation — all three were found by designing the scenario *first* ("what should happen if `workflow_type` is invalid?", "what should happen if `image` contains shell metacharacters?") and then checking whether the code actually did that, rather than reading the code and assuming the docstring or the existence of a validator function meant it was wired up.

## Gaps found in this pass, status as of commit `4dc7f65`

All four were fixed in a later pass than the one that found them — noted here so this doc doesn't silently drift out of sync with the code the way the bugs above did.

- ✅ **Jenkins/GitLab `pipeline_type` validation** — added, matching GHA's `workflow_type` pattern (`mcp_server/validators.py`).
- ✅ **`ConcurrencyManager` wiring** — added `limit_sync()` (thread-safe, since all 13 tools are sync functions) and a `concurrency_limited` decorator applied to all 13 handlers. Caveat: scientific before/after testing (stashing the fix, re-running the same 25-pipelined-call reproduction) showed it does *not* fix a reproducible crash — the original "concurrency crash" was most likely fully explained by the `workflow_type` hang (Bug #1) hitting several calls at once, not a distinct defect. The wiring is legitimate defense-in-depth for genuinely heavy load, not a confirmed fix for that specific incident.
- ✅ **HTTP transport parity** — turned out to already be fixed as a side effect of the Bug #2 fix (the global init moved before the transport branch, not just inside the stdio arm).
- ✅ **`test_http.py`'s tautological tests** — `/health` and `/ready` didn't just lack good tests, they didn't exist as routes at all, and `docker-compose.yml`'s healthcheck + `scripts/smoke-test.py` both already depended on them — a live, previously-undetected production bug. Implemented both routes for real (`_register_health_routes`), tested via an ASGI client. Separately, the MCP-SDK-client tests in the same file were fixed too: a dead import (`StdioClientTransport` — the TypeScript SDK's class name, never valid in Python) meant two tests had likely never executed in this repo's history.

---

## MCP spec compliance audit (after all bugs above were fixed)

A separate pass checked the server against the actual [MCP specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — not the test suite, the primary source doc — since passing every test above only proves the server does what *this project's own tests* expected, not that it gives other clients what the protocol says they're entitled to. Confirmed correct by reading SDK source rather than assuming: stdout hygiene (every `print()` in `devops_os/core/*.py` is CLI-only, never reachable from the MCP path), error-handling semantics (the SDK converts any raised exception into `isError: true`, never a malformed protocol error — the reason Bug #1's `sys.exit()` → `raise ValueError` fix was spec-correct, not just tidier), and DNS-rebinding protection for the default localhost deployment (the SDK auto-enables it when `host` is `127.0.0.1`/`localhost`/`::1`).

Two real gaps found, both fixed:

| Gap | Detail | Fix |
|---|---|---|
| **Zero tool annotations on all 13 tools** | The spec defines `readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint` so clients can tell a safe read apart from a state-changing write before prompting a human for approval. Every tool here looked identical to a client trying to make that call. | Added a `TOOL_METADATA` dict (`mcp_server/server.py`) applied consistently to both the stdio and HTTP-transport instances; 12 generators/lookups get `readOnlyHint=True`, `update_versions` (the one tool that mutates server state) is the sole exception. Tested in `mcp_server/test_http.py::test_tool_annotations_declare_read_only_and_risk_correctly`. |
| **DNS-rebinding protection silently disabled for non-localhost (remote) deployment** | The SDK's auto-enable only fires for localhost. Binding `0.0.0.0` — required for the server to be reachable at all inside a container, and what the "remote" profile and `docker-compose.yml` already do — turns that protection off with no warning. | Added `_build_transport_security()` (`mcp_server/server.py`) plus two new `Config` fields (`DEVOPS_OS_ALLOWED_HOSTS`/`DEVOPS_OS_ALLOWED_ORIGINS`, `mcp_server/config.py`): builds real `TransportSecuritySettings` when the deployment configures its allowlist, logs a loud warning when it hasn't (no safe default exists to guess). Documented operator-facing in `docs/mcp/HTTP-SETUP.md`. Tested in `mcp_server/test_http.py::test_transport_security_*` and `mcp_server/test_config.py::test_config_allowed_hosts_and_origins_from_env`. |

Neither gap was reachable by any test in this suite, including the 84-test scenario pass above — they're not input-validation problems, they're missing protocol metadata and missing transport-layer configuration. A scenario framework finds "does this tool reject bad input"; it doesn't find "does this tool tell the client what kind of tool it is" unless you specifically go looking by reading the spec, not the code.

---

## How to extend this suite

When adding a new MCP tool:
1. Add a row to the coverage table above before writing code — decide up front which categories apply (not every tool needs cross-parameter tests; every tool needs invalid/rejected if it has any validated field).
2. Write the validator in `validators.py` **and** the test in the same change — Bug #1's postmortem rule ("write a test for every claim") applies literally: a validator with no corresponding rejection test is exactly how Bugs #1 and #3 shipped.
3. If the new behavior depends on server-level wiring (not just input validation), add at least one `_MCPSession`-based live test, not just a unit-level call — Bug #2 is the reason this rule exists.
4. Reuse the hello-world sample apps (`mcp-validation/hello/`) for happy-path input where an app name/image is needed, instead of inventing a new placeholder each time.
5. Add the new tool to `TOOL_METADATA` in `server.py` with real annotations (`readOnlyHint` etc.) at the same time you write the tool, not as a later pass — the spec-compliance audit above is the reason this rule exists; it's easy to ship 13 tools with correct validation and zero metadata, same as it's easy to ship a validator with no test.
