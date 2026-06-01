"""
Compare chat module — cross-video comparison using LangChain.
Retrieves chunks from both Video A and B via ChromaDB, builds a structured
grounded prompt, and streams or returns a full comparison analysis.
"""

from __future__ import annotations

import json
import os
from typing import Generator

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from vector_store import search_both_transcripts

load_dotenv()


def _build_llm(streaming: bool = False) -> ChatGroq:
    return ChatGroq(
        model_name="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_tokens=1024,
    )


def _fmt_meta(v: dict) -> str:
    m = v.get("metadata", {})
    er = v.get("engagement_rate")            # may be None for Instagram
    likes = m.get("likes", 0) or 0
    comments = m.get("comments", 0) or 0
    views = m.get("views")                   # may be None for Instagram
    followers = m.get("follower_count")
    hashtags = ", ".join(m.get("hashtags", [])[:8]) or "N/A"
    platform = m.get("platform", "unknown")

    views_str = f"{views:,}" if views is not None else "N/A (Instagram restricts view counts without auth)"
    if er is not None:
        er_str = f"{er}%  (= ({likes:,} likes + {comments:,} comments) / {views:,} views × 100)"
    else:
        er_str = f"N/A — views unavailable; interaction score = {likes + comments:,} (likes + comments)"

    return (
        f"  Title: {m.get('title', 'Unknown')}\n"
        f"  Platform: {platform}\n"
        f"  Creator: {m.get('creator', 'Unknown')}"
        + (f" | Followers: {followers:,}" if followers else "")
        + "\n"
        f"  Views: {views_str} | Likes: {likes:,} | Comments: {comments:,}\n"
        f"  Engagement Rate: {er_str}\n"
        f"  Duration: {m.get('duration', 0)}s | Uploaded: {m.get('upload_date', 'N/A')}\n"
        f"  Hashtags: {hashtags}"
    )


def _build_messages(question: str, video_a: dict, video_b: dict, context: str) -> list:
    system = SystemMessage(content=f"""You are an expert social media content analyst.

Video A metadata:
{_fmt_meta(video_a)}

Video B metadata:
{_fmt_meta(video_b)}

Relevant transcript excerpts (cite these with [Video A | Chunk N] or [Video B | Chunk N]):
{context}

Provide a structured analysis with these exact sections:
🏆 **Winner** — one sentence verdict  
📈 **Engagement Rate Comparison** — show exact numbers and difference  
🎯 **Why One Performed Better** — ground your reasoning in transcript evidence  
🎬 **Hook Analysis** — compare the opening 5 seconds of each video  
👤 **Creator Analysis** — creator profiles, follower counts, upload strategy  
💡 **Suggestions for the Lower-Performing Video** — specific & actionable  
📌 **Final Verdict** — one paragraph summary""")

    return [system, HumanMessage(content=question)]


def compare_videos(question: str, video_a: dict, video_b: dict) -> dict:
    """Non-streaming compare — returns answer + citations dict."""
    docs = search_both_transcripts(question, k_each=3)
    context = "\n\n".join(
        f"[Video {d.metadata.get('video_id')} | Chunk {d.metadata.get('chunk_id', i)}]\n{d.page_content}"
        for i, d in enumerate(docs)
    )

    messages = _build_messages(question, video_a, video_b, context)
    llm = _build_llm(streaming=False)
    
    from retry_utils import with_rate_limit_retry
    @with_rate_limit_retry
    def _invoke():
        return llm.invoke(messages)
        
    response = _invoke()

    citations = [
        {
            "video_id": d.metadata.get("video_id"),
            "chunk_id": d.metadata.get("chunk_id", i),
            "text": d.page_content[:200],
        }
        for i, d in enumerate(docs)
    ]

    return {"answer": response.content, "citations": citations}


def compare_videos_stream(
    question: str, video_a: dict, video_b: dict
) -> Generator[str, None, None]:
    """Streaming compare — yields SSE lines."""
    docs = search_both_transcripts(question, k_each=3)
    context = "\n\n".join(
        f"[Video {d.metadata.get('video_id')} | Chunk {d.metadata.get('chunk_id', i)}]\n{d.page_content}"
        for i, d in enumerate(docs)
    )

    messages = _build_messages(question, video_a, video_b, context)
    llm = _build_llm(streaming=True)

    try:
        res = llm.invoke(messages)
        token = res.content
        if token:
            safe = token.replace("\n", "\\n")
            yield f"data: {safe}\n\n"
    except Exception as e:
        key_hint = os.environ.get("GROQ_API_KEY", "")[-4:]
        yield f"data: ⚠️ Error (Key ending in {key_hint}): {str(e).replace(chr(10), ' ')}\n\n"

    citations = [
        {
            "video_id": d.metadata.get("video_id"),
            "chunk_id": d.metadata.get("chunk_id", i),
            "text": d.page_content[:200],
        }
        for i, d in enumerate(docs)
    ]
    yield f"event: citations\ndata: {json.dumps(citations)}\n\n"
    yield "event: done\ndata: [DONE]\n\n"