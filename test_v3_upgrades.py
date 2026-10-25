import sys
import time
from dotenv import load_dotenv
from hieradoc import HieraDoc

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

def run_v3_test_suite():
    print("=" * 70)
    print("   HIERADOC v0.3.0 CORE UPGRADE BENCHMARK (TESTING 3 RESOLUTIONS)")
    print("=" * 70)

    engine = HieraDoc(storage="sqlite", db_path="hieradoc_v3_vault.db")

    # =========================================================================
    # TEST 1: SEMANTIC BOUNDARY CHUNKING ON UNSTRUCTURED / FLAT DOCUMENT
    # (Giải quyết Điểm yếu #1 - Văn bản hoàn toàn không có đề mục Chương/Điều)
    # =========================================================================
    print("\n" + "=" * 70)
    print(" [TEST 1] VĂN BẢN PHẲNG KHÔNG ĐỀ MỤC: Semantic Boundary Chunking")
    print("=" * 70)
    print("Đang nạp 'sample_unstructured_memo.txt' (Văn xuôi không đề mục)...")
    res_flat = engine.index("examples/sample_unstructured_memo.txt", doc_id="memo_2026", cluster="Tài Chính")
    print(f" -> Cây sinh ra: {res_flat['total_branches']} Branch, {res_flat['total_leaves']} Leaves theo chủ đề ngữ nghĩa.")
    
    q1 = "Hạn mức dự trữ tiền mặt tối thiểu được hội đồng quản trị phê duyệt là bao nhiêu và gửi tại đâu?"
    print(f" -> Câu hỏi: \"{q1}\"")
    start_t1 = time.time()
    resp1 = engine.query(q1, parallel=True)
    t1 = time.time() - start_t1

    print("\n[KẾT QUẢ TEST 1]:")
    print(resp1.answer)
    print(f"Thời gian: {round(t1, 2)}s | Trích dẫn ({len(resp1.citations)}):")
    for c in resp1.citations:
        print(f"  • Lines {c.lines}: \"{c.exact_quote}\"")

    # =========================================================================
    # TEST 2: AGENTIC QUERY EXPANSION & SYNONYM RESILIENCE
    # (Giải quyết Điểm yếu #2 - Người dùng dùng từ đồng nghĩa/ẩn dụ không có trong SQL LIKE)
    # =========================================================================
    print("\n" + "=" * 70)
    print(" [TEST 2] TỪ ĐỒNG NGHĨA / LEXICAL GAP: Agentic Query Expansion")
    print("=" * 70)
    engine.index("examples/sample_nda.txt", doc_id="nda_2026", cluster="Pháp Lý")

    # Câu hỏi cố tình dùng từ "mã nguồn thuật toán", "bí mật công nghệ"
    q2 = "Mã nguồn thuật toán và bí mật công nghệ có thuộc phạm vi được cam kết bảo vệ không?"
    print(f" -> Câu hỏi từ đồng nghĩa: \"{q2}\"")
    start_t2 = time.time()
    resp2 = engine.query(q2, parallel=True)
    t2 = time.time() - start_t2

    print("\n[KẾT QUẢ TEST 2]:")
    print(resp2.answer)
    print("Lộ trình Master Dispatcher:")
    for step in resp2.traversal_path[:3]:
        print(f"  • {step}")
    print(f"Thời gian: {round(t2, 2)}s | Trích dẫn ({len(resp2.citations)}):")
    for c in resp2.citations:
        print(f"  • [{c.doc_title} > {c.branch_title}] Lines {c.lines}: \"{c.exact_quote}\"")

    # =========================================================================
    # TEST 3: PARENT ROLLUP / FULL BRANCH RETRIEVAL
    # (Giải quyết Điểm yếu #3 - Câu hỏi toàn cảnh cần cuộn đọc cả Chương)
    # =========================================================================
    print("\n" + "=" * 70)
    print(" [TEST 3] TOÀN CẢNH / AUTO-MERGING: Parent Rollup (Đọc trọn vẹn cả Chương)")
    print("=" * 70)
    q3 = "Trình bày toàn bộ nội dung của Chương II về các nghĩa vụ và chế tài xử lý vi phạm hợp đồng?"
    print(f" -> Câu hỏi toàn cảnh: \"{q3}\"")
    start_t3 = time.time()
    resp3 = engine.query(q3, parallel=True)
    t3 = time.time() - start_t3

    print("\n[KẾT QUẢ TEST 3]:")
    print(resp3.answer)
    print("Lộ trình Sub-Agents:")
    for step in resp3.traversal_path:
        if "Rolled up" in step or "Master" in step or "Spawned" in step:
            print(f"  • {step}")
    print(f"Thời gian: {round(t3, 2)}s | Trích dẫn ({len(resp3.citations)}):")
    for c in resp3.citations:
        print(f"  • [{c.doc_title} > {c.branch_title}] Lines {c.lines}: \"{c.exact_quote}\"")

if __name__ == "__main__":
    run_v3_test_suite()
