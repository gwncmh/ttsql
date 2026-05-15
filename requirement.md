# Software Requirements Specification (SRS)

# Hệ Thống Text-to-SQL Đa Tác Tử Sử Dụng RAG và Adaptive Routing

---

# 1. Giới thiệu

## 1.1 Mục đích tài liệu

Tài liệu này mô tả đặc tả yêu cầu phần mềm cho hệ thống:

> **Multi-Agent Text-to-SQL System with RAG and Adaptive Routing**

Hệ thống cho phép người dùng nhập câu hỏi bằng ngôn ngữ tự nhiên và tự động:

- phân tích yêu cầu,
- truy xuất schema liên quan,
- sinh câu lệnh SQL,
- thực thi truy vấn,
- sửa lỗi SQL nếu cần,
- trả kết quả dưới dạng ngôn ngữ tự nhiên.

---

## 1.2 Phạm vi dự án

Hệ thống hỗ trợ:

- Chuyển đổi Natural Language → SQL
- Hỗ trợ truy vấn đơn giản và phức tạp
- Tự động chọn chiến lược sinh SQL
- Tự sửa lỗi SQL thông qua feedback loop
- Sinh câu trả lời tự nhiên cho người dùng

Hệ thống áp dụng cho:

- Chatbot dữ liệu doanh nghiệp
- Hệ thống hỏi đáp cơ sở dữ liệu
- AI Data Assistant
- Business Intelligence
- Database Query Automation

---

## 1.3 Định nghĩa và thuật ngữ

| Thuật ngữ | Ý nghĩa                             |
| --------- | ----------------------------------- |
| LLM       | Large Language Model                |
| RAG       | Retrieval-Augmented Generation      |
| CoT       | Chain-of-Thought                    |
| NLG       | Natural Language Generation         |
| SQL       | Structured Query Language           |
| Schema    | Cấu trúc cơ sở dữ liệu              |
| Agent     | Tác tử AI xử lý một nhiệm vụ cụ thể |

---

# 2. Tổng quan hệ thống

## 2.1 Kiến trúc tổng thể

```text
User Question
    ↓
Query Rewriter Agent
    ↓
Schema Retrieval Agent (RAG)
    ↓
Adaptive Router Agent
    ├── SIMPLE → SQL Generator (1-shot)
    └── COMPLEX → SQL Generator (CoT)
    ↓
Execution + Feedback Agent
    ↓
Answer Generation Agent (NLG)
    ↓
Final Answer
```

---

## 2.2 Mô hình kiến trúc

Hệ thống sử dụng:

- Multi-Agent Architecture
- Retrieval-Augmented Generation
- LLM-based SQL Generation
- Feedback-based Self-Correction

---

# 3. Yêu cầu chức năng

---

# FR-1: Tiếp nhận câu hỏi người dùng

## Mô tả

Hệ thống phải cho phép người dùng nhập câu hỏi bằng ngôn ngữ tự nhiên.

## Input

```text
Top 3 sinh viên có GPA cao nhất thuộc khoa CNTT?
```

## Output

Câu hỏi được chuyển đến Query Rewriter Agent.

---

# FR-2: Viết lại câu hỏi (Query Rewriting)

## Mô tả

Hệ thống phải chuẩn hóa câu hỏi nhằm:

- giảm ambiguity,
- tăng tính rõ ràng,
- hỗ trợ SQL generation.

---

## Input

```text
Top 3 sinh viên có GPA cao nhất thuộc khoa CNTT?
```

## Output

```text
Liệt kê 3 sinh viên có GPA cao nhất thuộc khoa CNTT,
sắp xếp giảm dần theo GPA.
```

---

## Điều kiện

- Không làm thay đổi ý nghĩa câu hỏi.
- Giữ nguyên entity quan trọng.

---

# FR-3: Truy xuất schema liên quan (Schema Retrieval)

## Mô tả

Hệ thống phải truy xuất các bảng, cột và quan hệ liên quan đến câu hỏi.

---

## Input

Rewritten Query.

## Output

### Relevant Tables

```text
students
majors
faculties
```

### Relevant Columns

```text
students.gpa
students.major_id
faculties.name
```

### Relevant Relations

```text
students.major_id = majors.id
majors.faculty_id = faculties.id
```

---

## Yêu cầu

- Hỗ trợ semantic search.
- Hỗ trợ vector retrieval.
- Hỗ trợ schema graph traversal.

---

# FR-4: Phân loại độ phức tạp truy vấn

## Mô tả

Hệ thống phải đánh giá độ phức tạp truy vấn SQL.

---

## SIMPLE Query

### Điều kiện

- SELECT đơn giản
- Ít JOIN
- Không subquery
- Không aggregation phức tạp

### Action

```text
Route → SQL Generator (1-shot)
```

---

## COMPLEX Query

### Điều kiện

- Multi JOIN
- GROUP BY
- HAVING
- Nested Query
- Subquery
- Set Operations

### Action

```text
Route → SQL Generator (CoT)
```

---

# FR-5: Sinh SQL

---

# FR-5.1: Sinh SQL kiểu 1-shot

## Mô tả

Hệ thống phải sinh trực tiếp SQL cho truy vấn đơn giản.

---

## Input

- Rewritten Query
- Relevant Schema

---

## Output

```sql
SELECT s.name, s.gpa
FROM students s
JOIN majors m ON s.major_id = m.id
JOIN faculties f ON m.faculty_id = f.id
WHERE f.name = 'CNTT'
ORDER BY s.gpa DESC
LIMIT 3;
```

---

# FR-5.2: Sinh SQL kiểu Chain-of-Thought

## Mô tả

Hệ thống phải hỗ trợ reasoning nhiều bước đối với truy vấn phức tạp.

---

## Ví dụ reasoning

```text
1. Xác định bảng students
2. Join bảng majors
3. Join bảng faculties
4. Lọc khoa CNTT
5. Sắp xếp GPA giảm dần
6. Giới hạn 3 kết quả
```

---

# FR-6: Thực thi SQL

## Mô tả

Hệ thống phải thực thi SQL trên Database Engine.

---

## Input

Generated SQL.

## Output

Kết quả truy vấn.

---

## Điều kiện

- Hỗ trợ SQLite/PostgreSQL/MySQL.
- Timeout phải được kiểm soát.
- Chỉ cho phép SELECT query.

---

# FR-7: Kiểm tra và sửa lỗi SQL

## Mô tả

Hệ thống phải phát hiện lỗi và tự sửa SQL.

---

## Các loại lỗi

| Loại lỗi         | Mô tả              |
| ---------------- | ------------------ |
| Syntax Error     | Sai cú pháp        |
| Column Not Found | Không tồn tại cột  |
| Table Not Found  | Không tồn tại bảng |
| Runtime Error    | Lỗi thực thi       |
| Empty Result     | Không có dữ liệu   |

---

## Feedback Loop

### Retry Policy

```text
Retry tối đa 3 lần
```

---

## Quy trình

```text
Generate SQL
    ↓
Execute SQL
    ↓
Error?
 ├── No → Success
 └── Yes → Repair SQL
```

---

# FR-8: Sinh câu trả lời tự nhiên

## Mô tả

Hệ thống phải chuyển kết quả SQL thành câu trả lời tự nhiên.

---

## Input

- User Question
- SQL Result

---

## Output

```text
Top 3 sinh viên có GPA cao nhất thuộc khoa CNTT là:
1. Nguyen A (3.95)
2. Tran B (3.80)
3. Le C (3.75)
```

---

# FR-9: Logging và Monitoring

## Mô tả

Hệ thống phải lưu:

- user query,
- rewritten query,
- generated SQL,
- execution status,
- retry count,
- latency.

---

# 4. Yêu cầu phi chức năng

---

# NFR-1: Hiệu năng

| Yêu cầu               | Giá trị   |
| --------------------- | --------- |
| Response Time         | < 10 giây |
| SQL Execution Timeout | ≤ 5 giây  |
| Retry Limit           | ≤ 3       |

---

# NFR-2: Độ chính xác

| Thành phần                 | Mục tiêu |
| -------------------------- | -------- |
| Schema Retrieval Accuracy  | ≥ 90%    |
| SQL Execution Success Rate | ≥ 85%    |

---

# NFR-3: Khả năng mở rộng

Hệ thống phải hỗ trợ:

- nhiều schema,
- nhiều database,
- nhiều domain dữ liệu.

---

# NFR-4: Bảo mật

Hệ thống phải:

- chặn SQL Injection,
- chỉ cho phép SELECT,
- validate generated SQL,
- giới hạn quyền DB user.

---

# NFR-5: Khả năng bảo trì

Hệ thống phải hỗ trợ:

- modular agents,
- dễ mở rộng pipeline,
- logging đầy đủ,
- config model động.

---

# 5. Thiết kế thành phần

---

# 5.1 Query Rewriter Agent

## Chức năng

- Query normalization
- Intent enhancement
- Ambiguity reduction

---

# 5.2 Schema Retrieval Agent

## Chức năng

- Vector retrieval
- Schema linking
- FK graph traversal

---

# 5.3 Adaptive Router Agent

## Chức năng

- Complexity classification
- Dynamic routing

---

# 5.4 SQL Generator

## Chức năng

- SQL synthesis
- Reasoning generation
- Prompt-based generation

---

# 5.5 Execution & Feedback Agent

## Chức năng

- Execute SQL
- Detect error
- Repair SQL

---

# 5.6 Answer Generation Agent

## Chức năng

- NLG
- Response summarization

---

# 6. Công nghệ đề xuất

| Thành phần      | Công nghệ             |
| --------------- | --------------------- |
| Backend         | Python / FastAPI      |
| LLM             | GPT / Claude / Llama  |
| Vector DB       | FAISS / Chroma        |
| Database        | PostgreSQL / SQLite   |
| Embedding Model | Sentence Transformers |
| Orchestration   | LangChain / LangGraph |
| Monitoring      | LangSmith             |

---

# 7. Use Case chính

---

# UC-1: Truy vấn dữ liệu

## Actor

Người dùng.

## Flow

1. User nhập câu hỏi.
2. Query được rewrite.
3. Schema được retrieve.
4. Router phân loại query.
5. SQL được generate.
6. SQL được execute.
7. Nếu lỗi → repair.
8. Trả kết quả tự nhiên.

---

# 8. Ràng buộc hệ thống

- Chỉ hỗ trợ read-only query.
- Không cho phép INSERT/UPDATE/DELETE.
- Không cho phép query nguy hiểm.
- Phụ thuộc vào chất lượng schema metadata.

---

# 9. Hướng phát triển tương lai

- Multi-turn conversation
- Query memory
- Visualization generation
- Fine-tuned SQL model
- Self-learning feedback
- Hybrid symbolic reasoning

---

# 10. Kết luận

Hệ thống Multi-Agent Text-to-SQL với RAG và Adaptive Routing giúp:

- tăng độ chính xác sinh SQL,
- giảm lỗi thực thi,
- hỗ trợ reasoning phức tạp,
- cải thiện trải nghiệm truy vấn dữ liệu bằng ngôn ngữ tự nhiên.

Kiến trúc đa tác tử giúp hệ thống:

- dễ mở rộng,
- dễ bảo trì,
- tối ưu hiệu năng,
- phù hợp các hệ thống AI Data Assistant hiện đại.
