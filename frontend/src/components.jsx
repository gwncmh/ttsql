// ─────────────────────────────────────────────
// components.jsx — fix bảng, logo, scroll
// ─────────────────────────────────────────────
import { useState, useEffect } from "react";
import { SCHEMA_TABLES, AGENT_PIPELINE, EXAMPLE_QUESTIONS } from "./constants";
import { highlightSQL, escapeHTML } from "./utils";

// ── Toast ─────────────────────────────────────
let _setToast = null;
export function ToastProvider() {
  const [toast, setToast] = useState(null);
  useEffect(() => {
    _setToast = (msg, type = "success") => setToast({ msg, type, id: Date.now() });
    return () => { _setToast = null; };
  }, []);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(t);
  }, [toast]);
  if (!toast) return null;
  return (
    <div key={toast.id} style={{
      position:"fixed",top:20,right:20,zIndex:9999,
      background:toast.type==="error"?"var(--red-dim)":"var(--green-dim)",
      border:`1px solid ${toast.type==="error"?"rgba(252,129,129,0.4)":"rgba(104,211,145,0.4)"}`,
      color:toast.type==="error"?"var(--red)":"var(--green)",
      padding:"10px 16px",borderRadius:"var(--radius)",fontSize:13,fontWeight:500,
      display:"flex",alignItems:"center",gap:8,
      boxShadow:"0 4px 20px rgba(0,0,0,0.4)",animation:"toastIn 0.2s ease",
    }}>
      {toast.type==="error"?"⚠️":"✓"} {toast.msg}
    </div>
  );
}
export function showToast(msg, type = "success") { _setToast?.(msg, type); }

// ── Logo — ảnh từ /assets/logo.png ───────────
export function Logo() {
  const [imgErr, setImgErr] = useState(false);
  return (
    <div className="logo">
      {!imgErr ? (
        <img src="dist/assets/logo.png" alt="Logo" className="logo-img"
          onError={() => setImgErr(true)} />
      ) : (
        <div className="logo-icon">🧠</div>
      )}
      <span>Text2SQL</span>
    </div>
  );
}

// ── AgentStatusPanel ──────────────────────────
export function AgentStatusPanel({ agentStates }) {
  return (
    <div className="agent-status">
      {AGENT_PIPELINE.map((agent) => {
        const state = agentStates[agent.id] || "idle";
        return (
          <div className="agent-row" key={agent.id}>
            <div className={`agent-dot ${state}`} />
            <span className="agent-name">{agent.icon} {agent.name}</span>
            <span className="agent-label">
              {state==="thinking"?"Đang chạy...":state==="done"?"✓":"—"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── SchemaPanel — expandable ──────────────────
export function SchemaPanel({ activeTable, onSelectTable }) {
  const [expanded, setExpanded] = useState(null);
  const toggle = (i) => { setExpanded(expanded===i?null:i); onSelectTable(i); };
  const FK_MAP = {
    students:["major_id → majors.id"],
    majors:["faculty_id → faculties.id"],
    scores:["student_id → students.id"],
    faculties:[],
  };
  return (
    <div id="schema-list">
      {SCHEMA_TABLES.map((t, i) => (
        <div key={t.name}>
          <div className={`schema-item ${activeTable===i?"active":""}`} onClick={() => toggle(i)}>
            <div className="schema-icon">⬡</div>
            <div style={{flex:1}}>
              <div className="schema-name">{t.name}</div>
              <div className="schema-cols">{t.cols.slice(0,4).join(", ")}{t.cols.length>4?", …":""}</div>
            </div>
            <span style={{fontSize:10,color:"var(--text-dim)",marginLeft:4}}>{expanded===i?"▲":"▼"}</span>
          </div>
          {expanded===i && (
            <div style={{background:"var(--bg)",border:"1px solid var(--border)",borderTop:"none",borderRadius:"0 0 var(--radius) var(--radius)",padding:"8px 10px",marginBottom:4}}>
              <div style={{fontSize:10,color:"var(--text-dim)",marginBottom:6,textTransform:"uppercase",letterSpacing:1}}>Cột</div>
              {t.cols.map(col => (
                <div key={col} style={{display:"flex",alignItems:"center",gap:6,marginBottom:3}}>
                  <span style={{fontSize:11,color:"var(--accent)",fontFamily:"var(--font-mono)"}}>{col}</span>
                  {col==="id"&&<span style={{fontSize:9,color:"var(--amber)",background:"rgba(246,173,85,0.1)",padding:"1px 5px",borderRadius:4}}>PK</span>}
                  {col.endsWith("_id")&&col!=="id"&&<span style={{fontSize:9,color:"var(--purple)",background:"rgba(183,148,244,0.1)",padding:"1px 5px",borderRadius:4}}>FK</span>}
                </div>
              ))}
              {FK_MAP[t.name]?.length>0&&(
                <>
                  <div style={{fontSize:10,color:"var(--text-dim)",marginTop:8,marginBottom:4,textTransform:"uppercase",letterSpacing:1}}>Quan hệ</div>
                  {FK_MAP[t.name].map(fk=><div key={fk} style={{fontSize:10,color:"var(--text-muted)",fontFamily:"var(--font-mono)"}}>→ {fk}</div>)}
                </>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── SQLBlock ──────────────────────────────────
export function SQLBlock({ sql }) {
  const handleCopy = () => navigator.clipboard.writeText(sql).then(()=>showToast("Đã sao chép SQL!"));
  return (
    <div className="sql-block">
      <div className="sql-header">
        <span className="sql-lang">SQL</span>
        <button className="sql-copy" onClick={handleCopy}>Sao chép</button>
      </div>
      <div className="sql-code" dangerouslySetInnerHTML={{__html:highlightSQL(sql)}} />
    </div>
  );
}

function ResultTable({ rows }) {
  if (!rows || rows.length === 0) return null;
  const headers = Object.keys(rows[0]);
  const exportCSV = () => {
    const csvRows = [
      headers.join(","),
      ...rows.map(r => headers.map(h => `"${String(r[h] ?? "").replace(/"/g, '""')}"`).join(","))
    ];
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `query_result_${Date.now()}.csv`; a.click();
    URL.revokeObjectURL(url);
    showToast("Đã tải CSV!");
  };
  return (
    <>
      <div className="result-body">
        <table className="result-table">
          <thead><tr>{headers.map(h => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>{headers.map(h => <td key={h} title={String(row[h] ?? "")}>{String(row[h] ?? "—")}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="result-footer">
        <span className="result-row-count">{rows.length} dòng</span>
        <button className="btn-export-csv" onClick={exportCSV}>↓ Tải CSV</button>
      </div>
    </>
  );
}

// ── ThinkingTrace ─────────────────────────────
export function ThinkingTrace({ complexity }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`thinking-trace ${open?"open":""}`}>
      <div className="thinking-header" onClick={()=>setOpen(!open)}>
        <div className="thinking-dot" />
        Quá trình xử lý đa tác tử
        <span className="thinking-chevron">▾</span>
      </div>
      <div className="thinking-body">
        {AGENT_PIPELINE.map((agent)=>(
          <div className="trace-step done" key={agent.id}>
            <span className="step-icon">✓</span>
            <span className="step-text">
              {agent.id==="rewriter"&&"Chuẩn hóa câu hỏi đầu vào"}
              {agent.id==="schema"&&"Truy xuất schema liên quan (RAG)"}
              {agent.id==="router"&&`Phân loại → ${complexity||"SIMPLE"}`}
              {agent.id==="generator"&&`Sinh SQL (${complexity==="COMPLEX"?"Chain-of-Thought":"1-shot"})`}
              {agent.id==="executor"&&"Thực thi SQL trên PostgreSQL"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── TypingIndicator ───────────────────────────
export function TypingIndicator() {
  return (
    <div className="msg ai">
      <div className="typing-indicator">
        <div className="typing-dot"/><div className="typing-dot"/><div className="typing-dot"/>
      </div>
    </div>
  );
}

// ── SkeletonLine helper ───────────────────────
function SkeletonLine({width="100%"}) {
  return <div style={{height:12,width,background:"rgba(255,255,255,0.06)",borderRadius:4,animation:"pulse 1.5s infinite"}}/>;
}

// ── LoadingSkeleton ───────────────────────────
export function LoadingSkeleton({ userQuestion }) {
  return (
    <>
      <div className="msg user">
        <div className="msg-bubble">{userQuestion}</div>
      </div>
      <div className="msg ai">
        <div className="thinking-trace">
          <div className="thinking-header" style={{cursor:"default"}}>
            <div className="thinking-dot" style={{background:"var(--amber)",animation:"pulse 1s infinite"}}/>
            Đang xử lý...
          </div>
        </div>
        <div className="sql-block">
          <div className="sql-header"><span className="sql-lang">SQL</span></div>
          <div className="sql-code" style={{display:"flex",flexDirection:"column",gap:6}}>
            <SkeletonLine width="70%"/><SkeletonLine width="90%"/><SkeletonLine width="55%"/>
          </div>
        </div>
        <div className="result-card">
          <div className="result-header">
            <span style={{color:"var(--text-dim)",fontSize:14}}>◌</span>
            <span className="result-title" style={{color:"var(--text-dim)"}}>Đang chờ kết quả...</span>
          </div>
          <div style={{padding:"12px 14px",display:"flex",flexDirection:"column",gap:6}}>
            <SkeletonLine width="80%"/><SkeletonLine width="65%"/><SkeletonLine width="75%"/>
          </div>
        </div>
      </div>
    </>
  );
}

// ── ErrorMessage ──────────────────────────────
export function ErrorMessage({ error, onRetry }) {
  const getInfo = (err) => {
    if (!err) return {icon:"⚠️",title:"Lỗi không xác định",hint:null};
    const m = err.toLowerCase();
    if (m.includes("timeout")||m.includes("timed out")) return {icon:"⏱️",title:"Timeout",hint:"Backend mất quá lâu. Thử lại?"};
    if (m.includes("sql")||m.includes("database")||m.includes("query")) return {icon:"🗄️",title:"Lỗi SQL",hint:err};
    if (m.includes("llm")||m.includes("openrouter")||m.includes("api")) return {icon:"🤖",title:"Lỗi LLM",hint:"Không kết nối được AI. Kiểm tra API key."};
    if (m.includes("network")||m.includes("fetch")||m.includes("failed to fetch")) return {icon:"📡",title:"Lỗi mạng",hint:"Không kết nối được backend."};
    return {icon:"⚠️",title:"Lỗi",hint:err};
  };
  const info = getInfo(error);
  return (
    <div className="msg ai">
      <div style={{background:"var(--red-dim)",border:"1px solid rgba(252,129,129,0.3)",borderRadius:"var(--radius)",padding:"12px 14px",display:"flex",alignItems:"flex-start",gap:10}}>
        <span style={{fontSize:18}}>{info.icon}</span>
        <div style={{flex:1}}>
          <div style={{fontWeight:600,color:"var(--red)",fontSize:13}}>{info.title}</div>
          {info.hint&&<div style={{fontSize:12,color:"var(--text-muted)",marginTop:3}}>{info.hint}</div>}
        </div>
        {onRetry&&(
          <button onClick={onRetry} style={{fontSize:11,padding:"4px 10px",border:"1px solid rgba(252,129,129,0.4)",borderRadius:"var(--radius-pill)",background:"transparent",color:"var(--red)",cursor:"pointer",whiteSpace:"nowrap",fontFamily:"var(--font-body)"}}>
            Thử lại ↺
          </button>
        )}
      </div>
    </div>
  );
}

// ── ChatMessage ───────────────────────────────
export function ChatMessage({ item, onEdit }) {
  const safeAnswer = escapeHTML(item.answer || "").replace(/\n/g, "<br/>");
  const rows = item.rows || [];           // lấy từ backend, không parse text
  const hasTable = rows.length > 1;       // > 1 dòng mới hiển thị bảng

  return (
    <>
      <div className="msg user">
        <div className="msg-bubble">{item.userQuestion}</div>
        <div className="msg-meta" style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
          <span>{item.time}</span>
          <button onClick={() => onEdit?.(item.userQuestion)}
            style={{ background: "none", border: "none", color: "var(--text-dim)", cursor: "pointer", fontSize: 11, padding: "2px 6px", borderRadius: 4, fontFamily: "var(--font-body)" }}
            title="Chỉnh sửa câu hỏi này">
            ✎ Sửa
          </button>
        </div>
      </div>

      <div className="msg ai">
        <ThinkingTrace complexity={item.complexity} />
        <SQLBlock sql={item.sql} />

        <div className="result-card">
          <div className="result-header">
            <span style={{ color: "var(--green)", fontSize: 14 }}>✓</span>
            <span className="result-title">Kết quả truy vấn</span>
            <span className="result-count">{item.elapsed}s</span>
          </div>

          {/* Answer — luôn hiển thị, kể cả khi có bảng */}
          <div
            style={{ padding: "10px 14px", fontSize: 13, color: "var(--text)", lineHeight: 1.7, borderBottom: hasTable ? "1px solid var(--border)" : "none" }}
            dangerouslySetInnerHTML={{ __html: safeAnswer }}
          />

          {/* Bảng — chỉ hiển thị khi có nhiều hơn 1 dòng */}
          {hasTable && <ResultTable rows={rows} />}
        </div>

        <div className="msg-meta">{item.time} · {item.complexity} · {item.elapsed}s</div>
        <div className="msg-rewritten">Rewritten: {item.rewrittenQuery}</div>
      </div>
    </>
  );
}

// ── WelcomeScreen ─────────────────────────────
export function WelcomeScreen({ onSelectExample }) {
  return (
    <div className="welcome" id="welcome-screen">
      <div className="welcome-icon">💬</div>
      <h2>Hỏi đáp cơ sở dữ liệu</h2>
      <p>Đặt câu hỏi bằng ngôn ngữ tự nhiên, hệ thống đa tác tử sẽ tự động tạo SQL và trả kết quả cho bạn.</p>
      <div className="example-pills">
        {EXAMPLE_QUESTIONS.map((e)=>(
          <button key={e.text} className="example-pill" onClick={()=>onSelectExample(e.text)}>
            <span className="pill-icon">{e.icon}</span>{e.text}
          </button>
        ))}
      </div>
    </div>
  );
}