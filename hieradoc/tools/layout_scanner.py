import re
from typing import List, Optional
from pydantic import BaseModel

class RawHeadingCandidate(BaseModel):
    line_number: int
    matched_text: str
    level: int

class LayoutScanner:
    """Scans heading candidates based on regex patterns and structural layout."""

    @classmethod
    def scan_headings(
        cls,
        clean_lines: List[str],
        level_1_pattern: Optional[str] = None,
        level_2_pattern: Optional[str] = None,
        level_3_pattern: Optional[str] = None,
    ) -> List[RawHeadingCandidate]:
        candidates: List[RawHeadingCandidate] = []

        patterns = [
            (1, re.compile(level_1_pattern, re.IGNORECASE) if level_1_pattern else None),
            (2, re.compile(level_2_pattern, re.IGNORECASE) if level_2_pattern else None),
            (3, re.compile(level_3_pattern, re.IGNORECASE) if level_3_pattern else None),
        ]

        ignore_prefixes = (
            "theo quy định tại", "hướng dẫn tại", "quy định tại", "được nêu tại",
            "như tại", "căn cứ tại", "as described in", "pursuant to", "according to", "referred to in"
        )

        for line_idx, line in enumerate(clean_lines, start=1):
            if not line or len(line) > 150:
                continue

            lower_line = line.lower()
            if any(lower_line.startswith(prefix) for prefix in ignore_prefixes):
                continue

            for level, compiled_pat in patterns:
                if compiled_pat and compiled_pat.search(line):
                    candidates.append(
                        RawHeadingCandidate(
                            line_number=line_idx,
                            matched_text=line,
                            level=level,
                        )
                    )
                    break

        return candidates
