'use client'

import React from 'react'

export default function Footer() {
  const currentYear = new Date().getFullYear()
  
  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4>DevOps-OS MCP</h4>
          <p>
            Open-source MCP server for generating production-ready DevOps configurations 
            using Claude, ChatGPT, or any MCP-compatible AI assistant.
          </p>
        </div>
        
        <div className="footer-section">
          <h4>Links</h4>
          <ul className="footer-links">
            <li><a href="https://github.com/chefgs/devops_os_mcp">GitHub Repository</a></li>
            <li><a href="https://github.com/chefgs/devops_os_mcp#readme">Documentation</a></li>
            <li><a href="https://github.com/cloudengine-labs/devops_os">Original DevOps-OS CLI</a></li>
            <li><a href="https://github.com/chefgs/devops_os_mcp/blob/main/LICENSE">License (MIT)</a></li>
          </ul>
        </div>

        <div className="footer-section">
          <h4>Community</h4>
          <ul className="footer-links">
            <li><a href="https://github.com/chefgs/devops_os_mcp/issues">Report Issues</a></li>
            <li><a href="https://github.com/chefgs/devops_os_mcp/discussions">Discussions</a></li>
            <li><a href="https://github.com/chefgs/devops_os_mcp/blob/main/CONTRIBUTING.md">Contributing</a></li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom">
        <p>
          © {currentYear} DevOps-OS Contributors. Built with care for people who value their time.
        </p>
      </div>
    </footer>
  )
}
