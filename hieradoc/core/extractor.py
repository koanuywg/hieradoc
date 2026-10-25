import re
from pathlib import Path
from typing import Tuple, List

class FileExtractor:
    """Extracts raw text and prepends zero-indexed line numbers [L0001]."""

    @classmethod
    def extract_text(cls, file_path_or_bytes: str | bytes, filename: str = "") -> str:
        if isinstance(file_path_or_bytes, (str, Path)):
            p = Path(file_path_or_bytes)
            filename = p.name
            if p.suffix.lower() == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(p))
                    pages_text = [page.extract_text() or "" for page in reader.pages]
                    return "\n".join(pages_text)
                except ImportError:
                    raise ImportError("For PDF support, please install pypdf: pip install pypdf")
            else:
                return p.read_text(encoding="utf-8")
        elif isinstance(file_path_or_bytes, bytes):
            if filename.lower().endswith(".pdf"):
                try:
                    import pypdf
                    import io
                    reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))
                    pages_text = [page.extract_text() or "" for page in reader.pages]
                    return "\n".join(pages_text)
                except ImportError:
                    raise ImportError("For PDF support, please install pypdf: pip install pypdf")
            else:
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
