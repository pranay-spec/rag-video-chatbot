"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";

// ─── Types ────────────────────────────────────────────────────────────────────
interface Citation {
  video_id: string;
  chunk_id: number;
  text: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
}

interface VideoMeta {
  title: string;
  creator: string;
  views: number | null;          // null = not available (e.g. Instagram without auth)
  likes: number;
  comments: number;
  duration: number;
  upload_date: string;
  hashtags: string[];
  follower_count: number | null;
  thumbnail: string;
  url: string;
  platform: string;
}

interface VideoData {
  video_id: string;
  chunks: number;
  engagement_rate: number | null; // null when views unavailable (Instagram)
  interaction_score: number;      // likes + comments — always available
  views_available: boolean;
  metadata: VideoMeta;
  transcript_preview: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SESSION_ID = `session-${Date.now()}`;

const SUGGESTED_COMPARE = [
  "Why did Video A get more engagement than Video B?",
  "Compare the hooks in the first 5 seconds.",
  "What's the engagement rate of each?",
  "Suggest improvements for the lower-performing video.",
  "Who has more followers and does it correlate with performance?",
];

const SUGGESTED_A = [
  "What is the main topic of this video?",
  "What hook does this creator use?",
  "Who is the creator and what's their follower count?",
];

const SUGGESTED_B = [
  "What is the main topic of this video?",
  "What hook does this creator use?",
  "Who is the creator and what's their follower count?",
];

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmt(n: number | null | undefined): string {
  if (n == null) return "N/A";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function fmtDuration(s: number): string {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

// ─── Citation pill ────────────────────────────────────────────────────────────
function CitationPill({
  citation,
  expanded,
  onToggle,
}: {
  citation: Citation;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div style={{ marginTop: 6 }}>
      <button className="citation" onClick={onToggle}>
        📎 Video {citation.video_id} · Chunk {citation.chunk_id}
        <span style={{ opacity: 0.7 }}>{expanded ? " ▲" : " ▼"}</span>
      </button>
      {expanded && (
        <div
          style={{
            marginTop: 4,
            padding: "8px 12px",
            background: "rgba(99,102,241,0.08)",
            border: "1px solid rgba(99,102,241,0.2)",
            borderRadius: 8,
            fontSize: 12,
            color: "#94a3b8",
            lineHeight: 1.6,
            fontStyle: "italic",
          }}
        >
          &ldquo;{citation.text}&rdquo;
        </div>
      )}
    </div>
  );
}

// ─── Video Card ───────────────────────────────────────────────────────────────
function VideoCard({
  label,
  data,
  winner,
}: {
  label: string;
  data: VideoData;
  winner: boolean;
}) {
  const m = data.metadata;
  return (
    <div
      className="glass-card"
      style={{ padding: 20, position: "relative", overflow: "hidden" }}
    >
      {winner && (
        <div
          style={{
            position: "absolute",
            top: 12,
            right: 12,
            padding: "4px 12px",
            background: "linear-gradient(135deg, #f59e0b, #d97706)",
            borderRadius: 20,
            fontSize: 11,
            fontWeight: 700,
            color: "#1a1000",
          }}
        >
          🏆 WINNER
        </div>
      )}

      {/* Thumbnail */}
      {m.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={`${API}/proxy-image?url=${encodeURIComponent(m.thumbnail)}`}
          alt={m.title}
          className="video-thumb"
          referrerPolicy="no-referrer"
          style={{ marginBottom: 14 }}
        />
      ) : (
        <div
          className="video-thumb"
          style={{
            marginBottom: 14,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#475569",
            fontSize: 40,
          }}
        >
          🎬
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <div style={{ padding: "3px 10px", background: "rgba(99,102,241,0.2)", border: "1px solid rgba(99,102,241,0.4)", borderRadius: 6, fontSize: 11, fontWeight: 700, color: "#a5b4fc" }}>
          VIDEO {label}
        </div>
        {/* Platform badge */}
        <div style={{
          padding: "3px 8px",
          background: m.platform === "instagram" ? "rgba(225,48,108,0.15)" : m.platform === "youtube" ? "rgba(255,0,0,0.12)" : "rgba(99,102,241,0.1)",
          border: `1px solid ${m.platform === "instagram" ? "rgba(225,48,108,0.35)" : m.platform === "youtube" ? "rgba(255,0,0,0.3)" : "rgba(99,102,241,0.2)"}`,
          borderRadius: 6, fontSize: 11, fontWeight: 600,
          color: m.platform === "instagram" ? "#fb7185" : m.platform === "youtube" ? "#f87171" : "#a5b4fc",
        }}>
          {m.platform === "instagram" ? "📸 Instagram" : m.platform === "youtube" ? "▶ YouTube" : "🎬 Video"}
        </div>
        {/* Engagement / Interaction badge */}
        {data.engagement_rate !== null ? (
          <div className="engagement-badge">{data.engagement_rate}% ER</div>
        ) : (
          <div className="engagement-badge" style={{ background: "rgba(251,146,60,0.15)", border: "1px solid rgba(251,146,60,0.35)", color: "#fb923c" }}
            title="Instagram hides views — showing Interaction Score (likes + comments) instead">
            🔥 {fmt(data.interaction_score)} interactions
          </div>
        )}
      </div>

      <h3 style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.4, marginBottom: 6, color: "#f1f5f9" }}>
        {m.title}
      </h3>

      <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: 12 }}>
        by <strong style={{ color: "#c4b5fd" }}>{m.creator}</strong>
        {m.follower_count != null && (
          <span style={{ color: "#64748b" }}>{" "}· {fmt(m.follower_count)} followers</span>
        )}
      </p>

      <div className="stat-row">
        <div className="stat-chip" style={m.views === null ? { opacity: 0.45 } : {}}
          title={m.views === null ? "Instagram restricts view counts — platform limitation" : undefined}>
          👁 <span>{m.views !== null ? fmt(m.views) : "—"}</span>
        </div>
        <div className="stat-chip">❤️ <span>{fmt(m.likes)}</span></div>
        <div className="stat-chip">💬 <span>{fmt(m.comments)}</span></div>
        <div className="stat-chip">⏱ <span>{fmtDuration(m.duration)}</span></div>
        <div className="stat-chip">📅 <span>{m.upload_date || "N/A"}</span></div>
      </div>
      {m.views === null && (
        <div style={{ marginTop: 10, padding: "7px 12px", background: "rgba(251,146,60,0.08)", border: "1px solid rgba(251,146,60,0.2)", borderRadius: 8, fontSize: 11, color: "#fb923c", display: "flex", alignItems: "center", gap: 6 }}>
          ⚠️ Instagram hides view counts — comparing via <strong style={{ marginLeft: 3 }}>Interaction Score</strong>
        </div>
      )}

      {m.hashtags.length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
            marginTop: 12,
          }}
        >
          {m.hashtags.slice(0, 6).map((h) => (
            <span key={h} className="hashtag">
              {h}
            </span>
          ))}
        </div>
      )}

      <div
        style={{
          marginTop: 12,
          padding: "8px 12px",
          background: "rgba(10,16,30,0.6)",
          borderRadius: 8,
          fontSize: 11,
          color: "#475569",
          fontStyle: "italic",
          lineHeight: 1.5,
        }}
      >
        📝 &ldquo;{data.transcript_preview}…&rdquo;
      </div>
    </div>
  );
}

// ─── Metrics Comparison Bar ───────────────────────────────────────────────────
function MetricsComparison({ a, b }: { a: VideoData; b: VideoData }) {
  const metrics: Array<{
    label: string;
    icon: string;
    valA: number | null;
    valB: number | null;
    format: (v: number) => string;
    color: string;
  }> = [
    {
      label: "Likes",
      icon: "❤️",
      valA: a.metadata.likes,
      valB: b.metadata.likes,
      format: fmt,
      color: "#f43f5e",
    },
    {
      label: "Comments",
      icon: "💬",
      valA: a.metadata.comments,
      valB: b.metadata.comments,
      format: fmt,
      color: "#a78bfa",
    },
    {
      label: a.views_available && b.views_available ? "Engagement Rate %" : "Interaction Score",
      icon: "📈",
      valA: a.views_available ? a.engagement_rate : a.interaction_score,
      valB: b.views_available ? b.engagement_rate : b.interaction_score,
      format: a.views_available && b.views_available ? (v) => `${v}%` : fmt,
      color: "#34d399",
    },
    ...(a.metadata.views !== null && b.metadata.views !== null
      ? [
          {
            label: "Views",
            icon: "👁",
            valA: a.metadata.views,
            valB: b.metadata.views,
            format: fmt,
            color: "#60a5fa",
          },
        ]
      : []),
  ];

  return (
    <div
      className="glass-card"
      style={{ padding: "16px 20px", marginBottom: 20 }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: "#64748b",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: 14,
        }}
      >
        📊 Head-to-Head Comparison
        {(!a.views_available || !b.views_available) && (
          <span
            style={{
              marginLeft: 10,
              fontSize: 11,
              fontWeight: 500,
              color: "#fb923c",
              textTransform: "none",
              letterSpacing: 0,
            }}
          >
            · ER unavailable for Instagram — using Interaction Score
          </span>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {metrics.map((m) => {
          const vA = m.valA ?? 0;
          const vB = m.valB ?? 0;
          const total = vA + vB || 1;
          const pctA = (vA / total) * 100;
          const pctB = (vB / total) * 100;
          const winnerA = vA >= vB;
          return (
            <div key={m.label}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 12,
                  color: "#94a3b8",
                  marginBottom: 5,
                }}
              >
                <span style={{ fontWeight: winnerA ? 700 : 400, color: winnerA ? "#f1f5f9" : "#64748b" }}>
                  {m.icon} A: {m.format(vA)}
                  {winnerA && <span style={{ color: "#f59e0b", marginLeft: 4 }}>▲</span>}
                </span>
                <span style={{ fontWeight: 600, color: "#475569" }}>{m.label}</span>
                <span style={{ fontWeight: !winnerA ? 700 : 400, color: !winnerA ? "#f1f5f9" : "#64748b" }}>
                  {!winnerA && <span style={{ color: "#f59e0b", marginRight: 4 }}>▲</span>}
                  B: {m.format(vB)}
                </span>
              </div>
              {/* Dual bar */}
              <div style={{ display: "flex", height: 8, borderRadius: 6, overflow: "hidden", background: "rgba(15,23,42,0.8)" }}>
                <div
                  style={{
                    width: `${pctA}%`,
                    background: winnerA
                      ? `linear-gradient(90deg, ${m.color}cc, ${m.color})`
                      : `${m.color}44`,
                    borderRadius: "6px 0 0 6px",
                    transition: "width 0.6s ease",
                  }}
                />
                <div
                  style={{
                    width: `${pctB}%`,
                    background: !winnerA
                      ? `linear-gradient(90deg, ${m.color}, ${m.color}cc)`
                      : `${m.color}44`,
                    borderRadius: "0 6px 6px 0",
                    transition: "width 0.6s ease",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: 20, marginTop: 12, fontSize: 11, color: "#475569" }}>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 2, background: "rgba(99,102,241,0.6)", marginRight: 5 }} />
          Video A — {a.metadata.platform}
        </span>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 2, background: "rgba(139,92,246,0.6)", marginRight: 5 }} />
          Video B — {b.metadata.platform}
        </span>
      </div>
    </div>
  );
}

// ─── Chat Panel ───────────────────────────────────────────────────────────────
function ChatPanel({
  tab,
  videoA,
  videoB,
}: {
  tab: "compare" | "A" | "B";
  videoA: VideoData | null;
  videoB: VideoData | null;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedCitations, setExpandedCitations] = useState<
    Record<string, boolean>
  >({});

  // Reset messages when tab changes
  useEffect(() => {
    setMessages([]);
    setInput("");
  }, [tab]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleCitation = (key: string) =>
    setExpandedCitations((prev) => ({ ...prev, [key]: !prev[key] }));

  const sendMessage = useCallback(
    async (q?: string) => {
      const question = (q ?? input).trim();
      if (!question || loading) return;

      setInput("");
      setMessages((prev) => [
        ...prev,
        { role: "user", content: question },
      ]);
      setLoading(true);

      // Add empty assistant message for streaming
      const assistantIdx = messages.length + 1;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", streaming: true },
      ]);

      try {
        let endpoint: string;
        let body: Record<string, string>;

        if (tab === "compare") {
          endpoint = `${API}/compare/stream`;
          body = { question, session_id: SESSION_ID };
        } else {
          endpoint = `${API}/chat/stream`;
          body = { question, video_id: tab, session_id: SESSION_ID };
        }

        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let fullText = "";
        let citations: Citation[] = [];

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (line.startsWith("event: citations")) {
              // Next data line has citations
            } else if (line.startsWith("event: done")) {
              // stream finished
            } else if (line.startsWith("data: [DONE]")) {
              // skip
            } else if (line.startsWith("data: ")) {
              const raw = line.slice(6);
              // Check if this is a citations JSON
              try {
                const parsed = JSON.parse(raw);
                if (Array.isArray(parsed)) {
                  citations = parsed;
                  continue;
                }
              } catch {
                // not JSON, it's a text token
              }
              const token = raw.replace(/\\n/g, "\n");
              fullText += token;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: fullText,
                  streaming: true,
                };
                return updated;
              });
            }
          }
        }

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: fullText,
            citations,
            streaming: false,
          };
          return updated;
        });
      } catch (err) {
        console.error(err);
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: "⚠️ Error fetching response. Is the backend running?",
            streaming: false,
          };
          return updated;
        });
      } finally {
        setLoading(false);
      }
      void assistantIdx; // suppress unused warning
    },
    [input, loading, messages.length, tab]
  );

  const suggestions =
    tab === "compare" ? SUGGESTED_COMPARE : tab === "A" ? SUGGESTED_A : SUGGESTED_B;

  const tabLabel =
    tab === "compare"
      ? "Compare A vs B"
      : tab === "A"
      ? `Video A — ${videoA?.metadata.title?.slice(0, 30) ?? ""}…`
      : `Video B — ${videoB?.metadata.title?.slice(0, 30) ?? ""}…`;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      {/* Chat header */}
      <div
        style={{
          padding: "12px 18px",
          borderBottom: "1px solid rgba(99,133,255,0.12)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ fontSize: 13, color: "#94a3b8" }}>💬 {tabLabel}</div>
        {messages.length > 0 && (
          <button
            className="btn-ghost"
            onClick={() => setMessages([])}
            style={{ fontSize: 11, padding: "4px 10px" }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 18px",
          display: "flex",
          flexDirection: "column",
          gap: 14,
          minHeight: 0,
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "40px 20px",
              color: "#475569",
            }}
          >
            <div style={{ fontSize: 36, marginBottom: 10 }}>🤖</div>
            <p style={{ fontSize: 14, marginBottom: 20 }}>
              Ask anything about the videos
            </p>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                justifyContent: "center",
              }}
            >
              {suggestions.slice(0, 3).map((s) => (
                <button
                  key={s}
                  className="suggested-q"
                  onClick={() => sendMessage(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === "user" ? (
              <div className="bubble-user">{msg.content}</div>
            ) : (
              <div
                className={`bubble-ai${msg.streaming ? " streaming-cursor" : ""}`}
              >
                <ReactMarkdown>{msg.content}</ReactMarkdown>
                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#475569",
                        marginBottom: 4,
                      }}
                    >
                      Sources:
                    </div>
                    {msg.citations.map((c, ci) => {
                      const key = `${i}-${ci}`;
                      return (
                        <CitationPill
                          key={key}
                          citation={c}
                          expanded={!!expandedCitations[key]}
                          onToggle={() => toggleCitation(key)}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Suggested questions strip */}
      {messages.length > 0 && !loading && (
        <div
          style={{
            padding: "8px 18px",
            display: "flex",
            gap: 8,
            overflowX: "auto",
            flexShrink: 0,
            borderTop: "1px solid rgba(99,133,255,0.08)",
          }}
        >
          {suggestions.map((s) => (
            <button
              key={s}
              className="suggested-q"
              onClick={() => sendMessage(s)}
              style={{ flexShrink: 0 }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div
        style={{
          padding: "14px 18px",
          borderTop: "1px solid rgba(99,133,255,0.12)",
          display: "flex",
          gap: 10,
          flexShrink: 0,
        }}
      >
        <input
          className="input-field"
          placeholder={`Ask about ${tab === "compare" ? "both videos" : `Video ${tab}`}…`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
          disabled={loading}
          style={{ flex: 1 }}
        />
        <button
          className="btn-primary"
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
          style={{ padding: "12px 20px", flexShrink: 0 }}
        >
          {loading ? <div className="spinner" /> : "Send"}
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Home() {
  const [videoAUrl, setVideoAUrl] = useState("");
  const [videoBUrl, setVideoBUrl] = useState("");
  const [videoA, setVideoA] = useState<VideoData | null>(null);
  const [videoB, setVideoB] = useState<VideoData | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeStep, setAnalyzeStep] = useState("");
  const [activeTab, setActiveTab] = useState<"compare" | "A" | "B">("compare");
  const [error, setError] = useState("");

  // Winner: prefer engagement rate; fall back to likes+comments when views unavailable
  const _score = (v: typeof videoA) => {
    if (!v) return 0;
    if (v.engagement_rate !== null) return v.engagement_rate;
    return (v.metadata.likes || 0) + (v.metadata.comments || 0);
  };
  const winner =
    videoA && videoB
      ? _score(videoA) >= _score(videoB)
        ? "A"
        : "B"
      : null;

  const analyze = async () => {
    if (!videoAUrl.trim() || !videoBUrl.trim()) {
      setError("Please enter both video URLs.");
      return;
    }
    setError("");
    setAnalyzing(true);
    setVideoA(null);
    setVideoB(null);

    try {
      setAnalyzeStep("Downloading & transcribing videos…");
      const res = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ videoA: videoAUrl, videoB: videoBUrl }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Analyze failed");
      }

      const data = await res.json();
      setVideoA(data.videoA);
      setVideoB(data.videoB);
      setAnalyzeStep("");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setError(msg);
      setAnalyzeStep("");
    } finally {
      setAnalyzing(false);
    }
  };

  const analyzed = videoA && videoB;

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "32px 24px",
      }}
    >
      <div style={{ maxWidth: 1400, margin: "auto" }}>
        {/* ── Header ── */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h1
            className="gradient-text"
            style={{ fontSize: 36, fontWeight: 800, marginBottom: 8 }}
          >
            🎬 RAG Video Analyst
          </h1>
          <p style={{ color: "#64748b", fontSize: 15 }}>
            Paste two social media video URLs · Get AI-powered engagement insights
          </p>
        </div>

        {/* ── URL Inputs ── */}
        <div className="glass-card" style={{ padding: 28, marginBottom: 28 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 20,
            }}
          >
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#94a3b8",
                  marginBottom: 8,
                  letterSpacing: "0.05em",
                  textTransform: "uppercase",
                }}
              >
                🎥 Video A — YouTube or Instagram
              </label>
              <input
                className="input-field"
                placeholder="https://youtube.com/watch?v=... or https://instagram.com/reel/..."
                value={videoAUrl}
                onChange={(e) => setVideoAUrl(e.target.value)}
                disabled={analyzing}
              />
            </div>
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#94a3b8",
                  marginBottom: 8,
                  letterSpacing: "0.05em",
                  textTransform: "uppercase",
                }}
              >
                🎥 Video B — YouTube or Instagram
              </label>
              <input
                className="input-field"
                placeholder="https://youtube.com/watch?v=... or https://instagram.com/reel/..."
                value={videoBUrl}
                onChange={(e) => setVideoBUrl(e.target.value)}
                disabled={analyzing}
              />
            </div>
          </div>

          {error && (
            <div
              style={{
                padding: "10px 16px",
                background: "rgba(239,68,68,0.12)",
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 10,
                color: "#fca5a5",
                fontSize: 13,
                marginBottom: 16,
              }}
            >
              ⚠️ {error}
            </div>
          )}

          <button
            className="btn-primary"
            onClick={analyze}
            disabled={analyzing}
            style={{ width: "100%", fontSize: 16, padding: "16px 28px" }}
          >
            {analyzing ? (
              <>
                <div className="spinner" />
                {analyzeStep || "Analyzing…"}
              </>
            ) : (
              <>🚀 Analyze Both Videos</>
            )}
          </button>

          {analyzing && (
            <div className="progress-bar" style={{ marginTop: 12 }} />
          )}
        </div>

        {/* ── Results ── */}
        {analyzed && (
          <div className="results-wrapper">
            {/* Comparison bar — spans full width above cards */}
            <MetricsComparison a={videoA!} b={videoB!} />

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1.4fr",
                gap: 20,
                alignItems: "start",
              }}
            >
            {/* Video Cards */}
            <VideoCard label="A" data={videoA!} winner={winner === "A"} />
            <VideoCard label="B" data={videoB!} winner={winner === "B"} />

            {/* Chat Panel */}
            <div
              className="glass-card"
              style={{
                display: "flex",
                flexDirection: "column",
                height: 700,
                overflow: "hidden",
              }}
            >
              {/* Tabs */}
              <div style={{ padding: "14px 14px 0" }}>
                <div className="tab-bar">
                  <button
                    className={`tab ${activeTab === "compare" ? "active" : ""}`}
                    onClick={() => setActiveTab("compare")}
                  >
                    ⚖️ Compare
                  </button>
                  <button
                    className={`tab ${activeTab === "A" ? "active" : ""}`}
                    onClick={() => setActiveTab("A")}
                  >
                    🎬 Video A
                  </button>
                  <button
                    className={`tab ${activeTab === "B" ? "active" : ""}`}
                    onClick={() => setActiveTab("B")}
                  >
                    🎬 Video B
                  </button>
                </div>
              </div>

              {/* Chat content */}
              <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
                <ChatPanel tab={activeTab} videoA={videoA} videoB={videoB} />
              </div>
            </div>
          </div>
          </div>
        )}

        {/* ── Footer ── */}
        <div
          style={{
            textAlign: "center",
            marginTop: 48,
            color: "#334155",
            fontSize: 12,
          }}
        >
          RAG Video Analyst · Powered by LangChain + ChromaDB + Gemini 2.5 Flash
        </div>
      </div>
    </main>
  );
}