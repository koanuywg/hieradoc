import os
from typing import Optional
from openai import OpenAI
from hieradoc.schemas.node import DocumentBlueprint

class DocumentInspectorAgent:
    """Inspects document sample text to detect document type, language, and heading patterns."""

    @classmethod
    def inspect(
        cls,
        sample_indexed_text: str,
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> DocumentBlueprint:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        system_prompt = """
        You are a Document Structure Architect.
        Tasks:
        1. Read the sample text (with line numbers [L0001]...).
        2. Detect the main document title, document type (contract, policy, report, manual, etc.), and primary language (vi, en, etc.).
        3. Determine whether the document has an explicit hierarchical heading system (has_explicit_headings).
           - True: Legal codes, policies, contracts, SLAs (with Chapters/Articles, Parts/Sections, 1./1.1...).
           - False: Essays, stories, continuous narrative prose.
        4. IF STRUCTURED: Generate exact Python Regex Patterns to match heading lines at the start of line (^):
           - level_1_pattern: Top-level headers (e.g. ^(Chương|CHƯƠNG|PART|SECTION|PHẦN)\s+[IVX0-9]+).
           - level_2_pattern: Second-level headers (e.g. ^(Điều|ARTICLE|ĐIỀU)\s+[0-9]+).
           - level_3_pattern: Third-level headers if applicable (e.g. ^[0-9]+\.[0-9]+).
        """

        response = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Sample Text:\n\n{sample_indexed_text[:4000]}"}
            ],
            response_format=DocumentBlueprint,
            temperature=0.0
        )

        blueprint = response.choices[0].message.parsed
        if not blueprint:
            raise ValueError("DocumentInspectorAgent failed to produce a valid DocumentBlueprint.")
        return blueprint
