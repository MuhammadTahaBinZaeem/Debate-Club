# Letsee Debate Front-end

This Vite + React application connects to the Letsee debate backend to provide matchmaking, topic selection, live debating, and AI-assisted results.

## Setup

```bash
cd frontend
npm install
npm run dev
```

By default the app expects the backend at `http://localhost:8000`. Configure different origins via environment variables:

```
VITE_API_BASE_URL=http://localhost:8000/api
VITE_SOCKET_URL=http://localhost:8000
```

Create a `.env` file in `frontend/` (or set shell variables) before running `npm run dev` to override the defaults.

## Key Screens

- **Lobby** – choose display name, join random matchmaking, or create/share an invite code.
- **Topic Selection** – fetch Gemini-suggested topics, veto picks, or propose a custom topic for invite matches.
- **Debate Room** – turn-based argument entry with live timers, transcript display, and manual end button.
- **Results** – shows AI scoring, penalties, and offers a PDF export.

## Deployment

Run `npm run build` to output static assets under `dist/`. Deploy to any static hosting provider (Cloudflare Pages, Netlify, Vercel, etc.) and set environment variables to point to the deployed backend.
