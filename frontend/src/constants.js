// ─────────────────────────────────────────────
// constants.js
// Chứa toàn bộ dữ liệu tĩnh dùng trong app.
// Tách ra đây để App.jsx và components gọn hơn,
// và dễ chỉnh nội dung mà không cần đụng vào logic.
// ─────────────────────────────────────────────

// URL gọi API backend — đọc từ biến môi trường Vite,
// nếu không có thì fallback về "/api/chat" (dùng Vite proxy local)
export const API_URL = import.meta.env.VITE_API_URL || "/api/chat";

// Danh sách bảng hiển thị trong sidebar Schema
// cols: các cột mẫu để preview, không cần đủ hết
export const SCHEMA_TABLES = [
  { name: "students",  cols: ["id", "name", "gpa", "major_id", "year"] },
  { name: "majors",    cols: ["id", "name", "faculty_id"] },
  { name: "faculties", cols: ["id", "name", "dean"] },
  { name: "scores",    cols: ["id", "student_id", "subject", "score"] },
];

// Câu hỏi mẫu hiển thị ở màn hình chào
// icon: emoji hiển thị trước câu hỏi
// text: nội dung câu hỏi điền vào input khi click
export const EXAMPLE_QUESTIONS = [
  { icon: "🏆", text: "Top 3 sinh viên có GPA cao nhất thuộc khoa CNTT?" },
  { icon: "📊", text: "Đếm số sinh viên theo từng khoa." },
  { icon: "⭐", text: "Sinh viên nào có GPA lớn hơn 3.5?" },
  { icon: "📈", text: "GPA trung bình của từng ngành là bao nhiêu?" },
];

// Các bước trong pipeline AI — theo đúng thứ tự xử lý
// id: dùng làm key trong agentStates (idle | thinking | done)
// name: tên hiển thị
// icon: emoji đại diện
export const AGENT_PIPELINE = [
  { id: "rewriter",  name: "Query Rewriter",   icon: "✍️" },
  { id: "schema",    name: "Schema Retrieval",  icon: "🔍" },
  { id: "router",    name: "Adaptive Router",   icon: "⚡" },
  { id: "generator", name: "SQL Generator",     icon: "⚙️" },
  { id: "executor",  name: "Executor",          icon: "▶️" },
];

// Từ khóa SQL được highlight màu đỏ trong SQL block
export const SQL_KEYWORDS = [
  "SELECT","FROM","WHERE","JOIN","LEFT","RIGHT","INNER","OUTER","GROUP BY",
  "ORDER BY","HAVING","LIMIT","AS","ON","AND","OR","NOT","IN","DISTINCT",
  "UNION","ALL","CASE","WHEN","THEN","ELSE","END","WITH","DESC","ASC",
];

// Tên hàm SQL được highlight màu xanh dương trong SQL block
export const SQL_FUNCTIONS = [
  "COUNT","SUM","AVG","MAX","MIN","ROUND","COALESCE","CONCAT","LENGTH",
  "SUBSTR","TRIM","UPPER","LOWER","CAST","NOW","DATE","YEAR","MONTH",
];