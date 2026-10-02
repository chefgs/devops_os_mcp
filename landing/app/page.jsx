import React from 'react'
import Link from 'next/link'
import Header from './components/Header'
import Footer from './components/Footer'
import './styles/globals.css'

export const metadata = {
  title: 'DevOps-OS MCP | AI-Powered DevOps Configuration',
  description: 'Stop writing boilerplate DevOps configs. Use Claude or ChatGPT to generate production-ready CI/CD pipelines, Kubernetes manifests, and SRE dashboards.',
  openGraph: {
    title: 'DevOps-OS MCP | AI-Powered DevOps Configuration',
    description: 'Stop writing boilerplate DevOps configs. Use Claude or ChatGPT to generate production-ready CI/CD pipelines, Kubernetes manifests, and SRE dashboards.',
  },
}

export default function Home() {
  return (
    <main className="page-container">
      <Header />
      
      {/* Hero Section - Problem-focused, not marketing-focused */}
      <section className="hero">
        <div className="hero-content">
          <div className="hero-text">
            <h1>Stop Writing DevOps Configs by Hand</h1>
            <p className="hero-subtitle">
              Ask Claude or ChatGPT in plain English. Get production-ready CI/CD pipelines, 
              Kubernetes configs, and SRE dashboards in seconds.
            </p>
            <div className="hero-cta">
              <a href="https://github.com/chefgs/devops_os_mcp" className="button button-primary">
                Get Started on GitHub
              </a>
              <a href="#how-it-works" className="button button-secondary">
                See How It Works
              </a>
            </div>
          </div>
          <div className="hero-visual">
            <div className="code-example">
              <div className="code-header">Your request (plain English)</div>
              <p className="code-text">
                "Generate a GitHub Actions workflow for testing and deploying a Node.js app to Kubernetes"
              </p>
              <div className="code-arrow">↓</div>
              <div className="code-header">DevOps-OS MCP</div>
              <p className="code-text small">Processes through AI assistant</p>
              <div className="code-arrow">↓</div>
              <div className="code-header success">Production-Ready Config</div>
              <p className="code-text">Complete, tested, deployment-ready</p>
            </div>
          </div>
        </div>
      </section>

      {/* Real Problems Section */}
      <section className="problems-section">
        <h2>The Reality of DevOps Today</h2>
        <div className="problems-grid">
          <div className="problem-card">
            <h3>🔄 Copy-Paste Hell</h3>
            <p>
              You know exactly what you need, but you spend hours copy-pasting from documentation, 
              Stack Overflow, and old projects. Config templates have subtle bugs that only show 
              up in production.
            </p>
          </div>
          <div className="problem-card">
            <h3>📚 Knowledge Tax</h3>
            <p>
              You shouldn't need to be a Kubernetes expert to deploy an app. Yet you're forced to 
              learn YAML syntax, ArgoCD patterns, Kustomize overlays, and a dozen other tools just 
              to get the basics right.
            </p>
          </div>
          <div className="problem-card">
            <h3>⏱️ Inconsistent Standards</h3>
            <p>
              Different teams use different pipeline templates. Naming conventions drift. Security 
              policies are half-implemented. Each project reinvents the wheel instead of using shared, 
              battle-tested patterns.
            </p>
          </div>
          <div className="problem-card">
            <h3>🐛 Silent Failures</h3>
            <p>
              A monitoring setup works until it doesn't. Alert thresholds are cargo-culted from 
              examples. Dashboards show metrics no one looks at. When things break, you're blind.
            </p>
          </div>
        </div>
      </section>

      {/* What DevOps-OS Actually Does */}
      <section className="what-does-it-do" id="how-it-works">
        <h2>What You Actually Get</h2>
        <div className="features-list">
          <div className="feature">
            <h3>🚀 CI/CD Pipelines</h3>
            <p>
              <strong>GitHub Actions, GitLab CI, or Jenkins—your choice.</strong><br/>
              Generate complete pipelines with testing, building, and deployment stages. 
              Includes dependency caching, matrix builds, and secrets management. 
              Takes 30 seconds instead of 3 hours.
            </p>
          </div>

          <div className="feature">
            <h3>☸️ Kubernetes Manifests</h3>
            <p>
              <strong>Deployments, Services, Ingress, ConfigMaps, and more.</strong><br/>
              Get YAML that actually works. Properly formatted, with resource limits, 
              health checks, and security contexts. Never hand-write another Deployment spec.
            </p>
          </div>

          <div className="feature">
            <h3>🏗️ GitOps Configs</h3>
            <p>
              <strong>ArgoCD Applications or Flux CD Kustomizations.</strong><br/>
              Set up declarative deployments with proper sync policies. Stop managing 
              clusters manually. Get reproducible, versioned infrastructure.
            </p>
          </div>

          <div className="feature">
            <h3>📊 SRE Dashboards & Alerts</h3>
            <p>
              <strong>Prometheus alert rules and Grafana dashboards that make sense.</strong><br/>
              Forget metric-dumping dashboards. Get dashboards that show what actually matters: 
              latency, error rates, resource usage. Alerts that fire for real problems.
            </p>
          </div>

          <div className="feature">
            <h3>🔐 Infrastructure Hardening</h3>
            <p>
              <strong>Security policies based on industry standards.</strong><br/>
              Generate Kyverno policies, InSpec profiles, and compliance checks aligned with 
              CIS, STIG, NSA/CISA, and Pod Security Standards. Ship secure by default.
            </p>
          </div>

          <div className="feature">
            <h3>🧪 Test Scaffolding</h3>
            <p>
              <strong>pytest, Jest, Vitest, Mocha, or Go test configs.</strong><br/>
              Get a complete test setup with fixtures, mocks, and CI integration. 
              Start writing tests immediately, not boilerplate.
            </p>
          </div>
        </div>
      </section>

      {/* Who This Is For */}
      <section className="audience-section">
        <h2>Built for Different Teams</h2>
        <div className="audience-grid">
          <div className="audience-card">
            <h3>Solo Developers</h3>
            <p>
              Ship production-ready infrastructure without learning DevOps. Ask Claude, get a 
              working pipeline. Focus on your code, not configuration.
            </p>
          </div>
          <div className="audience-card">
            <h3>DevOps Engineers</h3>
            <p>
              Standardize across 50 teams. Use DevOps-OS as your scaffold tool—generate configs 
              fast, maintain consistency, let AI handle the boilerplate.
            </p>
          </div>
          <div className="audience-card">
            <h3>SRE Teams</h3>
            <p>
              Generate monitoring and alerting setups in minutes. Stop writing dashboard YAML 
              by hand. Define once, scale everywhere.
            </p>
          </div>
          <div className="audience-card">
            <h3>Learning Developers</h3>
            <p>
              Understand DevOps by doing. Generate configs, see how they work, learn the 
              Process-First SDLC philosophy through runnable examples.
            </p>
          </div>
        </div>
      </section>

      {/* Technical Details - No Fluff */}
      <section className="technical-section">
        <h2>How It Works (The Real Details)</h2>
        <div className="technical-content">
          <div className="tech-step">
            <div className="tech-number">1</div>
            <div className="tech-text">
              <h3>Install DevOps-OS MCP</h3>
              <p>
                Add DevOps-OS as an MCP server to Claude Desktop, ChatGPT, Cursor, or VS Code. 
                One configuration file, that's it.
              </p>
            </div>
          </div>

          <div className="tech-step">
            <div className="tech-number">2</div>
            <div className="tech-text">
              <h3>Describe What You Need</h3>
              <p>
                Chat with Claude or ChatGPT in plain English. "I need a GitHub Actions workflow 
                that tests my Python app and deploys it to ECS." That's all.
              </p>
            </div>
          </div>

          <div className="tech-step">
            <div className="tech-number">3</div>
            <div className="tech-text">
              <h3>Get Production-Ready Config</h3>
              <p>
                DevOps-OS generates YAML that's ready to use. No tweaking required. Copy it, 
                commit it, deploy it.
              </p>
            </div>
          </div>

          <div className="tech-step">
            <div className="tech-number">4</div>
            <div className="tech-text">
              <h3>Learn as You Go</h3>
              <p>
                Each generated config includes explanations. Understand what you're shipping. 
                Modify with confidence. Build real expertise.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="tech-stack-section">
        <h2>Supports What You Actually Use</h2>
        <div className="tech-stack">
          <div className="tech-category">
            <h3>CI/CD</h3>
            <div className="tech-list">
              <span>GitHub Actions</span>
              <span>GitLab CI</span>
              <span>Jenkins</span>
            </div>
          </div>
          <div className="tech-category">
            <h3>GitOps</h3>
            <div className="tech-list">
              <span>ArgoCD</span>
              <span>Flux CD</span>
              <span>Kustomize</span>
            </div>
          </div>
          <div className="tech-category">
            <h3>Infrastructure</h3>
            <div className="tech-list">
              <span>Kubernetes</span>
              <span>Docker</span>
              <span>Terraform</span>
            </div>
          </div>
          <div className="tech-category">
            <h3>Observability</h3>
            <div className="tech-list">
              <span>Prometheus</span>
              <span>Grafana</span>
              <span>Loki</span>
            </div>
          </div>
          <div className="tech-category">
            <h3>Languages</h3>
            <div className="tech-list">
              <span>Python</span>
              <span>Go</span>
              <span>Node.js</span>
              <span>Java</span>
            </div>
          </div>
        </div>
      </section>

      {/* Process-First Philosophy */}
      <section className="philosophy-section">
        <h2>Built on Process-First Thinking</h2>
        <div className="philosophy-content">
          <p>
            DevOps-OS isn't just a code generator. It's built around the <strong>Process-First SDLC philosophy</strong>—
            the idea that good processes lead to good outcomes.
          </p>
          <p>
            Every tool, every template, every generated config teaches you:
          </p>
          <ul className="philosophy-list">
            <li><strong>Why</strong> certain patterns matter (not just what to copy)</li>
            <li><strong>How</strong> different tools fit together</li>
            <li><strong>When</strong> to apply different strategies</li>
            <li><strong>What</strong> to monitor and why</li>
          </ul>
          <p>
            You're not just getting code. You're learning DevOps through real, working examples.
          </p>
        </div>
      </section>

      {/* Call to Action */}
      <section className="cta-section">
        <div className="cta-content">
          <h2>Ready to Stop Writing Boilerplate?</h2>
          <p>
            Check out the GitHub repository, read the docs, and try it with Claude Desktop today.
          </p>
          <div className="cta-buttons">
            <a href="https://github.com/chefgs/devops_os_mcp" className="button button-primary">
              View on GitHub
            </a>
            <a href="https://github.com/chefgs/devops_os_mcp#getting-started" className="button button-secondary">
              Getting Started Guide
            </a>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  )
}
