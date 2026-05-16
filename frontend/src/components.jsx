// ─────────────────────────────────────────────
// components.jsx
// Tất cả các UI component nhỏ dùng trong App.jsx.
// Mỗi component chỉ nhận props, không giữ state phức tạp
// (trừ SQLBlock giữ state "copied" cho nút copy).
// ─────────────────────────────────────────────

import { useState } from "react";
import { SCHEMA_TABLES, AGENT_PIPELINE, EXAMPLE_QUESTIONS } from "./constants";
import { highlightSQL } from "./utils";

// ── AgentStatusPanel ──────────────────────────
// Hiển thị trạng thái từng bước trong pipeline AI ở sidebar trái.
// agentStates: object dạng { rewriter: "idle"|"thinking"|"done", ... }
export function AgentStatusPanel({ agentStates }) {
  return (
    <div className="agent-status">
      {AGENT_PIPELINE.map((agent) => {
        const state = agentStates[agent.id] || "idle";
        return (
          <div className="agent-row" key={agent.id}>
            {/* Chấm tròn đổi màu theo state: xám/vàng nhấp nháy/xanh */}
            <div className={`agent-dot ${state}`} />
            <span className="agent-name">
              {agent.icon} {agent.name}
            </span>
            {/* Label phải: hiện "Đang chạy..." hoặc "✓" hoặc "—" */}
            <span className="agent-label">
              {state === "thinking" ? "Đang chạy..." : state === "done" ? "✓" : "—"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── SchemaPanel ───────────────────────────────
// Danh sách bảng DB hiển thị ở sidebar trái.
// activeTable: index bảng đang được chọn (highlight xanh)
// onSelectTable: callback khi click vào một bảng
export function SchemaPanel({ activeTable, onSelectTable }) {
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
            {/* Hiện tối đa 4 cột, nếu nhiều hơn thêm "…" */}
            <div className="schema-cols">
              {t.cols.slice(0, 4).join(", ")}
              {t.cols.length > 4 ? ", …" : ""}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── SQLBlock ──────────────────────────────────
// Khung hiển thị câu SQL với syntax highlighting và nút copy.
// sql: chuỗi SQL thô cần hiển thị
export function SQLBlock({ sql }) {
  // copied: true trong 1.5s sau khi bấm copy → đổi text nút
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
      {/*
        dangerouslySetInnerHTML dùng ở đây vì highlightSQL() trả về HTML string
        có các <span> màu sắc. Input đã được escapeHTML() trước → an toàn.
      */}
      <div
        className="sql-code"
        dangerouslySetInnerHTML={{ __html: highlightSQL(sql) }}
      />
    </div>
  );
}

// ── ThinkingTrace ─────────────────────────────
// Accordion "Quá trình xử lý đa tác tử" — có thể bấm để mở/đóng.
// Hiển thị các bước pipeline đã chạy sau khi có kết quả.
// complexity: "SIMPLE" | "COMPLEX" — ảnh hưởng text mô tả bước generator
export function ThinkingTrace({ complexity }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`thinking-trace ${open ? "open" : ""}`}>
      <div className="thinking-header" onClick={() => setOpen(!open)}>
        <div className="thinking-dot" />
        Quá trình xử lý đa tác tử
        {/* Mũi tên xoay 180° khi open (CSS transition) */}
        <span className="thinking-chevron">▾</span>
      </div>

      <div className="thinking-body">
        {AGENT_PIPELINE.map((agent) => (
          <div className="trace-step done" key={agent.id}>
            <span className="step-icon">✓</span>
            <span className="step-text">
              {/* Mô tả ngắn cho từng bước, tuỳ agent id */}
              {agent.id === "rewriter"  && "Chuẩn hóa câu hỏi đầu vào"}
              {agent.id === "schema"    && "Truy xuất schema liên quan (RAG)"}
              {agent.id === "router"    && `Phân loại → ${complexity || "SIMPLE"}`}
              {agent.id === "generator" && `Sinh SQL (${complexity === "COMPLEX" ? "Chain-of-Thought" : "1-shot"})`}
              {agent.id === "executor"  && "Thực thi SQL trên PostgreSQL"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── TypingIndicator ───────────────────────────
// Ba chấm nhấp nháy hiển thị khi đang chờ phản hồi từ backend.
// Không nhận props — hoàn toàn CSS animation.
export function TypingIndicator() {
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

// ── ChatMessage ───────────────────────────────
// Một cặp tin nhắn: user bubble (phải) + AI response (trái).
// item: object từ conversation state, gồm:
//   userQuestion, rewrittenQuery, complexity, sql, answer, elapsed, time
export function ChatMessage({ item }) {
  return (
    <>
      {/* Bubble người dùng — căn phải */}
      <div className="msg user">
        <div className="msg-bubble">{item.userQuestion}</div>
        <div className="msg-meta">{item.time}</div>
      </div>

      {/* Phản hồi AI — căn trái */}
      <div className="msg ai">
        <ThinkingTrace complexity={item.complexity} />
        <SQLBlock sql={item.sql} />

        {/* Card kết quả truy vấn */}
        <div className="result-card">
          <div className="result-header">
            <span style={{ color: "var(--green)", fontSize: 14 }}>✓</span>
            <span className="result-title">Kết quả truy vấn</span>
            {/* Hiện thời gian xử lý (giây) ở góc phải */}
            <span className="result-count">{item.elapsed}s</span>
          </div>
          <div style={{ padding: "12px 14px" }}>
            {/*
              answer từ backend là plain text hiện tại.
              Nếu sau này backend trả HTML thì cần sanitize trước!
            */}
            <div
              style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.7 }}
              dangerouslySetInnerHTML={{ __html: item.answer }}
            />
          </div>
        </div>

        {/* Metadata nhỏ bên dưới: giờ · độ phức tạp · thời gian */}
        <div className="msg-meta">
          {item.time} · {item.complexity} · {item.elapsed}s
        </div>

        {/* Câu hỏi đã được rewrite — dạng chữ nghiêng nhỏ */}
        <div className="msg-rewritten">
          Rewritten: {item.rewrittenQuery}
        </div>
      </div>
    </>
  );
}

// ── WelcomeScreen ─────────────────────────────
// Màn hình chào khi chưa có conversation nào.
// onSelectExample: callback nhận text câu hỏi mẫu khi click pill
export function WelcomeScreen({ onSelectExample }) {
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