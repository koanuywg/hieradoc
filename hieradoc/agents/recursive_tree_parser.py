import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from hieradoc.tools.text_slicer import TextSlicer
from hieradoc.agents.hierarchical_summarizer import HierarchicalSummarizerAgent

class SplitDecision(BaseModel):
    should_split: bool = Field(..., description="True if this text block contains sub-sections/sub-clauses that should be split into children branches or leaves")
    child_type: str = Field("leaf", description="'branch' if children themselves contain further sub-items, or 'leaf' if they are atomic units")
    split_pattern: Optional[str] = Field(None, description="Regex pattern matching the beginning of each child heading (e.g. '^Khoản\\s+\\d+', '^[a-z]\\)', '^\\d+\\.\\d+')")
    reasoning: str = Field(..., description="Brief reasoning why this segment is atomic or composite")

class RecursiveTreeParserAgent:
    """
    Intelligent Agent that recursively decomposes text segments into an arbitrary N-depth tree.
    Adapts dynamically to any language (vi, en, fr...) and formatting style (Articles, Clauses, Points, 1.1.1...).
    """

    MAX_LEAF_LINES = 35  # Ngưỡng dòng tối đa trước khi cân nhắc chia nhỏ hơn

    @classmethod
    def parse_document_recursively(
        cls,
        clean_lines: List[str],
        level_patterns: List[str],
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> List[Dict[str, Any]]:
        """
        Parses document into a fully recursive N-ary tree using dynamic hierarchy patterns
        and autonomous deep-splitting.
        """
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        total_lines = len(clean_lines)
        if not level_patterns:
            # Fallback nếu không có pattern
            return [{
                "title": "Phần Nội Dung Chính",
                "node_type": "leaf",
                "content_text": TextSlicer.slice_by_lines(clean_lines, 1, total_lines),
                "start_line": 1,
                "end_line": total_lines,
                "summary": "Toàn bộ nội dung tài liệu."
            }]

        top_pattern = level_patterns[0]
        sub_patterns = level_patterns[1:]

        # 1. Tìm các heading cấp cao nhất
        matches = cls._find_pattern_headings(clean_lines, top_pattern)

        if not matches:
            # Nếu top pattern không khớp dòng nào, thử các pattern cấp dưới
            if sub_patterns:
                return cls.parse_document_recursively(clean_lines, sub_patterns, client, model)
            else:
                return [{
                    "title": "Nội Dung Chính",
                    "node_type": "leaf",
                    "content_text": TextSlicer.slice_by_lines(clean_lines, 1, total_lines),
                    "start_line": 1,
                    "end_line": total_lines,
                    "summary": "Nội dung chính"
                }]

        # 2. Phân đoạn theo các heading cấp cao nhất (Đệ quy phân rã đồng thời)
        def _process_top_heading(i, match):
            start_l = match["line"]
            end_l = matches[i + 1]["line"] - 1 if i + 1 < len(matches) else total_lines
            title = match["title"]
            return cls._decompose_segment(
                title=title,
                clean_lines=clean_lines,
                start_line=start_l,
                end_line=end_l,
                remaining_patterns=sub_patterns,
                client=client,
                model=model,
                current_depth=1
            )

        if len(matches) > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(len(matches), 6)) as executor:
                futures = [executor.submit(_process_top_heading, i, m) for i, m in enumerate(matches)]
                nodes = [f.result() for f in futures]
        else:
            nodes = [_process_top_heading(0, matches[0])]

        return nodes

    @classmethod
    def _decompose_segment(
        cls,
        title: str,
        clean_lines: List[str],
        start_line: int,
        end_line: int,
        remaining_patterns: List[str],
        client: OpenAI,
        model: str,
        current_depth: int
    ) -> Dict[str, Any]:
        """
        Decomposes a specific line range [start_line, end_line] into sub-nodes.
        """
        num_lines = end_line - start_line + 1
        content = TextSlicer.slice_by_lines(clean_lines, start_line, end_line)

        # Base case 1: Nếu còn pattern xác định trước, thử chia theo pattern kế tiếp
        patterns_to_try = list(remaining_patterns)
        while patterns_to_try:
            next_pat = patterns_to_try.pop(0)
            matches = cls._find_pattern_headings_in_range(clean_lines, next_pat, start_line, end_line)
            # Không tính chính heading ở dòng start_line nếu nó trùng
            sub_matches = [m for m in matches if m["line"] > start_line]
            if not sub_matches and matches and matches[0]["line"] == start_line and len(matches) > 1:
                sub_matches = matches[1:]
            elif matches and matches[0]["line"] > start_line:
                sub_matches = matches

            if sub_matches:
                # Nếu có phần mào đầu trước heading con đầu tiên
                first_sub_line = sub_matches[0]["line"]
                children = []
                if first_sub_line > start_line + 1:
                    preamble_content = TextSlicer.slice_by_lines(clean_lines, start_line, first_sub_line - 1)
                    if preamble_content.strip():
                        children.append({
                            "title": f"Mở đầu - {title}",
                            "node_type": "leaf",
                            "start_line": start_line,
                            "end_line": first_sub_line - 1,
                            "content_text": preamble_content,
                            "summary": preamble_content[:150],
                            "children": []
                        })

                for j, m in enumerate(sub_matches):
                    sub_start = m["line"]
                    sub_end = sub_matches[j + 1]["line"] - 1 if j + 1 < len(sub_matches) else end_line
                    sub_title = m["title"]
                    sub_node = cls._decompose_segment(
                        title=sub_title,
                        clean_lines=clean_lines,
                        start_line=sub_start,
                        end_line=sub_end,
                        remaining_patterns=patterns_to_try,
                        client=client,
                        model=model,
                        current_depth=current_depth + 1
                    )
                    children.append(sub_node)

                # Tóm tắt branch từ children
                summary = HierarchicalSummarizerAgent.summarize_branch(
                    branch_title=title,
                    children_summaries=[{"title": c["title"], "summary": c.get("summary", "")} for c in children],
                    client=client,
                    model=model
                )
                return {
                    "title": title,
                    "node_type": "branch",
                    "start_line": start_line,
                    "end_line": end_line,
                    "summary": summary,
                    "children": children
                }

        # Base case 2: Đoạn ngắn hoặc không vượt ngưỡng MAX_LEAF_LINES -> Trở thành Leaf nguyên tử
        if num_lines <= cls.MAX_LEAF_LINES:
            # Tạo Leaf trước, việc summarize có thể thực hiện đồng loạt hoặc ngay tại đây
            summary = HierarchicalSummarizerAgent.summarize_leaf(
                title=title,
                content_text=content,
                client=client,
                model=model
            )
            return {
                "title": title,
                "node_type": "leaf",
                "start_line": start_line,
                "end_line": end_line,
                "content_text": content,
                "summary": summary,
                "children": []
            }

        # Base case 3: Đoạn văn dài (> 35 dòng) và không còn pattern định sẵn
        # -> Gọi LLM Inspector để quyết định xem có nên deep-split tiếp hay không
        decision = cls._consult_split_agent(title, content, client, model)
        if decision.should_split and decision.split_pattern:
            matches = cls._find_pattern_headings_in_range(clean_lines, decision.split_pattern, start_line, end_line)
            if len(matches) >= 2:
                children = []
                for k, km in enumerate(matches):
                    sub_start = km["line"]
                    sub_end = matches[k + 1]["line"] - 1 if k + 1 < len(matches) else end_line
                    sub_title = km["title"]
                    sub_node = cls._decompose_segment(
                        title=sub_title,
                        clean_lines=clean_lines,
                        start_line=sub_start,
                        end_line=sub_end,
                        remaining_patterns=[],
                        client=client,
                        model=model,
                        current_depth=current_depth + 1
                    )
                    children.append(sub_node)

                summary = HierarchicalSummarizerAgent.summarize_branch(
                    branch_title=title,
                    children_summaries=[{"title": c["title"], "summary": c.get("summary", "")} for c in children],
                    client=client,
                    model=model
                )
                return {
                    "title": title,
                    "node_type": "branch",
                    "start_line": start_line,
                    "end_line": end_line,
                    "summary": summary,
                    "children": children
                }

        # Nếu không thể chia tiếp, giữ làm Leaf
        summary = HierarchicalSummarizerAgent.summarize_leaf(
            title=title,
            content_text=content,
            client=client,
            model=model
        )
        return {
            "title": title,
            "node_type": "leaf",
            "start_line": start_line,
            "end_line": end_line,
            "content_text": content,
            "summary": summary,
            "children": []
        }

    @classmethod
    def _consult_split_agent(
        cls,
        title: str,
        content: str,
        client: OpenAI,
        model: str
    ) -> SplitDecision:
        sample_text = content[:3000]
        prompt = f"""
        You are an expert Document Structure Decomposer.
        Given a text section titled: "{title}" that is over 35 lines long.
        Evaluate if this section contains distinct sub-clauses, sub-articles, or bullet points (e.g. '1.', '2.', 'a)', 'b)', 'Khoản 1', 'Section 1.1') that should be separated into child nodes.

        If yes:
        - Set should_split = true
        - Provide the exact Python Regex 'split_pattern' matching the heading line of each sub-item.
        - Set child_type = 'branch' if those sub-items also contain smaller points, or 'leaf' if they are the smallest units.
        If no (e.g. continuous narrative paragraph):
        - Set should_split = false.
        """
        try:
            res = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Text:\n{sample_text}"}
                ],
                response_format=SplitDecision,
                temperature=0.0
            )
            return res.choices[0].message.parsed
        except Exception:
            return SplitDecision(should_split=False, reasoning="Fallback on error")

    @classmethod
    def _find_pattern_headings(cls, clean_lines: List[str], pattern: str) -> List[Dict[str, Any]]:
        return cls._find_pattern_headings_in_range(clean_lines, pattern, 1, len(clean_lines))

    @classmethod
    def _find_pattern_headings_in_range(
        cls,
        clean_lines: List[str],
        pattern: str,
        start_line: int,
        end_line: int
    ) -> List[Dict[str, Any]]:
        headings = []
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []

        for line_num in range(start_line, end_line + 1):
            line_str = clean_lines[line_num - 1].strip()
            if rx.search(line_str):
                headings.append({
                    "line": line_num,
                    "title": line_str[:120]
                })
        return headings
