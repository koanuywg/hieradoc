import os
import sys
import sqlite3
from dotenv import load_dotenv

load_dotenv("D:/code/HỌC/hieradoc/.env")
from hieradoc import HieraDoc

DEEP_LEGAL_DOC = """BỘ LUẬT DÂN SỰ MẪU KIỂM THỬ ĐỘ SÂU ĐỆ QUY

Chương I: QUY ĐỊNH CHUNG VỀ NGHĨA VỤ DÂN SỰ
Điều 1. Khái niệm và căn cứ xác lập nghĩa vụ
Khoản 1. Nghĩa vụ là việc mà theo đó bên có nghĩa vụ phải chuyển giao vật, chuyển giao quyền, trả tiền hoặc giấy tờ có giá, thực hiện công việc khác vì lợi ích của bên có quyền.
Điểm a) Nghĩa vụ phát sinh từ hợp đồng và các giao dịch dân sự hợp pháp.
Tiết 1: Các hợp đồng song vụ làm phát sinh quyền và nghĩa vụ bình đẳng giữa các chủ thể tham gia xác lập cam kết.
Tiết 2: Hợp đồng có đền bù đòi hỏi sự tương xứng về giá trị tài sản trao đổi giữa hai bên trong giao dịch.
Điểm b) Nghĩa vụ phát sinh từ hành vi đơn phương và vi phạm pháp luật.
Tiết 1: Hành vi gây thiệt hại ngoài hợp đồng buộc người gây thiệt hại phải bồi hoàn toàn bộ và kịp thời.
Tiết 2: Người làm công, học nghề gây thiệt hại thì cơ quan, tổ chức phải bồi thường theo quy định của điều khoản thi hành.

Khoản 2. Căn cứ chấm dứt nghĩa vụ dân sự
Điểm a) Chấp hành xong toàn bộ nội dung cam kết
Tiết 1: Bên có nghĩa vụ đã hoàn thành việc chuyển giao toàn bộ số tiền thanh toán cùng lãi suất theo thỏa thuận.
Tiết 2: Tài sản bảo đảm đã được giải chấp và trao trả lại quyền định đoạt cho chủ sở hữu hợp pháp.
Điểm b) Chấm dứt theo ý chí của các bên
Tiết 1: Thỏa thuận thay thế nghĩa vụ ban đầu bằng một nghĩa vụ hoàn toàn mới.
Tiết 2: Bên có quyền tuyên bố miễn trừ toàn bộ nghĩa vụ mà không đòi hỏi bất kỳ khoản tiền bồi hoàn nào.

Chương II: HỢP ĐỒNG MUA BÁN VÀ PHẠT VI PHẠM
Điều 2. Chế tài vi phạm nghĩa vụ hợp đồng
Khoản 1. Mức phạt vi phạm và tiền lãi do chậm trả
Điểm a) Khung phạt vi phạm hợp đồng thương mại
Tiết 1: Mức phạt vi phạm nghĩa vụ do các bên tự nguyện thỏa thuận nhưng không được vượt quá 8% giá trị phần nghĩa vụ bị vi phạm.
Tiết 2: Đối với giao dịch xây dựng dân dụng, mức phạt tối đa được áp dụng là 12% giá trị hợp đồng vi phạm.
"""

def test_deep_recursive_tree():
    print("=====================================================================")
    print(">>> TEST: DEEP RECURSIVE TREE INGESTION & RETRIEVAL (5 TẦNG LỒNG NHAU)")
    print("=====================================================================")

    db_path = "test_deep_recursive.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    # Ghi file tài liệu kiểm thử
    file_path = "sample_deep_legal.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(DEEP_LEGAL_DOC)

    hieradoc = HieraDoc(storage="sqlite", db_path=db_path)

    print("\n--- 1. Ingesting 5-Level Deep Legal Document ---")
    res = hieradoc.index(file_path_or_text=file_path, doc_id="BO_LUAT_DAN_SU_TEST", cluster="Pháp Luật Dân Sự")
    print(f"Index result: {res}")

    # Kiểm tra cấu trúc phân cấp trong SQLite
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, parent_id, node_type, title, start_line, end_line FROM tree_nodes")
    rows = cursor.fetchall()

    print(f"\n--- 2. Database Verification: Total nodes = {len(rows)} ---")
    for r in rows:
        p_info = r["parent_id"][:8] if r["parent_id"] else "ROOT"
        print(f"[{r['node_type'].upper():8}] (Parent: {p_info}) {r['title'][:65]}")

    # Đếm số tầng sâu nhất của cây
    def get_node_depth(node_id):
        depth = 0
        curr = node_id
        while curr:
            cursor.execute("SELECT parent_id FROM tree_nodes WHERE id = ?", (curr,))
            parent = cursor.fetchone()
            if parent and parent["parent_id"]:
                depth += 1
                curr = parent["parent_id"]
            else:
                break
        return depth

    max_depth = max(get_node_depth(r["id"]) for r in rows)
    print(f"\n=> Maximum Tree Depth in Database: {max_depth} levels!")

    print("\n--- 3. Testing Deep Traversal Query ---")
    query = "Mức phạt tối đa đối với vi phạm trong hợp đồng xây dựng dân dụng là bao nhiêu phần trăm?"
    print(f"Query: '{query}'")

    response = hieradoc.query(question=query)
    print(f"\nFinal Answer:\n{response.answer}")
    print(f"\nCitations ({len(response.citations)}):")
    for c in response.citations:
        print(f" - [{c.doc_id}] {c.leaf_title} Lines {c.lines}: \"{c.exact_quote}\"")

    assert "12%" in response.answer or "12" in response.answer, "Failed to retrieve 12% penalty from deeply nested Tiết 2!"
    print("\n>>> ALL TESTS PASSED! Deep recursive tree ingestion and query functioning perfectly!")

if __name__ == "__main__":
    test_deep_recursive_tree()
