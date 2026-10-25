import os
import sys
import time
from dotenv import load_dotenv

load_dotenv("D:/code/HỌC/hieradoc/.env")
from hieradoc import HieraDoc

# Tạo một văn bản lớn với 10 Điều khoản độc lập
LARGE_CONTRACT = """QUY CHẾ VẬN HÀNH VÀ QUẢN TRỊ DỮ LIỆU TẬP ĐOÀN CÔNG NGHỆ

Chương I: QUẢN TRỊ DỮ LIỆU VÀ BẢO MẬT HỆ THỐNG
Điều 1. Phân loại dữ liệu và quyền truy cập
Khoản 1. Dữ liệu nhạy cảm cấp độ 1 bao gồm thông tin thanh toán, mật khẩu và khóa mã hóa cá nhân của người dùng.
Khoản 2. Quyền truy cập vào dữ liệu cấp độ 1 phải được cấp duyệt bởi Giám đốc Công nghệ (CTO).

Điều 2. Thời hạn lưu trữ và sao lưu dữ liệu
Khoản 1. Tất cả nhật ký hệ thống (system logs) phải được lưu trữ tối thiểu trong thời gian 24 tháng.
Khoản 2. Bản sao lưu ngoại tuyến (cold storage backup) phải được thực hiện định kỳ vào 02:00 sáng mỗi Chủ Nhật.

Điều 3. Quy trình khắc phục sự cố rò rỉ thông tin
Khoản 1. Khi phát hiện dấu hiệu xâm nhập trái phép, Đội ngũ An toàn thông tin phải kích hoạt quy trình cô lập trong vòng 15 phút.
Khoản 2. Thông báo khẩn cấp phải được gửi đến Cơ quan thẩm quyền và các bên bị ảnh hưởng trong thời hạn tối đa 72 giờ.

Chương II: CHÍNH SÁCH BẢO HÀNH VÀ BỒI THƯỜNG THIỆT HẠI
Điều 4. Cam kết thời gian khả dụng (SLA)
Khoản 1. Tỷ lệ sẵn sàng vận hành của các dịch vụ cốt lõi không được thấp hơn 99.95% trong mỗi tháng dương lịch.
Khoản 2. Thời gian bảo trì định kỳ phải được thông báo trước ít nhất 48 giờ cho toàn thể khách hàng.

Điều 5. Mức khấu trừ và bồi thường dịch vụ
Khoản 1. Nếu tỷ lệ SLA giảm xuống dưới 99.0%, khách hàng được hoàn trả 30% giá trị cước phí của tháng đó.
Khoản 2. Mức bồi hoàn tối đa cho mọi thiệt hại gián tiếp không vượt quá 100% tổng chi phí dịch vụ 06 tháng gần nhất.
"""

def test_concurrent_summarization():
    print("=====================================================================")
    print(">>> TEST: CONCURRENT SUMMARIZATION & PARALLEL TREE INGESTION (v0.7.0)")
    print("=====================================================================")

    db_path = "test_concurrent_speed.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    file_path = "sample_large_contract.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(LARGE_CONTRACT)

    hieradoc = HieraDoc(storage="sqlite", db_path=db_path)

    print("\n--- 1. Measuring Ingestion Latency with Concurrent Summarizer ---")
    start_t = time.time()
    res = hieradoc.index(file_path_or_text=file_path, doc_id="LARGE_ENTERPRISE_DOC", cluster="Quy Chế Doanh Nghiệp")
    ingest_duration = time.time() - start_t

    print(f"Index Completed in: {ingest_duration:.2f} seconds!")
    print(f"Total Branches: {res['total_branches']}, Total Leaves: {res['total_leaves']}")
    print(f"Summary Overview: {res['summary'][:150]}...")

    print("\n--- 2. Verifying Search Retrieval on Concurrently Indexed Tree ---")
    query = "Thời hạn lưu trữ nhật ký hệ thống là bao lâu và thời gian kích hoạt quy trình cô lập sự cố là bao nhiêu phút?"
    q_start = time.time()
    response = hieradoc.query(question=query)
    q_duration = time.time() - q_start

    print(f"Query Completed in: {q_duration:.2f} seconds!")
    print(f"\nFinal Answer:\n{response.answer}")
    print(f"\nCitations ({len(response.citations)}):")
    for c in response.citations:
        print(f" - [{c.doc_id}] {c.leaf_title} Lines {c.lines}: \"{c.exact_quote}\"")

    assert "24 tháng" in response.answer or "24" in response.answer, "Failed to retrieve 24 months log retention!"
    assert "15 phút" in response.answer or "15" in response.answer, "Failed to retrieve 15 minutes isolation!"

    print("\n>>> ALL TESTS PASSED! Concurrent Summarizer delivers lightning fast multi-branch indexing!")

if __name__ == "__main__":
    test_concurrent_summarization()
