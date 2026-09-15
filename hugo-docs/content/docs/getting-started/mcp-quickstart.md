---
title: "MCP Quick Start"
weight: 15
---

# MCP Quick Start — 5 Minutes

Get DevOps-OS running as an MCP server in Claude Desktop in under 5 minutes.

---

## What You'll Do

1. Clone the repo
2. Install dependencies
3. Add to Claude Desktop config
4. Generate your first pipeline with AI

**Total time: ~4 minutes**

---

## Step 1: Clone & Install (1 minute)

```bash
git clone https://github.com/cloudengine-labs/devops_os.git
cd devops_os

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install MCP dependencies
pip install -r mcp_server/requirements.txt
```

---

## Step 2: Configure Claude Desktop (2 minutes)

### Find Your DevOps-OS Path

```bash
# In the devops_os directory, get the full path
pwd
# Output: /Users/alice/projects/devops_os (macOS/Linux)
# Or: C:\Users\alice\projects\devops_os (Windows)
```

### Open Claude Config File

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
Open `%APPDATA%\Claude\claude_desktop_config.json` in your text editor

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

### Add DevOps-OS to Config

Insert this block (if `mcpServers` already exists, just add the `devops-os` entry):

```json
{
  "mcpServers": {
    "devops-os": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/Users/alice/projects/devops_os"
    }
  }
}
```

Replace `/Users/alice/projects/devops_os` with your actual path.

### Restart Claude

- Quit Claude completely (⌘Q on macOS, Alt+F4 on Windows)
- Reopen Claude Desktop
- You should see a wrench icon 🔧 at the bottom right of the chat

---

## Step 3: Generate Your First Pipeline (2 minutes)

### Ask Claude

In Claude Desktop, ask:

> *Generate a GitHub Actions CI/CD workflow for a Python Flask API with pytest tests and Docker build to Docker Hub.*

Claude will:
1. Call the `generate_github_actions_workflow` tool
2. Return a ready-to-use YAML file
3. Explain each stage

### Copy the Output

Claude shows the generated workflow YAML. Copy it and save as `.github/workflows/ci.yml` in your project.

---

## Step 4: Try More Prompts

### Jenkins Pipeline

> *Generate a Jenkins Declarative Pipeline for a Java Spring Boot application with Maven build, SonarQube scan, and ArgoCD deployment to production.*

### Kubernetes

> *Create Kubernetes manifests (Deployment + Service) for a Node.js API with 3 replicas, port 3000, and image `myregistry/myapp:v1.0`.*

### GitLab CI

> *Generate a `.gitlab-ci.yml` for a Python project with lint, test, and Docker build stages.*

### SRE/Observability

> *Generate SRE monitoring configs (Prometheus alert rules, Grafana dashboard, and SLO) for a microservice called "payment-api".*

---

## Common Tasks

### Task: Multi-language Pipeline

> *Generate GitHub Actions for a project with Python backend and React frontend. Include separate test stages and a combined Docker build.*

### Task: GitOps Deployment

> *Create ArgoCD Application manifests for deploying a service from GitHub to a Kubernetes cluster, with auto-sync enabled.*

### Task: Hardening Baseline

> *Generate Kyverno policies for a production Kubernetes cluster following CIS Kubernetes Benchmarks.*

### Task: Dev Container

> *Scaffold a devcontainer for Python + Go + Node.js development with pre-installed tools.*

---

## Troubleshooting

### "Wrench icon shows error"

1. Check the path in `claude_desktop_config.json` is correct:
   ```bash
   ls /path/you/configured/mcp_server/server.py
   ```

2. Verify Python can run the server:
   ```bash
   python -m mcp_server.server
   ```
   You should see output about MCP tools being registered. Press Ctrl+C to stop.

3. Restart Claude completely (not just refresh).

### "Tool not found" error

- Ensure you have the latest version: `git pull`
- Reinstall dependencies: `pip install -r mcp_server/requirements.txt`
- Restart Claude

### Other Issues

See [MCP Setup & Configuration]({{< relref "/docs/ai-integration/mcp-setup" >}}) for detailed troubleshooting.

---

## Next Steps

| I want to… | Read |
|-----------|------|
| Understand MCP in depth | [MCP Setup & Configuration]({{< relref "/docs/ai-integration/mcp-setup" >}}) |
| Set up for ChatGPT (not Claude) | [MCP Setup: ChatGPT Custom GPT]({{< relref "/docs/ai-integration/mcp-setup#chatgpt-setup-custom-gpt" >}}) |
| Deploy to production | [MCP Setup: Docker & Remote]({{< relref "/docs/ai-integration/mcp-setup#docker-deployment" >}}) |
| See all available tools | [AI Integration Overview]({{< relref "/docs/ai-integration" >}}) |
| Learn CLI instead of MCP | [Getting Started]({{< relref "/docs/getting-started" >}}) |

---

## What's Next?

Once you're comfortable generating configs with Claude, check out:
- **[CLI Reference]({{< relref "/docs/reference" >}})** — Run the same generators from the command line
- **[GitHub Actions Deep Dive]({{< relref "/docs/ci-cd/github-actions" >}})** — Understand every stage
- **[Infrastructure Hardening]({{< relref "/docs/platform-engineering/hardening" >}})** — Generate security policies
- **[SRE Configuration]({{< relref "/docs/sre" >}})** — Set up observability

---

## Questions?

- 🐛 Report bugs: [GitHub Issues](https://github.com/cloudengine-labs/devops_os/issues)
- 💬 Ask questions: [GitHub Discussions](https://github.com/cloudengine-labs/devops_os/discussions)
