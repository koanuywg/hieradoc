"""
HieraDoc Quickstart Demo
Hierarchical Tree-of-Thought RAG with Zero-Hallucination Line Citations.
"""

import sys
from dotenv import load_dotenv
from hieradoc import HieraDoc

# Ensure UTF-8 output on Windows terminal
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

def main():
    print("==================================================")
    print("   HieraDoc: Hierarchical Document Tree RAG       ")
    print("==================================================")

    # 1. Khởi tạo Engine với CSDL SQLite cục bộ (Zero-Setup)
    print("\n[1] Khởi tạo HieraDoc Engine (Local SQLite Vault)...")
    doc_engine = HieraDoc(storage="sqlite", db_path="hieradoc_vault.db")

    # 2. Nạp văn bản mẫu và tự động dựng cây phân cấp (Clusters -> Documents -> Branches -> Leaves)
    print("[2] Đang phân tích cấu trúc văn bản và lập chỉ mục số dòng [L0001]...")
    ingest_result = doc_engine.index(
        file_path_or_text="examples/sample_nda.txt",
        doc_id="nda_sample_2026",
        cluster="Pháp Lý & Hợp Đồng"
    )
    print(f" -> Đã phân cấp thành công: '{ingest_result['title']}'")
    print(f" -> Số nhánh (Branches): {ingest_result['total_branches']} | Số nút lá (Leaves): {ingest_result['total_leaves']}")
    print(f" -> Tóm tắt tổng thể: {ingest_result['summary'][:150]}...")

    # 3. Đặt câu hỏi tra cứu
    question = "Thời hạn bảo mật thông tin được các bên cam kết duy trì trong bao lâu kể từ ngày chấm dứt thỏa thuận?"
    print(f"\n[3] Đang gửi câu hỏi cho Autonomous Tree Navigator:\n -> \"{question}\"")
    
    response = doc_engine.query(question)

    # 4. In kết quả và bằng chứng số dòng
    print("\n" + "=" * 50)
    print(" CÂU TRẢ LỜI ĐƯỢC XÁC THỰC (GROUNDED ANSWER)")
    print("=" * 50)
    print(response.answer)

    print("\n" + "-" * 50)
    print(f" LỘ TRÌNH DUYỆT CÂY ({len(response.traversal_path)} bước):")
    print("-" * 50)
    for step in response.traversal_path:
        print(f"  • {step}")

    print("\n" + "-" * 50)
    print(f" BẰNG CHỨNG TRÍCH DẪN SỐ DÒNG ({len(response.citations)} trích dẫn):")
    print("-" * 50)
    for c in response.citations:
        lines_str = f"L{c.lines[0]:04d} - L{c.lines[-1]:04d}" if c.lines else "N/A"
        print(f"  [{lines_str}] {c.doc_title} > {c.branch_title}")
        print(f"  \"\"{c.exact_quote}\"\"")
        print()

    print(f"Thời gian xử lý: {response.execution_time_seconds}s | Tokens: {response.total_tokens}")

if __name__ == "__main__":
    main()
