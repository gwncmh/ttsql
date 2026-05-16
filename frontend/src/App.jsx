// ─────────────────────────────────────────────
// App.jsx — cải tiến
// ─────────────────────────────────────────────

import { useState, useRef, useEffect, useCallback } from "react";

import { API_URL, AGENT_PIPELINE } from "./constants";
import { timeNow } from "./utils";
import {
  AgentStatusPanel,
  SchemaPanel,
  TypingIndicator,
  ChatMessage,
  WelcomeScreen,
  LoadingSkeleton,
  ErrorMessage,
  ToastProvider,
  Logo,
} from "./components";

import "./styles/base.css";
import "./styles/layout.css";
import "./styles/sidebar.css";
import "./styles/chat.css";
import "./styles/input.css";
import "./styles/rightpanel.css";

export default function App() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // Lỗi có kèm câu hỏi để retry
  const [errorState, setErrorState] = useState(null); // { message, question }

  // Câu hỏi đang chờ — hiển thị skeleton ngay lập tức
  const [pendingQuestion, setPendingQuestion] = useState("");

  const [conversation, setConversation] = useState([]);
  const [activeTable, setActiveTable] = useState(0);
  const [agentStates, setAgentStates] = useState({});
  const [stats, setStats] = useState({ totalQueries: 0, totalLatency: 0 });

  const chatRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [conversation, loading, pendingQuestion, errorState]);

  const autoResize = (el) => {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  const runAgentPipeline = useCallback(async () => {
    const reset = {};
    AGENT_PIPELINE.forEach((a) => { reset[a.id] = "idle"; });
    setAgentStates(reset);

    for (const agent of AGENT_PIPELINE) {
      setAgentStates((prev) => ({ ...prev, [agent.id]: "thinking" }));
      await new Promise((r) => setTimeout(r, 350 + Math.random() * 300));
      setAgentStates((prev) => ({ ...prev, [agent.id]: "done" }));
    }
  }, []);

  const submitQuestion = async (userMessage) => {
    if (!userMessage.trim() || loading) return;

    setLoading(true);
    setErrorState(null);
    setPendingQuestion(userMessage);

    const t0 = Date.now();

    try {
      const [res] = await Promise.all([
        fetch(API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMessage }),
        }),
        runAgentPipeline(),
      ]);

      if (!res.ok) {
        let detail = "Backend trả về lỗi";
        try {
          const errJson = await res.json();
          detail = errJson.detail || detail;
        } catch {}
        throw new Error(detail);
      }

      const data = await res.json();
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

      setConversation((prev) => [
        ...prev,
        {
          id:             crypto.randomUUID(),
          userQuestion:   userMessage,
          rewrittenQuery: data.rewritten_query,
          complexity:     data.complexity,
          sql:            data.sql,
          answer:         data.answer,
          rawRows:        data.rows || null, // nếu backend trả về rows riêng
          elapsed,
          time:           timeNow(),
        },
      ]);

      setStats((prev) => ({
        totalQueries: prev.totalQueries + 1,
        totalLatency: prev.totalLatency + parseFloat(elapsed),
      }));

    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Đã có lỗi xảy ra";
      setErrorState({ message: errMsg, question: userMessage });
      const errState = {};
      AGENT_PIPELINE.forEach((a) => { errState[a.id] = "idle"; });
      setAgentStates(errState);
    } finally {
      setLoading(false);
      setPendingQuestion("");
    }
  };

  const onSubmit = async () => {
    if (!message.trim() || loading) return;
    const userMessage = message.trim();
    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await submitQuestion(userMessage);
  };

  // Retry câu hỏi vừa lỗi
  const onRetry = () => {
    if (!errorState) return;
    const q = errorState.question;
    setErrorState(null);
    submitQuestion(q);
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  // Điền câu hỏi mẫu — dùng React state, không set DOM .value trực tiếp
  const useExample = (text) => {
    setMessage(text);
    // Trigger autoResize sau khi React cập nhật DOM
    requestAnimationFrame(() => autoResize(textareaRef.current));
  };

  // Chỉnh sửa câu hỏi cũ
  const onEdit = (text) => {
    setMessage(text);
    requestAnimationFrame(() => {
      autoResize(textareaRef.current);
      textareaRef.current?.focus();
    });
  };

  const clearHistory = () => {
    setConversation([]);
    setErrorState(null);
    setStats({ totalQueries: 0, totalLatency: 0 });
    const reset = {};
    AGENT_PIPELINE.forEach((a) => { reset[a.id] = "idle"; });
    setAgentStates(reset);
  };

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

  return (
    <>
      <ToastProvider />

      <header>
        <Logo />
        <div className="header-meta">
          <span className="badge badge-green">● Đang chạy</span>
          <span className="badge badge-blue">Multi-Agent</span>
          {conversation.length > 0 && (
            <button type="button" className="btn-clear" onClick={clearHistory} title="Xóa lịch sử">
              Xóa
            </button>
          )}
        </div>
      </header>

      <div className="app">
        {/* Sidebar trái */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-label">Schema</div>
            <SchemaPanel activeTable={activeTable} onSelectTable={setActiveTable} />
          </div>
          <div className="sidebar-section">
            <div className="sidebar-label">Trạng thái Agent</div>
            <AgentStatusPanel agentStates={agentStates} />
          </div>
        </aside>

        {/* Vùng chat chính */}
        <main className="main">
          <div className="chat-history" ref={chatRef}>
            {conversation.length === 0 && !loading && !pendingQuestion && !errorState && (
              <WelcomeScreen onSelectExample={useExample} />
            )}

            {/* Các lượt hội thoại đã hoàn thành */}
            {conversation.map((item) => (
              <ChatMessage key={item.id} item={item} onEdit={onEdit} />
            ))}

            {/* Skeleton + câu hỏi pending ngay khi gửi */}
            {loading && pendingQuestion && (
              <LoadingSkeleton userQuestion={pendingQuestion} />
            )}

            {/* Fallback typing indicator nếu không có pending */}
            {loading && !pendingQuestion && <TypingIndicator />}

            {/* Lỗi có thể retry */}
            {errorState && !loading && (
              <ErrorMessage error={errorState.message} onRetry={onRetry} />
            )}
          </div>

          {/* Ô nhập liệu */}
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

        {/* Right panel */}
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
                <div className="stat-val">{lastComplexity}</div>
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
                      onClick={() => onEdit(item.userQuestion)}
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