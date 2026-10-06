# Deployment Guide for DevOps-OS MCP Landing Page

This guide covers multiple deployment options for the DevOps-OS MCP landing page.

## Table of Contents

1. [Local Development](#local-development)
2. [Vercel (Recommended)](#vercel-recommended)
3. [Docker](#docker)
4. [Traditional Node.js Server](#traditional-nodejs-server)
5. [GitHub Pages (Static Export)](#github-pages-static-export)
6. [Environment Variables](#environment-variables)

---

## Local Development

### Prerequisites

- Node.js 18+ ([Download](https://nodejs.org/))
- npm or yarn

### Setup

```bash
cd landing
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### Development Commands

- `npm run dev` - Start development server with hot-reload
- `npm run build` - Create production build
- `npm start` - Start production server
- `npm run lint` - Run ESLint

---

## Vercel (Recommended)

Vercel is the official Next.js hosting platform. It's the easiest and most straightforward option.

### Option 1: Deploy via CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd landing
vercel

# Follow the prompts
```

### Option 2: GitHub Integration

1. Push to GitHub: `git push origin`
2. Go to [vercel.com](https://vercel.com)
3. Click "New Project"
4. Select your GitHub repository
5. Root Directory: `landing`
6. Click "Deploy"

Vercel will automatically:
- Build on every push
- Deploy previews for PRs
- Handle SSL certificates
- Provide CDN distribution

### Vercel Environment Variables

If needed, set via Vercel dashboard:
1. Project Settings → Environment Variables
2. Add variables for development/preview/production

---

## Docker

### Build and Run

```bash
# Build image
docker build -t devops-os-landing .

# Run container
docker run -p 3000:3000 devops-os-landing

# Visit http://localhost:3000
```

### Using Docker Compose

```bash
# Start service
docker-compose up --build

# Stop service
docker-compose down
```

### Dockerfile Details

The included `Dockerfile`:
- Uses multi-stage build for optimized size
- Node 20-alpine as base (lightweight)
- Installs dependencies
- Builds Next.js application
- Runs only production dependencies in final stage

### Docker Registry (Docker Hub/ECR)

```bash
# Build with tag
docker build -t your-username/devops-os-landing:latest .

# Push to Docker Hub
docker login
docker push your-username/devops-os-landing:latest

# Pull and run on server
docker pull your-username/devops-os-landing:latest
docker run -d -p 3000:3000 your-username/devops-os-landing:latest
```

---

## Traditional Node.js Server

### Prerequisites

- Node.js 18+
- A server with SSH access

### Deployment Steps

```bash
# On your local machine
npm run build

# Copy to server
scp -r .next package.json package-lock.json user@server:/app/landing/

# On the server
cd /app/landing
npm ci --only=production
npm start

# Server runs on http://localhost:3000
```

### Using PM2 (Process Manager)

```bash
# On server - Install PM2
npm install -g pm2

# Create ecosystem config
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'devops-os-landing',
    script: 'npm',
    args: 'start',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
EOF

# Start with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

# Monitor
pm2 monit
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/devops-os-landing

upstream landing_backend {
    server localhost:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://landing_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/devops-os-landing /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### SSL with Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

---

## GitHub Pages (Static Export)

If you want to serve as static content on GitHub Pages:

### Modify next.config.js

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',  // Static export
  basePath: '/devops_os_mcp',  // If serving from subdirectory
}

module.exports = nextConfig
```

### Build and Deploy

```bash
npm run build

# Files are in `out/` directory
# Push to gh-pages branch:
git add out/
git commit -m "Deploy static site"
git subtree push --prefix out origin gh-pages
```

### GitHub Pages Settings

1. Go to repository Settings
2. Pages → Build and deployment
3. Source: Deploy from a branch
4. Branch: `gh-pages` / `/(root)`

---

## Environment Variables

### Development (.env.local)

```bash
# Development only
NEXT_PUBLIC_API_URL=http://localhost:3000
```

### Production

**For Vercel:** Set in Project Settings → Environment Variables

**For Docker/Node:**
```bash
export NODE_ENV=production
npm start
```

### Available Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_ENV` | Environment mode | production |
| `PORT` | Server port | 3000 |
| `NEXT_PUBLIC_*` | Public environment variables | - |

---

## Performance Optimization

### Cache Headers

For production, set proper cache headers:

```nginx
# Nginx example
location /_next/static {
    expires 365d;
    add_header Cache-Control "public, max-age=31536000, immutable";
}

location / {
    add_header Cache-Control "public, max-age=3600";
}
```

### Image Optimization

Next.js automatically optimizes images. To enable:

```javascript
// next.config.js
const nextConfig = {
  images: {
    formats: ['image/avif', 'image/webp'],
  },
}
```

### Monitoring

- **Vercel Analytics**: Built-in
- **Sentry**: For error tracking
- **New Relic**: For performance monitoring

---

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 3000
sudo lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 npm start
```

### Build Fails

```bash
# Clear build cache
rm -rf .next
npm install
npm run build
```

### Docker Image Too Large

```bash
# Prune unused images
docker image prune

# Check size
docker images | grep devops-os-landing
```

### Nginx 502 Bad Gateway

- Check Node.js is running: `pm2 status`
- Verify upstream: `curl http://localhost:3000`
- Check logs: `pm2 logs`

---

## Quick Reference Commands

```bash
# Local
npm run dev              # Start dev server
npm run build            # Build for production
npm start                # Start production server

# Docker
docker build -t landing .
docker run -p 3000:3000 landing
docker-compose up

# Deployment
vercel                   # Deploy to Vercel
pm2 start ecosystem.config.js  # Start with PM2
```

---

## Support & Resources

- [Next.js Deployment Docs](https://nextjs.org/docs/deployment)
- [Vercel Docs](https://vercel.com/docs)
- [Docker Docs](https://docs.docker.com/)
- [PM2 Docs](https://pm2.keymetrics.io/docs)
