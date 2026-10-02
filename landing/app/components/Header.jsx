'use client'

import React from 'react'
import Link from 'next/link'

export default function Header() {
  return (
    <header className="header">
      <nav className="nav">
        <div className="nav-brand">
          <Link href="/" className="brand-link">
            <span className="brand-symbol">◆</span>
            <span className="brand-text">DevOps-OS</span>
          </Link>
        </div>
        <ul className="nav-menu">
          <li><a href="#how-it-works" className="nav-link">How It Works</a></li>
          <li><a href="https://github.com/chefgs/devops_os_mcp" className="nav-link">GitHub</a></li>
          <li><a href="https://github.com/chefgs/devops_os_mcp#readme" className="nav-link">Docs</a></li>
        </ul>
      </nav>
    </header>
  )
}
