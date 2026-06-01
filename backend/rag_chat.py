"""
RAG chat module — single video Q&A with conversation memory.
Uses LangChain ChatGoogleGenerativeAI + manual ConversationBufferMemory.
Supports both streaming (SSE generator) and non-streaming modes.
"""

from __future__ import annotations

import json
import os
from typing import Generator

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from vector_store import search_transcript

load_dotenv()

# ---------------------------------------------------------------------------
# In-memory conversation history store
# Format: {session_id: {video_id: [{"role": "user"|"assistant", "content": str}]}}
# ---------------------------------------------------------------------------
_history_store: dict[str, dict[str, list[dict]]] = {}


def _get_history(session_id: str, video_id: str) -> list[dict]:
    if session_id not in _history_store:
        _history_store[session_id] = {}
    if video_id not in _history_store[session_id]:
        _history_store[session_id][video_id] = []
    return _history_store[session_id][video_id]


def reset_memory(session_id: str):
    """Clear all conversation history for a session."""
    _history_store.pop(session_id, None)


def _build_llm(streaming: bool = False) -> ChatGroq:
    return ChatGroq(
        model_name="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_tokens=1024,
    )


def _fmt_meta(m: dict) -> str:
    """Format metadata nicely for the LLM."""
    if not m:
        return "No metadata available."
    views = m.get("views")
    views_str = f"{views:,}" if views is not None else "Hidden"
    likes = m.get("likes", 0)
    comments = m.get("comments", 0)
    followers = m.get("follower_count")
    er_str = f"{m.get('engagement_rate', 0):.4f}%" if views else "N/A"
    hashtags = " ".join(m.get("hashtags", [])) if m.get("hashtags") else "None"

    return (
        f"  Title: {m.get('title')}\n"
        f"  Creator: {m.get('creator', 'Unknown')}"
        + (f" | Followers: {followers:,}" if followers else "")
        + "\n"
        f"  Views: {views_str} | Likes: {likes:,} | Comments: {comments:,}\n"
        f"  Engagement Rate: {er_str}\n"
        f"  Duration: {m.get('duration', 0)}s | Uploaded: {m.get('upload_date', 'N/A')}\n"
        f"  Hashtags: {hashtags}"
    )

def _build_messages(
    question: str,
    video_id: str,
    video: dict,
    history: list[dict],
    docs: list,
) -> list:
    """Build the LangChain message list with context + history."""
    context = "\n\n".join(
        f"[Video {d.metadata.get('video_id', video_id)} | Chunk {d.metadata.get('chunk_id', i)}]\n{d.page_content}"
        for i, d in enumerate(docs)
    )

    meta_str = _fmt_meta(video.get("metadata", {})) if video else "No metadata available."

    system_msg = SystemMessage(content=f"""You are an expert video content analyst specialising in social media performance.

You are answering questions about Video {video_id}.

Video Metadata:
{meta_str}

Always cite which transcript chunk supports your answer using the notation: [Video {video_id} | Chunk N].
If the user asks about creator or metrics, refer to the Video Metadata above.
Be concise, insightful, and actionable.

Relevant transcript context:
{context}""")

    messages = [system_msg]

    # Add conversation history
    for turn in history[-6:]:  # keep last 6 turns to stay within context limits
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))

    messages.append(HumanMessage(content=question))
    return messages


# ---------------------------------------------------------------------------
# Non-streaming ask
# ---------------------------------------------------------------------------
def ask_rag(question: str, video_id: str, video: dict, session_id: str = "default") -> dict:
    history = _get_history(session_id, video_id)
    docs = search_transcript(question, video_id, k=4)

    messages = _build_messages(question, video_id, video, history, docs)
    llm = _build_llm(streaming=False)
    
    from retry_utils import with_rate_limit_retry
    
    @with_rate_limit_retry
    def _invoke():
        return llm.invoke(messages)
        
    response = _invoke()
    answer = response.content

    # Persist to history
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    citations = [
        {
            "video_id": d.metadata.get("video_id", video_id),
            "chunk_id": d.metadata.get("chunk_id", i),
            "text": d.page_content[:200],
        }
        for i, d in enumerate(docs)
    ]

    return {"answer": answer, "citations": citations}


# ---------------------------------------------------------------------------
# Streaming ask — yields SSE-formatted lines
# ---------------------------------------------------------------------------
def ask_rag_stream(
    question: str, video_id: str, video: dict, session_id: str = "default"
) -> Generator[str, None, None]:
    """Yield SSE lines: 'data: <token>\\n\\n', then citations event, then done."""
    history = _get_history(session_id, video_id)
    docs = search_transcript(question, video_id, k=4)

    messages = _build_messages(question, video_id, video, history, docs)
    llm = _build_llm(streaming=True)

    full_answer = ""
    try:
        # Faking the stream to prevent FastAPI threadpool hangs with httpx
        res = llm.invoke(messages)
        token = res.content
        if token:
            full_answer += token
            safe = token.replace("\n", "\\n")
            yield f"data: {safe}\n\n"
    except Exception as e:
        key_hint = os.environ.get("GROQ_API_KEY", "")[-4:]
        yield f"data: ⚠️ Error (Key ending in {key_hint}): {str(e).replace(chr(10), ' ')}\n\n"

    # Persist to history
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": full_answer})

    citations = [
        {
            "video_id": d.metadata.get("video_id", video_id),
            "chunk_id": d.metadata.get("chunk_id", i),
            "text": d.page_content[:200],
        }
        for i, d in enumerate(docs)
    ]
    yield f"event: citations\ndata: {json.dumps(citations)}\n\n"
    yield "event: done\ndata: [DONE]\n\n"