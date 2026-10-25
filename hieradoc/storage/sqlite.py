import sqlite3
import uuid
from typing import List, Dict, Any, Optional
from hieradoc.storage.base import BaseTreeStorage

class SQLiteTreeStorage(BaseTreeStorage):
    """
    Zero-Setup Local SQLite Storage for Hierarchical Document Trees.
    Creates and manages local .db file without requiring external servers.
    """

    def __init__(self, db_path: str = "hieradoc_vault.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    code_name TEXT UNIQUE,
                    title TEXT NOT NULL,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 2. Tree Nodes table (cluster -> document -> branch -> leaf)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tree_nodes (
                    id TEXT PRIMARY KEY,
                    document_id TEXT,
                    parent_id TEXT,
                    node_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    content_text TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    node_index INTEGER DEFAULT 0,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY(parent_id) REFERENCES tree_nodes(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_parent ON tree_nodes(parent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON tree_nodes(node_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_doc ON tree_nodes(document_id)")
            conn.commit()

    def save_document_tree(
        self,
        doc_id: str,
        title: str,
        summary: str,
        tree_data: List[Dict[str, Any]],
        cluster_title: str = "Tài Liệu Chung"
    ) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Kiểm tra hoặc tạo Cụm Gốc (Root Cluster)
            cursor.execute(
                "SELECT id FROM tree_nodes WHERE node_type = 'cluster' AND title = ? AND parent_id IS NULL",
                (cluster_title,)
            )
            cluster_row = cursor.fetchone()
            if cluster_row:
                cluster_id = cluster_row["id"]
            else:
                cluster_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO tree_nodes (id, parent_id, node_type, title, summary, node_index)
                    VALUES (?, NULL, 'cluster', ?, ?, 0)
                """, (cluster_id, cluster_title, f"Cụm chủ đề: {cluster_title}"))

            # 2. Tạo hoặc ghi đè Document
            cursor.execute("SELECT id FROM documents WHERE code_name = ?", (doc_id,))
            existing_doc = cursor.fetchone()
            if existing_doc:
                db_doc_id = existing_doc["id"]
                # Xóa các node cũ của văn bản này
                cursor.execute("DELETE FROM tree_nodes WHERE document_id = ?", (db_doc_id,))
                cursor.execute("UPDATE documents SET title = ?, summary = ? WHERE id = ?", (title, summary, db_doc_id))
            else:
                db_doc_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO documents (id, code_name, title, summary)
                    VALUES (?, ?, ?, ?)
                """, (db_doc_id, doc_id, title, summary))

            # 3. Tạo Document Node (nằm dưới Root Cluster)
            doc_node_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tree_nodes (id, document_id, parent_id, node_type, title, summary, node_index)
                VALUES (?, ?, ?, 'document', ?, ?, 0)
            """, (doc_node_id, db_doc_id, cluster_id, title, summary))

            # 4. Lưu các Nhánh (Branches) và Node Lá (Leaves)
            for b_idx, branch in enumerate(tree_data):
                branch_node_id = str(uuid.uuid4())
                b_title = branch.get("chapter_title") or branch.get("branch_title") or f"Nhánh {b_idx + 1}"
                b_summary = branch.get("summary") or ""
                cursor.execute("""
                    INSERT INTO tree_nodes (id, document_id, parent_id, node_type, title, summary, node_index)
                    VALUES (?, ?, ?, 'branch', ?, ?, ?)
                """, (branch_node_id, db_doc_id, doc_node_id, b_title, b_summary, b_idx))

                articles = branch.get("articles") or branch.get("leaves") or []
                for a_idx, leaf in enumerate(articles):
                    leaf_node_id = str(uuid.uuid4())
                    l_title = leaf.get("title") or f"Mục {a_idx + 1}"
                    l_summary = leaf.get("summary") or ""
                    l_content = leaf.get("content_text") or leaf.get("content") or ""
                    l_start = leaf.get("start_line")
                    l_end = leaf.get("end_line")

                    cursor.execute("""
                        INSERT INTO tree_nodes (
                            id, document_id, parent_id, node_type, title, summary, 
                            content_text, start_line, end_line, node_index
                        )
                        VALUES (?, ?, ?, 'leaf', ?, ?, ?, ?, ?, ?)
                    """, (
                        leaf_node_id, db_doc_id, branch_node_id, l_title, l_summary,
                        l_content, l_start, l_end, a_idx
                    ))

            conn.commit()
            return {"document_id": db_doc_id, "cluster_id": cluster_id, "title": title}

    def explore_node(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if node_id is None:
                # Trả về các Root Clusters
                cursor.execute("""
                    SELECT id, title, summary, node_type, start_line, end_line
                    FROM tree_nodes
                    WHERE parent_id IS NULL AND node_type = 'cluster'
                    ORDER BY node_index ASC
                """)
            else:
                cursor.execute("""
                    SELECT id, title, summary, node_type, start_line, end_line
                    FROM tree_nodes
                    WHERE parent_id = ?
                    ORDER BY node_index ASC
                """, (node_id,))

            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "node_type": r["node_type"],
                    "summary": (r["summary"] or "")[:200],
                    "start_line": r["start_line"],
                    "end_line": r["end_line"]
                }
                for r in rows
            ]

    def search_keyword(self, keyword: str, limit: int = 15) -> List[Dict[str, Any]]:
        clean_kw = keyword.strip()
        if not clean_kw:
            return []

        stop_words = {"và", "với", "các", "những", "của", "cho", "trong", "được", "là", "bởi", "tại", "theo", 
                      "what", "is", "the", "by", "of", "in", "to", "for", "and", "or", "how", "when", "does"}
        raw_words = [w for w in clean_kw.replace(",", " ").replace(".", " ").replace("?", " ").split() if len(w) > 1]
        meaningful_words = [w for w in raw_words if w.lower() not in stop_words]

        candidates = []
        if len(meaningful_words) >= 3:
            for i in range(len(meaningful_words) - 2):
                candidates.append(f"{meaningful_words[i]} {meaningful_words[i+1]} {meaningful_words[i+2]}")
        if len(meaningful_words) >= 2:
            for i in range(len(meaningful_words) - 1):
                candidates.append(f"{meaningful_words[i]} {meaningful_words[i+1]}")
        candidates.extend(meaningful_words)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            node_scores: Dict[str, float] = {}
            node_data: Dict[str, Dict[str, Any]] = {}

            # 1. Thử tìm cụm đầy đủ
            cursor.execute("""
                SELECT id, title, summary, node_type, document_id, parent_id
                FROM tree_nodes
                WHERE title LIKE ? OR summary LIKE ?
                LIMIT ?
            """, (f"%{clean_kw}%", f"%{clean_kw}%", limit))
            exact_matches = cursor.fetchall()
            for r in exact_matches:
                nid = r["id"]
                node_scores[nid] = 50.0
                node_data[nid] = dict(r)

            # 2. Xếp hạng trọng số từ khóa n-grams
            for cand in candidates[:8]:
                weight = len(cand.split()) * 3.0
                cand_pattern = f"%{cand}%"
                cursor.execute("""
                    SELECT id, title, summary, node_type, document_id, parent_id
                    FROM tree_nodes
                    WHERE title LIKE ? OR summary LIKE ? OR content_text LIKE ?
                    LIMIT 20
                """, (cand_pattern, cand_pattern, cand_pattern))
                matches = cursor.fetchall()
                for r in matches:
                    nid = r["id"]
                    node_scores[nid] = node_scores.get(nid, 0.0) + weight
                    if r["node_type"] == "leaf":
                        node_scores[nid] += 1.5
                    if nid not in node_data:
                        node_data[nid] = dict(r)

            sorted_ids = sorted(node_scores.keys(), key=lambda x: node_scores[x], reverse=True)
            return [node_data[nid] for nid in sorted_ids[:limit]]

    def read_leaf(self, leaf_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, document_id, parent_id, title, summary, content_text, start_line, end_line
                FROM tree_nodes
                WHERE id = ? AND node_type = 'leaf'
            """, (leaf_id,))
            leaf = cursor.fetchone()
            if not leaf:
                return {"error": f"Không tìm thấy node lá có ID {leaf_id}"}

            doc_title = "Văn bản"
            if leaf["document_id"]:
                cursor.execute("SELECT title FROM documents WHERE id = ?", (leaf["document_id"],))
                d_row = cursor.fetchone()
                if d_row:
                    doc_title = d_row["title"]

            branch_title = "Phần"
            if leaf["parent_id"]:
                cursor.execute("SELECT title FROM tree_nodes WHERE id = ?", (leaf["parent_id"],))
                b_row = cursor.fetchone()
                if b_row:
                    branch_title = b_row["title"]

            return {
                "leaf_id": leaf["id"],
                "title": leaf["title"],
                "doc_title": doc_title,
                "branch_title": branch_title,
                "summary": leaf["summary"] or "",
                "content": leaf["content_text"] or "",
                "start_line": leaf["start_line"],
                "end_line": leaf["end_line"]
            }

    def read_branch_full(self, branch_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, document_id, title, summary
                FROM tree_nodes
                WHERE id = ?
            """, (branch_id,))
            branch = cursor.fetchone()
            if not branch:
                return {"error": f"Không tìm thấy branch ID {branch_id}"}

            doc_title = "Văn bản"
            if branch["document_id"]:
                cursor.execute("SELECT title FROM documents WHERE id = ?", (branch["document_id"],))
                d_row = cursor.fetchone()
                if d_row:
                    doc_title = d_row["title"]

            # Lấy toàn bộ leaves con của branch này
            cursor.execute("""
                SELECT id, title, content_text, start_line, end_line
                FROM tree_nodes
                WHERE parent_id = ?
                ORDER BY node_index ASC
            """, (branch_id,))
            leaves = cursor.fetchall()
            if not leaves:
                return {"error": f"Nhánh {branch_id} không có node con"}

            full_texts = []
            min_line = None
            max_line = None

            for l in leaves:
                t = l["content_text"] or ""
                if t:
                    full_texts.append(f"### {l['title']}\n{t}")
                if l["start_line"] is not None:
                    min_line = l["start_line"] if min_line is None else min(min_line, l["start_line"])
                if l["end_line"] is not None:
                    max_line = l["end_line"] if max_line is None else max(max_line, l["end_line"])

            return {
                "branch_id": branch["id"],
                "title": branch["title"],
                "doc_title": doc_title,
                "branch_title": branch["title"],
                "summary": branch["summary"] or "",
                "content": "\n\n".join(full_texts),
                "start_line": min_line,
                "end_line": max_line,
                "leaves_count": len(leaves)
            }

    def list_documents(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.id, d.code_name, d.title, d.summary, COUNT(n.id) as total_nodes
                FROM documents d
                LEFT JOIN tree_nodes n ON d.id = n.document_id
                GROUP BY d.id
                ORDER BY d.created_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
