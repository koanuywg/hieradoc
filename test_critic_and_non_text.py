import sys
import time
from dotenv import load_dotenv
from hieradoc import HieraDoc

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

def run_critic_and_non_text_tests():
    print("=" * 70)
    print("   HIERADOC v0.4.0: BALANCED CRITIC & NON-TEXT TABLE/SANDBOX TEST")
    print("=" * 70)

    engine = HieraDoc(storage="sqlite", db_path="hieradoc_v4_vault.db")

    # Nạp văn bản tài chính SLA có Bảng biểu và Dẫn chiếu chéo (Cross-reference)
    print("\n[1] Lập chỉ mục 'sample_financial_sla.txt' (Chứa Bảng SLA và Dẫn chiếu)...")
    res = engine.index("examples/sample_financial_sla.txt", doc_id="fin_sla_2026", cluster="SLA & Tài Chính")
    print(f" -> Nạp thành công: '{res['title']}' ({res['total_branches']} Branches, {res['total_leaves']} Leaves)")

    # -------------------------------------------------------------------------
    # TEST 1: BALANCED TREE CRITIC PHÁT HIỆN DẪN CHIẾU CHÉO (CROSS-REFERENCE)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(" [TEST 1] BALANCED CRITIC: Phát hiện dẫn chiếu chéo và tự động đi tiếp")
    print("=" * 70)
    q1 = "Quy trình và thời hạn để khách hàng nộp hồ sơ khiếu nại bồi thường dịch vụ được quy định như thế nào?"
    print(f" -> Câu hỏi: \"{q1}\"")

    start_t1 = time.time()
    resp1 = engine.query(q1, parallel=True)
    t1 = time.time() - start_t1

    print("\n[KẾT QUẢ TEST 1]:")
    print(resp1.answer)
    print("\nLộ trình Critic & Sub-Agents:")
    for step in resp1.traversal_path:
        if "Critic" in step or "Followed Ref" in step or "Master" in step:
            print(f"  • {step}")
    print(f"\nThời gian: {round(t1, 2)}s | Trích dẫn ({len(resp1.citations)} citations):")
    for c in resp1.citations:
        print(f"  • [{c.doc_title} > {c.branch_title}] Lines {c.lines}: \"{c.exact_quote}\"")

    # -------------------------------------------------------------------------
    # TEST 2: NON-TEXT STRUCTURED TABLE & PYTHON SANDBOX CALCULATION
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(" [TEST 2] BẢNG BIỂU ĐỊNH LƯỢNG + PYTHON SANDBOX TÍNH TOÁN CHÍNH XÁC")
    print("=" * 70)
    q2 = "Nếu mức Uptime thực tế đạt 96.5% và chi phí dịch vụ hàng tháng là 50,000 USD, hãy tính chính xác tổng số tiền nhà cung cấp phải bồi hoàn (gồm hoàn phí và phạt bổ sung)?"
    print(f" -> Câu hỏi tính toán bảng biểu: \"{q2}\"")

    start_t2 = time.time()
    resp2 = engine.query(q2, parallel=True)
    t2 = time.time() - start_t2

    print("\n[KẾT QUẢ TEST 2]:")
    print(resp2.answer)
    print("\nLộ trình Sub-Agents:")
    for step in resp2.traversal_path:
        if "Critic" in step or "Read leaf" in step or "Master" in step:
            print(f"  • {step}")
    print(f"\nThời gian: {round(t2, 2)}s | Trích dẫn ({len(resp2.citations)} citations):")
    for c in resp2.citations:
        print(f"  • [{c.doc_title} > {c.branch_title}] Lines {c.lines}: \"{c.exact_quote}\"")

if __name__ == "__main__":
    run_critic_and_non_text_tests()
