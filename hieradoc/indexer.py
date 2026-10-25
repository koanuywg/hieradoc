import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
from hieradoc.storage.base import BaseTreeStorage
from hieradoc.core.extractor import FileExtractor
from hieradoc.tools.layout_scanner import LayoutScanner
from hieradoc.tools.text_slicer import TextSlicer
from hieradoc.tools.boundary_detector import SemanticBoundaryDetector
from hieradoc.agents.document_inspector import DocumentInspectorAgent
from hieradoc.agents.hierarchical_summarizer import HierarchicalSummarizerAgent
from hieradoc.agents.recursive_tree_parser import RecursiveTreeParserAgent

class HierarchicalIndexer:
    """
    Ingests documents, automatically detects hierarchical structure,
    indexes line coordinates [L0001], generates bottom-up summaries,
    and saves the tree into any BaseTreeStorage adapter.
    """

    def __init__(
        self,
        storage: BaseTreeStorage,
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ):
        self.storage = storage
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def index_file(
        self,
        file_path: str,
        doc_id: Optional[str] = None,
        cluster_title: str = "Tài Liệu Chung"
    ) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        code_name = doc_id or p.stem
        raw_text = FileExtractor.extract_text(str(p))
        return self.index_text(
            raw_text=raw_text,
            doc_id=code_name,
            cluster_title=cluster_title
        )

    def index_text(
        self,
        raw_text: str,
        doc_id: str,
        title: Optional[str] = None,
        cluster_title: str = "Tài Liệu Chung"
    ) -> Dict[str, Any]:
        if not raw_text.strip():
            raise ValueError("Document content is empty.")

        indexed_text, clean_lines = FileExtractor.add_line_numbers(raw_text)

        # 1. Blueprint Inspection
        sample_size = min(len(indexed_text), 6000)
        blueprint = DocumentInspectorAgent.inspect(
            sample_indexed_text=indexed_text[:sample_size],
            client=self.client,
            model=self.model
        )
        doc_title = title or blueprint.title or doc_id

        # 2. Extract Hierarchical Tree
        if blueprint.has_explicit_headings:
            patterns = [
                p for p in [
                    blueprint.level_1_pattern,
                    blueprint.level_2_pattern,
                    blueprint.level_3_pattern,
                    blueprint.level_4_pattern
                ] if p
            ]
            tree_data = RecursiveTreeParserAgent.parse_document_recursively(
                clean_lines=clean_lines,
                level_patterns=patterns,
                client=self.client,
                model=self.model
            )
        else:
            tree_data = self._process_flat(clean_lines, doc_title)

        # 3. Summarize Root Document
        top_overview = [
            {"branch_title": node.get("title") or node.get("branch_title", "Phần"), "summary": node.get("summary", "")}
            for node in tree_data
        ]
        doc_summary = HierarchicalSummarizerAgent.summarize_root(
            doc_title=doc_title,
            chapters_overview=top_overview,
            client=self.client,
            model=self.model
        )

        # 4. Save into Storage Adapter (SQLite or Supabase) with recursive support
        save_res = self.storage.save_document_tree(
            doc_id=doc_id,
            title=doc_title,
            summary=doc_summary,
            tree_data=tree_data,
            cluster_title=cluster_title
        )

        def _count_leaves(nodes_list):
            count = 0
            for n in nodes_list:
                if n.get("node_type") == "leaf":
                    count += 1
                ch = n.get("children") or n.get("articles") or n.get("leaves") or []
                count += _count_leaves(ch)
            return count

        total_leaves = _count_leaves(tree_data)
        return {
            "doc_id": doc_id,
            "title": doc_title,
            "total_branches": len(tree_data),
            "total_leaves": total_leaves,
            "cluster_title": cluster_title,
            "summary": doc_summary
        }

    def _process_structured(self, clean_lines: List[str], blueprint) -> List[Dict[str, Any]]:
        headings = LayoutScanner.scan_headings(
            clean_lines=clean_lines,
            level_1_pattern=blueprint.level_1_pattern,
            level_2_pattern=blueprint.level_2_pattern,
            level_3_pattern=blueprint.level_3_pattern
        )

        # Group into level 1 branches
        level_1 = [h for h in headings if h.level == 1]
        level_2 = [h for h in headings if h.level == 2]

        total_lines = len(clean_lines)
        tree_branches = []

        if not level_1 and level_2:
            # Chỉ có Level 2 (Điều/Article) mà không có Chương -> Gom vào 1 Branch chung
            branch_title = "Phần Nội Dung Chính"
            leaves = self._slice_leaves(level_2, clean_lines, total_lines)
            b_summary = HierarchicalSummarizerAgent.summarize_branch(
                branch_title=branch_title,
                children_summaries=[{"title": l["title"], "summary": l["summary"]} for l in leaves],
                client=self.client,
                model=self.model
            )
            tree_branches.append({
                "branch_title": branch_title,
                "summary": b_summary,
                "articles": leaves
            })
            return tree_branches

        for i, b_head in enumerate(level_1):
            start_l = b_head.line_number
            end_l = level_1[i + 1].line_number - 1 if i + 1 < len(level_1) else total_lines
            branch_title = b_head.matched_text

            # Các Điều thuộc Chương này
            branch_leaves_heads = [h for h in level_2 if start_l <= h.line_number <= end_l]
            if branch_leaves_heads:
                leaves = self._slice_leaves(branch_leaves_heads, clean_lines, end_l)
            else:
                # Nếu chương không có Điều nhỏ hơn, chính chương là 1 leaf
                leaf_content = TextSlicer.slice_by_lines(clean_lines, start_l, end_l)
                leaf_summary = HierarchicalSummarizerAgent.summarize_leaf(
                    title=branch_title,
                    content_text=leaf_content,
                    client=self.client,
                    model=self.model
                )
                leaves = [{
                    "title": branch_title,
                    "summary": leaf_summary,
                    "content_text": leaf_content,
                    "start_line": start_l,
                    "end_line": end_l
                }]

            b_summary = HierarchicalSummarizerAgent.summarize_branch(
                branch_title=branch_title,
                children_summaries=[{"title": l["title"], "summary": l["summary"]} for l in leaves],
                client=self.client,
                model=self.model
            )
            tree_branches.append({
                "branch_title": branch_title,
                "summary": b_summary,
                "articles": leaves
            })

        return tree_branches

    def _slice_leaves(self, leaf_heads, clean_lines: List[str], max_line: int) -> List[Dict[str, Any]]:
        leaves = []
        for j, l_head in enumerate(leaf_heads):
            l_start = l_head.line_number
            l_end = leaf_heads[j + 1].line_number - 1 if j + 1 < len(leaf_heads) else max_line
            l_title = l_head.matched_text
            l_content = TextSlicer.slice_by_lines(clean_lines, l_start, l_end)
            l_summary = HierarchicalSummarizerAgent.summarize_leaf(
                title=l_title,
                content_text=l_content,
                client=self.client,
                model=self.model
            )
            leaves.append({
                "title": l_title,
                "summary": l_summary,
                "content_text": l_content,
                "start_line": l_start,
                "end_line": l_end
            })
        return leaves

    def _process_flat(self, clean_lines: List[str], doc_title: str) -> List[Dict[str, Any]]:
        """
        Segments unstructured/flat documents using Semantic Topic Shift detection
        instead of mechanical line slicing. Preserves natural topic coherence.
        """
        sections = SemanticBoundaryDetector.segment_text(
            clean_lines=clean_lines,
            client=self.client,
            model=self.model
        )

        leaves = []
        for sec in sections:
            chunk_content = TextSlicer.slice_by_lines(clean_lines, sec.start_line, sec.end_line)
            leaves.append({
                "title": sec.title,
                "summary": sec.summary,
                "content_text": chunk_content,
                "start_line": sec.start_line,
                "end_line": sec.end_line
            })

        b_summary = HierarchicalSummarizerAgent.summarize_branch(
            branch_title=doc_title,
            children_summaries=[{"title": l["title"], "summary": l["summary"]} for l in leaves],
            client=self.client,
            model=self.model
        )
        return [{
            "branch_title": f"Chủ Đề Chính: {doc_title}",
            "summary": b_summary,
            "articles": leaves
        }]
