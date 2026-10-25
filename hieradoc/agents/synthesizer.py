import os
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from hieradoc.schemas.query import Citation

class SynthesizerResult(BaseModel):
    answer: str = Field(..., description="Complete, direct and grounded response")
    citations: List[Citation] = Field(default_factory=list, description="Verbatim citations with lines")
    confidence_score: float = Field(..., description="Confidence score from 0.0 to 1.0 based on evidence")

class QuerySynthesizer:
    """Synthesizes final answer with line-level citations from collected leaf nodes."""

    @classmethod
    def synthesize_answer(
        cls, 
        query: str, 
        collected_evidences: List[Dict[str, Any]], 
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> Tuple[SynthesizerResult, int, int]:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if not collected_evidences:
            res = SynthesizerResult(
                answer="Không tìm thấy thông tin hoặc căn cứ liên quan trong tài liệu để trả lời câu hỏi này.",
                citations=[],
                confidence_score=0.0
            )
            return res, 0, 0

        evidences_text = []
        for i, ev in enumerate(collected_evidences, 1):
            doc_title = ev.get("doc_title", ev.get("doc_id", "Văn bản"))
            branch = ev.get("branch_title", ev.get("branch_folder", "Mục"))
            title = ev.get("title", "Điều khoản")
            content = ev.get("content", "")
            s_line = ev.get("start_line")
            e_line = ev.get("end_line")

            evidences_text.append(
                f"--- EVIDENCE #{i} ---\n"
                f"Document: {doc_title} | Section: {branch} | Title: {title}\n"
                f"Line Range: L{s_line}-L{e_line}\n"
                f"Verbatim Content:\n{content}\n\n"
            )

        system_prompt = """
        You are a Grounded Evidence Synthesizer.
        Your task:
        1. Read the user's question and the provided VERBATIM EVIDENCE CHUNKS carefully.
        2. Formulate a comprehensive, direct, and well-structured answer in the same language as the user's query.
        3. STRICT GROUNDING PRINCIPLE:
           - NEVER speculate or hallucinate facts not present in the evidence.
           - For every assertion, rule, commitment or number, attach an exact quote in the citations list (exact_quote).
           - Provide accurate doc_id, doc_title, branch_title, leaf_title, and line numbers [start_line, end_line] for every citation.
        4. If evidence is missing or insufficient, explicitly declare what information could not be found.
        """

        user_content = (
            f"USER QUERY: {query}\n\n"
            f"COLLECTED EVIDENCE FROM TREE NODES:\n"
            f"{''.join(evidences_text)}"
        )

        response = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format=SynthesizerResult,
            temperature=0.0
        )

        result = response.choices[0].message.parsed
        u = response.usage
        inp_tokens = u.prompt_tokens if u else 0
        out_tokens = u.completion_tokens if u else 0
        return result, inp_tokens, out_tokens
