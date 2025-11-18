# Letsee Debate Backend

This Flask + Socket.IO service provides matchmaking, topic selection, real-time debating, AI-assisted judging, and PDF export for the Letsee debate platform.

## Features

- **Matchmaking** for random and invite-only debates.
- **Gemini integration** for topic generation and AI scoring with offline fallbacks.
- **Opus-inspired judging pipeline** that logs each stage of the decision-making process.
- **Qdrant memory** to persist argument embeddings for future recommendations.
- **ReportLab PDF export** for transcripts and final scores.
- **Socket.IO** real-time events for vetoes, timers, and argument exchange.

## Getting Started

1. Create a virtual environment and install dependencies:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure environment variables (either via `.env` or your shell):

   ```bash
   export GEMINI_API_KEY=your_google_gemini_key
   export QDRANT_URL=https://<cluster>.cloud.qdrant.io
   export QDRANT_API_KEY=your_qdrant_key
   export OPUS_API_KEY=optional_opus_key
   export OPUS_WORKFLOW_ID=optional_workflow_id
   export APP_PORT=8000
   export CORS_ORIGINS=http://localhost:5173
   ```

   Secrets are **not** committed to the repository. The service gracefully falls back to deterministic logic when APIs are unavailable.

3. Run the development server:

   ```bash
   python server.py
   ```

   The REST API is available at `http://localhost:8000/api` and the Socket.IO namespace shares the same origin.

## Key Endpoints

| Method | Route | Description |
| ------ | ----- | ----------- |
| `POST` | `/api/sessions/create` | Create an invite-only lobby and return the session identifier. |
| `POST` | `/api/sessions/join/random` | Join or create a random matchmaking lobby. |
| `POST` | `/api/sessions/join/invite` | Join by invite code. |
| `GET`  | `/api/topics/<session_id>` | Retrieve (or generate) topic options via Gemini. |
| `POST` | `/api/sessions/<session_id>/topic` | Confirm the debate topic (supports custom topic for invites). |
| `POST` | `/api/sessions/<session_id>/finish` | Trigger the judging pipeline and persist results. |
| `GET`  | `/api/export/<session_id>` | Download the transcript and results as a PDF. |

Real-time events (`join_session`, `veto_topic`, `send_message`, `end_debate`, etc.) are described inline in `routes/websocket.py`.

## Deployment Notes

- The app is fully compatible with Gunicorn + Eventlet or with Google Cloud Run. A sample command:

  ```bash
  gunicorn --worker-class eventlet -w 1 server:socketio --bind 0.0.0.0:8000
  ```

  > **Tip:** Run this command from the `backend/` directory. If you prefer launching
  > from the monorepo root, reference the fully qualified module path instead
  > (`backend.server:socketio`).

- Ensure that environment variables are provided securely (e.g., via Cloud Run secrets).
- When deploying behind HTTPS, update `CORS_ORIGINS` to include the production front-end URL.

## Tests and Linting

Automated tests are not included in this hackathon scaffold. Consider adding unit tests for the session registry and judging pipeline as the project evolves.
