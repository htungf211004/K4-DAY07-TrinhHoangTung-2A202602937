# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Trịnh Hoàng Tùng
**Nhóm:** phoboi
**Ngày:** 19/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Khi hai đoạn văn bản có độ tương tự cosine cao, điều đó có nghĩa là các vector embedding của chúng chỉ cùng một hướng trong không gian nhiều chiều — tức là chúng mang ý nghĩa ngữ nghĩa (semantic meaning) tương tự nhau. Giá trị cosine similarity gần 1.0 cho thấy hai văn bản nói về cùng một chủ đề hoặc ý tưởng.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Sinh viên đăng ký học phần qua cổng thông tin đào tạo."
- Câu B: "Người học ghi danh môn học trên hệ thống quản lý đào tạo."
- Tại sao tương đồng: Cả hai câu đều nói về hành động đăng ký/ghi danh học phần của sinh viên trên hệ thống, chỉ khác cách diễn đạt (paraphrase).

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Thư viện mở cửa từ 8h đến 21h các ngày trong tuần."
- Câu B: "Công thức nấu phở bò truyền thống cần xương ống và thảo quả."
- Tại sao khác: Hai câu thuộc hai chủ đề hoàn toàn khác nhau (thư viện vs nấu ăn), không có điểm chung về ngữ nghĩa.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine similarity chỉ đo góc giữa hai vector, không bị ảnh hưởng bởi độ dài (magnitude) của vector. Trong text embeddings, các vector có thể có magnitude khác nhau tùy thuộc vào độ dài văn bản hoặc mô hình embedding, nhưng hướng (direction) mới là thứ mang thông tin ngữ nghĩa — vì vậy cosine phù hợp hơn Euclidean distance vốn nhạy cảm với cả magnitude.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Công thức: `ceil((doc_length - overlap) / (chunk_size - overlap))`
> `= ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23 chunks`
>
> Kiểm chứng bằng code: `len(FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000))` → **23**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Với overlap=100: `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks`. Số chunk tăng từ 23 lên 25 vì bước nhảy (step) giảm. Overlap lớn hơn giúp giảm nguy cơ cắt đứt ý nghĩa tại ranh giới chunk — thông tin ở biên được lặp lại ở chunk kế tiếp, giúp retrieval chính xác hơn khi câu hỏi rơi đúng vào vùng giao nhau.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng regex `r'(?<=[.!?])[\s]+'` để tách câu tại các dấu chấm câu (`.`, `!`, `?`) theo sau bởi khoảng trắng. Sau đó nhóm các câu theo `max_sentences_per_chunk` bằng vòng lặp với bước nhảy bằng giá trị này, join bằng khoảng trắng. Edge case xử lý: text rỗng trả về `[]`, text không chứa dấu câu trả về nguyên text đã strip.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Hàm `chunk()` gọi `_split(text, self.separators)` và lọc bỏ chunk rỗng. Hàm `_split()` hoạt động đệ quy: base case là khi `len(text) <= chunk_size` thì trả về `[text]`. Nếu chưa đủ nhỏ, thử separator đầu tiên để split, gộp lại (merge) các phần nhỏ liền kề nếu tổng ≤ chunk_size, rồi đệ quy trên các phần quá lớn với danh sách separators còn lại. Separator `""` là fallback cuối cùng — cắt cứng theo chunk_size.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Mỗi document được chuyển thành record dict `{id, doc_id, content, embedding, metadata}` qua `_make_record()`, trong đó embedding được tính bằng `self._embedding_fn(doc.content)`. Record được append vào `self._store` (in-memory list). Khi search, embed query rồi tính dot product với mỗi record, sort descending theo score và trả về top_k kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc **trước** khi search: duyệt `self._store`, giữ lại các record mà tất cả key-value trong `metadata_filter` đều khớp, rồi gọi `_search_records` trên tập đã lọc. `delete_document` dùng list comprehension để tạo store mới không chứa record có `metadata['doc_id'] == doc_id`, so sánh kích thước trước/sau để return True/False.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Gọi `self.store.search(question, top_k)` để lấy top-k chunks liên quan nhất. Xây dựng prompt theo cấu trúc: "Based on the following context, answer the question." + context (đánh số [1], [2], [3]) + question. Cuối cùng gọi `self.llm_fn(prompt)` và trả về kết quả trực tiếp.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.1.1, pluggy-1.6.0 -- C:\VinAI\K4-DAY07-TrinhHoangTung-2A202602937\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\VinAI\K4-DAY07-TrinhHoangTung-2A202602937
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================== 42 passed in 0.10s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên mượn sách tại thư viện | Bạn đọc mượn tài liệu ở phòng đọc | cao | 0.1394 | Không hẳn (dương nhưng thấp) |
| 2 | Thư viện mở cửa lúc 8 giờ sáng | Giá vàng hôm nay tăng 2% | thấp | -0.2504 | Đúng (điểm âm, khác biệt) |
| 3 | Quy trình gia hạn sách tham khảo | Hướng dẫn gia hạn tài liệu mượn | cao | 0.1280 | Không hẳn (dương nhưng thấp) |
| 4 | Python là ngôn ngữ lập trình bậc cao | Machine learning sử dụng thuật toán học từ dữ liệu | thấp | 0.1515 | Sai (điểm cao hơn cặp 1 & 3) |
| 5 | Phòng học nhóm cần đăng ký trước | Đặt phòng họp nhóm qua form online | cao | -0.1464 | Sai (bất ngờ: điểm âm) |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> **Kết quả bất ngờ nhất:** Cặp 5 (*"Phòng học nhóm cần đăng ký trước"* và *"Đặt phòng họp nhóm qua form online"*) mang ngữ nghĩa rất tương đồng trong bối cảnh dịch vụ thư viện, nhưng điểm cosine similarity thực tế lại là số âm (-0.1464). Ngược lại, Cặp 4 (*"Python..."* và *"Machine learning..."*) đề cập hai khái niệm khác nhau lại có điểm tương tự dương cao nhất trong 5 cặp (0.1515).
>
> **Bản chất của hiện tượng này và cách embeddings biểu diễn ý nghĩa:**
> 1. `MockEmbedder` sử dụng hàm băm MD5 kết hợp với thuật toán sinh số giả ngẫu nhiên LCG (*Linear Congruential Generator*) để tạo vector 64 chiều. Do tính chất tán xạ (*avalanche effect*) của hàm băm cryptographic, hai câu dù đồng nghĩa hoàn toàn nhưng chuỗi ký tự khác nhau sẽ sinh ra hash hoàn toàn độc lập, khiến vector kết quả phân bố ngẫu nhiên trong không gian.
> 2. Điều này chứng minh rằng `MockEmbedder` **không có khả năng biểu diễn ngữ nghĩa (semantic representation)**; các giá trị tương tự đo được chỉ là sự trùng hợp hình học ngẫu nhiên.
> 3. Để embeddings thực sự phản ánh ngữ nghĩa (các câu đồng nghĩa có độ tương tự cao > 0.7, câu khác chủ đề có độ tương tự thấp), cần sử dụng các mô hình Transformer-based embeddings (như `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, OpenAI `text-embedding-3-small`, hoặc Google Gemini Embeddings). Các mô hình này học được mối liên hệ ngữ nghĩa đa chiều qua hàng tỷ mẫu văn bản trong quá trình huấn luyện.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Với giáo trình tại phòng 111, được mượn tối đa bao nhiêu cuốn, trong bao lâu và được gia hạn thế nào? | Tối đa 8 cuốn trong 90 ngày, được gia hạn một lần thêm 30 ngày, tổng tối đa 120 ngày. Câu này chạy với metadata_filter={"audience": "student"}. | student-textbook-borrowing, mục Chính sách mượn |
| 2 | Chính sách mượn sách tham khảo tại phòng 102 quy định số lượng, thời hạn và gia hạn như thế nào? | Tối đa 5 cuốn, mượn từ 1 đến 30 ngày và được gia hạn một lần thêm 7 ngày. | student-reference-book-borrowing, mục Chính sách mượn |
| 3 | Phòng học nhóm phục vụ vào thời gian nào và quy trình nhận trả chìa khóa ra sao? | Thứ Hai–thứ Sáu 08:00–21:00, cuối tuần 08:00–16:00; đăng ký, để lại thẻ tại P411 để nhận chìa khóa rồi trả chìa khóa để nhận lại thẻ. | group-study-room, mục Thời gian sử dụng và Quy trình đăng ký |
| 4 | Khi quên mật khẩu tài khoản thư viện, bạn đọc cần thực hiện các bước nào? | Truy cập libopac, chọn Đăng nhập, chọn Quên mật khẩu/Quên mã PIN, nhập mã số thẻ, mở liên kết trong email rồi đặt mật khẩu mới. | library-account, mục Đặt lại mật khẩu |
| 5 | Bạn đọc ngoài HUST có thể đọc toàn văn tài nguyên số không và cần điều kiện gì? | Có, nếu đăng ký thẻ hoặc tài khoản thư viện; họ có thể đọc toàn văn tài liệu số và tải học liệu mở. | digital-resource-faq, mục Quyền truy cập của bạn đọc ngoài HUST |

### Bảng top-3 và cosine score chi tiết

Benchmark dùng Heading-based Chunking với `chunk_size=1000`, local embedding `paraphrase-multilingual-MiniLM-L12-v2` và `top_k=3`.

| Câu | Rank | Chunk (`doc_id#chunk_index`) | Cosine score | Đánh giá | Điểm câu |
|---|---:|---|---:|---|---:|
| Q1 | 1 | `student-reference-book-borrowing#1` | 0.6625 | Nhiễu: chính sách sách tham khảo phòng 102 | 1/2 |
| Q1 | 2 | `student-textbook-borrowing#0` | 0.6408 | **Gold chunk, chứa đáp án** |  |
| Q1 | 3 | `student-textbook-borrowing#1` | 0.6270 | Đúng tài liệu, khác phần |  |
| Q2 | 1 | `student-reference-book-borrowing#1` | 0.5996 | **Gold chunk, chứa đáp án** | 2/2 |
| Q2 | 2 | `document-renewal#1` | 0.5150 | Liên quan chung đến gia hạn |  |
| Q2 | 3 | `student-textbook-borrowing#1` | 0.5055 | Chính sách giáo trình, không phải sách tham khảo |  |
| Q3 | 1 | `group-study-room#1` | 0.6327 | **Gold chunk, chứa thời gian và quy trình chìa khóa** | 2/2 |
| Q3 | 2 | `group-study-room#2` | 0.5279 | Đúng tài liệu, phần thông tin hỗ trợ |  |
| Q3 | 3 | `group-study-room#0` | 0.5268 | Đúng tài liệu, phần mở đầu |  |
| Q4 | 1 | `library-account#1` | 0.6840 | **Gold chunk, chứa các bước đặt lại mật khẩu** | 2/2 |
| Q4 | 2 | `library-account#2` | 0.6506 | Đúng tài liệu, phần đổi mật khẩu/khắc phục lỗi |  |
| Q4 | 3 | `student-textbook-borrowing#2` | 0.5617 | Nhiễu |  |
| Q5 | 1 | `digital-resource-faq#2` | 0.7342 | **Gold chunk, chứa điều kiện đăng ký thẻ/tài khoản** | 2/2 |
| Q5 | 2 | `information-on-demand#1` | 0.5089 | Nhiễu: dịch vụ cung cấp thông tin |  |
| Q5 | 3 | `digital-resource-faq#0` | 0.4954 | Đúng tài liệu, khác phần |  |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5 / 5**

**Tổng điểm truy xuất:** **9 / 10** (Q1: 1/2; Q2–Q5: 2/2 mỗi câu).

**Kiểm soát section dài:** Corpus tạo ra 30 chunks; độ dài nhỏ nhất 63, trung bình 825.93 và lớn nhất 996 ký tự. Không có chunk nào vượt `chunk_size=1000` (`over_limit=0`). Khi một section Markdown dài hơn ngưỡng, `HeadingBasedChunker` gọi `RecursiveChunker` để tách nhỏ rồi gắn lại heading vào từng mảnh con; kết quả kiểm tra cho thấy 30/30 chunks vẫn giữ heading.

**Phân tích lỗi:** Q1 chỉ đạt 1/2 vì chunk sách tham khảo phòng 102 có từ vựng “số lượng, thời hạn, gia hạn” tương tự và đứng top-1; chunk giáo trình phòng 111 chứa đáp án đứng top-2. Cách cải thiện là thêm reranking theo thực thể `phòng 111` hoặc dùng metadata `category` chi tiết hơn để phân biệt hai chính sách mượn.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
Qua phần demo và so sánh kết quả, tôi nhận ra truy xuất đúng tài liệu chưa chắc đã đủ để agent trả lời chính xác; cần kiểm tra chunk được trả về có thực sự chứa đáp án hay không. Tôi cũng học được rằng Heading-based Chunking giữ ngữ cảnh chủ đề tốt, nhưng vẫn cần điều chỉnh chunk_size và có thể bổ sung reranking để đưa chunk chứa đáp án lên vị trí cao hơn.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 9/10 |
| **Tổng phần cá nhân** | **59 / 60** |
