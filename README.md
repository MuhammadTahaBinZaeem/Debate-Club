# Letsee Debate Platform

Letsee is a two-player, AI-assisted debate experience that combines real-time messaging, Gemini topic suggestions, an Opus-style judging pipeline, and Qdrant-powered memory.

## Project Structure

```
backend/   # Flask + Socket.IO API and services
frontend/  # Vite + React single-page app
```

## Quick Start

### Backend

#### macOS / Linux (bash)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

#### Windows (PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
python server.py
```

Environment variables (e.g. stored in `.env`) configure API keys and time limits:

- `GEMINI_API_KEY` – Google Gemini key for topic generation and judging.
- `QDRANT_URL`, `QDRANT_API_KEY` – Qdrant vector database credentials.
- `OPUS_API_KEY`, `OPUS_WORKFLOW_ID` – optional Opus workflow integration.
- `TURN_SECONDS`, `TOTAL_SECONDS`, `MAX_TURNS` – customise timers.
- `CORS_ORIGINS` – allowed front-end origins.

### Front-end

#### macOS / Linux (bash)

```bash
cd frontend
npm install
npm run dev
```

#### Windows (PowerShell)

```powershell
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` (default `http://localhost:8000/api`) and `VITE_SOCKET_URL` to point at the backend.

## Features

- Random and invite-based matchmaking with lobby status.
- Gemini-assisted topic suggestions with per-side vetoes or custom topics.
- Turn-based debate interface with per-turn and overall timers.
- Opus-inspired judging pipeline that logs each phase and applies rule-based penalties.
- Qdrant memory store for argument embeddings and similar-content lookups.
- ReportLab PDF export summarising the transcript and AI scores.

## Deployment Notes

- Build the front-end with `npm run build` and host the static `dist/` directory.
- Deploy the backend with Eventlet-enabled workers (`gunicorn --worker-class eventlet -w 1 backend.server:socketio`).
- Provide secrets via your hosting platform (e.g. Cloud Run secrets or GitHub Actions environment).

## Contributing

This hackathon scaffold focuses on demonstrating integrations. Contributions adding tests, accessibility improvements, or tighter API error handling are welcome.
