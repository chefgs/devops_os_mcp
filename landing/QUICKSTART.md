# Quick Start Guide

Get the DevOps-OS MCP landing page up and running in seconds.

## 🚀 Instant Setup (60 seconds)

### Option 1: Local Development (Fastest)

```bash
cd landing
npm install
npm run dev
```

→ Visit [http://localhost:3000](http://localhost:3000)

Stop with `Ctrl+C`

### Option 2: Vercel Deployment (Easiest)

```bash
# Install Vercel CLI (one-time)
npm install -g vercel

# Deploy
cd landing
vercel

# Follow prompts, done!
```

Visit your Vercel URL. Zero configuration needed.

### Option 3: Docker (Works Everywhere)

```bash
cd landing
docker build -t devops-os-landing .
docker run -p 3000:3000 devops-os-landing
```

→ Visit [http://localhost:3000](http://localhost:3000)

## 📝 Common Commands

```bash
# Development
npm run dev       # Start dev server on http://localhost:3000
npm run build     # Build for production
npm start         # Start production server
npm run lint      # Check code style

# Docker
docker build .                                    # Build image
docker run -p 3000:3000 <image-id>              # Run container
docker-compose up                                 # Docker Compose

# Production
npm run build && npm start                        # Manual production
pm2 start ecosystem.config.js                    # With PM2
```

## 📂 What's Inside

```
landing/
├── app/page.jsx              # Main landing page
├── app/styles/globals.css    # All styling
├── app/components/           # Header, Footer
├── Dockerfile                # Docker config
├── DEPLOYMENT.md             # Full deployment guide
├── DESIGN_PHILOSOPHY.md      # Design principles
├── README.md                 # Project info
└── package.json              # Dependencies
```

## 🎯 Next Steps After Setup

1. **View the page**: Open http://localhost:3000
2. **Edit content**: Modify `app/page.jsx` (changes auto-refresh)
3. **Change styling**: Edit `app/styles/globals.css`
4. **Deploy**: See DEPLOYMENT.md for full options

## 🌐 Deployment Options at a Glance

| Option | Effort | Cost | Time |
|--------|--------|------|------|
| **Vercel** | 30 sec | Free | Instant |
| **Docker** | 2 min | Varies | 2 min |
| **Node.js** | 5 min | Varies | 5 min |
| **GitHub Pages** | 3 min | Free | 3 min |

See **DEPLOYMENT.md** for detailed instructions.

## 🎨 Making Changes

### Edit Content

Open `app/page.jsx` and modify the text directly. Changes appear in your browser instantly (with dev server running).

### Edit Styles

Open `app/styles/globals.css`. Everything is organized by section:
- Colors and spacing at the top
- Components below
- Mobile responsive at the bottom

### Change Colors

In `globals.css`, update the CSS variables:

```css
:root {
  --color-primary: #000000;      /* Main brand color */
  --color-accent: #0066cc;       /* Links and highlights */
  --color-text: #1f2937;         /* Body text */
  /* ... */
}
```

### Adjust Spacing

Update the spacing scale in `globals.css`:

```css
--spacing-xs: 0.5rem;      /* 8px */
--spacing-sm: 1rem;        /* 16px */
--spacing-md: 1.5rem;      /* 24px */
/* ... */
```

All components automatically use these values.

## ✅ Verification Checklist

After setup:
- [ ] Dev server starts without errors
- [ ] Page loads at http://localhost:3000
- [ ] Navigation links work
- [ ] Page is readable on mobile (resize browser)
- [ ] Build completes: `npm run build`

## 🆘 Troubleshooting

### Port 3000 Already in Use

```bash
# Find and kill the process
sudo lsof -ti:3000 | xargs kill -9

# Or use a different port
PORT=3001 npm run dev
```

### Build Fails

```bash
# Clear cache and reinstall
rm -rf node_modules .next
npm install
npm run build
```

### Changes Not Showing

```bash
# Restart dev server
# Stop with Ctrl+C, then:
npm run dev
```

### Docker Issues

```bash
# Rebuild without cache
docker build --no-cache -t devops-os-landing .

# Or use Docker Compose
docker-compose down
docker-compose up --build
```

## 📖 Learn More

- **Design Philosophy**: Read `DESIGN_PHILOSOPHY.md`
- **Full Deployment Guide**: Read `DEPLOYMENT.md`
- **Project Details**: Read `README.md`
- **Next.js Docs**: https://nextjs.org/docs

## 🎓 Understanding the Structure

```
One page serves everything:
app/page.jsx → Renders all sections
app/styles/globals.css → All styling (no component CSS)
app/components/ → Header, Footer (shared sections)
```

Why this approach?
- **Simple**: Single file to edit for content
- **Fast**: No component overhead
- **Maintainable**: Everything organized by section
- **Responsive**: Mobile-first CSS approach

## 🚢 Ready to Ship?

```bash
# 1. Make your changes
npm run dev
# Edit and preview...

# 2. Build for production
npm run build

# 3. Choose deployment option:
vercel                           # Option A: Vercel (easiest)
docker build . && docker run ... # Option B: Docker
npm start                        # Option C: Node.js
```

## 💡 Pro Tips

- Use `npm run dev` for quick iteration
- Edit CSS variables for brand consistency
- Test on mobile: `npm run dev` then view on phone (use your computer's IP)
- Use `npm run lint` before committing
- Keep semantic HTML structure when editing

## Questions?

- **How do I change the domain?** Deploy to Vercel or your own server
- **Can I add analytics?** Yes, add to `app/layout.jsx`
- **Can I use Tailwind/Bootstrap?** Yes, but the current setup avoids them by design
- **How do I add more pages?** Create new files in `app/` directory
- **Is this SEO-optimized?** Yes, proper semantic HTML + Next.js rendering

---

**You're all set!** 🎉

Run `npm run dev` and start building the landing page.
