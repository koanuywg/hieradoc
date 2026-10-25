import os
from typing import List, Dict, Any, Optional
from hieradoc.storage.base import BaseTreeStorage

class SupabaseTreeStorage(BaseTreeStorage):
    """
    Cloud PostgreSQL & Multi-tenant Tree Storage via Supabase.
    Requires supabase-py and SUPABASE_URL / SUPABASE_KEY.
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None, workspace_id: Optional[str] = None):
        try:
            from supabase import create_client, Client
        except ImportError:
            raise ImportError("Please install supabase: pip install supabase")

        sb_url = url or os.getenv("SUPABASE_URL")
        sb_key = key or os.getenv("SUPABASE_KEY")
        if not sb_url or not sb_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be provided")

        self.client: Client = create_client(sb_url, sb_key)
        self.workspace_id = workspace_id

    def save_document_tree(
        self,
        doc_id: str,
        title: str,
        summary: str,
        tree_data: List[Dict[str, Any]],
        cluster_title: str = "Tài Liệu Chung"
    ) -> Dict[str, Any]:
        # Tương thích với bảng legal_nodes và documents trên Supabase
        # 1. Tìm hoặc tạo cluster
        c_query = self.client.table("legal_nodes").select("id").eq("node_type", "cluster").eq("title", cluster_title)
        if self.workspace_id:
            c_query = c_query.eq("workspace_id", self.workspace_id)
        c_res = c_query.execute()
        if c_res.data:
            cluster_id = c_res.data[0]["id"]
        else:
            ins = self.client.table("legal_nodes").insert({
                "title": cluster_title,
                "summary": f"Cụm chủ đề: {cluster_title}",
                "node_type": "cluster",
                "workspace_id": self.workspace_id
            }).execute()
            cluster_id = ins.data[0]["id"]

        # 2. Insert document
        doc_res = self.client.table("documents").upsert({
            "code_name": doc_id,
            "title": title,
            "law_summary": summary,
            "workspace_id": self.workspace_id
        }, on_conflict="code_name").execute()
        db_doc_id = doc_res.data[0]["id"]

        # 3. Insert document node
        doc_node = self.client.table("legal_nodes").insert({
            "document_id": db_doc_id,
            "parent_id": cluster_id,
            "title": title,
            "summary": summary,
            "node_type": "document",
            "workspace_id": self.workspace_id
        }).execute()
        doc_node_id = doc_node.data[0]["id"]

        # 4. Insert branches & leaves
        for b_idx, branch in enumerate(tree_data):
            b_title = branch.get("chapter_title") or branch.get("branch_title") or f"Nhánh {b_idx + 1}"
            br_res = self.client.table("legal_nodes").insert({
                "document_id": db_doc_id,
                "parent_id": doc_node_id,
                "title": b_title,
                "summary": branch.get("summary", ""),
                "node_type": "branch",
                "node_index": b_idx,
                "workspace_id": self.workspace_id
            }).execute()
            branch_id = br_res.data[0]["id"]

            articles = branch.get("articles") or branch.get("leaves") or []
            leaf_payloads = []
            for a_idx, leaf in enumerate(articles):
                leaf_payloads.append({
                    "document_id": db_doc_id,
                    "parent_id": branch_id,
                    "title": leaf.get("title", f"Mục {a_idx + 1}"),
                    "summary": leaf.get("summary", ""),
                    "content_text": leaf.get("content_text") or leaf.get("content", ""),
                    "start_line": leaf.get("start_line"),
                    "end_line": leaf.get("end_line"),
                    "node_type": "leaf",
                    "node_index": a_idx,
                    "workspace_id": self.workspace_id
                })
            if leaf_payloads:
                self.client.table("legal_nodes").insert(leaf_payloads).execute()

        return {"document_id": db_doc_id, "cluster_id": cluster_id, "title": title}

    def explore_node(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.client.table("legal_nodes").select("id, title, summary, node_type, start_line, end_line")
        if node_id is None:
            query = query.is_("parent_id", "null").eq("node_type", "cluster")
        else:
            query = query.eq("parent_id", node_id)

        if self.workspace_id:
            query = query.or_(f"workspace_id.eq.{self.workspace_id},workspace_id.is.null")

        query = query.order("node_index", desc=False)
        res = query.execute()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "node_type": r["node_type"],
                "summary": (r.get("summary") or "")[:200],
                "start_line": r.get("start_line"),
                "end_line": r.get("end_line")
            }
            for r in (res.data or [])
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

        node_scores: Dict[str, float] = {}
        node_data: Dict[str, Dict[str, Any]] = {}

        for cand in candidates[:8]:
            try:
                sub_q = self.client.table("legal_nodes")\
                    .select("id, title, summary, node_type, document_id, parent_id")\
                    .or_(f"title.ilike.%{cand}%,summary.ilike.%{cand}%,content_text.ilike.%{cand}%")
                if self.workspace_id:
                    sub_q = sub_q.or_(f"workspace_id.eq.{self.workspace_id},workspace_id.is.null")
                sub_res = sub_q.limit(20).execute()
                weight = len(cand.split()) * 3.0
                for item in (sub_res.data or []):
                    nid = item["id"]
                    node_scores[nid] = node_scores.get(nid, 0.0) + weight
                    if item.get("node_type") == "leaf":
                        node_scores[nid] += 1.5
                    if nid not in node_data:
                        node_data[nid] = item
            except Exception:
                continue

        sorted_ids = sorted(node_scores.keys(), key=lambda x: node_scores[x], reverse=True)
        return [node_data[nid] for nid in sorted_ids[:limit]]

    def read_leaf(self, leaf_id: str) -> Dict[str, Any]:
        res = self.client.table("legal_nodes")\
            .select("id, title, summary, content_text, start_line, end_line, parent_id, document_id")\
            .eq("id", leaf_id).execute()
        if not res.data:
            return {"error": f"Node {leaf_id} not found"}
        leaf = res.data[0]

        doc_title = "Văn bản"
        if leaf.get("document_id"):
            d_res = self.client.table("documents").select("title").eq("id", leaf["document_id"]).execute()
            if d_res.data:
                doc_title = d_res.data[0]["title"]

        branch_title = "Phần"
        if leaf.get("parent_id"):
            b_res = self.client.table("legal_nodes").select("title").eq("id", leaf["parent_id"]).execute()
            if b_res.data:
                branch_title = b_res.data[0]["title"]

        return {
            "leaf_id": leaf["id"],
            "title": leaf["title"],
            "doc_title": doc_title,
            "branch_title": branch_title,
            "summary": leaf.get("summary", ""),
            "content": leaf.get("content_text", ""),
            "start_line": leaf.get("start_line"),
            "end_line": leaf.get("end_line")
        }

    def list_documents(self) -> List[Dict[str, Any]]:
        q = self.client.table("documents").select("id, code_name, title, law_summary")
        if self.workspace_id:
            q = q.eq("workspace_id", self.workspace_id)
        res = q.execute()
        return res.data or []
