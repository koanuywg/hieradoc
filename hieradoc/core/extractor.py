import re
from pathlib import Path
from typing import Tuple, List

import re
import os
from pathlib import Path
from typing import Tuple, List, Optional
from openai import OpenAI
from hieradoc.agents.vision_ocr import VisionOCRAgent

class FileExtractor:
    """
    Universal Document Extractor.
    Integrates Microsoft MarkItDown (Word, Excel, PowerPoint, PDF, HTML)
    and VisionOCRAgent (Scanned documents, photos, receipts, PNG/JPG)
    to convert any file format into clean Structured Markdown before line indexing.
    """

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}

    @classmethod
    def extract_text(
        cls,
        file_path_or_bytes: str | bytes,
        filename: str = "",
        client: Optional[OpenAI] = None,
        vision_model: str = "gpt-4o-mini"
    ) -> str:
        # 1. Xử lý đường dẫn file
        if isinstance(file_path_or_bytes, (str, Path)):
            p = Path(file_path_or_bytes)
            if not p.exists():
                raise FileNotFoundError(f"File not found: {file_path_or_bytes}")
            ext = p.suffix.lower()

            # A. Nếu là ảnh quét / ảnh chụp -> Dùng VisionOCRAgent
            if ext in cls.IMAGE_EXTENSIONS:
                return VisionOCRAgent.transcribe_image(p, client=client, model=vision_model)

            # B. Thử dùng MarkItDown của Microsoft cho các định dạng văn phòng và PDF
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(str(p))
                if result.text_content and result.text_content.strip():
                    return result.text_content
            except Exception:
                pass  # Fallback sang các bộ đọc chuyên biệt

            # C. Fallback cho PDF
            if ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(p))
                    pages_text = [page.extract_text() or "" for page in reader.pages]
                    return "\n".join(pages_text)
                except ImportError:
                    raise ImportError("Please install pypdf: pip install pypdf")

            # D. File văn bản thông thường (txt, md, json, csv, v.v.)
            return p.read_text(encoding="utf-8", errors="replace")

        # 2. Xử lý dạng bytes in-memory
        elif isinstance(file_path_or_bytes, bytes):
            ext = Path(filename).suffix.lower() if filename else ""

            if ext in cls.IMAGE_EXTENSIONS:
                return VisionOCRAgent.transcribe_image(file_path_or_bytes, client=client, model=vision_model)

            # Thử decode text thô
            try:
                return file_path_or_bytes.decode("utf-8")
            except UnicodeDecodeError:
                if ext == ".pdf":
                    import pypdf
                    import io
                    reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))
                    pages_text = [page.extract_text() or "" for page in reader.pages]
                    return "\n".join(pages_text)
                return file_path_or_bytes.decode("utf-8", errors="replace")

        return ""

    @classmethod
    def add_line_numbers(cls, raw_text: str) -> Tuple[str, List[str]]:
        """
        Splits text into lines and prepends [L0001], [L0002]...
        Returns: (indexed_text, clean_lines)
        """
        lines = raw_text.splitlines()
        clean_lines = []
        indexed_lines = []
        for i, line in enumerate(lines, 1):
            s_line = line.strip()
            clean_lines.append(s_line)
            indexed_lines.append(f"[L{i:04d}] {s_line}")
        return "\n".join(indexed_lines), clean_lines
