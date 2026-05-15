import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "/api/chat";

const EXAMPLE_QUESTIONS = [
  "Top 3 sinh vien co GPA cao nhat thuoc khoa CNTT?",
  "Dem so sinh vien theo tung khoa.",
  "Sinh vien nao co GPA lon hon 3.5?",
];

export default function App() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [conversation, setConversation] = useState([]);

  const onSubmit = async (event) => {
    event.preventDefault();
    if (!message.trim()) {
      return;
    }

    const userMessage = message.trim();
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      });
      if (!res.ok) {
        throw new Error("Backend tra ve loi");
      }
      const data = await res.json();
      setConversation((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          userQuestion: userMessage,
          rewrittenQuery: data.rewritten_query,
          complexity: data.complexity,
          sql: data.sql,
          answer: data.answer,
          createdAt: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Da co loi xay ra");
    } finally {
      setLoading(false);
    }
  };

  const onSelectExample = (text) => setMessage(text);

  const clearConversation = () => {
    setConversation([]);
    setError("");
  };

  return (
    <main className="app-shell">
      <section className="app-header">
        <div>
          <h1>Text-to-SQL Chatbot</h1>
          <p>Nhap cau hoi bang ngon ngu tu nhien va theo doi pipeline SQL.</p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          onClick={clearConversation}
          disabled={!conversation.length}
        >
          Xoa lich su
        </button>
      </section>

      <section className="chat-input-panel">
        <form className="chat-form" onSubmit={onSubmit}>
          <textarea
            placeholder="Vi du: Top 3 sinh vien co GPA cao nhat thuoc khoa CNTT?"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={4}
            disabled={loading}
          />
          <div className="action-row">
            <button type="submit" disabled={loading || !message.trim()}>
              {loading ? "Dang xu ly..." : "Gui cau hoi"}
            </button>
          </div>
        </form>
        <div className="example-list">
          {EXAMPLE_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              className="chip"
              onClick={() => onSelectExample(question)}
            >
              {question}
            </button>
          ))}
        </div>
      </section>

      {error ? <p className="error">{error}</p> : null}

      <section className="conversation">
        {!conversation.length ? (
          <p className="empty-state">
            Chua co hoi dap nao. Gui cau hoi dau tien de bat dau.
          </p>
        ) : null}

        {conversation.map((item, index) => (
          <article className="chat-turn" key={item.id}>
            <p className="turn-label">Luot #{index + 1}</p>
            <p>
              <strong>User:</strong> {item.userQuestion}
            </p>
            <p>
              <strong>Rewritten Query:</strong> {item.rewrittenQuery}
            </p>
            <p>
              <strong>Complexity:</strong> {item.complexity}
            </p>
            <p>
              <strong>Generated SQL:</strong> <code>{item.sql}</code>
            </p>
            <p>
              <strong>Answer:</strong> {item.answer}
            </p>
          </article>
        ))}
      </section>
    </main>
  );
}
