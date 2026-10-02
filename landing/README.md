# DevOps-OS MCP Landing Page

A humanistic, authentic landing page for the DevOps-OS MCP Server built with Next.js.

## Philosophy

This landing page is designed with **humanistic UX principles**:

- **Authentic**: Speaks directly about real problems developers face, not marketing fluff
- **Clarity-First**: No unnecessary animations, gradients, or trendy patterns
- **Human-Focused**: Focuses on solving real problems, not showcasing technology
- **Accessible**: Clean typography, proper contrast, readable at all sizes
- **Functional**: Every element has a purpose; form follows function

## Features

- ✨ No AI slop UI patterns (avoiding trendy but hollow design)
- 🎯 Problem-focused content (real use cases and solutions)
- 📱 Fully responsive design
- ♿ Semantic HTML for accessibility
- ⚡ Fast and lightweight
- 🎨 Cohesive design system with CSS variables

## Tech Stack

- **Next.js 14+** - React framework
- **Vanilla CSS** - No heavy CSS frameworks
- **No external dependencies** - Just React and Next.js

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd landing
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view it.

### Build

```bash
npm run build
npm start
```

## Project Structure

```
landing/
├── app/
│   ├── page.jsx           # Main landing page
│   ├── layout.jsx         # Root layout
│   ├── styles/
│   │   └── globals.css    # Design system & styles
│   └── components/
│       ├── Header.jsx     # Navigation
│       └── Footer.jsx     # Footer
├── package.json
├── next.config.js
└── README.md
```

## Design System

The design system uses CSS custom properties for a consistent, maintainable approach:

- **Colors**: Semantic naming (primary, secondary, accent, success)
- **Spacing**: 8px base unit system
- **Typography**: System fonts for speed and familiarity
- **Interactions**: Subtle transitions for clarity, not distraction

### Key Design Decisions

1. **No gradients or unnecessary effects** - They distract from content
2. **Semantic color usage** - Colors convey meaning, not just aesthetics
3. **Proper spacing hierarchy** - Breathing room between sections
4. **Accessible typography** - Proper contrast ratios, readable font sizes
5. **Responsive by default** - Mobile-first approach

## Sections

1. **Header** - Clean navigation with brand identity
2. **Hero** - Problem statement and immediate value
3. **Real Problems** - Honest look at DevOps challenges
4. **Features** - What DevOps-OS actually does
5. **Audience** - Who this is built for
6. **Technical Details** - How it works (step-by-step)
7. **Tech Stack** - Supported tools and technologies
8. **Philosophy** - Process-First thinking
9. **CTA** - Call to action
10. **Footer** - Links and community

## Deployment

### Vercel (Recommended)

```bash
npm install -g vercel
vercel
```

### Docker

```bash
docker build -t devops-os-landing .
docker run -p 3000:3000 devops-os-landing
```

### Traditional Node.js

```bash
npm run build
npm start
```

## Contributing

Feedback and improvements are welcome! The philosophy of this landing page is **humanistic UX**, so please:

- Keep content honest and problem-focused
- Avoid trendy design patterns
- Maintain accessibility standards
- Keep the design clean and purposeful

## License

MIT - Same as the main DevOps-OS MCP project

## Links

- [DevOps-OS MCP Repository](https://github.com/chefgs/devops_os_mcp)
- [Original DevOps-OS CLI](https://github.com/cloudengine-labs/devops_os)
- [Process-First SDLC Philosophy](https://github.com/chefgs/devops_os_mcp#readme)
