import sys
import time
from dotenv import load_dotenv
from hieradoc import HieraDoc

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

def run_tests():
    print("=" * 60)
    print("   TESTING PARALLEL MULTI-AGENT RETRIEVAL ENGINE")
    print("=" * 60)

    # Khởi tạo Engine SQLite
    engine = HieraDoc(storage="sqlite", db_path="hieradoc_vault.db")

    # Nạp cả 2 tài liệu: NDA và Cloud SLA
    print("\n[1] Lập chỉ mục 2 văn bản: sample_nda.txt & sample_cloud_sla.txt...")
    res_nda = engine.index("examples/sample_nda.txt", doc_id="nda_doc", cluster="Pháp Lý")
    res_sla = engine.index("examples/sample_cloud_sla.txt", doc_id="sla_doc", cluster="Hạ Tầng Cloud")

    print(f" -> Nạp NDA: '{res_nda['title']}' ({res_nda['total_leaves']} leaves)")
    print(f" -> Nạp SLA: '{res_sla['title']}' ({res_sla['total_leaves']} leaves)")

    # -------------------------------------------------------------
    # TEST 1: Cross-Document Parallel Query
    # -------------------------------------------------------------
    q1 = "So sánh thời hạn lưu giữ dữ liệu sau khi chấm dứt trong Cloud SLA và thời hạn bảo mật thông tin trong thỏa thuận NDA?"
    print(f"\n[2] TEST 1: Truy vấn Đa Tài Liệu (Cross-Document):\n -> \"{q1}\"")

    start_t = time.time()
    resp1 = engine.query(q1, parallel=True)
    t1 = time.time() - start_t

    print("\n[KẾT QUẢ TEST 1]:")
    print(resp1.answer)
    print("\nLộ trình phân luồng Sub-Agents:")
    for p in resp1.traversal_path:
        print(f"  • {p}")
    print(f"\nTrích dẫn ({len(resp1.citations)} citations):")
    for c in resp1.citations:
        print(f"  - [{c.doc_title} > {c.branch_title}] Lines {c.lines}: \"{c.exact_quote}\"")
    print(f"Thời gian: {round(t1, 2)}s | Tokens: {resp1.total_tokens}")

    # -------------------------------------------------------------
    # TEST 2: Cross-Chapter Parallel Query (Cùng 1 tài liệu nhưng 2 chương khác nhau)
    # -------------------------------------------------------------
    q2 = "Thời hạn bảo mật kéo dài bao lâu và mức phạt tối đa khi vi phạm nghĩa vụ bảo mật là bao nhiêu?"
    print(f"\n[3] TEST 2: Truy vấn Đa Chương (Cross-Chapter):\n -> \"{q2}\"")

    start_t = time.time()
    resp2 = engine.query(q2, parallel=True)
    t2 = time.time() - start_t

    print("\n[KẾT QUẢ TEST 2]:")
    print(resp2.answer)
    print("\nLộ trình phân luồng Sub-Agents:")
    for p in resp2.traversal_path:
        print(f"  • {p}")
    print(f"\nTrích dẫn ({len(resp2.citations)} citations):")
    for c in resp2.citations:
        print(f"  - [{c.doc_title} > {c.branch_title}] Lines {c.lines}: \"{c.exact_quote}\"")
    print(f"Thời gian: {round(t2, 2)}s | Tokens: {resp2.total_tokens}")

if __name__ == "__main__":
    run_tests()
