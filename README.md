# 🎬 RAG Video Analyst

A full-stack RAG (Retrieval-Augmented Generation) chatbot that analyzes two social media videos side-by-side — comparing engagement, transcripts, creator metrics, and providing AI-powered improvement suggestions.

## Features

- **Dual video analysis** — YouTube + Instagram Reels (or any yt-dlp supported URL)
- **Whisper transcription** — Automatic speech recognition via OpenAI Whisper (base model)
- **ChromaDB vector store** — Transcript chunks embedded with `all-MiniLM-L6-v2` (HuggingFace)
- **LangChain RAG** — `ChatGoogleGenerativeAI` (Gemini 2.5 Flash) with vector retrieval
- **Conversation memory** — Multi-turn chat with per-session history across tabs
- **Streaming responses** — Server-Sent Events (SSE) for real-time token streaming
- **Source citations** — Every answer cites which video + which chunk it's based on
- **Engagement rate** — `(likes + comments) / views × 100` with full metadata display
- **Modern frontend** — Next.js 16, glassmorphism design, side-by-side cards + chat panel

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript |
| Backend | FastAPI + Python 3.x |
| Orchestration | LangChain (`langchain-google-genai`, `langchain-core`) |
| LLM | Gemini 2.5 Flash (via Google AI Studio) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace, free) |
| Vector DB | ChromaDB (local persistence) |
| Transcription | OpenAI Whisper `base` model |
| Downloader | yt-dlp (YouTube + Instagram + 1000+ sites) |

## Why This Stack?

- **ChromaDB** — Zero infra cost, runs locally, production-ready for ~10K docs. At 1000 creators/day, migrate to Qdrant Cloud (~$0.02/M vectors) for horizontal scaling.
- **Whisper base** — Free, runs on CPU. At scale, swap for AssemblyAI ($0.00025/min) or Groq Whisper API for 10× speed.
- **Gemini 2.5 Flash** — Best cost/quality ratio. ~$0.0004 input / $0.0016 output per 1K tokens vs GPT-4o at 30× the cost.
- **all-MiniLM-L6-v2** — 80MB model, ~500ms on CPU per batch. At scale, swap for Cohere Embed v3 ($0.0001/1K tokens) for superior multilingual support.
- **Chunk size 500 / overlap 50** — Tuned for social media transcripts (short sentences). Larger chunks reduce retrieval precision; smaller chunks lose context.

## Scalability at 1000 Creators/Day

| Bottleneck | Current | At Scale |
|---|---|---|
| Transcription | Whisper base, ~2× realtime | AssemblyAI API, async, $0.0065/min |
| Embeddings | Local model | Batch via Cohere/OpenAI API |
| Vector DB | ChromaDB local | Qdrant Cloud / Pinecone |
| LLM | Gemini 2.5 Flash | Same — already optimal cost |
| Queue | None (sync) | Celery + Redis / BullMQ |

Estimated cost per video analysis at scale: **~$0.03–0.05** (dominated by transcription + LLM tokens).

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- FFmpeg (required by Whisper for audio conversion)

### Backend

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install fastapi uvicorn python-dotenv yt-dlp openai-whisper \
    langchain langchain-google-genai langchain-community langchain-core \
    langchain-text-splitters chromadb sentence-transformers

# Configure environment
cp .env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY

# Start backend
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:3000

## Usage

1. Paste a **YouTube URL** into Video A field
2. Paste a **YouTube or Instagram Reel URL** into Video B field
3. Click **🚀 Analyze Both Videos** (takes 1–3 min depending on video length)
4. Explore the side-by-side metadata cards
5. Use the **Compare** tab to ask cross-video questions with streaming AI responses
6. Switch to **Video A / B** tabs for per-video deep-dives
7. Click source citations to expand the transcript chunks used

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/analyze` | Download, transcribe, embed both videos |
| POST | `/chat/stream` | Streaming single-video Q&A (SSE) |
| POST | `/compare/stream` | Streaming cross-video comparison (SSE) |
| POST | `/chat` | Non-streaming single-video Q&A |
| POST | `/compare` | Non-streaming comparison |
| POST | `/reset` | Clear conversation memory for a session |
| GET | `/status` | Check which videos are loaded |

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key (free tier available) |
