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

## Feature overview

### Matchmaking & lobby management

- **Random queue or invite-only rooms.** The `SessionRegistry` creates lobbies on demand and pairs random players automatically, while hosts can generate six-character invite codes for private matches. Each lobby tracks who has connected, their role, and whether they are ready to progress past the lobby/veto/coin toss phases.
- **Cross-device session resume.** Participant metadata (name, role, connection state, elapsed time, warnings) is persisted server-side so reconnecting clients immediately receive the full snapshot via the `session:update` Socket.IO event.

### Topic discovery & selection

- **Gemini topic generation with fallbacks.** The backend requests three balanced prompts from Google Gemini (`backend/services/gemini.py`). When the API or key is unavailable, a curated fallback list ensures the app always has neutral topics to present.
- **Refresh limits and veto tracking.** Each session records how many topic refreshes have been used, enforcing the `TOPIC_REFRESH_LIMIT` set in the environment. Both sides can veto topics in real time; when only one option remains it is auto-selected.
- **Custom prompts for invites.** Invite-mode hosts can bypass suggestions entirely and propose bespoke topics, which are validated on the server before locking in.

### Debate room experience

- **Coin toss role assignment.** After a topic is chosen, the server swaps roles randomly to keep the debate fair, storing the result in session metadata so both clients see who argues pro vs. con.
- **Turn and total timers.** Dedicated turn + global timers (`backend/utils/timers.py`) emit countdown events to both clients. Expiring timers automatically switch turns or conclude the debate when the total duration is consumed.
- **Structured turn-taking.** Only the active speaker can submit a message; turns are recorded in the transcript with timestamps, duration, and speaker info, enabling accurate judging later.
- **In-line moderation.** Submitted messages are sanitized via `backend/utils/moderation.py`. Repeated violations increment warnings, notify the speaker, and can end the debate automatically once the configured warning cap is hit.

### AI-assisted judging & memory

- **Multi-step judging pipeline.** The `DebateJudge` class orchestrates Intake → Understand → Decide → Review → Deliver phases, logging each checkpoint. Gemini scores every argument, while local heuristics step in if the model is unreachable.
- **Time & participation penalties.** The Decide step subtracts points for missed turns or debates that overrun the allotted time, reinforcing pacing rules baked into the timers.
- **Memory via Qdrant.** After judging, every argument is embedded (deterministically hashed) and stored in Qdrant so future sessions can surface similar material or related evidence.
- **Opus workflow hook.** A stubbed workflow service allows deployments with Opus credentials to forward session summaries for automation or additional review.

### Reporting & exports

- **Rich in-app results view.** The React `Results` component shows overall winner, per-turn feedback, moderation flags, penalties, and judge rationale once the debate concludes.
- **One-click PDF export.** The backend renders a multi-page ReportLab document mirroring the UI: cover page, participants, transcript, per-argument notes, and a growth plan that can be downloaded at any time post-judging.

### Front-end UX highlights

- **Lobby & waiting room.** `Lobby.jsx` and `WaitingRoom.jsx` help players name themselves, pick matchmaking mode, monitor opponent readiness, and share invite codes.
- **Topic selection workflow.** `TopicSelection.jsx` and `TopicPrompt.jsx` surface Gemini suggestions, veto choices, and custom topic submission with animated state changes as Socket.IO events arrive.
- **Debate dashboard.** `DebateRoom.jsx` combines timers, transcript history, moderation banners, and the rich-text composer into a single responsive view tuned for laptops and tablets.
- **Coin toss animation.** `CoinToss.jsx` adds a brief celebratory interlude between topic lock-in and the first turn so both players see their assigned stance before the timers start.

### Deployment-friendly configuration

- **Environment-driven behavior.** Everything from timer lengths to allowed CORS origins is configured via env vars (see `backend/config.py`), making the stack portable across local machines, containers, and managed platforms.
- **Graceful fallbacks.** Missing secrets (Gemini, Qdrant, Opus) trigger deterministic fallback modes so hackathon demos remain functional without every integration enabled.

## Deployment Notes

- Build the front-end with `npm run build` and host the static `dist/` directory.
- Deploy the backend with Eventlet-enabled workers. From the `backend/` directory run
  `gunicorn --worker-class eventlet -w 1 server:socketio`; if starting from the repo root,
  reference the fully qualified module path instead (`backend.server:socketio`).
- Provide secrets via your hosting platform (e.g. Cloud Run secrets or GitHub Actions environment).

## Contributing

This hackathon scaffold focuses on demonstrating integrations. Contributions adding tests, accessibility improvements, or tighter API error handling are welcome.
