import json
import os
from datetime import datetime, timezone

from intent_router_agent import graph

TEST_QUESTIONS = [
    # 5 câu kiến thức thuần
    {
        "question": "Thủ đô của Nhật Bản là gì?",
        "expected_intent": "knowledge",
        "category": "knowledge",
    },
    {
        "question": "Ai là người sáng lập ra Microsoft?",
        "expected_intent": "knowledge",
        "category": "knowledge",
    },
    {
        "question": "Ngôn ngữ lập trình Python được phát hành lần đầu năm nào?",
        "expected_intent": "knowledge",
        "category": "knowledge",
    },
    {
        "question": "Sông dài nhất thế giới là sông nào?",
        "expected_intent": "knowledge",
        "category": "knowledge",
    },
    {
        "question": "Giải thích ngắn gọn thuyết tương đối hẹp của Einstein là gì?",
        "expected_intent": "knowledge",
        "category": "knowledge",
    },
    # 5 câu tính toán trực tiếp
    {
        "question": (
            "Một cửa hàng sách buổi sáng bán được 125 cuốn, buổi chiều bán "
            "được nhiều hơn buổi sáng 250 cuốn. Hỏi cả ngày cửa hàng bán "
            "được bao nhiêu cuốn sách?"
        ),
        "expected_intent": "calculation",
        "category": "calculation",
    },
    {
        "question": (
            "Một xưởng may nhập về 900 mét vải, đã dùng hết 356 mét để may "
            "cho đơn hàng thứ nhất. Số vải còn lại được chia đều để may cho "
            "4 đơn hàng tiếp theo. Hỏi mỗi đơn hàng tiếp theo được cấp bao "
            "nhiêu mét vải?"
        ),
        "expected_intent": "calculation",
        "category": "calculation",
    },
    {
        "question": (
            "Một rạp chiếu phim có 17 hàng ghế, mỗi hàng xếp được 23 ghế. "
            "Hỏi rạp có tổng cộng bao nhiêu ghế?"
        ),
        "expected_intent": "calculation",
        "category": "calculation",
    },
    {
        "question": (
            "Một nhà máy sản xuất được 48 sản phẩm mỗi giờ và hoạt động "
            "liên tục 7 giờ mỗi ngày trong 3 ngày liên tiếp. Hỏi sau 3 "
            "ngày đó nhà máy sản xuất được bao nhiêu sản phẩm?"
        ),
        "expected_intent": "calculation",
        "category": "calculation",
    },
    {
        "question": (
            "Một bể chứa có 200 lít nước, sau đó người ta rút bớt 50 lít "
            "để tưới cây. Lượng nước còn lại được chia đều vào 3 bình "
            "chứa nhỏ. Nếu rót thêm nước sao cho lượng nước trong mỗi "
            "bình tăng lên gấp 6 lần so với lúc vừa chia xong, hỏi mỗi "
            "bình chứa bao nhiêu lít nước sau khi rót thêm?"
        ),
        "expected_intent": "calculation",
        "category": "calculation",
    },
    # 5 câu ngoài phạm vi (out_of_scope)
    {
        "question": "Chào bạn, dạo này bạn thế nào?",
        "expected_intent": "out_of_scope",
        "category": "out_of_scope",
    },
    {
        "question": "Viết giúp mình một đoạn code Python tính dãy Fibonacci.",
        "expected_intent": "out_of_scope",
        "category": "out_of_scope",
    },
    {
        "question": "Thủ đô của Nhật Bản là gì và 125 nhân 7 bằng bao nhiêu?",
        "expected_intent": "out_of_scope",
        "category": "out_of_scope",
    },
    {
        "question": "Bạn dịch giúp mình câu này sang tiếng Anh: Hôm nay trời đẹp.",
        "expected_intent": "out_of_scope",
        "category": "out_of_scope",
    },
    {
        "question": "Cho mình lời khuyên nên đầu tư vào cổ phiếu nào bây giờ?",
        "expected_intent": "out_of_scope",
        "category": "out_of_scope",
    },
    # 5 câu nhập nhằng: kể chuyện dài, nhồi nhiều số liệu nhiễu,
    # nhưng chỉ chứa đúng 1 yêu cầu thật cần trả lời
    {
        "question": (
            "Máy bay Boeing 747-400 có chiều dài thân 70,7 mét, sải cánh "
            "64,4 mét, cao 19,4 mét, trọng lượng cất cánh tối đa gần 397 tấn, "
            "sức chứa khoảng 416 hành khách ở cấu hình ba hạng, được trang bị "
            "bốn động cơ và từng là biểu tượng của hàng không dân dụng suốt "
            "nhiều thập kỷ. Công trình này trải qua hàng nghìn giờ bay thử "
            "nghiệm trước khi đi vào khai thác thương mại. Khi hoàn thiện "
            "phần chú thích kỹ thuật cho một triển lãm lịch sử hàng không, "
            "vẫn còn thiếu thông tin về diện tích mặt sàn dành cho hành khách."
        ),
        "expected_intent": "calculation",
        "category": "ambiguous",
    },
    {
        "question": (
            "Tàu Titanic được đóng với chiều dài 269 mét, bề ngang 28 mét, "
            "cao 53 mét tính từ đáy tàu lên đỉnh ống khói, trọng tải đăng ký "
            "khoảng 46.000 tấn, có thể chở hơn 2.200 người, trang bị 16 phân "
            "khoang kín nước và bốn ống khói. Con tàu khởi hành chuyến đi "
            "đầu tiên vào mùa xuân năm 1912 và trở thành biểu tượng của "
            "thảm họa hàng hải. Trong phần ghi chú của một cuốn sách về "
            "lịch sử đóng tàu, dòng giới thiệu về người thiết kế chính của "
            "con tàu vẫn còn để trống."
        ),
        "expected_intent": "knowledge",
        "category": "ambiguous",
    },
    {
        "question": (
            "Cá voi xanh trưởng thành thường dài từ 25 đến 30 mét, nặng "
            "trung bình 150–200 tấn, có trái tim nặng gần 180 kg và lưỡi "
            "nặng tương đương một con voi châu Phi. Chúng có thể duy trì "
            "tốc độ tuần tra khoảng 20 km mỗi giờ khi di chuyển trên đại "
            "dương. Khi lập kế hoạch quan sát trên biển cho một nhóm nghiên "
            "cứu gồm 8 người, cần ước lượng thời gian để một cá thể bơi "
            "hết quãng đường 36 km với tốc độ tuần tra thông thường."
        ),
        "expected_intent": "calculation",
        "category": "ambiguous",
    },
    {
        "question": (
            "Sứ mệnh Apollo 11 sử dụng tên lửa Saturn V cao 110,6 mét, "
            "nặng gần 3.000 tấn khi đầy nhiên liệu, đưa ba phi hành gia "
            "bay khoảng 384.000 km đến Mặt Trăng và trở về Trái Đất trong "
            "tổng cộng hơn 8 ngày. Module hạ cánh Eagle đã ở lại bề mặt "
            "Mặt Trăng khoảng 21 giờ rưỡi. Trong phần chú thích ảnh tại "
            "bảo tàng hàng không vũ trụ, dòng chữ nêu tên người đã đặt "
            "bước chân đầu tiên xuống bề mặt vệ tinh tự nhiên của Trái Đất "
            "vẫn chưa được điền."
        ),
        "expected_intent": "knowledge",
        "category": "ambiguous",
    },
    {
        "question": (
            "Sân vận động Maracanã tại Rio de Janeiro từng có sức chứa "
            "kỷ lục hơn 200.000 người vào giữa thế kỷ 20, hiện được cải "
            "tạo còn khoảng 78.800 chỗ ngồi, chu vi khán đài khoảng 900 mét, "
            "chiều cao mái che gần 30 mét, mặt sân thi đấu có chiều dài 105 "
            "mét và chiều rộng 68 mét theo tiêu chuẩn FIFA, và từng chứng "
            "kiến trận chung kết World Cup năm 1950. Công trình trải qua "
            "nhiều lần nâng cấp lớn. Khi soạn phần mô tả kỹ thuật cho tài "
            "liệu hướng dẫn tham quan, cần biết diện tích mặt sân bóng "
            "chính thức bên trong sân vận động."
        ),
        "expected_intent": "calculation",
        "category": "ambiguous",
    },
]

OUTPUT_DIR = "outputs"


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []
    correct = 0

    for i, item in enumerate(TEST_QUESTIONS, start=1):
        initial_state = {
            "question": item["question"],
            "intent": "",
            "answer": "",
            "trace": [],
        }
        try:
            result = graph.invoke(initial_state)
            error = None
        except Exception as exc:
            result = {"intent": "ERROR", "answer": "", "trace": [f"exception: {exc}"]}
            error = str(exc)

        is_correct = result["intent"] == item["expected_intent"]
        correct += is_correct

        print(f"\n[{i}] ({item['category']}) Câu hỏi: {item['question']}")
        print(
            f"    Nhãn kỳ vọng: {item['expected_intent']} | "
            f"Nhãn thực tế: {result['intent']} | {'ĐÚNG' if is_correct else 'SAI'}"
        )
        print(f"    Trả lời: {result['answer']}")
        for step in result["trace"]:
            print(f"      - {step}")

        results.append(
            {
                "index": i,
                "category": item["category"],
                "question": item["question"],
                "expected_intent": item["expected_intent"],
                "actual_intent": result["intent"],
                "routed_correctly": is_correct,
                "answer": result["answer"],
                "trace": result["trace"],
                "error": error,
            }
        )

    print(f"\nTổng kết: {correct}/{len(TEST_QUESTIONS)} câu hỏi đi đúng nhánh.")

    by_category: dict[str, list[bool]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r["routed_correctly"])
    print("Chi tiết theo nhóm:")
    for category, flags in by_category.items():
        print(f"  - {category}: {sum(flags)}/{len(flags)}")

    by_category_summary = {
        k: {"correct": sum(v), "total": len(v)} for k, v in by_category.items()
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"{timestamp}_routing_log.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total": len(TEST_QUESTIONS),
                "correct": correct,
                "by_category": by_category_summary,
                "results": results,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nĐã lưu log đầy đủ vào {output_path}")


if __name__ == "__main__":
    main()
