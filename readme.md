# RPA Code Generator

Project này nhận yêu cầu bằng ngôn ngữ tự nhiên, làm rõ yêu cầu bằng thông tin kỹ thuật, tìm các function Python có liên quan trong project và dùng các function đó làm tham khảo để sinh một function RPA mới.

## Cách hoạt động

Khi chạy `main.py`, project thực hiện các bước sau:

1. **Nhận prompt:** yêu cầu người dùng nhập mô tả chức năng cần tạo.
2. **Đọc function mẫu:** trích xuất function và method từ `test.py` để dùng làm nguồn tham khảo.
3. **Bổ sung thông tin cho prompt:** `augmented_prompt.py` dùng CrewAI và mô hình Groq `openai/openai/gpt-oss-20b` để bổ sung chi tiết kỹ thuật trong phạm vi yêu cầu. Agent có công cụ tìm kiếm DuckDuckGo và được cung cấp URL repository được cấu hình trong `main.py`.
4. **Xếp hạng function qua ba luồng** trong `essemble_streaming.py`:
   - `stream01`: so sánh embedding của prompt đã bổ sung với embedding của từng function mẫu.
   - `stream02`: sinh một đoạn code dựa trên prompt, sau đó so sánh embedding của đoạn code đó với các function mẫu.
   - `stream03`: so sánh các function mẫu với function được sinh ở luồng thứ hai.

   Embedding được tạo bằng `all-MiniLM-L6-v2` từ Sentence Transformers; độ tương đồng được tính bằng cosine similarity. Mỗi luồng thêm tối đa ba kết quả vào bảng xếp hạng, sau đó toàn bộ kết quả được sắp xếp theo độ tương đồng giảm dần.
5. **Sinh function RPA:** `rpa_code_generate.py` gửi prompt đã bổ sung, bảng xếp hạng, hướng dẫn trong `standarlize.md` và nội dung mẫu từ `rpa_code.py` cho agent. Agent được yêu cầu tạo đúng một function Python.
6. **Kiểm tra và lưu kết quả:** code trả về được phân tích cú pháp bằng `ast`. Nếu hợp lệ, function được in ra màn hình và nối thêm vào cuối `rpa_code.py`.

## Các tệp chính

| Tệp | Vai trò |
| --- | --- |
| `main.py` | Điều phối toàn bộ quy trình: nhận prompt, lấy function mẫu, chạy các luồng và sinh code RPA. |
| `augmented_prompt.py` | Bổ sung thông tin kỹ thuật cho prompt bằng CrewAI và Groq; cung cấp công cụ tìm kiếm DuckDuckGo cho agent. |
| `code_split.py` | Trích xuất function/method Python và tạo embedding, tính cosine similarity. |
| `code_gen.py` | Cấu hình LLM Groq và cung cấp hàm sinh code Python cho luồng thứ hai. |
| `essemble_streaming.py` | Thực hiện ba luồng đối chiếu function và tạo bảng xếp hạng. |
| `rpa_code_generate.py` | Tạo, kiểm tra cú pháp và ghi function RPA vào thư viện. |
| `test.py` | Chứa các function và class mẫu được dùng để xếp hạng, tham khảo. |
| `rpa_code.py` | Chứa các method mẫu có sẵn; cũng là nơi lưu các function được sinh ra. |
| `standarlize.md` | Mẫu cấu trúc mà function RPA được sinh ra cần tuân theo. |
| `requirements.txt` | Danh sách các package Python cần thiết. |

## Cài đặt và chạy

Yêu cầu Python và một API key của Groq.

1. Mở terminal tại thư mục project.
2. Tạo và kích hoạt môi trường ảo trên Windows:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Cài đặt dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Tạo tệp `.env` tại thư mục gốc của project và đặt API key:

   ```dotenv
   GROQ_API_KEY=your_groq_api_key
   ```

   Thay `your_groq_api_key` bằng API key của bạn. Không chia sẻ hoặc commit API key vào repository.

5. Chạy project từ thư mục gốc:

   ```powershell
   python main.py
   ```

   Nhập prompt khi được yêu cầu. Sau khi hoàn tất, project hiển thị prompt đã bổ sung, bảng xếp hạng và function RPA được sinh ra. Function hợp lệ sẽ được nối vào `rpa_code.py`.

## Lưu ý

- `main.py` hiện dùng `test.py` làm tệp chứa function mẫu và repository URL được khai báo trong biến `GITHUB_REPO`. Có thể cập nhật các giá trị này trong `main.py` để đổi nguồn tham khảo.
- Project cần kết nối Internet để gọi Groq và tìm kiếm bằng DuckDuckGo. Sentence Transformers cũng có thể tải model `all-MiniLM-L6-v2` trong lần sử dụng đầu tiên.
- Hãy chạy lệnh từ thư mục gốc project: đường dẫn ghi kết quả trong `rpa_code_generate.py` là `rpa_code.py` tương đối với thư mục làm việc hiện tại.
- `code_split.py` có một ví dụ chạy độc lập để xếp hạng function trong `test.py`; quy trình đầy đủ của project được khởi chạy bằng `main.py`.
