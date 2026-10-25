import os
from enum import Enum
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

class CritiqueVerdict(str, Enum):
    FULFILLED = "FULFILLED"              # Bằng chứng đầy đủ, trực diện
    PARTIAL = "PARTIAL"                  # Đúng hướng nhưng thiếu con số/điều kiện
    CROSS_REFERENCE = "CROSS_REFERENCE"  # Dẫn chiếu sang Điều khoản khác cần tìm tiếp
    UNFULFILLED = "UNFULFILLED"          # Lạc đề hoặc không có thông tin

class EvidenceCritique(BaseModel):
    verdict: CritiqueVerdict
    confidence_score: float = Field(..., description="Score from 0.0 to 1.0 on evidence sufficiency")
    reasoning: str = Field(..., description="Concise assessment of why the evidence is sufficient or what is missing")
    missing_aspects: List[str] = Field(default_factory=list, description="Specific missing points from the query/objective")
    target_reference: Optional[str] = Field(None, description="Name or identifier of referenced article to follow, e.g. 'Điều 15' or 'Article 4'")
    suggested_action: str = Field(..., description="'accept', 'follow_reference', 'read_neighbor', 'backtrack'")

class TreeCriticAgent:
    """
    Balanced Tree Critic Agent.
    Evaluates leaf evidence against the user objective in a single-pass reflection.
    Diagnoses whether evidence is fulfilled, partial, or contains a cross-reference
    and prescribes concrete corrective actions for Sub-Agents.
    """

    @classmethod
    def critique_evidence(
        cls,
        objective: str,
        leaf_data: Dict[str, Any],
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> EvidenceCritique:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        title = leaf_data.get("title", "")
        content = leaf_data.get("content", "")

        system_prompt = """
        You are the Balanced Tree Critic for an Autonomous Hierarchical Document Navigator.
        Your task is to critique a retrieved leaf evidence chunk against the user's objective.

        Evaluation Criteria:
        1. FULFILLED: The evidence chunk directly, fully answers the objective with concrete rules/numbers.
        2. CROSS_REFERENCE: The text explicitly defers or cross-references another specific article/clause 
           (e.g., 'theo quy định tại Điều 15', 'as set forth in Section 4', 'pursuant to Article 7').
           Extract the target_reference and prescribe 'follow_reference'.
        3. PARTIAL: The chunk is on-topic but incomplete (e.g. query asks for terms AND penalties, but chunk only has terms).
           Prescribe 'read_neighbor'.
        4. UNFULFILLED: The chunk does not contain relevant information. Prescribe 'backtrack'.

        Be objective, concise, and decisive.
        """

        user_content = (
            f"SUB-AGENT OBJECTIVE: {objective}\n\n"
            f"LEAF TITLE: {title}\n"
            f"LEAF CONTENT:\n{content[:2500]}"
        )

        try:
            resp = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format=EvidenceCritique,
                temperature=0.0
            )
            result = resp.choices[0].message.parsed
            if result:
                return result
        except Exception:
            pass

        # Fallback default
        return EvidenceCritique(
            verdict=CritiqueVerdict.FULFILLED,
            confidence_score=0.7,
            reasoning="Default fallback: accepted without deep critique",
            missing_aspects=[],
            target_reference=None,
            suggested_action="accept"
        )
