from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pipeline import process_video
from rag_chat import ask_rag, ask_rag_stream, reset_memory
from compare_chat import compare_videos, compare_videos_stream

app = FastAPI(title="RAG Video Chatbot API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory video state  (survives server lifetime)
VIDEO_STORE: dict[str, dict] = {}

import requests
from fastapi.responses import Response

@app.get("/proxy-image")
def proxy_image(url: str):
    try:
        resp = requests.get(url, timeout=5)
        return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to load image")


# ─── Health ─────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"status": "ok", "message": "RAG Video Chatbot API v2"}


# ─── Analyze ─────────────────────────────────────────────────────────────────

class VideoInput(BaseModel):
    videoA: str
    videoB: str


@app.post("/analyze")
def analyze(data: VideoInput):
    try:
        video_a = process_video(data.videoA, "A")
        video_b = process_video(data.videoB, "B")
        VIDEO_STORE["A"] = video_a
        VIDEO_STORE["B"] = video_b
        return {"videoA": video_a, "videoB": video_b, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Single-video chat (streaming) ───────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    video_id: str          # "A" or "B"
    session_id: str = "default"


@app.post("/chat")
def chat(data: ChatRequest):
    """Non-streaming chat — returns full answer + citations."""
    video = VIDEO_STORE.get(data.video_id)
    if not video:
        raise HTTPException(status_code=400, detail="Video not analyzed yet.")
    result = ask_rag(data.question, data.video_id, video, data.session_id)
    return result


@app.post("/chat/stream")
def chat_stream(data: ChatRequest):
    """Streaming chat — SSE response."""
    video = VIDEO_STORE.get(data.video_id)
    if not video:
        raise HTTPException(status_code=400, detail="Video not analyzed yet.")
    gen = ask_rag_stream(data.question, data.video_id, video, data.session_id)
    return StreamingResponse(gen, media_type="text/event-stream")


# ─── Compare (streaming) ─────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    question: str
    session_id: str = "default"


@app.post("/compare")
def compare(data: CompareRequest):
    """Non-streaming compare."""
    video_a = VIDEO_STORE.get("A")
    video_b = VIDEO_STORE.get("B")
    if not video_a or not video_b:
        raise HTTPException(status_code=400, detail="Videos not yet analyzed. Call /analyze first.")
    result = compare_videos(data.question, video_a, video_b)
    return result


@app.post("/compare/stream")
def compare_stream(data: CompareRequest):
    """Streaming compare — SSE response."""
    video_a = VIDEO_STORE.get("A")
    video_b = VIDEO_STORE.get("B")
    if not video_a or not video_b:
        raise HTTPException(status_code=400, detail="Videos not yet analyzed.")
    gen = compare_videos_stream(data.question, video_a, video_b)
    return StreamingResponse(gen, media_type="text/event-stream")


# ─── Memory management ───────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    session_id: str = "default"


@app.post("/reset")
def reset(data: ResetRequest):
    """Clear conversation memory for a session."""
    reset_memory(data.session_id)
    return {"status": "ok", "message": f"Memory cleared for session {data.session_id}"}


@app.get("/status")
def status():
    """Return which videos are currently loaded."""
    return {
        "videos_loaded": list(VIDEO_STORE.keys()),
        "video_a": VIDEO_STORE.get("A", {}).get("metadata", {}).get("title"),
        "video_b": VIDEO_STORE.get("B", {}).get("metadata", {}).get("title"),
    }