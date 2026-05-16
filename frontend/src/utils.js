// ─────────────────────────────────────────────
// utils.js
// Các hàm tiện ích dùng chung trong app.
// Không chứa JSX, không chứa state — pure functions.
// ─────────────────────────────────────────────

import { SQL_KEYWORDS, SQL_FUNCTIONS } from "./constants";

// Trả về giờ hiện tại dạng "HH:MM" theo múi giờ Việt Nam
// Dùng để gắn timestamp vào mỗi tin nhắn trong conversation
export function timeNow() {
  return new Date().toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Escape các ký tự đặc biệt HTML để tránh XSS khi render string thô
// Phải chạy hàm này TRƯỚC khi inject HTML bằng dangerouslySetInnerHTML
// & → &amp;   < → &lt;   > → &gt;
export function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// Highlight cú pháp SQL — trả về string HTML có các <span> màu sắc
// Thứ tự quan trọng: comment → string → số → function → keyword
// Đảo thứ tự có thể làm regex match nhầm bên trong nhau
export function highlightSQL(sql) {
  // Bước 1: escape HTML để an toàn trước khi thêm thẻ
  let h = escapeHTML(sql);

  // Bước 2: highlight comment SQL (-- đến hết dòng) → màu xám
  h = h.replace(/(--[^\n]*)/g, '<span class="sql-cmt">$1</span>');

  // Bước 3: highlight string literal ('...') → màu xanh nhạt
  h = h.replace(/('[^']*')/g, '<span class="sql-str">$1</span>');

  // Bước 4: highlight số nguyên và thập phân → màu xanh dương
  // \b là word boundary — tránh match số bên trong tên cột
  h = h.replace(/\b(\d+\.?\d*)\b/g, '<span class="sql-num">$1</span>');

  // Bước 5: highlight tên hàm SQL (COUNT, AVG...) → màu xanh dương
  // flag "gi": g = tất cả, i = case-insensitive
  SQL_FUNCTIONS.forEach((fn) => {
    h = h.replace(
      new RegExp(`\\b(${fn})\\b`, "gi"),
      '<span class="sql-fn">$1</span>'
    );
  });

  // Bước 6: highlight từ khóa SQL (SELECT, FROM...) → màu đỏ
  // Dùng \\s+ cho "GROUP BY" / "ORDER BY" để match khoảng trắng giữa 2 từ
  SQL_KEYWORDS.forEach((kw) => {
    const esc = kw.replace(" ", "\\s+");
    h = h.replace(
      new RegExp(`\\b(${esc})\\b`, "gi"),
      '<span class="sql-kw">$1</span>'
    );
  });

  return h;
}