Deploy Guide

Local
1) Backend
   - cd backend
   - python -m venv .venv && source .venv/bin/activate
   - pip install -r requirements.txt
   - export GEMINI_API_KEY=... (keep private)
   - uvicorn server:app --host 0.0.0.0 --port 8000

2) Frontend
   - Open frontend/index.html directly or serve:
     python -m http.server -d frontend 5173

Cloud (Vercel + Cloud Run, example)
- Backend: Google Cloud Run
  1. Add a Dockerfile in backend (if needed)
  2. Set env var GEMINI_API_KEY in service config
  3. Allow unauthenticated invocation

- Frontend: Vercel static deploy
  1. Import repo into Vercel
  2. Set frontend as output dir
  3. Configure env FRONTEND_API_BASE to Cloud Run URL and replace in app.js if desired

Security
- Never expose GEMINI_API_KEY client-side.
- Rate limit the backend if opening publicly.

