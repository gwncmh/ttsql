// ─────────────────────────────────────────────
// main.jsx
// Entry point của app — mount React vào #root.
// CSS đã chuyển sang import trong App.jsx,
// nên file này chỉ cần render App thôi.
// ─────────────────────────────────────────────

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

// KHÔNG import styles.css ở đây nữa —
// App.jsx đã import từng file CSS riêng trong styles/

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);