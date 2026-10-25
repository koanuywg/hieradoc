from typing import List

class TextSlicer:
    """Slices exact raw text by 1-indexed line numbers without losing whitespace or modifying content."""

    @classmethod
    def slice_by_lines(cls, clean_lines: List[str], start_line: int, end_line: int) -> str:
        idx_start = max(0, start_line - 1)
        idx_end = min(len(clean_lines), end_line)
        return "\n".join(clean_lines[idx_start:idx_end]).strip()

    @classmethod
    def count_words(cls, text: str) -> int:
        return len(text.split())
