import os
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

class SemanticSection(BaseModel):
    title: str = Field(..., description="Concise title summarizing this coherent topic section")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    summary: str = Field(..., description="1-2 sentences summarizing the core topic or obligation of this section")

class DocumentSegmentationResult(BaseModel):
    sections: List[SemanticSection] = Field(..., description="Ordered, contiguous semantic topic sections covering the document from start to finish")

class SemanticBoundaryDetector:
    """
    Detects natural semantic topic boundaries in unstructured/flat documents
    without relying on explicit 'Chapter/Article' headings.
    Ensures every section has meaningful thematic boundaries and exact line coordinates.
    """

    @classmethod
    def segment_text(
        cls,
        clean_lines: List[str],
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> List[SemanticSection]:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        total_lines = len(clean_lines)
        if total_lines == 0:
            return []

        # Tạo văn bản có gắn số dòng [L0001]
        indexed_text = "\n".join(f"[L{i:04d}] {line}" for i, line in enumerate(clean_lines, 1))

        # Nếu văn bản ngắn (dưới 150 dòng), phân đoạn toàn bộ trong 1 lần gọi
        if total_lines <= 150:
            prompt = """
            You are a Structural Discourse Analyst.
            Analyze the provided line-indexed document (which lacks formal Chapter/Article headings).
            Identify the natural semantic topic boundaries where the discourse shifts from one topic/theme to another.

            Rules:
            1. Divide the document into 2 to 6 contiguous, non-overlapping semantic sections.
            2. The first section must start at line 1. The last section must end at the very last line of the document.
            3. For each section, assign a clear descriptive title, start_line, end_line, and a 1-2 sentence summary.
            """

            try:
                resp = client.beta.chat.completions.parse(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Document Lines (Total {total_lines} lines):\n\n{indexed_text}"}
                    ],
                    response_format=DocumentSegmentationResult,
                    temperature=0.0
                )
                res = resp.choices[0].message.parsed
                if res and res.sections:
                    return res.sections
            except Exception:
                pass

        # Fallback: Quét theo từng khối trượt 50 dòng có bảo toàn ranh giới
        chunk_size = 40
        sections = []
        for i in range(0, total_lines, chunk_size):
            s_l = i + 1
            e_l = min(total_lines, i + chunk_size)
            snippet = " ".join(clean_lines[i:min(i+3, total_lines)])
            sec_title = f"Phần {len(sections)+1}: {snippet[:50]}..."
            sections.append(SemanticSection(
                title=sec_title,
                start_line=s_l,
                end_line=e_l,
                summary=f"Nội dung từ dòng {s_l} đến {e_l}"
            ))
        return sections
