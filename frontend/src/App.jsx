// ─────────────────────────────────────────────
// App.jsx
// Component gốc — chỉ chứa state, logic gọi API,
// và layout tổng thể (header / sidebar / main / right panel).
// Các UI nhỏ đã tách sang components.jsx.
// ─────────────────────────────────────────────

import { useState, useRef, useEffect, useCallback } from "react";

import { API_URL, AGENT_PIPELINE } from "./constants";
import { timeNow } from "./utils";
import {
  AgentStatusPanel,
  SchemaPanel,
  SQLBlock,
  TypingIndicator,
  ChatMessage,
  WelcomeScreen,
} from "./components";

// Import CSS — mỗi file CSS phụ trách một nhóm component
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/sidebar.css";
import "./styles/chat.css";
import "./styles/input.css";
import "./styles/rightpanel.css";

export default function App() {
  // ── State ──────────────────────────────────

  // Nội dung đang gõ trong ô input
  const [message, setMessage] = useState("");

  // true khi đang chờ response từ backend
  const [loading, setLoading] = useState(false);

  // Chuỗi lỗi hiển thị dưới chat nếu request thất bại
  const [error, setError] = useState("");

  // Mảng các lượt hội thoại — mỗi phần tử là một Q&A
  const [conversation, setConversation] = useState([]);

  // Index bảng đang được chọn trong SchemaPanel (0-based)
  const [activeTable, setActiveTable] = useState(0);

  // Trạng thái từng agent: { rewriter: "idle"|"thinking"|"done", ... }
  const [agentStates, setAgentStates] = useState({});

  // Thống kê tổng hợp hiển thị ở right panel
  const [stats, setStats] = useState({
    totalQueries: 0,
    totalLatency: 0,
  });

  // ── Refs ────────────────────────────────────

  // Ref đến vùng chat — dùng để auto-scroll xuống cuối
  const chatRef = useRef(null);

  // Ref đến textarea — dùng để auto-resize khi gõ
  const textareaRef = useRef(null);

  // ── Effects ─────────────────────────────────

  // Mỗi khi conversation hoặc loading thay đổi → scroll xuống cuối
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [conversation, loading]);

  // ── Helpers ─────────────────────────────────

  // Tự động điều chỉnh chiều cao textarea theo nội dung
  // max 120px — quá thì scroll bên trong textarea
  const autoResize = (el) => {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  // Chạy animation pipeline từng bước — mỗi bước delay 350-650ms
  // Chạy song song với fetch API (Promise.all trong onSubmit)
  const runAgentPipeline = useCallback(async () => {
    // Reset tất cả về idle trước khi chạy lại
    const reset = {};
    AGENT_PIPELINE.forEach((a) => { reset[a.id] = "idle"; });
    setAgentStates(reset);

    for (const agent of AGENT_PIPELINE) {
      // Bật "thinking" cho bước hiện tại
      setAgentStates((prev) => ({ ...prev, [agent.id]: "thinking" }));
      // Chờ ngẫu nhiên 350-650ms để giả lập processing
      await new Promise((r) => setTimeout(r, 350 + Math.random() * 300));
      // Chuyển sang "done"
      setAgentStates((prev) => ({ ...prev, [agent.id]: "done" }));
    }
  }, []);

  // ── Submit handler ───────────────────────────

  const onSubmit = async () => {
    if (!message.trim() || loading) return;

    const userMessage = message.trim();
    setLoading(true);
    setError("");
    setMessage("");

    // Reset chiều cao textarea về mặc định sau khi submit
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    const t0 = Date.now();

    try {
      // Chạy đồng thời: gọi API + chạy animation pipeline
      const [res] = await Promise.all([
        fetch(API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMessage }),
        }),
        runAgentPipeline(),
      ]);

      if (!res.ok) throw new Error("Backend trả về lỗi");

      const data = await res.json();
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

      // Thêm lượt hội thoại mới vào cuối mảng
      setConversation((prev) => [
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

      // Cộng dồn stats
      setStats((prev) => ({
        totalQueries: prev.totalQueries + 1,
        totalLatency: prev.totalLatency + parseFloat(elapsed),
      }));

    } catch (err) {
      setError(err instanceof Error ? err.message : "Đã có lỗi xảy ra");
      // Reset agent states về idle khi có lỗi
      const errState = {};
      AGENT_PIPELINE.forEach((a) => { errState[a.id] = "idle"; });
      setAgentStates(errState);
    } finally {
      setLoading(false);
    }
  };

  // Submit bằng Enter (Shift+Enter = xuống dòng)
  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  // Điền câu hỏi mẫu vào input khi click pill ở WelcomeScreen
  const useExample = (text) => {
    setMessage(text);
    if (textareaRef.current) {
      textareaRef.current.value = text;
      autoResize(textareaRef.current);
    }
  };

  // Xoá toàn bộ lịch sử và reset state
  const clearHistory = () => {
    setConversation([]);
    setError("");
    setStats({ totalQueries: 0, totalLatency: 0 });
    const reset = {};
    AGENT_PIPELINE.forEach((a) => { reset[a.id] = "idle"; });
    setAgentStates(reset);
  };

  // ── Computed values ──────────────────────────

  const avgLatency = stats.totalQueries
    ? (stats.totalLatency / stats.totalQueries).toFixed(1) + "s"
    : "—";

  const successRate = stats.totalQueries ? "100%" : "—";

  const lastComplexity =
    conversation.length > 0
      ? conversation[conversation.length - 1].complexity === "COMPLEX"
        ? "CoT"
        : "1-shot"
      : "—";

  // ── Render ───────────────────────────────────

  return (
    <>
      {/* ── Header ── */}
      <header>
        <div className="logo">
          <div className="logo-icon">🧠</div>
          <span>Text2SQL</span>
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

        {/* ── Vùng chat chính ── */}
        <main className="main">
          <div className="chat-history" ref={chatRef}>
            {/* Màn hình chào — chỉ hiện khi chưa có conversation */}
            {conversation.length === 0 && !loading && (
              <WelcomeScreen onSelectExample={useExample} />
            )}

            {/* Danh sách các lượt hội thoại */}
            {conversation.map((item) => (
              <ChatMessage key={item.id} item={item} />
            ))}

            {/* Ba chấm nhấp nháy khi đang chờ */}
            {loading && <TypingIndicator />}

            {/* Thông báo lỗi */}
            {error && (
              <div className="msg ai">
                <div className="msg-bubble error-bubble">⚠️ {error}</div>
              </div>
            )}
          </div>

          {/* ── Ô nhập liệu ── */}
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
          {/* Thống kê */}
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
                <div className="stat-val">{lastComplexity}</div>
                <div className="stat-key">Chiến lược</div>
              </div>
            </div>
          </div>

          {/* Lịch sử — 12 câu gần nhất, click để điền lại input */}
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
                      <div className="history-t">
                        {item.time} · {item.complexity}
                      </div>
                    </div>
                  ))
              )}
            </div>
          </div>

          {/* Danh sách pipeline + dot trạng thái */}
          <div className="rpanel-section">
            <div className="rpanel-label">🔧 Pipeline</div>
            <div className="pipeline-list">
              {AGENT_PIPELINE.map((agent) => (
                <div className="pipeline-item" key={agent.id}>
                  <span>{agent.icon}</span>
                  <span className="pipeline-name">{agent.name}</span>
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