# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** phoboi
**Thành viên:** Trịnh Đức Huy — 2A202602865; Trịnh Hoàng Tùng — 2A202602937; Nguyễn Hoàng Sơn — 2A202602457; Đỗ Quốc An — 2A202602892
**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Dịch vụ và quy định Thư viện Đại học Bách khoa Hà Nội

**Tại sao nhóm chọn chủ đề này?**
> Nhóm chọn chủ đề thư viện vì các quy định mượn–trả, gia hạn, tài khoản, phòng học và tài nguyên số có câu trả lời cụ thể, dễ kiểm chứng từ nguồn chính thức. Corpus cũng có nhiều loại câu hỏi khác nhau như tra cứu con số, điều kiện, thời gian và quy trình, phù hợp để đánh giá ảnh hưởng của chunking và metadata filter.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Câu hỏi thường gặp về tài nguyên số | https://library.hust.edu.vn/vi/node/528 | 19/09/2026 / not-stated | 1.367 | `audience=all`, `category=digital-resources`, `language=vi` |
| 2 | Hướng dẫn gia hạn tài liệu | https://library.hust.edu.vn/vi/node/183 | 19/09/2026 / not-stated | 622 | `audience=all`, `category=renewal`, `language=vi` |
| 3 | Dịch vụ sử dụng phòng học nhóm | https://library.hust.edu.vn/vi/node/1363 | 19/09/2026 / not-stated | 896 | `audience=all`, `category=study-room`, `language=vi` |
| 4 | Dịch vụ cung cấp thông tin theo yêu cầu | https://library.hust.edu.vn/vi/node/41 | 19/09/2026 / not-stated | 1.184 | `audience=all`, `category=research-support`, `language=vi` |
| 5 | Hướng dẫn quản lý tài khoản bạn đọc | https://library.hust.edu.vn/vi/node/49 | 19/09/2026 / not-stated | 1.090 | `audience=all`, `category=library-account`, `language=vi` |
| 6 | Giờ phục vụ thư viện | https://library.hust.edu.vn/vi/node/416 | 19/09/2026 / not-stated | 650 | `audience=all`, `category=hours`, `language=vi` |
| 7 | Hướng dẫn mượn sách tham khảo phòng 102 | https://library.hust.edu.vn/vi/node/502 | 19/09/2026 / not-stated | 826 | `audience=student`, `category=borrowing`, `language=vi` |
| 8 | Quy trình mượn trả giáo trình phòng 111 | https://library.hust.edu.vn/vi/node/483 | 19/09/2026 / not-stated | 1.568 | `audience=student`, `category=borrowing`, `language=vi` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `student-textbook-borrowing` | Liên kết mọi chunk với tài liệu gốc và hỗ trợ xóa theo tài liệu. |
| `title` | string | `Quy trình mượn trả giáo trình phòng 111` | Hiển thị nguồn dễ hiểu và hỗ trợ truy vết. |
| `source_url` | string | `https://library.hust.edu.vn/vi/node/483` | Kiểm chứng câu trả lời tại nguồn chính thức. |
| `retrieved_at` | date string | `2026-09-19` | Cho biết thời điểm dữ liệu được thu thập. |
| `document_version` | string | `not-stated` | Theo dõi phiên bản; ghi minh bạch khi nguồn không nêu. |
| `audience` | enum | `student`, `all` | Lọc chính sách theo đúng đối tượng người dùng. |
| `department` | string | `library` | Giới hạn truy xuất theo đơn vị phụ trách. |
| `category` | string | `borrowing`, `study-room` | Thu hẹp kết quả theo loại dịch vụ/quy định. |
| `language` | string | `vi` | Chọn tài liệu theo ngôn ngữ truy vấn. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Mượn giáo trình P.111 | FixedSizeChunker (`fixed_size`) | 4 | 429,5 | Có thể cắt ngang mục/quy trình. |
| Mượn giáo trình P.111 | SentenceChunker (`by_sentences`) | 11 | 141,0 | Giữ câu tốt nhưng tạo nhiều chunk nhỏ. |
| Mượn giáo trình P.111 | RecursiveChunker (`recursive`) | 5 | 312,0 | Khá tốt; ưu tiên ranh giới heading và đoạn. |
| FAQ tài nguyên số | FixedSizeChunker (`fixed_size`) | 3 | 489,0 | Có nguy cơ tách câu hỏi khỏi câu trả lời. |
| FAQ tài nguyên số | SentenceChunker (`by_sentences`) | 5 | 271,4 | Giữ câu nhưng không bảo đảm giữ cặp hỏi–đáp. |
| FAQ tài nguyên số | RecursiveChunker (`recursive`) | 4 | 340,2 | Giữ các đoạn và danh sách tương đối trọn vẹn. |
| Tài khoản thư viện | FixedSizeChunker (`fixed_size`) | 3 | 396,7 | Có thể cắt ngang chuỗi bước. |
| Tài khoản thư viện | SentenceChunker (`by_sentences`) | 8 | 135,0 | Nhiều chunk nhỏ, dễ mất ngữ cảnh bước trước. |
| Tài khoản thư viện | RecursiveChunker (`recursive`) | 3 | 362,0 | Giữ các nhóm bước tốt hơn trong baseline. |

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Đỗ Quốc An**
- **Loại chiến lược:** Fixed-size Chunking, `FixedSizeChunker(chunk_size=500, overlap=50)`.
- **Mô tả & lý do chọn:** Kích thước cố định giúp dự đoán số chunk và tạo một baseline đơn giản. Overlap 50 ký tự giữ lại một phần ngữ cảnh ở ranh giới, nhưng chiến lược vẫn có thể cắt giữa câu hoặc giữa các bước hướng dẫn.
- **Code snippet (nếu custom):** Không custom; dùng `FixedSizeChunker` trong `src/chunking.py`.

**Thành viên 2 — Nguyễn Hoàng Sơn**
- **Loại chiến lược:** Recursive Chunking, `RecursiveChunker(chunk_size=500)`.
- **Mô tả & lý do chọn:** Tài liệu thư viện có heading, đoạn văn, danh sách và các bước thao tác với độ dài khác nhau. Recursive chunking ưu tiên ranh giới lớn trước rồi mới hạ xuống câu/từ, nhờ đó giảm khả năng cắt ngang quy trình trong khi vẫn kiểm soát kích thước chunk.
- **Code snippet (nếu custom):** Không custom; cấu hình sử dụng:
```python
chunker = RecursiveChunker(chunk_size=500)
```

**Thành viên 3 — Trịnh Hoàng Tùng**
- **Loại chiến lược:** Heading-based Chunking (custom).
- **Mô tả & lý do chọn:** Tách tại heading cấp `##` và giữ heading cấp `###` trong mục cha. Cách này phù hợp Markdown có cấu trúc và giữ trọn các mục như “Chính sách mượn” hoặc “Đặt lại mật khẩu”, nhưng section dài có thể tạo chunk lớn.
- **Code snippet (nếu custom):**
```python
def heading_chunks(text: str) -> list[str]:
    sections = [
        part.strip()
        for part in re.split(r"(?m)(?=^## )", text)
        if part.strip()
    ]
    if len(sections) > 1 and not sections[0].startswith("## "):
        sections[1] = sections[0] + "\n\n" + sections[1]
        sections = sections[1:]
    return sections
```

**Thành viên 4 — Trịnh Đức Huy**
- **Loại chiến lược:** Semantic Chunking (custom), `chunk_size=500`, `semantic_threshold=0.5`.
- **Mô tả & lý do chọn:** Nhúng từng câu/dòng bằng mô hình local đa ngữ và tạo ranh giới khi cosine similarity giữa hai đơn vị liên tiếp nhỏ hơn 0,5 hoặc khi ứng viên vượt 500 ký tự. Chiến lược hướng tới ranh giới theo chủ đề, nhưng ngưỡng hiện tại sinh 156 chunk rất ngắn và thường đưa chunk chỉ có tiêu đề lên top đầu.
- **Code snippet (nếu custom):**
```python
boundary = (
    previous is not None
    and compute_similarity(previous, vector) < threshold
)
if current and (boundary or len(candidate) > chunk_size):
    chunks.append(current)
    current = ""
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Đỗ Quốc An | Fixed-size, 500/50 | 8/10 | Đơn giản, ổn định và có overlap bảo vệ ranh giới. | Báo cáo chỉ ghi 3/5 câu có tài liệu gold trong top-3; top-1 của nhiều câu chưa chứa đáp án. |
| Nguyễn Hoàng Sơn | Recursive, 500 | 10/10 | Cả 5 tài liệu gold ở top-1; top-3 chứa đủ dữ kiện của 5/5 câu. | Câu hỏi có đáp án trải qua hai mục vẫn cần ghép nhiều chunk trong top-k. |
| Trịnh Hoàng Tùng | Heading-based | 9/10 | Báo cáo ghi 5/5 câu có chunk liên quan trong top-3; giữ tốt section Markdown. | Thiếu bảng top-3 và score chi tiết theo từng câu; section dài có thể tạo chunk quá lớn. |
| Trịnh Đức Huy | Semantic, 500, ngưỡng 0,5 | 4/10 | Câu 1 và 5 đủ dữ kiện khi ghép top-3; phát hiện đúng chủ đề tài liệu. | Sinh 156 chunk quá nhỏ; câu 2–3 thất bại, câu 4 chỉ đủ một phần. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Theo bằng chứng chi tiết hiện có, `RecursiveChunker(chunk_size=500)` là chiến lược tốt nhất: đạt 10/10, đưa tài liệu gold lên top-1 ở cả năm câu và giữ kích thước chunk không quá 500 ký tự trên corpus của Sơn. Heading-based là hướng bổ sung tốt cho các quy trình khép kín như đặt lại mật khẩu; phương án cải thiện hợp lý là tách theo heading trước, sau đó dùng Recursive cho section vượt giới hạn.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Với giáo trình tại phòng 111, được mượn tối đa bao nhiêu cuốn, trong bao lâu và được gia hạn thế nào? | Tối đa 8 cuốn trong 90 ngày, được gia hạn một lần thêm 30 ngày, tổng tối đa 120 ngày. Câu này chạy với `metadata_filter={"audience": "student"}`. | `student-textbook-borrowing`, mục **Chính sách mượn** |
| 2 | Chính sách mượn sách tham khảo tại phòng 102 quy định số lượng, thời hạn và gia hạn như thế nào? | Tối đa 5 cuốn, mượn từ 1 đến 30 ngày và được gia hạn một lần thêm 7 ngày. | `student-reference-book-borrowing`, mục **Chính sách mượn** |
| 3 | Phòng học nhóm phục vụ vào thời gian nào và quy trình nhận trả chìa khóa ra sao? | Thứ Hai–thứ Sáu 08:00–21:00, cuối tuần 08:00–16:00; đăng ký, để lại thẻ tại P411 để nhận chìa khóa rồi trả chìa khóa để nhận lại thẻ. | `group-study-room`, mục **Thời gian sử dụng** và **Quy trình đăng ký** |
| 4 | Khi quên mật khẩu tài khoản thư viện, bạn đọc cần thực hiện các bước nào? | Truy cập libopac, chọn Đăng nhập, chọn Quên mật khẩu/Quên mã PIN, nhập mã số thẻ, mở liên kết trong email rồi đặt mật khẩu mới. | `library-account`, mục **Đặt lại mật khẩu** |
| 5 | Bạn đọc ngoài HUST có thể đọc toàn văn tài nguyên số không và cần điều kiện gì? | Có, nếu đăng ký thẻ hoặc tài khoản thư viện; họ có thể đọc toàn văn tài liệu số và tải học liệu mở. | `digital-resource-faq`, mục **Quyền truy cập của bạn đọc ngoài HUST** |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Mượn giáo trình P.111 | Recursive 500 | Có — top-1 | Recursive: score 0,7012 và đủ ba nhóm dữ kiện. Semantic cũng đủ khi ghép top-2 và top-3; Fixed-size chỉ báo liên quan một phần. |
| 2 | Mượn sách tham khảo P.102 | Recursive 500 | Có — top-1 | Recursive: score 0,6653, đủ 5 cuốn, 1–30 ngày và gia hạn 7 ngày. Semantic và kết quả Fixed-size trong báo cáo cá nhân không lấy đủ dữ kiện. |
| 3 | Phòng học nhóm | Recursive 500 | Có — top-1 và top-3 | Recursive: chunk 0 đứng top-1, chunk 1 của cùng tài liệu ở top-3; ghép lại đủ thời gian và quy trình chìa khóa. Semantic và Fixed-size cá nhân thất bại. |
| 4 | Quên mật khẩu | Recursive / Heading-based | Có — top-1 | Recursive đạt score 0,6201 và hai chunk tài khoản đứng top-2. Heading-based phù hợp vì giữ trọn section; Semantic và Fixed-size chỉ lấy được một phần. |
| 5 | Quyền truy cập tài nguyên số | Recursive 500 | Có — top-1 | Recursive: score 0,7217, cao nhất trong năm truy vấn. Semantic cũng đủ điều kiện và quyền lợi khi ghép top-1 với top-2. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Câu 1 dùng `metadata_filter={"audience": "student"}`, thu hẹp phạm vi từ tám xuống hai tài liệu. Trong lần chạy Recursive, A/B có và không có filter đều giữ tài liệu đúng ở top-1 với score 0,7012 vì ba kết quả đầu vốn đã thuộc nhóm sinh viên. Filter vẫn hữu ích để kiểm soát đối tượng, nhưng không thể tự phân biệt giáo trình P.111 với sách tham khảo P.102 vì cả hai cùng có `audience=student`; các từ “giáo trình” và “phòng 111” trong query vẫn quyết định kết quả.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> - Đúng `doc_id` chưa đồng nghĩa có đủ ngữ cảnh: Semantic thường đưa đúng tài liệu hoặc tiêu đề lên đầu nhưng các con số và bước thực hiện nằm ngoài top-3.
> - Ranh giới chunk quyết định khả năng trả lời: Heading-based giữ section, Recursive cân bằng cấu trúc và giới hạn độ dài, còn Fixed-size cần overlap để giảm mất thông tin tại điểm cắt.
> - Metadata filter giúp giảm không gian tìm kiếm, nhưng không thay thế truy xuất ngữ nghĩa khi nhiều tài liệu có cùng `audience=student`.

**Bài học rút ra khi so sánh trong nhóm:**
> Recursive cho kết quả ổn định nhất trong lần chạy có bằng chứng chi tiết vì giữ được đoạn và danh sách mà không tạo quá nhiều chunk. Semantic với ngưỡng 0,5 tạo 156 mảnh, khiến tiêu đề có score cao nhưng tách rời tiêu đề khỏi dữ kiện. Heading-based phù hợp tài liệu Markdown có cấu trúc rõ, còn Fixed-size là baseline dễ hiểu nhưng có thể cắt ngang câu hoặc quy trình.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ cố định một snapshot corpus và một script benchmark dùng chung trước khi so sánh để tránh sai lệch giữa workspace cá nhân. Về chunking, nhóm sẽ thử pipeline hai tầng: tách theo heading trước rồi dùng Recursive cho section dài; với Semantic, sẽ gom các dòng trong cùng đoạn trước khi tính cosine và chọn threshold trên một tập phát triển riêng. Nhóm cũng sẽ lưu top-3 và câu trả lời agent dưới dạng JSON để mọi điểm số đều có thể kiểm chứng.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 9 / 10 |
| Thiết kế chiến lược (Strategy Design) | 14 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 9 / 10 |
| Thuyết trình (Demo) | 4 / 5 |
| **Tổng phần nhóm** | **36 / 40** |