import os
import base64
from pathlib import Path
from typing import Optional, Union
from openai import OpenAI

class VisionOCRAgent:
    """
    Agentic Vision OCR using Vision-capable LLMs (gpt-4o-mini, gpt-4o).
    Transcribes images, scanned receipts, contracts, and documents into cleanly formatted,
    structured Markdown with preserved tables and headings.
    """

    SYSTEM_PROMPT = """
    You are an expert Document Transcription and OCR Agent.
    Your task:
    1. Transcribe all text from the provided image accurately and comprehensively.
    2. Faithfully reconstruct the hierarchical structure:
       - Use Markdown headings (# for Document title, ## for Chapters/Sections, ### for Articles/Clauses).
       - Reconstruct tables into clean Markdown tables (| col1 | col2 |).
       - Maintain lists (1., 2., a), b)) exactly as they appear.
    3. Output ONLY the clean transcribed Markdown text. Do not add markdown wrappers (no ```markdown).
    """

    @classmethod
    def transcribe_image(
        cls,
        image_path_or_bytes: Union[str, Path, bytes],
        client: Optional[OpenAI] = None,
        model: str = "gpt-4o-mini"
    ) -> str:
        if client is None:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if isinstance(image_path_or_bytes, (str, Path)):
            p = Path(image_path_or_bytes)
            with open(p, "rb") as f:
                img_bytes = f.read()
            mime_type = "image/png"
            if p.suffix.lower() in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            elif p.suffix.lower() == ".webp":
                mime_type = "image/webp"
        else:
            img_bytes = image_path_or_bytes
            mime_type = "image/png"

        b64_data = base64.b64encode(img_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_data}"

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": cls.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe this document image into clean structured markdown:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url}
                        }
                    ]
                }
            ],
            temperature=0.0
        )
        content = response.choices[0].message.content or ""
        return content.strip()
