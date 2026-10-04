#!/usr/bin/env python3
"""
DevOps-OS deploy preflight plan.

Produces a local test plan for a ``deploy_target``: the secret names to set, a
placeholder-only env template, and an ordered list of commands to run on the
user's own workstation. This module never runs anything and never sees a
credential; the commands are executed by the user (or their AI client, with the
user's approval) using the user's own environment.
"""

from devops_os.core.scaffold_gha import (
    DEPLOY_TARGETS,
    NETLIFY_CLI_VERSION,
    VERCEL_CLI_VERSION,
)

WRANGLER_VERSION = "4.147.0"  # checked 2026-10-04; the workflow itself uses cloudflare/wrangler-action

READ_ONLY = "read-only"
LOCAL_BUILD = "local-build"  # builds or writes files on this machine only
PUBLISHES = "publishes"      # changes something on the hosting platform

ENV_FILE = ".env.deploy"
PLACEHOLDERS = {
    "VERCEL_TOKEN": "<token from vercel.com/account/tokens>",
    "VERCEL_ORG_ID": "<orgId from .vercel/project.json after `vercel link`>",
    "VERCEL_PROJECT_ID": "<projectId from .vercel/project.json after `vercel link`>",
    "CLOUDFLARE_API_TOKEN": "<API token with Workers/Pages edit permission>",
    "CLOUDFLARE_ACCOUNT_ID": "<account id from the Cloudflare dashboard>",
    "NETLIFY_AUTH_TOKEN": "<personal access token>",
    "NETLIFY_SITE_ID": "<site id of a TEST site>",
    "RENDER_DEPLOY_HOOK_URL": "<deploy hook URL of a TEST service>",
}


def _check(cid, title, command, effect, expect, note=""):
    c = {"id": cid, "title": title, "command": command, "effect": effect, "expect": expect}
    if note:
        c["note"] = note
    return c


def _build_check(out_dir):
    return _check(
        "local-build", f"Build locally and confirm the output directory '{out_dir}' exists",
        f'npm ci && npm run build --if-present && test -d "{out_dir}" && echo "build output found"',
        LOCAL_BUILD, f"prints 'build output found'; if not, set build_output_dir to your framework's real output directory")


def _plan(target, name, out_dir):
    v = f"npx --yes vercel@{VERCEL_CLI_VERSION}"
    w = f"npx --yes wrangler@{WRANGLER_VERSION}"
    n = f"npx --yes netlify-cli@{NETLIFY_CLI_VERSION}"
    if target == "vercel":
        return [
            _check("identity", "Confirm the token works", f'{v} whoami --token "$VERCEL_TOKEN"', READ_ONLY,
                   "prints your Vercel username"),
            _check("pull", "Pull project settings (writes .vercel/)",
                   f'{v} pull --yes --environment=preview --token "$VERCEL_TOKEN"', LOCAL_BUILD,
                   "'Downloading ... Development/Preview Environment Variables' without errors",
                   "Needs VERCEL_ORG_ID and VERCEL_PROJECT_ID; the project must exist on Vercel. "
                   "It also writes .vercel/.env.*.local, which can hold secrets: keep .vercel/ out of git."),
            _check("build", "Build with Vercel's builder", f'{v} build --token "$VERCEL_TOKEN"', LOCAL_BUILD,
                   "a .vercel/output directory is created"),
            _check("deploy-preview", "Publish a PREVIEW deployment (not production)",
                   f'{v} deploy --prebuilt --token "$VERCEL_TOKEN"', PUBLISHES,
                   "prints a preview URL",
                   "The generated workflow adds --prod; this check differs only by that flag."),
        ]
    if target == "cloudflare-workers":
        return [
            _check("identity", "Confirm the token and account", f"{w} whoami", READ_ONLY,
                   "lists your account; the account ID matches CLOUDFLARE_ACCOUNT_ID"),
            _check("dry-run", "Compile the Worker without uploading", f"{w} deploy --dry-run", LOCAL_BUILD,
                   "'--dry-run: exiting now' with no errors"),
            _check("deploy", "Publish the Worker", f"{w} deploy", PUBLISHES, "prints the Worker URL",
                   "Publishes to the Worker named in wrangler config; use a test Worker name or --env."),
        ]
    if target == "cloudflare-pages":
        return [
            _check("identity", "Confirm the token and account", f"{w} whoami", READ_ONLY,
                   "lists your account; the account ID matches CLOUDFLARE_ACCOUNT_ID"),
            _check("project", "Confirm the Pages project exists", f"{w} pages project list", READ_ONLY,
                   f"'{name}' appears in the list",
                   f"The workflow deploys to project '{name}'; create it first (`wrangler pages project create {name}`) if missing."),
            _build_check(out_dir),
            _check("deploy-preview", "Publish a PREVIEW deployment on a non-production branch",
                   f'{w} pages deploy "{out_dir}" --project-name={name} --branch=preflight-test', PUBLISHES,
                   "prints a preview URL on a preflight-test.<project>.pages.dev alias"),
        ]
    if target == "netlify":
        return [
            _check("identity", "Confirm the token and site", f"{n} status", READ_ONLY,
                   "shows your account; with NETLIFY_SITE_ID set, the site resolves"),
            _build_check(out_dir),
            _check("deploy-draft", "Publish a DRAFT deploy (not production)",
                   f'{n} deploy --dir="{out_dir}" --message "preflight test"', PUBLISHES,
                   "prints a unique draft URL; the live site is unchanged",
                   "The generated workflow adds --prod; this check differs only by that flag."),
        ]
    if target == "render":
        return [
            _check("hook-set", "Confirm the hook URL is set", 'test -n "$RENDER_DEPLOY_HOOK_URL" && echo set', READ_ONLY,
                   "prints 'set'"),
            _check("hook-format", "Confirm it looks like a Render deploy hook",
                   'printf "%s" "$RENDER_DEPLOY_HOOK_URL" | grep -Eq "^https://api\\.render\\.com/deploy/srv-" && echo ok',
                   READ_ONLY, "prints 'ok'"),
            _check("trigger", "Trigger a deploy of the TEST service",
                   'curl -fsS -X POST "$RENDER_DEPLOY_HOOK_URL" > /dev/null && echo triggered', PUBLISHES,
                   "prints 'triggered'; the deploy appears in the Render dashboard",
                   "Render hooks have no dry run: this starts a real deploy, so use a test service."),
        ]
    if target == "github-pages":
        return [
            _check("pages-enabled", "Confirm Pages is enabled with the 'GitHub Actions' source",
                   'gh api repos/{owner}/{repo}/pages --jq .build_type', READ_ONLY,
                   "prints 'workflow'; a 404 means Pages is not enabled (Settings > Pages > Source: GitHub Actions)"),
            _build_check(out_dir),
        ]
    raise ValueError(f"Unknown deploy target '{target}'. Valid targets: {sorted(DEPLOY_TARGETS)}")


def build_plan(target, name="my-app", build_output_dir="dist"):
    """Return the preflight plan for ``target`` as a JSON-serialisable dict."""
    checks = _plan(target, name, build_output_dir)
    secrets = list(DEPLOY_TARGETS[target])
    not_local = []
    if target == "github-pages":
        not_local.append("The deploy itself (actions/deploy-pages) needs GitHub's OIDC token and only runs in "
                         "Actions. After the checks above pass, trigger it from a test branch or fork.")
    return {
        "deploy_target": target,
        "summary": f"{len(checks)} checks for {target}: run them in order from the repository root. "
                   f"'{READ_ONLY}' and '{LOCAL_BUILD}' checks change nothing on {target}; "
                   f"'{PUBLISHES}' checks do, so point them at a test project.",
        "required_secrets": secrets,
        "env_file": {
            "path": ENV_FILE,
            "content": "".join(f"{s}={PLACEHOLDERS.get(s, '<value>')!r}\n".replace("'", '"') for s in secrets),
            "usage": f'Fill in the values yourself, add {ENV_FILE} to .gitignore, then run: set -a; . ./{ENV_FILE}; set +a',
        } if secrets else None,
        "checks": checks,
        "not_testable_locally": not_local,
        "run_whole_workflow_locally": {
            "tool": "act (https://github.com/nektos/act, needs Docker)",
            "list_jobs": "act -l",
            "validate_only": "act -n -W .github/workflows/<generated-file>.yml",
            "warning": "Without -n, act executes every step for real. With real tokens that publishes to the "
                       "target, so use it only against a test project.",
        },
        "safety": [
            "Do not paste tokens into a chat or an MCP tool call; set them in your shell or with `gh secret set`.",
            f"Add {ENV_FILE} to .gitignore and never commit it.",
            "Point 'publishes' checks at a test project, site or service, not production.",
            "Add the same secret names as repository secrets before the first workflow run.",
        ],
    }
