# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Portrait Studio (AI 사진관) is a hackathon project that generates high-quality portrait photos using Gemini 2.5 Flash Image Preview. The system transforms user photos into professional headshots, passport photos, or memory-style portraits based on selected themes.

## Architecture

**Backend** (`/backend/`):
- FastAPI server (`server.py`) handling image generation requests
- Single endpoint: `POST /api/generate` accepting theme and base64 image
- Direct integration with Google's Gemini 2.5 Flash Image Preview API
- Supports three themes: `resume`, `passport`, `memory`
- Static file serving for generated outputs

**Frontend** (`/frontend/`):
- Vanilla JavaScript SPA with camera integration
- Components: camera capture (`components.js`), theme selection, image processing
- Direct base64 image encoding and API communication
- Real-time camera preview with capture functionality

**Core Data Flow**:
1. User captures/uploads image → base64 encoding
2. Theme selection (resume/passport/memory) 
3. API call to `/api/generate` with structured prompt
4. Gemini API generates styled portrait
5. Result returned as base64 with saved file URL

## Development Commands

**Backend Setup**:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your_key_here"
```

**Run Backend**:
```bash
uvicorn server:app --reload --port 8000
```

**Run Frontend**:
```bash
# Direct file opening
open frontend/index.html

# Or serve statically
python -m http.server -d frontend 5173
```

## Environment Setup

- Required: `GEMINI_API_KEY` environment variable
- Python 3.10+ required
- See `backend/.env.example` for environment template

## Key Implementation Details

**Prompt Engineering**: The `build_prompt()` function in `server.py` generates theme-specific prompts with consistent base instructions for portrait generation, identity preservation, and studio lighting.

**Image Processing**: Direct base64 handling without intermediate file storage during API calls. Generated images are saved to `static/outputs/` with UUID filenames.

**Theme Specifications**:
- `resume`: Professional attire, studio lighting, neutral background
- `passport`: Regulatory compliance, white background, neutral expression  
- `memory`: Film tone, warm colors, vintage aesthetic

**Security**: API key is server-side only, never exposed to frontend code.