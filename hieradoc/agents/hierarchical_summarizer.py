import json
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI

class HierarchicalSummarizerAgent:
    """Bottom-up hierarchical summarizer: Leaf -> Branch -> Document Root."""

    @classmethod
    def summarize_leaf(
        cls,
        title: str,
        content_text: str,
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> str:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = f"Title: {title}\nContent:\n{content_text[:3000]}\n\nSummarize the key rule/obligation/commitment in 1-2 concise sentences."
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a concise document and policy summarizer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()

    @classmethod
    def summarize_branch(
        cls,
        branch_title: str,
        children_summaries: List[Dict[str, Any]],
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> str:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = (
            f"Branch Title: {branch_title}\n"
            f"Articles Summaries:\n{json.dumps(children_summaries, ensure_ascii=False)}\n\n"
            "Write a concise overview (under 100 words) summarizing the scope and purpose of this branch/chapter."
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a document policy summarizer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()

    @classmethod
    def summarize_root(
        cls,
        doc_title: str,
        chapters_overview: List[Dict[str, Any]],
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> str:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        prompt = (
            f"Document Title: {doc_title}\n"
            f"Chapters Overview:\n{json.dumps(chapters_overview, ensure_ascii=False)}\n\n"
            "Write a 2-4 sentence executive summary covering the overall scope and governance of this document."
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an executive document analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
