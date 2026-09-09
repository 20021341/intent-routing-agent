# Intent Routing Agent

Agent định tuyến ý định bằng [LangGraph](https://langchain-ai.github.io/langgraph/): phân loại câu hỏi vào một trong ba nhánh `knowledge` (tra cứu kiến thức qua Wikipedia), `calculation` (tính toán bằng tool cộng/trừ/nhân/chia), hoặc `out_of_scope` (từ chối lịch sự), rồi định tuyến sang đúng node xử lý.

Bài viết chi tiết: xem blog "Xây Agent định tuyến bằng LangGraph" trên AI Guru.

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Sao chép `.env.example` thành `.env` rồi điền `OPENROUTER_API_KEY` của bạn (lấy tại [openrouter.ai](https://openrouter.ai)):

```bash
cp .env.example .env
```

## Chạy thử

```bash
python3 run_20_questions.py
```

Script chạy 20 câu hỏi kiểm thử chia đều 4 nhóm (`knowledge`, `calculation`, `out_of_scope`, `ambiguous`), in log chi tiết ra terminal, và lưu kết quả đầy đủ vào `outputs/<timestamp>_routing_log.json`.

## Kết quả kiểm thử

Log đầy đủ của các lần chạy được commit trong `outputs/`, gồm câu hỏi, nhãn kỳ vọng, nhãn thực tế, câu trả lời, và từng bước `trace` cho cả 20 câu (kể cả những câu đã đi đúng nhánh mà bài không in log chi tiết để đỡ dài). File dùng làm số liệu chính thức trong bài blog là [`outputs/20260909-145838_routing_log.json`](outputs/20260909-145838_routing_log.json); file `20260909-142245_routing_log.json` là lần chạy trước, giữ lại để đối chiếu lịch sử thay đổi system prompt.

## Cấu trúc

- `intent_router_agent.py`: định nghĩa `State`, các tool, node phân loại, ba node xử lý, và `build_graph()`.
- `run_20_questions.py`: bộ 20 câu hỏi kiểm thử và script chạy.
- `outputs/`: log kết quả các lần chạy thật, dùng làm số liệu tham chiếu cho bài blog.
