# Git Setup for Mission Control

Mission Control is a custom Next.js dashboard for managing OpenClaw agents. It's NOT part of the OpenClaw installation - it's your custom application.

## Current Status
✅ Git repository initialized
✅ Initial commit created
⏳ Remote repository needs to be set up

## To Push to GitHub:

1. Create a new repository on GitHub (don't initialize with README/license/gitignore)

2. Add the remote:
```bash
git remote add origin https://github.com/YOUR_USERNAME/openclaw-mission-control.git
```

3. Push to remote:
```bash
git push -u origin master
```

## Directory Structure
This project lives at: `/Users/durdan/.openclaw/workspace/mission-control/`

## What This Is
- Custom Next.js dashboard for monitoring OpenClaw agents
- Provides UI for:
  - Agent status monitoring
  - Task management
  - Project tracking
  - Activity logs

## Development
```bash
npm run dev    # Start development server
npm run build  # Build for production
npm run lint   # Run linter
```

## Managing Updates
Since this is YOUR custom app (not OpenClaw native), you can:
- Modify it freely
- Add features as needed
- Keep it in your own git repository
- Deploy it wherever you want (Vercel, self-hosted, etc.)

## Important Notes
- The `.gitignore` excludes node_modules and .next build files
- Environment variables (.env files) are ignored by git
- The data/ directory contains JSON files for local data storage