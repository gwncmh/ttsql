import { useState, useRef, useEffect, useCallback } from "react";

// ── Config ────────────────────────────────────────────────────────────────
const API_URL = import.meta.env.VITE_API_URL || "/api/chat";

// ── Data: Schema hiển thị sidebar ────────────────────────────────────────
const SCHEMA_TABLES = [
  { name: "students",  cols: ["id", "name", "gpa", "major_id", "year"] },
  { name: "majors",    cols: ["id", "name", "faculty_id"] },
  { name: "faculties", cols: ["id", "name", "dean"] },
  { name: "scores",    cols: ["id", "student_id", "subject", "score"] },
];

const EXAMPLE_QUESTIONS = [
  { icon: "🏆", text: "Top 3 sinh viên có GPA cao nhất thuộc khoa CNTT?" },
  { icon: "📊", text: "Đếm số sinh viên theo từng khoa." },
  { icon: "⭐", text: "Sinh viên nào có GPA lớn hơn 3.5?" },
  { icon: "📈", text: "GPA trung bình của từng ngành là bao nhiêu?" },
];

const AGENT_PIPELINE = [
  { id: "rewriter",   name: "Query Rewriter",   icon: "✍️" },
  { id: "schema",     name: "Schema Retrieval", icon: "🔍" },
  { id: "router",     name: "Adaptive Router",  icon: "⚡" },
  { id: "generator",  name: "SQL Generator",    icon: "⚙️" },
  { id: "executor",   name: "Executor",         icon: "▶️" },
];

// ── Helpers ───────────────────────────────────────────────────────────────
function timeNow() {
  return new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const SQL_KEYWORDS = [
  "SELECT","FROM","WHERE","JOIN","LEFT","RIGHT","INNER","OUTER","GROUP BY",
  "ORDER BY","HAVING","LIMIT","AS","ON","AND","OR","NOT","IN","DISTINCT",
  "UNION","ALL","CASE","WHEN","THEN","ELSE","END","WITH","DESC","ASC",
];
const SQL_FUNCTIONS = [
  "COUNT","SUM","AVG","MAX","MIN","ROUND","COALESCE","CONCAT","LENGTH",
  "SUBSTR","TRIM","UPPER","LOWER","CAST","NOW","DATE","YEAR","MONTH",
];

function highlightSQL(sql) {
  let h = escapeHTML(sql);
  h = h.replace(/(--[^\n]*)/g, '<span class="sql-cmt">$1</span>');
  h = h.replace(/('[^']*')/g, '<span class="sql-str">$1</span>');
  h = h.replace(/\b(\d+\.?\d*)\b/g, '<span class="sql-num">$1</span>');
  SQL_FUNCTIONS.forEach(fn => {
    h = h.replace(new RegExp(`\\b(${fn})\\b`, "gi"), '<span class="sql-fn">$1</span>');
  });
  SQL_KEYWORDS.forEach(kw => {
    const esc = kw.replace(" ", "\\s+");
    h = h.replace(new RegExp(`\\b(${esc})\\b`, "gi"), '<span class="sql-kw">$1</span>');
  });
  return h;
}

// ── Sub-components ────────────────────────────────────────────────────────

function AgentStatusPanel({ agentStates }) {
  return (
    <div className="agent-status">
      {AGENT_PIPELINE.map((agent) => {
        const state = agentStates[agent.id] || "idle";
        return (
          <div className="agent-row" key={agent.id}>
            <div className={`agent-dot ${state}`} />
            <span className="agent-name">{agent.icon} {agent.name}</span>
            <span className="agent-label">
              {state === "thinking" ? "Đang chạy..." : state === "done" ? "✓" : "—"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function SchemaPanel({ activeTable, onSelectTable }) {
  return (
    <div id="schema-list">
      {SCHEMA_TABLES.map((t, i) => (
        <div
          key={t.name}
          className={`schema-item ${activeTable === i ? "active" : ""}`}
          onClick={() => onSelectTable(i)}
        >
          <div className="schema-icon">⬡</div>
          <div>
            <div className="schema-name">{t.name}</div>
            <div className="schema-cols">
              {t.cols.slice(0, 4).join(", ")}{t.cols.length > 4 ? ", …" : ""}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function SQLBlock({ sql }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div className="sql-block">
      <div className="sql-header">
        <span className="sql-lang">SQL</span>
        <button className="sql-copy" onClick={handleCopy}>
          {copied ? "✓ Đã chép" : "Sao chép"}
        </button>
      </div>
      <div
        className="sql-code"
        dangerouslySetInnerHTML={{ __html: highlightSQL(sql) }}
      />
    </div>
  );
}

function ThinkingTrace({ model, complexity }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`thinking-trace ${open ? "open" : ""}`}>
      <div className="thinking-header" onClick={() => setOpen(!open)}>
        <div className="thinking-dot" />
        Quá trình xử lý đa tác tử
        <span className="thinking-chevron">▾</span>
      </div>
      <div className="thinking-body">
        {AGENT_PIPELINE.map((agent) => (
          <div className="trace-step done" key={agent.id}>
            <span className="step-icon">✓</span>
            <span className="step-text">
              {agent.name}: {
                agent.id === "router"
                  ? `Phân loại → ${complexity || "SIMPLE"}`
                  : agent.id === "generator"
                  ? `Sinh SQL (${complexity === "COMPLEX" ? "Chain-of-Thought" : "1-shot"})`
                  : agent.id === "rewriter"
                  ? "Chuẩn hóa câu hỏi đầu vào"
                  : agent.id === "schema"
                  ? "Truy xuất schema liên quan (RAG)"
                  : "Thực thi SQL trên PostgreSQL"
              }
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="msg ai">
      <div className="typing-indicator">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
}

function ChatMessage({ item, index }) {
  return (
    <>
      {/* User bubble */}
      <div className="msg user">
        <div className="msg-bubble">{item.userQuestion}</div>
        <div className="msg-meta">{item.time}</div>
      </div>

      {/* AI response */}
      <div className="msg ai">
        <ThinkingTrace model="Pipeline" complexity={item.complexity} />
        <SQLBlock sql={item.sql} />

        {/* Result table (mock-style từ dữ liệu trả về) */}
        <div className="result-card">
          <div className="result-header">
            <span style={{ color: "var(--green)", fontSize: 14 }}>✓</span>
            <span className="result-title">Kết quả truy vấn</span>
            <span className="result-count">{item.elapsed}s</span>
          </div>
          <div style={{ padding: "12px 14px" }}>
            <div style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.7 }}
              dangerouslySetInnerHTML={{ __html: item.answer }} />
          </div>
        </div>

        {/* Meta info */}
        <div className="msg-meta">
          {item.time} · {item.complexity} · {item.elapsed}s
        </div>

        {/* Rewritten query info */}
        <div style={{
          fontSize: 11,
          color: "var(--text-dim)",
          marginTop: 4,
          padding: "0 4px",
          fontStyle: "italic"
        }}>
          Rewritten: {item.rewrittenQuery}
        </div>
      </div>
    </>
  );
}

function WelcomeScreen({ onSelectExample }) {
  return (
    <div className="welcome" id="welcome-screen">
      <div className="welcome-icon">💬</div>
      <h2>Hỏi đáp cơ sở dữ liệu bằng tiếng Việt</h2>
      <p>
        Đặt câu hỏi bằng ngôn ngữ tự nhiên, hệ thống đa tác tử sẽ tự động
        tạo SQL và trả kết quả cho bạn.
      </p>
      <div className="example-pills">
        {EXAMPLE_QUESTIONS.map((e) => (
          <button
            key={e.text}
            className="example-pill"
            onClick={() => onSelectExample(e.text)}
          >
            <span className="pill-icon">{e.icon}</span>
            {e.text}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────
export default function App() {
  const [message, setMessage]         = useState("");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");
  const [conversation, setConversation] = useState([]);
  const [activeTable, setActiveTable] = useState(0);
  const [agentStates, setAgentStates] = useState({});
  const [stats, setStats]             = useState({
    totalQueries: 0, totalLatency: 0, totalRows: 0,
  });

  const chatRef     = useRef(null);
  const inputRef    = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [conversation, loading]);

  // Auto-resize textarea
  const autoResize = (el) => {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  // Animate agent pipeline
  const runAgentPipeline = useCallback(async () => {
    const reset = {};
    AGENT_PIPELINE.forEach(a => { reset[a.id] = "idle"; });
    setAgentStates(reset);

    for (const agent of AGENT_PIPELINE) {
      setAgentStates(prev => ({ ...prev, [agent.id]: "thinking" }));
      await new Promise(r => setTimeout(r, 350 + Math.random() * 300));
      setAgentStates(prev => ({ ...prev, [agent.id]: "done" }));
    }
  }, []);

  const onSubmit = async () => {
    if (!message.trim() || loading) return;

    const userMessage = message.trim();
    setLoading(true);
    setError("");
    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const t0 = Date.now();

    try {
      const [res] = await Promise.all([
        fetch(API_URL, {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ message: userMessage }),
        }),
        runAgentPipeline(),
      ]);

      if (!res.ok) throw new Error("Backend trả về lỗi");

      const data    = await res.json();
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

      setConversation(prev => [
        ...prev,
        {
          id:             crypto.randomUUID(),
          userQuestion:   userMessage,
          rewrittenQuery: data.rewritten_query,
          complexity:     data.complexity,
          sql:            data.sql,
          answer:         data.answer,
          elapsed,
          time:           timeNow(),
        },
      ]);

      setStats(prev => ({
        totalQueries: prev.totalQueries + 1,
        totalLatency: prev.totalLatency + parseFloat(elapsed),
        totalRows:    prev.totalRows,
      }));

    } catch (err) {
      setError(err instanceof Error ? err.message : "Đã có lỗi xảy ra");
      // Reset agent states on error
      const errState = {};
      AGENT_PIPELINE.forEach(a => { errState[a.id] = "idle"; });
      setAgentStates(errState);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  const useExample = (text) => {
    setMessage(text);
    if (textareaRef.current) {
      textareaRef.current.value = text;
      autoResize(textareaRef.current);
    }
    // Auto-send
    setTimeout(() => {
      setMessage(text);
    }, 0);
  };

  const clearHistory = () => {
    setConversation([]);
    setError("");
    setStats({ totalQueries: 0, totalLatency: 0, totalRows: 0 });
    const reset = {};
    AGENT_PIPELINE.forEach(a => { reset[a.id] = "idle"; });
    setAgentStates(reset);
  };

  const avgLatency = stats.totalQueries
    ? (stats.totalLatency / stats.totalQueries).toFixed(1) + "s"
    : "—";
  const successRate = stats.totalQueries
    ? "100%"
    : "—";

  return (
    <>
      {/* ── Header ── */}
      <header>
        <div className="logo">
          <div className="logo-icon">🧠</div>
          Vi<span>Text2SQL</span>
        </div>
        <div className="header-meta">
          <span className="badge badge-green">● Đang chạy</span>
          <span className="badge badge-blue">Multi-Agent</span>
          {conversation.length > 0 && (
            <button
              type="button"
              className="btn-clear"
              onClick={clearHistory}
              title="Xóa lịch sử"
            >
              Xóa
            </button>
          )}
        </div>
      </header>

      <div className="app">

        {/* ── Sidebar trái ── */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-label">Schema</div>
            <SchemaPanel
              activeTable={activeTable}
              onSelectTable={setActiveTable}
            />
          </div>

          <div className="sidebar-section">
            <div className="sidebar-label">Trạng thái Agent</div>
            <AgentStatusPanel agentStates={agentStates} />
          </div>
        </aside>

        {/* ── Main chat ── */}
        <main className="main">
          <div className="chat-history" ref={chatRef}>
            {conversation.length === 0 && !loading && (
              <WelcomeScreen onSelectExample={useExample} />
            )}

            {conversation.map((item, index) => (
              <ChatMessage key={item.id} item={item} index={index} />
            ))}

            {loading && <TypingIndicator />}

            {error && (
              <div className="msg ai">
                <div className="msg-bubble error-bubble">
                  ⚠️ {error}
                </div>
              </div>
            )}
          </div>

          {/* ── Input area ── */}
          <div className="input-area">
            <div className={`input-box ${loading ? "disabled" : ""}`}>
              <textarea
                ref={textareaRef}
                id="query-input"
                rows={1}
                placeholder="Hỏi gì đó về cơ sở dữ liệu... (Ví dụ: Top 3 sinh viên GPA cao nhất?)"
                value={message}
                onChange={(e) => {
                  setMessage(e.target.value);
                  autoResize(e.target);
                }}
                onKeyDown={handleKey}
                disabled={loading}
              />
              <button
                className="send-btn"
                onClick={onSubmit}
                disabled={loading || !message.trim()}
                title="Gửi (Enter)"
              >
                {loading ? "…" : "↑"}
              </button>
            </div>
            <div className="input-hint">
              Nhấn <kbd>Enter</kbd> để gửi · <kbd>Shift+Enter</kbd> xuống dòng
            </div>
          </div>
        </main>

        {/* ── Right panel ── */}
        <aside className="right-panel">
          <div className="rpanel-section">
            <div className="rpanel-label">📊 Thống kê</div>
            <div className="stat-grid">
              <div className="stat-cell">
                <div className="stat-val">{stats.totalQueries}</div>
                <div className="stat-key">Số câu hỏi</div>
              </div>
              <div className="stat-cell">
                <div className="stat-val">{successRate}</div>
                <div className="stat-key">Tỉ lệ đúng</div>
              </div>
              <div className="stat-cell">
                <div className="stat-val">{avgLatency}</div>
                <div className="stat-key">Thời gian TB</div>
              </div>
              <div className="stat-cell">
                <div className="stat-val">
                  {conversation.length > 0
                    ? conversation[conversation.length - 1].complexity === "COMPLEX"
                      ? "CoT"
                      : "1-shot"
                    : "—"}
                </div>
                <div className="stat-key">Chiến lược</div>
              </div>
            </div>
          </div>

          <div className="rpanel-section" style={{ flex: 1 }}>
            <div className="rpanel-label">🕘 Lịch sử</div>
            <div id="history-list">
              {conversation.length === 0 ? (
                <div style={{ fontSize: 12, color: "var(--text-dim)", padding: 4 }}>
                  Chưa có lịch sử
                </div>
              ) : (
                conversation
                  .slice()
                  .reverse()
                  .slice(0, 12)
                  .map((item) => (
                    <div
                      key={item.id}
                      className="history-item"
                      onClick={() => setMessage(item.userQuestion)}
                      title={item.userQuestion}
                    >
                      <div className="history-q">{item.userQuestion}</div>
                      <div className="history-t">{item.time} · {item.complexity}</div>
                    </div>
                  ))
              )}
            </div>
          </div>

          <div className="rpanel-section">
            <div className="rpanel-label">🔧 Pipeline</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {AGENT_PIPELINE.map((agent) => (
                <div
                  key={agent.id}
                  style={{
                    fontSize: 11,
                    color: "var(--text-muted)",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 8px",
                    background: "var(--bg-card)",
                    borderRadius: "var(--radius)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <span>{agent.icon}</span>
                  <span style={{ flex: 1 }}>{agent.name}</span>
                  <div className={`agent-dot ${agentStates[agent.id] || "idle"}`} />
                </div>
              ))}
            </div>
          </div>
        </aside>

      </div>
    </>
  );
}